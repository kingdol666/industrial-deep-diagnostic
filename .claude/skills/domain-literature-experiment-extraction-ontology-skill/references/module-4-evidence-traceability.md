# Module 4: Evidence & Traceability

> **Load this file when Module 4 is invoked.**
> Purpose: Attach provenance metadata to every extracted data point, compute per-field confidence scores, and generate the full provenance table.

## Core Principle

Every piece of data must answer: **"Where did this come from, and how much should I trust it?"**

If a field cannot be traced to a specific location in a source document, its confidence score must reflect that uncertainty. The skill must NEVER fabricate provenance.

## Provenance Schema

Each extracted record carries provenance at two levels:

### Record-Level Provenance

```json
{
  "experiment_id": "SRC_001_E001",
  "source_id": "SRC_001",
  "source_title": "Enhanced Optical and Mechanical Properties...",
  "source_authors": ["Zhang, W.", "Li, X.", "Wang, Y."],
  "source_year": 2023,
  "source_doi": "10.1016/j.carbpol.2023.120563",
  "extraction_date": "2026-05-30",
  "extraction_agent": "domain-literature-experiment-extraction-ontology-skill v1.0.0"
}
```

### Field-Level Provenance

For each populated field, store:

```json
{
  "field_provenance": {
    "additive_concentration": {
      "source_location": "Table 2, Row 3, Column 'CNC content (wt%)'",
      "source_page": 5,
      "source_snippet": "The PVA/CNC-5% film...",
      "extraction_method": "table_parse",
      "confidence": 1.0,
      "assumptions": []
    },
    "drying_temperature": {
      "source_location": "Section 2.3, Paragraph 2",
      "source_page": 3,
      "source_snippet": "...cast films were dried at 40°C for 24 h in a vacuum oven",
      "extraction_method": "text_regex",
      "confidence": 0.85,
      "assumptions": ["Assumed vacuum oven drying; paper does not specify oven type explicitly"]
    }
  }
}
```

## Extraction Methods

| Method | Description | Typical Confidence Range |
|--------|-------------|------------------------|
| `table_parse` | Directly parsed from a structured table cell | 0.9 - 1.0 |
| `text_regex` | Extracted from narrative text using pattern matching | 0.7 - 0.9 |
| `llm_extraction` | Extracted by LLM reasoning from ambiguous text | 0.5 - 0.8 |
| `caption_parse` | Extracted from figure/table caption | 0.6 - 0.8 |
| `graph_digitize` | Estimated from a chart/graph (if digitization was performed) | 0.3 - 0.6 |
| `inferred_context` | Inferred from context (e.g., units assumed from adjacent columns) | 0.3 - 0.5 |
| `cross_reference` | Value confirmed by cross-referencing multiple locations in the paper | +0.05 to +0.1 boost |

## Confidence Scoring Rules

### Per-Field Confidence

Apply these rules to determine the initial confidence for each field:

**Confidence = 1.0** (Definitive):
- Value directly from a clearly labeled table cell with explicit unit in the column header
- Example: Table column "Tensile strength (MPa)" with cell value "65.3" → confidence 1.0

**Confidence = 0.9** (High):
- Value explicitly stated in narrative text with unit immediately adjacent
- Value from a table cell where the unit is in the table caption (not column header)
- Example: "... exhibited a tensile strength of 65.3 MPa" → confidence 0.9

**Confidence = 0.8** (Good):
- Value from a table cell where the unit must be inferred from adjacent columns or table notes
- Value stated in text with unit elsewhere in the same paragraph
- Example: "Tensile strength was 65.3" (unit "MPa" found in previous sentence) → confidence 0.8

**Confidence = 0.7** (Moderate):
- Value extracted from text with non-standard phrasing
- Value from a figure/table caption
- Cross-referenced value where one source is weaker
- Example: Caption: "Fig 3. Tensile strength of PVA/CNC films (CNC-5%: 65.3 MPa)" → confidence 0.7

**Confidence = 0.6** (Fair):
- Value requires one reasonable assumption (e.g., "room temperature" → assumed 25°C)
- Value extracted from a non-English text with translation
- Value from a supplementary file with different formatting than the main paper

**Confidence = 0.5** (Borderline):
- Value is ambiguous; recorded with alternative_values
- Value from multiple locations in the paper that slightly disagree (±5%)
- Value that required unit inference from domain knowledge (not stated in paper)

**Confidence = 0.4** (Low):
- Value that required two or more assumptions
- Value digitized from a graph/chart (if graph digitization was performed)
- Value from a preprint (not peer-reviewed)

**Confidence = 0.3** (Very Low):
- Value from a patent (may use idealized or range-bound values)
- Value from a review paper citing another source (secondary source)

**Confidence = 0.1-0.2** (Marginal):
- Value mentioned in passing without supporting data in the paper
- Value appears in abstract only, not in results section

**Confidence = 0.0** (None):
- Field is null; no value could be extracted

### Confidence Adjustments

After initial scoring, apply these adjustments:

| Condition | Adjustment |
|-----------|------------|
| Paper is peer-reviewed (journal article) | No change (baseline) |
| Paper is a preprint (not yet peer-reviewed) | -0.1 |
| Paper is a patent | -0.2 |
| Paper is from a top-tier journal (Nature, Science, Advanced Materials, etc.) | No change (don't inflate for prestige) |
| Value confirmed by cross-referencing two independent locations in the same paper | +0.05 |
| Value appears in both text AND a table, with exact match | +0.05 |
| Value conflicts with another value in the same paper (±10% or more) | -0.2, record conflict |
| Value is from a paper with a known retraction or correction | Flag, -0.3 |
| Unit was inferred from domain knowledge (not stated in paper) | -0.1 |
| Paper has fewer than 5 citations (recent paper or low-impact) | No change (don't penalize for newness) |

### Record-Level Confidence

The overall record confidence is the **minimum** of all populated field confidences (not the average). A record is only as trustworthy as its weakest data point.

Records with `record_confidence < 0.5` are flagged in `confidence_distribution.json` as `low_confidence_records`.

## Provenance Table Generation

Run the script to compile the full provenance table:

```bash
python scripts/build_provenance.py \
  --input 03_normalized/experiments_normalized.json \
  --sources 01_literature/source_manifest.json \
  --output 04_provenance/provenance.json
```

The provenance table is a flat JSON structure:

```json
[
  {
    "experiment_id": "SRC_001_E001",
    "field": "additive_concentration",
    "source_id": "SRC_001",
    "source_title": "...",
    "source_page": 5,
    "source_location": "Table 2, Row 3, Column 'CNC content (wt%)'",
    "source_snippet": "...",
    "extraction_method": "table_parse",
    "value_normalized": 5,
    "unit_normalized": "wt%",
    "confidence": 1.0,
    "assumptions": []
  }
]
```

## Confidence Distribution Report

Generate a summary of confidence across all records:

```json
{
  "total_records": 342,
  "total_fields_populated": 4788,
  "mean_confidence": 0.82,
  "median_confidence": 0.85,
  "confidence_histogram": {
    "1.0": 1200,
    "0.9": 1800,
    "0.8": 900,
    "0.7": 500,
    "0.6": 200,
    "0.5": 100,
    "0.4": 60,
    "0.3": 20,
    "0.2": 5,
    "0.1": 3
  },
  "low_confidence_records": [
    {"experiment_id": "SRC_008_E045", "record_confidence": 0.3, "weakest_field": "drying_temperature"},
    {"experiment_id": "SRC_012_E078", "record_confidence": 0.4, "weakest_field": "additive_concentration"}
  ],
  "extraction_method_distribution": {
    "table_parse": 3200,
    "text_regex": 1200,
    "llm_extraction": 300,
    "caption_parse": 88
  }
}
```

## Evidence Gaps Report

Identify and report what the collected papers do NOT provide:

- Which extraction schema fields are null across all records? (systemic gap)
- Which papers contributed the most low-confidence records? (source quality issue)
- Which experiment types or measurement types are underrepresented?

## Rules for Handling Missing Evidence

1. **Never hallucinate a source location.** If you can't pinpoint where a value came from, set `source_location` to `"unknown"` and reduce confidence by 0.2.

2. **Never invent a source snippet.** If the original text was not preserved, set `source_snippet` to `null` and note `"original_text_not_preserved"` in assumptions.

3. **Never elevate confidence without justification.** If a value was simply "found" without clear extraction, confidence must be ≤ 0.5.

4. **Always prefer under-confidence to over-confidence.** A user who sees a low confidence score can investigate further. A user who trusts a high-confidence fabricated value may make bad decisions.

## Edge Cases

| Scenario | Action |
|----------|--------|
| Paper is a meta-analysis citing other papers | Each cited value gets source = the meta-analysis paper, NOT the original paper. Flag `secondary_source: true` and -0.2 confidence |
| Same data appears in multiple papers (e.g., thesis + journal article) | Keep both but cross-reference; note `duplicate_data: true`, use the more authoritative version |
| Paper has an erratum/correction | If correction changes a value, use corrected value. Note `corrected: true` with reference to erratum |
| Value digitized from a graph (user-requested) | Set `extraction_method: "graph_digitize"`, confidence 0.3-0.6 depending on graph quality |