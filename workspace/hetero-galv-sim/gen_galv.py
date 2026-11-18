#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous hot-dip galvanizing line — simulated multi-source dataset (3 days, compact).

Ground truth (kept OUTSIDE the upload folder):
  Day 1.5 (hour 36) onset: right-side air-knife lip build-up (dross) ->
  GAL-AIRKNIFE-R-PRES fluctuation up, right-edge coating +6~9 g/m2,
  pot field right column warm drift, edge streaks appear, yield 98.5->96.8.
  Day 2.5 (hour 60) repair: knife cleaned, full recovery by ~hour 67.

Layout (ALL files flat in one folder so the web UI can upload it in one go):
  L1_galv_pot_dcs_10min.csv       432 rows (anchor)
  L1_coating_profile_30min.csv    144 rows x 10 positions (PROF)
  L1_pot_thermal_map_2h.csv       36 snapshots x 5x4 (MAP)
  L1_surface_defect_index.csv     + frame_000.png..frame_035.png (IMG, index refs bare names)
  L1_operator_notes.csv           7 notes (TXT)
  L1_lab_coating_2h.csv           36 rows lab g/m2
  README.md                       context
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(20261018)

T0 = pd.Timestamp("2026-02-09 00:00:00")
DAYS = 3
HOURS = DAYS * 24
ONSET_H = 36.0
RAMP_H = 6.0
REPAIR_H = 60.0
RECOVERY_H = 7.0


def ramp(h):
    rise = np.clip((h - ONSET_H) / RAMP_H, 0.0, 1.0)
    fall = np.clip((h - REPAIR_H) / RECOVERY_H, 0.0, 1.0)
    return rise * (1.0 - fall)


def iso(ts):
    return [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts]


# ---- anchor DCS: 10-min ---------------------------------------------------------
n = HOURS * 6
ts = [T0 + pd.Timedelta(minutes=10 * i) for i in range(n)]
h = np.arange(n) / 6.0
r = ramp(h)
knife_r = 0.42 + 0.20 * r * (1 + rng.normal(0, 0.5, n)) + rng.normal(0, 0.012, n)
dcs = pd.DataFrame({
    "时间": iso(ts),
    "GAL-POT-TEMP": np.round(455.0 + 0.6 * r + rng.normal(0, 0.35, n), 2),
    "GAL-LINE-SPEED": np.round(100.0 + rng.normal(0, 0.4, n), 2),
    "GAL-TENSION": np.round(2.4 + rng.normal(0, 0.02, n), 3),
    "GAL-AIRKNIFE-L-PRES": np.round(0.42 + rng.normal(0, 0.012, n), 4),
    "GAL-AIRKNIFE-R-PRES": np.round(knife_r, 4),
    "GAL-COATING-GSM": np.round(120.0 + 5.5 * r + rng.normal(0, 0.8, n), 2),
    "GAL-YIELD": np.round(98.5 - 1.7 * r + rng.normal(0, 0.12, n), 2),
})
dcs.to_csv(RAW / "L1_galv_pot_dcs_10min.csv", index=False, encoding="utf-8-sig")

# ---- PROF: transverse coating weight, 30-min, 10 positions -----------------------
m = HOURS * 2
pts = [T0 + pd.Timedelta(minutes=30 * i) for i in range(m)]
rp = ramp(np.arange(m) / 2.0)
cols = {}
for j in range(1, 11):
    edge = (6.0 + 2.5 * np.sin(np.arange(m) / 30)) * rp if j >= 8 else (1.2 * rp if j >= 6 else 0.0)
    cols[f"pos_{j:02d}"] = np.round(120 + edge + 0.9 * np.sin(np.arange(m) / 25 + j / 2)
                                    + rng.normal(0, 0.6, m), 2)
pd.DataFrame({"时间": iso(pts), **cols}).to_csv(
    RAW / "L1_coating_profile_30min.csv", index=False, encoding="utf-8-sig")

# ---- MAP: pot thermal field, 2-h, 5x4 grid ---------------------------------------
g = HOURS // 2
mt = [T0 + pd.Timedelta(hours=2 * i) for i in range(g)]
rg = ramp(np.arange(g) * 2.0)
rows = []
for i, t in enumerate(mt):
    for x in range(5):
        for y in range(4):
            v = 455 + 0.35 * x + 0.2 * np.sin(i / 5 + y) + rng.normal(0, 0.25)
            if x == 4:
                v += 6.0 * rg[i]
            rows.append({"时间": iso([t])[0], "x": x, "y": y, "值": round(v, 2)})
pd.DataFrame(rows).to_csv(RAW / "L1_pot_thermal_map_2h.csv", index=False, encoding="utf-8-sig")

# ---- TXT: operator notes ---------------------------------------------------------
notes = [
    ("2026-02-09 08:00:00", "接班：锌锅温度与镀层克重正常，线速 100m/min"),
    ("2026-02-09 20:30:00", "右侧气刀附近听到异响，镀层目视右边缘略厚，已记录"),
    ("2026-02-10 04:10:00", "右边缘镀层持续偏厚，怀疑右侧气刀唇口结渣，通知工艺"),
    ("2026-02-10 16:40:00", "计划清理右侧气刀，降速准备"),
    ("2026-02-10 19:00:00", "清理右侧气刀唇口结渣完成，升速观察"),
    ("2026-02-10 23:30:00", "右边缘镀层恢复正常，克重回到目标窗口"),
    ("2026-02-11 08:30:00", "交接班：镀层克重与合格率回稳，问题闭环"),
]
pd.DataFrame(notes, columns=["时间", "备注"]).to_csv(
    RAW / "L1_operator_notes.csv", index=False, encoding="utf-8-sig")

# ---- IMG: surface check frames, 2-h, flat names (bare names in the index) --------
idx = []
for i, t in enumerate(mt):
    arr = rng.normal(170, 7, (48, 48))
    rr = ramp(i * 2.0)
    if rr > 0:
        yy, xx = np.mgrid[0:48, 0:48]
        band = np.exp(-(((xx - (40 - i % 4)) ** 2) / 6.0)) * np.exp(-(((yy - 24) ** 2) / 900.0))
        arr -= 65 * rr * band
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    fn = f"frame_{i:03d}.png"
    Image.fromarray(arr, mode="L").save(RAW / fn)
    idx.append({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), "文件": fn})
pd.DataFrame(idx).to_csv(RAW / "L1_surface_defect_index.csv", index=False, encoding="utf-8-sig")

# ---- LAB: offline coating weight, 2-h --------------------------------------------
lab = pd.DataFrame({
    "时间": iso(mt),
    "LAB-COATING-GSM": np.round(120.0 + 5.8 * rg + rng.normal(0, 0.9, g), 2),
})
lab.to_csv(RAW / "L1_lab_coating_2h.csv", index=False, encoding="utf-8-sig")

(RAW / "README.md").write_text(
    "# 连续热镀锌线数据（模拟场景，3 天）\n\n"
    "锚定主表 = L1_galv_pot_dcs_10min.csv（10 分钟）。\n"
    "同目录另有：镀层横向剖面（30 分钟，pos_01..pos_10）、锌锅温度场（2 小时，5×4 网格）、\n"
    "表面检查图像（2 小时，frame_*.png + L1_surface_defect_index.csv 索引，文件列写裸文件名）、\n"
    "操作备注、实验室镀层克重（2 小时）。\n",
    encoding="utf-8")

(HERE / "ground_truth.md").write_text(f"""# GROUND TRUTH — 热镀锌线模拟场景（勿上传/勿给诊断 agent）

- 注入故障：右侧气刀唇口结渣（dross build-up）
  - 故障窗：day 1.5（第 {ONSET_H:.0f} 小时）→ 全效 {RAMP_H:.0f} 小时内；day 2.5（第 {REPAIR_H:.0f} 小时 = 02-10 12:00 前后备注清理）→ {RECOVERY_H:.0f} 小时恢复
- 可观测后果（预期证据）：
  1. GAL-AIRKNIFE-R-PRES 均值上抬且波动放大（左侧不变）
  2. GAL-COATING-GSM 在线克重 +5.5 左右（超标），GAL-YIELD 98.5→~96.8，修复后回升
  3. 剖面 pos_08..10（右缘）镀层 +6~8.5 g/m²；左侧无变化
  4. 锌锅温度场右列（x=4）+6℃ 暖漂（局部）
  5. 表面检查帧右缘暗条带出现并随结渣增长，清理后消失
  6. 实验室 LAB-COATING-GSM 同步 +5.8，修复后回落
  7. 备注记录：右侧气刀异响→结渣判断→清理→恢复
- 正确根因：右侧气刀唇口结渣 → 右缘吹扫不足 → 右缘镀层偏厚 → 克重超标/合格率下降；清理后恢复（因果闭环）
- 干扰项（未注入）：锌锅温度、线速、张力、左侧气刀
""", encoding="utf-8")

print(json.dumps({
    "raw": str(RAW), "anchor_rows": len(dcs), "profile_rows": m,
    "map_rows": len(rows), "frames": len(idx), "notes": len(notes), "lab_rows": g,
    "total_files": len(list(RAW.iterdir())),
}, ensure_ascii=False, indent=2))
