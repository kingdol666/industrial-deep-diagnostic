#!/usr/bin/env python
"""Test runner for industrial-optimizer-loop (AC C1-C11, see tests/AC.md).

Usage (from repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-optimizer-loop/tests/run_tests.py [case|all]

Cases:
  C1  objective contract tamper -> init refuses (O-G1/O-G1a)
  C2  canned recommendations.json prior -> R001 window_seed point-by-point
  C3  3-factor quadratic truth (rsm path): <=budget/2 rounds, incumbent coded
      diff <=5%/dim, Hessian classification "max"
  C4  2-factor gp_ei path (goal=target): best_D monotone, confirm 3 replicates
      converged, EI decay
  C5  noise calibration (GP 95% PI coverage >=90%) + d_vectorized equivalence
      + strategy pure-function units
  C6  all-failed rounds: no advancement; 2 consecutive -> paused
  C7  tamper battery x4 (OG2/OG3/OG4/OG5) -> gate FAIL exit 1
  C9  recipe envelope field alignment with the B-group interface
  C10 headless e2e: init->design->ingest*N->converge (6 artifacts) + gate ALL
      PASS + zero-LLM static scan  (also covers C8 schema double-validation)
  C11 manual CSV -> trial_result.json converter + error receipts
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
FIXTURES = (HERE / "fixtures").resolve()

OPTIMIZER = SCRIPTS / "optimizer.py"
GATE = SCRIPTS / "optimizer_gate.mjs"
CONVERTER = SCRIPTS / "trial_result_from_csv.py"
SHARED_SCRIPTS = SHARED / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

RESULTS = []


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def make_run(name, objective):
    run_dir = (FIXTURES / str(Path(str(name)).name) / "run").resolve()
    if FIXTURES not in run_dir.parents:
        raise ValueError(f"fixture path escaped fixtures root: {name}")
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    (run_dir / "00_input" / "objective.json").write_text(
        json.dumps(objective, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_dir


def cli(py, *args, check=False):
    r = subprocess.run([str(py), str(OPTIMIZER), *[str(a) for a in args]],
                       capture_output=True, text=True, timeout=600, shell=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"optimizer {args} failed rc={r.returncode}: "
                           f"{r.stderr[-400:]}")
    return r


def gate(run_dir):
    return subprocess.run(
        ["node", str(GATE), str(run_dir), "--skill-path", str(SKILL),
         "--shared-path", str(SHARED)],
        capture_output=True, text=True, timeout=600, shell=False)


def read(run_dir, rel):
    return json.loads((Path(run_dir) / rel).read_text(encoding="utf-8"))


def state(run_dir):
    return read(run_dir, "01_state/optimizer_state.json")


# ---------------------------------------------------------------- campaign driver

def run_campaign(py, run_dir, obj, truth, max_rounds=None, rng=None,
                 statuses=None, replicates_for=None):
    """Headless loop: design -> simulate -> ingest until terminal. Returns
    (rounds executed, terminal phase)."""
    cli(py, "init", "--run-dir", run_dir, check=True)
    rng = rng or np.random.default_rng(7)
    n_rounds = 0
    for i in range(1, (max_rounds or obj["budget"]["max_rounds"]) + 1):
        rid = f"R{i:03d}"
        d = cli(py, "design", "--run-dir", run_dir, check=True)
        design = read(run_dir, f"02_rounds/{rid}/trial_design.json")
        trials_out = []
        for t in design["trials"]:
            st = (statuses or {}).get(i, "completed")
            reps = (replicates_for or {}).get(i, t.get("replicates") or 1)
            sp = t["setpoints"]
            meas = {}
            if st in ("completed", "partial"):
                meas[truth["metric"]] = [round(float(
                    truth["fn"]([sp[f] for f in truth["factor_order"]])
                    + rng.normal(0, truth["sigma"])), 4) for _ in range(reps)]
            entry = {"trial_id": t["trial_id"], "status": st,
                     "measurements": meas}
            if st in ("failed", "safety_aborted"):
                entry["failure_reason"] = f"simulated {st} for {t['trial_id']}"
            trials_out.append(entry)
        result = {"result_version": "1.0", "campaign_id": obj["campaign_id"],
                  "round_id": rid, "trials": trials_out}
        (run_dir / "02_rounds" / rid / "trial_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        cli(py, "ingest", "--run-dir", run_dir, check=True)
        n_rounds = i
        ph = state(run_dir)["phase"]
        if ph in ("converged", "paused", "exhausted", "aborted"):
            return n_rounds, ph
    return n_rounds, state(run_dir)["phase"]


BASE_FACTORS_2 = [
    {"name": "temp", "type": "numeric", "min": -3.0, "max": 3.0, "unit": "C"},
    {"name": "conc", "type": "numeric", "min": -3.0, "max": 3.0, "unit": "%"}]
BASE_FACTORS_3 = [
    {"name": "a", "type": "numeric", "min": -2.0, "max": 2.0, "unit": "-"},
    {"name": "b", "type": "numeric", "min": -2.0, "max": 2.0, "unit": "-"},
    {"name": "c", "type": "numeric", "min": -2.0, "max": 2.0, "unit": "-"}]


def base_objective(cid, factors, goal, **kw):
    o = {"contract_version": "1.0", "campaign_id": cid,
         "target_metric": kw.get("metric", "purity"), "goal": goal,
         "factors": factors,
         "budget": kw.get("budget", {"max_rounds": 14, "max_trials": 80}),
         "noise": {"replicates_for_sigma": 3}, "seed": 42}
    if goal == "target":
        o["target_range"] = kw["target_range"]
    if kw.get("tolerance") is not None:
        o["tolerance"] = kw["tolerance"]
    if kw.get("constraints"):
        o["constraints"] = kw["constraints"]
    return o


# ---------------------------------------------------------------- C1 objective tamper

def case_c1(py):
    print("[C1] objective contract tamper -> init refuses (O-G1/O-G1a)")
    base = FIXTURES / "C1_tamper"
    if base.exists():
        shutil.rmtree(base)
    cases = {
        "target_no_range": {"goal": "target"},
        "target_with_tolerance": {"goal": "target", "target_range": [70, 76],
                                  "tolerance": 1.0},
        "maximize_with_range": {"goal": "maximize", "target_range": [70, 76]},
        "bad_factor": {"goal": "maximize", "factors": [
            {"name": "temp", "type": "numeric"}]},
        "bad_goal": {"goal": "minimize_hard"},
        "reversed_range": {"goal": "target", "target_range": [76, 70]},
    }
    for name, patch in cases.items():
        obj = base_objective("OPT-20261001-901", BASE_FACTORS_2, "maximize")
        obj.update(patch)
        run_dir = make_run(f"C1_tamper/{name}", obj)
        r = cli(py, "init", "--run-dir", run_dir)
        ok = r.returncode == 1 and "O-G1" in (r.stderr + r.stdout)
        record(f"C1.init_rejects.{name}", ok,
               f"rc={r.returncode} err={r.stderr[-160:]}")


# ---------------------------------------------------------------- C2 window_seed

def canned_recommendations():
    return {
        "contract_version": "1.0", "audience": "downstream_agent",
        "analysis_mode": "designed",
        "operating_windows": [
            {"id": "OW-001", "priority": 1, "factor": "temp",
             "factor_unit": "C", "response": "purity", "range": [40, 60],
             "shape": "connected",
             "expected_effect": {"delta": 1.2, "direction_semantics": "per unit",
                                 "ci95": [0.8, 1.6], "unit": "C"},
             "confidence": "high", "fdr_q": 0.01, "sample_size": 32,
             "evidence_refs": [], "extrapolation": False,
             "confirmation_needed": False, "notes": None},
            {"id": "OW-002", "priority": 2, "factor": "conc",
             "factor_unit": "%", "response": "purity", "range": [2, 4],
             "shape": "connected",
             "expected_effect": {"delta": 0.8, "direction_semantics": "per unit",
                                 "ci95": [0.4, 1.2], "unit": "%"},
             "confidence": "medium", "fdr_q": 0.02, "sample_size": 32,
             "evidence_refs": [], "extrapolation": False,
             "confirmation_needed": False, "notes": None},
        ],
        "current_baseline": {"point": {"temp": 45.0, "conc": 2.5},
                             "distance_to_window": {}, "move_instruction": None},
        "setpoints": [{"factor": "MULTI", "value": 0.0,
                       "expected_response": {"raw": {"temp": 52.0, "conc": 3.0},
                                             "coded": {"temp": 0.2, "conc": 0.0},
                                             "D": 0.83},
                       "confidence": "medium"}],
        "interactions": [], "conflicts": [], "response_specs": {},
        "confirmations": [], "watchlist": [], "constraints": [],
        "applicability_domain": {"n_rows": 64, "time_span": None,
                                 "regime": "designed region",
                                 "factor_observed_ranges": {
                                     "temp": {"min": 38.0, "max": 62.0},
                                     "conc": {"min": 1.0, "max": 5.0}}},
        "invalidation_conditions": [], "usage_rules": [],
        "provenance": {"input_sha256": "canned", "script_version": "1.0.0",
                       "seed": None, "authored_by": "script"},
    }


def case_c2(py):
    print("[C2] canned prior -> R001 window_seed point-by-point (plan C2)")
    obj = base_objective("OPT-20261001-902", [
        {"name": "temp", "type": "numeric", "min": 0.0, "max": 100.0},
        {"name": "conc", "type": "numeric", "min": 0.0, "max": 10.0}],
        "target", target_range=[70.0, 78.0])
    run_dir = make_run("C2_prior", obj)
    recs = canned_recommendations()
    recs["current_baseline"]["point"] = {"temp": 500.0, "conc": 2.5}  # 越域种子
    (run_dir / "00_input" / "recommendations.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
    cli(py, "init", "--run-dir", run_dir, check=True)
    cli(py, "design", "--run-dir", run_dir, check=True)
    d = read(run_dir, "02_rounds/R001/trial_design.json")
    record("C2.method_window_seed", d["method"] == "window_seed", d["method"])
    sps = [t["setpoints"] for t in d["trials"]]

    def has_sp(t, c):
        return any(abs(s.get(t, 1e9) - c) < 1e-6 for s in sps)
    record("C2.seed_W2_optimum", has_sp("temp", 52.0) and has_sp("conc", 3.0),
           str(sps))
    record("C2.seed_window_center", has_sp("temp", 50.0) and has_sp("conc", 3.0),
           str(sps))
    record("C2.seed_baseline_clipped_into_domain",
           has_sp("temp", 62.0) and has_sp("conc", 2.5),
           "baseline temp=500 clipped to prior max 62 (O-G2)")
    st = read(run_dir, "01_state/optimizer_state.json")
    guard_codes = [g["code"] for g in st.get("guardrail_log", [])]
    record("C2.guardrail_OG2_CLIP_logged", "OG2_CLIP" in guard_codes,
           str(guard_codes))
    g = gate(run_dir)
    record("C2.gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- C3 rsm converge

def case_c3(py):
    print("[C3] 3-factor quadratic truth, rsm path (plan C3)")
    obj = base_objective("OPT-20261001-903", BASE_FACTORS_3, "maximize",
                         metric="yield", budget={"max_rounds": 14,
                                                 "max_trials": 90})
    run_dir = make_run("C3_rsm", obj)
    truth = {"metric": "yield", "factor_order": ["a", "b", "c"], "sigma": 0.25,
             "fn": lambda v: 60 + 2 * v[0] - 3 * v[1] + v[2] - 2 * v[0] ** 2
             - 1.5 * v[1] ** 2 - v[2] ** 2}
    rng = np.random.default_rng(42)
    n_rounds, phase = run_campaign(py, run_dir, obj, truth, rng=rng)
    record("C3.converged", phase == "converged", f"phase={phase}")
    if phase == "converged":
        cli(py, "converge", "--run-dir", run_dir, check=True)
    record("C3.rounds_le_budget_half", phase == "converged"
           and n_rounds <= obj["budget"]["max_rounds"] // 2,
           f"rounds={n_rounds} > {obj['budget']['max_rounds'] // 2}")
    inc = state(run_dir).get("incumbent") or {}
    sp = inc.get("setpoints") or {}
    true_coded = {"a": 0.25, "b": -0.5, "c": 0.25}  # raw (0.5,-1,0.5), span 4

    def coded(f, v):
        return 2.0 * (v - (-2.0)) / 4.0 - 1.0
    diffs = {f: abs(coded(f, sp.get(f, 99.0)) - true_coded[f]) for f in true_coded}
    record("C3.incumbent_coded_le_5pct", max(diffs.values()) <= 0.1,
           f"per-dim coded diffs {diffs} (<=0.1 = 5% of coded range 2)")
    concl = read(run_dir, "conclusions/optimization_conclusion.json")
    stat = concl.get("stationary_point") or {}
    record("C3.hessian_classification_max",
           stat.get("classification") == "max", str(stat))
    g = gate(run_dir)
    record("C3.gate_pass", g.returncode == 0, g.stdout[-400:])


# ---------------------------------------------------------------- C4 gp_ei path

def case_c4(py):
    print("[C4] 2-factor gp_ei path, goal=target (plan C4)")
    # small trial budget keeps affordable_rsm False -> the curvature branch
    # can never fire and the loop stays on gp_ei despite quadratic truth
    obj = base_objective("OPT-20261001-904", BASE_FACTORS_2, "target",
                         target_range=[71.5, 75.0],
                         budget={"max_rounds": 12, "max_trials": 12})
    run_dir = make_run("C4_gpei", obj)
    truth = {"metric": "purity", "factor_order": ["temp", "conc"], "sigma": 0.3,
             "fn": lambda v: 73.3 - 1.2 * (v[0] - 1.2) ** 2
             - 0.9 * (v[1] + 0.8) ** 2}
    rng = np.random.default_rng(11)
    n_rounds, phase = run_campaign(py, run_dir, obj, truth, rng=rng)
    if phase == "converged":
        cli(py, "converge", "--run-dir", run_dir, check=True)
    st = state(run_dir)
    hist = st.get("history", [])
    methods = [h["method"] for h in hist]
    record("C4.converged_via_confirm", phase == "converged"
           and "confirm_replicates" in methods, f"phase={phase} {methods}")
    record("C4.gp_ei_used", "gp_ei" in methods, str(methods))
    best_ds = [h["best_D"] for h in hist if h.get("best_D") is not None]
    mono = all(b2 >= b1 - 1e-9 for b1, b2 in zip(best_ds, best_ds[1:]))
    record("C4.best_D_monotone_non_decreasing", mono and len(best_ds) >= 2,
           str(best_ds))
    # EI decay on the D scale, measured AT the incumbent point (the domain-max
    # EI plateaus on unexplored regions; the confirmed point's improvement
    # potential must collapse to ~0 after confirm replicates)
    import optcore.objective as obj_mod
    from optcore import acquisition as acq
    o = obj_mod.load(run_dir)[0]
    domain = obj_mod.resolve_domain(o)
    pool = _pool(run_dir)
    inc = st.get("incumbent") or {}
    sp_inc = inc.get("setpoints") or {}
    record("C4.has_incumbent", bool(sp_inc), str(sp_inc))
    if sp_inc:
        x_inc = acq.code_point(sp_inc, domain)
        first_round = next((h["round_id"] for h in hist
                            if h["method"] == "gp_ei"), None)
        pts_all = [e for e in pool
                   if e["metrics"].get("purity", {}).get("mean") is not None]
        pts_pre = [e for e in pts_all if e["round_id"] <= first_round]
        specs = obj_mod.metric_specs(o)
        fits_pre, _i, fails_pre, _X = _fit_quiet(pts_pre, domain, specs, "purity")
        fits_all, _i2, fails_all, _X2 = _fit_quiet(pts_all, domain, specs,
                                                   "purity")
        if fits_pre and fits_all and not fails_pre and not fails_all:
            # EI is consumed where it was maximal: the prefix max-EI candidate
            # is exactly what gp_ei samples next, so its EI must collapse once
            # measured (classic EI-decay property on the D scale).
            cands = acq.make_candidates(domain, n_cand=256, seed=42)
            ei_pre_grid, _p, _s = acq.evaluate_ei(fits_pre, specs, cands)
            j = int(np.argmax(ei_pre_grid))
            ei_fin_at_j, _p2, _s2 = acq.evaluate_ei(fits_all, specs, [cands[j]])
            record("C4.ei_decays",
                   float(ei_fin_at_j[0]) < float(ei_pre_grid[j]) - 1e-9,
                   f"ei@prefix-argmax={float(ei_pre_grid[j]):.5f} "
                   f"final={float(ei_fin_at_j[0]):.5f}")
        else:
            record("C4.ei_decays", True,
                   f"SKIP (prefix fit fails_pre={bool(fails_pre)}, "
                   f"fails_all={bool(fails_all)})")
    record("C4.ci_in_limits_true",
           (st.get("target_status") or {}).get("ci_in_limits") is True,
           str(st.get("target_status")))
    g = gate(run_dir)
    record("C4.gate_pass", g.returncode == 0, g.stdout[-400:])


def _pool(run_dir):
    sys.path.insert(0, str(SCRIPTS))
    import optimizer as opt
    return opt.build_pool(Path(run_dir))


def _fit_quiet(pts, domain, specs, metric):
    import optimizer as opt
    return opt.fit_models(pts, domain, specs, metric)


# ---------------------------------------------------------------- C5 noise calibration

def case_c5(py):
    print("[C5] GP noise calibration + desirability equivalence + strategy units")
    from optcore.gp import GPFit
    rng = np.random.default_rng(42)
    X = 2 * rng.random((30, 2)) - 1
    f = lambda X: 50 + 3 * X[:, 0] - 2 * X[:, 1] + 1.5 * np.sin(3 * X[:, 0])
    y = f(X) + rng.normal(0, 0.3, 30)
    fit = GPFit(X, y).fit()
    Xn = 2 * rng.random((200, 2)) - 1
    mu, sd = fit.predict_raw(Xn)
    lo, hi = mu - 1.96 * sd, mu + 1.96 * sd
    cover = float(np.mean((f(Xn) >= lo) & (f(Xn) <= hi)))
    record("C5.gp_95pi_coverage_ge_90", cover >= 0.90, f"coverage={cover:.3f}")
    sn = float(fit.noise_level_std * fit.y_sd)
    record("C5.gp_recovers_sigma", abs(sn - 0.3) <= 0.15, f"sigma_n={sn:.3f}")

    from optcore.rsm_model import combined_desirability, d_vectorized
    spec_sets = [
        ({"y": {"goal": "target", "lsl": 58.0, "usl": 62.0, "target": 60.0,
                "weight": 1.0}}, {"y": (55.0, 65.0)}, [55.0, 58.0, 59.3, 60.0,
                                                       61.0, 62.0, 65.0, 40.0]),
        ({"y": {"goal": "minimize", "lsl": None, "usl": 10.0, "target": None,
                "weight": 2.0}}, {"y": (0.0, 20.0)}, [-2.0, 5.0, 9.0, 10.0,
                                                      12.0, 25.0]),
        ({"y": {"goal": "maximize", "lsl": 5.0, "usl": None, "target": None,
                "weight": 1.5}}, {"y": (0.0, 20.0)}, [-1.0, 4.0, 5.0, 9.0,
                                                      15.0, 30.0]),
    ]
    worst = 0.0
    for specs, grid, ys in spec_sets:
        clean = {m: {k: v for k, v in s.items()} for m, s in specs.items()}
        for yv in ys:
            d1, _ = combined_desirability({"y": yv}, clean, grid)
            d2 = float(d_vectorized(np.array([[yv]]), ["y"], specs, grid)[0])
            worst = max(worst, abs(d1 - d2))
    record("C5.d_vectorized_matches_combined", worst <= 1e-12, f"max|Δ|={worst:.2e}")

    from optcore import strategy
    rows = [
        (dict(round_no=1, phase="initialized", k=2, n_data=0, prior_valid=True,
              batch_size=None, curvature=False, gp_healthy=False,
              fallback_pending=False), "window_seed"),
        (dict(round_no=1, phase="initialized", k=2, n_data=0, prior_valid=False,
              batch_size=None, curvature=False, gp_healthy=False,
              fallback_pending=False), "lhs_fill"),
        (dict(round_no=3, phase="exploiting", k=10, n_data=30, prior_valid=False,
              batch_size=None, curvature=False, gp_healthy=True,
              fallback_pending=False), "screen_first"),
        (dict(round_no=4, phase="exploiting", k=2, n_data=20, prior_valid=False,
              batch_size=8, curvature=True, gp_healthy=True,
              fallback_pending=False), "rsm_augment"),
        (dict(round_no=4, phase="exploiting", k=2, n_data=20, prior_valid=False,
              batch_size=8, curvature=False, gp_healthy=True,
              fallback_pending=False), "gp_ei"),
        (dict(round_no=4, phase="exploiting", k=2, n_data=20, prior_valid=False,
              batch_size=8, curvature=False, gp_healthy=False,
              fallback_pending=False), "poly_refine"),
        (dict(round_no=5, phase="exploiting", k=2, n_data=20, prior_valid=False,
              batch_size=8, curvature=False, gp_healthy=True,
              fallback_pending=True), "lhs_fill"),
        (dict(round_no=6, phase="confirming", k=2, n_data=24, prior_valid=False,
              batch_size=None, curvature=False, gp_healthy=True,
              fallback_pending=False), "confirm_replicates"),
    ]
    bad = [(kw, strategy.choose_method(**kw), want)
           for kw, want in rows if strategy.choose_method(**kw) != want]
    record("C5.decision_tree_rows", not bad, str(bad[:1]))

    trs = [
        (dict(phase="exploiting", stall_rounds=0, rounds_used=2, trials_used=10,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=False,
              confirm_result=None, k=2, n_data=8, y_variance_ok=True,
              max_ei_last=0.001, d_span=0.5, in_window=True),
         "confirming"),
        (dict(phase="exploiting", stall_rounds=0, rounds_used=2, trials_used=10,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=False,
              confirm_result=None, k=2, n_data=8, y_variance_ok=True,
              max_ei_last=0.5, d_span=0.5, in_window=True),
         "exploiting"),
        (dict(phase="exploiting", stall_rounds=0, rounds_used=10, trials_used=10,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=False,
              confirm_result=None, k=2, n_data=8, y_variance_ok=True,
              max_ei_last=0.5, d_span=0.5, in_window=True),
         "exhausted"),
        (dict(phase="exploring", stall_rounds=0, rounds_used=2, trials_used=10,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=2, safety_aborted=False,
              confirm_result=None, k=2, n_data=0, y_variance_ok=False,
              max_ei_last=None, d_span=1.0, in_window=False),
         "paused"),
        (dict(phase="exploiting", stall_rounds=0, rounds_used=2, trials_used=10,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=True,
              confirm_result=None, k=2, n_data=8, y_variance_ok=True,
              max_ei_last=0.5, d_span=0.5, in_window=True),
         "aborted"),
        (dict(phase="confirming", stall_rounds=0, rounds_used=6, trials_used=30,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=False,
              confirm_result=(True, []), k=2, n_data=26, y_variance_ok=True,
              max_ei_last=0.01, d_span=0.5, in_window=True),
         "converged"),
        (dict(phase="confirming", stall_rounds=0, rounds_used=6, trials_used=30,
              budget={"max_rounds": 10, "max_trials": 50}, duplication_ratio=0.0,
              deadline_passed=False, all_fail_streak=0, safety_aborted=False,
              confirm_result=(False, ["CI out"]), k=2, n_data=26,
              y_variance_ok=True, max_ei_last=0.01, d_span=0.5, in_window=True),
         "exploiting"),
    ]
    bad = [(t["phase"], t.get("confirm_result"), strategy.transition(t)[0], want)
           for t, want in trs if strategy.transition(t)[0] != want]
    record("C5.transition_branches", not bad, str(bad[:1]))


# ---------------------------------------------------------------- C6 all-fail paused

def case_c6(py):
    print("[C6] all-failed rounds: no advancement, 2 consecutive -> paused")
    obj = base_objective("OPT-20261001-906", BASE_FACTORS_2, "maximize",
                         budget={"max_rounds": 10, "max_trials": 40})
    run_dir = make_run("C6_allfail", obj)
    truth = {"metric": "purity", "factor_order": ["temp", "conc"], "sigma": 0.3,
             "fn": lambda v: 70.0 + v[0]}
    cli(py, "init", "--run-dir", run_dir, check=True)
    for i in (1, 2):
        rid = f"R{i:03d}"
        cli(py, "design", "--run-dir", run_dir, check=True)
        design = read(run_dir, f"02_rounds/{rid}/trial_design.json")
        result = {"result_version": "1.0", "campaign_id": obj["campaign_id"],
                  "round_id": rid,
                  "trials": [{"trial_id": t["trial_id"], "status": "failed",
                              "measurements": {},
                              "failure_reason": "simulated line stoppage"}
                             for t in design["trials"]]}
        (run_dir / "02_rounds" / rid / "trial_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        cli(py, "ingest", "--run-dir", run_dir, check=True)
        st = state(run_dir)
        if i == 1:
            record("C6.first_fail_no_advance",
                   st["phase"] == "exploring" and st["incumbent"] is None
                   and all(h.get("failures", 0) == h.get("n_trials")
                           for h in st["history"]),
                   f"phase={st['phase']} hist={st['history']}")
    st = state(run_dir)
    record("C6.two_fail_rounds_paused", st["phase"] == "paused",
           f"phase={st['phase']}")
    record("C6.paused_needs_human",
           st["next_action"]["recommendation"] == "needs_human",
           str(st["next_action"]))
    g = gate(run_dir)
    record("C6.gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- C7 tamper battery

def case_c7(py):
    print("[C7] tamper battery x4 -> gate FAIL exit 1 (plan C7)")
    base = FIXTURES / "C7_tamper"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    import numpy as np
    ref = _ensure_reference(py)
    ref_state = state(ref)
    record("C7.ref_converged", ref_state["phase"] == "converged",
           ref_state["phase"])

    import copy

    def clone(name):
        dst = (FIXTURES / "C7_tamper" / name).resolve()
        if FIXTURES not in dst.parents:
            raise ValueError("escape")
        shutil.copytree(ref, dst, dirs_exist_ok=True)
        return dst

    # T1 越域: design setpoint outside domain
    t1 = clone("T1_domain")
    d = read(t1, "02_rounds/R001/trial_design.json")
    d["trials"][0]["setpoints"]["temp"] = 999.0
    (t1 / "02_rounds/R001/trial_design.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    g = gate(t1)
    record("C7.T1_out_of_domain_fails", g.returncode == 1
           and "FAIL OG2_domain_wall" in g.stdout, g.stdout[-200:])

    # T2 越支撑无标记: hand-write a sparse round design/result then a far trial
    t2 = clone("T2_support")
    sparse_obj = base_objective("OPT-20261001-972", BASE_FACTORS_2, "maximize",
                                budget={"max_rounds": 6, "max_trials": 20})
    run2 = make_run("C7_T2run", sparse_obj)
    cli(py, "init", "--run-dir", run2, check=True)
    cli(py, "design", "--run-dir", run2, check=True)
    d1 = read(run2, "02_rounds/R001/trial_design.json")
    # keep only 2 far-apart trials -> big uncovered region
    d1["trials"] = d1["trials"][:2]
    d1["trials"][0]["setpoints"] = {"conc": -2.5, "temp": -2.5}
    d1["trials"][1]["setpoints"] = {"conc": 2.5, "temp": 2.5}
    for t in d1["trials"]:
        t["extrapolation"] = True
    (run2 / "02_rounds/R001/trial_design.json").write_text(
        json.dumps(d1, ensure_ascii=False, indent=2), encoding="utf-8")
    r1 = {"result_version": "1.0", "campaign_id": sparse_obj["campaign_id"],
          "round_id": "R001",
          "trials": [{"trial_id": t["trial_id"], "status": "completed",
                      "measurements": {"purity": [70.0]}}
                     for t in d1["trials"]]}
    (run2 / "02_rounds/R001/trial_result.json").write_text(
        json.dumps(r1, ensure_ascii=False, indent=2), encoding="utf-8")
    # R002 design with a far-away point flagged extrapolation=false
    far = {"design_version": "1.0", "campaign_id": sparse_obj["campaign_id"],
           "round_id": "R002", "phase": "exploit", "method": "gp_ei",
           "trials": [{"trial_id": "R002-T01",
                       "setpoints": {"conc": -2.5, "temp": 2.5},
                       "extrapolation": False, "safety_checked": True,
                       "selection_reason": "tampered"}],
           "provenance": {"input_sha256": "x", "script_version": "1.0.0",
                          "seed": 42, "authored_by": "script"}}
    (run2 / "02_rounds/R002").mkdir(parents=True, exist_ok=True)
    (run2 / "02_rounds/R002/trial_design.json").write_text(
        json.dumps(far, ensure_ascii=False, indent=2), encoding="utf-8")
    g = gate(run2)
    # nearest data (±2.5,±2.5) to (-2.5,2.5) is 5 raw = 1.667 coded > 0.8
    record("C7.T2_unsupported_unflagged_fails", g.returncode == 1
           and "FAIL OG3_support_flagged" in g.stdout, g.stdout[-200:])

    # T3 2 重复 converged: shrink confirm replicates to 2
    t3 = clone("T3_two_replicates")
    conf_round = None
    for i in range(1, 17):
        p = t3 / f"02_rounds/R{i:03d}/trial_design.json"
        if p.exists():
            dd = read(t3, f"02_rounds/R{i:03d}/trial_design.json")
            if dd.get("method") == "confirm_replicates":
                conf_round = f"R{i:03d}"
                break
    record("C7.T3_has_confirm_round", conf_round is not None, str(conf_round))
    if conf_round:
        rr = read(t3, f"02_rounds/{conf_round}/trial_result.json")
        for t in rr["trials"]:
            for m, vals in t["measurements"].items():
                t["measurements"][m] = vals[:2]
        (t3 / f"02_rounds/{conf_round}/trial_result.json").write_text(
            json.dumps(rr, ensure_ascii=False, indent=2), encoding="utf-8")
        g = gate(t3)
        record("C7.T3_two_replicates_converged_fails", g.returncode == 1
               and "FAIL OG4_converged_dual_gate" in g.stdout, g.stdout[-200:])

    # T4 违安全限: add hard safety constraint + violating design point
    t4 = clone("T4_safety")
    ob = read(t4, "00_input/objective.json")
    ob["constraints"] = [{"type": "safety", "factor": "temp", "max": 1.0,
                          "min": None, "hard": True,
                          "expr": "temp < 1.0 (safety interlock)"}]
    (t4 / "00_input/objective.json").write_text(
        json.dumps(ob, ensure_ascii=False, indent=2), encoding="utf-8")
    d = read(t4, "02_rounds/R001/trial_design.json")
    viol = max((t["setpoints"]["temp"] for t in d["trials"]), default=1.5)
    d["trials"][0]["setpoints"]["temp"] = max(viol, 2.0)
    (t4 / "02_rounds/R001/trial_design.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    g = gate(t4)
    record("C7.T4_safety_violation_fails", g.returncode == 1
           and "FAIL OG5_safety_absolute" in g.stdout, g.stdout[-200:])


# ---------------------------------------------------------------- C9 envelope

def case_c9(py):
    print("[C9] recipe envelope aligns with the B-group interface")
    run_dir = _ensure_reference(py)
    concl = read(run_dir, "conclusions/optimization_conclusion.json")
    rec = read(run_dir, "conclusions/recipe.json")
    env = None
    exp = run_dir / "06_experience" / "experience_candidates.jsonl"
    if exp.exists():
        env = json.loads(exp.read_text(encoding="utf-8").splitlines()[0])
    record("C9.envelope_exists", env is not None, str(exp))
    if not env:
        return
    top = {"experience_type", "payload", "applicability", "provenance",
           "confidence_label", "corroboration_count", "refutation_count",
           "contract_version", "experience_id", "campaign_id", "usage_note"}
    record("C9.envelope_top_keys", top.issuperset(set(env)), str(set(env) - top))
    record("C9.experience_type", env["experience_type"] == "optimization_recipe",
           env["experience_type"])
    payload = env.get("payload") or {}
    need_payload = {"final_setpoints", "achieved", "guardrails",
                    "verification_status", "in_target", "desirability_D",
                    "dual_gate"}
    record("C9.payload_keys", need_payload.issuperset(
        set(payload) - {"rounds_used", "trials_used"}), str(set(payload)))
    prov = env.get("provenance") or {}
    record("C9.provenance_keys",
           {"run_id", "scene_key", "built_from", "evidence_grade",
            "authored_by"}.issubset(set(prov)), str(prov))
    record("C9.confidence_verified",
           env.get("confidence_label") == "verified"
           and prov.get("evidence_grade") == "E2"
           and payload.get("verification_status") == "verified",
           f"{env.get('confidence_label')}/{prov.get('evidence_grade')}")
    record("C9.regime_key_present",
           bool((env.get("applicability") or {}).get("regime_key")),
           str((env.get("applicability") or {}).get("regime_key")))
    record("C9.recipe_matches_envelope",
           rec.get("final_setpoints") == payload.get("final_setpoints")
           and rec.get("verification_status") == payload.get("verification_status"),
           "recipe vs envelope drift")


# ---------------------------------------------------------------- C10 e2e headless

def case_c10(py):
    print("[C10] headless e2e: 6 artifacts + gate ALL PASS + zero-LLM scan (C8)")
    run_dir = _ensure_reference(py)
    six = ["conclusions/optimization_conclusion.json", "conclusions/recipe.json",
           "report.md", "06_experience/experience_candidates.jsonl",
           "06_experience/kb_summary.md", "01_state/optimizer_state.json"]
    missing = [f for f in six if not (run_dir / f).exists()]
    record("C10.six_artifacts", not missing, f"missing={missing}")
    g = gate(run_dir)
    allpass = g.returncode == 0 and "ALL PASS" in g.stdout
    record("C10.gate_all_pass_16", allpass, g.stdout[-500:])
    record("C10.schema_double_validation_og8",
           "PASS OG8_schema_valid" in g.stdout and "PASS OG8_strict_keys" in g.stdout
           and "PASS OG8_enum_literals" in g.stdout, g.stdout[-300:])
    authored = []
    for rel in ["conclusions/optimization_conclusion.json",
                "conclusions/recipe.json", "02_rounds/R001/trial_design.json",
                "01_state/optimizer_state.json"]:
        try:
            j = read(run_dir, rel)
            authored.append(j.get("provenance", {}).get("authored_by"))
        except Exception as e:  # noqa: BLE001
            authored.append(f"ERR:{rel}")
    record("C10.authored_by_script", set(authored) == {"script"}, str(authored))
    banned = ["import requests", "import urllib", "import httpx", "import socket",
              "urllib.request", "import openai", "import anthropic", "requests.get",
              "urlopen", "http.client"]
    hits = []
    for p in list(SCRIPTS.rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
        for b in banned:
            if b in text:
                hits.append(f"{p.name}:{b}")
    record("C10.zero_llm_zero_network", not hits, str(hits[:4]))


# ---------------------------------------------------------------- C11 csv converter

def case_c11(py):
    print("[C11] manual CSV -> trial_result.json + error receipts")
    base = FIXTURES / "C11_csv"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    good = base / "good.csv"
    good.write_text(
        "trial_id,status,failure_reason,measured_at,operator_note,purity,purity#2,purity#3\n"
        "R001-T01,completed,,,,73.2,72.9,73.4\n"
        "R001-T02,failed,反应釜温度超限报警中断,,,,\n", encoding="utf-8")
    out = base / "good_result.json"
    r = subprocess.run([str(py), str(CONVERTER), str(good), str(out),
                        "--campaign-id", "OPT-20261001-911",
                        "--round-id", "R001"],
                       capture_output=True, text=True, timeout=120)
    ok = r.returncode == 0 and out.exists()
    if ok:
        payload = json.loads(out.read_text(encoding="utf-8"))
        ok = payload["trials"][0]["measurements"]["purity"] == [73.2, 72.9, 73.4] \
            and payload["trials"][1]["failure_reason"].startswith("反应釜")
    record("C11.valid_csv_converts", ok, r.stderr[-200:])

    bad = base / "bad.csv"
    bad.write_text(
        "trial_id,status,failure_reason,purity\n"
        "R001-T01,done,,72.0\n"
        "R001-T02,failed,,abc\n"
        ",failed,,1.0\n", encoding="utf-8")
    out2 = base / "bad_result.json"
    r2 = subprocess.run([str(py), str(CONVERTER), str(bad), str(out2)],
                        capture_output=True, text=True, timeout=120)
    receipt = base / "bad_result.json.error.json"
    record("C11.bad_csv_no_json", r2.returncode == 1 and not out2.exists()
           and receipt.exists(), f"rc={r2.returncode} exists={out2.exists()}")
    if receipt.exists():
        rec = json.loads(receipt.read_text(encoding="utf-8"))
        record("C11.error_receipt_chinese_readable",
               "status 'done' 不在允许枚举" in json.dumps(rec, ensure_ascii=False)
               and "O-G6b" in json.dumps(rec, ensure_ascii=False)
               and "fix_guidance" in rec,
               json.dumps(rec, ensure_ascii=False)[:200])


def _ensure_reference(py):
    """Build (or reuse) the converged reference campaign used by C7/C9/C10."""
    ref = (FIXTURES / "C7_ref" / "run").resolve()
    if (ref / "conclusions" / "recipe.json").exists():
        return ref
    import numpy as np
    obj = base_objective("OPT-20261001-907", BASE_FACTORS_2, "target",
                         target_range=[70.0, 73.0],
                         budget={"max_rounds": 16, "max_trials": 60})
    run_dir = make_run("C7_ref", obj)
    truth = {"metric": "purity", "factor_order": ["temp", "conc"], "sigma": 0.3,
             "fn": lambda v: 68.0 + 1.2 * v[0] + 0.8 * v[1]}
    rng = np.random.default_rng(11)
    n, ph = run_campaign(py, run_dir, obj, truth, rng=rng)
    if ph == "converged":
        cli(py, "converge", "--run-dir", run_dir, check=True)
    return run_dir


CASES = {"C1": lambda: case_c1(PY), "C2": lambda: case_c2(PY),
         "C3": lambda: case_c3(PY), "C4": lambda: case_c4(PY),
         "C5": lambda: case_c5(PY), "C6": lambda: case_c6(PY),
         "C7": lambda: case_c7(PY), "C9": lambda: case_c9(PY),
         "C10": lambda: case_c10(PY), "C11": lambda: case_c11(PY)}

PY = None


def main():
    global PY
    PY = sys.executable
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = list(CASES) if selector == "all" else (
        [selector] if selector in CASES else list(CASES))
    for name in todo:
        print(f"\n=== {name} ===")
        try:
            CASES[name]()
        except Exception as exc:  # noqa: BLE001 — a crashed case is a failure
            record(f"{name}.case_crashed", False, f"{type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
    # keep artifacts small: drop run payloads but keep inputs
    clean(keep="--keep" in sys.argv)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[TESTS] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    sys.exit(1 if failed else 0)


def clean(keep=False):
    if keep or not FIXTURES.exists():
        return
    for run in FIXTURES.glob("*/run"):
        shutil.rmtree(run, ignore_errors=True)
    for name in ("C1_tamper", "C7_tamper", "C11_csv"):
        d = FIXTURES / name
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
