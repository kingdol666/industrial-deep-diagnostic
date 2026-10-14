# IDD 对外集成 API（/api/external/v1）

> 面向外部应用的稳定集成面：选择分析模式 → 选择执行引擎（harness）→ 发起分析 →
> 流式返回（SSE）或阻塞等待 → 统一结果（score/verdict/report.md/html 清单一次拿全）。
> 鉴权继承全局 authGuard：`Authorization: Bearer <登录JWT 或 idd_ API Token>`。

Base URL：`http://<host>:3210/api/external/v1`

## 端点总览

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/capabilities` | 发现：支持的分析模式（intents）+ 可用引擎（harnesses） |
| POST | `/analyze` | 发起分析（默认异步 202 立返；`wait:true` 阻塞到完成返回统一结果） |
| GET | `/analyze/:runId` | 统一状态/结果视图（终态含 score/verdict/summary/report_md/html 清单） |
| GET | `/analyze/:runId/stream` | SSE 实时事件流，结束时推 `event: result`（统一结果）后关闭 |
| POST | `/chat` | 向**运行中**的分析投递对话消息 `{run_id, message}` |
| POST | `/analyze/:runId/stop` | 停止运行中的分析 |

## 分析模式（analysisIntent）

| intent | 执行 skill |
|---|---|
| `deep-diagnosis`（默认） | industrial-analysis-auto（9 阶段根因诊断） |
| `quick-screen` | industrial-sentinel（哨兵快筛 + HTML 快筛报告） |
| `stability-report` | industrial-line-stability-report（稳定性评分 + HTML 报告） |
| `doe-analysis` | industrial-doe-analyzer |
| `experience-mining` | industrial-tuning-memory |
| `optimizer-campaign` | industrial-optimizer-loop |

harness：`claude`（默认）/ `omp` / `mock`（集成测试用）/ `codex` / `dsh` / `opencode` / `gemini` / `copilot` / `cursor` / `crush` / `goose` / `hermes`（`qwen`/`pi` 未安装）——以 `GET /capabilities` 实时返回为准。

## 快速开始（curl）

```bash
BASE=http://localhost:3210/api

# 1) 登录换取会话 token（外部系统推荐直接用 API Token，见第 3 步）
JWT=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"you","password":"***"}' | jq -r .data.session_token)

# 2) 签发长期 API Token（明文仅此一次，服务端只存哈希）
API_TOKEN=$(curl -s -X POST $BASE/auth/tokens -H "Authorization: Bearer $JWT" \
  -H 'Content-Type: application/json' -d '{"name":"my-integration"}' | jq -r .data.token)

# 3) 发起分析：quick-screen 模式 × claude 引擎（异步）
curl -s -X POST $BASE/external/v1/analyze -H "Authorization: Bearer $API_TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "folderPath": "bopet_demo",
    "analysisIntent": "quick-screen",
    "harness": "claude",
    "sceneName": "my-analysis",
    "question": "重点关注熔体压力与厚度通道"
  }'
# → {"success":true,"data":{"run_id":"9a327e66","status":"running","links":{...}}}

# 3b) 或者阻塞等待统一结果（mock 引擎秒级；claude 建议异步+轮询/SSE）
curl -s -X POST $BASE/external/v1/analyze -H "Authorization: Bearer $API_TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "folderPath": "bopet_demo", "analysisIntent": "stability-report",
    "harness": "claude", "wait": true, "wait_timeout_minutes": 30
  }'
# → data.status="completed" 时 data.result 携带 summary/score/verdict/report_md

# 4) 订阅 SSE 流（事件流结束前最后一条为 event: result —— 统一结果）
curl -N "$BASE/external/v1/analyze/<run_id>/stream" -H "Authorization: Bearer $API_TOKEN"

# 5) 轮询统一结果
curl -s "$BASE/external/v1/analyze/<run_id>" -H "Authorization: Bearer $API_TOKEN"

# 6) 向运行中的分析投递对话消息
curl -s -X POST $BASE/external/v1/chat -H "Authorization: Bearer $API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"run_id":"<run_id>","message":"请优先关注熔体压力通道的告警"}'

# 7) 停止
curl -s -X POST $BASE/external/v1/analyze/<run_id>/stop -H "Authorization: Bearer $API_TOKEN"
```

## 统一结果结构（GET /analyze/:runId 或 SSE result 事件）

```json
{
  "run_id": "9a327e66",
  "status": "completed",            // running | completed | failed | stopped | interrupted
  "harness": "claude",
  "intent": "quick-screen",
  "objective": "重点关注熔体压力与厚度通道",
  "workspace": "workspace/diagnostic-runs/<ts>_<scene>",
  "links": { "status": "...", "result": "...", "stream": "...", "report_md": "..." },
  "result": {
    "summary": "结论摘要（≤1500 字符）",
    "verdict": "ENDORSED",
    "score": 96,
    "report_md": "# 完整报告 Markdown…",
    "report_md_url": "/api/files/workspace/report/<工作区名>"
  },
  "html_reports": ["line_report/line_stability_report.html", "sentinel/quick_screen_report.html"]
}
```

`html_reports` 为 run 目录内全部 HTML 产物的**run 相对路径**，浏览器可用
`/api/files/workspace/asset/<工作区名>/<相对路径>?token=<API Token>` 直接打开。

## 行为说明与边界

- `POST /analyze` 默认**异步**（202 立返 run_id）；`wait:true` 最长阻塞
  `wait_timeout_minutes`（默认 30）分钟，超时返回 202 + `wait:"timeout_still_running"`。
  外部 HTTP 客户端对 claude 等真实引擎建议异步 + 轮询/SSE。
- `POST /chat` 只对**运行中**的分析有效；无存活进程返回 409
  `EXTERNAL_CHAT_UNAVAILABLE`（对话回复内容经 SSE 流返回）。
- 结果里的 `report_md` 为分析 agent 产出的原始 Markdown；`html_reports` 依赖各 skill
  的 HTML 产物约定（line-report/sentinel 均已内置生成步骤）。
- 鉴权失败返回 401 `AUTH_REQUIRED`；未知 intent 返回 400 `EXTERNAL_INTENT_UNKNOWN`
  并附 supported 列表；数据路径不存在返回 400/404。
