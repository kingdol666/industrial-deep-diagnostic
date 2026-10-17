#!/usr/bin/env python
"""Generate a multi-industry, multi-design DOE corpus for generality testing.

Each case is a self-contained input directory:

    cases/<id>/
      00_input/run_table.csv
      00_input/doe_context.json
      truth.json          planted design/effects (acceptance only)

The corpus deliberately crosses industries (injection, heat treatment, chemical,
semiconductor, food, battery, paper, coating, plastics, machining, display,
lab design-only) and design types (full/fractional factorial, CCD, BBD, OA, LHS,
observational, high-throughput multi-response, unit/constraint edge cases).

Usage: python generate_cases.py [--force]
"""
from __future__ import annotations

import csv
import io
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CASES_DIR = HERE / "cases"
sys.path.insert(0, str(REPO / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"))
from doestats.design_build import build_design  # noqa: E402

SEED = 20261018


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in header})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def numeric_factor(col, low, high, unit, sign="+", name=None):
    return {"col": col, "name": name or col, "type": "numeric", "unit": unit,
            "low": low, "high": high, "expected_sign": sign}


def categorical_factor(col, levels, unit="-", name=None):
    return {"col": col, "name": name or col, "type": "categorical", "unit": unit,
            "levels": levels, "expected_sign": "+"}


def response(col, goal, unit, lsl=None, usl=None, target=None, weight=1.0, name=None):
    return {"col": col, "name": name or col, "goal": goal, "unit": unit,
            "lsl": lsl, "usl": usl, "target": target, "weight": weight}


def model(intercept, terms=None, noise=0.1):
    return {"intercept": intercept, "terms": terms or {}, "noise": noise}


# ---------------------------------------------------------------- case specs

def cases():
    return [
        {
            "id": "injection_full_factorial",
            "industry": "注塑成型",
            "scene": "injection-molding-lineB-pa66",
            "design": {"design_type": "full_factorial",
                       "factors": [
                           {"name": "melt_temp", "type": "numeric", "low": 260, "high": 290},
                           {"name": "pressure", "type": "numeric", "low": 50, "high": 80},
                           {"name": "cooling_s", "type": "numeric", "low": 10, "high": 20},
                           {"name": "material", "type": "categorical", "levels": ["A", "B"]},
                       ], "n_center": 2},
            "factors": [
                numeric_factor("melt_temp", 260, 290, "°C", "+"),
                numeric_factor("pressure", 50, 80, "MPa", "-"),
                numeric_factor("cooling_s", 10, 20, "s", "-"),
                categorical_factor("material", ["A", "B"]),
            ],
            "responses": [
                response("weight_g", "target", "g", lsl=97, usl=103, target=100),
                response("warpage_mm", "minimize", "mm", usl=0.8),
                response("cycle_s", "minimize", "s", usl=18),
            ],
            "models": {
                "weight_g": model(100, {"melt_temp": 3.0, "pressure": -2.2,
                                        "cooling_s": -1.6, "material": 2.5,
                                        "melt_temp:pressure": 1.5}, 0.18),
                "warpage_mm": model(0.45, {"melt_temp": -0.18, "pressure": 0.06,
                                           "cooling_s": 0.28, "material": -0.10}, 0.025),
                "cycle_s": model(15, {"melt_temp": 0.3, "pressure": 0.6,
                                      "cooling_s": -1.2}, 0.12),
            },
            "missing": [("doerun-03", "weight_g")],
            "covariates": ["ambient_temp"],
            "blocks": True,
            "constraints": [],
            "current_setpoint": {"melt_temp": 275, "pressure": 65, "cooling_s": 15,
                                 "material": "A"},
            "expected": {"design": "full_factorial",
                         "effects": [("weight_g", "melt_temp", "+"),
                                     ("weight_g", "material", "*"),
                                     ("warpage_mm", "cooling_s", "+"),
                                     ("cycle_s", "cooling_s", "-")],
                         "null": []},
        },
        {
            "id": "heat_treat_ccd",
            "industry": "热处理",
            "scene": "heat-treat-furnace3-4140",
            "design": {"design_type": "rsm_ccd",
                       "factors": [
                           {"name": "aust_temp", "type": "numeric", "low": 840, "high": 880},
                           {"name": "hold_min", "type": "numeric", "low": 30, "high": 60},
                           {"name": "carbon", "type": "numeric", "low": 0.40, "high": 0.60},
                       ], "alpha": 1.0, "n_center": 4},
            "factors": [
                numeric_factor("aust_temp", 840, 880, "°C", "+"),
                numeric_factor("hold_min", 30, 60, "min", "+"),
                numeric_factor("carbon", 0.40, 0.60, "%", "-"),
            ],
            "responses": [
                response("hardness_hrc", "target", "HRC", lsl=56, usl=60, target=58),
                response("distortion_mm", "minimize", "mm", usl=0.15),
            ],
            "models": {
                "hardness_hrc": model(58, {"aust_temp": 1.6, "hold_min": 0.8,
                                           "carbon": -0.5, "aust_temp^2": -1.2,
                                           "hold_min^2": -0.7,
                                           "aust_temp:hold_min": 0.4}, 0.18),
                "distortion_mm": model(0.10, {"aust_temp": 0.030, "hold_min": 0.020,
                                               "carbon": -0.010, "aust_temp^2": 0.010}, 0.004),
            },
            "missing": [],
            "covariates": ["quench_temp"],
            "blocks": False,
            "constraints": [
                {"factor": "aust_temp", "type": "box", "min": 835, "max": 885,
                 "hard": True, "reason": "炉膛安全限", "source": "ontology"},
            ],
            "current_setpoint": {"aust_temp": 860, "hold_min": 45, "carbon": 0.50},
            "expected": {"design": "rsm_ccd",
                         "effects": [("hardness_hrc", "aust_temp", "+"),
                                     ("distortion_mm", "aust_temp", "+")],
                         "null": []},
        },
        {
            "id": "reactor_bbd",
            "industry": "化工反应",
            "scene": "reactor-r12-esterification",
            "design": {"design_type": "rsm_bbd",
                       "factors": [
                           {"name": "react_temp", "type": "numeric", "low": 60, "high": 80},
                           {"name": "ph", "type": "numeric", "low": 6.5, "high": 7.5},
                           {"name": "catalyst", "type": "numeric", "low": 1.0, "high": 3.0},
                       ], "n_center": 3},
            "factors": [
                numeric_factor("react_temp", 60, 80, "°C", "+"),
                numeric_factor("ph", 6.5, 7.5, "-", "-"),
                numeric_factor("catalyst", 1.0, 3.0, "wt%", "+"),
            ],
            "responses": [
                response("yield_pct", "maximize", "%", lsl=80),
                response("impurity_pct", "minimize", "%", usl=0.5),
                response("viscosity_cp", "target", "cP", lsl=11, usl=13, target=12),
            ],
            "models": {
                "yield_pct": model(88, {"react_temp": 3.0, "ph": -2.0,
                                        "catalyst": 1.0, "react_temp^2": -2.5,
                                        "ph^2": -1.5, "react_temp:ph": 1.2}, 0.5),
                "impurity_pct": model(0.25, {"react_temp": -0.08, "ph": 0.06,
                                             "catalyst": -0.03, "react_temp^2": 0.05}, 0.015),
                "viscosity_cp": model(12, {"react_temp": 0.8, "ph": 0.5,
                                           "catalyst": -0.3}, 0.12),
            },
            "missing": [],
            "covariates": ["coolant_temp"],
            "blocks": False,
            "constraints": [
                {"type": "linear", "coefficients": {"react_temp": 1.0, "catalyst": 5.0},
                 "rhs": 90.0, "hard": True, "reason": "总热负荷", "source": "ontology"},
            ],
            "current_setpoint": {"react_temp": 70, "ph": 7.0, "catalyst": 2.0},
            "expected": {"design": "rsm_bbd",
                         "effects": [("yield_pct", "react_temp", "+"),
                                     ("impurity_pct", "ph", "+")],
                         "null": []},
        },
        {
            "id": "etch_fractional",
            "industry": "半导体刻蚀",
            "scene": "etch-tool2-oxide",
            "design": {"design_type": "fractional_factorial",
                       "factors": [
                           {"name": "rf_power", "type": "numeric", "low": 200, "high": 400},
                           {"name": "pressure", "type": "numeric", "low": 5, "high": 15},
                           {"name": "gas_flow", "type": "numeric", "low": 20, "high": 40},
                           {"name": "gap", "type": "numeric", "low": 2, "high": 6},
                       ], "resolution": 4, "n_center": 4},
            "factors": [
                numeric_factor("rf_power", 200, 400, "W", "+"),
                numeric_factor("pressure", 5, 15, "mTorr", "-"),
                numeric_factor("gas_flow", 20, 40, "sccm", "+"),
                numeric_factor("gap", 2, 6, "mm", "-"),
            ],
            "responses": [
                response("etch_depth_nm", "target", "nm", lsl=475, usl=525, target=500),
                response("selectivity", "maximize", "-", lsl=8),
            ],
            "models": {
                "etch_depth_nm": model(500, {"rf_power": 55, "pressure": -30,
                                             "gas_flow": 22, "gap": -15}, 4),
                "selectivity": model(10, {"rf_power": 1.2, "pressure": -0.8,
                                          "gap": 0.4}, 0.12),
            },
            "missing": [],
            "covariates": ["chamber_temp"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"rf_power": 300, "pressure": 10, "gas_flow": 30, "gap": 4},
            "expected": {"design": ["fractional_factorial", "orthogonal_array"],
                         "effects": [("etch_depth_nm", "rf_power", "+"),
                                     ("selectivity", "rf_power", "+")],
                         "null": []},
        },
        {
            "id": "food_l9_oa",
            "industry": "食品调味",
            "scene": "sauce-kettle-l9",
            "design": {"design_type": "orthogonal_array",
                       "factors": [
                           {"name": "sugar", "type": "numeric", "levels": [5, 10, 15]},
                           {"name": "acid", "type": "numeric", "levels": [0.5, 1.0, 1.5]},
                           {"name": "cook_temp", "type": "numeric", "levels": [60, 75, 90]},
                           {"name": "cook_min", "type": "numeric", "levels": [10, 20, 30]},
                       ]},
            "factors": [
                numeric_factor("sugar", 5, 15, "g/100g", "+"),
                numeric_factor("acid", 0.5, 1.5, "g/100g", "-"),
                numeric_factor("cook_temp", 60, 90, "°C", "+"),
                numeric_factor("cook_min", 10, 30, "min", "+"),
            ],
            "responses": [
                response("taste_score", "maximize", "pt", lsl=65),
                response("texture_score", "target", "pt", lsl=60, usl=80, target=70),
                response("color_score", "target", "pt", lsl=55, usl=85, target=70),
            ],
            "models": {
                "taste_score": model(72, {"sugar": 8.0, "acid": -4.0,
                                          "cook_temp": 3.0, "cook_min": 2.0}, 0.6),
                "texture_score": model(70, {"sugar": -1.0, "cook_temp": 2.5,
                                            "cook_min": 3.0}, 1.0),
                "color_score": model(70, {"cook_temp": -2.0, "cook_min": -1.5}, 1.0),
            },
            "missing": [],
            "covariates": [],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"sugar": 10, "acid": 1.0, "cook_temp": 75,
                                 "cook_min": 20},
            "expected": {"design": "orthogonal_array",
                         "effects": [("taste_score", "sugar", "+")],
                         "null": []},
        },
        {
            "id": "battery_lhs",
            "industry": "电池材料",
            "scene": "cathode-lhs-5f",
            "design": {"design_type": "latin_hypercube",
                       "factors": [
                           {"name": "ni_ratio", "type": "numeric", "low": 0.5, "high": 0.9},
                           {"name": "coating_um", "type": "numeric", "low": 10, "high": 30},
                           {"name": "sinter_temp", "type": "numeric", "low": 700, "high": 800},
                           {"name": "sinter_h", "type": "numeric", "low": 2, "high": 6},
                           {"name": "press_mpa", "type": "numeric", "low": 5, "high": 15},
                       ], "runs": 20},
            "factors": [
                numeric_factor("ni_ratio", 0.5, 0.9, "-", "+"),
                numeric_factor("coating_um", 10, 30, "um", "-"),
                numeric_factor("sinter_temp", 700, 800, "°C", "+"),
                numeric_factor("sinter_h", 2, 6, "h", "+"),
                numeric_factor("press_mpa", 5, 15, "MPa", "-"),
            ],
            "responses": [
                response("capacity_mah", "maximize", "mAh/g", lsl=150),
                response("resistance_ohm", "minimize", "ohm", usl=40),
            ],
            "models": {
                "capacity_mah": model(180, {"ni_ratio": 8, "coating_um": -5,
                                            "sinter_temp": 4, "sinter_h": -3,
                                            "press_mpa": 2}, 1.2),
                "resistance_ohm": model(30, {"ni_ratio": -3, "coating_um": 2,
                                             "sinter_temp": -1.5}, 0.8),
            },
            "missing": [],
            "covariates": ["humidity"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"ni_ratio": 0.7, "coating_um": 20,
                                 "sinter_temp": 750, "sinter_h": 4, "press_mpa": 10},
            "expected": {"design": "latin_hypercube",
                         "effects": [("capacity_mah", "ni_ratio", "+")],
                         "null": []},
        },
        {
            "id": "coating_conflict",
            "industry": "涂布",
            "scene": "coating-line1-gloss",
            "design": {"design_type": "full_factorial",
                       "factors": [
                           {"name": "oven_temp", "type": "numeric", "low": 120, "high": 160},
                           {"name": "line_speed", "type": "numeric", "low": 20, "high": 40},
                       ], "n_center": 3, "replicates": 2},
            "factors": [
                numeric_factor("oven_temp", 120, 160, "°C", "+"),
                numeric_factor("line_speed", 20, 40, "m/min", "-"),
            ],
            "responses": [
                response("gloss_gu", "maximize", "GU", lsl=80),
                response("orange_peel", "minimize", "OI", usl=30),
            ],
            "models": {
                "gloss_gu": model(85, {"oven_temp": 6.0, "line_speed": -3.0}, 0.5),
                "orange_peel": model(25, {"oven_temp": 4.0, "line_speed": 1.5}, 0.45),
            },
            "missing": [],
            "covariates": ["ambient_temp"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"oven_temp": 140, "line_speed": 30},
            "expected": {"design": "full_factorial",
                         "effects": [("gloss_gu", "oven_temp", "+"),
                                     ("orange_peel", "oven_temp", "+")],
                         "null": []},
        },
        {
            "id": "plastics_units",
            "industry": "塑料薄膜",
            "scene": "cast-film-die-units",
            "design": {"design_type": "rsm_ccd",
                       "factors": [
                           {"name": "die_temp", "type": "numeric", "low": 200, "high": 240},
                           {"name": "screw_rpm", "type": "numeric", "low": 50, "high": 100},
                       ], "alpha": 1.0, "n_center": 3},
            "factors": [
                {**numeric_factor("die_temp", 200, 240, "°C", "+"),
                 "platform_ref": {"recipe_param": "DIE_TEMP", "node_id": "die_temp",
                                  "unit": "C", "unit_conversion": 1.0, "rounding": 0.1,
                                  "hard_limits": {"min": 195, "max": 245}}},
                numeric_factor("screw_rpm", 50, 100, "rpm", "-"),
            ],
            "responses": [
                response("thickness_um", "target", "um", lsl=190, usl=210, target=200),
                response("haze_pct", "minimize", "%"),  # no spec on purpose
            ],
            "models": {
                "thickness_um": model(200, {"die_temp": 5.0, "screw_rpm": -3.0,
                                            "die_temp^2": -2.0}, 0.6),
                "haze_pct": model(1.5, {"die_temp": 0.10, "screw_rpm": -0.05}, 0.04),
            },
            "missing": [],
            "covariates": [],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"die_temp": 220, "screw_rpm": 75},
            "expected": {"design": "rsm_ccd",
                         "effects": [("thickness_um", "die_temp", "+")],
                         "null": []},
        },
        {
            "id": "machining_noise",
            "industry": "机加工",
            "scene": "cnc-mill-noise",
            "design": {"design_type": "full_factorial",
                       "factors": [
                           {"name": "spindle_rpm", "type": "numeric", "low": 1000, "high": 2000},
                           {"name": "feed_mm", "type": "numeric", "low": 0.1, "high": 0.3},
                           {"name": "depth_mm", "type": "numeric", "low": 0.5, "high": 1.5},
                       ], "n_center": 3},
            "factors": [
                numeric_factor("spindle_rpm", 1000, 2000, "rpm", "-"),
                numeric_factor("feed_mm", 0.1, 0.3, "mm/rev", "+"),
                numeric_factor("depth_mm", 0.5, 1.5, "mm", "+"),
            ],
            "responses": [
                response("roughness_ra", "minimize", "um", usl=1.8),
                response("roundness_um", "minimize", "um", usl=8),
            ],
            "models": {
                "roughness_ra": model(1.2, {"feed_mm": 0.40, "spindle_rpm": -0.15,
                                            "depth_mm": 0.12}, 0.035),
                "roundness_um": model(5.0, {}, 0.45),  # pure noise, no factor effect
            },
            "missing": [],
            "covariates": ["coolant_flow"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"spindle_rpm": 1500, "feed_mm": 0.2, "depth_mm": 1.0},
            "expected": {"design": "full_factorial",
                         "effects": [("roughness_ra", "feed_mm", "+")],
                         "null": [("roundness_um", "feed_mm"),
                                  ("roundness_um", "spindle_rpm")]},
        },
        {
            "id": "panel_high_throughput",
            "industry": "显示面板",
            "scene": "panel-line5-ht",
            "design": {"design_type": "fractional_factorial",
                       "factors": [
                           {"name": "temp", "type": "numeric", "low": 200, "high": 240},
                           {"name": "pressure", "type": "numeric", "low": 1, "high": 5},
                           {"name": "flow", "type": "numeric", "low": 10, "high": 30},
                           {"name": "gap", "type": "numeric", "low": 2, "high": 6},
                           {"name": "speed", "type": "numeric", "low": 5, "high": 15},
                       ], "resolution": 5, "n_center": 4},
            "factors": [
                numeric_factor("temp", 200, 240, "°C", "+"),
                numeric_factor("pressure", 1, 5, "Torr", "-"),
                numeric_factor("flow", 10, 30, "sccm", "+"),
                numeric_factor("gap", 2, 6, "mm", "-"),
                numeric_factor("speed", 5, 15, "mm/s", "+"),
            ],
            "responses": [
                response("luminance", "maximize", "cd/m2", lsl=400),
                response("uniformity", "maximize", "%", lsl=90),
                response("contrast", "maximize", "-", lsl=1000),
                response("color_shift", "minimize", "dE", usl=2.0),
                response("power_w", "minimize", "W", usl=8),
                response("lifetime_h", "maximize", "h", lsl=30000),
                response("defect_ppm", "minimize", "ppm", usl=50),
                response("stress_mpa", "minimize", "MPa", usl=120),
                response("thickness_nm", "target", "nm", lsl=95, usl=105, target=100),
                response("haze_pct", "minimize", "%", usl=1.0),
            ],
            "models": {
                "luminance": model(450, {"temp": 60, "flow": 20}, 3),
                "uniformity": model(94, {"gap": -1.5, "pressure": 1.0}, 0.4),
                "contrast": model(1200, {"temp": 90, "speed": 40}, 20),
                "color_shift": model(1.2, {"temp": 0.35, "gap": 0.15}, 0.03),
                "power_w": model(6.0, {"temp": 0.8, "flow": -0.4}, 0.12),
                "lifetime_h": model(35000, {"temp": -6000, "pressure": 1500}, 300),
                "defect_ppm": model(25, {"pressure": 8, "flow": -4}, 1.5),
                "stress_mpa": model(90, {"gap": 8, "speed": -4}, 2.0),
                "thickness_nm": model(100, {"flow": 3.0, "speed": -1.5}, 0.8),
                "haze_pct": model(0.55, {"temp": 0.06, "flow": -0.03}, 0.02),
            },
            "missing": [],
            "covariates": ["cleanroom_rh"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"temp": 220, "pressure": 3, "flow": 20, "gap": 4,
                                 "speed": 10},
            "expected": {"design": ["fractional_factorial", "orthogonal_array"],
                         "effects": [("luminance", "temp", "+"),
                                     ("color_shift", "temp", "+"),
                                     ("lifetime_h", "temp", "-")],
                         "null": []},
        },
        {
            "id": "design_only",
            "industry": "实验室设计",
            "scene": "lab-design-only",
            "kind": "design_only",
            "design": {"design_type": "full_factorial",
                       "factors": [
                           {"name": "ph", "type": "numeric", "low": 6, "high": 8},
                           {"name": "temp", "type": "numeric", "low": 20, "high": 40},
                       ], "n_center": 2},
            "factors": [
                numeric_factor("ph", 6, 8, "-", "+"),
                numeric_factor("temp", 20, 40, "°C", "+"),
            ],
            "responses": [response("yield_pct", "maximize", "%", lsl=50)],
            "models": {"yield_pct": model(60, {"ph": 5, "temp": 4}, 1)},
            "missing": [],
            "covariates": [],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"ph": 7, "temp": 30},
            "expected": {"design": "full_factorial", "effects": [], "null": []},
        },
        {
            "id": "paper_observational",
            "industry": "造纸",
            "scene": "paper-machine-observational",
            "kind": "observational",
            "factors": [
                numeric_factor("stock_flow", 80, 120, "L/min", "+"),
                numeric_factor("machine_speed", 600, 900, "m/min", "-"),
            ],
            "responses": [
                response("basis_weight", "target", "g/m2", lsl=78, usl=82, target=80),
                response("moisture_pct", "target", "%", lsl=4.5, usl=5.5, target=5.0),
            ],
            "missing": [],
            "covariates": ["steam_pressure", "filler_flow", "ambient_rh"],
            "blocks": False,
            "constraints": [],
            "current_setpoint": {"stock_flow": 100, "machine_speed": 750},
            "expected": {"design": "observational", "effects": [], "null": []},
        },
    ]


# ---------------------------------------------------------------- simulation

def _coded_value(col, row, factor):
    """The `coded` rows from design_build are ALREADY in coded units for numeric
    factors. Re-coding them with the raw bounds would compress every contrast to
    ~1/half_range and destroy the planted effects (the first version did exactly
    that). Categorical rows keep the level string and are mapped to -1/0/+1."""
    if factor["type"] == "categorical":
        levels = factor["levels"]
        idx = levels.index(str(row[col])) if str(row[col]) in levels else 0
        return (idx - (len(levels) - 1) / 2.0) / max((len(levels) - 1) / 2.0, 1)
    return float(row[col])


def _term_value(term, row, factors):
    sign = 1.0
    t = term
    if t.endswith("^2"):
        base = t[:-2]
        return _coded_value(base, row, factors[base]) ** 2
    if ":" in t:
        a, b = t.split(":", 1)
        return _coded_value(a, row, factors[a]) * _coded_value(b, row, factors[b])
    return _coded_value(t, row, factors[t])


def _add_centres(built: dict, case: dict) -> None:
    """design_build ignores n_center for full/fractional factorials; a design
    without centre runs has no pure error and no usable denominator for the
    saturated 2FI model. Append the declared centre executions here."""
    spec = case.get("design") or {}
    n = int(spec.get("n_center") or 0)
    if n <= 0 or spec.get("design_type") not in ("full_factorial",
                                                 "fractional_factorial"):
        return
    centre, coded_centre = {}, {}
    for f in case["factors"]:
        if f["type"] == "numeric":
            centre[f["col"]] = (f["low"] + f["high"]) / 2.0
            coded_centre[f["col"]] = 0.0
        else:
            centre[f["col"]] = f["levels"][0]
            coded_centre[f["col"]] = f["levels"][0]
    start = max((int(r.get("run_order") or 0) for r in built["run_table"]), default=0) + 1
    for i in range(n):
        rid = f"doerun-c{i + 1:02d}"
        built["run_table"].append({
            "run_id": rid, "design_point_id": "dp-centre", "run_order": start + i,
            "block": None, "replicate_group": "rg-centre",
            "replicate_kind": "center", **centre,
        })
        built["coded"].append({"run_id": rid, **coded_centre})


def simulate_designed(case: dict, out: Path, seed: int) -> None:
    built = build_design(case["design"], seed=seed)
    _add_centres(built, case)
    factors = {f["col"]: f for f in case["factors"]}
    coded = {r["run_id"]: r for r in built["coded"]}
    rng = np.random.default_rng(seed + 7)
    rows = []
    for i, run in enumerate(built["run_table"]):
        row = dict(run)
        c = coded.get(run["run_id"], {})
        for resp in case["responses"]:
            m = case["models"][resp["col"]]
            y = float(m["intercept"])
            for term, coef in (m.get("terms") or {}).items():
                y += float(coef) * _term_value(term, c, factors)
            y += float(rng.normal(0, m.get("noise", 0.1)))
            row[resp["col"]] = f"{y:.6f}"
        row["ambient_temp"] = f"{24.0 + float(rng.normal(0, 0.4)):.4f}"
        row["quench_temp"] = f"{60.0 + float(rng.normal(0, 1.0)):.4f}"
        row["coolant_temp"] = f"{18.0 + float(rng.normal(0, 0.3)):.4f}"
        row["chamber_temp"] = f"{45.0 + float(rng.normal(0, 0.5)):.4f}"
        row["humidity"] = f"{35.0 + float(rng.normal(0, 2.0)):.3f}"
        row["coolant_flow"] = f"{12.0 + float(rng.normal(0, 0.3)):.3f}"
        row["cleanroom_rh"] = f"{45.0 + float(rng.normal(0, 1.0)):.3f}"
        if case.get("blocks"):
            row["block"] = f"B{i % 2 + 1}"
        rows.append(row)
    for rid, col in case.get("missing") or []:
        for row in rows:
            if row["run_id"] == rid:
                row[col] = ""
    if case.get("kind") == "design_only":
        for row in rows:
            for r in case["responses"]:
                row[r["col"]] = ""
    header = list(rows[0].keys())
    for col in [r["col"] for r in case["responses"]]:
        if col not in header:
            header.append(col)
    write_csv(out / "00_input" / "run_table.csv", header, rows)

    ctx = build_context(case, rows, built)
    (out / "00_input" / "doe_context.json").write_text(
        json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    truth = {"id": case["id"], "industry": case["industry"],
             "kind": case.get("kind", "designed"),
             "design": case["expected"]["design"], "n_rows": len(rows),
             "effects": case["expected"]["effects"], "null": case["expected"]["null"],
             "models": case["models"]}
    (out / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2),
                                    encoding="utf-8")


def simulate_observational(case: dict, out: Path, seed: int) -> None:
    rng = np.random.default_rng(seed + 11)
    n = 600
    t = np.arange(n)
    stock = 100 + 8 * np.sin(t / 40) + rng.normal(0, 1.5, n)
    speed = 750 + 30 * np.sin(t / 55 + 0.5) + rng.normal(0, 2.0, n)
    steam = 3.0 + 0.004 * t + 0.15 * np.sin(t / 30) + rng.normal(0, 0.05, n)
    filler = 12 + 0.12 * (stock - 100) + rng.normal(0, 0.4, n)  # confounder
    ambient = 24 + 0.3 * np.sin(t / 80) + rng.normal(0, 0.2, n)
    basis = (80 + 0.35 * (stock - 100) - 0.02 * (speed - 750)
             + 0.0008 * t + 0.04 * (filler - 12) + rng.normal(0, 0.25, n))
    moisture = (5.0 + 0.25 * (steam - 3.0) - 0.001 * (speed - 750)
                + rng.normal(0, 0.08, n))
    rows = []
    for i in range(n):
        rows.append({
            "timestamp": f"2026-10-{(i // 1440) + 1:02d}T{(i % 1440) // 60:02d}:{i % 60:02d}:00Z",
            "stock_flow": f"{stock[i]:.4f}",
            "machine_speed": f"{speed[i]:.4f}",
            "steam_pressure": f"{steam[i]:.4f}",
            "filler_flow": f"{filler[i]:.4f}",
            "ambient_rh": f"{ambient[i]:.4f}",
            "basis_weight": f"{basis[i]:.4f}",
            "moisture_pct": f"{moisture[i]:.4f}",
        })
    write_csv(out / "00_input" / "run_table.csv",
              ["timestamp", "stock_flow", "machine_speed", "steam_pressure",
               "filler_flow", "ambient_rh", "basis_weight", "moisture_pct"], rows)
    ctx = build_context(case, rows, None)
    ctx["mode_override"] = "observational"
    ctx["time_col"] = "timestamp"
    ctx["data_stage"] = "collected"
    ctx["design_type_declared"] = "observational"
    ctx["design_region"] = None
    ctx["ontology"]["data_stage"] = "collected"
    (out / "00_input" / "doe_context.json").write_text(
        json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    truth = {"id": case["id"], "industry": case["industry"], "kind": "observational",
             "design": "observational", "n_rows": n,
             "effects": [], "null": [],
             "expected_correlations": {
                 "basis_weight": ["stock_flow", "filler_flow"],
                 "moisture_pct": ["steam_pressure"],
             }}
    (out / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2),
                                    encoding="utf-8")


def build_context(case: dict, rows: list[dict], built: dict | None) -> dict:
    factors = []
    for f in case["factors"]:
        entry = {
            "name": f["name"], "col": f["col"], "type": f["type"], "unit": f["unit"],
            "role": "control", "expected_sign": f.get("expected_sign"),
            "physical_meaning": f.get("name"),
            "platform_ref": f.get("platform_ref"),
        }
        if f["type"] == "numeric":
            vals = [float(r[f["col"]]) for r in rows
                    if str(r.get(f["col"], "")).strip() not in ("", "None")]
            entry["min"] = min(vals) if vals else f["low"]
            entry["max"] = max(vals) if vals else f["high"]
        else:
            entry["levels"] = f["levels"]
        factors.append(entry)
    responses = []
    for r in case["responses"]:
        responses.append({
            "name": r["name"], "col": r["col"], "unit": r["unit"],
            "goal": r["goal"], "lsl": r.get("lsl"), "usl": r.get("usl"),
            "target": r.get("target"), "weight": r.get("weight"),
        })
    bounds = {f["col"]: [f["low"], f["high"]] for f in case["factors"]
              if f["type"] == "numeric"}
    hull = {"full_factorial": "full_cube", "fractional_factorial": "full_cube",
            "rsm_ccd": "ccd_star", "rsm_bbd": "bbd_hull",
            "orthogonal_array": "full_cube", "latin_hypercube": "lhs_hull"}
    dtype = case["design"]["design_type"] if built else "observational"
    return {
        "contract_version": "1.0",
        "experiment_id": f"gen-{case['id']}",
        "line_id": case["scene"],
        "product_id": case["scene"],
        "objective": f"{case['industry']}：识别关键因子并给出可执行的操作条件",
        "design_type_declared": dtype,
        "data_stage": "design_only" if case.get("kind") == "design_only" else "collected",
        "data_file": "run_table.csv",
        "factors": factors,
        "responses": responses,
        "blocks": ["block"] if case.get("blocks") else [],
        "covariates": case.get("covariates") or [],
        "constraints": case.get("constraints") or [],
        "replicates_col": "replicate_group" if built and any(
            "replicate_group" in r for r in (built.get("run_table") or [])) else None,
        "run_order_col": "run_order",
        "group_col": "run_id",
        "time_col": "timestamp" if case.get("kind") == "observational" else None,
        "current_setpoint": case.get("current_setpoint"),
        "baseline_source": "platform_recipe" if any(
            f.get("platform_ref") for f in case["factors"]) else "dataset_median",
        "design_region": ({"factorial_bounds": bounds,
                           "design_hull": hull.get(dtype, "imported")}
                          if built else None),
        "ontology": {"profile": "doe", "mode": "auto",
                     "scene_key": case["scene"],
                     "data_stage": "design_only" if case.get("kind") == "design_only"
                     else "collected"},
        "provenance": {"platform": "generality-corpus", "created_by": "generate_cases.py"},
    }


def main(argv=None) -> int:
    force = "--force" in (argv or sys.argv[1:])
    if CASES_DIR.exists() and not force:
        print(f"[skip] {CASES_DIR} exists (use --force)")
        return 0
    if CASES_DIR.exists():
        shutil.rmtree(CASES_DIR)
    CASES_DIR.mkdir(parents=True)
    for i, case in enumerate(cases()):
        out = CASES_DIR / case["id"]
        out.mkdir(parents=True)
        if case.get("kind") == "observational":
            simulate_observational(case, out, SEED + i)
        else:
            simulate_designed(case, out, SEED + i)
        print(f"[case] {case['id']:<26} {case['industry']:<8} "
              f"{(case.get('design') or {}).get('design_type', case.get('kind'))}")
    print(f"[generality] {len(cases())} cases -> {CASES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
