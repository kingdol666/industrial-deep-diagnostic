# Ontology Builder — Detailed Execution Reference

## Phase 0: Load User Context + Data Inspection

Read `00_input/user_context.json` and `00_input/input_manifest.json` if they exist.

From these files, extract:
- **process_type** (user-specified or auto-inferred)
- **known_issues**: Anomalies the user already knows about
- **target_columns**: Which columns are quality/defect metrics
- **column_name_patterns**: All column names and their inferred physical quantities
- **value_ranges**: Per-column min/max for physical quantity confirmation
- **categorical_columns**: Potential stratification dimensions

**DO NOT match against a fixed industry list.** The data's column patterns, value ranges, and statistical signatures define the process — not a pre-defined taxonomy.

## Phase 1: Search Reference Directory

If REFERENCE_DIR is provided and exists, recursively search it for relevant documents.

Read each file and extract:
- Equipment names, identifiers, manufacturers, models
- Process stages and their sequence (with typical parameter ranges)
- Variable descriptions, setpoints, operating limits, units
- **Known fault patterns and symptoms** — the most valuable reference content
- Causal relationships between variables (with quantitative estimates if available)
- Control logic descriptions (PID loops, cascade controls, feedforward)
- **Product/grade change procedures** — critical for identifying confounding variables
- Maintenance records and known degradation modes

Save results to `RUN_DIR/00_input/extracted_knowledge.json`.

**If REFERENCE_DIR is empty or not provided**: Skip this phase. The ontology will be built from Phase 3 (RAG knowledge retrieval) and Phase 4-5 (data↔ontology mapping + first-principles inference). If Phase 3 also fails (RAG unavailable), Phase 4-5 alone are sufficient — the diagnostic pipeline does not depend on any single knowledge source.

## Phase 2: Optional Web Research

If after reference search there are significant knowledge gaps, perform targeted web research (max 5 queries). Focus on process technology fundamentals, known failure modes, parameter physical meaning, quantitative relationships, and equipment specifications.

Label ALL web findings as EXTERNAL KNOWLEDGE. Save to `RUN_DIR/00_input/web_findings.md`.

## Phase 3: RAG Knowledge Retrieval + DEEP UNDERSTANDING

### 3.1 Delegate to rag-knowledge-builder Skill

Construct the invocation context from data inspection:
1. **domain**: Use `PROCESS_DESCRIPTION` if available; otherwise, describe the process from column name patterns
2. **target_concepts**: Quality/defect metrics (comma-separated)
3. **related_concepts**: All numeric columns minus targets and metadata (comma-separated)
4. **context_dimensions**: Categorical columns for stratification (comma-separated)
5. **run_dir**: Use `RUN_DIR`

Invoke via `Skill` tool:
```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<constructed_scenario_label>' target_concepts='<comma_separated>' related_concepts='<comma_separated>' context_dimensions='<comma_separated>' run_dir='<RUN_DIR>' interaction_mode='auto'"
})
```

**Fallback path**: If the `rag-knowledge-builder` skill is unavailable (Skill tool call fails), skip Phase 3 entirely. Proceed directly to Phase 4.

### 3.2 Four-Step Deep Understanding Protocol (R1-R4)

After receiving RAG output (`rag_ontology_draft.json`), execute the full four-step protocol. Each step is documented below.

#### Step R1: Semantic Comprehension

For each piece of RAG knowledge, articulate understanding in your own terms:

1. **Physics Principles**: What physical laws govern the causal relationships in the RAG knowledge?
2. **Domain Constraints**: What assumptions does the RAG knowledge implicitly make?
3. **Failure Modes**: What are the characteristic degradation mechanisms? Time scales? Tell-tale signatures?
4. **Confounders**: What operational factors typically affect multiple parameters simultaneously?

Output to `rag_deep_understanding.json` → `deep_understanding` section. See protocol for exact JSON schema.

#### Step R2: Knowledge-Data Alignment — STAGE 1 PRE-CHECKS

This is Stage 1 of a two-stage protocol. You run PRE-CHECKS on the raw data. The Data Processor runs Stage 2 THOROUGH VALIDATION.

For EVERY RAG claim, run PRE-CHECKS against raw data at DATA_PATH:

| RAG Claim Type | Pre-Check | Record Result | Queue for Stage 2? |
|---------------|-----------|---------------|---------------------|
| "Parameter X has normal range [a, b]" | Read column, check min/max | `range_validated`: true/false | If false → YES |
| "X causes Y via mechanism M with lag τ" | Check basic correlation sign | `direction_pre_check`: consistent/contradicted/untestable | ALWAYS YES |
| "X should correlate with Y positively" | Quick Pearson → check sign | `direction_pre_check` | If |r|>0.3 → YES |
| "X's effect on Y delayed by T seconds" | Read `expected_lag` from RAG | `lag_pre_check` | ALWAYS YES |
| "Degradation rate is R per unit time" | Simple linear trend slope | `rate_pre_check` | If testable → YES |
| "X and Y are confounded by Z" | Check if Z exists in columns | `confound_check`: Z_present/Z_absent | If Z_present → YES |

Output `claim_validations` and `validation_queue` to `rag_deep_understanding.json`.

#### Step R3: Physics Principle Extraction

From the RAG knowledge, extract REUSABLE physics principles:
1. **Conservation laws**: mass, energy, momentum
2. **Constitutive relations**: material behaviors (stress-strain, viscosity-temperature, reaction rate-concentration)
3. **Scaling laws**: flow ∝ √ΔP, cooling time ∝ thickness², reaction rate ∝ exp(-Ea/RT)
4. **Threshold physics**: yield stress, glass transition, resonance, cavitation

Output `reusable_physics_principles` to `rag_deep_understanding.json`.

#### Step R4: Gap-Aware Knowledge Integration

Identify what the RAG knowledge does NOT cover:
1. **Parameter-level gaps**: Which data columns have NO RAG concept match?
2. **Mechanism-level gaps**: Which statistical relationships lack RAG causal explanation?
3. **Domain-level gaps**: Is the RAG knowledge domain sufficiently close? (CLOSE_MATCH | PARTIAL_MATCH | ANALOGY | NO_MATCH)

Output `knowledge_gaps` to `rag_deep_understanding.json`.

### 3.3 Load ALL RAG Output Files and Map to Ontology

The rag-knowledge-builder skill produces 5 output files. Load and integrate ALL of them.

#### 3.3.1 Primary: rag_ontology_draft.json → Field Mapping

**Step 1 — Classify concepts into diagnostic signal categories:**

| RAG `concept_type` | Diagnostic Signal Category |
|---------------------|---------------------------|
| `measurement` | `inspection_signals[]` or `process_parameters[]` depending on role |
| `outcome` | `inspection_signals[]` |
| `composite_score` | `inspection_signals[]` |
| `predictor` / `input` | `process_parameters[]` |
| `control` | `control_variables[]` |
| `risk_factor` | `process_parameters[]` with `role: "confounder"` |
| `metadata` (context_dimensions) | `metadata_columns[]` |

**Step 2 — Map RAG v4 concept fields to diagnostic signal_v6 fields:**

| RAG v4 Concept Field | Diagnostic signal_v6 Field | Mapping Logic |
|----------------------|---------------------------|---------------|
| `name` | `name` + `column` | Check `terminology.context_aliases.data_column` for actual column name |
| `definition` | `physical_meaning` | Direct |
| `definition_confidence` | `physical_meaning_confidence` | Direct: KNOWN→KNOWN, INFERRED→INFERRED, UNKNOWN→UNKNOWN |
| `expected_value_range` | `normal_range` | Parse string to numeric array |
| `unit` | `unit` | Direct |
| `abnormal_indicates` | Enriches `discrepancy_signal` in Phase 4 | Context for data contradictions |
| `broader_concept` | Enriches `physical_meaning` context | IS-A parent taxonomy |
| `distinguish_from` | Disambiguation metadata | Resolve column-concept matching conflicts |
| `sibling_concepts` | Cross-reference metadata | `parameter_groups` grouping |
| `terminology.canonical_name` | `name` | If more readable than raw name |
| `terminology.synonyms` | Column name matching | Try synonyms as aliases |
| `terminology.abbreviations` | Column name matching | Short codes like "Tr", "QI" |
| `terminology.cross_language` | Column name matching | zh↔en mapping |
| `terminology.context_aliases` | Column name matching | `data_column` alias is PRIMARY hint |
| `concept_type` | `role` + signal category | See Step 1 table |
| `knowledge_source` | `knowledge_source` tag | Set to `"rag_retrieval"`; preserve original |

#### 3.3.2-3.3.5: Load Supporting Files

Read `rag_semantic_relationships.json`, `rag_external_knowledge.json` (versioned), `rag_integration_summary.md`, and `rag_quality_report.json`. Extract at minimum:
- `knowledge_source` per entity (RAG/web/ontology-inferred/reference/parameter_to_physics)
- `knowledge_confidence` (high/unknown/low/none)
- `relationship_type` (causal/correlative/confounding/threshold)
- `trigger_conditions`, `latency`, `reversibility`

### 3.4 Clarification Gate

If unresolved ambiguities remain after Phase 3, output `clarification_needed.json`:
- 3-5 CRITICAL questions (INTERACTION_MODE=interactive)
- 0 CRITICAL questions (INTERACTION_MODE=auto — attempt best inference, mark as INFERRED)
- Set importance: CRITICAL/HIGH/MEDIUM

## Phase 4: Build Ontology from Data + Knowledge

### 4.1 Parameter Identification

For EACH data column, produce: `column`, `name`, `unit`, `physical_meaning`, `physical_meaning_confidence`, `role`, `normal_range`, `knowledge_source`. For multi-zone sensors (T1-T12), produce a `parameter_groups.zone_temperature_group` entry with zone order and topology.

### 4.2 Process Stage Construction

Build `process_stages[]` from column name patterns, equipment references, and knowledge. Each stage must include the governing physical equations.

### 4.3 Discrepancy Signal Detection

Detect `discrepancy_signals` by comparing data behavior against ontology expectations:

| Signal Type | Detection |
|-------------|-----------|
| `range_violation` | Data value outside normal_range |
| `behavior_mismatch` | Trend/direction contradicts physics prediction |
| `pair_relationship_violation` | Two parameters that should correlate but don't |
| `parameter_role_conflict` | Parameter behaves as predictor but claimed as target |
| `timing_violation` | Expected lag not observed |

### 4.4 Physical Relationship Construction

Build `physics_relationships[]` table documenting for each pair: governing equation, quantitative prediction, statistical verification, confidence.

### 4.5 Causal Graph Construction

Build a directed causal graph with nodes for each parameter, metadata column, process stage, and equipment element. Edges must be annotated with `relationship_type` (causal/correlative/confounding/threshold), governing equation, direction, expected sign, and uncertainty.

## Phase 5: Write Final Outputs

Write all outputs to `RUN_DIR/01_ontology/`:
- `ontology.json` — the complete process ontology
- `schema.json` — normalized schema with variable classification
- If RAG was used: `rag_deep_understanding.json`

**Core principle**: Parameter physical meaning is foundational — document the full inference chain so downstream agents can judge its reliability.

## Output Verification

```bash
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/ontology_schema.json" "$RUN_DIR/01_ontology/ontology.json"
```

## Pipeline Events

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_start --agent context-builder --step context_builder
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_complete --agent context-builder --step context_builder --files 01_ontology/ontology.json,01_ontology/rag_deep_understanding.json
```
