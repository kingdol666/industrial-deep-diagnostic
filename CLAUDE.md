# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Industrial Deep Diagnostic — 端到端工业深度诊断系统，对传感器/工艺数据进行 9 阶段根因分析。核心架构：

1. **OMP Skills** (`.omp/skills/`) + **Claude Skills** (`.claude/skills/`) — 12 个标准化 Skill × 9 个专用 Agent，含 JSON Schema 验证 + 脚本工具链
2. **Web 应用** — Express.js 后端 (port 3210) + Vue 3 / Vite 前端 (port 5180)
3. **RAG Retrieval Engine** (`rag-retrieval-engine/`) — ChromaDB + FastAPI 微服务 (port 8765)

### 双 Harness 架构

```
.omp/skills/<name>/SKILL.md    ← OMP 发现入口 (thin wrapper, 仅 SKILL.md)
    ↓ SKILL_PATH 自动重定向 (<this-skill-directory>/../../../.claude/skills/<name>)
.claude/skills/<name>/         ← 完整资源 (scripts/ schemas/ references/ resources/ templates/)
    ↓ 启动 Agent
.omp/agents/<name>.md          ← Agent 定义 (model + tools + thinkingLevel)
.claude/agents/<name>.md       ← Agent 定义 (.claude 格式, model + tools + color)
    ↓ 读取协议
references/agent-protocol.md   ← Phase 0-N 完整执行清单
```

## Commands

### CLI (`ind-diag`)
```bash
ind-diag all          # 后端 + 前端
ind-diag backend      # http://localhost:3210
ind-diag frontend     # http://localhost:5180
ind-diag build        # 生产构建
ind-diag init         # 初始化
ind-diag status       # 状态
ind-diag webfrp       # Cloudflare Tunnel
ind-diag config list/get/set/reset
```

### npm scripts
```bash
npm start             # = ind-diag all
npm run backend       # = ind-diag backend
npm run frontend      # = ind-diag frontend
```

### Python 环境
```bash
# 所有 Python 脚本必须使用 uv 管理的 venv
node scripts/uv_env_setup.mjs
# 之后: scripts/.venv/bin/python
```

### RAG 检索引擎
```bash
cd rag-retrieval-engine
python server.py      # FastAPI → http://localhost:8765
```

## Architecture

### 诊断管线 (Step 0–9)

| Steps | Agent | Skill | Model | 产出 |
|-------|-------|-------|:-----:|------|
| Step 0: Setup | main-agent | `industrial-analysis-auto` | — | run_manifest, pipeline_events |
| Step 1: Inspect | main-agent | — | — | input_manifest, user_context |
| Step 2: Context | **context-builder** | `industrial-ontology-builder` | default | ontology.json, rag_deep_understanding |
| Step 3: Process | **data-processor** | `industrial-data-processor` | default | data_analysis_conclusion, plots |
| Step 3.5: VLM | **vlm-visual-analyzer** | `industrial-vlm-analyzer` | **vision** | visual_analysis.json |
| Step 4: Diagnose | **diagnostician** | `industrial-diagnostician` | default | diagnosis, evidence, confidence, reasoning_chain |
| Step 5a: Judge | **judge** | `industrial-judge` | default | judge_feedback.json |
| Step 5b: Pre-Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer_preflight.md |
| Step 6: Report | **reporter** | `industrial-reporter` | default | report.md, run_summary.json |
| Step 7: Final Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer.md (ENDORSED) |
| Step 8: HTML Viz | **html-visualizer** | `industrial-html-visualizer` | default | diagnostic-report.html |
| Step 8.5: HTML Review | **html-reviewer** | `industrial-html-reviewer` | default | html_review.json |
| Step 9: Finalize | main-agent | — | — | evidence_closure_report |

**修复循环**: Judge 评分 < 90 → 重跑 Diagnostician (最多 3 次)；Reviewer 未通过 → D→J→R→R (最多 2 轮)；**全局上限: 总重诊断 ≤ 5**。反振荡: 同问题第 3 次 → COMPETING_SET，置信度≤50。

**Step 5a/5b 并行**: Judge 与 pre-audit 是管线中唯一并行的两步。Step 3.5 VLM 由 data-processor 内部委托。

### 检查点门禁 (CP-1 ~ CP-9)

| CP | 验证 | 失败→ |
|:--|------|-------|
| CP-1 | input_manifest + user_context | 回 Step 0 |
| CP-2 | ontology.json ≥1KB + schema-valid | 重跑 ontology |
| CP-3 | clarification AUTO_RESOLVED | 解决 |
| CP-4 | data_analysis_conclusion + plots>0 | 重跑 processor |
| CP-5 | 4 诊断输出 schema-valid | 修复 |
| CP-6 | judge_repair_summary | best-of-3 |
| CP-7 | report.md + run_summary.json | 重跑 reporter |
| CP-8 | optimizer.md ENDORSED | 修复循环 |
| CP-9 | diagnostic-report.html ≥5KB + review pass | 重跑 visualizer |

### 四个独立编号体系
| 体系 | 范围 | 示例 |
|------|------|------|
| Pipeline Step 0-9 | 编排层面 | "Step 4: Diagnostician" |
| Agent Phase 0-7 | Agent 内部流程 | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

### 诊断方法论核心
- **竞争假设协议**: 假设→数据区分性→排除→结论。输出: DETERMINED / COMPETING_SET / NEEDS_DATA
- **双驱动分析**: 纯工艺波动 + 工艺-检测双驱动
- **证据等级 L1-L7**: 结论受限最低证据等级
- **四条件**: 时间先后 + 统计显著 + 物理机制 + 无矛盾
- **置信度上限**: COMPETING_SET INDISTINGUISHABLE ≤65, oscillation ≤50
- **反假相关 v6.4-v6.7**: 时滞 CCF · 稳态过滤 · 批次完整性 · leave-one-out
- **HTML 自动构建**: CP-8 ENDORSED 后自动 Step 8→8.5→9

### Skill 目录约定
| 目录 | 用途 |
|------|------|
| `.omp/skills/<name>/SKILL.md` | OMP 发现入口 (thin wrapper) |
| `.claude/skills/<name>/` | 完整资源 (scripts, schemas, references, resources, templates) |
| `.omp/agents/<name>.md` | Agent 定义 (model + thinkingLevel + protocol ref) |
| `.claude/agents/<name>.md` | Agent 定义 (.claude 格式) |

### 诊断产出目录
```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/          # 输入数据 + 用户上下文
├── 01_ontology/       # 本体 (含 RAG 深度理解)
├── 02_processed/      # 清洗/验证/特征/异常报告
├── 03_figures/        # 可视化图表 + VLM 分析
├── 04_diagnostics/    # 诊断/证据/置信度/推理链
├── 05_review/         # Judge 评审 + HTML 审校
├── report.md          # 最终报告
├── diagnostic-report.html
├── optimizer.md
└── .pipeline_events.jsonl
```

### Web 应用
- **Backend** (`app/backend/`): Express.js + SQLite (WAL) + WebSocket
- **Frontend** (`app/frontend/`): Vue 3 + Vite + SSE 实时流

### RAG 检索引擎
- FastAPI + ChromaDB 向量检索 + Web 搜索
- 端点: `/retrieve`, `/score`, `/inject`, `/pipeline/full`
- 不可用时自动降级: `parameter_to_physics.json` + 网络搜索

### 关键脚本
- `setup.mjs` — 创建运行目录 + pipeline_events
- `inspect.mjs` — 数据文件检测
- `stats.mjs` / `stats_validate.mjs` — 统计分析 + 鲁棒性验证
- `validate.mjs` — JSON Schema 运行时验证
- `artifact-check.mjs` — 管线产物完整性验证
- `pipeline-log-check.mjs` — 管线事件日志审计
- `uv_env_setup.mjs` — Python venv 管理器

### 证据体系
| 等级 | 来源 | 置信度 |
|------|------|--------|
| L1 | 直接测量值 | 最高 |
| L2 | 用户文档 (SOP/手册) | 高 |
| L3 | 统计分析 (含验证报告) | 中高 |
| L4 | 图表视觉证据 (VLM) | 中 |
| L5 | 领域知识/工艺逻辑 | 中 |
| L6 | 外部网络引用 | 低 |
| L7 | 无支持假设 | 最低 |

## Configuration

配置优先级: `config/default.yaml` → `config/local.yaml` + 环境变量

| 环境变量 | 对应配置 |
|----------|----------|
| `SERVER_PORT` | `server.port` |
| `CLAUDE_MODEL` | `claude.model` |
| `DATA_DIR` | `data.dir` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |

## Language Default

默认输出**中文**。报告、诊断结论、审计文档使用中文。JSON enum 字段保持英文。

## Key Gotchas

- **双 Harness**: `.omp/` 是入口，`.claude/` 是资源。`SKILL_PATH` 通过 `<this-skill-directory>/../../../.claude/skills/<name>` 重定向
- **Python 路径**: 必须 `scripts/.venv/bin/python`，非系统 python3
- **修复计数器**: `diag_iters` 由 `.pipeline_events.jsonl` 的 `repair_spawn` 持久化
- **执行证明**: `.pipeline_events.jsonl` 通过 `pipeline-log-check.mjs` 才算完整执行
- **交接文件**: `data_analysis_conclusion.json` 是 data-processor→diagnostician 的强制交接
- **图像回退**: `image_captions.json` 是 PNG 渲染失败时的回退
- **HTML 自动构建**: CP-8 ENDORSED 后自动 Step 8→8.5→9；`00_input/html_opt_out` 可跳过
- **VLM Agent**: 唯一使用 `model: vision` 的 Agent，需要 vision-capable 模型读取图表
- **Agent 自引用已修复**: 所有 Agent 初始化读取 `references/agent-protocol.md`，不是 `agents/<self>.md`
- **四套编号不可混用**
