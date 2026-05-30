#!/usr/bin/env python3
"""
Chemistry Experiment Data Cleaner
==================================
Cleans and standardizes chemistry lab data from heterogeneous sources.

Usage:
  python clean_data.py --input data.xlsx --output cleaned.json
  python clean_data.py --input data.csv --output cleaned.json --imputation median
  cat raw.json | python clean_data.py --stdin --output cleaned.json
  python clean_data.py --input data.xlsx --output cleaned.json --target-units metric

Supported: .xlsx, .xls, .csv, .tsv, .txt, JSON stdin
"""

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: pip install pandas numpy openpyxl", file=sys.stderr)
    sys.exit(1)

warnings.filterwarnings("ignore")

MISSING_PATTERNS = [
    "N/A", "NA", "n/a", "-", "--", "null", "NULL", "NaN", "#VALUE!", "#N/A",
    "TBD", "tbd", "<LOD", "<LOQ", "",
]

UNIT_MAP = {
    "MPa": ("pressure", 1.0),
    "bar": ("pressure", 0.1),
    "psi": ("pressure", 0.00689476),
    "kPa": ("pressure", 0.001),
    "atm": ("pressure", 0.101325),
    "mmHg": ("pressure", 0.000133322),
    "Torr": ("pressure", 0.000133322),
    "C": ("temperature", 1.0),
    "℃": ("temperature", 1.0),
    "°C": ("temperature", 1.0),
    "F": ("temperature", "lambda x: (x-32)*5/9"),
    "°F": ("temperature", "lambda x: (x-32)*5/9"),
    "K": ("temperature", "lambda x: x-273.15"),
    "wt%": ("concentration", 1.0),
    "vol%": ("concentration", 1.0),
    "mol/L": ("concentration", 1.0),
    "M": ("concentration", 1.0),
    "mM": ("concentration", 0.001),
    "μM": ("concentration", 0.000001),
    "ppm": ("concentration", 1.0),
    "ppb": ("concentration", 0.001),
    "mg/mL": ("concentration", 1.0),
    "μg/mL": ("concentration", 0.001),
    "g/L": ("concentration", 1.0),
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "mg": ("mass", 0.001),
    "μg": ("mass", 0.000001),
    "lb": ("mass", 453.592),
    "oz": ("mass", 28.3495),
    "L": ("volume", 1.0),
    "mL": ("volume", 0.001),
    "μL": ("volume", 0.000001),
    "gal": ("volume", 3.78541),
    "h": ("time", 60.0),
    "hr": ("time", 60.0),
    "min": ("time", 1.0),
    "s": ("time", 1.0 / 60.0),
    "sec": ("time", 1.0 / 60.0),
    "day": ("time", 1440.0),
    "mm": ("length", 1.0),
    "cm": ("length", 10.0),
    "m": ("length", 1000.0),
    "μm": ("length", 0.001),
    "nm": ("length", 0.000001),
    "Å": ("length", 0.0001),
}

TIME_COLUMN_PATTERNS = [
    "time", "date", "timestamp", "datetime", "时间", "日期", "时刻",
]


def detect_time_column(df):
    for col in df.columns:
        if any(p in col.lower() for p in TIME_COLUMN_PATTERNS):
            return col
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def infer_column_type(series, n_rows):
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    try:
        pd.to_numeric(series, errors="raise")
        return "numeric"
    except (ValueError, TypeError):
        pass
    n_unique = series.nunique()
    if n_unique < max(0.2 * n_rows, 2):
        return "categorical"
    return "text"


def replace_missing(df):
    for col in df.columns:
        mask = df[col].astype(str).str.strip().isin(MISSING_PATTERNS)
        df.loc[mask, col] = np.nan
        df[col] = df[col].replace(["nan", "NaN", "None"], np.nan)
    return df


def impute_missing(df, strategy, col_types):
    imputed = {}
    for col, ctype in col_types.items():
        if ctype != "numeric":
            continue
        nan_count = df[col].isna().sum()
        if nan_count == 0:
            continue
        if strategy == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif strategy == "median":
            df[col] = df[col].fillna(df[col].median())
        elif strategy == "ffill":
            df[col] = df[col].ffill()
        elif strategy == "bfill":
            df[col] = df[col].bfill()
        elif strategy == "drop":
            df = df.dropna(subset=[col])
        elif strategy == "interpolate":
            df[col] = df[col].interpolate(method="linear")
        elif strategy.startswith("constant:"):
            val = float(strategy.split(":", 1)[1])
            df[col] = df[col].fillna(val)
        imputed[col] = int(nan_count)
    return df, imputed


def detect_outliers_iqr(series, threshold=1.5):
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
    return (series < lower) | (series > upper)


def detect_outliers_zscore(series, threshold=3.0):
    z = np.abs((series - series.mean()) / series.std())
    return z > threshold


def detect_outliers_mad(series, threshold=3.5):
    median = series.median()
    mad = np.median(np.abs(series - median))
    if mad == 0:
        return pd.Series(False, index=series.index)
    modified_z = 0.6745 * (series - median) / mad
    return np.abs(modified_z) > threshold


def handle_outliers(df, col_types, method, threshold, handling):
    outliers_found = {}
    for col, ctype in col_types.items():
        if ctype != "numeric":
            continue
        series = df[col].dropna()
        if len(series) < 4:
            continue
        if method == "iqr":
            mask = detect_outliers_iqr(series, threshold)
        elif method == "zscore":
            mask = detect_outliers_zscore(series, threshold)
        elif method == "mad":
            mask = detect_outliers_mad(series, threshold)
        else:
            continue
        n_out = mask.sum()
        if n_out == 0:
            continue
        outliers_found[col] = int(n_out)
        if handling == "cap":
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
            df.loc[series.index[mask], col] = df.loc[series.index[mask], col].clip(lower, upper)
        elif handling == "remove":
            df.loc[series.index[mask], col] = np.nan
    return df, outliers_found


def detect_units_from_header(col_name):
    col_lower = col_name.lower()
    for unit_key in UNIT_MAP:
        if col_lower.endswith(unit_key.lower()) or f"_{unit_key.lower()}" in col_lower:
            return unit_key
        if f"({unit_key})" in col_lower or f"[{unit_key}]" in col_lower:
            return unit_key
    return None


def normalize_units(df, col_types, target_units):
    conversions = []
    for col, ctype in col_types.items():
        if ctype != "numeric":
            continue
        detected_unit = detect_units_from_header(col)
        if not detected_unit:
            continue
        entry = UNIT_MAP.get(detected_unit)
        if not entry:
            continue
        _, factor = entry
        if target_units == "none":
            conversions.append({"column": col, "detected_unit": detected_unit, "operation": "annotate_only"})
            continue
        if isinstance(factor, str) and factor.startswith("lambda"):
            df[col] = df[col].apply(lambda x: eval(factor)(x) if pd.notna(x) else x)
        elif factor != 1.0:
            df[col] = df[col] * factor
        new_unit = detected_unit
        conversions.append({
            "column": col, "original_unit": detected_unit,
            "target_unit": new_unit, "conversion_factor": factor,
            "operation": "unit_normalize" if factor != 1.0 else "unit_verified",
        })
    return df, conversions


def normalize_values(df, col_types, method):
    for col, ctype in col_types.items():
        if ctype != "numeric":
            continue
        series = df[col].dropna()
        if len(series) < 2:
            continue
        if method == "minmax":
            mn, mx = series.min(), series.max()
            if mx > mn:
                df[col] = (df[col] - mn) / (mx - mn)
        elif method == "zscore":
            df[col] = (df[col] - series.mean()) / series.std()
    return df


def process_file(file_path, args):
    suffix = Path(file_path).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=args.sheet or 0)
    elif suffix == ".tsv":
        df = pd.read_csv(file_path, sep="\t")
    elif suffix == ".csv":
        try:
            df = pd.read_csv(file_path)
        except (UnicodeDecodeError, pd.errors.ParserError):
            for enc in ["utf-8", "gbk", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"Cannot decode {file_path}")
    elif suffix == ".json":
        df = pd.read_json(file_path)
    else:
        df = pd.read_csv(file_path, sep=None, engine="python")

    n_rows_input = len(df)
    transformations = []

    time_col = detect_time_column(df)
    if time_col and pd.api.types.is_object_dtype(df[time_col]):
        try:
            df[time_col] = pd.to_datetime(df[time_col])
        except Exception:
            pass

    col_types = {}
    for col in df.columns:
        col_types[col] = infer_column_type(df[col], n_rows_input)

    df = replace_missing(df)

    df, imputed = impute_missing(df, args.imputation, col_types)
    for col, count in imputed.items():
        transformations.append({"column": col, "operation": "impute", "method": args.imputation, "imputed_count": count})

    if args.outlier != "none":
        df, outliers = handle_outliers(df, col_types, args.outlier, args.outlier_threshold, args.outlier_handling)
        for col, count in outliers.items():
            transformations.append({"column": col, "operation": "outlier_flag", "method": args.outlier, "outliers_found": count, "handling": args.outlier_handling})

    if args.target_units != "none":
        df, unit_convs = normalize_units(df, col_types, args.target_units)
        transformations.extend(unit_convs)

    if args.normalize in ("minmax", "zscore"):
        df = normalize_values(df, col_types, args.normalize)

    experiments = []
    for idx, row in df.iterrows():
        variables = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                variables[col] = None
            elif col_types[col] == "numeric":
                unit = detect_units_from_header(col)
                variables[col] = {"value": float(val), "unit": unit}
            else:
                variables[col] = str(val)

        experiments.append({
            "experiment_id": f"EXP-{idx + 1:04d}",
            "timestamp": str(row[time_col]) if time_col and pd.notna(row.get(time_col)) else None,
            "variables": {k: v for k, v in variables.items() if k != time_col},
            "observations": {},
            "batch_id": None,
            "source_file": str(Path(file_path).name),
            "source_sheet": args.sheet or "Sheet1",
            "source_row": idx + 1,
        })

    metadata = {
        "script": "clean_data.py",
        "version": "1.0.0",
        "input_file": str(file_path),
        "processing_timestamp": datetime.utcnow().isoformat() + "Z",
        "rows_input": n_rows_input,
        "rows_output": len(experiments),
        "rows_removed": n_rows_input - len(experiments),
        "column_types": col_types,
        "transformations": transformations,
    }

    return {"metadata": metadata, "experiments": experiments}


def main():
    parser = argparse.ArgumentParser(description="Chemistry Experiment Data Cleaner")
    parser.add_argument("--input", help="Input file path (.xlsx, .csv, .tsv, .txt, .json)")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin (JSON)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--sheet", type=int, default=None, help="Excel sheet index (0-based)")
    parser.add_argument("--imputation", default="median", choices=["mean", "median", "ffill", "bfill", "drop", "interpolate", "constant:0"], help="Missing value strategy")
    parser.add_argument("--outlier", default="iqr", choices=["iqr", "zscore", "mad", "none"], help="Outlier detection method")
    parser.add_argument("--outlier-threshold", type=float, default=1.5, help="Outlier threshold (IQR multiplier or Z-score)")
    parser.add_argument("--outlier-handling", default="flag", choices=["flag", "cap", "remove"], help="How to handle detected outliers")
    parser.add_argument("--normalize", default="none", choices=["minmax", "zscore", "none"], help="Value normalization")
    parser.add_argument("--target-units", default="metric", choices=["SI", "metric", "none"], help="Target unit system")
    parser.add_argument("--time-align", default="auto", choices=["auto", "minutely", "hourly", "daily", "none"], help="Timestamp alignment")

    args = parser.parse_args()

    if args.stdin:
        if args.input:
            print("ERROR: --stdin and --input are mutually exclusive", file=sys.stderr)
            sys.exit(1)
        raw = json.load(sys.stdin)
        result = raw
    else:
        if not args.input:
            print("ERROR: --input or --stdin required", file=sys.stderr)
            sys.exit(1)
        if not Path(args.input).exists():
            print(f"ERROR: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        result = process_file(args.input, args)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Cleaned: {result['metadata']['rows_input']} rows → {result['metadata']['rows_output']} rows")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()