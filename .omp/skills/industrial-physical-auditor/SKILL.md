---
name: industrial-physical-auditor
description: "工业诊断管线Step 5b/7 — 物理真相独立审计。PRE_REPORT_AUDIT模式与Judge并行输出optimizer_preflight.md；FINAL_AUDIT模式终审report.md输出optimizer.md(ENDORSED/CONDITIONAL/REJECTED)。独立验证物理机制、统计基础、逻辑一致性。Trigger: physical audit, 物理审计, 预报告审计, pre-audit, optimizer, 审核, physical truth, 独立审计, report-reviewer."
---

# Industrial Physical Auditor

独立物理真相审计引擎。两种模式共享 `report-reviewer` Agent，通过 `PRE_REPORT_AUDIT` 参数切换：预报告审计（与 Judge 并行）验证诊断产物物理合理性；终审审计 report.md 追溯每条因果链到控制方程。输出 `optimizer.md` 含 ENDORSED / CONDITIONAL / REJECTED 判定。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `01_ontology/ontology.json` | 领域本体 |
| `02_processed/data_analysis_conclusion.json` | 统计分析结论 |
| 原始/清洗数据 | 直接统计验证用 |
| `report.md` *(FINAL only)* | 诊断报告 |
| `05_review/optimizer_preflight.md` *(FINAL, optional)* | 预报告审计结果（复用已验证发现） |

### Outputs

| Mode | File | Verdict |
|------|------|---------|
| PRE_REPORT | `05_review/optimizer_preflight.md` | PREFLIGHT_PASS / PREFLIGHT_NEEDS_REPAIR / PREFLIGHT_BLOCKED |
| FINAL | `optimizer.md` | ENDORSED / CONDITIONAL / REJECTED |

## Dispatch

启动 `report-reviewer` Agent：

```javascript
// PRE_REPORT_AUDIT mode (Step 5b) — 与 Judge 并行
task({
  agent: "report-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.omp/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.omp/shared>
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=true

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the PRE_REPORT_AUDIT protocol.

Pre-report audit scope:
- Physical plausibility: 每条因果链是否可追溯到控制方程？
- Falsifiability: falsification_condition 是否具体、可执行？
- Competing hypotheses: 排除逻辑是否基于物理而非纯统计？
- Confidence: 上限约束是否合理？
- Confounding variables: 独立统计验算

Output: optimizer_preflight.md with PREFLIGHT_PASS / PREFLIGHT_NEEDS_REPAIR / PREFLIGHT_BLOCKED verdict.
`,
  effort: "hi"
})

// FINAL_AUDIT mode (Step 7) — 报告生成后终审
task({
  agent: "report-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.omp/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.omp/shared>
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=false

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the FINAL_AUDIT protocol.

Final audit scope:
- Physical truthfulness: report.md 每条因果链追溯到 governing equation
- No over-claiming: 置信度是否合理，证据等级分配正确
- Evidence completeness: 证据等级分配正确
- Falsifiability: 证伪条件具体且可执行
- Statistical foundation: 相关是否通过全量反假相关验证

Output: optimizer.md with ENDORSED / CONDITIONAL / REJECTED verdict.
`,
  effort: "hi"
})
```

## Audit Scopes

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md`, `resources/process_knowledge_base.md`.

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
SKILL_PATH="<path-to-.omp/skills/industrial-physical-auditor>"
SHARED_PATH="<path-to-.omp/shared>"

# PRE_REPORT_AUDIT
test -f "$RUN_DIR/05_review/optimizer_preflight.md"
grep -Eq "PREFLIGHT_PASS|PREFLIGHT_NEEDS_REPAIR|PREFLIGHT_BLOCKED" "$RUN_DIR/05_review/optimizer_preflight.md"

# FINAL_AUDIT
test -f "$RUN_DIR/optimizer.md"
grep -Eq "ENDORSED|CONDITIONAL|REJECTED" "$RUN_DIR/optimizer.md"
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Missing diagnosis artifacts | 报告缺失 → 标记 PREFLIGHT_BLOCKED / REJECTED |
| report.md 不存在 (FINAL) | 等待 Reporter 完成 → 重新触发 FINAL_AUDIT |
| 物理机制无法验证 | 降低置信度 → 标记 CONDITIONAL 并附带限制说明 |
| 统计验算与声明矛盾 | 标记 REJECTED → 触发 D→J→R→R 修复循环 |
| Auditor 超时 | 检查部分产物 → 可用则继续，否则重试 |
