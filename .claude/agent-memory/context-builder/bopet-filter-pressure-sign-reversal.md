---
name: bopet-filter-pressure-sign-reversal
description: BOPET scratch vs F_PS003 (filter after-pressure) shows r≈-0.19 overall but sign reverses within FG22 (r=+0.42) and PG32D (r=+0.41). Simpson's Paradox confirmed — aggregate correlation unreliable.
metadata:
  type: project
---

Updated 2026-06-18 from run 202606171624539 (149 batches, 8+ models):

F_PS003 (main filter after-pressure) vs scratch correlation:

**Aggregate (all 149 batches):** r = -0.189 (weak negative — consistent with physics: lower pressure = more scratches)

**Stratified by model:**
- FG22 (n=6): r = +0.421 — SIGNS REVERSED
- PG32D (n=16): r = +0.406 — SIGNS REVERSED
- PG32DS (n=9): r = +0.449 — SIGNS REVERSED
- FP21 (n=19): r = -0.319 — consistent direction
- PG31DS (n=67): r = +0.112 — near zero, slightly reversed

**Interpretation:**
This is a textbook Simpson's Paradox: the aggregate correlation sign is driven by between-model differences (lower-scratch models run at higher F_PS003), but within each model the relationship is weak or reversed.

**Diagnostic implication:** Filter pressure (F_PS003) is NOT a useful predictor of scratch at the within-model level. The filter clogging hypothesis is NOT supported by this data. Previous memory's claim that "contradicting physics expectation" is the strongest diagnostic signal was tested and confirmed across three independent data snapshots.

**Why:** The previous memory emphasized sign reversal as a diagnostic signal. The 20260618 update with MORE data (149 batches, broader model coverage) confirms the pattern is NOT a stable causal signal but is entirely model-driven. This is itself diagnostic: it tells us that between-model differences dominate within-model effects for pressure parameters.
