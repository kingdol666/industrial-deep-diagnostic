# IDD 对外集成 API 完整接口文档（/api/external/v1）

> 版本 v1 · Base URL：`http://<host>:3210/api/external/v1`（下文省写为 `{base}`）
> 通用响应信封：成功 `{"success": true, "data": …}`；失败 `{"success": false, "code": "…", "error": "…"}`
> 本文档逐端点给出**每个字段的类型、必填性、默认值、支持取值**。最后附错误码总表与接入配方。

---

## 1. 认证

所有 `/api/external/v1/*` 端点要求请求头：

```
Authorization: Bearer <token>
```

`<token>` 两种取值：

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

---

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
| `quick-screen` | industrial-sentinel | 哨兵快筛：`alert.json` + `sentinel/watch_report.md` + `quick_screen_report.html`（本体集成后另有 `01_ontology/` 四件套，见 §3.1 ontology 字段） |
| `stability-report` | industrial-line-stability-report | 稳定性评分（0-100/A-D）+ `line_stability_report.html` + `line_stability_report.md`（本体集成后另有 `01_ontology/` 四件套） |
| `doe-analysis` | industrial-doe-analyzer | DOE/工况分析 + 操作窗 `recommendations.json` |
| `experience-mining` | industrial-tuning-memory | 调优动作归因 + 经验条目 |
| `optimizer-campaign` | industrial-optimizer-loop | 布点寻优（只设计不下发参数） |

**harness 支持值（14 个）**：`claude`（推荐，真实 agent）· `omp`（推荐）· `mock`（集成测试，非真实分析）· `codex` · `dsh` · `opencode` · `gemini` · `copilot` · `cursor` · `crush` · `goose` · `hermes` —— 以上需本机已安装对应 CLI；`qwen` · `pi`（未安装，选中返回 409）。

> **专项 intent 的引擎支持面**：specialist intents（非 deep-diagnosis）的 intent 指令由 `buildIntentDirective` 注入，当前覆盖 claude / omp / acp 族（dsh·qwen·hermes）/ one-shot 族（gemini·copilot·cursor·crush·goose·pi）共 12 引擎；`codex` / `opencode` 暂不消费该指令（对 doe-analysis 亦然，补齐在列）。deep-diagnosis 主链路不受影响。

---

## 3. POST /analyze — 发起分析

### 3.1 Request body 字段

| 字段 | 类型 | 必填 | 默认 | 支持值/约束 | 说明 |
|---|---|---|---|---|---|
| folderPath | string | ✓(与 dataPath/dataPaths 三选一) | — | 相对 `data/` 的文件夹名，如 `"bopet_demo"`；文件夹内至少 1 个可解析数据表 | 数据来源 |
| dataPath | string | 三选一 | — | 相对 `data/` 的单文件路径 | 单文件模式 |
| dataPaths | string[] | 三选一 | — | 多个相对文件路径 | 多文件模式 |
| analysisIntent | string | - | `deep-diagnosis` | §2 表中 6 值之一；其他值 → 400 `EXTERNAL_INTENT_UNKNOWN`（响应附 supported） | 分析模式 |
| preprocessingMode | string | - | `single_primary` | `single_primary` / `integrate_merge`；**仅 `stability-report`**（其他 intent 传 → 400 `PREPROCESSING_MODE_UNSUPPORTED_INTENT`）；integrate_merge = 受控时间轴融合（cadence 门 + 列审计） | 文件夹输入预处理策略 |
| harness | string | - | `claude` | §2 表中 14 值之一；未安装 → 409；未知 → 400 `HARNESS_UNKNOWN` | 执行引擎 |
| sceneName | string | - | 文件夹名 | 任意字符串（用于 run 命名与场景识别） | 场景名 |
| question | string | - | "" | 自由文本 | **分析目标**：进入报告 objective 与 agent 指令，越具体越好 |
| reportLanguage | string | - | `zh` | `zh` / `en` | 报告语言 |
| wait | bool | - | `false` | true/false | `true`=阻塞直到完成，响应即最终任务条目 |
| wait_timeout_minutes | number | - | 30 | ≥1 整数 | wait 模式阻塞上限 |
| maxTurns | number | - | 200 | 正整数 | agent 最大轮次 |
| timeoutMinutes | number | - | 引擎默认 | 正整数 | 单次执行超时 |
| ontologyMode | string | - | `auto` | `auto` / `full` / `reuse` / `extend`（`off` 仅 doe + dev override） | 本体策略；**`deep-diagnosis` / `doe-analysis` / `stability-report` / `quick-screen` 支持**（watch 两 intent 的确定性 prepare 阶段消费） |
| ontologyScene | string | - | 从数据推导 | 场景 key | 复用/扩展的本体场景；仅上述四个 intent |
| ontologySource | string | - | store 查找 | 本体资产路径 | 显式复用/扩展来源；仅上述四个 intent |
| ontologyDataStage | string | - | 从响应推导 | `design_only` / `collected` | DOE 本体阶段；仅 `doe-analysis` 消费 |
| ontologyDevOverride | bool | - | `false` | true/false | 仅调试时允许 DOE `mode=off`；仅 `doe-analysis` 消费 |

> 对其余 analysisIntent（`experience-mining` / `optimizer-campaign`）传 ontology 字段会返回 **400 `ONTOLOGY_UNSUPPORTED_INTENT`**（不再静默忽略）。

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

---

## 4. GET /tasks/:taskId — 实时进度轮询

**Request**：路径参数 `taskId`（`POST /analyze` 返回的 `task_id`；传 run_id 也会被自动识别）。

**Response `data` 字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| task_id / run_id | string | 双 ID |
| intent / harness / scene / objective | string\|null | 发起时的参数回显 |
| status | string | 任务生命周期：`accepted → running → completed | failed | stopped | interrupted` |
| created_at / started_at / finished_at | string\|null | ISO 时间戳（finished 仅终态有） |
| progress.events | number | 事件流累计事件数（实时增长 = agent 活跃） |
| progress.tools | number | 其中工具调用类事件数 |
| progress.phase | string | `queued` / `executing` / `awaiting` |
| progress.last_event | string | 最近一条事件类型 |
| links | object | task/result/stream/status 四个地址 |
| result | object\|null | **终态后入库的统一结果**（完成前为 null；结构见 §6） |
| error | string\|null | 失败原因（仅 failed） |

---

## 5. GET /tasks — 任务列表

**Response `data`**：任务条目数组（每项含 task_id/run_id/intent/harness/status/created_at）。
注意：任务注册表在后端内存中，**后端重启后清空**；run 本体不受影响（用 §7 run 视图继续取结果）。

---

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

---

## 7. GET /analyze/:runId — run 维度统一视图（兼容保留）

**Request**：路径参数 `run_id`。**Response `data`**：§6 任务条目的同构视图 + `html_reports`
（相对路径字符串数组）。适合只拿到 run_id 的调用方（如从 `/api/history/runs` 过来的集成）。

---

## 8. GET /analyze/:runId/stream — SSE 流式

**Request**：路径参数 `runId`；`Accept: text/event-stream`。

**事件类型（`event:` 字段全部取值）**：
`status` · `message` · `tool_use` · `tool_result` · `thinking` · `system` · `stats` ·
`log` · `question`（HITL 提问）· `hitl_request` / `hitl_result` · `complete` · `error` ·
`task_progress` · `question_result` · `stream_event` · `unknown` ·
**`result`（收尾事件：统一结果，结构同 §6，之后流关闭）**。

---

## 9. POST /chat — 对话

**Request body**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| run_id | string | ✓ | 目标运行 ID |
| message | string | ✓ | 发送给分析 agent 的消息（中文即可） |

**Response 200**：`{ "success": true, "data": { "run_id": "…", "delivered": true } }`
`delivered=true` 表示消息已投递给该 run 的引擎会话。**不要求 run 仍在运行**：只要引擎保留了可恢复的
`session_id`（mock 恒可；OMP/Claude 在会话仍可恢复时），已完成/失败/停止的 run 也可以继续对话，
agent 的回复经该 run 的 SSE 流返回。
**Response 409**：`EXTERNAL_CHAT_UNAVAILABLE`（run 不存在，或引擎进程已结束且会话不可恢复）。

---

## 10. POST /analyze/:runId/stop — 停止

**Response 200**：`{ "success": true, "data": { "run_id": "…", "status": "stopped" } }`

---

## 11. GET /analyze/:runId — run 维度统一视图（兼容保留）

路径参数为 `run_id`。**Response `data`**：§6 任务条目的同构视图 + `html_reports`
（相对路径字符串数组）。适合只拿到 run_id 的调用方（如从 `/api/history/runs` 过来的集成）。

---

## 12. 数据文件夹要求（folderPath 指向的文件夹里放什么）

`folderPath` 相对于服务器 `data/` 目录（前端 Data 页上传/建的文件夹即在此）。文件夹内：

| 内容 | 必要性 | 说明 |
|---|---|---|
| 数据表 ≥1 份 | ✅ | `data/` 系统支持的格式：CSV（utf-8；line-stability-report 另支持 GBK 回退）、TSV、XLSX/XLS、Parquet、JSON（行对象数组）。首行列名，一行一时刻/记录，含一个时间列 + 数值参数列 |
| `ontology.json` | 可选 | 挂本体后机制校验/语义加权生效（line-stability-report） |
| `report_context.json` | 可选 | line-stability-report 上下文：scenario/objective/group_col/group_filter/inspection_cols/spec_limits/weights |
| 历史段 + 监视窗两段数据 | sentinel 建议 | quick-screen 的 agent 会按哨兵协议自行拆分，或接受单表冷启动 |
| 参考工艺文档 | 可选 | analysis-auto 会作为 L2 证据读取 |

数据量下限：line-report ≥50 行；sentinel watch ≥60 行（建基线 ≥100 稳态行/组）；
analysis-auto 建议 ≥100 行（>10 万行自动抽样）。上传入口：`POST /api/files/upload/...`
（或前端 Data 页拖拽）。

---

## 13. 错误码总表

| HTTP | code | 场景 | 处理 |
|---|---|---|---|
| 401 | AUTH_REQUIRED | 缺/错 token | 重新登录或换 API Token |
| 400 | EXTERNAL_INTENT_UNKNOWN | 未知 analysisIntent | 按 supported 列表修正 |
| 400 | EXTERNAL_DATA_REQUIRED | 未提供数据来源 | 补 folderPath/dataPath |
| 400 | HARNESS_UNKNOWN | 未知 harness | 按 capabilities 修正 |
| 400 | ONTOLOGY_UNSUPPORTED_INTENT | 对不支持的 intent 传了 ontology 字段 | 只用 deep-diagnosis / doe-analysis / stability-report / quick-screen，或去掉字段 |
| 400 | PREPROCESSING_MODE_UNKNOWN / PREPROCESSING_MODE_UNSUPPORTED_INTENT | preprocessingMode 值非法 / 用于非 stability-report intent | 修正值或去掉字段（仅 stability-report 支持） |
| 400 | VALIDATION_ERROR | token 参数不合法 | 见 error 信息 |
| 404 | — | run/task 不存在 | 检查 ID |
| 409 | HARNESS_UNAVAILABLE | 引擎未安装 | 换已安装引擎 |
| 409 | EXTERNAL_TASK_RUNNING | 结果未就绪 | 继续轮询 |
| 409 | EXTERNAL_CHAT_UNAVAILABLE | run 不存在或会话不可恢复 | 重新发起分析 |
| 409 | RUN_TERMINAL | stop 一个已终态 run | 读取当前状态，不要重复 stop |
| 202 | — | wait 超时仍运行 | 继续 GET /tasks/:taskId |

---

## 14. 接入配方

### 14.1 异步 + 轮询（推荐，适配真实引擎）

```python
import requests, time

BASE = "http://localhost:3210/api/external/v1"
HDR = {"Authorization": "Bearer <idd_xxxx API Token>"}

# 1) 发起（非 wait → 拿 task_id）
r = requests.post(f"{BASE}/analyze", headers=HDR, json={
    "folderPath": "bopet_demo", "analysisIntent": "stability-report",
    "harness": "claude", "sceneName": "my-analysis",
    "question": "重点关注熔体压力与薄膜厚度"}).json()
task_id = r["data"]["task_id"]

# 2) 轮询进度
while True:
    t = requests.get(f"{BASE}/tasks/{task_id}", headers=HDR).json()["data"]
    print(t["status"], t["progress"])
    if t["status"] in ("completed", "failed", "stopped"):
        break
    time.sleep(15)

# 3) 取入库结果（含 md 全文与文件路径）
res = requests.get(f"{BASE}/tasks/{task_id}/result", headers=HDR).json()["data"]
print(res["result"]["summary"], res["result"]["files"]["report_md_path"])
for h in res["result"]["files"]["html"]:
    print("HTML:", h["abs_path"])
```

### 14.2 SSE 流式

```python
import requests, json
with requests.get(f"{BASE}/analyze/<run_id>/stream",
                  headers=HDR, stream=True, timeout=1800) as resp:
    event, data = None, None
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("event:"): event = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:])
            if event == "result":           # 统一结果收尾
                print(data["result"]["report_md"][:500]); break
```

---

## 15. 行为与状态说明

- 任务状态机：`accepted → running → completed | failed | stopped | interrupted`；
  `running` 期间 `progress.events` 持续增长（claude 引擎为流式分片计数，数值偏大属正常）。
- 任务注册表在后端**内存**中：后端重启后 `GET /tasks` 清空，但 run 永久保存在
  `data/diagnostic.db`，用 `GET /analyze/:runId`（run 视图）仍可取全部结果。
- specialist 模式（quick-screen/stability-report 等）不走 9 阶段 judge 门，因此
  `result.score/verdict` 为 null——质量结论在报告与 HTML 内（稳定性报告自带 81 分制评分）。
- 纯分析边界：所有模式只产报告与告警，绝不向产线下发参数。
