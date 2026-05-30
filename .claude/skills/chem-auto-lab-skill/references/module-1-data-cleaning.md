# Module 1: Experiment Data Cleaner

You clean and standardize chemistry experiment data from heterogeneous sources.

## Core Principle

Never silently drop data. Every transformation (imputation, outlier removal, unit conversion) is **explicitly logged** in the output metadata. The user must be able to trace every change.

## Input Formats

| Format | Detection | Notes |
|--------|-----------|-------|
| `.xlsx` / `.xls` | Extension | Multi-sheet supported; first sheet by default unless `--sheet` specified |
| `.csv` | Extension | Auto-detect delimiter (`,` `;` `\t` `|`) and encoding (UTF-8, GBK, Latin-1) |
| `.tsv` | Extension | Tab-separated |
| `.txt` | Extension | Treated as delimiter-separated; auto-detect delimiter |
| JSON stdin | `--stdin` flag | Already structured data; skip format detection |

## Cleaning Operations

### 1. Missing Value Detection & Handling

**Detection**: Recognize all common chemistry lab NA patterns:
- `N/A`, `NA`, `n/a`, `-`, `--`, `null`, `NULL`, `NaN`, `#VALUE!`, `#N/A`, empty cell, `<LOD`, `<LOQ`, `TBD`

**Handling strategies** (controlled by `--imputation`):
- `mean` — Replace with column mean (numeric only)
- `median` — Replace with column median (robust to outliers)
- `ffill` — Forward fill (time-series assumption)
- `bfill` — Backward fill
- `drop` — Remove rows with any missing values
- `constant:<value>` — Replace with a fixed value (e.g., `constant:0`)
- `interpolate` — Linear interpolation (time-series)

**Default**: `median` for numeric, `ffill` for time-series columns.

### 2. Unit Detection & Normalization

**Auto-detect units** embedded in column headers or cell values:
- Pressure: `MPa`, `bar`, `psi`, `kPa`, `atm`, `mmHg`, `Torr`
- Temperature: `°C`, `℃`, `F`, `°F`, `K`
- Concentration: `wt%`, `vol%`, `mol/L`, `M`, `mM`, `μM`, `ppm`, `ppb`, `mg/mL`, `μg/mL`, `g/L`
- Mass: `kg`, `g`, `mg`, `μg`, `lb`, `oz`
- Volume: `L`, `mL`, `μL`, `gal`
- Time: `h`, `hr`, `min`, `s`, `sec`, `day`
- Length: `m`, `cm`, `mm`, `μm`, `nm`, `Å`

**Normalization** (controlled by `--target-units`):
- `SI` — Convert all to SI base units (Pa, K, kg, m³, s, m)
- `metric` — Keep metric but standardize (MPa, °C, g, mL, min, mm)
- `custom:<path>` — User-provided unit mapping JSON
- `none` — Keep original units, just detect and annotate

**How normalization works**: For each numeric column, detect unit from header/cell annotations. Look up conversion factor in `assets/unit_conversions.json`. Apply conversion. Annotate output with `{"original_unit": "bar", "target_unit": "MPa", "conversion_factor": 0.1}`.

### 3. Timestamp Alignment

**Detection**: Auto-detect time columns by name pattern (`time`, `date`, `timestamp`, `datetime`, `时间`, `日期`) or by column type (datetime).

**Alignment** (controlled by `--time-align`):
- `auto` — Detect the most common sampling rate and resample to regular grid
- `minutely` / `hourly` / `daily` — Force specific frequency
- `none` — Keep original timestamps

**Multi-source alignment**: When processing multiple files, align all to a common time grid. Use nearest-neighbor or linear interpolation for resampling.

### 4. Outlier Detection

**Methods** (controlled by `--outlier`):
- `iqr` — Values beyond Q1 - 1.5×IQR or Q3 + 1.5×IQR. Adjust multiplier with `--outlier-threshold` (default 1.5).
- `zscore` — Values with |z-score| > threshold. Default threshold: 3.0.
- `mad` — Median Absolute Deviation. Robust to non-normal distributions. Default threshold: 3.5.
- `none` — Skip outlier detection.

**Handling** (controlled by `--outlier-handling`):
- `flag` — Keep the value but mark `outlier: true` in output
- `cap` — Cap values at threshold boundaries (Winsorization)
- `remove` — Replace with NaN, then apply imputation strategy

**Default**: `iqr` with `flag` handling. Never silently remove data.

### 5. Batch Normalization

When a `batch_id` or `group` column is detected, apply normalization within each batch:

- `zscore` — Standardize to mean=0, std=1 within each batch
- `minmax` — Scale to [0, 1] within each batch
- `none` — No batch normalization

**Important**: Normalization is applied **per batch**, not globally. This preserves batch-to-batch variation while removing within-batch scale differences.

### 6. Column Type Inference

Auto-infer column types:
1. Try `pd.to_numeric` → if success, numeric
2. Try `pd.to_datetime` → if success, datetime
3. If unique values < 20% of total rows → categorical
4. Otherwise → text

Report the inferred types in output metadata. If inference seems wrong, suggest corrections to user.

## Script Usage

```bash
# Basic usage
python scripts/clean_data.py --input experiment_data.xlsx --output cleaned.json

# With options
python scripts/clean_data.py \
  --input data.csv \
  --output cleaned.json \
  --imputation median \
  --outlier iqr --outlier-threshold 2.0 \
  --outlier-handling cap \
  --normalize minmax \
  --target-units metric \
  --time-align hourly

# Stdin mode (pipeline)
cat raw.json | python scripts/clean_data.py --stdin --output cleaned.json
```

## Output Format

Output is a JSON object matching `schemas/experiment_record.schema.json`:

```json
{
  "metadata": {
    "script": "clean_data.py",
    "version": "1.0.0",
    "input_file": "experiment_data.xlsx",
    "processing_timestamp": "2026-05-24T10:00:00Z",
    "rows_input": 1500,
    "rows_output": 1480,
    "rows_removed": 20,
    "transformations": [
      {"column": "temperature_C", "operation": "unit_normalize", "original_unit": "F", "target_unit": "C"},
      {"column": "pressure_MPa", "operation": "outlier_flag", "method": "iqr", "outliers_found": 5},
      {"column": "concentration_wt%", "operation": "impute", "method": "median", "imputed_count": 3}
    ]
  },
  "experiments": [
    {
      "experiment_id": "EXP-001",
      "timestamp": "2026-05-24T09:00:00Z",
      "variables": {
        "temperature_C": {"value": 120.0, "unit": "C", "outlier": false},
        "pressure_MPa": {"value": 0.5, "unit": "MPa", "outlier": false},
        "concentration_wt%": {"value": 5.0, "unit": "wt%", "outlier": false}
      },
      "observations": {},
      "batch_id": null,
      "source_file": "experiment_data.xlsx",
      "source_sheet": "Sheet1",
      "source_row": 1
    }
  ]
}
```

## Edge Cases

1. **Mixed units in same column** — Detect per-cell patterns. If inconsistent, warn user and flag the column.
2. **Chemical formulas in data** — `H2SO4`, `NaCl` etc. should not be treated as missing. Detect by mixed alphanumeric pattern.
3. **Below detection limit** — Values like `<0.01` are valid observations. Extract numeric part, flag as `below_detection_limit: true`.
4. **Very wide datasets** — >50 columns. Process in chunks, report column-level stats.
5. **Non-ASCII column names** — Chinese, Japanese, Greek letters in headers. Preserve as-is, use for type inference.