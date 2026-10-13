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
- [ ] Check cumulative exposure feature is computed when an ontology-identified or name-heuristic poison/impurity/fouling column exists; otherwise it must be `not_applicable`
- [ ] Check time_since transition feature is computed if a primary-group/event column exists
- [ ] Check regime indicators are computed if `production_regime_filter.json` exists
- [ ] Check lag-aligned feature is computed only when nonzero optimal lag exists
- [ ] Verify `enhancement/derived_data.csv` exists and contains every `computed` feature column

### Phase 4: Run E3+E4+E3.5 — Conditional Analysis + Tradeoffs + Association Graph
- [ ] Execute `conditional_analysis.py --run-dir <RUN_DIR>` (writes `deep_data_analysis.json` AND `association_graph.json` — E3 already emits the graph; do NOT also run `association_graph_builder.py` in the same pass)
- [ ] Run `verify_enhancement.py --run-dir <RUN_DIR>` — it asserts all structural checks below in one pass; only investigate rules it reports FAIL on. The remaining items are kept as reference for what the verifier asserts:
- [ ] Verify `enhancement/deep_data_analysis.json` is created
- [ ] Verify at least one relationship exists for every ontology relationship that resolves to actual columns (INCLUDING process→process edges)
- [ ] For any relationship whose ontology marks `data_direction_validated=false`, verify `operability=ENDOGENOUS_RESPONSE` (compensation response, not cause)
- [ ] Verify BH-corrected q-values are in [0, 1] range and NOT exact 0.0 (floor values ≤1e-8 stay un-rounded; `p_floor_hit` must be true then)
- [ ] Verify validity flags are present per relationship, with `change_point_tested`/`outlier_influence_checked` reflecting real computations
- [ ] Verify `partial_full.method` is `full_order_ridge` or `stepwise_topk` (not `insufficient`) when n > p
- [ ] Verify `tradeoff_and_operability[]` is non-empty
- [ ] Check each tradeoff has `parameter`, `controllability`, `effects_on_targets`, `tradeoff_summary`, `operability_assessment`, `support_domain`, `extrapolation_warning`, `open_questions`
- [ ] Verify `enhancement/association_graph.json` is created with nodes/edges and edge semantics {supports, inhibits, contradicts}
- [ ] Verify graph edges carry `sign`, `confidence`, `causal_ceiling`, `ontology_contradiction`
- [ ] Standalone rerun possible: `association_graph_builder.py --run-dir <RUN_DIR>` rebuilds only the graph

### Phase 5: Cross-Validation
- [ ] Rerun `verify_enhancement.py` after any fix; it re-asserts every rule below (distinct column names, derived:true on computed features, formula/reason on skipped ones, no predictor==target, no metadata/control predictors, neutral zeros paired with validity flags). Additionally confirm `git status` shows no modifications to existing baseline files.

### Phase 6: Report
- [ ] Write execution summary to `<RUN_DIR>/enhancement/execution_summary.md`
- [ ] Include exact commands run, counts from `verify_enhancement.py` output, and any concerns