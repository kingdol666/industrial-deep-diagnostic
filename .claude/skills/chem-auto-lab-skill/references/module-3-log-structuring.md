# Module 3: Experiment Log Structuring

You convert natural language chemistry laboratory notes into structured JSON records with high fidelity.

## Core Principle

Preserve the chemist's intent. Abbreviations, shorthand, and implicit knowledge are common in lab notes. Extract what you can with confidence, flag what is ambiguous, and NEVER fabricate data. Every extracted field includes a `confidence` score.

## Common Chemistry Lab Note Patterns

### Pattern 1: Synthesis / Preparation

> "Dissolved 2.5g of PVA (Mw 89000-98000) in 50mL deionized water at 90°C for 2h with stirring at 300rpm. Solution became clear and viscous."

**Expected extraction**:
```json
{
  "action": "dissolution",
  "material": {"name": "PVA", "spec": "Mw 89000-98000"},
  "amount": {"value": 2.5, "unit": "g"},
  "solvent": {"name": "deionized water", "amount": {"value": 50, "unit": "mL"}},
  "conditions": [
    {"parameter": "temperature", "value": 90, "unit": "C"},
    {"parameter": "duration", "value": 2, "unit": "h"},
    {"parameter": "stirring_speed", "value": 300, "unit": "rpm"}
  ],
  "observation": "solution became clear and viscous"
}
```

### Pattern 2: Characterization / Measurement

> "UV-Vis at 550nm showed transmittance of 92%. Film thickness was 0.15mm ±0.02."

**Expected extraction**:
```json
{
  "measurements": [
    {"technique": "UV-Vis", "wavelength": {"value": 550, "unit": "nm"}, "result": {"parameter": "transmittance", "value": 92, "unit": "%"}},
    {"technique": "micrometer", "result": {"parameter": "thickness", "value": 0.15, "unit": "mm", "uncertainty": 0.02}}
  ]
}
```

### Pattern 3: Observation / Result

> "After drying at 60C overnight, film turned slightly yellow. Transparency decreased from 95% to 88%."

**Expected extraction**:
```json
{
  "condition_change": {"parameter": "drying", "temperature": {"value": 60, "unit": "C"}, "duration": "overnight"},
  "observations": [
    {"type": "color_change", "from": null, "to": "slightly yellow"},
    {"type": "property_change", "parameter": "transmittance", "from": {"value": 95, "unit": "%"}, "to": {"value": 88, "unit": "%"}}
  ]
}
```

### Pattern 4: Bilingual Notes (Chinese + English mixed)

> "加入5wt%纳米纤维素 (CNC, length 100-200nm)，搅拌30min后粘度明显增加。Viscosity increased from 1200 to 3500 cP."

**Expected extraction**:
```json
{
  "materials": [{"name": "CNC (nanocellulose)", "spec": "length 100-200nm", "amount": {"value": 5, "unit": "wt%"}}],
  "procedure": [{"action": "stirring", "duration": {"value": 30, "unit": "min"}}],
  "observations": [{"type": "property_change", "parameter": "viscosity", "from": {"value": 1200, "unit": "cP"}, "to": {"value": 3500, "unit": "cP"}}]
}
```

## Extraction Strategy

### Phase 1: Pre-processing (script does this)

1. **Abbreviation expansion**: Expand common chemistry abbreviations using a built-in dictionary.
   - `DI water` → `deionized water`
   - `RT` → `room temperature (~25°C)`
   - `o/n` → `overnight (~12-16h)`
   - `r.t.` → `room temperature`
   - `eq.` → `equivalent`

2. **Unit normalization**: Recognize and standardize unit expressions.
   - `120C` → `120 °C`
   - `5wt%` → `5 wt%`
   - `50mL` → `50 mL`
   - `2h` → `2 h`

3. **Number normalization**: Handle ranges, uncertainties, and special values.
   - `0.15mm ±0.02` → `{"value": 0.15, "uncertainty": 0.02, "unit": "mm"}`
   - `~25°C` → `{"value": 25, "approximate": true, "unit": "C"}`
   - `120-130°C` → `{"range": [120, 130], "unit": "C"}`
   - `slightly`, `a little` → tag as `qualitative: true`

### Phase 2: LLM Extraction (Claude processes the text)

Use the few-shot examples above as the extraction guide. For each sentence or paragraph:

1. Classify the sentence type: `procedure`, `measurement`, `observation`, `result`, `planning`
2. Extract structured fields matching `schemas/experiment_record.schema.json`
3. Assign confidence to each extracted field:
   - `high` — Explicitly stated with clear numeric value and unit
   - `medium` — Explicitly stated but unit ambiguous or value approximate
   - `low` — Implied or inferred from context

### Phase 3: Post-processing (script validates)

1. Validate against JSON schema
2. Cross-check: same parameter mentioned multiple times should have consistent values
3. Flag contradictions (e.g., "dried at 120°C" in one sentence, "heat treatment at 100°C" later)

## Script Usage

```bash
# Basic usage
python scripts/structure_notes.py --input lab_notebook.txt --output structured.json

# With additional context (helps disambiguate)
python scripts/structure_notes.py \
  --input lab_notebook.txt \
  --output structured.json \
  --context "This is a nanocellulose composite film preparation experiment."

# Stdin mode
echo "Dissolved 5g PVA in 100mL water at 90C for 1h." | python scripts/structure_notes.py --stdin --output result.json
```

## Output Format

```json
{
  "metadata": {
    "script": "structure_notes.py",
    "version": "1.0.0",
    "input_file": "lab_notebook.txt",
    "context": "nanocellulose composite film",
    "processing_timestamp": "2026-05-24T10:00:00Z",
    "sentences_processed": 12,
    "fields_extracted": 28
  },
  "experiments": [
    {
      "experiment_id": "NOTE-001",
      "source_text": "Dissolved 2.5g of PVA in 50mL deionized water at 90°C for 2h.",
      "structured": {
        "action": "dissolution",
        "materials": [
          {
            "name": "PVA",
            "specification": null,
            "amount": {"value": 2.5, "unit": "g"},
            "role": "solute",
            "confidence": "high"
          }
        ],
        "solvent": {
          "name": "deionized water",
          "amount": {"value": 50, "unit": "mL"},
          "confidence": "high"
        },
        "conditions": [
          {"parameter": "temperature", "value": 90, "unit": "C", "confidence": "high"},
          {"parameter": "duration", "value": 2, "unit": "h", "confidence": "high"}
        ],
        "observations": []
      },
      "confidence_overall": "high",
      "ambiguities": [],
      "warnings": []
    }
  ]
}
```

## Ambiguity Handling

When the LLM cannot confidently extract a field:

1. **Multiple interpretations**: List all candidate interpretations with likelihoods.
   - "heated" → could be hot plate, oven, or microwave → `{"ambiguity": "heating_method", "candidates": ["hot_plate", "oven", "microwave"], "most_likely": "oven"}`

2. **Missing units**: Infer from context if possible, otherwise flag.
   - "added 5 NaCl" → `{"value": 5, "unit_ambiguous": true, "possible_units": ["g", "mg", "wt%"]}`

3. **Vague temporal**: Map common phrases to ranges.
   - "overnight" → `{"duration_range": [8, 16], "unit": "h", "confidence": "medium"}`
   - "briefly" → `{"duration_range": [1, 5], "unit": "min", "confidence": "low"}`

## Edge Cases

1. **Handwritten OCR output** — Expect typos, missing punctuation. Use fuzzy matching for chemical names.
2. **Reaction schemes** — `A + B → C (yield 85%)`. Extract reactants, products, yield.
3. **Tabular notes** — Some notes are semi-structured tables. Detect alignment, parse as table first.
4. **Strikethrough/corrections** — If notes show "~~120°C~~ 110°C", extract the corrected value with a note about the edit.
5. **References to other experiments** — "Same conditions as EXP-042". Link to referenced experiment ID.