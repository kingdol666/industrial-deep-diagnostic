---
name: literature-to-lab-bridge
description: "Use when the user wants to search scientific literature for experimental data AND automatically analyze it through a chemistry laboratory pipeline. This skill bridges domain-literature-experiment-extraction-ontology-skill (literature search + experiment extraction) with chem-auto-lab-skill (data cleaning + spectroscopy + report + recommendations). Triggers on: 从文献中搜索实验数据并自动分析, 文献数据自动化处理, 论文实验数据提取并分析, literature-to-lab, 搜索论文并分析实验, 文献挖掘+化学分析, automated literature-driven lab analysis, search papers and run chemical analysis. Make sure to use this skill whenever the user mentions both literature search/data extraction AND chemical/laboratory analysis in the same request. Do NOT trigger for: literature search only (use domain-literature skill), lab data analysis only (use chem-auto-lab skill), or non-chemistry domains."
version: 1.0.0
---

# Literature-to-Lab Bridge Skill

## Language Default

默认输出语言为中文。报告、解释、摘要使用中文。JSON 字段名、Schema 定义、枚举值使用英文。

## Core Principle

This skill orchestrates a **five-phase pipeline with anti-fabrication guarantees**:

- **Phase 0**: Multi-round iterative literature search (3-4 rounds of increasingly specific queries)
- **Phase 1**: Literature data extraction + normalization (`domain-literature-experiment-extraction-ontology-skill`)
- **Phase 1.5**: **Gap Verification** — verifies each identified research gap via targeted literature cross-reference
- **Phase 2**: Lab analysis — cleaning, report, recommendations (`chem-auto-lab-skill`)
- **Phase 3**: **Evidence Grading** — grades every recommendation by evidence quality (A/B/C/D), scores feasibility, and outputs the single most feasible research plan with literature anchors for every claim

A **data transformer** bridges Phase 1 → Phase 2 to map literature schema into lab-compatible format.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   Literature-to-Lab Bridge Pipeline v2.0                          │
│                        with Anti-Fabrication Guarantees                            │
│                                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  PHASE 0: Multi-Round Literature Search (NEW)                 │                 │
│  │  Round 1: Core domain keywords                                │                 │
│  │  Round 2: Synonym/related terms broader coverage              │                 │
│  │  Round 3: Mechanism-specific deep dive                        │                 │
│  │  Round 4: Quality filter (impact factor, citations, recency)  │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ merged paper corpus                                  │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  PHASE 1: Literature Extraction & Normalization               │                 │
│  │  domain-literature-experiment-extraction-ontology-skill       │                 │
│  │  Module 1→2→3→4→7                                             │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ experiments_normalized.json                          │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  QUALITY GATE                                                 │                 │
│  │  records≥10 | confidence≥0.5 | papers≥3                       │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ PASS                                               │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  PHASE 1.5: Gap Verification (NEW)                            │                 │
│  │  gap_verifier.py                                              │                 │
│  │  ├─ Cross-reference gaps against all extracted papers         │                 │
│  │  ├─ Build targeted search queries for each gap                │                 │
│  │  ├─ Score: novelty (0-10) + evidence grade (A-E)              │                 │
│  │  └─ Reject false gaps, prioritize verified ones               │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ verified_gaps.json                                   │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  DATA TRANSFORMER                                             │                 │
│  │  transform_literature_to_lab.py                               │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ lab_experiments.json                                  │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  PHASE 2: Lab Analysis                                        │                 │
│  │  chem-auto-lab-skill (Module 1→4→5)                           │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │ report.md + recommendations.json                     │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  PHASE 3: Evidence-Graded Recommendations (NEW)               │                 │
│  │  evidence_grader.py                                           │                 │
│  │  ├─ Grade every claim: A(直接证据) B(间接) C(理论) D(推断)     │                 │
│  │  ├─ Score feasibility: equipment×complexity×time×cost         │                 │
│  │  ├─ Generate literature anchors for every claim               │                 │
│  │  └─ Output: SINGLE most feasible, evidence-backed plan        │                 │
│  └──────────────────────────┬───────────────────────────────────┘                 │
│                             │                                                     │
│                             ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────┐                 │
│  │  INTEGRATED OUTPUTS                                           │                 │
│  │  - bridge_manifest.json (complete execution trace)            │                 │
│  │  - verified_gaps.json (verified research gaps with scores)    │                 │
│  │  - evidence_graded_recommendations.json (graded plans)        │                 │
│  │  - lab_report.md (analysis report)                            │                 │
│  │  - TOP_PLAN.md (single most feasible plan, ready to execute)  │                 │
│  └──────────────────────────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────────────────────┘
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
Step 0.5: PHASE 0 — Multi-Round Literature Search (NEW)
    │  Round 1: Core domain keywords → broad coverage
    │  Round 2: Synonym/related terms → expanded coverage
    │  Round 3: Mechanism-specific keywords → deep dive
    │  Round 4: Quality filter → deduplicate, rank by relevance
    │
    ▼
Step 1: PHASE 1 — Literature Extraction & Normalization
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
Step 2.5: PHASE 1.5 — Gap Verification (NEW)
    │  gap_verifier.py
    │  ├── Cross-reference each gap against all extracted papers
    │  ├── Score novelty (0-10), evidence grade (A-E)
    │  ├── Build targeted search queries for each gap
    │  └── Reject false gaps, keep verified ones
    │
    ▼
Step 3: DATA TRANSFORMER — Schema Mapping
    │  transform_literature_to_lab.py
    │  文献 experiment_record → 化学 lab experiment_record
    │
    ▼
Step 4: PHASE 2 — Lab Analysis & Report
    │  (chem-auto-lab-skill)
    │  Modules 1→4→5 (+ Module 2 if spectral data present)
    │
    ▼
Step 5: PHASE 3 — Evidence-Graded Recommendations (NEW)
    │  evidence_grader.py
    │  ├── Grade every claim: A(直接) B(间接) C(理论) D(推断)
    │  ├── Score feasibility: equipment × complexity × time × cost
    │  ├── Generate literature anchors for every claim
    │  └── Output single most feasible evidence-backed plan
    │
    ▼
Step 6: INTEGRATED OUTPUT — Merge & Present
       bridge_manifest.json + verified_gaps.json + TOP_PLAN.md
```

## Phase 0: Multi-Round Literature Search (NEW)

Before running Phase 1 extraction, execute **3-4 rounds of iterative literature search** to maximize coverage and minimize the risk of missing key papers.

### Round Strategy

| Round | Purpose | Query Type | Expected Results |
|-------|---------|-----------|:---:|
| **R1: Core** | Domain + primary keywords | "{material} {property} {condition}" | 8-15 papers |
| **R2: Expanded** | Synonyms, related terms, broader scope | "{material} {synonym} {related_property}" | 10-20 papers |
| **R3: Deep Dive** | Specific mechanisms, degradation pathways | "{mechanism} {material} {condition}" | 8-15 papers |
| **R4: Quality** | Filter by impact, citations, recency | Same as R1-R3 with quality filters | 10-15 papers |

### Round Construction Algorithm

```python
def build_multi_round_queries(user_input: str, domain: str) -> dict:
    # Round 1: Core — extract primary keywords from user input
    core_keywords = extract_keywords(user_input)
    r1 = f"{core_keywords['material']} {core_keywords['property']} {core_keywords['condition']}"

    # Round 2: Expanded — synonyms and related terms
    synonyms = get_synonyms(core_keywords['material'])
    r2 = f"({' OR '.join(synonyms)}) {core_keywords['property']}"

    # Round 3: Deep Dive — mechanism-specific
    mechanisms = infer_mechanisms(domain, core_keywords)
    r3 = f"{core_keywords['material']} {mechanisms[0]} {core_keywords['condition']}"

    # Round 4: Quality — cited by / recent / high impact
    r4 = f"{core_keywords['material']} review {core_keywords['property']}"

    return {
        "round_1_core": r1,
        "round_2_expanded": r2,
        "round_3_deep_dive": r3,
        "round_4_quality": r4
    }
```

### Deduplication & Merge

After all rounds, deduplicate papers by title/DOI and merge into a single corpus. Papers appearing in multiple rounds get higher relevance scores.

### Output

- `phase0_output/search_rounds.json` — Query strategy and per-round results
- `phase0_output/merged_corpus.json` — Deduplicated paper list for Phase 1 input

---

## Phase 1: Literature Extraction & Normalization

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

If gate passes, proceed to Phase 1.5 automatically. If gate fails, present results to user and ask for direction.

---

## Phase 1.5: Gap Verification (NEW)

After quality gate passes, run `gap_verifier.py` to verify each identified research gap against the actual literature data.

### Purpose

Research gaps identified in `literature_summary.json` may be:
- **True gaps** — genuinely under-studied with high research value
- **False gaps** — actually well-studied, but missed by the initial search
- **Low-value gaps** — real but not worth investigating (no practical impact)

Phase 1.5 verifies each gap by cross-referencing against all extracted papers and scoring on novelty, evidence, and research value.

### Execution

```bash
python "$BRIDGE_SKILL/scripts/gap_verifier.py" \
  --gaps "$RUN_DIR/phase1_output/07_summary/literature_summary.json" \
  --experiments "$RUN_DIR/phase1_output/03_normalized/experiments_normalized.json" \
  --papers "$RUN_DIR/phase1_output/01_literature/source_manifest.json" \
  --domain "$DOMAIN" \
  --output "$RUN_DIR/phase1.5_output/verified_gaps.json"
```

### Scoring System

| Metric | Range | Meaning |
|--------|:-----:|---------|
| **novelty_score** | 0-10 | 0=well-studied, 10=completely unexplored |
| **evidence_grade** | A-E | A=direct papers confirm gap exists, E=multiple papers fully address it |
| **research_value.composite** | 0-10 | Weighted: scientific(40%) + industrial(30%) + feasibility(30%) |

### Gap Classification

| Verdict | Criteria | Action |
|---------|----------|--------|
| **high** | novelty≥7, composite≥7 | Proceed to Phase 3 recommendation |
| **medium** | novelty≥5, composite≥5 | Include in Phase 3 with lower priority |
| **low** | novelty≥3 | Document but deprioritize |
| **rejected** | novelty<3 or evidence_grade=E | Gap is closed — exclude from recommendations |

### Output

- `verified_gaps.json` — Each gap with novelty score, evidence grade, research value, and priority classification

---

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

---

## Phase 3: Evidence-Graded Recommendations (NEW)

Phase 3 is the **anti-fabrication guarantee** layer. It takes the verified gaps from Phase 1.5 and the lab analysis from Phase 2, then produces a single, highest-feasibility research plan where every claim is anchored to specific literature evidence.

### Execution

```bash
python "$BRIDGE_SKILL/scripts/evidence_grader.py" \
  --verified-gaps "$RUN_DIR/phase1.5_output/verified_gaps.json" \
  --experiments "$RUN_DIR/phase1_output/03_normalized/experiments_normalized.json" \
  --literature-summary "$RUN_DIR/phase1_output/07_summary/literature_summary.json" \
  --output "$RUN_DIR/phase3_output/evidence_graded_recommendations.json" \
  --max-recommendations 3
```

### Evidence Grading System

| Grade | Definition | Source Requirement |
|:-----:|-----------|-------------------|
| **A** | Direct experimental evidence | ≥3 papers with consistent data |
| **B** | Strong indirect evidence | ≥1 paper with related data |
| **C** | Weak indirect / theoretical | Well-established mechanism, no direct data |
| **D** | Inference only | Chemical intuition, adjacent systems |
| **F** | Pure speculation | **EXCLUDED** from final output |

**Anti-fabrication rule**: Any claim graded D is flagged with `⚠️ 推断 — 无文献直接支持`. Claims graded F are never included.

### Feasibility Scoring

| Factor | Weight | Levels |
|--------|:------:|--------|
| **Equipment** | 25% | standard(9) / specialized(6) / advanced(3) / custom(1) |
| **Complexity** | 25% | simple(9) / moderate(6) / complex(3) / very_complex(1) |
| **Time** | 25% | fast(9) / moderate(6) / long(3) / very_long(1) |
| **Cost** | 25% | low(9) / moderate(6) / high(3) / very_high(1) |

### Output: TOP_PLAN.md

The final output is a single Markdown document — **TOP_PLAN.md** — containing:

1. **Executive Summary** — One-paragraph summary of the recommended plan
2. **Literature Evidence** — Every claim with its evidence grade and source citation
3. **Experimental Protocol** — Materials, equipment, step-by-step procedure
4. **Expected Results** — What to expect, with confidence intervals
5. **Risk Assessment** — What could go wrong and mitigation strategies
6. **Evidence Anchors** — Table mapping each claim to its literature source

### Why Only One Plan?

Previous versions generated 3-5 recommendations. The optimization narrows to **one** plan because:
- The single best plan is what a researcher needs to start working
- Multiple plans dilute focus and create decision paralysis
- The one plan is selected by: `max(evidence_grade_score × feasibility_score × novelty_score)`

---

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
├── phase0_output/                    # (NEW) Multi-round search results
│   ├── search_rounds.json
│   └── merged_corpus.json
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
├── phase1.5_output/                  # (NEW) Gap verification results
│   └── verified_gaps.json
├── phase2_input/                     # Transformed data
│   └── lab_experiments.json
├── phase2_output/                    # Lab analysis outputs
│   ├── 01_cleaned/
│   │   └── merged_experiments.json
│   ├── 02_spectra/                   # (if spectral data)
│   ├── figures/
│   ├── report.md
│   └── recommendations.json
├── phase3_output/                    # (NEW) Evidence-graded recommendations
│   ├── evidence_graded_recommendations.json
│   └── TOP_PLAN.md                   # ⭐ Single most feasible plan
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
2. **Multi-domain support** — Pre-built vocabulary for battery materials, catalysts, drug formulations
3. **Confidence-weighted analysis** — Phase 2 report generation weights results by Phase 1 confidence scores
4. **External API integration** — Direct Semantic Scholar / PubMed / Crossref API for Phase 0 search
5. **Auto-search refinement** — Phase 1.5 gap verification automatically triggers new Phase 0 search rounds

### v2.0 Optimizations (Implemented)

| Feature | Status | Description |
|---------|:------:|-------------|
| **Phase 0: Multi-Round Search** | ✅ | 3-4 rounds of iterative literature search with increasing specificity |
| **Phase 1.5: Gap Verification** | ✅ | Cross-reference gaps against literature, score novelty, reject false gaps |
| **Phase 3: Evidence Grading** | ✅ | Grade every claim (A/B/C/D), feasibility scoring, TOP_PLAN.md output |
| **Anti-Fabrication** | ✅ | No claim included without evidence anchor; F-grade claims excluded |
| **Single Best Plan** | ✅ | One recommendation instead of multiple, selected by evidence×feasibility×novelty |