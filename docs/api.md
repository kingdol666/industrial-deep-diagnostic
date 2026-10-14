# IDD API 接口文档

> 本文档覆盖两组 API：
> **A. 对外集成 API `/api/external/v1`** —— 外部应用的推荐接入面（任务托管 + 流式 + 统一结果）；
> **B. 诊断任务 API `/api/diagnosis`** —— 诊断执行的全端点细粒度面（含 AgentWorkShop 桥接沿用的 `/tasks`）。
>
> Base URL：`http://<host>:3210/api`（下文省写为 `{base}`）
> 通用响应信封：成功 `{"success": true, "data": …}`；失败 `{"success": false, "code": "…", "error": "…"}`
> 鉴权：除 `POST /api/auth/register`、`POST /api/auth/login`、`GET /api/health` 外全部要求
> `Authorization: Bearer <token>`（登录 JWT 或 `idd_` API Token；`AUTH_ENABLED=0` 可临时关闭）。

---

# A. 对外集成 API `/api/external/v1`（外部应用推荐接入面）

## 0. 生命周期总览（非 wait 模式 = 任务管理对象托管）

```
POST /analyze ──返回──▶ task_id（+run_id）
                          │
                          ▼
        GET /tasks/:taskId          ← 实时轮询进度（status/progress）
                          │ 运行完成
                          ▼
        任务管理对象把统一结果入库（summary/score/verdict/report.md/文件路径）
                          │
                          ▼
        GET /tasks/:taskId/result   ← 专属结果 API（稳定读取入库结果）
```

- `POST /analyze` 支持 `wait:true` 阻塞模式：请求挂起直到完成，响应体即最终任务条目
  （与 `/tasks/:taskId/result` 同构），超时上限 `wait_timeout_minutes`（默认 30）。
- 任务条目由后端**任务管理对象**（内存注册表）持有；后端重启后任务清空，
  但 run 本体仍在（用 `GET /analyze/:runId`（run 视图）继续取结果）。

## 1. 认证

| token 类型 | 获取方式 | 有效期 | 适用 |
|---|---|---|---|
| 会话 JWT | `POST /api/auth/login` → `data.session_token` | 24 小时（env `AUTH_SESSION_TTL_HOURS` 可调） | 交互调试 |
| **API Token**（推荐） | `POST /api/auth/tokens` → `data.token` | 默认 30 天；可传 `expires_in_days`（1–365 整数）或 `null`（永久） | 外部系统长期接入 |

**签发 API Token**：

```
POST /api/auth/tokens        （需要 Bearer 会话 JWT）
 body: { "name": "my-integration",        // 必填，≤64 字符
         "expires_in_days": 90 }          // 可选：1-365 整数；null=永不过期；缺省=30
 response.data: { "id", "token": "idd_xxxx…",   // 明文仅此一次，请保存
                  "token_prefix": "idd_xxxx", "expires_at": "…" }
```

管理：`GET /api/auth/tokens`（列表，脱敏）、`DELETE /api/auth/tokens/:id`（吊销）、
`GET /api/auth/me`（验证当前 token，返回 `auth_type: "api_token"`）。
登录失败/无 token → **401 `AUTH_REQUIRED`**。

## 2. GET /capabilities — 能力发现

**Request**：无参数。

**Response `data` 字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| intents[].intent | string | 分析模式名，可直接填入 `/analyze` 的 `analysisIntent` |
| intents[].skill | string | 该模式内部执行的 skill |
| intents[].default | bool | 是否默认模式（deep-diagnosis） |
| harnesses[].id | string | 引擎名，可直接填入 `/analyze` 的 `harness` |
| harnesses[].label / runs_capable | string/bool | 展示名 / 是否支持 run 执行 |

**analysisIntent 支持值（6 个）**：

| 值 | 执行 skill | 产出 |
|---|---|---|
| `deep-diagnosis`（默认） | industrial-analysis-auto | 9 阶段根因诊断：竞争假设+证据链+`diagnostic-report.html` |
| `quick-screen` | industrial-sentinel | 哨兵快筛：`alert.json` + 巡检 md + `quick_screen_report.html` |
| `stability-report` | industrial-line-stability-report | 稳定性评分（0-100/A-D）+ `line_stability_report.html` |
| `doe-analysis` | industrial-doe-analyzer | DOE/工况分析 + 操作窗 `recommendations.json` |
| `experience-mining` | industrial-tuning-memory | 调优动作归因 + 经验条目 |
| `optimizer-campaign` | industrial-optimizer-loop | 布点寻优（只设计不下发参数） |

**harness 支持值（14 个）**：`claude`（推荐，真实 agent）· `omp`（推荐）· `mock`（集成测试，非真实分析）· `codex` · `dsh` · `opencode` · `gemini` · `copilot` · `cursor` · `crush` · `goose` · `hermes` —— 以上需本机已安装对应 CLI；`qwen` · `pi`（未安装，选中返回 409）。

## 3. POST /analyze — 发起分析

### 3.1 Request body 字段

| 字段 | 类型 | 必填 | 默认 | 支持值/约束 | 说明 |
|---|---|---|---|---|---|
| folderPath | string | ✓(与 dataPath/dataPaths 三选一) | — | 相对 `data/` 的文件夹名，如 `"bopet_demo"`；文件夹内至少 1 个可解析数据表 | 数据来源 |
| dataPath | string | 三选一 | — | 相对 `data/` 的单文件路径 | 单文件模式 |
| dataPaths | string[] | 三选一 | — | 多个相对文件路径 | 多文件模式 |
| analysisIntent | string | - | `deep-diagnosis` | §2 表中 6 值之一；其他值 → 400 `EXTERNAL_INTENT_UNKNOWN`（响应附 supported） | 分析模式 |
| harness | string | - | `claude` | §2 表中 14 值之一；未安装 → 409；未知 → 400 `HARNESS_UNKNOWN` | 执行引擎 |
| sceneName | string | - | 文件夹名 | 任意字符串（用于 run 命名与场景识别） | 场景名 |
| question | string | - | "" | 自由文本 | **分析目标**：进入报告 objective 与 agent 指令，越具体越好 |
| reportLanguage | string | - | `zh` | `zh` / `en` | 报告语言 |
| wait | bool | - | `false` | true/false | `true`=阻塞直到完成，响应即最终任务条目 |
| wait_timeout_minutes | number | - | 30 | ≥1 整数 | wait 模式阻塞上限 |
| maxTurns | number | - | 200 | 正整数 | agent 最大轮次 |
| timeoutMinutes | number | - | 引擎默认 | 正整数 | 单次执行超时 |

### 3.2 Response

**默认（wait=false）→ 202**：

| 字段 | 类型 | 说明 |
|---|---|---|
| data.task_id | string | **任务 ID（`TASK-XXXX…`），非 wait 模式的跟踪凭据** |
| data.run_id | string | 内部运行 ID（stream/stop/chat 用） |
| data.status | string | 初始 `accepted` |
| data.links.task | string | 进度轮询地址（§5） |
| data.links.result | string | 结果读取地址（§6） |
| data.links.stream | string | SSE 流地址（§8） |
| data.links.status | string | run 视图地址（§7） |

**wait=true → 200**（完成时）：响应体 = `GET /tasks/:taskId` 的任务条目（含已入库 `result`，见 §6）。
**wait=true → 202**（超时仍运行）：同上条目 + `"wait": "timeout_still_running"`，继续轮询即可。

错误：400 `EXTERNAL_DATA_REQUIRED` / `EXTERNAL_INTENT_UNKNOWN` / `HARNESS_UNKNOWN`；409 `HARNESS_UNAVAILABLE`；401 `AUTH_REQUIRED`。

## 4. GET /tasks/:taskId — 实时进度轮询

**Request**：路径参数 `taskId`（`POST /analyze` 返回的 `task_id`；传 run_id 也会被自动识别）。

**Response `data` 字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| task_id / run_id | string | 双 ID |
| intent / harness / scene / objective | string\|null | 发起时的参数回显 |
| status | string | 任务生命周期：`accepted → running → completed | failed | stopped | interrupted` |
| created_at / started_at / finished_at | string\|null | ISO 时间戳（finished 仅终态有） |
| progress.events | number | 事件流累计事件数（实时增长 = agent 活跃；claude 为流式分片计数，数值偏大属正常） |
| progress.tools | number | 其中工具调用类事件数 |
| progress.phase | string | `queued` / `executing` / `awaiting` |
| progress.last_event | string | 最近一条事件类型 |
| links | object | task/result/stream/status 四个地址 |
| result | object\|null | **终态后入库的统一结果**（完成前为 null；结构见 §6） |
| error | string\|null | 失败原因（仅 failed） |

## 5. GET /tasks — 任务列表

**Response `data`**：任务条目数组（每项含 task_id/run_id/intent/harness/status/created_at）。
任务注册表在后端内存中，后端重启后清空；run 本体不受影响（§7）。

## 6. GET /tasks/:taskId/result — 专属结果 API（终态后稳定可读）

**Request**：路径参数 `taskId`。

**Response 409**（未完成）：`code: "EXTERNAL_TASK_RUNNING"`，`data` 携带当前 status/progress——继续轮询即可。

**Response 200**（终态；**内容为任务管理对象入库副本，重复读取稳定不变**）：

| 字段路径 | 类型 | 说明 |
|---|---|---|
| data.task_id / run_id | string | 双 ID |
| data.status | string | 终态（completed/failed/stopped/interrupted） |
| data.finished_at | string | 完成时间 |
| data.error | string\|null | 失败原因（仅 failed） |
| data.result.summary | string | 结论摘要（≤1500 字符，取自报告结论节） |
| data.result.verdict | string\|null | 审计判定（`ENDORSED` 等；specialist 模式无 judge 时为 null） |
| data.result.score | number\|null | 质量门分数（specialist 模式为 null，评分在报告/html 内） |
| data.result.report_md | string | **完整分析报告 Markdown 全文** |
| data.result.report_md_url | string | md 的 API 读取地址 |
| data.result.files.workspace_path | string\|null | run 工作区路径 |
| data.result.files.report_md_path | string | report.md 的**磁盘绝对路径**（可直接读取） |
| data.result.files.html[].path | string | HTML 报告相对 run 目录的路径 |
| data.result.files.html[].abs_path | string | HTML 报告的**磁盘绝对路径** |
| data.result.files.html[].url | string | 带 token 即可在浏览器打开的 API 地址 |

**各 skill 的 HTML 产物约定**（出现在 `files.html` 里）：

| intent | HTML 产物（run 相对路径） |
|---|---|
| quick-screen | `sentinel/quick_screen_report.html` |
| stability-report | `line_report/line_stability_report.html`（含 `--doe-auto` 时另有 `line_report/doe_auto_run/report.html`） |
| deep-diagnosis | `diagnostic-report.html` |
| doe-analysis | `report.html` |
| experience-mining / optimizer-campaign | 暂无 HTML（`html: []`；md 报告正常返回） |

`report_md_path` / `abs_path` 直接指向磁盘真实文件（已验收存在）；`url` 需带
`?token=<API Token>` 在浏览器打开（HTML 内图片已自动注入 token）。

## 7. GET /analyze/:runId — run 维度统一视图（兼容保留）

路径参数 `run_id`。Response `data`：§6 任务条目的同构视图 + `html_reports`（相对路径字符串数组）。

## 8. GET /analyze/:runId/stream — SSE 流式

事件类型（`event:` 全部取值）：`status` · `message` · `tool_use` · `tool_result` · `thinking` ·
`system` · `stats` · `log` · `question` · `hitl_request` / `hitl_result` · `complete` · `error` ·
`task_progress` · `question_result` · `stream_event` · `unknown` ·
**`result`（收尾：统一结果，之后流关闭）**。连接时已终态则立即推 `result`。

## 9. POST /chat — 对话

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| run_id | string | ✓ | 目标运行 ID |
| message | string | ✓ | 发送给分析 agent 的消息 |

200：`{run_id, delivered: true}`；409 `EXTERNAL_CHAT_UNAVAILABLE`（要求分析运行中；回复经该 run 的 SSE 流返回）。

## 10. POST /analyze/:runId/stop — 停止

200：`{ "run_id": "…", "status": "stopped" }`。

## 11. 数据文件夹要求（folderPath 指向的文件夹里放什么）

| 内容 | 必要性 | 说明 |
|---|---|---|
| 数据表 ≥1 份 | ✅ | CSV（utf-8；line-stability-report 另支持 GBK 回退）、TSV、XLSX/XLS、Parquet、JSON（行对象数组）。首行列名，一行一时刻/记录，含时间列 + 数值参数列 |
| `ontology.json` | 可选 | 挂本体后机制校验/语义加权生效（line-stability-report） |
| `report_context.json` | 可选 | line-stability-report 上下文：scenario/objective/group_col/group_filter/inspection_cols/spec_limits/weights |
| 历史段 + 监视窗两段数据 | sentinel 建议 | quick-screen 的 agent 会按哨兵协议自行拆分 |
| 参考工艺文档 | 可选 | analysis-auto 作为 L2 证据读取 |

数据量下限：line-report ≥50 行；sentinel watch ≥60 行（建基线 ≥100 稳态行/组）；
analysis-auto 建议 ≥100 行（>10 万行自动抽样，上传上限 500MB/50 文件）。

---

# B. 诊断任务 API `/api/diagnosis`（细粒度执行面）

> 与 A 的关系：**同一执行内核的细粒度面**——`/tasks` 即 A 组 `/analyze` 异步模式的
> 桥接版（AgentWorkShop 沿用），其余端点暴露启动/执行/流/停止/续跑/HITL/增强等
> 全部内部控制点。新集成建议优先 A；需要细粒度控制时用本组。

## B1. POST /start — 创建诊断 run（不自动执行）

**Request body**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| folderPath / dataPath / dataPaths | string/array | 三选一 | 数据来源（同 A§3） |
| harness | string | - | 引擎（未知 400 `HARNESS_UNKNOWN`，未安装 409） |
| analysisIntent | string | - | 同 A§2 六值，默认 deep-diagnosis |
| sceneName / userQuestion / reportLanguage | string | - | 场景 / 分析目标 / 报告语言(zh/en) |
| maxTurns / timeoutMinutes | number | - | 轮次与超时 |
| model / permissionMode | string | - | 引擎侧模型与权限模式（按引擎目录校验，不支持→400） |

**Response 200 `data`**：`{ "runId": "9a327e66", "name": "<scene>_<runId>", "status": "pending", "mode": "folder", "harness": "claude", "analysisIntent": "quick-screen", "ontologyHit": 0, "enhancementPolicy": "off", "enhancementIntent": false }`

之后调 `POST /execute/:runId` 启动执行（或直接 `GET /stream/:runId`，会自动触发 pending 的 run）。

## B2. POST /execute/:runId — 启动执行

**Response 200 `data`**：`{ "runId", "status": "running" }`。错误：404 不存在 / 400 非 pending / 409 已在执行。

## B3. GET /stream/:runId — SSE 实时事件流

事件类型同 A§8（`status/message/tool_use/tool_result/thinking/system/stats/log/question/hitl_*/complete/error/task_progress/stream_event/stream_end`）。连接时若 run 为 pending 会**自动触发执行**；已终态则立即 `complete` 事件后关闭。

## B4. GET /status/:runId — 运行状态（DB 行）

**Response `data`**：`{ "id", "run_id", "name", "scene_name", "data_path", "data_folder", "user_question", "status", "session_id", "workspace_path", "report_path", "score", "judge_verdict", "error_message", "model", "max_turns", "created_at", "updated_at", "completed_at", "report_language", "harness", "ontology_hit", "enhancement_policy", "enhancement_triggered", "analysis_intent", "engineStatus", "liveStatus" }`

## B5. GET /snapshot/:runId — 实时快照

**Response `data`**：`{ "run"(DB 行), "events"(事件数组), "liveStatus", "hasActiveEngineRun", "currentQuestion"(HITL 提问或 null) }` —— 进度类集成的推荐数据源。

## B6. GET /list — 引擎侧运行清单（内存视图，非历史）

## B7. GET /session/:runId — 会话内容（harness 会话消息数组；omp 会话走 omp 分支）

## B8. POST /chat/:runId — 向**运行中**的引擎进程投递消息

body `{ "message": "…" }` → 200 `{ "runId", "resumed": true }`；404 无活跃进程。

## B9. POST /continue/:runId — 续跑失败/停止的 run

body `{ "followUpMessage": "可选补充说明" }` → 200 `{ "runId", "status": "running", "continued": true }`；
404 不存在 / 400 pending 状态不可续跑。

## B10. POST /hitl/:hitlId + GET /hitl/:runId — HITL 审批

POST body `{ "approved": true|false }` → 200 `{ "hitlId", "approved" }`；GET 返回 `{ "pending": [...] }`。

## B11. POST /answer/:runId — 回答 AskUserQuestion

body `{ "questionId", "toolUseId", "answers": {...} }` → 200 `{ "runId", "questionId", "answered": true }`。

## B12. POST /enhance/:runId — 一键 E0-E8 深度增强

仅 `completed` 且已有 `report.md` 的 run 可触发（E0 门禁校验基线完整；重复触发 409）。
响应为触发结果；增强过程事件写入该 run 的事件流。

## B13. POST /tasks — 异步任务（AgentWorkShop 桥接，兼容保留）

**Request body**：同 B1（含 `analysisIntent` 六模式与 `harness`）。
**Response 200 `data`**：`{ "task_id": "<runId>", "status": "running", "poll": "GET /api/diagnosis/tasks/<runId>" }`
—— **接收即返**，诊断在引擎子进程后台执行；拉起失败也会如实呈现在查询里。

## B14. GET /tasks/:taskId — 任务视图（taskId = runId）

**Response `data`**：

| 字段 | 说明 |
|---|---|
| task_id / status | `running` / `completed` / `failed` / `stopped` |
| run_status | 引擎侧原始状态 |
| name / scene / harness / created_at / finished_at | 元信息 |
| result | completed 时：`{ "summary"(报告结论节 ≤1500 字符), "verdict", "score", "report_md_path"(绝对路径) }`；failed 时：`{ "error" }`；其余为 null |

深度诊断（deep-diagnosis）为多子代理串行执行，**墙钟可达 1.5-2 小时**——本端点专为
此类长任务设计（外部轮询即可，无需保持连接）。

## B15. 其他

- `POST /stop/:runId` — 停止（200 stopped / 404 无活跃进程）。
- 错误码：401 `AUTH_REQUIRED` / 400 `HARNESS_UNKNOWN`·`VALIDATION_ERROR` / 409 `HARNESS_UNAVAILABLE` / 404。

---

# C. 其他路由组索引

| 组 | 前缀 | 说明 |
|---|---|---|
| auth | `/api/auth` | 注册/登录/我/token 管理（见 A§1） |
| files | `/api/files` | 数据浏览/上传/文件夹、run 产物（report/optimizer/files/**html 清单**/asset 资产服务） |
| history | `/api/history` | `GET /runs`（DB 历史，含 score/verdict）、`GET|DELETE /runs/:runId` |
| analysis | `/api/analysis` | `GET /chart-data/:runDirName`（9 阶段管线图表数据） |
| harness | `/api/harness` | 14 引擎清单/健康/runs/产物/HTML |
| ontology | `/api/ontology` | 本体资产库管理（版本/复用/推荐） |
| chat / omp | `/api/chat` `/api/omp` | 会话工作台 / OMP 原生运行浏览 |

# D. 选型指引

- **外部系统接入（推荐）**：A 组 `/api/external/v1`——task_id 托管、进度计数、统一结果封装（含 md 全文与 html 文件路径）、SSE 收尾 result 事件。
- **需要细粒度控制**（续跑/HITL 应答/增强/会话内容）：B 组 `/api/diagnosis`。
- **AgentWorkShop 桥接存量**：`B13/B14`（`/api/diagnosis/tasks`）保持兼容，不必迁移。
- 深度诊断（deep-diagnosis）真实耗时 1.5-2 小时（多子代理串行），务必使用异步任务 +
  轮询/SSE 模式，不要用阻塞 HTTP。
