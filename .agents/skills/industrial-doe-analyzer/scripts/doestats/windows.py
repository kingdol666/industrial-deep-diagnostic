"""Operating-window derivation + downstream recommendations contract.

Legacy entry points (v1.0, byte-for-byte frozen — 136 assertions in
tests/run_tests.py consume them directly):
Designed mode (W1-W5): one-sided-95%-CI feasible region per response, grid
desirability with L-BFGS-B refinement, per-factor window projection of the
{feasible AND D >= 0.8*Dmax} set (connected-block rule), linear-only downgrade.
Observational mode (W6-W8): top-K steady segments by Cpk/goal score, P10-P90
factor windows within pooled selected segments, tercile delta with Welch CI
(stratified when a group column exists), confirmation always required.

v1.1 layer (contract docs/plans/contracts/README.md §5/§6/§9; entry points
`designed_windows_v11` / `observational_windows_v11` / `windows_seed_export`):
four separated interval types (effect CI / mean CI / prediction interval with the
`1 +` term / 95-95 tolerance interval), joint windows + joint setpoints chosen on
the unit-free desirability scale, executed constraints (box/linear/safety,
hard/soft) at every stage, design-hull filtering with leverage diagnostics,
bounded adaptive grid scaling with disclosed deferrals, unit status gating
`actionable`, and a zero-silent-cell factor x response matrix.
"""

import copy
import json
import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import design_detect as dd_mod
from . import effects_anova as ea_mod
from . import rsm as rsm_mod
from ._stats_util import normal_tolerance_factor, welch_delta_ci

EFFECT_GATE_ETA2 = 0.01   # C5 effect-size gate (partial eta^2)
CONF_LEGEND = {
    "high": "q<0.05 且效应量过门槛且（designed）resolution>=V/full",
    "medium": "其余可估计情形",
    "low": "observational 或任一检查未过（必须确认试验）",
}


# ------------------------------------------------------------------ shared

def _specs_by_response(ctx):
    return {r["col"]: r for r in ctx.get("responses", [])}


def _unit_of(ctx, response):
    spec = _specs_by_response(ctx).get(response, {})
    return spec.get("unit") or "response units"


def _c7_confidence(q, effect_ok, designed, resolution, all_pass=True):
    if designed:
        if q is not None and q < 0.05 and effect_ok and all_pass and \
                (resolution is None or resolution >= 5):
            return "high"
        if q is not None and q < 0.05 and effect_ok:
            return "medium"
        return "low"
    return "low"


def base_skeleton(mode):
    return {
        "contract_version": "1.0",
        "audience": "downstream_agent",
        "analysis_mode": mode,
        "operating_windows": [],
        "current_baseline": {"point": {}, "distance_to_window": {},
                             "move_instruction": None},
        "setpoints": [],
        "interactions": [],
        "conflicts": [],
        "response_specs": {},
        "confirmations": [],
        "watchlist": [],
        "constraints": [],
        "applicability_domain": {"n_rows": 0, "time_span": None, "regime": None,
                                 "factor_observed_ranges": {}},
        "invalidation_conditions": [],
        "usage_rules": [],
        "provenance": {"input_sha256": None, "script_version": None,
                       "seed": None, "authored_by": "script"},
    }


# ------------------------------------------------------------------ designed

def designed_windows(models, effect_table, profile, ctx, df):
    """W1-W5. Returns (windows, interactions, confirmations, watchlist, setpoints)."""
    resolution = (profile.get("design") or {}).get("resolution")
    design_type = (profile.get("design") or {}).get("design_type")
    factor_info = models[next(iter(models))]["factor_info"] if models else []
    infos = {i["col"]: i for i in factor_info}
    core = [c for c, i in infos.items()
            if not i.get("is_block") and not i.get("is_covariate") and not i["zero_variance"]]

    # active factors: estimable tests with q<0.05 and effect gate, order <= 2
    active, strength = [], {}
    significant_pairs = []
    for fam in effect_table.get("families", []):
        for t in fam.get("tests", []):
            if not t.get("estimable"):
                continue
            q = t.get("q_value_bh")
            eta = t.get("partial_eta_squared") or 0
            if q is None or q >= 0.05 or eta < EFFECT_GATE_ETA2 or t["order"] > 2:
                continue
            significant_pairs.append((fam["response"], t))
            for f in t["term"].split(":"):
                if f in core and f not in active:
                    active.append(f)
                strength[(fam["response"], f)] = max(
                    strength.get((fam["response"], f), 0), abs(eta))
    active_all = active[:4]
    # the grid walks RAW numeric axes only — categorical significant factors get
    # a favored-level setpoint advice instead (no mean/half_range to project)
    cat_active = [f for f in active_all if infos[f]["type"] != "numeric"]
    active = [f for f in active_all if infos[f]["type"] == "numeric"]

    specs = _specs_by_response(ctx)

    def _cat_setpoints():
        out = []
        for f in cat_active:
            mt = _main_test(effect_table, None, f)
            if not (mt and mt.get("coefficient") is not None):
                continue
            info = infos[f]
            resp_best = max(
                ((resp, strength.get((resp, f), 0)) for resp in _resp_names(models)),
                key=lambda x: x[1], default=(None, 0))[0]
            spec = specs.get(resp_best, {}) if resp_best else {}
            goal_sign = -1.0 if spec.get("goal") == "minimize" else 1.0
            favored = (info["levels"][0] if mt["coefficient"] * goal_sign > 0
                       else info["levels"][-1])
            out.append({
                "factor": f, "value": favored,
                "expected_response": {
                    "kind": "categorical_level_choice",
                    "coefficient_coded": mt["coefficient"],
                    "q_value_bh": mt.get("q_value_bh"),
                    "note": f"类别因子 {f}：偏向水平「{favored}」（编码主效应 {mt['coefficient']}）"},
                "confidence": _c7_confidence(mt.get("q_value_bh"), True, True, resolution)})
        return out

    confirmations, watchlist = [], []
    if not active_all:
        watchlist.append({
            "code": "NO_SIGNIFICANT_FACTOR",
            "message": "没有任何因子通过显著性+效应量双重门槛 — 不产出数值窗口",
        })
        confirmations.append({
            "id": "CF-001", "reason": "所有因子均未过显著性/效应量门槛 — 需增大设计或复核响应",
            "reason_code": "linear_only",
            "design_hint": "增加重复或扩大因子水平范围后重跑", "runs": None})
        return [], [], confirmations, watchlist, []
    if not active:
        confirmations.append({
            "id": None,
            "reason": "仅类别因子显著 — 无数值操作窗口，请按 setpoints 选择水平后补做数值寻优试验",
            "reason_code": "linear_only",
            "design_hint": "固定类别因子于有利水平后，对数值因子补做小型 RSM",
            "runs": None})
        return [], [], confirmations, watchlist, _cat_setpoints()

    # linear-only downgrade (W4): no significant curvature/2FI anywhere or tiny df
    min_df_resid = min(m["df_resid"] for m in models.values())
    has_curvature = any(
        t["order"] == 2 and t.get("q_value_bh") is not None and t["q_value_bh"] < 0.05
        and t.get("estimable") for _, t in significant_pairs)
    linear_only = (not has_curvature) or min_df_resid < 3

    # stationary points (informational / grid anchor)
    st_points = {resp: rsm_mod.stationary_point(m) for resp, m in models.items()}
    # full center baseline: EVERY modelable factor gets a value so predict_raw
    # never sees None (non-active factors sit at center; blocks/covariates too)
    center_raw = {}
    for i in factor_info:
        if i["zero_variance"]:
            continue
        if i["type"] == "numeric":
            center_raw[i["col"]] = i["mean"]
        else:
            center_raw[i["col"]] = i["levels"][len(i["levels"]) // 2]
    anchor_raw = dict(center_raw)
    for resp, st in st_points.items():
        if st and st["inside_design_region"] and st["classification"] == "max":
            anchor_raw.update(st["raw"])
            break

    specs = _specs_by_response(ctx)
    predict_fns = {resp: m["predict_raw"] for resp, m in models.items()}
    se_fns = {resp: m.get("se_predict_raw") for resp, m in models.items()}
    t95 = {resp: (m["df_resid"] and sps.t.ppf(0.95, m["df_resid"])) for resp, m in models.items()}

    # grid over active factors (W2/W3)
    grid_n = 9
    axes = [np.linspace(-1.0, 1.0, grid_n) for _ in active]
    pts, ys = [], []
    for combo in itertools.product(*axes):
        raw = dict(anchor_raw)
        for f, v in zip(active, combo):
            raw[f] = infos[f]["mean"] + float(v) * infos[f]["half_range"]
        y_by = {}
        ok = True
        for resp, fn in predict_fns.items():
            yv = fn(raw)
            if yv is None or not np.isfinite(yv):
                ok = False
                break
            y_by[resp] = yv
        if ok:
            pts.append(combo)
            ys.append(y_by)
    if not pts:
        return [], [], confirmations, watchlist + [{
            "code": "GRID_EMPTY", "message": "网格预测全部失败 — 不产出数值窗口"}], []

    grid_lo_hi = {resp: (min(y[resp] for y in ys), max(y[resp] for y in ys)) for resp in ys[0]}

    # W1 per-point feasibility (one-sided 95% CI bound vs limits)
    feas = []
    for combo, y_by in zip(pts, ys):
        raw = _raw_point(combo, active, infos, anchor_raw)
        ok = True
        for resp, yv in y_by.items():
            spec = specs.get(resp, {})
            se_fn = se_fns.get(resp)
            se = se_fn(raw) if se_fn else None
            t = t95.get(resp) or 1.64
            lo_b = yv - (t * se if se is not None else 0.0)
            hi_b = yv + (t * se if se is not None else 0.0)
            if spec.get("lsl") is not None and lo_b < spec["lsl"]:
                ok = False
            if spec.get("usl") is not None and hi_b > spec["usl"]:
                ok = False
        feas.append(ok)
    feas = np.array(feas)

    # W2 desirability on the grid + L-BFGS-B refinement
    D = [rsm_mod.combined_desirability(y_by, specs, grid_lo_hi)[0] for y_by in ys]
    Dmax = max(D) if D else 0.0
    refined = None
    if len(models) >= 1 and Dmax > 0:
        try:
            refined = rsm_mod.refine_optimum(predict_fns, specs, factor_info,
                                             active, anchor_raw, grid_lo_hi)
        except Exception:
            refined = None
    # W3 candidate set: feasible AND D >= 0.8*Dmax (or top-decile responses when
    # no goals/specs give a meaningful D surface)
    if Dmax > 0:
        cand = feas & (np.array(D) >= 0.8 * Dmax)
    else:
        cand = feas
    if not cand.any():
        cand = feas
    if not cand.any():
        watchlist.append({"code": "NO_FEASIBLE_POINT",
                          "message": "无满足规格置信界的网格点 — 窗口降级为方向建议"})
        cand = np.ones(len(pts), dtype=bool)

    windows = []
    for f in active:
        vals = np.array([p[active.index(f)] for p, keep in zip(pts, cand) if keep])
        if vals.size == 0:
            continue
        lo_c, hi_c = float(vals.min()), float(vals.max())
        shape = _connected_shape(vals, grid_n)
        lo_raw = infos[f]["mean"] + lo_c * infos[f]["half_range"]
        hi_raw = infos[f]["mean"] + hi_c * infos[f]["half_range"]
        if shape == "disconnected":
            watchlist.append({
                "code": "DISCONNECTED_WINDOW",
                "message": f"因子 {f} 的可行集不连通 — 仅报告含最优点的连通块",
                "factor": f})
        # response attribution: strongest significant response for this factor
        resp_best = max(
            ((resp, strength.get((resp, f), 0)) for resp in _resp_names(models)),
            key=lambda x: x[1], default=(None, 0))[0]
        main_test = _main_test(effect_table, resp_best, f)
        coef = (main_test or {}).get("coefficient")
        q = (main_test or {}).get("q_value_bh")
        eta = (main_test or {}).get("partial_eta_squared")
        hr = infos[f]["half_range"]
        delta_raw = round(coef / hr, 6) if coef is not None and hr else None
        all_pass = True
        windows.append({
            "id": None,  # assigned by caller
            "priority": None,
            "factor": f,
            "factor_unit": infos[f].get("unit"),
            "response": resp_best,
            "range": [round(lo_raw, 6), round(hi_raw, 6)],
            "shape": shape,
            "expected_effect": {
                "delta": delta_raw,
                "direction_semantics": f"因子 {f} 每增加 1 个原始单位，响应 {resp_best} 变化约 {delta_raw}（编码主效应 {coef}/半极差 {round(hr, 6)}）",
                "ci95": None,
                "unit": _unit_of(ctx, resp_best) if resp_best else None,
            },
            "confidence": _c7_confidence(q, eta is not None and eta >= EFFECT_GATE_ETA2,
                                         True, resolution),
            "fdr_q": q,
            "sample_size": (main_test or {}).get("n"),
            "evidence_refs": [f"effect_table.json#{resp_best}.{f}.main"] if resp_best else [],
            "extrapolation": bool(lo_c <= -1.0 + 1e-9 or hi_c >= 1.0 - 1e-9),
            "confirmation_needed": False,
            "notes": None,
        })

    # W4 downgrade artifacts
    if linear_only:
        confirmations.append({
            "id": None, "reason": "模型仅线性项可估（无显著曲率/交互或残差自由度不足）— 数值窗口置信有限",
            "reason_code": "linear_only",
            "design_hint": "补中心点与轴点升级为 RSM（布点数 = 未估项数 + 5）",
            "runs": int(len(models) * 0 + len(active) + 5)})
        for f in active:
            mt = _main_test(effect_table, None, f)
            if mt and mt.get("coefficient") is not None:
                windows_note = None  # direction advice carried by expected_effect
    # W4 directional advice into watchlist when linear_only
    if linear_only:
        for f in active:
            for resp in _resp_names(models):
                mt = _main_test(effect_table, resp, f)
                if mt and mt.get("coefficient") is not None:
                    se = mt.get("std_err")
                    ci = ([round((mt["coefficient"] - 2 * se) / infos[f]["half_range"], 6),
                           round((mt["coefficient"] + 2 * se) / infos[f]["half_range"], 6)]
                          if se else None)
                    watchlist.append({
                        "code": "DIRECTION_ONLY",
                        "message": (f"线性模型方向建议：因子 {f} 每增加 1 原始单位，响应 {resp} "
                                    f"变化 {round(mt['coefficient'] / infos[f]['half_range'], 6)}（CI95 约 {ci}，编码单位）"),
                        "factor": f, "response": resp, "threshold": None})

    # interactions (significant 2FI)
    interactions = []
    for resp, t in significant_pairs:
        if t["order"] == 2 and ":" in t["term"]:
            interactions.append({
                "pair": t["term"].split(":"),
                "nature": f"交互显著（q={t.get('q_value_bh')}, partial η²={t.get('partial_eta_squared')}），{resp} 的因子效应随另一因子水平变化",
                "q_value_bh": t.get("q_value_bh")})

    # setpoints: refined optimum (W2) + categorical level choices + stationary info
    setpoints = _cat_setpoints()
    if refined and refined.get("D", 0) > 0:
        setpoints.append({
            "factor": "MULTI",
            "value": 0.0,
            "expected_response": refined,
            "confidence": "medium"})
    for resp, st in st_points.items():
        if st and st.get("warning"):
            watchlist.append({
                "code": "STATIONARY_POINT_WARNING",
                "message": f"响应 {resp}: {st['warning']}",
                "response": resp})

    return windows, interactions, confirmations, watchlist, setpoints


def _raw_point(combo, active, infos, anchor_raw):
    raw = dict(anchor_raw)
    for f, v in zip(active, combo):
        raw[f] = infos[f]["mean"] + float(v) * infos[f]["half_range"]
    return raw


def _connected_shape(vals, grid_n):
    """Bins with an interior empty-run > 1 => disconnected."""
    hist, _ = np.histogram(vals, bins=grid_n)
    occupied = hist > 0
    idx_occ = np.where(occupied)[0]
    if idx_occ.size <= 1:
        return "connected"
    first, last = idx_occ[0], idx_occ[-1]
    gaps = 0
    run = 0
    for o in occupied[first:last + 1]:
        run = 0 if o else run + 1
        gaps = max(gaps, run)
    return "connected" if gaps <= 1 else "disconnected"


def _resp_names(models):
    return list(models.keys())


def _main_test(effect_table, response, factor):
    for fam in effect_table.get("families", []):
        if response and fam["response"] != response:
            continue
        for t in fam.get("tests", []):
            if t["term"] == factor:
                return t
    return None


# ------------------------------------------------------------------ observational

def observational_windows(stability, profile, ctx, df, correlation=None):
    """W6-W8. Returns (windows, interactions, confirmations, watchlist, setpoints).

    `correlation` (optional, the correlation_report dict) drives the
    trend-confounded block: a pair whose raw correlation collapses after
    detrending (trend_confounded=True AND |detrended_r| < 0.1) must NOT emit a
    window — the tercile delta would ride the shared time trend — and is
    demoted to a watchlist entry instead.
    """
    confirmations, watchlist = [], []
    specs = _specs_by_response(ctx)
    pair_map = {(p.get("target"), p.get("parameter")): p
                for p in ((correlation or {}).get("pairs") or [])
                if isinstance(p, dict)}
    selected = [s for s in stability.get("steady_segments", []) if s.get("selected_for_windows")]
    if not selected:
        confirmations.append({
            "id": None, "reason": "未检出稳态段 — 无法产出可信窗口", "reason_code": "observational",
            "design_hint": "按当前工况补做小型试验设计（因子数 + 2 个中心点）",
            "runs": None})
        return [], [], confirmations, watchlist + [{
            "code": "NO_STEADY_SEGMENTS",
            "message": "无稳态段可用 — 建议基于全部数据的方向性结论并安排确认试验"}], []

    pooled_idx = np.concatenate([np.arange(s["start"], s["end"] + 1) for s in selected])
    sub = df.iloc[pooled_idx]
    numeric_predictors = [c for c in ctx.get("_predictor_cols", []) if c in sub.columns]
    numeric_predictors = [c for c in numeric_predictors
                          if pd.to_numeric(sub[c], errors="coerce").nunique() > 2][:8]
    group_col = ctx.get("group_col")
    targets = [r["col"] for r in ctx.get("responses", []) if r["col"] in sub.columns]
    if not targets:
        targets = []

    windows = []
    for resp in targets:
        y = pd.to_numeric(sub[resp], errors="coerce")
        for f in numeric_predictors:
            x = pd.to_numeric(sub[f], errors="coerce")
            ok = x.notna() & y.notna()
            x, yv = x[ok], y[ok]
            if len(x) < 30:
                continue
            # trend-confounded hard block: a STRONG raw correlation (|r|>=0.3)
            # that collapses after detrending (|detrended_r|<0.1) must not emit
            # a window — the tercile delta rides the shared time trend. Weak-raw
            # pairs are already dropped later by the meaningful-CI gate.
            pair_info = pair_map.get((resp, f))
            raw_r = pair_info.get("r") if pair_info else None
            if pair_info is not None and pair_info.get("trend_confounded") is True \
                    and raw_r is not None and abs(raw_r) >= 0.3:
                det_r = pair_info.get("detrended_r")
                if det_r is None or abs(det_r) < 0.1:
                    watchlist.append({
                        "code": "TREND_CONFOUNDED_NO_WINDOW",
                        "message": (f"{resp}~{f} 原始 r={raw_r} 主要由共同时间趋势驱动"
                                    f"（去趋势 r={det_r}，|detrended_r|<0.1）— 不产出操作窗口，"
                                    f"仅列入观察清单等待去趋势后复核"),
                        "factor": f, "response": resp, "threshold": "0.1"})
                    continue
            lo, hi = np.percentile(x, [10, 90])
            ci = _stratified_tercile_delta(x.to_numpy(), yv.to_numpy(),
                                           sub.loc[ok, group_col].astype(str).to_numpy()
                                           if group_col and group_col in sub.columns else None)
            if ci["delta"] is None or ci["ci"] is None:
                continue  # tercile/Welch not estimable (group too small) — skip quietly
            spec = specs.get(resp, {})
            goal = spec.get("goal")
            slope_sign = 1.0 if (goal != "minimize") else -1.0
            delta = ci["delta"] * slope_sign
            meaningful = ci["ci"] and ci["ci"][0] * ci["ci"][1] > 0  # CI excludes 0
            if not meaningful:
                continue
            # P0-1: the goal correction flips the sign of the point estimate for
            # minimize — the CI must flip with it (endpoints swap + negate), so the
            # reported interval brackets the corrected delta. `meaningful` stays
            # computed on the RAW CI: sign flip does not change zero-exclusion.
            ci_corr = ci["ci"]
            if slope_sign < 0 and ci_corr:
                ci_corr = [round(-ci_corr[1], 6), round(-ci_corr[0], 6)]
            windows.append({
                "id": None, "priority": None,
                "factor": f, "factor_unit": None,
                "response": resp,
                "range": [round(float(lo), 6), round(float(hi), 6)],
                "shape": "connected",
                "expected_effect": {
                    "delta": round(float(delta), 6),
                    "direction_semantics": (f"观察性结论：{f} 处于窗内上三分位 vs 下三分位时，"
                                            f"{resp} 均值差为 {ci['delta']:.4g}（方向已按目标校正）"),
                    "ci95": ci_corr,
                    "unit": _unit_of(ctx, resp),
                },
                "confidence": "low",  # C7: observational -> always low
                "fdr_q": None,
                "sample_size": int(ci["n"]),
                "evidence_refs": [f"correlation_report.json#{resp}.{f}",
                                  "stability_report.json#steady_segments"],
                "extrapolation": False,
                "confirmation_needed": True,  # G4 hard rule
                "notes": f"窗口取自 {len(selected)} 个最优稳态段的 P10-P90",
            })
    windows.sort(key=lambda w: abs(w["expected_effect"]["delta"] or 0), reverse=True)
    if windows:
        confirmations.append({
            "id": None, "reason": "全部窗口来自观察性数据（相关级证据）— 闭环执行前必须确认",
            "reason_code": "observational",
            "design_hint": "在窗口中点附近做确认试验（每因子 ±半窗宽两点 + 中心点，2 次重复）",
            "runs": int(min(12, 2 * len({w['factor'] for w in windows}) + 2))})
    watchlist.append({
        "code": "OBSERVATIONAL_EVIDENCE",
        "message": "本合同全部窗口为观察性（相关级）结论 — 不得在确认试验前直接闭环执行"})
    return windows, [], confirmations, watchlist, []


def _stratified_tercile_delta(x, y, groups):
    """W8: delta = E[y | x in Q3] - E[y | x in Q1]; stratified when groups given."""
    q1, q3 = np.percentile(x, [33.33, 66.67])
    if groups is None:
        res = welch_delta_ci(y[x >= q3], y[x <= q1])
        if not res:
            return {"delta": None, "ci": None, "n": int(len(x))}
        d, lo, hi, n_hi, n_lo = res
        return {"delta": round(float(d), 6), "ci": [round(lo, 6), round(hi, 6)],
                "n": int(n_hi + n_lo)}
    per_g = []
    for g in sorted(set(groups)):
        m = groups == g
        if m.sum() < 20:
            continue
        res = welch_delta_ci(y[m & (x >= q3)], y[m & (x <= q1)])
        if res:
            per_g.append((m.sum(), res))
    if not per_g:
        return {"delta": None, "ci": None, "n": int(len(x))}
    n_tot = sum(n for n, _ in per_g)
    delta = sum(n / n_tot * r[0] for n, r in per_g)
    se = np.sqrt(sum((n / n_tot) ** 2 *
                     ((r[2] - r[1]) / (2 * 1.96)) ** 2 for n, r in per_g)) or 1e-12
    return {"delta": round(float(delta), 6),
            "ci": [round(float(delta - 1.96 * se), 6), round(float(delta + 1.96 * se), 6)],
            "n": int(n_tot)}


# ------------------------------------------------------------------ assembly

def assemble(mode, windows, interactions, confirmations, watchlist, setpoints,
             ctx, df, profile, stability, sha256, version, seed):
    rec = base_skeleton(mode)
    specs = _specs_by_response(ctx)
    for i, w in enumerate(sorted(windows,
                                 key=lambda x: abs((x.get("expected_effect") or {}).get("delta") or 0),
                                 reverse=True), start=1):
        w["id"] = f"OW-{i:03d}"
        w["priority"] = i
        rec["operating_windows"].append(w)

    # conflicts: same factor, disjoint ranges
    by_factor = {}
    for w in rec["operating_windows"]:
        by_factor.setdefault(w["factor"], []).append(w)

    def _abs_delta(w):
        return abs(((w.get("expected_effect") or {}).get("delta")) or 0)

    for f, ws in by_factor.items():
        if len(ws) < 2:
            continue
        # sort by range start keeps the pairwise sweep deterministic; the CHOICE
        # follows the documented rule (method_notes): keep the higher-|delta|
        # window — i.e. the higher-priority one, since priority is |delta| desc.
        ws_sorted = sorted(ws, key=lambda w: w["range"][0])
        for a, b in zip(ws_sorted, ws_sorted[1:]):
            if b["range"][0] > a["range"][1]:
                chosen_w = a if _abs_delta(a) >= _abs_delta(b) else b
                loser = b if chosen_w is a else a
                rec["conflicts"].append({
                    "factor": f, "between": [a["id"], b["id"]],
                    "resolution": "区间不相交：保留优先级高（|效应|大）者，另一窗口降入 watchlist",
                    "chosen": chosen_w["id"]})
                # NOTE: the loser goes through `watchlist` (the caller list) —
                # `assemble` assigns rec["watchlist"] = watchlist below, which
                # would clobber anything appended directly onto rec["watchlist"].
                watchlist.append({
                    "code": "WINDOW_CONFLICT_LOSER",
                    "message": f"窗口 {loser['id']} 与 {chosen_w['id']} 在因子 {f} 上冲突，未采纳",
                    "factor": f, "response": loser["response"], "threshold": None})
                loser["notes"] = (loser["notes"] or "") + " [冲突未采纳，仅供参照]"

    # baseline (current working point): the recipe in force when the trial
    # started (`current_setpoint`) wins; factor medians are only the fallback
    # for factors the platform did not pin (a designed run's median is its
    # centre, which is NOT the pre-trial working point).
    factor_cols = [w["factor"] for w in rec["operating_windows"]]
    pinned = ctx.get("current_setpoint") if isinstance(ctx.get("current_setpoint"), dict) else {}
    point, baseline_sources = {}, {}
    for f in dict.fromkeys(factor_cols):
        v = _num_or_none(pinned.get(f))
        if v is not None:
            point[f] = round(v, 6)
            baseline_sources[f] = "current_setpoint"
            continue
        if f in df.columns:
            v = pd.to_numeric(df[f], errors="coerce").dropna()
            if len(v):
                point[f] = round(float(v.median()), 6)
                baseline_sources[f] = "factor_median"
    rec["current_baseline"]["point"] = point
    rec["current_baseline"]["source"] = baseline_sources
    dist = {}
    for w in rec["operating_windows"]:
        v = point.get(w["factor"])
        if v is None:
            continue
        lo, hi = w["range"]
        dist[w["id"]] = round(max(lo - v, v - hi, 0.0), 6)
    rec["current_baseline"]["distance_to_window"] = dist
    if rec["operating_windows"] and point:
        first = rec["operating_windows"][0]
        rec["current_baseline"]["move_instruction"] = (
            f"优先处理 {first['id']}：将 {first['factor']} 调整至 "
            f"[{first['range'][0]}, {first['range'][1]}]"
            + ("（当前已在窗内）" if dist.get(first["id"], 1) == 0 else ""))

    rec["response_specs"] = {
        r: {"lsl": s.get("lsl"), "usl": s.get("usl"), "target": s.get("target"),
            "goal": s.get("goal"),
            "current": (round(float(pd.to_numeric(df[r], errors="coerce").dropna().mean()), 6)
                        if r in df.columns else None)}
        for r, s in specs.items()}

    for i, c in enumerate(confirmations, start=1):
        c["id"] = c.get("id") or f"CF-{i:03d}"
    rec["confirmations"] = confirmations
    rec["watchlist"] = watchlist
    rec["setpoints"] = setpoints
    rec["interactions"] = interactions

    factor_ranges = {}
    for f in dict.fromkeys(factor_cols):
        if f in df.columns:
            v = pd.to_numeric(df[f], errors="coerce").dropna()
            if len(v):
                factor_ranges[f] = {"min": round(float(v.min()), 6),
                                    "max": round(float(v.max()), 6)}
    time_span = None
    tcol = ctx.get("time_col")
    if tcol and tcol in df.columns:
        time_span = f"{df[tcol].iloc[0]} .. {df[tcol].iloc[-1]}"
    rec["applicability_domain"] = {
        "n_rows": int(len(df)), "time_span": time_span,
        "regime": "steady-state segments" if mode == "observational" else "designed region",
        "factor_observed_ranges": factor_ranges}
    rec["invalidation_conditions"] = [
        "任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%",
        "stability_report 变点检测触发新 regime（漂移/换产）",
        "确认试验结果与 expected_effect 的 CI95 不相交",
    ]
    rec["usage_rules"] = ([
        "observational 窗口在闭环执行前必须先跑 confirmations",
        "confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制",
    ] if mode == "observational" else [
        "窗口外推端点（extrapolation=true）需工艺确认后方可执行",
        "多响应窗口冲突以 conflicts[].chosen 为准",
    ])
    # NOTE (P2-4 fix): the pre-v1.1 version read the leaked loop variable `f`
    # here, which raised UnboundLocalError for a constraint list whose entries
    # carry no `factor` key (linear constraints) or when no window conflict was
    # iterated. No legacy fixture declares constraints (`constraints: []`
    # everywhere in tests/run_tests.py), so this only affects previously
    # crashing inputs; the emitted shape is unchanged for the legacy path.
    rec["constraints"] = [
        {"factor": c.get("factor"), "min": c.get("min"), "max": c.get("max"),
         "source": "user context"}
        for c in ctx.get("constraints", [])]
    rec["provenance"] = {"input_sha256": sha256, "script_version": version,
                         "seed": seed, "authored_by": "script"}
    return rec


# ==================================================================== v1.1 (P2)
# Additive contract v1.1 layer (contract docs/plans/contracts/README.md §5/§6/§9).
# The legacy entry points above are untouched; everything below is only reachable
# through designed_windows_v11 / observational_windows_v11 / windows_seed_export.

TOP_K = 8                 # max active factors carried into window computation
GRID_MIN_N = 3            # frozen grid_plan design (P2-7)
GRID_MAX_N = 9
MAX_GRID_POINTS = 200000
MAX_GRID_FACTORS = 8
HARD_ATOL = 1e-9          # DS-05: hard-constraint violation tolerance

# Frozen enums (contract §5.2 / §5.4) — used for self-checks and ordering.
NO_WINDOW_REASONS = (
    "NO_SIGNIFICANT_FACTOR", "GRID_EMPTY", "NO_FEASIBLE_POINT", "DISCONNECTED_WINDOW",
    "DIRECTION_ONLY", "CONSTRAINTS_INFEASIBLE", "UNIT_MISSING", "UNIT_CONFLICT",
    "EXTRAPOLATION_ONLY", "HULL_UNSUPPORTED", "NOT_ESTIMABLE", "TREND_CONFOUNDED_NO_WINDOW",
    "DESIGN_NOT_INFORMATIVE", "RESPONSE_ALL_MISSING")
ACTIONABLE_BLOCKERS = (
    "unit_missing", "unit_conflict", "constraint_infeasible", "extrapolation",
    "design_hull_low_confidence", "trend_confounded",
    "non_randomized_confirmation_pending", "no_prediction_interval")
MC_COVERAGE_PATH = (Path(__file__).resolve().parents[2] / "tests" / "results"
                    / "mc_pi_coverage.json")


def _grid_n_for(k):
    """Adaptive grid resolution: max n in [GRID_MIN_N, GRID_MAX_N] with n^k <= budget."""
    if k <= 0:
        return GRID_MAX_N
    for n in range(GRID_MAX_N, GRID_MIN_N - 1, -1):
        if n ** k <= MAX_GRID_POINTS:
            return n
    return GRID_MIN_N


def _watch(watchlist, entry):
    """Append a watchlist entry unless an identical (code, factor, response) exists."""
    key = (entry.get("code"), entry.get("factor"), entry.get("response"))
    for existing in watchlist:
        if (existing.get("code"), existing.get("factor"),
                existing.get("response")) == key:
            return existing
    watchlist.append(entry)
    return entry


# ------------------------------------------------------------------ constraints (P2-4)

def normalize_constraints(ctx, brief=None):
    """Normalise declared constraints into evaluable records (P2-4/DS-05).

    Accepted input forms (`col` is accepted as an alias of `factor`):
      {"factor": f, "type": "box"|"safety", "min": n, "max": n, "hard": bool, "source": s}
      {"type": "linear", "coeffs"|"coefficients": {f: c, ...}, "min": n, "max": n, ...}
      {"factor": f, "min": n, "max": n}          # type defaults to "box"

    `hard` defaults to True: a declared limit binds unless explicitly marked soft
    (DS-05 requires 0 hard violations for anything emitted as feasible). Soft
    constraints never filter candidates — they multiply the desirability by
    `1 / (1 + violation/span)`, a strictly decaying penalty (1.0 when satisfied)
    that degrades but never eliminates a candidate, so `joint_setpoints` can
    still disagree with a soft limit and MUST disclose it
    (watchlist code SOFT_CONSTRAINT_RELAXED).
    Returns records sorted deterministically by (type, factor, min, max).
    """
    raw = []
    for source in (ctx.get("constraints") or []):
        if isinstance(source, dict):
            raw.append(("analysis_context.constraints", source))
    for source in ((brief or {}).get("constraints") or []):
        if isinstance(source, dict):
            raw.append(("ontology_brief.constraints", source))
    out = []
    for origin, c in raw:
        ctype = str(c.get("type") or "box").strip().lower()
        hard = bool(c.get("hard", True))
        if ctype == "linear":
            coeffs = c.get("coeffs") or c.get("coefficients") or {}
            coeffs = {str(k): float(v) for k, v in coeffs.items() if v is not None}
            if not coeffs:
                continue
            factor = "linear:" + "+".join(sorted(coeffs))
            # Contract §4.2 spells a one-sided linear limit as {coefficients, rhs};
            # the evaluator works on [min, max] of the weighted sum. Translate rhs
            # (default orientation "sum <= rhs") instead of silently dropping it.
            lo = _num_or_none(c.get("min"))
            hi = _num_or_none(c.get("max"))
            rhs = _num_or_none(c.get("rhs"))
            if rhs is not None:
                op = str(c.get("op") or c.get("relation") or "<=").strip()
                if op in (">=", ">", "min"):
                    lo = rhs if lo is None else lo
                else:
                    hi = rhs if hi is None else hi
            out.append({"factor": factor, "factors": sorted(coeffs), "type": "linear",
                        "min": lo, "max": hi,
                        "hard": hard, "coeffs": coeffs,
                        "source": str(c.get("source") or origin),
                        "reason": c.get("reason")})
            continue
        factor = c.get("factor") or c.get("col")
        if not factor:
            continue
        out.append({"factor": str(factor), "factors": [str(factor)], "type": ctype,
                    "min": _num_or_none(c.get("min")), "max": _num_or_none(c.get("max")),
                    "hard": hard, "coeffs": None,
                    "source": str(c.get("source") or origin),
                    "reason": c.get("reason")})
    out.sort(key=lambda r: (r["type"], r["factor"],
                            -np.inf if r["min"] is None else r["min"],
                            np.inf if r["max"] is None else r["max"]))
    return out


def _num_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def _constraint_slack(rec, raw):
    """Signed slack of one constraint at a raw point (negative => violated).

    box/safety: min(value - min, max - value); linear: min(S - min, max - S)
    with S = sum(coeff_i * raw_i). None when the point cannot be evaluated
    (missing/non-numeric factor) — unevaluable constraints never count as
    violations (they are disclosed through `constraints_applied`).
    """
    if rec["type"] == "linear":
        total = 0.0
        for f, coef in rec["coeffs"].items():
            v = raw.get(f)
            if v is None or isinstance(v, str):
                return None
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return None
            if not np.isfinite(fv):
                return None
            total += coef * fv
        bounds = []
        if rec["min"] is not None:
            bounds.append(total - rec["min"])
        if rec["max"] is not None:
            bounds.append(rec["max"] - total)
        return min(bounds) if bounds else None
    v = raw.get(rec["factor"])
    if v is None or isinstance(v, str):
        return None
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(fv):
        return None
    bounds = []
    if rec["min"] is not None:
        bounds.append(fv - rec["min"])
    if rec["max"] is not None:
        bounds.append(rec["max"] - fv)
    return min(bounds) if bounds else None


def constraint_report(recs, raw):
    """Evaluate every constraint at one raw point.

    Returns (n_hard_violations, slack_by_factor, hard_violated, soft_violated,
    soft_penalty). `slack_by_factor` keeps the WORST (minimum) slack per factor
    over the HARD constraints only — it is the executable safety margin reported
    as `constraint_slack` and is therefore never negative on an actionable point.
    Soft relaxations are reported separately (soft_violated / soft_penalty) and
    disclosed through the watchlist, not through the slack map.
    """
    n_hard, slack_by_factor = 0, {}
    hard_violated, soft_violated = [], []
    penalty = 1.0
    for rec in recs:
        slack = _constraint_slack(rec, raw)
        if slack is None:
            continue
        if rec["hard"]:
            for f in rec["factors"]:
                prev = slack_by_factor.get(f)
                slack_by_factor[f] = slack if prev is None else min(prev, slack)
        violated = slack < -HARD_ATOL
        if violated:
            if rec["hard"]:
                n_hard += 1
                hard_violated.append(rec)
            else:
                soft_violated.append(rec)
                span = None
                if rec["min"] is not None and rec["max"] is not None:
                    span = abs(rec["max"] - rec["min"])
                span = span or 1.0
                # strictly decaying multiplicative penalty: 1 when satisfied,
                # 0.5 at one full span of violation, never 0 (a soft limit can
                # still be relaxed — and then gets disclosed)
                penalty *= float(1.0 / (1.0 + (-slack) / span))
    return n_hard, slack_by_factor, hard_violated, soft_violated, penalty


def constraints_applied_for(recs, factor):
    """The constraints that actually participated for one factor (contract §5.2)."""
    out = []
    for rec in recs:
        if factor not in rec["factors"]:
            continue
        out.append({"factor": rec["factor"], "type": rec["type"],
                    "min": rec["min"], "max": rec["max"],
                    "hard": rec["hard"], "source": rec["source"]})
    return out


def coded_bounds_from_constraints(recs, infos, active):
    """Coded per-factor bounds from HARD box/safety constraints (P2-4).

    {factor: (lo_coded, hi_coded)} clipped to the coded box [-1, 1]; the raw
    limits map to coded as (raw - mean) / half_range. Soft constraints are NOT
    bounds (they are desirability penalties).
    """
    bounds = {}
    for f in active:
        info = infos.get(f)
        if not info or not info.get("half_range"):
            continue
        lo, hi = -1.0, 1.0
        for rec in recs:
            if not rec["hard"] or rec["type"] == "linear" or rec["factor"] != f:
                continue
            if rec["min"] is not None:
                lo = max(lo, (rec["min"] - info["mean"]) / info["half_range"])
            if rec["max"] is not None:
                hi = min(hi, (rec["max"] - info["mean"]) / info["half_range"])
        bounds[f] = (float(lo), float(hi))
    return bounds


def coded_linear_records(recs, infos, active):
    """Hard linear constraints converted to coded coordinates for rsm.refine_optimum.

    x_raw = mean + coded * half_range, so S_raw = const + sum(c_i * hr_i * coded_i).
    Returns records {"coeffs": {factor: c_i*hr_i}, "min": min - const, "max": max - const}.
    """
    out = []
    for rec in recs:
        if rec["type"] != "linear" or not rec["hard"]:
            continue
        if any(f not in infos for f in rec["coeffs"]):
            continue
        coeffs, const = {}, 0.0
        for f, coef in rec["coeffs"].items():
            hr = infos[f].get("half_range")
            if not hr:
                continue
            coeffs[f] = coef * hr
            const += coef * infos[f]["mean"]
        if not coeffs:
            continue
        out.append({"coeffs": coeffs,
                    "min": None if rec["min"] is None else rec["min"] - const,
                    "max": None if rec["max"] is None else rec["max"] - const})
    return out


# ------------------------------------------------------------------ design region (P2-3)

def build_design_region(profile, ctx, df, models, factor_info, evaluated_points=0):
    """`recommendations.design_region` (+ `model.design_hull`/`leverage` content).

    Leverage h_i = x_i'(X'X)^-1 x_i over the fitted design rows with the classic
    2p/n screening threshold; max/mean/n_exceed are reported for every response
    model (identical across responses: the design matrix is response-independent)
    and the worst case is kept.
    """
    design = profile.get("design") or {}
    mode = design.get("mode")
    numeric_cols = [i["col"] for i in factor_info
                    if i["type"] == "numeric" and not i["zero_variance"]
                    and not i.get("is_block") and not i.get("is_covariate")]
    declared = (ctx.get("design_region") or {})
    desc = dd_mod.detect_design_hull(df, numeric_cols, design, mode or "designed")
    if declared.get("design_hull") and declared.get("design_hull") != desc["hull"]:
        desc["note"] = ((desc.get("note") or "") +
                        f" | declared design_hull={declared['design_hull']!r} vs "
                        f"data-derived {desc['hull']!r} — data-derived hull wins")
    lev = {"max_leverage": None, "mean_leverage": None, "leverage_threshold": None,
           "n_exceed": None, "n_rows": 0}
    for resp, model in (models or {}).items():
        cur = dd_mod.leverage_stats(model, df)
        if cur.get("max_leverage") is None:
            continue
        if lev["max_leverage"] is None or cur["max_leverage"] > lev["max_leverage"]:
            lev = cur
    n_rows = lev.get("n_rows") or 0
    n_exceed = lev.get("n_exceed")
    if desc["hull"] == "unbounded":
        risk = "high"
    elif n_exceed is None:
        risk = "medium"
    elif n_rows and n_exceed / n_rows > 0.25:
        risk = "high"
    elif n_exceed > 0:
        risk = "medium"
    else:
        risk = "low"
    if desc.get("hull") == "convex_hull" and desc.get("hull_exact") is False \
            and risk == "low":
        # the exact hull was not affordable: the coded box stands in for it, so a
        # "low" extrapolation risk would overstate what was actually verified
        risk = "medium"
    ax = desc.get("axial_alpha")
    if ax is None and declared.get("axial_alpha") is not None:
        ax = declared["axial_alpha"]
    block = {
        "type": design.get("design_type"),
        "hull": desc["hull"],
        "coded_bounds": desc.get("coded_bounds") or {},
        "axial_alpha": ax,
        "max_leverage": _r6(lev.get("max_leverage")),
        "mean_leverage": _r6(lev.get("mean_leverage")),
        "leverage_threshold": _r6(lev.get("leverage_threshold")),
        "n_exceed": lev.get("n_exceed"),
        "extrapolation_risk": risk,
        "evaluated_points": int(evaluated_points),
        "design_hull_confidence": desc.get("design_hull_confidence", "low"),
        "factor_order": list(desc.get("factor_order") or []),
        "n_design_rows": int(n_rows),
        "note": desc.get("note"),
    }
    return block, desc


def _r6(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 6) if np.isfinite(f) else None


def _hull_coords(coded_active, active, desc, infos, anchor_raw):
    """Hull coordinates for grid points: (m, len(factor_order)).

    Active factors take their grid coordinate; every other hull factor sits at
    the anchor's coded value (the grid walks only the active axes).
    """
    order = list(desc.get("factor_order") or [])
    if not order:
        return np.zeros((len(coded_active), 0))
    m = len(coded_active)
    out = np.zeros((m, len(order)))
    a_idx = {f: i for i, f in enumerate(active)}
    for j, f in enumerate(order):
        info = infos.get(f)
        if f in a_idx:
            out[:, j] = coded_active[:, a_idx[f]]
        elif info and info.get("half_range"):
            v = anchor_raw.get(f)
            out[:, j] = 0.0 if v is None else (float(v) - info["mean"]) / info["half_range"]
    return out


def point_in_hull(raw, desc, infos):
    """Scalar hull test for one raw point (used for window centres / setpoints)."""
    order = list(desc.get("factor_order") or [])
    if not order:
        return True
    vec = []
    for f in order:
        info = infos.get(f)
        v = raw.get(f)
        if info is None or not info.get("half_range") or v is None:
            return desc.get("hull") == "unbounded"
        vec.append((float(v) - info["mean"]) / info["half_range"])
    return bool(dd_mod.hull_mask(desc, np.asarray([vec], dtype=float))[0])


# ------------------------------------------------------------------ intervals (P2-1)

def interval_bundle(model, raw_point):
    """The four separated interval types at one raw point (contract §5.2).

    mean (ŷ) with
      mean_ci95 = ŷ ± t_{0.975,df} * sqrt(x0'(X'X)^-1 x0 * MSE)
      pi95      = ŷ ± t_{0.975,df} * sqrt((1 + x0'(X'X)^-1 x0) * MSE)   <- the "1 +"
      ti95_95   = ŷ ± k * sqrt(MSE),  k = normal_tolerance_factor (ISO 16269-6)
    Everything is None when the model cannot support it (no xtx_inv / MSE / df).
    """
    out = {"mean": None, "mean_ci95": None, "pi95": None, "ti95_95": None,
           "se_mean": None, "s": None, "k": None, "pi95_halfwidth": None,
           "mean_ci95_halfwidth": None}
    if model is None:
        return out
    yhat, se = ea_mod.predict_many(model, [raw_point])
    y = float(yhat[0])
    s = float(se[0])
    if not np.isfinite(y):
        return out
    out["mean"] = round(y, 6)
    df = model.get("df_resid")
    mse = model.get("mse")
    n = model.get("n")
    if np.isfinite(s) and df and df > 0:
        t = float(sps.t.ppf(0.975, df))
        hw = t * s
        out["se_mean"] = round(s, 6)
        out["mean_ci95"] = [round(y - hw, 6), round(y + hw, 6)]
        out["mean_ci95_halfwidth"] = round(hw, 6)
        if mse is not None and mse >= 0:
            pi_hw = t * math.sqrt(s * s + float(mse))
            out["pi95"] = [round(y - pi_hw, 6), round(y + pi_hw, 6)]
            out["pi95_halfwidth"] = round(pi_hw, 6)
    if mse not in (None, 0) and df and df > 0 and n:
        k = normal_tolerance_factor(n, df)
        if k:
            s_res = math.sqrt(float(mse))
            out["k"] = round(k, 6)
            out["s"] = round(s_res, 6)
            out["ti95_95"] = [round(y - k * s_res, 6), round(y + k * s_res, 6)]
    return out


def _mc_coverage_check():
    """Measured PI coverage from tests/results/mc_pi_coverage.json when present."""
    try:
        if not MC_COVERAGE_PATH.exists():
            return None
        data = json.loads(MC_COVERAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    n = data.get("n_replications") or data.get("n")
    cov = data.get("pi_point_coverage")
    if n is None or cov is None:
        return None
    return {"n": int(n), "pi_point_coverage": float(cov)}


# ------------------------------------------------------------------ v1.1 helpers

def _active_scan(effect_table, core):
    """Significant-factor scan — identical rule to the legacy designed path."""
    active, strength, pairs = [], {}, []
    for fam in effect_table.get("families", []):
        for t in fam.get("tests", []):
            if not t.get("estimable"):
                continue
            q = t.get("q_value_bh")
            eta = t.get("partial_eta_squared") or 0
            if q is None or q >= 0.05 or eta < EFFECT_GATE_ETA2 or t["order"] > 2:
                continue
            pairs.append((fam["response"], t))
            for f in t["term"].split(":"):
                if f in core and f not in active:
                    active.append(f)
                strength[(fam["response"], f)] = max(
                    strength.get((fam["response"], f), 0), abs(eta))
    return active, strength, pairs


def _unit_entry(units, kind, col):
    return ((units.get(kind) or {}).get(col)
            or {"canonical": None, "display": None, "unit_status": "missing",
                "source": None})


def _v11_window_stub(f, infos, strength, effect_table, models, resolution, ctx):
    """Window shell with the legacy 15 keys (used for factors beyond the legacy
    active cap of 4 — the v1.1 grid covers up to TOP_K = 8)."""
    resp_best = max(((resp, strength.get((resp, f), 0)) for resp in _resp_names(models)),
                    key=lambda x: x[1], default=(None, 0))[0]
    main_test = _main_test(effect_table, resp_best, f)
    coef = (main_test or {}).get("coefficient")
    q = (main_test or {}).get("q_value_bh")
    eta = (main_test or {}).get("partial_eta_squared")
    hr = infos[f].get("half_range")
    delta = round(coef / hr, 6) if (coef is not None and hr) else None
    return {
        "id": None, "priority": None, "factor": f,
        "factor_unit": infos[f].get("unit"), "response": resp_best,
        "range": [None, None], "shape": "connected",
        "expected_effect": {
            "delta": delta,
            "direction_semantics": (f"因子 {f} 每增加 1 个原始单位，响应 {resp_best} 变化约 "
                                    f"{delta}（编码主效应 {coef}/半极差 {round(hr, 6) if hr else None}）"),
            "ci95": None,
            "unit": _unit_of(ctx, resp_best) if resp_best else None,
        },
        "confidence": _c7_confidence(q, eta is not None and eta >= EFFECT_GATE_ETA2,
                                     True, resolution),
        "fdr_q": q, "sample_size": (main_test or {}).get("n"),
        "evidence_refs": [f"effect_table.json#{resp_best}.{f}.main"] if resp_best else [],
        "extrapolation": False, "confirmation_needed": False, "notes": None,
    }


def _raws_from_grid(coded, active, infos, anchor_raw):
    out = []
    for row in coded:
        raw = dict(anchor_raw)
        for f, v in zip(active, row):
            info = infos[f]
            raw[f] = info["mean"] + float(v) * info["half_range"]
        out.append(raw)
    return out


def _response_satisfied(resp, y, se_mean, spec, t95, d):
    """Is one response's requirement met at a point? (documented rule)

    - declared lsl/usl: the MEAN-CI bound (y +- t_{0.95,df} * se) must stay inside
      the limits — the same confidence convention the legacy grid feasibility uses;
    - goal/target-only responses (no limits): satisfied when the individual
      desirability d >= 0.5, i.e. the point sits in the better half of the
      ACHIEVABLE range (normalised by grid_lo_hi) or within half the target span.
      This is point-independent (no dependence on the anchor prediction).
    """
    if y is None or not np.isfinite(y):
        return False
    bound = t95 * se_mean if (np.isfinite(se_mean) and t95) else 0.0
    lsl, usl = spec.get("lsl"), spec.get("usl")
    if lsl is not None and (y - bound) < lsl:
        return False
    if usl is not None and (y + bound) > usl:
        return False
    if lsl is None and usl is None:
        return d is not None and d >= 0.5
    return True


def _joint_confidence(responses, models):
    """Weakest link across the joint responses (documented rule).

    "medium" when every response has a usable interval-bearing fit (df_resid >= 3,
    non-zero MSE, invertible X'X); otherwise "low". A joint recommendation is
    never labelled "high": closed-loop execution always needs a confirmation run
    (contract §10 requires confidence >= medium for optimizer-loop seeds).
    """
    for resp in responses:
        m = models.get(resp) or {}
        df = m.get("df_resid")
        if not df or df < 3 or m.get("mse") in (None, 0) or m.get("xtx_inv") is None:
            return "low"
    return "medium"


def _window_ids_covering(operating_windows, point):
    out = []
    for w in operating_windows:
        f = w["factor"]
        v = point.get(f)
        if v is None:
            continue
        rng = w.get("range") or [None, None]
        if rng[0] is None or rng[1] is None:
            continue
        if rng[0] - 1e-9 <= float(v) <= rng[1] + 1e-9:
            out.append(w["id"])
    return out


# ------------------------------------------------------------------ designed v1.1

def _window_v11_fields(w, infos, units, cons, models, desc, design_region,
                       confirmed, effect_table, center_raw):
    """Attach every v1.1 window field (contract §5.2) and derive `actionable`.

    `center_raw` is the window's representative raw point (the best legal
    candidate with THIS factor at its window centre) — all intervals and the
    constraint check are evaluated there.
    """
    f = w["factor"]
    resp = w.get("response")
    unit_f = _unit_entry(units, "factors", f)
    unit_r = _unit_entry(units, "responses", resp) if resp else {"canonical": None, "unit_status": "missing"}
    info = infos.get(f) or {}

    model = models.get(resp) if resp else None
    bundle = interval_bundle(model, center_raw) if (model and center_raw) else {
        "mean": None, "mean_ci95": None, "pi95": None, "ti95_95": None}
    in_hull = point_in_hull(center_raw, desc, infos) if center_raw else False
    n_hard = 0
    if center_raw:
        n_hard = constraint_report(cons, center_raw)[0]

    ee = w.setdefault("expected_effect", {})
    main_test = _main_test(effect_table, resp, f) or _main_test(effect_table, None, f)
    hr = info.get("half_range")
    eff_ci = (main_test or {}).get("effect_ci95")
    ee["mean_ci95"] = bundle.get("mean_ci95")
    ee["pi95"] = bundle.get("pi95")
    ee["pi95_method"] = ea_mod.PI95_METHOD
    ee["effect_ci95"] = ([round(eff_ci[0] / hr, 6), round(eff_ci[1] / hr, 6)]
                         if (eff_ci and hr) else None)
    ee["unit_status"] = unit_r["unit_status"]
    ee["response_unit"] = unit_r["canonical"]
    ee["tolerance_interval_95_95"] = bundle.get("ti95_95")
    # v1.1 never falls back to the fake "response units" placeholder
    ee["unit"] = unit_r["canonical"]

    w["window_role"] = "marginal_diagnostic"
    w["in_design_hull"] = bool(in_hull)
    w["constraints_applied"] = constraints_applied_for(cons, f)
    w["constraint_violations"] = int(n_hard)
    w["predicted_at_center"] = {
        "mean": bundle.get("mean"), "mean_ci95": bundle.get("mean_ci95"),
        "pi95": bundle.get("pi95"), "ti95_95": bundle.get("ti95_95")}

    blockers = []
    if unit_f["unit_status"] == "missing" or unit_r["unit_status"] == "missing":
        blockers.append("unit_missing")
    if unit_f["unit_status"] == "conflict" or unit_r["unit_status"] == "conflict":
        blockers.append("unit_conflict")
    if n_hard > 0:
        blockers.append("constraint_infeasible")
    if not in_hull:
        # only a genuine out-of-hull point blocks; the legacy `extrapolation`
        # boundary flag stays a caution (usage_rules), not a hard blocker
        blockers.append("extrapolation")
    if design_region.get("design_hull_confidence") == "low":
        blockers.append("design_hull_low_confidence")
    if ee.get("pi95") is None:
        blockers.append("no_prediction_interval")
    if w.get("confirmation_needed") and not confirmed:
        blockers.append("non_randomized_confirmation_pending")
    if resp is None:
        blockers.append("unit_missing")
    w["actionable_blockers"] = sorted(set(blockers), key=ACTIONABLE_BLOCKERS.index)
    w["actionable"] = not w["actionable_blockers"]
    return w


def designed_windows_v11(models, effect_table, profile, ctx, df, *, brief=None, seed=None):
    """v1.1 designed-mode entry point (contract §9). Returns the full dict.

    Keys: the contract §9 set (windows, interactions, confirmations, watchlist,
    setpoints, joint_windows, joint_setpoints, factor_response_matrix, grid_plan,
    units, design_region, interval_disclosure, actionable_summary,
    association_screen_ref, next_design_ref) PLUS the complete v1.1
    recommendations.json payload (contract_version "1.1", operating_windows,
    current_baseline, conflicts, response_specs, constraints, applicability_domain,
    invalidation_conditions, usage_rules, provenance) so the caller can write it
    directly. `windows` is the same list object as `operating_windows`.

    Legacy mirror: the marginal windows are seeded from the legacy
    `designed_windows` output (same delta/confidence/evidence fields) and their
    ranges are recomputed with the v1.1 candidate set = legacy candidates
    INTERSECT design hull INTERSECT hard constraints. With no declared
    constraints and a box hull the numbers are identical to the legacy entry
    point (asserted by tests/test_phase2_stats.py).
    """
    resolution = (profile.get("design") or {}).get("resolution")
    factor_info = models[next(iter(models))]["factor_info"] if models else []
    infos = {i["col"]: i for i in factor_info}
    specs = _specs_by_response(ctx)
    model_responses = list(models)
    declared_responses = [r.get("col") for r in (ctx.get("responses") or [])
                          if isinstance(r, dict) and r.get("col")]
    declared_responses = [r for r in declared_responses if r] or list(model_responses)
    declared_factors = [f.get("col") for f in (ctx.get("factors") or [])
                        if isinstance(f, dict) and f.get("col")]
    declared_factors = [f for f in declared_factors if f] or [i["col"] for i in factor_info]
    units = ea_mod.build_units_block(ctx, brief, declared_factors, declared_responses)
    cons = normalize_constraints(ctx, brief)
    confirmed = bool(ctx.get("confirmation_completed") or ctx.get("confirmed"))

    lwindows, interactions, confirmations, watchlist, _legacy_sp = designed_windows(
        models, effect_table, profile, ctx, df)

    core = [c for c, i in infos.items() if not i.get("is_block")
            and not i.get("is_covariate") and not i["zero_variance"]]
    active_found, strength, _sig = _active_scan(effect_table, core)
    top = active_found[:TOP_K]
    deferred = sorted(active_found[TOP_K:])
    if deferred:
        _watch(watchlist, {
            "code": "FACTORS_DEFERRED",
            "message": (f"top_k={TOP_K} 上限：显著因子 {'、'.join(deferred)} 未进入窗口网格"
                        f"（已披露在 grid_plan.deferred_factors，无静默丢弃）"),
            "factor": None, "response": None, "threshold": str(TOP_K)})
    cat_active = [f for f in top if infos[f]["type"] != "numeric"]
    active = [f for f in top if infos[f]["type"] == "numeric"]

    k = len(active)
    grid_n = _grid_n_for(k) if k else GRID_MAX_N
    # P2-7: the decision uses the number of DETECTED significant factors, not the
    # capped working set — 8 active -> bounded grid, >8 (or a 3^k budget blow-up)
    # -> continuous optimization over the first TOP_K factors.
    possible = (len(active_found) <= MAX_GRID_FACTORS
                and (not active_found or GRID_MIN_N ** len(active_found) <= MAX_GRID_POINTS))
    approach = "grid" if possible else "continuous_optimization"
    grid_plan = {"n_active": len(active_found), "top_k": TOP_K, "grid_n": int(grid_n),
                 "n_grid_points": 0, "approach": approach,
                 "max_grid_points": MAX_GRID_POINTS, "deferred_factors": deferred,
                 "truncated": bool(deferred), "n_grid_factors": k}
    diag = {"constraints_infeasible": False, "hull_failed": False,
            "continuous": approach != "grid", "deferred": set(deferred),
            "no_feasible_point": False, "extrapolation_only": False,
            "trend_blocked": set(), "direction_only": set(), "not_estimable": set(),
            "no_significant": set(), "response_all_missing": set()}
    for resp in declared_responses:
        if resp not in df.columns or pd.to_numeric(df[resp], errors="coerce").notna().sum() == 0:
            diag["response_all_missing"].add(resp)
    for f in declared_factors:
        if f not in df.columns or f not in infos or infos[f]["zero_variance"]:
            diag["not_estimable"].add(f)

    design_region, desc = build_design_region(profile, ctx, df, models, factor_info,
                                              evaluated_points=0)

    # ---- anchor (identical convention to the legacy path) ----
    center_raw = {}
    for i in factor_info:
        if i["zero_variance"]:
            continue
        center_raw[i["col"]] = (i["mean"] if i["type"] == "numeric"
                                else i["levels"][len(i["levels"]) // 2])
    anchor_raw = dict(center_raw)
    st_points = {resp: rsm_mod.stationary_point(m) for resp, m in models.items()}
    for resp, st in st_points.items():
        if st and st["inside_design_region"] and st["classification"] == "max":
            anchor_raw.update(st["raw"])
            break

    predict_fns = {resp: m["predict_raw"] for resp, m in models.items()}
    t95_raw = {resp: (m["df_resid"] and sps.t.ppf(0.95, m["df_resid"]))
               for resp, m in models.items()}

    # ---- grid candidate evaluation (P2-7) ----
    grid = None
    if k and approach == "grid":
        axes = [np.linspace(-1.0, 1.0, grid_n) for _ in range(k)]
        coded = np.array(list(itertools.product(*axes)), dtype=float)
        raws = _raws_from_grid(coded, active, infos, anchor_raw)
        Y, SE = {}, {}
        ok = np.ones(len(raws), dtype=bool)
        for resp, model in models.items():
            yhat, se = ea_mod.predict_many(model, raws)
            Y[resp] = yhat
            SE[resp] = se
            ok &= np.isfinite(yhat)
        keep = np.where(ok)[0]
        coded = coded[keep]
        raws = [raws[i] for i in keep]
        for resp in Y:
            Y[resp] = Y[resp][keep]
            SE[resp] = SE[resp][keep]
        m = len(raws)
        grid_plan["n_grid_points"] = int(m)
        grid = {"coded": coded, "raws": raws, "Y": Y, "SE": SE, "n": m}
        if m:
            grid_lo_hi = {resp: (float(np.min(Y[resp])), float(np.max(Y[resp])))
                          for resp in Y}
            grid["grid_lo_hi"] = grid_lo_hi
            feas = np.ones(m, dtype=bool)
            for resp in Y:
                t = t95_raw.get(resp) or 1.64
                se_eff = np.where(np.isfinite(SE[resp]), SE[resp], 0.0)
                spec = specs.get(resp, {})
                if spec.get("lsl") is not None:
                    feas &= ~((Y[resp] - t * se_eff) < spec["lsl"])
                if spec.get("usl") is not None:
                    feas &= ~((Y[resp] + t * se_eff) > spec["usl"])
            D = np.array([rsm_mod.combined_desirability(
                {resp: Y[resp][i] for resp in Y}, specs, grid_lo_hi)[0]
                for i in range(m)])
            coded_hull = _hull_coords(coded, active, desc, infos, anchor_raw)
            hull_ok = dd_mod.hull_mask(desc, coded_hull)
            hard_ok = np.ones(m, dtype=bool)
            soft_pen = np.ones(m)
            for i, raw in enumerate(raws):
                n_hard, _slack, _hv, sv, pen = constraint_report(cons, raw)
                if n_hard:
                    hard_ok[i] = False
                if sv:
                    soft_pen[i] = pen
            Deff = D * soft_pen
            base_ok = hull_ok & hard_ok
            grid.update({"feas": feas, "D": D, "Deff": Deff, "hull_ok": hull_ok,
                         "hard_ok": hard_ok, "base_ok": base_ok})
            if not base_ok.any():
                if not hard_ok.any() and cons:
                    diag["constraints_infeasible"] = True
                    _watch(watchlist, {
                        "code": "CONSTRAINTS_INFEASIBLE",
                        "message": ("全部候选点违反硬约束 — 不产出窗口/推荐点；"
                                    "请在约束放宽或补做试验后重跑"),
                        "factor": None, "response": None, "threshold": None})
                else:
                    diag["hull_failed"] = True
                    _watch(watchlist, {
                        "code": "HULL_UNSUPPORTED",
                        "message": ("全部候选点落在设计域（凸包）之外 — 不产出窗口；"
                                    "未运行角点不予评估"),
                        "factor": None, "response": None, "threshold": None})
            Dmax = float(Deff.max()) if m else 0.0
            if Dmax > 0:
                cand = base_ok & feas & (Deff >= 0.8 * Dmax)
            else:
                cand = base_ok & feas
            if not cand.any():
                cand = base_ok & feas
            if not cand.any():
                if not feas.any():
                    diag["no_feasible_point"] = True
                    _watch(watchlist, {
                        "code": "NO_FEASIBLE_POINT",
                        "message": "无满足规格置信界的网格点 — 窗口降级为方向建议",
                        "factor": None, "response": None, "threshold": None})
                cand = base_ok
            grid.update({"cand": cand, "Dmax": Dmax})

    design_region["evaluated_points"] = int(
        grid["n"] if grid else len(active) * (2 * len(active) + 1))

    # ---- marginal windows (P2-2): legacy seeds, v1.1 candidate set ----
    legacy_by_factor = {w["factor"]: w for w in lwindows}
    windows = []
    if grid is not None and grid["n"]:
        cand_idx = np.where(grid["cand"])[0]
        best_cand = (int(cand_idx[int(np.argmax(grid["Deff"][cand_idx]))])
                     if cand_idx.size else None)
        for f in active:
            w = copy.deepcopy(legacy_by_factor.get(f))
            if w is None:
                w = _v11_window_stub(f, infos, strength, effect_table, models, resolution, ctx)
            idx = active.index(f)
            vals = grid["coded"][grid["cand"], idx]
            if vals.size == 0:
                continue
            lo_c, hi_c = float(vals.min()), float(vals.max())
            info = infos[f]
            lo_raw = info["mean"] + lo_c * info["half_range"]
            hi_raw = info["mean"] + hi_c * info["half_range"]
            w["range"] = [round(lo_raw, 6), round(hi_raw, 6)]
            w["shape"] = _connected_shape(vals, grid_n)
            w["extrapolation"] = bool(lo_c <= -1.0 + 1e-9 or hi_c >= 1.0 - 1e-9)
            if w["shape"] == "disconnected":
                _watch(watchlist, {
                    "code": "DISCONNECTED_WINDOW",
                    "message": f"因子 {f} 的可行集不连通 — 仅报告含最优点的连通块",
                    "factor": f, "response": w.get("response"), "threshold": None})
            # representative point: best legal candidate, this factor at the
            # window centre; falls back to the candidate itself when the override
            # would leave the hull / violate a hard (e.g. cross-factor) constraint
            if best_cand is not None:
                rep = dict(grid["raws"][best_cand])
            else:
                rep = dict(anchor_raw)
            rep[f] = (lo_raw + hi_raw) / 2.0
            if best_cand is not None and (
                    constraint_report(cons, rep)[0]
                    or not point_in_hull(rep, desc, infos)):
                rep = dict(grid["raws"][best_cand])
            _window_v11_fields(w, infos, units, cons, models, desc, design_region,
                               confirmed, effect_table, rep)
            windows.append(w)
    elif grid is None and active and approach != "grid":
        _watch(watchlist, {
            "code": "GRID_SKIPPED",
            "message": (f"{len(active)} 个活跃数值因子超过网格预算 — 采用连续寻优"
                        f"（multi-start SLSQP/L-BFGS-B，约束已施加），不产出网格边际窗口"),
            "factor": None, "response": None, "threshold": str(MAX_GRID_FACTORS)})

    # direction-only disclosure for the pairs that stayed without a window
    for fam in effect_table.get("families", []):
        for t in fam.get("tests", []):
            if t.get("order", 1) > 1:
                continue
            f = str(t.get("term"))
            resp = fam.get("response")
            if f not in declared_factors:
                continue
            q = t.get("q_value_bh")
            eta = t.get("partial_eta_squared")
            significant = bool(t.get("estimable")) and q is not None and q < 0.05 \
                and (eta is None or eta >= EFFECT_GATE_ETA2)
            if significant and f in active and approach == "grid":
                continue  # a window (or its absence-of-candidates) is computed
            if significant:
                diag["direction_only"].add((f, resp))
            else:
                diag["no_significant"].add((f, resp))

    # ---- assemble the v1.1 recommendations payload ----
    cat_setpoints = [s for s in _legacy_sp if s.get("factor") != "MULTI"]
    sha = ctx.get("input_sha256") or ctx.get("_input_sha256")
    version = ctx.get("script_version") or ctx.get("_script_version") or "1.1"
    seed_v = seed if seed is not None else ctx.get("seed")
    rec = assemble("designed", windows, interactions, confirmations, watchlist,
                   cat_setpoints, ctx, df, profile, None, sha, version, seed_v)
    rec["contract_version"] = "1.1"

    # ---- joint domain / setpoints (P2-2, DS-04/DS-08) ----
    joint_windows, joint_setpoints = _build_joint_designed(
        rec, df, models, specs, units, cons, desc, design_region, infos, active,
        model_responses, grid, approach, watchlist, diag, anchor_raw, t95_raw,
        factor_info, predict_fns, st_points)
    rec["joint_windows"] = joint_windows
    rec["joint_setpoints"] = joint_setpoints

    # `setpoints` stays populated as a legacy mirror of the same content
    rec["setpoints"] = cat_setpoints + _joint_setpoint_mirror(joint_setpoints)

    # ---- units / design region / matrix / disclosure (P2-5/P2-6/P2-3) ----
    for f in declared_factors:
        st = _unit_entry(units, "factors", f)["unit_status"]
        if st == "missing":
            _watch(watchlist, {"code": "UNIT_MISSING",
                               "message": f"因子 {f} 未声明单位 — 相关窗口/推荐点 actionable=false"
                                          f"（不删除窗口，仅阻断执行）",
                               "factor": f, "response": None, "threshold": None})
        elif st == "conflict":
            _watch(watchlist, {"code": "UNIT_CONFLICT",
                               "message": f"因子 {f} 的单位声明冲突 — 相关窗口/推荐点 actionable=false",
                               "factor": f, "response": None, "threshold": None})
    for c in units.get("conflicts", []):
        # Two conflict shapes reach here: resolve_units' own entries carry
        # `message`; the context adapter's platform-side mismatches carry
        # {factor_or_response, from, to, reason}. Accept both.
        _watch(watchlist, {"code": "UNIT_CONFLICT",
                           "message": (c.get("message") or c.get("reason")
                                       or "单位声明冲突"),
                           "factor": c.get("factor_or_response"), "response": None,
                           "threshold": None})
    rec["units"] = units
    rec["design_region"] = design_region
    rec["grid_plan"] = grid_plan
    rec["constraints"] = [
        {"factor": r["factor"], "type": r["type"], "min": r["min"], "max": r["max"],
         "hard": r["hard"], "source": r["source"]} for r in cons]
    rec["factor_response_matrix"] = build_factor_response_matrix(
        declared_factors, declared_responses, rec["operating_windows"], df, infos,
        effect_table, diag, specs)
    rec["actionable_summary"] = _actionable_summary(rec)
    rec["interval_disclosure"] = _interval_disclosure(
        designed=True, joint_setpoints=joint_setpoints, model_responses=model_responses,
        selection_scale=_selection_scale(rec))
    rec["association_screen_ref"] = _artifact_ref(
        "02_analysis/association_screen.json", ctx, "n_pairs",
        {"causal_claim": "none"})
    rec["next_design_ref"] = _artifact_ref(
        "conclusions/next_design.json", ctx, None,
        {"recommended_action": None, "primary_action_id": None})
    rec["windows"] = rec["operating_windows"]
    return rec


# ------------------------------------------------------------------ joint domain (P2-2)

def _point_eval(raw, models, specs, grid_lo_hi, cons, desc, infos, t95_by):
    """Score one raw point: predicted means, desirability, satisfactions, legality."""
    out = {"y": {}, "se": {}, "d": {}, "D": 0.0, "penalty": 1.0, "Deff": 0.0,
           "satisfied": [], "hard": 0, "slack": {}, "in_hull": True,
           "soft_violated": []}
    if raw is None:
        return out
    y_by = {}
    for resp, model in models.items():
        yhat, se = ea_mod.predict_many(model, [raw])
        y = float(yhat[0]) if np.isfinite(yhat[0]) else None
        s = float(se[0]) if np.isfinite(se[0]) else float("nan")
        out["y"][resp] = None if y is None else round(y, 6)
        out["se"][resp] = None if not np.isfinite(s) else round(s, 6)
        spec = specs.get(resp, {})
        lo_hi = (grid_lo_hi or {}).get(resp, (None, None))
        d = None
        if y is not None:
            y_by[resp] = y
            try:
                d = round(float(rsm_mod.d_individual(y, spec, lo_hi[0], lo_hi[1])), 6)
            except Exception:
                d = None
        out["d"][resp] = d
        if _response_satisfied(resp, y, s, spec, t95_by.get(resp), d):
            out["satisfied"].append(resp)
    if y_by:
        out["D"] = float(rsm_mod.combined_desirability(y_by, specs, grid_lo_hi)[0])
    n_hard, slack, _hv, soft_v, penalty = constraint_report(cons, raw)
    out["hard"] = n_hard
    out["slack"] = {k: round(v, 6) for k, v in sorted(slack.items())}
    out["penalty"] = penalty
    out["Deff"] = out["D"] * penalty
    out["soft_violated"] = [r["factor"] for r in soft_v]
    out["in_hull"] = point_in_hull(raw, desc, infos)
    return out


def _coded_vector(active, infos, point):
    vec = []
    for f in active:
        info = infos[f]
        v = (point or {}).get(f)
        if v is None or not info.get("half_range"):
            vec.append(0.0)
        else:
            vec.append((float(v) - info["mean"]) / info["half_range"])
    return np.array(vec)


def _design_starts(active, infos, df, desc, anchor_raw, st_points, cap=12):
    """Deterministic multi-start points (coded) for continuous optimization (P2-7)."""
    starts = []
    cols = [f for f in active if f in df.columns]
    if cols:
        sub = df[cols].dropna().drop_duplicates()
        rows = sub.to_dict("records")
        step = max(1, len(rows) // cap)
        for row in rows[::step][:cap]:
            raw = dict(anchor_raw)
            raw.update(row)
            if point_in_hull(raw, desc, infos):
                starts.append(_coded_vector(active, infos, raw))
    for st in (st_points or {}).values():
        if st and st.get("coded"):
            starts.append(np.array([st["coded"].get(f, 0.0) for f in active]))
            break
    starts.append(_coded_vector(active, infos, anchor_raw))
    seen, uniq = set(), []
    for s in starts:
        key = tuple(np.round(s, 9).tolist())
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq


def _joint_item(item_id, responses, mask, ctx, *, kind):
    """Build one joint window / joint setpoint payload from a candidate domain.

    `kind` is "window" or "setpoint"; the two payloads share the same best point
    (documented: `predicted` describes the best-desirability point of the domain).
    """
    raws = ctx["raws"]
    idx = ctx["best_idx"]
    point = ctx.get("best_point")
    if point is None:
        point = raws[idx] if (idx is not None and len(raws)) else {}
    best_eval = ctx["best_eval"] or {}
    if kind == "window":
        factors = {}
        if ctx.get("grid_domain") and mask is not None and mask.any():
            for j, f in enumerate(ctx["active"]):
                vals = np.array([raws[i][f] for i in np.where(mask)[0]], dtype=float)
                factors[f] = [round(float(vals.min()), 6), round(float(vals.max()), 6)]
        else:
            factors = {f: [None, None] for f in ctx["active"]}
    else:
        factors = {f: (None if point.get(f) is None else round(float(point[f]), 6))
                   for f in ctx["active"]}
    predicted = {}
    for resp in ctx["models"]:
        bundle = interval_bundle(ctx["models"].get(resp), point) if point else {
            "mean": None, "mean_ci95": None, "pi95": None}
        predicted[resp] = {
            "mean": bundle.get("mean"), "mean_ci95": bundle.get("mean_ci95"),
            "pi95": bundle.get("pi95"),
            "d": (best_eval.get("d") or {}).get(resp),
            "unit_status": _unit_entry(ctx["units"], "responses", resp)["unit_status"]}
    satisfied = [r for r in responses if r in (best_eval.get("satisfied") or [])]
    if ctx.get("grid_domain"):
        feasible = bool(mask is not None and mask.any())
    else:
        # continuous optimization: the "domain" is the single solved point
        feasible = bool(responses) and all(r in satisfied for r in responses)
    hard = int(best_eval.get("hard") or 0)
    in_hull = bool(best_eval.get("in_hull", True))
    unit_status = _worst_unit_status(
        ctx["units"], ctx["active"], [r for r in responses if r in ctx["models"]])
    blockers = []
    if unit_status == "missing":
        blockers.append("unit_missing")
    if unit_status == "conflict":
        blockers.append("unit_conflict")
    if hard > 0 or not feasible:
        blockers.append("constraint_infeasible")
    if not in_hull:
        blockers.append("extrapolation")
    if (ctx.get("design_region") or {}).get("design_hull_confidence") == "low":
        blockers.append("design_hull_low_confidence")
    if any((predicted[r].get("pi95") is None) for r in responses):
        blockers.append("no_prediction_interval")
    # DS-04/DS-08: a multi-response recommendation is only executable when every
    # spec-bearing response is satisfied at the recommended point. A response with
    # a goal only expresses a preference and never blocks on its own.
    spec_unmet = [r for r in responses
                  if r in (ctx.get("spec_responses") or []) and r not in satisfied]
    if spec_unmet:
        blockers.append("constraint_infeasible")
    blockers = sorted(set(blockers), key=ACTIONABLE_BLOCKERS.index)
    confidence = ctx["confidence"] if feasible else "low"
    if (ctx.get("design_region") or {}).get("design_hull_confidence") == "low":
        confidence = "low"
    window_ids = _window_ids_covering(ctx["operating_windows"], point) if point else []
    common = {
        "id": item_id, "responses": list(responses),
        "predicted": {r: predicted[r] for r in responses},
        "responses_satisfied": satisfied, "feasible": feasible,
        "hard_constraint_violations": hard,
        "constraint_slack": dict(best_eval.get("slack") or {}),
        "desirability": (round(float(best_eval.get("Deff") or 0.0), 6)
                         if point else None),
        "evidence_level": "L3",
        "confidence": confidence, "window_ids": window_ids,
        "unit_status": unit_status, "actionable": not blockers, "blockers": blockers,
        "selection_scale": ctx["selection_scale"],
    }
    if kind == "window":
        common.update({"constraint_violations": hard, "factors": factors,
                       "method": ctx["method"]})
        return {"id": item_id, "responses": common["responses"],
                "factors": factors, "feasible": feasible,
                "constraint_violations": hard, "predicted": common["predicted"],
                "desirability": common["desirability"], "method": ctx["method"],
                "evidence_level": "L3",
                "responses_satisfied": satisfied,
                "hard_constraint_violations": hard,
                "constraint_slack": common["constraint_slack"],
                "confidence": confidence, "window_ids": window_ids,
                "unit_status": unit_status, "actionable": common["actionable"],
                "blockers": blockers, "selection_scale": ctx["selection_scale"]}
    coverage = None
    if predicted and any(predicted[r].get("pi95") is not None for r in responses):
        coverage = round(max(0.0, 1.0 - 0.05 * len(responses)), 6)
    return {"id": item_id, "method": ctx["method"], "factors": factors,
            "predicted": common["predicted"], "responses_satisfied": satisfied,
            "feasible": feasible, "hard_constraint_violations": hard,
            "constraint_slack": common["constraint_slack"],
            "desirability": common["desirability"], "joint_coverage": coverage,
            "evidence_level": "L3", "confidence": confidence,
            "window_ids": window_ids, "unit_status": unit_status,
            "actionable": common["actionable"], "blockers": blockers,
            "responses": common["responses"],
            "selection_scale": ctx["selection_scale"]}


def _worst_unit_status(units, factors, responses):
    order = {"valid": 2, "missing": 1, "conflict": 0}
    worst = "valid"
    for f in factors:
        st = _unit_entry(units, "factors", f)["unit_status"]
        if order[st] < order[worst]:
            worst = st
    for r in responses:
        st = _unit_entry(units, "responses", r)["unit_status"]
        if order[st] < order[worst]:
            worst = st
    return worst


def _build_joint_designed(rec, df, models, specs, units, cons, desc, design_region,
                          infos, active, model_responses, grid, approach, watchlist,
                          diag, anchor_raw, t95_raw, factor_info, predict_fns, st_points):
    """Joint windows + joint setpoints for the designed mode (P2-2)."""
    joint_windows, joint_setpoints = [], []
    if not models or not active:
        return joint_windows, joint_setpoints
    grid_lo_hi = (grid or {}).get("grid_lo_hi") or {}
    t95_by = {r: (t95_raw.get(r) or 1.64) for r in models}

    if grid is not None and grid["n"]:
        raws, Y, SE = grid["raws"], grid["Y"], grid["SE"]
        Deff, base_ok = grid["Deff"], grid["base_ok"]
        masks = {}
        for resp in model_responses:
            if resp not in Y:
                masks[resp] = np.zeros(len(raws), dtype=bool)
                continue
            t = t95_by.get(resp) or 1.64
            se_eff = np.where(np.isfinite(SE[resp]), SE[resp], 0.0)
            spec = specs.get(resp, {})
            mm = np.ones(len(raws), dtype=bool)
            if spec.get("lsl") is not None:
                mm &= ~((Y[resp] - t * se_eff) < spec["lsl"])
            if spec.get("usl") is not None:
                mm &= ~((Y[resp] + t * se_eff) > spec["usl"])
            masks[resp] = mm
        pool = base_ok & np.logical_and.reduce([masks[r] for r in model_responses]) \
            if model_responses else base_ok
    else:
        raws, Deff, base_ok, masks, pool = [], np.zeros(0), np.zeros(0, dtype=bool), {}, np.zeros(0, dtype=bool)

    # ---- solve: grid best, then constrained refinement (P2-4) ----
    method = "grid_search"
    best_point, best_eval, best_idx = None, None, None
    # Responses that carry a declared specification. A response with only a goal
    # expresses a preference; one with lsl/usl/target is an acceptance criterion
    # (DS-04/DS-08: an executable recommendation must satisfy all of them).
    spec_responses = sorted(
        r for r in model_responses
        if isinstance(specs.get(r), dict)
        and any(specs[r].get(k) is not None for k in ("lsl", "usl", "target")))
    if len(raws):
        if not base_ok.any():
            # nothing legal (all candidates violate the hull / hard constraints):
            # no joint item is emitted — the matrix carries CONSTRAINTS_INFEASIBLE
            return joint_windows, joint_setpoints
        scores = np.where(base_ok, Deff, -np.inf)
        best_idx = int(np.argmax(scores))
        best_point = raws[best_idx]
        best_eval = _point_eval(best_point, models, specs, grid_lo_hi, cons, desc,
                                infos, t95_by)
        # Prefer the best multi-response spec-feasible candidate when the pure
        # desirability peak breaks another response's spec. Never trade a spec for
        # a marginally higher composite score.
        if spec_responses and len(pool) == len(scores) and pool.any():
            unmet = [r for r in spec_responses
                     if r not in (best_eval.get("satisfied") or [])]
            if unmet:
                spec_scores = np.where(pool, Deff, -np.inf)
                cand = int(np.argmax(spec_scores))
                if np.isfinite(spec_scores[cand]):
                    best_idx = cand
                    best_point = raws[cand]
                    best_eval = _point_eval(best_point, models, specs, grid_lo_hi,
                                            cons, desc, infos, t95_by)
    bounds = coded_bounds_from_constraints(cons, infos, active)
    tightened = any(lo > -1.0 + 1e-12 or hi < 1.0 - 1e-12 for lo, hi in bounds.values())
    ineqs = rsm_mod.coded_linear_ineqs(coded_linear_records(cons, infos, active))
    starts = []
    if approach != "grid":
        starts = _design_starts(active, infos, df, desc, anchor_raw, st_points)
    elif best_point is not None:
        starts = [_coded_vector(active, infos, best_point)]
    refined = None
    try:
        refined = rsm_mod.refine_optimum(
            predict_fns, specs, factor_info, active, anchor_raw, grid_lo_hi,
            bounds=bounds if tightened else None,
            constraints=ineqs or None, starts=starts or None)
    except Exception:
        refined = None
    if refined is not None:
        cand_eval = _point_eval(refined["raw"], models, specs, grid_lo_hi, cons, desc,
                                infos, t95_by)
        better = (best_eval is None
                  or cand_eval["Deff"] >= best_eval["Deff"] - 1e-9)
        if spec_responses and best_eval is not None:
            cur_ok = all(r in (best_eval.get("satisfied") or []) for r in spec_responses)
            cand_ok = all(r in (cand_eval.get("satisfied") or []) for r in spec_responses)
            if cur_ok and not cand_ok:
                better = False
        if cand_eval["hard"] == 0 and cand_eval["in_hull"] and better:
            best_point, best_eval = refined["raw"], cand_eval
            best_idx = None
            method = "constraint_projection" if (cons or tightened or ineqs) else "desirability_lbfgsb"

    if approach != "grid" and best_point is None:
        # no run rows available for a start: fall back to the anchor point
        best_point = dict(anchor_raw)
        best_eval = _point_eval(best_point, models, specs, grid_lo_hi, cons, desc,
                                infos, t95_by)
        method = "constraint_projection" if (cons or ineqs) else "desirability_lbfgsb"
    if best_point is None:
        return joint_windows, joint_setpoints

    if best_eval is None:
        best_eval = _point_eval(best_point, models, specs, grid_lo_hi, cons, desc,
                                infos, t95_by)

    # continuous mode has no grid mask: the domain is the point itself
    if approach != "grid":
        pool = np.array([True])
        raws = [best_point]

    selection_scale = "desirability" if any(
        (best_eval.get("d") or {}).get(r) is not None for r in model_responses) else "std_effect"
    confidence = _joint_confidence(model_responses, models)
    ctx = {"raws": raws, "active": active, "models": models, "units": units,
           "best_idx": best_idx, "best_point": best_point, "best_eval": best_eval,
           "grid_domain": approach == "grid", "spec_responses": spec_responses,
           "operating_windows": rec.get("operating_windows") or [],
           "design_region": design_region, "confidence": confidence,
           "method": method, "selection_scale": selection_scale}
    jw = _joint_item("JW-001", model_responses, pool, ctx, kind="window")
    js = _joint_item("JS-001", model_responses, pool, ctx, kind="setpoint")
    joint_windows.append(jw)
    joint_setpoints.append(js)
    if not js["feasible"] and approach == "grid":
        # honest disclosure: the full response set has no joint domain — emit the
        # best single-response domains as alternatives (deterministic order)
        for resp in model_responses[:4]:
            mm = masks.get(resp)
            if mm is None or not mm.any():
                continue
            sub_pool = base_ok & mm
            if not sub_pool.any():
                continue
            scores = np.where(sub_pool, Deff, -np.inf)
            sub_idx = int(np.argmax(scores))
            sub_ctx = dict(ctx)
            sub_ctx["best_idx"] = sub_idx
            sub_ctx["best_point"] = raws[sub_idx]
            sub_ctx["best_eval"] = _point_eval(raws[sub_idx], models, specs,
                                               grid_lo_hi, cons, desc, infos, t95_by)
            rid = f"JW-{len(joint_windows) + 1:03d}"
            joint_windows.append(_joint_item(rid, [resp], sub_pool, sub_ctx, kind="window"))
            joint_setpoints.append(_joint_item(
                f"JS-{len(joint_setpoints) + 1:03d}", [resp], sub_pool, sub_ctx,
                kind="setpoint"))
        _watch(watchlist, {
            "code": "JOINT_DOMAIN_INFEASIBLE",
            "message": ("全部响应无法同时满足 — joint_windows/joint_setpoints 首项 feasible=false，"
                        "其余为单响应可行情形的替代建议（DS-04：按 desirability 标度选优）"),
            "factor": None, "response": None, "threshold": None})
    if best_eval.get("soft_violated"):
        _watch(watchlist, {
            "code": "SOFT_CONSTRAINT_RELAXED",
            "message": (f"推荐点放宽了软约束：{'、'.join(best_eval['soft_violated'])}"
                        f"（desirability 乘子 {round(best_eval['penalty'], 6)}）"),
            "factor": None, "response": None, "threshold": None})
    return joint_windows, joint_setpoints


def _joint_setpoint_mirror(joint_setpoints):
    """Legacy `setpoints` mirror of the joint setpoints (P2-2, additive).

    Two entry shapes so both legacy consumers keep working:
    - `factor == "MULTI"` with `expected_response.raw`/`D` (the optimizer-loop's
      W2-optimum seed shape). It mirrors the v1.1 CONSTRAINED joint optimum, never
      the legacy unconstrained refinement — that one may violate declared hard
      constraints and must not be handed to a closed loop.
    - one entry per factor per setpoint (`factor`, `value`), which is the direct
      "same content" mirror.
    """
    out = []
    primary = next((s for s in joint_setpoints if s.get("feasible") is True), None)
    if primary is None and joint_setpoints:
        primary = joint_setpoints[0]
    if primary is not None:
        out.append({
            "factor": "MULTI", "value": 0.0,
            "expected_response": {
                "kind": "joint_setpoint", "setpoint_id": primary.get("id"),
                "raw": dict(primary.get("factors") or {}),
                "D": primary.get("desirability"),
                "responses_satisfied": primary.get("responses_satisfied"),
                "selection_scale": primary.get("selection_scale"),
                "predicted": primary.get("predicted") or {}},
            "confidence": primary.get("confidence")})
    for s in joint_setpoints:
        pred = s.get("predicted") or {}
        for f, v in (s.get("factors") or {}).items():
            out.append({
                "factor": f, "value": v,
                "expected_response": {
                    "kind": "joint_setpoint", "setpoint_id": s.get("id"),
                    "responses_satisfied": s.get("responses_satisfied"),
                    "desirability": s.get("desirability"),
                    "selection_scale": s.get("selection_scale"),
                    "predicted": pred},
                "confidence": s.get("confidence")})
    return out


# ------------------------------------------------------------------ matrix (P2-6)

def build_factor_response_matrix(declared_factors, declared_responses, windows, df,
                                 infos, effect_table, diag, specs):
    """factor x response matrix with ZERO silent cells (contract §5.1/§5.4, DS-03).

    Every declared factor x declared response pair carries either `window_id` or
    a `no_window_reason` from the frozen §5.4 enum. Reason priority (documented):
      RESPONSE_ALL_MISSING > NOT_ESTIMABLE(factor) > window present >
      CONSTRAINTS_INFEASIBLE > HULL_UNSUPPORTED > GRID_EMPTY(deferred/continuous) >
      NO_FEASIBLE_POINT > EXTRAPOLATION_ONLY > TREND_CONFOUNDED_NO_WINDOW >
      DIRECTION_ONLY > NO_SIGNIFICANT_FACTOR > NOT_ESTIMABLE(default)
    """
    win_by_pair = {}
    for w in windows:
        win_by_pair.setdefault((w.get("factor"), w.get("response")), w)
    no_sig = diag.get("no_significant") or set()
    rows = []
    for factor in sorted(set(declared_factors)):
        for response in sorted(set(declared_responses)):
            win = win_by_pair.get((factor, response))
            main = _main_test(effect_table, response, factor)
            delta = None
            if main and main.get("coefficient") is not None:
                hr = (infos.get(factor) or {}).get("half_range")
                delta = round(main["coefficient"] / hr, 6) if hr else None
            direction = None
            if main and main.get("coefficient") is not None:
                direction = "+" if main["coefficient"] > 0 else "-"
            effect_size = (main or {}).get("partial_eta_squared")
            row = {
                "factor": factor, "response": response,
                "window_id": None, "no_window_reason": None,
                "delta": delta, "effect_size": effect_size, "direction": direction,
                "fdr_q": (main or {}).get("q_value_bh"),
                "evidence_level": "L3" if main else None,
                "confidence": None,
            }
            if win is not None:
                row["window_id"] = win.get("id")
                row["confidence"] = win.get("confidence")
                if delta is None:
                    row["delta"] = (win.get("expected_effect") or {}).get("delta")
            else:
                row["no_window_reason"] = _no_window_reason(
                    factor, response, df, infos, effect_table, diag, no_sig, main)
                row["confidence"] = _c7_confidence(
                    (main or {}).get("q_value_bh"),
                    (effect_size or 0) >= EFFECT_GATE_ETA2, True, None)
            rows.append(row)
    return rows


def _no_window_reason(factor, response, df, infos, effect_table, diag, no_sig, main):
    """Documented reason priority for a (factor, response) cell (contract §5.4)."""
    if response in (diag.get("response_all_missing") or set()):
        return "RESPONSE_ALL_MISSING"
    if factor in (diag.get("not_estimable") or set()):
        return "NOT_ESTIMABLE"
    if diag.get("constraints_infeasible"):
        return "CONSTRAINTS_INFEASIBLE"
    if diag.get("hull_failed"):
        return "HULL_UNSUPPORTED"
    if diag.get("continuous") or factor in (diag.get("deferred") or set()):
        return "GRID_EMPTY"
    if diag.get("no_feasible_point"):
        return "NO_FEASIBLE_POINT"
    if diag.get("extrapolation_only"):
        return "EXTRAPOLATION_ONLY"
    if (factor, response) in (diag.get("trend_blocked") or set()):
        return "TREND_CONFOUNDED_NO_WINDOW"
    if (factor, response) in (diag.get("direction_only") or set()):
        return "DIRECTION_ONLY"
    if (factor, response) in (no_sig or set()):
        return "NO_SIGNIFICANT_FACTOR"
    if main is None or not main.get("estimable"):
        return "NOT_ESTIMABLE"
    return "DESIGN_NOT_INFORMATIVE"


# ------------------------------------------------------------------ disclosure / refs

def _selection_scale(rec):
    """DS-04: which unit-free scale ranked the joint winners."""
    for s in rec.get("joint_setpoints") or []:
        for p in (s.get("predicted") or {}).values():
            if p.get("d") is not None:
                return "desirability"
    return "std_effect"


def _actionable_summary(rec):
    blocked, n_act = [], 0
    for w in rec.get("operating_windows") or []:
        if w.get("actionable"):
            n_act += 1
        else:
            blocked.append({"window_id": w.get("id"),
                            "reasons": list(w.get("actionable_blockers") or [])})
    for s in rec.get("joint_setpoints") or []:
        if s.get("actionable"):
            n_act += 1
        else:
            blocked.append({"setpoint_id": s.get("id"),
                            "reasons": list(s.get("blockers") or [])})
    return {"n_actionable": n_act, "n_blocked": len(blocked), "blocked": blocked}


def _interval_disclosure(designed, joint_setpoints, model_responses, selection_scale):
    coverage = _mc_coverage_check()
    joint_cov = None
    for s in joint_setpoints or []:
        if s.get("joint_coverage") is not None:
            joint_cov = s["joint_coverage"]
            break
    if designed:
        note = ("四类区间互不替代：ci95/mean_ci95=均值响应 95% CI（既有 ci95 语义，本版未改写）；"
                "pi95=单个未来观测预测区间（含 1 +，同点宽度必大于均值 CI）；"
                "pi95 不是合格率/通过率/收率，禁止据此宣称达标；"
                "tolerance_interval_95_95=95% 总体 @95% 置信容差区间。"
                "joint_coverage 为多响应联合覆盖的 Bonferroni 名义值 1-0.05*m。"
                f"联合选优标度：{selection_scale}（禁止跨单位比较 raw delta，DS-04）。")
        return {"pi_method": ea_mod.PI95_METHOD,
                "ci_method": ea_mod.MEAN_CI95_METHOD + "（均值响应，不是预测区间）",
                "effect_ci_method": ea_mod.EFFECT_CI95_METHOD,
                "tolerance_method": ea_mod.TOLERANCE_METHOD,
                "note": note, "joint_coverage": joint_cov,
                "coverage_check": coverage}
    note = ("观察性模式无回归模型：不产出均值 CI / 预测区间 / 容差区间，"
            "也不可计算 PI 覆盖率。expected_effect.ci95/effect_ci95 为三分位差值的 "
            "Welch CI（相关级证据，方向已按目标校正），闭环执行前必须完成确认试验。"
            f"选优标度：{selection_scale}。")
    return {"pi_method": None,
            "ci_method": "Welch t CI of the tercile-Q3 - Q1 mean difference (observational)",
            "effect_ci_method": "Welch t CI of the tercile delta (same as ci95)",
            "tolerance_method": None, "note": note, "joint_coverage": None,
            "coverage_check": None}


def _artifact_ref(rel_path, ctx, count_key, extra):
    """Pointer-only artifact reference (contract §5.1) — never inlined content."""
    ref = {"path": rel_path, "sha256": None}
    if count_key:
        ref[count_key] = None
    ref.update(extra or {})
    run_dir = ctx.get("run_dir") or ctx.get("_run_dir")
    if not run_dir:
        return ref
    p = Path(str(run_dir)) / rel_path
    try:
        if not p.exists():
            return ref
        import hashlib
        ref["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if count_key and data.get(count_key) is not None:
                ref[count_key] = data[count_key]
            for k in (extra or {}):
                if data.get(k) is not None:
                    ref[k] = data[k]
    except Exception:
        pass
    return ref


# ------------------------------------------------------------------ observational v1.1

def observational_windows_v11(stability, profile, ctx, df, correlation=None, *,
                              brief=None, seed=None):
    """v1.1 observational entry point (contract §9). Same key set as the designed
    variant; designed-only keys are null / [] (no model => no joint domain)."""
    lw, interactions, confirmations, watchlist, _lsp = observational_windows(
        stability, profile, ctx, df, correlation=correlation)
    declared_responses = [r.get("col") for r in (ctx.get("responses") or [])
                          if isinstance(r, dict) and r.get("col")]
    declared_factors = [f.get("col") for f in (ctx.get("factors") or [])
                        if isinstance(f, dict) and f.get("col")]
    if not declared_factors:
        declared_factors = list(ctx.get("_predictor_cols") or [])
    units = ea_mod.build_units_block(ctx, brief, declared_factors, declared_responses)
    cons = normalize_constraints(ctx, brief)
    confirmed = bool(ctx.get("confirmation_completed") or ctx.get("confirmed"))
    design_region = {
        "type": None, "hull": "unbounded", "coded_bounds": {}, "axial_alpha": None,
        "max_leverage": None, "mean_leverage": None, "leverage_threshold": None,
        "n_exceed": None, "extrapolation_risk": "high", "evaluated_points": 0,
        "design_hull_confidence": "low", "factor_order": [], "n_design_rows": 0,
        "note": "observational data: no designed region (hull unbounded)"}
    trend_pairs = set()
    trend_blocked = set()
    for p in ((correlation or {}).get("pairs") or []):
        if not isinstance(p, dict):
            continue
        if p.get("trend_confounded") is True:
            trend_pairs.add((p.get("target"), p.get("parameter")))
    for e in watchlist:
        if e.get("code") == "TREND_CONFOUNDED_NO_WINDOW":
            trend_blocked.add((e.get("factor"), e.get("response")))

    windows = []
    for w in lw:
        clone = copy.deepcopy(w)
        f, resp = clone["factor"], clone.get("response")
        unit_f = _unit_entry(units, "factors", f)
        unit_r = _unit_entry(units, "responses", resp) if resp else {
            "canonical": None, "unit_status": "missing"}
        ee = clone.setdefault("expected_effect", {})
        ee["mean_ci95"] = None
        ee["pi95"] = None
        ee["pi95_method"] = None
        ee["effect_ci95"] = copy.deepcopy(ee.get("ci95"))
        ee["unit_status"] = unit_r["unit_status"]
        ee["response_unit"] = unit_r["canonical"]
        ee["tolerance_interval_95_95"] = None
        ee["unit"] = unit_r["canonical"]
        clone["window_role"] = "marginal_diagnostic"
        clone["in_design_hull"] = True
        clone["constraints_applied"] = constraints_applied_for(cons, f)
        clone["constraint_violations"] = 0
        clone["predicted_at_center"] = {"mean": None, "mean_ci95": None,
                                        "pi95": None, "ti95_95": None}
        blockers = []
        if unit_f["unit_status"] == "missing" or unit_r["unit_status"] == "missing":
            blockers.append("unit_missing")
        if unit_f["unit_status"] == "conflict" or unit_r["unit_status"] == "conflict":
            blockers.append("unit_conflict")
        if (f, resp) in trend_pairs:
            blockers.append("trend_confounded")
        blockers.append("design_hull_low_confidence")
        blockers.append("no_prediction_interval")
        if clone.get("confirmation_needed") and not confirmed:
            blockers.append("non_randomized_confirmation_pending")
        clone["actionable_blockers"] = sorted(set(blockers), key=ACTIONABLE_BLOCKERS.index)
        clone["actionable"] = False  # observational windows are never actionable alone
        windows.append(clone)
    for f in declared_factors:
        st = _unit_entry(units, "factors", f)["unit_status"]
        if st in ("missing", "conflict"):
            _watch(watchlist, {"code": "UNIT_MISSING" if st == "missing" else "UNIT_CONFLICT",
                               "message": f"因子 {f} 的单位状态 {st} — 相关窗口 actionable=false",
                               "factor": f, "response": None, "threshold": None})

    sha = ctx.get("input_sha256") or ctx.get("_input_sha256")
    version = ctx.get("script_version") or ctx.get("_script_version") or "1.1"
    seed_v = seed if seed is not None else ctx.get("seed")
    rec = assemble("observational", windows, interactions, confirmations, watchlist,
                   [], ctx, df, profile, stability, sha, version, seed_v)
    rec["contract_version"] = "1.1"
    diag = {"constraints_infeasible": False, "hull_failed": False, "continuous": False,
            "deferred": set(), "no_feasible_point": False, "extrapolation_only": False,
            "trend_blocked": trend_blocked, "direction_only": set(), "not_estimable": set(),
            "response_all_missing": set(),
            "no_significant": {(f, r) for f in declared_factors
                               for r in declared_responses}}
    rec["joint_windows"] = []
    rec["joint_setpoints"] = []
    rec["units"] = units
    rec["design_region"] = design_region
    rec["grid_plan"] = None
    rec["constraints"] = [
        {"factor": r["factor"], "type": r["type"], "min": r["min"], "max": r["max"],
         "hard": r["hard"], "source": r["source"]} for r in cons]
    rec["factor_response_matrix"] = build_factor_response_matrix(
        declared_factors, declared_responses, rec["operating_windows"], df,
        {f: {"col": f, "type": "numeric", "half_range": None, "zero_variance": False}
         for f in declared_factors},
        {}, diag, _specs_by_response(ctx))
    rec["actionable_summary"] = _actionable_summary(rec)
    rec["interval_disclosure"] = _interval_disclosure(
        designed=False, joint_setpoints=[], model_responses=declared_responses,
        selection_scale="std_effect")
    rec["association_screen_ref"] = _artifact_ref(
        "02_analysis/association_screen.json", ctx, "n_pairs", {"causal_claim": "none"})
    rec["next_design_ref"] = _artifact_ref(
        "conclusions/next_design.json", ctx, None,
        {"recommended_action": None, "primary_action_id": None})
    rec["windows"] = rec["operating_windows"]
    return rec


# ------------------------------------------------------------------ wiring helper

def recommendations_payload(recs):
    """recommendations.json payload for the v1.1 dict returned by the entry points.

    The entry points also return the contract §9 key `windows`, which is the SAME
    list object as `operating_windows` (a return-value convenience). The written
    artifact must not carry both: quality_gate.mjs G6 compares the top level
    against the frozen §5.1 key set, which has `operating_windows` only. This
    helper returns a shallow copy with the alias removed — write it verbatim.
    """
    payload = dict(recs or {})
    payload.pop("windows", None)
    return payload


# ------------------------------------------------------------------ optimizer-loop view

def windows_seed_export(recs):
    """optimizer-loop compatible view (contract §10).

    Consumes (a) marginal windows with window_role == "marginal_diagnostic" AND
    actionable == true, and (b) joint_setpoints with actionable == true,
    confidence >= medium and evidence_level present. Everything rejected lands in
    `rejected_prior` with {source, window_id|setpoint_id, reason} so the pruning
    is traceable.
    """
    out_windows, out_setpoints, rejected = [], [], []
    for w in (recs or {}).get("operating_windows") or []:
        reasons = []
        if w.get("window_role") != "marginal_diagnostic":
            reasons.append("window_role_not_marginal_diagnostic")
        if w.get("actionable") is not True:
            reasons.extend(w.get("actionable_blockers") or ["not_actionable"])
        if reasons:
            rejected.append({"source": "operating_window", "window_id": w.get("id"),
                             "reason": "; ".join(dict.fromkeys(reasons))})
        else:
            out_windows.append(w)
    for s in (recs or {}).get("joint_setpoints") or []:
        reasons = []
        if s.get("actionable") is not True:
            reasons.extend(s.get("blockers") or ["not_actionable"])
        if s.get("confidence") not in ("high", "medium"):
            reasons.append("confidence_below_medium")
        if not s.get("evidence_level"):
            reasons.append("missing_evidence_level")
        if reasons:
            rejected.append({"source": "joint_setpoint", "setpoint_id": s.get("id"),
                             "reason": "; ".join(dict.fromkeys(reasons))})
        else:
            out_setpoints.append(s)
    return {"contract_version": (recs or {}).get("contract_version"),
            "windows": out_windows, "setpoints": out_setpoints,
            "rejected_prior": rejected}



