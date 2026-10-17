# Plan: DOE 数据分析流程优化（本体优先 · 可执行闭环）

- **Status**: `approved (executing)`（2026-10-17 用户指令批准；Phase 0 已完成，见 `doe-baseline-2026-10-17.md`）
- **Date**: 2026-10-17
- **Repo**: `D:\codes\myskills\industrial-deep-diagnostic`（IDD）
  - **执行工作树**: `D:\codes\myskills\idd-doe-impl`（分支 `feat/doe-ontology-first`，自 `1ff3d6c`；主工作树 421 条并行变更未被触碰）
- **Contract freeze**: `docs/plans/contracts/`（Phase 0 P0-2 交付物；字段级单一权威源）
- **Cross-repo dependency**: `D:\codes\ABO\AgentWorkShop`（平台侧 DOE 实体/执行/回流）
- **Baseline**: IDD HEAD `1ff3d6c`（工作树含未提交改动；开工前必须先冻结并记录 SHA）
- **Authoritative companion**: AgentWorkShop `.AgentWorkShop/analysis/idd-doe-enhancement-plan-v2-2026-10-17.md`
- **Expert review**: AgentWorkShop `.AgentWorkShop/analysis/idd-doe-plan-expert-review-2026-10-17.md`（四席 ACCEPT WITH CHANGES）
- **Scope**: IDD 的 DOE 分析流程（本体优先 → Agent 理解 → DOE 分析 → 可执行结论 → 平台 handoff）；平台集成作为跨仓库工作包单独列出
- **Non-goal**: 本计划不实现硬实时控制、不自动执行试验、不把观测相关升级为因果、不重构诊断主管线

---

## 1. Requirements Summary

| # | 需求（用户原话归纳） | 实现回应 | 验收 |
|---|---|---|---|
| R1 | DOE 分析必须集成深度根因诊断的本体建模 skill | 扩展 `industrial-ontology-builder` 的 `profile=doe`；不另起炉灶；默认 `diagnosis` 行为不变 | OD-01/OD-08 |
| R2 | 先查看是否有相关本体模型 | `doe_ontology_prepare` 先查 store：`profile + scene_key + context_fp`；exact→reuse，同 scene 新列→extend | OD-02 |
| R3 | 没有则先按先验知识创建 | `data_stage=design_only`：只有设计矩阵/因子列也能建；工艺描述+RAG+web+physics prior；响应行为 `NOT_APPLICABLE`；不编造 | OD-03 |
| R4 | 确保 Agent 理解场景和场景数据模型 | `ontology_brief.json/.md`；DOE Phase 0 强制读取并写 `analysis_plan.md`；不读 brief 不得跑统计 | OD-04 |
| R5 | 然后再执行 DOE 数据分析 | 本体 stage 完成后才进入 analyzer；brief 缺失且 mode≠off 时阻断 | OD-05 |
| R6 | 得到所有参数与被优化目标之间的关系 | designed 效应全覆盖 + design-adjusted association 分层；factor×response 矩阵；不把相关当因果 | DS-03/DS-10 |
| R7 | 分析结论指导 AgentWorkShop 优化场景作业 | `optimization_guidance.json` + `platform_ref`（recipe_param/node_id/plc_tag/单位换算/硬限）+ `next_design.json` | OD-11 / XR-03 |
| R8 | 不破坏现有能力 | 现有 136 条 DOE 断言 + 诊断 ontology 语义 + quality gate 全绿 | RG-01/RG-04 |

---

## 2. 现状基线与缺口（代码级）

| 缺口 | 证据 | 影响 |
|---|---|---|
| DOE intent 把 ontology 置空 | `app/backend/src/services/diagnosis.service.mjs:296-310`（创建）、`:913-914`（执行） | 本体永远进不了 DOE |
| builder 要求 DATA_PATH，不能 design-only | `.claude/skills/industrial-ontology-builder/references/agent-protocol.md:18`；`SKILL.md:14-23` | 试验前无法先建本体 |
| DOE skill 0 处 ontology 引用 | `.claude/skills/industrial-doe-analyzer/` grep `ontology` = 0 | Agent 在统计前没有场景语义 |
| 文件选择会选错表 | `scripts/analyze.py:253-261`（`_find_data` 取 `00_input` 排序第一个数据文件；`--data/--context` 已支持，但 agent protocol 未强制） | `doe_context.json`/`run_exclusions.csv` 可能被当数据 |
| PI 用均值 CI 冒充预测界 | `scripts/doestats/effects_anova.py:480-508`（`x0'X⁻¹x0·MSE`，无 `1+`） | 单点达标被高估 |
| designed CI 恒空 | `scripts/doestats/windows.py:284-289` | 下游无法判断效应不确定性 |
| 逐因子边际窗口被当联合域 | `scripts/doestats/windows.py:251-298` | 每个因子取中点不保证多响应同时合格 |
| active 最多 4、9^k 网格 | `scripts/doestats/windows.py:102,185-191` | 取消封顶会指数爆炸；不取消则漏因子 |
| constraints 只回显 | `scripts/doestats/windows.py:647-649` | 安全限不生效 |
| factor_unit 恒 null；响应单位假回退 | `scripts/doestats/effects_anova.py:50-61`、`windows.py:34-36,280` | 单位错误/缺失不可见 |
| fold-over 只有文字 | `scripts/doestats/design_detect.py:199` | 确认实验不可执行 |
| 多响应只归因一个响应 | 真实样例 `workspace/bopet-skill-eval/S2_doe_mdo_ccd/conclusions/recommendations.json`：3 响应只出 2 窗、`ci95=null`、`factor_unit=null`、`confirmations=[]` | 多目标优化不完整 |
| store 无 profile/context_fp | `.claude/shared/scripts/ontology_store.mjs:382-422,538-557` | 同列不同范围/单位/规格会被错误 reuse |
| external API 无 DOE artifact | `app/backend/src/services/external.service.mjs:55-107` | 结构化结论回不来 |
| quality gate 严格 key 白名单 | `scripts/quality_gate.mjs:185-210` | 新增字段会 FAIL |
| 现有测试基线 | `tests/run_tests.py`：18 组 case / 136 断言，2026-10-17 实跑 136/136 | 改造必须保持绿 |

---

## 3. 目标流程（本体优先）

```
00_input/run_table.csv + doe_context.json
        │
        ▼
[Phase A] doe_ontology_prepare（HARD GATE）
  1) context_fp = 列/因子范围/单位/响应规格/设计类型
  2) store lookup(profile=doe, scene_key, context_fp)
     exact → reuse（≤60s）
     same scene/new columns → extend
     miss → full（design_only 可用先验知识）
  3) 01_ontology/ontology.json + ontology_brief.json/.md
  4) CP-2 strict schema + CP-3 clarification
        │
        ▼
[Phase B] Agent 理解
  读 ontology_brief → 写 01_profile/analysis_plan.md
  （场景/因子/响应/单位/预期方向/混杂/局限/分析模式）
  未读 brief 或 plan 缺失 → 阻断
        │
        ▼
[Phase C] DOE analyzer
  designed effects + association screen + ontology consistency
  输出 effect_table / model / association_screen /
       doe_conclusion / recommendations / next_design / optimization_guidance
        │
        ▼
[Phase D] 平台 handoff
  artifact manifest → AgentWorkShop
  optimization_guidance → campaign/optimization channel
  next_design → recipe patch / node setpoints
```

### 3.1 关键设计决策（ADR）

| 决策 | 选择 | 理由 | 备选/被否 |
|---|---|---|---|
| 本体入口 | 扩展 `industrial-ontology-builder`（`profile=doe`） | 复用 RAG/物理/CP-2/store，不复制引擎 | 新建 `doe-ontology` skill：重复、易漂移 |
| 无本体时 | 先验构建（design_only） | 满足“先建本体再分析”；不依赖响应数据 | 等有数据再建：违反硬要求 |
| Agent 理解 | `ontology_brief` + Phase 0 门禁 | 让 Agent 先解释场景/数据模型，再跑统计 | 只写报告：Agent 仍盲分析 |
| 上下文 | 单一 `analysis_context.json` + 显式 `--data` | 避免两套 schema/选错表 | 目录首文件 fallback：已证明会选错 |
| 窗口 | marginal + `joint_setpoint` | 可执行推荐必须多响应同时可行 | 只给逐因子窗口：下游误用 |
| 区间 | 效应 CI / PI / 均值 CI / 容差区间分离 | 防止 PI 冒充 CI/合格率 | 单一 `ci95`：语义混淆 |
| 初始设计 | IDD `design_build`（或 import-only MVP） | 统计设计单一 owner，避免平台自研 | 平台自研：口径漂移/工期爆炸 |
| 兼容 | schema 加法式 v1.1 | 保持 136 断言绿 | 直接 v2.0：破坏下游/测试 |

---

## 4. 数据契约

### 4.1 `00_input/run_table.csv`

一行 = 一个 `run_id`（一次执行）；重复执行是新 `run_id`。

```
run_id,design_point_id,replicate_group,replicate_kind,run_order,block,<factor_1>,...,<response_1>,...
doerun-a1,dp-1,rg-1,replicate,1,1,185,...
doerun-a2,dp-1,rg-1,replicate,2,1,185,...
```

- `design_point_id`：同一因子组合分组。
- `replicate_group`：独立重复分组（纯误差用）；同 block 内。
- `replicate_kind`：`repeat|replicate|center`。
- 响应单元格允许空（未测/失败），缺列拒绝。
- `run_exclusions.csv` 放 `00_input/exclusions/`，不进数据发现目录。

### 4.2 `00_input/doe_context.json`

字段对齐 IDD `analysis_context`，但使用 `col` 命名：

```json
{
  "contract_version": "1.0",
  "experiment_id": "doe-...",
  "line_id": "...", "product_id": "...", "recipe_id": "...",
  "objective": "...",
  "design_type_declared": "ccd",
  "design_region": {"factorial_bounds": {"zone1_temp": [180,220]}, "axial_alpha": 1.414, "design_hull": "ccd_star"},
  "data_file": "run_table.csv",
  "factors": [{
    "name": "zone1_temp", "col": "zone1_temp", "type": "numeric", "unit": "°C",
    "min": 180, "max": 220, "levels": null, "role": "control",
    "expected_sign": "+", "physical_meaning": "...", "ontology_signal": "...",
    "platform_ref": {"recipe_param": "zone1_temp", "node_id": "dw-...", "plc_tag": "...",
      "unit_conversion": 1.0, "rounding": 0.1, "hard_limits": {"min": 185, "max": 215}}
  }],
  "responses": [{
    "name": "thickness", "col": "thickness", "unit": "um", "goal": "target",
    "lsl": 48, "usl": 52, "target": 50, "weight": 1,
    "ontology_signal": "...", "platform_metric_ref": {"node_id": "dn-...", "aggregation": "steady_mean"}
  }],
  "blocks": ["batch"], "covariates": ["ambient_temp"],
  "constraints": [
    {"factor": "zone1_temp", "type": "box", "min": 185, "max": 215, "hard": true, "reason": "安全限", "source": "ontology"}
  ],
  "replicates_col": "replicate_group", "run_order_col": "run_order", "group_col": "run_id", "time_col": null,
  "current_setpoint": {"zone1_temp": 200}, "baseline_source": "platform_recipe|dataset_median",
  "ontology": {"profile": "doe", "mode": "auto", "scene_key": "...", "version": "v3", "data_stage": "design_only|collected"},
  "provenance": {"platform": "AgentWorkShop", "created_by": "...", "created_at": "..."}
}
```

### 4.3 `00_input/analysis_context.json`（唯一上下文）

由 `doe_context_adapter` 生成：

- `data_path: "00_input/run_table.csv"`；
- factors/responses 用 `col`；
- units/goals/limits/constraints/blocks/covariates/replicates/ontology 全部映射；
- 每字段 `assigned_by: user|ontology|auto`；
- 禁止 `analysis_context.merged.json` 作为候选数据；合并结果直接写本文件。

### 4.4 Artifacts

| 工件 | 路径 | 用途 |
|---|---|---|
| ontology | `01_ontology/ontology.json` | 本体 |
| ontology_brief | `01_ontology/ontology_brief.json/.md` | Agent 理解契约 |
| ontology_coverage | `01_ontology/ontology_coverage.json` | 列映射/未匹配原因 |
| data_profile | `01_profile/data_profile.json` | 设计识别/质量 |
| analysis_plan | `01_profile/analysis_plan.md` | Agent 的场景理解/分析计划 |
| effect_table | `02_analysis/effect_table.json` | designed 效应 |
| model | `02_analysis/model.json` | 模型/诊断 |
| association_screen | `02_analysis/association_screen.json` | 全参数相关级线索 |
| doe_conclusion | `conclusions/doe_conclusion.json` | 主结论/证据/本体一致性 |
| recommendations | `conclusions/recommendations.json` | 窗口/联合 setpoint/确认 |
| next_design | `conclusions/next_design.json` | 下一轮布点 |
| optimization_guidance | `conclusions/optimization_guidance.json` | 平台优化 handoff |
| report | `report.md` / `report.html` | 人读报告 |

Artifact manifest（tasks result + external result 同源）：kind/path/url/sha256/schema_version。

---

## 5. 实施步骤（按阶段执行）

> 每个任务有 ID、文件、交付物、验证。按阶段顺序执行；阶段内可并行。

### Phase 0 — 基线冻结与契约（1 周）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P0-1 | 冻结基线：记录双仓库 SHA、工作树、Node/Python/uv 版本；IDD 先提交/分支 | repo | `git rev-parse HEAD` 写入 `docs/plans/doe-baseline-2026-10-17.md` |
| P0-2 | 冻结 `run_table.csv` / `doe_context` / `analysis_context` / artifact schema | 新建 `docs/plans/contracts/` | schema + 示例 + round-trip 测试 |
| P0-3 | 建立 traceability matrix（验收 ID → test case → fixture → 命令） | `docs/plans/doe-traceability.md` | 每项有映射 |
| P0-4 | 强制显式数据选择：`--data/--context` 已支持，改为 agent protocol 必填；`_find_data` 排除 aux（context/exclusions/manifest/README） | `scripts/analyze.py`、`references/agent-protocol.md` | 单测：目录含 context/exclusions 时仍选 run_table |
| P0-5 | 兼容性清单：`quality_gate.mjs` 白名单、schema version、report path | `scripts/quality_gate.mjs`、`schemas/*` | 旧 fixture 136 断言不变 |

**Exit**: 契约评审通过；基线 136/136 可复现；traceability 完整。

### Phase 1 — 本体优先（1.5-2 周，P0 硬门）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P1-1 | builder 增加 `profile=doe` + `data_stage=design_only`；物化三件输入 | `.claude/skills/industrial-ontology-builder/SKILL.md`、`references/agent-protocol.md`、`schemas/` | design-only 夹具可建 ontology，`observed_data_behavior=NOT_APPLICABLE` |
| P1-2 | store 增加 `profile`/`context_fp`；publish/findMatch 过滤 | `.claude/shared/scripts/ontology_store.mjs` | 跨 profile 不复用；context 变化→extend/新版本 |
| P1-3 | `doe_ontology_prepare`：lookup→reuse/extend/full | 新 `scripts/doe_ontology_prepare.py`（或 mjs） | exact ≤60s；miss 走 full；返回 version/brief |
| P1-4 | `ontology_brief.json/.md` 生成 | 新 `scripts/ontology_brief.py` | brief 含 scene/factors/responses/units/relationships/confounders/columns/coverage |
| P1-5 | DOE analyzer Phase 0 门禁：读 brief + 写 analysis_plan | `references/agent-protocol.md`、`scripts/analyze.py` | 无 brief 阻断；有 brief 才 profile |
| P1-6 | DOE intent 本体编排：两处白名单 + 参数 | `app/backend/src/services/diagnosis.service.mjs`、`engine/claude-client.mjs` | `doe-analysis` 带 ontology；生产禁 off |
| P1-7 | 新 orchestrator skill（薄编排） | 新 `.claude/skills/industrial-doe-orchestrator/SKILL.md` | prepare→brief→analyzer→consistency→next_design |
| P1-8 | 一致性与回写 | 新 `scripts/ontology_consistency.py`、`ontology_feedback.json` | checked/matched/not_estimable/contradictions；advisory |

**Exit**: ONT1-ONT5/ONT8/ONT9/ONT13/ONT14 通过；诊断管线回归绿。

### Phase 2 — 统计合同正确性（2 周，P0）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P2-1 | 四类区间语义：效应 CI / PI / 均值 CI / 容差区间 | `effects_anova.py`、`windows.py`、`schemas` | PI 覆盖率 n≥2000 93.5-96.5%；CI 不冒充 |
| P2-2 | `joint_window`/`joint_setpoint`；marginal 只作诊断 | `windows.py`、`recommendations.schema.json` | 多响应同时可行；冲突按标准化效应/desirability |
| P2-3 | 设计域/凸包/leverage；CCD/BBD 不评估未运行角点 | `design_detect.py`、`windows.py` | max_leverage/distance/extrapolation；LHS 最高 medium |
| P2-4 | 约束执行：box/linear/safety，hard/soft | `windows.py`、`rsm.py`、`analyze.py`、schema | 绑定约束测试；hard 0 违例；不可行→no window |
| P2-5 | 单位链：canonical/display/conversion/status | `effects_anova.py`、`windows.py`、schema | 缺失/冲突阻断 actionable window；mm/µm 负例 |
| P2-6 | 多响应 factor×response 矩阵 | `windows.py`、`conclusion_template.py` | 每格 window 或 no_window_reason |
| P2-7 | active/grid 规模：top_k + 连续优化/profile | `windows.py`、`rsm.py` | 8/10/20 active 有界；性能分档 |
| P2-8 | 向后兼容：加法式 v1.1、白名单、grade 拆分 | `quality_gate.mjs`、`schemas` | 136 断言逐条不变；contract_status 独立 |

**Exit**: IDD1-IDD10/IDD12 通过；性能达标；136 断言绿。

### Phase 3 — 全参数关系与下一轮设计（2 周）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P3-1 | association screen：设计调整/边际/held_constant/unmodeled | 新 `scripts/doestats/association_screen.py` | 每非因子×响应；`causal_claim:none`；G8 禁止进窗口 |
| P3-2 | 初始设计 `design_build`：full/fractional/CCD/BBD/LHS/D-optimal | 新 `scripts/doestats/design_build.py` | 分辨率/别名/VIF/power/MDE/随机化/block |
| P3-3 | next_design：fold-over/augment/space-filling/confirm | 新 `scripts/doestats/design_next.py` | 每项含 settings/block/replicate/expected_information |
| P3-4 | optimizer-loop 兼容：只消费 designed+confidence≥medium+已确认窗口 | `.claude/skills/industrial-optimizer-loop/scripts/optcore/windows_seed.py` | rejected_prior 可追踪；O-G1..G8 绿 |
| P3-5 | optimization_guidance 生成 | 新 `scripts/optimization_guidance.py` | platform_ref/constraints/next_design/ontology_basis |

**Exit**: IDD11、LOOP1/LOOP2/LOOP6（IDD 侧）通过。

### Phase 4 — Artifact/API 暴露（1 周）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P4-1 | tasks result + external result 同源 artifact manifest | `app/backend/src/services/diagnosis.service.mjs`、`external.service.mjs` | 12 类工件；path/url/sha256 |
| P4-2 | OMP artifact map 增加 DOE 键 | `app/backend/src/services/omp.service.mjs` | getOmpArtifact 可取 |
| P4-3 | report.md/html 引用 brief/effect/window/joint/next design | `templates/analysis_report_template.md`、`report_html.py` | 章节齐全；hash 可溯 |
| P4-4 | quality gate 覆盖新工件/字段 | `quality_gate.mjs` | G6/G7/G8-G11 绿 |

**Exit**: 外部 API 可取全部 DOE 工件；schema 校验通过。

### Phase 5 — E2E 与验收（1.5 周）

| ID | 任务 | 文件 | 交付/验证 |
|---|---|---|---|
| P5-1 | 合成 fixtures：full/fractional/CCD/BBD/OA/LHS/constraints/multi-response/non-randomized/design-only | `tests/fixtures/doe/` | 每个带 truth.json |
| P5-2 | 单测/门禁：F13-F22 + 负路径 | `tests/run_tests.py` | 全绿；tamper/G8-G11 |
| P5-3 | IDD E2E：design-only→prepare→brief→analyze→next_design | `tmp/` 或 `scripts/e2e/` | 一次跑通，产物可查 |
| P5-4 | 性能/确定性：种子、两次数值一致、内存 | `tests/` | REG4 达标 |
| P5-5 | 文档：SKILL/method_notes/agent-protocol/README | `.claude/skills/...`、`docs/` | 与代码一致 |

**Exit**: REG1-REG6（IDD 侧）通过。

### Phase 6 — AgentWorkShop 集成（跨仓库，4-6 周，单独 owner）

> 该阶段不在 IDD 仓库执行；IDD 通过文件/API 契约支持。完整内容见 AgentWorkShop v2 计划 §6。

| ID | 任务 | 仓库 | 交付 |
|---|---|---|---|
| X-1 | DOE 实体/run/measurement + 导出 + context adapter | AgentWorkShop | `run_table.csv` + `doe_context.json` |
| X-2 | `diag_run` 修复 DOE 默认问题 + ontology 参数 + artifact 回流 | AgentWorkShop | DOE intent 真正生效 |
| X-3 | 原子 `doe_run_start/capture/stop` + recipeVersion 冻结 + HITL | AgentWorkShop | 1 run = 1 RecipeRun/LineRun |
| X-4 | `doe_to_optimization` + campaign/optimization channel | AgentWorkShop | 结论指导优化 |
| X-5 | `/doe` UI + `/analysis` 链接 | AgentWorkShop | 可操作/可审计 |

**Exit**: XR-01/XR-02/XR-03 通过；IDD E2E 与平台 E2E 对接。

---

## 6. Acceptance Criteria（可测）

> 所有阈值必须可复现；P0 = 发布阻断，P1 = 发布门槛，P2 = 后续。完整 56 条见 AgentWorkShop v2 §9；以下为 IDD 主计划的关键集合。

### 6.1 本体（OD）

| ID | 条件 | 阈值/验证 |
|---|---|---|
| OD-01 | DOE 使用 ontology-builder（profile=doe） | DOE run 有 `01_ontology/ontology.json` + `ontology_brief`；不是另起引擎 |
| OD-02 | 先查 store；exact reuse ≤60s | 同 profile/scene/context_fp → `reused`；pipeline event 证明无 RAG/web |
| OD-03 | design-only 先验构建 | 响应空表可建；`observed_data_behavior=NOT_APPLICABLE`；不跑统计 |
| OD-04 | Agent 理解门 | 无 brief/`analysis_plan.md` → 阻断；plan 含因子/响应/方向/混杂/局限 |
| OD-05 | 本体后再分析 | brief 存在才 profile/统计；顺序在 run manifest 中可证 |
| OD-06 | 一致性 | 仅 causal/physical + 可归一化 sign；checked/matched/not_estimable/contradictions |
| OD-07 | 版本钉住 | experiment 记录 ontology version/hash；context 变化→extend/新版本 |
| OD-08 | 诊断回归 | 默认 diagnosis profile 的 ontology 行为/CP-2/输出不变 |
| OD-09 | 映射覆盖 | factor/response 100% matched 或 inferred+reason；0 静默 |
| OD-10 | 报告引用 | 引用 id 存在；允许 `no_ontology_basis+reason`；无编造 |
| OD-11 | handoff | 每个 joint_setpoint/next_design 因子有 platform_ref；可生成 recipe_patch/node_setpoints |

### 6.2 统计（DS）

| ID | 条件 | 阈值/验证 |
|---|---|---|
| DS-01 | 设计识别 | full/fractional/CCD/BBD/OA/LHS 6/6 |
| DS-02 | 效应恢复 | 1000 次 MC；≥2×MDE 符号 ≥99%、power ≥80%；FWER ≤10% |
| DS-03 | factor×response 覆盖 | 每格有 window 或 `not_estimable+reason`；0 静默 |
| DS-04 | 多响应 | 每格 window/no_window_reason；joint setpoint；不按跨单位 delta 选赢家 |
| DS-05 | 约束 | 绑定约束测试；hard 0 违例（1e-9）；不可行→no window；全阶段执行 |
| DS-06 | 单位 | unit 或 missing+reason；mm/µm、°C/K 冲突负例；阻断 actionable |
| DS-07 | 预测区间 | n≥2000；点覆盖 93.5-96.5%；PI 宽>均值 CI；多响应联合覆盖披露 |
| DS-08 | 联合窗口 | 逐因子窗口只作诊断；joint_setpoint 多响应可行 |
| DS-09 | active/grid | top_k + 连续优化/profile；8/10/20 active 有界；性能分档 |
| DS-10 | association screen | 设计调整/边际/held_constant/unmodeled；causal_claim:none；G8 |
| DS-11 | 确认/下一轮 | fold-over/augment/space-filling/confirm 可执行；setpoints 在约束内 |
| DS-12 | 初始设计 | design_build 或 import-only 明确；分辨率/别名/随机化/power |
| DS-13 | 向后兼容 | 136 断言逐条不变；v1.1 加法；contract_status 独立 |

### 6.3 工件/回归（AR/RG）

| ID | 条件 | 阈值/验证 |
|---|---|---|
| AR-01 | artifact manifest | tasks+external 同源；12 类工件；path/url/sha256/schema_version |
| AR-02 | report | report.md/html 含 brief/effect/window/joint/next design；hash 可溯 |
| AR-03 | gate | G1-G11 全绿；tamper 负例 FAIL；无 NaN/Inf |
| RG-01 | 既有测试 | 18 组/136 断言仍绿 |
| RG-02 | 新增测试 | F13-F22 + fixtures 全绿 |
| RG-03 | 确定性 | 同输入两次数值一致（时间戳除外） |
| RG-04 | 诊断回归 | 诊断管线 E2E/ontology 语义不变 |
| RG-05 | 性能 | 100×8×3 ≤60s；1000×10×3 ≤120s；8 active 窗口 ≤60s；内存 <2GB |
| RG-06 | 可复现 | 双仓库 SHA、版本、硬件、命令、输出摘要 |

### 6.4 跨仓库（XR，平台侧）

| ID | 条件 | 阈值/验证 |
|---|---|---|
| XR-01 | `doe_context → analysis_context` | IDD 输出与平台 context 一致；无 auto-infer 兜底 |
| XR-02 | artifact 回流 | 平台拿到 12 类工件；幂等/重试/坏 schema 显式失败 |
| XR-03 | 优化 handoff | `optimization_guidance` 进入 campaign/optimization channel；parent/round 谱系 |
| XR-04 | 执行 | run 窗口内样本 100% 关联 recipe_run_id；HITL/硬限/审计 |

---

## 7. Test Plan

### 7.1 Fixtures（IDD）

| Fixture | 目的 | Truth |
|---|---|---|
| `full_2^4` | 主效应/交互/ANOVA | 效应向量/噪声/显著项 |
| `fractional_resIV` | 别名链/fold-over | 生成元/别名链/镜像点 |
| `ccd_optimum` | RSM/驻点/设计域 | 最优点/Dmax |
| `bbd_multi_response` | 多响应/冲突 | 各响应最优/冲突 |
| `oa_lhs` | OA/LHS 识别 | 设计类型/置信 |
| `constraints_binding` | 约束绑定 | 无约束最优点在约束外 |
| `non_randomized` | 强制确认 | 顺序/确认 runs |
| `design_only` | 先验本体 | 无响应也可建 |
| `ontology_reuse` | store 命中 | 同 context_fp |
| `ontology_contradiction` | 方向矛盾 | 预期符号/机理 |
| `association_confounder` | 混杂 | 设计调整 vs 边际 |

### 7.2 验证命令

```bash
cd D:/codes/myskills/industrial-deep-diagnostic

# 基线/回归
uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/run_tests.py all

# 质量门（替换 <RUN_DIR> 为实际 run）
node .claude/skills/industrial-doe-analyzer/scripts/quality_gate.mjs <RUN_DIR> \
  --skill-path .claude/skills/industrial-doe-analyzer \
  --shared-path .claude/shared

# 本体 store
node .claude/shared/scripts/ontology_store.mjs recommend --scene <scene>
node .claude/shared/scripts/ontology_store.mjs reuse --source <store>/<scene>/vN/ontology.json --run-dir <RUN_DIR>
```

### 7.3 Traceability

`docs/plans/doe-traceability.md` 必须把每条验收 ID 映射到 test case / fixture / 命令 / 证据文件；没有映射不得标记 PASS。

---

## 8. Risks & Mitigations

| 风险 | 影响 | 缓解 |
|---|---|---|
| design-only 本体质量差 | 语义错/置信低 | 工艺描述/RAG/物理先验；低置信 INFERRED；HITL clarification；不编造 |
| full 构建慢 | 阻断分析 | auto：reuse ≤60s；full 异步/仅 debug 可关；报告披露 |
| 9^k 网格爆炸 | 性能不达标 | top_k + 连续优化/profile；max_grid_factors；分档性能 |
| PI/CI 语义误用 | 下游乐观 | 四类区间字段；PI≠合格率；报告/合同显式 |
| 约束未绑定测试空洞通过 | 假绿 | 绑定约束 fixture（无约束最优点在约束外） |
| 新字段破坏 136 断言 | 回归失败 | 加法式 v1.1；白名单同步；逐条断言保留 |
| 双副本/接口漂移 | 行为不一致 | 单一权威源；契约测试；E2E |
| 工期低估 | 延期 | 9-12 周全量；IDD-only MVP 5-6 周；按阶段退出 |
| IDD 工作树未提交 | 冲突 | 开工前分支/提交基线；记录 SHA |
| 平台未就绪 | 无法闭环 | IDD 先支持手工 run_table；XR 工作包单独跟踪 |

---

## 9. Execution Order & Effort

| 阶段 | 工期 | 依赖 | 退出标准 |
|---|---|---|---|
| Phase 0 契约 | 1 周 | 无 | 契约/traceability/基线绿 |
| Phase 1 本体优先 | 1.5-2 周 | P0 | OD-01..OD-05/OD-09/OD-10 |
| Phase 2 统计正确性 | 2 周 | P0 | DS-01..DS-09/DS-13 |
| Phase 3 全参数/下一轮 | 2 周 | P1/P2 | DS-10..DS-12 |
| Phase 4 Artifact/API | 1 周 | P2 | AR-01..AR-03 |
| Phase 5 E2E/验收 | 1.5 周 | 全部 | RG-01..RG-06 |
| Phase 6 平台集成 | 4-6 周 | P4 | XR-01..XR-04 |

- **IDD-only 全量：8-9 周**（可与平台 XR 并行）。
- **IDD-only MVP：5-6 周**：Phase 0 + Phase 1 + Phase 2（PI/CI、单位、约束、joint）+ Phase 3（next_design 最小）+ Phase 4（artifact）。
- **完整闭环：9-12 周**（含平台 XR）。

### 9.1 执行纪律

1. 每个阶段先写/更新 traceability，再写实现。
2. 每个 PR 只动一个验收组；提交信息含验收 ID。
3. 每阶段结束跑全量 136 + 新增；红灯不进入下一阶段。
4. 所有数值由脚本算；Agent 只解释；禁止手改 JSON/HTML。
5. 开工前记录 IDD/AgentWorkShop SHA；IDD 工作树未提交改动先建分支/提交。

---

## 10. Definition of Done

1. **P0 全绿**：OD-01..OD-11、DS-01..DS-13、AR-01..AR-03、RG-01..RG-04/RG-06。
2. **P1 全绿或明确延期**：RG-05；XR-01..XR-04（若纳入本期）。
3. **真实流程**：design-only→prepare→brief→analysis→next_design 一次跑通；产物可查。
4. **零回归**：136 断言 + 诊断 E2E + tool-verify（若平台）仍绿。
5. **文档一致**：SKILL/method_notes/agent-protocol/API 与代码一致；无未证实承诺。
6. **可复现**：双仓库 SHA、版本、硬件、命令、输出摘要、artifact hash 齐全。

---

## 11. Open Decisions（开工前需拍板）

1. **初始设计**：IDD `design_build`（推荐）还是 MVP 只支持 imported matrix；若只导入，UI/文档必须明确“不生成设计”。
2. **HITL 粒度**：批次审批绑定 `design_hash`，还是每 run 一次审批；前者需逐 run 校验 approval_id。
3. **先验知识来源**：工艺描述/RAG 文档是否齐备；缺失时本体只能低置信，需 HITL clarification。
4. **性能硬件**：REG5 的 60s/120s 以哪台机器为准；需固定 runner 规格。
5. **平台集成是否本期**：IDD-only MVP 可先落地；XR 作为下一阶段。

---

## 12. Review Log

- 2026-10-17：四席专家评审（DOE 统计 / 本体知识工程 / 平台架构 / QA 交付）一致 **ACCEPT WITH CHANGES**；6 个 Critical 已在 AgentWorkShop v2 计划中修订，本计划继承其结论。
- 本计划为 IDD 落地版：把 v2 的通用计划收敛到 IDD 可执行文件/阶段/验收；平台侧保留为 Phase 6/XR。
- 评审证据与完整处置表：AgentWorkShop `.AgentWorkShop/analysis/idd-doe-plan-expert-review-2026-10-17.md`。

---

## 13. Readiness Check（2026-10-17，只读预检）→ Phase 0 执行结果（2026-10-17，已执行）

| 检查 | 结果 |
|---|---|
| 计划文件 | `docs/plans/doe-analysis-flow-optimization-plan-2026-10-17.md`（37 条验收 ID） |
| 文档索引 | `docs/README.md` + `docs/plans/README.md` 已登记 |
| omc-plan 注册 | `.omc/plans/doe-analysis-flow-optimization-v1.md`（指针；`.omc/` 被 gitignore） |
| 关键锚点 | 13/13 存在：`analyze.py`、`effects_anova.py`、`windows.py`、`design_detect.py`、`quality_gate.mjs`、`analysis_context.schema.json`、`run_tests.py`、`ontology-builder/SKILL.md`、`ontology_store.mjs`、`diagnosis.service.mjs`、`external.service.mjs`、`claude-client.mjs` 等 |
| 测试基线 | IDD DOE `run_tests.py all`：**136/136 绿**（干净工作树实跑） |
| Traceability | `docs/plans/doe-traceability.md` 已填：37 条全部有 case/fixture/命令/证据映射 |
| 契约冻结 | `docs/plans/contracts/`：README + 3 schema + run_table.md + examples（确定性生成）+ round-trip **28/28 绿** |
| 隔离 | 工作树 `D:/codes/myskills/idd-doe-impl`（`feat/doe-ontology-first`）；主工作树 421 条并行变更未被触碰 |
| 数据入口 | `doe_context_adapter.py` 已实现（MISSING_COLUMN / DUPLICATE_RUN_ID / MISSING_RUN_TABLE / NO_RUN_TABLE 显式失败） |
| 状态 | `approved (executing)` |

### 批准后第一批动作

1. 建分支并提交基线（或记录 SHA）；把 IDD 工作树未提交改动单独提交/隔离。
2. 填 `doe-traceability.md` 的基线与 Phase 0 必填 case。
3. 按 Phase 1 先做 `profile=doe` + `design_only` + `ontology_brief`，再动统计。

