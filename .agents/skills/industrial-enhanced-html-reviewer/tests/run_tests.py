#!/usr/bin/env python
"""Test runner for industrial-enhanced-html-reviewer/scripts/quality_gate.mjs (AC in tests/AC.md).

Usage (from repo root):
  .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-enhanced-html-reviewer/tests/run_tests.py [case|all]
  python .claude/skills/industrial-enhanced-html-reviewer/tests/run_tests.py       # any python3

Fixtures are generated on the fly into a system temp dir and removed afterwards; nothing is committed.
The pass path runs the REAL builder + reviewer scripts (end-to-end), the warn path is a hand-shaped page.

Gate exit codes: 0 ok (verdict pass) | 1 hard error | 2 undetermined (build artifacts absent)
                 | 3 gate-fail (verdict warn/fail; warn only with --allow-warn becomes 0).
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REPO = SKILL.parents[2]
BUILDER = REPO / ".claude" / "skills" / "industrial-enhanced-html-visualizer" / "scripts" / "html_builder.py"
GATE = SKILL / "scripts" / "quality_gate.mjs"
RESULTS = []
TMP = None

CONTAINERS = ["chartNetwork", "chartHeatmap", "radarGrid", "chartOperMatrix", "physicsGrid"]


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def run_gate(*args, **kw):
    return subprocess.run(["node", str(GATE), *args, "--python", sys.executable],
                          capture_output=True, text=True, timeout=180, shell=False, **kw)


def make_run(name):
    enh = Path(TMP) / name / "enhancement"
    enh.mkdir(parents=True, exist_ok=True)
    return enh


def knowledge_fixture() -> dict:
    edge = {
        "source": "temp_zone1", "target": "thickness", "relationship": "causes", "strength": 0.62,
        "confidence": 0.8, "operability": "LEVER_IDENTIFIED", "causal_ceiling": "temporal_precedence",
        "statistical_evidence": {"global_r": 0.7, "detrended_r": 0.62, "lag_aligned_r": 0.6,
                                 "temporal_direction": "x_leads_y", "direct_association": True},
        "physics_verification": {"direction": "MATCH", "functional_form": "PLAUSIBLE", "time_lag": "MATCH",
                                 "magnitude": "PARTIAL", "state_dependence": "UNTESTED",
                                 "overall_status": "plausible"},
    }
    return {
        "run_id": "20261017_demo",
        "enhancement_status": "READY",
        "relationship_graph": {
            "nodes": [{"id": "temp_zone1", "label": "一区温度", "type": "parameter", "role": "predictor", "unit": "degC"},
                      {"id": "thickness", "label": "膜厚", "type": "target", "role": "target", "unit": "um"}],
            "edges": [edge],
        },
        "tradeoff_matrix": [{"parameter": "temp_zone1", "effects": {"thickness": "r=0.62"}, "operability": "LEVER_IDENTIFIED"}],
        "mechanism_chains": [{"claim": "一区温度升高导致膜厚增大"}],
        "operability_summary": "共识别 1 个可操作杠杆参数（一区温度）。",
        "open_questions": [],
        "provenance": {"data_source": {"file": "data.csv", "sha256": "a" * 64, "rows": 120, "cols": 8},
                       "source_artifacts": {"diagnosis.json": "x"}},
    }


def build(enh) -> subprocess.CompletedProcess:
    (enh / "enhanced_knowledge.json").write_text(json.dumps(knowledge_fixture(), ensure_ascii=False), encoding="utf-8")
    return subprocess.run([sys.executable, str(BUILDER), "--knowledge", str(enh / "enhanced_knowledge.json"),
                           "--output", str(enh / "enhanced-analysis.html")], capture_output=True, text=True)


# ── case 1: real builder artifacts → gate runs reviewer → verdict pass → exit 0 ──
def case_end_to_end_pass():
    enh = make_run("e2e")
    proc = build(enh)
    record("e2e.builder_exit0", proc.returncode == 0, proc.stderr[-200:])
    p = run_gate("--run-dir", str(enh.parent))
    record("e2e.gate_exit0_on_real_artifacts", p.returncode == 0, f"rc={p.returncode} out={p.stdout[-400:]}")
    record("e2e.review_artifact_written", (enh / "enhancement_html_review.json").exists(), "")
    head = p.stdout[:400]
    record("e2e.verdict_pass_mapped", '"verdict_value": "pass"' in p.stdout, head)


# ── case 2: build artifacts absent → exit 2 ─────────────────────────────────
def case_absent():
    enh = make_run("absent")
    p = run_gate("--run-dir", str(enh.parent))
    record("absent.inputs_missing_exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")

    (enh / "enhanced_knowledge.json").write_text(json.dumps(knowledge_fixture(), ensure_ascii=False), encoding="utf-8")
    p = run_gate("--run-dir", str(enh.parent))
    record("absent.html_missing_exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")


# ── case 3: corrupt page → reviewer verdict fail → exit 3 ───────────────────
def case_corrupt_page():
    enh = make_run("corrupt")
    build(enh)
    (enh / "enhanced-analysis.html").write_text("<!DOCTYPE html><html><head><title>x</title></head><body></body></html>",
                                                encoding="utf-8")
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.truncated_page_exit3", p.returncode == 3 and '"verdict_value": "fail"' in p.stdout,
           f"rc={p.returncode} out={p.stdout[-300:]}")
    record("corrupt.blocking_reported", '"blocking_issues":' in p.stdout and '"warnings":' in p.stdout,
           p.stdout[-300:])


# ── case 4: warn verdict mapping (+ --allow-warn) ───────────────────────────
def case_warn_mapping():
    enh = make_run("warn")
    (enh / "enhanced_knowledge.json").write_text(json.dumps(knowledge_fixture(), ensure_ascii=False), encoding="utf-8")
    ids = "".join(f'<div id="{c}"></div>' for c in CONTAINERS[:3])  # 3/5 charts -> warn
    html = (
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>增强诊断分析</title></head><body>'
        '<div class="status-badge"></div><div class="display"></div><div class="key-findings"></div>'
        "可操作性 数据溯源 sha256 staticFallback "
        "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js https://unpkg.com/echarts@5/dist/echarts.min.js"
        + ids + "<p>填充</p>" * 600 + "</body></html>"
    )
    (enh / "enhanced-analysis.html").write_text(html, encoding="utf-8")
    p = run_gate("--run-dir", str(enh.parent))
    record("warn.exit3_by_default", p.returncode == 3 and '"verdict_value": "warn"' in p.stdout,
           f"rc={p.returncode} out={p.stdout[-300:]}")
    p2 = run_gate("--run-dir", str(enh.parent), "--no-run", "--allow-warn")
    record("warn.allow_warn_exit0", p2.returncode == 0, f"rc={p2.returncode} out={p2.stdout[-300:]}")


# ── case 5: --no-run consumes without re-running the reviewer ───────────────
def case_no_run():
    enh = make_run("norun")
    p = run_gate("--run-dir", str(enh.parent), "--no-run")
    record("no_run.missing_artifact_exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")
    (enh / "enhancement_html_review.json").write_text(json.dumps({
        "verdict": "pass", "overall_score": 88, "blocking_issues": [], "warnings": [],
        "checks": [{"name": "hero_clarity", "status": "pass", "evidence": "x"}], "html_size_bytes": 20000,
    }, ensure_ascii=False), encoding="utf-8")
    p = run_gate("--run-dir", str(enh.parent), "--no-run")
    record("no_run.consumes_existing_pass_exit0", p.returncode == 0, f"rc={p.returncode} out={p.stdout[-300:]}")


CASES = {"e2e_pass": case_end_to_end_pass, "absent": case_absent, "corrupt": case_corrupt_page,
         "warn": case_warn_mapping, "no_run": case_no_run}


def main():
    global TMP
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(CASES) if selector == "all" else ([selector] if selector in CASES else list(CASES))
    TMP = tempfile.mkdtemp(prefix="enh_html_reviewer_gate_")
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
