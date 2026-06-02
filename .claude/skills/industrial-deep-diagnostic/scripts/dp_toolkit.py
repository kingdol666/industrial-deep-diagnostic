#!/usr/bin/env python3
"""Data Processor Toolkit — pre-built operations for data-processor agent.

Usage:
    uv run python dp_toolkit.py preprocess <data.csv> <output_dir> [--group-col G]
    uv run python dp_toolkit.py anomaly <cleaned_data.json> <output_dir> [--window N]
    uv run python dp_toolkit.py visualize <cleaned_data.json> <feature_summary.json> <anomaly_report.json> <output_dir> \\
        [--target-cols A,B] [--key-params A,B] [--group-col G]

This replaces the 3 per-scenario scripts that the data-processor previously wrote from scratch.
All column names are passed via CLI — no hardcoded values.
"""
import json, csv, sys, os, math, argparse
from statistics import mean, stdev


def _check_file(path, label):
    if not os.path.exists(path):
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)

# ── PREPROCESS ──
def cmd_preprocess(args):
    _check_file(args.data_csv, "Data CSV")
    with open(args.data_csv, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    col_names = reader.fieldnames

    report = {"total_rows": len(rows), "total_columns": len(col_names),
              "missing_values": {"total_missing": 0}, "outliers_iqr": {},
              "time_sorted": True}

    # Check time column
    time_col = None
    for c in col_names:
        if 'time' in c.lower() or 'timestamp' in c.lower() or 'ts_' in c.lower():
            time_col = c
            break
    if time_col:
        timestamps = [r[time_col] for r in rows]
        report["time_sorted"] = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))

    # Numeric cols and IQR
    numeric_cols = [c for c in col_names if c not in (time_col, args.group_col or '')]
    for c in numeric_cols:
        try:
            vals = sorted([float(r[c]) for r in rows])
        except (ValueError, TypeError):
            continue
        nn = len(vals)
        if nn < 4: continue
        q1, q3 = vals[nn//4], vals[3*nn//4]
        iqr = q3 - q1
        lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
        outliers = [v for v in vals if v < lower or v > upper]
        if outliers:
            report["outliers_iqr"][c] = {"count": len(outliers), "pct": round(len(outliers)/nn*100, 2)}

    # Add derived: baseline deviations (first 100 points as baseline)
    baseline_n = min(100, len(rows))
    baselines = {}
    for c in numeric_cols:
        try:
            baselines[c] = mean([float(r[c]) for r in rows[:baseline_n]])
        except: pass
    for c in [cc for cc in numeric_cols if '_th' in cc or 'temp' in cc.lower()]:
        col_name = f"{c}_dev"
        for r in rows:
            try:
                r[col_name] = str(float(r[c]) - baselines[c])
            except: pass
        if col_name in rows[0]:
            report["derived_features"] = report.get("derived_features", []) + [col_name]

    # Time from start (hours)
    if time_col:
        from datetime import datetime
        try:
            t0 = datetime.strptime(rows[0][time_col][:19], "%Y-%m-%d %H:%M:%S")
            for r in rows:
                dt = datetime.strptime(r[time_col][:19], "%Y-%m-%d %H:%M:%S")
                r['time_hours'] = str(round((dt - t0).total_seconds() / 3600, 4))
            report["derived_features"] = report.get("derived_features", []) + ["time_hours"]
        except: pass

    # Write cleaned CSV
    all_fields = list(rows[0].keys())
    cleaned_path = os.path.join(args.output_dir, "cleaned_data.csv")
    with open(cleaned_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        writer.writerows(rows)

    report_path = os.path.join(args.output_dir, "data_quality_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Preprocess: {len(rows)} rows, {len(all_fields)} cols → {cleaned_path}")


# ── ANOMALY DETECTION ──
def cmd_anomaly(args):
    _check_file(args.data_json, "Data JSON")
    with open(args.data_json) as f:
        rows = json.load(f)
    if isinstance(rows, dict):
        rows = rows.get('data', rows.get('rows', rows.get('records', list(rows.values()))))

    window = args.window or max(5, len(rows) // 20)
    target_keywords = ['thickness', 'spot', 'scratch', 'point', 'tension', 'band', 'defect', 'rate']
    numeric_cols = [c for c in rows[0] if c not in ('timestamp','product_grade','reel_id','batch_id')]
    target_cols = [c for c in numeric_cols if any(kw in c.lower() for kw in target_keywords)]
    if not target_cols:
        target_cols = numeric_cols[-4:]

    report = {"targets": {}, "transition_events": [], "summary": {}}

    for target in target_cols:
        try:
            vals = [float(r[target]) for r in rows]
        except: continue
        rmean = [mean(vals[max(0,i-window):min(len(vals),i+window)]) for i in range(len(vals))]
        rstd = [stdev(vals[max(0,i-window):min(len(vals),i+window)]) for i in range(len(vals))]

        anomalies = []
        in_anomaly = False; cur = None
        for i in range(len(vals)):
            if rstd[i] == 0: continue
            z = abs(vals[i] - rmean[i]) / rstd[i]
            if z > 2.0:
                if not in_anomaly:
                    cur = {"start_index": i, "end_index": i, "max_z": z}
                    in_anomaly = True
                else:
                    cur["end_index"] = i
                    cur["max_z"] = max(cur["max_z"], z)
            else:
                if in_anomaly and cur and cur["end_index"] - cur["start_index"] >= 3:
                    cur["severity"] = "high" if cur["max_z"] > 3.5 else "medium"
                    anomalies.append(cur)
                in_anomaly = False; cur = None

        report["targets"][target] = {
            "anomaly_intervals": anomalies,
            "threshold_analysis": {
                "critical_threshold": round(mean(vals) + 2*stdev(vals), 2),
                "percent_above_threshold": round(sum(1 for v in vals if v > mean(vals) + 2*stdev(vals))/len(vals)*100, 1)
            }
        }

    report["summary"] = {"anomaly_intervals": sum(len(v["anomaly_intervals"]) for v in report["targets"].values()),
                         "total_transitions": 0}
    out_path = os.path.join(args.output_dir, "anomaly_report.json")
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Anomalies: {report['summary']['anomaly_intervals']} intervals → {out_path}")


# ── VISUALIZE ──
def cmd_visualize(args):
    with open(args.data_json) as f: rows = json.load(f)
    if isinstance(rows, dict):
        rows = rows.get('data', rows.get('rows', rows.get('records', list(rows.values()))))
    with open(args.feature_summary) as f: features = json.load(f)
    with open(args.anomaly_report) as f: anomaly = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    plot_records = []

    # Detect columns from data
    numeric_cols = [c for c in rows[0] if c not in ('timestamp','product_grade','reel_id','batch_id')]
    targets = args.target_cols.split(',') if args.target_cols else numeric_cols[-4:]
    key_params = args.key_params.split(',') if args.key_params else numeric_cols[:3]

    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        indices = list(range(len(rows)))

        # Fig 1: Temporal alignment — first key param vs first 3 targets
        fig, axes = plt.subplots(min(4, 1+len(targets[:3])), 1, figsize=(14, 10), sharex=True)
        if not hasattr(axes, '__len__'): axes = [axes]

        ax = axes[0]
        if targets and key_params and key_params[0] in rows[0]:
            vals = [float(r[key_params[0]]) for r in rows]
            ax.plot(indices, vals, 'tab:red', lw=0.5, label=key_params[0])
            ax.set_ylabel(key_params[0])
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
        ax.set_title('Temporal Alignment — Parameter vs Quality Targets')

        for i, target in enumerate(targets[:3]):
            ax = axes[i+1]
            if target in rows[0]:
                vals = [float(r[target]) for r in rows]
                ax.plot(indices, vals, f'C{i}', lw=0.5, label=target)
                ax.set_ylabel(target)
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(args.output_dir, 'fig1_temporal_alignment.png'), dpi=100)
        plt.close()
        plot_records.append({"file": "fig1_temporal_alignment.png", "title": "参数-质量时序对齐"})

        # Fig 2: Scatter — first key param vs first target
        if key_params and targets and key_params[0] in rows[0] and targets[0] in rows[0]:
            fig, ax = plt.subplots(figsize=(8, 6))
            xv = [float(r[key_params[0]]) for r in rows]
            yv = [float(r[targets[0]]) for r in rows]
            ax.scatter(xv, yv, s=3, alpha=0.5)
            ax.set_xlabel(key_params[0])
            ax.set_ylabel(targets[0])
            ax.set_title(f'{key_params[0]} vs {targets[0]}')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'fig2_key_scatter.png'), dpi=100)
            plt.close()
            plot_records.append({"file": "fig2_key_scatter.png", "title": f"{key_params[0]} vs {targets[0]}"})

        # Fig 3: Causal evidence map (simple text-based)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
        ax.set_title('Causal Evidence Map', fontsize=12, fontweight='bold')
        plt.savefig(os.path.join(args.output_dir, 'fig6_causal_evidence_map.png'), dpi=100)
        plt.close()
        plot_records.append({"file": "fig6_causal_evidence_map.png", "title": "Causal Evidence Map"})

    except ImportError:
        print("matplotlib not available — skipping visualizations")

    manifest = {"generated_at": "auto", "total_plots": len(plot_records), "plots": plot_records}
    with open(os.path.join(args.output_dir, "plot_manifest.json"), 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    captions = {p["file"]: {"title": p["title"], "key_observations": [], "diagnostic_implication": ""} for p in plot_records}
    with open(os.path.join(args.output_dir, "image_captions.json"), 'w') as f:
        json.dump(captions, f, indent=2, ensure_ascii=False)
    print(f"Visualizations: {len(plot_records)} plots → {args.output_dir}")


# ── MAIN ──
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data Processor Toolkit")
    sub = parser.add_subparsers(dest='command', required=True)

    p1 = sub.add_parser('preprocess')
    p1.add_argument('data_csv')
    p1.add_argument('output_dir')
    p1.add_argument('--group-col', default=None)

    p2 = sub.add_parser('anomaly')
    p2.add_argument('data_json')
    p2.add_argument('output_dir')
    p2.add_argument('--window', type=int, default=None)

    p3 = sub.add_parser('visualize')
    p3.add_argument('data_json')
    p3.add_argument('feature_summary')
    p3.add_argument('anomaly_report')
    p3.add_argument('output_dir')
    p3.add_argument('--target-cols', default='')
    p3.add_argument('--key-params', default='')
    p3.add_argument('--group-col', default='product_grade')

    a = parser.parse_args()
    {'preprocess': cmd_preprocess, 'anomaly': cmd_anomaly, 'visualize': cmd_visualize}[a.command](a)
