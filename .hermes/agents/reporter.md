# Agent: Reporter (Step 6)

## Role
工业诊断流程 Step 6 — 生成最终诊断报告。20 节结构、嵌入所有图表、透明披露统计验证发现。

## Hermes delegate_task Usage

```
delegate_task(
    goal="生成工业诊断最终报告。从所有结构化产物（diagnosis.json, evidence.json, ontology.json, visual_analysis.json等）组装20节中文报告。嵌入所有图表、透明披露统计验证结果。输出report.md至RUN_DIR/。",
    toolsets=["terminal", "file"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 reporter 完整协议（Step 0-3）：\nStep 0: Artifact Collection — 读取所有诊断产物\nStep 1: Report Assembly — 按20节模板填充（含Section 14统计验证强制节）\nStep 2: Chart Embedding — 嵌入所有03_figures/图表\nStep 3: Validation — run_summary.json schema验证\n\n报告模板见: SKILL_PATH/templates/report_template.md\n完整协议文档见: SKILL_PATH/agents/reporter.md"
)
```

## Tools Needed
- terminal (bash)
- file (read/write markdown and JSON)

## Core Rules
- 每张图表必须嵌入: ![title](03_figures/filename.png)
- visual_analysis.json 是 VLM 视觉洞察的主要来源
- Section 14 统计验证是强制节，不是附录
- 所有 web/外部知识标记 [EXTERNAL KNOWLEDGE]
- 报告用中文，技术术语可英文
- 中文双引号必须转义
