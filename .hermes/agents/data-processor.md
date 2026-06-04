# Agent: Data Processor (Step 3)

> Hermes launch stub only. This file is for the main agent to prepare `delegate_task`. The spawned sub-agent must read `SKILL_PATH/agents/data-processor.md` as its full execution protocol.

## Role
工业诊断流程 Step 3 — 数据处理与可视化。运行统计基线脚本 + 专家自定义分析，生成图表和 data_analysis_conclusion.json。

## Hermes delegate_task Usage

```
delegate_task(
    goal="执行工业数据深度处理与可视化分析。运行统计基线脚本（Simpson悖论检测、趋势混淆分析、变点检测），进行场景特化分析，生成自适应可视化图表，委托VLM视觉分析子代理读图，最终输出data_analysis_conclusion.json和validate_report.json。",
    toolsets=["terminal", "file", "vision"],
    role="orchestrator",
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 data-processor 完整流程（Phase 0-6）：\nPhase 0 (MANDATORY): 数据探索 — 理解工艺、识别数据结构、写 analysis_plan.md\nPhase 1: 场景分类 → scenario_classification.json\nPhase 2: 通用基线分析（convert, preprocess, stats, anomaly detection）\nPhase 2.5: 如存在产品分组列 → group-aware analysis 强制执行\nPhase 2.7: 专家缺口分析 → 决定是否需要 custom scripts\nPhase 3 (CORE): 场景特化分析（按 A-G 决策树执行）\nPhase 4: RAG知识 Stage 2 验证\nPhase 5: 自适应可视化（主时间对齐叠加图 + 场景特化图 + VLM图表）\nPhase 5.5: VLM视觉分析 — 委托 vlm-visual-analyzer 子代理读图\nPhase 6: 写 data_analysis_conclusion.json + 运行 normalize/synthesize helper scripts\n\n所有 Python 必须用 SKILL_PATH/scripts/.venv/bin/python\n完整协议文档见: SKILL_PATH/agents/data-processor.md"
)
```

## Launch Contract
- `spawn_method`: `delegate_task`
- `role`: `orchestrator`
- Full protocol entry: `SKILL_PATH/agents/data-processor.md`
- Nested delegation requirement: parent Hermes config must set `delegation.orchestrator_enabled: true` and `delegation.max_spawn_depth >= 2`

## Tools Needed
- terminal (bash, python scripts)
- file (read/write JSON, read images)
- vision (image analysis for charts)

## Core Rules
- 场景优先 — 先读数据再决策，不同数据不同分析
- Phase 0 是强制且最重要的 — 必须先写 analysis_plan.md
- 产品分组列存在时 — 分组分析强制，模内时序排列
- Python 必须用 uv venv — 通过 uv_env_setup.mjs 获取路径
- 所有路径包含空格时必须双引号包裹
- Phase 5.5 VLM 视觉分析可委托子代理
- 默认中文
