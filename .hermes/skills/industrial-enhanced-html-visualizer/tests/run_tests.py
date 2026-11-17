#!/usr/bin/env python
"""Test runner for industrial-enhanced-html-visualizer/scripts/quality_gate.mjs (AC in tests/AC.md).

Usage (from repo root):
  .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-enhanced-html-visualizer/tests/run_tests.py [case|all]
  python .claude/skills/industrial-enhanced-html-visualizer/tests/run_tests.py    # any python3

Fixtures are generated on the fly into a system temp dir and removed afterwards; nothing is committed.
The marker fixture mirrors the exact shape written by scripts/html_builder.py::generate_selfcheck.

Gate exit codes: 0 ok | 1 hard error | 2 undetermined (page or marker absent) | 3 gate-fail.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
BUILDER = SKILL / "scripts" / "html_builder.py"
GATE = SKILL / "scripts" / "quality_gate.mjs"
RESULTS = []
TMP = None

CONTAINERS = ["chartNetwork", "chartHeatmap", "radarGrid", "chartOperMatrix", "physicsGrid"]
CDNS = [
    "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js",
    "https://unpkg.com/echarts@5/dist/echarts.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js",
]


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def run_gate(*args):
    return subprocess.run(["node", str(GATE), *args], capture_output=True, text=True, timeout=120, shell=False)


def make_run(name):
    enh = Path(TMP) / name / "enhancement"
    enh.mkdir(parents=True, exist_ok=True)
    return enh


def page(marker_extra="", containers=CONTAINERS) -> str:
    ids = "".join(f'<div class="chart-canvas" id="{c}"></div>' for c in containers)
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>增强诊断分析 · run_x</title><style>.page{}</style></head><body>"
        "<div class=\"loader-strip\"></div>" + ids + "<section id=\"staticFallback\"></section>"
        "<script>var selfcheck={echarts_available:false,degraded_mode:true};</script>"
        + "<p>填充</p>" * 600 + marker_extra + "</body></html>"
    )


def marker_for(html: str, **over) -> dict:
    m = {
        "builder": "enhanced_html_builder",
        "generated_at": "2026-10-17T00:00:00",
        "html_size_bytes": len(html.encode("utf-8")),
        "size_requirement_met": len(html.encode("utf-8")) >= 5120,
        "charts_built": 5,
        "chart_types": ["network_graph", "heatmap", "radar", "operability_scatter", "physics_traffic_light"],
        "governance_card_rendered": True,
        "runtime_ready": "ECHARTS_CDN_MULTI_SOURCE",
        "echarts_cdn_sources": CDNS,
        "fallback_mode": "static_tables_when_echarts_unavailable",
    }
    m.update(over)
    return m


def knowledge_fixture() -> dict:
    """Minimal enhanced_knowledge.json in the shape the fusion stage produces."""
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
                      {"id": "thickness", "label": "膜厚", "type": "target", "role": "target", "unit": "um"},
                      {"id": "timestamp", "label": "时间", "type": "meta", "role": "timestamp", "unit": ""}],
            "edges": [edge],
        },
        "tradeoff_matrix": [{"parameter": "temp_zone1", "effects": {"thickness": "r=0.62"}, "operability": "LEVER_IDENTIFIED"}],
        "mechanism_chains": [{"claim": "一区温度升高导致膜厚增大"}],
        "operability_summary": "共识别 1 个可操作杠杆参数（一区温度）。",
        "open_questions": [],
        "provenance": {"data_source": {"file": "data.csv", "sha256": "a" * 64, "rows": 120, "cols": 8},
                       "source_artifacts": {"diagnosis.json": "x"}},
    }


def write_artifacts(enh, html: str, marker: dict):
    (enh / "enhanced-analysis.html").write_text(html, encoding="utf-8")
    (enh / "html_selfcheck.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")


# ── case 1: valid page + marker → exit 0 ────────────────────────────────────
def case_valid():
    enh = make_run("valid")
    html = page()
    write_artifacts(enh, html, marker_for(html))
    p = run_gate("--run-dir", str(enh.parent))
    record("valid.builder_pair_exit0", p.returncode == 0, f"rc={p.returncode} out={p.stdout[-300:]}")
    record("valid.reports_marker_identity",
           '"marker_builder": "enhanced_html_builder"' in p.stdout and '"charts_built": 5' in p.stdout,
           p.stdout[-300:])
    # a real builder page (byte-level) also satisfies the gate
    (enh / "k.json").write_text(json.dumps(knowledge_fixture(), ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(BUILDER), "--knowledge", str(enh / "k.json"),
                           "--output", str(enh / "enhanced-analysis.html")], capture_output=True, text=True)
    if proc.returncode != 0:
        record("valid.real_builder_roundtrip", False, f"builder rc={proc.returncode} {proc.stderr[-200:]}")
    else:
        record("valid.real_builder_roundtrip", run_gate("--run-dir", str(enh.parent)).returncode == 0,
               f"builder={proc.stdout[-160:]}")


# ── case 2: artifacts absent → exit 2 ───────────────────────────────────────
def case_absent():
    enh = make_run("absent")
    p = run_gate("--run-dir", str(enh.parent))
    record("absent.both_missing_exit2", p.returncode == 2, f"rc={p.returncode} out={p.stdout[-300:]}")

    html = page()
    (enh / "enhanced-analysis.html").write_text(html, encoding="utf-8")  # marker still missing
    p = run_gate("--run-dir", str(enh.parent))
    record("absent.marker_missing_exit2", p.returncode == 2 and "html_selfcheck.json" in p.stdout,
           f"rc={p.returncode} out={p.stdout[-300:]}")


# ── case 3: corrupt artifacts → exit 3 ──────────────────────────────────────
def case_corrupt():
    enh = make_run("corrupt")
    html = page()

    (enh / "html_selfcheck.json").write_text("{broken", encoding="utf-8")
    write_artifacts(enh, html, marker_for(html))  # restore valid, then break the marker
    (enh / "html_selfcheck.json").write_text("{broken", encoding="utf-8")
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.marker_unparseable_exit3", p.returncode == 3 and "E3" in p.stdout, f"rc={p.returncode}")

    write_artifacts(enh, html, marker_for(html, builder="html_builder"))
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.wrong_builder_identity_exit3", p.returncode == 3 and "E4" in p.stdout, f"rc={p.returncode}")

    write_artifacts(enh, html, marker_for(html, charts_built=4, size_requirement_met=False))
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.marker_claims_exit3", p.returncode == 3 and "E5" in p.stdout, f"rc={p.returncode}")

    write_artifacts(enh, html, marker_for(html, echarts_cdn_sources=["https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"]))
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.single_cdn_source_exit3", p.returncode == 3 and "E6" in p.stdout, f"rc={p.returncode}")

    write_artifacts(enh, page(containers=["chartNetwork"]), marker_for(page()))
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.missing_chart_containers_exit3", p.returncode == 3 and "E7" in p.stdout, f"rc={p.returncode}")

    tiny = "<!DOCTYPE html><html><head><title>x</title></head><body></body></html>"
    write_artifacts(enh, tiny, marker_for(tiny))
    p = run_gate("--run-dir", str(enh.parent))
    record("corrupt.undersized_page_exit3", p.returncode == 3 and "E2" in p.stdout, f"rc={p.returncode}")


CASES = {"valid": case_valid, "absent": case_absent, "corrupt": case_corrupt}


def main():
    global TMP
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(CASES) if selector == "all" else ([selector] if selector in CASES else list(CASES))
    TMP = tempfile.mkdtemp(prefix="enh_html_visualizer_gate_")
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
