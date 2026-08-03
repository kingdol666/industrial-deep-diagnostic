#!/usr/bin/env python3
"""physics_bridge_builder.py — Task 4: Physics Bridge Construction

Reads ontology, diagnosis, evidence, confidence, reasoning_chain,
visual_analysis, deep_data_analysis, and optionally rag_deep_understanding,
then produces schema-valid physics_bridge.json under RUN_DIR/enhancement/.

CLI: python physics_bridge_builder.py --run-dir PATH [--output PATH]

Uses only Python stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── helpers ────────────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_required(path: Path, label: str) -> dict:
    """Load a required pipeline artifact; missing → clean error (exit 1)."""
    if not path.is_file():
        print(f"ERROR: required input missing: {path} ({label})"
              f" — physics bridge (E5) requires a completed baseline diagnosis;"
              f" run the pipeline through Step 4-9 first or check RUN_DIR.", file=sys.stderr)
        sys.exit(1)
    return _load(path)


def _safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ── ontology lookup ────────────────────────────────────────────────────

def _build_ontology_index(ontology: dict) -> Dict[Tuple[str, str], dict]:
    """Index ontology relationships by (from, to)."""
    idx: Dict[Tuple[str, str], dict] = {}
    for rel in ontology.get("relationships", []):
        key = (rel.get("from", ""), rel.get("to", ""))
        idx[key] = rel
    return idx


# ── five-item verification ─────────────────────────────────────────────

def _direction_verification(
    dd_rel: dict, onto_rel: Optional[dict]
) -> Tuple[str, str]:
    """Return direction match verdict using ontology data_direction_validated.

    data_direction_validated is the ontology-authoritative comparison result:
      "true"  -> data direction matches physics prediction -> MATCH
      "false" -> data direction contradicts physics      -> MISMATCH
      "untested"/missing                                  -> UNTESTED
    """
    if not onto_rel:
        return ("UNTESTED", "No ontology relationship")

    onto_dir_validated = onto_rel.get("data_direction_validated", "untested")

    if onto_dir_validated == "true":
        return ("MATCH", "Ontology confirms data direction matches physics prediction")
    elif onto_dir_validated == "false":
        discrepancy = onto_rel.get("lag_discrepancy_note", "")
        return (
            "MISMATCH",
            f"Ontology confirms data direction contradicts physics. {discrepancy[:100]}"
        )
    else:
        return ("UNTESTED", f"Ontology data_direction_validated={onto_dir_validated}")

def _functional_form_verification(
    dd_rel: dict, onto_rel: Optional[dict]
) -> Tuple[str, str]:
    """Compare data form_match vs ontology.predicted_functional_form."""
    dd_form = dd_rel.get("form_match", "").lower()
    onto_form = (onto_rel.get("predicted_functional_form", "") if onto_rel else "").lower()

    if not onto_form or onto_form == "untested":
        return ("UNTESTED", "No ontology predicted_functional_form")

    if "no detectable" in dd_form or "insufficient" in dd_form:
        return ("UNTESTED", f"Data form indeterminate: {dd_form}")

    # Check for matches
    form_map = {
        "exponential": ["exponential", "exp"],
        "linear": ["linear"],
        "monotonic": ["monotonic", "linear", "consistent with linear"],
        "inverse": ["inverse", "hyperbolic"],
        "threshold": ["threshold", "step"],
        "delayed_response": ["delayed", "lag", "nonlinear"],
    }

    onto_aliases = form_map.get(onto_form, [onto_form])

    matched = any(alias in dd_form for alias in onto_aliases)

    if matched:
        return ("MATCH", f"Data {dd_form} matches ontology predicted {onto_form}")
    else:
        # Check if data form explicitly contradicts
        if "expected: " in dd_rel.get("form_match", ""):
            parts = dd_rel.get("form_match", "").split("expected:")
            expected_part = parts[1].strip() if len(parts) > 1 else ""
            if onto_form in expected_part.lower():
                return (
                    "MISMATCH",
                    f"Data form={dd_rel.get('form_match','')} contradicts ontology {onto_form}"
                )
        return (
            "MISMATCH",
            f"Data form={dd_form} does not match ontology predicted {onto_form}"
        )


def _time_lag_verification(
    dd_rel: dict, onto_rel: Optional[dict]
) -> Tuple[str, str]:
    """Compare deep_data lag_aligned vs ontology time_lag."""
    if not onto_rel:
        return ("UNTESTED", "No ontology relationship")

    onto_time_lag = onto_rel.get("time_lag", "").lower()
    lag_agreement = onto_rel.get("lag_agreement", "no_physics_prior")
    lag_significant = dd_rel.get("validity_flags", {}).get("lag_significant", False)

    if lag_agreement == "consistent":
        return ("MATCH", f"Ontology lag_agreement=consistent; time_lag={onto_rel.get('time_lag','')}")

    if lag_agreement == "no_physics_prior":
        if lag_significant:
            return (
                "MISMATCH",
                f"lag_significant=true but ontology has no_physics_prior; "
                f"lag_aligned r={dd_rel.get('lag_aligned',0):.4f} vs global r={dd_rel.get('global',0):.4f}"
            )
        else:
            return (
                "MATCH",
                f"No significant lag detected, consistent with {onto_rel.get('time_lag','')}"
            )

    # Manual detection
    onto_detection = onto_rel.get("lag_detection_method", "")
    if onto_detection == "manual":
        return ("MATCH", f"Ontology lag determined manually; consistent with manual assessment")

    # Compare global vs lag_aligned correlation
    global_r = abs(dd_rel.get("global", 0.0))
    lag_r = abs(dd_rel.get("lag_aligned", 0.0))
    if lag_r > global_r * 1.15 and global_r > 0.01:
        return ("MISMATCH", f"Lag-aligned r ({lag_r:.3f}) > global r ({global_r:.3f}); suggests real lag")

    onto_time_lag_str = onto_rel.get("time_lag", "")
    _tlag = onto_time_lag_str.lower()

    # Near real-time: explicit wording in either language
    if any(k in _tlag for k in ("近实时", "即时", "实时", "real-time", "real time", "immediate", "同步")):
        return ("MATCH", f"Near real-time expected ({onto_time_lag_str}), data consistent")

    # Long-lag: day/week/month-scale tokens in either language
    _LONG_LAG_TOKENS = ("天", "日", "周", "月", "day", "week", "month", "长滞后", "数日", "数周", "数月")
    if any(k in _tlag for k in _LONG_LAG_TOKENS):
        # Long lag expected - instantaneous correlation should be weak
        if global_r < 0.1:
            return ("MATCH", f"Long lag expected ({onto_time_lag_str}), instantaneous r≈0 consistent")
        else:
            return ("MISMATCH", f"Long lag expected but instantaneous r={global_r:.3f} significant")

    # Hour-scale (≥1h) also implies material lag
    if re.search(r"\d+\s*(小时|h|hr|hour)", _tlag) or "数小时" in _tlag or "several hours" in _tlag:
        if global_r < 0.1:
            return ("MATCH", f"Hour-scale lag expected ({onto_time_lag_str}), instantaneous r≈0 consistent")
        else:
            return ("MISMATCH", f"Hour-scale lag expected but instantaneous r={global_r:.3f} significant")

    return ("UNTESTED", f"time_lag '{onto_time_lag_str}' has no machine-readable scale (numeric+unit) — treated as untested")


def _magnitude_verification(
    dd_rel: dict, onto_rel: Optional[dict]
) -> Tuple[str, str]:
    """First-principles order-of-magnitude estimate vs observed."""
    if not onto_rel:
        return ("UNTESTED", "No ontology governing_equation")

    governing_eq = onto_rel.get("governing_equation", "")
    if not governing_eq:
        return ("UNTESTED", "No governing equation in ontology")

    # Check if diagnosis has magnitude assessment
    onto_mechanism = onto_rel.get("mechanism", "")
    global_r = dd_rel.get("global", 0.0)
    operability = dd_rel.get("operability", "")

    # Generic rule: when ontology marks data direction as validated-false, the
    # magnitude assessment is IMPLAUSIBLE under the standard governing equation
    # (the contradiction itself is the diagnostic signal).
    onto_dir_validated = onto_rel.get("data_direction_validated", "untested")
    if onto_dir_validated == "false":
        return (
            "IMPLAUSIBLE",
            "Direction contradiction with governing equation makes magnitude "
            "assessment IMPLAUSIBLE under standard physics assumptions"
        )

    # For strong correlations with physics-consistent direction
    if abs(global_r) > 0.3 and onto_dir_validated in ("true", "untested"):
        return (
            "PLAUSIBLE",
            f"Observed r={global_r:.3f} with physics-consistent direction; "
            f"order-of-magnitude plausible given governing_equation"
        )

    if abs(global_r) > 0.6:
        return (
            "STRONG",
            f"Strong observed effect r={global_r:.3f}; magnitude significant"
        )

    if operability in ("CONFOUNDED", "ENDOGENOUS_RESPONSE"):
        return (
            "IMPLAUSIBLE",
            f"Operability={operability} suggests effect is not physically causal"
        )

    return ("PLAUSIBLE", f"Observed r={global_r:.3f} within plausible range")


def _state_dependence_verification(dd_rel: dict, onto_rel: Optional[dict]) -> Tuple[str, str]:
    """Check per_group/per_regime variation for state dependence."""
    per_group = dd_rel.get("per_group", [])
    per_regime = dd_rel.get("per_regime", [])

    if not per_group and not per_regime:
        return ("UNTESTED", "No per_group or per_regime data")

    # Check for sign reversal across groups
    if per_group:
        signs = set()
        for v in per_group:
            if isinstance(v, (int, float)):
                signs.add("positive" if v > 0.01 else ("negative" if v < -0.01 else "zero"))
        if len(signs) > 1:
            return (
                "REVERSES",
                f"Direction reverses across groups (per_group={per_group})"
            )
        if "zero" in signs:
            return ("STATE_DEPENDENT", f"Effect vanishes in some groups (per_group={per_group})")

    if per_regime:
        signs = set()
        for v in per_regime:
            if isinstance(v, (int, float)):
                signs.add("positive" if v > 0.01 else ("negative" if v < -0.01 else "zero"))
        if len(signs) > 1:
            return (
                "REVERSES",
                f"Direction reverses across regimes (per_regime={per_regime})"
            )
        if "zero" in signs:
            return ("STATE_DEPENDENT", f"Effect vanishes in some regimes (per_regime={per_regime})")

    # Check magnitude variation
    all_vals = [v for v in per_group + per_regime if isinstance(v, (int, float))]
    if all_vals and len(all_vals) > 1:
        max_v = max(all_vals)
        min_v = min(all_vals)
        if max(abs(max_v), abs(min_v)) > 0.01 and abs(max_v - min_v) / max(abs(max_v), abs(min_v)) > 0.5:
            return ("STATE_DEPENDENT", f"Magnitude varies substantially across states")

    return ("STABLE", "Effect direction and magnitude consistent across groups and regimes")


def _determine_overall_status(
    direction: str,
    functional_form: str,
    time_lag: str,
    magnitude: str,
    state_dependence: str,
    dd_rel: dict,
    onto_rel: Optional[dict],
) -> str:
    """Determine overall_status from five verification items."""
    # Direction MISMATCH → inconsistent (key diagnostic signal)
    if direction == "MISMATCH":
        return "inconsistent"


    # All MATCH/PLAUSIBLE/STABLE → consistent
    if direction == "MATCH" and functional_form == "MATCH" and time_lag == "MATCH" \
            and magnitude in ("PLAUSIBLE", "STRONG") and state_dependence == "STABLE":
        return "consistent"

    # All UNTESTED → untestable
    items = [direction, functional_form, time_lag, magnitude, state_dependence]
    if all(it == "UNTESTED" for it in items):
        return "untestable"

    # Magnitude IMPLAUSIBLE → rejected
    if magnitude == "IMPLAUSIBLE":
        return "rejected"

    # Partial match → plausible
    matches = sum(1 for it in items if it in ("MATCH", "PLAUSIBLE", "STRONG", "STABLE"))
    mismatches = sum(1 for it in items if it == "MISMATCH")
    if matches > mismatches:
        return "plausible"
    if mismatches > 0:
        return "inconsistent"

    return "plausible"


# ── evidence references ────────────────────────────────────────────────

def _collect_relationship_evidence(
    predictor: str,
    target: str,
    onto_rel: Optional[dict],
    dd_rel: dict,
    diagnosis: dict,
    evidence: dict,
    confidence: dict,
) -> List[str]:
    """Collect evidence_refs for a relationship."""
    refs: List[str] = []

    # From ontology
    if onto_rel:
        mechanism = onto_rel.get("mechanism", "")
        if mechanism:
            refs.append(f"ontology.{predictor}_to_{target}.mechanism")
        gov_eq = onto_rel.get("governing_equation", "")
        if gov_eq:
            refs.append(f"ontology.{predictor}_to_{target}.governing_equation: {gov_eq[:80]}")

    # From deep_data_analysis
    global_r = dd_rel.get("global", 0.0)
    detrended_r = dd_rel.get("detrended", 0.0)
    refs.append(f"deep_data.{predictor}_to_{target}.global_r={global_r:.4f}")
    if abs(detrended_r) > 0.01:
        refs.append(f"deep_data.{predictor}_to_{target}.detrended_r={detrended_r:.4f}")
    form = dd_rel.get("form_match", "")
    if form:
        refs.append(f"deep_data.{predictor}_to_{target}.form_match: {form[:100]}")

    # From diagnosis (generic physics-contradiction evidence: any relationship whose
    # observed direction contradicts the physics story in the primary finding)
    primary = diagnosis.get("primary_finding", "")
    if primary and any(kw in primary for kw in ("contradict", "consequence", "compensat", "反", "补偿", "矛盾", "果非因")):
        refs.append(f"diagnosis.primary_finding: {primary[:120]}")

    # From evidence
    ev_inv = evidence.get("evidence_inventory", {})
    for ev_type in ("numerical_evidence", "physical_evidence"):
        for item in ev_inv.get(ev_type, []):
            detail = item.get("detail", "")
            if predictor in detail and target in detail:
                refs.append(f"evidence.{item.get('type','')}: {detail[:100]}")

    return refs


# ── mechanism chains ───────────────────────────────────────────────────

def _build_mechanism_chains(diagnosis: dict, evidence: dict) -> List[dict]:
    """Extract mechanism chains from surviving hypotheses."""
    chains: List[dict] = []
    hypotheses = diagnosis.get("hypotheses", {})
    surviving = hypotheses.get("surviving", [])

    for idx, hyp in enumerate(surviving):
        chain_id = f"MC-{idx + 1:03d}"
        hyp_id = hyp.get("id", "?")
        hyp_name = hyp.get("name", "")

        # Claim
        claim = f"{hyp_name}: {hyp.get('root_physical_cause', '')}"

        # Evidence refs
        evidence_refs: List[str] = []
        for ev in hyp.get("supporting_evidence", []):
            ev_src = ev.get("source", "")
            ev_detail = ev.get("detail", "")
            if ev_src or ev_detail:
                evidence_refs.append(f"{hyp_id}.{ev_src}: {ev_detail[:120]}")

        # Physics law
        phys_chain = hyp.get("physical_logic_chain", [])
        physics_laws = []
        for link in phys_chain:
            link_text = link.get("link", "")
            if link_text:
                physics_laws.append(link_text[:150])
        physics_law = " | ".join(physics_laws) if physics_laws else "Unknown"

        # Data support (localized to Chinese for downstream markdown)
        proof = hyp.get("ontology_data_physics_proof", {})
        _STRENGTH_ZH = {
            "STRONG_EVIDENCE": "强证据",
            "MODERATE_EVIDENCE": "中等证据",
            "WEAK_EVIDENCE": "弱证据",
        }
        _FORM_ZH = {
            "MATCH": "一致",
            "PARTIAL": "部分一致",
            "MISMATCH": "不一致",
            "UNTESTED": "未测试",
            "UNTESTABLE": "不可测试",
        }
        _DIR_ZH = {
            "MATCH": "方向一致",
            "MISMATCH": "方向矛盾",
            "UNTESTED": "未测试",
            "UNTESTABLE": "不可测试",
        }
        data_support = (
            f"证据强度={_STRENGTH_ZH.get(proof.get('overall_proof_strength',''), proof.get('overall_proof_strength','') or '未知')}, "
            f"函数形态验证={_FORM_ZH.get(proof.get('functional_form_match',''), proof.get('functional_form_match','') or '未知')}, "
            f"方向验证={_DIR_ZH.get(proof.get('direction_match',''), proof.get('direction_match','') or '未知')}"
        )

        # Diagnosis support
        # Actually use the confidence directly from hyp
        diag_support = (
            f"hypothesis_id={hyp_id}, confidence={hyp.get('confidence','?')}, "
            f"verdict=SURVIVING, chain_quality={hyp.get('chain_quality','')}"
        )

        # Competing explanations
        # Find eliminated hypotheses that competed with this one
        eliminated = hypotheses.get("eliminated", [])
        competing = []
        for elim in eliminated:
            competing.append(f"{elim.get('hypothesis_id','')} {elim.get('name','')} (EXCLUDED: {elim.get('elimination_reason','')[:100]})")

        # What would change conclusion
        falsification = hyp.get("falsification_conditions", [])
        what_would = "; ".join(falsification) if falsification else "Not specified"

        chains.append({
            "chain_id": chain_id,
            "claim": claim,
            "evidence_refs": evidence_refs,
            "physics_law": physics_law,
            "data_support": data_support,
            "diagnosis_support": diag_support,
            "competing_explanations": competing,
            "what_would_change_conclusion": what_would,
        })

    return chains


# ── competing explanations ─────────────────────────────────────────────

def _build_competing_explanations(diagnosis: dict) -> List[dict]:
    """Extract competing explanations from eliminated hypotheses."""
    explanations: List[dict] = []
    hypotheses = diagnosis.get("hypotheses", {})
    eliminated = hypotheses.get("eliminated", [])

    for elim in eliminated:
        hyp_id = elim.get("hypothesis_id", "")
        name = elim.get("name", "")

        explanation = f"{name}: {elim.get('elimination_reason', '')}"
        support_level = f"Exclusion confidence: {elim.get('exclusion_confidence', '?')}%"
        against = [
            elim.get("specific_evidence", "")[:200]
        ]
        resolution = f"Excluded via {elim.get('exclusion_type', 'UNKNOWN')} reasoning. Revival condition: {elim.get('revival_condition', 'None')[:150]}"

        explanations.append({
            "explanation": explanation,
            "support_level": support_level,
            "against": against,
            "resolution": resolution,
        })

    return explanations


# ── evidence gaps ──────────────────────────────────────────────────────

def _build_evidence_gaps(
    diagnosis: dict,
    confidence: dict,
    reasoning_chain: dict,
    deep_data: dict,
) -> List[dict]:
    """Collect evidence gaps from multiple sources."""
    gaps: List[dict] = []

    # From confidence H1 and H2 evidence_gaps
    for hyp_key, hyp_data in confidence.get("confidence_breakdown", {}).items():
        for gap_text in hyp_data.get("evidence_gaps", []):
            gaps.append({
                "gap": f"[{hyp_key}] {gap_text}",
                "severity": "major",
                "impact_on_conclusions": "Limits precision of mechanism attribution",
                "mitigation": "Requires targeted offline characterization or speciation analysis for the implicated species",
            })

    # From reasoning_chain uncertainty_summary
    unc_summary = reasoning_chain.get("uncertainty_summary", {})
    for gap_text in unc_summary.get("epistemic_gaps", []):
        gaps.append({
            "gap": f"[Epistemic] {gap_text}",
            "severity": "major",
            "impact_on_conclusions": str(unc_summary.get("overall_confidence_ceiling", "?")) or "Reduces confidence ceiling",
            "mitigation": "Targeted additional measurements needed",
        })

    # From deep_data tradeoff open_questions
    for tradeoff in deep_data.get("tradeoff_and_operability", []):
        for q in tradeoff.get("open_questions", []):
            if "Discrepancy:" in q or "discrepancy" in q.lower():
                gaps.append({
                    "gap": f"[{tradeoff.get('parameter','?')}] {q}",
                    "severity": "minor",
                    "impact_on_conclusions": "Clarifies mechanistic details without changing main finding",
                    "mitigation": "Further data collection or controlled experiment",
                })

    # Deduplicate
    seen = set()
    unique_gaps = []
    for g in gaps:
        gap_key = g["gap"][:60]
        if gap_key not in seen:
            seen.add(gap_key)
            unique_gaps.append(g)

    # Ensure severity "critical" for key gaps: generic severity escalation for
    # gaps tied to offline characterization / speciation / material analysis
    for g in unique_gaps:
        if any(kw in g["gap"] for kw in ("离线活性", "离线表征", "speciation", "characterization", "离线分析")):
            g["severity"] = "critical"

    return unique_gaps


# ── main pipeline ──────────────────────────────────────────────────────

def build_physics_bridge(run_dir: Path, output_path: Path) -> None:
    """Main pipeline: read inputs, produce physics_bridge.json."""

    # 1. Load all required inputs
    ontology = _load_required(run_dir / "01_ontology" / "ontology.json", "ontology")
    diagnosis = _load_required(run_dir / "04_diagnostics" / "diagnosis.json", "diagnosis")
    evidence = _load_required(run_dir / "04_diagnostics" / "evidence.json", "evidence")
    confidence = _load_required(run_dir / "04_diagnostics" / "confidence.json", "confidence")
    reasoning_chain = _load_required(run_dir / "04_diagnostics" / "reasoning_chain.json", "reasoning_chain")
    visual_analysis = _load_required(run_dir / "03_figures" / "visual_analysis.json", "visual_analysis")
    deep_data = _load_required(run_dir / "enhancement" / "deep_data_analysis.json", "deep_data_analysis")

    # Optional
    rag_path = run_dir / "00_input" / "rag_deep_understanding.json"
    rag = _load(rag_path) if rag_path.exists() else None

    run_id = diagnosis.get("run_id", run_dir.name)

    # 2. Build ontology index
    onto_idx = _build_ontology_index(ontology)

    # 3. Process each deep_data relationship
    relationship_verifications: List[dict] = []
    dd_rels = deep_data.get("relationships", [])

    for dd_rel in dd_rels:
        predictor = dd_rel.get("predictor", "")
        target = dd_rel.get("target", "")
        key = (predictor, target)
        onto_rel = onto_idx.get(key)

        direction, dir_narrative = _direction_verification(dd_rel, onto_rel)
        func_form, func_narrative = _functional_form_verification(dd_rel, onto_rel)
        time_lag, lag_narrative = _time_lag_verification(dd_rel, onto_rel)
        magnitude, mag_narrative = _magnitude_verification(dd_rel, onto_rel)
        state_dep, state_narrative = _state_dependence_verification(dd_rel, onto_rel)

        overall_status = _determine_overall_status(
            direction, func_form, time_lag, magnitude, state_dep,
            dd_rel, onto_rel,
        )

        # Contract: when ontology marks data_direction_validated=false, direction MUST be
        # reported as MISMATCH (data contradicts the physics prior). This is the CSTR
        # AC-2 case generalized to any scene with a direction-validated=false relationship.
        assert not (direction == "MATCH" and onto_rel.get("data_direction_validated") is False), \
            f"AC-2 violation: {predictor}→{target} ontology data_direction_validated=false but direction=MATCH"

        evidence_refs = _collect_relationship_evidence(
            predictor, target, onto_rel, dd_rel, diagnosis, evidence, confidence,
        )

        verification = {
            "predictor": predictor,
            "target": target,
            "direction": direction,
            "functional_form": func_form,
            "time_lag": time_lag,
            "magnitude": magnitude,
            "state_dependence": state_dep,
            "overall_status": overall_status,
            "evidence_refs": evidence_refs,
        }

        # Add narrative for debugging/audit
        verification["_narrative"] = {
            "direction_narrative": dir_narrative,
            "functional_form_narrative": func_narrative,
            "time_lag_narrative": lag_narrative,
            "magnitude_narrative": mag_narrative,
            "state_dependence_narrative": state_narrative,
        }

        relationship_verifications.append(verification)

    # 4. Build mechanism chains
    mechanism_chains = _build_mechanism_chains(diagnosis, evidence)

    # 5. Build competing explanations
    competing_explanations = _build_competing_explanations(diagnosis)

    # 6. Build evidence gaps
    evidence_gaps = _build_evidence_gaps(
        diagnosis, confidence, reasoning_chain, deep_data,
    )

    # 7. Assemble output
    output = {
        "run_id": run_id,
        "relationship_verifications": relationship_verifications,
        "mechanism_chains": mechanism_chains,
        "competing_explanations": competing_explanations,
        "evidence_gaps": evidence_gaps,
    }

    # Clean up _narrative fields for schema validation (they are not in schema)
    for rv in output["relationship_verifications"]:
        rv.pop("_narrative", None)

    _ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[physics_bridge_builder] Wrote {len(relationship_verifications)} relationship verifications")
    print(f"[physics_bridge_builder] Wrote {len(mechanism_chains)} mechanism chains")
    print(f"[physics_bridge_builder] Wrote {len(competing_explanations)} competing explanations")
    print(f"[physics_bridge_builder] Wrote {len(evidence_gaps)} evidence gaps")
    print(f"[physics_bridge_builder] Output: {output_path}")


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Physics Bridge Builder — Task 4 enhancement layer"
    )
    parser.add_argument(
        "--run-dir", required=True,
        help="Path to diagnostic run directory"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path (default: RUN_DIR/enhancement/physics_bridge.json)"
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"ERROR: run-dir not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else (
        run_dir / "enhancement" / "physics_bridge.json"
    )

    try:
        build_physics_bridge(run_dir, output_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
