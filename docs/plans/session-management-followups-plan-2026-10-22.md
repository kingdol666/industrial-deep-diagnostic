# 续聊/评分/引擎覆盖/前端可测试性 — 后续优化计划 v1 (2026-10-22)

> **状态：pending approval**（omc-plan Direct 模式产出；未授权前不实施）
> 代码基线：`973e049`（已推送 `origin/feat/doe-ontology-first`），全量回归绿。
> 存储位置说明：仓库惯例为 `docs/plans/`（omc-plan 默认 `.omc/plans/`，本仓库无 `.omc/` 目录，按仓库惯例落盘）。

## 0. 五项问题复核（2026-10-22 实测证据）

| # | 问题 | 是否成立 | 证据（file:line / 实测） |
|---|---|---|---|
| 1 | 部分引擎不支持 run 级 resume | **成立（契约/体验问题）** | 仅 `goose` 标记 `resumable: true`（`app/backend/src/engine/oneshot-specs.mjs:316`）；`engineCanResumeSession` 对 acp/codex/opencode/mock 恒 false（`services/diagnosis.service.mjs:961-972`）；codex/opencode 的 `startSessionChat` 直接抛 400（`engine/codex-client.mjs:255-260`、`engine/opencode-client.mjs:382-387`）→ **11/14 harness 不可 resume**（可 resume：claude/omp/goose）。`sendChatMessage` 吞掉异常后路由统一 404（`services/diagnosis.service.mjs` sendChatMessage catch、`routes/diagnosis.routes.mjs:144-163`），API 调用方拿到误导性 "Run not found"。 |
| 2 | codex/opencode 未接意图指令 | **成立（正确性问题）** | 两个 client 的 `startDiagnosis` 参数中 `analysisIntent` 出现次数为 **0**（`engine/codex-client.mjs:233-239`、`engine/opencode-client.mjs:367-372`），prompt 仅含 runtime protocol + ontology/enhancement。specialist intent 在这两个引擎上会跑通用协议：stability/quick-screen 因缺必产物会被判 failed（`services/diagnosis.service.mjs:685-697`），experience-mining/optimizer-campaign 无必产物检查 → **静默跑错技能**。 |
| 3 | mock 不产 specialist 工件 | **不成立（设计如此）** | 必产物检查对 mock 显式豁免（`services/diagnosis.service.mjs:694`）；文档已标 "mock（集成测试，非真实分析）"（`docs/api-external.md:65`）。仅需语义标注。 |
| 4 | History 评分列对 specialist run 显示 `--` | **成立（用户可见缺口）** | 完成时只从 `report.md` 提取 `Judge Score:`（`services/diagnosis.service.mjs:1202-1205`）；历史列仅在 `run.score != null` 时渲染（`components/history/HistoryList.vue:158-159`）。稳定性 JSON 已有 `conclusion.score=65.8 / grade=C / label=波动`（实测 run `202610220455199_lsr_demo`），未写入 run 级字段。 |
| 5 | 持续重渲染导致自动化点击超时 | **成立（可测试性/性能，非功能缺陷）** | 前端 11 处 `animation: … infinite`（登录页呼吸点 `components/auth/AuthView.vue:302`、状态点、进度条等）；运行视图每秒 elapsed 定时器（`components/diagnosis/DiagnosisView.vue:510`）；实测 Playwright 对登录按钮/历史行点击超时（locator 重试期元素被替换），页面内事件点击正常。 |

## 1. Requirements Summary

- **R1**（用户可见）：specialist run 完成后，run 级 `score` / `judge_verdict` 与报告工件一致（稳定性分数、等级；哨兵告警摘要），History/报表页不再显示 `--`。
- **R2**（覆盖）：任意 harness 的 run 都能"一键继续对话"——支持 resume 的用原 session，不支持的走同 harness/intent/data 的受控重建；HTTP 错误语义不再用 404 冒充。
- **R3**（正确性）：codex/opencode 上选择 specialist intent 时注入对应意图指令；若引擎能力不足以执行该 intent，则**显式 400 拒绝**而非静默跑错。
- **R4**（诚实标注）：mock run 在外部结果/任务条目中带 `analysis_mode:"mock"`，明确不参与产物契约。
- **R5**（可测试性）：前端交互元素具备稳定测试锚点、减少无谓重渲染、尊重 reduced-motion；自动化可用原生 click 完成登录→历史→续聊冒烟。

## 2. Acceptance Criteria（全部可执行）

| ID | 判据（命令/断言） |
|---|---|
| AC-1a | 对稳定性 run 调用 `GET /api/history/runs/:id` → `score == 65.8` 且 `judge_verdict` 含 `C`（以该 run 的 `stability_report.json` 的 `conclusion.score/grade` 为准）；History 行渲染出 65.8 与 "C"。 |
| AC-1b | 对哨兵 run → `judge_verdict` 含 alert 状态与告警数（如 `alert · 742 alerts`），`score` 为 null；History 结论列显示该文本。 |
| AC-1c | deep-diagnosis run 的评分行为与现在**逐字节一致**（仍取 `Judge Score:`），全套件绿。 |
| AC-2a | 非 resume 引擎（以 mock 之外的 codex/opencode/gemini 任一可用者验证；不可用时用单测注入）发 `POST /api/diagnosis/chat/:runId` → 200，且 service 走 `continueDiagnosis`（日志/emit 含"已按当前上下文重建"系统条），**不调用** `startSessionChat`。 |
| AC-2b | 真正不可恢复错误（如 claude session 丢失）返回 **409 `RESUME_UNSUPPORTED`**，错误体含 `harness` 与建议；不再返回 404。 |
| AC-2c | claude/omp/goose 的既有 resume 行为不变（`session-map.resumable=true`，续聊 WS 实时收到 assistant 事件——复用 `scripts/e2e/ws-live-chat-e2e.mjs`）。 |
| AC-3a | `scripts/e2e/intent-prompt-contract.mjs` 扩展后断言：codex/opencode 的 prompt 渲染函数包含 `ANALYSIS_INTENT: <intent>` 与对应 skill 名。 |
| AC-3b | 若某 engine 被标注不支持某 intent，`POST /api/external/v1/analyze` 返回 400 `INTENT_UNSUPPORTED_ON_HARNESS`（supported 列表附可用引擎）。 |
| AC-4 | mock run 的 `GET /api/external/v1/analyze/:runId` → `analysis_mode == "mock"`；任务条目同样带该字段；非 mock 结果不出现该字段。 |
| AC-5a | 新增 `scripts/e2e/ui-smoke-native.mjs`：仅用 Playwright 原生 `click()/fill()`（无 JS 兜底）完成 登录 → History → 继续对话 → 发送 → 收到回复，全部步骤通过。 |
| AC-5b | 登录页/历史页的交互元素带 `data-testid`；`prefers-reduced-motion: reduce` 下装饰性 infinite 动画停止；completed 视图不再每秒重渲染（elapsed 定时器仅在 running 时启动）。 |
| AC-G | 全量回归：backend 176+、stability 173、sentinel 183、doe 199+69+46、preprocessor、conformance、store lock、前端 build、镜像 `--check` 全绿。 |

## 3. Implementation Steps

### P0-A 评分/结论打通（0.5 人日）

1. `app/backend/src/services/diagnosis.service.mjs` 增加 `extractIntentOutcome(runDir, analysisIntent)`：
   - `stability-report`：读 `line_report/stability_report.json` → `conclusion.score`（number）、`conclusion.grade` + `conclusion.label`（如 `C·波动`）；
   - `quick-screen`：读 `sentinel/alert.json` → `status` + `alerts.length` → verdict 文本；
   - `doe-analysis`：读 `conclusions/doe_conclusion.json`（存在 `score/verdict` 才写）；
   - 其他/缺失 → 回退现有 `Judge Score` 正则。
2. 完成分支（`diagnosis.service.mjs:1192-1245`）调用该函数，优先使用工件结果，再 fallback 正则；`completeRun` 写入 score/verdict；completion event 同步携带（前端实时刷新）。
3. 测试：新增 `app/backend/test/intent-outcome.test.mjs`（临时 run 目录 + 四种 intent 的 JSON 夹具；断言提取与兜底）；现有 `artifact-manifest`/`analysis-intent` 测试不动。

### P0-B 一键继续（所有 harness）+ HTTP 语义（0.5 人日）

1. `services/diagnosis.service.mjs`：
   - 新增 `engineSupportsSessionChat(harness)` = `{claude, omp, goose, mock}`（mock 为进程内聊天，保留现状，避免破坏透传 E2E）；
   - `sendChatMessage`：若当前 harness 不支持 session chat → 直接 `continueDiagnosis(runId, message)` 并 emit `session_chat` 系统条（"该引擎不支持会话恢复，已按当前上下文重建"）；保留 `CHAT_TURN_BUSY` 与 `RUN_HARNESS_MISMATCH` 语义；
   - 真正的 resume 失败：抛出带 `status=409, code='RESUME_UNSUPPORTED'` 的错误（含 harness、run_id、建议）。
2. `routes/diagnosis.routes.mjs:144-163`：按 err.status/code 返回；404 仅用于 run 不存在。
3. 测试：`session-management.test.mjs` 增 `engineSupportsSessionChat` 表驱动用例；单测桩断言非支持引擎不调用 `startSessionChat`。

### P1 codex/opencode 意图指令（0.5 人日）

1. `engine/codex-client.mjs:233-249`、`engine/opencode-client.mjs:367-380`：`startDiagnosis` 接收 `analysisIntent = 'deep-diagnosis'`，在各自 prompt builder 末尾追加 `buildIntentDirective(analysisIntent, sceneName)`（与 omp/one-shot 同源，`engine/claude-client.mjs` 导出）。
2. 能力矩阵：在 `ANALYSIS_INTENTS` 或引擎元数据中声明每个 harness 支持的 intent；API 层对不支持组合返回 400 `INTENT_UNSUPPORTED_ON_HARNESS`（`routes/external.routes.mjs`、`routes/diagnosis.routes.mjs`）。
3. 测试：扩展 `scripts/e2e/intent-prompt-contract.mjs`（对两个 builder 的静态/导出接口断言）；`analysis-intent.test.mjs` 增能力矩阵用例。

### P2-1 前端可测试性与渲染瘦身（0.5-0.75 人日）

1. `components/auth/AuthView.vue`、`components/history/HistoryList.vue`、`components/diagnosis/DiagnosisView.vue`：给输入框/按钮/行加 `data-testid`（如 `auth-username`、`auth-submit`、`history-row-<runId>`、`run-chat-input`）。
2. `components/history/HistoryList.vue`：分类选项改为共享 computed（现每行每次渲染重建 `未分类+分类列表`）；行 key 用 `run_id` 稳定。
3. `components/diagnosis/DiagnosisView.vue:510`：elapsed 定时器仅在 `isRunning` 时启动，终态视图停止。
4. `styles/global.css` + 各组件：`@media (prefers-reduced-motion: reduce)` 停止装饰性 infinite 动画（保留 loading spin 的语义类）；呼吸点动画不改布局属性，仅 opacity。
5. 新增 `scripts/e2e/ui-smoke-native.mjs`：原生 click 冒烟（AC-5a）。

### P2-2 mock 语义标注（0.25 人日）

1. `services/external.service.mjs` 的 `buildExternalResult` 与 task entry 增 `analysis_mode: harness === 'mock' ? 'mock' : 'real'`（加法式）。
2. `docs/api-external.md` 增一句说明；`app/backend/test` 增断言。

## 4. Risks and Mitigations

| 风险 | 缓解 |
|---|---|
| 完成分支改动影响深诊评分 | 提取顺序为"工件优先、Judge Score 兜底"，AC-1c 逐字节回归 + 全套件 |
| 非 resume 回退改变 mock 聊天行为 | mock 列入 `engineSupportsSessionChat`（进程内 chat），透传 E2E 保持 |
| codex/opencode prompt 变更影响非专项 run | 默认 intent 不追加任何指令（`buildIntentDirective` 返回空串），行为不变 |
| 能力矩阵 400 误伤既有调用 | 仅对"该引擎明确不支持"的 intent 组合生效；capabilities 响应同步暴露 supported_intents |
| 前端改动引入回归 | 仅加测试锚点/共享 computed/定时器条件；`npm run build` + 原生 click 冒烟 |
| P0-B 与 409 语义影响现有前端提示 | 前端已展示 emit 的 error 文本；路由 status 变化不影响 UI 文案 |

## 5. Verification Steps

```bash
# 后端与套件
cd app/backend && npm test
uv run --project .claude/shared/scripts python .claude/skills/industrial-line-stability-report/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-sentinel/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/run_tests.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/test_ontology_phase1.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/test_aws_capture.py all
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
uv run --project .claude/shared/scripts python .claude/shared/scripts/test_ontology_prepare_common.py
uv run --project .claude/shared/scripts python .claude/shared/scripts/test_ontology_store_lock.py
# 前端
cd app/frontend && npm run build
# E2E（后端 3211 在场）
node scripts/e2e/intent-prompt-contract.mjs
node scripts/e2e/ws-live-chat-e2e.mjs --run b5c9236a --base http://127.0.0.1:3211
node scripts/e2e/continue-chat-state-e2e.mjs before --base http://127.0.0.1:3211   # 重启后端
node scripts/e2e/continue-chat-state-e2e.mjs after  --base http://127.0.0.1:3211
node scripts/e2e/ui-smoke-native.mjs                                              # 新增
# 镜像（静态时点）
node scripts/sync-harness-skills.mjs --check
```

## 6. RALPLAN-DR Summary

**Principles**

1. 冻结契约只增不改（`sentinel-alert/1.0`、`line-stability-report/1.0`、文件名、退出码）。
2. 诚实语义优先于"看起来成功"（不支持就 409/400，不静默跑错或 404 冒充）。
3. 用户可见数字必须与工件一致（评分/结论来自产物本身）。
4. 引擎能力是数据而非猜测（能力矩阵 + capabilities 暴露）。
5. 每个修复都有可重复的 E2E 或单测锚点。

**Decision Drivers**

1. 用户可见一致性（评分列/续聊可用性）；
2. 14 harness 全覆盖；
3. 回归成本与冻结契约风险。

**Viable Options**

| 选项 | 做法 | Pros | Cons |
|---|---|---|---|
| **A（推荐）** | 两阶段：P0（评分+续聊覆盖）→ P1（意图）→ P2（前端/mock） | 每阶段可独立验收；P0 用户感知最快；回归面小 | 周期分两次，总时长略长 |
| B | 一次性全做 | 一次交付 | 后端/前端/引擎混在一轮，回归定位成本高 |
| C | 只修评分 | 改动最小 | 静默跑错技能与 404 语义仍在，续聊覆盖仍 3/14 |

## 7. ADR

- **Decision**：采用选项 A，先 P0（评分 + 全 harness 一键继续），再 P1/P2。
- **Drivers**：用户可见一致性；诚实错误语义；控制冻结契约风险。
- **Alternatives considered**：B（单批，回归风险高）；C（覆盖面不足）。
- **Why chosen**：P0 两项都是用户每天会碰到的行为，且不触碰引擎/前端大改；P1/P2 可在其后独立验收。
- **Consequences**：需要两轮回归；P0 完成后 History 分数与报告一致、所有 harness 可一键继续。
- **Follow-ups**：7 个不可 resume 引擎的原生 resume 需上游 CLI 支持（不在本计划内）；UI 重渲染若仍有残留，再做一次渲染 profiler。

## 8. 排期

| 阶段 | 内容 | 人日 |
|---|---|---|
| P0-A | 评分/结论打通 + 测试 | 0.5 |
| P0-B | 全 harness 一键继续 + 409 语义 + 测试 | 0.5 |
| P1 | codex/opencode 意图 + 能力矩阵 | 0.5 |
| P2-1 | 前端测试锚点/渲染瘦身/原生 click 冒烟 | 0.5-0.75 |
| P2-2 | mock 语义标注 | 0.25 |
| 验收 | 全量回归 + E2E | 0.5 |
| **合计** | | **2.75-3.0** |
