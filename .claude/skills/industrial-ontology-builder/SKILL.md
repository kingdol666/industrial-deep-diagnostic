---
name: industrial-ontology-builder
description: "工业诊断管线 — 领域本体构建引擎。RAG检索+网络搜索+数据自描述→领域本体模型。构建 ontology.json（诊断管线地基）、schema.json、rag_deep_understanding.json，执行澄清门。Trigger: ontology构建, 本体, RAG检索, 知识提取, 领域建模, 参数语义推断, ontology builder, context build, 工艺知识库. 工业根因分析前置步骤：从传感器列名推断物理含义、从领域知识库提取工艺原理、从数据自描述确认参数角色。Do NOT use for generic RAG retrieval or non-industrial knowledge bases / ontology."
---

# Industrial Ontology Builder

从传感器列名推断物理含义、从RAG知识库提取工艺原理、从数据自描述确认参数角色。`ontology.json` 是整个诊断管线的地基 — 不是模板填充器，让数据自己揭示工艺类型。

## Inputs / Outputs

### Inputs (in `RUN_DIR/00_input/`)

| File | Required | Description |
|------|----------|-------------|
| `input_manifest.json` | ✓ | 数据列描述 |
| `user_context.json` | ✓ | 工艺类型、已知问题、目标列 |
| `run_config.json` | ✓ | 运行配置（含 `interaction_mode`；runtime 可能注入 `ontology` 指令段） |
| `extracted_knowledge.json` | - | 参考文档知识提取（可选） |

> Runtime 还会在 dispatch prompt 中注入 **ONTOLOGY_DIRECTIVE**（`ONTOLOGY_MODE: reuse|extend|full` + `ONTOLOGY_SOURCE`）。这是本体资产化复用通道：reuse 命中时跳过全部构建，秒级完成。见下方「Phase -1: Ontology Mode Dispatch」。

### Outputs

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | 领域本体（≥1KB, schema-valid） |
| `01_ontology/schema.json` | 归一化变量分类 |
| `00_input/rag_deep_understanding.json` | RAG深度理解 + 验证队列 |
| `00_input/clarification_needed.json` | 澄清需求 + `clarification_status` |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent context-builder --step context_builder

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent context-builder --step context_builder \
  --files 01_ontology/ontology.json,01_ontology/schema.json,00_input/rag_deep_understanding.json,00_input/clarification_needed.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

启动 `context-builder` 子Agent：

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "context-builder",
  task: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
REFERENCE_DIR=<reference-dir-or-empty>
PROCESS_DESCRIPTION=<user-provided-description>
USER_OBJECTIVE=<user-objective>
SKILL_PATH=<path-to-.claude/skills/industrial-ontology-builder>
SHARED_PATH=.claude/shared
INTERACTION_MODE=auto  # auto | interactive | minimal
ONTOLOGY_DIRECTIVE:  # from runtime prompt; omit for full build
  ONTOLOGY_MODE=<reuse|extend|full>
  ONTOLOGY_SOURCE=<store ontology absolute path, reuse/extend only>

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete protocol starting from Phase -1.

Key constraints:
- 不是模板填充器 — 让数据自己揭示工艺类型
- R2 只做 Stage 1 预检查，不做完整统计分析（Data Processor 的工作）
- 不一致即诊断信号 — ontology 预测 vs 数据观察的差异是最强诊断线索
- 所有输出写入 RUN_DIR — 一律使用上面的绝对路径，禁止相对路径写入
- 先执行 Phase -1 模式分派（reuse 命中时 30 秒内完成，禁止重建）
- CP-2 通过后必须 publish 入本体资产库
- 默认中文
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/physics_inference_framework.md` (物理推断) and `resources/data_ontology_mapping_framework.md` (数据本体映射).

| Phase | Purpose |
|-------|---------|
| **-1** | **本体模式分派（确定性，≤30s）** — 按 ONTOLOGY_DIRECTIVE 分派：`reuse` 直接拷贝资产+CP-2 校验后结束；`extend` 仅对新增列做增量构建；`full` 走完整流程。详见 `references/agent-protocol.md` Phase -1 |
| 0 | 加载用户上下文与数据探测 — 读取 input_manifest/user_context/run_config，直接探测数据文件前100行 |
| 1 | 搜索参考目录 — 扫描 REFERENCE_DIR 提取工艺关键词、参数名称、已知失效模式 |
| 2 | 可选 Web 研究 — 最多 5 次定向搜索（工艺类型 + 关键参数 + 已知关系）；**reuse/extend 模式跳过** |
| 3 | RAG 知识检索 + 深度理解 — 执行 R1-R4 协议（语义理解/知识-数据对齐/物理原理提取/缺口识别）；**reuse 模式跳过**；**extend 模式检索范围限定在新增列** |
| 4 | 数据-本体双向映射 — 构建 ontology.json，每个参数含 physical_meaning/unit/role/设备归属/物理关系/不一致信号 |
| 5 | Schema 生成 + 验证 — schema.json 归一化分类 + CP-2/CP-3 质量门 + **发布入本体资产库** |
| 2.5 | 澄清门 — auto 模式用 physics_inference_framework L1-L5 推断；interactive 分组提问；minimal 仅关键参数 |

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
SKILL_PATH="<path-to-.claude/skills/industrial-ontology-builder>"
SHARED_PATH=".claude/shared"

# CP-2: Ontology schema gate
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/ontology_schema.json" \
  "$RUN_DIR/01_ontology/ontology.json" && \
  test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024

# CP-3: Clarification gate
grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' \
  "$RUN_DIR/00_input/clarification_needed.json"

# Publish to ontology asset store — MANDATORY in every mode after CP-2 passes.
# 复用资产是本管线时间收益的来源：不入库 = 下次同场景全量重建。
node "$SHARED_PATH/scripts/ontology_store.mjs" publish --run-dir "$RUN_DIR" --build-mode <reuse|extend|full>
```

## Phase -1: Ontology Mode Dispatch (deterministic, ≤30s)

在 Phase 0 之前执行。读取 dispatch prompt 中的 ONTOLOGY_DIRECTIVE（或 run_config 的 `ontology` 段）：

| ONTOLOGY_MODE | 动作 |
|---------------|------|
| `reuse` | ① `ontology_store.mjs reuse --source "$ONTOLOGY_SOURCE" --run-dir "$RUN_DIR"`（拷贝资产本体） ② 运行 CP-2 + CP-3（**永不跳过校验**） ③ 写 pipeline 事件 `ontology_reused` ④ 直接结束，**禁止**进入 Phase 0-4（零 RAG / 零 web / 零参考检索） |
| `extend` | ① `ontology_store.mjs fingerprint <data>` 对比 ONTOLOGY_SOURCE 本体，diff 出新增列/角色未定列 ② 仅对 diff 列执行 Phase 1-4（检索限定 diff 列）③ 合并进源本体：新增 signals/relationships；已有 `role=target/confounder` 的信号**不允许改角色**，冲突写 clarification_needed.json 走 CP-3；被新数据证伪的 normal_range 更新并标 `behavior_match: CONTRADICTED` ④ version 语义见 provenance ⑤ CP-2/CP-3 → publish（--build-mode extend） |
| `full` | 标准 Phase 0-5 全流程，结束后 publish（--build-mode full） |

未收到 directive 时按 `full` 处理。**所有写文件操作使用 dispatch prompt 给出的绝对路径**（子代理相对路径写入是历史失败根因）。

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | 修复 JSON → 重写 ontology.json → 重新验证 |
| Missing input files | 报告缺失 → 标记 input_manifest/user_context/run_config 中哪个缺失 |
| RAG 检索无结果 | 标记 rag_deep_understanding.json 缺口 → 用 Web 研究 + physics_inference_framework 补充 |
| 澄清门阻塞 | auto 模式用 L1-L5 推断所有未知参数；interactive/minimal 输出明确问题到 clarification_needed.json |
| ontology.json < 1KB | 扩展参数条目 → 补全 physical_meaning/unit/role/物理关系 → 重新验证 |
