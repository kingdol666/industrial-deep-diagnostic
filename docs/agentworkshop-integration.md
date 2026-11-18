# AgentWorkShop 集成说明(diag-bridge 插件消费契约)

> 本项目作为 [AgentWorkShop](https://github.com/kingdol666/AgentWorkShop) 的**工业深度诊断引擎插件**后端。
> AgentWorkShop 侧插件:`.AgentWorkShop/plugins/diag-bridge/` —— 导出 DAQ 时序快照 CSV → 本服务执行 9 阶段根因分析 → 报告回流入 AgentWorkShop 知识库(rag-knowledge)。
> 本文记录 2026-09-07 三系统集成时钉死的调用契约,本项目**零代码改动**,仅需保证以下行为不破坏。
>
> **2026-11-18 更新（推荐迁移）**：新增统一对外集成面 `/api/external/v1/*`（完整字段级文档见
> `docs/api-external.md`）。新插件/增强应优先走 external v1 —— 一个 `POST /analyze` 即含
> start+execute+任务跟踪（支持 `wait:true` 同步阻塞或 task 轮询/SSE 异步），且自动注入
> skill 规范提示词 + 本体指令 + 产线记忆（§17/§18）。下表 diag-bridge 旧契约继续有效。

## ⚠️ 鉴权(v4 起强制)

- 除 `GET /api/health`、`POST /api/auth/register`、`POST /api/auth/login` 外，**所有 `/api/*` 端点（含本表全部端点与 WS `/ws`）均要求** `Authorization: Bearer <token>`。
- 调用方需先在系统注册账号并登录，创建一个 API Token（如 `diag-bridge-key`），之后所有请求携带该 token。
- 失败返回 401 + `{success:false, code:'AUTH_REQUIRED'|'AUTH_INVALID'|'AUTH_TOKEN_EXPIRED'|'AUTH_TOKEN_REVOKED', error}`；WebSocket 认证失败以 close code 4401 关闭。
- Token 规范:`idd_` 前缀 + 256bit 熵，服务端仅存 SHA-256 哈希；支持名称/创建时间/失效时间(1-365 天或永久)/吊销/最近使用时间；每个用户可创建多个。
- 应急开关：env `AUTH_ENABLED=0` 可临时关闭鉴权（仅限本机调试）。

## 调用方(AgentWorkShop diag-bridge 插件)

| 步骤 | 端点 | 关键约定 |
|---|---|---|
| 健康 | `GET :3210/api/health` | `checks.activeRuns` 可观测 |
| 数据上传 | `POST :3210/api/files/data/upload` | multipart 字段名**必须是 `files`**(可带 `folder`);**dataPath 必须用返回的相对路径**(如 `data/aw-snapshots/x.csv`),绝对路径会被 PATH_TRAVERSAL 拦截(403) |
| 发起诊断 | `POST :3210/api/diagnosis/start` | `{dataPath, sceneName, userQuestion, harness:"omp", enhancement:"off", reportLanguage:"zh", maxTurns, timeoutMinutes}` → `{success, data:{runId, name}}`。**harness 必须显式传 `"omp"`**——`normalizeHarness` 仅识别 `'omp'`,其余一切取值(含缺省)落 claude 引擎,部署机无 ANTHROPIC_API_KEY 时会失败 |
| 执行 | `POST :3210/api/diagnosis/execute/:runId` | start 后必须显式 execute |
| 状态轮询 | `GET :3210/api/diagnosis/status/:runId` | 插件 15s 轮询;关注 `status/name/score/judge_verdict/report_path` |
| 报告全文 | `GET :3210/api/files/workspace/report/:runName` | runName 取 status 响应的 `name` |

## 推荐：external v1 一步式（新插件用这个）

```bash
BASE=http://<host>:3210/api/external/v1
# 1) 能力发现（7 intent × 14 harness，含每引擎 supported_intents）
curl "$BASE/capabilities" -H "Authorization: Bearer $TOKEN"
# 2) 一步发起（start+execute 合一；wait:true=同步阻塞到终态，否则 202+task_id 异步轮询）
curl -X POST "$BASE/analyze" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"folderPath":"aw-snapshots","analysisIntent":"stability-report","harness":"omp",
       "sceneName":"lineA","question":"近 72h 稳定性如何","wait":false}'
# 3) 轮询 → 终态取结果（result 内含 summary/verdict/score/report_md 全文/files 路径）
curl "$BASE/tasks/$TASK_ID"        -H "Authorization: Bearer $TOKEN"
curl "$BASE/tasks/$TASK_ID/result" -H "Authorization: Bearer $TOKEN"
# 4) 可选：SSE 实时流 / chat 续聊 / stop 停止 / results 结果库索引
```

可用 `analysisIntent`：`deep-diagnosis`（默认 9 阶段）· `stability-report` · `quick-screen` ·
`doe-analysis` · `experience-mining` · `optimizer-campaign` · `improvement-advisory`（A/B/C 分级
建议 + 95%CI + optimizer_seed）。每个 intent 由后端自动注入对应 skill 的规范提示词（skill 协议为
绑定契约、禁止跳步/编数），并按产线自动携带跨 run 记忆先验——见 `docs/api-external.md` §17/§18。

## 快照 CSV 输入约定

- 列:`timestamp`(本地时区 ISO,带偏移)+ 每数采节点一列(列名=节点 id);行=时间戳对齐(bucket 5s 降采样)。
- 上限:插件保证唯一时间戳 < 10000(超出即拒绝导出并提示缩小时间窗),远低于本服务 500MB×50 文件上限。

## 运行依赖

- 执行引擎 `omp`:`GET /api/harness/omp/health` 应为 `available:true`;omp CLI 需在宿主机可用且已配置模型。
- E0-E8 增强(零 LLM)可作为低成本档:`enhancement` 传 `on`/`auto`;当前插件默认 `off` 以控制时长。

## 与 AgentWorkShop 的闭环

```
AgentWorkShop DAQ(实时数采)
  → diag-bridge 导出快照 CSV → POST /api/files/data/upload
  → POST /api/diagnosis/start(harness=omp)→ execute → 轮询 status
  → GET report → 写入 rag-knowledge(aw-industrial 库,tags: source:diag-bridge)
  → Agent 经 kb_search / diag_status 工具消费 → DCW 控制策略 + HITL 审批 → 写回产线
```
