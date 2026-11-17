# Agent Protocol — industrial-line-stability-report

完整执行清单（agent 模式）。脚本模式（后端直调）只跑 Phase 1 + Phase 2 的 report_builder/gate。

## Phase 0 — 本体优先的上下文确认（只读）

1. **本体获取（按序，命中即停）**：
   a. 用户/上下文给的本体路径（`--ontology` 或 context.ontology_path）；
   b. `<run_dir>/00_input/ontology.json`、`<run_dir>/01_ontology/ontology.json`（ontology-builder 产物）；
   c. `data/ontology_store/index.json` 按 scene（`--scene` 或产线名）匹配资产，取最新版本；
   d. 全部未命中 → auto 模式继续（脚本会用确定性启发推断并标 assigned_by=auto），并在交付时建议用户：需要物理语义/控制方程级解读时，先用 `industrial-ontology-builder` 建本体（支持资产复用）再重跑本 skill。
2. 确认输入三选一：`--data <file>`、`--run-dir`（`00_input/` 下有数据文件）、或 context 的 `data_path`。**若输入是文件夹**（含混合格式/多文件），先运行确定性预处理器，得到唯一主时序规范表后再分析：
   ```bash
   uv run --project .claude/shared/scripts python \
     .claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py \
     --data-path "<INPUT_DIR>" --output "$RUN_DIR/00_input" \
     --stability-single-primary --recursive
   ```
   然后以 `$RUN_DIR` 为 `--run-dir` 调用 analyzer；不要直接把文件夹交给 `stability_analyzer.py`，也不要手工合并不同采样率的数据。把 `preprocessing_report.json` 的来源/选择理由写入 `report_context.preprocessing`。
3. 若用户提供的信息足以填写 `templates/report_context.template.json`（产线名/时段/规格限/协同路径/ontology_path），写出 `00_input/report_context.json`（经 report_context.schema.json 校验）。用户显式给的规格限/参数角色优先级高于本体。
4. **意图与场景识别**：确定被分析对象是什么——用户语境/本体 scene 显示非产线场景（能耗、环境、实验室流程等）时，把 `scenario` 写入 report_context；用户给了分析目标（想回答什么问题）时写 `objective`。两者驱动报告主语（产线/系统/对象三档自适应）与头部目标展示；都不给则脚本按本体 scene / line_id 自动推断。
5. 明确告诉用户哪些协同输入可用：sentinel 基线、action_log（本期是否有人工调参）、doe_run（或是否加 `--doe-auto` 让 doe-analyzer 现场做观测分析）。缺席的协同项将在报告 degradations 中如实记录——不要为了凑数编造路径。
6. 禁止读取/改写 benchmark ground truth（`scripts/benchmark/cases/benchmark_cases.json`）。

## Phase 0.5 — 本体制备（ontology_prepare；analyzer 入口也会自动执行）

本体制备是"先理解工况、再碰统计"的第一半：从声明构建本体先验，供 Phase 1 的分析器消费。`stability_analyzer.py analyze` 在入口会自动以当前 `--mode auto` 跑一次 prepare——以下手工命令用于显式控制（换 mode/scene/store）或修复门禁失败：

```bash
uv run --project .claude/shared/scripts python \
  "$SKILL_PATH/scripts/ontology_prepare.py" \
  --run-dir "$RUN_DIR" \
  [--ontology <ontology.json>]      # 显式采纳：文件存在、合法 JSON、含 scene+signals，否则报错退出
  [--mode auto|full|reuse|extend|off] \
  [--scene <scene-key>] [--store-dir <dir>] [--json]
```

**发现顺序（命中即停）**：`--ontology` 显式路径（原样采纳，build_mode=full）→ `<run_dir>/00_input/ontology.json` → `<run_dir>/01_ontology/ontology.json`（prepare 产物）→ `data/ontology_store` 资产库按 scene+context_fp 匹配（stability profile 优先、diagnosis 兜底）→ 都没有才 auto 启发。

**动作机（store 语义）**：`context_fp` = 声明契约指纹（列角色/单位/规格）。exact 命中 → reused（秒级拷贝）；scene 命中但声明变化 → extended（增量合并）；miss → built（声明先验构建）。资产库是唯一写入口（`ontology_store.mjs`，profile=stability 落 `<scene>/stability/vN`）；store 不可用只降级记录，不阻断分析。

**声明先验纪律（不可削弱）**：
1. report_context 声明（spec_limits / parameter_cols / inspection_cols / units）→ `knowledge_source="user_provided"`、`confidence="KNOWN"`；只有用户声明的 spec_limits 才写 `normal_range`。
2. 物理词典（ontology-builder 份 `parameter_to_physics.json`）只在**唯一候选**命中时贡献 unit（physical_unit_SI）/ 物理含义（physical_quantity）/ 控制方程（governing_law），`knowledge_source="auto_inferred"`、`confidence="INFERRED"`；零/多候选一律 `mapping_status="unmatched"` 带原因，绝不猜。
3. **词典 `typical_ranges` 是参考区间（非规格）**：只落本体 `watch.reference_bands` 与简报"参考区间（非规格）"小节，永不写 `normal_range`/spec/Cpk（分析器还有第二道防线：`auto_inferred` 信号不参与 Cpk）。
4. **无方向声明不造因果边**：prepare 产物 `relationships=[]`；无声明单位列在简报/报告中一律"单位未声明（unit undeclared）"。
5. 本体内容零时钟（store 去重靠内容稳定）；`rag_used`/`web_used` 恒为 false（确定性路径），如实写入 provenance。

**CP-2 硬闸**：`01_ontology/ontology.json` 必须过 `node .claude/shared/scripts/validate.mjs <ontology-builder>/schemas/ontology_schema.json <ontology.json>` 且 ≥1024B，否则 SystemExit（`ONTOLOGY_CP2_FAILED`）。

**门禁**：`report_context.ontology.mode`（或编排层注入的 `ontologyMode`）≠ off 时，`01_ontology/ontology_brief.json` 缺失即阻断分析（`ONTOLOGY_BRIEF_REQUIRED`）。agent 必须先读 `ontology_brief.md`（场景理解/列角色与单位/规格与参考区间/混杂与局限/列映射覆盖/未解决项）再进入 Phase 1 的解读工作。

## Phase 1 — 确定性分析

```bash
uv run --project .claude/shared/scripts python \
  "$SKILL_PATH/scripts/stability_analyzer.py" analyze \
  --run-dir "$RUN_DIR" \
  [--ontology <ontology.json>] [--scene <scene-key>] \
  [--time-col t] [--baseline <watch_baseline.json>] \
  [--action-log <action_log.json>] [--doe-run-dir <doe_run>] [--doe-auto] \
  [--no-advisory]
```

- 期望退出码 0（无发现）或 1（有发现）；2 = 数据不足（向用户说明缺什么，停止后续 Phase）；3 = 输入错误（按 SKILL.md Failure Recovery 排查后重试）。
- 产出：`<RUN_DIR>/line_report/stability_report.json` + `charts.json`。
- **集成改善建议步骤（默认自动）**：分析完成后确定性运行 improvement-advisory 适配器（origin=stability，秒级、零额外 LLM），产出 `<RUN_DIR>/advisory/`（graded 动作 + 处方 + `chapter.md` + 独立 HTML）并把摘要写进 `stability_report.json.advisory`。该步骤**绝不改变稳定性退出码**；`--no-advisory` 或 `00_input/advisory_opt_out` 文件可关闭；`advisory/step_status.json` 如实记录 used|skipped|failed。
- 自检本体命中情况：`condition.ontology.mode`；prepare 的动作与本体制备溯源在 `provenance.ontology`（action/scene_key/rag_used/brief_summary）。若为 auto 且资产库存在近似 scene，提示用户可指定 `--scene` 复用。

## Phase 2 — HTML 落地页 + 门禁

```bash
uv run --project .claude/shared/scripts python \
  "$SKILL_PATH/scripts/report_builder.py" \
  --report "$RUN_DIR/line_report/stability_report.json" \
  --charts "$RUN_DIR/line_report/charts.json" \
  --out "$RUN_DIR/line_report/line_stability_report.html"
# 默认同时产出 line_stability_report.md（中文 Markdown 伴随报告，gate 检查其存在；
# --no-md 仅供调试，交付一律保留 md）

node "$SKILL_PATH/scripts/quality_gate.mjs" \
  "$RUN_DIR/line_report/stability_report.json" "$RUN_DIR/line_report"
```

- gate 必须 exit 0。修复 = 修正输入后重跑脚本；**禁止手改任何数值产物**；最多 3 轮，仍败则上报。
- 自检 `html_selfcheck.json` 的 `pass=false` 时先看哪一项 checks 为 false（通常=趋势数据为空或占位文本残留）。

## Phase 3 — Agent 解读（唯一允许 agent 写入的部分）

在 `stability_report.json` 顶层追加一个键：

```json
"interpretation": {
  "authored_by": "<agent-id>",
  "text": "面向产线管理者的 3-6 句中文解读：总体结论 → 最需关注的 1-3 件事（引用 finding_id 与证据值）→ 下一步建议（建议只能指向分析/试验类动作，如下一轮工况分析、补数据、按操作窗校准，绝不下发参数）"
}
```

解读纪律：结论必须与 `conclusion.statement` 一致；引用的每个数值必须能在 findings[].evidence 或 parameters[] 里找到；带 [MECHANISM_UNKNOWN] 的相关性发现只能表述为"统计共变、待机理确认"，不得写成因果；置信度 ≤60 的发现须明示"初步线索"；不得引入 JSON 之外的新数字。

## Phase 4 — 交付

向用户报告：HTML 与 Markdown 绝对路径、score/grade、findings 按 severity 计数、协同项启用情况、degradations。提醒：HTML 可直接用浏览器打开（ECharts CDN 不可用时自动静态降级）；JSON 供下游系统消费。

## 红线

1. 数值字段神圣——agent 只能写 `interpretation`。
2. 不编造协同输入；缺席就降级记录。
3. not_assessable 不是失败，不许硬凑评分。
4. 报告是咨询产物，措辞避免任何"已自动调整/下发"类表述。
5. 退化输入是数据事实，不是可隐藏的瑕疵：时间不变量通道（快照导出/死点）由脚本剔除并发 data_quality 发现，agent 必须向用户如实转述，绝不把“无波动”解读为“稳定”。
6. **单位不得发明**：报告/解读中出现的单位只能来自 `report_context`、本体、或数据列声明；任一单位缺失或不确定时，写“单位未声明（unit undeclared）”，禁止根据产品名/经验猜写 mm、µm、°C 等。`drift_quantify.json` 等 agent 生成的 JSON 中每个信号必须带 `unit`（可为 null）与 `unit_status`（`declared|undeclared`）。

---

## Line Memory 先验纪律（跨 run 产线记忆，2026-11-03 起生效）

运行上下文中若出现 `## 产线记忆（跨 run 共识…）` 块（或 `00_input/context/line_memory.json` 存在），它来自本产线历史多次独立观测的确定性沉淀——**先验级别 L5，仅作参考**：

1. **必须用本次数据重新验证**每一条先验；禁止直接复制旧结论或旧数字。
2. 先验与本次数据冲突时，以本次数据为准，并在报告/结论中明确标注「与历史记忆不一致」。
3. `[共性]`（≥3 次独立观测且无方向矛盾）可作强先验；`[候选]`（2 次）作弱先验；`[线索]`（1 次）只作排查方向；`[警示]`（竞争/反证/陈旧）必须当作反例对待。
4. 若发现本体模型与现实不符（参数归类/单位/物理分组/缺失参数），写 `05_review/ontology_proposals.json`（契约 `ontology-proposal/1.0`，schema：`.claude/shared/schemas/ontology_proposal.schema.json`，每次 ≤10 条，target 必须存在于本次数据列）。分级生效：新增自动、修正需 ≥2 次独立佐证、移除需人工审批（完成钩子校验，无需你自行修改本体）。
5. 稳定性报告的 findings[]（SPC 判异）与 parameters[].drift.significant（漂移）会被完成钩子确定性抽取入产线记忆；同一产线的重复分析（数据窗重叠 >50%）只计一次独立观测，不要把它当作“新证据”。
