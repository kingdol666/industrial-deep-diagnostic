---
name: industrial-deep-analysis
description: >
  确定性深层数据分析层（增强管线 E1-E4）。消费现有诊断 RUN_DIR，产出全列覆盖矩阵、
  物理派生特征、条件关系分析与多目标权衡，只写 RUN_DIR/enhancement/，绝不修改基线诊断产物。
  Trigger: deep analysis, 深层分析, coverage builder, derived feature, conditional analysis, tradeoff.
---

# industrial-deep-analysis

## Description
Deterministic deep-analysis layer (Task 3 of DOE enhancement plan). Consumes an existing diagnostic `RUN_DIR` and writes only enhancement outputs under `RUN_DIR/enhancement/`. Never modifies existing diagnostic artifacts.

## Inputs (read-only)
- `01_ontology/ontology.json` — domain ontology with signals, relationships, confounders
- `02_processed/feature_summary.json` — column-level statistics, targets, predictors
- `02_processed/analysis_parameter_selection.json` — tiered parameter selection
- `02_processed/production_regime_filter.json` — steady/transition regime labels (optional)
- `02_processed/data_analysis_conclusion.json` — time-lag analysis, coverage matrix
- `02_processed/cleaned_data.csv` (or `.json` fallback) — numeric cleaned data
- `02_processed/derived_features.json` — optional pre-computed derived features (from E2)
- `.claude/skills/industrial-deep-analysis/scripts/stat_utils.py` — Task 2 statistical utilities

## Outputs (write only)
- `enhancement/analysis_coverage.json` — per-column coverage assessment (E1)
- `enhancement/derived_features.json` — physically justified derived features (E2)
- `enhancement/deep_data_analysis.json` — relationships + tradeoff_and_operability (E3+E4)

## Phase Protocol (E1 → E4)

### E1: Coverage Builder
```
python .claude/skills/industrial-deep-analysis/scripts/coverage_builder.py --run-dir <RUN_DIR>
```
For every cleaned-data column, emits:
- `role` from ontology signal / selection fallback
- `coverage_status` enum: `covered_primary`, `covered_conditional`, `pruned_physics`, `pruned_confounded`, `not_applicable`, `insufficient_data`
- `unit` from ontology metadata, else `dimensionless` (numeric) or `metadata` (non-numeric)
- `n_total`, `n_steady` as finite numeric counts after coercion
- `support_domain` with p5/p25/p50/p75/p95/n/current_median for numeric columns; finite sentinel values (0.0, n=1) for non-numeric metadata with explicit reason
- `physics_ref` from governing_law/physical_meaning, or `NOT_APPLICABLE`
- `reason` explaining every pruned/not-applicable decision

### E2: Derived Feature Builder
```
python .claude/skills/industrial-deep-analysis/scripts/derived_feature_builder.py --run-dir <RUN_DIR>
```
Physically justified derived features (only when source columns and ontology conditions exist):
1. `cumulative_<poisoning_column>_exposure` — trapezoidal sum over sorted timestamp
2. `time_since_<event_or_group_transition>` — hours since group transition
3. `regime_<name>` — one-hot indicators from `production_regime_filter.json`
4. Lag-aligned feature from `time_lag_analysis.key_findings` with nonzero optimal lag

No invented constants (reactor volume, heat capacity, etc.). Status `not_applicable` for skipped candidates with nonempty formula/reason.

### E3: Conditional Analysis
```
python .claude/skills/industrial-deep-analysis/scripts/conditional_analysis.py --run-dir <RUN_DIR>
```
Builds candidate pairs from:
1. `ontology.relationships[]` from/to names
2. Selection Tier 1/2 predictor columns → quality targets
3. Deduplicated; excludes target=predictor, metadata, control-output, pruned pairs

Per pair computes: `global`, `detrended`, `per_group`, `steady`, `lag_aligned`, `per_regime`, `slope_at_current`, `partial`, `form_match`, `q_value` (BH-corrected), `n_effective`, all seven validity flags. Invokes `tradeoff_builder.build_tradeoff_and_operability` for the final `tradeoff_and_operability[]`.

### E4: Tradeoff Builder
```
python .claude/skills/industrial-deep-analysis/scripts/tradeoff_builder.py --deep-analysis <DEEP_JSON> [--output <OUT>]
```
Library function `build_tradeoff_and_operability(df, relationships, ontology, selection, feature_metadata=None) -> list[dict]`. CLI can rewrite `tradeoff_and_operability` in an existing deep analysis JSON deterministically.

## Operability Enum Values
1. `ENDOGENOUS_RESPONSE` — data_direction_validated=false, predictor is endogenous/control response, or observed direction contradicts governing physics while data shows compensation
2. `CONFOUNDED` — Simpson/group reversal or unresolved time confounding
3. `CONSTRAINT_UNCONTROLLABLE` — ontology role is constraint/uncontrollable
4. `NOT_IDENTIFIABLE` — insufficient effective n, no usable numeric variation, competing state estimates indistinguishable
5. `LEVER_IDENTIFIED` — physics direction/form match, q ≤ 0.05, group/steady direction stable, no confounding, predictor directly controllable
6. `LEVER_OBSERVATIONAL` — fallback when none of the above apply

## Numeric Truth Mandate
- Every numeric schema field that cannot be estimated must use finite neutral values (0.0, q=1.0, slope=0.0) together with explicit validity flags (`insufficient_data=true` etc.)
- Never interpret neutral values as evidence
- Never call a relationship causal merely because a p-value is small
- Never invent physical constants absent from ontology/user context

## Verification Commands
```bash
# Compile check
python -m py_compile .claude/skills/industrial-deep-analysis/scripts/*.py

# Run on real CSTR data
python .claude/skills/industrial-deep-analysis/scripts/coverage_builder.py \
  --run-dir workspace/diagnostic-runs/202607300458012_cstr_catalyst_real

python .claude/skills/industrial-deep-analysis/scripts/derived_feature_builder.py \
  --run-dir workspace/diagnostic-runs/202607300458012_cstr_catalyst_real

python .claude/skills/industrial-deep-analysis/scripts/conditional_analysis.py \
  --run-dir workspace/diagnostic-runs/202607300458012_cstr_catalyst_real

# Validate with schemas
python -c "
import json
with open('workspace/diagnostic-runs/202607300458012_cstr_catalyst_real/enhancement/analysis_coverage.json') as f:
    c = json.load(f)
print(f'Columns: {len(c[\"columns\"])}')
# Check every cleaned-data column is present
with open('workspace/diagnostic-runs/202607300458012_cstr_catalyst_real/02_processed/cleaned_data.csv') as f:
    csv_cols = f.readline().strip().split(',')
covered = {col['column'] for col in c['columns']}
missing = [col for col in csv_cols if col not in covered]
print(f'Missing columns: {missing}')
"
```

## Dependencies
- Python ≥ 3.10
- numpy, pandas (standard library only otherwise)
- Task 2 `stat_utils.py` (read-only, imported via local path)

## Read-Only Baseline Rule
This skill must NEVER modify any file outside `RUN_DIR/enhancement/` or its own skill directory. Existing diagnostic skills, agents, schemas, scripts, and baseline `RUN_DIR` files are read-only.