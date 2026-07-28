---
name: industrial-data-processor
description: "工业诊断管线 — ontologically-guided 统计分析 + 可视化图表 + artifact 完整性修复。运行 Simpson/去趋势/变点/时滞CCF/批次唯一性/离群杠杆等验证。Trigger: 统计分析, data processing, 数据清洗, 数据可视化, 图表生成, statistics, Simpson, correlation, CCF, 批次分析, data processor. Do NOT use for general data analysis or statistics homework."
---

# Industrial Data Processor

在本体引导下对工业传感器/工艺数据执行全链路统计分析——场景分类、数据清洗、生产状态识别、多维度统计验证、可视化图表生成。产出 `data_analysis_conclusion.json` 作为诊断专家的强制交接文件。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | 领域本体（CP-2 已通过） |
| `00_input/input_manifest.json` | 数据源信息 |
| `00_input/run_config.json` | 运行配置 |
| `00_input/rag_deep_understanding.json` | RAG 验证队列（如有） |
| 原始数据文件 | CSV/XLSX/Parquet（DATA_PATH 指向） |

### Outputs

| File | Description |
|------|-------------|
| `02_processed/scenario_classification.json` | 场景分类 |
| `02_processed/anomaly_report.json` | 异常报告 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论（强制交接文件） |
| `02_processed/validate_report.json` | 统计验证报告 |
| `02_processed/feature_summary.json` | 特征摘要 |
| `02_processed/production_regime_filter.json` | 生产状态过滤（如适用） |
| `02_processed/time_lag_analysis.json` | 时滞分析结果（如适用） |
| `02_processed/duplicate_batch_report.json` | 批次重复报告（如适用） |
| `02_processed/analysis_plan.md` | 分析计划 |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/image_captions.json` | 图表说明 |
| `03_figures/visual_analysis.json` | VLM 视觉分析输出 |
| `03_figures/*.png` | 可视化图表 |

## Dispatch

启动 `data-processor` 子Agent（**ontology_first** 模式——统计前先读本体）：

```javascript
Agent({
  subagent_type: "data-processor",
  description: "ontologically-guided 统计分析 + 可视化",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>

Read "<this-skill-directory>/references/agent-protocol.md" and execute Phase 0-6.

Key constraints:
- Phase 0.4 gates all analysis — read ontology before any statistical work
- v6.5: Production regime detection (three-algorithm fusion) runs BEFORE stats; filter to steady-state only
- v6.4: Time-lag compensation (CCF-based optimal lag per parameter pair)
- v6.5: Per-product mandatory analysis — worst product by anomaly rate, steady-state compare, Simpson detection
- v6.6: Batch identity integrity — verify batch_id uniqueness; split/duplicate batch records MUST be merged or flagged
- v6.7: Leave-one-out leverage check — any |r|≥0.3 cited as evidence must pass leave-one-out
- Python venv: "<this-skill-directory>/scripts/.venv/bin/python" (run uv_env_setup.mjs first if missing)
- VLM 视觉分析已合并至 Phase 5.5（metadata-first，VLM_ENABLED=true 时调用 API，含防伪造验证）
  run_in_background: true
})
```

### Post-Processing (after agent completes)

```bash
SKILL_PATH="<this-skill-directory>"

# Normalize anomaly report + synthesize data analysis conclusion
node "$SKILL_PATH/scripts/data-processor-finalize.mjs" "$RUN_DIR"
```

## Execution Flow (Phase 0-6)

Full protocol in `references/agent-protocol.md` (Phase 0-6 checklist, persona, data truth mandate, gates). On-demand references at `resources/execution_reference.md` (bash commands), `resources/anti_spurious_rules.md` (v6 rules), `resources/scenario_patterns.md` (scenario-specific analysis patterns), and `resources/visual_analysis_framework.md` (chart design).

| Phase | Purpose | Gate |
|-------|---------|------|
| 0 | Data exploration + ontology-first analysis plan | `analysis_parameter_selection.json` + plan section |
| 1 | Scenario classification + production state detection | Schema-valid `scenario_classification.json`; stats input source determined |
| 2 | Universal analysis (stats, anomaly, time-lag, batch integrity) | `feature_summary.json` + `validate_report.json` exist; `data_source` set |
| 3 | Scenario-specific deep analysis + dual-drive | Schema-valid `data_analysis_conclusion.json`; coverage matrix complete |
| 4 | RAG knowledge validation | All claims validated or marked untestable |
| 5 | Visualization — per-product time-aligned overlays | `plot_manifest.json` has ≥1 verified real plot |
| 5.5 | VLM visual analysis (optional, auto-degrade) | `visual_analysis.json` exists (metadata or VLM-enriched) |
| 6 | Stabilize + verify output contract | All mandatory files exist and non-empty |

## Verification

```bash
SKILL_PATH="<this-skill-directory>"
SHARED_PATH="<omc-shared-directory>"

# Schema validations
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/scenario_classification_schema.json" \
  "$RUN_DIR/02_processed/scenario_classification.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/anomaly_report_schema.json" \
  "$RUN_DIR/02_processed/anomaly_report.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/data_analysis_conclusion_schema.json" \
  "$RUN_DIR/02_processed/data_analysis_conclusion.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/image_captions_schema.json" \
  "$RUN_DIR/03_figures/image_captions.json"

# CP-4 Handoff: verify plot_manifest has plots
test -f "$RUN_DIR/02_processed/data_analysis_conclusion.json" && \
  node -e "var p=JSON.parse(require('fs').readFileSync('$RUN_DIR/03_figures/plot_manifest.json','utf8')); process.exit(p.plots&&p.plots.length>0?0:1)"
```

## Artifact Integrity Recovery

Missing outputs auto-restored by scripts in `<SKILL_PATH>/scripts/`:

| Missing | Recovery |
|---------|----------|
| `scenario_classification.json` | Infer from ontology.json + feature_summary.json |
| `anomaly_report.json` | Infer from validate_report + data_analysis_conclusion |
| `plot_manifest.json` | Reverse from 03_figures/*.png |
| `image_captions.json` | Generate fallback from plot_manifest |

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Python venv missing | `node scripts/uv_env_setup.mjs` |
| Files >500MB | `python scripts/file_inspect.py --sample 50000` |
| Plot generation fails | Fix data and rerun; else L4 text fallback in `image_captions.json` |
| No time column | Document in `analysis_plan.md` + `data_analysis_conclusion.json` |
