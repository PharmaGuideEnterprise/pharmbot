#!/usr/bin/env python3
"""CSV Q&A eval harness for PharmBot.

Reads eval/csv_questions.csv, runs each question through PharmBot (ChromaDB +
Claude), then uses a Claude judge to compare the bot answer against the
expected answer. Outputs a scored JSONL file and a summary scorecard.

Usage:
    /usr/bin/python3 eval/run_csv_eval.py --csv eval/csv_questions.csv
    /usr/bin/python3 eval/run_csv_eval.py --csv eval/csv_questions.csv --limit 5
    python eval/run_csv_eval.py
    python eval/run_csv_eval.py --limit 5
    python eval/run_csv_eval.py --csv path/to/other.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

EVAL_DIR        = Path(__file__).resolve().parent
REPO_ROOT       = EVAL_DIR.parent
CHROMA_DIR      = str(REPO_ROOT / "chroma_db")
COLLECTION_NAME = "medical_docs"
TOP_K           = 8
MIN_RELEVANCE   = 1.2
MODEL           = "claude-sonnet-4-6"
MAX_TOKENS      = 1024

SYSTEM_PROMPT = """You are PharmBot, an AI assistant for licensed pharmacists.

Rules:
- Answer ONLY from the provided document excerpts. Do not use outside knowledge.
- If the excerpts do not contain enough information, say exactly: "I couldn't find this in the provided documents."
- Always mention the source document name when citing specific facts.
- Be precise: dosages, contraindications, and drug interactions must be quoted accurately.
- Use clear headings and bullet points for readability.
- Never guess or extrapolate drug information."""

JUDGE_SYSTEM = """You are an expert clinical pharmacist evaluating an AI assistant's answer.

Compare the bot's response to the expected answer and assign one of these scores:
- PASS    : Bot's answer is clinically correct and covers the key point(s) in the expected answer.
- PARTIAL : Bot's answer is partially correct but misses important clinical details or is vague.
- FAIL    : Bot's answer is incorrect, contradicts the expected answer, or states it cannot find the information when it should be able to.

Be strict about clinical accuracy: drug names, dosages, and key clinical decisions must be correct.
Respond ONLY with valid JSON matching this schema exactly — no extra text:
{"score": "PASS"|"PARTIAL"|"FAIL", "reason": "<1-2 sentence explanation>", "key_miss": "<what was missing/wrong, or null>"}"""


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def load_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = embedding_functions.DefaultEmbeddingFunction()
    try:
        return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception as e:
        sys.exit(
            f"[csv_eval] Cannot open ChromaDB collection at {CHROMA_DIR}.\n"
            f"  Run: python index_docs.py\n  Error: {e}"
        )


def retrieve(query: str, collection) -> list[dict]:
    results = collection.query(
        query_texts=[query],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist < MIN_RELEVANCE:
            chunks.append({
                "text":   doc,
                "title":  meta.get("title", ""),
                "source": meta.get("source", ""),
                "dist":   dist,
            })
    return chunks


def build_context(chunks: list[dict]) -> str:
    parts = [f"[Excerpt {i} — {c['title']}]\n{c['text']}" for i, c in enumerate(chunks, 1)]
    return "\n\n---\n\n".join(parts)


# ── PharmBot call ─────────────────────────────────────────────────────────────

def ask_pharmbot(client: anthropic.Anthropic, collection, question: str) -> tuple[str, list[dict]]:
    chunks = retrieve(question, collection)
    if not chunks:
        return "I couldn't find this in the provided documents.", []
    context = build_context(chunks)
    user_msg = f"Context from pharmaceutical documents:\n\n{context}\n\n---\n\nQuestion: {question}"
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return (resp.content[0].text if resp.content else ""), chunks


# ── Judge ─────────────────────────────────────────────────────────────────────

def judge(client: anthropic.Anthropic, question: str, bot_answer: str, expected: str) -> dict:
    prompt = (
        f"Question: {question}\n\n"
        f"Expected answer: {expected}\n\n"
        f"Bot answer: {bot_answer}"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text if resp.content else ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {"score": "ERROR", "reason": f"Judge parse error: {raw[:120]}", "key_miss": None}


# ── MCQ helpers ───────────────────────────────────────────────────────────────

def is_mcq_letter(answer: str) -> bool:
    return answer.strip().lower() in ("a", "b", "c")


def resolve_mcq(question: str, letter: str) -> str:
    """Return the full text of the MCQ option matching the given letter."""
    target = letter.strip().upper()
    # Split question text on option markers A) B) C)
    parts = re.split(r"(?<!\w)(?=[A-C]\))", question)
    for part in parts:
        if part.startswith(f"{target})"):
            text = part[2:].strip()
            # Strip trailing "Give me the answer..." prompt
            text = re.sub(r"\s*Give me the answer.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
            return text.strip()
    return letter  # fallback: return the letter unchanged


# ── CSV loader ────────────────────────────────────────────────────────────────

_SKIP_PATTERNS = re.compile(
    r"^(where did it come from|user should|resolved with|n/?a)$",
    re.IGNORECASE,
)


def load_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            q = row.get("question", "").strip()
            a = row.get("answer", "").strip()
            if not q or not a or _SKIP_PATTERNS.match(a):
                continue
            rows.append({
                "question": q,
                "raw_answer": a,
                "category": row.get("category", "").strip(),
                "source": row.get("source", "").strip(),
            })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def summarize(results: list[dict]) -> None:
    total   = len(results)
    counts  = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "ERROR": 0}
    for r in results:
        counts[r["judgment"].get("score", "ERROR")] += 1

    print()
    print("=" * 64)
    print("  PharmBot — CSV Eval Scorecard")
    print("=" * 64)
    print(f"  Total questions : {total}")
    for label, n in counts.items():
        if n or label != "ERROR":
            bar = "#" * n + "-" * (total - n)
            print(f"  {label:<8}        : {n:>3}  ({100*n/total:4.1f}%)  [{bar}]")
    print()

    # By category
    cats: dict[str, list[str]] = {}
    for r in results:
        cats.setdefault(r["category"] or "unknown", []).append(
            r["judgment"].get("score", "ERROR")
        )
    print("  By category:")
    for cat, scores in sorted(cats.items()):
        p = scores.count("PASS")
        t = len(scores)
        print(f"    {cat:<35} {p}/{t} PASS")

    print()
    # Regression bar
    pass_rate = counts["PASS"] / total if total else 0
    status = "PASS" if pass_rate >= 0.60 else "FAIL"
    print(f"  Regression bar (≥ 60% PASS): [{status}]  got {pass_rate:.1%}")
    print("=" * 64)

    # Failures detail
    failures = [r for r in results if r["judgment"].get("score") in ("FAIL", "PARTIAL")]
    if failures:
        print(f"\n  Questions that need attention ({len(failures)}):")
        for r in failures:
            sc = r["judgment"].get("score")
            reason = r["judgment"].get("reason", "")
            miss   = r["judgment"].get("key_miss") or ""
            q_short = r["question"][:80].replace("\n", " ")
            print(f"\n  [{sc}] {q_short}...")
            print(f"        Reason : {reason}")
            if miss:
                print(f"        Missing: {miss}")
    print()


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    ap = argparse.ArgumentParser(description="Run CSV-based PharmBot eval.")
    ap.add_argument("--csv",   default=str(EVAL_DIR / "csv_questions.csv"), help="Path to Q&A CSV.")
    ap.add_argument("--limit", type=int, default=None, help="Run only first N questions.")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit("[csv_eval] ANTHROPIC_API_KEY missing — add it to .env or environment.")

    csv_path = Path(args.csv)
    if not csv_path.exists():
        sys.exit(f"[csv_eval] CSV not found: {csv_path}")

    questions = load_csv(csv_path)
    if args.limit:
        questions = questions[: args.limit]
    print(f"[csv_eval] {len(questions)} questions loaded from {csv_path.name}")

    collection       = load_collection()
    anthropic_client = anthropic.Anthropic(api_key=api_key)

    ts       = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = EVAL_DIR / f"csv_results_{ts}.jsonl"

    results: list[dict] = []
    with out_path.open("w") as out_f:
        for i, q in enumerate(questions, 1):
            question   = q["question"]
            raw_answer = q["raw_answer"]

            if is_mcq_letter(raw_answer):
                expected      = resolve_mcq(question, raw_answer)
                question_type = "mcq"
            else:
                expected      = raw_answer
                question_type = "open"

            print(f"[{i:>2}/{len(questions)}] ({question_type}) {question[:75]}...")

            t0 = time.time()
            try:
                bot_answer, chunks = ask_pharmbot(anthropic_client, collection, question)
                judgment           = judge(anthropic_client, question, bot_answer, expected)
                error              = None
            except Exception as e:
                bot_answer = ""
                chunks     = []
                judgment   = {"score": "ERROR", "reason": str(e), "key_miss": None}
                error      = str(e)

            elapsed = time.time() - t0
            score   = judgment.get("score", "ERROR")
            print(f"         -> {score}  |  {judgment.get('reason', '')[:70]}")

            row = {
                "id":               f"CSV{i:03d}",
                "question":         question,
                "category":         q["category"],
                "question_type":    question_type,
                "expected_answer":  expected,
                "bot_answer":       bot_answer,
                "chunks_retrieved": len(chunks),
                "top3_sources":     [c["source"] for c in chunks[:3]],
                "judgment":         judgment,
                "elapsed_s":        round(elapsed, 2),
                "error":            error,
            }
            results.append(row)
            out_f.write(json.dumps(row) + "\n")
            out_f.flush()

    print(f"\n[csv_eval] Results written to: {out_path}")
    summarize(results)


if __name__ == "__main__":
    main()
