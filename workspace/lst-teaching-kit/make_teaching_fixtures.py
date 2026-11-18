# -*- coding: utf-8 -*-
"""产线稳定性报告教学套件 —— 7 个不同格式/场景的演示数据（确定性合成）。

T1 水泥球磨机   XLSX      + 本体 + report_context   （完整示范）
T2 污水曝气池   TSV       无 context                （最简路径）
T3 注塑机       JSON      + report_context          （spec/质检列教学）
T4 食品烘干线   Parquet   无 context                （健康基线对照）
T5 空压机站     GBK CSV   死点数值通道              （编码回退+时间不变量教学）
T6 冶金加热炉   CSV       秒级时间戳+英文表头       （时间解析教学）
T7 涂装线       CSV       仅 30 行                  （not_assessable 诚实降级教学）

Run:  uv run --project .claude/shared/scripts python make_teaching_fixtures.py
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def _contained(path: Path) -> Path:
    if ".." in path.parts:
        raise ValueError(f"path must not contain '..': {path}")
    resolved = path.resolve()
    if ROOT not in resolved.parents:
        raise ValueError(f"path outside fixture root: {resolved}")
    return resolved


def _save(df: pd.DataFrame, rel: str, **kw) -> None:
    path = _contained(ROOT / rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        df.to_excel(path, index=False, engine="openpyxl")
    elif suffix == ".tsv":
        kw.setdefault("sep", "\t")
        df.to_csv(path, index=False, **kw)
    elif suffix == ".json":
        c0 = df.columns[0]
        path.write_text(json.dumps(
            [{c0: r[0], **{c: r[i] for i, c in enumerate(df.columns[1:], 1)}}
             for r in df.itertuples(index=False, name=None)],
            ensure_ascii=False, indent=1), encoding="utf-8")
    elif suffix == ".parquet":
        df.to_parquet(path, index=False, engine="pyarrow")
    else:
        df.to_csv(path, index=False, **kw)
    print(f"  wrote {rel} ({len(df)} rows)")


def _ts(start: str, n: int, step_h: float = 1.0) -> list[str]:
    t0 = datetime.fromisoformat(start)
    return [(t0 + timedelta(hours=step_h * i)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(n)]


def ar1(rng, n, sigma, rho=0.3):
    e = rng.normal(0, sigma, n)
    for i in range(1, n):
        e[i] += rho * e[i - 1]
    return e


# -------------------------------------------------- T1 水泥球磨机 (XLSX)
def t1_cement():
    rng = np.random.default_rng(701)
    n = 180
    t = np.arange(n)
    bearing = 62.0 + 0.05 * np.clip(t - 72, 0, None) + ar1(rng, n, 0.35)
    current = 245 + 1.9 * (bearing - 62) + ar1(rng, n, 1.6)
    feed = 128 + ar1(rng, n, 1.8)
    separator = 1180 + ar1(rng, n, 6)
    noise_db = 86 - 0.12 * (bearing - 62) + ar1(rng, n, 0.4)
    blaine = 3480 - 1.1 * (bearing - 62) + ar1(rng, n, 9)
    output = 142 + ar1(rng, n, 1.1)
    df = pd.DataFrame({
        "时间": _ts("2026-09-01 00:00:00", n),
        "磨机电流": np.round(current, 1),
        "主轴承温度": np.round(bearing, 2),
        "入磨喂料量": np.round(feed, 1),
        "选粉机转速": np.round(separator, 0),
        "磨音": np.round(noise_db, 2),
        "比表面积": np.round(blaine, 0),
        "台时产量": np.round(output, 1),
    })
    _save(df, "T1_cement_mill/00_input/mill_7d.xlsx")


# -------------------------------------------------- T2 污水曝气池 (TSV)
def t2_wastewater():
    rng = np.random.default_rng(702)
    n = 144
    t = np.arange(n)
    do = 3.2 - 0.006 * t + ar1(rng, n, 0.08)          # DO 缓降 ≈0.86%/天
    blower = 42 + 0.045 * t + ar1(rng, n, 0.15)       # 频率补偿上升
    mlss = 3.8 + ar1(rng, n, 0.12)
    cod_in = 420 + 25 * np.sin(2 * np.pi * t / 24) + ar1(rng, n, 9)
    nh3 = 4.2 + 0.02 * np.clip(t - 96, 0, None) + ar1(rng, n, 0.15)
    df = pd.DataFrame({
        "时间": _ts("2026-09-05 00:00:00", n),
        "溶解氧DO": np.round(do, 3),
        "鼓风机频率": np.round(blower, 2),
        "MLSS浓度": np.round(mlss, 3),
        "进水COD": np.round(cod_in, 1),
        "出水氨氮": np.round(nh3, 3),
    })
    _save(df, "T2_wastewater_aeration/00_input/aeration_6d.tsv", sep="\t")


# -------------------------------------------------- T3 注塑机 (JSON)
def t3_injection():
    rng = np.random.default_rng(703)
    n = 120
    t = np.arange(n)
    hold = 68.5 + np.sin(2 * np.pi * t / 20) * 2.6 + ar1(rng, n, 0.35)
    melt = 265 + ar1(rng, n, 0.8)
    clamp = 1080 + ar1(rng, n, 4)
    cycle = 38.5 + ar1(rng, n, 0.12)
    weight = 25.0 + 0.045 * (hold - 68.5) + ar1(rng, n, 0.02)
    df = pd.DataFrame({
        "模次时间": _ts("2026-09-08 06:00:00", n, step_h=0.25),
        "保压压力": np.round(hold, 2),
        "熔体温度": np.round(melt, 1),
        "锁模力": np.round(clamp, 0),
        "循环时间": np.round(cycle, 2),
        "单件重量": np.round(weight, 3),
    })
    _save(df, "T3_injection_molding/00_input/shots_30h.json")


# -------------------------------------------------- T4 食品烘干线 (Parquet, 健康)
def t4_dryer():
    rng = np.random.default_rng(704)
    n = 168
    df = pd.DataFrame({
        "时间": _ts("2026-09-01 00:00:00", n),
        "烘干温度": np.round(82.0 + ar1(rng, n, 0.15, rho=0.05), 2),
        "排湿风机频率": np.round(46.0 + ar1(rng, n, 0.10, rho=0.05), 2),
        "网带速度": np.round(12.5 + ar1(rng, n, 0.02, rho=0.05), 3),
        "出料水分": np.round(7.2 + ar1(rng, n, 0.035, rho=0.05), 3),
        "水分活度": np.round(0.58 + ar1(rng, n, 0.0022, rho=0.05), 4),
    })
    _save(df, "T4_food_dryer/00_input/dryer_7d.parquet")


# -------------------------------------------------- T5 空压机站 (GBK CSV + 死点)
def t5_compressor():
    rng = np.random.default_rng(705)
    n = 120
    t = np.arange(n)
    p1 = 0.72 + 0.03 * np.abs(np.sin(2 * np.pi * t / 8)) + ar1(rng, n, 0.004)
    load = 62 + 8 * np.abs(np.sin(2 * np.pi * t / 8 + 1.2)) + ar1(rng, n, 0.8)
    p2 = 0.70 + ar1(rng, n, 0.005)
    i2 = 96 + 0.28 * np.clip(t - 48, 0, None) + ar1(rng, n, 0.7)  # 电流缓升
    header = 0.65 + 0.02 * np.sin(2 * np.pi * t / 8 + 0.6) + ar1(rng, n, 0.003)
    df = pd.DataFrame({
        "时间": _ts("2026-09-10 00:00:00", n),
        "1号机组排气压力": np.round(p1, 4),
        "1号机组加载率": np.round(load, 2),
        "2号机组排气压力": np.round(p2, 4),
        "2号机组电机电流": np.round(i2, 1),
        "母管压力": np.round(header, 4),
        "油位传感器显示": np.zeros(n),              # 死点：全程恒 0
    })
    _save(df, "T5_air_compressor/00_input/station_5d.csv", encoding="gb18030")


# -------------------------------------------------- T6 冶金加热炉 (秒级时间戳+英文)
def t6_furnace():
    rng = np.random.default_rng(706)
    n = 160
    t0 = int(datetime(2026, 9, 12, 0, 0).timestamp())
    ts = [t0 + 1800 * i for i in range(n)]
    hour = np.array([(1800 * i // 3600) % 24 for i in range(n)])
    night = ((hour >= 0) & (hour < 8)).astype(float)     # 0-8 点夜班
    z2 = 1120 - 8.0 * night + ar1(rng, n, 2.2)
    z1 = 1050 + ar1(rng, n, 2.0)
    soak = np.round(96 - 1.5 * night + ar1(rng, n, 0.8)).astype(int)
    exit_t = 868 + 0.82 * (z2 - 1120) + 0.35 * (z1 - 1050) + ar1(rng, n, 1.4)
    scale = 0.86 + 0.0004 * (exit_t - 868) + ar1(rng, n, 0.02)
    df = pd.DataFrame({
        "timestamp": ts,
        "zone1_temp_c": np.round(z1, 1),
        "zone2_temp_c": np.round(z2, 1),
        "soak_time_s": soak,
        "billet_exit_temp_c": np.round(exit_t, 1),
        "scale_loss_pct": np.round(scale, 4),
    })
    _save(df, "T6_reheating_furnace/00_input/furnace_80h.csv")


# -------------------------------------------------- T7 涂装线 (30 行, 不足)
def t7_coating():
    rng = np.random.default_rng(707)
    n = 30
    df = pd.DataFrame({
        "时间": _ts("2026-09-14 08:00:00", n),
        "喷房温度": np.round(23.5 + ar1(rng, n, 0.4), 2),
        "链速": np.round(3.2 + ar1(rng, n, 0.03), 3),
        "膜厚": np.round(28.0 + ar1(rng, n, 0.6), 2),
    })
    _save(df, "T7_coating_too_few_rows/00_input/coating_30rows.csv")


if __name__ == "__main__":
    t1_cement()
    t2_wastewater()
    t3_injection()
    t4_dryer()
    t5_compressor()
    t6_furnace()
    t7_coating()
    print("teaching fixtures written under", ROOT)
