#!/usr/bin/env python
"""Run the generality corpus through the real DOE pipeline.

For every case: doe_context_adapter -> doe_ontology_prepare -> analysis_plan ->
analyze.py all -> quality_gate.mjs, then assert the recovered design type, the
planted effects, the gate and the report against the case's truth.json.

Usage:
    python run_cases.py [--only id1,id2] [--keep]
Exit 0 = every case passed.
"""
from __future__ import annotations

import argparse
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
CASES = HERE / "cases"
WORK = REPO / "workspace" / "doe-generality"
STORE = WORK / "_store"
GEN = ["01_profile", "02_analysis", "03_figures", "conclusions", "01_ontology",
       "run_manifest.json", "report.html", "artifact_manifest.json"]
RESULTS: list[dict] = []


def record(case_id: str, check: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"case": case_id, "check": check, "ok": ok, "detail": detail})
    if not ok:
        print(f"  FAIL  {case_id}:{check}  {detail}")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def brief_to_plan(brief: dict) -> str:
    lines = ["# Analysis plan（由 ontology_brief 生成）", "",
             f"- 场景 scene_key: `{brief.get('scene_key')}`（profile={brief.get('profile')}, "
             f"data_stage={brief.get('data_stage')}）",
             f"- 本体版本: v{brief.get('ontology_version')}", "", "## 因子", ""]
    for f in brief.get("factors") or []:
        lines.append(f"- `{f.get('col')}`（{f.get('unit') or '未声明'}）预期方向 "
                     f"{f.get('expected_sign') or '未声明'}：{f.get('physical_meaning') or ''}")
    lines += ["", "## 响应与规格", ""]
    for r in brief.get("responses") or []:
        lines.append(f"- `{r.get('col')}`（{r.get('unit') or '—'}）goal={r.get('goal')} "
                     f"lsl={r.get('lsl')} usl={r.get('usl')} target={r.get('target')}")
    lines += ["", "## 混杂与局限", ""]
    for c in brief.get("confounders") or []:
        lines.append(f"- 混杂: {c}")
    for lim in brief.get("limitations") or []:
        lines.append(f"- 局限: {lim}")
    lines += ["", "## 分析模式", "",
              "- designed（设计矩阵可识别）→ 效应表 + 响应面 + 联合推荐点",
              "- 逐因子窗口仅作诊断，执行依据取 joint_setpoints", ""]
    return "\n".join(lines)


def find_tests(effect: dict, response: str) -> list[dict]:
    for fam in effect.get("families") or []:
        if fam.get("response") == response:
            return fam.get("tests") or []
    return []


def term_row(tests: list[dict], term: str) -> dict | None:
    for t in tests:
        if t.get("term") == term:
            return t
    for t in tests:
        if str(t.get("term", "")).startswith(term + "[") or str(t.get("term")) == term:
            return t
    return None


def run_case(case_dir: Path) -> dict:
    case_id = case_dir.name
    truth = read(case_dir / "truth.json")
    run_dir = WORK / case_id
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(case_dir, run_dir)
    for name in GEN:
        target = run_dir / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            target.unlink(missing_ok=True)
    (run_dir / "00_input" / "analysis_context.json").unlink(missing_ok=True)

    adapter = load("gen_adapter", SCRIPTS / "doe_context_adapter.py")
    rc = adapter.main(["--run-dir", str(run_dir)])
    record(case_id, "adapter", rc == 0, f"rc={rc}")

    prep = load("gen_prepare", SCRIPTS / "doe_ontology_prepare.py")
    res = prep.prepare(run_dir, mode="full", store_dir=str(STORE))
    record(case_id, "ontology", res.get("action") in ("built", "extended", "reused"),
           str(res.get("action")))
    brief = read(run_dir / "01_ontology" / "ontology_brief.json")
    cov = brief.get("coverage") or {}
    record(case_id, "coverage", cov.get("ratio") == 1.0 and cov.get("n_unmatched") == 0,
           str(cov))
    (run_dir / "01_profile").mkdir(parents=True, exist_ok=True)
    (run_dir / "01_profile" / "analysis_plan.md").write_text(
        brief_to_plan(brief), encoding="utf-8")

    analyze = load("gen_analyze", SCRIPTS / "analyze.py")
    saved = sys.argv
    sys.argv = ["analyze.py", "all", "--run-dir", str(run_dir)]
    try:
        analyze.main()
        rc_analyze = 0
        err = ""
    except SystemExit as exc:
        rc_analyze = exc.code or 0
        err = ""
    except Exception as exc:  # noqa: BLE001 - record the real failure
        rc_analyze = 99
        err = f"{type(exc).__name__}: {exc}"
    finally:
        sys.argv = saved

    if truth.get("kind") == "design_only":
        record(case_id, "design_only_refused", rc_analyze != 0,
               f"rc={rc_analyze} expected a refusal")
        record(case_id, "design_only_stage", brief.get("data_stage") == "design_only",
               str(brief.get("data_stage")))
        return summary_row(case_id, truth, None, brief, refused=rc_analyze != 0)

    record(case_id, "analyze", rc_analyze == 0, f"rc={rc_analyze} {err}")
    if rc_analyze != 0:
        return summary_row(case_id, truth, None, brief, error=err)

    gate = subprocess.run(
        ["node", str(SKILL / "scripts" / "quality_gate.mjs"), str(run_dir),
         "--skill-path", str(SKILL), "--shared-path", str(SHARED)],
        capture_output=True, text=True, shell=False, timeout=300, cwd=str(REPO))
    record(case_id, "gate", gate.returncode == 0,
           next((ln for ln in gate.stdout.splitlines() if ln.startswith("[GATE]")),
                gate.stderr[-300:]))
    profile = read(run_dir / "01_profile" / "data_profile.json")
    recs = read(run_dir / "conclusions" / "recommendations.json")
    manifest = read(run_dir / "artifact_manifest.json")
    detected = (profile.get("design") or {}).get("design_type")
    expected_design = truth.get("design")
    expected_set = expected_design if isinstance(expected_design, list) else [expected_design]
    record(case_id, "design_type", detected in expected_set,
           f"{detected} not in {expected_set}")
    record(case_id, "mode", (profile.get("design") or {}).get("mode")
           == ("observational" if "observational" in expected_set else "designed"),
           str((profile.get("design") or {}).get("mode")))
    record(case_id, "manifest", not (manifest.get("missing") or [])
           and len(manifest.get("artifacts") or []) >= (10 if "observational" in expected_set else 12),
           str(manifest.get("missing")))
    report = run_dir / "report.html"
    record(case_id, "report", report.is_file() and report.stat().st_size > 10_000,
           f"{report.stat().st_size if report.is_file() else 0}B")

    if "observational" in expected_set:
        corr = run_dir / "02_analysis" / "correlation_report.json"
        record(case_id, "correlation", corr.is_file(), "correlation_report missing")
        grade = read(run_dir / "conclusions" / "doe_conclusion.json").get("evidence_grade")
        record(case_id, "evidence_grade", grade in ("A-", "B+", "B", "B-"), str(grade))
        wins = recs.get("operating_windows") or []
        record(case_id, "confirmation_needed",
               all(w.get("confirmation_needed") is True for w in wins),
               f"{len(wins)} windows")
        return summary_row(case_id, truth, profile, brief, recs=recs,
                           detected=detected, gate_ok=gate.returncode == 0)

    effect = read(run_dir / "02_analysis" / "effect_table.json")
    for response, term, sign in truth.get("effects") or []:
        tests = find_tests(effect, response)
        row = term_row(tests, term)
        ok = row is not None and row.get("coefficient") is not None
        if ok:
            coef = float(row["coefficient"])
            if sign != "*":
                ok = (coef > 0) == (sign == "+")
        else:
            coef = None
        q = (row or {}).get("q_value_bh")
        ok = ok and q is not None and float(q) < 0.05
        record(case_id, f"effect.{response}.{term}", ok,
               f"coef={(row or {}).get('coefficient')} q={q}")

    for response, term in truth.get("null") or []:
        tests = find_tests(effect, response)
        rows = [t for t in tests if str(t.get("term", "")).startswith(term)]
        qs = [t.get("q_value_bh") for t in rows if t.get("q_value_bh") is not None]
        record(case_id, f"null.{response}.{term}", not qs or min(qs) > 0.05,
               f"q={qs}")

    if case_id == "plastics_units":
        units = recs.get("units") or {}
        record(case_id, "unit_conflict", bool(units.get("conflicts")),
               str(units.get("conflicts")))
        guide = read(run_dir / "conclusions" / "optimization_guidance.json")
        missing = [m.get("factor") for m in guide.get("platform_ref_missing") or []]
        record(case_id, "platform_ref_missing", "screw_rpm" in missing, str(missing))
        patch = [p.get("factor") for p in guide.get("recipe_patch") or []]
        record(case_id, "patch_excludes_missing", "screw_rpm" not in patch, str(patch))
    if case_id == "coating_conflict":
        record(case_id, "joint", bool(recs.get("joint_setpoints")),
               "no joint setpoint")
    return summary_row(case_id, truth, profile, brief, effect=effect, recs=recs,
                       detected=detected, gate_ok=gate.returncode == 0)


def summary_row(case_id, truth, profile, brief, **kw):
    return {
        "id": case_id,
        "industry": truth.get("industry"),
        "kind": truth.get("kind", "designed"),
        "expected_design": truth.get("design"),
        "detected_design": kw.get("detected"),
        "n_rows": truth.get("n_rows"),
        "ontology": brief.get("data_stage"),
        "gate": kw.get("gate_ok"),
        "error": kw.get("error"),
        "refused": kw.get("refused"),
        "checks": [r for r in RESULTS if r["case"] == case_id],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    dirs = sorted([d for d in CASES.iterdir() if d.is_dir()])
    if only:
        dirs = [d for d in dirs if d.name in only]
    print(f"== generality corpus: {len(dirs)} cases ==")
    rows = []
    for d in dirs:
        print(f"-- {d.name}")
        rows.append(run_case(d))
    failed = [r for r in RESULTS if not r["ok"]]
    by_case: dict[str, dict] = {}
    for r in rows:
        by_case[r["id"]] = r
    matrix = {"contract_version": "1.0", "cases": rows,
              "total_checks": len(RESULTS),
              "passed_checks": len(RESULTS) - len(failed),
              "failed": failed}
    (HERE / "generality_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[CASES] {len(rows) - len({f['case'] for f in failed})}/{len(rows)} cases green; "
          f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        for f in failed[:20]:
            print(f"  FAIL {f['case']}:{f['check']} {f['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
