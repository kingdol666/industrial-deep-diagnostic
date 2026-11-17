#!/usr/bin/env python
"""Test runner for industrial-html-reviewer/scripts/quality_gate.mjs (AC in tests/AC.md).

Usage (from repo root):
  .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-html-reviewer/tests/run_tests.py [case|all]
  python .claude/skills/industrial-html-reviewer/tests/run_tests.py              # any python3

Fixtures are generated on the fly into a system temp dir and removed afterwards; nothing is committed.

Gate exit codes: 0 ok | 1 hard error | 2 undetermined (review artifact absent) | 3 gate-fail.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCHEMAS = SKILL / "schemas"
GATE = SKILL / "scripts" / "quality_gate.mjs"
RESULTS = []
TMP = None

CHECK_NAMES = [
    "hero_clarity", "evidence_layer_1_statistical", "evidence_layer_2_physics", "evidence_layer_3_exclusion",
    "image_usage_from_03_figures", "three_d_fidelity", "chart_initialization", "dual_evidence_per_conclusion",
    "plain_language_translation", "action_and_limitations", "render_manifest_produced",
    "manifest_page_consistency", "no_cross_run_pollution", "selfcheck_audit",
]


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def run_gate(*args):
    return subprocess.run(["node", str(GATE), *args], capture_output=True, text=True, timeout=120, shell=False)


def make_run(name):
    run = Path(TMP) / name
    (run / "05_review").mkdir(parents=True, exist_ok=True)
    return run


def valid_review() -> dict:
    return {
        "verdict": "pass",
        "overall_score": 92,
        "blocking_issues": [],
        "warnings": [],
        "checks": [{"name": n, "status": "pass", "evidence": f"页面证据：{n} 通过"} for n in CHECK_NAMES],
    }


def write_review(run, obj):
    (run / "05_review" / "html_review.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# ── case 1: valid artifact → exit 0 ─────────────────────────────────────────
def case_valid():
    run = make_run("valid")
    write_review(run, valid_review())
    p = run_gate("--run-dir", str(run))
    record("valid.full_pass_exit0", p.returncode == 0, f"rc={p.returncode} out={p.stdout[-300:]}")
    record("valid.reports_verdict_and_checks", '"verdict_value": "pass"' in p.stdout and '"checks": 14' in p.stdout,
           p.stdout[-300:])
    # warn verdicts are legitimate outcomes: structurally valid -> still exit 0
    r = valid_review()
    r["verdict"] = "warn"
    r["overall_score"] = 80
    r["warnings"] = ["建议补充机理链下钻"]
    write_review(run, r)
    record("valid.warn_verdict_exit0", run_gate("--run-dir", str(run)).returncode == 0, "")


# ── case 2: artifact absent → exit 2 (undetermined) ─────────────────────────
def case_absent():
    run = make_run("absent")
    p = run_gate("--run-dir", str(run))
    record("absent.exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")


# ── case 3: corrupt artifacts → exit 3 ──────────────────────────────────────
def case_corrupt():
    run = make_run("corrupt")
    target = run / "05_review" / "html_review.json"

    target.write_text("{not json at all", encoding="utf-8")
    record("corrupt.unparseable_exit3", run_gate("--run-dir", str(run)).returncode == 3, "")

    target.write_text(json.dumps({"verdict": "maybe"}), encoding="utf-8")
    p = run_gate("--run-dir", str(run))
    record("corrupt.missing_fields_exit3", p.returncode == 3 and "R2" in p.stdout, p.stdout[-300:])

    r = valid_review()
    r["verdict"] = "maybe"
    write_review(run, r)
    p = run_gate("--run-dir", str(run))
    record("corrupt.bad_verdict_enum_exit3", p.returncode == 3 and "R3" in p.stdout, p.stdout[-300:])

    r = valid_review()
    r["blocking_issues"] = [{"red_line": 11, "note": "fabricated"}]
    write_review(run, r)
    p = run_gate("--run-dir", str(run))
    record("corrupt.blocking_issues_objects_exit3", p.returncode == 3 and "R5" in p.stdout, p.stdout[-300:])

    r = valid_review()
    r["checks"][0]["name"] = "made_up_check"
    write_review(run, r)
    p = run_gate("--run-dir", str(run))
    record("corrupt.check_name_outside_enum_exit3", p.returncode == 3 and "R6" in p.stdout, p.stdout[-300:])

    r = valid_review()
    r["verdict"] = "pass"
    r["blocking_issues"] = ["red line 14: manifest mismatch"]
    write_review(run, r)
    p = run_gate("--run-dir", str(run))
    record("corrupt.pass_with_blockers_exit3", p.returncode == 3 and "R7" in p.stdout, p.stdout[-300:])


# ── case 4: schema agreement (gate enum == schema enum) ─────────────────────
def case_schema_agreement():
    schema = json.loads((SCHEMAS / "html_review_schema.json").read_text(encoding="utf-8"))
    enum = schema["properties"]["checks"]["items"]["properties"]["name"]["enum"]
    record("schema.check_enum_matches_gate", sorted(enum) == sorted(CHECK_NAMES),
           f"schema={sorted(enum)}")
    record("schema.required_matches_gate", schema["required"] ==
           ["verdict", "overall_score", "blocking_issues", "warnings", "checks"], str(schema["required"]))


CASES = {"valid": case_valid, "absent": case_absent, "corrupt": case_corrupt, "schema_agreement": case_schema_agreement}


def main():
    global TMP
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(CASES) if selector == "all" else ([selector] if selector in CASES else list(CASES))
    TMP = tempfile.mkdtemp(prefix="html_reviewer_gate_")
    try:
        for name in names:
            print(f"== {name} ==")
            CASES[name]()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(TMP, ignore_errors=True)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[TESTS] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
