# Agent: RAG Scoring Agent (Phase 1)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/scoring-agent.md` as its full execution protocol.

## Role
RAG Phase 1 — 5 维相关性评分与质量门。对检索知识块执行相关性评分、分层、拒绝原因标注，并输出 `rag_scored_chunks.json`。

## Hermes delegate_task Usage

```text
delegate_task(
    goal="执行 RAG Phase 1 评分与筛选。读取 retrieval 结果和上下文，完成 5 维相关性评分、tier 分类、拒绝原因说明，并输出 rag_scored_chunks.json。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\nRETRIEVAL_RESULTS={RETRIEVAL_RESULTS}\nSCORING_CONTEXT={SCORING_CONTEXT}\nPASS_THRESHOLD={PASS_THRESHOLD}\n\n执行 scoring-agent 完整协议。\n完整协议文档见: SKILL_PATH/agents/scoring-agent.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/scoring-agent.md`
- Output boundary: write only inside `RUN_DIR/00_input`
