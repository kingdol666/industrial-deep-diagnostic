---
name: industrial-judge
description: "10-point quality gate for industrial diagnosis artifacts. Verifies physical traceability, evidence sufficiency, reasoning chain integrity, anti-spurious validation carry-forward, and no overclaiming. Outputs judge_feedback.json with verdict+score+blocking_issues. Trigger: quality gate, quality review, judge gate, audit quality, verdict check, blocking issues. Do NOT use without diagnosis artifacts."
---

# Industrial Judge

评审 6 个诊断产物 → `05_review/judge_feedback.json`（verdict + score + blocking_issues）。

## Inputs

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 + COMPETING_SET |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | R1-R8 推理链 |
| `02_processed/validate_report.json` | 统计验证报告（Simpson/去趋势/变点/离群） |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |

## Output

`05_review/judge_feedback.json` — verdict + overall_score + dimension_scores[0-10] + blocking_issues + repair_instructions

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

## Execution

```javascript
Agent({
  subagent_type: "judge",
  description: "10-point quality gate review",
  permissionMode: "bypassPermissions",
  run_in_background: true,
  prompt: `RUN_DIR=<...> SKILL_PATH=<...> SHARED_PATH=<...>
Read "$SKILL_PATH/references/agent-protocol.md" and execute the full gate.`
})
```

## Verification

```bash
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/judge_feedback_schema.json" \
  "$RUN_DIR/05_review/judge_feedback.json"
node "$SKILL_PATH/scripts/judge-gate-check.mjs" "$RUN_DIR" --skip-summary
```

## References

`references/agent-protocol.md` | `schemas/judge_feedback_schema.json` | `templates/judge_template.json`
