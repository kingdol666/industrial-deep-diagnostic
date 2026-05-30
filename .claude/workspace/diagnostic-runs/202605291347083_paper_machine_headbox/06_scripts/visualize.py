#!/usr/bin/env python3
"""
Paper Machine Headbox — Scenario-Adaptive Visualization Pipeline
Continuous Process scenario.
Generates all mandatory + scenario-specific + conditional visualizations.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import FancyBboxPatch
import json
import os
import warnings
warnings.filterwarnings('ignore')

# ─── Config ─────────────────────────────────────────────
RUN_DIR = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox"
DATA_PATH = os.path.join(RUN_DIR, "02_processed", "cleaned_data.csv")
FEATURE_PATH = os.path.join(RUN_DIR, "02_processed", "feature_summary.json")
VALIDATE_PATH = os.path.join(RUN_DIR, "02_processed", "validate_report.json")
ANOMALY_PATH = os.path.join(RUN_DIR, "02_processed", "anomaly_report.json")
CAUSAL_PATH = os.path.join(RUN_DIR, "02_processed", "causal_evidence_map.json")
FIG_DIR = os.path.join(RUN_DIR, "03_figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Matplotlib Chinese font setup
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

# ─── Load Data ──────────────────────────────────────────
print("Loading data...")
df = pd.read_csv(DATA_PATH)
df['ts_dcs'] = pd.to_datetime(df['ts_dcs'])
df.sort_values('ts_dcs', inplace=True)
df.reset_index(drop=True, inplace=True)

with open(FEATURE_PATH) as f:
    features = json.load(f)
with open(VALIDATE_PATH) as f:
    validation = json.load(f)
with open(ANOMALY_PATH) as f:
    anomaly = json.load(f)
with open(CAUSAL_PATH) as f:
    causal = json.load(f)

target_cols = ['cd_basis_weight_cv_pct', 'formation_index', 'strength_rel_pct', 'defect_grade_numeric']
target_labels = {
    'cd_basis_weight_cv_pct': 'CD Basis Weight CV%',
    'formation_index': 'Formation Index',
    'strength_rel_pct': 'Strength Relative %',
    'defect_grade_numeric': 'Defect Grade (Numeric)'
}
target_direction = {
    'cd_basis_weight_cv_pct': 'lower_better',
    'formation_index': 'higher_better',
    'strength_rel_pct': 'higher_better',
    'defect_grade_numeric': 'higher_better'
}
process_vars = [
    'headbox_pressure_kPa', 'approach_flow_lpm', 'fan_pump_speed_rpm',
    'white_water_consistency_pct', 'retention_aid_dosage_ppm',
    'slice_opening_mm', 'machine_speed_mmin', 'stock_temp_C',
    'jet_to_wire_ratio', 'vacuum_pump1_kPa', 'vacuum_pump2_kPa'
]
var_labels = {
    'headbox_pressure_kPa': 'Headbox Pressure (kPa)',
    'approach_flow_lpm': 'Approach Flow (L/min)',
    'fan_pump_speed_rpm': 'Fan Pump Speed (RPM)',
    'white_water_consistency_pct': 'White Water Consistency (%)',
    'retention_aid_dosage_ppm': 'Retention Aid Dosage (ppm)',
    'slice_opening_mm': 'Slice Opening (mm)',
    'machine_speed_mmin': 'Machine Speed (m/min)',
    'stock_temp_C': 'Stock Temp (C)',
    'jet_to_wire_ratio': 'Jet-to-Wire Ratio',
    'vacuum_pump1_kPa': 'Vacuum Pump 1 (kPa)',
    'vacuum_pump2_kPa': 'Vacuum Pump 2 (kPa)'
}
grades = ['GSM80', 'GSM100', 'GSM120']
grade_colors = {'GSM80': '#2196F3', 'GSM100': '#FF9800', 'GSM120': '#4CAF50'}

plot_records = []
image_captions = []

def save_fig(fig, name, caption_zh, caption_en, diagnostic_implication):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    plot_records.append({"name": name, "path": path, "type": "png"})
    image_captions.append({
        "name": name,
        "caption_zh": caption_zh,
        "caption_en": caption_en,
        "diagnostic_implication": diagnostic_implication
    })
    print(f"  Saved: {name}")

# ═══════════════════════════════════════════════════════════
# Fig A: Correlation Heatmap (Pearson matrix with Spearman divergence)
# ═══════════════════════════════════════════════════════════
print("\n=== Fig A: Correlation Heatmap ===")

# Build combined correlation matrix (process vars + targets)
all_vars = process_vars + target_cols
pearson_matrix = {}
spearman_matrix = {}
cm = features.get('correlation_matrices', {})
pm = cm.get('pearson', {})
sm = cm.get('spearman', {})

for v1 in all_vars:
    pearson_matrix[v1] = {}
    spearman_matrix[v1] = {}
    for v2 in all_vars:
        pearson_matrix[v1][v2] = pm.get(v1, {}).get(v2, 0) or 0
        spearman_matrix[v1][v2] = sm.get(v1, {}).get(v2, 0) or 0

n_vars = len(all_vars)
pearson_arr = np.zeros((n_vars, n_vars))
spearman_arr = np.zeros((n_vars, n_vars))
for i, v1 in enumerate(all_vars):
    for j, v2 in enumerate(all_vars):
        pearson_arr[i, j] = pearson_matrix[v1][v2]
        spearman_arr[i, j] = spearman_matrix[v1][v2]

divergence = np.abs(pearson_arr - spearman_arr)

fig, axes = plt.subplots(1, 2, figsize=(20, 9))

# Pearson heatmap
im1 = axes[0].imshow(pearson_arr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
axes[0].set_xticks(range(n_vars))
axes[0].set_yticks(range(n_vars))
axes[0].set_xticklabels([v.replace('_', '\n') for v in all_vars], rotation=45, ha='right', fontsize=7)
axes[0].set_yticklabels([v.replace('_', '\n') for v in all_vars], fontsize=7)
axes[0].set_title('Pearson Correlation Matrix', fontsize=12, fontweight='bold')
plt.colorbar(im1, ax=axes[0], shrink=0.8)

# Spearman divergence heatmap
im2 = axes[1].imshow(divergence, cmap='YlOrRd', vmin=0, vmax=0.3, aspect='auto')
axes[1].set_xticks(range(n_vars))
axes[1].set_yticks(range(n_vars))
axes[1].set_xticklabels([v.replace('_', '\n') for v in all_vars], rotation=45, ha='right', fontsize=7)
axes[1].set_yticklabels([v.replace('_', '\n') for v in all_vars], fontsize=7)
axes[1].set_title('Pearson-Spearman Divergence |r-rs|', fontsize=12, fontweight='bold')
cb2 = plt.colorbar(im2, ax=axes[1], shrink=0.8)
cb2.set_label('Divergence')

fig.suptitle('Correlation Structure — Paper Machine Headbox', fontsize=14, fontweight='bold')
plt.tight_layout()
save_fig(fig, 'fig_a_correlation_heatmap.png',
    '相关性热力图：左为Pearson相关矩阵，右为Pearson与Spearman的偏差。偏差值越大说明非线性关系越强。',
    'Correlation heatmap: Pearson matrix (left) and Pearson-Spearman divergence (right). Higher divergence indicates stronger nonlinear relationships.',
    'Spearman divergence > 0.15 flags non-linear dependencies that Pearson alone would miss. Check parameters with high divergence for non-monotonic effects on quality.')

# ═══════════════════════════════════════════════════════════
# Fig B: Top-Parameter vs Quality Scatter Grid
# ═══════════════════════════════════════════════════════════
print("=== Fig B: Top-Parameter Scatter Grid ===")

# Get top 5 parameters by mean |r| across targets
param_scores = {}
for e in causal.get('validated_edges', []):
    p = e['parameter']
    if p not in param_scores:
        param_scores[p] = []
    param_scores[p].append(e['abs_r'])

param_ranking = sorted(param_scores.items(), key=lambda x: np.mean(x[1]), reverse=True)
top5_params = [p for p, _ in param_ranking[:5]]

fig, axes = plt.subplots(len(top5_params), len(target_cols), figsize=(4*len(target_cols), 3.5*len(top5_params)))
fig.suptitle('Top Parameters vs Quality Targets (by Grade)', fontsize=14, fontweight='bold')

for i, param in enumerate(top5_params):
    for j, target in enumerate(target_cols):
        ax = axes[i, j] if len(top5_params) > 1 and len(target_cols) > 1 else axes[max(i,j)]
        for grade in grades:
            mask = df['grade_running'] == grade
            ax.scatter(df.loc[mask, param], df.loc[mask, target],
                      c=grade_colors[grade], alpha=0.4, s=8, label=grade if i == 0 and j == 0 else '')
        # Per-grade regression
        for grade in grades:
            mask = df['grade_running'] == grade
            x_g = df.loc[mask, param].values
            y_g = df.loc[mask, target].values
            if len(x_g) > 2:
                try:
                    from numpy.polynomial.polynomial import polyfit
                    coeffs = polyfit(x_g, y_g, 1)
                    x_line = np.linspace(x_g.min(), x_g.max(), 50)
                    y_line = coeffs[0] + coeffs[1] * x_line
                    ax.plot(x_line, y_line, color=grade_colors[grade], linewidth=1)
                except:
                    pass
        ax.set_xlabel(var_labels.get(param, param), fontsize=7)
        ax.set_ylabel(target_labels.get(target, target), fontsize=7)
        ax.tick_params(labelsize=6)

# Single legend
if len(top5_params) > 0:
    handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=grade_colors[g], label=g, markersize=6) for g in grades]
    fig.legend(handles=handles, loc='upper right', fontsize=8)

plt.tight_layout()
save_fig(fig, 'fig_b_top_param_scatter_grid.png',
    '关键参数与质量目标的散点矩阵：Top-5参数（按平均|r|排序），按产品等级着色并叠加分组回归线。',
    'Top-5 parameter vs quality scatter grid, colored by grade with per-grade regression lines.',
    'Parallel regression slopes across grades indicate a uniform physical mechanism. Diverging slopes suggest grade-dependent effects that require stratified control strategies.')

# ═══════════════════════════════════════════════════════════
# Fig C: Raw vs Detrended Comparison
# ═══════════════════════════════════════════════════════════
print("=== Fig C: Raw vs Detrended Comparison ===")

pairs_data = []
for e in causal.get('all_edges', []):
    if e['abs_r'] > 0.3:
        pairs_data.append(e)

if pairs_data:
    pair_labels = [f"{e['parameter'][:20]}\nvs\n{e['target'][:20]}" for e in pairs_data]
    raw_r = [e['pearson_r'] for e in pairs_data]
    det_r = [e['detrended_r'] if e['detrended_r'] is not None else 0 for e in pairs_data]

    x = np.arange(len(pairs_data))
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(12, len(pairs_data)*0.8), 6))
    bars1 = ax.bar(x - width/2, raw_r, width, label='Raw Pearson r', color='#2196F3', alpha=0.85)
    bars2 = ax.bar(x + width/2, det_r, width, label='Detrended r', color='#FF5722', alpha=0.85)

    # Mark attenuation >30%
    for i, e in enumerate(pairs_data):
        att = e.get('attenuation_pct', 0) or 0
        if att > 30:
            ax.annotate(f'ATT {att:.0f}%', (i, raw_r[i]), textcoords="offset points",
                       xytext=(0, 15 if raw_r[i] > 0 else -25), ha='center', fontsize=7,
                       color='red', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='red', lw=0.8))

    ax.set_xticks(x)
    ax.set_xticklabels(pair_labels, rotation=45, ha='right', fontsize=7)
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_ylabel('Correlation Coefficient', fontsize=11)
    ax.set_title('Raw vs Detrended Correlation (|r| > 0.3 pairs)', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    save_fig(fig, 'fig_c_raw_vs_detrended.png',
        '原始与去趋势后Pearson相关系数对比柱状图。标注衰减超过30%的变量对，趋势效应可能夸大真实关联。',
        'Bar chart comparing raw vs detrended Pearson correlations for |r|>0.3 pairs. Pairs with >30% attenuation are flagged as trend-confounded.',
        'High attenuation pairs (>30%) indicate correlations driven by long-term drift rather than instantaneous process coupling. These are likely confounded and should not be used as causal evidence.')

# ═══════════════════════════════════════════════════════════
# Fig D: Zone/Parameter Profile (upstream -> downstream)
# ═══════════════════════════════════════════════════════════
print("=== Fig D: Zone Parameter Profile ===")

zone_order = [
    ('Stock Prep', ['stock_temp_C', 'white_water_consistency_pct', 'retention_aid_dosage_ppm']),
    ('Approach System', ['approach_flow_lpm', 'fan_pump_speed_rpm', 'headbox_pressure_kPa']),
    ('Headbox', ['slice_opening_mm', 'jet_to_wire_ratio']),
    ('Wire Section', ['machine_speed_mmin']),
    ('Vacuum', ['vacuum_pump1_kPa', 'vacuum_pump2_kPa'])
]

zone_data = {}
for zone_name, z_vars in zone_order:
    zone_vals = {}
    for v in z_vars:
        if v in df.columns:
            zone_vals[v] = df[v].values
    zone_data[zone_name] = zone_vals

fig, axes = plt.subplots(len(zone_order), 1, figsize=(14, 3*len(zone_order)), sharex=True)
fig.suptitle('Process Parameter Profiles by Zone (Upstream -> Downstream)', fontsize=14, fontweight='bold')

time_hours = (df['ts_dcs'] - df['ts_dcs'].iloc[0]).dt.total_seconds() / 3600

for idx, (zone_name, z_vars) in enumerate(zone_order):
    ax = axes[idx]
    for v in z_vars:
        if v in df.columns:
            vals = df[v].values
            vals_norm = (vals - np.nanmean(vals)) / np.nanstd(vals)
            ax.plot(time_hours, vals_norm, linewidth=0.5, alpha=0.7, label=var_labels.get(v, v))
    ax.set_ylabel('Normalized Value', fontsize=9)
    ax.set_title(f'{zone_name}', fontsize=11, fontweight='bold', loc='left')
    ax.legend(loc='upper right', fontsize=7, ncol=min(3, len(z_vars)))
    ax.grid(alpha=0.3)
    ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')

axes[-1].set_xlabel('Time (hours)', fontsize=10)
plt.tight_layout()
save_fig(fig, 'fig_d_zone_parameter_profile.png',
    '按工艺流程分区（备浆→流送→流浆箱→网部→真空）的参数归一化时间序列。展示上下游参数联动关系。',
    'Zone-based normalized parameter profiles from stock prep through vacuum section. Reveals upstream-downstream coupling dynamics.',
    'Cascading disturbances visible when upstream zone deviation propagates downstream with time delay. Sudden vacuum changes after stock prep variations suggest pump response lags.')

# ═══════════════════════════════════════════════════════════
# Fig E: Speed-Tension Coupling (machine_speed vs jet_to_wire_ratio)
# ═══════════════════════════════════════════════════════════
print("=== Fig E: Speed-Tension Coupling ===")

fig, ax1 = plt.subplots(figsize=(14, 6))
time_hours = (df['ts_dcs'] - df['ts_dcs'].iloc[0]).dt.total_seconds() / 3600

ax1.plot(time_hours, df['machine_speed_mmin'], color='#2196F3', linewidth=0.8, alpha=0.8, label='Machine Speed (m/min)')
ax1.set_ylabel('Machine Speed (m/min)', color='#2196F3', fontsize=11)
ax1.tick_params(axis='y', labelcolor='#2196F3')

ax2 = ax1.twinx()
ax2.plot(time_hours, df['jet_to_wire_ratio'], color='#FF5722', linewidth=0.8, alpha=0.8, label='Jet-to-Wire Ratio')
ax2.set_ylabel('Jet-to-Wire Ratio', color='#FF5722', fontsize=11)
ax2.tick_params(axis='y', labelcolor='#FF5722')

# Color by grade
for grade in grades:
    mask = df['grade_running'] == grade
    ax1.fill_between(time_hours, df['machine_speed_mmin'].min(), df['machine_speed_mmin'].max(),
                     where=mask, alpha=0.06, color=grade_colors[grade])

ax1.set_xlabel('Time (hours)', fontsize=11)
fig.suptitle('Speed-Tension Coupling: Machine Speed vs Jet-to-Wire Ratio', fontsize=13, fontweight='bold')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
ax1.grid(alpha=0.3)
plt.tight_layout()
save_fig(fig, 'fig_e_speed_tension_coupling.png',
    '车速与浆网速比的双Y轴时间序列。背景色带标识产品等级切换区间。两者偏离理想耦合关系时提示流浆箱控制异常。',
    'Dual Y-axis time series of machine speed and jet-to-wire ratio. Grade regions shaded. Decoupling events indicate headbox control anomalies.',
    'Jet-to-wire ratio should maintain ~1.0-1.05 for optimal formation. Persistent deviations from this range, especially during speed changes, indicate slice opening or approach flow control lags that degrade formation quality.')

# ═══════════════════════════════════════════════════════════
# Fig F: Steady-State Deviation Time Series
# ═══════════════════════════════════════════════════════════
print("=== Fig F: Steady-State Deviation ===")

fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
fig.suptitle('Steady-State Deviation: Drift vs Sudden Shifts', fontsize=14, fontweight='bold')

for idx, target in enumerate(target_cols):
    ax = axes[idx]
    series = df[target].values
    # Overall mean as baseline
    baseline = np.mean(series)
    deviation = series - baseline

    # Rolling mean for trend visualization
    window = max(10, len(series) // 50)
    rolling = pd.Series(series).rolling(window=window, center=True).mean()

    ax.plot(time_hours, deviation, linewidth=0.4, alpha=0.5, color='gray', label='Deviation')
    ax.plot(time_hours, rolling.values - baseline, linewidth=1.5, color='#E91E63', label=f'Rolling Mean (w={window})')
    ax.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax.axhline(y=2*np.std(series), color='red', linewidth=0.5, linestyle=':', alpha=0.7, label='+2σ')
    ax.axhline(y=-2*np.std(series), color='red', linewidth=0.5, linestyle=':', alpha=0.7)

    # Mark grade transitions
    for i in range(1, len(df)):
        if df.iloc[i]['grade_running'] != df.iloc[i-1]['grade_running']:
            ax.axvline(x=time_hours[i], color='purple', linewidth=0.3, alpha=0.3)

    ax.set_ylabel(target_labels[target], fontsize=9)
    ax.legend(loc='upper right', fontsize=7, ncol=3)
    ax.grid(alpha=0.2)

axes[-1].set_xlabel('Time (hours)', fontsize=10)
plt.tight_layout()
save_fig(fig, 'fig_f_steady_state_deviation.png',
    '稳态偏差时间序列：各质量指标偏离均值的滚动趋势。紫色竖线标记产品等级切换点，红色虚线标记±2σ控制限。',
    'Steady-state deviation time series with rolling trend. Purple lines mark grade transitions, red dashed lines show ±2σ control limits.',
    'Gradual drift in rolling mean (spanning multiple grade changes) suggests equipment degradation. Sudden step changes at grade transitions indicate grade-dependent setpoint issues rather than progressive wear.')

# ═══════════════════════════════════════════════════════════
# Fig G: Per-Grade Quality Distribution
# ═══════════════════════════════════════════════════════════
print("=== Fig G: Per-Grade Distribution ===")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

for idx, target in enumerate(target_cols):
    ax = axes[idx]
    positions = []
    data_list = []
    for gi, grade in enumerate(grades):
        gdata = df.loc[df['grade_running'] == grade, target].dropna().values
        data_list.append(gdata)
        positions.append(gi + 1)

    bp = ax.boxplot(data_list, positions=positions, widths=0.5, patch_artist=True)
    for gi, grade in enumerate(grades):
        bp['boxes'][gi].set_facecolor(grade_colors[grade])
        bp['boxes'][gi].set_alpha(0.6)

    # Add violin-like distribution via scatter
    for gi, grade in enumerate(grades):
        gdata = data_list[gi]
        if len(gdata) > 0:
            jitter = np.random.normal(0, 0.08, size=len(gdata))
            ax.scatter(np.full(len(gdata), gi+1) + jitter, gdata,
                      alpha=0.15, s=3, color=grade_colors[grade])

    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(grades, fontsize=9)
    ax.set_ylabel(target_labels[target], fontsize=9)
    direction = target_direction[target]
    ax.set_title(f'{target_labels[target]} ({direction})', fontsize=10, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
save_fig(fig, 'fig_g_per_grade_distribution.png',
    '各产品等级（GSM80/GSM100/GSM120）质量指标箱线图与散点分布。对比不同等级的质量一致性与变异度。',
    'Per-grade quality distribution boxplots with scatter overlay for GSM80/GSM100/GSM120 grades.',
    'Different within-grade variance across grades suggests grade-dependent process capability. A grade with systematically worse quality may indicate suboptimal setpoints for that specific product.')

# ═══════════════════════════════════════════════════════════
# Fig H: Anomaly Timeline
# ═══════════════════════════════════════════════════════════
print("=== Fig H: Anomaly Timeline ===")

fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
fig.suptitle('Quality Anomaly Timeline with Adaptive Thresholds', fontsize=14, fontweight='bold')

anomaly_data = anomaly.get('target_results', {})
window = anomaly.get('adaptive_window', 159)

for idx, target in enumerate(target_cols):
    ax = axes[idx]
    series = df[target].values
    ax.plot(time_hours, series, linewidth=0.6, color='#333333', alpha=0.7, label='Actual')

    # Rolling mean ± 2σ
    rolling_mean = pd.Series(series).rolling(window=window, center=True, min_periods=window//2).mean()
    rolling_std = pd.Series(series).rolling(window=window, center=True, min_periods=window//2).std()
    upper = rolling_mean + 2 * rolling_std
    lower = rolling_mean - 2 * rolling_std

    ax.fill_between(time_hours, lower, upper, alpha=0.15, color='blue', label='Adaptive ±2σ')
    ax.plot(time_hours, rolling_mean, linewidth=1, color='blue', alpha=0.6, linestyle='--')

    # Shade anomaly intervals
    intervals = anomaly_data.get(target, {}).get('intervals', [])[:20]
    for interval in intervals:
        si = interval['start_index']
        ei = interval['end_index']
        if si < len(time_hours) and ei < len(time_hours):
            ax.axvspan(time_hours[si], time_hours[ei], alpha=0.2, color='red')

    ax.set_ylabel(target_labels[target], fontsize=9)
    ax.legend(loc='upper right', fontsize=7)
    ax.grid(alpha=0.2)

axes[-1].set_xlabel('Time (hours)', fontsize=10)
plt.tight_layout()
save_fig(fig, 'fig_h_anomaly_timeline.png',
    '质量异常时间线：自适应滚动阈值（±2σ）标记异常区间（红色阴影）。超越阈值区间的数据点提示过程失控事件。',
    'Anomaly timeline with adaptive rolling thresholds (±2σ). Red shaded regions mark anomaly intervals where quality exceeds threshold bounds.',
    'Clustering of anomalies at specific time periods suggests episodic root causes (e.g., raw material batch changes, shift changes) rather than continuous degradation. Cross-reference with operator event log for temporal correlation.')

# ═══════════════════════════════════════════════════════════
# Fig I: Transition Impact — Before/After Grade Change
# ═══════════════════════════════════════════════════════════
print("=== Fig I: Transition Impact ===")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

transition_window = 5
transitions = []
for i in range(1, len(df)):
    if df.iloc[i]['grade_running'] != df.iloc[i-1]['grade_running']:
        transitions.append(i)

# Aggregate before/after for all transitions
for idx, target in enumerate(target_cols):
    ax = axes[idx]
    before_vals = []
    after_vals = []
    transition_types = []

    for ti in transitions[:100]:
        bs = max(0, ti - transition_window)
        ae = min(len(df), ti + transition_window)
        bv = df.iloc[bs:ti][target].values
        av = df.iloc[ti:ae][target].values
        if len(bv) > 0 and len(av) > 0:
            before_vals.append(np.mean(bv))
            after_vals.append(np.mean(av))
            transition_types.append(f"{df.iloc[ti-1]['grade_running']}→{df.iloc[ti]['grade_running']}")

    if before_vals:
        pairs = list(zip(before_vals, after_vals))
        for i, (b, a) in enumerate(pairs):
            # Color by transition type
            color = '#2196F3' if 'GSM' in transition_types[i].split('→')[0] else '#FF9800'
            ax.scatter(b, a, alpha=0.5, s=15, c=color)
            ax.plot([b, b], [b, a], color='gray', alpha=0.2, linewidth=0.5)
            ax.plot([b, a], [a, a], color='gray', alpha=0.2, linewidth=0.5)

        # 1:1 line
        all_vals = before_vals + after_vals
        min_v, max_v = min(all_vals), max(all_vals)
        ax.plot([min_v, max_v], [min_v, max_v], 'k--', linewidth=0.8, alpha=0.5, label='No Change')

        ax.set_xlabel(f'Before Transition ({target_labels[target]})', fontsize=9)
        ax.set_ylabel(f'After Transition ({target_labels[target]})', fontsize=9)
        ax.set_title(f'{target_labels[target]}', fontsize=10, fontweight='bold')
        ax.grid(alpha=0.3)

plt.tight_layout()
save_fig(fig, 'fig_i_transition_impact.png',
    '等级切换前后质量对比散点图。每个点代表一次等级切换事件，对角线为无变化基准线。偏离对角线说明切换导致质量偏移。',
    'Before/after grade transition quality comparison. Each point is a transition event; the diagonal is the no-change baseline. Points off the diagonal indicate quality shifts caused by grade transitions.',
    'Systematic deviation above or below the diagonal indicates transition-induced quality bias. Persistent offset suggests setpoint adjustment delays or grade-dependent parameter interactions not captured by static control recipes.')

# ═══════════════════════════════════════════════════════════
# Fig J: By-Grade Quality Time Series
# ═══════════════════════════════════════════════════════════
print("=== Fig J: By-Grade Quality Time Series ===")

fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
fig.suptitle('Quality Time Series by Product Grade', fontsize=14, fontweight='bold')

for idx, target in enumerate(target_cols):
    ax = axes[idx]
    for grade in grades:
        mask = df['grade_running'] == grade
        gdf = df[mask]
        gtime = (gdf['ts_dcs'] - df['ts_dcs'].iloc[0]).dt.total_seconds() / 3600
        ax.scatter(gtime, gdf[target], s=4, alpha=0.5, color=grade_colors[grade], label=grade)

    ax.set_ylabel(target_labels[target], fontsize=9)
    ax.legend(loc='upper right', fontsize=8, ncol=3)
    ax.grid(alpha=0.2)

axes[-1].set_xlabel('Time (hours)', fontsize=10)
plt.tight_layout()
save_fig(fig, 'fig_j_by_grade_quality_ts.png',
    '按产品等级着色的质量指标时间序列。GSM80/GSM100/GSM120分别以蓝/橙/绿标识。观察各等级内部质量随时间的演变趋势。',
    'Quality time series colored by product grade (GSM80=blue, GSM100=orange, GSM120=green). Reveals within-grade temporal quality evolution.',
    'Within-grade quality trends that differ from between-grade patterns indicate grade-specific degradation mechanisms. If all grades show the same drift pattern, root cause is likely a common-mode factor (e.g., raw material, shared equipment).')

# ═══════════════════════════════════════════════════════════
# CONDITIONAL: Regime-Segmented Time Series (change points)
# ═══════════════════════════════════════════════════════════
change_points_count = validation.get('summary', {}).get('change_points_detected', 0)
if change_points_count > 0:
    print(f"=== Conditional: Regime-Segmented TS ({change_points_count} change points) ===")

    cp_data = validation.get('change_point_analysis', {}).get('change_points_by_column', {})

    fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
    fig.suptitle(f'Regime-Segmented Time Series ({change_points_count} Change Points Detected)', fontsize=14, fontweight='bold')

    for idx, target in enumerate(target_cols):
        ax = axes[idx]
        series = df[target].values
        ax.plot(time_hours, series, linewidth=0.5, color='#333', alpha=0.7)

        # Mark change points
        cps = cp_data.get(target, [])
        if isinstance(cps, list):
            for cp in cps:
                if isinstance(cp, dict):
                    cp_idx = cp.get('index', cp.get('location', None))
                else:
                    cp_idx = cp
                if cp_idx is not None and int(cp_idx) < len(time_hours):
                    ax.axvline(x=time_hours[int(cp_idx)], color='red', linewidth=1.5, linestyle='--', alpha=0.7)

        ax.set_ylabel(target_labels[target], fontsize=9)
        ax.grid(alpha=0.2)

    axes[-1].set_xlabel('Time (hours)', fontsize=10)
    plt.tight_layout()
    save_fig(fig, 'fig_k_regime_segmented_ts.png',
        '变点分段时间序列：红色虚线标记统计变点位置（PELT算法检测）。分段内相关性可能不同于全局相关性。',
        'Regime-segmented time series with detected change points (PELT algorithm) marked by red dashed lines.',
        'Correlations computed across regime boundaries may be spurious. Per-segment re-analysis is required before accepting any causal hypothesis that spans change point boundaries.')

# ═══════════════════════════════════════════════════════════
# CONDITIONAL: Spearman vs Pearson Robustness
# ═══════════════════════════════════════════════════════════
spearman_div = validation.get('summary', {}).get('spearman_divergence_findings', 0)
if spearman_div > 0:
    print(f"=== Conditional: Spearman-Pearson Divergence ===")

    diverged_pairs = []
    for e in causal.get('all_edges', []):
        if e.get('spearman_divergence', 0) > 0.1:
            diverged_pairs.append(e)

    if diverged_pairs:
        fig, ax = plt.subplots(figsize=(12, 6))
        names = [f"{e['parameter'][:15]}\nvs\n{e['target'][:15]}" for e in diverged_pairs]
        pearson_vals = [e['pearson_r'] for e in diverged_pairs]
        spearman_vals = [e['spearman_rho'] for e in diverged_pairs]

        x = np.arange(len(diverged_pairs))
        ax.bar(x - 0.2, pearson_vals, 0.4, label='Pearson', color='#2196F3')
        ax.bar(x + 0.2, spearman_vals, 0.4, label='Spearman', color='#4CAF50')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Correlation Coefficient', fontsize=11)
        ax.set_title('Pearson vs Spearman: Divergent Pairs (|r-rs| > 0.1)', fontsize=13, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=0.5)
        plt.tight_layout()
        save_fig(fig, 'fig_l_spearman_divergence.png',
            'Pearson与Spearman相关系数存在显著偏离的变量对。偏离>0.1提示存在非线性单调关系或离群值影响。',
            'Pairs with significant Pearson-Spearman divergence (>0.1). Indicates nonlinear monotonic relationships or outlier sensitivity.',
            'Spearman >> Pearson suggests rank-preserving nonlinear effects (e.g., saturation). Pearson >> Spearman suggests outlier-driven correlations that may not be robust.')

# ═══════════════════════════════════════════════════════════
# Save Manifests
# ═══════════════════════════════════════════════════════════
print("\nSaving manifests...")

manifest = {
    "run_id": "202605291347083_paper_machine_headbox",
    "scenario": "continuous_process",
    "figures": plot_records,
    "total_plots": len(plot_records),
    "generated_at": str(pd.Timestamp.now())
}

with open(os.path.join(FIG_DIR, 'plot_manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

with open(os.path.join(FIG_DIR, 'image_captions.json'), 'w', encoding='utf-8') as f:
    json.dump({"captions": image_captions, "total": len(image_captions)}, f, indent=2, ensure_ascii=False)

print(f"\n=== Visualization Complete ===")
print(f"  Total plots: {len(plot_records)}")
print(f"  Captions: {len(image_captions)}")
print(f"  Manifest: {os.path.join(FIG_DIR, 'plot_manifest.json')}")
print(f"  Captions: {os.path.join(FIG_DIR, 'image_captions.json')}")
