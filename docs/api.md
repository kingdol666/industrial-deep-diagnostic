# Industrial Deep Diagnostic — 外部 API 接口定义

> Base URL: `http://localhost:3210` · 鉴权: `Authorization: Bearer <token>`（登录会话或 API Token；`AUTH_ENABLED=0` 可本机关闭）
> 所有响应统一信封: 成功 `{"success": true, "data": ...}` · 失败 `{"success": false, "code": "<ERROR_CODE>", "error": "<人话消息>"}`

---

## 0. 外部接入三步（已验证的调用路径）

```bash
# ① 注册/登录拿会话 token（或让管理员用已有账号创建 API Token）
curl -s -X POST http://localhost:3210/api/auth/login \
  -H "content-type: application/json" \
  -d '{"username":"<user>","password":"<pwd>"}'
# → {"success":true,"data":{"session_token":"...",...}}

# ② 用会话 token 创建程序化 API Token（明文仅返回一次）
curl -s -X POST http://localhost:3210/api/auth/tokens \
  -H "Authorization: Bearer <session_token>" -H "content-type: application/json" \
  -d '{"name":"agentshop-integration"}'
# → {"success":true,"data":{"token":"idd_xxxxxxxx",...}}

# ③ 用 API Token 调用任意业务接口 / 启动指定 harness 的诊断作业
node scripts/smoke-api.mjs --base http://localhost:3210 --token idd_xxxxxxxx
# 冒烟脚本覆盖: 14 引擎注册表 / default 引擎 / availability / 健康 /
# 指定 harness 作业全链路 / 默认引擎作业 / 会话续聊 / continue / 三类错误契约 / 历史列表
```

- 本仓库自带外部调用方冒烟脚本 `scripts/smoke-api.mjs`（token 经参数或 `IDD_API_TOKEN` 环境变量传入，不落盘不入库）。
- API Token 前缀 `idd_`，可创建多个、可吊销（`DELETE /api/auth/tokens/:id`）。

---

## 1. 错误码总表（外部调用者按此分支处理）

| code | HTTP | 含义 | 调用方应对 |
|---|---|---|---|
| `AUTH_REQUIRED` / `AUTH_INVALID` / `AUTH_EXPIRED` | 401 | 未携带/无效/过期 token | 重新登录或换 API Token |
| `AUTH_FORBIDDEN` | 403 | 权限不足 | 联系管理员 |
| `HARNESS_UNKNOWN` | 400 | harness id 未注册（拼写错误/不存在） | 读取 `GET /api/harness` 修正 id；错误消息内含全部合法 id 列表 |
| `HARNESS_UNAVAILABLE` | 409 | 引擎已注册但当前不可用（CLI 未安装 / `--version` 探测失败） | 安装引擎 CLI，或用 `config harness.engines.<id>.binary` / env `HARNESS_<ID>_COMMAND` 覆盖命令；错误消息含 resolved command |
| `HARNESS_NOT_FOUND` | 404 | URL 中的 harness id 不存在 | 同 `HARNESS_UNKNOWN` |
| `HARNESS_NOT_SUPPORTED` | 400 | 该引擎不支持所请求的操作（如对无 runs 能力的引擎请求运行列表） | 检查 manifest 的 `capabilities` |
| `HARNESS_NONE_AVAILABLE` | 503 | 无任何引擎可用 | 检查安装/配置 |
| `CHAT_HARNESS_UNSUPPORTED` | 400 | AI Chat 仅支持 claude/omp（诊断作业无此限制） | 用 claude/omp 起 chat；诊断作业改走 `/api/diagnosis/start` |
| `DATA_NOT_FOUND` | 404 | 数据路径不存在 | 修正 `dataPath`（相对 `data/` 或项目根） |
| `PATH_TRAVERSAL` | 403 | 数据路径越界（项目根之外） | 使用项目内路径 |
| `DIAGNOSIS_ERROR` / `CHAT_ERROR` / `HARNESS_ERROR` | 400/500 | 业务/内部错误（兜底码） | 读 `error` 消息 |

错误消息原则：**人话 + 可执行指引**。例如 409 会明确写出"哪个命令没找到、如何覆盖"。

---

## 2. Harness 接口

| 方法 & 路径 | 说明 |
|---|---|
| `GET /api/harness` | 全部 14 引擎 manifest：`{id,name,kind,description,capabilities[],processModel,homepage,features,authEnv[]}`。capabilities: `live`(可执行诊断)/`chat`(会话续聊)/`runs`(运行浏览)/`report`/`html`/`enhancement` |
| `GET /api/harness/default` | 当前默认引擎（= 适配最好的已装引擎）：`{"id":"omp","manifest":{...}}`。解析链：`config harness.default`（omp）不可用 → claude → mock → 其余按适配度 |
| `GET /api/harness/availability` | 批量探测（服务端缓存 30s）：每项含 `available`、`default`（恰有一个为 true）、`meta.binary/version/probe_error` |
| `GET /api/harness/:id/health` | 单引擎健康 + resolved binary + 版本 |
| `GET /api/harness/:id/runs` | 运行列表（需 `runs` 能力，当前 omp） |
| `GET /api/harness/:id/runs/:run` | 运行详情（manifest/artifacts/events） |
| `GET /api/harness/:id/runs/:run/summary` | 轻量摘要 |
| `GET /api/harness/:id/runs/:run/artifact/:kind` | 产物内容（report/diagnosis/…；缺失返回 200+null） |
| `GET /api/harness/:id/runs/:run/enhancement/:kind` | 增强产物 |
| `GET /api/harness/:id/runs/:run/html?mode=baseline\|enhanced` | HTML 报告（可直接 iframe） |

## 3. 诊断作业（可指定 Harness；缺省用默认引擎）

| 方法 & 路径 | 说明 |
|---|---|
| `POST /api/diagnosis/start` | 创建作业。body: `{harness?, dataPath|folderPath|dataPaths, userQuestion?, sceneName?, maxTurns?, timeoutMinutes?, reportLanguage?, ontologyMode?, enhancement?}`。**harness 缺省 = 默认引擎（omp）**；未知→400 `HARNESS_UNKNOWN`；未安装→409 `HARNESS_UNAVAILABLE`。返回 `{runId,name,harness,...}` |
| `POST /api/diagnosis/execute/:runId` | 执行 pending 作业（引擎按入库时的 harness 分发） |
| `GET /api/diagnosis/stream/:runId` | SSE 实时流（status/message/tool_use/tool_result/stats/complete/error） |
| `GET /api/diagnosis/status/:runId` | 状态查询（含 workspace_path/report_path/score/judge_verdict） |
| `GET /api/diagnosis/snapshot/:runId` | 事件流快照（断线重连恢复用） |
| `POST /api/diagnosis/stop/:runId` | 停止（杀引擎进程树） |
| `POST /api/diagnosis/continue/:runId` | Continue — 附 `{followUpMessage?}`；支持跨进程续会话的引擎（omp/claude/gemini/goose）走 session resume，其余引擎全量重放 |
| `POST /api/diagnosis/chat/:runId` | 向运行中会话发消息（引擎不支持 resume 时 error 事件含人话指引） |
| `POST /api/diagnosis/enhance/:runId` | 一键深度增强（E0-E8，确定性脚本链） |
| `POST /api/diagnosis/answer/:runId` | 回答 AskUserQuestion 结构化提问 |
| `POST /api/diagnosis/hitl/:hitlId` | HITL 审批应答 `{approved}` |
| `GET /api/diagnosis/list` / `GET /api/history/...` | 作业列表 / 历史 |

**外部调用示例（指定 harness）**：

```bash
TOKEN=...
# 指定引擎
curl -X POST http://localhost:3210/api/diagnosis/start \
  -H "Authorization: Bearer $TOKEN" -H "content-type: application/json" \
  -d '{"harness":"goose","dataPath":"data/smoke.csv","userQuestion":"分析主轴温升根因","sceneName":"spindle_check"}'
# → {"success":true,"data":{"runId":"a1b2c3d4","harness":"goose",...}}

# 用默认引擎（harness 缺省）
curl -X POST http://localhost:3210/api/diagnosis/start \
  -H "Authorization: Bearer $TOKEN" -H "content-type: application/json" \
  -d '{"dataPath":"data/smoke.csv","userQuestion":"..."}'

# 错误响应示例（409）
# {"success":false,"code":"HARNESS_UNAVAILABLE","error":"Harness \"cursor\" is not usable:
#  spawn cursor-agent ENOENT. Install the engine CLI, or override the command via
#  config harness.engines.cursor.binary / env HARNESS_CURSOR_COMMAND."}
```

## 4. AI Chat

| 方法 & 路径 | 说明 |
|---|---|
| `POST /api/chat/start` | `{harness?('claude'|'omp'), prompt, cwd?, ...}`；其它引擎→400 `CHAT_HARNESS_UNSUPPORTED` |
| `GET /api/chat/stream/:chatId` | SSE 会话流 |
| `POST /api/chat/send/:chatId` / `stop/:chatId` | 发消息 / 停止 |

## 5. 数据 / 分析 / 本体 / RAG

| 方法 & 路径 | 说明 |
|---|---|
| `POST /api/files/upload` · `GET /api/files/list` · `GET /api/files/preview/:name` | 数据接入 |
| `GET /api/analysis/chart-data/:runName` | 报告图表数据 |
| `POST /api/ontology/...` | 本体资产管理（reuse/extend/full） |
| RAG 引擎（独立服务 :8764） | `GET /health` · `POST /retrieve {scenario,target_columns,parameter_columns,mode:local_only|web_only|hybrid,top_k,custom_query?}` · `POST /score` · `POST /inject` · `POST /pipeline/retrieve-score` · `POST /pipeline/full` · `POST /index/upload`（入库：md/txt/csv/json/pdf + `scenario` form 字段） · `POST /index`（按 config.yaml 索引源重建） · `GET /runs`（执行证明落库） |

## 6. 认证

| 方法 & 路径 | 说明 |
|---|---|
| `POST /api/auth/register` / `POST /api/auth/login` | 公开；返回 `session_token` |
| `GET /api/auth/me` | 当前身份 |
| `POST/GET/DELETE /api/auth/tokens[...]` | API Token 管理（明文仅返回一次） |
