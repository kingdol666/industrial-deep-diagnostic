# Agent: RAG Ontology Construction Agent (Phase 2)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/ontology-construction-agent.md` as its full execution protocol.

## Role
RAG Phase 2 — 领域本体构建。基于评分后的知识块构建结构化本体与自然语言规范。

## Hermes delegate_task Usage

```text
delegate_task(
    goal="执行 RAG Phase 2 本体构建。基于 rag_scored_chunks.json 和本体设计原则，构建 rag_ontology_draft.json 与 rag_ontology_nl_spec.md。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\nDOMAIN={DOMAIN}\nTARGET_CONCEPTS={TARGET_CONCEPTS}\nRELATED_CONCEPTS={RELATED_CONCEPTS}\nCONTEXT_DIMENSIONS={CONTEXT_DIMENSIONS}\n\n执行 ontology-construction-agent 完整协议。\n完整协议文档见: SKILL_PATH/agents/ontology-construction-agent.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/ontology-construction-agent.md`
- Output boundary: write only inside `RUN_DIR/00_input`
