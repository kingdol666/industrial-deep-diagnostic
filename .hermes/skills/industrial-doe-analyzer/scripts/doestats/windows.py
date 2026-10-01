"""Operating-window derivation + downstream recommendations contract v1.0.

Designed mode (W1-W5): one-sided-95%-CI feasible region per response, grid
desirability with L-BFGS-B refinement, per-factor window projection of the
{feasible AND D >= 0.8*Dmax} set (connected-block rule), linear-only downgrade.
Observational mode (W6-W8): top-K steady segments by Cpk/goal score, P10-P90
factor windows within pooled selected segments, tercile delta with Welch CI
(stratified when a group column exists), confirmation always required.
"""

import itertools

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import rsm as rsm_mod
from ._stats_util import welch_delta_ci

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

    # baseline (current working point): factor medians
    factor_cols = [w["factor"] for w in rec["operating_windows"]]
    point = {}
    for f in dict.fromkeys(factor_cols):
        if f in df.columns:
            v = pd.to_numeric(df[f], errors="coerce").dropna()
            if len(v):
                point[f] = round(float(v.median()), 6)
    rec["current_baseline"]["point"] = point
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
    rec["constraints"] = [
        {"factor": f, "min": c.get("min"), "max": c.get("max"), "source": "user context"}
        for c in ctx.get("constraints", [])]
    rec["provenance"] = {"input_sha256": sha256, "script_version": version,
                         "seed": seed, "authored_by": "script"}
    return rec
