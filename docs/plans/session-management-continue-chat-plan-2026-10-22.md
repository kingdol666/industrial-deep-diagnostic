# 会话管理 + 续聊增强 + 持久化补齐 + 生产加固 — 实施计划 v2 (2026-10-22)

> **状态：已批准执行**（v1 → v2 新增 §Phase B0 会话保真三道锁，对应 2026-10-22 追加需求）
> 事实底座：2026-10-22 四路并行调查 + 续聊路径二次核实，全部结论带 file:line。

## 0. 现状一句话

- **继续对话主体已实现**：run 完成后原视图输入框即续聊，claude/omp/goose 真 session resume，specialist intents 同构，聊天落库重启可回放——缺口是 4 个（见 Phase B）。
- **会话管理基本缺失**：仅有的删除只删 DB 行（工作区残留 + 孤儿目录被新 run 收养的串数据 bug）；改名/分类/归属全无。
- **持久化 runId 维度已达标**（DB+事件流+工作区，重启可查）；缺口是 task 内存态、产物无索引、无保留策略。
- **生产加固 6 项真风险**：store 并发写无锁、specialist 判定双向失真、无输入字节上限、崩溃 exit 语义冲突、磁盘无界、specialist 零事件。

## 0.1 v2 追加需求（用户 2026-10-22 明确）

| # | 需求 | 现状 | 本计划落点 |
|---|---|---|---|
| N1 | pending run 被终止后，项目启动时标为 **stopped**（不是 failed/expired） | 启动只把 `running→failed`（`index.mjs:38-43` + `getActiveRuns` SQL 只选 running），pending 原样滞留 | **B0.1** |
| N2 | **stop 与 complete 两种 run 都能点开继续对话** | complete ✅（sendChatMessage）；stopped ✅ 有 session 时；**stopped 但无 session（从未执行）→ 直接报错无法继续** | **B0.2** |
| N3 | **runId ↔ 真实 harness sessionId 完整映射，能找回对话内容** | session_id 只在 init 事件到达时写入；早期失败/中断的 run 可空；无回补机制 | **B0.3** |
| N4 | **续聊必须锁定原诊断的 harness，不得切换导致 sessionId 找不到** | 路径本身已用 `run.harness`（`sendChatMessage:671`、`executeDiagnosis:956`），但**无一致性校验**：session_id 是 omp 标记而 harness 被改成 claude 时会找错会话 | **B0.4** |

## 1. 决策记录（用户未答复，按推荐缺省执行；任何一条可推翻重排）

| # | 决策 | 采用 | 理由 |
|---|---|---|---|
| D1 | 分类与 run 归属 | **按用户隔离**：runs 加 `user_id`，分类按用户；admin 可见全部 | auth 基建在；修复"任何用户可删任何 run" |
| D2 | 删除语义 | **软删（deleted_at）默认 + 显式彻底删（连工作区目录）** | 修孤儿目录收养 bug；误删可挽回 |
| D3 | 续聊范围 | **核心三修**（NULL 覆写 bug / prompt 锚定 run_dir / 轮次可配）；其余引擎维持 400+Continue | 回归面最小，覆盖主用例 |
| D4 | 生产加固 | **纳入本轮**（§Phase D 六项） | 用户明确要"能够投入生产中使用" |

## 2. Phase A — 会话归属、分类与管理（约 1.5 人日）

**DB 迁移**（`app/backend/src/db/database.mjs`，迁移模式照抄 harness 列 :121-143）：
- `diagnostic_runs` ADD `user_id TEXT` / `title TEXT` / `deleted_at TEXT` / `category_id TEXT`；
- 新表 `run_categories(id TEXT PK, user_id TEXT NOT NULL, name TEXT NOT NULL, created_at)`（同 user 内 name 唯一，应用层校验）；
- `insertRun` 增加 user_id/title（title 缺省 = name）。

**归属接线**：`POST /api/diagnosis/start`、`/tasks`、`POST /api/external/v1/analyze` 均传 `userId: req.user.id`（三处 routes 已有 `req.user`）。

**端点**（挂 `history.routes.mjs`，rename 先例 = `PATCH /api/chat/session/:chatId`）：
- `PATCH /api/history/runs/:runId` `{title?|category_id?}` — 改名/归类（归属校验：非 admin 只能改自己的）；
- `DELETE /api/history/runs/:runId?purge=true|false` — 默认软删（`deleted_at=now`）；`purge=true` 连工作区目录 `rmSync(workspace_path)`（先例 `chat.service.mjs:1200-1228`；**必须同步删目录**，修 findLatestRunDir 孤儿收养 bug）；
- `POST /api/history/runs/:runId/restore` — 软删恢复；
- `GET /api/history/runs` 增强：`?include_deleted=false`（默认）`&category_id=&status=&q=&limit=&offset=`（`getAllRuns` 现无分页，加参数化 SQL）；
- 分类 CRUD：`GET|POST /api/history/categories`、`PATCH|DELETE /api/history/categories/:id`（删除分类时其 runs 的 category_id 置 null；admin 可见全部分类，普通用户只见自己的）。

**前端**（`HistoryList.vue` + `api/index.js` + i18n）：
- 标题列（显示 title，双击 inline 改名）；分类筛选下拉 + 行内归类；分类管理器（建/改名/删）；回收站 toggle（deleted 列表 + 恢复 + 彻底删按钮）；删除确认文案区分软删/彻底删。

**测试**：backend npm test 新增（DAO 层软删/恢复/purge/归属校验/分类 CRUD/分页过滤）；前端构建通过。

## 3. Phase B0 — 会话保真三道锁 + 重启语义（v2 新增，约 1 人日）

### B0.1 启动恢复语义：pending → stopped

现状：`index.mjs:38-43` 只遍历 `getActiveRuns`（SQL 仅 `status='running'`），pending 永久滞留。
做法：
- 新增 `stmts.getPendingRuns`（`status='pending'`）与 `stmts.markStopped`（status='stopped', error_message=注记, completed_at 不写）；
- 启动恢复顺序：①`running → failed`（保留既有语义，error='Server restarted — diagnosis interrupted'）②**`pending → stopped`**（error='Server restarted before execution — marked stopped'）；
- 前端状态映射：`stopped` 与 `completed` 行都显示"继续对话"入口（现状 stopped 已可 continue，补 UI 显式入口）。

### B0.2 stop/complete 都可续聊（含无 session 的 stopped）

现状：`sendChatMessage` 直接把 `run.session_id` 交给引擎；stopped 且从未执行过的 run（原 pending）session_id 为 null → 引擎报错、用户无法继续。
做法（`sendChatMessage`，diagnosis.service.mjs:668）：
- 前置分流：`if (!run.session_id)` → **委托 `continueDiagnosis(runId, message)`**（全量重建上下文的可续路径：同 harness、同 intent、同数据、follow-up 段落携带用户消息），并 emit system 提示"该会话无历史 session，已按当前诊断上下文重新建立"；
- 有 session → 原 resume 路径；
- 两条路径都对 `stopped`/`completed`/`failed` 开放（`continueDiagnosis` 已允许任何非 pending 状态）。

### B0.3 runId ↔ sessionId 完整映射（回补 + 校验）

现状：session_id 只在 init 事件到达时写入（`updateRunSession`）；中断早的 run 可空，重启后无回补。
做法：
- 启动时 `reconcileSessionIds()`：对 `status IN ('completed','stopped','failed')` 且 `session_id IS NULL` 的 run，从 `diagnosis_event_stream` 回扫 `event_type='system'` 且 payload 含 `session_id` 的最新一条 → 回写 DB；omp 的确定性标记 `omp:run:<runId>` 在无事件时按 harness 补齐；回补数量写日志；
- omp 会话目录 `workspace/.omp-sessions/<runId>/` 存在性作为二次证据（存在则必补标记）；
- 新增只读审计端点 `GET /api/diagnosis/session-map/:runId` → `{run_id, harness, session_id, session_kind, resumable, source, reconcilable}`，供前端/运维确认映射完整。

### B0.4 harness 锁：续聊绝不切换引擎

现状：resolveEngine 用 run.harness（正确），但无一致性校验；DB 手工改动或旧数据可能 harness 与 session 标记不符。
做法：
- `assertSessionHarnessMatch(run)`（新，diagnosis.service.mjs）：session_id 前缀 `omp:` → 必须 omp；`goose:` → 必须 goose；UUID 形态 → 必须 claude；其他（空/未知）→ 放行但标 `session_kind:'unknown'`；
- 不匹配 → 409 `RUN_HARNESS_MISMATCH`，消息明确"run 记录的 harness 与 session 来源不一致，已拒绝切换以避免找不到会话"；
- `sendChatMessage` / `executeDiagnosis`（resume 分支）双处调用；
- API 层：续聊端点**不接受 harness 参数**（现状已如此），显式文档化"harness 由 run 固定，不可覆盖"。

**测试（B0）**：pending→stopped 启动恢复；无 session stopped → 续聊走 Continue 路径成功；session_id 从事件流回补；omp 无事件时按 harness 补标记；三类前缀匹配校验 + 错配 409；session-map 端点字段。

## 4. Phase B — 续聊核心三修（约 0.5-1 人日）

| # | 修复 | 位置 | 做法 |
|---|---|---|---|
| B1 | **Continue 覆写 NULL bug**（对已完成 run 重跑时 completeRun 把 workspace/report/score 覆写为 NULL） | `diagnosis.service.mjs:1115-1155` + `database.mjs:264-270` | completeRun SQL 改 `COALESCE(excluded 列, 既有值)`：新目录/新 score 存在才覆盖，否则保留原值 |
| B2 | **续聊 prompt 锚定 run 上下文**（现状 resume 只发裸消息） | `claude-client.mjs startSessionChat :503-541`、`omp-client.mjs :383-404` | prompt 前置固定一行上下文：`[run 上下文] run_id=<id>；工作区=<abs>；报告=<report_path>。引用结论时以这些文件为准。` 用户消息跟随——用户仍只需打一句话 |
| B3 | **续聊轮次可配**（写死 maxTurns=1，工具类追问做不到） | `diagnosis.service.mjs:703` | `maxTurns = body.maxTurns（1-20 夹取）\|\| 8`；REST 与 WS `run_chat` 通道同参 |
| B4 | **续聊互斥**（现状连发两条互相杀） | `sendChatMessage :672` | 同 run 已有活跃 chat turn → 409 `CHAT_TURN_BUSY`（前端提示等待），替代静默互杀 |

**测试**：backend 新增（COALESCE 行为、resume prompt 含 run_dir 断言、maxTurns 夹取、409 互斥）；真实续聊存证进 Phase E。

## 4. Phase C — 持久化补齐（约 1 人日）

| # | 项 | 做法 |
|---|---|---|
| C1 | **external_tasks 落库** | 新表 `external_tasks(task_id PK, run_id, intent, harness, scene, objective, status, created_at, updated_at)`；`createTask` 双写（DB+内存 Map 作活跃缓存），`refreshTask` 终态回写；`/v1/tasks` 列表改 DB 查询（活跃态从内存合并）；**重启后 task_id 查询返回 DB 行（status 由 run 行重推导）** |
| C2 | **产物统一索引** | `artifact-manifest.service.mjs` 增 `STABILITY_ARTIFACTS`（stability_report.json/charts.json/html/md/selfcheck）与 `SENTINEL_ARTIFACTS`（alert.json/watch_report.md/quick_screen_report.html/baseline）清单 + intent 集合，替换非 DOE intent 的 `applicable:false` 占位；condition 项语义照 DOE 先例 |
| C3 | **wait 终态映射修复** | `getDiagTaskView`（diagnosis.service.mjs:489-496）把 `expired→expired(terminal)`、`awaiting_input→awaiting_input`（wait 循环对后者提示需人工应答而非空转）；external TERMINAL 集合同步 |

**测试**：backend 新增（task 落库+重启重建、stability/sentinel manifest applicable、终态映射表驱动用例）。

## 5. Phase D — 生产加固 Top-6（约 1.5-2 人日）

| # | 风险（调查证据） | 修复 |
|---|---|---|
| D1 | 本体 store 并发 publish 无锁 → 同 scene 并发互覆+丢 entry（`ontology_store.mjs:452,647,716`） | index 读-改-写全程包**仓库内文件锁**（`data/ontology_store/.lock`，`O_EXCL` 自旋+超时+stale 抢占），覆盖 addVersion/reuse/updateEntry/removeVersion |
| D2 | specialist 判定双向失真：report.md 靠 prompt 约定 + findLatestRunDir 任意目录收养竞态（`:1135,:1280`） | ①完成判定按 intent 加**必产物检查**（stability: line_report/stability_report.json+html；sentinel: sentinel/alert.json+quick_screen_report.html；doe 沿用 manifest）②去掉 `latest || fallback` 任意收养，无匹配→run failed（诚实） |
| D3 | 全链路无输入字节上限 + 整文件进内存（fingerprint `readFileSync` 全读再切 2MB；sentinel sha256 整读且×2） | `fingerprintFile` 改流式 64KB 块采样 + 200MB 上限（超限诚实报错）；`load_table_columns` 限读前 2000 行；sentinel `_io.sha256_file` 改流式并复用单次结果 |
| D4 | 崩溃 exit 1 ≡ "有发现/有告警"（sentinel watch / stability analyze 无 catch-all） | 两 main() 加 catch-all → **exit 4（crash）**并 stderr 输出 `CRASH:` 前缀；文档/协议同步 |
| D5 | workspace 无界增长（实测 212 目录/172MB） | config 增 `workspace_retention_days`（默认 90）+ `purge_deleted_after_days`（默认 30）；后端启动时执行一次清理（软删超期→连目录彻底删；超 retention 的 completed run 只清工作区保留 DB 行）；清理动作写日志 |
| D6 | specialist 零事件观测（`.pipeline_events` 仅 run_initialized；`appendPipelineEvent` 死代码；`reuse()` 注释虚构事件） | stability/sentinel 的 prepare→analyze/gate 各接一条最小事件（prepare_done/analysis_done/gate_done）；`ontology_store.reuse()` 的陈旧 docstring 修正或真补事件 |

**测试**：并发 publish 压测（同 scene 双进程 ×20 publish → index 完整、版本不互覆）；大文件上限负例；exit 4 正例；retention 清理用临时目录；事件存在断言。

## 6. Phase E — 验收标准与执行（约 1-1.5 人日）

### 6.1 验收标准（Definition of Done）

**S 会话记录与续聊（用户核心诉求）**

- **S1 记录可回查**：任一 run 完成后（completed）或终止后（stopped），`GET /api/history/runs/:runId` 返回完整 `diagnosis_logs` 与 `diagnosis_event_stream`；重启后端后同一查询结果不变（逐条比对条数与首末内容）。
- **S2 completed 可续聊**：对 completed run 发 `POST /api/diagnosis/chat/:runId {message}` → 200；回复 token 流落库（`diagnosis_logs` 新增 ≥2 行：user + assistant）；run 状态仍为 `completed`（不因续聊改写终态）；断言发送给引擎的 prompt 包含 `run_id`/工作区路径锚点（B2）。
- **S3 stopped 可续聊**：
  - S3a（有 session 的 stopped）：stop 一个 executing run → status=stopped → 续聊走 resume 成功；
  - S3b（无 session 的 stopped，即 B0.1 的 pending→stopped）：续聊**自动走 Continue 全量重建路径**并成功返回（不报错、不 400），且仍使用 run 原 harness。
- **S4 pending 重启语义**：DB 造一条 `status='pending'` 行 → 重启后端 → 该行变为 `stopped` 且 error_message 说明"restarted before execution"；`running` 行仍为 `failed`。
- **S5 sessionId 映射完整**：①有 init 事件的 run session_id 非空；②人为清空某 completed run 的 session_id → 重启 → `reconcileSessionIds` 从事件流回补成功（值与原值一致）；③omp run 无事件时补 `omp:run:<runId>`；④`GET /api/diagnosis/session-map/:runId` 四字段（harness/session_id/session_kind/resumable）与 DB 一致。
- **S6 harness 锁**：①把某 run 的 session_id 改成 `omp:run:x` 而 harness=claude → 续聊返回 409 `RUN_HARNESS_MISMATCH`（不静默切换）；②正常 run 续聊只调用 `run.harness` 对应引擎（测试桩断言 resolveEngine 入参 === run.harness）；③续聊端点带 `harness` 参数不生效（被忽略或 400，按实现文档化）。

**M 会话管理**

- **M1 归属**：普通用户 A 只看到/可改自己的 run；用户 B 的 run 不出现在 A 的列表；admin 可见全部；非 admin 改他人 run → 403。
- **M2 改名**：`PATCH /api/history/runs/:id {title}` → 列表返回新 title（长度 1-200，空白拒绝）。
- **M3 分类**：创建分类 → 归类 run → 按 `category_id` 过滤命中；删除分类 → 该 run `category_id=null` 且 run 本身保留；同用户重名分类 → 409。
- **M4 软删/恢复/彻底删**：软删后默认列表不显示、`include_deleted=true` 可见；恢复后回到默认列表；彻底删后 DB 行消失且**工作区目录一并删除**（断言目录不存在）；软删期间续聊返回 404/410 明确错误。
- **M5 前端**：History 页出现标题编辑、分类下拉/管理、回收站 toggle、继续对话按钮（stopped/completed 均可见）；`npm run build` 通过。

**P 持久化**

- **P1 external task 落库**：非 wait 模式创建 task → 重启后端 → `GET /v1/tasks/:taskId` 返回 200（DB 重建行，status 由 run 推导）；`/v1/tasks` 列表含该 task。
- **P2 产物索引**：stability run 的 `result.artifacts` 含 `line_report/stability_report.json`、`line_report_report.html`、`line_report/stability_report.md`（applicable:true）；sentinel run 含 `alert.json`/`watch_report.md`/`quick_screen_report.html`；缺件时 `missing[]` 明示。
- **P3 wait 终态**：`expired` 与 `awaiting_input` 不再被当作 running 空转（wait 循环对前者立即返回终态、对后者返回 state 提示）。

**R 生产加固**

- **R1 store 并发**：同 scene 双进程并发 publish ×20 → index 完整（20 条或去重后一致）、无版本目录互覆（每版本 ontology.json 内容哈希唯一映射到 index content_sha256）。
- **R2 specialist 完成判定**：stability run 缺 `line_report/stability_report.json` 时不得判 completed（failed + 明确 error）；sentinel 缺 `sentinel/alert.json` 同理；DOE 沿用 manifest。
- **R3 输入上限**：>200MB 数据文件 → 诚实报错（不 OOM）；哨兵 watch 超 100k 行/60 列 → exit 2 明确披露。
- **R4 崩溃语义**：畸形输入触发未捕获异常 → exit 4（stderr 含 `CRASH:`），不再混同 exit 1（findings）。
- **R5 保留策略**：`workspace_retention_days` 生效（构造过期目录 → 启动清理 → 目录消失、DB 行保留；软删超 purge 期限 → 连目录删除）。
- **R6 specialist 事件**：stability/sentinel run 的 `.pipeline_events.jsonl` 至少含 prepare_done/analysis_done/gate_done 三条（按实际实现命名）。

**G 全局回归**

- **G1** 全部套件绿：conformance / preprocessor / doe×3 / stability / sentinel / backend npm test（含新增）。
- **G2** 三镜像 `sync-harness-skills --check` exit 0（静态时点）。
- **G3** 真实 harness 续聊存证：对既有 `202610220224192_lsr_demo`（claude/completed）发一条追问，回复内容引用报告事实（人工+日志双证）。

### 6.2 执行

- **E1 前后端交互 E2E**（API 级 + 真实 claude harness）：S2/S3a/S3b/S5/M1-M4/P1-P3 全部脚本化探针；前端 `npm run build`。
- **E2 重启存活**：重启 3211 → S4/S5②/P1 复验。
- **E3 并发资产安全**：R1 压测脚本。
- **E4 全套件回归** + 镜像 check（静态时点）。

## 7. 排期与风险

| Phase | 人日 | 风险 |
|---|---|---|
| A 会话管理 | 1.5 | runs 加 user_id 动既有测试的 INSERT 断言 → 同步修 |
| B 续聊三修 | 0.5-1 | COALESCE 改动波及所有 run 完成路径 → 全 harness mock 回归 |
| C 持久化 | 1 | task 双写一致性 → DB 为准、内存为缓存 |
| D 生产加固 | 1.5-2 | store 锁的死锁/性能 → 自旋上限+stale 抢占；必产物检查误伤部分完成 run → condition 语义 |
| E 验收 | 0.5-1 | — |
| **合计** | **5-6** | — |

## 8. 明确不做（本轮）

- 7 个不可 resume 引擎的 transcript 回放兜底（维持 400+Continue 提示）。
- runs 多级目录/标签树（单层分类 + 筛选已覆盖需求）。
- 前端 Playwright 浏览器级自动化（UI 验收 = 构建 + API 断言 + 手工一遍）。
- watch 常驻进程化（维持批式）。

## 9. 实施记录（2026-10-22）

### 9.1 改动清单（按 Phase）

| Phase | 文件 | 要点 |
|---|---|---|
| B0.1 | `app/backend/src/index.mjs`, `db/database.mjs`, `services/session-integrity.service.mjs` | 启动恢复：`pending → stopped`（error 注明 before execution）、`running → failed`（保留） |
| B0.2 | `services/diagnosis.service.mjs`（sendChatMessage） | 无 session 的终态 run 续聊自动委托 Continue 全量重建（同 harness/intent/data） |
| B0.3 | `services/session-integrity.service.mjs` | `reconcileSessionIds()`：事件流 init payload → omp 会话目录 → omp 确定性标记；`GET /api/diagnosis/session-map/:runId` 审计端点 |
| B0.4 | 同上 + `diagnosis.service.mjs` | `sessionKind()` + `assertSessionHarnessMatch()`：omp:/goose:/UUID 前缀与 run.harness 必须一致，错配 409 `RUN_HARNESS_MISMATCH`；chat/continue 双处调用 |
| B1 | `db/database.mjs` | `completeRun` 改 COALESCE：续跑不再把 workspace/report/score 覆写为 NULL |
| B2（已被 2026-10-22 后续要求取代） | `diagnosis.service.mjs` | ~~续聊 prompt 锚点~~ → **续聊原样透传**：直接以当前 harness 的 sessionId 发送用户原文，不注入任何额外提示词/路径；`CHAT_TURN_PASSTHROUGH` 常量钉住契约 |
| B3 | `clampChatTurns` | 续聊轮次默认 8、范围 1-20（原写死 1） |
| B4 | `diagnosis.service.mjs` | `activeChatTurns` 互斥：同 run 并发续聊 409 `CHAT_TURN_BUSY` |
| A | `db` migrations + `history.service.mjs` + `history.routes.mjs` | runs 加 user_id/title/deleted_at/category_id；`run_categories` 表；PATCH 改名/归类、软删/恢复/purge、分类 CRUD、筛选分页；遗留无归属行对所有用户可见 |
| A(front) | `app/frontend`（子代理） | History：搜索/状态/分类筛选、回收站 toggle、标题 inline 编辑、行内归类、分类管理面板、软删/恢复/彻底删、继续对话按钮；api + i18n；构建通过 |
| C1 | `external.service.mjs` + `external_tasks` 表 | task_id↔run_id 落库，重启后 `hydrateTask` 由 run 行重推导状态；`/v1/tasks` 以 DB 为主叠加活跃缓存 |
| C2 | `artifact-manifest.service.mjs` | 新增 `STABILITY_ARTIFACTS` / `SENTINEL_ARTIFACTS` 清单（applicable:true + 必产物 missing） |
| C3 | `diagnosis.service.mjs` `getDiagTaskView` | `expired` / `awaiting_input` 不再伪装 running；external 终态集合同步 |
| D1 | `ontology_store.mjs`（子代理） | `withStoreLock` 文件锁（wx 抢占 + 50ms 重试 + stale 抢占），全部写路径入锁；并发 publish ×20 测试 |
| D2 | `diagnosis.service.mjs` | 完成判定按 intent 校验必产物（stability: report.json + html；sentinel: alert.json + html；mock 豁免）；`findLatestRunDir` 去掉任意目录收养，歧义时拒绝并告警 |
| D3 | `ontology_store.mjs`, `ontology_prepare_common.py`, `sentinelcore/_io.py`, `sentinel.py`（子代理） | 流式指纹 + 200MB 上限、探测只读 2000 行、sha256 流式且单次、watch 行数 >100k exit 2、参数列 >60 截断披露 |
| D4 | `sentinel.py`, `stability_analyzer.py`（子代理） | 顶层 catch-all → stderr `CRASH:` + exit 4（与 findings 的 exit 1 区分） |
| D5 | `retention.service.mjs` + `config/default.yaml` | `retention_days`(90) / `purge_deleted_after_days`(30)；启动时过期工作区清理、软删超期 purge、孤儿目录清扫 |
| D6 | `stability_analyzer.py` / `report_builder.py` / `sentinel.py` / `sentinel_ontology_prepare.py`（子代理） | specialist 最小事件集 prepare_done/analysis_done/gate_done |

### 9.2 验收证据

**单元/套件**

| 套件 | 结果 |
|---|---|
| shared conformance（指纹对拍/命名空间/裁剪/词典） | 9/9 |
| shared store lock（并发 publish ×20） | 1/1 OK |
| preprocessor | 89/89 |
| doe main / ontology / aws_capture | 199/199 · 69/69 · 46/46 |
| stability（含 S19-S23） | 173/173 |
| sentinel（含 F9-F13） | 183/183 |
| backend npm test（含 session-management 10 例） | 174/174 |
| 前端 build | 通过 |

**E2E（`scripts/e2e/session-management-e2e.mjs`，3211 实例，两阶段跨重启）**

Stage A 14/14 PASS：task 创建、分类创建/重名 409、改名/空白拒绝、归类 + category 过滤、软删/默认隐藏/include_deleted/恢复、harness 错配 409、无 session 续聊接受、session-map 形状。

Stage B 9/9 PASS（重启后）：`pending→stopped`（启动日志 `Pending runs marked stopped: e2e-pend-…`）、session 从事件流回补（`Reconciled 1 session id(s): …<-event_stream`）、task 重启后可查（status=completed）且仍在列表、purge 后 404、删分类后 run 保留且 category 清空、stability 产物清单 applicable:true（kinds 含 stability_report/html/md）。

**真实续聊存证（claude，run b5c9236a / stability-report / completed）**

- session-map：`{harness:"claude", session_id:"6b5c16a9-…", session_kind:"claude", resumable:true, harness_matches_session:true}`；
- `POST /api/diagnosis/chat/b5c9236a {message, maxTurns:8}` → 200 resumed；
- 日志 131 → 133（user + assistant），run 状态保持 `completed`；
- 回复内容引用了报告真实数字（评分 65.8/C、Cpk 0.7902、Ppk 0.2121、漂移 -0.502%/天、首次跌破 2026-10-09 06:35）并注明依据 `line_report/stability_report.json` —— 证明 session 真 resume + B2 锚点生效。

### 9.3 已知边界

- claude 以外不可 resume 的引擎（gemini/copilot/cursor/crush/pi/acp 族/codex/opencode）续聊仍返回 400 并提示用 Continue（本轮范围外，已文档化）。
- 遗留无归属（user_id IS NULL）run 对所有认证用户可见可管；新 run 按创建者隔离，admin 可见全部。
- retention 在启动时执行一次；无后台定时任务（按计划）。
- `workspace_removed:false` 在 purge 夹具上出现，是因为该夹具 run 无 workspace_path（DB 直插的测试行），真实 run 的 purge 会删目录（M4 语义由 removeWorkspaceDir 路径白名单保证）。

### 9.4 终回归（2026-10-22 收尾）

全套件复跑：shared conformance OK · store lock OK · preprocessor 89（ALL TESTS PASSED）· doe 199/199 + 69/69 + 46/46 · stability 173/173 · sentinel 183/183 · backend 174/174 · 前端构建通过 · 三镜像 `--check` exit 0。

## 10. 续聊/状态管理专项复测（2026-10-22 第二批次）

### 10.1 需求修订：续聊不做任何提示词注入

用户明确要求：续聊必须“直接以当前诊断对话所用 harness 的 sessionId 发送聊天、渲染结果，没有额外的提示词注入”。因此 §3 的 B2 run 锚点被**移除**，契约改为 `CHAT_TURN_PASSTHROUGH`：`sendChatMessage` 与 `continueDiagnosis` 的 resume 分支原样发送用户消息（Continue 无消息时发 `null`，由引擎按空 follow-up 处理；重建分支沿用引擎自身的完整 prompt 构建）。

### 10.2 复测发现并修复的三个真实缺陷

| # | 缺陷（现象） | 根因 | 修复 |
|---|---|---|---|
| 1 | 完成态 run 续聊时，助手回复**不实时渲染**，刷新后才出现 | `diagnosis-engine.subscribe()` 在 run 引擎条目已被 `closeRun` 清理后**静默返回空订阅**；随后聊天轮 `createRun` 重建条目时，先前建立的 WS 订阅已不存在 | `subscribe()` 对缺失条目先 `createRun()` 再注册 |
| 2 | 同上（第二个根因）：即使订阅存在，前端仍丢弃回复 | 重建条目的 `nextSeq` 从 0 开始，live 事件的 `_seq` 与 DB 历史序号冲突；前端 `appendEvent` 对 `seq <= lastEventSeq` 直接丢弃 | `createRun()` 从 `diagnosis_event_stream` 的 `MAX(seq)+1` 续号（新增 `stmts.getMaxEventSeq`） |
| 3 | 历史 run 的助手气泡标签错误（claude run 显示 OMP Engine） | `runEngineLabel` 用“启动时选择的引擎”，打开历史 run 时未改用 run 自身 `harness` | 打开历史运行时优先 `run.harness` |
| 4 | 单元测试导入引擎模块会挂起 | 引擎清理定时器未 `unref()` | `cleanupTimer.unref()` |

### 10.3 验收证据

**脚本化（可重复）**

- `scripts/e2e/intent-prompt-contract.mjs`：13/13 PASS——默认模式不注入意图指令；stability/quick-screen/doe/experience/optimizer 各自注入自己的 skill 与运行约束；stability 带 `data_preprocessor.py`、quick-screen 带 `build_screen_report.py` 且互不串。
- `scripts/e2e/continue-chat-state-e2e.mjs`（before→重启→after，20 项全 PASS）：
  - **透传实证**：mock 回显 `"(mock) 已收到消息: 透传校验-xxxx"` 与用户原文**逐字相等**，日志中用户消息亦为原文；
  - completed run 续聊 → 200 + 助手回复 + 状态保持 completed；
  - 运行中捕获 session → stop → status stopped → 续聊 200 + 助手回复 + 状态保持 stopped；
  - 重启后：pending→stopped（可续，重建路径成功）、running→failed、stopped+session 映射仍可续。
- `scripts/e2e/ws-live-chat-e2e.mjs`：5/5 PASS——已关闭的 completed run 可订阅；chat POST 后 **WS 实时收到 assistant 消息**；用户消息事件逐字一致（无注入）。

**UI（浏览器实测）**

`lsr_demo_b5c9236a`（claude/stability-report/completed）从 History「继续对话」打开 → 输入“联验-gn5s：只回答两个字‘收到’” → 界面依次渲染：原文用户消息 → “会话消息已发送 · 已发送到当前 CLAUDE session” → 助手气泡（头像 C / **CLAUDE**）→ **“收到”** → 1 轮次 / 6.0s。全程无刷新、无提示词前缀。

后端套件 176/176（新增 subscribe/序号连续性两个引擎级回归用例）。
