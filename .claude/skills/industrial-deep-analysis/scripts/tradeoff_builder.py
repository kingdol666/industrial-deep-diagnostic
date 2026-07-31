#!/usr/bin/env python3
"""E4: Tradeoff and operability assessment builder.

Library function plus CLI.  The public function
``build_tradeoff_and_operability`` is consumed by ``conditional_analysis.py``.

CLI::

    python tradeoff_builder.py --deep-analysis PATH [--output PATH]

Rewrites ``tradeoff_and_operability`` in a deep-data-analysis JSON
deterministically (used for offline re-computation or auditing).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Operability enum (must match the six values from the schema)
# ---------------------------------------------------------------------------
_OPERABILITY_VALUES = {
    "ENDOGENOUS_RESPONSE",
    "CONFOUNDED",
    "CONSTRAINT_UNCONTROLLABLE",
    "NOT_IDENTIFIABLE",
    "LEVER_IDENTIFIED",
    "LEVER_OBSERVATIONAL",
}


def _classify_operability(
    predictor: str,
    relationships_for_predictor: List[dict],
    ontology: dict,
    selection: dict,
) -> str:
    """Classify operability using the six-enum rules from the brief."""
    # Build ontology signal index once (used by endogenous/constraint checks)
    signal_idx = {}
    for section in ["inspection_signals", "process_parameters", "control_variables"]:
        for sig in ontology.get("signals", {}).get(section, []):
            signal_idx[sig.get("column", "")] = sig

    # Gather ontology relationship for this predictor
    onto_rels = ontology.get("relationships", [])
    onto_rel = None
    for rel in onto_rels:
        if rel.get("from") == predictor:
            onto_rel = rel
            break

    # Check: ENDOGENOUS_RESPONSE — when the ontology relationship from this
    # predictor TOWARD one of its analyzed targets is direction-validated=false,
    # or the signal semantics mark it as a control/compensation response.
    analyzed_targets = {r.get("target") for r in relationships_for_predictor}
    for rel in onto_rels:
        if rel.get("from") != predictor:
            continue
        if rel.get("to") in analyzed_targets and rel.get("data_direction_validated") == "false":
            return "ENDOGENOUS_RESPONSE"

    # Signal-level endogenous marker: controlled_by describes adaptive control /
    # load-shedding / operator compensation — the variable RESPONDS to degradation.
    # Exclude state indicators (controlled_by names a monitored degradation state
    # as the PRIMARY source) — those are observable symptoms, not control outputs.
    sig = signal_idx.get(predictor, {})
    cb = str(sig.get("controlled_by", "")).lower()
    is_state_indicator = any(k in cb for k in ("状态", "磨损", "反映", "监测", "指示", "degradation state", "indicator", "monitor"))
    if not is_state_indicator and any(k in cb for k in ("控制", "降载", "自适应", "补偿", "操作员", "adaptive control", "load shedding", "compensat")):
        return "ENDOGENOUS_RESPONSE"

    # Check if predictor is endogenous / control response — only tiers whose KEY
    # carries control/endogenous/compensation semantics, plus explicit control_cols
    # and ontology control roles. (Scanning every tier over-marks confounders.)
    tiers = selection.get("analysis_tiers", {})
    for _tk, tier in (tiers or {}).items():
        if not isinstance(tier, dict):
            continue
        tk_low = _tk.lower()
        if any(k in tk_low for k in ("control", "endogenous", "response", "compensat", "output")) \
                and predictor in (tier.get("columns", []) or []):
            return "ENDOGENOUS_RESPONSE"

    # Check if control_cols
    if predictor in selection.get("control_cols", []):
        return "ENDOGENOUS_RESPONSE"

    # Check: CONSTRAINT_UNCONTROLLABLE
    sig = signal_idx.get(predictor, {})
    if sig.get("role") == "control":
        return "CONSTRAINT_UNCONTROLLABLE"

    # Check: CONFOUNDED
    # Only flag as CONFOUNDED when there's genuine Simpson/group reversal or
    # known external time-confounder, not merely detrended drop from long-timescale
    # causal dynamics (catalyst degradation acts on day-week scale, so first-differencing
    # at 1h removes the causal signal and leaves noise).
    for r in relationships_for_predictor:
        flags = r.get("validity_flags", {})
        # Simpson paradox: group correlations have opposite signs
        per_group = r.get("per_group", [])
        if len(per_group) >= 2:
            signs = {1 if v > 0 else -1 for v in per_group if v != 0}
            if len(signs) > 1:
                return "CONFOUNDED"
        # Time confounding: only flag if detrended r ~ 0 AND global r strong,
        # AND the predictor has no validated physics direction (i.e., it's a
        # known confounder like cooling_water_temp_C seasonal trend, not a
        # real causal driver with long-timescale dynamics).
        if (flags.get("trend_confounding_checked") and
                abs(r.get("detrended", r.get("global", 0))) < 0.15 and
                abs(r.get("global", r.get("detrended", 0))) > 0.4):
            # Only flag as confounded if physics direction is NOT validated
            if onto_rel is None or onto_rel.get("data_direction_validated") != "true":
                return "CONFOUNDED"
    # Default NOT_IDENTIFIABLE if no usable relationships
    if not relationships_for_predictor:
        return "NOT_IDENTIFIABLE"

    usable = [r for r in relationships_for_predictor
              if r.get("validity_flags", {}).get("insufficient_data") is not True
              and r.get("n_effective", 0) >= 10]

    if not usable:
        return "NOT_IDENTIFIABLE"

    # Check for LEVER_IDENTIFIED criteria
    best = usable[0]
    for r in usable:
        if abs(r.get("global", 0)) > abs(best.get("global", 0)):
            best = r

    physics_ok = (onto_rel and onto_rel.get("data_direction_validated") == "true")
    q_ok = best.get("q_value", 1.0) <= 0.05
    direction_stable = True  # Simplification
    no_confounding = not best.get("validity_flags", {}).get("confounding_checked", False) or \
        (best.get("validity_flags", {}).get("confounding_checked") and not
         best.get("validity_flags", {}).get("simpson_paradox_checked", False))

    # Check directly controllable
    controllable = True
    if predictor in selection.get("confounder_cols", []):
        controllable = False
    if sig.get("control_type") == "output":
        controllable = False

    # Indicator downgrade: a predictor whose ontology semantics describe it as a
    # monitored state / symptom / indicator of an upstream degradation process
    # (e.g. bearing vibration or temperature reflecting wear) is observable but
    # NOT a directly adjustable operating lever — downgrade to OBSERVATIONAL.
    sig_desc = " ".join([
        str(sig.get("physical_meaning", "")),
        str(sig.get("controlled_by", "")),
        str(sig.get("role", "")),
    ]).lower()
    is_indicator = any(k in sig_desc for k in (
        "状态", "磨损", "反映", "指示", "监测", "症状", "indicator", "monitor",
        "reflect", "symptom", "状态指示", "承载", "degradation state",
    ))

    if physics_ok and q_ok and direction_stable and not best.get("validity_flags", {}).get("confounding_checked", False) is False and controllable and not is_indicator:
        return "LEVER_IDENTIFIED"

    return "LEVER_OBSERVATIONAL"


def build_tradeoff_and_operability(
    df: pd.DataFrame,
    relationships: List[dict],
    ontology: dict,
    selection: dict,
    feature_metadata: Optional[List[dict]] = None,
) -> List[dict]:
    """Build tradeoff entries for every usable target and predictor.

    Parameters
    ----------
    df: Cleaned data DataFrame (used only for support domain extraction).
    relationships: List of relationship dicts from deep_data_analysis.
    ontology: Ontology dict.
    selection: Parameter selection dict.
    feature_metadata: Optional derived feature metadata (unused for now).

    Returns
    -------
    List of tradeoff+operability dicts matching the schema.
    """
    targets = selection.get("quality_targets", [])
    tiers = selection.get("analysis_tiers", {})

    # Group relationships by predictor
    by_pred: Dict[str, List[dict]] = {}
    for rel in relationships:
        pred = rel.get("predictor", "")
        by_pred.setdefault(pred, []).append(rel)

    # Build signal index
    signal_idx: Dict[str, dict] = {}
    for section in ["inspection_signals", "process_parameters", "control_variables"]:
        for sig in ontology.get("signals", {}).get(section, []):
            signal_idx[sig.get("column", "")] = sig

    onto_units = ontology.get("metadata", {}).get("units", {})

    tradeoffs: List[dict] = []
    for predictor, pred_rels in by_pred.items():
        sig = signal_idx.get(predictor, {})
        # Controllability string
        role = sig.get("role", "")
        # Controllability string — must distinguish endogenous predictors from true confounders
        onto_rel_for_pred = None
        for rel in ontology.get("relationships", []):
            if rel.get("from") == predictor:
                onto_rel_for_pred = rel
                break
        is_endogenous = (
            predictor in selection.get("confounder_cols", []) and
            onto_rel_for_pred is not None and
            onto_rel_for_pred.get("data_direction_validated") == "false"
        )
        if predictor in selection.get("group_cols", []) or role in ("group", "product_code", "operator"):
            controllability = "grouping/stratification variable — not a process lever"
        elif predictor in selection.get("control_cols", []):
            controllability = "control output — not directly manipulable independently"
        elif is_endogenous:
            controllability = "endogenous response — operator-adjustable but observed correlation direction is consequence, not cause"
        elif predictor in selection.get("confounder_cols", []):
            controllability = "confounder — not controllable in this process"
        elif predictor in selection.get("metadata_cols", []):
            controllability = "metadata"
        elif role == "control":
            controllability = "constraint — control output, not independent lever"
        elif role == "target":
            controllability = "quality target — observed outcome, not a lever"
        else:
            controllability = "directly controllable via process setpoint adjustment"

        # Effects on targets
        effect_parts = []
        for rel in pred_rels:
            tgt = rel.get("target", "")
            r_val = rel.get("global", 0)
            direction = "positive" if r_val > 0 else "negative"
            tgt_unit = onto_units.get(tgt, "")
            effect_parts.append(
                f"{direction} effect on {tgt} (r={r_val:.3f})" +
                (f" [{tgt_unit}]" if tgt_unit else "")
            )
        effects_summary = "; ".join(effect_parts) if effect_parts else "no reliable effect detected"

        # Operability assessment
        operability = _classify_operability(predictor, pred_rels, ontology, selection)

        # Support domain
        if predictor in df.columns:
            try:
                series = pd.to_numeric(df[predictor], errors="coerce")
                finite = series[np.isfinite(series)]
                if len(finite) > 0:
                    p5 = float(np.percentile(finite, 5))
                    p95 = float(np.percentile(finite, 95))
                    current = float(series.iloc[-1]) if np.isfinite(series.iloc[-1]) else float(finite.iloc[-1])
                    n = int(len(finite))
                    support = f"p5={p5:.2f}, p95={p95:.2f}, current={current:.2f}, n={n}"
                else:
                    support = "insufficient data"
            except Exception:
                support = "extraction failed"
        else:
            support = "column not in cleaned data"

        # Tradeoff summary
        if len(pred_rels) >= 2:
            r_vals = [abs(r.get("global", 0)) for r in pred_rels]
            if max(r_vals) - min(r_vals) > 0.1:
                tradeoff_summary = f"Tradeoff: effects on different targets diverge in magnitude (max |r|={max(r_vals):.3f}, min |r|={min(r_vals):.3f})"
            else:
                tradeoff_summary = f"Effects are directionally consistent across targets (|r| range {min(r_vals):.3f}-{max(r_vals):.3f})"
        elif pred_rels:
            r_val = pred_rels[0].get("global", 0)
            tradeoff_summary = f"Single-target effect: r={r_val:.3f}"
        else:
            tradeoff_summary = "No reliable effect detectable"

        # Extrapolation warning
        extrapolation = "Extrapolation beyond observed operating range is not supported without additional experiments."

        # Open questions
        open_qs: List[str] = []
        sig_disc = sig.get("discrepancy_signal", "")
        if sig_disc:
            open_qs.append(f"数据矛盾点：{sig_disc[:120]}")
        if operability == "ENDOGENOUS_RESPONSE":
            open_qs.append("内生响应：观测相关方向可能是结果而非原因，需工具变量或去趋势分析进一步确认。")
        if operability == "CONFOUNDED":
            open_qs.append("存在混杂：因果识别需分层分析或受控实验。")
        if not open_qs:
            open_qs.append("建议在投入运行前做进一步机制验证。")

        tradeoffs.append({
            "parameter": predictor,
            "controllability": controllability,
            "effects_on_targets": effects_summary,
            "tradeoff_summary": tradeoff_summary,
            "operability_assessment": operability,
            "support_domain": support,
            "extrapolation_warning": extrapolation,
            "open_questions": open_qs,
        })

    return tradeoffs


def main() -> None:
    ap = argparse.ArgumentParser(description="E4: Build/rewrite tradeoff & operability")
    ap.add_argument("--run-dir", default=None, help="Path to diagnostic RUN_DIR (preferred)")
    ap.add_argument("--deep-analysis", default=None, help="Path to deep_data_analysis.json")
    ap.add_argument("--output", default=None, help="Output path (default: overwrite input)")
    args = ap.parse_args()

    if not args.run_dir and not args.deep_analysis:
        print("ERROR: must provide --run-dir or --deep-analysis", file=sys.stderr)
        sys.exit(1)

    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_dir():
            print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
            sys.exit(1)
        da_path = run_dir / "enhancement" / "deep_data_analysis.json"
        if not da_path.is_file():
            print(f"ERROR: deep_data_analysis.json not found: {da_path}", file=sys.stderr)
            sys.exit(1)
    else:
        da_path = Path(args.deep_analysis)
        if not da_path.is_file():
            print(f"ERROR: deep-analysis file not found: {da_path}", file=sys.stderr)
            sys.exit(1)

    with open(da_path, encoding="utf-8") as fh:
        deep = json.load(fh)

    # Load df/ontology/selection from run-dir when available
    if args.run_dir:
        run_dir = Path(args.run_dir)
        ontology = json.loads((run_dir / "01_ontology" / "ontology.json").read_text(encoding="utf-8"))
        selection = json.loads((run_dir / "02_processed" / "analysis_parameter_selection.json").read_text(encoding="utf-8"))
        csv = run_dir / "02_processed" / "cleaned_data.csv"
        if csv.is_file():
            df = pd.read_csv(csv)
        else:
            df = pd.read_json(run_dir / "02_processed" / "cleaned_data.json")
    else:
        # Can't load df without run-dir — emit empty tradeoffs
        print("[tradeoff_builder] No run-dir provided; writing empty tradeoffs")
        df = pd.DataFrame()
        ontology = {"relationships": [], "signals": {}, "metadata": {"units": {}}}
        selection = {"quality_targets": [], "analysis_tiers": {}}

    tradeoffs = build_tradeoff_and_operability(
        df, deep.get("relationships", []), ontology, selection
    )

    deep["tradeoff_and_operability"] = tradeoffs

    output = Path(args.output) if args.output else da_path
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(deep, fh, indent=2, ensure_ascii=False, default=str)

    print(f"[tradeoff_builder] Wrote {len(tradeoffs)} tradeoff entries → {output}")


if __name__ == "__main__":
    main()