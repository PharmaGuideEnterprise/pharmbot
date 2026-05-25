# Cohere Rerank Experiment — Findings

**Date:** 2026-05-23
**Branch:** `poc/chatbot-onyx-s7`
**Decision:** Reverted. Cohere `rerank-english-v3.0` over Cohere `embed-english-v3.0` retrieval regressed accuracy on the canonical 51 by ~9 percentage points vs Voyage `voyage-4-large` alone.

---

## What was tested

We swapped retrieval from Voyage `voyage-4-large` (1024d, 9682 chunks) to Cohere `embed-english-v3.0` (1024d, same 224 documents → 9682 chunks). On top of that, we patched Onyx's `search_runner.py` to add a Cohere `rerank-english-v3.0` step after hybrid retrieval (50 candidates → top-K after rerank). Tested K=5 and K=15.

Two surprises:

1. Onyx v2.12.13's OpenSearch retrieval path **does not invoke rerank natively** — the `RerankerProvider.COHERE` enum exists, the `cohere_rerank_api()` function exists, but they're only wired into the Vespa retrieval path. With OpenSearch active, rerank is dead code. The patched `search_runner.py` (mounted as a docker volume override) inserts the rerank step manually after `combine_retrieval_results`.

2. The rerank+Cohere combination **performed worse** than Voyage alone on this corpus:

| Metric | Voyage (no rerank) | Cohere + rerank top_5 | Cohere + rerank top_15 |
|---|---|---|---|
| Canonical 51 (regression) | **91.1%** (41/45) | 75.6% (34/45) | 82.2% (37/45) |
| New 30 (generalization) | **53.3%** (16/30) | 46.7% (14/30) | 46.7% (14/30) |

## Where Cohere+rerank specifically regressed

Five canonical questions Voyage passes but Cohere+rerank fails:

| ID | Question | Failure mode |
|---|---|---|
| CF-7 | First-line treatment in rhinosinusitis | Rerank surfaced antibiotic-treatment chunks. Answer led with "amoxicillin is first-line" instead of "watchful waiting / INCS first" — the exact mistake the original client feedback flagged. |
| CF-10 | Constipation in 7-month-old | Rerank reordered chunks; PEG dose still correct but answer violated some negative feedback. |
| PC-1 | First-line treatment for infant constipation | Same chunk-ordering shift. |
| PC-11 | Possible causes of chest pain | Rerank narrowed the chunks to angina-specific instead of the differential-diagnosis chunks. |
| SQ-23 | (meta-question, was already borderline) | — |

One canonical question Cohere+rerank passes but Voyage doesn't:
- CF-14 (QT prolongation external link) — rerank surfaced a chunk that mentioned external resources, marginally helping.

## Why this happened

1. **Older embedder.** Cohere `embed-english-v3.0` (released 2023) doesn't capture clinical-pharmacy semantics as well as Voyage `voyage-4-large` (released 2025-2026). The base retrieval is weaker, so rerank has worse candidates to reorder.

2. **Rerank "relevance" doesn't match clinical workflow.** For "first-line treatment of rhinosinusitis", chunks containing the specific drug (amoxicillin) score higher on lexical relevance than chunks describing the *recommended treatment hierarchy* (watchful waiting → INCS → antibiotics only after 10 days or worsening). Rerank pulled the lexically-relevant chunk to the top, which is clinically wrong.

3. **top_5 was too aggressive.** top_15 recovered some lost ground (75.6% → 82.2%) but still didn't reach Voyage's 91.1%.

## What this means strategically

Rerank isn't free quality. It only helps when:
- The base retrieval is the bottleneck (which it isn't here — Voyage's voyage-4-large already retrieves well)
- The rerank model's training distribution matches the domain (Cohere rerank-english-v3 is general-purpose; clinical pharmacy isn't its specialty)
- The top-K is tuned conservatively enough not to lose helpful context

Voyage offers `rerank-2.5` which sits on top of voyage-4-large in their training. That's the natural next test — but it requires standing up a LiteLLM proxy because Onyx v2.12.13 routes Voyage rerank through `RerankerProvider.LITELLM`. See `chatbot_poc/scripts/KNOWN_ISSUES.md` §4.

## Final decision

- **Embedder reverted to Voyage `voyage-4-large`** as active.
- **Rerank disabled** (`ENABLE_COHERE_RERANK=false`). The patch on `search_runner.py` stays in place — toggling the env flag is the only thing needed to re-enable.
- The full Cohere corpus (9682 chunks, same content, different embeddings) **stays indexed in OpenSearch** as a parallel Pattern-B option. Hot-switching back to Cohere via `EMBEDDING_PROVIDER=cohere python3 chatbot_poc/scripts/switch_active.py` remains a one-command operation.

## What's worth testing next

1. **Voyage rerank via LiteLLM** (KNOWN_ISSUES.md §4). LiteLLM proxy + Onyx config → uses voyage `rerank-2.5` on top of voyage-4-large. This is the version of rerank most likely to help.

2. **Domain-specific rerank.** If Voyage rerank-2.5 also doesn't help, the next layer is a clinical-fine-tuned reranker (e.g. BiomedBERT-based cross-encoder). Not commercially available off the shelf — would require training.

3. **Skip rerank, use verification pass instead** (Strategy 2 from `PRODUCTION_STRATEGIES.md`). A second LLM call that checks the answer against retrieved chunks catches the *application* failures (wrong drug for patient context), which rerank cannot help with anyway. This is likely the higher-leverage investment.

## What was learned that's worth keeping

- The Pattern B dual-embedder switching infrastructure works exactly as designed — we proved both providers are first-class, indexed in parallel, and hot-switchable in ~5 seconds.
- The `search_runner.py` patch pattern (mount via docker-compose.override.yml) is a clean way to extend Onyx without forking the codebase. Same pattern works for any post-retrieval hook (verifier, deduplicator, source-citation grounding).
- LLM-as-judge eval (the agnostic strategy) caught the regression cleanly. The regex-based eval from earlier iterations would not have surfaced "amoxicillin became first-line" as a problem since both contain `amoxicillin`.
