---
name: industrial-data-preprocessor
description: >
  Adaptive data preprocessing (stage E-1). Normalizes any user-supplied data source —
  a single file or an entire directory, any mix of formats (CSV/TSV/delimited text,
  Excel xlsx/xlsm/xls multi-sheet, JSON records, Markdown tables, HTML tables,
  free-text descriptions) — into the canonical table preprocessed_data.csv that the
  pipeline can consume directly, plus a full audit report and preserved context files.
  Trigger: data preprocessing, preprocess, data formats, multi-format data,
  directory data, xlsm, multi-sheet, adaptive data, any data format.
  Guarantees data-source independence: the pipeline flow works for any data shape.
  Do NOT use for statistics, cleaning, correlation/CCF or charts (use industrial-data-processor);
  do NOT use for profile/2D-field/image-sequence/time-anchored-text heterogeneous features
  (use industrial-hetero-preprocessor); do NOT use for designed-experiment / ANOVA /
  operating-window analysis (use industrial-doe-analyzer); do NOT use for root-cause
  diagnosis (use industrial-diagnostician) or full pipeline orchestration (use industrial-analysis-auto).
---

# Industrial Data Preprocessor

## Why This Stage Exists

The diagnostic pipeline downstream (inspect → ontology → process → diagnose →
judge → report) consumes **one canonical tabular file**. Raw user data never
looks like that: it arrives as a directory full of mixed formats, Excel
workbooks with junk sheets, GBK-encoded Chinese CSVs, JSON dumps, Markdown
tables, or free-text process notes. This stage absorbs ALL of that variance
deterministically and emits the canonical input, so the rest of the pipeline
is genuinely **data-source agnostic**.

## Inputs (read-only)

- `--data-path`: a single file **or** a directory (any mix of the formats
  below). The input is NEVER modified.
- `--stability-single-primary --recursive`: folder-only profile for line-stability reporting. Recursively discovers supported sources, selects one ≥50-row time-series primary by deterministic score (premerged-name preference first), preserves context/metadata, excludes sparse events and explicitly named low-frequency quality sources, and never resamples or merges multiple cadences. Every discovered source receives a disposition/reason; ground-truth/answer files are excluded without reading or copying their contents.

## Outputs (written under `--output`, typically `RUN_DIR/00_input/`)

| File | Content |
|------|---------|
| `preprocessed_data.csv` | canonical table — the pipeline input (utf-8-sig) |
| `preprocessed_data.json` | same data as JSON records (fallback reader) |
| `preprocessing_report.json` | full audit: per-source disposition, format detection, table selection/merge, quality flags |
| `context/` | non-tabular files preserved verbatim (process descriptions, ground truth, notes) for the ontology/context builder |

## Format Adaptation Matrix

| Input | Adaptation |
|-------|-----------|
| `.csv/.tsv/.txt/.dat` | delimiter voted over the first lines (tab/semicolon/comma/pipe); encoding fallback utf-8 → gb18030 → latin-1; junk title lines skipped; multi-block files yield separate candidates (largest wins) |
| `.xlsx/.xlsm/.xls` | every sheet scored (rows × cols + numeric density − junk penalties); 1×1 stubs and query sheets dropped; sheet whose name matches the file stem wins; remaining large sheets merge on a common time column |
| `.json` | array of records, `{data: [...]}`, or single object → DataFrame |
| `.md/.markdown` | pipe tables extracted; text without tables → context file |
| `.html/.htm` | regex-based table extraction (no lxml dependency) |
| everything else | skipped with reason in the report (scripts, binaries, images, db files) |

## Selection & Merge Rules

1. Excel sheet whose name matches the workbook stem (e.g. `MD_tempture.xlsx`
   → sheet `MD_tempture`) is the primary table when ≥100 rows.
2. Otherwise the highest-scoring table wins.
3. When several ≥100-row tables share a same-named time column, they are
   outer-merged on that column (duplicate non-key columns are dropped from the
   right side).
4. Non-tabular files are copied into `context/` and listed in the report — the
   ontology builder uses them as process background.
5. The stability-specific `--stability-single-primary --recursive` mode does
   not merge different sampling cadences. It selects one ≥50-row time-series
   primary and records all auxiliary/event/context/skipped files with reasons.
   Truth/answer references are filename-audited only and their contents are
   neither parsed nor copied. Ontology JSONs (`ontology*.json`, `*本体*`) are
   classified as metadata context so downstream skills can auto-wire them.
6. PV/SV columns inside the primary table are NOT pre-filtered here: PV
   (actual) channels are scored normally; near-constant SV (setpoint)
   channels are dropped downstream by the stability analyzer's
   time-invariant-channel guard and disclosed as a data_quality finding.

## Normalization

- Column names trimmed, de-duplicated (`_2` suffix), fully-empty columns dropped.
- Time column detected by name hints + datetime parseability (numeric columns
  excluded from the fallback — they are never misread as epoch datetimes).
- Time values normalized to ISO `YYYY-MM-DD HH:MM:SS` where parseable; the
  original value is preserved otherwise.
- Missing cells stay NaN — downstream cleaning handles them.

## Usage

```bash
# Directory of mixed formats (recommended: point at the whole data dir)
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py \
  --data-path data/lekaiData --output <RUN_DIR>/00_input --name my_run

# Single file of any supported format
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py \
  --data-path data/eval_reactor_catalyst/data.csv --output <RUN_DIR>/00_input
```

Exit 0 with `status: ok` (table produced) or `status: no_tabular_data`
(report explains; the caller decides). Exit 1 only on hard errors.

## Integration Points

- **Mode A (new data)**: `entry_a_init.mjs` runs this stage between setup and
  inspect; `input_manifest.json.data_path` then points at
  `00_input/preprocessed_data.csv`, with `raw_data_path` and the
  `preprocessing` block recording provenance.
- **Baseline Step 0.5**: the main agent may run this stage directly before
  Step 1 Inspect whenever the user supplies a directory or non-CSV input.
- Idempotent: if the input already IS `preprocessed_data.csv`, it passes
  through unchanged.

## Quality gate

```bash
node .claude/skills/industrial-data-preprocessor/scripts/quality_gate.mjs \
  --run-dir <RUN_DIR> [--raw-path <data-file-or-dir>]
# exit 0 ok | 1 hard error (bad inputs / unreadable audit) | 2 undetermined | 3 gate-fail
```

Post-hoc, zero-LLM verification of an E-1 run dir (D1–D7): canonical table
non-empty; report↔disk rows/cols/numeric-column agreement; declared time
column present (time-less cross-sectional data is a supported scenario —
disclosed as a note, never a fail); `selected_table.file` resolves against
`--raw-path` when given; merge/dedup actions internally consistent (E-1 never
dedups — disclosed duplicate counts must be arithmetically sound; the
stability mode's `single_primary_no_merge` policy and
`single_primary_policy` exclusions are documented, accepted actions); every
reported output path resolves inside `00_input` (moved/exported run dirs whose
report keeps the canonical `.../00_input/<name>` suffix stay valid).

**Passthrough semantics decide exit 2 vs 3** (the marker is
`00_input/preprocessing_report.json`):

| Disk state | Verdict |
|---|---|
| `preprocessed_data.csv` AND `preprocessing_report.json` both absent — E-1 did not run (single-file passthrough: the raw file is consumed directly) | exit 2 |
| report `status: no_tabular_data` (or `no_time_series` in stability mode), no canonical csv — documented non-production outcome, the caller decides | exit 2 |
| report claims `status: ok` but the declared `preprocessed_data.csv` is missing, empty, truncated, or inconsistent | exit 3 |

Gate tests (fixtures generated on the fly):

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/run_tests.py
```

## Verification

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
```

Covers: clean CSV, GBK+semicolon+junk-header text, multi-sheet xlsx with junk,
xlsm, JSON records, Markdown tables vs context text, mixed directories
(csv+xlsx+md+script merge/context/skip), batch data without time, multi-block
delimited files, and empty-tabular directories.