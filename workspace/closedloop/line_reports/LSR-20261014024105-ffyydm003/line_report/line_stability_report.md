# 产线运行稳定性报告 · DEMO-REACTOR-NOONTO

- **报告编号**：LSR-1791945668-iudlp8（line-stability-report/1.0）
- **时段**：2026-10-07 08:00:00 ~ 2026-10-10 07:55:00
- **综合评分**：**84.5（B 级 · 亚稳定）**
- **结论**：该产线在本时段总体运行亚稳定（84.5 分，B 级）：评估 4 个参数，检出 343 个 SPC 违规剧集、2 项显著漂移；最需关注：yield_pct。

## 核心发现（结论与证据）

### F001 [high] yield_pct 检出 SPC 违规（置信度 90）

共 170 个判异剧集命中（每百点 19.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值95.8863±3σ_within（σ=0.1182）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 170 | 0 | lstcore |
| rate_per_100 | 19.68 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.1182 | — | lstcore |

### F002 [high] reactor_temp 检出 SPC 违规（置信度 90）

共 18 个判异剧集命中（每百点 2.1 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值80.004±3σ_within（σ=0.3368）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 18 | 0 | lstcore |
| rate_per_100 | 2.08 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.3368 | — | lstcore |

### F003 [high] feed_rate 检出 SPC 违规（置信度 90）

共 144 个判异剧集命中（每百点 16.7 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值104.575±3σ_within（σ=0.1819）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 144 | 0 | lstcore |
| rate_per_100 | 16.67 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.1819 | — | lstcore |

### F004 [warn] cooling_flow 检出 SPC 违规（置信度 90）

共 11 个判异剧集命中（每百点 1.3 个，规则：NELSON_R1/NELSON_R2/NELSON_R3/NELSON_R5/NELSON_R6），控制限为中心值50.007±3σ_within（σ=0.218）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| violation_episodes | 11 | 0 | lstcore |
| rate_per_100 | 1.27 | <2 for warn; >=2 for high | lstcore |
| sigma_within_mr | 0.218 | — | lstcore |

### F005 [warn] yield_pct 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.502%/天，方向对应斜率 -0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.005 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | -0 | — | lstcore |

### F006 [warn] feed_rate 存在显著漂移（置信度 80）

Theil–Sen 斜率显著（Mann–Kendall p=0.0，且相对漂移≥0.1%/天才计入），相对漂移约 0.823%/天，方向对应斜率 0/秒。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| mk_p | 0 | <0.01 且 >=0.1%/天 | lstcore |
| per_day_relative | 0.0082 | <0.001 ok; >=0.01 high | lstcore |
| slope_per_second | 0 | — | lstcore |

### F007 [info] feed_rate 是 yield_pct 波动的主要解释项（置信度 50）｜[MECHANISM_UNKNOWN]

滞后补偿后 |r|² 归一，feed_rate 解释了 yield_pct 约 100% 的方差（|r|=0.8973，领先 4 行）。本体未见因果边——占比仅为统计分解。置信度 50。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| share | 1 | >=0.4 | lstcore（derived） |
| abs_r | 0.8973 | — | lstcore（derived） |
| mechanism_level | unknown | — | ontology |

### F008 [info] 强相关对：yield_pct ↔ feed_rate [MECHANISM_UNKNOWN]（置信度 45）｜[MECHANISM_UNKNOWN]

滞后补偿后最强 |Spearman|=0.8973（feed_rate 领先 4 行）；零滞后 Pearson=-0.9389。本体未提供物理机制支持——仅是统计共变，不可作因果线索使用。置信度 45（统计证据充分度 × 机制支持度）。

| 证据项 | 数值 | 阈值/口径 | 来源 |
|---|---|---|---|
| best_abs_r | 0.8973 | >=0.7 | lstcore（derived） |
| best_lag_rows | 4 | — | lstcore |
| mechanism_level | unknown | — | ontology |

## 参数稳定性总览

| 参数 | 角色 | 样本 | 中位数 | CV | SPC剧集 | 漂移/天 | Cpk | 评分 |
|---|---|---|---|---|---|---|---|---|
| yield_pct | 检测 | 864 | 95.8863 | 0.004594 | 170 | 0.005023（显著） | — | 69 |
| reactor_temp | 参数 | 864 | 80.004 | 0.00445 | 18 | 0.000032 | — | 98 |
| feed_rate | 参数 | 864 | 104.575 | 0.007454 | 144 | 0.008231（显著） | — | 72 |
| cooling_flow | 参数 | 864 | 50.007 | 0.004449 | 11 | 0.000537 | — | 99 |

## 数据与口径

- 数据：`D:\codes\industrial-deep-diagnostic\workspace\closedloop\line_reports\LSR-20261014024105-ffyydm003\00_input\preprocessed_data.csv`（sha256:5b713e22e18d411ce08e37582a3fc98f3b27f794f2e1998e8214f2dd98c7d566）
- 行数（原始/入评）：864 / 864
- 时间列/采样间隔：t / 300 s；缺失率 0.00%
- 输入模式：自适应目录 `D:\codes\industrial-deep-diagnostic\data\lsr_demo_noonto`；评分主表 `line_demo.csv`（864 行，时间列 `t`）。
- 逐文件来源角色/处置及 SHA-256：`D:\codes\industrial-deep-diagnostic\workspace\closedloop\line_reports\LSR-20261014024105-ffyydm003\00_input\input_manifest.json`

| 来源文件 | 角色 | 处置 | 原因 |
|---|---|---|---|
| line_demo.csv | primary_time_series | selected | highest-scoring eligible time-series table |

### 假设与局限（darwin 条款）

- raw (this skill never cleans or imputes; every number is recomputable from the raw table)
- 假设：lag-compensated Spearman window 0–10 rows (lead/lag beyond this window is invisible)
- 假设：whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading
- 假设：Cpk treats within-sigma as MR̄/1.128 moving-range estimate

---

> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，不构成参数下发指令。LSR-1791945668-iudlp8 · script v1.0.0 · 2026-10-14T02:41:08Z