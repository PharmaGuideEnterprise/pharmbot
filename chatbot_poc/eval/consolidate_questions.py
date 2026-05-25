#!/usr/bin/env python3
"""Consolidate ALL evaluation questions from the 4 CSVs in evaluation-questions/.

Output: chatbot_poc/eval/all_questions.json with structure:
[
  {
    "id": "CF-1",
    "source": "customer-feedback",
    "topic": "uti_pregnancy",
    "showstopper": True/False,
    "question": "...",
    "expected": "...",       # what the clinical professional expects
    "negative": "...",       # what they flagged as wrong
    "chapters": ["urinary_tract_infection"],
    "scorable": True,        # whether we can auto-score
  },
  ...
]

The clinical professional's NEGATIVE comments are ground truth — any "pass"
criterion is derived from "did we avoid the mistake they flagged?".
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

EVDIR = Path("/Users/emad/Code/cps/evaluation-questions")
OUT = Path("/Users/emad/Code/cps/chatbot_poc/eval/all_questions.json")

# Map topic keywords → CPS chapter slug(s). Used to derive which chapters
# need to be in the index for each question to be answerable.
TOPIC_TO_CHAPTERS = {
    # showstoppers
    "uti": ["urinary_tract_infection"],
    "diverticular": ["diverticular_disease"],
    "incontinence": ["urinary_incontinence_in_adults"],
    "oxybutynin": ["urinary_incontinence_in_adults"],
    "nausea": ["nausea_vomiting_pregnancy"],
    "diclectin": ["nausea_vomiting_pregnancy"],
    "meningitis": ["bacterial_meningitis"],
    "chemoprophylaxis": ["bacterial_meningitis"],
    "rhinosinusitis": ["sinusitis"],
    "sinusitis": ["sinusitis"],
    "duavive": ["menopause"],
    "menopause": ["menopause"],
    "vasomotor": ["menopause"],
    "infant colic": ["infant_colic"],  # minor_ailment PDF
    "constipation in a 7-month": ["constipation_in_children"],
    "constipation in a 7-month-old": ["constipation_in_children"],
    "infant constipation": ["constipation_in_children"],
    # additional topics
    "hypertension": ["hypertension"],
    "black": ["hypertension", "heart_failure"],   # H/F in Black pt, HTN in Black pt
    "heart failure": ["heart_failure"],
    "qt": ["ventricular_tachyarrhythmias"],
    "ms": ["multiple_sclerosis"],
    "multiple sclerosis": ["multiple_sclerosis"],
    "probiotics": ["multiple_sclerosis"],
    "cladribine": ["multiple_sclerosis"],
    "spms": ["multiple_sclerosis"],
    "gout": ["gout_and_hyperuricemia"],
    "otitis media": ["acute_otitis_media_in_childhood"],
    "amox": ["acute_otitis_media_in_childhood"],
    "azithromycin": ["acute_otitis_media_in_childhood"],
    "stable angina": ["stable_angina"],
    "diabetes": ["diabetes_mellitus"],
    "metformin": ["diabetes_mellitus"],
    "acute pain": ["acute_pain"],
    "tylenol": ["acute_pain"],
    "covid": ["covid19"],
    "paxlovid": ["covid19"],
    "lithium": ["bipolar_disorder"],
    "emergency contraception": ["contraception"],
    "ec contraception": ["contraception"],
    "breastfeeding": ["contraception"],  # for EC in breastfeeding
    "contraception": ["contraception"],
    "migraine": ["contraception", "headache_in_adults"],
    "warfarin": ["venous_thromboembolism"],
    "valacyclovir": ["herpesvirus_infections"],
    "cold sores": ["herpesvirus_infections"],
    "viral hepatitis": ["viral_hepatitis_acute"],
    "hepatitis": ["viral_hepatitis_acute"],
    "twinrix": ["routine_vaccinations"],
    "ozempic": ["diabetes_mellitus", "obesity"],
    "candesartan": ["hypertension"],
    "mpox": ["hiv_infection"],  # may not have mpox
    "monkey pox": ["hiv_infection"],
    "carbamazepine": ["seizures_and_epilepsy"],
    "allergic rhinitis": ["allergic_rhinitis"],
}


def slugify_topic(text: str) -> list[str]:
    """Heuristically map question text → chapter slugs."""
    low = text.lower()
    matched: set[str] = set()
    for kw, slugs in TOPIC_TO_CHAPTERS.items():
        if kw in low:
            for s in slugs:
                matched.add(s)
    return sorted(matched)


def parse_customer_feedback() -> list[dict]:
    """Parse customer-feedback.csv — 18 detailed clinical-editor questions."""
    out = []
    with open(EVDIR / "customer-feedback.csv", newline="") as f:
        rows = list(csv.reader(f))
    for r in rows[1:]:
        if len(r) < 8:
            continue
        qid_raw = r[0].strip()
        question = r[3].strip()
        expected = r[4].strip()
        pos = r[6].strip() if len(r) > 6 else ""
        neg = r[7].strip() if len(r) > 7 else ""
        showstopper = r[2].strip().upper().startswith("Y")
        if not question or not (expected or neg):
            continue
        out.append({
            "id": f"CF-{qid_raw}",
            "source": "customer-feedback.csv",
            "showstopper": showstopper,
            "question": question,
            "expected": expected,
            "positive": pos,
            "negative": neg,
            "chapters": slugify_topic(question + " " + expected),
        })
    return out


def parse_sample_questions() -> list[dict]:
    """Parse the patient-scenario MCQ-style sheet. Each row has a clinical
    scenario + multiple-choice question. The first column is the correct
    answer letter (or blank for context/follow-up turns)."""
    out = []
    with open(EVDIR / "Sample Questions - CPS Bot - Sheet1.csv", newline="") as f:
        rows = list(csv.reader(f))
    for i, r in enumerate(rows):
        if len(r) < 3:
            continue
        answer_letter = r[0].strip().lower()
        topic = r[1].strip()
        content = r[2].strip()
        if not content:
            continue
        # Skip pure context / follow-up turns (no MCQ structure)
        is_mcq = bool(re.search(r"\bA\)|\bB\)|\bC\)", content))
        out.append({
            "id": f"SQ-{i+1}",
            "source": "Sample Questions",
            "showstopper": False,
            "question": content,
            "expected": f"Answer: {answer_letter.upper()}" if answer_letter else "(open-ended)",
            "positive": "",
            "negative": "",
            "topic_tag": topic,
            "is_mcq": is_mcq,
            "mcq_answer": answer_letter if is_mcq else None,
            "chapters": slugify_topic(content + " " + topic),
        })
    return out


def parse_pharmachat_feedback() -> list[dict]:
    """CPS PharmaChat — form submissions with feedback about specific issues.

    The "Question Asked" column is often blank — the actual question is
    described inside the Detail column. For known cases we synthesize a
    clean test question from the feedback narrative so we test the real
    underlying clinical query, not just the page name.
    """
    # Curated overrides: synthesize the actual question being tested from the
    # feedback narrative. Keyed by (page, fragment-of-detail) — both must
    # match for the override to apply.
    OVERRIDES = [
        # PC-8: Hypertension page, candesartan + renal — the clinical Q is
        # "does candesartan require dosage adjustment in renal impairment?"
        ("Hypertension", "candesartan",
         "Does candesartan require dosage adjustment in patients with renal impairment?"),
        # PC-15: HIV chapter, mpox issue — the clinical Q is about mpox treatment
        ("HIV infection", "mpox",
         "What is the treatment for mpox?"),
        # PC-11: stable angina — the issue was confidently diagnosing angina
        # without considering other causes of chest pain
        ("stable angina", "multiple causes",
         "I have a patient with chest pain. What could the cause be?"),
        # PC-13: contraception with migraine
        ("Contraception CTC", "migraine",
         "Is combined hormonal contraception appropriate for a patient with migraine with aura?"),
        # PC-14: EC in breastfeeding
        ("Contraception (therapeutic choices)", "breastfeeding",
         "Can emergency contraception be used in a breastfeeding patient?"),
    ]

    out = []
    with open(EVDIR / "CPS PharmaChat Feedback Results - Form Submissions.csv", newline="") as f:
        rows = list(csv.reader(f))
    for i, r in enumerate(rows[1:], 1):
        if len(r) < 9:
            continue
        page = r[4].strip()
        severity = r[6].strip()
        question = r[7].strip() or (r[11].strip() if len(r) > 11 else "")
        detail = r[8].strip()
        if not question and not detail:
            continue

        # Apply override if the page + detail fragment match
        for ov_page, ov_frag, ov_q in OVERRIDES:
            if (ov_page.lower() in page.lower()
                and ov_frag.lower() in detail.lower()):
                question = ov_q
                break

        # Fallback: page name if still no question
        if not question and page:
            question = page
        if not question:
            continue
        out.append({
            "id": f"PC-{i}",
            "source": "CPS PharmaChat",
            "showstopper": severity.lower() == "high",
            "question": question,
            "expected": detail[:300],
            "positive": "",
            "negative": detail,
            "severity": severity,
            "chapters": slugify_topic(question + " " + detail),
        })
    return out


def parse_cpha_feedback() -> list[dict]:
    """CPhA Feedback — mostly bug reports, extract the ones that contain
    Q/A pairs or specific question complaints."""
    out = []
    with open(EVDIR / "CPhA Feedback 20240411.xlsx - CPhAFeedback.csv", newline="") as f:
        rows = list(csv.reader(f))
    for i, r in enumerate(rows):
        if len(r) < 3:
            continue
        feedback_on = r[0].strip()
        raised_by = r[1].strip()
        comments = r[2].strip()
        if "AI Chatbot" not in feedback_on or not comments:
            continue
        # Try to extract Q: ... A: ... pattern
        q_match = re.search(r"Q:\s*([^\n]+(?:\n(?!A:)[^\n]+)*)", comments)
        if q_match:
            question = q_match.group(1).strip()
            # Find the negative complaint after the answer
            negative = comments
            out.append({
                "id": f"CPHA-{i+1}",
                "source": "CPhA Feedback",
                "showstopper": False,
                "question": question,
                "expected": "(see full comment)",
                "positive": "",
                "negative": negative[:500],
                "chapters": slugify_topic(question + " " + comments),
            })
        else:
            # Pull questions from natural-language complaints
            # e.g. "lithium use in pregnancy", "emergency contraception in breastfeeding"
            topics = []
            for kw in ["lithium", "emergency contraception", "warfarin", "margarita pizza",
                       "CPS stands for"]:
                if kw.lower() in comments.lower():
                    topics.append(kw)
            if topics:
                for topic in topics:
                    # Synthesize a question if we can
                    if "margarita pizza" in topic.lower():
                        q = "How do I make a margarita pizza?"
                    elif "lithium" in topic.lower():
                        q = "What is the use of lithium in pregnancy?"
                    elif "emergency contraception" in topic.lower():
                        q = "Can emergency contraception be used in breastfeeding patients?"
                    elif "warfarin" in topic.lower():
                        q = "What are the drug interactions with warfarin?"
                    elif "CPS stands" in topic.lower():
                        q = "What does CPS stand for?"
                    else:
                        continue
                    out.append({
                        "id": f"CPHA-{i+1}-{topic.replace(' ', '_')}",
                        "source": "CPhA Feedback",
                        "showstopper": False,
                        "question": q,
                        "expected": "(see full comment)",
                        "positive": "",
                        "negative": comments[:500],
                        "chapters": slugify_topic(q + " " + comments),
                    })
    return out


def main() -> int:
    all_questions = []
    all_questions.extend(parse_customer_feedback())
    all_questions.extend(parse_sample_questions())
    all_questions.extend(parse_pharmachat_feedback())
    all_questions.extend(parse_cpha_feedback())

    OUT.write_text(json.dumps(all_questions, indent=2))

    # Summary
    by_source: dict[str, int] = {}
    chapters_needed: set[str] = set()
    no_chapter_mapped = 0
    for q in all_questions:
        by_source[q["source"]] = by_source.get(q["source"], 0) + 1
        for c in q["chapters"]:
            chapters_needed.add(c)
        if not q["chapters"]:
            no_chapter_mapped += 1

    print(f"Consolidated {len(all_questions)} questions:")
    for src, n in by_source.items():
        print(f"  {src}: {n}")
    print()
    print(f"Showstoppers (Y): {sum(1 for q in all_questions if q['showstopper'])}")
    print(f"No chapter mapped: {no_chapter_mapped}")
    print()
    print(f"Unique chapters needed ({len(chapters_needed)}):")
    for c in sorted(chapters_needed):
        print(f"  - {c}")
    print()
    print(f"Saved to: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
