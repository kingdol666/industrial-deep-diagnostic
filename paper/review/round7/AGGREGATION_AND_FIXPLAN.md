# Round 7 — Aggregated Verdicts & Fix Plan (v2)

## Verdicts: R5 MINOR / R6 MINOR / R7 MINOR / R8 MINOR (all MINOR — converged from R1's MAJOR)

## Verified must-fixes (all confirmed by lead before dispatch)
1. **L6 claim overcorrected in Round 6** (R6#1 + R8#2): canonical tep_d14 `04_diagnostics/evidence.json`
   holds a rank-6 item sourced "TEP基准过程知识(L5/L6)" (corroboration-only). Fix both occurrences
   (§3.2, §9): "no L6 item enters any surviving chain as decision evidence (the single L5/L6-tagged
   item in the corpus is marked corroboration-only); no verdict rests on external evidence."
2. **RAG era-split wrong** (R8#1 + R6-S1): engagement varied run-by-run — skab_valve1_1 retrieved 21
   chunks; canonical tep_d14 also retrieved successfully; skab_cavitation_13/skab_normal_control have
   no RAG file (fast-reuse); tep_d00/d01/batch093 record explicit fallback events. Rewrite per-run.
3. **Eq(1) conditioning-variable mixing** (R5#1): restate as c ≤ min(five-factor, applicable caps);
   caps: 0.70 CS, 0.65 INDIST subclass, 0.50 anti-osc (code name PARAM_AMBIGUITY); no protocol cap
   for det/nd; reason-coded per-run ceilings may still bind.
4. **|Xi|>|Ei| is agent-applied protocol** (R5#3): machine-checked parts = ≥2 eliminations +
   exclusion_confidence schema floor ≥90 (verified diagnosis_schema.json) + evidence citation.
5. **Keyword sensitivity CLOSED by exact computation**: re-scoring the frozen corpus under
   pre-revision keyword sets (git 221d061^) reproduces headlines exactly — Top-1 6/9, top-k 8/9
   under both sets (run: Temp/kw_sensitivity.mjs, grader logic replicated verbatim from
   zcode_direct_pipeline.mjs:373-390). Add sentence + commit-221d061 pin to C1.
6. **Fig 3(a)/Fig 4 captions describe pre-Round-6 colours** (R7#1/#2) + calibration capped bars
   pixel-identical to DET bars → hatch the capped sky bars; rewrite both captions to the
   sky/amber/hatch convention.
7. **Appendix A1/A2 under-filled floats** (R7#3): [!htbp] → [t].
8. **Step 3.5 vs Phase 5.5 mapping sentence** (R8#3); bare-LLM 2/3 controls note (R5#3, baselines.json
   note verified); audit record path docs/benchmark/AUDIT-2026-09-13.md cited (R8#4); Table 2 row
   clarifications (R6#2/#3); \mbox the three protocol state names (R7#5); Table 8 caption drop
   "(mode: recorded)" field-name implication (R5#2); Table 9 session dates from run-dir timestamps
   (R5#5); fig_tep pale-amber → standard amber (R7#3-S); mild font bumps fig_suite_matrix/fig_forest
   (R7#4-S).

## Declined (recorded for the response doc)
- Full §8 restructure / dedup passes (R8-S1/S2): proof-stage churn risk; reserved for production editing.
- Fig 2 right-to-left bottom row (R6-S4/R8-S6): TikZ restructure risk; caption already instructs the reading order.
- Fig 3(b) jitter at 100 (R5-S4): jitter would misrepresent deterministic values.
- Zenodo DOI: external action, tracked in data-availability.
