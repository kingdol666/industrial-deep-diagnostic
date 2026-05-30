---
name: domain-literature-experiment-extraction-ontology-skill
description: "Use when the user wants to systematically collect, extract, and structure experimental data from scientific literature in a specific domain (PVA/BOPET optical films, catalyst synthesis, battery materials, polymer modification, drug formulation, etc.). Triggers on: 文献数据提取, 论文实验数据整理, 文献知识图谱, 领域本体构建, literature mining, experiment extraction from papers, scientific knowledge base construction, paper data collection, ontology from literature, 文献综述数据化. Make sure to use this skill whenever the user mentions extracting experimental parameters from research papers, building a structured database from literature, constructing a domain ontology from publications, or systematic literature data mining — even if they don't explicitly ask for a 'skill' or 'pipeline.' Do NOT trigger for: simple PDF text extraction, one-off paper summarization, general web search, or reading a single paper without data structuring intent."
version: 1.0.0
---

# Domain Literature Experiment Extraction & Ontology Skill

## Language Default

默认输出语言为中文。报告、解释、摘要使用中文。JSON 字段名、Schema 定义、枚举值使用英文。化合物命名遵循 IUPAC 规范，材料命名优先使用工业通用名称并附 CAS 号（如有）。

## Core Principle

Every module is independently callable, producing schema-validated structured output. The full pipeline composes these modules sequentially. Provenance is paramount — every extracted data point carries a traceable link back to its source document, page, and original text snippet. When evidence is weak, confidence drops; when evidence is missing, the field stays empty. Never invent data.

## Loading Guide — What to Read and When

This skill uses progressive loading. Read only what each step needs:

| When | Read | Why |
|------|------|-----|
| Skill triggered | This file (SKILL.md) | Intent routing, module selection, domain config |
| Module 1: Literature Acquisition | `references/module-1-literature-acquisition.md` | Search strategy, dedup rules, source metadata |
| Module 2: Experiment Extraction | `references/module-2-experiment-extraction.md` | Extraction patterns, table parsing, text-to-field mapping |
| Module 3: Data Normalization | `references/module-3-data-normalization.md` | Unit conversion, synonym mapping, canonical naming |
| Module 4: Evidence & Traceability | `references/module-4-evidence-traceability.md` | Provenance schema, confidence scoring rules |
| Module 5: Explanation Generation | `references/module-5-explanation-generation.md` | Scientific interpretation templates, caveat rules |
| Module 6: Ontology Modeling | `references/module-6-ontology-modeling.md` | Class hierarchy, relationship extraction, OWL/JSON-LD export |
| Module 7: Literature Summary | `references/module-7-literature-summary.md` | Trend synthesis, gap analysis, meta-review structure |
| Full pipeline mode | `pipeline-execution.md` | Orchestration sequence, error recovery, event logging |
| Schema validation | `schemas/*.json` matching output type | Validate module outputs |
| Domain vocabulary | `assets/pva_bopet_vocabulary.json` | Canonical names, synonyms, unit mappings for the target domain |
| Custom extraction schema | `templates/extraction_config_template.json` | User-defined field schema for specialized extraction |

**Do NOT load everything upfront.** Each module reference is self-contained — read it only when that module is invoked.

---

## Domain Configuration (PVA/BOPET Optical Films)

This skill is pre-configured for **PVA/BOPET optical film** research. All pre-built vocabulary, synonym maps, and unit conversions in `assets/` target this domain. To adapt to another domain (catalyst synthesis, battery materials, etc.), replace the assets and update the extraction schema.

### Pre-loaded Domain Knowledge

| Category | Coverage |
|----------|----------|
| **Materials** | PVA (1799/1788/1792/0588 grades), PET (optical grade), TAC, COP, PMMA, PC |
| **Additives** | Plasticizers (glycerol, EG, PEG, sorbitol), crosslinkers (boric acid, glutaraldehyde, citric acid), nanofillers (CNC, CNF, MMT, GO, CNT, SiO₂, TiO₂, ZnO) |
| **Process steps** | Solution casting, melt extrusion, uniaxial/biaxial stretching, coating (bar/gravure/slot-die), drying (thermal/IR), heat treatment/annealing |
| **Properties** | Light transmittance (%), haze (%), tensile strength (MPa), elongation at break (%), Young's modulus (GPa), WVTR (g/m²·day), OTR (cc/m²·day·atm), Tg/Tm/Td (°C), crystallinity (%), contact angle (°) |
| **Instruments** | UV-Vis spectrophotometer, haze meter, tensile tester (UTM), DSC, TGA, DMA, SEM, AFM, XRD, FTIR, contact angle goniometer, oxygen/water vapor permeability tester |
| **Units** | See `assets/unit_conversions.json` for automatic conversion rules |

---

## Intent Routing

When a user makes a request, classify it and route to the correct module:

```
User Request
    │
    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Intent Classification                             │
├────────────┬───────────┬──────────┬──────────┬─────────┬────────┬───────┤
│ 搜索/收集   │ 提取实验   │ 标准化   │ 溯源/     │ 解释/   │ 本体/  │ 综述/ │
│ 文献       │ 数据      │ 归一化   │ 置信度    │ 说明    │ 知识图谱│ 总结  │
│            │           │          │          │         │        │       │
│ Module 1   │ Module 2  │ Module 3 │ Module 4 │ Module 5│Module 6│Module7│
└────────────┴───────────┴──────────┴──────────┴─────────┴────────┴───────┘
    │
    │  "帮我把PVA光学膜文献的实验数据全部提取出来" → Full Pipeline
    │  "从这个文件夹的论文里建一个知识图谱" → Modules 1→2→3→4→6
    ▼
┌─────────────────────────────────┐
│         Full Pipeline           │
│  run_pipeline.py --mode full    │
│  (Step 1→2→3→4→5→6→7 顺序执行)  │
└─────────────────────────────────┘
```

### Routing Keywords

| User says (any language) | Route to |
|--------------------------|----------|
| 搜索文献/找论文/检索/literature search/收集相关论文/查找文献 | → Module 1 |
| 提取数据/抽取实验/提取参数/extract experiments/data extraction/从论文中提取/解析实验条件 | → Module 2 |
| 标准化/归一化/统一单位/统一命名/normalize/standardize/canonical names | → Module 3 |
| 溯源/出处/来源/证据/置信度/provenance/traceability/evidence/confidence | → Module 4 |
| 解释/说明/科学解释/为什么/机理分析/interpretation/explanation | → Module 5 |
| 本体/知识图谱/ontology/OWL/RDF/构建知识图谱/关系抽取/实体 | → Module 6 |
| 综述/总结/趋势/研究空白/literature summary/gap analysis/文献综述 | → Module 7 |
| 全部/完整流程/全流程/pipeline/end-to-end/批量处理/一次性 | → Full Pipeline |

---

## Module Execution Protocol

Each module follows the same execution pattern:

```
Step 0: Read the module reference file (references/module-N-*.md)
Step 1: Load any domain assets needed (assets/*.json)
Step 2: Read the input data (from previous module output or user-provided files)
Step 3: Execute extraction/processing logic
Step 4: Run deterministic script if applicable (scripts/*.py)
Step 5: Validate output against schema (schemas/*.json)
Step 6: Report results with statistics (records processed, confidence distribution, errors)
Step 7: Save output to the designated run directory
```

### Script Invocation Pattern

Scripts handle deterministic, repetitive tasks. LLM-guided reasoning handles NLP extraction, explanation, and ontology construction.

```bash
# Direct file input
python scripts/<script>.py --input <path> --output <path> [options]

# Pipeline mode (stdin JSON)
cat <previous_output.json> | python scripts/<script>.py --stdin --output <path>

# Get help
python scripts/<script>.py --help
```

### Output Validation

After each module execution, validate the output against its schema:

```bash
python -c "
import json, jsonschema
with open('<schema_path>') as sf: schema = json.load(sf)
with open('<output_path>') as of: data = json.load(of)
jsonschema.validate(data, schema)
print('Validation PASSED')
"
```

If validation fails, report the specific schema violation and stop the pipeline for that module.

---

## Full Pipeline — Quick Start

When the user wants end-to-end processing:

```bash
python scripts/run_pipeline.py \
  --input-dir <path_to_papers_or_previous_output> \
  --output-dir <path_to_results_folder> \
  --mode full \
  --skill-path <path_to_this_skill> \
  --domain pva_bopet \
  --search-keywords "PVA optical film, BOPET, light transmittance, haze, tensile"
```

The pipeline:
1. **Module 1** — Searches/collects literature; deduplicates; builds source manifest
2. **Module 2** — Extracts experimental data from each paper (tables + narrative text)
3. **Module 3** — Normalizes units, names, abbreviations to canonical forms
4. **Module 4** — Attaches provenance (source, page, snippet, confidence) to every record
5. **Module 5** — Generates scientific explanations for extracted records
6. **Module 6** — Constructs domain ontology (classes, entities, relationships)
7. **Module 7** — Synthesizes literature summary (trends, gaps, patterns)
8. Outputs all results with a `pipeline_manifest.json` summary

See `pipeline-execution.md` for detailed orchestration rules, error recovery, and logging format.

### Pipeline Modes

| Mode | Description | Modules Executed |
|------|-------------|-----------------|
| `full` | Complete end-to-end processing | 1 → 2 → 3 → 4 → 5 → 6 → 7 |
| `extract-only` | Acquire + extract + normalize + evidence | 1 → 2 → 3 → 4 |
| `knowledge-build` | Build ontology + summary from existing extracted data | 6 → 7 |
| `explain` | Generate explanations for already-extracted data | 5 only |
| `resume` | Resume from a specific module (requires previous outputs) | N → ... → 7 |

---

## Supported Input Formats

| Category | Formats | Notes |
|----------|---------|-------|
| Research papers | `.pdf` | Full text extraction via PDF parsing |
| Web articles | HTML (via URL) | Full text from open-access pages |
| Supplementary materials | `.pdf`, `.xlsx`, `.csv`, `.docx` | Tables and figures |
| Patents | `.pdf`, HTML | Experimental examples section |
| Pre-extracted data | `.json`, `.csv` | Already-structured experiment records |
| Search results | JSON (Semantic Scholar / PubMed API response) | Module 1 can consume API output directly |

---

## Required Outputs

Every full pipeline run produces:

| # | Output | Format | Schema |
|---|--------|--------|--------|
| 1 | Unified experiment table | `experiments.csv` / `experiments.json` / `experiments.xlsx` | `schemas/experiment_record.schema.json` |
| 2 | Provenance table | `provenance.json` | `schemas/provenance_record.schema.json` |
| 3 | Confidence report | Embedded in experiment records (`confidence` field per row) | `schemas/experiment_record.schema.json` |
| 4 | Data explanation report | `explanations.md` / `explanations.json` | `schemas/explanation.schema.json` |
| 5 | Ontology model | `ontology.json` (also exportable to OWL/Turtle/JSON-LD) | `schemas/ontology.schema.json` |
| 6 | Ambiguity & missing fields log | `ambiguities.json` | `schemas/ambiguity.schema.json` |
| 7 | Literature summary | `literature_summary.md` / `literature_summary.json` | `schemas/literature_summary.schema.json` |

---

## Output Standards

- All JSON keys are `snake_case` in English
- All dates are ISO 8601 (`YYYY-MM-DD`)
- All numeric values include `value`, `unit`, and `unit_normalized` fields
- All outputs include a `metadata` block with provenance (skill version, timestamp, input sources, domain)
- CSV exports use UTF-8 BOM encoding for Excel compatibility
- Missing values are explicitly `null` — never empty strings, never 0, never "N/A" as a substitute
- Confidence scores range from 0.0 (no evidence) to 1.0 (directly quoted from paper)

---

## Error Handling

1. **Paper cannot be parsed** — Log the paper as `unparseable` with reason; continue to next paper
2. **Field extraction ambiguous** — Record both possible values in `alternatives` array; set `confidence` to 0.5
3. **Unit cannot be converted** — Keep original value + unit; flag in `normalization_errors`
4. **Ontology conflict** — Two papers claim contradictory relationships → flag as `ontology_conflict` with both sources
5. **Search returns zero results** — Report to user; suggest broader keywords or different sources
6. **Disk full** — Stop pipeline immediately; report space needed
7. **Schema validation failure** — Report exact JSON path + constraint violated; skip that record, continue pipeline

**Golden rule**: A partially complete output with quality annotations is always preferable to a complete output with fabricated data.

---

## Output Directory Structure

```
<output_dir>/
├── pipeline_manifest.json
├── .pipeline_events.jsonl
├── 01_literature/
│   ├── source_manifest.json          # All papers found, with metadata
│   ├── dedup_report.json             # Duplicates removed
│   └── downloaded/                   # Local copies of papers (optional)
├── 02_extracted/
│   ├── experiments_raw.json          # Raw extraction before normalization
│   └── extraction_log.json           # Per-paper extraction statistics
├── 03_normalized/
│   ├── experiments_normalized.json   # After unit/name normalization
│   ├── experiments.csv               # CSV export
│   ├── experiments.xlsx              # Excel export
│   └── normalization_log.json        # What was transformed
├── 04_provenance/
│   ├── provenance.json               # Full provenance table
│   └── confidence_distribution.json  # Confidence score histogram
├── 05_explanations/
│   ├── explanations.md               # Human-readable report
│   └── explanations.json             # Structured explanations
├── 06_ontology/
│   ├── ontology.json                 # Main ontology
│   ├── ontology.ttl                  # Turtle export (if requested)
│   └── ontology.owl                  # OWL export (if requested)
├── 07_summary/
│   ├── literature_summary.md         # Narrative summary
│   └── literature_summary.json       # Structured summary
├── ambiguities.json                  # All unresolved issues
└── run_summary.json                  # Final statistics
```

---

## Quick Reference — Script Arguments

| Script | Key Arguments |
|--------|--------------|
| `literature_search.py` | `--keywords`, `--sources`, `--year-from`, `--year-to`, `--max-results`, `--output` |
| `extract_experiments.py` | `--input`, `--output`, `--config` (extraction schema), `--mode` (table/text/both) |
| `normalize_data.py` | `--input`, `--output`, `--vocabulary`, `--unit-map`, `--synonym-map` |
| `build_ontology.py` | `--experiments`, `--output`, `--format` (json/owl/ttl/jsonld), `--domain` |
| `generate_explanations.py` | `--experiments`, `--output`, `--language` (zh/en) |
| `summarize_literature.py` | `--experiments`, `--provenance`, `--output`, `--focus-areas` |
| `validate_outputs.py` | `--data`, `--schema`, `--report-errors` |
| `run_pipeline.py` | `--input-dir`, `--output-dir`, `--mode`, `--skill-path`, `--domain`, `--search-keywords` |