# Agent Protocol — industrial-improvement-advisor

完整执行清单（agent 模式）。脚本模式（后端直调）只跑 Phase 1-3。

## Phase 0 — 上下文与目标确认（只读）

1. **数据确认**：`00_input/` 下存在唯一时序主表（CSV/TSV，≥50 行）。多文件 → 先用 `industrial-data-preprocessor` 得到单一主表，不要手工合并。
2. **目标确认（核心）**：读 `00_input/objective.json`（若有）。
   - 有且 `targets` 非空 → 显式目标模式：向用户复述目标（KPI/方向/约束/dead_time），请其确认理解无误后继续。
   - 无 → 模糊模式：明确告知用户"系统将基于数据推断最合适的优化目标并回显；推断目标未确认前全部建议封顶 B 级"。**不要阻止用户补充目标**——用户随后贴出目标时按显式模式重跑。
3. **协同输入盘点**：`--doe-run-dir`（操作窗）、`--action-log`（动作日志）、本体资产（store）。缺席的腿将被如实记入 degradations——不要为凑数编造路径。
4. **本体获取（按序，命中即停）**：`--ontology` 显式路径 → `<run_dir>/00_input|01_ontology/ontology.json` → `data/ontology_store` 按 scene 匹配 → auto 模式（由 Phase 0.5 prepare 构建声明先验）。缺本体时机制链全部 `[MECHANISM_UNKNOWN]`、建议封顶 C——交付时建议用户先建本体再重跑。

## Phase 0.5 — 本体制备（profile=improvement）

```bash
uv run --project "$SHARED_PATH/scripts" python \
  "$SKILL_PATH/scripts/ontology_prepare.py" --run-dir "$RUN_DIR" \
  [--ontology <ontology.json>] [--mode auto|full|reuse|extend|off] [--scene <key>] [--json]
```

产出 `01_ontology/` 四件套。**先读 `01_ontology/ontology_brief.md`**（列角色/单位/参考区间/未解决项）再进入分析——杠杆与 KPI 的角色判定依据来自它。

## Phase 1 — 确定性分析

```bash
uv run --project "$SHARED_PATH/scripts" python \
  "$SKILL_PATH/scripts/improvement_analyzer.py" analyze \
  --run-dir "$RUN_DIR" \
  [--data <path>] [--time-col <col>] [--doe-run-dir <doe_run>] [--action-log <action_log>] \
  [--objective <objective.json>] [--max-actions 12]
```

- 退出码：0 有建议且全过 / 1 有建议但含降级腿 / 2 not_actionable（读处方清单，向用户说明缺什么）/ 3 输入或门禁失败（按 SKILL.md Failure Recovery 排查）。
- 产出：`02_evidence/{dose_response.json, window_check.json, attributions/}` + `advisory/{objective_resolved.json, advisory_actions.json, optimizer_seed.json, charts.json}`。
- **读 `advisory/objective_resolved.json`**：若 `inferred=true`，在解读中显著声明"目标为系统推断"。

## Phase 2 — HTML 落地页 + 门禁

```bash
uv run --project "$SHARED_PATH/scripts" python \
  "$SKILL_PATH/scripts/report_builder.py" \
  --advisory "$RUN_DIR/advisory/advisory_actions.json" \
  --charts "$RUN_DIR/advisory/charts.json" \
  --out "$RUN_DIR/advisory/improvement_advisory.html"

node "$SKILL_PATH/scripts/quality_gate.mjs" \
  "$RUN_DIR/advisory/advisory_actions.json" "$RUN_DIR/advisory"
```

- gate 必须 exit 0（not_actionable 产物按 exit 2 语义放行）。修复 = 重跑脚本；**禁止手改任何数值产物**；最多 3 轮，仍败则上报。
- `html_selfcheck.json pass=false` 时看哪项 checks 为 false（通常=图表数据为空或占位文本残留）。

## Phase 3 — Agent 解读（唯一允许 agent 写入的部分）

向 `advisory_actions.json` 的每条 action 追加 `interpretation` 字段（或顶层 `interpretation`）：

```json
{ "authored_by": "<agent-id>", "text": "中文解读：这条建议做什么 → 为什么可信（引用证据值）→ 执行前注意什么" }
```

解读纪律：
1. 每条解读必须引用该 action 的 `expected_gain` / `grade_reasons` / `evidence_refs` 中的数值，**不得引入 JSON 之外的新数字**。
2. C 级动作必须表述为"方向参考，未验证"；B 级必须表述为"需小试验证"；A 级可表述为"可执行（advisory）"——**任何级别都不得写成"已下发/已调整"**。
3. `[MECHANISM_UNKNOWN]` 的动作只能写"统计共变、机理待确认"，不得写成因果。
4. 目标为推断时，首句必须声明"本报告目标由系统基于数据推断"。

## Phase 4 — 交付

向用户报告：HTML 与 Markdown 绝对路径、目标模式（显式/推断）、A/B/C 计数、处方区条目（缺什么数据/做什么试验）、degradations、以及 optimizer_seed.json（B 级动作一键升闭环的入口）。提醒：报告是咨询产物，执行须走产线审批 / optimizer-campaign；IDD 绝不下发参数。

## 红线

1. 数值字段神圣——agent 只能写 `interpretation`。
2. 不编造协同输入与收益数字；不可估就写不可估（effect=null）。
3. not_actionable 不是失败，不许硬凑建议。
4. A 级 ≤3 条是门禁哨兵；发现异常多先怀疑数据/门禁 bug，而不是庆祝。
5. 报告页脚必须保留咨询免责声明；任何措辞不得暗示系统已执行或已下发。

---

## Line Memory 先验纪律（跨 run 产线记忆）

运行上下文中若出现 `## 产线记忆（跨 run 共识…）` 块（或 `00_input/context/line_memory.json` 存在），它来自本产线历史多次独立观测的确定性沉淀——**先验级别 L5，仅作参考**：

1. 必须用本次数据重新验证每条先验；禁止直接复制旧结论或旧数字。
2. 先验与本次数据冲突时，以本次数据为准，并明确标注「与历史记忆不一致」。
3. `[共性]`（≥3 次独立观测）可作强先验；`[警示]`（竞争/反证）必须当反例对待；与强共识反方向的建议由门禁自动降级（`memory_conflict_strong`）。
4. 若发现本体与现实不符（参数归类/单位/缺失参数），写 `05_review/ontology_proposals.json`（契约 `ontology-proposal/1.0`，≤10 条/run，target 必须存在于本次数据列）。
5. 本 skill 的 findings（杠杆-方向-收益）会被完成钩子确定性抽取入产线记忆——建议被后续动作验证后，下一次的 A 级会更可及。
