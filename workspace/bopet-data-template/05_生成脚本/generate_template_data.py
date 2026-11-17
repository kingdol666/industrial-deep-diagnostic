#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOPET 产线数据模板 —— 样例数据生成器（确定性，固定 seed）
=============================================================

生成内容（本脚本是数据、映射表、本体的唯一来源，三者保证一致）：

  02_data/L3_line_main_10min.csv     主表：DCS 工艺 + 在线质量（10min，21 天）
  02_data/L3_lab_quality_2h.csv      化验表：LIMS 抽检（2h，与主表同一时间轴）
  03_映射文档/tag_mapping.json        代号 → 语义映射（机器可读）
  03_映射文档/tag_mapping.csv         代号 → 语义映射（Excel 维护版）
  03_映射文档/L3_bopet_ontology.json  预构建本体（符合 ontology_schema.json）
  05_生成脚本/generation_manifest.json 生成清单（seed / 行数 / sha256 / 注入事件）

运行：
  .claude/shared/scripts/.venv/Scripts/python.exe generate_template_data.py

设计要点（写入本脚本的"物理模型"）：
  * 正常工况：各信号围绕设定值/目标值做有界噪声波动，量级取 BOPET 12μm 光膜典型运行值；
  * 注入故障：第 9 天起 TDO 北侧拉伸区（Z4）热风加热能力缓慢衰减 —— 设定值不变、
    实际风温缓慢下偏、加热输出持续上升直至触及 80% 上限（执行器饱和），
    下游表现为北边缘厚度偏厚 → 横向不匀率上升 → 优品率滞后下降；
  * 干扰项（用于检验分析系统的判别能力，不是答案）：
      1) 第 8 天原料批次切换 + 回料掺入比例 8%→12%（雾度/晶点小幅阶跃，与故障起点仅差 1 天）；
      2) 环境温度随季节/昼夜下降（与北侧风温同向下降，需靠"南侧不变"排除）；
      3) 过滤器压差锯齿上升 + 两次计划换网（与熔体压力波动相关）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# 常量与时间轴
# --------------------------------------------------------------------------
SEED = 20261015
T0 = pd.Timestamp("2026-09-20 00:00:00")   # 数据起点
DAYS = 21
STEP_MIN = 10
N = DAYS * 24 * 60 // STEP_MIN             # 3024 行
LAB_STEP_H = 2                             # 化验抽检间隔（小时）

PKG_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PKG_ROOT / "02_data"
MAP_DIR = PKG_ROOT / "03_映射文档"
GEN_DIR = PKG_ROOT / "05_生成脚本"

TIME_COL = "时间"
ROWS = pd.date_range(T0, periods=N, freq=f"{STEP_MIN}min")
HOURS = np.arange(N) * (STEP_MIN / 60.0)          # 自起点的小时数
DAY = HOURS / 24.0

# 事件时间线（小时偏移，自 2026-09-20 00:00 起）
H_RECYCLE = 7 * 24 + 8          # 2026-09-27 08:00 原料批次切换 / 回料比例上调
H_FAULT = 8 * 24                # 2026-09-28 00:00 TDO 北侧加热能力开始衰减
FAULT_RATE_C_PER_DAY = 0.15     # 衰减速率 ℃/天
FAULT_MAX_C = 1.95              # 窗口末端累计偏差 ℃
FILTER_CHANGES = [9 * 24 + 2, 16 * 24 + 2]   # 换网时刻（02:00），持续 2h
SLOWDOWN_WINDOWS = [(H_RECYCLE, 40 / 60.0)] + [(h, 2.0) for h in FILTER_CHANGES]

# 膜厚横向剖面（独立测厚扫描文件，非主表列）
PROFILE_STEP_MIN = 10                        # 每 10 分钟一帧扫描剖面
PROFILE_OFFSET_MIN = 5                       # 扫描完成时刻比 DCS 采样点晚 5 分钟（避免被当成同一行）
PROFILE_POS_MM = np.arange(50, 6300, 100)    # 距北侧边缘 50~6250 mm，共 63 个测点
PROFILE_EDGE_UM_PER_C = 0.114                # 北侧加热偏差每 1℃ 引起边缘增厚 μm（末端约 +0.22μm ≈ +1.85%）

MANUFACTURER_NOTE = "本样例为格式模板，产线用真实导出数据替换即可"


def ramp(hours: np.ndarray, start: float, rate_per_day: float, cap: float) -> np.ndarray:
    """线性斜坡：hours>=start 后按天速率增长，封顶 cap。"""
    return np.clip((hours - start) / 24.0 * rate_per_day, 0.0, cap)


def in_window(hours: np.ndarray, start: float, dur_h: float) -> np.ndarray:
    return (hours >= start) & (hours < start + dur_h)


def yield_dip(hours: np.ndarray, start: float, dur_h: float, depth: float,
              recover_h: float = 1.5) -> np.ndarray:
    """降速/换网造成的优品率凹陷 + 线性恢复。"""
    out = np.zeros_like(hours)
    for i, h in enumerate(hours):
        if start <= h < start + dur_h:
            out[i] = -depth
        elif start + dur_h <= h < start + dur_h + recover_h:
            out[i] = -depth * (1 - (h - start - dur_h) / recover_h)
    return out


# --------------------------------------------------------------------------
# 信号定义表（唯一来源：数据列 / 映射表 / 本体 都由它派生）
# role: process=工艺参数 | quality=质量指标 | control=控制量(设定/输出/测量)
#       env=环境量 | meta=批次/状态元数据
# --------------------------------------------------------------------------
SIGNALS = [
    # --- 干燥与挤出 -------------------------------------------------------
    dict(code="L3-DRY-DP-TE01", name="干燥塔露点温度", unit="℃", stage="原料干燥",
         equip="L3-DRY", loop="AI-1101", role="process", target=-60.0,
         rng=(-62.0, -58.0), meaning="切片干燥塔出口空气露点，反映切片含水控制水平；露点劣化会把水分带进熔体",
         law="干燥平衡：露点 ← 再生风温度/风量，含水率 ∝ 露点"),
    dict(code="L3-DRY-RG-TE01", name="再生风加热温度", unit="℃", stage="原料干燥",
         equip="L3-DRY", loop="TIC-1102", role="process", target=175.0,
         rng=(172.0, 178.0), meaning="干燥塔再生风加热器出口温度，决定除湿能力", law="干燥再生热平衡"),
    dict(code="L3-EX-MGT-TE01", name="主挤出机计量段温度", unit="℃", stage="熔融挤出",
         equip="L3-EX", loop="TIC-1201", role="process", target=282.0,
         rng=(281.0, 283.2), meaning="计量段熔体温度，决定熔体粘度与泵送稳定性", law="Arrhenius 粘度-温度依赖 η=A·exp(Ea/RT)"),
    dict(code="L3-EX-PT01", name="熔体压力（模头前）", unit="bar", stage="熔融挤出",
         equip="L3-EX", loop="PIC-1202", role="process", target=110.0,
         rng=(107.0, 113.5), meaning="模头前熔体压力，反映计量泵输送与管路阻力状态", law="计量泵输送 Q∝n/η(T)；滤网堵塞时 ΔP 上升"),
    dict(code="L3-EX-CUR01", name="主挤出机电流", unit="A", stage="熔融挤出",
         equip="L3-EX", loop="II-1203", role="process", target=212.0,
         rng=(205.0, 218.0), meaning="主挤出机螺杆驱动电流，与扭矩/熔体粘度同向", law="电机功率 ∝ 扭矩 × 转速"),
    dict(code="L3-EX-SPD01", name="主挤出机螺杆转速", unit="rpm", stage="熔融挤出",
         equip="L3-EX", loop="SI-1204", role="process", target=63.0,
         rng=(62.0, 64.0), meaning="主挤出机转速，与铸片厚度基准成正比", law="体积守恒：挤出量 ∝ 转速"),
    dict(code="L3-FL-DP01", name="熔体过滤器压差", unit="bar", stage="熔融挤出",
         equip="L3-FL", loop="PDI-1205", role="process", target=0.8,
         rng=(0.5, 2.5), meaning="熔体过滤器进出口压差，随时间锯齿上升，换网后复位；是滤网寿命直接指标",
         law="Darcy 渗流 ΔP∝μ·Q·R_filter(t)"),
    dict(code="L3-DIE-TE01", name="模头温度", unit="℃", stage="熔融挤出",
         equip="L3-DIE", loop="TIC-1301", role="process", target=285.0,
         rng=(284.3, 285.8), meaning="模头区熔体温度，影响模口出膜厚度横向分布", law="同主挤 Arrhenius 依赖"),
    dict(code="L3-DIE-HOUT01", name="模头加热输出", unit="%", stage="熔融挤出",
         equip="L3-DIE", loop="TIC-1301.OUT", role="control", target=44.0,
         rng=(40.0, 48.0), meaning="模头加热器输出百分比（闭环输出量），长期偏高说明热损失/加热器老化",
         law="闭环输出 = f(偏差)；输出持续偏高 = 执行器效能下降"),
    # --- 铸片（急冷） -----------------------------------------------------
    dict(code="L3-CR-TE01", name="铸片辊表面温度", unit="℃", stage="铸片急冷",
         equip="L3-CR", loop="TIC-1401", role="process", target=26.5,
         rng=(26.2, 26.9), meaning="急冷辊表面温度，决定预结晶度；过高会发雾、过低会粘辊",
         law="骤冷结晶度 Xc ∝ 1/冷却速率"),
    dict(code="L3-CR-CW-IN-TE01", name="急冷辊冷却水进水温度", unit="℃", stage="铸片急冷",
         equip="L3-CW", loop="TI-1402", role="env", target=22.0,
         rng=(21.6, 22.4), meaning="循环水系统来水温度（随季节缓慢变化），是辊温控制的外部输入",
         law="换热 Q=K·A·ΔT_lm"),
    dict(code="L3-CR-CW-OUT-TE01", name="急冷辊冷却水回水温度", unit="℃", stage="铸片急冷",
         equip="L3-CW", loop="TI-1403", role="process", target=24.2,
         rng=(23.9, 24.7), meaning="回水温度；进/回水温差反映换热能力（结垢会缩小温差）", law="Q=K·A·ΔT_lm"),
    dict(code="L3-CR-CW-FQ01", name="急冷辊冷却水流量", unit="m³/h", stage="铸片急冷",
         equip="L3-CW", loop="FI-1404", role="process", target=60.0,
         rng=(58.0, 63.0), meaning="辊内冷却水流量，与温差共同决定换热量", law="Q = c·m·ΔT"),
    dict(code="L3-CR-SPD01", name="铸片辊线速度", unit="m/min", stage="铸片急冷",
         equip="L3-CR", loop="SI-1405", role="process", target=16.40,
         rng=(16.30, 16.52), meaning="铸片线速，与挤出量共同决定铸片厚度基准", law="体积守恒（铸片段）"),
    dict(code="L3-CR-ES-V01", name="静电贴附电压", unit="kV", stage="铸片急冷",
         equip="L3-CR", loop="EI-1406", role="control", target=7.0,
         rng=(6.8, 7.3), meaning="静电吸附电压，保证铸片与冷辊贴合（不足会产生横向厚度条纹）", law="静电吸附力 ∝ V²/d²"),
    # --- MDO 纵拉 ---------------------------------------------------------
    dict(code="L3-MDO-PH1-TE01", name="纵拉预热辊1温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2101", role="process", target=78.0,
         rng=(77.4, 78.6), meaning="预热段第1辊温度（接近 PET Tg≈78℃）", law="PET 玻璃化转变：预热需贴近 Tg"),
    dict(code="L3-MDO-PH2-TE01", name="纵拉预热辊2温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2102", role="process", target=79.0,
         rng=(78.4, 79.6), meaning="预热段第2辊温度", law="同上"),
    dict(code="L3-MDO-PH3-TE01", name="纵拉预热辊3温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2103", role="process", target=80.0,
         rng=(79.4, 80.6), meaning="预热段第3辊温度", law="同上"),
    dict(code="L3-MDO-ST1-TE01", name="纵拉拉伸辊1温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2104", role="process", target=86.5,
         rng=(85.8, 87.2), meaning="拉伸段第1辊温度（Tg 以上 8℃ 左右，保证均匀拉伸）", law="拉伸应力-温度关系"),
    dict(code="L3-MDO-ST2-TE01", name="纵拉拉伸辊2温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2105", role="process", target=87.0,
         rng=(86.4, 87.8), meaning="拉伸段第2辊温度", law="同上"),
    dict(code="L3-MDO-AN-TE01", name="纵拉定型辊温度", unit="℃", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="TIC-2106", role="process", target=35.0,
         rng=(33.6, 36.4), meaning="纵拉出口急冷定型辊温度", law="急冷抑制回弹"),
    dict(code="L3-MDO-V01", name="纵拉入口速度", unit="m/min", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="SI-2107", role="process", target=16.40,
         rng=(16.32, 16.52), meaning="纵拉慢辊线速度（拉伸入口）", law="拉伸比 λ=v2/v1"),
    dict(code="L3-MDO-V02", name="纵拉出口速度", unit="m/min", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="SI-2108", role="process", target=52.90,
         rng=(52.70, 53.15), meaning="纵拉快辊线速度（拉伸出口）", law="拉伸比 λ=v2/v1"),
    dict(code="L3-MDO-TQ01", name="纵拉机组扭矩", unit="%", stage="纵向拉伸(MDO)",
         equip="L3-MDO", loop="JI-2109", role="process", target=62.0,
         rng=(60.5, 63.5), meaning="纵拉驱动扭矩，反映拉伸应力水平", law="σ = E·ε；扭矩 ∝ 拉伸应力"),
    # --- TDO 横拉（故障注入点） -------------------------------------------
    dict(code="L3-TDO-N-PH-TE01", name="TDO北侧预热区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2301N", role="process", target=155.0,
         rng=(154.4, 155.6), meaning="横拉机北侧预热区热风温度（链铗入机前）", law="对流换热 h∝Re^0.8"),
    dict(code="L3-TDO-S-PH-TE01", name="TDO南侧预热区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2301S", role="process", target=155.0,
         rng=(154.4, 155.6), meaning="横拉机南侧预热区热风温度", law="同上"),
    dict(code="L3-TDO-N-ST-Z4-TE01", name="TDO北侧拉伸区4区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2404N", role="process", target=240.0,
         rng=(237.8, 240.6), meaning="横向拉伸主拉伸区（第4分区）北侧热风实际温度，决定该侧 PET 取向与横向厚度分布",
         law="结晶动力学 Avrami；热收缩 ∝ (T-Tg) 热历史"),
    dict(code="L3-TDO-S-ST-Z4-TE01", name="TDO南侧拉伸区4区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2404S", role="process", target=240.0,
         rng=(239.6, 240.4), meaning="横向拉伸主拉伸区（第4分区）南侧热风实际温度", law="同上"),
    dict(code="L3-TDO-N-AN-Z6-TE01", name="TDO北侧定型区6区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2606N", role="process", target=191.0,
         rng=(190.1, 191.4), meaning="定型区（第6分区）北侧热风温度，决定热收缩率与尺寸稳定性", law="定型度-尺寸稳定性平衡"),
    dict(code="L3-TDO-S-AN-Z6-TE01", name="TDO南侧定型区6区热风温度", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2606S", role="process", target=191.0,
         rng=(190.7, 191.3), meaning="定型区（第6分区）南侧热风温度", law="同上"),
    dict(code="L3-TDO-N-ST-Z4-SP01", name="TDO北侧拉伸区4区温度设定值", unit="℃", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2404N.SP", role="control", target=240.0,
         rng=(240.0, 240.0), meaning="操作设定的北侧拉伸区温度目标值（本窗口内未调整，恒定 240.0）",
         law="——", const=240.0),
    dict(code="L3-TDO-N-Z4-HOUT01", name="TDO北侧4区加热输出", unit="%", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2404N.OUT", role="control", target=45.0,
         rng=(44.0, 80.0), meaning="北侧4区热风加热器输出百分比。闭环输出持续上升直至触及上限，说明加热/送风效能下降（执行器饱和特征）",
         law="闭环输出 = f(偏差)；饱和 = 执行器能力不足"),
    dict(code="L3-TDO-S-Z4-HOUT01", name="TDO南侧4区加热输出", unit="%", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="TIC-2404S.OUT", role="control", target=45.0,
         rng=(43.5, 47.0), meaning="南侧4区热风加热器输出百分比（正常工况下平稳）", law="同上"),
    dict(code="L3-TDO-N-FAN-HZ01", name="TDO北侧循环风机频率", unit="Hz", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="SIC-2405N", role="control", target=85.0,
         rng=(84.8, 85.2), meaning="北侧热风循环风机频率（风量指标），本窗口内恒定 —— 可据此排除风机故障",
         law="风量 ∝ 频率；h∝Re^0.8"),
    dict(code="L3-TDO-S-FAN-HZ01", name="TDO南侧循环风机频率", unit="Hz", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="SIC-2405S", role="control", target=85.0,
         rng=(84.8, 85.2), meaning="南侧热风循环风机频率", law="同上"),
    dict(code="L3-TDO-RAIL-W01", name="TDO出口轨宽", unit="mm", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="WI-2501", role="process", target=6330.0,
         rng=(6324.0, 6336.0), meaning="横拉出口链铗轨距，反映横向拉伸倍率与破膜风险", law="几何守恒（横拉比 × 入口宽度）"),
    dict(code="L3-TDO-CHAIN-I01", name="TDO链铗驱动电流", unit="A", stage="横向拉伸(TDO)",
         equip="L3-TDO", loop="II-2502", role="process", target=40.0,
         rng=(38.0, 42.0), meaning="链铗驱动电流，反映横向拉伸阻力（随拉伸区温度变化）", law="电流 ∝ 拉伸张力"),
    # --- 牵引与收卷 -------------------------------------------------------
    dict(code="L3-PU-TN01", name="牵引入口张力", unit="N", stage="牵引收卷",
         equip="L3-PU", loop="ZI-3101", role="process", target=2270.0,
         rng=(2240.0, 2300.0), meaning="牵引段入口张力，过大产生纵向应变、过小跑偏", law="胡克弹性 σ=E·ε"),
    dict(code="L3-PU-V01", name="牵引速度", unit="m/min", stage="牵引收卷",
         equip="L3-PU", loop="SI-3102", role="process", target=52.95,
         rng=(52.7, 53.2), meaning="牵引线速度（主线速基准）", law="体积守恒"),
    dict(code="L3-WD-TN01", name="卷绕张力", unit="N", stage="牵引收卷",
         equip="L3-WD", loop="ZI-3201", role="process", target=1180.0,
         rng=(1160.0, 1200.0), meaning="收卷张力，影响卷形与膜卷内应力", law="同上"),
    dict(code="L3-WD-V01", name="收卷速度", unit="m/min", stage="牵引收卷",
         equip="L3-WD", loop="SI-3202", role="process", target=52.90,
         rng=(52.7, 53.2), meaning="收卷线速度", law="体积守恒"),
    # --- 在线质量 ---------------------------------------------------------
    dict(code="L3-GA-TH-AVG01", name="在线平均厚度", unit="μm", stage="在线测厚",
         equip="L3-GA", loop="QI-4101", role="quality", target=12.00,
         rng=(11.95, 12.05), meaning="在线测厚仪全幅平均厚度（产品规格 12.0μm，内控 ±0.20μm）",
         law="体积守恒：h = 挤出量/(宽×速)；均值正常不代表分布正常"),
    dict(code="L3-GA-TH-CV01", name="横向厚度不匀率", unit="%", stage="在线测厚",
         equip="L3-GA", loop="QI-4102", role="quality", target=1.40,
         rng=(1.30, 2.70), meaning="全幅厚度变异系数（内控 ≤2.0%）；横向拉伸温度不对称会直接抬高该值",
         law="TD 均匀性 ← 拉伸区横向温度分布"),
    dict(code="L3-GA-EDGE-N01", name="北边缘厚度偏差", unit="%", stage="在线测厚",
         equip="L3-GA", loop="QI-4103", role="quality", target=0.0,
         rng=(-0.5, 2.0), meaning="距北侧边缘 50mm 处厚度相对均值偏差（内控 ±1.0%）；北侧拉伸温度偏低会使该处偏厚",
         law="拉伸应力-温度：温度低→应力高→拉伸不足→偏厚"),
    dict(code="L3-GA-EDGE-S01", name="南边缘厚度偏差", unit="%", stage="在线测厚",
         equip="L3-GA", loop="QI-4104", role="quality", target=-0.3,
         rng=(-0.5, -0.1), meaning="距南侧边缘 50mm 处厚度相对均值偏差（内控 ±1.0%）", law="同上"),
    dict(code="L3-QM-YIELD01", name="综合优品率", unit="%", stage="在线测厚",
         equip="L3-GA", loop="QI-4105", role="quality", target=98.6,
         rng=(95.8, 98.8), meaning="在线综合优品率（含厚度/外观判定），对工艺偏差存在数小时滞后响应",
         law="滞后响应：膜卷后处理+离线判定引入时滞"),
    # --- 环境 / 循环水 ----------------------------------------------------
    dict(code="L3-ENV-TE01", name="车间环境温度", unit="℃", stage="环境",
         equip="L3-ENV", loop="TI-9001", role="env", target=26.5,
         rng=(23.5, 29.0), meaning="车间环境温度（昼夜周期 + 季节趋势），是风温类指标的天然混淆变量",
         law="环境散热/散热损失 ∝ (T_process - T_env)"),
    dict(code="L3-ENV-RH01", name="车间环境湿度", unit="%", stage="环境",
         equip="L3-ENV", loop="HI-9002", role="env", target=55.0,
         rng=(42.0, 68.0), meaning="车间相对湿度", law="——"),
    dict(code="L3-CW-SUP-TE01", name="循环水供水温度", unit="℃", stage="环境",
         equip="L3-CW", loop="TI-9101", role="env", target=22.0,
         rng=(21.3, 22.4), meaning="全厂循环水供水温度（随季节变化）", law="——"),
    # --- 元数据 -----------------------------------------------------------
    dict(code="L3-MES-BATCH01", name="生产批次号", unit="-", stage="生产管理",
         equip="L3-MES", loop="-", role="meta", target=None, rng=None,
         meaning="12 小时一个生产批次（同一规格连续生产的分卷批次），用于批次级统计与完整性校验",
         law="——", dtype="str"),
    dict(code="L3-MES-SPEC01", name="产品规格代号", unit="-", stage="生产管理",
         equip="L3-MES", loop="-", role="meta", target=None, rng=None,
         meaning="产品规格代号（本例 GP12 = 12μm 包装级光膜）", law="——", dtype="str"),
    dict(code="L3-MES-RECYCLE01", name="回料掺入比例", unit="%", stage="生产管理",
         equip="L3-MES", loop="-", role="meta", target=8.0, rng=(8.0, 12.0),
         meaning="回用切片掺入比例（配方参数，本窗口内 8%→12%），会影响雾度/晶点，是重要的混杂因素",
         law="回料中杂质/降解物 → 晶点、雾度上升", dtype="num"),
    dict(code="L3-LINE-MODE01", name="产线运行状态码", unit="-", stage="生产管理",
         equip="L3-MES", loop="-", role="meta", target=None, rng=None,
         meaning="1=正常运行 2=升降速/换网 3=停机（本窗口无停机）；用于工况识别与稳态筛选",
         law="——", dtype="int"),
]

LAB_SIGNALS = [
    dict(code="L3-LAB-HAZE01", name="雾度", unit="%", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=1.55, rng=(1.40, 2.10),
         meaning="薄膜雾度（内控 ≤2.0%），对回料比例与结晶状态敏感", law="结晶/杂质散射 → 雾度"),
    dict(code="L3-LAB-GEL01", name="晶点数", unit="个/㎡", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=3.2, rng=(2.0, 7.0),
         meaning="单位面积晶点数量（内控 ≤10 个/㎡），与原料洁净度/回料比例强相关", law="杂质/凝胶点计数"),
    dict(code="L3-LAB-SHR-TD01", name="热收缩率(TD)", unit="%", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=1.80, rng=(1.60, 2.45),
         meaning="横向热收缩率（内控 ≤2.0%，150℃×30min），定型区温度不足会使其上升", law="收缩 ∝ (T-Tg) 热历史"),
    dict(code="L3-LAB-SHR-MD01", name="热收缩率(MD)", unit="%", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=3.10, rng=(3.00, 3.25),
         meaning="纵向热收缩率（内控 ≤3.5%）", law="同上"),
    dict(code="L3-LAB-STR-TD01", name="拉伸强度(TD)", unit="MPa", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=215.0, rng=(208.0, 220.0),
         meaning="横向拉伸强度，取向度下降时会降低", law="强度 ← 取向度 ← 拉伸温度"),
    dict(code="L3-LAB-STR-MD01", name="拉伸强度(MD)", unit="MPa", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=225.0, rng=(219.0, 231.0), meaning="纵向拉伸强度", law="同上"),
    dict(code="L3-LAB-TH-AVG01", name="实验室平均厚度", unit="μm", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=12.00, rng=(11.95, 12.05),
         meaning="离线测厚复核（与在线测厚交叉验证）", law="——"),
    dict(code="L3-LAB-WATER01", name="切片含水率", unit="ppm", stage="实验室检验", equip="L3-LAB", loop="-",
         role="quality", target=32.0, rng=(24.0, 42.0),
         meaning="干燥后切片含水率（内控 ≤50 ppm），干燥系统健康度的化验证据", law="含水率 ← 露点"),
]

EQUIPMENT_NODES = [
    dict(code="L3-DRY", name="干燥系统", type="unit", function="切片预结晶与干燥除湿，控制切片含水率"),
    dict(code="L3-EX", name="主挤出机", type="unit", function="PET 切片熔融、计量泵送熔体"),
    dict(code="L3-FL", name="熔体过滤器", type="unit", function="过滤熔体杂质（滤网随运行堵塞，需定期换网）"),
    dict(code="L3-DIE", name="模头", type="unit", function="熔体分配到设定宽度与厚度"),
    dict(code="L3-CR", name="铸片辊（急冷辊）", type="unit", function="熔膜骤冷成铸片，控制预结晶度"),
    dict(code="L3-MDO", name="纵拉机(MDO)", type="unit", function="铸片预热后在 Tg 以上纵向拉伸并急冷定型"),
    dict(code="L3-TDO", name="横拉机(TDO)", type="unit", function="纵拉片预热、横向拉伸（分区分侧热风）、热定型"),
    dict(code="L3-PU", name="牵引机组", type="unit", function="张力控制与薄膜输送"),
    dict(code="L3-WD", name="收卷机", type="unit", function="成品膜卷收卷"),
    dict(code="L3-GA", name="在线测厚仪", type="instrument", function="全幅扫描测厚：平均厚度、横向不匀率、边缘偏差、在线优品率"),
    dict(code="L3-LAB", name="实验室/化验室", type="instrument", function="雾度、晶点、热收缩率、拉伸强度、含水率抽检"),
    dict(code="L3-ENV", name="车间环境", type="environment", function="环境温湿度（混淆因素来源）"),
    dict(code="L3-CW", name="循环水系统", type="utility", function="急冷辊/工艺冷却水供应"),
    dict(code="L3-MES", name="生产管理系统(MES)", type="system", function="批次、规格、配方（回料比例）与运行状态记录"),
]

STAGES = [
    dict(id="dry", name="原料干燥", sequence=0, key_physics="干燥平衡 + 结晶动力学"),
    dict(id="extrude", name="熔融挤出", sequence=1, key_physics="Arrhenius 粘度-温度；计量泵体积守恒"),
    dict(id="cast", name="铸片急冷", sequence=2, key_physics="骤冷结晶 Xc∝1/冷却速率；换热 Q=K·A·ΔT"),
    dict(id="mdo", name="纵向拉伸(MDO)", sequence=3, key_physics="Tg 附近拉伸；取向与拉伸比"),
    dict(id="tdo", name="横向拉伸与定型(TDO)", sequence=4, key_physics="Avrami 结晶；横向温度分布决定 TD 均匀性；热收缩 ∝ 热历史"),
    dict(id="pull", name="牵引收卷", sequence=5, key_physics="胡克弹性；张力-应变"),
    dict(id="inspect", name="在线/离线检验", sequence=6, key_physics="测量系统与工艺真值分离"),
]

RELATIONSHIPS = [
    dict(from_="L3-DRY-DP-TE01", to="L3-LAB-WATER01", type="causal", strength="strong",
         mechanism="露点劣化 → 干燥能力不足 → 切片含水率上升 → 熔体水解降解（IV 下降）",
         time_lag="2-6 h", equation="含水率 ∝ 露点", form="monotonic"),
    dict(from_="L3-FL-DP01", to="L3-EX-PT01", type="causal", strength="moderate",
         mechanism="滤网堵塞 → 管路阻力上升 → 模头前熔体压力上升/波动放大",
         time_lag="< 10 min", equation="ΔP ∝ μ·Q·R_filter(t)", form="linear"),
    dict(from_="L3-TDO-N-ST-Z4-TE01", to="L3-GA-EDGE-N01", type="causal", strength="strong",
         mechanism="北侧拉伸区风温下降 → 该侧拉伸应力上升 → 横向拉伸不足 → 北边缘厚度偏厚",
         time_lag="< 30 min", equation="σ=E·ε；h ∝ 1/(拉伸比)", form="inverse"),
    dict(from_="L3-TDO-N-ST-Z4-TE01", to="L3-GA-TH-CV01", type="causal", strength="strong",
         mechanism="横向拉伸温度南北不对称 → 横向厚度分布不对称 → 不匀率 CV 上升",
         time_lag="< 30 min", equation="CV ∝ 横向温度梯度", form="linear"),
    dict(from_="L3-TDO-N-Z4-HOUT01", to="L3-TDO-N-ST-Z4-TE01", type="control", strength="strong",
         mechanism="加热输出闭环调节风温；输出持续上升直至饱和说明加热/送风效能衰减",
         time_lag="< 10 min", equation="闭环：输出 = Kp·e + Ki∫e（限幅 80%）", form="threshold"),
    dict(from_="L3-TDO-N-AN-Z6-TE01", to="L3-LAB-SHR-TD01", type="causal", strength="strong",
         mechanism="定型区风温不足 → 取向解取向/热历史变化 → 横向热收缩率上升",
         time_lag="1-3 h", equation="收缩率 ∝ (T-Tg) 热历史", form="monotonic"),
    dict(from_="L3-TDO-N-ST-Z4-TE01", to="L3-LAB-STR-TD01", type="causal", strength="moderate",
         mechanism="拉伸温度偏低 → 取向度下降 → TD 拉伸强度略降", time_lag="2-4 h",
         equation="强度 ← 取向因子 f ← 拉伸温度", form="monotonic"),
    dict(from_="L3-GA-TH-CV01", to="L3-QM-YIELD01", type="causal", strength="strong",
         mechanism="横向不匀率与边缘偏差超差 → 分切/判定不合格 → 优品率下降（存在膜卷后处理与判定滞后）",
         time_lag="4-8 h", equation="优品率 = 1 - 不合格比例（含判定滞后）", form="delayed_response"),
    dict(from_="L3-MES-RECYCLE01", to="L3-LAB-HAZE01", type="causal", strength="moderate",
         mechanism="回料掺入比例上升 → 杂质/降解物增加 → 雾度与晶点上升",
         time_lag="1-2 h", equation="雾度 ∝ 杂质浓度", form="linear"),
    dict(from_="L3-MES-RECYCLE01", to="L3-LAB-GEL01", type="causal", strength="moderate",
         mechanism="回料凝胶点带入 → 晶点数上升", time_lag="1-2 h", equation="晶点 ∝ 回料比例", form="linear"),
    dict(from_="L3-ENV-TE01", to="L3-TDO-N-ST-Z4-TE01", type="correlative", strength="weak",
         mechanism="环境温度下降会增加设备散热、降低热风效率（但南北两侧应同向变化——“仅北侧单侧下偏”可用于排除该假设）",
         time_lag="0-2 h", equation="热损失 ∝ (T_process - T_env)", form="monotonic",
         role_hint="confounder"),
    dict(from_="L3-CW-SUP-TE01", to="L3-CR-TE01", type="causal", strength="moderate",
         mechanism="循环水来水温度变化 → 急冷辊表面温度随之变化（辊温闭环可部分补偿）",
         time_lag="< 30 min", equation="Q=K·A·ΔT_lm", form="linear"),
    dict(from_="L3-EX-MGT-TE01", to="L3-DIE-TE01", type="physical", strength="strong",
         mechanism="同一熔体管路热状态连续性（温度变化同向）", time_lag="< 10 min",
         equation="热平衡/热传导", form="monotonic"),
    dict(from_="L3-MDO-V02", to="L3-PU-TN01", type="control", strength="moderate",
         mechanism="线速/拉伸比变化 → 张力闭环跟随调整", time_lag="< 10 min",
         equation="张力闭环", form="monotonic"),
]

CONFOUNDERS = [
    dict(variable="L3-ENV-TE01", why="环境温度随时间下降，与北侧风温下偏同向（需用南侧不变的“单侧不对称”判别）",
         controlled=False),
    dict(variable="L3-MES-RECYCLE01", why="回料比例在故障起点前一天上调，同时抬高雾度/晶点（时间上近似共线）",
         controlled=True),
    dict(variable="L3-FL-DP01", why="滤网堵塞随运行时间推进，放大熔体压力波动（与时间共线）", controlled=True),
    dict(variable="L3-CW-SUP-TE01", why="季节降温影响循环水温与辊温（与时间共线）", controlled=True),
]


# --------------------------------------------------------------------------
# 数据生成
# --------------------------------------------------------------------------
def build_main_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = N
    d = DAY
    h = HOURS
    noise = lambda s: rng.normal(0, s, n)

    # --- 故障与事件进度 ---
    fault = ramp(h, H_FAULT, FAULT_RATE_C_PER_DAY, FAULT_MAX_C)      # 0 → 1.95 ℃
    fault_lag = ramp(h - 6.0, H_FAULT, FAULT_RATE_C_PER_DAY, FAULT_MAX_C)  # 优品率滞后 6h
    recycle_on = (h >= H_RECYCLE).astype(float)
    slowdown = np.zeros(n, dtype=bool)
    for start, dur in SLOWDOWN_WINDOWS:
        slowdown |= in_window(h, start, dur)
    speed_factor = np.where(slowdown, 0.82, 1.0)
    dip = np.zeros(n)
    for start, dur in SLOWDOWN_WINDOWS:
        dip += yield_dip(h, start, dur, depth=0.35)

    # 过滤器压差：分段锯齿，换网复位
    fl_dp = np.zeros(n)
    seg_start_h, seg_start_v = 0.0, 0.62
    for change_h in FILTER_CHANGES + [h[-1] + 1]:
        m = (h >= seg_start_h) & (h < change_h)
        span_d = (change_h - seg_start_h) / 24.0
        slope = (2.30 - seg_start_v) / max(span_d, 0.1)
        fl_dp[m] = seg_start_v + (h[m] - seg_start_h) / 24.0 * slope
        seg_start_h, seg_start_v = change_h, 0.60
    fl_dp = fl_dp + noise(0.02)

    env_temp = 26.8 + 1.2 * np.sin(2 * np.pi * (h / 24.0 - 0.35)) - 0.19 * d + noise(0.25)
    cw_sup = 22.0 - 0.06 * d + noise(0.08)

    vals: dict[str, np.ndarray | list] = {}
    vals["L3-DRY-DP-TE01"] = -60.0 + noise(0.25)
    vals["L3-DRY-RG-TE01"] = 175.0 + noise(0.55)
    vals["L3-EX-MGT-TE01"] = 282.0 + noise(0.35)
    vals["L3-EX-PT01"] = 110.0 + 0.15 * (fl_dp - 0.8) + noise(1.2)
    vals["L3-EX-CUR01"] = 212.0 + 0.6 * (fl_dp - 0.8) + noise(1.1)
    vals["L3-EX-SPD01"] = 63.0 + noise(0.12) - 0.4 * (1 - speed_factor)
    vals["L3-FL-DP01"] = fl_dp
    vals["L3-DIE-TE01"] = 285.0 + noise(0.28)
    vals["L3-DIE-HOUT01"] = 44.0 + 0.25 * (env_temp - 26.8) + noise(0.9)

    vals["L3-CR-TE01"] = 26.5 + 0.55 * (cw_sup - 22.0) + noise(0.16)
    vals["L3-CR-CW-IN-TE01"] = cw_sup
    vals["L3-CR-CW-OUT-TE01"] = cw_sup + 2.2 + 0.15 * (fl_dp - 0.8) * 0 + noise(0.12)
    vals["L3-CR-CW-FQ01"] = 60.0 + noise(0.9)
    vals["L3-CR-SPD01"] = 16.40 * speed_factor + noise(0.03)
    vals["L3-CR-ES-V01"] = 7.0 + noise(0.08)

    vals["L3-MDO-PH1-TE01"] = 78.0 + noise(0.24)
    vals["L3-MDO-PH2-TE01"] = 79.0 + noise(0.25)
    vals["L3-MDO-PH3-TE01"] = 80.0 + noise(0.26)
    vals["L3-MDO-ST1-TE01"] = 86.5 + noise(0.30)
    vals["L3-MDO-ST2-TE01"] = 87.0 + noise(0.30)
    vals["L3-MDO-AN-TE01"] = 35.0 + noise(0.55)
    vals["L3-MDO-V01"] = 16.40 * speed_factor + noise(0.03)
    vals["L3-MDO-V02"] = 52.90 * speed_factor + noise(0.07)
    vals["L3-MDO-TQ01"] = 62.0 + 0.3 * fault + noise(0.55)

    # --- TDO：故障注入点 ---
    vals["L3-TDO-N-PH-TE01"] = 155.0 + noise(0.28)
    vals["L3-TDO-S-PH-TE01"] = 155.0 + noise(0.28)
    vals["L3-TDO-N-ST-Z4-TE01"] = 240.0 - fault + noise(0.16)
    vals["L3-TDO-S-ST-Z4-TE01"] = 240.0 + noise(0.16)
    vals["L3-TDO-N-AN-Z6-TE01"] = 191.0 - 0.35 * fault + noise(0.15)
    vals["L3-TDO-S-AN-Z6-TE01"] = 191.0 + noise(0.15)
    vals["L3-TDO-N-ST-Z4-SP01"] = np.full(n, 240.0)
    vals["L3-TDO-N-Z4-HOUT01"] = np.minimum(44.5 + 27.0 * fault, 80.0) + noise(0.7)
    vals["L3-TDO-S-Z4-HOUT01"] = 45.0 + 0.2 * (env_temp - 26.8) + noise(0.8)
    vals["L3-TDO-N-FAN-HZ01"] = 85.0 + noise(0.08)
    vals["L3-TDO-S-FAN-HZ01"] = 85.0 + noise(0.08)
    vals["L3-TDO-RAIL-W01"] = 6330.0 - 0.15 * fault + noise(1.6)
    vals["L3-TDO-CHAIN-I01"] = 40.0 + 0.45 * fault + noise(0.7)

    vals["L3-PU-TN01"] = 2270.0 * (1 - 0.10 * (1 - speed_factor)) + 0.6 * fault + noise(11.0)
    vals["L3-PU-V01"] = 52.95 * speed_factor + noise(0.07)
    vals["L3-WD-TN01"] = 1180.0 * (1 - 0.05 * (1 - speed_factor)) + noise(7.0)
    vals["L3-WD-V01"] = 52.90 * speed_factor + noise(0.07)

    # --- 在线质量：均值正常，分布劣化（核心诊断线索） ---
    vals["L3-GA-TH-AVG01"] = 12.00 + 0.02 * (env_temp - 26.8) * 0.2 + noise(0.014)
    vals["L3-GA-TH-CV01"] = 1.40 + 0.55 * fault + noise(0.022) + 0.02 * recycle_on
    vals["L3-GA-EDGE-N01"] = 0.35 + 0.77 * fault + noise(0.05)
    vals["L3-GA-EDGE-S01"] = -0.30 + 0.02 * (env_temp - 26.8) + noise(0.05)
    vals["L3-QM-YIELD01"] = (98.66 - 1.15 * fault_lag - 0.05 * recycle_on + dip + noise(0.05))

    # --- 环境 / 循环水 ---
    vals["L3-ENV-TE01"] = env_temp
    vals["L3-ENV-RH01"] = 55.0 + 6.0 * np.sin(2 * np.pi * (h / 24.0 + 0.15)) + noise(2.6)
    vals["L3-CW-SUP-TE01"] = cw_sup

    # --- 元数据 ---
    batch_idx = (h // 12).astype(int)                       # 12h 一批
    vals["L3-MES-BATCH01"] = [
        f"{(T0 + pd.Timedelta(hours=12 * b)).strftime('%Y%m%d')}-A{b % 2 + 1:02d}" for b in batch_idx
    ]
    vals["L3-MES-SPEC01"] = ["GP12"] * n
    vals["L3-MES-RECYCLE01"] = np.where(h >= H_RECYCLE, 12.0, 8.0)
    mode = np.ones(n, dtype=int)
    mode[slowdown] = 2
    vals["L3-LINE-MODE01"] = mode

    df = pd.DataFrame({TIME_COL: ROWS.strftime("%Y-%m-%d %H:%M:%S")})
    for sig in SIGNALS:
        code = sig["code"]
        v = vals[code]
        if sig.get("dtype") == "str":
            df[code] = v
        elif sig.get("dtype") == "int":
            df[code] = np.asarray(v).astype(int)
        else:
            df[code] = np.round(np.asarray(v, dtype=float), 3)
    return df


def build_lab_table(main: pd.DataFrame) -> pd.DataFrame:
    """化验表：2h 抽检，时间点落在主表 10min 网格上（保证自动合并时不新增行）。"""
    rng = np.random.default_rng(SEED + 1)
    lab_times = pd.date_range(T0, ROWS[-1], freq=f"{LAB_STEP_H}h")
    h = (lab_times - T0).total_seconds().to_numpy() / 3600.0
    n = len(lab_times)
    noise = lambda s: rng.normal(0, s, n)

    fault = ramp(h, H_FAULT, FAULT_RATE_C_PER_DAY, FAULT_MAX_C)
    recycle_on = (h >= H_RECYCLE).astype(float)

    df = pd.DataFrame({TIME_COL: lab_times.strftime("%Y-%m-%d %H:%M:%S")})
    df["L3-LAB-HAZE01"] = np.round(1.55 + 0.25 * recycle_on + 0.010 * fault + noise(0.030), 3)
    df["L3-LAB-GEL01"] = np.round(3.2 + 1.6 * recycle_on + 0.25 * fault + noise(0.35), 2)
    df["L3-LAB-SHR-TD01"] = np.round(1.80 + 0.28 * fault + noise(0.035), 3)
    df["L3-LAB-SHR-MD01"] = np.round(3.10 + 0.02 * fault + noise(0.045), 3)
    df["L3-LAB-STR-TD01"] = np.round(215.0 - 2.2 * fault + noise(1.8), 2)
    df["L3-LAB-STR-MD01"] = np.round(225.0 - 0.5 * fault + noise(1.9), 2)
    df["L3-LAB-TH-AVG01"] = np.round(12.00 + noise(0.018), 3)
    df["L3-LAB-WATER01"] = np.round(32.0 + 0.15 * (h - h.mean()) / 24.0 + noise(3.0), 1)
    return df


def build_thickness_profile() -> pd.DataFrame:
    """膜厚横向剖面：10min 一帧 × 63 个横向测点（距北侧边缘 50~6250 mm，间距 100 mm）。

    与主表共用同一故障进度：TDO 北侧 Z4 加热能力衰减 → 北侧风温下偏 → 北侧取向不足 →
    该侧（尤其近边缘）厚度偏厚。剖面还叠加了：
      * 常态横向弓形（中心略薄、两侧略厚，量级 ±0.03 μm）；
      * 每测点固定增益误差与逐帧测量噪声（模拟扫描仪重复性）；
      * 全幅共模漂移（很小，保持平均厚度在 12.00±0.05 μm 内，与在线均值一致）。
    时间戳比 DCS 采样点晚 5 分钟（扫描完成时刻），独立成表，不参与主表列合并。
    """
    rng = np.random.default_rng(SEED + 2)
    n = len(ROWS)
    times = ROWS + pd.Timedelta(minutes=PROFILE_OFFSET_MIN)
    x = PROFILE_POS_MM.astype(float)
    width = float(PROFILE_POS_MM[-1] - PROFILE_POS_MM[0])

    fault = ramp(HOURS, H_FAULT, FAULT_RATE_C_PER_DAY, FAULT_MAX_C)   # 0 → 1.95 ℃
    north_weight = np.exp(-((x - x[0]) / 1200.0) ** 2)                # 北侧影响，向中心指数衰减

    base_shape = 0.030 * np.cos(2.0 * np.pi * (x - x[0]) / width)     # 中心 -0.03，两侧 +0.03
    # 横向驻波（TDO 风道形成的 3 个完整波），幅度较小并随加热不均略增；
    # 63 个 100mm 测点只能部分表达扫描仪的高频横向不匀，剖面 CV 会低于在线 GA-CV（口径差异）
    wave_amp = 0.080 + 0.040 * (fault / FAULT_MAX_C if FAULT_MAX_C else 0.0)
    cross_wave = wave_amp[:, None] * np.sin(6.0 * np.pi * (x - x[0]) / width)[None, :]
    position_bias = rng.normal(0.0, 0.004, x.size)                    # 测点固定增益误差
    common_drift = 0.006 * np.sin(2.0 * np.pi * HOURS / 24.0) + rng.normal(0.0, 0.004, n)
    scan_noise = rng.normal(0.0, 0.006, (n, x.size))

    # 故障场：末端北边缘 +0.22 μm（≈+1.85%），中心约 +0.02 μm，南侧几乎不变
    fault_field = np.outer(PROFILE_EDGE_UM_PER_C * fault, north_weight)
    matrix = (12.0 + base_shape[None, :] + cross_wave + position_bias[None, :]
              + common_drift[:, None] + scan_noise + fault_field)

    df = pd.DataFrame({TIME_COL: times.strftime("%Y-%m-%d %H:%M:%S"), "单位": "μm"})
    for j in range(x.size):
        df[f"pos_{j + 1:02d}"] = np.round(matrix[:, j], 3)
    return df


def write_profile_reference_md(path: Path) -> None:
    """膜厚剖面数据说明（给分析系统与产线共读；刻意不用 Markdown 表格）。"""
    lines = [
        "# 膜厚横向剖面数据说明（L3_GA_TH_PROFILE_10min.csv）",
        "",
        "> 本文件说明独立膜厚扫描剖面文件的格式与口径。它是数据文件（不是分析结论），",
        "> 由在线测厚仪全幅扫描生成；与主表（DCS 10 分钟）分开导出。",
        "",
        "## 文件形态",
        "",
        "- 一行 = 一次全幅扫描（扫描完成时刻），行时刻为 `YYYY-MM-DD HH:MM:SS`，间隔 10 分钟；",
        "- 扫描完成时刻比主表 DCS 采样点晚 5 分钟（例如主表 00:00 对应剖面 00:05），属正常时序；",
        "- 列 `pos_01` ～ `pos_63` = 横向 63 个测点，**pos_01 位于北侧边缘，pos_63 位于南侧边缘**；",
        "- 列 `单位` = `μm`（全表统一，供分析系统识别量纲）；",
        "- 测点间距 100 mm，pos_01 距北侧切边 50 mm，pos_63 距南侧切边 50 mm；",
        "- 单元格数值 = 该测点膜厚，单位 μm，保留 3 位小数；无缺失值；",
        "- 一次扫描的 63 个值构成该时刻的**横向厚度向量**，列顺序即从北到南的位置顺序。",
        "",
        "## 与主表的关系",
        "",
        "- 主表 `L3-GA-TH-AVG01` 是全幅平均厚度，`L3-GA-TH-CV01` 是横向不匀率，`L3-GA-EDGE-N01` / `-S01` 是距边 50 mm 的边缘偏差；",
        "- 本文件是这些在线统计量背后的原始横向剖面，可用于定位“偏差发生在哪个横向位置”；",
        "- 时间轴与主表对齐（同一本地时钟，+08:00），但采样时刻错开 5 分钟，按时间就近对齐即可；",
        "- 平均厚度始终应在 12.0 μm ± 0.20 μm 内；剖面局部异常不一定改变平均值。",
        "",
        "## 使用注意",
        "",
        "- 不要按“63 个独立工艺变量”理解这 63 列：它们同一物理量的空间采样，需按剖面/向量处理；",
        "- 横向位置与设备侧别的对应：pos_01 侧 = 北侧（N），pos_63 侧 = 南侧（S）；",
        "- 扫描仪已按月校准；异常应优先从工艺侧（横向温度/风量分布）找原因，而不是先怀疑测厚仪。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# 映射表与本体
# --------------------------------------------------------------------------
def build_tag_mapping() -> dict:
    params = []
    for s in SIGNALS + LAB_SIGNALS:
        row = {
            "code": s["code"],
            "name": s["name"],
            "unit": s["unit"],
            "stage": s["stage"],
            "equipment": s["equip"],
            "loop": s.get("loop", "-"),
            "role": s["role"],
            "target": s.get("target"),
            "normal_range": list(s["rng"]) if s.get("rng") else None,
            "sampling": f"{STEP_MIN}min" if s in SIGNALS else f"{LAB_STEP_H}h",
            "physical_meaning": s["meaning"],
            "governing_law": s.get("law", "——"),
        }
        if s["role"] == "control":
            row["setpoint"] = s.get("const", s.get("target"))
        params.append(row)
    return {
        "_meta": {
            "scene": "BOPET 双向拉伸聚酯薄膜产线（L3 线）",
            "product": "12 μm 包装级光膜（规格代号 GP12）",
            "data_window": f"{ROWS[0]:%Y-%m-%d %H:%M} ~ {ROWS[-1]:%Y-%m-%d %H:%M}（{DAYS} 天）",
            "source_systems": ["DCS/PLC 历史站", "在线测厚仪", "LIMS 化验系统", "MES"],
            "version": "1.0",
            "updated": "2026-10-15",
            "note": "code 必须与导出数据表的表头逐字一致（含大小写与连字符）；产线新增测点请在本表追加一行",
            "unmapped_code_policy": "未在映射表中的代号，分析系统只能按统计特征推断含义，建议补齐后再分析",
        },
        "equipment_nodes": EQUIPMENT_NODES,
        "stages": STAGES,
        "parameters": params,
        "batch_and_metadata": [
            {"code": "时间", "name": "采样时间", "format": "YYYY-MM-DD HH:MM:SS", "note": "本地时区（+08:00）"},
            {"code": "L3-MES-BATCH01", "name": "生产批次号", "format": "YYYYMMDD-A01", "note": "12 小时一批"},
            {"code": "L3-LINE-MODE01", "name": "运行状态码", "values": {"1": "正常运行", "2": "升降速/换网", "3": "停机"}},
        ],
    }


def build_ontology() -> dict:
    def sig(s, role):
        o = {
            "name": s["name"],
            "column": s["code"],
            "unit": s["unit"],
            "role": role,
            "physical_meaning": s["meaning"],
            "physical_meaning_confidence": "KNOWN",
            "governing_law": s.get("law", "——"),
            "equipment_ref": s["equip"],
            "stage_ref": s["stage"],
            "knowledge_source": "user_provided",
        }
        if s.get("target") is not None:
            o["target"] = float(s["target"])
        if s.get("rng"):
            o["normal_range"] = [float(s["rng"][0]), float(s["rng"][1])]
        return o

    inspection, process, control, env, meta = [], [], [], [], []
    for s in SIGNALS + LAB_SIGNALS:
        if s["role"] == "quality":
            inspection.append(sig(s, "target"))
        elif s["role"] == "process":
            process.append(sig(s, "predictor"))
        elif s["role"] == "control":
            c = sig(s, "control")
            c["control_type"] = "setpoint" if "SP01" in s["code"] else "output"
            if s["code"] == "L3-TDO-N-ST-Z4-SP01":
                c["setpoint"] = 240.0
            control.append(c)
        elif s["role"] == "env":
            env.append(sig(s, "confounder"))
        else:
            m = {"name": s["name"], "column": s["code"], "role": "batch_id",
                 "description": s["meaning"]}
            meta.append(m)

    rels = []
    for r in RELATIONSHIPS:
        rel = {
            "from": r["from_"], "to": r["to"], "type": r["type"],
            "strength": r["strength"], "mechanism": r["mechanism"],
            "time_lag": r["time_lag"], "governing_equation": r["equation"],
            "predicted_functional_form": r["form"], "inferred": False,
        }
        rels.append(rel)

    return {
        "scene": {
            "name": "BOPET-L3 双向拉伸聚酯薄膜产线（12μm 光膜）",
            "process_type": "pet_film_biaxial_orientation_line",
            "production_goal": "在厚度公差 ±0.20μm、横向不匀率 ≤2.0%、热收缩率TD ≤2.0% 约束下最大化优品率",
            "equipment": [{"id": e["code"], "name": e["name"], "type": e["type"],
                           "function": e["function"]} for e in EQUIPMENT_NODES],
            "stages": [{"id": s["id"], "name": s["name"], "sequence": s["sequence"],
                        "key_physics": s["key_physics"]} for s in STAGES],
            "objectives": ["定位优品率下降与横向厚度劣化的主导原因", "区分工艺真值劣化与测量/原料等混杂因素"],
        },
        "signals": {
            "inspection_signals": inspection,
            "process_parameters": process,
            "control_variables": control,
            "events": [{"name": "产线运行状态码", "column": "L3-LINE-MODE01",
                        "description": "1=正常运行 2=升降速/换网 3=停机",
                        "event_values": [1, 2, 3],
                        "event_meanings": {"1": "正常运行（稳态）", "2": "升降速或换网（非稳态）", "3": "停机"}}],
            "metadata_columns": [
                {"name": "采样时间", "column": "时间", "role": "timestamp"},
                {"name": "生产批次号", "column": "L3-MES-BATCH01", "role": "batch_id",
                 "description": "12 小时一个生产批次"},
                {"name": "产品规格代号", "column": "L3-MES-SPEC01", "role": "product_code"},
            ],
        },
        "parameter_groups": {
            "原料与配方": ["L3-DRY-DP-TE01", "L3-DRY-RG-TE01", "L3-MES-RECYCLE01", "L3-MES-BATCH01"],
            "挤出熔体": ["L3-EX-MGT-TE01", "L3-EX-PT01", "L3-EX-CUR01", "L3-EX-SPD01", "L3-FL-DP01", "L3-DIE-TE01"],
            "铸片冷却": ["L3-CR-TE01", "L3-CR-CW-IN-TE01", "L3-CR-CW-OUT-TE01", "L3-CR-CW-FQ01", "L3-CR-SPD01", "L3-CW-SUP-TE01"],
            "纵拉热辊": ["L3-MDO-PH1-TE01", "L3-MDO-PH2-TE01", "L3-MDO-PH3-TE01", "L3-MDO-ST1-TE01",
                     "L3-MDO-ST2-TE01", "L3-MDO-AN-TE01", "L3-MDO-V01", "L3-MDO-V02", "L3-MDO-TQ01"],
            "横拉热风北侧": ["L3-TDO-N-PH-TE01", "L3-TDO-N-ST-Z4-TE01", "L3-TDO-N-AN-Z6-TE01",
                        "L3-TDO-N-Z4-HOUT01", "L3-TDO-N-FAN-HZ01", "L3-TDO-N-ST-Z4-SP01"],
            "横拉热风南侧": ["L3-TDO-S-PH-TE01", "L3-TDO-S-ST-Z4-TE01", "L3-TDO-S-AN-Z6-TE01",
                        "L3-TDO-S-Z4-HOUT01", "L3-TDO-S-FAN-HZ01"],
            "牵引收卷": ["L3-PU-TN01", "L3-PU-V01", "L3-WD-TN01", "L3-WD-V01", "L3-TDO-RAIL-W01", "L3-TDO-CHAIN-I01"],
            "环境与公用工程": ["L3-ENV-TE01", "L3-ENV-RH01", "L3-CW-SUP-TE01"],
        },
        "relationships": rels,
        "confounders": [{"variable": c["variable"], "why": c["why"], "controlled": c["controlled"]}
                        for c in CONFOUNDERS],
        "metadata": {
            "units": {s["code"]: s["unit"] for s in SIGNALS + LAB_SIGNALS},
            "sampling_rate": f"{STEP_MIN} 分钟（主表）；{LAB_STEP_H} 小时（化验表）",
            "batch_id": None,
            "timezone": "+08:00",
            "start_time": ROWS[0].strftime("%Y-%m-%dT%H:%M:%S"),
            "end_time": ROWS[-1].strftime("%Y-%m-%dT%H:%M:%S"),
            "product_grades": [{"name": "GP12", "key_parameter_differences": {}}],
        },
    }


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_code_reference_md(path: Path) -> None:
    """02_data/参数代号对照说明.md —— 给分析系统与产线共读的代号速查（由 SIGNALS 派生，保证与数据一致）。

    注意：本文件刻意不使用 Markdown 表格（表格会被数据预处理流程当作"数据表"处理），
    全部使用列表形式，确保它被当作"文字背景"进入分析。
    """
    equip_name = {e["code"]: e["name"] for e in EQUIPMENT_NODES}
    lines = [
        "# 参数代号对照说明（填写示例）",
        "",
        "> 本文件说明数据表表头代号的命名规则与含义。**代号是本厂/产线内部命名，外部无法直接理解，",
        "> 因此这份对照说明是必附文件**；产线请按同样格式维护自己的代号表（可另存为 json/csv 供系统读取，",
        "> 见 `03_映射文档/tag_mapping.json` 的字段结构）。",
        "",
        "## 命名规则",
        "",
        "`L3-<设备节点>-<侧别/部位>-<功能>-<序号>`，例如：",
        "",
        "- `L3-TDO-N-ST-Z4-TE01` = L3线 / 横拉机TDO / 北侧N / 拉伸区ST / 第4分区Z4 / 温度TE / 编号01",
        "- `L3-FL-DP01` = L3线 / 熔体过滤器FL / 压差DP / 编号01",
        "- 常用功能码：TE=温度、PT/DP=压力/压差、FQ=流量、SPD=速度、TN=张力、CUR/I=电流、",
        "  HOUT=加热输出(%)、FAN-HZ=风机频率、W=宽度、SP=设定值(SetPoint)、OUT=闭环输出",
        "",
        "## 代号明细（按设备节点分组）",
        "",
    ]
    for e in EQUIPMENT_NODES:
        codes = [s for s in SIGNALS if s["equip"] == e["code"]] + \
                [s for s in LAB_SIGNALS if s["equip"] == e["code"]]
        if not codes:
            continue
        lines.append(f"### {e['code']} {e['name']}（{e['function']}）")
        lines.append("")
        for s in codes:
            rng = f"，正常范围 {s['rng'][0]}~{s['rng'][1]}{s['unit']}" if s.get("rng") else ""
            extra = ""
            if s.get("const") is not None:
                extra = f"（设定值恒定 {s['const']}）"
            elif s["role"] == "control":
                extra = f"（控制量，目标 {s['target']}{s['unit']}）"
            lines.append(f"- `{s['code']}` = {s['name']}（{s['unit']}，回路 {s.get('loop','-')}"
                         f"{rng}）{extra}：{s['meaning']}")
        lines.append("")
    lines += [
        "## 批次号与状态码",
        "",
        "- `L3-MES-BATCH01` 生产批次号：格式 `YYYYMMDD-A01`，12 小时一个批次（同一规格连续生产的分卷批次）",
        "- `L3-MES-SPEC01` 产品规格代号：`GP12` = 12 μm 包装级光膜",
        "- `L3-MES-RECYCLE01` 回料掺入比例：配方参数（%），本窗口 2026-09-27 08:00 由 8 调整为 12",
        "- `L3-LINE-MODE01` 运行状态码：1=正常运行，2=升降速/换网，3=停机（本窗口无停机）",
        "",
        "## 特殊说明",
        "",
        "- 带 `SP01` 后缀的列是**设定值（SV）**，本窗口内恒定；带 `HOUT01/OUT` 的是**闭环输出百分比**，",
        "  用于判断执行器是否需要“更费力”才能维持设定——输出持续上升是设备效能下降的重要线索",
        "- 主表与化验表时间轴对齐（化验表时间点均落在主表 10 分钟网格上），系统可自动按时间合并",
        "- 全部数值不带单位（单位见本说明或映射表），缺失值请留空单元格",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_mapping_csv(mapping: dict, path: Path) -> None:
    rows = []
    for p in mapping["parameters"]:
        rows.append({
            "代号(code)": p["code"], "名称": p["name"], "单位": p["unit"],
            "工段": p["stage"], "设备节点": p["equipment"], "DCS回路号": p["loop"],
            "角色": {"process": "工艺参数", "quality": "质量指标", "control": "控制量",
                   "env": "环境量", "meta": "元数据"}.get(p["role"], p["role"]),
            "目标值": p["target"], "正常范围下限": (p["normal_range"] or [None, None])[0],
            "正常范围上限": (p["normal_range"] or [None, None])[1],
            "采样": p["sampling"], "物理含义": p["physical_meaning"], "物理规律": p["governing_law"],
        })
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    for d in (DATA_DIR, MAP_DIR, GEN_DIR):
        d.mkdir(parents=True, exist_ok=True)

    main_df = build_main_table()
    lab_df = build_lab_table(main_df)
    profile_df = build_thickness_profile()
    main_path = DATA_DIR / "L3_line_main_10min.csv"
    lab_path = DATA_DIR / "L3_lab_quality_2h.csv"
    profile_path = DATA_DIR / "L3_GA_TH_PROFILE_10min.csv"
    main_df.to_csv(main_path, index=False, encoding="utf-8-sig")
    lab_df.to_csv(lab_path, index=False, encoding="utf-8-sig")
    profile_df.to_csv(profile_path, index=False, encoding="utf-8-sig")
    write_code_reference_md(DATA_DIR / "参数代号对照说明.md")
    write_profile_reference_md(DATA_DIR / "膜厚剖面数据说明.md")

    mapping = build_tag_mapping()
    map_json = MAP_DIR / "tag_mapping.json"
    map_csv = MAP_DIR / "tag_mapping.csv"
    map_json.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_mapping_csv(mapping, map_csv)

    ontology = build_ontology()
    onto_path = MAP_DIR / "L3_bopet_ontology.json"
    onto_path.write_text(json.dumps(ontology, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "generator": "generate_template_data.py",
        "seed": SEED,
        "generated_for": "BOPET-L3 数据模板样例（12μm 光膜）",
        "time_window": [ROWS[0].strftime("%Y-%m-%d %H:%M:%S"), ROWS[-1].strftime("%Y-%m-%d %H:%M:%S")],
        "cadence": {"main": f"{STEP_MIN}min", "lab": f"{LAB_STEP_H}h",
                    "profile": f"{PROFILE_STEP_MIN}min (offset +{PROFILE_OFFSET_MIN}min)"},
        "files": {
            str(main_path.relative_to(PKG_ROOT)): {"rows": int(len(main_df)), "cols": int(main_df.shape[1]),
                                                   "sha256": sha256_of(main_path)},
            str(lab_path.relative_to(PKG_ROOT)): {"rows": int(len(lab_df)), "cols": int(lab_df.shape[1]),
                                                  "sha256": sha256_of(lab_path)},
            str(profile_path.relative_to(PKG_ROOT)): {"rows": int(len(profile_df)), "cols": int(profile_df.shape[1]),
                                                      "sha256": sha256_of(profile_path),
                                                      "positions_mm": [int(PROFILE_POS_MM[0]), int(PROFILE_POS_MM[-1])],
                                                      "position_step_mm": 100},
            str(map_json.relative_to(PKG_ROOT)): {"sha256": sha256_of(map_json)},
            str(map_csv.relative_to(PKG_ROOT)): {"sha256": sha256_of(map_csv)},
            str(onto_path.relative_to(PKG_ROOT)): {"sha256": sha256_of(onto_path)},
        },
        "injected_events": [
            {"hour_offset": H_RECYCLE, "time": "2026-09-27 08:00", "type": "配方变更",
             "detail": "原料批次切换 + 回料掺入比例 8%→12%（雾度/晶点小幅阶跃；干扰项）"},
            {"hour_offset": H_FAULT, "time": "2026-09-28 00:00", "type": "注入故障（主）",
             "detail": "TDO 北侧拉伸区4区热风加热能力缓慢衰减：设定值恒定 240℃，实际风温以 0.15℃/天 下偏"
                       "（累计 1.95℃），加热输出由 44.5% 上升至 80% 上限（执行器饱和）；"
                       "下游：北边缘厚度偏差 +0.35%→+1.85%、横向不匀率 1.40%→2.50%、"
                       "定型区北侧同步下偏 0.68℃ → 热收缩率TD 1.80%→2.35%、优品率滞后 6h 下降至约 96.4%"},
            {"hour_offset": FILTER_CHANGES[0], "time": "2026-09-29 02:00", "type": "计划换网",
             "detail": "过滤器压差复位、产线降速 2 小时（非稳态段，供工况过滤演示）"},
            {"hour_offset": FILTER_CHANGES[1], "time": "2026-10-06 02:00", "type": "计划换网",
             "detail": "同上"},
            {"hour_offset": H_FAULT, "time": "2026-09-28 00:05", "type": "注入故障（剖面同源）",
             "detail": "独立膜厚横向剖面（63 测点）同步体现同一故障：北侧近边缘渐进增厚，"
                       "末端约 +0.22 μm；中心与南侧基本不变 → 剖面左边缘偏差上升、右边缘平稳，"
                       "平均厚度仍保持在 12.00 μm 附近"},
        ],
        "notes": [
            "全部数值为确定性合成（固定 seed），不代表任何真实产线；" + MANUFACTURER_NOTE,
            "未注入停机事件；最末累计偏差未进一步恶化（便于检验系统是否给出“趋势外推”而非“已失效”结论）",
        ],
    }
    (GEN_DIR / "generation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "main": {"path": str(main_path), "rows": len(main_df), "cols": main_df.shape[1]},
        "lab": {"path": str(lab_path), "rows": len(lab_df), "cols": lab_df.shape[1]},
        "profile": {"path": str(profile_path), "rows": len(profile_df), "cols": profile_df.shape[1]},
        "mapping_params": len(mapping["parameters"]),
        "ontology": {"relationships": len(ontology["relationships"]),
                     "targets": len(ontology["signals"]["inspection_signals"])},
        "manifest": str(GEN_DIR / "generation_manifest.json"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
