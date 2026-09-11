---
name: industrial-ontology-builder
description: "Industrial diagnostic pipeline — domain ontology construction engine. Combines RAG retrieval, web search, and data self-description into a domain ontology model. Builds ontology.json (the foundation of the diagnostic pipeline), schema.json, and rag_deep_understanding.json, and runs the clarification gate. Use it as the prerequisite step of industrial root-cause analysis: infer physical meaning from sensor column names, extract process principles from the domain knowledge base, and confirm parameter roles from data self-description. Do NOT use for generic RAG retrieval or non-industrial knowledge bases / ontology. Trigger: ontology building, ontology, RAG retrieval, knowledge extraction, domain modeling, parameter semantic inference, ontology builder, context build, process knowledge base."
---

# Industrial Ontology Builder

Infer physical meaning from sensor column names, extract process principles from the RAG knowledge base, and confirm parameter roles from data self-description. `ontology.json` is the foundation of the entire diagnostic pipeline — this is not a template filler; let the data reveal the process type itself.

## Inputs / Outputs

### Inputs (in `RUN_DIR/00_input/`)

| File | Required | Description |
|------|----------|-------------|
| `input_manifest.json` | ✓ | Data column descriptions |
| `user_context.json` | ✓ | Process type, known issues, target columns |
| `run_config.json` | ✓ | Run configuration (contains `interaction_mode`; runtime may inject an `ontology` directive block) |
| `extracted_knowledge.json` | - | Knowledge extracted from reference documents (optional) |

> The runtime also injects an **ONTOLOGY_DIRECTIVE** block into the dispatch prompt (`ONTOLOGY_MODE: reuse|extend|full` + `ONTOLOGY_SOURCE`). This is the ontology asset reuse channel: when `reuse` hits, all construction is skipped and the step completes in seconds. See "Phase -1: Ontology Mode Dispatch" below.

### Outputs

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | Domain ontology (≥1KB, schema-valid) |
| `01_ontology/schema.json` | Normalized variable classification |
| `00_input/rag_deep_understanding.json` | RAG deep understanding + verification queue |
| `00_input/clarification_needed.json` | Clarification requests + `clarification_status` |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent context-builder --step context_builder

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent context-builder --step context_builder \
  --files 01_ontology/ontology.json,01_ontology/schema.json,00_input/rag_deep_understanding.json,00_input/clarification_needed.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `context-builder` subagent:

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "context-builder",
  task: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
REFERENCE_DIR=<reference-dir-or-empty>
PROCESS_DESCRIPTION=<user-provided-description>
USER_OBJECTIVE=<user-objective>
SKILL_PATH=<path-to-.claude/skills/industrial-ontology-builder>
SHARED_PATH=.claude/shared
INTERACTION_MODE=auto  # auto | interactive | minimal
ONTOLOGY_DIRECTIVE:  # from runtime prompt; omit for full build
  ONTOLOGY_MODE=<reuse|extend|full>
  ONTOLOGY_SOURCE=<store ontology absolute path, reuse/extend only>

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete protocol starting from Phase -1.

Key constraints:
- Not a template filler — let the data reveal the process type itself
- R2 performs only the Stage 1 pre-check, not full statistical analysis (that is the Data Processor's job)
- Inconsistency is a diagnostic signal — differences between ontology predictions and data observations are the strongest diagnostic clues
- Write all outputs into RUN_DIR — always use the absolute paths above; relative-path writes are forbidden
- Execute the Phase -1 mode dispatch first (when reuse hits, finish within 30 seconds; rebuilding is forbidden)
- After CP-2 passes, you must publish to the ontology asset store
- Default output language: Chinese
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/physics_inference_framework.md` (physics inference) and `resources/data_ontology_mapping_framework.md` (data-ontology mapping).

| Phase | Purpose |
|-------|---------|
| **-1** | **Ontology mode dispatch (deterministic, ≤30s)** — dispatch per ONTOLOGY_DIRECTIVE: `reuse` copies the asset ontology directly and ends after CP-2 validation; `extend` performs incremental construction only for newly added columns; `full` runs the complete flow. See `references/agent-protocol.md` Phase -1 |
| 0 | Load user context and probe the data — read input_manifest/user_context/run_config, directly probe the first 100 rows of the data file |
| 1 | Search the reference directory — scan REFERENCE_DIR to extract process keywords, parameter names, and known failure modes |
| 2 | Optional web research — at most 5 targeted searches (process type + key parameters + known relationships); **skipped in reuse/extend modes** |
| 3 | RAG knowledge retrieval + deep understanding — execute the R1-R4 protocol (semantic understanding / knowledge-data alignment / physical principle extraction / gap identification); **skipped in reuse mode**; **in extend mode, retrieval scope is limited to the new columns** |
| 4 | Bidirectional data-ontology mapping — build ontology.json; every parameter carries physical_meaning/unit/role/equipment attribution/physical relationships/inconsistency signals |
| 5 | Schema generation + validation — schema.json normalized classification + CP-2/CP-3 quality gates + **publish to the ontology asset store** |
| 2.5 | Clarification gate — auto mode infers via the physics_inference_framework L1-L5; interactive asks grouped questions; minimal only asks about critical parameters |

## Data Truth Mandate

**Every number written to JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart must be traceable to specific rows of the dataset |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion standard | If any condition is not met → mark as an excluded candidate and provide quantitative justification |
| Physical boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate/noise/missing extremes/range restrictions |
| Model assumptions | Linear approximation/steady-state assumption/distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Label every conclusion with confidence ± error margin |

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable outcomes
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → inspect existing artifacts; if partially usable, continue forward

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-ontology-builder>"
SHARED_PATH=".claude/shared"

# CP-2: Ontology schema gate
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/ontology_schema.json" \
  "$RUN_DIR/01_ontology/ontology.json" && \
  test "$(wc -c < "$RUN_DIR/01_ontology/ontology.json")" -ge 1024

# CP-3: Clarification gate
grep -q '"clarification_status" *: *"AUTO_RESOLVED\|USER_CONFIRMED"' \
  "$RUN_DIR/00_input/clarification_needed.json"

# Publish to ontology asset store — MANDATORY in every mode after CP-2 passes.
# Reused assets are where this pipeline's time savings come from: not publishing = a full rebuild for the same scenario next time.
node "$SHARED_PATH/scripts/ontology_store.mjs" publish --run-dir "$RUN_DIR" --build-mode <reuse|extend|full>
```

## Phase -1: Ontology Mode Dispatch (deterministic, ≤30s)

Executed before Phase 0. Read the ONTOLOGY_DIRECTIVE from the dispatch prompt (or the `ontology` block in run_config):

| ONTOLOGY_MODE | Action |
|---------------|------|
| `reuse` | (1) `ontology_store.mjs reuse --source "$ONTOLOGY_SOURCE" --run-dir "$RUN_DIR"` (copy the asset ontology) (2) Run CP-2 + CP-3 (**never skip validation**) (3) Write pipeline event `ontology_reused` (4) End directly; entering Phase 0-4 is **forbidden** (zero RAG / zero web / zero reference retrieval) |
| `extend` | (1) `ontology_store.mjs fingerprint <data>` compares against the ONTOLOGY_SOURCE ontology and diffs out newly added columns / columns with undetermined roles (2) Run Phase 1-4 only for the diff columns (retrieval limited to the diff columns) (3) Merge into the source ontology: add new signals/relationships; signals that already have `role=target/confounder` **must not have their role changed** — write conflicts to clarification_needed.json and route them through CP-3; update normal_range values falsified by the new data and mark `behavior_match: CONTRADICTED` (4) Version semantics per provenance (5) CP-2/CP-3 → publish (--build-mode extend) |
| `full` | Standard full Phase 0-5 flow, then publish (--build-mode full) |

When no directive is received, treat it as `full`. **All file-writing operations use the absolute paths given in the dispatch prompt** (relative-path writes by subagents are a historical root cause of failures).

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | Fix the JSON → rewrite ontology.json → re-validate |
| Missing input files | Report what is missing → indicate which of input_manifest/user_context/run_config is missing |
| RAG retrieval returns no results | Mark the gap in rag_deep_understanding.json → supplement with web research + physics_inference_framework |
| Clarification gate blocked | auto mode infers all unknown parameters via L1-L5; interactive/minimal write explicit questions to clarification_needed.json |
| ontology.json < 1KB | Expand parameter entries → complete physical_meaning/unit/role/physical relationships → re-validate |
