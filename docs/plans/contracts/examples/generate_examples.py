#!/usr/bin/env python
"""Deterministically generate the frozen contract examples.

Run from anywhere:
    uv run --project .claude/shared/scripts python docs/plans/contracts/examples/generate_examples.py

Writes next to this file:
    run_table.csv            design_only  (responses present as columns but empty)
    run_table_collected.csv  collected    (values, replicates, blocks, one empty cell)
    doe_context.json         design_only platform context
    doe_context_collected.json  collected platform context

Deterministic: no RNG, no clock. Re-running yields byte-identical files.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- design: CCD k=3, alpha=1.682, 6 center points -------------------------
FACTORS = {
    "zone1_temp": {"center": 200.0, "half": 20.0, "unit": "\u00b0C"},
    "line_speed": {"center": 320.0, "half": 40.0, "unit": "m/min"},
    "tdo_ratio": {"center": 3.0, "half": 0.5, "unit": "-"},
}
ALPHA = 1.682

CUBE = [
    (-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (-1, 1, 1), (1, 1, 1),
]
AXIAL = [
    (ALPHA, 0, 0), (-ALPHA, 0, 0), (0, ALPHA, 0),
    (0, -ALPHA, 0), (0, 0, ALPHA), (0, 0, -ALPHA),
]
CENTER = [(0, 0, 0)] * 6

# deterministic, non-monotonic execution order (a proper randomization draw would
# come from the platform; this is a fixed permutation so the example is reproducible)
RUN_PERMUTATION = [0, 5, 12, 3, 18, 9, 1, 14, 7, 2, 16, 11, 4, 19, 8, 13, 6, 17, 10, 15]


def raw_values(coded: tuple[float, float, float]) -> dict[str, float]:
    out = {}
    for (name, spec), c in zip(FACTORS.items(), coded):
        out[name] = round(spec["center"] + spec["half"] * c, 3)
    return out


def design_points() -> list[dict]:
    pts = []
    for i, coded in enumerate(CUBE + AXIAL + CENTER, start=1):
        pts.append({
            "design_point_id": f"dp-{i:02d}",
            "coded": coded,
            "kind": "center" if coded == (0, 0, 0) else ("axial" if 0 in coded and coded != (0, 0, 0) else "cube"),
        })
    return pts


def truth_thickness(raw: dict[str, float]) -> float:
    """Second-order response surface used only to make the example numbers plausible."""
    z = (raw["zone1_temp"] - 200.0) / 20.0
    s = (raw["line_speed"] - 320.0) / 40.0
    r = (raw["tdo_ratio"] - 3.0) / 0.5
    y = (50.0
         - 1.6 * z + 1.1 * s + 0.45 * r
         - 1.9 * z * z - 1.2 * s * s - 0.7 * r * r
         + 0.8 * z * s - 0.3 * z * r)
    return round(y, 3)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


BASE_FIELDS = ["run_id", "design_point_id", "replicate_group", "replicate_kind",
               "run_order", "block", "zone1_temp", "line_speed", "tdo_ratio"]
RESP_FIELDS = ["thickness_um", "haze_pct"]


def build_design_only() -> list[dict]:
    rows = []
    for i, pt in enumerate(design_points(), start=1):
        raw = raw_values(pt["coded"])
        rows.append({
            "run_id": f"doerun-{i:02d}",
            "design_point_id": pt["design_point_id"],
            "replicate_group": "" if pt["kind"] != "center" else f"rg-{pt['design_point_id']}",
            "replicate_kind": pt["kind"],
            "run_order": i,
            "block": "1",
            **raw,
            "thickness_um": "",
            "haze_pct": "",
        })
    return rows


def build_collected() -> list[dict]:
    """Cube/axial points get one independent replicate; two cube points get a third.
    One response cell is left empty on purpose (failed measurement)."""
    pts = design_points()
    extra = {
        "dp-01": 2, "dp-04": 2, "dp-06": 1, "dp-11": 1, "dp-12": 1,
    }
    plan: list[tuple[dict, int]] = []
    for pt in pts:
        reps = 1 + extra.get(pt["design_point_id"], 0)
        if pt["kind"] == "center":
            reps = 6  # centre points are independent repeats already present in the design
        for k in range(reps):
            plan.append((pt, k))

    order = RUN_PERMUTATION + list(range(len(RUN_PERMUTATION), len(plan)))
    seq = 0
    rows = []
    for idx, (pt, k) in enumerate(plan):
        raw = raw_values(pt["coded"])
        y = truth_thickness(raw)
        # deterministic replicate offsets (no RNG): alternating small shifts
        offset = [0.0, 0.21, -0.17, 0.09, -0.12, 0.15][k % 6]
        thickness = round(y + offset, 3)
        haze = round(1.35 + 0.12 * abs((raw["zone1_temp"] - 200.0) / 20.0) + 0.05 * k, 3)
        seq += 1
        run_id = f"doerun-{seq:03d}"
        # plant one failed measurement (empty cell) — contract §1 allows it
        if run_id == "doerun-004":
            thickness = ""
        rows.append({
            "run_id": run_id,
            "design_point_id": pt["design_point_id"],
            "replicate_group": f"rg-{pt['design_point_id']}",
            "replicate_kind": "center" if pt["kind"] == "center" else "replicate",
            "run_order": order[idx] + 1,
            "block": "1" if idx < len(order) else "2",
            **raw,
            "thickness_um": thickness,
            "haze_pct": haze,
        })
    return rows


def doe_context_collected() -> dict:
    ctx = doe_context(design_only=False)
    return ctx


def doe_context(*, design_only: bool) -> dict:
    return {
        "contract_version": "1.1",
        "experiment_id": "doe-bopet-tdo-ccd-2026q4",
        "line_id": "L5-bopet",
        "product_id": "film-12um",
        "recipe_id": "rcp-bopet-12um-v3",
        "objective": "\u5c06\u539a\u5ea6\u7a33\u5b9a\u5728 50\u00b11.5um \u7684\u540c\u65f6\u4f4e\u4e8e\u96fe\u5ea6\u4e0a\u9650",
        "design_type_declared": "ccd",
        "data_stage": "design_only" if design_only else "collected",
        "design_region": {
            "factorial_bounds": {
                "zone1_temp": [180, 220],
                "line_speed": [280, 360],
                "tdo_ratio": [2.5, 3.5],
            },
            "axial_alpha": ALPHA,
            "design_hull": "ccd_star",
        },
        "data_file": "run_table.csv" if design_only else "run_table_collected.csv",
        "factors": [
            {
                "name": "zone1_temp", "col": "zone1_temp", "type": "numeric",
                "unit": "\u00b0C", "min": 180, "max": 220, "levels": None,
                "role": "control", "expected_sign": "+",
                "physical_meaning": "TDO \u5317\u4fa7 Z4 \u52a0\u70ed\u533a\u6e29\u5ea6\uff0c\u4e3b\u5bfc\u5f20\u529b\u4e0e\u539a\u5ea6",
                "ontology_signal": "TDO_Z4_SETPOINT",
                "platform_ref": {
                    "recipe_param": "zone1_temp", "node_id": "dw-tdo-z4",
                    "plc_tag": "TDO_Z4_SP", "unit_conversion": 1.0, "rounding": 0.1,
                    "hard_limits": {"min": 185, "max": 215},
                },
            },
            {
                "name": "line_speed", "col": "line_speed", "type": "numeric",
                "unit": "m/min", "min": 280, "max": 360, "levels": None,
                "role": "control", "expected_sign": "-",
                "physical_meaning": "\u7ebf\u901f\u4e0e\u5f20\u529b\u8026\u5408\uff0c\u63d0\u901f\u4f1a\u8584\u5316",
                "ontology_signal": "MD_LINE_SPEED",
                "platform_ref": {
                    "recipe_param": "line_speed", "node_id": "dw-mdo-01",
                    "plc_tag": "MDO_SPEED_SP", "unit_conversion": 1.0, "rounding": 0.5,
                    "hard_limits": {"min": 290, "max": 350},
                },
            },
            {
                "name": "tdo_ratio", "col": "tdo_ratio", "type": "numeric",
                "unit": "-", "min": 2.5, "max": 3.5, "levels": None,
                "role": "control", "expected_sign": "+",
                "physical_meaning": "TDO \u7eb5\u6a2a\u5411\u62c9\u4f38\u6bd4",
                "ontology_signal": "TDO_STRETCH_RATIO",
                "platform_ref": {
                    "recipe_param": "tdo_ratio", "node_id": "dw-tdo-01",
                    "plc_tag": "TDO_RATIO_SP", "unit_conversion": 1.0, "rounding": 0.01,
                    "hard_limits": {"min": 2.6, "max": 3.4},
                },
            },
        ],
        "responses": [
            {
                "name": "thickness_um", "col": "thickness_um", "unit": "um",
                "goal": "target", "lsl": 48.0, "usl": 52.0, "target": 50.0, "weight": 1.0,
                "ontology_signal": "FILM_THICKNESS_MEAN",
                "platform_metric_ref": {"node_id": "dn-thk-01", "aggregation": "steady_mean"},
            },
            {
                "name": "haze_pct", "col": "haze_pct", "unit": "%",
                "goal": "minimize", "lsl": None, "usl": 1.8, "target": None, "weight": 0.5,
                "ontology_signal": "FILM_HAZE",
                "platform_metric_ref": {"node_id": "dn-haze-01", "aggregation": "steady_mean"},
            },
        ],
        "blocks": ["block"],
        "covariates": [],
        "constraints": [
            {"factor": "zone1_temp", "type": "box", "min": 185, "max": 215,
             "hard": True, "reason": "\u5b89\u5168\u4e0e\u819c\u9762\u7f3a\u9677\u9650", "source": "ontology"},
            {"factor": "line_speed", "type": "box", "min": 290, "max": 350,
             "hard": True, "reason": "\u8bbe\u5907\u8bbe\u5b9a\u4e0a\u4e0b\u9650", "source": "platform"},
            {"factor": "tdo_ratio", "type": "box", "min": 2.6, "max": 3.4,
             "hard": False, "reason": "\u5de5\u827a\u7ecf\u9a8c\u533a\u95f4", "source": "ontology"},
        ],
        "replicates_col": "replicate_group",
        "run_order_col": "run_order",
        "group_col": "run_id",
        "time_col": None,
        "current_setpoint": {"zone1_temp": 200, "line_speed": 320, "tdo_ratio": 3.0},
        "baseline_source": "platform_recipe",
        "ontology": {
            "profile": "doe", "mode": "auto",
            "scene_key": "bopet-tdo-thickness", "version": None,
            "data_stage": "design_only" if design_only else "collected",
        },
        "provenance": {
            "platform": "RecipeWorkShop",
            "created_by": "contract-example-generator",
            "created_at": "2026-10-17T00:00:00+08:00",
        },
    }


def main() -> int:
    design_rows = build_design_only()
    write_csv(HERE / "run_table.csv", design_rows, BASE_FIELDS + RESP_FIELDS)

    coll_rows = build_collected()
    write_csv(HERE / "run_table_collected.csv", coll_rows, BASE_FIELDS + RESP_FIELDS)

    (HERE / "doe_context.json").write_text(
        json.dumps(doe_context(design_only=True), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (HERE / "doe_context_collected.json").write_text(
        json.dumps(doe_context(design_only=False), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"[examples] run_table.csv rows={len(design_rows)}")
    print(f"[examples] run_table_collected.csv rows={len(coll_rows)}")
    print("[examples] doe_context.json / doe_context_collected.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
