# Eval Harness — CPS Pharmacy Chatbot POC

Minimal pharmacist-question regression harness. Hits a running local Onyx
instance, scores each golden question on retrieval, keyword coverage,
off-topic refusal, and citation presence. **Structural checks only — no
LLM-as-judge.** That's enough to catch obvious regressions in v1.

This is the **v1 minimum** (32 Q&A pairs). Production target is **200+
pharmacist-graded Q&A pairs** before clinician rollout.

---

## Prerequisites

1. Onyx is running locally (`http://localhost:8080` reachable):
   ```bash
   cd ../  # chatbot_poc/
   ./bootstrap.sh
   ```
2. The CPS corpus has been ingested (`ingest/push_markdown_to_onyx.py`).
3. `.env` has `ONYX_ADMIN_EMAIL` and `ONYX_ADMIN_PASSWORD`.

## Run

```bash
# Full run (all 32 questions in golden_set.jsonl)
python3 eval/run_eval.py

# Quick smoke test (first 5 questions)
python3 eval/run_eval.py --limit 5

# Custom output path
python3 eval/run_eval.py --output /tmp/eval_run_2026_05_22.jsonl
```

If Onyx isn't reachable the script exits fast with a clear message pointing
back to `bootstrap.sh`.

## Output

- Stdout: scorecard (totals, retrieval %, avg keyword coverage, refusal %,
  citation-present %).
- File: `eval/results_{utc_timestamp}.jsonl` — one row per question with
  the full answer, citation count, top-3 citation previews, per-axis
  scores, elapsed time, and any error string. Inspect failures here.

## Scorecard axes

| Axis | Applies to | What it measures |
|---|---|---|
| **Retrieval correct** | Questions with `expected_chapter` set | Did any returned citation reference the expected chapter slug? |
| **Avg keyword coverage** | Questions with non-empty `expected_keywords` | Mean fraction of expected drug names / mechanisms present in the answer (0.0 – 1.0) |
| **Off-topic refusal correct** | `category == "off-topic"` or `expected_refusal: true` | Did the answer contain a refusal phrase (regex-matched)? |
| **Citation present** | `must_cite: true` | Did the response include ≥1 citation? |

### Pass / regression bars (v1 POC)

These are the v1 sanity bars; the real bars are pharmacist-judged correctness
in Week 4 of the PLAN.

- **Retrieval correct ≥ 70%** — below this, retrieval is broken.
- **Avg keyword coverage ≥ 0.50** — below this, the LLM is paraphrasing
  away clinical detail.
- **Off-topic refusal ≥ 90%** — patient-safety bar; refusing off-topic
  is a domain guardrail, not a polish item.
- **Citation present 100%** on `must_cite` questions — citation-grounded
  RAG with zero citations is a hard failure.

Regression is **any axis dropping by ≥10 percentage points run-over-run**
or any of the above bars breached.

## Adding new Q&A pairs

`golden_set.jsonl` is one JSON object per line. Schema:

```json
{
  "id": "Q033",
  "question": "string — the pharmacist's question",
  "expected_chapter": "string slug under cps_content/ (or null for off-topic)",
  "expected_keywords": ["3-5 precise terms a correct answer must mention"],
  "must_cite": true,
  "category": "treatment-selection | dose-titration | adverse-effects | drug-interactions | monitoring | off-topic",
  "expected_refusal": true  // off-topic only; omit otherwise
}
```

**Tips for good questions**:
- `expected_chapter` must match an existing directory under `cps_content/`.
  Verify with `ls cps_content/ | grep <slug>`.
- Keep `expected_keywords` to 3-5 *precise* terms (drug names, mechanisms,
  numeric thresholds). Avoid generic words like "treatment" or "patient".
- For adversarial off-topic questions, set `expected_chapter: null`,
  `expected_keywords: []`, `must_cite: false`, `expected_refusal: true`.

After editing, verify the file is valid JSONL:

```bash
python3 -c "import json; [json.loads(l) for l in open('eval/golden_set.jsonl') if l.strip()]"
```

## Roadmap

- v1 (now): structural checks, 32 Q&A. Swap-in target.
- v2: migrate to **Promptfoo** with citation-aware LLM grading per `PLAN.md`
  Week 4. Expand to 200+ Q&A with pharmacist sign-off.
- v3: nightly CI run, regression diffs posted to Slack / Linear, citation
  click-through telemetry from Langfuse joined into the scorecard.
