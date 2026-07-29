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
| `run_config.json` | ✓ | 运行配置（含 `interaction_mode`） |
| `extracted_knowledge.json` | - | 参考文档知识提取（可选） |

### Outputs

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | 领域本体（≥1KB, schema-valid） |
| `01_ontology/schema.json` | 归一化变量分类 |
| `00_input/rag_deep_understanding.json` | RAG深度理解 + 验证队列 |
| `00_input/clarification_needed.json` | 澄清需求 + `clarification_status` |

## Dispatch

启动 `context-builder` 子Agent：

```javascript
// OMP dispatch via task tool:
task({
  agent: "context-builder",
  task: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
REFERENCE_DIR=<reference-dir-or-empty>
PROCESS_DESCRIPTION=<user-provided-description>
USER_OBJECTIVE=<user-objective>
SKILL_PATH=.omp/skills/industrial-ontology-builder
SHARED_PATH=.omp/shared
INTERACTION_MODE=auto  # auto | interactive | minimal

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete protocol.

Key constraints:
- 不是模板填充器 — 让数据自己揭示工艺类型
- R2 只做 Stage 1 预检查，不做完整统计分析（Data Processor 的工作）
- 不一致即诊断信号 — ontology 预测 vs 数据观察的差异是最强诊断线索
- 所有输出写入 RUN_DIR
- 默认中文
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/physics_inference_framework.md` (物理推断) and `resources/data_ontology_mapping_framework.md` (数据本体映射).

| Phase | Purpose |
|-------|---------|
| 0 | 加载用户上下文与数据探测 — 读取 input_manifest/user_context/run_config，直接探测数据文件前100行 |
| 1 | 搜索参考目录 — 扫描 REFERENCE_DIR 提取工艺关键词、参数名称、已知失效模式 |
| 2 | 可选 Web 研究 — 最多 5 次定向搜索（工艺类型 + 关键参数 + 已知关系） |
| 3 | RAG 知识检索 + 深度理解 — 执行 R1-R4 协议（语义理解/知识-数据对齐/物理原理提取/缺口识别） |
| 4 | 数据-本体双向映射 — 构建 ontology.json，每个参数含 physical_meaning/unit/role/设备归属/物理关系/不一致信号 |
| 5 | Schema 生成 + 验证 — schema.json 归一化分类 + CP-2/CP-3 质量门 |
| 2.5 | 澄清门 — auto 模式用 physics_inference_framework L1-L5 推断；interactive 分组提问；minimal 仅关键参数 |

## Verification

```bash
SKILL_PATH=".omp/skills/industrial-ontology-builder"
SHARED_PATH=".omp/shared"

# CP-2: Ontology schema gate
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/ontology_schema.json" \
  "$RUN_DIR/01_ontology/ontology.json" && \
  test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024

# CP-3: Clarification gate
grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' \
  "$RUN_DIR/00_input/clarification_needed.json"
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | 修复 JSON → 重写 ontology.json → 重新验证 |
| Missing input files | 报告缺失 → 标记 input_manifest/user_context/run_config 中哪个缺失 |
| RAG 检索无结果 | 标记 rag_deep_understanding.json 缺口 → 用 Web 研究 + physics_inference_framework 补充 |
| 澄清门阻塞 | auto 模式用 L1-L5 推断所有未知参数；interactive/minimal 输出明确问题到 clarification_needed.json |
| ontology.json < 1KB | 扩展参数条目 → 补全 physical_meaning/unit/role/物理关系 → 重新验证 |
