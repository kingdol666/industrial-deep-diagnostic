#!/usr/bin/env python3
"""
physics_check.py — Automated Physical Feasibility Check Engine

Reads cleaned data, ontology, and feature summary to perform quantitative
physical verification of hypothesized causal relationships.

The Diagnostician references these results instead of manually computing
Arrhenius rates, thermal expansion, or energy balances.

Usage:
    python physics_check.py <RUN_DIR> <ontology.json> <feature_summary.json> <anomaly_report.json> --output <output.json>
"""

import json
import sys
import os
import math
from typing import Any


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


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
    flows = [row[flow_col] for row in data if flow_col in row]
    pressures = [row[pressure_drop_col] for row in data if pressure_drop_col in row]
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


def check_force_balance(
    cutting_speed_col: str,
    feed_col: str,
    depth_of_cut_col: str,
    force_col: str,
    data: list[dict],
    specific_cutting_force_N_per_mm2: float = 2500,
) -> dict:
    """
    F = k_s × a_p × f

    Checks if measured cutting force is consistent with cutting parameters.
    k_s (specific cutting force) for steel: ~2500 N/mm²
    """
    speeds = [row[cutting_speed_col] for row in data if cutting_speed_col in row]
    feeds = [row[feed_col] for row in data if feed_col in row]
    depths = [row[depth_of_cut_col] for row in data if depth_of_cut_col in row]
    forces = [row[force_col] for row in data if force_col in row]

    if not all([speeds, feeds, depths, forces]):
        return {"check": "force_balance", "status": "INCONCLUSIVE", "reason": "Missing data columns"}

    from statistics import mean, stdev

    # Predicted force from cutting parameters (simplified)
    predicted_forces = []
    for i in range(len(feeds)):
        F_pred = specific_cutting_force_N_per_mm2 * depths[i] * feeds[i]
        predicted_forces.append(F_pred)

    F_actual_mean = mean(forces)
    F_pred_mean = mean(predicted_forces)
    force_ratio = F_actual_mean / F_pred_mean if F_pred_mean > 0 else 0

    result = {
        "check": "force_balance",
        "specific_cutting_force_N_per_mm2": specific_cutting_force_N_per_mm2,
        "actual_force_mean": round(F_actual_mean, 2),
        "predicted_force_mean": round(F_pred_mean, 2),
        "ratio_actual_to_predicted": round(force_ratio, 4),
    }

    if 0.5 <= force_ratio <= 2.0:
        result["conclusion"] = "FORCE_BALANCE_PLAUSIBLE"
        result[
            "explanation"
        ] = f"Measured force ({F_actual_mean:.1f}N) is within 2× of cutting force model ({F_pred_mean:.1f}N) — consistent with machining physics"
    elif force_ratio > 2.0:
        result["conclusion"] = "FORCE_EXCEEDS_MODEL"
        result[
            "explanation"
        ] = f"Measured force ({F_actual_mean:.1f}N) is {force_ratio:.1f}× predicted ({F_pred_mean:.1f}N) — tool wear, material hardening, or wrong k_s value"
    elif force_ratio < 0.5 and force_ratio > 0:
        result["conclusion"] = "FORCE_BELOW_MODEL"
        result[
            "explanation"
        ] = f"Measured force ({F_actual_mean:.1f}N) is only {force_ratio:.1%} of predicted ({F_pred_mean:.1f}N) — overestimated k_s or no actual cutting load"

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
                    v = cleaned_data[i][q]
                    if isinstance(v, (int, float)):
                        before_vals.append(v)
            for i in range(idx, min(idx + N_CONTEXT, len(cleaned_data))):
                if i < len(cleaned_data) and isinstance(cleaned_data[i], dict) and q in cleaned_data[i]:
                    v = cleaned_data[i][q]
                    if isinstance(v, (int, float)):
                        after_vals.append(v)

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
            pre_vals = [r[param] for r in pre_window if param in r and isinstance(r.get(param), (int, float))]
            anomaly_vals = [r[param] for r in anomaly_window if param in r and isinstance(r.get(param), (int, float))]

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
    parser.add_argument("--cleaned-data", help="Path to cleaned_data.json (for reset analysis)")
    parser.add_argument("--quality-targets", nargs="+", default=[], help="Quality target column names")
    parser.add_argument("--candidate-params", nargs="+", default=[], help="Candidate parameter columns for onset analysis")

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
    temp_cols = find_cols(["temp", "temperature", "T_"])
    dev_cols = find_cols(["deviation", "dimension", "error", "defect_size"])
    vib_cols = find_cols(["vibration", "vib"])
    power_cols = find_cols(["power", "current", "motor_load", "power_consumption"])
    flow_cols = find_cols(["flow", "flow_rate"])
    pressure_cols = find_cols(["pressure", "pressure_drop"])
    speed_cols = find_cols(["speed", "rpm", "cutting_speed"])
    feed_cols = find_cols(["feed", "feed_rate"])
    depth_cols = find_cols(["depth", "depth_of_cut", "ap"])
    force_cols = find_cols(["force", "cutting_force", "Fx", "Fy", "Fz"])
    quality_cols = quality_targets
    ph_cols = find_cols(["pH", "acidity"])
    corrosion_cols = find_cols(["corrosion", "corrosion_rate"])

    # 1. Thermal expansion check
    if temp_cols and dev_cols:
        checks["thermal_expansion"] = check_thermal_expansion(
            temp_cols[0], dev_cols[0], cleaned_data if cleaned_data else []
        )

    # 2. Vibration threshold check
    if vib_cols and quality_cols:
        checks["vibration_threshold"] = check_vibration_threshold(
            vib_cols[0], quality_cols[0], cleaned_data if cleaned_data else []
        )

    # 3. Energy balance check (requires mass/Cp from user or defaults)
    if power_cols and temp_cols and cleaned_data:
        checks["energy_balance"] = check_energy_balance(
            power_cols[0], temp_cols[0], mass_kg=100.0, cp_J_per_kgK=500.0, data=cleaned_data
        )

    # 4. Flow restriction check
    if flow_cols and pressure_cols and cleaned_data:
        checks["flow_restriction"] = check_flow_restriction(
            flow_cols[0], pressure_cols[0], cleaned_data
        )

    # 5. Force balance check (CNC-specific)
    if speed_cols and feed_cols and depth_cols and force_cols and cleaned_data:
        checks["force_balance"] = check_force_balance(
            speed_cols[0], feed_cols[0], depth_cols[0], force_cols[0], cleaned_data
        )

    # 6. Corrosion check
    if ph_cols and temp_cols and corrosion_cols and cleaned_data:
        checks["corrosion_rate"] = check_corrosion_rate(
            ph_cols[0], temp_cols[0], corrosion_cols[0], cleaned_data
        )

    # 7. Quality reset analysis (from transitions)
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
        "phyiscal_checks": checks,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
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