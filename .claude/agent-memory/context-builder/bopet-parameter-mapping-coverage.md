---
name: bopet-parameter-mapping-coverage
description: parameter_mapping.json covers all 44 BOPET MD stretch parameters comprehensively. This run (20260617) uses 149-batch aligned data with 184 columns (4 stats per parameter: mean/std/min/max).
metadata:
  type: reference
---

BOPET scratch run 202606171624539 uses 149-batch aligned data. Key difference from previous runs: aligned_scratch_process_full.csv has 184 columns including mean/std/min/max variants of each parameter.

**Data file structure:**
- `aligned_scratch_process_full.csv` — 149 rows, 184 columns (9 meta + 175 stats: 44 params x 4 stats = 176 total, minus 1 with no std)
- `merged_process_data.csv` — 8640 rows, 45 columns (1 time + 44 params), 30-sec interval, covering 2026-05-07~05-10
- `scratch_defects.csv` — 1729 defect records by roll/batch

**Column naming convention:** `ParameterName_stat` where stat ∈ {mean, std, min, max}
Example: `MD_TH001@PV_mean`, `MD_TH001@PV_std`, `MD_TH001@PV_min`, `MD_TH001@PV_max`

**44 process parameters** (same as before, all verified):
- 18 temperatures (MD_TH001-018@PV)
- 18 torques (W1C7C-8D@PV1)
- 2 speeds (W1C40@PV1, W1C4B@PV1)
- 2 extruder speeds (W1C00@PV1, W1C01@PV1)
- 4 filter pressures (F_PS002-006@PV1, F_PS005-006@PV1)

**NEW: 3 derived parameters added to ontology** (from parameter_mapping.json):
- `MD_DRAW_RATIO` = W1C4B/W1C40 ≈ 3.08 (stable, CV~1%)
- `MF_FILTER_DELTA_P` = F_PS002 - F_PS003 ≈ 6.76 bar
- `SF_FILTER_DELTA_P` = F_PS005 - F_PS006 ≈ 4.8 bar

**Torque profile confirmed (from 149 batches):**
- R1 = -41.4 (negative: passive drag roll) — expected
- R2-R5 = 7.2-47.7 (positive: active preheat drives)
- R6-R10 = 6.1-57.4 (positive: active stretch)
- R11 = -67.7 (negative: tension anchor) — expected
- R12-R18 = 4.1-52.6 (positive: quench transport, small values at exit)

**Quench zone front half std=3.5°C** is the highest variability parameter group in the entire dataset. See bopet-quench-zone-variability.md.
