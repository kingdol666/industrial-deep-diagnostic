# -*- coding: utf-8 -*-
"""L5 锂电正极极片涂布线 — 多源异构场景数据生成器（确定性，真实工况量级）。

写入 data/L5_COAT_20261001-20261021/：
  L5_coat_main_10min.csv      DCS 主表：工艺参数 + 在线质量（10 min × 21 天 = 3024 行 × 25 列）
  L5_AREAL_PROFILE_10min.csv  面密度横向剖面：时间 × 41 测点（独立文件，pos_01=操作侧）
  L5_lab_quality_2h.csv       化验表：5 项互不相关指标（负样本：不应被识别为剖面）
  L5_operator_notes.csv       操作交接班备注（时间锚定文本）
  L5_ccd_index.csv + L5_ccd_frame_*.png  CCD 表面检测图像流（63 帧 + 索引）
  三份说明文档（背景/异常/参数代号）

注入事件（出题口径，详见 workspace/l5-coat-multiskill-eval/ground_truth.md）：
  E1 设备性缓漂（主因）：2026-10-08 00:00 起操作侧涂布间隙微开（螺杆微松），
     GAP-OS 120→124.6 μm，操作侧边缘面密度渐进增厚至 +3.3 g/m²（约 +1.5%），
     CV 1.25%→2.2%，优品率滞后 6 h 下滑（末段约 96.4%）；全幅均值基本不变。
  D1 干扰（全幅阶跃）：2026-10-12 08:00 浆料批次 SL-2231→SL-2245，固含量 +0.25、
     粘度 +150，面密度 +0.35 g/m² 阶跃 24 h 内衰减；无空间选择性。
  D2 干扰（后期放大器）：2026-10-15 02:00 起烘箱三段加热效率下降（HOUT3 45→75%，
     T3 实际 118→116.5 ℃），含水率 320→470 ppm（内控 ≤500），轻微拖累优品率。
  计划停机/换卷窗口（LINE-MODE=2）：10-05 08:00、10-12 08:00、10-19 08:00。
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

SEED = 20261017
T0 = pd.Timestamp("2026-10-01 00:00:00")
DAYS = 21
STEP_MIN = 10
N = DAYS * 24 * 60 // STEP_MIN            # 3024
HOURS = np.arange(N) * (STEP_MIN / 60.0)  # 0 .. 503.83

DATA = Path(__file__).resolve().parents[2] / "data" / "L5_COAT_20261001-20261021"
GT_NONE = None  # ground truth lives outside the data folder

H_FAULT = 7 * 24          # 2026-10-08 00:00 间隙开始微开
H_SLURRY = 11 * 24 + 8    # 2026-10-12 08:00 浆料批次切换
H_OVEN = 14 * 24 + 2      # 2026-10-15 02:00 烘箱三段效率下降
SLOWDOWN_WINDOWS = [(4 * 24 + 8, 1.0), (H_SLURRY, 1.0), (18 * 24 + 8, 2.0)]

PROFILE_OFFSET_MIN = 5    # 剖面扫描完成时刻比 DCS 晚 5 min
PROFILE_POS_MM = np.arange(25, 640, 15)   # 25..625 mm，41 点；pos_01=操作侧(OS)

FAULT_EDGE_GSM = 3.3      # 操作侧边缘末端增量 g/m²（≈+1.5%）
FAULT_SIGMA_MM = 85.0     # 横向衰减尺度


def ramp(start_h: float) -> np.ndarray:
    span = HOURS[-1] - start_h
    return np.clip((HOURS - start_h) / span, 0.0, 1.0)


def in_window(h, start, dur):
    return (h >= start) & (h < start + dur)


def noise(rng, n, s):
    e = rng.normal(0, s, n)
    for i in range(1, n):
        e[i] += 0.3 * e[i - 1]
    return e


def build_main() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = N
    r_fault = ramp(H_FAULT)
    r_fault_lag = ramp(H_FAULT - 6.0)
    r_oven = ramp(H_OVEN)
    r_oven_lag = ramp(H_OVEN - 3.0)
    slurry_on = (HOURS >= H_SLURRY).astype(float)
    slow = np.zeros(n, dtype=bool)
    for s, d in SLOWDOWN_WINDOWS:
        slow |= in_window(HOURS, s, d)
    speed_f = np.where(slow, 0.94, 1.0)

    dip = np.zeros(n)
    for s, d in SLOWDOWN_WINDOWS:
        dip += np.where(in_window(HOURS, s, d), 0.35, 0.0)

    vals: dict[str, object] = {}
    vals["L5-SLRY-VISC"] = 4500 + 150 * slurry_on + noise(rng, n, 25)
    vals["L5-SLRY-SC"] = 51.5 + 0.25 * slurry_on + noise(rng, n, 0.05)
    vals["L5-SLRY-TEMP"] = 25.0 + 0.8 * np.sin(2 * np.pi * HOURS / 24) + noise(rng, n, 0.15)
    vals["L5-COAT-GAP-OS"] = 120.0 + 4.6 * r_fault + noise(rng, n, 0.12)
    vals["L5-COAT-GAP-DS"] = 120.0 + noise(rng, n, 0.10)
    vals["L5-COAT-SPD"] = 35.0 * speed_f + noise(rng, n, 0.08)
    vals["L5-OVEN-T1"] = 110.0 + noise(rng, n, 0.45)
    vals["L5-OVEN-T2"] = 120.0 + noise(rng, n, 0.45)
    vals["L5-OVEN-T3"] = 118.0 - 1.5 * r_oven + noise(rng, n, 0.20)
    vals["L5-OVEN-T4"] = 90.0 + noise(rng, n, 0.40)
    vals["L5-OVEN-HOUT3"] = 45.0 + 30.0 * r_oven + noise(rng, n, 0.8)
    vals["L5-OVEN-FAN1-HZ"] = 40.0 + noise(rng, n, 0.15)
    vals["L5-OVEN-FAN2-HZ"] = 40.0 + noise(rng, n, 0.15)
    vals["L5-OVEN-FAN3-HZ"] = 40.0 + noise(rng, n, 0.15)
    vals["L5-OVEN-NMP"] = 380 + 20 * r_oven + noise(rng, n, 12)
    vals["L5-MSR-WT-AVG"] = (220.0 + 0.35 * slurry_on * np.exp(-np.clip(HOURS - H_SLURRY, 0, None) / 12.0)
                             + 0.05 * r_fault + noise(rng, n, 0.12))
    vals["L5-MSR-WT-CV"] = 1.25 + 0.95 * r_fault + noise(rng, n, 0.025)
    vals["L5-MSR-EDGE-OS"] = 0.15 + 1.75 * r_fault + noise(rng, n, 0.04)
    vals["L5-MSR-EDGE-DS"] = -0.25 + noise(rng, n, 0.04)
    vals["L5-MSR-MOIST"] = 320 + 150 * r_oven + noise(rng, n, 8)
    vals["L5-QLT-YIELD"] = (98.35 - 1.70 * r_fault_lag - 0.30 * r_oven_lag + dip
                            + noise(rng, n, 0.05))

    batch_idx = (HOURS // 12).astype(int)
    t = T0 + pd.to_timedelta(HOURS, unit="h")
    vals["L5-MES-BATCH"] = [f"L5-{x.strftime('%Y%m%d')}-B{b % 2 + 1:02d}"
                            for x, b in zip(t, batch_idx)]
    vals["L5-MES-SHIFT"] = ["甲乙丙丁"[b % 4] for b in batch_idx]
    mode = np.ones(n, dtype=int)
    mode[slow] = 2
    vals["L5-LINE-MODE"] = mode

    df = pd.DataFrame({"时间": t.strftime("%Y-%m-%d %H:%M:%S")})
    for col, v in vals.items():
        if col == "L5-LINE-MODE":
            df[col] = v.astype(int)
        elif isinstance(v, np.ndarray) and v.dtype != object:
            df[col] = np.round(v.astype(float), 3)
        else:
            df[col] = v
    return df


def build_profile() -> pd.DataFrame:
    """面密度横向剖面：41 点 × 10 min，pos_01=操作侧。E1 故障场 = OS 边缘高斯增厚。"""
    rng = np.random.default_rng(SEED + 1)
    n = N
    times = T0 + pd.to_timedelta(HOURS, unit="h") + pd.Timedelta(minutes=PROFILE_OFFSET_MIN)
    x = PROFILE_POS_MM.astype(float)
    x0, W = float(x[0]), float(x[-1] - x[0])
    r_fault = ramp(H_FAULT)

    crown = -0.4 * np.cos(2 * np.pi * (x - x0) / W)          # 中心 +0.4，两侧 -0.4
    pos_bias = rng.normal(0, 0.02, x.size)
    common = 0.05 * np.sin(2 * np.pi * HOURS / 24) + rng.normal(0, 0.02, n)
    scan = rng.normal(0, 0.12, (n, x.size))
    fault_field = np.outer(FAULT_EDGE_GSM * r_fault, np.exp(-((x - x0) / FAULT_SIGMA_MM) ** 2))
    # 泵总量补偿：扣除均匀量，使全幅均值保持 ~220（平均正常、边缘超差的悖论）
    compensate = fault_field.mean(axis=1, keepdims=True)
    matrix = 220.0 + crown[None, :] + pos_bias[None, :] + common[:, None] + scan + fault_field - compensate

    df = pd.DataFrame({"时间": times.strftime("%Y-%m-%d %H:%M:%S"), "单位": "g/m²"})
    for j in range(x.size):
        df[f"pos_{j + 1:02d}"] = np.round(matrix[:, j], 3)
    return df


def ramp_at(start_h: float, h: np.ndarray) -> np.ndarray:
    span = h[-1] - start_h
    return np.clip((h - start_h) / span, 0.0, 1.0)


def build_lab() -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 2)
    times = pd.date_range(T0, periods=DAYS * 12, freq="2h")
    h = (times - T0).total_seconds().to_numpy() / 3600.0
    slurry_on = (h >= H_SLURRY).astype(float)
    r_oven = ramp_at(H_OVEN, h)
    df = pd.DataFrame({"时间": times.strftime("%Y-%m-%d %H:%M:%S")})
    df["L5-LAB-VISC"] = np.round(4510 + 140 * slurry_on + noise(rng, len(h), 20), 0)
    df["L5-LAB-SC"] = np.round(51.5 + 0.24 * slurry_on + noise(rng, len(h), 0.04), 3)
    df["L5-LAB-MOIST"] = np.round(325 + 145 * r_oven + noise(rng, len(h), 10), 0)
    df["L5-LAB-WT"] = np.round(220.0 + noise(rng, len(h), 0.25), 3)
    df["L5-LAB-PEEL"] = np.round(1.82 + noise(rng, len(h), 0.05), 3)
    return df


NOTES = [
    ("2026-10-01 07:55", "交接班：运行正常，优品率 98.4% 附近，无异常记录。"),
    ("2026-10-05 08:10", "计划换卷，卷芯对中重新调整，降速约 1 小时。"),
    ("2026-10-08 09:30", "操作侧边部面密度报警 2 次，离线复测 223.9 g/m²，已通知工艺员。"),
    ("2026-10-10 03:20", "烘箱三段风机有异响，已报修，频率显示正常。"),
    ("2026-10-12 08:00", "浆料批次 SL-2231 切换为 SL-2245，固含量化验 51.7%，换批降速 1 小时。"),
    ("2026-10-14 10:00", "质量周会：优品率连续两周下滑，要求排查测厚仪、浆料与间隙。"),
    ("2026-10-15 09:00", "测厚仪标准片校准完成，偏差在 0.1% 以内。"),
    ("2026-10-17 11:40", "操作侧边缘超差频繁，临时将内控收紧至 ±1.2% 并加严抽检。"),
    ("2026-10-19 08:05", "计划停机 2 小时，检查操作侧刮刀并更换，改善不明显。"),
    ("2026-10-21 07:50", "交接班：优品率约 96.6%，操作侧边部仍偏厚，待深入分析。"),
]


def build_notes() -> pd.DataFrame:
    return pd.DataFrame(NOTES, columns=["时间", "备注"])


def build_images() -> tuple[pd.DataFrame, int]:
    """CCD 表面检测图像流：8 h 一帧 × 63 帧。E1 后操作侧出现渐进变宽变亮的纵向亮纹。"""
    rng = np.random.default_rng(SEED + 3)
    times = pd.date_range(T0 + pd.Timedelta(hours=2), periods=63, freq="8h")
    rows = []
    for k, ts in enumerate(times):
        img = rng.normal(0, 6.0, (120, 160))
        img = np.clip(img, -18, 18)
        # 简易平滑（3x3 均值）模拟表面纹理
        padded = np.pad(img, 1, mode="edge")
        smooth = (padded[:-2, :-2] + padded[:-2, 1:-1] + padded[:-2, 2:] +
                  padded[1:-1, :-2] + padded[1:-1, 1:-1] + padded[1:-1, 2:] +
                  padded[2:, :-2] + padded[2:, 1:-1] + padded[2:, 2:]) / 9.0
        g = 120 + smooth + rng.normal(0, 2.0, smooth.shape)
        if ts >= T0 + pd.Timedelta(hours=H_FAULT):
            frac = min(1.0, (h_frac(ts) - H_FAULT) / (7 * 24.0))
            width = int(round(2 + 3 * frac))
            amp = 10 + 40 * frac
            x0 = 30
            g[:, x0:x0 + width] += amp + rng.normal(0, 1.5, (120, width))
            g[:, x0 + width:x0 + width + 2] += amp * 0.35
        arr = np.clip(g, 0, 255).astype(np.uint8)
        name = f"L5_ccd_frame_{k:03d}.png"
        Image.fromarray(arr, mode="L").save(DATA / name)
        rows.append((ts.strftime("%Y-%m-%d %H:%M:%S"), name))
    return pd.DataFrame(rows, columns=["时间", "文件名"]), 63


def h_frac(ts: pd.Timestamp) -> float:
    return (ts - T0).total_seconds() / 3600.0


def write_csv(path: Path, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    path.write_text(buf.getvalue(), encoding="utf-8-sig", newline="")


def write_docs() -> None:
    (DATA / "工艺背景与设备说明.md").write_text("""# 工艺背景与设备说明（L5 涂布线）

## 一、产线概况
- 产线：L5 锂电池正极极片微凹版/狭缝挤压涂布线，产品 NCM811 正极极片（单面涂布）
- 幅宽：650 mm（涂布宽度 600 mm，两侧各留 25 mm 边部）
- 面密度目标：220 g/m²（内控 ±3 g/m²）；涂布速度约 35 m/min
- 数据窗口：2026-10-01 00:00 ～ 2026-10-21 23:50（21 天），本地时间 +08:00
- 生产组织：12 小时一个批次（`L5-MES-BATCH`），四班两运转（`L5-MES-SHIFT` = 甲/乙/丙/丁）

## 二、工艺流程与设备节点
1. 浆料制备（搅拌罐，批次号管理）：固含量约 51.5 wt%，粘度约 4500 mPa·s
2. 泵送与供浆系统：螺杆泵闭环，按总量控制全幅平均面密度
3. 狭缝挤压涂布头：涂布间隙由操作侧（OS）与传动侧（DS）两根微调丝杆独立设定
   （本数据只有实际值，无设定值列）；正常间隙约 120 μm
4. 烘箱 4 段干燥：T1 110 ℃ / T2 120 ℃ / T3 118 ℃ / T4 90 ℃；每段独立循环风机（约 40 Hz）
5. 在线检测：β 射线面密度仪全幅扫描（`L5_AREAL_PROFILE_10min.csv` 为其原始横向剖面）+
   CCD 表面检测相机（`L5_ccd_index.csv` 索引的图像流）
6. 收卷

## 三、关键控制与常识
- 全幅平均面密度由泵总量闭环维持；间隙单侧开大 → 该侧局部面密度增厚、横向不匀率上升
- 浆料固含量/粘度变化 → 全幅面密度轻微阶跃，无左右选择性
- 烘箱加热/风量不足 → 含水率上升（内控 ≤500 ppm），严重时优品率下降
- CCD 图像中纵向亮纹多与涂布机构（刮刀/间隙）条痕有关，横向暗带多与箔材有关

## 四、质量内控标准
- 面密度：220 ± 3 g/m²（均值口径）
- 横向面密度不匀率（CV）：≤ 2.0%
- 边缘面密度偏差（距边 25 mm）：± 1.5%
- 极片含水率：≤ 500 ppm
- 在线优品率：目标 ≥ 98%

## 五、数据口径
- 主表（DCS/在线）：10 min 采样；`L5-LINE-MODE`：1=正常，2=降速/换卷/换批
- 面密度横向剖面：独立文件，10 min 一帧、每帧 41 个测点（距操作侧边 25～625 mm，
  间距 15 mm），单位 g/m²；扫描完成时刻比主表晚 5 分钟
- 化验表：2 小时抽检（浆料粘度/固含量/含水率/离线面密度/剥离强度）
- CCD 图像：8 小时一帧，索引表 `L5_ccd_index.csv`（时间 + 文件名，160×120 灰度）
- 交接班备注：`L5_operator_notes.csv`（时间 + 备注，均为事实记录）
""", encoding="utf-8")

    (DATA / "异常现象与已做排查.md").write_text("""# 异常现象与已做排查（给分析系统的问题说明书）

## 一、现象描述（客观事实）
- 发现时间：2026-10-08 之后，在线优品率从 98.3% 附近持续下滑，10-21 已跌至约 96.4%～96.6%
- 主要不合格项：**操作侧边缘面密度超差**（距操作侧边 25 mm 处偏厚）与横向面密度不匀率偏高
  （内控 ≤2.0%，近期 2.2%～2.3%）
- 重要事实：**全幅平均面密度始终正常**（219.9～220.4 g/m²），只看均值发现不了问题
- 劣化形态：持续两周以上的缓慢劣化（斜坡形，非台阶）
- 10-15 起极片含水率同步上升（320 → 约 470 ppm，内控 ≤500），尚未超标
- 离线 10-08 复测：操作侧边部 223.9 g/m²（超 +1.5% 内控线）

## 二、时间线上的相关事件（已知事实）
- 2026-10-05 08:00：计划换卷（降速约 1 小时）
- 2026-10-10 03:20：烘箱三段风机异响报修（风机频率显示一直正常）
- 2026-10-12 08:00：浆料批次 SL-2231 → SL-2245（固含量化验 51.7%，规格内）
- 2026-10-15 09:00：测厚仪标准片校准完成，偏差 0.1% 以内
- 2026-10-19 08:00：计划停机 2 小时，更换操作侧刮刀，改善不明显

## 三、车间已做排查（结论均为"正常"或"已做"）
- 泵送系统：泵压力、转速平稳，供浆管路无堵塞
- 浆料：两批次固含量/粘度化验均在规格内
- 测厚仪：标准片校准合格
- 传动侧：间隙、刮刀状态正常，边缘无异常
- CCD：表面检测无贯通缺陷报警，仅操作侧有轻微信号

## 四、我们的问题（希望分析系统回答）
1. 优品率下滑与操作侧边缘超差的**主导原因**是什么？依据是什么？
2. 与 10-12 浆料批次切换、10-10 烘箱风机、10-19 刮刀更换有没有关系？如何区分？
3. 为什么**平均面密度正常、只有操作侧边部劣化**？
4. 现在（10-21）该不该停机检修？给立即 / 短期 / 长期三层处置建议与补测建议。
""", encoding="utf-8")

    (DATA / "参数代号对照说明.md").write_text("""# 参数代号对照说明（L5 涂布线）

## 命名规则
`L5-<节点>-<部位>-<功能>`：SLRY=浆料，COAT=涂布头，OVEN=烘箱，MSR=在线检测，QLT=质量，MES=MES，LAB=化验室。
常用功能码：VISC=粘度、SC=固含量、TEMP=温度、GAP=涂布间隙、SPD=速度、T1-T4=烘箱分段温度、
HOUT=加热输出(%)、FAN-HZ=风机频率、NMP=NMP 浓度、WT=面密度、CV=横向不匀率、EDGE=边缘偏差、MOIST=含水率。

## 主表代号明细（L5_coat_main_10min.csv）
- `L5-SLRY-VISC` 浆料粘度（mPa·s，正常 4400~4700）
- `L5-SLRY-SC` 浆料固含量（wt%，正常 51.2~51.8）
- `L5-SLRY-TEMP` 浆料温度（℃，正常 24~26）
- `L5-COAT-GAP-OS` 操作侧涂布间隙实际值（μm，基准 120）——两根丝杆独立微调，本窗口无设定值列
- `L5-COAT-GAP-DS` 传动侧涂布间隙实际值（μm，基准 120）
- `L5-COAT-SPD` 涂布速度（m/min，正常 34.5~35.3；MODE=2 时降速）
- `L5-OVEN-T1/T2/T3/T4` 烘箱 1~4 段实际温度（℃，基准 110/120/118/90）
- `L5-OVEN-HOUT3` 烘箱 3 段加热输出（%，正常 44~46；持续上升=该段效能下降线索）
- `L5-OVEN-FAN1/2/3-HZ` 烘箱循环风机频率（Hz，基准 40，本窗口恒定）
- `L5-OVEN-NMP` 烘箱排风 NMP 浓度（ppm，正常 360~410）
- `L5-MSR-WT-AVG` 在线全幅平均面密度（g/m²，内控 217~223）
- `L5-MSR-WT-CV` 横向面密度不匀率（%，内控 ≤2.0）
- `L5-MSR-EDGE-OS` 操作侧边缘面密度偏差（%，距边 25 mm，内控 ±1.5）
- `L5-MSR-EDGE-DS` 传动侧边缘面密度偏差（%，内控 ±1.5）
- `L5-MSR-MOIST` 极片含水率（ppm，内控 ≤500）
- `L5-QLT-YIELD` 在线优品率（%，目标 ≥98）
- `L5-MES-BATCH` 生产批次号（12 h 一批）；`L5-MES-SHIFT` 班组（甲/乙/丙/丁，12 h 轮转）
- `L5-LINE-MODE` 运行状态码（1=正常，2=降速/换卷/换批）

## 面密度横向剖面（L5_AREAL_PROFILE_10min.csv）
- 一行 = 一次全幅扫描（完成时刻），10 min 一帧；比主表 DCS 采样点晚 5 分钟
- `单位` 列 = g/m²；`pos_01`～`pos_41` = 横向 41 个测点（间距 15 mm）
- **pos_01 = 操作侧（OS）边缘（距边 25 mm），pos_41 = 传动侧（DS）边缘（距边 625 mm）**
- 这 41 列是同一物理量（面密度）沿幅宽方向的空间采样，是"向量随时间"，不是 41 个独立变量

## CCD 图像流（L5_ccd_index.csv + L5_ccd_frame_XXX.png）
- 索引表两列：`时间`（采集时刻）、`文件名`（同目录相对路径）
- 160×120 灰度图，8 小时一帧；图像中纵坐标为运行方向（MD），横坐标为幅宽方向（TD）
- 图像横坐标左端 ≈ 操作侧、右端 ≈ 传动侧（与剖面 pos 轴同向）

## 化验表（L5_lab_quality_2h.csv）
2 小时抽检 5 项，量纲互不相同：粘度/固含量/含水率/离线面密度/剥离强度（N/m）。
它们不是同一物理量的空间扫描，不能按"剖面"理解。

## 交接班备注（L5_operator_notes.csv）
时间 + 备注两列，均为当班事实记录（报警、报修、换批、校准等），不包含结论性判断。
""", encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    main_df = build_main()
    profile_df = build_profile()
    lab_df = build_lab()
    notes_df = build_notes()
    idx_df, n_img = build_images()

    write_csv(DATA / "L5_coat_main_10min.csv", main_df)
    write_csv(DATA / "L5_AREAL_PROFILE_10min.csv", profile_df)
    write_csv(DATA / "L5_lab_quality_2h.csv", lab_df)
    write_csv(DATA / "L5_operator_notes.csv", notes_df)
    write_csv(DATA / "L5_ccd_index.csv", idx_df)
    write_docs()

    print({
        "main": {"rows": len(main_df), "cols": main_df.shape[1]},
        "profile": {"rows": len(profile_df), "cols": profile_df.shape[1],
                    "pos_first_mm": int(PROFILE_POS_MM[0]), "pos_last_mm": int(PROFILE_POS_MM[-1])},
        "lab": {"rows": len(lab_df), "cols": lab_df.shape[1]},
        "notes": {"rows": len(notes_df)},
        "images": n_img,
        "data_dir": str(DATA),
    })


if __name__ == "__main__":
    main()
