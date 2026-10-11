# -*- coding: utf-8 -*-
"""BOPET 双拉产线演示数据生成器（确定性，seed=42）。

以乐凯 FW3 快照的真实工艺窗口为基准，仿真 10 天逐小时数据，导出两张表：
  bopet_demo_setpoint.csv  设定值表（配方记录，含一次有意的提产改设定）
  bopet_demo_actual.csv    实际值表（PV = 设定值 + 回路噪声 + 事件）

注入的事件（分析报告应能分别检出）：
  E1 提产改设定  hour 144 起：纵拉拉伸速度设定 52.9 → 53.4 m/min（+0.95%）
                 → 实际值跟随阶跃，薄膜厚度 −1% 左右，牵引张力 +18 N
  E2 加热器老化  hour 96 起：TDO 拉伸区温度 CX4 实际值缓慢漂移 +1.8℃（设定不变）
  E3 滤器堵孔    hour 160-163 / 171-174 / 182-184：熔体压力尖峰 +2.5~4 bar
  E4 质检联动    厚度响应速度阶跃；优品率响应 CX4 偏移与压力尖峰
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(42)

OUT = "data/bopet_demo"
N = 240  # 小时
t0 = pd.Timestamp("2026-10-01 00:00")
t = pd.date_range(t0, periods=N, freq="h")
hour = np.arange(N)


def ar1(n, sigma, phi=0.6, rng=rng):
    """一阶自回归噪声：回路 PV 的现实形态（相邻采样相关，不是白噪声）。"""
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


# ── 设定值（配方） ────────────────────────────────────────────────
sp = {
    "主挤计量段温度": np.full(N, 282.0),
    "熔体压力": np.full(N, 110.0),
    "模头温度": np.full(N, 285.0),
    "铸片辊温度": np.full(N, 26.5),
    "铸片辊线速": np.full(N, 16.4),
    "纵拉预热辊温": np.full(N, 78.0),
    "纵拉拉伸速度": np.where(hour >= 144, 53.4, 52.9),   # E1: hour 144 提产
    "TDO拉伸区温度CX4": np.full(N, 240.0),
    "TDO定型区温度CX6": np.full(N, 191.0),
    "TDO出口轨宽": np.full(N, 6330.0),
    "TDO风机频率CX4": np.full(N, 85.0),
    "牵引入口张力": np.full(N, 2270.0),
}
sp_df = pd.DataFrame({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), **sp})
sp_df.to_csv(f"{OUT}/bopet_demo_setpoint.csv", index=False, encoding="utf-8-sig")

# ── 实际值（PV） ──────────────────────────────────────────────────
s3_sp = sp["纵拉拉伸速度"]
# E2: CX4 加热器老化漂移（hour 96 起 +1.8℃/144h），设定不变
cx4_drift = np.where(hour >= 96, (hour - 96) * (1.8 / 144), 0.0)
# E3: 熔体压力尖峰（滤器堵孔片段）
p_spike = np.zeros(N)
for a, b, amp in ((160, 163, 2.6), (171, 174, 3.8), (182, 184, 2.9)):
    p_spike[a:b + 1] += amp

cast_temp = sp["铸片辊温度"] + ar1(N, 0.10)
pv = {
    "主挤计量段温度": sp["主挤计量段温度"] + ar1(N, 0.12),
    # 压力 = 泵送与口模阻力的平衡；对速度阶跃有响应 + 尖峰片段
    "熔体压力": 110.0 + 0.6 * (s3_sp - 52.9) + ar1(N, 0.65, phi=0.7) + p_spike,
    "模头温度": sp["模头温度"] + ar1(N, 0.15),
    "铸片辊温度": cast_temp,
    "铸片辊线速": sp["铸片辊线速"] + ar1(N, 0.008),
    "纵拉预热辊温": sp["纵拉预热辊温"] + ar1(N, 0.12),
    # 速度回路跟随设定阶跃（2 小时过渡）
    "纵拉拉伸速度": s3_sp + ar1(N, 0.018)
                    + np.where(hour == 144, -0.06, 0.0) + np.where(hour == 145, -0.02, 0.0),
    "TDO拉伸区温度CX4": sp["TDO拉伸区温度CX4"] + cx4_drift + ar1(N, 0.14),
    "TDO定型区温度CX6": sp["TDO定型区温度CX6"] + ar1(N, 0.15),
    "TDO出口轨宽": sp["TDO出口轨宽"] + ar1(N, 0.6),
    "TDO风机频率CX4": sp["TDO风机频率CX4"] + ar1(N, 0.05),
    # 张力随速度阶跃重分配（E1 联动）
    "牵引入口张力": 2270.0 + 36.0 * (s3_sp - 52.9) + ar1(N, 5.5),
    # E4 质检：厚度 −1.15×Δ速度（≈ −1%/+1% 提产），铸片辊温微影响
    "薄膜厚度": 12.0 - 1.15 * ((s3_sp + ar1(N, 0.018)) - 52.9)
                + 0.05 * (cast_temp - 26.5) + rng.normal(0, 0.02, N),
    # 优品率：CX4 偏移（>0.4℃ 起罚）+ 压力尖峰时段 + 厚度偏离
    "优品率": np.clip(
        98.6 - 1.1 * np.maximum(0.0, cx4_drift - 0.4)
        - 1.4 * (p_spike > 0) * (0.6 + 0.1 * p_spike)
        - 2.0 * np.abs(12.0 - (12.0 - 1.15 * (s3_sp - 52.9))) + rng.normal(0, 0.12, N),
        92.0, 99.6),
}
pv_df = pd.DataFrame({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), **pv})
pv_df.to_csv(f"{OUT}/bopet_demo_actual.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_bopet_demo.py",
    "seed": 42,
    "rows": N,
    "period": [str(t[0]), str(t[-1])],
    "sampling": "1h",
    "files": {
        "setpoint": {"path": "bopet_demo_setpoint.csv", "sha256": sha(f"{OUT}/bopet_demo_setpoint.csv")},
        "actual": {"path": "bopet_demo_actual.csv", "sha256": sha(f"{OUT}/bopet_demo_actual.csv")},
    },
    "events": {
        "E1_提产改设定": "hour144 起纵拉拉伸速度设定 52.9→53.4（设定值表可见台阶；厚度 −1%、张力 +18N 跟随）",
        "E2_加热器老化": "hour96 起 CX4 实际值漂移 +1.8℃/144h（设定值不变 → 设备性问题）",
        "E3_滤器堵孔": "hour160-163/171-174/182-184 熔体压力尖峰 +2.6/3.8/2.9 bar",
        "E4_质检联动": "优品率响应 CX4 偏移与压力尖峰；厚度响应速度阶跃",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照（data/lekai-test）的典型运行值",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("setpoint rows:", len(sp_df), "actual rows:", len(pv_df))
for c in ("纵拉拉伸速度", "TDO拉伸区温度CX4", "熔体压力", "薄膜厚度", "优品率"):
    v = pv[c]
    print(f"  {c:14} {v.min():9.3f} ~ {v.max():9.3f}  CV={np.std(v)/abs(np.mean(v)):.3%}")
