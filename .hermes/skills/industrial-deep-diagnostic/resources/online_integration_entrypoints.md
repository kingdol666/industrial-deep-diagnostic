# Online Integration Entrypoints

This skill **can** be extended for online / system-integrated diagnosis where data is pulled on demand from a database or service API instead of being manually dropped into `00_input/`.

## Recommended Entrypoints

### 1. Step 0 / Setup Layer — run registration

Best place to attach:
- `scripts/setup.mjs`
- an upstream system wrapper / scheduler / API endpoint

What to add:
- external job ID
- user / system request metadata
- source-system identifier
- requested time range / product / equipment / lot filters

Why here:
- every online diagnosis still needs a stable `RUN_DIR`
- request metadata should be frozen before any data pull

### 2. Step 1 / Inspect Intake Layer — data acquisition adapter

Best place to attach:
- **new script** such as `scripts/fetch-input-data.mjs`
- or an upstream orchestration service before `inspect.mjs`

What this adapter should do:
- query the target database / historian / MES / quality DB
- export a deterministic snapshot (CSV / JSON / Parquet) into `RUN_DIR/00_input/`
- write a source manifest like:
  - queried tables / views
  - SQL / API request fingerprint
  - time range
  - product / lot filters
  - row counts

Why here:
- keeps the rest of the skill unchanged
- all downstream steps still operate on a frozen, auditable snapshot

### 3. Step 3 / Data Processor Layer — online enrichment

Best place to attach:
- a second adapter such as `scripts/fetch-context-join-data.mjs`
- or custom `06_scripts/*.py` for scenario-specific joins

What to pull here:
- maintenance events
- shift schedule
- recipe changes
- quality inspection events
- product genealogy / lot traceability

Why here:
- this data is often only needed after the process structure is understood
- keeps heavy joins out of the minimal intake path

### 4. Step 8 / Delivery Layer — system callback

Best place to attach:
- after `artifact-check.mjs`
- upstream service / workflow engine

What to push back:
- `run_summary.json`
- `diagnosis.json`
- `judge_feedback.json`
- `optimizer.md`
- `evidence_closure_report.json`

Why here:
- only final validated outputs should be written back to external systems

## Recommended Minimal Architecture

For production integration, the cleanest pattern is:

1. External scheduler / API receives request
2. Calls `setup.mjs`
3. Calls **data-fetch adapter** to materialize snapshot into `00_input/`
4. Calls the normal skill pipeline unchanged
5. Calls `artifact-check.mjs`
6. Pushes validated outputs back to the system

## Important Rule

For online integration, **do not let downstream steps query the database directly in an ad hoc way** unless the access is explicitly logged and snapshotted. The diagnosis must remain reproducible. The safest approach is always:

`online query -> frozen input snapshot -> normal skill pipeline`
