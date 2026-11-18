#!/usr/bin/env python
"""Test runner for the darwin-skill quality gate (scripts/quality_gate.mjs).

Usage (from repo root):
    python .claude/skills/darwin-skill/tests/run_tests.py [case|all]

Pure stdlib (no venv needed — the gate under test is a Node builtin-only script).

Cases (fixtures built in a temp dir; the REAL results.tsv is also exercised
read-only as the primary positive case):
  darwin_real_log_ok        the repository's actual results.tsv -> exit 0/ok
  darwin_header_only        header + comment only -> exit 2 (undetermined)
  darwin_missing_file       nonexistent path -> exit 1 (hard error)
  darwin_dir_arg            --file points at a directory -> exit 1
  darwin_bad_header         reordered header -> exit 3 (D1)
  darwin_short_row          8 fields on one line -> exit 3 (D2)
  darwin_bad_timestamp      '2026/01/01 10:00' -> exit 3 (D3)
  darwin_tz_timestamp_ok    '+08:00' offset form (in real use) -> exit 0
  darwin_high_score_ok      score 115 (real later-era value) -> exit 0
  darwin_score_too_big      score 1000 -> exit 3 (D4)
  darwin_bad_eval_mode      eval_mode 'prod' -> exit 3 (D6)
  darwin_monotonic_improved improved but 50 -> 40 -> exit 3 (D7)
  darwin_monotonic_regressed regressed but 40 -> 50 -> exit 3 (D7)
  darwin_drift_status_note  unknown slug status -> exit 0 + vocabulary note
  darwin_comment_lines_ok   '#' comment and blank lines are skipped -> exit 0

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
REAL_LOG = SKILL / "results.tsv"

TMP = Path(tempfile.mkdtemp(prefix="darwin_gate_tests_"))
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


HEADER = "timestamp\tcommit\tskill\told_score\tnew_score\tstatus\tdimension\tnote\teval_mode"


def row(ts="2026-10-05T10:00:00", commit="abc1234", skill="industrial-sentinel",
        old="-", new="85", status="baseline", dim="-", note="n", mode="live") -> str:
    return "\t".join([ts, commit, skill, old, new, status, dim, note, mode])


def write_log(name: str, *lines: str) -> Path:
    p = TMP / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


# ── cases ──────────────────────────────────────────────────────────────

def case_real_log() -> None:
    require(REAL_LOG.exists(), "darwin_real_log_ok", f"missing {REAL_LOG}")
    r = gate("--file", str(REAL_LOG))
    record("darwin_real_log_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-300:]}")
    j = gate_json(r)
    record("darwin_real_log_verdict_ok", j.get("verdict") == "ok", str(j)[:200])
    record("darwin_real_log_rows", (j.get("evaluations") or 0) >= 200, f"evaluations={j.get('evaluations')}")


def case_header_only() -> None:
    p = write_log("header_only.tsv", HEADER, "# a phase comment")
    r = gate("--file", str(p))
    record("darwin_header_only_exit2", r.returncode == 2, f"rc={r.returncode} {r.stdout[-200:]}")
    record("darwin_header_only_undetermined",
           gate_json(r).get("verdict") == "undetermined", r.stdout[-200:])


def case_missing_file() -> None:
    r = gate("--file", str(TMP / "nope.tsv"))
    record("darwin_missing_file_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")


def case_dir_arg() -> None:
    r = gate("--file", str(TMP))
    record("darwin_dir_arg_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")


def case_bad_header() -> None:
    bad = HEADER.replace("old_score", "prev_score")
    p = write_log("bad_header.tsv", bad, row())
    r = gate("--file", str(p))
    record("darwin_bad_header_exit3", r.returncode == 3, f"rc={r.returncode} {r.stdout[-200:]}")
    record("darwin_bad_header_rule", any("D1" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_short_row() -> None:
    p = write_log("short_row.tsv", HEADER, "\t".join(["2026-10-05T10:00:00", "abc1234", "skill-x"]))
    r = gate("--file", str(p))
    record("darwin_short_row_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("darwin_short_row_rule", any("D2" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_bad_timestamp() -> None:
    p = write_log("bad_ts.tsv", HEADER, row(ts="2026/01/01 10:00"))
    r = gate("--file", str(p))
    record("darwin_bad_timestamp_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("darwin_bad_timestamp_rule", any("D3" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_tz_timestamp_ok() -> None:
    p = write_log("tz_ts.tsv", HEADER, row(ts="2026-10-10T13:28:26+08:00"))
    r = gate("--file", str(p))
    record("darwin_tz_timestamp_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")


def case_high_score_ok() -> None:
    p = write_log("high_score.tsv", HEADER, row(old="102", new="115", status="improved"))
    r = gate("--file", str(p))
    record("darwin_high_score_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")


def case_score_too_big() -> None:
    p = write_log("big_score.tsv", HEADER, row(new="1000"))
    r = gate("--file", str(p))
    record("darwin_score_too_big_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("darwin_score_too_big_rule", any("D4" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_bad_eval_mode() -> None:
    p = write_log("bad_mode.tsv", HEADER, row(mode="prod"))
    r = gate("--file", str(p))
    record("darwin_bad_eval_mode_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("darwin_bad_eval_mode_rule", any("D6" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_monotonic_improved() -> None:
    p = write_log("mono_imp.tsv", HEADER, row(old="50", new="40", status="improved"))
    r = gate("--file", str(p))
    record("darwin_monotonic_improved_exit3", r.returncode == 3, f"rc={r.returncode}")
    record("darwin_monotonic_improved_rule", any("D7" in f for f in gate_json(r).get("fails", [])),
           r.stdout[-200:])


def case_monotonic_regressed() -> None:
    p = write_log("mono_reg.tsv", HEADER, row(old="40", new="50", status="regressed"))
    r = gate("--file", str(p))
    record("darwin_monotonic_regressed_exit3", r.returncode == 3, f"rc={r.returncode}")


def case_drift_status_note() -> None:
    p = write_log("drift.tsv", HEADER, row(status="ecosystem_fix_v2", old="-", new="43"))
    r = gate("--file", str(p))
    j = gate_json(r)
    record("darwin_drift_status_note_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
    record("darwin_drift_status_note_reported",
           any("ecosystem_fix_v2" in n for n in j.get("notes", [])), str(j)[:300])


def case_comment_lines_ok() -> None:
    p = write_log("comments.tsv", HEADER, row(), "# mid-file comment", "", row(ts="2026-10-05T10:05:00"))
    r = gate("--file", str(p))
    j = gate_json(r)
    record("darwin_comment_lines_ok_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
    record("darwin_comment_lines_rows", j.get("evaluations") == 2, f"evaluations={j.get('evaluations')}")


CASES = {
    "darwin_real_log": case_real_log,
    "darwin_header_only": case_header_only,
    "darwin_missing_file": case_missing_file,
    "darwin_dir_arg": case_dir_arg,
    "darwin_bad_header": case_bad_header,
    "darwin_short_row": case_short_row,
    "darwin_bad_timestamp": case_bad_timestamp,
    "darwin_tz_timestamp_ok": case_tz_timestamp_ok,
    "darwin_high_score_ok": case_high_score_ok,
    "darwin_score_too_big": case_score_too_big,
    "darwin_bad_eval_mode": case_bad_eval_mode,
    "darwin_monotonic_improved": case_monotonic_improved,
    "darwin_monotonic_regressed": case_monotonic_regressed,
    "darwin_drift_status_note": case_drift_status_note,
    "darwin_comment_lines_ok": case_comment_lines_ok,
}


def main(argv) -> int:
    which = argv[1] if len(argv) > 1 else "all"
    names = list(CASES) if which == "all" else [k for k in CASES if which in k]
    if not names:
        print(f"no case matches {which!r}; known: {', '.join(CASES)}")
        return 2
    print(f"[gate-tests] darwin-skill quality gate — temp fixtures in {TMP}")
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
