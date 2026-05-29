#!/usr/bin/env python3
"""
deep_analyze.py — 方法参考脚本（BOPET 纵拉段示例）

⚠️ v8.0 说明：此脚本为方法学参考，不直接运行。
Agent 根据 Step 0 的数据理解结果，自行决定分析策略并编写分析代码。
此脚本提供以下可复用的方法学：
  - 高频时序批次窗口切片 + 动态特征提取
  - 12维度全特征关联展开（{param}@{dimension}）
  - 产品分层Spearman/Pearson关联
  - 去趋势分析

适用场景: 有高频时序+批次标签的数据（如BOPET薄膜生产）。
其他场景（CNC单件记录、事件日志等）Agent应自行编写适配的分析代码。

核心策略：
1. 加载高频时序数据(30s间隔) + 批次缺陷数据
2. 按批次窗口切片，提取每个批次内的时序动态特征
3. 批次级特征与缺陷关联分析
4. 物理过程分段对齐分析
5. 输出结构化JSON供下游Agent解读

Usage:
  python3 deep_analyze.py \
    --timeseries data/merged_process_data.csv \
    --batches data/aligned_multidefect.csv \
    --params data/parameter_mapping.json \
    --output workspace/analysis_output.json
"""

import argparse
import json
import sys
import math
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
import csv

# ═══════════════════════════════════════════════════════════
#  数据加载
# ═══════════════════════════════════════════════════════════

def load_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════
#  批次-时序对齐：将高频时序数据按批次时间窗口切片
# ═══════════════════════════════════════════════════════════

def align_batches_with_timeseries(ts_rows, batches, time_col='time'):
    """将高频时序数据按批次起止时间切片，返回 {batch_id: [rows]}"""
    ts_times = []
    for row in ts_rows:
        try:
            ts_times.append(datetime.strptime(row[time_col], '%Y-%m-%d %H:%M:%S'))
        except (ValueError, KeyError):
            ts_times.append(None)

    batch_slices = {}
    for b in batches:
        try:
            t_start = datetime.strptime(b['ts_start'], '%Y-%m-%d %H:%M:%S')
            t_end = datetime.strptime(b['ts_end'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, KeyError):
            continue

        # 扩展窗口 ±5分钟以覆盖边界
        margin = timedelta(minutes=5)
        slice_rows = []
        for i, t in enumerate(ts_times):
            if t and (t_start - margin) <= t <= (t_end + margin):
                slice_rows.append(ts_rows[i])

        if len(slice_rows) >= 10:  # 至少5分钟数据
            batch_slices[b['batch_id']] = {
                'rows': slice_rows,
                'batch_info': b,
                'model': b.get('model', 'UNKNOWN').strip(),
                'n_points': len(slice_rows),
                'duration_minutes': (t_end - t_start).total_seconds() / 60
            }

    return batch_slices


# ═══════════════════════════════════════════════════════════
#  时序动态特征提取（每个批次内的参数行为）
# ═══════════════════════════════════════════════════════════

def safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def extract_timeseries_features(values):
    """从单个参数的时序切片中提取动态特征"""
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if len(clean) < 5:
        return None

    n = len(clean)
    mean = statistics.mean(clean)
    std = statistics.stdev(clean) if n >= 2 else 0
    cv = std / abs(mean) * 100 if mean != 0 else 0

    # 趋势：线性回归斜率
    t = list(range(n))
    slope, intercept = linear_regression(t, clean)
    trend_pct = (slope * n / mean * 100) if mean != 0 else 0  # 整个批次的趋势变化率

    # 变化点检测：基于滑动窗口均值的突变
    change_points = detect_change_points(clean, window=10)

    # 波动性：连续点间差的绝对值均值
    diffs = [abs(clean[i+1] - clean[i]) for i in range(n-1)]
    volatility = statistics.mean(diffs) if diffs else 0

    # 极值位置：最大/最小值出现的归一化时间位置
    max_pos = clean.index(max(clean)) / n if n > 0 else 0
    min_pos = clean.index(min(clean)) / n if n > 0 else 0

    # 自相关 lag-1（衡量平滑度/惯性）
    autocorr_lag1 = autocorrelation(clean, 1)

    return {
        'mean': round(mean, 4),
        'std': round(std, 4),
        'cv_pct': round(cv, 2),
        'min': round(min(clean), 4),
        'max': round(max(clean), 4),
        'range': round(max(clean) - min(clean), 4),
        'slope_per_step': round(slope, 6),
        'trend_pct': round(trend_pct, 2),
        'volatility': round(volatility, 4),
        'autocorr_lag1': round(autocorr_lag1, 4),
        'n_points': n,
        'change_points': change_points,
        'max_pos': round(max_pos, 3),
        'min_pos': round(min_pos, 3)
    }


def linear_regression(x, y):
    """最小二乘线性回归"""
    n = len(x)
    if n < 2:
        return 0, 0
    sx = sum(x)
    sy = sum(y)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    sx2 = sum(xi * xi for xi in x)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0, sy / n
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def detect_change_points(values, window=10, threshold_factor=3.0):
    """基于滑动窗口均值差的简单变点检测"""
    if len(values) < 2 * window:
        return []
    points = []
    for i in range(window, len(values) - window):
        left = values[i - window:i]
        right = values[i:i + window]
        left_mean = statistics.mean(left)
        right_mean = statistics.mean(right)
        left_std = statistics.stdev(left) if len(left) >= 2 else 0.1
        right_std = statistics.stdev(right) if len(right) >= 2 else 0.1
        pooled_std = math.sqrt(left_std ** 2 + right_std ** 2) / math.sqrt(2)
        if pooled_std < 0.001:
            pooled_std = 0.001
        t_stat = abs(left_mean - right_mean) / pooled_std
        if t_stat > threshold_factor:
            points.append({
                'position': i,
                'position_pct': round(i / len(values), 3),
                'left_mean': round(left_mean, 3),
                'right_mean': round(right_mean, 3),
                'jump': round(right_mean - left_mean, 3),
                't_stat': round(t_stat, 2)
            })
    # 去重：合并距离<5的相邻变点
    deduped = []
    for p in points:
        if not deduped or p['position'] - deduped[-1]['position'] > 5:
            deduped.append(p)
    return deduped


def autocorrelation(values, lag):
    """计算自相关系数"""
    n = len(values)
    if n <= lag:
        return 0
    mean = statistics.mean(values)
    if all(v == mean for v in values):
        return 0
    num = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(n - lag))
    den = sum((v - mean) ** 2 for v in values)
    return num / den if den != 0 else 0


# ═══════════════════════════════════════════════════════════
#  物理过程分段分析
# ═══════════════════════════════════════════════════════════

PROCESS_ZONES = {
    'preheat': {'rolls': [1, 2, 3, 4, 5], 'label': '预加热段(near Tg)', 'typical_temp': '~75°C'},
    'stretch': {'rolls': [6, 7, 8, 9, 10, 11], 'label': '拉伸段(above Tg)', 'typical_temp': '~82°C'},
    'quench':  {'rolls': [12, 13, 14, 15, 16, 17, 18], 'label': '急冷定型段(<< Tg)', 'typical_temp': '~35°C'}
}


def roll_to_zone(roll_num):
    """根据辊号返回物理分区"""
    for zone, info in PROCESS_ZONES.items():
        if roll_num in info['rolls']:
            return zone
    return 'unknown'


def extract_zone_features(batch_features, param_mapping):
    """按物理分区聚合温度特征"""
    zone_features = {}
    for zone, info in PROCESS_ZONES.items():
        roll_data = {}  # roll_num -> feature dict (one per roll)
        for roll in info['rolls']:
            prefix = f'MD_TH{roll:03d}'
            for pk, pf in batch_features.items():
                if pk == prefix:
                    if pf and roll not in roll_data:
                        roll_data[roll] = pf
                    break

        if roll_data:
            means = [t['mean'] for t in roll_data.values()]
            stds = [t['std'] for t in roll_data.values()]
            volatilities = [t['volatility'] for t in roll_data.values()]
            zone_features[zone] = {
                'label': info['label'],
                'temp_mean_avg': round(statistics.mean(means), 3),
                'temp_std_avg': round(statistics.mean(stds), 4),
                'temp_volatility_avg': round(statistics.mean(volatilities), 4),
                'temp_range': round(max(means) - min(means), 3),
                'n_rolls': len(roll_data),
                'individual': {f'roll_{r}': roll_data[r] for r in sorted(roll_data.keys())}
            }
    return zone_features


# ═══════════════════════════════════════════════════════════
#  批次级统计分析：时序特征 vs 缺陷关联
# ═══════════════════════════════════════════════════════════

def pearson_r(x, y):
    """Pearson相关系数"""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None and not math.isnan(a) and not math.isnan(b)]
    if len(pairs) < 3:
        return {'r': 0, 'n': len(pairs), 'p': 1}
    xs, ys = zip(*pairs)
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    den = math.sqrt(dx * dy)
    r = num / den if den != 0 else 0
    # t-test p-value
    t = r * math.sqrt((n - 2) / (1 - r ** 2 + 1e-12))
    # 近似 p（使用正态近似）
    p = 2 * (1 - normal_cdf(abs(t)))
    return {'r': round(r, 4), 'n': n, 'p': round(p, 4)}


def normal_cdf(x):
    """正态CDF近似"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def spearman_r(x, y):
    """Spearman秩相关"""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None and not math.isnan(a) and not math.isnan(b)]
    if len(pairs) < 3:
        return {'r': 0, 'n': len(pairs)}
    xs, ys = zip(*pairs)
    rx = rank_values(xs)
    ry = rank_values(ys)
    result = pearson_r(rx, ry)
    return result


def rank_values(vals):
    """排序取秩"""
    indexed = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0] * len(vals)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 2) / 2
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


SCALAR_DIMENSIONS = [
    'mean', 'std', 'cv_pct', 'min', 'max', 'range',
    'slope_per_step', 'trend_pct', 'volatility',
    'autocorr_lag1', 'max_pos', 'min_pos'
]


def compute_batch_level_correlations(batch_data, defect_types):
    """
    全维度关联：对每个参数的每个标量维度分别与缺陷计算相关。
    例如 MD_TH001 有 12 个维度（mean, slope, volatility 等），
    每个维度独立参与 Spearman/Pearson/去趋势分析。
    """
    # 收集参数名（原始列名）
    param_names = set()
    for bd in batch_data.values():
        param_names.update(bd.get('timeseries_features', {}).keys())
    param_names = sorted(param_names)

    # 展开为 {param}@{dimension} 标量值
    def get_expanded_features(bd):
        feats = {}
        for param in param_names:
            pf = bd.get('timeseries_features', {}).get(param)
            if not pf:
                continue
            for dim in SCALAR_DIMENSIONS:
                val = pf.get(dim)
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
                    feats[f'{param}@{dim}'] = val
        return feats

    expanded_keys = set()
    for bd in batch_data.values():
        expanded_keys.update(get_expanded_features(bd).keys())
    expanded_keys = sorted(expanded_keys)

    results = {
        'defect_correlations': {},
        'defect_cooccurrence': {},
        'product_stratified': {},
        'top_predictors': {},
        'interaction_effects': []
    }

    # 1. 缺陷-特征全维度相关
    for defect in defect_types:
        defect_vals = {}
        for bid, bd in batch_data.items():
            d = bd['batch_info'].get(defect)
            if d is not None:
                defect_vals[bid] = safe_float(d)

        corr_list = []
        for feat_key in expanded_keys:
            param, dim = feat_key.rsplit('@', 1)
            feat_vals = {}
            for bid, bd in batch_data.items():
                pf = bd.get('timeseries_features', {}).get(param)
                if pf:
                    v = pf.get(dim)
                    if v is not None and not (isinstance(v, float) and math.isnan(v)):
                        feat_vals[bid] = v

            common = [bid for bid in defect_vals if bid in feat_vals
                       and defect_vals[bid] is not None and feat_vals[bid] is not None]
            if len(common) < 10:
                continue

            x = [feat_vals[bid] for bid in common]
            y = [defect_vals[bid] for bid in common]

            p = pearson_r(x, y)
            s = spearman_r(x, y)
            det = detrended_check(x, y)

            corr_list.append({
                'feature': feat_key,
                'parameter': param,
                'dimension': dim,
                'pearson_r': p['r'],
                'pearson_p': p['p'],
                'spearman_r': s['r'],
                'n': p['n'],
                'detrended_r': det['detrended_r'],
                'attenuation_pct': det['attenuation_pct'],
                'trend_confounded': det['trend_confounded']
            })

        corr_list.sort(key=lambda c: abs(c['spearman_r']), reverse=True)
        results['defect_correlations'][defect] = corr_list[:30]
        results['top_predictors'][defect] = corr_list[:10]

    # 2. 缺陷共现矩阵
    for d1 in defect_types:
        results['defect_cooccurrence'][d1] = {}
        for d2 in defect_types:
            if d1 >= d2:
                continue
            x, y = [], []
            for bd in batch_data.values():
                v1 = safe_float(bd['batch_info'].get(d1))
                v2 = safe_float(bd['batch_info'].get(d2))
                if v1 is not None and v2 is not None:
                    x.append(v1)
                    y.append(v2)
            if len(x) >= 5:
                s = spearman_r(x, y)
                results['defect_cooccurrence'][d1][d2] = s['r']

    # 3. 分产品分层分析（全维度）
    by_product = defaultdict(list)
    for bid, bd in batch_data.items():
        by_product[bd['model']].append(bid)

    for defect in defect_types:
        results['product_stratified'][defect] = {}
        for product, bids in by_product.items():
            if len(bids) < 8:
                continue
            for feat_key in expanded_keys:
                param, dim = feat_key.rsplit('@', 1)
                x, y = [], []
                for bid in bids:
                    pf = batch_data[bid].get('timeseries_features', {}).get(param)
                    dv = safe_float(batch_data[bid]['batch_info'].get(defect))
                    if pf and dv is not None:
                        v = pf.get(dim)
                        if v is not None and not (isinstance(v, float) and math.isnan(v)):
                            x.append(v)
                            y.append(dv)
                if len(x) >= 5:
                    s = spearman_r(x, y)
                    if feat_key not in results['product_stratified'][defect]:
                        results['product_stratified'][defect][feat_key] = {}
                    results['product_stratified'][defect][feat_key][product] = {
                        'r': s['r'],
                        'n': len(x)
                    }

    return results


def detrended_check(x, y):
    """去趋势相关检查"""
    n = len(x)
    if n < 5:
        return {'detrended_r': 0, 'attenuation_pct': 0, 'trend_confounded': False}

    t = list(range(n))
    sx, bx = linear_regression(t, x)
    sy, by = linear_regression(t, y)
    x_resid = [x[i] - (sx * i + bx) for i in range(n)]
    y_resid = [y[i] - (sy * i + by) for i in range(n)]

    raw = pearson_r(x, y)
    det = pearson_r(x_resid, y_resid)

    atten = ((raw['r'] - det['r']) / abs(raw['r']) * 100) if raw['r'] != 0 else 0

    return {
        'detrended_r': det['r'],
        'attenuation_pct': round(atten, 1),
        'trend_confounded': abs(atten) > 50
    }


# ═══════════════════════════════════════════════════════════
#  变点检测：跨批次的时间趋势分析
# ═══════════════════════════════════════════════════════════

def cross_batch_change_detection(batch_data, param_cols):
    """检测跨批次的关键参数变化点（可能是产品切换或工艺调整）"""
    # 按时间排序批次
    sorted_batches = sorted(batch_data.items(), key=lambda x: x[1]['batch_info'].get('ts_start', ''))

    transitions = []
    for i in range(1, len(sorted_batches)):
        bid_prev, bd_prev = sorted_batches[i - 1]
        bid_curr, bd_curr = sorted_batches[i]

        # 产品切换检测
        model_prev = bd_prev['model']
        model_curr = bd_curr['model']
        is_product_switch = model_prev != model_curr

        # 参数跳变检测
        param_jumps = {}
        prev_feats = bd_prev.get('timeseries_features', {})
        curr_feats = bd_curr.get('timeseries_features', {})
        for key in set(prev_feats.keys()) & set(curr_feats.keys()):
            pf = prev_feats[key]
            cf = curr_feats[key]
            if pf and cf and pf['mean'] != 0:
                jump_pct = (cf['mean'] - pf['mean']) / abs(pf['mean']) * 100
                if abs(jump_pct) > 5:  # 超过5%的跳变
                    param_jumps[key] = round(jump_pct, 2)

        if is_product_switch or any(abs(v) > 15 for v in param_jumps.values()):
            transitions.append({
                'from_batch': bid_prev,
                'to_batch': bid_curr,
                'from_model': model_prev,
                'to_model': model_curr,
                'is_product_switch': is_product_switch,
                'timestamp': bd_curr['batch_info'].get('ts_start'),
                'param_jumps': dict(sorted(param_jumps.items(), key=lambda x: abs(x[1]), reverse=True)[:10])
            })

    return transitions


# ═══════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='BOPET深度时序分析引擎')
    parser.add_argument('--timeseries', required=True, help='高频时序CSV路径')
    parser.add_argument('--batches', required=True, help='批次缺陷CSV路径')
    parser.add_argument('--params', default=None, help='参数映射JSON路径')
    parser.add_argument('--output', required=True, help='输出JSON路径')
    parser.add_argument('--scratch-data', default=None, help='划伤缺陷CSV路径（可选）')
    args = parser.parse_args()

    print("[1/7] 加载数据...")
    ts_rows = load_csv(args.timeseries)
    batches = load_csv(args.batches)
    param_mapping = load_json(args.params) if args.params else {}

    defect_types = ['film_points', 'oligomer', 'dust', 'bubbles', 'melt_spots']

    # 获取时序数据中的参数列（排除time）
    ts_cols = [c for c in ts_rows[0].keys() if c != 'time']
    print(f"  时序数据: {len(ts_rows)}行 × {len(ts_cols)}参数, 间隔30s")
    print(f"  批次数据: {len(batches)}批次 × {len(defect_types)}缺陷类型")

    print("[2/7] 批次-时序对齐...")
    batch_slices = align_batches_with_timeseries(ts_rows, batches)
    print(f"  成功对齐: {len(batch_slices)}/{len(batches)}批次")

    if len(batch_slices) < 5:
        print(f"  WARNING: 仅{len(batch_slices)}批次可对齐，统计功效有限")

    print("[3/7] 提取批次内时序动态特征...")
    for bid, bd in batch_slices.items():
        features = {}
        for col in ts_cols:
            values = [safe_float(row[col]) for row in bd['rows']]
            feat = extract_timeseries_features(values)
            if feat:
                features[col] = feat
        bd['timeseries_features'] = features

    # 统计已提取特征数
    sample_bid = next(iter(batch_slices))
    n_features = len(batch_slices[sample_bid].get('timeseries_features', {}))
    print(f"  每批次提取 {n_features} 参数 × 14 动态特征")

    print("[4/7] 物理过程分段分析...")
    for bid, bd in batch_slices.items():
        bd['zone_features'] = extract_zone_features(
            bd.get('timeseries_features', {}), param_mapping
        )

    print("[5/7] 批次级关联分析...")
    correlations = compute_batch_level_correlations(batch_slices, defect_types)

    # 输出统计摘要（显示维度信息）
    for defect in defect_types:
        top = correlations['top_predictors'].get(defect, [])
        if top:
            best = top[0]
            dim = best.get('dimension', 'mean')
            print(f"  {defect}: top = {best['feature']} (Sp={best['spearman_r']:.3f}, r={best['pearson_r']:.3f}, dim={dim})")

    print("[6/7] 变点检测...")
    transitions = cross_batch_change_detection(batch_slices, ts_cols)
    n_switches = sum(1 for t in transitions if t['is_product_switch'])
    print(f"  检测到 {len(transitions)} 个过渡点（其中 {n_switches} 个产品切换）")

    print("[7/7] 输出结构化结果...")
    output = {
        'meta': {
            'engine': 'deep_analyze.py v7.0',
            'timestamp': datetime.now().isoformat(),
            'n_timeseries_rows': len(ts_rows),
            'n_batches_total': len(batches),
            'n_batches_aligned': len(batch_slices),
            'n_params': len(ts_cols),
            'defect_types': defect_types,
            'ts_interval': '30s',
            'ts_time_range': {
                'start': ts_rows[0].get('time', ''),
                'end': ts_rows[-1].get('time', '')
            }
        },
        'batch_inventory': {
            bid: {
                'model': bd['model'],
                'n_points': bd['n_points'],
                'duration_minutes': round(bd['duration_minutes'], 1),
                'n_features': len(bd.get('timeseries_features', {})),
                'defects': {d: safe_float(bd['batch_info'].get(d)) for d in defect_types},
                'zone_features': bd.get('zone_features', {})
            }
            for bid, bd in batch_slices.items()
        },
        'correlations': correlations,
        'transitions': transitions,
        'feature_catalog': {
            'dynamic_features': SCALAR_DIMENSIONS,
            'correlation_expansion': '每个参数展开为 {param}@{dim} 关联对，共12个标量维度独立参与关联分析',
            'description': {
                'mean': '批内均值',
                'std': '批内标准差',
                'cv_pct': '变异系数(%)',
                'slope_per_step': '线性趋势斜率(每30s变化) — 检测批内参数漂移',
                'trend_pct': '趋势变化率(%) — 漂移占均值的比例',
                'volatility': '波动性(相邻点差均值) — 高频波动强度',
                'autocorr_lag1': 'lag-1自相关 — 过程惯性/控制品质',
                'max_pos': '最大值归一化位置(0=开始,1=结束)',
                'min_pos': '最小值归一化位置'
            }
        }
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n输出完成: {args.output}")
    print(f"  批次详情: {len(output['batch_inventory'])} 批次")
    print(f"  相关分析: {len(correlations['defect_correlations'])} 缺陷类型")
    print(f"  过渡点: {len(transitions)}")

    # 输出快速摘要
    print("\n═══════════════════════════════════════")
    print("快速诊断摘要")
    print("═══════════════════════════════════════")
    for defect in defect_types:
        top3 = correlations['top_predictors'].get(defect, [])[:3]
        if top3:
            print(f"\n{defect} Top 3 预测因子:")
            for c in top3:
                flag = ""
                if c['trend_confounded']:
                    flag += " [趋势混杂]"
                if abs(c['pearson_r']) > 0.3 and abs(c['spearman_r']) < 0.15:
                    flag += " [离 outlier驱动]"
                dim = c.get('dimension', '?')
                print(f"  {c['feature']} [{dim}]: Sp={c['spearman_r']:.3f} r={c['pearson_r']:.3f} det={c['detrended_r']:.3f}{flag}")


if __name__ == '__main__':
    main()
