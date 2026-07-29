---
name: industrial-diagnostician
description: "工业诊断管线 — 物理约束的竞争性假设诊断引擎。融合 data+ontology+physics+VLM+time-lag 信息，输出 diagnosis/evidence/confidence/reasoning_chain。Trigger: 诊断, diagnoze, root cause, 根因, 竞争假设, competing hypotheses, physics diagnosis, 物理推断, diagnostician, 根因诊断, 假设排除, hypothesis elimination, 因果推断, causal inference, 物理约束诊断, 竞争假设分析. Do NOT use without upstream data_analysis_conclusion.json."
---
# Industrial Diagnostician
物理约束的竞争性假设根因诊断引擎。融合数据分析结论、领域本体、物理第一原理、VLM 视觉证据和时滞分析，通过排除而非确认输出结论。

核心规则：**诊断 = 排除**。每条结论满足四条件——时间先后 + 统计显著 + 物理机制 + 无矛盾。至少 3 条竞争假设，至少 2 条被排除。
## Inputs (expected in `RUN_DIR`)

| File | Role |
|------|------|
| `02_processed/data_analysis_conclusion.json` | 强制交接文件——统计分析结论 |
| `01_ontology/ontology.json` | 物理语义本体 |
| `03_figures/visual_analysis.json` | VLM 视觉证据 |
| `02_processed/time_lag_analysis.json` | 时滞分析（存在则必须读取） |
| `02_processed/anomaly_report.json` | 异常报告 |
| `02_processed/validate_report.json` | 统计验证报告 |
| `02_processed/feature_summary.json` | 特征摘要 |

## Outputs

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 结论（process_fluctuation + integrated_dual_drive） |
| `04_diagnostics/evidence.json` | 证据清单（L1-L7 等级，含 ontology_data_physics_proof） |
| `04_diagnostics/confidence.json` | 5 因子置信度评估 + adjustment_log |
| `04_diagnostics/reasoning_chain.json` | R1-R8 完整推理链 |

## Core Rules

- **3+ hypotheses** — each with falsification conditions + causal chain (governing equation)
- **2+ EXCLUDED** — via NO_RESET, IMPOSSIBLE physics, IMPLAUSIBLE magnitude, CONTRADICTED ontology
- **Conclusion types**: `DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **COMPETING_SET honesty**: never force to DETERMINED; ambiguity is truth
- **Anti-spurious**: every |r|>=0.3 reference passes Simpson/detrend/lag/leave-one-out
- **Confidence ceilings**: INDISTINGUISHABLE<=65, COMPETING_SET<=70, [PARAM_AMBIGUITY]<=50
- **Schema-First**: read schema -> construct -> write -> validate, one shot per file
## Execution

```javascript
Agent({
  subagent_type: "diagnostician",
  description: "物理约束的竞争假说根因诊断",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=.claude/skills/industrial-diagnostician
${REPAIR_INSTRUCTIONS ? 'REPAIR_INSTRUCTIONS=' + REPAIR_INSTRUCTIONS : ''}

Read ".claude/skills/industrial-diagnostician/references/agent-protocol.md"
and execute Phase 0-7. Fuse data+ontology+physics+VLM+time-lag.
If time_lag_analysis.json exists, MUST read it.
Every hypothesis includes ontology_data_physics_proof,
physical_logic_chain, and falsification_conditions.`,
  run_in_background: true
})
```
## Verification
```bash
SKILL_PATH=".claude/skills/industrial-diagnostician"

for f in diagnosis evidence confidence reasoning_chain; do
  node "$SHARED_PATH/scripts/validate.mjs" \
    "$SHARED_PATH/schemas/${f}_schema.json" \
    "$RUN_DIR/04_diagnostics/${f}.json" || exit 1
done

node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/schema-validation-loop.mjs" "$RUN_DIR" "$SKILL_PATH" diagnostician
```
## References

- `references/agent-protocol.md` — Phase 0-7 执行协议（假设排比/物理推断/证据融合/写入验证）
- `references/resources/execution_reference.md` — 文件列表/筛选规则/控制方程/hallucination prevention
- `resources/evidence_rules.md` — 证据等级体系/因果五条件/反推测
- `resources/physics_inference_framework.md` — L1-L5 物理推断
- `resources/diagnosis_method.md` — 置信度上限/诊断方法论
- `resources/diagnostician_dual_drive_reference.md` — View A/B 双驱动分析
- `resources/parameter_to_physics.json` — 参数物理量映射
- `schemas/` — 4 个输出 JSON Schema
- `scripts/` — schema-validation-loop.mjs, diagnostic-quality-check.mjs, physics_check.py
