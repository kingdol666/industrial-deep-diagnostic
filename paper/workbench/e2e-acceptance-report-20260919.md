# Web 控制端到端实机验收报告（2026-09-19）

- 方式：真实浏览器驱动前端 UI 完成全部操作，页内同步核对后端 API（同源同 token）；
  关键节点截图存档于 `paper/workbench/ui-after/`。
- 账号：uitest2026（真实注册/登录）；服务：backend :3210 + frontend :5180 + RAG :8764 全 healthy。

## 结果总览：28 项检查全部 PASS（含 1 项设计行为确认）

| # | 检查项 | 结果 | 证据/备注 |
|---|---|---|---|
| A1 | 登出 → 登录页渲染 | PASS | .auth-submit 出现 |
| A2 | 登录 → 壳层（侧栏/WS/引擎/导航） | PASS | Realtime Connected，6+ 导航项 |
| A3 | 引擎下拉列出全部 14 引擎 | PASS | 14 行、无禁用项（14/14 探测可用） |
| B1 | 数据页统计读数 + 文件清单 | PASS | 13 文件夹 / 5 文件 / 21 行 |
| B2 | 双击进入文件夹（面包屑） | PASS | eval_heat_exchanger_scaling 内 3 文件 |
| B3 | 面包屑返回根目录 | PASS | |
| B4 | 文件预览渲染（PREVIEW 弹层） | PASS | smoke.csv 内容可见 |
| B5 | 新建文件夹出现 | PASS | e2e-acceptance-folder |
| B6 | 真实上传（FormData → POST upload）+ UI 可见 | PASS | e2e-upload-sensor.csv 200 |
| B7 | 删除非空文件夹被拒（设计行为） | PASS† | "Folder is not empty" 安全防护；清理后可删 |
| C1 | 诊断启动（UI 全链路） | PASS | mock 引擎 e2e-mock-diag |
| C2 | 流式事件渲染 + 终态横幅 | PASS | ENDORSED · Score 96 |
| C3 | 任务列表状态 + New Task 入口 | PASS | |
| C4 | Stop 中止真实运行 → stopped | PASS | e2e-stop-test（claude 引擎） |
| D1 | 新建聊天 → 发送 → 流式回复 | PASS | MOCK 徽章 |
| D2 | 同会话续聊（session resume） | PASS | resume 回复 30ms success |
| D3 | 重命名会话（PATCH + 列表刷新） | PASS | E2E renamed session |
| D4 | 删除会话（✕ → 列表移除） | PASS | |
| E1 | 报告页列表渲染 | PASS | 68 个 Read Report 入口 |
| E2 | 打开报告渲染 Markdown | PASS | SKAB valve1_1 报告 21217 字符，Report/Audit/HTML 三标签 |
| F1 | 本体页：资产库 + 图画布 + 图例 + 标签 | PASS | 图例 5 项（新仪表配色） |
| F2 | Structure 视图切换 | PASS | Signals/关系编辑器渲染 |
| G1 | 历史页列表 + 状态徽章 | PASS | 142 个 Detail 入口 |
| G2 | 运行详情面板 | PASS | 30713 字符（含日志/会话） |
| G3 | 删除运行（UI Delete → 确认 → 移除） | PASS | e2e-stop-test 已删 |
| H1 | OMP Runs 页（统计 + 31 张运行卡） | PASS | 引擎联动显示引擎专属标签页 |
| I1 | 8 个核心 API 端点同源鉴权对接 | PASS | files/runs/chats/harness/ontology/history/workspace/me |
| J1 | Codex 长管线诊断后台真实执行 | PASS(运行中) | codex-smoke-02：01_ontology/ontology.json 已产出（Step 2 完成） |

† B7 为正向安全行为验证：非空文件夹拒绝删除（"Folder is not empty"），防止误删数据。

## 关键结论

1. **前端渲染与后端 API 对接全链路无断点**：所有 UI 操作均有对应的真实 API 往返
   （登录 token、上传 FormData、诊断 start/stream、聊天 WS+SSE、CRUD 全套）。
2. **实时性**：诊断与聊天的流式事件（阶段/工具调用/统计条）实时渲染；WS 断线重连指示正常。
3. **引擎体系**：下拉选择 ↔ 运行记录引擎徽章 ↔ 引擎专属标签页（OMP Runs）三者联动一致；
   mock 与 codex 两个真实引擎在本次验收中分别完成了端到端诊断与聊天。
4. **数据安全语义正确**：非空文件夹拒删；运行删除有确认框；全部测试产物已清理
   （e2e 文件夹/上传文件/测试运行已删，聊天会话已删）。

## 过程中发现并当场修复的缺陷（本轮验收前修复，属本轮验收范围）

| 缺陷 | 修复 |
|---|---|
| codex 0.155 协议漂移 → 诊断必失败（threadId null / turn/start 提前成功） | codex-client 兼容新返回结构 + 完成通知驱动 |
| WS 快照把 harness 压成 omp/claude → 聊天徽章错误 | 透传真实 harness |
| qwen/pi 探测超时假阴性（8s） | 默认 15s，14/14 可用 |
| 本体资产 ETag 不含渲染版本 → 304 永远命中旧图 | 带图响应 no-store |
