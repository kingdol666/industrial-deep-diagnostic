# Plan: IDD 审计问题复验与修复计划

- **Status**: `executed`（2026-10-18；`OPS-01` + `DEF-01…DEF-12` + `FIX-12` 已修复并验收；`GAP-01/02/03` 保留为需产品决策的设计增强，未在本轮实施）
- **Date**: 2026-10-18
- **Current worktree**: `D:\codes\myskills\idd-doe-impl`
  - Branch: `feat/doe-ontology-first`
  - HEAD: `3b6ae99` (`fix(api): harden file access; test(doe): 12-industry generality + AgentWorkShop E2E`)
  - Working tree: 除本 plan 文件外，仅 `app/backend/src/routes/external.routes.mjs` 有未提交的 `runs_capable` 修复
- **Other worktree**: `D:\codes\myskills\industrial-deep-diagnostic`
  - Branch: `v4-AgentWorkShopIntegrate`
  - HEAD: `1ff3d6c`
  - **当前 3210/5180 端口运行的是这个 worktree，不是当前分支**
- **Verification backend**: 从当前 worktree 启动的 3211（`PORT=3211 AUTH_ENABLED=0`），仅用于本机审计；复验结束后已停止（PID 46880 已终止）
- **Independent reviewer**: 本轮已由独立 Explore reviewer 逐条对照代码复核；修正项见 §9
- **Scope**: 复验上一轮审计中的每个问题，保留真实、可修的问题，剔除幻觉/已修复项，并给出可执行修复计划
- **Non-goal**: 本计划不实现代码修复；不改变产品范围；不做未经确认的架构重构

---

## 0. 复验结论（TL;DR）

| 类别 | 数量 | 说明 |
|---|---:|---|
| 确认的缺陷/运维/契约问题 | 13 | `OPS-01` + `DEF-01` … `DEF-12`，均有代码位置或可复现实验证据 |
| 已修复但未提交 | 1 | `FIX-12`（`runs_capable`） |
| 真实的设计缺口（需产品决策） | 3 | DOE 本体深度、DOE 双驱动深度、产线多源融合范围 |
| 剔除/降级的审计结论 | 6 | 镜像漂移、clone/delete 403、PATCH 422、qwen、多源“完全不可用” |

**最需要先处理的 6 件事：**

1. **OPS-01**：3210/5180 跑的是另一个 worktree，当前分支的功能无法在 UI 上被验证。
2. **DEF-01**：`stop` 返回 stopped，但最终 run 状态变成 failed；且外部 stop 对未知/已完成 run 也会改写状态。
3. **DEF-02**：非 DOE 分析也套用 DOE artifact manifest，稳定报告/快筛结果会列出 13 个“缺失 DOE 工件”。
4. **DEF-03**：同一 `context_fp` 因 scene_key 不同产生重复本体资产，跨 scene_key 的首次复用会 miss。
5. **DEF-12**：任务进度计数器只在非终态刷新，终态任务的 `events/tools` 会停留在 0 或旧值。
6. **GAP-01/02**：DOE 标准流程的本体是“声明先验”，不做 RAG/web enrichment；统计模型也不受本体先验约束——与“自适应本体 + 真正双驱动”的目标存在差距。

---

## 1. 复验方法与证据基线

### 1.1 环境复验

```bash
git worktree list
# D:/codes/myskills/industrial-deep-diagnostic  1ff3d6c [v4-AgentWorkShopIntegrate]
# D:/codes/myskills/idd-doe-impl                3b6ae99 [feat/doe-ontology-first]

# 5180 进程命令行
# node ...\industrial-deep-diagnostic\app\frontend\node_modules\vite\bin\vite.js --port 5180

# 3210 后端日志（other worktree）
# Project root: D:\codes\myskills\industrial-deep-diagnostic
# HTTP + WebSocket server on http://localhost:3210  (2026-10-18T09:31:18Z)
```

> 3210 的命令行本身只有 `node src/index.mjs`，不能单独区分 worktree；**other worktree 的 `.runtime/backend.log` 中 project root 与启动时间**是判别证据。

### 1.2 实跑与测试基线

| 检查 | 结果 | 备注 |
|---|---|---|
| 后端 `npm test` | 150/150 | 本会话早前实跑 |
| DOE analyzer `run_tests.py all` | 199/199 | 本会话早前实跑 |
| AWS capture `test_aws_capture.py all` | 46/46 | 本会话早前实跑 |
| 产线稳定性 `run_tests.py all` | 117/117 | 本会话早前实跑 |
| 哨兵 `run_tests.py all` | 107/107 | 本会话早前实跑 |
| 数据预处理器 | ALL TESTS PASSED | 本会话早前实跑 |
| 当前 worktree 3211 `GET /api/health` | 200 | 审计期间实跑 |
| 当前 worktree 3211 capabilities | `omp runs_capable=true`，其余 false | FIX-12 生效 |
| 当前 worktree 3211 mock quick-screen | completed，`artifacts.present=0`，`missing=13` | DEF-02 复现 |
| 当前 worktree 3211 stop 实测 | stop 200 stopped → 5 秒后 final view `failed` | DEF-01 复现 |
| 当前 worktree 3211 completed run chat | 200 `delivered=true` | DEF-08 复现 |

> 独立 reviewer 复核了代码与关键实测，但没有重跑全部测试套件（避免再次回写 fixtures）；上表计数来自本会话早前的真实运行输出。

---

## 2. 确认的问题登记表

> 约定：**Real** = 已在当前 worktree 复验；**Fixable** = 有明确、低风险的修复路径；**Type** = defect / ops / contract / test / docs / design-gap。

| ID | Sev | Type | 问题 | 关键证据 | Real | Fixable |
|---|---|---|---|---|---|---|
| OPS-01 | P0 | ops | 3210/5180 运行的是另一个 worktree | `git worktree list`；5180 命令行；other worktree 日志 `Project root: industrial-deep-diagnostic` | ✅ | ✅ |
| DEF-01 | P1 | defect | `stop` 返回 stopped，最终状态变 failed；外部 stop 无终态/存在性保护 | 实测 run `7237ed65`：stop 200 → final `failed`；`diagnosis.service.mjs:568`、`:1094-1101`；`omp-client.mjs:267-272`；`external.routes.mjs:266-274` 无 guard | ✅ | ✅ |
| DEF-02 | P1 | defect/contract | 非 DOE 分析套用 DOE artifact manifest | 当前 3211 mock quick-screen：`missing=13`；`artifact-manifest.service.mjs:16-31` 硬编码 DOE 清单；`diagnosis.service.mjs:479` 对所有 run 调用 | ✅ | ✅ |
| DEF-03 | P1 | defect | 同一 `context_fp` 因 scene_key 不同重复入库，跨 scene 复用 miss | `data/ontology_store/index.json` 中 `sha256:5145e3…` 同时挂在 `doe-api-e2e` 与 `bopet-lineA-12um-tdo`；`doe_ontology_prepare.py:213-228` 先按 scene 过滤再匹配 fp | ✅ | ✅ |
| DEF-04 | P1 | frontend | 本体策略选择只在 deep-diagnosis 暴露/发送 | `DiagnosisView.vue:93,101,569-570` 均以 `analysisIntent === 'deep-diagnosis'` 为条件 | ✅ | ✅ |
| DEF-05 | P1 | backend/contract | specialist intent 接受但静默忽略 ontology 字段 | `diagnosis.service.mjs:297-321`：注释明确非默认 intent 不接收 ontology directive；内部 `/start` 透传 `req.body`（`diagnosis.routes.mjs:35`）→ 传了也不报错 | ✅ | ✅ |
| DEF-06 | P1 | skill wiring | 产线稳定性文件夹预处理未接线，文档引用已退役的 HTTP 目录模式 | `SKILL.md:53`；`agent-protocol.md:5-20` 无 preprocessor；`stability_analyzer.py:66-75` 只接受 file/run-dir；`data_preprocessor.py:1118` 的 `--stability-single-primary` 无调用方；backend 无 `line-report` 路由 | ✅ | ✅ |
| DEF-07 | P2 | skill/agent behavior | 单位未声明时 agent 会自行发明单位 | quick-screen `report.md:15,56` 写 `mm/h` / `mm`；运行目录只有 `00_input/user_context.json`，无 unit；输入 `data/sim_line_case/report_context.json` 无 unit；`drift_quantify.json` 无 unit 字段；µm 是从产品名推断，不是声明值 | ✅ | ✅ |
| DEF-08 | P2 | contract/docs | completed run 的 `/chat` 返回 200，文档写 409 | 当前 3211 实测 run `e1e982ba`：POST `/api/external/v1/chat` → 200 `delivered=true`；`docs/api-external.md:207` 写 409；`sendChatMessage` 无终态检查 | ✅ | ✅ |
| DEF-09 | P2 | test harness | `test_aws_capture.py` 不被 pytest 发现 | `pytest ... --collect-only -q` → `no tests collected`；文件只有 `main()`（`test_aws_capture.py:382`）；项目惯用 `run_tests.py` 自定义 runner | ✅ | ✅ |
| DEF-10 | P2 | test hygiene | 测试回写已提交的 fixtures，弄脏 git | `industrial-sentinel/tests/run_tests.py:41,81-90` 指向 tracked `tests/fixtures` 并 rmtree/重建；本会话实测 48 个 tracked fixture 文件 modified；`sync --check` 报 47 个 drift 条目；恢复后全绿 | ✅ | ✅ |
| DEF-11 | P3 | docs | AGENTS.md 技能数量/表格与仓库不一致 | `.claude/skills` 24 个；`AGENTS.md:142` 写 23；表格只有 22 行，缺少 `industrial-doe-orchestrator` 与 `industrial-line-stability-report` | ✅ | ✅ |
| DEF-12 | P2 | defect | 终态任务的 progress 计数器不刷新 | `external.service.mjs:168-190` 只在非终态更新 `progress`；mock run `e1e982ba` 有 21 条持久事件（含 3 tool_use/3 tool_result），task `TASK-MVDO5B27-5QPT` 仍显示 `events=2, tools=0` | ✅ | ✅ |
| FIX-12 | P3 | pending commit | `runs_capable` 修复未提交 | 工作树 `external.routes.mjs:40` 已改为 `capabilities.includes('runs')`；`omp-harness.mjs:24` 含 `runs`；3211 实测 omp=true | ✅ | ✅ |

### 2.1 设计缺口（真实，但不是“代码 bug”）

| ID | Sev | 缺口 | 证据 | 需要决策 |
|---|---|---|---|---|
| GAP-01 | P1 | DOE 本体是声明先验，不是知识型自适应本体 | `doe_ontology_prepare.py:332-525` 的 `build_prior_ontology`，provenance `rag_used=false/web_used=false`（`:520-521`）；真实 store 条目 `semantic_confidence` 全 `INFERRED`；live metrics health 79/C；orchestrator 不 dispatch ontology-builder | 增加 enrichment，还是明确标注“先验本体”范围 |
| GAP-02 | P1 | DOE 不是严格的“模型+数据双驱动” | `analyze.py:643` brief 进入 units block；`:526,530` brief 也进入窗口计算；`doestats/windows.py:739-762` 消费 ontology constraints；但模型项由 `factor_info`/design 构建（`analyze.py:654-656`），`expected_sign` 只在 `ontology_consistency.py` 使用 | 明确“ontology-framed + data-driven + constraints-aware”定位，或增加确定性的本体先验建模 |
| GAP-03 | P2 | 产线报告不自动建本体，也不做跨源/跨采样率融合 | `lstcore/ontology.py:6-87` 发现顺序；`references/agent-protocol.md:9-11` 只建议用户自行建本体；`data_preprocessor.py:1061` 与 `industrial-data-preprocessor/SKILL.md:30` 明确不合并 cadence | 自动建本体 + 单主表范围，还是实现融合 |

---

## 3. 剔除/降级的审计结论（防幻觉清单）

| 上一轮结论 | 复验结果 | 处理 |
|---|---|---|
| “`.agents`/`.hermes` 镜像漂移是真实缺陷” | 运行测试会回写 fixtures，导致 `--check` 报 47 个差异；恢复 fixtures 后 `sync --check` 全绿（532 files identical） | **降级为 DEF-10 测试卫生问题**，不作为镜像缺陷 |
| “`runs_capable` 恒为 false” | 当前工作树已有未提交修复，3211 实测 omp=true | **转为 FIX-12：验证并提交** |
| “本体 API clone/delete 返回 403” | 只在 other worktree 的旧代码/权限模型上出现（其 routes 有 adminOnly）；当前 worktree 3211 实测 clone 201、delete 200 | **剔除**，不是当前分支缺陷 |
| “PATCH quality=validated 返回 422” | 合法枚举是 `unvalidated/endorsed/deprecated/rejected`（`ontology_store.mjs:859`）；前端只传 `endorsed/unvalidated` | **剔除**，是预期行为 |
| “qwen 不可用” | `config/default.yaml:51,59` 的 8 秒 probe 超时；`cli-common.mjs:196` 注释明确 8s 对慢 CLI 会产生 false negative，默认回退 15s | **剔除**，环境/探测配置问题，不是代码缺陷 |
| “mock 进度 events=0 是 mock 行为” | 错。mock 确实产生 3 组 tool_use/tool_result；真正原因是 `external.service.mjs:168-190` 只在非终态刷新 progress | **转为 DEF-12**（真实 minor defect） |
| “产线报告完全不能做多源异构” | 支持多格式、目录发现、辅助源；明确限制是“单主时序表、不跨 cadence 合并” | **改为 GAP-03 范围决策**，不夸大为“完全不可用” |

---

## 4. 修复工作包（PRD 用户故事）

### WP-0 · 环境对齐（P0）

**US-0.1 让 3210/5180 指向当前 worktree**

- **问题**: OPS-01
- **动作**:
  1. 停止 other worktree 的 3210/5180（确认 `activeRuns=0`）。
  2. 从 `D:\codes\myskills\idd-doe-impl` 启动 backend/frontend。
  3. 验证后端日志 `Project root: D:\codes\myskills\idd-doe-impl`，前端进程命令行指向当前 worktree。
  4. 在 UI/本体 API 创建一个临时场景，确认落盘路径是 `idd-doe-impl\data\ontology_store`。
- **验收**:
  - [ ] 3210 日志 project root = `idd-doe-impl`
  - [ ] 5180 进程 cwd/命令 = `idd-doe-impl`
  - [ ] 临时本体落盘到 `idd-doe-impl/data/ontology_store`，删除后无残留
  - [ ] `GET /api/health` 200，DB ok，`activeRuns=0`
- **文件**: 运维脚本/README/`commands/cli.mjs`（如需固定 worktree）
- **依赖**: 无
- **风险**: 停服务前必须确认没有运行中的诊断任务

---

### WP-1 · 运行生命周期与结果契约（P1）

**US-1.1 修复 stop 终态与外部 stop 保护**

- **问题**: DEF-01
- **动作**:
  1. 在 `diagnosis.service.mjs` 增加 `stoppingRuns` 集合（或等价状态）。
  2. `stopDiagnosis` 标记 stopping，关闭引擎，持久化 `stopped`。
  3. `diagnosis.service.mjs:1094-1101` 的错误分支检查 stopping 标记：显式 stop 的 run 不得被覆盖为 `failed`；保留非 stop 的真实失败语义。
  4. `external.routes.mjs:266-274` 增加存在性/终态检查：未知 run → 404；已完成/已失败 run → 409（或返回当前终态，明确不改写）。
- **验收**:
  - [ ] 启动 omp/fake 引擎 → stop → 最终 `status=stopped`，`error` 为空
  - [ ] 非 stop 的引擎崩溃仍为 `failed` 且带错误
  - [ ] stop 未知 run → 404；stop completed run → 409/不变更，且不重写 status
  - [ ] 后端测试新增至少 2 个 stop 生命周期用例
- **文件**: `app/backend/src/services/diagnosis.service.mjs`, `app/backend/src/engine/omp-client.mjs`, `app/backend/src/routes/external.routes.mjs`, `app/backend/test/*.test.mjs`
- **依赖**: WP-0（建议在正确 worktree 上验证）

**US-1.2 让 artifact manifest 感知 analysisIntent**

- **问题**: DEF-02
- **动作**:
  1. 给 `buildArtifactManifest` 传入 `analysisIntent`（或新增 `buildIntentManifest`）。
  2. `doe-analysis` 保持现有 DOE 工件清单；`report`/`analysis_plan` 仍是条件产物（当前 13/15 差异来自条件项）。
  3. 非 DOE intent 不再返回 DOE 的 `missing[]`；返回 `applicable:false` + 该 intent 实际产物（如有），或空清单。
  4. 更新 `docs/api-external.md` 的 artifact 说明。
- **验收**:
  - [ ] quick-screen/stability/deep-diagnosis 的 `result.artifacts.missing` 不再出现 effect_table/recommendations 等 DOE 工件
  - [ ] DOE run 的 `missing` 不包含实际已生成的 report.html/analysis_plan；不硬编码 15/15
  - [ ] 新增 API 契约测试
- **文件**: `app/backend/src/services/artifact-manifest.service.mjs`, `app/backend/src/services/diagnosis.service.mjs`, `app/backend/test/*`
- **依赖**: 无

**US-1.3 统一 completed run 的 chat 契约**

- **问题**: DEF-08
- **动作**: 二选一（需产品确认）：
  - A. 保留 resume 语义：更新 `docs/api-external.md §9`，说明 completed run 可 resume chat；返回 `delivered` 的真实含义。
  - B. 严格 running-only：completed/terminal run 返回 409 `EXTERNAL_CHAT_UNAVAILABLE`，并在 `chatWithRun` 中检查 run 终态。
- **验收**:
  - [ ] 文档与实际行为一致
  - [ ] 新增 completed run chat 测试（200 或 409，按选择）
- **文件**: `docs/api-external.md`, `app/backend/src/services/external.service.mjs` / `diagnosis.service.mjs`
- **依赖**: 产品决策

**US-1.4 终态任务 progress 刷新**

- **问题**: DEF-12
- **动作**: `refreshTask` 在终态分支也更新 `progress`（从 DB 事件/日志聚合 events/tools/phase/last_event），而不是只在非终态更新。
- **验收**:
  - [ ] 终态 task 的 `progress.events/tools` 与 DB 持久事件计数一致
  - [ ] mock 与 omp 各至少 1 个用例
- **文件**: `app/backend/src/services/external.service.mjs`, tests
- **依赖**: 无

---

### WP-2 · 本体资产复用正确性（P1）

**US-2.1 修复 context_fp/scene_key 复用**

- **问题**: DEF-03
- **动作**:
  1. `_lookup` 先做 **跨 scene 的 exact context_fp** 匹配；仅当无 exact 时再按 scene 匹配。
  2. 明确 canonical scene_key：优先 `doe_context.ontology.scene_key`，其次数据推导值；不要让 agent 用 run sceneName 覆盖。
  3. 对已有重复条目提供一次性去重/合并脚本（保留最新、记录 alias）。
  4. 增加回归：同一 context_fp、不同 scene_key 的第二次 prepare 必须 `action=reused`。
- **验收**:
  - [ ] 同一 context_fp 再次 prepare（即使 scene_key 不同）：`action=reused`、`elapsed_ms` ≤ 60s、`rag_used=false`、`web_used=false`
  - [ ] 不再新增重复 index entry
  - [ ] 现有 store 条目可通过迁移脚本合并，且不丢版本
- **文件**: `.claude/skills/industrial-doe-analyzer/scripts/doe_ontology_prepare.py`, `.claude/shared/scripts/ontology_store.mjs`, tests
- **依赖**: 无
- **备注**: 同 scene_key 的复用本来就是 exact；本问题只在“同一 fp、不同 scene_key”时触发。

---

### WP-3 · 前端/后端本体策略（P1）

**US-3.1 前端为 DOE 暴露本体策略**

- **问题**: DEF-04
- **动作**:
  1. `DiagnosisView.vue` 的 ontology 选择从 `deep-diagnosis` 扩展到 `doe-analysis`（可选 stability）。
  2. DOE 发送 `ontologyMode`（auto/full/reuse/extend）和 `ontologyScene`。
  3. 增加 i18n 文案和“扩展”选项（如产品允许）。
- **验收**:
  - [ ] UI 选择 DOE 时可见本体策略
  - [ ] 提交 payload 带 `ontologyMode/Scene`
  - [ ] 前端构建通过；至少一个组件/E2E 测试断言 payload
- **文件**: `app/frontend/src/components/diagnosis/DiagnosisView.vue`, i18n
- **依赖**: DEF-05 的行为定义

**US-3.2 specialist intent 不再“接受但忽略” ontology 字段**

- **问题**: DEF-05
- **背景**: 当前行为是**有意设计**（`diagnosis.service.mjs:297-300` 注释明确非默认 intent 不接收 ontology directive），但 API 接受字段后静默忽略，属于契约不清晰。
- **动作**: 二选一：
  - A. 支持：为 stability/quick-screen 解析 `ontologyScene`，把 `--ontology/--scene` 传给 skill；在 runtime prompt 中加 directive。
  - B. 拒绝：不支持的 intent 传 ontology 字段 → 400 `ONTOLOGY_UNSUPPORTED_INTENT`，文档写明。
- **验收**:
  - [ ] 不再出现“传了但被忽略”的静默行为
  - [ ] 若支持，stability run 的 `condition.ontology.mode/path` 能反映指定场景
  - [ ] 新增 API 测试
- **文件**: `app/backend/src/services/diagnosis.service.mjs`, `app/backend/src/engine/claude-client.mjs`, tests
- **依赖**: 产品决策

---

### WP-4 · 产线稳定性输入与单位（P1/P2）

**US-4.1 接线文件夹预处理**

- **问题**: DEF-06
- **动作**:
  1. 在 stability `agent-protocol.md` Phase 0 增加：输入为文件夹时，先运行
     `data_preprocessor.py --stability-single-primary --recursive`，把规范主表放到 `RUN_DIR/00_input/`。
  2. 删除/更新 `SKILL.md:53` 中已退役的 “HTTP line-report 目录模式” 表述（backend 无该路由）。
  3. 在报告 `data.preprocessing` 记录来源、sha256、选择理由。
- **验收**:
  - [ ] 混合格式文件夹（CSV+XLSX+context）能选出唯一主表并完成分析
  - [ ] 报告 `input_manifest`/`preprocessing` 可追溯
  - [ ] 文档不再引用不存在的 HTTP 端点
- **文件**: `.claude/skills/industrial-line-stability-report/SKILL.md`, `references/agent-protocol.md`, 可能 `scripts/stability_analyzer.py`
- **依赖**: 无

**US-4.2 单位缺失时禁止发明单位**

- **问题**: DEF-07
- **动作**:
  1. 在 `drift_quantify.json` / `stability_report.json` 为每个信号增加 `unit`（可为 null）与 `unit_status`。
  2. agent protocol 增加硬规则：只能引用 `report_context`/ontology/数据声明的单位；未知时写“单位未声明”，禁止写 mm/µm 等猜测。
  3. quality gate 增加“报告单位必须在 JSON/context 中有来源”的检查（可先 warning）。
- **验收**:
  - [ ] 无单位数据：报告写“单位未声明”，不出现 `mm/h`
  - [ ] 有单位数据：报告单位与声明一致
  - [ ] gate 能捕获无来源单位（至少 warning）
- **文件**: `.claude/skills/industrial-line-stability-report/scripts/*`, `sentinel/*`, reports, tests
- **依赖**: 无
- **证据修正**: 运行目录 `202610171701117_sim-line-quick-screen/00_input/` 只有 `user_context.json`，没有 `report_context.json`；输入侧 `data/sim_line_case/report_context.json` 也只在 `spec_limits` 里写数值、没有 unit。µm 是从 `product: "BOPET 12um (simulated)"` 推断，不是声明值。

---

### WP-5 · 本体/双驱动范围（设计决策，P1）

**US-5.1 DOE 本体 enrichment（GAP-01）**

- **问题**: 标准 DOE 流程不调用 `industrial-ontology-builder`，本体是声明先验。
- **选项**:
  - **A（推荐，若目标是“自适应知识型本体”）**: 在 `prepare` 之后增加可选 enrichment：
    - `ontologyMode=full/extend` 时 dispatch `context-builder`（`PROFILE=doe`），执行 RAG/web + 物理先验；
    - 只 enrich `physical_meaning/relationships/confounders/limitations`，不改变已声明列和统计；
    - 重新 publish（`--build-mode extend`），provenance 如实记录 `rag_used/web_used`；
    - 设时间/检索预算，超时降级并记录。
  - **B（最小改动）**: 明确文档与 UI 标注“DOE 本体为声明先验，不做 RAG/web”，移除“知识型自适应”的隐含承诺。
- **验收（A）**:
  - [ ] 至少一个真实 run 的 ontology provenance 显示 `rag_used=true` 或 `web_used=true`（在允许联网时）
  - [ ] 语义覆盖/健康分提升，且 CP-2/quality gate 全绿
  - [ ] 不改变任何统计数字（回归 199/199）
  - [ ] enrichment 超时降级不阻塞分析
- **验收（B）**:
  - [ ] SKILL/README/UI 明确 prior-only 范围
  - [ ] 不再有“自适应构建”的误导性表述
- **文件**: orchestrator SKILL/agent-protocol、ontology-builder、backend prompt
- **依赖**: 产品决策

**US-5.2 DOE 双驱动深度（GAP-02）**

- **背景修正**: 本体并非“只影响 units”。`brief` 还进入窗口计算（`analyze.py:526,530`），ontology constraints 在 `doestats/windows.py:739-762` 参与推荐窗口；但**模型项与效应估计仍完全由数据决定**，`expected_sign` 只在一致性检查中使用。
- **选项**:
  - **A（推荐，最小诚实）**: 文档定义“ontology-framed + data-driven + constraints-aware + advisory consistency”，不宣称联合推理。
  - **B（增强）**: 增加确定性的 ontology-informed modeling：
    - 用 `expected_sign` 预声明主效应/交互项（仍由脚本估计）；
    - 用 ontology units 做编码/单位校验；
    - 把 ontology constraints 作为模型/窗口的硬约束（已有部分）；
    - provenance 记录哪些项来自本体。
- **验收（B）**:
  - [ ] 模型 spec 明确标注 ontology-derived terms
  - [ ] 统计仍由脚本计算，agent 不改数
  - [ ] 回归 199/199；新增至少 1 个用例证明 expected_sign 影响 term spec
- **依赖**: US-5.1 的决策

**US-5.3 产线报告本体自动构建/多源范围（GAP-03）**

- **选项**:
  - **A（推荐）**: 无本体且已声明 scene 时，dispatch ontology-builder（bounded，复用 store）；否则如实 auto。
  - **B**: 保持 auto，明确“首次无本体”的降级说明。
  - **C（较大项目）**: 实现跨源/跨采样率融合（时间对齐、重采样、join 策略、冲突处理）。
- **验收（A）**:
  - [ ] 新场景首次 stability run 能生成并发布本体（或在预算内降级）
  - [ ] 第二次 run 命中 store，`condition.ontology.mode != auto`
  - [ ] 测试 117/117 保持绿
- **依赖**: 产品决策

---

### WP-6 · 测试与文档卫生（P2/P3）

**US-6.1 让 AWS capture 测试可被标准 runner 发现**

- **问题**: DEF-09
- **动作**: 在 `test_aws_capture.py` 增加 pytest 入口（`def test_*` 或 `pytest.main`），或把 `main()` 接入 `run_tests.py`；CI 明确执行。
- **验收**: `pytest .../test_aws_capture.py` 实际运行 46 个断言（或 runner 输出 46/46）。
- **备注**: 项目惯用 `run_tests.py` 自定义 runner，因此这是“测试可发现性”缺口，不是产品缺陷。

**US-6.2 测试不弄脏 git**

- **问题**: DEF-10
- **动作**: 测试输出写 `tmp_path`/临时目录；对必须生成的 fixture 加 `.gitignore` 或改为运行时生成；CI 增加“测试后 git status 干净”检查。
- **验收**: 全量测试后 `git status --porcelain` 为空（本 plan 文件除外）；`sync-harness-skills --check` 绿。

**US-6.3 更新 AGENTS.md**

- **问题**: DEF-11
- **动作**: 技能数 23→24；补 `industrial-doe-orchestrator` 与 `industrial-line-stability-report` 两行；核查 `.omp/agents` 数量。
- **验收**: 表格覆盖全部 24 个技能；计数与 `.claude/skills` 一致。

**US-6.4 提交 runs_capable 修复**

- **问题**: FIX-12
- **动作**: 保留当前工作树 `external.routes.mjs` 修复；增加 capabilities 测试；提交。
- **验收**: 测试断言 `omp.runs_capable=true`、`mock.runs_capable=false`；提交后工作树干净。

---

## 5. 需要产品确认的决策

| 决策 | 选项 | 推荐 | 影响 |
|---|---|---|---|
| DOE 本体深度（GAP-01） | A 增加 RAG/web enrichment / B 明确先验范围 | A，若“自适应知识型本体”是硬目标；否则 B | 运行时间、联网依赖、本体质量 |
| DOE 双驱动（GAP-02） | A 文档定位 / B 本体先验建模增强 | A 先诚实定位；B 作为后续增强 | 统计模型复杂度、可解释性 |
| 产线本体（GAP-03） | A 自动建本体 + 单主表 / B 仅 auto / C 跨源融合 | A+B；C 单独立项 | 首次运行时间、数据工程范围 |
| chat 契约（DEF-08） | A 更新文档支持 resume / B 终态 409 | A（现有实现已支持 resume，DB 有 user_message + assistant reply） | 外部调用方兼容性 |

---

## 6. 执行顺序与完成定义

**建议顺序：**

1. WP-0（环境对齐，必须先做，否则所有 UI 验证无效）
2. WP-1（stop/stop guard、artifact manifest、chat 契约、progress）
3. WP-2（scene_key/context_fp 复用）
4. WP-3（前端/后端本体策略）
5. WP-4（稳定性文件夹预处理、单位）
6. WP-5（产品决策 + 本体/双驱动增强）
7. WP-6（测试与文档卫生）

**每个故事的完成定义（DoD）：**

- [ ] 验收标准逐条有 fresh evidence（测试输出/API 响应/文件路径）
- [ ] 相关测试通过，且无回归（199/199、117/117、107/107、150/150）
- [ ] 不修改统计数字；agent 只解读
- [ ] 文档与行为一致
- [ ] 变更文件在 PR 中列出；必要时加迁移/回滚说明
- [ ] `git status` 干净（本 plan 文件作为交付物单独提交）

**回归命令：**

```bash
# 后端
cd app/backend && npm test

# DOE
.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-doe-analyzer/tests/run_tests.py all
.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-doe-analyzer/tests/test_aws_capture.py all

# 稳定性 / 哨兵 / 预处理
.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-line-stability-report/tests/run_tests.py all
.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-sentinel/tests/run_tests.py all
.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py

# 镜像
node scripts/sync-harness-skills.mjs --check
```

---

## 7. 复验证据附录

### 7.1 环境

```text
git worktree list
D:/codes/myskills/industrial-deep-diagnostic  1ff3d6c [v4-AgentWorkShopIntegrate]
D:/codes/myskills/idd-doe-impl                3b6ae99 [feat/doe-ontology-first]

5180: node ...\industrial-deep-diagnostic\app\frontend\node_modules\vite\bin\vite.js --port 5180
3210: other worktree log: Project root: D:\codes\myskills\industrial-deep-diagnostic
```

### 7.2 DEF-01（stop）

```text
analyze 202 run 7237ed65
stop 200 {"success":true,"data":{"run_id":"7237ed65","status":"stopped"}}
final view status: failed | result error: "Query stopped: omp_process_exit:null"

DB event stream run 7237ed65:
seq2 status stopped → seq3 complete stopped → seq4 stats stopReason=omp_process_exit:null
→ seq5 status failed → seq6 complete failed
```

代码位置：`diagnosis.service.mjs:568-577`（写 stopped）、`diagnosis.service.mjs:1094-1101`（覆盖为 failed）、`omp-client.mjs:267-272`（exit 发 error result）。

### 7.3 DEF-02（artifact manifest）

```text
http 200 status completed
artifacts present: 0 missing: 13
missing kinds: ontology, ontology_brief, ontology_coverage, ontology_feedback,
ontology_consistency, data_profile, effect_table, model, association_screen,
doe_conclusion, recommendations, next_design, optimization_guidance
```

代码：`artifact-manifest.service.mjs:16-31` 硬编码 DOE 15 类；`report`/`analysis_plan` 条件产物（`:87-91`），所以非 DOE 常见 13 个 missing。

### 7.4 DEF-03（重复 context_fp）

```text
DUP context_fp sha256:5145e3a39ae4c103403cf13bd0646a9c9bc7138780497244cbb9a8336f003a19
[{"scene":"doe-api-e2e","version":1,"profile":"doe","stage":"collected","run":"202610171619346_doe-api-e2e"},
 {"scene":"bopet-lineA-12um-tdo","version":1,"profile":"doe","stage":"collected","run":"doe-reuse-check"}]
```

### 7.5 DEF-07（单位）

```text
report.md:15 速率 +0.005418 mm/h；窗口末 12.4001 mm
report.md:56 厚度以约 0.0054 mm/h 上升；+8h 12.4434 mm
运行目录 00_input/: user_context.json（无 unit）；无 report_context.json
输入 data/sim_line_case/report_context.json: 只有 spec_limits 数值，无 unit
drift_quantify.json: signals["薄膜厚度"].unit = undefined
```

### 7.6 DEF-12（progress 计数器）

```text
mock run e1e982ba: DB 持久 21 条事件（含 3 tool_use / 3 tool_result）
task TASK-MVDO5B27-5QPT: events=2, tools=0
代码: external.service.mjs:168-190 只在非终态更新 progress
```

### 7.7 已剔除项

```text
sync-harness-skills --check → All harness skill mirrors are in sync（恢复 fixtures 后，532 files identical）
capabilities → omp runs_capable=true（当前工作树已修复）
current worktree clone → 201；delete → 200
PATCH quality=unvalidated → 200；validated → 422（预期枚举）
```

---

## 8. 范围外/不做

- 不在本计划中实现硬实时控制、自动下发参数、自动执行试验。
- 不把观测相关升级为因果。
- 不重构 9 阶段诊断主管线。
- 不在未确认的情况下引入新的统计引擎或 LLM 计算数字。
- 不修改 other worktree（`industrial-deep-diagnostic`）中的并行变更。

---

## 9. 独立 reviewer 复核与修正记录

| Reviewer 发现 | 处理 |
|---|---|
| DEF-01 遗漏实际覆盖点 `diagnosis.service.mjs:1094-1101` | 已补入证据与修复动作 |
| 外部 stop 无终态/存在性 guard | 新增到 DEF-01 的 US-1.1，作为同一工作包的第二部分 |
| DEF-05 是有意设计，不是“意外忽略” | 改写为“接受但静默忽略”的契约问题，优先选项 B（拒绝）或文档化 |
| DEF-07 引用了不存在的运行目录 `report_context.json` | 改为 `00_input/user_context.json` + 输入侧 `data/sim_line_case/report_context.json`，并说明 µm 是推断值 |
| DEF-11 表格缺两个技能，不是缺一个 | 改为缺少 `industrial-doe-orchestrator` + `industrial-line-stability-report`；表格 22 行 |
| Mock progress 不是“mock 无事件” | 转为 DEF-12，指出 `external.service.mjs:168-190` 的非终态刷新逻辑 |
| GAP-02 “brief 只用于 units”不成立 | 改为“brief 也进入窗口/constraints；但模型项与估计仍由数据决定” |
| DEF-03 “首次复现 miss”需限定 | 改为“仅当第二次 prepare 使用不同 scene_key 时 miss；同 scene 仍 exact” |
| DEF-02 “DOE 15/15”是条件值 | 改为“不硬编码 15/15；report/analysis_plan 是条件产物” |
| 3211 审计后端仍在运行 | 已终止 PID 46880，并更新 header |
| Plan 计数不一致（11/12、6/7） | 统一为 13 个确认问题 + 1 个待提交修复 + 3 个设计缺口 + 6 个剔除/降级 |
| DEF-09 是自定义 runner 约定 | 标注为“测试可发现性缺口”，不称为产品缺陷 |
| DEF-08 可能是 resume 语义 | 保留为契约/文档问题，推荐 A（更新文档） |

---

## 10. 执行结果与验收证据（2026-10-18）

### 10.1 修复清单

| ID | 修复内容 | 验收证据 |
|---|---|---|
| OPS-01 | 停止 other worktree 的 3210/5180，从当前 worktree 启动 | backend 日志 `Project root: D:\codes\myskills\idd-doe-impl`；5180 命令行指向 `idd-doe-impl`；本体临时场景落盘 `idd-doe-impl\data\ontology_store\...`，清理 200 |
| DEF-01 | `stoppingRuns` 状态 + 错误分支不再覆盖 stopped；外部 stop 增加 404/409 保护 | 实测 run `5ed25187`：stop 200 → final `stopped`、error null；重复 stop 409；未知 run 404 |
| DEF-02 | `buildArtifactManifest(runDir, {analysisIntent})`；非 DOE 返回 `applicable:false, missing:[]` | 实测 mock quick-screen：`applicable=false, missing=0, present=0`；单测 9/9 |
| DEF-03 | `_lookup` 先跨 scene 匹配 exact context_fp，再 scene_only | ontology phase1 测试 69/69，新增 `ont-store.cross_scene_exact_reuse` PASS |
| DEF-04 | DOE 暴露本体策略；发送 `ontologyMode/Scene`；新增 `extend` 选项与 i18n | 前端 `npm run build` 成功；`DiagnosisView.vue` 条件改为 deep-diagnosis + doe-analysis |
| DEF-05 | 抽出纯函数 `ontology-intent-guard.mjs`；不支持的 intent 返回 400 | 实测 `ONTOLOGY_UNSUPPORTED_INTENT` 400；单测 PASS |
| DEF-06 | 稳定性协议加入文件夹预处理器步骤；更新 SKILL.md；intent directive 增加 preprocessStep | 单测断言 `data_preprocessor.py` / `--stability-single-primary` / “do not merge files or sampling cadences”；镜像同步 |
| DEF-07 | sentinel/stability 协议加入“单位不得发明”红线；intent directive 增加 unitRule | 单测断言 `unit undeclared` / `never infer mm/µm/°C`；镜像同步 |
| DEF-08 | `docs/api-external.md §9` 改为 resume 语义 | 文档更新；实测 completed run chat 200 |
| DEF-09 | `test_aws_capture.py` 增加 pytest 入口 `test_aws_capture_all` | `pytest ... -q` → `1 passed`；standalone 仍 46/46 |
| DEF-10 | sentinel/DOE 测试改用仓库内临时 fixture 副本；`.gitignore` 加清理兜底 | sentinel 107/107、DOE 199/199；测试后 `git status` fixture 区干净；无残留 `.tmp-fixtures-*` |
| DEF-11 | AGENTS.md 23→24，补 orchestrator 与 line-stability 两行 | 表格覆盖 24 个技能 |
| DEF-12 | `refreshTask` 终态也从 snapshot 更新 progress；phase 增加 `completed` | 实测 mock task：`events=15, tools=6, phase=completed` |
| FIX-12 | `runs_capable` 使用 `capabilities.includes('runs')` | 实测 omp=true、mock=false；仍未提交 |

### 10.2 全量回归

| 套件 | 结果 |
|---|---|
| 后端 `npm test` | **156/156 passed**（新增 6 个测试） |
| DOE `run_tests.py all` | **199/199 passed** |
| Ontology phase1 | **69/69 passed** |
| AWS capture pytest | **1 passed**（内部 46/46 断言） |
| Sentinel | **107/107 passed** |
| Line stability | **117/117 passed** |
| Frontend build | **✓ built in 5.10s** |
| Skill mirrors | `.agents` / `.hermes` 532 files identical |
| Fixture hygiene | 测试后 fixture 区无 modified，无残留临时目录 |

### 10.3 未实施项（需产品决策）

- **GAP-01 / GAP-02 / GAP-03**：DOE 本体的 RAG/web enrichment、DOE 双驱动深度、产线本体自动构建/跨源融合。它们不是本轮可无争议修复的代码缺陷，需要先确认产品范围；计划中的选项 A/B/C 仍然有效。
- **提交**：本轮未执行 git commit（未收到提交指令）；`external.routes.mjs` 的 `runs_capable` 修复与全部改动仍在工作树中。
