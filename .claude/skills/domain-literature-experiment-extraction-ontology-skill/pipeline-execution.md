# Pipeline Execution Reference

> **Load this file only during full pipeline execution or error recovery.**
> SKILL.md contains the intent routing and module invocation basics. This file covers: orchestration, error recovery, file classification, data handoff, and event logging.

## Pipeline Modes

| Mode | Description | Modules Executed | Requires |
|------|-------------|-----------------|----------|
| `full` | Complete end-to-end processing | 1 → 2 → 3 → 4 → 5 → 6 → 7 | User provides domain + search keywords (or paper files) |
| `extract-only` | Acquire + extract + normalize + attach evidence | 1 → 2 → 3 → 4 | Same as `full` |
| `knowledge-build` | Build ontology + summary from existing extracted data | 6 → 7 | Previous run's `03_normalized/experiments_normalized.json` |
| `explain` | Generate explanations for already-extracted data | 5 only | Previous run's `03_normalized/experiments_normalized.json` |
| `resume` | Resume from a specific module N | N → ... → 7 | All outputs from modules 1 through N-1 must exist |

## Step-by-Step Orchestration

### Step 0: Input Scan & Validation

Determine the starting state:

**Case A — User provides paper files:**
```
Scan --input-dir for files:
  .pdf               → classify as "paper"
  .html, .htm        → classify as "web_article"
  .xlsx, .csv, .tsv  → classify as "supplementary_table"
  .docx              → classify as "supplementary_doc"
  .json              → classify as "pre_extracted_data"
```

**Case B — User provides search keywords (no local files):**
Module 1 will perform online literature search. Check for `--search-keywords` argument or prompt user.

**Case C — User provides a previous run directory (resume mode):**
Validate that all required outputs from modules 1 through N-1 exist. If not, report which files are missing and stop.

Save classification to `pipeline_manifest.json`:

```json
{
  "pipeline_id": "run_20260530_001",
  "mode": "full",
  "domain": "pva_bopet",
  "classified_inputs": {
    "papers": ["paper1.pdf", "paper2.pdf"],
    "web_articles": [],
    "supplementary_tables": ["supp_table1.xlsx"],
    "supplementary_docs": [],
    "pre_extracted_data": [],
    "unrecognized": []
  },
  "search_terms": ["PVA optical film", "light transmittance", "haze"],
  "status": "initialized"
}
```

**If no valid input found**, report to user and suggest: provide paper files, provide search keywords, or provide a previous run directory.

---

### Step 1: Literature Acquisition (Module 1)

#### Case A — Local files provided:
1. For each `paper` (.pdf): extract text content. If PDF is scanned/image-based, flag as `requires_ocr` and attempt OCR. If OCR fails, mark as `unparseable`.
2. For each `web_article` (.html): extract main text body, strip navigation/ads/footers.
3. For each `supplementary_table` (.xlsx/.csv): parse tables, preserve sheet/table names.
4. Deduplicate papers by DOI > title similarity (>90%) > author+year match.
5. Build source manifest with metadata for every unique paper.

#### Case B — Online search:
1. Read `references/module-1-literature-acquisition.md` for search strategy.
2. Execute search via available tools (WebSearch, Semantic Scholar API, PubMed).
3. Collect paper metadata (title, authors, year, journal, DOI, abstract, URL).
4. For each result, attempt to fetch full text if open-access.
5. Deduplicate as above.
6. Build source manifest.

#### Output:
```
01_literature/
├── source_manifest.json     # [{source_id, title, authors, year, doi, abstract, url, access_status, file_path}]
├── dedup_report.json        # {duplicates_removed: N, duplicate_pairs: [{kept_id, removed_id, reason}]}
└── full_text/               # Extracted text content (one .txt per paper)
    ├── <source_id_1>.txt
    └── <source_id_2>.txt
```

Validate source manifest has at least 1 valid source. If zero, report and stop.

---

### Step 2: Experiment Data Extraction (Module 2)

For each paper in `source_manifest.json`:

1. Read `references/module-2-experiment-extraction.md` for extraction patterns.
2. Load the extraction schema from `templates/extraction_config_template.json` (or user-provided custom schema).
3. Load domain vocabulary from `assets/pva_bopet_vocabulary.json`.
4. Parse the paper's full text:
   - **Table extraction**: Identify all tables in text. Parse rows/columns. Map column headers to extraction schema fields.
   - **Text extraction**: Scan narrative paragraphs for experimental descriptions. Match patterns: "X was measured at Y °C", "the sample contained Z wt%", etc.
   - **Caption extraction**: Extract figure/table captions for context.
5. For each extracted experiment record:
   - Assign a unique `experiment_id` (format: `<source_id>_E<NNN>`)
   - Populate all applicable schema fields
   - Capture `source_snippet` (the original text that yielded this data)
   - Set initial `confidence` based on extraction clarity (direct table cell > explicit text > inferred from context)
6. Handle conflicts: if a paper reports the same experiment with different values (e.g., text says 80°C, table says 85°C), record both in `alternative_values` and flag in `ambiguities`.

#### Output:
```
02_extracted/
├── experiments_raw.json     # [{experiment_id, source_id, ...fields, source_snippet, confidence, alternative_values}]
└── extraction_log.json      # {total_papers, total_records_extracted, per_paper_stats, extraction_errors}
```

---

### Step 3: Data Normalization (Module 3)

Take `experiments_raw.json` as input. For each record:

1. Read `references/module-3-data-normalization.md` for normalization rules.
2. Load `assets/unit_conversions.json` and `assets/synonym_map.json`.
3. For each field that has a `value` + `unit`:
   - Standardize the unit (e.g., "°C" → canonical, "wt %" → "wt%", "μm" → canonical)
   - Convert to SI or domain-standard unit (e.g., mil → μm, kgf → N, atm → kPa)
   - Add `value_normalized` and `unit_normalized` fields
   - Log the conversion in `normalization_log.json`
4. For each material/additive/solvent name:
   - Map to canonical name using synonym map (e.g., "PVA-1799" → "PVA 1799", "glycerin" → "glycerol")
   - Add `name_canonical` field alongside `name_original`
5. Run the deterministic script for batch unit conversion:

```bash
python scripts/normalize_data.py \
  --input 02_extracted/experiments_raw.json \
  --output 03_normalized/experiments_normalized.json \
  --vocabulary assets/pva_bopet_vocabulary.json \
  --unit-map assets/unit_conversions.json \
  --synonym-map assets/synonym_map.json
```

6. Export to CSV and Excel:

```bash
python scripts/normalize_data.py \
  --input 03_normalized/experiments_normalized.json \
  --export-csv 03_normalized/experiments.csv \
  --export-xlsx 03_normalized/experiments.xlsx
```

#### Output:
```
03_normalized/
├── experiments_normalized.json
├── experiments.csv
├── experiments.xlsx
└── normalization_log.json   # {total_transformations, unit_conversions: [...], name_normalizations: [...], unconvertible: [...]}
```

---

### Step 4: Evidence & Traceability (Module 4)

Take `experiments_normalized.json` as input. For each record:

1. Read `references/module-4-evidence-traceability.md` for confidence scoring rules.
2. Link every field to its source evidence:
   - `source_id` → which paper
   - `source_page` → page number (if available from PDF)
   - `source_location` → "Table 2, Row 5" or "Section 3.2, Paragraph 2"
   - `source_snippet` → the original text
   - `extraction_method` → "table_parse" / "text_regex" / "llm_extraction" / "manual"
3. Recalculate confidence scores per field:
   - **1.0**: Directly quoted numerical value from a clearly labeled table cell
   - **0.8-0.9**: Explicitly stated in narrative text with unit
   - **0.6-0.7**: Extracted from text but unit or condition required inference
   - **0.4-0.5**: Value is ambiguous; recorded with alternatives
   - **0.1-0.3**: Estimated from graph/figure (digitized)
   - **0.0**: Value is missing; field null
4. Generate provenance table:

```bash
python scripts/build_provenance.py \
  --input 03_normalized/experiments_normalized.json \
  --sources 01_literature/source_manifest.json \
  --output 04_provenance/provenance.json
```

#### Output:
```
04_provenance/
├── provenance.json                    # [{experiment_id, field_provenance: {field: {source_snippet, page, confidence, method}}}]
└── confidence_distribution.json       # {histogram: {1.0: N, 0.8: N, ...}, mean_confidence, low_confidence_records: [...]}
```

---

### Step 5: Explanation Generation (Module 5)

Take `experiments_normalized.json` as input. For each record or group of related records:

1. Read `references/module-5-explanation-generation.md` for explanation templates.
2. For each experiment, generate a structured explanation:
   - **what_was_tested**: One sentence describing the experiment objective
   - **parameter_meaning**: What this parameter represents physically
   - **result_interpretation**: How the measured value should be understood
   - **trend_or_pattern**: If multiple related records exist, describe the visible trend
   - **hypothesis_support**: Whether this result supports or contradicts the paper's hypothesis
   - **caveats**: Limitations, potential confounding factors, or measurement uncertainties
3. Explanations must be factual and based on extracted evidence. If the paper does not state something explicitly, do not infer it.
4. Generate both Markdown report and structured JSON:

```bash
python scripts/generate_explanations.py \
  --input 03_normalized/experiments_normalized.json \
  --output 05_explanations/explanations.json \
  --language zh
```

#### Output:
```
05_explanations/
├── explanations.md          # Human-readable report with sections by material/property
└── explanations.json        # [{experiment_id, what_was_tested, parameter_meaning, ...}]
```

---

### Step 6: Ontology Modeling (Module 6)

Take `experiments_normalized.json` and `provenance.json` as input:

1. Read `references/module-6-ontology-modeling.md` for ontology construction rules.
2. Extract entities and relationships from the experiment data:
   - **Classes**: Material, Additive, ProcessStep, Instrument, Condition, Measurement, Property, Result
   - **Subclasses**: e.g., Material → Polymer → PVA, Material → Polymer → PET
   - **Relationships**: `hasAdditive`, `processedBy`, `measuredWith`, `hasProperty`, `conductedUnder`, `reportedIn`
   - **Attributes**: For each class, define relevant attributes (e.g., Material has `name`, `grade`, `molecular_weight`, `supplier`)
3. Build hierarchical structure. Handle conflicts: if two papers use different names for the same concept, merge under canonical name.
4. Generate ontology in multiple formats:

```bash
python scripts/build_ontology.py \
  --experiments 03_normalized/experiments_normalized.json \
  --provenance 04_provenance/provenance.json \
  --output 06_ontology/ontology.json \
  --format json,ttl,owl
```

#### Output:
```
06_ontology/
├── ontology.json            # Internal JSON representation
├── ontology.ttl             # Turtle format (if requested)
└── ontology.owl             # OWL format (if requested)
```

---

### Step 7: Literature Summary (Module 7)

Take all previous outputs as input:

1. Read `references/module-7-literature-summary.md` for summary structure.
2. Synthesize across all papers:
   - **Main themes**: What research questions dominate the collected literature
   - **Common experimental patterns**: Frequently used materials, conditions, measurement methods
   - **Performance trends**: How do key properties (transmittance, haze, tensile strength) vary across formulations
   - **Frequently used materials/conditions**: Top-10 most common additives, process temperatures, etc.
   - **Unresolved gaps**: What questions are not yet answered by the collected papers
   - **Promising directions**: Based on trends, what seems worth investigating
3. Generate structured summary:

```bash
python scripts/summarize_literature.py \
  --experiments 03_normalized/experiments_normalized.json \
  --provenance 04_provenance/provenance.json \
  --output 07_summary/literature_summary.json \
  --language zh
```

#### Output:
```
07_summary/
├── literature_summary.md    # Narrative summary with sections
└── literature_summary.json  # Structured summary
```

---

### Step 8: Finalize

1. Compile `ambiguities.json` — aggregate all unresolved ambiguities, missing fields, and conflicts from all modules.
2. Generate `run_summary.json`:

```json
{
  "pipeline_id": "run_20260530_001",
  "status": "completed",
  "domain": "pva_bopet",
  "modules_executed": [1, 2, 3, 4, 5, 6, 7],
  "statistics": {
    "papers_processed": 15,
    "experiments_extracted": 342,
    "experiments_after_dedup": 338,
    "mean_confidence": 0.82,
    "low_confidence_records": 23,
    "ontology_classes": 47,
    "ontology_relationships": 156,
    "ambiguities_unresolved": 12
  },
  "errors": [],
  "warnings": ["3 papers had no extractable experiment data"],
  "output_artifacts": ["experiments.csv", "experiments.xlsx", "provenance.json", "explanations.md", "ontology.json", "ontology.ttl", "literature_summary.md"]
}
```

3. Update `pipeline_manifest.json` with `status: "completed"`.

---

## Error Recovery Rules

1. **Single module failure** → Continue remaining modules if they don't depend on the failed module's output. Mark failure in manifest.

2. **Module dependencies**:
   - Module 2 depends on Module 1 output (source_manifest.json)
   - Module 3 depends on Module 2 output (experiments_raw.json)
   - Module 4 depends on Module 3 output (experiments_normalized.json)
   - Module 5 depends on Module 3 output (experiments_normalized.json) — can run independently of 4
   - Module 6 depends on Module 3 + Module 4 outputs
   - Module 7 depends on Module 3 + Module 4 outputs — can run independently of 5, 6

   If a dependency fails, skip dependent modules. Example: Module 2 fails → skip 3, 4; but 5, 6, 7 cannot run (need Module 3 data).

3. **PDF parsing failure** → Mark paper as `unparseable` in source_manifest.json. Add `parse_error` field with reason. Continue with remaining papers.

4. **Single record extraction failure** → Skip that record. Log the paper + location in `extraction_log.json`. Do not stop the pipeline.

5. **Unit conversion failure** → Keep original value. Add to `unconvertible` list in normalization_log.json. Do not fabricate a conversion.

6. **Ontology conflict** → Two papers claim contradictory relationships (e.g., Paper A says additive X increases haze, Paper B says it decreases). Record both as `ontology_conflict` in ambiguities.json with both sources. Do not resolve — flag for human review.

7. **Disk full** → Stop pipeline immediately. Report available space needed (estimate from current output size × remaining modules).

8. **All papers fail extraction** → Report pipeline as `failed`. Suggest: check paper format (scanned PDFs need OCR), check extraction schema compatibility, or try different papers.

---

## Pipeline Event Log

Each step writes a JSON line to `<output_dir>/.pipeline_events.jsonl`:

```jsonl
{"event": "pipeline_start", "mode": "full", "domain": "pva_bopet", "timestamp": "2026-05-30T10:00:00Z"}
{"event": "module_start", "module": 1, "module_name": "literature_acquisition", "timestamp": "2026-05-30T10:00:01Z"}
{"event": "module_complete", "module": 1, "papers_found": 15, "papers_after_dedup": 13, "duration_ms": 45000, "timestamp": "2026-05-30T10:00:46Z"}
{"event": "module_start", "module": 2, "module_name": "experiment_extraction", "timestamp": "2026-05-30T10:00:46Z"}
{"event": "module_complete", "module": 2, "records_extracted": 342, "papers_with_data": 10, "papers_no_data": 3, "duration_ms": 120000, "timestamp": "2026-05-30T10:02:46Z"}
{"event": "module_error", "module": 3, "error_type": "unconvertible_unit", "record_id": "paper5_E023", "field": "pressure", "original_value": "3 bar_g", "reason": "gauge pressure cannot be auto-converted to absolute", "timestamp": "2026-05-30T10:03:00Z"}
{"event": "module_complete", "module": 3, "records_normalized": 338, "unit_conversions": 523, "name_normalizations": 187, "unconvertible": 4, "timestamp": "2026-05-30T10:03:15Z"}
{"event": "pipeline_complete", "status": "completed", "total_duration_ms": 210000, "errors": 0, "warnings": 4, "timestamp": "2026-05-30T10:03:30Z"}
```

---

## Data Handoff Protocol

Modules pass data to each other via files, not in-memory. This ensures:
- Each module output is independently inspectable
- Pipeline can be resumed from any module
- Errors in one module don't corrupt upstream data

**Handoff chain:**
```
Module 1 → source_manifest.json + full_text/*.txt
                ↓
Module 2 → experiments_raw.json
                ↓
Module 3 → experiments_normalized.json + experiments.csv + experiments.xlsx
                ↓
Module 4 ─────────────┬──────────────────┐
  provenance.json     ↓                  ↓
                Module 5              Module 6
            explanations.json      ontology.json
                                       ↓
                                  Module 7
                              literature_summary.json
```

---

## Merging Rules for Incremental Runs

When adding new papers to an existing extraction:

1. Load the previous run's `03_normalized/experiments_normalized.json`
2. Run Modules 1-4 on the new papers only
3. Merge new records into existing ones:
   - If `experiment_id` already exists (same source), newer version wins
   - If different sources → append as new records
   - New `_merge_metadata` records the merge: `{"merged_from": "run_20260529_001", "new_sources": ["paper16.pdf"], "merge_timestamp": "..."}`
4. Re-run Modules 5-7 on the merged dataset to update explanations, ontology, and summary

---

## Resume Protocol

To resume from module N:

```bash
python scripts/run_pipeline.py \
  --input-dir <previous_run_output_dir> \
  --output-dir <new_output_dir> \
  --mode resume \
  --resume-from <N> \
  --skill-path <path_to_this_skill>
```

The script will:
1. Validate all outputs from modules 1 to N-1 exist in `<previous_run_output_dir>`
2. Copy them to `<new_output_dir>`
3. Continue execution from module N
4. Mark in manifest: `"resumed_from": "<previous_run_id>"`