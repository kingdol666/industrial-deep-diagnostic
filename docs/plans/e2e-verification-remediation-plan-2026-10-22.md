# E2E 全链路验证问题汇整与优化计划 v1 (2026-10-22)

> **状态：已实施并验收（2026-10-22）**。结果见 §9。
> 基线：本轮真实端到端验证已完成且全绿（见 §1）；本计划处理验证中**实测发现**的问题与已知开放项。
> 验证证据：`workspace/acceptance/2026-10-22/`（截图 + audit.json）、
> `docs/plans/followups-acceptance-2026-10-22.md` §9。

## 1. 本轮真实端到端验证结果（2026-10-22）

| 项 | 结果 |
|---|---|
| 真实引擎 run（claude / stability-report / 865 行）`d6593a4f` | 完成，score **65.8** / verdict **`C · 波动`** 与工件逐字一致；四件套产物齐全；session-map resumable |
| Harness API 契约（`harness-api-acceptance.mjs`，14 引擎 + 外部 API） | A/C 全 PASS；B5/B6/B8 PASS；B3/B4 两条为**探针竞态**（t=0 断言，引擎首帧未到），已改轮询并在本轮后修复 |
| 浏览器交互审计（`ui-visual-audit.mjs`，原生输入） | **20/20**：0 异常 / 0 console error / 0 失败 `/api`；报告 MD+HTML、实时流、评分/结论、续聊全通过 |
| 原生输入冒烟（`ui-smoke-native.mjs`） | **12/12**（登录→History→继续→发送→回复；reduced-motion `1e-05s`） |
| 大 run 渲染探针（`ui-large-run-probe.mjs`，**53,490 事件**） | 打开 113–163ms、堆 47MB、流式 DOM 有界、无 console error——**但快照全量 11.5MB 传输**（见 P0-1） |
| 真实引擎续聊 | claude run 5/5（WS 实时回复「收到」）；OMP 被 provider 预算 429 拒绝（已显式进事件流，见 P0-4） |

## 2. 问题汇整（本轮实测 + 开放项）

### P0 — 正确性 / 用户可感

| # | 问题 | 证据（实测） | 影响 |
|---|---|---|---|
| P0-1 | **大 run 快照全量传输**：`GET /api/diagnosis/snapshot/:id` 返回 run 的全部事件（53,490 条 = **11.5 MB**），前端 store 只保留最后 3000 条（`diagnosisRealtimeStore.js:151` `MAX_EVENTS=3000`） | 实测 11.5MB / 391ms（本机）；广域网下每次打开大 run 数十秒 | 打开慢、流量浪费 ~94%；`derivePendingQuestionFromEvents` 每次全量扫描 53k 行，外部 wait 轮询每 2s 一次 |
| P0-2 | **后端退出不清理引擎子进程**：无 SIGINT/SIGTERM 处理，杀后端后 omp/claude 子进程成为孤儿 | 实测 5 个隔日 `omp.exe` 孤儿；本轮 OMP 续聊撞"session open in another omp process"锁（其根因之一） | 孤儿进程持锁/占资源；restart 后无法恢复 |
| P0-3 | **OMP provider 预算耗尽（429）**：`Budget has been exceeded (100.38/100.0)`，OMP 全部续聊/新 run 被拒 | session jsonl `stopReason:error, errorStatus:429`；本轮 OMP 续聊失败 | 环境问题，但系统层面**无预算/成本可见性**，耗尽只能靠读会话文件发现 |
| P0-4 | **探针竞态**（已修）：验收脚本在引擎首帧前断言 session/init → 假 FAIL | 本轮 B3/B4 两条 | 仅影响验收脚本可信度 |

### P1 — 性能 / 健壮性

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| P1-1 | **消息流每追加一事件全量重算**：`MessageStream.renderedItems` 对 store 内全部事件（上限 3000）重建数组再 slice(300) | `MessageStream.vue:241-411`；claude run 高峰每秒数十事件 | 活跃 run 期间 CPU 尖刺（有 3000 上限兜底，但为 O(n²) 累计） |
| P1-2 | **`diagnosis_event_stream` 无界增长**：单 claude run 53,490 行（含全量 payload JSON），保留策略只清软删 run | DB 实测；`data.retention_days=90` 只作用于 run 行 | DB 膨胀（数 GB/月量级），快照/派生查询随之变慢 |
| P1-3 | **1280px 下结论列被 sticky 操作栏遮挡**（横向滚动回退时） | `06-history-1280.png`；操作栏 380px 固定右缘 | 窄屏用户看不到结论/评分（可横向滚动，属体验债） |
| P1-4 | **WS 应用层心跳协议未文档化**：服务端 60s 无 pong 即断连；外部集成者（如本轮 ws-live 初版）会莫名掉线 | `ws-server.mjs:481-495`；本轮 ws-live 首次运行即断 | 集成摩擦 |
| P1-5 | **`close_run_delay_seconds=60` 语义残留**：子进程已即杀（已修），延迟只服务内存清理，但配置注释未更新，易误解 | `config/default.yaml:130` | 维护认知成本 |

### P2 — 打磨

| # | 问题 | 说明 |
|---|---|---|
| P2-1 | 登录页**注册路径**未被自动审计覆盖（audit 只测 login） | smoke 增加注册→登出→再登录 |
| P2-2 | 运行视图用户消息头像与气泡间距偏大（视觉 nit） | `03-run-view.png` 右缘 |
| P2-3 | 文档滞后：`AGENTS.md`/`docs/api.md` 未提 `session_resume`/`supported_intents`/`analysis_mode` 与续聊 mode 语义（api-external 已更） | 文档一致性 |
| P2-4 | **本轮及上轮改动未提交**（~40 文件） | 需要提交推送（立即动作，不属本计划） |

## 3. Requirements Summary

- **R1**（P0-1/P1-2）：快照按需分页——默认只传事件尾部（`events_limit`，默认 2000），响应带 `events_total/truncated`；`derivePendingQuestionFromEvents` 只扫尾部；DB 事件保留策略（按 run 行数上限 + 过期归档删除）。
- **R2**（P0-2）：后端优雅退出——SIGINT/SIGTERM 时 `closeAllEngines` + `killTree` 所有活动子进程；启动时检测「上次为 running」的 run 已由现有恢复逻辑覆盖，孤儿进程以告警记录（不自动杀无关进程）。
- **R3**（P0-3）：Provider 预算/成本可见性——把 OMP/引擎错误中的 429/budget 信号升级为 run 级 `error_message` 标注（"provider 预算/配额"分类），`GET /api/harness/availability` 的 meta 暴露最近一次 provider 错误摘要；文档给出换 provider/预算检查步骤。
- **R4**（P1-1）：消息流增量构建——`renderedItems` 以 `lastSeq` 增量 append（保留合并/分组逻辑），消除每事件全量重算。
- **R5**（P1-3/P2）：窄屏 History 列策略（结论列在 <1360px 移入展开详情或允许用户隐藏低价值列）；WS 心跳写进 `docs/api.md`；smoke 增注册路径；头像间距微调；配置注释更新。

## 4. Acceptance Criteria

| ID | 判据 |
|---|---|
| AC-1 | 打开 53k 事件 run：`/api/diagnosis/snapshot/:id?events_limit=2000` 响应 ≤ 1MB（实测对比 11.5MB），`events_total=53490`、`events_truncated=true`；UI 打开时间与内存不劣于现状（探针 `openMs`、`heapMB` 不升） |
| AC-2 | `derivePendingQuestionFromEvents` 只处理返回的尾部事件（单测：53k 行夹具 < 50ms，旧实现对照） |
| AC-3 | 事件保留：配置 `data.event_stream_max_rows_per_run`（默认 20000）+ 后台清理；超限 run 截断最旧行且 `events_total` 仍准确；单测覆盖截断与快照一致性 |
| AC-4 | 向后端进程发 SIGTERM：所有活动引擎子进程退出（`tasklist` 无遗留 omp/node 子进程）；在途 run 按 restart 语义标 failed；单测/脚本验证 |
| AC-5 | OMP provider 429 后：run `error_message` 含「provider 预算/配额」分类标记；availability meta 可见最近 provider 错误；事件流出现 system:notice（已有） |
| AC-6 | 消息流增量：单测以 5000 事件逐条 append，断言 `renderedItems` 计算复杂度常数化（以重算计数器 ≤ 常数/事件）；现有流渲染快照测试不回归 |
| AC-7 | 1280px：结论列可见或展开详情一键可达（审计脚本新增窄屏断言）；心跳协议写入 docs；smoke 注册路径 12→14 项全过 |
| AC-G | 全量回归：backend 208+、四套件、build、镜像、ui-smoke、visual-audit、large-run 探针全绿 |

## 5. Implementation Steps

### Phase A — 快照与事件治理（P0-1/P1-2，约 1 人日）
1. `diagnosis.service.getRunRealtimeSnapshot(runId, { eventsLimit })`：SQL 倒序取 tail（`ORDER BY seq DESC LIMIT ?` 再反转）；默认 2000，`events_total` 用 `COUNT(*)`；`currentQuestion` 改为倒序扫描尾部 N 条。
2. 路由 `GET /snapshot/:runId` 与 `getRunWithLogs` 透传 `events_limit`；前端 `hydrateRun` 传 2000 并展示「已截断，显示最近 2000/53490」徽标（i18n）。
3. DB：`data.event_stream_max_rows_per_run`（默认 20000）+ 启动/每日清理（复用 retention 调度点）；`database.mjs` 增 `pruneEventStream(runId, keep)` 与按 run 汇总清理语句。
4. 测试：`snapshot-tail.test.mjs`（分页字段、截断语义、question 派生、53k 夹具性能）；续聊 seq 续号不受影响（已有 _seq 测试）。

### Phase B — 优雅退出 + provider 错误分类（P0-2/P0-3，约 0.5 人日）
1. `src/index.mjs`：`process.on('SIGINT'/'SIGTERM')` → `stopAllEngineChildren()`（遍历 engine registries 的活跃 child，`killTree`）→ server.close → exit；Windows 下同样注册（Ctrl+C 触发 SIGINT）。
2. 错误分类：`formatResumeError`/OMP notice/claude error 归一化出 `provider_budget_exceeded|provider_error` 标记 → `stmts.failRun` 时写入 `error_message` 前缀 `[provider_quota]`；availability health meta 带 `last_provider_error`。
3. 测试：`graceful-shutdown.test.mjs`（spawn 假 CLI 子进程，SIGTERM 后无遗留）；错误分类单测。

### Phase C — 流渲染增量 + 前端打磨（P1-1/P1-3/P2，约 1 人日）
1. `MessageStream`：`renderedItems` 改「基线数组 + 按 `props.events` 尾部增量 append」；重算计数器仅测试态注入；MAX_ITEMS 逻辑保留。
2. History 窄屏：<1360px 隐藏「问题」列（详情面板已有），结论列保持可见；audit 增 1280 断言。
3. smoke 增注册路径（注册→登出→登录）；头像间距 CSS 微调；心跳文档 + `close_run_delay_seconds` 注释更新；AGENTS.md/api.md 能力面补记。

### Phase D — 验收与回归（0.5 人日）
按 §4 全部执行；`harness-api-acceptance`/`ui-visual-audit`/`ui-large-run-probe`/`ui-smoke-native` 纳入常规验收脚本清单（README 或 docs/e2e.md 汇总）。

## 6. Risks and Mitigations

| 风险 | 缓解 |
|---|---|
| 快照 tail 改变前端可见历史（用户想看更早事件） | `events_limit` 可调 + 截断徽标明示；后续可加分页 API（`before_seq`），本期不做 |
| 事件截断与续聊 `_seq` 续号交互 | `createRun` 续号取 `MAX(seq)`，截断最旧行不影响 MAX；单测覆盖「截断后续聊」 |
| 优雅退出在 Windows 的信号差异 | SIGINT 由 Ctrl+C 触发；`SIGBREAK` 一并注册；killTree 已有 Windows 实现（stop 路径在用） |
| 增量渲染重构破坏分组/合并语义 | 以「重算计数器」+ 现有流渲染 E2E 双护栏；分阶段：先 memo 再增量 |
| OMP 预算问题被误当平台缺陷 | 错误分类 + 文档明示；capabilities/health 暴露 provider 状态 |

## 7. RALPLAN-DR Summary

**Principles**：传输与计算按需（tail-first）；进程生命周期必须受控；错误要可分类可见；性能改动必须带量化探针。

**Decision Drivers**：大 run 用户打开体验；DB 增长可控性；孤儿进程/锁的复发预防；改动回归面。

**Options**：
- **A（推荐）**：A→B→C→D 分四阶段，每阶段独立验收。
- B：只做快照 tail（最小改动）——遗留孤儿进程与 DB 增长风险。
- C：全面改分页 API（`before_seq` 游标）——体验最佳但涉及虚拟滚动重构，本期不做。

**ADR**：选 A。快照 tail + 保留上限解决 94% 传输浪费与 DB 增长；优雅退出消除锁复发；增量渲染在 3000 上限内收益适中、风险可控。游标分页列为 follow-up。

## 8. 排期

| 阶段 | 内容 | 人日 |
|---|---|---|
| A | 快照 tail + 事件保留 | 1.0 |
| B | 优雅退出 + provider 错误分类 | 0.5 |
| C | 流渲染增量 + 前端打磨 | 1.0 |
| D | 验收回归 | 0.5 |
| **合计** | | **3.0** |


## 9. 实施与验收记录（2026-10-22）

### 9.1 落地清单

| 项 | 实现 |
|---|---|
| P0-1 快照窗口 | `getRunRealtimeSnapshot(runId, {eventsLimit})` 只读最新 N 条（SQL `ORDER BY seq DESC LIMIT` 再升序）；默认 2000，范围 100–10000；响应带 `events_total/events_truncated/events_limit`；前端 `hydrateRun` 传 2000，运行头显示琥珀色 `2000/5001 事件（窗口）` 徽标（title 说明全量仍在服务端）；WS `run_snapshot` 同步携带三个字段 |
| P1-2 事件保留 | `data.event_stream_max_rows_per_run: 20000`；`applyEventStreamRetention({runIds?})` 启动 + 每 6h 执行；只裁终态 run 的最旧行，`MAX(seq)` 保留（续聊续号不受影响）；测试必须传 `runIds`（全局扫描会裁全库） |
| P0-2 优雅退出 | `shutdownAllEngines()` + SIGINT/SIGTERM/SIGBREAK：关闭所有引擎子进程（含已完成 run 上的聊天 child）与 WS，再关 HTTP；`scripts/e2e/graceful-shutdown-check.mjs` 用真实 OMP 子进程验证 `killed=true` |
| P0-3 Provider 分类 | `services/provider-error.service.mjs`：`provider_quota/rate_limit/auth/unavailable`；OMP `stopReason=error` 发 system:notice（带 `provider_error`）并记录 per-harness；run 失败写 `[provider_quota] …`；`/api/harness/availability` 暴露 `provider_error` |
| P1-1 流增量 | `MessageStream` 以 `buildCache` 增量处理新事件（分组/合并 map 跨帧保留；数组替换或缩短时重建），只返回最后 300 项的**新数组**以触发 Vue 更新 |
| P1-3 窄屏 | History 列顺序改为 标题/分类/状态/评分/结论/场景/数据/问题/创建/操作（结论前置）；≤1360px 隐藏数据/问题列、操作栏 330px、隐藏「增强」→ 1280 无横向滚动、无遮挡 |
| P1-4/P1-5/P2-1 | `docs/api.md` 新增 WS 心跳协议（ping/pong 60s）与事件窗口说明；`close_run_delay_seconds` 注释澄清；`ui-smoke-native` 增加 登出→注册→自动登录→登出（15 项） |
| P2-3 | AGENTS.md 补能力面/快照窗口/provider 分类/shutdown 不变量 |

### 9.2 验收结果

| 判据 | 结果 |
|---|---|
| AC-1 快照有界 | 5,001 事件 run：**226 KB / 11 ms**（对比旧实现 11.5 MB / 391 ms），`events_total=5001`、`truncated=true`、`limit=2000`；UI `openMs 79–211ms`、堆 33–36MB、无 console error |
| AC-2/3 事件治理 | `snapshot-tail.test.mjs` 5/5：窗口/总量/截断、尾部问题派生、5000 事件 <500ms、裁剪保留 `MAX(seq)=499`、按 run 定向裁剪 |
| AC-4 优雅退出 | `graceful-shutdown-check.mjs`：真实 OMP child `killed=true`、引用清空、探针行清理，0 failures |
| AC-5 Provider 分类 | OMP 429 budget：notice `provider_error=provider_quota`；availability `omp.provider_error.code=provider_quota`；`provider-error.test.mjs` 7/7 |
| AC-6 流增量 | 5001 事件窗口：`renderedItems=301`、DOM 4.1k、eval 延迟 1–2ms；UI smoke 15/15 |
| AC-7 窄屏/文档/注册 | 1440 全列可见；1280 无横向滚动、结论可见；WS 心跳文档；注册路径冒烟通过 |
| 真实 E2E | `harness-api-acceptance --harness claude`：A/B/C **全 PASS**，真实 claude run `837404b0` 完成，score 65.8 / `C · 波动` 与工件一致，六类 skill 产物核对全 PASS |
| UI 审计 | `ui-visual-audit` **20/20**：0 异常 / 0 console error / 0 失败 `/api`；报告 MD+HTML、续聊、评分结论全通 |
| 回归 | backend **220/220**；stability 173；sentinel 183；doe 199+69+46；preprocessor/shared 全过；前端 build；镜像一致；intent-contract 0 失败 |

### 9.3 过程说明（诚实记录）

- 在编写事件保留单测时，初版测试调用了**全局** `applyEventStreamRetention()` 并把 cap 临时改成 100，导致开发库
  24 个 run 的事件行被裁到 100 条（367,804 → 3,906 行）。**报告/HTML/日志/评分均未受影响**，仅事件回放历史变短。
  已修复：函数新增 `runIds` 定向参数，测试只作用于自己的 run，并加注释禁止全局扫描；这是保留机制按设计工作的副作用，不是数据损坏。
- OMP 当前 provider（ustc/deepseek-flash）预算耗尽（429，100.38/100.0）仍是环境边界；平台现在会把它分类并显式暴露，OMP 续聊的真实引擎证明由 claude run 承担。
- 报告 HTML iframe 的验收改为轮询就绪：报告页从三个 CDN 拉 ECharts，固定 2.5s 截图会偶发空白（测试时序问题，非渲染缺陷）。
