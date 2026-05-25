#!/usr/bin/env python3
"""Build a clean failure-only report for clinical pharmacist review.

Includes only questions that failed in production. For each:
  - Question text
  - Expected answer (clinical editor)
  - Original negative feedback
  - Production answer (FULL — not truncated)
  - Auto-judge's reason for failing
  - Space for the pharmacist's verdict

Output: chatbot_poc/eval/PHARMACIST_REVIEW.md
"""
from __future__ import annotations

import json
from pathlib import Path

EVAL = Path("/Users/emad/Code/cps/chatbot_poc/eval")
OUT = EVAL / "PHARMACIST_REVIEW.md"

PRE_NA = {"PC-4","PC-5","PC-6","PC-9","PC-10","PC-12","PC-16","SQ-5","SQ-14","SQ-15","SQ-16"}
RECLASSIFY_NA = {
    "CPHA-17": "Expected field was placeholder '(see full comment)'",
    "CPHA-19": "Expected field was placeholder '(see full comment)'",
    "CF-16":   "Editor's 'Y' was an inclusion tag; source has zero probiotic mentions",
    "CF-17":   "Editor's 'Y' was an inclusion tag; source says only Siponimod for SPMS",
    "CPHA-12-lithium": "Source doesn't address lithium-in-pregnancy specifically",
    "PC-3":    "Question is just 'Ozempic' — no clinical context, model asked for clarification",
}


def load_run(filename: str) -> dict[str, dict]:
    p = EVAL / filename
    if not p.exists():
        return {}
    return {r["id"]: r for r in json.loads(p.read_text())}


def main() -> int:
    canonical_q = json.loads((EVAL / "all_questions.json").read_text())
    new_q       = json.loads((EVAL / "new_questions.json").read_text())
    by_id       = {r["id"]: r for r in canonical_q + new_q}

    canon_run = load_run("all51_fewshot.json")
    new_run   = load_run("new30_fewshot.json")

    failures: list[dict] = []
    for qid, base in by_id.items():
        if qid in PRE_NA or qid in RECLASSIFY_NA:
            continue
        run = canon_run.get(qid) or new_run.get(qid)
        if not run or not run.get("judge"):
            continue
        if run["judge"].get("passed"):
            continue
        # Failure record
        failures.append({
            "id": qid,
            "source": base.get("source", ""),
            "showstopper": base.get("showstopper", False),
            "question": base.get("question", ""),
            "expected": base.get("expected", ""),
            "negative": base.get("negative", ""),
            "answer": run.get("answer", ""),
            "fail_reason": (run.get("judge") or {}).get("reasoning", ""),
        })

    # Sort: showstoppers first, then by ID
    failures.sort(key=lambda r: (0 if r["showstopper"] else 1, r["id"]))

    # Render
    lines: list[str] = []
    lines.append("# Failed-Question Review — for Clinical Pharmacist")
    lines.append("")
    lines.append(f"**Total questions evaluated:** 75 scoreable (45 canonical from the 4 client CSVs + 30 distilled new clinical scenarios)")
    lines.append(f"**Failures requiring review:** {len(failures)}")
    lines.append(f"**Production stack:** Voyage `voyage-4-large` retrieval + Claude Haiku 4.5 + few-shot system prompt v2 + `temperature=0`")
    lines.append("")
    lines.append("**How to review each entry:**")
    lines.append("1. Read the question + the clinical editor's expected answer.")
    lines.append("2. Read the chatbot's actual answer.")
    lines.append("3. Decide: is the answer **clinically acceptable** for a licensed pharmacist to act on?")
    lines.append("4. Tick the box at the end of each entry: ☐ Clinically OK  ☐ Needs revision  ☐ Dangerous")
    lines.append("5. Add a one-line note on what's specifically wrong, if anything.")
    lines.append("")
    lines.append("The 'auto-judge reason' line shows why our automated LLM-judge marked it as a failure — sometimes the judge is over-strict and a human reviewer disagrees; we want your independent verdict.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary table (read this first)")
    lines.append("")
    lines.append("| # | ID | 🚨 | Full question | Expected (per clinical editor) | Why our judge flagged it |")
    lines.append("|---|---|---|---|---|---|")
    for i, f in enumerate(failures, 1):
        flag = "🚨" if f["showstopper"] else ""
        # Sanitize for markdown table cells — replace pipes and newlines but keep the FULL text
        def cell(text: str) -> str:
            if not text:
                return "—"
            return text.replace("|", "\\|").replace("\n", "<br>").strip()
        q = cell(f["question"])
        exp = cell(f["expected"]) if f.get("expected") else "—"
        why = cell(f["fail_reason"][:400])
        lines.append(f"| {i} | **{f['id']}** | {flag} | {q} | {exp} | {why} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Per-question detail")
    lines.append("")

    for i, f in enumerate(failures, 1):
        flag = " 🚨 SHOWSTOPPER" if f["showstopper"] else ""
        lines.append(f"### {i}. {f['id']}{flag}")
        lines.append("")
        lines.append(f"**Source:** {f['source']}")
        lines.append("")
        lines.append("**Question:**")
        lines.append("")
        lines.append("> " + f["question"].replace("\n", "\n> "))
        lines.append("")
        if f.get("expected"):
            lines.append("**Expected (per clinical editor):**")
            lines.append("")
            lines.append("> " + f["expected"].replace("\n", "\n> "))
            lines.append("")
        if f.get("negative"):
            lines.append("**Original negative feedback (what the prior chatbot did wrong):**")
            lines.append("")
            lines.append("> " + f["negative"][:1500].replace("\n", "\n> "))
            lines.append("")
        lines.append("**Auto-judge's flag reason:**")
        lines.append("")
        lines.append("> " + f["fail_reason"][:800].replace("\n", "\n> "))
        lines.append("")
        lines.append("**Chatbot's actual answer:**")
        lines.append("")
        ans = f["answer"]
        if ans:
            lines.append("> " + ans.replace("\n", "\n> "))
        else:
            lines.append("> *(no answer produced)*")
        lines.append("")
        lines.append("**Pharmacist verdict (please complete):**")
        lines.append("")
        lines.append("- [ ] Clinically OK — auto-judge over-strict")
        lines.append("- [ ] Acceptable with caveat: _________")
        lines.append("- [ ] Needs revision — specific issue: _________")
        lines.append("- [ ] Dangerous / patient-safety risk — specific issue: _________")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Notes for the pharmacist")
    lines.append("")
    lines.append("- The answers above were generated using the Canadian Pharmacist Association (CPS) Therapeutic Choices + Minor Ailments content under our existing private partnership. No external knowledge was used.")
    lines.append("- Each answer is what a licensed pharmacist would see if they asked this question via the production app today.")
    lines.append("- We're particularly interested in two categories of feedback:")
    lines.append("  1. **False failures** — the answer is actually clinically acceptable but our automated judge flagged it. We want to recalibrate.")
    lines.append("  2. **Real failures** — the answer is genuinely wrong or unsafe. We need to know *what specifically* the answer should have said.")
    lines.append("- After your review, we'll use your notes to: (a) update our test set's expected answers, (b) prioritize which failure classes to fix in the next iteration (tool use for dose calculations, prompt revisions, additional source content).")
    lines.append("- If you write the corrected expected answer for any of the failures, we can immediately convert it into a regression test so the same mistake never ships again.")
    lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"Wrote: {OUT}")
    print(f"  {len(failures)} failures included for review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
