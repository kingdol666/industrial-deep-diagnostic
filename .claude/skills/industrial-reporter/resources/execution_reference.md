# Reporter — Detailed Execution Reference

## Step 0: Load All Evidence Artifacts

Required reading (RUN_DIR):
- `00_input/user_context.json` — user scenario, known issues
- `01_ontology/ontology.json` — physical meaning of parameters, process stages
- `01_ontology/schema.json` — variable classification schema
- `02_processed/data_quality_report.json` — data quality
- `02_processed/feature_summary.json` — statistical features
- `02_processed/validate_report.json` — statistical validation
- `02_processed/scenario_classification.json` — scenario classification
- `02_processed/anomaly_report.json` — anomaly intervals, dual-driver
- `02_processed/data_analysis_conclusion.json` — Data-processor expert handover
- `02_processed/production_regime_filter.json` — steady-state filtering (v6.5)
- `02_processed/time_lag_analysis.json` — time-lag compensation (v6.4)
- `03_figures/plot_manifest.json` — chart inventory
- `03_figures/visual_analysis.json` — VLM visual analysis
- `03_figures/image_captions.json` — chart captions
- `04_diagnostics/diagnosis.json` — diagnostic conclusion
- `04_diagnostics/evidence.json` — evidence inventory
- `04_diagnostics/confidence.json` — confidence decomposition
- `04_diagnostics/reasoning_chain.json` — full reasoning chain
- `05_review/judge_feedback.json` — Judge score

Optional reading:
- `00_input/extracted_knowledge.json` / `rag_deep_understanding.json`
- `02_processed/zone_analysis.json` / `event_analysis.json`
- `02_processed/analysis_plan.md`

Read from SKILL_PATH:
- `resources/evidence_rules.md`
- `templates/report_template.md`
- `schemas/run_summary_schema.json` + `templates/run_summary_template.json`

## Step 0.5: Alignment Chart First-Pass Identification

Confirm the following before you start writing the report:
1. Read the product list and the focus products from `production_regime_filter.json`
2. List every per-product overlay chart from `plot_manifest.json` and `visual_analysis.json`
3. Check the VLM observations chart by chart
4. Confirm the three-dimension interpretation for every alignment chart: synchronized fluctuating parameters, anomaly windows, ontology judgement
5. If the interpretation of an alignment chart is incomplete → flag `pipeline_warnings`

## Step 0.6: Evidence Completeness Self-Check

Answer these before you put pen to paper:
1. Is the primary conclusion supported by evidence of rank L3 or above?
2. Has temporal precedence been verified (CCF or VLM time alignment)?
3. Has the physical mechanism been verified (ontology + rag_deep_understanding)?
4. Has statistical validation been performed (detrending / Simpson / robustness)?
5. Does every alignment chart have a corresponding VLM observation?
6. In a COMPETING_SET, have all competing hypotheses been retained?

## Step 1: Build the "Conclusion → Evidence → Business Impact" Mapping Table

### 1.0 Visual–Statistical Cross-Validation

Cross-validate every VLM observation in `visual_analysis.json` against the statistical claims in `feature_summary.json` / `diagnosis.json`, one by one:
1. Do the VLM direction and the statistical direction agree?
2. The VLM reports synchrony but the statistical r is very low → `[视觉与统计不一致]` (visual–statistical inconsistency) — must be disclosed
3. The statistical r is very high but the VLM observed nothing → possibly outlier-driven or trend-confounded
4. diagnosis claims visual confirmation but the pair is not in `synchronous_groups` → `[视觉证据过度声称]` (visual-evidence overclaim)
5. Add one sentence at every visual citation stating the visual–statistical alignment status

### 1.1 Evidence Tracing for Every Key Finding

Construct the following form (internal working structure, not report output):
```
Finding ID: F1
├── One-sentence conclusion
├── Data observation (source: feature_summary.json, anomaly_report.json)
├── Alignment-chart fluctuation interpretation (source: visual_analysis.json, plot_manifest)
├── Statistical evidence (source: feature_summary.json, validate_report.json)
├── Physical mechanism (source: ontology.json, rag_deep_understanding.json)
├── Image evidence (source: visual_analysis.json, 03_figures/)
├── Eliminated alternative explanations (source: diagnosis.json, reasoning_chain.json)
├── Confidence assessment (source: confidence.json)
├── Business impact
└── Falsification condition
```

### 1.2 Evidence Tracing When Evidence Is Insufficient

If no clear relationship is visible in the alignment charts, state it plainly, using the literal sentence the report must carry:
"未观察到任何工艺参数与检测指标之间的清晰同步波动模式"
("no clear synchronous fluctuation pattern was observed between any process parameter and any inspection metric.")

## Step 2: Generate the Report — 9-Section Pyramid Structure

The report body is written in Chinese (see the `Language` parameter in `references/agent-protocol.md`). The fenced block below is the literal 9-section skeleton `report.md` must follow, so its section titles are retained verbatim in Chinese; the section order and numbering are fixed. The English equivalents of the nine sections are listed in `references/agent-protocol.md` → Phase 2.

```markdown
# [场景名称] 工业诊断报告

## 1. 执行摘要 (Executive Summary)
- 一句话结论
- 根因判定（置信度 + 证据等级）
- 业务影响量化
- 建议行动（P0/P1/P2优先级）

## 2. 诊断结论
- 主结论 + 置信度分解
- 竞争假设对比表
- 排除逻辑说明

## 3. 证据详解 — 统计验证
- 关键相关性（含去趋势/Simpson/CCF结果）
- 统计陷阱披露（Simpson's Paradox、趋势混淆等）
- 稳健性验证

## 4. 证据详解 — 时间对齐分析
- 每张对齐图的三段式解读
- 视觉-统计交叉验证
- 时序先后判定

## 5. 证据详解 — 物理机制验证
- 因果物理链
- 定量验算
- [PHYSICS_UNVERIFIED] 标注

## 6. 异常窗口深度分析
- 异常区间详情
- 双驱动分析
- 事件前后对比

## 7. 建议行动计划
- P0/P1/P2 分级
- 每项含: 具体操作、预期效果、验证方法、时间/成本

## 8. 不确定性与数据缺口
- 证据缺口清单
- 置信度天花板说明
- 下一步数据采集建议

## 9. 附录
- 方法说明
- 数据质量报告摘要
- 补充图表
```

## Step 3: Generate run_summary.json

Read `schemas/run_summary_schema.json` and `templates/run_summary_template.json`, and generate according to the template.

## Hard Writing Rules

| # | Rule |
|---|------|
| 1 | State the conclusion first, the reasoning second |
| 2 | Every sentence must survive the challenge "on what grounds?" — it must carry a number, a chart, or a source |
| 3 | Every number must carry business meaning |
| 4 | Organize the content on the pyramid principle |
| 5 | Translate complex concepts into plain language |
| 6 | Charts are evidence, not decoration |
| 7 | Reject "AI-speak" and "engineer boilerplate" |
| 8 | Not knowing is itself a mark of professionalism — state data gaps honestly |

## Forbidden Phrasings

The banned forms and their replacements are Chinese report prose, so the report-language examples below are retained verbatim; the English rendering of each is given in italics.

| Forbidden | Instead |
|-----------|---------|
| "基于本次数据分析，我们认为..."<br>*("Based on this data analysis, we believe that…")* | "数据直接显示: Z3温度从82→89°C，同期缺陷密度从3.2→8.7个/m²（+172%）。"<br>*("The data shows directly: Z3 temperature rose from 82 → 89 °C, and over the same period defect density rose from 3.2 → 8.7 per m² (+172%).")* |
| "可能存在一定的关联性"<br>*("There may be a certain correlation")* | "Spearman ρ=0.73, p<0.001。去趋势后降到0.58。"<br>*("Spearman ρ = 0.73, p < 0.001. After detrending it drops to 0.58.")* |
| "综上所述"/"值得注意的是"<br>*("In summary" / "It is worth noting that")* | 直接说结论<br>*(State the conclusion directly)* |
| "强烈建议"/"高度重视"<br>*("We strongly recommend" / "Attach great importance to")* | "P0 行动: 校准Z3温控系统，目标82°C±1.5°C，预计2小时。"<br>*("P0 action: recalibrate the Z3 temperature control system, target 82 °C ± 1.5 °C, estimated 2 hours.")* |
| 归因于"AI分析"或"模型判断"<br>*(Attributing to "AI analysis" or "model judgement")* | 归因于: 测量数据 / 统计检验 / 物理定律计算 / 图像直接观察<br>*(Attribute to: measurement data / statistical tests / physics-law calculation / direct image observation)* |

## Output Template for Insufficient Evidence

When the diagnosis cannot determine a root cause, Section 2 uses the following literal Chinese skeleton:

```markdown
## 2. 诊断结论: 证据不足以确定单一根因
### 2.1 当前可以确定的
### 2.2 当前无法区分的竞争假设
### 2.3 为什么无法确定
### 2.4 建议的下一步
```

*(EN: "2. Diagnostic Conclusion: Evidence Is Insufficient to Determine a Single Root Cause" → 2.1 What Can Be Determined Now / 2.2 Competing Hypotheses That Currently Cannot Be Distinguished / 2.3 Why It Cannot Be Determined / 2.4 Recommended Next Steps)*

## Output Verification

```bash
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/run_summary_schema.json" "$RUN_DIR/run_summary.json"
```
