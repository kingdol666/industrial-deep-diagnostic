#!/usr/bin/env python3
# dump_digests.py — 汇总一个 tier 文件全部 case 的 prepare_digest 统计证据（供诊断推理阅读）
# 用法: python dump_digests.py --tier scripts/benchmark/cases/tier2_main.json
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
tier_arg = args[args.index('--tier') + 1] if '--tier' in args else 'scripts/benchmark/cases/tier2_main.json'
tier = ROOT / tier_arg
tier_key = tier_arg.replace('\\', '/')

state = json.load((ROOT / 'results/benchmark/tier_state.json').open(encoding='utf-8'))
cases = state['tiers'][tier_key]['cases']

for cid, e in cases.items():
    rd = e.get('run_dir')
    if not rd:
        print(f'== {cid} — NOT PREPARED')
        continue
    d = json.load((Path(rd) / 'prepare_digest.json').open(encoding='utf-8'))
    print(f'== {cid}')
    print(f"   engine={d['engine']} rows={d['rows']} cols={d['cols']}")
    print('   anomalies:', ' | '.join(f"{a['col']}(z={a['max_abs_z']},{a['pct_z3']*100:.1f}%)" for a in d['anomaly_columns'][:5]))
    print('   top_pairs:', ' ; '.join(d['top_pairs'][:4]))
