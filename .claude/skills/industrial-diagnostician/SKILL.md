---
name: industrial-diagnostician
description: "工业诊断管线 — 物理约束的竞争性假设诊断引擎。融合数据分析结论+领域本体+物理机制+VLM视觉证据+时滞分析，通过排除而非确认输出结论。Trigger: 诊断, diagnoze, root cause, 根因, 竞争假设, competing hypotheses, physics diagnosis, 物理推断, diagnostician, 根因诊断, 假设排除, hypothesis elimination, 因果推断, causal inference, 物理约束诊断, 竞争假设分析. Do NOT use without upstream data_analysis_conclusion.json."
---

# Industrial Diagnostician

物理约束的竞争性假设根因诊断引擎。融合数据分析结论、领域本体、物理第一原理、VLM 视觉证据和时滞分析，通过排除而非确认输出结论。

核心规则：**诊断 = 排除**。每条结论满足四条件——时间先后 + 统计显著 + 物理机制 + 无矛盾。至少 3 条竞争假设，至少 2 条被排除。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Role |
|------|------|
| `02_processed/data_analysis_conclusion.json` | 强制交接文件——统计分析结论 |
| `01_ontology/ontology.json` | 物理语义本体 |
| `03_figures/visual_analysis.json` | VLM 视觉证据 |
| `02_processed/time_lag_analysis.json` | 时滞分析（存在则必须读取） |
| `02_processed/anomaly_report.json` | 异常报告 |
| `02_processed/validate_report.json` | 统计验证报告 |
| `02_processed/feature_summary.json` | 特征摘要 |
| `02_processed/scenario_classification.json` | 场景/产品分层分类 |

### Outputs

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 结论（process_fluctuation + integrated_dual_drive） |
| `04_diagnostics/evidence.json` | 证据清单（L1-L7 等级，含 ontology_data_physics_proof） |
| `04_diagnostics/confidence.json` | 5 因子置信度评估 + adjustment_log |
| `04_diagnostics/reasoning_chain.json` | R1-R8 完整推理链 |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent diagnostician --step diagnostician

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent diagnostician --step diagnostician \
  --files 04_diagnostics/diagnosis.json,04_diagnostics/evidence.json,04_diagnostics/confidence.json,04_diagnostics/reasoning_chain.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

启动 `diagnostician` 子Agent：

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "diagnostician",
  task: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-diagnostician>
SHARED_PATH=<path-to-.claude/shared>
${REPAIR_INSTRUCTIONS ? 'REPAIR_INSTRUCTIONS=' + REPAIR_INSTRUCTIONS : ''}

Read "<SKILL_PATH>/references/agent-protocol.md"
and execute Phase 0-7. Fuse data+ontology+physics+VLM+time-lag.

Key constraints:
- 三驱动：物理主导 + 数据验证 + 视觉补充
- 每个假说必须有物理机制 — governing equation 和因果链
- 至少 3 个竞争假设（H1, H2, H3），至少排除 2 个
- COMPETING_SET 不能只有一个假设
- 推理链必须 R1-R8 完整
- 如果 time_lag_analysis.json 存在，必须读取
- Every hypothesis includes ontology_data_physics_proof, physical_logic_chain, and falsification_conditions
- 输出中文，enum 保持英文
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/physics_inference_framework.md`, `resources/evidence_rules.md`, `resources/diagnosis_method.md`.

| Phase | Purpose |
|-------|---------|
| 0 | 数据探测 — 读取所有输入文件 + 4 个输出 schema |
| 1 | 统计基础 — 校验 validate_report（Simpson/去趋势/留一法/CCF），记录通过验证的相关性 |
| 2 | 产品分层 — 读取 scenario_classification，确定 focus_product，检测 Simpson 反转 |
| 3 | 假说生成 — 3+ 竞争假设，每个含物理链（governing equation）+ 支持证据 + 反对证据 + 证伪条件 |
| 4 | 数据区分性 — 逐对评估 discriminability_matrix，INDISTINGUISHABLE → confidence_ceiling ≤ 65 |
| 5 | 假设排除 — 至少排除 2 个，exclusion_confidence ≥ 90，记录 revival_condition |
| 6 | 置信度评估 — 5 因素分解（statistical/physical/temporal/confounds/symptom）+ adjustment_log + ceilings |
| 7 | 写输出 + Schema 验证 — 4 JSON 文件 + validate.mjs 逐个验证，全部通过才算完成 |

## Core Rules

- **3+ hypotheses** — each with falsification conditions + causal chain (governing equation)
- **2+ EXCLUDED** — via NO_RESET, IMPOSSIBLE physics, IMPLAUSIBLE magnitude, CONTRADICTED ontology
- **Conclusion types**: `DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **COMPETING_SET honesty**: never force to DETERMINED; ambiguity is truth
- **Anti-spurious**: every |r|≥0.3 reference passes Simpson/detrend/lag/leave-one-out
- **Confidence ceilings**: INDISTINGUISHABLE ≤ 65, COMPETING_SET ≤ 70, [PARAM_AMBIGUITY] ≤ 50
- **Schema-First**: read schema → construct → write → validate, one shot per file
- **Physics chain format**: 参数X的测量值Y → 经过物理定律Z → 影响质量指标W（三段式）

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
SKILL_PATH="<path-to-.claude/skills/industrial-diagnostician>"
SHARED_PATH="<path-to-.claude/shared>"

for f in diagnosis evidence confidence reasoning_chain; do
  node "$SHARED_PATH/scripts/validate.mjs" \
    "$SKILL_PATH/schemas/${f}_schema.json" \
    "$RUN_DIR/04_diagnostics/${f}.json" || exit 1
done

node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/schema-validation-loop.mjs" "$RUN_DIR" "$SKILL_PATH" diagnostician
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | 修复 JSON → 重写 → 重新验证（schema-validation-loop） |
| Missing data_analysis_conclusion.json | 不可继续 — upstream 未完成 |
| Missing time_lag_analysis.json | 非强制 — 标记无时滞证据，降级 temporal_evidence |
| No hypothesis resolvable | COMPETING_SET + 诚实披露 ambiguity |
| Correlation confounded (Simpson/detrend) | 降级证据等级，标记 confound_detected: true |
| VLM 视觉分析不可用 | 降级 temporal_evidence，不阻塞诊断 |

## References

- `references/agent-protocol.md` — Phase 0-7 执行协议（假设排比/物理推断/证据融合/写入验证）
- `resources/execution_reference.md` — 文件列表/筛选规则/控制方程/hallucination prevention
- `resources/evidence_rules.md` — 证据等级体系/因果五条件/反推测
- `resources/physics_inference_framework.md` — L1-L5 物理推断阶梯
- `resources/diagnosis_method.md` — 置信度上限/诊断方法论
- `resources/diagnostician_dual_drive_reference.md` — View A/B 双驱动分析
- `resources/parameter_to_physics.json` — 参数物理量映射
- `schemas/` — 5 个输出 JSON Schema（diagnosis/evidence/confidence/reasoning_chain/causal_evidence_map）
- `scripts/` — schema-validation-loop.mjs, diagnostic-quality-check.mjs, physics_check.py, confidence-completeness-check.mjs
- `templates/` — diagnosis_template.json
