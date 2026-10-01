#!/usr/bin/env python
"""sentinel_fast.py — fast-screen entry point of industrial-sentinel.

Incremental screening of 1-500 newly arrived rows against a frozen watch
baseline, carrying its continuation state in fast_state.json
(state ring buffer <= 300 rows, suppression table, hysteresis counters,
known change points). Target latency <= 5s per run.

Usage:
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-sentinel/scripts/sentinel_fast.py \
      --data NEW_ROWS.csv --state fast_state.json --baseline watch_baseline.json \
      [--group G] [--out fast_alert.json] [--line-id LINE1] [--config PATH]

Semantics:
  no baseline (missing/unreadable)          -> exit 2, refuse to run
  bad input (unreadable / > 500 rows /       -> exit 2
  ambiguous group without --group)
  clean                                      -> exit 0
  findings (warn/high/critical)              -> exit 1
  self-check (contract) failure              -> exit 3

Checks in fast mode: C1 SPC on the ring buffer (baseline center/sigma),
C4 robust z + Mahalanobis on the newest rows, quiet zones around change
points carried in state. C2 projection / C3 change-point detection are
watch-mode jobs (documented in method_notes.md). Anti-storm across runs via
state.suppression (60-min same-key merge) + hysteresis downgrade (5
consecutive in-band rows). ZERO LLM / ZERO NETWORK, no raw open().
"""

import argparse
import datetime
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sentinelcore import (  # noqa: E402
    ALERT_CONTRACT_VERSION,
    CHECK,
    EXIT_FINDINGS,
    EXIT_GATE_FAIL,
    EXIT_OK,
    EXIT_UNDETERMINED,
    MODE,
    NEXT_SKILL,
    NS,
    RULE,
    SCRIPT_VERSION,
    SEV,
    SEV_RANK,
    STATUS,
    SUPPRESSION_DEFAULTS,
    URG,
)
from sentinelcore import _io, robust, spc, suppress  # noqa: E402
from sentinel import (  # noqa: E402  (in-process reuse of watch helpers)
    build_alert,
    merged_thresholds,
    self_check,
    severity_rank,
    urgency_for,
    _spc_suggestion,
    _finite,
)

MAX_NEW_ROWS = 500
RING_MAX = 300
STATE_VERSION = "sentinel-state/1.0"


def load_state(path, line_id, ring_cols):
    """Load fast_state.json (creating a fresh one when absent)."""
    p = Path(path)
    if p.exists():
        try:
            state = _io.read_json(p)
            if state.get("state_version") == STATE_VERSION:
                state.setdefault("suppression", {})
                state.setdefault("consecutive_in_band", {})
                state.setdefault("known_change_points", [])
                state.setdefault("projection_cache", {})
                if not state.get("ring_buffer", {}).get("cols"):
                    state["ring_buffer"] = {"cols": list(ring_cols), "rows": []}
                return state
        except Exception:  # noqa: BLE001 — corrupted state restarts fresh
            pass
    return {
        "state_version": STATE_VERSION,
        "line_id": line_id,
        "updated_at": _io.now_iso(),
        "baseline_ref": None,
        "last_seen_ts": None,
        "last_index": None,
        "ring_buffer": {"cols": list(ring_cols), "rows": []},
        "known_change_points": [],
        "projection_cache": {},
        "suppression": {},
        "consecutive_in_band": {},
        "provenance": {"script_version": SCRIPT_VERSION, "authored_by": "script"},
    }


def rows_to_ring(new_df, ring_cols):
    rows = []
    for _, r in new_df.iterrows():
        row = []
        for c in ring_cols:
            v = r[c] if c in new_df.columns else None
            try:
                fv = float(v)
                row.append(fv if np.isfinite(fv) else None)
            except (TypeError, ValueError):
                row.append(None)
        rows.append(row)
    return rows


def cmd_fast(args):
    t0 = datetime.datetime.now(datetime.timezone.utc)
    try:
        baseline = _io.read_json(args.baseline)
    except Exception as exc:  # noqa: BLE001
        print(f"[sentinel_fast] no baseline ({exc}) — refusing to run (exit 2)")
        return EXIT_UNDETERMINED
    bgroups = baseline.get("groups") or {}
    if not bgroups:
        print("[sentinel_fast] baseline has no groups — refusing to run (exit 2)")
        return EXIT_UNDETERMINED
    group = args.group
    if group is None:
        if len(bgroups) == 1:
            group = next(iter(bgroups))
        else:
            print(f"[sentinel_fast] ambiguous baseline groups {sorted(bgroups)}: "
                  f"pass --group — refusing (exit 2)")
            return EXIT_UNDETERMINED
    if group not in bgroups:
        print(f"[sentinel_fast] group {group} not in baseline — refusing (exit 2)")
        return EXIT_UNDETERMINED
    store = bgroups[group]

    try:
        new_df = _io.load_table(args.data)
    except Exception as exc:  # noqa: BLE001
        print(f"[sentinel_fast] bad input: cannot load {args.data}: {exc}")
        return EXIT_UNDETERMINED
    n_new = len(new_df)
    if n_new == 0 or n_new > MAX_NEW_ROWS:
        print(f"[sentinel_fast] bad input: {n_new} rows (allowed 1-{MAX_NEW_ROWS})")
        return EXIT_UNDETERMINED

    cfg, _ = ({}, None)
    if args.config:
        try:
            cfg = _io.read_json(args.config)
        except Exception:  # noqa: BLE001
            cfg = {}
    th = merged_thresholds(cfg)

    ring_cols = list(baseline.get("global", {}).get("numeric_columns") or [])
    state = load_state(args.state, args.line_id or group, ring_cols)
    state["line_id"] = args.line_id or state.get("line_id") or group
    state["baseline_ref"] = str(_io._contained(args.baseline))
    prev_rows = state["ring_buffer"].get("rows") or []
    prev_cols = state["ring_buffer"].get("cols") or ring_cols
    if prev_cols != ring_cols:  # baseline changed — restart buffer
        prev_rows = []

    buffer_rows = [list(r) for r in prev_rows] + rows_to_ring(new_df, ring_cols)
    buffer_rows = buffer_rows[-RING_MAX:]
    col_pos = {c: i for i, c in enumerate(ring_cols)}
    last_index = state.get("last_index")
    offset_base = (int(last_index) + 1 - (len(buffer_rows) - n_new)
                   if last_index is not None else 0)

    # ---- z-scores against baseline (ring buffer aligned to ring_cols)
    zcols = {}
    for c in ring_cols:
        p = (store.get("parameters") or {}).get(c) or {}
        center, sigma = p.get("center"), p.get("sigma_within_mr")
        if center is None or not sigma:
            continue
        vals = np.array([row[col_pos[c]] if col_pos[c] < len(row) else None
                         for row in buffer_rows], dtype=float)
        with np.errstate(invalid="ignore"):
            zcols[c] = (vals - float(center)) / float(sigma)

    quiet_n = int(th.get("post_changepoint_quiet_rows",
                         SUPPRESSION_DEFAULTS["post_changepoint_quiet_rows"]))
    known_cps = [int(c) for c in (state.get("known_change_points") or [])]

    raw_alerts = []
    generated_at = _io.now_iso()
    spc_params = {k: th[k] for k in
                  ("run_length_r2", "run_length_r3", "r5_count", "r5_of",
                   "r6_count", "r6_of", "min_points",
                   "r2_materiality_z", "r3_materiality_z") if k in th}

    for col, z in zcols.items():
        for e in spc.evaluate(z, spc_params):
            abs_idx = offset_base + int(e["index"])
            if any(cp <= abs_idx < cp + quiet_n for cp in known_cps):
                continue  # quiet zone around a known change point
            sev = spc.severity_for(e["rule_name"])
            raw_alerts.append(build_alert(
                check_type=CHECK["spc"], rule_name=e["rule_name"],
                severity=sev, urgency=urgency_for(sev), group=group,
                parameter=col,
                observed={"value": _finite(_row_value(
                    buffer_rows, col_pos, col, e["index"])),
                    "statistic": _finite(e.get("statistic")),
                    "index": abs_idx,
                    "run_length": int(e.get("run_length") or 1)},
                threshold={"sigma_level": 3.0 if e["rule_name"] == RULE["NELSON_R1"]
                           else None},
                evidence={"n_points": int(e.get("run_length") or 1)},
                suggested_check=_spc_suggestion(e["rule_name"], col) + "（快筛）",
                suggested_next_skill=NEXT_SKILL["spc"],
                generated_at=generated_at))

    # ---- robust z on the newest rows only
    for c in ring_cols:
        p = (store.get("parameters") or {}).get(c) or {}
        vals = np.array([row[col_pos[c]] if col_pos[c] < len(row) else None
                         for row in buffer_rows[-n_new:]], dtype=float)
        zr = robust.robust_z(vals, p.get("median"), p.get("mad"),
                             p.get("sigma_overall"))
        for e in robust.robust_outliers(zr, float(th["robust_z_limit"])):
            raw_alerts.append(build_alert(
                check_type=CHECK["multivariate"], rule_name=robust.rule_robust(),
                severity=SEV["high"], urgency=urgency_for(SEV["high"]),
                group=group, parameter=c,
                observed={"value": _finite(vals[e["index"]]),
                          "statistic": _finite(e["statistic"]),
                          "index": offset_base + len(buffer_rows) - n_new
                          + int(e["index"]),
                          "run_length": int(e["run_length"])},
                threshold={"bound": float(th["robust_z_limit"])},
                evidence={"n_points": int(e["run_length"])},
                suggested_check=f"{c} 稳健 z |{e['statistic']:.2f}| 超阈值（快筛），"
                                f"建议进入 watch 全量核查",
                suggested_next_skill=NEXT_SKILL["multivariate"],
                generated_at=generated_at))

    # ---- anti-storm: same-key merge, hysteresis downgrade, suppression table
    merged = suppress.merge_by_key(raw_alerts)

    def violating_keys_of(alerts):
        return {a["suppression_key"] for a in alerts
                if a["check_type"] == CHECK["spc"]}

    violating_now = violating_keys_of(merged)
    # hysteresis: a re-trigger after >= N consecutive in-band rows is
    # downgraded one level; the counters BEFORE this batch's reset decide
    counters_before = dict(state.get("consecutive_in_band") or {})
    merged = suppress.hysteresis_downgrade(
        merged, counters_before, SUPPRESSION_DEFAULTS["hysteresis_points"])
    counters = suppress.hysteresis_update(
        state.get("consecutive_in_band") or {}, violating_now, n_new,
        SUPPRESSION_DEFAULTS["hysteresis_points"])

    suppression_table, prior_counts = suppress.suppression_table_update(
        state.get("suppression") or {}, [a["suppression_key"] for a in merged],
        generated_at, SUPPRESSION_DEFAULTS["suppress_window_minutes"])
    for a in merged:
        prior = int(prior_counts.get(a["suppression_key"], 0))
        if prior:
            a["repeat_count"] = prior + 1

    state["suppression"] = suppression_table
    state["consecutive_in_band"] = counters

    repeat_totals = {}
    for a in merged:
        repeat_totals[a["suppression_key"]] = (
            repeat_totals.get(a["suppression_key"], 0) + int(a["repeat_count"]))

    merged.sort(key=lambda a: (-severity_rank(a["severity"]), a["check_type"],
                               a["rule_name"], str(a.get("parameter"))))
    for i, a in enumerate(merged, 1):
        a["alert_id"] = (f"ALT-{generated_at[0:10].replace('-', '')}"
                         f"-{generated_at[11:19].replace(':', '')}-{i:03d}")

    # ---- update ring-buffer state (sole writer discipline)
    state["ring_buffer"] = {"cols": list(ring_cols), "rows": buffer_rows}
    state["last_index"] = int(int(last_index) + n_new) if last_index is not None \
        else int(n_new - 1)
    state["updated_at"] = generated_at
    state["provenance"] = {"script_version": SCRIPT_VERSION, "authored_by": "script"}

    duration_ms = int((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() * 1000)
    if any(severity_rank(a["severity"]) >= severity_rank(SEV["high"])
           for a in merged):
        status = STATUS["alert"]
    elif any(a["severity"] == SEV["warn"] for a in merged):
        status = STATUS["warn"]
    else:
        status = STATUS["ok"]

    payload = {
        "contract_version": ALERT_CONTRACT_VERSION,
        "alert_id": f"ALT-{generated_at[0:10].replace('-', '')}"
                    f"-{generated_at[11:19].replace(':', '')}-000",
        "mode": MODE["fast_screen"],
        "status": status,
        "group_scope": group,
        "generated_at": generated_at,
        "source": {
            "data_path": str(_io._contained(args.data)),
            "sha256": _io.sha256_file(args.data),
            "window_start": None,
            "window_end": None,
            "n_rows": int(n_new),
            "time_col": baseline.get("global", {}).get("time_col"),
            "group_col": baseline.get("global", {}).get("group_col"),
        },
        "baseline": {
            "path": str(_io._contained(args.baseline)),
            "baseline_version": baseline.get("baseline_version"),
            "mode": "prior",
            "generated_from": baseline.get("generated_from", {}).get("doe_run_dir"),
        },
        "checks_summary": {
            "spc": {"n_triggered": sum(1 for a in merged
                                       if a["check_type"] == CHECK["spc"]),
                    "rules_hit": {}},
            "window_projection": {"n_triggered": 0},
            "regime": {"labels": {}, "n_change_points_new": 0},
            "multivariate": {"n_outliers": sum(1 for a in merged
                                               if a["check_type"] == CHECK["multivariate"]),
                             "max_d2": None},
            "rows_skipped": 0,
        },
        "alerts": merged,
        "regime_summary": None,
        "projection_summary": None,
        "suppression": {
            "applied": [
                {"suppression_key": k, "repeat_count": int(v)}
                for k, v in sorted(repeat_totals.items()) if int(v) > 1
            ],
            "config": {
                "suppress_window_minutes": SUPPRESSION_DEFAULTS["suppress_window_minutes"],
                "hysteresis_points": SUPPRESSION_DEFAULTS["hysteresis_points"],
                "post_changepoint_quiet_rows": quiet_n,
            },
        },
        "provenance": {
            "input_sha256": _io.sha256_file(args.data),
            "script_version": SCRIPT_VERSION,
            "duration_ms": duration_ms,
            "zero_llm": True,
            "authored_by": "script",
        },
    }

    problems = self_check(payload)
    out_path = args.out or (Path(str(args.data)).parent / "fast_alert.json")
    if problems:
        for p in problems:
            print(f"[sentinel_fast] SELF-CHECK FAIL: {p}")
        _io.write_json(out_path, payload)
        _io.write_json(args.state, state)
        return EXIT_GATE_FAIL

    _io.write_json(out_path, payload)
    _io.write_json(args.state, state)
    print(f"[sentinel_fast] status={status} alerts={len(merged)} -> {out_path} "
          f"({duration_ms}ms, ring={len(buffer_rows)}/{RING_MAX})")
    return EXIT_OK if status == STATUS["ok"] else EXIT_FINDINGS


def _row_value(buffer_rows, col_pos, col, idx):
    row = buffer_rows[idx] if 0 <= idx < len(buffer_rows) else []
    pos = col_pos.get(col)
    if row and pos is not None and pos < len(row):
        return row[pos]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="industrial-sentinel fast-screen")
    ap.add_argument("--data", required=True, help="new rows CSV (1-500 rows)")
    ap.add_argument("--state", required=True, help="fast_state.json path")
    ap.add_argument("--baseline", required=True, help="watch_baseline.json path")
    ap.add_argument("--group", default=None)
    ap.add_argument("--line-id", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    return cmd_fast(args)


if __name__ == "__main__":
    sys.exit(main())
