#!/usr/bin/env python3
"""LLM-as-judge scorer — agnostic, generic evaluation that replaces the
brittle per-question regex/keyword checks.

For each question, calls Claude Haiku 4.5 with:
  - the question
  - the clinical editor's "Expected Result" (positive ground truth)
  - the clinical editor's "Negative Comments" (what must NOT happen)
  - the actual new answer

Claude returns a structured JSON verdict:
  {
    "passed": true|false,
    "reasoning": "...",
    "missing_expected": ["..."],
    "violated_negative": ["..."]
  }

This is the strategy upgrade from per-question regex: no hand-tuning per
question, works for any new question with expected + negative fields,
catches subtle clinical errors that regex can't (e.g. "the answer says
oxybutynin 5mg in a paragraph that doesn't clearly disclaim it's for
urgency not stress" → regex misses this, LLM judge catches it).
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

# Read ANTHROPIC_API_KEY from chatbot_poc/.env
ENV_PATH = Path("/Users/emad/Code/cps/chatbot_poc/.env")
def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

ENV = _load_env()
ANTHROPIC_KEY = ENV.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")

# JUDGE_MODEL is resolved at call time via chatbot_poc.shim_service.llm_config
# (default tier = Onyx admin's fast_default_model_name, overridable via env
# JUDGE_MODEL — see ai/plans/onyx-llm-source-of-truth.md).
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))
from chatbot_poc.shim_service import llm_config  # noqa: E402

JUDGE_SYSTEM = """You are an expert clinical-pharmacy reviewer evaluating answers from an AI clinical chatbot. You will be shown:

1. The QUESTION asked of the chatbot
2. The EXPECTED RESULT — a SHORT NOTE the clinical professional wrote summarising what the answer should contain. This is a MINIMUM bar, not a maximum. Additional clinically-correct content beyond the expected is fine and often desirable.
3. The NEGATIVE FEEDBACK — a description of the SPECIFIC mistake an earlier chatbot version made. The new answer passes this section if it DOES NOT make that specific mistake.
4. The ACTUAL ANSWER the chatbot produced

DECISION RULE — pass requires BOTH:

  (a) The substantive clinical content from EXPECTED is present (in any form — paraphrase, expanded explanation, embedded in a list, with extra detail around it). If the expected says "treat after 2 cultures, drug list including X, Y, Z", the answer passes (a) when those concepts appear, regardless of phrasing or surrounding extra content.

  (b) The answer does NOT make the SPECIFIC mistake described in NEGATIVE FEEDBACK. To violate (b), the answer must commit the actual error the clinical editor described — e.g. "merged SMX vs TMP" means the answer treats them as one rule with one trimester restriction; "invented Cephalexin description" means the answer adds a class/mechanism description not in the source.

CRITICAL: Adding correct, source-grounded content BEYOND what's literally in EXPECTED is NOT a violation. The expected field is a clinical-editor shorthand, not a verbatim transcript of what the answer must say. Only count something as "missing" if it's a clinical fact required by the question that the answer omitted.

Be strict on safety-critical content:
  - Patient-specific applicability (age thresholds, pregnancy contraindications, weight-based dosing)
  - Combination vs individual entity distinction (e.g. SMX/TMP first-trimester rule vs SMX-alone last-6-weeks rule must be PRESENT AS SEPARATE rules to pass; merging them is a fail)
  - Numeric thresholds the source provides ("2 consecutive cultures", "weeks 12-16", "10 days")
  - Refusing or hedging when the question targets a sub-scenario the source doesn't directly address

Examples of (b) violations vs non-violations:
  - VIOLATION: negative says "merged SMX vs TMP" → answer says only "Avoid trimethoprim and SMX/TMP in pregnancy" with no separate sulfamethoxazole-late-pregnancy rule.
  - NOT a violation: negative says "merged SMX vs TMP" → answer says BOTH "TMP and SMX/TMP avoided in 1st trimester" AND "sulfamethoxazole avoided last 6 weeks" — this IS the distinction the editor wanted.
  - VIOLATION: negative says "invented Cephalexin description" → answer says "Cephalexin: a commonly used first-line cephalosporin antibiotic" with no source citation.
  - NOT a violation: negative says "invented Cephalexin description" → answer lists "Cephalexin" as a plain bullet with no embellishment.

Output ONLY a JSON object, no other text:
{
  "passed": true | false,
  "reasoning": "1-2 sentence explanation citing the specific (a) or (b) check that drove the decision",
  "missing_expected": ["specific clinical points from expected that are genuinely absent (not just paraphrased)"],
  "violated_negative": ["specific mistakes from negative feedback that the answer actually made"]
}"""


@dataclass
class JudgeVerdict:
    passed: bool
    reasoning: str
    missing_expected: list[str]
    violated_negative: list[str]


def judge(question: str, expected: str, negative: str, answer: str,
          retries: int = 3) -> JudgeVerdict:
    """Call Claude as judge. Returns JudgeVerdict; raises on persistent error."""
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in env or .env")

    user_msg = f"""QUESTION:
{question}

EXPECTED RESULT (from clinical professional):
{expected or '(none provided)'}

NEGATIVE FEEDBACK (what the chatbot must avoid, per clinical professional):
{negative or '(none provided)'}

ACTUAL ANSWER from chatbot:
{answer}

Output your verdict as a JSON object only."""

    body = {
        "model": llm_config.get_judge_model(),
        "max_tokens": 1024,
        "system": JUDGE_SYSTEM,
        "messages": [{"role": "user", "content": user_msg}],
        "temperature": 0.0,
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
    }

    for attempt in range(retries):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=body, timeout=60,
            )
        except Exception as e:
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"judge API error: {e}") from e
        if r.status_code == 429:
            # Rate limit: backoff
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"judge HTTP {r.status_code}: {r.text[:300]}")

        text = r.json()["content"][0]["text"].strip()
        # Strip code fences if present
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            if attempt + 1 < retries:
                continue
            raise RuntimeError(f"judge returned non-JSON: {text[:300]}") from e

        return JudgeVerdict(
            passed=bool(data.get("passed")),
            reasoning=str(data.get("reasoning", ""))[:500],
            missing_expected=list(data.get("missing_expected") or []),
            violated_negative=list(data.get("violated_negative") or []),
        )
    raise RuntimeError("judge exhausted retries")


def judge_results(answers_file: Path, out_file: Path) -> dict:
    """Run the judge across all scoreable items in answers_file.
    Returns summary stats."""
    items = json.loads(answers_file.read_text())
    # Filter to scoreable items (passed is not None)
    scoreable = [i for i in items if i.get("passed") is not None]
    print(f"Judging {len(scoreable)} scoreable items via {llm_config.get_judge_model()}…")

    verdicts: list[dict] = []
    for i, item in enumerate(scoreable, 1):
        qid = item["id"]
        question = item["question"]
        expected = item.get("expected", "")
        negative = item.get("negative", "")
        answer = item.get("answer", "")
        if not answer or answer.startswith("<ERROR"):
            verdicts.append({**item, "judge": {
                "passed": False,
                "reasoning": "API error or empty answer",
                "missing_expected": [],
                "violated_negative": [],
            }})
            print(f"  [{i:>2}/{len(scoreable)}] {qid:<24} SKIP (empty/error answer)")
            continue

        try:
            v = judge(question, expected, negative, answer)
        except Exception as e:
            print(f"  [{i:>2}/{len(scoreable)}] {qid:<24} JUDGE ERROR: {e}")
            verdicts.append({**item, "judge": {
                "passed": None,
                "reasoning": f"judge error: {e}",
                "missing_expected": [],
                "violated_negative": [],
            }})
            continue
        mark = "PASS" if v.passed else "FAIL"
        print(f"  [{i:>2}/{len(scoreable)}] {qid:<24} {mark}  {v.reasoning[:80]}")
        verdicts.append({**item, "judge": {
            "passed": v.passed,
            "reasoning": v.reasoning,
            "missing_expected": v.missing_expected,
            "violated_negative": v.violated_negative,
        }})
        time.sleep(0.5)  # avoid bursting

    out_file.write_text(json.dumps(verdicts, indent=2))

    # Summary
    passed = sum(1 for v in verdicts if v["judge"]["passed"] is True)
    failed = sum(1 for v in verdicts if v["judge"]["passed"] is False)
    errored = sum(1 for v in verdicts if v["judge"]["passed"] is None)
    n = len(verdicts) - errored
    pct = 100 * passed / n if n else 0
    print(f"\n  LLM-judge accuracy: {passed}/{n} = {pct:.1f}%"
          f" (errored: {errored})")
    return {"passed": passed, "failed": failed, "errored": errored, "pct": pct, "n": n}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default="chatbot_poc/eval/full_eval_answers.json")
    ap.add_argument("--out", default="chatbot_poc/eval/llm_judge_verdicts.json")
    args = ap.parse_args()
    judge_results(Path(args.answers), Path(args.out))
