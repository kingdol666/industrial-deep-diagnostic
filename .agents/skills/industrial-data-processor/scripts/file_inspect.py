#!/usr/bin/env python3
"""
file_inspect.py — Data file inspection for Excel, Parquet, Feather formats
=====================================================================
Zero-dep for CSV. Requires pandas + openpyxl (Excel) or pyarrow (Parquet/Feather).

Usage: file_inspect.py <file> [--rows N] (invoke via uv venv Python)
Output: JSON with column details, types, stats, time column detection, preview

Used by inspect.mjs as a fallback for binary/proprietary formats that
Node.js cannot natively parse.
"""

import json, sys, os, warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print(json.dumps({
        "error": "Missing pandas/numpy. Install: node scripts/uv_env_setup.mjs  # was: pip3 install pandas numpy openpyxl pyarrow",
        "file": sys.argv[1] if len(sys.argv) > 1 else None
    }, indent=2))
    sys.exit(1)


def load_file(file_path):
    """Load CSV/Excel/Parquet/Feather/JSON into a DataFrame."""
    suffix = Path(file_path).suffix.lower()
    if suffix in ('.xlsx', '.xls'):
        return pd.read_excel(file_path)
    elif suffix == '.parquet':
        return pd.read_parquet(file_path)
    elif suffix in ('.feather', '.ipc', '.arrow'):
        return pd.read_feather(file_path)
    elif suffix == '.json':
        return pd.read_json(file_path)
    elif suffix == '.tsv':
        return pd.read_csv(file_path, sep='\t')
    else:
        return pd.read_csv(file_path)


def infer_dtype(series):
    """Infer column data type from pandas Series."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'datetime'
    if pd.api.types.is_numeric_dtype(series):
        return 'number'
    if pd.api.types.is_bool_dtype(series):
        return 'boolean'
    # Try to detect datetime strings
    if series.dropna().nunique() > 0:
        try:
            converted = pd.to_datetime(series.dropna(), errors='coerce')
            if converted.notna().sum() / max(len(series.dropna()), 1) > 0.9:
                return 'datetime'
        except Exception:
            pass
    return 'string'


def numeric_stats(series):
    """Compute descriptive statistics for a numeric column."""
    clean = series.dropna()
    if len(clean) == 0:
        return None
    desc = clean.describe(percentiles=[0.25, 0.5, 0.75])
    return {
        "count": int(desc["count"]),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "mean": round(float(desc["mean"]), 4),
        "std": round(float(desc["std"]), 4),
        "min": float(desc["min"]),
        "max": float(desc["max"]),
        "p25": float(desc["25%"]),
        "p50": float(desc["50%"]),
        "p75": float(desc["75%"]),
    }


def string_stats(series):
    """Compute descriptive statistics for a string/categorical column."""
    missing = int(series.isna().sum())
    valid = series.dropna()
    value_counts = valid.value_counts()
    return {
        "count": len(valid),
        "missing": missing,
        "missing_pct": round(missing / max(len(series), 1) * 100, 2),
        "unique": int(valid.nunique()),
        "top_values": [[str(k), int(v)] for k, v in value_counts.head(5).items()],
    }


def detect_time_column(df):
    """Heuristically detect the time column by name and dtype."""
    keywords = ['time', 'timestamp', 'datetime', 'date', 'zeit', 'ts']
    for col in df.columns:
        lower = str(col).lower().strip()
        if any(kw in lower for kw in keywords):
            return col
    # Fallback: first datetime column
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not file_path:
        print(json.dumps({"error": "Usage: file_inspect.py <file> [--rows N] (invoke via uv venv Python)"}, indent=2))
        sys.exit(1)

    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found: {file_path}"}, indent=2))
        sys.exit(1)

    preview_rows = 5
    for i, arg in enumerate(sys.argv):
        if arg == '--rows' and i + 1 < len(sys.argv):
            preview_rows = int(sys.argv[i + 1])

    suffix = Path(file_path).suffix.lower()
    unsupported = {'.feather', '.ipc', '.arrow'}
    if suffix in unsupported:
        try:
            import pyarrow
        except ImportError:
            print(json.dumps({
                "error": "pyarrow required for Feather/Arrow format. Install: node scripts/uv_env_setup.mjs  # was: pip3 install pyarrow",
                "file": file_path
            }, indent=2))
            sys.exit(1)

    if suffix in ('.xlsx', '.xls'):
        try:
            import openpyxl
        except ImportError:
            print(json.dumps({
                "error": "openpyxl required for Excel format. Install: node scripts/uv_env_setup.mjs  # was: pip3 install openpyxl",
                "file": file_path
            }, indent=2))
            sys.exit(1)

    df = load_file(file_path)

    if len(df) == 0:
        print(json.dumps({"error": "File has no data rows", "file": file_path}, indent=2))
        sys.exit(1)

    # Sampling for very large files: compute stats on a 50K sample, note full row count
    full_rows = len(df)
    sampled = False
    if full_rows > 50000:
        df_stats = df.sample(n=50000, random_state=42)
        sampled = True
    else:
        df_stats = df

    time_col = detect_time_column(df)

    column_details = []
    for ci, col_name in enumerate(df.columns):
        series = df_stats[col_name]
        dtype = infer_dtype(series)

        if dtype == 'number':
            stats = numeric_stats(series)
        else:
            stats = string_stats(series.astype(str) if dtype != 'number' else series)

        column_details.append({
            "name": str(col_name),
            "index": ci,
            "type": dtype,
            "stats": stats,
        })

    # Preview from the original (unsampled) DataFrame
    preview = df.head(preview_rows).to_dict(orient='records')
    # Convert non-serializable types
    for row in preview:
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                row[k] = int(v)
            elif isinstance(v, (np.floating,)):
                row[k] = float(v)
            elif isinstance(v, (np.bool_,)):
                row[k] = bool(v)
            elif pd.isna(v):
                row[k] = None
            elif isinstance(v, (datetime, pd.Timestamp)):
                row[k] = str(v)

    result = {
        "file": os.path.abspath(file_path),
        "format": suffix.replace('.', ''),
        "rows": full_rows,
        "columns": len(df.columns),
        "time_column": time_col,
        "column_details": column_details,
        "preview": preview[:preview_rows],
    }

    if sampled:
        result["_note"] = f"Stats computed on 50K random sample of {full_rows} total rows"

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
