#!/usr/bin/env python
"""adaptive_charts.py — Phase 5.0a adaptive chart planner (deterministic, data-truth mandate).

Profiles the dataset shape and picks the chart type per column BEFORE any plotting:

  data shape detected                      -> chart type
  ----------------------------------------+---------------------------------------------
  2D field (x/y coordinate grid + value)  -> filled contour (cloud map) + colorbar,
                                             actual sample points overlaid
  multi-parameter time series (2..8 cols) -> z-normalized temporal overlay
  single time series column               -> line chart
  (all temporal charts use the aligned time axis)

Time alignment (mandatory before any temporal chart):
  - detect/parse the time column (multi-format), count unparsable rows
  - verify monotonicity, measure sampling interval
  - provenance recorded in 02_processed/time_alignment.json

Outputs (all written inside RUN_DIR via safe_path/safe_open containment):
  02_processed/time_alignment.json      alignment provenance
  03_figures/adaptive_chart_plan.json   per-column decision record (why this chart)
  03_figures/fig_adaptive_*.png         rendered charts
  03_figures/plot_manifest.json         entries appended (source=adaptive_charts.py)

Usage:
  python adaptive_charts.py "$RUN_DIR" [--data FILE] [--time-col NAME]
      [--x-col NAME] [--y-col NAME] [--value-cols a,b,c] [--max-charts 12]

Exit codes: 0 = charts written; 2 = nothing applicable (reason printed, no charts);
1 = hard failure. Never fabricates data (Data Truth Mandate).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm

TIME_NAME_HINTS = ("time", "date", "timestamp", "day", "hour", "minute", "second", "ts")
MAX_OVERLAY_COLS = 8
MIN_GRID_UNIQUE_PER_AXIS = 4


def log(msg):
    print(msg, flush=True)


def make_guards(run_dir):
    """Containment guards: every read/write is confined to the resolved run dir."""
    expected = Path(run_dir).resolve()

    def safe_path(rel):
        p = (expected / rel).resolve()
        p.relative_to(expected)
        return p

    def safe_open(rel, mode="r", **kw):
        return safe_path(rel).open(mode, **kw)

    return expected, safe_path, safe_open


def load_frame(safe_path, data_arg):
    """Load the analysis frame: explicit --data, else 02_processed/cleaned_data.csv."""
    candidates = []
    if data_arg:
        candidates.append(data_arg)
    candidates.append("02_processed/cleaned_data.csv")
    for rel in candidates:
        try:
            p = safe_path(rel)
            if p.is_file():
                log("[adaptive] data source: %s" % p)
                return pd.read_csv(p), str(p)
        except (ValueError, OSError):
            continue
    return None, None


def detect_time_col(df, explicit):
    if explicit and explicit in df.columns:
        return explicit
    for col in df.columns:
        if any(h in str(col).lower() for h in TIME_NAME_HINTS):
            return col
    for col in df.columns:
        if df[col].dtype == object:
            parsed = pd.to_datetime(df[col].head(30), errors="coerce", format="mixed")
            if parsed.notna().sum() >= 25:
                return col
    return None


def align_time(df, time_col):
    """Parse + sort the time axis; return aligned frame + alignment provenance."""
    info = {"time_col": time_col, "method": "single-source-parse", "merged_sources": []}
    if time_col is None:
        info["method"] = "index-implied"
        info["note"] = ("no parsable time column; charts use sample index as a uniform "
                        "surrogate axis and this is recorded as index-implied, not real time")
        info["n_rows"] = int(len(df))
        return df.reset_index(drop=True).assign(_t=np.arange(len(df))), info
    parsed = pd.to_datetime(df[time_col], errors="coerce", format="mixed")
    n_total, n_bad = int(len(df)), int(parsed.isna().sum())
    kept = df.loc[parsed.notna()].copy()
    kept["_t"] = parsed[parsed.notna()]
    kept = kept.sort_values("_t", kind="mergesort")
    intervals = kept["_t"].diff().dt.total_seconds().dropna()
    info.update({
        "n_rows_total": n_total, "n_rows_dropped_unparsable": n_bad,
        "monotonic_after_sort": bool(kept["_t"].is_monotonic_increasing),
        "median_interval_s": float(intervals.median()) if len(intervals) else None,
        "span_s": float((kept["_t"].iloc[-1] - kept["_t"].iloc[0]).total_seconds()) if len(kept) > 1 else 0.0,
    })
    return kept.reset_index(drop=True), info


def detect_2d_field(df, numeric_cols, x_col, y_col, value_cols):
    """Detect an x/y coordinate grid: repeated coordinate values covering a grid."""
    if x_col and y_col and x_col in df.columns and y_col in df.columns:
        vals = [c for c in (value_cols or []) if c in df.columns and c not in (x_col, y_col)]
        return (x_col, y_col, vals, "explicit")
    cand = [c for c in numeric_cols if df[c].nunique() >= MIN_GRID_UNIQUE_PER_AXIS]
    for xi in range(len(cand)):
        for yi in range(xi + 1, len(cand)):
            x, y = cand[xi], cand[yi]
            nx, ny = df[x].nunique(), df[y].nunique()
            pairs = df[[x, y]].drop_duplicates().shape[0]
            # grid coverage alone separates fields from sensor pairs: two
            # unrelated numeric columns give coverage ~ pairs/(nx*ny) ~ 1/N,
            # a coordinate grid gives ~1.0 (partial grids 0.6+)
            grid_coverage = pairs / float(nx * ny)
            if grid_coverage >= 0.6 and nx <= 400 and ny <= 400:
                vals = [c for c in numeric_cols if c not in (x, y)]
                if vals:
                    return (x, y, vals, "grid-inferred (%d x %d grid, %.0f%% coverage)"
                            % (nx, ny, grid_coverage * 100))
    return None


def plot_contour(ax, df, x_col, y_col, v_col):
    """Filled contour (cloud map) from grid samples; binned-mean fallback when sparse."""
    x, y, z = df[x_col].to_numpy(float), df[y_col].to_numpy(float), df[v_col].to_numpy(float)
    xi, yi = np.unique(x), np.unique(y)
    if len(xi) >= MIN_GRID_UNIQUE_PER_AXIS and len(yi) >= MIN_GRID_UNIQUE_PER_AXIS \
            and len(x) >= len(xi) * len(yi) * 0.6:
        grid = df.pivot_table(index=y_col, columns=x_col, values=v_col, aggfunc="mean")
        gx, gy = np.meshgrid(grid.columns.to_numpy(float), grid.index.to_numpy(float))
        cs = ax.contourf(gx, gy, grid.to_numpy(float), levels=18, cmap=plt.get_cmap("viridis"))
        method = "pivot-grid contourf"
    else:
        bins = min(60, max(10, int(np.sqrt(len(x)))))
        H, xe, ye = np.histogram2d(x, y, bins=bins, weights=z)
        cnt, _, _ = np.histogram2d(x, y, bins=bins)
        mean_grid = np.divide(H, cnt, out=np.full_like(H, np.nan), where=cnt > 0)
        xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
        cs = ax.contourf(xc, yc, mean_grid.T, levels=18, cmap=plt.get_cmap("viridis"))
        method = "binned-mean contourf (sparse samples)"
    ax.scatter(x, y, s=4, c="white", alpha=0.25, linewidths=0, label="samples")
    bar = plt.colorbar(cs, ax=ax, fraction=0.046, pad=0.02)
    bar.set_label(v_col, fontsize=12)
    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title("%s over %s x %s (filled contour)" % (v_col, x_col, y_col), fontsize=13)
    return method


def append_plot_manifest(safe_path, safe_open, entries):
    manifest = {}
    if safe_path("03_figures/plot_manifest.json").is_file():
        with safe_open("03_figures/plot_manifest.json", "r", encoding="utf-8") as fh:
            try:
                manifest = json.load(fh)
            except json.JSONDecodeError:
                manifest = {}
    plots = manifest.get("plots")
    if not isinstance(plots, list):
        plots = []
    have = {p.get("filename") for p in plots if isinstance(p, dict)}
    for e in entries:
        if e["filename"] not in have:
            plots.append(e)
            have.add(e["filename"])
    manifest["plots"] = plots
    with safe_open("03_figures/plot_manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--data", default=None)
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--x-col", default=None)
    ap.add_argument("--y-col", default=None)
    ap.add_argument("--value-cols", default=None)
    ap.add_argument("--max-charts", type=int, default=12)
    args = ap.parse_args()

    expected, safe_path, safe_open = make_guards(args.run_dir)
    if not expected.is_dir():
        log("[adaptive] FAIL: run dir does not exist: %s" % expected)
        sys.exit(1)
    fig_dir = expected / "03_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    (expected / "02_processed").mkdir(parents=True, exist_ok=True)

    df, source = load_frame(safe_path, args.data)
    if df is None:
        log("[adaptive] NOT_APPLICABLE: no data file (checked --data, 02_processed/cleaned_data.csv)")
        sys.exit(2)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    decisions, files, manifest_entries = [], [], []

    # -- time alignment first (mandatory before any temporal chart) -------------
    time_col = detect_time_col(df, args.time_col)
    aligned, align_info = align_time(df, time_col)
    with safe_open("02_processed/time_alignment.json", "w", encoding="utf-8") as fh:
        json.dump(align_info, fh, ensure_ascii=False, indent=1)
    log("[adaptive] time alignment: %s" % json.dumps(align_info)[:220])

    value_filter = [c.strip() for c in args.value_cols.split(",")] if args.value_cols else None

    # -- 2D field -> contour (cloud map) ---------------------------------------
    field = detect_2d_field(aligned, numeric_cols, args.x_col, args.y_col, value_filter)
    if field:
        x_col, y_col, val_cols, why = field
        if value_filter:
            val_cols = [c for c in val_cols if c in value_filter] or val_cols
        log("[adaptive] 2D field detected: %s x %s (%s)" % (x_col, y_col, why))
        for v_col in val_cols[: max(1, args.max_charts // 2)]:
            fig, ax = plt.subplots(figsize=(9, 6.2))
            method = plot_contour(ax, aligned, x_col, y_col, v_col)
            out = fig_dir / ("fig_adaptive_contour_%s.png" % v_col)
            fig.tight_layout()
            fig.savefig(out, dpi=130)
            plt.close(fig)
            files.append(str(out))
            decisions.append({"target": v_col, "shape": "2d_field", "chart_type": "contour_cloud",
                              "axes": {"x": x_col, "y": y_col}, "render_method": method, "reason": why})
            manifest_entries.append({"filename": out.name,
                                     "title": "%s contour (%s x %s)" % (v_col, x_col, y_col),
                                     "chart_type": "contour", "source": "adaptive_charts.py",
                                     "vlm_priority": "MANDATORY"})

    # -- time series -> line / overlay -----------------------------------------
    ts_cols = [c for c in numeric_cols if not (field and c in field[:2])]
    ts_cols = [c for c in ts_cols if (value_filter is None or c in value_filter)][:MAX_OVERLAY_COLS]
    if ts_cols and not field:
        axis_label = str(align_info.get("time_col") or "sample index")
        if 1 < len(ts_cols) <= MAX_OVERLAY_COLS:
            fig, ax = plt.subplots(figsize=(11, 5.6))
            mu, sd = aligned[ts_cols].mean(), aligned[ts_cols].std().replace(0, 1)
            for c in ts_cols:
                ax.plot(aligned["_t"], (aligned[c] - mu[c]) / sd[c], lw=1.0, label=c)
            ax.legend(fontsize=9, ncol=min(4, len(ts_cols)))
            ax.set_xlabel(axis_label, fontsize=12)
            ax.set_ylabel("z-score", fontsize=12)
            ax.set_title("Temporal overlay (z-normalized, %d parameters, time-aligned)" % len(ts_cols), fontsize=13)
            ax.grid(True, alpha=0.25)
            out = fig_dir / "fig_adaptive_overlay.png"
            fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
            files.append(str(out))
            decisions.append({"target": ts_cols, "shape": "multi_parameter_time_series",
                              "chart_type": "z_overlay",
                              "reason": "2..8 numeric series on one aligned time axis"})
            manifest_entries.append({"filename": out.name, "title": "Adaptive temporal overlay",
                                     "chart_type": "temporal_overlay", "source": "adaptive_charts.py",
                                     "vlm_priority": "MANDATORY"})
        singles = ts_cols[1:5] if len(ts_cols) > MAX_OVERLAY_COLS else ts_cols[:1]
        for c in singles:
            fig, ax = plt.subplots(figsize=(11, 4.4))
            ax.plot(aligned["_t"], aligned[c], lw=1.0, color="#1a3a5c")
            ax.set_xlabel(axis_label, fontsize=12)
            ax.set_ylabel(c, fontsize=12)
            ax.set_title("%s vs %s (line)" % (c, axis_label), fontsize=13)
            ax.grid(True, alpha=0.25)
            out = fig_dir / ("fig_adaptive_line_%s.png" % c)
            fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
            files.append(str(out))
            decisions.append({"target": c, "shape": "single_time_series", "chart_type": "line",
                              "reason": "single measurement channel over the aligned time axis"})
            manifest_entries.append({"filename": out.name, "title": "%s (line)" % c,
                                     "chart_type": "line", "source": "adaptive_charts.py",
                                     "vlm_priority": "SUPPLEMENTARY"})

    plan = {
        "source_data": source, "time_alignment": align_info,
        "decisions": decisions, "files": files,
        "chart_policy": ("2d_field->contour_cloud; multi_parameter_time_series->z_overlay; "
                         "single_time_series->line; all temporal charts on the aligned axis"),
    }
    with safe_open("03_figures/adaptive_chart_plan.json", "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1)
    if manifest_entries:
        append_plot_manifest(safe_path, safe_open, manifest_entries)
    if not files:
        log("[adaptive] NOT_APPLICABLE: no mappable data shape (no 2D field, no numeric series)")
        sys.exit(2)
    log("[adaptive] wrote %d chart(s); plan + alignment provenance recorded" % len(files))


if __name__ == "__main__":
    main()
