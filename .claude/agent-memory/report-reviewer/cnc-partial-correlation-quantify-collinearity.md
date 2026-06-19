---
name: cnc-partial-correlation-quantify-collinearity
description: CNC simulateData spindle_temp and spindle_vibration r=0.967; partial correlation temp|vib=0.8515 vs raw r=0.9908; 14% indirect path via shared covariance was not quantified in report
metadata:
  type: feedback
---

CNC simulateData: H2 (spindle_temp -> dimensional_deviation) claimed r=0.9908 and was endorsed as DETERMINED. Independent partial correlation controlling for spindle_vibration showed temp|vib partial r=0.8515, and vib|temp partial r=0.6226. The raw r=0.9908 overstates temp's unique explanatory power because temp and vibration share 93.5% variance (r=0.967). About 14% of temp->dim_dev effect is indirect via vibration covariance.

**Why:** When two predictor variables in a diagnostic have |r|>0.95 and both correlate >0.97 with the target, the individual causal claims are weaker than their raw correlations suggest. The report's five-factor scoring already deducted 3 points in absence_of_confounds for this but didn't surface the partial correlation explicitly.

**How to apply:** In any diagnosis where the top 2 predictors have mutual |r|>0.8 AND both correlate with target >0.9, the pipeline must compute and report partial correlations. If the partial r drops below 0.7 from a raw r>0.9, flag as potential colinearity confound. Add automatic partial_corr function in stats_analysis.py.

Related memory: [[h6-h7-collinearity-audit-pattern]] — same principle applied to BOPET sensor collinearity.
