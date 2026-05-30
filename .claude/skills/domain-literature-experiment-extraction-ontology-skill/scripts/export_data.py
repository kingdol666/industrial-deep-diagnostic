#!/usr/bin/env python3
"""
CSV/Excel export utilities for experiment data.
Converts JSON experiment records to CSV or Excel with proper column ordering.
"""

import csv
import json
from datetime import datetime
from pathlib import Path


DEFAULT_COLUMNS = [
    "experiment_id", "paper_title", "year", "source_doi",
    "sample_name", "material_system", "material_grade",
    "additive", "additive_concentration", "additive_concentration_unit",
    "plasticizer", "plasticizer_concentration", "plasticizer_concentration_unit",
    "crosslinker", "crosslinker_concentration", "crosslinker_concentration_unit",
    "solvent", "film_preparation_method",
    "drying_temperature", "drying_temperature_unit",
    "drying_time", "drying_time_unit",
    "film_thickness", "film_thickness_unit",
    "measured_property", "measured_value", "measured_unit",
    "comparison_baseline", "result_direction",
    "confidence", "source_page", "notes"
]


def experiments_to_csv(experiments: list, output_path: Path,
                       columns: list = None):
    columns = columns or DEFAULT_COLUMNS
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for exp in experiments:
            row = {col: exp.get(col, "") for col in columns}
            if row.get("confidence") == "":
                row["confidence"] = exp.get("confidence", "")
            writer.writerow(row)
    print(f"CSV exported: {len(experiments)} rows -> {output_path}")


def experiments_to_excel(experiments: list, output_path: Path,
                         columns: list = None):
    try:
        import openpyxl
    except ImportError:
        print("openpyxl not installed. Install with: pip install openpyxl")
        print("Falling back to CSV...")
        experiments_to_csv(experiments, output_path.with_suffix(".csv"), columns)
        return

    columns = columns or DEFAULT_COLUMNS
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Experiments"
    ws.append(columns)

    for exp in experiments:
        row = [exp.get(col, "") for col in columns]
        ws.append(row)

    wb.save(output_path)
    print(f"Excel exported: {len(experiments)} rows -> {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Export experiment data to CSV or Excel")
    parser.add_argument("--input", required=True, help="Path to experiment results JSON")
    parser.add_argument("--output", required=True, help="Output file path (.csv or .xlsx)")
    parser.add_argument("--columns", nargs="*", help="Column order (default: standard schema)")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    experiments = data.get("experiments", [])
    if not experiments:
        print("No experiments found in input data.")
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".xlsx":
        experiments_to_excel(experiments, output_path, args.columns)
    else:
        experiments_to_csv(experiments, output_path.with_suffix(".csv"), args.columns)


if __name__ == "__main__":
    main()