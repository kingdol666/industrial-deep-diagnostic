# IDD 产线共享与按需记忆服务 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 作业按不可变产线 ID 隔离；授权用户按版本发布、选用经验与数据；诊断 Agent 在运行期间通过只读工具按需检索，不在启动时获得历史正文。

**Architecture:** Express 模块化知识服务封装 SQLite 查询、发布权限和审计；HTTP 与 Claude SDK 的进程内 MCP 调用相同服务。产线身份与作业策略单独持久化，原始证据不变，共享资产是单独发布的版本。可选数据对照走独立加载路径，不走记忆工具。

**Tech Stack:** Node 24、Express、better-sqlite3、SQLite FTS5、Vue 3、Claude Agent SDK、node:test、Playwright。

**Spec:** [产线共享与按需记忆服务设计](../specs/2026-11-26-line-knowledge-service-design.md)。**实际验收与仍关闭的上线能力：** [验收记录](../../line-knowledge-acceptance.md)。

## Global Constraints

- Node 24 / Express / Vue 3 / SQLite；新迁移 append-only；不修改历史原报告或诊断证据；不自动跨线、不自动公开、不发送真实现场数据到未批准的模型；任何无授权或来源不明输入都不进入检索或运行。
- `line_id` 不可变；别名不是权限依据；所有权限检查从已认证主体开始，不接受客户端代填操作者。
- `knowledgePolicy` 包含 `mode: on_demand | disabled`、`own_line: boolean` 和最多 8 个明确版本引用；未绑定旧作业保留查阅，不自动复用。
- `limit` 默认 5、最大 10，摘要最大 240 字、详情最大 1600 字、每次执行尝试最多 20 次调用。
- 启动无历史正文；不支持按需检索的引擎不降级为旧式正文注入。共享运行未验证隔离不开放生产使用。

## Review Focus

1. 同名产线与旧任务的归属不确定性：A 的迁移/权限测试保证同名不串线、未知来源不纳入。
2. 已公开会被误解为可下载或可注入：B 的三种作用域矩阵检查，源 run 文件仍不可访问。
3. 撤权、重跑与历史版本冲突：C、D 测试排队至执行、执行至工具调用，以及失效人工确认不能从自动索引绕回。
4. 中文两字关键词与无结果：C 对照测试同名信号仅返回授权来源，无结果不扩大范围；返回次数、摘要有边界。
5. CLI 的工具能力、Agent 子进程与历史内容可见范围：D、F 验证实际工具握手和文件/凭据边界，而不是把 `mcpServers` 配置存在当作通过。

## 分工与依赖

| 包 | 指派 / 可并行 | 依赖 | 可交付成果 |
|---|---|---|---|
| A · 产线与严格归属 | 后端身份与迁移实现者 | 无 | 产线 API、运行绑定、旧记录待核对、旧全局接口隔离 |
| B · 共享与数据 | 后端发布与数据实现者；A 的接口冻结后可独立编写 HTTP/权限测试 | A | 私有发布草稿、公开与定向授权、版本撤回、数据版本独立授权 |
| C · 知识检索 | 后端知识服务实现者；可与 B 并行先做本线测试 | A，跨线集成需 B | 真实搜索和详情 API、可重建索引、审计和版本来源 |
| D · 引擎工具 | Agent 引擎实现者；可先独立做 SDK 契约测试 | C | 取消初始化正文、运行期工具、能力检查、失败/恢复行为 |
| E · 控制台 | 前端实现者；接口冻结后可先完成界面，随后联调 | A/B/C | 产线管理、发布、引用与检索记录 |
| F · 验收 | 独立验证者 | A–E | API、真实浏览器与引擎证据，按引擎列上线结论 |

下发按依赖分两路，每次最多两个实现任务；每包独立审查。A 先冻结 API 和 schema；并行任务在独立工作树中分开写业务模块，迁移编号、共享路由挂载和启动入口由集成负责人按 A→B→C→D 顺序合入。各任务以下测试命令是**实现后的验收命令**，不是现在已存在或已通过的测试。

### A · 产线域与旧数据迁移

**Files:** add `app/backend/src/services/production-line.service.mjs`, `app/backend/src/routes/production-line.routes.mjs`, `app/backend/test/production-line.test.mjs`; modify `app/backend/src/db/migrations.mjs`, `app/backend/src/db/database.mjs`, `app/backend/src/index.mjs`, `app/backend/src/routes/{diagnosis,external,line-memory}.routes.mjs`, `app/backend/src/services/diagnosis.service.mjs`, `app/backend/test/migrations.test.mjs`.

**Interfaces:** `createLine(actor, { name }) → { line_id, name }`; `requireLineAction(actor, lineId, 'read'|'run'|'manage') → Line`; `requireRunKnowledgeScope(actor, runId) → { run_id, line_id, owner_user_id, knowledge_policy }`. `POST /api/lines` 与 `/api/lines/:lineId/members/:userId` 权限及其它路径按设计。`line_id` 和 `knowledge_policy_json` 在 run 中持久化，不放内存临时 meta；旧行列允许 NULL，不从别名授权。

- [ ] 写真实 SQLite/HTTP 回归：`same_name_lines_remain_distinct`（同人两个不同 UUID）；`legacy_alias_does_not_bind_run`（预览/作业不能通过旧 alias 进入另一线）；`readonly_member_cannot_run_or_grant`；普通用户请求旧全局 `findings`/`proposals` 不返回数据，管理员仍能治理。
- [ ] 跑 `node --test app/backend/test/production-line.test.mjs`，确认缺接口/缺规则失败。
- [ ] 加迁移、目标归属和基于 `production_line_members` 的授权；线管理员确认旧任务归属需权限，处理冲突和旧双所有者字段时使用一个明确的归属判定，不以 OR 自动授权。对 `/api/line-memory` 未改造的全局产线/提案读取逐个加管理员门禁；人工复核等独立接口延续各自 owner 检查，并在 C 移除旧预览旁路。
- [ ] 跑 `node --test app/backend/test/production-line.test.mjs app/backend/test/migrations.test.mjs app/backend/test/human-review.test.mjs`，确认 0 失败。
- [ ] 独立审查迁移和 ACL；若用户授权提交，单独提交该包。

### B · 发布、撤回和独立数据权限

**Files:** add `app/backend/src/services/knowledge-publication.service.mjs`, `app/backend/src/routes/knowledge-publication.routes.mjs`, `app/backend/test/knowledge-publication.test.mjs`; modify migrations、`app/backend/src/index.mjs`、`app/backend/src/services/diagnosis.service.mjs` 以及 `app/backend/src/services/files.service.mjs` 的数据解析接口。

**Interfaces:** `getPublishedVersion(actor, { asset_id, version }, 'read'|'reuse'|'download'|'analyze') → PublishedVersion`; `listCatalog(actor, { kind, q, cursor }) → { items, next_cursor }`; `stageComparisonDataset(scope, versionRef) → approved run-local data handle`. `knowledgePolicy.references` 每项为 `{asset_id, version}`，只包含 `experience` / `memory_excerpt`；`datasetRefs` 另列版本，非提示词内容。目录可见性不用于推导权限，使用显式操作授权；HTTP 对任一未知/不可见版本返回同一 404。

- [ ] 写 API 流程测试：`listed_does_not_grant_reuse`、`read_does_not_grant_raw_dataset`、`withdrawn_version_cannot_be_selected`、`release_cannot_expose_source_workspace`；对照数据从隔离存储按版本解析，不接收客户端路径替代。
- [ ] 跑 `node --test app/backend/test/knowledge-publication.test.mjs`，确认缺功能时红。
- [ ] 实现草稿→发布→撤回，固定版本号、许可范围和授权审计；公开只站内已认证目录，发布与使用权分别配置。将显式数据集选用纳入启动前校验与受控物化，拒绝过期授权或不能安全运行的目标引擎。
- [ ] 重跑该文件及 `app/backend/test/tenancy-isolation.test.mjs`，确认 0 失败。
- [ ] 审查资产响应与错误体不含私有 provenance/文件路径；若用户授权提交，单独提交该包。

### C · 记忆查询服务与溯源

**Files:** add `app/backend/src/services/knowledge.service.mjs`, `app/backend/src/routes/knowledge.routes.mjs`, `app/backend/test/knowledge-retrieval.test.mjs`; modify migrations、`app/backend/src/services/{human-review,line-memory,diagnosis}.service.mjs`、`app/backend/src/routes/diagnosis.routes.mjs`、`app/backend/src/index.mjs`。

**Interfaces:** `searchForRun(scope, { query, signals, limit }) → { items, retrieval_id }`; `getForRun(scope, refId) → { item, retrieval_id }`; `recordCompletedEvidence(runId, completionId)` 为片段投影入口。`scope` 由 A 解析，MCP 额外附可信执行尝试 ID；HTTP pending 是预览，不统计为 Agent 检索。每个 `item` 至少含 `ref_id/source_kind/source_version/excerpt/evidence_level/human_review/applicability`，不带系统路径或源运行私有数据。

- [ ] 写测试：`unselected_and_wrong_line_absent`、`withdrawal_between_search_and_get_denies`、`chinese_two_char_query_does_not_widen_scope`、`ineffective_and_stale_cannot_reenter_via_auto`、`approved_external_reference_is_not_local_observation`、`budget_and_no_hit_are_explicit`。
- [ ] 跑 `node --test app/backend/test/knowledge-retrieval.test.mjs`，确认缺检索行为时红。
- [ ] 用 FTS5 trigram 加受限的短词匹配实现授权集合内查询；根据 A/B 取交集后再排序、分页。补完成谱系：新完成生成单调版本或新 ID，读取时验证最新版本；人工和自动投影同门禁，存量无法确认的记录不复用。事件溯源保存来源版本、结果数量、授权结果与时间；不把原始正文当常规日志。旧 `/review-context` 改为使用新严格服务或对未绑定作业返回空，不保留别名旁路。
- [ ] 重跑检索、人工复核和原产线记忆套件，确认原始文件不被改写、0 失败。
- [ ] 独立审查检索前的授权和来源版本；若用户授权提交，单独提交该包。

### D · Claude MCP 运行期适配及启动行为

**Files:** add `app/backend/src/engine/memory-tools.mjs`, `app/backend/test/memory-tools.test.mjs`; modify `app/backend/src/services/diagnosis.service.mjs`, `app/backend/src/engine/claude-client.mjs`, `app/backend/src/harness/engines.mjs`, `app/backend/src/routes/{diagnosis,external}.routes.mjs`。检查其它引擎所用共享 formatter 无调用路径可意外填入旧历史内容。

**Interfaces:** `createMemoryToolServer(scope) → McpSdkServerConfig`，用 SDK 0.3.251 的 `tool`、`createSdkMcpServer` 与 `query` 的 `options.mcpServers` 绑定 `memory_search`/`memory_get`；`memory_tools` 能力明确声明。外部 CLI 不能序列化内存实例，不列入首阶段承诺。启动前明确选用版本被撤回，给出 `409 KNOWLEDGE_SOURCE_UNAVAILABLE`，用户可重建不含该引用的作业，不替换版本。

- [ ] 写启动与真实 SDK 契约测试：`fresh_prompt_contains_no_memory_excerpt`、`runtime_tool_uses_server_owned_scope`、`queued_revoke_stops_selected_source`、`unsupported_harness_has_no_prefill_fallback`、`resume_rechecks_or_refuses`；模拟供应商用测试接收端，不把测试夹具当真实模型表现。
- [ ] 跑 `node --test app/backend/test/memory-tools.test.mjs`，确认当前启动注入和缺工具行为下红。
- [ ] 新任务不用 `buildStartMemory` 正文；只暴露何时用工具及如何验证先验。MCP handlers 闭包绑定消费者身份及尝试 ID；输入只接受查询字段，不接收用户、产线、凭据覆盖。共享任务只在已验证隔离支持的模式开放；无隔离模式不得将用户的 Broader JWT 传给模型或子进程。CLI 运行在未支持阶段保留 `disabled`，不自动运行工具请求；通用只读 HTTP 仍可服务获批外部集成。
- [ ] 重跑工具、引擎与 API 合约；在验收环境核对事件从 init 到 tool_use/tool_result 的顺序，工具响应经数据标注、无凭据。
- [ ] 引擎与权限复核后，若用户授权提交，单独提交该包。

### E · 前端工作台与共享流程

**Files:** add `app/frontend/src/components/lines/ProductionLineView.vue`, `app/frontend/src/components/lines/KnowledgeReferencePicker.vue`, `app/frontend/src/components/lines/RunKnowledgePanel.vue`; modify `app/frontend/src/{App.vue,api/index.js,i18n/zh.js,i18n/en.js}` 及 `app/frontend/src/components/diagnosis/DiagnosisView.vue`；add `tests/e2e/line-knowledge-ui.py`。

**Interfaces:** 用 A–C 既定 API，作业表单提交 `lineId`、`knowledgePolicy` 和 `datasetRefs`；显示 `未检索 / 已检索` 与每次只读查询来源。组件不自行猜测产线或放行权限。

- [ ] 写 Playwright 流程：建两条同名线→分别建作业→进行一次发布授权→搜索目录并勾选指定版本→在 A 的预览显示 B 获批版本→撤回→已打开的界面刷新后显示不可用；对比目录、预览、实际检索轨迹。
- [ ] 在隔离服务验证脚本在未实现所需界面时失败。
- [ ] 接入产线工作台、资产权限、跨线引用选择、两种独立的数据选择和审计来源视图。保留现有 HITL 编辑、撤回和报告链；复核无效不默认删除历史。
- [ ] 跑 `npm --prefix app/frontend run build` 与 `tests/e2e/line-knowledge-ui.py`，保存关键截图与日志。
- [ ] 独立复核界面表达的授权与实际 API 一致；若用户授权提交，单独提交该包。

### F · 联合验收与发布门禁

**Files:** add `docs/line-knowledge-api.md`, `docs/line-knowledge-acceptance.md`; update `docs/multi-harness.md`、`README.md`、`README-zh.md`。验收数据用隔离目录，截图中不出现真实数据、凭据或路径。

- [ ] 运行真实启动服务的 API 矩阵：同名不同线、同线不同用户、只读无复用、同用户显式跨线、有授权的外部线、发布历史版本、预览后撤权、运行中撤权、模型没调用时无正文、索引重建、空检索和运行再完成。
- [ ] Chrome 实测 E 的全流程，收集产线、公开范围、作业引用选择、Agent 检索轨迹和撤回五个画面。
- [ ] 用已核准的 SDK 凭据和示例产线跑实际引擎：一条需查历史经验的诊断、一条无需历史的对照、一次授权撤回后的检索。验证 trace 中先有真实调用后有结果、启动内容无历史正文、报告标注引用与本线验证，不以服务测试替代真实调用。若 provider/隔离环境阻断，保留功能实现与契约结果，记录相应生产能力未验收。
- [ ] 后端 `cd app/backend && node --test --test-timeout=40000 --test-concurrency=1 test/*.test.mjs`；前端 `npm --prefix app/frontend run build`；仓库根 `node scripts/sync-harness-skills.mjs --check` 与 `git diff --check`。既有独立工具套件变化时补跑对应 skill。
- [ ] 写验收文档和能力矩阵，标明未支持与未验收；独立评审上线闸门。只在得到发布授权后提交/推送，不将沙箱示例误当现场实测。
