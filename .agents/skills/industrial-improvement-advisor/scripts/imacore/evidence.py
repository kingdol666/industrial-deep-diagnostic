"""imacore.evidence — three evidence legs (dose-response / window contrast /
action attribution) + the statistics the three gates need (method_notes §2-3).

All statistics come from family modules (core_stats / doestats / tune_stats
called IN-PROCESS — no shell, no subprocess); scipy's theilslopes/kendalltau
are the same primitives lstcore.drift uses (imported here directly so the
dose-response leg works on bin medians).
"""

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy import stats as sps

from . import _io

DESIGNED_TYPES = {"full_factorial", "fractional_factorial", "rsm_ccf", "rsm_ccd",
                  "rsm_bbd", "ccd", "bbd", "box_behnken", "latin_hypercube", "rsm"}


# --------------------------------------------------------------- primitives

def p_from_r(r, n):
    """Two-tailed p of a Pearson r (core_stats t-equation, reused)."""
    cs = _io.core_stats
    if cs is None or r is None or n is None or n < 4:
        return None
    if abs(r) >= 1.0:
        return 0.0
    t = abs(r) * math.sqrt((n - 2) / (1.0 - r * r))
    return float(cs._t_pvalue(t, n - 2))


def pair_stats(df, lever, kpi):
    cs = _io.core_stats
    sub = df[[lever, kpi]].dropna()
    if cs is None or len(sub) < _io.CONSTANTS["min_relation_points"]:
        return {"ok": False, "n": int(len(sub)), "r": None, "p": None,
                "reason": "reuse_leg_unavailable" if cs is None else "insufficient_data"}
    try:
        res = cs.pearson(sub[lever].tolist(), sub[kpi].tolist())
    except Exception:
        return {"ok": False, "n": int(len(sub)), "r": None, "p": None,
                "reason": "reuse_leg_unavailable"}
    r = res.get("r")
    n = int(res.get("n") or len(sub))
    p = p_from_r(r, n)
    return {"ok": r is not None, "n": n, "r": _io.finite(r), "p": _io.finite(p, 10)}


def peak_ccf(df, lever, kpi, max_lag):
    """Lag-bounded CCF with per-lag p-values (五陷阱: 时滞错配)."""
    cs = _io.core_stats
    if cs is None:
        return {"available": False, "entries": [], "peak": None}
    lag = max(1, int(max_lag))
    try:
        ccf = cs.full_lag_ccf(df[lever].tolist(), df[kpi].tolist(), lag)
    except Exception:
        return {"available": False, "entries": [], "peak": None}
    entries = []
    for e in ccf:
        r = e.get("r")
        entries.append({"lag": int(e["lag"]), "r": _io.finite(r),
                        "n": int(e.get("n") or 0),
                        "p": _io.finite(p_from_r(r, e.get("n") or 0), 10)})
    with_r = [e for e in entries if e["r"] is not None]
    peak = max(with_r, key=lambda e: abs(e["r"])) if with_r else None
    return {"available": True, "entries": entries, "peak": peak, "max_lag": lag}


def fdr_q_for_levers(ccf_by_lever):
    """BH family = every (lever × lag) test inside ONE KPI (method_notes §2).

    Returns {lever: q_peak} using the peak-|r| lag test per lever.
    """
    if _io.bh_adjust is None:
        return {lever: None for lever in ccf_by_lever}
    pvals = []
    for lever, ccf in ccf_by_lever.items():
        peak = (ccf or {}).get("peak") or {}
        pvals.append(peak.get("p"))
    qs = _io.bh_adjust(pvals)
    return {lever: qs[i] for i, lever in enumerate(ccf_by_lever)}


# ------------------------------------------------------------------- gates

def temporal_gate(ccf, dead_time):
    """None = not_assessable (dead_time missing); never assume 0."""
    if dead_time is None:
        return None
    peak = (ccf or {}).get("peak")
    if not peak or peak.get("r") is None:
        return False
    max_lag = int(max(1, math.ceil(float(dead_time))))
    return bool(0 <= peak["lag"] <= max_lag
                and abs(peak["r"]) >= _io.CONSTANTS["min_effect_r"])


def confound_gate(df, lever, kpi, group_col=None):
    """Stratified re-check when a group column exists; else high-leverage LOO."""
    cs = _io.core_stats
    if cs is None:
        return {"ok": False, "available": False}
    try:
        full = cs.pearson(df[lever].tolist(), df[kpi].tolist())
    except Exception:
        return {"ok": False, "available": False}
    base_r = full.get("r")
    if base_r is None:
        return {"ok": False, "available": False}
    base_sign = 1 if base_r > 0 else -1
    if group_col and group_col in df.columns:
        signs = []
        for _, group in df.groupby(group_col):
            clean = group[[lever, kpi]].dropna()
            if len(clean) < 20:
                continue
            try:
                r = cs.pearson(clean[lever].tolist(), clean[kpi].tolist()).get("r")
            except Exception:
                continue
            if r is not None:
                signs.append(1 if r > 0 else -1)
        if signs:
            ok = len(set(signs)) == 1 and signs[0] == base_sign
            return {"ok": bool(ok), "available": True, "method": "stratified",
                    "group_signs": signs}
    # high-leverage leave-one-out via the family's canonical implementation
    sp = getattr(_io, "_spurious", None)
    if sp is not None and hasattr(sp, "_leave_one_out_leverage"):
        try:
            res = sp._leave_one_out_leverage(df[lever].tolist(), df[kpi].tolist())
        except Exception:
            res = None
        if isinstance(res, dict) and "leveraged" in res:
            full_r = res.get("full_r")
            sign_ok = (full_r is not None
                       and (1 if full_r > 0 else -1) == base_sign)
            return {"ok": bool((not res.get("leveraged")) and sign_ok),
                    "available": True,
                    "method": "anti_spurious_leave_one_out_leverage",
                    "max_shift": res.get("max_shift"),
                    "full_r": full_r}
    # fallback: drop the 5 most extreme lever points and recheck
    sub = df[[lever, kpi]].dropna().copy()
    if len(sub) < 30:
        return {"ok": False, "available": False}
    extreme_idx = (sub[lever] - sub[lever].median()).abs().nlargest(5).index
    reduced = sub.drop(index=extreme_idx)
    try:
        r2 = cs.pearson(reduced[lever].tolist(), reduced[kpi].tolist()).get("r")
    except Exception:
        return {"ok": False, "available": False}
    if r2 is None:
        return {"ok": False, "available": False}
    sign_ok = (1 if r2 > 0 else -1) == base_sign
    strength_ok = abs(r2) >= 0.5 * abs(base_r)
    return {"ok": bool(sign_ok and strength_ok), "available": True,
            "method": "leave_one_out_high_leverage",
            "loo_r": _io.finite(r2), "full_r": _io.finite(base_r)}


# ------------------------------------------------------- dose-response leg

def dose_response(df, lever, kpi):
    """Equal-frequency binned slope + CI95 + monotonicity (method_notes §3).

    Returns {"status": "estimable"|"not_estimable", ...}. A monotonicity miss
    keeps the point estimate but sets verified=False (no extrapolation right).
    """
    const = _io.CONSTANTS
    sub = df[[lever, kpi]].dropna()
    n = len(sub)
    if n < max(const["min_relation_points"],
               const["dose_bins_min"] * const["dose_bin_min_n"]):
        return {"status": "not_estimable", "reason": "no_significant_relation",
                "detail": f"n={n} below binning floor"}
    k = min(const["dose_bins_max"], n // const["dose_bin_min_n"])
    if k < const["dose_bins_min"]:
        return {"status": "not_estimable", "reason": "no_significant_relation",
                "detail": f"bins={k} < {const['dose_bins_min']}"}
    bin_idx = np.floor((sub[lever].rank(method="first") - 1) * k / n).astype(int)
    bin_idx = np.clip(bin_idx, 0, k - 1)
    sub = sub.assign(_bin=bin_idx)
    bins = []
    for b in range(k):
        part = sub[sub["_bin"] == b]
        if len(part) < const["dose_bin_min_n"]:
            continue
        bins.append({"b": b, "n": int(len(part)),
                     "x": _io.finite(part[lever].median()),
                     "y": _io.finite(part[kpi].median())})
    if len(bins) < const["dose_bins_min"]:
        return {"status": "not_estimable", "reason": "no_significant_relation",
                "detail": f"usable bins={len(bins)}"}
    xs = np.asarray([b["x"] for b in bins], dtype=float)
    ys = np.asarray([b["y"] for b in bins], dtype=float)
    slope_ci = [None, None]
    slope = None
    if _io.ols_fit is not None:
        try:
            beta, rank, rss, xtx_inv, _Xa = _io.ols_fit(xs.reshape(-1, 1), ys)
            slope = float(beta[1])
            if xtx_inv is not None and len(bins) > 2:
                dof = len(bins) - 2
                sigma2 = rss / dof
                se = math.sqrt(max(sigma2 * xtx_inv[1, 1], 0.0))
                tcrit = float(sps.t.ppf(0.975, dof))
                slope_ci = [_io.finite(slope - tcrit * se),
                            _io.finite(slope + tcrit * se)]
        except Exception:
            slope = None
    if slope is None:
        slope = (float((ys[-1] - ys[0]) / (xs[-1] - xs[0]))
                 if abs(xs[-1] - xs[0]) > 1e-12 else 0.0)
    ts_ok = True
    try:
        ts_slope = float(sps.theilslopes(ys, xs)[0])
        ts_ok = (ts_slope > 0) == (slope > 0) or abs(ts_slope) < 1e-12
    except Exception:
        ts_ok = False
    try:
        mk_p = float(sps.kendalltau(xs, ys).pvalue)
    except Exception:
        mk_p = None
    monotone = bool(mk_p is not None
                    and mk_p < const["monotonicity_alpha"]
                    and abs(slope) > 1e-12)
    pair = pair_stats(df, lever, kpi)
    return {
        "status": "estimable",
        "bins": bins,
        "slope": _io.finite(slope),
        "slope_ci95": slope_ci,
        "theil_sen_consistent": bool(ts_ok),
        "monotone": monotone,
        "mk_p": _io.finite(mk_p, 10),
        "r": pair.get("r"), "p": pair.get("p"), "n_pairs": pair.get("n"),
        "verified": bool(monotone and ts_ok),
    }


# ------------------------------------------------- designed-experiment effect

def load_doe_effects(run_dir, df):
    """Designed-experiment effect leg: reuse the DOE analyzer's fitted model.

    `02_analysis/effect_table.json` families[].tests[] carry per-term
    coefficients with a 95% CI on the CODED scale ((x-mean)/half_range). One
    first-order estimable term per (factor, response) is converted back to raw
    units with the factor's half-range from THIS data window. Designed
    evidence: randomization replaces the observational temporal condition.
    """
    path = Path(run_dir) / "02_analysis" / "effect_table.json"
    if not path.is_file():
        return {"status": "absent", "effects": {}}
    try:
        data = _io.read_json(path)
    except (OSError, ValueError):
        return {"status": "failed", "effects": {}}
    effects = {}
    for fam in data.get("families") or []:
        if not isinstance(fam, dict):
            continue
        response = fam.get("response")
        for t in fam.get("tests") or []:
            if not isinstance(t, dict) or t.get("order") != 1:
                continue
            if t.get("estimable") is not True:
                continue
            term = t.get("term")
            coef = t.get("coefficient")
            if term not in df.columns or coef is None:
                continue
            vals = df[term].dropna()
            if len(vals) < 3:
                continue
            half = float(vals.max() - vals.min()) / 2.0
            if half <= 1e-12:
                continue
            ci = t.get("effect_ci95") or [None, None]
            effects[(str(term), str(response))] = {
                "slope": float(coef) / half,
                "slope_ci95": [
                    (float(ci[0]) / half) if ci and ci[0] is not None else None,
                    (float(ci[1]) / half) if len(ci) > 1 and ci[1] is not None else None,
                ],
                "p": t.get("p_value"),
                "q": t.get("q_value_bh"),
                "n": fam.get("n"),
                "design": "designed",
                "term_unit": t.get("term_unit"),
            }
    return {"status": "used" if effects else "not_estimable",
            "effects": effects}


# ---------------------------------------------------------- window contrast

def load_doe_windows(doe_run_dir):
    """Read <doe_run>/conclusions/recommendations.json operating windows."""
    path = Path(doe_run_dir) / "conclusions" / "recommendations.json"
    if not path.is_file():
        return {"status": "failed",
                "reason": f"recommendations.json missing at {path}",
                "windows": {}, "analysis_mode": None, "design_type": None}
    try:
        data = _io.read_json(path)
    except (OSError, ValueError) as exc:
        return {"status": "failed", "reason": f"unreadable recommendations.json: {exc}",
                "windows": {}, "analysis_mode": None, "design_type": None}
    analysis_mode = data.get("analysis_mode")
    design_type = ((data.get("design_region") or {}).get("type")
                   if isinstance(data.get("design_region"), dict) else None)
    designed = bool(analysis_mode == "designed"
                    and str(design_type or "").lower() in DESIGNED_TYPES)
    windows = {}
    for w in data.get("operating_windows") or []:
        if not isinstance(w, dict):
            continue
        factor = w.get("factor")
        rng = w.get("range")
        if not factor or not isinstance(rng, (list, tuple)) or len(rng) != 2:
            continue
        if rng[0] is None or rng[1] is None:
            continue
        windows[str(factor)] = {
            "factor": str(factor),
            "range": [float(min(rng)), float(max(rng))],
            "response": w.get("response"),
            "confirmation_needed": w.get("confirmation_needed"),
            "actionable": w.get("actionable"),
            "window_role": w.get("window_role"),
            "unit": w.get("factor_unit"),
            "designed": bool(designed and w.get("confirmation_needed") is False),
        }
    return {"status": "used", "windows": windows, "analysis_mode": analysis_mode,
            "design_type": design_type,
            "designed_available": bool(designed
                                       and any(w["designed"] for w in windows.values()))}


def window_contrast(df, lever, kpi, window):
    """Inside-window vs outside-window KPI contrast (Welch + effective n)."""
    lo, hi = window["range"]
    sub = df[[lever, kpi]].dropna()
    inside = sub[(sub[lever] >= lo) & (sub[lever] <= hi)]
    outside = sub[(sub[lever] < lo) | (sub[lever] > hi)]
    if len(inside) < 10 or len(outside) < 10:
        return {"status": "not_estimable", "reason": "window_truncated",
                "detail": f"n_in={len(inside)} n_out={len(outside)}"}
    if _io.welch_delta_ci is None:
        return {"status": "not_estimable", "reason": "reuse_leg_unavailable"}
    res = _io.welch_delta_ci(inside[kpi].to_numpy(), outside[kpi].to_numpy())
    if res is None:
        return {"status": "not_estimable", "reason": "window_truncated"}
    delta, dlo, dhi, n_in, n_out = res
    return {
        "status": "estimable",
        "delta_in_minus_out": _io.finite(delta),
        "ci95": [_io.finite(dlo), _io.finite(dhi)],
        "n_in": int(n_in), "n_out": int(n_out),
        "median_current": _io.finite(sub[kpi].median()),
        "median_in": _io.finite(inside[kpi].median()),
        "current_in_window": bool(lo <= float(sub[lever].median()) <= hi),
        "designed": bool(window.get("designed")),
    }


# --------------------------------------------------------- attribution leg

def attribution_leg(run_dir, data_rel, time_col, kpis, dead_time, action_log_path):
    """Call tune_stats.attribute() IN-PROCESS per KPI; map reports to levers.

    Never fabricates: missing logs / metric / dead-time go to degradations and
    every affected action is capped at C.
    """
    ts = _io.tune_stats
    log_path = Path(action_log_path) if action_log_path else (
        Path(run_dir) / "00_input" / "action_log.json")
    if not Path(log_path).is_absolute():
        log_path = Path(run_dir) / log_path
    if not log_path.exists():
        return {"status": "absent", "by_param": {}, "reason": "no action_log supplied"}
    try:
        logs = _load_action_logs(log_path)
    except Exception as exc:
        return {"status": "failed", "by_param": {},
                "reason": f"action log unreadable: {exc}"}
    if not logs:
        return {"status": "failed", "by_param": {}, "reason": "no parseable action logs"}
    if ts is None:
        return {"status": "failed", "by_param": {},
                "reason": _io.REUSE_STATUS.get("tune_stats", "tune_stats unavailable")}
    param_by_log = {}
    for log in logs:
        log_id = log.get("action_log_id")
        params = [a.get("parameter") for a in (log.get("actions") or [])
                  if isinstance(a, dict) and a.get("parameter")]
        if log_id:
            param_by_log[str(log_id)] = params
    dead = "unknown" if dead_time is None else str(dead_time)
    errors = []
    for kpi in kpis:
        ns = SimpleNamespace(
            data=str(data_rel), time_col=str(time_col or "t"), group_key=None,
            metric=str(kpi), action_log=str(log_path), dead_time=dead,
            baseline_points=getattr(ts, "DEFAULT_BASELINE_POINTS", 30),
            tau_steps=getattr(ts, "DEFAULT_TAU_STEPS", 3),
            settle_steps=getattr(ts, "DEFAULT_SETTLE_STEPS", 2),
            min_points=getattr(ts, "DEFAULT_MIN_BASELINE_POINTS", 10),
        )
        try:
            ts.attribute(Path(run_dir), ns)
        except SystemExit as exc:
            errors.append(f"{kpi}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"{kpi}: {type(exc).__name__}: {exc}")
    report_dir = Path(run_dir) / "06_experience" / "attribution"
    if not report_dir.is_dir():
        return {"status": "failed" if errors else "not_estimable",
                "by_param": {},
                "reason": "; ".join(errors) or "no attribution reports"}
    by_param = {}
    for report_path in sorted(report_dir.glob("*.json")):
        try:
            report = _io.read_json(report_path)
        except (OSError, ValueError):
            continue
        log_id = str(report.get("action_log_id") or report_path.stem)
        params = param_by_log.get(log_id, [])
        status = report.get("attribution_status")
        effect = report.get("effect") or {}
        ci = effect.get("ci95") if isinstance(effect, dict) else None
        ci_excludes = None
        if isinstance(ci, (list, tuple)) and len(ci) == 2 and all(
                isinstance(v, (int, float)) for v in ci):
            ci_excludes = not (ci[0] <= 0 <= ci[1])
        for param in params:
            by_param.setdefault(str(param), []).append({
                "action_log_id": log_id,
                "metric": report.get("metric"),
                "attribution_status": status,
                "reason_code": report.get("reason_code"),
                "effect": effect.get("delta") if isinstance(effect, dict) else None,
                "ci95": ci,
                "ci_excludes_zero": ci_excludes,
                "evidence_grade": report.get("evidence_grade"),
            })
    status = "used" if by_param else ("failed" if errors else "not_estimable")
    out = {"status": status, "by_param": by_param}
    if errors:
        out["reason"] = "; ".join(errors[:4])
    return out


def _load_action_logs(path):
    """Object / array / JSONL — mirrors tuning-memory's accepted shapes."""
    p = Path(path)
    if p.is_dir():
        logs = []
        for f in sorted(p.glob("*.json")):
            logs.extend(_load_action_logs(f))
        return logs
    text = p.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            if isinstance(data, dict) and data.get("actions"):
                return [data]
            if isinstance(data, dict):
                return [x for x in (data.get("action_logs") or [])
                        if isinstance(x, dict)]
        except ValueError:
            pass
    logs = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("actions"):
            logs.append(obj)
    return logs
