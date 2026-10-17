#!/usr/bin/env python
"""Monte-Carlo interval-coverage check (DS-07 / T-STAT-01, frozen evidence file).

Independent of run_tests.py: refits a known 2^3 factorial `n_rep` times and
measures the POINT coverage of the published intervals against a fresh
observation drawn from the true model:

- `pi_point_coverage`      : should be ~0.95. The prediction interval includes the
                             `1 +` term, so it covers a single future observation at
                             the nominal rate.
- `mean_ci_new_obs_coverage`: should be well BELOW 0.95 (~0.38 at the design
                             centre for 16 runs). This is the quantitative proof
                             that the mean CI (the legacy `ci95` semantics) must not
                             be presented as a prediction bound.
- `pi_wider_than_ci`       : share of points where the PI half-width exceeds the
                             mean-CI half-width (must be 1.0 — contract §5.2 red line).

Deterministic: fixed seed, sorted iteration, no dict-order dependence.

Usage (repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/mc_pi_coverage.py [--rep N] [--seed N]

Writes tests/results/mc_pi_coverage.json.
"""

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))

from doestats import effects_anova as ea  # noqa: E402

RESULTS_DIR = HERE / "results"
OUT_JSON = RESULTS_DIR / "mc_pi_coverage.json"

FACTORS = ("A", "B", "C")
SIGMA = 1.0
BASE = 10.0
TRUTH = {"A": 2.0, "B": -1.5, "AB": 0.4}


def _truth(x):
    a, b, _c = x
    return BASE + TRUTH["A"] * a + TRUTH["B"] * b + TRUTH["AB"] * a * b


def _design_rows():
    """2^3 with 2 replicates (16 runs) — df_resid = 9 for the quadratic-free model."""
    return [tuple(float(v) for v in c)
            for _rep in range(2)
            for c in itertools.product([-1.0, 1.0], repeat=3)]


def run(n_rep=2000, seed=20261017, sigma=SIGMA, x_points=None):
    rng = np.random.default_rng(seed)
    rows = _design_rows()
    basis = np.array(rows)
    y_base = np.array([_truth(r) for r in rows])
    x_points = x_points or [(0.0, 0.0, 0.0), (1.0, 1.0, -1.0), (-1.0, 0.5, 0.0)]
    hits_pi = hits_ci = total = 0
    wider = 0
    for _rep in range(n_rep):
        y = y_base + rng.normal(0.0, sigma, size=len(rows))
        df = pd.DataFrame({c: basis[:, i] for i, c in enumerate(FACTORS)})
        df["y"] = y
        specs = [{"col": c, "type": "numeric"} for c in FACTORS]
        fi = ea.build_factor_info(df, specs)
        bs = ea.base_column_specs(fi)
        bd = ea.code_base_columns(df, bs)
        terms = ea.build_terms(fi)   # mains + 2FI (p = 7, df_resid = 9 on 16 runs)
        _tests, model, _meta = ea.fit_design(df, "y", fi, terms, bd, bs)
        if not model.get("df_resid"):
            continue
        t = float(sps.t.ppf(0.975, model["df_resid"]))
        mse = float(model["mse"])
        for x0 in x_points:
            raw = {c: v for c, v in zip(FACTORS, x0)}
            yhat, se = ea.predict_many(model, [raw])
            yh, s = float(yhat[0]), float(se[0])
            if not (np.isfinite(yh) and np.isfinite(s)):
                continue
            ci_hw = t * s
            pi_hw = t * math.sqrt(s * s + mse)
            y_new = _truth(x0) + rng.normal(0.0, sigma)
            hits_pi += int(abs(y_new - yh) <= pi_hw)
            hits_ci += int(abs(y_new - yh) <= ci_hw)
            wider += int(pi_hw > ci_hw)
            total += 1
    out = {
        "script": "mc_pi_coverage.py",
        "seed": int(seed),
        "n_replications": int(n_rep),
        "n_points": int(total),
        "sigma": float(sigma),
        "design": "2^3 full factorial x2 replicates",
        "pi_point_coverage": round(hits_pi / total, 6) if total else None,
        "mean_ci_new_obs_coverage": round(hits_ci / total, 6) if total else None,
        "pi_wider_than_ci": round(wider / total, 6) if total else None,
        "acceptance": {"pi_point_coverage_band": [0.935, 0.965],
                       "mean_ci_new_obs_coverage_max": 0.90,
                       "pi_wider_than_ci": 1.0},
        "note": ("pi_point_coverage is the point coverage of the 95% PREDICTION "
                 "interval for a single future observation (must be ~0.95). "
                 "mean_ci_new_obs_coverage is the same measurement for the mean "
                 "response CI (the legacy ci95 semantics) and must sit well below "
                 "0.95 — the mean CI is not a prediction bound."),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    out = run(n_rep=args.rep, seed=args.seed)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"[mc-pi-coverage] n_rep={out['n_replications']} points={out['n_points']} "
              f"pi_point_coverage={out['pi_point_coverage']} "
              f"mean_ci_new_obs_coverage={out['mean_ci_new_obs_coverage']} "
              f"pi_wider_than_ci={out['pi_wider_than_ci']}")
        print(f"[mc-pi-coverage] wrote {OUT_JSON}")
    return 0 if (out["pi_point_coverage"] is not None
                 and 0.935 <= out["pi_point_coverage"] <= 0.965) else 1


if __name__ == "__main__":
    sys.exit(main())
