#!/usr/bin/env python3
"""markdown_publisher.py — Task 5 / E7a: Markdown Publisher

Uses Python string.Template to render enhanced_analysis.md from
enhanced_knowledge.json and a .tmpl template file.

CLI: python markdown_publisher.py --knowledge PATH --template PATH --output PATH
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List


# ── helpers ────────────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt_r(val: float) -> str:
    """Format a correlation coefficient for display."""
    if val == 0.0:
        return "0.00"
    return f"{val:.3f}"


def _fmt_q(val: float) -> str:
    """Format a q-value for display."""
    if val >= 0.999:
        return "~1.0"
    return f"{val:.4f}"


def _operability_zh(op: str) -> str:
    """Translate operability enum to Chinese."""
    mapping = {
        "LEVER_IDENTIFIED": "已确认可操作杠杆",
        "LEVER_OBSERVATIONAL": "观察性关联（暂非杠杆）",
        "ENDOGENOUS_RESPONSE": "内生响应（方向与物理矛盾）",
        "CONFOUNDED": "混杂（Simpson/群组逆转或时间混淆）",
        "NOT_IDENTIFIABLE": "不可识别",
        "CONSTRAINT_UNCONTROLLABLE": "不可控约束条件",
    }
    return mapping.get(op, op)


def _status_zh(status: str) -> str:
    """Translate enhancement status to Chinese."""
    mapping = {
        "READY": "就绪",
        "READY_WITH_WARNINGS": "就绪（附警告）",
        "BLOCKED": "阻塞",
        "FAILED": "失败",
    }
    return mapping.get(status, status)


# ── variable builders ───────────────────────────────────────────────────

def build_variables(kb: dict) -> Dict[str, str]:
    """Build the complete substitution dictionary for the template.

    Every key maps to a string. Multi-line blocks are pre-rendered.
    """
    v: Dict[str, str] = {}

    # ── basic fields ──
    v["run_id"] = kb.get("run_id", "unknown")
    v["enhancement_status"] = kb.get("enhancement_status", "FAILED")
    v["enhancement_status_zh"] = _status_zh(kb.get("enhancement_status", "FAILED"))

    # ── provenance ──
    prov = kb.get("provenance", {})
    ds = prov.get("data_source", {})
    v["data_file"] = ds.get("file", "unknown")
    v["data_rows"] = str(ds.get("rows", 0))
    v["data_cols"] = str(ds.get("cols", 0))
    v["data_sha256"] = ds.get("sha256", "")[:16] + "..."
    v["source_artifacts_list"] = _build_source_list(prov)

    # ── warnings ──
    v["warnings_block"] = _build_warnings(kb)

    # ── relationship graph summary ──
    rg = kb.get("relationship_graph", {})
    nodes = rg.get("nodes", [])
    edges = rg.get("edges", [])
    v["n_nodes"] = str(len(nodes))
    v["n_edges"] = str(len(edges))
    v["nodes_table"] = _build_nodes_table(nodes)
    v["edges_sections"] = _build_edges_sections(edges)

    # ── mechanism chains ──
    v["n_mech_chains"] = str(len(kb.get("mechanism_chains", [])))
    v["mechanism_chain_sections"] = _build_mechanism_sections(kb.get("mechanism_chains", []))

    # ── tradeoff matrix ──
    v["n_tradeoffs"] = str(len(kb.get("tradeoff_matrix", [])))
    v["tradeoff_sections"] = _build_tradeoff_sections(kb.get("tradeoff_matrix", []))

    # ── operability summary ──
    v["operability_summary_text"] = kb.get("operability_summary", "")
    v["operability_distribution_table"] = _build_operability_dist(edges)

    # ── open questions ──
    v["n_open_questions"] = str(len(kb.get("open_questions", [])))
    v["open_questions_list"] = _build_question_list(kb.get("open_questions", []))

    # ── evidence gaps ──
    v["n_evidence_gaps"] = str(len(kb.get("evidence_gaps", [])))
    v["evidence_gaps_list"] = _build_gaps_list(kb.get("evidence_gaps", []))

    # ── appendix ──
    v["appendix_json"] = json.dumps(kb, ensure_ascii=False, indent=2)

    # ── timestamp ──
    import datetime
    v["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    return v


def _build_source_list(prov: dict) -> str:
    """Build a markdown list of source artifacts."""
    sa = prov.get("source_artifacts", {})
    lines = []
    for key, val in sa.items():
        if val:
            lines.append(f"- `{key}`: {val}")
    return "\n".join(lines) if lines else "- 无"


def _build_warnings(kb: dict) -> str:
    """Build warnings block based on operability distribution."""
    edges = kb.get("relationship_graph", {}).get("edges", [])
    total = len(edges)
    if total == 0:
        return "> 无可用关系数据。"

    from collections import Counter
    op_counts = Counter(e.get("operability", "") for e in edges)
    confounded = op_counts.get("CONFOUNDED", 0)
    not_id = op_counts.get("NOT_IDENTIFIABLE", 0)
    endog = op_counts.get("ENDOGENOUS_RESPONSE", 0)

    lines = ["> 关系可操作性分布："]
    lines.append(f"> - 已确认杠杆: {op_counts.get('LEVER_IDENTIFIED', 0)}")
    lines.append(f"> - 观察性关联: {op_counts.get('LEVER_OBSERVATIONAL', 0)}")
    lines.append(f"> - 内生响应: {endog}")
    lines.append(f"> - 混杂: {confounded}")
    lines.append(f"> - 不可识别: {not_id}")
    lines.append(f"> - 不可控约束: {op_counts.get('CONSTRAINT_UNCONTROLLABLE', 0)}")

    if confounded + not_id > 0.3 * total:
        ratio_pct = round((confounded + not_id) / total * 100)
        lines.append(f"> **警告**: {confounded + not_id}/{total} ({ratio_pct}%) 关系为混杂或不可识别，超过30%阈值。")

    return "\n".join(lines)


def _build_nodes_table(nodes: List[dict]) -> str:
    """Build a markdown table of nodes."""
    if not nodes:
        return "无节点数据。"
    rows = [
        "| 节点ID | 类型 | 单位 | 角色 | 覆盖状态 |",
        "|--------|------|------|------|----------|",
    ]
    for n in nodes:
        node_type = n.get("type", "")
        unit = n.get("unit", "dimensionless")
        role = n.get("role", "")
        cov = n.get("coverage_status", "")
        rows.append(f"| `{n.get('id','')}` | {node_type} | {unit} | {role} | {cov} |")
    return "\n".join(rows)


def _build_edges_sections(edges: List[dict]) -> str:
    """Build per-edge claim sections with embedded JSON blocks."""
    if not edges:
        return "无关系数据。"

    sections = []
    for i, e in enumerate(edges):
        source = e.get("source", "?")
        target = e.get("target", "?")
        operability = e.get("operability", "NOT_IDENTIFIABLE")
        rel_type = e.get("relationship", "correlates")
        stats = e.get("statistical_evidence", {})
        phys = e.get("physics_verification", {})

        claim_id = f"REL-{i+1:03d}"
        global_r = stats.get("global_r", 0.0)
        partial_r = stats.get("partial_r", 0.0)
        n_eff = stats.get("n_effective", 0)
        q_val = stats.get("q_value", 1.0)
        form = stats.get("form_match", "")

        # Build the section
        parts = [
            f"### 关系 {claim_id}: {source} → {target}",
            "",
            f"**原始列**: `{source}` → `{target}`",
            f"**可操作性**: {_operability_zh(operability)} (`{operability}`)",
            f"**关系类型**: {rel_type}",
            "",
        ]

        # Statistical evidence summary
        parts.append(f"| 指标 | 值 |")
        parts.append(f"|------|----|")
        parts.append(f"| 全局相关系数 r | {_fmt_r(global_r)} |")
        parts.append(f"| 偏相关系数 | {_fmt_r(partial_r)} |")
        parts.append(f"| 有效样本量 n | {n_eff} |")
        parts.append(f"| q 值 (BH校正) | {_fmt_q(q_val)} |")
        parts.append(f"| 函数形式匹配 | {form} |")

        if phys:
            parts.append(f"| 方向验证 | {phys.get('direction','?')} |")
            parts.append(f"| 物理状态 | {phys.get('overall_status','?')} |")
        parts.append("")

        # Embedded JSON claim block
        claim_json = json.dumps({
            "claim_id": claim_id,
            "status": operability,
            "source": f"{source}->{target}",
            "mask": f"finite + steady (n_eff={n_eff})",
            "n": n_eff,
            "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected",
            "effect": {
                "global_r": global_r,
                "partial_r": partial_r,
                "slope_at_current": stats.get("slope_at_current", 0.0),
                "lag_aligned_r": stats.get("lag_aligned_r", 0.0),
            },
            "causal_ceiling": f"operability={operability}",
            "not_for": "直接因果推断（无随机对照实验）",
        }, ensure_ascii=False, indent=2)
        parts.append("```json")
        parts.append(claim_json)
        parts.append("```")
        parts.append("")

        sections.append("\n".join(parts))

    return "\n".join(sections)


def _build_mechanism_sections(chains: List[dict]) -> str:
    """Build mechanism chain sections."""
    if not chains:
        return "无确认的机理链。"

    sections = []
    for mc in chains:
        chain_id = mc.get("chain_id", "?")
        sections.append(f"### {chain_id}\n")
        sections.append(f"**主张**: {mc.get('claim', '')}\n")
        sections.append(f"**置信度**: {mc.get('confidence', 'medium')}\n")
        refs = mc.get("evidence_refs", [])
        if refs:
            sections.append(f"**证据引用**: {', '.join(refs)}\n")
        sections.append("")

    return "\n".join(sections)


def _build_tradeoff_sections(tradeoffs: List[dict]) -> str:
    """Build tradeoff matrix sections."""
    if not tradeoffs:
        return "无权衡数据。"

    sections = []
    for i, t in enumerate(tradeoffs):
        param = t.get("parameter", "?")
        sections.append(f"### 参数: {param}\n")
        sections.append(f"- **可控性**: {t.get('controllability', '')}")
        sections.append(f"- **可操作性**: {_operability_zh(t.get('operability', 'NOT_IDENTIFIABLE'))}")
        sections.append(f"- **支持域**: {t.get('support_domain', '')}")

        effects = t.get("effects", {})
        if effects:
            sections.append("- **对各目标的影响**:")
            for k, v in effects.items():
                sections.append(f"  - {k}: {v}")
        sections.append("")

    return "\n".join(sections)


def _build_operability_dist(edges: List[dict]) -> str:
    """Build operability distribution table."""
    if not edges:
        return "无关系数据。"

    from collections import Counter
    op_counts = Counter(e.get("operability", "") for e in edges)
    total = len(edges)

    rows = [
        "| 可操作性 | 数量 | 占比 |",
        "|----------|------|------|",
    ]
    order = ["LEVER_IDENTIFIED", "LEVER_OBSERVATIONAL", "ENDOGENOUS_RESPONSE",
             "CONFOUNDED", "NOT_IDENTIFIABLE", "CONSTRAINT_UNCONTROLLABLE"]
    for op in order:
        count = op_counts.get(op, 0)
        if count > 0:
            pct = round(count / total * 100)
            rows.append(f"| {_operability_zh(op)} | {count} | {pct}% |")

    return "\n".join(rows)


def _build_question_list(questions: List[dict]) -> str:
    """Build open questions list."""
    if not questions:
        return "无待解决问题。"

    lines = []
    for i, q in enumerate(questions):
        severity = q.get("severity", "minor")
        lines.append(f"- **Q{i+1}** [{severity}]: {q.get('question', '')}")
        impact = q.get("potential_impact", "")
        if impact:
            lines.append(f"  - 潜在影响: {impact}")
    return "\n".join(lines)


def _build_gaps_list(gaps: List[dict]) -> str:
    """Build evidence gaps list."""
    if not gaps:
        return "无证据缺口。"

    lines = []
    for i, g in enumerate(gaps):
        severity = g.get("severity", "minor")
        lines.append(f"- **G{i+1}** [{severity}]: {g.get('gap', '')}")
        impact = g.get("impact", "")
        if impact:
            lines.append(f"  - 影响: {impact}")
    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Markdown Publisher — render enhanced_analysis.md from enhanced_knowledge.json"
    )
    parser.add_argument("--knowledge", required=True, help="Path to enhanced_knowledge.json")
    parser.add_argument("--template", required=True, help="Path to .tmpl template file")
    parser.add_argument("--output", required=True, help="Output path for enhanced_analysis.md")
    args = parser.parse_args()

    knowledge_path = Path(args.knowledge).resolve()
    template_path = Path(args.template).resolve()
    output_path = Path(args.output).resolve()

    if not knowledge_path.is_file():
        print(f"ERROR: knowledge file not found: {knowledge_path}", file=sys.stderr)
        sys.exit(1)
    if not template_path.is_file():
        print(f"ERROR: template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    try:
        kb = _load(knowledge_path)
    except Exception as e:
        print(f"ERROR: failed to load knowledge JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            tmpl_str = f.read()
    except Exception as e:
        print(f"ERROR: failed to load template: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        variables = build_variables(kb)
        template = Template(tmpl_str)
        # Use safe_substitute to avoid KeyError on missing placeholders
        rendered = template.safe_substitute(variables)
    except Exception as e:
        print(f"ERROR: template substitution failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(json.dumps({
            "status": "ok",
            "output": str(output_path),
            "size_bytes": len(rendered),
        }, indent=2))
    except Exception as e:
        print(f"ERROR: failed to write output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
