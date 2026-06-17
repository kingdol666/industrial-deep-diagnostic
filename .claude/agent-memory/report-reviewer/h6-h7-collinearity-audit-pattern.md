---
name: h6-h7-collinearity-audit-pattern
description: Report-reviewer audit found H6/H7 overclaimed as "independent corroboration" — shared 37.8% detrended variance with non-significant partial correlations. Pattern: same mechanism, adjacent sensors, one drive system → co-variation is system-level, not independent.
metadata:
  type: project
---

BOPET scratch Round 2 audit (202606151602359) revealed a persistent over-claiming pattern: H6(W1C8B_std roll#16) and H7(W1C89_std roll#14) were presented as "independent corroborating signals" when independent Python verification showed:
- Detrended r(W1C8B_std, W1C89_std) = 0.615 (37.8% shared variance)
- Partial correlation H6|H7: r=0.316, p=0.202 (NOT significant)
- Partial correlation H7|H6: r=0.197, p=0.434 (NOT significant)
- H7 adds only ΔR²=0.030 beyond H6 alone in regression
- Both rolls share the same drive system → torque variability on one roll mechanically transmits to the other

**Why:** Multi-sensor torque_std parameters on adjacent rolls in the same drive system are NOT independent measurements — they capture the same system-level torque dynamics. The pipeline should compute partial correlations before claiming independence.
**How to apply:** In future diagnoses, whenever two parameters share mechanism + physical proximity + drive system, flag the "two independent signals" claim and demand a partial correlation check. Two p<0.05 signals on adjacent roll torque_std are still just one signal from the drive system.

Related: [[cross-model-consistency-is-not-causal]], [[partial-correlation-independence-check]]
