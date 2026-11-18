#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous heat-treatment line — simulated multi-source dataset (10 days).

Ground truth (kept OUTSIDE run/ for the diagnosing agents):
  Day 4.5 onset: ZONE-3 rear heater aging -> ZONE-3 temperature drifts low
  (-9 °C over ~36 h) with growing fluctuation; band right-edge temp deficit
  -2.5 °C; furnace map hot-region deficit at the right column (-8 °C);
  CCD frames develop dark oxide spots; lab hardness HRC 58.6 -> 56.9;
  yield 99.3% -> 97.5%.

Raw folder layout:
  L1_furnace_dcs_10min.csv          1440 rows (anchor, 10-min)
  L1_band_temp_profile_30min.csv    480 rows x 12 positions (PROF)
  L1_furnace_thermal_map_2h.csv     120 snapshots x 5x4 grid (MAP)
  L1_surface_ccd_index.csv + ccd/   240 hourly frames (IMG)
  L1_operator_notes.csv             9 notes (TXT)
  L1_lab_hardness_2h.csv            120 rows lab HRC (merge-eligible >=100)
  README.md                         context
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(parents=True, exist_ok=True)
(HERE / "run" / "00_input").mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(20261017)

T0 = pd.Timestamp("2026-02-02 00:00:00")
DAYS = 10
HOURS = DAYS * 24
ONSET_H = 108.0          # day 4.5 fault onset
RAMP_H = 36.0            # ramp to full effect (done by day 6.0)
REPAIR_H = 162.0         # day 6.75: repair recorded; healer replaces ZONE-3 rear heater
RECOVERY_H = 12.0        # recovery completes by day ~7.25


def ramp(hours: np.ndarray) -> np.ndarray:
    """Fault amplitude: rise to 1.0, then (after the recorded repair) fall to 0."""
    rise = np.clip((hours - ONSET_H) / RAMP_H, 0.0, 1.0)
    fall = np.clip((hours - REPAIR_H) / RECOVERY_H, 0.0, 1.0)
    return rise * (1.0 - fall)


def iso(ts):
    return [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts]


# ---- anchor DCS: 10-min cadence -------------------------------------------------
n = HOURS * 6
ts = [T0 + pd.Timedelta(minutes=10 * i) for i in range(n)]
h = np.arange(n) / 6.0
r = ramp(h)
z3 = 880 - 9.0 * r + rng.normal(0, 0.8, n) * (1.0 + 2.0 * r)
z1 = 850 + rng.normal(0, 0.7, n)
z2 = 865 + rng.normal(0, 0.7, n)
out = 550 - 4.0 * r + rng.normal(0, 1.0, n)
dcs = pd.DataFrame({
    "时间": iso(ts),
    "FUR-Z1-TEMP": np.round(z1, 2),
    "FUR-Z2-TEMP": np.round(z2, 2),
    "FUR-Z3-TEMP": np.round(z3, 2),
    "FUR-SPEED": np.round(12.0 + rng.normal(0, 0.05, n), 3),
    "FUR-PRES": np.round(38.0 + rng.normal(0, 0.3, n), 3),
    "FUR-OUT-TEMP": np.round(out, 2),
    "FUR-YIELD": np.round(99.3 - 1.8 * r + rng.normal(0, 0.15, n), 2),
})
dcs.to_csv(RAW / "L1_furnace_dcs_10min.csv", index=False, encoding="utf-8-sig")

# ---- PROF: band cross-section temperature, 30-min, 12 positions ------------------
m = HOURS * 2
pts = [T0 + pd.Timedelta(minutes=30 * i) for i in range(m)]
hr = np.arange(m) / 2.0
rp = ramp(hr)
cols = {}
for j in range(1, 13):
    edge = -2.6 * rp if j >= 10 else (-0.6 * rp if j >= 8 else 0.0)
    base = 520 - (3.0 if j in (1, 12) else 0.0)      # natural edge falloff
    cols[f"pos_{j:02d}"] = np.round(base + edge + 0.8 * np.sin(np.arange(m) / 40 + j / 2)
                                    + rng.normal(0, 0.35, m), 2)
prof = pd.DataFrame({"时间": iso(pts), **cols})
prof.to_csv(RAW / "L1_band_temp_profile_30min.csv", index=False, encoding="utf-8-sig")

# ---- MAP: furnace cross-section thermal field, 2-h, 5x4 grid ---------------------
g = HOURS // 2
mt = [T0 + pd.Timedelta(hours=2 * i) for i in range(g)]
gh = np.arange(g) * 2.0
rg = ramp(gh)
rows = []
for i, t in enumerate(mt):
    for x in range(5):
        for y in range(4):
            v = 860 + 1.2 * x + 0.5 * np.sin(i / 9 + y) + rng.normal(0, 0.6)
            if x == 4:
                v -= 8.0 * rg[i]
            rows.append({"时间": iso([t])[0], "x": x, "y": y, "值": round(v, 2)})
pd.DataFrame(rows).to_csv(RAW / "L1_furnace_thermal_map_2h.csv", index=False, encoding="utf-8-sig")

# ---- TXT: operator notes ---------------------------------------------------------
notes = [
    ("2026-02-02 08:00:00", "交接班：全线运行正常，三区温度设定 880℃ 稳定"),
    ("2026-02-03 09:30:00", "带材入炉前检查正常，无异常记录"),
    ("2026-02-05 02:10:00", "三区温度波动偏大，已通知仪表检查热电偶"),
    ("2026-02-06 06:40:00", "三区后段温度持续偏低，怀疑加热管老化，安排计划检修"),
    ("2026-02-06 22:15:00", "右边缘温度感觉偏低，硬度抽检结果下降，通知工艺"),
    ("2026-02-08 10:00:00", "更换三区后段加热管，恢复送电升温"),
    ("2026-02-08 21:00:00", "更换后温度回升中，继续观察边缘硬度"),
    ("2026-02-10 09:00:00", "温度与硬度均已恢复，问题闭环"),
    ("2026-02-11 08:30:00", "交接班：一切正常"),
]
pd.DataFrame(notes, columns=["时间", "备注"]).to_csv(
    RAW / "L1_operator_notes.csv", index=False, encoding="utf-8-sig")

# ---- IMG: hourly surface-check CCD frames ----------------------------------------
ccd = RAW / "ccd"
ccd.mkdir(exist_ok=True)
idx = []
img_ts = [T0 + pd.Timedelta(hours=i) for i in range(HOURS)]
for i, t in enumerate(img_ts):
    arr = rng.normal(150, 8, (48, 48))
    rr = np.clip((i - ONSET_H) / RAMP_H, 0, 1) * (1.0 - np.clip((i - REPAIR_H) / RECOVERY_H, 0, 1))
    if i > ONSET_H:
        cy, cx = 20 + (i % 5), 28
        yy, xx = np.mgrid[0:48, 0:48]
        blob = np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * (3 + 4 * rr) ** 2)))
        arr -= (70 + 40 * rr) * blob                         # dark oxide spot grows then fades
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    fn = f"ccd_{i:04d}.png"
    Image.fromarray(arr, mode="L").save(ccd / fn)
    idx.append({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), "文件": f"ccd/{fn}"})
pd.DataFrame(idx).to_csv(RAW / "L1_surface_ccd_index.csv", index=False, encoding="utf-8-sig")

# ---- LAB: hardness every 2 h (merge-eligible, >=100 rows) ------------------------
ln = HOURS // 2
lt = [T0 + pd.Timedelta(hours=2 * i) for i in range(ln)]
lh = np.arange(ln) * 2.0
rl = ramp(lh)
lab = pd.DataFrame({
    "时间": iso(lt),
    "LAB-HRC": np.round(58.6 - 1.7 * rl + rng.normal(0, 0.25, ln), 2),
})
lab.to_csv(RAW / "L1_lab_hardness_2h.csv", index=False, encoding="utf-8-sig")

(RAW / "README.md").write_text(
    "# 连续热处理线数据（模拟场景）\n\n"
    "10 天连续生产数据。锚定主表 = L1_furnace_dcs_10min.csv（10 分钟粒度）。\n"
    "另有带材横向温度剖面（30 分钟）、炉膛温度场（2 小时）、表面检查图像索引（1 小时）、\n"
    "操作备注、实验室硬度抽检（2 小时）。用于端到端分析流程验证。\n",
    encoding="utf-8")

# ---- ground truth (OUTSIDE raw/ and run/) ----------------------------------------
(HERE / "ground_truth.md").write_text(f"""# GROUND TRUTH — 连续热处理线模拟场景（勿给诊断 agent 看）

- 注入故障：ZONE-3 后段加热管老化
  - 故障窗口：day 4.5（第 {ONSET_H:.0f} 小时）onset → 约 {RAMP_H:.0f} 小时内线性到全效（day 6.0）
  - 检修恢复：day 6.75（第 {REPAIR_H:.0f} 小时 = 2026-02-08 10:00 备注"更换加热管"）→ {RECOVERY_H:.0f} 小时内恢复
  - 操作备注含"怀疑加热管老化"（day 4.5）与"更换三区后段加热管"（day 6.75）——文本与数据一致
- 可观测后果与预期证据：
  1. FUR-Z3-TEMP 相对 880℃ 下漂（最大 ~-9℃）、波动增大（sd ~0.8→~2.4），**并在检修后回升至 880 附近**（时序先验：恢复发生在更换记录之后）
  2. FUR-OUT-TEMP 随动下降（~-4℃）；FUR-YIELD 99.3% → ~97.5%，检修后回升 ~99.2%
  3. 带材剖面（30min）右边缘 pos_10..12 亏欠 -2.6℃（故障期内），恢复后回到自然边缘落差
  4. 炉膛温度场（2h）x=4 列（右列）亏欠 -8℃（故障期内）
  5. CCD 表面检查：故障期暗斑（氧化点）出现并增长，检修后缩小消失（DARKFRAC/ENTROPY 回稳）
  6. 实验室硬度 LAB-HRC 58.6 → ~56.9（故障期），检修后回升 ~58.5
- 正确根因表述：三区后段加热管老化（热输入不足）→ 三区温度下漂+均匀性恶化 → 带材右边缘温度偏低
  → 硬度下降、合格率下降；更换加热管后全链恢复（因果闭环）。
- 干扰项（未注入变化，应被排除）：Z1/Z2、速度、炉压；热电偶故障假设（应被"更换后恢复"与均匀性空间分布鉴别）。
""", encoding="utf-8")

print(json.dumps({
    "raw": str(RAW), "anchor_rows": len(dcs), "profile_rows": len(prof),
    "map_rows": len(rows), "images": len(img_ts), "notes": len(notes), "lab_rows": len(lab),
    "onset_hour": ONSET_H, "days": DAYS,
}, ensure_ascii=False, indent=2))
