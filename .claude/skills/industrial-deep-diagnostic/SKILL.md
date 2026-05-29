---
name: industrial-deep-diagnostic
description: "Use when the user provides industrial, process, or manufacturing time-series data (CSV, XLSX, Parquet) and asks about anomalies, root causes, quality issues, equipment faults, or process diagnostics. Also triggers on: anomaly detection, root cause analysis, fault diagnosis, sensor data analysis, equipment health, SPC, statistical process control, 工业诊断, 过程分析, 异常检测, 根因分析, 质量分析, 故障诊断, 传感器数据. Do NOT trigger for: simple data visualization, general statistics homework, financial time-series, or non-industrial data."
commands:
  - industrial-deep-diagnostic
  - industrial-deep-diagnostic analyze
  - industrial-deep-diagnostic report
version: 8.0.0
---

# Industrial Deep Diagnostic v8.0

## Language Default

**默认输出语言为中文。** 所有报告、诊断结论均使用中文撰写（技术术语可保留英文）。

## v8.0 核心变化

**Agent驱动分析，而非脚本驱动。** v7.0的分析流程硬编码在 `deep_analyze.py`（BOPET专用），无法适配CNC、换热器、化工等其他工业场景。v8.0改为：

- **数据分析由Agent完成** — Agent先理解数据结构和物理场景，再决定分析策略
- **物理知识从用户和领域推理获取** — 不依赖预写的BOPET定律库
- **参考脚本提供方法学，不提供硬编码流程** — BOPET脚本变为"参考实现"，Agent根据实际数据选择/组合/改造分析方法

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline |
| `/industrial-deep-diagnostic analyze` | Only run analysis + visualize |
| `/industrial-deep-diagnostic report` | Generate report from existing analysis |

## Execution Flow (v8.0 — Agent-Driven)

```
Step 0: 数据理解与场景识别
  ├── 加载数据，识别结构（行数、列名、类型）
  ├── 分类列：工艺参数 vs 质量指标 vs 分组变量 vs 时间戳
  ├── 识别数据粒度：高频时序 / 批次聚合 / 单件记录 / 事件日志
  ├── 识别分组维度：产品型号 / 材料批次 / 设备编号 / 班次
  └── 向用户确认理解是否正确（如有歧义）

Step 1: Agent驱动的数据分析
  ├── 不运行固定脚本。根据Step 0的数据特征，自行决定分析策略：
  │
  │ 数据粒度 = 高频时序 + 批次标签？
  │   → 批次窗口切片，提取时序动态特征（slope/volatility/autocorr）
  │   → 参考 scripts/deep_analyze.py 的方法学
  │
  │ 数据粒度 = 单件/批次记录（每行=一件/一批）？
  │   → 直接做参数-质量关联分析（Spearman/Pearson）
  │   → 按分组维度做分层相关（Simpson检测）
  │
  │ 数据粒度 = 事件/报警日志？
  │   → 时间序列异常检测、事件前后对比
  │
  ├── 核心分析步骤（无论哪种粒度都必须执行）：
  │   1. 全参数×全质量指标关联矩阵（Spearman + Pearson）
  │   2. 分组维度分层分析（检测Simpson's Paradox）
  │   3. 去趋势检查（如数据有时间排序）
  │   4. 异常值敏感性检查（Spearman vs Pearson方向不一致=离outlier驱动）
  │   5. 关键变量随时间/磨损/批次的变化趋势
  │
  └── 输出: workspace/analysis_output.json

Step 2: 诊断可视化
  ├── 根据分析结果生成图表（自写Python/mplotlib，非固定脚本）
  ├── 必须生成的图表：
  │   1. 参数-质量相关热力图
  │   2. 每个质量指标的Top预测因子条形图
  │   3. 关键参数-质量散点图（按分组维度着色）
  │   4. 分层相关对比图（Simpson检测可视化）
  │   5. 领域特定图表（刀具磨损曲线/温度剖面/设备状态演变等）
  └── 输出: figures/*.png + image_captions.json

Step 3: 物理推理与诊断
  ├── 读取 analysis_output.json + image_captions.json
  ├── 应用竞争假设协议（interpreter.md）
  ├── 物理合理性检验（基于该工艺领域的物理定律，不是预写定律库）
  ├── 图表引用+解读：每缺陷至少引用2张图，结合物理场景还原
  ├── 输出结构化诊断结论 + 图文诊断报告(diagnostic_report.md)
  └── 直接向用户呈现结果
```

## 数据列分类协议（Step 0核心）

加载数据后，必须将列分为以下角色。这是后续所有分析的基础：

| 角色 | 定义 | 典型例子 |
|------|------|---------|
| **timestamp** | 时间标记列 | timestamp, datetime, time |
| **process_param** | 可控/可测的工艺参数 | 温度、压力、转速、流量、电流 |
| **quality_metric** | 质量/缺陷指标 | 粗糙度、缺陷计数、偏差、不良率 |
| **group_var** | 分组/分层维度 | 产品型号、材料、设备编号、班次 |
| **metadata** | 标识信息，不参与关联 | part_id, batch_id, operator |
| **confounder** | 混杂变量（可能同时影响参数和质量） | ambient_temp, operator, raw_material_lot |

**分类方法**：
1. 先看列名关键词（temp/pressure/speed/force → process; roughness/defect/error/grade → quality; material/product/device → group）
2. 再看数值分布（连续且变化大 → process/quality；类别型 → group/confounder）
3. 不确定的列标注为"uncertain"，不参与核心关联分析，仅在探索性分析中使用

## Anti-Speculation Rules

- **不预设因果方向** — 数据告诉你什么相关，物理定律告诉你是否可能因果
- **分层分析是硬要求** — 如果有分组维度（材料/产品/设备），必须在组内验证，层内方向反转 = Simpson's Paradox
- **Spearman vs Pearson方向不一致 = 离outlier驱动** — 标记而非淘汰，但降低置信度
- **量级匹配是硬约束** — 原因的量级必须能解释效果的量级
- **物理排除优先于统计** — 物理不可能 = 排除，无论r多大
- **COMPETING_SET是有效结论** — 数据无法区分时诚实说明
- **不要编造数据** — 只引用分析结果中的真实数字

## 参考脚本（方法学参考，非固定流程）

| 脚本 | 提供的方法学 | 适用场景 |
|------|------------|---------|
| `deep_analyze.py` | 高频时序动态特征提取、批次窗口对齐、12维度关联展开 | 有高频时序+批次标签的场景 |
| `deep_visualize.py` | 热力图/散点图/分层对比图的生成方法 | 任何需要可视化的场景 |
| `stats.mjs` | 批次聚合数据的基础统计方法 | 批次级数据 |
| `inspect.mjs` | 数据快速探查方法 | 任何数据 |

**使用原则**：这些脚本提供"怎么算"的方法学参考，但不直接运行。Agent根据实际数据结构选择合适的方法，自行编写分析代码。

## Agent Architecture (v8.0)

| Agent | 作用 | 对应Step |
|-------|------|---------|
| **main agent** | 编排全流程：数据理解→分析→可视化→诊断 | Step 0-3 |
| **interpreter** | 物理推理+竞争假设+诊断报告 | Step 3 |

Main Agent 在 Step 1-2 中自行编写和执行分析代码。这确保了对任何工业数据的适配性。

## Output Files

保存到 `workspace/` 目录：
- `analysis_output.json` — 全部分析结果
- `figures/*.png` — 诊断图表
- `image_captions.json` — 图表结构化描述
- `diagnosis.json` — 结构化诊断结论
- `reasoning_chain.json` — 物理推理链
- `diagnostic_report.md` — 图文诊断报告（嵌入图表+物理场景还原）
