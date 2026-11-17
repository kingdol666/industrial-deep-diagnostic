---
name: industrial-improvement-advisor
description: "产线优化改善指导 skill：给定一份生产数据 + 用户优化目标（目标模糊时由确定性脚本从数据推断并回显），一次性产出分级改善行动清单——每一条建议同时携带数据证据链（滞后CCF/分层/LOO/BH-FDR 可复算统计量 + 95% CI 预期收益区间）与物理机理链（本体机制边锚定），外加前提条件、验证方案与数值化回滚条件，以及企业可直接阅读的中文 HTML 落地页（结论先行、证据水位线前置披露、A/B/C 分级）。建议成立三重门（数据门/物理门/归因门）全部由脚本 exit code 判定：A 可立即执行（干预性证据）/ B 需小试验证（自动产 optimizer_seed.json 一键升闭环）/ C 仅方向参考 / 处方区（补数据与试验处方，绝不编造）。PURE-ANALYSIS：绝不下发参数、绝不写 optimizer_state。Trigger: 优化建议, 改善建议, 产线改善, 怎么调参数, 优化方案, 改善方案, 提升良率, 降低能耗, 减少波动, 稳定产线, 提高Cpk, 产线指导意见, improvement advice, optimization recommendation, actionable tuning guidance, what should we do next — even if they only paste a CSV and a goal. Negative boundary: 根因诊断 → industrial-diagnostician；稳定性评分报告 → industrial-line-stability-report；实时增量告警 → industrial-sentinel；多轮布点寻优闭环 → industrial-optimizer-loop；历史动作效果归因 → industrial-tuning-memory；DOE 试验数据分析 → industrial-doe-analyzer；纯结果库管理 → 平台 Results API。"
---

# Industrial Improvement Advisor（产线优化改善指导）

一句话：把"这份数据 + 我的目标"变成一份**每条建议都有数据证据链与物理机理链、预期收益带 95% CI、带验证方案与回滚条件、按 A/B/C 分级的改善行动清单**，以及一份企业全员可读的中文 HTML 报告。全部数值与分级由 `imacore` 确定性脚本计算（零 LLM、零网络），agent 只做中文解读，数值字段不可触碰。

## 设计原则（house rules）

1. **确定性优先**：每个数字、每个分级、每次目标推断都由脚本 + exit code 裁决；agent 只能追加中文 `interpretation` 字段。
2. **"数据+物理"必须可校验**：落成**三重门**（数据门/物理门/归因门）的门禁代码——软约束就是没有约束。
3. **诚实产出**：收益不可估就写不可估（effect=null + reason_code）；处方优先于编造的建议；`not_actionable` 是合法终态（exit 2）。
4. **严在数值，不严在产出**：B/C 级建议照常展示但强制携带降级原因 + 补数据处方标签；A 级三重门一个不让；单份报告 A 级 >3 条 = gate FAIL（门禁 bug 哨兵）。
5. **复用=单一事实源**（Critic 核证的 import 地图）：滞后 CCF/分层/LOO ← `industrial-data-processor/scripts/stats/core_stats.py`（`full_lag_ccf:279` / `_simpson_paradox_check:381` / `_leave_one_out_leverage:186`）；BH-FDR/Welch+AR(1)/OLS ← `industrial-doe-analyzer/scripts/doestats/_stats_util.py`（`bh_adjust:9` / `welch_delta_ci:31` / `effective_n:69` / `ols_fit:104`）；动作归因状态机 ← `industrial-tuning-memory/scripts/tune_stats.py`（attribute 子命令）；工况分段/Theil-Sen/Mann-Kendall ← lstcore；外推护栏 ← optimizer-loop O-G3 逻辑；枚举 ← `closedloop_enums.json` + python 镜像。**零新统计算法**：本 skill 的新代码只有编排 + 门禁 + 渲染。
6. **纯分析边界**：顶层 `mode:"advisory"`、每条 action `advisory:true`、HTML/MD 页脚免责声明、绝不写 optimizer_state、绝不产生可下发文件；执行策略归产线审批 / AWS 侧。
7. **本体优先**：Phase 0.5 本体制备（`scripts/ontology_prepare.py`，profile=improvement），机理链必须锚定本体机制边；本体 unknown → 封顶 C 并打 `[MECHANISM_UNKNOWN]`。**无方向声明不造因果边**。

## 定位

```
输入：  生产时序表（CSV/TSV；≥50 行）× 优化目标 objective.json（显式，或模糊 → 脚本推断回显）
协同：  doe 操作窗（--doe-run-dir，可选）· 动作日志归因（--action-log，可选）· line-memory 共识先验（L5 注入）
输出：  <run>/advisory/advisory_actions.json     建议清单（contract improvement-advisory/1.0）
        <run>/advisory/objective_resolved.json   目标回显（显式镜像 / inferred 候选）
        <run>/advisory/optimizer_seed.json       B 级 top-1 序列化为 optimizer-loop objective（一键升闭环）
        <run>/advisory/charts.json               图表数据束
        <run>/advisory/improvement_advisory.html 自包含中文落地页
        <run>/advisory/improvement_advisory.md   中文 Markdown 伴随报告
        <run>/advisory/html_selfcheck.json       HTML 自检
        <run>/02_evidence/                       dose_response / window_check / attributions
        <run>/01_ontology/                       本体四件套（Phase 0.5 制备）
退出码：0 有建议且门禁全过 | 1 有建议但含降级/not_estimable 证据腿 | 2 not_actionable（处方清单输出）| 3 输入/objective/门禁失败
```

三条铁律：
1. **确定性**：分级、收益、机理链全部来自脚本；agent 只能写 `interpretation`。
2. **诚实性**：数据撑不起动作 → exit 2 + 处方（补什么数据/做什么试验），绝不编造。
3. **咨询边界**：建议是 advisory，绝不构成下发指令（HTML 页脚声明）。

## 建议成立三重门（frozen v1，详见 references/method_notes.md）

- **门 A · 数据门**：杠杆有变异（非时间不变量）· 样本达标（基线≥10 有效点；AR(1) 有效 n 披露）· 方向证据四条件——滞后 CCF 显著且峰落在 dead-time 内（dead-time 缺省 → `not_assessable`，**禁止假设 0 放行**，相关动作 cap B）／BH-FDR 后显著（族=每 KPI 内全部 (杠杆×滞后) 对）／分层+LOO 后效应仍在／C3 工况分段后方向不翻转。
- **门 B · 物理门**：本体机制图谱存在 参数→KPI 边且方向一致（known 可冲 A；same_domain 封顶 B；unknown 封顶 C + `[MECHANISM_UNKNOWN]`）；与 line-memory 反方向共识冲突不得晋级。
- **门 C · 归因门**：动作日志必须归因；estimable 且 CI95 不跨 0 可冲 A；direction_uncertain/truncated/not_estimable 封顶 C；无动作日志时观察数据最高 B。

**分级**：A 可立即执行（三重门全过 + 干预性证据：归因 E2+ 或设计试验工作窗）· B 需小试验证（门 A+B 过、收益 CI 不跨 0、纯观察外推；产 optimizer_seed.json）· C 仅方向参考 · 处方区（触发清单 8 条，见 method_notes）。**推断目标未确认 → 全建议 cap B**。

**五陷阱防护**：混杂（分层+LOO）· 时滞错配（dead-time 限定 CCF 峰）· 反向因果（lead-lag 不对称 → 参数入 `excluded_levers` 永久禁用）· 区间选择偏差（脚本固定全窗+分段复算）· Goodhart（全受影响 KPI 方向披露，任一显著恶化 → tradeoff 声明 + cap B）。双目标方向冲突 → `conflicts[]` 声明 + 受影响动作封顶 C，绝不隐式加权合成。

## 预期收益（诚实算法，全部带 95% CI）

优先序：①分箱剂量响应（等频箱，箱数=min(8,⌊n/8⌋) 且 ≥5、每箱 n≥8；OLS 斜率+CI，Theil-Sen 交叉核对，Mann-Kendall 单调性）②工作窗对照（窗内外 Welch+AR(1) 有效 n）③归因增量（tune_stats delta）。四情形写 `not_estimable`+reason_code、effect=null。外推越包络（编码距离>0.8 或触界，O-G3 同款）→ 只许 C 级 + "未验证"标注。B/C 产出上限 12 条。

## HTML 报告结构（企业阅读顺序）

1. **目标卡**：显式/系统推断标注 + 候选依据 + **证据水位线**（本次数据可支撑的最高分级路径：归因腿/本体机制覆盖/dead-time/设计窗）
2. **改善路线图总览**：优先级矩阵 + A/B/C 分区（证据区/advisory 区）+ 冲突声明区
3. **动作卡 ×N**：杠杆/幅度/收益 CI/机理链/证据引用/前提/验证与回滚条款
4. **证据链附录**：剂量-响应图、窗对照、归因表（内联 SVG，零 CDN）
5. **执行与验证计划**：小试步骤 + optimizer_seed 交接说明
6. **数据与口径**：sha256、行范围、方法与阈值、假设与局限、复用降级如实披露
7. **页脚咨询免责**：复用 stability 页脚声明组件

## Modes

| Mode | 入口 | 输入 | 退出码 |
|---|---|---|---|
| 显式目标 | `improvement_analyzer.py analyze --run-dir` + `00_input/objective.json` | 数据+目标契约 | 0/1/2/3 |
| 模糊目标 | 同上（缺 objective.json 或 targets 为空） | 数据（目标脚本推断并回显） | 0/1/2/3 |

## Inputs / Outputs

| 文件 | 角色 |
|---|---|
| `schemas/objective.schema.json` | 目标契约（targets/constraints/horizon/dead_time/levers 可选） |
| `schemas/advisory_actions.schema.json` | 建议清单契约 `improvement-advisory/1.0` |
| `templates/objective.template.json` | 目标填写模板 |
| `scripts/ontology_prepare.py` | Phase 0.5 本体制备 CLI（profile=improvement） |
| `scripts/improvement_analyzer.py` | 核心分析 CLI（写 02_evidence/ + advisory/ JSON） |
| `scripts/imacore/` | 确定性内核（_io/objective/levers/evidence/actions/rank/chains/charts） |
| `scripts/report_builder.py` | HTML 落地页 + Markdown 伴随报告 |
| `scripts/quality_gate.mjs` | 交付门禁 S1 schema / S2 诚实性+重算比对密封 / S3 zero-LLM / S4 HTML+MD 自检 / S5 共享枚举 + advisory 边界 + A>3 哨兵 |
| `references/agent-protocol.md` | agent Phase 0-4 执行协议（agent 模式必读） |
| `references/method_notes.md` | 钉死常量与判定规则表（逐字值来源） |

协同输入（全部可选，缺席自动降级并记录 `degradations`）：
- `--doe-run-dir <doe_run>`：操作窗（`conclusions/recommendations.json` operating_windows）→ 窗对照腿 + 设计窗判定（仅 design_type ∈ 设计试验且 confirmation_needed=false 才构成 A 级窗路径）
- `--action-log <action_log.json>`：调 `tune_stats.py attribute` 归因 → 门 C
- line-memory 共识：以 L5 先验注入（agent 上下文），与 ≥3 独立观测反方向冲突 → 处方触发⑤

## Dispatch（调用卡）

```
任务：产线优化改善指导
RUN_DIR=<run-dir>                      # 00_input/ 放数据文件（可选 objective.json / action_log.json）
SKILL_PATH=<path-to-.claude/skills/industrial-improvement-advisor>
SHARED_PATH=<path-to-.claude/shared>
```

读 `references/agent-protocol.md` 并执行 Phase 0-4。硬约束：
- Phase 3 的 `quality_gate.mjs` 必须 exit 0（not_actionable 产物按 exit 2 语义放行）才算完成；修复 = 重跑脚本，禁止手改数值产物，最多 3 轮。
- exit 2（not_actionable）不是失败：向用户说明缺什么数据/做什么试验，不伪造建议。
- 报告语言中文；JSON 枚举字段保持英文。

## Verification

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-improvement-advisor/tests/run_tests.py all
# 期望：ALL GREEN
node .claude/skills/industrial-improvement-advisor/scripts/quality_gate.mjs \
  <run>/advisory/advisory_actions.json <run>/advisory
# 期望：PASS (exit 0)
```

## Failure Recovery

| 症状 | 处置 |
|---|---|
| exit 3 no data file | 检查 --data / --run-dir/00_input/ 两处 |
| exit 3 OBJECTIVE_INVALID | 按 objective.schema.json 修 objective.json 后重跑，绝不放宽校验 |
| exit 3 ONTOLOGY_BRIEF_REQUIRED | 先跑 `scripts/ontology_prepare.py --run-dir <run>` 再分析 |
| exit 2 not_actionable | 补 ≥50 行数据/补动作日志/提供 dead-time/先做设计试验；这是诚实结果 |
| gate FAIL（重算不一致） | 有产物被手改：重跑脚本重建，禁止手改；3 轮仍败 → 上报 |
| 复用腿 import 失败 | 自动降级：degradations 记录 + C 级定性方向（强制"未验证"标注）；全腿缺席 → exit 2 |
| tuning-memory 归因不可用 | 门 C 记 not_estimable，全建议 cap C/B，报告继续产出 |
