---
name: darwin-skill
description: "Darwin evolutionary skill evaluation tracker — tracks skill quality scores across dimensions over time. Used for internal skill fitness assessment and evolution tracking. Trigger: skill fitness, 技能评估, skill quality, evolutionary tracking, 技能进化."
---

# Darwin Skill — Evolutionary Skill Quality Tracker

Tracks skill quality scores across evaluation dimensions over commit history. Used for internal OMP skill fitness monitoring.

## Overview

This skill provides evolutionary fitness tracking for OMP skills. It records baseline evaluations and score changes across skill versions, enabling data-driven skill improvement.

## Data

Evaluation results are stored in `results.tsv`:

| Column | Description |
|--------|-------------|
| timestamp | Evaluation date/time |
| commit | Git commit reference |
| skill | Skill being evaluated |
| old_score | Previous score (or `-` for baseline) |
| new_score | Current evaluation score |
| status | baseline / improved / regressed |
| dimension | Evaluation dimension affected |
| note | Free-text evaluation notes |
| eval_mode | dry_run / live |

## Data Truth Mandate

**每一个写入 JSON/报告的数字必须可从原始数据重算。**
|规则|要求|
|---|---|
|数字可追溯性|每个数字必须标注数据源(cleaned/raw)、行范围、计算方法|
|派生值标记|推断/派生值必须显式 `"derived": true` 或 `"inferred": true`|
|清洗留痕|cleaning_integrity 记录全部清洗操作|
|可视化可追溯|每张图的每个数据点可追溯到数据集的具体行|
|不可用标记|无法从数据计算的 → 写 NOT_APPLICABLE + 原因|

## Counterfactual Reasoning — 排除约束

|约束|说明|
|---|---|
|四条件|时间先后 + 统计显著 + 物理机制 + 无矛盾|
|排除标准|任一条件不满足 → 标记为排除候选项并提供量化依据|
|物理边界|排除必须有第一性原理或控制方程支撑|
|置信阈值|排除置信度 <80 时标记 `[WEAK_EXCLUSION]`|

## Assumptions & Limitations

|类别|要求|
|---|---|
|数据限制|采样率/噪声/缺失最值/范围限制|
|模型假设|线性近似/稳态假设/分布假设|
|未控制混淆|明确列出无法控制的潜在混淆变量|
|结论可信区间|每个结论标注置信度 ± 误差范围|

## Efficiency — Parallel Execution

- 与上下游 agent 无数据依赖时 → 主动并行
- 对可预测结果使用确定性脚本而非 LLM 推理
- 大文件采样策略: >100K 行时系统抽样
- Agent stall >600s → 检查已有产物, 部分可用的继续推进

## Usage

```bash
# View evaluation history
cat .claude/skills/darwin-skill/results.tsv

# Append a new evaluation
echo "$(date -Iseconds)\t<commit>\t<skill-name>\t<old>\t<new>\t<status>\t<dim>\t<note>\tdry_run" >> .claude/skills/darwin-skill/results.tsv
```

## Integration

This skill is used by the OMP harness to track skill quality trends. Not part of the industrial diagnostic pipeline — it's a meta-skill for OMP skill governance.
