"""imacore.actions — assembly of the advisory report (method_notes §1-6, §8).

Responsibilities:
  * per (lever, target-KPI) evidence assembly via the three gates
  * grade decision (grade_from_inputs — the canonical rule table mirrored by
    quality_gate.mjs; any change here MUST be mirrored there)
  * magnitude / expected-gain (CI95, honest not_estimable=null)
  * prescription triggers (8-item list) and excluded_levers disclosure
  * affected-KPI disclosure + Goodhart tradeoff cap
  * evidence waterline, report status, optimizer_seed.json
"""

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import _io, chains, evidence, levers as levers_mod, objective as objective_mod
from . import rank


# ------------------------------------------------------------ grade (canonical)

def grade_from_inputs(gi):
    """Canonical grade rule (method_notes §1). Mirrored in quality_gate.mjs.

    A: data gate fully pass (temporal True, or randomized design evidence
       with temporal not False) ∧ physics known ∧ intervention evidence
       (attribution estimable+CI∌0 OR designed window OR designed DOE effect)
       ∧ gain CI ∌0 ∧ not inferred/conflict/extrapolated/dead_time_missing/tradeoff
    B: data core pass ∧ temporal True|None ∧ physics known|same_domain ∧
       gain CI ∌0 ∧ not conflict/inferred/tradeoff
    C: everything else that still has a relation
    """
    data = gi["data"]
    phys = gi["physics"]["status"]
    attr = gi["attribution"]
    flags = gi["flags"]
    data_core = all(bool(data.get(k)) for k in
                    ("lever_variance_ok", "samples_ok", "fdr_ok",
                     "confound_ok", "regime_stable_ok"))
    temporal = data.get("temporal_ok")
    gain_ok = bool(flags.get("gain_ci_excludes_zero"))
    intervention = ((attr.get("status") == "estimable"
                     and attr.get("ci_excludes_zero") is True)
                    or bool(flags.get("designed_window"))
                    or bool(flags.get("designed_effect")))
    # Designed evidence (randomized first-order coefficient): randomization
    # replaces observational temporal precedence, so temporal=None counts as
    # satisfied for the A path; an explicit temporal=False still fails it.
    temporal_ok_for_a = temporal is True or (
        flags.get("designed_effect") and temporal is not False)
    dead_time_ok = (not flags.get("dead_time_missing")
                    or bool(flags.get("designed_effect")))
    if (data_core and temporal_ok_for_a and phys == "known" and intervention
            and gain_ok and not flags.get("objective_inferred")
            and not flags.get("conflict") and not flags.get("extrapolated")
            and dead_time_ok
            and not flags.get("tradeoff_declared")):
        return "A"
    if (data_core and temporal in (True, None)
            and phys in ("known", "same_domain") and gain_ok
            and not flags.get("conflict")
            and not flags.get("tradeoff_declared")):
        return "B"
    return "C"


def grade_reasons(gi, grade):
    """Human-readable deterministic reasons for the assigned grade."""
    reasons = []
    data = gi["data"]
    flags = gi["flags"]
    if not data.get("lever_variance_ok"):
        reasons.append("杠杆无变异")
    if not data.get("samples_ok"):
        reasons.append("有效样本不足")
    designed = bool(flags.get("designed_effect"))
    if designed:
        reasons.append("随机化设计证据（doe_effect 一阶系数 95%CI）：时间先后/混杂/工况分段由随机化替代")
    elif data.get("temporal_ok") is None:
        reasons.append("dead_time 缺省：时间先后 not_assessable（禁假设 0 放行）")
    elif data.get("temporal_ok") is False:
        reasons.append("滞后 CCF 峰不在 dead-time 窗内")
    if not data.get("fdr_ok"):
        reasons.append("BH-FDR 后不显著")
    if not data.get("confound_ok"):
        reasons.append("分层/LOO 后效应不稳健")
    if not data.get("regime_stable_ok"):
        reasons.append("工况分段方向翻转（direction_uncertain）")
    phys = gi["physics"]["status"]
    if phys == "unknown":
        reasons.append("[MECHANISM_UNKNOWN] 机理未知，封顶 C")
    elif phys == "same_domain":
        reasons.append("机制为同域先验（无方向边），封顶 B")
    attr = gi["attribution"]
    if not designed:
        if attr.get("status") == "absent":
            reasons.append("无动作日志：观察数据最高 B")
        elif attr.get("status") not in (None, "estimable"):
            reasons.append(f"归因状态 {attr.get('status')}：封顶 C")
        elif attr.get("status") == "estimable" and attr.get("ci_excludes_zero") is not True:
            reasons.append("归因 CI 跨 0：不作干预性证据")
    if flags.get("objective_inferred"):
        reasons.append("目标为系统推断（未确认），封顶 B")
    if flags.get("conflict"):
        reasons.append("目标冲突未裁决，封顶 C")
    if flags.get("extrapolated"):
        reasons.append("建议点越数据包络（未验证），封顶 C")
    if flags.get("dead_time_missing") and not designed:
        reasons.append("dead_time 缺省，相关动作封顶 B")
    if flags.get("tradeoff_declared"):
        reasons.append("其他 KPI 显著恶化（Goodhart 防护），封顶 B")
    if not flags.get("gain_ci_excludes_zero"):
        reasons.append("预期收益 CI 跨 0 或不可估")
    if grade == "A":
        reasons = ["三重门全过 + 干预性证据（归因 E2+/设计窗/随机化设计效应）+ 收益 CI 不跨 0"]
    return reasons


# --------------------------------------------------------------- gain legs

def _signed_want(direction, current, target_value):
    if direction == "min":
        return -1
    if direction == "max":
        return 1
    if current is None or target_value is None:
        return 0
    return 1 if target_value > current else (-1 if target_value < current else 0)


def _gain_from_doe_effect(doe_eff, want, delta_signed):
    """Designed-experiment coefficient leg: intervention evidence by design.

    slope/slope_ci95 are raw-unit coefficients from effect_table.json
    (coded coefficient / half-range), so gain math is identical to the dose
    leg — but `verified=True` because randomization makes the estimate
    causal-grade (not observational).
    """
    b = doe_eff.get("slope")
    if b is None or want == 0:
        return None
    point = want * (b * delta_signed)
    ci = None
    excludes = None
    slope_ci = doe_eff.get("slope_ci95") or [None, None]
    if slope_ci[0] is not None and slope_ci[1] is not None:
        c1 = want * (slope_ci[0] * delta_signed)
        c2 = want * (slope_ci[1] * delta_signed)
        lo, hi = min(c1, c2), max(c1, c2)
        ci = [_io.finite(lo, 10), _io.finite(hi, 10)]
        excludes = bool(lo > 0 or hi < 0)
    return {
        "point": _io.finite(point, 10),
        "ci95": ci,
        "method": "doe_effect",
        "verified": True,
        "ci_excludes_zero": excludes,
        "not_estimable_reason": None,
    }


def _gain_from_dose(dose, want, delta_signed):
    b = dose.get("slope")
    if b is None or want == 0:
        return None
    point = want * (b * delta_signed)
    ci = None
    excludes = None
    slope_ci = dose.get("slope_ci95") or [None, None]
    if slope_ci[0] is not None and slope_ci[1] is not None:
        c1 = want * (slope_ci[0] * delta_signed)
        c2 = want * (slope_ci[1] * delta_signed)
        lo, hi = min(c1, c2), max(c1, c2)
        ci = [_io.finite(lo, 10), _io.finite(hi, 10)]
        excludes = bool(lo > 0 or hi < 0)
    return {
        "point": _io.finite(point, 10),
        "ci95": ci,
        "method": "dose_response",
        "verified": bool(dose.get("verified")),
        "ci_excludes_zero": excludes,
        "not_estimable_reason": None,
    }


def _gain_from_window(contrast, want):
    delta = contrast.get("delta_in_minus_out")
    ci = contrast.get("ci95")
    if delta is None or want == 0:
        return None
    point = want * delta
    out_ci, excludes = None, None
    if ci and ci[0] is not None and ci[1] is not None:
        c1, c2 = want * ci[0], want * ci[1]
        lo, hi = min(c1, c2), max(c1, c2)
        out_ci = [_io.finite(lo, 10), _io.finite(hi, 10)]
        excludes = bool(lo > 0 or hi < 0)
    return {
        "point": _io.finite(point, 10),
        "ci95": out_ci,
        "method": "window_contrast",
        "verified": bool(contrast.get("designed")),
        "ci_excludes_zero": excludes,
        "not_estimable_reason": None,
    }


def _gain_from_attribution(records, want, historical_delta, suggested_delta):
    if not records or want == 0:
        return None
    best = None
    for rec in records:
        if rec.get("attribution_status") == "estimable" and rec.get("effect") is not None:
            best = rec
            break
    if best is None:
        return None
    scale = 1.0
    if historical_delta and abs(historical_delta) > 1e-12:
        scale = abs(suggested_delta) / abs(historical_delta)
    point = want * float(best["effect"]) * scale
    ci = best.get("ci95")
    out_ci, excludes = None, None
    if ci and ci[0] is not None and ci[1] is not None:
        c1, c2 = want * ci[0] * scale, want * ci[1] * scale
        lo, hi = min(c1, c2), max(c1, c2)
        out_ci = [_io.finite(lo, 10), _io.finite(hi, 10)]
        excludes = bool(lo > 0 or hi < 0)
    return {
        "point": _io.finite(point, 10),
        "ci95": out_ci,
        "method": "attribution_delta",
        "verified": bool(best.get("ci_excludes_zero")),
        "ci_excludes_zero": excludes,
        "not_estimable_reason": None,
    }


def compute_gain(dose, window_contrast, attr_records, want, delta_signed,
                 historical_delta, doe_eff=None):
    """Priority: designed DOE effect > dose-response > window > attribution.

    The designed effect leg comes first when present: a randomized
    first-order coefficient with a 95% CI is intervention-grade evidence,
    strictly stronger than any observational dose-response fit.
    """
    for leg in (
        _gain_from_doe_effect(doe_eff, want, delta_signed) if doe_eff else None,
        _gain_from_dose(dose, want, delta_signed) if dose else None,
        _gain_from_window(window_contrast, want) if window_contrast else None,
        _gain_from_attribution(attr_records, want, historical_delta,
                               delta_signed) if attr_records else None,
    ):
        if leg is not None:
            return leg
    reason = "reuse_leg_unavailable" if not any(
        (dose, window_contrast, attr_records, doe_eff)) else "no_significant_relation"
    return {"point": None, "ci95": None, "method": "none", "verified": False,
            "ci_excludes_zero": None, "not_estimable_reason": reason}


# ----------------------------------------------------------- magnitude/bounds

def _bounds_for(lever, constraints, window):
    lo = hi = None
    for c in constraints:
        if c.get("param") == lever:
            if c.get("min") is not None:
                lo = float(c["min"]) if lo is None else max(lo, float(c["min"]))
            if c.get("max") is not None:
                hi = float(c["max"]) if hi is None else min(hi, float(c["max"]))
    if window and window.get("range"):
        w_lo, w_hi = window["range"]
        lo = w_lo if lo is None else max(lo, w_lo)
        hi = w_hi if hi is None else min(hi, w_hi)
    return lo, hi


def choose_magnitude(stats, direction_sign, lo, hi):
    """Half an SD, capped at half the remaining room to the nearest bound."""
    from_v = stats.get("q50")
    sd = stats.get("sd")
    if from_v is None or not sd:
        return None
    step = abs(sd) * 0.5
    room = None
    if direction_sign > 0 and hi is not None:
        room = hi - from_v
    elif direction_sign < 0 and lo is not None:
        room = from_v - lo
    if room is not None:
        step = min(step, max(room, 0.0) * 0.5)
    if step <= 1e-12:
        return None
    return from_v + direction_sign * step


def extrapolated_flag(stats, to_value):
    lo, hi = stats.get("min"), stats.get("max")
    mean = stats.get("mean")
    if to_value is None or lo is None or hi is None or mean is None:
        return False
    half = (hi - lo) / 2.0
    if half <= 1e-12:
        return False
    if to_value <= lo + 1e-9 or to_value >= hi - 1e-9:
        return True
    return abs(to_value - mean) / half > _io.CONSTANTS["extrapolation_coded_distance"]


# ------------------------------------------------------------- assembly core

def build(state):
    """Assemble the advisory report dict from analyzer state.

    state keys: df, run_dir, data_path, data_rel, data_sha256, time_col,
    group_col, roles, ontology, ontology_meta, targets, goal_mode,
    inferred_candidates, inference_rationale, dead_time, constraints,
    doe_leg, attr_leg, degradations, limitations, specs, windows,
    memory_conflicts
    """
    const = _io.CONSTANTS
    df = state["df"]
    targets = state["targets"]
    roles = state["roles"]
    dead_time = state.get("dead_time")
    constraints = state.get("constraints") or []
    ontology = state.get("ontology") or {}
    degradations = state["degradations"]
    limitations = state["limitations"]

    excluded_levers = []
    lever_stats = {}
    for lever in roles["levers"]:
        stats = levers_mod.variance_stats(df, lever)
        lever_stats[lever] = stats
        if not levers_mod.has_variance(stats):
            excluded_levers.append({"param": lever, "reason": "no_variance",
                                    "detail": f"cv={stats.get('cv')} nunique={stats.get('nunique')}"})

    # reverse causality per lever (against the primary target KPI)
    primary_kpi = targets[0]["metric"] if targets else None
    surviving = [lv for lv in roles["levers"]
                 if lv not in {e["param"] for e in excluded_levers}]
    excluded_reverse = {}
    for lever in list(surviving):
        if primary_kpi is None:
            break
        rc = levers_mod.reverse_causality(df, lever, primary_kpi,
                                          max_lag=dead_time or 3)
        if rc.get("reverse"):
            excluded_levers.append({
                "param": lever, "reason": "reverse_causality",
                "detail": f"KPI leads lever (neg_lag={rc.get('best_neg_lag')} "
                          f"r={rc.get('best_neg_r')} > pos r={rc.get('best_pos_r')})"})
            excluded_reverse[lever] = rc
            surviving.remove(lever)

    doe_leg = state.get("doe_leg") or {"status": "skipped", "windows": {}}
    attr_leg = state.get("attr_leg") or {"status": "absent", "by_param": {}}
    doe_effects = state.get("doe_effects") or {}
    specs = state.get("specs") or {}
    windows = state.get("windows") or {}
    memory_conflicts = state.get("memory_conflicts") or {}

    actions = []
    prescriptions = []
    dose_evidence = []
    window_notes = []
    pair_records = []
    window_contrasts = []
    pairs_seen = 0
    pairs_significant = 0

    # FDR families per target KPI (all levers × lags)
    for target in targets:
        kpi = target["metric"]
        if kpi not in df.columns:
            continue
        direction = target.get("direction")
        kpi_series = df[kpi].dropna()
        kpi_current = float(kpi_series.median()) if len(kpi_series) else None
        kpi_rho = None
        kpi_neff = None
        if _io.lag1_autocorr is not None and _io.effective_n is not None and len(kpi_series) > 10:
            try:
                kpi_rho = _io.lag1_autocorr(kpi_series.to_numpy())
                kpi_neff = float(_io.effective_n(int(len(kpi_series)), kpi_rho))
            except Exception:
                kpi_rho = None
                kpi_neff = None
        ccf_by_lever = {}
        for lever in surviving:
            max_lag = int(max(1, math.ceil(dead_time))) if dead_time is not None else 3
            ccf_by_lever[lever] = evidence.peak_ccf(df, lever, kpi, max_lag)
        q_by_lever = evidence.fdr_q_for_levers(ccf_by_lever)
        kpi_actions = 0
        for lever in surviving:
            pairs_seen += 1
            ccf = ccf_by_lever[lever]
            pair = evidence.pair_stats(df, lever, kpi)
            q = q_by_lever.get(lever)
            temporal = evidence.temporal_gate(ccf, dead_time)
            fdr_ok = bool(q is not None and q < const["fdr_q"])
            confound = evidence.confound_gate(df, lever, kpi, state.get("group_col"))
            regime = levers_mod.segment_check(df, lever, kpi)
            stats = lever_stats[lever]
            window = (doe_leg.get("windows") or {}).get(lever)
            if window:
                window_notes.append({"lever": lever, "range": window["range"],
                                     "metric": kpi, "designed": window.get("designed")})
            dose = evidence.dose_response(df, lever, kpi)
            if dose.get("status") == "estimable":
                dose_evidence.append({"lever": lever, "metric": kpi,
                                      "bins": dose.get("bins"),
                                      "slope": dose.get("slope"),
                                      "slope_ci95": dose.get("slope_ci95")})
            contrast = (evidence.window_contrast(df, lever, kpi, window)
                        if window else None)
            attr_records = (attr_leg.get("by_param") or {}).get(lever)
            doe_eff = ((doe_effects.get("effects") or {}).get((lever, kpi))
                       if isinstance(doe_effects, dict) else None)
            if doe_eff:
                # Randomized design evidence replaces the observational checks:
                # FDR from the DOE analyzer's own BH q, confound/regime covered
                # by run-order randomization (recorded as such, never invented).
                doe_q = doe_eff.get("q")
                fdr_ok = bool(doe_q is not None and doe_q < const["fdr_q"])
                q = doe_q
                confound = {"ok": True, "available": True,
                            "method": "randomized_design"}
                regime = {"stable": True, "available": True,
                          "method": "randomized_design"}

            relation_strength = abs(pair.get("r") or 0.0)
            if doe_eff:
                pair_ok = bool(doe_eff.get("slope") is not None
                               and doe_eff.get("slope_ci95")
                               and fdr_ok)
            else:
                pair_ok = bool(pair.get("ok") and relation_strength
                               >= const["min_effect_r"] and fdr_ok)
            if fdr_ok and (relation_strength >= const["min_effect_r"]
                           or doe_eff):
                pairs_significant += 1
            if not pair_ok:
                # trigger ②/③ territory — collected once per KPI below
                pair_records.append({
                    "lever": lever, "metric": kpi, "status": "below_threshold",
                    "r": pair.get("r"), "p": pair.get("p"), "fdr_q": q,
                    "temporal_ok": temporal,
                })
                continue

            slope = dose.get("slope") if dose.get("status") == "estimable" else None
            if slope is None and pair.get("r") is not None:
                sub = df[[lever, kpi]].dropna()
                denom = float(np.ptp(sub[lever].to_numpy()))
                if denom > 1e-12:
                    y = sub[kpi].to_numpy()
                    x = sub[lever].to_numpy()
                    slope = float(np.polyfit(x, y, 1)[0]) if len(sub) > 2 else 0.0
                else:
                    slope = 0.0
            slope = slope or 0.0
            req_sign = objective_mod.required_lever_sign(
                direction, slope, current=kpi_current,
                target_value=target.get("target_value"))
            if req_sign == 0:
                prescriptions.append({
                    "prescription_id": f"PRE-{lever}-{kpi}-ATTARGET".replace(" ", "_"),
                    "kind": "data",
                    "detail": (f"KPI {kpi} 已处于目标值（或无可判方向）：无需动作；"
                               f"如需稳定化，请提供规格窗/动作日志以启用稳定性类目标"),
                    "addresses": [f"{lever}:{kpi}"],
                })
                continue
            lo, hi = _bounds_for(lever, constraints, window)
            to_value = choose_magnitude(stats, req_sign, lo, hi)
            if to_value is None:
                prescriptions.append({
                    "prescription_id": f"PRE-{lever}-{kpi}-BOUND".replace(" ", "_"),
                    "kind": "data",
                    "detail": f"杠杆 {lever} 已到约束/数据边界，无法给出可执行幅度；"
                              f"需工程评审放宽约束或补充更宽数据窗",
                    "addresses": [f"{lever}:{kpi}"],
                })
                continue
            delta_signed = to_value - (stats.get("q50") or 0.0)
            extrapolated = extrapolated_flag(stats, to_value)
            want = _signed_want(direction, kpi_current, target.get("target_value"))
            if want == 0:
                want = 1 if req_sign * slope > 0 else -1
            gain = compute_gain(dose, contrast, attr_records, want,
                                delta_signed, None, doe_eff=doe_eff)
            # ambiguity: prefer verified dose/window; attribution never wins over
            # a verified dose leg (already encoded by order in compute_gain)

            slope_sign = 1 if slope > 0 else (-1 if slope < 0 else 0)
            mech = chains.mechanism_for(ontology, lever, kpi, slope_sign)

            attribution_entry = _attribution_summary(attr_records)
            flags = {
                "objective_inferred": state["goal_mode"] == "inferred",
                "conflict": bool((state.get("conflict_levers") or set())
                                 and lever in state["conflict_levers"]),
                "extrapolated": bool(extrapolated),
                "dead_time_missing": dead_time is None,
                "tradeoff_declared": False,
                "designed_window": bool(window and window.get("designed")),
                "designed_effect": bool(doe_eff),
                "gain_ci_excludes_zero": bool(gain.get("ci_excludes_zero")),
            }
            mem_dir = (memory_conflicts or {}).get(lever)
            suggested_dir = "increase" if delta_signed > 0 else "decrease"
            if mem_dir and mem_dir != suggested_dir:
                mech = {"status": "unknown",
                        "reason": "memory_conflict_strong",
                        "chain": mech.get("chain") + [{
                            "step": f"产线记忆强共识方向={mem_dir} 与本次建议方向={suggested_dir} 相反（证据更弱，不晋级）",
                            "ontology_ref": "line_memory.consensus"}],
                        "edges": mech.get("edges")}
            gi = {
                "data": {
                    "lever_variance_ok": True,
                    "samples_ok": bool(
                        stats.get("n") and stats["n"] >= const["min_analysis_rows"]
                        and (kpi_neff is None
                             or kpi_neff >= const["min_relation_points"])),
                    "temporal_ok": temporal,
                    "fdr_ok": fdr_ok,
                    "confound_ok": bool(confound.get("ok")),
                    "regime_stable_ok": bool(regime.get("stable")),
                },
                "physics": {"status": mech["status"]},
                "attribution": attribution_entry,
                "flags": flags,
            }

            # affected KPIs / Goodhart disclosure
            affected, tradeoff = _affected_kpis(df, lever, kpi, delta_signed)
            flags["tradeoff_declared"] = tradeoff
            grade = grade_from_inputs(gi)
            reasons = grade_reasons(gi, grade)
            if mech.get("reason") == "mechanism_contradicted":
                reasons.append("本体声明方向与数据建议方向矛盾（no-contradiction 失败）")

            record = {
                "lever": lever, "metric": kpi, "status": "evaluated",
                "r": pair.get("r"), "p": pair.get("p"), "fdr_q": q,
                "temporal_ok": temporal,
                "n_eff": _io.finite(kpi_neff),
                "rho_lag1": _io.finite(kpi_rho),
                "gates": dict(gi["data"]),
                "physics": dict(gi["physics"]),
                "attribution": dict(gi["attribution"]),
                "flags": dict(flags),
                "dose": ({k: dose.get(k) for k in
                          ("status", "slope", "slope_ci95", "monotone", "verified",
                           "reason", "detail", "bins", "r", "p", "n_pairs")}
                         if dose else None),
                "doe": (dict(doe_eff) if doe_eff else None),
                "window": ({k: contrast.get(k) for k in
                            ("status", "delta_in_minus_out", "ci95", "n_in", "n_out",
                             "designed", "current_in_window", "reason", "detail")}
                           if contrast else None),
            }
            pair_records.append(record)
            if contrast is not None:
                window_contrasts.append({
                    "lever": lever, "metric": kpi,
                    "status": contrast.get("status"),
                    "delta_in_minus_out": contrast.get("delta_in_minus_out"),
                    "ci95": contrast.get("ci95"),
                    "designed": bool(contrast.get("designed")),
                })

            # prescription triggers that replace the action
            if extrapolated and not (dose.get("monotone") and dose.get("verified")):
                record["status"] = "prescribed_extrapolated"
                prescriptions.append({
                    "prescription_id": f"PRE-{lever}-{kpi}-EXTRAP".replace(" ", "_"),
                    "kind": "experiment",
                    "detail": f"{lever}→{kpi} 建议点越数据包络且剂量响应未过单调性；"
                              f"先做设计试验扩展域，再重跑本 skill",
                    "addresses": [f"{lever}:{kpi}"],
                })
                continue
            if mech["status"] == "unknown" and attribution_entry["status"] in ("absent",):
                record["status"] = "prescribed_mechanism"
                kind = "data" if mech.get("reason") == "memory_conflict_strong" else "ontology"
                prescriptions.append({
                    "prescription_id": f"PRE-{lever}-{kpi}-MECH".replace(" ", "_"),
                    "kind": kind,
                    "detail": (f"{lever}→{kpi} 与产线记忆强共识反方向且己方证据更弱；"
                               f"补数据重验或采纳历史共识，不晋级建议"
                               if kind == "data" else
                               f"{lever}→{kpi} 机理未知且无历史归因；先补本体机制边"
                               f"（industrial-ontology-builder）或先做小试验证"),
                    "addresses": [f"{lever}:{kpi}"],
                })
                continue
            if _hits_hard_bound(constraints, lever, to_value):
                record["status"] = "prescribed_safety"
                prescriptions.append({
                    "prescription_id": f"PRE-{lever}-{kpi}-SAFETY".replace(" ", "_"),
                    "kind": "data",
                    "detail": f"{lever} 建议值越过安全限（hard constraint）；"
                              f"禁止执行，需工程变更评审",
                    "addresses": [f"{lever}:{kpi}"],
                })
                continue

            feasibility = rank.feasibility_ratio(to_value, lo, hi, delta_signed)
            action = {
                "action_id": _action_id(lever, kpi),
                "lever_param": _display_name(ontology, lever),
                "lever_column": lever,
                "direction": "increase" if delta_signed > 0 else "decrease",
                "magnitude": {
                    "from": _io.finite(stats.get("q50"), 10),
                    "to": _io.finite(to_value, 10),
                    "delta": _io.finite(delta_signed, 10),
                    "unit": _unit(ontology, lever),
                },
                "expected_gain": {
                    "metric": kpi,
                    "current": _io.finite(kpi_current, 10),
                    "point": gain.get("point"),
                    "ci95": gain.get("ci95"),
                    "method": gain.get("method"),
                    "verified": bool(gain.get("verified")),
                    "not_estimable_reason": gain.get("not_estimable_reason"),
                },
                "evidence_refs": _evidence_refs(lever, kpi, dose, contrast,
                                                attr_records, pair, q, ccf,
                                                doe_eff=doe_eff),
                "mechanism_chain": mech.get("chain") or [],
                "mechanism_status": mech["status"],
                "affected_kpis": affected,
                "grade": grade,
                "grade_reasons": reasons,
                "priority_score": 0.0,  # filled by rank after loop
                "risk": {
                    "assumptions": _assumptions(dead_time, doe_leg, attr_leg),
                    "confidence_cap": {"A": 90, "B": 70, "C": 50}.get(grade, 50),
                },
                "preconditions": _preconditions(lever, kpi, window, doe_leg),
                "side_effects": [f"{a['metric']} 将{'上升' if a['direction'] == 'increase' else '下降'}"
                                 for a in affected if a.get("significant")],
                "verification_plan": {
                    "metric": kpi,
                    "window": ("小试 ≥3 批（同工况确认）" if grade == "B"
                               else "在线连续 ≥24h 对比基线窗"),
                    "threshold": _verification_threshold(gain, kpi),
                },
                "rollback_condition": _rollback(lever, stats, delta_signed, lo, hi),
                "prescription_tags": [],
                "advisory": True,
                "grade_inputs": gi,
                "interpretation": None,
            }
            action["_feasibility"] = feasibility
            action["_evidence_r"] = pair.get("r")
            record["status"] = "emitted"
            record["action_id"] = action["action_id"]
            actions.append(action)
            kpi_actions += 1

        if kpi_actions == 0:
            prescriptions.append({
                "prescription_id": f"PRE-{kpi}-NONE".replace(" ", "_"),
                "kind": "experiment" if pairs_significant == 0 else "data",
                "detail": (f"KPI {kpi} 没有通过门禁的可操作杠杆；"
                           f"先补动作日志/更宽数据窗，或用 doe-analyzer 设计试验分离因果"),
                "addresses": [kpi],
            })

    # rank & cap
    if actions:
        max_abs_point = max((abs(a["expected_gain"]["point"])
                             for a in actions
                             if a["expected_gain"].get("point") is not None),
                            default=0.0)
        for a in actions:
            a["priority_score"] = rank.priority_score(
                a["grade"], a["expected_gain"].get("point"), max_abs_point,
                a.get("_evidence_r"), a.get("_feasibility"))
        actions = rank.sort_and_cap(actions, const["max_actions"])
        for a in actions:
            a.pop("_feasibility", None)
            a.pop("_evidence_r", None)

    # waterline
    waterline = _waterline(state, actions, excluded_levers, pairs_seen,
                           pairs_significant, doe_leg, attr_leg)
    status = "not_actionable"
    if any(a["grade"] in ("A", "B") for a in actions):
        status = "actionable"
    elif any(a["grade"] == "C" for a in actions):
        status = "advisory_only"

    # KPI-level prescriptions when nothing at all survived
    if not actions and not prescriptions:
        prescriptions.append({
            "prescription_id": "PRE-GLOBAL-NONE",
            "kind": "data",
            "detail": "没有任何杠杆-目标关系通过门禁；补 ≥50 行有效数据、动作日志与 dead-time",
            "addresses": [],
        })

    goal = {
        "mode": "inferred" if state["goal_mode"] == "inferred" else "explicit",
        "targets": targets,
        "conflicts": state.get("conflicts") or [],
        "inferred_rationale": state.get("inference_rationale"),
    }
    report = {
        "contract_version": "improvement-advisory/1.0",
        "report_id": _report_id(state),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "advisory",
        "status": status,
        "goal": goal,
        "data": {
            "path": str(state["data_path"]),
            "sha256": state["data_sha256"],
            "n_rows": int(len(df)),
            "n_rows_used": int(len(df)),
            "time_col": state.get("time_col"),
            "levers": list(surviving),
            "kpis": [t["metric"] for t in targets],
            "sampled": False,
        },
        "waterline": waterline,
        "actions": actions,
        "prescriptions": prescriptions,
        "excluded_levers": excluded_levers,
        "degradations": degradations,
        "provenance": {
            "authored_by": "imacore",
            "engine": "industrial-improvement-advisor",
            "ontology": state.get("ontology_meta"),
            "reuses": [f"{k}: {v}" for k, v in _io.REUSE_STATUS.items()],
            "data_source": "raw",
        },
        "limitations": limitations,
        "evidence": {
            "dose_response": dose_evidence,
            "window_notes": window_notes,
            "pairs": pair_records,
            "window_contrasts": window_contrasts,
        },
    }
    return report


# ------------------------------------------------------------------ helpers

def _attribution_summary(records):
    if not records:
        return {"status": "absent", "ci_excludes_zero": None}
    best = records[0]
    for rec in records:
        if rec.get("attribution_status") == "estimable":
            best = rec
            break
    return {"status": best.get("attribution_status") or "not_estimable",
            "ci_excludes_zero": best.get("ci_excludes_zero")}


def _affected_kpis(df, lever, kpi, delta_signed):
    affected = []
    tradeoff = False
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    checked = 0
    for other in numeric:
        if other == lever or other == kpi or checked >= 5:
            continue
        pair = evidence.pair_stats(df, lever, other)
        if not pair.get("ok") or pair.get("r") is None:
            continue
        p_value = pair.get("p")
        if abs(pair["r"]) < _io.CONSTANTS["min_effect_r"] or (
                p_value is None or p_value >= 0.05):
            continue
        checked += 1
        change = 1 if pair["r"] * delta_signed > 0 else -1
        preferred = objective_mod.name_direction(other)
        worsening = ((preferred == "max" and change < 0)
                     or (preferred == "min" and change > 0))
        affected.append({"metric": other,
                         "direction": "increase" if change > 0 else "decrease",
                         "significant": True})
        if worsening:
            tradeoff = True
    return affected, tradeoff


def _hits_hard_bound(constraints, lever, to_value):
    for c in constraints:
        if c.get("param") != lever or not c.get("hard"):
            continue
        if c.get("min") is not None and to_value < float(c["min"]) - 1e-9:
            return True
        if c.get("max") is not None and to_value > float(c["max"]) + 1e-9:
            return True
    return False


def _display_name(ontology, lever):
    signals = chains._flatten_signals(ontology)
    sig = signals.get(lever) or {}
    return sig.get("name") or lever


def _unit(ontology, lever):
    signals = chains._flatten_signals(ontology)
    sig = signals.get(lever) or {}
    return sig.get("unit")


def _action_id(lever, kpi):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(lever))[:32]
    digest = 0
    for ch in f"{lever}:{kpi}":
        digest = (digest * 131 + ord(ch)) % 9973
    return f"ACT-{safe}-{digest % 1000:03d}"


def _report_id(state):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = (state.get("data_sha256") or "sha256:0")[-6:]
    return f"IMA-{stamp}-{digest}"


def _evidence_refs(lever, kpi, dose, contrast, attr_records, pair, q, ccf, doe_eff=None):
    refs = []
    if doe_eff:
        refs.append({"type": "doe_effect",
                     "source_file": "02_analysis/effect_table.json",
                     "finding_id": f"doe:{lever}:{kpi}",
                     "stat": {"slope": doe_eff.get("slope"),
                              "ci95": doe_eff.get("slope_ci95"),
                              "q": doe_eff.get("q"), "n": doe_eff.get("n"),
                              "design": doe_eff.get("design")}})
    if dose and dose.get("status") == "estimable":
        refs.append({"type": "dose_response",
                     "source_file": "02_evidence/dose_response.json",
                     "finding_id": f"dose:{lever}:{kpi}",
                     "stat": {"slope": dose.get("slope"),
                              "ci95": dose.get("slope_ci95"),
                              "monotone": dose.get("monotone"),
                              "r": dose.get("r"), "n": dose.get("n_pairs")}})
    if contrast:
        refs.append({"type": "window_contrast",
                     "source_file": "02_evidence/window_check.json",
                     "finding_id": f"window:{lever}:{kpi}",
                     "stat": {"delta": contrast.get("delta_in_minus_out"),
                              "ci95": contrast.get("ci95")}})
    if attr_records:
        refs.append({"type": "attribution",
                     "source_file": "06_experience/attribution",
                     "finding_id": attr_records[0].get("action_log_id"),
                     "stat": {"status": attr_records[0].get("attribution_status"),
                              "effect": attr_records[0].get("effect"),
                              "ci95": attr_records[0].get("ci95")}})
    peak = (ccf or {}).get("peak") or {}
    refs.append({"type": "dose_response",
                 "source_file": "02_evidence/dose_response.json",
                 "finding_id": f"ccf:{lever}:{kpi}",
                 "stat": {"r": pair.get("r"), "p": pair.get("p"),
                          "fdr_q": q, "peak_lag": peak.get("lag"),
                          "peak_r": peak.get("r")}})
    return refs


def _assumptions(dead_time, doe_leg, attr_leg):
    out = ["线性剂量响应假设（分箱中位斜率）"]
    if dead_time is None:
        out.append("dead_time 未提供：时间先后条件未评估（禁假设 0）")
    if doe_leg.get("status") != "used":
        out.append("无 DOE 操作窗对照")
    if attr_leg.get("status") != "used":
        out.append("无动作日志归因")
    return out


def _preconditions(lever, kpi, window, doe_leg):
    out = [f"工况与本次数据窗一致（物料/批次/设备状态）"]
    if window:
        out.append(f"{lever} 建议值保持在操作窗 {window['range']} 内或经确认可放宽")
    if doe_leg.get("status") != "used":
        out.append("未使用 DOE 操作窗：以数据包络为界")
    return out


def _verification_threshold(gain, kpi):
    point = gain.get("point")
    if point is None:
        return "方向验证：监控目标 KPI 变化方向，连续 3 批同向视为初步有效"
    return f"目标 {kpi} 改善 ≥ {abs(point) * 0.5:.4g}（点估计的 50%）视为有效"


def _rollback(lever, stats, delta_signed, lo, hi):
    base = stats.get("q50")
    if base is None:
        return "出现任何质量/安全指标恶化即回退至调整前设定"
    back = base
    return (f"若调整后 {lever} 输出未按预期改善或任一受约束指标恶化，"
            f"回退至 {back}（调整前中位），并复核工况前提")


def _waterline(state, actions, excluded_levers, pairs_seen,
               pairs_significant, doe_leg, attr_leg):
    attr_available = attr_leg.get("status") == "used"
    mechanism_edges = 0
    ontology = state.get("ontology") or {}
    sigs = chains._flatten_signals(ontology)
    mechanism_edges = sum(1 for s in sigs.values() if s.get("physical_meaning"))
    designed = bool(doe_leg.get("designed_available"))
    dead_time_provided = state.get("dead_time") is not None
    objective_confirmed = state["goal_mode"] == "explicit"
    if not actions:
        max_grade = "none"
    elif (objective_confirmed and dead_time_provided
          and (attr_available or designed) and mechanism_edges > 0
          and pairs_significant > 0):
        max_grade = "A"
    elif pairs_significant > 0 and mechanism_edges > 0:
        max_grade = "B"
    else:
        max_grade = "C"
    note_bits = []
    note_bits.append("归因腿可用" if attr_available else "无动作日志：观察数据最高 B")
    note_bits.append("dead_time 已提供" if dead_time_provided
                     else "dead_time 缺省：时间先后未评估，相关动作封顶 B")
    note_bits.append("设计窗可用" if designed else "无设计试验窗")
    note_bits.append("目标已显式声明" if objective_confirmed
                     else "目标为系统推断：全部建议封顶 B")
    return {
        "max_achievable_grade": max_grade,
        "factors": {
            "attribution_available": attr_available,
            "mechanism_edges": int(mechanism_edges),
            "dead_time_provided": dead_time_provided,
            "designed_window_available": designed,
            "objective_confirmed": objective_confirmed,
        },
        "note": "；".join(note_bits),
    }


def build_optimizer_seed(report, lever_stats):
    """Serialize the top A/B action into an optimizer-loop O-G1 objective."""
    candidates = [a for a in report["actions"] if a["grade"] in ("A", "B")]
    if not candidates:
        return None
    top = candidates[0]
    target = next((t for t in report["goal"]["targets"]
                   if t["metric"] == top["expected_gain"]["metric"]), None)
    if target is None:
        return None
    direction = target.get("direction")
    goal = {"min": "minimize", "max": "maximize", "target": "target"}[direction]
    lever = top["lever_column"]
    stats = lever_stats.get(lever) or {}
    factor = {"name": lever, "type": "numeric",
              "min": stats.get("min"), "max": stats.get("max"),
              "unit": top["magnitude"].get("unit")}
    seed = {
        "contract_version": "1.0",
        "campaign_id": f"OPT-{datetime.now(timezone.utc):%Y%m%d}-001",
        "target_metric": top["expected_gain"]["metric"],
        "goal": goal,
        "target_range": None,
        "tolerance": target.get("tolerance"),
        "factors": [factor],
        "constraints": [],
        "budget": {"max_rounds": 5, "max_trials": 30},
        "prior": {
            "advisory_report_id": report["report_id"],
            "advisory_action_id": top["action_id"],
            "advisory_expected_gain": top["expected_gain"],
        },
        "seed": 42,
        "note": "由 improvement-advisory 自动生成：验证型 campaign 种子（需人工确认后使用）",
    }
    if direction == "target" and target.get("target_value") is not None:
        tol = target.get("tolerance") or 0.0
        seed["target_range"] = [target["target_value"] - tol,
                                target["target_value"] + tol]
        seed["tolerance"] = None
    return seed
