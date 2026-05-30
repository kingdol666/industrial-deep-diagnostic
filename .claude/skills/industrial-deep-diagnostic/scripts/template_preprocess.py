#!/usr/bin/env python3
"""
PREPROCESSING TEMPLATE — Agent Customizes This Script
======================================================

Instructions for the agent:
1. Run `node inspect.mjs <data_path>` first to see data structure
2. Based on the inspection results, customize this script:
   - Set TIME_COL to the actual time column name
   - Set NUMERIC_COLS to the numeric columns to process
   - Set FILL_STRATEGY per column based on its type
   - Set RESAMPLE_RATE if needed
3. Write the customized script to <RUN_DIR>/06_scripts/preprocess.py
4. Run it: $PYTHON <RUN_DIR>/06_scripts/preprocess.py (use uv venv, NOT system python3)
"""

import json, sys
from pathlib import Path

# === AGENT: FILL IN THESE VALUES BASED ON DATA INSPECTION ===
INPUT_FILE = "{{INPUT_FILE}}"       # e.g., path to CSV
OUTPUT_DIR = "{{OUTPUT_DIR}}"       # e.g., RUN_DIR/02_processed
TIME_COL = "{{TIME_COL}}"           # e.g., "timestamp"
NUMERIC_COLS = []                    # e.g., ["temp_c", "pressure_mpa", "thickness_um"]
FILL_STRATEGY = {}                   # e.g., {"temp_c": "interpolate", "valve_pos": "ffill"}
RESAMPLE_RATE = None                 # e.g., "1s" or None to keep original
# === END AGENT SECTION ===

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: Run: node scripts/uv_env_setup.mjs to create the Python venv", file=sys.stderr)
    sys.exit(1)

def main():
    # Load data
    suffix = Path(INPUT_FILE).suffix.lower()
    if suffix == '.csv':
        df = pd.read_csv(INPUT_FILE)
    elif suffix == '.parquet':
        df = pd.read_parquet(INPUT_FILE)
    elif suffix == '.json':
        df = pd.read_json(INPUT_FILE)
    else:
        df = pd.read_csv(INPUT_FILE)

    print(f"Loaded: {len(df)} rows x {len(df.columns)} columns")

    # Parse time column
    if TIME_COL and TIME_COL in df.columns:
        df[TIME_COL] = pd.to_datetime(df[TIME_COL])

    # Handle missing values
    report = {"missing_values": {}, "outliers": {}, "transformations": []}
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        missing = df[col].isna().sum()
        if missing > 0:
            strategy = FILL_STRATEGY.get(col, "interpolate")
            if strategy == "interpolate":
                df[col] = df[col].interpolate(method='linear', limit_area='inside')
            elif strategy == "ffill":
                df[col] = df[col].ffill()
            report["missing_values"][col] = {"count": int(missing), "method": strategy}

    # Detect outliers (IQR method, flag only)
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outlier_mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
            count = outlier_mask.sum()
            if count > 0:
                df[f"{col}_outlier"] = outlier_mask
                report["outliers"][col] = {"count": int(count), "method": "iqr"}

    # Resample if requested
    if RESAMPLE_RATE and TIME_COL and TIME_COL in df.columns:
        df = df.set_index(TIME_COL).resample(RESAMPLE_RATE).mean(numeric_only=True).reset_index()
        report["resample"] = {"rate": RESAMPLE_RATE, "rows_after": len(df)}

    # Save
    out_path = Path(OUTPUT_DIR)
    out_path.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_path / "cleaned_data.csv", index=False)
    with open(out_path / "data_quality_report.json", 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Saved: {out_path / 'cleaned_data.csv'}")
    print(f"Report: {out_path / 'data_quality_report.json'}")

if __name__ == "__main__":
    main()
