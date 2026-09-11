#!/usr/bin/env python3
"""TEP (Tennessee Eastman Process) 经典 Braatz 数据准备脚本。

把 data/benchmark/tep_braatz_classic/d*_te.dat (空格分隔, 960x52, 无表头)
转换为诊断系统可直接上传的 CSV：timestamp + XMEAS_1..41 + XMV_1..11。

采样约定（Downs & Vogel 1993 / Rieth et al. 2017 官方描述）：
- 采样间隔 3 分钟；testing 文件 960 行 = 48 小时
- 故障在 testing 文件第 161 行（8h）注入（normal d00_te 无故障）

用法:
    python prep_tep.py --src ../../../data/benchmark/tep_braatz_classic \
                       --out ../../../data/benchmark/prepared/tep \
                       --faults d00_te,d01_te,d04_te,d07_te,d11_te,d14_te,d21_te
"""
import argparse
import csv
import datetime as dt
from pathlib import Path

HEADER = [f"XMEAS_{i}" for i in range(1, 42)] + [f"XMV_{i}" for i in range(1, 12)]
T0 = dt.datetime(2020, 1, 1, 0, 0, 0)
INTERVAL = dt.timedelta(minutes=3)
FAULT_ONSET_ROW = 160  # 0-indexed; 第 161 个样本 = 8h


def convert_one(dat_path: Path, out_path: Path) -> dict:
    rows = []
    for line in dat_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        vals = [float(v) for v in line.split()]
        if len(vals) != 52:
            raise ValueError(f"{dat_path.name}: expect 52 cols, got {len(vals)}")
        rows.append(vals)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp"] + HEADER)
        for i, vals in enumerate(rows):
            ts = (T0 + i * INTERVAL).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([ts] + vals)

    return {
        "file": out_path.name,
        "source": dat_path.name,
        "rows": len(rows),
        "cols": 53,
        "sampling": "3min",
        "duration_hours": len(rows) * 3 / 60,
        "fault_onset": (T0 + FAULT_ONSET_ROW * INTERVAL).strftime("%Y-%m-%d %H:%M:%S")
        if dat_path.stem.startswith("d") and dat_path.stem[1:3].isdigit() and dat_path.stem != "d00_te"
        else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--faults", default="d00_te,d01_te,d04_te,d07_te,d11_te,d14_te,d21_te")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in args.faults.split(","):
        dat = src / f"{name}.dat"
        info = convert_one(dat, out / f"{name}.csv")
        manifest.append(info)
        print(f"converted {dat.name} -> {info['file']} ({info['rows']} rows)")
    (out / "_manifest.json").write_text(str(manifest).replace("'", '"'), encoding="utf-8")
    print(f"manifest -> {out / '_manifest.json'}")


if __name__ == "__main__":
    main()
