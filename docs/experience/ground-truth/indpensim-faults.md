# IndPenSim 根因真值表

> 来源：Mendeley `pdnjz7zz5x` v2（100_Batches_IndPenSim_Statistics.csv 的 Fault ref 列）+ 实测 V3 宽表 `Fault reference` 字段（故障激活时段）+ Goldrick et al. 2019 原文（故障类型定义）。

## 批次总体结构

| 批次 | 状态 | 控制策略 |
|---|---|---|
| 1–30 | 正常（0） | Recipe 驱动（Control_ref=0） |
| 31–60 | 正常（0） | 操作员控制（Control_ref=1） |
| 61–90 | 正常（0） | Raman-APC（Control_ref=0，PAT 在环） |
| **91–100** | **故障（1）** | 同上混合 |

每批 ~895–1390 行（0.2h 采样，批长 200–258h）。_statistics 真值文件：`data/benchmark/indpensim/Mendeley_data/100_Batches_IndPenSim_Statistics.csv`。

## 故障批次真值与故障激活窗口（实测提取，窗口单位 = 批内小时 Time(h)）

| 批次 | 行数 | 时长(h) | 故障激活窗口 | 备注 |
|---|---|---|---|---|
| 91 | 1290 | 0.2–258 | **20–30.2 / 76–92.2 / 200–214.2** | 三段激活 |
| 92 | 1150 | 0.2–230 | 80–84.2 / 140–160.2 | |
| 93 | 1050 | 0.2–210 | 70–90.2 | |
| 94 | 1150 | 0.2–230 | 20–24.2 / 100–110.2 | 文献引用其 DO2 下降与曝气相关（Metcalfe 2025） |
| 95 | 1055 | 0.2–211 | 20–30.2 / 76–92.2 / 200–211 | 与 91 同构 |
| 96 | 1150 | 0.2–230 | 70–90.2 | |
| 97 | 1125 | 0.2–225 | 20–30.2 / 76–92.2 / 200–214.2 | 与 91 同构 |
| 98 | 1150 | 0.2–230 | 80–84.2 / 140–160.2 | 与 92 同构 |
| 99 | 1255 | 0.2–251 | 20–24.2 / 100–110.2 | |
| 100 | 1150 | 0.2–230 | 20–24.2 / 100–110.2 | |

> 故障类型：原论文把 91–100 描述为"故障导致工艺偏差"（曝气故障、pH 传感器漂移、DO2 下降等，Acosta-Pavas 2024 转述）。**每批的精确故障定义表以 Goldrick et al. 2019（Biotechnol. Bioeng.）原文 Table 为准**，写作 Exp-4 时需引原文核对到批。

## 诊断输入说明

- 诊断用 CSV（`data/benchmark/prepared/indpensim*/batch_XXX.csv`）：32 列 = `Time (h)` + 30 过程变量 + `Fault reference`。
  - **`Time (h)` 是批内相对小时**（0.2h 步长），非墙钟时间 —— 在 process_description 声明即可；
  - **`Fault reference` 列保留在 CSV 中仅作评测对照**，诊断请求的 user_context 应声明"该列为评测标注，不作为证据"（或评测版删除该列，两可；保留+声明的优点是 reviewer 阶段可交叉验证）；
  - 离线分析列（PAA_offline / NH3_offline / X_offline / P_offline / Viscosity）NaN 率高 —— 属预期，processor 会在 analysis_boundary 声明。
- 关键过程列（语义自解释，本体层无需外供词典）：
  `Aeration rate(Fg)` 曝气、`Agitator RPM` 搅拌、`Sugar feed rate(Fs)` 糖流加、`Acid/Base flow(Fa/Fb)` 酸碱流加、`Heating/cooling water(Fc)`、`Water for injection(Fw)`、`Air head pressure` 罐压、`Dissolved oxygen(DO2)` 溶氧、`Penicillin concentration(P)` 青霉素浓度（质量目标）、`Vessel Volume/Weight`、`pH`、`Temperature(T:K)`、`Generated heat(Q)`、`CO2outgas / O2` 尾气、`OUR / CER` 呼吸代谢、`Oil flow(Foil)`、`Ammonia shots`。

## 故障信号链预期（供结果解读）

| 故障机制（论文口径） | 信号链 | 可检测性 |
|---|---|---|
| 曝气故障（aeration） | Fg↓ → DO2↓ → OUR/O2 尾气↓、CO2↑ → P 产率降 | 高（多变量强联动，CCF 强项） |
| pH 传感器漂移 | pH 读数漂 → Base flow(Fb) 补偿性异常 → 无真实化学偏差 | 中（传感器漂移 vs 真实偏差的区分 = 竞争假设的好案例） |
| 搅拌/功率类 | Agitator RPM/功率 → DO2 分布 → 代谢 | 中高 |
| 底物流加异常 | Fs → S 基质 → X 生物量/OUR | 高 |

## Exp-4 评测设计要点

- 正例：批次 91–100 全跑（10 runs）；负例：90 个正常批分层抽 10（覆盖三种控制策略）测误报率；
- 计分除 CDR/Top-k 外，可利用故障窗口评 **根因时间定位**（诊断给出的异常起点 vs 上表窗口起点）；
- 注意批次 91/95/97、92/98、94/99/100 互为同构故障 —— 报告 per-fault 命中率时按"故障机制"聚合而非按批次。
