---
name: industrial-physics-bridge
description: >
  物理机理桥接——将统计关系验证为物理因果链，记录证据缺口。
  Trigger: physics bridge, 物理桥接, physics verification, 机理验证, 物理一致性检查, physics consistency.
  Reads ontology/diagnosis/evidence/confidence/reasoning_chain/visual_analysis/deep_data_analysis
  from an existing diagnostic RUN_DIR and produces physics_bridge.json.
---

# Industrial Physics Bridge

从统计回归到物理因果的桥接层。对每条深度数据关系执行五项物理验证（方向、函数形式、时滞、量级、状态依赖），提取存活的物理机理链，记录已排除的竞争性解释和证据缺口。

## Inputs / Outputs

### Inputs (from existing RUN_DIR)

| File | Required | Description |
|------|----------|-------------|
| `01_ontology/ontology.json` | ✓ | 领域本体：governing_law, predicted_functional_form, time_lag, data_direction_validated, relationships |
| `02_processed/physics_check.json` | ✓ | physics_check 输出：quality_reset_analysis, manual_physics_verification |
| `04_diagnostics/diagnosis.json` | ✓ | 诊断输出：hypotheses (surviving/eliminated), primary_finding |
| `04_diagnostics/evidence.json` | ✓ | 证据清单：evidence_inventory |
| `04_diagnostics/confidence.json` | ✓ | 置信度分解：five_factor_breakdown, adjustment_log, ceilings |
| `04_diagnostics/reasoning_chain.json` | ✓ | 推理链：R1-R8 完整记录 |
| `03_figures/visual_analysis.json` | ✓ | 可视化分析：图表清单, key_visual_observations |
| `enhancement/deep_data_analysis.json` | ✓ | 深度数据分析：relationships[], tradeoff_and_operability[] |
| `00_input/rag_deep_understanding.json` | - | RAG 深度理解（可选） |

### Output

| File | Description |
|------|-------------|
| `enhancement/physics_bridge.json` | 物理桥接输出：包含 relationship_verifications, mechanism_chains, competing_explanations, evidence_gaps |

## Usage

```bash
python physics_bridge_builder.py --run-dir <RUN_DIR> [--output <OUTPUT_PATH>]
```

Default output: `<RUN_DIR>/enhancement/physics_bridge.json`

## E5 Verification Protocol

五项物理一致性验证针对 `deep_data_analysis.json.relationships[]` 中的每条关系：

### Five-Item Verification Table

| Item | Source Comparison | Output Enum |
|------|------------------|-------------|
| direction | 统计斜率符号 vs ontology.governing_law 预测 / data_direction_validated | `MATCH` / `MISMATCH` / `UNTESTED` |
| functional_form | 数据 form_match vs ontology.predicted_functional_form | `MATCH` / `MISMATCH` / `UNTESTED` |
| time_lag | deep_data lag_aligned 滞后 vs ontology.time_lag / lag_agreement | `MATCH` / `MISMATCH` / `UNTESTED` |
| magnitude | 从 ontology.governing_equation 的一阶量级估计 vs 观测值 | `PLAUSIBLE` / `STRONG` / `IMPLAUSIBLE` / `UNTESTED` |
| state_dependence | per_group 和 per_regime 变异 | `STABLE` / `STATE_DEPENDENT` / `REVERSES` / `UNTESTED` |

### Overall Status Determination

| Condition | overall_status |
|-----------|----------------|
| All MATCH/PLAUSIBLE/STABLE | `consistent` |
| Direction MISMATCH | `inconsistent`（关键诊断信号） |
| Partial match | `plausible` |
| All UNTESTED | `untestable` |
| Physics_check explicit rejection | `rejected` |
| Diagnosis confirms mechanism | `confirmed` |

## Mechanism Chains

从 `diagnosis.json.hypotheses.surviving[]` 提取。每个存活的假说生成一个 mechanism_chain，包含：
- `chain_id`: MC-NNN
- `claim`: 假说名称 + 根物理原因
- `evidence_refs`: 从 supporting_evidence 提取
- `physics_law`: 从 physical_logic_chain 提取
- `data_support`: 从 ontology_data_physics_proof 提取
- `diagnosis_support`: 假说判定和置信度
- `competing_explanations`: 已排除假说作为竞争解释
- `what_would_change_conclusion`: 证伪条件

## Competing Explanations

从 `diagnosis.json.hypotheses.eliminated[]` 提取。每个已排除假说生成一个 competing_explanation 条目，包含：
- `explanation`: 假说名称和排除原因
- `support_level`: 排除置信度
- `against`: 具体证据
- `resolution`: 排除类型和复活条件

## Evidence Gaps

从以下来源汇总：
1. `confidence.json.breakdown[].evidence_gaps`
2. `reasoning_chain.json.uncertainty_summary.epistemic_gaps`
3. `deep_data_analysis.json.tradeoff_and_operability[].open_questions` 中标有 "Discrepancy" 的问题

严重程度分级：`critical` / `major` / `minor` / `cosmetic`

## CSTR Contract (AC-2)

对于 CSTR 催化加氢运行，`reactor_temp_C → conversion_pct` 必须满足：
- `direction` = `MISMATCH`
- `overall_status` = `inconsistent`
- `evidence_refs` 包含 diagnosis Arrhenius 矛盾引用
- mechanism_chain 包含存活的硫中毒假说

## References

- `references/agent-protocol.md` — Agent 执行协议
- `resources/physics_verification_rules.md` — 物理验证规则详解
