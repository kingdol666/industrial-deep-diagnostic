#!/usr/bin/env python
"""Test runner for the industrial-deep-analysis quality gate.

Usage (from repo root, inside the uv venv):

    uv run --project .claude/shared/scripts python \
        .claude/skills/industrial-deep-analysis/tests/run_tests.py [case|all]

Cases (fixtures generated on the fly into a temp dir; schema-faithful
synthetic E1-E4 artifacts, no pandas needed):

  da_fixture_ok        full synthetic E1-E4 artifact set -> gate exit 0 and
                       the delegation to verify_enhancement.py exits 0
  da_absent            run dir without enhancement artifacts -> gate exit 2
                       (the enhancement was not run for this run dir)
  da_partial           only analysis_coverage.json present -> gate exit 3
                       (ran but incomplete)
  da_missing_graph     association_graph.json removed -> gate exit 3 (A2)
  da_corrupt_json      analysis_coverage.json truncated -> gate exit 3
  da_rule_violation    coverage_status set to an illegal enum -> gate exit 3
                       with verify_enhancement.py's failing rule surfaced
                       (proves the delegation is wired, not just local checks)
  da_python_override   --python <interpreter> is honored for the delegation
  da_bad_args          no --run-dir -> gate exit 1

Exit 0 iff every assertion passes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]

GATE = SCRIPTS / "quality_gate.mjs"
VERIFIER = SCRIPTS / "verify_enhancement.py"

TMP = Path(tempfile.mkdtemp(prefix="deep_analysis_gate_tests_"))
RESULTS: list[tuple[str, bool, str]] = []


class CaseAbort(Exception):
    """Prerequisite failed — abort this case, keep the battery running."""


def record(case: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def require(cond: bool, case: str, detail: str = "") -> None:
    if not cond:
        record(case, False, detail)
        raise CaseAbort(case)


def gate(run_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(GATE), "--run-dir", str(run_dir), *extra],
        capture_output=True, text=True, timeout=180, shell=False)


def gate_json(r: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


COVERAGE_STATUSES = [
    "covered_primary", "covered_conditional", "pruned_physics",
    "pruned_confounded", "not_applicable", "insufficient_data", "derived_and_used",
]


def valid_run_dir(name: str) -> Path:
    """Build a schema-faithful synthetic run dir whose E1-E4 artifacts satisfy
    every rule in scripts/verify_enhancement.py."""
    run = TMP / name
    cols = ["ts", "pressure_bar", "temp_c"]

    write_json(run / "01_ontology" / "ontology.json",
               {"relationships": [{"from": "pressure_bar", "to": "temp_c"}]})
    write_json(run / "02_processed" / "feature_summary.json", {"columns": cols})
    (run / "02_processed").mkdir(parents=True, exist_ok=True)
    (run / "02_processed" / "cleaned_data.csv").write_text(
        ",".join(cols) + "\n" +
        "\n".join(f"2025-01-01 00:0{i}:00,{10 + i},{60 + i}" for i in range(3)) + "\n",
        encoding="utf-8")

    enh = run / "enhancement"
    write_json(enh / "analysis_coverage.json", {
        "run_id": name,
        "columns": [
            {"column": c, "role": "process", "coverage_status": "covered_primary",
             "unit": "dimensionless", "n_total": 3, "n_steady": 3,
             "support_domain": {"p50": 1.0, "n": 3}, "physics_ref": "NOT_APPLICABLE",
             "reason": "directly analyzed"}
            for c in cols
        ],
    })
    write_json(enh / "derived_features.json", {
        "run_id": name,
        "features": [{
            "name": "cumulative_pressure_bar_exposure", "status": "computed",
            "formula": "trapezoidal sum over sorted ts", "physics_basis": "exposure integral",
            "unit": "bar*h", "source_columns": ["pressure_bar"], "row_range": [0, 3],
            "mask": "all", "derived": True,
        }],
    })
    (enh / "derived_data.csv").write_text(
        "ts,cumulative_pressure_bar_exposure\n2025-01-01 00:00:00,0.0\n"
        "2025-01-01 00:01:00,0.2\n2025-01-01 00:02:00,0.4\n", encoding="utf-8")

    flags = {k: False for k in [
        "simpson_paradox_checked", "confounding_checked", "trend_confounding_checked",
        "change_point_tested", "batch_effect_tested", "lag_significant",
        "outlier_influence_checked", "insufficient_data"]}
    write_json(enh / "deep_data_analysis.json", {
        "run_id": name,
        "relationships": [{
            "predictor": "pressure_bar", "target": "temp_c",
            "global": {"r": 0.4, "p": 0.01}, "detrended": {"r": 0.3},
            "per_group": {}, "steady": {"r": 0.35}, "lag_aligned": {"lag": 2},
            "per_regime": {}, "slope_at_current": 0.5, "partial": {"r": 0.2},
            "partial_full": {"method": "partial_correlation", "partial_r": 0.2},
            "form_match": "monotone", "q_value": 0.04, "p_floor_hit": False,
            "n_effective": 3, "validity_flags": flags,
            "operability": "LEVER_OBSERVATIONAL",
        }],
        "tradeoff_and_operability": [{
            "parameter": "pressure_bar", "controllability": "controllable",
            "effects_on_targets": [{"target": "temp_c", "direction": "+"}],
            "tradeoff_summary": "raised pressure lifts temperature",
            "operability_assessment": "LEVER_OBSERVATIONAL",
            "support_domain": {"p5": 9.9, "p95": 10.1},
            "extrapolation_warning": "none within observed range",
            "open_questions": [],
        }],
    })
    write_json(enh / "association_graph.json", {
        "run_id": name, "n_nodes": 2, "n_edges": 1,
        "nodes": [{"id": "pressure_bar", "role": "process"},
                  {"id": "temp_c", "role": "quality"}],
        "edges": [{
            "source": "pressure_bar", "target": "temp_c",
            "relationship": "supports", "strength": 0.4, "sign": "+",
            "confidence": 0.6, "causal_ceiling": "temporal_precedence",
            "ontology_contradiction": False, "statistical_evidence": {"q": 0.04},
        }],
        "metadata": {"built_by": "test-fixture"},
    })
    return run


# ── cases ──────────────────────────────────────────────────────────────

def case_fixture_ok() -> None:
    run = valid_run_dir("valid")
    r = gate(run)
    j = gate_json(r)
    record("da_fixture_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-500:]}")
    record("da_fixture_ok_verdict", j.get("verdict") == "ok", str(j)[:300])
    record("da_fixture_ok_delegation", (j.get("delegation") or {}).get("ok") is True,
           f"delegation={j.get('delegation')}")
    record("da_fixture_ok_delegation_exit0", (j.get("delegation") or {}).get("exit_code") == 0,
           f"delegation={j.get('delegation')}")


def case_absent() -> None:
    run = TMP / "absent"
    run.mkdir(parents=True, exist_ok=True)
    r = gate(run)
    record("da_absent_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("da_absent_verdict", gate_json(r).get("verdict") == "undetermined", r.stdout[-300:])


def case_partial() -> None:
    run = valid_run_dir("valid")
    partial = TMP / "partial"
    (partial / "enhancement").mkdir(parents=True, exist_ok=True)
    shutil.copy2(run / "enhancement" / "analysis_coverage.json",
                 partial / "enhancement" / "analysis_coverage.json")
    r = gate(partial)
    record("da_partial_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")
    fails = " ".join(gate_json(r).get("fails", []))
    record("da_partial_names_missing", "derived_features.json" in fails and "association_graph.json" in fails,
           fails[:300])


def case_missing_graph() -> None:
    run = valid_run_dir("valid")
    broken = TMP / "missing_graph"
    shutil.copytree(run, broken)
    (broken / "enhancement" / "association_graph.json").unlink()
    r = gate(broken)
    record("da_missing_graph_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")
    record("da_missing_graph_rule", any("A2" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_corrupt_json() -> None:
    run = valid_run_dir("valid")
    broken = TMP / "corrupt_json"
    shutil.copytree(run, broken)
    (broken / "enhancement" / "analysis_coverage.json").write_text('{"run_id": "x", "columns": [{"col',
                                                                  encoding="utf-8")
    r = gate(broken)
    record("da_corrupt_json_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("da_corrupt_json_rule", any("A1" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_rule_violation() -> None:
    """Local shapes are fine; only verify_enhancement.py can catch this — proves
    the delegation actually runs and its verdict feeds the gate."""
    run = valid_run_dir("valid")
    broken = TMP / "rule_violation"
    shutil.copytree(run, broken)
    p = broken / "enhancement" / "analysis_coverage.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["columns"][0]["coverage_status"] = "bogus_status"
    write_json(p, data)
    r = gate(broken)
    j = gate_json(r)
    record("da_rule_violation_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("da_rule_violation_delegated", (j.get("delegation") or {}).get("ok") is False,
           f"delegation={j.get('delegation')}")
    notes = " ".join(j.get("notes", []))
    record("da_rule_violation_rule_named", "coverage_status" in notes,
           f"verifier rule must surface in notes: {notes[:300]}")


def case_python_override() -> None:
    run = valid_run_dir("valid")
    r = gate(run, "--python", sys.executable)
    j = gate_json(r)
    record("da_python_override_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-300:]}")
    record("da_python_override_used", "--python" in str((j.get("delegation") or {}).get("interpreter", "")),
           f"delegation={j.get('delegation')}")


def case_bad_args() -> None:
    r = subprocess.run(["node", str(GATE)], capture_output=True, text=True, timeout=60)
    record("da_bad_args_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    r2 = subprocess.run(["node", str(GATE), "--run-dir", str(TMP / "nope")],
                        capture_output=True, text=True, timeout=60)
    record("da_missing_run_dir_exit1", r2.returncode == 1, f"rc={r2.returncode} {r2.stdout[-200:]}")


CASES = {
    "da_fixture_ok": case_fixture_ok,
    "da_absent": case_absent,
    "da_partial": case_partial,
    "da_missing_graph": case_missing_graph,
    "da_corrupt_json": case_corrupt_json,
    "da_rule_violation": case_rule_violation,
    "da_python_override": case_python_override,
    "da_bad_args": case_bad_args,
}


def main(argv) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    names = list(CASES) if which == "all" else [k for k in CASES if which in k]
    if not names:
        print(f"no case matches {which!r}; known: {', '.join(CASES)}")
        return 2
    print(f"[gate-tests] deep-analysis quality gate — temp fixtures in {TMP}")
    for name in names:
        try:
            CASES[name]()
        except CaseAbort:
            print(f"  (case {name} aborted after prerequisite failure)")
        except Exception as e:
            record(name, False, f"EXCEPTION {type(e).__name__}: {e}")
    failed = [c for c, ok, _ in RESULTS if not ok]
    print("\n" + "=" * 62)
    print(f"[RESULT] {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f" — FAILED: {', '.join(failed)}" if failed else " — ALL GREEN"))
    if not failed:
        shutil.rmtree(TMP, ignore_errors=True)
    else:
        print(f"[gate-tests] failing fixtures kept for inspection: {TMP}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
