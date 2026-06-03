---
name: bopet-md-stretching-scratch-diag-20260603
description: BOPET film MD stretching scratch defect diagnosis — 55 batches, 18 temperature rolls, preheat/stretch/quench stages
metadata:
  type: project
---

# BOPET MD Stretching Scratch Diagnosis (2026-06-03)

## Process
- BOPET film longitudinal stretching (MD Stretching) at leKai line
- 18 rolls organized in 3 thermal stages: preheat (rolls 1-5, ~75-76C, near PET Tg), stretch (rolls 6-11, ~82C, above Tg), quench (rolls 12-18, ~31-35C, well below Tg)
- Scratch defect count per batch as quality target

## Key Discovery
- Data is batch-level aggregate (55 batches), each parameter has _mean / _std / _min / _max columns (182 total columns)
- R2 pre-checks revealed scratch correlates with: preheat temperature (negative), entry speed (positive), quench start temperature (positive)
- Product model type is a strong confounder (11 model types, very different scratch baselines)
- One extreme batch (FP41 model) has 76 scratches, severely skewing distributions

## Ontology Structure
- Built ontology with 44 base process parameters + statistical variants, all mapped to physical meaning from parameter_mapping.json
- 4 process stages: melt_delivery, preheat, stretch, quench (mapped to 18 rolls)
- 13 relationships documented connecting temperature/speed/torque to scratch_count

## Notes for Future Sessions
- RAG knowledge builder skill was invoked but hadn't completed by the time context-builder finished → may need to check `00_input/rag_ontology_draft.json` later
- Strongest pre-check signals: MD_TH005 (r=-0.25), MD_TH003 (r=-0.24), MD_TH006 (r=-0.24) with scratch_count
- Speed correlation (r=0.21) is confounded by temperature (higher speed = less heating time)
- Model stratification is essential — the 11 product types have very different baselines
