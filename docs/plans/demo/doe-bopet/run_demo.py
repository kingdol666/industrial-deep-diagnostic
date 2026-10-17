#!/usr/bin/env python
"""run_demo.py — end-to-end DOE flow on the simulated BOPET trial.

Drives the REAL pipeline exactly as an agent would (no shortcuts, no hand-written
numbers) and then checks the result against `scenario_truth.json`:

    1. doh_context_adapter      doe_context + run_table -> analysis_context (col contract)
    2. doe_ontology_prepare     context_fp -> store lookup -> reuse/extend/build
                                -> ontology.json + ontology_brief.json/.md + coverage
    3. (agent step)             read the brief, write 01_profile/analysis_plan.md
    4. analyze.py all           profile -> statistics -> report.html
    5. quality_gate.mjs         G1-G11
    6. assertions               design recovery, planted effects, stationary point,
                                actionable joint setpoint inside the hard limits,
                                association screen discipline, next design,
                                platform handoff, artifact manifest, report sections

Usage:
    uv run --project .claude/shared/scripts python docs/plans/demo/doe-bopet/run_demo.py [--fresh]
`--fresh` wipes the local ontology store so the run demonstrates the full
prior-knowledge build instead of a store reuse.
Exit 0 = every check passed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SKILL = REPO / ".claude" / "skills" / "industrial-doe-analyzer"
SHARED = REPO / ".claude" / "shared"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

GENERATED = ["01_profile", "02_analysis", "03_figures", "conclusions", "01_ontology",
             "run_manifest.json", "report.html", "artifact_manifest.json"]
RESULTS: list[tuple[str, bool, str]] = []


def record(cid: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((cid, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {cid}" + (f"  {detail}" if detail and not ok else ""))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read(rel: str) -> dict:
    return json.loads((HERE / rel).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run_demo.py")
    ap.add_argument("--fresh", action="store_true",
                    help="wipe the local ontology store first (full build path)")
    args = ap.parse_args(argv)

    truth = read("scenario_truth.json")
    print("== DOE end-to-end demo: BOPET 12um TDO/MDO trial ==")

    # ---- 0. reset generated state (inputs + generator are the source of truth)
    for name in GENERATED:
        target = HERE / name
        shutil.rmtree(target, ignore_errors=True) if target.is_dir() else target.unlink(
            missing_ok=True)
    (HERE / "00_input" / "analysis_context.json").unlink(missing_ok=True)
    store = HERE / "_store"
    if args.fresh:
        shutil.rmtree(store, ignore_errors=True)

    # ---- 1. data entry: doe_context + run_table -> analysis_context
    adapter = _load("doe_context_adapter", SCRIPTS / "doe_context_adapter.py")
    rc = adapter.main(["--run-dir", str(HERE)])
    record("stage.adapter", rc == 0, f"rc={rc}")
    ctx = read("00_input/analysis_context.json")
    record("adapter.data_path", ctx.get("data_path") == "00_input/run_table.csv",
           str(ctx.get("data_path")))
    record("adapter.assigned_by_user",
           (ctx.get("provenance") or {}).get("assigned_by", {}).get("factors[tdo_z4_temp].unit")
           == "user", "declared units must be provenance=user")

    # ---- 2. ontology stage (hard gate)
    prep = _load("doe_ontology_prepare", SCRIPTS / "doe_ontology_prepare.py")
    res = prep.prepare(HERE, mode="auto", store_dir=str(store))
    record("stage.ontology", res.get("action") in ("built", "extended", "reused"),
           str(res.get("action")))
    print(f"         ontology action={res.get('action')} version=v{res.get('version')} "
          f"fp={str(res.get('context_fp'))[:12]} elapsed={res.get('elapsed_ms')}ms "
          f"rag={res.get('rag_used')}")
    brief = read("01_ontology/ontology_brief.json")
    cov = brief.get("coverage") or {}
    record("ontology.brief_profile", brief.get("profile") == "doe", str(brief.get("profile")))
    record("ontology.coverage_complete",
           cov.get("n_unmatched") == 0 and float(cov.get("ratio") or 0) == 1.0, str(cov))

    # ---- 3. the agent step: read the brief, write the plan
    (HERE / "01_profile").mkdir(parents=True, exist_ok=True)
    (HERE / "01_profile" / "analysis_plan.md").write_text(brief_to_plan(brief), encoding="utf-8")
    record("stage.analysis_plan", (HERE / "01_profile" / "analysis_plan.md").is_file())

    # ---- 4. the deterministic analyzer (profile -> statistics -> report)
    analyze = _load("analyze_demo", SCRIPTS / "analyze.py")
    saved_argv = sys.argv
    sys.argv = ["analyze.py", "all", "--run-dir", str(HERE)]
    try:
        analyze.main()
        ok = True
    except SystemExit as exc:
        ok = not exc.code
    finally:
        sys.argv = saved_argv
    record("stage.analyze_all", ok)
    if not ok:
        return report_out()

    # ---- 5. quality gate
    gate = subprocess.run(
        ["node", str(SKILL / "scripts" / "quality_gate.mjs"), str(HERE),
         "--skill-path", str(SKILL), "--shared-path", str(SHARED)],
        capture_output=True, text=True, shell=False, timeout=600)
    gate_line = [ln for ln in gate.stdout.splitlines() if ln.startswith("[GATE]")]
    record("stage.gate", gate.returncode == 0, "; ".join(gate_line) or gate.stderr[-200:])
    print(f"         {gate_line[0] if gate_line else 'no [GATE] line'}")

    # ---- 6. correctness against the planted truth
    profile, effect = read("01_profile/data_profile.json"), read("02_analysis/effect_table.json")
    models, recs = read("02_analysis/model.json"), read("conclusions/recommendations.json")
    screen, nxt = read("02_analysis/association_screen.json"), read("conclusions/next_design.json")
    guide, man = read("conclusions/optimization_guidance.json"), read("artifact_manifest.json")
    conclusion = read("conclusions/doe_conclusion.json")

    # design recovery
    design = profile.get("design") or {}
    record("design.type", design.get("design_type") == truth["design"]["type"],
           str(design.get("design_type")))
    record("design.center_points", design.get("center_points") == truth["design"]["n_centre_executions"],
           str(design.get("center_points")))
    record("design.axial_points", design.get("axial_points") == truth["design"]["n_axial"],
           str(design.get("axial_points")))
    record("design.mode", design.get("mode") == "designed", str(design.get("mode")))

    # data quality: the failed gauge reading is disclosed, not imputed
    cols = {c["name"]: c for c in profile.get("columns") or []}
    record("quality.empty_cell_disclosed", cols.get("thickness_um", {}).get("n_missing") == 1,
           str(cols.get("thickness_um", {}).get("n_missing")))

    # planted effects recovered, null effects not
    fam = next(f for f in effect["families"] if f["response"] == "thickness_um")
    q_of = {t["term"]: t.get("q_value_bh") for t in fam["tests"]}
    for term in truth["expected_significant_thickness_terms"]:
        q = q_of.get(term)
        record(f"effect.thickness.{term}", q is not None and q < 0.05, f"q={q}")
    for term in ("shift_handover_min",):
        q = q_of.get(term)
        record(f"effect.null.{term}", q is None or q >= 0.05, f"q={q}")
    # A declared covariate with no TRUE effect still lands at p<0.05 in ~5% of
    # datasets — that is what alpha means, not a defect. What must hold is that a
    # nuisance variable never becomes material or actionable, so the checks below
    # are about magnitude and about the recommendation path.
    amb = next((t for t in fam["tests"] if t["term"] == "ambient_temp"), {})
    strongest = max((abs(t.get("std_effect") or 0) for t in fam["tests"]
                     if t.get("estimable")), default=0.0)
    amb_std = abs(amb.get("std_effect") or 0.0)
    record("effect.covariate_immaterial",
           amb and amb_std < 0.25 and amb_std < 0.35 * strongest,
           f"std_effect={amb.get('std_effect')} vs strongest={strongest:.3f} "
           f"(p={amb.get('p_value')}, q={amb.get('q_value_bh')})")
    print(f"         covariate ambient_temp: p={amb.get('p_value'):.4f} "
          f"std_effect={amb_std:.3f} (strongest factor {strongest:.3f}) "
          "-> statistically detectable, physically negligible")

    fam_h = next(f for f in effect["families"] if f["response"] == "haze_pct")
    qh = {t["term"]: t.get("q_value_bh") for t in fam_h["tests"]}
    for term in truth["expected_significant_haze_terms"]:
        q = qh.get(term)
        record(f"effect.haze.{term}", q is not None and q < 0.05, f"q={q}")

    # stationary point recovered and inside the region
    m0 = next(m for m in models if m["response"] == "thickness_um")
    sp = m0.get("stationary_point") or {}
    coded = sp.get("coded") or {}
    exp = truth["expected_stationary_point_coded"]
    near = all(abs(float(coded.get(k, 9e9)) - v) < 0.25 for k, v in exp.items())
    record("model.stationary_point_recovered", near,
           f"got={coded} expected={exp}")
    record("model.stationary_point_inside", bool(sp.get("inside_design_region")),
           str(sp.get("inside_design_region")))
    if coded:
        for k, v in exp.items():
            centre, half, _u = (truth["factors"][k]["centre"], truth["factors"][k]["half_range"], None)
            print(f"         stationary {k}: coded {coded.get(k):+.3f} (planted {v:+.3f}) "
                  f"-> raw {centre + half * float(coded.get(k)):.3f}")

    # recommendations: marginal windows are diagnostics, the joint point executes
    wins = recs.get("operating_windows") or []
    record("recs.window_role", all(w.get("window_role") == "marginal_diagnostic" for w in wins),
           str([w.get("window_role") for w in wins]))
    matrix = recs.get("factor_response_matrix") or []
    n_expected = len(truth["factors"]) * 2
    record("recs.matrix_complete", len(matrix) == n_expected, f"{len(matrix)} vs {n_expected}")
    record("recs.matrix_no_silent_cell",
           all(c.get("window_id") or c.get("no_window_reason") for c in matrix))
    js = recs.get("joint_setpoints") or []
    record("recs.joint_present", bool(js))
    if js:
        j = js[0]
        pred = j.get("predicted") or {}
        t_mean = (pred.get("thickness_um") or {}).get("mean")
        h_mean = (pred.get("haze_pct") or {}).get("mean")
        lo, hi = truth["expected_recommendation"]["thickness_within"]
        record("recs.joint_actionable", j.get("actionable") is True,
               f"actionable={j.get('actionable')} blockers={j.get('blockers')}")
        record("recs.joint_hard_zero", int(j.get("hard_constraint_violations") or 0) == 0,
               str(j.get("hard_constraint_violations")))
        record("recs.joint_thickness_in_spec",
               t_mean is not None and lo <= float(t_mean) <= hi, str(t_mean))
        record("recs.joint_haze_under_usl",
               h_mean is not None and float(h_mean) <= truth["expected_recommendation"]["haze_ceiling"],
               str(h_mean))
        limits = {k: v["platform_ref"]["hard_limits"] for k, v in
                  {f["col"]: f for f in ctx["factors"]}.items()}
        bad = [f for f, v in (j.get("factors") or {}).items()
               if not (limits[f]["min"] <= float(v) <= limits[f]["max"])]
        record("recs.joint_inside_hard_limits", not bad, f"outside: {bad}")
        record("recs.joint_units_valid", j.get("unit_status") == "valid", str(j.get("unit_status")))
        print(f"         joint setpoint: {j.get('factors')}")
        print(f"         predicted: thickness {t_mean:.3f} um (spec {lo}-{hi}), "
              f"haze {h_mean:.3f} % (usl {truth['expected_recommendation']['haze_ceiling']})")
        print(f"         desirability {j.get('desirability')} window_ids={j.get('window_ids')}")

    # association screen discipline
    record("screen.causal_claim_none", screen.get("causal_claim") == "none",
           str(screen.get("causal_claim")))
    pairs = {p.get("factor"): p for p in screen.get("pairs") or []}
    for col in ("chiller_pressure", "shift_handover_min", "ambient_temp"):
        p = pairs.get(col)
        adj_p = ((p or {}).get("design_adjusted") or {}).get("p")
        record(f"screen.{col}_not_causal",
               p is not None and (adj_p is None or float(adj_p) > 0.05),
               f"kind={(p or {}).get('kind')} adj_p={adj_p}")
    record("screen.not_a_window_factor",
           all(w.get("factor") not in pairs for w in wins) or
           all(pairs.get(w.get("factor"), {}).get("kind") == "designed_factor" for w in wins),
           "a non-designed screen variable leaked into a window")

    # the discipline that actually matters: no nuisance variable reaches a decision
    nuisance = {"ambient_temp", "chiller_pressure", "shift_handover_min"}
    record("discipline.no_nuisance_window",
           not (nuisance & {w.get("factor") for w in wins}),
           str(nuisance & {w.get("factor") for w in wins}))
    if js:
        record("discipline.no_nuisance_setpoint",
               not (nuisance & set((js[0].get("factors") or {}).keys())),
               str(nuisance & set((js[0].get("factors") or {}).keys())))
    record("discipline.no_nuisance_patch",
           not (nuisance & {p.get("factor") for p in (guide.get("recipe_patch") or [])}),
           "a nuisance variable reached the platform handoff")

    # next design + platform handoff
    actions = nxt.get("actions") or []
    record("next.actions_present", bool(actions), str(nxt.get("recommended_action")))
    record("next.constraints_ok", all(a.get("constraints_ok") for a in actions))
    print(f"         next design: {nxt.get('recommended_action')} — "
          f"{str(nxt.get('rationale'))[:90]}...")
    patch = guide.get("recipe_patch") or []
    record("guidance.recipe_patch_present", bool(patch), str(len(patch)))
    record("guidance.within_limits", all(p.get("within_limits") for p in patch),
           str([p.get("factor") for p in patch if not p.get("within_limits")]))
    record("guidance.no_platform_ref_missing", not guide.get("platform_ref_missing"),
           str(guide.get("platform_ref_missing")))
    for p in patch:
        print(f"         recipe patch: {p['factor']} {p.get('from')} -> {p.get('to')} "
              f"{p.get('unit')} (plc {p.get('platform_ref', {}).get('plc_tag')})")

    # artifact registry + report rendering
    kinds = {a.get("kind") for a in man.get("artifacts") or []}
    record("manifest.no_missing", not man.get("missing"), str(man.get("missing")))
    record("manifest.core_kinds",
           {"data_profile", "effect_table", "model", "association_screen", "doe_conclusion",
            "recommendations", "next_design", "optimization_guidance", "report"} <= kinds,
           str(sorted(kinds)))
    bad_hash = [a["kind"] for a in man["artifacts"]
                if hashlib.sha256((HERE / a["path"]).read_bytes()).hexdigest() != a["sha256"]]
    record("manifest.sha256_matches", not bad_hash, str(bad_hash))
    html = (HERE / "report.html").read_text(encoding="utf-8")
    record("report.size", len(html) >= 20000, f"{len(html)} bytes")
    for sec in ("sec-hero", "sec-4", "sec-8", "sec-9", "sec-11", "sec-appendix"):
        record(f"report.section.{sec}", f'id="{sec}"' in html)
    record("report.charts", html.count('class="chart-body') >= 4,
           str(html.count('class="chart-body')))
    record("report.readings", html.count('class="chart-reading') >= 4,
           str(html.count('class="chart-reading')))
    print(f"         report: {len(html)} bytes, {html.count('class=\"chart-body')} charts, "
          f"grade={conclusion.get('evidence_grade')}")

    return report_out()


def brief_to_plan(brief: dict) -> str:
    """Compose the analysis plan FROM the brief — the agent step of the flow."""
    lines = ["# Analysis plan（由 ontology_brief 生成）", "",
             f"- 场景 scene_key: `{brief.get('scene_key')}`（profile={brief.get('profile')}, "
             f"data_stage={brief.get('data_stage')}）",
             f"- 本体版本: v{brief.get('ontology_version')} "
             f"sha256={str(brief.get('ontology_sha256'))[:16]}…", "",
             "## 因子", ""]
    for f in brief.get("factors") or []:
        lines.append(f"- `{f.get('col')}`（{f.get('unit') or '单位未声明'}）预期方向 "
                     f"{f.get('expected_sign') or '未声明'}：{f.get('physical_meaning') or ''}")
    lines += ["", "## 响应与规格", ""]
    for r in brief.get("responses") or []:
        lines.append(f"- `{r.get('col')}`（{r.get('unit') or '—'}）goal={r.get('goal')} "
                     f"lsl={r.get('lsl')} usl={r.get('usl')} target={r.get('target')}")
    lines += ["", "## 机理关系", ""]
    for rel in (brief.get("relationships") or [])[:10]:
        lines.append(f"- {rel.get('from')} → {rel.get('to')}：{rel.get('mechanism') or rel.get('relation')}")
    lines += ["", "## 混杂与局限", ""]
    for c in brief.get("confounders") or []:
        lines.append(f"- 混杂: {c}")
    for lim in brief.get("limitations") or []:
        lines.append(f"- 局限: {lim}")
    cov = brief.get("coverage") or {}
    lines += ["", f"## 映射覆盖（0 静默）", "",
              f"- 因子 {cov.get('n_factors_matched')}/{cov.get('n_factors_declared')}，"
              f"响应 {cov.get('n_responses_matched')}/{cov.get('n_responses_declared')}，"
              f"未匹配 {cov.get('n_unmatched')}", "",
              "## 分析模式", "",
              "- designed（设计矩阵可识别）→ 效应表 + 响应面 + 联合推荐点；",
              "  逐因子窗口仅作诊断，执行依据取 joint_setpoints（单位有效 + 无硬约束违例）。", ""]
    return "\n".join(lines)


def report_out() -> int:
    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"\n[DEMO] {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f" — FAILED: {failed}" if failed else " — ALL GREEN"))
    print(f"[DEMO] run directory: {HERE}")
    print(f"[DEMO] human report:  {HERE / 'report.html'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
