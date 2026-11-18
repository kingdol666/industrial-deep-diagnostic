# Run Modes, Step Budgets & Efficiency (moved verbatim from SKILL.md)

> The two-mode table and `run_config.run_mode` authority stay in `SKILL.md` §Run Modes. The Step Turn Budgets
> table is in `references/orchestration-steps.md` (with the HARD_BUDGET enforcement rule in `SKILL.md` §Dispatch).

**fast vs full — what is cut (reasoning core untouched: ontology-first, competing-hypotheses exclusion, four-condition causality, judge gate, final physical audit all stay)**:

| # | Cut in fast | Rationale | Saves |
|---|-------------|-----------|:-----:|
| 1 | Step 2P separate pre-profile agent NOT dispatched — data-processor runs Phase 0-1 in-process (parallel pre-profile only for >20K rows) | separate agent = protocol re-read + duplicate probing for small data | ~8 min |
| 2 | Step 3.5 VLM: only CRITICAL-priority plots, cap 4; skip entirely if no vision model | VLM is L4 evidence, judge discounts it anyway | ~8 min |
| 3 | Step 5b pre-report audit SKIPPED — CP-8 final audit remains the sole physical gate | pre-audit + final audit overlap heavily on small runs | ~13 min |
| 4 | Plot budget ≤8 (trend overlay / dual-axis compensation / stratified scatter / CCF window / correlation robustness / causal evidence + 2 free) | 18 plots burned 12 min; 6 carry the reasoning | ~10 min |
| 5 | Diagnostician reuses upstream statistics verbatim (marked `[reused]`), computes only discriminative tests | upstream already computed global/detrended/within-group r, Granger, change-points | ~10 min |
| 6 | Report embeds ≤8 key figures | smaller report, faster HTML | ~3 min |
| 7 | RAG: single attempt, 60s timeout, then `parameter_to_physics.json` fallback | 502 retry loops burned minutes | ~2 min |

Same 80-row fieldtest scene (2026-10-13): full-mode measured ≈115 min; fast-mode projection ≈35-45 min. fast-mode conclusion parity is enforced by the unchanged judge gate (≥90) + CP-8 final audit — not by skipping evidence, only by skipping redundant passes.

---

## Efficiency — Parallel Execution

- No data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; if partially usable, keep moving forward