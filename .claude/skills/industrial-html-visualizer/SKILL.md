---
name: industrial-html-visualizer
description: "工业诊断管线Step 8 — 从诊断产物构建 ECharts+Three.js 讲解式 HTML 可视化页面。复用 diagnostic-html-visualizer skill 的模板、设计系统和 Fallback 规则。结论必须在首屏，图表是证据不是装饰，3D 模型必须讲真话。Trigger: HTML可视化, 生成HTML, 前端页面, 可视化报告, html visualization, diagnostic HTML, 3D scene, ECharts. Do NOT use without CP-8 ENDORSED optimizer.md."
---

# Industrial HTML Visualizer

诊断结果前端可视化构建引擎。复用 `diagnostic-html-visualizer` skill 的 ECharts/Three.js 模板、设计系统、CSS 变量、视觉语法和 Fallback 规则，从诊断产物生成单文件讲解式 HTML 页面。

**硬前提**: CP-8 ENDORSED 审计结论 (`optimizer.md`)。无 optimizer.md → 拒绝执行，向主 agent 报告"缺少 CP-8 ENDORSED 审计结论"。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `optimizer.md` | **CP-8 ENDORSED** 审计结论（硬前提） |
| `report.md` | 诊断报告 |
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `01_ontology/ontology.json` | 领域本体（3D 工段恢复） |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论（数据治理留痕） |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/visual_analysis.json` | VLM 视觉分析 |
| `03_figures/image_captions.json` | 图片标注 |
| `03_figures/*.png` | 现成视觉证据 |
| `3d_model_data.json` | 3D 模型数据（如存在） |

缺少 P0 文件时执行 `skill://diagnostic-html-visualizer` §Fallback Rules 对应分支。

### Outputs

| File | Description |
|------|-------------|
| `diagnostic-report.html` | 单文件 HTML ≥5120B，含 ECharts + Three.js + 数据治理卡片 |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent html-visualizer --step present

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-visualizer --step present \
  --files diagnostic-report.html
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

启动 `html-visualizer` 子Agent（林工 — 工业前端可视化工程师）：

```javascript
Agent({
  subagent_type: "html-visualizer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

## Protocol

1. 首先读取 "skill://diagnostic-html-visualizer" — 加载 ECharts/Three.js 模板、设计系统、Fallback 规则、visual standards
2. 再读取 "$SKILL_PATH/references/agent-protocol.md" — 执行完整 checklist
3. 按 checklist Phase 1-4 顺序执行

## Key requirements
- ECharts for statistical charts (correlation, time series, anomaly overlays)
- Three.js for 3D process flow (recover real stages from ontology, NOT generic factory)
- Runtime readiness: window.echarts, window.THREE, OrbitControls — multi-source CDN with degraded static fallback
- Interactive evidence chain navigation (三层闭合: 统计→物理→排除)
- Chinese language interface
- Data governance card from data_analysis_conclusion.json
- 完成后向主 agent 汇报 11 项输出契约`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `skill://diagnostic-html-visualizer`.

| Phase | Purpose |
|-------|---------|
| 1 — Data Governance | 读取 `data_analysis_conclusion.json` → 渲染数据治理留痕卡片（清洗了什么、影响行数、原因、数据源） |
| 2 — Build Page | Hero 首屏（10 秒内回答结论/位置/原因/动作）→ 核心证据区（3-5 张图，每张回答看到什么/说明什么/为什么重要）→ 3D 场景（从 ontology 恢复真实工段/设备/物料流向）→ Runtime Readiness（多源 CDN + 降级检测） |
| 3 — CP-8 Gate | `html-reviewer` 审校。verdict = `pass` 方可完成；`warn`/`fail` 回退 Phase 2（最多 3 次） |
| 4 — Output Contract | 向主 agent 汇报 11 项：源文件、输出路径、图表/3D 状态、降级模式、3D 建模依据、异常映射、10s/1min/2min 可读性分层、核心证据选择、reviewer 状态、数据治理留痕 |

### Runtime Readiness (mandatory)

页面必须自检并报告：
- `window.echarts` 可用 → 至少一个 chart 成功初始化
- `window.THREE` 可用 → 至少一个 3D scene 初始化（如适用）
- CDN 加载失败 → 降级静态内容 + visible degraded-mode notice
- 至少一个图表渲染成功 → 否则显示 error placeholder

### Output Contract (11 项汇报)

子Agent 完成后必须汇报：
1. 读取了哪些关键源文件
2. 页面输出路径
3. 交互式图表是否初始化成功
4. 3D 模块是否初始化成功
5. 是否进入了降级模式
6. 3D 建模依据了哪些真实工艺文件
7. 异常位置如何映射到具体设备
8. 用户在 10 秒、1 分钟、2 分钟内分别能看懂什么
9. 主内容区的 3-5 个核心证据是什么
10. 页面是否通过 html-reviewer 质检
11. 数据治理卡片是否渲染

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
# CP-9: 文件存在 + 最小尺寸
test -f "$RUN_DIR/diagnostic-report.html" && \
  test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120

# html-reviewer 必须通过
# 读取 .claude/skills/industrial-html-reviewer/references/agent-protocol.md 执行审核
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| 缺少 optimizer.md | 拒绝执行，报告"缺少 CP-8 ENDORSED 审计结论" |
| 缺少 P0 诊断文件 | 执行 `skill://diagnostic-html-visualizer` §Fallback Rules |
| CDN 全部失败 | 降级静态内容 + visible degraded-mode notice，页面仍可用 |
| ECharts 初始化失败 | error placeholder 替代图表区，页面其余部分正常渲染 |
| Three.js 初始化失败 | 跳过 3D 场景，用静态工艺流程图替代 |
| html-reviewer warn/fail | 读取 reviewer feedback → 回退 Phase 2 修复（最多 3 次）→ 重新提交审核 |
| 3 次审核仍未通过 | 报告 pass-with-warnings，在页面标注已知问题 |
| 页面 < 5120B | 检查是否所有关键 section 都已渲染，重新生成 |
