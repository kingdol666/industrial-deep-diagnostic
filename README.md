# Industrial Deep Diagnostic

面向工业时序数据的工程化诊断项目：提供一个可运行的 Web/CLI 应用，以及两套核心 Skill（工业诊断 Skill 与 RAG 本体构建 Skill），用于完成**数据分析 → 本体理解 → 物理推理 → 根因诊断 → 报告交付**的完整闭环。

## 项目定位

这个仓库不是单一脚本，而是一个由以下部分组成的完整系统：
- **诊断应用层**：CLI、后端 API、前端 WebUI、历史记录与任务运行管理
- **诊断 Skill 层**：`.claude/skills/industrial-deep-diagnostic/`，负责工业数据分析与异常诊断
- **RAG Skill 层**：`.claude/skills/rag-knowledge-builder/`，负责知识检索与本体构建
- **RAG Engine 服务层**：`rag-retrieval-engine/`，为 RAG Skill 提供 HTTP 检索与知识注入能力
- **数据与运行产物层**：`data/`、`workspace/diagnostic-runs/`、`workspace/rag-outputs/`
- **项目文档层**：`docs/architecture/`、`docs/guides/`、`docs/reference/`

## 核心能力

- **工业数据自动分析**：支持 CSV、XLSX、Parquet、JSON、Feather 等列式数据
- **双驱动诊断**：同时支持纯工艺波动诊断与工艺+检测双驱动诊断
- **本体与物理推理**：通过本体模型、RAG 知识与一阶物理原理解释统计发现
- **多子代理流水线**：context-builder、data-processor、VLM visual analyzer、diagnostician、judge、reporter、report-reviewer
- **执行证明与证据闭环**：通过 `.pipeline_events.jsonl`、`run_manifest.json`、`evidence_closure_report.json` 验证流程真的被执行且结论可追溯
- **报告交付**：生成结构化 JSON 工件和中文 Markdown 诊断报告

## 仓库结构

```text
.
├── README.md
├── CLAUDE.md
├── commands/                     # CLI 入口与启动命令
├── app/
│   ├── backend/                  # Express / API / 历史记录 / Claude CLI 集成
│   └── frontend/                 # Vue WebUI
├── config/                       # 配置系统
├── data/                         # 样例数据、评测数据、参考资料
├── docs/                         # 项目架构、指南与参考文档
├── rag-retrieval-engine/         # 独立 RAG 检索服务
├── workspace/
│   ├── diagnostic-runs/          # 诊断流水线运行产物
│   └── rag-outputs/              # RAG / 本体构建产物
└── .claude/skills/
    ├── industrial-deep-diagnostic/
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── agents/
    │   ├── schemas/
    │   ├── scripts/
    │   └── resources/
    └── rag-knowledge-builder/
        ├── SKILL.md
        ├── README.md
        └── ...
```

## 组件关系

```text
WebUI / CLI
    │
    ▼
Diagnosis Orchestrator
    │
    ├── Industrial Deep Diagnostic Skill
    │     ├── Context Builder
    │     ├── Data Processor
    │     ├── VLM Visual Analyzer
    │     ├── Diagnostician
    │     ├── Judge
    │     ├── Reporter
    │     └── Report Reviewer
    │
    └── RAG Knowledge Builder Skill
          └── RAG Retrieval Engine (HTTP service)
```

## 快速开始

### 1. 环境要求

- Node.js `>= 18`
- Python `>= 3.9`
- 推荐安装 `uv`
- Claude Code CLI 可用（若要通过项目应用直接驱动 Claude）
- 若启用 RAG 检索，建议准备 `rag-retrieval-engine`

### 2. 安装依赖

```bash
npm install
```

### 3. 初始化 CLI

```bash
npm link
ind-diag init
```

### 4. 启动应用

```bash
ind-diag all
```

默认情况下：
- 后端：`http://localhost:3210`
- 前端：`http://localhost:5180`

### 5. 启动 RAG Engine（可选但推荐）

```bash
cd rag-retrieval-engine
uv sync
uv run python server.py
```

## 常用工作流

### 应用层工作流

```bash
ind-diag backend
ind-diag frontend
ind-diag all
ind-diag build
ind-diag status
```

### Skill 层工作流

- 工业诊断 Skill：见 `.`claude/skills/industrial-deep-diagnostic/README.md:1`
- RAG 本体 Skill：见 `.`claude/skills/rag-knowledge-builder/README.md:1`
- RAG 引擎服务：见 `rag-retrieval-engine/README.md:1`

## 运行产物

### 诊断产物

默认输出到：`workspace/diagnostic-runs/<timestamp>_<scene_name>/`

重要文件包括：
- `00_input/run_config.json`
- `01_ontology/ontology.json`
- `02_processed/data_analysis_conclusion.json`
- `03_figures/visual_analysis.json`
- `04_diagnostics/diagnosis.json`
- `report.md`
- `.pipeline_events.jsonl`
- `evidence_closure_report.json`

### RAG 产物

默认输出到：`workspace/rag-outputs/<timestamp>_<domain>/`

重要文件包括：
- `rag_ontology_draft.json`
- `rag_ontology_nl_spec.md`
- `rag_structured_data.json`
- `rag_audit_log.json`

## 文档导航

- **项目总体说明**：`README.md`
- **项目开发说明**：`CLAUDE.md`
- **系统架构说明**：`docs/architecture/system-overview.md`
- **仓库结构说明**：`docs/architecture/repository-layout.md`
- **数据流说明**：`docs/architecture/data-flow.md`
- **工业诊断 Skill**：`.`claude/skills/industrial-deep-diagnostic/README.md:1`
- **RAG 本体 Skill**：`.`claude/skills/rag-knowledge-builder/README.md:1`
- **RAG HTTP 服务**：`rag-retrieval-engine/README.md:1`

## 当前适用范围

本项目当前最适合：
- 工业过程时序数据分析
- 异常检测与根因诊断
- 工艺参数波动分析
- 质量缺陷与工艺变量关联诊断
- 基于本体与行业知识的诊断支撑

不适合：
- 一般数据可视化小工具
- 财务、舆情、非工业场景分析
- 只有简单问答、没有结构化诊断需求的任务

## 推荐阅读顺序

如果你第一次进入这个项目，建议按顺序阅读：
1. `README.md`
2. `.`claude/skills/industrial-deep-diagnostic/README.md:1`
3. `.`claude/skills/industrial-deep-diagnostic/SKILL.md:1`
4. `.`claude/skills/rag-knowledge-builder/README.md:1`
5. `rag-retrieval-engine/README.md:1`

## License

- 项目根 `package.json` 当前标记为 `ISC`
- 部分子目录 README 仍写有 `MIT`

如果后续要对外发布，建议统一许可证声明。
