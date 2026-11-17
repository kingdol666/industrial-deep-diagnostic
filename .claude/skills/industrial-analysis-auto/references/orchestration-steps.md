# Industrial Analysis Auto — Orchestration Steps (full protocol detail)

> Moved verbatim from `SKILL.md`. The slim `SKILL.md` is the scheduling view (pipeline shape, checkpoints,
> hard rules); this file carries the full step-by-step protocol, gate invocations in context, budgets, standing
> rule tables, recovery and event logging. Read the section named for the step you are about to execute.

## Inputs / Outputs

### Inputs
| Input | Required | Description |
|-------|----------|-------------|
| CSV/XLSX/Parquet data file | ✓ | Industrial sensor/process data (CSV, XLSX, Parquet) |
| run_config.json (auto-generated) | ✓ | Run configuration (interaction_mode etc.) |
| Reference docs (optional) | - | Process reference documents under data/references/ |

### Outputs
| Output | File | Gate |
|--------|------|:----:|
| Diagnostic ontology | 01_ontology/ontology.json | CP-2 |
| Data analysis conclusion | 02_processed/data_analysis_conclusion.json | CP-4 |
| Diagnosis conclusion | 04_diagnostics/diagnosis.json | CP-5 |
| Quality gate result | 05_review/judge_feedback.json | CP-6 |
| Final report | report.md / run_summary.json | CP-7 |
| Physical audit | optimizer.md | CP-8 |
| HTML report | diagnostic-report.html / 05_review/html_review.json | CP-9 |

---

## Main-Agent Steps

### Step 0: Setup

```bash
SKILL_PATH="<this-skill-directory>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"

# Create run directory
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --mode fast|full --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"

# Setup Python venv
node "$SHARED_PATH/scripts/uv_env_setup.mjs"
```

`setup.mjs` bootstraps `run_manifest.json` + `.pipeline_events.jsonl` with `run_initialized` event.

**Shell compatibility convention (mandatory)**: all bash commands must not use cmd built-in syntax (`cd /d`, `dir`, backslash paths).
For cross-drive/directory switching, invoke directly with absolute paths (`node "D:/.../setup.mjs"`) or use `cd "D:/path" && cmd`.
(Verified in practice: `cd /d D:\...` fails and retries under POSIX bash, wasting ~1 minute.)

**RAG availability pre-check (3s fast-fail)**: execute once at the end of Step 0 and record in run_config:
```bash
curl -m 3 -s http://localhost:8764/health >/dev/null 2>&1 && RAG_AVAILABLE=true || RAG_AVAILABLE=false
```
`RAG_AVAILABLE=false` → ontology-builder goes straight to the `parameter_to_physics.json` fallback path and skips Phase 2/3
(avoids repeated runtime probing and idle web-search spinning under uncontrollable networks).

### Step 0.5: Adaptive Data Preprocessing + Heterogeneous Stage (E-1 && E-1H, one chained command)

Before inspecting, normalize ANY user data source into the canonical pipeline
input. Run the E-1 stage when the data is a directory, an Excel workbook
(xlsx/xlsm with multiple sheets), a JSON dump, Markdown/HTML tables, or a
mix of formats. E-1 and the heterogeneous-data stage E-1H
(`industrial-hetero-preprocessor`: profile / 2D-map / image-stream /
time-anchored-text sources → deterministic `HX-*` scalar features anchored to
the canonical time axis) form ONE chained command — E-1H runs immediately
after E-1 and can never be skipped on its own:

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/../../industrial-data-preprocessor/scripts/data_preprocessor.py" \
  --data-path <data_file_or_dir> --output "$RUN_DIR/00_input" --name <scene_name> \
&& node "$SKILL_PATH/../../industrial-data-preprocessor/scripts/quality_gate.mjs" --run-dir "$RUN_DIR" \
&& uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/../../industrial-hetero-preprocessor/scripts/build.py" \
  --raw-path <data_file_or_dir> --run-dir "$RUN_DIR" \
&& node "$SKILL_PATH/../../industrial-hetero-preprocessor/scripts/quality_gate.mjs" --run-dir "$RUN_DIR" --raw-path <data_file_or_dir>
```

E-1 writes `00_input/preprocessed_data.csv` (canonical table), a
`preprocessing_report.json` audit (per-source disposition, encoding/delimiter/
sheet adaptation, merge keys), and preserves non-tabular docs in
`00_input/context/`. The chained E-1 gate re-verifies the canonical table and
its audit before E-1H runs. If the report says `no_tabular_data`, the E-1 gate
exits 2 and the chain stops — report the audit to the user instead of proceeding.
E-1H writes only `07_hetero/**` plus the always-marker
`07_hetero/hetero_manifest.json` (written even when no heterogeneous source
exists, so "stage skipped" can never masquerade as "stage ran").
Read `skill://industrial-data-preprocessor` for the full adaptation matrix.

**Chain state semantics — decide `DATA_PATH` from `07_hetero/hetero_manifest.json` + gate exit code**:

| Outcome | Action |
|---------|--------|
| `status: "ok"` AND `outputs.joined_table` non-empty | `DATA_PATH = 07_hetero/preprocessed_data_hetero.csv` for ALL downstream steps; write `run_config.hetero {enabled: "auto", anchor_path, manifest, anchor_sha256}`; append the `hetero` provenance block to `input_manifest.json` |
| `status: "no_hetero_sources"` or `"off"` | Everything stays as-is — `DATA_PATH = 00_input/preprocessed_data.csv`; no other behavior change |
| `quality_gate.mjs` exit 3 (gate-fail) | Fix and re-run the chain; proceeding with a failed gate is forbidden |
| `build.py` exit 4 (`raw_path_unresolved`) | Stop and ask the user for the raw data folder path — never treat it as `no_hetero_sources` |

Event log (execution proof; the `hetero_preprocess` step id is already registered in `setup.mjs` and `pipeline-log-check.mjs`):

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_start --agent main-agent --step hetero_preprocess
# …the chained command above…
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step hetero_preprocess \
  --files 07_hetero/hetero_manifest.json,07_hetero/column_contract.json,07_hetero/explicit_cols.json
```

### Step 1: Inspect

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

Log pipeline events:
```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_start --agent main-agent --step inspect \
  --data '{"data_path":"<data_path>"}'

node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step inspect \
  --files 00_input/input_manifest.json,00_input/user_context.json
```

**Write DATA_PATH back into run_config (fingerprint contract, mandatory)**: the ontology asset store fingerprints the data at publish time via `run_config.data_path` / `input_manifest.files[]`; if neither is filled, the entry is stored with `schema_fp=null` and fast-reuse can NEVER hit (observed 2026-10-13: published ontology unusable for reuse). After Step 1, set `00_input/run_config.json` → `data_path: "<DATA_PATH>"` (and prefer `input_manifest.files: [{path: "<DATA_PATH>"}]`). When the Step 0.5 chain ended `status: "ok"`, `<DATA_PATH>` is the joined table `07_hetero/preprocessed_data_hetero.csv`, so `input_manifest.files[]` records the joined table plus the `hetero` provenance block (not the anchor alone).

### Step 2-F: Ontology Deterministic Fast Path (reuse hit ≤60s, plan v5 F1)

**Before** dispatching Step 2, attempt the deterministic fast path (pure script asset copy + validation, no semantic judgment; outside the scope of Blacklist #2 "main agent executes the sub-agent protocol"):

```bash
node "$SHARED_PATH/scripts/ontology_store.mjs" fast-reuse \
  --data <DATA_PATH> --run-dir "$RUN_DIR" [--scene <scene_key>]
```

- Output `fastPath:true` → write an event recording the skip reason (satisfies the strictly-sequential `not_applicable` convention):

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step context_builder \
  --data '{"fastpath":true,"reason":"store reuse — deterministic fast path"}'
```

  Then write a `clarification_auto_inferred` event (the fast path has already generated `00_input/clarification_needed.json` AUTO_RESOLVED), and **jump directly to Step 3** — do not dispatch the context-builder sub-agent, do not enter hub wait. CP-2 (schema validation + ≥1KB) is already enforced inside fast-reuse; on failure it automatically rolls back and returns fastPath:false.
- Output `fastPath:false` → proceed with the Step 2 sub-agent dispatch below (extend/miss still require LLM semantic judgment; the Phase -1 instructions remain in effect).
- When `run_config.ontology.mode` is `full`, skip Step 2-F (user forces a rebuild).

### Step 2 + 2.5: Ontology Builder

Read `skill://industrial-ontology-builder` and dispatch via `Agent({subagent_type: "context-builder", ...})`. Key:
- `DATA_PATH`, `RUN_DIR`, `SKILL_PATH`, `SHARED_PATH` must be absolute paths
- `SKILL_PATH` = path to `industrial-ontology-builder` skill directory
- `INTERACTION_MODE` = `auto` (default for FULL-AUTO)
- **Forward the `## Ontology Directive` (ONTOLOGY_MODE / ONTOLOGY_SOURCE) from the runtime prompt** into the dispatch task — the agent executes the Phase -1 mode dispatch based on it:
  - `reuse` hit: the agent copies the asset ontology and completes this step with CP-2 validation within 30 seconds (the largest time win in this pipeline; rebuilding is forbidden)
  - `extend`: incrementally build only the new columns, then merge
  - `full`: standard full flow
- **Sub-agent stop-loss cap**: if cumulative waiting for `ontology.json` exceeds **8 minutes** without completion → abort the sub-agent task; the main agent builds a minimal valid ontology locally per the fallback protocol using `parameter_to_physics.json` (≤3 minutes). Three consecutive serial long waits are forbidden (180s+240s+300s=12 minutes of idle spinning was the largest measured waste).
- All file writes after dispatch must use absolute paths (sub-agent relative-path writes are a historical root cause of failures).

**CP-2**: `ontology.json` ≥1KB + schema-valid — deterministic gate (exit 0 ok | 2 stage absent | 3 fail):
```bash
node "$SHARED_PATH/../../.claude/skills/industrial-ontology-builder/scripts/quality_gate.mjs" --run-dir "$RUN_DIR"
```
**Immediately after CP-2 passes, publish to the ontology asset store (mandatory in all modes; this is the prerequisite for future reuse hits)**:
```bash
node "$SHARED_PATH/scripts/ontology_store.mjs" publish --run-dir "$RUN_DIR"
```
**CP-3**: `clarification_needed.json` contains `AUTO_RESOLVED` or `USER_CONFIRMED` — enforced by the CP-2 gate invocation above

### Step 2P (parallel with Step 2, full mode and >20K rows only; fast mode: merged into Step 3): Data Profiling Pre-Pass

Read `run_mode` before dispatch. Only `full` mode with >20K rows launches the separate pre-profile agent in parallel with Step 2. In `fast` mode (or ≤20K rows), Step 3 performs Phase 0-1 in-process; do not launch a duplicate agent. If Step 2P is skipped, call the legal event helper:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event artifact_check_complete --agent main-agent --step inspect \
  --data '{"skipped_stage":"data_profile_prepass","reason":"<fast_mode|below_20k_rows>","integrity_check":"NOT_APPLICABLE"}'
```

The event helper mirrors `{stage, reason, event}` into `run_manifest.execution_policy.audit.skipped_stages`; do not hand-edit the manifest. Semantic analysis (discrepancy/R2 validation) still waits for ontology in both modes.

### Step 3 + 3.3: Data Processor

Read `skill://industrial-data-processor` and dispatch via `Agent({subagent_type: "data-processor", ...})`. **ontology_first** — read ontology before any statistical work. If `02_processed/pre_profile.json` exists (Step 2P artifact), resume from its conclusions and skip duplicate probing.

**VLM early-dispatch rule (A4)**: VLM depends on `plot_manifest.json` + `vlm_input_manifest.json`; when dispatched, start as soon as those files exist and overlap with remaining data processing. In `fast` mode dispatch only if a vision-capable model is reachable and there are CRITICAL plots, capped at 4; otherwise require `image_captions.json` L4 fallback and record the skip:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event artifact_check_complete --agent main-agent --step data_processor \
  --data '{"skipped_stage":"vlm_analysis","reason":"<no_vision_model|no_critical_plots|fast_mode_skip>","integrity_check":"NOT_APPLICABLE"}'
```

The logger mirrors the skip into execution_policy for finalizer verification. In `full` mode, VLM is attempted when the vision model is reachable; unavailable VLM requires the same caption fallback and a recorded skip. The large-data regime detector is vectorized (numpy path above 20K rows).

Post-processing after agent completes:
```bash
SKILL_PATH_DATA_PROCESSOR="$PROJECT_ROOT/.claude/skills/industrial-data-processor"
node "$SKILL_PATH_DATA_PROCESSOR/scripts/data-processor-finalize.mjs" "$RUN_DIR"
```

Event proof (deterministic remediation to guard against OMP sub-agents omitting execution events — idempotent and harmless if the sub-agent already emitted them):
```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent data-processor --step data_processor \
  --files 02_processed/data_analysis_conclusion.json,03_figures/plot_manifest.json
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step data_processor
```

**CP-4**: `data_analysis_conclusion.json` exists + `plot_manifest.json` has plots > 0

### Step 4: Diagnostician

Read `skill://industrial-diagnostician` and dispatch via `Agent({subagent_type: "diagnostician", ...})`. Fuses data + ontology + physics + VLM + time-lag → diagnosis/evidence/confidence/reasoning_chain.

For repair loops, pass `REPAIR_INSTRUCTIONS=<instructions>`; for rounds 2/3 also pass `REPAIR_SCOPE=<files>` (from the repair_scope mapping in judge_feedback.json, see Step 5a). Files outside the scope are restored from the best_round snapshot and marked `carried_over: true` — **not recomputed**.

**CP-5**: All 4 diagnosis outputs schema-valid + quality-check passes

### Step 5a: Judge

Read `skill://industrial-judge` and dispatch via `Agent({subagent_type: "judge", ...})`. 10-item quality gate → `judge_feedback.json`. The feedback must contain a **structured repair scope** `repair_scope: [{dimension, files, instructions}]` (Step 4 repair rounds recompute in a targeted way based on it, avoiding full recomputation of the 4 diagnosis JSONs). In rounds 2/3 the Judge re-reviews only in-scope dimensions plus previous-round blocking re-checks; already-pass dimensions reference previous-round conclusions.

### Step 5b: Physical Auditor (Pre-Report) — **full mode only**

Read `skill://industrial-physical-auditor` with `PRE_REPORT_AUDIT=true`. Dispatch via `Agent({subagent_type: "report-reviewer", ...})`. Runs **parallel** with Judge. Outputs `optimizer_preflight.md`.

**Run-mode rule**: `fast` mode skips 5b — CP-8 final audit (Step 7) remains mandatory. Record the skip via the legal event helper; the helper mirrors it into the manifest for finalizer verification:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event artifact_check_complete --agent main-agent --step judge \
  --data '{"skipped_stage":"pre_report_audit","reason":"fast_mode","integrity_check":"NOT_APPLICABLE"}'
```

This is a skip of a redundant pre-report pass only; it never skips the final physical audit or CP-8 ENDORSED gate. Do not write `run_completed` before finalizer passes.

> **Repair loop (Best-of-3 + anti-oscillation)**: see `references/repair-loop-and-gates.md`.

### Step 6: Reporter

Read `skill://industrial-reporter` and dispatch via `Agent({subagent_type: "reporter", ...})`. **Judge-gated**: only proceed if verdict==pass ∧ score≥90 OR `judge_repair_summary` proves 3 rounds exhausted.

**Section contract (inline into the dispatch prompt — lint L5 enforces it)**: report.md MUST contain 9 keyword sections — 执行摘要 / 核心证据(对齐图) / 诊断结论 / 证据全景 / 竞争假设(排除逻辑) / 详细推导(推理过程) / 推理链 / 统计(数据统计) / 行动方案(局限). Fast mode additionally caps: ≤250 lines, ≤6 embedded figures.

**CP-7**: `report.md` + `run_summary.json` exist

**CP-7L (pre-audit lint, mandatory before Step 7)**: run the deterministic lint and hand any FAIL back to the reporter as a targeted repair list — never dispatch the final audit over a lint-FAIL report:

```bash
node "$SHARED_PATH/../../.claude/skills/industrial-analysis-auto/scripts/pre_audit_lint.mjs" "$RUN_DIR"
```

Covers the seven mechanically-checkable defect classes observed in practice
(steps→time unit claims vs time_lag unit semantics, plot ink, run_summary
verbatim, report numbers vs diagnosis, sections, figure refs). Report-only —
it never edits artifacts; the final audit keeps full semantic authority.

### Step 7: Physical Auditor (Final)

Read `skill://industrial-physical-auditor` (final mode) and dispatch via `Agent({subagent_type: "report-reviewer", ...})`. Audits `report.md` → `optimizer.md`.

**CP-8**: `optimizer.md` contains `ENDORSED` — deterministic gate (exit 0 ok | 2 audit not run | 3 fail):
```bash
node "$SHARED_PATH/../../.claude/skills/industrial-physical-auditor/scripts/quality_gate.mjs" --run-dir "$RUN_DIR"
```

### Step 8: HTML Visualizer (AUTO)

Read `skill://industrial-html-visualizer` and dispatch via `Agent({subagent_type: "html-visualizer", ...})`. **Non-interactive** — after CP-8 ENDORSED, immediately launch without asking. Only skip if `00_input/html_opt_out` exists.

### Step 8.5: HTML Reviewer

Read `skill://industrial-html-reviewer` and dispatch via `Agent({subagent_type: "html-reviewer", ...})`. Review → pass/needs_revision.

**CP-9**: `diagnostic-report.html` ≥5120B + `html_review.json` verdict=pass

### Step 9: Finalize

```bash
SKILL_PATH="<this-skill-directory>"
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR" "$SKILL_PATH"
```

Present: executive summary + key findings + diagnosis type + confidence + recommendations + optimizer highlights + workspace/HTML paths.

### Step 9.5: Experience Distill (non-blocking, deterministic, zero-LLM)

After finalize, distill this run's reusable experience and write it to the RAG
knowledge base so future runs of similar scenes can retrieve it (read-side
credibility `accumulated_diag_*` is already wired in the engine):

```bash
# 1) deterministic distill (extraction only — never authors content)
node "$SHARED_PATH/scripts/experience_distill.mjs" "$RUN_DIR" --repo-root "$PROJECT_ROOT"
# → 06_experience/experience_candidates.jsonl

# 2) upload when the RAG engine is up AND judge ≥ 90 (server enforces the gate)
if [ "$RAG_AVAILABLE" = "true" ] && curl -m 3 -s http://localhost:8764/health >/dev/null 2>&1; then
  curl -s -X POST http://localhost:8764/accumulate \
    -H "Content-Type: application/json" -H "X-API-Key: ${RAG_API_KEY:-}" \
    -d "{\"run_dir\": \"$RUN_DIR\"}" || true
fi
```

Event proof: `append-pipeline-event --event step_complete --agent main-agent --step experience_distill --files 06_experience/experience_candidates.jsonl`.
Any failure (RAG down, candidates missing, upload error) → append `experience_skipped`
with the reason and continue — this step MUST NEVER block the pipeline. Contamination
red lines enforced in code: benchmark-scene `scene_fault_pattern` entries are rejected
server-side; payload text is capped at mode-level length; negative samples stay
`accumulated_diag_unverified`.

### Step 10: Enhanced Diagnosis (conditional step — deep enhancement E0-E8)

Read the `## Enhancement Directive` (ENHANCEMENT_POLICY / ENHANCEMENT_INTENT_HIT) from the runtime prompt:

| ENHANCEMENT_POLICY | Action |
|--------------------|--------|
| `on` (explicit user request or intent hit) | After baseline Step 9 completes, execute the enhancement chain in the **same run directory**: `node "$PROJECT_ROOT/.claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs" --run-dir "$RUN_DIR"`. E0-E1-E6 are all deterministic scripts with zero LLM; reuse the ontology, **never rebuild the baseline**. If E0 reports BLOCKED (baseline artifacts incomplete) → write enhancement_status.json{status:blocked} and close out gracefully, **do not mark the run as failed**. On completion, append-pipeline-event `--event step_complete --step enhance`, and append one line to the end of report.md: "Deep enhancement analysis generated: enhancement/enhanced_analysis.md" |
| `off` | Skip. append-pipeline-event `--event enhance_skipped --data '{"reason":"policy_off"}'` |
| `auto` no intent hit | Skip. `--event enhance_skipped --data '{"reason":"no_intent"}'`; at the end of the summary, tell the user: "If you need deep enhanced diagnosis (conditional analysis / physics bridging / correlation graph), it can be launched for this run with one click" |

Enhancement artifacts land in `RUN_DIR/enhancement/` (enhanced_analysis.md / enhanced-analysis.html / enhancement_status.json),
fully isolated from baseline artifacts; the E1-E6 mtime skip mechanism makes repeated execution incremental and cheap.

---

## Step Turn Budgets (advisory governance, not hard truncation)

| Step | Suggested turn cap | Action when exceeded |
|------|--------------------|----------------------|
| Step 0-1 setup/inspect | 4 | Check script invocation style (mostly path/syntax retries) |
| Step 2 ontology (reuse hit) | 2 | Main agent performs local validation directly |
| Step 2 ontology (full) | 6 | Triggers the 8-minute stop-loss cap |
| Step 3 data processing | 10 | Check whether pre_profile was consumed |
| Step 4 diagnosis | 12 | Check input artifact integrity |
| Step 5a/5b review | 6 | Reference previous-round conclusions |
| Step 6-7 report+audit | 8 | Streamline sections |
| Step 8-9 HTML+finalize | 6 | Degrade to static mode |
| Step 10 enhancement | 3 | Script chain is zero-LLM; exceeding the cap = anomaly |

If the same Step exceeds its budget 2x consecutively → record a `step_overbudget` pipeline event and surface it in run_summary.

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate / noise / missing extremes / range limits |
| Model assumptions | Linear approximation / steady-state assumptions / distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Annotate each conclusion with confidence ± error margin |

---

## Agent Decoupling

Sub-agents communicate ONLY through workspace files, never through main-agent context:

```
Ontology Builder  → 01_ontology/ontology.json, clarification_needed.json, rag_deep_understanding.json
Data Processor    → 02_processed/*, data_analysis_conclusion.json, 03_figures/* (includes visual_analysis.json)
Diagnostician     → 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge             → 05_review/judge_feedback.json
Pre-Audit         → 05_review/optimizer_preflight.md
Reporter          → report.md, run_summary.json
Report Reviewer   → optimizer.md
HTML Visualizer   → diagnostic-report.html
HTML Reviewer     → 05_review/html_review.json
```

---

## Core Principle

Diagnosis = exclusion, not confirmation. Every conclusion requires four conditions: temporal precedence + statistical significance + physical mechanism + no contradiction.

| Pillar | Principle |
|--------|-----------|
| Scenario-Adaptive | Drive the analysis flow from data characteristics — no hardcoded process types |
| RAG Deep Understanding | Semantic understanding via RAG knowledge, not mechanical mapping |
| Data↔Ontology Bidirectional | Ontology predicts → data confirms; data reveals → ontology explains |
| Physics-Based | Every correlation must be traceable to governing equations |

---

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion criterion | Any unmet condition → mark as an excluded candidate and provide quantitative justification |
| Physics boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

---

## Path Stability

| Rule | Requirement |
|------|-------------|
| Absolute paths | `SKILL_PATH`, `RUN_DIR`, `DATA_PATH` must be absolute |
| Path quoting | All path variables quoted in bash: `"$SKILL_PATH/..."` |
| Python path | Use shared venv via `uv_env_setup.mjs`: `$SHARED_PATH/scripts/.venv/Scripts/python.exe` (Win) or `$SHARED_PATH/scripts/.venv/bin/python` (POSIX) |
| Artifact consistency | Sub-agents use the exact same `RUN_DIR` as the orchestrator |

---

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-analysis-auto>"
SHARED_PATH="<path-to-.claude/shared>"

# Step 0 setup validation
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --mode fast|full --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
node "$SHARED_PATH/scripts/uv_env_setup.mjs"

# Step 1 inspect
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>

# Step 9 finalize
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR" "$SKILL_PATH"
```

## Failure Recovery

| Trigger | Detection | Recovery |
|---------|-----------|----------|
| RAG engine down | `localhost:8764` unresponsive | Continue — ontology-builder uses `parameter_to_physics.json` + web search |
| uv venv creation fails | `uv_env_setup.mjs` non-zero exit | Install uv → retry; still fail → system Python + pip |
| Input data oversized | inspect timeout >300s | `file_inspect.py --sample 50000` |
| Agent timeout/stall | >600s no output | Check partial outputs → continue if usable; retry 1x → mark `[AGENT_TIMEOUT]` |
| API disconnect | System API error | Wait 30s → restart agent; 2x fail → `[API_ERROR]` + degrade to local scripts |
| Artifact missing | File not found after step | ontology missing → `parameter_to_physics.json` minimal ontology; diagnosis missing → `[DIAGNOSIS_FAILED]` |
| Schema validation fail | validate.mjs returns errors | Append error list to prompt → restart 1x; still fail → `[SCHEMA_FAIL]` |
| Plot generation fail | plot_manifest empty/missing | Repair data → redraw; still fail → `image_captions.json` L4 text fallback |
| HTML build fail | diagnostic-report.html missing or review fail | Re-run html-visualizer → 2x fail → deliver report.md only + `HTML_DELIVERY_FAILED` |

---

## Pipeline Event Logging

Every step logs to `RUN_DIR/.pipeline_events.jsonl`:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event <event_type> --agent <agent_name> --step <step_name> \
  [--files <comma,separated,paths>] [--data '<json>']
```

Key events: `run_initialized`, `step_start`, `step_complete`, `agent_start`, `agent_complete`, `repair_spawn`, `repair_cap_reached`, `artifact_finalize_complete`, `artifact_check_complete`.