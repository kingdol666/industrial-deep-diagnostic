---
name: bopet-parameter-mapping-coverage
description: parameter_mapping.json covers all 44 BOPET MD stretch parameters directly (18 temps, 18 torques, 2 speeds, 2 extruder speeds, 4 filter pressures) — verified by cross-referencing XLSX mapping against actual CSV data
metadata:
  type: reference
---

In BOPET scratch diagnosis runs, `data/lekaiData/parameter_mapping.json` provides verified physical meanings for all 44 process parameters. This file was cross-verified against XLSX mapping and actual `aligned_multidefect.csv` data. All parameters have `physical_meaning_confidence: KNOWN`. No RAG fallback needed for parameter identification.

**Key structural decisions from ontology rebuild (run 202606090216454):**
- Torque parameters (W1C7C-8D@PV1) are continuous sensor measurements, NOT events — they belong in `process_parameters`, not `events`
- Filter pressures (F_PS002-006@PV1) and extruder speeds (W1C00/01@PV1) are also measurements, not control variables
- The 18-roll MD stretcher has 3 distinct thermal zones: preheating (rolls 1-5, ~75-77°C), stretching (rolls 6-11, ~82-84°C), quenching (rolls 12-18, ~30-36°C)
- MD_DRAW_RATIO (~3.08) is extremely stable (CV~1%), so individual speed parameters may correlate more with defects than the ratio

**Why:** The initial auto-generated ontology misclassified 18 torque parameters as events and filter pressures as control variables. All 44 are continuous process measurements from the MD stretching line.

**How to apply:** When building BOPET ontology, always check the parameter categorization. Use stage_ref (preheating/stretching/quenching) and equipment_ref to group parameters.
