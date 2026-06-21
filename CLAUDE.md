# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Industrial Deep Diagnostic — 一个端到端工业深度诊断系统，对传感器/工艺数据进行 9 阶段根因分析。核心架构包含三大部分：

1. **Claude Code Skill** (`.claude/skills/industrial-deep-diagnostic/`) — 多智能体诊断管线，含 6 个子智能体 + JSON Schema 验证 + 脚本工具链
2. **Web 应用** — Express.js 后端 (port 3210) + Vue 3 / Vite 前端 (port 5180)
3. **RAG Retrieval Engine** (`rag-retrieval-engine/`) — ChromaDB + FastAPI 微服务 (port 8765)

## Commands

### CLI (`ind-diag`)
```bash
# 启动项目（后端 + 前端一起启动）
ind-diag all

# 单独启动
ind-diag backend      # http://localhost:3210
ind-diag frontend     # http://localhost:5180

# 生产构建前端
ind-diag build

# 初始化（检查 DB / 配置）
ind-diag init

# 状态查看
ind-diag status

# 配置管理
ind-diag config list
ind-diag config get server.port
ind-diag config set claude.model claude-opus-4-7
ind-diag config reset server.port
```

### 等价 npm scripts
```bash
npm start            # = ind-diag all
npm run backend      # = ind-diag backend
npm run frontend     # = ind-diag frontend
npm run build        # = ind-diag build
npm run status       # = ind-diag status
npm link             # = ind-diag 全局可用
```

### Skill 命令（在 Claude Code 对话中调用）
- `/industrial-deep-diagnostic` — 全管线（Step 0-9）
- `/industrial-deep-diagnostic analyze` — 跳过数据导入，从 Step 2 开始
- `/industrial-deep-diagnostic review` — 重新评审已有结果
- `/industrial-deep-diagnostic report` — 重新生成报告
- `/industrial-deep-diagnostic audit` — 仅运行报告评审

### Python 环境
```bash
# 所有 Python 脚本必须使用管理的 venv
node scripts/uv_env_setup.mjs
# 之后 Python 路径为 scripts/.venv/bin/python
```

### RAG 检索引擎
```bash
cd rag-retrieval-engine
python server.py     # 启动 FastAPI 服务 → http://localhost:8765
```

### 外网映射
```bash
ind-diag webfrp      # Cloudflare Tunnel 暴露公网
```

## Architecture

### 诊断管线（9 步）

| Steps | Agent | 产出 |
|-------|-------|------|
| Step 0: Setup | main-agent | `00_input/input_manifest.json`, `user_context.json` |
| Step 1: Inspect | main-agent | schema, feature_summary |
| Step 2: Context | **context-builder** | `01_ontology/ontology.json`, rag_deep_understanding |
| Step 3: Process | **data-processor** | `02_processed/validate_report.json`, `03_figures/*.png`, visual_analysis |
| Step 4: Diagnose | **diagnostician** | `04_diagnostics/diagnosis.json`, evidence.json, confidence.json, reasoning_chain.json |
| Step 5: Judge | **judge** | `05_review/judge_feedback.json` (10 项评分 + 阻断问题) |
| Step 6: Report | **reporter** | `report.md` |
| Step 7: Review | **report-reviewer** | `optimizer.md` |
| Step 8: HTML Viz | **html-visualizer** | `diagnostic-report.html` |
| Step 8.5: HTML Review | **html-reviewer** | `05_review/html_review.json` |
| Step 9: Finalize | main-agent | `evidence_closure_report.json`, 最终交付校验 |

**修复循环**: Judge 评分 < 90 → 重跑 Diagnostician（最多 3 次）；Reviewer 未通过 → 完整重跑 D→J→R→R（全局上限 5 次）。

### 四个独立的编号体系
| 体系 | 范围 | 示例 |
|------|------|------|
| Pipeline Step 0-9 | 编排层面 | "Step 4: Diagnostician" |
| Agent Phase 0-7 | Diagnostician 内部流程 | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

### 诊断方法论核心
- **竞争性假设协议** (Competing Hypotheses Protocol): 假设→数据区分性评估(Data Discriminability)→排除→结论。输出三种类型：`DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **双驱动分析**: 纯工艺波动诊断 + 工艺-检测双驱动诊断
- **证据等级 1-7**: 结论受限最低证据等级
- **反推测四条件**: 时间先后 + 统计显著 + 物理机制 + 无矛盾
- **置信度上限**: COMPETING_SET 场景受上限约束（INDISTINGUISHABLE 设为 65）

### 多智能体角色
- **context-builder**: RAG 检索 + 本体构建 + 物理原理提取（非模板填充）
- **data-processor**: 统计分析（Simpson's Paradox、趋势混淆、变点检测）+ 可视化 + VLM 图像分析
- **diagnostician**: 物理约束的竞争性假设诊断 + 一级原理推理
- **judge**: 10 项质量门评审（含物理源审计）
- **reporter**: 从结构化产物生成报告
- **report-reviewer**: 物理真相独立审计

### 诊断产出目录结构
```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/          # 输入数据 + 用户上下文
├── 01_ontology/       # 本体（含 RAG 深度理解）
├── 02_processed/      # 清洗/验证/特征/异常报告
├── 03_figures/        # 可视化图表 + VLM 分析
├── 04_diagnostics/    # 诊断/证据/置信度/推理链
├── 05_review/         # Judge 评审反馈
├── 06_scripts/        # 自定义分析脚本
├── report.md          # 最终报告
└── optimizer.md       # 优化建议
```

### Web 应用
- **Backend** (`app/backend/`): Express.js + SQLite (WAL mode) + WebSocket，事件总线架构
- **Frontend** (`app/frontend/`): Vue 3 + Vite + 标签页布局（Data / Diagnose / Reports / History），SSE 实时流 + WebSocket

### RAG 检索引擎 (`rag-retrieval-engine/`)
- FastAPI + ChromaDB 向量检索 + Web 搜索
- 端点: `/retrieve`, `/score` (5 维评分), `/inject` (本体注入), `/pipeline/full`
- 运行时由 `rag_client.py` 与 skill 管线集成

### Skill 目录约定
| 目录 | 用途 |
|------|------|
| `templates/` | 输出格式模板 |
| `schemas/` | JSON Schema (draft-07)，用 `validate.mjs` 运行时验证 |
| `assets/` | 共享媒体资源 |
| `scripts/` | 管线可执行脚本（Node.js + Python/uv） |
| `resources/` | 子智能体按需加载的领域知识 |
| `examples/` | 常见场景的样例配置/本体 |

### 关键脚本
- `setup.mjs` — 创建运行目录结构
- `inspect.mjs` — 数据文件检测（CSV/JSON/TSV 流式解析）
- `convert.mjs` — CSV/TSV → JSON 转换
- `stats.mjs` — 高级统计分析引擎（Pearson/Spearman/分层/延迟CCF/多重检验）
- `stats_validate.mjs` — 统计验证与鲁棒性引擎
- `validate.mjs` — JSON Schema 运行时验证（零依赖）
- `artifact-check.mjs` — 管线产物完整性验证
- `pipeline-log-check.mjs` — 管线事件日志审计
- `generate_captions.mjs` — 图表说明生成（PNG 不可用时的回退）
- `physics_check.py` / `dp_toolkit.py` — 物理约束验证
- `file_inspect.py` — 大文件格式回退解析
- `visual_analysis.py` — VLM 视觉分析
- `stats_analysis.py` — 自适应统计分析
- `uv_env_setup.mjs` — Python venv 管理器

### 证据体系
| 等级 | 来源 | 置信度 |
|------|------|--------|
| 1 | 直接测量值 | 最高 |
| 2 | 用户文档 (SOP/手册) | 高 |
| 3 | 统计分析（含验证报告） | 中高 |
| 4 | 图表视觉证据 | 中 |
| 5 | 领域知识/工艺逻辑 | 中 |
| 6 | 外部网络引用 | 低 |
| 7 | 无支持假设 | 最低 |

## Configuration

关键配置项 (`config/default.yaml`)，覆盖方式: `config/local.yaml` + 环境变量:

| 环境变量 | 对应配置 |
|----------|----------|
| `SERVER_PORT` | `server.port` |
| `CLAUDE_MODEL` | `claude.model` |
| `CLAUDE_MAX_TURNS` | `claude.max_turns` |
| `CLAUDE_TIMEOUT_MINUTES` | `claude.timeout_minutes` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |
| `DATA_DIR` | `data.dir` |

## Language Default

默认输出语言为**中文**。报告、诊断结论、审计文档使用中文。JSON enum 字段保持英文。

## Key Gotchas

- **autopilot 模式**: `setup.mjs` 创建 run_dir 后更新 `run_manifest.json` — autopilot 下需用 `data/autopilot_manifest.json` 实现文件发现
- **Python 路径**: 所有 Python 脚本必须使用 `scripts/.venv/bin/python`，非系统 python3
- **修复计数器**: `diag_iters` 由 `.pipeline_events.jsonl` 中的 `repair_spawn` 事件持久化维护，不依赖内存状态
- **执行证明**: 只有 `.pipeline_events.jsonl` 通过 `pipeline-log-check.mjs` 才算完整执行，仅文件存在不足够
- **Expert 交接**: `data_analysis_conclusion.json` 是 data-processor→diagnostician 的强制交接文件
- **图像回退**: `image_captions.json` 是 PNG 渲染不可用时的回退方案
- **SKILL.md 权威**: 与 CLI `ind-diag` 冲突时，SKILL.md 是管线执行入口
- **四套编号**: Pipeline Step / Agent Phase / Reasoning Segment / Method Stage 各独立，不可混用
