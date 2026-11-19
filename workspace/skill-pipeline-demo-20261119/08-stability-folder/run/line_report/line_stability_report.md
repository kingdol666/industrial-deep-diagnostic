# 产线运行稳定性报告 · offline-data_diag

- **报告编号**：LSR-1795069191-2j43d9（line-stability-report/1.0）
- **时段**：2026-11-18 06:00:00 ~ 2026-11-18 13:58:00
- **综合评分**：**86.2（A 级 · 稳定）**
- **结论**：该产线在本时段总体运行稳定（86.2 分，A 级）：评估 5 个参数，检出 21 个 SPC 违规剧集、1 项显著漂移；最需关注：scrap_rate_pct。

## 场景理解（本体优先）

- 场景：offline-data_diag（挤出/注塑式热工艺产线（PROTO3-B3 文档驱动接入线）时序数据稳定性评估）；生产目标：评估 2026-11-01 11:03 ~ 12:03 窗口内该产线 7 个标量节点的运行稳定性，给出评分与分级、证据链与中文落地报告
- 本体来源：ontology（run_dir）

| 参数 | 本体名 | 单位 | 角色 | 规格 | 控制方程 | assigned_by |
|---|---|---|---|---|---|---|
| film_tension_n | film_tension_n | 单位未声明（unit undeclared） | 加工参数 | — | — | auto |
| oven_temp_c | oven_temp_c | 单位未声明（unit undeclared） | 加工参数 | — | — | auto |
| line_speed_mpm | line_speed_mpm | 单位未声明（unit undeclared） | 加工参数 | — | — | auto |
| cooling_water_flow_lpm | cooling_water_flow_lpm | 单位未声明（unit undeclared） | 加工参数 | — | — | auto |
| scrap_rate_pct | scrap_rate_pct | 单位未声明（unit undeclared） | 加工参数 | — | — | auto |

**运行状态分段**（sentinel C3，方法 fast；变点 0 个）

| 段 | 行范围 | 主导状态 |
|---|---|---|
| 段 1 | 0–239（240 行） | steady |

## 核心发现（结论与证据）

### F001 [high] oven_temp_c 检出 SPC 违规（置信度 90）

共 10 个判异剧集命中（每百点 4.2 个，规则：NELSON_R1/NELSON_R2/NELSON_R5/NELSON_R6），控制限为中心值120.06±3σ_within（σ=0.4872）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 10 | 0 | lstcore |
| rate_per_100 | 4.17 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.4872 | — | lstcore |

### F002 [high] oven_temp_c 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 2.093%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0209 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F003 [warn] film_tension_n 检出 SPC 违规（置信度 90）

共 4 个判异剧集命中（每百点 1.7 个，规则：NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值249.79±3σ_within（σ=1.495）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 4 | 0 | lstcore |
| rate_per_100 | 1.67 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 1.495 | — | lstcore |

### F004 [warn] line_speed_mpm 检出 SPC 违规（置信度 90）

共 4 个判异剧集命中（每百点 1.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R6），控制限为中心值120±3σ_within（σ=0.8379）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 4 | 0 | lstcore |
| rate_per_100 | 1.67 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.8379 | — | lstcore |

### F005 [warn] cooling_water_flow_lpm 检出 SPC 违规（置信度 90）

共 3 个判异剧集命中（每百点 1.2 个，规则：NELSON_R1/NELSON_R2/NELSON_R6），控制限为中心值44.99±3σ_within（σ=0.7058）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 3 | 0 | lstcore |
| rate_per_100 | 1.25 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.7058 | — | lstcore |

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
| film_tension_n | 参数 | 240 | 249.79 | 0.006325 | 4 | 0.003348 | — | 99 |
| oven_temp_c | 参数 | 240 | 120.06 | 0.004515 | 10 | 0.020927（显著） | — | 72 |
| line_speed_mpm | 参数 | 240 | 120 | 0.006736 | 4 | 0 | — | 99 |
| cooling_water_flow_lpm | 参数 | 240 | 44.99 | 0.015632 | 3 | 0.011054 | — | 93 |
| scrap_rate_pct | 参数 | 240 | 1.485 | 0.131014 | 0 | 0 | — | 68 |

## 数据与口径

- 数据：`D:/codes/myskills/idd-doe-impl/workspace/skill-pipeline-demo-20261119/08-stability-folder/run\00_input\primary_table.csv`（sha256:866591abcec93794bea7d28668cb7bcfdb87ee7a4515fd9686db23369c9b7f56）
- 行数（原始/入评）：240 / 240
- 时间列/采样间隔：timestamp / 120 s；缺失率 0.00%

### 假设与局限（数据真值条款）

- raw (this skill never cleans or imputes; every number is recomputable from the raw table)
- 假设：lag-compensated Spearman window 0–10 rows (lead/lag beyond this window is invisible)
- 假设：whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading
- 假设：Cpk treats within-sigma as MR̄/1.128 moving-range estimate

---

> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，不构成参数下发指令。LSR-1795069191-2j43d9 · script v1.0.0 · 2026-11-19T06:19:51Z