---
name: paper-machine-headbox-time-trend-confounding
description: Paper machine headbox data shows extreme time-trend confounding — 8 parameters co-trend over 3 months (|r(day)|>0.7), driving spurious |r|>0.8 correlations. Fan_pump_speed_rpm has r(day)=0.91 but r=0.11 with flow, violating pump affinity law.
metadata:
  type: project
---

Paper machine headbox (paper_machine_headbox) diagnostic session 202606081510595: the dominant diagnostic signal is **time-trend confounding** across Oct-Dec 2025. Eight parameters (headbox_pressure_kPa, fan_pump_speed_rpm, white_water_consistency_pct, retention_aid_dosage_ppm, stock_temp_C, cd_basis_weight_cv_pct, formation_index, strength_rel_pct) all show strong temporal correlations (|r(day)| > 0.7), creating spurious cross-correlations (|r| > 0.85) that are primarily trend-driven.

**Why:** Stacked seasonal effects (stock_temp dropping 47->39C, r=-0.61) reduce chemical efficiency and increase viscosity, triggering operator compensation (increasing pressure, pump speed, retention aid). This creates a classic Pitfall 3 scenario where multiple variables share a clock, not physics.

**Key discrepancy:** fan_pump_speed_rpm r(day)=0.91 but r=0.11 with approach_flow_lpm — violates centrifugal pump affinity law (Q proportional to N). System resistance likely increased significantly, or pump performance degraded.

**How to apply:** Diagnostician must treat the high correlations as trend-confounded until detrended. The root cause is likely a cascade: seasonal temp drop -> viscosity increase -> retention efficiency loss -> operator compensation loop -> all parameters drifting together. Also note moisture_pct is constant (3.000±0.00035, effective setpoint), and vacuum_pump2 has 12 intermittent anomaly points scattered across grades/dates (not a single failure event).
