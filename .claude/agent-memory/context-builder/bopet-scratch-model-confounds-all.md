---
name: bopet-scratch-model-confounds-all
description: Product model (grade) is the dominant confounder in BOPET scratch diagnosis — 8 models with different speed setpoints and scratch baselines cause Simpson's Paradox
metadata:
  type: reference
---

In BOPET MD scratch diagnosis (run 202606050623599_bopet-scratch-diagnosis), the `model` column (8 product grades) confounds every parameter-defect correlation. Aggregate correlations (e.g., r=0.21 for speed vs scratch) reverse sign within some models. Key data: PG31DS runs at 11.3 m/min with scratch_mean=9.47; PG32M runs at 19.6 m/min with scratch_mean=4.75 — slower product has higher scratch mean, contradicting aggregate positive correlation. Speed, torque, and temperature all co-vary with model. The Data Processor and Diagnostician MUST stratify all analyses by model.

**Why:** Different product grades have fundamentally different recipe setpoints AND different defect baselines — this is the most common confounder in film production per process_knowledge_base.md.

**How to apply:** Any diagnosis of BOPET scratch must start with model-stratified analysis. The `scratch_count_by_model` breakdown: PG22C(0.83) < PG32B(4.20) < PG32M(4.75) < PG31DS(9.47) < FP21(15.50) < PG32D(25.67) < FP41(40.0). The small n for some models (PG32D=3, FP41=1) means their uncertainty is high.
