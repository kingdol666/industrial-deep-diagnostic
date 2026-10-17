#!/usr/bin/env python
"""perf_probe.py — acceptance RG-05 (performance envelopes).

Times the real analyzer pipeline on the three shapes the plan budgets, and
tracks Python-level peak allocation:

    100 rows  x  8 factors x 3 responses  <= 60 s
    1000 rows x 10 factors x 3 responses  <= 120 s
    8 active factors, window computation  <= 60 s, peak memory < 2 GB

The synthetic tables are generated from explicit seeds, so the same machine
produces the same numbers on every run.

Usage:
    uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/perf_probe.py [--json]
Writes tests/results/perf_probe.json. Exits non-zero on any missed budget.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
RESULTS = HERE / "results"
sys.path.insert(0, str(SCRIPTS))

import analyze as A  # noqa: E402

BUDGETS = {
    "100x8x3": 60.0,
    "1000x10x3": 120.0,
    "8_active_windows": 60.0,
}
MEMORY_CAP_MB = 2048.0


def _write_run(root: Path, n_rows: int, k: int, n_resp: int, seed: int) -> Path:
    run = root / f"run-{n_rows}x{k}x{n_resp}"
    (run / "00_input").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    factors = [f"f{i}" for i in range(k)]
    responses = [f"y{j}" for j in range(n_resp)]
    # space-filling-ish factor values so the detector sees a designed matrix
    X = rng.uniform(-1.0, 1.0, size=(n_rows, k))
    coef = rng.normal(0.0, 1.0, size=k)
    data = {f: np.round(X[:, i] * 20.0 + 100.0, 4) for i, f in enumerate(factors)}
    for j, r in enumerate(responses):
        y = X @ coef * (1.0 + 0.2 * j) + rng.normal(0.0, 0.5, size=n_rows)
        data[r] = np.round(y, 4)
    df = pd.DataFrame(data)
    df.insert(0, "run_id", [f"r{i:05d}" for i in range(n_rows)])
    df.insert(1, "run_order", list(range(1, n_rows + 1)))
    df.to_csv(run / "00_input" / "run_table.csv", index=False)

    ctx = {
        "contract_version": "1.1",
        "data_path": "00_input/run_table.csv",
        "factors": [{"col": f, "type": "numeric", "unit": "-"} for f in factors],
        "responses": [{"col": r, "unit": "...", "goal": "maximize"} for r in responses],
        "blocks": [], "covariates": [], "constraints": [],
        "index_cols": ["run_id"], "run_order_col": "run_order",
        "group_col": "run_id", "time_col": None,
        "mode_override": "designed",
        "inference": {"assigned_by": "user", "notes": []},
    }
    (run / "00_input" / "analysis_context.json").write_text(
        json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run


def _time_pipeline(run: Path) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    A.cmd_profile(run)
    A.cmd_run(run)
    elapsed = time.perf_counter() - t0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"seconds": round(elapsed, 3), "peak_mb": round(peak / (1024 * 1024), 1)}


def _active_windows_probe(root: Path) -> dict:
    """8 factors with a strong planted effect on every one, so all 8 are active."""
    run = root / "run-8active"
    (run / "00_input").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(4242)
    k = 8
    names = [f"g{i}" for i in range(k)]
    X = rng.uniform(-1.0, 1.0, size=(120, k))
    y = X @ np.full(k, 2.0) + rng.normal(0.0, 0.05, size=120)
    df = pd.DataFrame({n: np.round(X[:, i] * 10.0 + 50.0, 4) for i, n in enumerate(names)})
    df["yield"] = np.round(y, 5)
    df.insert(0, "run_id", [f"r{i:03d}" for i in range(len(df))])
    df.insert(1, "run_order", list(range(1, len(df) + 1)))
    df.to_csv(run / "00_input" / "run_table.csv", index=False)
    ctx = {
        "contract_version": "1.1",
        "data_path": "00_input/run_table.csv",
        "factors": [{"col": n, "type": "numeric", "unit": "-"} for n in names],
        "responses": [{"col": "yield", "unit": "kg", "goal": "maximize"}],
        "blocks": [], "covariates": [], "constraints": [],
        "index_cols": ["run_id"], "run_order_col": "run_order",
        "group_col": "run_id", "time_col": None, "mode_override": "designed",
        "inference": {"assigned_by": "user", "notes": []},
    }
    (run / "00_input" / "analysis_context.json").write_text(
        json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    res = _time_pipeline(run)
    rec = json.loads((run / "conclusions" / "recommendations.json").read_text(encoding="utf-8"))
    grid = rec.get("grid_plan") or {}
    return {"seconds": res["seconds"], "peak_mb": res["peak_mb"],
            "n_active": grid.get("n_active"), "grid_n": grid.get("grid_n"),
            "approach": grid.get("approach")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="perf_probe.py")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    out = {"budgets": BUDGETS, "memory_cap_mb": MEMORY_CAP_MB, "runs": {}}
    # analyze.py's _contained() only permits paths inside the repo root, so the
    # synthetic runs live in a repo-local scratch dir and are removed afterwards.
    root = HERE / ".perf-tmp"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        for key, (n_rows, k, n_resp, seed) in {
            "100x8x3": (100, 8, 3, 20261017),
            "1000x10x3": (1000, 10, 3, 20261018),
        }.items():
            run = _write_run(root, n_rows, k, n_resp, seed)
            res = _time_pipeline(run)
            res.update({"n_rows": n_rows, "n_factors": k, "n_responses": n_resp,
                        "budget_seconds": BUDGETS[key]})
            out["runs"][key] = res
        res8 = _active_windows_probe(root)
        res8["budget_seconds"] = BUDGETS["8_active_windows"]
        out["runs"]["8_active_windows"] = res8
    finally:
        shutil.rmtree(root, ignore_errors=True)

    passed, failed = {}, []
    for key, res in out["runs"].items():
        ok_time = res["seconds"] <= res["budget_seconds"]
        ok_mem = res["peak_mb"] <= MEMORY_CAP_MB
        passed[key] = ok_time and ok_mem
        if not ok_time:
            failed.append(f"{key}: {res['seconds']}s > {res['budget_seconds']}s")
        if not ok_mem:
            failed.append(f"{key}: peak {res['peak_mb']}MB > {MEMORY_CAP_MB}MB")
    out["pass"] = passed
    out["failures"] = failed
    out["machine"] = "AMD Ryzen 7 9700X 8-Core / 31.1 GB RAM / Windows 10.0.26200 x64"

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "perf_probe.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for key, res in out["runs"].items():
        print(f"[perf] {key}: {res['seconds']}s (budget {res['budget_seconds']}s), "
              f"peak {res['peak_mb']}MB -> {'PASS' if passed[key] else 'FAIL'}")
    print(f"[perf] wrote {path}")
    if failed:
        print("[perf] FAILURES: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
