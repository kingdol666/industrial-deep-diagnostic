#!/usr/bin/env python
"""Test runner for industrial-html-visualizer/scripts/quality_gate.mjs (AC in tests/AC.md).

Usage (from repo root):
  .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-html-visualizer/tests/run_tests.py [case|all]
  python .claude/skills/industrial-html-visualizer/tests/run_tests.py              # any python3

Fixtures are generated on the fly into a system temp dir and removed afterwards; nothing is committed.

Gate exit codes: 0 ok | 1 hard error | 2 undetermined (page absent) | 3 gate-fail.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
GATE = SKILL / "scripts" / "quality_gate.mjs"
RESULTS = []
TMP = None


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def run_gate(*args):
    return subprocess.run(["node", str(GATE), *args], capture_output=True, text=True, timeout=120, shell=False)


def make_run(name):
    run = Path(TMP) / name
    (run / "05_review").mkdir(parents=True, exist_ok=True)
    return run


def good_html(title="诊断可视化报告 · 测试") -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>.page{{color:#1e3a54}}</style></head>"
        "<body><div class=\"page\">" + "<p>证据链填充段落</p>" * 500 + "</div>"
        "<script>var ready = true;</script></body></html>"
    )


def verdict_of(proc):
    try:
        start = proc.stdout.index("{")
        return json.loads(proc.stdout[start:]).get("verdict")
    except Exception:
        return None


# ── case 1: valid page → exit 0 ─────────────────────────────────────────────
def case_valid():
    run = make_run("valid")
    html = good_html()
    (run / "diagnostic-report.html").write_text(html, encoding="utf-8")
    p = run_gate("--run-dir", str(run))
    on_disk = (run / "diagnostic-report.html").stat().st_size
    record("valid.minimal_page_exit0", p.returncode == 0, f"rc={p.returncode} out={p.stdout[-300:]}")
    record("valid.verdict_ok_and_bytes_reported",
           verdict_of(p) == "ok" and f'"bytes": {on_disk}' in p.stdout,
           p.stdout[-300:])


# ── case 2: page absent → exit 2 (undetermined) ─────────────────────────────
def case_absent():
    run = make_run("absent")
    p = run_gate("--run-dir", str(run))
    record("absent.exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")
    record("absent.verdict_undetermined", verdict_of(p) == "undetermined", p.stdout[-300:])


# ── case 3: corrupt pages → exit 3 ──────────────────────────────────────────
def case_corrupt():
    run = make_run("corrupt")
    target = run / "diagnostic-report.html"

    target.write_text("<!DOCTYPE html><html><body><p>no title here</p></body></html>" * 200, encoding="utf-8")
    p = run_gate("--run-dir", str(run))
    record("corrupt.no_title_exit3", p.returncode == 3, f"rc={p.returncode} out={p.stdout[-300:]}")

    target.write_text(good_html()[:2000], encoding="utf-8")  # truncated < 5120B
    p = run_gate("--run-dir", str(run))
    record("corrupt.truncated_undersized_exit3", p.returncode == 3, f"rc={p.returncode} out={p.stdout[-300:]}")

    target.write_text(good_html().replace("</script>", ""), encoding="utf-8")  # unbalanced tags
    p = run_gate("--run-dir", str(run))
    record("corrupt.unbalanced_script_tags_exit3", p.returncode == 3 and "V6" in p.stdout,
           f"rc={p.returncode} out={p.stdout[-300:]}")


# ── case 4: bad invocation → exit 1 (hard error) ────────────────────────────
def case_hard_error():
    p = run_gate()
    record("hard_error.no_args_exit1", p.returncode == 1, f"rc={p.returncode} out={p.stdout[-300:]}")


CASES = {"valid": case_valid, "absent": case_absent, "corrupt": case_corrupt, "hard_error": case_hard_error}


def main():
    global TMP
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(CASES) if selector == "all" else ([selector] if selector in CASES else list(CASES))
    TMP = tempfile.mkdtemp(prefix="html_visualizer_gate_")
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
