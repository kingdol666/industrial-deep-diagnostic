#!/usr/bin/env python3
"""IndPenSim 100 批次数据拆分脚本（已验证的文件布局）。

源文件: data/benchmark/indpensim/Mendeley_data/100_Batches_IndPenSim_V3.csv
  - 2,566 MB, 2,239 个表头列, 113,935 个数据行（数据行实际 2,237 字段）
  - 行块纵向堆叠：每批次一个连续行块（长度 895~1390 行不等），
    每行的 field[35] '2-PAT control(PAT_ref:PAT ref)' = 批次号 1..100（权威批次标识）
  - field[0..36]   : 过程变量命名列（Time (h) + 31 过程/标志变量）
  - field[31]      : Fault reference —— 故障激活时段标志（0/1，分布在批次 91-100 内）
  - field[37..38]  : 'Batch ID'/'Fault flag' 遗留脏列（数值上近似罐重，忽略）
  - field[39..2238]: 拉曼光谱通道（表头名 2400→201 递减的波数 cm⁻¹），诊断用不上

真值: 100_Batches_IndPenSim_Statistics.csv 的 Fault ref 列 —— 批次 91-100 为故障批次，
      1-90 正常；控制策略: 1-30 recipe / 31-60 operator / 61-90 Raman-APC。
      故障类型（曝气故障、pH 传感器漂移等）见 Goldrick et al. 2019 原文。

用法（流式单遍扫描，可拆全部 100 批）:
    python prep_indpensim.py --src ../../../data/benchmark/indpensim/Mendeley_data/100_Batches_IndPenSim_V3.csv \
                             --out ../../../data/benchmark/prepared/indpensim \
                             --batches 1,91,94,99
"""
import argparse
import csv
import json
from pathlib import Path

from pathlib import Path as _P

def _confined(x):
    """Normalize and confine write targets to this run's directory."""
    p = _P(x).resolve()
    p.relative_to(_P(__file__).resolve().parents[1])
    return p

KEEP_FIELDS = list(range(0, 32))  # Time + 30 过程变量 + Fault reference


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batches", default="1,91,94,99", help="逗号分隔批次号, 或 all")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    want = None if args.batches.strip() == "all" else {int(b) for b in args.batches.split(",")}

    handles = {}
    writers = {}
    summary = {}
    with open(args.src, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        names = [header[i] for i in KEEP_FIELDS]
        for row in reader:
            if len(row) < 36:
                continue
            batch_id = int(float(row[35]))
            if want is not None and batch_id not in want:
                continue
            if batch_id not in handles:
                fp = _confined(out / f"batch_{batch_id:03d}.csv").open("w", newline="", encoding="utf-8")
                handles[batch_id] = fp
                writers[batch_id] = csv.writer(fp)
                writers[batch_id].writerow(names)
                summary[batch_id] = {"rows": 0, "fault_active_points": 0,
                                     "fault_windows": [], "window_start": None,
                                     "t_min": None, "t_max": None}
            w = writers[batch_id]
            w.writerow([row[i] for i in KEEP_FIELDS])
            s = summary[batch_id]
            s["rows"] += 1
            t = float(row[0])
            s["t_min"] = t if s["t_min"] is None else min(s["t_min"], t)
            s["t_max"] = t if s["t_max"] is None else max(s["t_max"], t)
            if row[31].strip() == "1":
                s["fault_active_points"] += 1
                if s["window_start"] is None:
                    s["window_start"] = t
            elif s["window_start"] is not None:
                s["fault_windows"].append([s["window_start"], t])
                s["window_start"] = None
    for fp in handles.values():
        fp.close()
    for bid, s in summary.items():
        if s["window_start"] is not None:
            s["fault_windows"].append([s["window_start"], s["t_max"]])
        del s["window_start"]
        s["faulted_batch"] = bid >= 91
        print(f"batch {bid}: {s['rows']} rows, t=[{s['t_min']},{s['t_max']}]h, "
              f"fault_points={s['fault_active_points']}, windows={s['fault_windows']}")
    (out / "_indpensim_summary.json").write_text(
        json.dumps({"columns": names, "batches": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"summary -> {out / '_indpensim_summary.json'}")


if __name__ == "__main__":
    main()
