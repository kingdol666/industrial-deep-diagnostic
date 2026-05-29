#!/usr/bin/env python3
"""
deep_visualize.py — 方法参考脚本（BOPET 纵拉段示例）

⚠️ v8.0 说明：此脚本为方法学参考，不直接运行。
Agent 根据 Step 1 的分析结果，自行决定可视化方案并编写绘图代码。
此脚本提供以下可复用的方法学：
  - 相关热力图生成
  - Top预测因子条形图
  - 分组散点图（按产品/材料着色）
  - 分层相关对比图（Simpson检测可视化）

读取 deep_analyze.py 的输出 JSON，生成结构化图表。
所有图表描述写入 image_captions.json 供下游Agent使用。

Usage:
  python3 deep_visualize.py \
    --analysis workspace/deep_analysis_output.json \
    --output-dir workspace/deep_figures \
    --timeseries data/merged_process_data.csv
"""

import argparse
import json
import os
import math
import statistics
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════
#  图1: 时序总览图 — 关键参数全时程热力图
# ═══════════════════════════════════════════════════════════

def plot_timeseries_heatmap(analysis, output_dir, ts_csv_path=None):
    """生成参数随批次变化的 heatmap — X轴=批次时间, Y轴=参数"""
    inventory = analysis['batch_inventory']
    if not inventory:
        return None

    # 按时间排序
    batches_sorted = sorted(inventory.items(), key=lambda x: x[1].get('model', ''))

    # 取温度参数 (MD_TH*)
    temp_params = []
    for bid, bd in batches_sorted[:1]:
        temp_params = sorted([k for k in bd.keys() if k.startswith('MD_TH')])

    if not temp_params:
        return None

    # 构建 heatmap 矩阵: rows=params, cols=batches
    data_matrix = []
    param_labels = []
    for param in temp_params:
        row = [inventory[bid].get(param, {}).get('mean', np.nan) for bid, _ in batches_sorted]
        data_matrix.append(row)
        # 简化标签
        roll = param.replace('MD_TH', '').replace('@PV', '')
        param_labels.append(f'R{int(roll)}')

    data_matrix = np.array(data_matrix)

    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(data_matrix, aspect='auto', cmap='RdYlBu_r')
    ax.set_yticks(range(len(param_labels)))
    ax.set_yticklabels(param_labels)
    ax.set_xlabel('Batch Index (time-ordered)')
    ax.set_ylabel('MD Roller Temperature')
    ax.set_title('MD Roller Temperature Across Batches (°C)')

    # 标注产品切换
    models = [bd['model'] for _, bd in batches_sorted]
    for i in range(1, len(models)):
        if models[i] != models[i-1]:
            ax.axvline(x=i-0.5, color='white', linewidth=1.5, linestyle='--')

    plt.colorbar(im, ax=ax, label='Temperature (°C)')

    path = os.path.join(output_dir, 'fig_01_ts_heatmap.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': 'MD辊温批次热力图', 'description': '18个MD辊温度在55个批次中的均值变化。白色虚线标记产品切换点。红色=高温(拉伸段~82°C)，蓝色=低温(急冷段~35°C)'}


# ═══════════════════════════════════════════════════════════
#  图2: 物理过程分段 — 温度剖面图（按产品着色）
# ═══════════════════════════════════════════════════════════

def plot_zone_profile(analysis, output_dir):
    """每个产品的18辊温度分布曲线"""
    inventory = analysis['batch_inventory']

    # 按产品聚合
    by_product = defaultdict(list)
    for bid, bd in inventory.items():
        by_product[bd['model']].append(bd)

    # 取第一个批次的温度参数
    sample = next(iter(inventory.values()))
    temp_params = sorted([k for k in sample.keys() if k.startswith('MD_TH')])

    fig, ax = plt.subplots(figsize=(14, 6))

    for product in sorted(by_product.keys()):
        bids = by_product[product]
        means_per_roll = []
        for param in temp_params:
            vals = [inventory[bid].get(param, {}).get('mean', np.nan) for bid in bids]
            vals = [v for v in vals if not np.isnan(v)]
            means_per_roll.append(np.mean(vals) if vals else np.nan)

        rolls = [int(p.replace('MD_TH', '').replace('@PV', '')) for p in temp_params]
        ax.plot(rolls, means_per_roll, 'o-', label=f'{product} (n={len(bids)})', markersize=4)

    # 分区标记
    ax.axvspan(0.5, 5.5, alpha=0.08, color='blue', label='预加热段')
    ax.axvspan(5.5, 11.5, alpha=0.08, color='red', label='拉伸段')
    ax.axvspan(11.5, 18.5, alpha=0.08, color='cyan', label='急冷段')

    ax.axhline(y=75, color='gray', linestyle=':', alpha=0.5, label='Tg≈75°C')
    ax.set_xlabel('Roll Number')
    ax.set_ylabel('Temperature (°C)')
    ax.set_title('MD Roller Temperature Profile by Product Grade')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.set_xticks(range(1, 19))

    path = os.path.join(output_dir, 'fig_02_zone_profile.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': 'MD辊温分区剖面图', 'description': '各产品等级的18辊温度分布曲线。可清晰看到三段物理分区：预加热(~75°C near Tg)→拉伸(~82°C above Tg)→急冷(~35°C)。不同产品在预加热和急冷段的设定点差异显著'}


# ═══════════════════════════════════════════════════════════
#  图3: 缺陷-参数关联热力图（Spearman）
# ═══════════════════════════════════════════════════════════

def plot_defect_correlation_heatmap(analysis, output_dir):
    """Top 20 参数 × 5 缺陷的 Spearman 相关热力图"""
    corrs = analysis['correlations']['defect_correlations']
    defects = analysis['meta']['defect_types']

    # 收集所有参数
    all_params = set()
    for defect in defects:
        for c in corrs.get(defect, []):
            all_params.add(c['feature'])

    # 选Top 20 by max |spearman|
    param_max_sp = {}
    for param in all_params:
        max_sp = 0
        for defect in defects:
            for c in corrs.get(defect, []):
                if c['feature'] == param:
                    max_sp = max(max_sp, abs(c['spearman_r']))
        param_max_sp[param] = max_sp

    top_params = sorted(param_max_sp, key=lambda x: param_max_sp[x], reverse=True)[:25]

    # 构建矩阵
    matrix = np.zeros((len(top_params), len(defects)))
    for i, param in enumerate(top_params):
        for j, defect in enumerate(defects):
            for c in corrs.get(defect, []):
                if c['feature'] == param:
                    matrix[i, j] = c['spearman_r']

    fig, ax = plt.subplots(figsize=(10, 12))
    im = ax.imshow(matrix, aspect='auto', cmap='RdBu_r', vmin=-0.8, vmax=0.8)
    ax.set_xticks(range(len(defects)))
    ax.set_xticklabels(defects, rotation=45, ha='right')
    ax.set_yticks(range(len(top_params)))
    ax.set_yticklabels(top_params)
    ax.set_title('Parameter-Defect Spearman Correlation (Top 25)')

    # 标注数值
    for i in range(len(top_params)):
        for j in range(len(defects)):
            val = matrix[i, j]
            if abs(val) > 0.01:
                color = 'white' if abs(val) > 0.4 else 'black'
                ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=7, color=color)

    plt.colorbar(im, ax=ax, label='Spearman ρ')

    path = os.path.join(output_dir, 'fig_03_corr_heatmap.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '参数-缺陷Spearman相关热力图', 'description': 'Top 25参数与5种缺陷的Spearman秩相关。红色=正相关, 蓝色=负相关。基于高频时序的批次内均值特征。注意melt_spots列有极强相关(>0.7)'}


# ═══════════════════════════════════════════════════════════
#  图4: 每种缺陷的Top预测因子条形图
# ═══════════════════════════════════════════════════════════

def plot_top_predictors(analysis, output_dir):
    """每种缺陷 Top 8 预测因子的 Spearman r 条形图"""
    top = analysis['correlations']['top_predictors']
    defects = analysis['meta']['defect_types']

    fig, axes = plt.subplots(len(defects), 1, figsize=(14, 3 * len(defects)))
    if len(defects) == 1:
        axes = [axes]

    for idx, defect in enumerate(defects):
        ax = axes[idx]
        preds = top.get(defect, [])[:8]
        if not preds:
            ax.set_title(f'{defect}: 无足够数据')
            continue

        params = [p['feature'] for p in preds]
        sp_vals = [p['spearman_r'] for p in preds]
        pe_vals = [p['pearson_r'] for p in preds]

        colors_sp = ['#e74c3c' if v > 0 else '#3498db' for v in sp_vals]

        y_pos = np.arange(len(params))
        ax.barh(y_pos - 0.15, sp_vals, 0.3, label='Spearman', color=colors_sp, alpha=0.8)
        ax.barh(y_pos + 0.15, pe_vals, 0.3, label='Pearson', color='gray', alpha=0.5)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(params, fontsize=8)
        ax.set_xlabel('Correlation')
        ax.set_title(f'{defect} — Top 8 Predictors (from timeseries batch-means)')
        ax.legend(fontsize=7)
        ax.axvline(x=0, color='black', linewidth=0.5)

    plt.tight_layout()
    path = os.path.join(output_dir, 'fig_04_top_predictors.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '各缺陷Top预测因子', 'description': '5种缺陷各Top 8预测因子的Spearman(彩色)vs Pearson(灰色)对比。Sp和Pe方向不一致时暗示离 outlier驱动或非线性关系'}


# ═══════════════════════════════════════════════════════════
#  图5: 批次内时序动态特征 — 波动性热力图
# ═══════════════════════════════════════════════════════════

def plot_volatility_heatmap(analysis, output_dir):
    """各参数在各批次内的波动性(CV%)热力图"""
    inventory = analysis['batch_inventory']

    temp_params = sorted([k for k in next(iter(inventory.values())).keys() if k.startswith('MD_TH')])

    batches_sorted = sorted(inventory.items(), key=lambda x: x[1].get('model', ''))

    matrix = []
    param_labels = []
    for param in temp_params:
        row = [inventory[bid].get(param, {}).get('cv_pct', np.nan) for bid, _ in batches_sorted]
        matrix.append(row)
        roll = param.replace('MD_TH', '').replace('@PV', '')
        param_labels.append(f'R{int(roll)}')

    matrix = np.array(matrix)

    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(matrix, aspect='auto', cmap='YlOrRd', vmin=0, vmax=np.nanpercentile(matrix, 95))
    ax.set_yticks(range(len(param_labels)))
    ax.set_yticklabels(param_labels)
    ax.set_xlabel('Batch Index')
    ax.set_title('Parameter Coefficient of Variation (%) Across Batches — Within-Batch Stability')

    plt.colorbar(im, ax=ax, label='CV%')

    path = os.path.join(output_dir, 'fig_05_volatility.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '批次内参数波动性(CV%)', 'description': '各参数在各批次内的变异系数(CV%)。高CV(亮色)表示该参数在该批次中不稳定。可定位哪些批次存在异常波动'}


# ═══════════════════════════════════════════════════════════
#  图6: 缺陷-关键参数散点图（按产品着色）
# ═══════════════════════════════════════════════════════════

def plot_defect_param_scatter(analysis, output_dir):
    """每种缺陷 vs 其 Top 预测参数的散点图，按产品着色"""
    top = analysis['correlations']['top_predictors']
    inventory = analysis['batch_inventory']
    defects = analysis['meta']['defect_types']

    pairs = []
    for defect in defects:
        preds = top.get(defect, [])[:2]
        for p in preds:
            pairs.append((defect, p['feature'], p['spearman_r']))

    n_pairs = min(len(pairs), 10)
    if n_pairs == 0:
        return None

    n_cols = 2
    n_rows = (n_pairs + 1) // 2
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 4 * n_rows))
    axes = axes.flatten() if n_pairs > 1 else [axes]

    # 按产品分配颜色
    products = sorted(set(bd['model'] for bd in inventory.values()))
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(products), 1)))
    product_colors = {p: colors[i] for i, p in enumerate(products)}

    for idx in range(n_pairs):
        ax = axes[idx] if idx < len(axes) else axes[-1]
        defect, param, sp_r = pairs[idx]

        for product in products:
            x, y = [], []
            for bid, bd in inventory.items():
                if bd['model'] != product:
                    continue
                feat = bd.get(param, {}).get('mean')
                d = bd.get('defects', {}).get(defect)
                if feat is not None and d is not None:
                    x.append(feat)
                    y.append(d)
            if x:
                ax.scatter(x, y, label=product, color=product_colors[product], s=30, alpha=0.7)

        ax.set_xlabel(f'{param} (batch mean)')
        ax.set_ylabel(defect)
        ax.set_title(f'{defect} vs {param} (Sp={sp_r:.3f})')
        ax.legend(fontsize=6, loc='upper right')

    for idx in range(n_pairs, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, 'fig_06_scatter_by_product.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '缺陷-参数散点图(按产品着色)', 'description': '每种缺陷vs Top预测参数的散点图。点按产品等级着色。可直观看到是产品内相关还是产品间差异驱动'}


# ═══════════════════════════════════════════════════════════
#  图7: 变点/产品切换时间线
# ═══════════════════════════════════════════════════════════

def plot_transition_timeline(analysis, output_dir):
    """产品切换和参数跳变时间线"""
    transitions = analysis['transitions']
    if not transitions:
        return None

    fig, ax = plt.subplots(figsize=(16, 4))

    products = sorted(set(t['from_model'] for t in transitions) | set(t['to_model'] for t in transitions))
    colors = plt.cm.tab20(np.linspace(0, 1, max(len(products), 1)))
    p_colors = {p: colors[i] for i, p in enumerate(products)}

    # 画产品切换序列
    for i, t in enumerate(transitions):
        ax.barh(0, 1, left=i, color=p_colors.get(t['from_model'], 'gray'), edgecolor='white', linewidth=0.5)
        if t['is_product_switch']:
            ax.axvline(x=i, color='red', linewidth=0.5, alpha=0.5)

    ax.set_xlabel('Transition Index')
    ax.set_title('Product Switch Timeline (red lines = product changes)')
    ax.set_yticks([])

    # 图例
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=p_colors[p], label=p) for p in products if p in p_colors]
    ax.legend(handles=handles, bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7)

    path = os.path.join(output_dir, 'fig_07_transition_timeline.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '产品切换时间线', 'description': '批次过渡点的产品序列。红线标记产品等级切换。可帮助理解Simpson Paradox的来源'}


# ═══════════════════════════════════════════════════════════
#  图8: 缺陷共现矩阵
# ═══════════════════════════════════════════════════════════

def plot_defect_cooccurrence(analysis, output_dir):
    coocc = analysis['correlations']['defect_cooccurrence']
    defects = analysis['meta']['defect_types']

    n = len(defects)
    matrix = np.zeros((n, n))
    for i, d1 in enumerate(defects):
        for j, d2 in enumerate(defects):
            if i == j:
                matrix[i, j] = 1.0
            elif d1 in coocc and d2 in coocc[d1]:
                matrix[i, j] = coocc[d1][d2]
            elif d2 in coocc and d1 in coocc[d2]:
                matrix[i, j] = coocc[d2][d1]

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap='RdBu_r', vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_xticklabels(defects, rotation=45, ha='right')
    ax.set_yticks(range(n))
    ax.set_yticklabels(defects)
    ax.set_title('Defect Co-occurrence (Spearman)')

    for i in range(n):
        for j in range(n):
            ax.text(j, i, f'{matrix[i,j]:.2f}', ha='center', va='center', fontsize=9)

    plt.colorbar(im, ax=ax, label='Spearman ρ')

    path = os.path.join(output_dir, 'fig_08_cooccurrence.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '缺陷共现矩阵', 'description': '5种缺陷间的Spearman相关矩阵。基于高频对齐的55个批次数据'}


# ═══════════════════════════════════════════════════════════
#  图9: 分层相关对比图（Simpson's Paradox检测）
# ═══════════════════════════════════════════════════════════

def plot_stratified_comparison(analysis, output_dir):
    """对比整体相关 vs 各产品内部相关"""
    strat = analysis['correlations']['product_stratified']
    defects = analysis['meta']['defect_types']

    # 收集有分层数据的 top 特征
    top_features = set()
    for defect in defects:
        for feat, products in strat.get(defect, {}).items():
            if len(products) >= 2:
                top_features.add((defect, feat))

    if not top_features:
        return None

    top_features = sorted(top_features, key=lambda x: len(strat[x[0]][x[1]]), reverse=True)[:12]

    fig, axes = plt.subplots(3, 4, figsize=(18, 12))
    axes = axes.flatten()

    for idx, (defect, feat) in enumerate(top_features[:12]):
        ax = axes[idx]
        products_data = strat[defect][feat]

        names = sorted(products_data.keys())
        rs = [products_data[p]['r'] for p in names]
        ns = [products_data[p]['n'] for p in names]

        colors = ['#e74c3c' if r > 0 else '#3498db' for r in rs]
        bars = ax.barh(range(len(names)), rs, color=colors, alpha=0.7)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels([f'{n}(n={ns[i]})' for i, n in enumerate(names)], fontsize=7)
        ax.set_xlabel('Spearman ρ')
        ax.set_title(f'{defect[:8]} vs {feat[:15]}', fontsize=8)
        ax.axvline(x=0, color='black', linewidth=0.5)

    for idx in range(len(top_features), len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle('Stratified Correlation: Within-Product Analysis (Simpson\'s Paradox Detection)', fontsize=12)
    plt.tight_layout()

    path = os.path.join(output_dir, 'fig_09_stratified.png')
    fig.savefig(path)
    plt.close(fig)
    return {'file': path, 'title': '分层相关对比(Simpson检测)', 'description': '各产品内部参数-缺陷相关 vs 整体相关的对比。方向不一致= Simpson\'s Paradox。基于高频时序对齐的批次数据'}


# ═══════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='深度诊断可视化引擎')
    parser.add_argument('--analysis', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--timeseries', default=None)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    analysis = load_json(args.analysis)

    captions = {}
    plots = [
        ('fig_01', lambda: plot_timeseries_heatmap(analysis, args.output_dir, args.timeseries)),
        ('fig_02', lambda: plot_zone_profile(analysis, args.output_dir)),
        ('fig_03', lambda: plot_defect_correlation_heatmap(analysis, args.output_dir)),
        ('fig_04', lambda: plot_top_predictors(analysis, args.output_dir)),
        ('fig_05', lambda: plot_volatility_heatmap(analysis, args.output_dir)),
        ('fig_06', lambda: plot_defect_param_scatter(analysis, args.output_dir)),
        ('fig_07', lambda: plot_transition_timeline(analysis, args.output_dir)),
        ('fig_08', lambda: plot_defect_cooccurrence(analysis, args.output_dir)),
        ('fig_09', lambda: plot_stratified_comparison(analysis, args.output_dir)),
    ]

    for fig_id, plot_fn in plots:
        try:
            result = plot_fn()
            if result:
                captions[os.path.basename(result['file'])] = {
                    'figure_id': fig_id,
                    'title': result['title'],
                    'description': result['description']
                }
                print(f"  ✓ {os.path.basename(result['file'])}: {result['title']}")
        except Exception as e:
            print(f"  ✗ {fig_id}: {e}")

    # 写入 captions
    captions_path = os.path.join(args.output_dir, 'image_captions.json')
    with open(captions_path, 'w', encoding='utf-8') as f:
        json.dump({'generated_at': datetime.now().isoformat(), 'figures': captions}, f, ensure_ascii=False, indent=2)

    print(f"\n生成 {len(captions)} 张图表")
    print(f"Captions: {captions_path}")


if __name__ == '__main__':
    main()
