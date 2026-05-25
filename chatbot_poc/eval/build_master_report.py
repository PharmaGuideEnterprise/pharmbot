#!/usr/bin/env python3
"""Generate the master per-question report across every strategy tested.

For each of the 91 questions (62 from the 4 client CSVs + 30 generated new
clinical scenarios), produces a unified record showing:

  - The question (verbatim)
  - The clinical editor's expected result
  - The clinical editor's negative feedback (what the prior chatbot did wrong)
  - The current production answer (Voyage + few-shot v2 + temp=0)
  - Pass/fail under EVERY strategy variation tested
  - If the question fails in production: which strategy (if any) DID pass it
  - Failure-mode classification

Output: chatbot_poc/eval/MASTER_QUESTION_REPORT.md
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

EVAL = Path("/Users/emad/Code/cps/chatbot_poc/eval")
OUT = EVAL / "MASTER_QUESTION_REPORT.md"

# Strategy runs, ordered chronologically + their human names
STRATEGIES_51 = [
    ("voyage_baseline",       "Voyage + enhanced prompt v1 (original baseline)",      "all51_v2_judged.json"),
    ("cohere_rerank",         "Cohere embedder + rerank top_15",                      "all51_cohere_rerank_topk15.json"),
    ("specialist_agents",     "Voyage + specialist agents (markdown-defined)",        "all51_agents_v2_judged.json"),
    ("verifier_rerank",       "Voyage + verifier + Voyage rerank + few-shot",         "all51_verified_judged.json"),
    ("verifier_no_rerank",    "Voyage + verifier + few-shot (no rerank)",             "all51_v3_judged.json"),
    ("production_fewshot",    "PRODUCTION: Voyage + few-shot prompt v2",              "all51_fewshot.json"),
    ("top7_t07",              "Voyage + few-shot v2 + top_k=7 + temp=0.07",           "all51_top7_t07.json"),
]
STRATEGIES_30 = [
    ("voyage_baseline",       "Voyage + enhanced prompt v1 (original baseline)",      "new30_v2_judged.json"),
    ("cohere_rerank",         "Cohere embedder + rerank top_15",                      "new30_cohere_rerank_topk15.json"),
    ("specialist_agents",     "Voyage + specialist agents (markdown-defined)",        "new30_agents_v2_judged.json"),
    ("verifier_rerank",       "Voyage + verifier + Voyage rerank + few-shot",         "new30_verified_judged.json"),
    ("verifier_no_rerank",    "Voyage + verifier + few-shot (no rerank)",             "new30_v3_judged.json"),
    ("production_fewshot",    "PRODUCTION: Voyage + few-shot prompt v2",              "new30_fewshot.json"),
    ("top7_t07",              "Voyage + few-shot v2 + top_k=7 + temp=0.07",           "new30_top7_t07.json"),
]

# Items legitimately excluded from scoring (UX feedback, conversational follow-ups,
# meta complaints — pre-acknowledged N/A)
PRE_NA = {"PC-4","PC-5","PC-6","PC-9","PC-10","PC-12","PC-16","SQ-5","SQ-14","SQ-15","SQ-16"}

# Items with eval-data quality issues (placeholder expected fields, "Y" tags,
# source-verified missing content) — reclassified to N/A in the headline number
RECLASSIFY_NA = {
    "CPHA-17": "Expected field was placeholder '(see full comment)' — no clinical criteria for the judge",
    "CPHA-19": "Expected field was placeholder '(see full comment)' — no clinical criteria",
    "CF-16":   "Editor's expected was tag 'Y'; source-grep confirmed MS chapter has ZERO probiotic mentions — model's 'no info' is correct",
    "CF-17":   "Editor's expected was tag 'Y'; MS chapter states only Siponimod is indicated for SPMS — model's 'not indicated' is correct",
    "CPHA-12-lithium": "Source-grep confirmed bipolar chapter doesn't address lithium-in-pregnancy specifically — model's 'no specific info' is correct",
    "PC-3":    "Question is literally just 'Ozempic' with no clinical context — model's clarification request is appropriate",
}


def load_strategy(filename: str) -> dict[str, dict]:
    """Load a strategy run, return {question_id: record}."""
    p = EVAL / filename
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    out = {}
    for r in data:
        out[r["id"]] = r
    return out


def classify_failure(question_id: str, strategy_records: dict[str, dict]) -> str:
    """Classify why a question fails across strategies."""
    # If reclassified, that's the reason
    if question_id in RECLASSIFY_NA:
        return f"EVAL-DATA: {RECLASSIFY_NA[question_id]}"

    # Check if ANY strategy passed it
    passes = [s for s, r in strategy_records.items()
              if r and r.get("judge") and r["judge"].get("passed")]
    if not passes:
        # Failed everywhere — look at the production failure reason
        prod = strategy_records.get("production_fewshot")
        if prod and prod.get("judge"):
            reason = prod["judge"].get("reasoning", "")
            # Quick heuristic classification
            r = reason.lower()
            if "external link" in r or "credibledmeds" in r or "credible meds" in r:
                return "SOURCE-GAP: Expected content not in CPS corpus (external resource)"
            if "missing" in r and ("specific" in r or "exact" in r):
                return "RETRIEVAL/SYNTHESIS: model didn't surface the expected specific content"
            if "calculate" in r or "calculation" in r or "max" in r and "dose" in r:
                return "REASONING: dose calculation / max-cap enforcement"
            if "trimester" in r and "threshold" in r:
                return "REASONING: patient-specific threshold application"
            if "lead with" in r or "contraindication" in r:
                return "REASONING: safety-first ordering"
            if "refus" in r or "declin" in r:
                return "REFUSAL: model refused; depends on whether source actually covers it"
            return "OTHER: see specific failure reason"

    return f"PRODUCTION FAILS — passes under: {', '.join(passes[:3])}"


def summarize_question(qid: str, base_record: dict, strategy_records: dict[str, dict]) -> dict:
    """Build the unified per-question record."""
    out = {
        "id": qid,
        "question": base_record.get("question", ""),
        "expected": base_record.get("expected", ""),
        "negative": base_record.get("negative", "")[:600] if base_record.get("negative") else "",
        "showstopper": base_record.get("showstopper", False),
        "source_csv": base_record.get("source", base_record.get("source_csv", "")),
        "is_pre_na": qid in PRE_NA,
        "is_reclassified_na": qid in RECLASSIFY_NA,
        "reclassify_reason": RECLASSIFY_NA.get(qid, ""),
    }
    # Per-strategy results
    strategy_results = {}
    for strat_key in strategy_records:
        r = strategy_records[strat_key]
        if r and r.get("judge"):
            strategy_results[strat_key] = {
                "passed": r["judge"].get("passed"),
                "reasoning": r["judge"].get("reasoning", "")[:300],
            }
        else:
            strategy_results[strat_key] = {"passed": None, "reasoning": "(not run)"}
    out["strategies"] = strategy_results

    # The production answer text (most recent)
    prod = strategy_records.get("production_fewshot") or {}
    out["production_answer"] = prod.get("answer", "")[:2500]
    out["production_passed"] = (prod.get("judge") or {}).get("passed")
    out["production_reasoning"] = (prod.get("judge") or {}).get("reasoning", "")[:400]

    # Which strategy works (if any)
    working = []
    for skey, sval in strategy_results.items():
        if sval.get("passed") is True:
            working.append(skey)
    out["working_strategies"] = working

    # Classification
    out["failure_class"] = classify_failure(qid, strategy_records)
    return out


def main() -> int:
    # Load base questions
    base_51 = json.loads((EVAL / "all_questions.json").read_text())
    base_30 = json.loads((EVAL / "new_questions.json").read_text())
    base_records = {r["id"]: r for r in base_51 + base_30}

    # Load strategy runs (separate per question set since file paths differ)
    strategies_51_data = {key: load_strategy(fname) for key, _name, fname in STRATEGIES_51}
    strategies_30_data = {key: load_strategy(fname) for key, _name, fname in STRATEGIES_30}

    # Build per-question records
    records_51: list[dict] = []
    records_30: list[dict] = []
    for qid, base in base_records.items():
        # Determine which set this question belongs to
        if qid.startswith("NQ-"):
            strats = {k: data.get(qid) for k, data in strategies_30_data.items()}
            records_30.append(summarize_question(qid, base, strats))
        else:
            strats = {k: data.get(qid) for k, data in strategies_51_data.items()}
            records_51.append(summarize_question(qid, base, strats))

    # Counts
    def count_set(records):
        total = len(records)
        pre_na = sum(1 for r in records if r["is_pre_na"])
        reclass_na = sum(1 for r in records if r["is_reclassified_na"])
        scoreable = total - pre_na - reclass_na
        prod_passed = sum(1 for r in records
                          if not r["is_pre_na"] and not r["is_reclassified_na"]
                          and r["production_passed"])
        return total, pre_na, reclass_na, scoreable, prod_passed

    t51, pn51, rn51, sc51, pp51 = count_set(records_51)
    t30, pn30, rn30, sc30, pp30 = count_set(records_30)

    # Strategy name lookup
    strat_names = {k: name for k, name, _ in STRATEGIES_51}

    # Generate the report
    lines: list[str] = []
    lines.append("# Master Per-Question Report")
    lines.append("")
    lines.append("Every evaluation question from the 4 client CSVs + 30 distilled new clinical scenarios. For each: the question text, what the clinical editor wanted, the current production answer, pass/fail status across every strategy we tested, and which strategy (if any) solves it.")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"| Set | Total | Pre-acknowledged N/A | Eval-data N/A | Scoreable | Production passes |")
    lines.append(f"|---|---|---|---|---|---|")
    lines.append(f"| Canonical 51 (4 client CSVs) | {t51} | {pn51} | {rn51} | {sc51} | **{pp51}/{sc51} = {100*pp51/sc51:.1f}%** |")
    lines.append(f"| New 30 (distilled clinical) | {t30} | {pn30} | {rn30} | {sc30} | **{pp30}/{sc30} = {100*pp30/sc30:.1f}%** |")
    lines.append(f"| **TOTAL** | {t51+t30} | {pn51+pn30} | {rn51+rn30} | {sc51+sc30} | **{pp51+pp30}/{sc51+sc30} = {100*(pp51+pp30)/(sc51+sc30):.1f}%** |")
    lines.append("")
    lines.append("Production stack: Voyage `voyage-4-large` + few-shot prompt v2 + `temperature=0` + Claude Haiku 4.5.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Helper to render a strategy result icon
    def icon(passed):
        if passed is True: return "✅"
        if passed is False: return "❌"
        return "·"

    # Helper to render the strategy table for a single question
    def render_strategies_table(record: dict, strategies: list) -> list[str]:
        out = ["| # | Strategy | Result |"]
        out.append("|---|---|---|")
        for idx, (skey, sname, _) in enumerate(strategies, 1):
            s = record["strategies"].get(skey, {})
            out.append(f"| {idx} | {sname} | {icon(s.get('passed'))} |")
        return out

    def render_question(record: dict, strategies: list) -> list[str]:
        lines: list[str] = []
        qid = record["id"]
        prod_p = record["production_passed"]
        if record["is_pre_na"]:
            badge = "⏭️ NOT-APPLICABLE (pre-acknowledged)"
        elif record["is_reclassified_na"]:
            badge = "⏭️ NOT-APPLICABLE (eval-data issue)"
        elif prod_p is True:
            badge = "✅ PASS in production"
        elif prod_p is False:
            badge = "❌ FAIL in production"
        else:
            badge = "❓ unknown"
        showstopper = " 🚨 SHOWSTOPPER" if record.get("showstopper") else ""
        lines.append(f"### {qid}{showstopper} — {badge}")
        lines.append("")
        lines.append(f"**Question:** {record['question']}")
        lines.append("")
        if record.get("expected"):
            lines.append(f"**Expected (clinical editor):** {record['expected'][:400]}")
            lines.append("")
        if record.get("negative"):
            lines.append(f"**Original negative feedback:** {record['negative'][:400]}")
            lines.append("")
        if record["is_reclassified_na"]:
            lines.append(f"**Reclassification reason:** {record['reclassify_reason']}")
            lines.append("")
        if record["is_pre_na"]:
            lines.append("**N/A reason:** Not a clinical Q&A — UX feedback / conversational follow-up / meta complaint.")
            lines.append("")

        # Strategy results table
        if not record["is_pre_na"]:
            lines.append("**Pass/fail across strategies:**")
            lines.append("")
            lines.extend(render_strategies_table(record, strategies))
            lines.append("")

        # Why it fails (if it fails in production and isn't N/A)
        if prod_p is False and not record["is_pre_na"] and not record["is_reclassified_na"]:
            lines.append(f"**Why it failed in production:** {record['production_reasoning']}")
            lines.append("")
            if record["working_strategies"]:
                lines.append(f"**Strategy that DOES pass this question:** "
                             f"{', '.join(record['working_strategies'])}")
                lines.append("")
            else:
                lines.append("**Strategy that solves it:** *None of the 7 strategies tested solves this question. "
                             "Failure class: " + record.get('failure_class', 'unclassified') + "*")
                lines.append("")

        # Production answer (if not skipped)
        if record.get("production_answer"):
            ans = record["production_answer"]
            if len(ans) > 1500:
                ans = ans[:1500] + "\n\n…(truncated)…"
            lines.append("**Production answer (truncated):**")
            lines.append("")
            lines.append("> " + ans.replace("\n", "\n> "))
            lines.append("")

        lines.append("---")
        lines.append("")
        return lines

    # Render canonical 51 — order: showstoppers first, then by ID
    lines.append("## Canonical 51 (questions from the 4 client CSVs)")
    lines.append("")
    lines.append("Sorted: showstoppers first (the original client-flagged failures), then by source/ID.")
    lines.append("")
    sorted_51 = sorted(records_51,
                       key=lambda r: (0 if r.get("showstopper") else 1, r["id"]))
    for r in sorted_51:
        lines.extend(render_question(r, STRATEGIES_51))

    # Render new 30
    lines.append("## New 30 (distilled clinical scenarios)")
    lines.append("")
    lines.append("Generated by Claude in 6 categories: edge cases (A), expected refusals (B), off-topic (C), numeric/safety-critical (D), common Q&A (E), nuance/distinction (F).")
    lines.append("")
    sorted_30 = sorted(records_30, key=lambda r: r["id"])
    for r in sorted_30:
        lines.extend(render_question(r, STRATEGIES_30))

    # Summary: questions that NO strategy solves
    lines.append("## Unsolved questions across ALL strategies")
    lines.append("")
    unsolved_51 = [r for r in records_51
                   if not r["is_pre_na"] and not r["is_reclassified_na"]
                   and not r["working_strategies"]]
    unsolved_30 = [r for r in records_30
                   if not r["is_pre_na"] and not r["is_reclassified_na"]
                   and not r["working_strategies"]]
    lines.append(f"Of the {sc51 + sc30} truly scoreable questions, "
                 f"**{len(unsolved_51) + len(unsolved_30)} fail in every strategy tested.**")
    lines.append("")
    if unsolved_51:
        lines.append("### Canonical 51 — unsolved")
        for r in unsolved_51:
            lines.append(f"- **{r['id']}**: {r['question'][:90]}")
            lines.append(f"  - Failure class: {r['failure_class']}")
        lines.append("")
    if unsolved_30:
        lines.append("### New 30 — unsolved")
        for r in unsolved_30:
            lines.append(f"- **{r['id']}**: {r['question'][:90]}")
            lines.append(f"  - Failure class: {r['failure_class']}")
        lines.append("")

    # Strategy ranking summary
    lines.append("## Strategy ranking")
    lines.append("")
    lines.append("Pass rate of each strategy across the truly scoreable questions.")
    lines.append("")
    lines.append("| Strategy | Canonical 51 (n=45) | New 30 (n=30) | Combined (n=75) |")
    lines.append("|---|---|---|---|")
    for skey, sname, _ in STRATEGIES_51:
        c51 = sum(1 for r in records_51
                  if not r["is_pre_na"] and not r["is_reclassified_na"]
                  and r["strategies"].get(skey, {}).get("passed"))
        c30 = sum(1 for r in records_30
                  if not r["is_pre_na"] and not r["is_reclassified_na"]
                  and r["strategies"].get(skey, {}).get("passed"))
        combined = c51 + c30
        lines.append(f"| {sname} | {c51}/45 = {100*c51/45:.1f}% | {c30}/30 = {100*c30/30:.1f}% | {combined}/75 = {100*combined/75:.1f}% |")
    lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT}")
    print(f"  Canonical 51: {pp51}/{sc51} passed in production ({100*pp51/sc51:.1f}%)")
    print(f"  New 30:       {pp30}/{sc30} passed in production ({100*pp30/sc30:.1f}%)")
    print(f"  Total:        {pp51+pp30}/{sc51+sc30} ({100*(pp51+pp30)/(sc51+sc30):.1f}%)")
    print(f"  Unsolved across all strategies: {len(unsolved_51) + len(unsolved_30)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
