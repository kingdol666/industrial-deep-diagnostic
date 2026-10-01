"""Observational-mode stability & capability (C6 honest-caliber rules).

- Pp/Ppk from the OVERALL sigma (always reported when specs exist).
- Cp/Cpk from MR-bar/d2 (d2 = 1.128) ONLY when the data is time-ordered;
  labeled "Cpk(within, MRbar/d2)". Non-normal -> indicative + quantile index Cnp.
- n_eff from lag-1 autocorrelation under AR(1).
- Steady-state labeling reuses the industrial-data-processor detector IN-PROCESS
  (detect_by_variance_fast / detect_change_points_fast / detect_drift_ramps_fast /
  fuse_regimes) with an explicit window in ROWS — the detector's CLI default of
  --window-minutes assumes minute-level timestamps and is deliberately avoided.
- Change points per response come from the reused anti_spurious PELT detector.
"""

import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

from ._stats_util import effective_n, lag1_autocorr

D2_MR = 1.128  # MR-bar/d2 for individuals charts


def analyze_stability(df, run_dir, ctx, idp_scripts):
    """Returns stability_report_dict."""
    time_col = ctx.get("time_col")
    numeric_cols = [c for c in df.columns
                    if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]
    targets = [r["col"] for r in ctx.get("responses", []) if r["col"] in numeric_cols]
    if not targets:
        targets = numeric_cols[:3]

    regime_summary = None
    steady_indices = None
    if time_col and time_col in df.columns:
        regime_summary, steady_indices = _regime_labels(df, ctx, idp_scripts)

    capability = [_capability(df, t, ctx) for t in targets]

    change_points = []
    detector_note = None
    try:
        if str(idp_scripts) not in sys.path:
            sys.path.insert(0, str(idp_scripts))
        from stats import anti_spurious
        for t in targets:
            vals = pd.to_numeric(df[t], errors="coerce").tolist()
            cp = anti_spurious._detect_change_points(vals)
            if cp and cp.get("n_changes", 0) > 0:
                change_points.append({
                    "response": t,
                    "positions": [int(p) for p in cp.get("change_points", [])],
                    "detail": {"n_segments": cp.get("n_segments"),
                               "n_changes": cp.get("n_changes")},
                })
    except Exception as exc:  # detector unavailable -> report honestly, don't block
        detector_note = f"change-point detection unavailable: {exc}"

    segments = _steady_segments(df, steady_indices, targets, ctx)

    drift_flags = []
    for cp in change_points:
        if cp["positions"] and segments and all(cp["positions"][0] > seg["end"] for seg in segments):
            drift_flags.append({
                "code": "DRIFT_AFTER_LAST_STEADY",
                "message": (f"响应 {cp['response']} 的变点位于最后一个稳态段之后 — "
                            f"过程可能正在漂移出已分析的工况窗"),
                "response": cp["response"],
                "severity": "warn",
            })
    if regime_summary and regime_summary.get("error"):
        drift_flags.append({"code": "REGIME_DETECTOR_UNAVAILABLE",
                            "message": regime_summary["error"], "severity": "info"})
    if detector_note:
        drift_flags.append({"code": "CP_DETECTOR_UNAVAILABLE",
                            "message": detector_note, "severity": "info"})

    return {
        "generated_at": _now(),
        "n_rows": int(len(df)),
        "time_col": time_col,
        "capability": capability,
        "steady_segments": segments,
        "change_points": change_points,
        "drift_flags": drift_flags,
        "regime_summary": regime_summary,
    }


def _regime_labels(df, ctx, idp_scripts):
    """In-process reuse of the production-regime detector (row-window, fast path)."""
    try:
        if str(idp_scripts) not in sys.path:
            sys.path.insert(0, str(idp_scripts))
        import production_regime_detector as prd

        wanted = {ctx.get("time_col"), ctx.get("group_col")}
        wanted |= {r.get("col") for r in ctx.get("responses", [])}
        wanted |= set(ctx.get("_predictor_cols") or [])
        keep = [c for c in df.columns if c in wanted and c]
        sub = df[keep]
        rows = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v)
                 for k, v in rec.items()} for rec in sub.to_dict("records")]
        numeric_cols = prd._numeric_columns(rows)
        n = len(rows)
        window = min(max(20, n // 50), max(n // 3, 5))
        col_arrays = prd._col_arrays(rows, numeric_cols)
        variance_scores, _param_stats = prd.detect_by_variance_fast(col_arrays, window)
        change_points, _cp_params = prd.detect_change_points_fast(col_arrays, window)
        ramp_scores, _ramp_params = prd.detect_drift_ramps_fast(col_arrays, window, n)
        labels, _meta, _abnormal = prd.fuse_regimes(
            variance_scores, change_points, ramp_scores, n, window=window)
        steady = [i for i, lab in enumerate(labels) if lab == "steady"]
        dist = {}
        for lab in labels:
            dist[lab] = dist.get(lab, 0) + 1
        summary = {
            "method": "production_regime_detector (in-process, fast path)",
            "window_rows": window,
            "total_rows": n,
            "steady_state_ratio": round(len(steady) / n, 4) if n else 0.0,
            "regime_distribution": {k: {"count": v, "pct": round(v / n * 100, 2)}
                                    for k, v in dist.items()},
        }
        return summary, steady
    except Exception as exc:
        return {"error": f"regime detector failed: {exc}"}, None


def _steady_segments(df, steady_indices, targets, ctx):
    if not steady_indices:
        return []
    idx = sorted(int(i) for i in steady_indices)
    segments = []
    start = prev = idx[0]
    for i in idx[1:] + [None]:
        if i is not None and i == prev + 1:
            prev = i
            continue
        seg_rows = df.iloc[start:prev + 1]
        means = {}
        for t in targets:
            vals = pd.to_numeric(seg_rows[t], errors="coerce").dropna()
            if len(vals):
                means[t] = round(float(vals.mean()), 6)
        segments.append({
            "start": start, "end": prev, "n_rows": prev - start + 1,
            "response_means": means, "score": None,
            "selected_for_windows": False,
        })
        if i is not None:
            start = prev = i
    _score_segments(segments, df, targets, ctx)
    segments.sort(key=lambda s: s["score"] if s["score"] is not None else -1e18,
                  reverse=True)
    for seg in segments[:3]:
        seg["selected_for_windows"] = True
    segments.sort(key=lambda s: s["start"])
    return segments


def _score_segments(segments, df, targets, ctx):
    """W6 score: segment Cpk when specs exist, else goal-direction mean."""
    for seg in segments:
        scores = []
        for r in ctx.get("responses", []):
            t = r["col"]
            if t not in df.columns:
                continue
            vals = pd.to_numeric(df.iloc[seg["start"]:seg["end"] + 1][t],
                                 errors="coerce").dropna()
            if len(vals) < 3:
                continue
            s = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            m = float(vals.mean())
            lsl, usl = r.get("lsl"), r.get("usl")
            if lsl is not None and usl is not None and s > 0:
                scores.append(min((usl - m) / 3 / s, (m - lsl) / 3 / s))
            elif r.get("goal") == "maximize":
                scores.append(m)
            elif r.get("goal") == "minimize":
                scores.append(-m)
        seg["score"] = round(float(np.mean(scores)), 6) if scores else None


def _capability(df, response, ctx):
    x = pd.to_numeric(df[response], errors="coerce").dropna().astype(float)
    spec = next((r for r in ctx.get("responses", []) if r["col"] == response), {})
    lsl, usl, target = spec.get("lsl"), spec.get("usl"), spec.get("target")
    n = int(x.size)
    mean = float(x.mean()) if n else float("nan")
    std_overall = float(x.std(ddof=1)) if n > 1 else None
    time_col = ctx.get("time_col")
    time_ordered = bool(time_col and time_col in df.columns)

    sigma_within = None
    if time_ordered and n >= 3:
        diffs = x.diff().abs().dropna()
        mr_bar = float(diffs.mean())
        if mr_bar > 0:
            sigma_within = mr_bar / D2_MR

    rho = lag1_autocorr(x.to_numpy()) if time_ordered else None
    n_eff = effective_n(n, rho) if rho is not None else None

    skew = float(sps.skew(x)) if n >= 3 else None
    kurt = float(sps.kurtosis(x)) if n >= 4 else None
    ad_stat = ad_crit5 = None
    try:
        if 4 < n <= 100000:
            ad = sps.anderson(x, dist="norm")
            ad_stat = round(float(ad.statistic), 4)
            ad_crit5 = round(float(ad.critical_values[2]), 4)  # 5% level
    except Exception:
        pass
    normal = bool(ad_stat is not None and ad_crit5 is not None and ad_stat < ad_crit5
                  and abs(skew or 0) < 1.0)

    out = {
        "response": response, "n": n,
        "mean": round(mean, 6) if n else None,
        "std_overall": round(std_overall, 6) if std_overall is not None else None,
        "sigma_within_mr": round(sigma_within, 6) if sigma_within else None,
        "has_specs": lsl is not None or usl is not None,
        "lsl": lsl, "usl": usl, "target": target,
        "cp": None, "cpk": None, "cpk_label": None,
        "pp": None, "ppk": None, "cnp": None,
        "normality": {"skew": round(skew, 4) if skew is not None else None,
                      "excess_kurtosis": round(kurt, 4) if kurt is not None else None,
                      "ad_statistic": ad_stat, "ad_critical_5pct": ad_crit5,
                      "normal": normal},
        "autocorr_lag1": round(rho, 4) if rho is not None else None,
        "n_eff": n_eff,
        "note": None,
    }

    if not (lsl is not None or usl is not None):
        return out
    if not std_overall or std_overall <= 0:
        out["note"] = "zero variance — capability undefined"
        return out

    # overall-sigma performance indices (always honest-labeled)
    if lsl is not None and usl is not None:
        out["pp"] = round((usl - lsl) / (6 * std_overall), 6)
    ppk_sides = []
    if usl is not None:
        ppk_sides.append((usl - mean) / (3 * std_overall))
    if lsl is not None:
        ppk_sides.append((mean - lsl) / (3 * std_overall))
    out["ppk"] = round(min(ppk_sides), 6) if ppk_sides else None

    # within-sigma capability (Cp/Cpk) — only meaningful time-ordered
    if sigma_within and sigma_within > 0:
        if lsl is not None and usl is not None:
            out["cp"] = round((usl - lsl) / (6 * sigma_within), 6)
        sides = []
        if usl is not None:
            sides.append((usl - mean) / (3 * sigma_within))
        if lsl is not None:
            sides.append((mean - lsl) / (3 * sigma_within))
        out["cpk"] = round(min(sides), 6) if sides else None
        out["cpk_label"] = "Cpk(within, MRbar/d2)"
        if not normal:
            out["cpk_label"] = "Cpk(within, MRbar/d2) — INDICATIVE (non-normal data)"
            out["note"] = "非正态分布：Cpk 仅作指示值，请以 Cnp/分位数指数与原始分布图为准"

    if not normal and lsl is not None and usl is not None:
        p_lo, p_hi = np.percentile(x, [0.135, 99.865])
        if p_hi - p_lo > 0:
            out["cnp"] = round((usl - lsl) / (p_hi - p_lo), 4)
    if n_eff and n_eff < 0.5 * n:
        out["note"] = (out["note"] or "") + \
            f" | 正自相关 (rho={rho}): 有效样本量 {n_eff}/{n}，指标精度低于表面 n"
    return out


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
