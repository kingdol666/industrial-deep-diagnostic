#!/usr/bin/env python
"""s3_align.py — film-demo-style lag back-inference alignment for S3.

Joins the 1-min process rows onto the 2-min TD scans. For every scan at time
t the matched process row is the one nearest (t - BACK_MIN); BACK_MIN = 10 min
= 5 scan steps (the planted stripe transport lag).

Usage:
  python s3_align.py --back-min 10 --out S3/run/00_input/data.csv
  python s3_align.py --back-min 0  --out S3/run_unaligned/00_input/data.csv

Derived scan features (film-demo caliber):
  mean_thk, td_std, zone_L (pos_01-07), zone_C (pos_08-14), zone_R (pos_15-21),
  dev_pos07 = pos_07 - (pos_06 + pos_08) / 2
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
POS_COLS = [f"pos_{i:02d}" for i in range(1, 22)]
PROC_COLS = ["die_bolt_T3_pct", "melt_temp_C", "pull_speed_mpm"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--back-min", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    raw = HERE / "S3" / "raw"
    proc = pd.read_csv(raw / "process.csv", parse_dates=["timestamp"])
    scans = pd.read_csv(raw / "thickness_scans.csv", parse_dates=["timestamp"])

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

    proc_sorted = proc.sort_values("timestamp").reset_index(drop=True)
    back = pd.DataFrame({
        "scan_ts": feats["timestamp"],
        "match_ts": feats["timestamp"] - pd.Timedelta(minutes=a.back_min),
    }).sort_values("match_ts")
    proc_sorted["proc_ts"] = proc_sorted["timestamp"]
    merged = pd.merge_asof(
        back, proc_sorted.rename(columns={"timestamp": "match_ts"}),
        on="match_ts", direction="nearest")
    merged = merged.sort_values("match_ts").reset_index(drop=True)
    matched = merged[PROC_COLS].to_numpy(dtype=float)
    if np.isnan(matched).any():
        raise SystemExit("s3_align: unmatched process rows — check cadences")
    off_min = (merged["scan_ts"] - merged["proc_ts"]).dt.total_seconds() / 60.0
    exact = int((off_min == a.back_min).sum())
    print(f"s3_align back={a.back_min:g}min: {len(feats)} scans aligned, "
          f"{exact}/{len(feats)} exact-neighbour matches, "
          f"gap median={off_min.median():.1f} min")

    feats[PROC_COLS] = np.round(matched, 6)
    out = Path(a.out)
    if not out.is_absolute():
        out = HERE / out
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.round(6).to_csv(out, index=False)
    print("s3_align wrote", out)


if __name__ == "__main__":
    main()
