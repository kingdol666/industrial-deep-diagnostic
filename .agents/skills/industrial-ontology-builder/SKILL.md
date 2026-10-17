---
name: industrial-ontology-builder
description: "Industrial diagnostic pipeline — domain ontology construction engine. Combines RAG retrieval, web search, and data self-description into a domain ontology model. Builds ontology.json (the foundation of the diagnostic pipeline), schema.json, and rag_deep_understanding.json, and runs the clarification gate. Use it as the prerequisite step of industrial root-cause analysis: infer physical meaning from sensor column names, extract process principles from the domain knowledge base, and confirm parameter roles from data self-description. Two profiles: `profile=diagnosis` (default — column/process ontology for root-cause diagnosis, unchanged) and `profile=doe` (designed-experiment ontology: factor/response entities, units, expected directions, specs, confounders, limitations, design region; with `data_stage=design_only` it builds from prior knowledge alone — process description + RAG + web + physics priors — before any response is measured, marking every response observed_data_behavior as NOT_APPLICABLE and never fabricating measured behaviour). Do NOT use for generic RAG retrieval or non-industrial knowledge bases / ontology. Trigger: ontology building, ontology, RAG retrieval, knowledge extraction, domain modeling, parameter semantic inference, ontology builder, context build, process knowledge base, DOE ontology, design of experiments ontology, prior-knowledge ontology, design_only ontology, factor response ontology, 试验设计本体, 先验本体, 因子响应本体."
---

# Industrial Ontology Builder

Infer physical meaning from sensor column names, extract process principles from the RAG knowledge base, and confirm parameter roles from data self-description. `ontology.json` is the foundation of the entire diagnostic pipeline — this is not a template filler; let the data reveal the process type itself.

## Profile Dispatch

| `PROFILE` | `DATA_STAGE` | When | What it builds |
|-----------|--------------|------|----------------|
| `diagnosis` (default) | `collected` | the 9-stage diagnosis pipeline (Step 2) | column/signal/event/relationship ontology from data + RAG; **behaviour identical to before this profile existed** |
| `doe` | `collected` | designed-experiment run that already has measurements | factor (`control_variables`) / response (`inspection_signals`) entities + expected directions + specs + confounders + design region, enriched by data behaviour |
| `doe` | `design_only` | experiment designed, responses **not measured yet** | the same entity set built from **prior knowledge only**: process description + `doe_context.json`/`analysis_context.json` declarations + RAG + web + physics priors. Every response/behaviour field is `NOT_APPLICABLE` / `UNVERIFIED` — measured behaviour must never be invented |

`PROFILE`/`DATA_STAGE` arrive in the dispatch prompt (or as `run_config.ontology{profile,data_stage}`); missing → `diagnosis` / `collected` (legacy behaviour).

### DOE ontology shape (additive — the diagnosis path is untouched)

* factors → `signals.control_variables[]` (`role: "control"`, `control_type: "setpoint"`, `normal_range: [min,max]`, optional `expected_sign`)
* responses → `signals.inspection_signals[]` (`role: "target"`, `target`/`tolerance` from specs)
* covariates → `signals.process_parameters[]` (`role: "confounder"`); blocks → `signals.metadata_columns[]` (`role: "batch_id"`)
* relationships: factor → response with `type: "causal"|"physical"` **only when a direction is declared** (`expected_sign`), plus `mechanism`, `inferred: true`, `data_direction_validated: "untested"`; never invent a direction
* a `doe` block carries `profile`, `scene_key`, `data_stage`, `design_type`, `design_region`, `constraints`, per-factor/response `confidence`, and `limitations`
* `provenance` block (mandatory, read by the deterministic stage): `{engine: "industrial-ontology-builder", profile, build_mode, data_stage, rag_used, web_used, physics_prior_used, source}` — report `rag_used`/`web_used` truthfully; the deterministic reuse path reports both `false`

In `data_stage=design_only` the ontology is a **prior**, not a finding: `observed_data_behavior: "NOT_APPLICABLE"`, `behavior_match: "UNVERIFIED"`, `physical_meaning_confidence: KNOWN|INFERRED` only. Claims that need measurements are written into `limitations`, never into behaviour fields.

## Inputs / Outputs

### Inputs (in `RUN_DIR/00_input/`)

| File | Required | Description |
|------|----------|-------------|
| `input_manifest.json` | ✓ (diagnosis) | Data column descriptions |
| `user_context.json` | ✓ (diagnosis) | Process type, known issues, target columns |
| `run_config.json` | ✓ | Run configuration (contains `interaction_mode`; runtime may inject an `ontology` directive block) |
| `extracted_knowledge.json` | - | Knowledge extracted from reference documents (optional) |
| `doe_context.json` | ✓ (`profile=doe`) | Platform/user DOE declaration: factors/responses with `col`/unit/range/specs/`expected_sign`/`physical_meaning`/`ontology_signal`, constraints, design region, `data_stage` |
| `analysis_context.json` | ✓ (`profile=doe`) | The single resolved context (same declarations + `provenance.assigned_by`); authoritative column list for the DOE ontology |
| `extracted_knowledge.json` | - | Knowledge extracted from reference documents (optional) |

> `profile=doe` + `data_stage=design_only` builds **without any data file** — `DATA_PATH` may be absent/empty (a declared run table whose response columns are all empty is also accepted). `profile=diagnosis` and `data_stage=collected` keep the original requirement: `DATA_PATH` must exist.

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
  task: `DATA_PATH=<data-file-path-or-empty-when-design_only>
RUN_DIR=<run-dir-path>
REFERENCE_DIR=<reference-dir-or-empty>
PROCESS_DESCRIPTION=<user-provided-description>
USER_OBJECTIVE=<user-objective>
SKILL_PATH=<path-to-.claude/skills/industrial-ontology-builder>
SHARED_PATH=.claude/shared
INTERACTION_MODE=auto  # auto | interactive | minimal
PROFILE=diagnosis       # diagnosis (default) | doe
DATA_STAGE=collected    # collected (default) | design_only
CONTEXT_PATH=<RUN_DIR/00_input/analysis_context.json>   # required for PROFILE=doe
DOE_CONTEXT_PATH=<RUN_DIR/00_input/doe_context.json>    # optional, when the platform emitted it
ONTOLOGY_DIRECTIVE:  # from runtime prompt; omit for full build
  ONTOLOGY_MODE=<reuse|extend|full>
  ONTOLOGY_SOURCE=<store ontology absolute path, reuse/extend only>

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete protocol starting from Phase -1.

Key constraints:
- Not a template filler — let the data reveal the process type itself
- PROFILE=doe, DATA_STAGE=design_only: build from prior knowledge only; DATA_PATH may be empty;
  responses carry observed_data_behavior="NOT_APPLICABLE" and behaviour_match="UNVERIFIED";
  never write a measured value, range or direction you did not get from a declaration, document or first principle
- PROFILE=diagnosis behaviour is unchanged by the DOE profile
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
| 0 | Load user context and probe the data — read input_manifest/user_context/run_config, directly probe the first 100 rows of the data file (`profile=doe`: read `doe_context.json` + `analysis_context.json`; in `design_only` there may be no data file — the declarations are the ground truth) |
| 0D | **DOE profile only** — materialise factor/response/covariate/block entities from the declarations, specs and design region, with prior-only behaviour fields. See `references/agent-protocol.md` Phase 0D |
| 1 | Search the reference directory — scan REFERENCE_DIR to extract process keywords, parameter names, and known failure modes |
| 2 | Optional web research — at most 5 targeted searches (process type + key parameters + known relationships); **skipped in reuse/extend modes** |
| 3 | RAG knowledge retrieval + deep understanding — execute the R1-R4 protocol (semantic understanding / knowledge-data alignment / physical principle extraction / gap identification); **skipped in reuse mode**; **in extend mode, retrieval scope is limited to the new columns**; in `design_only` R2 validates *declarations/principles*, never response behaviour |
| 4 | Bidirectional data-ontology mapping — build ontology.json; every parameter carries physical_meaning/unit/role/equipment attribution/physical relationships/inconsistency signals (`design_only`: prior mapping only) |
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

# DOE profile — same CP-2 gate, but the asset is published with its semantic identity
# (profile + scene_key + context_fp + data_stage) so the next run can exact-reuse it:
node "$SHARED_PATH/scripts/ontology_store.mjs" publish --run-dir "$RUN_DIR" \
  --scene <scene_key> --profile doe --build-mode <reuse|extend|prior_knowledge|full> \
  --data-stage <design_only|collected> --context-fp "<sha256:… from doe_ontology_prepare>"
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
| `PROFILE=doe` + `DATA_STAGE=design_only` and no data file | Not a failure — build from `doe_context.json`/`analysis_context.json` + RAG + web + physics priors; every response behaviour field stays NOT_APPLICABLE; never invent measurements |
| `PROFILE=doe` declaration for a factor/response has no unit or no spec | Write the entity anyway (`unit: null`) and record the gap in `limitations` + the clarification queue — dropping it silently is forbidden |
| Deterministic stage already built the DOE ontology (`doe_ontology_prepare.py` reported `built`/`prior_knowledge`) | Do not rebuild: enrich the existing `01_ontology/ontology.json` (add semantics/RAG evidence), keep the declared columns/codes, and re-publish with `--build-mode extend` |
