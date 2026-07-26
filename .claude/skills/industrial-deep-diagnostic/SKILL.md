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
用户上传数据 → 9 步诊断 → report.md + diagnostic-report.html

输入: CSV/XLSX/Parquet 工业传感器/工艺数据
输出: 中文诊断报告 (report.md) + HTML 可视化讲解页 (diagnostic-report.html)
核心: 本体构建 → 去趋势/分层/Simpson检测 → 竞争假说 → 物理验证 → Judge审查 → HTML可视化

🔴 默认执行: FULL-AUTO — 9 步连续跑完、零人工干预、强制产出全部文件 (report.md + diagnostic-report.html + evidence_closure_report.json + optimizer.md)。仅当用户显式声明 (interactive 模式 / 跳过某步 / 不要 HTML) 才偏离。

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

## Execution Flow (V3 — 5 Phases)

```
Phase 1: BOOTSTRAP (主 Agent, ~2 min)
  └─ Setup + Inspect + Clarify merged
       │
       ▼
Phase 2: UNDERSTAND (并行 2 子 Agent, ~5 min)
  ├─ context-builder   → ontology + RAG + 知识
  └─ data-preprocessor → 清洗 + 特征 + 稳态
       │
       (主 Agent 汇合: ontology-guided analysis selection)
       ▼
Phase 3: ANALYZE (data-processor, ~8 min)
  └─ 统计分析 + 可视化 + VLM 视觉分析 + data_analysis_conclusion.json (V2 handoff)
       │
       ▼
Phase 4: DIAGNOSE (diagnostician, ~7 min)
  └─ 信任 V2 handoff; 竞争假说 + 物理推理 + 证据融合
       │
       ▼
Phase 5: DELIVER + AUDIT (3 子 Agent 并行, ~8 min)
  ├─ judge (7 项评分)
  ├─ reporter (report.md)
  └─ html-visualizer (HTML)
       │ [judge 完成]
       ▼
       report-reviewer (物理真相审计 + raw data spot-check)
       html-reviewer (HTML 审校)
       │
       ▼
       Finalize: evidence closure + artifact check
```

### 🔴 Auto-Build HTML（非交互强制执行）

当 Phase 4 完成（4 个诊断产物 schema-valid）后，主 Agent **必须立即、自动、连续地**并行启动 judge + reporter + html-visualizer，**全程不得向用户发出"是否继续？"之类的确认提问**。

**唯一允许跳过 HTML 的方式**（必须前置声明，不得临时询问）：①会话开始时用户已明确声明"不要 HTML"/"只要 report.md"；②或 `00_input/html_opt_out` 标记文件在 HTML 启动前已存在 — `touch "$RUN_DIR/00_input/html_opt_out"`。二者均不满足 → **无条件自动构建**。

**HTML 必须由 `html-visualizer` 子 Agent 生成，禁止主 Agent 在主上下文中拼页面（红灯动作 #1）。**

---

## Pipeline Governance

### Execution Discipline

- 🔴 **默认全自动 (FULL-AUTO)**：`interaction_mode` 默认 `auto`，5 阶段连续执行到 `report.md` + `diagnostic-report.html` + `evidence_closure_report.json` 全部产出，**中间零人工干预**。**仅用户显式指令**（interactive 模式 / 指定跳过某步 / `00_input/html_opt_out`）才偏离。
- Execute phases in order. Never skip, reorder, or silently omit. If a step does not apply, record `not_applicable_reason` in the relevant artifact.
- **Phase 2 并行**：context-builder 和 data-preprocessor 互不依赖，并行启动；主 Agent 等两者完成后做 ontology-guided analysis selection。
- **Phase 5 并行**：judge / reporter / html-visualizer 并行启动（消费同一份 Phase 4 产物）；report-reviewer 必须等 judge 完成后启动。
- **Agent 自治 (V3)**：每个子 Agent 对自己的输出验证负责（schema validate + quality check）。**删除了原 9 个 CP 检查点** — 主 Agent 不再逐项核查子 Agent 输出，而是依赖 `artifact-check.mjs` 作为权威结束门。

### Repair Loops

- **Judge best-of-3（保证交付）**：最多 3 轮 repair，每轮追最高分；`≥90` 立即 break；`<90` 取 3 轮内最高分诊断（`best_round_*` 快照），**永远产出 report + HTML**，不 halt。
- Reviewer → Diagnostician (full D→J→R→R cycle): max 2 cycles.
- **Global cap: total re-diagnosis ≤ 5.** Counter persists in `.pipeline_events.jsonl` via `repair_spawn` events. Before any repair loop, count existing `repair_spawn` entries to restore counter — do not rely on in-memory state.

### Anti-Oscillation Rule

Before re-spawning the diagnostician, compute the repair delta:
1. Compare repair instructions against the previous round: if substantively identical (>70% issue-type overlap) → repair oscillation.
2. On second oscillation (third repair with same issues): **halt repairs**, mark `COMPETING_SET — repair oscillation`, confidence ceiling ≤ 50. Document in `reasoning_chain.json` R8.

### Quality Gates (权威结束门 — 4 项)

| Gate | Requirement | Enforced By |
|------|-------------|-------------|
| **Judge Gate** | `verdict=="pass"` ∧ `overall_score>=90`，**或** `judge_repair_summary.json` 显示 3 轮耗尽（best-effort，标 `[BEST_EFFORT]`，confidence ≤70）| `artifact-check.mjs` |
| **Execution Proof** | `.pipeline_events.jsonl` valid per `pipeline-log-check.mjs` | `artifact-check.mjs` |
| **Evidence Closure** | Process + dual-drive + ontology interpretation all present | `evidence-closure-check.mjs` |
| **HTML Delivery** | `diagnostic-report.html` ≥ 5120 bytes ∧ `html_review.json` verdict=pass (除非 opt-out) | `artifact-check.mjs` |

**Judge-gated reporting rule**: Reporter launch requires EITHER (`verdict == "pass"` ∧ `overall_score >= 90`) OR a `judge_repair_summary.json` proving 3 repair rounds exhausted.

### Stability & Reproducibility

Final diagnosis must derive from deterministic artifacts. Unexplained primary-finding drift or confidence shifts >10 points between repeated runs is a Judge blocking issue. Confidence must be reproducible from `confidence.adjustment_log`, evidence ranks, and documented ceilings.

### 🛑 Path Stability Rules (跨环境安全)

| 规则 | 说明 |
|------|------|
| **绝对路径强制** | 所有传给子 Agent 的路径变量 (`SKILL_PATH`, `RUN_DIR`, `DATA_PATH`, `OUTPUT_HTML`) 必须使用绝对路径 |
| **Worktree 安全** | worktree 中 `SKILL_PATH` 必须指向主仓库的 skill 目录，而非 worktree 副本 |
| **空格安全** | 所有路径变量在 bash 中加双引号: `"$SKILL_PATH/scripts/..."` |
| **Python 路径锁定** | 所有 Python 脚本通过 `"$PYTHON_BIN"` 执行（Phase 1 锁定）|
| **产物路径一致性** | 子 Agent 的 `RUN_DIR` 必须与主管线创建的 `RUN_DIR` 完全一致 |

### 🛑 Agent Runtime Failure Recovery

Agent 执行失败是常态。每次启动子 Agent 后必须对以下场景做显式恢复：

| 触发条件 | 检测方式 | 恢复动作 |
|---------|---------|---------|
| RAG 引擎不可用 (localhost:8765 无响应) | `curl -s http://localhost:8765/docs` 失败或 context-builder 报告 `RAG_UNAVAILABLE` | 继续执行 — context-builder 用 `resources/parameter_to_physics.json` + 网络搜索。ontology.json 仍可构建 |
| uv Python venv 创建失败 | `uv_env_setup.mjs` 返回非零退出码 | 检查 `which uv`；无→安装 uv；已安装但失败→降级到系统 Python + `pip install requirements.txt` |
| 输入数据超大 (>500MB) | `inspect.mjs` 超时 > 300s | 运行 `file_inspect.py --sample 50000 <data_path>`，前 5 万行 + 均匀采样 5 万行做特征分析 |
| Agent 超时 (stall > 600s) | 系统返回 `Agent stalled` | 检查部分产物；有可用输出→继续；无→等待 60s 后重试 1 次；仍失败→标记 `[AGENT_TIMEOUT]` |
| API 连接断开 | 系统返回 `API Error` | 等待 30s 后重启同一 Agent；连续 2 次失败→标记 `[API_ERROR]` 并降级到本地脚本 |
| 产物文件缺失 | 每阶段完成后检查 expected outputs | ontology.json 缺失→主 Agent 用 `parameter_to_physics.json` 构建最小有效本体；diagnosis.json 缺失→标记 `[DIAGNOSIS_FAILED]` |
| Schema 验证失败 | `validate.mjs` 返回错误 | 将 schema 错误列表追加到 Agent 提示词，重启 1 次；仍失败→标记 `[SCHEMA_FAIL]` |
| 图片生成失败 (PNG 缺失) | `plot_verification.py` 失败 | **先按 cleaning_integrity_check.py + 修数据重画**（string-type 重定型 / raw 回退）；仍失败→`metadata_backed_inference` 须满足三准入条件（genuine 无数值结构 + 显式 reason + 非空 repair_attempts 链） |
| HTML 可视化失败 | HTML 不存在或 html-reviewer 未通过 | 重跑 `html-visualizer`；连续 2 次失败→仅交付 `report.md` + 标注 `HTML_DELIVERY_FAILED`（**禁止主 Agent 自己拼 HTML**）|
| Python 模块导入失败 | data-processor 报告 ModuleNotFoundError | 重跑 `uv_env_setup.mjs`；仍失败→检查 `pyproject.toml` 依赖完整性 |

**深层兜底**：上表恢复后仍失败 → 记录 `[RECOVERY_FAILED]` 事件 + 写部分产物（`_partial` 后缀）+ 向用户显式报告 + 用户决定跳过/终止。

---

## Phase-by-Phase Protocol

### Phase 1: Bootstrap (Main Agent, ~2 min)

合并原 Step 0 + Step 1 + Step 2.5。所有路径变量使用**绝对路径**。

```bash
# 1. Resolve SKILL_PATH (absolute, cross-platform safe)
SKILL_PATH="<absolute path to .claude/skills/industrial-deep-diagnostic>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"

# 2. Validate paths
[ -f "$SKILL_PATH/scripts/setup.mjs" ] || { echo "❌ setup.mjs not found" >&2; exit 1; }

# 3. Create run directory
SETUP_OUT=$(node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs")
RUN_DIR=$(echo "$SETUP_OUT" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{process.stdout.write(JSON.parse(s).run_dir||"")}catch(e){}})')
[ -d "$RUN_DIR" ] || { echo "❌ setup failed" >&2; echo "$SETUP_OUT" >&2; exit 1; }

# 4. Setup Python venv
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
PYTHON_BIN="$SKILL_PATH/scripts/.venv/bin/python"
[ -f "$PYTHON_BIN" ] || PYTHON_BIN="python3"

# 5. Inspect data (merged Step 1)
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
# → produces 00_input/input_manifest.json, 00_input/user_context.json, 00_input/run_config.json

# 6. Copy input data into 00_input/ and resolve clarification in auto mode (merged Step 2.5)
#    auto mode: infer unknown params via resources/physics_inference_framework.md L1-L5
#    Mark "clarification_status": "AUTO_RESOLVED" in 01_ontology/clarification_needed.json
#    (interactive mode: ask up to 4 questions; minimal: ask ≤2 critical only)
```

**Outputs**: `00_input/input_manifest.json`, `user_context.json`, `run_config.json`, `01_ontology/clarification_needed.json`. Store `SKILL_PATH`, `RUN_DIR`, `PYTHON_BIN` as session variables.

### Phase 2: Understand (Parallel 2 Sub-Agents, ~5 min)

并行启动两个子 Agent — 互不依赖：

```javascript
// 2a: context-builder
Agent({
  subagent_type: "context-builder",
  description: "Phase 2a: 构建领域本体 — RAG检索+本体+知识提取",
  permissionMode: "bypassPermissions",
  run_in_background: true,
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
INTERACTION_MODE=auto
Read "${SKILL_PATH}/agents/context-builder.md" and execute the complete protocol.`
})

// 2b: data-preprocessor (Phase 0 + Phase 1 of data-processor.md)
Agent({
  subagent_type: "data-processor",
  description: "Phase 2b: 数据预处理 — 清洗+特征摘要+稳态检测",
  permissionMode: "bypassPermissions",
  run_in_background: true,
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
PHASE_LIMIT=preprocess
Execute ONLY Phase 0 (data understanding) + Phase 1 (data preprocessing) of agents/data-processor.md.
Run cleaning_integrity_check.py + production_regime_detector.py. Stop after feature_summary.json is written.
Do NOT run statistical analysis, visualization, or VLM yet.`
})
```

**等待**: 两个 Agent 都完成。

**主 Agent 汇合** (ontology-guided analysis selection):
1. Read `01_ontology/ontology.json` → 确定参数物理分组
2. Read `02_processed/feature_summary.json` → 确定哪些参数值得分析
3. Write `02_processed/analysis_parameter_selection.json` (Phase 0.4 tier assignments)

### Phase 3: Analyze (Sub-Agent: `data-processor`, ~8 min)

启动 data-processor（执行剩余 phase — 统计分析 + 可视化 + VLM）：

```javascript
Agent({
  subagent_type: "data-processor",
  description: "Phase 3: 统计分析 + 可视化 + VLM 视觉分析",
  permissionMode: "bypassPermissions",
  run_in_background: true,
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
PHASE_LIMIT=analyze
Continue from Phase 2 (statistical pipeline) onward. Read agents/data-processor.md Phase 2-4.
ontology.json + analysis_parameter_selection.json already exist.
MUST run plot_verification.py before VLM delegation.
MUST write data_analysis_conclusion.json (V2 schema).`
})
```

**关键编排约束**：
- **v6.5 稳态过滤**：Phase 2 统计分析前用 `production_regime_filter.json` 过滤 startup/shutdown/transition
- **v6.4 时滞补偿**：process→quality 有物理延迟时跑 `time_lag_compensator.mjs`
- **v6.6 批次完整性**：batch_id 列存在时跑 `cleaning_integrity_check.py` 检测 split/duplicate
- **v6.7 留一法**：|r|≥0.3 相关必须过 leave-one-out
- **V2 handoff**：data_analysis_conclusion.json 必须用 V2 schema（每条 finding 有稳定引用 ID，下游诊断直接读此文件不再重读原始文件）

**Before Phase 4**, stabilize outputs:
```bash
node "$SKILL_PATH/scripts/normalize-anomaly-report.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/synthesize-data-analysis-conclusion.mjs" "$RUN_DIR"  # 合并 V2 字段
```

**Outputs**: `02_processed/` (feature_summary, validate_report, anomaly_report, time_lag_analysis, physics_check, data_analysis_conclusion_v2), `03_figures/*.png` + `plot_manifest.json` + `visual_analysis.json`.

### Phase 4: Diagnose (Sub-Agent: `diagnostician`, ~7 min)

```javascript
Agent({
  subagent_type: "diagnostician",
  description: "Phase 4: 物理约束的竞争假说根因诊断",
  permissionMode: "bypassPermissions",
  run_in_background: true,
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
REPAIR_INSTRUCTIONS=${REPAIR_INSTRUCTIONS:-}
Read "${SKILL_PATH}/agents/diagnostician.md" (V2) and execute Phase 0-4.
Trust data_analysis_conclusion.json (V2) as primary handoff — read only 3 core files + conditional 3.`
})
```

**V2 信任交接**：diagnostician 必读只 3 个文件 — `data_analysis_conclusion.json`, `ontology.json`, `visual_analysis.json`。条件必读 3 个 — `validate_report.json`, `time_lag_analysis.json`, `anomaly_report.json`（仅当 V2 handoff 中某结论需要深入验证时）。

**Outputs**: `04_diagnostics/diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json`. Agent 自验证 schema + 运行 `diagnostic-quality-check.mjs`。

### Phase 5: Deliver + Audit (Parallel 3 Sub-Agents, ~8 min)

并行启动 3 个子 Agent — 消费同一份 Phase 4 产物：

```javascript
// 5a: judge (7 项评分, 从 10 项精简)
Agent({subagent_type: "judge", run_in_background: true,
  prompt: `RUN_DIR=${RUN_DIR} SKILL_PATH=${SKILL_PATH} DATA_PATH=${DATA_PATH}
Read "${SKILL_PATH}/agents/judge.md" (V2). Cross-reference audit (4 checks) + 7 criteria scoring.`})

// 5b: reporter
Agent({subagent_type: "reporter", run_in_background: true,
  prompt: `RUN_DIR=${RUN_DIR} SKILL_PATH=${SKILL_PATH}
Read "${SKILL_PATH}/agents/reporter.md". Use visual_analysis.json as primary figure evidence.
Generate report.md (9-section pyramid) + run_summary.json.`})

// 5c: html-visualizer
Agent({subagent_type: "html-visualizer", run_in_background: true,
  prompt: `RUN_DIR=${RUN_DIR} SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed VISUAL_MODE=story
Read "${SKILL_PATH}/agents/html-visualizer.md" and execute the complete protocol.`})
```

**协调规则**：
- judge 完成 → 若 `pass` → reporter 的 report.md 直接发布
- judge 完成 → 若 `fail` → best-of-3 修复（回到 Phase 4）
- html-visualizer 不受 judge 阻塞（report 最终确认前可生成草稿 HTML）
- **judge 完成后串行启动**：report-reviewer + html-reviewer

```javascript
// 5d (after judge): report-reviewer — 物理真相审计 + raw data spot-check
Agent({subagent_type: "report-reviewer", run_in_background: true,
  prompt: `RUN_DIR=${RUN_DIR} SKILL_PATH=${SKILL_PATH} DATA_PATH=${DATA_PATH}
Read "${SKILL_PATH}/agents/report-reviewer.md" (V2). Step 1: raw data spot-check.
Step 2: physical truth audit. Step 3: cross-agent consistency.`})

// 5e (after html-visualizer): html-reviewer
Agent({subagent_type: "html-reviewer", run_in_background: true,
  prompt: `RUN_DIR=${RUN_DIR} SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html AUDIENCE=mixed
Read "${SKILL_PATH}/agents/html-reviewer.md" and execute the review protocol.`})
```

### Phase 6: Finalize (Main Agent, ~1 min)

```bash
node "$SKILL_PATH/scripts/evidence-closure-check.mjs" "$RUN_DIR" --write
node "$SKILL_PATH/scripts/artifact-check.mjs" "$RUN_DIR" "$SKILL_PATH"
```

`artifact-check.mjs` 是权威结束门（替代原 9 个 CP）。任一 critical gap → 标记为 blocked/repair-needed run。

**Present to user**: executive summary, diagnosis type (`DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`), confidence, recommendations, optimizer highlights, workspace path, HTML path.

---

## Agent Decoupling

Agents communicate ONLY through workspace files — never through the main agent's context:

```
Context Builder    ──► 01_ontology/ontology.json, schema.json, rag_deep_understanding.json
Data Preprocessor  ──► 02_processed/cleaned_data.{csv,json}, feature_summary.json,
                       production_regime_filter.json, data_quality_report.json (cleaning_integrity)
Data Processor     ──► 02_processed/data_analysis_conclusion.json (V2 handoff — 单一交接面)
                   ──► 02_processed/{validate_report, anomaly_report, time_lag_analysis, physics_check}.json
                   ──► 03_figures/*.png + plot_manifest.json + visual_analysis.json
Diagnostician      ──► 04_diagnostics/{diagnosis, evidence, confidence, reasoning_chain}.json
Judge              ──► 05_review/judge_feedback.json (+ best_round snapshots)
Reporter           ──► report.md, run_summary.json
Report Reviewer    ──► optimizer.md
HTML Visualizer    ──► diagnostic-report.html
HTML Reviewer      ──► 05_review/html_review.json
```

**Phase 2 + Phase 5 并行** — agent 解耦机制（仅通过文件通信）天然防竞争。

---

## Schema-First Writing Protocol

**Before writing any structured file**, read the matching schema first — construct content to the schema, write once, validate immediately.

| Phase | File | Schema(s) to Read First |
|------|------|-------------------------|
| Phase 1 | `input_manifest.json`, `run_config.json` | `run_config_schema.json` |
| Phase 2 | `ontology.json` | `ontology_schema.json` |
| Phase 3 | `data_analysis_conclusion.json` | **`data_analysis_conclusion_v2_schema.json`** |
| Phase 3 | `visual_analysis.json` | `visual_analysis_schema.json` |
| Phase 4 | `diagnosis.json`, `evidence.json`, `confidence.json`, `reasoning_chain.json` | matching schemas |
| Phase 5 | `judge_feedback.json`, `run_summary.json`, `html_review.json` | matching schemas |

**Rule**: Read schema → construct → write once → validate. Never write first and validate after.

---

## Evidence Hierarchy & Anti-Speculation

(See `resources/evidence_rules.md` for full rules, causation criteria, and language templates.)

| Rank | Source | Label |
|------|--------|-------|
| 1 | Direct measurements in data | `[Evidence Rank 1]` |
| 2 | User-provided documentation | `[Evidence Rank 2]` |
| 3 | Statistical analysis (validated) | `[Evidence Rank 3]` |
| 4 | Visual evidence (VLM-extracted) | `[Evidence Rank 4]` |
| 5 | Established process logic | `[Evidence Rank 5]` |
| 6 | External web references | `[Evidence Rank 6] [EXTERNAL]` |
| 7 | Hypotheses (unsupported) | `[Evidence Rank 7]` |

**核心反假相关检查（机器确定性执行，下游信任）：**
- Lag correlations require time-sorted data
- Aggregate correlations reverse within subgroups (Simpson) — always check stratified
- Trending variables share time as confounder — check detrended r
- Single-batch leverage — |r|≥0.3 MUST pass leave-one-out (|Δr|>0.2 → `leverage_driven`)
- Unknown parameter meanings → `[PARAM_AMBIGUITY]`
- Competing hypotheses with identical observables → `COMPETING_SET`, ceiling 65
- Physics-free correlations → `STATISTICAL_ONLY`, not a diagnosis
- Duplicate/split batch records — verify batch_id uniqueness
- RAG knowledge is suggestive, not authoritative
- Every conclusion needs a falsification condition

---

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline (Phases 1-6) |
| `/industrial-deep-diagnostic analyze` | Skip intake, run from Phase 2 |
| `/industrial-deep-diagnostic review` | Re-run judge on existing results |
| `/industrial-deep-diagnostic report` | Regenerate report from existing artifacts |
| `/industrial-deep-diagnostic audit` | Run report-reviewer only |

---

## Developer QA

For full bash command reference and statistical validation framework, see `pipeline-execution.md`. For implementation details not needed during execution, see project-level `CLAUDE.md`.
