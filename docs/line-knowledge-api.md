# 产线知识服务 API

产线以不可变 `line_id` 标识。同名产线不会合并；历史作业不会用场景名或别名自动归线。产线的 `read`、`run`、`manage` 由成员角色决定，HTTP 使用现有会话或 API token。发布、授权和撤回需要人类登录会话及源线 `manage` 权限。

## 管理与共享

| 方法与路径 | 说明 |
|---|---|
| `POST /api/lines` | `{ "name": "一号线" }`；返回新 `line_id`。 |
| `GET /api/lines` | 当前主体有成员权限的产线。 |
| `PATCH /api/lines/:lineId` | 修改展示名，不改身份。 |
| `GET /api/lines/legacy-runs`；`POST /api/lines/:lineId/legacy-runs/:runId/bind`；`GET /api/lines/:lineId/legacy-bindings` | 管理员查看待核对记录；有权管理目标线的人员确认归属并留下审计。不依据别名推断，也不为旧作业补写策略。 |
| `GET /api/lines/:lineId/members`；`PUT/DELETE …/members/:userId` | 列成员、设置角色（例如 `{ "role": "read" }`）、撤权。 |
| `POST /api/lines/:lineId/assets` | 创建私有草稿；经验和记忆使用 `kind`, `title`, `summary`, `content`, `applicability`。dataset 用 `csv`、`fields`、`use_restrictions` 代替经验正文。数据 CSV 必须单独整理，最多 1 MiB。 |
| `POST /api/knowledge/assets/:assetId/versions` | 新建草稿版本，不覆写既有版本。 |
| `POST /api/knowledge/assets/:assetId/versions/:version/publish` | `{ "confirmed": true, "visibility": "catalog", "public_read": false }`。站内目录发现并不等于正文读取或复用。 |
| `PUT/DELETE /api/knowledge/assets/:assetId/versions/:version/grants/:userId` | 经验权限 `read`、`reuse`；数据权限 `read`、`download`、`analyze`。PUT 的 `{ "rights": [...] }` 替换该版本对该用户的权限集合。 |
| `POST /api/knowledge/assets/:assetId/versions/:version/withdraw` | 停止后续访问；已发出的历史内容不可撤回。 |
| `GET /api/knowledge/catalog` | 只返回可发现的已发布版本的安全元数据。 |
| `GET /api/knowledge/assets/:assetId/versions/:version[/download]` | 正文或数据下载各自再查权；不能读取源运行、源文件和私有报告。 |

## 建立作业与按需检索

`POST /api/diagnosis/start` 保留先建作业、再 `/api/diagnosis/execute/:runId` 的契约。`POST /api/external/v1/analyze` 在同一个请求中申请启动。一个带知识策略的请求可以写成：

```json
{
  "harness": "claude",
  "analysisIntent": "deep-diagnosis",
  "dataPath": "my-upload-folder/sample.csv",
  "lineId": "<line_id>",
  "knowledgePolicy": {
    "mode": "on_demand",
    "own_line": true,
    "references": [{ "asset_id": "<asset_id>", "version": 1 }]
  },
  "datasetRefs": []
}
```

- 产线作业的现场输入限定在当前作业所有者的已登记数据目录。分别保存经验版本和数据版本引用。`disabled` 不接入工具；不支持按需记忆的引擎要运行产线作业须显式选择 `disabled`。
- `POST /api/knowledge/runs/:runId/search` 接受 `{ "query": "测温", "signals": ["出口温度"], "limit": 5 }`。只在该作业内的授权来源查找，空结果不扩权；本线私有检索当前限定为同线且同一作业所有者。
- `GET /api/knowledge/runs/:runId/items/:refId` 读取一次搜索中返回的引用；引用绑定当前作业、主体和执行尝试。权限撤回、重跑、失效复核使后续详情请求被拒绝。
- `GET /api/knowledge/runs/:runId/retrievals` 返回有限条目的审计元数据，区分 `preview` 和 `agent`，不返回查询与正文。普通界面查询不能伪装为 Agent 调用。
- Claude 的原生 SDK 适配器向运行中的 Agent 提供只读 `memory_search` / `memory_get`，没有启动历史正文，也不把 API 长效令牌给模型。结果是 L5 历史参考，不是本线观测或执行指令。每次执行尝试最多 20 个查询/详情调用。
- 其余常驻引擎通过同一策略层的临时回环 MCP 适配器获得同样的两个工具：`codex`（app-server `-c mcp_servers.idd_memory=…`，bearer 只进子进程环境变量，argv/日志/错误均脱敏）、`opencode`（每进程 `OPENCODE_CONFIG_CONTENT` 注入 remote MCP，同进程随机 Basic 凭据保护 `/config`）、`omp`（每次尝试独立目录的 `mcp.json`，bearer 经子进程环境变量名解析；启动时校验实际 provider/model 与工具注册，不符即失败）。三种绑定共用同一权限、预算与审计；令牌按次生成、随尝试关闭失效，不出现在提示词或命令行。

## 当前上线范围

| 场景 | 状态 |
|---|---|
| 产线、共享版本、权限、审计、授权预览 | 可由已登录用户在 HTTP/工作台操作。 |
| Claude 本线按需工具 | 仅受信单租户开发环境可显式设置 `IDD_TRUSTED_KNOWLEDGE_RUNTIME=1`；不是生产隔离。 |
| Claude 按需作业恢复历史会话 | 未验证；显式拒绝，不复用可能已有参考正文的会话。 |
| codex / opencode / omp 按需工具 | 已适配并注册（回环 MCP 传输，策略/预算/审计与 Claude 同层）。协议层有真实子进程与真实客户端测试；`codex` 真实 CLI 0.171.0 已验证注册与 Bearer 脱敏，`opencode`+真实 Gemma 已验证按需 tool_use/tool_result 回路；OMP 18.12.2 真实 RPC 注册与启动校验通过。完整作业要求模型端点上下文装得下该 harness 基线（实测：OpenCode ≈62.7k tokens、OMP ≈18.6k tokens，与仓库/提示词无关），8k ctx 端点会 `exceed_context_size_error` 失败。 |
| dsh / hermes / qwen 等其余引擎按需工具 | 未适配；`409 KNOWLEDGE_UNAVAILABLE_ON_HARNESS`，无启动注入回退。 |
| 任意引擎跨线知识或对照数据执行 | 隔离未验收，`409 KNOWLEDGE_ISOLATION_REQUIRED`；可以预览授权经验，不能把它或对照数据交给引擎。 |

`GET /api/external/v1/capabilities` 的 `memory_tools` 表示有适配器，不等于当前实例已允许工具运行；`shared_knowledge_execution: false` 表示不开放跨线执行。系统不自动复制、重新发布或将分享内容计为本线 RSI 观测。
