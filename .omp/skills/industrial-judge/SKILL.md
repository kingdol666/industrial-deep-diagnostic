---
name: industrial-judge
description: "工业诊断管线 — 10 项质量门评审，含物理源审计、不过度声称阻断项。输出 judge_feedback.json 含 verdict+score+blocking_issues。Trigger: quality gate, 质量评审, judge, 评审, audit quality, 诊断质量, verdict, 阻断项检查. Do NOT use without diagnosis artifacts."
---

# Industrial Judge

对诊断产物执行 10 项质量门评审——检查物理溯源性、证据充分性、推理链完整性、不过度声称等。产出 `judge_feedback.json`，判定 pass/needs_repair/major_issues/fail。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/confidence.json` | 置信度评估 |
| `04_diagnostics/reasoning_chain.json` | R1-R8 推理链 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/data_analysis_conclusion.json` | 统计分析结论 |
| `03_figures/visual_analysis.json` | VLM 视觉证据 |

## Outputs

| File | Description |
|------|-------------|
| `05_review/judge_feedback.json` | 评审反馈（verdict + score + blocking_issues + repair_instructions） |

## Execution

启动 `judge` 子Agent：

```javascript
Agent({
  subagent_type: "judge",
  description: "10项质量门评审",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>/../../../.claude/skills/industrial-judge
DATA_PATH=<data-file-path>

Read "<this-skill-directory>/../../../.claude/skills/industrial-judge/references/agent-protocol.md" and execute the full quality gate.
Use lowercase enum values only for all verdict/status fields.`,
  run_in_background: true
})
```

### 10-Point Quality Gate

| # | 评审项 | 检查要点 |
|---|--------|----------|
| 1 | 物理溯源性 | 每条因果声明能否追溯到控制方程？ |
| 2 | 证据充分性 | 每条结论是否有 ≥L3 证据？证据链是否闭合？ |
| 3 | 推理链完整性 | R1→R8 是否有跳跃？`[INFERENCE_GAP]` 是否标注？ |
| 4 | 反假相关 | 相关性是否通过 Simpson/去趋势/时滞/leave-one-out？ |
| 5 | 不选择性忽略 | 是否考虑了反面证据？竞争假说是否完整？ |
| 6 | 不过度声称 | COMPETING_SET 是否诚实输出？置信度是否合理？ |
| 7 | 反推测四条件 | 时间先后+统计显著+物理机制+无矛盾，缺→`[HYPOTHESIS]` |
| 8 | 红灯清单 | 10 条禁止动作是否全部遵守？ |
| 9 | Schema 合规 | 所有诊断产物是否 schema-valid？ |
| 10 | 证据等级标注 | 每条结论是否标注 `[Evidence Rank L1-L7]`？ |

### Verdict Table

| Verdict | Score | 含义 | 下一步 |
|---------|-------|------|--------|
| `pass` | ≥90 | 全部通过，零阻断问题 | 进入 Reporter |
| `needs_repair` | 70-89 | 非阻断问题，可修复 | 带 REPAIR_INSTRUCTIONS 重跑 Diagnostician |
| `major_issues` | 50-69 | 中等问题 | 修复（best-of-3 循环） |
| `fail` | <50 | 阻断问题 | 必须修复 |

## Verification

```bash
SKILL_PATH="<this-skill-directory>/../../../.claude/skills/industrial-judge"

# Schema validation
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/judge_feedback_schema.json" \
  "$RUN_DIR/05_review/judge_feedback.json"

# Gate check
node "$SKILL_PATH/scripts/judge-gate-check.mjs" "$RUN_DIR" --skip-summary
```

## References

- `references/agent-protocol.md` — 完整的 Judge 评审协议
- `schemas/judge_feedback_schema.json` — judge_feedback.json Schema
- `templates/judge_template.json` — 评审输出模板
