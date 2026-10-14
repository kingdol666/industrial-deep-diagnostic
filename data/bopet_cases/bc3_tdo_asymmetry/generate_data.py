# -*- coding: utf-8 -*-
"""BC3 TDO 烘箱温度场南北不对称 → 出口宽度收窄与破膜（确定性，seed=103）。

注入的信号：
  F1 单侧风温异常   09-08 06:00 起南侧拉伸区风温 -6.5℃（2h 阶跃）再缓降 3.5℃（3 天）
                    → 合计 -10℃；北侧与定型区两侧全程正常（温差 ≤2℃ 被破坏）
  F2 宽度响应       出口薄膜宽度 6329 → ~6320 mm（τ≈4h，南侧拉伸不足收缩）
  F3 张力恶化       牵引入口张力均值 +15N、波动 std 8→22N（应力分布不均）
  F4 破膜联动       破膜次数 0.3→2.5 次/班，位置集中于操作侧（南侧）；
                    优品率 98.6→97.1
  对照组（红鲱鱼）  轨道宽度设定 6330 恒定未动；定型区对称；风机频率平稳
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(103)

OUT = "data/bopet_cases/bc3_tdo_asymmetry"
N = 12 * 144  # 12 天 × 10 min
t = pd.date_range("2026-09-05 00:00", periods=N, freq="10min")
i = np.arange(N)
ONSET = 4 * 144 + 36  # 09-08 06:00


def ar1(n, sigma, phi=0.6, rng=rng):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


# ── 南侧拉伸区风温：2h 阶跃 -6.5℃ + 3 天缓降 -3.5℃ ───────────────
s = np.clip(i - ONSET, 0, None)
south_clean = 240.5 - np.minimum(0.542 * s, 6.5) - 0.00317 * np.clip(s - 12, 0, None)
resp = 1.0 - np.exp(-np.clip(i - ONSET, 0, None) / 24.0)  # τ≈4h 过程响应

width = 6329.0 - 9.0 * resp + ar1(N, 1.4)
tension = 2270.0 + 15.0 * resp + ar1(N, 8.0) + resp * ar1(N, 14.0, phi=0.45)

dcs = pd.DataFrame({
    "时间": t.strftime("%Y-%m-%d %H:%M:%S"),
    "TDO拉伸区北风温(℃)": np.round(240.8 + ar1(N, 0.85), 2),
    "TDO拉伸区南风温(℃)": np.round(south_clean + ar1(N, 0.9), 2),
    "TDO定型区北风温(℃)": np.round(191.0 + ar1(N, 0.75), 2),
    "TDO定型区南风温(℃)": np.round(190.8 + ar1(N, 0.75), 2),
    "TDO轨道宽度设定": np.full(N, 6330.0),
    "TDO出口薄膜宽度(mm)": np.round(width, 1),
    "牵引入口张力(N)": np.round(tension, 1),
    "TDO风机频率CX4": np.round(85.0 + ar1(N, 0.05), 2),
})
dcs.to_csv(f"{OUT}/dcs_tdo_10min.csv", index=False, encoding="utf-8-sig")

# ── 班次质检 8h ──────────────────────────────────────────────────
q_idx = np.arange(0, N, 48)
resp_q = 1.0 - np.exp(-np.clip(q_idx - ONSET, 0, None) / 6.0)  # τ≈半天
resp_qd = 1.0 - np.exp(-np.clip(q_idx - ONSET - 72, 0, None) / 8.0)  # 破膜再滞后 12h
breaks = rng.poisson(0.3 + 2.2 * np.clip(resp_qd, 0, 1))
pos = []
for b, r in zip(breaks, resp_qd):
    if b == 0 or r < 0.35:
        pos.append(rng.choice(["无", "中部", "驱动侧", "操作侧"], p=[0.6, 0.2, 0.1, 0.1]))
    else:
        pos.append(rng.choice(["操作侧", "中部", "驱动侧", "无"], p=[0.72, 0.12, 0.08, 0.08]))
qc = pd.DataFrame({
    "时间": t[q_idx].strftime("%Y-%m-%d %H:%M:%S"),
    "优品率(%)": np.round(98.6 - 1.5 * np.clip(resp_q, 0, 1) + ar1(len(q_idx), 0.12), 2),
    "破膜次数(次/班)": breaks,
    "主要破膜位置": pos,
    "出口宽度实测(mm)": np.round(width[q_idx] + rng.normal(0, 0.8, len(q_idx)), 1),
})
qc.to_csv(f"{OUT}/qc_shift_8h.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_data.py",
    "seed": 103,
    "rows": {"dcs": N, "qc": len(qc)},
    "period": [str(t[0]), str(t[-1])],
    "sampling": {"dcs": "10min", "qc": "8h"},
    "files": {
        "dcs": {"path": "dcs_tdo_10min.csv", "sha256": sha(f"{OUT}/dcs_tdo_10min.csv")},
        "qc": {"path": "qc_shift_8h.csv", "sha256": sha(f"{OUT}/qc_shift_8h.csv")},
    },
    "events": {
        "F1_单侧风温异常": "09-08 06:00 起南侧拉伸区风温 240.5→230.5℃（-10℃），北侧/定型区对称正常",
        "F2_宽度响应": "出口宽度 6329→~6320mm，τ≈4h",
        "F3_张力恶化": "牵引入口张力 +15N、波动 std 8→22N",
        "F4_破膜联动": "破膜 0.3→2.5 次/班且集中于操作侧；优品率 98.6→97.1",
        "红鲱鱼": "轨道宽度设定 6330 恒定未动；风机频率平稳",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照典型运行值（CX4≈240℃/CX6≈191℃/轨宽6330）",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("BC3 rows:", len(dcs), "dcs +", len(qc), "qc")
s_col = dcs["TDO拉伸区南风温(℃)"]
print("  南风温", s_col.max(), "~", s_col.min(), "| 出口宽度", round(width.min(), 1),
      "~", round(width.max(), 1), "| 破膜合计", int(qc["破膜次数(次/班)"].sum()))
