#!/usr/bin/env python
"""gen_T5_doe.py — Examiner generator for T5 (designed DOE table).

Creates cases/T5_doe_designed/:
  doe_table.csv          2^3 full factorial + 4 center points = 12 runs,
                         randomized run order (seed 20261005)
  analysis_context.json  analysis context pinning designed mode + responses
Injected truth (see truth/T5_truth.json):
  Tear_Strength = 42.0 + 4.2*xA - 3.1*xB + 0*xC + 1.8*xA*xB + N(0, 0.4)
  xA/xB/xC coded to [-1,+1]; physical ranges:
    Extrusion_Temp 175..195 degC (center 185)
    Draw_Ratio      2.0..4.0     (center 3.0)
    Cooling_Rate   15..35 m/min  (center 25)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261005
OUT = Path(__file__).resolve().parent.parent / "T5_doe_designed"
CENTER = {"Extrusion_Temp": 185.0, "Draw_Ratio": 3.0, "Cooling_Rate": 25.0}
HALF = {"Extrusion_Temp": 10.0, "Draw_Ratio": 1.0, "Cooling_Rate": 10.0}


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    design = [(x, y, z)
              for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    design += [(0, 0, 0)] * 4
    order = rng.permutation(len(design))

    rows = []
    for run_no, idx in enumerate(order, start=1):
        xA, xB, xC = design[idx]
        vals = {f: CENTER[f] + x * HALF[f] for f, x in
                zip(CENTER, (xA, xB, xC))}
        tear = 42.0 + 4.2 * xA - 3.1 * xB + 0.0 * xC + 1.8 * xA * xB \
            + rng.normal(0, 0.4)
        rows.append({
            "run_order": run_no,
            "Extrusion_Temp": round(vals["Extrusion_Temp"], 2),
            "Draw_Ratio": round(vals["Draw_Ratio"], 3),
            "Cooling_Rate": round(vals["Cooling_Rate"], 2),
            "Tear_Strength": round(float(tear), 3),
        })
    pd.DataFrame(rows).to_csv(OUT / "doe_table.csv", index=False)

    ctx = {
        "data_path": "00_input/doe_table.csv",
        "mode_override": "designed",
        "responses": [{"col": "Tear_Strength", "goal": "maximize"}],
        "factors": [
            {"col": "Extrusion_Temp", "type": "numeric"},
            {"col": "Draw_Ratio", "type": "numeric"},
            {"col": "Cooling_Rate", "type": "numeric"},
        ],
        "run_order_col": "run_order",
        "alpha": 0.05,
        "inference": {"assigned_by": "user",
                      "notes": ["film extrusion tear-strength study; maximize Tear_Strength"]},
    }
    (OUT / "analysis_context.json").write_text(json.dumps(ctx, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    print("T5 DOE assets written to", OUT)


if __name__ == "__main__":
    main()
