# Orchestration Protocol: E0 → E8

## Phase Checklist

### E0: Readiness Check
- [ ] Verify all 13 baseline files exist and are non-empty
- [ ] Compute sha256 of `02_processed/cleaned_data.csv`
- [ ] Count rows and columns of cleaned data
- [ ] Create `enhancement/` and `enhancement/figures/` directories
- [ ] Write `enhancement/enhancement_manifest.json`
- [ ] If any P0 file missing → write `enhancement/enhancement_status.json { status: "BLOCKED" }` and halt

### E1: Coverage Builder
- [ ] Run `coverage_builder.py --run-dir <RUN_DIR>`
- [ ] Verify `analysis_coverage.json` exists and validates
- [ ] Assert every `02_processed/cleaned_data.csv` column appears in coverage

### E2: Derived Feature Builder
- [ ] Run `derived_feature_builder.py --run-dir <RUN_DIR>`
- [ ] Verify `derived_features.json` exists and validates
- [ ] At least one feature should be `computed` or `not_applicable` with reason

### E3: Conditional Analysis
- [ ] Run `conditional_analysis.py --run-dir <RUN_DIR>`
- [ ] Verify `deep_data_analysis.json` exists and validates
- [ ] Assert relationships[] has valid operability values
- [ ] Assert tradeoff_and_operability[] entries match relationships

### E5: Physics Bridge
- [ ] Run `physics_bridge_builder.py --run-dir <RUN_DIR>`
- [ ] Verify `physics_bridge.json` exists and validates
- [ ] Assert per-relationship verifications cover all deep_data relationships
- [ ] For any relationship with ontology `data_direction_validated=false`: assert `direction=MISMATCH` in the verification

### E6: Knowledge Fusion
- [ ] Run `knowledge_fusion.py --run-dir <RUN_DIR> --output <OUTPUT>`
- [ ] Verify `enhanced_knowledge.json` validates against schema
- [ ] Assert nodes cover all coverage columns + derived features
- [ ] Assert edges correspond to deep_data relationships
- [ ] Assert mechanism_chains from physics_bridge
- [ ] Assert enhancement_status reflects operability distribution

### E7a: Markdown Publisher
- [ ] Run `markdown_publisher.py --knowledge <JSON> --template <TMPL> --output <MD>`
- [ ] Verify output has ≥9 `##` sections
- [ ] Verify each core relationship has an embedded ```json claim block
- [ ] Verify zero hardcoded numbers (all from variable substitution)
- [ ] Verify no raw JSON field names in body text
- [ ] Verify Chinese primary language, English for enum values

### E8: Finalize
- [ ] Write `enhancement_status.json` with final status, warnings, artifact paths
- [ ] Print executive summary to stdout
- [ ] Return exit code 0 (success) or 1 (BLOCKED/FAILED)

## Skip Logic

Each script checks: if its output file exists AND is newer than all its input files, skip execution. This allows re-running the pipeline on a partially completed run.

## Input Patterns

Input freshness for each phase:
- E1: ontology.json, feature_summary.json, cleaned_data.csv, analysis_parameter_selection.json
- E2: ontology.json, cleaned_data.csv, analysis_coverage.json
- E3: ontology.json, cleaned_data.csv, analysis_coverage.json, derived_features.json, data_analysis_conclusion.json
- E5: ontology.json, diagnosis.json, evidence.json, confidence.json, reasoning_chain.json, visual_analysis.json, deep_data_analysis.json

## Error Handling

- Any script returning non-zero → pipeline halts, status becomes FAILED
- Missing optional files → skip gracefully with warning
- Schema validation failure → report the exact errors and halt
