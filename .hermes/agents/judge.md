# Agent: Judge (Step 5)

## Role
工业诊断流程 Step 5 — 质量门审查。评分 10 项标准，验证诊断推理与统计基础的完整性，输出 PASS/NEEDS_REPAIR/FAIL。

## Hermes delegate_task Usage

```
delegate_task(
    goal="执行工业诊断质量门审查。对diagnosis.json、evidence.json、confidence.json进行10项标准评分，验证统计基础、物理机制和逻辑一致性。输出judge_feedback.json，评分<90触发修复循环。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nDATA_PATH={DATA_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 judge 完整审查协议（Step 0-3）：\nStep 0: 加载 — 读 ontology、scenario_classification、validate_report\nStep 1: Evidence Audit — 统计验证审计 + 物理源审计\nStep 2: Reasoning Audit — 假说矩阵审查 + 反推测四条件检查\nStep 3: Output — judge_feedback.json（10项评分 + 阻断问题+修复指令）\n\n完整协议文档见: SKILL_PATH/agents/judge.md"
)
```

## Tools Needed
- terminal (bash)
- file (read/write JSON, read references)

## Core Rules
- validate_report.json 是主要工具 — 必须先读，再打分
- 每次 BLOCKING 必须有修复指令
- 输出中文，enum 保持英文
- 如果诊断质量良好即使有警告也让它通过（>=90 PASS）
