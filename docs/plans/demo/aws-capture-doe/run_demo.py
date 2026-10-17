#!/usr/bin/env python
"""End-to-end field trial: AgentWorkShop capture → anomaly / fluctuation / DOE.

Drives the REAL pipeline (no hand-written numbers, no shortcuts) over one
simulated BOPET 12 µm line:

  0. capture          history/line/campaign exports + trial design + QC +
                      profiles + notes (regenerated deterministically on --fresh)
  1. E-1H             profile (63 points) + operator notes → scalar features,
                      joined to the DOE run table by run_id (skip = fallback)
  2. DOE              aws_capture → doe_context_adapter → ontology prepare
                      (build + reuse) → analysis_plan → analyze all → G1-G11
  3. quick-screen     sentinel baseline (with DOE operating windows) → watch
  4. stability        line stability report (ontology + sentinel baseline +
                      DOE windows) → HTML → gate
  5. retrieval        results_index.json + keyword queries
  6. routing          IDD intent directives × AgentWorkShop intent catalog
  7. evidence         compact, reviewable copy under ./evidence/

Usage:
    python run_demo.py [--fresh] [--skip-hetero] [--no-evidence]
Exit 0 = every check passed.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SKILL = REPO / ".claude" / "skills" / "industrial-doe-analyzer"
SENTINEL_SKILL = REPO / ".claude" / "skills" / "industrial-sentinel"
STABILITY_SKILL = REPO / ".claude" / "skills" / "industrial-line-stability-report"
SHARED = REPO / ".claude" / "shared"
SCRIPTS = SKILL / "scripts"
PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"

CAPTURE = HERE / "capture"
WORK = REPO / "workspace" / "aws-capture-e2e"
DOE = WORK / "doe"
SENT = WORK / "sentinel"
STAB = WORK / "stability"
HETERO = WORK / "hetero"
STORE = WORK / "_store"
EVID = HERE / "evidence"

GENERATED_DOE = ["01_profile", "02_analysis", "03_figures", "conclusions", "01_ontology",
                 "run_manifest.json", "report.html", "artifact_manifest.json"]
RESULTS: list[tuple[str, bool, str]] = []


def record(cid: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((cid, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {cid}" + (f"  {detail}" if detail and not ok else ""))


def run(argv: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True,
                          timeout=timeout, shell=False, cwd=str(REPO))


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def read_csv(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in header})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(buf.getvalue(), encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ stage 0

def stage_prepare(fresh: bool) -> None:
    print("\n== 0. capture ==")
    if fresh or not (CAPTURE / "campaign" / "mapping.json").is_file():
        r = run([PY, HERE / "generate_capture.py", "--force"])
        record("capture.generate", r.returncode == 0, r.stderr[-300:])
    for d in (DOE, SENT, STAB, HETERO):
        shutil.rmtree(d, ignore_errors=True)
    if fresh:
        shutil.rmtree(STORE, ignore_errors=True)
    n_runs = len(list((CAPTURE / "campaign" / "runs").iterdir()))
    record("capture.runs", n_runs == 22, str(n_runs))
    record("capture.exports", (CAPTURE / "history" / "manifest.json").is_file()
           and (CAPTURE / "line" / "manifest.json").is_file())


# ------------------------------------------------------------------ stage 1

def find_hetero_skill() -> Path | None:
    candidates = [
        REPO / ".claude" / "skills" / "industrial-hetero-preprocessor" / "scripts" / "build.py",
        Path("D:/codes/myskills/industrial-deep-diagnostic/.claude/skills/"
             "industrial-hetero-preprocessor/scripts/build.py"),
    ]
    return next((p for p in candidates if p.is_file()), None)


def stage_hetero(skip: bool) -> str:
    print("\n== 1. heterogeneous (E-1H) ==")
    truth = read_json(HERE / "scenario_truth.json")
    build = None if skip else find_hetero_skill()
    if build is None:
        record("hetero.skill", True, "skipped — capture fallback features are used")
        record("hetero.fallback_present",
               (CAPTURE / "campaign" / "hetero_features.csv").is_file())
        return "fallback"
    HETERO.mkdir(parents=True, exist_ok=True)
    r = run([PY, build, "--raw-path", CAPTURE / "hetero",
             "--anchor", CAPTURE / "hetero" / "anchor.csv", "--run-dir", HETERO])
    try:
        status = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        status = {}
    record("hetero.status", status.get("status") == "ok", (r.stdout or r.stderr)[-300:])
    if status.get("status") != "ok":
        return "fallback"
    feat_path = HETERO / "07_hetero" / "features" / "PROF-PROFILES.csv"
    contract = read_json(HETERO / "07_hetero" / "column_contract.json")
    anchor = {r["时间"]: r["run_id"] for r in read_csv(CAPTURE / "hetero" / "anchor.csv")}
    cols = ["HX-PROF-PROFILES-MEAN", "HX-PROF-PROFILES-STD",
            "HX-PROF-PROFILES-EDGE-L-DEV", "HX-PROF-PROFILES-EDGE-R-DEV",
            "HX-PROF-PROFILES-CURV-LSQ"]
    rows = []
    for row in read_csv(feat_path):
        rid = anchor.get(row["ts"])
        if rid:
            rows.append({"run_id": rid, **{c: row.get(c, "") for c in cols}})
    record("hetero.join_rows", len(rows) == 22, str(len(rows)))
    write_csv(CAPTURE / "campaign" / "hetero_features.csv", ["run_id"] + cols, rows)
    # plant check: the E-1H edge feature must track the planted edge signal
    truth_edge = {t["run_id"]: t["planted"]["edge_dev"] for t in truth["runs"]}
    truth_thick = {t["run_id"]: t["planted"]["thickness_um"] for t in truth["runs"]}
    xs = [float(r["HX-PROF-PROFILES-EDGE-L-DEV"]) for r in rows]
    ys = [truth_edge[r["run_id"]] for r in rows]
    corr = _corr(xs, ys)
    record("hetero.edge_tracks_truth", corr > 0.9, f"r={corr:.3f}")
    mxs = [float(r["HX-PROF-PROFILES-MEAN"]) for r in rows]
    mys = [truth_thick[r["run_id"]] for r in rows]
    record("hetero.mean_tracks_truth", _corr(mxs, mys) > 0.99,
           f"r={_corr(mxs, mys):.4f}")
    n_cols = len(contract.get("columns") or [])
    record("hetero.contract", n_cols >= 15, f"columns={n_cols}")
    ann = HETERO / "07_hetero" / "annotations.json"
    record("hetero.notes", ann.is_file() and len(read_json(ann)) >= 20,
           "annotations missing" if not ann.is_file() else str(len(read_json(ann))))
    return "e1h"


def _corr(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


# ------------------------------------------------------------------ stage 2

def brief_to_plan(brief: dict) -> str:
    lines = ["# Analysis plan（由 ontology_brief 生成）", "",
             f"- 场景 scene_key: `{brief.get('scene_key')}`（profile={brief.get('profile')}, "
             f"data_stage={brief.get('data_stage')}）",
             f"- 本体版本: v{brief.get('ontology_version')}", "", "## 因子", ""]
    for f in brief.get("factors") or []:
        lines.append(f"- `{f.get('col')}`（{f.get('unit') or '单位未声明'}）预期方向 "
                     f"{f.get('expected_sign') or '未声明'}：{f.get('physical_meaning') or ''}")
    lines += ["", "## 响应与规格", ""]
    for r in brief.get("responses") or []:
        lines.append(f"- `{r.get('col')}`（{r.get('unit') or '—'}）goal={r.get('goal')} "
                     f"lsl={r.get('lsl')} usl={r.get('usl')} target={r.get('target')}")
    lines += ["", "## 机理关系", ""]
    for rel in (brief.get("relationships") or [])[:12]:
        lines.append(f"- {rel.get('from')} → {rel.get('to')}：{rel.get('mechanism') or rel.get('relation')}")
    lines += ["", "## 混杂与局限", ""]
    for c in brief.get("confounders") or []:
        lines.append(f"- 混杂: {c}")
    for lim in brief.get("limitations") or []:
        lines.append(f"- 局限: {lim}")
    lines += ["", "## 分析模式", "",
              "- designed（CCD 设计矩阵可识别）→ 效应表 + 响应面 + 联合推荐点",
              "- 逐因子窗口仅作诊断，执行依据取 joint_setpoints",
              "- 异构剖面特征 HX-PROF-* 由 E-1H 提供，作为附加响应/证据，不改变因果层级", ""]
    return "\n".join(lines)


def stage_doe() -> dict:
    print("\n== 2. DOE (ontology-first) ==")
    aws = load_module("aws_capture", SCRIPTS / "aws_capture.py")
    rep = aws.build_capture(CAPTURE / "campaign", CAPTURE / "campaign" / "mapping.json", DOE)
    record("doe.capture_build", rep["rows"] == 22 and rep["responses"] == 5, str(rep))

    adapter = load_module("doe_context_adapter", SCRIPTS / "doe_context_adapter.py")
    rc = adapter.main(["--run-dir", str(DOE)])
    record("doe.adapter", rc == 0, f"rc={rc}")
    ctx = read_json(DOE / "00_input" / "analysis_context.json")
    record("doe.data_path", ctx.get("data_path") == "00_input/run_table.csv")
    record("doe.baseline", ctx.get("current_setpoint", {}).get("tdo_z4_temp") == 196.0,
           str(ctx.get("current_setpoint")))
    record("doe.constraints", len(ctx.get("constraints") or []) == 2)

    prep = load_module("doe_ontology_prepare", SCRIPTS / "doe_ontology_prepare.py")
    first = prep.prepare(DOE, mode="auto", store_dir=str(STORE))
    record("doe.ontology_stage", first.get("action") in ("built", "extended", "reused"),
           str(first.get("action")))
    second = prep.prepare(DOE, mode="auto", store_dir=str(STORE))
    record("doe.ontology_reuse", second.get("action") == "reused", str(second.get("action")))
    print(f"         ontology: {first.get('action')} -> {second.get('action')} "
          f"fp={str(first.get('context_fp'))[:12]}")
    brief = read_json(DOE / "01_ontology" / "ontology_brief.json")
    cov = brief.get("coverage") or {}
    record("doe.brief_coverage", cov.get("n_unmatched") == 0 and cov.get("ratio") == 1.0,
           str(cov))
    record("doe.brief_stage", brief.get("data_stage") == "collected")
    record("doe.brief_confounders_unique",
           len({c.get("variable") for c in brief.get("confounders") or []})
           == len(brief.get("confounders") or []))
    (DOE / "01_profile").mkdir(parents=True, exist_ok=True)
    (DOE / "01_profile" / "analysis_plan.md").write_text(brief_to_plan(brief), encoding="utf-8")

    analyze = load_module("analyze_demo", SCRIPTS / "analyze.py")
    saved = sys.argv
    sys.argv = ["analyze.py", "all", "--run-dir", str(DOE)]
    try:
        analyze.main()
        ok = True
    except SystemExit as exc:
        ok = not exc.code
    finally:
        sys.argv = saved
    record("doe.analyze_all", ok)

    gate = run(["node", SKILL / "scripts" / "quality_gate.mjs", DOE,
                "--skill-path", SKILL, "--shared-path", SHARED])
    gate_line = next((ln for ln in gate.stdout.splitlines() if ln.startswith("[GATE]")), "")
    record("doe.gate", gate.returncode == 0, gate_line or gate.stderr[-300:])
    print(f"         {gate_line}")
    return {"brief": brief, "first": first, "second": second}


def assert_doe() -> dict:
    print("\n-- 2b. DOE result vs planted truth --")
    truth = read_json(HERE / "scenario_truth.json")
    profile = read_json(DOE / "01_profile" / "data_profile.json")
    effect = read_json(DOE / "02_analysis" / "effect_table.json")
    models = read_json(DOE / "02_analysis" / "model.json")
    recs = read_json(DOE / "conclusions" / "recommendations.json")
    nxt = read_json(DOE / "conclusions" / "next_design.json")
    guide = read_json(DOE / "conclusions" / "optimization_guidance.json")
    cons = read_json(DOE / "02_analysis" / "ontology_consistency.json")
    screen = read_json(DOE / "02_analysis" / "association_screen.json")
    man = read_json(DOE / "artifact_manifest.json")

    design = profile.get("design") or {}
    record("design.type", design.get("design_type") == "rsm_ccd", str(design.get("design_type")))
    record("design.mode", design.get("mode") == "designed")
    record("design.centre", design.get("center_points") == 6, str(design.get("center_points")))
    record("design.axial", design.get("axial_points") == 6, str(design.get("axial_points")))

    fams = {f["response"]: f for f in effect.get("families") or []}
    th = {t["term"]: t for t in fams["thickness_um"]["tests"]}
    rec = {
        "tdo_z4_temp": (1.251, 0.20, 0.25),
        "mdo_speed": (-0.937, 0.20, 0.20),
        "tdo_ratio": (-0.360, 0.20, 0.15),
        "tdo_z4_temp:mdo_speed": (0.461, 0.20, 0.20),
    }
    for term, (expected, tol, _) in rec.items():
        got = float(th[term]["coefficient"])
        record(f"effect.{term}", abs(got - expected) <= tol, f"{got} vs {expected}")
    for term in ("tdo_z4_temp", "mdo_speed", "tdo_ratio"):
        q = th[term].get("q_value_bh")
        record(f"effect.q.{term}", q is not None and q < 0.01, str(q))
    record("effect.n_families", len(fams) == 5, str(sorted(fams)))
    record("effect.interval_semantics",
           isinstance(effect.get("interval_semantics"), str)
           and "pi95" in effect["interval_semantics"]
           and "tolerance_interval_95_95" in effect["interval_semantics"])
    record("effect.ci_excludes_zero",
           th["tdo_z4_temp"]["effect_ci95"][0] > 0 and th["mdo_speed"]["effect_ci95"][1] < 0,
           str(th["tdo_z4_temp"]["effect_ci95"]))

    thick_model = next(m for m in models if m.get("response") == "thickness_um")
    st = thick_model.get("stationary_point") or {}
    coded = st.get("coded") or {}
    tstat = truth["stationary"]["stationary_thickness_coded"]
    record("rsm.stationary_temp", abs(coded.get("tdo_z4_temp", 99) - tstat[0]) < 0.25,
           f"{coded.get('tdo_z4_temp')} vs {tstat[0]}")
    record("rsm.stationary_speed", abs(coded.get("mdo_speed", 99) - tstat[1]) < 0.25,
           f"{coded.get('mdo_speed')} vs {tstat[1]}")
    record("rsm.stationary_inside", st.get("inside_design_region") is True)
    record("rsm.lof", (fams["thickness_um"].get("lack_of_fit") or {}).get("p_value", 0) > 0.05,
           str((fams["thickness_um"].get("lack_of_fit") or {}).get("p_value")))

    js = (recs.get("joint_setpoints") or [{}])[0]
    pred = js.get("predicted") or {}
    record("joint.exists", bool(js.get("id")))
    record("joint.feasible", js.get("feasible") is True and js.get("hard_constraint_violations") == 0,
           str(js.get("hard_constraint_violations")))
    record("joint.thickness_in_spec", 48 <= pred["thickness_um"]["mean"] <= 52,
           str(pred["thickness_um"]["mean"]))
    record("joint.haze_in_spec", pred["haze_pct"]["mean"] <= 2.2,
           str(pred["haze_pct"]["mean"]))
    record("joint.tensile_lsl", pred["tensile_mpa"]["mean"] >= 170,
           str(pred["tensile_mpa"]["mean"]))
    record("joint.desirability", float(js.get("desirability") or 0) > 0.6,
           str(js.get("desirability")))
    record("joint.linear_constraint_enforced",
           any(c.get("factor", "").startswith("linear:") for c in recs.get("constraints") or []),
           str(recs.get("constraints")))
    record("baseline.source",
           (recs.get("current_baseline") or {}).get("source", {}).get("tdo_z4_temp")
           == "current_setpoint",
           str((recs.get("current_baseline") or {}).get("source")))

    patches = {p["factor"]: p for p in guide.get("recipe_patch") or []}
    record("patch.temp", patches.get("tdo_z4_temp", {}).get("from") == 196.0
           and abs(patches["tdo_z4_temp"]["to"] - js["factors"]["tdo_z4_temp"]) < 0.11,
           str(patches.get("tdo_z4_temp")))
    record("patch.speed", patches.get("mdo_speed", {}).get("from") == 330.0
           and abs(patches["mdo_speed"]["to"] - js["factors"]["mdo_speed"]) < 0.11,
           str(patches.get("mdo_speed")))
    record("patch.actionable", all(p.get("actionable") and p.get("within_limits")
                                   for p in patches.values()), str(list(patches)))
    record("patch.platform_ref", all((p.get("platform_ref") or {}).get("recipe_param")
                                     for p in patches.values()))
    record("guide.node_setpoints", len(guide.get("node_setpoints") or []) >= 2,
           str(len(guide.get("node_setpoints") or [])))

    record("screen.causal_none", screen.get("causal_claim") == "none")
    record("screen.pairs", int(screen.get("n_pairs") or 0) > 10, str(screen.get("n_pairs")))
    record("screen.no_window", "forbidden" in str(screen.get("window_emission", "")))
    record("consistency.checked", int(cons.get("checked") or 0) >= 10,
           str(cons.get("checked")))
    record("consistency.advisory_only",
           all((c.get("severity") or "advisory") == "advisory"
               for c in cons.get("contradictions") or []),
           str(cons.get("contradictions"))[:200])
    record("next.action", bool(nxt.get("recommended_action"))
           and bool(nxt.get("actions")), str(nxt.get("recommended_action")))
    record("next.constraints_ok", (nxt.get("actions") or [{}])[0].get("constraints_ok") is True)

    record("manifest.complete", not (man.get("missing") or [])
           and len(man.get("artifacts") or []) == 15, str(man.get("missing")))
    kinds = {a.get("kind") for a in man.get("artifacts") or []}
    for kind in ("effect_table", "model", "recommendations", "next_design",
                 "optimization_guidance", "ontology_brief", "report"):
        record(f"manifest.{kind}", kind in kinds)
    probe = run(["node", "-e",
                 "import('./app/backend/src/services/artifact-manifest.service.mjs')"
                 ".then(m=>console.log(JSON.stringify(m.buildArtifactManifest(process.argv[1]))))",
                 str(DOE)])
    try:
        backend_man = json.loads((probe.stdout or "").strip().splitlines()[-1])
    except Exception:
        backend_man = {}
    record("manifest.backend_read", backend_man.get("source") == "analyzer"
           and len(backend_man.get("artifacts") or []) == 15,
           (probe.stdout or probe.stderr)[-300:])
    return {"joint": js, "grade": recs.get("contract_version"), "patches": patches}


# ------------------------------------------------------------------ stage 3

def stage_sentinel() -> dict:
    print("\n== 3. quick-screen (sentinel) ==")
    SENT.mkdir(parents=True, exist_ok=True)
    aws = load_module("aws_capture_sent", SCRIPTS / "aws_capture.py")
    hist = WORK / "history_wide.csv"
    line = WORK / "line_wide.csv"
    aws.pivot_export(CAPTURE / "history", hist, names="id", fmt="iso")
    aws.pivot_export(CAPTURE / "line", line, names="id", fmt="iso")
    r = run([PY, SENTINEL_SKILL / "scripts" / "build_baseline.py",
             "--history-csv", hist, "--doe-run-dir", DOE,
             "--out", SENT / "watch_baseline.json", "--time-col", "ts_iso"])
    record("sentinel.baseline", r.returncode == 0, (r.stderr or r.stdout)[-300:])
    w = run([PY, SENTINEL_SKILL / "scripts" / "sentinel.py", "watch",
             "--data", line, "--baseline", SENT / "watch_baseline.json",
             "--out-dir", SENT, "--time-col", "ts_iso"])
    record("sentinel.watch", w.returncode in (0, 1), (w.stderr or w.stdout)[-300:])
    gate = run(["node", SENTINEL_SKILL / "scripts" / "quality_gate.mjs",
                SENT / "alert.json", "--baseline", SENT / "watch_baseline.json",
                "--skill-path", SENTINEL_SKILL, "--shared-path", SHARED])
    record("sentinel.gate", gate.returncode == 0,
           next((ln for ln in gate.stdout.splitlines() if ln.startswith("[GATE]")), gate.stderr[-200:]))
    return read_json(SENT / "alert.json")


def assert_sentinel(alert: dict) -> None:
    print("\n-- 3b. anomaly result vs planted truth --")
    truth = read_json(HERE / "scenario_truth.json")["anomaly"]
    record("sentinel.status", alert.get("status") == "alert", str(alert.get("status")))
    checks = alert.get("checks_summary") or {}
    record("sentinel.spc", int((checks.get("spc") or {}).get("n_triggered") or 0) > 0,
           str(checks.get("spc")))
    proj = {p["factor"]: p for p in (alert.get("projection_summary") or [])}
    zt = proj.get("tdo_z4_temp") or {}
    record("sentinel.drift_detected", zt.get("hours_to_edge") == 0
           and truth["z4_drift_c_per_h"] * 0.7 <= float(zt.get("slope_per_hour") or 0)
           <= truth["z4_drift_c_per_h"] * 1.25,
           str(zt))
    record("sentinel.regime", int((checks.get("regime") or {}).get("n_change_points_new") or 0) >= 1,
           str(checks.get("regime")))
    alerts = alert.get("alerts") or []
    record("sentinel.chiller_frozen",
           any("chiller_pressure" in str(a.get("parameter")) for a in alerts),
           "no chiller alert")
    record("sentinel.route_to_doe",
           any(a.get("suggested_next_skill") == "industrial-doe-analyzer" for a in alerts))
    print(f"         alerts={len(alerts)} spc={checks.get('spc', {}).get('n_triggered')} "
          f"drift={zt.get('slope_per_hour')} C/h -> {zt.get('hours_to_edge')}h")


# ------------------------------------------------------------------ stage 4

def stage_stability() -> dict:
    print("\n== 4. fluctuation (stability report) ==")
    STAB.mkdir(parents=True, exist_ok=True)
    write_json(STAB / "report_context.json", {
        "line_id": "bopet-lineA", "product": "BOPET-12um", "time_col": "ts_iso",
        "inspection_cols": ["thickness_gauge", "haze_gauge"],
        "spec_limits": {"thickness_gauge": {"lsl": 48.0, "usl": 52.0, "target": 50.0},
                        "haze_gauge": {"usl": 2.2}},
        "baseline_path": str(SENT / "watch_baseline.json"),
        "doe_run_dir": str(DOE),
    })
    line = WORK / "line_wide.csv"
    r = run([PY, STABILITY_SKILL / "scripts" / "stability_analyzer.py", "analyze",
             "--data", line, "--context", STAB / "report_context.json",
             "--out-dir", STAB, "--time-col", "ts_iso",
             "--baseline", SENT / "watch_baseline.json",
             "--doe-run-dir", DOE,
             "--ontology", DOE / "01_ontology" / "ontology.json"])
    record("stability.analyze", r.returncode in (0, 1), (r.stderr or r.stdout)[-300:])
    b = run([PY, STABILITY_SKILL / "scripts" / "report_builder.py",
             "--report", STAB / "stability_report.json",
             "--charts", STAB / "charts.json",
             "--out", STAB / "line_stability_report.html",
             "--md", STAB / "line_stability_report.md"])
    html = STAB / "line_stability_report.html"
    record("stability.html", b.returncode == 0 and html.is_file() and html.stat().st_size > 8000,
           (b.stderr or b.stdout)[-200:])
    gate = run(["node", STABILITY_SKILL / "scripts" / "quality_gate.mjs",
                STAB / "stability_report.json", STAB])
    record("stability.gate", gate.returncode == 0,
           next((ln for ln in gate.stdout.splitlines() if ln.startswith("[line-report-gate]")),
                gate.stderr[-200:]))
    return read_json(STAB / "stability_report.json")


def assert_stability(rep: dict) -> None:
    print("\n-- 4b. fluctuation result --")
    con = rep.get("conclusion") or {}
    score = float(con.get("score") or 0)
    record("stability.score", 40 <= score <= 70, str(score))
    record("stability.grade", con.get("grade") in ("C", "D"), str(con.get("grade")))
    findings = rep.get("findings") or []
    record("stability.drift_finding",
           any(f.get("category") == "drift" and "tdo_z4_temp" in str(f.get("title"))
               for f in findings))
    doe = (rep.get("integrations") or {}).get("doe_analyzer") or {}
    record("stability.doe_used", doe.get("used") is True)
    wins = doe.get("operating_windows") or []
    record("stability.doe_windows", len(wins) >= 3
           and all(w.get("parameter") and w.get("low") is not None
                   and w.get("high") is not None for w in wins), str(wins))
    record("stability.doe_role",
           all(w.get("window_role") == "marginal_diagnostic" for w in wins))
    record("stability.doe_joint", bool(doe.get("joint_setpoints")))
    record("stability.ontology",
           ((rep.get("condition") or {}).get("ontology") or {}).get("mode") == "ontology")
    selfcheck = read_json(STAB / "html_selfcheck.json")
    record("stability.html_selfcheck", selfcheck.get("pass") is True, str(selfcheck)[:200])
    print(f"         score={score} grade={con.get('grade')} findings={len(findings)} "
          f"doe_windows={len(wins)}")


# ------------------------------------------------------------------ stage 5

def build_index() -> list[dict]:
    print("\n== 5. result retrieval index ==")
    entries = []

    def add(eid, title, tags, path, summary, metrics=None):
        p = Path(path)
        if not p.is_file():
            return
        entries.append({"id": eid, "title": title, "tags": tags,
                        "path": str(p.relative_to(REPO)).replace("\\", "/"),
                        "summary": summary, "metrics": metrics or {}})

    eff = read_json(DOE / "02_analysis" / "effect_table.json")
    th = next(f for f in eff["families"] if f["response"] == "thickness_um")
    top = {t["term"]: round(float(t["coefficient"]), 4)
           for t in th["tests"][:3] if t.get("coefficient") is not None}
    add("doe_effects", "DOE 效应表（厚度/雾度/拉伸/在线测厚/剖面）",
        ["DOE", "因子", "效应", "显著性", "ANOVA", "厚度", "雾度", "拉伸", "q值"],
        DOE / "02_analysis" / "effect_table.json",
        "全因子主效应 + 2FI + 二次项，含效应 CI 与 BH q", top)
    recs = read_json(DOE / "conclusions" / "recommendations.json")
    js = (recs.get("joint_setpoints") or [{}])[0]
    add("doe_recommendations", "联合设定点与推荐操作窗",
        ["推荐", "联合设定点", "操作窗", "优化", "参数", "执行", "厚度", "雾度", "拉伸"],
        DOE / "conclusions" / "recommendations.json",
        "joint_setpoints 是唯一可执行载体；逐因子窗口为边际诊断",
        {"joint": js.get("factors"), "D": js.get("desirability")})
    guide = read_json(DOE / "conclusions" / "optimization_guidance.json")
    add("doe_guidance", "平台落参指导（recipe patch）",
        ["平台", "recipe", "setpoint", "执行", "联合设定点", "优化"],
        DOE / "conclusions" / "optimization_guidance.json",
        "带 platform_ref 的 recipe_patch 与 node_setpoints", {"patches": len(guide.get("recipe_patch") or [])})
    nxt = read_json(DOE / "conclusions" / "next_design.json")
    add("doe_next_design", "下一轮布点建议",
        ["下一轮", "布点", "确认", "augment", "设计"],
        DOE / "conclusions" / "next_design.json",
        f"recommended_action={nxt.get('recommended_action')}")
    add("doe_ontology", "场景本体与 Agent 理解 brief",
        ["本体", "场景", "机理", "因子", "响应", "单位", "混杂", "审计"],
        DOE / "01_ontology" / "ontology_brief.json",
        "因子/响应/单位/预期方向/机理/混杂，coverage=1.0")
    add("doe_association", "全参数关联筛查（causal_claim=none）",
        ["相关", "关联", "全参数", "筛查", "因果边界"],
        DOE / "02_analysis" / "association_screen.json",
        "设计校正 vs 边际关联；不进入任何窗口")
    add("doe_consistency", "本体一致性校验（advisory）",
        ["本体", "一致性", "方向", "矛盾"],
        DOE / "02_analysis" / "ontology_consistency.json",
        "预期方向 vs 实测效应；矛盾只作 advisory")
    add("sentinel_alert", "异常筛查告警（SPC / 漂移投影 / 变点 / 稳健 z）",
        ["异常", "告警", "漂移", "冻结", "SPC", "变点", "温度"],
        SENT / "alert.json",
        "Z4 温度漂移投影与交接班张力台阶",
        {"drift": (read_json(SENT / "alert.json").get("projection_summary") or [{}])})
    rep = read_json(STAB / "stability_report.json")
    add("stability_report", "波动/稳定性报告（评分 + 证据链）",
        ["波动", "稳定性", "稳定性评分", "评分", "等级", "Cpk", "漂移"],
        STAB / "stability_report.json",
        "综合评分与逐参数证据", {"score": rep["conclusion"]["score"],
                                 "grade": rep["conclusion"]["grade"]})
    add("stability_html", "稳定性 HTML 落地页",
        ["报告", "HTML", "可视化", "波动", "稳定性"],
        STAB / "line_stability_report.html", "可给企业全员阅读的中文报告")
    add("doe_html", "DOE HTML 分析报告（含本体/joint/next design）",
        ["报告", "HTML", "可视化", "DOE", "联合设定点"],
        DOE / "report.html", "确定性渲染，§11 含本体 brief 与联合设定点")
    add("hetero_contract", "异构特征契约（剖面/备注）",
        ["异构", "剖面", "特征", "E-1H", "多源"],
        HETERO / "07_hetero" / "column_contract.json",
        "每列公式/物理依据/证据等级/覆盖率")
    for e in entries:
        if e["id"] == "sentinel_alert":
            e["metrics"] = {"projection": (read_json(SENT / "alert.json").get("projection_summary") or [])}
    write_json(WORK / "results_index.json", {
        "contract_version": "1.0", "generated_by": "run_demo.py",
        "scenarios": {"anomaly": "quick-screen", "fluctuation": "stability-report",
                      "doe": "doe-analysis"},
        "entries": entries,
    })
    queries = {
        "厚度": ["doe_effects", "doe_recommendations"],
        "漂移": ["sentinel_alert", "stability_report"],
        "联合设定点": ["doe_recommendations", "doe_guidance"],
        "剖面": ["hetero_contract"],
        "稳定性评分": ["stability_report"],
        "下一轮": ["doe_next_design"],
        "本体": ["doe_ontology", "doe_consistency"],
    }
    index = read_json(WORK / "results_index.json")["entries"]
    for q, expected in queries.items():
        hits = [e["id"] for e in index
                if q.lower() in (e["id"] + " " + e["title"] + " "
                                 + " ".join(e["tags"]) + " " + e["summary"]).lower()]
        record(f"query.{q}", all(x in hits for x in expected), str(hits))
    print(f"         index entries={len(index)}; queries={len(queries)}/all hit")
    return index


# ------------------------------------------------------------------ stage 6

def stage_routing() -> dict:
    print("\n== 6. scenario → skill routing ==")
    r = run(["node", HERE / "routing_check.mjs", "--json"])
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {}
    record("routing.idd", rep.get("passed") == rep.get("total") and rep.get("total", 0) >= 18,
           (r.stdout or r.stderr)[-400:])
    record("routing.aws_aligned",
           any(c["id"] == "aws.skill_alignment" and c["ok"] for c in rep.get("checks") or [])
           or any(w["id"] == "aws.absent" for w in rep.get("warnings") or []))
    p0 = [w for w in rep.get("warnings") or [] if w.get("severity") == "P0-platform"]
    record("routing.platform_gap_disclosed", True,
           "; ".join(w["id"] for w in p0) if p0 else "no platform gap")
    print(f"         {rep.get('passed')}/{rep.get('total')} IDD checks; "
          f"platform warnings={[w['id'] for w in rep.get('warnings') or []]}")
    return rep


# ------------------------------------------------------------------ evidence

def copy_evidence(summary: dict, routing: dict) -> None:
    print("\n== 7. evidence ==")
    shutil.rmtree(EVID, ignore_errors=True)
    EVID.mkdir(parents=True)
    files = [
        (DOE / "report.html", "doe_report.html"),
        (DOE / "artifact_manifest.json", "doe_artifact_manifest.json"),
        (DOE / "conclusions" / "doe_conclusion.json", "doe_conclusion.json"),
        (DOE / "conclusions" / "recommendations.json", "doe_recommendations.json"),
        (DOE / "conclusions" / "next_design.json", "doe_next_design.json"),
        (DOE / "conclusions" / "optimization_guidance.json", "doe_optimization_guidance.json"),
        (DOE / "02_analysis" / "effect_table.json", "doe_effect_table.json"),
        (DOE / "02_analysis" / "association_screen.json", "doe_association_screen.json"),
        (DOE / "02_analysis" / "ontology_consistency.json", "doe_ontology_consistency.json"),
        (DOE / "01_ontology" / "ontology_brief.json", "doe_ontology_brief.json"),
        (DOE / "01_profile" / "analysis_plan.md", "doe_analysis_plan.md"),
        (SENT / "alert.json", "sentinel_alert.json"),
        (STAB / "stability_report.json", "stability_report.json"),
        (STAB / "line_stability_report.html", "line_stability_report.html"),
        (HETERO / "07_hetero" / "column_contract.json", "hetero_column_contract.json"),
    ]
    copied = 0
    for src, dst in files:
        if src.is_file():
            shutil.copyfile(src, EVID / dst)
            copied += 1
    # Rewrite the committed retrieval index to point at the evidence copies, so
    # `query_results.py` works in a fresh clone (the live work dir is ignored).
    ev_map = {
        "doe_effects": "doe_effect_table.json",
        "doe_recommendations": "doe_recommendations.json",
        "doe_guidance": "doe_optimization_guidance.json",
        "doe_next_design": "doe_next_design.json",
        "doe_ontology": "doe_ontology_brief.json",
        "doe_association": "doe_association_screen.json",
        "doe_consistency": "doe_ontology_consistency.json",
        "sentinel_alert": "sentinel_alert.json",
        "stability_report": "stability_report.json",
        "stability_html": "line_stability_report.html",
        "doe_html": "doe_report.html",
        "hetero_contract": "hetero_column_contract.json",
    }
    live = read_json(WORK / "results_index.json")
    for e in live.get("entries") or []:
        e["path"] = ev_map.get(e["id"], Path(e.get("path", "")).name)
    live["path_base"] = "evidence/"
    write_json(EVID / "results_index.json", live)
    write_json(EVID / "routing.json", routing)
    write_json(EVID / "demo_summary.json", summary)
    record("evidence.copy", copied >= 14, f"{copied} files")
    print(f"         {EVID} ({copied} files + index/routing/summary)")


# ------------------------------------------------------------------ main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run_demo.py")
    ap.add_argument("--fresh", action="store_true",
                    help="regenerate the capture and wipe the local ontology store")
    ap.add_argument("--skip-hetero", action="store_true")
    ap.add_argument("--no-evidence", action="store_true")
    args = ap.parse_args(argv)

    print("== AWS capture field trial: anomaly / fluctuation / DOE ==")
    stage_prepare(args.fresh)
    hetero_source = stage_hetero(args.skip_hetero)
    ontology = stage_doe()
    doe_summary = assert_doe()
    alert = stage_sentinel()
    assert_sentinel(alert)
    rep = stage_stability()
    assert_stability(rep)
    index = build_index()
    routing = stage_routing()
    summary = {
        "contract_version": "1.0",
        "capture": str(CAPTURE.relative_to(REPO)).replace("\\", "/"),
        "hetero_source": hetero_source,
        "ontology": {"first": ontology["first"].get("action"),
                     "second": ontology["second"].get("action")},
        "doe": {"joint_setpoint": doe_summary["joint"].get("factors"),
                "desirability": doe_summary["joint"].get("desirability"),
                "patches": {k: {"from": v.get("from"), "to": v.get("to")}
                            for k, v in doe_summary["patches"].items()},
                "evidence_grade": read_json(DOE / "conclusions" / "doe_conclusion.json")
                .get("evidence_grade")},
        "anomaly": {"alerts": len(alert.get("alerts") or []),
                    "spc_triggered": (alert.get("checks_summary", {}).get("spc") or {}).get("n_triggered"),
                    "projection": alert.get("projection_summary")},
        "fluctuation": {"score": rep["conclusion"]["score"],
                        "grade": rep["conclusion"]["grade"],
                        "findings": len(rep.get("findings") or [])},
        "retrieval": {"entries": len(index)},
        "routing": {"passed": routing.get("passed"), "total": routing.get("total"),
                    "warnings": [w.get("id") for w in routing.get("warnings") or []]},
    }
    if not args.no_evidence:
        copy_evidence(summary, routing)
    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"\n[DEMO] {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f" — FAILED: {failed}" if failed else " — ALL GREEN"))
    print(f"[DEMO] work dir: {WORK}")
    print(f"[DEMO] DOE report: {DOE / 'report.html'}")
    print(f"[DEMO] field report: {STAB / 'line_stability_report.html'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
