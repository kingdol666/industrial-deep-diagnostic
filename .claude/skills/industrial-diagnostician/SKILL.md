---
name: industrial-diagnostician
description: "工业诊断管线 — 物理约束的竞争性假设诊断。融合 data+ontology+physics+VLM+time-lag 信息，输出 diagnosis/evidence/confidence/reasoning_chain。Trigger: 诊断, diagnoze, root cause, 根因, 竞争假设, competing hypotheses, physics diagnosis, 物理推断, diagnostician. Do NOT use without upstream data_analysis_conclusion.json."
---

# Industrial Diagnostician

物理约束的竞争性假设根因诊断引擎。融合数据分析结论 + 领域本体 + 物理第一原理 + VLM 视觉证据 + 时滞分析 → 生成诊断结论、证据清单、置信度评估和完整推理链。

核心原则：**诊断 = 排除而非确认**。每条结论必须满足四条件（时间先后 + 统计显著 + 物理机制 + 无矛盾），缺一不可。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `02_processed/data_analysis_conclusion.json` | 强制交接文件——统计分析结论 |
| `02_processed/time_lag_analysis.json` | 时滞分析（如存在必须读取） |
| `03_figures/visual_analysis.json` | VLM 视觉证据 |
| `01_ontology/ontology.json` | 物理语义本体 |
| `02_processed/anomaly_report.json` | 异常报告 |
| `02_processed/validate_report.json` | 统计验证报告 |
| `02_processed/feature_summary.json` | 特征摘要 |

## Outputs

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论（DETERMINED/COMPETING_SET/NEEDS_DATA） |
| `04_diagnostics/evidence.json` | 证据清单（L1-L7 等级标注） |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | R1-R8 完整推理链 |

## Execution

启动 `diagnostician` 子Agent，执行 Phase 0-7 融合协议：

```javascript
Agent({
  subagent_type: "diagnostician",
  description: "物理约束的竞争假说根因诊断",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>
${REPAIR_INSTRUCTIONS ? 'REPAIR_INSTRUCTIONS=' + REPAIR_INSTRUCTIONS : ''}

Read "<this-skill-directory>/references/agent-protocol.md" and execute Phase 0-7.

Fuse data + ontology + physics + VLM evidence + time-lag analysis.
If time_lag_analysis.json exists, you MUST read it.
Every surviving hypothesis MUST include ontology_data_physics_proof, physical_logic_chain, and falsification_conditions.

Key rules:
- COMPETING_SET never forced to DETERMINED — honesty over certainty
- Confidence ceiling: INDISTINGUISHABLE≤65, COMPETING_SET≤70, BEST_EFFORT≤70
- Anti-spurious-correlation: every |r|≥0.3 reference must pass v6.4-v6.7 checks
- Schema-First: read schema before writing, write once, validate immediately`,
  run_in_background: true
})
```

### Diagnostic Phases

| Phase | Content | Key Output |
|-------|---------|------------|
| 0 | 加载上游产物 + 本体 | 融合上下文 |
| 1 | 数据探查 | 统计特征确认 |
| 2 | 异常模式识别 | 时间/空间/产品维度异常聚类 |
| 3 | 假设生成 | 竞争性假设（含 falsification_conditions） |
| 4 | 假设检验 | 数据区分性评估 (Data Discriminability) |
| 5 | 物理验证 | 每条因果链追溯到控制方程 |
| 6 | 假设排除 + 结论 | DETERMINED / COMPETING_SET / NEEDS_DATA |
| 7 | 证据 + 置信度 + 推理链 | 四文件输出 + schema 验证 |

### Evidence Hierarchy

| Level | Source | Confidence |
|-------|--------|------------|
| L1 | 直接测量值 | 最高 |
| L2 | 用户文档 (SOP/手册) | 高 |
| L3 | 统计分析（含验证报告） | 中高 |
| L4 | 图表视觉证据 (VLM) | 中 |
| L5 | 领域知识/工艺逻辑 | 中 |
| L6 | 外部网络引用 | 低 |
| L7 | 无支持假设 | 最低 |

结论受最低证据等级约束。

### Schema-First Protocol

1. **写前读 schema** — 构造内容前先读取对应 JSON Schema
2. **构造符合 schema 的内容** — 所有必填字段、正确类型、合法 enum 值
3. **一次写入** — 用 `write` 工具一次性写入完整文件
4. **立即验证** — `node scripts/schema-validation-loop.mjs "$RUN_DIR" "$SKILL_PATH" diagnostician`

## Verification

```bash
SKILL_PATH="<this-skill-directory>"

# Validate all four outputs
for f in diagnosis evidence confidence reasoning_chain; do
  node "$SKILL_PATH/scripts/validate.mjs" \
    "$SKILL_PATH/schemas/${f}_schema.json" \
    "$RUN_DIR/04_diagnostics/${f}.json" || exit 1
done

# Quality check
node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"

# Schema validation loop (with auto-repair)
node "$SKILL_PATH/scripts/schema-validation-loop.mjs" "$RUN_DIR" "$SKILL_PATH" diagnostician
```

## References

- `references/agent-protocol.md` — 完整的 diagnostician 执行协议（Phase 0-7, ~1032 lines）
- `schemas/` — 4 个输出 JSON Schema + causal_evidence_map_schema.json
- `scripts/` — physics_check.py, diagnostic-quality-check.mjs, confidence-completeness-check.mjs, schema-validation-loop.mjs
- `resources/diagnosis_method.md` — 诊断方法论（Method Stage 1-6）
- `resources/evidence_rules.md` — 证据规则与等级体系
- `resources/physics_inference_framework.md` — 物理推断框架（L1-L5）
- `resources/diagnostician_dual_drive_reference.md` — 双驱动分析参考
