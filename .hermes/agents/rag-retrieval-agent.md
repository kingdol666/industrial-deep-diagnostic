# Agent: RAG Retrieval Agent (Phase 1)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/retrieval-agent.md` as its full execution protocol.

## Role
RAG Phase 1 — 多视角知识检索。面向目标领域构造 4 个互补查询视角，从本地知识库与可选网络源检索候选知识块。

## Hermes delegate_task Usage

```text
delegate_task(
    goal="执行 RAG Phase 1 多视角知识检索。基于 DOMAIN、TARGET_CONCEPTS、RELATED_CONCEPTS、CONTEXT_DIMENSIONS 构造 4 个查询视角，完成本地/网络检索并写出原始 retrieval 结果。",
    toolsets=["terminal", "file", "web"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\nDOMAIN={DOMAIN}\nTARGET_CONCEPTS={TARGET_CONCEPTS}\nRELATED_CONCEPTS={RELATED_CONCEPTS}\nCONTEXT_DIMENSIONS={CONTEXT_DIMENSIONS}\nMODE={MODE}\nTOP_K={TOP_K}\n\n执行 retrieval-agent 完整协议。\n完整协议文档见: SKILL_PATH/agents/retrieval-agent.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/retrieval-agent.md`
- Output boundary: write only inside `RUN_DIR/00_input`
