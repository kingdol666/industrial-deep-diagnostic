#!/usr/bin/env python
"""tune_stats.py — deterministic action->outcome attribution (zero LLM).

Pipeline per action log (bundle = attribution unit):
  1. segment placement (segment_selector.select_segments)
  2. Welch before/after delta with AR(1)-corrected effective n entering the test
     (reduces EXACTLY to doestats.welch_delta_ci when n_eff == n)
  3. stratified_before_after_delta when --group-key is given — per-layer welch,
     layers with n_layer < 20 skipped (counted, skipped=true), weight n/n_tot,
     SE variance synthesis — formula-aligned with doe-analyzer windows.py
     _stratified_tercile_delta (L474-500)
  4. lightweight anti-spurious chain:
       trend   — pooled OLS detrend over baseline+effect rows; |delta| shrink
                 >= 0.3 after detrending -> CAUTION; detrended sign flip -> FAIL
                 (-> status direction_uncertain)
       outlier — leave-one-out over both segments; sign flip after removing the
                 single most influential point -> FAIL -> not_estimable/outlier_driven
  5. honest state machine estimable|direction_uncertain|truncated|not_estimable
     with reason_code; effect=null when not_estimable (never fabricate)

Evidence grade (advisory strength only — dispatch policy is AWS-side):
  E0 = truncated | confound_detected | attribution_compromised | direction_uncertain
  E1 = single estimable attribution (CI may cross 0)
  (E2/E3 emerge only through corroboration in the local experience store.)

Confound / overlap semantics:
  same-parameter action inside the effect window -> attribution_compromised
  different-parameter action inside the effect window, or action_log
  attribution_confounds non-empty               -> confound_detected (downgrade)

Writes 06_experience/attribution/{action_log_id}.json per action log.
File-IO discipline: pathlib only, every path through `_contained()`; no raw open().
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[2]
REPO_ROOT_NORM = os.path.normpath(os.path.abspath(str(REPO_ROOT)))
DOE_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(DOE_SCRIPTS))
sys.path.insert(0, str(SHARED_SCRIPTS))
from doestats._stats_util import effective_n, lag1_autocorr, welch_delta_ci  # noqa: E402,F401
from closedloop_common.enums import (  # noqa: E402  — the ONLY enum literal source
    ATTRIBUTION_STATUS, EVIDENCE_GRADES, NOT_ESTIMABLE_REASONS,
)
from segment_selector import (  # noqa: E402
    DEFAULT_BASELINE_POINTS, DEFAULT_MIN_BASELINE_POINTS, DEFAULT_SETTLE_STEPS,
    DEFAULT_TAU_STEPS, SCRIPT_VERSION as SEG_VERSION,  # noqa: F401
    _contained, _load_dataframe, _write_json, load_action_logs, next_action_rows,
    parse_ts, select_segments, ts_to_row,
)

SCRIPT_VERSION = "tune_stats/1.0"
STRAT_MIN_LAYER = 20          # aligned with windows.py: m.sum() < 20 skip
TREND_SHRINK_CAUTION = 0.3    # |delta| shrink >= 0.3 after detrending -> CAUTION
REPORT_DIR = "06_experience/attribution"


# ------------------------------------------------------------------- welch

def welch_delta_ci_neff(x_hi, x_lo, rho_hi=None, rho_lo=None, conf=0.95):
    """Delta = mean(x_hi) - mean(x_lo) with Welch t CI where the AR(1)-adjusted
    effective sample size enters the test: var(mean) = s^2 / n_eff.

    When n_eff == n (rho None or |rho| >= 0.99 per doestats.effective_n) this is
    numerically IDENTICAL to doestats.welch_delta_ci (B2 contract, 1e-9).
    Returns (delta, lo, hi, n_eff_hi, n_eff_lo) or None when a side is too small.
    """
    x_hi = np.asarray(x_hi, dtype=float)
    x_lo = np.asarray(x_lo, dtype=float)
    x_hi = x_hi[~np.isnan(x_hi)]
    x_lo = x_lo[~np.isnan(x_lo)]
    if x_hi.size < 2 or x_lo.size < 2:
        return None
    n_eff_hi = max(int(effective_n(int(x_hi.size), rho_hi)), 2) if rho_hi is not None else int(x_hi.size)
    n_eff_lo = max(int(effective_n(int(x_lo.size), rho_lo)), 2) if rho_lo is not None else int(x_lo.size)
    v_hi = x_hi.var(ddof=1) / n_eff_hi
    v_lo = x_lo.var(ddof=1) / n_eff_lo
    se = float(np.sqrt(v_hi + v_lo))
    if se <= 0:
        return None
    delta = float(x_hi.mean() - x_lo.mean())
    df = (v_hi + v_lo) ** 2 / max(
        (v_hi ** 2) / (n_eff_hi - 1) + (v_lo ** 2) / (n_eff_lo - 1), 1e-300)
    t_crit = float(sps.t.ppf(0.5 + conf / 2.0, df))
    return delta, delta - t_crit * se, delta + t_crit * se, int(n_eff_hi), int(n_eff_lo)


def stratified_before_after_delta(before, after, g_before, g_after,
                                  rho_before=None, rho_after=None):
    """Stratified before/after delta — formula aligned with doe-analyzer
    windows.py `_stratified_tercile_delta` (L474-500):
      per-layer welch -> layers with n_layer < 20 skipped (counted, skipped=true)
      weight w = n_layer / n_tot (n_layer = before+after rows of the layer)
      delta = sum(w * delta_layer)
      se    = sqrt(sum(w^2 * ((ci_hi - ci_lo) / (2*1.96))^2))  (or 1e-12)
      ci    = delta ± 1.96*se
    Returns {"delta", "ci95", "layers": [{group, n, delta, ci95, skipped}]}.
    """
    g_before = np.asarray([str(g) for g in g_before])
    g_after = np.asarray([str(g) for g in g_after])
    per, skipped = [], []
    for g in sorted(set(g_before.tolist()) | set(g_after.tolist())):
        m_b = g_before == g
        m_a = g_after == g
        n_layer = int(m_b.sum() + m_a.sum())
        entry = {"group": g, "n": n_layer, "delta": None, "ci95": None, "skipped": True}
        if n_layer < STRAT_MIN_LAYER:
            skipped.append(entry)
            continue
        r = welch_delta_ci_neff(after[m_a], before[m_b], rho_after, rho_before)
        if r is None:
            skipped.append(entry)
            continue
        d, lo, hi, _, _ = r
        entry.update(delta=float(d), ci95=[float(lo), float(hi)], skipped=False)
        per.append((n_layer, entry))
    layers_out = sorted([e for _, e in per] + skipped, key=lambda e: e["group"])
    if not per:
        return {"delta": None, "ci95": None, "layers": layers_out}
    n_tot = sum(n for n, _ in per)
    delta = sum(n / n_tot * e["delta"] for n, e in per)
    se = float(np.sqrt(sum((n / n_tot) ** 2 *
                           ((e["ci95"][1] - e["ci95"][0]) / (2 * 1.96)) ** 2
                           for n, e in per))) or 1e-12
    return {"delta": float(delta), "ci95": [float(delta - 1.96 * se), float(delta + 1.96 * se)],
            "layers": layers_out}


# ------------------------------------------------------- anti-spurious chain

def detrended_delta(series, base_rows, eff_rows):
    """Pooled OLS detrend over baseline+effect rows, then delta of residual
    segment means. Returns the detrended delta (None when not computable)."""
    base_rows = np.asarray(base_rows, dtype=int)
    eff_rows = np.asarray(eff_rows, dtype=int)
    raw_rows = np.concatenate([base_rows, eff_rows])
    y = np.asarray(series[raw_rows], dtype=float)
    ok = ~np.isnan(y)
    raw_rows, y = raw_rows[ok], y[ok]
    if y.size < 4 or base_rows.size == 0 or eff_rows.size == 0:
        return None
    X = np.column_stack([np.ones(y.size), raw_rows.astype(float)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    base_mask = np.isin(raw_rows, base_rows)
    eff_mask = np.isin(raw_rows, eff_rows)
    if base_mask.sum() < 1 or eff_mask.sum() < 1:
        return None
    return float(resid[eff_mask].mean() - resid[base_mask].mean())


def trend_check(series, base_rows, eff_rows, delta_raw):
    """Returns (verdict, delta_detrended). CAUTION when |delta| shrinks >= 0.3
    after detrending; FAIL when the detrended delta flips sign."""
    d_dt = detrended_delta(series, base_rows, eff_rows)
    if d_dt is None or not delta_raw:
        return "PASS", d_dt
    if np.sign(d_dt) != np.sign(delta_raw):
        return "FAIL", d_dt
    shrink = 1.0 - abs(d_dt) / abs(delta_raw)
    if shrink >= TREND_SHRINK_CAUTION:
        return "CAUTION", d_dt
    return "PASS", d_dt


def outlier_check(before, after, rho_b, rho_a):
    """Leave-one-out over both segments: remove the single most influential
    point (largest |delta change|) — if the delta flips sign -> FAIL."""
    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)
    full = welch_delta_ci_neff(after, before, rho_a, rho_b)
    if full is None:
        return "PASS", None
    d_full = full[0]
    worst_shift, worst_delta = -1.0, d_full
    for is_before, arr in ((True, before), (False, after)):
        for i in range(arr.size):
            if is_before:
                b2, a2 = np.delete(before, i), after
            else:
                b2, a2 = before, np.delete(after, i)
            r = welch_delta_ci_neff(a2, b2, rho_a, rho_b)
            if r is None:
                # the removal degenerated a group (constant series): the observed
                # delta hinged entirely on this point -> flip-to-zero candidate
                shift, d_excl = abs(d_full), 0.0
            else:
                shift, d_excl = abs(r[0] - d_full), r[0]
            if shift > worst_shift:
                worst_shift, worst_delta = shift, d_excl
    if d_full != 0 and np.sign(worst_delta) != np.sign(d_full):
        return "FAIL", float(worst_delta)
    return "PASS", float(worst_delta)


# ------------------------------------------------------------------ report

def _ci_excludes_zero(ci):
    if not ci or len(ci) != 2:
        return False
    return ci[0] > 0 or ci[1] < 0


def _empty_segments():
    return {"baseline": {"row_range": None, "n": 0, "n_eff": None, "lag1_autocorr": None},
            "effect": {"row_range": None, "n": 0, "n_eff": None,
                       "lag1_autocorr": None, "truncated_by": None},
            "dead_time_used": None, "boundaries": []}


def attribute_action_log(log_id, log, logs, cur_index, seg, args, series, metric_missing,
                         group_vals=None):
    """Fill the attribution report for one action log (bundle = unit)."""
    out = {
        "report_version": "1.0",
        "action_log_id": log_id,
        "bundle_scope": bool((log.get("bundled_action") or {}).get("is_bundle", False)),
        "attribution_status": "not_estimable",
        "reason_code": None,
        "metric": (log.get("outcome") or {}).get("metric") if metric_missing else args.metric,
        "segments": {
            "baseline": seg["baseline"],
            "effect": seg["effect"],
            "dead_time_used": seg["dead_time_used"],
        },
        "effect": None,
        "confound_detected": False,
        "attribution_compromised": False,
        "anti_spurious": {"trend_check": None, "outlier_check": None},
        "evidence_grade": "E0",
        "provenance": {"script_version": SCRIPT_VERSION, "authored_by": "script"},
    }

    if metric_missing:
        out["metric"] = None
        out["reason_code"] = "metric_missing"
        return out
    if str(args.dead_time).lower() == "unknown":
        out["reason_code"] = "dead_time_unknown"
        return out

    # confound / overlap scan over the effect REACH [win_lo, t+settle): a boundary
    # that truncated the window at exactly win_hi still contaminates the settling
    params = {a["parameter"] for a in (log.get("actions") or [])}
    win_lo, win_hi = seg["effect"]["row_range"]
    settle_end = int(round(seg["t_action_row"] + args.settle_steps))
    same_param_overlap = False
    for row_j, j_other in seg.get("boundaries", []):
        if not (win_lo <= row_j < max(win_hi, settle_end)):
            continue
        other = {a["parameter"] for a in (logs[j_other][1].get("actions") or [])}
        if other & params:
            same_param_overlap = True
        else:
            out["confound_detected"] = True
    if log.get("attribution_confounds"):
        out["confound_detected"] = True

    if same_param_overlap:
        out["attribution_compromised"] = True
        out["reason_code"] = "overlapping_action"

    if not seg["admissible_baseline"] or not seg["admissible_effect"]:
        out["attribution_status"] = "not_estimable"
        out["reason_code"] = out["reason_code"] or "min_points"
        return out

    br0, br1 = seg["baseline"]["row_range"]
    er0, er1 = seg["effect"]["row_range"]
    base_raw = np.asarray(series[br0:br1], dtype=float)
    eff_raw = np.asarray(series[er0:er1], dtype=float)
    base_vals = base_raw[~np.isnan(base_raw)]
    eff_vals = eff_raw[~np.isnan(eff_raw)]
    rho_b = seg["baseline"]["lag1_autocorr"]
    rho_a = seg["effect"]["lag1_autocorr"]

    # outlier gate first: an outlier-driven delta must never be reported
    o_verdict, _o_delta = outlier_check(base_vals, eff_vals, rho_b, rho_a)
    out["anti_spurious"]["outlier_check"] = o_verdict
    if o_verdict == "FAIL":
        out["attribution_status"] = "not_estimable"
        out["reason_code"] = out["reason_code"] or "outlier_driven"
        return out

    r = welch_delta_ci_neff(eff_vals, base_vals, rho_a, rho_b)
    if r is None:
        out["attribution_status"] = "not_estimable"
        out["reason_code"] = out["reason_code"] or "min_points"
        return out
    delta, lo, hi, n_eff_hi, n_eff_lo = r
    ci95 = [float(lo), float(hi)]

    stratified = None
    strat_delta = None
    if group_vals is not None:
        g_all = np.asarray([str(g) for g in group_vals])
        st = stratified_before_after_delta(base_raw, eff_raw,
                                           g_all[br0:br1], g_all[er0:er1], rho_b, rho_a)
        stratified = st["layers"]
        strat_delta = st["delta"]

    base_rows = np.arange(br0, br1)
    eff_rows = np.arange(er0, er1)
    t_verdict, _d_dt = trend_check(series, base_rows, eff_rows, delta)
    out["anti_spurious"]["trend_check"] = t_verdict

    direction = _ci_excludes_zero(ci95)
    conflict = False
    if direction and strat_delta is not None and strat_delta != 0 \
            and np.sign(strat_delta) != np.sign(delta):
        conflict = True
    if t_verdict == "FAIL":
        conflict = True

    if conflict:
        out["attribution_status"] = "direction_uncertain"
    elif seg["effect"].get("truncated_by"):
        out["attribution_status"] = "truncated"
    else:
        out["attribution_status"] = "estimable"

    out["effect"] = {
        "delta": float(delta),
        "ci95": ci95,
        "n_eff_hi": int(n_eff_hi),
        "n_eff_lo": int(n_eff_lo),
        "direction_established": bool(direction and not conflict),
        "stratified": stratified,
    }

    weak = (out["attribution_status"] in ("direction_uncertain", "truncated")
            or out["attribution_compromised"] or out["confound_detected"])
    out["evidence_grade"] = "E0" if weak else "E1"
    return out


def _assert_enums(report):
    """Guard: every enum-literal field must come from closedloop_enums.json
    (single source, mirrored by closedloop_common.enums)."""
    assert report["attribution_status"] in ATTRIBUTION_STATUS, report["attribution_status"]
    reason = report["reason_code"]
    assert reason is None or reason in NOT_ESTIMABLE_REASONS, reason
    assert report["evidence_grade"] in EVIDENCE_GRADES, report["evidence_grade"]
    for k in ("trend_check", "outlier_check"):
        v = report["anti_spurious"][k]
        assert v in ("PASS", "CAUTION", "FAIL", None), v


def attribute(run_dir, args):
    run_dir_p = _contained(run_dir)
    df = _load_dataframe(run_dir_p / args.data)
    time_values = None
    if args.time_col and args.time_col in df.columns:
        time_values = [parse_ts(v) for v in df[args.time_col].tolist()]
    group_vals = None
    if args.group_key:
        if args.group_key not in df.columns:
            raise SystemExit(f"group_key column missing: {args.group_key}")
        group_vals = df[args.group_key].tolist()

    import pandas as pd
    metric_missing = not args.metric or args.metric not in df.columns
    if metric_missing:
        series = np.zeros(max(1, len(df)), dtype=float)
    else:
        series = np.asarray(pd.to_numeric(df[args.metric], errors="coerce").to_numpy(),
                            dtype=float)

    log_path = Path(args.action_log)
    if not log_path.is_absolute():
        log_path = run_dir_p / log_path
    logs = load_action_logs(log_path)
    if not logs:
        raise SystemExit("no action logs found")

    dead_time_assumed = args.dead_time is None
    dead_time_arg = "0" if args.dead_time is None else str(args.dead_time)
    args.dead_time = dead_time_arg

    written = []
    for j, (log_id, log) in enumerate(logs):
        t_action = None
        if time_values is not None:
            t_action = ts_to_row(time_values, log.get("ts"))
        if t_action is None:
            rr = ((log.get("context") or {}).get("steady_segment_ref") or {}).get("row_range") or []
            if rr:
                t_action = int(rr[0])
        if metric_missing or t_action is None or str(dead_time_arg).lower() == "unknown":
            seg = _empty_segments()
        else:
            bounds = next_action_rows(logs, j, time_values) if time_values is not None else []
            seg = select_segments(series, t_action, bounds, dead_time=float(dead_time_arg),
                                  dead_time_assumed=dead_time_assumed,
                                  baseline_points=args.baseline_points, tau=args.tau_steps,
                                  settle=args.settle_steps, min_baseline_points=args.min_points)
            seg["boundaries"] = bounds
        report = attribute_action_log(log_id, log, logs, j, seg, args, series,
                                      metric_missing=metric_missing, group_vals=group_vals)
        _assert_enums(report)
        out_path = run_dir_p / REPORT_DIR / f"{log_id}.json"
        _write_json(out_path, report)
        written.append((log_id, report["attribution_status"], report["evidence_grade"]))
        print(f"[tune_stats] {log_id}: status={report['attribution_status']} "
              f"grade={report['evidence_grade']} reason={report['reason_code']} "
              f"-> {REPORT_DIR}/{log_id}.json")
    return written


def build_parser():
    p = argparse.ArgumentParser(description="deterministic action->outcome attribution")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("attribute", help="attribute all action logs in the run")
    a.add_argument("--run-dir", required=True)
    a.add_argument("--data", default="00_input/data.csv")
    a.add_argument("--time-col", default="t")
    a.add_argument("--metric", default=None)
    a.add_argument("--action-log", default="00_input/action_log.json")
    a.add_argument("--group-key", default=None)
    a.add_argument("--dead-time", default=None,
                   help="dead time in sampling steps; omit = assume 0 (annotated); "
                        "'unknown' refuses to assume (not_estimable/dead_time_unknown)")
    a.add_argument("--baseline-points", type=int, default=DEFAULT_BASELINE_POINTS)
    a.add_argument("--tau-steps", type=int, default=DEFAULT_TAU_STEPS)
    a.add_argument("--settle-steps", type=int, default=DEFAULT_SETTLE_STEPS)
    a.add_argument("--min-points", type=int, default=DEFAULT_MIN_BASELINE_POINTS)
    return p


if __name__ == "__main__":
    argv = build_parser().parse_args()
    if argv.cmd == "attribute":
        results = attribute(argv.run_dir, argv)
        n_bad = sum(1 for r in results if r[1] == "not_estimable")
        print(f"[tune_stats] {len(results)} report(s) written, {n_bad} not_estimable "
              f"(honest nulls)")
        sys.exit(0 if results else 2)
