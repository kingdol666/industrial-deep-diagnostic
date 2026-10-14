# -*- coding: utf-8 -*-
"""BC4 回料比例提升 + 季节升温混淆 → 力学性能下降（确定性，seed=104）。

注入的信号：
  F1 配方台阶   回料比例 5% →(05-11)→ 12% →(05-20 干预回调)→ 6% →(05-24)→ 12%
                每次切换约 3h 配料混合过渡
  F2 机制链     回料↑ → 特性粘度 IV 0.724 → 0.708 dL/g（-0.016，剂量-响应一致）
                → 拉伸强度 212→197.6 MPa、断裂伸长率 150→130.8%（贴下限）
  F3 混淆因素   环境温度 17→28℃、冷却水温 22→28.6℃ 单调上升（春→夏），
                与时间共变但与性能无台阶对应（H2 的诱惑与破绽）
  F4 对照项     雾度随冷却水温轻微爬升（1.9→2.2%，未超标）；厚度平稳
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
rng = np.random.default_rng(104)

OUT = "data/bopet_cases/bc4_regrind_confounded"
N = 720  # 30 天 × 1h
t = pd.date_range("2026-05-01 00:00", periods=N, freq="h")
h = np.arange(N)


def ar1(n, sigma, phi=0.6, rng=rng):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


# ── 回料比例台阶（含 3h 配料过渡） ────────────────────────────────
target = np.where(h < 248, 5.0, np.where(h < 464, 12.0, np.where(h < 560, 6.0, 12.0)))
regrind = target.copy().astype(float)
for b in (248, 464, 560):
    seg = slice(b, min(b + 3, N))
    steps = np.arange(1, seg.stop - seg.start + 1)
    regrind[seg] = regrind[b - 1] + (target[b] - regrind[b - 1]) * steps / 3.0
regrind += ar1(N, 0.18)
iv_frac = pd.Series(np.clip(regrind - 5.0, 0, None) / 7.0).rolling(8, min_periods=1).mean().to_numpy()
iv = 0.724 - 0.016 * iv_frac + ar1(N, 0.0016)

ambient = 17.0 + 0.36 * (h / 24.0) + 2.8 * np.sin(2 * np.pi * (h - 9) / 24.0) + ar1(N, 0.22)
cooling = 22.0 + 0.22 * (h / 24.0) + ar1(N, 0.18)

dcs = pd.DataFrame({
    "时间": t.strftime("%Y-%m-%d %H:%M:%S"),
    "回料比例(%)": np.round(regrind, 2),
    "环境温度(℃)": np.round(ambient, 2),
    "冷却水温度(℃)": np.round(cooling, 2),
    "熔体温度(℃)": np.round(285.5 + ar1(N, 0.33), 2),
    "熔体压力(bar)": np.round(110.0 + ar1(N, 0.6), 2),
    "铸片辊温度(℃)": np.round(26.0 + 0.18 * (h / 24.0) + ar1(N, 0.11), 2),
    "挤出机电流(A)": np.round(210.0 - 1.5 * (regrind - 5.0) / 7.0 + ar1(N, 1.0), 2),
})
dcs.to_csv(f"{OUT}/dcs_process_1h.csv", index=False, encoding="utf-8-sig")

# ── 化验室 12h ───────────────────────────────────────────────────
lab_idx = np.arange(0, N, 12)
iv_lab = iv[lab_idx] + rng.normal(0, 0.0022, len(lab_idx))
lab = pd.DataFrame({
    "时间": t[lab_idx].strftime("%Y-%m-%d %H:%M:%S"),
    "特性粘度(dL/g)": np.round(iv_lab, 4),
    "拉伸强度(MPa)": np.round(212.0 + 900.0 * (iv_lab - 0.724) + rng.normal(0, 0.85, len(lab_idx)), 1),
    "断裂伸长率(%)": np.round(150.0 + 1200.0 * (iv_lab - 0.724) + rng.normal(0, 1.1, len(lab_idx)), 1),
    "雾度(%)": np.round(1.9 + 0.028 * (cooling[lab_idx] - 22.0) + ar1(len(lab_idx), 0.04), 2),
    "薄膜厚度(μm)": np.round(12.0 + ar1(len(lab_idx), 0.012), 3),
    "透光率(%)": np.round(91.5 + ar1(len(lab_idx), 0.06), 2),
})
lab.to_csv(f"{OUT}/lab_film_props_12h.csv", index=False, encoding="utf-8-sig")

# ── 配方变更记录（MES 导出） ─────────────────────────────────────
recipe = pd.DataFrame({
    "时间": ["2026-05-11 08:00", "2026-05-20 08:00", "2026-05-24 08:00"],
    "变更项": ["回料比例", "回料比例", "回料比例"],
    "变更前": ["5%", "12%", "6%"],
    "变更后": ["12%", "6%", "12%"],
    "依据/备注": [
        "降本项目 CR-2605 批准实施（边角料回用提比例）",
        "质量部要求暂停：拉伸强度逼近内控下限，排查期间降回 6%",
        "排查未见工艺异常，降本考核压力下恢复 12% 执行",
    ],
})
recipe.to_csv(f"{OUT}/recipe_change_log.csv", index=False, encoding="utf-8-sig")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


manifest = {
    "generator": "generate_data.py",
    "seed": 104,
    "rows": {"dcs": N, "lab": len(lab), "recipe": len(recipe)},
    "period": [str(t[0]), str(t[-1])],
    "sampling": {"dcs": "1h", "lab": "12h", "recipe": "事件型"},
    "files": {
        "dcs": {"path": "dcs_process_1h.csv", "sha256": sha(f"{OUT}/dcs_process_1h.csv")},
        "lab": {"path": "lab_film_props_12h.csv", "sha256": sha(f"{OUT}/lab_film_props_12h.csv")},
        "recipe": {"path": "recipe_change_log.csv", "sha256": sha(f"{OUT}/recipe_change_log.csv")},
    },
    "events": {
        "F1_配方台阶": "回料比例 5→12→(05-20 回调)→6→(05-24 恢复)→12%，构成天然干预-响应实验",
        "F2_机制链": "回料↑ → IV 0.724→0.708 dL/g → 拉伸强度 212→~197.6 MPa、断裂伸长率 150→~130.8%",
        "F3_混淆因素": "环境温度 17→28℃ / 冷却水温 22→28.6℃ 单调上升（季节），与时间共变但无台阶对应",
        "F4_对照项": "雾度随冷却水温轻微爬升 1.9→2.2%（未超标）；厚度平稳",
    },
    "basis": "工艺窗口取自乐凯 FW3 快照典型运行值；内控标准拉伸强度≥195MPa 为题设",
}
with open(f"{OUT}/generation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("BC4 rows:", len(dcs), "dcs +", len(lab), "lab +", len(recipe), "recipe")
print("  拉伸强度", lab["拉伸强度(MPa)"].min(), "~", lab["拉伸强度(MPa)"].max(),
      "| IV", lab["特性粘度(dL/g)"].min(), "~", lab["特性粘度(dL/g)"].max())
