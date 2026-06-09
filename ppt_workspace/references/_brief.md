# Industrial Deep Diagnostic — PPT 架构介绍

## 主题
Industrial Deep Diagnostic 项目架构介绍

## 副标题
工业深度诊断系统 — 多智能体诊断 Skill + RAG 知识引擎 + Web 应用

## 目标受众
技术团队 / 架构师 / AI 工程师 / 潜在用户

## 预估页数
12 页

## 语言
中文

## 需要搜索的知识维度

### 维度1: 诊断 Skill 管线架构
- 8 步管线流程 (Step 0-8)
- 7 个子智能体角色与职责
- 竞争性假设协议 (ACH)
- 修复循环机制 (Judge→Diagnostician max 3, Reviewer max 2)
- Schema-First 写入协议
- 双驱动诊断 (纯工艺 + 工艺-检测)

### 维度2: RAG Knowledge Builder 架构
- 三阶段管线: Retrieve → Score → Inject
- ChromaDB 向量检索 + sentence-transformers
- 5 维相关度评分系统
- 多源知识索引 (Markdown/JSON/PDF/CSV/Web)
- FastAPI 微服务端点设计

### 维度3: 整体系统架构
- Express.js 后端 + SQLite WAL + WebSocket 事件总线
- Vue 3 + Vite + ECharts 前端
- RAG 引擎与诊断 Skill 的集成点
- CLI 工具 ind-diag
- Docker + nginx 部署方案

### 维度4: 技术栈与工程实践
- 多智能体解耦设计 (workspace 文件通信)
- 渐进式加载架构 (3级)
- JSON Schema 验证体系 (14个schema)
- Agent Memory 跨会话记忆
- 执行证明 (.pipeline_events.jsonl)

### 维度5: 行业价值与对比
- 场景自适应 vs 固定模板诊断
- 物理第一性原理 vs 纯统计相关
- 证据等级体系 (7级)
