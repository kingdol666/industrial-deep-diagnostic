#!/usr/bin/env python
"""gen_T2_sentinel.py — Examiner generator for T2 (sentinel stream).

Creates cases/T2_sentinel_stream/:
  history.csv            720 rows, tightly-controlled alternating jitter around
                         documented setpoints (the industrial-sentinel test
                         suite's own reference pattern for a deterministically
                         SPC-silent loop, cf. tests/run_tests.py jitter_df /
                         AC.md A-note)
  window_normal.csv      240 rows, same process, independent draw
  window_drift.csv       240 rows, speed_rpm ramps +0.06 rpm/min
                         (last-25% mean ~1262.6 -> hours_to_edge to the 1275
                         operating-window edge ~3.4 h)
  window_changepoint.csv 240 rows, temp_c steps +3.2 degC at row 120
  window_orphan.csv      60 rows normal data (screened with NO baseline)
  doe_prior/             minimal doe-analyzer-shaped run dir whose
                         recommendations.json carries the speed_rpm operating
                         window [1225, 1275] (verbatim-copied by build_baseline)

Process card (documented in the brief, not secret):
  temp_c 85.0 degC | pressure_mpa 2.40 | speed_rpm 1250 | flow_lpm 42.0
  jitter amplitudes: 0.08 / 0.005 / 0.6 / 0.12 (bounded alternating jitter)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261002
OUT = Path(__file__).resolve().parent.parent / "T2_sentinel_stream"
COLS = ["temp_c", "pressure_mpa", "speed_rpm", "flow_lpm"]
CENTERS = {"temp_c": 85.0, "pressure_mpa": 2.40, "speed_rpm": 1250.0, "flow_lpm": 42.0}
AMPS = {"temp_c": 0.08, "pressure_mpa": 0.005, "speed_rpm": 0.6, "flow_lpm": 0.12}


def alt_jitter(rng, n, col, k):
    """Center-free alternating bounded jitter — sign alternation kills R2/R3,
    amplitude << baseline sigma kills R1/R5/R6 (deterministically SPC-silent)."""
    i = np.arange(n)
    return (-1.0) ** (i + k) * rng.uniform(0, AMPS[col], n)


def jitter(rng, n, col, k):
    return CENTERS[col] + alt_jitter(rng, n, col, k)


def frame(rng, start, n, overrides=None):
    overrides = overrides or {}
    # NOTE: ISO timestamps WITH 9-digit nanosecond fraction. The sentinel
    # hours_axis divides parsed epoch ints by 1e9 assuming nanoseconds; under
    # pandas 3.x plain ISO strings parse to datetime64[us] (1000x unit error)
    # and epoch-second ints keep second resolution (1e9x error). Strings with
    # a .fffffffff fraction parse to datetime64[ns] -> correct hours.
    # Documented in truth/T2_truth.md.
    ts = pd.date_range(start, periods=n, freq="min")
    data = {"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.000000000")}
    for k, c in enumerate(COLS):
        if c in overrides:
            data[c] = overrides[c]
        else:
            data[c] = np.round(jitter(rng, n, c, k), 4)
    return pd.DataFrame(data)


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    hist = frame(rng, "2026-09-30 00:00", 720)
    hist.to_csv(OUT / "history.csv", index=False)

    normal = frame(rng, "2026-10-01 00:00", 240)
    normal.to_csv(OUT / "window_normal.csv", index=False)

    n = 240
    i = np.arange(n)
    drift_speed = np.round(1250.0 + 0.06 * i + alt_jitter(rng, n, "speed_rpm", 2), 4)
    drift = frame(rng, "2026-10-02 00:00", n, overrides={"speed_rpm": drift_speed})
    drift.to_csv(OUT / "window_drift.csv", index=False)

    temp = np.round(85.0 + 3.2 * (i >= 120) + alt_jitter(rng, n, "temp_c", 0), 4)
    cp = frame(rng, "2026-10-03 00:00", n, overrides={"temp_c": temp})
    cp.to_csv(OUT / "window_changepoint.csv", index=False)

    orphan = frame(rng, "2026-10-04 00:00", 60)
    orphan.to_csv(OUT / "window_orphan.csv", index=False)

    recs = {
        "contract_version": "1.0",
        "campaign_id": "DOE-20260920-001",
        "operating_windows": [{
            "factor": "speed_rpm",
            "unit": "rpm",
            "range": [1225.0, 1275.0],
            "confirmation_needed": False,
            "source": "DOE F-2026-09 line-speed operating window (line L7, product PVC-M)",
            "expected_effect": {"direction": "within_window_stable"}
        }],
        "response_specs": {},
        "applicability_domain": {"factor_observed_ranges": {"speed_rpm": [1235.0, 1265.0]}},
        "invalidation_conditions": ["valid for product PVC-M on line L7 only"],
    }
    (OUT / "doe_prior" / "conclusions").mkdir(parents=True, exist_ok=True)
    (OUT / "doe_prior" / "conclusions" / "recommendations.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
    stab = {"n_rows": 1440, "steady_ratio": 0.97, "change_points": []}
    (OUT / "doe_prior" / "02_analysis").mkdir(parents=True, exist_ok=True)
    (OUT / "doe_prior" / "02_analysis" / "stability_report.json").write_text(
        json.dumps(stab), encoding="utf-8")

    print("T2 stream written to", OUT)
    for f in sorted(OUT.glob("*.csv")):
        print(f"  {f.name:26s} rows={sum(1 for _ in open(f)) - 1}")


if __name__ == "__main__":
    main()
