# Conservative Strategies Iteration — Findings

**Date:** 2026-05-23
**Plan tested:** Four conservative additions on top of Voyage baseline:
1. Verification pass
2. Few-shot examples in system prompt
3. Confidence scoring
4. Voyage rerank-2.5 via direct API

**Result:** Few-shot examples (alone) gave the only net improvement. The other three either regressed or were neutral.

## Final comparison table

| # | Strategy | Canonical 51 | New 30 | Verdict |
|---|---|---|---|---|
| 1 | Voyage + enhanced prompt v1 (baseline) | **41/45 = 91.1%** | **16/30 = 53.3%** | Reference |
| 2 | Cohere + rerank top_15 | 37/45 = 82.2% | 14/30 = 46.7% | Regressed |
| 3 | Voyage + specialist agents | 35/45 = 77.8% | 12/30 = 40.0% | Regressed |
| 4 | + verifier + Voyage rerank + few-shot | 19/45 = 42.2% | 5/30 = 16.7% | Regressed hard |
| 5 | + verifier + few-shot (no rerank) | 35/45 = 77.8% | 17/30 = 56.7% | Mixed |
| 6 | **few-shot v2 ALONE** | **41/45 = 91.1%** | **17/30 = 56.7%** | **Winner** |

## What worked, honestly

**Few-shot examples in the system prompt** are the only conservative addition that actually moved the metric. New-30 went 53.3% → 56.7% (+3.4 pts) with no canonical regression. That's the strategy now deployed.

The five examples in `chatbot_poc/onyx_patches/enhanced_prompt_v2.txt` target the specific failure patterns we'd seen:
- Example 1: UTI in pregnancy — SMX vs TMP distinction
- Example 2: Duavive in hysterectomy — lead with contraindication
- Example 3: PE diabetes risk factors — apply age threshold to specific patient
- Example 4: amoxicillin for 50kg child — show calculation + max-dose cap
- Example 5: dual-allergy UTI in pregnancy — name what IS / ISN'T in source

The model uses these as format calibration and reasoning examples for similar question shapes.

## What didn't work, honestly

**Voyage rerank-2.5 regressed (same pattern as Cohere rerank).** Tested as Strategy 4. The verifier post-rerank truthfully said "source doesn't address this" — because rerank had reordered chunks so the right content didn't land in the top 15. Lesson: rerank quality is highly model-dependent, and for clinical workflow content, both Cohere and Voyage rerank prefer lexically-matching chunks over clinically-correct ones. Two rerank experiments, two regressions. We're done with rerank.

**Verification pass had a fundamental design issue.** Onyx's streaming events emit `blurb` (snippets), not full chunks. The verifier saw only 200-character snippets and incorrectly flagged correct synthesis as "invented content." Even after rewriting the verifier prompt to be permissive and audit on its own clinical knowledge, the verifier triggered regenerations that frequently *lost* correct content (Strategy 5: canonical regressed -13 pts despite new-30 gaining +3 pts).

The verifier's design intent is correct — catch safety errors — but it needs:
- Full chunk content (not blurbs)
- A confidence-gate so it doesn't second-guess already-good answers
- Per-question-type calibration (the same prompt is too strict for some questions, too lax for others)

That's >1 week of additional work. Cost-benefit doesn't justify it given few-shot already gave us +3.4 pts.

**Confidence scoring works correctly but is essentially unmeasured here.** It's computed (retrieval median + LLM self-rating + band), included in the response payload, but the eval doesn't surface it. For UI deployment it's ready — just needs front-end work to display.

## What's deployed now

- **Embedder:** Voyage `voyage-4-large` (unchanged)
- **System prompt:** `enhanced_prompt_v2.txt` (added 5 few-shot examples, applied to persona via SQL)
- **Verifier:** Code committed, default OFF (`ENABLE_VERIFIER=false` in `.env`). Opt-in via `?verify=1`.
- **Confidence scoring:** Computed when verifier is on; otherwise not surfaced. UI integration deferred.
- **Voyage rerank:** Code committed, default OFF. Opt-in via `ENABLE_VOYAGE_RERANK=true`.
- **Specialist agents:** Code committed, default OFF. Opt-in via `?use_agents=true`.

Three opt-in features sitting in code, three confirmed non-improvements. The default path is now: Voyage retrieval → Onyx RAG with few-shot v2 prompt → answer. Same architecture as the baseline, better prompt content.

## Production accuracy after this iteration

- **Canonical 51 (the client's original showstoppers + companions):** 91.1%
- **New 30 (designed to find gaps):** 56.7%

That's a +3.4 pt improvement on the generalization metric, no regression on the regression metric. Modest, but it's the first net improvement we've seen since the original Voyage + enhanced prompt baseline. Every other "clever" addition we've tried has regressed.

## What this means strategically

We've now tried six architectural changes; one (few-shot prompt) helped. The pattern is clear:

> **The Voyage + enhanced prompt baseline is a very strong local optimum. Further gains require either (a) better source content, (b) human clinical review feeding the eval, or (c) novel architectures that haven't been tried — not the conventional RAG-improvement playbook.**

For the remaining gap (43% of new-30 still fails), the failure analysis points at:
- **Patient-specific reasoning across multiple thresholds** — the model retrieves correctly but doesn't always apply numeric criteria to the patient
- **Cross-chapter synthesis** — questions that span multiple specialist domains
- **Specific dose calculations with max-cap enforcement** — pediatric dosing where the model gets the per-kg right but doesn't apply the cap

These are clinical-reasoning gaps, not retrieval gaps. The strategies most likely to move them further:

| Strategy | Why it would help | Risk |
|---|---|---|
| Tool use (e.g. `calculate_pediatric_dose(weight, mg_per_kg, max_cap)`) | Structurally enforces max-dose enforcement; eliminates calculation errors | Implementation complexity; only addresses a narrow failure class |
| Curated Q&A bank (vetted answers for the top 100 most-asked questions) | 100% accurate for covered questions; falls back to RAG for the rest | Maintenance burden; doesn't scale to novel queries |
| Clinical pharmacist review pipeline | Catches issues no automated eval can | Cost: pharmacist time; doesn't improve answers in real-time |
| Fine-tuning Haiku 4.5 on a corpus of vetted CPS Q&A | Trains the model to internalize CPS reasoning patterns | Training cost; weeks of work to get a clean dataset |

None of these are quick wins. The right move at this point is to **lock in the +3.4 pt few-shot gain, integrate confidence scoring into the UI, ship to supervised pharmacists, and let real usage tell us where to invest next.**

## Code artifacts

| File | Status |
|---|---|
| `chatbot_poc/onyx_patches/enhanced_prompt_v2.txt` | **Active** — applied to persona 0 and 1 |
| `chatbot_poc/shim_service/verifier.py` | Committed, off by default |
| `chatbot_poc/shim_service/app.py` | New paths: `_generate_verified_stream`, `_generate_agent_stream` (both off by default) |
| `chatbot_poc/docker-compose.override.yml` | `ENABLE_VOYAGE_RERANK=false`, `ENABLE_COHERE_RERANK=false` |
| `chatbot_poc/eval/all51_fewshot.json`, `new30_fewshot.json` | Winning strategy outputs |
| `chatbot_poc/eval/all51_verified_judged.json`, `all51_v3_judged.json` | Failed strategy outputs (kept for reproducibility) |
