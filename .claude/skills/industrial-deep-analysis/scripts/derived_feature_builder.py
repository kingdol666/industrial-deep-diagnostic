#!/usr/bin/env python3
"""E2: Derived-feature builder for industrial deep-analysis.

Computes physically justified derived features from cleaned data.
Only emits ``computed`` records when source columns and ontology
conditions exist; otherwise ``not_applicable``.

CLI::

    python derived_feature_builder.py --run-dir PATH [--output PATH]

Default output: ``RUN_DIR/enhancement/derived_features.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_df(run_dir: Path) -> pd.DataFrame:
    csv = run_dir / "02_processed" / "cleaned_data.csv"
    if csv.is_file():
        return pd.read_csv(csv)
    json_path = run_dir / "02_processed" / "cleaned_data.json"
    if json_path.is_file():
        return pd.read_json(json_path)
    raise FileNotFoundError("No cleaned_data.csv or .json found")


# ---------------------------------------------------------------------------
# Feature records helper
# ---------------------------------------------------------------------------

def _not_applicable(name: str, formula: str, physics_basis: str,
                    unit: str = "N/A",
                    source_columns: Optional[List[str]] = None) -> dict:
    return {
        "name": name,
        "status": "not_applicable",
        "formula": formula,
        "physics_basis": physics_basis,
        "unit": unit,
        "source_columns": source_columns or [],
        "row_range": "N/A",
        "mask": "N/A",
        "derived": False,
    }


def _computed(name: str, formula: str, physics_basis: str, unit: str,
              source_columns: List[str],
              row_range: str, mask: str) -> dict:
    return {
        "name": name,
        "status": "computed",
        "formula": formula,
        "physics_basis": physics_basis,
        "unit": unit,
        "source_columns": source_columns,
        "row_range": row_range,
        "mask": mask,
        "derived": True,
    }


# ---------------------------------------------------------------------------
# Feature builders
# ---------------------------------------------------------------------------

def _build_cumulative_exposure(df: pd.DataFrame, col: str, unit: str,
                               time_col: str = "timestamp") -> dict:
    """Cumulative poisoning exposure via trapezoidal integration over sorted time."""
    if col not in df.columns:
        return _not_applicable(
            f"cumulative_{col}_exposure",
            f"∫ {col} dt (trapezoidal sum over sorted {time_col})",
            "Cumulative poison exposure: active site occupation θ_p ∝ ∫C·dt (Langmuir adsorption)",
            unit=f"{unit}*hour",
            source_columns=[col, time_col],
        )

    df_sorted = df.sort_values(time_col).copy()
    try:
        times = pd.to_numeric(pd.to_datetime(df_sorted[time_col]) - pd.to_datetime(df_sorted[time_col].iloc[0]))
        times_h = times.dt.total_seconds().values / 3600.0
    except Exception:
        times_h = np.arange(len(df_sorted), dtype=float)

    vals = pd.to_numeric(df_sorted[col], errors="coerce").values.astype(float)
    finite = np.isfinite(vals) & np.isfinite(times_h)

    if not np.any(finite):
        return _not_applicable(
            f"cumulative_{col}_exposure",
            f"∫ {col} dt",
            "Cumulative poison exposure",
            unit=f"{unit}*hour",
            source_columns=[col, time_col],
        )

    cum = np.zeros(len(vals))
    cum[finite] = np.cumsum(
        vals[finite] * np.gradient(times_h[finite])
    )  # simple trapezoid approximation

    # Store as new column in df
    col_name = f"cumulative_{col}_exposure"
    df_sorted[col_name] = cum
    return _computed(
        f"cumulative_{col}_exposure",
        f"cumulative_sum({col} * Δt) over sorted {time_col}",
        "Cumulative poison exposure: integral of concentration over time drives active-site occupation",
        unit=f"{unit}*hour",
        source_columns=[col, time_col],
        row_range=f"rows 0-{len(df_sorted) - 1}",
        mask=f"{col} IS FINITE AND {time_col} IS FINITE",
    )


def _build_time_since_event(df: pd.DataFrame,
                            event_col: str,
                            time_col: str = "timestamp") -> dict:
    """Time since a group/event transition."""
    name = f"time_since_{event_col}_transition"
    if event_col not in df.columns or time_col not in df.columns:
        return _not_applicable(
            name,
            f"time since {event_col} transition",
            "Time since catalyst regeneration or bed switch event",
            unit="hours",
            source_columns=[event_col, time_col],
        )

    try:
        times = pd.to_datetime(df[time_col])
    except Exception:
        return _not_applicable(
            name,
            f"time since {event_col} transition",
            "Requires parsable timestamp",
            unit="hours",
            source_columns=[event_col, time_col],
        )

    # Find transition points
    groups = df[event_col].values
    transitions = np.where(groups[:-1] != groups[1:])[0] + 1

    if len(transitions) == 0:
        # No transition — time since start
        base = times.iloc[0]
        hours = (times - base).dt.total_seconds().values / 3600.0
    else:
        hours = np.zeros(len(df))
        start = 0
        for t_idx in list(transitions) + [len(df)]:
            base = times.iloc[start]
            seg = (times.iloc[start:t_idx] - base).dt.total_seconds().values / 3600.0
            hours[start:t_idx] = seg
            start = t_idx

    df[name] = hours
    return _computed(
        name,
        f"time since {event_col} group transition (hours)",
        f"Time since catalyst bed / regeneration event; captures deactivation drift within each bed regime",
        unit="hours",
        source_columns=[event_col, time_col],
        row_range=f"rows 0-{len(df) - 1}",
        mask=f"{time_col} IS FINITE",
    )


def _build_regime_indicators(df: pd.DataFrame,
                             regime_filter: Optional[dict]) -> List[dict]:
    """One-hot regime state indicators from production_regime_filter."""
    features: List[dict] = []
    if regime_filter is None:
        return features

    labels = regime_filter.get("per_row_labels", [])
    if not labels or len(labels) != len(df):
        return features

    # Determine unique regimes
    unique_regimes = sorted(set(str(lbl) for lbl in labels))
    for regime in unique_regimes:
        safe_name = regime.lower().replace(" ", "_").replace("-", "_")
        name = f"regime_{safe_name}"
        mask_arr = np.array([str(lbl) == regime for lbl in labels])
        df[name] = mask_arr.astype(int)
        features.append(_computed(
            name,
            f"indicator({regime}) from production_regime_filter",
            f"Process regime indicator for {regime} operating state",
            unit="binary",
            source_columns=["production_regime_filter.per_row_labels"],
            row_range=f"rows 0-{len(df) - 1}",
            mask="per_row_labels IS DEFINED",
        ))
    return features


def _build_lag_aligned_feature(df: pd.DataFrame,
                               predictor: str,
                               target: str,
                               lag_steps: int,
                               time_col: str = "timestamp") -> dict:
    """Create a lag-aligned predictor column."""
    name = f"{predictor}_lag{lag_steps}"
    if predictor not in df.columns:
        return _not_applicable(
            name,
            f"{predictor} shifted by {lag_steps} steps",
            f"Lag-aligned {predictor} for {target} at optimal lag {lag_steps}",
            unit="same as source",
            source_columns=[predictor, time_col],
        )

    if time_col in df.columns:
        df_sorted = df.sort_values(time_col).copy()
    else:
        df_sorted = df.copy()

    shifted = df_sorted[predictor].shift(lag_steps)
    df[name] = shifted.values if hasattr(shifted, 'values') else shifted

    return _computed(
        name,
        f"{predictor} lagged by {lag_steps} time steps",
        f"Lag-aligned feature: {predictor} → {target} at optimal lag {lag_steps}h from time_lag_analysis",
        unit="same_as_source",
        source_columns=[predictor, time_col],
        row_range=f"rows 0-{len(df_sorted) - 1}",
        mask=f"{predictor} IS FINITE AND lag {lag_steps} rows available",
    )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_derived_features(run_dir: Path) -> List[dict]:
    """Build derived feature records for the run directory.

    Returns the list for ``features`` in ``derived_features.json``.
    """
    df = _load_df(run_dir)
    ontology = _load_json(run_dir / "01_ontology" / "ontology.json")
    selection = _load_json(run_dir / "02_processed" / "analysis_parameter_selection.json")
    conclusion = _load_json(run_dir / "02_processed" / "data_analysis_conclusion.json")

    regime_path = run_dir / "02_processed" / "production_regime_filter.json"
    regime_filter = _load_json(regime_path) if regime_path.is_file() else None

    onto_units = ontology.get("metadata", {}).get("units", {})
    time_col = "timestamp"
    features: List[dict] = []

    # 1. Cumulative poisoning exposure (feed_sulfur_ppm)
    poison_col = "feed_sulfur_ppm"
    poison_unit = onto_units.get(poison_col, "ppm")
    features.append(_build_cumulative_exposure(df, poison_col, poison_unit, time_col))

    # 2. Time since catalyst_bed_id transition
    event_col = selection.get("grouping_strategy", {}).get("primary_group", "catalyst_bed_id")
    features.append(_build_time_since_event(df, event_col, time_col))

    # 3. Regime indicators
    features.extend(_build_regime_indicators(df, regime_filter))

    # 4. Lag-aligned feature from time_lag_analysis key_findings
    tla = conclusion.get("time_lag_analysis", {})
    key_findings = tla.get("key_findings", [])
    lag_added = False
    for kf in key_findings:
        lag_steps = kf.get("optimal_lag_steps", 0)
        if lag_steps is not None and abs(lag_steps) > 0:
            predictor = kf.get("predictor", "")
            target = kf.get("target", "")
            if predictor and target:
                features.append(_build_lag_aligned_feature(df, predictor, target, lag_steps, time_col))
                lag_added = True
                break
    if not lag_added:
        features.append(_not_applicable(
            "lag_aligned_feature",
            "predictor shifted by optimal_lag_steps",
            "Lag alignment from time_lag_analysis; no nonzero lag found or source/target unavailable",
            unit="same_as_source",
        ))

    # Write back columns to df for downstream use? No — downstream reads CSV fresh.
    return features


def main() -> None:
    ap = argparse.ArgumentParser(description="E2: Build derived features JSON")
    ap.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output) if args.output else run_dir / "enhancement" / "derived_features.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    features = build_derived_features(run_dir)
    result = {
        "run_id": "enhancement-derived",
        "features": features,
    }

    with open(output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)

    n_computed = sum(1 for f in features if f.get("status") == "computed")
    n_na = sum(1 for f in features if f.get("status") == "not_applicable")
    print(f"[derived_feature_builder] {n_computed} computed, {n_na} not_applicable → {output}")


if __name__ == "__main__":
    main()