# Industrial Deep Diagnostic

端到端工业深度诊断系统 — 调用 Claude Code CLI 对工业数据进行 8 阶段根因分析，结果持久化存储并可视化展示。

## 架构

```
app/
├── backend/           # Express.js API 服务 (端口 3210)
│   └── src/
│       ├── index.mjs          # 入口，路由挂载，静态文件服务
│       ├── db.mjs             # SQLite 数据库初始化 + Prepared Statements
│       ├── claude-code.mjs    # Claude Code CLI 集成层
│       └── routes/
│           ├── diagnosis.mjs  # 诊断任务管理 + SSE 流式输出
│           ├── files.mjs      # 数据文件和工作区文件浏览
│           └── history.mjs    # 历史诊断记录管理
├── frontend/          # Vue 3 + Vite 前端 (端口 5173)
│   └── src/
│       ├── App.vue            # 根组件，标签页路由
│       ├── api.js             # 后端 API 封装
│       └── components/
│           ├── DataBrowser.vue    # 数据文件浏览与上传
│           ├── DiagnosisPanel.vue # 诊断配置与 SSE 实时输出
│           ├── ReportViewer.vue   # 诊断报告查看
│           └── HistoryList.vue    # 历史记录管理
```

## 前置条件

- **Node.js** >= 18
- **Claude Code CLI** 全局安装：
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
- 确保 `claude` 命令在 PATH 中可用：
  ```bash
  which claude
  ```

## 快速启动

### 1. 安装依赖

```bash
cd app/backend && npm install
cd app/frontend && npm install
```

### 2. 启动后端 (端口 3210)

```bash
cd app/backend
npm run dev
```

### 3. 启动前端开发服务器 (端口 5173)

```bash
cd app/frontend
npx vite --port 5173
```

### 4. 打开浏览器

访问 **http://localhost:5173**

## 使用流程

1. **Data 标签页** — 选择要分析的数据文件（CSV 格式），点击文件自动跳转到诊断页
2. **Diagnose 标签页** — 填写分析问题，点击 "Start Analysis" 开始诊断。右侧实时显示 Claude 的分析进度
3. **Reports 标签页** — 查看已完成的诊断报告，支持下载和复制
4. **History 标签页** — 浏览所有历史诊断记录，点击可打开对应报告

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/files/data` | 列出数据文件 |
| POST | `/api/diagnosis/start` | 创建诊断任务 |
| GET | `/api/diagnosis/stream/:runId` | SSE 流式诊断输出 |
| GET | `/api/diagnosis/status/:runId` | 查询任务状态 |
| POST | `/api/diagnosis/stop/:runId` | 停止诊断 |
| GET | `/api/history/runs` | 历史记录列表 |
| GET | `/api/history/runs/:runId` | 单条记录详情（含日志） |
| GET | `/api/files/workspace` | 工作区诊断运行列表 |
| GET | `/api/files/workspace/report/:name` | 获取报告内容 |
| GET | `/api/files/workspace/files/:name` | 列出运行工作区文件 |

## 数据存储

- **数据库**：SQLite，位置 `app/backend/data/diagnostic.db`
- **数据文件**：`data/` 目录下
- **诊断产出**：`workspace/diagnostic-runs/<timestamp>_<scene_name>/`

## 生产部署

```bash
cd app/frontend && npm run build
cd app/backend && npm start
```

后端会自动 serve 前端构建产物，只需访问 **http://localhost:3210** 即可。
