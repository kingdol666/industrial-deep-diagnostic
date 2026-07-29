# Reporter — Detailed Execution Reference

## Step 0: 加载所有证据产物

必须读取（RUN_DIR）:
- `00_input/user_context.json` — 用户场景、已知问题
- `01_ontology/ontology.json` — 参数物理含义、工艺阶段
- `01_ontology/schema.json` — 变量分类schema
- `02_processed/data_quality_report.json` — 数据质量
- `02_processed/feature_summary.json` — 统计特征
- `02_processed/validate_report.json` — 统计验证
- `02_processed/scenario_classification.json` — 场景分类
- `02_processed/anomaly_report.json` — 异常区间、双驱动
- `02_processed/data_analysis_conclusion.json` — Data-processor专家交接
- `02_processed/production_regime_filter.json` — 稳态过滤 (v6.5)
- `02_processed/time_lag_analysis.json` — 时间滞后补偿 (v6.4)
- `03_figures/plot_manifest.json` — 图表清单
- `03_figures/visual_analysis.json` — VLM视觉分析
- `03_figures/image_captions.json` — 图表描述
- `04_diagnostics/diagnosis.json` — 诊断结论
- `04_diagnostics/evidence.json` — 证据清单
- `04_diagnostics/confidence.json` — 置信度分解
- `04_diagnostics/reasoning_chain.json` — 完整推理链
- `05_review/judge_feedback.json` — Judge评分

可选读取:
- `00_input/extracted_knowledge.json` / `rag_deep_understanding.json`
- `02_processed/zone_analysis.json` / `event_analysis.json`
- `02_processed/analysis_plan.md`

从SKILL_PATH读取:
- `resources/evidence_rules.md`
- `templates/report_template.md`
- `schemas/run_summary_schema.json` + `templates/run_summary_template.json`

## Step 0.5: 对齐图优先识别

在开始写报告之前确认:
1. 从 `production_regime_filter.json` 读取产品列表和重点产品
2. 从 `plot_manifest.json` 和 `visual_analysis.json` 列出所有 per-product overlay 图
3. 逐张检查 VLM 观察
4. 确认每张对齐图的三维度解读: 同步波动参数、异常窗口、ontology判断
5. 如果对齐图解读不完整 → 标记 `pipeline_warnings`

## Step 0.6: 证据完整性自检

动笔前回答:
1. 主结论是否有至少 L3 级以上证据支撑？
2. 是否经过了时间先后验证（CCF 或 VLM 时间对齐）？
3. 是否经过了物理机制验证（ontology + rag_deep_understanding）？
4. 是否经过了统计验证（去趋势/Simpson/稳健性）？
5. 每张对齐图是否有对应 VLM 观察？
6. 如果 COMPETING_SET，是否保留了所有竞争假设？

## Step 1: 构建"结论→证据→业务影响"映射表

### 1.0 视觉-统计交叉验证

逐一交叉验证 `visual_analysis.json` VLM观察与 `feature_summary.json`/`diagnosis.json` 统计声称:
1. VLM方向与统计方向是否一致？
2. VLM报告同步但统计r很低 → `[视觉与统计不一致]` — 必须披露
3. 统计r很高但VLM未观察 → 可能 outlier-driven 或 trend-confounded
4. diagnosis声称视觉确认但不在 synchronous_groups → `[视觉证据过度声称]`
5. 每个视觉引用处写一句话说明视觉-统计对齐状态

### 1.1 每个关键发现的证据溯源

构建格式:
```
发现ID: F1
├── 一句话结论
├── 数据观测（来源: feature_summary.json, anomaly_report.json）
├── 对齐图波动解读（来源: visual_analysis.json, plot_manifest）
├── 统计证据（来源: feature_summary.json, validate_report.json）
├── 物理机制（来源: ontology.json, rag_deep_understanding.json）
├── 图像证据（来源: visual_analysis.json, 03_figures/）
├── 排除的替代解释（来源: diagnosis.json, reasoning_chain.json）
├── 信心评估（来源: confidence.json）
├── 业务影响
└── 证伪条件
```

### 1.2 证据不足时的证据溯源

如果对齐图中看不到清晰关系，如实写出"未观察到任何工艺参数与检测指标之间的清晰同步波动模式"。

## Step 2: 生成报告 — 9节金字塔结构

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

## Step 3: 生成 run_summary.json

读取 `schemas/run_summary_schema.json` 和 `templates/run_summary_template.json`，按模板生成。

## 写作铁律

| # | 铁律 |
|---|------|
| 1 | 先说结论，再说理由 |
| 2 | 每句话都能被"凭什么"挑战 — 必须有数字/图表/来源 |
| 3 | 数字必须有业务含义 |
| 4 | 金字塔原理组织内容 |
| 5 | 复杂概念翻译成人话 |
| 6 | 图表是证据，不是装饰 |
| 7 | 拒绝"AI腔"和"工程师八股" |
| 8 | 不知道也是一种专业 — 诚实说明数据缺口 |

## 禁止写法

| 禁止 | 替代做法 |
|------|----------|
| "基于本次数据分析，我们认为..." | "数据直接显示: Z3温度从82→89°C，同期缺陷密度从3.2→8.7个/m²（+172%）。" |
| "可能存在一定的关联性" | "Spearman ρ=0.73, p<0.001。去趋势后降到0.58。" |
| "综上所述"/"值得注意的是" | 直接说结论 |
| "强烈建议"/"高度重视" | "P0 行动: 校准Z3温控系统，目标82°C±1.5°C，预计2小时。" |
| 归因于"AI分析"或"模型判断" | 归因于: 测量数据 / 统计检验 / 物理定律计算 / 图像直接观察 |

## 证据不足时的输出模板

当诊断无法确定根因时，第2节使用:
```markdown
## 2. 诊断结论: 证据不足以确定单一根因
### 2.1 当前可以确定的
### 2.2 当前无法区分的竞争假设
### 2.3 为什么无法确定
### 2.4 建议的下一步
```

## Output Verification

```bash
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/run_summary_schema.json" "$RUN_DIR/run_summary.json"
```
