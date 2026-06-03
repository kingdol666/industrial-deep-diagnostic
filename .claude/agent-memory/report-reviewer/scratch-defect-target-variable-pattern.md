---
name: scratch-defect-target-variable-pattern
description: BOPET scratch diagnosis revealed target variable inconsistency (scratch_count vs scratch_rate) as a recurring pipeline weakness
metadata:
  type: project
---

# Scratch Defect Target Variable Pattern

**Date**: 2026-06-03
**Run**: 202606031108498_lekai_scratch_defect

**Finding**: In BOPET scratch defect analysis, the pipeline mixed `scratch_count` (unnormalized) and `scratch_rate` (normalized per 100m) as target variables across different analysis stages. Simpson Paradox table used scratch_count (inflating global r from 0.31 to 0.49), while variance decomposition used scratch_rate.

**Why it matters**: scratch_count correlates with meters (r=0.30), confounding production volume with defect rate. The correct quality metric is scratch_rate. The inconsistency caused Spearman-Pearson divergence to be masked — scratch_count showed 0.52 divergence (Pearson=0.49, Spearman=-0.04) while scratch_rate showed only 0.08.

**How to apply**: For any defect count target variable, always normalize by exposure (length, time, area) before correlation analysis. The pipeline should enforce a single target variable across all analysis stages and auto-detect when raw counts vs rates are mixed.

**Related**: [[statistical-robustness-checks]]
