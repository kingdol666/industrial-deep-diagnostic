#!/usr/bin/env python
"""Phase-1 (ontology-first) tests — DOE ontology store + prepare + brief + gate + consistency.

Covers the traceability ids owned by Phase 1:
  F13.*      ontology stage (design-only build, brief, coverage, CP-2)
  ont-store.* ontology_store profile/context_fp/reuse/extend/isolation (P1-2)
  ont-gate.*  enforce_gate semantics (P1-3/P1-5)
  F22.*       advisory consistency + feedback (P1-8)
  P1-6/P1-7   backend DOE intent directive + orchestrator skill (static + render checks)

Run (repo root, uv venv — same convention as run_tests.py):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/test_ontology_phase1.py [case|all]

Every case is self-contained: fixtures + an isolated ontology store live in a
temp dir, so nothing is written into the repo's data/ontology_store.
"""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
SCRIPTS = SKILL / "scripts"
SCHEMAS = SKILL / "schemas"
STORE_JS = SHARED / "scripts" / "ontology_store.mjs"
VALIDATE_JS = SHARED / "scripts" / "validate.mjs"
ONTOLOGY_SCHEMA = REPO / ".claude" / "skills" / "industrial-ontology-builder" / "schemas" / "ontology_schema.json"

sys.path.insert(0, str(SCRIPTS))
from doe_ontology_prepare import (  # noqa: E402
    prepare, enforce_gate, _context_fp, build_prior_ontology, GATE_BRIEF_REQUIRED,
    GATE_PLAN_REQUIRED, GATE_DESIGN_ONLY_NO_RESPONSE,
)
from ontology_brief import build_brief, write_brief  # noqa: E402
from ontology_consistency import check, write_feedback, normalize_sign  # noqa: E402

RESULTS = []
TMP = Path(tempfile.mkdtemp(prefix="ont-phase1-")).resolve()


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def node(args, timeout=120, store=None):
    env = None
    if store is not None:
        import os
        env = dict(os.environ)
        env["ONTOLOGY_STORE_DIR"] = str(store)
    return subprocess.run(["node", *[str(a) for a in args]], capture_output=True,
                          text=True, timeout=timeout, shell=False, cwd=str(REPO), env=env)


def validate_doc(schema, doc):
    res = node([VALIDATE_JS, schema, doc])
    try:
        report = json.loads(res.stdout or "null")
    except json.JSONDecodeError:
        report = None
    if report is None:
        return False, (res.stdout or res.stderr)[-300:]
    errs = report.get("errors") or []
    return (res.returncode == 0 and not errs), json.dumps(errs[:4], ensure_ascii=False)


# --------------------------------------------------------------------- fixtures

FACTORS = [
    {"col": "zone1_temp", "name": "zone1_temp", "type": "numeric", "unit": "°C",
     "min": 180, "max": 220, "expected_sign": "+", "physical_meaning": "TDO 加热区温度",
     "ontology_signal": "TDO_Z4_SETPOINT", "role": "control"},
    {"col": "line_speed", "name": "line_speed", "type": "numeric", "unit": "m/min",
     "min": 280, "max": 360, "expected_sign": "-", "physical_meaning": "线速",
     "ontology_signal": "MD_LINE_SPEED", "role": "control"},
]
RESPONSES = [
    {"col": "thickness_um", "name": "thickness_um", "unit": "um", "goal": "target",
     "lsl": 48.0, "usl": 52.0, "target": 50.0, "ontology_signal": "FILM_THICKNESS_MEAN"},
    {"col": "haze_pct", "name": "haze_pct", "unit": "%", "goal": "minimize",
     "lsl": None, "usl": 2.5, "target": None},
]

RUN_TABLE = """run_id,design_point_id,zone1_temp,line_speed,thickness_um,haze_pct
d1,dp-1,180,280,,
d2,dp-1,180,280,,
d3,dp-2,220,280,,
d4,dp-3,180,360,,
"""


def make_context(**overrides):
    ctx = {
        "contract_version": "1.1",
        "experiment_id": "doe-phase1-fixture",
        "line_id": "L5-bopet",
        "objective": "厚度稳定在 50±1.5um",
        "data_path": "00_input/run_table.csv",
        "design_type_declared": "ccd",
        "design_region": {"factorial_bounds": {"zone1_temp": [180, 220]}, "design_hull": "ccd_star"},
        "factors": copy.deepcopy(FACTORS),
        "responses": copy.deepcopy(RESPONSES),
        "blocks": [],
        "covariates": ["ambient_temp"],
        "constraints": [{"factor": "zone1_temp", "type": "box", "min": 185, "max": 215, "hard": True}],
        "ontology": {"profile": "doe", "mode": "auto", "scene_key": "bopet_tdo",
                     "data_stage": "design_only"},
    }
    ctx.update(overrides)
    return ctx


def make_run(name, ctx=None, table=RUN_TABLE):
    run_dir = (TMP / name).resolve()
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    if table is not None:
        (run_dir / "00_input" / "run_table.csv").write_text(table, encoding="utf-8")
    if ctx is not None:
        (run_dir / "00_input" / "analysis_context.json").write_text(
            json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_dir


def new_store(name):
    store = (TMP / "stores" / name).resolve()
    store.mkdir(parents=True, exist_ok=True)
    return store


# ═════════════════════════════════════════════════════ F13 — ontology stage

def case_f13_design_only():
    store = new_store("f13")
    run = make_run("f13_build", make_context())
    res = prepare(run, store_dir=store, seed=42)
    record("F13.design_only_builds", res["action"] == "built" and Path(res["ontology_path"]).is_file(),
           f"action={res['action']}")
    record("F13.results_contract",
           all(k in res for k in ("action", "ontology_path", "brief_json", "brief_md", "coverage_path",
                                  "version", "context_fp", "scene_key", "data_stage", "elapsed_ms",
                                  "rag_used", "web_used")),
           "missing required result keys")
    record("F13.design_only_stage", res["data_stage"] == "design_only", res["data_stage"])
    record("F13.prior_no_rag", res["rag_used"] is False and res["web_used"] is False
           and res["rag_used_by_prepare"] is False,
           f"rag={res['rag_used']} web={res['web_used']}")
    record("F13.artifact_set",
           all(Path(p).is_file() for p in (res["brief_json"], res["brief_md"], res["coverage_path"])),
           "missing artifact")
    record("F13.cp2_floor", res["cp2_floor_ok"] and res["ontology_bytes"] >= 1024,
           f"bytes={res['ontology_bytes']}")

    ontology = read_json(res["ontology_path"])
    ok, detail = validate_doc(ONTOLOGY_SCHEMA, res["ontology_path"])
    record("F13.schema_valid", ok, detail)

    signals = ontology["signals"]
    behaviour = [s.get("observed_data_behavior") for s in signals["control_variables"]
                 + signals["inspection_signals"]]
    record("F13.obs_behavior_na", bool(behaviour) and all(b == "NOT_APPLICABLE" for b in behaviour),
           f"behaviour={sorted(set(map(str, behaviour)))}")
    matches = [s.get("behavior_match") for s in signals["control_variables"]
               + signals["inspection_signals"]]
    record("F13.no_fabrication", all(m == "UNVERIFIED" for m in matches),
           f"behavior_match={sorted(set(map(str, matches)))}")
    record("F13.prior_evidence",
           ontology["provenance"]["engine"] == "industrial-ontology-builder"
           and ontology["provenance"]["build_mode"] == "prior_knowledge"
           and ontology["provenance"]["physics_prior_used"] is True,
           json.dumps(ontology["provenance"], ensure_ascii=False)[:200])
    rels = ontology["relationships"]
    record("F13.relationships_declared_only",
           len(rels) == 4 and all(r["type"] == "causal" and r["inferred"] and r["expected_sign"] for r in rels),
           f"n={len(rels)}")

    brief = read_json(res["brief_json"])
    required = ("contract_version", "scene_key", "profile", "data_stage", "ontology_version",
                "ontology_sha256", "context_fp", "factors", "responses", "relationships",
                "confounders", "limitations", "column_mapping", "coverage", "provenance")
    record("F13.brief_fields", all(k in brief for k in required),
           f"missing={[k for k in required if k not in brief]}")
    record("F13.brief_profile", brief["profile"] == "doe", brief.get("profile"))
    ok, detail = validate_doc(SCHEMAS / "ontology_brief.schema.json", res["brief_json"])
    record("F13.brief_schema_valid", ok, detail)
    ok, detail = validate_doc(SCHEMAS / "ontology_coverage.schema.json", res["coverage_path"])
    record("F13.coverage_schema_valid", ok, detail)

    cm = brief["column_mapping"]
    mapped = cm["matched"] + cm["inferred"] + cm["unmatched"]
    cols = sorted(r["col"] for r in mapped)
    declared = sorted([f["col"] for f in FACTORS] + [r["col"] for r in RESPONSES])
    record("F13.coverage_complete",
           brief["coverage"]["ratio"] == 1.0 and cols == declared
           and all(r.get("reason") for r in cm["inferred"] + cm["unmatched"]),
           f"ratio={brief['coverage']['ratio']} cols={cols}")
    record("F13.coverage_zero_silent", len(mapped) == len(set(cols)),
           "duplicate mapping rows")

    md = Path(res["brief_md"]).read_text(encoding="utf-8")
    record("F13.brief_md", all(token in md for token in ("因子", "响应", "列映射覆盖", "局限")),
           "md sections missing")
    record("F13.design_only_limitation", any("design_only" in x for x in brief["limitations"]),
           "no design_only limitation recorded")


def case_f13_adopt_agent_ontology():
    store = new_store("f13b")
    run = make_run("f13b_adopt", make_context())
    ontology_dir = run / "01_ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    # an agent-authored (enriched) ontology already in the run dir must be adopted, not overwritten
    agent_ontology = build_prior_ontology(make_context(), scene_key="bopet_tdo",
                                          data_stage="design_only")
    agent_ontology["doe"]["limitations"].append("agent enrichment: Z4 heater PID interaction suspected")
    agent_ontology["provenance"].update({"build_mode": "full", "rag_used": True, "web_used": True})
    (ontology_dir / "ontology.json").write_text(
        json.dumps(agent_ontology, ensure_ascii=False, indent=2), encoding="utf-8")
    res = prepare(run, store_dir=store)
    written = read_json(res["ontology_path"])
    record("F13.agent_ontology_adopted",
           res["action"] == "built" and res["build_mode"] == "full"
           and any("agent enrichment" in x for x in written["doe"]["limitations"]),
           f"action={res['action']} mode={res['build_mode']}")
    record("F13.rag_used_truthful", res["rag_used"] is True and res["web_used"] is True
           and res["rag_used_by_prepare"] is False,
           f"rag={res['rag_used']} web={res['web_used']}")


# ═════════════════════════════════════════════ ont-store — store layer (P1-2)

def case_ont_store():
    store = new_store("store")
    ctx = make_context()
    run1 = make_run("store_run1", ctx)
    first = prepare(run1, store_dir=store, seed=7)
    record("ont-store.first_build", first["action"] == "built" and first["store"]["published"],
           f"action={first['action']} store={first['store']}")

    run2 = make_run("store_run2", ctx)
    t0 = Path(run2 / "00_input" / "analysis_context.json").read_text(encoding="utf-8")
    second = prepare(run2, store_dir=store)
    record("ont-store.exact_reuse_fast",
           second["action"] == "reused" and second["lookup"] == "exact"
           and second["elapsed_ms"] < 60000,
           f"action={second['action']} lookup={second['lookup']} ms={second['elapsed_ms']}")
    record("ont-store.reuse_no_rag",
           second["rag_used"] is False and second["web_used"] is False,
           "reuse path must not call RAG/web")
    # same data context published under a different scene key must still reuse
    # (DEF-03: exact context_fp is matched across scenes, not only inside scene).
    renamed_ctx = make_context()
    renamed_ctx["ontology"]["scene_key"] = "bopet_tdo_renamed"
    run_renamed = make_run("store_run_renamed", renamed_ctx)
    renamed = prepare(run_renamed, store_dir=store)
    record("ont-store.cross_scene_exact_reuse",
           renamed["action"] == "reused" and renamed["lookup"] == "exact",
           f"action={renamed['action']} lookup={renamed['lookup']} scene={renamed['scene_key']}")
    record("ont-store.version_pinned",
           second["version"] == first["version"]
           and read_json(second["brief_json"])["ontology_version"] == first["version"]
           and read_json(second["brief_json"])["ontology_sha256"],
           f"v1={first['version']} v2={second['version']}")

    # context change (spec) → scene_only → extend, new store version, new context_fp
    changed = make_context()
    changed["responses"][1]["usl"] = 3.0
    run3 = make_run("store_run3", changed)
    third = prepare(run3, store_dir=store)
    record("ont-store.context_change_extends",
           third["action"] == "extended" and third["lookup"] == "scene_only"
           and third["version"] != first["version"]
           and third["context_fp"] != first["context_fp"],
           f"action={third['action']} lookup={third['lookup']} v={third['version']}")
    index = read_json(store / "index.json")
    record("ont-store.index_entry_shape",
           all(all(k in e for k in ("scene_key", "profile", "context_fp", "data_stage", "version"))
               for e in index["entries"])
           and all(e["profile"] == "doe" for e in index["entries"]),
           json.dumps(index["entries"], ensure_ascii=False)[:300])

    # cross-language + cross-run determinism of context_fp
    js = node([STORE_JS, "context-fp", "--context", run1 / "00_input" / "analysis_context.json"])
    js_fp = json.loads(js.stdout or "{}").get("context_fp")
    record("ont-store.context_fp_cross_language",
           js_fp == _context_fp(ctx) == first["context_fp"],
           f"js={js_fp} py={_context_fp(ctx)}")

    # a diagnosis entry for the same scene/data file must never leak into the doe lookup
    # (2026-10-21 namespace change: version numbers are (profile, scope)-local and
    # directories are namespaced — the invariant is now "the doe asset is untouched
    # and on disk", not "version numbers differ")
    diag = make_run("store_diag", None, table=None)
    (diag / "01_ontology").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run1 / "01_ontology" / "ontology.json", diag / "01_ontology" / "ontology.json")
    pub = node([STORE_JS, "publish", "--run-dir", diag, "--scene", "bopet_tdo",
                "--data-file", run1 / "00_input" / "run_table.csv"], store=store)
    pub_out = json.loads(pub.stdout or "{}")
    doe_entry = next((e for e in read_json(store / "index.json")["entries"]
                      if e.get("profile") == "doe" and e.get("scene_key") == "bopet_tdo"), None)
    record("ont-store.diagnosis_profile_unchanged",
           pub_out.get("profile") == "diagnosis" and doe_entry is not None
           and (store / doe_entry["path"]).is_file()
           and Path(pub_out.get("path") or "").resolve() != (store / doe_entry["path"]).resolve(),
           json.dumps(pub_out)[:200])
    doe_find = json.loads(node([STORE_JS, "find", "--profile", "doe", "--scene", "bopet_tdo",
                                "--context-fp", first["context_fp"]], store=store).stdout or "{}")
    legacy_find = json.loads(node([STORE_JS, "find", run1 / "00_input" / "run_table.csv"],
                                  store=store).stdout or "{}")
    record("ont-store.cross_profile_never_reused",
           doe_find.get("profile") == "doe" and doe_find.get("version") == first["version"]
           and legacy_find.get("version") == pub_out.get("version"),
           f"doe={doe_find.get('version')} legacy={legacy_find.get('version')}")
    # wrong context on an existing scene is scene_only, never exact
    rec = json.loads(node([STORE_JS, "recommend", "--scene", "bopet_tdo", "--profile", "doe",
                           "--context-fp", "sha256:" + "0" * 64], store=store).stdout or "{}")
    record("ont-store.scene_only_not_exact", rec.get("status") == "scene_only",
           f"status={rec.get('status')}")


def case_ont_store_off_and_determinism():
    store = new_store("off")
    run = make_run("off_run", make_context())
    res = prepare(run, store_dir=store, mode="off")
    wrote = list((run / "01_ontology").glob("*")) if (run / "01_ontology").exists() else []
    record("ont-store.mode_off_skips",
           res["action"] == "skipped" and not wrote
           and not (store / "index.json").exists(),
           f"action={res['action']} files={wrote}")

    run_a = make_run("det_a", make_context())
    run_b = make_run("det_b", make_context())
    a = prepare(run_a, store_dir=new_store("det_a"))
    b = prepare(run_b, store_dir=new_store("det_b"))
    same_ontology = (run_a / "01_ontology" / "ontology.json").read_bytes() \
        == (run_b / "01_ontology" / "ontology.json").read_bytes()
    record("ont-store.determinism_two_runs",
           same_ontology and a["context_fp"] == b["context_fp"] and a["version"] == b["version"],
           "two identical inputs produced different ontology bytes / fp")


# ═════════════════════════════════════════════════ ont-gate — enforce_gate

def case_ont_gate():
    store = new_store("gate")
    run = make_run("gate_run", make_context())
    ctx = make_context()

    # (a) key missing / mode off → no-op (keeps F1–F12 behaviour identical)
    for label, payload in (("missing_key", {}), ("mode_off", {"ontology": {"mode": "off"}}),
                           ("mode_none", {"ontology": {"mode": None}})):
        try:
            enforce_gate(run, payload)
            record(f"ont-gate.{label}_noop", True)
        except SystemExit as exc:
            record(f"ont-gate.{label}_noop", False, str(exc)[:120])

    # (b) mode=auto without brief
    bare = make_run("gate_bare", None, table=None)
    try:
        enforce_gate(bare, {"ontology": {"mode": "auto"}})
        record("ont-gate.missing_brief_blocks", False, "no SystemExit")
    except SystemExit as exc:
        record("ont-gate.missing_brief_blocks", str(exc).startswith(GATE_BRIEF_REQUIRED),
               str(exc)[:120])

    # stage 1 → brief exists
    res = prepare(run, store_dir=store)
    record("ont-gate.prepare_ok", res["action"] == "built", res["action"])

    # (c) brief present, analysis_plan.md missing
    try:
        enforce_gate(run, {"ontology": {"mode": "auto"}})
        record("ont-gate.missing_plan_blocks", False, "no SystemExit")
    except SystemExit as exc:
        record("ont-gate.missing_plan_blocks", str(exc).startswith(GATE_PLAN_REQUIRED),
               str(exc)[:120])

    # (d) all present
    plan = run / "01_profile" / "analysis_plan.md"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("# 分析计划\n\n场景理解 / 因子 / 响应 / 混杂与局限\n", encoding="utf-8")
    try:
        enforce_gate(run, {"ontology": {"mode": "auto", "data_stage": "collected"}})
        record("ont-gate.all_present_ok", True)
    except SystemExit as exc:
        record("ont-gate.all_present_ok", False, str(exc)[:120])

    # (e) design_only + empty responses + statistics subcommand
    design_ctx = {"ontology": {"mode": "auto", "data_stage": "design_only"},
                  "responses": ctx["responses"], "data_path": "00_input/run_table.csv"}
    try:
        enforce_gate(run, design_ctx, subcommand="run")
        record("ont-gate.design_only_empty_blocks", False, "no SystemExit")
    except SystemExit as exc:
        record("ont-gate.design_only_empty_blocks",
               str(exc).startswith(GATE_DESIGN_ONLY_NO_RESPONSE), str(exc)[:120])
    try:
        enforce_gate(run, design_ctx, subcommand="profile")
        record("ont-gate.profile_subcommand_allowed", True)
    except SystemExit as exc:
        record("ont-gate.profile_subcommand_allowed", False, str(exc)[:120])

    # order evidence: plan newer than brief
    record("ont-gate.order_proven", plan.stat().st_mtime >= (run / "01_ontology" / "ontology_brief.json").stat().st_mtime,
           "analysis_plan.md is older than the brief")


# ═════════════════════════════════════════ F22 — advisory consistency (P1-8)

def synthetic_effect_table(thickness_sign=+1.0, haze_sign=+1.0, estimable=True):
    """Complete 2-factor × 2-response main-effect table (every pair estimable).

    signs: zone1_temp→thickness_um = thickness_sign ; line_speed→thickness_um = −thickness_sign
           zone1_temp→haze_pct = haze_sign ; line_speed→haze_pct = −haze_sign
    (the ontology expects zone1_temp '+' and line_speed '−' for both responses)
    """
    def test(term, coef):
        return {"term": term, "coefficient": coef, "estimable": True, "n": 12,
                "reason_code": None, "order": 1}
    thickness_tests = [test("zone1_temp", 2.0 * thickness_sign),
                       test("line_speed", -3.0 * thickness_sign)]
    haze_tests = [test("zone1_temp", 1.0 * haze_sign), test("line_speed", -4.0 * haze_sign)]
    if not estimable:
        haze_tests = [haze_tests[0], {"term": "line_speed", "coefficient": None, "estimable": False,
                                      "n": 12, "reason_code": "aliased", "order": 1}]
    return {
        "generated_at": "2026-10-17T00:00:00Z",
        "mode": "designed",
        "model_spec": {"main_effects": ["zone1_temp", "line_speed"], "interactions": [], "quadratic": []},
        "coding": {"method": "deviation", "continuous_scaling": "range/2"},
        "families": [
            {"response": "thickness_um", "n": 12, "df_resid": 9, "r_squared": 0.8, "tests": thickness_tests},
            {"response": "haze_pct", "n": 12, "df_resid": 9, "r_squared": 0.7, "tests": haze_tests},
        ],
        "multiple_testing": {"method": "BH", "n_families": 2, "total_tests": 4, "total_significant_q05": 2},
    }


def case_f22_consistency():
    store = new_store("f22")
    run = make_run("f22_run", make_context())
    prepare(run, store_dir=store)
    brief = read_json(run / "01_ontology" / "ontology_brief.json")
    ctx = make_context()
    effect_table = synthetic_effect_table()
    before = json.dumps(effect_table, sort_keys=True)

    matched = check(effect_table, ctx, brief)
    record("F22.consistency_keys",
           all(k in matched for k in ("contract_version", "profile", "checked", "matched",
                                      "not_estimable", "contradictions", "advisory_only", "pairs")),
           f"keys={sorted(matched)}")
    record("F22.matched_all", matched["checked"] == 4 and matched["matched"] == 4
           and matched["contradictions"] == [] and matched["not_estimable"] == 0,
           json.dumps(matched["pairs"], ensure_ascii=False)[:200])
    record("F22.advisory_flag", matched["advisory_only"] is True, "advisory_only must be true")

    # flipped sign on both factors (expected '+','−', observed the opposite) → advisory contradictions
    flipped = synthetic_effect_table(thickness_sign=-1.0, haze_sign=-1.0)
    contra = check(flipped, ctx, brief)
    record("F22.contradiction_advisory",
           len(contra["contradictions"]) == 4
           and all(c["severity"] == "advisory" for c in contra["contradictions"])
           and all(c["expected_sign"] in ("positive", "negative") for c in contra["contradictions"])
           and contra["checked"] == 4 and contra["matched"] == 0,
           json.dumps(contra["contradictions"], ensure_ascii=False)[:200])

    # non-estimable term + correlative relationship + categorical factor
    nonest = check(synthetic_effect_table(estimable=False), ctx, brief)
    reasons = {d["response"]: d["reason"] for d in nonest["not_estimable_detail"]}
    record("F22.not_estimable_reasons",
           nonest["not_estimable"] >= 1 and all(r for r in reasons.values())
           and any("not estimable" in r for r in reasons.values())
           and nonest["checked"] == 3,
           json.dumps(reasons, ensure_ascii=False)[:200])

    brief_corr = copy.deepcopy(brief)
    brief_corr["relationships"] = [{"from": "zone1_temp", "to": "thickness_um",
                                    "relation": "correlative", "mechanism": "co-movement",
                                    "confidence": "weak", "evidence_level": "statistical_prior",
                                    "expected_sign": None, "predicted_functional_form": None}]
    corr_only = check(effect_table, ctx, brief_corr)
    record("F22.correlative_excluded", corr_only["checked"] == 0
           and corr_only["not_estimable"] >= 1 and corr_only["contradictions"] == [],
           json.dumps(corr_only["pairs"], ensure_ascii=False)[:200])

    brief_cat = copy.deepcopy(brief)
    brief_cat["factors"] = [dict(f, type="categorical") if f["col"] == "zone1_temp" else f
                            for f in brief_cat["factors"]]
    cat = check(effect_table, ctx, brief_cat)
    record("F22.categorical_not_estimable",
           any("categorical" in d["reason"] for d in cat["not_estimable_detail"]),
           json.dumps(cat["not_estimable_detail"], ensure_ascii=False)[:200])

    record("F22.no_mutation", json.dumps(effect_table, sort_keys=True) == before,
           "check() mutated the effect table")

    feedback_path = write_feedback(run, {
        "ontology_version": brief.get("ontology_version"),
        "ontology_sha256": brief.get("ontology_sha256"),
        "scene_key": brief.get("scene_key"), "context_fp": brief.get("context_fp"),
    }, contra)
    ok, detail = validate_doc(SCHEMAS / "ontology_feedback.schema.json", feedback_path)
    feedback = read_json(feedback_path)
    record("F22.feedback_written",
           Path(feedback_path).is_file() and ok
           and all(k in feedback for k in ("contract_version", "ontology_version", "ontology_sha256",
                                           "checked", "matched", "not_estimable", "contradictions",
                                           "checked_at"))
           and feedback["advisory_only"] is True,
           detail)
    record("F22.normalisable_signs",
           normalize_sign("+") == "positive" and normalize_sign("increase") == "positive"
           and normalize_sign("-") == "negative" and normalize_sign("下降") == "negative"
           and normalize_sign("sideways") is None and normalize_sign(None) is None,
           "sign normalisation table changed")


def case_f22_cli_advisory_only():
    store = new_store("f22cli")
    run = make_run("f22_cli", make_context())
    prepare(run, store_dir=store)
    # a collected-stage effect table + flipped signs
    (run / "02_analysis").mkdir(parents=True, exist_ok=True)
    (run / "02_analysis" / "effect_table.json").write_text(
        json.dumps(synthetic_effect_table(thickness_sign=-1.0, haze_sign=-1.0),
                   ensure_ascii=False, indent=2), encoding="utf-8")
    before = (run / "02_analysis" / "effect_table.json").read_bytes()
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "ontology_consistency.py"),
         "--run-dir", str(run), "--consistency-json"],
        capture_output=True, text=True, timeout=180, shell=False)
    after = (run / "02_analysis" / "effect_table.json").read_bytes()
    out = {}
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        pass
    record("F22.cli_runs", proc.returncode == 0 and out.get("contradictions") == 4,
           (proc.stdout or proc.stderr)[-200:])
    record("F22.cli_advisory_only", before == after and out.get("advisory_only") is True,
           "effect_table.json was modified by the advisory check")
    ok, detail = validate_doc(SCHEMAS / "ontology_consistency.schema.json",
                              run / "02_analysis" / "ontology_consistency.json")
    record("F22.consistency_schema_valid", ok, detail)


# ═══════════════════════════════ P1-1 / P1-6 / P1-7 — surfaces & wiring

def case_p1_surfaces():
    skill_md = (REPO / ".claude" / "skills" / "industrial-ontology-builder" / "SKILL.md").read_text(encoding="utf-8")
    protocol = (REPO / ".claude" / "skills" / "industrial-ontology-builder" / "references"
                / "agent-protocol.md").read_text(encoding="utf-8")
    record("P1-1.skill_profile_selectors",
           "PROFILE" in skill_md and "DATA_STAGE" in skill_md and "design_only" in skill_md
           and "NOT_APPLICABLE" in skill_md and "profile=doe" in skill_md,
           "builder SKILL.md lacks the profile/data_stage contract")
    record("P1-1.protocol_phase0d",
           "Phase 0D" in protocol and "PROFILE=doe" in protocol
           and "design_only" in protocol and "NOT_APPLICABLE" in protocol,
           "builder protocol lacks the DOE checklist")
    record("P1-1.diagnosis_unchanged_doc",
           "PROFILE=diagnosis" in protocol or "`diagnosis` (default)" in skill_md,
           "diagnosis default not documented")

    schema = read_json(ONTOLOGY_SCHEMA)
    record("P1-1.ontology_schema_doe",
           "doe" in schema["properties"] and "provenance" in schema["properties"]
           and "expected_sign" in schema["definitions"]["control_signal_v6_3"]["properties"],
           "ontology_schema.json lacks the doe block / expected_sign")

    # P1-6 — backend wiring (static, plus a render check when backend deps are installed)
    service = (REPO / "app" / "backend" / "src" / "services" / "diagnosis.service.mjs").read_text(encoding="utf-8")
    client = (REPO / "app" / "backend" / "src" / "engine" / "claude-client.mjs").read_text(encoding="utf-8")
    record("P1-6.creation_payload",
           "resolveDoeOntologyDirective" in service
           and "analysisIntent === 'doe-analysis'" in service
           and "profile: 'doe'" in service,
           "DOE intent does not carry the doe ontology profile")
    record("P1-6.execution_passthrough",
           "'doe-analysis', 'stability-report', 'quick-screen'].includes(runIntent)" in service,
           "execution pass-through still blanks the DOE ontology")
    record("P1-6.off_refused_source",
           "refused_off" in service and "ontologyDevOverride" in service,
           "mode=off is not refused / no dev override path")
    record("P1-6.doe_directive_source",
           "buildDoeOntologyDirective" in client and "ONTOLOGY_PROFILE: doe" in client,
           "claude-client has no DOE ontology directive")

    client_uri = (REPO / "app" / "backend" / "src" / "engine" / "claude-client.mjs").as_uri()
    render = node(["-e", (
        f"const m = await import({json.dumps(client_uri)});"
        "const doe = m.buildOntologyDirective({profile:'doe',mode:'auto',scene_key:'s',"
        "data_stage:'design_only',reason:'r'});"
        "const diag = m.buildOntologyDirective({mode:'reuse',source:'/x.json',scene_key:'s',"
        "version:1,reason:'r'});"
        "console.log(JSON.stringify({doe, diag}));"
    ), "--input-type=module"], timeout=120)
    if render.returncode == 0 and render.stdout.strip().startswith("{"):
        payload = json.loads(render.stdout.strip().splitlines()[-1])
        record("P1-6.directive_render",
               "ONTOLOGY_PROFILE: doe" in payload["doe"]
               and "doe_ontology_prepare.py" in payload["doe"]
               and "ONTOLOGY_DATA_STAGE: design_only" in payload["doe"]
               and "ONTOLOGY_MODE: reuse" in payload["diag"]
               and "## Ontology Directive" in payload["diag"]
               and "DOE profile" not in payload["diag"],
               payload["doe"][:200])
    else:
        record("P1-6.directive_render", False,
               "SKIPPED-ENV: backend deps unavailable → " + (render.stderr or "")[-160:].replace("\n", " "))

    orchestrator_dir = REPO / ".claude" / "skills" / "industrial-doe-orchestrator"
    orch = (orchestrator_dir / "SKILL.md").read_text(encoding="utf-8")
    orch_protocol = (orchestrator_dir / "references" / "agent-protocol.md").read_text(encoding="utf-8")
    ordered = all(token in orch for token in ("prepare", "brief", "analyzer", "consistency", "next_design",
                                              "HARD GATE", "ontology_coverage.json", "analysis_plan.md"))
    record("P1-7.orchestrator_skill",
           orch.startswith("---") and "name: industrial-doe-orchestrator" in orch and ordered,
           "orchestrator SKILL.md missing the frozen order / gates")
    negatives = orch[orch.find("## Negative triggers"):orch.find("## Failure Recovery")]
    record("P1-7.negative_triggers",
           all(token in negatives for token in ("industrial-analysis-auto", "industrial-sentinel",
                                                "industrial-tuning-memory", "industrial-optimizer-loop",
                                                "industrial-line-stability-report")),
           "negative triggers incomplete")
    record("P1-7.orchestrator_protocol",
           all(token in orch_protocol for token in ("enforce_gate", "ONTOLOGY_BRIEF_REQUIRED",
                                                    "ANALYSIS_PLAN_REQUIRED", "DESIGN_ONLY_NO_RESPONSE",
                                                    "doe_ontology_prepare.py")),
           "orchestrator protocol lacks the gate commands")


CASES = {
    "F13": [case_f13_design_only, case_f13_adopt_agent_ontology],
    "ont-store": [case_ont_store, case_ont_store_off_and_determinism],
    "ont-gate": [case_ont_gate],
    "F22": [case_f22_consistency, case_f22_cli_advisory_only],
    "surfaces": [case_p1_surfaces],
}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    selected = CASES if which == "all" else {which: CASES[which]}
    for group, cases in selected.items():
        print(f"[{group}]")
        for fn in cases:
            try:
                fn()
            except Exception as exc:  # a crashing case is a failed case, never a silent skip
                record(f"{group}.{fn.__name__}_EXCEPTION", False, f"{type(exc).__name__}: {exc}")
    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"[TESTS] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    try:
        shutil.rmtree(TMP, ignore_errors=True)
    except OSError:
        pass
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
