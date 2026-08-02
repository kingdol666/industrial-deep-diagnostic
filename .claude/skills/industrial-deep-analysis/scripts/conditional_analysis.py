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
    safe_p_value,
    stationarity_check,
)
from inference_engine import (  # noqa: E402
    temporal_causality,
    change_point_co_movement,
    conditional_independence,
    leverage_stability,
    moderator_check,
    mediation_scan,
    causality_ceiling,
    build_association_graph,
    pairwise_scan,
    MIN_ABS_R,
    Q_THRESHOLD,
    MIN_PAIR_N,
    DIRECT_MIN_PARTIAL,
    INDIRECT_MAX_PARTIAL,
)
from tradeoff_builder import build_tradeoff_and_operability  # noqa: E402

# Cache of change-point positions per column (df fixed per run)
_CP_CACHE: Dict[str, List[int]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_df(run_dir: Path) -> pd.DataFrame:
    # Prefer the E2-derived data file so computed derived features are available
    derived_csv = run_dir / "enhancement" / "derived_data.csv"
    if derived_csv.is_file():
        df = pd.read_csv(derived_csv)
        if "timestamp" in df.columns:
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception:
                pass
        return df
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

def _strip_suffix(name: str) -> str:
    """Strip common aggregation suffixes so ontology/selection names match actual columns.

    E.g. 'F_PS002@PV1_mean' -> 'F_PS002@PV1', 'reactor_temp_C_dev' -> 'reactor_temp_C'.
    """
    for suffix in ("_mean", "_median", "_std", "_dev", "_avg", "_max", "_min"):
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _resolve_col(name: str, df_cols: set) -> Optional[str]:
    """Resolve a possibly-suffixed name to an actual DataFrame column."""
    if name in df_cols:
        return name
    stripped = _strip_suffix(name)
    for col in df_cols:
        if _strip_suffix(col) == stripped:
            return col
    return None


def _build_candidate_pairs(
    ontology: dict,
    selection: dict,
    df_columns: Optional[List[str]] = None,
    derived_features: Optional[List[dict]] = None,
) -> List[Tuple[str, str]]:
    """Build deduplicated (predictor, target) candidate pairs.

    Resolves ontology/tier names against the actual DataFrame columns so
    suffix drift (e.g. '_mean' in cleaned columns) cannot silently drop pairs.
    Also adds computed derived features (E2 output) as candidate predictors
    against every quality target — e.g. cumulative_sulfur exposure vs conversion.
    """
    pairs: Set[Tuple[str, str]] = set()
    targets = set(selection.get("quality_targets", []))
    df_cols = set(df_columns or [])

    def _resolve_tgt(name: str) -> Optional[str]:
        if df_cols:
            return _resolve_col(name, df_cols)
        return name

    # From ontology relationships (always included; the relationship target may
    # be a process parameter — process→process edges are the backbone of the
    # association logic, e.g. vibration→temperature dual-channel wear evidence)
    for rel in ontology.get("relationships", []):
        frm = rel.get("from", "")
        to = rel.get("to", "")
        tgt = _resolve_tgt(to)
        if not frm or not tgt:
            continue
        pairs.add((_resolve_col(frm, df_cols) or frm, tgt))

    # From selection tiers — scan ALL tier keys dynamically, supporting three shapes:
    #   A) {key: {columns: [...], must_analyze_vs_targets: [...]}}  (CSTR/BOPET style)
    #   B) {key: {columns: [...]}}                                   (thin style)
    #   C) {key: [{target, predictor, ...}, ...]}                    (pair-object style)
    tiers = selection.get("analysis_tiers", {})
    for tier_key, tier in (tiers or {}).items():
        if isinstance(tier, dict):
            preds = tier.get("columns", []) or []
            must_vs = tier.get("must_analyze_vs_targets", []) or []
            if not must_vs:
                must_vs = list(targets)
            for pred in preds:
                for tgt in must_vs:
                    resolved_tgt = _resolve_tgt(tgt)
                    if targets and resolved_tgt not in targets:
                        continue
                    pairs.add((_resolve_col(pred, df_cols) or pred, resolved_tgt))
        elif isinstance(tier, list):
            for item in tier:
                if not isinstance(item, dict):
                    continue
                pred = item.get("predictor", "")
                tgt = item.get("target", "")
                if not pred or not tgt:
                    continue
                # Tier pairs are declared analysis targets (may be process
                # parameters, e.g. control-endogenous checks) — keep as declared.
                pairs.add((_resolve_col(pred, df_cols) or pred, _resolve_tgt(tgt) or tgt))

    # Also add direct selection predictor_cols -> quality_targets when tier info is thin
    for pred in selection.get("predictor_cols", []):
        for tgt in targets:
            resolved_tgt = _resolve_tgt(tgt)
            if resolved_tgt in targets:
                pairs.add((_resolve_col(pred, df_cols) or pred, resolved_tgt))

    # Add computed derived features (E2) as candidate predictors against all targets
    for feat in derived_features or []:
        if feat.get("status") != "computed":
            continue
        fname = feat.get("name", "")
        if not fname:
            continue
        # Regime one-hot partitions are moderators, not numeric drivers — they
        # are covered by per_regime analysis; feeding them as linear predictors
        # produces meaningless binary-vs-continuous correlations.
        if fname.startswith("regime_"):
            continue
        resolved = _resolve_col(fname, df_cols) or fname
        for tgt in targets:
            resolved_tgt = _resolve_tgt(tgt)
            if resolved_tgt in targets:
                pairs.add((resolved, resolved_tgt))

    # Process-only fallback: when the scene declares no quality targets, analyze
    # relationships among process parameters themselves (physics-driven pairs only)
    if not targets:
        proc_cols = [c for c in selection.get("predictor_cols", []) if _resolve_col(c, df_cols)]
        proc_cols = [(_resolve_col(c, df_cols) or c) for c in proc_cols]
        for i, pa in enumerate(proc_cols):
            for pb in proc_cols[i + 1:]:
                pairs.add((pa, pb))
        # ontology relationships already added above cover process-to-process edges

    # Exclude: target == predictor, metadata, control outputs, pruned (resolved names)
    metadata_cols = {_resolve_col(c, df_cols) or c for c in selection.get("metadata_cols", [])}
    control_cols = {_resolve_col(c, df_cols) or c for c in selection.get("control_cols", [])}
    pruned_pairs = selection.get("pruned_pairs", [])

    pruned_set: Set[Tuple[str, str]] = set()
    for pp in pruned_pairs:
        pair_str = pp.get("pair", "")
        # Parse "A <-> B" or "A -> B"
        parts = pair_str.replace("<->", "->").split("->")
        if len(parts) >= 2:
            a = _resolve_col(parts[0].strip().split(" ")[0], df_cols) or parts[0].strip().split(" ")[0]
            b = _resolve_col(parts[1].strip().split(" ")[0], df_cols) or parts[1].strip().split(" ")[0]
            pruned_set.add((a, b))
            pruned_set.add((b, a))

    filtered: Set[Tuple[str, str]] = set()
    # Stratification/grouping columns from ontology parameter groups (e.g. material,
    # grade, lot) must never serve as numeric predictors — they are grouping keys.
    strat_cols: Set[str] = set()
    for gk, cols in (ontology.get("parameter_groups", {}) or {}).items():
        if any(k in gk.lower() for k in ("strat", "group", "class", "segment")):
            strat_cols.update(cols or [])
    strat_cols = {_resolve_col(c, df_cols) or c for c in strat_cols}
    for pred, tgt in pairs:
        if pred == tgt:
            continue
        if pred in metadata_cols:
            continue
        if pred in control_cols:
            continue
        if pred in strat_cols:
            continue
        if (pred, tgt) in pruned_set:
            continue
        # Quality targets are response variables, not adjustable predictors —
        # exclude target-as-predictor pairs unless the ontology explicitly declares
        # the relationship (e.g. a composite index derived from its components).
        if targets and pred in targets:
            declared = any(
                (r.get("from") == pred or _strip_suffix(r.get("from", "")) == _strip_suffix(pred))
                and (r.get("to") == tgt or _strip_suffix(r.get("to", "")) == _strip_suffix(tgt))
                for r in ontology.get("relationships", [])
            )
            if not declared:
                continue
        filtered.add((pred, tgt))

    return sorted(filtered)


# ---------------------------------------------------------------------------
# Per-pair computation
# ---------------------------------------------------------------------------

def _detect_time_col(df: pd.DataFrame, ontology: dict, selection: dict) -> Optional[str]:
    """Detect the time column for a given scene, in priority order:
    1. ontology signals metadata_columns with role=timestamp
    2. selection.metadata_cols whose name carries time/date/ts semantics
    3. column-name heuristics (timestamp/time/datetime/date/ts_*)
    4. datetime64 dtype detection
    Returns None when no time column is found (scene is batch/cross-sectional).
    """
    for sig in ontology.get("signals", {}).get("metadata_columns", []):
        if sig.get("role") == "timestamp":
            col = sig.get("column")
            if col and col in df.columns:
                return col
    for col in selection.get("metadata_cols", []) or []:
        low = col.lower()
        if any(k in low for k in ("time", "date", "ts")) and col in df.columns:
            return col
    for col in df.columns:
        low = col.lower()
        if low in ("timestamp", "time", "datetime", "date") or low.startswith("ts_"):
            return col
    for col in df.columns:
        if str(df[col].dtype).startswith("datetime64"):
            return col
    return None


def _detect_group_col(df: pd.DataFrame, selection: dict, regime_filter: Optional[dict] = None) -> str:
    """Detect the grouping/stratification column for any scene, in priority order:
    1. selection.grouping_strategy.primary_group (CSTR-style contract)
    2. regime_filter.group_column (regime detector output contract)
    3. low-cardinality categorical columns (grade/lot/bed/shift style markers)
    Returns '' when no plausible grouping column exists (fully cross-sectional).
    """
    gs = selection.get("grouping_strategy", {}) or {}
    cand = gs.get("primary_group", "")
    if cand and cand in df.columns:
        return cand
    if regime_filter:
        cand = regime_filter.get("group_column", "")
        if cand and cand in df.columns:
            return cand
    for col in df.columns:
        if df[col].dtype.kind == "O":
            try:
                nun = df[col].nunique(dropna=True)
            except Exception:
                continue
            if 2 <= nun <= 8:
                low = col.lower()
                if any(k in low for k in ("grade", "lot", "bed", "product", "shift", "group", "batch", "unit", "material", "zone")):
                    return col
    # fallback: any low-cardinality categorical column
    for col in df.columns:
        if df[col].dtype.kind == "O":
            try:
                nun = df[col].nunique(dropna=True)
            except Exception:
                continue
            if 2 <= nun <= 8:
                return col
    return ""


def _collect_tier_predictors(selection: dict) -> List[str]:
    """Collect all predictor columns named across every analysis tier, in any
    supported tier shape (dict-of-columns or list-of-pair-objects)."""
    preds: List[str] = []
    for _tk, tier in (selection.get("analysis_tiers", {}) or {}).items():
        if isinstance(tier, dict):
            preds.extend(tier.get("columns", []) or [])
        elif isinstance(tier, list):
            for item in tier:
                if isinstance(item, dict) and item.get("predictor"):
                    preds.append(item["predictor"])
    # de-dup preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for p in preds:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _cached_cp_movement(df: pd.DataFrame, pred: str, tgt: str) -> dict:
    """Change-point co-movement with a per-column cache (CP positions are
    pair-independent, so caching avoids recomputing CUSUM per pair)."""
    try:
        from inference_engine import _cusum_change_points, CP_ALIGN_WINDOW_FRACTION

        n = len(df)

        def _cps(col: str) -> List[int]:
            if col not in _CP_CACHE:
                vals = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
                mask = _finite_mask(vals)
                idx = np.where(mask)[0]
                positions = [int(idx[p]) for p in _cusum_change_points(vals[mask])]
                _CP_CACHE[col] = positions
            return _CP_CACHE[col]

        cpa, cpb = _cps(pred), _cps(tgt)
        if not cpa or not cpb:
            return {"valid": True, "cp_a": cpa, "cp_b": cpb, "matched": 0,
                    "score": 0.0, "flagged": False,
                    "window_steps": max(3, int(n * CP_ALIGN_WINDOW_FRACTION))}
        window = max(3, int(n * CP_ALIGN_WINDOW_FRACTION))
        smaller, larger = (cpa, cpb) if len(cpa) <= len(cpb) else (cpb, cpa)
        matched, used = 0, []
        for p in smaller:
            for q in larger:
                if q in used:
                    continue
                if abs(p - q) <= window:
                    matched += 1
                    used.append(q)
                    break
        score = matched / min(len(cpa), len(cpb))
        single_shift = matched == 1 and score == 1.0 and len(cpa) == 1 and len(cpb) == 1
        return {"valid": True, "cp_a": cpa, "cp_b": cpb, "matched": matched,
                "score": round(float(score), 4),
                "flagged": bool((score >= 0.5 and matched >= 2) or single_shift),
                "window_steps": window}
    except Exception:
        return {"valid": False, "cp_a": [], "cp_b": [], "matched": 0,
                "score": 0.0, "flagged": False, "window_steps": 0}


def _compute_relationship(
    df: pd.DataFrame,
    pred: str,
    tgt: str,
    ontology: dict,
    selection: dict,
    conclusion: dict,
    regime_filter: Optional[dict],
    time_col: Optional[str] = None,
) -> dict:
    """Compute all relationship metrics for a single predictor→target pair."""
    if time_col is None:
        time_col = _detect_time_col(df, ontology, selection)
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
    p_floor_hit = False
    if n_finite >= MIN_PAIR_N:
        global_r = _pearson_r(x, y) or 0.0
        if abs(global_r) < 1.0 and n_finite > 2:
            t_stat = global_r * np.sqrt((n_finite - 2) / (1 - global_r ** 2))
            global_p, p_floor_hit = safe_p_value(float(t_stat))
        elif abs(global_r) >= 1.0:
            global_p, p_floor_hit = safe_p_value(float("inf"))
        all_p_values.append(global_p)

    # --- detrended ---
    detrended_r = global_r
    detrend_flag = False
    if time_col and time_col in df.columns and n_finite >= 10:
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
    primary_group = _detect_group_col(df, selection, regime_filter)
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

    # --- lag_aligned + temporal causality (fresh per pair) ---
    tla = conclusion.get("time_lag_analysis", {})
    key_findings = tla.get("key_findings", [])
    lag_r = steady_r
    lag_significant = False
    best_lag_steps = 0
    temporal = {"valid": False, "direction": "insufficient", "optimal_lag_steps": 0,
                "ccf_peak_r": 0.0, "p_value": 1.0, "p_floor_hit": False,
                "lag_aligned_r": 0.0, "n_used": 0}

    # Fresh lag-CCF precedence test on the actual time series
    if time_col and time_col in df.columns and n_finite >= MIN_PAIR_N:
        try:
            tvals = pd.to_datetime(df[time_col]).astype("int64").to_numpy(dtype=float)
        except Exception:
            tvals = df[time_col].to_numpy(dtype=float)
        temporal = temporal_causality(x_raw, y_raw, tvals)
        if temporal.get("valid") and temporal.get("direction") != "concurrent":
            best_lag_steps = int(temporal.get("optimal_lag_steps", 0))
            lag_r = float(temporal.get("lag_aligned_r", steady_r))
            lag_significant = bool(temporal.get("p_value", 1.0) <= Q_THRESHOLD)

    # Fallback to baseline key_findings when the fresh test found no precedence
    if not lag_significant:
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

    # --- partial correlation (controls from ALL tier shapes, not hardcoded keys) ---
    partial_r = 0.0
    partial_valid = False
    all_tier_preds = _collect_tier_predictors(selection)
    controls = [c for c in all_tier_preds if c != pred and c in df.columns]
    if controls and n_finite >= MIN_PAIR_N:
        try:
            result = partial_correlation(df.iloc[finite], pred, tgt, controls)
            partial_r = float(result.get("partial_r", 0.0))
            partial_valid = bool(result.get("valid", False))
        except Exception:
            pass

    # --- full-order conditional independence (direct vs indirect) ---
    # Conditioning set = primary numeric signals only. Object metadata coerce
    # to all-NaN, and derived aggregates (_dev rolling stats, regime_* one-hots)
    # are near-duplicates of the parent signal — conditioning on them would
    # trivially collapse every correlation and fake mediation channels.
    others = []
    for c in df.columns:
        if c in (pred, tgt):
            continue
        if c.lower() in ("timestamp", "time", "datetime", "date", "time_hours") or c.lower().startswith("ts_"):
            continue
        if c.endswith("_dev") or c.startswith("regime_"):
            continue
        try:
            nun = pd.to_numeric(df[c], errors="coerce").nunique(dropna=True)
        except Exception:
            continue
        if nun > 1:
            others.append(c)
    partial_full = conditional_independence(df, pred, tgt, others)
    partial_full_r = float(partial_full.get("partial_r", 0.0))
    partial_full_valid = bool(partial_full.get("valid", False))
    direct_association = bool(partial_full_valid and abs(partial_full_r) >= DIRECT_MIN_PARTIAL
                              and (partial_full_r > 0) == (global_r > 0))
    indirect_association = bool(partial_full_valid and abs(global_r) >= MIN_ABS_R
                                and abs(partial_full_r) < INDIRECT_MAX_PARTIAL)

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

    # --- change-point co-movement + leverage stability + moderator ---
    cp_movement = _cached_cp_movement(df, pred, tgt)
    loo = leverage_stability(x, y)
    primary_group = _detect_group_col(df, selection, regime_filter)
    interaction = moderator_check(df, pred, tgt, primary_group or None, per_group,
                                  partition_name=primary_group)

    # --- mediation scan (indirect channels) ---
    mediation = mediation_scan(df, pred, tgt, others,
                               global_r, partial_full_r, partial_full_valid)

    # --- causality ceiling + ontology contradiction ---
    onto_rels = ontology.get("relationships", [])
    onto_rel = None
    for rel in onto_rels:
        if rel.get("from") == pred and rel.get("to") == tgt:
            onto_rel = rel
            break
    ceiling = causality_ceiling(temporal, partial_full, onto_rel, global_r, n_finite)

    # --- validity_flags (all now actually computed) ---
    insufficient = bool(n_finite < MIN_PAIR_N or (abs(global_r) < 0.05 and n_finite < 30))
    validity_flags = {
        "simpson_paradox_checked": bool(primary_group and len(per_group) >= 2),
        "confounding_checked": bool(primary_group),
        "trend_confounding_checked": detrend_flag,
        "change_point_tested": bool(cp_movement.get("valid", False)),
        "batch_effect_tested": bool(primary_group and len(per_group) >= 2),
        "lag_significant": lag_significant,
        "outlier_influence_checked": bool(loo.get("valid", False)),
        "insufficient_data": insufficient,
    }

    return {
        "predictor": pred,
        "target": tgt,
        "global": round(global_r, 6),
        "p_value": float(global_p),
        "p_floor_hit": p_floor_hit,
        "detrended": round(detrended_r, 6),
        "per_group": per_group,
        "steady": round(steady_r, 6),
        "lag_aligned": round(lag_r, 6),
        "per_regime": per_regime,
        "slope_at_current": round(slope_cur, 6),
        "slope_valid": slope_valid,
        "partial": round(partial_r, 6),
        "partial_valid": partial_valid,
        "partial_full": partial_full,
        "direct_association": direct_association,
        "indirect_association": indirect_association,
        "mediator_candidates": mediation.get("candidates", []),
        "temporal": temporal,
        "temporal_direction": temporal.get("direction", "insufficient"),
        "optimal_lag_steps": int(temporal.get("optimal_lag_steps", 0) or best_lag_steps or 0),
        "change_point_co_movement": cp_movement,
        "loo_stability": loo,
        "interaction": interaction,
        "causality_ceiling": ceiling.get("ceiling", "insufficient_evidence"),
        "ontology_contradiction": bool(ceiling.get("ontology_contradiction", False)),
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
        primary_p_values.append(rel["p_value"])

    # BH correction across all pairs (on the safe erfc p-values)
    if primary_p_values:
        q_values = benjamini_hochberg(primary_p_values)
        for i, qv in enumerate(q_values):
            qv = float(qv)
            # Rounding to 6 decimals would collapse floored p-values (1e-300) to
            # exact 0.0 — keep tiny q values un-rounded so they stay truthful.
            relationships[i]["q_value"] = round(qv, 6) if qv >= 1e-8 else qv

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
    candidate_pairs = _build_candidate_pairs(
        ontology, selection, df_columns=list(df.columns), derived_features=feature_metadata
    )
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

    # ---- E3.5: association graph (full pairwise network + inference evidence) ----
    graph_output = run_dir / "enhancement" / "association_graph.json"
    try:
        meta = set(selection.get("metadata_cols", []) or [])
        exclude = {c for c in df.columns if c.lower() in
                   ("timestamp", "time", "datetime", "date", "time_hours") or c.lower().startswith("ts_")}
        exclude |= meta
        exclude |= {c for c in df.columns if c.endswith("_dev") or c.startswith("regime_")}
        numeric_cols = [c for c in df.columns
                        if c not in exclude
                        and pd.to_numeric(df[c], errors="coerce").nunique(dropna=True) > 1]
        pairwise = pairwise_scan(df, numeric_cols)
        graph = build_association_graph(df, numeric_cols, ontology, selection,
                                        relationships, pairwise)
        with open(graph_output, "w", encoding="utf-8") as fh:
            json.dump(graph, fh, indent=2, ensure_ascii=False, default=str)
        print(f"[association_graph] {len(graph['nodes'])} nodes, {len(graph['edges'])} edges → {graph_output}")
    except Exception as exc:  # pragma: no cover — graph must never break E3
        print(f"[association_graph] WARNING: graph build failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()