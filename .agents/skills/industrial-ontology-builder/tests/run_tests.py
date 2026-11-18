#!/usr/bin/env python
"""Test runner for the industrial-ontology-builder quality gate (CP-2/CP-3).

Usage (from repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-ontology-builder/tests/run_tests.py [case|all]

(stdlib only — plain `python` works too if the shared venv is not needed)

Cases (fixtures generated on the fly into a temp dir; nothing large committed):
  T1  well-formed run (ontology + rag + CP-3 + hetero contract merged) -> exit 0
  T1b minimal valid run (no rag, no hetero contract)                   -> exit 0
  T2  run dir without 01_ontology (stage did not run)                  -> exit 2
  T3a 01_ontology present but ontology.json missing                    -> exit 3
  T3b ontology.json schema-invalid under BOTH ontology schemas         -> exit 3
  T3c ontology.json unparseable                                        -> exit 3
  T3d HX column present with physical_meaning_confidence=UNKNOWN       -> exit 3
  T3e HX contract column absent from the ontology (merge skipped)      -> exit 3
  T3f clarification_status missing / wrong (CP-3 violated)             -> exit 3
  T3g rag_deep_understanding.json unparseable                          -> exit 3
  T4  run dir does not exist (bad input)                               -> exit 1

Every gate invocation must emit a machine-readable JSON verdict on stdout.
Exit 0 iff all checks pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
GATE = SKILL / "scripts" / "quality_gate.mjs"

RESULTS = []


class CaseAbort(Exception):
    """Prerequisite failed — abort this case, keep the battery running."""


def require(cond, case, detail=""):
    if not cond:
        record(case, False, detail)
        raise CaseAbort(case)


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def run_gate(run_dir):
    return subprocess.run(["node", str(GATE), "--run-dir", str(run_dir)],
                          capture_output=True, text=True, timeout=120, shell=False)


def parse_verdict(proc, case):
    try:
        return json.loads(proc.stdout)
    except Exception as e:
        record(case, False, f"stdout is not JSON: {e}; stdout={proc.stdout[:200]!r}; stderr={proc.stderr[:200]!r}")
        raise CaseAbort(case)


# ---------------------------------------------------------------- fixture builders

def good_ontology():
    """Canonical v6.4 form: satisfies the CP-2 skill schema (and the shared
    domain-agnostic schema's anyOf scene+signals branch). >1KB by content."""
    long_meaning = (
        "reactor jacket coolant temperature measured at the outlet header; "
        "governs the heat-removal rate of the exothermic hydrogenation reaction"
    )
    return {
        "ontology_version": "6.4.0",
        "created_at": None,
        "scene": {
            "name": "test_cstr_scene",
            "process_type": "catalytic_hydrogenation",
            "equipment": [
                {"id": "R-101", "name": "CSTR reactor", "type": "stirred tank",
                 "function": "catalytic hydrogenation", "location": "line-1"}
            ],
            "stages": [
                {"id": "S1", "name": "reaction", "sequence": 1,
                 "typical_duration": "45 min", "key_physics": "Arrhenius kinetics"},
                {"id": "S2", "name": "separation", "sequence": 2,
                 "typical_duration": "20 min", "key_physics": "flash equilibrium"},
            ],
            "objectives": ["maximize product purity while holding reactor temperature in range"],
        },
        "signals": {
            "inspection_signals": [
                {"name": "product purity", "column": "product_purity", "role": "target",
                 "unit": "%", "physical_meaning": "offline GC purity of the product stream",
                 "target": 98.0, "tolerance": 0.5},
            ],
            "process_parameters": [
                {"name": "reactor temperature", "column": "reactor_temp", "role": "predictor",
                 "unit": "C", "physical_meaning": "temperature of the reacting mixture in R-101",
                 "physical_meaning_confidence": "KNOWN",
                 "governing_law": "Arrhenius rate constant", "normal_range": [60.0, 80.0]},
                {"name": "jacket coolant temperature", "column": "coolant_temp", "role": "predictor",
                 "unit": "C", "physical_meaning": long_meaning,
                 "physical_meaning_confidence": "KNOWN", "normal_range": [20.0, 40.0]},
                {"name": "HX reactor mean temperature", "column": "HX-PROF-REACTOR-MEAN",
                 "role": "predictor", "unit": "C",
                 "physical_meaning": "time-mean of the reactor temperature profile source (HX derived)",
                 "physical_meaning_confidence": "KNOWN",
                 "auto_inferred": False, "inference_basis": "07_hetero/column_contract.json mapping",
                 "derived": {"formula": "mean(profile)", "method": "profile_mean",
                             "n_inputs": 12, "model_derived": False},
                 "knowledge_source": "user_provided"},
            ],
            "control_variables": [
                {"name": "feed ratio SP", "column": "feed_ratio_sp", "role": "control",
                 "unit": "-", "physical_meaning": "setpoint of the feed ratio controller",
                 "control_type": "setpoint", "setpoint": 1.05},
            ],
            "events": [
                {"name": "operator note event", "column": "HX-TXT-OPNOTE01-EVT-BATCH",
                 "description": "operator handover note window (0/1, forward-only expiry)",
                 "event_values": [0, 1], "event_meanings": {"0": "no", "1": "operator note active"}},
            ],
            "metadata_columns": [],
        },
        "relationships": [
            {"from": "reactor_temp", "to": "product_purity", "type": "causal",
             "strength": "strong", "direction": "forward",
             "mechanism": "higher reactor temperature accelerates conversion until selectivity drops",
             "governing_equation": "k = A exp(-Ea/RT)",
             "predicted_functional_form": "threshold", "data_direction_validated": "true",
             "lag_detection_method": "ccf_peak", "lag_agreement": "consistent"},
            {"from": "coolant_temp", "to": "reactor_temp", "type": "physical",
             "strength": "moderate", "direction": "reverse",
             "mechanism": "jacket heat removal lowers the reactor temperature",
             "governing_equation": "Q = U A dT_lm", "data_direction_validated": "true"},
        ],
        "confounders": [
            {"variable": "ambient_temperature", "why": "shifts jacket coolant inlet temperature",
             "controlled": False},
        ],
        "parameter_groups": {"thermal": ["reactor_temp", "coolant_temp"]},
        "metadata": {
            "units": {"reactor_temp": "C", "coolant_temp": "C", "product_purity": "%"},
            "sampling_rate": "1 min", "timezone": "Asia/Shanghai",
        },
    }


def good_contract():
    """Minimal column contract: one PROF column (merged with KNOWN) + one TXT
    event column (deterministic events mapping omits the confidence field)."""
    def col(name, **kw):
        base = {"column": name, "shape": "PROF", "source_id": "SRC1",
                "source_path": "data/profile.csv", "source_sha256": "sha256:test",
                "unit": "C", "role": "predictor_candidate",
                "physical_meaning": "test column physical meaning",
                "formula": "mean(profile)", "physics_basis": "energy balance",
                "evidence_level": 3, "evidence_level_basis": "derived measurement",
                "method": "profile_mean", "method_version": "1.0",
                "n_inputs": 12, "coverage": 1.0, "effective_n": 12, "sparse": False,
                "stats_eligible": True, "cadence_s": 60, "ts_source": "anchor",
                "tz": "Asia/Shanghai", "tag_cn": "测试列", "tag_en": name,
                "model_derived": False, "insufficient_data": False}
        base.update(kw)
        return base
    return {
        "contract_version": "hetero-features/1.1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "anchor_sha256": "sha256:anchor",
        "columns": [
            col("HX-PROF-REACTOR-MEAN"),
            col("HX-TXT-OPNOTE01-EVT-BATCH", shape="TXT", unit=None,
                role="metadata", model_derived= False,
                physical_meaning="operator handover note event window (text source)",
                formula="event_window(operator_note)", evt_window_s=3600),
        ],
    }


def write_good_run(root, with_rag=True, with_contract=True):
    (root / "01_ontology").mkdir(parents=True, exist_ok=True)
    (root / "00_input").mkdir(parents=True, exist_ok=True)
    (root / "01_ontology" / "ontology.json").write_text(
        json.dumps(good_ontology(), ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "01_ontology" / "schema.json").write_text(
        json.dumps({"version": "1.0", "signals": {"targets": ["product_purity"]}}, indent=2), encoding="utf-8")
    if with_rag:
        (root / "01_ontology" / "rag_deep_understanding.json").write_text(
            json.dumps({"claims": [], "validation_queue": []}, indent=2), encoding="utf-8")
    (root / "00_input" / "clarification_needed.json").write_text(
        json.dumps({"clarification_status": "AUTO_RESOLVED", "source": "test"}, indent=2), encoding="utf-8")
    if with_contract:
        (root / "07_hetero").mkdir(parents=True, exist_ok=True)
        (root / "07_hetero" / "column_contract.json").write_text(
            json.dumps(good_contract(), ensure_ascii=False, indent=2), encoding="utf-8")
    return root


TMP_ROOT = None


def case_dir(name):
    d = Path(tempfile.mkdtemp(prefix=f"onto_gate_{name}_", dir=TMP_ROOT))
    return d


# ---------------------------------------------------------------- cases

def case_t1():
    print("[T1] well-formed run (ontology + rag + CP-3 + hetero merge) -> exit 0")
    d = write_good_run(case_dir("good_full"))
    # fixture self-check: the ontology must clear the CP-2 1KB floor
    size = (d / "01_ontology" / "ontology.json").stat().st_size
    require(size >= 1024, "T1_fixture_size_ge_1kb", f"fixture only {size} bytes")
    record("T1_fixture_size_ge_1kb", True, f"{size} bytes")
    p = run_gate(d)
    v = parse_verdict(p, "T1_verdict_json")
    record("T1_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T1_verdict_ok", v.get("verdict") == "ok", str(v.get("verdict")))
    record("T1_all_checks_pass", all(c["ok"] for c in v.get("checks", [])),
           str([c for c in v.get("checks", []) if not c["ok"]]))


def case_t1b():
    print("[T1b] minimal valid run (no rag file, no hetero contract) -> exit 0")
    d = write_good_run(case_dir("good_minimal"), with_rag=False, with_contract=False)
    p = run_gate(d)
    v = parse_verdict(p, "T1b_verdict_json")
    record("T1b_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T1b_notes_skip_hetero", any("O8 skipped" in n for n in v.get("notes", [])),
           str(v.get("notes")))


def case_t2():
    print("[T2] run dir without 01_ontology (stage did not run) -> exit 2")
    d = case_dir("no_stage")
    (d / "00_input").mkdir(parents=True)
    p = run_gate(d)
    v = parse_verdict(p, "T2_verdict_json")
    record("T2_exit2", p.returncode == 2, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T2_verdict_undetermined", v.get("verdict") == "undetermined", str(v.get("verdict")))
    record("T2_reason_stage", "01_ontology" in str(v.get("reason", "")), str(v.get("reason")))


def case_t3a():
    print("[T3a] 01_ontology present but ontology.json missing -> exit 3")
    d = write_good_run(case_dir("missing_artifact"))
    (d / "01_ontology" / "ontology.json").unlink()
    p = run_gate(d)
    v = parse_verdict(p, "T3a_verdict_json")
    record("T3a_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3a_verdict_gate_fail", v.get("verdict") == "gate_fail", str(v.get("verdict")))
    record("T3a_fail_is_O1", any(f.startswith("O1_ontology_exists") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3b():
    print("[T3b] ontology.json schema-invalid under BOTH schemas -> exit 3")
    d = write_good_run(case_dir("schema_invalid"))
    (d / "01_ontology" / "ontology.json").write_text(
        json.dumps({"ontology_version": "1.0"}), encoding="utf-8")  # no scene/signals/parameters
    p = run_gate(d)
    v = parse_verdict(p, "T3b_verdict_json")
    record("T3b_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3b_fail_is_O3", any(f.startswith("O3_ontology_schema_valid") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3c():
    print("[T3c] ontology.json unparseable -> exit 3")
    d = write_good_run(case_dir("unparseable"))
    (d / "01_ontology" / "ontology.json").write_text('{"scene": {  broken', encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3c_verdict_json")
    record("T3c_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3c_fail_is_O2", any(f.startswith("O2_ontology_parses") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3d():
    print("[T3d] HX column with physical_meaning_confidence=UNKNOWN -> exit 3")
    d = write_good_run(case_dir("hx_unknown"))
    ont = json.loads((d / "01_ontology" / "ontology.json").read_text(encoding="utf-8"))
    for sig in ont["signals"]["process_parameters"]:
        if sig.get("column") == "HX-PROF-REACTOR-MEAN":
            sig["physical_meaning_confidence"] = "UNKNOWN"
    (d / "01_ontology" / "ontology.json").write_text(
        json.dumps(ont, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3d_verdict_json")
    record("T3d_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3d_fail_is_O8", any(f.startswith("O8_hetero_merge") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3d_mentions_UNKNOWN", any("UNKNOWN" in f for f in v.get("fails", [])), str(v.get("fails")))


def case_t3e():
    print("[T3e] HX contract column absent from the ontology -> exit 3")
    d = write_good_run(case_dir("hx_missing"))
    contract = json.loads((d / "07_hetero" / "column_contract.json").read_text(encoding="utf-8"))
    contract["columns"].append({
        "column": "HX-PROF-ABSENT01-MEAN", "shape": "PROF", "source_id": "SRC2",
        "role": "predictor_candidate", "unit": "mm", "stats_eligible": True,
    })
    (d / "07_hetero" / "column_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3e_verdict_json")
    record("T3e_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3e_fail_is_O8_absent", any("absent" in f or "O8_hetero_merge" in f for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3f():
    print("[T3f] clarification_status missing / wrong (CP-3) -> exit 3")
    d = write_good_run(case_dir("cp3_bad"))
    (d / "00_input" / "clarification_needed.json").write_text(
        json.dumps({"clarification_status": "PENDING", "questions": []}, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3f_verdict_json")
    record("T3f_exit3_wrong_status", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3f_fail_is_O7", any(f.startswith("O7_clarification_status") for f in v.get("fails", [])),
           str(v.get("fails")))

    d2 = write_good_run(case_dir("cp3_missing_file"))
    (d2 / "00_input" / "clarification_needed.json").unlink()
    p2 = run_gate(d2)
    record("T3f_exit3_missing_file", p2.returncode == 3, f"rc={p2.returncode} {p2.stdout[-200:]}")


def case_t3g():
    print("[T3g] rag_deep_understanding.json unparseable -> exit 3")
    d = write_good_run(case_dir("rag_bad"))
    (d / "01_ontology" / "rag_deep_understanding.json").write_text("{ not json", encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3g_verdict_json")
    record("T3g_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3g_fail_is_O6", any(f.startswith("O6_rag_deep_understanding_parses") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t4():
    print("[T4] run dir does not exist (bad input) -> exit 1 hard error")
    missing = Path(TMP_ROOT) / "does_not_exist_run"
    p = run_gate(missing)
    v = parse_verdict(p, "T4_verdict_json")
    record("T4_exit1", p.returncode == 1, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T4_verdict_hard_error", v.get("verdict") == "hard_error", str(v.get("verdict")))


CASES = {
    "T1": case_t1,
    "T1b": case_t1b,
    "T2": case_t2,
    "T3a": case_t3a,
    "T3b": case_t3b,
    "T3c": case_t3c,
    "T3d": case_t3d,
    "T3e": case_t3e,
    "T3f": case_t3f,
    "T3g": case_t3g,
    "T4": case_t4,
}


def main(argv):
    global TMP_ROOT
    which = argv[1] if len(argv) > 1 else "all"
    TMP_ROOT = tempfile.mkdtemp(prefix="ontology_gate_tests_")
    t0 = time.time()
    require(GATE.exists(), "gate_exists", f"missing {GATE}")
    if which == "all":
        for name, fn in CASES.items():
            try:
                fn()
            except CaseAbort:
                print(f"  (case {name} aborted after prerequisite failure)")
    else:
        try:
            CASES[which]()
        except CaseAbort:
            pass

    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"\n{'=' * 62}")
    print(f"[RESULT] {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          f" in {time.time() - t0:.1f}s"
          + (f" — FAILED: {', '.join(failed)}" if failed else " — ALL GREEN"))
    shutil.rmtree(TMP_ROOT, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
