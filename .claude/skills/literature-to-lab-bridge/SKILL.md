---
name: literature-to-lab-bridge
description: "Use when the user wants to search scientific literature for experimental data AND automatically analyze it through a chemistry laboratory pipeline. This skill bridges domain-literature-experiment-extraction-ontology-skill (literature search + experiment extraction) with chem-auto-lab-skill (data cleaning + spectroscopy + report + recommendations). Triggers on: 从文献中搜索实验数据并自动分析, 文献数据自动化处理, 论文实验数据提取并分析, literature-to-lab, 搜索论文并分析实验, 文献挖掘+化学分析, automated literature-driven lab analysis, search papers and run chemical analysis. Make sure to use this skill whenever the user mentions both literature search/data extraction AND chemical/laboratory analysis in the same request. Do NOT trigger for: literature search only (use domain-literature skill), lab data analysis only (use chem-auto-lab skill), or non-chemistry domains."
version: 1.0.0
---

# Literature-to-Lab Bridge Skill

## Language Default

默认输出语言为中文。报告、解释、摘要使用中文。JSON 字段名、Schema 定义、枚举值使用英文。

## Core Principle

This skill orchestrates a two-phase pipeline: **Phase 1** searches literature and extracts experiment data using `domain-literature-experiment-extraction-ontology-skill`; **Phase 2** feeds that extracted data into `chem-auto-lab-skill` for automated chemical analysis, report generation, and experiment recommendations. The two phases are connected by a **data transformer** that maps literature-extracted records into the lab analysis input format.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Literature-to-Lab Bridge Pipeline                     │
│                                                                          │
│  ┌───────────────────────────────────────┐                               │
│  │           PHASE 1: Literature          │                               │
│  │  domain-literature-experiment-         │                               │
│  │  extraction-ontology-skill             │                               │
│  │                                         │                               │
│  │  Module 1 → Literature Search          │                               │
│  │  Module 2 → Experiment Extraction      │                               │
│  │  Module 3 → Data Normalization         │                               │
│  │  Module 4 → Evidence & Traceability    │                               │
│  │  Module 7 → Literature Summary         │                               │
│  └──────────────────┬────────────────────┘                               │
│                     │ experiments_normalized.json                        │
│                     ▼                                                    │
│  ┌───────────────────────────────────────┐                               │
│  │         DATA TRANSFORMER              │                               │
│  │  transform_literature_to_lab.py       │                               │
│  │                                         │                               │
│  │  文献 schema → 化学实验 schema 映射     │                               │
│  │  - material_system → variables        │                               │
│  │  - measured_value → variables         │                               │
│  │  - unit → unit annotation            │                               │
│  └──────────────────┬────────────────────┘                               │
│                     │ lab_experiments.json                                │
│                     ▼                                                    │
│  ┌───────────────────────────────────────┐                               │
│  │           PHASE 2: Lab Analysis        │                               │
│  │  chem-auto-lab-skill                   │                               │
│  │                                         │                               │
│  │  Module 1 → Data Cleaning             │                               │
│  │  Module 2 → Spectroscopy (if data)    │                               │
│  │  Module 4 → Report Generation         │                               │
│  │  Module 5 → Experiment Recommendation │                               │
│  └───────────────────────────────────────┘                               │
│                     │                                                    │
│                     ▼                                                    │
│  ┌───────────────────────────────────────┐                               │
│  │         INTEGRATED OUTPUTS            │                               │
│  │  - lab_report.md                     │                               │
│  │  - recommendations.json              │                               │
│  │  - figures/                           │                               │
│  │  - bridge_manifest.json              │                               │
│  └───────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## When to Use This Skill

| Scenario | Use This Skill? |
|----------|:---:|
| "搜索PVA光学膜文献，提取实验数据，然后做化学分析" | ✅ |
| "从论文里收集催化剂合成数据，清洗后生成报告并推荐下一步实验" | ✅ |
| "帮我查找最近5年电池材料的文献，把数据提取出来分析趋势" | ✅ |
| "只搜索文献、提取数据" | ❌ → Use `domain-literature-experiment-extraction-ontology-skill` |
| "只分析我已有的化学实验数据" | ❌ → Use `chem-auto-lab-skill` |

## Loading Guide

| When | Read | Why |
|------|------|-----|
| Skill triggered | This file (SKILL.md) | Bridge architecture, phase orchestration |
| Phase 1 details | `domain-literature-experiment-extraction-ontology-skill/SKILL.md` | Literature search + extraction protocol |
| Phase 2 details | `chem-auto-lab-skill/SKILL.md` | Lab analysis pipeline protocol |
| Full bridge execution | `pipeline-execution.md` | Detailed orchestration, error recovery, handoff |
| Data transformation rules | `scripts/transform_literature_to_lab.py --help` | Schema mapping reference |

## Execution Flow

```
Step 0: Bridge Setup
    │
    ▼
Step 1: PHASE 1 — Literature Search & Extraction
    │  (domain-literature-experiment-extraction-ontology-skill)
    │  Modules 1→2→3→4→7
    │
    ▼
Step 2: QUALITY GATE — Data Sufficiency Check
    │  ├── records_extracted >= min_records (default: 10)
    │  ├── mean_confidence >= min_confidence (default: 0.5)
    │  ├── unique_papers >= min_papers (default: 3)
    │  └── FAIL → report to user, offer options
    │
    ▼
Step 3: DATA TRANSFORMER — Schema Mapping
    │  transform_literature_to_lab.py
    │  文献 experiment_record → 化学 lab experiment_record
    │
    ▼
Step 4: PHASE 2 — Lab Analysis & Recommendations
    │  (chem-auto-lab-skill)
    │  Modules 1→4→5 (+ Module 2 if spectral data present)
    │
    ▼
Step 5: INTEGRATED REPORT — Merge & Present
       bridge_manifest.json + combined summary
```

## Phase 1: Literature Search & Extraction

Invoke `domain-literature-experiment-extraction-ontology-skill` with the user's domain and search keywords.

### Execution

```bash
# Bridge generates manifest from user parameters:
# { "pipeline_id": "...", "mode": "full", "domain": "$DOMAIN",
#   "search_terms": [...keywords...], "classified_inputs": {...} }

python "$LITERATURE_SKILL/scripts/run_pipeline.py" \
  --manifest "$RUN_DIR/phase1_input/pipeline_manifest.json" \
  --output-dir "$RUN_DIR/phase1_output/"
```

### Expected Outputs

| File | Location | Purpose |
|------|----------|---------|
| `experiments_normalized.json` | `phase1_output/03_normalized/` | Primary data for Phase 2 |
| `experiments.csv` | `phase1_output/03_normalized/` | Alternative input format |
| `source_manifest.json` | `phase1_output/01_literature/` | Paper metadata |
| `literature_summary.json` | `phase1_output/07_summary/` | Gap analysis for recommendations |
| `run_summary.json` | `phase1_output/` | Statistics for quality gate |

### Module Selection by Data Type

The bridge can selectively run literature modules based on data type:

```markdown
| Data contains | Literature Modules | Lab Modules |
|---------------|:---:|:---:|
| Spectral peaks (FTIR/NMR/Raman/UV-Vis) | 1→2→3→4 | 1→2→4→5 |
| Process conditions only (T, P, time, concentration) | 1→2→3→4 | 1→4→5 |
| Both spectral + process | 1→2→3→4→7 | 1→2→4→5 |
| Only material properties (transmittance, strength) | 1→2→3→4→7 | 1→4→5 |
```

## Quality Gate

After Phase 1 completes, run the quality gate check:

```bash
python "$BRIDGE_SKILL/scripts/bridge_pipeline.py" \
  --mode quality-gate \
  --phase1-output "$RUN_DIR/phase1_output/" \
  --min-records 10 \
  --min-confidence 0.5 \
  --min-papers 3
```

### Gate Criteria

| Criterion | Threshold | Action on Failure |
|-----------|-----------|-------------------|
| `records_extracted` | ≥ `min_records` (default 10) | Report: "文献提取数据不足 (N records)。建议：扩大搜索范围、增加关键词、或提供更多论文。" Ask user: broaden search, provide more papers, or continue with available data |
| `mean_confidence` | ≥ `min_confidence` (default 0.5) | Report low-confidence records. Ask user: accept lower confidence, manually review, or skip |
| `unique_papers` | ≥ `min_papers` (default 3) | Report: "有效论文数量不足 (N papers)。建议：扩展搜索源或放宽筛选条件。" |

If gate passes, proceed to Phase 2 automatically. If gate fails, present results to user and ask for direction.

## Data Transformer

Map literature-extracted records to chem-auto-lab input format:

```bash
python "$BRIDGE_SKILL/scripts/transform_literature_to_lab.py" \
  --input "$RUN_DIR/phase1_output/03_normalized/experiments_normalized.json" \
  --output "$RUN_DIR/phase2_input/lab_experiments.json" \
  --domain "$DOMAIN" \
  --include-spectral \
  --confidence-threshold 0.3
```

### Schema Mapping

| Literature Field | Lab Field | Transformation |
|-----------------|-----------|----------------|
| `experiment_id` | `experiment_id` | Pass through |
| `source_id` | `batch_id` | Map as source batch |
| `material_system` | `variables.material` | String |
| `film_thickness` + `film_thickness_unit` | `variables.film_thickness` | `{"value": N, "unit": U}` |
| `drying_temperature` + `drying_temperature_unit` | `variables.drying_temperature` | `{"value": N, "unit": U}` |
| `measured_property` + `measured_value` + `measured_unit` | `variables.{property}` | Dynamic key from measured_property → `{"value": N, "unit": U}` |
| `measured_property_2..5` + values | `variables.{property_2..5}` | Same as above |
| `additive` + `additive_concentration` | `variables.additive` | `{"name": X, "concentration": {"value": N, "unit": U}}` |
| `confidence` | `source_confidence` | Annotated, not used for filtering |
| `source_snippet` | `observations.source_text` | Preserve traceability |
| `paper_title` + `year` + `source_doi` | `observations.paper_ref` | Compound reference |

Records with `confidence < confidence-threshold` are included but flagged with `low_confidence: true` for Phase 2 to handle appropriately.

### Spectral Data Detection

The transformer auto-detects if Phase 1 data contains spectral information:

- Fields named `wavenumber`, `wavelength`, `chemical_shift`, `mz`, `retention_time` → spectral data present
- `measured_property` values: `FTIR`, `Raman`, `NMR`, `UV-Vis`, `HPLC`, `GC-MS` → spectral data present
- If detected, Phase 2 Module 2 (Spectroscopy) is enabled

## Phase 2: Lab Analysis

Feed transformed data into `chem-auto-lab-skill`:

```bash
python "$CHEM_LAB_SKILL/scripts/run_pipeline.py" \
  --input-dir "$RUN_DIR/phase2_input/" \
  --output-dir "$RUN_DIR/phase2_output/" \
  --mode clean-and-report
```

### Module Execution Rules

| Module | Condition | Script |
|--------|-----------|--------|
| 1: Data Cleaning | Always run | `clean_data.py` with `--imputation median --outlier iqr` |
| 2: Spectroscopy | Only if spectral data detected in transformer | `parse_spectrum.py` |
| 3: Log Structuring | Only if literature notes/observations present | `structure_notes.py` |
| 4: Report Generation | Always run | `generate_report.py` + `visualize.py` |
| 5: Recommendations | Always run (enhanced with literature gap data) | `recommend.py` with `--literature-gaps` |

### Enhanced Recommendations

Phase 2 Module 5 is enhanced by Phase 1 literature summary data. The recommender uses:

1. **Literature gaps** from `literature_summary.json` → suggest unexplored experimental conditions
2. **Confidence distribution** from Phase 1 → prioritize validating low-confidence findings
3. **Trend analysis** from report → suggest parameter ranges that extend beyond literature coverage

## Integrated Output

After both phases complete, generate the bridge manifest:

```bash
python "$BRIDGE_SKILL/scripts/bridge_pipeline.py" \
  --mode finalize \
  --phase1-output "$RUN_DIR/phase1_output/" \
  --phase2-output "$RUN_DIR/phase2_output/" \
  --run-dir "$RUN_DIR"
```

### Final Output Structure

```
<run_dir>/
├── bridge_manifest.json              # Overall bridge status
├── .bridge_events.jsonl              # Bridge execution log
├── phase1_output/                    # Literature skill outputs
│   ├── 01_literature/
│   ├── 02_extracted/
│   ├── 03_normalized/
│   │   ├── experiments_normalized.json
│   │   └── experiments.csv
│   ├── 04_provenance/
│   ├── 07_summary/
│   │   └── literature_summary.json
│   └── run_summary.json
├── phase2_input/                     # Transformed data
│   └── lab_experiments.json
├── phase2_output/                    # Lab analysis outputs
│   ├── 01_cleaned/
│   │   └── merged_experiments.json
│   ├── 02_spectra/                   # (if spectral data)
│   ├── figures/
│   ├── report.md
│   └── recommendations.json
└── integrated_report.md              # Combined summary (optional)
```

## Quick Reference — Script Arguments

| Script | Key Arguments |
|--------|--------------|
| `bridge_pipeline.py` | `--mode` (full/quality-gate/finalize/status), `--phase1-output`, `--phase2-output`, `--run-dir`, `--min-records`, `--min-confidence`, `--min-papers` |
| `transform_literature_to_lab.py` | `--input`, `--output`, `--domain`, `--include-spectral`, `--confidence-threshold` |

## Error Handling

1. **Phase 1 fails completely** → Report literature search/extraction errors. Do not proceed to Phase 2. Suggest: check search keywords, provide local paper files, or check network access.
2. **Phase 1 partial success** → Run quality gate. If gate passes, proceed with available data. Mark `phase1_warnings` in bridge manifest.
3. **Transformer fails** → Report schema mapping errors. Check that Phase 1 output matches expected schema. Suggest manual review of extracted data.
4. **Phase 2 fails** → Phase 1 outputs are preserved. User can re-run Phase 2 independently or use `chem-auto-lab-skill` directly.
5. **Quality gate fails** → Present gate report to user. Offer options: broaden search, lower thresholds, provide more papers, or continue anyway.

## Roadmap / Future Enhancements

1. **Incremental mode** — Add new papers to existing extraction without re-running entire Phase 1
2. **Iterative feedback loop** — Phase 2 recommendations feed back into Phase 1 search keywords
3. **Multi-domain support** — Pre-built vocabulary for battery materials, catalysts, drug formulations
4. **Confidence-weighted analysis** — Phase 2 report generation weights results by Phase 1 confidence scores
5. **Auto-search refinement** — Phase 2 gap analysis automatically generates new Phase 1 search queries