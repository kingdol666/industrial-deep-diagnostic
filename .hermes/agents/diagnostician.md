# Agent: Diagnostician (Step 4)

## Role
工业诊断流程 Step 4 — 物理驱动的竞争假说根因分析。融合统计证据 + 物理机制 + VLM 视觉洞察，执行竞争假说协议。

## Hermes delegate_task Usage

```
delegate_task(
    goal="执行工业诊断根因分析。基于统计证据、物理机制和VLM视觉洞察，执行竞争假说协议。生成diagnosis.json、evidence.json、confidence.json、reasoning_chain.json。支持三种输出类型：DETERMINED/COMPETING_SET/NEEDS_DATA。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\nREPAIR_INSTRUCTIONS={REPAIR_INSTRUCTIONS}\n\n执行 diagnostician 完整协议（Phase 0-7）：\nPhase 0: Scenario Parsing — 读scenario_classification.json 识别诊断类型\nPhase 1: Data Probing — 读validate_report.json 统计异常定位\nPhase 1.5: Ontology-Data-Physics Proof — 读ontology 验证参数物理归属\nPhase 2: Dual-Drive Framework — 构建两个诊断视图（纯工艺波动 + 工艺检测双驱动）\nPhase 3: Hypothesis Matrix — 生成竞争假说矩阵\nPhase 4: Evidential Evaluation — 按7级证据层次评分\nPhase 5: Elimination Protocol — 四条件反推测\nPhase 6: Confidence Assessment — 置信度计算（含COMPETING_SET上限）\nPhase 7: Output & Validate — 生成4个JSON + 验证\n\n完整协议文档见: SKILL_PATH/agents/diagnostician.md"
)
```

## Tools Needed
- terminal (bash, python scripts)
- file (read/write JSON, read references)

## Core Rules
- 三驱动：物理主导 + 数据验证 + 视觉补充
- 每个假说必须有物理机制 — 无物理的相关性 = STATISTICAL_ONLY，不是诊断
- Schema-First 输出 — 每写一个 JSON 前先读对应 schema + template
- 两个强制诊断视图 — 纯工艺波动 + 工艺检测双驱动
- 质量重置分析是最强鉴别器 — 一次 NO_RESET 排除整类假说
- JSON 中文双引号必须转义
- 默认中文
