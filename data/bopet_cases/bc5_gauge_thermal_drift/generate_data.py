# -*- coding: utf-8 -*-
"""BC5 在线厚度"漂移"实为测厚仪温漂（确定性，seed=105）。

注入的信号：
  F1 车间温度异动   07-02 10:00 起空调制冷不足：日均温 +0.11℃/天、
                    日振幅 4.3→6.6℃，白天峰值 31℃+，夜间仅小幅回落
  F2 测量伪影       探头罩温度跟随车间温度（增益 0.93、滞后 1h）；
                    在线平均厚度 = 真值 12.000 + 0.023×(罩温-24.5) —— 纯测量温漂，
                    白班峰值 12.10+ μm、夜间回落 ~11.97，日均 12.00→12.04
  F3 真值未动       计量泵转速/熔体压力/厚度 MD 波动/横向剖面峰值位置全程平稳
  F4 真值锚点       标准膜片(10.000μm)校准读数与罩温同步漂移（决定性证据）
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(105)

OUT = "data/bopet_cases/bc5_gauge_thermal_drift"
N = 10 * 144  # 10 天 × 10 min
t = pd.date_range("2026-07-01 00:00", periods=N, freq="10min")
i = np.arange(N)
AC_FAIL = 2 * 144 + 60  # 07-02 10:00


def ar1(n, sigma, phi=0.6, rng=rng):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


# ── 车间环境温度：昼夜节律 + 空调衰减（白天高峰、夜间小幅回落） ──
tod = (i % 144) / 144.0
s = np.sin(2 * np.pi * (tod - 9.0 / 24.0))
shape = np.where(s > 0, s, 0.25 * s)
extra_amp = 2.3 * np.clip((i - AC_FAIL) / 576.0, 0, 1)  # 4 天爬升
mean_rise = 0.11 * np.clip(i - AC_FAIL, 0, None) / 144.0
env_clean = 24.5 + mean_rise + (4.3 + extra_amp) * shape
env = env_clean + ar1(N, 0.25)

cover_clean = 0.93 * np.r_[np.full(6, env_clean[:6].mean()), env_clean[:-6]] + 1.1
cover = cover_clean + ar1(N, 0.1)

thickness = 12.000 + 0.0230 * (cover_clean - 24.5) + ar1(N, 0.0040) + rng.normal(0, 0.0028, N)

dcs = pd.DataFrame({
    "时间": t.strftime("%Y-%m-%d %H:%M:%S"),
    "车间环境温度(℃)": np.round(env, 2),
    "测厚仪探头罩温度(℃)": np.round(cover, 2),
    "在线平均厚度(μm)": np.round(thickness, 4),
    "薄膜厚度MD波动(μm)": np.round(0.048 + ar1(N, 0.0032), 4),
    "横向剖面峰值位置(mm)": np.round(3165.0 + ar1(N, 2.2), 1),
    "计量泵转速(rpm)": np.round(88.0 + ar1(N, 0.05), 2),
    "熔体压力(bar)": np.round(110.0 + ar1(N, 0.55), 2),
    "铸片辊温度(℃)": np.round(26.3 + ar1(N, 0.09), 2),
})
dcs.to_csv(f"{OUT}/dcs_thickness_gauge_10min.csv", index=False, encoding="utf-8-sig")

# ── 仪表班标准膜片校准记录 8h ────────────────────────────────────
c_idx = np.arange(0, N, 48)
cal = pd.DataFrame({
    "时间": t[c_idx].strftime("%Y-%m-%d %H:%M:%S"),
    "标准膜片读数(μm)": np.round(10.000 + 0.021 * (cover_clean[c_idx] - 24.5)
                                  + rng.normal(0, 0.0035, len(c_idx)), 4),
    "探头罩温度(℃)": np.round(cover[c_idx], 2),
})
cal.to_csv(f"{OUT}/gauge_calib_8h.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_data.py",
    "seed": 105,
    "rows": {"dcs": N, "cal": len(cal)},
    "period": [str(t[0]), str(t[-1])],
    "sampling": {"dcs": "10min", "cal": "8h"},
    "files": {
        "dcs": {"path": "dcs_thickness_gauge_10min.csv", "sha256": sha(f"{OUT}/dcs_thickness_gauge_10min.csv")},
        "cal": {"path": "gauge_calib_8h.csv", "sha256": sha(f"{OUT}/gauge_calib_8h.csv")},
    },
    "events": {
        "F1_车间温度异动": "07-02 10:00 起空调不足：日均温 +0.11℃/天、日振幅 4.3→6.6℃，峰值 31℃+",
        "F2_测量伪影": "平均厚度=真值12.000+0.023×(罩温-24.5)：白班峰值 12.10+、夜间回落 ~11.97，日均 12.00→12.04",
        "F3_真值未动": "泵转速/熔体压力/MD波动/横向剖面峰值位置全程平稳（过程无变化）",
        "F4_真值锚点": "标准膜片读数与罩温同步漂移（10.000→10.10@白天峰），仪器问题的决定性证据",
        "决策锚点": "报警限 12.18μm 未触发；若按白班读数降泵速 0.5%，夜间真实厚度将触及下限 11.82μm",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照典型运行值；厚度公差 12±1.5% 为题设",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("BC5 rows:", len(dcs), "dcs +", len(cal), "cal")
print("  环境温度", round(env.min(), 1), "~", round(env.max(), 1),
      "| 在线厚度", round(thickness.min(), 3), "~", round(thickness.max(), 3),
      "| 标准片", round(cal["标准膜片读数(μm)"].min(), 3), "~", round(cal["标准膜片读数(μm)"].max(), 3))
