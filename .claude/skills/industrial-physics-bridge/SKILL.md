---
name: industrial-physics-bridge
description: >
  Physics mechanism bridge — validates statistical relationships as physical causal
  chains and records evidence gaps.
  Trigger: physics bridge, physics bridging, physics verification, mechanism verification,
  physics consistency check, physics consistency.
  Reads ontology/diagnosis/evidence/confidence/reasoning_chain/visual_analysis/deep_data_analysis
  from an existing diagnostic RUN_DIR and produces physics_bridge.json.
---

# Industrial Physics Bridge

A bridge layer from statistical regression to physical causality. Runs five physics verifications (direction, functional form, time lag, magnitude, state dependence) on every deep data relationship, extracts the surviving physical mechanism chains, and records the excluded competing explanations and evidence gaps.

## Inputs / Outputs

### Inputs (from existing RUN_DIR)

| File | Required | Description |
|------|----------|-------------|
| `01_ontology/ontology.json` | ✓ | Domain ontology: governing_law, predicted_functional_form, time_lag, data_direction_validated, relationships |
| `02_processed/physics_check.json` | ✓ | physics_check output: quality_reset_analysis, manual_physics_verification |
| `04_diagnostics/diagnosis.json` | ✓ | Diagnosis output: hypotheses (surviving/eliminated), primary_finding |
| `04_diagnostics/evidence.json` | ✓ | Evidence inventory: evidence_inventory |
| `04_diagnostics/confidence.json` | ✓ | Confidence decomposition: five_factor_breakdown, adjustment_log, ceilings |
| `04_diagnostics/reasoning_chain.json` | ✓ | Reasoning chain: complete R1-R8 record |
| `03_figures/visual_analysis.json` | ✓ | Visual analysis: figure inventory, key_visual_observations |
| `enhancement/deep_data_analysis.json` | ✓ | Deep data analysis: relationships[], tradeoff_and_operability[] |
| `00_input/rag_deep_understanding.json` | - | RAG deep understanding (optional) |

### Output

| File | Description |
|------|-------------|
| `enhancement/physics_bridge.json` | Physics bridge output: contains relationship_verifications, mechanism_chains, competing_explanations, evidence_gaps |

## Usage

```bash
# Standalone execution (recommended)
uv run --project .claude/shared/scripts python .claude/skills/industrial-physics-bridge/scripts/physics_bridge_builder.py \
  --run-dir <RUN_DIR> [--output <OUTPUT_PATH>]

# Or invoked automatically by the orchestrator (E5 stage)
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir <RUN_DIR>
```

Default output: `<RUN_DIR>/enhancement/physics_bridge.json`

## E5 Verification Protocol

Five physics consistency verifications are applied to every relationship in `deep_data_analysis.json.relationships[]`:

### Five-Item Verification Table

| Item | Source Comparison | Output Enum |
|------|------------------|-------------|
| direction | Statistical slope sign vs ontology.governing_law prediction / data_direction_validated | `MATCH` / `MISMATCH` / `UNTESTED` |
| functional_form | Data form_match vs ontology.predicted_functional_form | `MATCH` / `MISMATCH` / `UNTESTED` |
| time_lag | deep_data lag_aligned lag vs ontology.time_lag / lag_agreement | `MATCH` / `MISMATCH` / `UNTESTED` |
| magnitude | First-order magnitude estimate from ontology.governing_equation vs observed values | `PLAUSIBLE` / `STRONG` / `IMPLAUSIBLE` / `UNTESTED` |
| state_dependence | per_group and per_regime variation | `STABLE` / `STATE_DEPENDENT` / `REVERSES` / `UNTESTED` |

### Overall Status Determination

| Condition | overall_status |
|-----------|----------------|
| All MATCH/PLAUSIBLE/STABLE | `consistent` |
| Direction MISMATCH | `inconsistent` (critical diagnostic signal) |
| Partial match | `plausible` |
| All UNTESTED | `untestable` |
| Physics_check explicit rejection | `rejected` |
| Diagnosis confirms mechanism | `confirmed` |

## Mechanism Chains

Extracted from `diagnosis.json.hypotheses.surviving[]`. Each surviving hypothesis produces one mechanism_chain containing:
- `chain_id`: MC-NNN
- `claim`: hypothesis name + root physical cause
- `evidence_refs`: extracted from supporting_evidence
- `physics_law`: extracted from physical_logic_chain
- `data_support`: extracted from ontology_data_physics_proof
- `diagnosis_support`: hypothesis verdict and confidence
- `competing_explanations`: eliminated hypotheses as competing explanations
- `what_would_change_conclusion`: falsification conditions

## Competing Explanations

Extracted from `diagnosis.json.hypotheses.eliminated[]`. Each eliminated hypothesis produces one competing_explanation entry containing:
- `explanation`: hypothesis name and exclusion reason
- `support_level`: exclusion confidence
- `against`: specific evidence
- `resolution`: exclusion type and revival condition

## Evidence Gaps

Aggregated from the following sources:
1. `confidence.json.breakdown[].evidence_gaps`
2. `reasoning_chain.json.uncertainty_summary.epistemic_gaps`
3. `deep_data_analysis.json.tradeoff_and_operability[].open_questions` — questions tagged "Discrepancy"

Severity levels: `critical` / `major` / `minor` / `cosmetic`

## AC-2 Contract (scene-agnostic)

For any scene, when a relationship satisfies the following conditions, the corresponding assertions must hold:
- A relationship flagged `data_direction_validated=false` in the ontology → `direction` = `MISMATCH`, `overall_status` = `inconsistent`
- Diagnosis primary_finding describes a physical contradiction/compensation response → that relationship's `evidence_refs` includes a diagnosis reference
- Hypotheses surviving diagnosis → every surviving hypothesis produces one mechanism_chain

(The CSTR catalytic hydrogenation run is the representative scenario validating this contract: `reactor_temp_C → conversion_pct` must be MISMATCH/inconsistent because the ontology flags the direction as unverified, and the mechanism chain includes the sulfur-poisoning hypothesis.)

## References

- `references/agent-protocol.md` — Agent execution protocol
- `resources/physics_verification_rules.md` — Detailed physics verification rules