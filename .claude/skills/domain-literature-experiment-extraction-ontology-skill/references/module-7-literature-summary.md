# Module 7: Literature Summary

> **Load this file when Module 7 is invoked.**
> Purpose: Synthesize findings across all collected papers — identify main themes, common patterns, performance trends, gaps, and promising future directions.

## Summary Structure

Generate a structured literature summary with seven sections:

```
1. Overview (scope + statistics)
2. Main Research Themes
3. Common Experimental Patterns
4. Performance Trends
5. Frequently Used Materials & Conditions
6. Unresolved Gaps & Contradictions
7. Promising Directions
```

## Section 1: Overview

Synthesize the high-level picture:

```json
{
  "overview": {
    "papers_analyzed": 15,
    "year_range": "2018-2025",
    "total_experiments": 342,
    "unique_materials": 12,
    "unique_additives": 18,
    "unique_measurement_types": 8,
    "journals_represented": ["Carbohydrate Polymers", "Polymer", "ACS Applied Materials & Interfaces", "..."],
    "geographic_distribution": {"China": 8, "South Korea": 3, "USA": 2, "Japan": 1, "Germany": 1},
    "summary_text": "The collected literature on PVA/BOPET optical films (2018-2025) spans 15 papers with 342 experimental records. Research is predominantly from East Asian institutions, reflecting the regional concentration of display manufacturing. The dominant research theme is nanofiller reinforcement of PVA films for simultaneous optical and mechanical improvement."
  }
}
```

## Section 2: Main Research Themes

Cluster papers by research question. Identify 3-5 major themes:

```json
{
  "themes": [
    {
      "theme": "Nanocellulose reinforcement of PVA films",
      "papers": ["SRC_001", "SRC_005", "SRC_008", "SRC_012"],
      "paper_count": 4,
      "experiment_count": 89,
      "core_question": "Can cellulose nanocrystals/nanofibers improve PVA film mechanical properties without compromising optical transparency?",
      "consensus": "Yes, at loadings ≤5-7 wt%. Beyond this, CNC aggregation causes haze increase and strength plateau.",
      "key_finding": "Optimal CNC loading is 3-5 wt%, achieving tensile strength improvements of 30-50% with transmittance >88%",
      "unresolved": "Dispersion quality depends strongly on processing method — no standardized dispersion protocol exists across papers"
    },
    {
      "theme": "Crosslinking strategies for barrier property enhancement",
      "papers": ["SRC_003", "SRC_009", "SRC_014"],
      "paper_count": 3,
      "experiment_count": 56,
      "core_question": "Which crosslinkers most effectively reduce WVTR/OTR in PVA films without embrittlement?",
      "consensus": "Boric acid crosslinking reduces WVTR by 40-60% but increases brittleness. Citric acid provides a better balance but requires thermal curing ≥120°C.",
      "key_finding": "Citric acid + thermal curing (140°C, 30 min) achieves WVTR reduction of 45% with <10% loss in elongation",
      "unresolved": "Long-term crosslinking stability under humid conditions is not studied"
    }
  ]
}
```

### Theme Detection Strategy

Cluster papers using these signals:
1. **Same additive family**: Papers studying CNC, CNF, or bacterial cellulose → "Nanocellulose reinforcement"
2. **Same property focus**: Papers emphasizing WVTR/OTR → "Barrier property enhancement"
3. **Same processing approach**: Papers using crosslinking → "Crosslinking strategies"
4. **Overlapping citations**: Papers that cite each other or share key references

If a paper doesn't fit any theme, create an "Individual Studies" category.

## Section 3: Common Experimental Patterns

Identify what experimental designs are most common:

```json
{
  "experimental_patterns": {
    "preparation_methods": [
      {"method": "Solution casting", "count": 185, "percentage": 54.1},
      {"method": "Melt extrusion", "count": 42, "percentage": 12.3},
      {"method": "Spin coating", "count": 28, "percentage": 8.2}
    ],
    "most_studied_properties": [
      {"property": "Tensile strength", "records": 210},
      {"property": "Light transmittance", "records": 195},
      {"property": "Elongation at break", "records": 188},
      {"property": "Haze", "records": 98},
      {"property": "WVTR", "records": 76}
    ],
    "typical_sample_size": "3-5 replicates per formulation (most papers)",
    "common_controls": "Pure PVA film as baseline (12/15 papers)",
    "common_concentration_ranges": {
      "CNC": "1-10 wt%",
      "glycerol": "20-40 wt%",
      "GO": "0.1-3 wt%"
    },
    "common_testing_standards": ["ASTM D882 (tensile)", "ASTM D1003 (haze/transmittance)", "ASTM E96 (WVTR)"]
  }
}
```

## Section 4: Performance Trends

Analyze how key properties vary across formulations. This is data-driven — compute from the normalized experiment data.

```json
{
  "performance_trends": [
    {
      "property": "Light transmittance at 550 nm",
      "unit": "%",
      "baseline_pure_pva": {"mean": 89.5, "std": 1.2, "n": 25},
      "best_performing_systems": [
        {"formulation": "PVA/CNC-5%", "mean_transmittance": 90.5, "papers": ["SRC_001", "SRC_005"]},
        {"formulation": "PVA/GO-0.5%", "mean_transmittance": 89.8, "papers": ["SRC_008"]}
      ],
      "worst_performing_systems": [
        {"formulation": "PVA/CNT-3%", "mean_transmittance": 65.2, "papers": ["SRC_014"]}
      ],
      "trend": "Nanofillers with refractive index close to PVA (n≈1.52) maintain transmittance better. High-aspect-ratio conductive fillers (CNT, rGO) cause severe transmittance loss at >1 wt%."
    },
    {
      "property": "Tensile strength",
      "unit": "MPa",
      "baseline_pure_pva": {"mean": 48.3, "std": 5.6, "n": 25},
      "best_performing_systems": [
        {"formulation": "PVA/GO-2%", "mean_strength": 82.1, "papers": ["SRC_008"]},
        {"formulation": "PVA/CNC-5%", "mean_strength": 65.3, "papers": ["SRC_001"]},
        {"formulation": "PVA/CNT-1%", "mean_strength": 72.5, "papers": ["SRC_014"]}
      ],
      "trend": "Graphene derivatives (GO, rGO) provide the highest absolute reinforcement. CNC provides the best strength-transparency balance."
    }
  ]
}
```

### Trend Analysis Rules

1. **Group by formulation**: Same material + additive + concentration range → compute mean and std across papers
2. **Compare to baseline**: Pure PVA values serve as the reference point
3. **Report N**: Always include the number of data points — small N trends are speculative
4. **Flag outliers**: If one paper reports dramatically different values, investigate and flag
5. **Cross-paper consistency**: Note when multiple papers agree vs when results diverge

## Section 5: Frequently Used Materials & Conditions

```json
{
  "common_materials": {
    "polymers": [
      {"name": "PVA 1799", "count": 210, "reason": "High hydrolysis degree → better mechanical properties, standard for optical films"},
      {"name": "PVA 1788", "count": 45, "reason": "Partial hydrolysis → better solubility, used for solution processing"},
      {"name": "PET (optical grade)", "count": 30, "reason": "BOPET substrate for display applications"}
    ],
    "top_additives": [
      {"name": "CNC", "count": 89, "typical_loading": "1-7 wt%"},
      {"name": "Glycerol", "count": 120, "typical_loading": "20-40 wt%"},
      {"name": "GO", "count": 35, "typical_loading": "0.1-3 wt%"}
    ],
    "top_solvents": [
      {"name": "Water", "count": 250, "note": "Dominant solvent for PVA solution casting"}
    ]
  },
  "common_conditions": {
    "drying_temperature": {"range": "25-60°C", "most_common": "40°C", "most_common_unit": "°C"},
    "drying_time": {"range": "6-48 h", "most_common": "24 h", "most_common_unit": "h"},
    "film_thickness": {"range": "20-200 μm", "most_common": "50-100 μm", "most_common_unit": "μm"}
  }
}
```

## Section 6: Unresolved Gaps & Contradictions

Identify what the collected literature does NOT address:

```json
{
  "gaps": [
    {
      "gap": "Long-term stability data",
      "severity": "critical",
      "description": "All 15 papers report properties measured immediately or within days of film preparation. No paper studies property evolution over weeks/months under storage conditions. For commercial applications, 6-12 month stability data is essential.",
      "papers_with_partial_data": [],
      "suggested_experiment": "Accelerated aging at 40°C/75%RH for 30 days, measuring properties at 7-day intervals"
    },
    {
      "gap": "Scale-up from lab casting to continuous production",
      "severity": "high",
      "description": "14/15 papers use lab-scale solution casting (petri dish or glass plate). Only one paper uses pilot-scale tape casting. Relationships between lab-scale and production-scale properties are unknown.",
      "papers_with_partial_data": ["SRC_011"],
      "suggested_experiment": "Compare lab-cast vs continuously-cast films with identical formulations"
    },
    {
      "gap": "Humidity-dependent mechanical behavior",
      "severity": "medium",
      "description": "Only 3/15 papers report mechanical properties at controlled humidity. PVA is highly hygroscopic — tensile strength and modulus decrease significantly above 50%RH. Most papers test at ambient lab conditions without reporting RH.",
      "papers_with_partial_data": ["SRC_003", "SRC_007", "SRC_011"],
      "suggested_experiment": "Systematic mechanical testing at 0%, 30%, 50%, 75%, 90% RH"
    }
  ],
  "contradictions": [
    {
      "contradiction": "CNC loading beyond 5 wt% — improvement or decline?",
      "claim_1": {"paper": "SRC_001", "claim": "Tensile strength plateaus at 5-7 wt% CNC"},
      "claim_2": {"paper": "SRC_012", "claim": "Tensile strength continues to increase up to 10 wt% CNC"},
      "possible_explanation": "SRC_012 uses tunicate CNC (higher aspect ratio ~80 vs wood CNC ~20 in SRC_001). Higher aspect ratio enables better load transfer at higher loadings.",
      "resolution_status": "unresolved"
    }
  ]
}
```

## Section 7: Promising Directions

Based on the synthesis, identify what seems most promising for future work:

```json
{
  "promising_directions": [
    {
      "direction": "Hybrid nanofiller systems (CNC + GO)",
      "rationale": "No paper studied CNC+GO hybrid systems, despite CNC offering optical clarity and GO offering highest mechanical reinforcement. Combining both could achieve the best of both.",
      "supporting_evidence": "CNC-5% achieves 90.5% transmittance; GO-0.5% achieves 82 MPa tensile. Synergy potential is unexplored.",
      "risk": "CNC and GO may compete for hydrogen bonding sites on PVA chains; dispersion of two nanofillers is more challenging than one"
    },
    {
      "direction": "Bio-based crosslinkers for barrier applications",
      "rationale": "Citric acid shows promise but requires 140°C curing. Other bio-based polycarboxylic acids (malic, tartaric, succinic) are unexplored for PVA crosslinking at lower temperatures.",
      "supporting_evidence": "Citric acid crosslinking at 140°C reduces WVTR by 45% (SRC_009). Lower-temperature alternatives would enable heat-sensitive substrates.",
      "risk": "Lower reactivity of other organic acids may require catalysts or longer curing times"
    }
  ]
}
```

## Script Execution

```bash
python scripts/summarize_literature.py \
  --experiments 03_normalized/experiments_normalized.json \
  --provenance 04_provenance/provenance.json \
  --output 07_summary/literature_summary.json \
  --language zh
```

The script handles statistical aggregation, theme clustering, and trend computation. The LLM provides the narrative synthesis (theme descriptions, gap analysis, direction recommendations).

## Output Formats

### Structured JSON (literature_summary.json)

Complete structured data as shown above.

### Markdown Report (literature_summary.md)

Narrative format:

```markdown
# Literature Summary: PVA/BOPET Optical Films
## Generated: 2026-05-30 | Papers: 15 | Experiments: 342

## 1. Overview
...

## 2. Main Research Themes
### 2.1 Nanocellulose Reinforcement
...

## 3. Common Experimental Patterns
...

## 4. Performance Trends
### 4.1 Light Transmittance
...

## 5. Frequently Used Materials & Conditions
...

## 6. Unresolved Gaps & Contradictions
...

## 7. Promising Directions
...
```

## Edge Cases

| Scenario | Action |
|----------|--------|
| Only 1-2 papers in the collection | Generate all sections but note `limited_sample: true`. Trends are illustrative, not statistically meaningful. |
| Papers from vastly different sub-domains (no common themes) | Group by sub-domain. Report that no meta-themes exist across the collection. |
| No baseline (pure material) data exists | Cannot compute "improvement over baseline." State all values as absolute and note the missing baseline. |
| One paper dominates the data (>50% of records) | Flag `single_paper_dominance: true`. Trends may reflect one lab's methodology, not general consensus. |
| All papers report only one property type | Note `narrow_coverage: true`. The ontology and summary will be limited. |