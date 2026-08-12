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
from typing import Any, Dict, List, Tuple


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

# ── AI-actionable deep synthesis sections ──────────────────────────────

def _build_ai_actionable_summary(kb: dict) -> str:
    """Build a compact machine-parseable JSON block for AI consumption.

    This is THE primary interface for downstream AI agents: it encodes
    the top control levers, strongest pathways, and key risk factors
    in a single JSON structure that an agent can parse without reading
    the full document.
    """
    levers = kb.get("control_levers", [])
    pathways = kb.get("causal_pathways", [])
    centrality = kb.get("parameter_centrality", [])
    edges = kb.get("relationship_graph", {}).get("edges", [])

    # Top levers (controllable, highest confidence)
    top_levers = []
    for lev in levers[:10]:
        top_levers.append({
            "parameter": lev.get("parameter", ""),
            "physical_meaning": lev.get("physical_meaning", ""),
            "controllable": lev.get("controllable", False),
            "confidence": lev.get("overall_confidence", 0.0),
            "downstream": [
                {"target": d["target"], "direction": d["direction"],
                 "strength": d["strength"], "physics_verified": d["physics_verified"]}
                for d in lev.get("downstream_effects", [])[:3]
            ],
            "risks": lev.get("risk_factors", [])[:2],
        })

    # Top pathways (strongest multi-hop chains)
    top_paths = []
    for p in pathways[:5]:
        top_paths.append({
            "path": " → ".join(p.get("path", [])),
            "strength": p.get("total_strength", 0.0),
            "hops": p.get("path_length", 0),
        })

    # Hub parameters (highest influence)
    hubs = [{"parameter": c["parameter"], "influence": c["influence_score"],
             "targets": c.get("downstream_targets", [])[:3]}
            for c in centrality if c.get("is_hub")][:5]

    # Physics verification rate
    phys_verified = sum(1 for e in edges if e.get("physics_verification", {}).get("overall_status") == "confirmed")
    phys_total = sum(1 for e in edges if e.get("physics_verification", {}))

    summary = {
        "document_type": "industrial_deep_analysis",
        "version": "2.0",
        "run_id": kb.get("run_id", ""),
        "status": kb.get("enhancement_status", ""),
        "parameter_count": len(kb.get("relationship_graph", {}).get("nodes", [])),
        "relationship_count": len(edges),
        "physics_verification": {
            "verified": phys_verified,
            "total_tested": phys_total,
            "rate": round(phys_verified / max(phys_total, 1), 3),
        },
        "top_control_levers": top_levers,
        "strongest_causal_pathways": top_paths,
        "hub_parameters": hubs,
        "usage_instruction": (
            "This summary encodes the analysis results for machine consumption. "
            "Each control lever lists its downstream effects on quality targets. "
            "'direction: increase' means raising the parameter raises the target. "
            "'physics_verified: true' means the relationship passed 5-item physics verification. "
            "Always check 'risk_factors' before acting. See full document for detailed evidence."
        ),
    }

    return json.dumps(summary, ensure_ascii=False, indent=2)


def _build_control_levers_table(kb: dict) -> str:
    """Build a markdown table of control levers with expected impact."""
    levers = kb.get("control_levers", [])
    if not levers:
        return "无可识别的控制杠杆。"

    lines = [
        "| 参数 | 物理含义 | 可控 | 置信度 | 下游目标 | 方向 | 强度 | 物理验证 | 风险 |",
        "|------|----------|:----:|:------:|----------|------|------|:--------:|------|",
    ]

    for lev in levers:
        param = lev.get("parameter", "?")
        meaning = lev.get("physical_meaning", "")[:30]
        ctrl = "✅" if lev.get("controllable") else "❌"
        conf = f"{lev.get('overall_confidence', 0):.2f}"

        effects = lev.get("downstream_effects", [])
        if effects:
            first = effects[0]
            target = first.get("target", "?")
            direction = "↑" if first.get("direction") == "increase" else "↓"
            strength = f"{first.get('strength', 0):.3f}"
            phys = "✅" if first.get("physics_verified") else "—"
        else:
            target = direction = strength = phys = "—"

        risks = lev.get("risk_factors", [])
        risk_str = risks[0][:25] if risks and risks[0] != "None identified" else "无"

        lines.append(f"| `{param}` | {meaning} | {ctrl} | {conf} | `{target}` | {direction} | {strength} | {phys} | {risk_str} |")

        # Additional effects on separate rows
        for eff in effects[1:]:
            tgt = eff.get("target", "?")
            d = "↑" if eff.get("direction") == "increase" else "↓"
            s = f"{eff.get('strength', 0):.3f}"
            p = "✅" if eff.get("physics_verified") else "—"
            lines.append(f"| | | | | `{tgt}` | {d} | {s} | {p} | |")

    return "\n".join(lines)


def _build_control_levers_detail(kb: dict) -> str:
    """Build detailed per-lever sections with embedded JSON for AI consumption."""
    levers = kb.get("control_levers", [])
    if not levers:
        return "无控制杠杆详情。"

    sections = []
    for i, lev in enumerate(levers):
        param = lev.get("parameter", "?")
        conf = lev.get("overall_confidence", 0.0)
        ctrl = lev.get("controllable", False)

        parts = [
            f"### 控制杠杆 LEVER-{i+1:03d}: `{param}`",
            "",
            f"**物理含义**: {lev.get('physical_meaning', '未知')}",
            f"**单位**: {lev.get('unit', 'dimensionless')}",
            f"**当前值(中位数)**: {lev.get('current_value', 'N/A')}",
            f"**可控性**: {'✅ 已验证可控' if ctrl else '⚠️ 观测性关联'}",
            f"**综合置信度**: {conf:.2f}/1.00",
            f"**设备工段**: {lev.get('equipment_stage', '未标注')}",
            "",
        ]

        # Downstream effects table
        effects = lev.get("downstream_effects", [])
        if effects:
            parts.append("| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |")
            parts.append("|----------|------|---------|----------|--------|:--------:|-----|----------|")
            for eff in effects:
                tgt = eff.get("target", "?")
                d = "↑ 增加" if eff.get("direction") == "increase" else "↓ 减少"
                s = f"{eff.get('strength', 0):.3f}"
                slope = f"{eff.get('slope_at_current', 0):.4f}"
                c = f"{eff.get('confidence', 0):.2f}"
                pv = "✅" if eff.get("physics_verified") else "—"
                q = f"{eff.get('q_value', 1.0):.4f}"
                td = eff.get("temporal_direction", "concurrent")
                parts.append(f"| `{tgt}` | {d} | {s} | {slope} | {c} | {pv} | {q} | {td} |")
            parts.append("")

        # Risk factors
        risks = lev.get("risk_factors", [])
        if risks and risks != ["None identified"]:
            parts.append("**⚠️ 风险因素**:")
            for r in risks:
                parts.append(f"- {r}")
            parts.append("")

        # Embedded JSON for AI
        lever_json = json.dumps({
            "lever_id": f"LEVER-{i+1:03d}",
            "parameter": param,
            "controllable": ctrl,
            "confidence": conf,
            "downstream_effects": effects,
            "risk_factors": risks,
            "operability": lev.get("operability", []),
            "support_domain": lev.get("support_domain", {}),
        }, ensure_ascii=False, indent=2)
        parts.append("```json")
        parts.append(lever_json)
        parts.append("```")
        parts.append("")

        sections.append("\n".join(parts))

    return "\n".join(sections)


def _build_influence_matrix(kb: dict) -> str:
    """Build a compact parameter × target influence matrix.

    Rows = process parameters, Columns = quality targets.
    Each cell shows the correlation strength with sign.
    """
    edges = kb.get("relationship_graph", {}).get("edges", [])
    nodes = kb.get("relationship_graph", {}).get("nodes", [])

    target_ids = sorted({
        n.get("id", "") for n in nodes
        if n.get("type") == "target" or n.get("role") in ("target", "quality_target")
    })
    param_ids = sorted({
        n.get("id", "") for n in nodes
        if n.get("type") != "target" and n.get("role") not in ("target", "quality_target")
        and n.get("id", "")
    })

    if not target_ids or not param_ids:
        return "无足够数据构建影响矩阵。"

    # Build lookup: (param, target) -> edge
    edge_lookup: Dict[Tuple[str, str], dict] = {}
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src and tgt:
            edge_lookup[(src, tgt)] = e

    # Header
    col_width = max(len(t) for t in target_ids) + 2
    col_width = min(col_width, 18)
    header = "| 参数 |" + "|".join(f" `{t[:col_width-2]}` " for t in target_ids) + "|"
    sep = "|------|" + "|".join("---:" for _ in target_ids) + "|"

    lines = [header, sep]

    for param in param_ids:
        cells = []
        for tgt in target_ids:
            e = edge_lookup.get((param, tgt))
            if e:
                r = e.get("strength", 0.0)
                conf = e.get("confidence", 0.0)
                phys = e.get("physics_verification", {}).get("overall_status", "")
                if abs(r) >= 0.5 and conf >= 0.5:
                    symbol = "🟢" if r > 0 else "🔴"
                elif abs(r) >= 0.3:
                    symbol = "🟡" if r > 0 else "🟠"
                elif abs(r) >= 0.1:
                    symbol = "⚫"
                else:
                    symbol = "·"
                cell = f"{symbol}{r:+.2f}"
                if phys == "confirmed":
                    cell += "✓"
            else:
                cell = "—"
            cells.append(f" {cell} ")
        lines.append(f"| `{param[:20]}` |" + "|".join(cells) + "|")

    legend = "\n\n**图例**: 🟢强正相关(≥0.5) 🟡中等正相关(0.3-0.5) ⚫弱相关(0.1-0.3) · 极弱/无关 | 🔴🔴🟠 负相关同级别 | ✓ 物理验证通过"
    return "\n".join(lines) + legend


def _build_causal_pathways_section(kb: dict) -> str:
    """Build multi-hop causal pathway sections."""
    pathways = kb.get("causal_pathways", [])
    if not pathways:
        return "未识别出多跳因果路径。"

    sections = []
    for i, p in enumerate(pathways[:20]):
        path = p.get("path", [])
        path_str = " → ".join(f"`{node}`" for node in path)
        strength = p.get("total_strength", 0.0)
        hops = p.get("path_length", 0)
        min_conf = p.get("min_confidence", 0.0)

        parts = [
            f"### 因果路径 PATH-{i+1:03d}: {path_str}",
            "",
            f"**跳数**: {hops}",
            f"**路径强度** (边强度乘积): {strength:.4f}",
            f"**最小置信度**: {min_conf:.2f}",
            "",
        ]

        # Edge details
        edges_in_path = p.get("edges", [])
        if edges_in_path:
            parts.append("**路径上的每条边**:")
            parts.append("")
            parts.append("| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |")
            parts.append("|-------------|----------|------|--------|:--------:|")
            for pe in edges_in_path:
                src = pe.get("from", "?")
                tgt = pe.get("to", "?")
                rel = pe.get("relationship", "?")
                s = f"{pe.get('strength', 0):.3f}"
                c = f"{pe.get('confidence', 0):.2f}"
                pv = "✅" if pe.get("physics_verified") else "—"
                parts.append(f"| `{src}` → `{tgt}` | {rel} | {s} | {c} | {pv} |")
            parts.append("")

        # Physical interpretation
        phys_ctx = kb.get("physical_context", {})
        interp_parts = []
        for node in path:
            ctx = phys_ctx.get(node, {})
            meaning = ctx.get("physical_meaning", "")
            if meaning:
                interp_parts.append(f"`{node}`: {meaning}")
        if interp_parts:
            parts.append("**物理链条解读**:")
            for ip in interp_parts:
                parts.append(f"- {ip}")
            parts.append("")

        sections.append("\n".join(parts))

    return "\n".join(sections)


def _build_parameter_centrality_section(kb: dict) -> str:
    """Build parameter centrality table."""
    centrality = kb.get("parameter_centrality", [])
    if not centrality:
        return "无参数中心性数据。"

    lines = [
        "| 参数 | 角色 | 出度 | 入度 | 影响力分 | 枢纽? | 下游质量目标 | 物理参考 |",
        "|------|------|:----:|:----:|:--------:|:-----:|-------------|----------|",
    ]

    for c in centrality:
        param = c.get("parameter", "?")
        role = c.get("role", "")
        out_d = str(c.get("out_degree", 0))
        in_d = str(c.get("in_degree", 0))
        influence = f"{c.get('influence_score', 0):.3f}"
        hub = "⭐" if c.get("is_hub") else ""
        targets = c.get("downstream_targets", [])
        tgt_str = ", ".join(f"`{t}`" for t in targets[:3]) if targets else "—"
        phys = c.get("physics_ref", "")[:30]

        lines.append(f"| `{param}` | {role} | {out_d} | {in_d} | {influence} | {hub} | {tgt_str} | {phys} |")

    return "\n".join(lines)


def _build_physical_context_section(kb: dict) -> str:
    """Build physical context table from ontology."""
    ctx = kb.get("physical_context", {})
    if not ctx:
        return "无物理上下文数据（本体模型未提供参数物理含义）。"

    lines = [
        "| 参数 | 物理含义 | 单位 | 角色 | 控制方程/预期行为 | 设备工段 |",
        "|------|----------|------|------|-------------------|----------|",
    ]

    for param, info in sorted(ctx.items()):
        meaning = info.get("physical_meaning", "")[:40]
        unit = info.get("unit", "")
        role = info.get("role", "")
        gov = info.get("governing_law", info.get("expected_behavior", ""))[:40]
        equip = info.get("equipment_stage", "")[:20]
        lines.append(f"| `{param}` | {meaning} | {unit} | {role} | {gov} | {equip} |")

    return "\n".join(lines)


# ── end deep synthesis sections ────────────────────────────────────────


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
    v["evidence_gaps_list"] = _build_gaps_list(kb.get("evidence_gaps", []))

    # ── AI-actionable deep synthesis ──
    v["ai_actionable_summary"] = _build_ai_actionable_summary(kb)
    v["control_levers_table"] = _build_control_levers_table(kb)
    v["control_levers_detail"] = _build_control_levers_detail(kb)
    v["influence_matrix"] = _build_influence_matrix(kb)
    v["causal_pathways_section"] = _build_causal_pathways_section(kb)
    v["parameter_centrality_table"] = _build_parameter_centrality_section(kb)
    v["physical_context_table"] = _build_physical_context_section(kb)
    v["n_causal_pathways"] = str(len(kb.get("causal_pathways", [])))
    v["n_control_levers"] = str(len(kb.get("control_levers", [])))
    v["n_hubs"] = str(sum(1 for c in kb.get("parameter_centrality", []) if c.get("is_hub")))
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
