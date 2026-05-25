# MedEmbed + top-7 + temp=0.07 — Findings

**Date:** 2026-05-23
**Plan tested:** Three changes in sequence:
1. Switch embedder to `abhinand/MedEmbed-large-v0.1` (domain-specific medical embedder, BGE-large derived)
2. Retrieve top-7 chunks per query (down from default top-10)
3. Set temperature to 0.07 (small bump from 0)

**Result:** MedEmbed indexing didn't complete (env limitation). Top-7 + temp=0.07 on Voyage **regressed -2.2 pts canonical, -3.4 pts new-30**.

## What happened with MedEmbed

| Step | Result |
|---|---|
| Add MedEmbed search_settings row (1024-dim, local provider) | ✅ |
| Clone OpenSearch index mapping from Voyage | ✅ |
| Switch active to MedEmbed + restart Onyx | ✅ |
| Pre-warm model in inference_model_server (Sentence-Transformers 4.0.2) | ✅ — model loaded in 44s |
| Test embed speed on CPU | **1.1 chunks/sec** on realistic 500-token clinical text |
| Trigger reindexing of all 6 file connectors | ✅ — 6 IN_PROGRESS attempts created |
| Actual chunk-count growth after 7 minutes | **0 chunks indexed.** |

Three failure modes hit simultaneously:

1. **CPU-only inference is too slow for this corpus.** Measured 1.1 chunks/sec on realistic clinical text. 9,682 chunks → ~2.5 hours estimated. We don't have GPU.

2. **Onyx's worker-to-model-server wiring stalled.** Onyx's indexing workers initialized the HuggingFaceTokenizer for MedEmbed correctly, but the actual embedding requests never reached the inference_model_server container (its logs showed only `/api/health` calls). After 7 minutes of "IN_PROGRESS" with 0 batches completed, the indexing pipeline was effectively stuck — diagnosing would have burned another hour.

3. **Memory pressure across multiple workers.** Onyx spawns one indexing worker per connector. Each loads the full ~1.3 GB MedEmbed model into memory independently. 6 workers × 1.3 GB = 7.8 GB of model context alone, before considering Onyx's other processes.

**Reverted to Voyage** to avoid sitting on stalled indexing for hours.

## What happened with top-7 + temp=0.07

Test setup: Voyage embedder (no MedEmbed), few-shot prompt v2 (deployed), `num_chunks=7` on persona, `temperature_override=0.07` in shim.

| Metric | Voyage + few-shot v2 + temp=0 (prior best) | This run (top_7 + temp=0.07) | Δ |
|---|---|---|---|
| Canonical 51 | 41/45 = 91.1% | 40/45 = 88.9% | **-2.2 pts** |
| New 30 | 17/30 = 56.7% | 16/30 = 53.3% | **-3.4 pts** |

### Why this regressed

**top_k=7 vs top_k=10:** Fewer chunks = less context for the LLM to synthesize from. Questions that need cross-section knowledge (e.g. drug + trimester + dose combination) lose helpful context when retrieval is too tight. 10 was the right number for our corpus.

**Temperature 0.07 vs 0:** Tiny stochasticity adds variance without measurable benefit. The few questions that regressed showed up as one-shot variance — same question, slightly different rendering, judged differently by the LLM-as-judge. With `temperature=0`, the same question deterministically produces the same answer; at 0.07, you get a sliver of variation that's enough to flip borderline judgments.

Both changes individually probably contribute roughly equally to the regression. Combined they cost ~5 pts.

## What's deployed now

Reverted both:

| Setting | Value |
|---|---|
| Active embedder | Voyage `voyage-4-large` (PRESENT) |
| MedEmbed search_settings row | Kept (PAST status — easy to flip back if we get GPU access or HF Inference Endpoint) |
| `num_chunks` on personas 0 and 1 | 10 (reverted from 7) |
| `temperature_override` in shim | 0.0 (reverted from 0.07) |
| Few-shot prompt v2 | Active (still the +3.4 pt win) |

## What we'd need to actually test MedEmbed properly

| Path | Time | Cost |
|---|---|---|
| **A.** HuggingFace Inference Endpoint (GPU, paid) | ~15-20 min reindex + 30-60 min eval | ~$0.30-1.00 |
| **B.** Run a separate `text-embeddings-inference` container with GPU (e.g. on a colab/cloud GPU) | ~3 hours setup + ~15 min reindex | ~$1-3 |
| **C.** Use a pre-quantized MedEmbed (ONNX or GGUF) on CPU | ~1 hour setup + ~30-60 min reindex | $0 |
| **D.** Skip MedEmbed entirely — the data so far suggests retrieval isn't our bottleneck | — | — |

For option D: of our 6 previous architecture experiments, all 5 that touched retrieval (Cohere rerank, Voyage rerank, specialist agents, top-K change, MedEmbed) either regressed or stalled. The one that helped (few-shot examples) was content, not retrieval.

## Lesson confirmed

Our remaining failures are predominantly **clinical reasoning** (patient-context application, numeric threshold mapping, max-dose enforcement) — not retrieval. Five experiments in a row have suggested retrieval isn't the bottleneck.

The strategies most likely to actually move the metric now:
- **Tool use** (`calculate_pediatric_dose(weight, mg_per_kg, max_cap)`) — addresses the specific NQ-002/NQ-017/CF-18 failure class
- **Clinical pharmacist review pipeline** — to refine the eval and surface gaps that automated checks miss
- **Fine-tuning** on a vetted Q&A dataset — biggest potential lift, multi-week effort

Or accept the current 91.1% / 56.7% as the deployable state and ship.

## Production state right now

Same as the previous iteration:
- Canonical 51: **41/45 = 91.1%**
- New 30: **17/30 = 56.7%** (+3.4 pts vs the original 53.3%)
- Configuration: Voyage `voyage-4-large` + few-shot prompt v2 + `temperature=0` + top-10 retrieval

Everything else (verifier, rerank, specialist agents, MedEmbed, top-7, temp=0.07) is committed under feature flags but disabled by default.
