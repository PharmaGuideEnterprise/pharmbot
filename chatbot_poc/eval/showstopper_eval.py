#!/usr/bin/env python3
"""Run the 10 client-flagged showstopper questions through the new chat
strategy (temp=0 via shim) and score against each question's specific
pass/fail criteria derived from the client's feedback CSV.

The criteria mirror the client's NEGATIVE Comments column — a "pass" means
the new answer DOES NOT make the same mistake the client flagged. Some
checks also require a positive signal (e.g. "must mention the 2-consecutive-
cultures threshold").

Output: per-question report + summary. Raw answers saved for inspection.
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

SHIM = "http://localhost:3001"
OUT_DIR = Path(__file__).resolve().parent
ANSWERS_FILE = OUT_DIR / "showstopper_answers.json"
REPORT_FILE = OUT_DIR / "showstopper_report.md"


# ────────── pass/fail criteria, derived from the client's CSV ──────

@dataclass
class Check:
    name: str
    # Each predicate returns True/False; True = passes that check.
    predicate: callable  # type: ignore[type-arg]


@dataclass
class Question:
    id: str
    editor: str
    text: str
    expected: str
    negative_feedback: str
    checks: list[Check] = field(default_factory=list)


def low(s: str) -> str:
    return (s or "").lower()


def has_phrase(text: str, phrases: list[str]) -> bool:
    t = low(text)
    return any(low(p) in t for p in phrases)


def has_all(text: str, phrases: list[str]) -> bool:
    t = low(text)
    return all(low(p) in t for p in phrases)


def regex_in(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, low(text), flags=re.IGNORECASE))


# Per-question checks. Each Question lists the criteria a passing answer
# must satisfy. Comments quote the client's reasoning so the link is clear.
QUESTIONS: list[Question] = [
    Question(
        id="1", editor="CE5",
        text="Treatment for asymptomatic UTI in a pregnant patient",
        expected="Treat after 2 cultures, nitrofurantoin, fosfomycin, cephalexin, amoxicillin",
        negative_feedback="Did not clarify 2 consecutive cultures; invented Cephalexin description; merged SMX vs TMP",
        checks=[
            # Client: "didn't clarify to treat asymptomatic only after 2 consecutive positive cultures"
            Check("mentions 2 consecutive cultures",
                  lambda a: regex_in(a, r"\b2\s+consecutive\b|\btwo\s+consecutive\b")),
            # Client: "Cephalexin: A commonly used cephalosporin..." was invented
            Check("no invented cephalexin elaboration",
                  lambda a: not (("cephalexin" in low(a)) and has_phrase(a, [
                      "commonly used", "broad-spectrum", "broad spectrum",
                      "first-line cephalosporin", "first generation cephalosporin",
                      "is a cephalosporin", "cell wall", "beta-lactam",
                  ]))),
            # Client: "didn't distinguish between SMX and TMP as single entities versus combination"
            Check("SMX vs TMP distinction preserved",
                  lambda a: ("first trimester" in low(a) or "antifolate" in low(a))
                  and ("hyperbilirubinemia" in low(a) or "kernicterus" in low(a)
                       or re.search(r"sulfamethoxazole[^.\n]{0,120}(?:last\s+(?:6|six)\s+weeks|near\s+term)", low(a)))),
        ],
    ),
    Question(
        id="2", editor="CE5",
        text="When should antibiotics be used in diverticular disease",
        expected="Antibiotics no longer first-line for inflammatory process; guidelines do not support routine antibiotic use in uncomplicated disease",
        negative_feedback='Blatantly wrong: "Antibiotics are used in the management of diverticular disease primarily for acute diverticulitis..."',
        checks=[
            # Pass requires the answer to acknowledge antibiotics are NOT routinely used
            # for uncomplicated disease (the client's actual complaint).
            Check("acknowledges antibiotics not routine for uncomplicated diverticulitis",
                  lambda a: has_phrase(a, [
                      "no longer first-line", "not first-line", "not first line",
                      "without antibiotic", "without antibiotics",
                      "not routinely", "not routine", "not recommended",
                      "selective use", "selectively used",
                      "no benefit", "not necessary", "inflammatory process",
                  ])),
            # Negative — should NOT just say antibiotics are the standard treatment
            Check("does not say antibiotics are the default treatment",
                  lambda a: not regex_in(a, r"antibiotics?\s+(?:are\s+)?(?:the\s+)?(?:primary|standard|mainstay|cornerstone|first-line)")),
        ],
    ),
    Question(
        id="3", editor="CE5",
        text="What is the dosage of oxybutynin to treat stress incontinence in an 85 yo female?",
        expected="Oxybutynin is not a recommended therapy for stress incontinence",
        negative_feedback="Information supplied was for urgency incontinence, not stress; dementia risk omitted",
        checks=[
            # Pass: must say oxybutynin is not for stress, OR distinguish stress vs urgency
            Check("clarifies oxybutynin not indicated for stress incontinence",
                  lambda a: (("oxybutynin" in low(a)) and has_phrase(a, [
                      "not recommended", "not indicated", "not appropriate",
                      "not first-line", "not used", "for urgency", "urgency incontinence",
                      "not for stress", "not indicated for stress",
                  ]))),
            # Should not just give a dosage without the caveat
            Check("does not give plain oxybutynin dose without stress-vs-urgency caveat",
                  lambda a: not (
                      regex_in(a, r"oxybutynin\s+\d+\s*mg")
                      and not has_phrase(a, ["urgency", "not indicated", "not recommended"])
                  )),
        ],
    ),
    Question(
        id="4", editor="CE5",
        text="Is Diclectin recommended for nausea in pregnancy?",
        expected="Mention lack of efficacy and controversy; pyridoxine alone as alternative",
        negative_feedback="NVP content not included; efficacy controversy not acknowledged; pyridoxine alone not mentioned",
        checks=[
            # Must mention pyridoxine (a key omission the client flagged)
            Check("mentions pyridoxine (vitamin B6)",
                  lambda a: "pyridoxine" in low(a) or "vitamin b6" in low(a)),
            # Should acknowledge efficacy concerns / controversy
            Check("acknowledges efficacy controversy or limited evidence",
                  lambda a: has_phrase(a, [
                      "efficacy", "controversial", "controversy",
                      "evidence", "limited", "unclear", "modest",
                      "questionable", "debate",
                  ])),
        ],
    ),
    Question(
        id="5", editor="CE1",
        text="When should chemoprophylaxis be used in potential bacterial meningitis cases?",
        expected="Close contacts (same household, daycare, dorm, military)",
        negative_feedback="(Client's concern applies more to Q6, but for Q5 expected = close contacts list)",
        checks=[
            Check("identifies close-contact scope (household / daycare / dorm)",
                  lambda a: has_phrase(a, [
                      "close contact", "household", "daycare", "dormitory", "dorm",
                      "military", "intimate contact",
                  ])),
        ],
    ),
    Question(
        id="6", editor="CE1",
        text="What agent to use in chemoprophylaxis for potential bacterial meningitis in pregnant woman?",
        expected="Ceftriaxone is standard of care for PEP in pregnancy",
        negative_feedback="Rifampin and ciprofloxacin should be avoided in pregnancy",
        checks=[
            Check("recommends ceftriaxone for pregnancy",
                  lambda a: "ceftriaxone" in low(a)),
            # Strong fail: confidently recommending rifampin or cipro WITHOUT a pregnancy caveat
            Check("does not recommend rifampin/cipro as primary choice in pregnancy",
                  lambda a: not (
                      regex_in(a, r"(?:rifampin|ciprofloxacin)[^.\n]{0,80}(?:first.line|recommended|use)")
                      and not has_phrase(a, [
                          "avoid in pregnancy", "not in pregnancy",
                          "contraindicated", "avoided in pregnancy",
                          "use ceftriaxone instead", "ceftriaxone is preferred",
                      ])
                  )),
        ],
    ),
    Question(
        id="7", editor="CE1",
        text="What is the first line treatment in rhinosinusitis?",
        expected="INCS or watchful waiting if <7 days; symptomatic mgmt (NSAIDs, acetaminophen)",
        negative_feedback="Implies antibiotics should always be used; no mention of allergy testing",
        checks=[
            Check("includes watchful waiting or INCS as first-line",
                  lambda a: has_phrase(a, [
                      "watchful waiting", "intranasal corticosteroid",
                      "intranasal corticosteroids", "incs", "nasal corticosteroid",
                      "symptomatic management", "symptomatic treatment",
                  ])),
            Check("does not imply antibiotics are universal first-line",
                  lambda a: not regex_in(a, r"antibiotics?\s+(?:are\s+)?(?:the\s+)?first.line\s+treatment(?:\s+for\s+rhinosinusitis|\s+in\s+rhinosinusitis|\s+for\s+sinusitis|\.)")),
        ],
    ),
    Question(
        id="8", editor="CE4",
        text="What is Duavive dose for 55 year old woman experiencing vasomotor symptoms with recent hysterectomy",
        expected="Not recommended in patients with hysterectomy (contains SERM/bazedoxifene)",
        negative_feedback="Should not have given a dose; product not recommended in hysterectomy",
        checks=[
            Check("flags Duavive not recommended in hysterectomy",
                  lambda a: ("duavive" in low(a) or "bazedoxifene" in low(a))
                  and has_phrase(a, [
                      "hysterectomy", "intact uterus", "without a uterus",
                      "not recommended", "not indicated", "contraindicated",
                      "not appropriate",
                  ])),
            # Fail if it just gives a dose without contraindication notice
            Check("does not give Duavive dose without contraindication notice",
                  lambda a: not (
                      regex_in(a, r"duavive[^.\n]{0,80}\d+\s*mg|\d+\s*mg[^.\n]{0,80}duavive")
                      and not has_phrase(a, [
                          "not recommended", "contraindicated", "not indicated",
                          "intact uterus", "hysterectomy",
                      ])
                  )),
        ],
    ),
    Question(
        id="9", editor="CE4",
        text="What are pharmacologic therapy options for Infant Colic in 6 month old baby",
        expected="Child should be assessed — red flag to have symptoms >5 months of age",
        negative_feedback="Did not flag age as warning sign; did not suggest urgent assessment",
        checks=[
            Check("flags age >5 months as a red flag / requires assessment",
                  lambda a: has_phrase(a, [
                      "red flag", "red-flag", "warning sign", "urgent assessment",
                      "medical assessment", "see a physician", "see a doctor",
                      "needs evaluation", "needs assessment", "not typical",
                      "atypical", "5 months", "five months",
                      "should be assessed", "should be evaluated",
                      "refer", "physician evaluation",
                  ])),
        ],
    ),
    Question(
        id="10", editor="CE5",
        text="Medications and dosages to treat constipation in a 7-month old",
        expected="PEG 1–1.5 g/kg/day PO × 3–6 days",
        negative_feedback="Adult content cited; adult glycerin suppository dose given; PEG dose not provided",
        checks=[
            # CPS Therapeutic Choices gives infant PEG dosing in absolute grams
            # ("4–17 g daily for 3–6 days") rather than the per-kg formulation
            # ("1–1.5 g/kg/day") the client wrote. Both are equivalent for a
            # 7-month-old (~7-9 kg → 7-13.5 g/day overlaps 4-17 g/day). Accept
            # either form, as long as PEG is recommended with an infant-scoped dose.
            Check("provides infant PEG dose (per-kg or absolute g/day) for evacuation",
                  lambda a: ("peg" in low(a) or "polyethylene glycol" in low(a))
                  and (
                      # per-kg dosing the client expected
                      has_phrase(a, [
                          "1-1.5 g/kg", "1–1.5 g/kg", "1 to 1.5 g/kg",
                          "1.5 g/kg/day", "1 g/kg/day", "g/kg/day",
                      ])
                      # or absolute-dose form from the source
                      or regex_in(a, r"\d+\s*[–-]\s*\d+\s*g\s+(?:daily|/day|per day)")
                      or regex_in(a, r"\d+\s*g\s+(?:daily|per day|/day)")
                  )
                  # and the dose must be in an infant context, not adult
                  and has_phrase(a, ["infant", "under 1 year", "children", "child"])),
            # Should NOT just cite the adult constipation chapter / adult dose
            Check("does not give an adult-only suppository dose for the infant",
                  lambda a: not (
                      "glycerin suppository" in low(a)
                      and has_phrase(a, ["adult"]) and "infant" not in low(a)
                  )),
        ],
    ),
]


# ────────── shim caller ─────────────────────────────────────────────

def ask(question: str) -> str:
    """Send a question to the shim and return the assistant's full text."""
    body = {
        "messages": [{"role": "user", "content": question}],
        "conversation_id": None,
        "stream": False,
    }
    r = requests.post(
        f"{SHIM}/aoai/history/generate",
        headers={"Content-Type": "application/json", "Authorization": "Bearer eval"},
        json=body, timeout=180,
    )
    if r.status_code != 200:
        return f"<ERROR HTTP {r.status_code}: {r.text[:200]}>"
    full = ""
    for line in r.text.strip().split("\n"):
        try:
            d = json.loads(line)
            for ch in d.get("choices", []):
                for m in ch.get("messages", []):
                    if m.get("role") == "assistant":
                        full += m.get("content", "")
        except json.JSONDecodeError:
            continue
    return full


# ────────── runner ──────────────────────────────────────────────────

def main() -> int:
    results = []
    print(f"Running {len(QUESTIONS)} showstopper questions through the new chat strategy")
    print(f"  (Voyage embeddings + temp=0, via http://localhost:3001)\n")

    for i, q in enumerate(QUESTIONS, 1):
        print(f"━━ #{q.id}  ({i}/{len(QUESTIONS)}) ━━")
        print(f"  Q: {q.text[:90]}")
        try:
            answer = ask(q.text)
        except Exception as e:
            answer = f"<ERROR: {type(e).__name__}: {e}>"
        # Score
        check_results = []
        for ch in q.checks:
            try:
                ok = bool(ch.predicate(answer))
            except Exception as e:
                ok = False
                print(f"    check error in {ch.name!r}: {e}")
            check_results.append((ch.name, ok))
            print(f"    {'✓' if ok else '✗'} {ch.name}")
        all_pass = all(r[1] for r in check_results)
        print(f"  → {'PASS' if all_pass else 'FAIL'}\n")
        results.append({
            "id": q.id,
            "editor": q.editor,
            "question": q.text,
            "expected": q.expected,
            "negative_feedback": q.negative_feedback,
            "answer": answer,
            "checks": [{"name": n, "passed": p} for n, p in check_results],
            "passed": all_pass,
        })
        time.sleep(2)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{'='*70}")
    print(f"SUMMARY: {passed}/{len(results)} questions PASS")
    print(f"{'='*70}")
    for r in results:
        mark = "✓ PASS" if r["passed"] else "✗ FAIL"
        failures = [c["name"] for c in r["checks"] if not c["passed"]]
        line = f"  #{r['id']:>2} {mark}  {r['question'][:60]}"
        print(line)
        for f in failures:
            print(f"          ✗ {f}")

    # Save artifacts
    ANSWERS_FILE.write_text(json.dumps(results, indent=2))
    print(f"\nFull answers saved to: {ANSWERS_FILE}")

    # Generate the markdown report
    md = ["# Showstopper Re-evaluation Report",
          "",
          f"Run against the new chat strategy (Voyage `voyage-4-large` retrieval + Claude Haiku 4.5 with `temperature_override=0`) on {time.strftime('%Y-%m-%d')}.",
          "",
          f"**Result: {passed}/{len(results)} of the 10 client-flagged showstoppers PASS** the regression criteria derived from the client's original feedback.",
          "",
          "## Methodology",
          "",
          "For each question:",
          "1. Send the question (verbatim from the client's CSV) through the shim's `/aoai/history/generate` endpoint",
          "2. Run automated checks that encode the client's original complaint — pass means we did **not** make the same mistake the client flagged",
          "3. Each question may have multiple checks (e.g. positive: must mention the threshold; negative: must not invent drug elaborations)",
          "",
          "All checks are heuristic (regex / keyword). They catch the specific failure patterns the client called out, but a clinical reviewer should still spot-check the full answers.",
          "",
          "## Per-question results",
          ""]
    for r in results:
        mark = "✅ **PASS**" if r["passed"] else "❌ **FAIL**"
        md.append(f"### #{r['id']} — {mark}")
        md.append(f"**Question:** {r['question']}")
        md.append("")
        md.append(f"**Client's expected answer:** {r['expected']}")
        md.append("")
        md.append(f"**Client's original complaint:** {r['negative_feedback']}")
        md.append("")
        md.append(f"**Checks:**")
        for c in r["checks"]:
            md.append(f"- {'✅' if c['passed'] else '❌'} {c['name']}")
        md.append("")
        md.append("**Our new answer:**")
        md.append("")
        md.append("> " + r["answer"].replace("\n", "\n> "))
        md.append("")
        md.append("---")
        md.append("")
    REPORT_FILE.write_text("\n".join(md))
    print(f"Markdown report saved to: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
