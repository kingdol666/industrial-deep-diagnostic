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
- `report-reviewer`：对物理真实性审计负责

## 5. 最终通过条件

一次运行仅在以下条件全部满足时才算工程完成：
- `pipeline-log-check.mjs` 通过
- `evidence-closure-check.mjs` 通过
- `artifact-check.mjs` 通过
- `run_manifest.json` 中 `present` 步骤完成
- `.pipeline_events.jsonl` 中存在最终 `run_completed` 事件
