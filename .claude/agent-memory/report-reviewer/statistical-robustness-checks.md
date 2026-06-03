---
name: statistical-robustness-checks
description: validate_report SERIOUS_CONCERNS should be surfaced in report text, not summarized as "all passed"
metadata:
  type: feedback
---

# Statistical Robustness Findings Must Be Surfaced

**Rule**: When validate_report.json has `overall_validity: "SERIOUS_CONCERNS"`, the diagnostic report must explicitly state this in the body text. "All checks passed" is misleading.

**Why**: In the BOPET scratch run, validate_report flagged outlier-driven correlations (W1C86_std r drops from 0.49 to -0.21 after outlier removal), Spearman-Pearson divergence of 0.52, and multiple testing issues. The report summarized these as "all checks passed", hiding serious robustness concerns from the reader.

**How to apply**: The Reporter agent should extract the overall_validity field and any SERIOUS/CRITICAL findings from validate_report.json and include them as a dedicated subsection in the report. The wording should match the severity — "SERIOUS_CONCERNS" should not become "passed".

**Related**: [[scratch-defect-target-variable-pattern]]
