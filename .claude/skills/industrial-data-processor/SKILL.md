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
| 原始数据文件 | CSV/TSV/分隔符文本/XLSX/XLSM/JSON/Parquet 或经 E-1 前处理的 `00_input/preprocessed_data.csv`（DATA_PATH 指向） |

### Outputs

| File | Description |
|------|-------------|
| `02_processed/scenario_classification.json` | 场景分类 |
| `02_processed/anomaly_report.json` | 异常报告 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论（强制交接文件） |
| `02_processed/validate_report.json` | 统计验证报告 |
| `02_processed/feature_summary.json` | 特征摘要 — 必须包含 columns(object)/dataset_profile(object)/metadata(object) 三个顶层字段 (feature_summary_schema required) |
| `02_processed/production_regime_filter.json` | 生产状态过滤（如适用） |
| `02_processed/time_lag_analysis.json` | 时滞分析结果（如适用） |
| `02_processed/duplicate_batch_report.json` | 批次重复报告（如适用） |
| `02_processed/analysis_plan.md` | 分析计划 |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/image_captions.json` | 图表说明 |
| `03_figures/visual_analysis.json` | VLM 视觉分析输出 |
| `03_figures/*.png` | 可视化图表 |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent data-processor --step data_processor

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent data-processor --step data_processor \
  --files 02_processed/data_analysis_conclusion.json,02_processed/validate_report.json,03_figures/plot_manifest.json,03_figures/visual_analysis.json,03_figures/image_captions.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

启动 `data-processor` 子Agent（**ontology_first** 模式——统计前先读本体）：

```javascript
Agent({
  subagent_type: "data-processor",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>

Read "$SKILL_PATH/references/agent-protocol.md" and execute Phase 0-6.

Key constraints:
- Phase 0.4 gates all analysis — read ontology before any statistical work
- v6.5: Production regime detection (three-algorithm fusion) runs BEFORE stats; filter to steady-state only
- v6.4: Time-lag compensation (CCF-based optimal lag per parameter pair)
- v6.5: Per-product mandatory analysis — worst product by anomaly rate, steady-state compare, Simpson detection
- VLM 视觉分析通过独立 Agent() 派发 vlm-visual-analyzer Agent — 参见下方 VLM Visual Analysis Dispatch 节
`
})
```

### VLM Visual Analysis Dispatch (Phase 5.5)

#### Step 0: Generate VLM-Specialized Temporal Overlay Charts

Before dispatching VLM, generate VLM-optimized temporal overlay charts following `visual_analysis_framework.md` design specs:

```bash
# Generate fig_vlm_temporal_overlay.png (all parameters, z-score normalized, direction-aligned)
# Generate fig_vlm_per_product_overlay.png (per-group temporal alignment)
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/generate_vlm_charts.py" "$RUN_DIR" \
  --target-cols <quality_cols> \
  --key-params <process_params> \
  --group-col <group_col> \
  --time-col <time_col> \
  --events <events_json>
```

Key design specs for VLM chart（参考 `resources/visual_analysis_framework.md` §设计原则）:
- 所有参数 z-score 归一化到同一尺度
- 负相关参数反转方向（使所有线同向变化）
- 共享 x 轴（时间）— 仅当存在有效时间列时
- 事件标记为红色虚线 + 文字标注
- 字体 >= 12pt，高对比度
- 标题用英文（兼容 matplotlib 渲染）

#### Step 1: Build VLM Input Filter Manifest

**Not all images go to VLM.** Only images with true spatio-temporal alignment carry diagnostic value for VLM. Generate `vlm_input_manifest.json` to filter:

| Priority | Image Type | VLM Value | Example |
|----------|-----------|-----------|---------|
| **MANDATORY** | Temporal overlay (multi-param, shared time axis, normalized) | VLM reads synchrony, precedence, event response, trend morphology | `fig_vlm_temporal_overlay.png` |
| **MANDATORY** | Per-product temporal overlay | VLM reads group-specific degradation patterns | `fig_vlm_per_product_overlay.png` |
| **SUPPLEMENTARY** | Scatter with confounder coloring | VLM checks Simpson Paradox (cluster separation) | `separator_vs_residue.png` |
| **NOT_FOR_VLM** | Single-param trend, bar chart, basic plot | No cross-parameter insight for VLM | `correlation_robustness.png`, `mill_power_trend.png` |

```bash
# Generate vlm_input_manifest.json (selects which images VLM reads)
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/generate_vlm_manifest.py" "$RUN_DIR" --plot-manifest "$RUN_DIR/03_figures/plot_manifest.json"
```

#### Step 2: Write Skeleton (Fallback Base)

```bash
node "$SKILL_PATH/scripts/generate_captions.mjs" "$RUN_DIR"
# Write visual_analysis.json with observation_mode: "skeleton_pre_vlm"
```

#### Step 3: Dispatch vlm-visual-analyzer Agent

**Only images in `vlm_input_manifest.json` are sent to VLM.** VLM MUST read `vlm_input_manifest.json` first to know which images to read and in what order.

```javascript
Agent({
  subagent_type: "vlm-visual-analyzer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>
SHARED_PATH=.claude/shared/
DATA_PATH=<data-file-path>

Read ".claude/agents/vlm-visual-analyzer.md" and follow the complete VLM visual analysis protocol.

## IMAGE SELECTION (MANDATORY — DO NOT READ ALL PNGs)
- FIRST read "vlm_input_manifest.json" from RUN_DIR/03_figures/
- ONLY read images listed in vlm_input_manifest.json with priority MANDATORY or SUPPLEMENTARY
- DO NOT read images excluded from vlm_input_manifest — they have no cross-parameter temporal alignment
- Read MANDATORY images first (temporal overlays), then SUPPLEMENTARY (scatter for Simpson check)
- MANDATORY images have z-score normalization + direction reversal — understand this before interpretation

Key constraints:
- Read ontology.json BEFORE reading any image — blind image reading is prohibited
- Read vlm_input_manifest.json for image priority ordering (NOT plot_manifest.json directly)
- Read data_analysis_conclusion.json and validate_report.json for statistical context
- Read each selected PNG in priority order, extracting structured visual observations
- Focus on: temporal synchrony, precedence signals, event response, trend morphology, group separation
- Overwrite skeleton_pre_vlm if present — final output MUST have analysis_provenance.source_agent = "vlm-visual-analyzer"
- Output visual_analysis.json and image_captions.json to RUN_DIR/03_figures/
- At least 2 key visual observations MUST contain non-empty ontology_context
- Fallback: if VLM_ENABLED=false or API unavailable, write metadata-only skeleton with observation_mode: "metadata_fallback"
`
})
```

VLM 分析完成后进行防伪造验证：

```bash
# Verify source_agent, skeleton_overwritten, and that only vlm_input_manifest images were read
node "$SKILL_PATH/scripts/vlm-verification-check.mjs" "$RUN_DIR"
# Verify that excluded images were NOT read
uv run --project "$SHARED_PATH/scripts" python -c "import json; v=json.load(open('$RUN_DIR/03_figures/visual_analysis.json')); m=json.load(open('$RUN_DIR/03_figures/vlm_input_manifest.json')); vlm_files=[i['filename'] for i in m['vlm_images']]; read=[i['filename'] for i in v.get('chart_inventory',[]) if i.get('filename') in vlm_files]; excluded_read=[i['filename'] for i in v.get('chart_inventory',[]) if i.get('filename') not in vlm_files]; print(f'VLM read {len(read)}/{len(vlm_files)} selected images, excluded reads: {excluded_read if excluded_read else "NONE (clean)"}')"

### Post-Processing (after both agents complete)

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-data-processor>"

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

## Data Truth Mandate

**每一个写入 JSON/报告的数字必须可从原始数据重算。**

| 规则 | 要求 |
|------|------|
| 数字可追溯性 | 每个数字必须标注数据源(cleaned/raw)、行范围、计算方法 |
| 派生值标记 | 推断/派生值必须显式 `"derived": true` 或 `"inferred": true` |
| 清洗留痕 | cleaning_integrity 记录全部清洗操作 |
| 可视化可追溯 | 每张图的每个数据点可追溯到数据集的具体行 |
| 不可用标记 | 无法从数据计算的 → 写 NOT_APPLICABLE + 原因 |

## Counterfactual Reasoning — 排除约束

| 约束 | 说明 |
|------|------|
| 四条件 | 时间先后 + 统计显著 + 物理机制 + 无矛盾 |
| 排除标准 | 任一条件不满足 → 标记为排除候选项并提供量化依据 |
| 物理边界 | 排除必须有第一性原理或控制方程支撑 |
| 置信阈值 | 排除置信度 <80 时标记 `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| 类别 | 要求 |
|------|------|
| 数据限制 | 采样率/噪声/缺失最值/范围限制 |
| 模型假设 | 线性近似/稳态假设/分布假设 |
| 未控制混淆 | 明确列出无法控制的潜在混淆变量 |
| 结论可信区间 | 每个结论标注置信度 ± 误差范围 |

## Efficiency — Parallel Execution

- 与上下游 agent 无数据依赖时 → 主动并行
- 对可预测结果使用确定性脚本而非 LLM 推理
- 大文件采样策略: >100K 行时系统抽样
- Agent stall >600s → 检查已有产物, 部分可用的继续推进

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-data-processor>"
SHARED_PATH=".claude/shared/"

# Schema validations
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/scenario_classification_schema.json" \
  "$RUN_DIR/02_processed/scenario_classification.json"

# Feature summary schema compliance (MUST include columns/dataset_profile/metadata)
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/feature_summary_schema.json" "$RUN_DIR/02_processed/feature_summary.json"

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

Missing outputs auto-restored by scripts in `.claude/skills/industrial-data-processor/scripts/`:

| Missing | Recovery |
|---------|----------|
| `scenario_classification.json` | Infer from ontology.json + feature_summary.json |
| `anomaly_report.json` | Infer from validate_report + data_analysis_conclusion |
| `plot_manifest.json` | Reverse from 03_figures/*.png |
| `image_captions.json` | Generate fallback from plot_manifest |

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Python venv missing | `node .claude/shared/scripts/uv_env_setup.mjs` |
|| Files >500MB | `uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-data-processor/scripts/file_inspect.py --sample 50000` |
| Plot generation fails | Fix data and rerun; else L4 text fallback in `image_captions.json` |
| No time column | Document in `analysis_plan.md` + `data_analysis_conclusion.json` |
