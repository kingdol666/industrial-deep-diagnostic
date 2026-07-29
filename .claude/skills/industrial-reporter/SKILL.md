---
name: industrial-reporter
description: "工业诊断管线Step 6 — 从诊断产物生成9节金字塔结构中文诊断报告(report.md)和结构化摘要(run_summary.json)。Trigger: 写报告, 诊断报告, report generation, generate report, 报告生成, write report. Judge-gated: 仅在Judge verdict=pass且score≥90（或3轮耗尽）后才可启动。"
---

# Industrial Reporter

从诊断产物生成9节金字塔结构中文诊断报告`report.md`和结构化摘要`run_summary.json`。Judge-gated：仅在Judge verdict=pass且score≥90（或3轮耗尽）后才可启动。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 根因诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `03_figures/visual_analysis.json` | VLM视觉分析（主要图表证据来源） |
| `03_figures/plot_manifest.json` | 图表清单 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |
| `05_review/judge_feedback.json` | Judge质量门反馈 |

### Outputs

| File | Description |
|------|-------------|
| `report.md` | 9节金字塔结构中文诊断报告 |
| `run_summary.json` | 结构化摘要（schema-valid） |

## 9-Section Report Structure

| # | Section | Content |
|---|---------|---------|
| 1 | 执行摘要 | 诊断类型、置信度、关键发现（≤300字） |
| 2 | 诊断背景 | 工艺/设备描述、数据概览、用户问题 |
| 3 | 数据质量评估 | 完整性、异常值、生产状态、批次完整性 |
| 4 | 统计分析发现 | 关键相关、异常模式、Simpson/趋势/时滞（强制节，非附录） |
| 5 | 假设检验 | 竞争假说表、证据支持/反对、排除理由 |
| 6 | 根因结论 | 物理逻辑链、因果路径、置信度 |
| 7 | 证据附录 | 证据等级总览、关键图表引用 |
| 8 | 建议与后续 | 可执行建议 + 具体证伪条件 |
| 9 | 方法论备注 | 分析方法、局限性、数据范围 |

## Dispatch

启动 `reporter` 子Agent：

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "reporter",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-reporter>
SHARED_PATH=.claude/shared

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the complete report generation protocol.

Step 0: Read all diagnostic products from RUN_DIR:
- RUN_DIR/04_diagnostics/diagnosis.json
- RUN_DIR/04_diagnostics/evidence.json
- RUN_DIR/04_diagnostics/confidence.json
- RUN_DIR/04_diagnostics/reasoning_chain.json
- RUN_DIR/03_figures/visual_analysis.json
- RUN_DIR/03_figures/plot_manifest.json
- RUN_DIR/01_ontology/ontology.json
- RUN_DIR/02_processed/data_analysis_conclusion.json
- RUN_DIR/05_review/judge_feedback.json

Step 1: Generate 9-section pyramid report. Use $SKILL_PATH/templates/report_template.md as structure guide.
- Every chart must be embedded: ![title](03_figures/filename.png)
- visual_analysis.json is the primary source for VLM visual insights
- Section 4 (统计分析发现) is mandatory, not an appendix
- All web/external knowledge marked [EXTERNAL KNOWLEDGE]
- Report in Chinese; technical terms may be in English
- Write to RUN_DIR/report.md

Step 2: Generate structured summary. Use $SKILL_PATH/schemas/run_summary_schema.json schema and $SKILL_PATH/templates/run_summary_template.json template. Write to RUN_DIR/run_summary.json.

Step 3: Post-processing:
- node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"
- node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"

Step 4: Validate:
- node "$SHARED_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/run_summary_schema.json" "$RUN_DIR/run_summary.json"
- Verify both RUN_DIR/report.md and RUN_DIR/run_summary.json exist.
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md`.

| Step | Purpose |
|------|---------|
| 0 | 读取所有诊断产物（diagnosis/evidence/confidence/reasoning_chain/visual_analysis/plot_manifest/ontology/data_analysis_conclusion/judge_feedback） |
| 1 | 按9节金字塔结构生成report.md，嵌入所有图表 |
| 2 | 按schema生成run_summary.json结构化摘要 |
| 3 | 后处理：摘要合成 + 章节完整性检查 |
| 4 | 验证：schema校验 + 文件存在性 |

## Core Rules

- **每张图表必须嵌入**: `![title](03_figures/filename.png)`
- **visual_analysis.json 是VLM视觉洞察的主要来源**
- **Section 4 统计验证是强制节**，不是附录
- 所有web/外部知识标记 `[EXTERNAL KNOWLEDGE]`
- 报告用中文，技术术语可英文
- 中文双引号必须转义

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-reporter>"
SHARED_PATH=".claude/shared"

# Schema validation
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/run_summary_schema.json" \
  "$RUN_DIR/run_summary.json"

# Post-processing checks
node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"

# File existence
test -f "$RUN_DIR/report.md" && test -f "$RUN_DIR/run_summary.json"
```
