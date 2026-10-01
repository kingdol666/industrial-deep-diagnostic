#!/usr/bin/env python
"""segment_selector.py — baseline/effect segment placement for tuning attribution.

All time quantities are in sampling steps (dt = 1 row of the time-ordered series).
Placement contract (frozen, plan industrial-closedloop-skills-v1 §4 Workstream B):

  baseline segment = [t_action - dead_time - N, t_action - dead_time)   N default 30
  effect segment   = [t_action + tau, min(next_action_row, t_action + settle))
  tau default 5 steps; settle default 200 steps; dead_time default 0 (assumed)

NaN discipline: a segment's `n` counts only finite metric values inside the raw
window; baseline admission requires n >= 10 (min_points) after NaN removal.
Both segments get lag-1 autocorrelation -> AR(1) effective sample size, reusing
industrial-doe-analyzer's doestats._stats_util (welch_delta_ci / lag1_autocorr /
effective_n) via sys.path injection — zero new dependencies, zero LLM.

File-IO discipline: every path passes through `_contained()` (normpath +
traversal-segment rejection + repo-root prefix whitelist); reads/writes use
pathlib only — there is no raw open() in this module.

CLI:
  uv run --project .claude/shared/scripts python segment_selector.py select \
      --run-dir RUN_DIR [--data 00_input/data.csv] [--time-col t] [--metric y] \
      [--action-log 00_input/action_log.json] [--action-index 0] \
      [--dead-time 0|unknown] [--baseline-points 30] [--tau-steps 5] [--settle-steps 200]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[2]
REPO_ROOT_NORM = os.path.normpath(os.path.abspath(str(REPO_ROOT)))
DOE_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"

# reuse doestats (industrial-doe-analyzer) — never re-implement shared numerics
sys.path.insert(0, str(DOE_SCRIPTS))
sys.path.insert(0, str(SHARED_SCRIPTS))
from doestats._stats_util import effective_n, lag1_autocorr  # noqa: E402

SCRIPT_VERSION = "segment_selector/1.0"

DEFAULT_BASELINE_POINTS = 30
DEFAULT_TAU_STEPS = 5
DEFAULT_SETTLE_STEPS = 200
DEFAULT_MIN_BASELINE_POINTS = 10
MIN_EFFECT_POINTS = 2


def _contained(candidate, extra_root=None):
    """Return candidate as a Path, enforcing containment inline: normpath ->
    reject traversal segments -> repo-root prefix whitelist."""
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    roots = [REPO_ROOT_NORM]
    if extra_root is not None:
        roots.append(os.path.normpath(os.path.abspath(str(extra_root))))
    for root in roots:
        if cand == root or cand.startswith(root + os.sep):
            return Path(cand)
    raise ValueError(f"path outside allowed roots: {candidate}")


def _read_json(path):
    return json.loads(_contained(path).read_text(encoding="utf-8"))


def _write_json(path, payload, extra_root=None):
    out = _contained(path, extra_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=float),
                   encoding="utf-8")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------- action logs

def _norm_numbers(o):
    """Normalize integral floats to ints so the canonical form is byte-identical
    across the Python and Node id derivations (JS has no int/float distinction)."""
    if isinstance(o, bool) or o is None:
        return o
    if isinstance(o, float) and o.is_integer() and abs(o) < 1e15:
        return int(o)
    if isinstance(o, dict):
        return {k: _norm_numbers(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_norm_numbers(v) for v in o]
    return o


def canonical_json(obj):
    return json.dumps(_norm_numbers(obj), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=float)


def derive_action_log_id(log):
    """action_log_id = ts8 + sha256(canonical)[..8] — server contract; when the
    log already carries an id (server-assigned) it is kept as-is (idempotent replay)."""
    if log.get("action_log_id"):
        return str(log["action_log_id"])
    ts = str(log.get("ts", ""))
    ts8 = "".join(ch for ch in ts if ch.isdigit())[:8] or "00000000"
    digest = hashlib.sha256(canonical_json(log).encode("utf-8")).hexdigest()
    return f"{ts8}{digest[:8]}"


def load_action_logs(path):
    """Accept a single JSON object, a JSON array, a JSONL file, or a directory
    of .json files. Returns a list of (action_log_id, log) sorted by ts."""
    p = _contained(path)
    if p.is_dir():
        logs = []
        for f in sorted(p.glob("*.json")):
            logs.extend(load_action_logs(f))
        return logs
    text = p.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        raw = json.loads(text)
    elif stripped.startswith("{"):
        raw = [json.loads(text)]
    else:  # JSONL
        raw = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [(derive_action_log_id(log), log) for log in raw]


def parse_ts(value):
    """Parse ISO8601-ish timestamps to a comparable float (epoch seconds).
    Returns None when unparseable."""
    if value is None:
        return None
    s = str(value).strip()
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def ts_to_row(time_values, ts):
    """Nearest row index of timestamp `ts` in the ordered time column.
    time_values: list of parsed floats (None entries keep index order)."""
    target = parse_ts(ts)
    if target is None:
        return None
    best, best_d = None, None
    for i, tv in enumerate(time_values):
        if tv is None:
            continue
        d = abs(tv - target)
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best


# ------------------------------------------------------------ segment logic

def finite_vals(series, lo, hi):
    """Finite metric values in the half-open row window [lo, hi)."""
    if lo is None or hi is None or hi <= lo:
        return np.array([], dtype=float)
    window = np.asarray(series[max(lo, 0):min(hi, len(series))], dtype=float)
    return window[~np.isnan(window)]


def segment_stats(series, lo, hi):
    """Finite-metric stats for the window [lo, hi). The reported row_range is the
    CLAMPED effective window (negative starts near data start must never leak as
    negative indices — numpy would silently wrap around to the array tail)."""
    if lo is None or hi is None:
        return {"row_range": None, "n": 0, "n_eff": None, "lag1_autocorr": None}
    lo_c, hi_c = max(int(lo), 0), min(int(hi), len(series))
    vals = finite_vals(series, lo_c, hi_c)
    rho = lag1_autocorr(vals)
    n_eff = effective_n(int(vals.size), rho) if rho is not None else None
    return {
        "row_range": [lo_c, hi_c],
        "n": int(vals.size),
        "n_eff": (int(n_eff) if n_eff is not None else None),
        "lag1_autocorr": (float(rho) if rho is not None else None),
    }


def next_action_rows(action_logs, current_index, time_values):
    """Row indices + ids of every other action event strictly after this one,
    sorted ascending. Bundles are attribution units, so ANY later action event
    (same bundle stream) truncates the effect window; same-parameter overlap
    inside the window is escalated to `overlapping_action` by tune_stats."""
    out = []
    cur_ts = parse_ts(action_logs[current_index][1].get("ts", ""))
    for j, (_jid, log) in enumerate(action_logs):
        if j == current_index:
            continue
        tv = parse_ts(log.get("ts", ""))
        if tv is None or cur_ts is None:
            continue
        if tv > cur_ts:
            row = ts_to_row(time_values, log.get("ts"))
            if row is not None:
                out.append((row, j))
    return sorted(out)


def select_segments(series, t_action, boundaries, dead_time=0.0, dead_time_assumed=False,
                    baseline_points=DEFAULT_BASELINE_POINTS, tau=DEFAULT_TAU_STEPS,
                    settle=DEFAULT_SETTLE_STEPS, min_baseline_points=DEFAULT_MIN_BASELINE_POINTS):
    """Place baseline + effect windows around action row `t_action`.

    boundaries: list of (row, action_index) strictly after the action — the first
    one caps the effect window (truncation).
    Returns a dict with raw windows, finite counts, per-segment autocorr/n_eff,
    truncation info and the dead-time assumption annotation.
    """
    n_rows = len(series)
    b_start = int(round(t_action - dead_time - baseline_points))
    b_end = int(round(t_action - dead_time))
    base = segment_stats(series, b_start, b_end)

    e_start = int(round(t_action + tau))
    settle_end = int(round(t_action + settle))
    trunc_by = None
    e_end = settle_end
    first_boundary = boundaries[0] if boundaries else None
    if first_boundary is not None and first_boundary[0] < e_end:
        e_end = first_boundary[0]
        trunc_by = f"action_log[{first_boundary[1]}]@row{first_boundary[0]}"
    if e_end > n_rows:
        e_end = n_rows
        if trunc_by is None:
            trunc_by = "data_end"
    if e_start >= e_end:
        trunc_by = trunc_by or "data_end"
    eff = segment_stats(series, e_start, max(e_start, e_end))

    return {
        "t_action_row": int(t_action),
        "baseline": base,
        "effect": {**eff, "truncated_by": trunc_by},
        "dead_time_used": float(dead_time),
        "dead_time_assumed": bool(dead_time_assumed),
        "constants": {"baseline_points": int(baseline_points), "tau_steps": int(tau),
                      "settle_steps": int(settle), "min_baseline_points": int(min_baseline_points)},
        "admissible_baseline": base["n"] >= min_baseline_points,
        "admissible_effect": eff["n"] >= MIN_EFFECT_POINTS,
        "script_version": SCRIPT_VERSION,
        "generated_at": now_iso(),
    }


# ---------------------------------------------------------------------- CLI

def _load_dataframe(data_path):
    import pandas as pd
    sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "industrial-data-processor" / "scripts"))
    from file_inspect import load_file  # reused multi-format loader
    return load_file(str(_contained(data_path)))


def cmd_select(args):
    run_dir = _contained(args.run_dir)
    df = _load_dataframe(run_dir / args.data)
    if args.metric not in df.columns:
        print(json.dumps({"error": "metric_missing", "metric": args.metric}, ensure_ascii=False))
        return 2
    series = np.asarray(pd.to_numeric(df[args.metric], errors="coerce").to_numpy(), dtype=float)

    time_values = None
    if args.time_col and args.time_col in df.columns:
        time_values = [parse_ts(v) for v in df[args.time_col].tolist()]

    log_path = run_dir / args.action_log if not os.path.isabs(args.action_log) else Path(args.action_log)
    logs = load_action_logs(log_path)
    if not logs:
        print(json.dumps({"error": "no_action_logs"}, ensure_ascii=False))
        return 2
    j = min(max(args.action_index, 0), len(logs) - 1)
    log_id, log = logs[j]

    t_action = None
    if time_values is not None:
        t_action = ts_to_row(time_values, log.get("ts"))
    if t_action is None:
        ref = ((log.get("context") or {}).get("steady_segment_ref") or {})
        rr = ref.get("row_range") or []
        if rr:
            t_action = int(rr[0])
    if t_action is None:
        print(json.dumps({"error": "action_time_unresolvable", "action_log_id": log_id},
                         ensure_ascii=False))
        return 2

    dead_time_assumed = args.dead_time is None  # degradation annotation, never silent
    if args.dead_time is not None and args.dead_time.lower() == "unknown":
        print(json.dumps({"error": "dead_time_unknown"}, ensure_ascii=False))
        return 2
    dead_time = float(args.dead_time if args.dead_time is not None else 0.0)

    bounds = next_action_rows(logs, j, time_values) if time_values is not None else []
    seg = select_segments(series, t_action, bounds, dead_time=dead_time,
                          dead_time_assumed=dead_time_assumed,
                          baseline_points=args.baseline_points, tau=args.tau_steps,
                          settle=args.settle_steps, min_baseline_points=args.min_points)
    seg["action_log_id"] = log_id
    print(json.dumps(seg, ensure_ascii=False, indent=2, default=float))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="segment placement for tuning attribution")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select", help="place baseline/effect segments for one action log")
    s.add_argument("--run-dir", required=True)
    s.add_argument("--data", default="00_input/data.csv")
    s.add_argument("--time-col", default="t")
    s.add_argument("--metric", required=True)
    s.add_argument("--action-log", default="00_input/action_log.json")
    s.add_argument("--action-index", type=int, default=0)
    s.add_argument("--dead-time", default=None,
                   help="dead time in sampling steps; omit = assume 0 (annotated); "
                        "'unknown' = refuse to assume (not_estimable/dead_time_unknown)")
    s.add_argument("--baseline-points", type=int, default=DEFAULT_BASELINE_POINTS)
    s.add_argument("--tau-steps", type=int, default=DEFAULT_TAU_STEPS)
    s.add_argument("--settle-steps", type=int, default=DEFAULT_SETTLE_STEPS)
    s.add_argument("--min-points", type=int, default=DEFAULT_MIN_BASELINE_POINTS)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.cmd == "select":
        sys.exit(cmd_select(args))
