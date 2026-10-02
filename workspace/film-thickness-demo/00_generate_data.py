#!/usr/bin/env python
"""00_generate_data.py — film-thickness demo data generator (seed=7).

Ground truth (process time, minutes):
  T1  m>=800   die_bolt_T3_pct ramps up +6.0 pct (die-block accumulation / bolt loosening)
      -> stripe at pos_07, visible in film thickness from m>=805 (5-min process lag),
         ramping to +2.5 um over 400 min then plateau (deposit grows then stabilises)
  T2  m>=1400  melt_temp_C ramps up +2.5 C (heating runaway)
      -> full-width mean thickness drops linearly to -0.8 um from m>=1405
  T3  m>=1900  lip_gap_mm step -0.02 mm (manual die-bolt adjustment)
      -> pos_06/07/08 step -1.5 um from m>=1905 (cancels in dev_pos07 by construction)

Outputs (this directory):
  process.csv          2400 rows, 1/min
  thickness_scans.csv  1200 rows, 1/2min, pos_01..pos_21 (um)
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 7
START = pd.Timestamp("2026-09-30 00:00:00")
LAG_MIN = 5  # process -> thickness transport lag

rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ process
n_proc = 2400
m = np.arange(n_proc, dtype=float)
ts_proc = pd.date_range(START, periods=n_proc, freq="1min")


def ramp(start, total, until):
    """Linear ramp from `start`, reaching `total` at `until` (minutes)."""
    return total * np.clip(m - start, 0, None) / float(until - start)


die_bolt_T3 = 50.0 + rng.normal(0.0, 0.25, n_proc) + ramp(800, 6.0, 2399)   # T1
melt_temp = 285.0 + rng.normal(0.0, 0.15, n_proc) + ramp(1400, 2.5, 2399)   # T2
pull_speed = 120.0 + rng.normal(0.0, 0.20, n_proc)
lip_gap = 0.850 + rng.normal(0.0, 0.0006, n_proc)
lip_gap[m >= 1900] -= 0.02                                                   # T3
pump_rpm = 25.0 + rng.normal(0.0, 0.12, n_proc)

process = pd.DataFrame({
    "timestamp": ts_proc.strftime("%Y-%m-%dT%H:%M:%S"),
    "die_bolt_T3_pct": np.round(die_bolt_T3, 4),
    "melt_temp_C": np.round(melt_temp, 4),
    "pull_speed_mpm": np.round(pull_speed, 4),
    "lip_gap_mm": np.round(lip_gap, 5),
    "pump_rpm": np.round(pump_rpm, 4),
})
process.to_csv(HERE / "process.csv", index=False)

# ------------------------------------------------------------------ thickness
n_scan = 1200
t_scan = np.arange(n_scan, dtype=float) * 2.0          # scan minutes 0..2398
ts_scan = (START + pd.to_timedelta(t_scan, unit="min")).strftime("%Y-%m-%dT%H:%M:%S")
pos = np.arange(1, 22)                                  # pos_01..pos_21

# baseline profile: 50 um target + parabolic edge thinning (+-1.2 um at edges)
profile = 50.0 - 1.2 * ((pos - 11) / 10.0) ** 2
X = np.tile(profile, (n_scan, 1)) + rng.normal(0.0, 0.15, (n_scan, 21))

# implant 1: pos_07 stripe, visible from t>=800+LAG, ramp to +2.5 um in 400 min
stripe = 2.5 * np.clip((t_scan - (800 + LAG_MIN)) / 400.0, 0.0, 1.0)
stripe[t_scan < 800 + LAG_MIN] = 0.0
X[:, 6] += stripe

# implant 2: full-width MD drop from t>=1400+LAG, linear ramp to -0.8 um at run end
md = -0.8 * np.clip((t_scan - (1400 + LAG_MIN)) / (2398.0 - (1400 + LAG_MIN)), 0.0, None)
X += md[:, None]

# implant 3: lip adjustment effect from t>=1900+LAG: pos_06/07/08 step -1.5 um
adj = np.where(t_scan >= 1900 + LAG_MIN, -1.5, 0.0)
X[:, [5, 6, 7]] += adj[:, None]

scans = pd.DataFrame(X, columns=[f"pos_{i:02d}" for i in range(1, 22)]).round(4)
scans.insert(0, "timestamp", ts_scan)
scans.to_csv(HERE / "thickness_scans.csv", index=False)

print(f"process.csv: {len(process)} rows, "
      f"{process['timestamp'].iloc[0]} .. {process['timestamp'].iloc[-1]}")
print(f"thickness_scans.csv: {len(scans)} rows x 21 positions")
print(f"ground truth (thickness-visible, scan-minute): T1 stripe @805, "
      f"T2 MD drop @1405, T3 lip step @1905 (lag={LAG_MIN} min)")
