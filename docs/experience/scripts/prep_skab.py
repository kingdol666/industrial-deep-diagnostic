#!/usr/bin/env python3
"""SKAB (Skoltech Anomaly Benchmark) 数据准备脚本。

把 data/benchmark/skab/data/**/*.csv (分号分隔, 含 anomaly/changepoint 标签列)
转换为诊断系统输入 CSV（timestamp + 8 传感器列，剥离标签列），
并生成每文件根因真值清单 ground_truth.json / ground_truth.md。

真值依据: SKAB 官方仓库 data/README.md（每个文件单一人工注入异常）。

用法:
    python prep_skab.py --src ../../../data/benchmark/skab/data \
                        --out ../../../data/benchmark/prepared/skab
"""
import argparse
import csv
import json
from pathlib import Path

ANOMALY_BY_PATH = {
    "valve1": "泵入口流量阀门关闭（valve at flow inlet to pump partially closed）",
    "valve2": "泵出口阀门关闭（valve at outlet of flow from pump closed）",
}
ANOMALY_BY_FILE = {
    ("other", "1"): "流体泄漏/添加模拟（fluid leaks and additions）",
    ("other", "2"): "流体泄漏/添加模拟（fluid leaks and additions）",
    ("other", "3"): "流体泄漏/添加模拟（fluid leaks and additions）",
    ("other", "4"): "流体泄漏/添加模拟（fluid leaks and additions）",
    ("other", "5"): "转子不平衡·尖锐行为（sharply rotor imbalance）",
    ("other", "6"): "转子不平衡·线性行为（linear rotor imbalance）",
    ("other", "7"): "转子不平衡·阶跃行为（step rotor imbalance）",
    ("other", "8"): "转子不平衡·Dirac 冲激行为（Dirac delta rotor imbalance）",
    ("other", "9"): "转子不平衡·指数行为（exponential rotor imbalance）",
    ("other", "10"): "回路水量缓慢增加（slow increase of water in circuit）",
    ("other", "11"): "回路水量突然增加（sudden increase of water in circuit）",
    ("other", "12"): "排水至气蚀（draining water from tank until cavitation）",
    ("other", "13"): "泵入口两相流→气蚀（two-phase flow supply to pump inlet, cavitation）",
    ("other", "14"): "高温供水（water supply of increased temperature）",
}


def ground_truth_for(rel_parts):
    folder = rel_parts[0]
    stem = rel_parts[1]
    if folder == "anomaly-free":
        return "正常工况（anomaly-free baseline）", "NORMAL"
    if folder in ANOMALY_BY_PATH:
        return ANOMALY_BY_PATH[folder], "VALVE_CLOSURE"
    if (folder, stem) in ANOMALY_BY_FILE:
        return ANOMALY_BY_FILE[(folder, stem)], "OTHER"
    return "未知", "UNKNOWN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for csv_path in sorted(src.rglob("*.csv")):
        rel = csv_path.relative_to(src)
        parts = list(rel.parts[:-1]) + [rel.stem]
        desc, category = ground_truth_for(parts)
        out_name = f"{'_'.join(rel.parts[:-1])}_{rel.stem}.csv"
        out_path = out / out_name

        with csv_path.open(encoding="utf-8") as f, out_path.open("w", newline="", encoding="utf-8") as g:
            reader = csv.reader(f, delimiter=";")
            writer = csv.writer(g)
            header = next(reader)
            keep = [i for i, h in enumerate(header) if h not in ("anomaly", "changepoint")]
            writer.writerow([header[i] for i in keep])
            n_anom = 0
            n_rows = 0
            first_anom_ts = None
            for row in reader:
                if not row:
                    continue
                n_rows += 1
                writer.writerow([row[i] for i in keep])
                if "anomaly" in header and row[header.index("anomaly")] in ("1", "1.0"):
                    n_anom += 1
                    if first_anom_ts is None:
                        first_anom_ts = row[header.index("datetime")]
        manifest.append({
            "file": out_name,
            "source": str(rel).replace("\\", "/"),
            "rows": n_rows,
            "anomaly_points": n_anom,
            "first_anomaly_ts": first_anom_ts,
            "ground_truth": desc,
            "category": category,
        })
        print(f"{out_name}: {n_rows} rows, {n_anom} anomalous, truth={desc[:40]}")
    (out / "ground_truth.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest -> {out / 'ground_truth.json'} ({len(manifest)} files)")


if __name__ == "__main__":
    main()
