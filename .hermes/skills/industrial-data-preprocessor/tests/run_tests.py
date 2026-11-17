#!/usr/bin/env python
"""Test runner for the E-1 quality gate (industrial-data-preprocessor).

Usage (from repo root, inside the uv venv — the runner needs pandas to execute
the real E-1 stage when generating fixtures):

    uv run --project .claude/shared/scripts python \
        .claude/skills/industrial-data-preprocessor/tests/run_tests.py [case|all]

Cases (fixtures generated on the fly into a temp dir; the run dirs are built by
executing the REAL E-1 stage with --output <RUN_DIR>/00_input, so the gate sees
authentic reports; nothing is committed):

  prep_ok_single       single clean CSV  -> real E-1 run -> gate exit 0
  prep_ok_merge        two CSVs sharing a time axis -> real E-1 merge -> gate
                       exit 0 (exercises the D6 merge-consistency checks)
  prep_ok_no_time      cross-sectional CSV without a time column -> gate exit 0
                       with a note (time-less data is a supported scenario;
                       D4 must never fail it)
  prep_ok_stability    --stability-single-primary folder mode (one primary
                       time series, single_primary_no_merge) -> gate exit 0
                       (regression guard for the documented stability policy)
  prep_absent          empty run dir -> gate exit 2 (E-1 did not run)
  prep_passthrough     real no_tabular_data run (documented passthrough
                       marker) -> gate exit 2, NOT 3 — this case encodes the
                       chosen exit-2-for-passthrough semantics
  prep_corrupt_csv     csv truncated after the stage ran -> gate exit 3
  prep_missing_report  csv present, audit deleted -> gate exit 3
  prep_corrupt_report  audit unparseable: with csv -> exit 3; without csv
                       -> exit 1 (hard error, stage identity undecidable)
  prep_outputs_escape  report.outputs/context_files tampered to point outside
                       00_input -> gate exit 3 (D7)
  prep_raw_unresolved  --raw-path does not contain the selected table
                       -> gate exit 3 (D5)
  prep_time_contract   declared time column absent from the header
                       -> gate exit 3 (D4)
  prep_bad_args        no --run-dir / missing run dir -> gate exit 1

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
SHARED = REPO / ".claude" / "shared"

PREPROCESSOR = SCRIPTS / "data_preprocessor.py"
GATE = SCRIPTS / "quality_gate.mjs"

TMP = Path(tempfile.mkdtemp(prefix="prep_gate_tests_"))
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
        capture_output=True, text=True, timeout=120, shell=False)


def gate_json(r: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.write_text(
        "\n".join([",".join(header)] + [",".join(r) for r in rows]) + "\n",
        encoding="utf-8")


def ts_rows(n: int, base_minute: int = 0, col: str = "x") -> tuple[list[str], list[list[str]]]:
    rows = []
    for i in range(n):
        m = base_minute + i
        rows.append([f"2025-03-01 {m // 60:02d}:{m % 60:02d}:00", f"{10 + 0.01 * i:.2f}"])
    return ["timestamp", col], rows


def make_run(name: str) -> Path:
    run = TMP / name
    (run / "00_input").mkdir(parents=True, exist_ok=True)
    return run


def run_preprocessor(data_path: Path, out_dir: Path, name: str, *extra: str) -> None:
    r = subprocess.run(
        [sys.executable, "-W", "ignore", str(PREPROCESSOR),
         "--data-path", str(data_path), "--output", str(out_dir), "--name", name, *extra],
        capture_output=True, text=True, timeout=300, shell=False)
    if r.returncode not in (0, 1):
        raise CaseAbort(f"E-1 crashed rc={r.returncode}: {r.stderr[-300:]}")


def build_single_run(name: str = "single", n: int = 120) -> tuple[Path, Path]:
    """Real E-1 run on a single clean CSV, written directly into RUN_DIR/00_input."""
    raw = TMP / f"raw_{name}"
    raw.mkdir(parents=True, exist_ok=True)
    header, rows = ts_rows(n, col="pressure_bar")
    write_csv(raw / "data.csv", header, rows)
    run = make_run(f"run_{name}")
    run_preprocessor(raw, run / "00_input", name)
    return run, raw


def clone(src_run: Path, name: str) -> Path:
    """Copy a fixture run dir and re-point the paths it recorded at itself
    (report.outputs / context_files / signature sidecars) at the copy."""
    dest = TMP / name
    shutil.copytree(src_run, dest)
    old, new = str(src_run.resolve()), str(dest.resolve())
    report_path = dest / "00_input" / "preprocessing_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if isinstance(report.get("outputs"), dict):
            report["outputs"] = {k: (new + v[len(old):]) if isinstance(v, str) and v.startswith(old) else v
                                 for k, v in report["outputs"].items()}
        if isinstance(report.get("context_files"), list):
            report["context_files"] = [(new + v[len(old):]) if isinstance(v, str) and v.startswith(old) else v
                                       for v in report["context_files"]]
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


# ── cases ──────────────────────────────────────────────────────────────

def case_ok_single() -> None:
    run, raw = build_single_run("single")
    r = gate(run, "--raw-path", str(raw))
    record("prep_ok_single_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-400:]}")
    j = gate_json(r)
    record("prep_ok_single_verdict", j.get("verdict") == "ok", str(j)[:300])
    record("prep_ok_single_rows", j.get("rows") == 120 and j.get("time_column") == "timestamp",
           f"rows={j.get('rows')} time={j.get('time_column')}")


def case_ok_merge() -> None:
    raw = TMP / "raw_merge"
    raw.mkdir(parents=True, exist_ok=True)
    for fname, col in (("a_export.csv", "flow_lph"), ("b_export.csv", "ph")):
        header = ["timestamp", col]
        rows = [[f"2025-02-01 {i // 60:02d}:{i % 60:02d}:00", f"{100 + 0.1 * i:.2f}"]
                for i in range(150)]
        write_csv(raw / fname, header, rows)
    run = make_run("run_merge")
    run_preprocessor(raw, run / "00_input", "merge")
    report = json.loads((run / "00_input" / "preprocessing_report.json").read_text(encoding="utf-8"))
    require(report.get("merge", {}).get("strategy") == "outer_merge_on_time_column",
            "prep_ok_merge_abort", f"merge not attempted: {report.get('merge')}")
    r = gate(run, "--raw-path", str(raw))
    record("prep_ok_merge_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-400:]}")
    record("prep_ok_merge_flag", gate_json(r).get("merged") is True, r.stdout[-300:])


def case_ok_no_time() -> None:
    raw = TMP / "raw_batch"
    raw.mkdir(parents=True, exist_ok=True)
    write_csv(raw / "batch.csv", ["batch_id", "grade", "yield_pct"],
              [[f"B{i:03d}", "A", f"{90 + (i % 7) * 0.5:.2f}"] for i in range(60)])
    run = make_run("run_batch")
    run_preprocessor(raw, run / "00_input", "batch")
    r = gate(run, "--raw-path", str(raw))
    record("prep_ok_no_time_exit0", r.returncode == 0,
           f"time-less cross-sectional data must not fail: rc={r.returncode} {r.stdout[-300:]}")
    j = gate_json(r)
    record("prep_ok_no_time_note", any("D4" in n for n in j.get("notes", [])),
           f"expected a D4 note, got {j.get('notes')}")


def case_ok_stability() -> None:
    """--stability-single-primary folder mode: one >=50-row time-series primary,
    merge.strategy single_primary_no_merge, single_primary_policy exclusions —
    the gate must pass this documented outcome (regression guard)."""
    raw = TMP / "raw_stability"
    raw.mkdir(parents=True, exist_ok=True)
    header, rows = ts_rows(80, col="melt_temp")
    write_csv(raw / "dcs_main.csv", header, rows)
    write_csv(raw / "maintenance_log.csv", ["timestamp", "event"],
              [["2025-03-01 00:10:00", "bearing repair"]])
    run = make_run("run_stability")
    run_preprocessor(raw, run / "00_input", "stab", "--stability-single-primary", "--recursive")
    report = json.loads((run / "00_input" / "preprocessing_report.json").read_text(encoding="utf-8"))
    require(report.get("status") == "ok"
            and (report.get("merge") or {}).get("strategy") == "single_primary_no_merge",
            "prep_ok_stability_abort",
            f"unexpected report: status={report.get('status')} merge={report.get('merge')}")
    r = gate(run, "--raw-path", str(raw))
    record("prep_ok_stability_exit0", r.returncode == 0,
           f"stability mode must not false-fail: rc={r.returncode} {r.stdout[-400:]}")


def case_absent() -> None:
    run = make_run("run_absent")
    r = gate(run)
    record("prep_absent_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-300:]}")
    record("prep_absent_verdict", gate_json(r).get("verdict") == "undetermined", r.stdout[-300:])


def case_passthrough_marker() -> None:
    """Documented passthrough semantics: csv absent + report.status
    no_tabular_data => exit 2 (the caller decides), never 3."""
    raw = TMP / "raw_notabular"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "notes.txt").write_text("free-text process notes, no table here\n", encoding="utf-8")
    run = make_run("run_notabular")
    run_preprocessor(raw, run / "00_input", "notabular")
    report = json.loads((run / "00_input" / "preprocessing_report.json").read_text(encoding="utf-8"))
    require(report.get("status") == "no_tabular_data"
            and not (run / "00_input" / "preprocessed_data.csv").exists(),
            "prep_passthrough_abort", f"unexpected stage outcome: {report.get('status')}")
    r = gate(run)
    record("prep_passthrough_exit2", r.returncode == 2,
           f"rc={r.returncode} (documented marker must map to undetermined, not fail) {r.stdout[-300:]}")
    reason = gate_json(r).get("reason", "")
    record("prep_passthrough_reason", "no_tabular_data" in reason, reason)


def case_corrupt_csv() -> None:
    run, raw = build_single_run("single")
    tampered = clone(run, "corrupt_csv")
    csv_path = tampered / "00_input" / "preprocessed_data.csv"
    lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
    csv_path.write_text("\n".join(lines[:10]) + "\n", encoding="utf-8")
    r = gate(tampered, "--raw-path", str(raw))
    record("prep_corrupt_csv_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    record("prep_corrupt_csv_rule", any("D3" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-400:])


def case_missing_report() -> None:
    run, _raw = build_single_run("single")

    a = clone(run, "missing_report")
    (a / "00_input" / "preprocessing_report.json").unlink()
    r = gate(a)
    record("prep_missing_report_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")

    b = clone(run, "corrupt_report")
    (b / "00_input" / "preprocessing_report.json").write_text('{"status": "ok", "quality"',
                                                             encoding="utf-8")
    r2 = gate(b)
    record("prep_corrupt_report_exit3", r2.returncode == 3, f"rc={r2.returncode} {r2.stdout[-300:]}")

    c = make_run("run_corrupt_report_no_csv")
    (c / "00_input" / "preprocessing_report.json").write_text("{not json", encoding="utf-8")
    r3 = gate(c)
    record("prep_corrupt_report_nocsv_exit1", r3.returncode == 1,
           f"rc={r3.returncode} {r3.stdout[-300:]}")


def case_outputs_escape() -> None:
    run, _raw = build_single_run("single")
    tampered = clone(run, "outputs_escape")
    rp = tampered / "00_input" / "preprocessing_report.json"
    report = json.loads(rp.read_text(encoding="utf-8"))
    report["outputs"]["preprocessed_data.csv"] = "../02_processed/preprocessed_data.csv"
    report["context_files"] = ["../leaked_context/notes.txt"]
    rp.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    r = gate(tampered)
    record("prep_outputs_escape_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-400:]}")
    fails = " ".join(gate_json(r).get("fails", []))
    record("prep_outputs_escape_rules",
           "outputs.preprocessed_data.csv" in fails and "context_files" in fails,
           f"both escapes must be caught: {fails[:300]}")


def case_raw_unresolved() -> None:
    run, _raw = build_single_run("single")
    other = TMP / "raw_other"
    other.mkdir(parents=True, exist_ok=True)
    write_csv(other / "different.csv", ["timestamp", "y"], [["2025-01-01 00:00:00", "1"]])
    r = gate(run, "--raw-path", str(other))
    record("prep_raw_unresolved_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")
    record("prep_raw_unresolved_rule", any("D5" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_time_contract() -> None:
    run, _raw = build_single_run("single")
    tampered = clone(run, "time_contract")
    rp = tampered / "00_input" / "preprocessing_report.json"
    report = json.loads(rp.read_text(encoding="utf-8"))
    report["quality"]["time_column"] = "not_a_column"
    rp.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    r = gate(tampered)
    record("prep_time_contract_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-300:]}")
    record("prep_time_contract_rule", any("D4" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-300:])


def case_bad_args() -> None:
    r = subprocess.run(["node", str(GATE)], capture_output=True, text=True, timeout=60)
    record("prep_bad_args_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    r2 = subprocess.run(["node", str(GATE), "--run-dir", str(TMP / "does_not_exist")],
                        capture_output=True, text=True, timeout=60)
    record("prep_missing_run_dir_exit1", r2.returncode == 1, f"rc={r2.returncode} {r2.stdout[-200:]}")


CASES = {
    "prep_ok_single": case_ok_single,
    "prep_ok_merge": case_ok_merge,
    "prep_ok_no_time": case_ok_no_time,
    "prep_ok_stability": case_ok_stability,
    "prep_absent": case_absent,
    "prep_passthrough": case_passthrough_marker,
    "prep_corrupt_csv": case_corrupt_csv,
    "prep_missing_report": case_missing_report,
    "prep_outputs_escape": case_outputs_escape,
    "prep_raw_unresolved": case_raw_unresolved,
    "prep_time_contract": case_time_contract,
    "prep_bad_args": case_bad_args,
}


def main(argv) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    names = list(CASES) if which == "all" else [k for k in CASES if which in k]
    if not names:
        print(f"no case matches {which!r}; known: {', '.join(CASES)}")
        return 2
    print(f"[gate-tests] data-preprocessor quality gate — temp fixtures in {TMP}")
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
