#!/usr/bin/env python
"""Test runner for the industrial-physics-bridge quality gate (E5 artifacts).

Usage (from repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-physics-bridge/tests/run_tests.py [case|all]

(stdlib only — plain `python` works too if the shared venv is not needed)

Cases (fixtures generated on the fly into a temp dir; nothing committed):
  T1  well-formed run (schema-valid bridge + AC-2 ontology + diagnosis)  -> exit 0
  T1b minimal valid bridge (no diagnosis/ontology context files)         -> exit 0
  T2  enhancement/ dir absent (E-stage did not run)                      -> exit 2
  T3a enhancement/ present but physics_bridge.json missing               -> exit 3
  T3b physics_bridge.json unparseable                                    -> exit 3
  T3c physics_bridge.json schema-invalid (bad overall_status enum)       -> exit 3
  T3d five-item enum violation (direction="MATCHES")                     -> exit 3
  T3e direction=MISMATCH with overall_status != inconsistent             -> exit 3
  T3f mechanism-chain shortfall vs surviving hypotheses / duplicate ids  -> exit 3
  T3g AC-2 violation: data_direction_validated=false but direction=MATCH -> exit 3
  T4  run dir does not exist (bad input)                                 -> exit 1

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


# ---------------------------------------------------------------- fixtures

def base_bridge():
    return {
        "run_id": "test_run",
        "relationship_verifications": [
            {
                "predictor": "coolant_flow", "target": "product_purity",
                "direction": "MATCH", "functional_form": "MATCH", "time_lag": "MATCH",
                "magnitude": "PLAUSIBLE", "state_dependence": "STABLE",
                "overall_status": "consistent",
                "evidence_refs": ["deep_data.coolant_flow_to_product_purity.global_r=-0.87"],
            },
            {
                "predictor": "reactor_temp", "target": "product_purity",
                "direction": "MISMATCH", "functional_form": "MATCH", "time_lag": "UNTESTED",
                "magnitude": "IMPLAUSIBLE", "state_dependence": "STABLE",
                "overall_status": "inconsistent",
                "evidence_refs": ["ontology.reactor_temp_to_product_purity.mechanism"],
            },
        ],
        "mechanism_chains": [
            {
                "chain_id": "MC-001",
                "claim": "coolant flow shortfall lowers heat removal and purity",
                "evidence_refs": ["H1.numerical: jacket flow step -15%"],
                "physics_law": "Q = U A dT_lm",
                "data_support": "证据强度=强证据",
                "diagnosis_support": "hypothesis_id=H1, confidence=82, verdict=SURVIVING",
                "competing_explanations": ["H2 reactor-side fouling (EXCLUDED: no pressure signature)"],
                "what_would_change_conclusion": "jacket inlet temperature step without flow change",
            },
        ],
        "competing_explanations": [
            {
                "explanation": "Reactor-side fouling: no corresponding pressure-drop signature",
                "support_level": "Exclusion confidence: 80%",
                "against": ["no pressure-drop deviation in the window"],
                "resolution": "Excluded via TIME_ORDER reasoning. Revival condition: pressure-drop signature appears",
            },
        ],
        "evidence_gaps": [
            {
                "gap": "offline characterization of coolant fouling is unavailable",
                "severity": "major",
                "impact_on_conclusions": "limits precision of mechanism attribution",
                "mitigation": "targeted offline characterization",
            },
        ],
    }


def write_bridge(root, bridge=None, diagnosis=None, ontology=None, write=True):
    (root / "enhancement").mkdir(parents=True, exist_ok=True)
    if write:
        payload = bridge if bridge is not None else base_bridge()
        (root / "enhancement" / "physics_bridge.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if diagnosis is not None:
        (root / "04_diagnostics").mkdir(parents=True, exist_ok=True)
        (root / "04_diagnostics" / "diagnosis.json").write_text(
            json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    if ontology is not None:
        (root / "01_ontology").mkdir(parents=True, exist_ok=True)
        (root / "01_ontology" / "ontology.json").write_text(
            json.dumps(ontology, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


def base_diagnosis(n_surviving=1):
    return {
        "run_id": "test_run",
        "primary_finding": "coolant flow shortfall is the root cause",
        "hypotheses": {
            "surviving": [{"id": f"H{i + 1}", "name": f"hypothesis {i + 1}"} for i in range(n_surviving)],
            "eliminated": [{"hypothesis_id": "H2", "name": "reactor-side fouling",
                            "elimination_reason": "no pressure signature",
                            "exclusion_confidence": 80, "exclusion_type": "TIME_ORDER",
                            "specific_evidence": "pressure-drop deviation absent",
                            "revival_condition": "pressure-drop signature appears"}],
        },
    }


def base_ontology():
    return {
        "ontology_version": "6.4.0",
        "scene": {"name": "test", "process_type": "catalytic_hydrogenation"},
        "signals": {"inspection_signals": [], "process_parameters": [], "control_variables": [],
                    "events": [], "metadata_columns": []},
        "relationships": [
            {"from": "coolant_flow", "to": "product_purity", "type": "causal",
             "data_direction_validated": "true"},
            {"from": "reactor_temp", "to": "product_purity", "type": "causal",
             "data_direction_validated": "false"},
        ],
        "metadata": {},
    }


def case_dir(name):
    return Path(tempfile.mkdtemp(prefix=f"bridge_gate_{name}_", dir=TMP_ROOT))


# ---------------------------------------------------------------- cases

def case_t1():
    print("[T1] well-formed run (schema-valid bridge + AC-2 ontology + diagnosis) -> exit 0")
    d = write_bridge(case_dir("good"), diagnosis=base_diagnosis(1), ontology=base_ontology())
    p = run_gate(d)
    v = parse_verdict(p, "T1_verdict_json")
    record("T1_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-400:]}")
    record("T1_verdict_ok", v.get("verdict") == "ok", str(v.get("verdict")))
    record("T1_all_checks_pass", all(c["ok"] for c in v.get("checks", [])),
           str([c for c in v.get("checks", []) if not c["ok"]]))
    record("T1_counts", v.get("relationship_verifications") == 2 and v.get("mechanism_chains") == 1,
           f"rv={v.get('relationship_verifications')} mc={v.get('mechanism_chains')}")


def case_t1b():
    print("[T1b] minimal valid bridge (no diagnosis/ontology context) -> exit 0")
    empty = {"run_id": "test_run", "relationship_verifications": [], "mechanism_chains": [],
             "competing_explanations": [], "evidence_gaps": []}
    d = write_bridge(case_dir("minimal"), bridge=empty)
    p = run_gate(d)
    v = parse_verdict(p, "T1b_verdict_json")
    record("T1b_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-300:]}")
    notes = " ".join(v.get("notes", []))
    record("T1b_notes_context_missing", "B6 note" in notes and "B7 skipped" in notes, notes)


def case_t2():
    print("[T2] enhancement/ dir absent -> exit 2 (E-stage did not run)")
    d = case_dir("no_stage")
    (d / "04_diagnostics").mkdir(parents=True)
    p = run_gate(d)
    v = parse_verdict(p, "T2_verdict_json")
    record("T2_exit2", p.returncode == 2, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T2_verdict_undetermined", v.get("verdict") == "undetermined", str(v.get("verdict")))
    record("T2_reason_stage", "enhancement/" in str(v.get("reason", "")), str(v.get("reason")))


def case_t3a():
    print("[T3a] enhancement/ present but physics_bridge.json missing -> exit 3")
    d = write_bridge(case_dir("missing_artifact"), write=False)
    (d / "enhancement" / "deep_data_analysis.json").write_text(
        json.dumps({"relationships": [], "tradeoff_and_operability": []}), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3a_verdict_json")
    record("T3a_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3a_fail_is_B1", any(f.startswith("B1_bridge_exists") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3b():
    print("[T3b] physics_bridge.json unparseable -> exit 3")
    d = write_bridge(case_dir("unparseable"))
    (d / "enhancement" / "physics_bridge.json").write_text('{"run_id": "x", broken', encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3b_verdict_json")
    record("T3b_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3b_fail_is_B2", any(f.startswith("B2_bridge_parses") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3c():
    print("[T3c] schema-invalid bridge (bad overall_status enum) -> exit 3")
    d = write_bridge(case_dir("schema_invalid"))
    payload = base_bridge()
    payload["relationship_verifications"][0]["overall_status"] = "MAYBE"
    (d / "enhancement" / "physics_bridge.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3c_verdict_json")
    record("T3c_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3c_fail_is_B3", any(f.startswith("B3_schema_valid") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3d():
    print("[T3d] five-item enum violation (direction=\"MATCHES\") -> exit 3")
    d = write_bridge(case_dir("bad_enum"))
    payload = base_bridge()
    payload["relationship_verifications"][0]["direction"] = "MATCHES"
    (d / "enhancement" / "physics_bridge.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3d_verdict_json")
    record("T3d_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3d_fail_is_B4", any(f.startswith("B4_five_item_enums") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3e():
    print("[T3e] direction=MISMATCH with overall_status != inconsistent -> exit 3")
    d = write_bridge(case_dir("mismatch_status"))
    payload = base_bridge()
    payload["relationship_verifications"][1]["overall_status"] = "plausible"
    (d / "enhancement" / "physics_bridge.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3e_verdict_json")
    record("T3e_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3e_fail_is_B5", any(f.startswith("B5_mismatch_status_rule") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3f():
    print("[T3f] mechanism-chain shortfall vs surviving hypotheses / duplicate ids -> exit 3")
    # shortfall: 2 surviving hypotheses, 1 chain
    d = write_bridge(case_dir("chain_shortfall"), diagnosis=base_diagnosis(2), ontology=base_ontology())
    p = run_gate(d)
    v = parse_verdict(p, "T3f_verdict_json")
    record("T3f_shortfall_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3f_fail_is_B6", any(f.startswith("B6_mechanism_chains") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3f_mentions_AC2", any("AC-2" in f for f in v.get("fails", [])), str(v.get("fails")))

    # duplicate chain ids
    dumb = base_bridge()
    dumb["mechanism_chains"].append(dict(dumb["mechanism_chains"][0]))
    d2 = write_bridge(case_dir("chain_dup"), bridge=dumb, diagnosis=base_diagnosis(1))
    p2 = run_gate(d2)
    v2 = parse_verdict(p2, "T3f_dup_verdict_json")
    record("T3f_dup_exit3", p2.returncode == 3, f"rc={p2.returncode} {p2.stdout[-300:]}")
    record("T3f_dup_mentions_duplicate", any("duplicate chain_id" in f for f in v2.get("fails", [])),
           str(v2.get("fails")))


def case_t3g():
    print("[T3g] AC-2 violation: data_direction_validated=false but direction=MATCH -> exit 3")
    d = write_bridge(case_dir("ac2_violation"), diagnosis=base_diagnosis(1), ontology=base_ontology())
    payload = base_bridge()
    payload["relationship_verifications"][1]["direction"] = "MATCH"  # ontology says false
    payload["relationship_verifications"][1]["overall_status"] = "plausible"
    (d / "enhancement" / "physics_bridge.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3g_verdict_json")
    record("T3g_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3g_fail_is_B7", any(f.startswith("B7_ontology_direction_rule") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t4():
    print("[T4] run dir does not exist (bad input) -> exit 1 hard error")
    p = run_gate(Path(TMP_ROOT) / "no_such_run")
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
    TMP_ROOT = tempfile.mkdtemp(prefix="bridge_gate_tests_")
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
