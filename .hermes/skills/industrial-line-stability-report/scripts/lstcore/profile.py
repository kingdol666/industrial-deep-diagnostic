"""Period coverage / completeness profile."""
from __future__ import annotations

import numpy as np
import pandas as pd


def profile_period(df: pd.DataFrame, roles: dict, n_rows_raw: int) -> dict:
    """Compute data-summary facts used by the report hero + evidence appendix."""
    time_col = roles["time_col"]
    dt = df["_dt"]
    n_used = int(len(df))
    numeric_cols = roles["parameter_cols"]
    span_seconds = None
    interval_seconds = None
    if len(df) >= 2:
        is_dt = pd.api.types.is_datetime64_any_dtype(dt.dtype)
        deltas = (np.diff(dt.values.astype("datetime64[ns]").astype(np.int64)) / 1e9
                  if is_dt else np.diff(pd.to_numeric(dt).values))
        deltas = deltas[deltas > 0]
        if len(deltas):
            interval_seconds = float(np.median(deltas))
            span_seconds = (float((dt.iloc[-1] - dt.iloc[0]).total_seconds()) if is_dt
                            else float(pd.to_numeric(dt).iloc[-1] - pd.to_numeric(dt).iloc[0]))
    missing_cells = int(df[numeric_cols].isna().sum().sum()) if numeric_cols else 0
    total_cells = n_used * len(numeric_cols) if numeric_cols else 0
    missing_rate = (missing_cells / total_cells) if total_cells else 0.0
    # degenerate channels: a column with a single unique value over the whole
    # period carries no stability information (frozen snapshot export / dead
    # sensor / never-commissioned point). Scoring it as "perfectly stable"
    # would fabricate a perfect grade, so the analyzer excludes and reports it.
    invariant_cols = []
    for c in numeric_cols:
        v = pd.to_numeric(df[c], errors="coerce").dropna()
        if v.nunique() < 2:
            invariant_cols.append(c)
    time_invariant = {
        "count": len(invariant_cols),
        "total": len(numeric_cols),
        "share": round(len(invariant_cols) / len(numeric_cols), 6) if numeric_cols else 0.0,
        "examples": invariant_cols[:10],
    }
    # coverage: rows actually present vs rows implied by the median sampling interval
    coverage_ratio = 1.0
    if interval_seconds and interval_seconds > 0 and np.issubdtype(dt.dtype, np.datetime64):
        implied = span_seconds / interval_seconds + 1
        coverage_ratio = float(min(1.0, n_used / implied)) if implied else 1.0
    return {
        "n_rows_raw": int(n_rows_raw),
        "n_rows_used": n_used,
        "time_span_seconds": span_seconds,
        "sampling_interval_median_seconds": interval_seconds,
        "missing_rate": round(missing_rate, 6),
        "coverage_ratio": round(coverage_ratio, 6),
        "time_invariant_channels": time_invariant,
    }
