---
name: industrial-reporter
description: "工业诊断管线 — 从诊断产物生成 9 节金字塔结构中文诊断报告 (report.md) 和结构化摘要 (run_summary.json)。Trigger: 写报告, 诊断报告, report generation, generate report, 报告生成, write report. Judge-gated: only after Judge verdict=pass and score≥90 (or 3 repair rounds exhausted). Do NOT use before judge gate has passed."
---

# Industrial Reporter

从诊断产物生成 9 节金字塔结构中文诊断报告 `report.md` 和结构化摘要 `run_summary.json`。Judge-gated: 仅在 Judge verdict=pass 且 score≥90（或 3 轮耗尽）后才可启动。

## Inputs → Outputs

| Input | Source | Output |
|-------|--------|--------|
| `04_diagnostics/diagnosis.json` | Diagnostician | `report.md` (9 节金字塔报告) |
| `04_diagnostics/evidence.json` | Diagnostician | `run_summary.json` (结构化摘要) |
| `04_diagnostics/confidence.json` | Diagnostician | |
| `04_diagnostics/reasoning_chain.json` | Diagnostician | |
| `03_figures/visual_analysis.json` | Data Processor | |
| `03_figures/plot_manifest.json` | Data Processor | |
| `01_ontology/ontology.json` | Ontology Builder | |
| `02_processed/data_analysis_conclusion.json` | Data Processor | |
## 9-Section Report

| # | Title | Description |
|---|-------|-------------|
| 1 | 执行摘要 | 诊断类型、置信度、关键发现（≤300字） |
| 2 | 诊断背景 | 工艺/设备描述、数据概览、用户问题 |
| 3 | 数据质量评估 | 完整性、异常值、生产状态、批次完整性 |
| 4 | 统计分析发现 | 关键相关、异常模式、Simpson/趋势/时滞 |
| 5 | 假设检验 | 竞争假说表、证据支持/反对、排除理由 |
| 6 | 根因结论 | 物理逻辑链、因果路径、置信度 |
| 7 | 证据附录 | 证据等级总览、关键图表引用 |
| 8 | 建议与后续 | 可执行建议 + 具体证伪条件 |
| 9 | 方法论备注 | 分析方法、局限性、数据范围 |
## Execution

```javascript
Agent({
  subagent_type: "reporter",
  description: "生成 9 节金字塔结构中文诊断报告",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<path>
SKILL_PATH=<this-skill-directory>
Execute references/agent-protocol.md fully. Use visual_analysis.json as primary figure evidence.`,
  run_in_background: true
})
```

## Post-Processing & Verification

```bash
SKILL_PATH="<this-skill-directory>"
node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/run_summary_schema.json" "$RUN_DIR/run_summary.json"
test -f "$RUN_DIR/report.md" && test -f "$RUN_DIR/run_summary.json"
```

## References

- `references/agent-protocol.md` — Reporter 执行协议
- `templates/report_template.md` + `templates/run_summary_template.json` — 报告/摘要模板
- `schemas/run_summary_schema.json` — run_summary.json Schema
