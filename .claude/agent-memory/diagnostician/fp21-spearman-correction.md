---
name: fp21-spearman-correction
description: FP21 model W1C80_std vs scratch correlation corrected from Pearson r=0.935 to Spearman rho=0.2504 — outlier-driven artifact
metadata:
  type: reference
---

In the BOPET scratch diagnosis (run 202606081100505_BOPET_scratch_diagnosis), the FP21 within-model correlation between W1C80_std (5th roller torque std) and scratch_count was originally reported as Pearson r=0.935 (n=19, p significant). A repair iteration computed the Spearman rank correlation and found rho=0.2504 (p approx 0.30, not significant), with a Pearson-Spearman delta of 0.6846 far exceeding the 0.15 threshold. Investigation revealed that a single extreme leverage point (W1C80_std=16.32, scratch=6925) drove the entire Pearson correlation; removing it dropped Pearson to 0.326. The validate_report.json had flagged both W1C80_std (skewness=3.0) and scratch_count (skewness=8.8) as SPEARMAN_RECOMMENDED, but this warning was not heeded in the original diagnosis.

**Impact**: H1 confidence was reduced from 55 (MEDIUM) to 27 (LOW). H1 was downgraded from ACTIONABLE_HYPOTHESIS to PLAUSIBLE_HYPOTHESIS. The diagnosis shifted from "FP21 has a strong torque-scratch link" to "no model has a reliable within-group process-quality association; model baseline (H3, 60) is the dominant driver."

**Why**: Spearman must always be reported alongside Pearson when validate_report flags SPEARMAN_RECOMMENDED. Heavy skew + single leverage points can produce Pearson r > 0.9 with no real monotonic association.

**How to apply**: In BOPET or any heavily-skewed thin-film scratch diagnosis, always cross-check within-group Pearson with Spearman before claiming model-specific correlations. The `feature_summary.json` spearman_correlations section already contains global Spearman values, but within-model Spearman requires custom computation from the full dataset.
