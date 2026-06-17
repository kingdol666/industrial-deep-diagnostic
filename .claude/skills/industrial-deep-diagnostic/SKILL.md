---
name: industrial-deep-diagnostic
description: "Multi-agent industrial diagnostic engine for manufacturing root cause analysis. Use with sensor/process data (CSV, XLSX, Parquet) and anomalies, quality defects, equipment faults, SPC excursions, or root cause analysis — applies to ANY industrial process. Triggers on: 诊断, 故障分析, 异常检测, 根因分析, 质量缺陷, 过程异常, 设备故障, 传感器数据分析, 工艺参数优化, 生产过程诊断. Pipeline: ontology → statistical validation (Simpson, trend confounding, change-point) → multi-hypothesis physics diagnosis → quality-gate → adversarial physical-truth audit. 3 modes: auto/interactive/minimal. Do NOT trigger for non-industrial data, charting, financial analysis, or statistics homework."
commands:
  - industrial-deep-diagnostic
  - industrial-deep-diagnostic analyze
  - industrial-deep-diagnostic review
  - industrial-deep-diagnostic report
  - industrial-deep-diagnostic audit
compatibility: |
  Requires Node.js 18+ for pipeline orchestration scripts (setup.mjs, inspect.mjs, stats.mjs, stats_validate.mjs, validate.mjs).
  Python 3.9+ managed via uv venv for adaptive analysis (matplotlib, numpy, pandas, scipy, seaborn, openpyxl).
  uv auto-installed if missing. Run `node scripts/uv_env_setup.mjs` before any Python use.
  Optional: rag-retrieval-engine running on localhost:8765 for runtime knowledge retrieval. Falls back to local-only ontology building if unavailable.
---

# Industrial Deep Diagnostic

## TL;DR Quick Reference

```
用户上传数据 → 8 步诊断 → report.md + diagnostic-report.html

输入: CSV/XLSX/Parquet 工业传感器/工艺数据
输出: 中文诊断报告 (report.md) + HTML 可视化讲解页 (diagnostic-report.html)
核心: 本体构建 → 去趋势/分层/Simpson检测 → 竞争假说 → 物理验证 → Judge审查 → HTML可视化

最易出错的 3 个地方:
  1. 全局相关 ≠ 因果 → 必须先做产品内去趋势 + Simpson检测
  2. Agent 执行失败是常态 → 按 Recovery Table 恢复 (10 场景), 不要手动接管
  3. HTML 必须由 html-visualizer 子 Agent 生成 → 禁止主 agent 自己拼 HTML

🔴 红灯动作 (命中任一条 → Judge 直接判 fail):
  - 主 agent 自己写 HTML  /  读子 Agent 协议后自行执行  /  跳过数据分析直接做诊断
  - Judge gate 未通过就启动 Reporter  /  对 COMPETING_SET 强行挑一个当结论
  - 3D 模型画通用工厂  /  结论缺证据等级标注  /  用模糊词逃避判断
```

## Language Default

**默认输出语言为中文。** 报告、诊断结论、审计文档使用中文。JSON enum 字段保持英文。

---

## What This Skill Does

This is a **scenario-adaptive diagnostic engine** — it diagnoses ANY industrial process by combining three knowledge sources:

1. **Data self-describes** — column names, value ranges, and statistical signatures reveal the process type without a fixed taxonomy
2. **RAG provides domain context** — retrieved physics principles, causal mechanisms, known failure modes, and parameter semantics for the data's domain
3. **First-principles physics** — every statistical correlation must trace to a governing equation; unknown parameters derived from conservation laws, dimensional analysis, and constitutive relations

Every diagnosis must support **two complementary views**:

1. **纯工艺波动诊断 / Process-Fluctuation Diagnosis** — from process data alone, identify physically meaningful abnormal drift, instability, threshold behavior, or regime switching
2. **工艺+检测双驱动诊断 / Integrated Dual-Drive Diagnosis** — combine process abnormalities with inspection/quality anomalies to determine whether the process-side abnormality enters the defect causal chain

**Both views must be grounded in ontology semantics and physical reasoning, not just statistics.**

## Core Principle

Diagnosis is elimination, not confirmation. Every conclusion needs: (1) temporal precedence, (2) statistical evidence, (3) physical mechanism, (4) no contradictions. Missing any → label as `[HYPOTHESIS]`. When data cannot discriminate between competing hypotheses → `COMPETING_SET`, not a guess.

| Pillar | Principle | Anti-Pattern |
|--------|-----------|--------------|
| Scenario-Adaptive | Analysis flows from data characteristics — no hardcoded process types | Applying a "CNC template" to non-CNC data |
| RAG Deep Understanding | RAG knowledge is semantically comprehended, not mechanically mapped | Field-by-field copy from RAG output to ontology |
| Data↔Ontology Bidirectional | Ontology predicts → data confirms; data reveals → ontology explains; discrepancies are diagnostic signals | Building ontology and analyzing data independently |
| Physics-Based Inference | Every correlation must trace to governing equations; derive from first principles when needed | "Parameter X correlates with quality, therefore X is the cause" |

---

## Truth-Seeking Mandate — 实事求是（最高优先级）

**这是整个 Skill 执行的最基本、最优先的约束。所有 Agent 必须遵守，任何输出不能与此冲突。**

### 三条铁律

**铁律 1: 只讲数据真话，不讲假结论。**

- 如果证据不足以确定根因，必须明确说"现有数据无法确定"，并呈现竞争假设
- 如果统计相关性存在但物理机制不清，必须标注 `[PHYSICS_UNVERIFIED]`
- 如果物理机制合理但统计上不显著，必须标注 `[STATISTICALLY_UNVERIFIED]`
- 不得为了"给出一个答案"而选择性地忽略反面证据
- 不得用"可能"、"或许"、"大概"等模糊词掩盖证据不足
- **结论必须归因于具体的数据来源**：`[OBSERVED: feature_summary.json §X]`、`[MEASURED: row 847, col Z3_temp]`、`[VLM_OBSERVED: fig_vlm_temporal_overlay_focus_PG31DS.png]`

**铁律 2: 对齐图是诊断的核心证据，不是装饰。**

- 每个产品的 per-product time-aligned overlay 图必须嵌入报告
- 每张对齐图必须配有一段独立的波动解读：哪些参数同步、哪些先变后变、哪些异常窗口
- 对齐图的解读必须直接回答："哪个工艺参数的波动导致检测数据异常？"
- 如果对齐图中看不出任何关联，必须明确写"该产品数据中未观察到工艺参数与检测指标的清晰时间对齐模式"
- 对齐图的解读必须结合 ontology 中的物理含义（"为什么这个参数可能会影响这个检测指标"）
- 对齐图不能只是"贴图"——每张图要有"图上看到了什么 → 统计怎么说 → 物理上说得通吗"三段式解读

**铁律 3: 推理链必须透明可追溯。**

- 每个结论必须能从 `reasoning_chain.json` 中追溯完整的 R1→R8 推理路径
- 每个证据引用必须标明证据等级（L1-L7）和来源文件
- 如果推理链中存在"跳跃"（从统计相关直接跳到因果结论），必须标注 `[INFERENCE_GAP]`
- 证伪条件必须具体、可执行——不能说"需要更多数据"，要说"需要下一批次在 Z3 温度 82°C 条件下的缺陷密度数据"

### 证据不足时的标准输出

当无法确定根因时，以下是**应当输出的内容**，而非编造结论：

```markdown
## 诊断结论: 证据不足以确定单一根因

### 当前可以确定的
- [列出有统计+物理双重支持的发现]

### 当前无法区分的竞争假设
| 假设 | 支持的证据 | 反对的证据 | 需要什么才能区分 |
|------|----------|-----------|----------------|
| H1: ... | ... | ... | ... |
| H2: ... | ... | ... | ... |

### 为什么无法确定
[诚实说明: 数据缺失/物理机制不清/统计不显著/时间对齐不可靠]

### 建议的下一步
[具体、可操作的后续诊断步骤]
```

### 禁止的虚假表述清单

以下表述在任何 Agent 的输出中均被禁止：

| 禁止表述 | 原因 | 替代做法 |
|---------|------|---------|
| "可以确定X是根因"（当置信度<70或证据等级<L3时） | 过度声称 | "X是最可能的根因，置信度XX/100，最大不确定性是..." |
| "经全面分析..." | 无法验证是否"全面" | 列出具体分析步骤和覆盖范围 |
| "数据显示明显相关"（不给出具体r值和p值） | 模糊不可验证 | "Spearman ρ=0.73, p<0.001" |
| "物理机制支持这一结论"（不给出具体机制） | 空洞 | "Z3温度↑ → PET结晶速率↑（Arrhenius方程，Ea≈150kJ/mol）→ 薄膜雾度↑" |
| "建议优化工艺参数"（不给出具体参数和目标值） | 无法执行 | "将Z3温度从89°C调回82°C±1.5°C" |
| "可能存在一定影响" | 逃避判断 | 给出具体数字或明确说"无法判断" |
| 把统计相关直接等同因果 | 逻辑跳跃 | 必须经过物理机制和时间先后验证 |

### 🔴 红灯动作黑名单（任何 Agent 不准做的事）

以下动作在任何 Pipeline Step 均被禁止。命中任一条 → Judge 可直接判 `fail`。

| # | 🚫 禁止动作 | 为什么禁止 | 允许的替代动作 |
|---|-----------|----------|-------------|
| 1 | **主 agent 直接编写 HTML 页面** | 违反 Agent 分工纪律；页面质量无保证；无法通过 html-reviewer 审计 | 启动 `html-visualizer` 子 Agent (Step 8)；启动 `html-reviewer` 审校 (Step 8.5) |
| 2 | **主 agent 读取子 Agent 协议后自行执行** | 违反管线纪律；主 agent 上下文会被 500+ 行协议撑爆；输出质量远低于专用 Agent | 使用 `Agent({subagent_type: "xxx"})` 启动子 Agent，只传参数不执行 |
| 3 | **跳过数据分析直接做诊断** | 缺失统计验证会导致假相关伪装成因果 | Step 3 data-processor → Step 4 diagnostician（严格执行 ontology_first） |
| 4 | **Judge gate 未通过就启动 Reporter** | 质量未经验证的诊断进入报告，结论可能有根本性错误 | 检查 `judge_feedback.json` verdict==pass + score≥90 + 无 blocking issues |
| 5 | **对 COMPETING_SET 强行挑一个当结论** | 数据无法区分竞争假说时挑一个 = 制造假结论 | 诚实输出竞争假说表，标记 `COMPETING_SET`，confidence ceiling≤65 |
| 6 | **全局相关系数直接当做因果证据** | Simpson 悖论会逆转产品内相关方向；趋势混淆会产生虚假高相关 | 必须做 per-product 分层 + 去趋势后相关 + Simpson 检测 |
| 7 | **HTML 页面只挂 CDN script 标签不做初始化检测** | 远程脚本加载失败时页面白屏，用户看到空白页 | 多源加载 + runtime 检测 + 失败降级静态内容 + 显式状态面板 |
| 8 | **3D 模型画通用工厂/抽象流水线** | 与当前诊断场景无关的 3D = 装饰垃圾，误导用户 | 从 ontology + report + diagnosis 恢复真实工段 → 按工艺顺序建模 → 异常点精确落位 |
| 9 | **结论缺少证据等级标注** | 用户无法判断结论可信度 | 每个结论必须标注 `[Evidence Rank L1-L7]`，受最低证据等级约束 |
| 10 | **用模糊词逃避判断**（"可能""或许""大概""有一定影响"） | 给用户虚假安全感；实则未做判断 | 给出具体数字 + 置信度；或明确说"当前证据无法判断" |

---

## Loading Guide — Progressive Disclosure

This skill uses **three levels**. Only load what the current step needs.

### Level 1: Always Loaded (this file)

The orchestration protocol — step sequence, agent launch templates, governance rules, evidence/anti-speculation checks.

For production-style execution, also treat `resources/engineering_delivery_contract.md` as binding acceptance criteria.

### Level 2: Launched Per Step (8 sub-agents)

> **禁止主 agent 执行子智能体工作！** 表格中的 **Launch sub-agent** 行意味着直接启动子智能体 — **不是**主 agent 读协议自己干。子智能体自行 Read 自己的协议并执行，主 agent 只负责传参和等待。

| Step | Agent (Persona) | Subagent Type | Action | Why |
|:----:|----------------|:-------------:|--------|-----|
| 2 | **王教授** — 化工/材料专家，25年失效分析经验 | `context-builder` | **Launch sub-agent** | RAG检索 + 本体ontology构建（物理语义深度理解） |
| 3 | **张工** — 高级过程数据科学家，16年流程制造分析 | `data-processor` | **Launch sub-agent** | 统计分析 + 可视化（内部委托 vlm-visual-analyzer） |
| 3.5 | **老孙（目视）** — 设备状态监测工程师，20年目视巡检经验 | `vlm-visual-analyzer` | data-processor 内部启动 | 本体感知的VLM视觉图像分析 |
| 4 | **刘总工** — 首席根因分析工程师，28年产线诊断经验 | `diagnostician` | **Launch sub-agent** | 物理约束的竞争假说根因诊断 |
| 5a | **陈主任** — 国家工业产品质检中心高级审核员，15年质量审计 | `judge` | **Launch sub-agent** | 10项标准质量门审查 |
| 5b | **孙审计** — 过程安全与质量审计专家，32年跨国工业审计 | `report-reviewer` | **Launch sub-agent** (PRE_REPORT_AUDIT=true) | 预报告物理审计（与Judge并行） |
| 6 | **周工** — 技术报告撰写专家，15年产线技术报告经验 | `reporter` | **Launch sub-agent** | 9节金字塔结构诊断报告（结论优先、白话解释） |
| 7 | **孙审计** — 同上 | `report-reviewer` | **Launch sub-agent** | 独立物理真实审计 |
| 8 | **林工** — 工业前端可视化工程师，14年HMI/SCADA+工业Web | `html-visualizer` | **Launch sub-agent** | 生成讲解式 HTML 可视化页面（ECharts + Three.js + 证据链） |
| 8.5 | **赵审阅** — 工业信息可视化审校，15年技术文档审校经验 | `html-reviewer` | **Launch sub-agent** | 审核 HTML 是否清楚、完整、能支撑结论 |

> **vlm-visual-analyzer** 是 data-processor 的内部子智能体 — 不是独立的管线步骤。**Step 5a (judge) 和 Step 5b (pre-audit) 是唯一可并行的步骤。**

### Level 3: Loaded On-Demand (resources/)

Detailed frameworks — load only when an agent's instructions tell you to.

| When | Read | Content |
|------|------|---------|
| context-builder needs RAG deep understanding protocol | `resources/rag_deep_understanding_protocol.md` | R1-R4: semantic comprehension, knowledge-data alignment, physics extraction, gap identification |
| context-builder builds ontology; data-processor updates it | `resources/data_ontology_mapping_framework.md` | Three mapping directions: prediction→validation, discovery→refinement, discrepancy→diagnostic signal |
| data-processor needs scenario-specific analysis patterns | `resources/scenario_patterns.md` | Patterns A-I: multi-zone, paired sensors, grouping, events, nonlinear, cyclic, manual physics, process-only, regime detection |
| data-processor needs VLM chart design principles | `resources/visual_analysis_framework.md` | Chart design principles + Phase 5.5 visual analysis protocol |
| diagnostician encounters novel parameters | `resources/physics_inference_framework.md` | L1-L5 ladder: physical quantity → governing law → causal chain → magnitude → competing mechanisms |
| diagnostician needs evidence definitions | `resources/evidence_rules.md` | 7-rank evidence hierarchy and 5-condition causation criteria |
| diagnostician needs methodology | `resources/diagnosis_method.md` | 6-stage diagnostic methodology with statistical thresholds |
| diagnostician reads pre-computed checks | `resources/diagnostician_dual_drive_reference.md` | Quality reset analysis, onset-coincidence classification, physical check conclusions |
| any agent needs physics pattern examples | `resources/parameter_to_physics.json` | Pattern library — structural examples, NOT a lookup table |
| report-reviewer needs cross-industry physics | `resources/process_knowledge_base.md` | 16 universal physics principles, quantitative relationships, degradation patterns |
| troubleshooting pipeline integration | `resources/pipeline_coherence_and_synergy.md` | Step synergy rules, cross-step verification, RAG two-stage protocol |
| developer reference | `resources/script_and_toolkit_reference.md` | Complete catalog of scripts, schemas, and templates |
| engineering delivery contract | `resources/engineering_delivery_contract.md` | Mandatory execution, artifact, and completion contract for deployable runs |

**After each agent produces output**, validate with the matching schema. See `pipeline-execution.md` §Step Command Reference for full validation commands.

**Do NOT load everything upfront.** Detailed frameworks (Level 3) are only needed when an agent explicitly references them. Agents (Level 2) are self-contained.

---

## Execution Flow

```
Step 0: Setup ──► Step 1: Inspect
                         │
                         ▼
                    Step 2: context-builder (RAG + Ontology + Deep Mapping)
                         │
                         ▼
                    Step 2.5: Clarify
                         │
                         ▼
                    Step 3: data-processor (Ontology-Guided Analysis)
                         │
                         ▼
                    Step 4: diagnostician (Physics-Based Competing Hypotheses)
                         │
              ┌──────────▼──────────┐
              │ Step 5a: judge       │◄── repair max 3 ─┐
              │ Step 5b: pre-audit   │                   │
              │ run in parallel      │                   │
              └──────────┬──────────┘                   │
                         │ pass                         │
                         ▼                              │
                   Step 6: reporter                     │
                         │                              │
                         ▼                              │
                   ┌─────▼──────┐                       │
                   │ Step 7:    │── re-diagnose ────────┘
                   │ report-reviewer
                   └─────┬──────┘
                         │ ENDORSED
                         ▼
                   Step 8: html-visualizer
                         │
                         ▼
                   Step 8.5: html-reviewer
                         │ PASS
                         ▼
                   Step 9: Finalize
```

### Default Post-Audit HTML Visualization

当诊断流程完成到 Step 7 且 `report-reviewer` 给出 `ENDORSED` 后，主诊断 skill 默认继续执行 HTML 可视化构建，除非用户明确要求跳过前端产出。**这一步必须通过专用子 Agent `html-visualizer` 实现，不允许主诊断 agent 在主上下文中直接拼页面。**

推荐调用形式：

```javascript
// Step 8: HTML 可视化构建
Agent({
  subagent_type: "html-visualizer",
  description: "Step 8: 生成诊断结果的前端 HTML 可视化讲解页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

Read "${SKILL_PATH}/agents/html-visualizer.md" and execute the complete protocol.`,
  run_in_background: true
})
```

`html-visualizer` 完成后，再启动 `html-reviewer` 审校页面：

```javascript
// Step 8.5: HTML 页面审校
Agent({
  subagent_type: "html-reviewer",
  description: "Step 8.5: 审核 HTML 可视化页面是否清楚、完整、能支撑结论",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed

Read "${SKILL_PATH}/agents/html-reviewer.md" and execute the complete review protocol.`,
  run_in_background: true
})
```

只有当 `diagnostic-report.html` 生成完成，且 `html-reviewer` 给出 `pass`，且页面内对 ECharts / Three.js / OrbitControls 的加载状态与初始化状态有明确自检与降级说明时，Step 8 才算完整。

**Default execution mode: `ontology_first`.** Step 2 completes before Step 3's Phase 0.4 — the ontology model tells you which parameter groups are physically meaningful, which pairs to test, and which to prune before statistics wastes degrees of freedom on meaningless pairs.

### 🛑 Formal Checkpoints

以下检查点是诊断管线的强制暂停点。在到达每个检查点时，必须显式验证条件满足后才能继续。

| 🛑 Checkpoint | 位置 | 验证命令 | 不满足时 |
|:------------|------|---------|---------|
| **CP-1: Data Readiness** | Step 1→2 | `test -f "$RUN_DIR/00_input/input_manifest.json" && test -f "$RUN_DIR/00_input/user_context.json" && test -f "$RUN_DIR/00_input/run_config.json"` | 回 Step 0 补全 |
| **CP-2: Ontology Gate** | Step 2→2.5 | `node "$SKILL_PATH/scripts/validate.mjs" "$RUN_DIR/01_ontology/ontology.json" "$SKILL_PATH/schemas/ontology_schema.json" && test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024` | 重新启动 context-builder Agent |
| **CP-3: Clarification Gate** | Step 2.5→3 | `grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' "$RUN_DIR/01_ontology/clarification_needed.json"` | 如有 unresolved→按 interaction_mode 处理 (auto=自行推断, interactive=向用户提问) |
| **CP-4: Data Processor Handoff** | Step 3→4 | `test -f "$RUN_DIR/02_processed/data_analysis_conclusion.json" && node -e "JSON.parse(require('fs').readFileSync('$RUN_DIR/03_figures/plot_manifest.json','utf8')); var p=JSON.parse(require('fs').readFileSync('$RUN_DIR/03_figures/plot_manifest.json','utf8')); process.exit(p.plots&&p.plots.length>0?0:1)"` | 重新启动 data-processor Agent |
| **CP-5: Diagnostician Quality** | Step 4→5 | `for f in diagnosis evidence confidence reasoning_chain; do node "$SKILL_PATH/scripts/validate.mjs" "$RUN_DIR/04_diagnostics/${f}.json" "$SKILL_PATH/schemas/${f}_schema.json" || exit 1; done && node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"` | 修复诊断产物 |
| **CP-6: Dual Gate** | Step 5→6 | `node -e "var j=require('$RUN_DIR/05_review/judge_feedback.json'); process.exit(j.verdict==='pass'&&j.overall_score>=90?0:1)" && grep -qv 'FATAL' "$RUN_DIR/05_review/optimizer_preflight.md"` | 启动修复循环 |
| **CP-7: Report Gate** | Step 6→7 | `test -f "$RUN_DIR/report.md" && test -f "$RUN_DIR/run_summary.json"` | 重新启动 reporter Agent |
| **CP-8: Audit Gate** | Step 7→8 | `test -f "$RUN_DIR/optimizer.md" && grep -qE 'ENDORSED|CONDITIONAL' "$RUN_DIR/optimizer.md"` | CONDITIONAL→评估是否可继续; REJECTED→修复循环 |
| **CP-9: HTML Delivery** | Step 8.5 | `test -f "$RUN_DIR/diagnostic-report.html" && test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120 && test -f "$RUN_DIR/05_review/html_review.json" && grep -q '"verdict" *: *"pass"' "$RUN_DIR/05_review/html_review.json"` | 回到 html-visualizer 修订 |

---

## Pipeline Governance

These rules ensure every run produces trustworthy, auditable diagnoses. Full implementation details in `pipeline-execution.md`.

### Execution Discipline

- Execute steps in order. Never skip, reorder, or silently omit a step.
- If a step does not apply, record `not_applicable_reason` in the relevant artifact — never silently bypass.
- **`ontology_first` mode**: Step 2 completes before Step 3's Phase 0.4 runs. Pre-ontology work is limited to data conversion, preprocessing, and quality profiling.
- Steps 5a (judge) and 5b (pre-audit) are the only parallel steps — both consume the same diagnosis artifacts. All other steps are serial.
- 在 Step 7 获得 `ENDORSED` 后，默认进入 HTML 可视化构建（Step 8 + Step 8.5 html-reviewer）；只有用户明确 opt-out 时才允许跳过。
- HTML 构建必须由专用子 Agent `html-visualizer` 完成，审核必须由 `html-reviewer` 完成，主 agent 不得在主上下文中直接实现或自审页面。

### Repair Loops

- Judge → Diagnostician: max 3 iterations. Reviewer → Diagnostician (full D→J→R→R cycle): max 2 cycles.
- **Global cap: total re-diagnosis ≤ 5.** Counter persists in `.pipeline_events.jsonl` via `repair_spawn` events.
- See `pipeline-execution.md` §Repair Loop Protocol for full procedures.

### 🛑 Agent Runtime Failure Recovery

Agent execution 失败不是异常——是管线运行中的常态。每次启动子 Agent 后必须对以下场景做显式恢复：

| 触发条件 | 检测方式 | 恢复动作 |
|---------|---------|---------|
| RAG 引擎不可用 (localhost:8765 无响应) | `curl -s http://localhost:8765/docs` 失败或 Step 2 context-builder 报告 `RAG_UNAVAILABLE` | 继续执行——context-builder 使用 `resources/parameter_to_physics.json` + 网络搜索作为知识源。ontology.json 仍然可以构建完整，只是缺少特定产线的检索知识 |
| uv Python venv 创建失败 | `uv_env_setup.mjs` 返回非零退出码或 venv 目录不存在 | 检查系统是否已安装 uv (`which uv`)。若无→安装 uv (`curl -LsSf https://astral.sh/uv/install.sh \| sh`)。若已安装 uv 但失败→降级使用系统 Python 并 pip install requirements.txt |
| 输入数据超大 (>500MB CSV/XLSX) | `inspect.mjs` 超时 > 300s 或系统内存不足 | 运行 `file_inspect.py` 做采样解析: `python scripts/file_inspect.py --sample 50000 <data_path>`。对超大文件只读取前 5 万行 + 均匀采样 5 万行做特征分析。内存不足时加 `--low-memory` 标识 |
| Agent 超时 (stall > 600s) | 系统返回 `Agent stalled` 通知 | 检查产物文件是否部分生成。若有可用输出→继续下一步。若无任何输出→等待 60s 后重试 1 次；仍失败→标记 `[AGENT_TIMEOUT]` 并跳过该步骤 |
| API 连接断开 (`socket connection closed`) | 系统返回 `API Error` 通知 | 等待 30s 后重启同一 Agent，传递相同的 prompt。连续 2 次失败→标记 `[API_ERROR]` 并降级到本地脚本执行 |
| 产物文件缺失 | 每步完成后检查 Step 表格中的 expected outputs | 若 ontology.json 缺失→主 agent 用 `resources/parameter_to_physics.json` 构建最小有效本体。若 diagnosis.json 缺失→标记 `[DIAGNOSIS_FAILED]` 并写入失败报告 |
| Schema 验证失败 | 运行 `validate.mjs` 返回错误 | 将 schema 错误列表追加到 Agent 提示词中，重新启动 1 次。仍失败→标记 `[SCHEMA_FAIL]` 并记录到 `.pipeline_events.jsonl` |
| 图片生成失败 (PNG 缺失) | plot_manifest.json 中 plots 数组为空或不存在 | 运行 `generate_captions.mjs` 生成 `image_captions.json` 作为回退。诊断可继续，但 VLM 视觉证据降为 L3+ |
| HTML 可视化失败 | `diagnostic-report.html` 不存在或 html-reviewer 未通过 | 运行 `diagnostic-html-visualizer` skill 重新生成。连续 2 次失败→降级到主 agent 生成简化版报告页面 |
| uv venv 中 Python 模块导入失败 (`ModuleNotFoundError`) | data-processor 报告 Python 脚本执行错误 | 运行 `node "$SKILL_PATH/scripts/uv_env_setup.mjs"` 重建 venv。仍失败→检查 `pyproject.toml` 依赖声明是否完整，缺失依赖追加后重装 |

### Anti-Oscillation Rule

Before re-spawning the diagnostician, compute the repair delta:

1. Compare repair instructions against the previous round: if substantively identical (>70% issue-type overlap in `.pipeline_events.jsonl`) → repair oscillation.
2. On second oscillation (third repair with same issues): **halt repairs**, mark `COMPETING_SET — repair oscillation`, confidence ceiling ≤ 50. Document in `reasoning_chain.json` R8.

### Quality Gates

All must pass for a run to be considered complete:

| Gate | Requirement | Enforced By |
|------|-------------|-------------|
| **Judge Gate** | `verdict == "pass"`, `overall_score >= 90`, no blocking issues | `reporter` launch blocked; `artifact-check.mjs` |
| **Execution Proof** | `.pipeline_events.jsonl` valid per `pipeline-log-check.mjs` | `artifact-check.mjs` |
| **Evidence Closure** | Process + dual-drive + ontology interpretation all present | `evidence-closure-check.mjs` |
| **Engineering Acceptance** | All mandatory artifacts + `run_completed` event | `artifact-check.mjs` per `engineering_delivery_contract.md` |
| **Optimizer Completeness** | `optimizer.md` with all 4 standard sections | `artifact-check.mjs` |
| **HTML Delivery** | `diagnostic-report.html` present + `html-reviewer` passed | `artifact-check.mjs` |

**Judge-gated reporting rule**: Reporter launch is illegal unless `judge_feedback.json` is schema-valid, `verdict == "pass"`, `overall_score >= 90`, and there are no blocking issues. If `append-pipeline-event.mjs` returns `JUDGE_GATE_NOT_PASSED` at `agent_start reporter`, the only valid next action is repair/rejudge — not manual report writing.

### Stability & Reproducibility

Final diagnosis must derive from deterministic artifacts (`data_analysis_conclusion.json`, `diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json`). Unexplained primary-finding drift or confidence shifts >10 points between repeated runs is a Judge blocking issue. Confidence must be reproducible from `confidence.adjustment_log`, evidence ranks, and documented ceilings.

### 🛑 Path Stability Rules (跨环境安全)

路径不一致是管线失败的最常见根因。以下规则必须在每一步强制执行：

| 规则 | 说明 |
|------|------|
| **绝对路径强制** | 所有传给子 Agent 的路径变量 (`SKILL_PATH`, `RUN_DIR`, `DATA_PATH`, `OUTPUT_HTML`) 必须使用绝对路径，不得使用 `./` 或 `~/` 相对路径 |
| **Worktree 安全** | 子 Agent 启动在 worktree 中时，`SKILL_PATH` 必须指向**主仓库的 skill 目录**而非 worktree 的副本 — worktree 可能不含 `.claude/skills/` 子目录 |
| **空格安全** | 所有路径变量在 bash 中使用时必须加双引号: `"$SKILL_PATH/scripts/..."` |
| **Python 路径锁定** | 所有 Python 脚本通过 `"$PYTHON_BIN"` 执行（Step 0 锁定），不允许裸 `python3` 调用 |
| **产物路径一致性** | 子 Agent 的 `RUN_DIR` 必须与主管线创建的 `RUN_DIR` 完全一致 — 用 `RUN_DIR` 而非硬编码路径读写产物 |

---

## Step-by-Step Protocol

### Step 0: Setup (Main Agent)

**路径解析规则（跨平台安全）**：所有路径变量必须使用**绝对路径**。若在 git worktree 中运行，`SKILL_PATH` 必须指向主仓库的 skill 目录而非 worktree 符号链接。

```bash
# 1. Resolve SKILL_PATH to absolute (cross-platform safe)
SKILL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # 或用已知绝对路径

# 2. Resolve project root
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"

# 3. Validate paths exist
if [ ! -f "$SKILL_PATH/scripts/setup.mjs" ]; then
  echo "❌ setup.mjs not found at SKILL_PATH=$SKILL_PATH" >&2
  echo "Verify SKILL_PATH points to the .claude/skills/industrial-deep-diagnostic/ directory"
  exit 1
fi

# 4. Create run directory
RUN_DIR=$(node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs" 2>&1 || echo "")
if [ -z "$RUN_DIR" ] || [ ! -d "$RUN_DIR" ]; then
  echo "❌ setup.mjs failed to create run directory" >&2
  exit 1
fi
echo "✅ Run directory: $RUN_DIR"

# 5. Setup Python venv
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
PYTHON_BIN="$SKILL_PATH/scripts/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
  echo "⚠️ Python venv not found — falling back to system python3" >&2
  PYTHON_BIN="python3"
fi
echo "✅ Python: $PYTHON_BIN"
```

Copy input data files into `00_input/`. Update `00_input/run_config.json` with `data_path` (absolute path), user objective, and constraints. Store `SKILL_PATH`, `RUN_DIR`, and `PYTHON_BIN` as session variables — every subsequent step references them. **All Python invocations MUST use `"$PYTHON_BIN"`, never bare `python3`.**

### Step 1: Inspect Data (Main Agent)

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

| Mode | Behavior |
|------|----------|
| **auto** | Zero user questions. Infer everything from column patterns and value ranges. |
| **interactive** | Ask up to 5 clarification questions. |
| **minimal** | Ask 1-2 essential questions only. |

Produce process-agnostic characterization: column patterns → physical quantity hypotheses, value range confirmation, statistical signature classification (trending/cyclic/step-change/stationary), categorical columns for stratification, time column detection.

Save `input_manifest.json` and `user_context.json` to `00_input/`.

### Step 2: Context Build (Sub-Agent: `context-builder`)

Launch the sub-agent. Do NOT read its full protocol in the main agent.

```javascript
Agent({
  subagent_type: "context-builder",
  description: "Step 2: 构建领域本体 — RAG检索+网络搜索+本体构建",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
REFERENCE_DIR=${REFERENCE_DIR}
PROCESS_DESCRIPTION=${PROCESS_DESCRIPTION}
USER_OBJECTIVE=${USER_OBJECTIVE}
SKILL_PATH=${SKILL_PATH}
INTERACTION_MODE=auto

Read "$SKILL_PATH/agents/context-builder.md" and execute the complete protocol. Validate ontology_schema before completion.`,
  run_in_background: true
})
```

**Completion Verification Checklist (🛑 CP-2)**:
- [ ] `01_ontology/ontology.json` ≥ 1KB
- [ ] `01_ontology/ontology.json` passes schema validation: `node "$SKILL_PATH/scripts/validate.mjs" "$RUN_DIR/01_ontology/ontology.json" "$SKILL_PATH/schemas/ontology_schema.json"`
- [ ] `00_input/rag_deep_understanding.json` exists
- [ ] `00_input/extracted_knowledge.json` exists
- [ ] If any missing → re-launch context-builder Agent (not main agent manual build)

**Outputs**: `01_ontology/ontology.json`, `schema.json`, `00_input/extracted_knowledge.json`, `rag_deep_understanding.json`, `clarification_needed.json`

### Step 2.5: Clarification Gate (Main Agent)

Check `clarification_needed.json`. Behavior depends on `interaction_mode` (defaults to `auto`):

- **auto**: Infer all unknown parameters using `resources/physics_inference_framework.md` L1-L5. Mark `"auto_inferred": true`. Do NOT ask the user.
- **interactive**: Group related parameters, ask up to 4 questions per round with best-guess suggestions.
- **minimal**: Ask only CRITICAL parameters (max 2). Auto-infer the rest.

See `pipeline-execution.md` §Step 2.5 for full protocol including skip conditions and event logging.

### Step 3: Data Processing + Visualization (Sub-Agent: `data-processor`)

Launch `data-processor` **after** `01_ontology/ontology.json` exists. Tell it to read `agents/data-processor.md`, execute Phase 0-6, use only the uv-managed Python path, and delegate Phase 5.5 to `vlm-visual-analyzer`.

Key orchestration constraints to communicate:
- **Phase 0.4 gates all analysis** — read ontology before any statistical work
- **v6.5: Production regime detection runs BEFORE stats** — auto-detect startup/shutdown/steady states via three-algorithm fusion; filter to steady-state only
- **v6.4: Time-lag compensation runs after feature_summary** — CCF-based optimal lag per parameter pair; raw zero-lag correlations are systematically biased when process→quality has a physical delay
- **v6.5: Per-product mandatory analysis** — when multi-product data: identify worst product by anomaly rate, isolate steady-state rows, compare within-product vs cross-product correlations (Simpson's Paradox is the #1 threat)

**Before Step 4**, stabilize outputs:
```bash
node "$SKILL_PATH/scripts/normalize-anomaly-report.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/synthesize-data-analysis-conclusion.mjs" "$RUN_DIR"
```

**Key outputs**: `02_processed/` validated artifacts (including `production_regime_filter.json`, `time_lag_analysis.json`, `data_analysis_conclusion.json`), `03_figures/*.png` + `plot_manifest.json` + `visual_analysis.json`, `analysis_plan.md`

### Step 3.5: VLM Visual Analysis (Embedded in Step 3)

`data-processor`'s Phase 5.5 delegates VLM image reading to `vlm-visual-analyzer` internally. No separate main-agent call needed. Outputs: `03_figures/visual_analysis.json`, `03_figures/image_captions.json`.

If a valid time column exists, Step 3 is only complete when `plot_manifest.json` contains at least one temporal/aligned/process-health figure. If no valid time column exists, record the reason in `analysis_plan.md` and `data_analysis_conclusion.json`.

### Step 4: Diagnostician (Sub-Agent: `diagnostician`)

Launch `diagnostician` with `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`, and optional `REPAIR_INSTRUCTIONS`. Tell it to read `agents/diagnostician.md`, execute Phase 0-7, and fuse data + ontology + physics + VLM evidence + time-lag analysis.

The diagnostician MUST read `02_processed/time_lag_analysis.json` before forming causal hypotheses. Every surviving hypothesis must include `ontology_data_physics_proof`, `physical_logic_chain`, and `falsification_conditions`.

**Outputs**: `04_diagnostics/diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json`

Validate all four against their schemas + run `diagnostic-quality-check.mjs`. See `pipeline-execution.md` §Step Command Reference for full validation commands.

### Step 5: Judge Review (Sub-Agent: `judge`)

Launch `judge` with `RUN_DIR`, `SKILL_PATH`, and `DATA_PATH`. Tell it to read `agents/judge.md`, run the full quality gate, use lowercase schema enum values only.

| Verdict | Score | Action |
|---------|:-----:|--------|
| `pass` | ≥90, no blocking issues | Proceed to Step 6 |
| `needs_repair` | 70-89 | Re-spawn diagnostician (within caps) |
| `major_issues` | 50-69 | Re-spawn diagnostician (within caps) |
| `fail` | <50 | Halt — present as blocked run |

**Hard pass invariant**: `verdict="pass"` is valid only when ALL of these are true: `overall_score >= 90`, `blocking_issues.length == 0`, `reasoning_chain_audit.blocking_issues.length == 0`, `criteria_scores.no_over_claiming.blocking_issues == 0`.

After schema validation, also run `judge-gate-check.mjs`. If it fails, repair Step 4. **Output**: `05_review/judge_feedback.json`

### Step 5b: Pre-Report Physical Audit (Parallel with Judge)

Launch `report-reviewer` with `PRE_REPORT_AUDIT=true` in parallel with Step 5. Must not require `report.md`; writes `05_review/optimizer_preflight.md`. Before Step 6, require both the Judge gate and no blocking physical issues in `optimizer_preflight.md`.

### Step 6: Report Generation (Sub-Agent: `reporter`)

Launch `reporter` with `RUN_DIR` and `SKILL_PATH`. Tell it to read `agents/reporter.md`, use `visual_analysis.json` as primary figure evidence, and generate `report.md` plus schema-valid `run_summary.json`.

Reporter launch is illegal unless the Judge gate has already passed. **Output**: `report.md` (9 节面向决策者的诊断报告 — 金字塔结构: 执行摘要→对齐图核心证据→诊断结论→证据全景→详细推导→推理过程→数据统计→行动方案→局限性), `run_summary.json`

### Step 7: Physical Truth Audit (Sub-Agent: `report-reviewer`)

Launch `report-reviewer` with `RUN_DIR`, `SKILL_PATH`, and `DATA_PATH`. Tell it to read `agents/report-reviewer.md`, verify physics/statistics against raw artifacts, reuse `optimizer_preflight.md` if present, and write `optimizer.md`.

`optimizer.md` must include: scene-specific optimization plan, current problems and opportunities, next-step diagnostic confirmation plan, and action classification (immediate containment / low-risk optimization / controlled experiment / measurement improvement / deferred or unsafe).

| Verdict | Action |
|---------|--------|
| ENDORSED | Proceed to Step 8 |
| CONDITIONAL / REJECTED | Re-spawn diagnostician (max 2 cycles, global cap ≤ 5) |

### Step 8: Present Results (Main Agent)

```bash
node "$SKILL_PATH/scripts/finalize-run-artifacts.mjs" "$RUN_DIR" "$SKILL_PATH"
node "$SKILL_PATH/scripts/artifact-check.mjs" "$RUN_DIR" "$SKILL_PATH"
```

If either reports `JUDGE_GATE_NOT_PASSED`, `PIPELINE_LOG_MISSING`, or any critical gap → summarize as blocked/repair-needed run.

在上述检查通过后，默认继续启动 `html-visualizer` 子 Agent：

```javascript
Agent({
  subagent_type: "html-visualizer",
  description: "Step 8: 生成诊断结果的前端 HTML 可视化讲解页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

Read "$SKILL_PATH/agents/html-visualizer.md" and execute the complete protocol. Do not ask the main agent to produce the page in its own context.`,
  run_in_background: true
})
```

如果用户没有明确要求跳过 HTML，可视化构建是 Step 8 的默认组成部分，而且必须由专用子 Agent 完成。

**最终交付要求**：本 skill 的正常完成结果必须同时包含 `report.md` 和 `diagnostic-report.html`。其中 HTML 只能由独立的 `html-visualizer` 子 Agent 生成，且该子 Agent 必须复用 `diagnostic-html-visualizer` skill，不允许主 agent 在主上下文中直接编写 HTML。

### HTML Review Gate

页面生成完成后，必须立即启动 `html-reviewer` 子 Agent 审核。只有审核通过，页面才算最终交付。

```javascript
Agent({
  subagent_type: "html-reviewer",
  description: "Step 8.5: 审核诊断 HTML 可视化页面的可读性、证据完整性和逻辑链",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
SKILL_PATH=${SKILL_PATH}
AUDIENCE=mixed

Read "$SKILL_PATH/agents/html-reviewer.md" and review the generated page against clarity, evidence completeness, logic chain strength, and chart/3D coverage. Write a machine-readable review artifact and report pass/fail clearly.`,
  run_in_background: true
})
```

如果 `html-reviewer` 给出 blocking issues，必须回到 `html-visualizer` 修订页面，再次审核。

Present: executive summary, key findings, diagnosis type, confidence, recommendations, optimizer highlights, workspace path, and generated HTML path. Highlight CONDITIONAL/REJECTED concerns.

---

## Agent Decoupling

Agents communicate ONLY through workspace files — never through the main agent's context:

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                ──► 00_input/extracted_knowledge.json, clarification_needed.json
                ──► 00_input/rag_deep_understanding.json
Data Processor  ──► 02_processed/ (universal + scenario-specific analysis)
                ──► 02_processed/data_analysis_conclusion.json (mandatory handoff)
                ──► 03_figures/*.png + plot_manifest.json + image_captions.json
                ──► 03_figures/visual_analysis.json (VLM evidence)
                ──► analysis_plan.md
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge           ──► 05_review/judge_feedback.json
Reporter        ──► report.md, run_summary.json
Report Reviewer ──► optimizer.md
HTML Visualizer ──► diagnostic-report.html
```

---

## Schema-First Writing Protocol

**Before writing any structured file**, read the matching schema first — construct content to the schema, write once, validate immediately. This prevents expensive rewrite cycles.

| Step | File | Schema(s) to Read First |
|------|------|-------------------------|
| Step 2 | `ontology.json` | `ontology_schema.json` |
| Step 3 | `scenario_classification.json`, `anomaly_report.json`, `data_analysis_conclusion.json` | `scenario_classification_schema.json`, `anomaly_report_schema.json`, `data_analysis_conclusion_schema.json` |
| Step 3.5 | `visual_analysis.json`, `image_captions.json` | `visual_analysis_schema.json`, `image_captions_schema.json` |
| Step 4 | `diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json` | `diagnosis_schema.json`, `evidence_schema.json`, `confidence_schema.json`, `reasoning_chain_schema.json` |
| Step 5 | `judge_feedback.json` | `judge_feedback_schema.json` |
| Step 6 | `run_summary.json` | `run_summary_schema.json` |

**Rule**: Read schema → construct content → write once → validate. Never write first and validate after.

---

## Evidence Hierarchy

Every non-observation statement must cite its evidence rank. Conclusions are limited by their weakest rank.

| Rank | Source | Label |
|------|--------|-------|
| 1 | Direct measurements in data | `[Evidence Rank 1]` |
| 2 | User-provided documentation (SOPs, manuals) | `[Evidence Rank 2]` |
| 3 | Statistical analysis (incl. validation report) | `[Evidence Rank 3]` |
| 4 | Visual evidence from charts | `[Evidence Rank 4]` |
| 5 | Established process logic / domain knowledge | `[Evidence Rank 5]` |
| 6 | External web references | `[Evidence Rank 6] [EXTERNAL]` |
| 7 | Hypotheses (unsupported) | `[Evidence Rank 7]` |

Full causation criteria (5 conditions), confidence scoring, language templates, and validation-adjusted evidence rules: `resources/evidence_rules.md`.

---

## Anti-Speculation Checks

Apply before writing any diagnostic finding:

- **Lag correlations** require time-sorted data — check `sorting_validation.time_sorted` first
- **Aggregate correlations** can reverse within subgroups — always check stratified correlations
- **Trending variables** share time as hidden confounder — check detrended r
- **Unknown parameter meanings** → `[PARAM_AMBIGUITY]` — correlation to a label is not correlation to a physical cause
- **Competing hypotheses** with identical observables are INDISTINGUISHABLE → `COMPETING_SET`, confidence ceiling 65
- **Physics-free correlations** are not diagnoses — `STATISTICAL_ONLY` is not a root cause
- **RAG knowledge is suggestive, not authoritative** — validate every RAG claim against actual data
- **Confidence, evidence gaps, and assumptions** must always be disclosed
- **Falsification conditions** must be specified for every conclusion

---

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline (Steps 0-8) |
| `/industrial-deep-diagnostic analyze` | Skip intake, run from Step 2 |
| `/industrial-deep-diagnostic review` | Re-run judge on existing results |
| `/industrial-deep-diagnostic report` | Regenerate report from existing artifacts |
| `/industrial-deep-diagnostic audit` | Run report-reviewer only (generates optimizer.md) |

---

## Developer QA

For implementation details not needed during normal execution, use `CLAUDE.md`. For repair-loop details and full bash command reference, use `pipeline-execution.md`.
