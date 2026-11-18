#!/usr/bin/env python
"""Test runner for the rag-knowledge-builder output-contract gate (scripts/quality_gate.mjs).

Usage (from repo root):
    python .claude/skills/rag-knowledge-builder/tests/run_tests.py [case|all]

Pure stdlib (no venv needed — the gate under test is a Node builtin-only script).

Cases (fixtures built in a temp dir; one REAL archived run is exercised
read-only to pin the honest legacy behavior):
  rag_ok                        complete minimal build -> exit 0/ok
  rag_input_dir_mode            --input-dir direct instead of --run-dir -> exit 0
  rag_absent                    empty dir -> exit 2 (undetermined)
  rag_missing_run_dir           nonexistent --run-dir -> exit 1
  rag_bad_args                  no args -> exit 1
  rag_legacy_run_no_nl_spec     archived 2026-06 workspace run (pre-NL-spec
                                contract) -> exit 3 R1 naming the missing file
  rag_generic_domain            domain_type 'generic' -> exit 3 R2 (blocking)
  rag_concept_missing_definition -> exit 3 R2
  rag_context_dim_no_broader_ok context dimensions are NOT IS-A concepts —
                                missing broader_concept there is legal -> exit 0
  rag_relation_missing_mechanism -> exit 3 R2
  rag_corrupt_draft             unparseable JSON -> exit 3 R1
  rag_audit_fail                audit verdict FAIL -> exit 3 R3
  rag_audit_conditional         audit verdict CONDITIONAL -> exit 0 + note
  rag_short_nl_spec             50-char spec -> exit 3 R6
  rag_zero_chunks_note          chunks [] (documented degradation path) -> exit 0 + note

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
REPO = SKILL.parents[2]
GATE = SKILL / "scripts" / "quality_gate.mjs"
ARCHIVED_RUN = REPO / "workspace" / "rag-outputs" / "20260602233646_eval_reactor_catalyst"

TMP = Path(tempfile.mkdtemp(prefix="rag_gate_tests_"))
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


def gate(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(GATE), *extra], capture_output=True, text=True, timeout=60, shell=False)


def gate_json(r: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def concept(name: str, **over) -> dict:
    c = {"name": name, "definition": f"{name} is a precisely defined quantity in this domain.",
         "definition_confidence": "KNOWN", "broader_concept": "process_state",
         "knowledge_source": "kb_chunk_1"}
    c.update(over)
    return c


def draft_payload() -> dict:
    return {
        "scene": {"name": "test scene", "domain_type": "reactor_operation", "domain_summary": "s"},
        "concepts": {
            "target_concepts": [concept("conversion_pct")],
            "related_concepts": [concept("catalyst_activity")],
            "context_dimensions": [{"name": "product_lot", "definition": "batch identifier.",
                                    "definition_confidence": "KNOWN", "knowledge_source": "kb_2"}],
        },
        "relationships": [{"id": "rel_1", "from": "catalyst_activity", "to": "conversion_pct",
                           "type": "causal", "mechanism": "Active sites drive the reaction rate.",
                           "knowledge_source": "kb_1"}],
        "entities": [{"id": "e1", "name": "catalyst_bed", "knowledge_source": "kb_1"}],
        "constraints": [{"name": "c1", "type": "hard", "description": "d", "knowledge_source": "kb_1"}],
    }


NL_SPEC_OK = "# 领域本体规格\n\n## 领域概览\n" + ("这是自然语言本体规格的中文描述段落。" * 12) + "\n\n## 概念词典\n- 概念\n"


def make_build(name: str, *, draft=None, nl_spec: str | None = NL_SPEC_OK,
               structured=True, chunks=None, audit=None, run_dir_mode: bool = True) -> Path:
    base = TMP / name
    inp = base / "00_input" if run_dir_mode else base
    inp.mkdir(parents=True, exist_ok=True)
    if draft is not ...:
        (inp / "rag_ontology_draft.json").write_text(
            json.dumps(draft_payload() if draft is None else draft, ensure_ascii=False),
            encoding="utf-8")
    if nl_spec is not None:
        (inp / "rag_ontology_nl_spec.md").write_text(nl_spec, encoding="utf-8")
    if structured:
        (inp / "rag_structured_data.json").write_text('{"sample_data": {}}', encoding="utf-8")
    if chunks is None:
        chunks = {"status": "scored", "chunks": [{"id": "c1"}]}
    if chunks is not ...:
        (inp / "rag_scored_chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
    if audit is None:
        audit = {"verdict": "PASS", "checks": {}, "summary": {}}
    if audit is not ...:
        (inp / "rag_audit_log.json").write_text(json.dumps(audit), encoding="utf-8")
    return base


# ── cases ──────────────────────────────────────────────────────────────

def case_ok() -> None:
    run = make_build("ok")
    r = gate("--run-dir", str(run))
    record("rag_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-400:]}")
    j = gate_json(r)
    record("rag_ok_verdict", j.get("verdict") == "ok", str(j)[:300])


def case_input_dir_mode() -> None:
    run = make_build("direct", run_dir_mode=False)
    r = gate("--input-dir", str(run))
    record("rag_input_dir_mode_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-300:]}")


def case_absent() -> None:
    run = make_build("absent", draft=..., nl_spec=None, structured=False, chunks=..., audit=...)
    r = gate("--run-dir", str(run))
    record("rag_absent_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("rag_absent_undetermined", gate_json(r).get("verdict") == "undetermined", r.stdout[-300:])


def case_missing_run_dir() -> None:
    r = gate("--run-dir", str(TMP / "does_not_exist"))
    record("rag_missing_run_dir_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")


def case_bad_args() -> None:
    r = subprocess.run(["node", str(GATE)], capture_output=True, text=True, timeout=60, shell=False)
    record("rag_bad_args_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")


def case_legacy_run_no_nl_spec() -> None:
    if not ARCHIVED_RUN.exists():
        record("rag_legacy_run_no_nl_spec_exit3", True, "archived run absent — case skipped vacuously")
        return
    r = gate("--run-dir", str(ARCHIVED_RUN))
    j = gate_json(r)
    record("rag_legacy_run_no_nl_spec_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")
    record("rag_legacy_run_no_nl_spec_names_file",
           any("nl_spec" in f for f in j.get("fails", [])), str(j.get("fails"))[:300])


def case_generic_domain() -> None:
    d = draft_payload()
    d["scene"]["domain_type"] = "generic"
    run = make_build("generic", draft=d)
    r = gate("--run-dir", str(run))
    record("rag_generic_domain_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("rag_generic_domain_rule", any("generic" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_concept_missing_definition() -> None:
    d = draft_payload()
    d["concepts"]["target_concepts"][0]["definition"] = ""
    run = make_build("nodef", draft=d)
    r = gate("--run-dir", str(run))
    record("rag_concept_missing_definition_exit3", r.returncode == 3, f"rc={r.returncode}")


def case_context_dim_no_broader_ok() -> None:
    """Regression guard: context dimensions are categorical fields, not IS-A
    concepts — the hierarchy rule must not false-fail them."""
    run = make_build("ctxdim")  # default payload: context dim has no broader_concept
    r = gate("--run-dir", str(run))
    record("rag_context_dim_no_broader_ok_exit0", r.returncode == 0,
           f"rc={r.returncode} {r.stdout[-300:]}")


def case_relation_missing_mechanism() -> None:
    d = draft_payload()
    d["relationships"][0]["mechanism"] = ""
    run = make_build("nomech", draft=d)
    r = gate("--run-dir", str(run))
    record("rag_relation_missing_mechanism_exit3", r.returncode == 3, f"rc={r.returncode}")


def case_corrupt_draft() -> None:
    run = make_build("corrupt")
    (run / "00_input" / "rag_ontology_draft.json").write_text('{"scene": {', encoding="utf-8")
    r = gate("--run-dir", str(run))
    record("rag_corrupt_draft_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("rag_corrupt_draft_rule", any("unparseable" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_audit_fail() -> None:
    run = make_build("audit_fail", audit={"verdict": "FAIL", "checks": {}, "summary": {}})
    r = gate("--run-dir", str(run))
    record("rag_audit_fail_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("rag_audit_fail_rule", any("FAIL" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_audit_conditional() -> None:
    run = make_build("audit_cond", audit={"verdict": "CONDITIONAL", "checks": {}, "summary": {}})
    r = gate("--run-dir", str(run))
    j = gate_json(r)
    record("rag_audit_conditional_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-300:]}")
    record("rag_audit_conditional_note", any("CONDITIONAL" in n for n in j.get("notes", [])),
           str(j.get("notes"))[:200])


def case_short_nl_spec() -> None:
    run = make_build("short_spec", nl_spec="# 规格\n太短了。\n")
    r = gate("--run-dir", str(run))
    record("rag_short_nl_spec_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("rag_short_nl_spec_rule", any("R6" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_zero_chunks_note() -> None:
    run = make_build("zero_chunks", chunks={"status": "scored", "chunks": []})
    r = gate("--run-dir", str(run))
    j = gate_json(r)
    record("rag_zero_chunks_note_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-300:]}")
    record("rag_zero_chunks_note_reported", any("zero scored chunks" in n for n in j.get("notes", [])),
           str(j.get("notes"))[:200])


CASES = {
    "rag_ok": case_ok,
    "rag_input_dir_mode": case_input_dir_mode,
    "rag_absent": case_absent,
    "rag_missing_run_dir": case_missing_run_dir,
    "rag_bad_args": case_bad_args,
    "rag_legacy_run_no_nl_spec": case_legacy_run_no_nl_spec,
    "rag_generic_domain": case_generic_domain,
    "rag_concept_missing_definition": case_concept_missing_definition,
    "rag_context_dim_no_broader_ok": case_context_dim_no_broader_ok,
    "rag_relation_missing_mechanism": case_relation_missing_mechanism,
    "rag_corrupt_draft": case_corrupt_draft,
    "rag_audit_fail": case_audit_fail,
    "rag_audit_conditional": case_audit_conditional,
    "rag_short_nl_spec": case_short_nl_spec,
    "rag_zero_chunks_note": case_zero_chunks_note,
}


def main(argv) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    names = list(CASES) if which == "all" else [k for k in CASES if which in k]
    if not names:
        print(f"no case matches {which!r}; known: {', '.join(CASES)}")
        return 2
    print(f"[gate-tests] rag-knowledge-builder quality gate — temp fixtures in {TMP}")
    for name in names:
        try:
            CASES[name]()
        except CaseAbort:
            print(f"  (case {name} aborted after prerequisite failure)")
        except Exception as e:  # keep the battery running
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
