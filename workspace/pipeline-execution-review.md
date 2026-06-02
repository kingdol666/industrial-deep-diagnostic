# Industrial-Deep-Diagnostic 执行流程审查报告

**审查日期**: 2026-06-02
**审查范围**: 全部 6 个 agent 文件 + SKILL.md + pipeline-execution.md + 11 个 schema + 5 个 template + 10 个脚本
**方法**: 逐步骤输入输出契约追踪 + 跨步骤一致性验证 + schema 对齐检查

---

## 总览

| 类别 | 发现数量 |
|------|:---:|
| 🔴 阻塞性问题 (会导致执行失败或产出错误结果) | **7** |
| 🟡 警告 (可能出问题但不一定阻塞) | **5** |
| 🟢 建议优化 | **4** |

---

## 🔴 阻塞性问题

### B1: Reporter 不验证 run_summary.json — 但 schema 要求 4 个字段模板缺失

**文件**: `agents/reporter.md` + `templates/run_summary_template.json` + `schemas/run_summary_schema.json`

**问题**: `templates/run_summary_template.json` 缺少 schema 要求的 4 个必填字段：
- `timestamp` (schema 要求, 但模板用的是 `run_timestamp`)
- `pipeline_steps_completed` (schema 要求, 模板完全缺失)
- `diagnosis_type` (schema 要求, 模板完全缺失)
- `judge_verdict` (schema 要求的是 `{score, verdict}` 对象, 模板用的是字符串)

**影响**: 每次 Step 6 都会因 schema 验证失败而需要重写 run_summary.json。这是我们在 BOPET 诊断中实际遇到的 bug——修复了 3 次才通过验证。

**修复**: 将 `templates/run_summary_template.json` 与 schema 对齐，或者把 schema 改为与模板匹配。

### B2: data-processor 要求编写 3 个 Python 脚本，但每次都从零开始

**文件**: `agents/data-processor.md` 第 101、162、489 行

**问题**: Data processor agent 需要为每个诊断场景从零开始编写 `preprocess.py`、`anomaly_detection.py`、`visualize.py`。这种方法：
1. 浪费 token（上述 BOPET 诊断中，3 个脚本各自约 50-200 行）
2. 容易出错（异常检测脚本 bug 修复了 2 次）
3. 每次执行间行为不一致

**建议**: 将 `stats_analysis.py` 作为模板——将 `preprocess.py`、`anomaly_detection.py`、`visualize.py` 预置为 scripts/ 中的模板脚本，通过 CLI 参数（`--target-cols`、`--group-col` 等）接收列名。data-processor agent 只需要调用脚本而不需要编写它们。

### B3: Diagnostician Phase 0 要求加载 `parameter_to_physics.json` 但它被标记为 "pattern library, not lookup table"

**文件**: `agents/diagnostician.md` Phase 0 的 CRITICAL 文件列表

**问题**: diagnostician.md 将 `parameter_to_physics.json` 列为 CRITICAL（缺失即停止），但同时标签为 "PATTERN LIBRARY — not a lookup table"。这种矛盾会让诊断师困惑：
1. 如果 CRITICAL 表示"必须读取"，但只是 pattern library —— 为什么是 CRITICAL？
2. 如果缺失则停止，但在之前的方案中，物理检查自动执行 0 次也继续运行

**建议**: 将 `parameter_to_physics.json` 降级为 IMPORTANT（缺失时继续但降低置信度）。

### B4: Reporter 在 Step 3 生成的 run_summary.json 结构与 schema 不同

**文件**: `agents/reporter.md:290-318` (Step 3: Generate Run Summary)

**问题**: Reporter 模板指定了 `run_summary.json` 的 JSON 结构（第 291-318 行），但这个结构与 `schemas/run_summary_schema.json` 不一致：
- Reporter 使用 `run_timestamp`，schema 要求 `timestamp`
- Reporter 使用 `primary_diagnosis`（字符串），schema 要求 `diagnosis_type`（枚举）
- Reporter 使用 `judge_score` 和 `judge_verdict`（分拆），schema 要求 `judge_verdict`（`{score, verdict}` 对象）
- Reporter 使用 `validation_summary`，schema 要求 `pipeline_steps_completed`（数组）

**影响**: 每次 reporter 完成都需额外的验证修复循环。BOPET 诊断中这浪费了约 3 轮修正。

**修复**: 将 reporter 模板和 schema 对齐到同一套字段。选择一个作为权威，另一个对齐。

### B5: data-processor 内部分步编号与管线步骤冲突

**文件**: `agents/data-processor.md`

**问题**: Data processor（管线 Step 3）内部使用"Step 1-6"的命名。但管线已在 SKILL.md 中定义了 Step 0-8。这导致：
1. Data processor 提到 "Step 4.1（Enhanced Stats）"时，不清楚这是内部的 Step 4 还是管线的 Step 4
2. "Step 5（Automated Physical Feasibility Checks）" 有双重含义
3. 输出文件注释中的 "← Step 1.2" 等标签含糊不清

| data-processor 内部编号 | 实际管线步骤 |
|------------------------|:----------:|
| Step 1, 2, 3, 4, 5, 5.5, 6 | 全部在管线 Step 3 中 |

**修复**: 将 data-processor.md 的内部编号改为字母（Phase A-G），或明确前缀（DP-Step-1 etc）。

### B6: Judge 评分标准引用不存在的 criteria_scores 子字段

**文件**: `agents/judge.md:300-310` (Step 3: Generate Feedback)

**问题**: Judge 的反馈 JSON 模板使用了 10 个 criteria 名称（如 `data_quality_awareness`、`variable_classification`...），但 `schemas/judge_feedback_schema.json` 的 `criteria_scores` 是一个自由格式的对象（没有限制子字段名称），意味着：
- Schema 不会因为字段名拼写错误而拒绝
- 但也没有确保 judge 使用了正确的 10 个标准名称
- 特别是：`judge_feedback_schema.json` 本身没有 `properties` 键，这意味着 schema 依赖于 `additionalProperties`（默认允许）

**建议**: 在 schema 中明确定义 criteria_scores 的 expected keys，或者至少在 judge.md 中更明确地定义这 10 个字段。

### B7: resolve of physics_check.py 0次检查的处理逻辑不完整

**文件**: `agents/data-processor.md:274`

**问题**: 当 physics_check.py 执行 0 次检查时，data processor 的指令是：
> 在 scenario_classification.json 中标注 `"physics_auto_checks": 0`
> 在异常报告中记录 `"physics_manual_verification_needed": true`

但 scenario_classification_schema.json 中没有 `physics_auto_checks` 字段，anomaly_report_schema.json 中也没有 `physics_manual_verification_needed` 字段。这意味着添加这些字段会因 `additionalProperties: false` 而导致 schema 验证失败。

**修复**: 要么将这些字段添加到对应的 schema 中，要么在 agent 输出中的其他地方（如 `data_quality_report.json`）记录此信息。

---

## 🟡 警告

### W1: Reporter 的两处 run_summary 参数来源不一致

**文件**: `agents/reporter.md:290` vs `SKILL.md:261`

**问题**: SKILL.md 说 `Validate: node ... run_summary_schema.json ... run_summary.json`。但 Reporter 的 Step 3 既生成也验证 run_summary.json。SKILL.md 中的验证命令是多余的（Reporter 已在其内部步骤中包含了验证逻辑）。

### W2: Step 2.5 (Clarification Gate) 在 auto 模式下的 auto-inference 没有明确的 fallback

**文件**: `SKILL.md` 和 `pipeline-execution.md §Step 2.5`

**问题**: Auto 模式跳过所有澄清问题，但没有规定当 `physical_meaning_confidence: UNKNOWN` 的参数在 auto-inference 后仍无法确定时的行为。应该有一个标记机制，比如 `[AUTO_INFERRED_WITH_LOW_CONFIDENCE]`，告诉下游步骤这些参数的物理意义不可靠。

### W3: 上下文构建器的 RAG 回退路径没有被量化

**文件**: `agents/context-builder.md` Phase 3

**问题**: Context builder 有 RAG fallback（"如果 RAG unavailable → 从零构建本体"），但没有规定何时应该放弃 RAG 并切换到回退。对 RAG 引擎的多次失败调用会导致时间浪费。

### W4: Report reviewer 的独立统计检查代码片段使用了硬编码列名

**文件**: `agents/report-reviewer.md:226-262` (Step 2.1: Python 代码块)

**问题**: Reviewer 的独立数据采样 Python 代码包含 `['key_param_1', 'key_param_2']` 和 `['defect_1', 'defect_2']` —— 通用占位符，但在 `'product_model'` vs `'product_grade'` 的列名检测中也直接假定了 `ts_start` 作为时间列。这些假定可能在非标准列名时失败。

**建议**: 改为让 reviewer 从 ontology.json 读取实际的列名，而不是使用硬编码占位符。

### W5: Reasoning chain 的 `falsification_condition` 在某些 steps 中可能为空

**文件**: `schemas/reasoning_chain_schema.json`

**问题**: Schema 将 `falsification_condition` 设为必填，但 diagnostician 的 R1 和 R2（数据特征描述、统计发现描述）本身就没有可证伪的结论——它们是纯粹的观测性步骤。强迫每个步骤都有 `falsification_condition` 会导致填充无意义的占位符。

**建议**: 将 `falsification_condition` 设为可选字段，或允许空字符串（`""`）。

---

## 🟢 优化建议

### S1: 合并冗余的验证步骤

**当前**: Step 3 验证 3 个 schema → Step 4 验证 4 个 schema → Step 5 验证 1 个 schema → Step 6 验证 1 个 schema

**建议**: 在 SKILL.md 中集中列出所有验证命令为表格，减少 agent 文件中的重复。

### S2: 为 Python 脚本添加 `--dry-run` 模式

**建议**: `physics_check.py` 和 `stats_analysis.py` 应该支持 `--dry-run`，只报告它们**会**执行哪些检查而不实际运行。这允许 data processor 在运行完整的物理检查之前先检查覆盖率。

### S3: 添加 `pipeline_check.sh` 快速健康检查脚本

**建议**: 在 scripts/ 中添加一个小脚本，在执行任何步骤前检查所有先决条件：数据文件存在、Python venv 可用、RAG 引擎在线、列名不为空。在 Step 0 执行时调用。

### S4: diagnostic_template.json 应改为抽象模板

**当前**: `templates/diagnosis_template.json` 充满 BOPET 特定的列名和物理链——这不是模板，是示例。

**建议**: 将模板改为 `{{parameter_name}}`-风格的占位符。将当前内容移至 `examples/bopet_film_diagnosis_output.json`。

---

## 管线执行流程图（带问题标注）

```
Step 0: Setup ═════════════════════════════════════════════════════ ✅
  node setup.mjs → 创建目录结构 ✅
  node uv_env_setup.mjs → Python venv ✅
  └─ ⚠️ 缺少 pipeline_check.sh 快速健康检查

Step 1: Inspect ════════════════════════════════════════════════════ ✅
  node inspect.mjs → input_manifest.json ✅
  手动创建 user_context.json ✅
  └─ ⚠️ user_context.json 没有 schema 验证

Step 2: Context Build ══════════════════════════════════════════════ ⚠️
  Skill(rag-knowledge-builder) → RAG 本体草稿 ⚠️ (RAG 不可靠)
  Phase B: Web 搜索 ⚠️ (无数量限制或超时)
  Phase C: 双向数据↔本体映射 ✅
  Phase D: 输出 ontology.json + schema.json ✅ (schema 验证)
  └─ 🔴 B3: parameter_to_physics.json 是 CRITICAL 但也是 pattern library

Step 2.5: Clarify ══════════════════════════════════════════════════ ⚠️
  auto 模式跳过所有问题 ✅
  └─ 🟡 W2: UNKNOWN 参数的 auto-inference 无 fallback 标记

Step 3: Data Processing ════════════════════════════════════════════ 🔴
  转换数据 → 预处理 → 统计分析 🔴 B2: 需要编写 3 个 Python 脚本
  └─ stats.mjs (或 Python fallback) ✅
  └─ stats_validate.mjs ✅
  异常检测 → 转变分析 ⚠️
  physics_check.py 🔴 B7: 0 次检查时写 schema 不支持的字段
  └─ 🔴 B5: 内部步骤编号与管线步骤冲突
  RAG Stage 2 验证 ✅
  场景自适应可视化 ✅
  └─ 验证: 3 个 schema ⚠️ (scenario_classification_schema 无 physics_auto_checks)

Step 4: Diagnostician ═════════════════════════════════════════════ ⚠️
  Phase 0: 加载 12 个证据文件 ✅
  Phase 1: 第一原理物理 L1-L5 ⚠️ (模板示例全是 CNC/振动)
  Phase 1.5: 证明构造 ✅
  Phase 3: 候选参数筛选 ✅
  Phase 4: 5 步竞争假设 ✅
  Phase 6: 写入 4 个文件 + 验证 4 个 schema ⚠️ (JSON 转义 bug 历史)
  └─ 🔴 B3: CRITICAL vs pattern library 矛盾

Step 5: Judge ═════════════════════════════════════════════════════ 🔴
  Step 0.5: 交叉引用 validate_report ✅
  Step 0.6: 审计推理链 ✅
  Step 0.65: 物理来源质量审计 ✅
  Step 0.7: 独立数据抽样 ✅ (但内嵌代码使用硬编码列名 🟡 W4)
  Step 1: 10 条标准评分 ✅
  Step 3: 写入 judge_feedback.json 🔴 B6: schema 无 criteria 验证
  └─ 🔴 如果 PASS: continue → Step 6
  └─ 🔴 如果 NEEDS_REPAIR: 重新生成 Step 4 (max 3 次)

Step 6: Reporter ═════════════════════════════════════════════════ 🔴
  Step 0: 加载所有构件 ✅
  Step 1: 读取所有图 ✅ (image_captions.json 作为主源)
  Step 1.5: 合成推理链 ✅
  Step 2: 生成 report.md ✅
  Step 3: 生成 run_summary.json 🔴 B1 + B4: schema 不匹配
  └─ 🟡 W1: SKILL.md 中的重复验证命令

Step 7: Audit ════════════════════════════════════════════════════ ⚠️
  Step 1: 物理机制验证 ✅
  Step 1.1b: RAG 知识交叉检查 ✅
  Step 1.2: 推理链审计 ✅
  Step 2: 混杂变量检测 ⚠️ (Python 片段使用硬编码列名 🟡 W4)
  Step 3: 统计谬误审计 ✅
  Step 5: 输出 optimizer.md ✅
  └─ 如果 ENDORSED: → Step 8
  └─ 如果 CONDITIONAL/REJECTED: 重新生成 Step 4 (max 2 次)

Step 8: Present ═══════════════════════════════════════════════════ ✅
  node artifact-check.mjs ✅
  └─ 总是需要 schema.json (我们为此手动创建了一个桩)
```

---

## Schema-Template-Output 三对齐问题汇总

| 场景 | Schema 要求 | 模板提供 | Agent 生成 | 状态 |
|------|-----------|--------|-----------|:---:|
| diagnosis.json | `run_id, diagnosis_time, diagnosis_type, primary_finding, hypotheses` | ✅ 全部匹配 | ✅ | 🟢 对齐 |
| run_summary.json | `run_id, scene_name, timestamp, pipeline_steps_completed, diagnosis_type, judge_verdict` | ❌ 缺少 `timestamp, pipeline_steps_completed, diagnosis_type, judge_verdict` | ❌ 使用 `run_timestamp, primary_diagnosis` | 🔴 需修复 |
| judge_feedback.json | `overall_score, verdict, criteria_scores, blocking_issues` | ✅ 但 criteria 是自由形式 | ✅ | 🟢 基本对齐 |
| confidence.json | `run_id, diagnosis_time, confidence_breakdown, overall_confidence, adjustment_log` | N/A (无 confidence 模板) | ✅ | 🟡 需添加模板 |
| reasoning_chain.json | `run_id, reasoning_chains, uncertainty_summary` + 每个链: 9 个字段 | N/A (无 reasoning_chain 模板) | ✅ | 🟡 需添加模板 |

---

## 总体评分

| 维度 | 评分 | 说明 |
|------|:---:|------|
| 步骤定义清晰度 | 8/10 | 基本的输入输出契约已定义 |
| 跨步骤一致性 | 6/10 | 多个 schema-template-output 不匹配 |
| Agent 自包含性 | 7/10 | 除 data-processor 编写 3 个脚本外，其余都可自包含 |
| 脚本可执行性 | 8/10 | 10/10 脚本存在，physics_check 已去 CNC |
| Schema 覆盖率 | 9/10 | 11/11 输出类型有 schema |
| 修复合约可用性 | 7/10 | 定义了 max 迭代，但修复触发器存在一些缺陷 |
| **综合执行流程评分** | **7.5/10** | 结构合理但需要 schema 对齐和脚本预置 |

**关键结论**: 管线逻辑是正确的，步骤顺序是合理的。**最大的 bug 是多个 schema 与 agent 输出格式不匹配**——这会导致每次执行需要 1-3 轮额外的"验证失败→重写"循环。通过修复上述 7 个阻塞性问题，可以将管线从 "7.5/10 需要重试" 提升到 "9/10 一次执行成功"。
