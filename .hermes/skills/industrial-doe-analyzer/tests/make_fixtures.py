#!/usr/bin/env python
"""make_fixtures.py — deterministic DOE acceptance fixtures (P5-1).

Each fixture lands at tests/fixtures/doe/<name>/run/00_input/{doe_context.json,<table>.csv}
plus a sibling truth.json holding GROUND TRUTH derived analytically from the
generator's own model — never a transcript of analyzer output.

Re-running is idempotent: the generator writes only when the bytes differ, and a
second run therefore leaves the tree clean.

Usage:
    uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/make_fixtures.py [name...]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixtures" / "doe"
ALPHA = 1.682

CUBE = [(-1, -1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (-1, 1, 1), (1, 1, 1)]
AXIAL = [(ALPHA, 0, 0), (-ALPHA, 0, 0), (0, ALPHA, 0),
         (0, -ALPHA, 0), (0, 0, ALPHA), (0, 0, -ALPHA)]
CENTER3 = [(0, 0, 0)]


def ccd3(n_center=3):
    return CUBE + AXIAL + CENTER3 * n_center


def bbd3(n_center=3):
    """Canonical Box-Behnken: every run varies exactly one factor pair."""
    pts = []
    for i, j in ((0, 1), (0, 2), (1, 2)):
        for si in (-1, 1):
            for sj in (-1, 1):
                row = [0, 0, 0]
                row[i], row[j] = si, sj
                pts.append(tuple(row))
    return pts + [(0, 0, 0)] * n_center


def full23(reps=2):
    pts = []
    for p in CUBE:
        pts.extend([p] * reps)
    return pts


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


def raw(coded, specs):
    out = {}
    for (name, (center, half)), c in zip(specs.items(), coded):
        out[name] = round(center + half * c, 4)
    return out


def factor(name, col, unit, lo, hi, **kw):
    d = {"name": name, "col": col, "type": "numeric", "unit": unit,
         "min": lo, "max": hi, "levels": None, "role": "control"}
    d.update(kw)
    return d


def response(name, col, unit, goal, lsl=None, usl=None, target=None, weight=1.0):
    return {"name": name, "col": col, "unit": unit, "goal": goal,
            "lsl": lsl, "usl": usl, "target": target, "weight": weight}


def doe_context(experiment_id, factors, responses, *, data_file, data_stage="collected",
                constraints=None, blocks=None, run_order_col="run_order",
                scene_key=None, mode="off", design_type="rsm_ccd",
                design_region=None, objective=None):
    return {
        "contract_version": "1.1",
        "experiment_id": experiment_id,
        "line_id": "L5-bopet",
        "product_id": "film-12um",
        "recipe_id": "rcp-bopet-12um-v3",
        "objective": objective or "工艺窗口优化",
        "design_type_declared": design_type,
        "data_stage": data_stage,
        "design_region": design_region or {},
        "data_file": data_file,
        "factors": factors,
        "responses": responses,
        "blocks": blocks or [],
        "covariates": [],
        "constraints": constraints or [],
        "replicates_col": "replicate_group",
        "run_order_col": run_order_col,
        "group_col": "run_id",
        "time_col": None,
        "current_setpoint": {f["col"]: f["min"] for f in factors},
        "baseline_source": "dataset_median",
        "ontology": {"profile": "doe", "mode": mode, "scene_key": scene_key,
                     "version": None, "data_stage": data_stage},
        "provenance": {"platform": "RecipeWorkShop", "created_by": "make_fixtures",
                       "created_at": "2026-10-17T00:00:00+08:00"},
    }


def emit(name, ctx, fields, rows, truth):
    base = ROOT / name
    write_json(base / "run" / "00_input" / "doe_context.json", ctx)
    write_csv(base / "run" / "00_input" / ctx["data_file"], fields, rows)
    write_json(base / "truth.json", truth)
    return name, len(rows)


# ---------------------------------------------------------------- fixtures

def fx_design_only():
    specs = {"zone1_temp": (200.0, 20.0), "line_speed": (320.0, 40.0),
             "tdo_ratio": (3.0, 0.5)}
    factors = [factor("zone1_temp", "zone1_temp", "\u00b0C", 180, 220,
                      physical_meaning="TDO Z4 \u52a0\u70ed\u533a\u6e29\u5ea6",
                      ontology_signal="TDO_Z4_SETPOINT", expected_sign="+"),
               factor("line_speed", "line_speed", "m/min", 280, 360,
                      physical_meaning="\u7ebf\u901f", ontology_signal="MD_LINE_SPEED",
                      expected_sign="-"),
               factor("tdo_ratio", "tdo_ratio", "-", 2.5, 3.5,
                      physical_meaning="TDO \u62c9\u4f38\u6bd4",
                      ontology_signal="TDO_STRETCH_RATIO", expected_sign="+")]
    responses = [response("thickness_um", "thickness_um", "um", "target", 48, 52, 50),
                 response("haze_pct", "haze_pct", "%", "minimize", usl=1.8, weight=0.5)]
    rows = []
    for i, c in enumerate(ccd3(), start=1):
        r = {"run_id": f"doerun-{i:03d}", "design_point_id": f"dp-{i:02d}",
             "replicate_group": f"rg-{i:02d}", "replicate_kind": "center" if c == (0, 0, 0) else "run",
             "run_order": i, "block": "1"}
        r.update(raw(c, specs))
        r["thickness_um"] = ""
        r["haze_pct"] = ""
        rows.append(r)
    ctx = doe_context("fx-design-only", factors, responses, data_file="run_table.csv",
                      data_stage="design_only", scene_key="doe-design-only",
                      mode="auto", design_type="rsm_ccd", design_region={
                          "factorial_bounds": {k: [v[0] - v[1], v[0] + v[1]] for k, v in specs.items()},
                          "axial_alpha": ALPHA, "design_hull": "ccd_star"},
                      objective="\u5148\u9a8c\u5efa\u672c\u4f53\uff0c\u5c1a\u672a\u6d4b\u54cd\u5e94")
    truth = {
        "fixture": "design_only", "design_type": "rsm_ccd", "n_runs": len(rows),
        "factors": [f["col"] for f in factors],
        "responses": [r["col"] for r in responses],
        "responses_measured": False,
        "expected": {"data_stage": "design_only",
                     "observed_data_behavior": "NOT_APPLICABLE",
                     "statistics_allowed": False,
                     "blocked_code": "DESIGN_ONLY_NO_RESPONSE"},
        "generation": {"alpha": ALPHA, "criteria": "CCD k=3, 8 cube + 6 axial + 3 center"},
    }
    return emit("design_only", ctx, ["run_id", "design_point_id", "replicate_group",
                                     "replicate_kind", "run_order", "block",
                                     *specs, "thickness_um", "haze_pct"], rows, truth)


def fx_ccd_constraints():
    specs = {"temp": (200.0, 20.0), "pressure": (5.0, 0.5), "flow": (100.0, 10.0)}
    rng = np.random.default_rng(20261017)
    true_center = 1.4
    rows = []
    for i, c in enumerate(ccd3(), start=1):
        zt, zp, zf = c
        y = 60.0 - 2.0 * (zt - true_center) ** 2 - 1.5 * zp ** 2 - 1.2 * zf ** 2
        y += float(rng.normal(0.0, 0.25))
        r = {"run_id": f"doerun-{i:03d}", "design_point_id": f"dp-{i:02d}",
             "replicate_group": f"rg-{i:02d}",
             "replicate_kind": "center" if c == (0, 0, 0) else "run",
             "run_order": i, "block": "1"}
        r.update(raw(c, specs))
        r["purity"] = round(y, 4)
        rows.append(r)
    factors = [factor("temp", "temp", "\u00b0C", 180, 220, expected_sign="+"),
               factor("pressure", "pressure", "bar", 4.5, 5.5),
               factor("flow", "flow", "L/min", 90, 110)]
    responses = [response("purity", "purity", "%", "maximize", lsl=50.0)]
    # hard box on temp at coded [-1, 1] = raw [180, 220] while the design spans +-1.682
    constraints = [{"factor": "temp", "type": "box", "min": 180.0, "max": 220.0,
                    "hard": True, "reason": "\u5b89\u5168\u4e0e\u819c\u9762\u9650",
                    "source": "ontology"}]
    ctx = doe_context("fx-ccd-constraints", factors, responses,
                      data_file="run_table.csv", constraints=constraints,
                      design_region={"factorial_bounds": {k: [v[0] - v[1], v[0] + v[1]]
                                                          for k, v in specs.items()},
                                     "axial_alpha": ALPHA, "design_hull": "ccd_star"},
                      objective="\u5728\u786c\u7ea6\u675f\u5185\u6700\u5927\u5316\u7eaf\u5ea6")
    truth = {
        "fixture": "ccd_constraints", "design_type": "rsm_ccd", "n_runs": len(rows),
        "factors": ["temp", "pressure", "flow"], "responses": ["purity"],
        "generation": {"alpha": ALPHA, "noise_sigma": 0.25,
                       "model": "y = 60 - 2.0*(zt-1.4)^2 - 1.5*zp^2 - 1.2*zf^2 + eps"},
        "unconstrained_optimum_coded": {"temp": true_center, "pressure": 0.0, "flow": 0.0},
        "unconstrained_optimum_raw": {"temp": 200.0 + 20.0 * true_center,
                                      "pressure": 5.0, "flow": 100.0},
        "constrained_optimum_raw": {"temp": 220.0},
        "binding_constraint": {"factor": "temp", "type": "box", "min": 180.0, "max": 220.0,
                               "hard": True},
        "design_span_coded": [-ALPHA, ALPHA],
        "expected": {"hard_constraint_violations": 0,
                     "joint_setpoint_temp_max": 220.0,
                     "no_window_reason_if_infeasible": "CONSTRAINTS_INFEASIBLE"},
    }
    return emit("ccd_constraints", ctx, ["run_id", "design_point_id", "replicate_group",
                                         "replicate_kind", "run_order", "block",
                                         *specs, "purity"], rows, truth)


def fx_bbd_multi_response():
    specs = {"a_ratio": (1.0, 0.2), "b_temp": (100.0, 10.0), "c_speed": (50.0, 5.0)}
    rng = np.random.default_rng(20261018)
    rows = []
    for i, c in enumerate(bbd3(), start=1):
        za, zb, zc = c
        thick = 50.0 - 1.2 * (za - 0.8) ** 2 - 1.0 * zb ** 2 - 0.8 * zc ** 2
        haze = 1.35 + 0.5 * (za + 0.8) ** 2 + 0.2 * zb ** 2 + 0.15 * zc ** 2
        r = {"run_id": f"doerun-{i:03d}", "design_point_id": f"dp-{i:02d}",
             "replicate_group": f"rg-{i:02d}",
             "replicate_kind": "center" if c == (0, 0, 0) else "edge",
             "run_order": i, "block": "1"}
        r.update(raw(c, specs))
        r["thickness_um"] = round(thick + float(rng.normal(0, 0.12)), 4)
        r["haze_pct"] = round(haze + float(rng.normal(0, 0.03)), 4)
        rows.append(r)
    factors = [factor("a_ratio", "a_ratio", "-", 0.8, 1.2, expected_sign="+"),
               factor("b_temp", "b_temp", "\u00b0C", 90, 110),
               factor("c_speed", "c_speed", "m/min", 45, 55)]
    responses = [response("thickness_um", "thickness_um", "um", "target", 48, 52, 50),
                 response("haze_pct", "haze_pct", "%", "minimize", usl=1.8, weight=0.5)]
    ctx = doe_context("fx-bbd-multi", factors, responses, data_file="run_table.csv",
                      design_type="rsm_bbd",
                      design_region={"factorial_bounds": {k: [v[0] - v[1], v[0] + v[1]]
                                                          for k, v in specs.items()},
                                     "design_hull": "convex_hull"},
                      objective="\u540c\u65f6\u6ee1\u8db3\u539a\u5ea6\u76ee\u6807\u4e0e\u96fe\u5ea6\u4e0a\u9650")
    truth = {
        "fixture": "bbd_multi_response", "design_type": "rsm_bbd", "n_runs": len(rows),
        "factors": ["a_ratio", "b_temp", "c_speed"],
        "responses": ["thickness_um", "haze_pct"],
        "generation": {"noise_sigma": {"thickness_um": 0.12, "haze_pct": 0.03},
                       "thickness": "50 - 1.2*(za-0.8)^2 - 1.0*zb^2 - 0.8*zc^2",
                       "haze": "1.35 + 0.5*(za+0.8)^2 + 0.2*zb^2 + 0.15*zc^2"},
        "per_response_optimum_coded": {"thickness_um": {"a_ratio": 0.8},
                                       "haze_pct": {"a_ratio": -0.8}},
        "conflict": {"factor": "a_ratio", "kind": "opposing optimum along the same factor",
                     "thickness_wants": "+0.8", "haze_wants": "-0.8"},
        "jointly_feasible": True,
        "expected": {"matrix_cells": 6, "window_role": "marginal_diagnostic",
                     "responses_satisfied_min": 2},
    }
    return emit("bbd_multi_response", ctx, ["run_id", "design_point_id", "replicate_group",
                                            "replicate_kind", "run_order", "block",
                                            *specs, "thickness_um", "haze_pct"], rows, truth)


def fx_units_conflict():
    specs = {"film_width": (1000.0, 50.0), "line_speed": (320.0, 40.0)}
    pts = [(-1, -1), (1, -1), (-1, 1), (1, 1),
           (1.41, 0), (-1.41, 0), (0, 1.41), (0, -1.41),
           (0, 0), (0, 0), (0, 0)]
    rng = np.random.default_rng(20261019)
    rows = []
    for i, c in enumerate(pts, start=1):
        z1, z2 = c
        y = 50.0 - 1.5 * z1 ** 2 - 1.0 * z2 ** 2 + 0.8 * z1 + float(rng.normal(0, 0.1))
        r = {"run_id": f"doerun-{i:03d}", "design_point_id": f"dp-{i:02d}",
             "replicate_group": f"rg-{i:02d}",
             "replicate_kind": "center" if c == (0, 0) else "run",
             "run_order": i, "block": "1"}
        r.update(raw(c, specs))
        r["width_um"] = round(y, 4)
        rows.append(r)
    # The analysis column is in mm; the platform recipe parameter is in um.
    factors = [factor("film_width", "film_width", "mm", 950, 1050,
                      platform_ref={"recipe_param": "film_width", "node_id": "dw-mdo-01",
                                    "plc_tag": "FILM_WIDTH_SP", "unit": "\u00b5m",
                                    "unit_conversion": 1000.0, "rounding": 1.0,
                                    "hard_limits": {"min": 960, "max": 1040}}),
               factor("line_speed", "line_speed", "m/min", 280, 360)]
    responses = [response("width_um", "width_um", "um", "target", 48, 52, 50)]
    ctx = doe_context("fx-units-conflict", factors, responses, data_file="run_table.csv",
                      design_type="rsm_ccd",
                      design_region={"factorial_bounds": {k: [v[0] - v[1], v[0] + v[1]]
                                                          for k, v in specs.items()},
                                     "axial_alpha": 1.41, "design_hull": "ccd_star"})
    truth = {
        "fixture": "units_conflict", "design_type": "rsm_ccd", "n_runs": len(rows),
        "factors": ["film_width", "line_speed"], "responses": ["width_um"],
        "conflict": {"factor": "film_width", "analysis_unit": "mm", "platform_unit": "\u00b5m",
                     "unit_conversion": 1000.0},
        "expected": {"unit_status": "conflict", "actionable": False,
                     "blocker": "unit_conflict", "units_conflicts_min": 1},
    }
    return emit("units_conflict", ctx, ["run_id", "design_point_id", "replicate_group",
                                        "replicate_kind", "run_order", "block",
                                        *specs, "width_um"], rows, truth)


def fx_association_confounder():
    names = ["a_level", "b_level", "c_level"]
    specs = {"a_level": (10.0, 5.0), "b_level": (50.0, 10.0), "c_level": (200.0, 20.0)}
    rng = np.random.default_rng(20261020)
    rows = []
    schedule = full23(reps=2) * 2  # 32 runs
    for i, c in enumerate(schedule, start=1):
        za, zb, zc = c
        y = 4.0 * za + 2.0 * zb + float(rng.normal(0, 0.3))
        r = {"run_id": f"doerun-{i:03d}", "design_point_id": f"dp-{i:02d}",
             "replicate_group": f"rg-{i:02d}", "replicate_kind": "replicate",
             "run_order": i, "block": "1"}
        r.update(raw(c, specs))
        r["yield_kg"] = round(y, 4)
        # non-factor: shares A's driver, never declared anywhere in the context
        r["ambient_temp"] = round(25.0 + 2.0 * za + float(rng.normal(0, 0.05)), 4)
        rows.append(r)
    factors = [factor("a_level", "a_level", "-", 5, 15),
               factor("b_level", "b_level", "kg", 40, 60),
               factor("c_level", "c_level", "rpm", 180, 220)]
    responses = [response("yield_kg", "yield_kg", "kg", "maximize")]
    ctx = doe_context("fx-association-confounder", factors, responses,
                      data_file="run_table.csv", design_type="full_factorial",
                      design_region={"factorial_bounds": {k: [v[0] - v[1], v[0] + v[1]]
                                                          for k, v in specs.items()},
                                     "design_hull": "box"})
    truth = {
        "fixture": "association_confounder", "design_type": "full_factorial",
        "n_runs": len(rows), "factors": ["a_level", "b_level", "c_level"],
        "responses": ["yield_kg"],
        "generation": {"model": "y = 4.0*a + 2.0*b + eps (sigma=0.3)",
                       "confounder": "ambient_temp = 25 + 2.0*a + noise(0.05)",
                       "confounder_is_declared": False},
        "expected": {"confounder": "ambient_temp",
                     "marginal_abs_r_min": 0.5,
                     "adjusted_effect_materially_smaller": True,
                     "causal_claim": "none",
                     "must_not_appear_as_window_factor": True},
    }
    return emit("association_confounder", ctx, ["run_id", "design_point_id",
                                                "replicate_group", "replicate_kind",
                                                "run_order", "block", *specs,
                                                "yield_kg", "ambient_temp"], rows, truth)


FIXTURES = {
    "design_only": fx_design_only,
    "ccd_constraints": fx_ccd_constraints,
    "bbd_multi_response": fx_bbd_multi_response,
    "units_conflict": fx_units_conflict,
    "association_confounder": fx_association_confounder,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    names = argv or list(FIXTURES)
    unknown = [n for n in names if n not in FIXTURES]
    if unknown:
        print(f"ERROR: unknown fixture(s): {unknown}", file=sys.stderr)
        print(f"known: {list(FIXTURES)}", file=sys.stderr)
        return 2
    total = 0
    for name in names:
        written, n_rows = FIXTURES[name]()
        total += n_rows
        print(f"[fixture] {written}: rows={n_rows}")
    print(f"[fixtures] {len(names)} fixture(s), {total} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
