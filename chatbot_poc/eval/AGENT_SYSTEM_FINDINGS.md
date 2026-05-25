# Specialist Agent System — Experimental Findings

**Date:** 2026-05-23
**Branch:** `poc/chatbot-onyx-s7`
**Decision:** Implementation works; the architecture pattern regressed accuracy vs the simpler Voyage RAG baseline in this iteration. Kept in code under a feature flag (`use_agents=true`) for further iteration, but default route remains Voyage RAG.

## What we built

A specialist-agent system that mirrors Claude Code's agent definitions: each agent is a markdown file with YAML frontmatter. Per-query flow:

```
question
   ↓
Router (Claude call, picks specialist + confidence 1–10)
   ↓
If confidence ≥ threshold (6) AND specialist exists AND not rag_fallback:
   Specialist invocation (Claude with full chapter content loaded as context)
Else:
   Fall back to existing Onyx + Voyage RAG path
   ↓
Stream answer back to UI (same AOAI shape as before)
```

Three specialists + one fallback agent shipped:

| Agent | Scope | Chapters loaded |
|---|---|---|
| `pregnancy_lactation` | Trimester safety, NVP, EC in breastfeeding, menopause | NVP, contraception, menopause, UTI, bipolar, depression |
| `pediatric` | Weight-based dosing, age red flags, infant colic, OM | Constipation/child, OM child, asthma child, dehydration child, infant colic PDF, meningitis, acute pain, urinary incontinence child |
| `infectious_disease` | Antibiotic selection, UTI, meningitis prophylaxis, OM, rhinosinusitis | UTI, bacterial meningitis, sinusitis, acute OM child |
| `general_pharmacy` | Catch-all fallback (uses Onyx RAG instead of full-chapter loading) | — (uses Onyx) |

## Results

### Canonical 51 (regression metric)

| Strategy | Pass / Scoreable | % |
|---|---|---|
| Voyage + enhanced prompt (baseline) | 41/45 | **91.1%** |
| Cohere + rerank top_15 | 37/45 | 82.2% |
| **Voyage + specialist agents (this run)** | 35/45 | **77.8%** ↓ |

### 30 distilled new questions (generalization metric)

| Strategy | Pass / Scoreable | % |
|---|---|---|
| Voyage + enhanced prompt (baseline) | 16/30 | **53.3%** |
| Cohere + rerank top_15 | 14/30 | 46.7% |
| **Voyage + specialist agents (this run)** | 12/30 | **40.0%** ↓ |

### Route distribution on canonical 51

```
pregnancy_lactation:    6
infectious_disease:     7
pediatric:              8
onyx_fallback (broad):  41
```

(Note: 41 onyx_fallback because the router prefers general_pharmacy for anything not clearly in a specialist domain. Of the 21 specialist-routed questions, ~67% passed — but the specialist routes that regressed account for nearly all the lost ground vs baseline.)

## Why it regressed

Three distinct failure modes, all in the specialist-routed subset:

**1. Specialists are too restrictive at scope boundaries.** When a question is close-to-but-not-quite in scope, specialists refuse rather than hand off:

| ID | Routed to | Specialist's reason for failure |
|---|---|---|
| CF-2 | infectious_disease (conf=7) | "specialist does not cover diverticular disease" → refused. Should have routed to general_pharmacy or invoked Onyx fallback. |
| CF-6 | pregnancy_lactation (conf=8) | "lacks a source document on meningitis prophylaxis" → refused. The agent's chapter_files didn't include bacterial_meningitis.md. |
| SQ-6 | pediatric (conf=8) | Refused because patient age was in a previous conversation turn, not this question. Multi-turn context issue. |

**2. Cross-domain questions need multi-specialist orchestration.** CF-6 specifically: "meningitis prophylaxis in a pregnant patient" is BOTH an infectious-disease question AND a pregnancy question. The router picked one (pregnancy_lactation), that specialist didn't have the meningitis chapter, refused. The right move would have been to invoke infectious_disease's prompt (which explicitly handles "use ceftriaxone in pregnancy, not rifampin").

**3. Specialists' format diverges from clinical-editor's expected format.** CF-10: pediatric correctly gave PEG 4-17 g daily for infants (the absolute-grams form from the source). The clinical editor wrote "PEG 1-1.5 g/kg/day" in expected. Clinically equivalent for a 7-month-old (~7-9 kg), but the LLM judge flagged the missing per-kg form.

## What works

The Duavive smoke test (out-of-the-canonical-set):

> Question: "What is Duavive dose for 55 year old woman with recent hysterectomy?"
> Routed to: general_pharmacy → Onyx RAG fallback
> Answer opens with: "**Duavive is not recommended for a patient with a hysterectomy.**"

The architecture's design intent — lead with the contraindication — comes through when the right specialist (or general fallback) is selected. The pattern itself isn't wrong; the failure is in router decisions + specialist scope.

The UTI-in-pregnancy smoke test:

> Routed to: pregnancy_lactation (confidence 9, rationale: "Question involves medication safety in pregnancy combined with UTI management")
> Answer: clinically excellent — 2 consecutive cultures threshold preserved, full drug list with trimester-specific contraindications, fluoroquinolone caveat.

## What would fix the regression

Three things, in increasing complexity:

1. **Specialists should fall through to general_pharmacy when out of scope** instead of refusing. One-line shim change: if the specialist's first paragraph contains "does not cover" or "outside my scope" or similar, re-invoke as general_pharmacy. ~1 hour.

2. **Specialists need overlapping chapter assignments.** Pregnancy_lactation needs bacterial_meningitis (for meningitis-in-pregnancy questions). Pediatric needs more infectious-disease chapters. Either expand each specialist's chapter list, OR have an orchestrator that loads the specialist's prompt + chapters from multiple specialists when routing detects cross-domain. ~2 days.

3. **Multi-specialist routing for cross-domain questions.** The router should return a list (e.g. `[infectious_disease, pregnancy_lactation]`) for CF-6-style questions. The orchestrator invokes both, then aggregates. ~3 days, with the aggregator becoming a new failure point.

## Honest call

Specialist agents in their current shape **regressed** the metric we care about (clinical accuracy under LLM-judge eval). The architecture is sound; the **content design** (which chapters each specialist owns, how they handle scope-boundary questions) needs more iteration than fits this round.

Choices for the next iteration:

- **A — Keep agents disabled, revisit later.** Voyage baseline is the production setting. The agent code stays committed but unused via the `use_agents` flag. Focus next on verification pass + confidence scoring on top of Voyage baseline (the two strategies from PRODUCTION_STRATEGIES.md that don't depend on specialist routing).
- **B — Iterate on specialist scope.** Spend 2-3 days expanding chapter assignments and adding the "specialist out-of-scope → fall through" behavior, then re-test. If it doesn't reach Voyage baseline, accept the result and disable.
- **C — Pivot to broad-RAG-only with verification pass.** Skip specialists entirely. Use the saved engineering effort on verification + confidence on top of Voyage.

My recommendation: **C**. The specialist pattern is interesting, but the verification pass attacks the same failure class (patient-context reasoning) without the routing complexity. If verification + confidence don't close the gap, then revisit specialists with the lessons learned here.

## Code committed

- `chatbot_poc/agents/*.md` — 4 agent definitions
- `chatbot_poc/shim_service/agents.py` — loader + router + invoker + confidence helpers
- `chatbot_poc/shim_service/app.py` — `?use_agents=true` route flag
- `chatbot_poc/eval/ask_and_judge.py` — `--use-agents` test flag
- `chatbot_poc/eval/all51_agents_v2_judged.json` and `new30_agents_v2_judged.json` — eval outputs

All reusable, all gated behind the feature flag, default behavior unchanged.
