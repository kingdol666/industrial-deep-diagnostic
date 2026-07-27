---
name: industrial-reporter
description: "工业诊断管线 — 从诊断产物生成 9 节金字塔结构中文诊断报告 (report.md) 和结构化摘要 (run_summary.json)。Trigger: 写报告, 诊断报告, report generation, generate report, 报告生成, write report. Do NOT use before judge gate has passed."
---

# Industrial Reporter

从诊断产物（diagnosis + evidence + confidence + reasoning_chain + visual_analysis）生成 9 节金字塔结构中文诊断报告 `report.md` 和结构化摘要 `run_summary.json`。

Judge-gated: 仅在 Judge verdict=pass 且 score≥90（或 judge_repair_summary 证明 3 轮耗尽）后才可启动。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `03_figures/visual_analysis.json` | VLM 视觉证据（primary figure evidence） |
| `03_figures/plot_manifest.json` | 图表清单 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |

## Outputs

| File | Description |
|------|-------------|
| `report.md` | 9 节金字塔结构中文诊断报告 |
| `run_summary.json` | 结构化摘要 |

## Execution

启动 `reporter` 子Agent：

```javascript
Agent({
  subagent_type: "reporter",
  description: "生成 9 节金字塔结构中文诊断报告",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>/../../../.claude/skills/industrial-reporter

Read "<this-skill-directory>/../../../.claude/skills/industrial-reporter/references/agent-protocol.md" and execute the complete reporting protocol.
Use visual_analysis.json as primary figure evidence.
Follow the 9-section pyramid structure from the report template.`,
  run_in_background: true
})
```

### Report Structure (9 Sections)

| Section | Title | Content |
|---------|-------|---------|
| 1 | 执行摘要 | 诊断类型、置信度、关键发现（≤300字） |
| 2 | 诊断背景 | 工艺/设备描述、数据概览、用户问题 |
| 3 | 数据质量评估 | 完整性、异常值、生产状态、批次完整性 |
| 4 | 统计分析发现 | 关键相关、异常模式、Simpson/趋势/时滞 |
| 5 | 假设检验 | 竞争假说表、证据支持/反对、排除理由 |
| 6 | 根因结论 | 物理逻辑链、因果路径、置信度 |
| 7 | 证据附录 | 证据等级总览、关键图表引用 |
| 8 | 建议与后续 | 可执行建议 + 具体证伪条件 |
| 9 | 方法论备注 | 分析方法、局限性、数据范围 |

### Post-Processing

```bash
SKILL_PATH="<this-skill-directory>/../../../.claude/skills/industrial-reporter"

# Synthesize run summary
node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"

# Report section check
node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"
```

## Verification

```bash
SKILL_PATH="<this-skill-directory>/../../../.claude/skills/industrial-reporter"

# Schema validation
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/run_summary_schema.json" \
  "$RUN_DIR/run_summary.json"

# CP-7: Report gate
test -f "$RUN_DIR/report.md" && test -f "$RUN_DIR/run_summary.json"
```

## References

- `references/agent-protocol.md` — 完整的 Reporter 执行协议
- `schemas/run_summary_schema.json` — run_summary.json Schema
- `templates/report_template.md` — 9 节报告模板
- `templates/run_summary_template.json` — 摘要模板
