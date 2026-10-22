# 续聊/评分/引擎覆盖/前端可测试性 — 后续优化计划 v2 (2026-10-22)

> **状态：已实施并验收（2026-10-22）**。v1 评审发现 4 处会导致「测试绿但问题未修」的缺陷，v2 已修正并全部落地；验收记录见 §9。
> 代码基线：`03168f5`（已推送 `origin/feat/doe-ontology-first`）。
> 存储位置：仓库惯例 `docs/plans/`。

## 0.5 计划评审结论（v1 → v2）

对 v1 的每一条 file:line 锚点与真实工件做了复核。**结论：方向正确，但有 4 处必须修正，否则验收会假通过。**

| # | v1 的问题 | 证据 | v2 修正 |
|---|---|---|---|
| R-1 | P0-A 的 DOE 分支读 `conclusions/doe_conclusion.json` 的 `score/verdict`，**该文件没有这两个键** | 真实工件只有 `evidence_grade:"A"`、`design_type:"rsm_ccd"`、`key_findings` | 用 `evidence_grade · design_type` 作 verdict；score 保持 null（不伪造分数） |
| R-2 | P0-A 只在**完成写入时**提取，AC-1a 却指向一个**已经完成**的 run（`46833919`，DB 中 score=null）——按 v1 实现 AC-1a 永远失败，只能重跑真实分析才能验收 | `SELECT score FROM diagnostic_runs WHERE run_id='46833919'` → null；工件 `conclusion.score=65.8` | 增加**读取时派生**：终态 specialist run 的 score/verdict 为空时从自身工件派生（历史 run 与崩溃遗留 run 一并修复），写入时仍照常落库 |
| R-3 | P0-B 的 AC-2b 要求「claude session 丢失 → 409」，与 R2「任意 harness 一键继续」及现有 no-session 重建语义冲突 | `sendChatMessage` 已有 no-session 重建分支；`continueDiagnosis` 支持任意非 pending 状态重建 | 统一为**可重建就重建**（带系统条说明原因）；`409 RESUME_UNSUPPORTED` 只用于「连重建上下文都没有」（无 data_path/data_folder）。404 只表示 run 不存在 |
| R-4 | P1 的「能力矩阵 400」在修完 codex/opencode 后没有真实触发组合；更严重的是**现有 `capabilities:['chat']` 对 11/14 引擎是假的** | `base.mjs` 定义 `chat = can resume conversations`；`HARNESS_DEFS` 每个引擎都写 `['live','chat']` | `chat` 能力改由 `RESUMABLE` 单一事实源生成（claude/omp/goose/mock）；新增 `supported_intents` 暴露；400 守卫保留并由单测注入一个受限引擎验证 |
| R-5 | v1 说「completed 视图每秒重渲染」，实际 watcher 已在非 running/awaiting 时停止计时 | `DiagnosisView.vue:808-810` | 收紧为仅 `isRunning`；不再声称存在该缺陷 |
| R-6 | v1 漏掉前端 **verdict 徽章把所有非 PASS/ENDORSED 判红**，稳定性 `A · 稳定` 也会显示红色 | `HistoryList.vue:637-641` | 增加等级感知配色 + 长文本 title/省略 |
| R-7 | v1 的「HistoryList 分类共享 computed」不是主要重渲染源（`categories` 已是 ref） | `HistoryList.vue:347` | 不做无效重构；改为补稳定测试锚点 + reduced-motion |

**v1 中成立且保留的部分**：五项问题的定性、P0→P1→P2 的选项 A 排序、冻结契约只增不改、mock 不产工件属设计而非缺陷。

## 1. Requirements Summary

- **R1**（用户可见）：specialist run 完成后，run 级 `score` / `judge_verdict` 与其报告工件一致；History/外部 API 不再对已有工件的 run 显示 `--`。
- **R2**（覆盖）：任意 harness 的 run 都能"一键继续对话"——能 resume 的走原 session，不能的走同 harness/intent/data 的受控重建；HTTP 语义不再用 404 冒充。
- **R3**（正确性）：codex/opencode 选择 specialist intent 时注入对应意图指令；引擎能力表（chat / supported_intents）与实际行为一致。
- **R4**（诚实标注）：mock run 在外部结果/任务条目中带 `analysis_mode:"mock"`。
- **R5**（可测试性）：交互元素有稳定测试锚点、尊重 reduced-motion、原生输入可完成登录→历史→续聊冒烟。

## 2. Acceptance Criteria

| ID | 判据（命令/断言） |
|---|---|
| AC-1a | 对历史稳定性 run `46833919` 调用 `GET /api/history/runs/46833919` → `score == 65.8`、`judge_verdict == "C · 波动"`（读取时从 `line_report/stability_report.json` 派生）；History 行渲染 65.8 与徽章。 |
| AC-1b | 对哨兵 run `46894aff` → `judge_verdict` 含 `alert` 与告警条数（`alert · N alerts`），`score` 为 null；History 结论列显示该文本。 |
| AC-1c | deep-diagnosis 行为逐字节不变：仍只认 `Judge Score:`；既有 96/ENDORSED run 回归通过；后端全套件绿。 |
| AC-1d | DOE run `2a7ef23f` → `judge_verdict == "A · rsm_ccd"`；experience run `c2ef3526` → `playbook_hit · 1 playbook`；optimizer run `a3cd1d7f` → `exploiting · round 2`；三者 score 均为 null。 |
| AC-2a | 非 resume 引擎（以 mock 之外的单测桩 + 可用的 codex/gemini 现场验证）发 `POST /api/diagnosis/chat/:runId` → 200 `{mode:"rebuild"}`，emit 系统条"已按当前上下文重建"，**不调用** `startSessionChat`。 |
| AC-2b | 有重建上下文时 resume 失败 → 200 rebuild + 说明条；**无任何数据上下文**时才 409 `RESUME_UNSUPPORTED`（含 harness / run_id / 建议）。404 仅用于 run 不存在。 |
| AC-2c | claude/omp/goose 的既有 resume 行为不变（`session-map.resumable=true`；`ws-live-chat-e2e` 5/5）。 |
| AC-2d | `HARNESS_DEFS` 中 `chat` 能力 ↔ `engineSupportsSessionChat` 一致（claude/omp/goose/mock=true，其余 false）；`/api/external/v1/capabilities` 暴露 `session_resume`。 |
| AC-3a | `scripts/e2e/intent-prompt-contract.mjs`：codex/opencode 的 prompt builder 输出含 `ANALYSIS_INTENT: <intent>`、对应 skill 与步骤；deep-diagnosis 不追加。 |
| AC-3b | `supported_intents` 在 capabilities 暴露；守卫对「显式声明不支持」的组合返回 400 `INTENT_UNSUPPORTED_ON_HARNESS`（单测注入受限矩阵）；修复后所有 live 引擎 × 6 intents 均 supported。 |
| AC-4 | mock run 的 `GET /api/external/v1/analyze/:runId` → `analysis_mode == "mock"`；任务条目同字段；非 mock 为 `"real"`。 |
| AC-5a | 新增 `scripts/e2e/ui-smoke-native.mjs`：仅用 CDP `Input.*` 原生事件（无 `element.click()`/JS 点击兜底）完成 登录 → History → 继续对话 → 发送 → 收到回复。 |
| AC-5b | 登录/导航/历史行/聊天框带 `data-testid`；`prefers-reduced-motion: reduce` 下装饰动画停止；elapsed 定时器仅在 `isRunning` 时运行。 |
| AC-G | 全量回归：backend、stability、sentinel、doe×3、preprocessor、conformance、store lock、前端 build、镜像 `--check` 全绿。 |

## 3. Implementation Steps

### P0-A 评分/结论打通（write-time + read-time）

1. 新增 `app/backend/src/services/intent-outcome.service.mjs`（纯函数，便于单测）：
   - `extractIntentOutcome(runDir, intent)`：稳定性 `line_report/stability_report.json` → `conclusion.score/grade/label`；哨兵 `sentinel/alert.json` → `status + alerts.length`；DOE `conclusions/doe_conclusion.json` → `evidence_grade + design_type`；经验 `conclusions/recommendation.json` → `recommendation_status + playbooks.length`；优化 `01_state/optimizer_state.json` → `phase + round_count`；deep-diagnosis 恒返回空。
   - `enrichRunOutcome(run)`：仅对**终态、score 与 verdict 均空、有 workspace_path** 的 specialist run 派生（不覆盖已有值；文件缺失/JSON 损坏安全返回）。
2. 完成分支（`diagnosis.service.mjs` result 处理）改为「工件优先，`Judge Score:` 兜底」，completion event 同步携带。
3. 读取面接入派生：`history.service.listRunsForUser` / `getRunWithLogs`、`diagnosis.service.getDiagTaskView`（外部 API 与任务条目同源）。
4. 前端 `HistoryList.vue`：等级感知 verdict 配色 + title；分数原样显示小数。
5. 测试：`app/backend/test/intent-outcome.test.mjs`（5 类工件 + 损坏 JSON + 不覆盖已有值 + deep-diagnosis 空）。

### P0-B 一键继续（所有 harness）+ HTTP 语义

1. `session-integrity.service.mjs`：导出 `RESUMABLE_HARNESSES`、`engineSupportsSessionChat`、`resolveChatRoute(run)`（`session` / `rebuild(reason)` / 409 `RESUME_UNSUPPORTED`）。
2. `diagnosis.service.sendChatMessage`：
   - rebuild 路由 → 系统条 + `continueDiagnosis`，返回 `{mode:'rebuild',reason}`；
   - session 路由失败 → 有上下文则系统条 + 重建，无上下文才 409；
   - 保留 `CHAT_TURN_BUSY`、`RUN_HARNESS_MISMATCH`、`RUN_DELETED`。
3. `routes/diagnosis.routes.mjs` 按 err.status/code 返回；响应带 `mode`；404 仅 run 不存在。
4. `HARNESS_DEFS` 的 `chat` 能力由 `RESUMABLE` 集合派生；`capabilities` 暴露 `session_resume`。
5. 测试：`session-management.test.mjs` 增 `resolveChatRoute` 表驱动；E2E 用真实 mock run 验证 rebuild 路径。

### P1 codex/opencode 意图指令 + 能力矩阵

1. `codex-client.mjs` / `opencode-client.mjs`：`startDiagnosis` 接收 `analysisIntent`、`preprocessingMode`；导出 prompt builder；skill 引用按 intent 重定向（与 omp 同构）；末尾追加 `buildIntentDirective`。
2. `intent-capability.service.mjs`：`supportedIntentsFor(harness)`（HARNESS_DEFS.intents ?? 全部）、`assertIntentSupportedOnHarness`；`createDiagnosisRun` 在 intent 解析后调用。
3. `external.service.listIntents`/capabilities 暴露 `supported_intents`、`session_resume`。
4. 测试：`intent-prompt-contract.mjs` 扩展两个 builder；`analysis-intent.test.mjs` 增矩阵用例（全引擎支持 + 注入受限引擎触发 400）。

### P2-1 前端可测试性与 reduced-motion

1. `AuthView.vue`：username/password/email/tabs/submit 的 `data-testid`。
2. `App.vue`：`nav-<key>`、`engine-select`、`logout`。
3. `HistoryList.vue`：`history-search`、`history-status-filter`、`history-row-<runId>`、`history-continue-<runId>`。
4. `ChatInput.vue`：`run-chat-input`、`run-chat-send`。
5. `DiagnosisView.vue`：elapsed 仅 `isRunning` 启动。
6. `styles/global.css`：`@media (prefers-reduced-motion: reduce)` 关闭装饰动画与过渡。
7. 新增 `scripts/e2e/ui-smoke-native.mjs`（CDP 原生输入，依赖本机 Chrome/Edge，无新增 npm 依赖）。

### P2-2 mock 语义标注

1. `buildExternalResult`、`createTask`、`hydrateTask`、`listTaskEntries` 增 `analysis_mode`（mock/real）。
2. `docs/api-external.md` 说明；`external` 测试断言。

## 4. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 读取时派生拖慢历史列表 | 仅对「终态 + score/verdict 均空 + specialist + 有 workspace」的行读 1-2 个小 JSON；结果按 run_id 缓存；文件缺失立即返回 |
| 派生值覆盖真实评分 | 只在 DB 两列为空时派生；写入路径仍以工件结果落库 |
| 重建回退让聊天变重 | 系统条明示原因；`CHAT_TURN_BUSY` 防并发；同 harness/intent/data |
| 能力表改动影响 UI | 仅移除与实际不符的 `chat`；`live` 不变；console 不以 capability 决定可否继续 |
| codex/opencode prompt 变更影响默认 run | `buildIntentDirective('deep-diagnosis')` 返回空串，skill 引用不变 |
| 前端锚点/动画改动 | 仅加属性与 CSS 媒体查询；`npm run build` + 原生冒烟 |

## 5. Verification Steps

```bash
cd app/backend && npm test
# specialist skills
uv run --project .claude/shared/scripts python .claude/skills/industrial-line-stability-report/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-sentinel/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/test_ontology_phase1.py
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/test_aws_capture.py
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
uv run --project .claude/shared/scripts python .claude/shared/scripts/test_ontology_prepare_common.py
uv run --project .claude/shared/scripts python .claude/shared/scripts/test_ontology_store_lock.py
cd app/frontend && npm run build
# contracts + live E2E (backend up)
node scripts/e2e/intent-prompt-contract.mjs
node scripts/e2e/ui-smoke-native.mjs --api http://127.0.0.1:3211 --web http://127.0.0.1:5181
node scripts/e2e/ws-live-chat-e2e.mjs --run <id> --base http://127.0.0.1:3211
node scripts/sync-harness-skills.mjs --check
```

## 6. RALPLAN-DR Summary

**Principles**：冻结契约只增不改；诚实语义优先于"看起来成功"；用户可见数字必须与工件一致；引擎能力是数据而非猜测；每个修复都有可重复锚点。

**Options**：A（推荐，P0→P1→P2 分阶段）/ B（一次性）/ C（只修评分）。选 A：P0 直接修用户每天可见的两件事，回归面可控。

## 7. ADR

- **Decision**：选项 A；P0-A 采用「写入时落库 + 读取时派生」双轨；P0-B 采用「能重建就重建」而非一刀切 409；P1 修 wiring 并把能力表变成事实。
- **Consequences**：历史 specialist run 立即恢复分数/结论；11 个非 resume 引擎的"继续"从 404 变为受控重建；`chat` 能力不再撒谎。
- **Follow-ups**：原生 resume 仍需上游 CLI 支持（不在本计划内）。

## 8. 排期

| 阶段 | 内容 | 人日 |
|---|---|---|
| P0-A | 评分/结论双轨 + 测试 | 0.5 |
| P0-B | 全 harness 继续 + 语义 + 能力真相 | 0.5 |
| P1 | codex/opencode + 矩阵 | 0.5 |
| P2-1 | 锚点/动效/原生冒烟 | 0.5 |
| P2-2 | mock 标注 | 0.25 |
| 验收 | 全量回归 + E2E | 0.5 |
| **合计** | | **2.75** |

## 9. 实施与验收记录（2026-10-22）

### 9.1 落地清单

| 阶段 | 文件 | 结果 |
|---|---|---|
| P0-A | 新增 `services/intent-outcome.service.mjs`；`diagnosis.service` 完成分支改「工件优先 + Judge Score 兜底」；`history.service`/`getDiagTaskView` 读取时派生；`HistoryList.vue` 等级感知徽章 | 5 类 specialist 工件 + 历史 run 全部可读；deep-diagnosis 不变 |
| P0-B | `session-integrity` 新增 `RESUMABLE_HARNESSES`/`engineSupportsSessionChat`/`resolveChatRoute`/`rebuildNotice`；`sendChatMessage` 重构为 session/rebuild 两路由；路由 404/409/400 语义修正；`HARNESS_DEFS.chat` 改为事实 | 11 个非 resume 引擎不再 404；`chat` 能力不再撒谎 |
| P1 | codex/opencode `startDiagnosis` 接收 `analysisIntent`/`preprocessingMode`，builder 导出并注入指令 + 技能重定向；新增 `intent-capability.service.mjs`；capabilities 暴露 `session_resume`/`supported_intents` | 14 引擎 × 6 intent 全覆盖；受限组合 400 |
| P2-1 | Auth/App/History/ChatInput `data-testid`；elapsed 仅 running；global.css reduced-motion；新增 `scripts/e2e/ui-smoke-native.mjs` | 原生输入冒烟 12/12 |
| P2-2 | `buildExternalResult`/task entry 增 `analysis_mode`；`docs/api-external.md`/`docs/api.md` 更新 | mock/real 可区分 |

### 9.2 实施中发现并修复的额外缺陷

- **回合锁/流生命周期泄漏**：`consumeSessionChat` 原先只在流结束时释放 `activeChatTurns`；mock/常驻引擎在 `result` 之后流不关闭，导致第二次聊天永久 409 `CHAT_TURN_BUSY`。改为「一个 result = 一个回合」：聊天路径收到 result 即释放锁、`query.close()` 并退出循环；`executeDiagnosis` 收到 result 也立即 `break`，由循环后逻辑统一收尾（避免执行 promise 与锁永久悬挂）。实测同一 mock run 连续 3 次聊天均 200；`ws-live-chat-e2e` 5/5，并加 `_seq` 水位避免把订阅回放误判为新回复。
- **`asNumber(null) → 0`**：稳定性无评分时会把 null 读成 0 分；已改为 null/undefined/'' 直返 null（单测覆盖）。
- **`emit()` 需要内存 run 条目**：对从未在本进程执行过的持久化 run 发 rebuild 系统条时被静默丢弃；rebuild 路径先 `createRun`（`nextSeq` 从 DB MAX(seq) 续接）。

### 9.3 验收结果（全绿）

| 判据 | 结果 |
|---|---|
| AC-1a | `GET /api/history/runs/46833919` → `score=65.8`、`verdict="C · 波动"`（source `line_report/stability_report.json#conclusion`） |
| AC-1b | `46894aff` → `verdict="alert · 742 alerts"`，score=null |
| AC-1c | deep-diagnosis `11995a0a` → 96 / ENDORSED，未变 |
| AC-1d | DOE `2a7ef23f` → `A · rsm_ccd`；experience `c2ef3526` → `playbook_hit · 1 playbook`；optimizer `a3cd1d7f` → `exploiting · round 2`；score 均 null |
| AC-2a/2b/2c | mock-e2e：codex run chat → 200 `{mode:"rebuild",reason:"engine_no_resume"}` + 说明条；无上下文 → 409 `RESUME_UNSUPPORTED`；mock session → 200 `{mode:"session"}` |
| AC-2d | capabilities：claude/omp/goose/mock `session_resume=true`，其余 false；`HARNESS_DEFS.chat` 与之一致 |
| AC-3a/3b | `intent-prompt-contract.mjs` 全 PASS（含 codex/opencode × 5 specialist）；矩阵单测覆盖受限引擎 400 |
| AC-4 | 外部 mock run → `analysis_mode="mock"`（result + task entry）；非 mock → `"real"` |
| AC-5a/5b | `ui-smoke-native.mjs` 12/12：原生鼠标/键盘完成 登录→History→继续→发送→回复；reduced-motion 计算值 `1e-05s` |
| AC-G | backend **207/207**；stability **173/173**；sentinel **183/183**；doe **199/199 + 69/69 + 46/46**；preprocessor ALL PASSED；shared **9/9 + 1/1**；前端 build OK；镜像 534 files identical；session-management E2E before/after 各 0 failures；ws-live-chat 5/5 |
