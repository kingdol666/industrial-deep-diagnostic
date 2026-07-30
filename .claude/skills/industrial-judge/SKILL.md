---
name: industrial-judge
description: "工业诊断管线 — 质量门审查。10项评分验证诊断推理与统计基础的完整性，跨文件交叉验证审计。Trigger: quality gate, 质量审查, judge, 诊断评审, 质量门, 交叉验证, 审计, quality review, diagnosis audit, verdict check, blocking issues."
---

# Industrial Judge

质量门审查引擎。10 项标准评分，验证诊断推理与统计基础的完整性，执行跨文件交叉验证审计。输出 `judge_feedback.json` 含 pass/needs_repair/major_issues/fail 判定。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 + COMPETING_SET |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | R1-R8 推理链 |
| `02_processed/validate_report.json` | 统计验证报告（Simpson/去趋势/变点/离群） |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |
| `03_figures/visual_analysis.json` | VLM 视觉分析 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/feature_summary.json` | 特征摘要 |

### Outputs

| File | Description |
|------|-------------|
| `05_review/judge_feedback.json` | verdict + overall_score + dimension_scores[0-10] + blocking_issues + repair_instructions |

## 10-Point Gate

| # | Gate | 1-Line Check |
|---|------|-------------|
| 1 | 物理溯源性 | 每条因果声明追溯到控制方程？ |
| 2 | 证据充分性 | 每条结论≥L3 证据且链闭合？ |
| 3 | 推理链完整性 | R1→R8 无跳跃，`[INFERENCE_GAP]` 已标注？ |
| 4 | 反假相关 | Simpson/去趋势/时滞/leave-one-out 验证？ |
| 5 | 不选择性忽略 | 反面证据和竞争假说完整？ |
| 6 | 不过度声称 | COMPETING_SET 诚实；置信度合理？ |
| 7 | 反推测四条件 | 时间先后+显著+机制+无矛盾？ |
| 8 | 红灯清单 | 10 条禁止动作全部遵守？ |
| 9 | Schema 合规 | 所有诊断产物 schema-valid？ |
| 10 | 证据等级标注 | 每条结论标注 Evidence Rank L1-L7？ |

## Verdict

| Verdict | Score | Meaning | Next |
|---------|-------|---------|------|
| `pass` | ≥90 | Zero blocking | Reporter |
| `needs_repair` | 70-89 | Non-blocking issues | Diagnostician with REPAIR_INSTRUCTIONS |
| `major_issues` | 50-69 | Moderate | Fix (best-of-3 loop) |
| `fail` | <50 | Blocking | Must fix |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent judge --step judge

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent judge --step judge \
  --files 05_review/judge_feedback.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

启动 `judge` 子Agent：

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "judge",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-judge>
SHARED_PATH=<path-to-.claude/shared>
DATA_PATH=<data-file-path>

Read the agent protocol at <SKILL_PATH>/references/agent-protocol.md and execute the full quality gate review.

Key constraints:
- validate_report.json 是主要验证工具 — 必须先读再打分
- 每次 BLOCKING 必须有修复指令
- reasoning_chain < 8 段 → blocking issue
- diagnosis.hypotheses.surviving 为空 → blocking issue
- 结论缺少 falsification_conditions → blocking issue
- evidence.validation_evidence 为空 → warning
- 输出中文，enum 保持英文
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md` and `resources/execution_reference.md`.

| Step | Purpose |
|------|---------|
| 0 | 读取所有诊断产物 (diagnosis/evidence/confidence/reasoning_chain/validate_report/data_analysis_conclusion/visual_analysis/ontology/feature_summary) |
| 0.5 | 交叉验证：validate_report 发现与 diagnosis 一致性审计 |
| 0.6 | 推理链质量审计 (R1-R8 完整性/证据基础/反事实/可证伪性/幻觉审计) |
| 0.65 | 物理来源质量审计 (pre_cached/rag_extracted/first_principles 溯源) |
| 0.7 | 独立数据采样：关键相关声明抽样验证 |
| 0.8 | 稳定性/可复现性审计 |
| 1 | 10 项评分 (0-10 每项) — 综合 Steps 0.5-0.8 所有发现 |
| 2 | Cross-Reference Audit (5 项跨文件交叉验证) |
| 3 | 输出 judge_feedback.json |

## Data Truth Mandate

**每一个写入 JSON/报告的数字必须可从原始数据重算。**

| 规则 | 要求 |
|------|------|
| 数字可追溯性 | 每个数字必须标注数据源(cleaned/raw)、行范围、计算方法 |
| 派生值标记 | 推断/派生值必须显式 `"derived": true` 或 `"inferred": true` |
| 清洗留痕 | cleaning_integrity 记录全部清洗操作 |
| 可视化可追溯 | 每张图的每个数据点可追溯到数据集的具体行 |
| 不可用标记 | 无法从数据计算的 → 写 NOT_APPLICABLE + 原因 |

## Counterfactual Reasoning — 排除约束

| 约束 | 说明 |
|------|------|
| 四条件 | 时间先后 + 统计显著 + 物理机制 + 无矛盾 |
| 排除标准 | 任一条件不满足 → 标记为排除候选项并提供量化依据 |
| 物理边界 | 排除必须有第一性原理或控制方程支撑 |
| 置信阈值 | 排除置信度 <80 时标记 `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| 类别 | 要求 |
|------|------|
| 数据限制 | 采样率/噪声/缺失最值/范围限制 |
| 模型假设 | 线性近似/稳态假设/分布假设 |
| 未控制混淆 | 明确列出无法控制的潜在混淆变量 |
| 结论可信区间 | 每个结论标注置信度 ± 误差范围 |

## Efficiency — Parallel Execution

- 与上下游 agent 无数据依赖时 → 主动并行
- 对可预测结果使用确定性脚本而非 LLM 推理
- 大文件采样策略: >100K 行时系统抽样
- Agent stall >600s → 检查已有产物, 部分可用的继续推进

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-judge>"
SHARED_PATH="<path-to-.claude/shared>"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/judge_feedback_schema.json" \
  "$RUN_DIR/05_review/judge_feedback.json"

node "$SKILL_PATH/scripts/judge-gate-check.mjs" "$RUN_DIR" --skip-summary
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | 修复 JSON → 重写 → 重新验证 |
| Missing input files | 报告缺失 → verdict=fail, score=0, blocking issues listed |
| Gate check fail | 使用 blocking_issues 中的修复指令 → 回退 Diagnostician 修复 |
| Judge timeout | 检查部分产物 → 可用则继续 |
