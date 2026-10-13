---
name: industrial-line-stability-report
description: "产线运行稳定性报告 skill：给定时间段的生产数据（可以只有加工参数，也可以加工参数+检测指标都有），协同 industrial-sentinel（历史基线对照）、industrial-tuning-memory（调优动作归因）、industrial-doe-analyzer（推荐操作窗）做确定性稳定性评估，产出企业可直接阅读的中文 HTML 落地页报告（结论先行、证据链齐全、ECharts 可视化）+ 机器可读 stability_report.json。综合评分 0-100 分级：A≥85 稳定 / B≥70 亚稳定 / C≥50 波动 / D<50 不稳定；数据不足时诚实输出「无法评估」绝不编造——对时间不变量通道（冻结快照导出/死点）自动剔除评分并声明，全部不变量则直接判定无法评估。PURE-ANALYSIS：只产分析报告，绝不下发参数。Trigger: 产线稳不稳定、产线运行情况报告、稳定性报告、line stability report、production status report、运行一段时间稳不稳、生成产线周期报告、给老板看产线报告、DCS导出分析、主控工艺参数 — even if they only paste a CSV path without saying 'report'. Negative boundary: deep root-cause attribution → industrial-diagnostician；DOE 设计试验分析 → industrial-doe-analyzer；实时增量告警值守 → industrial-sentinel fast-screen；参数布点寻优 → industrial-optimizer-loop；多级表头宽表/原始导出清洗 → industrial-data-preprocessor（预处理配方见 references/data-prep-dcs.md）。"
---

# Industrial Line Stability Report（产线运行稳定性报告）

一句话：把"这段时间我的产线稳不稳定"变成一份**有评分、有分级、有证据链、可给企业全员看**的中文 HTML 报告。全部数值由 `lstcore` 确定性脚本计算（零 LLM、零网络），agent 只做中文解读，数值字段不可触碰。

## 设计原则（house rules）

1. **本体优先**：先理解工况、再碰统计。本体发现顺序：`--ontology` 显式路径 → `<run_dir>/00_input|01_ontology/ontology.json`（ontology-builder 产物）→ `data/ontology_store` 资产库按 scene 匹配 → 都没有才进入 auto 模式（启发推断），**每个理解字段带 `assigned_by=ontology|user|auto` 溯源**。本体提供的 normal_range 在用户未给规格时回退为 Cpk 规格限；relationships 作为相关性发现的物理机制校验（darwin 四条件）；confounders 进入报告"假设与局限"。
2. **不重复造轮子**（复用=单一事实源）：Nelson 判异剧集与稳健 z 复用 `industrial-sentinel/sentinelcore`（spc/robust），工况分段复用 `sentinelcore/regime_map`（C3 方差比+漂移坡道+二分变点），操作窗来自 `industrial-doe-analyzer` recommendations，动作归因调 `industrial-tuning-memory` tune_stats，`--doe-auto` 可选深腿直接跑 doe 观测分析并融合其 BH-FDR 相关报告。复用不可用时显式降级（provenance.spc_source=local_fallback 等）。
3. **确定性**：评分、发现、证据全部来自脚本；agent 禁止改动任何数值字段，只能追加中文 `interpretation` 字段与面向人的解读。
4. **诚实性**：行数 <50 或无数值参数列 → `status=not_assessable`（exit 2），说明原因，不评分不编造；协同输入缺席时在 `degradations` 记录原因；>100k 行系统抽样并标记 `data.sampled`。
5. **darwin 数据真值条款**：数值可由原始表复算（data_source=raw、row_range、方法清单）；推导字段标 `derived:true`；每条发现带 0-100 确定性置信度（统计证据 × 本体机制支持，抽样 -20）；`limitations` 显式列出模型假设、规格覆盖与未控混杂。
6. **咨询边界**：报告仅描述"发生了什么、有多稳"，绝不构成参数下发指令（HTML 页脚已声明）。

## 定位

```
输入：  时段生产数据（加工参数 ± 检测指标，CSV/TSV/XLSX/Parquet/JSON，≥50 行）
协同：  sentinel 基线（可选） · tuning-memory 动作归因（可选） · doe-analyzer 操作窗（可选）
输出：  <out>/stability_report.json      机器可读契约 line-stability-report/1.0
        <out>/charts.json                 图表数据束 line-stability-charts/1.0
        <out>/line_stability_report.html  自包含中文落地页（结论先行+证据链附录）
        <out>/html_selfcheck.json         HTML 自检
退出码：0 ok | 1 有发现（报告完整） | 2 not_assessable（数据不足，诚实降级） | 3 输入/门禁失败
```

三条铁律：
1. **确定性**：评分、发现、证据全部来自 `stability_analyzer.py`；agent 禁止改动任何数值字段，只能追加中文 `interpretation` 字段与面向人的解读。
2. **诚实性**：行数 <50 或无数值参数列 → `status=not_assessable`（exit 2），说明原因，不评分不编造；协同输入缺席时在 `degradations` 记录原因。
3. **咨询边界**：报告仅描述"发生了什么、有多稳"，绝不构成参数下发指令（HTML 页脚已声明）。

## 评分模型（frozen v1，详见附录与 schema）

每参数 100 分起扣：SPC 违规剧集率（-0.8/百分点，封顶 -40；剧集来自 sentinelcore.spc.evaluate）· CV 分档（≤1% 0 → >10% -32）· Cpk 分档（≥1.67 0 → <0.67 -34，规格限来源：用户 > 本体资产 normal_range > 不计算）· 显著漂移分档（相对每日漂移 <0.3% -6 → ≥1% -25；仅在 Theil-Sen+Mann-Kendall p<0.01 **且**相对漂移 ≥0.1%/天 时计入，防纯噪声外推假漂移）· 基线偏离分档（|robust z|>3.5 -8 → >6.7 -25，需 sentinel 基线）。综合分 = 参数加权均值（context.weights 或等权）；A≥85 稳定 / B≥70 亚稳定 / C≥50 波动 / D<50 不稳定。发现置信度为确定性评分：统计证据基础分 + 本体机制加成（known +15~20 / same_domain +5 / unknown 封顶 45 并打 [MECHANISM_UNKNOWN] 标），抽样 -20。

## HTML 报告结构（企业阅读顺序）

1. **Hero**：产线/时段/综合评分徽章 + 一句话结论
2. **工况理解（本体优先）**：场景叙事 + 逐参数（本体名/单位/角色/规格来源/控制方程/assigned_by）+ 工况分段表（sentinel C3 变点）
3. **核心发现**：每条含严重度、置信度、（相关性类）物理机制校验、证据表（derived 字段显式标记）
4. **参数稳定性总览** → 5. **趋势与控制限**（ECharts，违规剧集标红）→ 6. **相关与波动驱动**（热力图+贡献条）
7. **协同分析输入**（三件套启用/降级如实展示）→ 8. **数据与口径**：sha256、行范围、方法与阈值、**假设与局限**（抽样/模型假设/本体混杂因子/规格覆盖）→ 页脚咨询免责声明

## Modes

| Mode | 入口 | 输入 | 时延 | 退出码 |
|---|---|---|---|---|
| script-only（后端/无人值守） | `stability_analyzer.py analyze` | 数据 + 可选协同输入 | 秒级 | 0/1/2/3 |
| agent-assisted（完整报告） | 本 SKILL.md → Phase 0-4 | 同上 + agent 解读 | 分钟级 | 同上 + gate |

## Inputs / Outputs

| 文件 | 角色 |
|---|---|
| `schemas/report_context.schema.json` | 上下文契约（全字段可选：line_id/product/时段/spec_limits/weights/协同路径/preprocessing 预处理溯源） |
| `templates/report_context.template.json` | 上下文填写模板 |
| `references/data-prep-dcs.md` | DCS 多级表头宽表 → tidy 表的确定性预处理配方（含冻结快照检测） |
| `scripts/stability_analyzer.py` | 核心分析 CLI（写 stability_report.json + charts.json） |
| `scripts/report_builder.py` | HTML 落地页构建（写 line_stability_report.html + html_selfcheck.json） |
| `scripts/quality_gate.mjs` | 交付门禁（S1 schema / S2 诚实性 / S3 zero-LLM / S4 HTML 自检 / S5 共享枚举） |
| `scripts/lstcore/` | 确定性核心（_io/profile/stability/drivers/score/findings/charts） |
| `references/agent-protocol.md` | agent Phase 0-4 执行协议（agent 模式必读） |

协同输入（全部可选，缺席自动降级并记录）：
- `--ontology <ontology.json>` / `--scene <scene-key>` / context.ontology_path：本体优先的工况理解（角色/单位/规格回退/机制图谱/混杂因子）。
- `--baseline <watch_baseline.json>`：sentinel 基线逐参数对照（median/MAD → robust z 越限即偏离发现+扣分）。
- `--action-log <action_log.json> --run-dir ...`：调 industrial-tuning-memory `tune_stats.py attribute` 归因本期调优动作，归因报告并入 `integrations.tuning_memory`（estimable 动作产出效果发现；不可估时如实说明）。
- `--doe-run-dir <doe_run>`：读 doe-analyzer `conclusions/recommendations.json` 推荐操作窗，时段中位超窗产出 warn 发现。
- `--doe-auto`：无 doe 产物时自动跑一次 doe 观测分析（嵌套 run）并融合其相关性报告与操作窗（深腿，分钟级）。

## Dispatch（调用卡）

```
任务：产线运行稳定性报告
RUN_DIR=<run-dir>                      # 00_input/ 下放数据文件（可选 report_context.json）
SKILL_PATH=<path-to-.claude/skills/industrial-line-stability-report>
SHARED_PATH=<path-to-.claude/shared>
```

读 `references/agent-protocol.md` 并执行 Phase 0-4。硬约束：
- Phase 2 的 `quality_gate.mjs` 必须 exit 0 才算完成；修复 = 重跑脚本，禁止手改数值产物，最多 3 轮。
- exit 2（not_assessable）不是失败：向用户说明缺什么数据，不伪造结论。
- 报告语言中文；JSON 枚举字段保持英文。

## Verification

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-line-stability-report/tests/run_tests.py all
# 期望：ALL GREEN
node .claude/skills/industrial-line-stability-report/scripts/quality_gate.mjs \
  <out>/stability_report.json <out>
# 期望：PASS (exit 0)
```

## Failure Recovery

| 症状 | 处置 |
|---|---|
| exit 3 no data file | 检查 --data / --run-dir/00_input/ / context.data_path 三处 |
| exit 2 not_assessable | 补足 ≥50 行数据或放宽 start/end；这是诚实结果，不是错误 |
| exit 2 且结论提到「快照」 | 全部数值通道时间不变量（冻结快照导出/死点）：改从 DCS 历史站导出逐时刻存档值（每时刻一行、数值随时间变化）后重试，不是脚本问题 |
| 部分通道时间不变量 | 正常行为：不变量通道被剔除评分并发 data_quality 发现（占比 ≥50% 为 high），结论只覆盖变化通道 |
| time column 解析失败 | 用 --time-col 显式指定；数值时间列自动按秒处理 |
| excel 读不了（缺 openpyxl） | 让用户提供 CSV（degradation 已记录原因） |
| tuning-memory 归因不可用 | 报告继续产出，integrations.tuning_memory.used=false + reason |
| gate FAIL | 重跑脚本（先删旧 out 目录），禁止手改；3 轮仍败 → 上报 |
