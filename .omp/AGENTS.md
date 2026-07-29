# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project Overview

Industrial Deep Diagnostic — 端到端工业深度诊断系统，对传感器/工艺数据进行 9 阶段根因分析。核心架构包含三大部分：

1. **Skills** (`.claude/skills/`) — 12 个标准化 Skill（OMP 经 `claude` provider 发现）+ JSON Schema 验证 + 脚本工具链
2. **OMP Agents** (`.omp/agents/`) — 9 个专用子代理（OMP task-agent 唯一发现源），每个对应管线的一个步骤
3. **Web 应用** — Express.js 后端 (port 3210) + Vue 3 / Vite 前端 (port 5180)
4. **RAG Retrieval Engine** (`rag-retrieval-engine/`) — ChromaDB + FastAPI 微服务 (port 8764)

## Pipeline Architecture

### 诊断管线（9 步）

|Steps|Agent|产出|
|---|---|---|
|Step 0: Setup|main-agent|`00_input/input_manifest.json`, `user_context.json`|
|Step 1: Inspect|main-agent|schema, feature_summary|
|Step 2: Context|**context-builder**|`01_ontology/ontology.json`, rag_deep_understanding|
|Step 3: Process|**data-processor**|`02_processed/validate_report.json`, `03_figures/*.png`, visual_analysis|
|Step 4: Diagnose|**diagnostician**|`04_diagnostics/diagnosis.json`, evidence.json, confidence.json, reasoning_chain.json`|
|Step 5: Judge|**judge**|`05_review/judge_feedback.json` (10 项评分 + 阻断问题)|
|Step 6: Report|**reporter**|`report.md`|
|Step 7: Review|**report-reviewer**|`optimizer.md`|
|Step 8: HTML Viz|**html-visualizer**|`diagnostic-report.html`|
|Step 8.5: HTML Review|**html-reviewer**|`05_review/html_review.json`|
|Step 9: Finalize|main-agent|`evidence_closure_report.json`, 最终交付校验|

**修复循环**: Judge 评分 < 90 → 重跑 Diagnostician（最多 3 次）；Reviewer 未通过 → 完整重跑 D→J→R→R（最多 2 轮）；**全局上限：总重诊断 ≤ 5**

## OMP Agent Summary

| Agent | Role | Spawns | Key Tools |
|-------|------|--------|-----------|
| context-builder | 本体构建 (Step 2) | * | read, write, bash, glob, grep, web_search, skill |
| data-processor | 数据分析 (Step 3) | * | read, write, bash, glob, grep, task |
| vlm-visual-analyzer | 视觉分析 (Step 3.5) | leaf | read, write, bash, glob, grep |
| diagnostician | 根因诊断 (Step 4) | leaf | read, write, bash, glob, grep |
| judge | 质量评审 (Step 5) | leaf | read, write, bash, glob, grep |
| reporter | 报告生成 (Step 6) | leaf | read, write, bash, glob, grep |
| report-reviewer | 物理审计 (Step 5b/7) | leaf | read, write, bash, glob, grep, web_search |
| html-visualizer | HTML可视化 (Step 8) | leaf | read, write, bash, glob, grep, skill |
| html-reviewer | HTML审校 (Step 8.5) | leaf | read, write, bash, glob, grep |

## Skill Directory Convention

> `.omp/skills/` 已移除。skill 资源统一在 `.claude/skills/`，由 OMP `claude` provider (priority 80) 发现。`.omp/agents/` 是 OMP task-agent 唯一发现源（OMP 跳过 `.claude/agents`）。

| Directory | Purpose |
|-----------|---------|
| `.claude/skills/<name>/SKILL.md` | 唯一 skill 入口 (OMP claude provider + Claude Code 发现) |
| `templates/` | Output format templates |
| `schemas/` | JSON Schema (draft-07), validated with `validate.mjs` |
| `scripts/` | Pipeline executables (Node.js + Python/uv) |
| `resources/` | Domain knowledge loaded on demand |

## Commands

```bash
# Start project (backend + frontend)
ind-diag all

# Individual services
ind-diag backend      # http://localhost:3210
ind-diag frontend     # http://localhost:5180

# Production build
ind-diag build

# Initialize (check DB / config)
ind-diag init

# Status
ind-diag status
```

## Key Gotchas

- **Python venv**: All Python scripts MUST use `scripts/.venv/bin/python` via `uv_env_setup.mjs`
- **Repair counters**: `diag_iters` tracked by `repair_spawn` events in `.pipeline_events.jsonl`
- **Execution proof**: Only `.pipeline_events.jsonl` passing `pipeline-log-check.mjs` proves full execution
- **Expert handoff**: `data_analysis_conclusion.json` is the mandatory data-processor→diagnostician handoff
- **Image fallback**: `image_captions.json` is the fallback when PNG rendering fails
- **HTML auto-build**: CP-8 ENDORSED → auto-build Steps 8→8.5→9, no user prompts
- **Anti-spurious-correlation v6.4-v6.7**: Lag-compensated CCF, steady-state filter, batch identity integrity, leave-one-out leverage check
- **Four separate numbering systems**: Pipeline Step (0-9), Agent Phase (0-7), Reasoning Segment (R1-R8), Method Stage (1-6) — DO NOT mix
- **Default language**: 中文 for reports, conclusions, audits; English for JSON enum fields
