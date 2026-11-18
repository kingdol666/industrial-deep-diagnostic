# IDD 外部调用 API · AgentWorkShop 插件集成手册（v1.3 摘要）

> 目标读者：外部系统/插件开发者（如 AgentWorkShop diag-bridge 及后续插件）。
> 完整字段级文档：`docs/api-external.md`；本文是**可直接照抄的调用手册**，全部端点均在
> 2026-11-18 用真实 token 实测通过（同步/异步/SSE/续聊/停止/错误契约）。
> Base：`http://<host>:3210/api/external/v1`，认证 `Authorization: Bearer idd_…`。

---

## 0. 30 秒接入

```bash
BASE=http://<host>:3210/api/external/v1
TOKEN=idd_xxxxxxxx                                   # POST /api/auth/tokens 签发（见 §1）

# 能力发现：7 个分析意图 × 14 个执行引擎
curl "$BASE/capabilities" -H "Authorization: Bearer $TOKEN"

# 发起分析（异步）：202 + task_id + links
curl -X POST "$BASE/analyze" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"folderPath":"aw-snapshots","analysisIntent":"stability-report",
       "harness":"omp","sceneName":"lineA","question":"近72h稳定性","reportLanguage":"zh"}'

# 轮询 → 终态 → 取结果（report_md 全文 + files 路径都在 result 里）
curl "$BASE/tasks/$TASK_ID/result" -H "Authorization: Bearer $TOKEN"
```

## 1. 鉴权

| 事项 | 说明 |
|---|---|
| 获取 | `POST /api/auth/login`（会话 JWT）→ `POST /api/auth/tokens` `{name, expires_in_days}`（`idd_` 前缀明文仅返回一次） |
| 校验 | `GET /api/auth/me` → `auth_type:"api_token"` |
| 吊销 | `DELETE /api/auth/tokens/:id` |
| 失败码 | 401 `AUTH_REQUIRED` / `AUTH_INVALID` / `AUTH_TOKEN_EXPIRED` / `AUTH_TOKEN_REVOKED` |
- ⚠️ 凭据只存环境变量/密钥服务；不要把 `idd_` token 写进插件源码或配置模板。

## 2. 分析意图（analysisIntent，7 个）

| intent | skill | 典型产物 |
|---|---|---|
| `deep-diagnosis`（默认） | industrial-analysis-auto | 9 阶段诊断 + `diagnostic-report.html` |
| `stability-report` | industrial-line-stability-report | 0-100 评分/A-D 等级 + `line_stability_report.{html,md}` + 内置改善建议章 |
| `quick-screen` | industrial-sentinel | `alert.json` + `quick_screen_report.html` |
| `doe-analysis` | industrial-doe-analyzer | 效应/ANOVA/操作窗 + `recommendations.json`（证据等级 A~C） |
| `experience-mining` | industrial-tuning-memory | 调优动作归因 |
| `optimizer-campaign` | industrial-optimizer-loop | 布点试验设计（不下发参数） |
| `improvement-advisory` | industrial-improvement-advisor | A/B/C 分级建议（95%CI + 验证/回滚）+ `optimizer_seed.json`；数据不足时诚实 `not_actionable` + 处方清单 |

## 3. 执行引擎（harness，14 个）

`claude`（默认，真实 agent）· `omp`（推荐）· `mock`（进程内剧本，联调/CI 恒可用，**非真实分析**）·
`codex` · `dsh` · `opencode` · `gemini` · `copilot` · `cursor` · `crush` · `goose` · `qwen` ·
`pi` · `hermes`。未知 → 400 `HARNESS_UNKNOWN`；已声明但不可用 → 409 `HARNESS_UNAVAILABLE`。
`session_resume:true` 仅 claude/omp/goose/mock；其余引擎「续聊」为受控重建。
⚠️ 选 harness 前先看 `/capabilities` 的 `runs_capable`：只有 `live` 能力的引擎（如 qwen）提交会被
接受但执行诚实失败；引擎安装状态随机器变化，以 `GET /api/harness/availability` 实时探测为准。

## 4. POST /analyze — 发起分析（同步与异步二选一）

关键 body 字段（全表见 api-external.md §3.1）：

| 字段 | 必填 | 说明 |
|---|---|---|
| folderPath / dataPath / dataPaths | 三选一 | 相对 `data/` 或 workspace 白名单的路径；穿越 → 403/404 |
| analysisIntent | - | 缺省 deep-diagnosis；未知 → 400 `EXTERNAL_INTENT_UNKNOWN` |
| harness | - | 缺省 claude |
| sceneName / question / reportLanguage | - | 场景名 / 分析目标（进入 objective 与 agent 指令）/ `zh`·`en` |
| wait | - | `true` = **同步**：阻塞到终态（上限 `wait_timeout_minutes`，默认 30），响应即任务条目；超时 202 + `wait:"timeout_still_running"` |
| wait_timeout_minutes | - | ≥1 整数 |
| ontologyMode / ontologyScene / ontologySource | - | 本体策略（auto/full/reuse/extend；仅 deep-diagnosis/doe/stability/quick-screen） |
| preprocessingMode | - | `single_primary`（默认）/ `integrate_merge`，仅 stability-report |

**响应**：
- 异步：`202 {task_id, run_id, status:"accepted", links:{task,result,stream,status}}`
- 同步（wait=true，完成）：`200` 任务条目，`result` 内含 `summary/verdict/score/report_md/files`

## 5. 任务跟踪（异步三件套）

| 端点 | 用途 |
|---|---|
| `GET /tasks` | 本实例任务列表 |
| `GET /tasks/:taskId` | 进度轮询（`status/progress{events,tools,phase}`；传 run_id 也可识别） |
| `GET /tasks/:taskId/result` | **终态后稳定可读**：`result.summary/verdict/score/report_md/files{workspace_path,report_md_path,report_md_url,html[]}` |
| `GET /analyze/:runId/stream` | SSE 实时事件流（`text/event-stream`，终态以 `event: result` 收尾；`?events_limit=N` 有界回放） |
| `POST /analyze/:runId/stop` | 停止运行中的 run（已终态 → 409 + 原因） |
| `POST /chat` | 向运行中/已完成 run 发对话消息（claude/omp/goose/mock 支持真 resume；响应 `{delivered,mode,resumed}`） |

终态集合：`completed / failed / stopped / interrupted / expired / awaiting_input`。

## 6. 结果库（跨 run 知识索引）

```
GET   /results?brief=true&q=<关键词>     摘要索引（先看这个，省 token）
GET   /results/:resultId                 详情（summary_json.key_numbers 带溯源 + report_md 全文元数据）
PATCH /results/:resultId                 编辑 description/tags/title/category_id
GET|POST /results/categories             分类管理；GET /results/categories/:id/results 分类视图
```

## 7. 提示词注入：为什么外部调用不需要拼 prompt

后端 spawn 引擎时**确定性组装**完整提示词，所有引擎同一契约：

1. **Runtime Protocol** — 管道纪律（协议绑定、禁跳步、禁编数、语言规则）；
2. **Analysis Intent Directive**（专项意图）— 声明改派 skill：
   `Executing skill: <skill>. FIRST read .claude/skills/<skill>/SKILL.md in full`，
   并强制 setup → 预处理（stability）→ 分析 → HTML 步骤（quick-screen/advisory）→ report.md；
3. **Ontology Directive** — 本体阶段硬门（profile 感知；`ONTOLOGY_BRIEF_REQUIRED`）；
4. **Enhancement Directive**（仅 deep-diagnosis）— E0–E8 开关；
5. **Line Memory Directive** — 产线跨 run 记忆先验（L5，带"必须重新验证"纪律声明）。

含义：调用方只传 `analysisIntent` + 数据路径，引擎收到的就是"按该 skill 规范作业"的完整约束。
实测存证：`.runtime/acceptance/injection-proof-prompt.md`（5,364 chars，绑定行齐全）。

## 8. 产线记忆（自动，零配置）

- 同产线 run 越多，后续 run 的 prompt 自动携带越强的先验（共识/候选/线索分级，≈600 token 预算）；
- 同一数据窗重复跑**不会**虚增共识（同事故去重：窗口重叠 >50% 记 1 次独立）；
- 治理（查看/否决/合并/提案审批）走 console 面 `/api/line-memory/*`，外部 v1 面只读不写。

## 9. 错误码速查

| code | HTTP | 触发 |
|---|---|---|
| `AUTH_*` | 401 | token 缺失/无效/过期/吊销 |
| `EXTERNAL_INTENT_UNKNOWN` | 400 | analysisIntent 不在 7 值内（响应附 supported） |
| `HARNESS_UNKNOWN` / `HARNESS_UNAVAILABLE` | 400 / 409 | 引擎名错 / 未安装 |
| `EXTERNAL_DATA_REQUIRED` | 400 | 未传任何数据路径 |
| `DATA_NOT_FOUND` / `PATH_TRAVERSAL` | 404 / 403 | 数据路径不存在 / 越界 |
| `INTENT_UNSUPPORTED_ON_HARNESS` | 400 | 该引擎显式不支持该 intent |
| `PREPROCESSING_MODE_UNSUPPORTED_INTENT` | 400 | preprocessingMode 用在非 stability intent |
| `ONTOLOGY_UNSUPPORTED_INTENT` | 400 | ontology 字段用在 experience/optimizer intent |
| `RUN_NOT_IDLE` | 409 | 对运行中 run 续聊（先 stop 或等终态） |
| `RESULT_FORBIDDEN` | 403 | 结果库越权（外部 run 归属调用者） |

## 10. 推荐接入配方（AgentWorkShop 插件）

```js
// 1) 同步小任务（mock 冒烟 / 快筛类短任务）
const r = await POST(`${BASE}/analyze`, { folderPath, analysisIntent, harness:'omp', wait:true, wait_timeout_minutes:15 });
if (r.data.status === 'completed') use(r.data.result.report_md, r.data.result.files);

// 2) 异步真实分析（claude/omp，分钟级）：提交 → 轮询 → SSE 可选
const { data } = await POST(`${BASE}/analyze`, { folderPath, analysisIntent, harness:'omp' });
poll: while (true) {
  const t = await GET(`${BASE}/tasks/${data.task_id}`);
  if (TERMINAL.has(t.data.status)) break poll;
  await sleep(15000);                       // 15s 足够；不要 <2s
}
const res = await GET(`${BASE}/tasks/${data.task_id}/result`);
// 3) 报告入库（rag-knowledge）：直接取 res.data.result.report_md 全文 + files.html[] 路径
// 4) 续聊追问（可选）：POST /chat { run_id, message } —— 真引擎走 session resume
```

**插件侧建议**：① token 走环境变量；② 轮询间隔 ≥15s；③ 长任务优先 SSE `?events_limit=200`
做进度展示；④ 结果消费统一走 `result.report_md` + `results` 库索引，不要解析 DB；
⑤ 每个外部 run 都带 `sceneName` + `question`，会进结果库摘要与 objective，便于后续检索。
