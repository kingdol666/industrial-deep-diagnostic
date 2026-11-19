# 产线运行稳定性报告 · 包装产线烘箱段 8 小时 DCS 导出运行稳定性评估

- **报告编号**：LSR-1795030063-idulkh（line-stability-report/1.0）
- **时段**：2026-11-18T06:00:00+08:00 ~ 2026-11-18T14:00:00+08:00
- **综合评分**：**83.5（B 级 · 亚稳定）**
- **结论**：该产线在本时段总体运行亚稳定（83.5 分，B 级）：评估 5 个参数，检出 574 个 SPC 违规剧集、1 项显著漂移。

## 场景理解（本体优先）

- 场景：packaging_line_oven（包装产线烘箱段 8 小时 DCS 导出运行稳定性评估）；生产目标：评估包装线烘箱段本班次 8 小时运行稳定性并识别主要波动来源
- 本体来源：ontology（run_dir）

| 参数 | 本体名 | 单位 | 角色 | 规格 | 控制方程 | assigned_by |
|---|---|---|---|---|---|---|
| scrap_rate_pct | scrap_rate_pct | % | 检测指标 | — | — | user |
| film_tension_n | film_tension_n | N | 加工参数 | — | — | auto |
| oven_temp_c | oven_temp_c | ℃ | 加工参数 | — | — | auto |
| line_speed_mpm | line_speed_mpm | m/min | 加工参数 | — | — | auto |
| cooling_water_flow_lpm | cooling_water_flow_lpm | L/min | 加工参数 | — | — | auto |

**运行状态分段**（sentinel C3，方法 fast；变点 0 个）

| 段 | 行范围 | 主导状态 |
|---|---|---|
| 段 1 | 0–5760（5761 行） | steady |

## 核心发现（结论与证据）

### F001 [high] oven_temp_c 检出 SPC 违规（置信度 90）

共 234 个判异剧集命中（每百点 4.1 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值120.119 ℃±3σ_within（σ=0.3443）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 234 | 0 | lstcore |
| rate_per_100 | 4.06 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.3443 | — | lstcore |

### F002 [high] oven_temp_c 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 3.414%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0341 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F003 [warn] scrap_rate_pct 检出 SPC 违规（置信度 90）

共 82 个判异剧集命中（每百点 1.4 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值1.201 %±3σ_within（σ=0.081）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 82 | 0 | lstcore |
| rate_per_100 | 1.42 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.081 | — | lstcore |

### F004 [warn] film_tension_n 检出 SPC 违规（置信度 90）

共 84 个判异剧集命中（每百点 1.5 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值250 N±3σ_within（σ=1.5063）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 84 | 0 | lstcore |
| rate_per_100 | 1.46 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 1.5063 | — | lstcore |

### F005 [warn] line_speed_mpm 检出 SPC 违规（置信度 90）

共 82 个判异剧集命中（每百点 1.4 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值119.98 m/min±3σ_within（σ=0.7921）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 82 | 0 | lstcore |
| rate_per_100 | 1.42 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.7921 | — | lstcore |

### F006 [warn] cooling_water_flow_lpm 检出 SPC 违规（置信度 90）

共 92 个判异剧集命中（每百点 1.6 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值44.84 L/min±3σ_within（σ=0.8685）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 92 | 0 | lstcore |
| rate_per_100 | 1.6 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.8685 | — | lstcore |

## 改善建议与验证计划（集成）

**状态**：无建议（处方模式） · 目标模式 explicit · 证据水位线 none

| KPI | 方向 | 目标值 | 容差 |
| --- | --- | --- | --- |
| scrap_rate_pct | min | — | — |

本次没有建议进入建议区（数据撑不起可执行行动）。

### 处方区（不成建议）
- [experiment] KPI scrap_rate_pct 没有通过门禁的可操作杠杆；先补动作日志/更宽数据窗，或用 doe-analyzer 设计试验分离因果

> 本节为确定性脚本生成的咨询建议（advisory），不构成参数下发；执行须经产线审批 / optimizer-campaign 验证。


## 参数稳定性总览

| 参数 | 角色 | 样本 | 中位数 | CV | SPC剧集 | 漂移/天 | Cpk | 评分 |
|---|---|---|---|---|---|---|---|---|
| scrap_rate_pct | 检测 | 5761 | 1.201 | 0.067419 | 82 | 0.005146 | — | 77 |
| film_tension_n | 参数 | 5761 | 250 | 0.0061 | 84 | 0.002683 | — | 99 |
| oven_temp_c | 参数 | 5761 | 120.119 | 0.007116 | 234 | 0.034139（显著） | — | 72 |
| line_speed_mpm | 参数 | 5761 | 119.98 | 0.006608 | 82 | 0.002684 | — | 99 |
| cooling_water_flow_lpm | 参数 | 5761 | 44.84 | 0.054263 | 92 | 0.002309 | — | 77 |

## 数据与口径

- 数据：`D:/codes/myskills/idd-doe-impl/workspace/skill-pipeline-demo-20261119/01-stability/00_input/dcs_export.csv`（sha256:4626a86c2da76415b1ab6d465bb9b6e24c675c2a2f25595710a1903af487da6b）
- 行数（原始/入评）：5761 / 5761
- 时间列/采样间隔：timestamp / 5 s；缺失率 0.00%

### 假设与局限（数据真值条款）

- raw (this skill never cleans or imputes; every number is recomputable from the raw table)
- 假设：lag-compensated Spearman window 0–10 rows (lead/lag beyond this window is invisible)
- 假设：whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading
- 假设：Cpk treats within-sigma as MR̄/1.128 moving-range estimate

---

> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，不构成参数下发指令。LSR-1795030063-idulkh · script v1.0.0 · 2026-11-18T19:27:43Z