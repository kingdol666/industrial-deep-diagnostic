# 后续优化批次 — 验收规范 v1 (2026-10-22)

> 适用对象：`docs/plans/session-management-followups-plan-2026-10-22.md`（v2）所交付的
> 评分打通、全 harness 续聊、codex/opencode 意图、前端可测试性、mock 语义标注。
> 本文是**可执行判据**，不是描述；每条都给出命令或浏览器断言。证据目录：
> `workspace/acceptance/2026-10-22/`（截图 + `audit.json`）。

## 1. 验收范围与原则

- 范围：Harness 注册/探测 API、统一诊断调度、specialist 结果派生、续聊路由、外部 API、
  前端-后端实时交互、界面渲染与视觉质量。
- 原则：**真实引擎优先**（至少一次 OMP 真实完成 + 一次真实续聊）；mock 只证明平台契约；
  每个用户可见数字必须能追溯到工件；界面验收必须包含控制台/网络审计与截图。

## 2. AC-A：Harness API 契约

| ID | 判据 | 期望 |
|---|---|---|
| AC-A1 | `GET /api/harness` | 200，14 个引擎；`mock/goose` 含 `chat`，其余定义表引擎只有 `live`；claude/omp 含 `chat` |
| AC-A2 | `GET /api/harness/availability` | 200，14 项；恰好 1 项 `default:true` 且 `available:true`；`mock` 恒可用；不可用引擎带 `meta.probe_error` |
| AC-A3 | `GET /api/harness/default` | 200，`id` 属于可用集合；`manifest.id == id` |
| AC-A4 | `GET /api/harness/mock/health` | 200，`available:true`，`meta.inprocess:true` |
| AC-A5 | `GET /api/harness/omp/runs` | 200，返回 OMP 运行列表（runs 能力） |
| AC-A6 | `GET /api/harness/not-a-real-engine/health` | 404 `HARNESS_NOT_FOUND` |
| AC-A7 | `GET /api/harness/mock/runs` | 400（该引擎不提供 run 浏览） |

## 3. AC-B：统一诊断调度（真实引擎）

| ID | 判据 | 期望 |
|---|---|---|
| AC-B1 | `POST /api/diagnosis/start {harness:'not-a-real-engine'}` | 400 `HARNESS_UNKNOWN` |
| AC-B2 | 显式不可用引擎（本机 `qwen`/`pi` 或测试覆盖） | 409 `HARNESS_UNAVAILABLE` |
| AC-B3 | `POST /api/diagnosis/start {harness:'omp', analysisIntent:'stability-report', dataPath:'data/lsr_demo/line_demo.csv'}` + `/execute` | 200；run 行 `harness=omp`、`analysis_intent=stability-report`、`session_id` 以 `omp:` 开头 |
| AC-B4 | 运行期间 `GET /api/diagnosis/snapshot/:id` | 事件数持续增长；含 `system/init`、`message`、`tool_use`、`tool_result`；`engineStatus=running` |
| AC-B5 | 运行完成 | `status=completed`；`workspace_path`/`report_path` 已链接；stability 工件 `line_report/stability_report.json` + `line_stability_report.html` 存在；`score==conclusion.score`、`verdict=='<grade> · <label>'` |
| AC-B6 | `GET /api/diagnosis/session-map/:id` | `harness_matches_session=true`、`session_kind=omp`、`resumable=true` |
| AC-B7 | WS 续聊（`scripts/e2e/ws-live-chat-e2e.mjs --run <id>`） | 5/5；POST 200 `mode=session`；新 `_seq` 的 assistant 事件实时到达；用户消息原文无注入 |
| AC-B8 | 运行中 `POST /api/diagnosis/stop/:id` | 200 `stopped`；后续 result 不得改回 `failed` |
| AC-B9 | `POST /api/diagnosis/chat/does-not-exist` | 404 `RUN_NOT_FOUND` |

## 4. AC-C：外部集成 API

| ID | 判据 | 期望 |
|---|---|---|
| AC-C1 | `GET /api/external/v1/capabilities` | 6 intents；每个 harness 含 `session_resume`、`supported_intents`（6 个） |
| AC-C2 | `POST /api/external/v1/analyze`（mock，非 wait） | 202，返回 `task_id`/`run_id`；任务条目 `analysis_mode=mock` |
| AC-C3 | `GET /api/external/v1/analyze/:id`（完成的真实 run） | `analysis_mode=real`；`result.score/verdict` 与工件一致；`files.html[]` 含真实路径 |
| AC-C4 | `POST /api/external/v1/chat`（真实 run） | 200 `mode=session`；不存在的 run → 404；无上下文 → 409 `RESUME_UNSUPPORTED` |
| AC-C5 | `GET /api/external/v1/tasks/:id/result`（终态） | 200，`result.report_md` 非空，`files.report_md_path` 指向真实文件 |

## 5. AC-D：前端-后端交互

| ID | 判据 | 期望 |
|---|---|---|
| AC-D1 | 浏览器加载登录页→登录→History→续聊→发送 | 无 `Runtime.exceptionThrown`；`console.error` 为 0；无失败的 `/api/*` 请求（status≥400） |
| AC-D2 | 实时视图 | 打开运行中的 run 后，工具流/消息无需刷新持续追加；完成后状态徽章变 `completed` |
| AC-D3 | History 评分/结论 | `46833919` 行显示 `65.8` 与 `C · 波动`；`C` 徽章为黄色；`alert · …` 为红色；优化 phase 为中性色 |
| AC-D4 | 报告页 | Markdown 正文渲染出标题与表格；HTML 标签页 iframe 有内容（非空白、非 401 页） |
| AC-D5 | 续聊 | 点击历史行「继续对话」进入 run 视图；发送后收到 assistant 回复；输入框清空 |
| AC-D6 | 可选探针不产生噪音 | 缺失工件的 `artifact/:kind` 返回 200+null；前端无 404 控制台噪音 |

## 6. AC-E：界面渲染与视觉质量

| ID | 判据 | 期望 |
|---|---|---|
| AC-E1 | 1440×900 登录页 | 卡片居中、无横向滚动、字段对齐、主按钮层级清晰 |
| AC-E2 | 1440×900 History | 页面无横向溢出（`documentElement.scrollWidth ≤ innerWidth+1`）；表格在容器内滚动；评分/结论列不换行、不裁切（长文本有 `title`） |
| AC-E3 | 运行视图 | 头部/状态/时间线/聊天坞不重叠；聊天坞固定可见；长路径省略号 |
| AC-E4 | 报告页 | 行宽可读、标题层级清楚；HTML iframe 高度占满且无双重滚动条；图表/表格未溢出卡片 |
| AC-E5 | 1280×800 History | 无横向页面溢出；关键操作按钮仍可见（表格容器可滚动） |
| AC-E6 | reduced-motion | `prefers-reduced-motion: reduce` 下装饰动画 `animation-duration < 0.01s` |
| AC-E7 | 截图人工复核 | 6 张截图（登录/History/运行/报告 MD/报告 HTML/1280）无错位、遮挡、空白块；配色符合语义 |

> 视觉判据以截图人工复核为准；AC-E2/E5 的溢出为程序断言，避免主观漏判。

## 7. AC-F：回归

`app/backend npm test` 207/207；stability 173；sentinel 183；doe 199+69+46；
preprocessor 全过；shared 9+1；前端 build；镜像 `--check`；`intent-prompt-contract`
failures=0；`ui-smoke-native` 12/12。

## 8. 执行方式

```bash
# 契约 + 真实运行（脚本化）
node scripts/e2e/harness-api-acceptance.mjs --base http://127.0.0.1:3211
node scripts/e2e/ws-live-chat-e2e.mjs --run <completedRunId> --base http://127.0.0.1:3211
# 浏览器交互 + 截图 + 控制台/网络审计
node scripts/e2e/ui-visual-audit.mjs --api http://127.0.0.1:3211 --web http://127.0.0.1:5181 \
  --run 46833919 --out workspace/acceptance/2026-10-22
```

验收结果回填到本文 §9（执行后）。

## 9. 验收结果（2026-10-22 执行）

### 9.1 总体

| 组 | 结果 |
|---|---|
| AC-A Harness API（`scripts/e2e/harness-api-acceptance.mjs`） | **全 PASS**（A1-A7；14 引擎、能力表如实、availability/default/health/runs、404/400 语义） |
| AC-B 统一调度（真实 OMP） | **全 PASS**（B1/B3-B9；B2 因本机全部引擎可用跳过，由 mock-e2e 的强制不可用用例覆盖） |
| AC-C 外部 API | **全 PASS**（C1-C5；capabilities 带能力面，mock `analysis_mode`，真实 run 结果与工件一致，chat mode=session） |
| AC-D 前端-后端交互（`scripts/e2e/ui-visual-audit.mjs`） | **20/20 PASS**（无未捕获异常/console error/失败 `/api` 请求；实时渲染、评分/结论、报告 MD+HTML、续聊） |
| AC-E 界面渲染 | 程序断言全过 + 6 张截图人工复核通过（1440 全列可见、1280 粘性操作栏、reduced-motion `1e-05s`） |
| AC-F 回归 | backend **208/208**；stability 173；sentinel 183；doe 199+69+46；preprocessor 全过；shared 9+1；前端 build；镜像一致；intent-contract 0 失败；ui-smoke-native 12/12；session-management E2E before/after 0 失败 |

真实引擎存证：OMP run `bf9e6aa2`（stability-report，`data/lsr_demo/line_demo.csv`）完整跑完，
score 65.8 / verdict `C · 波动` 与 `stability_report.json` 一致；session-map resumable；
真实引擎续聊在 **claude run `b5c9236a`** 上全链路 5/5（WS 实时收到回复「收到」，无提示词注入）。

### 9.2 验收过程中发现并修复的缺陷（6 个）

| # | 缺陷 | 修复 |
|---|---|---|
| 1 | **打开已完成 run 会把它变成 pending**：引擎 `subscribe()` 对缺失 run 建的内存条目默认 `pending`，而 `listRuns()`/状态视图优先引擎状态 → History 状态翻转、继续/报告按钮消失 | `diagnosis.service.subscribeRunView/subscribeSSE` 先按持久化状态 `seedRunViewEntry`；WS 视图订阅改走该入口；单测锁定 |
| 2 | **History 操作列在 1440px 被横向滚动出屏**（1350px 表宽 > ~1150px 内容区），报告/继续按钮不可见 | 操作列 `position: sticky; right: 0` 兜底 + 压缩列宽至 1138px（1440 全列可见）、按钮文案精简、日期短格式（title 保留全量） |
| 3 | **报告页每次打开都对 `optimizer.md` 打 404**（console/网络噪音） | `/api/files/workspace/optimizer/:run` 改为 200+null（与 harness artifact 约定一致），前端空安全 |
| 4 | **History「报告」按钮在 Windows 落到 run 列表**：`report_path.split('/')` 遇反斜杠取不到目录名 | `runDirFromReportPath` 按 `/[\/]/` 切分 |
| 5 | **已完成 run 的耗时显示 0:00**；聊天提示写死「已选 Claude session」 | 终态一次性计算 created→completed 真实时长；提示改为引擎中立（可恢复则续聊，否则同引擎重建） |
| 6 | **OMP 续聊静默无响应（两个叠加根因）**：① 完成的 run 引擎进程在 `close_run_delay` 内仍持有会话文件锁，随后的 resume 撞 OMP 跨进程锁进入无事件重试；`-c` 一旦落在新会话文件上会永远续到空回放 | ① 流结束即 `closeAllEngines`（closeRun 仍延迟）；② resume 改为 `--resume=<目录内最旧 jsonl>`（run 自己的会话文件）而非 `-c`；③ 聊天回合 10 分钟无事件看门狗（`diagnosis.chat_turn_idle_timeout_minutes`）；④ OMP assistant `stopReason=error` 显式发 system:notice |

### 9.3 环境边界（非代码缺陷）

- OMP 当前 provider（ustc/deepseek-flash）**预算耗尽**（429 `Budget has been exceeded … Current cost: 100.38, Max budget: 100.0`）：
  本日 OMP 的续聊回合由 provider 拒绝，错误现已显式出现在事件流（system:notice）。
  真实引擎续聊的完整证明由 claude run 承担（上表）；OMP 的调度/完成/产物/评分链路当日已全绿。
- OMP resume 的 `--resume=<最旧 jsonl>` 约定依赖「每个诊断 run 只创建一个会话文件」；若上游行为变化需同步调整。
