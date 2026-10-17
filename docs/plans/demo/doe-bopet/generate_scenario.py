#!/usr/bin/env python
"""generate_scenario.py — a realistic, deterministic BOPET trial dataset.

Scenario: a 12 µm BOPET film line ran a face-centred CCD (α = 1) over the TDO /
MDO window to pull film thickness back into 50 ± 2 µm while keeping haze under
1.8 %. 22 executions across 3 production sessions, including 6 centre points and
2 repeated corner runs.

What makes it realistic rather than a toy matrix:

* a **constrained operating region** — the safe window has hard limits, so a
  rotatable CCD (α = 1.682) would have placed its axial runs outside them; a
  face-centred CCD (α = 1) keeps every execution inside;
* **batch structure** — three sessions with a small, real batch offset;
* **replicates** — 6 centre points plus 2 repeats of corner points (pure error);
* **one failed measurement** — a gauge fault left one thickness cell empty; the
  data contract allows it, so it must be disclosed and never imputed;
* **ambient temperature** declared as a covariate with no true effect;
* **two undeclared columns** — `chiller_pressure`, almost exactly a linear
  function of the TDO zone temperature (so a naive screen "finds" an effect), and
  `shift_handover_min`, pure noise. Neither may reach a recommendation.

The planted surface is written to `scenario_truth.json` and is the ground truth
this demo checks the analyzer against.

Usage:
    uv run --project .claude/shared/scripts python docs/plans/demo/doe-bopet/generate_scenario.py
Idempotent: writes only when the bytes change.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INPUT = HERE / "00_input"
SEED = 20261017
ALPHA = 1.0  # face-centred CCD: every run stays inside the safe window

FACTOR_ORDER = ("tdo_z4_temp", "mdo_speed", "tdo_ratio")
FACTORS = {                      # name -> (centre, half-range, unit)
    "tdo_z4_temp": (200.0, 4.0, "\u00b0C"),
    "mdo_speed": (320.0, 10.0, "m/min"),
    "tdo_ratio": (3.00, 0.10, "-"),
}
B_THICK = {"zt": 1.30, "zm": -0.95, "zr": -0.35,
           "zt2": -1.10, "zm2": -0.85, "zr2": -0.45, "zt_zm": 0.60}
F_THICK = 50.0
B_HAZE = {"zt": 0.15, "zt2": 0.22, "zm2": 0.30, "zr2": 0.10}
F_HAZE = 1.45
SIGMA_THICK = 0.18
SIGMA_HAZE = 0.035
BATCH_OFFSET = {"B1": 0.06, "B2": -0.05, "B3": 0.02}

CUBE = [(-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (-1, 1, 1), (1, 1, 1)]
AXIAL = [(ALPHA, 0, 0), (-ALPHA, 0, 0), (0, ALPHA, 0),
         (0, -ALPHA, 0), (0, 0, ALPHA), (0, 0, -ALPHA)]
N_CENTRE = 6
REPEATED = ("dp-02", "dp-07")     # corners re-run for an independent error estimate


def raw_of(coded, names=FACTOR_ORDER):
    out = {}
    for name, c in zip(names, coded):
        centre, half, _u = FACTORS[name]
        out[name] = round(centre + half * c, 4)
    return out


def thick_of(coded, batch_offset=0.0):
    zt, zm, zr = coded
    return (F_THICK + B_THICK["zt"] * zt + B_THICK["zm"] * zm + B_THICK["zr"] * zr
            + B_THICK["zt2"] * zt ** 2 + B_THICK["zm2"] * zm ** 2
            + B_THICK["zr2"] * zr ** 2 + B_THICK["zt_zm"] * zt * zm + batch_offset)


def haze_of(coded):
    zt, zm, zr = coded
    return (F_HAZE + B_HAZE["zt"] * zt + B_HAZE["zt2"] * zt ** 2
            + B_HAZE["zm2"] * zm ** 2 + B_HAZE["zr2"] * zr ** 2)


def design_points():
    """Unique factor combinations: design_point_id groups identical coded rows."""
    pts = []
    for coded in CUBE:
        pts.append({"coded": coded, "kind": "corner"})
    for coded in AXIAL:
        pts.append({"coded": coded, "kind": "axial"})
    pts.append({"coded": (0.0, 0.0, 0.0), "kind": "centre"})   # one point, 6 executions
    for i, p in enumerate(pts, start=1):
        p["dp"] = f"dp-{i:02d}"
    return pts


def executions(pts):
    """One entry per EXECUTION; centre points and repeats share their design point."""
    ex = []
    for p in pts:
        if p["kind"] == "centre":
            for k in range(N_CENTRE):
                ex.append({**p, "rep": k + 1, "replicate_kind": "center"})
        else:
            ex.append({**p, "rep": 1, "replicate_kind": "extra"})
    for dp in REPEATED:
        base = next(p for p in pts if p["dp"] == dp)
        ex.append({**base, "rep": 2, "replicate_kind": "replicate"})
    return ex


def main() -> int:
    rng = np.random.default_rng(SEED)
    pts = design_points()
    ex = executions(pts)

    # ---- execution order: a real randomization, then split into 3 sessions
    perm = rng.permutation(len(ex))
    block_of = {}
    for pos, idx in enumerate(perm):
        block_of[int(idx)] = "B1" if pos < 8 else ("B2" if pos < 16 else "B3")

    rows, runs_truth = [], []
    gauge_fault = None
    for idx, e in enumerate(ex):
        block = block_of[idx]
        coded = e["coded"]
        raw = raw_of(coded)
        thick = thick_of(coded, BATCH_OFFSET[block])
        haze = haze_of(coded)
        t_obs = thick + float(rng.normal(0.0, SIGMA_THICK))
        h_obs = haze + float(rng.normal(0.0, SIGMA_HAZE))
        run_id = f"doerun-{idx + 1:03d}"
        if idx == 5:                      # the gauge fault
            gauge_fault = run_id
            thickness = ""
        else:
            thickness = round(t_obs, 3)
        rows.append({
            "run_id": run_id,
            "design_point_id": e["dp"],
            "replicate_group": f"rg-{e['dp']}" if e["replicate_kind"] != "extra" else "",
            "replicate_kind": e["replicate_kind"],
            "run_order": idx + 1,
            "block": block,
            **raw,
            "thickness_um": thickness,
            "haze_pct": round(h_obs, 4),
            "ambient_temp": round(24.5 + float(rng.normal(0.0, 0.35)), 3),
            "chiller_pressure": round(3.20 + 0.055 * (raw["tdo_z4_temp"] - 200.0)
                                      + float(rng.normal(0.0, 0.008)), 4),
            "shift_handover_min": int(rng.integers(4, 19)),
        })
        runs_truth.append({"run_id": run_id, "design_point_id": e["dp"], "block": block,
                           "coded": list(coded),
                           "thickness_noiseless": round(thick, 4),
                           "haze_noiseless": round(haze, 4)})

    fields = ["run_id", "design_point_id", "replicate_group", "replicate_kind",
              "run_order", "block", *FACTOR_ORDER, "thickness_um", "haze_pct",
              "ambient_temp", "chiller_pressure", "shift_handover_min"]
    write_csv(INPUT / "run_table.csv", fields, rows)
    write_json(INPUT / "doe_context.json", doe_context())
    (INPUT / "experiment_notes.md").write_text(notes(gauge_fault), encoding="utf-8")

    # ---- analytic truth: the stationary point of the planted thickness surface
    hess = np.array([[2.0 * B_THICK["zt2"], B_THICK["zt_zm"]],
                     [B_THICK["zt_zm"], 2.0 * B_THICK["zm2"]]])
    grad = np.array([B_THICK["zt"], B_THICK["zm"]])
    zt_s, zm_s = np.linalg.solve(hess, -grad)
    zr_s = -B_THICK["zr"] / (2.0 * B_THICK["zr2"])
    sp_coded = tuple(round(float(v), 4) for v in (zt_s, zm_s, zr_s))
    sp_raw = raw_of(sp_coded)
    truth = {
        "scenario": "BOPET 12um TDO/MDO trial — face-centred CCD (alpha=1), 3 sessions",
        "seed": SEED,
        "design": {"type": "rsm_ccd", "alpha": ALPHA, "factorial": "2^3",
                   "n_centre_executions": N_CENTRE, "n_axial": 6,
                   "n_repeats": len(REPEATED), "n_executions": len(rows),
                   "n_distinct_combinations": len(pts), "n_blocks": 3,
                   "note": "face-centred so every execution stays inside the hard limits"},
        "factors": {k: {"centre": v[0], "half_range": v[1], "unit": v[2]}
                    for k, v in FACTORS.items()},
        "planted_surface": {
            "thickness_um": {"intercept": F_THICK,
                             **{f"b_{k}": v for k, v in B_THICK.items()}},
            "haze_pct": {"intercept": F_HAZE, **{f"b_{k}": v for k, v in B_HAZE.items()}},
            "noise_sigma": {"thickness_um": SIGMA_THICK, "haze_pct": SIGMA_HAZE},
            "batch_offsets": BATCH_OFFSET,
            "convention": "zt/zm/zr are coded coordinates in [-1, 1]",
        },
        "expected_stationary_point_coded": dict(zip(FACTOR_ORDER, sp_coded)),
        "expected_stationary_point_raw": sp_raw,
        "expected_at_stationary_point": {"thickness_um": round(thick_of(sp_coded), 4),
                                         "haze_pct": round(haze_of(sp_coded), 4)},
        "expected_stationary_point_in_design_region": True,
        "expected_significant_thickness_terms": ["tdo_z4_temp", "mdo_speed",
                                                 "tdo_z4_temp^2", "mdo_speed^2",
                                                 "tdo_z4_temp:mdo_speed"],
        "expected_significant_haze_terms": ["mdo_speed^2", "tdo_z4_temp^2"],
        "expected_null_effects": {
            "ambient_temp": ("declared covariate, no true effect — may still test "
                             "significant by chance at alpha=0.05; it must stay "
                             "immaterial (|std_effect| far below the real factors) and "
                             "must never reach a window / setpoint / recipe patch"),
            "chiller_pressure": "collinear with tdo_z4_temp — must not be recommended",
            "shift_handover_min": "pure noise — must not be recommended",
        },
        "expected_recommendation": {"actionable": True,
                                    "thickness_within": [48.0, 52.0],
                                    "haze_ceiling": 1.8,
                                    "hard_limits_respected": True},
        "data_quality": {"failed_measurement_run": gauge_fault, "empty_cells": 1,
                         "note": "allowed by the data contract; must be disclosed"},
        "runs": runs_truth,
    }
    write_json(HERE / "scenario_truth.json", truth)
    print(f"[scenario] {len(rows)} executions over {len(pts)} distinct factor "
          f"combinations, {len(FACTORS)} factors, 2 responses, 3 sessions")
    print(f"[scenario] failed measurement: {gauge_fault}")
    print(f"[scenario] planted stationary point coded={sp_coded} raw={sp_raw}")
    return 0


def doe_context() -> dict:
    return {
        "contract_version": "1.1",
        "experiment_id": "doe-bopet-tdo-2026q4-r3",
        "line_id": "L5-bopet",
        "product_id": "film-12um",
        "recipe_id": "rcp-bopet-12um-v3",
        "objective": ("在安全窗口内寻找 TDO/MDO 工况，使厚度落在 50\u00b12 \u00b5m 的同时"
                      "抑制雾度（\u22641.8%），并给出下一轮布点建议"),
        "design_type_declared": "ccd",
        "data_stage": "collected",
        "design_region": {
            "factorial_bounds": {"tdo_z4_temp": [196, 204], "mdo_speed": [310, 330],
                                 "tdo_ratio": [2.9, 3.1]},
            "axial_alpha": ALPHA,
            "design_hull": "ccd_star",
        },
        "data_file": "run_table.csv",
        "factors": [
            {"name": "tdo_z4_temp", "col": "tdo_z4_temp", "type": "numeric",
             "unit": "\u00b0C", "min": 196, "max": 204, "levels": None,
             "role": "control", "expected_sign": "-",
             "physical_meaning": ("TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，"
                                  "直接影响厚度与雾度"),
             "ontology_signal": "TDO_Z4_SETPOINT",
             "platform_ref": {"recipe_param": "tdo_z4_temp", "node_id": "dw-tdo-z4",
                              "plc_tag": "TDO_Z4_SP", "unit": "\u00b0C",
                              "unit_conversion": 1.0, "rounding": 0.1,
                              "hard_limits": {"min": 195, "max": 205}}},
            {"name": "mdo_speed", "col": "mdo_speed", "type": "numeric",
             "unit": "m/min", "min": 310, "max": 330, "levels": None,
             "role": "control", "expected_sign": "-",
             "physical_meaning": "MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度",
             "ontology_signal": "MD_LINE_SPEED",
             "platform_ref": {"recipe_param": "mdo_speed", "node_id": "dw-mdo-01",
                              "plc_tag": "MDO_SPEED_SP", "unit": "m/min",
                              "unit_conversion": 1.0, "rounding": 0.5,
                              "hard_limits": {"min": 305, "max": 335}}},
            {"name": "tdo_ratio", "col": "tdo_ratio", "type": "numeric",
             "unit": "-", "min": 2.9, "max": 3.1, "levels": None,
             "role": "control", "expected_sign": "+",
             "physical_meaning": "TDO 纵横向拉伸比，影响厚度均匀性",
             "ontology_signal": "TDO_STRETCH_RATIO",
             "platform_ref": {"recipe_param": "tdo_ratio", "node_id": "dw-tdo-01",
                              "plc_tag": "TDO_RATIO_SP", "unit": "-",
                              "unit_conversion": 1.0, "rounding": 0.01,
                              "hard_limits": {"min": 2.85, "max": 3.15}}},
        ],
        "responses": [
            {"name": "thickness_um", "col": "thickness_um", "unit": "um",
             "goal": "target", "lsl": 48.0, "usl": 52.0, "target": 50.0, "weight": 1.0,
             "ontology_signal": "FILM_THICKNESS_MEAN",
             "platform_metric_ref": {"node_id": "dn-thk-01", "aggregation": "steady_mean"}},
            {"name": "haze_pct", "col": "haze_pct", "unit": "%",
             "goal": "minimize", "lsl": None, "usl": 1.8, "target": None, "weight": 0.5,
             "ontology_signal": "FILM_HAZE",
             "platform_metric_ref": {"node_id": "dn-haze-01", "aggregation": "steady_mean"}},
        ],
        "blocks": ["block"],
        "covariates": ["ambient_temp"],
        "constraints": [
            {"factor": "tdo_z4_temp", "type": "box", "min": 195, "max": 205, "hard": True,
             "reason": "\u5b89\u5168\u4e0e\u819c\u9762\u7f3a\u9677\u9650", "source": "ontology"},
            {"factor": "mdo_speed", "type": "box", "min": 305, "max": 335, "hard": True,
             "reason": "\u8bbe\u5907\u8bbe\u5b9a\u4e0a\u4e0b\u9650", "source": "platform"},
            {"factor": "tdo_ratio", "type": "box", "min": 2.85, "max": 3.15, "hard": True,
             "reason": "\u5de5\u827a\u7a97\u53e3\u9650", "source": "platform"},
        ],
        "replicates_col": "replicate_group",
        "run_order_col": "run_order",
        "group_col": "run_id",
        "time_col": None,
        "current_setpoint": {"tdo_z4_temp": 200, "mdo_speed": 320, "tdo_ratio": 3.0},
        "baseline_source": "platform_recipe",
        "ontology": {"profile": "doe", "mode": "auto",
                     "scene_key": "bopet-tdo-thickness", "version": None,
                     "data_stage": "collected"},
        "provenance": {"platform": "RecipeWorkShop", "created_by": "doe-bopet-demo",
                       "created_at": "2026-10-17T09:00:00+08:00"},
    }


def notes(gauge_fault) -> str:
    return f"""# 试验记录（BOPET 12µm · TDO/MDO 工况窗口）

## 1. 目的
产线反馈近两周 12 µm 膜厚波动偏大、雾度偶发超上限。本轮试验在**安全窗口内**
寻找 TDO Z4 温度 / MDO 线速 / TDO 拉伸比 的工况组合，使厚度稳定在 50±2 µm 的
同时把雾度压到 1.8% 以下，并为下一轮布点提供依据。

## 2. 试验设计
- 因子 3 个，均为连续量：`tdo_z4_temp`（196–204 °C）、`mdo_speed`（310–330 m/min）、
  `tdo_ratio`（2.90–3.10）。
- 因为安全窗口有硬限（TDO Z4 195–205 °C，超出会触发膜面缺陷），**没有采用可旋转 CCD
  （α=1.682 会把轴向点放到窗口外），改用面心 CCD（α=1）**，所有执行点都落在硬限内。
- 8 个角点 + 6 个轴向点 + 6 次中心点执行；另外在 dp-02、dp-07 各多做 1 次独立重复，
  用于估计纯误差。
- 22 次执行分 3 个生产班次（block = B1/B2/B3），执行顺序按随机化排定后拆分。
- 响应：`thickness_um`（目标 50，规格 48–52）、`haze_pct`（越小越好，上限 1.8）。
- 附带记录：车间环境温度 `ambient_temp`；冷冻机压力 `chiller_pressure`（仪表记录，
  随 TDO 温度联动）；交接班时长 `shift_handover_min`（生产记录，与工艺无关）。

## 3. 执行与异常
- 全部 22 次执行完成，无停机。
- **`{gauge_fault}` 的厚度测厚仪读数丢失**（探头报错），该格留空未补测，未做插补。
- 班次间环境温度 23.5–25.5 °C，未超出正常范围。

## 4. 交付物
- `run_table.csv`：一行 = 一次执行。
- `doe_context.json`：因子/响应/规格/硬限/平台映射（RecipeWorkShop 导出）。
"""


def write_csv(path: Path, fields, rows) -> None:
    lines = [",".join(fields)]
    for r in rows:
        lines.append(",".join("" if r.get(f) is None else str(r.get(f)) for f in fields))
    text = "\n".join(lines) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
