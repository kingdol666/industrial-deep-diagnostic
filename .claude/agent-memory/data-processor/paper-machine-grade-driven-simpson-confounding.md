---
name: paper-machine-grade-driven-simpson-confounding
description: Paper machine headbox: all process-quality correlations are grade-driven Simpson-like artifacts, not causal
metadata:
  type: project
---

# Paper Machine Headbox — Grade-Driven Simpson Confounding Confirmed

**Run**: 202606081510595_paper_machine_headbox  
**Date analyzed**: 2026-06-08

## Key finding

All strong process-quality correlations (|r| > 0.8) in this 91-day paper machine headbox dataset are driven by **between-grade differences** (GSM80/GSM100/GSM120 paper grades), not within-grade process instability. Within each individual grade, process-quality correlations are near-zero.

**Why**: The 3 paper grades have very different process setpoints (headbox pressure, fan pump speed, retention aid dosage). When aggregated, these setpoint differences create strong but spurious correlations with quality metrics (CD basis weight CV, formation index). This is confirmed via within-grade stratification (product_grade_analysis.json) and detrending (correlations attenuate 30-56% after removing linear trends).

**How to apply**: For future paper machine data with product grades, immediately stratify by grade before reporting any process-quality correlations. Aggregate-only correlations are misleading.

## Confirming evidence
- Within-grade correlations near-zero for ALL process-quality pairs
- Detrended r drops 30-56% from raw r (confirmed in statistical_warnings)
- 3 distinct grade clusters visible in scatter_grid.png  
- Headbox pressure has a +46.5% regime shift at mid-run (18.9→27.7 kPa) — probably a grade mix change
- No monotonic degradation over 91 days — process wear excluded

## Related memories
- [[cnc-simpson-paradox-rejected]] — different mechanism (Simpson rejected for CNC, confirmed for paper machine)
