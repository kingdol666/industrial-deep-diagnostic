#!/usr/bin/env python3
# make_tier2.py — 生成 tier2_main.json（29 场景：SKAB 16 / TEP 7 / IndPenSim 6）
#
# 真值来源（不进入管线可见输入，仅评分器使用）：
#   SKAB      → data/benchmark/prepared/skab/ground_truth.json（官方标签）
#   TEP       → Downs & Vogel 1993 / Chiang et al. 2001 教科书根因表（d21 unknown 已排除）
#   IndPenSim → 批次 91/93 为文档化工艺偏差批；batch 1/2 为正常对照
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'data' / 'benchmark' / 'prepared'
OUT = ROOT / 'scripts' / 'benchmark' / 'cases' / 'tier2_main.json'

# ── SKAB 官方标签 → 评分关键词 ──
SKAB_KEYS = [
    (lambda f: f.startswith('valve1'), ['valve', '阀', '入口', 'inlet', '节流', '关闭', 'flow inlet']),
    (lambda f: f.startswith('valve2'), ['valve', '阀', '出口', 'outlet', '关闭', 'flow outlet']),
    (lambda f: f in ('other_13', 'other_12'), ['cavitation', '气蚀', '两相', 'two-phase', '入口', 'inlet']),
    (lambda f: f in ('other_5', 'other_6', 'other_8'), ['imbalance', '不平衡', 'rotor', '转子']),
    (lambda f: f == 'other_1', ['leak', '泄漏', '流体', 'fluid', 'addition']),
    (lambda f: f == 'other_11', ['water', '水量', '增加', 'sudden', 'increase', '回路']),
    (lambda f: f == 'other_14', ['temperature', '高温', '供水', 'supply', '温度']),
]
SKAB_TARGETS = 'Pressure,Accelerometer1RMS'
SKAB_PROC = ('水循环试验台：水箱+离心泵+阀门闭环回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，'
             'Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，'
             'Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Flow RateRMS=回路流量(L/min)。1Hz 采样，回路封闭循环。')

cases = []
gt = json.load((PREP / 'skab' / 'ground_truth.json').open(encoding='utf-8'))
gt_by_file = {e['file'].replace('.csv', ''): e for e in gt}

skab_pick = ['valve1_1', 'valve1_7', 'valve1_12', 'valve2_0', 'valve2_2',
             'other_13', 'other_12', 'other_5', 'other_6', 'other_8',
             'other_1', 'other_11', 'other_14']
for name in skab_pick:
    e = gt_by_file[name]
    keys = next((k for cond, k in SKAB_KEYS if cond(name)), [])
    cases.append({
        'case_id': f'skab2_{name}', 'dataset': 'skab',
        'csv': f'data/benchmark/prepared/skab/{name}.csv',
        'time_col': 'datetime', 'target_cols': SKAB_TARGETS,
        'truth': f"{e['ground_truth']}（SKAB 官方标签，异常点 {e['anomaly_points']}/{e['rows']}）",
        'keywords': keys, 'expect_type_set': ['DETERMINED', 'COMPETING_SET'],
        'process_description': SKAB_PROC,
    })
cases.append({
    'case_id': 'skab2_normal_control', 'dataset': 'skab',
    'csv': 'data/benchmark/prepared/skab/anomaly-free_anomaly-free.csv',
    'time_col': 'datetime', 'target_cols': SKAB_TARGETS, 'control': True,
    'truth': '正常工况（SKAB anomaly-free 官方无异常基线）', 'keywords': [],
    'expect_type_set': ['NORMAL'], 'process_description': SKAB_PROC,
})

# ── TEP（教科书根因表：Downs & Vogel 1993；Chiang et al. 2001）──
TEP_PROC = ('Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。'
            'XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3 分钟采样，前 160 样本为正常闭环，之后注入扰动。')
TEP_FAULTS = {
    'd04': {'truth': 'IDV(4)：反应器冷却水入口温度阶跃', 'keys': ['cooling water', '冷却水', 'reactor', '反应器', '温度', 'step'],
            'targets': 'XMEAS_9,XMEAS_21'},
    'd07': {'truth': 'IDV(7)：C 段压头损失（C 进料 4 可用量减少，组成阶跃关联）', 'keys': ['c header', '压头', 'c feed', 'c 进料', 'stream 4', '压力'],
            'targets': 'XMEAS_4,XMEAS_23'},
    'd11': {'truth': 'IDV(11)：反应器冷却水入口温度随机波动', 'keys': ['cooling water', '冷却水', 'random', '随机', 'reactor', '波动'],
            'targets': 'XMEAS_9,XMEAS_21'},
    'd14': {'truth': 'IDV(14)：反应器冷却水阀粘滞（sticking）', 'keys': ['cooling water', '冷却水', 'valve', '阀', 'sticky', '粘滞'],
            'targets': 'XMEAS_9,XMEAS_21'},
}
for d, info in TEP_FAULTS.items():
    cases.append({
        'case_id': f'tep2_{d}', 'dataset': 'tep',
        'csv': f'data/benchmark/prepared/tep/{d}_te.csv',
        'time_col': 'timestamp', 'target_cols': info['targets'],
        'truth': info['truth'], 'keywords': info['keys'],
        'expect_type_set': ['DETERMINED', 'COMPETING_SET', 'NEEDS_DATA'],
        'process_description': TEP_PROC,
    })
cases.append({
    'case_id': 'tep2_d00_control', 'dataset': 'tep',
    'csv': 'data/benchmark/prepared/tep/d00_te.csv',
    'time_col': 'timestamp', 'target_cols': 'XMEAS_9,XMEAS_7', 'control': True,
    'truth': '正常工况（d00 无故障基线）', 'keywords': [],
    'expect_type_set': ['NORMAL'], 'process_description': TEP_PROC,
})

# ── IndPenSim（91/93 为文档化工艺偏差批；1/2 正常对照）──
IPS_TARGETS = 'Penicillin concentration(P:g/L),Dissolved oxygen concentration(DO2:mg/L)'
IPS_PROC = ('100,000L 青霉素补料分批发酵（IndPenSim）。列含流加率（Fs/Fa/Fb/Fc/Fh/Fw）、过程变量（pH/温度/产热/DO/OUR/CER）'
            '与产品浓度；Fault reference 列标记扰动窗口（本 case 排除该列，不进入分析）。500L/h 采样≈0.2h 间隔。')
ips_pick = [
    ('batch_091', 'data/benchmark/prepared/indpensim/batch_091.csv', False,
     '批次91工艺偏差故障（激活窗口 20-30.2h / 76-92.2h / 200-214.2h；曝气/流加类）',
     ['aeration', '曝气', 'do2', '溶氧', 'feed', '流加', 'ph', '工艺偏差', 'deviation']),
    ('batch_093', 'data/benchmark/prepared/indpensim_all/batch_093.csv', False,
     '批次93工艺偏差故障（激活窗口 70-90.2h；曝气/流加类）',
     ['aeration', '曝气', 'do2', '溶氧', 'feed', '流加', 'ph', '工艺偏差', 'deviation']),
    ('batch_001', 'data/benchmark/prepared/indpensim/batch_001.csv', True,
     '正常批次（batch 1，recipe 驱动正常批）', []),
    ('batch_002', 'data/benchmark/prepared/indpensim_all/batch_002.csv', True,
     '正常批次（batch 2，recipe 驱动正常批）', []),
]
for name, csv, control, truth, keys in ips_pick:
    c = {
        'case_id': f'ips2_{name}', 'dataset': 'indpensim', 'csv': csv,
        'time_col': 'Time (h)', 'target_cols': IPS_TARGETS, 'exclude_cols': 'Fault reference',
        'truth': truth, 'keywords': keys, 'expect_type_set': ['NORMAL' if control else 'DETERMINED', 'COMPETING_SET'],
        'process_description': IPS_PROC,
    }
    if control:
        c['control'] = True
    cases.append(c)

out = {'tier': 2, 'name': 'tier2_main', 'cases': cases}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
faults = sum(1 for c in cases if not c.get('control'))
controls = sum(1 for c in cases if c.get('control'))
print(f'tier2_main.json: {len(cases)} cases = {faults} fault + {controls} control')
from collections import Counter
print('by dataset:', dict(Counter(c['dataset'] for c in cases)))
