#!/usr/bin/env python3
"""Minimal eval harness for the CPS Pharmacy Chatbot POC.

Reads golden_set.jsonl, hits Onyx's chat API for each question, and scores
the response on retrieval (citation chapter match), keyword coverage,
off-topic refusal correctness, and citation presence. Prints a summary
scorecard and writes per-question results to a timestamped JSONL file.
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

import requests

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
ENV_PATH = REPO_ROOT / ".env"
GOLDEN_PATH = EVAL_DIR / "golden_set.jsonl"

ONYX_BASE = os.environ.get("ONYX_BASE_URL", "http://localhost:8080")
HEALTH_PATH = "/api/health"

REFUSAL_PATTERNS = [
    r"i can only answer",
    r"outside (my|the) scope",
    r"not able to (help|answer|assist)",
    r"i (can'?t|cannot) help with",
    r"only (handle|answer) (questions about )?(pharmacy|medical|clinical)",
    r"unable to (help|assist|answer) with",
    r"this (is|falls) outside",
    r"i'?m (designed|here) (to|only)",
    r"refuse",
    r"not (a |an )?(pharmacy|medical|clinical) question",
]
REFUSAL_RE = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if k.startswith("ONYX_") or k in ("ANTHROPIC_API_KEY",):
            values[k] = v
    return values


def fail_fast_if_unreachable() -> None:
    try:
        r = requests.get(f"{ONYX_BASE}{HEALTH_PATH}", timeout=5)
        if r.status_code >= 500:
            raise RuntimeError(f"health check returned {r.status_code}")
    except Exception as e:
        sys.exit(
            f"[run_eval] Onyx API at {ONYX_BASE} is not reachable ({e}) — "
            f"run bootstrap.sh first."
        )


def login(env: dict[str, str]) -> requests.Session:
    s = requests.Session()
    email = env.get("ONYX_ADMIN_EMAIL", "").strip()
    password = env.get("ONYX_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        sys.exit("[run_eval] ONYX_ADMIN_EMAIL / ONYX_ADMIN_PASSWORD missing in .env.")
    r = s.post(
        f"{ONYX_BASE}/api/auth/login",
        data={"username": email, "password": password},
        timeout=15,
    )
    if r.status_code != 200:
        sys.exit(f"[run_eval] Onyx login failed ({r.status_code}): {r.text[:200]}")
    token = r.json().get("access_token") if r.headers.get("content-type", "").startswith("application/json") else None
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def send_chat(session: requests.Session, question: str) -> dict:
    # TODO: verify endpoint — Onyx has used /api/chat/send-message and /api/chat/create-chat-session+send-message across versions.
    create = session.post(
        f"{ONYX_BASE}/api/chat/create-chat-session",
        json={"persona_id": 0, "description": "eval"},
        timeout=30,
    )
    chat_session_id = None
    if create.status_code in (200, 201):
        try:
            chat_session_id = create.json().get("chat_session_id") or create.json().get("id")
        except Exception:
            chat_session_id = None

    payload = {
        "chat_session_id": chat_session_id,
        "message": question,
        "parent_message_id": None,
        "prompt_id": None,
        "search_doc_ids": None,
        "retrieval_options": {"run_search": "auto", "real_time": True},
    }
    r = session.post(
        f"{ONYX_BASE}/api/chat/send-message",
        json=payload,
        timeout=120,
        stream=True,
    )
    if r.status_code != 200:
        return {"error": f"send-message {r.status_code}: {r.text[:200]}", "answer": "", "citations": []}

    answer_parts: list[str] = []
    citations: list[dict] = []
    for raw_line in r.iter_lines():
        if not raw_line:
            continue
        try:
            obj = json.loads(raw_line.decode("utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict):
            if isinstance(obj.get("answer_piece"), str):
                answer_parts.append(obj["answer_piece"])
            if isinstance(obj.get("message"), str) and not answer_parts:
                answer_parts.append(obj["message"])
            for key in ("citations", "context_docs", "top_documents"):
                val = obj.get(key)
                if isinstance(val, list):
                    citations.extend(val)
                elif isinstance(val, dict) and isinstance(val.get("top_documents"), list):
                    citations.extend(val["top_documents"])
    return {"answer": "".join(answer_parts), "citations": citations}


def score_question(q: dict, resp: dict) -> dict:
    answer = (resp.get("answer") or "").lower()
    citations = resp.get("citations") or []

    citation_blob = json.dumps(citations).lower()
    expected_chapter = (q.get("expected_chapter") or "").lower()
    retrieval_hit = bool(expected_chapter and expected_chapter in citation_blob)

    expected_kw = [k.lower() for k in q.get("expected_keywords") or []]
    if expected_kw:
        hits = sum(1 for k in expected_kw if k in answer)
        kw_coverage = hits / len(expected_kw)
    else:
        kw_coverage = None

    is_off_topic = q.get("category") == "off-topic" or q.get("expected_refusal") is True
    refusal_correct = None
    if is_off_topic:
        refusal_correct = bool(REFUSAL_RE.search(answer))

    must_cite = bool(q.get("must_cite"))
    citation_present = None
    if must_cite:
        citation_present = len(citations) > 0

    return {
        "retrieval_hit": retrieval_hit if expected_chapter else None,
        "keyword_coverage": kw_coverage,
        "refusal_correct": refusal_correct,
        "citation_present": citation_present,
    }


def load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        sys.exit(f"[run_eval] {GOLDEN_PATH} not found.")
    rows: list[dict] = []
    for raw in GOLDEN_PATH.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def summarize(results: list[dict]) -> None:
    total = len(results)
    retrieval_evaluated = [r for r in results if r["scores"]["retrieval_hit"] is not None]
    retrieval_hits = sum(1 for r in retrieval_evaluated if r["scores"]["retrieval_hit"])
    kw_scored = [r for r in results if r["scores"]["keyword_coverage"] is not None]
    avg_kw = sum(r["scores"]["keyword_coverage"] for r in kw_scored) / len(kw_scored) if kw_scored else 0.0
    refusal_evaluated = [r for r in results if r["scores"]["refusal_correct"] is not None]
    refusal_hits = sum(1 for r in refusal_evaluated if r["scores"]["refusal_correct"])
    cite_evaluated = [r for r in results if r["scores"]["citation_present"] is not None]
    cite_hits = sum(1 for r in cite_evaluated if r["scores"]["citation_present"])
    errors = sum(1 for r in results if r.get("error"))

    def pct(num: int, denom: int) -> str:
        return f"{(100.0 * num / denom):.1f}%" if denom else "n/a"

    print()
    print("=" * 64)
    print(f" CPS Pharmacy Chatbot — Eval Scorecard")
    print("=" * 64)
    print(f" Total questions:        {total}")
    print(f" Errors (request fail):  {errors}")
    print(f" Retrieval correct:      {pct(retrieval_hits, len(retrieval_evaluated))}  ({retrieval_hits}/{len(retrieval_evaluated)})")
    print(f" Avg keyword coverage:   {avg_kw:.2f}  (n={len(kw_scored)})")
    print(f" Off-topic refusals OK:  {pct(refusal_hits, len(refusal_evaluated))}  ({refusal_hits}/{len(refusal_evaluated)})")
    print(f" Citation present:       {pct(cite_hits, len(cite_evaluated))}  ({cite_hits}/{len(cite_evaluated)})")
    print("=" * 64)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the CPS chatbot eval against a running Onyx instance.")
    ap.add_argument("--limit", type=int, default=None, help="Only run the first N questions (smoke test).")
    ap.add_argument("--output", type=str, default=None, help="Override the results JSONL output path.")
    args = ap.parse_args()

    fail_fast_if_unreachable()
    env = load_env()
    session = login(env)

    golden = load_golden()
    if args.limit:
        golden = golden[: args.limit]

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.output) if args.output else EVAL_DIR / f"results_{ts}.jsonl"

    results: list[dict] = []
    with out_path.open("w") as out_f:
        for i, q in enumerate(golden, 1):
            print(f"[{i}/{len(golden)}] {q['id']} :: {q['question'][:80]}")
            t0 = time.time()
            try:
                resp = send_chat(session, q["question"])
            except Exception as e:
                resp = {"error": f"exception: {e}", "answer": "", "citations": []}
            elapsed = time.time() - t0
            scores = score_question(q, resp)
            row = {
                "id": q["id"],
                "question": q["question"],
                "category": q.get("category"),
                "expected_chapter": q.get("expected_chapter"),
                "answer": resp.get("answer", ""),
                "citations_count": len(resp.get("citations") or []),
                "citations_preview": (resp.get("citations") or [])[:3],
                "scores": scores,
                "elapsed_s": round(elapsed, 2),
                "error": resp.get("error"),
            }
            results.append(row)
            out_f.write(json.dumps(row) + "\n")
            out_f.flush()

    print(f"\n[run_eval] Per-question results written to: {out_path}")
    summarize(results)


if __name__ == "__main__":
    main()
