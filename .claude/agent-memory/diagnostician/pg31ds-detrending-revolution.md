---
name: pg31ds-detrending-revolution
description: PG31DS product-internal detrending collapsed H1/H2 and revealed W1C8B/W1C89 torque variability as the strongest surviving scratch predictors
metadata:
  type: project
---

# PG31DS Product-Internal Detrending Revolution

**What changed**: The preflight audit (optimizer_preflight.md) revealed that the original diagnosis's competing set {H1: TH005, H2: QUENCH_DELTA_T} relied on raw (non-detrended) correlations within PG31DS, which were heavily contaminated by shared product-internal temporal trends.

**Why**: The pipeline's validate_report.json only performed global detrending across all 55 batches, missing product-internal trends entirely. PG31DS's 19 batches were produced over ~24 hours, during which multiple parameters drifted systematically:
- TH005: r_trend=-0.826 (cooled ~0.05°C/day)
- QUENCH_DELTA_T: r_trend=+0.660 (increased ~0.13°C/day)
- W1C8B_std: r_trend=+0.856 (torque variability increased strongly)
- scratch_count: r_trend=+0.407 (also trended upward)

Any pair of trending parameters produced spurious correlations.

**Detrended results (PG31DS-only)**:
- H1 (TH005): raw r=-0.361 → detrended r=-0.049, Spearman rho=-0.004 (p=0.989) — **STATISTICALLY DEAD**
- H2 (QUENCH_DELTA_T): raw r=+0.377 → detrended Spearman rho=+0.109 (p=0.658) — **NOT SIGNIFICANT**
- H6 (W1C8B@PV1_std, roll#16): detrended Spearman rho=+0.554 (p=0.014) — **STRONGEST SURVIVING SIGNAL**
- H7 (W1C89@PV1_std, roll#14): detrended Spearman rho=+0.493 (p=0.032) — **SECOND STRONGEST**

**How to apply**: All future BOPET scratch diagnoses MUST perform product-internal detrending before forming causal hypotheses. The pipeline should be enhanced to add per-product detrending as a validation step. Spearman rho is the authoritative metric for skewed variables (scratch_count, torque_std, QUENCH_DELTA_T).

**Related**: [[fp21-spearman-correction]], [[quality-check-resolution]]
