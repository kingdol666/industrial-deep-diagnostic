# -*- coding: utf-8 -*-
"""BC2 熔体过滤器压差锯齿 → 换网时机决策（确定性，seed=102）。

注入的信号：
  F1 压差锯齿   三个周期：换网后复位 ~26.5 bar，近似线性爬升至 ~72 bar 触发换网
                C1 速率 5.3 bar/天 → C2 5.7 → C3 7.5（新原料 PET-P2 杂质偏多）
  F2 联动效应   高压差段：计量泵电流 +0.09×ΔP；厚度 MD 波动 0.050→0.08 μm；
                优品率微降、破膜次数上升（ΔP>52 bar 起显著）
  F3 原料事件   08-26 09:00 新批次 PET-P2 投用（恰在 C3 起点，速率加倍的诱因）
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(102)

OUT = "data/bopet_cases/bc2_filter_dp_cycles"
N = 21 * 144  # 21 天 × 10 min
t = pd.date_range("2026-08-10 00:00", periods=N, freq="10min")
STEP = 1 / 144.0  # 天/采样


def ar1(n, sigma, phi=0.6, rng=rng):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


# ── 压差锯齿（分段构造：上一周期尾巴 → 复位 → C1 → C2 → C3） ────────
TRIG = 72.0
RESET = 26.5
rates = [5.3, 5.7, 7.5]           # bar/天
bounds = [32]                     # 08-10 05:20 复位点（上一周期尾部 32 个采样）
dp_clean = np.full(N, np.nan)
dp_clean[:32] = 70.8 + rates[0] * STEP * np.arange(32)  # 上一周期尾部爬升
for c in range(3):
    a = bounds[-1]
    steps = int(np.ceil((TRIG - RESET) / (rates[c] * STEP)))
    b = min(a + steps, N)
    dp_clean[a:b] = RESET + rates[c] * STEP * np.arange(b - a)
    if b < N:
        dp_clean[b - 1] = TRIG - 0.3  # 触发采样点
        bounds.append(b)
bounds.append(N)
# 触发时刻（用于维护记录，与数据严格一致）
trig_times = [str(t[b - 1])[:16] for b in bounds[1:-1]]

dp = dp_clean + ar1(N, 0.55)
out_p = 118.0 + ar1(N, 0.85)
in_p = out_p + dp

dp_shift = pd.Series(np.clip(dp - 45.0, 0, None)).rolling(72, min_periods=1).mean().to_numpy()
md_sigma = 0.050 + 0.0011 * np.clip(dp, 45.0, TRIG) - 0.0011 * 45.0 + ar1(N, 0.0028)

dcs = pd.DataFrame({
    "时间": t.strftime("%Y-%m-%d %H:%M:%S"),
    "换网器入口压力(bar)": np.round(in_p, 2),
    "换网器出口压力(bar)": np.round(out_p, 2),
    "过滤器压差(bar)": np.round(dp, 2),
    "计量泵电流(A)": np.round(46.0 + 0.09 * dp + ar1(N, 0.35), 2),
    "熔体温度(℃)": np.round(285.0 + ar1(N, 0.33), 2),
    "薄膜厚度MD波动(μm)": np.round(md_sigma, 4),
    "挤出机螺杆转速(rpm)": np.round(68.0 + ar1(N, 0.07), 2),
})
dcs.to_csv(f"{OUT}/dcs_melt_system_10min.csv", index=False, encoding="utf-8-sig")

# ── 班次质检 8h（取整点采样） ─────────────────────────────────────
q_idx = np.arange(0, N, 48)
dp_q = dp_clean[q_idx]
sev_q = np.clip((dp_q - 52.0) / 25.0, 0.0, 1.0)
breaks = rng.poisson(0.25 + 1.7 * sev_q)
qc = pd.DataFrame({
    "时间": t[q_idx].strftime("%Y-%m-%d %H:%M:%S"),
    "优品率(%)": np.round(98.6 - 0.9 * np.clip((dp_q - 55.0) / 20.0, 0, 1)
                          + ar1(len(q_idx), 0.09), 2),
    "破膜次数(次/班)": breaks,
})
qc.to_csv(f"{OUT}/qc_shift_8h.csv", index=False, encoding="utf-8-sig")

# ── 换网/原料维护记录（与数据严格对齐） ───────────────────────────
log = pd.DataFrame({
    "时间": ["2026-08-10 05:20", trig_times[0], "2026-08-26 09:00", trig_times[1]],
    "事件类型": ["计划换网", "计划换网", "原料变更", "计划换网"],
    "事件内容": [
        "压差71.2bar触发，网面杂质中等，换网+清理",
        f"压差{dp_clean[bounds[1]-1]:.1f}bar触发，网面杂质中等，换网+清理",
        "新批次PET-P2（供应商B）投用，熔体灰分待检",
        f"压差{dp_clean[bounds[2]-1]:.1f}bar触发，网面杂质明显偏多，换网+清理",
    ],
})
log.to_csv(f"{OUT}/maintenance_log.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_data.py",
    "seed": 102,
    "rows": {"dcs": N, "qc": len(qc), "log": len(log)},
    "period": [str(t[0]), str(t[-1])],
    "sampling": {"dcs": "10min", "qc": "8h", "log": "事件型"},
    "files": {
        "dcs": {"path": "dcs_melt_system_10min.csv", "sha256": sha(f"{OUT}/dcs_melt_system_10min.csv")},
        "qc": {"path": "qc_shift_8h.csv", "sha256": sha(f"{OUT}/qc_shift_8h.csv")},
        "log": {"path": "maintenance_log.csv", "sha256": sha(f"{OUT}/maintenance_log.csv")},
    },
    "events": {
        "F1_压差锯齿": f"三周期复位~26.5→触发72bar；速率 5.3/5.7/7.5 bar/天；触发时刻 {trig_times}",
        "F2_联动效应": "ΔP>52bar 起破膜上升、ΔP>55bar 优品率下降；泵电流 +0.09×ΔP；厚度MD波动 0.050→0.08μm",
        "F3_原料事件": "08-26 09:00 新批次 PET-P2 投用 → C3 速率加倍（7.5 bar/天）",
        "决策锚点": "数据末端 ΔP≈58bar；按 C3 速率外推触及 72bar ≈ 09-01（距数据结束约 1.8 天，48h 计划流程已不够）",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照典型运行值；换网阈值 72bar 为题设规程",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("BC2 rows:", len(dcs), "dcs +", len(qc), "qc +", len(log), "log")
print("  ΔP", round(dp.min(), 1), "~", round(dp.max(), 1), "| 触发时刻", trig_times,
      "| 末端ΔP", round(dp_clean[-1], 1))
