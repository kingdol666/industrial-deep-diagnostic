---
name: industrial-deep-diagnostic
description: "Use when the user provides industrial sensor/process data (CSV, XLSX, Parquet) and asks about anomalies, quality defects, equipment faults, SPC excursions, or root cause analysis. Also triggers on 诊断, 故障分析, 异常检测, 根因分析, 质量缺陷, 过程异常, 设备故障, 传感器数据分析, 工艺参数优化, 生产过程诊断. Runs an 8-step multi-agent diagnostic pipeline: ontology-building, statistical validation (Simpson's Paradox, trend confounding, change-point detection), multi-hypothesis diagnosis with physical quantitative verification, quality-gate review, and adversarial physical-truth audit. Do NOT trigger for: non-industrial data, simple charting, financial analysis, or general statistics homework."
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [industrial, diagnostics, root-cause-analysis, time-series, manufacturing, physics, multi-agent]
    related_skills: [data-science, jupyter-live-kernel, hermes-agent]
---

# Industrial Deep Diagnostic

## Overview

端到端工业深度诊断系统 — 对传感器/工艺数据执行 8 阶段根因分析的场景自适应诊断引擎。融合三大知识源：数据自描述（列名/值域/统计特征推断工艺类型）、RAG 领域知识（物理原理/因果机制/失效模式）、第一性原理物理推断（守恒律/量纲分析/本构关系）。诊断是排除而非确认，每个结论必须有 (1) 时间先后 (2) 统计显著 (3) 物理机制 (4) 无矛盾。

**默认输出语言为中文。** 报告、诊断结论、审计文档使用中文。JSON enum 字段保持英文。

## When to Use

**触发条件:**
- 用户提供工业传感器/过程数据（CSV, XLSX, Parquet）并询问异常、质量缺陷、设备故障、SPC 异常或根因分析
- 中文触发词: 诊断, 故障分析, 异常检测, 根因分析, 质量缺陷, 过程异常, 设备故障, 传感器数据分析, 工艺参数优化, 生产过程诊断
- 任何需要从工业数据中追溯物理根因的场景

**不要触发:**
- 非工业数据（金融、社交、通用统计作业）
- 简单图表绘制（没有诊断需求）
- 通用数据分析（没有物理机制要求）
- 纯 RAG 知识检索（没有数据文件输入）

## Core Principle

Diagnosis is elimination, not confirmation. Every conclusion needs: (1) temporal precedence, (2) statistical evidence, (3) physical mechanism, (4) no contradictions. Missing any → label as `[HYPOTHESIS]`. When data cannot discriminate between competing hypotheses → output `COMPETING_SET`, not a guess.

**Four pillars** that make this work across any industry:

| Pillar | Principle | Anti-Pattern |
|--------|-----------|--------------|
| Scenario-Adaptive | Analysis flows from data characteristics — no hardcoded process types | Applying a "CNC template" to non-CNC data |
| RAG Deep Understanding | RAG knowledge is semantically comprehended, not mechanically mapped | Field-by-field copy from RAG output to ontology |
| Data↔Ontology Bidirectional | Ontology predicts → data confirms; data reveals → ontology explains; discrepancies are diagnostic signals | Building ontology and analyzing data independently |
| Physics-Based Inference | Every correlation must trace to governing equations; derive from first principles when needed | "Parameter X correlates with quality, therefore X is the cause" |

---

## Loading Guide — Progressive Disclosure

This skill uses **three levels** of loading. Only read what the current step needs:

### Level 1: Always Loaded (this file)
The orchestration protocol — step sequence, commands, evidence rules, anti-speculation checks.

For any production-style execution, also treat `resources/engineering_delivery_contract.md` as binding acceptance criteria.

### Level 2: Launched Per Step (Hermes delegate_task)

> ⚠️ **禁止主 agent 执行子智能体工作！** 使用 `delegate_task` 启动子代理 — 子代理自己读取资源并执行，主 agent 只负责传参和等待。

| When | Action | Why |
|------|--------|-----|
| Before Step 0 | Read `resources/rag_integration_guide.md` | RAG engine setup and one-time indexing |
| Before Step 2 | `delegate_task` — load `.hermes/agents/context-builder.md` 获取 goal/context | RAG retrieval + ontology construction + deep mapping |
| Before Step 3 | `delegate_task` — load `.hermes/agents/data-processor.md` 获取 goal/context。**data-processor 内部使用 `delegate_task` 启动 vlm-visual-analyzer 子代理** | Statistical analysis + physics checks + scenario-adaptive visualization |
| Before Step 3 | `resources/visual_analysis_framework.md` | VLM chart design principles + Phase 5.5 visual analysis protocol |
| Before Step 4 | `delegate_task` — load `.hermes/agents/diagnostician.md` 获取 goal/context | Physics-based competing hypotheses diagnosis |
| Before Step 5 | `delegate_task` — load `.hermes/agents/judge.md` 获取 goal/context | Quality gate (10 criteria + physics source audit) |
| Before Step 6 | `delegate_task` — load `.hermes/agents/reporter.md` 获取 goal/context | Report generation from structured artifacts |
| Before Step 7 | `delegate_task` — load `.hermes/agents/report-reviewer.md` 获取 goal/context | Independent physical truth audit |
| During repair loops | Read `pipeline-execution.md` | Repair counter protocol and detailed validation rules |

### Level 3: Loaded On-Demand (resources/)
Detailed frameworks — load only when the agent's instructions tell you to.

| When | Read | Content |
|------|------|---------|
| context-builder needs RAG deep understanding protocol | `resources/rag_deep_understanding_protocol.md` | R1-R4: semantic comprehension, knowledge-data alignment, physics extraction, gap identification |
| context-builder builds ontology; data-processor updates it | `resources/data_ontology_mapping_framework.md` | Three mapping directions: prediction→validation, discovery→refinement, discrepancy→diagnostic signal |
| diagnostician encounters novel parameters | `resources/physics_inference_framework.md` | L1-L5 ladder: physical quantity → governing law → causal chain → magnitude → competing mechanisms |
| troubleshooting pipeline integration | `resources/pipeline_coherence_and_synergy.md` | Step synergy rules, cross-step verification checklist, RAG two-stage protocol, artifact completeness |
| diagnostician needs evidence definitions | `resources/evidence_rules.md` | 7-rank evidence hierarchy and causation criteria |
| diagnostician needs methodology | `resources/diagnosis_method.md` | 6-stage diagnostic methodology with statistical thresholds |
| diagnostician reads pre-computed checks | `resources/diagnostician_dual_drive_reference.md` | Quality reset analysis tables, onset-coincidence classification, physical check conclusions |
| any agent needs physics pattern examples | `resources/parameter_to_physics.json` | Pattern library — structural examples for building physics arguments, NOT a lookup table |
| report-reviewer needs cross-industry physics | `resources/process_knowledge_base.md` | 16 universal physics principles, quantitative relationships, degradation patterns |
| developer reference | `resources/script_and_toolkit_reference.md` | Complete catalog of scripts, schemas, and templates |
| engineering delivery contract | `resources/engineering_delivery_contract.md` | Mandatory execution, artifact, and completion contract for deployable runs |

**After each agent produces output**, validate with the matching schema:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/<schema>.json" "$RUN_DIR/<path>/<output>.json"
```

**RAG dependency**: Step 2 delegates to the `rag-knowledge-builder` skill. If unavailable, context-builder falls back to building the ontology from scratch. See `resources/rag_integration_guide.md`.

---

## Agent Configuration (agents.yaml)

**项目级 Agent 配置文件**: `.hermes/agents.yaml`

在执行管线前，主 agent **必须先读取** `.hermes/agents.yaml` 获取每个子 agent 的:
- **model/provider**: 子 agent 使用的模型（vlm-visual-analyzer 需要 vision-capable 模型）
- **spawn_method**: 启动方式 — `delegate_task`（继承主模型）或 `terminal_spawn`（独立模型进程）
- **toolsets**: 推荐工具集
- **max_iterations**: 最大迭代次数
- **reasoning_effort**: 推理强度

```bash
# 读取 agent 配置
cat "$PROJECT_ROOT/.hermes/agents.yaml"
```

**技能发现机制 (Symlink)**:
- **无需写死绝对路径** — 通过 symlink 让 Hermes 自动发现项目技能
- 运行 `bash .hermes/setup_skills.sh` 创建 symlink
- 两个技能会链接到 `~/.hermes/skills/` 下，Hermes 自动加载

---

## Multi-Agent Pipeline Architecture

This skill uses **7 specialized sub-agents** launched via Hermes `delegate_task`. Each agent has a task definition in `.hermes/agents/` containing its `goal`, `context`, and recommended `toolsets`.

| Pipeline Step | Agent Name | Purpose |
|:-------------:|------------|---------|
| Step 2 | Context Builder | RAG检索 + 本体ontology构建 |
| Step 3 | Data Processor | 数据分析 + 可视化 |
| Step 3.5 (internal) | VLM Visual Analyzer | 本体感知的VLM视觉图像分析 — 由图+统计+知识联合提取结构化视觉证据 |
| Step 4 | Diagnostician | 竞争假说根因诊断 |
| Step 5 | Judge | 10项标准质量门审查 |
| Step 6 | Reporter | 20节中文诊断报告生成 |
| Step 7 | Report Reviewer | 独立物理真实审计 |

> **vlm-visual-analyzer 是内部子代理** — 它由 data-processor 在其 Phase 5.5 内部启动，不是独立的管线步骤。

## Execution Flow

```
Step 0: Setup ──► Step 1: Inspect ──► Step 2: context-builder (RAG + Ontology + Deep Mapping)
                                          │
                                          ▼
                                     Step 2.5: Clarify ──┐
                                          │               │
                                          ▼               │
                                     Step 3: data-processor (Data+Viz+VLM Analysis)
                                          │               │
                                          ▼               │
                                     Step 4: diagnostician (Physics-Based Competing Hypotheses)
                                          │               │
                                    ┌─────▼─────┐         │
                                    │ Step 5:   │◄── repair max 3 ─┐
                                    │ judge     │                    │
                                    └─────┬─────┘                    │
                                          │ pass                     │
                                          ▼                         │
                                    Step 6: reporter (Report Generation)
                                          │                         │
                                          ▼                         │
                                    ┌─────▼──────┐                  │
                                    │ Step 7:    │── re-diagnose ───┘
                                    │ report-reviewer (Audit)│
                                    └─────┬──────┘
                                          │ ENDORSED
                                          ▼
                                    Step 8: Present
```

**Sequence**: Steps 2→2.5→3 are strictly sequential. Steps 4→5→6→7 are sequential with quality gates between each.

**Pipeline discipline rule**: When executing this skill, the agent MUST follow the pipeline step-by-step and **must not skip, reorder, or silently omit steps** just to save time or tokens. Every step must be explicitly checked and executed according to the pipeline contract unless the pipeline itself defines a documented skip condition.

**Repair loops**: Judge→Diagnostician max 3 iterations. Reviewer→Diagnostician max 2 cycles. **Global cap: total re-diagnosis ≤ 5**. Counter persists in `.pipeline_events.jsonl`. See `pipeline-execution.md` §Repair Loop Protocol.

**Execution proof rule**: A run is not considered fully valid unless the final artifact check confirms both the output artifacts and the `.pipeline_events.jsonl` execution log.

**Engineering acceptance rule**: A run is not considered deployable unless it also satisfies `resources/engineering_delivery_contract.md`.

**Evidence-closure rule**: A run is not considered diagnostically complete unless the final checks confirm the evidence loop is closed.

---

## Step-by-Step Protocol

### Step 0: Setup (Main Agent)

```bash
SKILL_PATH="<path-to-this-skill>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"

# Create run directory: <timestamp>_<name>/ with 00_input/ through 06_scripts/
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"

# Ensure Python venv ready (auto-installs uv + deps)
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
```

`setup.mjs` now bootstraps both `run_manifest.json` and `.pipeline_events.jsonl` with a `run_initialized` event. Treat this as the start of execution proof.

Copy input data files into `00_input/`. All Python invocations MUST use `scripts/.venv/bin/python` — never system `python3`.

### Step 1: Inspect Data (Main Agent)

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

Recommended main-agent execution log:
```bash
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_start --agent main-agent --step inspect --data '{"data_path":"<data_path>"}'
# run inspect + write 00_input/input_manifest.json / user_context.json
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_complete --agent main-agent --step inspect --files 00_input/input_manifest.json,00_input/user_context.json
```

`setup.mjs` now creates a default `00_input/run_config.json`. Main agent must update it with the real `data_path` and any user-provided objective/constraints before Step 2.

| Mode | Behavior |
|------|----------|
| **auto** | Zero user questions. Infer process characteristics, quality targets, parameter meanings from column patterns and value ranges. |
| **interactive** | Ask up to 5 clarification questions. |
| **minimal** | Ask 1-2 essential questions only. |

Produce process-agnostic characterization: column name patterns → physical quantity hypotheses, value range confirmation, statistical signature classification (trending/cyclic/step-change/stationary), categorical columns for stratification, time column detection.

Save `input_manifest.json` and `user_context.json` to `00_input/`.

### Step 2: Context Build (Sub-Agent via delegate_task)

⚠️ **DELEGATION GUARD — 不要在主 agent 中执行 context-builder 的工作！**

| 错误的做法 | 正确的做法 |
|-----------|-----------|
| Read `agents/context-builder.md` 全文后自己执行 Phase A-D | 直接通过 `delegate_task` 启动子代理，让它自己读协议执行 |
| 自己调用 `rag-knowledge-builder` skill | 子代理有工具权限，它会自己调用 |
| 自己写 ontology.json | 子代理写完后主 agent 只需验证 |

**正确的启动方式 — Load `.hermes/agents/context-builder.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="构建工业诊断领域本体模型。基于输入数据自描述特征，结合RAG知识检索和网络搜索，构建ontology.json。执行完整的R1-R4深度理解协议，完成数据↔本体双向映射。输出ontology.json至RUN_DIR/01_ontology/。",
    toolsets=["terminal", "file", "web"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\nREFERENCE_DIR={REFERENCE_DIR}\nPROCESS_DESCRIPTION={PROCESS_DESCRIPTION}\nUSER_OBJECTIVE={USER_OBJECTIVE}\nINTERACTION_MODE=auto\n\n执行 context-builder 协议完整流程。\n完整协议文档见: agents/context-builder.md"
)
```

**Sub-agent loads**: It reads its own protocol from `agents/context-builder.md` and `resources/` files.

**Outputs**: `01_ontology/ontology.json`, `schema.json`, `00_input/extracted_knowledge.json`, `rag_deep_understanding.json`, `clarification_needed.json`

### Step 2.5: Clarification Gate (Main Agent)

Check `clarification_needed.json`. Auto mode skips all questions and applies physics inference. Interactive/minimal modes ask per their respective rules. See `pipeline-execution.md` §Step 2.5 for detailed protocol.

Record the gate outcome explicitly:
```bash
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event clarification_auto_inferred --agent main-agent --step clarification_gate
```

### Step 3: Data Processing + Visualization (Sub-Agent via delegate_task)

**Load `.hermes/agents/data-processor.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="执行工业数据深度处理与可视化分析。运行统计基线脚本（Simpson悖论检测、趋势混淆分析、变点检测），进行场景特化分析，生成自适应可视化图表，委托VLM视觉分析子代理读图，最终输出data_analysis_conclusion.json和validate_report.json。",
    toolsets=["terminal", "file", "vision"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 data-processor 完整流程（Phase 0-6）。\n所有 Python 必须用 SKILL_PATH/scripts/.venv/bin/python\n完整协议文档见: agents/data-processor.md"
)
```

**Sub-agent loads**: Its own protocol from `agents/data-processor.md`. The agent knows full Phase 0-6 structure, group-aware rules, visualization protocol, and internally delegates image reading via another `delegate_task` for `vlm-visual-analyzer`.

**Stabilization rule**: Before Step 4, run:
```bash
node "$SKILL_PATH/scripts/normalize-anomaly-report.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/synthesize-data-analysis-conclusion.mjs" "$RUN_DIR"
```

**Key outputs**: `02_processed/` (17+ files), `03_figures/*.png` (9+ plots), `03_figures/visual_analysis.json`, `analysis_plan.md`, `06_scripts/`

### Step 3.5: VLM Visual Analysis (Embedded in Step 3)

The `data-processor` agent's Phase 5.5 delegates VLM image reading to the `vlm-visual-analyzer` sub-agent via `delegate_task` internally. No separate main-agent call needed.

Outputs: `03_figures/visual_analysis.json`, `03_figures/image_captions.json`

If a valid time column exists, Step 3 is only considered complete when a master shared-time-axis figure such as `03_figures/fig_master_time_aligned_overlay.png` exists. If no valid time column exists, Step 3 must explicitly record the not-applicable reason in `visual_analysis.json` and `analysis_plan.md`.

### Step 4: Diagnostician (Sub-Agent via delegate_task)

**Load `.hermes/agents/diagnostician.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="执行工业诊断根因分析。基于统计证据、物理机制和VLM视觉洞察，执行竞争假说协议。生成diagnosis.json、evidence.json、confidence.json、reasoning_chain.json。支持三种输出类型：DETERMINED/COMPETING_SET/NEEDS_DATA。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\nREPAIR_INSTRUCTIONS={REPAIR_INSTRUCTIONS}\n\n执行 diagnostician 完整协议（Phase 0-7）。\n完整协议文档见: agents/diagnostician.md"
)
```

**Schema-First 规则**: Sub-agent 按 Phase 6 规则执行 — 先读 `templates/diagnosis_template.json` 和全部 4 个 schema，按 required 字段构造，一次写入通过验证。

Validate (×4):
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/diagnosis_schema.json" "$RUN_DIR/04_diagnostics/diagnosis.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/evidence_schema.json" "$RUN_DIR/04_diagnostics/evidence.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/confidence_schema.json" "$RUN_DIR/04_diagnostics/confidence.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/reasoning_chain_schema.json" "$RUN_DIR/04_diagnostics/reasoning_chain.json"
```

Outputs: `04_diagnostics/diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json`

### Step 5: Judge Review (Sub-Agent via delegate_task)

**Load `.hermes/agents/judge.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="执行工业诊断质量门审查。对diagnosis.json、evidence.json、confidence.json进行10项标准评分，验证统计基础、物理机制和逻辑一致性。输出judge_feedback.json，评分<90触发修复循环。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 judge 完整审查协议。\n完整协议文档见: agents/judge.md"
)
```

**Verdict**: PASS (≥90) → Step 6 | NEEDS_REPAIR (70-89) → re-spawn diagnostician (max 3) | FAIL (<70) → halt

Validate:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/judge_feedback_schema.json" "$RUN_DIR/05_review/judge_feedback.json"
```
Output: `05_review/judge_feedback.json`

### Step 6: Report Generation (Sub-Agent via delegate_task)

**Load `.hermes/agents/reporter.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="生成工业诊断最终报告。从所有结构化产物组装20节中文报告。嵌入所有图表、透明披露统计验证结果。输出report.md至RUN_DIR/。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 reporter 完整协议。\n完整协议文档见: agents/reporter.md"
)
```

Output: `report.md` (791+ lines, 20 sections), `run_summary.json`

### Step 7: Physical Truth Audit (Sub-Agent via delegate_task)

**Load `.hermes/agents/report-reviewer.md` for the goal/context template, then use `delegate_task`:**

```
delegate_task(
    goal="执行工业诊断报告独立物理真实审计。作为怀疑论者，自己运行Python验证关键统计，不信任管线摘要。检查物理机制的可溯源性、统计基础的完整性、逻辑的连贯性。输出optimizer.md。",
    toolsets=["terminal", "file", "web"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 report-reviewer 完整审计协议。\n完整协议文档见: agents/report-reviewer.md"
)
```

**Verdict**: ENDORSED → Step 8 | CONDITIONAL / REJECTED → re-spawn diagnostician (max 2 cycles, global cap ≤ 5)

Output: `optimizer.md`

### Step 8: Present Results (Main Agent)

```bash
node "$SKILL_PATH/scripts/finalize-run-artifacts.mjs" "$RUN_DIR" "$SKILL_PATH"
node "$SKILL_PATH/scripts/artifact-check.mjs" "$RUN_DIR" "$SKILL_PATH"
```

Show: executive summary, key findings, diagnosis type, confidence, recommendations, workspace path. Highlight CONDITIONAL/REJECTED concerns.

---

## Agent Decoupling

Agents communicate ONLY through workspace files — never through the main agent's context:

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                ──► 00_input/extracted_knowledge.json, clarification_needed.json, web_findings.md
                ──► 00_input/rag_deep_understanding.json
User Clarification ──► Updated ontology.json, schema.json
Data Processor  ──► 02_processed/ (universal + scenario-specific analysis files)
                ──► 02_processed/data_analysis_conclusion.json (expert data-analysis handoff)
                ──► 03_figures/*.png + plot_manifest.json + image_captions.json
                ──► 03_figures/visual_analysis.json (VLM visual insights from vlm-visual-analyzer sub-agent)
                ──► analysis_plan.md, 06_scripts/scenario_plots.py, 06_scripts/expert_analysis.py when needed
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge           ──► 05_review/judge_feedback.json
Reporter        ──► report.md, run_summary.json
Report Reviewer ──► optimizer.md
```

---

## 全局规则: Schema-First Writing Protocol

**这是最重要的规则。**

在向 `RUN_DIR` **写入任何结构化文件**之前，必须先读取对应的 schema 文件（`schemas/*.json`）和模板（`templates/*.json`）—— 这样一次写入就能通过验证。

```
读取 schema → 按 schema 字段构造 → 一次写入 → 立即验证
                                     ↓ 失败
                               停止! 检查 schema 字段定义
```

| 步骤 | 写入文件 | 写入前必须读取 |
|------|---------|---------------|
| Step 2 | `ontology.json` | `schemas/ontology_schema.json` |
| Step 3 | `scenario_classification.json` | `schemas/scenario_classification_schema.json` |
| Step 3 | `data_analysis_conclusion.json` | `schemas/data_analysis_conclusion_schema.json` + `templates/data_analysis_conclusion_template.json` |
| Step 3.5 | `visual_analysis.json` | `schemas/visual_analysis_schema.json` |
| Step 3.5 | `image_captions.json` | `schemas/image_captions_schema.json` |
| Step 4 | `diagnosis.json` | `schemas/diagnosis_schema.json` + `templates/diagnosis_template.json` |
| Step 4 | `evidence.json` | `schemas/evidence_schema.json` |
| Step 4 | `confidence.json` | `schemas/confidence_schema.json` |
| Step 4 | `reasoning_chain.json` | `schemas/reasoning_chain_schema.json` |
| Step 5 | `judge_feedback.json` | `schemas/judge_feedback_schema.json` + `templates/judge_template.json` |
| Step 6 | `run_summary.json` | `schemas/run_summary_schema.json` + `templates/run_summary_template.json` |

## JSON 转义与路径引号规则

1. **JSON 中的引号嵌套**: 在 JSON 字符串中写入中文文本时，如果文本包含双引号，必须转义为 `\"...\"`，或改写为无引号的表达方式。
2. **路径引号**: 当 `SKILL_PATH` 或 `DATA_PATH` 包含空格时，Bash 命令必须对所有路径变量使用双引号包裹。

## Evidence Hierarchy

| Rank | Source | Label |
|------|--------|-------|
| 1 | Direct measurements in data | `[Evidence Rank 1]` |
| 2 | User-provided documentation | `[Evidence Rank 2]` |
| 3 | Statistical analysis (incl. validation report) | `[Evidence Rank 3]` |
| 4 | Visual evidence from charts | `[Evidence Rank 4]` |
| 5 | Established process logic / domain knowledge | `[Evidence Rank 5]` |
| 6 | External web references | `[Evidence Rank 6] [EXTERNAL]` |
| 7 | Hypotheses (unsupported) | `[Evidence Rank 7]` |

Every conclusion limited by its weakest evidence rank.

---

## Anti-Speculation Rules

Apply these checks before writing any finding:

- **Lag correlations** require time-sorted data — check `sorting_validation.time_sorted` first
- **Aggregate correlations** can reverse within subgroups — always check stratified correlations
- **Trending variables** share time as hidden confounder — check detrended r
- **Unknown parameter meanings** → `[PARAM_AMBIGUITY]` — correlation to a label is not correlation to a physical cause
- **Competing hypotheses** with identical observables are INDISTINGUISHABLE → `COMPETING_SET`, confidence ceiling 65
- **Physics-free correlations** are not diagnoses — `STATISTICAL_ONLY` is not a root cause
- **RAG knowledge is suggestive, not authoritative** — every RAG claim must be validated against actual data
- **Confidence, evidence gaps, and assumptions** must always be disclosed
- **Falsification conditions** must be specified for every conclusion

---

## Workflow Instructions

This skill does not use slash commands. Instead, load this skill and describe what you need:

| User intent | How the agent executes |
|-------------|----------------------|
| "诊断这个数据文件" / "Analyze this data" | Full pipeline (Steps 0-8) |
| "分析已有数据" / "Analyze existing data" | Skip intake, run from Step 2 |
| "重新评审结果" / "Review results" | Re-run judge on existing results |
| "重新生成报告" / "Regenerate report" | Regenerate report from existing artifacts |
| "审计报告" / "Audit report" | Run report-reviewer only (generates optimizer.md) |

---

## Reference Files — Complete Index

### Execution & Protocol
| File | When | Content |
|------|------|---------|
| `pipeline-execution.md` | During repair loops | Repair counter protocol, clarification gate details, statistical validation framework, confidence adjustment rules |

### Agent Instructions (Level 2)
| File | When | Content |
|------|------|---------|
| `agents/context-builder.md` | Before Step 2 | Full RAG retrieval + deep understanding + ontology construction protocol |
| `agents/data-processor.md` | Before Step 3 | Full statistical analysis + anomaly detection + physics checks + VLM visualization protocol |
| `agents/diagnostician.md` | Before Step 4 | Full physics-based competing hypotheses + first-principles inference protocol |
| `agents/judge.md` | Before Step 5 | Full 10-criteria quality gate + physics source audit protocol |
| `agents/reporter.md` | Before Step 6 | Full report generation from structured artifacts protocol |
| `agents/report-reviewer.md` | Before Step 7 | Full independent physical truth audit protocol |
| `agents/vlm-visual-analyzer.md` | Before Step 3.5 (internal) | Full VLM image reading protocol |

### Hermes Agent Task Definitions
| File | When | Content |
|------|------|---------|
| `.hermes/agents/context-builder.md` | Before Step 2 | delegate_task goal/context/toolsets template |
| `.hermes/agents/data-processor.md` | Before Step 3 | delegate_task goal/context/toolsets template |
| `.hermes/agents/diagnostician.md` | Before Step 4 | delegate_task goal/context/toolsets template |
| `.hermes/agents/judge.md` | Before Step 5 | delegate_task goal/context/toolsets template |
| `.hermes/agents/reporter.md` | Before Step 6 | delegate_task goal/context/toolsets template |
| `.hermes/agents/report-reviewer.md` | Before Step 7 | delegate_task goal/context/toolsets template |
| `.hermes/agents/vlm-visual-analyzer.md` | Before Step 3.5 | delegate_task goal/context/toolsets template |

### Frameworks & Methodology (Level 3 — load on demand)
| File | When | Content |
|------|------|---------|
| `resources/rag_deep_understanding_protocol.md` | context-builder Phase 3 | R1-R4: semantic comprehension → knowledge-data alignment → physics extraction → gap identification |
| `resources/visual_analysis_framework.md` | data-processor Phase 5.5 / diagnostician Phase 0 | VLM chart design principles, time-aligned overlay spec, visual observation extraction protocol |
| `resources/data_ontology_mapping_framework.md` | context-builder Phase 4 / data-processor Phase 5.5.6 | Three mapping directions, discrepancy-as-signal, deep mapping checklist |
| `resources/physics_inference_framework.md` | diagnostician Phase 1 | L1-L5 ladder: quantity ID → governing law → causal chain → magnitude → competing mechanisms |
| `resources/pipeline_coherence_and_synergy.md` | Troubleshooting pipeline integration | Step synergy rules, cross-step verification, RAG two-stage protocol, artifact completeness |
| `resources/evidence_rules.md` | diagnostician / judge / reviewer | Evidence hierarchy details and causation criteria |
| `resources/diagnosis_method.md` | diagnostician | 6-stage methodology with statistical thresholds |
| `resources/diagnostician_dual_drive_reference.md` | diagnostician | Pre-computed check results, classification tables, R2 documentation format |

### Knowledge & Data
| File | When | Content |
|------|------|---------|
| `resources/parameter_to_physics.json` | diagnostician Phase 0.5 | Pattern library — structural examples, NOT a lookup table |
| `resources/process_knowledge_base.md` | report-reviewer Step 1 | 16 universal physics principles, quantitative relationships, degradation patterns |
| `resources/rag_integration_guide.md` | Before Step 0 | RAG engine setup, one-time indexing, fallback behavior |

### Schemas, Templates & Scripts
| Directory | When | Content |
|-----------|------|---------|
| `schemas/*.json` (11 files) | After each agent output | JSON Schema validation for every structured artifact |
| `templates/*.md`, `templates/*.json` | During Steps 3-6 | Output format templates |
| `scripts/` (14 files) | Throughout pipeline | Pre-built Node.js + Python scripts |
| `examples/` (3 scenarios) | Context builder reference | Sample ontologies for common process types |
| `tests/checklists/` (4 files) | Developer QA | Diagnosis, judge, ontology, report quality checklists |

---

## Common Pitfalls

1. **主 agent 越权执行子 agent 工作** — 不要在读完 agent 协议后自己执行。正确做法是 `delegate_task` 启动子代理，让它自己读协议。

2. **跳过 Phase 0** — data-processor 的 Phase 0（数据探索 + analysis_plan.md）是强制步骤，跳过会导致后续分析方向错误。

3. **Schema-First 违规** — 先写 JSON 后验证是最常见的 token 浪费源。正确流程: 读 schema → 按字段构造 → 一次写入 → 立即验证。

4. **Python 路径错误** — 必须使用 `scripts/.venv/bin/python`，不是系统 `python3`。运行 `node scripts/uv_env_setup.mjs` 获取路径。

5. **统计相关性当诊断** — 没有物理机制的 r=0.95 只是统计发现，不是根因。每个结论必须追溯到控制方程或物理机制。

6. **忽略产品分组** — 当数据中存在产品分组列时，不分组的分析会把型号差异当成工艺漂移。强制分组分析。

7. **忘记 RAG 知识验证** — RAG 检索的知识是启发性的，不是权威的。每个 RAG 断言必须在实际数据中验证。

8. **路径未加引号** — SKILL_PATH 或 DATA_PATH 包含空格时，Bash 命令必须用双引号包裹。

## Verification Checklist

- [ ] `setup.mjs` 创建 run_dir 后检查 `run_manifest.json` 和 `.pipeline_events.jsonl` 存在
- [ ] Step 1 inspect 后 `input_manifest.json` 和 `user_context.json` 写入 00_input/
- [ ] Step 2 context-builder 通过 `delegate_task` 启动（非主 agent 自己执行）
- [ ] Step 2 输出 `ontology.json` 通过 `validate.mjs` schema 验证
- [ ] Step 3 data-processor 先写 `analysis_plan.md`（Phase 0）再执行分析
- [ ] Step 3 输出 `data_analysis_conclusion.json` 和 `validate_report.json`
- [ ] Step 4 diagnostician 生成全部 4 个诊断文件并通过 schema 验证
- [ ] Step 5 judge 评分 >= 90 才进入 Step 6（否则进入修复循环，最多 3 次）
- [ ] Step 6 reporter 生成的 report.md 包含 Section 14（统计验证强制节）
- [ ] Step 7 report-reviewer 输出 `optimizer.md` 且判定为 ENDORSED
- [ ] Step 8 `artifact-check.mjs` 通过（产物完整性 + 事件日志完整性）
- [ ] 全局重诊断次数 <= 5（`pipeline_events.jsonl` 中 `repair_spawn` 事件计数）
- [ ] 所有 Python 调用使用 `scripts/.venv/bin/python`
