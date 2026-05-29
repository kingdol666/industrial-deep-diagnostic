# Ontology Extraction Checklist

Use this checklist to validate the ontology construction step.

## Structure Validation

- [ ] `scene.name` is set and descriptive
- [ ] `scene.process_type` is identified
- [ ] `scene.production_goal` is documented
- [ ] `scene.equipment` lists all relevant equipment
- [ ] `scene.stages` are ordered by sequence
- [ ] `scene.objectives` reflect the user's goal

## Signal Classification

- [ ] All data columns are mapped to signals
- [ ] `inspection_signals` contains quality/outcome measurements
- [ ] `process_parameters` contains process state measurements
- [ ] `control_variables` contains actively adjusted variables
- [ ] `events` contains discrete state changes
- [ ] `metadata_columns` contains identifiers and context
- [ ] No column appears in multiple categories

## Relationships

- [ ] All relationships have a physical or logical basis
- [ ] `from` and `to` reference valid signal names
- [ ] `type` is correctly classified (causal/correlative/control/physical)
- [ ] `direction` is correct (forward/bidirectional)
- [ ] `strength` reflects actual evidence
- [ ] Inferred relationships are marked with `inferred: true`

## Metadata

- [ ] Units are specified for all numeric signals
- [ ] Sampling rate is estimated or provided
- [ ] Batch ID is included if available
- [ ] Timezone is documented
- [ ] Time range is recorded

## Quality Checks

- [ ] No fabricated equipment or stages
- [ ] No speculative relationships without evidence
- [ ] Ontology is consistent with user-provided documentation
- [ ] Knowledge gaps are identified and documented
