#!/usr/bin/env python3
"""
physics_check.py — Automated Physical Feasibility Check Engine

Reads cleaned data, ontology, and feature summary to perform quantitative
physical verification of hypothesized causal relationships.

The Diagnostician references these results instead of manually computing
Arrhenius rates, thermal expansion, or energy balances.

Usage:
    python physics_check.py <RUN_DIR> <ontology.json> <feature_summary.json> <anomaly_report.json> \\
        --output <output.json> \\
        --temp-col <col_name> --dev-col <col_name>    # explicit column assignments
        --vib-col <col_name> --flow-col <col_name>
        --pressure-col <col_name> --power-col <col_name>
        --quality-targets <col1> <col2> ...
        --candidate-params <col1> <col2> ...
        --cleaned-data <cleaned_data.json>

    This script is a GENERIC TEMPLATE. The data-processor agent reads ontology.json
    to determine which physical checks are applicable, then passes the actual column
    names as CLI arguments. No column-name guessing occurs.
"""

import json
import sys
import os
import math
from typing import Any


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _safe_float(v: Any) -> float | None:
    """Coerce a value to float, returning None if not possible.

    cleaned_data.json carries numeric values as strings (CSV→JSON conversion
    performs no type coercion — the string-type-gotcha). Raw
    ``isinstance(v, (int, float))`` gates therefore silently drop every value
    and produce empty before/after windows. This helper parses the string
    instead. Booleans are excluded (bool subclasses int in Python but is not a
    measurement).
    """
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ──────────────────────────────────────────────
# Physical Check Implementations
# ──────────────────────────────────────────────


def check_thermal_expansion(
    temp_col: str,
    dev_col: str,
    data: list[dict],
    coefficient_alpha: float = None,
    reference_length_m: float = None,
) -> dict:
    """
    ΔL = α × L₀ × ΔT — WITHOUT invented constants.

    The expansion coefficient α and reference length are MATERIAL/PROCESS
    SPECIFIC. Inventing them (steel α=12e-6, L=1m) would produce misleading
    "PLAUSIBLE" verdicts for non-steel scenes (film, concrete, water, ...).
    So this check is DATA-DRIVEN: it verifies the coupling itself — does the
    dimensional deviation co-vary with temperature as thermal physics demands?

    * strong positive coupling (|r| >= 0.3, same sign)  → THERMAL_COUPLING_DETECTED
      (quantitative confirmation needs the real α·L₀ from the ontology)
    * strong negative coupling                       → THERMAL_ANTI_CORRELATED
      (compensation/endogenous control, not passive expansion)
    * otherwise                                      → INCONCLUSIVE

    When the ontology supplies coefficient_alpha and reference_length_m, a
    quantitative predicted-vs-actual ratio is ADDED but never decides alone.
    """
    temps = [_safe_float(row[temp_col]) for row in data if temp_col in row]
    devs = [_safe_float(row[dev_col]) for row in data if dev_col in row]
    temps = [t for t in temps if t is not None]
    devs = [d for d in devs if d is not None]
    if not temps or not devs:
        return {"check": "thermal_expansion", "status": "INCONCLUSIVE", "reason": "Missing data columns"}
    if len(temps) < 10 or len(devs) < 10:
        return {"check": "thermal_expansion", "status": "INCONCLUSIVE", "reason": "Insufficient rows for coupling test"}

    n = min(len(temps), len(devs))
    tx, dy = temps[:n], devs[:n]
    from statistics import mean, stdev
    try:
        mx, my = mean(tx), mean(dy)
        sx, sy = stdev(tx), stdev(dy)
        r = sum((a - mx) * (b - my) for a, b in zip(tx, dy)) / (sx * sy * (n - 1))
    except (ZeroDivisionError, ValueError):
        return {"check": "thermal_expansion", "status": "INCONCLUSIVE", "reason": "Degenerate input"}

    checks = {
        "T_range_C": [min(temps), max(temps)],
        "deviation_range": [min(devs), max(devs)],
        "coupling_r": round(r, 4),
        "coupling_n": n,
        "note": "quantitative ΔL=α·L₀·ΔT requires material coefficient from ontology",
    }

    if coefficient_alpha and reference_length_m:
        T_ref = min(temps)
        predicted_mean = mean([coefficient_alpha * reference_length_m * (t - T_ref) for t in temps])
        actual_mean = mean(devs)
        checks["alpha_per_C"] = coefficient_alpha
        checks["reference_length_m"] = reference_length_m
        checks["ratio_predicted_to_actual"] = round(predicted_mean / actual_mean, 4) if actual_mean else None
        checks["quantitative"] = True

    if abs(r) >= 0.3 and r > 0:
        checks["conclusion"] = "THERMAL_COUPLING_DETECTED"
        checks[
            "explanation"
        ] = f"Deviation co-varies positively with temperature (r={r:.3f}) — thermal expansion is a plausible channel; quantify with the real α·L₀ from the ontology"
    elif abs(r) >= 0.3 and r < 0:
        checks["conclusion"] = "THERMAL_ANTI_CORRELATED"
        checks[
            "explanation"
        ] = f"Deviation moves AGAINST temperature (r={r:.3f}) — compensation/control, not passive expansion"
    else:
        checks["conclusion"] = "THERMAL_COUPLING_NOT_DETECTED"
        checks["explanation"] = (
            f"Deviation shows no material coupling with temperature (r={r:.3f}) — "
            "thermal expansion is not the dominant channel for this deviation"
        )

    return checks


def check_arrhenius(
    temp_high_col: str,
    temp_low_col: str,
    degradation_rate_col: str,
    data: list[dict],
    Ea_J_per_mol: float = 80000,
) -> dict:
    """
    k₂/k₁ = exp(Ea/R × (1/T₁ - 1/T₂))

    Checks if degradation rate ratio is physically plausible given temperature difference.
    Typical Ea for chemical degradation: 40-120 kJ/mol
    R = 8.314 J/(mol·K)
    """
    R = 8.314

    # If we have actual temperature data, compute from it
    if temp_high_col in data[0] if data else False:
        temps_high = [_safe_float(row[temp_high_col]) for row in data if temp_high_col in row]
        temps_low = [_safe_float(row[temp_low_col]) for row in data if temp_low_col in row]
        temps_high = [v for v in temps_high if v is not None]
        temps_low = [v for v in temps_low if v is not None]
        if not temps_high or not temps_low:
            return {"check": "arrhenius_kinetics", "status": "INCONCLUSIVE", "reason": "Missing temperature data"}

        try:
            T1_K = min(temps_low) + 273.15
            T2_K = max(temps_high) + 273.15
        except (TypeError, ValueError):
            return {"check": "arrhenius_kinetics", "status": "INCONCLUSIVE", "reason": "Invalid temperature values"}

        if T1_K <= 0 or T2_K <= 0:
            return {"check": "arrhenius_kinetics", "status": "INCONCLUSIVE", "reason": "Invalid temperature (below absolute zero)"}

        rate_ratio = math.exp(Ea_J_per_mol / R * (1 / T1_K - 1 / T2_K))

        # Also check if degradation rate correlates with temperature
        rates = [_safe_float(row[degradation_rate_col]) for row in data if degradation_rate_col in row]
        rates = [v for v in rates if v is not None]
        rate_observed_ratio = 1.0
        if rates:
            rate_observed_ratio = max(rates) / min(rates) if min(rates) > 0 else 0

        check = {
            "check": "arrhenius_kinetics",
            "Ea_J_per_mol": Ea_J_per_mol,
            "R_J_per_mol_K": R,
            "T_low_C": round(T1_K - 273.15, 1),
            "T_high_C": round(T2_K - 273.15, 1),
            "predicted_rate_ratio": round(rate_ratio, 4),
            "observed_rate_ratio": round(rate_observed_ratio, 4) if rate_observed_ratio else "N/A",
        }

        if rate_ratio < 1e-6:
            check["conclusion"] = "ARRHENIUS_NEGLIGIBLE"
            check[
                "explanation"
            ] = f"With ΔT={T2_K - T1_K:.1f}K and Ea={Ea_J_per_mol / 1000:.0f}kJ/mol, predicted rate ratio={rate_ratio:.2e} — temperature effect is negligible in observation window"
        elif 1e-6 <= rate_ratio <= 1e3:
            check["conclusion"] = "ARRHENIUS_PLAUSIBLE"
            check[
                "explanation"
            ] = f"Rate ratio {rate_ratio:.2e} is physically observable — temperature-driven degradation is plausible"
        else:
            check["conclusion"] = "ARRHENIUS_DOMINANT"
            check[
                "explanation"
            ] = f"Rate ratio {rate_ratio:.2e} suggests temperature dominantly controls degradation — setpoint stabilization recommended"

        if 0.1 <= rate_observed_ratio / max(rate_ratio, 1e-10) <= 10:
            check["observational_consistency"] = "CONSISTENT"
            check[
                "observational_detail"
            ] = f"Observed rate ratio ({rate_observed_ratio:.2f}) is consistent with Arrhenius prediction ({rate_ratio:.2e})"
        elif rate_observed_ratio > 0:
            check["observational_consistency"] = "INCONSISTENT"
            check[
                "observational_detail"
            ] = f"Observed rate ratio ({rate_observed_ratio:.2f}) deviates significantly from Arrhenius prediction ({rate_ratio:.2e}) — other mechanisms may dominate"

        return check

    return {"check": "arrhenius_kinetics", "status": "INCONCLUSIVE", "reason": "Temperature columns not found in data"}


def check_vibration_threshold(
    vibration_col: str,
    quality_col: str,
    data: list[dict],
    iso_zone_boundaries: list[float] | None = None,
    equipment_class: str = None,
) -> dict:
    """
    ISO 10816 vibration severity classification.

    Zone A (good): < 1.8 mm/s  (for Class I)
    Zone B (acceptable): 1.8-4.5 mm/s
    Zone C (unsatisfactory): 4.5-11.2 mm/s
    Zone D (unacceptable): > 11.2 mm/s

    ISO 10816 applies to ROTATING machinery only. When the equipment class
    (from ontology) is unknown or clearly non-rotating, the zone ladder is
    reported as reference but the check returns INCONCLUSIVE instead of
    branding the scene VIBRATION_ACCEPTABLE/ELEVATED.
    """
    if iso_zone_boundaries is None:
        # ISO 10816 reference zones for ROTATING machinery (mm/s, velocity).
        # They are a relative severity ladder, not a physics law: pass explicit
        # boundaries from the ontology when the equipment class differs.
        iso_zone_boundaries = [1.8, 4.5, 11.2]

    _ROTATING_KEYWORDS = (
        "pump", "motor", "fan", "blower", "compressor", "turbine", "spindle",
        "bearing", "centrifuge", "mixer", "agitator", "mill", "rotor",
        "gear", "extruder", "旋转", "泵", "电机", "风机", "压缩机", "主轴",
        "轴承", "搅拌", "离心", "齿轮",
    )
    equipment_applicable = True
    if equipment_class:
        eq = str(equipment_class).lower()
        equipment_applicable = any(kw in eq for kw in _ROTATING_KEYWORDS)

    vibs = [_safe_float(row[vibration_col]) for row in data if vibration_col in row]
    quals = [_safe_float(row[quality_col]) for row in data if quality_col in row]
    vibs = [v for v in vibs if v is not None]
    quals = [q for q in quals if q is not None]
    if not vibs or not quals:
        return {"check": "vibration_threshold", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    from statistics import mean, stdev

    # Find quality cliff: is there a vibration level where quality sharply degrades?
    paired = sorted(zip(vibs, quals), key=lambda x: x[0])
    sorted_vibs = [p[0] for p in paired]
    sorted_quals = [p[1] for p in paired]

    # Split into zones per ISO 10816
    zones = {"A (good)": [], "B (acceptable)": [], "C (unsatisfactory)": [], "D (unacceptable)": []}
    zone_keys = list(zones.keys())
    zone_bounds = [0] + iso_zone_boundaries + [float("inf")]

    for v, q in paired:
        for i in range(len(zone_bounds) - 1):
            if zone_bounds[i] <= v < zone_bounds[i + 1]:
                zones[zone_keys[i]].append(q)
                break

    zone_stats = {}
    cliff_detected = False
    cliff_threshold = None
    prev_mean = mean(zones[zone_keys[0]]) if zones[zone_keys[0]] else 0
    for zk in zone_keys[1:]:
        curr = zones[zk]
        if curr:
            curr_mean = mean(curr)
            if prev_mean > 0 and curr_mean / prev_mean > 2.0:  # 2x quality degradation
                cliff_detected = True
                cliff_threshold = zone_bounds[zone_keys.index(zk)]
                break
            prev_mean = curr_mean

    for zk in zone_keys:
        vals = zones[zk]
        if vals:
            zone_stats[zk] = {"count": len(vals), "mean": round(mean(vals), 4), "std": round(stdev(vals), 4) if len(vals) > 1 else 0}
        else:
            zone_stats[zk] = {"count": 0, "mean": None}

    result = {
        "check": "vibration_threshold",
        "iso_10816_zones": zone_bounds,
        "zones": zone_stats,
        "vibration_range": [min(vibs), max(vibs)],
        "quality_range": [min(quals), max(quals)],
        "cliff_detected": cliff_detected,
        "cliff_threshold_mm_s": cliff_threshold,
        "iso_10816_applicable": equipment_applicable,
        "equipment_class": equipment_class,
        "unit_note": "ISO 10816 zones are defined in mm/s velocity — verify the vibration column unit before zone interpretation",
    }

    if not equipment_applicable:
        result["conclusion"] = "INCONCLUSIVE"
        result[
            "explanation"
        ] = f"Equipment class '{equipment_class}' is not recognized as rotating machinery — ISO 10816 zone ladder does not apply; quality-cliff signal reported in cliff_detected"
        return result

    if cliff_detected:
        result["conclusion"] = "VIBRATION_CLIFF_DETECTED"
        result[
            "explanation"
        ] = f"Quality degrades >2× at vibration ~{cliff_threshold:.1f}mm/s — this is a critical threshold for process control"
    elif max(vibs) > iso_zone_boundaries[1]:
        result["conclusion"] = "VIBRATION_ELEVATED"
        result[
            "explanation"
        ] = (f"Vibration reaches {max(vibs):.1f}mm/s — above the upper reference zone "
             f"(ISO 10816 ladder for rotating machinery, if applicable to this equipment). "
             f"Mechanical degradation/wear/imbalance are candidate mechanisms — confirm the "
             f"exact mode against the equipment ontology before concluding.")
    else:
        result["conclusion"] = "VIBRATION_ACCEPTABLE"
        result["explanation"] = f"Vibration within acceptable range (max={max(vibs):.1f}mm/s) — not the primary root cause"

    return result


def check_energy_balance(
    power_col: str,
    temp_rise_col: str,
    mass_kg: float = None,
    cp_J_per_kgK: float = None,
    data: list[dict] = None,
) -> dict:
    """
    ΔT = P × t / (m × Cp) — WITHOUT invented constants.

    Mass and heat capacity are PROCESS SPECIFIC; fabricating m=100kg/Cp=500
    would brand any scene "ENERGY_PLAUSIBLE". This check therefore verifies the
    COUPLING that energy balance demands of the data itself: does temperature
    rise with power?

    * strong positive coupling (|r| >= 0.3) → ENERGY_COUPLED
    * strong negative coupling              → ENERGY_ANTI_CORRELATED
      (power cuts in when temperature rises = endogenous control)
    * otherwise                             → ENERGY_DECOUPLED

    When the ontology supplies mass_kg and cp_J_per_kgK, a quantitative
    ΔT = P·t/(m·Cp) estimate is ADDED but never decides alone.
    """
    if data is None:
        data = []
    powers = [_safe_float(row[power_col]) for row in data if power_col in row]
    temp_rises = [_safe_float(row[temp_rise_col]) for row in data if temp_rise_col in row]
    powers = [v for v in powers if v is not None]
    temp_rises = [v for v in temp_rises if v is not None]
    if not powers or not temp_rises:
        return {"check": "energy_balance", "status": "INCONCLUSIVE", "reason": "Missing data columns"}
    n = min(len(powers), len(temp_rises))
    if n < 10:
        return {"check": "energy_balance", "status": "INCONCLUSIVE", "reason": "Insufficient rows for coupling test"}

    from statistics import mean, stdev
    px, ty = powers[:n], temp_rises[:n]
    try:
        mx, my = mean(px), mean(ty)
        sx, sy = stdev(px), stdev(ty)
        r = sum((a - mx) * (b - my) for a, b in zip(px, ty)) / (sx * sy * (n - 1))
    except (ZeroDivisionError, ValueError):
        return {"check": "energy_balance", "status": "INCONCLUSIVE", "reason": "Degenerate input"}

    result = {
        "check": "energy_balance",
        "power_temperature_coupling_r": round(r, 4),
        "coupling_n": n,
        "average_power": round(mean(px), 2),
        "note": "quantitative ΔT=P·t/(m·Cp) requires mass & heat capacity from ontology",
    }

    if mass_kg and cp_J_per_kgK:
        P_avg = mean(px)
        dT_avg = mean(ty)
        predicted_dT_per_s = P_avg / (mass_kg * cp_J_per_kgK)
        result["mass_kg"] = mass_kg
        result["cp_J_per_kgK"] = cp_J_per_kgK
        result["observed_dT"] = round(dT_avg, 4)
        result["predicted_dT_per_s"] = round(predicted_dT_per_s, 8)
        result["quantitative"] = True

    if abs(r) >= 0.3 and r > 0:
        result["conclusion"] = "ENERGY_COUPLED"
        result[
            "explanation"
        ] = f"Temperature co-varies positively with power (r={r:.3f}) — power input is a plausible heat source; quantify with the real m·Cp from the ontology"
    elif abs(r) >= 0.3 and r < 0:
        result["conclusion"] = "ENERGY_ANTI_CORRELATED"
        result[
            "explanation"
        ] = f"Temperature moves AGAINST power (r={r:.3f}) — load-shedding/endogenous control masks the thermal link"
    else:
        result["conclusion"] = "ENERGY_DECOUPLED"
        result[
            "explanation"
        ] = f"No material coupling between power and temperature (r={r:.3f}) — thermal inertia or missing heat path"

    return result


def check_flow_restriction(
    flow_col: str,
    pressure_drop_col: str,
    data: list[dict],
) -> dict:
    """
    ΔP = f × (L/D) × (ρv²/2)

    Simplified: pressure drop ∝ flow_rate² for turbulent flow.
    Checks if pressure drop scales quadratically with flow rate,
    which is the physical expectation for unrestricted flow.
    """
    flows = [_safe_float(row[flow_col]) for row in data if flow_col in row]
    pressures = [_safe_float(row[pressure_drop_col]) for row in data if pressure_drop_col in row]
    flows = [v for v in flows if v is not None]
    pressures = [v for v in pressures if v is not None]
    if not flows or not pressures:
        return {"check": "flow_restriction", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    from statistics import mean, stdev

    # If pressure ∝ flow², then pressure/flow² should be approximately constant
    ratios = []
    for f, p in zip(flows, pressures):
        if f and f > 0:
            ratios.append(p / (f * f))

    ratio_mean = mean(ratios) if ratios else 0
    ratio_cv = stdev(ratios) / ratio_mean if ratios and ratio_mean > 0 else 0

    result = {
        "check": "flow_restriction",
        "flow_range": [min(flows), max(flows)],
        "pressure_range": [min(pressures), max(pressures)],
        "pressure_over_flow_sq_mean": round(ratio_mean, 6),
        "pressure_over_flow_sq_cv": round(ratio_cv, 4),
    }

    if ratio_cv < 0.2 and ratio_mean > 0:
        result["conclusion"] = "FLOW_QUADRATIC_PLAUSIBLE"
        result[
            "explanation"
        ] = f"Pressure ∝ flow² holds (CV={ratio_cv:.2%}) — no significant flow restriction or fouling detected"
    elif ratio_cv >= 0.2 and ratio_mean > 0:
        result["conclusion"] = "FLOW_RESTRICTION_DETECTED"
        result[
            "explanation"
        ] = f"Pressure/flow² ratio varies significantly (CV={ratio_cv:.2%}) — flow restriction or fouling may be present"
        # Check if pressure/flow² is increasing over time (fouling indicator)
        from statistics import linear_regression

        try:
            x = list(range(len(ratios)))
            slope, intercept = linear_regression(x, ratios)
            result["ratio_trend_slope"] = round(slope, 8)
            if slope > 0:
                result["fouling_indicator"] = "INCREASING"
                result["fouling_detail"] = f"Pressure/flow² ratio increasing (slope={slope:.2e}) — consistent with progressive fouling"
            else:
                result["fouling_indicator"] = "STABLE_OR_DECREASING"
                result["fouling_detail"] = "No progressive fouling trend detected"
        except Exception:
            pass
    else:
        result["conclusion"] = "INCONCLUSIVE"
        result["explanation"] = "Insufficient data for flow restriction analysis"

    return result


def check_heat_transfer(
    T_in_col: str,
    T_out_col: str,
    flow_col: str,
    data: list[dict],
    heat_exchange_area_m2: float = None,
    fluid_cp_J_per_kgK: float = None,
) -> dict:
    """
    U = Q / (A × ΔT_LMTD) — WITHOUT invented constants.

    Heat exchange area and fluid heat capacity are PROCESS SPECIFIC; inventing
    A=1m² / Cp=4186 (water) would fabricate U magnitudes for any other
    geometry/fluid. The fouling signal lives in the RELATIVE trend of the
    energy proxy (Q' = flow × ΔT), so this check is DATA-DRIVEN:

    * U values are only reported when the ontology/CLI supplies
      heat_exchange_area_m2 and fluid_cp_J_per_kgK (marked quantitative=true)
    * otherwise a scale-free proxy (flow × ΔT) drives the CV and
      first-half/second-half trend conclusions
    * flow is treated as MASS flow for Q=m·cp·ΔT; when the flow column is
      volumetric, the U scale shifts by fluid density — noted, trend
      conclusions unaffected
    """
    T_ins = [_safe_float(row[T_in_col]) for row in data if T_in_col in row]
    T_outs = [_safe_float(row[T_out_col]) for row in data if T_out_col in row]
    flows = [_safe_float(row[flow_col]) for row in data if flow_col in row]
    T_ins = [v for v in T_ins if v is not None]
    T_outs = [v for v in T_outs if v is not None]
    flows = [v for v in flows if v is not None]

    if not T_ins or not T_outs or not flows:
        return {"check": "heat_transfer", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    proxy_values = []
    from statistics import mean, stdev

    for i in range(len(T_ins)):
        dT1 = T_ins[i] - T_outs[i]
        if dT1 <= 0:
            continue
        # Simplified LMTD for counter-flow; energy proxy = flow × ΔT
        # (scale-free: U = Q/(A·LMTD) needs A, Cp and MASS flow)
        proxy_values.append(flows[i] * dT1)

    if not proxy_values:
        return {"check": "heat_transfer", "status": "INCONCLUSIVE", "reason": "All LMTD values are non-positive"}

    proxy_mean = mean(proxy_values)
    proxy_std = stdev(proxy_values) if len(proxy_values) > 1 else 0
    proxy_cv = proxy_std / proxy_mean if proxy_mean > 0 else 0

    # Check if the energy proxy declines over time (fouling signature)
    n = len(proxy_values)
    first_half = proxy_values[: n // 2]
    second_half = proxy_values[n // 2 :]
    proxy_first = mean(first_half) if first_half else 0
    proxy_second = mean(second_half) if second_half else 0
    fouling_pct = ((proxy_first - proxy_second) / proxy_first * 100) if proxy_first > 0 else 0

    result = {
        "check": "heat_transfer",
        "energy_proxy_mean": round(proxy_mean, 4),
        "energy_proxy_cv": round(proxy_cv, 4),
        "proxy_first_half_mean": round(proxy_first, 4),
        "proxy_second_half_mean": round(proxy_second, 4),
        "fouling_decline_pct": round(fouling_pct, 2),
        "quantitative": bool(heat_exchange_area_m2 and fluid_cp_J_per_kgK),
        "dimension_note": (
            "flow treated as MASS flow for Q=m·cp·ΔT; if the flow column is volumetric, "
            "any U scale shifts by fluid density — relative trend conclusions unaffected"
        ),
    }

    if heat_exchange_area_m2 and fluid_cp_J_per_kgK:
        # U = Q/(A·LMTD); Q = ṁ·cp·ΔT; LMTD ≈ ΔT (simplified path) → U = ṁ·cp/A
        U_values = [f * fluid_cp_J_per_kgK / heat_exchange_area_m2 for f in flows if f > 0]
        if U_values:
            U_mean = mean(U_values)
            U_std = stdev(U_values) if len(U_values) > 1 else 0
            result["U_mean_W_per_m2K"] = round(U_mean, 2)
            result["U_std_W_per_m2K"] = round(U_std, 2)
            result["U_cv"] = round(U_std / U_mean, 4) if U_mean > 0 else 0
            result["heat_exchange_area_m2"] = heat_exchange_area_m2
            result["fluid_cp_J_per_kgK"] = fluid_cp_J_per_kgK

    if proxy_cv < 0.1:
        result["conclusion"] = "HEAT_TRANSFER_STABLE"
        result["explanation"] = f"Energy proxy CV={proxy_cv:.2%} — heat transfer stable, no significant fouling"
    elif fouling_pct > 10:
        result["conclusion"] = "FOULING_PROGRESSION"
        result[
            "explanation"
        ] = f"Energy proxy declined {fouling_pct:.1f}% from first to second half of data — consistent with progressive fouling"
    else:
        result["conclusion"] = "HEAT_TRANSFER_VARIABLE"
        result["explanation"] = f"Energy proxy varies (CV={proxy_cv:.2%}) but no monotonic decline — process condition changes, not long-term fouling"

    return result


def check_corrosion_rate(
    pH_col: str,
    temp_col: str,
    corrosion_col: str,
    data: list[dict],
) -> dict:
    """
    Simplified corrosion rate check based on pH-temperature effects.
    Low pH (<4) or high pH (>10) with elevated temperature → accelerated corrosion.
    """
    pHs = [_safe_float(row[pH_col]) for row in data if pH_col in row]
    temps = [_safe_float(row[temp_col]) for row in data if temp_col in row]
    corrs = [_safe_float(row[corrosion_col]) for row in data if corrosion_col in row]
    pHs = [v for v in pHs if v is not None]
    temps = [v for v in temps if v is not None]
    corrs = [v for v in corrs if v is not None]

    if not all([pHs, temps, corrs]):
        return {"check": "corrosion_rate", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    from statistics import mean

    pH_mean = mean(pHs)
    T_mean = mean(temps)

    # Corrosion risk assessment
    if pH_mean < 4:
        corrosion_risk = "HIGH"
        detail = f"pH={pH_mean:.1f} (<4) — aggressive acidic corrosion regime"
    elif pH_mean > 10:
        corrosion_risk = "HIGH"
        detail = f"pH={pH_mean:.1f} (>10) — aggressive alkaline corrosion regime"
    elif 4 <= pH_mean <= 6:
        corrosion_risk = "MODERATE"
        detail = f"pH={pH_mean:.1f} (mildly acidic) — mild corrosion risk, elevated temperature amplifies rate"
    elif 8 <= pH_mean <= 10:
        corrosion_risk = "MODERATE"
        detail = f"pH={pH_mean:.1f} (mildly alkaline) — mild corrosion risk"
    else:
        corrosion_risk = "LOW"
        detail = f"pH={pH_mean:.1f} (neutral) — minimal corrosion risk from pH"

    # Arrhenius amplification (simplified)
    T_activation = T_mean > 60
    if T_activation and corrosion_risk in ("MODERATE", "HIGH"):
        corrosion_risk = "CRITICAL" if corrosion_risk == "HIGH" else "HIGH"
        detail += f", T={T_mean:.1f}°C (>60°C) accelerates corrosion rate ~2-3× per 10°C rise"

    result = {
        "check": "corrosion_rate",
        "pH_mean": round(pH_mean, 2),
        "T_mean_C": round(T_mean, 2),
        "corrosion_risk": corrosion_risk,
        "detail": detail,
        "observed_corrosion_mean": round(mean(corrs), 6) if corrs else None,
    }

    return result


# ──────────────────────────────────────────────
# Quality Reset Analysis (Transition Processing)
# ──────────────────────────────────────────────


def analyze_quality_resets(
    anomaly_report: dict,
    cleaned_data: list[dict],
    quality_targets: list[str],
    quality_direction: dict[str, str] | None = None,
) -> list[dict]:
    """
    For each transition event in anomaly_report, compute whether quality
    resets (IMPROVES) or continues degrading after the transition.

    This is the single most powerful test for distinguishing
    component-level vs system-level root causes.

    The "better" direction is PROCESS SPECIFIC — defects/ppm/roughness are
    lower-is-better, yield/efficiency/uptime are higher-is-better. It must be
    declared via quality_direction (e.g. {"roughness": "lower", "yield":
    "higher"}). When the direction is UNKNOWN for a metric, significant
    changes are classified INCONCLUSIVE with the observed delta reported —
    never silently assumed lower-is-better.
    """
    transitions = anomaly_report.get("transition_events", [])
    if not transitions:
        return []

    results = []
    N_CONTEXT = 20  # points before/after to examine

    for t in transitions:
        idx = t.get("index", 0)
        from_val = t.get("from", "?")
        to_val = t.get("to", "?")

        for q in quality_targets:
            before_vals = []
            after_vals = []
            for i in range(max(0, idx - N_CONTEXT), idx):
                if i < len(cleaned_data) and isinstance(cleaned_data[i], dict) and q in cleaned_data[i]:
                    fv = _safe_float(cleaned_data[i][q])
                    if fv is not None:
                        before_vals.append(fv)
            for i in range(idx, min(idx + N_CONTEXT, len(cleaned_data))):
                if i < len(cleaned_data) and isinstance(cleaned_data[i], dict) and q in cleaned_data[i]:
                    fv = _safe_float(cleaned_data[i][q])
                    if fv is not None:
                        after_vals.append(fv)

            if not before_vals or not after_vals:
                continue

            from statistics import mean, stdev

            mu_before = mean(before_vals)
            mu_after = mean(after_vals)
            sigma_before = stdev(before_vals) if len(before_vals) > 1 else 0.01
            sigma_after = stdev(after_vals) if len(after_vals) > 1 else 0.01
            pooled_std = ((sigma_before**2 + sigma_after**2) / 2) ** 0.5 or 0.01
            effect_size = abs(mu_after - mu_before) / pooled_std

            # Does quality IMPROVE after the transition? The "better"
            # direction must be declared (lower-is-better for defects/ppm/
            # roughness; higher-is-better for yield/efficiency). Unknown
            # direction → INCONCLUSIVE, never an assumed direction.
            delta = mu_after - mu_before
            direction = (quality_direction or {}).get(q)
            reset_detected = abs(delta) < 0.1 * abs(mu_before)  # Within 10% = no significant change

            # Statistical test: if means differ significantly
            significant_change = effect_size > 1.0  # Cohen's d > 1.0 = large effect

            interpretation = ""
            if not significant_change and reset_detected:
                interpretation = f"No significant quality change after transition ({from_val}→{to_val}) — degradation continues, system-level root cause (not component-specific)"
                reset_class = "NO_RESET"
            elif significant_change and direction is None:
                interpretation = (
                    f"Significant quality change after transition ({from_val}→{to_val}, "
                    f"delta={delta:+.4f}, d={effect_size:.1f}) — direction of improvement "
                    f"not declared for '{q}' (lower vs higher is better), cannot classify RESET/WORSENED"
                )
                reset_class = "INCONCLUSIVE"
            elif significant_change and direction == "lower" and delta < 0:
                interpretation = f"Quality IMPROVED after transition (d={effect_size:.1f}) — component replacement ({from_val}→{to_val}) was effective, indicates component-level root cause"
                reset_class = "RESET"
            elif significant_change and direction == "lower" and delta > 0:
                interpretation = f"Quality WORSENED after transition (d={effect_size:.1f}) — replacement introduced additional degradation"
                reset_class = "WORSENED"
            elif significant_change and direction == "higher" and delta > 0:
                interpretation = f"Quality IMPROVED after transition (d={effect_size:.1f}) — component replacement ({from_val}→{to_val}) was effective, indicates component-level root cause"
                reset_class = "RESET"
            elif significant_change and direction == "higher" and delta < 0:
                interpretation = f"Quality WORSENED after transition (d={effect_size:.1f}) — replacement introduced additional degradation"
                reset_class = "WORSENED"
            else:
                interpretation = f"Marginal quality change (d={effect_size:.1f}) — insufficient evidence for component-level or system-level determination"
                reset_class = "INCONCLUSIVE"

            results.append(
                {
                    "transition_index": idx,
                    "transition_type": t.get("type", "unknown"),
                    "from": from_val,
                    "to": to_val,
                    "quality_metric": q,
                    "declared_direction": (quality_direction or {}).get(q),
                    "mean_before": round(mu_before, 4),
                    "mean_after": round(mu_after, 4),
                    "effect_size_cohens_d": round(effect_size, 3),
                    "reset_detected": reset_class == "RESET",
                    "reset_classification": reset_class,
                    "interpretation": interpretation,
                    "n_before": len(before_vals),
                    "n_after": len(after_vals),
                }
            )

    return results


# ──────────────────────────────────────────────
# Anomaly-Onset Coincidence Analysis
# ──────────────────────────────────────────────


def analyze_anomaly_onset(
    anomaly_report: dict,
    feature_summary: dict,
    cleaned_data: list[dict],
    candidate_params: list[str],
) -> list[dict]:
    """
    For each anomaly interval, check which candidate parameters change
    significantly BEFORE or DURING the anomaly.

    This provides the temporal ordering needed for causal inference:
    "Parameter X changed BEFORE quality degraded" → potential cause
    "Parameter X changed AFTER quality degraded" → potential effect
    "Parameter X unchanged during anomaly" → not a cause
    """
    targets = anomaly_report.get("targets", {})
    intervals = []
    for tgt_name, tgt_data in targets.items():
        for iv in tgt_data.get("anomaly_intervals", []):
            intervals.append(
                {
                    "target": tgt_name,
                    "start": iv.get("start_index", 0),
                    "end": iv.get("end_index", 0),
                    "severity": iv.get("severity", "unknown"),
                }
            )

    if not intervals:
        return []

    results = []
    LOOKBACK = 10  # How many points before anomaly to check for precursor changes

    for iv in intervals:
        start = iv["start"]
        lookback_start = max(0, start - LOOKBACK)
        pre_window = cleaned_data[lookback_start:start] if lookback_start < start else []
        anomaly_window = cleaned_data[start : iv["end"] + 1] if start < len(cleaned_data) else []

        for param in candidate_params:
            # Check pre-anomaly values
            pre_vals = [s for r in pre_window if (s := _safe_float(r.get(param))) is not None]
            anomaly_vals = [s for r in anomaly_window if (s := _safe_float(r.get(param))) is not None]

            if not pre_vals or not anomaly_vals:
                continue

            from statistics import mean, stdev

            mu_pre = mean(pre_vals)
            mu_anom = mean(anomaly_vals)

            pre_std = stdev(pre_vals) if len(pre_vals) > 1 else 0.01
            anom_std = stdev(anomaly_vals) if len(anomaly_vals) > 1 else 0.01
            pooled_std = ((pre_std**2 + anom_std**2) / 2) ** 0.5 or 0.01
            effect = (mu_anom - mu_pre) / pooled_std

            if abs(effect) > 1.0:
                # Check if trend starts before anomaly
                precursor = False
                if len(pre_vals) >= 3:
                    # Check last 3 points for monotonic trend
                    last_3 = pre_vals[-3:]
                    if last_3[0] < last_3[1] < last_3[2] or last_3[0] > last_3[1] > last_3[2]:
                        precursor = True

                results.append(
                    {
                        "anomaly_interval": [start, iv["end"]],
                        "target": iv["target"],
                        "parameter": param,
                        "effect_size": round(effect, 3),
                        "mean_before": round(mu_pre, 4),
                        "mean_during": round(mu_anom, 4),
                        "parameter_changed_before_anomaly": precursor,
                        "parameter_change_timing": "PRECURSOR" if precursor else "CONCURRENT",
                        "classification": "POTENTIAL_CAUSE" if precursor else "CONCURRENT_CHANGE",
                    }
                )

    return results


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Physical Feasibility Check Engine")
    parser.add_argument("run_dir", help="Run directory")
    parser.add_argument("ontology", help="Path to ontology.json")
    parser.add_argument("feature_summary", help="Path to feature_summary.json")
    parser.add_argument("anomaly_report", help="Path to anomaly_report.json")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--cleaned-data", help="Path to cleaned_data.json")
    parser.add_argument("--quality-targets", nargs="+", default=[], help="Quality target column names")
    parser.add_argument("--candidate-params", nargs="+", default=[], help="Candidate parameter columns")
    # Explicit column assignments (agent reads ontology, passes these)
    parser.add_argument("--temp-col", default=None, help="Temperature column name")
    parser.add_argument("--dev-col", default=None, help="Dimensional deviation column name")
    parser.add_argument("--vib-col", default=None, help="Vibration column name")
    parser.add_argument("--flow-col", default=None, help="Flow rate column name")
    parser.add_argument("--pressure-col", default=None, help="Pressure column name")
    parser.add_argument("--power-col", default=None, help="Power/current column name")
    parser.add_argument("--speed-col", default=None, help="Speed/RPM column name")
    parser.add_argument("--ph-col", default=None, help="pH column name")
    parser.add_argument("--corrosion-col", default=None, help="Corrosion rate column name")
    parser.add_argument("--quality-direction", nargs="+", default=[],
                        help="Declared 'better' direction per quality column: COL=lower|higher (repeatable, e.g. --quality-direction roughness=lower yield=higher)")
    parser.add_argument("--ea-kj-mol", type=float, default=None,
                        help="Arrhenius activation energy kJ/mol (ontology value); omitted → neutral 80 kJ/mol prior, flagged as assumed")
    parser.add_argument("--heat-exchange-area-m2", type=float, default=None,
                        help="Heat exchanger area m² (ontology value); omitted → scale-free energy-proxy trend only")
    parser.add_argument("--fluid-cp-j-kg-k", type=float, default=None,
                        help="Fluid heat capacity J/(kg·K) (ontology value); omitted → scale-free energy-proxy trend only")

    args = parser.parse_args()

    if not os.path.exists(args.ontology):
        print(f'{{"error": "ontology.json not found: {args.ontology}"}}')
        sys.exit(1)

    ontology = load_json(args.ontology)
    feature_summary = load_json(args.feature_summary)
    anomaly_report = load_json(args.anomaly_report)

    # Determine scenario from ontology signals
    signals = ontology.get("signals", {})
    all_param_names = []
    for section in ["inspection_signals", "process_parameters", "control_variables"]:
        for p in signals.get(section, []):
            all_param_names.append(p.get("column", p.get("name", "")))

    quality_targets = args.quality_targets or [
        p.get("column", p.get("name", ""))
        for p in signals.get("inspection_signals", [])
    ]
    candidate_params = args.candidate_params or [
        p.get("column", p.get("name", ""))
        for p in signals.get("process_parameters", [])
    ]

    quality_direction = {}
    for pair in args.quality_direction:
        if "=" in pair:
            col, d = pair.split("=", 1)
            if d in ("lower", "higher"):
                quality_direction[col] = d

    equipment_class = None
    scene = ontology.get("scene", {}) or {}
    eq_names = [e.get("name", "") for e in scene.get("equipment", [])]
    process_type = scene.get("process_type", "") or ""
    equipment_class = " ".join(eq_names + [process_type]).strip() or None

    checks = {}

    # Load cleaned_data if available
    cleaned_data = []
    if args.cleaned_data and os.path.exists(args.cleaned_data):
        cd = load_json(args.cleaned_data)
        if isinstance(cd, list):
            cleaned_data = cd
        elif isinstance(cd, dict):
            for key in ["data", "records", "rows", "values"]:
                if key in cd and isinstance(cd[key], list):
                    cleaned_data = cd[key]
                    break
            if not cleaned_data:
                cleaned_data = [cd]

    # ── Column detection from parameter names ──
    def find_cols(keywords: list[str], source: list[str] = None):
        source = source or all_param_names
        found = []
        for kw in keywords:
            for name in source:
                if kw.lower() in name.lower():
                    found.append(name)
        return found

    # ── Run available checks ──
    # Column priority: explicit CLI arg > ontology > keyword fallback
    temp_col = args.temp_col or (find_cols(["temp", "temperature"])[:1] or [None])[0]
    dev_col = args.dev_col or (find_cols(["deviation", "dimension", "error", "defect_size", "gap", "thickness"])[:1] or [None])[0]
    vib_col = args.vib_col or (find_cols(["vibration", "vib"])[:1] or [None])[0]
    flow_col = args.flow_col or (find_cols(["flow", "flow_rate"])[:1] or [None])[0]
    pressure_col = args.pressure_col or (find_cols(["pressure"])[:1] or [None])[0]
    power_col = args.power_col or (find_cols(["power", "current"])[:1] or [None])[0]

    # --- Run applicable checks ---
    if temp_col and dev_col and cleaned_data:
        checks["thermal_expansion"] = check_thermal_expansion(temp_col, dev_col, cleaned_data)

    if temp_col and cleaned_data:
        low_temp_cols = [c for c in all_param_names if c != temp_col and "temp" in c.lower()]
        low_temp = low_temp_cols[0] if low_temp_cols else None
        if low_temp and quality_targets:
            checks["arrhenius_kinetics"] = check_arrhenius(
                temp_col, low_temp, quality_targets[0], cleaned_data,
                Ea_J_per_mol=(args.ea_kj_mol * 1000 if args.ea_kj_mol else None) or 80000,
            )
            if not args.ea_kj_mol:
                checks["arrhenius_kinetics"]["Ea_assumed_default"] = True
                checks["arrhenius_kinetics"]["Ea_note"] = "No activation energy supplied via --ea-kj-mol/ontology — 80 kJ/mol neutral prior used; conclusion is a plausibility band, not a quantitative law"

    if vib_col and quality_targets and cleaned_data:
        checks["vibration_threshold"] = check_vibration_threshold(vib_col, quality_targets[0], cleaned_data, equipment_class=equipment_class)

    if power_col and temp_col and cleaned_data:
        checks["energy_balance"] = check_energy_balance(power_col, temp_col, data=cleaned_data)

    if flow_col and pressure_col and cleaned_data:
        checks["flow_restriction"] = check_flow_restriction(flow_col, pressure_col, cleaned_data)

    all_temps = find_cols(["temp", "temperature"])
    if len(all_temps) >= 2 and flow_col and cleaned_data:
        checks["heat_transfer"] = check_heat_transfer(
            all_temps[0], all_temps[1], flow_col, cleaned_data,
            heat_exchange_area_m2=args.heat_exchange_area_m2,
            fluid_cp_J_per_kgK=args.fluid_cp_j_kg_k,
        )

    if args.ph_col and args.temp_col and args.corrosion_col and cleaned_data:
        checks["corrosion_rate"] = check_corrosion_rate(args.ph_col, args.temp_col, args.corrosion_col, cleaned_data)

    transition_results = analyze_quality_resets(anomaly_report, cleaned_data, quality_targets, quality_direction)
    if transition_results:
        checks["quality_reset_analysis"] = {
            "reset_found": any(r["reset_detected"] for r in transition_results),
            "total_transitions_analyzed": len(transition_results),
            "details": transition_results,
            "summary": _summarize_resets(transition_results),
        }

    # 8. Anomaly-onset coincidence analysis
    onset_results = analyze_anomaly_onset(anomaly_report, feature_summary, cleaned_data, candidate_params)
    if onset_results:
        checks["anomaly_onset_coincidence"] = onset_results

    output = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "scenario": ontology.get("scene", {}).get("process_type", "unknown"),
        "checks_summary": {k: v.get("conclusion", v.get("status", "COMPLETED")) for k, v in checks.items() if isinstance(v, dict)},
        "physical_checks": checks,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Physics checks written to {args.output}")
    print(f"  Checks performed: {len(checks)}")
    for k, v in checks.items():
        if isinstance(v, dict):
            conclusion = v.get("conclusion", v.get("status", "UNKNOWN"))
        else:
            conclusion = f"list[{len(v)}]"
        print(f"  [{conclusion}] {k}")


def _summarize_resets(results: list[dict]) -> str:
    resets = [r for r in results if r["reset_classification"] == "RESET"]
    no_resets = [r for r in results if r["reset_classification"] == "NO_RESET"]
    parts = []
    if resets:
        parts.append(f"{len(resets)} transition(s) show quality RESET after component replacement")
    if no_resets:
        parts.append(f"{len(no_resets)} transition(s) show NO quality reset — degradation is system-level, not component-specific")
    if not parts:
        parts.append("No definitive quality reset pattern detected")
    return "; ".join(parts)


if __name__ == "__main__":
    main()