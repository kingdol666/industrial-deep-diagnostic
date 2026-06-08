---
name: bopet-filter-pressure-sign-reversal
description: BOPET scratch vs filter pressure shows sign reversal — higher pressure correlates with fewer scratches (r≈-0.19), contradicting the physics expectation that blocked filters increase impurities
metadata:
  type: reference
---

In BOPET scratch diagnosis (202606081100505), the main filter pressure (F_PS002 pre-filter, F_PS003 post-filter) correlates negatively with scratch_count (r≈-0.19), contradicting the expected positive correlation (higher pressure = more filter blockage = more impurities = more scratches). This sign reversal is a diagnostic signal: either (a) pressure is higher during normal steady-state operation while scratches come from transient events, (b) pressure co-varies with product model (some models run higher pressure and lower scratch), or (c) the impurity→scratch mechanism is not dominant in this dataset. The global correlation landscape is uniformly weak (|r|<0.25 for all parameters vs scratch), consistent with Simpson's Paradox masking through model confounding.

**Why:** Contradicted physics expectations are the strongest diagnostic signals per context-builder protocol §4.3. This specific contradiction tells the Diagnostician that filter state is likely NOT the root cause, saving analysis effort.

**How to apply:** When the Data Processor finds negative correlation where physics predicts positive, flag for model-stratified analysis. The Diagnostician should deprioritize filter-related hypotheses unless within-model evidence supports them.
