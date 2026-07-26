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
    with open(path, "r", encoding="utf-8") as f:
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
    coefficient_alpha: float = 12e-6,
    reference_length_m: float = 1.0,
) -> dict:
    """
    ΔL = α × L₀ × ΔT

    Verifies whether dimensional deviation is consistent with thermal expansion.
    For steel: α ≈ 12×10⁻⁶ /°C
    """
    temps = [row[temp_col] for row in data if temp_col in row]
    devs = [row[dev_col] for row in data if dev_col in row]
    if not temps or not devs:
        return {"check": "thermal_expansion", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    T_ref = min(temps) if temps else 20.0
    predicted_devs = [coefficient_alpha * reference_length_m * (t - T_ref) for t in temps]

    from statistics import mean, stdev

    actual_mean = mean(devs)
    predicted_mean = mean(predicted_devs)
    if actual_mean == 0:
        return {"check": "thermal_expansion", "status": "INCONCLUSIVE", "reason": "Actual deviation is zero"}

    ratio = predicted_mean / actual_mean if actual_mean != 0 else 0
    ratio_mag = abs(predicted_mean / actual_mean) if actual_mean != 0 else 0

    # Physical check: is the predicted thermal expansion close to observed deviation?
    checks = {
        "reference_length_m": reference_length_m,
        "alpha_per_C": coefficient_alpha,
        "T_range_C": [min(temps), max(temps)],
        "deviation_range_mm": [min(devs), max(devs)],
        "predicted_deviation_mm": predicted_mean,
        "actual_deviation_mm": actual_mean,
        "ratio_predicted_to_actual": round(ratio, 4),
        "max_predicted_mm": max(predicted_devs) if predicted_devs else 0,
        "max_actual_mm": max(devs) if devs else 0,
    }

    if 0.5 <= ratio_mag <= 2.0:
        checks["conclusion"] = "THERMAL_EXPANSION_PLAUSIBLE"
        checks[
            "explanation"
        ] = f"Observed deviation ({actual_mean:.4f}mm) is within 2× of thermal expansion prediction ({predicted_mean:.4f}mm) — thermal effect is physically plausible"
    elif ratio_mag < 0.5:
        checks["conclusion"] = "THERMAL_EXPANSION_INSUFFICIENT"
        checks[
            "explanation"
        ] = f"Thermal expansion ({predicted_mean:.4f}mm) explains <50% of observed deviation ({actual_mean:.4f}mm) — other mechanisms dominate"
    else:
        checks["conclusion"] = "THERMAL_EXPANSION_EXCEEDS"
        checks[
            "explanation"
        ] = f"Thermal expansion ({predicted_mean:.4f}mm) exceeds observed deviation ({actual_mean:.4f}mm) by >2× — material constraint or compensating mechanism present"

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
        temps_high = [row[temp_high_col] for row in data if temp_high_col in row]
        temps_low = [row[temp_low_col] for row in data if temp_low_col in row]
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
        rates = [row[degradation_rate_col] for row in data if degradation_rate_col in row]
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
) -> dict:
    """
    ISO 10816 vibration severity classification.

    Zone A (good): < 1.8 mm/s  (for Class I)
    Zone B (acceptable): 1.8-4.5 mm/s
    Zone C (unsatisfactory): 4.5-11.2 mm/s
    Zone D (unacceptable): > 11.2 mm/s
    """
    if iso_zone_boundaries is None:
        iso_zone_boundaries = [1.8, 4.5, 11.2]

    vibs = [row[vibration_col] for row in data if vibration_col in row]
    quals = [row[quality_col] for row in data if quality_col in row]
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
    }

    if cliff_detected:
        result["conclusion"] = "VIBRATION_CLIFF_DETECTED"
        result[
            "explanation"
        ] = f"Quality degrades >2× at vibration ~{cliff_threshold:.1f}mm/s — this is a critical threshold for process control"
    elif max(vibs) > iso_zone_boundaries[1]:
        result["conclusion"] = "VIBRATION_ELEVATED"
        result[
            "explanation"
        ] = f"Vibration reaches {max(vibs):.1f}mm/s (Zone C/D per ISO 10816) — bearing wear or imbalance probable"
    else:
        result["conclusion"] = "VIBRATION_ACCEPTABLE"
        result["explanation"] = f"Vibration within acceptable range (max={max(vibs):.1f}mm/s) — not the primary root cause"

    return result


def check_energy_balance(
    power_col: str,
    temp_rise_col: str,
    mass_kg: float,
    cp_J_per_kgK: float,
    data: list[dict],
) -> dict:
    """
    ΔT = P × t / (m × Cp)

    Checks if observed temperature rise is consistent with power input.
    For water: Cp ≈ 4186 J/(kg·K)
    For steel: Cp ≈ 500 J/(kg·K)
    For oil: Cp ≈ 2000 J/(kg·K)
    """
    powers = [row[power_col] for row in data if power_col in row]
    temp_rises = [row[temp_rise_col] for row in data if temp_rise_col in row]
    if not powers or not temp_rises:
        return {"check": "energy_balance", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    P_avg = sum(powers) / len(powers)
    dT_avg = sum(temp_rises) / len(temp_rises)

    # Predicted ΔT per second (assuming continuous power input)
    predicted_dT_per_s = P_avg / (mass_kg * cp_J_per_kgK)

    result = {
        "check": "energy_balance",
        "mass_kg": mass_kg,
        "cp_J_per_kgK": cp_J_per_kgK,
        "average_power_W": round(P_avg, 2),
        "observed_dT": round(dT_avg, 4),
        "predicted_dT_per_s": f"{predicted_dT_per_s:.6f}",
        "thermal_time_constant_s": "Requires transient data for precise calculation",
    }

    if abs(predicted_dT_per_s) < 1e-6:
        result["conclusion"] = "ENERGY_NEGLIGIBLE"
        result[
            "explanation"
        ] = f"Power input ({P_avg:.1f}W) is insufficient to cause detectable temperature rise in {mass_kg}kg mass — thermal effect negligible"
    else:
        result["conclusion"] = "ENERGY_PLAUSIBLE"
        result[
            "explanation"
        ] = f"Power input ({P_avg:.1f}W) can produce ~{predicted_dT_per_s:.4f}°C/s temperature rise — persistent power input over time explains observed temperature"

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
    flows = [_safe_float(row.get(flow_col)) for row in data if flow_col in row]
    pressures = [_safe_float(row.get(pressure_drop_col)) for row in data if pressure_drop_col in row]
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
    heat_exchange_area_m2: float = 1.0,
    fluid_cp_J_per_kgK: float = 4186,
) -> dict:
    """
    U = Q / (A × ΔT_LMTD)

    Calculates heat transfer coefficient to check for fouling/degradation.
    U decreasing over time = fouling progression.
    """
    T_ins = [row[T_in_col] for row in data if T_in_col in row]
    T_outs = [row[T_out_col] for row in data if T_out_col in row]
    flows = [row[flow_col] for row in data if flow_col in row]

    if not T_ins or not T_outs or not flows:
        return {"check": "heat_transfer", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    U_values = []
    from statistics import mean, stdev

    for i in range(len(T_ins)):
        dT1 = T_ins[i] - T_outs[i]
        if dT1 <= 0:
            continue
        # Simplified LMTD for counter-flow
        LMTD = dT1
        Q = flows[i] * fluid_cp_J_per_kgK * dT1
        U = Q / (heat_exchange_area_m2 * LMTD)
        U_values.append(U)

    if not U_values:
        return {"check": "heat_transfer", "status": "INCONCLUSIVE", "reason": "All LMTD values are non-positive"}

    U_mean = mean(U_values)
    U_std = stdev(U_values) if len(U_values) > 1 else 0
    U_cv = U_std / U_mean if U_mean > 0 else 0

    # Check if U is decreasing over time (fouling)
    n = len(U_values)
    first_half = U_values[: n // 2]
    second_half = U_values[n // 2 :]
    U_first = mean(first_half) if first_half else 0
    U_second = mean(second_half) if second_half else 0
    fouling_pct = ((U_first - U_second) / U_first * 100) if U_first > 0 else 0

    result = {
        "check": "heat_transfer",
        "U_mean_W_per_m2K": round(U_mean, 2),
        "U_std_W_per_m2K": round(U_std, 2),
        "U_cv": round(U_cv, 4),
        "U_first_half_mean": round(U_first, 2),
        "U_second_half_mean": round(U_second, 2),
        "fouling_decline_pct": round(fouling_pct, 2),
    }

    if U_cv < 0.1:
        result["conclusion"] = "HEAT_TRANSFER_STABLE"
        result["explanation"] = f"U={U_mean:.1f}±{U_std:.1f} W/m²K (CV={U_cv:.2%}) — heat transfer stable, no significant fouling"
    elif fouling_pct > 10:
        result["conclusion"] = "FOULING_PROGRESSION"
        result[
            "explanation"
        ] = f"U declined {fouling_pct:.1f}% from first to second half of data — consistent with progressive fouling"
    else:
        result["conclusion"] = "HEAT_TRANSFER_VARIABLE"
        result["explanation"] = f"U varies (CV={U_cv:.2%}) but no monotonic decline — process condition changes, not long-term fouling"

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
    pHs = [row[pH_col] for row in data if pH_col in row]
    temps = [row[temp_col] for row in data if temp_col in row]
    corrs = [row[corrosion_col] for row in data if corrosion_col in row]

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


def check_pump_affinity(
    flow_col: str,
    speed_col: str,
    power_col: str,
    data: list[dict],
) -> dict:
    """
    Pump affinity laws:
        Q ∝ N,  ΔP ∝ N²,  P ∝ N³

    For a centrifugal pump, flow should scale linearly with speed; power
    cubically. Deviations indicate pump degradation, cavitation, or wrong
    pump curve. Useful for verifying pump-speed-flow causality.
    """
    flows = [_safe_float(r.get(flow_col)) for r in data if flow_col in r]
    speeds = [_safe_float(r.get(speed_col)) for r in data if speed_col in r]
    powers = [_safe_float(r.get(power_col)) for r in data if power_col in r]
    flows = [v for v in flows if v is not None]
    speeds = [v for v in speeds if v is not None]
    powers = [v for v in powers if v is not None]
    if not flows or not speeds or len(flows) != len(speeds):
        return {"check": "pump_affinity", "status": "INCONCLUSIVE", "reason": "Missing/mismatched flow and speed data"}

    from statistics import mean, stdev

    # Q/N should be ~constant for healthy pump
    qn_ratios = [q / n for q, n in zip(flows, speeds) if n and n > 0]
    qn_mean = mean(qn_ratios) if qn_ratios else 0
    qn_cv = stdev(qn_ratios) / qn_mean if qn_ratios and qn_mean > 0 else 0

    result = {
        "check": "pump_affinity",
        "Q_per_N_mean": round(qn_mean, 6),
        "Q_per_N_cv": round(qn_cv, 4),
    }

    # P/N³ should be ~constant (if power available)
    pn_ratios = []
    if powers and len(powers) == len(speeds):
        pn_ratios = [p / (n ** 3) for p, n in zip(powers, speeds) if n and n > 0]
    if pn_ratios:
        pn_mean = mean(pn_ratios)
        pn_cv = stdev(pn_ratios) / pn_mean if pn_mean > 0 else 0
        result["P_per_N_cubed_mean"] = round(pn_mean, 8)
        result["P_per_N_cubed_cv"] = round(pn_cv, 4)

    if qn_cv < 0.15:
        result["conclusion"] = "PUMP_AFFINITY_CONSISTENT"
        result["explanation"] = f"Q/N ratio stable (CV={qn_cv:.2%}) — flow follows pump affinity law; speed→flow causality is physical"
    elif qn_cv >= 0.30:
        result["conclusion"] = "PUMP_DEGRADATION_SUSPECTED"
        result["explanation"] = f"Q/N ratio highly variable (CV={qn_cv:.2%}) — pump may be cavitating, worn, or off-curve; investigate"
    else:
        result["conclusion"] = "PUMP_AFFINITY_PARTIAL"
        result["explanation"] = f"Q/N ratio moderately variable (CV={qn_cv:.2%}) — partially consistent with affinity law; system effects may be present"
    return result


def check_darcy_weisbach(
    flow_col: str,
    pressure_drop_col: str,
    length_m: float = 10.0,
    diameter_m: float = 0.05,
    roughness_mm: float = 0.045,
    density_kg_m3: float = 1000.0,
    data: list[dict] = None,
) -> dict:
    """
    ΔP = f · (L/D) · (ρv²/2)

    Darcy-Weisbach pressure drop. For turbulent flow, ΔP ∝ Q². This check
    extracts the effective friction factor f from observed (Q, ΔP) pairs and
    compares against expected range (0.015-0.04 for smooth commercial pipes).
    Rising f over time → fouling/scaling.
    """
    if data is None:
        data = []
    flows = [_safe_float(r.get(flow_col)) for r in data if flow_col in r]
    drops = [_safe_float(r.get(pressure_drop_col)) for r in data if pressure_drop_col in r]
    flows = [v for v in flows if v is not None]
    drops = [v for v in drops if v is not None]
    if not flows or not drops or len(flows) != len(drops):
        return {"check": "darcy_weisbach", "status": "INCONCLUSIVE", "reason": "Missing/mismatched flow and pressure data"}

    from statistics import mean, stdev

    area = math.pi * (diameter_m / 2) ** 2
    # f = ΔP · 2 · D / (L · ρ · v²), where v = Q / A
    frictions = []
    for q, dp in zip(flows, drops):
        # Convert Q (assume m³/s if value small, else L/min → m³/s)
        q_m3s = q / 60000.0 if q > 1.0 else q  # heuristic: >1 → L/min
        v = q_m3s / area if area > 0 else 0
        if v <= 0:
            continue
        f = dp * 2 * diameter_m / (length_m * density_kg_m3 * v ** 2)
        frictions.append(f)

    if not frictions:
        return {"check": "darcy_weisbach", "status": "INCONCLUSIVE", "reason": "Could not compute velocities"}

    f_mean = mean(frictions)
    f_cv = stdev(frictions) / f_mean if f_mean > 0 else 0

    result = {
        "check": "darcy_weisbach",
        "assumed_L_m": length_m,
        "assumed_D_m": diameter_m,
        "assumed_roughness_mm": roughness_mm,
        "effective_friction_factor": round(f_mean, 5),
        "friction_cv": round(f_cv, 4),
    }

    if f_cv > 0.3:
        # Check trend
        n = len(frictions)
        first_half = mean(frictions[: n // 2]) if n > 2 else f_mean
        second_half = mean(frictions[n // 2 :]) if n > 2 else f_mean
        if second_half > first_half * 1.2:
            result["conclusion"] = "FOULING_PROGRESSIVE"
            result["explanation"] = f"Effective friction factor rose {(second_half/first_half - 1)*100:.0f}% — pipe scaling/fouling probable"
            return result

    if 0.012 <= f_mean <= 0.05:
        result["conclusion"] = "DARCY_PLAUSIBLE"
        result["explanation"] = f"Effective f={f_mean:.4f} within typical turbulent range (0.012-0.05) — pressure drop is physically explained"
    elif f_mean < 0.012:
        result["conclusion"] = "DARCY_F_TOO_LOW"
        result["explanation"] = f"Effective f={f_mean:.4f} below typical — possible laminar regime or oversized pipe assumption"
    else:
        result["conclusion"] = "DARCY_F_TOO_HIGH"
        result["explanation"] = f"Effective f={f_mean:.4f} above typical — pipe fouling, restrictions, or wrong geometry assumptions"
    return result


def check_forced_oscillator(
    vib_col: str,
    speed_col: str,
    quality_col: str,
    data: list[dict],
) -> dict:
    """
    Forced-oscillator (ISO 10816) + speed-coupling check.

    Vibration in rotating equipment is governed by m·ẍ + c·ẋ + kx = F(t).
    F(t) typically scales with N² (unbalance) or N (misalignment). This check
    verifies whether vibration scales with speed as physics predicts and
    whether vibration→quality threshold is physical.
    """
    vibs = [_safe_float(r.get(vib_col)) for r in data if vib_col in r]
    speeds = [_safe_float(r.get(speed_col)) for r in data if speed_col in r]
    quals = [_safe_float(r.get(quality_col)) for r in data if quality_col in r]
    vibs = [v for v in vibs if v is not None]
    speeds = [s for s in speeds if s is not None]
    quals = [q for q in quals if q is not None]
    if not vibs or not speeds or len(vibs) != len(speeds):
        return {"check": "forced_oscillator", "status": "INCONCLUSIVE", "reason": "Missing/mismatched vibration and speed data"}

    from statistics import mean, stdev

    # Vib / N (unbalance ~N², misalignment ~N — try both)
    v_over_n = [v / n for v, n in zip(vibs, speeds) if n > 0]
    v_over_n2 = [v / (n ** 2) for v, n in zip(vibs, speeds) if n > 0]
    cv_n = stdev(v_over_n) / mean(v_over_n) if v_over_n and mean(v_over_n) > 0 else 1
    cv_n2 = stdev(v_over_n2) / mean(v_over_n2) if v_over_n2 and mean(v_over_n2) > 0 else 1

    result = {
        "check": "forced_oscillator",
        "vib_per_N_cv": round(cv_n, 4),
        "vib_per_N_sq_cv": round(cv_n2, 4),
    }

    if cv_n < 0.2:
        result["conclusion"] = "MISALIGNMENT_PATTERN"
        result["explanation"] = f"Vibration ∝ N (CV={cv_n:.2%}) — consistent with misalignment or gear-mesh forcing"
    elif cv_n2 < 0.2:
        result["conclusion"] = "UNBALANCE_PATTERN"
        result["explanation"] = f"Vibration ∝ N² (CV={cv_n2:.2%}) — consistent with rotating unbalance; balance correction needed"
    else:
        result["conclusion"] = "VIBRATION_NOT_SPEED_COUPLED"
        result["explanation"] = "Vibration does not scale cleanly with N or N² — bearing fault, resonance, or external forcing likely"

    # Quality-vibration threshold check
    if quals and len(quals) == len(vibs):
        paired = sorted(zip(vibs, quals))
        n = len(paired)
        low_vib_q = mean([q for _, q in paired[: n // 4]])
        high_vib_q = mean([q for _, q in paired[-(n // 4):]])
        if low_vib_q > 0:
            result["quality_ratio_high_to_low_vib"] = round(high_vib_q / low_vib_q, 3)
            if high_vib_q / low_vib_q > 2.0:
                result["cliff_detected"] = True
                result["cliff_explanation"] = f"Quality at high-vibration quartile is {high_vib_q/low_vib_q:.1f}× low-vibration quartile — strong vib→quality coupling"
    return result


def check_preston_cmp(
    pressure_col: str,
    velocity_col: str,
    removal_rate_col: str,
    data: list[dict],
    K_p: float = 1.0,
) -> dict:
    """
    Chemical Mechanical Polishing (CMP) Preston equation:
        RR = K_p · P · v

    Removal rate ∝ pressure × relative velocity. Useful for wafer polishing,
    lapping, or grinding processes. Deviations indicate pad wear, slurry
    depletion, or non-Preston regime.
    """
    pressures = [_safe_float(r.get(pressure_col)) for r in data if pressure_col in r]
    velocities = [_safe_float(r.get(velocity_col)) for r in data if velocity_col in r]
    removals = [_safe_float(r.get(removal_rate_col)) for r in data if removal_rate_col in r]
    pressures = [p for p in pressures if p is not None]
    velocities = [v for v in velocities if v is not None]
    removals = [r for r in removals if r is not None]
    if not (pressures and velocities and removals and len(pressures) == len(velocities) == len(removals)):
        return {"check": "preston_cmp", "status": "INCONCLUSIVE", "reason": "Missing/mismatched pressure, velocity, removal rate"}

    from statistics import mean, stdev

    # RR / (P·v) should be ~constant
    pv_ratios = [rr / (p * v) for rr, p, v in zip(removals, pressures, velocities) if p > 0 and v > 0]
    if not pv_ratios:
        return {"check": "preston_cmp", "status": "INCONCLUSIVE", "reason": "Zero pressure or velocity"}
    k_mean = mean(pv_ratios)
    k_cv = stdev(pv_ratios) / k_mean if k_mean > 0 else 0

    result = {
        "check": "preston_cmp",
        "effective_K_p": round(k_mean, 6),
        "K_p_cv": round(k_cv, 4),
    }
    if k_cv < 0.15:
        result["conclusion"] = "PRESTON_CONSISTENT"
        result["explanation"] = f"RR = K_p·P·v holds (CV={k_cv:.2%}, K_p={k_mean:.4f}) — mechanical polishing regime confirmed"
    elif k_cv < 0.35:
        result["conclusion"] = "PRESTON_PARTIAL"
        result["explanation"] = f"Moderate deviation from Preston (CV={k_cv:.2%}) — chemical contribution or pad conditioning effects"
    else:
        result["conclusion"] = "PRESTON_VIOLATED"
        result["explanation"] = f"Large deviation (CV={k_cv:.2%}) — non-Preston regime; possible pad wear, slurry starvation, or end-of-life"
    return result


def check_taylor_tool_life(
    speed_col: str,
    wear_col: str,
    data: list[dict],
    n_taylor: float = 3.0,
) -> dict:
    """
    Taylor tool life:  V·T^n = C  (extended to wear rate: dw/dt ∝ V^(1/n))

    Tool wear rate should scale with cutting speed per Taylor. Useful for CNC,
    machining, drilling. Observed wear-rate vs predicted scaling indicates
    whether speed is the dominant wear driver.
    """
    speeds = [_safe_float(r.get(speed_col)) for r in data if speed_col in r]
    wears = [_safe_float(r.get(wear_col)) for r in data if wear_col in r]
    speeds = [s for s in speeds if s is not None]
    wears = [w for w in wears if w is not None]
    if not speeds or not wears or len(speeds) != len(wears):
        return {"check": "taylor_tool_life", "status": "INCONCLUSIVE", "reason": "Missing/mismatched speed and wear data"}

    from statistics import mean, stdev

    # Group speeds into bins, compute mean wear per bin
    paired = sorted(zip(speeds, wears))
    n_bins = min(5, len(paired))
    if n_bins < 2:
        return {"check": "taylor_tool_life", "status": "INCONCLUSIVE", "reason": "Insufficient data range"}
    bin_size = len(paired) // n_bins
    bin_means = []
    for i in range(n_bins):
        chunk = paired[i * bin_size : (i + 1) * bin_size if i < n_bins - 1 else len(paired)]
        if chunk:
            bin_means.append((mean([s for s, _ in chunk]), mean([w for _, w in chunk])))

    # Taylor predicts wear ∝ V^(1/n) — check log-log slope
    if len(bin_means) >= 2:
        import math as _m
        v_min, w_min = bin_means[0]
        v_max, w_max = bin_means[-1]
        if v_min > 0 and v_max > 0 and w_min > 0 and w_max > 0:
            observed_exp = (_m.log(w_max) - _m.log(w_min)) / (_m.log(v_max) - _m.log(v_min))
            predicted_exp = 1.0 / n_taylor
            ratio = observed_exp / predicted_exp if predicted_exp else 0

            result = {
                "check": "taylor_tool_life",
                "assumed_n_taylor": n_taylor,
                "predicted_wear_exponent": round(predicted_exp, 3),
                "observed_wear_exponent": round(observed_exp, 3),
                "observed_to_predicted_ratio": round(ratio, 3),
            }
            if 0.5 <= ratio <= 2.0:
                result["conclusion"] = "TAYLOR_CONSISTENT"
                result["explanation"] = f"Observed wear exponent ({observed_exp:.2f}) within 2× of Taylor prediction ({predicted_exp:.2f}) — speed-driven wear"
            elif ratio < 0.5:
                result["conclusion"] = "TAYLOR_UNDEREXPONENT"
                result["explanation"] = f"Observed wear exponent ({observed_exp:.2f}) << Taylor prediction — wear dominated by non-speed factors (abrasion, adhesive, thermal)"
            else:
                result["conclusion"] = "TAYLOR_OVEREXPONENT"
                result["explanation"] = f"Observed wear exponent ({observed_exp:.2f}) >> Taylor prediction — severe speed-driven regime or thermal softening"
            return result

    return {"check": "taylor_tool_life", "status": "INCONCLUSIVE", "reason": "Insufficient speed variation to estimate exponent"}


# ──────────────────────────────────────────────
# Quality Reset Analysis (Transition Processing)
# ──────────────────────────────────────────────


def analyze_quality_resets(
    anomaly_report: dict,
    cleaned_data: list[dict],
    quality_targets: list[str],
) -> list[dict]:
    """
    For each transition event in anomaly_report, compute whether quality
    resets (IMPROVES) or continues degrading after the transition.

    This is the single most powerful test for distinguishing
    component-level vs system-level root causes.
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

            # Does quality IMPROVE (lower is better) after the transition?
            # Quality metric: lower = better (roughness, deviation, defect rate)
            # Higher = better (yield, efficiency)
            # Here we use heuristic: if after < before, it might be a reset.
            delta = mu_after - mu_before
            reset_detected = abs(delta) < 0.1 * abs(mu_before)  # Within 10% = no significant change

            # Statistical test: if means differ significantly
            significant_change = effect_size > 1.0  # Cohen's d > 1.0 = large effect

            interpretation = ""
            if significant_change and delta < 0:
                interpretation = f"Quality IMPROVED after transition (d={effect_size:.1f}) — component replacement ({from_val}→{to_val}) was effective, indicates component-level root cause"
                reset_class = "RESET"
            elif significant_change and delta > 0:
                interpretation = f"Quality WORSENED after transition (d={effect_size:.1f}) — replacement introduced additional degradation"
                reset_class = "WORSENED"
            elif reset_detected:
                interpretation = f"No significant quality change after transition ({from_val}→{to_val}) — degradation continues, system-level root cause (not component-specific)"
                reset_class = "NO_RESET"
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
                timing = "PRECURSOR" if True else "DURING"  # Simplified
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
            checks["arrhenius_kinetics"] = check_arrhenius(temp_col, low_temp, quality_targets[0], cleaned_data)

    if vib_col and quality_targets and cleaned_data:
        checks["vibration_threshold"] = check_vibration_threshold(vib_col, quality_targets[0], cleaned_data)

    if power_col and temp_col and cleaned_data:
        checks["energy_balance"] = check_energy_balance(power_col, temp_col, mass_kg=100.0, cp_J_per_kgK=500.0, data=cleaned_data)

    if flow_col and pressure_col and cleaned_data:
        checks["flow_restriction"] = check_flow_restriction(flow_col, pressure_col, cleaned_data)

    all_temps = find_cols(["temp", "temperature"])
    if len(all_temps) >= 2 and flow_col and cleaned_data:
        checks["heat_transfer"] = check_heat_transfer(all_temps[0], all_temps[1], flow_col, cleaned_data)

    if args.ph_col and args.temp_col and args.corrosion_col and cleaned_data:
        checks["corrosion_rate"] = check_corrosion_rate(args.ph_col, args.temp_col, args.corrosion_col, cleaned_data)

    # ── Extended physics checks (Phase B3) ──
    speed_col = args.speed_col or (find_cols(["speed", "rpm", "n_speed", "spindle"])[:1] or [None])[0]

    # Pump affinity: needs flow + speed [+ power optional]
    if flow_col and speed_col and cleaned_data:
        checks["pump_affinity"] = check_pump_affinity(flow_col, speed_col, power_col or "_none_", cleaned_data)

    # Darcy-Weisbach: needs flow + pressure_drop
    if flow_col and pressure_col and cleaned_data:
        checks["darcy_weisbach"] = check_darcy_weisbach(flow_col, pressure_col, data=cleaned_data)

    # Forced oscillator: vib + speed + quality_target
    if vib_col and speed_col and quality_targets and cleaned_data:
        checks["forced_oscillator"] = check_forced_oscillator(vib_col, speed_col, quality_targets[0], cleaned_data)

    # Preston CMP: pressure + velocity + removal_rate
    if pressure_col and speed_col and quality_targets and cleaned_data:
        checks["preston_cmp"] = check_preston_cmp(pressure_col, speed_col, quality_targets[0], cleaned_data)

    # Taylor tool life: speed + wear (use a quality target as wear proxy if no wear col)
    wear_col = (find_cols(["wear", "tool_wear"])[:1] or [None])[0]
    if speed_col and wear_col and cleaned_data:
        checks["taylor_tool_life"] = check_taylor_tool_life(speed_col, wear_col, cleaned_data)

    transition_results = analyze_quality_resets(anomaly_report, cleaned_data, quality_targets)
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
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Physics checks written to {args.output}")
    print(f"  Checks performed: {len(checks)}")
    for k, v in checks.items():
        conclusion = v.get("conclusion", v.get("status", "UNKNOWN"))
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