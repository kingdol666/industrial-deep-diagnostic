# Pipeline Execution Reference

> **Load this file only during full pipeline execution or error recovery.**
> SKILL.md contains the intent routing and module invocation basics. This file covers: orchestration, error recovery, file classification, and logging.

## Pipeline Modes

| Mode | Description | Modules Executed |
|------|-------------|-----------------|
| `full` | Complete end-to-end processing | 1 → 2 → 3 → 4 → 5 (sequential) |
| `clean-and-report` | Clean data then generate report | 1 → 4 |
| `analyze` | Clean + spectrum + report | 1 → 2 → 4 |
| `recommend-only` | Generate recommendations from existing data | 5 only |

## Step-by-Step Orchestration

### Step 0: Input Scan & Classification

```
Scan --input-dir for all files with extensions:
  .xlsx, .xls, .csv, .tsv → classify as "spreadsheet"
  .txt, .md, .log          → classify as "lab_notes"
  .jdx, .spc                → classify as "spectrum"
  xy.csv, xy.txt (paired)  → classify as "spectrum" if column names match spectral patterns
```

Save classification to `pipeline_manifest.json`:

```json
{
  "pipeline_id": "run_20260524_001",
  "mode": "full",
  "classified_files": {
    "spreadsheets": ["data.xlsx", "results.csv"],
    "lab_notes": ["notebook.txt"],
    "spectra": ["ftir_sample.csv"],
    "unrecognized": []
  },
  "status": "initialized"
}
```

**If no recognizable files found**, report to user and stop.

### Step 1: Data Cleaning (Module 1)

For each `spreadsheet` file:
```bash
python scripts/clean_data.py --input <file> --output <output_dir>/01_cleaned/<basename>.json
```

- Merge all cleaned outputs into `01_cleaned/merged_experiments.json`
- Validate against `schemas/experiment_record.schema.json`
- Update manifest with status

**Error recovery**: If one file fails, skip it and continue. Record the failure in manifest.

### Step 2: Spectroscopy Parsing (Module 2)

For each `spectrum` file:
```bash
python scripts/parse_spectrum.py --input <file> --output <output_dir>/02_spectra/<basename>.json
```

- Auto-detect spectrum type (FTIR/Raman/UV-Vis/NMR/HPLC)
- If detection fails, try common fallback patterns
- Validate against `schemas/spectroscopy_output.schema.json`

**If no spectral files**, skip this step and mark manifest.

### Step 3: Lab Notes Structuring (Module 3)

For each `lab_notes` file:
```bash
python scripts/structure_notes.py --input <file> --output <output_dir>/03_structured/<basename>.json
```

- Merge all structured notes into `03_structured/merged_notes.json`
- Validate against `schemas/experiment_record.schema.json`

**If no lab notes files**, skip this step and mark manifest.

### Step 4: Report Generation (Module 4)

```bash
python scripts/generate_report.py \
  --data <output_dir>/01_cleaned/merged_experiments.json \
  --spectra <output_dir>/02_spectra/ \
  --notes <output_dir>/03_structured/merged_notes.json \
  --output <output_dir>/report.md \
  --figures-dir <output_dir>/figures/
```

First generate figures:
```bash
python scripts/visualize.py --data <merged_experiments.json> --output-dir <output_dir>/figures/
```

Then generate report using the figures. Validate report against `schemas/report.schema.json`.

### Step 5: Experiment Recommendation (Module 5)

```bash
python scripts/recommend.py \
  --experiments <output_dir>/01_cleaned/merged_experiments.json \
  --output <output_dir>/recommendations.json \
  --n-recommendations 3
```

Validate against `schemas/recommendation.schema.json`.

### Step 6: Finalize

Update `pipeline_manifest.json` with `status: "completed"` and summary:

```json
{
  "summary": {
    "files_processed": 4,
    "modules_executed": [1, 2, 3, 4, 5],
    "modules_skipped": [],
    "errors": [],
    "output_artifacts": ["report.md", "recommendations.json", "figures/"]
  }
}
```

## Error Recovery Rules

1. **Single module failure** → Continue remaining modules. The pipeline is designed to be partially resilient.

2. **Data file not found** → Report exact path, ask user. Do not guess.

3. **Script crash** → Capture full stderr. Report to user with: script name, error message, suggested fix.

4. **Schema validation failure** → Report the specific JSON path and constraint. Example: `$.temperature: expected number, got string "120°C"`

5. **Disk full** → Stop pipeline immediately. Report available space needed.

6. **All modules fail** → Report the pipeline as failed. Suggest running individual modules manually for debugging.

## Pipeline Event Log

Each step writes a JSON line to `<output_dir>/.pipeline_events.jsonl`:

```jsonl
{"event": "pipeline_start", "mode": "full", "timestamp": "2026-05-24T10:00:00Z"}
{"event": "step_start", "module": 1, "file": "data.xlsx", "timestamp": "2026-05-24T10:00:01Z"}
{"event": "step_complete", "module": 1, "file": "data.xlsx", "rows": 1500, "errors": 0, "timestamp": "2026-05-24T10:00:05Z"}
{"event": "step_error", "module": 2, "file": "bad_spectrum.txt", "error": "Format not recognized", "timestamp": "2026-05-24T10:00:06Z"}
{"event": "pipeline_complete", "status": "partial_success", "errors": 1, "timestamp": "2026-05-24T10:00:15Z"}
```

## Merging Rules

When merging multiple cleaned/structured files:

1. All records must share the same JSON structure (schema-validated)
2. If two records have the same `experiment_id`, the later file wins (file modification time)
3. Merged output is a JSON array: `[{record1}, {record2}, ...]`
4. A `_merge_metadata` key is added: `{"source_files": ["data.xlsx", "results.csv"], "merge_timestamp": "..."}`

## Output Directory Structure

```
<output_dir>/
├── pipeline_manifest.json
├── .pipeline_events.jsonl
├── 01_cleaned/
│   ├── <basename1>.json
│   ├── <basename2>.json
│   └── merged_experiments.json
├── 02_spectra/
│   └── <basename>.json
├── 03_structured/
│   └── merged_notes.json
├── figures/
│   ├── 01_timeseries.png
│   ├── 02_correlation_heatmap.png
│   └── plot_manifest.json
├── report.md
├── report.pdf           (if --format pdf)
└── recommendations.json
```