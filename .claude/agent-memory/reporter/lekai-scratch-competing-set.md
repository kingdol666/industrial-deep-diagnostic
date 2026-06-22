---
name: lekai-scratch-competing-set
description: "BOPET MD Scratch (2026-06-22): COMPETING_SET diagnosis, product confounding dominates, only W1C8C @PV1_mean shows consistent cross-product sign"
metadata:
  type: project
---

**Run**: 20260622_lekai-scratch | **Scene**: BOPET MD Scratch | **Date**: 2026-06-22

**Key lesson**: 55 batches / 3 days / no time sort -- even well-executed statistics (Simpson, outlier sensitivity, stratification) cannot compensate for insufficient data span. Product model (7 levels) was the dominant confounder; highest Pearson r (0.487 torque std) collapsed to |r|<0.25 after stratification. Only W1C8C@PV1_mean (roll 17 quench torque mean) showed consistent negative sign across 4 major products (rho range -0.613 to -0.329). This is the archetypal "honest COMPETING_SET" -- the diagnostician correctly refused to pick a false single root cause.

**Why**: Limited dataset (55 batches, 3-day window, batch-aggregated, no time ordering) made it impossible to distinguish product confound (H3, 60 conf) from quench torque level (H1, 55 conf) from PG31DS torque std (H2, 40 conf).

**How to apply**: For future runs with similarly small multi-product datasets, pre-emptively flag product-stratified analysis as mandatory from Step 0. The top-correlation parameters will be BETWEEN_PRODUCT_ONLY artifacts; W1C8C@PV1_mean pattern (consistent sign across products despite weak magnitude) should be checked as a habitual candidate.
