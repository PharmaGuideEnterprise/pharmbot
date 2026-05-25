#!/usr/bin/env python3
"""Eval harness for PharmBot (ChromaDB + Claude).

Reads eval/golden_set.jsonl, runs each question through local ChromaDB
retrieval + Claude, and scores on retrieval, keyword coverage, off-topic
refusal, and citation presence. Prints a summary scorecard and writes
per-question results to a timestamped JSONL file.

Usage:
    python eval/run_eval.py               # all 32 questions
    python eval/run_eval.py --limit 5     # quick smoke test
    python eval/run_eval.py --output /tmp/run.jsonl

Prerequisites:
    - chroma_db/ built: python index_docs.py
    - ANTHROPIC_API_KEY set in .env or environment
"""
from __future__ import annotations

import argparse
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

EVAL_DIR   = Path(__file__).resolve().parent
REPO_ROOT  = EVAL_DIR.parent
GOLDEN_PATH = EVAL_DIR / "golden_set.jsonl"
CHROMA_DIR  = str(REPO_ROOT / "chroma_db")
COLLECTION_NAME = "medical_docs"
TOP_K        = 8
MIN_RELEVANCE = 1.2
MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 1024

SYSTEM_PROMPT = """You are PharmBot, an AI assistant for licensed pharmacists.

Rules:
- Answer ONLY from the provided document excerpts. Do not use outside knowledge.
- If the excerpts do not contain enough information, say exactly: "I couldn't find this in the provided documents."
- Always mention the source document name when citing specific facts.
- Be precise: dosages, contraindications, and drug interactions must be quoted accurately.
- Use clear headings and bullet points for readability.
- Never guess or extrapolate drug information."""

REFUSAL_PATTERNS = [
    r"i can only answer",
    r"outside (my|the) scope",
    r"not able to (help|answer|assist)",
    r"i (can'?t|cannot) help with",
    r"only (handle|answer) (questions about )?(pharmacy|medical|clinical)",
    r"unable to (help|assist|answer) with",
    r"(this |writing \w+ )?(is|falls) outside",
    r"i'?m (designed|here) (to|only)",
    r"refuse",
    r"not (a |an )?(pharmacy|medical|clinical) question",
    r"couldn'?t find this in the provided documents",
    r"no (relevant |)information",
]
REFUSAL_RE = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)


def load_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = embedding_functions.DefaultEmbeddingFunction()
    try:
        return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception as e:
        sys.exit(
            f"[run_eval] Could not open ChromaDB collection '{COLLECTION_NAME}' at {CHROMA_DIR}.\n"
            f"  Run: python index_docs.py\n  Error: {e}"
        )


def retrieve(query: str, collection) -> list[dict]:
    results = collection.query(
        query_texts=[query],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )
    chunks: list[dict] = []
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
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[Excerpt {i} — {c['title']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def ask_claude(client: anthropic.Anthropic, question: str, context: str) -> str:
    user_msg = f"Context from pharmaceutical documents:\n\n{context}\n\n---\n\nQuestion: {question}"
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text if resp.content else ""


def query_pharmbot(
    client: anthropic.Anthropic,
    collection,
    question: str,
) -> dict:
    chunks = retrieve(question, collection)
    if not chunks:
        answer = "I couldn't find this in the provided documents."
    else:
        context = build_context(chunks)
        answer = ask_claude(client, question, context)
    return {"answer": answer, "chunks": chunks}


def score_question(q: dict, resp: dict) -> dict:
    answer = (resp.get("answer") or "").lower()
    chunks = resp.get("chunks") or []

    # Retrieval: does expected_chapter appear in any chunk's source path?
    expected_chapter = (q.get("expected_chapter") or "").lower()
    if expected_chapter:
        retrieval_hit = any(expected_chapter in c.get("source", "").lower() for c in chunks)
    else:
        retrieval_hit = None

    # Keyword coverage
    expected_kw = [k.lower() for k in (q.get("expected_keywords") or [])]
    if expected_kw:
        hits = sum(1 for k in expected_kw if k in answer)
        kw_coverage = hits / len(expected_kw)
    else:
        kw_coverage = None

    # Off-topic refusal
    is_off_topic = q.get("category") == "off-topic" or q.get("expected_refusal") is True
    refusal_correct = bool(REFUSAL_RE.search(answer)) if is_off_topic else None

    # Citation presence (any chunk was retrieved and cited)
    must_cite = bool(q.get("must_cite"))
    citation_present = (len(chunks) > 0) if must_cite else None

    return {
        "retrieval_hit":    retrieval_hit,
        "keyword_coverage": kw_coverage,
        "refusal_correct":  refusal_correct,
        "citation_present": citation_present,
    }


def load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        sys.exit(f"[run_eval] {GOLDEN_PATH} not found.")
    rows: list[dict] = []
    for raw in GOLDEN_PATH.read_text().splitlines():
        line = raw.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def summarize(results: list[dict]) -> None:
    total = len(results)
    retrieval_ev  = [r for r in results if r["scores"]["retrieval_hit"] is not None]
    retrieval_ok  = sum(1 for r in retrieval_ev if r["scores"]["retrieval_hit"])
    kw_scored     = [r for r in results if r["scores"]["keyword_coverage"] is not None]
    avg_kw        = sum(r["scores"]["keyword_coverage"] for r in kw_scored) / len(kw_scored) if kw_scored else 0.0
    refusal_ev    = [r for r in results if r["scores"]["refusal_correct"] is not None]
    refusal_ok    = sum(1 for r in refusal_ev if r["scores"]["refusal_correct"])
    cite_ev       = [r for r in results if r["scores"]["citation_present"] is not None]
    cite_ok       = sum(1 for r in cite_ev if r["scores"]["citation_present"])
    errors        = sum(1 for r in results if r.get("error"))

    def pct(num: int, denom: int) -> str:
        return f"{(100.0 * num / denom):.1f}%" if denom else "n/a"

    print()
    print("=" * 64)
    print("  PharmBot — Eval Scorecard")
    print("=" * 64)
    print(f"  Total questions:        {total}")
    print(f"  Errors (request fail):  {errors}")
    print(f"  Retrieval correct:      {pct(retrieval_ok, len(retrieval_ev))}  ({retrieval_ok}/{len(retrieval_ev)})")
    print(f"  Avg keyword coverage:   {avg_kw:.2f}  (n={len(kw_scored)})")
    print(f"  Off-topic refusals OK:  {pct(refusal_ok, len(refusal_ev))}  ({refusal_ok}/{len(refusal_ev)})")
    print(f"  Citation present:       {pct(cite_ok, len(cite_ev))}  ({cite_ok}/{len(cite_ev)})")
    print("=" * 64)

    # Regression bars (v1 POC)
    print()
    print("  Regression bars (v1):")
    bars = [
        ("Retrieval ≥ 70%",    retrieval_ev, retrieval_ok / len(retrieval_ev) if retrieval_ev else None, 0.70),
        ("Keyword cov ≥ 0.50", kw_scored,    avg_kw if kw_scored else None,                             0.50),
        ("Refusal ≥ 90%",      refusal_ev,   refusal_ok / len(refusal_ev) if refusal_ev else None,      0.90),
        ("Citation 100%",      cite_ev,      cite_ok / len(cite_ev) if cite_ev else None,               1.00),
    ]
    for label, evaluated, val, threshold in bars:
        if val is None:
            print(f"    [ n/a] {label}  (no questions evaluated)")
        else:
            status = "PASS" if val >= threshold else "FAIL"
            print(f"    [{status}] {label}  (got {val:.1%})")
    print("=" * 64)


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    ap = argparse.ArgumentParser(description="Run the PharmBot eval harness.")
    ap.add_argument("--limit",  type=int, default=None, help="Run only the first N questions.")
    ap.add_argument("--output", type=str, default=None, help="Override results JSONL output path.")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit("[run_eval] ANTHROPIC_API_KEY missing — add it to .env or the environment.")

    collection    = load_collection()
    anthropic_client = anthropic.Anthropic(api_key=api_key)

    golden = load_golden()
    if args.limit:
        golden = golden[: args.limit]

    ts       = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.output) if args.output else EVAL_DIR / f"results_{ts}.jsonl"

    results: list[dict] = []
    with out_path.open("w") as out_f:
        for i, q in enumerate(golden, 1):
            print(f"[{i}/{len(golden)}] {q['id']} :: {q['question'][:80]}")
            t0 = time.time()
            try:
                resp = query_pharmbot(anthropic_client, collection, q["question"])
                error = None
            except Exception as e:
                resp  = {"answer": "", "chunks": []}
                error = f"exception: {e}"

            elapsed = time.time() - t0
            scores  = score_question(q, resp)
            row = {
                "id":               q["id"],
                "question":         q["question"],
                "category":         q.get("category"),
                "expected_chapter": q.get("expected_chapter"),
                "answer":           resp.get("answer", ""),
                "chunks_retrieved": len(resp.get("chunks") or []),
                "top3_sources":     [c["source"] for c in (resp.get("chunks") or [])[:3]],
                "scores":           scores,
                "elapsed_s":        round(elapsed, 2),
                "error":            error,
            }
            results.append(row)
            out_f.write(json.dumps(row) + "\n")
            out_f.flush()

    print(f"\n[run_eval] Per-question results written to: {out_path}")
    summarize(results)


if __name__ == "__main__":
    main()
