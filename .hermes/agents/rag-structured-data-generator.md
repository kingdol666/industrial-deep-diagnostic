# Agent: RAG Structured Data Generator (Phase 3)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/structured-data-generator.md` as its full execution protocol.

## Role
RAG Phase 3 — 本体到机器消费模板转换。生成示例数据、验证规则、查询模板等结构化产物。

## Hermes delegate_task Usage

```text
delegate_task(
    goal="执行 RAG Phase 3 结构化数据生成。读取 rag_ontology_draft.json 与 rag_ontology_nl_spec.md，输出 rag_structured_data.json。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 structured-data-generator 完整协议。\n完整协议文档见: SKILL_PATH/agents/structured-data-generator.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/structured-data-generator.md`
- Output boundary: write only inside `RUN_DIR/00_input`
