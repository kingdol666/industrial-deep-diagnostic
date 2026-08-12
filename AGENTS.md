# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project Overview

Industrial Deep Diagnostic — 端到端工业深度诊断系统，对传感器/工艺数据进行 9 阶段根因分析 + E0-E8 增强分析管线。核心架构：

1. **Skills** (`.claude/skills/`) — 18 个标准化 Skill（OMP 经 `claude` provider 发现）× 14 个专用 Agent，含 JSON Schema 验证 + 脚本工具链
2. **Web 应用** — Express.js 后端 (port 3210) + Vue 3 / Vite 前端 (port 5180)
3. **RAG Retrieval Engine** (`rag-retrieval-engine/`) — ChromaDB + FastAPI 微服务 (port 8764)

### Harness 发现架构

```
.claude/skills/<name>/         ← 唯一 skill 源 (OMP claude provider priority-80 发现 + Claude Code 原生发现)
    │  scripts/ schemas/ references/ resources/ templates/ 全在此处
    ↓ skill://<name> 解析到此处；Agent dispatch 传 SKILL_PATH 指向此处
.omp/agents/<name>.md          ← OMP task-agent 唯一发现源 (OMP 跳过 .claude/agents)
    │  OMP frontmatter: name + description + tools + spawns + model + thinkingLevel
    ↓ 读取协议
.claude/skills/<name>/references/agent-protocol.md  ← Phase 0-N 完整执行清单
```

> **架构要点**: skill 资源统一在 `.claude/skills/`（OMP 与 Claude Code 共用）；agent 定义在 `.omp/agents/`（满足 OMP task-agent 契约，是 task 创建的唯一来源）。

## Commands

```bash
# Start project (backend + frontend)
ind-diag all
ind-diag backend      # http://localhost:3210
ind-diag frontend     # http://localhost:5180
ind-diag build        # Production build
ind-diag init         # Initialize (check DB / config)
ind-diag status       # Status
```

### Python venv
```bash
# All Python scripts MUST use the shared venv via uv_env_setup.mjs
node .claude/shared/scripts/uv_env_setup.mjs
# Resolves to: .claude/shared/scripts/.venv/Scripts/python.exe (Windows)
#              .claude/shared/scripts/.venv/bin/python (POSIX)
```

### RAG Engine
```bash
cd rag-retrieval-engine
python server.py      # → http://localhost:8764
```

## Architecture

### Pipeline (Step 0–9)

| Steps | Agent | Skill | Model | 产出 |
|-------|-------|-------|:-----:|------|
| Step 0: Setup | main-agent | `industrial-analysis-auto` | — | run_manifest, pipeline_events |
| Step 1: Inspect | main-agent | — | — | input_manifest, user_context |
| Step 2: Context | **context-builder** | `industrial-ontology-builder` | default | ontology.json |
| Step 3: Process | **data-processor** | `industrial-data-processor` | default | data_analysis_conclusion, plots |
| Step 3.5: VLM | **vlm-visual-analyzer** | *(data-processor Phase 5.5)* | **vision** | visual_analysis.json |
| Step 4: Diagnose | **diagnostician** | `industrial-diagnostician` | default | diagnosis, evidence, confidence, reasoning_chain |
| Step 5a: Judge | **judge** | `industrial-judge` | default | judge_feedback.json |
| Step 5b: Pre-Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer_preflight.md |
| Step 6: Report | **reporter** | `industrial-reporter` | default | report.md, run_summary.json |
| Step 7: Final Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer.md (ENDORSED) |
| Step 8: HTML Viz | **html-visualizer** | `industrial-html-visualizer` | default | diagnostic-report.html |
| Step 8.5: HTML Review | **html-reviewer** | `industrial-html-reviewer` | default | html_review.json |
| Step 9: Finalize | main-agent | — | — | evidence_closure_report |

**修复循环**: Judge 评分 < 90 → 重跑 Diagnostician（最多 3 次）；Reviewer 未通过 → 完整重跑 D→J→R→R（最多 2 轮）；**全局上限：总重诊断 ≤ 5**（由 `.pipeline_events.jsonl` 的 `repair_spawn` 事件持久化计数）。反振荡：同问题第 3 次重诊断 → 停止，标 `COMPETING_SET`，置信度上限 ≤50。

**检查点 🛑 CP-1 ~ CP-9**：每个检查点有精确 bash 验证命令，不满足则阻断或回退。详见 orchestrator SKILL.md。

**Step 5a/5b 并行**：Judge 与 report-reviewer 预审计是管线中**唯一并行**的两步。

### 四个独立的编号体系
| 体系 | 范围 | 示例 |
|------|------|------|
| Pipeline Step 0-9 | 编排层面 | "Step 4: Diagnostician" |
| Agent Phase 0-7 | Agent 内部流程 | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

### 诊断方法论核心
- **竞争性假设协议**: 假设→数据区分性评估→排除→结论。输出三种类型：`DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **双驱动分析**: 纯工艺波动诊断 + 工艺-检测双驱动诊断
- **证据等级 1-7**: 结论受限最低证据等级
- **反推测四条件**: 时间先后 + 统计显著 + 物理机制 + 无矛盾
- **置信度上限**: COMPETING_SET INDISTINGUISHABLE ≤65, oscillation ≤50
- **反假相关强制（v6.4–v6.7）**: 时滞补偿 CCF · 生产状态识别+稳态过滤 · 批次标识完整性 · 离群杠杆 leave-one-out
- **HTML 自动构建（非交互）**: CP-8 `ENDORSED` 后默认自动连续执行 Step 8→8.5→9，不询问用户

### Skill 体系 (18 Skills)

| Skill | 触发条件 | 模型 |
|-------|---------|:----:|
| `industrial-analysis-auto` | 工业诊断, 根因分析, 故障诊断... | default |
| `industrial-data-preprocessor` | 数据前处理, 预处理, 多格式数据... | default |
| `industrial-ontology-builder` | ontology构建, 本体, RAG检索... | default |
| `industrial-data-processor` | 统计分析, 数据清洗, 数据可视化... | default |
| `industrial-diagnostician` | 诊断, 根因, 竞争假设... | default |
| `industrial-judge` | quality gate, 质量评审... | default |
| `industrial-physical-auditor` | physical audit, 物理审计... | default |
| `industrial-reporter` | 写报告, 诊断报告... | default |
| `industrial-html-visualizer` | HTML可视化, 生成HTML... | default |
| `industrial-html-reviewer` | HTML审校, review HTML... | default |
| `industrial-deep-analysis` | deep analysis, 深层分析, coverage builder... | default |
| `industrial-physics-bridge` | physics bridge, 物理桥接, physics verification... | default |
| `industrial-analysis-enhance-auto` | enhance auto, 增强自动, enhancement orchestration... | default |
| `industrial-enhanced-html-visualizer` | enhanced html, 增强可视化... | default |
| `industrial-enhanced-html-reviewer` | enhanced html review, 增强审校... | default |
| `rag-knowledge-builder` | 知识库构建, 本体构建... | default |
| `diagnostic-html-visualizer` | 诊断结果可视化, dashboard... | — |
| `darwin-skill` | skill fitness, 技能评估... | — |

### Agent 角色 (14 agents)

| Agent | 人格 | 核心产出 |
|-------|------|---------|
| context-builder | 王教授 · 失效分析 | 本体+物理原理 |
| data-processor | 张工 · 流程分析 | 统计+图表+交接 |
| vlm-visual-analyzer | 老孙 · 目视巡检 | 图表视觉证据 |
| diagnostician | 刘总工 · 根因诊断 | 竞争假说+推理链 |
| judge | 陈主任 · 质量审计 | 10项评分门禁 |
| report-reviewer | 孙审计 · 物理审计 | 物理真相审计 |
| reporter | 周工 · 技术报告 | 金字塔报告 |
| html-visualizer | 林工 · HMI可视化 | ECharts+Three.js |
| html-reviewer | 赵审阅 · 页面审校 | HTML可用性审核 |
| deep-analyst | 深层分析引擎 | E1-E4 覆盖+条件+权衡 |
| physics-bridge | 物理机理桥接 | 五项物理验证+机理链 |
| enhance-orchestrator | 增强管线编排 | E0-E8 全自动增强 |
| enhanced-visualizer | 增强版前端 | 增强版 ECharts HTML |
| enhanced-html-reviewer | 增强版审校 | 增强版 HTML 审核 |

### 诊断产出目录结构
```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/          # 输入数据 + 用户上下文
├── 01_ontology/       # 本体（含 RAG 深度理解）
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
- **Backend** (`app/backend/`): Express.js + SQLite (WAL mode) + WebSocket，事件总线架构
- **Frontend** (`app/frontend/`): Vue 3 + Vite + 标签页布局（Data / Diagnose / Reports / History），SSE 实时流 + WebSocket

### RAG 检索引擎 (`rag-retrieval-engine/`)
- FastAPI + ChromaDB 向量检索 + Web 搜索
- 端点: `/retrieve`, `/score` (5 维评分), `/inject` (本体注入), `/pipeline/full`
- 不可用时自动降级：`parameter_to_physics.json` + 网络搜索

### Skill 目录约定
| 目录 | 用途 |
|------|------|
| `.claude/skills/<name>/SKILL.md` | 唯一 skill 入口 (OMP claude provider + Claude Code 发现) |
| `.claude/skills/<name>/{scripts,schemas,references,resources,templates}/` | 完整资源 |
| `.omp/agents/<name>.md` | OMP task-agent 定义 (model + tools + thinkingLevel + protocol ref) — task 创建唯一来源 |
| `.claude/agents/<name>.md` | Claude Code 格式 agent 定义 (OMP 不加载，仅 Claude Code 原生用) |

### 关键脚本
- `setup.mjs` — 创建运行目录结构
- `inspect.mjs` — 数据文件检测（CSV/JSON/TSV 流式解析）
- `stats.mjs` — 高级统计分析引擎（Pearson/Spearman/分层/延迟CCF/多重检验）
- `stats_validate.mjs` — 统计验证与鲁棒性引擎
- `validate.mjs` — JSON Schema 运行时验证（零依赖）
- `artifact-check.mjs` — 管线产物完整性验证
- `pipeline-log-check.mjs` — 管线事件日志审计
- `physics_check.py` / `dp_toolkit.py` — 物理约束验证
- `visual_analysis.py` — VLM 视觉分析
- `uv_env_setup.mjs` — Python venv 管理器

### 证据体系
| 等级 | 来源 | 置信度 |
|------|------|--------|
| L1 | 直接测量值 | 最高 |
| L2 | 用户文档 (SOP/手册) | 高 |
| L3 | 统计分析（含验证报告） | 中高 |
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
| `CLAUDE_MAX_TURNS` | `claude.max_turns` |
| `DATA_DIR` | `data.dir` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |

## Language Default

默认输出语言为**中文**。报告、诊断结论、审计文档使用中文。JSON enum 字段保持英文。

## Key Gotchas

- **双 Harness**: `.omp/` 是入口，`.claude/` 是资源。`SKILL_PATH` 通过 `<this-skill-directory>/../../../.claude/skills/<name>` 重定向
- **Python 路径**: 所有 Python 脚本必须使用 `scripts/.venv/bin/python`，非系统 python3
- **修复计数器**: `diag_iters` 由 `.pipeline_events.jsonl` 中的 `repair_spawn` 事件持久化维护
- **执行证明**: 只有 `.pipeline_events.jsonl` 通过 `pipeline-log-check.mjs` 才算完整执行
- **Expert 交接**: `data_analysis_conclusion.json` 是 data-processor→diagnostician 的强制交接文件
- **图像回退**: `image_captions.json` 是 PNG 渲染不可用时的回退方案
- **HTML 自动构建**: CP-8 ENDORSED 后默认非交互自动出 `diagnostic-report.html`（Step 8→8.5→9），仅前置 `00_input/html_opt_out` 可跳过
- **VLM Agent**: 唯一使用 `model: vision` 的 Agent，需要 vision-capable 模型读取图表 PNG
- **Agent 初始化**: 所有 Agent 读取 `references/agent-protocol.md`，不是 `agents/<self>.md` (已修复自引用 bug)
- **四套编号**: Pipeline Step / Agent Phase / Reasoning Segment / Method Stage 各独立，不可混用
