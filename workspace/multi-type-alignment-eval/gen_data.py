#!/usr/bin/env python
"""gen_data.py — seeded generator for the multi-type × multi-condition
time-alignment matching study (master seed 20261001).

Scenario ground truths
  S1  scalar×steady   : y = 50 + 0.6*x1(t-4) + N(0,0.3); x2 iid irrelevant.
  S2  scalar×2-cond   : same coupling in both products; product step at row 600
                        shifts x1 base 10→16 and y base 50→44 (anti-aligned level
                        step => pooled correlation is NEGATIVE, within-stratum
                        POSITIVE => Simpson direction reversal is plantable).
  S3  vector×TD scan  : 21 positions @2min/scan, process @1min; pos_07 stripe =
                        0.8 * die_bolt_T3(t - 10min) (= 5 scan steps) + N(0,0.15);
                        driver has AR(1) texture + a +2.0 step at process minute 600.
  S4  vector×spectral : 64 bins @5min/frame, 600 frames; bins 10-20 shift by
                        0.35*(furnace_temp(t-3 frames) - 1180); furnace AR(1)
                        around 1180 + step +6 at frame 350; other bins iid.
  S5  scalar×drift    : y = 50 + 0.6*x1(t-4) + 0.002*t + N(0,0.25); drift_a and
                        drift_b co-trend on slow ramps (drift confounders).
  S1T tuning          : S1 draws + setpoint step x1 +1.0 at row 700 (effect y
                        +0.6 at row 704) + matching action_log.json.
"""
from pathlib import Path

import json

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MASTER = 20261001
T0 = pd.Timestamp("2026-09-01 00:00:00")


def iso_series(n, step_min):
    return pd.Index((T0 + pd.to_timedelta(np.arange(n) * step_min, unit="m"))
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def ar1(rng, n, sd, phi=0.6):
    x = np.empty(n)
    x[0] = rng.normal()
    innov = rng.normal(0, 1, n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + innov[i]
    return x * (sd / max(x.std(ddof=1), 1e-12))


def ctx(responses, factors, time_col, group_col=None, max_lag=10,
        notes="multi-type-alignment-eval"):
    return {
        "data_path": "00_input/data.csv", "mode_override": None,
        "responses": [{"col": c, "goal": "maximize", "lsl": None, "usl": None,
                       "target": None, "weight": None} for c in responses],
        "factors": [{"col": c, "type": "numeric"} for c in factors],
        "blocks": [], "covariates": [], "index_cols": [],
        "time_col": time_col, "group_col": group_col, "run_order_col": None,
        "max_lag": max_lag, "alpha": 0.05, "effect_size_threshold": 0.01,
        "constraints": [],
        "inference": {"assigned_by": "user", "notes": [notes]},
    }


def make_run(name):
    run = HERE / name / "run" / "00_input"
    run.mkdir(parents=True, exist_ok=True)
    return run


def write_ctx(run_dir, payload):
    (run_dir / "analysis_context.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8")


def main():
    root = np.random.SeedSequence(MASTER)
    s1, s2, s3, s4, s5 = [np.random.default_rng(s) for s in root.spawn(5)]

    # ---------------- S1 scalar × steady --------------------------------
    n = 1200
    x1 = ar1(s1, n, 1.0)
    x2 = s1.normal(0, 1.0, n)
    y = 50.0 + 0.6 * np.r_[np.full(4, x1[0]), x1[:-4]] + s1.normal(0, 0.3, n)
    df = pd.DataFrame({"t": iso_series(n, 1), "x1": x1.round(6),
                       "x2": x2.round(6), "y": y.round(6)})
    run = make_run("S1")
    df.to_csv(run / "data.csv", index=False)
    write_ctx(run, ctx(["y"], ["x1", "x2"], "t", max_lag=10,
                       notes="S1 truth: y=50+0.6*x1(t-4), x2 irrelevant"))
    df.iloc[:600].to_csv(HERE / "S1" / "s1_history.csv", index=False)
    df.iloc[600:].to_csv(HERE / "S1" / "s1_watch.csv", index=False)

    # ---------------- S2 scalar × dual condition ------------------------
    n = 1200
    x1a = 10.0 + ar1(s2, 600, 1.0)
    x1b = 16.0 + ar1(s2, 600, 1.0)
    x1 = np.r_[x1a, x1b]
    ya = 50.0 + 0.6 * np.r_[np.full(4, x1a[0]), x1a[:-4]] + s2.normal(0, 0.3, 600)
    yb = 44.0 + 0.6 * np.r_[np.full(4, x1b[0]), x1b[:-4]] + s2.normal(0, 0.3, 600)
    y = np.r_[ya, yb]
    x2 = s2.normal(0, 1.0, n)
    df = pd.DataFrame({"t": iso_series(n, 1),
                       "product": np.where(np.arange(n) < 600, "P1", "P2"),
                       "x1": x1.round(6), "x2": x2.round(6), "y": y.round(6)})
    run = make_run("S2")
    df.to_csv(run / "data.csv", index=False)
    write_ctx(run, ctx(["y"], ["x1", "x2"], "t", group_col="product", max_lag=10,
                       notes="S2 truth: y=base+0.6*x1(t-4) per product; "
                             "level step x1 10->16, y 50->44 at row 600"))
    df[df["product"] == "P1"].to_csv(HERE / "S2" / "s2_p1.csv", index=False)
    df[df["product"] == "P2"].to_csv(HERE / "S2" / "s2_p2.csv", index=False)

    # ---------------- S3 vector × TD profile ----------------------------
    proc_min = np.arange(0, 810)          # 1-min cadence process rows
    scan_min = np.arange(10, 810, 2)      # 2-min cadence scans (400 rows)
    d = 52.0 + ar1(s3, proc_min.size, 1.0)
    d[proc_min >= 600] += 2.0             # step at process minute 600
    melt = 195.0 + ar1(s3, proc_min.size, 0.8)
    pull = 120.0 + ar1(s3, proc_min.size, 0.5)
    proc = pd.DataFrame({"timestamp": iso_series(proc_min.size, 1),
                         "die_bolt_T3_pct": d.round(6),
                         "melt_temp_C": melt.round(6),
                         "pull_speed_mpm": pull.round(6)})
    raw = HERE / "S3" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    proc.to_csv(raw / "process.csv", index=False)

    didx = {m: i for i, m in enumerate(proc_min)}
    scan_d = np.array([d[didx[m - 10]] for m in scan_min])
    k = scan_min.size
    X = np.empty((k, 21))
    for j in range(21):
        X[:, j] = 100.0 + 0.05 * (j - 10.5) ** 2 + s3.normal(0, 0.15, k)
    X[:, 6] = 100.0 + 0.8 * scan_d + s3.normal(0, 0.15, k)   # pos_07 stripe
    scans = pd.DataFrame({"timestamp": (T0 + pd.to_timedelta(scan_min, unit="m")
                                        ).strftime("%Y-%m-%dT%H:%M:%SZ")})
    for j in range(21):
        scans[f"pos_{j+1:02d}"] = X[:, j].round(6)
    scans.to_csv(raw / "thickness_scans.csv", index=False)
    print(f"S3: {k} scans, stripe truth = 0.8*die_bolt_T3(t-10min); "
          f"driver step at minute 600 (scan idx {int(np.searchsorted(scan_min, 600))})")

    # ---------------- S4 vector × spectral ------------------------------
    nf = 600
    furn = 1180.0 + ar1(s4, nf, 2.0)
    furn[350:] += 6.0                     # step at frame 350
    stir = 90.0 + ar1(s4, nf, 1.0)
    b = np.arange(64)
    base = 100.0 * np.exp(-((b - 32.0) ** 2) / (2 * 12.0 ** 2))
    dev_furn = furn - 1180.0
    spec = base[None, :] + s4.normal(0, 0.5, (nf, 64))
    for c in range(10, 21):               # truth band bins 10..20 (incl)
        spec[:, c] += 0.35 * np.r_[np.full(3, dev_furn[0]), dev_furn[:-3]]
    spec = np.round(spec, 6)
    band_mean = spec[:, 10:21].mean(axis=1)
    band_ref = spec[:, 45:56].mean(axis=1)
    fr = pd.DataFrame({"timestamp": iso_series(nf, 5),
                       "band_mean": band_mean.round(6),
                       "band_ref_mean": band_ref.round(6),
                       "furnace_temp_C": furn.round(6),
                       "stir_speed_rpm": stir.round(6)})
    raw4 = HERE / "S4" / "raw"
    raw4.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"timestamp": fr["timestamp"],
                  **{f"bin_{i:02d}": spec[:, i] for i in range(64)}}).to_csv(
        raw4 / "spectra.csv", index=False)
    fr.to_csv(raw4 / "process_frames.csv", index=False)
    run = make_run("S4")
    fr.to_csv(run / "data.csv", index=False)
    write_ctx(run, ctx(["band_mean"], ["furnace_temp_C", "stir_speed_rpm",
                                       "band_ref_mean"],
                       "timestamp", max_lag=8,
                       notes="S4 truth: band_mean(bins10-20) = 0.35*(furnace(t-3)-1180); "
                             "furnace step +6 at frame 350"))
    fr.iloc[:300].to_csv(HERE / "S4" / "s4_history.csv", index=False)
    fr.iloc[300:].to_csv(HERE / "S4" / "s4_watch.csv", index=False)

    # ---------------- S5 scalar × drift confound ------------------------
    n = 1200
    t = np.arange(n, dtype=float)
    x1 = ar1(s5, n, 1.0)
    drift_a = 0.012 * t + s5.normal(0, 0.4, n)
    drift_b = 0.010 * t + s5.normal(0, 0.4, n)
    y = (50.0 + 0.6 * np.r_[np.full(4, x1[0]), x1[:-4]]
         + 0.002 * t + s5.normal(0, 0.25, n))
    df = pd.DataFrame({"t": iso_series(n, 1), "x1": x1.round(6),
                       "drift_a": drift_a.round(6), "drift_b": drift_b.round(6),
                       "y": y.round(6)})
    run = make_run("S5")
    df.to_csv(run / "data.csv", index=False)
    write_ctx(run, ctx(["y"], ["x1", "drift_a", "drift_b"], "t", max_lag=10,
                       notes="S5 truth: y=50+0.6*x1(t-4)+0.002t; drift_a/b co-trend"))

    # ---------------- S1T = S1 + setpoint action at row 700 -------------
    x1t = x1.copy()
    x1t[700:] += 1.0
    yt = 50.0 + 0.6 * np.r_[np.full(4, x1t[0]), x1t[:-4]] + s1.normal(0, 0.3, n)
    df = pd.DataFrame({"t": iso_series(n, 1), "x1": x1t.round(6),
                       "x2": x2.round(6), "y": yt.round(6)})
    run = make_run("S1T")
    df.to_csv(run / "data.csv", index=False)
    action_log = [{
        "schema_version": "1.0",
        "ts": df["t"].iloc[700],
        "actor": {"actor_id": "ENG-LIU-0107", "actor_type": "engineer",
                  "display_alias": None},
        "actions": [{"parameter": "x1", "from": 50.0, "to": 51.0, "unit": "unit"}],
        "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
        "context": {"product": "P1", "machine": "M1", "regime_label": "R1",
                    "steady_segment_ref": None, "group_key": None},
        "attribution_confounds": [],
        "recommendation_ref": None,
        "ingest_meta": {"source": "csv_import", "ingested_at": None},
    }]
    import json
    (run / "action_log.json").write_text(json.dumps(action_log, indent=2),
                                         encoding="utf-8")
    write_ctx(run, ctx(["y"], ["x1", "x2"], "t", max_lag=10,
                       notes="S1T truth: x1 setpoint +1 at row 700, y +0.6 at row 704"))
    print("S1T: action ts =", df["t"].iloc[700])

    # ---------------- S6 objective (truth: 0.25*(T3-2)^2) ---------------
    run6 = make_run("S6")
    objective = {
        "contract_version": "1.0", "campaign_id": "OPT-20261001-S6",
        "target_metric": "dev_pos07", "goal": "minimize", "tolerance": 0.15,
        "factors": [{"name": "die_bolt_T3_pct", "type": "numeric",
                     "min": 0.0, "max": 10.0, "unit": "%"}],
        "budget": {"max_rounds": 14, "max_trials": 80},
        "noise": {"replicates_for_sigma": 3}, "seed": 42,
    }
    import json
    (run6 / "objective.json").write_text(json.dumps(objective, indent=2),
                                         encoding="utf-8")
    print("S6: objective written (goal=minimize, tolerance=0.15, truth "
          "dev=0.25*(T3-2)^2 + N(0,0.03))")

    print("ALL SCENARIOS WRITTEN under", HERE)


if __name__ == "__main__":
    main()
