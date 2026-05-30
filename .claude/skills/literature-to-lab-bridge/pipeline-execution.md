# Bridge Pipeline Execution Reference

> **Load this file during full bridge pipeline execution or error recovery.**
> SKILL.md contains the bridge architecture and phase overview. This file covers: detailed orchestration, data handoff protocol, quality gate logic, error recovery, event logging, and schema transformation rules.

## Pipeline Modes

| Mode | Description | Phases Executed |
|------|-------------|:---:|
| `full` | Complete literature-to-lab bridge | Phase 1 → Gate → Transform → Phase 2 → Finalize |
| `literature-only` | Run only Phase 1 (literature search + extraction) | Phase 1 only |
| `lab-only` | Run only Phase 2 from existing transformed data | Phase 2 only (requires `phase2_input/`) |
| `resume` | Resume from a specific phase | Gate → Transform → Phase 2, or Phase 2 only |
| `quality-gate` | Check Phase 1 data sufficiency without running Phase 2 | Gate only |
| `finalize` | Generate bridge manifest from existing phase outputs | Finalize only |
| `status` | Report current bridge state from manifest | Read-only, no execution |

## Step-by-Step Orchestration

### Step 0: Bridge Initialization

```
┌─────────────────────────────────────────────────┐
│              Bridge Initialization               │
├─────────────────────────────────────────────────┤
│ 1. Determine SKILL_HOME paths:                  │
│    BRIDGE_SKILL = .claude/skills/               │
│                   literature-to-lab-bridge       │
│    LITERATURE_SKILL = .claude/skills/            │
│                       domain-literature-         │
│                       experiment-extraction-     │
│                       ontology-skill             │
│    CHEM_LAB_SKILL = .claude/skills/              │
│                     chem-auto-lab-skill          │
│                                                  │
│ 2. Create RUN_DIR:                               │
│    workspace/bridge-runs/YYYYMMDDHHMMSS_<slug>/  │
│                                                  │
│ 3. Collect user parameters:                      │
│    - domain (required)                           │
│    - search_keywords (required for Phase 1)      │
│    - paper_files (optional, local PDF dir)       │
│    - min_records (default: 10)                   │
│    - min_confidence (default: 0.5)               │
│    - min_papers (default: 3)                     │
│                                                  │
│ 4. Write bridge_manifest.json:                   │
└─────────────────────────────────────────────────┘
```

Write initial `bridge_manifest.json`:

```json
{
  "bridge_id": "bridge_20260530_001",
  "domain": "pva_bopet",
  "search_keywords": "PVA optical film, light transmittance, haze",
  "paper_files_provided": false,
  "mode": "full",
  "status": "initialized",
  "phases": {
    "phase1": { "status": "pending", "skill": "domain-literature-experiment-extraction-ontology-skill" },
    "quality_gate": { "status": "pending" },
    "transform": { "status": "pending" },
    "phase2": { "status": "pending", "skill": "chem-auto-lab-skill" },
    "finalize": { "status": "pending" }
  },
  "run_dir": "/path/to/workspace/bridge-runs/bridge_20260530_001/",
  "created_at": "2026-05-30T10:00:00Z"
}
```

### Step 1: Phase 1 — Literature Search & Extraction

#### 1.1 Determine Input Source

**Case A — User provides search keywords (no local files):**
```
→ Run Module 1 (online literature search) of literature skill
→ Use WebSearch / Semantic Scholar API / PubMed
→ Keywords from user input or bridge parameters
```

**Case B — User provides local paper directory:**
```
→ Skip Module 1 online search
→ Classify files in paper directory (.pdf, .html, .xlsx, .csv)
→ Build source_manifest.json from local files directly
→ Run Modules 2→3→4→7
```

**Case C — User provides pre-extracted data (JSON/CSV):**
```
→ Skip Modules 1→2 entirely
→ Load pre-extracted data
→ Run Modules 3→4→7 for normalization and evidence attachment
```

#### 1.2 Execute Literature Pipeline

```bash
python "$LITERATURE_SKILL/scripts/run_pipeline.py" \
  --input-dir "${PAPER_DIR:-$RUN_DIR/phase1_input/}" \
  --output-dir "$RUN_DIR/phase1_output/" \
  --mode full \
  --skill-path "$LITERATURE_SKILL" \
  --domain "$DOMAIN" \
  --search-keywords "$KEYWORDS"
```

#### 1.3 Collect Phase 1 Statistics

After Phase 1 completes, extract statistics from `phase1_output/run_summary.json`:

```json
{
  "papers_processed": 15,
  "experiments_extracted": 342,
  "experiments_after_dedup": 338,
  "mean_confidence": 0.82,
  "low_confidence_records": 23,
  "records_with_spectral_data": 45
}
```

Update bridge manifest:
```json
{
  "phases": {
    "phase1": {
      "status": "completed",
      "papers_processed": 15,
      "experiments_extracted": 338,
      "mean_confidence": 0.82,
      "spectral_data_present": true,
      "spectral_records": 45,
      "errors": [],
      "warnings": ["2 papers had no extractable experiment data"]
    }
  }
}
```

### Step 2: Quality Gate

#### 2.1 Run Gate Checks

```python
def run_quality_gate(phase1_stats, config):
    checks = []
    passed = True
    warnings = []

    # Check 1: Minimum records
    records = phase1_stats['experiments_extracted']
    min_records = config.get('min_records', 10)
    checks.append({
        'check': 'min_records',
        'value': records,
        'threshold': min_records,
        'passed': records >= min_records,
        'message': f'Records extracted: {records} (threshold: {min_records})'
    })
    if records < min_records:
        passed = False
        warnings.append(f'Insufficient records extracted ({records} < {min_records})')

    # Check 2: Mean confidence
    mean_conf = phase1_stats['mean_confidence']
    min_conf = config.get('min_confidence', 0.5)
    checks.append({
        'check': 'mean_confidence',
        'value': round(mean_conf, 3),
        'threshold': min_conf,
        'passed': mean_conf >= min_conf,
        'message': f'Mean confidence: {mean_conf:.3f} (threshold: {min_conf})'
    })
    if mean_conf < min_conf:
        passed = False
        warnings.append(f'Low mean confidence ({mean_conf:.3f} < {min_conf})')

    # Check 3: Minimum unique papers
    papers = phase1_stats['papers_processed']
    min_papers = config.get('min_papers', 3)
    checks.append({
        'check': 'min_papers',
        'value': papers,
        'threshold': min_papers,
        'passed': papers >= min_papers,
        'message': f'Unique papers: {papers} (threshold: {min_papers})'
    })
    if papers < min_papers:
        passed = False
        warnings.append(f'Insufficient paper sources ({papers} < {min_papers})')

    # Check 4: Spectral data availability (informational only)
    spectral = phase1_stats.get('spectral_data_present', False)
    checks.append({
        'check': 'spectral_data',
        'value': spectral,
        'passed': True,  # Always passes; just informational
        'message': f'Spectral data present: {spectral}'
    })

    return {
        'passed': passed,
        'checks': checks,
        'warnings': warnings
    }
```

#### 2.2 Gate Pass → Auto-Continue

If gate passes, update manifest and proceed to Step 3 automatically:

```json
{
  "phases": {
    "quality_gate": {
      "status": "passed",
      "checks": [...],
      "auto_proceed": true
    }
  }
}
```

#### 2.3 Gate Fail → User Decision Required

If gate fails, present the gate report to user:

```
╔══════════════════════════════════════════════════════════════╗
║                    QUALITY GATE FAILED                       ║
╠══════════════════════════════════════════════════════════════╣
║  ✗ Records extracted: 7 (threshold: 10)                     ║
║  ✓ Mean confidence: 0.72 (threshold: 0.5)                   ║
║  ✓ Unique papers: 5 (threshold: 3)                          ║
╠══════════════════════════════════════════════════════════════╣
║  Options:                                                    ║
║  1. Broaden search keywords and re-run Phase 1               ║
║  2. Provide additional paper files                           ║
║  3. Lower min_records threshold and continue                 ║
║  4. Continue anyway with available data                      ║
║  5. Abort bridge pipeline                                    ║
╚══════════════════════════════════════════════════════════════╝
```

Update manifest with `quality_gate.status: "failed"` and wait for user input.

### Step 3: Data Transformation

#### 3.1 Determine Spectral Status

Before running the transformer, determine if Phase 2 Module 2 (Spectroscopy) should be enabled:

```python
def detect_spectral_data(experiments):
    spectral_indicators = [
        'wavenumber', 'wavelength', 'chemical_shift', 'mz',
        'retention_time', 'absorbance', 'transmittance_percent',
        'intensity', 'raman_shift'
    ]
    spectral_properties = ['FTIR', 'Raman', 'NMR', 'UV-Vis', 'HPLC', 'GC-MS', 'XRD']

    has_spectral_fields = any(
        any(ind in str(k).lower() for ind in spectral_indicators)
        for record in experiments
        for k in record.keys()
    )
    has_spectral_properties = any(
        str(record.get('measured_property', '')).upper() in spectral_properties
        for record in experiments
    )

    return has_spectral_fields or has_spectral_properties
```

#### 3.2 Run Transformer

```bash
INCLUDE_SPECTRAL_FLAG=""
if [ "$SPECTRAL_DETECTED" = "true" ]; then
  INCLUDE_SPECTRAL_FLAG="--include-spectral"
fi

python "$BRIDGE_SKILL/scripts/transform_literature_to_lab.py" \
  --input "$RUN_DIR/phase1_output/03_normalized/experiments_normalized.json" \
  --output "$RUN_DIR/phase2_input/lab_experiments.json" \
  --domain "$DOMAIN" \
  $INCLUDE_SPECTRAL_FLAG \
  --confidence-threshold 0.3
```

#### 3.3 Transformer Output Structure

The transformer produces `lab_experiments.json` in chem-auto-lab-skill compatible format:

```json
{
  "metadata": {
    "script": "transform_literature_to_lab.py",
    "version": "1.0.0",
    "source": "literature_extraction",
    "bridge_id": "bridge_20260530_001",
    "processing_timestamp": "2026-05-30T10:05:00Z",
    "rows_input": 338,
    "rows_output": 315,
    "rows_filtered": 23,
    "filter_reason": "confidence < 0.3",
    "spectral_data_present": true
  },
  "experiments": [
    {
      "experiment_id": "SRC_001_E001",
      "timestamp": null,
      "variables": {
        "material_system": "PVA/CNC composite",
        "film_thickness": {"value": 50, "unit": "μm"},
        "drying_temperature": {"value": 60, "unit": "°C"},
        "light_transmittance": {"value": 92.3, "unit": "%"},
        "tensile_strength": {"value": 85.4, "unit": "MPa"}
      },
      "spectral_peaks": [
        {"wavenumber": 3340, "intensity": 0.85, "assignment": "O-H stretch"},
        {"wavenumber": 2940, "intensity": 0.62, "assignment": "C-H stretch"}
      ],
      "observations": {
        "source_text": "The PVA/CNC composite film exhibited a light transmittance of 92.3% at 550 nm...",
        "paper_ref": "Zhang et al. (2023), Enhanced Optical and Mechanical Properties of PVA/CNC Composite Films, doi:10.1234/example",
        "source_confidence": 0.9,
        "extraction_method": "table_parse"
      },
      "batch_id": "SRC_001",
      "source_file": "experiments_normalized.json",
      "source_sheet": null,
      "source_row": 0,
      "low_confidence": false
    }
  ]
}
```

#### 3.4 Transformer Statistics

After transformation, log:

```json
{
  "transform": {
    "status": "completed",
    "records_input": 338,
    "records_output": 315,
    "records_filtered": 23,
    "filter_reason": "confidence < 0.3",
    "spectral_detected": true,
    "spectral_records": 45,
    "fields_mapped": {
      "material_system": 338,
      "film_thickness": 201,
      "drying_temperature": 156,
      "measured_property_1": 338,
      "measured_property_2": 187,
      "additive": 124
    },
    "unmapped_fields": ["crosslinker_concentration_unit", "solvent"],
    "warnings": []
  }
}
```

### Step 4: Phase 2 — Lab Analysis

#### 4.1 Determine Module Execution Plan

Based on transformer output:

```python
def plan_phase2_modules(transform_stats, phase1_stats):
    modules = [1]  # Module 1 (Data Cleaning) always runs

    if transform_stats.get('spectral_detected'):
        modules.append(2)  # Module 2: Spectroscopy

    if phase1_stats.get('has_observations'):
        modules.append(3)  # Module 3: Log Structuring

    modules.append(4)  # Module 4: Report Generation always runs
    modules.append(5)  # Module 5: Recommendations always runs

    return modules
```

#### 4.2 Execute Chem Lab Pipeline

```bash
python "$CHEM_LAB_SKILL/scripts/run_pipeline.py" \
  --input-dir "$RUN_DIR/phase2_input/" \
  --output-dir "$RUN_DIR/phase2_output/" \
  --mode full \
  --skill-path "$CHEM_LAB_SKILL"
```

#### 4.3 Enhanced Recommendations

When Module 5 runs in bridge mode, pass literature context:

```bash
python "$CHEM_LAB_SKILL/scripts/recommend.py" \
  --experiments "$RUN_DIR/phase2_output/01_cleaned/merged_experiments.json" \
  --output "$RUN_DIR/phase2_output/recommendations.json" \
  --n-recommendations 5 \
  --literature-gaps "$RUN_DIR/phase1_output/07_summary/literature_summary.json" \
  --confidence-data "$RUN_DIR/phase1_output/04_provenance/confidence_distribution.json"
```

This enriches recommendations with:
- Literature gaps identified in Phase 1
- Low-confidence findings worth validating
- Parameter ranges not yet covered in the literature

### Step 5: Finalize

#### 5.1 Generate Bridge Summary

```bash
python "$BRIDGE_SKILL/scripts/bridge_pipeline.py" \
  --mode finalize \
  --phase1-output "$RUN_DIR/phase1_output/" \
  --phase2-output "$RUN_DIR/phase2_output/" \
  --run-dir "$RUN_DIR"
```

#### 5.2 Final bridge_manifest.json

```json
{
  "bridge_id": "bridge_20260530_001",
  "domain": "pva_bopet",
  "mode": "full",
  "status": "completed",
  "phases": {
    "phase1": {
      "status": "completed",
      "skill": "domain-literature-experiment-extraction-ontology-skill",
      "papers_processed": 15,
      "experiments_extracted": 338,
      "mean_confidence": 0.82,
      "duration_ms": 210000
    },
    "quality_gate": {
      "status": "passed",
      "checks": [
        {"check": "min_records", "value": 338, "threshold": 10, "passed": true},
        {"check": "mean_confidence", "value": 0.82, "threshold": 0.5, "passed": true},
        {"check": "min_papers", "value": 15, "threshold": 3, "passed": true},
        {"check": "spectral_data", "value": true, "passed": true}
      ]
    },
    "transform": {
      "status": "completed",
      "records_transformed": 315,
      "records_filtered": 23,
      "spectral_detected": true,
      "duration_ms": 15000
    },
    "phase2": {
      "status": "completed",
      "skill": "chem-auto-lab-skill",
      "modules_executed": [1, 2, 4, 5],
      "modules_skipped": [3],
      "report_generated": "report.md",
      "recommendations_count": 5,
      "figures_count": 8,
      "duration_ms": 85000
    }
  },
  "summary": {
    "total_duration_ms": 310000,
    "total_papers": 15,
    "total_experiments_analyzed": 315,
    "key_findings": "See phase2_output/report.md",
    "recommendations": "See phase2_output/recommendations.json"
  },
  "output_artifacts": [
    "phase1_output/03_normalized/experiments_normalized.json",
    "phase1_output/03_normalized/experiments.csv",
    "phase1_output/07_summary/literature_summary.json",
    "phase2_input/lab_experiments.json",
    "phase2_output/report.md",
    "phase2_output/recommendations.json",
    "phase2_output/figures/"
  ],
  "errors": [],
  "warnings": [
    "2 papers in Phase 1 had no extractable data",
    "23 records filtered due to low confidence (<0.3)",
    "Module 3 (Log Structuring) skipped: no free-text observations"
  ],
  "created_at": "2026-05-30T10:00:00Z",
  "completed_at": "2026-05-30T10:05:10Z"
}
```

---

## Data Handoff Protocol

### Handoff Chain

```
Phase 1 (Literature Skill)
    │
    ├── 03_normalized/experiments_normalized.json
    │       │
    │       ▼
    │   [Quality Gate — Sufficiency Check]
    │       │
    │       ▼ PASS
    │   [Data Transformer]
    │       │
    │       ├── phase2_input/lab_experiments.json
    │       │       │
    │       │       ▼
    │       │   Phase 2 (Chem Lab Skill)
    │       │       │
    │       │       ├── 01_cleaned/merged_experiments.json
    │       │       ├── figures/
    │       │       ├── report.md
    │       │       └── recommendations.json
    │       │
    │       └── [Finalize] → bridge_manifest.json
    │
    └── 07_summary/literature_summary.json
            │
            └──→ [Enhanced Recommendations]
```

### Schema Transformation Rules

Detailed mapping from literature schema to lab schema:

```
literature experiment_record              lab experiment_record
─────────────────────────────────         ──────────────────────
experiment_id                    ──►      experiment_id (identity)
source_id                        ──►      batch_id
paper_title + year + source_doi  ──►      observations.paper_ref
source_snippet                   ──►      observations.source_text
confidence                       ──►      observations.source_confidence
extraction_method                ──►      observations.extraction_method

material_system                  ──►      variables.material (string)
material_grade                   ──►      variables.material_grade (string)

film_thickness + unit            ──►      variables.film_thickness {"value":N,"unit":U}
drying_temperature + unit        ──►      variables.drying_temperature {"value":N,"unit":U}
drying_time + unit               ──►      variables.drying_time {"value":N,"unit":U}
heat_treatment_temperature+unit  ──►      variables.heat_treatment_temp {"value":N,"unit":U}
heat_treatment_time + unit       ──►      variables.heat_treatment_time {"value":N,"unit":U}
stretching_ratio                 ──►      variables.stretching_ratio (number)
stretching_temperature + unit    ──►      variables.stretching_temp {"value":N,"unit":U}
solution_concentration + unit    ──►      variables.solution_concentration {"value":N,"unit":U}

additive                         ──►      variables.additive_name (string)
additive_concentration + unit    ──►      variables.additive_conc {"value":N,"unit":U}
plasticizer                      ──►      variables.plasticizer_name (string)
plasticizer_concentration + unit ──►      variables.plasticizer_conc {"value":N,"unit":U}
crosslinker                      ──►      variables.crosslinker_name (string)
crosslinker_concentration + unit ──►      variables.crosslinker_conc {"value":N,"unit":U}

film_preparation_method          ──►      variables.preparation_method (string)
instrument                       ──►      variables.instrument (string)

measured_property +              ──►      variables.{property_slug} {"value":N,"unit":U}
  measured_value + measured_unit           e.g., "light_transmittance" → variables.light_transmittance
measured_property_2..5 + values  ──►      Same pattern, slugified

Spectral detection:
  wavelength/wavenumber/...      ──►      spectral_peaks: [{wavenumber, intensity, assignment}]
  measured_property IN [FTIR,Raman,NMR,UV-Vis,HPLC,GC-MS,XRD] → flag as spectral record
```

### Slug Generation for Property Names

```python
import re

def slugify(property_name):
    if not property_name:
        return "unknown_property"
    slug = property_name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = re.sub(r'_+', '_', slug)
    slug = slug.strip('_')
    # Abbreviate common long names
    abbreviations = {
        'light_transmittance': 'transmittance',
        'elongation_at_break': 'elongation',
        'tensile_strength': 'tensile_strength',
        'young_s_modulus': 'youngs_modulus',
        'water_vapor_transmission_rate': 'wvtr',
        'oxygen_transmission_rate': 'otr',
        'contact_angle': 'contact_angle',
    }
    return abbreviations.get(slug, slug)
```

---

## Bridge Event Log

Each phase writes to `<RUN_DIR>/.bridge_events.jsonl`:

```jsonl
{"event": "bridge_start", "bridge_id": "bridge_20260530_001", "mode": "full", "domain": "pva_bopet", "timestamp": "2026-05-30T10:00:00Z"}
{"event": "phase_start", "phase": 1, "skill": "domain-literature-experiment-extraction-ontology-skill", "timestamp": "2026-05-30T10:00:01Z"}
{"event": "phase_complete", "phase": 1, "papers_processed": 15, "experiments_extracted": 338, "duration_ms": 210000, "timestamp": "2026-05-30T10:03:31Z"}
{"event": "gate_start", "timestamp": "2026-05-30T10:03:31Z"}
{"event": "gate_complete", "passed": true, "checks": [...], "timestamp": "2026-05-30T10:03:31Z"}
{"event": "transform_start", "timestamp": "2026-05-30T10:03:31Z"}
{"event": "transform_complete", "records_input": 338, "records_output": 315, "spectral_detected": true, "duration_ms": 15000, "timestamp": "2026-05-30T10:03:46Z"}
{"event": "phase_start", "phase": 2, "skill": "chem-auto-lab-skill", "modules": [1, 2, 4, 5], "timestamp": "2026-05-30T10:03:46Z"}
{"event": "phase_complete", "phase": 2, "modules_executed": [1, 2, 4, 5], "duration_ms": 85000, "timestamp": "2026-05-30T10:05:11Z"}
{"event": "bridge_complete", "status": "completed", "total_duration_ms": 311000, "timestamp": "2026-05-30T10:05:11Z"}
```

---

## Error Recovery Rules

### Phase 1 Errors

| Error | Recovery |
|-------|----------|
| No search results | Suggest broader keywords, different search sources. Do not proceed. |
| All papers unparseable | Check paper format (scanned PDFs need OCR). Suggest providing text-based PDFs. |
| Zero experiments extracted | Check extraction schema compatibility. Try with `--mode extract-only` to debug. |
| Partial extraction | Continue if gate passes. Mark `phase1_warnings` in manifest. |
| Network failure during search | Retry 3 times with exponential backoff (1s, 2s, 4s). If all fail, suggest providing local paper files. |

### Transformer Errors

| Error | Recovery |
|-------|----------|
| Input file not found | Report exact path. Check Phase 1 completed successfully. |
| Schema mismatch | Report specific field mismatch. Suggest manual review of extracted data. |
| All records filtered | Lower `--confidence-threshold` or skip filtering with `--confidence-threshold 0`. |
| Spectral detection ambiguous | Default to `--include-spectral` (conservative: better to have unused data than missing analysis). |

### Phase 2 Errors

| Error | Recovery |
|-------|----------|
| Module 1 (Cleaning) fails | Check data format. Try running chem-auto-lab-skill independently to debug. |
| Module 2 (Spectroscopy) fails | Skip spectroscopy, continue with remaining modules. Mark warning. |
| Module 4 (Report) fails | Generate figures only (`visualize.py`). Provide raw data for manual review. |
| Module 5 (Recommendations) fails | Skip. Literature summary is still available for manual review. |

### General Bridge Rules

1. **Phase 1 outputs are always preserved.** Phase 2 failure does not delete Phase 1 data.
2. **Partial success is acceptable.** A bridge run with Phase 1 complete and Phase 2 partial is still valuable.
3. **All errors are logged** in `.bridge_events.jsonl` with stack traces and context.
4. **Resume is supported.** Use `--mode resume` to re-run from the failed phase.

---

## Output Directory Structure

```
workspace/bridge-runs/<bridge_id>/
├── bridge_manifest.json                 # Overall bridge status + statistics
├── .bridge_events.jsonl                 # Bridge execution event log
├── integrated_report.md                 # (optional) Combined Phase 1 + Phase 2 summary
├── phase1_input/                        # (optional) User-provided papers
├── phase1_output/                       # Literature skill outputs
│   ├── pipeline_manifest.json
│   ├── .pipeline_events.jsonl
│   ├── run_summary.json
│   ├── 01_literature/
│   │   └── source_manifest.json
│   ├── 02_extracted/
│   │   └── experiments_raw.json
│   ├── 03_normalized/
│   │   ├── experiments_normalized.json
│   │   └── experiments.csv
│   ├── 04_provenance/
│   │   └── provenance.json
│   └── 07_summary/
│       └── literature_summary.json
├── phase2_input/                        # Transformed data for lab analysis
│   └── lab_experiments.json
└── phase2_output/                       # Lab analysis outputs
    ├── pipeline_manifest.json
    ├── .pipeline_events.jsonl
    ├── 01_cleaned/
    │   └── merged_experiments.json
    ├── 02_spectra/                      # (if spectral data present)
    ├── figures/
    │   ├── 01_timeseries.png
    │   ├── 02_correlation_heatmap.png
    │   ├── 03_distribution.png
    │   └── plot_manifest.json
    ├── report.md
    └── recommendations.json
```