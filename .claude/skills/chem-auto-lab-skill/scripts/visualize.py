#!/usr/bin/env python3
"""
Chemistry Experiment Visualization Toolkit
============================================
Generates publication-quality charts from structured experiment data.

Usage:
  python visualize.py --data cleaned.json --output-dir ./figures
  python visualize.py --data cleaned.json --output-dir ./figures --type timeseries
  python visualize.py --data cleaned.json --output-dir ./figures --type correlation
"""

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

warnings.filterwarnings("ignore")

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
})


def load_data(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_dataframe(data):
    experiments = data.get("experiments", [])
    rows = []
    for exp in experiments:
        row = {"_experiment_id": exp.get("experiment_id", ""), "_source_row": exp.get("source_row", 0)}
        for key, val in exp.get("variables", {}).items():
            if val is None:
                row[key] = np.nan
            elif isinstance(val, dict):
                row[key] = val.get("value", np.nan)
            elif isinstance(val, (int, float)):
                row[key] = val
            else:
                row[key] = val
        rows.append(row)
    return pd.DataFrame(rows)


def plot_timeseries(df, output_dir, plot_id=1):
    if not HAS_MATPLOTLIB:
        return None

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]
    if len(numeric_cols) < 1:
        return None

    n_cols = len(numeric_cols)
    n_rows = max(1, min(4, (n_cols + 2) // 3))
    n_cols_per_row = min(3, n_cols)

    fig, axes = plt.subplots(n_rows, n_cols_per_row, figsize=(5 * n_cols_per_row, 4 * n_rows))
    if n_rows == 1 and n_cols_per_row == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols_per_row == 1:
        axes = axes.reshape(-1, 1)

    for i, col in enumerate(numeric_cols):
        r, c = i // n_cols_per_row, i % n_cols_per_row
        ax = axes[r, c]
        series = df[col].dropna()
        if len(series) > 0:
            ax.plot(range(len(series)), series.values, linewidth=0.8, color="#2196F3")
            ax.set_title(col, fontsize=9)
            ax.set_xlabel("Index")
            ax.grid(True, alpha=0.3)

    for i in range(len(numeric_cols), n_rows * n_cols_per_row):
        r, c = i // n_cols_per_row, i % n_cols_per_row
        axes[r, c].set_visible(False)

    fig.suptitle("Multi-Panel Time Series", fontsize=14, fontweight="bold")
    fig.tight_layout()

    path = Path(output_dir) / f"{plot_id:02d}_timeseries.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)

    return {"id": plot_id, "file": path.name, "type": "multi_panel_timeseries", "variables": numeric_cols, "description": "Multi-panel overview of all numeric variables"}


def plot_correlation_heatmap(df, output_dir, plot_id=2):
    if not HAS_MATPLOTLIB:
        return None

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]
    if len(numeric_cols) < 2:
        return None

    corr = df[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(max(8, len(numeric_cols) * 0.8), max(6, len(numeric_cols) * 0.7)))
    if HAS_SEABORN:
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, square=True, linewidths=0.5, ax=ax)
    else:
        im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
        plt.colorbar(im, ax=ax)
        for i in range(len(numeric_cols)):
            for j in range(len(numeric_cols)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
        ax.set_xticks(range(len(numeric_cols)))
        ax.set_yticks(range(len(numeric_cols)))
        ax.set_xticklabels(numeric_cols, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(numeric_cols, fontsize=8)

    ax.set_title("Correlation Heatmap", fontsize=14, fontweight="bold")
    fig.tight_layout()

    path = Path(output_dir) / f"{plot_id:02d}_correlation_heatmap.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)

    return {"id": plot_id, "file": path.name, "type": "correlation_heatmap", "variables": numeric_cols, "description": "Correlation matrix of all numeric variables"}


def plot_distribution(df, output_dir, plot_id=3):
    if not HAS_MATPLOTLIB:
        return None

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]
    if len(numeric_cols) < 1:
        return None

    col = numeric_cols[0]
    series = df[col].dropna()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(series, bins=min(30, len(series) // 3), edgecolor="white", color="#4CAF50", alpha=0.8)
    ax.set_title(f"Distribution: {col}", fontsize=14, fontweight="bold")
    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = Path(output_dir) / f"{plot_id:02d}_distribution.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)

    return {"id": plot_id, "file": path.name, "type": "distribution", "variables": [col], "description": f"Distribution histogram of {col}"}


def plot_normalized_overlay(df, output_dir, plot_id=4):
    if not HAS_MATPLOTLIB:
        return None

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]
    if len(numeric_cols) < 2:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    for col in numeric_cols[:8]:
        series = df[col].dropna()
        if len(series) > 0:
            normalized = (series - series.min()) / (series.max() - series.min() + 1e-10)
            ax.plot(range(len(normalized)), normalized.values, linewidth=0.8, label=col, alpha=0.8)

    ax.set_title("Normalized Variable Overlay", fontsize=14, fontweight="bold")
    ax.set_xlabel("Index")
    ax.set_ylabel("Normalized Value")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = Path(output_dir) / f"{plot_id:02d}_normalized_overlay.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)

    return {"id": plot_id, "file": path.name, "type": "normalized_overlay", "variables": numeric_cols[:8], "description": "All variables normalized to [0,1] for pattern comparison"}


def generate_all(data_path, output_dir, chart_type="auto"):
    if not HAS_MATPLOTLIB:
        print("WARNING: matplotlib not available. Install: pip install matplotlib pandas numpy", file=sys.stderr)
        return []

    data = load_data(data_path)
    df = extract_dataframe(data)
    plots = []

    if chart_type in ("auto", "timeseries"):
        p = plot_timeseries(df, output_dir, 1)
        if p:
            plots.append(p)

    if chart_type in ("auto", "correlation"):
        p = plot_correlation_heatmap(df, output_dir, 2)
        if p:
            plots.append(p)

    if chart_type in ("auto", "distribution"):
        p = plot_distribution(df, output_dir, 3)
        if p:
            plots.append(p)

    if chart_type in ("auto", "comparison"):
        p = plot_normalized_overlay(df, output_dir, 4)
        if p:
            plots.append(p)

    manifest = {
        "generator": "visualize.py",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "figures": plots,
    }
    manifest_path = Path(output_dir) / "plot_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return plots


def main():
    parser = argparse.ArgumentParser(description="Chemistry Experiment Visualization Toolkit")
    parser.add_argument("--data", required=True, help="Cleaned experiment data JSON file")
    parser.add_argument("--output-dir", required=True, help="Output directory for figures")
    parser.add_argument("--type", default="auto", choices=["auto", "timeseries", "correlation", "distribution", "comparison"], help="Chart type to generate")

    args = parser.parse_args()

    if not Path(args.data).exists():
        print(f"ERROR: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib not available. Install: pip install matplotlib pandas numpy", file=sys.stderr)
        sys.exit(1)

    plots = generate_all(args.data, args.output_dir, args.type)

    if plots:
        print(f"Generated {len(plots)} figures in {args.output_dir}")
        for p in plots:
            print(f"  [{p['id']}] {p['file']} ({p['type']})")
    else:
        print("No figures generated (no numeric data found)")


if __name__ == "__main__":
    main()