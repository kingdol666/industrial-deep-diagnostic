---
name: heat-exchanger-scaling-confounds
description: HX scaling diagnosis — cold inlet temp masks approach temp trend; pump compensation; unit baselines differ 3x
metadata:
  type: reference
---

Rule: In heat exchanger scaling diagnosis, three critical confounders must be checked before interpreting trends:

1. **Cold inlet temperature masks approach temperature** — `approach_temp = T_hot,out - T_cold,in` is a mechanical identity. A 1 degC rise in cold inlet mechanically drops approach temp 1 degC, independent of fouling. In the eval_heat_exchanger_scaling case, HX-03 and HX-04 showed DECREASING approach temp while all other scaling indicators said fouling was active — fully explained by rising cold inlet. Correct approach temp by subtracting cold inlet delta before trending.

2. **Pump speed compensation** — When pump speed is actively controlled (VFD), increasing pump speed to maintain flow as scaling raises DP means raw DP trend UNDERSTATES scaling severity. The pump speed trend itself becomes a scaling indicator. For centrifugal pumps, check: flow vs pump_speed correlation weakening over time signals rising system resistance.

3. **5x baseline differences between units** — HX-01 through HX-05 had DP baselines ranging 0.93-2.53 bar (2.7x) and pump speeds 65-88%. Mixing without stratification creates Simpson's Paradox risk. Always stratify by unit_id.

Key physics: DP follows 5th-power law (Delta p proportional to d^-5), HTC follows linear thermal resistance (1/U_f = 1/U_c + R_f). DP is the more sensitive early indicator — even sub-mm scale produces measurable DP rise.

Why: The eval_heat_exchanger_scaling dataset (2026-06-08) demonstrated all three confounds simultaneously. The approach-temp paradox was the strongest diagnostic signal — it revealed the confound, not a contradiction of fouling.

How to apply: When analyzing any multi-unit heat exchanger fouling data, (1) separate by unit first, (2) correct approach temp for cold inlet, (3) treat pump speed trend as a scaling indicator, not just a control variable.
