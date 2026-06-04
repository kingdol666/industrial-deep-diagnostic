# Agent: RAG Quality Verification Agent (Phase 4)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/quality-verification-agent.md` as its full execution protocol.

## Role
RAG Phase 4 — 最终质量门。验证本体结构、自然语言规范、逻辑一致性和下游可消费性。

## Hermes delegate_task Usage

```text
delegate_task(
    goal="执行 RAG Phase 4 质量验证。读取 rag_ontology_draft.json、rag_ontology_nl_spec.md、rag_scored_chunks.json 与 rag_structured_data.json，输出 rag_audit_log.json 与最终 verdict。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\nDOMAIN={DOMAIN}\nTARGET_CONCEPTS={TARGET_CONCEPTS}\nRELATED_CONCEPTS={RELATED_CONCEPTS}\nCONTEXT_DIMENSIONS={CONTEXT_DIMENSIONS}\n\n执行 quality-verification-agent 完整协议。\n完整协议文档见: SKILL_PATH/agents/quality-verification-agent.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/quality-verification-agent.md`
- Output boundary: write only inside `RUN_DIR/00_input`
