# -*- coding: utf-8 -*-
"""BC1 干燥露点失控 → 雾度/晶点上升（确定性，seed=101）。

根因链（注入的信号，分析报告应能逐步检出）：
  F1 再生加热器老化   09-05 18:00 起：再生风温 175→118 ℃ 阶梯下滑，
                      同步干燥塔露点 -60 → -40 ℃ 缓升（设定侧无任何变更）
  F2 水分携带         露点越过 -52 ℃ 后，PET 含水率 35 → ~125 ppm（滞后 2~4 h）
  F3 质量联动         含水率 >80 ppm 后：雾度 1.85 → 3.5 %、晶点 3 → ~37 个/㎡
                      （滞后 8~12 h）；熔体压力波动增大、挤出电流微降（水解降粘）
  对照组（红鲱鱼）    主挤温度/预结晶/干燥风温/铸片辊温度全程平稳
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(101)

OUT = "data/bopet_cases/bc1_dryer_dewpoint"
N = 14 * 144  # 14 天 × 144 点/天（10 min）
t = pd.date_range("2026-09-01 00:00", periods=N, freq="10min")
i = np.arange(N)
ONSET = 5 * 144 + 108  # 09-05 18:00


def ar1(n, sigma, phi=0.6, rng=rng):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


# ── 露点与再生风温（设备侧异常，同步发生） ─────────────────────────
rise = np.clip(i - ONSET, 0, None)
dew_clean = -60.0 + np.minimum(0.11 * rise, 18.0) + 0.002 * np.clip(rise - 163.6, 0, None)
regen_clean = 175.0 - np.minimum(0.37 * rise, 53.0) - 0.004 * np.clip(rise - 144, 0, None)
dew = dew_clean + ar1(N, 0.30)
regen = regen_clean + ar1(N, 0.7)

# 水分携带严重度（露点越差越严重，渐变 0→1）
sev = np.clip((dew_clean + 50.0) / 8.0, 0.0, 1.0)
sev_s = pd.Series(sev).rolling(144, min_periods=1).mean().to_numpy()  # ~1 天平滑

melt_p = 110.0 + ar1(N, 0.55) + sev_s * ar1(N, 1.3, phi=0.5) + 0.8 * sev_s
motor_a = 212.0 + ar1(N, 0.9) - 5.0 * sev_s

dcs = pd.DataFrame({
    "时间": t.strftime("%Y-%m-%d %H:%M:%S"),
    "干燥塔露点温度(℃)": np.round(dew, 2),
    "再生风温度(℃)": np.round(regen, 2),
    "干燥风温度(℃)": np.round(168.0 + ar1(N, 0.5), 2),
    "预结晶温度(℃)": np.round(164.0 + ar1(N, 0.55), 2),
    "主挤计量段温度(℃)": np.round(282.0 + ar1(N, 0.14), 2),
    "熔体压力(bar)": np.round(melt_p, 2),
    "挤出机电流(A)": np.round(motor_a, 2),
    "铸片辊温度(℃)": np.round(26.5 + ar1(N, 0.07), 2),
})
dcs.to_csv(f"{OUT}/dcs_dryer_extruder_10min.csv", index=False, encoding="utf-8-sig")

# ── 化验室 4h 抽检（以露点驱动的滞后模型） ────────────────────────
lab_idx = np.arange(0, N, 24)
dp_lab = dew_clean[lab_idx]
exposure = np.clip((dp_lab + 52.0) / 6.0, 0, None)
moist = 35.0 + 93.0 * (1.0 - np.exp(-exposure / 1.2))
haze = 1.85 + 1.75 * np.clip((moist - 50.0) / 70.0, 0.0, 1.0) ** 0.8
gel = 3.2 + 34.0 * np.clip((moist - 55.0) / 65.0, 0.0, 1.0) ** 0.9
lab = pd.DataFrame({
    "时间": t[lab_idx].strftime("%Y-%m-%d %H:%M:%S"),
    "PET含水率(ppm)": np.round(moist + ar1(len(lab_idx), 2.5), 1),
    "雾度(%)": np.round(haze + ar1(len(lab_idx), 0.05), 2),
    "透光率(%)": np.round(91.6 - 1.1 * np.clip((moist - 55.0) / 70.0, 0, 1)
                          + ar1(len(lab_idx), 0.05), 2),
    "晶点数(个/㎡)": np.round(gel + ar1(len(lab_idx), 0.6), 1),
    "拉伸强度(MPa)": np.round(208.5 - 6.0 * np.clip((moist - 60.0) / 70.0, 0, 1) ** 1.2
                              + ar1(len(lab_idx), 0.9), 1),
})
lab.to_csv(f"{OUT}/lab_film_quality_4h.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_data.py",
    "seed": 101,
    "rows": {"dcs_dryer_extruder_10min.csv": N, "lab_film_quality_4h.csv": len(lab)},
    "period": [str(t[0]), str(t[-1])],
    "sampling": {"dcs": "10min", "lab": "4h"},
    "files": {
        "dcs": {"path": "dcs_dryer_extruder_10min.csv", "sha256": sha(f"{OUT}/dcs_dryer_extruder_10min.csv")},
        "lab": {"path": "lab_film_quality_4h.csv", "sha256": sha(f"{OUT}/lab_film_quality_4h.csv")},
    },
    "events": {
        "F1_再生加热器老化": "09-05 18:00 起再生风温 175→118℃ 下滑，露点 -60→-40℃ 缓升（无设定变更，设备性问题）",
        "F2_水分携带": "露点越过 -52℃ 后 PET 含水率 35→~125 ppm，滞后 2~4 h",
        "F3_质量联动": "含水率 >80 ppm 后雾度 1.85→3.5%、晶点 3→~37 个/㎡（滞后 8~12 h）；熔体压力波动增大、挤出电流微降",
        "红鲱鱼": "主挤温度/预结晶/干燥风温/铸片辊温度全程平稳",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照（data/lekai-test）典型运行值；干燥露点/含水/雾度机理参考 BOPET 干燥工艺常识",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("BC1 rows:", len(dcs), "dcs +", len(lab), "lab")
print("  露点", dew.min(), "~", round(dew.max(), 1), "| 再生风温", round(regen.max(), 1), "~", round(regen.min(), 1))
print("  含水率", round(lab["PET含水率(ppm)"].min(), 1), "~", round(lab["PET含水率(ppm)"].max(), 1),
      "| 雾度", round(lab["雾度(%)"].min(), 2), "~", round(lab["雾度(%)"].max(), 2),
      "| 晶点", round(lab["晶点数(个/㎡)"].min(), 1), "~", round(lab["晶点数(个/㎡)"].max(), 1))
