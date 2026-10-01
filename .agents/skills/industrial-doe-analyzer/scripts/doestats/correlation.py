"""Observational-mode correlation analysis with the full anti-spurious chain (C10).

Chain (the ONLY r/p/lag caliber is core_stats — recomputing with np.corrcoef is
forbidden): core_stats.run_correlation_analysis -> anti_spurious.run_anti_spurious_checks
(correlation_result / group_col / time_col MUST be passed — without correlation_result
the outlier/LOO/lag verdicts silently run empty) -> per-pair verdicts + leave-one-
factor-out ΔR² contribution + BH per target family (diverges from the legacy
Bonferroni by design; documented in method_notes).
"""

import numpy as np
import pandas as pd


def _rows_for_core(df):
    """list-of-dicts with NaN -> None (core_stats._safe_float contract)."""
    recs = df.astype(object).to_dict("records")
    return [{k: (None if (isinstance(v, float) and np.isnan(v)) else v)
             for k, v in r.items()} for r in recs]


def _contribution(df, target, predictors):
    """Leave-one-factor-out ΔR² on standardized OLS (C9 observational caliber).

    Returns ({predictor: delta_r2}, r2_full). Early exits return ({}, None) so the
    caller's two-value unpack never breaks on degenerate input.
    """
    cols = [c for c in [target] + predictors if c in df.columns]
    sub = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub) < 10 or not predictors:
        return {}, None
    y = sub[target].to_numpy(dtype=float)
    y = (y - y.mean()) / (y.std() or 1.0)
    Xfull = sub[predictors].to_numpy(dtype=float)
    Xfull = (Xfull - Xfull.mean(0)) / np.where(Xfull.std(0) == 0, 1, Xfull.std(0))
    r2 = lambda X: _r2(X, y)
    r2_full = r2(Xfull)
    out = {}
    for j, f in enumerate(predictors):
        idx = [i for i in range(Xfull.shape[1]) if i != j]
        out[f] = round(r2_full - r2(Xfull[:, idx]), 6)
    return out, r2_full


def _r2(X, y):
    n = X.shape[0]
    Xa = np.column_stack([np.ones(n), X])
    beta, _, _, _ = np.linalg.lstsq(Xa, y, rcond=None)
    resid = y - Xa @ beta
    tss = float(((y - y.mean()) ** 2).sum())
    return 1 - float(resid @ resid) / tss if tss > 0 else 0.0


def analyze_observational(df, run_dir, ctx, idp_scripts):
    """Returns (correlation_report_dict, anti_spurious_validate_report)."""
    import sys

    if str(idp_scripts) not in sys.path:
        sys.path.insert(0, str(idp_scripts))
    from stats import anti_spurious, core_stats

    rows = _rows_for_core(df)
    numeric_cols = [c for c in df.columns
                    if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]
    targets = [r["col"] for r in ctx.get("responses", []) if r["col"] in numeric_cols]
    predictors = [c for c in ctx.get("_predictor_cols", [])
                  if c in numeric_cols and c not in targets]
    if not targets:
        targets = numeric_cols[:3]
    time_col = ctx.get("time_col")
    group_col = ctx.get("group_col")
    max_lag = int(ctx.get("max_lag") or 20)
    alpha = float(ctx.get("alpha") or 0.05)

    corr = core_stats.run_correlation_analysis(
        rows, str(run_dir),
        target_cols=targets, predictor_cols=predictors,
        exclude_cols=set(ctx.get("index_cols") or []) - {time_col},
        time_col=time_col, group_col=group_col,
        max_lag=max_lag, alpha=alpha, data_view_mode="observational_doe")
    val = anti_spurious.run_anti_spurious_checks(
        rows, str(run_dir), correlation_result=corr,
        target_cols=targets, group_col=group_col, time_col=time_col)

    # --- per-pair assembly ---
    outlier_map, loo_map, trend_map, simpson_map = {}, {}, {}, {}
    for c in val.get("outlier_sensitivity", []) or []:
        outlier_map[(c.get("target"), c.get("parameter"))] = c
    for c in val.get("leave_one_out_leverage", []) or []:
        loo_map[(c.get("target"), c.get("parameter"))] = c
    for c in val.get("time_trend_confounding", []) or []:
        trend_map[(c.get("target"), c.get("parameter"))] = c
    for c in val.get("simpson_paradox", []) or []:
        if isinstance(c, dict) and not c.get("_meta"):
            simpson_map[(c.get("target"), c.get("parameter"))] = c

    contrib_by_target = {}
    ta_all = corr.get("target_analysis", {})
    pairs = []
    for target in targets:
        # P0-2: the ΔR² contribution is PER-TARGET — the previous code computed it
        # once for targets[0] and stamped that value onto every target's pairs.
        contrib, r2_full_t = {}, None
        try:
            contrib, r2_full_t = _contribution(df, target, predictors)
        except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
            # narrowed: genuine numeric/structural failures are logged once, never
            # silently treated as "no contribution"
            print(f"[contribution] ΔR² decomposition failed for target={target}: {exc!r}",
                  file=sys.stderr)
        contrib_by_target[target] = (contrib, r2_full_t)
        ta = ta_all.get(target, {})
        family = []
        for param, pc in (ta.get("pearson_correlations") or {}).items():
            if not isinstance(pc, dict):
                continue
            r = pc.get("r")
            if r is None:
                continue
            best = (ta.get("best_lags") or {}).get(param) or {}
            detrended = (ta.get("detrended_correlations") or {}).get(param) or {}
            det_r = detrended.get("detrended_r")
            if detrended.get("trend_confounded") is not None:
                trend_confounded = bool(detrended["trend_confounded"])
            else:
                trend_confounded = bool(det_r is not None
                                        and abs(r) - abs(det_r) >= 0.3)
            notes = []
            verdict_codes = []
            oc = outlier_map.get((target, param))
            if oc:
                if oc.get("outlier_driven"):
                    verdict_codes.append("FAIL")
                    notes.append("correlation is outlier-driven")
                elif oc.get("r_change_pct", 0) and abs(oc.get("r_change_pct", 0)) >= 15:
                    verdict_codes.append("CAUTION")
            lc = loo_map.get((target, param))
            if lc and lc.get("loo_unstable"):
                verdict_codes.append("FAIL")
                notes.append("leave-one-out leverage unstable")
            tc = trend_map.get((target, param))
            if tc or trend_confounded:
                verdict_codes.append("CAUTION")
                notes.append("shared time trend confounds the raw correlation")
            sc = simpson_map.get((target, param))
            if sc and (sc.get("simpson_paradox") or sc.get("direction_reversal")):
                verdict_codes.append("FAIL")
                notes.append("Simpson paradox / direction reversal across strata")
            lag_ok = None
            if best:
                lag_ok = bool(param in (ta.get("lag_window_consistency") or {}))
            verdict = "FAIL" if "FAIL" in verdict_codes else (
                "CAUTION" if "CAUTION" in verdict_codes else "PASS")
            family.append({
                "target": target, "parameter": param,
                "r": round(float(r), 4),
                "p_value": pc.get("p"), "n": int(pc.get("n") or 0),
                "best_lag": best.get("lag"),
                "best_lag_r": round(float(best["r"]), 4) if best.get("r") is not None else None,
                "lag_window_consistent": lag_ok,
                "detrended_r": round(float(det_r), 4) if det_r is not None else None,
                "trend_confounded": trend_confounded,
                "contribution_delta_r2": contrib.get(param),
                "verdicts": {
                    "outlier_sensitivity": (oc.get("severity") if oc else None),
                    "loo_leverage": (bool(lc and lc.get("loo_unstable")) if lc else None),
                    "time_trend": (tc.get("severity") if tc else
                                   ("CONFOUNDED" if trend_confounded else None)),
                    "simpson": (sc.get("paradox_type") if sc else None),
                },
                "anti_spurious_verdict": verdict,
                "evidence_level": "L3" if (verdict == "PASS" and abs(r) >= 0.3) else "L4",
                "notes": notes,
            })
        qs = _bh([p["p_value"] for p in family])
        for p, q in zip(family, qs):
            p["q_value_bh"] = q
        pairs.extend(family)

    top = sorted(
        ({"response": t, "factor": f, "delta_r2": d, "r_full_model": _rr(r2t)}
         for t, (c, r2t) in contrib_by_target.items() for f, d in (c or {}).items()),
        key=lambda x: x["delta_r2"], reverse=True)[:10]

    sig = sum(1 for p in pairs if (p.get("q_value_bh") is not None and p["q_value_bh"] < 0.05))
    report = {
        "generated_at": _now(),
        "mode": "observational",
        "n_rows": int(len(df)),
        "time_col": time_col,
        "group_col": group_col,
        "sorting_validation": corr.get("sorting_validation"),
        "pairs": pairs,
        "top_contributors": top,
        "multiple_testing": {
            "method": "BH", "n_families": len(targets),
            "total_tests": len(pairs), "total_significant_q05": sig,
        },
        "anti_spurious_summary": {
            "overall_validity": val.get("overall_validity"),
            "summary": val.get("summary"),
            "lag_warning": val.get("lag_warning"),
        },
    }
    return report, val


def _bh(pvals):
    from ._stats_util import bh_adjust
    return bh_adjust(pvals)


def _rr(v):
    return round(float(v), 6) if v is not None else None


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
