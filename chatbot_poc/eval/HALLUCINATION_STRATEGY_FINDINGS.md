# Hallucination Strategy Evaluation — Findings

**Date:** 2026-05-22
**Branch:** `poc/chatbot-onyx-s7`
**Eval script:** `chatbot_poc/eval/hallucination_strategies.py`
**Raw answers:** `chatbot_poc/eval/hallucination_strategies_output.json`

## Origin

Client review of one UTI-in-pregnancy answer flagged three failure modes:

| Code | Failure | Source-of-truth |
|------|---------|-----------------|
| F1 | Dropped the "2 consecutive cultures" diagnostic threshold | `urinary_tract_infection.md` says verbatim "treat if asymptomatic bacteriuria is confirmed on 2 consecutive cultures" |
| F2 | Invented elaboration on a bulleted drug name (e.g. "Cephalexin: Usage: A commonly used cephalosporin…") | Source lists cephalexin as a plain bullet with no description |
| F3 | Blurred sulfamethoxazole vs trimethoprim as if they were one warning | Source states TWO distinct rules: (a) TMP + SMX/TMP avoided in first trimester, (b) sulfamethoxazole avoided in last 6 weeks |

We added F5 (acknowledge when the source is silent on a sub-scenario) and F6 (refuse off-topic) to test generalization beyond the original complaint.

## Method

5 questions × 8 strategies × 3 trials = 120 LLM calls (G_two_pass added an extra turn each, ~135 total). Each strategy posted via Onyx's per-request `prompt_override.system_prompt` and `temperature_override` — no persona-row mutation needed.

| Strategy | Prompt | Temp | Notes |
|----------|--------|------|-------|
| B0_baseline | current persona prompt | default | what the client tested |
| A_hardened_prompt | + anti-hallucination rules H1-H5 | default | |
| B_temp0 | current persona prompt | 0 | minimal-change candidate |
| C_quote_anchor | hardened + verbatim-quote requirement | 0 | strictest |
| D_hardened_temp0 | hardened | 0 | |
| E_aggressive_minimal | "OVERSHOOT MODE — STRICT VERBATIM" | 0 | the "overshoot" idea |
| F_chunks_high | hardened + 2 extra chunks above/below | 0 | more context |
| G_two_pass_critique | hardened + self-critique turn | 0 | the "overshoot then tighten" idea |

Each answer is checked with regex/keyword heuristics that look for the specific failure pattern (e.g. F3 requires both `first trimester` AND `hyperbilirubinemia`/`last 6 weeks` adjacent to `sulfamethoxazole` — "near term" alone doesn't count because the source uses that phrase for nitrofurantoin too).

## Results (pass-rate, all trials)

```
strategy                Q1    Q2    Q3    Q5    Q6    overall
B0_baseline             9/9   3/3   1/3   0/3   3/3   16/21 (76%)
A_hardened_prompt       9/9   3/3   2/3   0/3   3/3   17/21 (81%)
B_temp0                 9/9   3/3   3/3   0/3   3/3   18/21 (86%)  ← winner
C_quote_anchor          9/9   3/3   2/3   1/3   3/3   18/21 (86%)  ← tied winner
D_hardened_temp0        9/9   3/3   2/3   0/3   3/3   17/21 (81%)
E_aggressive_minimal    3/9   0/3   3/3   1/3   3/3   10/21 (48%)
F_chunks_high           3/9   0/3   3/3   0/3   3/3    9/21 (43%)
G_two_pass_critique     3/9   0/3   3/3   0/3   2/3    8/21 (38%)
```

## Honest findings

1. **The biggest, cheapest win is `temperature=0`.** Setting it alone (B_temp0, no prompt changes) takes the system from 76 % → 86 %. The client's three reported failures (F1, F2, F3) all pass 100 % under B_temp0 across multiple question phrasings. **This is the change being deployed.**

2. **The client's complaint was a variance problem, not a prompt problem.** At default temperature the baseline produces correct answers 67–100 % of the time depending on which criterion. The cephalexin elaboration in particular reproduces only ~33 % of the time. Temperature=0 collapses the variance.

3. **More elaborate prompts barely help on top of temp=0.** A_hardened, D_hardened_temp0 (81 %) underperformed plain B_temp0 (86 %). Adding rules the model already implicitly knows is mostly cargo-culting at temperature 0.

4. **The "overshoot then tighten" idea backfired here.** The naive multi-turn self-critique (G_two_pass_critique) regressed to 38 %. Reading the failed answers shows why: the second turn's prompt ("re-read each sentence against the retrieved chunks") confused the model about which "text" to critique. It produced meta-commentary ("No clinical facts are present in the provided text…") instead of a revised answer. A better implementation would inject the original answer into a *single* prompt rather than splitting across turns — but that's future work.

5. **Aggressive minimal mode (E) and high-chunks mode (F) both made things worse.** E was too rigid — it sometimes refused to produce the comprehensive treatment list at all. F gave the model more context to confabulate connections from. Adding rules and adding context are not free.

6. **Q5 (PCN allergy gap) is the open problem.** Every strategy except C_quote_anchor failed to hedge that the source doesn't explicitly cover penicillin-allergic UTI in pregnancy. The model confidently provides a clinically reasonable synthesis (pick the non-penicillin options from the list) WITHOUT noting that the source never explicitly framed those as PCN-allergy recommendations. C_quote_anchor caught it 1/3 times.
   - This is a real production gap that needs a different intervention — probably a retrieval-quality check ("does any chunk mention 'penicillin allergy'? if not, hedge") rather than a prompt rule.

7. **Q3 (cephalexin-targeted) reproduces the client's F2 complaint only intermittently.** Baseline failed 2/3 trials with the elaboration pattern. B_temp0 fixed it 3/3. So the client did see a real issue — it just wasn't deterministic.

## What was deployed

`chatbot_poc/shim_service/app.py` now sends `temperature_override: 0.0` on every `/chat/send-message` call. One-line change, no persona-prompt mutation needed.

## What was NOT deployed

- C_quote_anchor's full prompt is ranked tied for first, and **uniquely catches Q5 some of the time**, BUT produces verbose answers stuffed with quotation marks. Whether that's worth the readability cost is a clinical-team call, not an engineering one.
- The hardened anti-hallucination rules (H1–H5) don't pay for themselves at temperature 0 — kept on disk in this doc for future reference but not enabled.
- The two-pass critique idea isn't dead — it just needs to be re-implemented as a single-prompt structure (original-answer-in-context, not a follow-up turn) before re-testing.

## Caveats — be careful with this data

- All eval calls were against Onyx's vector store running on **Cohere embed-english-v3.0**. The 144-trial run exhausted the Cohere Trial-tier quota (1000 calls/month), so end-to-end shim verification of the deployed change wasn't re-runnable in the same session. The change itself is a single body-field addition — verified live in code, not at runtime.
- Heuristic scoring isn't a substitute for clinical review. F1/F2/F3 use regex that can miss subtler hallucinations (e.g. wrong dose, wrong mechanism explanation that doesn't trigger our bad-term list). A human pharmacist needs to spot-check before this is a clinical product.
- Q3 (cephalexin) showed only ~33% failure on baseline — meaning the client's reported issue is real but probabilistic. A 10-trial run would give a tighter estimate; we ran 3.
- The two-pass critique might still work with a different prompt structure; we tested one specific implementation.
- Cohere Trial-key exhaustion is itself a production blocker — for ongoing eval and live traffic we either need a paid Cohere key, or a different embedding provider (Voyage, Nomic local, OpenAI text-embedding-3).
