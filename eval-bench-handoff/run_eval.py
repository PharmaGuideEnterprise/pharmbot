"""CPS pharmacy chatbot benchmark — runner for an external POC.

Plug your chatbot's `ask(question) -> str` function in (the `def ask` stub
below). Run this script and it will:

  1. Load the 102 raw questions, apply the 17 NA exclusions → 85 scoreable.
  2. For each scoreable question, call your chatbot 3 times.
  3. Run the LLM judge (judge.py) on each trial.
  4. Majority-vote (>=2/3 = PASS) per question.
  5. Print per-prefix totals + total /85 and write a results JSON.

Compare your totals to reference_results.json (our latest S8 = 75/85 = 88.2%).

Usage
-----
    export ANTHROPIC_API_KEY=sk-ant-...        # for the judge
    # edit `ask()` below to call YOUR chatbot
    python run_eval.py --out my_results.json
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pharmbot_retrieval import retrieve_hybrid  # noqa: E402

# ====================================================================== #
# STEP 1 — PharmBot pipeline (ChromaDB + DeepSeek, OpenAI-compatible).    #
# ====================================================================== #
import os

_TOP_K            = 35
_MIN_RELEVANCE    = 1.5
# Mirrors app.py — confirm the exact model id in DeepSeek's docs.
_MODEL            = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_SYSTEM_PROMPT = """You are PharmBot, an AI assistant for licensed pharmacists. You answer from provided CPS/CPhA document excerpts.

GROUNDING (most important):
- Use ONLY facts that appear in the excerpts. Never add a drug name, dose, frequency, threshold, indication, or mechanism that is not written in an excerpt — not even if it is "well known." If you find yourself writing a clinical fact you cannot point to in an excerpt, delete it.
- When you state a fact, name the source document it came from.
- Do NOT pad an answer with general background. Extra unsourced detail is the most common error and will be treated as a mistake.

ENGAGE — do not over-refuse:
- If ANY excerpt is relevant to the question, ANSWER from it. Give the grounded partial answer and then explicitly note what the excerpts do NOT cover. A bare "I couldn't find this" is WRONG whenever relevant excerpts were retrieved.
- Treat brand/generic and close product-name variants as the same item (e.g. "OneTouch Ultra2" ↔ "OneTouch Ultra"; "Atacand" ↔ "candesartan"). If a table row matches the product family, use it.
- Only output "I couldn't find this in the provided documents." when NONE of the excerpts bear on the question.
- A clinical-pharmacy question that names a real drug/device/condition is ALWAYS in scope. Only reply "I can only assist with clinical pharmacy questions." for genuinely non-clinical topics (travel, recipes, lifestyle). When unsure, treat it as in scope and answer.
- Do NOT reframe a genuinely off-topic question (travel itineraries, food/restaurant recommendations, recipes, general lifestyle) into a clinical one in order to answer it. Decline cleanly with the scope line and stop — do not append clinical "however" advice.

HONEST GAPS:
- If the excerpts address the general topic but not the specific sub-scenario asked (exact dose, specific population), say what IS in the excerpts and state plainly that the specific detail is not present. Do not invent the missing value.

STYLE:
- Be precise with dosages, contraindications, interactions — quote them as written.
- Use headings and bullets.
- When asked for THE first-line therapy, commit to the single guideline-preferred agent named in the excerpts. Do not split the answer across severity tiers (e.g. mild vs moderate) unless the question itself specifies severity.
- For multiple-choice, commit to the single best answer supported by the source; do not add defensible-but-extra options unless the question asks for all that apply.
- If a therapy is not recommended or contraindicated for the patient's scenario, say that first and do not provide a dose as though it should be used.
- For vague diagnostic questions, explicitly state that you cannot diagnose from the available information and that more patient-specific assessment is needed before listing possible causes.
- For medication review in older adults, explicitly assess anticholinergic burden, sedating drugs, renal clearance, drug interactions, deprescribing opportunities, collaboration with the prescriber, and Beers Criteria when relevant.
- For QT-prolonging medications, discuss patient risk factors, medication-risk mitigation, ECG/electrolyte monitoring, and external QT-risk resources such as CredibleMeds if supported by the excerpt."""

_pharmbot_collection = None
_pharmbot_client     = None


def _init_pharmbot():
    global _pharmbot_collection, _pharmbot_client
    if _pharmbot_client is not None:
        return
    from openai import OpenAI
    import chromadb
    from chromadb.utils import embedding_functions
    try:
        from dotenv import load_dotenv
        load_dotenv(HERE.parent / ".env")
    except ImportError:
        pass
    _pharmbot_client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=_DEEPSEEK_BASE_URL,
    )
    ef     = embedding_functions.DefaultEmbeddingFunction()
    chroma = chromadb.PersistentClient(path=str(HERE.parent / "chroma_db"))
    _pharmbot_collection = chroma.get_collection(
        name="medical_docs", embedding_function=ef)


def ask(question: str) -> str:
    _init_pharmbot()
    chunks, _sources = retrieve_hybrid(
        question,
        _pharmbot_collection,
        top_k=_TOP_K,
        min_relevance=_MIN_RELEVANCE,
        keyword_k=14,
        final_k=35,
    )
    if not chunks:
        return "I couldn't find this in the provided documents."
    context = "\n\n---\n\n".join(
        f"[Excerpt {i} — {c['title']}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    user_msg = (f"Context from pharmaceutical documents:\n\n{context}"
                f"\n\n---\n\nQuestion: {question}")
    resp = _pharmbot_client.chat.completions.create(
        model=_MODEL, max_tokens=1024,
        temperature=0.0,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp.choices[0].message.content or ""


# ====================================================================== #
# Everything below is the harness — you should not need to edit it.       #
# ====================================================================== #
HERE = Path(__file__).parent
QDIR = HERE / "questions"
PREFIXES = ["CF", "CPHA", "NQ", "PC", "SQ", "T2"]


def load_questions() -> tuple[list[dict], set[str]]:
    """Load all 102 raw questions + the NA exclusion set (17 qids)."""
    items: list[dict] = []
    for fn in ("all_questions.json", "new_questions.json",
               "tier2_targeted_questions.json"):
        items += json.loads((QDIR / fn).read_text())
    na_data = json.loads((HERE / "na_exclusions.json").read_text())
    na = set(na_data["pre_na"].keys()) | set(na_data["reclassify_na"].keys())
    return items, na


def majority(trials: list[bool | None]) -> bool | None:
    scored = [t for t in trials if t is not None]
    if not scored: return None
    return sum(scored) * 2 > len(scored)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=3,
                    help="trials per question (default 3, majority vote)")
    ap.add_argument("--out", default="eval_results.json",
                    help="output JSON path")
    ap.add_argument("--limit", type=int, default=None,
                    help="run only the first N scoreable questions (smoke test)")
    ap.add_argument("--ids", default=None,
                    help="comma-separated question ids to run, e.g. CF-3,T2-08-asa-storage-counsel")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(HERE.parent / ".env")
    except ImportError:
        pass

    # Import the judge here so a NotImplementedError from `ask()` shows
    # cleanly without requiring ANTHROPIC_API_KEY just to read help text.
    from judge import judge as llm_judge  # noqa: E402

    items, na = load_questions()
    scoreable = [it for it in items
                 if it["id"] not in na
                 and it["id"].split("-")[0] in PREFIXES]
    if args.ids:
        wanted = {qid.strip() for qid in args.ids.split(",") if qid.strip()}
        scoreable = [it for it in scoreable if it["id"] in wanted]
    if args.limit:
        scoreable = scoreable[:args.limit]

    print(f"Running {len(scoreable)} scoreable questions × {args.trials} trials\n")
    out: list[dict] = []
    byp_pass = defaultdict(int); byp_total = defaultdict(int)

    for i, it in enumerate(scoreable, 1):
        qid = it["id"]; prefix = qid.split("-")[0]
        byp_total[prefix] += 1
        trials = []
        for t in range(args.trials):
            try:
                ans = ask(it["question"])
            except Exception as e:
                print(f"  [{i:>3}/{len(scoreable)}] {qid} t{t+1}: ask() ERROR {e}")
                trials.append({"passed": None, "answer": "", "reasoning": f"ask err: {e}"})
                continue
            try:
                v = llm_judge(it["question"], it.get("expected", ""),
                              it.get("negative", ""), ans, qid=qid)
                trials.append({"passed": v.passed, "answer": ans,
                               "reasoning": v.reasoning})
            except Exception as e:
                trials.append({"passed": None, "answer": ans,
                               "reasoning": f"judge err: {e}"})
            time.sleep(0.3)
        passed = majority([t["passed"] for t in trials])
        mark = "PASS" if passed else ("FAIL" if passed is False else "ERR ")
        if passed: byp_pass[prefix] += 1
        nice = ", ".join("P" if t["passed"] else ("F" if t["passed"] is False else "E")
                        for t in trials)
        print(f"  [{i:>3}/{len(scoreable)}] {qid:<28} {mark}  ({nice})")
        out.append({
            "id": qid, "question": it["question"],
            "expected": it.get("expected", ""),
            "negative": it.get("negative", ""),
            "trials": trials,
            "majority": {"passed": passed,
                         "pass_count": sum(1 for t in trials if t["passed"]),
                         "scored_trials": sum(1 for t in trials if t["passed"] is not None)},
        })

    total_pass = sum(byp_pass.values()); total_den = sum(byp_total.values())
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    for p in PREFIXES:
        print(f"  {p:<6} {byp_pass[p]:>2}/{byp_total[p]:<3}")
    print(f"\n  TOTAL: {total_pass}/{total_den} = {100*total_pass/total_den:.1f}%")

    Path(args.out).write_text(json.dumps({
        "per_prefix": {p: f"{byp_pass[p]}/{byp_total[p]}" for p in PREFIXES},
        "total": total_pass, "denominator": total_den,
        "pct": round(100 * total_pass / total_den, 1),
        "trials": args.trials,
        "results": out,
    }, indent=2, ensure_ascii=False))
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
