#!/usr/bin/env python
"""Test runner for the industrial-analysis-enhance-auto quality gate (post-hoc
E0-E8 contract gate).

Usage (from repo root, inside the uv venv):

    uv run --project .claude/shared/scripts python \
        .claude/skills/industrial-analysis-enhance-auto/tests/run_tests.py [case|all]

Cases (fixtures generated on the fly into a temp dir):

  enh_fixture_ok        complete schema-valid E0-E8 artifact set -> gate exit 0
                        (exercises the imported orchestration_contract helpers:
                        reviewStatus/reviewIsPassing, resolveEnhancementStatus,
                        shouldBuildAssociationGraph, fileHash,
                        isFreshBySignature)
  enh_absent            no enhancement/ dir -> gate exit 2
  enh_status_absent     artifacts without the E8 marker -> gate exit 2
  enh_blocked           E0 recorded BLOCKED (baseline missing) -> gate exit 2
  enh_missing_marker    physics_bridge.json deleted -> gate exit 3
  enh_review_fail       review verdict=fail with blocking issues -> gate exit 3
  enh_corrupt_marker    enhanced_knowledge.json truncated -> gate exit 3
  enh_status_drift      recorded READY while knowledge says FAILED -> gate exit 3
  enh_graph_missing     association_graph.json deleted -> gate exit 3 (C5)
  enh_baseline_hash     cleaned_data.csv changed after the manifest -> exit 3 (C6)
  enh_stale_signature   recorded signature input changed -> exit 3 (C7)
  enh_schema_invalid    enhanced_knowledge.json missing a required key -> exit 3 (C8)
  enh_unreadable_status corrupt E8 marker -> gate exit 1
  enh_bad_args          no --run-dir -> gate exit 1

Exit 0 iff every assertion passes.
"""

from __future__ import annotations

import hashlib
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

TMP = Path(tempfile.mkdtemp(prefix="enh_auto_gate_tests_"))
RESULTS: list[tuple[str, bool, str]] = []

CLEANED = "02_processed/cleaned_data.csv"


class CaseAbort(Exception):
    """Prerequisite failed — abort this case, keep the battery running."""


def record(case: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def require(cond: bool, case: str, detail: str = "") -> None:
    if not cond:
        record(case, False, detail)
        raise CaseAbort(case)


def gate(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["node", str(GATE), "--run-dir", str(run_dir)],
                          capture_output=True, text=True, timeout=180, shell=False)


def gate_json(r: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_run_dir(name: str) -> Path:
    """Complete, schema-faithful enhanced run dir: every E0-E8 marker present,
    knowledge READY and schema-valid, review passing, manifest hash matching
    and one fresh signature sidecar."""
    run = TMP / name
    cleaned = run / CLEANED
    cleaned.parent.mkdir(parents=True, exist_ok=True)
    cleaned.write_text("ts,pressure_bar,temp_c\n2025-01-01 00:00:00,10,60\n"
                       "2025-01-01 00:01:00,10.1,60.1\n2025-01-01 00:02:00,10.2,60.2\n",
                       encoding="utf-8")
    feature_summary = run / "02_processed" / "feature_summary.json"
    write_json(feature_summary, {"columns": ["ts", "pressure_bar", "temp_c"]})
    csv_hash = sha256(cleaned)

    enh = run / "enhancement"
    write_json(enh / "enhancement_manifest.json", {
        "run_id": f"enhance-{name}",
        "baseline_run_dir": str(run),
        "input_mode": "B_existing_run",
        "data_source": {"file": "cleaned_data.csv", "original_path": None,
                        "sha256": csv_hash, "rows": 3, "cols": 3},
        "enhancement_version": "1.0.0",
        "created_at": "2026-01-01T00:00:00.000Z",
    })
    write_json(enh / "analysis_coverage.json", {
        "run_id": name,
        "columns": [{"column": c, "role": "process", "coverage_status": "covered_primary",
                     "unit": "dimensionless", "n_total": 3, "n_steady": 3,
                     "support_domain": {"n": 3}, "physics_ref": "NOT_APPLICABLE",
                     "reason": "directly analyzed"}
                    for c in ("ts", "pressure_bar", "temp_c")],
    })
    write_json(enh / "derived_features.json", {"run_id": name, "features": []})
    (enh / "derived_data.csv").write_text("ts,regime_steady\n2025-01-01 00:00:00,1\n",
                                          encoding="utf-8")
    write_json(enh / "deep_data_analysis.json", {
        "run_id": name,
        "relationships": [{"predictor": "pressure_bar", "target": "temp_c", "q_value": 0.04,
                           "operability": "LEVER_OBSERVATIONAL"}],
        "tradeoff_and_operability": [{"parameter": "pressure_bar",
                                      "operability_assessment": "LEVER_OBSERVATIONAL"}],
    })
    write_json(enh / "association_graph.json", {
        "run_id": name, "n_nodes": 2, "n_edges": 1,
        "nodes": [{"id": "pressure_bar", "role": "process"},
                  {"id": "temp_c", "role": "quality"}],
        "edges": [{"source": "pressure_bar", "target": "temp_c",
                   "relationship": "supports", "strength": 0.4, "sign": "+",
                   "confidence": 0.6, "causal_ceiling": "temporal_precedence",
                   "ontology_contradiction": False, "statistical_evidence": {}}],
        "metadata": {"built_by": "test-fixture"},
    })
    write_json(enh / "physics_bridge.json", {"run_id": name, "mechanisms": []})
    write_json(enh / "enhanced_knowledge.json", {
        "run_id": name,
        "enhancement_status": "READY",
        "relationship_graph": {
            "nodes": [{"id": "pressure_bar", "label": "pressure", "type": "process"},
                      {"id": "temp_c", "label": "temperature", "type": "quality"}],
            "edges": [{"source": "pressure_bar", "target": "temp_c",
                       "relationship": "supports", "strength": 0.4, "sign": 1,
                       "confidence": 0.6, "causal_ceiling": "temporal_precedence",
                       "ontology_contradiction": False,
                       "operability": "LEVER_OBSERVATIONAL"}],
        },
        "mechanism_chains": [{"chain_id": "MC-1", "claim": "pressure raises temperature",
                              "confidence": "0.6"}],
        "tradeoff_matrix": [{"parameter": "pressure_bar", "controllability": "controllable",
                             "operability": "LEVER_OBSERVATIONAL"}],
        "operability_summary": "one observational lever",
        "open_questions": [{"question": "does it hold at scale?", "severity": "low"}],
        "evidence_gaps": [{"gap": "no high-pressure data", "severity": "medium"}],
        "provenance": {
            "source_artifacts": {"analysis_coverage": "enhancement/analysis_coverage.json",
                                 "derived_features": "enhancement/derived_features.json",
                                 "deep_data_analysis": "enhancement/deep_data_analysis.json",
                                 "physics_bridge": "enhancement/physics_bridge.json"},
            "data_source": {"file": "02_processed/cleaned_data.csv", "sha256": csv_hash,
                            "rows": 3, "cols": 3},
        },
    })
    (enh / "enhanced_analysis.md").write_text("## 0. 摘要\n\nREADY\n\n## 1. 覆盖\n",
                                              encoding="utf-8")
    (enh / "enhanced-analysis.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        + "<!-- enhanced visualization -->" * 60 + "</body></html>\n", encoding="utf-8")
    write_json(enh / "html_selfcheck.json", {"ok": True, "charts": 4})
    write_json(enh / "enhancement_html_review.json", {
        "verdict": "pass", "overall_score": 92, "blocking_issues": [],
        "warnings": [], "checks": [],
    })
    write_json(enh / "enhancement_status.json", {
        "status": "READY", "warnings": [], "run_id": f"enhance-{name}",
        "created_at": "2026-01-01T00:00:01.000Z",
        "artifact_paths": {}, "launch_results": [],
    })
    # one freshness sidecar: analysis_coverage recorded feature_summary.json as input
    write_json(Path(str(enh / "analysis_coverage.json") + ".signature.json"), {
        "scriptHash": "fixture-script-hash",
        "inputs": {str(feature_summary.resolve()): sha256(feature_summary)},
    })
    return run


def clone(src_run: Path, name: str) -> Path:
    """Copy a fixture run dir and re-point its signature sidecar's absolute
    input paths at the copy (the gate recomputes them from disk)."""
    dest = TMP / name
    shutil.copytree(src_run, dest)
    sig = Path(str(dest / "enhancement" / "analysis_coverage.json") + ".signature.json")
    if sig.exists():
        data = json.loads(sig.read_text(encoding="utf-8"))
        old, new = str(src_run.resolve()), str(dest.resolve())
        data["inputs"] = {
            (new + k[len(old):]) if k.startswith(old) else k: v
            for k, v in (data.get("inputs") or {}).items()
        }
        write_json(sig, data)
    return dest


# ── cases ──────────────────────────────────────────────────────────────

def case_fixture_ok() -> None:
    run = valid_run_dir("valid")
    r = gate(run)
    j = gate_json(r)
    record("enh_fixture_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-600:]}")
    record("enh_fixture_ok_verdict", j.get("verdict") == "ok", str(j)[:300])
    contract = j.get("contract") or {}
    record("enh_fixture_ok_contract", contract.get("recomputed_status") == "READY"
           and contract.get("review_status") == "pass"
           and contract.get("knowledge_status") == "READY",
           f"contract={contract}")
    record("enh_fixture_ok_freshness", any("freshness verified for 1" in n for n in j.get("notes", [])),
           f"notes={j.get('notes')}")


def case_absent() -> None:
    run = TMP / "absent"
    run.mkdir(parents=True, exist_ok=True)
    r = gate(run)
    record("enh_absent_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("enh_absent_verdict", gate_json(r).get("verdict") == "undetermined", r.stdout[-300:])


def case_status_absent() -> None:
    run = valid_run_dir("valid")
    partial = TMP / "status_absent"
    (partial / "enhancement").mkdir(parents=True, exist_ok=True)
    shutil.copy2(run / "enhancement" / "analysis_coverage.json",
                 partial / "enhancement" / "analysis_coverage.json")
    r = gate(partial)
    record("enh_status_absent_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("enh_status_absent_notes", any("analysis_coverage.json" in n for n in gate_json(r).get("notes", [])),
           r.stdout[-300:])


def case_blocked() -> None:
    run = valid_run_dir("valid")
    blocked = TMP / "blocked"
    (blocked / "enhancement").mkdir(parents=True, exist_ok=True)
    write_json(blocked / "enhancement" / "enhancement_status.json", {
        "status": "BLOCKED", "missing": ["04_diagnostics/diagnosis.json"],
        "created_at": "2026-01-01T00:00:00.000Z", "guidance": "run the baseline first",
    })
    r = gate(blocked)
    record("enh_blocked_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("enh_blocked_reason", "BLOCKED" in gate_json(r).get("reason", ""), r.stdout[-300:])


def case_missing_marker() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "missing_marker")
    (broken / "enhancement" / "physics_bridge.json").unlink()
    r = gate(broken)
    record("enh_missing_marker_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    fails = " ".join(gate_json(r).get("fails", []))
    record("enh_missing_marker_rule", "physics_bridge.json" in fails and "C3" in fails,
           f"expected M1 missing + recomputed FAILED: {fails[:300]}")


def case_review_fail() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "review_fail")
    write_json(broken / "enhancement" / "enhancement_html_review.json", {
        "verdict": "fail", "overall_score": 41,
        "blocking_issues": ["charts do not render"], "warnings": [], "checks": [],
    })
    r = gate(broken)
    record("enh_review_fail_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    fails = " ".join(gate_json(r).get("fails", []))
    record("enh_review_fail_rule", "C2" in fails and "C3" in fails,
           f"expected C2 review + C3 recomputed FAILED: {fails[:300]}")


def case_corrupt_marker() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "corrupt_marker")
    (broken / "enhancement" / "enhanced_knowledge.json").write_text('{"run_id": "x"',
                                                                   encoding="utf-8")
    r = gate(broken)
    record("enh_corrupt_marker_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("enh_corrupt_marker_rule", any("corrupt marker" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_status_drift() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "status_drift")
    kb = broken / "enhancement" / "enhanced_knowledge.json"
    data = json.loads(kb.read_text(encoding="utf-8"))
    data["enhancement_status"] = "FAILED"
    write_json(kb, data)
    r = gate(broken)
    record("enh_status_drift_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    fails = " ".join(gate_json(r).get("fails", []))
    record("enh_status_drift_rule", "C1" in fails and "C4" in fails,
           f"expected C1 knowledge + C4 drift: {fails[:300]}")


def case_graph_missing() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "graph_missing")
    (broken / "enhancement" / "association_graph.json").unlink()
    r = gate(broken)
    record("enh_graph_missing_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("enh_graph_missing_rule", any("C5" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_baseline_hash() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "baseline_hash")
    cleaned = broken / CLEANED
    cleaned.write_text(cleaned.read_text(encoding="utf-8") + "2025-01-01 00:03:00,10.3,60.3\n",
                       encoding="utf-8")
    r = gate(broken)
    record("enh_baseline_hash_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("enh_baseline_hash_rule", any("C6" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_stale_signature() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "stale_signature")
    fs = broken / "02_processed" / "feature_summary.json"
    data = json.loads(fs.read_text(encoding="utf-8"))
    data["columns"].append("later_added")
    write_json(fs, data)
    r = gate(broken)
    record("enh_stale_signature_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("enh_stale_signature_rule", any("C7" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_schema_invalid() -> None:
    run = valid_run_dir("valid")
    broken = clone(run, "schema_invalid")
    kb = broken / "enhancement" / "enhanced_knowledge.json"
    data = json.loads(kb.read_text(encoding="utf-8"))
    del data["provenance"]
    write_json(kb, data)
    r = gate(broken)
    record("enh_schema_invalid_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("enh_schema_invalid_rule", any("C8" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_unreadable_status() -> None:
    run = TMP / "unreadable_status"
    (run / "enhancement").mkdir(parents=True, exist_ok=True)
    (run / "enhancement" / "enhancement_status.json").write_text("{broken", encoding="utf-8")
    r = gate(run)
    record("enh_unreadable_status_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-300:]}")


def case_bad_args() -> None:
    r = subprocess.run(["node", str(GATE)], capture_output=True, text=True, timeout=60)
    record("enh_bad_args_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    r2 = subprocess.run(["node", str(GATE), "--run-dir", str(TMP / "nope")],
                        capture_output=True, text=True, timeout=60)
    record("enh_missing_run_dir_exit1", r2.returncode == 1, f"rc={r2.returncode} {r2.stdout[-200:]}")


CASES = {
    "enh_fixture_ok": case_fixture_ok,
    "enh_absent": case_absent,
    "enh_status_absent": case_status_absent,
    "enh_blocked": case_blocked,
    "enh_missing_marker": case_missing_marker,
    "enh_review_fail": case_review_fail,
    "enh_corrupt_marker": case_corrupt_marker,
    "enh_status_drift": case_status_drift,
    "enh_graph_missing": case_graph_missing,
    "enh_baseline_hash": case_baseline_hash,
    "enh_stale_signature": case_stale_signature,
    "enh_schema_invalid": case_schema_invalid,
    "enh_unreadable_status": case_unreadable_status,
    "enh_bad_args": case_bad_args,
}


def main(argv) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    names = list(CASES) if which == "all" else [k for k in CASES if which in k]
    if not names:
        print(f"no case matches {which!r}; known: {', '.join(CASES)}")
        return 2
    print(f"[gate-tests] enhance-auto quality gate — temp fixtures in {TMP}")
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
