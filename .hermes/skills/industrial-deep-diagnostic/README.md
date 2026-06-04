# Industrial Deep Diagnostic Skill

面向工业数据分析与异常诊断的核心 Skill。这个 Skill 的目标不是“画几张图”，而是基于**数据、本体、物理知识、视觉证据**完成一条严格的诊断流水线，并输出可追溯的诊断结论与最终报告。

## Skill 定位

当用户提供工业数据，并要求进行：
- 异常检测
- 根因分析
- 质量缺陷诊断
- 工艺参数波动分析
- 设备故障诊断
- 工艺+检测联合判断

就应当触发这个 Skill。

它的输出不是单一结论，而是一组完整工件：
- 本体模型
- 数据分析产物
- 可视化与 VLM 视觉证据
- 诊断 JSON
- 评审结果
- 最终中文报告
- 执行日志与证据闭环报告

## 这个 Skill 做什么

它围绕两条诊断主线展开：
1. **纯工艺波动诊断**：只从工艺参数本身出发，分析波动、漂移、阈值切换、失稳
2. **工艺+检测双驱动诊断**：将工艺异常与检测/质量异常联动起来，判断工艺异常是否真正进入了缺陷因果链

同时要求：
- 统计结果必须经过验证
- 诊断必须有物理机制支撑
- 图像不是装饰，而是 VLM 会实际读取的证据
- 结论必须通过审查与审计

## 子代理架构

```text
Step 2   context-builder
Step 3   data-processor
         └── internal: vlm-visual-analyzer
Step 4   diagnostician
Step 5   judge
Step 6   reporter
Step 7   report-reviewer
Step 8   present (main agent)
```

## 标准执行流程

### Step 0-1：运行初始化
- `setup.mjs` 创建运行目录、`run_manifest.json`、`.pipeline_events.jsonl`
- `inspect.mjs` 检查输入数据，生成 `input_manifest.json` 和 `user_context.json`
- `run_config.json` 必须在进入 Step 2 前更新为真实运行参数

### Step 2：Context Build
- 构建领域理解、本体模型与 RAG 深理解产物
- 输出：`ontology.json`、`rag_deep_understanding.json`、`clarification_needed.json`

### Step 2.5：Clarification Gate
- auto / minimal / interactive 三种交互模式
- auto 模式不问用户，直接推理补齐未知参数含义

### Step 3：Data Processing
- 场景识别
- 基线脚本分析
- 产品分组/时间排序分析
- 物理检查
- 自适应可视化
- VLM 图像理解
- 输出专家数据结论 `data_analysis_conclusion.json`

### Step 4：Diagnostician
- 融合统计证据、本体、物理机制、视觉证据
- 构造竞争假说
- 输出结构化诊断工件

### Step 5：Judge
- 10 项质量门审查
- 低分时要求回修

### Step 6：Reporter
- 生成最终中文报告
- 报告必须包含逐图分析、统计验证、纯工艺诊断、双驱动诊断、数据分析专家结论

### Step 7：Report Reviewer
- 独立物理真实性审计
- 发现问题时重新触发诊断修复链

### Step 8：Present
- 汇总最终产物
- 执行 `finalize-run-artifacts.mjs`
- 执行 `artifact-check.mjs`
- 写入 `run_completed`

## 输出工件

关键工件包括：
- `00_input/run_config.json`
- `01_ontology/ontology.json`
- `02_processed/analysis_plan.md`
- `02_processed/data_analysis_conclusion.json`
- `03_figures/visual_analysis.json`
- `03_figures/image_captions.json`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `05_review/judge_feedback.json`
- `report.md`
- `run_summary.json`
- `.pipeline_events.jsonl`
- `evidence_closure_report.json`

## 最终通过条件

一次有效运行必须同时满足：
- 流程顺序正确
- 子代理有执行证据
- VLM 子代理有独立执行证据
- 核心结构化工件存在且通过 schema 校验
- 证据闭环成立
- `present` 步骤完成
- 最终记录 `run_completed`

## 工程化特征

这个 Skill 之所以不是普通 prompt，而是一个工程化 Skill，原因在于它同时具备：
- agents
- scripts
- schemas
- templates
- evals
- 事件日志
- 最终工件验收

## 配套文件

- 主协议：`SKILL.md`
- 开发备注：`CLAUDE.md`
- 流程细则：`pipeline-execution.md`
- 工程交付契约：`resources/engineering_delivery_contract.md`

## 适用与边界

适用：
- 工业制造场景
- 传感器/工艺/质量多变量分析
- 需要根因与报告交付的任务

不适用：
- 简单图表制作
- 非工业数据分析
- 纯统计教学题
