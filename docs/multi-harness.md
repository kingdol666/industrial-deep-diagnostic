# 多 Harness（执行引擎）适配架构

> 落地日期：2026-09-10 · 参照 `AgentWorkShop/docs/multi-harness-architecture.md` 移植
> 本文档描述工业深度诊断系统（industrial-deep-diagnostic）中的多引擎实现，14 个引擎全部可经 REST API / 前端选择驱动诊断作业。

---

## 0. 设计原则（与源文档一致的七条纪律）

1. **单一契约**：所有引擎客户端输出 Claude-SDK 兼容的标准事件流（`system` init / `assistant` text·tool_use·thinking / `user` tool_result / `result`）。`diagnosis.service.mjs` 的消费循环对所有引擎完全一致，永远不出现 `if (harness === 'codex')`。
2. **单一事实源注册表**：`app/backend/src/harness/engines.mjs` 的 `HARNESS_DEFS` 表声明每个引擎的 id/名称/描述/主页/进程模型/**能力面**/探测方式。前端下拉、可用性面板、执行前校验全部从此派生。
3. **两种进程模型**：**常驻会话型**（omp/codex/dsh/qwen/opencode/hermes：每回合一个长活子进程）与**一次性回合型**（gemini/copilot/cursor/crush/goose/pi：每回合 spawn，进程退出即回合结束）。各有共享基座。
4. **能力如实声明**：注册表 capabilities 反映真实能力，不虚报。引擎不支持跨进程 session resume 的（ACP 家族/codex/opencode），`startSessionChat` 直接 400 拒绝（诚实语义），Continue 走全量重放。
5. **执行前强校验**：所有启动入口（创建作业）统一 `assertHarnessUsable`——未知引擎 **400 HARNESS_UNKNOWN**、已注册但不可用 **409 HARNESS_UNAVAILABLE**（附 resolved command 与安装指引）。作业不会进入"起跑后失败"路径。
6. **错误即事件**：spawn 失败 / 非 0 退出 / 超时 / 协议错误全部产出 `result` error 事件（错误码形如 `CRUSH_EXIT_1` + stderr 尾部），绝不静默。
7. **探测与拉起同源**：可用性探测与真实 spawn 走同一个 `resolveCliBinary`（config `harness.engines.<id>.binary` → env `HARNESS_<ID>_COMMAND` → `where`/`which` → PATH+PATHEXT 扫描 → 裸名）。探测结果缓存 30s（`harness.health_cache_ms`）。

---

## 1. 十四个引擎一览

| id | 引擎 | 集成面 | 进程模型 | steer | HITL 审批 | session resume（跨进程） |
|---|---|---|---|:---:|:---:|:---:|
| claude | Claude Code SDK | 进程内 SDK（原有） | 进程内 | ✅ | canUseTool | ✅（UUID session） |
| omp | oh-my-pi | `omp --mode rpc`（原有） | 常驻子进程 | ✅ | auto-approve | ✅（`-c`，`omp:` 标记） |
| mock | 进程内剧本引擎 | 无 LLM，恒可用 | 进程内 | — | — | 进程内 ✅ |
| codex | OpenAI Codex CLI | `codex app-server`（NDJSON JSON-RPC v2，thread/start + turn/start） | 常驻 | ✅ | requestApproval → accept/decline | ❌ |
| dsh | DeepSeek Harness | `dsh --profile acp`（标准 ACP v1） | 常驻 | ❌ | session/request_permission | ❌ |
| opencode | OpenCode | `opencode serve` + HTTP + 全局 SSE | 常驻 | ✅ | permission.asked → once/reject | ❌ |
| gemini | Gemini CLI | `gemini --output-format stream-json` | 一次性 | ❌ | headless fail-safe | ✅（`--resume <sid>`，init 帧捕获） |
| copilot | GitHub Copilot CLI | `copilot --output-format json`（stdin 投递） | 一次性 | ❌ | 仅引擎默认 | ❌ |
| cursor | Cursor CLI | `cursor-agent --output-format stream-json`（Claude 同构帧；默认不带 `--force`） | 一次性 | ❌ | headless fail-safe | ❌ |
| crush | Charm Crush | `crush run -q`（纯文本 stdout；v0.92+ 无 JSON） | 一次性 | ❌ | 无 | ❌ |
| goose | Block Goose | `goose run -t --output-format stream-json --name idd-*` | 一次性 | ❌ | headless fail-safe | ✅（裸 `--resume` 按名恢复） |
| qwen | Qwen Code | `qwen --experimental-acp`（旧版 Zed ACP：camelCase、单隐式会话） | 常驻 | ❌ | requestToolCallConfirmation | ❌ |
| pi | pi coding agent | `pi -p --mode json`；prompt 经 **@临时文件** 投递 | 一次性 | ❌ | 无 | ❌ |
| hermes | Hermes Agent | `hermes acp`（标准 ACP v1，与 dsh 同型） | 常驻 | ❌ | session/request_permission | ❌ |

## 2. 代码地图

| 职责 | 文件 |
|---|---|
| 引擎定义表（单一事实源）+ 可用性探测缓存 | `app/backend/src/harness/engines.mjs` |
| 执行前强校验（400/409） | `app/backend/src/harness/availability.mjs` |
| 注册表 | `app/backend/src/harness/registry.mjs` |
| Harness 契约基类 | `app/backend/src/harness/base.mjs` |
| 引擎分发表（契约消费方） | `app/backend/src/services/diagnosis.service.mjs` (`ENGINES`) |
| 受控 spawn / 命令覆盖链 / `.cmd` 包装 / 进程树强杀 | `app/backend/src/engine/cli-common.mjs` |
| 一次性回合基座 | `app/backend/src/engine/one-shot.mjs` |
| 6 个 one-shot 引擎 spec（gemini/copilot/cursor/crush/goose/pi） | `app/backend/src/engine/oneshot-specs.mjs` |
| stdio JSON-RPC 2.0 基座 | `app/backend/src/engine/stdio-jsonrpc.mjs` |
| ACP 家族（dsh/hermes/qwen） | `app/backend/src/engine/acp-client.mjs` |
| codex app-server 客户端 | `app/backend/src/engine/codex-client.mjs` |
| opencode HTTP+SSE 客户端 | `app/backend/src/engine/opencode-client.mjs` |
| mock 剧本引擎 | `app/backend/src/engine/mock-client.mjs` |
| REST 层（列表/健康/批量可用性/运行浏览） | `app/backend/src/routes/harness.routes.mjs` |
| 前端引擎选择器 + 可用性灰化 | `app/frontend/src/App.vue` |

## 3. 关键工程纪律（本仓库实测沉淀）

- **npm shim 陷阱**：npm 全局包在 Windows 生成 sh / `.cmd` / `.ps1` 三种 shim；`where` 首选返回的 extensionless sh 文件 `spawn` 会 ENOENT。`whereLookup` 按优先级选 `.exe` → `.cmd/.bat`，Windows 上永不选无扩展名文件。
- **显式命令覆盖具权威性**：`HARNESS_<ID>_COMMAND` 指向不存在的路径时探测如实失败（409），**绝不静默回退**到 PATH 上的真实安装——否则"换引擎测试不可用路径"永远测不到。
- **`.cmd` 包装**：spawn 走字面量 `cmd.exe /d /s /c` + 逐参数校验（拒绝引号/控制字符/`%` 展开），参数面保持结构化；长 prompt 走 stdin 或 @argFile（pi），永不进 argv（goose 的 `-t` 例外：空白扁平化 + 6000 字符截断保护）。
- **sessionId 双模式**：`sessionMarker: true`（goose/crush）— `goose:run:<runId>` 不透明标记永久有效（goose 按 `--name` 恢复）；引擎型（gemini/cursor/pi）— 先发 `<id>:unbound:` 回退标记，引擎 init 帧上报真实 sid 后 **重发 init 事件**，`diagnosis.service` 据此二次落库（`meta.sessionId !== parsed.session_id` 判重）。
- **引擎能否续会话由引擎决定**：`engineCanResumeSession(harness, sessionId)` 在 continue/retry 前询问引擎 spec——不可续的引擎拿到完整 data_path 重新全量执行（带 follow-up 上下文），而不是拿到一个没有数据上下文的 `mode:'resume'`。
- **回合终点 = 进程终点**：resident 引擎（ACP/codex/opencode）在 result 事件后延迟 250ms 自杀进程树（win32 `taskkill /T /F`），杜绝每次诊断泄漏一个常驻引擎进程。
- **审批 fail-closed**：`harness.engines.<id>.auto_approve`（默认 true，无人值守诊断必须）关闭时，所有 permission/approval 请求一律拒绝。
- **schema 漂移防护**：解析器对未知事件忽略并计数，单帧解析异常不影响回合。

## 4. API

```
GET  /api/harness                    # 14 引擎 manifest（前端下拉数据源）
GET  /api/harness/availability       # 一次性批量探测（前端灰化数据源）
GET  /api/harness/:id/health         # 单引擎健康 + resolved binary + 版本
GET  /api/harness/:id/runs[...]      # 运行浏览（capabilities 含 runs 的引擎）
POST /api/diagnosis/start            # { harness: "<id>", ... } — 执行前强校验（400/409）
POST /api/diagnosis/execute/:runId   # 执行（SSE /api/diagnosis/stream/:runId）
POST /api/diagnosis/chat/:runId      # 会话续聊（引擎不支持 resume 时 400 人话报错）
POST /api/diagnosis/continue/:runId  # Continue — 不可续引擎走全量重放
```

## 5. 配置

`config/default.yaml` → `harness:` 段（可用 `config/local.yaml` 覆盖）：

```yaml
harness:
  timeout_minutes: 120        # CLI 引擎每回合超时
  health_timeout_ms: 8000
  health_cache_ms: 30000
  engines:
    codex:   { binary: "codex",  auto_approve: true }
    goose:   { binary: "goose",  session_name: "diag" }
    # ...每个引擎均可覆盖 binary / env / auto_approve / acp_args / model
```

命令覆盖链最后一环：环境变量 `HARNESS_<ID>_COMMAND`（如 `HARNESS_CODEX_COMMAND`）。

## 6. 已知边界（诚实声明）

- **Chat 标签页**（AI 对话）目前仅 claude/omp 引擎可实现；选择其它引擎时 chat 自动回落 claude 引擎（`chat.service.normalizeChatHarness`）。
- 一次性引擎的 `maxTurns` 由引擎内部循环决定，平台侧的回合预算 = 超时时间（`harness.timeout_minutes`）。
- 真实 LLM 诊断需要各引擎自身的凭据（环境变量，见 `/api/harness` 返回的 `authEnv`）；凭据缺失时引擎会以明确的错误事件失败（联调用 `mock` 引擎，恒可用、零依赖）。
- Web Chat 的 `harness` 列已入库但 chat 引擎分发仅 claude/omp 两路。

## 7. 测试

```bash
cd app/backend && npm test        # node --test，45 用例
```

- **registry.test** — 14 引擎注册 / 能力矩阵 / 400+409 三态校验（含"显式覆盖不存在→409 不回退"）。
- **one-shot.test** — 假 CLI（真实子进程）：stdin/@argFile 投递、标准事件映射、init 重发、resume 参数、非 0 退出→错误事件（stderr 尾部）、abort 杀树。
- **oneshot-specs.test** — 6 引擎 spec 纯映射：argv 纪律（cursor 无 `--force`、goose 长度截断、pi `@file`）、逐 dialect 事件映射、未知事件容忍。
- **resident-engines.test** — 假 ACP 引擎（dsh）+ 假 codex app-server：握手、单飞 prompt、session/update 映射、审批自动放行、诚实 400。
- **mock-e2e.test** — 启动真实服务器（隔离 DB、关闭鉴权）：REST 契约、可用性三态、mock 作业 create→execute→SSE→完成落库（workspace/report/score/verdict 关联）→chat→continue→stop→失败剧本。
