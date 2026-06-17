---
name: industrial-deep-diagnostic
description: "Multi-agent industrial diagnostic engine for manufacturing root cause analysis. Use when the user provides sensor/process data (CSV, XLSX, Parquet) and asks about anomalies, quality defects, equipment faults, SPC excursions, or root cause analysis — applies to ANY industrial process. Also triggers on: 诊断, 故障分析, 异常检测, 根因分析, 质量缺陷, 过程异常, 设备故障, 传感器数据分析, 工艺参数优化, 生产过程诊断. Pipeline: ontology construction → statistical validation (Simpson's Paradox, trend confounding, change-point detection) → multi-hypothesis physics-based diagnosis → quality-gate review → adversarial physical-truth audit. Three interaction modes: auto/interactive/minimal. Do NOT trigger for non-industrial data, simple charting, financial analysis, or statistics homework."
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

---

## Loading Guide — Progressive Disclosure

This skill uses **three levels**. Only load what the current step needs.

### Level 1: Always Loaded (this file)

The orchestration protocol — step sequence, agent launch templates, governance rules, evidence/anti-speculation checks.

For production-style execution, also treat `resources/engineering_delivery_contract.md` as binding acceptance criteria.

### Level 2: Launched Per Step (agents/)

> **禁止主 agent 执行子智能体工作！** 表格中的 **Launch sub-agent** 行意味着直接启动子智能体 — **不是**主 agent 读协议自己干。子智能体自行 Read 自己的协议并执行，主 agent 只负责传参和等待。曾经发生过主 agent 读了 context-builder 的 500+ 行协议后自己执行了全部工作，这是违反管线纪律的。

| When | Action | Why |
|------|--------|-----|
| Before Step 0 | Read `resources/rag_integration_guide.md` | RAG engine setup and one-time indexing |
| Before Step 2 | **Launch sub-agent** `Agent({subagent_type: "context-builder", ...})` | RAG retrieval + ontology construction + deep mapping |
| Before Step 3 | **Launch sub-agent** `Agent({subagent_type: "data-processor", ...})` | Statistical analysis + physics checks + visualization. data-processor internally delegates to `vlm-visual-analyzer` |
| Before Step 3 | Read `resources/visual_analysis_framework.md` | VLM chart design principles + Phase 5.5 visual analysis protocol |
| Before Step 4 | **Launch sub-agent** `Agent({subagent_type: "diagnostician", ...})` | Physics-based competing hypotheses diagnosis |
| Before Step 5 | **Launch sub-agent** `Agent({subagent_type: "judge", ...})` | Quality gate (10 criteria + physics source audit) |
| Before Step 6 | **Launch sub-agent** `Agent({subagent_type: "reporter", ...})` | Report generation from structured artifacts |
| Before Step 7 | **Launch sub-agent** `Agent({subagent_type: "report-reviewer", ...})` | Independent physical truth audit |
| Before Step 8 | **Launch sub-agent** `Agent({subagent_type: "html-visualizer", ...})` | Post-audit HTML explanation page generation (四段叙事 + ECharts + Three.js 3D产线) |
| After Step 8 | **Launch sub-agent** `Agent({subagent_type: "html-reviewer", ...})` | HTML readability / evidence-completeness review (pass/warn/fail) |
| During repair loops | Read `pipeline-execution.md` | Repair counter protocol and detailed validation rules |

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

## Multi-Agent Pipeline Architecture

This skill uses **7 specialized sub-agents** defined in `agents/`. Each is launched via the `Agent` tool with `permissionMode: "bypassPermissions"`.

| Pipeline Step | Agent | Persona | Subagent Type | Purpose |
|:-------------:|-------|--------|:-------------:|---------|
| Step 2 | Context Builder | **王教授** — 化工/材料领域知识专家，25年失效分析经验 | `context-builder` | RAG检索 + 本体ontology构建（物理语义深度理解） |
| Step 3 | Data Processor | **张工** — 高级过程数据科学家，16年流程制造数据分析经验 | `data-processor` | 数据分析 + 可视化（反幻觉、数据真实、专业图表标准） |
| Step 3.5 (internal) | VLM Visual Analyzer | **老孙（目视）** — 设备状态监测工程师，20年目视巡检经验 | `vlm-visual-analyzer` | 本体感知的VLM视觉图像分析，由图+统计+知识联合提取结构化视觉证据 |
| Step 4 | Diagnostician | **刘总工** — 首席根因分析工程师，28年产线诊断经验 | `diagnostician` | 竞争假说根因诊断（物理机制+定量验证+五条件反推测） |
| Step 5 | Judge | **陈主任** — 国家工业产品质检中心高级审核员，15年质量审计经验 | `judge` | 10项标准质量门审查 |
| Step 6 | Reporter | **周工** — 技术报告撰写专家，15年产线技术报告经验，近5年面向企业高管 | `reporter` | 面向决策者的9节诊断报告（金字塔结构: 结论优先、白话解释、证据链路清晰） |
| Step 7 | Report Reviewer | **孙审计** — 过程安全与质量审计专家，32年跨国工业审计经验 | `report-reviewer` | 独立物理真实审计 |
| Step 8 | HTML Visualizer | **林工** — 工业前端可视化工程师，14年HMI/SCADA+工业Web可视化经验，把复杂诊断结论转成一眼能看懂的讲解页面 | `html-visualizer` | 生成讲解式 HTML 可视化页面（ECharts + Three.js + 证据链） |
| Step 8.5 | HTML Reviewer | **赵审阅** — 工业信息可视化审校，15年技术文档审校经验，检查页面是否真的能让非算法用户看懂 | `html-reviewer` | 审核 HTML 是否清楚、完整、能支撑结论 |

> **vlm-visual-analyzer 是 data-processor 的内部子智能体** — 它在 Phase 5.5 内部启动，不是独立的管线步骤。它被独立定义为 agent 因为它需要专门的 context-aware 图像读取能力（先读 ontology 理解参数物理含义，再带有知识地看 PNG 图）。

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

---

## Step-by-Step Protocol

### Step 0: Setup (Main Agent)

```bash
SKILL_PATH="<path-to-this-skill>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
```

Copy input data files into `00_input/`. Update `00_input/run_config.json` with the real `data_path` and user objective/constraints. All Python invocations MUST use `scripts/.venv/bin/python`.

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
