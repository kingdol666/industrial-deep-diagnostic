# AgentWorkShop 集成说明(diag-bridge 插件消费契约)

> 本项目作为 [AgentWorkShop](https://github.com/kingdol666/AgentWorkShop) 的**工业深度诊断引擎插件**后端。
> AgentWorkShop 侧插件:`.AgentWorkShop/plugins/diag-bridge/` —— 导出 DAQ 时序快照 CSV → 本服务执行 9 阶段根因分析 → 报告回流入 AgentWorkShop 知识库(rag-knowledge)。
> 本文记录 2026-09-07 三系统集成时钉死的调用契约,本项目**零代码改动**,仅需保证以下行为不破坏。

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
