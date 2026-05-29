"""LLM-as-judge for the CPS pharmacy chatbot benchmark.

Self-contained: both judge-prompt variants (STRICT and SILENT-aware) are
inlined verbatim from the production judge. The judge routes by corpus_signal:

  * `silent`  → SILENT_JUDGE_SYSTEM  (accepts "honest source-silent refusal"
                                       as a pass — see criterion (c)). Used
                                       for 5 audited qids where our private
                                       corpus genuinely lacks the expected
                                       content. The list is in
                                       questions/corpus_silent_qids.json —
                                       you'll likely want to re-audit this
                                       against YOUR corpus, since which
                                       questions are silent depends on what
                                       content you've ingested.
  * `unknown` → STRICT_JUDGE_SYSTEM  (default; the strict pre-criterion-(c)
                                       judge).

Output verdict is a dict {passed, reasoning, missing_expected, violated_negative}.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Default judge model — Claude Haiku is fast/cheap and accurate enough for
# the rubric. You can override via env (e.g. claude-sonnet-4-6 for stricter).
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-4-5-20251001")

HERE = Path(__file__).parent


STRICT_JUDGE_SYSTEM = """You are an expert clinical-pharmacy reviewer evaluating answers from an AI clinical chatbot. You will be shown:

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

Output ONLY a JSON object, no other text:
{
  "passed": true | false,
  "reasoning": "1-2 sentence explanation citing the specific (a) or (b) check that drove the decision",
  "missing_expected": ["specific clinical points from expected that are genuinely absent (not just paraphrased)"],
  "violated_negative": ["specific mistakes from negative feedback that the answer actually made"]
}"""


SILENT_JUDGE_SYSTEM = """You are an expert clinical-pharmacy reviewer evaluating answers from an AI clinical chatbot.

This question has been pre-audited: **the CPS corpus does NOT contain the specific clinical content the EXPECTED RESULT is asking for.** The chatbot's safety contract is "answer from the corpus OR honestly refuse"; for this question, an honest refusal is the CORRECT behaviour and must be rewarded, not penalized.

You will be shown the QUESTION, EXPECTED RESULT, NEGATIVE FEEDBACK, and the ACTUAL ANSWER.

DECISION RULE — pass when ANY of the following holds:

  (a) The substantive clinical content from EXPECTED is present (paraphrase / expanded / embedded in a list / extra detail around). Despite this question's corpus-silent status, occasionally the chatbot may have retrieved related content sufficient to address the expected; if so, PASS.

  (b) The answer does NOT make the SPECIFIC mistake described in NEGATIVE FEEDBACK.

  (c) HONEST SOURCE-SILENT REFUSAL: the answer clearly states the CPS corpus does not contain the specific content (e.g., "The retrieved chunks do not specify the exact dose for this scenario", "The CPS chapter on X covers Y but does not specifically address Z"), AND describes what IS in the corpus (the related content the chatbot did retrieve), AND does NOT invent or hallucinate the missing content → PASS.

To PASS, satisfy (c), OR satisfy BOTH (a) AND (b).

Failure modes that count as FAIL even on this corpus-silent question:
  - Inventing numeric values or drug recommendations not in retrieved chunks
  - Refusing generically without describing what IS in the corpus
  - Committing the specific mistake from NEGATIVE FEEDBACK

Output ONLY a JSON object, no other text:
{
  "passed": true | false,
  "reasoning": "1-2 sentence explanation citing which criterion (a/b/c) drove the decision",
  "missing_expected": ["clinical points genuinely absent (empty list if (c) applies)"],
  "violated_negative": ["specific mistakes from negative feedback that the answer made"]
}"""


@dataclass
class Verdict:
    passed: bool
    reasoning: str
    missing_expected: list
    violated_negative: list


_SILENT: set | None = None

def _load_silent_qids() -> set:
    global _SILENT
    if _SILENT is None:
        path = HERE / "questions" / "corpus_silent_qids.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        _SILENT = set(data.get("corpus_silent", {}).keys())
    return _SILENT


def get_corpus_signal(qid: str | None) -> str:
    """`silent` for the audited corpus-silent qids, else `unknown`."""
    return "silent" if qid and qid in _load_silent_qids() else "unknown"


def judge(question: str, expected: str, negative: str, answer: str,
          qid: str | None = None, retries: int = 3) -> Verdict:
    """Run the LLM judge against (question, expected, negative, answer).
    Routes by qid → corpus_signal. Raises on persistent API failure."""
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in env")

    system_prompt = (SILENT_JUDGE_SYSTEM if get_corpus_signal(qid) == "silent"
                     else STRICT_JUDGE_SYSTEM)

    user_msg = (
        f"QUESTION:\n{question}\n\n"
        f"EXPECTED RESULT (from clinical professional):\n{expected or '(none provided)'}\n\n"
        f"NEGATIVE FEEDBACK (what the chatbot must avoid, per clinical professional):\n{negative or '(none provided)'}\n\n"
        f"ACTUAL ANSWER from chatbot:\n{answer}\n\n"
        "Output your verdict as a JSON object only."
    )
    body = {
        "model": JUDGE_MODEL, "max_tokens": 1024,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_msg}],
        "temperature": 0.0,
    }
    headers = {"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY,
               "anthropic-version": "2023-06-01"}

    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                              headers=headers, json=body, timeout=60)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                time.sleep(2 ** attempt); continue
            text = r.json()["content"][0]["text"].strip()
            # The model sometimes wraps the JSON in ```json … ``` fences.
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"): text = text[4:]
                text = text.strip().rstrip("`").strip()
            v = json.loads(text)
            return Verdict(
                passed=bool(v.get("passed")),
                reasoning=v.get("reasoning", ""),
                missing_expected=v.get("missing_expected", []) or [],
                violated_negative=v.get("violated_negative", []) or [],
            )
        except Exception as e:
            last_err = repr(e)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"judge failed after {retries} retries: {last_err}")
