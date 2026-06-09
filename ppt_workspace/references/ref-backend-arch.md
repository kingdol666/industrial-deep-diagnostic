---
name: backend-architecture
description: 后端架构评估 — Express+SQLite+WebSocket 事件总线设计
metadata: 
  node_type: memory
  type: project
  originSessionId: a048abac-a95d-468f-b017-6840248bcbae
---

# 后端架构评估

## 总体评分: ⭐⭐⭐⭐ (4/5) — 扎实、实用、可扩展

## 架构层次

```
index.mjs (入口)
  ├── routes/ (5个) — 薄路由层，委托 service
  ├── services/ (5个) — 业务逻辑
  ├── engine/ — 核心引擎
  │   ├── diagnosis-engine.mjs — EventEmitter 事件总线
  │   └── claude-client.mjs — Claude CLI 进程管理
  ├── transport/
  │   └── ws-server.mjs — WebSocket 服务端 (~650行)
  └── db/
      └── database.mjs — SQLite WAL + prepared statements
```

## 设计亮点

### 1. 事件总线 (diagnosis-engine.mjs) — ⭐⭐⭐⭐⭐
- `EventEmitter` 解耦 Claude CLI 进程事件与 WS/SSE 传输
- Per-run 状态: subscribers + child process + event buffer
- 双持久化: 内存 buffer (快速 replay) + SQLite event_stream 表 (持久化)
- 自动清理: 5 分钟间隔清理已完成无订阅者的 run
- `subscribe()` 自动 replay 历史 events 给新订阅者
- **评价**: 这是整个后端最精妙的设计。简洁但功能完备，支持断线重连、历史回放、状态广播。

### 2. WebSocket 协议设计 — ⭐⭐⭐⭐½
- 双通道: 诊断 run + chat 对话
- 消息类型: catalog_snapshot / run_snapshot / run_event / chat_event / hitl_respond
- 客户端状态管理: `WeakMap<ws, clientState>` 追踪订阅
- 广播机制: engine event → 自动 catalog + run status 广播
- **评价**: 协议设计完整，涵盖了实时诊断流、对话、HITL（人机协同）三大场景。

### 3. Claude CLI 客户端 — ⭐⭐⭐⭐
- 子进程管理 Claude Code CLI
- JSON streaming 解析
- 错误恢复和超时处理
- **评价**: 通过 CLI 子进程调用 Claude 是务实的方案，避免了 SDK 依赖。但进程管理有改进空间。

### 4. SQLite WAL 模式 — ⭐⭐⭐⭐
- WAL 模式支持并发读写
- Prepared statements 预编译
- Stale run 自动标记 (服务器重启时)
- **评价**: 对于单机部署恰到好处。如果需要多实例部署，需考虑 PostgreSQL。

## 可改进之处

### 1. 认证/授权 — 缺失
- API 完全开放，无认证机制
- RAG 引擎有可选 API Key，但主后端没有
- **建议**: 至少添加 Bearer token 或 API key 认证

### 2. 测试 — 零覆盖
- 无任何自动化测试
- **建议**: 优先为 diagnosis.service 和 chat.service 添加集成测试

### 3. ws-server.mjs 过于庞大 (650行)
- 消息路由、事件映射、chat 映射全部混在一个文件
- **建议**: 拆分为 message-handler + event-mapper + chat-mapper

### 4. 错误处理粒度
- 部分路由缺少细粒度错误分类
- **建议**: 引入自定义错误类 (NotFoundError, ValidationError 等)

## 数据模型

SQLite 核心表:
- `diagnosis_runs` — 诊断运行 (run_id, status, scene_name, score, verdict)
- `diagnosis_events` — 诊断事件流 (run_id, seq, event_type, payload)
- `chat_sessions` — 对话会话 (chat_id, session_id, status)
- `chat_messages` — 对话消息 (chat_id, seq, event_type, content)

## 关联记忆
- [[project-overview]]
- [[skill-design-assessment]]
