#!/usr/bin/env python3
"""Data Processor Toolkit — pre-built operations for data-processor agent.

Usage:
    uv run python dp_toolkit.py preprocess <data.csv> <output_dir> [--group-col G]
    uv run python dp_toolkit.py anomaly <cleaned_data.json> <output_dir> [--window N] [--data-view-mode MODE]
    uv run python dp_toolkit.py visualize <cleaned_data.json> <feature_summary.json> <anomaly_report.json> <output_dir> \\
        [--target-cols A,B] [--key-params A,B] [--group-col G] [--data-view-mode MODE]

This replaces the 3 per-scenario scripts that the data-processor previously wrote from scratch.
All column names are passed via CLI — no hardcoded values.
"""
import json, csv, sys, os, math, argparse
from statistics import mean, stdev


EXCLUDED_META_COLS = {
    'timestamp', 'time', 'time_hours',
    'product_grade', 'product_code', 'product_id', 'product_no',
    'reel_id', 'batch_id', 'lot_id', 'lot_no', 'grade'
}


def _safe_float(value):
    try:
        if value in (None, '', 'null', 'None'):
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def _detect_time_col(col_names):
    for c in col_names:
        cl = c.lower()
        if 'timestamp' in cl or 'time' == cl or cl.endswith('_time') or cl.startswith('time_') or 'date' in cl:
            return c
    return None


def _detect_group_col(col_names, explicit=None):
    if explicit:
        return explicit
    preferred = [
        'product_no', 'product_id', 'product_code', 'product_grade',
        'grade', 'lot_id', 'lot_no', 'batch_id', 'reel_id'
    ]
    lowered = {c.lower(): c for c in col_names}
    for key in preferred:
        if key in lowered:
            return lowered[key]
    return None


def _numeric_columns(rows, excluded=None):
    excluded = set(excluded or [])
    cols = []
    for c in rows[0].keys():
        if c in excluded:
            continue
        values = [_safe_float(r.get(c)) for r in rows[: min(len(rows), 50)]]
        valid = [v for v in values if v is not None]
        if len(valid) >= max(3, len(values) // 3 if values else 0):
            cols.append(c)
    return cols


def _product_groups(rows, group_col):
    if not group_col:
        return {}
    groups = {}
    for idx, row in enumerate(rows):
        key = str(row.get(group_col, '')).strip()
        if not key:
            continue
        groups.setdefault(key, []).append((idx, row))
    return groups


def _rolling_window(values, window):
    n = len(values)
    for i in range(n):
        left = max(0, i - window)
        right = min(n, i + window + 1)
        seg = values[left:right]
        yield seg


def _choose_target_cols(rows, numeric_cols):
    scored = []
    for c in numeric_cols:
        values = [_safe_float(r.get(c)) for r in rows]
        vals = [v for v in values if v is not None]
        if len(vals) < 5:
            continue
        mu = mean(vals)
        sigma = stdev(vals) if len(vals) > 1 else 0
        baseline = abs(mean(vals[: min(10, len(vals))])) + 1e-9
        trend = abs(vals[-1] - vals[0]) / baseline
        cv = sigma / (abs(mu) + 1e-9)
        q1 = sorted(vals)[len(vals) // 4]
        q3 = sorted(vals)[(len(vals) * 3) // 4]
        iqr = q3 - q1
        outlier_ratio = 0 if iqr == 0 else sum(v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr for v in vals) / len(vals)
        scored.append((trend * 0.45 + cv * 0.35 + outlier_ratio * 0.20, c))
    if scored:
        return [c for _, c in sorted(scored, reverse=True)[: min(4, len(scored))]]
    return numeric_cols[-4:]


def _choose_process_cols(numeric_cols, target_cols):
    return [c for c in numeric_cols if c not in set(target_cols)]


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
    col_names = reader.fieldnames or []

    report = {"total_rows": len(rows), "total_columns": len(col_names),
              "missing_values": {"total_missing": 0}, "outliers_iqr": {},
              "time_sorted": True}

    # Check time column
    time_col = _detect_time_col(col_names)
    group_col = _detect_group_col(col_names, args.group_col)
    if time_col:
        timestamps = [r[time_col] for r in rows]
        report["time_sorted"] = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
        if group_col:
            rows.sort(key=lambda r: ((r.get(group_col) or ''), (r.get(time_col) or '')))
            report["sorted_strategy"] = f"group_then_time:{group_col}+{time_col}"
        else:
            rows.sort(key=lambda r: (r.get(time_col) or ''))
            report["sorted_strategy"] = f"time_only:{time_col}"
        timestamps = [r[time_col] for r in rows]
        report["time_sorted_after_preprocess"] = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
    else:
        report["sorted_strategy"] = "original_row_order_no_time_column"

    # Numeric cols and IQR
    numeric_cols = _numeric_columns(rows, excluded={time_col, group_col})
    report["time_column"] = time_col
    report["primary_group_column"] = group_col
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
    for c in numeric_cols:
        vals = [_safe_float(r.get(c)) for r in rows[: min(200, len(rows))]]
        vals = [v for v in vals if v is not None]
        if len(vals) < 5:
            continue
        try:
            drift_ratio = abs(vals[-1] - vals[0]) / (abs(baselines[c]) + 1e-9)
        except Exception:
            drift_ratio = 0
        if drift_ratio < 0.02:
            continue
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

    if group_col:
        groups = _product_groups(rows, group_col)
        report["grouping_summary"] = {
            "group_column": group_col,
            "n_groups": len(groups),
            "groups": {
                g: {
                    "rows": len(gr),
                    "start_time": gr[0][1].get(time_col) if time_col else None,
                    "end_time": gr[-1][1].get(time_col) if time_col else None
                }
                for g, gr in list(groups.items())[:50]
            }
        }

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
    time_col = _detect_time_col(list(rows[0].keys()))
    group_col = _detect_group_col(list(rows[0].keys()), args.group_col)
    numeric_cols = _numeric_columns(rows, excluded={time_col, group_col})
    explicit_targets = [c for c in (args.target_cols.split(',') if args.target_cols else []) if c in numeric_cols]
    explicit_process = [c for c in (args.process_cols.split(',') if args.process_cols else []) if c in numeric_cols]
    data_view_mode = args.data_view_mode
    if data_view_mode == 'process_only':
        target_cols = []
        process_cols = explicit_process or numeric_cols
    else:
        target_cols = explicit_targets or _choose_target_cols(rows, numeric_cols)
        process_cols = explicit_process or _choose_process_cols(numeric_cols, target_cols)

    report = {
        "targets": {},
        "transition_events": [],
        "process_parameter_fluctuation": {},
        "dual_drive_analysis": {
            "data_view_mode": data_view_mode,
            "group_column": group_col,
            "time_column": time_col,
            "per_product_analysis": {},
            "cross_domain_links": [],
            "summary": ""
        },
        "summary": {}
    }

    for target in target_cols:
        try:
            vals = [float(r[target]) for r in rows]
        except: continue
        rmean = [mean(seg) for seg in _rolling_window(vals, window)]
        rstd = []
        for seg in _rolling_window(vals, window):
            try:
                rstd.append(stdev(seg) if len(seg) >= 2 else 0)
            except Exception:
                rstd.append(0)

        anomalies = []
        in_anomaly = False; cur = None
        for i in range(len(vals)):
            if rstd[i] == 0: continue
            z = abs(vals[i] - rmean[i]) / rstd[i]
            if z > 2.0:
                if not in_anomaly:
                    cur = {"start_index": i, "end_index": i, "max_deviation_sigma": round(z, 3)}
                    in_anomaly = True
                else:
                    cur["end_index"] = i
                    cur["max_deviation_sigma"] = max(cur["max_deviation_sigma"], round(z, 3))
            else:
                if in_anomaly and cur and cur["end_index"] - cur["start_index"] >= 3:
                    cur["severity"] = "critical" if cur["max_deviation_sigma"] > 4.5 else ("high" if cur["max_deviation_sigma"] > 3.5 else "medium")
                    anomalies.append(cur)
                in_anomaly = False; cur = None

        threshold = mean(vals) + 2*stdev(vals) if len(vals) >= 2 else mean(vals)
        crossing_index = next((i for i, v in enumerate(vals) if v > threshold), None)
        report["targets"][target] = {
            "anomaly_intervals": anomalies,
            "threshold_analysis": {
                "critical_threshold": round(threshold, 2),
                "threshold_crossing_index": crossing_index,
                "percent_above_threshold": round(sum(1 for v in vals if v > threshold)/len(vals)*100, 1)
            }
        }

    if group_col:
        last = None
        for idx, row in enumerate(rows):
            current = str(row.get(group_col, '')).strip()
            if idx == 0:
                last = current
                continue
            if current and current != last:
                event = {
                    "index": idx,
                    "type": "product_change",
                    "column": group_col,
                    "from": last,
                    "to": current,
                    "quality_before": {},
                    "quality_after": {}
                }
                for target in target_cols[:5]:
                    before_vals = [_safe_float(rows[j].get(target)) for j in range(max(0, idx - 10), idx)]
                    after_vals = [_safe_float(rows[j].get(target)) for j in range(idx, min(len(rows), idx + 10))]
                    before_vals = [v for v in before_vals if v is not None]
                    after_vals = [v for v in after_vals if v is not None]
                    if before_vals:
                        event["quality_before"][target] = round(mean(before_vals), 4)
                    if after_vals:
                        event["quality_after"][target] = round(mean(after_vals), 4)
                sigma_jumps = []
                for target in target_cols[:5]:
                    before = event["quality_before"].get(target)
                    after = event["quality_after"].get(target)
                    if before is not None and after is not None:
                        vals = [_safe_float(r.get(target)) for r in rows if _safe_float(r.get(target)) is not None]
                        if len(vals) >= 2:
                            try:
                                sigma = abs(after - before) / (stdev(vals) or 1.0)
                                sigma_jumps.append(sigma)
                            except Exception:
                                pass
                if sigma_jumps:
                    event["quality_jump_sigma"] = round(max(sigma_jumps), 3)
                report["transition_events"].append(event)
                last = current

    for col in process_cols[:20]:
        vals = [_safe_float(r.get(col)) for r in rows]
        vals = [v for v in vals if v is not None]
        if len(vals) < 3:
            continue
        try:
            col_std = stdev(vals)
        except Exception:
            col_std = 0
        col_mean = mean(vals) if vals else 0
        cv = abs(col_std / col_mean) if col_mean not in (0, None) else None
        p95 = sorted(vals)[int(0.95 * (len(vals) - 1))]
        p05 = sorted(vals)[int(0.05 * (len(vals) - 1))]
        report["process_parameter_fluctuation"][col] = {
            "mean": round(col_mean, 4),
            "std": round(col_std, 4),
            "cv": round(cv, 4) if cv is not None else None,
            "p05_p95_span": round(p95 - p05, 4),
            "abrupt_behavior": "yes" if cv is not None and cv > 0.15 else "no"
        }

    if group_col:
        groups = _product_groups(rows, group_col)
        for group_name, group_rows in list(groups.items())[:100]:
            only_rows = [r for _, r in group_rows]
            product_targets = {}
            product_process = {}
            for target in target_cols[:6]:
                vals = [_safe_float(r.get(target)) for r in only_rows]
                vals = [v for v in vals if v is not None]
                if not vals:
                    continue
                product_targets[target] = {
                    "mean": round(mean(vals), 4),
                    "max": round(max(vals), 4),
                    "min": round(min(vals), 4),
                    "n": len(vals)
                }
            for col in process_cols[:8]:
                vals = [_safe_float(r.get(col)) for r in only_rows]
                vals = [v for v in vals if v is not None]
                if len(vals) < 2:
                    continue
                try:
                    sd = stdev(vals)
                except Exception:
                    sd = 0
                mv = mean(vals)
                product_process[col] = {
                    "mean": round(mv, 4),
                    "std": round(sd, 4),
                    "cv": round(abs(sd / mv), 4) if mv not in (0, None) else None,
                    "large_fluctuation": bool(mv not in (0, None) and abs(sd / mv) > 0.12)
                }
            link_candidates = []
            for target in target_cols[:4]:
                target_anomaly_count = len(report["targets"].get(target, {}).get("anomaly_intervals", []))
                for col in process_cols[:6]:
                    pp = product_process.get(col)
                    if pp and pp.get("large_fluctuation") and target_anomaly_count > 0:
                        link_candidates.append({
                            "process_parameter": col,
                            "inspection_target": target,
                            "reason": "process volatility and inspection anomaly coexist in same product group",
                            "diagnostic_weight": "strong" if target_anomaly_count >= 2 else "moderate"
                        })
            report["dual_drive_analysis"]["per_product_analysis"][group_name] = {
                "rows": len(only_rows),
                "process_parameter_summary": product_process,
                "inspection_target_summary": product_targets,
                "integrated_findings": link_candidates[:10]
            }
            for finding in link_candidates[:4]:
                report["dual_drive_analysis"]["cross_domain_links"].append({
                    "group": group_name,
                    **finding
                })

    if data_view_mode == 'process_only' or not target_cols:
        report["dual_drive_analysis"]["summary"] = (
            "当前按process_only模式处理：已分析工艺参数波动、漂移、分组波动和切换候选；"
            "由于缺少真实检测/质量目标，不声明工艺-质量因果联动。"
        )
    else:
        report["dual_drive_analysis"]["summary"] = (
            f"按{group_col or '无产品分组'}执行了工艺参数波动与检测指标异常的联合分析；"
            f"识别到{len(report['dual_drive_analysis']['cross_domain_links'])}条工艺-检测联动线索。"
        )
    report["summary"] = {
        "data_view_mode": data_view_mode,
        "anomaly_intervals": sum(len(v["anomaly_intervals"]) for v in report["targets"].values()),
        "total_transitions": len(report["transition_events"]),
        "process_parameters_screened": len(report["process_parameter_fluctuation"]),
        "integrated_links": len(report["dual_drive_analysis"]["cross_domain_links"])
    }
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
    time_col = _detect_time_col(list(rows[0].keys()))
    group_col = _detect_group_col(list(rows[0].keys()), args.group_col)
    numeric_cols = _numeric_columns(rows, excluded={time_col, group_col})
    data_view_mode = args.data_view_mode or anomaly.get("summary", {}).get("data_view_mode") or anomaly.get("dual_drive_analysis", {}).get("data_view_mode") or "unknown"
    targets = [] if data_view_mode == 'process_only' else (args.target_cols.split(',') if args.target_cols else _choose_target_cols(rows, numeric_cols))
    key_params = args.key_params.split(',') if args.key_params else _choose_process_cols(numeric_cols, targets)
    is_process_only = data_view_mode == 'process_only' or not targets

    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        indices = list(range(len(rows)))
        if time_col:
            x_values = [r.get(time_col) for r in rows]
            x_label = time_col
        else:
            x_values = indices
            x_label = 'row_index'

        # Fig 1: Temporal alignment — grouped by product and ordered by time if available
        if time_col:
            fig, axes = plt.subplots(min(4, 1 + len(targets[:3])), 1, figsize=(14, 10), sharex=True)
            if not hasattr(axes, '__len__'):
                axes = [axes]

            ax = axes[0]
            if key_params and key_params[0] in rows[0]:
                vals = [_safe_float(r.get(key_params[0])) for r in rows]
                ax.plot(x_values, vals, 'tab:red', lw=0.8, label=key_params[0])
                ax.set_ylabel(key_params[0])
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
            ax.set_title('Process Health Timeline' if is_process_only else 'Temporal Alignment — Parameter vs Quality Targets')

            for i, target in enumerate(targets[:3]):
                ax = axes[i + 1]
                if target in rows[0]:
                    vals = [_safe_float(r.get(target)) for r in rows]
                    ax.plot(x_values, vals, f'C{i}', lw=0.8, label=target)
                    ax.set_ylabel(target)
                    ax.legend(fontsize=8)
                    ax.grid(True, alpha=0.3)
            axes[-1].set_xlabel(x_label)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'fig1_temporal_alignment.png'), dpi=100)
            plt.close()
            plot_records.append({
                "filename": "fig1_temporal_alignment.png",
                "file": "fig1_temporal_alignment.png",
                "title": "工艺健康时序趋势" if is_process_only else "参数-质量时序对齐",
                "plot_type": "process_health_timeline" if is_process_only else "param_defect_aligned",
                "description": "按时间顺序观察关键工艺参数漂移、波动和切换行为，不声明质量因果联动" if is_process_only else "按时间顺序叠加工艺参数与检测指标，观察是否存在参数先变、缺陷后变的时序关系"
            })

        # Process-only adaptive view: normalized multi-parameter drift + rolling volatility.
        if is_process_only and key_params:
            fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
            for col in key_params:
                if col not in rows[0]:
                    continue
                vals = [_safe_float(r.get(col)) for r in rows]
                valid = [v for v in vals if v is not None]
                if len(valid) < 3:
                    continue
                mv = mean(valid)
                try:
                    sd = stdev(valid) or 1.0
                except Exception:
                    sd = 1.0
                z_vals = [((v - mv) / sd) if v is not None else None for v in vals]
                axes[0].plot(x_values, z_vals, lw=0.85, label=col)

                roll = []
                window = max(5, len(vals) // 20)
                for i in range(len(vals)):
                    seg = [v for v in vals[max(0, i - window + 1):i + 1] if v is not None]
                    if len(seg) >= 2:
                        try:
                            roll.append(stdev(seg))
                        except Exception:
                            roll.append(None)
                    else:
                        roll.append(None)
                axes[1].plot(x_values, roll, lw=0.8, label=col)

            axes[0].axhline(0, color='black', lw=0.5, alpha=0.4)
            axes[0].set_ylabel('Normalized deviation (z)')
            axes[0].set_title('Process-only Adaptive View — Normalized Drift')
            axes[0].grid(True, alpha=0.25)
            axes[0].legend(fontsize=7, ncol=3)
            axes[1].set_ylabel('Rolling volatility')
            axes[1].set_xlabel(x_label)
            axes[1].set_title('Rolling Volatility / Stability')
            axes[1].grid(True, alpha=0.25)
            axes[1].legend(fontsize=7, ncol=3)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'fig2_process_only_health.png'), dpi=110)
            plt.close()
            plot_records.append({
                "filename": "fig2_process_only_health.png",
                "file": "fig2_process_only_health.png",
                "title": "Process-only Health and Stability",
                "plot_type": "process_health_stability",
                "description": "仅基于工艺数据展示多参数归一化漂移和滚动波动，用于识别工艺健康、稳定性和潜在工况切换"
            })

        # Fig 2: Scatter — first key param vs first target
        if key_params and targets and key_params[0] in rows[0] and targets[0] in rows[0]:
            fig, ax = plt.subplots(figsize=(8, 6))
            xv = [_safe_float(r.get(key_params[0])) for r in rows]
            yv = [_safe_float(r.get(targets[0])) for r in rows]
            xv_yv = [(x, y) for x, y in zip(xv, yv) if x is not None and y is not None]
            xv = [x for x, _ in xv_yv]
            yv = [y for _, y in xv_yv]
            if group_col and group_col in rows[0]:
                groups = sorted(set(str(r.get(group_col, '')) for r in rows if str(r.get(group_col, '')).strip()))
                for grp in groups[:8]:
                    gx = []
                    gy = []
                    for r in rows:
                        if str(r.get(group_col, '')).strip() == grp:
                            x = _safe_float(r.get(key_params[0]))
                            y = _safe_float(r.get(targets[0]))
                            if x is not None and y is not None:
                                gx.append(x); gy.append(y)
                    if gx:
                        ax.scatter(gx, gy, s=6, alpha=0.45, label=grp)
                ax.legend(fontsize=7)
            else:
                ax.scatter(xv, yv, s=3, alpha=0.5)
            ax.set_xlabel(key_params[0])
            ax.set_ylabel(targets[0])
            ax.set_title(f'{key_params[0]} vs {targets[0]}')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'fig2_key_scatter.png'), dpi=100)
            plt.close()
            plot_records.append({
                "filename": "fig2_key_scatter.png",
                "file": "fig2_key_scatter.png",
                "title": f"{key_params[0]} vs {targets[0]}",
                "plot_type": "product_defect_scatter" if group_col else "scatter_plot",
                "description": "按产品分组查看工艺参数与检测指标关系，区分组间伪相关与组内真实关联"
            })

        # Fig 3: Per-product grouped timeline
        if group_col and time_col and targets:
            groups = _product_groups(rows, group_col)
            groups = {g: r for g, r in groups.items() if r}
            if groups:
                n_panels = min(6, len(groups))
                fig, axes = plt.subplots(n_panels, 1, figsize=(16, 3.2 * n_panels), sharex=False)
                if not hasattr(axes, '__len__'):
                    axes = [axes]
                for ax, (grp, grp_rows) in zip(axes, list(groups.items())[:n_panels]):
                    gx = [r.get(time_col) for _, r in grp_rows]
                    for target in targets[:2]:
                        gy = [_safe_float(r.get(target)) for _, r in grp_rows]
                        ax.plot(gx, gy, lw=0.9, label=target)
                    for param in key_params:
                        gy = [_safe_float(r.get(param)) for _, r in grp_rows]
                        ax.plot(gx, gy, lw=0.8, linestyle='--', alpha=0.8, label=param)
                    ax.set_title(f'{group_col}={grp}')
                    ax.grid(True, alpha=0.25)
                    ax.legend(fontsize=7, ncol=4)
                axes[-1].set_xlabel(time_col)
                plt.tight_layout()
                plt.savefig(os.path.join(args.output_dir, 'fig3_product_grouped_timeline.png'), dpi=110)
                plt.close()
                plot_records.append({
                    "filename": "fig3_product_grouped_timeline.png",
                    "file": "fig3_product_grouped_timeline.png",
                    "title": "Product Grouped Timeline",
                    "plot_type": "product_timeseries",
                    "description": "按产品号分组并按时间排序，联合展示检测指标与关键工艺参数，观察每个产品内部是否存在同步异常"
                })

        # Fig 4: Process fluctuation severity by product
        if group_col:
            groups = _product_groups(rows, group_col)
            process_candidates = key_params
            if groups and process_candidates:
                fig, ax = plt.subplots(figsize=(12, 6))
                group_names = []
                bars = []
                for grp, grp_rows in list(groups.items())[:12]:
                    only_rows = [r for _, r in grp_rows]
                    cvs = []
                    for col in process_candidates:
                        vals = [_safe_float(r.get(col)) for r in only_rows]
                        vals = [v for v in vals if v is not None]
                        if len(vals) >= 2:
                            try:
                                sd = stdev(vals)
                                mv = mean(vals)
                                if mv not in (0, None):
                                    cvs.append(abs(sd / mv))
                            except Exception:
                                pass
                    if cvs:
                        group_names.append(grp)
                        bars.append(mean(cvs))
                if bars:
                    ax.bar(group_names, bars, color='tab:orange')
                    ax.set_ylabel('Average CV')
                    ax.set_title('Process Parameter Fluctuation by Product Group')
                    ax.tick_params(axis='x', rotation=35)
                    ax.grid(True, alpha=0.25, axis='y')
                    plt.tight_layout()
                    plt.savefig(os.path.join(args.output_dir, 'fig4_process_fluctuation_by_product.png'), dpi=110)
                    plt.close()
                    plot_records.append({
                        "filename": "fig4_process_fluctuation_by_product.png",
                        "file": "fig4_process_fluctuation_by_product.png",
                        "title": "Process Fluctuation by Product",
                        "plot_type": "cross_product_consistency",
                        "description": "比较不同产品组内关键工艺参数波动程度，识别是否存在产品特异的大幅度波动异常"
                    })

        # Fig 5: Causal evidence map (simple text-based)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
        ax.set_title('Causal Evidence Map', fontsize=12, fontweight='bold')
        plt.savefig(os.path.join(args.output_dir, 'fig6_causal_evidence_map.png'), dpi=100)
        plt.close()
        plot_records.append({
            "filename": "fig6_causal_evidence_map.png",
            "file": "fig6_causal_evidence_map.png",
            "title": "Causal Evidence Map",
            "plot_type": "physical_cascade",
            "description": "汇总工艺参数波动、检测指标异常与潜在因果传递链，作为双驱动诊断的结构化入口"
        })

    except ImportError:
        print("matplotlib not available — skipping visualizations")

    manifest = {"generated_at": "auto", "total_plots": len(plot_records), "plots": plot_records}
    with open(os.path.join(args.output_dir, "plot_manifest.json"), 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    captions = {p["file"]: {"title": p["title"], "key_observations": [], "diagnostic_implication": ""} for p in plot_records}
    with open(os.path.join(args.output_dir, "image_captions.json"), 'w') as f:
        json.dump(captions, f, indent=2, ensure_ascii=False)
    print(f"Visualizations: {len(plot_records)} plots → {args.output_dir}")


# ── REGIME FILTER (v6.5 MANDATORY) ──
def cmd_regime_filter(args):
    """Invoke production_regime_detector.py and return results.

    This filters out startup/shutdown/abnormal periods so downstream analysis
    only sees steady-state data. When a product grouping column exists, it
    also computes per-product anomaly rates and identifies the focus product
    for mandatory within-product analysis.
    """
    import subprocess, sys as _sys

    detector_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'production_regime_detector.py'
    )
    if not os.path.exists(detector_script):
        # If not found in same directory, try running it from the same working env
        # as a sibling script
        detector_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', '.omp', 'skills', 'industrial-data-processor',
            'scripts', 'production_regime_detector.py'
        )

    cmd = [
        _sys.executable, detector_script,
        args.data_csv, args.output_dir,
        '--variance-threshold', str(args.variance_threshold),
        '--min-steady-ratio', str(args.min_steady_ratio),
    ]
    if args.group_col:
        cmd += ['--group-col', args.group_col]
    if args.time_col:
        cmd += ['--time-col', args.time_col]
    if args.window_minutes:
        cmd += ['--window-minutes', str(args.window_minutes)]

    print(f"[regime-filter] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=_sys.stderr)
    if result.returncode != 0:
        print(f"[regime-filter] WARNING: production_regime_detector exited with code {result.returncode}", file=_sys.stderr)
        # Non-fatal — downstream analysis can still proceed without filtering

    # Read the output for pipeline integration
    out_path = os.path.join(args.output_dir, 'production_regime_filter.json')
    if os.path.exists(out_path):
        with open(out_path) as f:
            regime_data = json.load(f)
        steady_rows = regime_data.get('steady_row_indices', [])
        steady_ratio = regime_data.get('steady_state_ratio', 0)
        print(f"[regime-filter] Steady-state: {len(steady_rows)}/{regime_data.get('total_rows', '?')} rows ({steady_ratio:.1%})")

        # Per-product focus
        per_prod = regime_data.get('per_product_anomaly_analysis', {})
        if per_prod.get('applicable') and per_prod.get('focus_product'):
            print(f"[regime-filter] Focus product: '{per_prod['focus_product']}' "
                  f"(anomaly score: {per_prod.get('focus_product_stats', {}).get('overall_anomaly_score', 'N/A')}")
            print(f"[regime-filter] MANDATORY: per-product within-time-window analysis required for '{per_prod['focus_product']}'")
    else:
        print("[regime-filter] WARNING: production_regime_filter.json not produced", file=_sys.stderr)


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
    p2.add_argument('--group-col', default=None)
    p2.add_argument('--target-cols', default='')
    p2.add_argument('--process-cols', default='')
    p2.add_argument('--data-view-mode', choices=['process_plus_inspection', 'process_only', 'inspection_only', 'unknown'], default='unknown')

    p3 = sub.add_parser('visualize')
    p3.add_argument('data_json')
    p3.add_argument('feature_summary')
    p3.add_argument('anomaly_report')
    p3.add_argument('output_dir')
    p3.add_argument('--target-cols', default='')
    p3.add_argument('--key-params', default='')
    p3.add_argument('--group-col', default=None)
    p3.add_argument('--data-view-mode', choices=['process_plus_inspection', 'process_only', 'inspection_only', 'unknown'], default='unknown')

    # v6.5 NEW: Production regime filter
    p4 = sub.add_parser('regime-filter')
    p4.add_argument('data_csv')
    p4.add_argument('output_dir')
    p4.add_argument('--group-col', default=None)
    p4.add_argument('--time-col', default=None)
    p4.add_argument('--window-minutes', type=float, default=10)
    p4.add_argument('--variance-threshold', type=float, default=3.0)
    p4.add_argument('--min-steady-ratio', type=float, default=0.4)

    a = parser.parse_args()
    {'preprocess': cmd_preprocess, 'anomaly': cmd_anomaly, 'visualize': cmd_visualize, 'regime-filter': cmd_regime_filter}[a.command](a)
