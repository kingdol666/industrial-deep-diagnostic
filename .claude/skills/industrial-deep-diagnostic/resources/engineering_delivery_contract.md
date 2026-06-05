# Engineering Delivery Contract

本 Skill 的工程化交付标准如下：

## 1. 严格流水线

必须按以下顺序执行并留痕：
- setup
- inspect
- context_builder
- clarification_gate
- data_processor
- diagnostician
- judge
- reporter
- audit
- present

任何一步都不能静默跳过。若不适用，必须在对应工件中记录 `not_applicable_reason`。

## 2. 最低交付工件

一次有效运行至少要交付：
- `00_input/run_config.json`
- `00_input/input_manifest.json`
- `01_ontology/ontology.json`
- `02_processed/scenario_classification.json`
- `02_processed/anomaly_report.json`
- `02_processed/data_analysis_conclusion.json`
- `03_figures/plot_manifest.json`
- `03_figures/visual_analysis.json`
- `03_figures/image_captions.json`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `05_review/judge_feedback.json`
- `report.md`
- `run_summary.json`
- `optimizer.md`
- `evidence_closure_report.json`

若存在有效时间列，还必须交付：
- `03_figures/fig_master_time_aligned_overlay.png`

## 3. 证据闭环

必须同时具备：
- 纯工艺波动分析
- 工艺+检测双驱动分析
- 本体/行业知识解释
- 诊断结论与审查传递

## 4. 子代理交付责任

- `context-builder`：对领域知识、本体、澄清需求负责
- `data-processor`：对数据分析、图像、VLM视觉证据、专家数据结论负责
- `diagnostician`：对竞争假说、物理推理、最终诊断结构负责
- `judge`：对质量门审查负责
- `reporter`：对最终报告和 run_summary 负责
- `report-reviewer`：对物理真实性审计和 `optimizer.md` 标准优化交付物负责

## 5. optimizer.md 标准交付要求

`optimizer.md` 必须是基于当前数据和具体场景的优化方案，不能只是审计意见或通用建议。它必须包含：
- 场景特异性优化方案：说明当前数据支持哪些工艺、维护、检测、控制、采样或过程窗口改善
- 当前场景存在的问题和改善机会：列出异常行为、质量链路、测量缺口、混杂因素、物理模型缺口和图像证据缺口
- 下一步诊断确认计划：说明还需要采集什么数据、做什么受控试验、补什么物理验证，才能进一步提高诊断准确性和确定性
- 行动分类：区分立即遏制、低风险优化、受控实验、测量/数据改善、暂缓或不安全行动

## 6. 最终通过条件

一次运行仅在以下条件全部满足时才算工程完成：
- `pipeline-log-check.mjs` 通过
- `evidence-closure-check.mjs` 通过
- `artifact-check.mjs` 通过
- `optimizer.md` 存在并通过标准章节完整性检查
- `run_manifest.json` 中 `present` 步骤完成
- `.pipeline_events.jsonl` 中存在最终 `run_completed` 事件
