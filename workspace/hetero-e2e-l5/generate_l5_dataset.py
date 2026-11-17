#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L5 锂离子电池极片涂布产线 —— 多源异构 E2E 测试数据集生成器（确定性，固定 seed）。

场景（与 BOPET 完全不同的领域，用于证明 E-1H/LSR 接入是场景通用而非特设）：
  浆料供料 → 涂布（间隙式刮刀，左右独立间隙）→ 烘箱三区干燥 → 辊压 → 收卷 → 在线面密度/CCD 表面检测

数据形态（五源异构）：
  1. DCS 主表    L5_dcs_process_10min.csv        10min × 21 天（anchor）
  2. 剖面 PROF   L5_ad_scan_30min.csv            30min，时间 × pos_01..pos_24 面密度横向剖面
  3. 场 MAP      L5_calender_map_2h.csv          2h，时间,x,y,厚度（辊压后 5×4 测厚网格）
  4. 图像 IMG    ccd_frames/*.png + L5_ccd_index.csv  8h 一帧 CCD 表面检测图（60 帧）
  5. 文本 TXT    L5_operator_notes.csv           操作员/交接班备注（带时间）
  6. 化验 AUX    L5_lab_electrode_2h.csv         2h 化验（粘结力/孔隙率/水分）

注入故障（真值，写入 ground_truth.md，不随数据喂给分析端）：
  第 9 天 00:00 起涂布辊右端轴承磨损 → 右间隙缓慢增大（+0.0008 mm/天，累计 +0.008）
  → 右缘面密度渐进偏薄（边缘偏差 0 → −1.6%）→ 面密度 CV 1.25%→2.15%
  → 优品率滞后 6h 由 98.5% 滑落至 ~96.6%；CCD 缺陷斑点数 2→6（第 10 天起）
  混杂项：第 7 天浆料批次切换（固含量 48.5→49.5、回浆比例 8→12%，粘度 +30，
  但不影响横向对称性——用于检验分析能否排除）；第 14 天计划保养降速 2h。
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

SEED = 20261017
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
T0 = pd.Timestamp("2026-09-24 00:00:00")
DAYS = 21
N = DAYS * 24 * 6                      # 10min → 3024
H_FAULT = 9 * 24                        # 第 9 天 00:00
H_RECIPE = 7 * 24 + 8                   # 第 7 天 08:00 浆料批次切换
H_MAINT = 14 * 24 + 2                   # 第 14 天保养降速 2h
IMG_N = 60                              # CCD 帧数（8h 一帧）
IMG_STEP_H = 8

ROWS = pd.date_range(T0, periods=N, freq="10min")
HOURS = np.arange(N) / 6.0
DAY = HOURS / 24.0


def ramp(h, start, per_day, cap):
    return np.clip((h - start) / 24.0 * per_day, 0.0, cap)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    noise = lambda s: rng.normal(0, s, N)
    h = HOURS

    fault = ramp(h, H_FAULT, 0.0008, 0.008)          # 右间隙 mm
    fault_eff = ramp(h - 6.0, H_FAULT, 1.6 / 12.0, 1.6)   # 优品率用（6h 滞后、12 天线性）
    recipe = (h >= H_RECIPE).astype(float)
    maint = (h >= H_MAINT) & (h < H_MAINT + 2)

    speed_f = np.where(maint, 0.85, 1.0)

    dcs = pd.DataFrame({"时间": ROWS.strftime("%Y-%m-%d %H:%M:%S")})
    dcs["L5-SL-SC01"] = np.round(48.5 + 1.0 * recipe + noise(0.15), 3)
    dcs["L5-SL-VSC01"] = np.round(3500.0 + 30.0 * recipe + noise(60), 1)
    dcs["L5-CT-GAP-L01"] = np.round(0.250 + noise(0.0015), 4)
    dcs["L5-CT-GAP-R01"] = np.round(0.250 + fault + noise(0.0015), 4)
    dcs["L5-CT-PMP-SP01"] = np.round(42.0 * speed_f + noise(0.4), 2)
    dcs["L5-OV-Z1-TE01"] = np.round(85.0 + noise(0.6), 2)
    dcs["L5-OV-Z2-TE01"] = np.round(110.0 + noise(0.7), 2)
    dcs["L5-OV-Z3-TE01"] = np.round(95.0 + noise(0.6), 2)
    dcs["L5-CAL-P01"] = np.round(18.0 + noise(0.25), 3)
    dcs["L5-CAL-TE01"] = np.round(88.0 + noise(0.8), 2)
    dcs["L5-WD-TN01"] = np.round(950.0 * speed_f + noise(9), 1)
    dcs["L5-LN-SPD01"] = np.round(35.0 * speed_f + noise(0.15), 3)
    dcs["L5-ENV-TE01"] = np.round(25.0 + 1.5 * np.sin(2 * np.pi * (h / 24 - 0.35)) + noise(0.5), 2)
    dcs["L5-GA-AD-AVG01"] = np.round(96.0 - 0.06 * fault * 12 + noise(0.12), 3)
    dcs["L5-GA-AD-CV01"] = np.round(1.25 + 0.075 * fault * 12 + noise(0.03), 3)
    dcs["L5-GA-EDGE-R01"] = np.round(0.10 - 0.133 * fault * 12 + noise(0.05), 3)
    dcs["L5-GA-EDGE-L01"] = np.round(-0.10 + noise(0.05), 3)
    dip = np.where(maint, -0.4, 0.0)
    dcs["L5-QM-YIELD01"] = np.round(98.5 - 1.9 * (fault_eff / 1.6) + dip + noise(0.06), 3)
    dcs["L5-MES-RECY01"] = np.where(h >= H_RECIPE, 12.0, 8.0)
    mode = np.where(maint, 2, 1)
    dcs["L5-LINE-MODE01"] = mode
    batch = (h // 12).astype(int)
    dcs["L5-MES-BATCH01"] = [f"{(T0 + pd.Timedelta(hours=12 * b)).strftime('%Y%m%d')}-B{b % 2 + 1:02d}" for b in batch]
    dcs.to_csv(DATA / "L5_dcs_process_10min.csv", index=False, encoding="utf-8-sig")

    # ---- PROF 面密度横向剖面（30min，24 位点） ------------------------------
    pn = 24
    prof_rows = pd.date_range(T0, periods=DAYS * 48, freq="30min")   # 1008 快照
    hp = (np.arange(len(prof_rows)) / 2.0)
    fp = ramp(hp, H_FAULT, 0.0008, 0.008)
    base = 96.0 + 0.15 * np.cos(np.linspace(-np.pi, np.pi, pn))       # 轻微抛物
    edge = np.zeros(pn)
    edge[int(pn * 0.85):] = -1.0                                       # 右缘 15% 位点
    mat = np.zeros((len(prof_rows), pn))
    for i in range(len(prof_rows)):
        # full-fault right-edge thinning = -1.5% of 96 g/m² ≈ -1.44 (matches the
        # online gauge L5-GA-EDGE-R01 going +0.10% → -1.50%)
        mat[i] = base + edge * (fp[i] / 0.008) * 1.44 + rng.normal(0, 0.02, pn) + 0.008 * rng.normal()
    prof = pd.DataFrame({"时间": prof_rows.strftime("%Y-%m-%d %H:%M:%S")})
    for j in range(pn):
        prof[f"pos_{j+1:02d}"] = np.round(mat[:, j], 3)
    prof.to_csv(DATA / "L5_ad_scan_30min.csv", index=False, encoding="utf-8-sig")

    # ---- MAP 辊压厚度网格（2h，5×4） ---------------------------------------
    map_times = pd.date_range(T0, ROWS[-1], freq="2h")
    hm = (map_times - T0).total_seconds().to_numpy() / 3600.0
    fm = ramp(hm, H_FAULT, 0.0008, 0.008)
    rows = []
    for i, ts in enumerate(map_times):
        for y in range(4):
            for x in range(5):
                side = 1.5 * (fm[i] / 0.008) if x >= 3 else 0.0     # 右侧三列 +1.5μm
                v = 188.0 + 0.15 * np.cos(np.linspace(-np.pi, np.pi, 5))[x] + side + rng.normal(0, 0.3)
                rows.append((ts.strftime("%Y-%m-%d %H:%M:%S"), x, y, round(float(v), 3)))
    pd.DataFrame(rows, columns=["时间", "x", "y", "L5-CAL-TH-Um"]).to_csv(
        DATA / "L5_calender_map_2h.csv", index=False, encoding="utf-8-sig")

    # ---- IMG CCD 表面检测（8h 一帧，60 帧） --------------------------------
    img_dir = DATA / "ccd_frames"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_times = pd.date_range(T0, periods=IMG_N, freq=f"{IMG_STEP_H}h")
    idx_rows = []
    for i, ts in enumerate(img_times):
        g = np.random.default_rng(SEED + 1000 + i)
        base_img = g.normal(38, 3, (128, 128)) + 12 * np.sin(np.linspace(0, 3 * np.pi, 128))[None, :]
        n_def = 6 if i >= 30 else 2                       # 第 30 帧起缺陷增多（≈第 10 天）
        for k in range(n_def):
            cy, cx = g.integers(12, 116), g.integers(12, 116)
            rr = g.integers(2, 4)
            yy, xx = np.ogrid[:128, :128]
            base_img[(yy - cy) ** 2 + (xx - cx) ** 2 <= rr ** 2] += 140
        arr = np.clip(base_img, 0, 255).astype(np.uint8)
        name = f"ccd_{ts.strftime('%Y%m%d_%H%M%S')}.png"
        Image.fromarray(arr, mode="L").save(img_dir / name)
        idx_rows.append((ts.strftime("%Y-%m-%d %H:%M:%S"), f"ccd_frames/{name}"))
    pd.DataFrame(idx_rows, columns=["时间", "文件"]).to_csv(
        DATA / "L5_ccd_index.csv", index=False, encoding="utf-8-sig")

    # ---- TXT 操作备注 -------------------------------------------------------
    notes = [
        ("2026-09-27 10:20", "浆料管路例行清洗 40min，未停机"),
        ("2026-10-01 08:00", "浆料批次切换：S-4481 → S-4492，固含量按新批次工艺卡执行"),
        ("2026-10-02 23:40", "夜班：涂布辊右端偶有周期性异响，已报设备员登记"),
        ("2026-10-08 02:00", "计划保养：涂布/辊压降速 2h，更换刮刀密封条"),
        ("2026-10-11 14:30", "更换过滤滤芯，涂布泵入口压力恢复正常"),
    ]
    pd.DataFrame(notes, columns=["时间", "备注"]).to_csv(
        DATA / "L5_operator_notes.csv", index=False, encoding="utf-8-sig")

    # ---- LAB 化验（辅助表，稳定模式应被列为 auxiliary） ---------------------
    lab_times = pd.date_range(T0, ROWS[-1], freq="2h")
    hl = (lab_times - T0).total_seconds().to_numpy() / 3600.0
    fl = ramp(hl, H_FAULT, 0.0008, 0.008)
    lab = pd.DataFrame({"时间": lab_times.strftime("%Y-%m-%d %H:%M:%S")})
    lab["L5-LAB-PEEL01"] = np.round(1.85 - 0.10 * (fl / 0.008) + rng.normal(0, 0.04, len(lab_times)), 3)
    lab["L5-LAB-PORO01"] = np.round(16.5 + 0.25 * (fl / 0.008) + rng.normal(0, 0.2, len(lab_times)), 2)
    lab["L5-LAB-H2O01"] = np.round(420 + rng.normal(0, 15, len(lab_times)), 1)
    lab.to_csv(DATA / "L5_lab_electrode_2h.csv", index=False, encoding="utf-8-sig")

    # ---- 参数对照说明（.md 含"说明"→ context；正文只用列表不用大表格） ------
    lines = [
        "# L5 极片涂布产线参数代号对照说明", "",
        "## 命名规则", "",
        "- `L5-<工段>-<含义>-<序号>`；L5 = 5 号涂布线；工段：SL 浆料 / CT 涂布 / OV 烘箱 / CAL 辊压 / WD 收卷 / LN 主线 / GA 在线检测 / QM 质量 / MES 生产管理 / ENV 环境 / LAB 化验", "",
        "## 代号明细", "",
        "- `L5-SL-SC01` = 浆料固含量（%，目标 48.5）",
        "- `L5-SL-VSC01` = 浆料粘度（mPa·s，目标 3500）",
        "- `L5-CT-GAP-L01` / `L5-CT-GAP-R01` = 涂布间隙左/右（mm，目标 0.250；左右独立丝杆）",
        "- `L5-CT-PMP-SP01` = 涂布泵转速（rpm）",
        "- `L5-OV-Z1/Z2/Z3-TE01` = 烘箱一/二/三区风温（℃，目标 85/110/95）",
        "- `L5-CAL-P01` = 辊压压力（MPa，目标 18.0）；`L5-CAL-TE01` = 辊压温度（℃）",
        "- `L5-WD-TN01` = 收卷张力（N）；`L5-LN-SPD01` = 主线速（m/min）",
        "- `L5-GA-AD-AVG01` = 在线面密度平均（g/m²，目标 96.0）；`L5-GA-AD-CV01` = 面密度横向 CV（%，内控 ≤2.0）",
        "- `L5-GA-EDGE-L01` / `L5-GA-EDGE-R01` = 左/右边缘面密度偏差（%，内控 ±1.0）",
        "- `L5-QM-YIELD01` = 综合优品率（%，目标 ≥98.0）",
        "- `L5-MES-BATCH01` = 批次号（12h 一批）；`L5-MES-RECY01` = 回浆比例（%）；`L5-LINE-MODE01` = 1 正常 / 2 降速保养",
        "- `L5-LAB-PEEL01` = 极片剥离强度（N/mm）；`L5-LAB-PORO01` = 孔隙率（%）；`L5-LAB-H2O01` = 水分（ppm）",
        "",
        "## 物理常识", "",
        "- 涂布间隙左右不一致 → 该侧面密度偏移（间隙大 → 面密度偏薄）→ 横向 CV 上升",
        "- 面密度偏薄区域经辊压后厚度略低、烘干后易露箔，CCD 缺陷斑点增多",
        "- 浆料固含量/粘度变化影响泵送与干燥，但不直接造成左右不对称",
        "- 内控：面密度 96.0±1.5 g/m²，CV ≤2.0%，边缘偏差 ±1.0%，优品率 ≥98.0%",
    ]
    (DATA / "L5_参数对照说明.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- 清单 + 真值 ---------------------------------------------------------
    def sha(p: Path) -> str:
        return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()

    manifest = {
        "generator": "generate_l5_dataset.py", "seed": SEED,
        "window": [str(ROWS[0]), str(ROWS[-1])],
        "files": {f.name: {"sha256": sha(f)} for f in sorted(DATA.rglob("*")) if f.is_file()},
    }
    (ROOT / "generation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    truth = """# L5 E2E 真值（评分参考——不得喂给分析端）

注入故障：2026-10-03 00:00（=T0+9 天）起涂布辊右端轴承磨损。
传导链：右间隙 +0.008mm（渐进）→ 右缘面密度偏薄（边缘偏差 +0.10% → −1.50%）→
横向 CV 1.25% → 2.15%（超内控 2.0%）→ 优品率 98.5% → ~96.6%（滞后 6h）；
CCD 缺陷斑点 2 → 6/帧（第 30 帧起）；辊压厚度图右侧三列 +1.5μm。
化验：剥离强度微降、孔隙率微升（弱信号）。
混杂项：10-01 浆料批次切换（固含量 +1.0、粘度 +30、回浆 8→12%）——影响整体水平、不造成左右不对称。
干扰项：10-08 计划保养降速 2h（非稳态段）；10-02 夜班备注"涂布辊右端异响"（指向性线索）。
预期结论形态：DETERMINED——涂布右侧机械性渐变故障（右轴承/丝杆），单侧证据链。
"""
    (ROOT / "ground_truth.md").write_text(truth, encoding="utf-8")

    print(json.dumps({
        "dcs": list(dcs.shape), "prof": list(prof.shape), "map_rows": len(rows),
        "images": IMG_N, "notes": len(notes), "lab": list(lab.shape),
        "data_dir": str(DATA),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
