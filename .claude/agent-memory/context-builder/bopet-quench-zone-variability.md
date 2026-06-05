---
name: bopet-quench-zone-variability
description: BOPET quench zone (TH013-015) shows 5-17x higher batch-to-batch temperature variability vs stretch zone, with one clear outlier batch
metadata:
  type: reference
---

In the BOPET scratch run data, quench zone rolls 13-15 (MD_TH013-015) have across-batch temperature std of 0.34-0.37°C, compared to stretch zone std of 0.02-0.06°C. A single outlier batch (H2652620, the 2nd batch chronologically) shows temperature ~33°C vs the normal ~36°C. This batch has scratch_count=2 (below average), so the anomaly may not directly explain scratch defects, but it indicates the quench cooling system is less stable than the stretch heating system.

**Why:** Quench zone stability matters for film crystallinity and dimensional consistency. The high variability here vs stretch zone is a qualitative signal of equipment/system behavior.

**How to apply:** Data Processor should check if this outlier is a sensor glitch, start-up transient, or genuine cooling event. The Diagnostician should note quench stability as a secondary consideration since scratch correlation is weak (r<0.1 for TH013-018).
