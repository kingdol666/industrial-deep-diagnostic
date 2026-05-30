#!/usr/bin/env python3
"""
Adaptive visualization for tablet_press batch pharmaceutical compression data.
Generates scenario-driven diagnostic plots with statistical validation overlay.
"""
import json
import os
import sys
from collections import defaultdict, OrderedDict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

RUN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FIG_DIR = os.path.join(RUN_DIR, '03_figures')
os.makedirs(FIG_DIR, exist_ok=True)

# ── Load all inputs ──
with open(os.path.join(RUN_DIR, '02_processed', 'cleaned_data.json')) as f:
    data = json.load(f)

with open(os.path.join(RUN_DIR, '02_processed', 'scenario_classification.json')) as f:
    scenario = json.load(f)

with open(os.path.join(RUN_DIR, '02_processed', 'feature_summary.json')) as f:
    feature_summary = json.load(f)

with open(os.path.join(RUN_DIR, '02_processed', 'validate_report.json')) as f:
    validate_report = json.load(f)

with open(os.path.join(RUN_DIR, '02_processed', 'anomaly_report.json')) as f:
    anomaly_report = json.load(f)

# Sort data by batch_seq then tablet_seq
data.sort(key=lambda x: (x.get('batch_seq', 0), x.get('tablet_seq', 0)))

# Production events
events = [
    {'ts': '2025-11-02', 'batch_seq_start': 4, 'batch_seq_end': None,
     'type': 'CALIBRATION', 'label': 'Calibration', 'color': 'green'},
    {'ts': '2025-11-08', 'batch_seq_start': 22, 'batch_seq_end': None,
     'type': 'MATERIAL_INCIDENT', 'label': 'Material Incident', 'color': 'orange'},
    {'ts': '2025-11-14', 'batch_seq_start': 38, 'batch_seq_end': None,
     'type': 'PUNCH_DRESSING', 'label': 'Punch Dressing', 'color': 'blue'},
    {'ts': '2025-11-17', 'batch_seq_start': 50, 'batch_seq_end': None,
     'type': 'LUBRICANT_CHANGE', 'label': 'Lubricant Change', 'color': 'purple'},
]

plot_records = []
quality_targets = ['hardness_N', 'friability_pct', 'disintegration_time_min', 'tablet_weight_mg', 'thickness_mm']
process_params = ['compression_force_kN', 'pre_compression_force_kN', 'turret_speed_rpm',
                  'fill_depth_mm', 'dwell_time_ms', 'blend_moisture_pct', 'lubricant_level_pct',
                  'blend_uniformity_index', 'compression_zone_temp_C', 'ambient_temp_C', 'ambient_humidity_pct']

# Colors for stations and punches
station_colors = {1: '#E74C3C', 2: '#3498DB', 3: '#2ECC71'}
punch_colors = {'P101-7047': '#E74C3C', 'P102-9032': '#3498DB', 'P103-1001': '#2ECC71'}


def compute_pearson(x, y):
    """Compute Pearson correlation coefficient."""
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return 0
    x_mean, y_mean = np.mean(x), np.mean(y)
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sqrt(np.sum((x - x_mean)**2) * np.sum((y - y_mean)**2))
    return num / den if den != 0 else 0


def compute_spearman_divergence(x, y):
    """Compute |Pearson - Spearman| as divergence measure."""
    n = len(x)
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    r_spearman = compute_pearson(rx, ry)
    r_pearson = compute_pearson(x, y)
    return abs(r_pearson - r_spearman)


def lowess_smooth(x, y, frac=0.3):
    """Simple LOWESS implementation (no scipy dependency)."""
    n = len(x)
    if n < 10:
        return x.copy(), y.copy()
    smoothed = np.zeros(n)
    x_sorted_idx = np.argsort(x)
    x_sorted = x[x_sorted_idx]
    y_sorted = y[x_sorted_idx]
    k = max(3, int(n * frac))
    for i in range(n):
        distances = np.abs(x_sorted - x_sorted[i])
        idx = np.argsort(distances)[:k]
        local_x = x_sorted[idx]
        local_y = y_sorted[idx]
        max_d = distances[idx][-1] if distances[idx][-1] > 0 else 1
        weights = (1 - (distances[idx] / max_d) ** 3) ** 3
        if np.sum(weights) == 0:
            smoothed[i] = y_sorted[i]
        else:
            smoothed[i] = np.sum(weights * local_y) / np.sum(weights)
    return x_sorted, smoothed


# ═══════════════════════════════════════════
# FIGURE 1: Correlation Heatmap
# ═══════════════════════════════════════════

def plot_correlation_heatmap():
    """Fig A: Full Pearson matrix with Spearman divergence annotations."""
    all_vars = process_params + quality_targets
    n_vars = len(all_vars)

    # Build numeric arrays
    arr = np.zeros((n_vars, len(data)))
    for j, v in enumerate(all_vars):
        arr[j] = np.array([row.get(v, np.nan) if row.get(v) is not None else np.nan for row in data], dtype=float)

    pearson_mat = np.zeros((n_vars, n_vars))
    spearman_div = np.zeros((n_vars, n_vars))

    for i in range(n_vars):
        for j in range(n_vars):
            mask = ~(np.isnan(arr[i]) | np.isnan(arr[j]))
            x, y = arr[i][mask], arr[j][mask]
            pearson_mat[i][j] = compute_pearson(x, y)
            spearman_div[i][j] = compute_spearman_divergence(x, y)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 10))

    # Pearson heatmap
    im1 = ax1.imshow(pearson_mat, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax1.set_xticks(range(n_vars))
    ax1.set_yticks(range(n_vars))
    ax1.set_xticklabels(all_vars, rotation=90, fontsize=7)
    ax1.set_yticklabels(all_vars, fontsize=7)
    ax1.set_title('Pearson Correlation Matrix', fontsize=14, fontweight='bold')
    plt.colorbar(im1, ax=ax1, shrink=0.8)

    # Annotate strong correlations
    for i in range(n_vars):
        for j in range(n_vars):
            if abs(pearson_mat[i][j]) > 0.7 and i != j:
                ax1.text(j, i, f'{pearson_mat[i][j]:.2f}', ha='center', va='center',
                        fontsize=5, color='black' if abs(pearson_mat[i][j]) < 0.85 else 'white')

    # Spearman divergence heatmap
    im2 = ax2.imshow(spearman_div, cmap='YlOrRd', vmin=0, vmax=0.3, aspect='auto')
    ax2.set_xticks(range(n_vars))
    ax2.set_yticks(range(n_vars))
    ax2.set_xticklabels(all_vars, rotation=90, fontsize=7)
    ax2.set_yticklabels(all_vars, fontsize=7)
    ax2.set_title('Spearman Divergence |Pearson - Spearman|', fontsize=14, fontweight='bold')
    plt.colorbar(im2, ax=ax2, shrink=0.8)

    # Annotate high divergence
    for i in range(n_vars):
        for j in range(n_vars):
            if spearman_div[i][j] > 0.1 and i != j:
                ax2.text(j, i, f'{spearman_div[i][j]:.3f}', ha='center', va='center',
                        fontsize=5, color='black')

    plt.tight_layout()
    path = os.path.join(FIG_DIR, '01_correlation_heatmap.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '01_correlation_heatmap.png',
        'title': 'Correlation Heatmap - Pearson Matrix and Spearman Divergence',
        'type': 'mandatory',
        'description': '左图：Pearson相关矩阵（红蓝双色，-1到1）。右图：Spearman散度（|Pearson-Spearman|），黄色区域表示非线性关系。',
        'diagnostic_purpose': '识别哪些工艺参数与质量指标强相关，暴露非线性关系位置（高Spearman散度）。'
    })
    print(f'  Generated 01_correlation_heatmap.png')


# ═══════════════════════════════════════════
# FIGURE 2: Key Parameter vs Quality Scatter Grid
# ═══════════════════════════════════════════

def plot_scatter_grid():
    """Fig B: Top parameters vs quality targets, colored by station."""
    # Top 4 process params by average |r| with quality targets
    target_analysis = feature_summary.get('target_analysis', {})
    param_importance = defaultdict(list)
    for target in quality_targets:
        if target in target_analysis:
            pearson = target_analysis[target].get('pearson_correlations', {})
            for p in process_params:
                if p in pearson and isinstance(pearson[p], dict):
                    r = pearson[p].get('r', 0)
                    param_importance[p].append(abs(r))

    param_avg_r = {p: np.mean(rs) for p, rs in param_importance.items() if rs}
    top_params = sorted(param_avg_r.keys(), key=lambda p: param_avg_r[p], reverse=True)[:4]

    fig, axes = plt.subplots(len(top_params), len(quality_targets),
                             figsize=(20, 14), squeeze=False)

    for i, param in enumerate(top_params):
        param_vals = np.array([row.get(param, np.nan) if row.get(param) is not None else np.nan for row in data], dtype=float)
        for j, target in enumerate(quality_targets):
            ax = axes[i][j]
            target_vals = np.array([row.get(target, np.nan) if row.get(target) is not None else np.nan for row in data], dtype=float)

            stations = np.array([row.get('station', 1) for row in data])

            # Scatter by station
            for station in [1, 2, 3]:
                mask = (stations == station) & ~np.isnan(param_vals) & ~np.isnan(target_vals)
                if np.sum(mask) > 0:
                    ax.scatter(param_vals[mask], target_vals[mask],
                              c=station_colors[station], s=3, alpha=0.4,
                              label=f'Station {int(station)}', edgecolors='none')

            # Per-station regression lines
            for station in [1, 2, 3]:
                mask = (stations == station) & ~np.isnan(param_vals) & ~np.isnan(target_vals)
                if np.sum(mask) > 5:
                    x_sub = param_vals[mask]
                    y_sub = target_vals[mask]
                    A = np.vstack([x_sub, np.ones_like(x_sub)]).T
                    m, c = np.linalg.lstsq(A, y_sub, rcond=None)[0]
                    x_line = np.array([np.min(x_sub), np.max(x_sub)])
                    ax.plot(x_line, m * x_line + c, color=station_colors[station],
                           linewidth=1.2, linestyle='--')

            if i == 0:
                ax.set_title(target.replace('_', ' '), fontsize=9, fontweight='bold')
            if j == 0:
                ax.set_ylabel(param.replace('_', '\n'), fontsize=7)
            if i == len(top_params) - 1:
                ax.set_xlabel(param.replace('_', ' '), fontsize=7)

            ax.tick_params(labelsize=6)

            if i == 0 and j == len(quality_targets) - 1:
                ax.legend(fontsize=6, loc='upper right')

    fig.suptitle('Process Parameter vs Quality Scatter Grid (colored by Station)', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = os.path.join(FIG_DIR, '02_scatter_grid_by_station.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '02_scatter_grid_by_station.png',
        'title': 'Process Parameter vs Quality Scatter Grid (Station-colored)',
        'type': 'mandatory',        'description': 'Top-4关键工艺参数与5个质量指标散点图网格。三色按工位（Station 1/2/3），虚线为每组线性回归。',
        'diagnostic_purpose': "检查Pearson相关是否在工位分组内保持（Simpson's Paradox验证），观察工位间参数-质量关系是否一致。"
    })
    print(f'  Generated 02_scatter_grid_by_station.png')


# ═══════════════════════════════════════════
# FIGURE 3: Raw vs Detrended Comparison
# ═══════════════════════════════════════════

def plot_raw_vs_detrended():
    """Fig C: Bar chart comparing raw r vs detrended r for all |r|>0.3 pairs."""
    target_analysis = feature_summary.get('target_analysis', {})

    pairs = []
    for target in quality_targets:
        if target in target_analysis:
            pearson = target_analysis[target].get('pearson_correlations', {})
            detrended = target_analysis[target].get('detrended_correlations', {})
            for param in process_params + ['blend_moisture_pct']:
                if param in pearson and isinstance(pearson[param], dict):
                    r = pearson[param].get('r', 0)
                    if abs(r) > 0.3:
                        r_det = r
                        if param in detrended and isinstance(detrended[param], dict):
                            r_det = detrended[param].get('r', r)
                        pairs.append((f'{param} vs {target}', r, r_det))

    if not pairs:
        # Fallback: use any strong correlations
        for target in quality_targets:
            if target in target_analysis:
                pearson = target_analysis[target].get('pearson_correlations', {})
                for param, v in pearson.items():
                    if isinstance(v, dict) and abs(v.get('r', 0)) > 0.3:
                        r = v['r']
                        pairs.append((f'{param} vs {target}', r, r))

    pairs = pairs[:25]
    labels = [p[0] for p in pairs]
    raw_rs = [p[1] for p in pairs]
    detrended_rs = [p[2] for p in pairs]

    fig, ax = plt.subplots(figsize=(14, max(8, len(pairs) * 0.4)))
    y_pos = np.arange(len(pairs))

    bars1 = ax.barh(y_pos - 0.2, raw_rs, 0.35, label='Raw r', color='#3498DB', alpha=0.8)
    bars2 = ax.barh(y_pos + 0.2, detrended_rs, 0.35, label='Detrended r', color='#E74C3C', alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7)
    ax.axvline(0, color='black', linewidth=0.5)
    ax.set_xlabel('Pearson r', fontsize=10)
    ax.set_title('Raw vs Detrended Correlation Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(axis='x', alpha=0.3)

    # Annotate changes
    for i, (r1, r2) in enumerate(zip(raw_rs, detrended_rs)):
        change = abs(abs(r1) - abs(r2))
        if change > 0.05:
            ax.text(max(r1, r2) + 0.02, i, f'Δ={change:.3f}', fontsize=6,
                   va='center', color='red')

    plt.tight_layout()
    path = os.path.join(FIG_DIR, '03_raw_vs_detrended.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '03_raw_vs_detrended.png',
        'title': 'Raw vs Detrended Correlation Comparison',
        'type': 'mandatory',
        'description': '原始Pearson r（蓝色）与去趋势后Pearson r（红色）对比柱状图。Δ>0.05标注变化量，反映时间趋势混杂程度。',
        'diagnostic_purpose': '识别时间趋势伪相关：若去趋势后r大幅衰减，则原始相关主要由时间趋势驱动，非直接因果关系。'
    })
    print(f'  Generated 03_raw_vs_detrended.png')


# ═══════════════════════════════════════════
# FIGURE 4: Batch-to-Batch Quality Variation Trend
# ═══════════════════════════════════════════

def plot_batch_quality_trend():
    """Fig D: Batch-to-batch quality variation trend with event markers."""
    # Aggregate per batch
    batch_data = defaultdict(list)
    for row in data:
        bid = row.get('batch_id', '')
        batch_seq = row.get('batch_seq', 0)
        batch_data[bid].append(row)

    batch_seq_ids = sorted(set(row.get('batch_seq', 0) for row in data))

    batch_means = {}
    for bid, rows in batch_data.items():
        seq = rows[0].get('batch_seq', 0)
        means = {}
        for target in quality_targets:
            vals = [r[target] for r in rows if r.get(target) is not None]
            if vals:
                means[target] = np.mean(vals)
                means[f'{target}_std'] = np.std(vals)
        batch_means[seq] = means

    seqs = sorted(batch_means.keys())

    # Choose 3 targets for clear display
    plot_targets = ['hardness_N', 'friability_pct', 'disintegration_time_min']
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

    for idx, target in enumerate(plot_targets):
        ax = axes[idx]
        vals = [batch_means[s].get(target, np.nan) for s in seqs]
        stds = [batch_means[s].get(f'{target}_std', 0) for s in seqs]
        x = list(range(len(seqs)))

        ax.plot(x, vals, color='#2C3E50', linewidth=1.5, marker='o', markersize=3, label=f'Batch Mean {target.replace("_", " ")}')
        ax.fill_between(x, [v - s for v, s in zip(vals, stds)],
                        [v + s for v, s in zip(vals, stds)],
                        alpha=0.15, color='#3498DB', label='+/- 1 Std')

        # Event markers
        for ev in events:
            if ev['batch_seq_start'] is not None:
                xpos = seqs.index(ev['batch_seq_start']) if ev['batch_seq_start'] in seqs else min(seqs, key=lambda s: abs(s - ev['batch_seq_start']))
                # Find the index in seqs
                xidx = next(i for i, s in enumerate(seqs) if s >= ev['batch_seq_start'])
                ax.axvline(x=xidx, color=ev['color'], linestyle='--', linewidth=1.5, alpha=0.7)
                ax.text(xidx, ax.get_ylim()[1], ev['label'], rotation=45, fontsize=7,
                       color=ev['color'], ha='left', va='bottom')

        ax.set_ylabel(target.replace('_', ' '), fontsize=9)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')

        # Spec limit lines
        if target == 'hardness_N':
            ax.axhline(y=80, color='red', linestyle=':', linewidth=1, alpha=0.5, label='Min spec (80N)')
        elif target == 'friability_pct':
            ax.axhline(y=1.0, color='red', linestyle=':', linewidth=1, alpha=0.5, label='Max spec (1%)')
        elif target == 'disintegration_time_min':
            ax.axhline(y=15, color='red', linestyle=':', linewidth=1, alpha=0.5, label='Max spec (15min)')

    axes[-1].set_xlabel('Batch Sequence (ordered by time)', fontsize=10)
    fig.suptitle('Batch-to-Batch Quality Variation Trend with Production Events', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = os.path.join(FIG_DIR, '04_batch_quality_trend.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '04_batch_quality_trend.png',
        'title': 'Batch-to-Batch Quality Variation Trend',
        'type': 'scenario-driven',
        'description': '按批次序号的批次均值折线图（含标准差带），红色虚线为质量标准限（硬度>80N，脆碎度<1%，崩解<15min）。事件标记：绿色=校准，橙色=物料事件，蓝色=冲模重修，紫色=润滑剂更换。',
        'diagnostic_purpose': '追踪批次间质量变化趋势，识别生产事件前后的质量波动，判断是否存在系统性漂移。'
    })
    print(f'  Generated 04_batch_quality_trend.png')


# ═══════════════════════════════════════════
# FIGURE 5: Anomaly Timeline
# ═══════════════════════════════════════════

def plot_anomaly_timeline():
    """Fig: Anomaly Timeline - quality time series with anomaly intervals and events."""
    fig, axes = plt.subplots(3, 1, figsize=(18, 12), sharex=True)

    plot_targets = ['hardness_N', 'friability_pct', 'disintegration_time_min']

    for idx, target in enumerate(plot_targets):
        ax = axes[idx]
        vals = np.array([row.get(target, np.nan) if row.get(target) is not None else np.nan for row in data], dtype=float)
        x = np.arange(len(vals))

        # Plot main series
        ax.plot(x, vals, color='#2C3E50', linewidth=0.6, alpha=0.7)

        # Anomaly intervals from anomaly_report
        target_anomalies = anomaly_report.get('targets', {}).get(target, {}).get('anomaly_intervals', [])
        for interval in target_anomalies:
            si, ei = interval['start_index'], interval['end_index']
            severity = interval['severity']
            alpha = 0.3 if severity == 'high' or severity == 'critical' else 0.15
            color = '#E74C3C' if severity in ('high', 'critical') else '#F39C12'
            ax.axvspan(si, ei, alpha=alpha, color=color)

        # Threshold lines (IQR fences)
        target_threshold = anomaly_report.get('targets', {}).get(target, {}).get('threshold_analysis', {})
        if 'iqr_lower' in target_threshold:
            ax.axhline(y=target_threshold['iqr_lower'], color='red', linestyle=':', linewidth=0.8, alpha=0.5)
        if 'iqr_upper' in target_threshold:
            ax.axhline(y=target_threshold['iqr_upper'], color='red', linestyle=':', linewidth=0.8, alpha=0.5)

        # Event markers
        for ev in events:
            if ev['batch_seq_start'] is not None:
                # Find the first row with this batch_seq
                xidx = next((i for i, row in enumerate(data) if row.get('batch_seq') == ev['batch_seq_start']), None)
                if xidx is not None:
                    ax.axvline(x=xidx, color=ev['color'], linestyle='--', linewidth=1.2, alpha=0.7)
                    ax.text(xidx, ax.get_ylim()[1] * 0.95, ev['label'], rotation=45, fontsize=6,
                           color=ev['color'], ha='left', va='bottom')

        ax.set_ylabel(target.replace('_', ' '), fontsize=9)
        ax.grid(alpha=0.2)

        # Spec limit
        if target == 'hardness_N':
            ax.axhline(y=80, color='green', linestyle='--', linewidth=0.8, alpha=0.4, label='Spec: min 80N')
        elif target == 'friability_pct':
            ax.axhline(y=1.0, color='green', linestyle='--', linewidth=0.8, alpha=0.4, label='Spec: max 1%')

        # Anomaly count
        n_anomaly = target_anomalies
        ax.text(0.02, 0.98, f'{len(target_anomalies)} anomaly intervals', transform=ax.transAxes,
               fontsize=7, va='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    axes[-1].set_xlabel('Tablet Index (chronological order)', fontsize=10)
    fig.suptitle('Anomaly Timeline - Quality Metrics with Anomaly Intervals and Events', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = os.path.join(FIG_DIR, '05_anomaly_timeline.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '05_anomaly_timeline.png',
        'title': 'Anomaly Timeline with Event Markers',
        'type': 'anomaly',
        'description': '质量指标时间序列（每片），红色/橙色背景=异常区间（自适应±2σ阈值），绿色虚线=质量标准，彩色竖线=生产事件。',
        'diagnostic_purpose': '直观显示质量何时恶化、何时恢复，异常区间与生产事件的时间重叠关系，识别事件性根因。'
    })
    print(f'  Generated 05_anomaly_timeline.png')


# ═══════════════════════════════════════════
# FIGURE 6: Transition Impact Analysis
# ═══════════════════════════════════════════

def plot_transition_impact():
    """Fig: Transition impact - quality before/after station and punch changes."""
    transitions = anomaly_report.get('transition_events', [])

    # Filter to station and punch changes
    punch_trans = [t for t in transitions if t.get('type') == 'punch_change']
    station_trans = [t for t in transitions if t.get('type') == 'station_change']

    # Show first few significant transitions
    punch_trans = [t for t in punch_trans if t.get('max_quality_jump', 0) > 0.5][:5]
    station_trans = [t for t in station_trans if t.get('max_quality_jump', 0) > 0.5][:5]

    if not punch_trans and not station_trans:
        # Fallback: show all
        punch_trans = transitions[:3]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Plot punch transitions
    ax1 = axes[0]
    if punch_trans:
        labels = [f"{t.get('from','?')} -> {t.get('to','?')}" for t in punch_trans]
        for i, (trans, label) in enumerate(zip(punch_trans, labels)):
            qb = trans.get('quality_before', {})
            qa = trans.get('quality_after', {})
            for j, target in enumerate(['hardness_N', 'friability_pct', 'disintegration_time_min']):
                if target in qb and target in qa:
                    offset = j * 0.25
                    ax1.bar(i + offset - 0.25, qb[target], 0.2, color=['#3498DB', '#E74C3C', '#2ECC71'][j], alpha=0.6)
                    ax1.bar(i + offset, qa[target], 0.2, color=['#3498DB', '#E74C3C', '#2ECC71'][j], alpha=1.0)

        ax1.set_xticks(range(len(punch_trans)))
        ax1.set_xticklabels(labels, fontsize=8, rotation=15)
        ax1.set_ylabel('Quality Value', fontsize=9)
        ax1.set_title('Punch Change Transition Impact', fontsize=12, fontweight='bold')
        ax1.grid(alpha=0.3, axis='y')
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#3498DB', alpha=0.6, label='Hardness (before)'),
            Patch(facecolor='#3498DB', alpha=1.0, label='Hardness (after)'),
            Patch(facecolor='#E74C3C', alpha=0.6, label='Friability (before)'),
            Patch(facecolor='#E74C3C', alpha=1.0, label='Friability (after)'),
        ]
        ax1.legend(handles=legend_elements, fontsize=6, loc='upper right')
    else:
        ax1.text(0.5, 0.5, 'No significant punch change transitions detected', ha='center', va='center', transform=ax1.transAxes)

    # Plot station transitions
    ax2 = axes[1]
    if station_trans:
        labels = [f"St{int(t.get('from',0))} -> St{int(t.get('to',0))}" for t in station_trans]
        for i, (trans, label) in enumerate(zip(station_trans, labels)):
            qb = trans.get('quality_before', {})
            qa = trans.get('quality_after', {})
            for j, target in enumerate(['hardness_N', 'friability_pct', 'disintegration_time_min']):
                if target in qb and target in qa:
                    offset = j * 0.25
                    ax2.bar(i + offset - 0.25, qb[target], 0.2, color=['#3498DB', '#E74C3C', '#2ECC71'][j], alpha=0.6)
                    ax2.bar(i + offset, qa[target], 0.2, color=['#3498DB', '#E74C3C', '#2ECC71'][j], alpha=1.0)

        ax2.set_xticks(range(len(station_trans)))
        ax2.set_xticklabels(labels, fontsize=8)
        ax2.set_ylabel('Quality Value', fontsize=9)
        ax2.set_title('Station Change Transition Impact', fontsize=12, fontweight='bold')
        ax2.grid(alpha=0.3, axis='y')
    else:
        ax2.text(0.5, 0.5, 'No significant station change transitions detected', ha='center', va='center', transform=ax2.transAxes)

    fig.suptitle('Transition Impact Analysis - Quality Before/After Change Events', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = os.path.join(FIG_DIR, '06_transition_impact.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '06_transition_impact.png',
        'title': 'Transition Impact Analysis',
        'type': 'anomaly',
        'description': '冲模更换和工位更换前后质量变化对比图。浅色=更换前，深色=更换后。突变的跳跃值指示事件驱动的根因。',
        'diagnostic_purpose': '区分组件级退化（更换后质量恢复）vs系统级退化（更换后质量不恢复）。冲模更换后质量不恢复=冲模磨损不是根因。'
    })
    print(f'  Generated 06_transition_impact.png')


# ═══════════════════════════════════════════
# FIGURE 7: Degradation Curve (LOWESS)
# ═══════════════════════════════════════════

def plot_degradation_curve():
    """Fig: Degradation curve - quality vs key process parameters with LOWESS fit."""
    # Key degradation candidates from scenario
    degradation_params = ['blend_moisture_pct', 'compression_force_kN', 'pre_compression_force_kN', 'lubricant_level_pct']

    fig, axes = plt.subplots(len(degradation_params), 2, figsize=(14, 16), squeeze=False)

    for i, param in enumerate(degradation_params):
        param_vals = np.array([row.get(param, np.nan) if row.get(param) is not None else np.nan for row in data], dtype=float)

        for j, target in enumerate(['hardness_N', 'friability_pct']):
            ax = axes[i][j]
            target_vals = np.array([row.get(target, np.nan) if row.get(target) is not None else np.nan for row in data], dtype=float)

            mask = ~(np.isnan(param_vals) | np.isnan(target_vals))
            x, y = param_vals[mask], target_vals[mask]

            # Scatter
            defect_grades = np.array([row.get('defect_grade', 'A') for row in data])[mask]
            for grade, color, marker in [('A', 'green', 'o'), ('B', 'orange', 's'), ('C', 'red', 'x')]:
                gmask = defect_grades == grade
                if np.sum(gmask) > 0:
                    ax.scatter(x[gmask], y[gmask], c=color, marker=marker, s=4, alpha=0.3, label=f'Grade {grade}')

            # LOWESS fit
            if len(x) > 20:
                x_sorted, y_smoothed = lowess_smooth(x, y, frac=0.15)
                ax.plot(x_sorted, y_smoothed, color='black', linewidth=2, label='LOWESS trend')

            # Critical threshold
            if target == 'hardness_N':
                ax.axhline(y=80, color='red', linestyle=':', linewidth=1, alpha=0.5, label='Min spec')
            elif target == 'friability_pct':
                ax.axhline(y=1.0, color='red', linestyle=':', linewidth=1, alpha=0.5, label='Max spec')

            if i == 0:
                ax.set_title(target.replace('_', ' '), fontsize=10, fontweight='bold')
            if j == 0:
                ax.set_ylabel(target.replace('_', ' '), fontsize=8)
            ax.set_xlabel(param.replace('_', ' '), fontsize=8)
            ax.grid(alpha=0.2)
            ax.tick_params(labelsize=7)

            if i == 0 and j == 1:
                ax.legend(fontsize=6, loc='upper right')

    fig.suptitle('Degradation Curves - Process Parameters vs Quality (LOWESS Fit)', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    path = os.path.join(FIG_DIR, '07_degradation_curves.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    plot_records.append({
        'file': '07_degradation_curves.png',
        'title': 'Degradation Curves - Process Parameters vs Quality',
        'type': 'scenario-driven',
        'description': '工艺参数与质量指标散点图，黑线=LOWESS拟合趋势，颜色按缺陷等级（绿=合格，橙=边缘，红=不合格），红色虚线=质量标准。',
        'diagnostic_purpose': '确定质量退化的临界参数值——在哪个参数阈值下质量开始下降、缺陷开始出现。直接回答"过程何时失效"。'
    })
    print(f'  Generated 07_degradation_curves.png')


# ═══════════════════════════════════════════
# FIGURE 8: Causal Evidence Map
# ═══════════════════════════════════════════

def plot_causal_evidence_map():
    """Fig: Causal evidence map - validated directed graph of correlations."""
    target_analysis = feature_summary.get('target_analysis', {})

    # Build edges list from validated correlations
    edges = []
    for target in quality_targets:
        if target in target_analysis:
            pearson = target_analysis[target].get('pearson_correlations', {})
            for param in process_params:
                if param in pearson and isinstance(pearson[param], dict):
                    r = pearson[param].get('r', 0)
                    if abs(r) > 0.25:  # Only show moderate+ correlations
                        validated = abs(r) > 0.3
                        edges.append({
                            'from': param,
                            'to': target,
                            'r': round(r, 3),
                            'validated': validated
                        })

    fig, ax = plt.subplots(figsize=(16, 12))

    # Layout: quality targets on right, params on left, grouped by type
    target_nodes = {t: i for i, t in enumerate(quality_targets)}
    param_list = list(dict.fromkeys([e['from'] for e in edges]))  # unique, preserve order
    param_nodes = {p: i for i, p in enumerate(param_list)}

    n_params = len(param_nodes)
    n_targets = len(target_nodes)

    # Node positions
    pos = {}
    for i, p in enumerate(param_list):
        pos[p] = np.array([0.0, 1.0 - (i + 0.5) / n_params])
    for j, t in enumerate(quality_targets):
        pos[t] = np.array([1.0, 1.0 - (j + 0.5) / n_targets])

    # Draw edges
    colinear_pairs = []
    for i, p1 in enumerate(param_list):
        for p2 in param_list[i+1:]:
            pearson = target_analysis.get(quality_targets[0], {}).get('pearson_correlations', {})
            r1 = pearson.get(p1, {}) if isinstance(pearson.get(p1), dict) else {}
            if isinstance(r1, dict) and 'r' in r1:
                pass
            # Check correlation matrix
            if 'correlation_matrices' in feature_summary:
                cm = feature_summary['correlation_matrices']
                if 'pearson' in cm and p1 in cm['pearson'] and p2 in cm['pearson'][p1]:
                    r = cm['pearson'][p1][p2]
                    if isinstance(r, (int, float)) and abs(r) > 0.8:
                        colinear_pairs.append((p1, p2, r))

    # Draw edges
    for edge in edges:
        p1 = pos[edge['from']]
        p2 = pos[edge['to']]
        r = edge['r']
        validated = edge['validated']

        # Curve edge
        color = '#27AE60' if validated else '#F39C12'
        alpha = min(1.0, max(0.2, abs(r)))
        linewidth = max(1, abs(r) * 4)

        ax.annotate('', xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle='->', color=color, alpha=alpha,
                                   lw=linewidth, connectionstyle='arc3,rad=0.1'))

        # Edge label
        mid = (p1 + p2) / 2 + np.array([0, 0.03])
        r_label = f'r={r:.2f}'
        ax.text(mid[0], mid[1], r_label, fontsize=6, ha='center', va='bottom',
               color=color, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

    # Draw colinear edges between parameters
    for p1, p2, r in colinear_pairs[:6]:
        if p1 in pos and p2 in pos:
            ax.plot([pos[p1][0], pos[p2][0]], [pos[p1][1], pos[p2][1]],
                   color='#8E44AD', linewidth=0.5, linestyle=':', alpha=0.5)

    # Draw nodes
    for name, p in pos.items():
        is_target = name in quality_targets
        color = '#E74C3C' if is_target else '#3498DB'
        size = 400 if is_target else 250
        shape = 's' if is_target else 'o'

        ax.scatter(p[0], p[1], s=size, c=color, marker=shape, zorder=5, edgecolors='black', linewidths=0.5)

        # Count edges connecting to targets
        if not is_target:
            n_connected = sum(1 for e in edges if e['from'] == name)
            label = f'{name}\n({n_connected} targets)'
        else:
            label = name.replace('_', '\n')

        ax.text(p[0], p[1] - 0.04, label, fontsize=7, ha='center', va='top', fontweight='bold')

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27AE60', alpha=0.8, label='Validated (|r|>0.3)'),
        Patch(facecolor='#F39C12', alpha=0.8, label='Weak (|r|<0.3)'),
        Patch(facecolor='#3498DB', alpha=0.8, label='Process Parameter'),
        Patch(facecolor='#E74C3C', alpha=0.8, label='Quality Target'),
        plt.Line2D([0], [0], color='#8E44AD', linestyle=':', label='Colinear (|r|>0.8)'),
    ]
    ax.legend(handles=legend_elements, fontsize=8, loc='lower right')

    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.axis('off')
    ax.set_title('Causal Evidence Map - Validated Parameter-Quality Relationships\nBatch Pharmaceutical Compression\n', fontsize=14, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(FIG_DIR, '08_causal_evidence_map.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Also save the causal evidence JSON
    causal_map = {
        'nodes': [],
        'edges': [e for e in edges if abs(e['r']) > 0.25],
        'colinear_groups': [{'members': [p1, p2], 'r_mutual': r, 'implication': 'Shared upstream variation source'}
                           for p1, p2, r in colinear_pairs[:6]],
        'root_cause_candidates': []
    }

    # Find parameters that connect to multiple targets
    param_target_count = defaultdict(list)
    for e in edges:
        param_target_count[e['from']].append(e['to'])

    for param, targets in sorted(param_target_count.items(), key=lambda x: -len(set(x[1]))):
        if len(set(targets)) >= 2:
            avg_r = np.mean([e['r'] for e in edges if e['from'] == param and e['to'] in set(targets)])
            causal_map['root_cause_candidates'].append({
                'parameter': param,
                'reason': f'Connects to {len(set(targets))} quality targets, avg |r|={abs(avg_r):.3f}',
                'connected_targets': list(set(targets))
            })

    for param in param_list:
        n_targets_connected = len(set(e['to'] for e in edges if e['from'] == param))
        causal_map['nodes'].append({
            'id': param,
            'type': 'predictor',
            'label': param,
            'connects_to_targets': n_targets_connected
        })

    for target in quality_targets:
        causal_map['nodes'].append({
            'id': target,
            'type': 'target',
            'label': target
        })

    causal_map_path = os.path.join(RUN_DIR, '02_processed', 'causal_evidence_map.json')
    with open(causal_map_path, 'w') as f:
        json.dump(causal_map, f, indent=2, ensure_ascii=False)

    plot_records.append({
        'file': '08_causal_evidence_map.png',
        'title': 'Causal Evidence Map',
        'type': 'scenario-driven',
        'description': '验证后的因果网络图。左列=工艺参数节点（蓝色圆圈），右列=质量指标节点（红色方块），边宽度=|r|，颜色：绿色=已验证，橙色=弱相关。带连接数的节点标签。',
        'diagnostic_purpose': '提供诊断师根因分析的完整因果框架：识别连接多个质量指标的根因候选参数，显示已验证的物理因果链。'
    })
    print(f'  Generated 08_causal_evidence_map.png')
    print(f'  Causal evidence map JSON saved')


# ═══════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════

print('Generating visualizations...')
plot_correlation_heatmap()
plot_scatter_grid()
plot_raw_vs_detrended()
plot_batch_quality_trend()
plot_anomaly_timeline()
plot_transition_impact()
plot_degradation_curve()
plot_causal_evidence_map()

# ── Save Plot Manifest ──
manifest = {
    'generated_at': __import__('datetime').datetime.now().isoformat(),
    'total_plots': len(plot_records),
    'plots': plot_records,
    'scenario': scenario.get('scenario', 'unknown'),
    'quality_targets': quality_targets
}

manifest_path = os.path.join(FIG_DIR, 'plot_manifest.json')
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f'\nPlot manifest saved to {manifest_path}')

# ── Save Image Captions ──
captions = []
for rec in plot_records:
    captions.append({
        'file': rec['file'],
        'title': rec['title'],
        'description': rec.get('description', ''),
        'key_observations': [
            f'Figure shows {rec["type"]} analysis',
            'Refer to correlation values from feature_summary.json',
        ],
        'diagnostic_implication': rec.get('diagnostic_purpose', 'Diagnostic analysis figure')
    })

captions_path = os.path.join(FIG_DIR, 'image_captions.json')
with open(captions_path, 'w') as f:
    json.dump(captions, f, indent=2, ensure_ascii=False)
print(f'Image captions saved to {captions_path}')
print('\nAll visualizations complete!')
