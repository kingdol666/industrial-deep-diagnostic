#!/usr/bin/env python
"""Test runner for the industrial-physical-auditor quality gate (CP-8 / pre-audit).

Usage (from repo root):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-physical-auditor/tests/run_tests.py [case|all]

(stdlib only — plain `python` works too if the shared venv is not needed)

Cases (fixtures generated on the fly into a temp dir; nothing committed):
  T1  well-formed FINAL optimizer.md (ENDORSED, sections, grounding)    -> exit 0
  T1b well-formed PRE-AUDIT optimizer_preflight.md (PREFLIGHT_PASS)     -> exit 0
  T2  optimizer.md absent (final audit did not run)                     -> exit 2
  T2b optimizer_preflight.md absent (--pre-audit)                       -> exit 2
  T3a no verdict token at all                                           -> exit 3
  T3b required section missing (audit overview / statistical)           -> exit 3
  T3c well-formed CONDITIONAL verdict is not a CP-8 pass                -> exit 3
  T3d ambiguous verdict line (two conflicting tokens)                   -> exit 3
  T3e wrong-mode vocabulary (preflight tokens in a final artifact)      -> exit 3
  T3f pre-audit NEEDS_REPAIR without repair_instruction                 -> exit 3 (A3+A6)
  T3g pre-audit NEEDS_REPAIR with repair_instruction (A6 ok, A3 fails)  -> exit 3
  T4  run dir does not exist (bad input)                                -> exit 1

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


def run_gate(run_dir, pre=False):
    cmd = ["node", str(GATE), "--run-dir", str(run_dir)]
    if pre:
        cmd.append("--pre-audit")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=False)


def parse_verdict(proc, case):
    try:
        return json.loads(proc.stdout)
    except Exception as e:
        record(case, False, f"stdout is not JSON: {e}; stdout={proc.stdout[:200]!r}; stderr={proc.stderr[:200]!r}")
        raise CaseAbort(case)


GOOD_FINAL = """# 物理终审（Step 7）— ENDORSED

run: test_run  auditor: report-reviewer (industrial-physical-auditor protocol)

## 审计总览
独立复审报告.md 的物理推理链、统计基础与可视化证据；逐项核验本 run 的确定性产物。

## 统计核验
- validate_report 稳健性抽查：Simpson 分层、去趋势相关与留一法均复算一致。【通过】
- 数字抽验：报告中的相关系数与 02_processed 统计产物一致。【通过】

## 物理核验
- 机制链（反应器温度 → 转化率）可回溯至 Arrhenius 控制方程，量级与时间尺度自洽。【通过】
- 竞争假设排除逻辑基于物理边界，成立。【通过】

## 终审清单
1. primary_finding 与 diagnosis.json 逐字一致：【通过】
2. 证据分级合理、证据缺口已限定：【通过】

判定：**ENDORSED**（终审通过，无 FATAL 发现）。
"""

GOOD_PRE = """# 物理预审计（Step 5b, pre-report）

## 机制链物理核查
1. 反应器温度 → 转化率的机制链可由控制方程解释，量级估计合理。【通过】
2. 数据支持与物理先验方向一致。【通过】

## 数据真相抽查
- 关键统计量可由 02_processed 产物复算。【通过】

## 发现
- 无 FATAL 发现。

## 结论
预审计通过：PREFLIGHT_PASS
"""

CONDITIONAL_FINAL = GOOD_FINAL.replace("— ENDORSED", "— CONDITIONAL").replace(
    "判定：**ENDORSED**（终审通过，无 FATAL 发现）。",
    "判定：**CONDITIONAL**（存在可修复项，需按清单修复后复查）。")

NEEDS_REPAIR_NO_INSTR = """# 物理预审计（Step 5b, pre-report）

## 机制链物理核查
- 机制链与统计核验存在量级矛盾（物理量级估计偏差 10x）。【问题】

## 发现
- 发现一处物理不可行结论。

## 结论
PREFLIGHT_NEEDS_REPAIR
"""


def case_dir(name):
    return Path(tempfile.mkdtemp(prefix=f"auditor_gate_{name}_", dir=TMP_ROOT))


def case_t1():
    print("[T1] well-formed FINAL optimizer.md -> exit 0")
    d = case_dir("final_ok")
    (d / "optimizer.md").write_text(GOOD_FINAL, encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T1_verdict_json")
    record("T1_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T1_verdict_ok", v.get("verdict") == "ok", str(v.get("verdict")))
    record("T1_auditor_verdict", v.get("auditor_verdict") == "ENDORSED", str(v.get("auditor_verdict")))
    record("T1_mode_final", v.get("mode") == "final", str(v.get("mode")))
    record("T1_all_checks_pass", all(c["ok"] for c in v.get("checks", [])),
           str([c for c in v.get("checks", []) if not c["ok"]]))


def case_t1b():
    print("[T1b] well-formed PRE-AUDIT optimizer_preflight.md -> exit 0")
    d = case_dir("pre_ok")
    (d / "05_review").mkdir(parents=True)
    (d / "05_review" / "optimizer_preflight.md").write_text(GOOD_PRE, encoding="utf-8")
    p = run_gate(d, pre=True)
    v = parse_verdict(p, "T1b_verdict_json")
    record("T1b_exit0", p.returncode == 0, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T1b_mode_pre", v.get("mode") == "pre-audit", str(v.get("mode")))
    record("T1b_auditor_verdict", v.get("auditor_verdict") == "PREFLIGHT_PASS", str(v.get("auditor_verdict")))


def case_t2():
    print("[T2] optimizer.md absent -> exit 2 (final audit did not run)")
    d = case_dir("final_absent")
    (d / "04_diagnostics").mkdir(parents=True)
    p = run_gate(d)
    v = parse_verdict(p, "T2_verdict_json")
    record("T2_exit2", p.returncode == 2, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T2_verdict_undetermined", v.get("verdict") == "undetermined", str(v.get("verdict")))
    record("T2_reason_artifact", "optimizer.md" in str(v.get("reason", "")), str(v.get("reason")))


def case_t2b():
    print("[T2b] optimizer_preflight.md absent (--pre-audit) -> exit 2")
    d = case_dir("pre_absent")
    (d / "05_review").mkdir(parents=True)  # stage dir exists, artifact does not
    p = run_gate(d, pre=True)
    v = parse_verdict(p, "T2b_verdict_json")
    record("T2b_exit2", p.returncode == 2, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T2b_verdict_undetermined", v.get("verdict") == "undetermined", str(v.get("verdict")))


def case_t3a():
    print("[T3a] no verdict token at all -> exit 3")
    d = case_dir("no_verdict")
    (d / "optimizer.md").write_text(
        "## 审计总览\n统计核验与物理核验均完成（证据、诊断、物理、数据）。\n", encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3a_verdict_json")
    record("T3a_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3a_fail_is_A2", any(f.startswith("A2_verdict_recognized") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3a_no_auditor_verdict", v.get("auditor_verdict") is None, str(v.get("auditor_verdict")))


def case_t3b():
    print("[T3b] required sections missing -> exit 3")
    d = case_dir("missing_sections")
    (d / "optimizer.md").write_text(
        "判定：**ENDORSED**\n物理核验：成立。\n", encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3b_verdict_json")
    record("T3b_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3b_fail_is_A4", any(f.startswith("A4_sections_present") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3b_A2_ok", all(c["ok"] for c in v.get("checks", []) if c["id"].startswith("A2")),
           str(v.get("checks")))


def case_t3c():
    print("[T3c] well-formed CONDITIONAL is not a CP-8 pass -> exit 3")
    d = case_dir("conditional")
    (d / "optimizer.md").write_text(CONDITIONAL_FINAL, encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3c_verdict_json")
    record("T3c_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3c_recognized_conditional", v.get("auditor_verdict") == "CONDITIONAL", str(v.get("auditor_verdict")))
    record("T3c_fail_is_A3", any(f.startswith("A3_verdict_is_pass") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3d():
    print("[T3d] ambiguous verdict line -> exit 3")
    d = case_dir("ambiguous")
    body = GOOD_FINAL.replace("判定：**ENDORSED**（终审通过，无 FATAL 发现）。",
                              "判定：**ENDORSED / REJECTED**（需复核）。")
    (d / "optimizer.md").write_text(body, encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3d_verdict_json")
    record("T3d_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3d_fail_is_A2", any(f.startswith("A2_verdict_recognized") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3d_mentions_ambiguous", any("ambiguous" in f for f in v.get("fails", [])), str(v.get("fails")))


def case_t3e():
    print("[T3e] wrong-mode vocabulary (preflight tokens in final artifact) -> exit 3")
    d = case_dir("wrong_mode")
    (d / "optimizer.md").write_text(GOOD_PRE, encoding="utf-8")
    p = run_gate(d)
    v = parse_verdict(p, "T3e_verdict_json")
    record("T3e_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3e_mentions_other_vocab", any("other mode" in f for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3f():
    print("[T3f] pre-audit NEEDS_REPAIR without repair_instruction -> A3+A6 fail (exit 3)")
    d = case_dir("needs_repair_no_instr")
    (d / "05_review").mkdir(parents=True)
    (d / "05_review" / "optimizer_preflight.md").write_text(NEEDS_REPAIR_NO_INSTR, encoding="utf-8")
    p = run_gate(d, pre=True)
    v = parse_verdict(p, "T3f_verdict_json")
    record("T3f_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3f_recognized_needs_repair",
           v.get("auditor_verdict") == "PREFLIGHT_NEEDS_REPAIR", str(v.get("auditor_verdict")))
    record("T3f_fail_is_A3", any(f.startswith("A3_verdict_is_pass") for f in v.get("fails", [])),
           str(v.get("fails")))
    record("T3f_fail_is_A6", any(f.startswith("A6_repair_instructions") for f in v.get("fails", [])),
           str(v.get("fails")))


def case_t3g():
    print("[T3g] pre-audit NEEDS_REPAIR with repair_instruction -> A6 ok, A3 still fails")
    d = case_dir("needs_repair_with_instr")
    (d / "05_review").mkdir(parents=True)
    body = NEEDS_REPAIR_NO_INSTR + "\n- repair_instruction: 复核量级估计并补充离线表征证据。\n"
    (d / "05_review" / "optimizer_preflight.md").write_text(body, encoding="utf-8")
    p = run_gate(d, pre=True)
    v = parse_verdict(p, "T3g_verdict_json")
    record("T3g_exit3", p.returncode == 3, f"rc={p.returncode} {p.stdout[-300:]}")
    record("T3g_A6_ok", all(c["ok"] for c in v.get("checks", []) if c["id"].startswith("A6")),
           str(v.get("checks")))
    record("T3g_A3_fails", any(f.startswith("A3_verdict_is_pass") for f in v.get("fails", [])),
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
    "T2b": case_t2b,
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
    TMP_ROOT = tempfile.mkdtemp(prefix="auditor_gate_tests_")
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
