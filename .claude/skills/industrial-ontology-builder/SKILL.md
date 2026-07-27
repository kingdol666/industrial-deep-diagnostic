---
name: industrial-ontology-builder
description: "工业诊断管线 — RAG检索+网络搜索+数据自描述 → 领域本体构建。构建 ontology.json、rag_deep_understanding.json 并执行澄清门。Trigger: ontology构建, 本体, RAG检索, 知识提取, 领域建模, 参数语义推断, ontology builder, context build, 工艺知识库. Do NOT use for generic RAG or non-industrial knowledge bases."
---

# Industrial Ontology Builder

构建工业过程的领域本体模型——从传感器列名推断物理含义、从RAG知识库提取工艺原理、从数据自描述确认参数角色。产出 `ontology.json` 作为整个诊断管线的地基。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `00_input/input_manifest.json` | 数据列描述 |
| `00_input/user_context.json` | 用户上下文（工艺类型、已知问题、目标列） |
| `00_input/run_config.json` | 运行配置（含 `interaction_mode`） |
| `00_input/extracted_knowledge.json` | 参考文档提取的知识（可选） |

## Outputs

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | 领域本体（≥1KB, schema-valid） |
| `01_ontology/schema.json` | 本体概览 |
| `00_input/rag_deep_understanding.json` | RAG深度理解 + 验证队列 |
| `00_input/extracted_knowledge.json` | 参考文档知识提取 |
| `00_input/clarification_needed.json` | 澄清需求（含 `clarification_status`） |

## Execution

启动 `context-builder` 子Agent，执行完整的本体构建协议：

```javascript
Agent({
  subagent_type: "context-builder",
  description: "构建领域本体 — RAG检索+网络搜索+本体构建",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
REFERENCE_DIR=<reference-dir-or-empty>
PROCESS_DESCRIPTION=<user-provided-description>
USER_OBJECTIVE=<user-objective>
SKILL_PATH=<this-skill-directory>
INTERACTION_MODE=auto

Read "<this-skill-directory>/references/agent-protocol.md" and execute the complete protocol.
Phase 0: Load user context + data inspection
Phase 1: Search reference directory
Phase 2: Optional web research
Phase 3: RAG knowledge retrieval + deep understanding (four-step protocol)
Phase 4: Data↔Ontology bidirectional mapping
Phase 5: Schema generation + validation
Validate ontology_schema before completion.`,
  run_in_background: true
})
```

### Agent Protocol

子Agent 的完整执行协议见 `references/agent-protocol.md`。核心要点：
- **不是模板填充器** — 从数据自描述推导工艺特征，不套用固定行业模板
- **RAG 深度理解** — 四步协议：语义理解→知识-数据对齐→物理原理提取→缺口识别
- **双向映射** — 本体预测→数据确认；数据揭示→本体解释；差异=诊断信号

### Clarification Gate (Step 2.5)

行为取决于 `interaction_mode`：
- **`auto`**（默认）: 不询问用户。用 `physics_inference_framework.md` L1-L5 推断所有未知参数，标记 `"auto_inferred": true`
- **`interactive`**: 分组相关参数，每轮最多4个问题
- **`minimal`**: 仅提问CRITICAL参数（最多2个）

## Verification

```bash
SKILL_PATH="<this-skill-directory>"

# CP-2: Ontology gate
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/ontology_schema.json" \
  "$RUN_DIR/01_ontology/ontology.json" && \
  test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024

# CP-3: Clarification gate
grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' \
  "$RUN_DIR/00_input/clarification_needed.json"
```

## Failure Recovery

| 场景 | 恢复 |
|------|------|
| RAG 引擎不可用 (localhost:8765) | 继续 — 使用 `resources/parameter_to_physics.json` + 网络搜索 |
| ontology.json 缺失或 <1KB | 重新启动 context-builder |
| Schema 验证失败 | 重新启动 context-builder |
| 完全无输出 | 主 agent 用 `parameter_to_physics.json` 构建最小有效本体 |

## References

- `references/agent-protocol.md` — 完整的 context-builder 执行协议（Phase 0-5）
- `schemas/ontology_schema.json` — 本体 JSON Schema
- `resources/rag_deep_understanding_protocol.md` — RAG 四步深度理解协议
- `resources/physics_inference_framework.md` — 物理推断框架（L1-L5）
- `resources/parameter_to_physics.json` — 参数→物理量映射知识库
- `resources/data_ontology_mapping_framework.md` — 数据↔本体映射框架
