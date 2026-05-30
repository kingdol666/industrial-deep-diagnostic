# Module 2: Experiment Data Extraction

> **Load this file when Module 2 is invoked.**
> Purpose: Extract structured experimental data from paper full text — tables, narrative paragraphs, and figure captions.

## Extraction Approach

The extraction combines three strategies, applied in order:

1. **Table extraction** (deterministic) — Parse markdown/HTML tables; map column headers to schema fields
2. **Narrative extraction** (LLM-guided) — Scan paragraphs for experimental descriptions using domain patterns
3. **Caption extraction** (context) — Extract figure/table captions to supplement table/text data

## Extraction Schema

Default extraction fields for PVA/BOPET optical films. Each extracted record maps to these fields:

```json
{
  "experiment_id": "SRC_001_E001",
  "source_id": "SRC_001",
  "paper_title": "...",
  "year": 2023,
  "source_doi": "10.1016/...",
  "sample_name": "PVA/CNC-5%",
  "material_system": "PVA",
  "material_grade": "1799",
  "additive": "CNC",
  "additive_concentration": 5,
  "additive_concentration_unit": "wt%",
  "plasticizer": "glycerol",
  "plasticizer_concentration": 30,
  "plasticizer_concentration_unit": "wt%",
  "crosslinker": null,
  "crosslinker_concentration": null,
  "solvent": "water",
  "solution_concentration": 10,
  "solution_concentration_unit": "wt%",
  "film_preparation_method": "solution_casting",
  "drying_temperature": 40,
  "drying_temperature_unit": "°C",
  "drying_time": 24,
  "drying_time_unit": "h",
  "heat_treatment_temperature": null,
  "heat_treatment_time": null,
  "stretching_ratio": null,
  "stretching_temperature": null,
  "film_thickness": 80,
  "film_thickness_unit": "μm",
  "instrument": "UV-Vis spectrophotometer",
  "measured_property": "light_transmittance",
  "measured_value": 90.5,
  "measured_unit": "%",
  "wavelength": 550,
  "wavelength_unit": "nm",
  "measured_property_2": "tensile_strength",
  "measured_value_2": 65.3,
  "measured_unit_2": "MPa",
  "measured_property_3": "elongation_at_break",
  "measured_value_3": 180,
  "measured_unit_3": "%",
  "comparison_baseline": "pure PVA film (transmittance: 89.2%, tensile: 45.8 MPa)",
  "result_direction": "improved",
  "error_type": "std_dev",
  "error_value": 1.2,
  "conclusion_author": "CNC addition up to 5 wt% improves both optical transparency and mechanical strength",
  "source_page": 5,
  "source_location": "Table 2, Row 3",
  "source_snippet": "The PVA/CNC-5% film exhibited light transmittance of 90.5% at 550 nm and tensile strength of 65.3 MPa",
  "confidence": 0.9,
  "notes": ""
}
```

### Multi-Property Records

When a paper reports multiple properties for the same sample, populate all `measured_property_N` / `measured_value_N` pairs in a single record. This preserves the fact that these measurements came from the same physical sample.

When properties are measured on different samples or under different conditions → create separate records.

## Table Extraction Protocol

### Step 1: Identify Tables

Scan the full text for table markers:
- Markdown tables (`| col1 | col2 |`)
- HTML tables (`<table>...</table>`)
- ASCII/plain-text tables (rows aligned by whitespace)
- LaTeX tables (`\begin{tabular}...\end{tabular}`)

### Step 2: Parse Table Structure

For each table:
1. Extract column headers (first row or `<th>` elements)
2. Extract all data rows
3. Identify the "sample name" column (usually first column, contains material/formulation names)
4. Identify numeric columns (containing measured values)

### Step 3: Map Columns to Schema

Map column headers to extraction schema fields using keyword matching:

| Table Column Header Keywords | Maps to Schema Field |
|------------------------------|---------------------|
| "Sample", "Film", "Formulation", "Specimen", "样品", "薄膜" | `sample_name` |
| "PVA", "Matrix", "Polymer", "基体" | `material_system` |
| "Additive", "Filler", "Nanofiller", "Reinforcement", "添加物", "填料" | `additive` |
| "Content", "Loading", "Concentration", "wt%", "含量", "浓度" | `additive_concentration` |
| "Thickness", "Film thickness", "厚度" | `film_thickness` |
| "Transmittance", "T%", "Light transmission", "透光率" | `measured_property` = `light_transmittance` |
| "Haze", "雾度" | `measured_property` = `haze` |
| "Tensile strength", "σ", "拉伸强度" | `measured_property` = `tensile_strength` |
| "Elongation", "ε", "断裂伸长率" | `measured_property` = `elongation_at_break` |
| "Young's modulus", "E", "弹性模量" | `measured_property` = `youngs_modulus` |
| "WVTR", "Water vapor transmission", "水蒸气透过率" | `measured_property` = `wvtr` |
| "OTR", "Oxygen transmission", "氧气透过率" | `measured_property` = `otr` |
| "Contact angle", "接触角" | `measured_property` = `contact_angle` |
| "Tg", "Glass transition", "玻璃化转变温度" | `measured_property` = `tg` |
| "Tm", "Melting temperature", "熔点" | `measured_property` = `tm` |
| "Td", "Decomposition temperature", "分解温度" | `measured_property` = `td` |

If a column header does not match any known keyword, flag it in `notes` and skip it — don't force a mapping.

### Step 4: Extract Values with Units

For numeric columns:
1. Parse the number (handle "~", "≈", ">", "<" prefixes → flag as approximate)
2. Extract the unit from column header, table caption, or adjacent text
3. Handle ranges: "80-85" → record as `value: 82.5, value_type: "range_midpoint", value_min: 80, value_max: 85`
4. Handle error values: "65.3±1.2" → `value: 65.3, error_type: "std_dev", error_value: 1.2`

## Narrative Text Extraction Protocol

For paragraphs that describe experiments but do not contain structured tables:

### Pattern Matching Rules

Scan each paragraph for these patterns (case-insensitive, with unit flexibility):

```
Pattern: "<material> film[s] [were/was] prepared by <method>"
Extract: film_preparation_method

Pattern: "concentration of <X> [was/were] <value> <unit>"
Extract: X → additive/plasticizer, value, unit

Pattern: "dried at <value> <unit> for <value2> <unit2>"
Extract: drying_temperature + unit, drying_time + unit2

Pattern: "[was/were] measured [using/by] <instrument>"
Extract: instrument name

Pattern: "exhibited [a/an] <property> of <value> <unit>"
Extract: measured_property, measured_value, measured_unit

Pattern: "increased/decreased/improved/enhanced by <value>%"
Extract: result_direction ("improved" or "degraded"), comparison_baseline from context

Pattern: "compared to/with <baseline description>"
Extract: comparison_baseline
```

### Multi-Value Extraction from a Single Paragraph

A single paragraph may describe multiple measurements. Example:

> "The PVA/GO-2% film showed a light transmittance of 88.3% at 550 nm, tensile strength of 72.1 MPa, and elongation at break of 155%."

This yields ONE record with three measured properties — because all measurements are on the same sample.

### Ambiguous Extraction

When a value could come from multiple possible locations in the text:

```
Record all candidates in `alternative_values`:
[
  {"field": "drying_temperature", "value": 40, "unit": "°C", "source": "Section 2.3, Para 1"},
  {"field": "drying_temperature", "value": 50, "unit": "°C", "source": "Table 1 caption"}
]
```

Set confidence to 0.5. Do NOT arbitrarily pick one.

## Caption Extraction

For every figure and table caption found in the text:
1. Extract the caption text
2. Identify which sample(s) the figure/table refers to
3. Attach as `caption_context` to the relevant record(s)
4. If the caption contains numerical values not found in the main text or tables, extract them with lower confidence (0.6-0.7)

## Quality Control

After extraction, for each paper, report:

```
Paper SRC_001: 12 records extracted
  - 8 from tables (confidence 0.8-1.0)
  - 3 from narrative text (confidence 0.6-0.8)
  - 1 from caption (confidence 0.6)
  - 2 records with ambiguous values flagged
  - 0 records with missing required fields
```

## Edge Cases

| Scenario | Action |
|----------|--------|
| Paper describes multiple film formulations | Create one record per distinct formulation |
| Paper reports properties at multiple wavelengths | Record all wavelengths (do not average); create separate records if values differ significantly |
| Paper reports only graphs/charts, no tables | Flag as `graph_only`. Attempt digitization if user requests; otherwise mark as `data_not_extractable` |
| Paper uses non-standard units (e.g., "parts per hundred resin") | Extract as-is; Module 3 will normalize |
| Sample name is ambiguous ("Sample A", "Film 1") | Use as-is but flag `ambiguous_naming: true` in notes |
| Paper describes preparation but doesn't report measurements | Extract preparation conditions; leave measured properties null; flag as `preparation_only` |