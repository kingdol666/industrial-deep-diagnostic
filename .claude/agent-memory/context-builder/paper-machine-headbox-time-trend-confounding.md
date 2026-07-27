---
name: paper-machine-headbox-time-trend-confounding
description: Paper machine headbox data shows extreme time-trend confounding — 8 parameters co-trend over 3 months (|r(day)|>0.7), driving spurious |r|>0.8 correlations. Fan_pump_speed_rpm has r(day)=0.91 but r=0.11 with flow, violating pump affinity law.
metadata:
  type: project
---

Paper machine headbox (paper_machine_headbox) diagnostic session 202607271128116: the dominant diagnostic signal is **time-trend confounding** across Oct-Dec 2025. Parameters (headbox_pressure_kPa, fan_pump_speed_rpm, white_water_consistency_pct, retention_aid_dosage_ppm, stock_temp_C, cd_basis_weight_cv_pct, formation_index, strength_rel_pct) all show strong temporal correlations (|r(day)| > 0.7), creating spurious cross-correlations (|r| > 0.85) that are primarily trend-driven. Three product grades (GSM80/100/120) operate at non-overlapping parameter setpoints — grade is the dominant confounder ([[bopet-scratch-model-confounds-all|analogous to BOPET model confound]]).

**Why:** Stacked seasonal effects (stock_temp dropping 47->39C, r=-0.61) reduce chemical efficiency and increase viscosity, triggering operator compensation (increasing pressure, pump speed, retention aid). This creates a classic Pitfall 3 scenario where multiple variables share a clock, not physics. Grade confound means all cross-grade analyses risk Simpson's Paradox.

**Key discrepancy 1:** fan_pump_speed_rpm r(day)=0.91 but r=0.11 with approach_flow_lpm — violates centrifugal pump affinity law (Q proportional to n). System resistance increased significantly, or flow is regulated via dilution valve not pump VFD.

**Key discrepancy 2:** vacuum_pump2_kPa range 0.7-82.9 kPa far exceeds normal range (30-70 kPa). 0.7 kPa is near-zero vacuum suggesting seal leak, pump degradation, or intermittent cleaning cycles.

**Key discrepancy 3:** moisture_pct constant at 3.000% (3236/3238 points) — confirmed as pseudo-signal (setpoint target or frozen sensor), not actual measurement.

**Key discrepancy 4:** J/W ratio mean identical across all three grades (1.0207) — DCS precisely controls J/W as independent target, decoupling it from grade-based pressure/speed variation.

**How to apply:** Diagnostician must (1) stratify by grade before any analysis, (2) detrend by day to remove seasonal confound, (3) exclude moisture_pct from analysis, (4) treat vacuum_pump2 extremes as equipment anomaly candidate, (5) note that J/W ratio identical across grades means formation_index differences (if any) cannot be explained by J/W alone — look at temp, retention aid, and turbulence effects.
