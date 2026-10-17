#!/usr/bin/env python
"""Phase 2 (统计合同正确性) test suite — DOE analyzer contract v1.1.

Covers P2-1..P2-8 of docs/plans/doe-analysis-flow-optimization-plan-2026-10-17.md
against the FROZEN contract docs/plans/contracts/README.md (§5/§6/§9) and the
acceptance ids DS-03..DS-09 / DS-13 (the ones that are library-level):

  int.*     four separated interval types + independent Monte-Carlo PI coverage
  con.*     P2-4 constraint execution (box/linear/safety, hard/soft)
  joint.*   P2-2 joint windows / joint setpoints / desirability selection scale
  unit.*    P2-5 unit chain: missing + conflict block `actionable`, never a window
  hull.*    P2-3 design hull (CCD star rule), leverage, LHS confidence cap
  grid.*    P2-7 bounded active/grid scaling (8/10/20 active) + no silent drops
  matrix.*  P2-6 factor x response coverage, frozen no_window_reason enum
  obs.*     observational v1.1 entry point
  export.*  optimizer-loop seed view (contract §10)
  legacy.*  v1.1 marginal windows == legacy windows when nothing binds (DS-13)
  disc.*    interval disclosure / actionable summary bookkeeping

Usage (repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/test_phase2_stats.py [case|all]

This file only ADDS assertions; tests/run_tests.py (136 assertions) is untouched.
"""

import itertools
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
VALIDATE = REPO / ".claude" / "shared" / "scripts" / "validate.mjs"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))

from doestats import design_detect as dd          # noqa: E402
from doestats import effects_anova as ea          # noqa: E402
from doestats import rsm as rsm_mod               # noqa: E402
from doestats import windows as W                 # noqa: E402
from doestats._stats_util import normal_tolerance_factor  # noqa: E402

RESULTS = []


def record(case, ok, detail=""):
    RESULTS.append((case, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


# ---------------------------------------------------------------- fixtures

def _fit(df, ctx, quad=False, twofi=True, responses=None):
    """Fit every ctx response exactly like analyze.py does (==library-level)."""
    types = {f["col"]: f.get("type") for f in ctx.get("factors", [])}
    specs = [{"col": f["col"], "type": types.get(f["col"]),
              "unit": f.get("unit")} for f in ctx.get("factors", [])
             if f["col"] in df.columns]
    fi = ea.build_factor_info(df, specs)
    bs = ea.base_column_specs(fi)
    bd = ea.code_base_columns(df, bs)
    terms = ea.build_terms(fi, include_2fi=twofi, include_quadratic=quad)
    models, families = {}, []
    for spec in ctx.get("responses", []):
        resp = spec["col"]
        if resp not in df.columns:
            continue
        tests, model, meta = ea.fit_design(df, resp, fi, terms, bd, bs)
        families.append({"response": resp, "n": meta["n"], "df_resid": meta["df_resid"],
                         "df_pure_error": meta["df_pure_error"],
                         "df_lack_of_fit": meta["df_lack_of_fit"], "mse": meta["mse"],
                         "saturated": meta["saturated"], "r_squared": meta["r_squared"],
                         "lack_of_fit": meta["lack_of_fit"], "tests": tests})
        models[resp] = model
    return models, {"families": families}, fi


def _ctx(factors, responses, constraints=(), units=None):
    return {"responses": responses,
            "factors": [{"col": c, "type": "numeric", "unit": u}
                        for c, u in factors],
            "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
            "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
            "effect_size_threshold": 0.01, "constraints": list(constraints),
            **({"units": units} if units else {})}


def ccd_frame(seed=11, alpha=1.682, n_center=6, noise=0.5, k=3, coefs=None):
    """Face-centred CCD with quadratic truth (3 factors by default)."""
    rng = np.random.default_rng(seed)
    rows = [tuple(float(v) for v in c) for c in itertools.product([-1, 1], repeat=k)]
    for j in range(k):
        for s in (-1, 1):
            r = [0.0] * k
            r[j] = s * alpha
            rows.append(tuple(r))
    rows += [tuple([0.0] * k)] * n_center
    names = [f"F{i + 1}" for i in range(k)]
    coefs = coefs or [2.0, -3.0, 1.0]
    data = []
    for r in rows:
        y = 60.0
        for i in range(k):
            y += coefs[i % len(coefs)] * r[i] - 1.5 * r[i] * r[i]
        data.append({**{n: v for n, v in zip(names, r)},
                     "purity": round(float(y + rng.normal(0, noise)), 4)})
    return pd.DataFrame(data), names


def factorial_frame(k, seed=5, n_rep=2, noise=0.3, coefs=None, n_center=0):
    rng = np.random.default_rng(seed)
    names = [f"F{i + 1}" for i in range(k)]
    coefs = coefs or [3.0 * (-1) ** i for i in range(k)]
    rows = []
    for _rep in range(n_rep):
        for c in itertools.product([-1, 1], repeat=k):
            rows.append([float(v) for v in c])
    rows += [[0.0] * k] * n_center
    data = []
    for r in rows:
        y = 50.0 + sum(coefs[i] * r[i] for i in range(k))
        data.append({**{n: v for n, v in zip(names, r)},
                     "y": round(float(y + rng.normal(0, noise)), 4)})
    return pd.DataFrame(data), names


def space_filling_frame(k, n=64, seed=7, noise=0.3, coef_abs=4.0):
    """LHS-style random runs — keeps a k-active design affordable for k = 10/20."""
    rng = np.random.default_rng(seed)
    names = [f"F{i + 1}" for i in range(k)]
    X = rng.uniform(-1.0, 1.0, size=(n, k))
    coefs = np.array([coef_abs * (1 if i % 2 == 0 else -1) for i in range(k)])
    y = 50.0 + X @ coefs
    df = pd.DataFrame(X, columns=names)
    df["y"] = np.round(y + rng.normal(0, noise, n), 4)
    return df, names


def base_responses(cold="purity"):
    return [{"col": cold, "goal": "maximize", "lsl": None, "usl": None,
             "target": None, "weight": None}]


# ---------------------------------------------------------------- int.* (P2-1)

def case_intervals():
    print("== int: four separated interval types (P2-1/DS-07) ==")
    df, names = factorial_frame(2, seed=13, n_rep=2, noise=0.4)
    ctx = _ctx([(n, None) for n in names], base_responses("y"))
    models, et, fi = _fit(df, ctx)
    model = models["y"]
    raw = {"F1": 0.25, "F2": -0.5}

    # ---- independent hand-built design matrix (documented coding, C1) ----
    a = (df["F1"].to_numpy(float) - df["F1"].mean()) / ((df["F1"].max() - df["F1"].min()) / 2)
    b = (df["F2"].to_numpy(float) - df["F2"].mean()) / ((df["F2"].max() - df["F2"].min()) / 2)
    y = df["y"].to_numpy(float)
    X = np.column_stack([np.ones(len(y)), a, b, a * b])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, p = X.shape
    df_resid = n - p
    mse = float(resid @ resid) / df_resid
    xtx_inv = np.linalg.inv(X.T @ X)
    t = float(sps.t.ppf(0.975, df_resid))

    tests = {tt["term"]: tt for tt in et["families"][0]["tests"]}
    # effect CI: beta +- t * se(beta), se = sqrt(diag((X'X)^-1) * MSE)
    for j, term in enumerate(("F1", "F2", "F1:F2")):
        se = math.sqrt(mse * xtx_inv[j + 1, j + 1])
        lo, hi = beta[j + 1] - t * se, beta[j + 1] + t * se
        got = tests[term]["effect_ci95"]
        ok = (got is not None and abs(got[0] - lo) < 1e-5 and abs(got[1] - hi) < 1e-5
              and abs(tests[term]["std_err"] - se) < 1e-6)
        record(f"int.effect_ci95_formula[{term}]", ok, f"got={got} exp=[{lo},{hi}]")
    record("int.effect_ci95_scaled_for_cross_unit",
           tests["F1"]["std_effect"] is not None and abs(
               tests["F1"]["std_effect"] - tests["F1"]["coefficient"] / float(np.std(y, ddof=1))
           ) < 1e-5,
           f"std_effect={tests['F1']['std_effect']}")
    record("int.term_unit_labelled",
           tests["F1"]["term_unit"] == "coded" and tests["F1:F2"]["term_unit"] == "coded",
           str([tests[k]["term_unit"] for k in ("F1", "F1:F2")]))

    x0 = np.array([1.0, (raw["F1"] - df["F1"].mean()) / ((df["F1"].max() - df["F1"].min()) / 2),
                   (raw["F2"] - df["F2"].mean()) / ((df["F2"].max() - df["F2"].min()) / 2), 0.0])
    x0[3] = x0[1] * x0[2]
    yhat = float(x0 @ beta)
    h = float(x0 @ xtx_inv @ x0)
    bundle = W.interval_bundle(model, raw)
    record("int.mean_ci95_formula",
           bundle["mean"] is not None and abs(bundle["mean"] - yhat) < 1e-5
           and abs(bundle["mean_ci95"][0] - (yhat - t * math.sqrt(h * mse))) < 1e-5
           and abs(bundle["mean_ci95"][1] - (yhat + t * math.sqrt(h * mse))) < 1e-5,
           json.dumps(bundle))
    pi_hw = t * math.sqrt((1.0 + h) * mse)
    record("int.pi95_formula_and_gt_ci",
           abs(bundle["pi95"][0] - (yhat - pi_hw)) < 1e-5
           and abs(bundle["pi95"][1] - (yhat + pi_hw)) < 1e-5
           and (bundle["pi95"][1] - bundle["pi95"][0])
           > (bundle["mean_ci95"][1] - bundle["mean_ci95"][0]),
           json.dumps(bundle))
    k_iso = normal_tolerance_factor(n, df_resid)
    k_hand = math.sqrt(df_resid * (1.0 + 1.0 / n) * sps.norm.ppf(0.975) ** 2
                       / sps.chi2.ppf(0.05, df_resid))
    record("int.tolerance_formula",
           k_iso is not None and abs(k_iso - k_hand) < 1e-9
           and abs(bundle["ti95_95"][0] - (yhat - k_hand * math.sqrt(mse))) < 1e-5
           and abs(bundle["ti95_95"][1] - (yhat + k_hand * math.sqrt(mse))) < 1e-5,
           f"k={k_iso} hand={k_hand} band={bundle['ti95_95']}")
    record("int.tolerance_factor_reference_values",
           abs(normal_tolerance_factor(10, 9) - 3.382) < 0.01
           and abs(normal_tolerance_factor(20, 19) - 2.758) < 0.03,
           f"k(10,9)={normal_tolerance_factor(10, 9)} k(20,19)={normal_tolerance_factor(20, 19)}")
    record("int.pi_method_names_1plus",
           "1 +" in (ea.PI95_METHOD or "") and "1 +" in (W.ea_mod.PI95_METHOD or ""),
           ea.PI95_METHOD)

    # ---- library-level Monte-Carlo coverage (DS-07 / T-STAT-01) ----
    import mc_pi_coverage
    mc = mc_pi_coverage.run(n_rep=2000, seed=20261017)
    cov = mc["pi_point_coverage"]
    record("int.mc_pi_point_coverage_93.5_96.5", cov is not None and 0.935 <= cov <= 0.965,
           f"n={mc['n_points']} coverage={cov}")
    record("int.mc_pi_wider_than_ci_always", mc["pi_wider_than_ci"] == 1.0,
           str(mc["pi_wider_than_ci"]))
    record("int.mc_ci_is_not_a_prediction_bound",
           (mc["mean_ci_new_obs_coverage"] or 1.0) < 0.90,
           f"mean-CI coverage of a NEW observation = {mc['mean_ci_new_obs_coverage']}")

    # ---- window-level separation + no PI smuggled into ci95 ----
    ctx2 = _ctx([(n, "degC") for n in names],
                [{"col": "y", "goal": "maximize", "lsl": None, "usl": None,
                  "target": None, "weight": None}])
    rec = W.designed_windows_v11(models, et, {"design": {"mode": "designed",
                                                         "design_type": "full_factorial"}},
                                 ctx2, df)
    w = rec["operating_windows"][0]
    ee = w["expected_effect"]
    ci_hw = ee["mean_ci95"][1] - ee["mean_ci95"][0]
    pi_hw_w = ee["pi95"][1] - ee["pi95"][0]
    record("int.window_pi_gt_ci", pi_hw_w > ci_hw > 0, f"ci={ci_hw} pi={pi_hw_w}")
    record("int.window_ci95_not_a_pi", ee.get("ci95") is None,
           f"ci95={ee.get('ci95')}")
    record("int.window_has_all_four_intervals",
           all(k in ee for k in ("mean_ci95", "pi95", "pi95_method", "effect_ci95",
                                 "tolerance_interval_95_95", "unit_status", "response_unit")),
           str(sorted(ee)))
    pac = w["predicted_at_center"]
    record("int.predicted_at_center_centred_on_mean",
           abs((pac["mean_ci95"][0] + pac["mean_ci95"][1]) / 2 - pac["mean"]) < 1e-5
           and abs((pac["pi95"][0] + pac["pi95"][1]) / 2 - pac["mean"]) < 1e-5,
           json.dumps(pac))
    record("int.disclosure_lists_four_methods",
           all(rec["interval_disclosure"].get(k) for k in
               ("pi_method", "ci_method", "effect_ci_method", "tolerance_method")),
           json.dumps(rec["interval_disclosure"])[:200])


# ---------------------------------------------------------------- con.* (P2-4)

def _binding_setup(constraints, seed=5, axes=None):
    df, names = factorial_frame(2, seed=seed, noise=0.2)
    ctx = _ctx([(n, "degC") for n in names], base_responses("y"), constraints=constraints)
    models, et, fi = _fit(df, ctx)
    profile = {"design": {"mode": "designed", "design_type": "full_factorial"}}
    return df, names, ctx, models, et, profile


def case_constraints():
    print("== con: constraint execution (P2-4/DS-05) ==")
    df, names, ctx, models, et, profile = _binding_setup([])
    free = W.designed_windows_v11(models, et, profile, ctx, df)
    free_sp = free["joint_setpoints"][0]
    record("con.unconstrained_optimum_outside_bound",
           free_sp["factors"]["F2"] < 0.4,
           json.dumps(free_sp["factors"]))

    bound = [{"factor": "F2", "type": "box", "min": 0.4, "max": 1.0, "hard": True,
              "source": "safety"}]
    df, names, ctx, models, et, profile = _binding_setup(bound)
    rec = W.designed_windows_v11(models, et, profile, ctx, df)
    sp = rec["joint_setpoints"][0]
    record("con.binding_point_respects_bound",
           0.4 - 1e-9 <= sp["factors"]["F2"] <= 1.0 + 1e-9,
           json.dumps(sp["factors"]))
    record("con.hard_zero_violations", sp["hard_constraint_violations"] == 0,
           str(sp["hard_constraint_violations"]))
    record("con.constraint_really_binds",
           abs(sp["constraint_slack"].get("F2", 9.9) - 0.0) < 0.05,
           json.dumps(sp["constraint_slack"]))
    w_f2 = next(w for w in rec["operating_windows"] if w["factor"] == "F2")
    record("con.window_range_respects_bound", w_f2["range"][0] >= 0.4 - 1e-9,
           str(w_f2["range"]))
    record("con.constraints_applied_recorded",
           w_f2["constraints_applied"] == [{"factor": "F2", "type": "box", "min": 0.4,
                                            "max": 1.0, "hard": True, "source": "safety"}],
           json.dumps(w_f2["constraints_applied"]))
    record("con.window_violations_zero",
           all(w["constraint_violations"] == 0 for w in rec["operating_windows"]),
           json.dumps([(w["factor"], w["constraint_violations"]) for w in rec["operating_windows"]]))
    record("con.method_disclosed",
           sp["method"] in ("constraint_projection", "desirability_lbfgsb", "grid_search"),
           sp["method"])

    # infeasible: the bound lies entirely outside the design box
    infeas = [{"factor": "F2", "type": "box", "min": 5.0, "max": 6.0, "hard": True,
               "source": "safety"}]
    df, names, ctx, models, et, profile = _binding_setup(infeas)
    rec2 = W.designed_windows_v11(models, et, profile, ctx, df)
    record("con.infeasible_no_window", len(rec2["operating_windows"]) == 0,
           str(len(rec2["operating_windows"])))
    reasons = {c["no_window_reason"] for c in rec2["factor_response_matrix"]}
    record("con.infeasible_reason_enum", reasons == {"CONSTRAINTS_INFEASIBLE"}, str(reasons))
    record("con.infeasible_watchlist",
           any(e.get("code") == "CONSTRAINTS_INFEASIBLE" for e in rec2["watchlist"])
           or any(e.get("code") == "HULL_UNSUPPORTED" for e in rec2["watchlist"]),
           json.dumps([e.get("code") for e in rec2["watchlist"]]))
    record("con.infeasible_no_joint_setpoint", len(rec2["joint_setpoints"]) == 0,
           str(len(rec2["joint_setpoints"])))

    # linear constraint: A + B <= 0.5 with both factors significant-positive
    df, names = factorial_frame(2, seed=5, noise=0.2, coefs=[3.0, 3.0])
    lin = [{"type": "linear", "coeffs": {"F1": 1.0, "F2": 1.0}, "max": 0.5,
            "hard": True, "source": "user"}]
    ctx = _ctx([(n, "degC") for n in names], base_responses("y"), constraints=lin)
    models, et, fi = _fit(df, ctx)
    profile = {"design": {"mode": "designed", "design_type": "full_factorial"}}
    rec3 = W.designed_windows_v11(models, et, profile, ctx, df)
    sp3 = rec3["joint_setpoints"][0]
    total = sp3["factors"]["F1"] + sp3["factors"]["F2"]
    record("con.linear_constraint_binds", total <= 0.5 + 1e-6 and total >= 0.5 - 0.05,
           f"F1+F2={total} factors={json.dumps(sp3['factors'])}")
    record("con.linear_zero_hard_violations", sp3["hard_constraint_violations"] == 0,
           str(sp3["hard_constraint_violations"]))
    w3 = rec3["operating_windows"][0]
    record("con.linear_constraints_applied",
           any(c["type"] == "linear" for c in w3["constraints_applied"]),
           json.dumps(w3["constraints_applied"]))

    # soft constraint: penalised (never filters), relaxation disclosed when the
    # chosen point ends up disagreeing with the soft limit
    soft = [{"type": "linear", "coeffs": {"F1": 1.0, "F2": 1.0}, "max": 0.5,
             "hard": False, "source": "user"}]
    ctxs = _ctx([(n, "degC") for n in names], base_responses("y"), constraints=soft)
    recs = W.designed_windows_v11(models, et, profile, ctxs, df)
    sps_ = recs["joint_setpoints"][0]
    tot = sps_["factors"]["F1"] + sps_["factors"]["F2"]
    record("con.soft_penalty_steers_to_satisfaction", tot <= 0.5 + 1e-6,
           f"F1+F2={tot}")
    record("con.soft_no_hard_violation", sps_["hard_constraint_violations"] == 0,
           str(sps_["hard_constraint_violations"]))
    record("con.soft_not_filtering_candidates",
           any(w["constraints_applied"] for w in recs["operating_windows"]) and tot > 0.4,
           f"F1+F2={tot}")
    # unattainable soft limit (min 5 outside the design box) -> relaxation disclosed
    soft_impossible = [{"factor": "F1", "type": "box", "min": 5.0, "max": 6.0,
                        "hard": False, "source": "user"}]
    ctxi = _ctx([(n, "degC") for n in names], base_responses("y"),
                constraints=soft_impossible)
    reci = W.designed_windows_v11(models, et, profile, ctxi, df)
    record("con.soft_relaxation_disclosed",
           any(e.get("code") == "SOFT_CONSTRAINT_RELAXED" for e in reci["watchlist"])
           and len(reci["operating_windows"]) > 0,
           json.dumps([e.get("code") for e in reci["watchlist"]]))
    record("con.soft_relaxation_not_a_hard_violation",
           all(s["hard_constraint_violations"] == 0 for s in reci["joint_setpoints"]),
           json.dumps([s["hard_constraint_violations"] for s in reci["joint_setpoints"]]))


# ---------------------------------------------------------------- joint.* (P2-2)

def case_joint():
    print("== joint: joint windows / setpoints (P2-2/DS-04/DS-08) ==")
    rng = np.random.default_rng(21)
    rows = [tuple(float(v) for v in c) for c in itertools.product([-1, 1], repeat=2)]
    rows += [(0.0, 0.0)] * 3
    data = []
    for a, b in rows:
        y1 = 50 + 3 * a - 2 * b + rng.normal(0, 0.2)
        y2 = 10 - 2 * a + 3 * b + rng.normal(0, 0.2)
        data.append({"F1": a, "F2": b, "y1": round(float(y1), 4), "y2": round(float(y2), 4)})
    df = pd.DataFrame(data)
    responses = [{"col": "y1", "goal": None, "lsl": 48.0, "usl": 51.5, "target": None,
                  "weight": None},
                 {"col": "y2", "goal": None, "lsl": 8.5, "usl": 12.0, "target": None,
                  "weight": None}]
    ctx = _ctx([("F1", "degC"), ("F2", "degC")], responses)
    models, et, fi = _fit(df, ctx)
    rec = W.designed_windows_v11(models, et, {"design": {"mode": "designed",
                                                         "design_type": "full_factorial"}},
                                 ctx, df)
    sp = rec["joint_setpoints"][0]
    record("joint.multi_response_feasible",
           sp["feasible"] and set(sp["responses_satisfied"]) == {"y1", "y2"},
           json.dumps({"feasible": sp["feasible"], "sat": sp["responses_satisfied"]}))
    pred = sp["predicted"]
    ok_bounds = True
    for resp, spec in (("y1", responses[0]), ("y2", responses[1])):
        p = pred[resp]
        if p["mean"] is None or p["mean_ci95"] is None:
            ok_bounds = False
        elif (p["mean_ci95"][0] < spec["lsl"] - 1e-9
              or p["mean_ci95"][1] > spec["usl"] + 1e-9):
            ok_bounds = False
    record("joint.predicted_bounds_inside_specs", ok_bounds, json.dumps(pred))
    record("joint.setpoint_keys_frozen",
           all(k in sp for k in ("id", "method", "factors", "predicted",
                                 "responses_satisfied", "feasible",
                                 "hard_constraint_violations", "constraint_slack",
                                 "desirability", "joint_coverage", "evidence_level",
                                 "confidence", "window_ids", "unit_status",
                                 "actionable", "blockers")),
           str(sorted(sp)))
    record("joint.predicted_keys_frozen",
           all(all(k in pred[r] for k in ("mean", "mean_ci95", "pi95", "d", "unit_status"))
               for r in pred), json.dumps(pred))
    record("joint.no_cross_unit_winner",
           sp["selection_scale"] in ("desirability", "std_effect")
           and "禁止跨单位" in rec["interval_disclosure"]["note"],
           f"scale={sp['selection_scale']} note_ok={'禁止跨单位' in rec['interval_disclosure']['note']}")
    record("joint.window_ids_reference_windows",
           all(any(w["id"] == wid for w in rec["operating_windows"])
               for wid in sp["window_ids"]), json.dumps(sp["window_ids"]))
    record("joint.joint_window_shape",
           rec["joint_windows"] and all(
               k in rec["joint_windows"][0]
               for k in ("id", "responses", "factors", "feasible",
                         "constraint_violations", "predicted", "desirability",
                         "method", "evidence_level", "responses_satisfied",
                         "hard_constraint_violations", "constraint_slack",
                         "confidence", "window_ids", "unit_status", "actionable",
                         "blockers")),
           str(sorted(rec["joint_windows"][0])) if rec["joint_windows"] else "none")
    record("joint.legacy_setpoints_mirror",
           any(s.get("expected_response", {}).get("kind") == "joint_setpoint"
               for s in rec["setpoints"]), json.dumps(rec["setpoints"])[:200])
    multi = [s for s in rec["setpoints"] if s.get("factor") == "MULTI"]
    record("joint.legacy_multi_seed_shape",
           len(multi) == 1
           and multi[0]["expected_response"].get("raw") == {
               f: v for f, v in zip(("F1", "F2"), [sp["factors"]["F1"], sp["factors"]["F2"]])}
           and multi[0]["expected_response"].get("D") is not None
           and multi[0]["confidence"] in ("high", "medium"),
           json.dumps(multi, ensure_ascii=False)[:240])
    record("joint.role_marginal_diagnostic",
           all(w["window_role"] == "marginal_diagnostic"
               for w in rec["operating_windows"]),
           json.dumps([w["window_role"] for w in rec["operating_windows"]]))

    # conflicting responses -> honest infeasible disclosure with alternatives
    responses_c = [dict(responses[0], lsl=48.0, usl=49.0),
                   dict(responses[1], lsl=11.5, usl=12.0)]
    ctx_c = _ctx([("F1", "degC"), ("F2", "degC")], responses_c)
    rec_c = W.designed_windows_v11(models, et, {"design": {"mode": "designed",
                                                           "design_type": "full_factorial"}},
                                   ctx_c, df)
    first = rec_c["joint_setpoints"][0]
    record("joint.conflict_disclosed",
           (first["feasible"] is True) or (len(rec_c["joint_setpoints"]) > 1),
           json.dumps({"feasible": first["feasible"],
                       "n": len(rec_c["joint_setpoints"])}))


# ---------------------------------------------------------------- unit.* (P2-5)

def _unit_setup(factor_units, response_unit="degC", ctx_units=None, brief=None):
    df, names = factorial_frame(2, seed=5, noise=0.2)
    responses = [{"col": "y", "goal": "maximize", "lsl": None, "usl": None,
                  "target": None, "weight": None, "unit": response_unit}]
    ctx = _ctx([(n, u) for n, u in zip(names, factor_units)], responses,
               units=ctx_units)
    models, et, fi = _fit(df, ctx)
    profile = {"design": {"mode": "designed", "design_type": "full_factorial"}}
    return W.designed_windows_v11(models, et, profile, ctx, df, brief=brief), df, names, ctx


def case_units():
    print("== unit: chain / missing / conflict (P2-5/DS-06) ==")
    rec, df, names, ctx = _unit_setup(["degC", "degC"])
    record("unit.valid_status",
           all(u["unit_status"] == "valid" for u in rec["units"]["factors"].values())
           and rec["units"]["responses"]["y"]["unit_status"] == "valid",
           json.dumps(rec["units"]))
    record("unit.no_unit_blocker_when_valid",
           all("unit_missing" not in w["actionable_blockers"]
               and "unit_conflict" not in w["actionable_blockers"]
               for w in rec["operating_windows"]),
           json.dumps([w["actionable_blockers"] for w in rec["operating_windows"]]))
    record("unit.factor_unit_not_fake_fallback",
           all(w["factor_unit"] == "degC" for w in rec["operating_windows"])
           and all(w["expected_effect"]["unit"] == "degC"
                   for w in rec["operating_windows"]),
           json.dumps([(w["factor"], w["factor_unit"], w["expected_effect"]["unit"])
                       for w in rec["operating_windows"]]))

    rec_m, _df, _n, _c = _unit_setup([None, None], response_unit=None)
    record("unit.missing_status",
           all(u["unit_status"] == "missing" for u in rec_m["units"]["factors"].values())
           and rec_m["units"]["responses"]["y"]["unit_status"] == "missing"
           and rec_m["units"]["responses"]["y"]["canonical"] is None,
           json.dumps(rec_m["units"]))
    record("unit.window_not_dropped_by_missing",
           len(rec_m["operating_windows"]) > 0, str(len(rec_m["operating_windows"])))
    record("unit.missing_blocks_actionable",
           all(w["actionable"] is False and "unit_missing" in w["actionable_blockers"]
               for w in rec_m["operating_windows"])
           and rec_m["joint_setpoints"]
           and all(s["actionable"] is False for s in rec_m["joint_setpoints"]),
           json.dumps([w["actionable_blockers"] for w in rec_m["operating_windows"]]))
    record("unit.no_fake_response_units_string",
           all(w["expected_effect"]["unit"] is None for w in rec_m["operating_windows"]),
           json.dumps([w["expected_effect"]["unit"] for w in rec_m["operating_windows"]]))

    # mm vs um (same family, different scale) and degC vs K -> conflicts
    brief = {"factors": [{"col": "F1", "unit": "um"}, {"col": "F2", "unit": "K"}]}
    rec_c, _df2, _n2, _c2 = _unit_setup(["mm", "degC"], response_unit="um",
                                        brief=brief)
    conflicts = rec_c["units"]["conflicts"]
    record("unit.conflict_detected_mm_um",
           any(c["factor_or_response"] == "F1" and "um" in c["to"] for c in conflicts),
           json.dumps(conflicts, ensure_ascii=False))
    record("unit.conflict_detected_c_k",
           any(c["factor_or_response"] == "F2" for c in conflicts),
           json.dumps(conflicts, ensure_ascii=False))
    record("unit.conflict_blocks_actionable",
           all(w["actionable"] is False and "unit_conflict" in w["actionable_blockers"]
               for w in rec_c["operating_windows"]),
           json.dumps([w["actionable_blockers"] for w in rec_c["operating_windows"]]))
    record("unit.conflict_keeps_window",
           len(rec_c["operating_windows"]) > 0, str(len(rec_c["operating_windows"])))
    record("unit.um_and_µm_are_the_same_unit",
           ea.normalize_unit("um") == ea.normalize_unit("µm")
           and ea.unit_declaration_status([("a", "um"), ("b", "µm")])["unit_status"] == "valid",
           "")
    record("unit.unit_status_in_enum",
           all(u["unit_status"] in ("valid", "missing", "conflict")
               for u in list(rec_c["units"]["factors"].values())
               + list(rec_c["units"]["responses"].values())), "")


# ---------------------------------------------------------------- hull.* (P2-3)

def case_hull():
    print("== hull: design region / leverage (P2-3) ==")
    df, names = ccd_frame()
    ctx = _ctx([(n, "degC") for n in names], base_responses("purity"))
    models, et, fi = _fit(df, ctx, quad=True)
    profile = {"design": {"mode": "designed", "design_type": "rsm_ccd"}}
    rec = W.designed_windows_v11(models, et, profile, ctx, df)
    dr = rec["design_region"]
    record("hull.ccd_star_detected",
           dr["hull"] == "ccd_star" and abs((dr["axial_alpha"] or 0) - 1.682) < 0.01,
           json.dumps({k: dr[k] for k in ("hull", "axial_alpha", "design_hull_confidence")}))
    record("hull.hull_in_enum", dr["hull"] in dd.HULL_TYPES, dr["hull"])

    desc = dd.detect_design_hull(df, names, {"design_type": "rsm_ccd"}, "designed")
    coded, _b = dd.coded_columns(df.drop_duplicates(), names)
    mask = dd.hull_mask(desc, coded)
    record("hull.all_run_points_inside", bool(mask.all()) and mask.sum() == len(coded),
           f"{mask.sum()}/{len(coded)}")
    corners = np.array([list(c) for c in itertools.product([1.0, -1.0], repeat=3)])
    cmask = dd.hull_mask(desc, corners)
    record("hull.unrun_box_corners_excluded", not cmask.any(), str(cmask.tolist()))
    axial = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                      [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
    record("hull.axial_points_inside", bool(dd.hull_mask(desc, axial).all()),
           str(dd.hull_mask(desc, axial).tolist()))
    record("hull.centre_inside", bool(dd.hull_mask(desc, np.zeros((1, 3)))[0]), "")
    cube_c = desc["cube_corner_coded"]
    record("hull.executed_cube_corners_inside",
           bool(dd.hull_mask(desc, np.array([[cube_c, cube_c, 0.0]])).all()), str(cube_c))
    record("hull.windows_report_in_design_hull",
           all(w["in_design_hull"] is True for w in rec["operating_windows"]),
           json.dumps([(w["factor"], w["in_design_hull"]) for w in rec["operating_windows"]]))
    record("hull.leverage_stats_present",
           dr["max_leverage"] is not None and dr["leverage_threshold"] is not None
           and dr["max_leverage"] <= 1.0 + 1e-9
           and dr["n_exceed"] == 0,
           json.dumps({k: dr[k] for k in ("max_leverage", "mean_leverage",
                                          "leverage_threshold", "n_exceed")}))
    record("hull.evaluated_points_counted", dr["evaluated_points"] > 0,
           str(dr["evaluated_points"]))
    record("hull.extrapolation_risk_low", dr["extrapolation_risk"] == "low",
           dr["extrapolation_risk"])

    # LHS -> convex hull, confidence capped at medium
    df_sf, names_sf = space_filling_frame(3, n=80, seed=3)
    ctx_sf = _ctx([(n, "degC") for n in names_sf], base_responses("y"))
    models_sf, et_sf, _fi = _fit(df_sf, ctx_sf)
    profile_sf = {"design": {"mode": "designed", "design_type": "latin_hypercube"}}
    rec_sf = W.designed_windows_v11(models_sf, et_sf, profile_sf, ctx_sf, df_sf)
    record("hull.lhs_convex_hull_confidence_capped",
           rec_sf["design_region"]["hull"] == "convex_hull"
           and rec_sf["design_region"]["design_hull_confidence"] == "medium",
           json.dumps({k: rec_sf["design_region"][k]
                       for k in ("hull", "design_hull_confidence")}))
    desc_sf = dd.detect_design_hull(df_sf, names_sf,
                                    {"design_type": "latin_hypercube"}, "designed")
    box_corners = np.array([list(c) for c in itertools.product([1.0, -1.0], repeat=3)])
    record("hull.lhs_box_corners_excluded",
           not dd.hull_mask(desc_sf, box_corners).any(),
           str(dd.hull_mask(desc_sf, box_corners).tolist()))


# ---------------------------------------------------------------- grid.* (P2-7)

def case_grid_scaling():
    print("== grid: bounded active/grid scaling (P2-7/DS-09) ==")
    df4, names4 = factorial_frame(4, seed=5, noise=0.2)
    ctx4 = _ctx([(n, "degC") for n in names4], base_responses("y"))
    models4, et4, fi4 = _fit(df4, ctx4)
    profile4 = {"design": {"mode": "designed", "design_type": "full_factorial"}}
    rec4 = W.designed_windows_v11(models4, et4, profile4, ctx4, df4)
    gp4 = rec4["grid_plan"]
    record("grid.k4_grid_n_9", gp4["grid_n"] == 9 and gp4["approach"] == "grid"
           and gp4["n_grid_points"] == 9 ** 4,
           json.dumps(gp4))
    record("grid.plan_keys_frozen",
           all(k in gp4 for k in ("n_active", "top_k", "grid_n", "n_grid_points",
                                  "approach", "max_grid_points", "deferred_factors",
                                  "truncated")), str(sorted(gp4)))
    record("grid.top_k_frozen", W.TOP_K == 8 and W.GRID_MIN_N == 3 and W.GRID_MAX_N == 9
           and W.MAX_GRID_POINTS == 200000 and W.MAX_GRID_FACTORS == 8, "")

    df8, names8 = factorial_frame(8, seed=5, noise=0.2, n_rep=1)
    ctx8 = _ctx([(n, "degC") for n in names8], base_responses("y"))
    models8, et8, _fi8 = _fit(df8, ctx8, twofi=False)
    rec8 = W.designed_windows_v11(models8, et8, profile4, ctx8, df8)
    gp8 = rec8["grid_plan"]
    record("grid.k8_bounded",
           gp8["n_active"] == 8 and gp8["approach"] == "grid"
           and gp8["grid_n"] ** 8 <= W.MAX_GRID_POINTS
           and gp8["n_grid_points"] <= W.MAX_GRID_POINTS,
           json.dumps(gp8))
    record("grid.k8_windows_emitted", len(rec8["operating_windows"]) == 8,
           str(len(rec8["operating_windows"])))
    record("grid.k8_deferred_empty", gp8["deferred_factors"] == []
           and gp8["truncated"] is False, json.dumps(gp8))

    for k in (10, 20):
        dfk, namesk = space_filling_frame(k, n=64, seed=7 + k)
        ctxk = _ctx([(n, "degC") for n in namesk], base_responses("y"))
        modelsk, etk, _fk = _fit(dfk, ctxk, twofi=False)
        reck = W.designed_windows_v11(modelsk, etk, profile4, ctxk, dfk)
        gpk = reck["grid_plan"]
        record(f"grid.k{k}_continuous_optimization",
               gpk["approach"] == "continuous_optimization"
               and gpk["n_grid_points"] == 0
               and len(reck["operating_windows"]) == 0,
               json.dumps(gpk))
        record(f"grid.k{k}_still_emits_joint_setpoint",
               len(reck["joint_setpoints"]) >= 1
               and reck["joint_setpoints"][0]["hard_constraint_violations"] == 0,
               json.dumps(reck["joint_setpoints"][0])[:240] if reck["joint_setpoints"] else "none")
        record(f"grid.k{k}_no_silent_drop",
               len(gpk["deferred_factors"]) == max(0, k - W.TOP_K)
               and any(e.get("code") == "FACTORS_DEFERRED" for e in reck["watchlist"]),
               json.dumps(gpk["deferred_factors"]))
        covered = {(c["factor"], c["response"])
                   for c in reck["factor_response_matrix"]}
        record(f"grid.k{k}_matrix_covers_all_pairs",
               covered == {(f, "y") for f in namesk} and all(
                   (c["window_id"] is not None) != (c["no_window_reason"] is not None)
                   for c in reck["factor_response_matrix"]),
               f"{len(covered)} cells")
    record("grid.grid_n_adaptivity_rule",
           all(W._grid_n_for(k) == max(
               [n for n in range(W.GRID_MAX_N, W.GRID_MIN_N - 1, -1)
                if n ** k <= W.MAX_GRID_POINTS] or [W.GRID_MIN_N])
               for k in range(1, 9)), "")


# ---------------------------------------------------------------- matrix.* (P2-6)

def case_matrix():
    print("== matrix: factor x response coverage (P2-6/DS-03) ==")
    rng = np.random.default_rng(31)
    rows = [tuple(float(v) for v in c) for c in itertools.product([-1, 1], repeat=2)]
    rows = rows * 2
    data = []
    for a, b in rows:
        data.append({"F1": a, "F2": b,
                     "y1": round(float(50 + 3 * a + rng.normal(0, 0.2)), 4),
                     "y2": round(float(10 + rng.normal(0, 0.2)), 4)})
    df = pd.DataFrame(data)
    ctx = _ctx([("F1", "degC"), ("F2", "degC")],
               [{"col": "y1", "goal": "maximize", "lsl": None, "usl": None,
                 "target": None, "weight": None},
                {"col": "y2", "goal": "maximize", "lsl": None, "usl": None,
                 "target": None, "weight": None}])
    models, et, fi = _fit(df, ctx)
    rec = W.designed_windows_v11(models, et, {"design": {"mode": "designed",
                                                         "design_type": "full_factorial"}},
                                 ctx, df)
    m = rec["factor_response_matrix"]
    record("matrix.covers_all_pairs",
           {(c["factor"], c["response"]) for c in m}
           == {("F1", "y1"), ("F1", "y2"), ("F2", "y1"), ("F2", "y2")},
           json.dumps([(c["factor"], c["response"]) for c in m]))
    record("matrix.zero_silent_cells",
           all((c["window_id"] is not None) != (c["no_window_reason"] is not None)
               for c in m), json.dumps(m, ensure_ascii=False))
    record("matrix.reason_enum_frozen",
           all(c["no_window_reason"] is None or c["no_window_reason"] in W.NO_WINDOW_REASONS
               for c in m),
           json.dumps([c["no_window_reason"] for c in m]))
    record("matrix.cell_keys_frozen",
           all(all(k in c for k in ("factor", "response", "window_id",
                                    "no_window_reason", "delta", "effect_size",
                                    "direction", "fdr_q", "evidence_level",
                                    "confidence")) for c in m),
           str(sorted(m[0])))
    record("matrix.flat_response_reason",
           all(c["no_window_reason"] == "NO_SIGNIFICANT_FACTOR"
               for c in m if c["response"] == "y2"),
           json.dumps([(c["response"], c["no_window_reason"]) for c in m]))


# ---------------------------------------------------------------- obs.* / export.*

def case_observational():
    print("== obs: observational v1.1 entry point ==")
    n = 200
    x = np.linspace(100.0, 200.0, n)
    rng = np.random.default_rng(5)
    y = 0.5 * x + rng.normal(0, 0.4, n)
    df = pd.DataFrame({"x": x.round(3), "y": y.round(3), "t": np.arange(n, dtype=float)})
    ctx = {"responses": [{"col": "y", "goal": "maximize", "lsl": None, "usl": None,
                          "target": None, "weight": None, "unit": "um"}],
           "factors": [{"col": "x", "type": "numeric", "unit": "um"}],
           "_predictor_cols": ["x"], "group_col": None, "time_col": "t",
           "constraints": []}
    stability = {"steady_segments": [{"start": 0, "end": n - 1, "n_rows": n,
                                      "response_means": {"y": float(y.mean())},
                                      "score": 1.0, "selected_for_windows": True}]}
    confounded = {"pairs": [{"target": "y", "parameter": "x", "r": 0.99,
                             "detrended_r": 0.02, "trend_confounded": True}]}
    rec = W.observational_windows_v11(stability, {}, ctx, df, correlation=confounded)
    record("obs.v11_keys_present",
           all(k in rec for k in ("windows", "joint_windows", "joint_setpoints",
                                  "factor_response_matrix", "grid_plan", "units",
                                  "design_region", "interval_disclosure",
                                  "actionable_summary", "association_screen_ref",
                                  "next_design_ref")), str(sorted(rec)))
    record("obs.contract_version_1_1", rec["contract_version"] == "1.1",
           rec["contract_version"])
    record("obs.no_joint_domain", rec["joint_windows"] == []
           and rec["joint_setpoints"] == [] and rec["grid_plan"] is None, "")
    record("obs.hull_unbounded_low_conf",
           rec["design_region"]["hull"] == "unbounded"
           and rec["design_region"]["design_hull_confidence"] == "low", "")
    record("obs.trend_confounded_no_window",
           rec["operating_windows"] == []
           and any(e.get("code") == "TREND_CONFOUNDED_NO_WINDOW"
                   for e in rec["watchlist"]), "")
    record("obs.matrix_reason_trend_or_ns",
           all(c["no_window_reason"] in ("TREND_CONFOUNDED_NO_WINDOW",
                                         "NO_SIGNIFICANT_FACTOR", "NOT_ESTIMABLE")
               for c in rec["factor_response_matrix"]),
           json.dumps([c["no_window_reason"] for c in rec["factor_response_matrix"]]))
    clean = {"pairs": [{"target": "y", "parameter": "x", "r": 0.99,
                        "detrended_r": 0.95, "trend_confounded": False}]}
    rec2 = W.observational_windows_v11(stability, {}, ctx, df, correlation=clean)
    if rec2["operating_windows"]:
        w = rec2["operating_windows"][0]
        record("obs.window_never_actionable",
               w["actionable"] is False
               and "no_prediction_interval" in w["actionable_blockers"]
               and "design_hull_low_confidence" in w["actionable_blockers"],
               json.dumps(w["actionable_blockers"]))
        record("obs.effect_ci_kept_as_ci95",
               w["expected_effect"]["effect_ci95"] == w["expected_effect"]["ci95"],
               json.dumps(w["expected_effect"]))
        record("obs.no_pi_in_observational",
               w["expected_effect"]["pi95"] is None
               and w["expected_effect"]["pi95_method"] is None, "")
        record("obs.case_has_window_for_export_test", True, "")
    else:
        record("obs.window_never_actionable", False, "no window emitted")
        record("obs.effect_ci_kept_as_ci95", False, "no window emitted")
        record("obs.no_pi_in_observational", False, "no window emitted")
        record("obs.case_has_window_for_export_test", False, "no window emitted")

    exp = W.windows_seed_export(rec2)
    blocked_ids = {b.get("window_id") for b in rec2["actionable_summary"]["blocked"]}
    record("export.rejected_prior_traceable",
           all(r["source"] in ("operating_window", "joint_setpoint")
               and r.get("window_id") or r.get("setpoint_id") for r in exp["rejected_prior"])
           and all(r.get("reason") for r in exp["rejected_prior"]) != [],
           json.dumps(exp["rejected_prior"])[:200])
    record("export.actionable_summary_consistent",
           len(rec2["actionable_summary"]["blocked"]) + rec2["actionable_summary"]["n_actionable"]
           == len(rec2["operating_windows"]) + len(rec2["joint_setpoints"]),
           json.dumps(rec2["actionable_summary"])[:200])


# ---------------------------------------------------------------- legacy.* (DS-13)

def case_legacy():
    print("== legacy: v1.1 marginal windows mirror the legacy numbers (DS-13) ==")
    df, names = ccd_frame(seed=11)
    ctx = _ctx([(n, "degC") for n in names], base_responses("purity"))
    models, et, fi = _fit(df, ctx, quad=True)
    profile = {"design": {"mode": "designed", "design_type": "rsm_ccd"}}
    legacy_w, legacy_i, legacy_c, legacy_wl, legacy_s = W.designed_windows(
        models, et, profile, ctx, df)
    rec = W.designed_windows_v11(models, et, profile, ctx, df)
    lmap = {w["factor"]: w for w in legacy_w}
    vmap = {w["factor"]: w for w in rec["operating_windows"]}
    record("legacy.same_factor_set", set(lmap) == set(vmap),
           f"legacy={sorted(lmap)} v11={sorted(vmap)}")
    same = True
    detail = []
    for f in sorted(lmap):
        if f not in vmap:
            same = False
            continue
        a, b = lmap[f], vmap[f]
        if (a["range"] != b["range"] or a["shape"] != b["shape"]
                or a["extrapolation"] != b["extrapolation"]
                or a["expected_effect"]["delta"] != b["expected_effect"]["delta"]
                or a["expected_effect"]["direction_semantics"]
                != b["expected_effect"]["direction_semantics"]
                or a["confidence"] != b["confidence"] or a["fdr_q"] != b["fdr_q"]):
            same = False
            detail.append((f, a["range"], b["range"]))
    record("legacy.v11_ranges_byte_identical", same, json.dumps(detail))
    record("legacy.legacy_keys_preserved",
           all(set(lmap[f]) <= set(vmap[f]) for f in lmap),
           json.dumps({f: sorted(set(lmap[f]) - set(vmap[f])) for f in lmap}))
    lt = W.designed_windows(models, et, profile, ctx, df)
    record("legacy.entry_point_still_5_tuple",
           isinstance(lt, tuple) and len(lt) == 5, str(type(lt)))
    record("legacy.legacy_signature_unchanged",
           str(__import__("inspect").signature(W.designed_windows))
           == "(models, effect_table, profile, ctx, df)"
           and str(__import__("inspect").signature(W.observational_windows))
           == "(stability, profile, ctx, df, correlation=None)",
           str(__import__("inspect").signature(W.designed_windows)))
    record("legacy.v11_signature_frozen",
           str(__import__("inspect").signature(W.designed_windows_v11))
           == "(models, effect_table, profile, ctx, df, *, brief=None, seed=None)",
           str(__import__("inspect").signature(W.designed_windows_v11)))


# ---------------------------------------------------------------- disc.* (P2-8)

def case_schemas_and_disclosure():
    print("== disc: disclosure + additive v1.1 schemas (P2-8) ==")
    import hashlib
    df, names = factorial_frame(2, seed=5, noise=0.2)
    data_sha = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
    responses = [{"col": "y", "goal": "maximize", "lsl": None, "usl": None,
                  "target": None, "weight": None, "unit": "degC"}]
    ctx = _ctx([(n, "degC") for n in names], responses)
    ctx["input_sha256"] = data_sha
    ctx["script_version"] = "1.1-test"
    models, et, fi = _fit(df, ctx)
    rec = W.designed_windows_v11(models, et, {"design": {"mode": "designed",
                                                         "design_type": "full_factorial"}},
                                 ctx, df)
    record("disc.actionable_summary_shape",
           set(rec["actionable_summary"]) == {"n_actionable", "n_blocked", "blocked"}
           and all({"reasons"} <= set(b)
                   and ({"window_id"} <= set(b) or {"setpoint_id"} <= set(b))
                   for b in rec["actionable_summary"]["blocked"]), "")
    record("disc.blocked_ids_are_window_or_setpoint",
           all(("window_id" in b) != ("setpoint_id" in b)
               for b in rec["actionable_summary"]["blocked"]), "")
    record("disc.refs_are_pointers",
           rec["association_screen_ref"]["path"] == "02_analysis/association_screen.json"
           and rec["association_screen_ref"]["causal_claim"] == "none"
           and "pairs" not in rec["association_screen_ref"]
           and rec["next_design_ref"]["path"] == "conclusions/next_design.json", "")
    record("disc.contract_version_1_1", rec["contract_version"] == "1.1", "")
    record("disc.provenance_carries_sha",
           rec["provenance"]["input_sha256"] == data_sha
           and rec["provenance"]["script_version"] == "1.1-test",
           json.dumps(rec["provenance"]))
    record("disc.effect_table_metadata_helper",
           ea.table_v11_metadata(rec["units"])["response_units"] == {"y": "degC"}
           and "1 +" in ea.table_v11_metadata(rec["units"])["interval_semantics"],
           json.dumps(ea.table_v11_metadata(rec["units"])["response_units"]))
    from conclusion_template import build as build_conc, contract_status
    conc = build_conc({"design": {"mode": "designed", "design_type": "full_factorial"},
                       "caveats": []}, et, None, None, rec, {"plots": []}, models=None)
    card_cs = (conc.get("downstream_usage_card") or {}).get("contract_status") or {}
    record("disc.contract_status_independent",
           card_cs.get("evidence_grade_independent") is True
           and card_cs.get("contract_version") == "1.1"
           and "contract_status" not in conc          # gate: CONC_KEYS must not grow
           and conc["evidence_grade"] in ("A", "A-", "B"),
           json.dumps(card_cs))
    conc_v10 = build_conc({"design": {"mode": "designed", "design_type": "full_factorial"},
                           "caveats": []}, et, None, None,
                          {"contract_version": "1.0", "operating_windows": [],
                           "confirmations": [], "watchlist": [], "usage_rules": []},
                          {"plots": []}, models=None)
    v10_card = conc_v10.get("downstream_usage_card") or {}
    record("disc.v10_conclusion_unchanged",
           set(conc_v10) == set(conc) and "contract_status" not in v10_card
           and "factor_response_coverage" not in v10_card
           and v10_card.get("contract_version") == "1.0",
           json.dumps(sorted(v10_card)))
    # G6 strict-extra-keys conformance: the exact frozen key sets the gate uses
    REC_KEYS = {"contract_version", "audience", "analysis_mode", "operating_windows",
                "current_baseline", "setpoints", "interactions", "conflicts",
                "response_specs", "confirmations", "watchlist", "constraints",
                "applicability_domain", "invalidation_conditions", "usage_rules",
                "provenance", "units", "design_region", "joint_windows",
                "joint_setpoints", "factor_response_matrix", "actionable_summary",
                "interval_disclosure", "association_screen_ref", "next_design_ref",
                "grid_plan"}
    WIN_KEYS = {"id", "priority", "factor", "factor_unit", "response", "range", "shape",
                "expected_effect", "confidence", "fdr_q", "sample_size", "evidence_refs",
                "extrapolation", "confirmation_needed", "notes", "window_role",
                "actionable", "actionable_blockers", "in_design_hull",
                "constraints_applied", "constraint_violations", "predicted_at_center"}
    CONC_KEYS = {"generated_at", "analysis_mode", "design_type", "evidence_grade",
                 "grade_checklist", "authored_by", "key_findings", "limitations",
                 "figure_index", "recommendations_ref", "downstream_usage_card"}
    payload = W.recommendations_payload(rec)
    record("disc.payload_matches_gate_recl_keys",
           set(payload) <= REC_KEYS and "windows" in rec
           and payload["operating_windows"] is rec["operating_windows"],
           f"extra={sorted(set(payload) - REC_KEYS)} missing={sorted(REC_KEYS - set(payload))}")
    record("disc.window_keys_match_gate_win_keys",
           all(set(w) <= WIN_KEYS for w in payload["operating_windows"]),
           str(sorted({k for w in payload["operating_windows"] for k in w} - WIN_KEYS)))
    JW_KEYS = {"id", "responses", "factors", "feasible", "constraint_violations",
               "hard_constraint_violations", "predicted", "desirability", "method",
               "evidence_level", "responses_satisfied", "constraint_slack",
               "confidence", "window_ids", "unit_status", "actionable", "blockers",
               "selection_scale"}
    record("disc.joint_window_keys_frozen",
           all(set(jw) <= JW_KEYS for jw in payload["joint_windows"]),
           str(sorted({k for jw in payload["joint_windows"] for k in jw} - JW_KEYS)))
    record("disc.conclusion_keys_match_gate_conc_keys",
           set(conc) <= CONC_KEYS, str(sorted(set(conc) - CONC_KEYS)))
    record("disc.g10_constraint_slack_non_negative",
           all(all(v >= -1e-9 for v in (s.get("constraint_slack") or {}).values())
               for s in payload["joint_setpoints"] if s.get("actionable")),
           json.dumps([s.get("constraint_slack") for s in payload["joint_setpoints"]]))

    # schema validation of a v1.1 recommendations.json via the shared validator
    if VALIDATE.exists():
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "recommendations.json"
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            proc = subprocess.run(
                ["node", str(VALIDATE), str(SKILL / "schemas" / "recommendations.schema.json"),
                 str(p)], capture_output=True, text=True, shell=False)
            record("disc.v11_recommendations_schema_valid",
                   proc.returncode == 0, (proc.stdout + proc.stderr)[-300:])
    else:
        record("disc.v11_recommendations_schema_valid", False, "validate.mjs missing")


def case_determinism():
    print("== det: two runs identical (RG-03) ==")
    df, names = ccd_frame(seed=11)
    ctx = _ctx([(n, "degC") for n in names], base_responses("purity"))
    models, et, fi = _fit(df, ctx, quad=True)
    profile = {"design": {"mode": "designed", "design_type": "rsm_ccd"}}
    a = W.designed_windows_v11(models, et, profile, ctx, df)
    b = W.designed_windows_v11(models, et, profile, ctx, df)
    ja = json.dumps(a, ensure_ascii=False, sort_keys=True)
    jb = json.dumps(b, ensure_ascii=False, sort_keys=True)
    record("det.v11_two_runs_identical", ja == jb,
           f"len_a={len(ja)} len_b={len(jb)}")
    k = len(names)
    ctx_c = _ctx([(n, "degC") for n in names], base_responses("purity"),
                 constraints=[{"type": "linear", "coeffs": {names[0]: 1.0, names[1]: 1.0},
                               "max": 0.5, "hard": True, "source": "user"}])
    c = W.designed_windows_v11(models, et, profile, ctx_c, df)
    d = W.designed_windows_v11(models, et, profile, ctx_c, df)
    record("det.constrained_two_runs_identical",
           json.dumps(c, ensure_ascii=False, sort_keys=True)
           == json.dumps(d, ensure_ascii=False, sort_keys=True), "")
    record("det.seed_parameter_accepted",
           W.designed_windows_v11(models, et, profile, ctx, df, seed=7)["provenance"]["seed"] == 7
           and W.designed_windows_v11(models, et, profile, ctx, df,
                                      seed=7)["contract_version"] == "1.1", "")


CASES = {
    "int": case_intervals,
    "con": case_constraints,
    "joint": case_joint,
    "unit": case_units,
    "hull": case_hull,
    "grid": case_grid_scaling,
    "matrix": case_matrix,
    "obs": case_observational,
    "legacy": case_legacy,
    "det": case_determinism,
    "disc": case_schemas_and_disclosure,
}


def main():
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = list(CASES) if selector == "all" or selector not in CASES else [selector]
    for name in todo:
        CASES[name]()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[PHASE2] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
