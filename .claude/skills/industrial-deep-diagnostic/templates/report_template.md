# 工业诊断报告 / Industrial Diagnostic Report

**场景 / Scene**: {{scene_name}}
**批次 / Batch**: {{batch_id}}
**日期 / Date**: {{date}}
**运行ID / Run ID**: {{run_id}}
**Judge评分 / Judge Score**: XX/100 (VERDICT)

---

## 1. 执行摘要 / Executive Summary
{{executive_summary}}

## 2. 推理概述 / Reasoning Overview
[Synthesized from `04_diagnostics/reasoning_chain.json`. Step-by-step trace of the diagnostic reasoning.]

### 2.1 数据特征 / Data Characterization
{{reasoning_data_char}}

### 2.2 统计发现 / Statistical Discovery
{{reasoning_stat_discovery}}

### 2.3 验证过滤 / Validation Filter
{{reasoning_validation_filter}}

### 2.4 假设演变 / Hypothesis Evolution
{{reasoning_hypothesis_evolution}}

### 2.5 关键观测与推断 / Key Observations vs Inferences
{{reasoning_inference_vs_observation}}

### 2.6 排除的假设 / What We Ruled Out
{{reasoning_ruled_out}}

### 2.7 不确定性边界 / Uncertainty Boundaries
{{reasoning_uncertainty_bounds}}

## 3. 分析目标 / Analysis Objective
{{analysis_objective}}

## 4. 用户上下文与约束 / User Context and Constraints
{{user_context}}

## 5. 工业上下文与本体 / Industrial Context and Ontology
{{ontology_summary}}

## 6. 参考文档 / Reference Documents Used
{{references_used}}

## 7. 外部知识 / External Research Used
{{external_research}}

> **注意**: 本节所有发现均标记为 EXTERNAL KNOWLEDGE，非数据来源。

## 8. 数据描述 / Data Description
{{data_description}}

### 8.1 数据摘要 / Data Summary
| 列名 | 类型 | 单位 | 类别 | 缺失% | 异常值% |
|------|------|------|------|-------|---------|
{{data_summary_table}}

### 8.2 采样特征 / Sampling Characteristics
{{sampling_characteristics}}

### 8.3 数据质量评估 / Data Quality Assessment
{{data_quality_assessment}}

## 9. 变量分类 / Variable Classification
{{variable_classification}}

## 10. 预处理与对齐 / Preprocessing & Alignment
{{preprocessing_methods}}

{{time_alignment}}

## 11. 可视化证据 — 逐图分析 / Visualization Evidence — Per-Figure Analysis

> **本节嵌入 `03_figures/` 中的所有图片。每张图片包含可视化发现和诊断含义。**

### 11.N {{figure_title}}
![{{figure_title}}](03_figures/{{figure_filename}})

**图表展示内容 / What this figure shows**: {{figure_description}}

**可视化发现 / Visual findings ([OBSERVATION], 证据等级 4)**: {{figure_visual_findings}}

**诊断含义 / Diagnostic implication**: {{figure_implication}}

**[统计验证图附加] 验证发现 / Validation finding**: {{validation_finding}}

*(对 `plot_manifest.json` 中的每张图重复。不要跳过任何图片。)*

## 12. 诊断结果 / Diagnostic Findings

### 12.1 证据排除的假设 / Evidence-Eliminated Hypotheses
{{eliminated_hypotheses}}

### 12.2 存活的假设及推理 / Surviving Hypotheses with Reasoning
{{surviving_hypotheses}}

### 12.3 因果链模型 / Causal Chain Models
{{causal_chain_models}}

## 13. 根因分析 — 综合 / Root Cause Analysis — Synthesis
{{root_cause_analysis}}

## 14. 统计验证与置信度评估 / Statistical Validation & Confidence Assessment

> **本节为 v6.0 强制节。必须透明披露所有统计验证发现。**

### 14.1 数据排序验证 / Data Sorting Validation
[声明数据是否按时间排序。如果不是，说明对滞后分析的影响。]

### 14.2 子组分析 (Simpson's Paradox 检查) / Subgroup Analysis
[对于每个关键相关性，报告它是否在主产品组内成立。]

| 关系 | 全数据集 r | 主子组 r | 方向 |
|-----|:---------:|:-------:|------|
| film_points vs MD_TH009 | 0.22 | -0.01 | 反转/REVERSED |

### 14.3 时间趋势混杂 / Time-Trend Confounding
[报告关键关系的去趋势相关性。]

| 关系 | 原始 r | 去趋势 r | 衰减率 |
|-----|:------:|:-------:|:-----:|
| W1C88 vs melt_spots | 0.37 | 0.09 | -76% |

### 14.4 相关性稳健性 / Correlation Robustness
[Spearman vs Pearson, 异常值敏感性检查。]

### 14.5 调整后的置信度评估 / Adjusted Confidence Assessment

| 假设 | 原始置信度 | 调整原因 | 调整后置信度 |
|-----|:--------:|---------|:----------:|
| H1 | 75 | PG31DS子组 Simpson's Paradox | 45-50 |

## 15. 竞争假设披露 / Competing Hypotheses Disclosure (v6.0)

> **本节为 v6.0 强制节。** 当诊断类型为 COMPETING_SET 时，必须清晰呈现所有竞争假设及其机制、证据、为何无法区分、以及区分条件。

{{competing_hypotheses}}

## 16. 置信度与不确定性 / Confidence & Uncertainty
{{confidence_and_uncertainty}}

## 17. 局限性与不确定性分析 / Limitations & Uncertainty

### 17.1 偶然不确定性 / Aleatory Uncertainty
{{aleatory_uncertainty}}
[不可约的过程噪声、测量误差。]

### 17.2 认知不确定性 / Epistemic Uncertainty
{{epistemic_uncertainty}}
[可通过更多数据或更好模型解决的不确定性。]

### 17.3 什么会改变我们的结论 / What Would Change Our Conclusions
{{what_would_change_conclusions}}

### 17.4 推理链弱点 / Reasoning Chain Weaknesses
{{reasoning_weaknesses}}

## 18. 建议行动 / Recommended Actions

| 优先级 | 行动 | 理由 | 证据强度 | 验证备注 |
|:------:|------|------|:------:|----------|
| P0 | ... | ... | 高 | 通过所有检查 |
| P1 | ... | ... | 中 | 在子组中衰减 |

## 19. 限制说明 / Limitations
{{limitations}}
[本分析不涵盖的内容。假设。注意事项。明确列出验证限制。]

## 20. 附录 / Appendix

### A. 运行配置 / Run Configuration
{{run_configuration}}

### B. 统计摘要 / Statistical Summary
{{feature_summary}}

### C. 变化点日志 / Change Point Log
{{change_point_log}}

### D. 文件清单 / File Inventory
{{file_inventory}}

### E. 幻觉审计日志 / Hallucination Audit Log
{{hallucination_audit_log}}
[每个主要结论根据 STOP 清单进行通行/失败检查。]

### F. 竞争假设可分辨性矩阵 / Discriminability Matrix (v6.0)
{{discriminability_matrix}}
[每个假设对的可分辨性评估。]
