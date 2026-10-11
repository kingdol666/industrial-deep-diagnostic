# 产线运行稳定性报告 · LSR-HUB

- **报告编号**：LSR-1791608177-4mdbj2（line-stability-report/1.0）
- **时段**：2026-10-07 08:00:00 ~ 2026-10-10 07:55:00
- **综合评分**：**71.5（B 级 · 亚稳定）**
- **结论**：该产线在本时段总体运行亚稳定（71.5 分，B 级）：评估 4 个参数，检出 343 个 SPC 违规剧集、2 项显著漂移；最需关注：yield_pct。

## 工况理解（本体优先）

- 场景：演示反应产线（continuous_reactor）；生产目标：收率稳定 ≥ 96%，温度受控 80±1°C
- 本体来源：ontology（explicit）

| 参数 | 本体名 | 单位 | 角色 | 规格 | 控制方程 | assigned_by |
|---|---|---|---|---|---|---|
| reactor_temp | 反应器温度 | °C | 加工参数 | [79, 81]（ontology） | 能量平衡：Q = m·Cp·ΔT | ontology |
| feed_rate | 进料流量 | m3/h | 加工参数 | — | 停留时间 τ = V/Q | ontology |
| cooling_flow | 冷却流量 | m3/h | 加工参数 | — | 移热 Q = m·Cp·(T_out-T_in) | ontology |
| yield_pct | 收率 | % | 检测指标 | [95.5, 97]（ontology） | Arrhenius 动力学 + 停留时间分布 | ontology |

**工况分段**（sentinel C3，方法 fast；变点 0 个）

| 段 | 行范围 | 主导状态 |
|---|---|---|
| 段 1 | 0–863（864 行） | steady |

## 核心发现（结论与证据）

### F001 [high] reactor_temp 检出 SPC 违规（置信度 90）

共 18 个判异剧集命中（每百点 2.1 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值80.004 °C±3σ_within（σ=0.3368）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 18 | 0 | lstcore |
| rate_per_100 | 2.08 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.3368 | — | lstcore |

### F002 [high] feed_rate 检出 SPC 违规（置信度 90）

共 144 个判异剧集命中（每百点 16.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值104.575 m3/h±3σ_within（σ=0.1819）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 144 | 0 | lstcore |
| rate_per_100 | 16.67 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.1819 | — | lstcore |

### F003 [high] yield_pct 检出 SPC 违规（置信度 90）

共 170 个判异剧集命中（每百点 19.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值95.8863 %±3σ_within（σ=0.1182）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 170 | 0 | lstcore |
| rate_per_100 | 19.68 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.1182 | — | lstcore |

### F004 [high] reactor_temp 工序能力不足（置信度 85）

Cpk=0.9879（阈值：≥1.33 合格，<1.0 不足），规格界限 LSL=79 / USL=81（来源：本体资产）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| cpk | 0.9879 | >=1.33 | lstcore |
| ppk | 0.9342 | — | lstcore |
| spec_source | ontology | — | lstcore |

### F005 [high] yield_pct 工序能力不足（置信度 85）

Cpk=0.7902（阈值：≥1.33 合格，<1.0 不足），规格界限 LSL=95.5 / USL=97（来源：本体资产）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| cpk | 0.7902 | >=1.33 | lstcore |
| ppk | 0.2121 | — | lstcore |
| spec_source | ontology | — | lstcore |

### F006 [warn] cooling_flow 检出 SPC 违规（置信度 90）

共 11 个判异剧集命中（每百点 1.3 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值50.007 m3/h±3σ_within（σ=0.218）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 11 | 0 | lstcore |
| rate_per_100 | 1.27 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.218 | — | lstcore |

### F007 [warn] feed_rate 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.823%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0082 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F008 [warn] yield_pct 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.502%/天，方向对应斜率 -0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.005 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | -0 | — | lstcore |

### F009 [info] 强相关对：feed_rate ↔ yield_pct（置信度 80）｜本体因果边支持

滞后补偿后最强 |Spearman|=0.8973（feed_rate 领先 4 行）；零滞后 Pearson=-0.9389。本体机制佐证：进料流量↑ → 停留时间τ缩短 → 转化率↓ → 收率↓（τ = V/Q）；控制方程：τ = V/Q。置信度 80（统计证据充分度 × 机制支持度）。
> 物理机制：进料流量↑ → 停留时间τ缩短 → 转化率↓ → 收率↓（τ = V/Q）（τ = V/Q）

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| best_abs_r | 0.8973 | >=0.7 | lstcore（derived） |
| best_lag_rows | 4 | — | lstcore |
| mechanism_level | known | — | ontology |

### F010 [info] feed_rate 是 yield_pct 波动的主要解释项（置信度 65）｜本体因果边支持

滞后补偿后 |r|² 归一，feed_rate 解释了 yield_pct 约 100% 的方差（|r|=0.8973，领先 4 行）。本体有因果边支持。置信度 65。
> 物理机制：进料流量↑ → 停留时间τ缩短 → 转化率↓ → 收率↓（τ = V/Q）

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| share | 1 | >=0.4 | lstcore（derived） |
| abs_r | 0.8973 | — | lstcore（derived） |
| mechanism_level | known | — | ontology |

## 参数稳定性总览

| 参数 | 角色 | 样本 | 中位数 | CV | SPC剧集 | 漂移/天 | Cpk | 评分 |
|---|---|---|---|---|---|---|---|---|
| reactor_temp | 参数 | 864 | 80.004 | 0.00445 | 18 | 0.000032 | 0.9879 | 72 |
| feed_rate | 参数 | 864 | 104.575 | 0.007454 | 144 | 0.008231（显著） | — | 72 |
| cooling_flow | 参数 | 864 | 50.007 | 0.004449 | 11 | 0.000537 | — | 99 |
| yield_pct | 检测 | 864 | 95.8863 | 0.004594 | 170 | 0.005023（显著） | 0.7902 | 43 |

## 数据与口径

- 数据：`D:\codes\industrial-deep-diagnostic\data\lsr_demo\line_demo.csv`（sha256:51e144266bf49fef8f646fb160ba5c99b2ae0acbacb8e1d7ed5d29d09bf6a6ea）
- 行数（原始/入评）：864 / 864
- 时间列/采样间隔：t / 300 s；缺失率 0.00%

### 假设与局限（darwin 条款）

- raw (this skill never cleans or imputes; every number is recomputable from the raw table)
- 假设：lag-compensated Spearman window 0–10 rows (lead/lag beyond this window is invisible)
- 假设：whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading
- 假设：Cpk treats within-sigma as MR̄/1.128 moving-range estimate
- 混杂因子：catalyst_age — 催化剂活性随时间衰减，同时影响温度响应与收率基线（**未控**）

---

> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，不构成参数下发指令。LSR-1791608177-4mdbj2 · script v1.0.0 · 2026-10-10T04:56:17Z