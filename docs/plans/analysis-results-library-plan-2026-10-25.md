# 分析结果库（Results Library）— 设计计划 v2 (2026-10-25)

> **状态：IMPLEMENTED（2026-10-25 实施完成并通过全量验收，见 §9）**
> 基线：`70d2222`（已推送），后端 220/220、API 契约 22/22、skill 静态审计 0 失败。
> 需求来源：用户 2026-10-25 —— 结果的描述/摘要/分类管理，扁平结构化，报告元数据入库，
> Agent 先看全量摘要 → 选 id → 取详情，人与 Agent 均可 API 集成；
> v2 追加：详情/整体两级 API 具体契约（§8）、完成后自动摘要机制（§8.4）。

## 0. 现状与缺口（2026-10-25 实测）

| 现有能力 | 位置 | 缺口 |
|---|---|---|
| 运行台账（状态/score/verdict/分类/软删） | `diagnostic_runs` + `/api/history/*` | 面向"运行"而非"结果"：无 description、无 tags、无 metadata JSON |
| 摘要 | `getDiagTaskView` 读取时从 report.md 切结论段（≤1500 字符） | **不落库**、非结构化、每次重算、无法全文检索 |
| 评分/结论 | `intent-outcome.service`（工件派生） | 只写 score/verdict 两列，不带 key findings |
| 工件清单 | `buildArtifactManifest` | 只在结果视图临时拼装，不持久化 |
| 分类 | `run_categories`（用户自定义，run 级） | 无结果级 tags，无按意图/标签的扁平检索 |
| Agent 集成 | `/api/external/v1/*` | 无"摘要索引 → id → 详情"两级接口 |

已完成 run 106 个（含 6 种 intent 的真实工件），是回填与验证的现成语料。

## 1. 验收测试（实施前已完成）

| 项 | 结果 |
|---|---|
| skill 设计静态审计（24 skills/16 agents/frontmatter/协议引用/Schema/脚本路径/镜像） | **0 failures**（`node scripts/audit/skill-design.mjs`） |
| 后端回归 | **220/220** |
| 前后端 API 契约（GET-only，现有 run） | **22/22**（`scripts/e2e/api-contract-final.mjs`） |
| 多功能分析结果正确性（6 intents 真实工件核对，本会话） | stability 65.8/C·波动（新跑 837404b0 + 历史 46833919）、sentinel `alert · 742 alerts`、DOE `A · rsm_ccd`、experience `playbook_hit · 1 playbook`、optimizer `exploiting · round 2`、deep-diagnosis 96/ENDORSED |
| 实机交互演示（本会话 final-demo） | 23/23：全页签渲染、历史台账、报告 MD(9070字符)/HTML(6905字符)、1280 响应式、0 console error |
| 续问正确性 | Q1 引用 65.8/C/feed_rate、Q2 cooling_flow —— 回复与工件一致 |
| 开发规范 | 镜像 `--check` 同步；AGENTS.md 契约与实际一致；docs（api/api-external/AGENTS/plans）齐备；测试锚点可重复执行；工作区 clean |

**结论**：系统与 skill 流程健康，具备加入结果库的稳定基座。

## 2. Requirements Summary

- **R1 扁平结果表**：每个完成的分析一条记录（`analysis_results`），`result_id = run_id`（免双键）；含 title、**description（可编辑）**、**summary（自动摘要，落库）**、summary_json（结构化）、category_id、**tags**、metadata（报告与工件元数据）、intent/scene/harness/score/verdict、user_id、时间戳。
- **R2 自动摘要**：完成时由确定性提取器生成（零 LLM、可离线）：一行结论 + 关键数字（评分/等级/告警数/主效应/回合等，按 intent）+ 数据画像（行数/列数/时间范围）+ 工件清单；`sources` 字段记录每个数字的来源文件（可审计）。**`summary` 系统管理、不可手改；`description` 默认 null、可由用户/Agent 通过 PATCH 编辑；索引返回 `display_text = description || summary`**（见 §8.1），满足"自动总结一个摘要 description"且不污染用户可编辑字段。
- **R3 两级 Agent API**：`GET /api/external/v1/results`（扁平摘要索引，`q/intent/category/tag/scene/limit/offset/sort` 过滤，`?brief=true` 省token模式）→ 选中 id → `GET /api/external/v1/results/:id`（完整详情：summary_json + metadata + report_md 全文 + html/文件路径 + 工件清单）。控制台同源 `GET /api/results(…)`。
- **R4 管理能力**：`PATCH /api/results/:id`（description/category/tags/title，用户归属校验）；分类复用现有 `run_categories`（每用户隔离），tags 自由扁平。
- **R5 报告元数据入库**：report_md{path,bytes}、html[]、workspace_path、工件清单（kind+path+bytes）、duration、model、engine、（可得时）主表 sha256 指纹与行列数。
- **R6 回填与兜底**：启动幂等回填 106 个历史 run（只增不改）；API 读取时若行缺失则即时派生（与 intent-outcome 同模式），保证接口永不因缺行而空。
- **R7 可发现性**：`/api/external/v1/capabilities` 暴露 `results_index`；docs 更新；README 技能面提一句。

## 3. Acceptance Criteria（全部可执行）

| ID | 判据 |
|---|---|
| AC-1 | mock run 完成（既有 mock-e2e 扩展）→ `analysis_results` 行存在，summary ≥80 字符、summary_json.score/verdict 与工件一致、metadata.report_md.path 指向真实文件 |
| AC-2 | 回填幂等：连续两次 `backfillResults()` 计数一致、无重复行；历史 6 intents 各抽 1 run 的 summary 与工件核对一致 |
| AC-3 | `GET /api/external/v1/results?q=<关键词>` 命中摘要/描述/标签；`intent/category/tag` 过滤正确；分页/排序；`brief=true` 单卡 ≤ ~600 字符 |
| AC-4 | `GET /api/external/v1/results/:id` 返回 description、summary_json、metadata、report_md 全文、files.html[]、artifacts（对 837404b0：score 65.8、verdict `C · 波动`、html 含 line_stability_report.html） |
| AC-5 | `PATCH` 修改 description/tags/category 后，列表与详情立即反映；非属主 403；未认证 401 |
| AC-6 | 删除某行后 `GET /results/:id` 仍返回派生详情（read-time fallback）且标注 `derived:true` |
| AC-7 | capabilities 含 `results_index:true`；`docs/api-external.md` 新 §与错误码齐全 |
| AC-8 | Agent 演示脚本：仅凭 API 完成 "list(q=收率) → 选 id → detail → 引用报告数字" 三步（GET-only，可重复） |
| AC-9 | UI：History 详情面板显示摘要卡与描述/标签编辑；结果库页（扁平表格+筛选）渲染无 console error |
| AC-10 | **完成即可查**：run 完成事件后同进程同步写入，`GET /results/:id` 立即返回非空 summary（无需等回填）；摘要生成异常不得影响 run 终态（行仍写入，summary 允许为空串 + warn 日志） |
| AC-11 | **续跑/重建后更新**：对同一 run 继续（continue/chat rebuild）再次完成后，行被 UPSERT 更新（新 score/verdict/时间），不产生重复行 |
| AC-12 | **软删与可见性**：软删 run 在结果索引/详情中不可见（或带 `deleted:true` 标记，实现取其一并测试）；归属规则与 History 一致（本人 + 遗留 NULL 可见） |
| AC-G | 全量回归：backend 220+、四套 Python 件、前端 build、镜像 `--check`、既有 E2E（ui-smoke/ui-visual-audit/api-contract-final）全绿 |

## 4. Implementation Steps

### P0 存储与两级 API（1.0 人日）
1. `db/database.mjs`：建表 `analysis_results`（result_id PK、run_id UNIQUE、title/description/summary/summary_json/category_id/tags/metadata/intent/scene_name/harness/score/judge_verdict/user_id/created_at/updated_at）+ 索引（intent、category_id、user_id、created_at）+ `upsertResult`/`getResultById`/`listResultsFiltered`/`countResultsFiltered`/`updateResultFields`。
2. 新服务 `services/results-library.service.mjs`：
   - `summarizeRun(runDir, run)`：按 intent 从既有工件提取（复用 intent-outcome 读取器）→ `{ summary(中文一段), summary_json{conclusion,key_numbers,data_profile,artifacts,sources} }`；
   - `buildResultMetadata(run, runDir)`：报告/工件/时长/指纹；
   - `upsertResultFromRun(runId)`（完成钩子调用）、`backfillResults()`（启动幂等）、`deriveResultForApi(runId)`（read-time 兜底）。
3. `diagnosis.service` 完成分支（completeRun 之后）调用 `upsertResultFromRun`——**单一收口点**：全新 run、continue、chat rebuild 都经 `executeDiagnosis` 的 result 分支，续跑后行自动 UPSERT 更新（AC-11）；`index.mjs` 启动回填（只增）；列表 SQL 过滤软删 run（AC-12）。
4. 路由：`routes/results.routes.mjs`（console GET list/detail + PATCH）；`external.routes.mjs` 增 `/v1/results`、`/v1/results/:id`（brief 模式）；白名单/校验与现有外部路由同规。
5. 测试：`test/results-library.test.mjs`（六 intent 夹具摘要、回填幂等、fallback、PATCH 归属）；mock-e2e 增 AC-1。

### P1 摘要质量与 Agent 演示（0.5 人日）
1. 摘要模板打磨（六 intent 各一版，含 top-1 finding 截断与"无评估/数据不足"的诚实文案）。
2. `scripts/e2e/results-agent-workflow.mjs`：AC-8 三步演示。
3. docs：`api-external.md` 新 §Results Library（字段表+示例+错误码）、capabilities、README 一句。

### P2 前端管理（1.0 人日）
1. History 详情面板：摘要卡（summary + key_numbers）+ description/tags 编辑（PATCH）。
2. 新「结果库」页签：扁平表格（标题/摘要首行/intent/分类/标签/评分/结论/时间）+ q/intent/category/tag 筛选 + 行内跳报告/详情；空态与加载态。
3. `data-testid` 锚点 + ui-visual-audit 增结果库断言（AC-9）。

### P3 验收（0.5 人日）
按 §3 全量执行并回填记录；`harness-api-acceptance`/`api-contract-final` 纳入结果库检查。

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 确定性摘要质量低于 LLM | 摘要=结构化关键数字+报告结论段头部，附 sources；P2 可选"agent 撰写 interpretation"列（只追加不改数） |
| 双事实源（runs vs results） | runs 仍是运行生命周期权威；results 只存派生副本+用户字段；完成/续跑钩子同步；文档写明 |
| 回填扫全库（前车之鉴：事件误裁） | 回填只 INSERT/UPSERT 不删不改；幂等；日志计数；绝不触碰 event_stream |
| 归属/可见性 | 与 runs 同规：user_id 匹配或遗留 NULL 可见；PATCH 属主校验 |
| 大结果集列表 | 分页+索引+brief 模式；列表永不返回 report_md 全文 |

## 6. RALPLAN-DR

**Principles**：扁平单表、id 即 run_id；确定性摘要（数字可溯源）；两级 API（摘要索引→详情）；只增回填；与既有归属/分类体系复用而非再造。

**Options**：A（推荐）独立 `analysis_results` 表+双面 API；B 直接加列到 `diagnostic_runs`（表宽、生命周期与库混杂、迁移重）；C 全读时派生不落库（描述/标签无处存、列表慢）。

**ADR**：选 A。库与生命周期解耦，回填/兜底/编辑都简单；B/C 被上述缺点排除。

## 7. 排期

P0 1.0 + P1 0.5 + P2 1.0 + P3 0.5 = **3.0 人日**。

## 8. API 契约（v2 落地设计，示例取自真实 run `837404b0`）

通用：成功 `{"success":true,"data":…}`；失败 `{"success":false,"code":"…","error":"…"}`；鉴权同既有外部 API（Bearer 会话 JWT 或 `idd_` API Token）。控制台镜像路由 `/api/results*` 与外部路由同服务同实现。

### 8.1 结果索引（整体视图）— `GET /api/external/v1/results`

**Query**：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `q` | string | — | 全文匹配 title / description / summary / scene / tags（大小写不敏感） |
| `intent` | string | — | 6 值之一 |
| `category_id` | string | — | 用户分类（run_categories.id） |
| `tag` | string | — | 单标签精确匹配（tags JSON 数组含该值） |
| `scene` / `harness` | string | — | 精确匹配 |
| `min_score` | number | — | `score >= min_score` |
| `sort` | enum | `created_desc` | `created_desc` / `created_asc` / `score_desc` |
| `limit` / `offset` | int | 50 / 0 | 上限 200 |
| `brief` | bool | false | `true` 时 `display_text` 截断 160 字符、去掉 `key_numbers`，单卡 ≤ ~600 字符（Agent 省token模式） |

**响应 data：摘要卡片数组**（不含 report_md 全文、不含 metadata；总数与分页随响应返回）：

```json
{
  "total": 106, "limit": 50, "offset": 0,
  "results": [{
    "result_id": "837404b0",
    "title": "accept_api_837404b0",
    "description": null,
    "display_text": "演示反应产线 2026-10-07~10-10 总体波动（65.8 分，C 级）：4 参数入评，343 个 SPC 违规剧集、2 项显著漂移，最需关注 yield_pct。",
    "intent": "stability-report", "scene": "accept_api", "harness": "claude",
    "score": 65.8, "verdict": "C · 波动",
    "category_id": null, "tags": [],
    "key_numbers": { "grade": "C", "spc_violation_episodes": 343, "significant_drifts": 2, "top_concern": "yield_pct" },
    "has_report": true, "has_html": true,
    "created_at": "2026-10-22 14:15:05", "completed_at": "2026-10-22 14:33:12"
  }]
}
```

> `display_text = description || summary`（description 为用户/Agent 编辑值，优先展示；未编辑时即自动摘要首段）。

**错误**：401 `AUTH_REQUIRED`；400 `RESULTS_QUERY_INVALID`（非法 intent/sort/limit）。

### 8.2 结果详情 — `GET /api/external/v1/results/:resultId`

**Query**：`include_md`（默认 true，携带 report.md 全文；`false` 时只给 `report_md_url`）。

**响应 data**（单对象）：

```json
{
  "result_id": "837404b0",
  "title": "accept_api_837404b0",
  "description": null,
  "summary": "该产线在本时段总体运行波动（65.8 分，C 级）：评估 4 个参数，检出 343 个 SPC 违规剧集、2 项显著漂移；最需关注：yield_pct。数据 864 行 × 4 参数（5 分钟采样，缺失率 0），时段 2026-10-07 08:00 ~ 2026-10-10 07:55。",
  "summary_json": {
    "conclusion": "该产线在本时段总体运行波动（65.8 分，C 级）：评估 4 个参数，检出 343 个 SPC 违规剧集、2 项显著漂移；最需关注：yield_pct。",
    "key_numbers": {
      "score": 65.8, "grade": "C", "label": "波动",
      "n_parameters_assessed": 4, "n_findings": 10,
      "spc_violation_episodes": 343, "significant_drifts": 2,
      "top_concern": "yield_pct"
    },
    "data_profile": {
      "rows": 864, "parameter_cols": ["yield_pct","reactor_temp","feed_rate","cooling_flow"],
      "time_range": ["2026-10-07 08:00:00", "2026-10-10 07:55:00"],
      "sampling_interval_seconds": 300, "missing_rate": 0, "sampled": false,
      "sha256": "sha256:5b713e22…c7d566"
    },
    "artifacts": ["line_report/stability_report.json", "line_report/line_stability_report.html", "report.md"],
    "sources": {
      "score": "line_report/stability_report.json#conclusion.score",
      "spc_violation_episodes": "line_report/stability_report.json#conclusion.statement",
      "rows": "line_report/stability_report.json#data.n_rows_used"
    }
  },
  "metadata": {
    "workspace_path": "workspace/diagnostic-runs/202610221415056_accept_api",
    "report_md": { "path": "workspace/diagnostic-runs/202610221415056_accept_api/report.md", "bytes": 17093 },
    "html": [{ "path": "line_report/line_stability_report.html", "bytes": 120199 }],
    "artifacts": [{ "kind": "stability_report", "path": "line_report/stability_report.json" },
                  { "kind": "stability_html", "path": "line_report/line_stability_report.html" }],
    "duration_ms": 1087000, "engine": "claude", "model": null,
    "data_fingerprint": "sha256:5b713e22…c7d566", "ontology_hit": "reused"
  },
  "intent": "stability-report", "scene": "accept_api", "harness": "claude",
  "score": 65.8, "verdict": "C · 波动",
  "category_id": null, "tags": [],
  "report_md": "# 产线运行稳定性报告 · 演示反应产线（accept_api）…（全文）",
  "report_md_url": "/api/files/workspace/report/202610221415056_accept_api",
  "files": { "html": [{ "path": "line_report/line_stability_report.html",
                        "abs_path": "D:\…\line_stability_report.html",
                        "url": "/api/files/workspace/asset/202610221415056_accept_api/line_report/line_stability_report.html" }] },
  "run": { "run_id": "837404b0", "status": "completed", "session_resumable": true },
  "derived": false,
  "created_at": "2026-10-22 14:15:05", "completed_at": "2026-10-22 14:33:12"
}
```

**错误**：404 `RESULT_NOT_FOUND`（id 不存在或软删）；401 同上。`derived:true` 表示行缺失、由读取时派生（AC-6）。

### 8.3 结果管理 — `PATCH /api/external/v1/results/:resultId`（控制台 `/api/results/:id` 同）

**Body**（至少一项）：`{ "description"?: string ≤2000, "category_id"?: string|null, "tags"?: string[] ≤16 项单项 ≤40 字符, "title"?: string ≤200 }`

**响应**：200 + 更新后的完整卡片（同 8.2 结构）；未提供的字段不变；`summary` 不可通过 API 修改（400 `SUMMARY_READONLY`）。
**错误**：404 `RESULT_NOT_FOUND`；403 `RESULT_FORBIDDEN`（非属主）；400 校验码。

### 8.4 完成后自动摘要（机制收口）

```
executeDiagnosis 收到 result(success)
  → completeRun（落库 status/score/verdict）            # 既有逻辑不动
  → upsertResultFromRun(runId)                           # 新增，同步、try/catch
       ├─ summarizeRun(runDir, run)                      # 确定性提取，零 LLM
       │    stability: stability_report.json#conclusion(+statement)+data
       │    quick-screen: alert.json#status/alerts/checks_summary
       │    doe: doe_conclusion.json#evidence_grade/design_type/key_findings[0]
       │    experience: recommendation.json#recommendation_status/playbooks
       │    optimizer: optimizer_state.json#phase/round_count/incumbent
       │    deep-diagnosis: report.md 结论段头部（既有 1500 字符提取器）
       ├─ buildResultMetadata(run, runDir)               # 报告/工件/时长/指纹
       └─ stmts.upsertResult(...)                        # ON CONFLICT(result_id) DO UPDATE
  → 失败策略：提取异常仅 logger.warn，行仍以 title/intent/score/verdict 写入（summary=''）
```

- **单一收口**：全新 run、`continue`、chat `rebuild` 的完成都走这一个 result 分支 → 续跑后同一 `result_id` 行被更新（AC-11），不产生重复。
- **回填**：启动 `backfillResults()` 幂等只增（106 个历史 run）。
- **兜底**：API 读时行缺失 → `deriveResultForApi` 即时派生并标注 `derived:true`（AC-6）。
- 时序保证：完成事件与结果行写入在同一同步路径，完成即可查（AC-10）。

### 8.5 可发现性

`GET /api/external/v1/capabilities` 增 `"results_index": true` 与 results 端点清单；`docs/api-external.md` 新增 §Results Library（以上表格/示例/错误码）；README 技能面一句话。

## 9. 实施与验收记录（2026-10-25）

### 9.1 落地清单

| 层 | 内容 |
|---|---|
| 存储 | `db/database.mjs`：`analysis_results` 表（result_id=run_id PK、run_id UNIQUE、description/summary/summary_json/tags/metadata/intent/scene/harness/score/verdict/user_id）+ 4 索引 + upsertResult（ON CONFLICT 只刷派生字段，description/tags 存活）/listResultsFiltered(JOIN diagnostic_runs：软删过滤+title/category 真源)/countResultsFiltered/updateResultUserFields/deleteResultByRunId |
| 服务 | `services/results-library.service.mjs`：summarizeRun（六意图确定性提取 + **report.md 结论段兜底**——mock 专项运行无 skill 工件时用其自身报告，sources 标 `report_fallback`）、buildResultMetadata（report/html≤8/工件清单≤16/duration/fingerprint）、upsertResultFromRun（不抛错，AC-10）、backfillResults（幂等只增 + 空摘要且无用户描述的行安全刷新）、listResults/getResultDetail（`derived:true` 兜底）/updateResult（SUMMARY_READONLY/归属 403/title 与 category 委托 history 服务） |
| 钩子 | `diagnosis.service` 完成分支（completeRun 后）同步调用 `upsertResultFromRun`——全新/continue/chat-rebuild 单一收口（AC-11）；`index.mjs` 启动回填；`history.service.purgeRun` 同步删结果行 |
| 路由 | `routes/results.routes.mjs`（控制台 /api/results GET/PATCH）+ `external.routes.mjs`（/v1/results GET brief 索引、/:id 详情 include_md、PATCH；capabilities `results_index:true` + 端点清单） |
| 前端 | 新「Results 结果库」页签（`ResultsLibrary.vue`：q/intent/category/tag/sort 筛选 + 扁平表格 + 详情抽屉 + HTML/报告跳转）；`ResultSummaryCard.vue` 共享摘要卡（自动摘要 + key_numbers 溯源 chips + description/tags 原生输入编辑）；History 详情面板内嵌同一卡片；i18n zh/en；api/index.js listResults/getResultDetail/patchResult |
| 测试 | `test/results-library.test.mjs`（22 用例）；mock-e2e 增 AC-10/AC-11 断言；`scripts/e2e/results-api-acceptance.mjs`（36 检查）、`results-agent-workflow.mjs`（三步演示）、`results-ui-check.mjs`（原生输入 14 检查）、`results-ui-screenshots.mjs` / `results-ui-domcheck.mjs` |
| 文档 | `docs/api-external.md` §16（查询表/示例/错误码/Python 配方）；README/README-zh 外部 API 表 3 行；AGENTS.md 一条 |

### 9.2 验收结果（全部实机执行，2026-10-25）

| AC | 结果 | 证据 |
|---|---|---|
| AC-1 完成即落库 | ✅ | mock-e2e「run completes」：完成瞬间 `GET /api/results/:id` 返回 `derived:false`、score 96、report_md 全文 |
| AC-2 回填幂等 | ✅ | 单测两遍 backfill：第二遍 inserted=0/refreshed=0；110 行 0 重复；六意图齐全（单测 + 实库探针） |
| AC-3 索引过滤/brief | ✅ | results-api-acceptance 36/36：q/intent/tag 精确/min_score/score_desc 单调/分页/400 校验/brief 单卡 465 字符 |
| AC-4 详情完整 | ✅ | 837404b0：score 65.8、verdict `C · 波动`、summary_json.sources 全钉到工件字段、report_md 10,690 字符、files.html 带 asset URL、include_md=false 只留 URL、未知 id 404 |
| AC-5 PATCH + 归属 | ✅ | description/tags 修改即时反映；q 命中编辑值；summary→400 SUMMARY_READONLY；超长/空 body→400；未知 id→404；非属主 403（单测）；控制台镜像与外部详情一致 |
| AC-6 读时派生 | ✅ | 单测删行后 `derived:true` 且 score/summary 来自工件 |
| AC-7 可发现性 | ✅ | capabilities `results_index:true` + 3 端点清单；docs/api-external.md §16 |
| AC-8 Agent 三步 | ✅ | results-agent-workflow：list(brief,q=yield)→选 837404b0→detail→引用「评分 65.8；结论 C · 波动」，全部可溯源 sources |
| AC-9 UI | ✅ | results-ui-check 14/14（原生输入：页签渲染/搜索收窄/抽屉/描述 PATCH 往返/标签 PATCH/服务端确认/History 摘要卡/0 console error）；DOM 检查 38/50 行有摘要、无横向溢出；截图 4 张在 workspace/acceptance/2026-10-25/ |
| AC-10 完成即可查 | ✅ | 钩子与终态同一同步路径；摘要失败仅 warn 行仍写（单测 non-completed 拒绝 + mock-e2e 即时读） |
| AC-11 续跑 UPSERT | ✅ | mock-e2e continue 后索引中该 run 恰 1 行；单测 re-upsert 后 description/tags 存活、score 更新 |
| AC-12 软删可见性 | ✅ | 单测软删后索引/详情均 404，restore 恢复 |
| AC-G 全量回归 | ✅ | 后端 **242/242**；Python 5 套 779 检查全绿；前端 build ✓；镜像 `--check` 同步；ui-smoke-native 全过；ui-visual-audit 0 失败（1280 无溢出）；api-contract-final 22/22 |
| AC-13（追加）AWS/AgentWorkShop 集成 | ✅ | `results-aws-integration.mjs` **87/87**：`idd_` API Token 全链路（非会话 JWT）——索引→按 run id 取详情→**直接读取** report.md 全文（字节与 metadata 完全一致）、每个 HTML 报告（200 + text/html + 真实 HTML）、每个工件 JSON（6 意图 35 个文件全部可读可 parse）；`summary_json.sources` 关键数字逐项回溯工件字段；`?token=` 查询串同样可读（iframe/SSE 路径）；PATCH 与 404 语义一致 |
| AC-14（追加）四条需求级验收 | ✅ | `results-requirements-check.mjs`：R1 分类（列出/创建/指派/按分类筛选/详情回显/外部路由同源/恢复）；R2 全部描述（可见结果 0 条空 display_text；描述覆盖自动摘要、清除后回落，q 可检索描述）；R3 按 id 元信息（workspace/report{path,bytes}/html[]/工件清单/时长/引擎/指纹/运行态 + HTML 与 8 工件**全部可直读**）；R4 详细报告（report.md 全文 = 磁盘字节、report_md_url 信封内容一致、HTML 报告可渲染且含真实结论） |
| AC-15（追加）分类 API 管理 + 描述视图 | ✅ | 需求升级轮：结果面分类 CRUD（`GET/POST /api/results/categories`、`PATCH/DELETE /:id`、重名 409、删除清引用不删结果，全部委托 history.service 单实现）+ **分类描述视图** `GET /api/results/categories/:id/results`（每条含 description，未编辑回落 display_text；result_count 与索引/视图三处一致；外部镜像同语义；他人分类 404）——需求级 e2e **42/42**（R1 22 项，含空名校验、第二用户 HTTP 隔离、删分类后结果仍可读），UI 内联建分类（自动切换筛选 + 计数徽标 + 诚实空态）19/19，后端 **246/246（连续 3 轮稳定）** |

### 9.3 实施中发现并修复的缺陷

1. **首屏大量 `--` 摘要**（UI 截图审出）：51 个 mock 专项运行无 skill 工件 → 摘要空。修复：意图工件缺失时回退 report.md 结论段（sources 标 `report_fallback`），回填对"空摘要且无用户描述"行做安全刷新；刷新后仅剩 12 个无 workspace 的测试行为诚实空（DOM 38/50 有摘要）。
2. **结果库「报告」按钮打不开报告**（AWS 集成轮审出）：`ResultsLibrary.openReport` emit `{runId}`，而 App 的 `onOpenReport` 期望 `report_path` 字符串（`runDirFromReportPath` 会得到 `[object Object]`）。修复：从详情 metadata.report_md.path 解析真实路径（复用已加载详情或补一次 `include_md=false` 请求）。
3. **卡片 `has_html` 恒 false**：指数 SELECT 漏选 `a.metadata`，`buildCard` 解析不到 html 数组。修复 SELECT 并加 API 验收断言（837404b0 has_html===true）。
4. **结果库表格缺「分类」列、抽屉内无法指派分类**（需求验收轮发现，P2 计划原本要求分类列）：新增分类列（`results-cat-*`）与抽屉内分类下拉（PATCH category_id，委托 run 行），指派后表格即时回显、分类筛选生效（UI 19/19）。
5. **无工件运行摘要为空**（"查看全部的描述"不成立）：摘要提取无果时给出诚实文案（"该运行未产出可解析的工件/无 workspace，无自动摘要"），不编造结论；118 条结果 0 条空 display_text（DOM 50/50 行有摘要）。
6. **可见性计数**：非 admin 调用方索引总数 97<106 属正确归属过滤（9 行属其他用户），验收阈值相应修正。
7. 其余为测试脚本自身问题（regex/选择器/等待时机、`nativeType` 追加而非替换、`api()` 把 JSON 工件当信封解析、控制台路由 `data` 是数组而非 `data.results`）——非产品缺陷，均已修正脚本。
8. **回填幂等测试在并发套件下 flaky**（ralph 验收轮发现，1/246 偶发）：断言比较了"先取的结果行数"与"后取的完成 run 数"，而 `node --test` 的文件并行会并发完成/软删 dev DB 行。修复：`backfillResults()` 返回自身快照 `examined`，断言改为「各结果之和 = examined」+ 可见域比较用**单条 SQL**（一致性快照）；连续 3 轮 246/246 稳定。

### 9.4 遗留

- `harness-api-acceptance.mjs`（真引擎付费路径）本轮未重跑：完成钩子为纯增量且 mock-e2e 覆盖完成路径；基线 70d2222 时全绿。
- 深度摘要质量（LLM 撰写 interpretation 列）仍为 P2 可选项，未实施（数字可溯源性优先）。
