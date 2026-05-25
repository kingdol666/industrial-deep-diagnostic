# Industrial Deep Diagnostic

端到端工业深度诊断系统 — 调用 Claude Code CLI 对工业数据进行 8 阶段根因分析，结果持久化存储并通过 WebUI 可视化展示。

## 架构

```
├── config/
│   ├── default.yaml          # 全局默认配置
│   ├── local.yaml            # 用户本地覆盖配置（gitignore）
│   └── loader.mjs            # 配置加载器（合并 + 环境变量覆盖）
├── commands/
│   └── cli.mjs               # CLI 入口（ind-diag 命令）
├── app/
│   ├── backend/              # Express.js API 服务（端口 3210）
│   │   └── src/
│   │       ├── index.mjs             # 入口：HTTP + WebSocket 服务启动
│   │       ├── db/
│   │       │   └── database.mjs      # SQLite 初始化 + Prepared Statements
│   │       ├── engine/
│   │       │   ├── diagnosis-engine.mjs  # 发布/订阅事件总线
│   │       │   └── claude-client.mjs     # Claude Code CLI 集成（spawn + stdin）
│   │       ├── services/
│   │       │   ├── diagnosis.service.mjs # 诊断编排核心逻辑
│   │       │   ├── files.service.mjs     # 数据文件管理
│   │       │   └── history.service.mjs   # 历史记录 CRUD
│   │       ├── routes/
│   │       │   ├── diagnosis.routes.mjs  # 诊断 API + SSE 流
│   │       │   ├── files.routes.mjs      # 文件浏览/上传 API
│   │       │   └── history.routes.mjs    # 历史记录 API
│   │       └── transport/
│   │           └── ws-server.mjs         # WebSocket 实时推送
│   └── frontend/             # Vue 3 + Vite 前端（端口 5180）
│       └── src/
│           ├── App.vue               # 根组件，标签页路由
│           ├── api/index.js          # 后端 API 封装
│           ├── utils/markdown.js     # Markdown 渲染 + XSS 防护
│           ├── utils/time.js         # 时间格式化
│           └── components/
│               ├── data/DataBrowser.vue      # 数据文件浏览与上传
│               ├── diagnosis/DiagnosisView.vue  # 诊断主视图
│               ├── diagnosis/MessageStream.vue   # 实时消息流
│               ├── diagnosis/TaskList.vue        # 任务列表
│               ├── diagnosis/ChatInput.vue       # 对话输入框
│               ├── diagnosis/AnswerBar.vue       # AskUserQuestion 回答栏
│               ├── reports/ReportViewer.vue  # 报告查看
│               └── history/HistoryList.vue   # 历史记录
├── data/                     # 工业数据文件存放目录
├── workspace/diagnostic-runs/ # 诊断运行产出目录
└── .claude/skills/industrial-deep-diagnostic/ # Claude Code Skill 定义
```

## 前置条件

- **Node.js** >= 18
- **Claude Code CLI** 全局安装：
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
- 确保 `claude` 命令在 PATH 中可用：
  ```bash
  which claude   # 或 claude-code
  ```
- 配置 ANTHROPIC_API_KEY 环境变量

## CLI 安装

```bash
# 在项目根目录下
npm link
```

执行后 `ind-diag` 命令全局可用。

## CLI 使用

### 查看帮助

```bash
ind-diag help
```

输出：

```
  ╔══════════════════════════════════════════════╗
  ║   Industrial Deep Diagnostic — CLI v1.0       ║
  ╚══════════════════════════════════════════════╝

  Usage: ind-diag <command> [options]

  Commands:
    init                  Initialize project (check DB, config)
    config                 Manage configuration
      config list          Show merged configuration
      config get <key>     Get a config value (e.g. server.port)
      config set <key> <v> Set a config value, saves to local.yaml
      config reset <key>   Remove a key from local.yaml
      config path          Show config file paths
    backend               Start backend server (port 3210)
    frontend              Start frontend dev server (port 5180)
    all                   Start backend + frontend
    build                 Build frontend for production
    status                Project status overview
    help                  Show this help

  Examples:
    ind-diag all
    ind-diag config set server.port 9090
    ind-diag config get server.port
```

### 初始化项目

```bash
ind-diag init
```

检查配置文件、初始化 SQLite 数据库。首次使用或 clone 项目后执行一次。

### 配置管理

```bash
# 查看当前全部配置（default.yaml + local.yaml 合并结果）
ind-diag config list

# 查看单个配置项
ind-diag config get server.port
ind-diag config get claude.model
ind-diag config get database.path

# 修改配置（写入 local.yaml，不修改 default.yaml）
ind-diag config set server.port 9090
ind-diag config set claude.max_turns 300
ind-diag config set diagnosis.default_language en

# 重置配置项（删除 local.yaml 中的覆盖，恢复默认值）
ind-diag config reset server.port

# 查看配置文件路径
ind-diag config path
```

环境变量覆盖（优先级最高）：

| 环境变量 | 对应配置 |
|----------|----------|
| `SERVER_PORT` | `server.port` |
| `CLAUDE_MODEL` | `claude.model` |
| `CLAUDE_MAX_TURNS` | `claude.max_turns` |
| `CLAUDE_TIMEOUT_MINUTES` | `claude.timeout_minutes` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |
| `DATA_DIR` | `data.dir` |
| `SECURITY_HITL_TIMEOUT` | `security.hitl_auto_deny_seconds` |

### 启动服务

```bash
# 同时启动后端 + 前端（最常用）
ind-diag all

# 仅启动后端 API 服务 → http://localhost:3210
ind-diag backend

# 仅启动前端开发服务器 → http://localhost:5180
ind-diag frontend
```

`ind-diag all` 会自动安装依赖（如 node_modules 不存在），然后依次启动两个服务。按 `Ctrl+C` 同时停止。

### 前端构建

```bash
# 生产构建（输出到 app/frontend/dist/）
ind-diag build
```

构建后，后端会自动 serve 前端静态文件。只访问 `http://localhost:3210` 即可，无需单独启动前端。

### 外网映射（Webfrp）

```bash
ind-diag webfrp
```

通过 Cloudflare Tunnel 将本地服务暴露到公网。脚本会自动：
1. 检查 `cloudflared` 是否已安装（需要 `brew install cloudflared`）
2. 构建前端（如果尚未构建）
3. 启动后端服务
4. 创建 Cloudflare Tunnel 并输出公网 URL

启动后输出示例：
```
  ╔══════════════════════════════════════════════╗
  ║   Service is LIVE on the internet!            ║
  ╚══════════════════════════════════════════════╝

  Public URL:

    https://xxxx-yyyy-zzzz.trycloudflare.com

  Share this URL with anyone to access the
  Industrial Diagnostic WebUI.

  Press Ctrl+C to stop.
```

**注意事项**：
- Cloudflare Tunnel 免费使用，无需注册
- 公网 URL 每次启动随机分配，不固定
- 中国大陆访问速度可能不稳定，如需稳定访问建议使用 frp + 国内 VPS
- 按 `Ctrl+C` 停止服务

### 项目状态

```bash
ind-diag status
```

输出项目根路径、端口、数据文件数量、依赖安装状态、诊断运行记录数。

## 可选启动方式

除了 CLI，也可以使用 shell 脚本或直接 npm scripts：

```bash
# Shell 脚本
bash commands/start-backend.sh
bash commands/start-frontend.sh
bash commands/start-all.sh

# npm scripts
npm start              # = ind-diag all
npm run backend        # = ind-diag backend
npm run frontend       # = ind-diag frontend
npm run build          # = ind-diag build
npm run status         # = ind-diag status
```

## WebUI 使用流程

1. 启动服务：`ind-diag all`
2. 打开浏览器访问 **http://localhost:5180**
3. **Data 标签页** — 浏览/上传工业数据文件（CSV、XLSX、Parquet 等）。点击文件自动跳转到诊断页
4. **Diagnose 标签页** — 填写分析问题（可选），选择 Max Turns 和报告语言，点击 "Start Analysis"。右侧实时显示 Claude 的分析进度：
   - 消息流、工具调用、思考过程全部可见
   - 运行中可在底部 ChatInput 输入框发送消息引导分析方向
   - 失败后可输入 follow-up 指令恢复诊断
5. **Reports 标签页** — 查看已完成的诊断报告（Markdown 渲染）
6. **History 标签页** — 浏览所有历史诊断记录，点击继续或查看报告

## API 端点

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

### 数据文件

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files/data` | 列出数据目录 |
| GET | `/api/files/data/:folder` | 列出子文件夹内容 |
| POST | `/api/files/data/folder` | 创建子文件夹 |
| DELETE | `/api/files/data/folder/:name` | 删除子文件夹 |
| POST | `/api/files/data/upload` | 上传文件（multipart） |
| GET | `/api/files/data/file/*` | 读取/下载文件内容 |

### 诊断

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/diagnosis/start` | 创建诊断任务（pending 状态） |
| POST | `/api/diagnosis/execute/:runId` | 触发执行 pending 任务 |
| GET | `/api/diagnosis/stream/:runId` | SSE 流式诊断输出 |
| GET | `/api/diagnosis/status/:runId` | 查询任务状态 |
| POST | `/api/diagnosis/stop/:runId` | 停止运行中的诊断 |
| POST | `/api/diagnosis/chat/:runId` | 向运行中的 Claude 发送消息 |
| POST | `/api/diagnosis/continue/:runId` | 恢复失败/停止的诊断（可附带 follow-up） |
| POST | `/api/diagnosis/hitl/:hitlId` | 审批/拒绝危险命令 |
| POST | `/api/diagnosis/answer/:runId` | 回答 AskUserQuestion |
| GET | `/api/diagnosis/hitl/:runId` | 检查待处理 HITL 请求 |
| GET | `/api/diagnosis/list` | 列出所有诊断任务 |

### 工作区

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files/workspace` | 诊断运行列表 |
| GET | `/api/files/workspace/report/:name` | 获取报告 Markdown |
| GET | `/api/files/workspace/optimizer/:name` | 获取优化建议 |
| GET | `/api/files/workspace/files/:name` | 列出运行产出文件 |
| GET | `/api/files/workspace/asset/:name/*` | 获取产物中的静态资源（图片等） |

### 历史

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history/runs` | 历史记录列表 |
| GET | `/api/history/runs/:runId` | 单条记录详情（含日志） |
| DELETE | `/api/history/runs/:runId` | 删除记录 |

### WebSocket

```
ws://localhost:3210/ws
```

支持消息类型：`subscribe`、`unsubscribe`、`list_runs`、`ping`、`hitl_respond`

## 配置参考

完整配置项见 `config/default.yaml`。关键配置：

```yaml
server:
  port: 3210                    # 后端端口

frontend:
  port: 5180                    # 前端开发服务器端口

claude:
  model: "claude-opus-4-7"      # 默认模型
  max_turns: 200                # 最大对话轮数（0=不限制）
  timeout_minutes: 120          # 单个诊断超时时间

diagnosis:
  default_language: "zh"        # 报告语言（zh/en）
  run_id_length: 8              # run ID 长度

security:
  hitl_auto_deny_seconds: 120   # 危险命令审批超时自动拒绝
  dangerous_patterns: [...]     # 22 种危险命令检测规则
```

## 诊断输出

每次诊断在 `workspace/diagnostic-runs/<timestamp>_<scene_name>/` 下产出：

```
00_input/         # 输入数据副本
01_ontology/      # 字段类型推断
02_processed/     # 清洗后数据
03_figures/       # 可视化图表
04_diagnostics/   # 中间诊断结果
05_review/        # Judge 评审反馈
06_scripts/       # 分析脚本
report.md         # 最终诊断报告
optimizer.md      # 优化建议
```

## 生产部署

```bash
# 1. 构建前端
ind-diag build

# 2. 启动后端（自动 serve 前端 + API）
ind-diag backend
```

访问 **http://localhost:3210** 即可。前端构建产物已包含在内，无需单独部署。
