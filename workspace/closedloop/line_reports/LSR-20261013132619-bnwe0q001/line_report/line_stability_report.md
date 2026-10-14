# 产线运行稳定性报告 · LSR-1791897987-ezb7tx

- **报告编号**：LSR-1791897987-ezb7tx（line-stability-report/1.0）
- **时段**：2026-08-10 00:00:00 ~ 2026-08-30 23:50:00
- **综合评分**：**67.0（C 级 · 波动）**
- **结论**：该产线在本时段总体运行波动（67.0 分，C 级）：评估 7 个参数，检出 2916 个 SPC 违规剧集、4 项显著漂移；最需关注：换网器入口压力(bar)、过滤器压差(bar)、薄膜厚度MD波动(μm)。

## 核心发现（结论与证据）

### F001 [high] 换网器入口压力(bar) 检出 SPC 违规（置信度 90）

共 172 个判异剧集命中（每百点 5.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值165.41±3σ_within（σ=0.835）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 172 | 0 | lstcore |
| rate_per_100 | 5.69 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.835 | — | lstcore |

### F002 [high] 换网器出口压力(bar) 检出 SPC 违规（置信度 90）

共 499 个判异剧集命中（每百点 16.5 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值117.99±3σ_within（σ=0.6606）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 499 | 0 | lstcore |
| rate_per_100 | 16.5 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.6606 | — | lstcore |

### F003 [high] 过滤器压差(bar) 检出 SPC 违规（置信度 90）

共 116 个判异剧集命中（每百点 3.8 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值47.385±3σ_within（σ=0.4816）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 116 | 0 | lstcore |
| rate_per_100 | 3.84 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.4816 | — | lstcore |

### F004 [high] 计量泵电流(A) 检出 SPC 违规（置信度 90）

共 496 个判异剧集命中（每百点 16.4 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值50.26±3σ_within（σ=0.2805）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 496 | 0 | lstcore |
| rate_per_100 | 16.4 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.2805 | — | lstcore |

### F005 [high] 熔体温度(℃) 检出 SPC 违规（置信度 90）

共 553 个判异剧集命中（每百点 18.3 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值284.98±3σ_within（σ=0.2559）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 553 | 0 | lstcore |
| rate_per_100 | 18.29 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.2559 | — | lstcore |

### F006 [high] 薄膜厚度MD波动(μm) 检出 SPC 违规（置信度 90）

共 598 个判异剧集命中（每百点 19.8 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值0.0541±3σ_within（σ=0.0022）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 598 | 0 | lstcore |
| rate_per_100 | 19.78 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.0022 | — | lstcore |

### F007 [high] 挤出机螺杆转速(rpm) 检出 SPC 违规（置信度 90）

共 482 个判异剧集命中（每百点 15.9 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值68±3σ_within（σ=0.0551）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 482 | 0 | lstcore |
| rate_per_100 | 15.94 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.0551 | — | lstcore |

### F008 [high] 过滤器压差(bar) 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 1.730%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0173 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F009 [warn] 换网器入口压力(bar) 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.476%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0048 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F010 [warn] 计量泵电流(A) 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.105%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0011 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F011 [warn] 薄膜厚度MD波动(μm) 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.434%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0043 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F012 [info] 强相关对：换网器入口压力(bar) ↔ 过滤器压差(bar) [MECHANISM_UNKNOWN]（置信度 45）｜[MECHANISM_UNKNOWN]

滞后补偿后最强 |Spearman|=0.9969（零滞后同步）；零滞后 Pearson=0.9968。本体未提供物理机制支持——仅是统计共变，不可作因果线索使用。置信度 45（统计证据充分度 × 机制支持度）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| best_abs_r | 0.9969 | >=0.7 | lstcore（derived） |
| best_lag_rows | 0 | — | lstcore |
| mechanism_level | unknown | — | ontology |

### F013 [info] 强相关对：过滤器压差(bar) ↔ 计量泵电流(A) [MECHANISM_UNKNOWN]（置信度 45）｜[MECHANISM_UNKNOWN]

滞后补偿后最强 |Spearman|=0.9439（零滞后同步）；零滞后 Pearson=0.9402。本体未提供物理机制支持——仅是统计共变，不可作因果线索使用。置信度 45（统计证据充分度 × 机制支持度）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| best_abs_r | 0.9439 | >=0.7 | lstcore（derived） |
| best_lag_rows | 0 | — | lstcore |
| mechanism_level | unknown | — | ontology |

### F014 [info] 强相关对：换网器入口压力(bar) ↔ 计量泵电流(A) [MECHANISM_UNKNOWN]（置信度 45）｜[MECHANISM_UNKNOWN]

滞后补偿后最强 |Spearman|=0.9405（零滞后同步）；零滞后 Pearson=0.9368。本体未提供物理机制支持——仅是统计共变，不可作因果线索使用。置信度 45（统计证据充分度 × 机制支持度）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| best_abs_r | 0.9405 | >=0.7 | lstcore（derived） |
| best_lag_rows | 0 | — | lstcore |
| mechanism_level | unknown | — | ontology |

## 参数稳定性总览

| 参数 | 角色 | 样本 | 中位数 | CV | SPC剧集 | 漂移/天 | Cpk | 评分 |
|---|---|---|---|---|---|---|---|---|
| 换网器入口压力(bar) | 参数 | 3024 | 165.41 | 0.07853 | 172 | 0.004764（显著） | — | 58 |
| 换网器出口压力(bar) | 参数 | 3024 | 117.99 | 0.008779 | 499 | 0.000094 | — | 87 |
| 过滤器压差(bar) | 参数 | 3024 | 47.385 | 0.269655 | 116 | 0.017295（显著） | — | 40 |
| 计量泵电流(A) | 参数 | 3024 | 50.26 | 0.024982 | 496 | 0.001051（显著） | — | 75 |
| 熔体温度(℃) | 参数 | 3024 | 284.98 | 0.001425 | 553 | 0.000014 | — | 85 |
| 薄膜厚度MD波动(μm) | 参数 | 3024 | 0.0541 | 0.179379 | 598 | 0.004345（显著） | — | 37 |
| 挤出机螺杆转速(rpm) | 参数 | 3024 | 68 | 0.001252 | 482 | 0 | — | 87 |

## 数据与口径

- 数据：`D:\codes\industrial-deep-diagnostic\data\bopet_cases\bc2_filter_dp_cycles\dcs_melt_system_10min.csv`（sha256:3d97b98ea91c08d095d8eeba863197433166e0448cfc982beaac4c1967961b29）
- 行数（原始/入评）：3024 / 3024
- 时间列/采样间隔：时间 / 600 s；缺失率 0.00%

### 假设与局限（darwin 条款）

- raw (this skill never cleans or imputes; every number is recomputable from the raw table)
- 假设：lag-compensated Spearman window 0–10 rows (lead/lag beyond this window is invisible)
- 假设：whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading
- 假设：Cpk treats within-sigma as MR̄/1.128 moving-range estimate

---

> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，不构成参数下发指令。LSR-1791897987-ezb7tx · script v1.0.0 · 2026-10-13T13:26:27Z