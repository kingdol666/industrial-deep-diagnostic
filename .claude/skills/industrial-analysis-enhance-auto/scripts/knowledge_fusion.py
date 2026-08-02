#!/usr/bin/env python3
"""knowledge_fusion.py — Task 5 / E6: Knowledge Fusion Engine

Reads E1-E5 enhancement artifacts plus ontology and diagnosis from RUN_DIR,
builds a schema-valid enhanced_knowledge.json.

CLI: python knowledge_fusion.py --run-dir PATH --output PATH
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── helpers ────────────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ── E6: knowledge fusion ───────────────────────────────────────────────

def build_nodes(
    coverage: dict,
    ontology: dict,
    derived_features: Optional[dict],
) -> List[dict]:
    """Build relationship_graph.nodes from coverage columns and ontology signals."""
    nodes: List[dict] = []
    seen_ids: set = set()

    # From analysis_coverage columns
    for col in coverage.get("columns", []):
        col_name = col.get("column", "")
        if not col_name or col_name in seen_ids:
            continue
        seen_ids.add(col_name)

        node_type = "parameter"
        role = col.get("role", "")
        if role in ("target", "quality_target"):
            node_type = "target"
        elif role in ("derived",):
            node_type = "derived"

        node = {
            "id": col_name,
            "label": col.get("column", ""),
            "type": node_type,
            "unit": col.get("unit", "dimensionless"),
            "role": role,
            "coverage_status": col.get("coverage_status", ""),
            "support_domain": col.get("support_domain", {}),
            "physics_ref": col.get("physics_ref", "NOT_APPLICABLE"),
        }
        nodes.append(node)

    # Add derived features as nodes
    if derived_features:
        for feat in derived_features.get("features", []):
            name = feat.get("name", "")
            if not name or name in seen_ids:
                continue
            seen_ids.add(name)
            nodes.append({
                "id": name,
                "label": name,
                "type": "derived",
                "unit": feat.get("unit", "dimensionless"),
                "role": "derived_feature",
                "formula": feat.get("formula", ""),
                "source_columns": feat.get("source_columns", []),
                "status": feat.get("status", ""),
            })

    return nodes


def build_edges(
    deep_data: dict,
    physics_bridge: Optional[dict],
    association_graph: Optional[dict] = None,
) -> List[dict]:
    """Build relationship_graph.edges.

    When ``association_graph.json`` (E3.5) is present it is the primary source:
    it covers the full pairwise network with inference evidence (sign,
    confidence, causal ceiling, temporal direction, mediation channels).
    Deep-data relationships absent from the graph (e.g. below-threshold but
    physics-relevant) are appended with legacy semantics, so no prior
    information is ever lost.
    """
    edges: List[dict] = []
    phys_index: Dict[Tuple[str, str], dict] = {}

    if physics_bridge:
        for pv in physics_bridge.get("relationship_verifications", []):
            key = (pv.get("predictor", ""), pv.get("target", ""))
            phys_index[key] = pv

    def _attach_physics(edge: dict, pred: str, targ: str) -> None:
        pk = (pred, targ)
        if pk in phys_index:
            pv = phys_index[pk]
            edge["physics_verification"] = {
                "direction": pv.get("direction", ""),
                "functional_form": pv.get("functional_form", ""),
                "time_lag": pv.get("time_lag", ""),
                "magnitude": pv.get("magnitude", ""),
                "state_dependence": pv.get("state_dependence", ""),
                "overall_status": pv.get("overall_status", ""),
            }
            edge["evidence_ref"] = ", ".join(pv.get("evidence_refs", []))

    graph_keys: Set[Tuple[str, str]] = set()

    if association_graph:
        for g_edge in association_graph.get("edges", []):
            src = g_edge.get("source", "")
            tgt = g_edge.get("target", "")
            if not src or not tgt:
                continue
            graph_keys.add((src, tgt))
            sev = g_edge.get("statistical_evidence", {}) or {}
            edge = {
                "source": src,
                "target": tgt,
                "relationship": g_edge.get("relationship", "supports"),
                "strength": g_edge.get("strength", 0.0),
                "sign": g_edge.get("sign", 1 if g_edge.get("strength", 0) >= 0 else -1),
                "confidence": g_edge.get("confidence", 0.3),
                "causal_ceiling": g_edge.get("causal_ceiling", "contemporaneous_correlation"),
                "ontology_contradiction": bool(g_edge.get("ontology_contradiction", False)),
                "statistical_evidence": {
                    "global_r": sev.get("global_r", g_edge.get("strength", 0.0)),
                    "p_value": sev.get("p_value", 1.0),
                    "p_floor_hit": sev.get("p_floor_hit", False),
                    "detrended_r": sev.get("detrended_r", 0.0),
                    "partial_r": sev.get("partial_r", 0.0),
                    "partial_method": sev.get("partial_method", ""),
                    "temporal_direction": sev.get("temporal_direction", "concurrent"),
                    "optimal_lag_steps": sev.get("optimal_lag_steps", 0),
                    "ccf_peak_r": sev.get("ccf_peak_r", 0.0),
                    "lag_aligned_r": sev.get("lag_aligned_r", 0.0),
                    "direct_association": sev.get("direct_association", False),
                    "indirect_association": sev.get("indirect_association", False),
                    "mediator_candidates": sev.get("mediator_candidates", []),
                    "change_point_co_movement": sev.get("change_point_co_movement", 0.0),
                    "loo_stability": sev.get("loo_stability", 0.0),
                    "interaction_flagged": sev.get("interaction_flagged", False),
                    "slope_at_current": sev.get("slope_at_current", 0.0),
                    "form_match": sev.get("form_match", ""),
                    "q_value": sev.get("q_value", 1.0),
                    "n_effective": sev.get("n_effective", 0),
                },
                "physics_verification": {},
                "operability": "NOT_IDENTIFIABLE",
                "evidence_ref": "",
                "validity_flags": {},
            }
            # Physics verification + operability from deep-data records
            for rel in deep_data.get("relationships", []):
                if rel.get("predictor") == src and rel.get("target") == tgt:
                    edge["operability"] = rel.get("operability", "NOT_IDENTIFIABLE")
                    edge["validity_flags"] = rel.get("validity_flags", {})
                    break
            _attach_physics(edge, src, tgt)
            phys_status = edge.get("physics_verification", {}).get("overall_status", "")
            if phys_status == "confirmed" and edge["relationship"] != "contradicts":
                edge["relationship"] = "causes"
            edges.append(edge)

    for rel in deep_data.get("relationships", []):
        pred = rel.get("predictor", "")
        targ = rel.get("target", "")
        if not pred or not targ:
            continue
        if (pred, targ) in graph_keys:
            continue

        edge = {
            "source": pred,
            "target": targ,
            "relationship": "correlates",
            "strength": rel.get("global", 0.0),
            "sign": 1 if rel.get("global", 0.0) >= 0 else -1,
            "confidence": round(float(rel.get("q_value", 1.0) <= 0.05) * 0.6 + 0.2, 3),
            "causal_ceiling": rel.get("causality_ceiling", "contemporaneous_correlation"),
            "ontology_contradiction": bool(rel.get("ontology_contradiction", False)),
            "statistical_evidence": {
                "global_r": rel.get("global", 0.0),
                "p_value": rel.get("p_value", 1.0),
                "p_floor_hit": rel.get("p_floor_hit", False),
                "detrended_r": rel.get("detrended", 0.0),
                "partial_r": rel.get("partial", 0.0),
                "partial_method": (rel.get("partial_full") or {}).get("method", ""),
                "temporal_direction": rel.get("temporal_direction", "concurrent"),
                "optimal_lag_steps": rel.get("optimal_lag_steps", 0),
                "ccf_peak_r": (rel.get("temporal") or {}).get("ccf_peak_r", 0.0),
                "lag_aligned_r": rel.get("lag_aligned", 0.0),
                "direct_association": rel.get("direct_association", False),
                "indirect_association": rel.get("indirect_association", False),
                "mediator_candidates": [m.get("mediator", "") for m in rel.get("mediator_candidates", [])],
                "change_point_co_movement": (rel.get("change_point_co_movement") or {}).get("score", 0.0),
                "loo_stability": (rel.get("loo_stability") or {}).get("stability", 0.0),
                "interaction_flagged": (rel.get("interaction") or {}).get("flagged", False),
                "slope_at_current": rel.get("slope_at_current", 0.0),
                "form_match": rel.get("form_match", ""),
                "q_value": rel.get("q_value", 1.0),
                "n_effective": rel.get("n_effective", 0),
            },
            "physics_verification": {},
            "operability": rel.get("operability", "NOT_IDENTIFIABLE"),
            "evidence_ref": "",
            "validity_flags": rel.get("validity_flags", {}),
        }

        _attach_physics(edge, pred, targ)

        # Determine relationship type (legacy path)
        phys_status = edge.get("physics_verification", {}).get("overall_status", "")
        operability = rel.get("operability", "")
        if edge.get("ontology_contradiction"):
            edge["relationship"] = "contradicts"
        elif operability == "ENDOGENOUS_RESPONSE":
            edge["relationship"] = "correlates"
        elif phys_status == "confirmed":
            edge["relationship"] = "causes"
        elif phys_status == "inconsistent" or phys_status == "rejected":
            edge["relationship"] = "contradicts"
        elif phys_status == "plausible":
            edge["relationship"] = "supports"
        else:
            edge["relationship"] = "supports" if edge["sign"] > 0 else "inhibits"

        edges.append(edge)

    return edges


def build_mechanism_chains(physics_bridge: dict) -> List[dict]:
    """Extract mechanism_chains from physics_bridge.json."""
    chains = physics_bridge.get("mechanism_chains", [])
    result = []
    for mc in chains:
        result.append({
            "chain_id": mc.get("chain_id", ""),
            "claim": mc.get("claim", ""),
            "confidence": mc.get("data_support", "medium"),
            "evidence_refs": mc.get("evidence_refs", []),
        })
    return result


def build_tradeoff_matrix(deep_data: dict) -> List[dict]:
    """Extract tradeoff_matrix from deep_data_analysis.tradeoff_and_operability."""
    tradeoffs = deep_data.get("tradeoff_and_operability", [])
    result = []
    for t in tradeoffs:
        result.append({
            "parameter": t.get("parameter", ""),
            "controllability": t.get("controllability", ""),
            "operability": t.get("operability_assessment", "NOT_IDENTIFIABLE"),
            "effects": {t.get("parameter", ""): t.get("effects_on_targets", "")},
            "support_domain": t.get("support_domain", ""),
        })
    return result


def build_operability_summary(deep_data: dict) -> str:
    """Build a natural-language operability summary from the deep data analysis."""
    tradeoffs = deep_data.get("tradeoff_and_operability", [])
    relationships = deep_data.get("relationships", [])

    # Count operability classes
    from collections import Counter
    op_counts = Counter(r.get("operability", "") for r in relationships)

    levers = [t for t in tradeoffs if t.get("operability_assessment") == "LEVER_IDENTIFIED"]
    endogenous = op_counts.get("ENDOGENOUS_RESPONSE", 0)
    confounded = op_counts.get("CONFOUNDED", 0)
    not_id = op_counts.get("NOT_IDENTIFIABLE", 0)

    parts = []
    if levers:
        lever_names = [l.get("parameter", "?") for l in levers]
        parts.append(f"已确认可操作杠杆: {', '.join(lever_names)}")
    if endogenous:
        parts.append(f"{endogenous} 个预测变量为内生响应（数据方向与物理预测矛盾）")
    if confounded:
        parts.append(f"{confounded} 个关系受混杂因素影响（Simpson/群组逆转或未解决的时间混淆）")
    if not_id:
        parts.append(f"{not_id} 个关系在当前数据下不可识别")

    if not parts:
        return "根据现有数据无法得出可靠的可操作性评估。"

    return "。".join(parts) + "。"


def build_open_questions(
    deep_data: dict,
    physics_bridge: Optional[dict],
    confidence: Optional[dict],
) -> List[dict]:
    """Aggregate open questions from deep_data tradeoffs and physics bridge evidence gaps."""
    questions: List[dict] = []
    seen: set = set()

    # From tradeoff open questions
    for t in deep_data.get("tradeoff_and_operability", []):
        for q in t.get("open_questions", []):
            if q and q not in seen:
                seen.add(q)
                questions.append({
                    "question": q,
                    "severity": "minor",
                    "potential_impact": "Informs parameter optimization strategy",
                })

    # From physics bridge evidence gaps
    if physics_bridge:
        for gap in physics_bridge.get("evidence_gaps", []):
            q_text = gap.get("gap", "")
            if q_text and q_text not in seen:
                seen.add(q_text)
                questions.append({
                    "question": q_text,
                    "severity": gap.get("severity", "minor"),
                    "potential_impact": gap.get("impact_on_conclusions", ""),
                })

    # From confidence breakdown gaps
    if confidence:
        breakdown = confidence.get("confidence_breakdown", {})
        if isinstance(breakdown, dict):
            for hyp_id, hyp_data in breakdown.items():
                if isinstance(hyp_data, dict):
                    factors = hyp_data.get("five_factor_breakdown", {})
                    if isinstance(factors, dict):
                        for factor_name, factor_data in factors.items():
                            if isinstance(factor_data, dict):
                                gaps = factor_data.get("evidence_gaps", [])
                                for g in gaps:
                                    if g and g not in seen:
                                        seen.add(g)
                                        questions.append({
                                            "question": g,
                                            "severity": "major",
                                            "potential_impact": "Affects confidence in diagnostic conclusions",
                                        })

    return questions


def build_evidence_gaps(
    physics_bridge: Optional[dict],
    confidence: Optional[dict],
) -> List[dict]:
    """Aggregate evidence gaps from physics bridge and confidence."""
    gaps: List[dict] = []
    seen: set = set()

    # From physics bridge evidence_gaps
    if physics_bridge:
        for gap in physics_bridge.get("evidence_gaps", []):
            g_text = gap.get("gap", "")
            if g_text and g_text not in seen:
                seen.add(g_text)
                gaps.append({
                    "gap": g_text,
                    "severity": gap.get("severity", "minor"),
                    "impact": gap.get("impact_on_conclusions", ""),
                })

    # From confidence what_would_change
    if confidence:
        breakdown = confidence.get("confidence_breakdown", {})
        if isinstance(breakdown, dict):
            for hyp_id, hyp_data in breakdown.items():
                if isinstance(hyp_data, dict):
                    wwc = hyp_data.get("what_would_change_conclusion", "")
                    if wwc and isinstance(wwc, str) and wwc not in seen:
                        seen.add(wwc)
                        gaps.append({
                            "gap": wwc,
                            "severity": "major",
                            "impact": "Could modify primary diagnostic conclusion",
                        })

    return gaps


def determine_status(deep_data: dict) -> str:
    """Determine enhancement_status from relationship operability distribution."""
    relationships = deep_data.get("relationships", [])
    # Filter consistently with build_edges: skip empty predictor/target
    valid_rels = [r for r in relationships if r.get("predictor") and r.get("target")]
    if not valid_rels:
        return "FAILED"

    total = len(valid_rels)
    confounded_or_not_id = sum(
        1 for r in valid_rels
        if r.get("operability") in ("CONFOUNDED", "NOT_IDENTIFIABLE")
    )

    if confounded_or_not_id / total > 0.3:
        return "READY_WITH_WARNINGS"

    return "READY"


def fuse(
    run_dir: Path,
    output_path: Path,
) -> dict:
    """Main fusion logic: read all artifacts, build enhanced_knowledge.json."""
    enhance_dir = run_dir / "enhancement"

    # Load artifacts
    coverage_path = enhance_dir / "analysis_coverage.json"
    derived_path = enhance_dir / "derived_features.json"
    deep_data_path = enhance_dir / "deep_data_analysis.json"
    physics_path = enhance_dir / "physics_bridge.json"
    ontology_path = run_dir / "01_ontology" / "ontology.json"
    diagnosis_path = run_dir / "04_diagnostics" / "diagnosis.json"
    confidence_path = run_dir / "04_diagnostics" / "confidence.json"

    # Required artifacts
    coverage = _load(coverage_path) if coverage_path.exists() else None
    deep_data = _load(deep_data_path) if deep_data_path.exists() else None
    ontology = _load(ontology_path) if ontology_path.exists() else None
    diagnosis = _load(diagnosis_path) if diagnosis_path.exists() else None

    if not coverage:
        raise FileNotFoundError(f"Missing required artifact: {coverage_path}")
    if not deep_data:
        raise FileNotFoundError(f"Missing required artifact: {deep_data_path}")

    # Optional artifacts
    derived = _load(derived_path) if derived_path.exists() else None
    physics = _load(physics_path) if physics_path.exists() else None
    confidence = _load(confidence_path) if confidence_path.exists() else None
    graph_path = enhance_dir / "association_graph.json"
    association_graph = _load(graph_path) if graph_path.exists() else None

    # Compute CSV hash
    csv_path = run_dir / "02_processed" / "cleaned_data.csv"
    import hashlib
    if csv_path.exists():
        sha = hashlib.sha256()
        with open(csv_path, "rb") as f:
            sha.update(f.read())
        csv_hash = sha.hexdigest()
    else:
        csv_hash = ""

    # Count CSV rows/cols
    csv_rows = 0
    csv_cols = 0
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            header = f.readline()
            csv_cols = len(header.strip().split(","))
            csv_rows = sum(1 for _ in f)

    # Determine status
    status = determine_status(deep_data)

    # Build enhanced_knowledge
    nodes = build_nodes(coverage, ontology or {}, derived)
    edges = build_edges(deep_data, physics, association_graph)

    run_id = deep_data.get("run_id", "unknown")

    enhanced = {
        "run_id": run_id,
        "enhancement_status": status,
        "relationship_graph": {
            "nodes": nodes,
            "edges": edges,
        },
        "mechanism_chains": build_mechanism_chains(physics) if physics else [],
        "tradeoff_matrix": build_tradeoff_matrix(deep_data),
        "operability_summary": build_operability_summary(deep_data),
        "open_questions": build_open_questions(deep_data, physics, confidence),
        "evidence_gaps": build_evidence_gaps(physics, confidence),
        "provenance": {
            "source_artifacts": {
                "analysis_coverage": str(coverage_path),
                "derived_features": str(derived_path) if derived else "",
                "deep_data_analysis": str(deep_data_path),
                "association_graph": str(graph_path) if association_graph else "",
                "physics_bridge": str(physics_path) if physics else "",
                "ontology": str(ontology_path) if ontology else "",
                "diagnosis": str(diagnosis_path) if diagnosis else "",
            },
            "data_source": {
                "file": "cleaned_data.csv",
                "sha256": csv_hash,
                "rows": csv_rows,
                "cols": csv_cols,
            },
        },
    }

    # Write output
    _ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, ensure_ascii=False, indent=2)

    return enhanced


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Knowledge Fusion Engine — merge E1-E5 artifacts into enhanced_knowledge.json"
    )
    parser.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    parser.add_argument("--output", required=True, help="Output path for enhanced_knowledge.json")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    output_path = Path(args.output).resolve()

    if not run_dir.is_dir():
        print(f"ERROR: RUN_DIR not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        enhanced = fuse(run_dir, output_path)
        print(json.dumps({
            "status": "ok",
            "enhancement_status": enhanced["enhancement_status"],
            "nodes": len(enhanced["relationship_graph"]["nodes"]),
            "edges": len(enhanced["relationship_graph"]["edges"]),
            "mechanism_chains": len(enhanced["mechanism_chains"]),
            "output": str(output_path),
        }, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
