---
name: industrial-physical-auditor
description: "工业诊断管线 — 物理真相独立审计。PRE_REPORT_AUDIT 模式与 Judge 并行运行输出 optimizer_preflight.md；终审模式审计 report.md 输出 optimizer.md。Trigger: physical audit, 物理审计, 预报告审计, pre-audit, optimizer, 审核, physical truth, 独立审计. Do NOT use without upstream diagnosis or report."
---

# Industrial Physical Auditor

对诊断结果执行独立的物理真相审计。两个模式：
- **PRE_REPORT_AUDIT** (Step 5b): 与 Judge 并行运行，在报告生成前审计诊断产物的物理合理性
- **FINAL_AUDIT** (Step 7): 报告生成后审计 report.md，判定 ENDORSED / CONDITIONAL / REJECTED

## Inputs

### PRE_REPORT_AUDIT mode
| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |

### FINAL_AUDIT mode
| File | Description |
|------|-------------|
| `report.md` | 诊断报告 |
| `04_diagnostics/diagnosis.json` | 诊断结论（交叉验证） |
| `04_diagnostics/evidence.json` | 证据（交叉验证） |

## Outputs

| Mode | Output |
|------|--------|
| PRE_REPORT_AUDIT | `05_review/optimizer_preflight.md` |
| FINAL_AUDIT | `optimizer.md` (含 ENDORSED/CONDITIONAL/REJECTED 判定) |

## Execution

启动 `report-reviewer` 子Agent（两种模式共用同一 agent 类型）：

### PRE_REPORT_AUDIT (Step 5b)

```javascript
Agent({
  subagent_type: "report-reviewer",
  description: "预报告物理审计（与 Judge 并行）",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>/../../../.claude/skills/industrial-physical-auditor
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=true

Read "<this-skill-directory>/../../../.claude/skills/industrial-physical-auditor/references/agent-protocol.md" and execute the pre-report physical audit.
Focus on: physical plausibility of causal chains, governing equation traceability, falsification conditions.`,
  run_in_background: true
})
```

### FINAL_AUDIT (Step 7)

```javascript
Agent({
  subagent_type: "report-reviewer",
  description: "终审 — report.md 物理真相审计",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>/../../../.claude/skills/industrial-physical-auditor
DATA_PATH=<data-file-path>

Read "<this-skill-directory>/../../../.claude/skills/industrial-physical-auditor/references/agent-protocol.md" and execute the final physical audit.
Audit report.md against diagnosis artifacts for:
- Physical truthfulness: does every causal chain trace to governing equations?
- No over-claiming: are confidence levels justified?
- Evidence completeness: are all evidence ranks correctly assigned?
- Falsifiability: are falsification conditions specific and executable?

Output optimizer.md with ENDORSED/CONDITIONAL/REJECTED verdict.`,
  run_in_background: true
})
```

### Verdict Table

| Verdict | 含义 | 下一步 |
|---------|------|--------|
| `ENDORSED` | 审计通过，物理逻辑坚实 | 进入 Step 8 (HTML) |
| `CONDITIONAL` | 有条件通过，存在可修复问题 | 修复后进入 Step 8 |
| `REJECTED` | 物理逻辑有根本缺陷 | 触发修复循环 (D→J→R→R) |

## Verification

```bash
# PRE_REPORT_AUDIT
test -f "$RUN_DIR/05_review/optimizer_preflight.md"

# FINAL_AUDIT (CP-8)
test -f "$RUN_DIR/optimizer.md" && grep -q "ENDORSED" "$RUN_DIR/optimizer.md"
```

## References

- `references/agent-protocol.md` — 完整的 Auditor 执行协议（双模式）
- `resources/evidence_rules.md` — 证据规则
- `resources/engineering_delivery_contract.md` — 工程交付标准
