---
name: pearson-spearman-outlier-sensitivity-check
description: When validate_report.json has empty spearman_divergence, pipeline fails to detect outlier-driven correlations. Always run independent Pearson-Spearman comparison on key claims.
metadata:
  type: feedback
  related_memories: [[validate-report-serious-concerns-must-block]]
---

When the pipeline's `validate_report.json` has `spearman_divergence: []` (empty array), it means the Pearson-Spearman divergence check was skipped for ALL parameters. This is a pipeline-level statistical validation failure.

**What happened**: In the BOPET scratch diagnosis (run 202606081100505), the diagnostician claimed FP21 W1C80_std vs scratch had r=0.935. The pipeline's physics_check.json marked it as MODERATE. Independent verification found Spearman rho=0.2461 (divergence 0.689 >> threshold 0.15). The entire H1 hypothesis was driven by a single batch.

**Why**: The validate_report's spearman_divergence was empty, so no automated flag existed. The physics_check only checked temperature parameters for OUTLIER_SENSITIVE but not torque parameters.

**How to apply in future reviews**:
1. Always check if validate_report.json spearman_divergence is non-empty. If empty, flag it as a FATAL pipeline validation gap.
2. For ANY claim with Pearson |r| > 0.4 in highly skewed data (skewness > 5), independently compute Spearman rho.
3. When Pearson-Spearman divergence > 0.15, the claim is OUTLIER_SENSITIVE regardless of the pipeline's stated status.
4. For skewed target variables (scratch_count, defect counts), prefer Spearman rank correlation as primary metric.
5. Single-batch-driven correlations: if removing <=2 extreme batches collapses the correlation to near-zero, it is an artifact.
