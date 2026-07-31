# Agent Protocol: deep-analyst

## Phase Checklist

### Phase 1: Validate Inputs
- [ ] Confirm `RUN_DIR` exists and contains `01_ontology/`, `02_processed/`
- [ ] Verify `ontology.json`, `feature_summary.json`, `analysis_parameter_selection.json`, `data_analysis_conclusion.json` are present
- [ ] Confirm `cleaned_data.csv` (or `.json`) is readable
- [ ] Check optional `production_regime_filter.json` presence

### Phase 2: Run E1 — Coverage Builder
- [ ] Execute `coverage_builder.py --run-dir <RUN_DIR>`
- [ ] Verify `enhancement/analysis_coverage.json` is created
- [ ] Assert every cleaned-data column appears in `columns[]`
- [ ] Check that coverage_status values are consistent with ontology roles
- [ ] Verify metadata columns have `not_applicable` status with sentinel support_domain

### Phase 3: Run E2 — Derived Feature Builder
- [ ] Execute `derived_feature_builder.py --run-dir <RUN_DIR>`
- [ ] Verify `enhancement/derived_features.json` is created
- [ ] Check cumulative exposure feature is computed if `feed_sulfur_ppm` exists
- [ ] Check time_since transition feature is computed if event column exists
- [ ] Check regime indicators are computed if `production_regime_filter.json` exists
- [ ] Check lag-aligned feature is computed only when nonzero optimal lag exists

### Phase 4: Run E3+E4 — Conditional Analysis + Tradeoffs
- [ ] Execute `conditional_analysis.py --run-dir <RUN_DIR>`
- [ ] Verify `enhancement/deep_data_analysis.json` is created
- [ ] Check `reactor_temp_C → conversion_pct` relationship exists
- [ ] Verify `reactor_temp_C → conversion_pct` has `operability=ENDOGENOUS_RESPONSE`
- [ ] Verify BH-corrected q-values are in [0, 1] range
- [ ] Verify all seven validity flags are present per relationship
- [ ] Verify `tradeoff_and_operability[]` is non-empty
- [ ] Check each tradeoff has `parameter`, `controllability`, `effects_on_targets`, `tradeoff_summary`, `operability_assessment`, `support_domain`, `extrapolation_warning`, `open_questions`

### Phase 5: Cross-Validation
- [ ] All columns in `analysis_coverage.columns[]` have distinct `column` names
- [ ] All derived features with status `computed` have `derived: true`
- [ ] All derived features with status `not_applicable` have `derived: false` and nonempty `formula`/`physics_basis`
- [ ] No relationship has `predictor == target`
- [ ] No relationship has predictor in metadata/control cols
- [ ] Neutral finite values (0.0) in numeric fields are paired with explicit validity flags
- [ ] `git status` shows no modifications to existing baseline files

### Phase 6: Report
- [ ] Write execution summary to `.superpowers/sdd/doe-enhance-plan/task-3-report.md`
- [ ] Include exact commands run, counts, and any concerns
- [ ] Record commit hash after committing only Task 3 files