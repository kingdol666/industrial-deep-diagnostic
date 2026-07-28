---
name: industrial-ontology-builder
description: "工业诊断管线 — 领域本体构建引擎。RAG检索+网络搜索+数据自描述→领域本体模型。构建 ontology.json（诊断管线地基）、schema.json、rag_deep_understanding.json，执行澄清门。Trigger: ontology构建, 本体, RAG检索, 知识提取, 领域建模, 参数语义推断, ontology builder, context build, 工艺知识库. 工业根因分析前置步骤：从传感器列名推断物理含义、从领域知识库提取工艺原理、从数据自描述确认参数角色。Do NOT use for generic RAG retrieval or non-industrial knowledge bases / ontology."
---

# Industrial Ontology Builder

从传感器列名推断物理含义、从RAG知识库提取工艺原理、从数据自描述确认参数角色。`ontology.json` 是整个诊断管线的地基。

## Inputs (`RUN_DIR/00_input/`)

| File | Required | Contents |
|------|----------|----------|
| `input_manifest.json` | ✓ | 数据列描述 |
| `user_context.json` | ✓ | 工艺类型、已知问题、目标列 |
| `run_config.json` | ✓ | 运行配置（含 `interaction_mode`） |
| `extracted_knowledge.json` | - | 参考文档知识提取（可选） |

## Outputs (`RUN_DIR/`)

| File | Contents |
|------|----------|
| `01_ontology/ontology.json` | 领域本体（≥1KB, schema-valid） |
| `01_ontology/schema.json` | 归一化变量分类 |
| `00_input/rag_deep_understanding.json` | RAG深度理解 + 验证队列 |
| `00_input/clarification_needed.json` | 澄清需求 + `clarification_status` |

## Agent Dispatch

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
INTERACTION_MODE=auto  # auto | interactive | minimal

Read "\${SKILL_PATH}/references/agent-protocol.md" and execute the complete protocol.
Phase 0-5: data inspection → reference search → web research → RAG retrieval → ontology build → validation`,
  run_in_background: true
})
```

## Verification

```bash
SKILL_PATH="<this-skill-directory>" SHARED_PATH="<shared-scripts-directory>"

# CP-2: Ontology schema gate
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/ontology_schema.json" \
  "$RUN_DIR/01_ontology/ontology.json" && \
  test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024

# CP-3: Clarification gate
grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' \
  "$RUN_DIR/00_input/clarification_needed.json"
```

## References

| Resource | When |
|----------|------|
| `references/agent-protocol.md` | context-builder 完整执行协议（Phase 0-5 + 澄清门 + 故障恢复） |
| `schemas/ontology_schema.json` | 本体 JSON Schema |
| `resources/physics_inference_framework.md` | 物理推断不确定时 |
| `resources/parameter_to_physics.json` | 参数→物理量映射知识库 |
| `resources/data_ontology_mapping_framework.md` | 数据↔本体映射 |
