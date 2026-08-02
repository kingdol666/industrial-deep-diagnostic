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
    v["network_summary"] = _build_network_summary(edges)
    v["contradiction_list"] = _build_contradiction_list(edges)
    v["mediation_list"] = _build_mediation_list(edges)

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
        parts.append(f"| 偏相关系数（全阶条件独立） | {_fmt_r(partial_r)} |")
        parts.append(f"| 有效样本量 n | {n_eff} |")
        parts.append(f"| q 值 (BH校正) | {_fmt_q(q_val)} |")
        parts.append(f"| 函数形式匹配 | {form} |")
        ceiling = e.get("causal_ceiling", "")
        if ceiling:
            parts.append(f"| 因果上限 | {_ceiling_zh(ceiling)} (`{ceiling}`) |")
        if e.get("ontology_contradiction"):
            parts.append(f"| **本体矛盾** | 数据方向与本体校验方向相反 |")
        parts.append(f"| 证据置信度 | {e.get('confidence', 0.0):.2f}/1.00 |")
        tdir = stats.get("temporal_direction", "")
        if tdir and tdir not in ("concurrent", "insufficient", ""):
            parts.append(f"| 时序方向 | {_direction_zh(tdir)}（最优时滞 {stats.get('optimal_lag_steps', 0)} 步, CCF r={_fmt_r(stats.get('ccf_peak_r', 0.0))}） |")
        if stats.get("indirect_association"):
            meds = stats.get("mediator_candidates", []) or []
            med_str = " → ".join(f"`{m}`" for m in meds[:2]) if meds else "（未识别出具体中介）"
            parts.append(f"| 间接关联 | 关联经中介通道 {med_str} 传导，非直接作用 |")
        if stats.get("change_point_co_movement", 0.0) >= 0.5:
            parts.append(f"| 变点同步 | 两变量变点对齐评分 {stats.get('change_point_co_movement', 0.0):.2f} |")
        if stats.get("loo_stability", 0.0) > 0:
            parts.append(f"| LOO 稳定性 | {stats.get('loo_stability', 0.0):.2f} |")
        if stats.get("interaction_flagged"):
            parts.append(f"| 调节效应 | 关联在分组/工况间方向或强度分歧，不可外推为全局杠杆 |")

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
            "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
            "effect": {
                "global_r": global_r,
                "partial_r": partial_r,
                "slope_at_current": stats.get("slope_at_current", 0.0),
                "lag_aligned_r": stats.get("lag_aligned_r", 0.0),
            },
            "causal_ceiling": e.get("causal_ceiling", "contemporaneous_correlation"),
            "confidence": e.get("confidence", 0.0),
            "temporal_direction": stats.get("temporal_direction", "concurrent"),
            "optimal_lag_steps": stats.get("optimal_lag_steps", 0),
            "direct_association": stats.get("direct_association", False),
            "indirect_association": stats.get("indirect_association", False),
            "mediator_candidates": stats.get("mediator_candidates", []),
            "ontology_contradiction": e.get("ontology_contradiction", False),
            "not_for": "直接因果推断（无随机对照实验）",
        }, ensure_ascii=False, indent=2)
        parts.append("```json")
        parts.append(claim_json)
        parts.append("```")
        parts.append("")

        sections.append("\n".join(parts))

    return "\n".join(sections)


def _build_network_summary(edges: List[dict]) -> str:
    """Compact association-network summary: direction, ceiling, contradiction counts."""
    if not edges:
        return "无关系数据。"
    from collections import Counter
    rel_counts = Counter(e.get("relationship", "") for e in edges)
    ceiling_counts = Counter(e.get("causal_ceiling", "") for e in edges)
    direct = sum(1 for e in edges if e.get("statistical_evidence", {}).get("direct_association"))
    indirect = sum(1 for e in edges if e.get("statistical_evidence", {}).get("indirect_association"))
    contrad = sum(1 for e in edges if e.get("ontology_contradiction"))

    rows = [
        "| 维度 | 统计 |",
        "|------|------|",
        f"| 边总数 | {len(edges)} |",
        f"| 正关联 (supports) | {rel_counts.get('supports', 0)} |",
        f"| 负关联 (inhibits) | {rel_counts.get('inhibits', 0)} |",
        f"| 因果边 (causes) | {rel_counts.get('causes', 0)} |",
        f"| 矛盾边 (contradicts) | {rel_counts.get('contradicts', 0)} |",
        f"| 直接关联（条件独立成立） | {direct} |",
        f"| 间接关联（经中介传导） | {indirect} |",
        f"| 本体方向矛盾 | {contrad} |",
        f"| 时序领先 (temporal_precedence) | {ceiling_counts.get('temporal_precedence', 0)} |",
        f"| 条件独立支持 (conditional_independence_supported) | {ceiling_counts.get('conditional_independence_supported', 0)} |",
        f"| 本体一致 (ontology_consistent) | {ceiling_counts.get('ontology_consistent', 0)} |",
    ]
    return "\n".join(rows)


def _build_contradiction_list(edges: List[dict]) -> str:
    """List ontology contradictions as warnings."""
    contrad = [e for e in edges if e.get("ontology_contradiction")]
    if not contrad:
        return "无。数据方向与本体校验方向一致。"
    lines = []
    for e in contrad:
        stats = e.get("statistical_evidence", {})
        lines.append(
            f"- `{e.get('source','?')}` → `{e.get('target','?')}`：数据 r="
            f"{_fmt_r(stats.get('global_r', 0.0))}，与本体校验方向相反，可能为内生控制掩盖或本体方向标注错误"
        )
    return "\n".join(lines)


def _build_mediation_list(edges: List[dict]) -> str:
    """List indirect/mediation channels."""
    ind = [e for e in edges if e.get("statistical_evidence", {}).get("indirect_association")]
    if not ind:
        return "未识别出间接传导通道。"
    lines = []
    for e in ind:
        stats = e.get("statistical_evidence", {})
        meds = stats.get("mediator_candidates", []) or []
        med_str = " → ".join(f"`{m}`" for m in meds[:2]) if meds else "未识别"
        lines.append(f"- `{e.get('source','?')}` → `{e.get('target','?')}` 经 {med_str} 间接传导")
    return "\n".join(lines)


def _ceiling_zh(ceiling: str) -> str:
    return {
        "insufficient_evidence": "证据不足",
        "contemporaneous_correlation": "同期相关",
        "temporal_precedence": "时序领先",
        "conditional_independence_supported": "条件独立支持（直接关联）",
        "ontology_consistent": "本体一致（物理方向吻合）",
    }.get(ceiling, ceiling)


def _direction_zh(direction: str) -> str:
    return {
        "x_leads_y": "预测变量领先目标变量",
        "y_leads_x": "目标变量领先预测变量",
        "concurrent": "同步变化",
        "insufficient": "数据不足",
    }.get(direction, direction)


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
