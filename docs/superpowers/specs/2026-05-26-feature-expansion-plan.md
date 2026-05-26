# Industrial Deep Diagnostic — Feature Expansion Plan

## 概述

在现有 8 阶段诊断引擎基础上，沿 **6 个维度**扩展项目能力。每个维度独立可落地，按依赖关系排序。

---

## 维度一：数据接入

### 现状
手动上传 CSV/XLSX/Parquet 到 `data/` 目录 → 前端 DataBrowser 选择 → 分析

### 目标架构

```
OPC UA Server ──┐
MQTT Broker ────┤
PostgreSQL ─────┤──→ 数据接入层 → 数据管道 → 诊断引擎
REST API ───────┘     (adapter)   (scheduler)
S3/MinIO ──────┘
```

### 具体实现

| 子功能 | 技术选型 | 实现方式 |
|--------|---------|---------|
| **时序数据库直连** | InfluxDB v2 + 官方 Node.js client | 新 `app/backend/src/connectors/influxdb.mjs`，支持按时间范围拉取 + 自动重采样 |
| **OPC UA 接入** | node-opcua | `connectors/opcua.mjs`，订阅变量变化，按配置频率轮询或订阅式推送 |
| **MQTT 物联网协议** | mqtt.js | `connectors/mqtt.mjs`，订阅 topic，消息入缓冲区 → 批量写入诊断数据目录 |
| **文件系统监听** | chokidar | `connectors/file-watcher.mjs`，监听 `data/hot/` 目录，新文件到达自动触发分析 |
| **REST API 推送** | 现有 Express | 新增 `POST /api/ingest` 端点，接受 JSON/CSV payload，校验后入队 |
| **定时拉取** | node-cron | `connectors/scheduler.mjs`，cron 表达式配置，定时从外部源抓取数据 |

### 添加文件
```
app/backend/src/connectors/
├── influxdb.mjs     # InfluxDB connector
├── opcua.mjs        # OPC UA connector  
├── mqtt.mjs         # MQTT connector
├── file-watcher.mjs # Hot directory watcher
├── scheduler.mjs    # Cron-based scheduler
└── index.mjs        # Unified connector registry
```

### 前端改动
DataBrowser 新增"数据源"tab：列出已配置的连接器、连接状态、手动触发拉取。

---

## 维度二：诊断覆盖面扩展

### 现状
时序异常检测 + 根因分析（单次诊断，输出报告）

### 目标
```
诊断引擎
├── 实时异常检测     → 流式+告警
├── 预测性维护       → 剩余寿命(RUL)预测 + 维护建议
├── 设备健康管理     → 多指标综合健康评分(HI)
├── 工艺优化建议     → 参数推荐 + DOE 分析
└── 批量历史分析     → 定时巡检 + 趋势报告
```

### 具体实现

| 子功能 | 技术选型 | 说明 |
|--------|---------|------|
| **流式异常检测** | 统计阈值 + 滑动窗口 | `engine/streaming-detector.mjs`，接收实时数据点，用 EWMA + 3-sigma 判决 |
| **RUL 预测** | scikit-learn 离线训练 + ONNX 部署 | 新 Python 脚本 `scripts/predictive.py`，支持线性退化 + 指数退化 + 简单 MLP |
| **设备健康指数** | 多指标加权融合 | 温度/振动/电流/压力 → 归一化 → 加权综合 → 0-100 分 |
| **定时巡检** | node-cron + 现有诊断引擎 | `scheduler.mjs` 定时触发 `executeDiagnosis()`，结果写入新表 `inspection_runs` |
| **多工况对比** | 系统自带 | 现有 GPU 支持 batch 执行多个 run，前端增加对比视图 |

### 技术栈扩展
```bash
# Python 扩展
pip install scikit-learn onnxruntime pandas numpy

# Node.js 扩展
npm install node-cron @influxdata/influxdb-client
```

---

## 维度三：协同能力

### 现状
单机使用，所有用户共享同一个后端，无身份隔离

### 目标架构
```
多用户 ─→ Auth Gateway ─→ 角色权限 ─→ 隔离的工作空间
  │                         ├── admin: 全部权限
  │                         ├── engineer: 诊断+报告
  │                         └── viewer: 只读
```

### 具体实现

| 子功能 | 技术选型 | 说明 |
|--------|---------|------|
| **用户认证** | 简单 JWT（无需第三方） | `routes/auth.routes.mjs` + `middleware/auth.mjs`，注册/登录/Token 刷新 |
| **用户管理** | SQLite 新表 `users` | 表结构: id, username, password_hash, role, created_at |
| **角色权限** | 中间件守卫 | `requireRole('admin')` 装饰 route; 权限矩阵: admin/engineer/viewer |
| **团队空间** | 新表 + 文件隔离 | 每个用户一个独立的工作空间目录，数据相互隔离 |
| **分享报告** | 分享链接 (token) | 生成一次性/限时分享链接，无需登录可查看 |
| **审计日志** | 新表 `audit_logs` | 记录谁在什么时间做了什么操作 |

### 添加文件
```
app/backend/src/
├── middleware/auth.mjs        # JWT 验证中间件
├── routes/auth.routes.mjs    # 登录/注册/刷新
├── services/auth.service.mjs # 用户 CRUD
└── roles.mjs                 # 权限矩阵定义
```

### 前端改动
- 登录页面
- 用户设置页面（修改密码等）
- API 调用统一附加 Authorization header

---

## 维度四：告警与通知

### 现状
诊断完成后用户需要手动刷新前端查看结果

### 目标
自动通知链：异常检测 → 诊断完成 → 推送到用户选择的渠道

### 具体实现

| 渠道 | 技术选型 | 说明 |
|------|---------|------|
| **Web 推送** | 浏览器 Notification API + Service Worker | `frontend/src/utils/notify.js`，诊断完成时弹桌面通知 |
| **邮件** | nodemailer | `services/notification/email.mjs`，SMTP 配置 |
| **企业微信/钉钉** | Webhook | `services/notification/webhook.mjs`，支持配置多个 webhook URL |
| **Telegram** | Telegram Bot API | `services/notification/telegram.mjs`，bot token + chat ID 配置 |
| **WebSocket** | 现有 ws server | 诊断完成事件通过已连接的 WebSocket 推送 |

### 配置扩展示例
```yaml
# config/default.yaml
notifications:
  email:
    enabled: false
    smtp_host: "smtp.example.com"
    smtp_port: 587
    from: "diagnostic@example.com"
  webhook:
    enabled: false
    urls: []
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
```

---

## 维度五：知识系统升级

### 现状
4 个领域的硬编码 Markdown 知识库，作为 prompt 注入诊断引擎

### 目标架构
```
诊断提问
   │
   ▼
知识检索层 ───→ 向量知识库 (ChromaDB/LanceDB)
   │                  │
   │            ├── 领域知识文档
   │            ├── 历史诊断报告
   │            └── 用户标注反馈
   │
   ▼
检索增强(RAG) ───→ 精选上下文注入诊断 Prompt
```

### 具体实现

| 子功能 | 技术选型 | 说明 |
|--------|---------|------|
| **向量知识库** | LanceDB (嵌入式，零依赖) | `knowledge/vector-store.mjs`，初始化快，不需要独立服务 |
| **知识注入** | RAG 检索 + Prompt 拼接 | `knowledge/retriever.mjs`，诊断前检索 Top-K 片段拼入 prompt |
| **历史诊断学习** | 自动提取关键发现 | 新脚本 `scripts/extract_learnings.py`，从历史 report.md 提取因果规则 |
| **用户反馈闭环** | 新表 `knowledge_feedback` | 用户可标记诊断结论 "有用/无用" → 影响检索权重 |
| **知识图谱** | 轻量 JSON Graph | `knowledge/graph.json`，实体-关系-实体三元组，手动或自动构建 |

### 技术栈
```bash
npm install lancedb @anthropic-ai/sdk
# 或纯 Node.js 实现（避免原生依赖）:
# 用 simple-json-store + 关键词搜索做轻量 RAG
```

### 前端改动
新增 Knowledge 标签页：
- 浏览知识库内容
- 手动添加/编辑知识条目
- 查看检索历史（诊断使用了哪些知识）

---

## 维度六：可视化系统升级

### 现状
Python Matplotlib 生成静态 PNG 图片嵌入 Markdown 报告

### 目标
```
可视化层
├── 交互式诊断仪表盘
│   ├── 实时数据流折线图
│   ├── 多变量关联散点图
│   ├── 频谱/FFT 分析图
│   └── 相关性热力图
├── 报告内嵌动态图
│   └── 可缩放/可筛选的时间序列
└── 对比视图
    └── 多 run 结果叠放对比
```

### 具体实现

**方案 A（推荐，渐进式）：ECharts 替换 Matplotlib**

保留现有 Matplotlib 管线，新增一个前端可视化层：

| 组件 | 技术 | 说明 |
|------|------|------|
| **图表组件** | ECharts (apache-echarts) | `frontend/src/components/charts/` 目录，5-8 个图表类型 |
| **数据接口** | 后端新 endpoint | `GET /api/analysis/chart-data/:runId` 返回诊断过程中的中间数据 |
| **实时流** | WebSocket + ECharts 增量更新 | 诊断进行中即展示图表（不需要等报告完成） |
| **报告图表** | 双轨：保留静态图 + 新增交互式 | 报告 Markdown 中既嵌入 PNG，也提供"查看交互版"链接 |

**ECharts 图表类型：**

```
LineChart.vue        — 时序折线图（可缩放，多 Y 轴）
ScatterChart.vue     — 散点/气泡图（相关性）
HeatmapChart.vue     — 热力图（Pearson/Spearman 矩阵）
GaugeChart.vue       — 仪表盘（健康评分 0-100）
RadarChart.vue       — 雷达图（多维度能力对比）
BarChart.vue         — 柱状图（参数分布）
WaterfallChart.vue   — 瀑布图（根因贡献分解）
```

**方案 B（高级）：Grafana 集成**

如果用户已有 Grafana 基础设施：
- 诊断结果写入 Prometheus/Pushgateway
- Grafana dashboard 直接展示实时和历史数据
- 诊断引擎作为 Grafana 的数据源插件

### 前端改动
```bash
npm install echarts vue-echarts
```

新组件目录：`frontend/src/components/charts/`
DiagnosisView 中新增 Dashboard 子视图（含实时图表面板）

---

## 维度七：部署与运维

### 现状
手动的 `node app/backend/src/index.mjs` + `npx vite` 启动

### 目标架构
```
用户
 ├── Docker Compose (单机)
 │   ├── backend:3210
 │   ├── frontend:5180 (Vite proxy → backend)
 │   └── (可选) InfluxDB:8086
 │
 └── Docker Swarm / K8s (集群，未来)
     ├── 后端 replicas=2
     ├── SQLite → PostgreSQL 迁移
     └── Traefik/nginx 反向代理
```

### 具体实现

| 子功能 | 技术 | 说明 |
|--------|------|------|
| **Dockerfile** | 多阶段构建 | 前端 Vite build → nginx 托管静态文件；后端 node:22-alpine |
| **docker-compose.yml** | Docker Compose v3 | backend + (可选 InfluxDB) + (可选 PostgreSQL) |
| **生产 nginx 配置** | nginx | 反向代理 /api → backend，托管 /dist，gzip，CORS |
| **健康检查** | 现有 `/api/health` + Docker HEALTHCHECK | 后端存活 + 就绪探测 |
| **日志持久化** | winston 或 pino | 替换 console.log，输出 JSON 格式到 stdout + 文件 |
| **环境变量模板** | .env.example | 所有配置点集中在一个文件 |

### Dockerfile 示例结构
```dockerfile
# Stage 1: Build frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY app/frontend/ ./
RUN npm ci && npm run build

# Stage 2: Build backend
FROM node:22-alpine AS backend
WORKDIR /app
COPY app/backend/ ./backend/
COPY config/ ./config/
COPY commands/ ./commands/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
RUN cd backend && npm ci --production
EXPOSE 3210
CMD ["node", "backend/src/index.mjs"]
```

---

## 优先级路线图

```
Phase 1 (基础加固 · 2周)
├── Docker + docker-compose
├── 结构化日志 (winston/pino)
├── .env.example + 环境变量统一
└── 健康检查 + Docker HEALTHCHECK

Phase 2 (数据接入 · 2周)
├── InfluxDB 连接器
├── 文件监听器 (chokidar)
├── MQTT 连接器
└── 前端数据源管理界面

Phase 3 (可视化升级 · 2周)
├── ECharts 集成
├── 诊断过程实时折线图
├── 相关性热力图
└── 对比视图

Phase 4 (告警协同 · 2周)
├── 用户认证 (JWT)
├── 通知系统 (邮件/Webhook)
├── 定时巡检
└── 分享报告

Phase 5 (知识升级 · 2周)
├── LanceDB 向量知识库
├── RAG 检索注入
├── 历史诊断学习
└── 知识图谱

Phase 6 (高级诊断 · 2周)
├── 实时流式异常检测
├── RUL 预测
├── 设备健康指数
└── 多工况对比视图
```

---

## 技术栈汇总

| 领域 | 新增技术 | 类型 | 成熟度 |
|------|---------|------|--------|
| 数据接入 | InfluxDB, MQTT, OPC UA | 外部服务 | 生产级 |
| 定时调度 | node-cron | npm 包 | 生产级 |
| 用户认证 | jsonwebtoken, bcrypt | npm 包 | 生产级 |
| 通知 | nodemailer, Telegram Bot API | npm 包 / API | 生产级 |
| 向量知识库 | LanceDB | npm 包 | 生产级 |
| 可视化 | ECharts / vue-echarts | npm 包 | 生产级 |
| 部署 | Docker, nginx, winston | 基础设施 | 生产级 |
| RUL 预测 | scikit-learn, ONNX | Python 包 | 研究级 |
| OPC UA | node-opcua | npm 包 | 生产级 |
