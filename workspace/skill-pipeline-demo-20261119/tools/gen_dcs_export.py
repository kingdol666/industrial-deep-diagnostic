#!/usr/bin/env python3
"""Deterministic synthetic DCS export — packaging line oven section (demo scenario).

8-hour window, 5-second sampling, endpoints included (5761 rows), ISO-8601
timestamps with +08:00 timezone, evenly spaced, no missing values.

Injected signals (declared scenario ground truth for generation ONLY — these
are NOT analysis conclusions; every reported number must come from the
stability scripts):
  * oven_temp_c            : linear upward drift +1.5 C/h during the LAST 2
                             hours of the window (cumulative +3.0 C at end)
  * cooling_water_flow_lpm : one -15% step during the mid-section
                             (t=3.5h .. 4.5h), then recovery to baseline
  * all other channels     : stationary Gaussian noise only

Fixed seed => byte-identical output on every invocation.
"""
import argparse
import csv
import os
import random
from datetime import datetime, timedelta

COLUMNS = ["timestamp", "film_tension_n", "oven_temp_c", "line_speed_mpm",
           "cooling_water_flow_lpm", "scrap_rate_pct"]

# baselines / noise sigma (nominal setpoints of the packaging oven section)
BASE = {
    "film_tension_n": (250.0, 1.5),
    "oven_temp_c": (120.0, 0.35),
    "line_speed_mpm": (120.0, 0.8),
    "cooling_water_flow_lpm": (45.0, 0.9),
    "scrap_rate_pct": (1.20, 0.08),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--seed", type=int, default=20261119)
    ap.add_argument("--start", default="2026-11-18T06:00:00+08:00",
                    help="window start (ISO 8601 with timezone)")
    ap.add_argument("--hours", type=float, default=8.0)
    ap.add_argument("--interval-s", type=float, default=5.0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    t0 = datetime.fromisoformat(args.start)
    n = int(round(args.hours * 3600.0 / args.interval_s)) + 1  # both endpoints

    DRIFT_START_S = 6.0 * 3600.0      # last 2 hours of the 8-hour window
    DRIFT_RATE_C_PER_H = 1.5          # +1.5 C/h ramp
    STEP_START_S = 3.5 * 3600.0       # mid-section step down
    STEP_END_S = 4.5 * 3600.0         # recovery instant
    STEP_FACTOR = 0.85                # -15 %

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(n):
            t_s = i * args.interval_s
            ts = t0 + timedelta(seconds=t_s)
            tension = BASE["film_tension_n"][0] + rng.gauss(0.0, BASE["film_tension_n"][1])
            temp = BASE["oven_temp_c"][0] + rng.gauss(0.0, BASE["oven_temp_c"][1])
            if t_s >= DRIFT_START_S:
                temp += (t_s - DRIFT_START_S) / 3600.0 * DRIFT_RATE_C_PER_H
            speed = BASE["line_speed_mpm"][0] + rng.gauss(0.0, BASE["line_speed_mpm"][1])
            flow = BASE["cooling_water_flow_lpm"][0] + rng.gauss(0.0, BASE["cooling_water_flow_lpm"][1])
            if STEP_START_S <= t_s < STEP_END_S:
                flow *= STEP_FACTOR
            scrap = BASE["scrap_rate_pct"][0] + rng.gauss(0.0, BASE["scrap_rate_pct"][1])
            w.writerow([
                ts.isoformat(timespec="seconds"),
                f"{tension:.2f}",
                f"{temp:.3f}",
                f"{speed:.2f}",
                f"{flow:.2f}",
                f"{scrap:.3f}",
            ])
    print(f"seed={args.seed} rows={n} span={t0.isoformat()}.."
          f"{(t0 + timedelta(seconds=(n - 1) * args.interval_s)).isoformat()} "
          f"interval={args.interval_s}s -> {args.out}")


if __name__ == "__main__":
    main()
