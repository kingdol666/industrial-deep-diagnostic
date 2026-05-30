# Module 1: Literature Acquisition

> **Load this file when Module 1 is invoked.**
> Purpose: Search, collect, deduplicate, and build a source manifest of scientific literature for the target domain.

## Search Strategy

### Source Priority

Search in this order. Stop when enough relevant papers are found (default: 20-50 papers, configurable):

1. **User-provided files** (local PDFs, HTML, supplementary materials) — highest priority, always process first
2. **Semantic Scholar API** — best for academic paper discovery with citation context
3. **PubMed / Europe PMC** — for biomedical and materials-science adjacent papers
4. **arXiv** — for preprints in materials science, physics, chemistry
5. **Google Scholar** — broad coverage, use as fallback; harder to parse systematically
6. **Patent databases** (Google Patents, WIPO) — for industrial formulations and process patents

### Search Query Construction

For PVA/BOPET optical films, construct queries with Boolean operators:

**Core queries (always run):**
```
("PVA" OR "polyvinyl alcohol") AND ("optical film" OR "optical properties" OR "transparent")
("BOPET" OR "biaxially oriented PET") AND ("optical" OR "light transmittance" OR "haze")
```

**Property-focused queries:**
```
("PVA film" OR "PVA composite film") AND ("tensile strength" OR "mechanical properties" OR "elongation")
("PVA" OR "BOPET") AND ("water vapor transmission" OR "WVTR" OR "oxygen barrier" OR "OTR")
```

**Additive-focused queries:**
```
("PVA" OR "polyvinyl alcohol") AND ("nanocellulose" OR "CNC" OR "CNF" OR "graphene oxide" OR "GO") AND ("film")
("PVA film") AND ("crosslinker" OR "plasticizer") AND ("optical" OR "mechanical")
```

**Process-focused queries:**
```
("PVA film") AND ("solution casting" OR "melt extrusion" OR "stretching" OR "annealing") AND ("optical properties")
```

### Search Constraints

Apply filters based on user configuration or sensible defaults:

| Filter | Default | Rationale |
|--------|---------|-----------|
| Year range | 2015-2026 | Last 10 years covers modern formulations |
| Language | English, Chinese | Most PVA/BOPET research is in these languages |
| Publication type | Journal articles, conference papers, patents | Exclude books, theses (unless user requests) |
| Access | Prefer open-access; flag paywalled papers | Cannot extract from paywalled papers without user-provided PDF |

## Paper Relevance Screening

For each search result, apply a two-stage screening:

### Stage 1: Title + Abstract Screening (Fast)

**KEEP if** the paper mentions ALL of:
- PVA, BOPET, PET, or related optical polymer material AND
- Film, membrane, coating, or thin film AND
- At least one: experimental data, measurement, characterization, property, performance

**DISCARD if** the paper is:
- Pure theory/simulation without experimental validation
- Biomedical application (drug delivery, wound dressing, tissue engineering) — unless explicitly about optical properties
- Review paper without original experimental data
- Not about film form (e.g., PVA fiber, PVA hydrogel bead, PVA solution rheology)

**FLAG for manual review if**:
- Title is ambiguous but abstract suggests experimental data
- Paper is in a non-English/non-Chinese language
- Paper is from a non-materials-science journal

### Stage 2: Full Text Screening (After download)

**KEEP if** the paper contains:
- At least one data table with measured values
- At least one explicitly stated experimental condition (temperature, concentration, time)
- Measurable optical or mechanical property values

**DISCARD if** full text reveals:
- No quantitative experimental data (purely qualitative descriptions)
- Paywalled and cannot access full text
- Duplicate of another paper (same data, different publication)

## Source Metadata Collection

For every KEPT paper, extract the following metadata:

```json
{
  "source_id": "SRC_001",
  "title": "Enhanced Optical and Mechanical Properties of PVA/Cellulose Nanocrystal Composite Films",
  "authors": ["Zhang, W.", "Li, X.", "Wang, Y."],
  "year": 2023,
  "journal": "Carbohydrate Polymers",
  "volume": "305",
  "pages": "120563",
  "doi": "10.1016/j.carbpol.2023.120563",
  "url": "https://doi.org/10.1016/j.carbpol.2023.120563",
  "abstract": "Polyvinyl alcohol (PVA) composite films...",
  "document_type": "journal_article",
  "language": "en",
  "access_status": "open_access",
  "keywords_author": ["PVA", "cellulose nanocrystal", "composite film", "optical properties"],
  "citation_count": 15,
  "file_path": "01_literature/full_text/SRC_001.txt",
  "screening_decision": "KEPT",
  "screening_notes": ""
}
```

## Deduplication Protocol

Run deduplication in this priority order:

1. **DOI match** (exact) — definitive. Keep the version with more complete metadata.
2. **Title similarity > 90%** (case-insensitive, punctuation-stripped) — strong signal. Compute Levenshtein ratio.
3. **Same first author + same year + title similarity > 70%** — likely same paper (preprint vs published).
4. **Same DOI prefix but different suffix** — could be erratum/correction. Keep both, flag relationship.

For each duplicate pair found, log in `dedup_report.json`:

```json
{
  "duplicates_removed": 5,
  "duplicate_pairs": [
    {
      "kept_id": "SRC_003",
      "removed_id": "SRC_012",
      "reason": "DOI match",
      "kept_title": "...",
      "removed_title": "..."
    }
  ]
}
```

## Full Text Extraction

### PDF Processing

1. Attempt text extraction with `pdftotext` or equivalent tool
2. If text layer exists → extract directly
3. If text layer is empty/missing → flag as `requires_ocr`, attempt OCR
4. If OCR fails or produces < 500 characters of meaningful text → mark as `unparseable`
5. For scanned PDFs that produce garbled text → mark as `ocr_low_quality`, flag for human review

### HTML Processing

1. Extract main content area (ignore nav, sidebar, footer, ads)
2. Preserve heading hierarchy (h1 → h2 → h3) for section context
3. Strip HTML tags, preserve paragraph breaks
4. If tables are present, preserve their structure as markdown tables for Module 2

### Supplementary Materials

1. `.xlsx` / `.csv` → parse all sheets, preserve sheet name as context
2. `.docx` → extract text + tables
3. `.pdf` supplementary → same as PDF processing above

## Output Validation

After building `source_manifest.json`, validate:

- All `source_id` values are unique
- All KEPT papers have `file_path` pointing to an existing file
- At least one paper exists with `access_status: "open_access"` or has a local file
- No paper has `screening_decision: "KEPT"` without a `doi` or `title`

## Edge Cases

| Scenario | Action |
|----------|--------|
| Paper has no DOI | Use title + first author + year as identifier; flag `missing_doi: true` |
| Paper is a preprint (no journal/volume) | Set `document_type: "preprint"`, `journal: null` |
| Paper in Chinese | Process normally; set `language: "zh"`. Chinese text extraction requires CJK-aware tools |
| Patent document | Set `document_type: "patent"`. Focus on "Examples" or "实施例" section |
| Paper is a review but contains original data tables | Keep, but flag `review_with_original_data: true` |
| Paywalled paper without user-provided PDF | Mark `access_status: "paywalled_no_access"`, do not attempt extraction |