#!/usr/bin/env python
"""Generate a realistic AgentWorkShop capture for the DOE field trial.

The capture is shaped exactly like the platform's DAQ export:

    <export>/manifest.json            aw.daq-export/1
    <export>/nodes/<node>.csv         ts_iso,ts_ms,value,state

Three artifacts are produced from ONE simulated BOPET 12 µm line:

  history/    6 h of stable production        -> sentinel baseline
  line/       6 h that contains an anomaly    -> quick-screen + stability
  campaign/   22 executions of a face-centred 3-factor CCD, each execution a
              separate DAQ export, plus trial design / QC / profiles / notes
                                             -> DOE analysis
  hetero/     TD thickness profiles (63 points) + operator notes, one snapshot
              per trial run                     -> E-1H scalar features

Everything is seeded and deterministic; `scenario_truth.json` records the
planted surface, the stationary point and the anomaly times so the analysis
can be judged against truth instead of against itself.

Usage:
    python generate_capture.py [--force]
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import json
import math
import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "capture"
SEED = 20261017
PROFILE_POINTS = 63

NODES = {
    "tdo_z4_temp": ("TDO Z4 温度", "°C", 180.0, 220.0, 0.1),
    "mdo_speed": ("MDO 车速", "m/min", 280.0, 360.0, 0.1),
    "tdo_ratio": ("TDO 拉伸比", "-", 2.6, 3.4, 0.001),
    "thickness_gauge": ("在线测厚", "um", 40.0, 60.0, 0.001),
    "haze_gauge": ("在线雾度", "%", 0.0, 10.0, 0.001),
    "chiller_pressure": ("冷冻水压力", "bar", 0.0, 8.0, 0.001),
    "ambient_temp": ("环境温度", "°C", 0.0, 45.0, 0.01),
    "line_tension": ("收卷张力", "N", 0.0, 300.0, 0.01),
}

FACTORS = [
    {"name": "tdo_z4_temp", "col": "tdo_z4_temp", "unit": "°C", "centre": 200.0,
     "half": 4.0, "recipe_param": "TDO_Z4_TEMP", "node_id": "tdo_z4_temp",
     "plc_tag": "DB10.DBD0", "rounding": 0.1, "hard": (195.0, 205.0),
     "expected_sign": "+", "meaning": "TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升"},
    {"name": "mdo_speed", "col": "mdo_speed", "unit": "m/min", "centre": 320.0,
     "half": 10.0, "recipe_param": "MDO_SPEED", "node_id": "mdo_speed",
     "plc_tag": "DB10.DBD4", "rounding": 0.1, "hard": (300.0, 340.0),
     "expected_sign": "-", "meaning": "MDO 车速：提高纵向拉伸，厚度下降"},
    {"name": "tdo_ratio", "col": "tdo_ratio", "unit": "-", "centre": 3.0,
     "half": 0.1, "recipe_param": "TDO_RATIO", "node_id": "tdo_ratio",
     "plc_tag": "DB10.DBD8", "rounding": 0.01, "hard": (2.7, 3.3),
     "expected_sign": "-", "meaning": "TDO 横向拉伸比：提高横向取向，厚度略降"},
]

RESPONSES = [
    {"name": "thickness_um", "col": "thickness_um", "unit": "um", "goal": "target",
     "lsl": 48.0, "usl": 52.0, "target": 50.0, "weight": 1.0,
     "metric_ref": {"node_id": "thickness_gauge", "aggregation": "steady_mean"}},
    {"name": "haze_pct", "col": "haze_pct", "unit": "%", "goal": "minimize",
     "usl": 2.2, "weight": 0.8,
     "metric_ref": {"node_id": "haze_gauge", "aggregation": "steady_mean"}},
    {"name": "tensile_mpa", "col": "tensile_mpa", "unit": "MPa", "goal": "maximize",
     "lsl": 170.0, "weight": 0.6},
]


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in header})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def iso(ts_ms: int) -> str:
    import datetime as dt
    return (dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"))


def iso_naive(ts_ms: int) -> str:
    """E-1H time catalog form (no millis / no Z) for the derived hetero inputs."""
    import datetime as dt
    return (dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S"))


def write_export(root: Path, run_id: str, start_ms: int, step_ms: int,
                 series: dict[str, list[float]], *, title: str, note: str,
                 line_id: str = "bopet-lineA") -> None:
    root.mkdir(parents=True, exist_ok=True)
    nodes = []
    for nid, vals in series.items():
        name, unit, lo, hi, dec = NODES[nid]
        rows = []
        for i, v in enumerate(vals):
            rows.append({"ts_iso": iso(start_ms + i * step_ms),
                         "ts_ms": start_ms + i * step_ms,
                         "value": f"{v:.6f}", "state": "ok"})
        write_csv(root / "nodes" / f"{nid}.csv",
                  ["ts_iso", "ts_ms", "value", "state"], rows)
        obs = [v for v in vals if math.isfinite(v)]
        nodes.append({
            "id": nid, "name": name, "unit": unit, "line_id": line_id,
            "range": {"min": lo, "max": hi}, "warn": {"low": None, "high": None},
            "interval_ms": step_ms, "decimals": dec,
            "semantics": f"{name}（{unit}）",
            "file": f"nodes/{nid}.csv", "rows": len(vals),
            "value_range_observed": {
                "min": round(min(obs), 4), "max": round(max(obs), 4)} if obs else None,
            "state_summary": {"ok": len(vals)},
        })
    manifest = {
        "schema": "aw.daq-export/1",
        "export_id": f"daqexp-{run_id}",
        "created_at": iso(start_ms + len(next(iter(series.values()))) * step_ms),
        "title": title,
        "note": note,
        "window": {"from_ms": start_ms,
                   "to_ms": start_ms + (len(next(iter(series.values()))) - 1) * step_ms,
                   "from": iso(start_ms),
                   "to": iso(start_ms + (len(next(iter(series.values()))) - 1) * step_ms)},
        "lines": [{"lineId": line_id, "lineName": "BOPET 一号线",
                   "runId": run_id, "productId": "BOPET-12um",
                   "productName": "12 µm 电容膜", "recipeId": "RCP-12A",
                   "recipeName": "12um 标准配方", "recipeVersion": 3}],
        "nodes": nodes,
        "totals": {"files": len(nodes), "rows": len(nodes) * len(next(iter(series.values())))},
        "truncated_nodes": [],
        "usage": "nodes/ 下每标量节点一份全量原始时序 CSV(ts_iso,ts_ms,value,state;无降采样)",
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def smooth_noise(rng, n, sigma, phi=0.55):
    e = rng.normal(0, sigma, n)
    out = np.empty(n)
    out[0] = e[0]
    for i in range(1, n):
        out[i] = phi * out[i - 1] + math.sqrt(1 - phi * phi) * e[i]
    return out


def gen_history() -> None:
    rng = np.random.default_rng(SEED + 1)
    n = 1440
    t = np.arange(n) * 15 / 3600.0
    series = {
        "tdo_z4_temp": 200.0 + smooth_noise(rng, n, 0.12),
        "mdo_speed": 320.0 + smooth_noise(rng, n, 0.35),
        "tdo_ratio": 3.0 + smooth_noise(rng, n, 0.0015),
        "thickness_gauge": 50.0 + smooth_noise(rng, n, 0.07),
        "haze_gauge": 2.0 + smooth_noise(rng, n, 0.035),
        "chiller_pressure": 3.0 + smooth_noise(rng, n, 0.012),
        "ambient_temp": 24.0 + smooth_noise(rng, n, 0.12),
        "line_tension": 120.0 + smooth_noise(rng, n, 0.6),
    }
    series["chiller_pressure"] = 3.0 + 0.008 * (series["tdo_z4_temp"] - 200) \
        + smooth_noise(rng, n, 0.01)
    write_export(CAPTURE / "history", "prod-20261015-night",
                 1792022400000, 15000, series,
                 title="BOPET 一号线 夜班稳定段（哨兵基线）",
                 note="2026-10-15 00:00–06:00 稳定生产，无调整、无停机")


def gen_line() -> None:
    rng = np.random.default_rng(SEED + 2)
    n = 1440
    t = np.arange(n) * 15 / 3600.0  # hours
    step_i = int(n * 0.6)
    drift = 0.9 * t
    temp = 200.0 + drift + smooth_noise(rng, n, 0.13)
    ambient = 24.0 + 1.5 * (np.arange(n) >= step_i) + smooth_noise(rng, n, 0.15)
    tension = 120.0 + 8.0 * (np.arange(n) >= step_i) + smooth_noise(rng, n, 0.8)
    thick = 50.0 - 0.25 * t + smooth_noise(rng, n, 0.08)
    for frac in (0.30, 0.55, 0.80):
        thick[int(n * frac)] += 0.6
    haze = 2.0 + 0.03 * t + smooth_noise(rng, n, 0.04)
    chiller = 3.0 + 0.008 * (temp - 200) + smooth_noise(rng, n, 0.01)
    chiller[int(n * 0.40):int(n * 0.50)] = 3.06
    series = {
        "tdo_z4_temp": temp,
        "mdo_speed": 320.0 + smooth_noise(rng, n, 0.4),
        "tdo_ratio": 3.0 + smooth_noise(rng, n, 0.002),
        "thickness_gauge": thick,
        "haze_gauge": haze,
        "chiller_pressure": chiller,
        "ambient_temp": ambient,
        "line_tension": tension,
    }
    write_export(CAPTURE / "line", "prod-20261016-day",
                 1792137600000, 15000, series,
                 title="BOPET 一号线 白班 08:00–14:00（含异常）",
                 note="10:00 后 Z4 温度持续上爬；11:36 交接班后张力台阶；冷冻水压力表有一段读数不动")


def planted(z_t: float, z_m: float, z_r: float) -> dict[str, float]:
    thick = (50.0 + 1.20 * z_t - 0.90 * z_m - 0.35 * z_r
             - 1.10 * z_t * z_t - 0.80 * z_m * z_m - 0.30 * z_r * z_r
             + 0.50 * z_t * z_m)
    haze = 2.0 + 0.16 * z_t - 0.11 * z_m + 0.04 * z_r + 0.07 * z_t * z_t
    tensile = 185.0 + 6.0 * z_t - 4.0 * z_m + 2.0 * z_r - 3.0 * z_t * z_t
    edge = 0.22 + 0.05 * z_t - 0.03 * z_m
    return {"thickness_um": thick, "haze_pct": haze, "tensile_mpa": tensile,
            "gauge_mean": thick + 0.12, "edge_dev": edge}


def ccd_runs() -> list[dict]:
    """Face-centred CCD alpha=1: 8 corners + 6 axial + 6 centre + 2 repeats."""
    pts = []
    for corner in itertools.product((-1, 1), repeat=3):
        pts.append(corner)
    for axis in range(3):
        for sign in (-1, 1):
            p = [0, 0, 0]
            p[axis] = sign
            pts.append(tuple(p))
    design = []
    for i, (zt, zm, zr) in enumerate(pts):
        design.append({"design_point_id": f"dp-{i + 1:02d}", "z": (zt, zm, zr),
                       "replicate_kind": "extra", "replicate_group": ""})
    for j in range(6):
        design.append({"design_point_id": f"dp-c{j + 1}", "z": (0, 0, 0),
                       "replicate_kind": "center", "replicate_group": "rg-centre"})
    for src, new_id in ((1, "dp-02r"), (6, "dp-07r")):
        d = design[src]
        design.append({"design_point_id": new_id, "z": d["z"],
                       "replicate_kind": "replicate", "replicate_group": f"rg-{d['design_point_id']}"})
    return design


def gen_campaign() -> tuple[list[dict], dict]:
    rng = np.random.default_rng(SEED + 3)
    design = ccd_runs()
    order = list(rng.permutation(len(design)))
    start0 = 1792224000000  # 2026-10-17 08:00Z
    run_rows, qc_rows, profile_rows, note_rows, truth_runs = [], [], [], [], []
    feature_rows = []
    run_index = 0
    for slot, idx in enumerate(order):
        d = design[idx]
        run_id = f"doerun-{slot + 1:03d}"
        zt, zm, zr = d["z"]
        raw = {
            "tdo_z4_temp": FACTORS[0]["centre"] + FACTORS[0]["half"] * zt,
            "mdo_speed": FACTORS[1]["centre"] + FACTORS[1]["half"] * zm,
            "tdo_ratio": FACTORS[2]["centre"] + FACTORS[2]["half"] * zr,
        }
        truth_vals = planted(zt, zm, zr)
        drift = 0.02 * slot  # slow nuisance drift over the campaign
        n = 24
        t = np.arange(n) * 10 / 60.0
        warm = np.clip((t - 0.2) / 0.5, 0, 1)  # first minutes are a transient
        gauge_series = (truth_vals["gauge_mean"] + drift
                        + smooth_noise(rng, n, 0.06) - 0.25 * (1 - warm))
        series = {
            "tdo_z4_temp": raw["tdo_z4_temp"] + smooth_noise(rng, n, 0.08),
            "mdo_speed": raw["mdo_speed"] + smooth_noise(rng, n, 0.25),
            "tdo_ratio": raw["tdo_ratio"] + smooth_noise(rng, n, 0.001),
            "thickness_gauge": gauge_series,
            "haze_gauge": truth_vals["haze_pct"] + smooth_noise(rng, n, 0.025),
            "chiller_pressure": 3.0 + 0.008 * (raw["tdo_z4_temp"] - 200)
            + smooth_noise(rng, n, 0.008),
            "ambient_temp": 24.0 + 0.35 * math.sin(slot / 3) + smooth_noise(rng, n, 0.08),
            "line_tension": 120.0 + 0.5 * slot + smooth_noise(rng, n, 0.4),
        }
        write_export(CAPTURE / "campaign" / "runs" / run_id, run_id,
                     start0 + slot * 300000, 10000, series,
                     title=f"DOE {d['design_point_id']} run {run_id}",
                     note=f"CCD point {d['design_point_id']} block B{slot % 3 + 1}")
        run_rows.append({
            "run_id": run_id, "design_point_id": d["design_point_id"],
            "replicate_group": d["replicate_group"],
            "replicate_kind": d["replicate_kind"],
            "run_order": slot + 1, "block": f"B{slot % 3 + 1}",
            **{k: round(v, 4) for k, v in raw.items()},
        })
        qc_rows.append({
            "run_id": run_id,
            "thickness_um": f"{truth_vals['thickness_um'] + drift + rng.normal(0, 0.18):.4f}",
            "haze_pct": f"{truth_vals['haze_pct'] + rng.normal(0, 0.05):.4f}",
            "tensile_mpa": f"{truth_vals['tensile_mpa'] + rng.normal(0, 1.6):.3f}",
            "measured_at": iso(start0 + slot * 300000 + 600000),
        })
        # 63-point TD thickness profile at run end
        x = np.linspace(0, 1, PROFILE_POINTS)
        shape = truth_vals["edge_dev"] * (np.exp(-x / 0.04) + np.exp(-(1 - x) / 0.04))
        bow = 0.08 * np.sin(np.pi * x)
        prof = truth_vals["thickness_um"] + shape + bow + rng.normal(0, 0.012, PROFILE_POINTS)
        end_ms = start0 + slot * 300000 + (n - 1) * 10000
        for k, v in enumerate(prof):
            profile_rows.append({"时间": iso_naive(end_ms), "位置": k, "值": f"{v:.5f}",
                                 "run_id": run_id})
        note_rows.append({"时间": iso_naive(end_ms), "run_id": run_id,
                          "备注": f"{run_id} {d['design_point_id']}："
                                  + ("中心点复测" if d["replicate_kind"] == "center"
                                     else "首件膜面正常" if slot % 2 == 0
                                     else "边缘轻微波动，已记录")})
        feature_rows.append({
            "run_id": run_id,
            "HX-PROF-PROFILES-MEAN": f"{float(np.mean(prof)):.6f}",
            "HX-PROF-PROFILES-STD": f"{float(np.std(prof, ddof=1)):.6f}",
            "HX-PROF-PROFILES-EDGE-L-DEV": f"{float(np.mean(prof[:3]) - np.mean(prof)):.6f}",
        })
        truth_runs.append({"run_id": run_id, "design_point_id": d["design_point_id"],
                           "coded": [zt, zm, zr], "raw": raw,
                           "planted": truth_vals, "block": f"B{slot % 3 + 1}"})
    write_csv(CAPTURE / "campaign" / "trial_design.csv",
              ["run_id", "design_point_id", "replicate_group", "replicate_kind",
               "run_order", "block", "tdo_z4_temp", "mdo_speed", "tdo_ratio"],
              run_rows)
    write_csv(CAPTURE / "campaign" / "qc_measurements.csv",
              ["run_id", "thickness_um", "haze_pct", "tensile_mpa", "measured_at"],
              qc_rows)
    write_csv(CAPTURE / "hetero" / "profiles.csv",
              ["时间", "位置", "值", "run_id"], profile_rows)
    write_csv(CAPTURE / "hetero" / "notes.csv", ["时间", "备注"], note_rows)
    write_csv(CAPTURE / "campaign" / "hetero_features.csv",
              ["run_id", "HX-PROF-PROFILES-MEAN", "HX-PROF-PROFILES-STD",
               "HX-PROF-PROFILES-EDGE-L-DEV"], feature_rows)
    # anchor for E-1H: one row per run end (the profile/note timestamp)
    anchor_rows = [{"时间": r["时间"], "run_id": r["run_id"]} for r in note_rows]
    anchor_rows.sort(key=lambda r: r["时间"])
    write_csv(CAPTURE / "hetero" / "anchor.csv", ["时间", "run_id"], anchor_rows)

    # gradient-derived stationary point for thickness (coded)
    # d/dz_t: 1.20 - 2.20 z_t + 0.50 z_m = 0 ; d/dz_m: -0.90 - 1.60 z_m + 0.50 z_t = 0
    a = np.array([[2.20, -0.50], [-0.50, 1.60]])
    b = np.array([1.20, -0.90])
    zt_opt, zm_opt = np.linalg.solve(a, b)
    return truth_runs, {
        "stationary_thickness_coded": [float(zt_opt), float(zm_opt), 0.0],
        "stationary_thickness_raw": {
            "tdo_z4_temp": FACTORS[0]["centre"] + FACTORS[0]["half"] * float(zt_opt),
            "mdo_speed": FACTORS[1]["centre"] + FACTORS[1]["half"] * float(zm_opt),
            "tdo_ratio": FACTORS[2]["centre"],
        },
    }


def write_mapping() -> None:
    mapping = {
        "contract_version": "1.0",
        "experiment_id": "doe-aws-bopet-ccd-20261017",
        "campaign_id": "camp-aws-bopet-1",
        "round_no": 1,
        "line_id": "bopet-lineA",
        "product_id": "BOPET-12um",
        "recipe_id": "RCP-12A",
        "objective": "在厚度 50±2 µm、雾度 ≤2.2% 的约束下提高拉伸强度并稳定厚度：给出可执行的联合设定点与下一轮设计",
        "design_type_declared": "rsm_ccd",
        "trial_design_file": "trial_design.csv",
        "qc_file": "qc_measurements.csv",
        "features_file": "hetero_features.csv",
        "runs_dir": "runs",
        "aggregation": {"method": "steady_mean", "warmup_trim": 0.2,
                        "state_filter": ["ok"], "min_rows": 8},
        "factors": [
            {"name": f["name"], "col": f["col"], "type": "numeric", "unit": f["unit"],
             "min": f["centre"] - f["half"], "max": f["centre"] + f["half"],
             "role": "control", "expected_sign": f["expected_sign"],
             "physical_meaning": f["meaning"],
             "platform_ref": {
                 "recipe_param": f["recipe_param"], "node_id": f["node_id"],
                 "plc_tag": f["plc_tag"], "unit": f["unit"],
                 "unit_conversion": 1.0, "rounding": f["rounding"],
                 "hard_limits": {"min": f["hard"][0], "max": f["hard"][1],
                                 "reason": "设备安全限（本体资产）"}}}
            for f in FACTORS
        ],
        "responses": [
            {"name": r["name"], "col": r["col"], "unit": r["unit"],
             "goal": r["goal"], "lsl": r.get("lsl"), "usl": r.get("usl"),
             "target": r.get("target"), "weight": r["weight"],
             "platform_metric_ref": r.get("metric_ref")}
            for r in RESPONSES
        ] + [
            {"name": "gauge_mean", "col": "gauge_mean", "source": "node",
             "node": "thickness_gauge", "unit": "um", "goal": "target",
             "lsl": 48.0, "usl": 52.0, "target": 50.0, "weight": 0.5},
            {"name": "edge_dev", "col": "HX-PROF-PROFILES-EDGE-L-DEV", "source": "qc",
             "unit": "um", "goal": "minimize", "weight": 0.5},
        ],
        "covariates": [
            {"name": "ambient_temp", "col": "ambient_temp", "source": "node",
             "node": "ambient_temp", "unit": "°C"},
        ],
        "blocks": ["block"],
        "constraints": [
            {"factor": "tdo_z4_temp", "type": "box", "min": 195.0, "max": 205.0,
             "hard": True, "reason": "TDO 加热区安全限", "source": "ontology"},
            {"type": "linear", "coefficients": {"tdo_z4_temp": 1.0, "tdo_ratio": 10.0},
             "rhs": 235.0, "hard": True, "reason": "总热负荷与横向拉伸上限", "source": "ontology"},
        ],
        # the recipe in force when the trial started: a corner that runs thin
        "current_setpoint": {"tdo_z4_temp": 196.0, "mdo_speed": 330.0, "tdo_ratio": 3.1},
        "baseline_source": "platform_recipe",
        "design_region": {
            "factorial_bounds": {f["col"]: [f["centre"] - f["half"], f["centre"] + f["half"]]
                                 for f in FACTORS},
            "axial_alpha": 1.0,
            "design_hull": "ccd_star",
        },
        "ontology": {"profile": "doe", "mode": "auto",
                     "scene_key": "bopet-lineA-12um-tdo",
                     "data_stage": "collected"},
    }
    (CAPTURE / "campaign" / "mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    if CAPTURE.exists() and not args.force:
        print(f"[skip] {CAPTURE} exists (use --force to regenerate)")
        return 0
    if CAPTURE.exists():
        shutil.rmtree(CAPTURE)
    gen_history()
    gen_line()
    truth_runs, stationary = gen_campaign()
    write_mapping()
    truth = {
        "scenario": "BOPET 12 µm TDO/MDO face-centred CCD, captured as AgentWorkShop DAQ exports",
        "seed": SEED,
        "line_id": "bopet-lineA",
        "design": {
            "type": "rsm_ccd", "alpha": 1.0, "factorial": "2^3",
            "n_executions": len(truth_runs), "n_distinct": 15,
            "n_centre_executions": 6, "n_axial": 6, "n_repeats": 2,
            "n_blocks": 3,
        },
        "factors": {f["col"]: {"centre": f["centre"], "half": f["half"],
                               "unit": f["unit"], "hard": list(f["hard"])}
                    for f in FACTORS},
        "planted_surface": {
            "thickness_um": {"intercept": 50.0, "zt": 1.20, "zm": -0.90, "zr": -0.35,
                             "zt2": -1.10, "zm2": -0.80, "zr2": -0.30, "zt_zm": 0.50},
            "haze_pct": {"intercept": 2.0, "zt": 0.16, "zm": -0.11, "zr": 0.04, "zt2": 0.07},
            "tensile_mpa": {"intercept": 185.0, "zt": 6.0, "zm": -4.0, "zr": 2.0, "zt2": -3.0},
            "edge_dev": {"intercept": 0.22, "zt": 0.05, "zm": -0.03},
        },
        "stationary": stationary,
        "anomaly": {
            "window": "line/ 2026-10-16 08:00-14:00",
            "z4_drift_c_per_h": 0.9,
            "tension_step_at_fraction": 0.6, "tension_step_n": 8.0,
            "ambient_step_at_fraction": 0.6, "ambient_step_c": 1.5,
            "thickness_spikes_at_fraction": [0.30, 0.55, 0.80],
            "chiller_frozen_fraction": [0.40, 0.50],
        },
        "runs": truth_runs,
    }
    (HERE / "scenario_truth.json").write_text(
        json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    n_files = sum(1 for _ in CAPTURE.rglob("*") if _.is_file())
    print(f"[capture] {n_files} files under {CAPTURE}")
    print(f"[capture] stationary (coded) = {stationary['stationary_thickness_coded']}")
    print(f"[capture] stationary (raw)   = {stationary['stationary_thickness_raw']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
