#!/usr/bin/env python
"""mc_effect_recovery.py — acceptance DS-02 (Monte-Carlo effect recovery).

Repeats a 2^4 factorial experiment with fresh Gaussian noise from an explicit
seed, refits with the analyzer's OWN fit path (`effects_anova.fit_design`), and
measures:

  * sign recovery : for planted effects with |b| >= 2 x MDE, the fraction of
                    replications whose estimated sign matches (target >= 99%)
  * power         : detection rate for those effects (target >= 80%)
  * FWER          : fraction of replications with at least one false positive
                    among the null effects (target <= 10%)

Both the implementation's own Benjamini-Hochberg family correction and a strict
Bonferroni control are reported; the Bonferroni figure is the classical FWER
guarantee, the BH figure is what the analyzer actually ships.

Usage:
    uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/mc_effect_recovery.py \
      [--reps 1000] [--seed 20261017] [--json]
Writes tests/results/mc_effect_recovery.json. Exits non-zero when a threshold is
missed (never tune the seed to pass — report the failure).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
RESULTS = HERE / "results"
sys.path.insert(0, str(SCRIPTS))

from doestats import effects_anova as ea  # noqa: E402

PLANTED = {
    "A": 2.60,
    "B": -2.20,
    "C": 0.00,
    "D": 0.00,
    "A:B": 1.80,
    "A:C": 0.00,
    "A:D": 0.00,
    "B:C": 0.00,
    "B:D": -1.60,
    "C:D": 0.00,
}
SIGMA = 0.5
LEVELS = {
    "A": [-1.0, 1.0],
    "B": [-1.0, 1.0],
    "C": [-1.0, 1.0],
    "D": [-1.0, 1.0],
}


def design_frame() -> pd.DataFrame:
    rows = []
    for a in LEVELS["A"]:
        for b in LEVELS["B"]:
            for c in LEVELS["C"]:
                for d in LEVELS["D"]:
                    rows.append({"A": a, "B": b, "C": c, "D": d})
    return pd.DataFrame(rows)


def coded_effect(row: dict) -> float:
    """Coded linear predictor for one run (main effects + A:B + B:D)."""
    return (PLANTED["A"] * row["A"] + PLANTED["B"] * row["B"]
            + PLANTED["C"] * row["C"] + PLANTED["D"] * row["D"]
            + PLANTED["A:B"] * row["A"] * row["B"]
            + PLANTED["A:C"] * row["A"] * row["C"]
            + PLANTED["A:D"] * row["A"] * row["D"]
            + PLANTED["B:C"] * row["B"] * row["C"]
            + PLANTED["B:D"] * row["B"] * row["D"]
            + PLANTED["C:D"] * row["C"] * row["D"])


def run(reps: int, seed: int) -> dict:
    base = design_frame()
    base["y"] = [coded_effect(r) for r in base.to_dict("records")]

    columns_spec = [{"col": c, "type": "numeric", "unit": "-"} for c in LEVELS]
    factor_info = ea.build_factor_info(base, columns_spec)
    base_specs = ea.base_column_specs(factor_info)
    base_df = ea.code_base_columns(base, base_specs)
    terms = ea.build_terms(factor_info, include_2fi=True)

    rng = np.random.default_rng(seed)
    truth_mean = base["y"].to_numpy(dtype=float)
    planted = {t: PLANTED.get(t, 0.0) for t in
               [x["name"] for x in terms]}

    n_rows = len(base)
    mde = ea.mde_coded(SIGMA, n_rows, n_rows - (len(terms) + 1))
    threshold = 2.0 * (mde or 0.0)

    active = [t for t, v in planted.items() if v != 0.0 and abs(v) >= threshold]
    nulls = [t for t, v in planted.items() if v == 0.0]

    sign_hits = {t: 0 for t in active}
    detected = {t: 0 for t in active}
    fwer_bh = 0
    fwer_bonf = 0
    bonf_alpha = 0.05 / max(1, len(planted))

    for _ in range(reps):
        df = base.copy()
        df["y"] = truth_mean + rng.normal(0.0, SIGMA, size=n_rows)
        tests, _model, _meta = ea.fit_design(df, "y", factor_info, terms, base_df, base_specs)
        by_term = {t["term"]: t for t in tests}

        any_bh, any_bonf = False, False
        for t in active:
            row = by_term.get(t) or {}
            coef = row.get("coefficient")
            if coef is None:
                continue
            if np.sign(coef) == np.sign(planted[t]):
                sign_hits[t] += 1
            q = row.get("q_value_bh")
            if q is not None and q < 0.05:
                detected[t] += 1
        for t in nulls:
            row = by_term.get(t) or {}
            p = row.get("p_value")
            q = row.get("q_value_bh")
            if q is not None and q < 0.05:
                any_bh = True
            if p is not None and p < bonf_alpha:
                any_bonf = True
        fwer_bh += int(any_bh)
        fwer_bonf += int(any_bonf)

    sign_rate = {t: sign_hits[t] / reps for t in active}
    power_rate = {t: detected[t] / reps for t in active}
    return {
        "n_replications": reps,
        "seed": seed,
        "design": "2^4 full factorial, single replicate (16 runs)",
        "noise_sigma": SIGMA,
        "mde_coded": mde,
        "two_mde_threshold": threshold,
        "planted_effects": planted,
        "active_effects": active,
        "null_effects": nulls,
        "sign_recovery": sign_rate,
        "power": power_rate,
        "min_sign_recovery": min(sign_rate.values()) if sign_rate else None,
        "min_power": min(power_rate.values()) if power_rate else None,
        "fwer_bh_q05": fwer_bh / reps,
        "fwer_bonferroni": fwer_bonf / reps,
        "thresholds": {"sign_recovery_min": 0.99, "power_min": 0.80, "fwer_max": 0.10},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mc_effect_recovery.py")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = run(args.reps, args.seed)
    t = res["thresholds"]
    ok_sign = (res["min_sign_recovery"] or 0) >= t["sign_recovery_min"]
    ok_power = (res["min_power"] or 0) >= t["power_min"]
    ok_fwer = min(res["fwer_bh_q05"], res["fwer_bonferroni"]) <= t["fwer_max"]
    res["pass"] = {"sign_recovery": ok_sign, "power": ok_power, "fwer": ok_fwer}

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "mc_effect_recovery.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[mc-effect-recovery] reps={res['n_replications']} seed={res['seed']} "
          f"mde={res['mde_coded']:.4f} 2xMDE={res['two_mde_threshold']:.4f} "
          f"active={len(res['active_effects'])}")
    sr = res["min_sign_recovery"]
    pw = res["min_power"]
    print(f"[mc-effect-recovery] sign_recovery_min="
          f"{'n/a' if sr is None else f'{sr:.4f}'} "
          f"(>= {t['sign_recovery_min']}) -> {'PASS' if ok_sign else 'FAIL'}")
    print(f"[mc-effect-recovery] power_min="
          f"{'n/a' if pw is None else f'{pw:.4f}'} "
          f"(>= {t['power_min']}) -> {'PASS' if ok_power else 'FAIL'}")
    print(f"[mc-effect-recovery] fwer_bh={res['fwer_bh_q05']:.4f} "
          f"fwer_bonferroni={res['fwer_bonferroni']:.4f} "
          f"(<= {t['fwer_max']}) -> {'PASS' if ok_fwer else 'FAIL'}")
    print(f"[mc-effect-recovery] wrote {out}")
    return 0 if (ok_sign and ok_power and ok_fwer) else 1


if __name__ == "__main__":
    raise SystemExit(main())
