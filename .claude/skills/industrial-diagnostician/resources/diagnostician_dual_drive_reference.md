# Diagnostician — Dual-Drive Workflow Reference

> Reference file for `agents/diagnostician.md`. Load this when instructed to read the Dual-Drive reference during Phase 0.4 or Phase 1.

## Phase 0.4 — Parameter→Physics Mapping Template

When Loaded by Phase 0.4, read `resources/parameter_to_physics.json`:

```json
{
  "spindle_vibration_mm_s": {
    "governing_law": "ISO 10816-1 vibration severity classification",
    "causal_chains": [
      {"mechanism": "轴承磨损 → 旋转不平衡 → 振动↑ → 刀尖位移 → 表面粗糙度↑ → 尺寸偏差↑", "check_function": "check_vibration_threshold"},
      {"mechanism": "主轴过热 → 热膨胀 → 轴承间隙变化 → 振动↑", "check_function": "check_thermal_expansion"}
    ],
    "quantitative_check": "vibration_amplitude × inverse_tool_stiffness = tool_tip_deflection",
    "threshold_physics": "ISO 10816 Zone C (>4.5mm/s) — 超过此阈值时质量指数级下降",
    "competing_hypotheses": {
      "H1_bearing_wear": "振动与主轴温度强相关→轴承磨损同时导致振动和温升",
      "H2_imbalance": "振动与转速相关→旋转部件不平衡"
    }
  }
}
```

**Key insight**: This replaces manual physical reasoning. The mapping table provides the causal chains, equations, and competing hypotheses — you select, combine, and validate them against actual data evidence.

## Phase 0.5 — Pre-Computed Physical Checks Template

Read `anomaly_report.json.phyiscal_checks` (or `physics_check.json` if unavailable). Each check:

```json
{
  "thermal_expansion": {
    "conclusion": "THERMAL_COUPLING_DETECTED",
    "explanation": "Deviation co-varies positively with temperature (r=0.61) — thermal expansion is a plausible channel; quantify with the real α·L₀ from the ontology",
    "coupling_r": 0.61
  },
  "vibration_threshold": {
    "conclusion": "VIBRATION_CLIFF_DETECTED",
    "explanation": "Quality degrades >2× at vibration ~4.5mm/s",
    "cliff_threshold_mm_s": 4.5
  }
}
```

**Note**: thermal_expansion / energy_balance checks are DATA-DRIVEN coupling checks (no invented material constants). Quantitative ΔL/ΔT estimates appear only when the ontology supplies α·L₀ / m·Cp — treat their absence as a knowledge gap, not a failed check.

**Rule**: Do NOT manually re-compute these. If a check is INCONCLUSIVE, note it as a knowledge gap.

## Phase 1.1 — Quality Reset Analysis (from anomaly_report.json)

| `reset_classification` | Meaning | Root Cause Implication |
|------------------------|---------|------------------------|
| `RESET` | Quality drops significantly after component change | **Component IS the root cause** → tool, roll replacement works |
| `NO_RESET` | Quality unchanged after component change | **Component is NOT the root cause** → system-level issue |
| `WORSENED` | Quality got worse after component change | Improper setup or incompatible component |
| `INCONCLUSIVE` | Insufficient data before/after | Note as gap |

Document in R2 as: `Tool change T001→T002: NO_RESET (d=0.2, means 0.82→0.79) → System-level degradation.`

## Phase 1.2 — Anomaly-Onset Coincidence

| Classification | Meaning | Implication |
|----------------|---------|-------------|
| `POTENTIAL_CAUSE` | Parameter changed BEFORE quality anomaly | **Strong root cause candidate** — temporal precedence established |
| `CONCURRENT_CHANGE` | Changed simultaneously | Likely a correlate or co-effect, not a driver |
| Not in list | Did not change during anomaly | Cannot be the immediate cause |

Document in R2 as: `Anomaly at indices 450-520: spindle_vibration → PRECURSOR (d=3.2) → Vibration is causal driver`

## Phase 1.3 — Physical Check Conclusions

| Conclusion | Meaning | Use In Diagnosis |
|------------|---------|------------------|
| `THERMAL_COUPLING_DETECTED` | Deviation co-varies with temperature (r≥0.3) — expansion channel plausible | SUPPORT thermal hypotheses |
| `THERMAL_ANTI_CORRELATED` | Deviation moves AGAINST temperature — compensation/control, not passive expansion | Reject passive-expansion mechanism |
| `THERMAL_COUPLING_NOT_DETECTED` | No material coupling with temperature | Thermal expansion not the dominant channel |
| `ENERGY_COUPLED` / `ENERGY_ANTI_CORRELATED` / `ENERGY_DECOUPLED` | Power↔temperature coupling verdict (data-driven, no invented m·Cp) | SUPPORT / reject heat-input hypotheses |
| `VIBRATION_CLIFF_DETECTED` | Quality cliff at threshold value | Provide exact threshold in recommendations |
| `ARRHENIUS_NEGLIGIBLE` | Temperature too low for detectable chemical degradation | EXCLUDE temperature as primary mechanism |
| `FORCE_BALANCE_PLAUSIBLE` | Predicted force matches measured force | SUPPORT force/Wear hypotheses |
| `INCONCLUSIVE` | Check not run (missing data columns / unknown equipment class / unknown quality direction) | List as knowledge gap |
