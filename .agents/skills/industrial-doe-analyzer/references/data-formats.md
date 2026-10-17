# Data formats — DOE analyzer

This is the format contract for everything the analyzer accepts, including data captured by
AgentWorkShop. If a file does not follow this page, the analyzer either rejects it with a named
error or records the deviation in `assigned_by` / `provenance` — it never guesses silently.

## 0. Which entry point do I need?

| What you have | Entry point | Result |
|---|---|---|
| One tidy table, one row per trial run (CSV/TSV/Excel/Parquet/Feather/JSON) | `analyze.py profile` / `all` | Direct analysis; if `analysis_context.json` is absent, roles are auto-inferred |
| A platform-authored `doe_context.json` + `run_table.csv` | `doe_context_adapter.py --run-dir` → `analyze.py all` | Frozen contract §2/§3, every declared field `assigned_by: user` |
| AgentWorkShop DAQ exports (one export per trial run) + trial design + QC | `aws_capture.py build` → `doe_context_adapter.py` → `analyze.py all` | Run table assembled from the captures; node responses aggregated; units/specs from the mapping |
| One DAQ export (time series) for anomaly/stability | `aws_capture.py pivot --export … --out wide.csv` | Wide time-series table for `industrial-sentinel` / `industrial-line-stability-report` |
| Profiles / 2D maps / image streams / notes (non-scalar) | `industrial-hetero-preprocessor` first | `HX-*` scalar feature columns joined onto the run table |

## 1. Single-table formats

- Suffixes: `.csv`, `.tsv`, `.json`, `.xlsx`, `.xls`, `.parquet`, `.feather`.
- Encoding: UTF-8 (BOM tolerated). CSV delimiter `,`; TSV `\t`.
- One table per run. Directories and multi-file merges are **not** read by the analyzer; use
  `industrial-data-preprocessor` or the capture adapter first.
- JSON tables must be a list of records (`[{...}, {...}]`) or a column-oriented object; a nested
  API payload is not a table.
- Column names are case-sensitive and must match `doe_context.factors[].col` /
  `responses[].col` exactly.
- Factor columns: numeric or categorical. Numeric factors are coded by
  `(x − mean) / half_range`; categorical factors by deviation coding.
- Response columns: numeric; empty cells are allowed (unmeasured/failed run) and are disclosed as
  missing, never imputed. A missing **column** is a contract violation.
- Missing values: empty string, `NA`, `NaN`, `null` are accepted; `Inf` is rejected as
  non-finite. A response that is empty for every run forces `data_stage=design_only`.

## 2. Canonical run table (`run_table.csv`)

One row = one execution (`run_id`). A repeated execution of the same factor combination is a
**new `run_id`** with the same `design_point_id`/`replicate_group`.

| Column | Required | Meaning |
|---|:---:|---|
| `run_id` | ✅ | unique execution id; duplicates are rejected (`DUPLICATE_RUN_ID`) |
| `design_point_id` | recommended | groups executions of the same factor combination |
| `replicate_group` | recommended | independent repeats; pure error is keyed on this group |
| `replicate_kind` | optional | `repeat` / `replicate` / `center` |
| `run_order` | recommended | randomized execution order |
| `block` | optional | session/batch block; declared in `doe_context.blocks` |
| `<factor columns>` | ✅ | setpoints actually executed (not the requested recipe) |
| `<response columns>` | ✅ (≥1) | measured outcomes; blanks allowed |

Rules:

- Pure error / lack-of-fit come from `replicate_group` (within block). Covariates never define
  replicates.
- Excluded runs are **removed from the run table** and recorded in
  `00_input/exclusions/run_exclusions.csv` (`run_id,reason,excluded_at,by`). Exclusions are never
  placed in the data directory itself.
- The run table is the analysis input; the design matrix can be reconstructed from it. Do not
  add a second copy of the design under a different name.

## 3. `doe_context.json`

The platform-authored contract. The adapter (`doe_context_adapter.py`) turns it into
`analysis_context.json`; the analyzer only reads the latter. Field-level authority:
`docs/plans/contracts/README.md` §2 and `docs/plans/contracts/doe_context.schema.json`.

Minimum:

```json
{
  "contract_version": "1.0",
  "experiment_id": "doe-bopet-ccd-1",
  "data_file": "run_table.csv",
  "factors": [
    {"name": "tdo_z4_temp", "col": "tdo_z4_temp", "type": "numeric", "unit": "°C",
     "min": 196, "max": 204, "expected_sign": "+",
     "platform_ref": {"recipe_param": "TDO_Z4_TEMP", "node_id": "tdo_z4_temp",
                      "plc_tag": "DB10.DBD0", "unit": "°C", "unit_conversion": 1.0,
                      "rounding": 0.1, "hard_limits": {"min": 195, "max": 205}}}
  ],
  "responses": [
    {"name": "thickness_um", "col": "thickness_um", "unit": "um", "goal": "target",
     "lsl": 48, "usl": 52, "target": 50, "weight": 1.0,
     "platform_metric_ref": {"node_id": "thickness_gauge", "aggregation": "steady_mean"}}
  ]
}
```

Key rules:

- `factors` ≥ 2, `responses` ≥ 1. `col` must exist in the run table.
- `goal` ∈ `target | minimize | maximize`. Missing spec bounds are allowed; a response without
  both a goal and a spec cannot enter the joint desirability.
- `platform_ref` is mandatory for an executable handoff. Without it, the factor still appears in
  the analysis but is removed from `recipe_patch` with `platform_ref_missing`. `unit_conversion`
  is a **scale number** in the frozen contract; an offset must be folded into the recipe
  parameter (the adapter rejects a non-zero offset).
- `hard_limits` are platform safety limits, separate from the design range. `within_limits` is
  computed against these.
- `constraints`:
  - box/safety: `{"factor": "...", "type": "box"|"safety", "min": …, "max": …, "hard": true}`
  - linear: `{"type": "linear", "coefficients": {"a": 1, "b": 10}, "rhs": 235, "hard": true}` —
    the adapter/analyzer reads this as `Σ coeff·x ≤ rhs`. Use `"op": ">="` (or `"min"`) for the
    other direction; `min`/`max` on the weighted sum are also accepted.
  - Unsupported types fail closed; they are never silently ignored.
- `current_setpoint` is the recipe in force **before** the trial. It is the `from` of
  `recipe_patch` and the baseline for `current_baseline`; factor medians are only a fallback for
  factors it does not pin.
- `ontology`: `{"profile": "doe", "mode": "auto|full|reuse|extend", "scene_key": "...",
  "data_stage": "design_only|collected"}`. `mode=off` is refused in production.
- `provenance` is free-form; the adapter records the run-table sha256 and row count under
  `_source`.

### Mapping to `analysis_context.json`

```bash
python .claude/skills/industrial-doe-analyzer/scripts/doe_context_adapter.py --run-dir <RUN_DIR>
```

Writes `00_input/analysis_context.json` with `data_path`, every factor/response, units,
constraints, `current_setpoint`, ontology policy, and `provenance.assigned_by`. A declared data
file that does not exist is `MISSING_RUN_TABLE`, never a silent fallback.

## 4. AgentWorkShop capture

### 4.1 One export = one window

```
<export>/
  manifest.json                 aw.daq-export/1
  nodes/<node>.csv              ts_iso,ts_ms,value,state
  frames/<node>/...             vector long table or image files (E-1H territory)
```

`manifest.json` carries `schema`, `export_id`, `window`, `lines[]` (line/product/recipe/run),
`nodes[]` (`id/name/unit/range/warn/file/rows/value_range_observed/state_summary/semantics`) and
`totals`. The exporter writes `\r\n` and ISO-8601 timestamps with milliseconds; readers accept
both line endings.

### 4.2 A campaign = one export per trial run

```
campaign/
  mapping.json                  ← the only place semantics are declared
  trial_design.csv              run_id, design_point_id, replicate_group, replicate_kind,
                                run_order, block, <factor columns>
  qc_measurements.csv           run_id, <lab response columns>, measured_at
  hetero_features.csv           run_id, HX-* columns (from E-1H; optional)
  runs/<run_id>/                one DAQ export per execution
    manifest.json
    nodes/<node>.csv
```

`mapping.json`:

```json
{
  "experiment_id": "doe-aws-bopet-ccd-20261017",
  "line_id": "bopet-lineA", "product_id": "BOPET-12um", "recipe_id": "RCP-12A",
  "objective": "…",
  "design_type_declared": "rsm_ccd",
  "trial_design_file": "trial_design.csv",
  "qc_file": "qc_measurements.csv",
  "features_file": "hetero_features.csv",
  "runs_dir": "runs",
  "aggregation": {"method": "steady_mean", "warmup_trim": 0.2,
                  "state_filter": ["ok"], "min_rows": 8},
  "factors": [{"name": "...", "col": "...", "unit": "...", "platform_ref": {…}}],
  "responses": [
    {"name": "thickness_um", "col": "thickness_um", "source": "qc", "unit": "um",
     "goal": "target", "lsl": 48, "usl": 52, "target": 50},
    {"name": "gauge_mean", "col": "gauge_mean", "source": "node", "node": "thickness_gauge",
     "aggregate": "steady_mean", "unit": "um", "goal": "target", "lsl": 48, "usl": 52}
  ],
  "covariates": [{"name": "ambient_temp", "col": "ambient_temp",
                  "source": "node", "node": "ambient_temp", "unit": "°C"}],
  "blocks": ["block"],
  "constraints": [
    {"factor": "tdo_z4_temp", "type": "box", "min": 195, "max": 205, "hard": true},
    {"type": "linear", "coefficients": {"tdo_z4_temp": 1, "tdo_ratio": 10},
     "rhs": 235, "hard": true}
  ],
  "current_setpoint": {"tdo_z4_temp": 196, "mdo_speed": 330, "tdo_ratio": 3.1},
  "ontology": {"profile": "doe", "mode": "auto", "scene_key": "bopet-lineA-12um-tdo"}
}
```

Node responses: `source: "node"` + `node` (id or manifest name) + `aggregate`:

| `aggregate` | Meaning |
|---|---|
| `steady_mean` (default) | drop `state_filter` rows, trim the first `warmup_trim` fraction, average the rest |
| `mean` | average all finite rows of the kept states |
| `median` | median of all finite rows of the kept states |
| `end_mean` | average the last 10% of the kept rows |

`state_filter` defaults to `["ok"]`; `min_rows` (default 8 in the mapping, 5 in the adapter)
rejects a run with too few usable rows (`INSUFFICIENT_NODE_ROWS`) instead of averaging noise.

Build:

```bash
python .claude/skills/industrial-doe-analyzer/scripts/aws_capture.py inspect --export <dir>
python .claude/skills/industrial-doe-analyzer/scripts/aws_capture.py build \
  --capture-root <campaign> --mapping <campaign>/mapping.json --out-dir <RUN_DIR> \
  [--exclusions <exclusions.csv>] [--json]
```

Outputs: `00_input/run_table.csv`, `00_input/doe_context.json`,
`00_input/capture_manifest.json` (sha256s, per-node rows used/state-filtered), and
`00_input/exclusions/run_exclusions.csv` when runs were excluded. Then run
`doe_context_adapter.py`.

`pivot` (one export → wide time series, for sentinel/stability):

```bash
python .claude/skills/industrial-doe-analyzer/scripts/aws_capture.py pivot \
  --export <dir> --out wide.csv [--names id|name] [--format iso|ms]
```

The pivot drops non-finite values and aligns nodes on the exact `ts_ms` grid; it does not
interpolate or forward-fill. Vector/image frames are not pivoted — send them through E-1H.

### 4.3 Failure codes (fail closed)

| Code | Cause |
|---|---|
| `MISSING_MANIFEST` / `UNSUPPORTED_MANIFEST` | no manifest, or schema is not `aw.daq-export/1` |
| `NO_NODES` / `MISSING_NODE_FILE` | manifest has no nodes / a declared node file is absent |
| `UNKNOWN_NODE` | mapping references a node id/name not in the run manifest |
| `MISSING_TRIAL_DESIGN` / `MISSING_QC_FILE` / `MISSING_FEATURES_FILE` | declared file absent |
| `MISSING_COLUMN` | a factor column is absent from the trial design |
| `DUPLICATE_RUN_ID` | repeated `run_id` in the trial design |
| `MISSING_RUN_CAPTURE` | a trial run has no export directory |
| `INSUFFICIENT_NODE_ROWS` | fewer usable rows than `min_rows` |
| `BAD_AGGREGATE` / `BAD_WARMUP_TRIM` | unsupported aggregation or trim |
| `UNSUPPORTED_UNIT_CONVERSION_OFFSET` | `platform_ref.unit_conversion` carries a non-zero offset |

## 5. Heterogeneous data (E-1H)

E-1H projects non-scalar data onto the run time axis and writes `07_hetero/**`:

- `column_contract.json` — per-column `unit/role/physical_meaning/formula/physics_basis/
  evidence_level/n_inputs/coverage/stats_eligible`.
- `features/PROF-*.csv` — one row per snapshot: `ts,_src_ts,n_inputs,pos_1…pos_N,HX-PROF-*`.
- `features/TXT-*.csv`, `annotations.json` — operator notes/handover events.
- `explicit_cols.json` — targets/predictors/excludes for the stats layer.

To use profiles in a DOE analysis, join selected `HX-*` columns to the run table by `run_id`:

1. Give E-1H an anchor table with one row per run and the run-end timestamp
   (`hetero/anchor.csv`: `时间,run_id`), plus the profile long table (`时间,位置,值`) and notes
   (`时间,备注`).
2. Read `features/PROF-*.csv`; map `ts` → `run_id` via the anchor.
3. Keep only `stats_eligible` columns that are **scalar** (drop the `pos_*` matrix); write
   `hetero_features.csv` with `run_id` + selected `HX-*` columns and reference it from
   `mapping.features_file`.
4. The analyzer treats those columns as responses/covariates only if declared in the mapping;
   extra columns are screened by the association screen, not modelled as factors.

**Timestamp caveat**: E-1H's catalog does not parse ISO-8601 with milliseconds (`…T08:03:50.000Z`)
directly. The capture adapter's prepared `hetero/*.csv` uses `%Y-%m-%d %H:%M:%S`; keep the raw AWS
`ts_iso` in `nodes/*.csv` and convert on the way into E-1H. This is a known interop gap (see
`platform-integration.md`).

## 6. Data-quality rules the analyzer enforces

- ≥ 5 rows and ≥ 2 columns, at least one usable numeric column (`INSUFFICIENT_DATA` /
  `NO_NUMERIC_COLUMNS`).
- Duplicate `run_id` rejected; duplicate rows are counted and disclosed.
- Non-finite values are dropped from statistics and disclosed; they are never replaced by zero.
- A time column is only treated as time when it parses; `run_order`/`run_id` are structural, not
  time.
- Units: declared units flow into `recommendations.units`; a missing unit yields
  `unit_status=missing` and blocks the actionable handoff for that factor. A factor/response whose
  `platform_ref.unit` differs from the analysis unit is a `conflict`, never a silent conversion.
- Constraints are enforced in the grid, the design hull check, the desirability L-BFGS-B step and
  the joint solution; any hard violation blocks `actionable`.

## 7. Where the outputs are specified

- `docs/plans/contracts/README.md` — the frozen field-level contract (§2 context, §3 adapter,
  §4 artifact manifest, §5 recommendations v1.1).
- `docs/plans/contracts/run_table.md` — the run-table contract with examples.
- `artifacts/artifact_manifest.json` — every output path + sha256 + schema version.
- `references/platform-integration.md` — how IDD and AgentWorkShop exchange these files.
