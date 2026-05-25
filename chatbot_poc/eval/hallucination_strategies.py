#!/usr/bin/env python3
"""Test prompt/temperature strategies against general hallucination failures.

We want strategies that GENERALIZE across hallucination patterns, not just the
client's UTI question. So we test multiple question types:

  Q1. UTI in pregnancy — full treatment    → F1 (threshold) + F2 (no elaboration)
                                              + F3 (drug-entity distinction)
  Q2. UTI antibiotics to avoid              → F3 stress test
  Q3. Cephalexin for UTI                    → F2 stress test (targeted)
  Q4. COVID-19 treatment                    → F4 (no off-corpus drug invention)
  Q5. Penicillin allergy in pregnancy       → F5 (refuse when source absent)
  Q6. "Best pizza in Toronto"               → F6 (refuse off-topic)

We test these strategies, each posted via Onyx's per-request
`prompt_override.system_prompt` and `temperature_override`:

  B0_baseline           — current production prompt, default temp
  A_hardened_prompt     — baseline + explicit anti-hallucination rules
  B_temp0               — baseline prompt + temperature=0
  C_quote_anchor        — hardened + verbatim-quote requirement + temp=0
  D_hardened_temp0      — hardened + temp=0
  E_aggressive_minimal  — "OVERSHOOT": refuse to add ANYTHING beyond list items
  F_chunks_high         — temp=0 + ask Onyx to retrieve more chunks (less invention)
  G_two_pass_critique   — generate normal, then second-turn self-critique to strip
                          unsupported claims  ← the "overshoot then tighten" idea
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

ONYX = "http://localhost:8080"
PERSONA_ID = 1
N_TRIALS = 3  # per strategy per question

QUESTIONS = [
    ("Q1_uti_pregnancy",
     "What is the treatment for asymptomatic UTI in a pregnant patient?"),
    ("Q2_uti_avoid",
     "Which antibiotics should be avoided when treating UTI during pregnancy and why?"),
    ("Q3_cephalexin",
     "Tell me about cephalexin for treating UTI in a pregnant patient."),
    ("Q5_pcn_allergy",
     "How do I manage a UTI in a pregnant patient with severe penicillin allergy?"),
    ("Q6_offtopic",
     "What is the best Italian restaurant in downtown Toronto?"),
]

BASELINE_PROMPT = Path(
    "/Users/emad/Code/cps/chatbot_poc/onyx_patches/strict_prompt.txt"
).read_text(encoding="utf-8")

HARDENED_RULES = """

ANTI-HALLUCINATION RULES (these address known failure modes — follow exactly):

H1. BULLET FIDELITY. When the source lists items as plain bullets (e.g. drug
    names without descriptions), reproduce them as plain bullets. Do NOT add
    parenthetical descriptions, usage notes, drug-class summaries, or mechanism
    explanations unless that exact text appears verbatim in the retrieved chunk.
    Wrong: "Cephalexin: a commonly used cephalosporin for UTIs in pregnancy"
    Right: "Cephalexin"

H2. PRESERVE NUMERIC THRESHOLDS VERBATIM. When the source states a specific
    count, duration, week range, or culture criterion (e.g. "2 consecutive
    cultures", "weeks 12-16", "1-2 weeks later", "≥10^8 cfu/L"), reproduce the
    EXACT number/range. Do not generalize ("multiple cultures") or paraphrase
    ("a couple of weeks").

H3. DRUG-ENTITY DISTINCTION. When the source distinguishes between a
    combination product and one of its components — most commonly sulfamethoxazole/
    trimethoprim (SMX/TMP) vs trimethoprim alone vs sulfamethoxazole alone —
    preserve EACH distinct restriction as the source states it. If the source
    says "trimethoprim and SMX/TMP avoided in first trimester" AND
    "sulfamethoxazole avoided in last 6 weeks", list these as TWO separate
    rules. Never merge them into a single combination-product warning.

H4. NO INFERRED DETAIL. If a chunk lists a drug as a bullet under "treatment
    options" without telling you when, why, or how to use it, do not invent
    that context. State what the source says and stop.

H5. WHEN SOURCE IS SILENT, SAY SO. If the user asks about a specific scenario
    (e.g. "severe penicillin allergy") and the retrieved chunks do not address
    that scenario, you must say "The retrieved CPS content does not address
    this specific scenario" and either (a) describe the general framework the
    source DOES provide, or (b) decline to answer. Do not assume general
    medical knowledge fills the gap.
"""

QUOTE_ANCHOR_SUFFIX = """

QUOTE-ANCHOR FORMAT (mandatory):
For every clinical claim, structure supporting detail as:
  <verbatim quote from source in quotation marks> [N]
followed by, if helpful, one short sentence of clarification that introduces
NO new clinical facts. If you cannot point to a verbatim phrase in a retrieved
chunk supporting a claim, omit that claim.
"""

AGGRESSIVE_MINIMAL_PROMPT = BASELINE_PROMPT + """

OVERSHOOT MODE — STRICT VERBATIM:

You are now in strict verbatim mode. Every sentence you write must be either:
  (a) a direct quote from a retrieved chunk, in quotation marks, with citation
  (b) a one-sentence framing sentence with no clinical content (e.g.
      "The source addresses this as follows:")

You may NOT:
  - paraphrase
  - synthesize
  - add transitions like "additionally" or "moreover" that introduce new claims
  - explain WHY a recommendation exists if the source doesn't state the why
  - convert a bullet list into prose
  - add any drug description beyond the bare name listed in the source

If the retrieved chunks do not contain the answer, reply EXACTLY:
  "The CPS knowledge base I can access does not contain detailed information
  on this topic. Please consult primary sources or the full CPS publication."
"""

# Two-pass: a second turn that asks the model to critique its own answer
CRITIQUE_PROMPT = """Below is the answer you just generated. Re-read each sentence carefully against the retrieved CPS chunks.

For each clinical fact in the answer, ask: "Is this exact fact present in a retrieved chunk?" If NOT, the sentence must be deleted or rewritten to match the source exactly. Pay particular attention to:

  • Numeric thresholds (must be verbatim — e.g. "2 consecutive cultures", "weeks 12-16")
  • Drug names: if listed as a plain bullet in the source, do NOT add description, class, mechanism, or usage notes
  • Combination products vs individual entities: if the source distinguishes (e.g. "SMX/TMP first trimester" vs "sulfamethoxazole last 6 weeks"), preserve BOTH rules separately
  • Causal claims ("because X causes Y"): only include if the source states the causal relationship

Output ONLY the corrected answer. Do not explain your edits. Use the same citation markers [N] as the original."""

# ────────── strategies ──────────────────────────────────────────────

@dataclass
class Strategy:
    name: str
    system_prompt: str | None
    temperature: float | None
    chunks_above: int | None = None  # extra context
    chunks_below: int | None = None
    two_pass_critique: bool = False


STRATEGIES = [
    Strategy("B0_baseline", None, None),
    Strategy("A_hardened_prompt", BASELINE_PROMPT + HARDENED_RULES, None),
    Strategy("B_temp0", None, 0.0),
    Strategy("C_quote_anchor", BASELINE_PROMPT + HARDENED_RULES + QUOTE_ANCHOR_SUFFIX, 0.0),
    Strategy("D_hardened_temp0", BASELINE_PROMPT + HARDENED_RULES, 0.0),
    Strategy("E_aggressive_minimal", AGGRESSIVE_MINIMAL_PROMPT, 0.0),
    Strategy("F_chunks_high", BASELINE_PROMPT + HARDENED_RULES, 0.0, chunks_above=2, chunks_below=2),
    Strategy("G_two_pass_critique", BASELINE_PROMPT + HARDENED_RULES, 0.0, two_pass_critique=True),
]


# ────────── Onyx driver ────────────────────────────────────────────

def login() -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{ONYX}/auth/login",
        data={"username": "admin@example.com", "password": "changeme"},
        timeout=30,
    )
    if r.status_code not in (200, 204):
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:200]}")
    return s


def new_session(s: requests.Session) -> str:
    r = s.post(
        f"{ONYX}/chat/create-chat-session",
        json={"persona_id": PERSONA_ID, "description": "strategy test"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["chat_session_id"]


def _send(
    s: requests.Session,
    cid: str,
    message: str,
    strategy: Strategy,
    parent_message_id: int | None = None,
) -> tuple[str, int | None]:
    """Send one message; return (answer_text, message_id_of_assistant_reply)."""
    body: dict = {
        "chat_session_id": cid,
        "parent_message_id": parent_message_id,
        "message": message,
        "search_doc_ids": None,
        "retrieval_options": {
            "run_search": "always",
            "real_time": True,
            "enable_auto_detect_filters": False,
            "filters": None,
        },
        "file_descriptors": [],
    }
    if strategy.system_prompt is not None:
        body["prompt_override"] = {"system_prompt": strategy.system_prompt}
    if strategy.temperature is not None:
        body["temperature_override"] = strategy.temperature
    if strategy.chunks_above is not None:
        body["chunks_above"] = strategy.chunks_above
    if strategy.chunks_below is not None:
        body["chunks_below"] = strategy.chunks_below

    answer_parts: list[str] = []
    assistant_message_id: int | None = None

    with s.post(
        f"{ONYX}/chat/send-message", json=body, stream=True, timeout=180
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(
                f"send-message HTTP {resp.status_code}: {resp.text[:300]}"
            )
        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            inner = obj.get("obj") if isinstance(obj.get("obj"), dict) else obj
            if not isinstance(inner, dict):
                continue
            t = inner.get("type")
            if t == "message_delta":
                content = inner.get("content") or inner.get("answer_piece") or ""
                if content:
                    answer_parts.append(content)
            elif "answer_piece" in inner and inner.get("answer_piece"):
                answer_parts.append(inner["answer_piece"])
            # Capture the final assistant message id for two-pass critique
            if inner.get("message_id") and inner.get("message_type") in ("assistant", None):
                assistant_message_id = inner.get("message_id")

    return "".join(answer_parts), assistant_message_id


def send_message(s: requests.Session, question: str, strategy: Strategy) -> str:
    cid = new_session(s)
    answer, msg_id = _send(s, cid, question, strategy)
    if strategy.two_pass_critique and answer.strip():
        # Send the critique as a follow-up turn in the same session.
        critique_msg = (
            CRITIQUE_PROMPT
            + "\n\n────────── ORIGINAL ANSWER ──────────\n"
            + answer
        )
        revised, _ = _send(s, cid, critique_msg, strategy, parent_message_id=msg_id)
        # Use the revised answer if it's non-empty
        if revised.strip():
            return revised
    return answer


# ────────── scoring ────────────────────────────────────────────────

@dataclass
class Score:
    f1_threshold: bool
    f2_no_cephalexin_invention: bool
    f3_smx_tmp_distinct: bool
    f4_no_offtopic_drugs: bool
    f5_acknowledges_gap: bool
    f6_offtopic_refused: bool
    notes: list[str]

    def applicable_count(self, applicable: set[str]) -> tuple[int, int]:
        """How many applicable checks passed, out of how many applicable."""
        mapping = {
            "F1": self.f1_threshold,
            "F2": self.f2_no_cephalexin_invention,
            "F3": self.f3_smx_tmp_distinct,
            "F4": self.f4_no_offtopic_drugs,
            "F5": self.f5_acknowledges_gap,
            "F6": self.f6_offtopic_refused,
        }
        passed = sum(1 for k in applicable if mapping[k])
        return passed, len(applicable)


# Which checks are applicable to each question
QUESTION_CHECKS: dict[str, set[str]] = {
    "Q1_uti_pregnancy": {"F1", "F2", "F3"},
    "Q2_uti_avoid":     {"F3"},
    "Q3_cephalexin":    {"F2"},
    "Q5_pcn_allergy":   {"F5"},
    "Q6_offtopic":      {"F6"},
}


def score(qkey: str, question: str, answer: str) -> Score:
    notes: list[str] = []
    low = answer.lower()
    applicable = QUESTION_CHECKS[qkey]

    # F1 — "2 consecutive cultures" threshold preserved
    f1 = True
    if "F1" in applicable:
        f1 = bool(re.search(r"\b2\s+consecutive\b|\btwo\s+consecutive\b", low))
        if not f1:
            notes.append("F1: '2 consecutive cultures' threshold missing")

    # F2 — no invented elaboration on cephalexin
    f2 = True
    if "F2" in applicable and "cephalexin" in low:
        for m in re.finditer(r"cephalexin", low):
            window = low[m.start() : m.start() + 280]
            bad = [
                "commonly used", "broad-spectrum", "broad spectrum",
                "well-tolerated", "well tolerated", "first-line cephalosporin",
                "first line cephalosporin", "class of", "usage:", "mechanism",
                "bactericidal", "first-generation cephalosporin",
                "first generation cephalosporin", "is a cephalosporin",
                "is an oral cephalosporin", "oral cephalosporin antibiotic",
                "cell wall", "beta-lactam", "beta lactam",
            ]
            hits = [b for b in bad if b in window]
            if hits:
                f2 = False
                notes.append(f"F2: cephalexin invented elaboration {hits}")
                break

    # F3 — SMX vs TMP distinction. Must have BOTH:
    #   (a) first-trimester restriction (TMP or SMX/TMP)
    #   (b) sulfamethoxazole-SPECIFIC late-pregnancy restriction
    f3 = True
    if "F3" in applicable:
        has_first_tri = (
            "first trimester" in low or "1st trimester" in low or "antifolate" in low
        )
        near = r"(?:last\s+(?:6|six)\s+weeks|near\s+term)"
        has_late_sulfa = (
            "hyperbilirubinemia" in low
            or "kernicterus" in low
            or bool(re.search(rf"sulfamethoxazole[^.\n]{{0,120}}{near}", low))
            or bool(re.search(rf"{near}[^.\n]{{0,120}}sulfamethoxazole", low))
        )
        f3 = has_first_tri and has_late_sulfa
        if not f3:
            notes.append(
                f"F3: SMX vs TMP distinction missing "
                f"(first_tri={has_first_tri}, late_sulfa={has_late_sulfa})"
            )

    # F4 — for COVID, must NOT invent specific antiviral names that aren't in
    # the retrieved chunks. We can't easily check what was retrieved, but we
    # CAN flag known-likely-hallucination drugs that we know aren't in CPS
    # corpus. The covid19.md doesn't list Paxlovid by name in the chunks.
    f4 = True
    if "F4" in applicable:
        # Paxlovid IS legitimately in the source per the COVID-19 chapter,
        # so we don't flag it. We flag obviously off-corpus claims like
        # specific dose+frequency that often hallucinated, or specific brand
        # names not in CPS.
        # For now: if answer is suspiciously confident about a specific
        # regimen, flag it.  A more nuanced check requires chunk inspection.
        # Soft check: did the model add a definitive recommendation without
        # the "the CPS knowledge base does not contain" hedge while citing
        # only [1]?
        # Honest assessment: we cannot fully automate F4 without retrieved-
        # chunk comparison. Leave as True (pass) and inspect manually.
        f4 = True
        notes.append("F4: manual inspection required (not auto-scored)")

    # F5 — when source is silent, acknowledges the gap
    f5 = True
    if "F5" in applicable:
        gap_phrases = [
            "does not contain",
            "does not address",
            "not present",
            "not specified",
            "not mentioned",
            "not provided",
            "i can only answer",
            "i cannot find",
            "the source does not",
        ]
        f5 = any(p in low for p in gap_phrases)
        if not f5:
            notes.append("F5: did not acknowledge that source is silent on PCN-allergic UTI")

    # F6 — off-topic refusal
    f6 = True
    if "F6" in applicable:
        refusal_phrases = [
            "i can only answer",
            "off-topic",
            "off topic",
            "pharmacy knowledge base",
            "cps pharmacy",
            "not pharmacy",
            "i'm unable to",
            "outside the scope",
        ]
        f6 = any(p in low for p in refusal_phrases)
        if not f6:
            notes.append("F6: did not refuse off-topic question (restaurant query)")

    return Score(f1, f2, f3, f4, f5, f6, notes)


# ────────── runner ────────────────────────────────────────────────

def main() -> int:
    s = login()
    print(
        f"Strategies × Questions × Trials = {len(STRATEGIES)} × {len(QUESTIONS)} × {N_TRIALS}"
    )
    print()
    results: dict[str, dict[str, list[Score]]] = {}
    answers: dict[str, dict[str, list[str]]] = {}
    for strat in STRATEGIES:
        print(f"━━ {strat.name} ━━")
        results[strat.name] = {}
        answers[strat.name] = {}
        for qkey, qtext in QUESTIONS:
            applicable = QUESTION_CHECKS[qkey]
            print(f"  {qkey}: {qtext[:60]}…  (checks: {sorted(applicable)})")
            qscores: list[Score] = []
            qanswers: list[str] = []
            for trial in range(N_TRIALS):
                try:
                    ans = send_message(s, qtext, strat)
                except Exception as e:
                    ans = f"<ERROR: {e}>"
                sc = score(qkey, qtext, ans)
                qscores.append(sc)
                qanswers.append(ans)
                passed, total = sc.applicable_count(applicable)
                mark = "✓" if passed == total else "✗"
                print(f"    trial {trial+1}: {mark} {passed}/{total}")
                for n in sc.notes:
                    print(f"      - {n}")
                time.sleep(1)
            results[strat.name][qkey] = qscores
            answers[strat.name][qkey] = qanswers
        print()

    # Summary: % of applicable checks passed across all trials
    print("=" * 100)
    print("SUMMARY  (% of applicable checks passed, all trials)")
    print("=" * 100)
    header = f"{'strategy':<22}"
    for qkey, _ in QUESTIONS:
        header += f"  {qkey[:12]}"
    header += "   overall"
    print(header)
    overall_table: list[tuple[str, float]] = []
    for strat in STRATEGIES:
        row = f"{strat.name:<22}"
        total_passed = 0
        total_checks = 0
        for qkey, _ in QUESTIONS:
            qs = results[strat.name][qkey]
            applicable = QUESTION_CHECKS[qkey]
            qp = sum(sc.applicable_count(applicable)[0] for sc in qs)
            qt = sum(sc.applicable_count(applicable)[1] for sc in qs)
            row += f"  {qp:>3}/{qt:<3}    "
            total_passed += qp
            total_checks += qt
        pct = 100 * total_passed / total_checks if total_checks else 0.0
        row += f"   {total_passed}/{total_checks} ({pct:.0f}%)"
        overall_table.append((strat.name, pct))
        print(row)

    # Rank
    overall_table.sort(key=lambda x: -x[1])
    print("\nRanked:")
    for i, (name, pct) in enumerate(overall_table):
        print(f"  {i+1}. {name:<22} {pct:.0f}%")

    out = Path(__file__).resolve().parent / "hallucination_strategies_output.json"
    out.write_text(
        json.dumps(
            {
                strat.name: {
                    qkey: {
                        "question": qtext,
                        "checks": sorted(QUESTION_CHECKS[qkey]),
                        "answers": answers[strat.name][qkey],
                        "scores": [
                            {
                                "F1": sc.f1_threshold,
                                "F2": sc.f2_no_cephalexin_invention,
                                "F3": sc.f3_smx_tmp_distinct,
                                "F5": sc.f5_acknowledges_gap,
                                "F6": sc.f6_offtopic_refused,
                                "notes": sc.notes,
                            }
                            for sc in results[strat.name][qkey]
                        ],
                    }
                    for qkey, qtext in QUESTIONS
                }
                for strat in STRATEGIES
            },
            indent=2,
        )
    )
    print(f"\nFull answers saved to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
