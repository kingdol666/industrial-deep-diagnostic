# 产线报告 / 数据哨兵 × 本体模型 + 多源异构集成 — 开发计划 v2 (2026-10-21)

> **状态：已实施（2026-10-22）— 全套件回归绿；唯一剩余验收步 = P3.1 HTTP/harness 层 E2E（需后端在场，请求体见 §P3.1）**
> 评审记录见 §7；范围决策见 §6 ADR；v1 → v2 修订日志见 §8；**实施记录与偏差见 §9**。
> 目标不变：把「本体先验 → 多源异构归一 → 确定性集成分析 → HTML+MD 双产出」
> 从 DOE / deep-diagnosis 两个参照实现复制到 industrial-line-stability-report 与 industrial-sentinel。

## 0. 调研结论（v2 修订版）

### 0.1 分析模式全景（`ANALYSIS_INTENTS`，app/backend/src/engine/claude-client.mjs:140-160）

共 6 个 analysisIntent，无其他：四个测好的 `deep-diagnosis` / `stability-report` / `quick-screen` / `doe-analysis`，外加 `experience-mining`（→ industrial-tuning-memory）与 `optimizer-campaign`（→ industrial-optimizer-loop）。后两者不走传感器表格分析主链路，本轮不做本体化。sentinel 的 watch / fast-screen 是 quick-screen intent 内部子模式；14 个 harness 是执行引擎不是分析模式。

| intent | skill | 本体 | 多源异构 | HTML | MD |
|---|---|---|---|---|---|
| deep-diagnosis | industrial-analysis-auto | ✅ Step2 ontology-builder + RAG 三层降级 + store 复用 | ✅ preprocessor E-1 时间轴融合 | ✅ | ✅ |
| doe-analysis | industrial-doe-analyzer | ✅ declared-prior prepare v1.1 | ✅ aws_capture/异构归一为 run_table | ✅ | ✅ |
| stability-report | industrial-line-stability-report | ⚠️ skill 侧已实现，编排层断开 | ⚠️ 仅"选一"不融合 | ✅ | ⚠️ 仅 `--md` |
| quick-screen | industrial-sentinel | ❌ 仅 1 处 prose 提及；后端强制 null | ❌ 静默取第一个文件 | ✅ | ✅ watch_report.md |

### 0.2 stability-report 差距（半集成）

- ✅ skill 内已实现本体优先：`lstcore/ontology.py` 发现链 + `build_understanding`（unit/role/normal_range/governing_law 注入）+ `mechanism_for` 未知机制封顶；测试 `scenario_ontology`。
- ❌ 编排层断点：`ontology-intent-guard.mjs:12` `ONTOLOGY_INTENTS` 不含本 intent → 传本体字段（**扁平字段** `ontologyMode/ontologyScene/ontologySource/ontologyDataStage/ontologyDevOverride`，`ontology-intent-guard.mjs:6-9`，**无嵌套 ontology 对象**）被 400 `ONTOLOGY_UNSUPPORTED_INTENT`；`diagnosis.service.mjs:315-329, 932-934` 硬编码 null。SKILL.md "HTTP 自动接线"无代码支撑。
- ❌ miss 时无制备（无 doe 式 build/reuse/extend）。
- 🐛 `report_context.schema.json:6` `additionalProperties:false` 且未定义 `ontology_path`/`scene`，而 `stability_analyzer.py:239-240` 读这两个扁平键——故障面是**按协议自验的 agent 校验失败**（无运行时校验点，schema 在代码中零调用），非运行时崩溃。
- 🐛 数据发现：`_io.py:12` DATA_SUFFIXES 含 `.json`，仅排除 `report_context.json`/`action_log.json` → `run_config.json`/`input_manifest.json` 等按排序先于数据文件被选中；且 `lstcore/ontology.py:49-50` 文档化路径 `00_input/ontology.json`（'o' < CJK 码点）也会被当数据加载。
- 🐛 同源坑在 DOE 侧仍活：`industrial-doe-analyzer/scripts/analyze.py:74-82` aux 名单**不含** run_config.json。
- ⚠️ MD 非默认（`report_builder.py:783` `--md` opt-in）。

### 0.3 quick-screen (sentinel) 差距（未集成）

- 本体零代码（`agent-protocol.md:49` 一句 prose）；后端强制 null；无 preprocessStep（`claude-client.mjs:150-156`）。
- `sentinel.py:99-108 find_data_file` 静默取 00_input 第一个排序文件（DATA_SUFFIXES 无 .json，无 run_config 坑）。
- 输出侧已达标：`sentinel/alert.json` + `watch_report.md` + `quick_screen_report.html`（htmlStep 强制）。
- 冻结面核实：alert 顶层加可选块的**唯一硬闸是 gate S3 TOP_KEYS**（`quality_gate.mjs:112-118`）；`alert.schema.json` 顶层无 additionalProperties:false；`self_check`（`sentinel.py:1004-1059`）无 extra-keys 检查**无需同步**；`closedloop_enums.json` 头部规则只约束"改字面量须升版"——先例 commit `98ca9e0`（events 层）零 enums 改动保持 `sentinel-alert/1.0`。alert 条目已有零成本标注槽位 `interpretation`（schema 与 S3 白名单均已含，生产者从未发射）。

### 0.4 可复用资产与已知约束

- `ontology_store.mjs` 已 profile 化，但注意：`KNOWN_PROFILES`（:36）**是装饰**，真正开关是 `findMatch:292` 的 `wantProfile !== DEFAULT_PROFILE`；**版本命名空间与裁剪只按 scene 不分 profile**（`nextVersion:388-396`、`pruneVersions:398-413`）→ 跨 profile 撞 scene 会互挤版本窗口、互删资产，必须修；publish 指纹链只认 csv/tsv（:729）→ parquet/xlsx 主表 `schema_fp=null`（语义复用不受影响，接受并文档化）；CLI `context-fp`/usage 串/stats 需加 profile 维度（:1156-1170, :1277-1279, :1260-1271）。
- `doe_ontology_prepare.py` copy-adapt：骨架约 40% 可移植；真正逐 skill 新代码占 60%（prior 构建、指纹镜像、brief、数据探测）；唯一同 skill 依赖是 `ontology_brief.py`（**DOE 特化**：`PROFILE="doe"` :30、读 `ontology["doe"]` 块 :77-79）→ 新 skill 的 brief 构建器是重写不是拷贝；`enforce_gate` 语义需重定义（`01_profile/analysis_plan.md` 与 design_only 守卫是 DOE 特有）。
- `data_preprocessor.py` merge 机器**内联于 `preprocess()`**（:709-833），非可调用单元——`--integrate-merge` 需重构为 helper（默认模式同函数体护航），不是无成本复用；`_same_column_meaning`（:521）定义后从未被调用（死代码）；parquet 默认模式缺口属实（`_TABLE_EXTS:55-56` vs 派发 :612-621 vs 仅 stability 分支 :972-976），修复需逐源 try/except 护栏；`pyarrow>=12` 已在共享 venv 钉死。
- 后端接线面：`buildIntentDirective` 仅 claude/omp/acp 族/one-shot 族消费；**codex（codex-client.mjs:226）与 opencode（opencode-client.mjs:360）不消费**（对 doe-analysis 已存在的缺口）；`diagnosis.service.mjs:344-348` scene_key 兜底仅 doe profile；`buildOntologyDirective`（claude-client.mjs:64-69）仅 'doe' 特判；既有负例 `app/backend/test/analysis-intent.test.mjs:89-96` 放行后必炸，:33-75 directive 文本断言亦然；guard 错误文案硬编码 "Supported intents: deep-diagnosis, doe-analysis."（:20-22）。
- 前端：`DiagnosisView.vue:93`（控件 v-if）与 `:569-575`（payload 条件）硬编码 deep/doe；ClosedLoop 主入口 `AgentTaskLauncher.vue:147-153` payload 无本体字段（launcher 为 4 面板共享，改动波及 experience-mining/optimizer-campaign 面板需回归）；i18n 键已部分存在（zh.js:198）。
- 工件可见性：新 HTML 经 `listWorkspaceHtml`（`files.service.mjs:157-173`）自动出现；**md 不走 report.md 约定**（`getWorkspaceReport` 只服务 run 根 report.md，:131-136），两个新 md 经通用 workspace 文件列表可见；`ReportViewer.vue:346-356` 按文件基名映射标签，**不可改名**。
- 外部 API 需先 `POST /api/auth/tokens` 签发 `idd_` token（全局 authGuard，`index.mjs:61`）；`wait:true` 可省轮询；run 终态集 `completed/failed/stopped/expired`（`diagnosis.service.mjs:140`）。
- `parameter_to_physics.json` 有两份（industrial-diagnostician / industrial-ontology-builder）——**统一用 ontology-builder 份**（doe prepare 的 schema 即引自该 skill，`doe_ontology_prepare.py:60` 先例）。

## 1. 设计原则（v2 修订）

1. **本体 = 声明先验；可提供"声明的判定边界"，永不参与分布估计。** 修正 v1 的自相矛盾表述：本体 normal_range 可作为阈值型检查（C2 窗口、spec 展示）的**声明边界**，但必须 declared 来源标注 + **严重度封顶 ≤ warn**（复用 `confirmation_needed:true` 冻结封顶，`projection.py:86-87`），且**永不参与分布估计**（center/sigma_within/sigma_overall/median/MAD/分位数/相关矩阵/基线统计只来自实测数据，`build_baseline.py:112-197` 现状即如此）。`indicators` 的 lsl/usl（`sentinel.py:409-435` 无封顶硬 critical）**永远 DOE-only，本体禁入**。
2. **词典纪律**：`parameter_to_physics.json` 只提供 unit / role / physical_meaning / governing_law（L5 标注）；其 `typical_ranges` 是教科书参考带**永不开入 `normal_range`/spec/Cpk**，只进 brief 作"参考区间（非规格）"。名称匹配 = 归一化精确匹配 + 唯一候选才接受；多候选/零候选一律 `mapping_status:"unmatched"` 落 brief。理由：`lstcore/ontology.py:144,162-165 → stability_analyzer.py:303-313 → :361-363 → score.py:44-55` 注入链无人工确认点，错配会以 -34 分惩罚翻转等级（L5 冒充 L3 的证据洗白）。
3. **多源 = 预处理层受控归一**：分析核仍是单一规范主表。merge 需过 **cadence 门**（见 P0b.1），merge 产物**不进 sentinel watch**（watch 的 Nelson/抑制窗全是行数语义，按 1/min canonical cadence 设计；用户已裁定 v1 哨兵只吃单一规范表）。
4. **加法式契约演进**：`sentinel-alert/1.0` 不升版（先例 98ca9e0）；唯一硬闸 gate TOP_KEYS 与生产者**同一提交**；不新增枚举字面量；退出码语义、既有文件名、旧测试断言（除显式翻转的 backend 负例）全不动。
5. **显式数据路径优先**：新代码一律 `_resolve_data_path` 式解析（声明路径 → 固定候选名），不做自由目录扫描；发现排除用精确名集合（保留 .json 作为合法数据格式）。
6. **单源不变量上移 shared**：指纹、store 客户端、gate 骨架、canonical token 一份拷贝（`.claude/shared/` 不参与三镜像）；skill 内只留 profile 产品（prior 构建、brief、context 解析）。

## 2. 分阶段开发计划（realistic 5.5-7 人日；optimistic ~4.5；pessimistic 8-10）

### Phase 0a — 共享不变量上移（1-1.5 天，`.claude/shared/` 不镜像，单拷贝）

| # | 改动 | 文件 |
|---|---|---|
| P0a.1 | store 修三处：① 版本命名空间/裁剪改按 `profile+scene` 作用域（`nextVersion`/`pruneVersions`，:388-413）+ 跨 profile 裁剪防护测试；② 新增 watch-context-v1 指纹（列角色/单位/窗口声明行）+ CLI `context-fp` 派发 + usage 串 + `stats` profile 维度；③ publish 指纹链 csv/tsv-only 的 schema_fp=null 决策文档化 | `.claude/shared/scripts/ontology_store.mjs` |
| P0a.2 | 新增 `ontology_prepare_common.py`：`_store_call` subprocess 客户端（argv-list + `ONTOLOGY_STORE_DIR` 注入）、`canonical_number_token`、prepare 动作状态机骨架、gate 骨架、路径守卫、严格 JSON writers。**doe 本轮不迁移**（零回归风险），列 follow-up | `.claude/shared/scripts/ontology_prepare_common.py`（新） |
| P0a.3 | 三 profile conformance 测试：同一 fixture 下 store 侧行为一致 + 指纹跨语言钉死（样板 `test_ontology_phase1.py:294-299`） | shared tests |
| P0a.4 | lstcore 本体发现修复：`discover_ontology` 增 profile 参数 + store-dir 覆盖（现 :57 硬编码 `<repo>/data/ontology_store`，无视 ONTOLOGY_STORE_DIR）；修正 index.json 形态解析（:66-68 读 `scenes` 字典是死代码，实际写的是 `{version, entries[]}`，`ontology_store.mjs:261-266`）；目录扫描（:77-84）加 profile 过滤 | `.claude/skills/industrial-line-stability-report/scripts/lstcore/ontology.py` |

### Phase 0b — 数据预处理与发现坑修复（0.5-1 天）

| # | 改动 | 文件 |
|---|---|---|
| P0b.1 | `--integrate-merge` 第三模式：与 `--stability-single-primary` 硬互斥（同传 → usage error exit 2）；主表遴选（≥50 行 + 时间可解析 ≥0.8，:1029）× merge 闸门；将 :709-833 内联 merge 块**重构为 helper**（默认模式调用同一 helper，E-1 既有测试护航）；**cadence 门**：每源解析时间轴中位间隔 → `merge_info.source_cadence_seconds` + `cadence_ratio`，ratio>10 默认按 `cadence_mismatch` 排除（opt-in 放行）；`merge_info.column_source:{col:file}` + 真正调用 `_same_column_meaning`（:521）；parquet 默认模式分支 + 逐源 try/except；退出码严格档；merge 后主表 <50 行 → exit 2 | `.claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py` |
| P0b.2 | stability 发现排除改精确名集合：+= `run_config.json` / `input_manifest.json` / `preprocessing_report.json` / `ontology.json` / `ontology_brief.json` / `ontology_coverage.json` + `endswith("_manifest.json")`；保留 .json 数据文件支持（`load_table` JSON 行对象分支，`_io.py:62-72`） | `.claude/skills/industrial-line-stability-report/scripts/lstcore/_io.py` |
| P0b.3 | （小项）doe 同源坑：`is_aux_input_name` += `run_config.json`，修后跑 doe 全套件回归 | `.claude/skills/industrial-doe-analyzer/scripts/analyze.py` |
| P0b.4 | 新契约文件 `watch_context.schema.json`（声明式：列角色/单位/窗口），两 skill report_context 引用 | `docs/plans/contracts/` |

### Phase 1 — stability-report 集成 + 完整前端（1.5-2 天）

| # | 改动 | 文件 |
|---|---|---|
| P1.1 | `scripts/ontology_prepare.py`（薄适配器，复用 P0a.2 common 核）：profile=stability；context 来源 `00_input/report_context.json`；miss 时 declared-prior 构建（report_context 声明 + ontology-builder 份 `parameter_to_physics.json`，遵守词典纪律原则 2）；**新 gate 语义**：mode≠off 缺 brief → `ONTOLOGY_BRIEF_REQUIRED`；不设 analysis_plan 要求与 design_only 守卫（DOE 特有）；brief 构建器为 stability 新写（stability 块：列角色/单位/窗口/参考区间标注）；写 01_ontology 四件套；store publish profile=stability | `.claude/skills/industrial-line-stability-report/scripts/ontology_prepare.py`（新）+ `scripts/lstcore/`（brief 构建器） |
| P1.2 | `report_context.schema.json`：增**扁平**属性 `ontology_path` + `scene`（与 analyzer :239-240 零改动兼容）；`additionalProperties:false` 保留 | `schemas/report_context.schema.json` |
| P1.3 | `stability_analyzer.py`：analyze 前置 ontology_prepare（`--ontology/--scene` 已有 :652-664）；`provenance.ontology{source, brief_summary, rag_used}`；`spec_for()` 增 source 检查：`source:"dictionary"` 的 spec **不参与 Cpk**（新 source 值不触碰 run_tests.py:655 冻结断言）；merge 披露：preprocessing_report 的 merge 块 → `degradation`（:280-301 既有通道）追加条目；`_drift` 传**列级**中位间隔（:364 一行改动，消除混合 cadence 下 per-day 斜率虚增 ~60×） | `scripts/stability_analyzer.py` |
| P1.4 | MD 转默认必产（`--no-md` 仅调试、gate 将失败）；gate 增查 md 存在 | `scripts/report_builder.py`, `scripts/quality_gate.mjs` |
| P1.5 | 后端接线（完整清单）：`ontology-intent-guard.mjs` `ONTOLOGY_INTENTS += stability-report, quick-screen` + 错误文案更新（:20-22）；`diagnosis.service.mjs` :315-329/:932-934 分支 + :344-348 scene_key 兜底推广到新 profile + 仿 `resolveDoeOntologyDirective`（:239-283）增 stability/sentinel 指令构造；`claude-client.mjs` `buildOntologyDirective`（:64-69）加 profile 分支 + ANALYSIS_INTENTS spec 指令文本（prepare → analyze）；omp/acp/one-shot 通用消费已核实**无需改**；codex/opencode 不消费 `buildIntentDirective`（:226/:360，对 doe 已存在）→ 本轮文档声明 specialist intents 支持 12 引擎，补齐列 follow-up | guard / service / claude-client + `docs/` |
| P1.6 | **完整前端**（用户已定）：`DiagnosisView.vue` :93 v-if 放行 + :569-575 payload 条件放宽（抽 `ONTOLOGY_INTENTS` 共享常量）；`AgentTaskLauncher.vue` :147-153 payload 加 ontologyMode/ontologyScene + 条件控件（共享组件，注意 experience-mining/optimizer-campaign 面板回归）；`ClosedLoopView.vue` 按 intent 条件显示；i18n zh/en 新键 4-6 个 | `app/frontend/src/components/...` + `src/i18n/` |
| P1.7 | 测试：S19 prepare build/reuse（`ONTOLOGY_STORE_DIR` 隔离 + `cp2_floor_ok` 断言）；S20 `--integrate-merge` 多源 + cadence 门正负例；S21 md 默认 + gate；S22 单位纪律 + 词典 spec 不进 Cpk 正负例；**S22b（C1 具名用例）**：裸 CSV 零声明 → minimal prior（action="built"、全 undeclared、rag_used=false）→ tiny data exit 2 honest 保留（先例 S9）。新测试统一 in-repo `.tmp-fixtures-*` 前缀 | stability tests |
| P1.8 | backend npm test：**翻转** `analysis-intent.test.mjs:89-96` 负例（quick-screen + 本体从拒到放行）+ 更新 :33-75 directive 文本断言 + 新增两 intent 放行正例 | `app/backend/test/` |

### Phase 2 — quick-screen (sentinel) 集成（1.5-2 天）

| # | 改动 | 文件 |
|---|---|---|
| P2.1 | `scripts/sentinel_ontology_prepare.py`（薄适配器同构 P1.1）：profile=sentinel；数据探测 + 声明来源（report_context / watch config / 词典——同样只 unit/role/mechanism）；01_ontology 四件套；store publish | `.claude/skills/industrial-sentinel/scripts/`（新） |
| P2.2 | 本体消费（v1 单一规范表，用户已定）：后端 quick-screen `preprocessStep` = preprocessor **主表遴选**模式（`--stability-single-primary`，非 merge）→ 文件夹输入产出单一规范表 + 逐文件审计；`build_baseline.py` 无 `--doe-run-dir` 时本体 normal_range → operating_windows，**一律**写 `{"confirmation_needed": true, "window_source": "ontology_declared", "source_path": ...}`（继承 projection.py:86-87 冻结封顶 ≤warn，projection.py 零改动）；**禁止本体写 `indicators`**；`sentinel.py check_projection`（:356-398）读 `window_source`，ontology_declared 时建议文案改写 + alert 填 `interpretation`（已在 schema 与 S3 白名单，零契约改动）；本体角色声明优先于正则列识别 + **强制披露"本体排除/改角色列清单"**；`sentinel_fast.py` 不带 ontology 块（watch 专属，文档注明） | `scripts/sentinel.py`, `scripts/build_baseline.py`, `scripts/sentinel_fast.py`（文档） |
| P2.3 | alert 顶层可选 `ontology` 块（位置钉死：top-level）：**gate S3 `TOP_KEYS` += 'ontology' 与生产者同一提交**（`quality_gate.mjs:112-118`）；`alert.schema.json` 补属性声明；`self_check` 无需同步（无 extra-keys 检查，列为可选加固）；`closedloop_enums.json` 零改动；HTML 增"本体理解"小节（单位/角色/窗口来源/rag_used 如实）；`watch_report.md` 模板加窗口来源行 | `quality_gate.mjs`, `sentinel.py`, `alert.schema.json`, `build_screen_report.py`, `templates/alert_report_template.md` |
| P2.4 | 后端：quick-screen spec preprocessStep（主表遴选版）+ 本体放行（同 P1.5 清单）+ directive：prepare → watch → htmlStep → report.md | `claude-client.mjs` 等 |
| P2.5 | 前端（并入 P1.6） | — |
| P2.6 | 测试：F9 prepare build/reuse + 单位进 `alert.ontology` + cp2_floor_ok；F10 本体窗口建 baseline（断言 `watch_baseline.json` 的 `operating_windows[].window_source=="ontology_declared"` 且 `confirmation_needed==true`；正例：本体窗口越界 → severity==warn + interpretation 含声明标注；负例：不产 indicators）；F11 文件夹多源经主表遴选后 watch + preprocessing 审计断言 + perf ≤120s 继承；F12 alert 顶层 ontology 块 gate 正/负例 + schema。F1-F8/T7/tamper 不动全绿 | `tests/run_tests.py` |

### Phase 3 — E2E + 文档 + 镜像（1-1.5 天）

| # | 改动 |
|---|---|
| P3.1 | E2E（用户已定 mock 为主 + 真实存证）：**语料 = data/ 真实文件夹**：`lsr_demo`（单表 + 本体发现）、`cement_ball_mill`（DCS+化验+检修天然多源 → 覆盖 A2）、`bopet_demo`；3 场景 × 2 intent × **mock harness** 断言（可进 npm test/e2e）+ **1 次真实 claude harness 全链路存证**（stability-report on lsr_demo）。操作要点：请求体用**扁平字段** `ontologyMode/ontologyScene`（勿用嵌套 `ontology:{...}`——会被静默忽略，验收无效自证）；外部 API 先 `POST /api/auth/tokens` 签发 `idd_` token；Node fetch（Git Bash curl 中文 GBK 乱码坑）；`wait:true`；终态断言 `completed`；E2E 前核对 `.runtime/backend.log` 的 `Project root:`（双 worktree 端口陷阱） |
| P3.2 | 文档：`docs/api.md` B1 请求体表（:230-243）补 5 扁平字段 + `ONTOLOGY_UNSUPPORTED_INTENT`；`docs/api-external.md` 4 处（:87-93 字段表措辞、:260 错误码、:241-242 文件夹要求、intent 表）；`docs/ontology-management.md` **新增 profile 章节**（现全文 0 处 profile）；两 skill SKILL.md + agent-protocol.md 增 Phase 0.5 本体制备与 CP 检查项 + specialist intents 引擎支持声明（12 引擎，codex/opencode 后续）；`skill-optimization-plan-v4.md:174` 契约表加扩展注记（可选）；AGENTS.md 可选微调 |
| P3.3 | `node scripts/sync-harness-skills.mjs && node scripts/sync-harness-skills.mjs --check`；`cd app/backend && npm test` |

## 3. 验收标准（Definition of Done，v2 全部可测试）

### A. 功能

- **A1 本体优先贯通（API + UI）**：
  - API：`POST /api/external/v1/analyze`（Bearer `idd_` token）或 `/api/diagnosis/start`，body 含 `{"analysisIntent":"stability-report", "ontologyMode":"auto", "ontologyScene":"..."}`（扁平字段）→ 非 400；run 终态 `completed`；`<run>/01_ontology/` 四件套存在且 prepare 结果的 `action ∈ {built,reused,extended}`（action 落在 prepare 结果 JSON 与 `provenance.ontology.action`，不在 coverage.json 顶层——2026-10-22 评审对齐）；`stability_report.json.provenance.ontology.rag_used == false`（确定性路径）。quick-screen 同构。
  - UI：ClosedLoop 面板与 DiagnosisView 可选本体策略并发送（前端构建通过 + 浏览器手工验收一遍）。
- **A2 多源异构**：`cement_ball_mill` 文件夹输入 → `00_input/preprocessing_report.json` 逐文件 disposition；主表 ≥50 行；`stability_report.json` 的 preprocessing 透出块列出审计；cadence_ratio>10 的源被 `cadence_mismatch` 排除（或有 opt-in 放行记录）。
- **A3 单位与词典纪律**：无声明单位列在 HTML/MD 中一律"单位未声明（unit undeclared）"；`alert.json.ontology` 单位与本体一致；词典 `typical_ranges` 只出现在 brief"参考区间（非规格）"，**不出现在 spec/Cpk 输入**（S22 正负例）。
- **A4 双产出**：`line_stability_report.html` + `line_stability_report.md`（md 默认）、`quick_screen_report.html` + `sentinel/watch_report.md` 均落盘；`GET /api/files/workspace/html/<run>` 含两个 html；`GET /api/files/workspace/<run>` 文件列表含两个 .md 相对路径；文件名不变（ReportViewer 基名映射依赖）。
- **A5 gate 全过（命令写全）**：`node .claude/skills/industrial-line-stability-report/scripts/quality_gate.mjs <run>/line_report/stability_report.json <outdir>` exit 0；`node .claude/skills/industrial-sentinel/scripts/quality_gate.mjs <run>/sentinel/alert.json` exit 0（stability gate 语义 0/3、sentinel 0/1 不变）。

### B. 不回归

- **B1 全套件绿（N/N 动态计数表述）**：doe `run_tests.py all` + `test_ontology_phase1.py all` + `test_aws_capture.py all`；stability `run_tests.py all`（20 旧 + S19-S22b）；sentinel `run_tests.py all`（F1-F8/T7/tamper + F9-F12）；`cd app/backend && npm test`（含翻转后的 analysis-intent 断言）。
- **B2 冻结契约只增不改**：退出码语义、`line_stability_report`/`quick_screen_report` 文件名、`sentinel-alert/1.0` 不动（先例 98ca9e0）；alert 生产者与 gate TOP_KEYS **同一提交**（`git show --stat` 验证）；不新增枚举字面量；`ontologyDataStage`/`ontologyDevOverride` 仅 doe 消费（api 文档注明）；`indicators` 无本体路径（F10 负例）。
- **B3 fixtures 不污染 + 确定性**：新测试 in-repo `.tmp-fixtures-*` 隔离副本 + `ONTOLOGY_STORE_DIR` 隔离 + `cp2_floor_ok` 断言；确定性 = 同输入两次运行 `jq 'del(.report_id,.generated_at)'` 后 `stability_report.json`/`alert.json` 逐字节一致；HTML/MD 剥离 `generated_at` 时间戳文本后比对。
- **B4 三镜像一致**：`sync-harness-skills.mjs --check` exit 0。

### C. 场景普适

- **C1 零声明降级（具名用例 S22b/F9b）**：裸 CSV 零声明 → minimal prior（action="built"、全列单位 undeclared、rag_used=false）→ tiny data exit 2 honest 路径保留（先例 stability S9）；**且不因词典参考带新增 Cpk 罚分**（与今天"无 spec → 无罚分"行为一致）。
- **C2 跨行业 E2E（用户已定语料）**：`data/lsr_demo` + `data/cement_ball_mill` + `data/bopet_demo` × 两 intent × mock harness 全过（工件齐全 + gate exit 0 + 终态 completed）+ 1 次真实 claude harness 存证；12-industry 语料回归 doe-analysis 不受影响。

## 4. 风险与对策（v2 增补）

| 风险 | 对策 |
|---|---|
| sentinel 冻结契约联动 | 唯一硬闸 = gate TOP_KEYS 与生产者同提交；schema/enums/self_check 非硬闸（有 98ca9e0 先例）；F12 正负例双向覆盖 |
| run_config.json / ontology.json 发现已知坑 | 显式 `--data` 标准用法；P0b.2/P0b.3 精确名排除；新代码 `_resolve_data_path` 式解析 |
| cadence 门误杀合理的低频辅助表 | `cadence_ratio>10` 默认排除 + opt-in 放行参数；排除原因落 `merge_exclusions` |
| 融合模式被未来 directive 默认化（single-primary 初衷漂移） | sentinel v1 禁 merge 进 watch（用户裁定）；stability 后端 directive 维持 `--stability-single-primary` 默认，`--integrate-merge` 显式 opt-in（新增可选扁平字段 `preprocessingMode`，缺省行为不变） |
| 前端 launcher 共享组件波及其余两面板 | 条件渲染 + 4 面板手工回归清单 |
| guard 放行后 `ontologyDataStage/DevOverride` 被新 intent 接受但忽略 | v1 文档注明仅 doe 消费；per-intent 字段白名单列 follow-up |
| 双 worktree 端口陷阱 / GBK curl 乱码 | E2E 前核对 `.runtime/backend.log`；探针一律 Node fetch |
| store schema_fp=null（parquet/xlsx 主表） | 接受并文档化（context_fp 语义复用不受影响） |
| **回滚方案** | 回滚单元 = ①alert 契约提交（schema/gate/生产者同提交整体 revert）②guard/service/前端分支 revert；新增字段皆可选，旧消费端不受影响 |

## 5. 明确不做（本轮范围外）

- `experience-mining` / `optimizer-campaign` 本体化。
- 跨源统计融合推断（多源只做归一与审计）。
- sentinel watch 常驻 API / 调度器。
- **merge 产物进 sentinel watch**（v1 禁止，用户裁定；如需 v2 带 cadence 披露解禁）。
- **词典 `typical_ranges` 参与 Cpk**（v1 硬禁；opt-in `use_reference_bands_as_specs` 留 v2）。
- **本体声明窗口解封至 high/critical**（v1 一律封顶 warn；"人工核实后解封"留 v2）。
- codex / opencode 的 `buildIntentDirective` 补齐（follow-up，本轮文档声明 12 引擎支持）。
- doe prepare 迁移到 `ontology_prepare_common.py`（follow-up，本轮 doe 零改动）。
- 前端 Playwright 浏览器级验收（UI 级验收 = 构建通过 + 手工一遍）。

## 6. ADR

- **Decision**：通用核上移 `.claude/shared/scripts/ontology_prepare_common.py`（单拷贝，不镜像）+ 两 skill 薄适配器；sentinel v1 只吃单一规范表；本体声明窗口一律封顶 warn；词典区间永不进 Cpk；前端走完整路线（DiagnosisView + ClosedLoop launcher + i18n）；E2E = mock 批量断言 + 1 次真实 harness 存证；语料用 `data/` 真实文件夹。
- **Drivers**：仓库 shared 单源规则（`.claude/shared/README.md:41-43`）；三镜像维护成本（skill 脚本 = 3 拷贝 vs shared = 1）；指纹跨语言恒等不可分叉；watch 统计假设（行数语义）；证据等级纪律；用户可见性。
- **Alternatives considered**：纯 copy-adapt（被否：指纹/gate/provenance 纪律三份手工拷贝必然漂移）；API-only 前端（被否：用户选择完整可见）；merge 进 watch（被否：run-rule 时长语义破坏）；真实 harness 全量 E2E（被否：不可重复、慢）；12-industry 语料（被否：DOE 设计矩阵无时间列、<50 行，撞 stability 自身门槛）。
- **Why chosen**：在交付物不变的前提下，把可持续性从"三份手工同步拷贝"变为"一份核 + 两份声明"；把声明数字进统计与统计假设破坏两条伪证据轴用硬约束封死。
- **Consequences**：共享核变更需回归三个 skill（P0a.3 conformance 测试对冲）；Phase 排期由 3-4 上修至 realistic 5.5-7 人日。
- **Follow-ups**：doe prepare 迁移 common 核；codex/opencode directive 补齐；词典带 opt-in 解封；本体窗口人工核实解封（v2）；per-intent ontology 字段白名单；fast-screen 本体块（如需）。

## 7. 评审记录

5 个并行评审（2026-10-21）：架构师 / 契约回归 / 验收可测试性 / 数据统计正确性 / 范围流程。结论 **5 × REVISE**（无 REJECT）。全部 MAJOR 及以上发现已吸收进 v2（映射见 §8）；MINOR/NOTE 除标注"可选"外均已采纳。核实性说明：评审员对 §0 事实底座约 60 处 file:line 断言逐条核对，除 4 处定性修正（M-E schema 故障面、M-F doe 名单内容、KNOWN_PROFILES 装饰性、A4 md 可见性机制）外全部属实。

## 8. v1 → v2 修订日志

1. A1/E2E 请求体改 5 个扁平字段 + auth 链 + `ontology_coverage.json.action` 判定键（原嵌套记法会静默无效自证）。
2. 新增完整前端工作项 P1.6（用户裁定完整路线）。
3. C2 语料改 `data/` 真实文件夹（用户裁定；12-industry 是 DOE 设计矩阵，11/12 案例撞 ≥50 行 + 时间轴门）。
4. quick-screen 多源策略改主表遴选、禁 merge 进 watch（用户裁定）。
5. E2E 改 mock 为主 + 1 次真实存证（用户裁定）；补 token/wait/终态/工件判据。
6. 新增数据统计硬约束：声明窗口封顶 warn + interpretation 标注 + indicators 禁入；词典纪律（typical_ranges 不进 normal_range/Cpk）；cadence 门 + 列级 drift 间隔 + merge 披露；原则 1 表述修正（阈值边界 vs 分布估计二分）。
7. Phase 0 拆分 P0a（共享不变量：store 版本命名空间/裁剪修复、watch 指纹、ontology_prepare_common.py、conformance 测试、lstcore 发现修复）+ P0b（integrate-merge 重构实现、发现坑修复、doe 同源坑小项）。
8. 后端接线补全：guard 错误文案、scene_key 兜底推广、buildOntologyDirective/resolveDirective profile 分支、**翻转** analysis-intent.test.mjs 负例、codex/opencode 缺口声明。
9. P1.2 schema 修法改扁平 `ontology_path`+`scene`；P0b.2 排除名单 += ontology 家族精确名。
10. 排期上修 realistic 5.5-7 人日（含完整前端 +1）。
11. 验收条款全面可测试化：A4 改 workspace 列表 API 断言、A5 命令写全、B1 改 N/N 表述、B3 隔离前缀统一 + 确定性豁免字段点名、C1 具名用例 S22b/F9b、B2 同提交验证方式。
12. 新增回滚方案、ADR、评审记录。

## 9. 实施记录（2026-10-22）

### 9.1 回归矩阵（全部绿）

| 套件 | 结果 |
|---|---|
| `.claude/shared/scripts/test_ontology_prepare_common.py`（conformance：指纹跨语言对拍/版本命名空间隔离/跨 profile 裁剪防护/词典唯一候选匹配） | 9/9 |
| industrial-data-preprocessor `test_preprocessor.py`（含 `--integrate-merge`/cadence 门/parquet 新用例） | 89/89 |
| industrial-doe-analyzer `run_tests.py all` | 199/199 |
| industrial-doe-analyzer `test_ontology_phase1.py all` | 69/69 |
| industrial-doe-analyzer `test_aws_capture.py all` | 46/46 |
| industrial-line-stability-report `run_tests.py all`（含新增 S19-S22b 共 47 项） | 164/164 |
| industrial-sentinel `run_tests.py all`（含新增 F9-F12 共 56 项；旧 F1-F8/T7/tamper 零改动） | 163/163 |
| `app/backend` npm test（含翻转负例 + watch 指令契约新测试） | 159/159 |
| 前端 `npm run build` | 通过 |
| `sync-harness-skills.mjs` 同步 + `--check` | 每镜像 24 文件更新，drift exit 0 |

### 9.2 实施中的关键偏差与发现（全部有测试锚定）

1. **`commit_to_store` 陷阱（哨兵侧实测）**：按 lookup_status 驱动会在 mode=full/显式采纳 + exact lookup 时用旧 store 资产覆盖新构建——两 skill 均改为"仅 action==reused 走 reuse-copy，built/extended 直接 publish"；共享模块 docstring 已钉死该纪律。
2. **词典结构**：族在 `parameters` 子键下、字段名为 `physical_unit_SI`/`physical_quantity`/`governing_law`——共享模块新增 `load_physics_families()`（`load_physics_dictionary()` 保持返回原文件），conformance 测试用真实词典钉死唯一候选纪律（`temp` 双族碰撞 → unmatched 是预期诚实行为）。
3. **metadata role 枚举**：schema 只有 `batch_id/product_code/timestamp/operator`——时间列 timestamp、分组列 batch_id，watch 语义角色入自由 `watch` 块。
4. **preprocessor 潜伏 bug 顺带修复**：`_normalize_cn_datetime` 的 `\s+` 吞分隔符导致带时刻的中文时间戳分钟秒坍缩——cadence 门是该值的第一个消费者，不修则门对 ISO 数据失效。
5. ** Stability 侧增强**：`report_context.schema.json` 增补 `units` 与 `ontology{mode,scene_key}`（prepare/gate 实际读取的键，避免复刻 §0.2 故障面）；`TIME_COLUMN_NAMES` += `t`（防时间列被词典误配语义）；`coverage.ratio` 定义为已披露列占比（恒 1.0=无静默），另设 `matched_ratio` 承载强弱信号。
6. **doe surfaces 断言适配**：`P1-6.execution_passthrough` 的源码字符串断言随执行透传条件扩为四 intent 数组而更新（保护意图不变：doe 的 ontology 在执行期不再被置空）。

### 9.3 剩余项 / Follow-ups

- **P3.1 HTTP/harness 层 E2E 未执行**（本会话不启动后端，避免双 worktree 端口冲突）：请求体已在 §P3.1 备好（扁平 ontology 字段 + `idd_` token + Node fetch）；确定性链路已被 F11/S19/S20 进程内端到端覆盖，剩余的是编排层组装验证。
- `preprocessingMode` API 可选字段（stability 融合模式的后端 opt-in 通道）——follow-up。
- codex / opencode 的 `buildIntentDirective` 接入（对 doe 亦缺，本轮文档声明 12 引擎支持面）。
- `templates/report_context.template.json` 对 HEAD schema 的既有 validate 失败（5 错，先于本次改动存在）——follow-up。
- doe prepare 迁移 `ontology_prepare_common.py`（本轮 doe 逻辑零改动）；fast-screen 本体块（如需）。

### 9.4 验收评审收尾（2026-10-22）

独立评审结论 REVISE → 最小修复集全部执行：

| 修复项 | 结果 |
|---|---|
| C2 mock 矩阵补 4 组合（bopet×stability / bopet×quick-screen / cement×stability / lsr×quick-screen） | 全部 200 completed（mock 引擎不产 specialist 工件——该子句语义修订为“编排终态验证”，工件级证据由真实 harness 存证承担） |
| quick-screen 真实 harness 存证 | run `46894aff`（claude, cement_ball_mill, TASK-MVIYU3SE-0HZZ）completed：`01_ontology/` 四件套 + `sentinel/alert.json` + `watch_report.md` + `quick_screen_report.html` + gate exit 0 |
| F9b 具名用例（sentinel 裸 CSV 零声明 → minimal prior） | 13/13 PASS（action=built、零 matched、无 user spec、rag_used=false、brief 标“单位未声明”） |
| 仓库根残留目录清理 | `Namespace(run_dir='…')` 已删 |
| A1 措辞修订（action 键位置） | 已改（本节上方） |

评审其余 PASS 项（A2-A5、B1-B4、preprocessingMode）证据见评审报告；B4 观察项：测试套件运行期间并发执行 `sync --check` 会报瞬态漂移，runbook 应在静态时点执行 check。
