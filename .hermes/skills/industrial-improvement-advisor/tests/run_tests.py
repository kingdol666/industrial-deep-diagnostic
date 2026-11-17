#!/usr/bin/env python
"""Test battery for industrial-improvement-advisor (T1-T12).

Hermetic: fixtures are COPIED into ``tests/.tmp_run_<pid>/`` before analysis so
the committed fixture inputs are never dirtied. The deterministic core runs
in-process; node steps (quality gate, JSON-schema validation) run as
subprocesses against the temporary copies only.

Usage: python tests/run_tests.py all [--keep]
Exit: 0 ALL GREEN / 1 failures
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS = SKILL_DIR / "scripts"
FIXTURES = TESTS_DIR / "fixtures"
REPO_ROOT = SKILL_DIR.parents[2]
sys.path.insert(0, str(SCRIPTS))

import numpy as np  # noqa: E402

import imacore  # noqa: E402
from imacore import _io, evidence, levers, actions, objective as obj  # noqa: E402
import improvement_analyzer  # noqa: E402

# Load OUR report_builder by path: the stability skill ships a same-named
# module that imacore's reuse path puts earlier on sys.path.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ima_report_builder", SCRIPTS / "report_builder.py")
report_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report_builder)

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))


def run_analyzer(run_dir):
    args = improvement_analyzer.build_parser().parse_args(
        ["analyze", "--run-dir", str(run_dir), "--store-dir", str(run_dir.parent / "_store")])
    return improvement_analyzer.run_analyze(args)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def node_gate(advisory_path, out_dir):
    gate = SKILL_DIR / "scripts" / "quality_gate.mjs"
    proc = subprocess.run([shutil.which("node") or "node", str(gate),
                           str(advisory_path), str(out_dir)],
                          capture_output=True, text=True, timeout=120)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_builder(run_dir):
    adv = run_dir / "advisory" / "advisory_actions.json"
    charts = run_dir / "advisory" / "charts.json"
    return report_builder.main(["--advisory", str(adv), "--charts", str(charts),
                                "--out", str(run_dir / "advisory")])


def main(argv):
    keep = "--keep" in argv
    stamp = f"{os.getpid()}_{int(time.time())}"
    work = TESTS_DIR / f".tmp_run_{stamp}"
    shutil.copytree(FIXTURES, work)
    store_dir = work / "_store"
    try:
        # ------------------------------------------------ T1 explicit pipeline
        explicit = work / "explicit"
        code = run_analyzer(explicit)
        rep = read_json(explicit / "advisory" / "advisory_actions.json")
        check("T1 explicit exit 0", code == 0, f"exit {code}")
        check("T1 status actionable", rep["status"] == "actionable", rep["status"])
        check("T1 has B action", any(a["grade"] == "B" for a in rep["actions"]))
        required_action_fields = ["action_id", "lever_param", "magnitude", "expected_gain",
                                  "evidence_refs", "mechanism_chain", "grade", "grade_reasons",
                                  "risk", "preconditions", "side_effects", "verification_plan",
                                  "rollback_condition", "advisory", "grade_inputs"]
        check("T1 action field completeness",
              all(all(k in a for k in required_action_fields) for a in rep["actions"]))
        ev = read_json(explicit / "02_evidence" / "dose_response.json")
        check("T1 evidence pairs recorded", len(ev.get("pairs") or []) >= 1)
        check("T1 objective_resolved present",
              (explicit / "advisory" / "objective_resolved.json").is_file())

        # AC3: pure observation never yields A
        check("T1 no A on observational data",
              all(a["grade"] != "A" for a in rep["actions"]))

        # ------------------------------------------- T2 full JSON-schema check
        validator = REPO_ROOT / ".claude" / "shared" / "scripts" / "validate.mjs"
        schema = SKILL_DIR / "schemas" / "advisory_actions.schema.json"
        proc = subprocess.run([shutil.which("node") or "node", str(validator), str(schema),
                               str(explicit / "advisory" / "advisory_actions.json")],
                              capture_output=True, text=True, timeout=120)
        check("T2 advisory_actions schema validates", proc.returncode == 0,
              (proc.stdout or proc.stderr)[:300])

        # -------------------------------------------- T3 builder + gate + html
        bcode = run_builder(explicit)
        check("T3 builder exit 0", bcode == 0, f"exit {bcode}")
        html = (explicit / "advisory" / "improvement_advisory.html").read_text(encoding="utf-8")
        for sec in ("sec-goal", "sec-roadmap", "sec-actions", "sec-evidence",
                    "sec-execution", "sec-data", "sec-footer"):
            check(f"T3 html section {sec}", f'id="{sec}"' in html)
        sc = read_json(explicit / "advisory" / "html_selfcheck.json")
        check("T3 html selfcheck pass", sc["checks"]["pass"] is True)
        gcode, gtext = node_gate(explicit / "advisory" / "advisory_actions.json",
                                 explicit / "advisory")
        check("T3 quality gate exit 0", gcode == 0, gtext[-300:])

        # ------------------------------------------ T4 tamper battery (3 cases)
        tamper_root = work / "_tamper"
        for case in ("grade", "ci", "ref"):
            d = tamper_root / case
            shutil.copytree(explicit / "advisory", d / "advisory")
            shutil.copytree(explicit / "02_evidence", d / "02_evidence")
            p = d / "advisory" / "advisory_actions.json"
            tampered = read_json(p)
            a0 = tampered["actions"][0]
            if case == "grade":
                a0["grade"] = "A"
            elif case == "ci":
                a0["expected_gain"]["ci95"][1] = float(a0["expected_gain"]["ci95"][1]) + 100.0
            else:
                a0["evidence_refs"] = [r for r in a0["evidence_refs"]
                                       if not str(r.get("finding_id", "")).startswith("dose:")]
            p.write_text(json.dumps(tampered, ensure_ascii=False, indent=2), encoding="utf-8")
            tcode, ttext = node_gate(p, d / "advisory")
            check(f"T4 tamper-{case} gate FAIL", tcode == 3, ttext[-200:])

        # --------------------------------------------- T5 nodeadtime fixture
        nodt = work / "nodeadtime"
        code = run_analyzer(nodt)
        rep = read_json(nodt / "advisory" / "advisory_actions.json")
        check("T5 nodeadtime exit 1", code == 1, f"exit {code}")
        check("T5 temporal degradation recorded",
              any(d["leg"] == "temporal_precedence" and d["status"] == "not_estimable"
                  for d in rep["degradations"]))
        check("T5 dead_time_missing flags on actions",
              all(a["grade_inputs"]["flags"]["dead_time_missing"] for a in rep["actions"]))
        check("T5 no A/B->A escalation under missing dead_time",
              all(a["grade"] != "A" for a in rep["actions"]))

        # ------------------------------------------- T6 inferred-goal fixture
        infer = work / "infer"
        code = run_analyzer(infer)
        rep = read_json(infer / "advisory" / "advisory_actions.json")
        objres = read_json(infer / "advisory" / "objective_resolved.json")
        check("T6 infer exit 1", code == 1, f"exit {code}")
        check("T6 goal inferred", rep["goal"]["mode"] == "inferred")
        check("T6 objective_resolved inferred + candidates",
              objres["inferred"] is True and len(objres["candidates"]) >= 2)
        check("T6 inferred actions capped at B",
              all(a["grade"] in ("B", "C") for a in rep["actions"]))
        run_builder(infer)

        # ------------------------------------------------ T7 flat = no advice
        flat = work / "flat"
        code = run_analyzer(flat)
        rep = read_json(flat / "advisory" / "advisory_actions.json")
        check("T7 flat exit 2", code == 2, f"exit {code}")
        check("T7 flat not_actionable + prescriptions",
              rep["status"] == "not_actionable" and len(rep["prescriptions"]) >= 1)
        check("T7 flat zero actions", rep["actions"] == [])
        check("T7 flat no_variance exclusion",
              any(e["reason"] == "no_variance" for e in rep["excluded_levers"]))
        run_builder(flat)
        gcode, gtext = node_gate(flat / "advisory" / "advisory_actions.json",
                                 flat / "advisory")
        check("T7 not_actionable gate passes (exit-2 semantics)", gcode == 0, gtext[-200:])

        # -------------------------------------------- T8 reverse causality
        reverse = work / "reverse"
        run_analyzer(reverse)
        rep = read_json(reverse / "advisory" / "advisory_actions.json")
        check("T8 temp excluded reverse_causality",
              any(e["param"] == "temp" and e["reason"] == "reverse_causality"
                  for e in rep["excluded_levers"]))
        check("T8 no advice on excluded lever",
              all(a["lever_column"] != "temp" for a in rep["actions"]))

        # ----------------------------------------------- T9 goal conflicts
        conflict = work / "conflict"
        run_analyzer(conflict)
        rep = read_json(conflict / "advisory" / "advisory_actions.json")
        check("T9 conflicts declared", len(rep["goal"].get("conflicts") or []) >= 1)
        conflicted = {c["lever"] for c in rep["goal"].get("conflicts") or []}
        conflicted_actions = [a for a in rep["actions"] if a["lever_column"] in conflicted]
        check("T9 conflicted lever has actions (mechanism declared)",
              len(conflicted_actions) >= 1, f"actions={len(rep['actions'])}")
        check("T9 conflicted-lever actions capped at C",
              all(a["grade"] == "C" for a in conflicted_actions))

        # ------------------------- T13 line-memory strong consensus exclusion
        mem = work / "memory_conflict"
        shutil.copytree(explicit, mem)
        for d in ("advisory", "02_evidence", "01_ontology", "06_experience"):
            p = mem / d
            if p.exists():
                shutil.rmtree(p)
        ctx_dir = mem / "00_input" / "context"
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "line_memory.json").write_text(json.dumps({
            "line_key": "explicit",
            "entries": [{"subject": "speed", "claim_type": "improvement_action",
                         "grade": "consensus", "stale": False,
                         "directions": [{"direction": "up", "independent": 3}]}],
        }, ensure_ascii=False), encoding="utf-8")
        code = run_analyzer(mem)
        rep = read_json(mem / "advisory" / "advisory_actions.json")
        check("T13 memory consensus evicts opposing advice",
              all(a["lever_column"] != "speed" for a in rep["actions"]))
        check("T13 memory conflict prescription recorded",
              any(pr["kind"] == "data" and "产线记忆" in pr["detail"]
                  for pr in rep["prescriptions"]), str(rep["prescriptions"])[:200])
        check("T13 memory conflict exits 2 (not_actionable)", code == 2, f"exit {code}")

        # ------------------------------------------------ T10 determinism
        explicit2 = work / "explicit_rerun"
        shutil.copytree(work / "explicit", explicit2)
        for d in ("advisory", "02_evidence", "01_ontology", "06_experience"):
            p = explicit2 / d
            if p.exists():
                shutil.rmtree(p)
        run_analyzer(explicit2)
        rep2 = read_json(explicit2 / "advisory" / "advisory_actions.json")
        rep1 = read_json(explicit / "advisory" / "advisory_actions.json")
        ids1 = [a["action_id"] for a in rep1["actions"]]
        ids2 = [a["action_id"] for a in rep2["actions"]]
        gains1 = [a["expected_gain"]["point"] for a in rep1["actions"]]
        gains2 = [a["expected_gain"]["point"] for a in rep2["actions"]]
        check("T10 deterministic action ids", ids1 == ids2, f"{ids1} vs {ids2}")
        check("T10 deterministic gains", gains1 == gains2, f"{gains1} vs {gains2}")

        # ------------------------------------- T11 enums dual-end consistency
        enums = read_json(REPO_ROOT / ".claude" / "shared" / "schemas"
                          / "closedloop_enums.json")["improvement_advisor"]
        from closedloop_common.enums import (IMPROVEMENT_GRADES, IMPROVEMENT_STATUS,
                                             IMPROVEMENT_CONSTANTS)
        check("T11 enums grades mirror", IMPROVEMENT_GRADES == enums["grades"])
        check("T11 enums status mirror", IMPROVEMENT_STATUS == enums["status"])
        check("T11 enums constants mirror", IMPROVEMENT_CONSTANTS == enums["constants"])

        # --------------------------------- T12 not-estimable honesty (unit)
        gi = {"data": {"lever_variance_ok": True, "samples_ok": True,
                       "temporal_ok": None, "fdr_ok": True, "confound_ok": True,
                       "regime_stable_ok": True},
              "physics": {"status": "known"},
              "attribution": {"status": "estimable", "ci_excludes_zero": True},
              "flags": {"gain_ci_excludes_zero": True}}
        check("T12 grade_from_inputs B when temporal None", actions.grade_from_inputs(gi) == "B")
        gi_a = json.loads(json.dumps(gi))
        gi_a["data"]["temporal_ok"] = True
        gi_a["flags"].update({"objective_inferred": False, "conflict": False,
                              "extrapolated": False, "dead_time_missing": False,
                              "tradeoff_declared": False})
        check("T12 grade_from_inputs A when intervention+temporal", actions.grade_from_inputs(gi_a) == "A")
        gain = actions.compute_gain(None, None, None, 1, 1.0, None)
        check("T12 all legs absent -> method none + nulls",
              gain["method"] == "none" and gain["point"] is None
              and gain["not_estimable_reason"] == "reuse_leg_unavailable")
        check("T12 reuse status recorded", isinstance(_io.REUSE_STATUS, dict))
        check("T12 target equality means no direction",
              obj.required_lever_sign("target", 0.01, current=13.0,
                                      target_value=13.0) == 0)
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
        else:
            print(f"[keep] temp run dir: {work}")

    failures = [r for r in RESULTS if not r[1]]
    print(f"\n{'ALL GREEN' if not failures else 'FAILURES: ' + str(len(failures))} "
          f"({len(RESULTS) - len(failures)}/{len(RESULTS)} passed)")
    if failures:
        for name, _, detail in failures:
            print(f"  FAIL {name} {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
