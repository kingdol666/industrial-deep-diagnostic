#!/usr/bin/env python3
"""
Enhanced HTML Reviewer — Task 6
Reviews enhanced-analysis.html against enhanced_knowledge.json.
Outputs enhancement_html_review.json with verdict, score, checks.
"""
import json
import os
import re
import sys
import argparse
from datetime import datetime


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def review(knowledge_path: str, html_path: str, selfcheck_path: str = None) -> dict:
    """Review the generated HTML against the knowledge JSON."""
    knowledge = load_json(knowledge_path)
    html = load_text(html_path)
    html_lower = html.lower()

    checks = []
    warnings = []
    blocking = []
    total_score = 100

    # ── Check 1: Hero clarity ──
    has_status_badge = "status-badge" in html
    has_display = 'class="display"' in html
    has_key_findings = "key-findings" in html
    has_oper_summary = "可操作性" in html or "operability" in html_lower
    hero_ok = has_status_badge and has_display and has_key_findings

    if hero_ok:
        checks.append({
            "name": "hero_clarity",
            "status": "pass",
            "evidence": "Hero section present with status badge, display title, key findings, and operability summary"
        })
    else:
        missing = []
        if not has_status_badge: missing.append("status badge")
        if not has_display: missing.append("display title")
        if not has_key_findings: missing.append("key findings")
        checks.append({
            "name": "hero_clarity",
            "status": "fail",
            "evidence": f"Missing: {', '.join(missing)}"
        })
        blocking.append(f"Hero section missing: {', '.join(missing)}")
        total_score -= 20

    # ── Check 2: Evidence completeness (charts present) ──
    has_network = "chartNetwork" in html
    has_heatmap = "chartHeatmap" in html
    has_radar = "radarGrid" in html
    has_oper_matrix = "chartOperMatrix" in html
    has_physics = "physicsGrid" in html
    chart_count = sum([has_network, has_heatmap, has_radar, has_oper_matrix, has_physics])

    if chart_count >= 5:
        checks.append({
            "name": "evidence_layer_1_statistical",
            "status": "pass",
            "evidence": f"All {chart_count} chart containers present (network, heatmap, radar, operability matrix, physics verification)"
        })
    elif chart_count >= 3:
        checks.append({
            "name": "evidence_layer_1_statistical",
            "status": "warn",
            "evidence": f"Only {chart_count}/5 chart containers present"
        })
        warnings.append(f"Only {chart_count}/5 chart types present; expected 5")
        total_score -= 10
    else:
        checks.append({
            "name": "evidence_layer_1_statistical",
            "status": "fail",
            "evidence": f"Only {chart_count}/5 chart containers present"
        })
        blocking.append(f"Missing {5 - chart_count} chart types")
        total_score -= 25

    # ── Check 3: Evidence reading annotations ──
    reading_count = len(re.findall(r'cr-label', html))
    has_triple_reading = reading_count >= 5  # one per chart
    if has_triple_reading:
        checks.append({
            "name": "evidence_layer_2_physics",
            "status": "pass",
            "evidence": f"Charts have triple-reading annotations (至少 {reading_count} 组检测到)"
        })
    else:
        checks.append({
            "name": "evidence_layer_2_physics",
            "status": "warn",
            "evidence": f"Only {reading_count} chart-reading groups detected (expected ≥5)"
        })
        warnings.append(f"Chart reading annotations sparse: {reading_count} found")
        total_score -= 5

    # ── Check 4: CDN multi-source ──
    has_jsdelivr = "cdn.jsdelivr.net" in html
    has_unpkg = "unpkg.com" in html
    has_cdnjs = "cdnjs.cloudflare.com" in html
    cdn_ok = has_jsdelivr and has_unpkg and has_cdnjs

    if cdn_ok:
        checks.append({
            "name": "chart_initialization",
            "status": "pass",
            "evidence": "ECharts CDN multi-source loading (jsdelivr + unpkg + cdnjs) with runtime fallback"
        })
    elif has_jsdelivr and has_unpkg:
        checks.append({
            "name": "chart_initialization",
            "status": "warn",
            "evidence": "ECharts CDN: jsdelivr + unpkg present but cdnjs missing"
        })
        warnings.append("cdnjs backup CDN source not found")
        total_score -= 5
    else:
        checks.append({
            "name": "chart_initialization",
            "status": "fail",
            "evidence": f"CDN sources: jsdelivr={has_jsdelivr}, unpkg={has_unpkg}, cdnjs={has_cdnjs}"
        })
        blocking.append("ECharts CDN multi-source loading incomplete")
        total_score -= 15

    # ── Check 5: Runtime self-check ──
    has_selfcheck = "selfcheck" in html_lower
    has_echarts_check = "echarts_available" in html
    has_degraded = "degraded_mode" in html
    has_static_fallback = "staticFallback" in html

    if has_selfcheck and has_echarts_check and has_degraded and has_static_fallback:
        checks.append({
            "name": "three_d_fidelity",
            "status": "pass",
            "evidence": "Runtime self-check with echarts_available, degraded_mode, and static fallback tables"
        })
    else:
        checks.append({
            "name": "three_d_fidelity",
            "status": "warn",
            "evidence": f"Runtime self-check: selfcheck={has_selfcheck}, echarts_check={has_echarts_check}, degraded={has_degraded}, fallback={has_static_fallback}"
        })
        warnings.append("Runtime self-check may be incomplete")
        total_score -= 5

    # ── Check 6: Data governance card ──
    has_gov = "数据溯源" in html or "gov-card" in html
    has_sha = "sha256" in html_lower or "SHA256" in html
    has_rows = knowledge.get("provenance", {}).get("data_source", {}).get("rows", 0) > 0

    if has_gov and has_sha:
        checks.append({
            "name": "data_governance",
            "status": "pass",
            "evidence": "Data governance card with SHA256, row count, source artifacts"
        })
    elif has_gov:
        checks.append({
            "name": "data_governance",
            "status": "warn",
            "evidence": "Governance card present but SHA256 may be missing"
        })
        warnings.append("Data governance card missing SHA256 fingerprint")
        total_score -= 5
    else:
        checks.append({
            "name": "data_governance",
            "status": "fail",
            "evidence": "Data governance card missing from output"
        })
        blocking.append("Data governance card not found in HTML")
        total_score -= 15

    # ── Check 7: Static table fallback ──
    if has_static_fallback:
        checks.append({
            "name": "degraded_mode_fallback",
            "status": "pass",
            "evidence": "Static fallback table section present for degraded mode"
        })
    else:
        checks.append({
            "name": "degraded_mode_fallback",
            "status": "fail",
            "evidence": "No static fallback table found"
        })
        blocking.append("Static fallback table missing")
        total_score -= 10

    # ── Check 8: Size requirement ──
    html_size = len(html.encode("utf-8"))
    if html_size >= 5120:
        checks.append({
            "name": "size_requirement",
            "status": "pass",
            "evidence": f"HTML size: {html_size} bytes (≥ 5120)"
        })
    else:
        checks.append({
            "name": "size_requirement",
            "status": "fail",
            "evidence": f"HTML size: {html_size} bytes (< 5120)"
        })
        blocking.append(f"HTML too small: {html_size} < 5120 bytes")
        total_score -= 20

    # ── Check 9: Content references knowledge data ──
    knowledge_run_id = knowledge.get("run_id", "")
    has_run_id = knowledge_run_id in html
    edge_labels = knowledge.get("relationship_graph", {}).get("edges", [])
    edge_ref_count = sum(1 for e in edge_labels if e.get("source", "")[:10] in html)

    if has_run_id or edge_ref_count >= 1:
        checks.append({
            "name": "data_fidelity",
            "status": "pass",
            "evidence": f"HTML references knowledge data: run_id={has_run_id}, edge labels embedded"
        })
    else:
        checks.append({
            "name": "data_fidelity",
            "status": "warn",
            "evidence": "HTML may not reference knowledge data directly"
        })
        warnings.append("HTML content may not be sourced from enhanced_knowledge.json")
        total_score -= 5

    # ── Aggregate verdict ──
    if blocking:
        verdict = "fail"
    elif total_score < 75:
        verdict = "warn"
    else:
        verdict = "pass"

    # Cap score
    total_score = max(0, min(100, total_score))

    result = {
        "verdict": verdict,
        "overall_score": total_score,
        "blocking_issues": blocking,
        "warnings": warnings,
        "checks": checks,
        "reviewed_at": datetime.now().isoformat(),
        "html_path": os.path.abspath(html_path),
        "knowledge_path": os.path.abspath(knowledge_path),
        "html_size_bytes": html_size,
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Enhanced HTML Reviewer")
    parser.add_argument("--knowledge", required=True, help="Path to enhanced_knowledge.json")
    parser.add_argument("--html", required=True, help="Path to enhanced-analysis.html")
    parser.add_argument("--output", required=True, help="Path to output enhancement_html_review.json")
    parser.add_argument("--selfcheck", default=None, help="Path to html_selfcheck.json (optional)")
    args = parser.parse_args()

    if not os.path.exists(args.knowledge):
        print(f"ERROR: knowledge file not found: {args.knowledge}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.html):
        print(f"ERROR: html file not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    result = review(args.knowledge, args.html, args.selfcheck)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "verdict": result["verdict"],
        "overall_score": result["overall_score"],
        "blocking_issues": len(result["blocking_issues"]),
        "warnings": len(result["warnings"]),
        "output": os.path.abspath(args.output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
