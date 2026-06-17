---
name: fp21-double-detrend-pearson-spearman-divergence
description: FP21 cross-product W1C8B_std-scratch detrended Pearson=-0.057 vs Spearman=+0.406 — direction and significance are metric-dependent
metadata:
  type: feedback
---

In FP21 (n=10, 80% transitional batches), cross-product detrended W1C8B@PV1_std vs scratch produced Pearson r≈0 and Spearman rho≈+0.406 (p=0.244 non-significant). This Pearson-Spearman divergence was not flagged in the diagnosis — it simply reported the favorable Spearman value without noting the metric-dependence. When Pearson and Spearman disagree this strongly at n=10 (both detrended), the "correlation" is fundamentally a rank-sorting artifact of a few high-leverage pairs, not a genuine monotonic relationship. This is compounded by FP21 having only ~2-3 steady-state-equivalent batches (80% transitional).

**Why:** In small samples with heavy skew (W1C8B_std skew=2.9, scratch skew=2.4), Pearson-Spearman divergence >0.4 is a red flag. One metric showing zero while the other shows moderate correlation means the relationship is not robust — it's an artifact of how ranks map onto a sparse 10-point distribution with a few high-value pairs.

**How to apply:** When cross-product correlations are used to support "direction correct" claims, check BOTH Pearson and Spearman. If they diverge by more than 0.3 in absolute value, flag the cross-product validation as UNRELIABLE regardless of which metric is favorable. Also check n_effective for transitional batches.

Related: [[partial-correlation-independence-check]]
