#!/usr/bin/env python
"""step_detector.py — cold-start retro mining of setpoint steps (zero LLM).

Sliding-window mean-shift detection on settable columns: adjacent windows are
compared with a Welch t-test; a boundary fires when the BH-adjusted q-value
< --q-thresh (default 0.001) AND |delta| > k * robust sigma (1.4826*MAD).
Consecutive fired boundaries are merged to the single strongest boundary.

Output: a retro action log (action_log.schema.json-compatible entries) written
to 06_experience/retro_action_log.json. Every entry carries
  actor_type      = unknown_retro_inferred
  ingest_meta     = {source: retro_mined}
  bundled_action.note = advisory banner (E0 locked, advisory only — "仅参考")
Retro entries never participate in E2 corroboration promotion; an engineer
feedback `confirmed` completes ownership attribution.

File-IO discipline: pathlib only, every path through `_contained()`; no raw open().
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "shared" / "scripts"))
from segment_selector import _contained, _write_json, parse_ts  # noqa: E402
from closedloop_common.enums import ACTOR_TYPES  # noqa: E402  — enum literal source

SCRIPT_VERSION = "step_detector/1.0"
DEFAULT_WINDOW = 40
DEFAULT_K = 3.0
DEFAULT_Q = 0.001
D2 = 1.128  # MR-bar/d2 sigma convention (same family as sentinel baseline)


def robust_sigma_mr(x):
    """sigma_within via moving-range / d2; fallback to 1.4826*MAD."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < 3:
        return None
    mr = np.abs(np.diff(x))
    s = float(mr.mean()) / D2
    if s <= 0:
        mad = float(np.median(np.abs(x - np.median(x))))
        s = 1.4826 * mad
    return s if s > 0 else None


def bh_adjust(pvals):
    """Benjamini-Hochberg adjusted q-values (NaN/None pass through as None)."""
    idx = [i for i, p in enumerate(pvals) if p is not None and np.isfinite(p)]
    clean = [float(pvals[i]) for i in idx]
    m = len(clean)
    out = [None] * len(pvals)
    if m == 0:
        return out
    order = np.argsort(clean)
    ranked = np.asarray(clean, dtype=float)[order]
    q = ranked * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    for pos, orig_idx in enumerate(order):
        out[idx[orig_idx]] = float(q[pos])
    return out


def detect_steps(series, window=DEFAULT_WINDOW, k=DEFAULT_K, q_thresh=DEFAULT_Q):
    """Adjacent-window mean-shift detection on one series.
    Returns merged step boundaries: [{row, delta, q, sigma}]."""
    x = np.asarray(series, dtype=float)
    n = x.size
    if n < 2 * window:
        return []
    stride = max(1, window // 4)
    cand = []
    pvals = []
    bounds = list(range(window, n - window + 1, stride))
    for b in bounds:
        left = x[b - window:b]
        right = x[b:b + window]
        left = left[~np.isnan(left)]
        right = right[~np.isnan(right)]
        if left.size < window // 2 or right.size < window // 2:
            pvals.append(None)
            cand.append(None)
            continue
        res = sps.ttest_ind(right, left, equal_var=False)
        pvals.append(float(res.pvalue))
        cand.append((b, float(right.mean() - left.mean())))
    qvals = bh_adjust(pvals)
    sigma = robust_sigma_mr(x)
    if sigma is None:
        return []
    fires = []
    for i, b in enumerate(bounds):
        c = cand[i]
        q = qvals[i]
        if c is None or q is None:
            continue
        if q < q_thresh and abs(c[1]) > k * sigma:
            fires.append({"row": int(c[0]), "delta": c[1], "q": float(q),
                          "t": float(abs(sps.ttest_ind(
                              x[c[0]:c[0] + window][~np.isnan(x[c[0]:c[0] + window])],
                              x[c[0] - window:c[0]][~np.isnan(x[c[0] - window:c[0]])],
                              equal_var=False).statistic))})
    if not fires:
        return []
    # merge consecutive fires (within one window — boundaries this close see the
    # same physical step) -> keep the strongest boundary per cluster
    merged = []
    for f in sorted(fires, key=lambda d: d["row"]):
        if merged and f["row"] - merged[-1]["row"] <= window:
            if f["t"] > merged[-1]["t"]:
                merged[-1] = f
        else:
            merged.append(f)
    for m in merged:
        m["sigma"] = float(sigma)
    return merged


def build_retro_logs(df, cols, time_col, args):
    """One retro action log per detected step (per column)."""
    retro_actor = "unknown_retro_inferred"
    assert retro_actor in ACTOR_TYPES, "retro actor_type must mirror closedloop_enums.json"
    time_values = None
    if time_col and time_col in df.columns:
        time_values = [parse_ts(v) for v in df[time_col].tolist()]
    base_ts = args.base_ts
    logs = []
    for col in cols:
        series = np.asarray(
            __import__("pandas").to_numeric(df[col], errors="coerce").to_numpy(), dtype=float)
        steps = detect_steps(series, window=args.window, k=args.k, q_thresh=args.q_thresh)
        for st in steps:
            row = st["row"]
            pre = series[max(0, row - args.window):row]
            post = series[row:row + args.window]
            pre = pre[~np.isnan(pre)]
            post = post[~np.isnan(post)]
            if pre.size == 0 or post.size == 0:
                continue
            ts = None
            if time_values is not None and row < len(time_values):
                tv = time_values[row]
                if tv is not None:
                    ts = df[time_col].iloc[row]
            if ts is None:
                ts = f"{base_ts}+{int(row)}s" if base_ts else f"retro_row_{row}"
            logs.append({
                "schema_version": "1.0",
                "ts": str(ts),
                "actor": {"actor_id": "retro_step_detector", "actor_type": retro_actor,
                          "display_alias": None},
                "actions": [{"parameter": str(col),
                             "from": round(float(pre.mean()), 6),
                             "to": round(float(post.mean()), 6),
                             "to_level": None,
                             "unit": "unknown"}],
                "bundled_action": {"is_bundle": False, "bundle_reason": "single",
                                   "note": "retro-mined by step_detector — advisory only "
                                           "(仅参考), not an engineer-confirmed action"},
                "context": {"product": None, "machine": None, "regime_label": None,
                            "steady_segment_ref": {"data_path": args.data,
                                                   "row_range": [int(row), int(row)],
                                                   "time_range": [str(ts), str(ts)]},
                            "group_key": None},
                "ingest_meta": {"source": "retro_mined", "ingested_at": None},
            })
    return logs


def cmd_detect(args):
    import pandas as pd
    run_dir = _contained(args.run_dir)
    df = pd.read_csv(run_dir / args.data)
    if args.cols:
        cols = [c.strip() for c in args.cols.split(",") if c.strip() in df.columns]
    else:
        cols = [c for c in df.columns
                if c != args.time_col and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.9]
    if not cols:
        print(json.dumps({"error": "no_settable_columns"}, ensure_ascii=False))
        return 2
    logs = build_retro_logs(df, cols, args.time_col, args)
    out_path = run_dir / args.out if not Path(args.out).is_absolute() else Path(args.out)
    _write_json(out_path, logs)
    print(f"[step_detector] {len(logs)} retro step(s) over {len(cols)} column(s) "
          f"-> {args.out}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="cold-start retro step mining")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="sliding-window mean-shift detection -> retro action log")
    d.add_argument("--run-dir", required=True)
    d.add_argument("--data", default="00_input/data.csv")
    d.add_argument("--time-col", default="t")
    d.add_argument("--cols", default=None, help="comma-separated settable columns; default auto")
    d.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    d.add_argument("--k", type=float, default=DEFAULT_K)
    d.add_argument("--q-thresh", type=float, default=DEFAULT_Q)
    d.add_argument("--base-ts", default=None, help="synthetic ts base when the time column is absent")
    d.add_argument("--out", default="06_experience/retro_action_log.json")
    return p


if __name__ == "__main__":
    argv = build_parser().parse_args()
    if argv.cmd == "detect":
        sys.exit(cmd_detect(argv))
