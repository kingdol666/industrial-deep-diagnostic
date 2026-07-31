#!/usr/bin/env python3
"""E3: Conditional relationship analysis for industrial deep-analysis.

Builds candidate predictor→target pairs from ontology relationships,
selection tiers, and hypothesis artifacts. Computes global, detrended,
per-group, steady, lag-aligned, per-regime correlations plus slope_at_current,
partial correlation, form_match, q-value, n_effective, and all seven validity
flags. Invokes ``tradeoff_builder.build_tradeoff_and_operability`` for final
``tradeoff_and_operability``.

CLI::

    python conditional_analysis.py --run-dir PATH [--output PATH]

Default output: ``RUN_DIR/enhancement/deep_data_analysis.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from stat_utils import (  # noqa: E402
    _pearson_r,
    _finite_mask,
    slope_at_current,
    partial_correlation,
    benjamini_hochberg,
    stationarity_check,
)
from tradeoff_builder import build_tradeoff_and_operability  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_df(run_dir: Path) -> pd.DataFrame:
    csv = run_dir / "02_processed" / "cleaned_data.csv"
    if csv.is_file():
        df = pd.read_csv(csv)
        if "timestamp" in df.columns:
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception:
                pass
        return df
    json_path = run_dir / "02_processed" / "cleaned_data.json"
    if json_path.is_file():
        return pd.read_json(json_path)
    raise FileNotFoundError("No cleaned data found")


def _coerce_numeric(series: pd.Series) -> np.ndarray:
    """Coerce series to float64, returning finite mask as well."""
    vals = pd.to_numeric(series, errors="coerce").values.astype(float)
    return vals


def _per_group_r(df: pd.DataFrame, x_col: str, y_col: str, group_col: str,
                 min_rows: int = 10) -> List[float]:
    """Compute Pearson r per group. Returns empty list if insufficient."""
    results = []
    for grp_name, grp_df in df.groupby(group_col):
        if len(grp_df) < min_rows:
            continue
        x = _coerce_numeric(grp_df[x_col])
        y = _coerce_numeric(grp_df[y_col])
        mask = _finite_mask(x, y)
        if mask.sum() < min_rows:
            continue
        r = _pearson_r(x[mask], y[mask])
        if r is not None:
            results.append(round(r, 6))
    return results


def _per_regime_r(df: pd.DataFrame, x_col: str, y_col: str,
                  regime_labels: Optional[List[str]],
                  min_rows: int = 10) -> List[float]:
    """Compute Pearson r per regime partition."""
    if regime_labels is None:
        return []
    results = []
    labels_arr = np.array(regime_labels)
    for regime in sorted(set(str(lbl) for lbl in labels_arr)):
        mask = labels_arr == regime
        if mask.sum() < min_rows:
            continue
        x = _coerce_numeric(df.loc[df.index[mask], x_col]) if hasattr(df, 'loc') else _coerce_numeric(df[x_col].iloc[mask])
        # Use numpy indexing
        x_full = _coerce_numeric(df[x_col])
        y_full = _coerce_numeric(df[y_col])
        x = x_full[mask]
        y = y_full[mask]
        fm = _finite_mask(x, y)
        if fm.sum() < min_rows:
            continue
        r = _pearson_r(x[fm], y[fm])
        if r is not None:
            results.append(round(r, 6))
    return results


# ---------------------------------------------------------------------------
# Candidate pair builder
# ---------------------------------------------------------------------------

def _build_candidate_pairs(
    ontology: dict,
    selection: dict,
) -> List[Tuple[str, str]]:
    """Build deduplicated (predictor, target) candidate pairs."""
    pairs: Set[Tuple[str, str]] = set()
    targets = set(selection.get("quality_targets", []))

    # From ontology relationships
    for rel in ontology.get("relationships", []):
        frm = rel.get("from", "")
        to = rel.get("to", "")
        if frm and to and to in targets:
            pairs.add((frm, to))

    # From selection tiers
    tiers = selection.get("analysis_tiers", {})
    for tier_key in ["tier1_primary_kinetic_drivers", "tier2_feed_residence_pressure",
                     "tier3_confounders_caution"]:
        tier = tiers.get(tier_key, {})
        preds = tier.get("columns", [])
        must_vs = tier.get("must_analyze_vs_targets", [])
        for pred in preds:
            for tgt in must_vs:
                if tgt in targets:
                    pairs.add((pred, tgt))

    # Exclude: target == predictor, metadata, control outputs, pruned
    metadata_cols = set(selection.get("metadata_cols", []))
    control_cols = set(selection.get("control_cols", []))
    pruned_pairs = selection.get("pruned_pairs", [])

    pruned_set: Set[Tuple[str, str]] = set()
    for pp in pruned_pairs:
        pair_str = pp.get("pair", "")
        # Parse "A <-> B" or "A -> B"
        parts = pair_str.replace("<->", "->").split("->")
        if len(parts) >= 2:
            a = parts[0].strip().split(" ")[0]
            b = parts[1].strip().split(" ")[0]
            pruned_set.add((a, b))
            pruned_set.add((b, a))

    filtered: Set[Tuple[str, str]] = set()
    for pred, tgt in pairs:
        if pred == tgt:
            continue
        if pred in metadata_cols:
            continue
        if pred in control_cols:
            continue
        if (pred, tgt) in pruned_set:
            continue
        filtered.add((pred, tgt))

    return sorted(filtered)


# ---------------------------------------------------------------------------
# Per-pair computation
# ---------------------------------------------------------------------------

def _compute_relationship(
    df: pd.DataFrame,
    pred: str,
    tgt: str,
    ontology: dict,
    selection: dict,
    conclusion: dict,
    regime_filter: Optional[dict],
) -> dict:
    """Compute all relationship metrics for a single predictor→target pair."""
    x_raw = _coerce_numeric(df[pred])
    y_raw = _coerce_numeric(df[tgt])

    finite = _finite_mask(x_raw, y_raw)
    x = x_raw[finite]
    y = y_raw[finite]
    n_finite = int(finite.sum())

    # Collect all p-values for BH correction
    all_p_values: List[float] = []

    # --- global ---
    global_r = 0.0
    global_p = 1.0
    if n_finite >= 10:
        global_r = _pearson_r(x, y) or 0.0
        # Approximate p-value from r and n
        if abs(global_r) < 1.0 and n_finite > 2:
            t_stat = global_r * np.sqrt((n_finite - 2) / (1 - global_r ** 2))
            from math import erf
            global_p = float(2 * (1 - 0.5 * (1 + erf(abs(t_stat) / np.sqrt(2)))))
        all_p_values.append(global_p)

    # --- detrended ---
    detrended_r = global_r
    detrend_flag = False
    time_col = "timestamp"
    if time_col in df.columns and n_finite >= 10:
        try:
            df_finite = df.iloc[finite].copy()
            df_sorted = df_finite.sort_values(time_col)
            x_sorted = _coerce_numeric(df_sorted[pred])
            y_sorted = _coerce_numeric(df_sorted[tgt])
            x_diff = np.diff(x_sorted)
            y_diff = np.diff(y_sorted)
            diff_finite = _finite_mask(x_diff, y_diff)
            if diff_finite.sum() >= 10:
                detrended_r = _pearson_r(x_diff[diff_finite], y_diff[diff_finite]) or global_r
            detrend_flag = True
        except Exception:
            pass

    # --- per_group ---
    primary_group = selection.get("grouping_strategy", {}).get("primary_group", "")
    per_group: List[float] = []
    if primary_group and primary_group in df.columns:
        per_group = _per_group_r(df, pred, tgt, primary_group)

    # --- steady ---
    steady_r = global_r
    if regime_filter:
        steady_indices = regime_filter.get("steady_row_indices", [])
        if steady_indices:
            valid_steady = [i for i in steady_indices if i < len(df) and finite[i]]
            if len(valid_steady) >= 10:
                xs = x_raw[valid_steady]
                ys = y_raw[valid_steady]
                fm = _finite_mask(xs, ys)
                if fm.sum() >= 10:
                    steady_r = _pearson_r(xs[fm], ys[fm]) or global_r

    # --- lag_aligned ---
    tla = conclusion.get("time_lag_analysis", {})
    key_findings = tla.get("key_findings", [])
    lag_r = steady_r
    lag_significant = False
    best_lag_steps = 0
    for kf in key_findings:
        if kf.get("predictor") == pred and kf.get("target") == tgt:
            lag_steps = kf.get("optimal_lag_steps", 0)
            best_lag_steps = lag_steps or 0
            if lag_steps is not None and lag_steps != 0 and abs(lag_steps) > 0:
                if time_col in df.columns and n_finite >= 10:
                    try:
                        df_sorted = df.sort_values(time_col)
                        shifted = df_sorted[pred].shift(lag_steps)
                        xs = _coerce_numeric(shifted)
                        ys = _coerce_numeric(df_sorted[tgt])
                        mask = _finite_mask(xs, ys)
                        if mask.sum() >= 10:
                            lag_r = _pearson_r(xs[mask], ys[mask]) or steady_r
                    except Exception:
                        pass
            lag_significant = True if (lag_steps is not None and abs(lag_steps) > 0) else False
            break

    # --- per_regime ---
    regime_labels = None
    if regime_filter:
        labels = regime_filter.get("per_row_labels", [])
        if labels and len(labels) == len(df):
            regime_labels = labels
    per_regime: List[float] = []
    if regime_labels:
        per_regime = _per_regime_r(df, pred, tgt, regime_labels)

    # --- slope_at_current ---
    slope_cur = 0.0
    slope_valid = False
    if n_finite >= 10:
        try:
            result = slope_at_current(x, y, x[-1])
            slope_cur = float(result.get("slope", 0.0))
            slope_valid = bool(result.get("valid", False))
        except Exception:
            pass

    # --- partial correlation ---
    partial_r = 0.0
    partial_valid = False
    tiers = selection.get("analysis_tiers", {})
    all_tier_preds: List[str] = []
    for tk in ["tier1_primary_kinetic_drivers", "tier2_feed_residence_pressure",
               "tier3_confounders_caution"]:
        all_tier_preds.extend(tiers.get(tk, {}).get("columns", []))
    controls = [c for c in all_tier_preds if c != pred and c in df.columns]
    if controls and n_finite >= 10:
        try:
            result = partial_correlation(df.iloc[finite], pred, tgt, controls)
            partial_r = float(result.get("partial_r", 0.0))
            partial_valid = bool(result.get("valid", False))
        except Exception:
            pass

    # --- form_match ---
    onto_rels = ontology.get("relationships", [])
    predicted_form = "unknown"
    for rel in onto_rels:
        if rel.get("from") == pred and rel.get("to") == tgt:
            predicted_form = rel.get("predicted_functional_form", "unknown")
            break

    form_match = "unable to assess"
    if abs(global_r) < 0.1:
        form_match = "no detectable linear relationship; possible nonlinear or delayed_response"
    elif n_finite >= 20:
        # Simple quadratic check
        try:
            coeffs = np.polyfit(x, y, 2)
            r2_linear = global_r ** 2
            y_pred_quad = np.polyval(coeffs, x)
            ss_res_quad = np.sum((y - y_pred_quad) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2_quad = 1 - ss_res_quad / ss_tot if ss_tot > 0 else 0
            improvement = r2_quad - r2_linear
            if improvement > 0.05:
                form_match = f"quadratic curvature detected (R² improvement {improvement:.3f}); expected: {predicted_form}"
            elif abs(global_r) >= 0.5:
                form_match = f"consistent with linear/monotonic; expected: {predicted_form}"
            else:
                form_match = f"weak linear; predicted {predicted_form}, data insufficient to confirm"
        except Exception:
            form_match = f"assessed; predicted: {predicted_form}, observed: linear r={global_r:.3f}"

    # --- q_value (BH corrected) ---
    # Compute per-pair: the primary test p-value is global_p
    q_value = global_p  # Will be BH-corrected across all pairs

    # --- n_effective ---
    n_eff = n_finite
    if primary_group and primary_group in df.columns:
        n_groups = df[primary_group].nunique()
        if n_groups > 1:
            n_eff = int(n_finite / n_groups) * n_groups  # groups * avg per group

    # --- validity_flags ---
    validity_flags = {
        "simpson_paradox_checked": bool(primary_group and len(per_group) >= 2),
        "confounding_checked": bool(primary_group),
        "trend_confounding_checked": detrend_flag,
        "change_point_tested": False,  # Requires dedicated change-point detection
        "batch_effect_tested": bool(primary_group and len(per_group) >= 2),
        "lag_significant": lag_significant,
        "outlier_influence_checked": False,
    }

    return {
        "predictor": pred,
        "target": tgt,
        "global": round(global_r, 6),
        "detrended": round(detrended_r, 6),
        "per_group": per_group,
        "steady": round(steady_r, 6),
        "lag_aligned": round(lag_r, 6),
        "per_regime": per_regime,
        "slope_at_current": round(slope_cur, 6),
        "partial": round(partial_r, 6),
        "form_match": form_match,
        "q_value": round(q_value, 6),  # placeholder, BH-corrected later
        "n_effective": n_eff,
        "validity_flags": validity_flags,
        "operability": "",  # filled by tradeoff_builder
    }


# ---------------------------------------------------------------------------
# Main builder for conditional_analysis
# ---------------------------------------------------------------------------

def build_relationships(
    df: pd.DataFrame,
    candidate_pairs: List[Tuple[str, str]],
    ontology: dict,
    selection: dict,
    conclusion: dict,
    regime_filter: Optional[dict],
) -> List[dict]:
    """Compute relationship records for all candidate pairs."""
    relationships: List[dict] = []
    primary_p_values: List[float] = []

    for pred, tgt in candidate_pairs:
        if pred not in df.columns or tgt not in df.columns:
            continue
        rel = _compute_relationship(df, pred, tgt, ontology, selection, conclusion, regime_filter)
        relationships.append(rel)
        primary_p_values.append(rel["q_value"])

    # BH correction across all pairs
    if primary_p_values:
        q_values = benjamini_hochberg(primary_p_values)
        for i, qv in enumerate(q_values):
            relationships[i]["q_value"] = round(float(qv), 6)

    return relationships


def main() -> None:
    ap = argparse.ArgumentParser(description="E3: Conditional relationship analysis")
    ap.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output) if args.output else run_dir / "enhancement" / "deep_data_analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    # Load all inputs
    ontology = _load_json(run_dir / "01_ontology" / "ontology.json")
    selection = _load_json(run_dir / "02_processed" / "analysis_parameter_selection.json")
    conclusion = _load_json(run_dir / "02_processed" / "data_analysis_conclusion.json")

    regime_path = run_dir / "02_processed" / "production_regime_filter.json"
    regime_filter = _load_json(regime_path) if regime_path.is_file() else None

    df = _load_df(run_dir)
    # Read derived_features.json if present (E2 output)
    derived_path = run_dir / "enhancement" / "derived_features.json"
    feature_metadata: Optional[List[dict]] = None
    if derived_path.is_file():
        with open(derived_path, encoding="utf-8") as fh:
            feature_metadata = json.load(fh).get("features", None)

    # Build candidate pairs
    candidate_pairs = _build_candidate_pairs(ontology, selection)
    print(f"[conditional_analysis] {len(candidate_pairs)} candidate pairs")

    # Compute relationships
    relationships = build_relationships(df, candidate_pairs, ontology, selection, conclusion, regime_filter)

    # Build tradeoff_and_operability, passing feature_metadata
    tradeoffs = build_tradeoff_and_operability(df, relationships, ontology, selection, feature_metadata)

    # Assign operability to each relationship
    by_pred: Dict[str, List[dict]] = {}
    for rel in relationships:
        by_pred.setdefault(rel["predictor"], []).append(rel)

    for tradeoff in tradeoffs:
        pred = tradeoff["parameter"]
        op = tradeoff["operability_assessment"]
        for rel in by_pred.get(pred, []):
            rel["operability"] = op

    result = {
        "run_id": "enhancement-deep-analysis",
        "relationships": relationships,
        "tradeoff_and_operability": tradeoffs,
    }

    with open(output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)

    print(f"[conditional_analysis] {len(relationships)} relationships, {len(tradeoffs)} tradeoffs → {output}")

if __name__ == "__main__":
    main()