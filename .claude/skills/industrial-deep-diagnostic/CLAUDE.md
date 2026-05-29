# CLAUDE.md — Industrial Deep Diagnostic Skill v8.0

## Project Overview

工业数据深度诊断 Skill。**Agent驱动分析** + 物理定律双驱动推理。适配任何工业场景（CNC、BOPET、化工、换热器等）。

**语言默认**: 中文输出。Schema enum字段保持英文。

## Architecture (v8.0)

```
Main Agent (编排):
  Step 0: 数据理解 + 列分类
  Step 1: 自行编写分析代码 → analysis_output.json
  Step 2: 自行编写可视化代码 → figures + image_captions.json
  Step 3: Interpreter Agent → diagnosis + 推理链 + 图文报告
```

**核心变化 (v7→v8)**: 分析和可视化由Agent自行编写代码完成，不运行固定脚本。参考脚本提供方法学，不提供硬编码流程。

## Key Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill入口，v8.0 Agent驱动流程，数据列分类协议 |
| `agents/interpreter.md` | Interpreter Agent推理协议（v8.0通用化） |
| `scripts/deep_analyze.py` | 方法参考：高频时序分析（BOPET示例） |
| `scripts/deep_visualize.py` | 方法参考：诊断可视化（BOPET示例） |
| `resources/physics_reasoning.md` | 物理推理方法学指南（通用框架+BOPET/CNC案例） |

## Pipeline (v8.0)

```
Step 0: 加载数据 → 识别结构 → 分类列角色 → 确认理解
Step 1: Agent根据数据特征编写分析代码 → analysis_output.json
Step 2: Agent根据分析结果编写可视化代码 → figures + captions
Step 3: Interpreter Agent → 物理推理 + 诊断报告
```

## Core Principles

- **Agent驱动分析**: 不运行固定脚本，Agent理解数据后决定分析策略
- **数据+物理双驱动**: 统计筛选找信号，物理定律验证因果可行性
- **量级匹配是硬约束**: 原因的量级必须能解释效果的量级
- **物理排除优先于统计**: 物理不可能 = 排除, 无论r多大
- **分层分析是硬要求**: 有分组维度时必须做Simpson检测
- **COMPETING_SET是有效结论**: 数据无法区分时诚实说明
- **只引用真实数据**: 不编造数字, 不幻觉报告
