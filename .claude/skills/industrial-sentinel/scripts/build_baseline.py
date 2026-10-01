#!/usr/bin/env python
"""build_baseline.py — watch_baseline.json builder for industrial-sentinel.

Inputs
  --history-csv PATH   historical production data (CSV/TSV/Parquet), the sole
                       statistical source for parameter stores
  --doe-run-dir DIR    optional doe-analyzer run directory; its
                       conclusions/recommendations.json and
                       02_analysis/stability_report.json are copied into the
                       baseline FIELD BY FIELD (verbatim, diff-assertable —
                       AC A7). No value is recomputed from those files.

Statistical store per group / parameter (steady rows only, regime-filtered):
  center (mean), sigma_within_mr (MRbar/1.128), sigma_overall, median, MAD,
  q10, q90, cv, variance_ratio_baseline_std; plus the correlation matrix with
  its Cholesky factor (flat, row-major) over the parameter set.

A group needs >= 100 steady rows (closedloop_enums sentinel.baseline.
min_steady_rows_per_group) to be admitted; groups below the floor are
skipped with a warning (they will surface as UNSEEN_GROUP at watch time).

Exit codes: 0 ok · 2 bad input (unreadable data / no valid group).
Zero LLM, zero network, numpy/scipy/pandas only. No raw open() anywhere.
"""

import argparse
import copy
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sentinelcore import BASELINE_CONTRACT_VERSION, BASELINE_DEFAULTS, SCRIPT_VERSION
from sentinelcore import _io, regime_map, spc


def _corr_store(arrays, cols):
    """Correlation matrix + Cholesky over steady rows; L1 degrade on failure."""
    mat = np.column_stack([arrays[c] for c in cols])
    ok = np.isfinite(mat).all(axis=1)
    if ok.sum() < max(3, len(cols) + 2):
        return None
    sub = mat[ok]
    corr = np.corrcoef(sub, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    kept = list(range(len(cols)))
    for _ in range(len(kept)):
        try:
            L = np.linalg.cholesky(corr[np.ix_(kept, kept)])
            break
        except np.linalg.LinAlgError:
            if len(kept) <= 2:
                return {"cols": [cols[i] for i in kept],
                        "corr_matrix_flat": [float(x) for x in
                                             corr[np.ix_(kept, kept)].ravel()],
                        "cholesky_lower": None}
            subc = corr[np.ix_(kept, kept)]
            drop_local = robust_drop(subc)
            dropped = kept[drop_local]
            kept = [i for i in kept if i != dropped]
            L = None
    else:
        L = None
    if L is None:
        return None
    final = corr[np.ix_(kept, kept)]
    return {"cols": [cols[i] for i in kept],
            "corr_matrix_flat": [float(x) for x in final.ravel()],
            "cholesky_lower": [float(x) for x in L.ravel()]}


def robust_drop(corr):
    """Column index with the most |r|>0.98 partners (tie: larger sum|r|)."""
    n = corr.shape[0]
    counts = np.zeros(n, dtype=int)
    for i in range(n):
        for j in range(n):
            if i != j and abs(corr[i, j]) > 0.98:
                counts[i] += 1
    sums = np.nansum(np.abs(corr), axis=1)
    best = 0
    for i in range(n):
        if counts[i] > counts[best] or (counts[i] == counts[best] and sums[i] > sums[best]):
            best = i
    return int(best)


def _percentile(v, q):
    return float(np.percentile(v, q)) if v.size else None


def build_group_store(arrays, cols, time_hours, thresholds=None):
    """One group's parameter/correlation/regime store from raw arrays."""
    n = len(next(iter(arrays.values()))) if arrays else 0
    z_mean = None
    allmat = np.column_stack([arrays[c] for c in cols]) if cols else np.zeros((n, 0))
    if cols and n:
        mu = np.nanmean(allmat, axis=0)
        sd = np.nanstd(allmat, axis=0, ddof=1)
        sd_safe = np.where((sd > 0) & np.isfinite(sd), sd, np.inf)
        z = (allmat - mu) / sd_safe
        with np.errstate(invalid="ignore"):
            z_mean = np.nanmedian(z, axis=1)  # spike-immune (see method_notes §3)

    det = regime_map.detect(arrays, z_mean=z_mean, thresholds=thresholds)
    labels = det["labels"]
    steady = np.array([lab == "steady" for lab in labels], dtype=bool)
    n_steady = int(steady.sum())

    parameters = {}
    for c in cols:
        v = arrays[c]
        vs = v[steady & np.isfinite(v)]
        vr = v[np.isfinite(v)]
        center = float(np.mean(vs)) if vs.size else None
        sigma_mr = spc.sigma_within_mr(vs) if vs.size >= 2 else spc.sigma_within_mr(vr)
        sigma_all = float(np.std(vs, ddof=1)) if vs.size >= 2 else (
            float(np.std(vr, ddof=1)) if vr.size >= 2 else None)
        med = float(np.median(vs)) if vs.size else None
        mad = float(np.median(np.abs(vs - med))) if vs.size else None
        mean_abs = abs(center) if center is not None else None
        parameters[c] = {
            "center": center,
            "sigma_within_mr": sigma_mr,
            "sigma_overall": sigma_all,
            "median": med,
            "mad": mad,
            "q10": _percentile(vs, 10),
            "q90": _percentile(vs, 90),
            "cv": (float(np.std(vs, ddof=1) / mean_abs)) if (vs.size and mean_abs) else None,
            "variance_ratio_baseline_std": sigma_all,
        }

    corr = _corr_store({c: arrays[c][steady] for c in cols}, cols) if n_steady else None

    time_span = None
    if time_hours is not None and n:
        th = np.asarray(time_hours, dtype=float)
        th = th[np.isfinite(th)]
        if th.size >= 2:
            time_span = f"{float(th[0]):.3f}h .. {float(th[-1]):.3f}h (relative)"

    store = {
        "parameters": parameters,
        "indicators": {},
        "operating_windows": [],
        "applicability_domain": None,
        "correlation": corr,
        "regime": {
            "variance_threshold": float(regime_map.DEFAULTS["variance_threshold"]),
            "ramp_threshold": float(regime_map.DEFAULTS["ramp_threshold"]),
            "window_rows": int(regime_map.DEFAULTS["window_rows"]),
            "known_change_points": sorted(int(c) for c in det["change_points"]),
        },
        "validity": {
            "n_steady_rows": n_steady,
            "steady_ratio": (n_steady / n) if n else None,
            "time_span": time_span,
            "self_baseline_ttl_hours": None,
            "invalidation_conditions": [],
        },
        "_debug_labels": regime_map.label_counts(labels),
    }
    return store


def load_doe_artifacts(doe_run_dir):
    """Read doe-analyzer artifacts; returns (recs, stability) or (None, None)."""
    run_dir = _io._contained(doe_run_dir)
    recs_path = run_dir / "conclusions" / "recommendations.json"
    stab_path = run_dir / "02_analysis" / "stability_report.json"
    recs = _io.read_json(recs_path) if recs_path.exists() else None
    stab = _io.read_json(stab_path) if stab_path.exists() else None
    if recs is None and stab is None:
        raise FileNotFoundError(f"no doe-analyzer artifacts under {run_dir}")
    return recs, stab


def apply_doe_artifacts(store, recs, stab):
    """Verbatim field-by-field copy (AC A7) — never recompute from these."""
    if recs is not None:
        store["operating_windows"] = copy.deepcopy(recs.get("operating_windows") or [])
        specs = recs.get("response_specs") or {}
        for resp, s in specs.items():
            store["indicators"][resp] = {
                "lsl": s.get("lsl"), "usl": s.get("usl"),
                "target": s.get("target"), "goal": s.get("goal")}
        store["applicability_domain"] = copy.deepcopy(recs.get("applicability_domain"))
        store["validity"]["invalidation_conditions"] = list(
            recs.get("invalidation_conditions") or [])
    if stab is not None:
        positions = set()
        for cp in stab.get("change_points") or []:
            for p in cp.get("positions") or []:
                positions.add(int(p))
        known = set(store["regime"]["known_change_points"]) | positions
        store["regime"]["known_change_points"] = sorted(known)


def main(argv=None):
    ap = argparse.ArgumentParser(description="industrial-sentinel baseline builder")
    ap.add_argument("--history-csv", required=True)
    ap.add_argument("--doe-run-dir", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--group-col", default=None)
    ap.add_argument("--parameters", default=None,
                    help="comma-separated parameter columns (default: auto)")
    ap.add_argument("--indicators", default=None,
                    help="comma-separated indicator columns (spec/quality)")
    ap.add_argument("--window-rows", type=int, default=None)
    args = ap.parse_args(argv)

    try:
        history_path = _io._contained(args.history_csv)
        df = _io.load_table(history_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[build_baseline] bad input: {exc}")
        return 2

    time_col, group_col = _io.identify_columns(df, args.time_col, args.group_col)
    exclude = [time_col, group_col]
    if args.parameters:
        cols = [c.strip() for c in args.parameters.split(",") if c.strip()]
    else:
        cols = _io.numeric_columns(df, exclude)
    if not cols:
        print("[build_baseline] bad input: no usable numeric parameter columns")
        return 2

    recs = stab = None
    if args.doe_run_dir:
        try:
            recs, stab = load_doe_artifacts(args.doe_run_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"[build_baseline] bad input: {exc}")
            return 2

    groups = _io.split_groups(df, group_col)
    baseline_groups = {}
    skipped = []
    for gname, sub in groups.items():
        arrays = _io.to_arrays(sub, cols)
        time_hours = _io.hours_axis(sub, time_col) if time_col else None
        store = build_group_store(arrays, cols, time_hours)
        if args.doe_run_dir and recs is not None:
            apply_doe_artifacts(store, recs, stab)
        store.pop("_debug_labels", None)
        floor = BASELINE_DEFAULTS["min_steady_rows_per_group"]
        if store["validity"]["n_steady_rows"] < floor:
            skipped.append(f"{gname}({store['validity']['n_steady_rows']}<{floor})")
            continue
        baseline_groups[gname] = store

    if not baseline_groups:
        print("[build_baseline] bad input: no group reached "
              f"{BASELINE_DEFAULTS['min_steady_rows_per_group']} steady rows")
        return 2
    if skipped:
        print(f"[build_baseline] skipped groups below steady-row floor: {', '.join(skipped)}")

    out_path = (Path(args.out) if args.out
                else history_path.parent / "watch_baseline.json")
    payload = {
        "contract_version": BASELINE_CONTRACT_VERSION,
        "baseline_version": f"v{SCRIPT_VERSION}",
        "generated_at": _io.now_iso(),
        "generated_from": {
            "doe_recommendations_path": (str(_io._contained(args.doe_run_dir) /
                                              "conclusions" / "recommendations.json")
                                         if args.doe_run_dir and recs is not None else None),
            "doe_run_dir": str(_io._contained(args.doe_run_dir)) if args.doe_run_dir else None,
            "history_csv_sha256": _io.sha256_file(history_path),
            "recommendations_contract_version": (recs or {}).get("contract_version")
            if recs is not None else None,
        },
        "global": {
            "time_col": time_col,
            "group_col": group_col,
            "numeric_columns": list(cols),
            "fast_path_min_rows": int(BASELINE_DEFAULTS["fast_path_min_rows"]),
            "window_rows": args.window_rows,
        },
        "groups": baseline_groups,
        "state": None,
        "provenance": {
            "input_sha256": _io.sha256_file(history_path),
            "script_version": SCRIPT_VERSION,
            "authored_by": "script",
        },
    }
    _io.write_json(out_path, payload)
    print(f"[build_baseline] wrote {out_path} "
          f"(groups: {', '.join(sorted(baseline_groups))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
