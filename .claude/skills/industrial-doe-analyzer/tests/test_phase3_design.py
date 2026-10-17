#!/usr/bin/env python
"""Phase 3 tests — design_build / association_screen / design_next / guidance.

Usage (from the repo root, inside the shared uv venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/test_phase3_design.py [case|all]

Cases:
  build     design_build -> design_detect round-trip for all design types,
            properties completeness, determinism, CSV round-trip, code defects
            (detector gaps are reported as findings, never swallowed silently)
  next      design_next rule selection (fold_over / augment_star / augment_axial /
            confirm_replicate / space_filling / none) + hard-constraint skipping
  screen    association_screen on a planted confounder (marginal strong /
            design-adjusted null), the four kinds, causal_claim=none, no window keys
  guidance  optimization_guidance: platform_ref removal (OD-11), unit_conversion +
            rounding applied, within_limits, node_setpoint gating, lineage
  loop      optimizer-loop windows_seed gating: only marginal_diagnostic+actionable
            windows and actionable joint_setpoints are consumed; rejections traced;
            a legacy prior (no v1.1 keys) still produces the three seed classes
  schema    the four new schemas validate real payloads (shared validate.mjs)

This file is standalone: it does not modify tests/run_tests.py (frozen 136-assertion
baseline) and writes scratch payloads only to a temporary directory.
"""

import itertools
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SCHEMAS = SKILL / "schemas"
VALIDATE = REPO / ".claude" / "shared" / "scripts" / "validate.mjs"
OPT_SCRIPTS = REPO / ".claude" / "skills" / "industrial-optimizer-loop" / "scripts"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(OPT_SCRIPTS))

from doestats import design_next as dn                     # noqa: E402
from doestats import effects_anova                          # noqa: E402
from doestats.association_screen import screen              # noqa: E402
from doestats.design_build import build_design              # noqa: E402

RESULTS = []
TMP = Path(tempfile.mkdtemp(prefix="phase3_doe_"))


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def stable(payload):
    """JSON with the timestamp fields removed (RG-03: same input -> same numbers)."""
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    for field in ('"generated_at": "', '"checked_at": "'):
        while field in text:
            start = text.index(field)
            end = text.index('"', start + len(field))
            text = text[:start] + text[end + 1:]
    return text


def factors(*names, low=180.0, high=220.0, levels=None):
    out = []
    for n in names:
        f = {"name": n, "type": "numeric"}
        if levels:
            f["levels"] = list(levels)
        else:
            f.update(low=low, high=high)
        out.append(f)
    return out


# ---------------------------------------------------------------- build (P3-2)

def case_build():
    print("[build] design_build -> detect_design round-trip (DS-01 / DS-12)")
    specs = {
        "full_factorial": {"design_type": "full_factorial", "factors": factors("A", "B", "C"),
                           "replicates": 2},
        "fractional_factorial": {"design_type": "fractional_factorial",
                                 "factors": factors("A", "B", "C", "D"), "resolution": 4},
        "rsm_ccd": {"design_type": "rsm_ccd", "factors": factors("A", "B", "C"),
                    "n_center": 3},
        "rsm_bbd": {"design_type": "rsm_bbd", "factors": factors("A", "B", "C")},
        "orthogonal_array": {"design_type": "orthogonal_array",
                             "factors": factors("A", "B", "C", "D",
                                                levels=[1.0, 2.0, 3.0])},
        "latin_hypercube": {"design_type": "latin_hypercube", "factors": factors("A", "B", "C"),
                            "runs": 10},
        "d_optimal": {"design_type": "d_optimal", "factors": factors("A", "B", "C", "D"),
                      "runs": 8},
    }
    built, exact, mapped = {}, 0, 0
    for dtype, spec in specs.items():
        b = build_design(spec, seed=42)
        built[dtype] = b
        rt = b["properties"]["roundtrip"]
        if dtype == "rsm_bbd":
            # frozen design_detect cannot recover a canonical BBD (its pair-count rule
            # is unsatisfiable for Box-Behnken); accepted outcome = exact recovery
            # (if the detector is fixed later) OR the documented gap code.
            ok = rt["match"] is True or rt["gap"] == "design_detect_bbd_rule_unsatisfiable"
        else:
            ok = rt["match"] is True
            if dtype in ("full_factorial", "fractional_factorial", "rsm_ccd",
                         "orthogonal_array", "latin_hypercube"):
                exact += 1 if rt["detected_type"] == dtype else 0
        if rt["detected_type"] == dtype:
            mapped += 1
        record(f"build.roundtrip.{dtype}", bool(ok),
               f"detected={rt['detected_type']} match={rt['match']} "
               f"error={rt['detector_error']} gap={rt['gap']}")
        if rt["detector_error"] or rt["gap"]:
            print(f"        [detector] {dtype}: {rt['detector_error'] or rt['gap']}")
    record("build.roundtrip.exact_5of5",
           all(built[d]["properties"]["roundtrip"]["detected_type"] == d
               for d in ("full_factorial", "fractional_factorial", "rsm_ccd",
                         "orthogonal_array", "latin_hypercube")),
           str({d: built[d]["properties"]["roundtrip"]["detected_type"] for d in built}))
    record("build.roundtrip.bbd_documented_gap",
           built["rsm_bbd"]["properties"]["roundtrip"]["detected_type"] == "rsm_bbd"
           or built["rsm_bbd"]["properties"]["roundtrip"]["gap"] is not None,
           f"detected={built['rsm_bbd']['properties']['roundtrip']['detected_type']} "
           f"gap={built['rsm_bbd']['properties']['roundtrip']['gap']}")
    record("build.roundtrip.d_optimal_designed",
           built["d_optimal"]["properties"]["roundtrip"]["match"] is True,
           str(built["d_optimal"]["properties"]["roundtrip"]))

    full = built["full_factorial"]["properties"]
    record("build.properties_complete",
           all(k in full for k in ("resolution", "defining_relation", "alias_chains",
                                   "vif", "power", "mde", "d_efficiency"))
           and full["d_efficiency"]["value"] == 1.0
           and full["mde"]["value"] is not None
           and full["power"]["at_2mde"]["min"] is not None
           and all(v == 1.0 for v in full["vif"].values()),
           f"mde={full['mde']['value']} Deff={full['d_efficiency']['value']}")
    frac = built["fractional_factorial"]["properties"]
    record("build.fractional_generator_recovery",
           frac["resolution"] == 4 and frac["defining_relation"] == ["ABCD"]
           and frac["alias_chains"].get("A") == ["BCD"],
           json.dumps({k: frac[k] for k in ("resolution", "defining_relation",
                                            "alias_chains")}, ensure_ascii=False))

    # determinism (RG-03): same spec + seed twice
    a = json.dumps(build_design(specs["full_factorial"], seed=42), sort_keys=True)
    b = json.dumps(build_design(specs["full_factorial"], seed=42), sort_keys=True)
    record("build.deterministic", a == b, "two builds differ")
    no_seed = build_design(specs["full_factorial"])
    record("build.no_seed_natural_order",
           no_seed["randomization"]["randomized"] is False
           and [r["run_order"] for r in no_seed["run_table"]] == list(range(1, 17)),
           str(no_seed["randomization"]))

    # run table contract §1 columns + randomization disclosure
    rnd = built["full_factorial"]
    first = rnd["run_table"][0]
    record("build.run_table_columns",
           set(first) >= {"run_id", "design_point_id", "run_order", "block", "A", "B", "C"}
           and len({r["run_id"] for r in rnd["run_table"]}) == len(rnd["run_table"]),
           str(sorted(first)))
    record("build.randomized_with_seed",
           rnd["randomization"]["randomized"] is True
           and "randomized_within_block" in rnd["randomization"]["block_policy"],
           rnd["randomization"]["block_policy"])
    rep = [r for r in rnd["run_table"] if r.get("replicate_kind") == "replicate"]
    record("build.replicate_grouping", len(rep) == 16 and all(
        r.get("replicate_group") for r in rep), f"n_rep={len(rep)}")

    # coded matrix + explicit failure paths
    rec0 = rnd["run_table"][0]
    coded0 = [c for c in rnd["coded"] if c["run_id"] == rec0["run_id"]][0]
    record("build.coded_matrix",
           all(abs(coded0[f]) <= 1.0 + 1e-9 for f in ("A", "B", "C")),
           str(coded0))
    try:
        build_design({"design_type": "rsm_bbd", "factors": factors("A", "B")})
        ok, detail = False, "2-factor BBD was accepted"
    except ValueError as exc:
        ok, detail = "at least 3 factors" in str(exc), str(exc)
    record("build.explicit_failure_bbd_2f", ok, detail)
    try:
        build_design({"design_type": "nope", "factors": factors("A", "B")})
        record("build.explicit_failure_unknown_type", False, "unknown type accepted")
    except ValueError as exc:
        record("build.explicit_failure_unknown_type", "design_type" in str(exc), str(exc))

    # CLI: --spec --out (csv) writes a contract §1 run table
    spec_path = TMP / "spec.json"
    out_csv = TMP / "run_table.csv"
    spec_path.write_text(json.dumps(specs["full_factorial"]), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "doestats" / "design_build.py"),
                        "--spec", str(spec_path), "--out", str(out_csv), "--seed", "42"],
                       capture_output=True, text=True, shell=False)
    header = out_csv.read_text(encoding="utf-8").splitlines()[0] if out_csv.exists() else ""
    record("build.cli_csv_run_table",
           r.returncode == 0 and header.startswith("run_id,design_point_id"),
           f"rc={r.returncode} header={header[:60]} {r.stderr[-120:]}")
    df_csv = pd.read_csv(out_csv)
    from doestats.design_detect import detect_design
    det_csv = detect_design(df_csv, ["A", "B", "C"])["design_type"]
    record("build.csv_roundtrip_detect", det_csv == "full_factorial", det_csv)

    # detector defect probe (frozen design_detect): p>=2 fraction generator recovery
    frac6 = build_design({"design_type": "fractional_factorial",
                          "factors": factors("A", "B", "C", "D", "E", "G"),
                          "resolution": 4}, seed=7)
    rt6 = frac6["properties"]["roundtrip"]
    record("build.frac_p2_selfcheck",
           frac6["properties"]["resolution"] == 4
           and len(frac6["properties"]["defining_relation"]) == 3
           and (rt6["match"] is True or rt6["detector_error"] is not None),
           f"res={frac6['properties']['resolution']} detected={rt6['detected_type']} "
           f"error={rt6['detector_error']}")
    if rt6["detector_error"]:
        print(f"        [detector defect] 2^(6-2): {rt6['detector_error']}")


# ---------------------------------------------------------------- next (P3-3)

NEXT_CTX = {
    "alpha": 0.05,
    "factors": [{"col": "A", "low": 180.0, "high": 220.0},
                {"col": "B", "low": 1.0, "high": 5.0},
                {"col": "C", "low": 10.0, "high": 30.0}],
    "constraints": [{"factor": "A", "type": "box", "min": 185.0, "max": 215.0,
                     "hard": True, "source": "ontology"},
                    {"factor": "B", "type": "box", "min": 0.0, "max": 10.0, "hard": True},
                    {"factor": "C", "type": "box", "min": 10.0, "max": 30.0, "hard": False}],
}


def next_profile(**kw):
    design = {"design_type": "fractional_factorial", "mode": "designed", "resolution": 4,
              "alias_chains": {"A": ["BCD"], "B": ["ACD"]}, "n_distinct_combos": 8,
              "n_runs": 8, "n_factor_cols": 3}
    design.update(kw)
    return {"design": design, "caveats": [], "roles": {}}


def next_effect_table(quad=None):
    if quad is None:
        return {"model_spec": {"main_effects": ["A", "B", "C"], "quadratic": [],
                               "interactions": ["A:B"]},
                "families": [{"response": "y", "mde": 1.5, "df_resid": 5,
                              "sigma_pure_error": 0.4,
                              "tests": [{"term": "A", "estimable": True, "p_value": 0.01,
                                         "q_value_bh": 0.02}]}]}
    return {"model_spec": {"main_effects": ["A", "B", "C"], "quadratic": ["A^2"],
                           "interactions": []},
            "families": [{"response": "y", "mde": 1.5, "df_resid": 5,
                          "sigma_pure_error": 0.4,
                          "tests": [{"term": "A^2", "estimable": True, "p_value": quad,
                                     "q_value_bh": quad}]}]}


NEXT_RECS = {"joint_setpoints": [{"id": "JS-1", "actionable": True, "confidence": "high",
                                  "factors": {"A": 200.0, "B": 3.0, "C": 20.0}}],
             "current_baseline": {"point": {"A": 190.0, "B": 2.0, "C": 15.0}},
             "operating_windows": []}


def case_next():
    print("[next] design_next rule selection + hard-constraint skipping (DS-11)")
    cases = {
        "fold_over": (next_profile(), next_effect_table(), NEXT_RECS),
        "augment_star": (next_profile(resolution=None, alias_chains={}),
                         next_effect_table(), NEXT_RECS),
        "augment_axial": (next_profile(resolution=None, alias_chains={}),
                          next_effect_table(quad=0.001), NEXT_RECS),
        "space_filling": (next_profile(design_type="observational", mode="observational",
                                       resolution=None, alias_chains={}),
                          next_effect_table(quad=0.001), NEXT_RECS),
    }
    for name, (prof, et, recs) in cases.items():
        out = dn.propose(prof, et, None, recs, NEXT_CTX, seed=7)
        acts = [a["action"] for a in out["actions"]]
        ok = out["recommended_action"] == name and name in acts \
            and out["primary_action_id"] == out["actions"][0]["id"]
        detail = f"rec={out['recommended_action']} actions={acts} " \
                 f"skipped={[s['action'] for s in out['skipped_actions']]}"
        record(f"next.{name}_rule", ok, detail)
        if not ok:
            continue
        act = out["actions"][0]
        record(f"next.{name}_fields",
               all(k in act for k in ("settings", "n_runs", "block_policy",
                                      "replicate_policy", "expected_information",
                                      "constraints_ok", "source_evidence"))
               and act["constraints_ok"] is True and act["n_runs"] >= 1,
               json.dumps({k: act[k] for k in ("n_runs", "block_policy",
                                               "replicate_policy")}, ensure_ascii=False))
        # every proposed setpoint inside every hard constraint
        pts = act.get("design_points")
        if isinstance(pts, list) and pts:
            bad = dn._violations(pts, dn._hard_constraints(NEXT_CTX))
            record(f"next.{name}_setpoints_in_constraints", not bad, str(bad))

    # confirm_replicate needs an explicit non-randomized declaration
    prof = next_profile(design_type="rsm_ccd", resolution=None, alias_chains={})
    prof["caveats"] = [{"code": "NON_RANDOMIZED", "message": "因子 A 与运行顺序 ρ=0.8",
                        "evidence": {"spearman_rho": 0.8}}]
    out = dn.propose(prof, next_effect_table(quad=0.001), None, NEXT_RECS, NEXT_CTX, seed=7)
    act = out["actions"][0]
    record("next.confirm_rule",
           out["recommended_action"] == "confirm_replicate" and act["n_runs"] == 3
           and out["randomization"]["non_randomized"] is True,
           f"rec={out['recommended_action']} n={act['n_runs']} "
           f"evidence={out['randomization']['evidence']}")
    record("next.confirm_replicate_policy",
           "3 independent replicates" in act["replicate_policy"], act["replicate_policy"])

    # a well-specified RSM design with curvature -> nothing to do
    out = dn.propose(next_profile(design_type="rsm_ccd", resolution=None, alias_chains={}),
                     next_effect_table(quad=0.001), None, NEXT_RECS, NEXT_CTX, seed=7)
    record("next.none_when_adequate",
           out["recommended_action"] == "none" and out["actions"][0]["n_runs"] == 0,
           out["recommended_action"])

    # hard constraint -> skip + disclosure (incumbent outside the limits)
    bad_recs = {"joint_setpoints": [{"id": "JS-x", "actionable": True, "confidence": "high",
                                     "factors": {"A": 400.0, "B": 3.0, "C": 20.0}}],
                "current_baseline": {"point": {"A": 400.0, "B": 3.0, "C": 20.0}},
                "operating_windows": []}
    prof = {"design": {"design_type": "rsm_ccd", "mode": "designed", "resolution": None,
                       "alias_chains": {}},
            "caveats": [{"code": "NON_RANDOMIZED", "message": "x", "evidence": {}}],
            "roles": {}}
    out = dn.propose(prof, next_effect_table(quad=0.001), None, bad_recs, NEXT_CTX, seed=7)
    skipped = [s for s in out["skipped_actions"] if s.get("action") == "confirm_replicate"]
    record("next.hard_constraint_skips",
           bool(skipped) and skipped[0]["constraints_ok"] is False
           and skipped[0]["skipped_reason"] == "hard_constraint_violation",
           json.dumps(out["skipped_actions"], ensure_ascii=False)[:200])

    # CLI writes conclusions/next_design.json
    run_dir = TMP / "next_run"
    for sub in ("00_input", "01_profile", "02_analysis", "conclusions"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    (run_dir / "00_input" / "analysis_context.json").write_text(
        json.dumps(NEXT_CTX), encoding="utf-8")
    (run_dir / "01_profile" / "data_profile.json").write_text(
        json.dumps(next_profile()), encoding="utf-8")
    (run_dir / "02_analysis" / "effect_table.json").write_text(
        json.dumps(next_effect_table()), encoding="utf-8")
    (run_dir / "conclusions" / "recommendations.json").write_text(
        json.dumps(NEXT_RECS), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "doestats" / "design_next.py"),
                        "--run-dir", str(run_dir), "--seed", "7"],
                       capture_output=True, text=True, shell=False)
    written = run_dir / "conclusions" / "next_design.json"
    got = json.loads(written.read_text(encoding="utf-8")) if written.exists() else {}
    record("next.cli_writes_artifact",
           r.returncode == 0 and got.get("recommended_action") == "fold_over",
           f"rc={r.returncode} rec={got.get('recommended_action')} {r.stderr[-120:]}")
    twice = (dn.propose(next_profile(), next_effect_table(), None, NEXT_RECS, NEXT_CTX, seed=7),
             dn.propose(next_profile(), next_effect_table(), None, NEXT_RECS, NEXT_CTX, seed=7))
    record("next.deterministic", stable(twice[0]) == stable(twice[1]),
           "two proposals differ")


# ---------------------------------------------------------------- screen (P3-1)

def _confounder_frame(seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for _rep in range(2):
        for a, b, c in itertools.product([-1.0, 1.0], repeat=3):
            ambient = 4.0 * a + rng.normal(0, 1.0)          # driven by the design
            y = 50.0 + 3.0 * a + 2.0 * b + 0.5 * a * b + rng.normal(0, 0.4)
            rows.append({"A": a, "B": b, "C": c, "ambient": ambient, "yield_y": y,
                         "batch_const": 1.0, "A_dup": 2.0 * a,
                         "humidity": rng.normal(60, 5)})
    return pd.DataFrame(rows)


def case_screen():
    print("[screen] association_screen confounder + kinds (DS-10 / G8)")
    df = _confounder_frame()
    spec = [{"col": "A", "type": "numeric"}, {"col": "B", "type": "numeric"},
            {"col": "C", "type": "numeric"},
            {"col": "humidity", "type": "numeric", "is_covariate": True}]
    factor_info = effects_anova.build_factor_info(df, spec)
    ctx = {"alpha": 0.05, "index_cols": [], "responses": [{"col": "yield_y"}],
           "factors": [{"col": "A"}, {"col": "B"}, {"col": "C"}],
           "covariates": ["humidity"],
           "_effect_table": {"model_spec": {"term_status": {
               "C": {"estimated": False, "reason_code": "aliased"}}}}}
    profile = {"quality": {"constant_cols": ["batch_const"]}, "caveats": [], "roles": {}}
    res = screen(df, factor_info, ctx, profile, ["yield_y"])

    record("screen.causal_claim_none", res["causal_claim"] == "none", res["causal_claim"])
    record("screen.design_adjusted_flag", res["design_adjusted"] is True, "flag false")
    kinds = sorted({p["kind"] for p in res["pairs"]})
    record("screen.kinds_present",
           kinds == ["designed_factor", "held_constant", "non_factor", "unmodeled"],
           str(kinds))
    verdicts = sorted({p["verdict"] for p in res["pairs"]})
    record("screen.verdicts_present",
           verdicts == ["design_adjusted", "held_constant", "unmodeled"], str(verdicts))
    record("screen.no_window_keys",
           "operating_windows" not in json.dumps(res, ensure_ascii=False)
           and "window_role" not in json.dumps(res, ensure_ascii=False)
           and "actionable" not in json.dumps(res, ensure_ascii=False), "window-like key")

    by = {p["factor"]: p for p in res["pairs"]}
    amb = by.get("ambient", {})
    record("screen.confounder_marginal_strong",
           amb.get("marginal") and abs(amb["marginal"]["r"]) >= 0.3
           and amb["marginal"]["p"] < 0.05 and amb["verdict"] == "unmodeled",
           json.dumps(amb.get("marginal"), ensure_ascii=False))
    record("screen.confounder_adjusted_null",
           amb.get("design_adjusted") and amb["design_adjusted"]["p"] is not None
           and amb["design_adjusted"]["p"] >= 0.05 and amb.get("confounded") is True
           and "混杂" in amb.get("note", ""),
           json.dumps(amb.get("design_adjusted"), ensure_ascii=False))
    record("screen.marginal_method_core_stats",
           all((p["marginal"] or {}).get("method") in
               ("core_stats.pearson", "not_computable_constant", None)
               for p in res["pairs"]),
           str(sorted({(p["marginal"] or {}).get("method") for p in res["pairs"]})))
    record("screen.design_factor_adjusted",
           by["A"]["verdict"] == "design_adjusted"
           and by["A"]["design_adjusted"]["strata"], str(by["A"]["design_adjusted"]))
    record("screen.held_constant_constant_col",
           by["batch_const"]["kind"] == "held_constant"
           and by["batch_const"]["marginal"]["method"] == "not_computable_constant",
           json.dumps(by["batch_const"], ensure_ascii=False)[:160])
    record("screen.held_constant_collinear",
           by["A_dup"]["kind"] == "held_constant" and "共线" in by["A_dup"]["note"],
           by["A_dup"]["note"][:120])
    record("screen.non_factor_covariate",
           by["humidity"]["kind"] == "non_factor"
           and by["humidity"]["verdict"] == "design_adjusted",
           f"{by['humidity']['kind']}/{by['humidity']['verdict']}")
    record("screen.aliased_term_status",
           by["C"]["kind"] == "designed_factor"
           and by["C"].get("model_term_status", {}).get("reason_code") == "aliased",
           json.dumps(by["C"].get("model_term_status"), ensure_ascii=False))

    # a saturated 2^(3-1) design has df=0 for the adjusted model -> verdict "marginal"
    rows = [{k: v for k, v in zip(("A", "B", "C"), c)} for c in
            [(-1, -1, -1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]]
    for i, r in enumerate(rows):
        r["y"] = 10 + 2 * r["A"] + 3 * r["B"] + r["C"]
        r["extra"] = float(i)
    df2 = pd.DataFrame(rows)
    fi2 = effects_anova.build_factor_info(
        df2, [{"col": c, "type": "numeric"} for c in ("A", "B", "C")])
    res2 = screen(df2, fi2, {"alpha": 0.05, "index_cols": [],
                             "responses": [{"col": "y"}],
                             "factors": [{"col": c} for c in ("A", "B", "C")]},
                  {"roles": {}}, ["y"])
    got = {p["factor"]: p["verdict"] for p in res2["pairs"]}
    record("screen.marginal_verdict_reachable",
           got == {"A": "marginal", "B": "marginal", "C": "marginal", "extra": "unmodeled"},
           json.dumps(got, ensure_ascii=False))

    # CLI end-to-end: writes 02_analysis/association_screen.json for a run dir
    run_dir = TMP / "screen_run"
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    df.to_csv(run_dir / "00_input" / "run_table.csv", index=False)
    (run_dir / "00_input" / "analysis_context.json").write_text(json.dumps(
        {"data_path": "00_input/run_table.csv", "alpha": 0.05,
         "factors": [{"col": c, "type": "numeric"} for c in ("A", "B", "C")],
         "responses": [{"col": "yield_y"}], "covariates": ["humidity"],
         "index_cols": []}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "doestats" / "association_screen.py"),
                        "--run-dir", str(run_dir)], capture_output=True, text=True,
                       shell=False)
    written = run_dir / "02_analysis" / "association_screen.json"
    payload = json.loads(written.read_text(encoding="utf-8")) if written.is_file() else {}
    record("screen.cli_writes_artifact",
           r.returncode == 0 and payload.get("causal_claim") == "none"
           and payload.get("n_pairs", 0) >= 4,
           f"rc={r.returncode} n_pairs={payload.get('n_pairs')} {r.stderr[-150:]}")


# ---------------------------------------------------------------- guidance (P3-5)

def _guidance_run():
    run_dir = TMP / "guide_run"
    shutil.rmtree(run_dir, ignore_errors=True)
    for sub in ("00_input", "01_ontology", "01_profile", "02_analysis", "conclusions"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    doe = {
        "contract_version": "1.0", "experiment_id": "doe-exp-1",
        "objective": "提高厚度均匀性",
        "factors": [
            {"name": "zone1_temp", "col": "zone1_temp", "type": "numeric", "unit": "C",
             "low": 180, "high": 220,
             "platform_ref": {"recipe_param": "zone1_temp", "node_id": "dw-1",
                              "plc_tag": "PLC.T1", "unit_conversion": 1.0,
                              "rounding": 0.5, "hard_limits": {"min": 185, "max": 215}}},
            {"name": "flow", "col": "flow", "type": "numeric", "unit": "L/min",
             "low": 1, "high": 5,
             "platform_ref": {"recipe_param": "flow", "node_id": "dw-2", "plc_tag": "PLC.F",
                              "unit_conversion": 60.0,
                              "rounding": {"mode": "decimals", "value": 1},
                              "hard_limits": {"min": 60, "max": 300}}},
            {"name": "gap", "col": "gap", "type": "numeric", "unit": "um",
             "low": 10, "high": 30}],
        "responses": [
            {"name": "thickness", "col": "thickness", "unit": "um", "goal": "target",
             "target": 50, "platform_metric_ref": {"node_id": "dn-1",
                                                   "aggregation": "steady_mean"}},
            {"name": "roughness", "col": "roughness", "unit": "nm", "goal": "minimize"}],
        "constraints": [{"factor": "zone1_temp", "type": "box", "min": 185, "max": 215,
                         "hard": True, "source": "ontology"}],
        "optimization": {"campaign_id": "CAMP-7", "round": 2},
    }
    (run_dir / "00_input" / "doe_context.json").write_text(
        json.dumps(doe, ensure_ascii=False), encoding="utf-8")
    ctx = {"data_path": "00_input/run_table.csv", "factors": doe["factors"],
           "responses": doe["responses"], "constraints": doe["constraints"],
           "current_setpoint": {"zone1_temp": 195.0, "flow": 2.0, "gap": 20.0},
           "parent_run_id": "run-000",
           "ontology": {"profile": "doe", "mode": "auto", "scene_key": "bopet",
                        "version": "v3"}}
    (run_dir / "00_input" / "analysis_context.json").write_text(
        json.dumps(ctx, ensure_ascii=False), encoding="utf-8")
    (run_dir / "01_ontology" / "ontology_brief.json").write_text(json.dumps(
        {"contract_version": "1.0", "profile": "doe", "scene_key": "bopet",
         "ontology_version": "v3", "ontology_sha256": "abc123",
         "provenance": {"build_mode": "reused"}}, ensure_ascii=False), encoding="utf-8")
    (run_dir / "conclusions" / "recommendations.json").write_text(json.dumps(
        {"contract_version": "1.1",
         "operating_windows": [{"id": "OW-001", "factor": "zone1_temp",
                                "response": "thickness", "range": [190.0, 210.0],
                                "window_role": "marginal_diagnostic", "actionable": True}],
         "setpoints": [{"factor": "MULTI", "value": 0.0, "confidence": "high",
                        "expected_response": {"raw": {"zone1_temp": 202.4, "flow": 3.05,
                                                     "gap": 22.0}, "D": 0.8}}],
         "current_baseline": {"point": {"zone1_temp": 195.0, "flow": 2.0, "gap": 20.0}},
         "response_specs": {"thickness": {"lsl": 48, "usl": 52, "target": 50,
                                          "current": 49.1}}},
        ensure_ascii=False), encoding="utf-8")
    (run_dir / "conclusions" / "next_design.json").write_text(json.dumps(
        {"recommended_action": "augment_star", "primary_action_id": "ND-02",
         "actions": [{"id": "ND-02", "action": "augment_star", "n_runs": 9}]},
        ensure_ascii=False), encoding="utf-8")
    return run_dir


def case_guidance():
    print("[guidance] optimization_guidance platform handoff (OD-11 / XR-03)")
    run_dir = _guidance_run()
    from optimization_guidance import build
    out = build(run_dir)
    patch = {p["factor"]: p for p in out["recipe_patch"]}
    record("guidance.deterministic", stable(out) == stable(build(run_dir)),
           "two builds differ (RG-03)")
    record("guidance.contract_keys",
           all(k in out for k in ("contract_version", "schema_version", "run_id",
                                  "experiment_id", "ontology_basis", "objective",
                                  "recipe_patch", "node_setpoints", "constraints",
                                  "next_design", "lineage", "provenance")),
           str(sorted(out)))
    record("guidance.platform_ref_missing_removed",
           "gap" not in patch
           and any(m["factor"] == "gap" and m["reason"] == "platform_ref_missing"
                   for m in out["platform_ref_missing"]),
           json.dumps(out["platform_ref_missing"], ensure_ascii=False)[:200])
    record("guidance.unit_conversion_applied",
           patch["flow"]["to"] == 183.0 and patch["flow"]["value_analysis_units"] == 3.05,
           f"to={patch['flow']['to']} raw={patch['flow']['value_analysis_units']}")
    record("guidance.rounding_applied",
           patch["zone1_temp"]["to"] == 202.5 and patch["flow"]["to"] == 183.0,
           f"zone1_temp.to={patch['zone1_temp']['to']}")
    record("guidance.within_limits",
           patch["zone1_temp"]["within_limits"] is True
           and patch["flow"]["within_limits"] is True
           and patch["zone1_temp"]["hard_limits"] == {"min": 185, "max": 215},
           json.dumps({f: patch[f]["within_limits"] for f in patch}))
    record("guidance.from_value_converted",
           patch["flow"]["from"] == 120.0, str(patch["flow"]["from"]))
    record("guidance.node_setpoints",
           len(out["node_setpoints"]) == 1
           and out["node_setpoints"][0]["node_id"] == "dn-1"
           and out["node_setpoints"][0]["aggregation"] == "steady_mean"
           and any(m["kind"] == "node_setpoint" and m["metric"] == "roughness"
                   for m in out["platform_ref_missing"]),
           json.dumps(out["node_setpoints"], ensure_ascii=False))
    record("guidance.ontology_basis",
           out["ontology_basis"]["version"] == "v3"
           and out["ontology_basis"]["sha256"] == "abc123"
           and out["ontology_basis"]["reused"] is True,
           json.dumps(out["ontology_basis"], ensure_ascii=False))
    record("guidance.lineage_and_next_design",
           out["lineage"]["campaign_id"] == "CAMP-7" and out["lineage"]["round"] == 2
           and out["lineage"]["parent_run_id"] == "run-000"
           and out["next_design"]["n_runs"] == 9
           and out["next_design"]["ref"] == "conclusions/next_design.json",
           json.dumps({"lineage": out["lineage"], "next": out["next_design"]},
                      ensure_ascii=False))
    record("guidance.inputs_hashed",
           all(len(i["sha256"]) == 64 for i in out["provenance"]["inputs"])
           and len(out["provenance"]["inputs"]) >= 5,
           str([i["path"] for i in out["provenance"]["inputs"]]))

    # CLI writes conclusions/optimization_guidance.json
    r = subprocess.run([sys.executable, str(SCRIPTS / "optimization_guidance.py"),
                        "--run-dir", str(run_dir)], capture_output=True, text=True,
                       shell=False)
    written = run_dir / "conclusions" / "optimization_guidance.json"
    record("guidance.cli_writes_artifact",
           r.returncode == 0 and written.is_file()
           and json.loads(written.read_text(encoding="utf-8"))["run_id"] == run_dir.name,
           f"rc={r.returncode} {r.stderr[-150:]}")

    # no actionable source at all -> empty patch, disclosed, never fabricated
    (run_dir / "conclusions" / "recommendations.json").write_text(
        json.dumps({"contract_version": "1.0", "operating_windows": [],
                    "setpoints": [], "current_baseline": {"point": {}},
                    "response_specs": {}}), encoding="utf-8")
    empty = build(run_dir)
    record("guidance.no_fabricated_values",
           empty["recipe_patch"] == []
           and empty["provenance"]["recommended_point_source"] is None
           and any("不编造" in n for n in empty["provenance"]["notes"]),
           json.dumps(empty["provenance"]["notes"], ensure_ascii=False)[:200])


# ---------------------------------------------------------------- loop (P3-4)

def case_loop():
    print("[loop] windows_seed gating + rejected_prior (contract §10)")
    from optcore import windows_seed as wins
    domain = {"temp": {"lo": 0.0, "hi": 100.0}, "conc": {"lo": 0.0, "hi": 10.0}}
    legacy = {
        "contract_version": "1.0",
        "operating_windows": [
            {"id": "OW-001", "priority": 1, "factor": "temp", "range": [40, 60]},
            {"id": "OW-002", "priority": 2, "factor": "conc", "range": [2, 4]}],
        "current_baseline": {"point": {"temp": 45.0, "conc": 2.5}},
        "setpoints": [{"factor": "MULTI", "value": 0.0,
                       "expected_response": {"raw": {"temp": 52.0, "conc": 3.0},
                                             "D": 0.83}, "confidence": "medium"}],
    }
    seeds = wins.seed_points(legacy, domain)
    record("loop.legacy_three_class_seeds",
           sorted(s["kind"] for s in seeds) == ["W2_optimum", "current_baseline",
                                                "window_center"]
           and isinstance(seeds, list) and seeds.rejected_prior == [],
           str([(s["kind"], s["setpoints"]) for s in seeds]))

    v11 = {
        "contract_version": "1.1",
        "operating_windows": [
            {"id": "OW-001", "priority": 1, "factor": "temp", "range": [40, 60],
             "window_role": "marginal_diagnostic", "actionable": True},
            {"id": "OW-002", "priority": 2, "factor": "conc", "range": [2, 4],
             "window_role": "marginal_diagnostic", "actionable": False,
             "actionable_blockers": ["unit_missing"]},
            {"id": "OW-003", "priority": 3, "factor": "temp", "range": [30, 70],
             "window_role": "diagnostic_only", "actionable": True}],
        "current_baseline": {"point": {"temp": 45.0, "conc": 2.5}},
        "joint_setpoints": [
            {"id": "JS-001", "actionable": True, "confidence": "high",
             "evidence_level": "L3", "feasible": True, "hard_constraint_violations": 0,
             "desirability": 0.91, "factors": {"temp": 55.0, "conc": 3.5}},
            {"id": "JS-002", "actionable": True, "confidence": "low",
             "evidence_level": "L3", "factors": {"temp": 10.0, "conc": 9.0}},
            {"id": "JS-003", "actionable": True, "confidence": "high",
             "evidence_level": "L6", "factors": {"temp": 90.0, "conc": 9.0}},
            {"id": "JS-004", "actionable": False, "confidence": "high",
             "blockers": ["extrapolation"], "factors": {"temp": 20.0, "conc": 1.0}},
            {"id": "JS-005", "actionable": True, "confidence": "high",
             "evidence_level": "L2", "feasible": False,
             "hard_constraint_violations": 2, "factors": {"temp": 5.0, "conc": 5.0}}],
    }
    plan = wins.seed_plan(v11, domain)
    kinds = sorted(s["kind"] for s in plan["seeds"])
    rej = {r.get("setpoint_id") or r.get("window_id"): r["reason"]
           for r in plan["rejected_prior"]}
    record("loop.v11_gating",
           kinds == ["current_baseline", "joint_setpoint", "window_center"]
           and not any(s["setpoints"].get("temp") == 10.0 for s in plan["seeds"]),
           json.dumps([(s["kind"], s["source"], s["setpoints"]) for s in plan["seeds"]]))
    record("loop.actionable_window_only",
           rej.get("OW-002") == "actionable=false"
           and any(r.get("window_id") == "OW-002" and r.get("detail") == {
               "blockers": ["unit_missing"]} for r in plan["rejected_prior"])
           and all(s["setpoints"]["conc"] != 3.0
                   for s in plan["seeds"] if s["kind"] == "window_center"),
           json.dumps(rej, ensure_ascii=False))
    record("loop.role_filtered",
           "OW-003" in rej and "not marginal_diagnostic" in rej["OW-003"], str(rej))
    record("loop.setpoint_rejections_traced",
           rej.get("JS-002", "").startswith("confidence=low")
           and "above the L4 threshold" in rej.get("JS-003", "")
           and rej.get("JS-004") == "actionable!=true"
           and "feasible=false" == rej.get("JS-005"),
           json.dumps(rej, ensure_ascii=False))
    record("loop.joint_setpoint_seed_used",
           any(s["kind"] == "joint_setpoint" and s["setpoints"]["temp"] == 55.0
               and s["prior_D"] == 0.91 for s in plan["seeds"]),
           json.dumps([s for s in plan["seeds"] if s["kind"] == "joint_setpoint"]))
    record("loop.prior_valid_uses_joint_setpoint",
           wins.prior_valid({"joint_setpoints": v11["joint_setpoints"]}) is True
           and wins.prior_valid({"operating_windows": [
               {"id": "OW-x", "factor": "temp", "range": [1, 2], "actionable": False}]}) is False,
           "prior_valid gating")
    # clipping still reported for the optimizer guardrail log
    clipped = wins.seed_points({"current_baseline": {"point": {"temp": 500.0, "conc": 2.5}}},
                               domain)
    record("loop.clip_reported",
           clipped and clipped[0]["moved"] == ["temp"]
           and clipped[0]["setpoints"]["temp"] == 100.0,
           json.dumps([dict(s) for s in clipped]))


# ---------------------------------------------------------------- schema

def case_schema():
    print("[schema] the four new schemas validate real payloads (validate.mjs)")
    payloads = {
        "design_build.schema.json": build_design(
            {"design_type": "rsm_ccd", "factors": factors("A", "B", "C"), "n_center": 3},
            seed=42),
        "next_design.schema.json": dn.propose(next_profile(), next_effect_table(), None,
                                              NEXT_RECS, NEXT_CTX, seed=7),
    }
    df = _confounder_frame()
    fi = effects_anova.build_factor_info(
        df, [{"col": c, "type": "numeric"} for c in ("A", "B", "C")])
    payloads["association_screen.schema.json"] = screen(
        df, fi, {"alpha": 0.05, "index_cols": [], "responses": [{"col": "yield_y"}],
                 "factors": [{"col": c} for c in ("A", "B", "C")]}, {"roles": {}},
        ["yield_y"])
    from optimization_guidance import build as guidance_build
    payloads["optimization_guidance.schema.json"] = guidance_build(_guidance_run())

    for schema_name, payload in sorted(payloads.items()):
        schema_path = SCHEMAS / schema_name
        data_path = TMP / (schema_name.replace(".schema.json", "") + ".json")
        text = json.dumps(payload, ensure_ascii=False, default=str)
        data_path.write_text(text, encoding="utf-8")
        # strict JSON: artifacts must never carry NaN/Infinity (AR-03 discipline)
        try:
            json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(
                ValueError(f"non-finite constant {c} in artifact")))
            strict = True
        except ValueError as exc:
            strict = False
            print(f"        [strict-json] {schema_name}: {exc}")
        record(f"schema.{schema_name}.strict_json", strict, "NaN/Infinity in payload")
        r = subprocess.run(["node", str(VALIDATE), str(schema_path), str(data_path)],
                           capture_output=True, text=True, shell=False)
        report = {}
        try:
            report = json.loads(r.stdout or "{}")
        except ValueError:
            report = {"raw": r.stdout[-200:], "stderr": r.stderr[-200:]}
        record(f"schema.{schema_name}",
               r.returncode == 0 and report.get("valid") is not False,
               f"rc={r.returncode} {json.dumps(report, ensure_ascii=False)[:300]}")


CASES = {"build": case_build, "next": case_next, "screen": case_screen,
         "guidance": case_guidance, "loop": case_loop, "schema": case_schema}


def main():
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = list(CASES) if selector in ("all",) or selector not in CASES else [selector]
    try:
        for name in todo:
            CASES[name]()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(TMP, ignore_errors=True)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[PHASE3] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
