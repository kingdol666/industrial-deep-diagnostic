---
name: industrial-data-processor
description: "工业诊断管线 — ontologically-guided 统计分析 + 可视化图表 + artifact 完整性修复。运行 Simpson/去趋势/变点/时滞CCF/批次唯一性/离群杠杆等验证。Trigger: 统计分析, data processing, 数据清洗, 数据可视化, 图表生成, statistics, Simpson, correlation, CCF, 批次分析, data processor. Do NOT use for general data analysis or statistics homework."
---

# Industrial Data Processor

在本体引导下对工业传感器/工艺数据执行全链路统计分析——场景分类、数据清洗、生产状态识别、多维度统计验证（Simpson/去趋势/变点/时滞CCF/批次唯一性/离群杠杆）、可视化图表生成。产出 `data_analysis_conclusion.json` 作为诊断专家的强制交接文件。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | 领域本体（CP-2 已通过） |
| `00_input/input_manifest.json` | 数据源信息 |
| `00_input/run_config.json` | 运行配置 |
| `00_input/rag_deep_understanding.json` | RAG 验证队列（如有） |
| 原始数据文件 | CSV/XLSX/Parquet（DATA_PATH 指向） |

## Outputs

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
| `03_figures/visual_analysis.json` | VLM pre-skeleton |
| `03_figures/*.png` | 可视化图表 |

## Execution

启动 `data-processor` 子Agent，**ontology_first** 模式——在任何统计工作前先读取本体：

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
- VLM visual analysis is handled by Step 3.5 (industrial-vlm-analyzer), NOT by data-processor
- Write visual_analysis.json as pre-VLM skeleton only`,
  run_in_background: true
})
```

### Post-Processing (after agent completes)

```bash
SKILL_PATH="<this-skill-directory>"

# Normalize anomaly report (补全缺失字段)
node "$SKILL_PATH/scripts/normalize-anomaly-report.mjs" "$RUN_DIR"

# Synthesize data analysis conclusion (聚合所有分析产物)
node "$SKILL_PATH/scripts/synthesize-data-analysis-conclusion.mjs" "$RUN_DIR"
```

### Key Analysis Phases

| Phase | Content | Key Validation |
|-------|---------|----------------|
| 0 | 数据探索 + 本体读取 (ontology_first) | 列类型推断、缺失率、值域 |
| 0.4 | 本体引导分析计划 | 从 ontology 确定分析参数和分层维度 |
| 1 | 场景分类 | scenario_classification.json |
| 2 | 数据转换 + 预处理 + 清洗完整性 | cleaning_integrity_check.py |
| 2.5 | 生产状态识别 (v6.5) | 三算法融合：稳态/过渡/启停 |
| 3 | 统计分析 | Simpson/去趋势/变点/时滞CCF/批次唯一性/离群杠杆 |
| 4 | 专家缺口分析 | 对比 RAG 验证队列 |
| 5 | 物理检查 + 可视化 + 结论合成 | per-product overlay 图表 |

## Verification

```bash
SKILL_PATH="<this-skill-directory>"

# Schema validations
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/scenario_classification_schema.json" \
  "$RUN_DIR/02_processed/scenario_classification.json"

node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/anomaly_report_schema.json" \
  "$RUN_DIR/02_processed/anomaly_report.json"

node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/data_analysis_conclusion_schema.json" \
  "$RUN_DIR/02_processed/data_analysis_conclusion.json"

node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/image_captions_schema.json" \
  "$RUN_DIR/03_figures/image_captions.json"

# CP-4 Handoff
test -f "$RUN_DIR/02_processed/data_analysis_conclusion.json" && \
  node -e "var p=JSON.parse(require('fs').readFileSync('$RUN_DIR/03_figures/plot_manifest.json','utf8')); process.exit(p.plots&&p.plots.length>0?0:1)"
```

## Artifact Integrity (Step 3.3)

缺失产物的自动恢复——使用 `scripts/` 下的恢复脚本：

| 缺失文件 | 恢复方式 |
|---------|---------|
| scenario_classification.json | 从 ontology.json + feature_summary.json 推断 |
| anomaly_report.json | 从 validate_report + data_analysis_conclusion 推断 |
| plot_manifest.json | 从 03_figures/*.png 反推 |
| image_captions.json | 从 plot_manifest 生成回退 caption |

## Failure Recovery

| 场景 | 恢复 |
|------|------|
| Python venv 缺失 | `node scripts/uv_env_setup.mjs` 重建（uv 管理） |
| 超大文件 (>500MB) | `python scripts/file_inspect.py --sample 50000` 采样 |
| 图片生成失败 | Phase 2.2.5 + Phase 5.9 修数据重画 → 仍失败则 `image_captions.json` L4 文本回退 |
| 无可用时间列 | 记录原因到 `analysis_plan.md` + `data_analysis_conclusion.json` |

## References

- `references/agent-protocol.md` — 完整的 data-processor 执行协议（Phase 0-6, 1139 lines）
- `schemas/` — 5 个输出 JSON Schema
- `scripts/` — 统计分析 + 可视化 + 后处理脚本（stats.mjs, dp_toolkit.py, time_lag_compensator.mjs 等）
- `resources/visual_analysis_framework.md` — 图表视觉分析框架
