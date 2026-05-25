#!/usr/bin/env python3
"""Ask a question set to the shim, then judge each answer with the LLM judge.

Generic — works for any JSON file with items having {id, question, expected,
negative, ...}. Output is a JSON with each item augmented by {answer, judge}.

Usage:
  python3 ask_and_judge.py --in chatbot_poc/eval/paraphrases.json \\
                           --out chatbot_poc/eval/paraphrases_judged.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Local import
sys.path.insert(0, str(Path(__file__).parent))
from llm_judge import judge as llm_judge_call  # type: ignore

SHIM = "http://localhost:3001"


def ask(question: str, use_agents: bool = False, use_agentic: bool = False,
        use_hybrid: bool = False, use_paraphrase: bool = False) -> tuple[str, dict | None]:
    """Returns (answer_text, specialist_meta_or_None)."""
    body = {
        "messages": [{"role": "user", "content": question}],
        "conversation_id": None,
        "stream": False,
    }
    url = f"{SHIM}/aoai/history/generate"
    if use_hybrid:
        url += "?hybrid=1&verify=0"
    elif use_agentic:
        url += "?agentic=1&verify=0"
    elif use_agents:
        url += "?use_agents=true"
    else:
        url += "?verify=" + ("1" if "--verify" in __import__("sys").argv else "0")
    if use_paraphrase:
        url += ("&" if "?" in url else "?") + "paraphrase=1"
    try:
        r = requests.post(
            url,
            headers={"Content-Type": "application/json", "Authorization": "Bearer eval"},
            json=body, timeout=300,
        )
    except Exception as e:
        return f"<ERROR: {type(e).__name__}: {e}>", None
    if r.status_code != 200:
        return f"<ERROR HTTP {r.status_code}: {r.text[:200]}>", None
    full = ""
    meta = None
    for line in r.text.strip().split("\n"):
        try:
            d = json.loads(line)
            if "specialist_meta" in d:
                meta = d["specialist_meta"]
            for ch in d.get("choices", []):
                for m in ch.get("messages", []):
                    if m.get("role") == "assistant" and m.get("content"):
                        full += m.get("content", "")
        except json.JSONDecodeError:
            continue
    return full, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input JSON file")
    ap.add_argument("--out", required=True, help="output JSON file")
    ap.add_argument("--skip-judge", action="store_true",
                    help="just ask, don't judge")
    ap.add_argument("--use-agents", action="store_true",
                    help="route through the specialist-agent system")
    ap.add_argument("--agentic", action="store_true",
                    help="use the agentic retrieval path (fetch_full_section tool)")
    ap.add_argument("--hybrid", action="store_true",
                    help="use the hybrid router (dose-class → agentic, else naive RAG)")
    ap.add_argument("--paraphrase", action="store_true",
                    help="enable paraphrase expansion on the agentic seed retrieval")
    args = ap.parse_args()

    items = json.loads(Path(args.inp).read_text())
    print(f"Asking {len(items)} questions (use_agents={args.use_agents}, agentic={args.agentic}, hybrid={args.hybrid}, paraphrase={args.paraphrase}), then judging…")
    out: list[dict] = []
    for i, it in enumerate(items, 1):
        qid = it["id"]
        print(f"  [{i:>3}/{len(items)}] {qid:<24}", end=" ", flush=True)
        meta = None
        try:
            answer, meta = ask(it["question"], use_agents=args.use_agents,
                               use_agentic=args.agentic, use_hybrid=args.hybrid,
                               use_paraphrase=args.paraphrase)
        except Exception as e:
            answer = f"<ERROR: {type(e).__name__}: {e}>"
        if answer.startswith("<ERROR"):
            print(f"ASK ERROR: {answer[:100]}")
            out.append({**it, "answer": answer, "specialist_meta": meta, "judge": None})
            continue
        if args.skip_judge:
            print(f"ASKED (len {len(answer)})")
            out.append({**it, "answer": answer, "specialist_meta": meta, "judge": None})
            continue
        try:
            v = llm_judge_call(
                it["question"], it.get("expected", ""), it.get("negative", ""), answer,
            )
        except Exception as e:
            print(f"JUDGE ERROR: {e}")
            out.append({**it, "answer": answer, "specialist_meta": meta, "judge": {
                "passed": None, "reasoning": f"judge error: {e}",
                "missing_expected": [], "violated_negative": [],
            }})
            continue
        mark = "PASS" if v.passed else "FAIL"
        spec = (meta or {}).get("agent", "onyx") if meta else "onyx"
        print(f"{mark}  [{spec}]  {v.reasoning[:70]}")
        out.append({**it, "answer": answer, "specialist_meta": meta, "judge": {
            "passed": v.passed, "reasoning": v.reasoning,
            "missing_expected": v.missing_expected,
            "violated_negative": v.violated_negative,
        }})
        time.sleep(0.4)

    Path(args.out).write_text(json.dumps(out, indent=2))

    # Summary
    scored = [r for r in out if r.get("judge") is not None and r["judge"].get("passed") is not None]
    passed = [r for r in scored if r["judge"]["passed"]]
    pct = 100 * len(passed) / len(scored) if scored else 0
    print(f"\n{len(passed)}/{len(scored)} = {pct:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
