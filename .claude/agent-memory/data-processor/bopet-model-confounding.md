---
name: bopet-model-confounding
description: BOPET scratch analysis showed product model confounding is the dominant effect - within-model W1C80 torque correlations dramatically differ from global
metadata:
  type: project
---

**Finding**: In BOPET MD stretch scratch diagnosis, product model (8 grades) is the strongest confounder. Global W1C80@PV1_std (roll 5 torque std) vs scratch_count shows r=0.45, but within-model analysis reveals:
- FP21 (high-scratch model, n=19): r=0.935
- PG31DS (main model, n=67): near-zero correlation
This is a Simpson-like confounding pattern: aggregate correlation is diluted by model mixing, not reversed. The key diagnostic implication: 5th roll (preheat-to-stretch transition point) torque stability matters specifically for FP21, not universally.

**Why**: Product models differ in thickness, additive配方, speed setpoints (W1C40 CV=23%). Within-model variability is much lower than between-model. Aggregate stats conflate both.

**How to apply**: Always check within-model correlations when `model` grouping column exists. Per-model time-order trends (PG31DS r=0.41, PG32B r=0.69 increasing) are more diagnostic than global trends.
