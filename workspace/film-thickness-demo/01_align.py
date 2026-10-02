#!/usr/bin/env python
"""01_align.py — align thickness scans onto process rows with lag back-inference.

The thickness gauge samples a TD scan every 2 min; the film at the gauge left
the die ~5 min earlier (transport lag). For every scan timestamp t we therefore
match the process row nearest to (t - 5 min) — nearest-neighbour matching on
timestamps — and join the process parameters onto the scan features.

Output: aligned.csv
  timestamp, mean_thk, td_std, zone_L, zone_C, zone_R, dev_pos07,
  die_bolt_T3_pct, melt_temp_C, pull_speed_mpm, lip_gap_mm

  zone_L/C/R  = means of pos_01-07 / pos_08-14 / pos_15-21
  dev_pos07   = pos_07 - (pos_06 + pos_08) / 2   (stripe detector, lag-free
                neighbourhood: the T3 lip step hits pos_06/07/08 together and
                cancels in the difference)
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAG_MIN = 5  # process -> gauge transport lag (back-inference horizon)

POS_COLS = [f"pos_{i:02d}" for i in range(1, 22)]
PROC_COLS = ["die_bolt_T3_pct", "melt_temp_C", "pull_speed_mpm", "lip_gap_mm"]


def main():
    proc = pd.read_csv(HERE / "process.csv", parse_dates=["timestamp"])
    scans = pd.read_csv(HERE / "thickness_scans.csv", parse_dates=["timestamp"])

    # --- scan features -------------------------------------------------
    X = scans[POS_COLS].to_numpy(dtype=float)
    feats = pd.DataFrame({
        "timestamp": scans["timestamp"],
        "mean_thk": X.mean(axis=1),
        "td_std": X.std(axis=1, ddof=1),
        "zone_L": X[:, 0:7].mean(axis=1),
        "zone_C": X[:, 7:14].mean(axis=1),
        "zone_R": X[:, 14:21].mean(axis=1),
        "dev_pos07": X[:, 6] - (X[:, 5] + X[:, 7]) / 2.0,
    })

    # --- lag back-inference: scan t -> process row nearest (t - 5 min) --
    proc_sorted = proc.sort_values("timestamp").reset_index(drop=True)
    back = pd.DataFrame({
        "scan_ts": feats["timestamp"],
        "match_ts": feats["timestamp"] - pd.Timedelta(minutes=LAG_MIN),
    }).sort_values("match_ts")
    # nearest-neighbour match, no tolerance: rows whose back-inferred target
    # precedes the first process record clamp to the first available row
    proc_sorted["proc_ts"] = proc_sorted["timestamp"]
    merged = pd.merge_asof(
        back, proc_sorted.rename(columns={"timestamp": "match_ts"}),
        on="match_ts", direction="nearest")
    merged = merged.sort_values("match_ts").reset_index(drop=True)
    matched = merged[PROC_COLS].to_numpy(dtype=float)
    if np.isnan(matched).any():
        raise SystemExit("01_align: unmatched process rows — check cadences")
    back_min = (merged["scan_ts"] - merged["proc_ts"]).dt.total_seconds() / 60.0
    off = int((back_min != LAG_MIN).sum())
    print(f"01_align: {len(feats)} scan rows aligned; back-inference gap "
          f"median={back_min.median():.1f} min (design {LAG_MIN} min)")
    if off:
        idxs = list(np.flatnonzero((back_min != LAG_MIN).to_numpy()))
        print(f"01_align: note — {off} row(s) at indices {idxs[:8]} back-infer "
              f"before the first process record; clamped to nearest row")

    feats[PROC_COLS] = np.round(matched, 6)

    out = HERE / "aligned.csv"
    feats.round(6).to_csv(out, index=False)
    print(f"01_align: wrote {out}")

    # quick ground-truth sanity echo (aligned-row indices; scans every 2 min)
    t0 = feats["timestamp"].iloc[0]
    for label, minute in (("T1 stripe onset", 805), ("T2 MD-drop onset", 1405),
                          ("T3 lip step", 1905)):
        hit = feats["timestamp"] >= t0 + pd.Timedelta(minutes=minute)
        idx = int(np.flatnonzero(hit.to_numpy())[0]) if hit.any() else -1
        print(f"  truth {label}: thickness minute {minute} -> aligned row {idx}")


if __name__ == "__main__":
    main()
