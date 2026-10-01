#!/usr/bin/env python
"""Test runner for industrial-doe-analyzer (plan AC1-AC8).

Usage (from repo root, inside the uv venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/run_tests.py [case|all]

Cases:
  F1  2^3 full factorial x2 replicates (seed 42)   -> AC1 + gate + headless
  F2  2^(4-1) fractional, D=ABC, resolution IV     -> AC2 (aliasing disclosure)
  F3  CCD with quadratic ground truth              -> AC7 (stationary point recovery)
  F4  observational AR(1) lag-3 truth + trend trap -> AC3 (anti-spurious chain)
  F5  stability/capability with planted drift      -> AC4 (change point + Cp/Cpk)
  F6  unbalanced 2^2 with interaction              -> P0-5 (ss_extra_ss = independent
      reduced-model refit; UNBALANCED_DESIGN caveat)
  F7  observational minimize-goal                  -> P0-1 (delta>0, ci95 brackets it)
  F8  dual-response observational                  -> P0-2 (per-target dR2 contribution)
  F9  constant response, designed                  -> P0-3 (strict JSON, adj_r2 null)
  F10 6-row tiny data                              -> P0-4 (0 plots legal, gate PASS)
  F11 "Runtime (s)" + real date col                -> P0-6 (time axis picks the date)
  tamper  G1/G3/G4 gate negative battery           -> AC5
  conflict  same-factor disjoint windows           -> P0-7 (chosen = higher |delta|)
  report-D designed report (F3 CCD)                -> Phase C (sections trim + G7 + tamper)
  report-O observational report (F4)               -> Phase C (mode trim + G7)
  trend-block observational trend_confounded pair  -> Phase C fix (no window, watchlist)
  conc-rules grade checklist v2 + limitations      -> Phase C fix (balanced None,
                                                      model_adequacy, model/corr inheritance)
"""

import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
FIXTURES = (HERE / "fixtures").resolve()

ANALYZE = SCRIPTS / "analyze.py"
GATE = SCRIPTS / "quality_gate.mjs"

RESULTS = []


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def make_run(name, df, ctx):
    """Fixture dir is ALWAYS a direct child of the fixtures root (containment
    guard before any directory creation)."""
    safe_name = Path(str(name)).name
    run_dir = (FIXTURES / safe_name / "run").resolve()
    if FIXTURES not in run_dir.parents:
        raise ValueError(f"fixture path escaped fixtures root: {name}")
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    df.to_csv(run_dir / "00_input" / "data.csv", index=False)
    if ctx is not None:
        ctx_payload = json.dumps(ctx, ensure_ascii=False, indent=2)
        (run_dir / "00_input" / "analysis_context.json").write_text(
            ctx_payload, encoding="utf-8")
    return run_dir


def run_analyze(run_dir):
    return subprocess.run(
        [sys.executable, str(ANALYZE), "all", "--run-dir", str(run_dir)],
        capture_output=True, text=True, timeout=600, shell=False)


def run_gate(run_dir):
    return subprocess.run(
        ["node", str(GATE), str(run_dir),
         "--skill-path", str(SKILL), "--shared-path", str(SHARED)],
        capture_output=True, text=True, timeout=300, shell=False)


def read(run_dir, rel):
    return json.loads((Path(run_dir) / rel).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- fixtures

def fixture_f1():
    rng = np.random.default_rng(42)
    rows = []
    for _rep in range(2):
        for a, b, c in itertools.product([-1, 1], repeat=3):
            y = 50 + 2.0 * a - 1.5 * b + 0.0 * c + 0.3 * a * b + rng.normal(0, 0.3)
            rows.append({"A": a, "B": b, "C": c, "quality": round(float(y), 4)})
    df = pd.DataFrame(rows)
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "quality", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": "A", "type": "numeric"}, {"col": "B", "type": "numeric"},
                       {"col": "C", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
           "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F1 fixture"]}}
    return make_run("F1", df, ctx), ctx


def fixture_f2():
    rng = np.random.default_rng(7)
    rows = []
    for _rep in range(2):
        for a, b, c in itertools.product([-1, 1], repeat=3):
            d = a * b * c
            y = 40 + 1.5 * a - 0.8 * b + 0.3 * c + rng.normal(0, 0.4)
            rows.append({"A": a, "B": b, "C": c, "D": d, "yield": round(float(y), 4)})
    df = pd.DataFrame(rows)
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "yield", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": n, "type": "numeric"} for n in "ABCD"],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
           "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F2 fixture"]}}
    return make_run("F2", df, ctx), ctx


def fixture_f3():
    rng = np.random.default_rng(11)
    alpha = 1.682
    rows = []
    for a, b, c in itertools.product([-1, 1], repeat=3):
        rows.append((a, b, c))
    for f in [-1, 1]:  # axial
        rows.append((f * alpha, 0, 0))
        rows.append((0, f * alpha, 0))
        rows.append((0, 0, f * alpha))
    for _ in range(6):  # center
        rows.append((0, 0, 0))
    data = []
    for a, b, c in rows:
        y = 60 + 2 * a - 3 * b + 1 * c - 2 * a * a - 1.5 * b * b - 1 * c * c \
            + rng.normal(0, 0.5)
        data.append({"temp": a, "pressure": b, "flow": c, "purity": round(float(y), 4)})
    df = pd.DataFrame(data)
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "purity", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": n, "type": "numeric"}
                       for n in ("temp", "pressure", "flow")],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
           "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F3 fixture"]}}
    return make_run("F3", df, ctx), ctx


def fixture_f4():
    rng = np.random.default_rng(13)
    n = 600
    t = np.arange(n, dtype=float)
    x1 = np.zeros(n)
    x1[0] = rng.normal()
    for i in range(1, n):
        x1[i] = 0.9 * x1[i - 1] + rng.normal()
    x1_lag = np.empty(n)
    x1_lag[:3] = x1[:3]
    x1_lag[3:] = x1[:-3]
    y = 0.8 * x1_lag + 0.02 * t + rng.normal(0, 0.3, n)
    x2 = 0.05 * t + rng.normal(0, 0.5, n)   # shared trend -> spurious pair
    x3 = rng.normal(0, 1, n)                 # independent control
    df = pd.DataFrame({"t": t, "x1": x1, "x2": x2, "x3": x3, "y": y})
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "y", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": "x1", "type": "numeric"}, {"col": "x2", "type": "numeric"},
                       {"col": "x3", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": "t",
           "group_col": None, "run_order_col": None, "max_lag": 10, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F4 fixture"]}}
    return make_run("F4", df, ctx), ctx


def fixture_f5():
    rng = np.random.default_rng(17)
    n = 300
    mean = np.where(np.arange(n) < 100, 50.0, 52.0)
    y = mean + rng.normal(0, 1.0, n)
    p = 20 + rng.normal(0, 0.8, n)
    df = pd.DataFrame({"t": np.arange(n, dtype=float), "p": p, "y": np.round(y, 4)})
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "y", "goal": "target", "lsl": 46.0,
                          "usl": 54.0, "target": 50.0, "weight": None}],
           "factors": [{"col": "p", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": "t",
           "group_col": None, "run_order_col": None, "max_lag": 10, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F5 fixture"]}}
    return make_run("F5", df, ctx), ctx


# ---------------------------------------------------------------- strict JSON

def _no_nonfinite_constant(tok):
    raise AssertionError(f"non-standard JSON constant in artifact: {tok}")


def strict_parse(path):
    """json.loads that rejects Infinity/-Infinity/NaN literals + walk check."""
    text = Path(path).read_text(encoding="utf-8")
    obj = json.loads(text, parse_constant=_no_nonfinite_constant)

    def walk(v):
        if isinstance(v, dict):
            return all(walk(x) for x in v.values())
        if isinstance(v, list):
            return all(walk(x) for x in v)
        if isinstance(v, float):
            return v == v and v not in (float("inf"), float("-inf"))
        return True
    assert walk(obj), "non-finite float survived strict parse"
    return obj


ARTIFACTS = [
    "00_input/analysis_context.json",
    "01_profile/data_profile.json",
    "02_analysis/effect_table.json",
    "02_analysis/model.json",
    "02_analysis/correlation_report.json",
    "02_analysis/stability_report.json",
    "03_figures/plot_manifest.json",
    "conclusions/recommendations.json",
    "conclusions/doe_conclusion.json",
]


# ---------------------------------------------------------------- fixtures

def fixture_f6():
    """Unbalanced 2^2 with an interaction, deterministic (noise-free) response."""
    rows, reps = [], {(-1, -1): 3, (-1, 1): 2, (1, -1): 5, (1, 1): 2}
    for (a, b), k in reps.items():
        for _ in range(k):
            y = 50.0 + 2.0 * a - 1.5 * b + 1.2 * a * b
            rows.append({"A": a, "B": b, "yield": round(y, 6)})
    df = pd.DataFrame(rows)
    ctx = {"data_path": "00_input/data.csv", "mode_override": "designed",
           "responses": [{"col": "yield", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": "A", "type": "numeric"},
                       {"col": "B", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
           "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F6 fixture"]}}
    return make_run("F6", df, ctx), df


def fixture_f7():
    rng = np.random.default_rng(23)
    n = 400
    t = np.arange(n, dtype=float)
    x = 60.0 + 0.05 * t + rng.normal(0, 1.0, n)
    y = 200.0 - 1.5 * x + rng.normal(0, 0.8, n)   # x up -> y down (minimize goal)
    df = pd.DataFrame({"t": t, "x": np.round(x, 3), "y": np.round(y, 4)})
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "y", "goal": "minimize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": "x", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": "t",
           "group_col": None, "run_order_col": None, "max_lag": 10, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F7 fixture"]}}
    return make_run("F7", df, ctx), ctx


def fixture_f8():
    rng = np.random.default_rng(29)
    n = 300
    t = np.arange(n, dtype=float)
    x1 = rng.normal(50, 5, n)
    x2 = rng.normal(10, 2, n)
    y1 = 3.0 * x1 + rng.normal(0, 0.5, n)
    y2 = 2.0 * x2 + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"t": t, "x1": np.round(x1, 3), "x2": np.round(x2, 3),
                       "y1": np.round(y1, 4), "y2": np.round(y2, 4)})
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "y1", "goal": "maximize", "lsl": None, "usl": None,
                          "target": None, "weight": None},
                         {"col": "y2", "goal": "maximize", "lsl": None, "usl": None,
                          "target": None, "weight": None}],
           "factors": [{"col": "x1", "type": "numeric"},
                       {"col": "x2", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": "t",
           "group_col": None, "run_order_col": None, "max_lag": 10, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F8 fixture"]}}
    return make_run("F8", df, ctx), ctx


def fixture_f9():
    rows = []
    for _rep in range(2):
        for a, b in itertools.product([-1, 1], repeat=2):
            rows.append({"A": a, "B": b, "quality": 88.0})   # constant response
    df = pd.DataFrame(rows)
    ctx = {"data_path": "00_input/data.csv", "mode_override": None,
           "responses": [{"col": "quality", "goal": "maximize", "lsl": None,
                          "usl": None, "target": None, "weight": None}],
           "factors": [{"col": "A", "type": "numeric"}, {"col": "B", "type": "numeric"}],
           "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
           "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
           "effect_size_threshold": 0.01, "constraints": [],
           "inference": {"assigned_by": "user", "notes": ["F9 fixture"]}}
    return make_run("F9", df, ctx), ctx


def fixture_f10():
    df = pd.DataFrame({
        "speed": ["lo", "hi", "lo", "hi", "lo", "hi"],
        "yield": [4.9, 7.2, 5.1, 6.8, 5.0, 7.5]})
    return make_run("F10", df, None)   # no context -> auto-inference path


def fixture_f11():
    n = 40
    dates = pd.date_range("2026-01-01", periods=n, freq="D").strftime("%Y-%m-%d")
    runtime = np.linspace(500, 2500, n).round(1)   # numeric, name contains "time"
    temp = np.linspace(140, 200, n).round(1)
    yld = (50 + 0.4 * (temp - 140)).round(2)
    df = pd.DataFrame({"Runtime (s)": runtime, "日期": dates,
                       "temp": temp, "yield": yld})
    return make_run("F11", df, None)   # no context -> auto-inference path


# ---------------------------------------------------------------- cases

def case_f1():
    print("== F1: 2^3 full factorial x2 replicates (AC1) ==")
    run_dir, _ = fixture_f1()
    proc = run_analyze(run_dir)
    record("F1.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    eff = read(run_dir, "02_analysis/effect_table.json")
    fam = eff["families"][0]
    tests = {t["term"]: t for t in fam["tests"]}
    record("F1.sign_A_positive", tests["A"]["coefficient"] > 1.0,
           f"coefA={tests['A']['coefficient']}")
    record("F1.sign_B_negative", tests["B"]["coefficient"] < -1.0,
           f"coefB={tests['B']['coefficient']}")
    record("F1.q_A_sig", tests["A"]["q_value_bh"] < 0.05, str(tests["A"]["q_value_bh"]))
    record("F1.q_B_sig", tests["B"]["q_value_bh"] < 0.05, str(tests["B"]["q_value_bh"]))
    record("F1.q_C_not_sig", (tests["C"]["q_value_bh"] or 1) > 0.05,
           str(tests["C"]["q_value_bh"]))
    truth = {"A": 2.0, "B": -1.5, "C": 0.0, "A:B": 0.3, "A:C": 0.0, "B:C": 0.0}
    est = {k: abs(tests[k]["coefficient"]) for k in truth if k in tests}
    from scipy.stats import spearmanr
    keys = sorted(est)
    rho = spearmanr([est[k] for k in keys],
                    [abs(truth[k]) for k in keys]).statistic
    record("F1.effect_rank_corr>=0.9", rho >= 0.9, f"rho={rho}")
    top2 = sorted(est, key=est.get, reverse=True)[:2]
    record("F1.top2_are_A_B", set(top2) == {"A", "B"}, str(top2))
    recs = read(run_dir, "conclusions/recommendations.json")
    wfact = {w["factor"] for w in recs["operating_windows"]}
    record("F1.window_A_present", "A" in wfact, str(wfact))
    conc = read(run_dir, "conclusions/doe_conclusion.json")
    record("F1.authored_by_script", conc["authored_by"] == "script", "")
    record("F1.grade_A_or_A-", conc["evidence_grade"] in ("A", "A-"),
           conc["evidence_grade"])
    gate = run_gate(run_dir)
    record("F1.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f2():
    print("== F2: 2^(4-1) fractional factorial, resolution IV (AC2) ==")
    run_dir, _ = fixture_f2()
    proc = run_analyze(run_dir)
    record("F2.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    profile = read(run_dir, "01_profile/data_profile.json")
    design = profile["design"]
    record("F2.design_fractional", design["design_type"] == "fractional_factorial",
           design["design_type"])
    record("F2.resolution_IV", design.get("resolution") == 4,
           str(design.get("resolution")))
    record("F2.generator_D=ABC", "D = ABC" in (design.get("generators") or []),
           str(design.get("generators")))
    ab_aliases = (design.get("alias_chains") or {}).get("AB", [])
    record("F2.AB_aliased_with_CD", "CD" in ab_aliases, str(ab_aliases))
    eff = read(run_dir, "02_analysis/effect_table.json")
    fam = eff["families"][0]
    aliased_2fi = [t for t in fam["tests"] if ":" in t["term"]
                   and t.get("estimable") is False]
    record("F2.aliased_2fi_marked", len(aliased_2fi) >= 1,
           json.dumps([(t["term"], t.get("estimable"),
                        t.get("reason_code")) for t in fam["tests"]]))
    record("F2.aliased_reason_code",
           all(t.get("reason_code") == "aliased" for t in aliased_2fi),
           str([(t["term"], t.get("reason_code")) for t in aliased_2fi]))
    record("F2.aliased_rows_no_q",
           all(t.get("q_value_bh") is None for t in aliased_2fi),
           str([(t["term"], t.get("q_value_bh")) for t in aliased_2fi]))
    record("F2.main_estimable",
           any(t["term"] == "A" and t.get("estimable") and t.get("p_value") is not None
               for t in fam["tests"]),
           json.dumps([(t["term"], t.get("p_value")) for t in fam["tests"]]))
    gate = run_gate(run_dir)
    record("F2.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f3():
    print("== F3: CCD quadratic recovery (AC7) ==")
    run_dir, _ = fixture_f3()
    proc = run_analyze(run_dir)
    record("F3.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    profile = read(run_dir, "01_profile/data_profile.json")
    record("F3.detected_ccd", profile["design"]["design_type"] == "rsm_ccd",
           profile["design"]["design_type"])
    model = read(run_dir, "02_analysis/model.json")[0]
    st = model.get("stationary_point")
    record("F3.stationary_present", st is not None, "no stationary point")
    if not st:
        return
    expected_raw = {"temp": 0.5, "pressure": -1.0, "flow": 0.5}
    errs = {k: abs(st["raw"][k] - v) for k, v in expected_raw.items()}
    tol = 0.05 * 2 * 1.682  # 5% of the raw factor range
    record("F3.stationary_within_5pct", max(errs.values()) <= tol,
           f"errs={errs} tol={round(tol, 3)}")
    record("F3.classified_max", st["classification"] == "max", st["classification"])
    record("F3.inside_region", st["inside_design_region"] is True, "")
    # Phase C grade rules: CCD balanced is None (not a fail) and the quadratic
    # ground truth leaves lack-of-fit non-significant -> every evaluable gate
    # passes -> grade A (recomputed under the new checklist, not the old A-).
    conc = read(run_dir, "conclusions/doe_conclusion.json")
    record("F3.balanced_not_rated", conc["grade_checklist"]["balanced"] is None,
           str(conc["grade_checklist"]))
    record("F3.model_adequacy_ok", conc["grade_checklist"]["model_adequacy_ok"] is True,
           str(conc["grade_checklist"]))
    record("F3.grade_A_under_new_rules", conc["evidence_grade"] == "A",
           conc["evidence_grade"])
    gate = run_gate(run_dir)
    record("F3.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f4():
    print("== F4: observational lag-3 truth + trend trap (AC3) ==")
    run_dir, _ = fixture_f4()
    proc = run_analyze(run_dir)
    record("F4.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    corr = read(run_dir, "02_analysis/correlation_report.json")
    pairs = {(p["target"], p["parameter"]): p for p in corr["pairs"]}
    p1 = pairs.get(("y", "x1"))
    record("F4.pair_x1_present", p1 is not None, str(list(pairs)))
    if p1:
        # core_stats CCF convention: best_lag < 0 means the PARAMETER led the
        # target (target(t) ~ param(t+lag)); x1 leads y by 3 -> lag = -3
        record("F4.lag3_detected", p1.get("best_lag") == -3, str(p1.get("best_lag")))
        record("F4.x1_verdict_not_fail",
               p1.get("anti_spurious_verdict") in ("PASS", "CAUTION"),
               p1.get("anti_spurious_verdict"))
    p2 = pairs.get(("y", "x2"))
    record("F4.pair_x2_present", p2 is not None, "")
    if p2:
        record("F4.x2_trend_confounded", p2.get("trend_confounded") is True,
               f"r={p2['r']} detrended={p2.get('detrended_r')}")
        record("F4.x2_not_pass", p2.get("anti_spurious_verdict") in ("CAUTION", "FAIL"),
               p2.get("anti_spurious_verdict"))
    bad = [p for p in corr["pairs"]
           if abs(p.get("r") or 0) >= 0.3 and not p.get("anti_spurious_verdict")]
    record("F4.all_r03_have_verdicts", not bad, str(bad[:2]))
    recs = read(run_dir, "conclusions/recommendations.json")
    wins_ = recs["operating_windows"]
    record("F4.windows_exist", len(wins_) >= 1, str(len(wins_)))
    record("F4.all_confirmation_needed",
           all(w["confirmation_needed"] is True for w in wins_),
           json.dumps([w.get("confirmation_needed") for w in wins_]))
    record("F4.confidence_low", all(w["confidence"] == "low" for w in wins_), "")
    record("F4.confirmations_present", len(recs["confirmations"]) >= 1, "")
    conc = read(run_dir, "conclusions/doe_conclusion.json")
    record("F4.grade_B", conc["evidence_grade"] == "B", conc["evidence_grade"])
    gate = run_gate(run_dir)
    record("F4.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f5():
    print("== F5: stability/capability with planted drift (AC4) ==")
    run_dir, _ = fixture_f5()
    proc = run_analyze(run_dir)
    record("F5.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    stab = read(run_dir, "02_analysis/stability_report.json")
    cps = [c for c in stab["change_points"] if c["response"] == "y"]
    record("F5.change_point_found", bool(cps and cps[0]["positions"]),
           json.dumps(stab["change_points"]))
    if cps and cps[0]["positions"]:
        cp0 = cps[0]["positions"][0]
        record("F5.cp_localized", abs(cp0 - 100) <= 25, f"cp={cp0}")
    cap = next(c for c in stab["capability"] if c["response"] == "y")
    # reference implementation: same formulas recomputed from the raw fixture
    x = pd.to_numeric(pd.read_csv(Path(run_dir) / "00_input" / "data.csv")["y"],
                      errors="coerce").dropna()
    mr = x.diff().abs().dropna().mean()
    sigma_within = float(mr) / 1.128
    mean, s = float(x.mean()), float(x.std(ddof=1))
    exp_cpk = min((54.0 - mean) / (3 * sigma_within), (mean - 46.0) / (3 * sigma_within))
    record("F5.cpk_label_honest", "MRbar" in (cap.get("cpk_label") or ""),
           str(cap.get("cpk_label")))
    record("F5.cpk_matches_reference", cap.get("cpk") is not None
           and abs(cap["cpk"] - exp_cpk) < 1e-6,
           f"got={cap.get('cpk')} exp={round(exp_cpk, 6)}")
    record("F5.ppk_present", cap.get("ppk") is not None, "")
    gate = run_gate(run_dir)
    record("F5.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_tamper():
    print("== tamper: gate negative battery (AC5) ==")
    base = FIXTURES
    base.mkdir(parents=True, exist_ok=True)

    # G1: effect row missing q WITHOUT reason_code -> FAIL
    t1 = (base / "tamper_g1").resolve()
    if FIXTURES not in t1.parents:
        raise ValueError("fixture escaped root")
    (t1 / "01_profile").mkdir(parents=True, exist_ok=True)
    (t1 / "02_analysis").mkdir(parents=True, exist_ok=True)
    (t1 / "01_profile" / "data_profile.json").write_text(json.dumps(
        {"design": {"mode": "designed", "design_type": "full_factorial"}}),
        encoding="utf-8")
    (t1 / "02_analysis" / "effect_table.json").write_text(json.dumps({
        "generated_at": "t", "mode": "designed",
        "model_spec": {"main_effects": [], "interactions": [], "quadratic": []},
        "coding": {"method": "deviation", "continuous_scaling": "x"},
        "families": [{"response": "y", "tests": [{"term": "A", "coefficient": 1.0,
                                                  "estimable": True, "n": 16,
                                                  "p_value": 0.01,
                                                  "q_value_bh": None}],
                      "df_resid": 8, "r_squared": 0.5}],
        "multiple_testing": {"method": "BH", "n_families": 1, "total_tests": 1,
                             "total_significant_q05": 1}}), encoding="utf-8")
    g1 = run_gate(t1)
    record("tamper.G1_fails", g1.returncode == 1 and "G1_" in g1.stdout,
           f"rc={g1.returncode} out={g1.stdout[-300:]}")

    # G3/G4: observational window out of range + confirmation flag off -> FAIL
    t2 = (base / "tamper_g34").resolve()
    if FIXTURES not in t2.parents:
        raise ValueError("fixture escaped root")
    (t2 / "01_profile").mkdir(parents=True, exist_ok=True)
    (t2 / "conclusions").mkdir(parents=True, exist_ok=True)
    (t2 / "01_profile" / "data_profile.json").write_text(json.dumps(
        {"design": {"mode": "observational", "design_type": "observational"}}),
        encoding="utf-8")
    (t2 / "conclusions" / "doe_conclusion.json").write_text(json.dumps(
        {"analysis_mode": "observational"}), encoding="utf-8")
    (t2 / "conclusions" / "recommendations.json").write_text(json.dumps({
        "contract_version": "1.0", "audience": "downstream_agent",
        "operating_windows": [{"id": "OW-001", "factor": "temp",
                               "factor_unit": "C", "response": "y",
                               "range": [500.0, 600.0],
                               "expected_effect": {"delta": 1.0,
                                                   "direction_semantics": "per unit",
                                                   "ci95": None, "unit": None},
                               "confidence": "low", "fdr_q": None,
                               "sample_size": 10, "evidence_refs": [],
                               "extrapolation": False,
                               "confirmation_needed": False}],
        "current_baseline": {"point": {}},
        "response_specs": {}, "confirmations": [], "watchlist": [],
        "constraints": [],
        "applicability_domain": {"n_rows": 10, "time_span": None, "regime": None,
                                 "factor_observed_ranges": {"temp": {"min": 0.0,
                                                                     "max": 100.0}}},
        "invalidation_conditions": [], "usage_rules": [],
        "provenance": {"input_sha256": "x", "script_version": "1", "seed": None,
                       "authored_by": "script"}}), encoding="utf-8")
    g34 = run_gate(t2)
    record("tamper.G3_fails", g34.returncode == 1 and "FAIL G3_" in g34.stdout,
           f"rc={g34.returncode} out={g34.stdout[-300:]}")
    record("tamper.G4_fails", g34.returncode == 1 and "FAIL G4_" in g34.stdout,
           f"rc={g34.returncode} out={g34.stdout[-300:]}")


def case_f6():
    print("== F6: unbalanced 2^2 with interaction (P0-5 extra-SS semantics) ==")
    run_dir, df = fixture_f6()
    proc = run_analyze(run_dir)
    record("F6.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    profile = read(run_dir, "01_profile/data_profile.json")
    record("F6.design_mode_designed", profile["design"].get("mode") == "designed",
           str(profile["design"].get("mode")))
    codes = [c.get("code") for c in profile.get("caveats", [])]
    record("F6.unbalanced_caveat", "UNBALANCED_DESIGN" in codes, str(codes))

    # independent reference: hand-built reduced-model refit (single deletion),
    # deviation coding per method-notes C1 — (x - midrange) / half_range —
    # interaction = product. (Centering convention matters here: unbalanced
    # extra-SS is coding-dependent, which is exactly the documented caveat.)
    a_raw = df["A"].to_numpy(dtype=float)
    b_raw = df["B"].to_numpy(dtype=float)
    y = df["yield"].to_numpy(dtype=float)

    def code(v):
        lo, hi = float(np.min(v)), float(np.max(v))
        return (v - (lo + hi) / 2.0) / ((hi - lo) / 2.0)

    a, b = code(a_raw), code(b_raw)
    ab = a * b

    def rss(cols):
        X = np.column_stack([np.ones(len(y))] + list(cols))
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ beta
        return float(r @ r)

    full = rss([a, b, ab])
    ref = {"A": rss([b, ab]) - full,
           "B": rss([a, ab]) - full,
           "A:B": rss([a, b]) - full}

    eff = read(run_dir, "02_analysis/effect_table.json")
    tests = {t["term"]: t for t in eff["families"][0]["tests"]}
    record("F6.no_ss_type2_key", all("ss_type2" not in t for t in tests.values()),
           str(list(tests.values())[0].keys()))
    for term, expect in ref.items():
        got = tests[term].get("ss_extra_ss")
        record(f"F6.ss_extra_ss[{term}]", got is not None
               and abs(got - expect) <= 1e-5, f"got={got} expect={round(expect, 6)}")
    gate = run_gate(run_dir)
    record("F6.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f7():
    print("== F7: observational minimize-goal window CI consistency (P0-1) ==")
    run_dir, _ = fixture_f7()
    proc = run_analyze(run_dir)
    record("F7.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    recs = read(run_dir, "conclusions/recommendations.json")
    wins_ = recs["operating_windows"]
    record("F7.windows_exist", len(wins_) >= 1, str(len(wins_)))
    if not wins_:
        return
    for w in wins_:
        d = w["expected_effect"]["delta"]
        ci = w["expected_effect"]["ci95"]
        record(f"F7[{w['id']}].delta_positive", d is not None and d > 0,
               f"delta={d} ci95={ci}")
        record(f"F7[{w['id']}].ci_brackets_delta",
               ci is not None and ci[0] <= d <= ci[1],
               f"delta={d} ci95={ci}")
        record(f"F7[{w['id']}].semantics_goal_corrected",
               "方向已按目标校正" in (w["expected_effect"].get("direction_semantics") or ""),
               w["expected_effect"].get("direction_semantics"))
    gate = run_gate(run_dir)
    record("F7.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f8():
    print("== F8: per-target dR2 contribution (P0-2) ==")
    run_dir, _ = fixture_f8()
    proc = run_analyze(run_dir)
    record("F8.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    corr = read(run_dir, "02_analysis/correlation_report.json")
    pairs = {(p["target"], p["parameter"]): p for p in corr["pairs"]}
    record("F8.pairs_present", len(pairs) >= 4, str(list(pairs)))
    if len(pairs) < 4:
        return

    # reference: the SAME _contribution applied per target on the raw fixture
    sys.path.insert(0, str(SCRIPTS))
    from doestats.correlation import _contribution
    df = pd.read_csv(Path(run_dir) / "00_input" / "data.csv")
    refs = {}
    for target in ("y1", "y2"):
        refs[target] = _contribution(df, target, ["x1", "x2"])[0]

    record("F8.refs_discriminate", refs["y1"]["x1"] != refs["y2"]["x1"],
           f"y1={refs['y1']['x1']} y2={refs['y2']['x1']}")
    ok = True
    detail = []
    for (target, param), p in sorted(pairs.items()):
        got = p.get("contribution_delta_r2")
        expect = refs.get(target, {}).get(param)
        if got is None and expect is None:
            continue
        if got is None or expect is None or abs(got - expect) > 1e-9:
            ok = False
            detail.append(f"{target}~{param}: got={got} expect={expect}")
    record("F8.contribution_per_target", ok, "; ".join(detail[:4]))
    gate = run_gate(run_dir)
    record("F8.gate_exit0", gate.returncode == 0, gate.stdout[-500:])


def case_f9():
    print("== F9: constant response -> strict JSON + adj_r_squared null (P0-3) ==")
    run_dir, _ = fixture_f9()
    proc = run_analyze(run_dir)
    record("F9.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    parse_fail = []
    for rel in ARTIFACTS:
        p = Path(run_dir) / rel
        if not p.exists():
            continue
        try:
            strict_parse(p)
        except AssertionError as exc:
            parse_fail.append(f"{rel}: {exc}")
    record("F9.strict_json_all_artifacts", not parse_fail, "; ".join(parse_fail[:3]))
    eff = read(run_dir, "02_analysis/effect_table.json")
    model = read(run_dir, "02_analysis/model.json")
    record("F9.effect_adj_null", all(f.get("adj_r_squared") is None
                                     for f in eff["families"]),
           json.dumps([f.get("adj_r_squared") for f in eff["families"]]))
    record("F9.model_adj_null", all(m.get("adj_r_squared") is None for m in model),
           json.dumps([m.get("adj_r_squared") for m in model]))
    # Phase C: the constant-response report must render with zero leaked tokens
    report = Path(run_dir) / "report.html"
    record("F9.report_built", report.exists() and report.stat().st_size >= 20 * 1024,
           f"size={report.stat().st_size if report.exists() else 0}")
    if report.exists():
        import re as _re
        body = _re.sub(r"<script[\s\S]*?</script>", " ", report.read_text(encoding="utf-8"))
        leak = [w for w in ("NaN", "Infinity", "undefined", "null")
                if _re.search(r"\b" + w + r"\b", body)]
        record("F9.report_no_leaked_tokens", not leak, str(leak))
    gate = run_gate(run_dir)
    # PASS, or an honest figure-gate-only FAIL (degenerate data -> empty ink)
    honest = gate.returncode == 0 or all(
        fid.startswith("G5_") or fid.startswith("FILE_")
        for fid in [line.split(" ")[1] for line in gate.stdout.splitlines()
                    if line.startswith("FAIL ")])
    record("F9.gate_pass_or_honest", honest, gate.stdout[-500:])


def case_f10():
    print("== F10: 6-row tiny data -> 0 plots legal, gate PASS (P0-4) ==")
    run_dir = fixture_f10()
    proc = run_analyze(run_dir)
    record("F10.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    manifest = read(run_dir, "03_figures/plot_manifest.json")
    record("F10.manifest_parses", isinstance(manifest.get("plots"), list),
           str(type(manifest.get("plots"))))
    if manifest.get("plots") == []:
        record("F10.zero_plot_disclosed", bool(manifest.get("notes")),
               str(manifest.get("notes")))
    else:
        record("F10.zero_plot_disclosed", True, f"plots={len(manifest['plots'])}")
    gate = run_gate(run_dir)
    record("F10.gate_exit0", gate.returncode == 0, gate.stdout[-600:])


def case_f11():
    print("== F11: time-column gates pick the real date column (P0-6) ==")
    run_dir = fixture_f11()
    proc = run_analyze(run_dir)
    record("F11.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    ctx = read(run_dir, "00_input/analysis_context.json")
    record("F11.time_col_is_date", ctx.get("time_col") == "日期",
           str(ctx.get("time_col")))
    record("F11.runtime_not_time", ctx.get("time_col") != "Runtime (s)",
           str(ctx.get("time_col")))
    profile = read(run_dir, "01_profile/data_profile.json")
    notes = [n for n in (profile["design"].get("detection_notes") or [])
             if isinstance(n, str) and n.startswith("time_col:")]
    record("F11.detection_notes_written", bool(notes), str(notes[:2]))
    recs = read(run_dir, "conclusions/recommendations.json")
    span = recs["applicability_domain"].get("time_span")
    record("F11.time_span_is_date_span", span is not None and span.startswith("2026-"),
           str(span))


def case_conflict():
    print("== conflict: chosen = higher |delta| window (P0-7) ==")
    sys.path.insert(0, str(SCRIPTS))
    from doestats import windows as wins

    def w(delta, lo, hi):
        return {"id": None, "priority": None, "factor": "temp", "factor_unit": "C",
                "response": "y", "range": [lo, hi], "shape": "connected",
                "expected_effect": {"delta": delta, "direction_semantics": "per unit",
                                    "ci95": None, "unit": None},
                "confidence": "low", "fdr_q": None, "sample_size": 40,
                "evidence_refs": [], "extrapolation": False,
                "confirmation_needed": True, "notes": None}

    # |delta| 9.0 window STARTS LATER (range [30,40]) than the |delta| 5.0 one
    wins_ = [w(5.0, 10.0, 20.0), w(9.0, 30.0, 40.0)]
    df = pd.DataFrame({"temp": [12.0, 35.0], "y": [1.0, 2.0]})
    rec = wins.assemble("observational", wins_, [], [], [], [],
                        {"responses": []}, df, {}, None, "sha", "test", None)
    conflicts = rec["conflicts"]
    record("conflict.detected", len(conflicts) == 1, json.dumps(conflicts))
    if conflicts:
        record("conflict.chosen_is_higher_delta",
               conflicts[0]["chosen"] == "OW-001", json.dumps(conflicts[0]))
        wl = [x for x in rec["watchlist"] if x.get("code") == "WINDOW_CONFLICT_LOSER"]
        record("conflict.loser_demoted",
               len(wl) == 1 and "OW-002" in wl[0]["message"],
               json.dumps([x.get("message") for x in wl]))
    # inverse arrangement: bigger |delta| starts EARLIER -> still chosen
    wins2 = [w(9.0, 10.0, 20.0), w(5.0, 30.0, 40.0)]
    rec2 = wins.assemble("observational", wins2, [], [], [], [],
                         {"responses": []}, df, {}, None, "sha", "test", None)
    if rec2["conflicts"]:
        record("conflict.chosen_when_first",
               rec2["conflicts"][0]["chosen"] == "OW-001",
               json.dumps(rec2["conflicts"][0]))
    else:
        record("conflict.chosen_when_first", False, "no conflict detected")


def case_report_designed():
    print("== report-D: designed HTML report + G7 + post-build tamper (Phase C) ==")
    run_dir, _ = fixture_f3()
    proc = run_analyze(run_dir)
    record("RD.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    report = Path(run_dir) / "report.html"
    record("RD.report_built", report.exists() and report.stat().st_size >= 20 * 1024,
           f"size={report.stat().st_size if report.exists() else 0}")
    html = report.read_text(encoding="utf-8") if report.exists() else ""
    import re as _re
    body = _re.sub(r"<script[\s\S]*?</script>", " ", html) if html else ""
    leak = [w for w in ("NaN", "Infinity", "undefined", "null")
            if _re.search(r"\b" + w + r"\b", body)]
    record("RD.no_leaked_tokens", html and not leak, str(leak))
    record("RD.designed_sections_present", all(f'id="{s}"' in html for s in
           ("sec-hero", "sec-1", "sec-2", "sec-3", "sec-4", "sec-5", "sec-8",
            "sec-9", "sec-10", "sec-appendix")), "")
    record("RD.observational_sections_absent",
           not any(f'id="{s}"' in html for s in ("sec-4b", "sec-6b", "sec-7")),
           "designed report must not contain observational-only sections")
    figs = _re.findall(r'<figure class="chart"[\s\S]*?</figure>', html)
    record("RD.charts_have_readings",
           bool(figs) and all('class="chart-reading"' in f for f in figs),
           f"{len(figs)} figures")
    record("RD.meta_block_present", 'id="report-meta"' in html, "")
    gate = run_gate(run_dir)
    record("RD.gate_exit0_with_G7", gate.returncode == 0 and "G7b" in gate.stdout,
           gate.stdout[-600:])

    # tamper: change one number in an artifact AFTER the build -> G7b must fail
    eff_path = Path(run_dir) / "02_analysis" / "effect_table.json"
    original = eff_path.read_text(encoding="utf-8")
    eff = json.loads(original)
    eff["families"][0]["tests"][0]["coefficient"] = \
        (eff["families"][0]["tests"][0]["coefficient"] or 0) + 1.234
    eff_path.write_text(json.dumps(eff, ensure_ascii=False, indent=2), encoding="utf-8")
    gate_t = run_gate(run_dir)
    record("RD.tamper_G7b_fails", gate_t.returncode == 1 and "FAIL G7b" in gate_t.stdout,
           f"rc={gate_t.returncode} out={gate_t.stdout[-400:]}")
    eff_path.write_text(original, encoding="utf-8")
    gate_r = run_gate(run_dir)
    record("RD.restore_G7b_passes", gate_r.returncode == 0, gate_r.stdout[-400:])


def case_report_observational():
    print("== report-O: observational HTML report mode trim (Phase C) ==")
    run_dir, _ = fixture_f4()
    proc = run_analyze(run_dir)
    record("RO.analyze_exit0", proc.returncode == 0, proc.stderr[-600:])
    if proc.returncode != 0:
        return
    report = Path(run_dir) / "report.html"
    record("RO.report_built", report.exists() and report.stat().st_size >= 20 * 1024,
           f"size={report.stat().st_size if report.exists() else 0}")
    html = report.read_text(encoding="utf-8") if report.exists() else ""
    record("RO.obs_sections_present", all(f'id="{s}"' in html for s in
           ("sec-hero", "sec-1", "sec-2", "sec-3", "sec-6b", "sec-7", "sec-8",
            "sec-9", "sec-10", "sec-appendix")), "")
    record("RO.designed_sections_absent",
           not any(f'id="{s}"' in html for s in ("sec-4", "sec-5", "sec-6")),
           "observational report must not contain designed-only sections")
    gate = run_gate(run_dir)
    record("RO.gate_exit0_with_G7", gate.returncode == 0 and "G7b" in gate.stdout,
           gate.stdout[-600:])


def case_trend_block():
    print("== trend-block: observational trend_confounded pair gets no window ==")
    sys.path.insert(0, str(SCRIPTS))
    from doestats import windows as wins

    n = 120
    x = np.linspace(100.0, 200.0, n)
    y = 0.5 * x + 2.0                       # strong raw r, driven by the ramp
    df = pd.DataFrame({"x": x.round(3), "y": y.round(3)})
    stability = {"steady_segments": [{"start": 0, "end": n - 1, "n_rows": n,
                                      "response_means": {"y": float(y.mean())},
                                      "score": 1.0, "selected_for_windows": True}]}
    ctx = {"responses": [{"col": "y", "goal": "maximize"}],
           "_predictor_cols": ["x"], "group_col": None}
    confounded = {"pairs": [{"target": "y", "parameter": "x", "r": 0.99,
                             "detrended_r": 0.02, "trend_confounded": True}]}
    wins_c, _i, _cf, wl_c, _sp = wins.observational_windows(
        stability, {}, ctx, df, correlation=confounded)
    record("trend.blocked_no_window", len(wins_c) == 0, json.dumps(
        [(w["factor"], w["range"]) for w in wins_c]))
    hit = [w for w in wl_c if w.get("code") == "TREND_CONFOUNDED_NO_WINDOW"]
    record("trend.watchlist_entry", len(hit) == 1
           and "0.02" in hit[0]["message"] and "0.99" in hit[0]["message"],
           json.dumps([w.get("message") for w in wl_c]))
    # weak-raw pair (|r|<0.3) must NOT be blocked by this rule
    weak = {"pairs": [{"target": "y", "parameter": "x", "r": 0.05,
                       "detrended_r": 0.01, "trend_confounded": True}]}
    wins_w, _i2, _cf2, wl_w, _sp2 = wins.observational_windows(
        stability, {}, ctx, df, correlation=weak)
    record("trend.weak_pair_not_blocked",
           not any(w.get("code") == "TREND_CONFOUNDED_NO_WINDOW" for w in wl_w),
           json.dumps([w.get("code") for w in wl_w]))
    # honest pair: detrended_r survives -> window still emitted
    clean = {"pairs": [{"target": "y", "parameter": "x", "r": 0.99,
                        "detrended_r": 0.95, "trend_confounded": False}]}
    wins_o, _i3, _cf3, wl_o, _sp3 = wins.observational_windows(
        stability, {}, ctx, df, correlation=clean)
    record("trend.clean_pair_window_kept", len(wins_o) == 1, str(len(wins_o)))


def case_conc_rules():
    print("== conc-rules: grade checklist v2 + limitations inheritance (Phase C) ==")
    sys.path.insert(0, str(SCRIPTS))
    from conclusion_template import build as build_conc

    prof = {"design": {"mode": "designed", "design_type": "latin_hypercube",
                       "balanced": None, "resolution": None},
            "caveats": []}
    eff = {"families": [{"response": "y", "saturated": False, "df_pure_error": 4,
                         "lack_of_fit": {"estimable": False, "reason": "no pure-error replicates",
                                         "p_value": None}}]}
    recs = {"contract_version": "1.0", "operating_windows": [], "confirmations": [],
            "watchlist": [], "usage_rules": []}
    # (a) balanced=None must stay None (unrated) and NOT count as a failure
    c1 = build_conc(prof, eff, None, None, recs, {"plots": []}, models=None)
    record("conc.balanced_none_kept", c1["grade_checklist"]["balanced"] is None,
           str(c1["grade_checklist"]))
    record("conc.grade_A_when_only_none", c1["evidence_grade"] == "A",
           f"grade={c1['evidence_grade']} checklist={json.dumps(c1['grade_checklist'])}")
    # (b) model_adequacy: significant lack-of-fit -> False -> grade drops
    eff_bad = {"families": [{"response": "y", "saturated": False, "df_pure_error": 4,
                             "lack_of_fit": {"estimable": True, "reason": None,
                                             "f_stat": 9.1, "p_value": 0.003}}]}
    c2 = build_conc(prof, eff_bad, None, None, recs, {"plots": []}, models=None)
    record("conc.model_adequacy_fail", c2["grade_checklist"]["model_adequacy_ok"] is False,
           str(c2["grade_checklist"]))
    record("conc.grade_drops_to_A-", c2["evidence_grade"] == "A-",
           c2["evidence_grade"])
    # (c) saturated model also fails adequacy
    eff_sat = {"families": [{"response": "y", "saturated": True, "df_pure_error": 0,
                             "lack_of_fit": {"estimable": False, "p_value": None}}]}
    c3 = build_conc(prof, eff_sat, None, None, recs, {"plots": []}, models=None)
    record("conc.saturated_fails_adequacy", c3["grade_checklist"]["model_adequacy_ok"] is False,
           str(c3["grade_checklist"]))
    # (d) limitations inherit from model residual diagnostics
    models = [{"response": "y", "n": 20, "mse": 0.5,
               "residual_diagnostics": {"n_high_residual_abs_gt3sigma": 2,
                                        "max_cooks_d": 0.5}},
              {"response": "z", "n": 16, "mse": 0.0,
               "residual_diagnostics": {"n_high_residual_abs_gt3sigma": None,
                                        "max_cooks_d": None}}]
    c4 = build_conc(prof, eff, None, None, recs, {"plots": []}, models=models)
    lims = "\n".join(c4["limitations"])
    record("conc.limit_high_residual", "残差诊断" in lims and "y" in lims,
           lims[:200])
    record("conc.limit_cooks_d", "Cook" in lims, lims[:200])
    record("conc.limit_zero_variance", "零方差" in lims and "z" in lims, lims[:300])
    # (e) limitations inherit outlier-sensitivity FAILures from correlation (observational)
    prof_obs = {"design": {"mode": "observational", "design_type": "observational"},
                "caveats": []}
    corr = {"pairs": [{"parameter": "p1", "target": "y", "r": 0.6,
                       "verdicts": {"outlier_sensitivity": "SERIOUS"},
                       "anti_spurious_verdict": "CAUTION", "notes": []}]}
    c5 = build_conc(prof_obs, None, corr, None, recs, {"plots": []}, models=None)
    lims5 = "\n".join(c5["limitations"])
    record("conc.limit_outlier_sensitivity",
           "离群点敏感" in lims5 and "p1" in lims5, lims5[:200])
    record("conc.observational_still_B", c5["evidence_grade"] == "B",
           c5["evidence_grade"])


def clean_fixture_artifacts(keep=False):
    """Remove generated run artifacts (figures/analysis outputs) so the repo
    keeps only the tiny inputs. `--keep` preserves everything for debugging."""
    if keep or not FIXTURES.exists():
        return
    import shutil
    for run in FIXTURES.glob("*/run"):
        for sub in ("01_profile", "02_analysis", "03_figures", "conclusions"):
            shutil.rmtree(run / sub, ignore_errors=True)
        (run / "run_manifest.json").unlink(missing_ok=True)
        (run / "report.html").unlink(missing_ok=True)


CASES = {"F1": case_f1, "F2": case_f2, "F3": case_f3,
         "F4": case_f4, "F5": case_f5, "F6": case_f6, "F7": case_f7,
         "F8": case_f8, "F9": case_f9, "F10": case_f10, "F11": case_f11,
         "tamper": case_tamper, "conflict": case_conflict,
         "report-D": case_report_designed, "report-O": case_report_observational,
         "trend-block": case_trend_block, "conc-rules": case_conc_rules}


def main():
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    keep = "--keep" in sys.argv
    todo = list(CASES) if selector not in CASES and selector != "all" else (
        list(CASES) if selector == "all" else [selector])
    for name in todo:
        CASES[name]()
    clean_fixture_artifacts(keep=keep)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[TESTS] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
