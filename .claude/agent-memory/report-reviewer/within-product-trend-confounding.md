---
name: within-product-trend-confounding
description: PG31DS H1/H2 time-trend within single product group: both hypotheses collapsed after within-product detrending — 86.5% attenuation for TH005
metadata:
  type: feedback
---

# Within-Product Time-Trend Confounding

**Rule**: When the diagnosis relies on within-product correlations for a single product group (e.g., PG31DS, n=19), check within-product time trends by detrending against row/batch order within that specific product group — NOT just global detrending.

**Why**: In the BOPET Lekai scratch diagnosis (run 202606151602359), the COMPETING_SET {H1: TH005, H2: QUENCH_DELTA_T} relied entirely on PG31DS within-product correlations (r=-0.361 and r=+0.377). My independent detrending within PG31DS showed:

- H1/TH005: raw r=-0.361 → detrended r=-0.049 (86.5% attenuation — ZERO)
- TH005 itself had r=-0.826 with PG31DS batch order (systematic cooldown over 1 day)
- scratch_count had r=+0.407 with PG31DS batch order
- H2/QUENCH_DELTA_T: raw r=+0.377 → detrended r=+0.157 (58.3% attenuation), detrended Spearman=+0.109 (p=0.658 — NOT significant)
- QUENCH_DELTA_T itself had r=+0.660 with batch order

Meanwhile, torque variability params (W1C8B@PV1_std, W1C89@PV1_std) survived detrending with detrended Spearman=+0.554 (p=0.014) and +0.493 (p=0.032) — signals completely missed by the diagnosis.

**How to apply**: The validate_report.json only checked global trend confounding (and found none), missing the within-product time trends. Any time a single product group dominates the sample (here PG31DS 19/55=35%), within-product detrending is mandatory. The `time_sorted=null` in validate_report should have been a red flag — no time validation was performed at all.

This is a more insidious variant of [[time-trend-confound-within-model]] — here it's within a single product group over a short time window (1 day), not across the global timeline.

Related: [[time-trend-confound-within-model]], [[cross-model-consistency-is-not-causal]]
