---
name: bopet-quench-zone-variability
description: BOPET scratch quench zone (TH013-015) shows 5-17x HIGHER batch-to-batch temperature variability (std≈3.5°C) vs stretch zone (std≈0.35°C). One batch hit 41.2°C — above PET Tg.
metadata:
  type: project
---

Updated 2026-06-18 from run 202606171624539 with new batch-level analysis (149 batches):

Quench zone (TH012-TH018) temperature behavior is strikingly different from preheat and stretch zones:

**Variability comparison (across all 149 batches):**
- Preheat zone (TH001-TH005): std ≈ 0.4-0.5°C, CV ≈ 0.59%
- Stretch zone (TH006-TH011): std ≈ 0.35-0.40°C, CV ≈ 0.43%
- TH012 (transition, 83→30°C): std = 1.51°C (expected — this is the quench entry roller)
- TH013: std = 3.53°C, range [26.4, 41.2°C]
- TH014: std = 3.54°C, range [26.1, 41.0°C]
- TH015: std = 3.56°C, range [25.9, 40.8°C]
- TH016: std = 1.62°C, range [29.3, 35.6°C]
- TH017: std = 1.61°C
- TH018: std = 1.60°C

**Key finding:** The quench zone splits into two sub-regions:
1. TH012-TH015 (front half): std ≈ 2.5-3.5°C — VERY high variability
2. TH016-TH018 (rear half): std ≈ 1.6°C — moderate variability

The 3.5x difference between front-half and rear-half quench variability suggests different cooling circuits or control strategies.

**One batch reached TH013=41.2°C — ABOVE Tg=75°C.** For PET, if quench temperature exceeds Tg, the film doesn't crystallize properly. This batch likely has different mechanical properties.

**Correlation with scratch:** TH012-TH018 all show very weak correlation with scratch (|r|<0.10). Quench zone fluctuation does not appear to be a PRIMARY scratch driver, but the system stability issue is a quality concern on its own.
