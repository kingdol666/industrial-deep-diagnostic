---
name: industrial-data-preprocessor
description: >
  自适应数据前处理（E-1 阶段）。把用户给的任何数据源——单个文件或整个目录、
  任意格式混合（CSV/TSV/分隔符文本、Excel xlsx/xlsm/xls 多工作表、JSON 记录、
  Markdown 表格、HTML 表格、自由文本说明）——归一化为管线可直接消费的标准表
  preprocessed_data.csv + 完整审计报告 + 上下文文件保留。
  Trigger: 数据前处理, 预处理, 数据格式, 多格式数据, 目录数据, xlsm, 多sheet,
  data preprocessing, preprocess, adaptive data, any data format.
  保证与数据源无关：管线流程对任何数据形态生效。
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

## Verification

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
```

Covers: clean CSV, GBK+semicolon+junk-header text, multi-sheet xlsx with junk,
xlsm, JSON records, Markdown tables vs context text, mixed directories
(csv+xlsx+md+script merge/context/skip), batch data without time, multi-block
delimited files, and empty-tabular directories.
