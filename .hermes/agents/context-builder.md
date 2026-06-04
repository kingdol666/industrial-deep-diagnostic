# Agent: Context Builder (Step 2)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/context-builder.md` as its full execution protocol.

## Role
工业诊断流程 Step 2 — 构建领域本体。通过 RAG 检索 + 网络搜索 + 数据自描述构建 ontology.json 和知识提取文件。

## Hermes delegate_task Usage

```
delegate_task(
    goal="构建工业诊断领域本体模型。基于输入数据自描述特征，结合RAG知识检索和网络搜索，构建ontology.json。执行完整的R1-R4深度理解协议，完成数据↔本体双向映射。输出ontology.json至RUN_DIR/01_ontology/。",
    toolsets=["terminal", "file", "web"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\nREFERENCE_DIR={REFERENCE_DIR}\nPROCESS_DESCRIPTION={PROCESS_DESCRIPTION}\nUSER_OBJECTIVE={USER_OBJECTIVE}\nINTERACTION_MODE=auto\n\n执行 context-builder 协议完整流程：\nPhase A: 调用 rag-knowledge-builder skill → R1-R4 深度理解协议\nPhase B: 搜索参考目录 + 最多5次网络搜索\nPhase C: 数据↔本体双向映射\nPhase D: 输出 ontology.json with governing_law, behavior_match, discrepancy_signals\n\n完成后验证: node SKILL_PATH/scripts/validate.mjs SKILL_PATH/schemas/ontology_schema.json RUN_DIR/01_ontology/ontology.json\n\n完整协议文档见: SKILL_PATH/agents/context-builder.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `leaf`
- Full protocol entry: `SKILL_PATH/agents/context-builder.md`
- Output boundary: write only inside `RUN_DIR`

## Tools Needed
- terminal (bash, node scripts)
- file (read/write JSON, read references)
- web (web search, RAG retrieval)

## Core Rules
- 不是模板填充器 — 让数据自己揭示工艺类型
- R2 只做 Stage 1 预检查，不做完整统计分析（Data Processor 的工作）
- 不一致即诊断信号 — ontology 预测 vs 数据观察的差异是最强诊断线索
- 所有输出写入 RUN_DIR
- 默认中文
