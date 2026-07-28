---
name: industrial-physical-auditor
description: "工业诊断管线 — 物理真相独立审计。PRE_REPORT_AUDIT 模式与 Judge 并行运行输出 optimizer_preflight.md；终审模式审计 report.md 输出 optimizer.md (ENDORSED/CONDITIONAL/REJECTED)。Trigger: physical audit, 物理审计, 预报告审计, pre-audit, optimizer, 审核, physical truth, 独立审计, report-reviewer. Do NOT use without upstream diagnosis or report."
---

# Industrial Physical Auditor

独立物理真相审计，两种模式共享 `report-reviewer` 子Agent，通过 `PRE_REPORT_AUDIT` 环境变量区分。

## Inputs

| Mode | File | Description |
|------|------|-------------|
| BOTH | `04_diagnostics/diagnosis.json` | 诊断结论 |
| BOTH | `04_diagnostics/evidence.json` | 证据清单 |
| BOTH | `04_diagnostics/reasoning_chain.json` | 推理链 |
| BOTH | `01_ontology/ontology.json` | 领域本体 |
| BOTH | `02_processed/data_analysis_conclusion.json` | 统计分析结论 |
| BOTH | 原始/清洗数据 | 直接验证用 |
| FINAL | `report.md` | 诊断报告 |
| FINAL | `05_review/optimizer_preflight.md` | 预报告审计结果（如存在，复用已验证发现） |

## Outputs

| Mode | File | Verdict |
|------|------|---------|
| PRE_REPORT | `05_review/optimizer_preflight.md` | PREFLIGHT_PASS / PREFLIGHT_NEEDS_REPAIR / PREFLIGHT_BLOCKED |
| FINAL | `optimizer.md` | ENDORSED / CONDITIONAL / REJECTED |

## Execution

启动 `report-reviewer` 子Agent。两种模式共享同一 agent 类型，通过 `PRE_REPORT_AUDIT` 环境变量切换：

```javascript
Agent({
  subagent_type: "report-reviewer",
  description: "物理真相审计（PRE_REPORT_AUDIT=true=预报告, absent=终审）",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=<true|false>

Read "<this-skill-directory>/references/agent-protocol.md" and execute the ${"${PRE_REPORT_AUDIT}"} protocol.
${"${PRE_REPORT_AUDIT}"}:
  true  → pre-report audit: check diagnosis artifacts for physical plausibility before report generation
  false → final audit: audit report.md against diagnosis artifacts, output optimizer.md with verdict`,
  run_in_background: true
})
```

### Audit Scopes

| Scope | PRE_REPORT_AUDIT | FINAL_AUDIT |
|-------|-----------------|-------------|
| Physical mechanism chain verification | 物理可解释性 + 定量估算 | report.md 每条因果链追溯控制方程 |
| RAG knowledge cross-check | 物理原则 + 失效模式 + 混淆覆盖 | 同上 + 已验证 claim 审计 |
| Reasoning chain audit (hallucination detection) | 8 种红旗模式检查 | spot-check 协议 |
| Confounding variable detection | 独立统计验算 | — |
| Competing hypothesis completeness | ≥3 个竞争假说 | 同上 |
| Confidence assessment audit | 置信度分解 | 不过度声称检查 |
| Over-claiming check | — | 置信度是否合理，证据等级是否正确 |
| Falsifiability check | falsification_condition 是否具体可执行 | 同上 |

## Verdict

| Mode | Verdict | 含义 | 下一步 |
|------|---------|------|--------|
| PRE | `PREFLIGHT_PASS` | 预报告通过 | 继续 Step 6 (Reporter) |
| PRE | `PREFLIGHT_NEEDS_REPAIR` | 可修复问题 | 携带 repair_instruction 修复诊断 |
| PRE | `PREFLIGHT_BLOCKED` | 物理逻辑缺陷 | 触发修复循环 |
| FINAL | `ENDORSED` | 物理逻辑坚实 | 进入 Step 8 (HTML) |
| FINAL | `CONDITIONAL` | 存在可修复问题 | 修复后进入 Step 8 |
| FINAL | `REJECTED` | 根本缺陷 | 触发修复循环 (D→J→R→R) |

## Verification

```bash
# PRE_REPORT_AUDIT
test -f "$RUN_DIR/05_review/optimizer_preflight.md"

# FINAL_AUDIT
test -f "$RUN_DIR/optimizer.md" && grep -Eq "ENDORSED|CONDITIONAL|REJECTED" "$RUN_DIR/optimizer.md"
```

## References

- `references/agent-protocol.md` — 完整的 Auditor 执行协议（双模式，Persona→Step 0-5→Verdict）
- `references/resources/execution_reference.md` — 详细 bash 命令、Python 验证脚本、物理验证框架
- `resources/evidence_rules.md` — 证据等级规则
- `resources/engineering_delivery_contract.md` — 工程交付标准
