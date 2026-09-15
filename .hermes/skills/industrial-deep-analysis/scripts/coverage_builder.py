#!/usr/bin/env python3
"""E1: Analysis coverage builder for industrial deep-analysis.

Reads ontology, selection, regime filter, data analysis conclusion, and
cleaned data; emits ``analysis_coverage.json`` with one ``columns[]``
entry per cleaned-data column.

CLI::

    python coverage_builder.py --run-dir PATH [--output PATH]

Default output: ``RUN_DIR/enhancement/analysis_coverage.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Reuse Task-2 utilities.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from stat_utils import support_domain as _support_domain  # noqa: E402

# ---------------------------------------------------------------------------
# Finite-value sentinel helpers
# ---------------------------------------------------------------------------

_NONNUMERIC_SENTINEL = {
    "p5": 0.0,
    "p25": 0.0,
    "p50": 0.0,
    "p75": 0.0,
    "p95": 0.0,
    "n": 1,
    "current_median": 0.0,
}


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _has_timestamp(path: Path) -> bool:
    """Check if a CSV file has a 'timestamp' column without leaking file handles."""
    try:
        with open(path, encoding="utf-8") as fh:
            return "timestamp" in fh.readline()
    except Exception:
        return False


def _load_data(run_dir: Path) -> pd.DataFrame:
    """Load numeric data for coverage: prefer E2-derived data (includes derived
    feature columns) so the coverage matrix truly covers every analyzable column.
    Falls back to cleaned data, CSV first then JSON."""
    derived_csv = run_dir / "enhancement" / "derived_data.csv"
    if derived_csv.is_file():
        return pd.read_csv(derived_csv, parse_dates=["timestamp"] if _has_timestamp(derived_csv) else False)
    csv = run_dir / "02_processed" / "cleaned_data.csv"
    if csv.is_file():
        return pd.read_csv(csv, parse_dates=["timestamp"] if _has_timestamp(csv) else False)
    json_path = run_dir / "02_processed" / "cleaned_data.json"
    if json_path.is_file():
        return pd.read_json(json_path)
    raise FileNotFoundError(
        "Neither derived_data.csv, cleaned_data.csv nor cleaned_data.json found"
    )


def _coerce_n(n_val: Any) -> float:
    """Return finite numeric value from any n-like input."""
    try:
        v = float(n_val)
        return v if np.isfinite(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Ontology signal index
# ---------------------------------------------------------------------------

def _build_signal_index(ontology: dict) -> Dict[str, dict]:
    """Map every ontology signal column -> signal record."""
    idx: Dict[str, dict] = {}
    for section in ["inspection_signals", "process_parameters", "control_variables"]:
        for sig in ontology.get("signals", {}).get(section, []):
            col = sig.get("column")
            if col:
                idx[col] = sig
    for sig in ontology.get("signals", {}).get("metadata_columns", []):
        col = sig.get("column")
        if col:
            idx[col] = sig
    # events column (e.g. catalyst_bed_id)
    for evt in ontology.get("signals", {}).get("events", []):
        col = evt.get("column")
        if col:
            idx[col] = evt
    return idx


def _role_from_ontology(col: str, signal_idx: Dict[str, dict], selection: dict) -> str:
    """Return a role string from ontology or selection fallback."""
    if col in signal_idx:
        r = signal_idx[col].get("role", "")
        if r:
            return r
    # _dev columns: strip suffix and look up parent
    if col.endswith("_dev"):
        parent = col[:-4]
        parent_role = _role_from_ontology(parent, signal_idx, selection)
        if parent_role != "unknown":
            return "derived_deviation"
        return "derived_deviation"
    if col == "time_hours":
        return "derived_time"
    # Fallback to selection
    if col in selection.get("quality_targets", []):
        return "target"
    if col in selection.get("predictor_cols", []):
        return "predictor"
    if col in selection.get("confounder_cols", []):
        return "confounder"
    if col in selection.get("control_cols", []):
        return "control"
    if col in selection.get("group_cols", []):
        return "group"
    if col in selection.get("metadata_cols", []):
        return "metadata"
    return "unknown"


def _coverage_status(
    col: str,
    role: str,
    selection: dict,
    is_numeric: bool,
    has_data: bool,
) -> str:
    """Determine coverage_status enum value."""
    if col.endswith("_dev"):
        return "derived_and_used"
    if col == "time_hours":
        return "not_applicable"
    if col in selection.get("metadata_cols", []) or role == "timestamp":
        return "not_applicable"
    if not has_data and col in selection.get("exclude_cols", []):
        return "not_applicable"

    if not is_numeric:
        # Non-numeric columns like product_lot, shift, catalyst_bed_id
        if role in ("group", "product_code", "operator"):
            return "not_applicable"
        return "not_applicable"

    if not has_data:
        return "insufficient_data"

    # Determine tier (scan ALL tier shapes — dict-of-columns and pair-object
    # lists; hardcoded tier keys silently empty for pair-object selections)
    tiers = selection.get("analysis_tiers", {})
    tier1_cols: List[str] = []
    tier2_cols: List[str] = []
    tier3_cols: List[str] = []
    tier4_cols: List[str] = []
    target_cols: List[str] = []
    for tier_key, tier in (tiers or {}).items():
        if isinstance(tier, dict):
            cols = tier.get("columns", []) or []
            tk_low = tier_key.lower()
            if "confound" in tk_low or "caution" in tk_low:
                tier3_cols.extend(cols)
            elif "control" in tk_low or "output" in tk_low or "endogen" in tk_low:
                tier4_cols.extend(cols)
            elif "target" in tk_low:
                target_cols.extend(cols)
            elif "tier1" in tk_low or "tier_1" in tk_low or "primary" in tk_low:
                tier1_cols.extend(cols)
            else:
                tier2_cols.extend(cols)
        elif isinstance(tier, list):
            for item in tier:
                if not isinstance(item, dict):
                    continue
                tk_low = tier_key.lower()
                pred = item.get("predictor", "")
                tgt = item.get("target", "")
                if "confound" in tk_low or "caution" in tk_low:
                    tier3_cols.extend([pred, tgt])
                elif "control" in tk_low or "output" in tk_low or "endogen" in tk_low:
                    tier4_cols.extend([pred, tgt])
                elif "target" in tk_low:
                    target_cols.extend([pred, tgt])
                elif "tier1" in tk_low or "tier_1" in tk_low or "primary" in tk_low:
                    tier1_cols.extend([pred, tgt])
                else:
                    tier2_cols.extend([pred, tgt])
    tier1_cols = list(dict.fromkeys(tier1_cols))
    tier2_cols = list(dict.fromkeys(tier2_cols))
    tier3_cols = list(dict.fromkeys(tier3_cols))
    tier4_cols = list(dict.fromkeys(tier4_cols))
    target_cols = list(dict.fromkeys(target_cols))
    pruned_cols = set()
    for pp in selection.get("pruned_pairs", []):
        for part in pp.get("pair", "").replace("<->", "->").split("->"):
            pruned_cols.add(part.strip().split(" ")[0])

    if col in target_cols:
        return "covered_primary"
    if col in tier1_cols or col in tier2_cols:
        return "covered_primary"
    if col in tier3_cols:
        return "covered_conditional"
    if col in tier4_cols:
        return "pruned_physics"

    # Check confounders - if only used for stratification
    confounders = selection.get("confounder_cols", [])
    if col in confounders:
        if col in tier3_cols:
            return "covered_conditional"
        return "covered_conditional"  # default confounders are conditional

    if col in pruned_cols:
        return "pruned_confounded"

    return "covered_primary"  # default for unrecognized numerics


def _physics_ref(col: str, signal_idx: Dict[str, dict]) -> str:
    """Extract physics reference from ontology signal."""
    sig = signal_idx.get(col, {})
    gl = sig.get("governing_law", "")
    pm = sig.get("physical_meaning", "")
    if gl:
        return gl.split("。")[0][:200]
    if pm:
        return pm.split("。")[0][:200]
    return "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def _load_optional(path: Path) -> dict:
    """Load an optional pipeline artifact; missing → {} (graceful fallback)."""
    try:
        return _load_json(path)
    except FileNotFoundError:
        return {}


def build_coverage(run_dir: Path) -> List[dict]:
    """Build analysis coverage records for every cleaned-data column.

    Returns the list suitable for ``columns`` in the output JSON.
    """
    ontology = _load_json(run_dir / "01_ontology" / "ontology.json")
    feature_summary = _load_json(run_dir / "02_processed" / "feature_summary.json")
    selection = _load_optional(run_dir / "02_processed" / "analysis_parameter_selection.json")
    conclusion = _load_optional(run_dir / "02_processed" / "data_analysis_conclusion.json")

    # Regime filter (optional)
    regime_path = run_dir / "02_processed" / "production_regime_filter.json"
    regime_filter: Optional[dict] = None
    if regime_path.is_file():
        regime_filter = _load_json(regime_path)

    df = _load_data(run_dir)
    signal_idx = _build_signal_index(ontology)

    # Determine numeric columns
    numeric_cols = set(feature_summary.get("numeric_columns", []))
    # Build column list from CSV
    all_cols = list(df.columns)
    exclude_cols = set(selection.get("exclude_cols", []))
    metadata_cols = set(selection.get("metadata_cols", []))
    group_cols = set(selection.get("group_cols", []))

    # Steady indices
    steady_indices: Optional[List[int]] = None
    if regime_filter:
        steady_indices = regime_filter.get("steady_row_indices", None)

    # Ontology metadata units
    onto_units = ontology.get("metadata", {}).get("units", {})

    columns_out: List[dict] = []
    for col in all_cols:
        is_numeric = col in numeric_cols
        role = _role_from_ontology(col, signal_idx, selection)


        # Coerce n_total and n_steady
        series = df[col] if col in df.columns else None
        has_data = series is not None and len(series) > 0
        n_total = int(len(series)) if has_data else 0
        n_steady = 0
        if has_data and steady_indices is not None and is_numeric:
            valid_steady = [i for i in steady_indices if i < len(series)]
            n_steady = len(valid_steady)
        elif has_data:
            n_steady = n_total

        status = _coverage_status(col, role, selection, is_numeric, has_data)

        # Unit resolution
        unit = onto_units.get(col, "")
        if not unit:
            sig = signal_idx.get(col, {})
            unit = sig.get("unit", "")
        if not unit and is_numeric:
            unit = "dimensionless"
        elif not unit:
            unit = "metadata"

        # Support domain
        if is_numeric and has_data:
            try:
                sd = _support_domain(series)
                support_domain_entry = {
                    "p5": float(sd["p5"]),
                    "p25": float(sd["p25"]),
                    "p50": float(sd["p50"]),
                    "p75": float(sd["p75"]),
                    "p95": float(sd["p95"]),
                    "n": int(sd["n"]),
                    "current_median": float(sd["current_median"]),
                }
            except Exception:
                support_domain_entry = {**_NONNUMERIC_SENTINEL}
        else:
            support_domain_entry = {**_NONNUMERIC_SENTINEL}

        physics_ref = _physics_ref(col, signal_idx)

        # Build reason
        reason_parts = []
        if status == "derived_and_used":
            parent = col[:-4]
            reason_parts.append(f"Derived deviation column '{col}' (parent '{parent}'); used in pipeline computations but not a raw process signal.")
        elif status == "not_applicable":
            if col == "time_hours":
                reason_parts.append(f"Derived time index column '{col}'; not a quantitative process signal.")
            elif col in metadata_cols or role in ("timestamp", "group", "product_code", "operator", "derived_time"):
                reason_parts.append(f"Column '{col}' is metadata/group/derived (role={role}), not a quantitative process signal.")
            else:
                reason_parts.append(f"Column '{col}' excluded from quantitative analysis.")
        elif status == "pruned_physics":
            reason_parts.append(f"Column '{col}' is a control output or physically pruned; not independent causal driver.")
            sig = signal_idx.get(col, {})
            if sig.get("role") == "control":
                reason_parts.append("It is a control output amount (effect, not cause).")
            if sig.get("discrepancy_signal"):
                reason_parts.append(sig["discrepancy_signal"][:150])
        elif status == "pruned_confounded":
            reason_parts.append(f"Column '{col}' is explicit confounded-only; excluded from primary causal analysis.")
        elif status == "covered_conditional":
            if col in selection.get("confounder_cols", []):
                reason_parts.append(f"Confounder '{col}': used for stratification/control, not primary identification.")
            else:
                reason_parts.append(f"Column '{col}' has conditional coverage due to data limitations or confounding.")
        elif status == "covered_primary":
            if role == "target":
                reason_parts.append(f"Quality target '{col}' with full coverage for diagnostic analysis.")
            else:
                reason_parts.append(f"Primary predictor/kinetic driver '{col}' with full coverage.")
        elif status == "insufficient_data":
            reason_parts.append(f"Column '{col}' has insufficient or unusable data.")
        # If non-numeric with support domain filled with sentinels, add reason
        if not is_numeric:
            reason_parts.append(f"Non-numeric metadata column; support domain uses finite sentinel values (0.0) — not a quantitative domain.")

        reason = " ".join(reason_parts) if reason_parts else f"Column '{col}' assessed."

        columns_out.append({
            "column": col,
            "role": role,
            "coverage_status": status,
            "unit": unit,
            "n_total": n_total,
            "n_steady": n_steady,
            "support_domain": support_domain_entry,
            "physics_ref": physics_ref,
            "reason": reason,
        })

    return columns_out


def main() -> None:
    ap = argparse.ArgumentParser(description="E1: Build analysis coverage JSON")
    ap.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    ap.add_argument("--output", default=None, help="Output JSON path (default: RUN_DIR/enhancement/analysis_coverage.json)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output) if args.output else run_dir / "enhancement" / "analysis_coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    columns = build_coverage(run_dir)
    result = {
        "run_id": "enhancement-coverage",
        "columns": columns,
    }

    with open(output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)

    print(f"[coverage_builder] Wrote {len(columns)} column entries → {output}")


if __name__ == "__main__":
    main()