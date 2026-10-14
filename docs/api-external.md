# IDD 对外集成 API 接口文档（/api/external/v1）

> 版本：v1 · Base URL：`http://<host>:3210/api/external/v1`
> 鉴权：除本文件特别标注外，所有端点要求 `Authorization: Bearer <token>`。
> token 两种：登录会话 JWT、或 `POST /api/auth/tokens` 签发的 **API Token**（`idd_` 前缀，
> 30 天有效，明文仅返回一次，服务端只存 SHA-256）——外部系统推荐使用 API Token。

---

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
  但 run 本体仍在（可用 `GET /analyze/:runId`（run 视图）继续取结果）。

---

## 1. GET /capabilities — 能力发现

**Request**：无参数。

**Response 200**：
```json
{
  "success": true,
  "data": {
    "intents": [
      { "intent": "deep-diagnosis",   "skill": "industrial-analysis-auto", "default": true },
      { "intent": "stability-report", "skill": "industrial-line-stability-report" },
      { "intent": "quick-screen",     "skill": "industrial-sentinel" },
      { "intent": "doe-analysis",     "skill": "industrial-doe-analyzer" },
      { "intent": "experience-mining","skill": "industrial-tuning-memory" },
      { "intent": "optimizer-campaign","skill": "industrial-optimizer-loop" }
    ],
    "harnesses": [ { "id": "claude", "label": "Claude Code", "runs_capable": true },
                   { "id": "omp", "label": "OMP Engine", "runs_capable": true },
                   { "id": "mock", "label": "Mock Engine", "runs_capable": true } ]
  }
}
```
错误：401 `AUTH_REQUIRED`（无/错 token）。

---

## 2. POST /analyze — 发起分析（选模式 + 选引擎 + 数据文件夹）

**Request body**（`Content-Type: application/json`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| folderPath | string | ✓(三选一) | 数据文件夹（相对 `data/`，如 `"bopet_demo"`）；或 dataPath/dataPaths |
| analysisIntent | string | - | 分析模式，默认 `deep-diagnosis`；未知值 → 400 `EXTERNAL_INTENT_UNKNOWN` |
| harness | string | - | 执行引擎，默认 `claude`；未安装 → 409 `HARNESS_UNAVAILABLE` |
| sceneName | string | - | 场景名（默认取文件夹名） |
| question | string | - | 分析目标/关注点（进入报告 objective 与 agent 指令） |
| reportLanguage | string | - | 默认 `zh` |
| wait | bool | - | `true`=阻塞到完成（见下）；默认 `false` |
| wait_timeout_minutes | number | - | wait 模式上限，默认 30 |
| maxTurns | number | - | agent 最大轮次 |

**Response 202**（非 wait，默认）：
```json
{
  "success": true,
  "data": {
    "task_id": "TASK-MV84YFPI-SO4N",
    "run_id": "1479fe6d",
    "status": "accepted",
    "links": {
      "task":   "/api/external/v1/tasks/TASK-MV84YFPI-SO4N",
      "result": "/api/external/v1/tasks/TASK-MV84YFPI-SO4N/result",
      "stream": "/api/external/v1/analyze/1479fe6d/stream",
      "status": "/api/external/v1/analyze/1479fe6d"
    }
  }
}
```

**Response 200**（`wait:true` 且在超时内完成）= `GET /tasks/:taskId` 的任务条目
（含已入库的 `result`，结构见 §4）。**202 + `wait:"timeout_still_running"`** = 超时仍在跑，
改用任务轮询继续等待。

错误：400 `EXTERNAL_DATA_REQUIRED` / `EXTERNAL_INTENT_UNKNOWN`；409 `HARNESS_UNAVAILABLE`；401。

---

## 3. GET /tasks/:taskId — 实时进度轮询

**Request**：路径参数 `taskId`。

**Response 200**：
```json
{
  "success": true,
  "data": {
    "task_id": "TASK-MV84YFPI-SO4N",
    "run_id": "1479fe6d",
    "intent": "quick-screen",
    "harness": "claude",
    "scene": "mgmt-eval-sentinel",
    "objective": "重点关注熔体压力与薄膜厚度通道",
    "status": "running",                    // accepted→running→completed|failed|stopped
    "created_at": "2026-10-14T13:20:00.000Z",
    "started_at": "2026-10-14T13:20:01.000Z",
    "finished_at": null,
    "progress": {
      "events": 12,                         // 事件流累计事件数（实时）
      "tools": 5,                           // 其中工具调用事件数
      "phase": "executing",                 // queued | executing | awaiting
      "last_event": "tool_result"
    },
    "links": { "task": "…", "result": "…", "stream": "…", "status": "…" },
    "result": null                          // 终态前为 null；完成后入库（见 §4）
  }
}
```
错误：404 `Task not found`（未知 taskId；传 run_id 也会被自动识别转发）。

---

## 4. GET /tasks/:taskId/result — 专属结果 API（终态后稳定可读）

**Request**：路径参数 `taskId`。

**Response 200**（终态；结果为**任务管理对象入库副本**，重复读取稳定）：
```json
{
  "success": true,
  "data": {
    "task_id": "TASK-…",
    "run_id": "1479fe6d",
    "status": "completed",
    "finished_at": "2026-10-14T13:31:00.000Z",
    "error": null,
    "result": {
      "summary": "结论摘要（≤1500 字符）",
      "verdict": "ENDORSED",
      "score": 96,
      "report_md": "# 完整分析报告 Markdown 全文…",
      "files": {
        "workspace_path": "workspace\\diagnostic-runs\\<ts>_<scene>",
        "report_md_path": "D:\\…\\workspace\\diagnostic-runs\\<ts>_<scene>\\report.md",
        "report_md_url":  "/api/files/workspace/report/<ts>_<scene>",
        "html": [
          { "path":    "sentinel/quick_screen_report.html",
            "abs_path":"D:\\…\\workspace\\diagnostic-runs\\<ts>_<scene>\\sentinel\\quick_screen_report.html",
            "url":    "/api/files/workspace/asset/<ts>_<scene>/sentinel/quick_screen_report.html" },
          { "path":    "line_report/line_stability_report.html", "abs_path": "…", "url": "…" }
        ]
      }
    }
  }
}
```

**Response 409**（未完成）：
```json
{ "success": false, "code": "EXTERNAL_TASK_RUNNING",
  "error": "task is running — result is available after completion",
  "data": { "task_id": "…", "status": "running", "progress": {…} } }
```

**文件路径说明**（`result.files`）：
- `report_md_path`：报告 Markdown 的**磁盘绝对路径**（可直接读取）；
- `html[].abs_path`：每个 HTML 可视化报告的磁盘绝对路径；
- `html[].path / url`：run 相对路径与带 token 的 API 打开地址；
- 各 skill 的 HTML 产物约定：sentinel → `sentinel/quick_screen_report.html`、
  line-stability-report → `line_report/line_stability_report.html`、
  analysis-auto → `diagnostic-report.html`。mock 引擎不产 HTML（`html: []` 属正常）。

---

## 5. GET /analyze/:runId — run 维度统一视图（兼容保留）

路径参数为 `run_id`。Response：同 §4 任务条目视图 + `html_reports`（相对路径数组）+
`result.report_md`；另含 `links`。适合只拿到 run_id 的调用方。

---

## 6. GET /analyze/:runId/stream — SSE 流式（对话回复也经此返回）

**Request**：路径参数 `runId`；`Accept: text/event-stream`。

**事件序列**：
```
event: assistant|tool_result|…     （引擎实时事件，多条）
…
event: result
data: {"run_id":"…","status":"completed","result":{…同 §4…},"html_reports":[…]}
```
流以 `result` 事件收尾后关闭；若连接时已终态，立即推送 `result` 并关闭。

---

## 7. POST /chat — 对话（投递到运行中的分析）

**Request body**：`{ "run_id": "…", "message": "请优先关注熔体压力通道" }`
（两字段必填；message 为字符串）。

**Response 200**：`{ "success": true, "data": { "run_id": "…", "delivered": true } }`
**Response 409**：`EXTERNAL_CHAT_UNAVAILABLE`（run 不存在或无存活引擎进程——对话要求分析正在运行；
回复内容经该 run 的 SSE 流返回）。

---

## 8. POST /analyze/:runId/stop — 停止

**Response 200**：`{ "success": true, "data": { "run_id": "…", "status": "stopped" } }`

---

## 9. GET /tasks — 列出本后端实例跟踪的全部任务

**Response 200**：`{ "success": true, "data": [ { "task_id","run_id","intent","harness","status","created_at" }, … ] }`

---

## 10. 错误码汇总

| HTTP | code | 场景 |
|---|---|---|
| 401 | AUTH_REQUIRED | 缺/错 token |
| 400 | EXTERNAL_INTENT_UNKNOWN | 未知分析模式（响应附 supported） |
| 400 | EXTERNAL_DATA_REQUIRED | 未提供数据文件夹/文件 |
| 400 | HARNESS_UNKNOWN | 未知引擎 |
| 409 | HARNESS_UNAVAILABLE | 引擎未安装 |
| 409 | EXTERNAL_TASK_RUNNING | 结果未就绪（result 专属端点） |
| 409 | EXTERNAL_CHAT_UNAVAILABLE | 无存活引擎进程（chat） |
| 404 | — | run/task 不存在 |
