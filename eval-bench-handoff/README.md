# CPS Pharmacy Chatbot Benchmark — Handoff to External POC

This bundle lets you evaluate **your** pharmacy-chatbot POC against the same
85-question clinical test set + LLM-as-judge methodology we've been using to
develop and lock our reference assistant. Result: a directly comparable
**/85 score** with a per-prefix breakdown.

**Our current reference: S8 = 75/85 = 88.2%** (3-trial majority). Reproducible
band ~72–76/85 due to LLM judge + generation variance.

---

## What's in this bundle

| File | Purpose |
|---|---|
| `README.md` | This document |
| `questions/all_questions.json` | The 62 "canon" questions (CF + CPHA + PC + SQ + showstoppers) |
| `questions/new_questions.json` | The 30 "new clinical scenario" questions (NQ-001 … NQ-030) |
| `questions/tier2_targeted_questions.json` | The 10 "tier-2 targeted" questions (T2-01 … T2-10) — brand/dose/IFP focus |
| `questions/corpus_silent_qids.json` | 5 questions the audit flagged as our private corpus genuinely lacks (used to route the judge) |
| `na_exclusions.json` | 17 questions excluded from scoring (UX feedback, conversational follow-ups, malformed expecteds) → leaves **85 scoreable** |
| `judge.py` | Self-contained LLM-as-judge (two prompt variants: STRICT + SILENT-aware) |
| `run_eval.py` | The runner you plug your chatbot into |
| `reference_results.json` | Our scores for direct comparison (S8 / S7 / S6 / S5 R5 RERUN / S1 / Perfect) |

102 raw questions − 17 NA → **85 scoreable**. Prefixes: CF (16) + CPHA (6) +
NQ (30) + PC (8) + SQ (15) + T2 (10) = 85.

---

## Quick start

```bash
# 1. Python ≥3.10, install deps
pip install requests

# 2. The judge calls Claude — set your key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Open run_eval.py and replace the `def ask(question)` stub
#    with a call to YOUR chatbot's endpoint.

# 4. Smoke test (3 questions × 3 trials = ~30 sec):
python run_eval.py --limit 3 --out smoke.json

# 5. Full run (85 questions × 3 trials ≈ 60–90 min depending on
#    your chatbot's latency + the judge's):
python run_eval.py --out my_results.json
```

The script prints per-prefix totals + the /85 score and writes a JSON with
every trial's answer, judge reasoning, and per-question verdict.

---

## What each question looks like

Every question record has the same shape:

```json
{
  "id": "CF-12",
  "question": "What is the recommended duration of amoxicillin in pediatric AOM failure of first-line?",
  "expected": "Per the CPS AOM chapter ... 10 days in children even on failure of first-line.",
  "negative": "Inventing a shorter duration based on adult guidance ..."
}
```

`expected` and `negative` come from clinical-pharmacist review. They are
**shorthand notes**, not verbatim transcripts the model must reproduce — the
judge's instructions explicitly allow paraphrase, expansion, and extra
correct content.

---

## How the judge decides PASS / FAIL

`judge.py` has **two prompt variants**; the runner picks one per question
based on a pre-audited corpus-signal flag:

### STRICT_JUDGE_SYSTEM (default — all `unknown` qids)

Pass requires **BOTH**:
- **(a)** Substantive clinical content from `expected` is present in the
  answer (paraphrase / expanded / embedded in a list / extra detail OK).
- **(b)** The answer does NOT make the **specific** mistake described in
  `negative`. Extra correct content is fine; the bar is "did the answer
  commit that exact error?"

### SILENT_JUDGE_SYSTEM (only the 5 qids in `corpus_silent_qids.json`)

Same as STRICT, **plus** criterion (c):
- **(c)** HONEST SOURCE-SILENT REFUSAL — if the answer clearly states the
  corpus does not contain the specific content, describes what *is* in the
  corpus, and does not invent the missing detail → PASS.

> ⚠️ Re-audit `corpus_silent_qids.json` for your stack. Whether a question
> is "silent" depends on what content you've ingested. Our 5 are based on
> our (CPS) corpus — yours may differ.

### Scoring

For each question we run **3 trials** and majority-vote (≥2/3 = PASS). This
trades a small amount of API cost for resistance to single-shot LLM noise.

### Why an LLM judge?

We previously used hand-graded answers and a hard-coded string-match judge;
both proved brittle on a corpus this size. The LLM judge with these two
prompts gave us ±2–3 question variance per 85-Q run — tight enough to
detect real model deltas while accepting paraphrase / verbose-but-correct
answers.

---

## NA exclusions — why 17 questions don't count

Two categories (full list in `na_exclusions.json`):

**PRE_NA (11)** — questions that aren't really clinical Q&A:
- UX feedback ("the chat history doesn't persist", "the print option is hard
  to find")
- Conversational follow-ups that need prior-turn context (the harness is
  single-turn)

**RECLASSIFY_NA (6)** — eval-data-quality issues:
- Placeholder `"expected": "(see full comment)"` with no criteria to judge
  against (CPHA-17, CPHA-19)
- Editor's expected was a bare tag like `"Y"` that source-grep confirmed
  is *absent* from the corpus (CF-16 probiotics-in-MS, CF-17 cladribine
  for SPMS); the chatbot's "no info" answer is actually correct
- `CPHA-12-lithium`, `PC-3` (bare "Ozempic" with no context): similar
  data-quality reasons

These exclusions are documented honestly so you can decide whether to
exclude them for your run or include them with different expecteds.

---

## Our reference results

| Strategy | CF/16 | CPHA/6 | NQ/30 | PC/8 | SQ/15 | T2/10 | **Total /85** | **%** | Basis |
|---|---|---|---|---|---|---|---|---|---|
| S1 (original agentic-v3) | 15 | 6 | 24 | 8 | 14 | 7 | 74 | 87.1% | 1-shot |
| S5 R5 RERUN | 13 | 3 | 23 | 5 | 14 | 6 | 64 | 75.3% | 3-trial |
| S6 Final | 13 | 4 | 24 | 5 | 14 | 6 | 66 | 77.6% | 3-trial |
| S7 (dosing-fidelity few-shot) | 16 | 6 | 24 | 6 | 12 | 8 | 72 | 84.7% | 3-trial |
| **S8 (vision-LLM corpus, current)** | **16** | **5** | **24** | **7** | **14** | **9** | **75** | **88.2%** | 3-trial |
| *Perfect (nail every Q)* | 16 | 6 | 30 | 8 | 15 | 10 | *85* | *100%* | — |

(`reference_results.json` has these in machine-readable form.)

### Honest caveats on this comparison
- **Trial basis**: S1 is **single-verdict** (1 saved answer/question); S5–S8
  are **3-trial majority**. Single-verdict tends to run noisier and slightly
  higher. Run your eval at 3-trial for a clean S5+ comparison.
- **Corpus dependency**: a big chunk of our progression came from corpus
  improvements (corpus-grounded expected corrections, vision-LLM image
  captioning) — not pure model quality. If you can ingest images via OCR or
  vision, you'll close the same gap; if not, T2 and SQ may be lower.
- **The judge has variance** (~±2–3 questions on an 85-Q run). One run is
  not a definitive ranking — average 2–3 runs if you need a tight estimate.

---

## What you'll learn from running this

1. **Total /85** → your headline accuracy on the same set we use.
2. **Per-prefix breakdown** → tells you whether failures cluster in a
   specific clinical-skill axis (T2 = brand/dose lookups, NQ = clinical
   scenarios, SQ = MCQs, CF = formulary, etc.).
3. **The trial JSON** → every answer + judge reasoning, so you can audit
   *why* a question failed and decide if it's a model issue, a retrieval
   issue, a corpus-coverage issue, or a test-data issue.

If you spot any test-data issue (a `negative` that's too strict, an
`expected` that's outdated, or an NA case we should add) — flag it back and
we'll reconcile our test set with yours.

---

## Tips for your run

- **Smoke test first** (`--limit 3`) to confirm `ask()` and the judge both
  work end-to-end before committing 60+ min to the full run.
- **Streaming**: if your chatbot streams, accumulate the full text in
  `ask()` before returning — the judge needs the complete answer.
- **Timeouts**: agentic chatbots can take 30–90 s on dose/algorithm
  questions; default your `requests.post(timeout=…)` accordingly.
- **Judge model**: defaults to `claude-haiku-4-5-20251001`. For tighter
  variance, set `export JUDGE_MODEL=claude-sonnet-4-6` (slower, pricier,
  marginally more consistent — diminishing returns).
- **API budget**: 85 × 3 = 255 chatbot calls + 255 judge calls. Haiku-judge
  is roughly $0.30–$0.60 per full run depending on answer length.

---

## Output schema

`run_eval.py` writes a single JSON:

```json
{
  "per_prefix": {"CF":"15/16","CPHA":"5/6","NQ":"24/30","PC":"7/8","SQ":"14/15","T2":"9/10"},
  "total": 75, "denominator": 85, "pct": 88.2,
  "trials": 3,
  "results": [
    {"id":"CF-1","question":"...","expected":"...","negative":"...",
     "trials":[{"passed":true,"answer":"...","reasoning":"..."}, ...],
     "majority":{"passed":true,"pass_count":3,"scored_trials":3}},
    ...
  ]
}
```

The `results` list contains every question, every trial — drop it into a
spreadsheet or feed it back into your own analytics.

---

## Questions / feedback

Open an issue or email back with:
- the JSON your run produced
- which `ask()` integration you used (endpoint shape, model, retrieval setup)
- any test-data issues you spotted

We'll reconcile and iterate.
