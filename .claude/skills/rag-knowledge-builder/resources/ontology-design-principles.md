# Ontology Design Principles — Natural Language Ontology Quality Standard

> This document defines the design principles that a good ontology model must satisfy at the natural-language level.
> This is the core reference standard for the Phase 2 ontology-construction agent.
>
> **Language directive:** the examples below are shown in English for readability. The natural-language values actually written into the ontology must be produced in the configured output language — default **Chinese** (see the Language Default section of `SKILL.md`). Structured field names and enum values always remain in English.

---

## 1. Concept Precision

### Principle
Every concept has one — and only one — precise natural-language definition. The definition must be:
- **Unique:** within this ontology, no other concept carries the same meaning
- **Disambiguating:** states explicitly what the concept is *not*, so that it cannot be confused with similar concepts
- **Operational:** a domain expert can read the definition and decide whether any given instance belongs to the concept

### Anti-patterns
```
❌ "temperature" — too vague: which temperature? where? under what conditions?
❌ "reaction temperature, in degrees Celsius" — no physical meaning, merely a restatement of the name
❌ "spindle temperature" — does not say whether it is bearing temperature, motor winding temperature, or spindle surface temperature

✅ "Spindle front-bearing outer-race temperature (°C) — a key indicator of spindle bearing
   operating condition. Normal range 20-70°C; >80°C indicates lubrication failure or overload;
   >90°C requires an immediate shutdown. Distinct from motor winding temperature
   (winding_temp_C), which reflects motor heating rather than bearing condition."
```

```
✅ "HbA1c (glycated hemoglobin percentage, %) — an indicator of average blood glucose level
   over the past 2-3 months. Distinct from fasting glucose (fasting_glucose_mg_dl):
   HbA1c reflects a long-term trend rather than an instantaneous value.
   Normal <5.7%; 5.7-6.4% is prediabetes; ≥6.5% is the diagnostic threshold for diabetes.
   May be inaccurate in patients with anemia or hemoglobinopathy."
```

### Test Method
For every concept definition, ask three questions:
1. **Can a domain expert distinguish it from similar concepts?** If not → the definition is not precise enough
2. **Does the definition contain "etc.", "roughly", or "similar to"?** If so → disambiguation is insufficient
3. **After reading the definition, can you decide whether an instance belongs to the concept?** If not → the definition is too vague

---

## 2. Hierarchical Completeness

### Principle
Core concepts must have IS-A (classification) and PART-OF (composition) relations. The hierarchy must:
- **Cover the core concepts:** every important concept appears in at least one hierarchy chain
- **Avoid orphan nodes:** no concept floats entirely outside the hierarchy
- **Distinguish IS-A from PART-OF:** IS-A means "is a kind of", PART-OF means "is a part of"
- **Avoid excessive depth:** generally no more than 4 levels (root → child → grandchild → leaf); deeper hierarchies should be flattened

### IS-A Hierarchy (Taxonomy)
```
An IS-A hierarchy expresses the classification relations among concepts:

Industrial domain example:
  Physical quantity
  ├── Temperature quantity
  │   ├── Melt temperature (melt_temp_C)
  │   ├── Bearing temperature (bearing_temp_C)
  │   └── Ambient temperature (ambient_temp_C)
  ├── Vibration quantity
  │   ├── Bearing vibration velocity (bearing_vib_mm_s)
  │   └── Structural vibration acceleration (structure_vib_g)
  └── Flow rate
      ├── Cooling water flow (coolant_flow_L_min)
      └── Feed flow (feed_rate_L_min)

Medical domain example:
  Biomarker
  ├── Glycemic markers
  │   ├── Fasting glucose (fasting_glucose_mg_dl)
  │   ├── HbA1c (hba1c_pct)
  │   └── Postprandial glucose (postprandial_glucose_mg_dl)
  ├── Cardiovascular markers
  │   ├── Blood pressure (blood_pressure_mmhg)
  │   └── Heart rate (heart_rate_bpm)
  └── Renal-function markers
      ├── eGFR (egfr_ml_min)
      └── Creatinine (creatinine_mg_dl)
```

### PART-OF Hierarchy (Mereology)
```
A PART-OF hierarchy expresses composition relations:

Industrial domain example:
  CNC machining system
  ├── Spindle system
  │   ├── Spindle bearing
  │   ├── Spindle motor
  │   └── Cooling system
  ├── Feed system
  │   ├── X-axis drive
  │   ├── Y-axis drive
  │   └── Z-axis drive
  └── Tooling system
      ├── Tool holder
      └── Cutting insert

Medical domain example:
  Type 2 diabetes management
  ├── Glycemic monitoring
  │   ├── HbA1c testing
  │   ├── Fasting glucose testing
  │   └── Continuous glucose monitoring (CGM)
  ├── Pharmacotherapy
  │   ├── Metformin
  │   ├── SGLT2 inhibitors
  │   └── Insulin
  └── Lifestyle intervention
      ├── Dietary management
      └── Exercise prescription
```

### Anti-patterns
```
❌ All concepts flattened into a single list, with no hierarchical relations at all
❌ IS-A and PART-OF confused ("spindle IS-A CNC" is wrong; "spindle PART-OF CNC system" is right)
❌ Hierarchy too deep (5+ levels): industrial process → polymer processing → film stretching → biaxial stretching → MDO stretching → MDO temperature → zone T1 temperature
✅ Appropriately flattened: industrial process → film stretching → MDO temperature (with a description of each T1-T12 heating zone)
```

---

## 3. Relationship Semantic Richness

### Principle
Every relationship has not only a `from → to` direction, but also:
- **Relationship type:** a precise semantic type (not just "related_to")
- **Mechanism description:** 2-3 natural-language sentences explaining why this relationship exists
- **Directionality:** an explicit causal, temporal, or logical direction
- **Cardinality constraint:** one-to-one, one-to-many, many-to-many
- **Conditional constraint:** the conditions under which the relationship holds
- **Time lag:** the delay between cause and effect
- **Strength/confidence:** how certain this relationship is

### Relationship Type Taxonomy

| Type | Semantics | Natural-language pattern | Example |
|------|------|-------------|------|
| `causal` | Direct physical/biological causation | "X causes Y, because..." | "Bearing wear causes increased vibration, because..." |
| `correlative` | Statistical association (no evidence of causation) | "X is correlated with Y, in the direction..." | "BMI is positively correlated with HbA1c" |
| `physical` | Constrained by a physical law | "According to [law], X determines Y" | "According to the Arrhenius equation, temperature determines reaction rate" |
| `control` | Control loop | "X is the control variable for Y" | "The PID controller regulates cooling water flow to hold the temperature setpoint" |
| `temporal` | Temporal ordering/evolution | "X occurs before Y" | "A feed change precedes the outlet temperature change by about 5 minutes" |
| `compositional` | Composition | "X is a component of Y" | "The spindle bearing is a component of the spindle system" |
| `classificational` | Classification | "X is a kind of Y" | "HbA1c is a kind of glycemic biomarker" |
| `conditional` | Conditional dependency | "Under condition Z, X affects Y" | "Under high temperature (>85°C), an increased draw ratio raises haze" |
| `regulatory` | Regulatory/statutory | "A regulation/standard requires X to limit Y" | "ISO 10816 requires vibration velocity <4.5 mm/s" |
| `definitional` | Definitional | "X is defined as Y" | "Conversion rate is defined as (feed - output) / feed × 100%" |
| `statistical` | Statistical model | "A statistical model predicts X → Y" | "A logistic regression model predicts debt-to-income ratio → probability of default" |
| `precedential` | Precedent/reference | "Precedent X guides Y" | "Delaware case law guides the enforceability of indemnification clauses" |

### Anti-patterns
```
❌ "temperature → quality" — no mechanism, no direction, no conditions
❌ "spindle_vib → roughness (related)" — "related" is not a relationship type
❌ "HbA1c affects blood glucose" — the causal direction is reversed (blood glucose affects HbA1c)

✅ "melt_temp_C →(causal)→ melt_viscosity_Pa_s →(causal)→ draw_stability
     Mechanism: PET melt viscosity follows an Arrhenius-type temperature dependence.
          Rising temperature → falling viscosity → reduced melt strength → unstable drawing → thickness fluctuation.
          This chain holds within 270-290°C; below 270°C unmelted particles appear (a different mechanism).
     Time lag: about 30-60 s (melt residence time in the extruder)
     Conditions: holds only within the normal PET IV range (0.60-0.80 dL/g)"
```

---

## 4. Terminology Mapping

### Principle
Every core concept must have a terminology mapping table containing:
- **Canonical name:** the formal name used in the ontology
- **Synonyms:** names that are interchangeable within the same domain
- **Abbreviations:** the common abbreviated forms
- **Cross-language terms:** Chinese-English correspondences (or other languages)
- **Upstream/downstream aliases** (context-specific aliases): the different names that may be used at different stages or in different contexts

### Examples

```json
{
  "canonical_name": "HbA1c",
  "synonyms": ["glycated hemoglobin", "hemoglobin A1c", "A1C test"],
  "abbreviations": ["HbA1c", "A1C", "HBA1C"],
  "cross_language": {
    "zh": "糖化血红蛋白",
    "en": "glycated hemoglobin",
    "ja": "糖化ヘモグロビン"
  },
  "context_aliases": {
    "clinical_lab": "HbA1c%",
    "icd10": "R73.0 (abnormal glycated hemoglobin)",
    "data_column": "hba1c_pct"
  }
}
```

```json
{
  "canonical_name": "MDO stretching temperature",
  "synonyms": ["machine-direction stretching temperature", "MD stretching temperature", "machine direction orientation temperature"],
  "abbreviations": ["MDO_temp", "MDT"],
  "cross_language": {
    "zh": "MDO拉伸温度 / 纵拉温度",
    "en": "MDO stretching temperature / machine-direction orientation temperature"
  },
  "context_aliases": {
    "process_control": "MD_TH001~MD_TH012 (individual heating zones)",
    "quality_report": "machine-direction stretching setpoint temperature",
    "data_column": "mdo_temp_C"
  }
}
```

---

## 5. Axioms and Constraints

### Principle
The rules and constraints of a domain must be stated explicitly in natural language. Axioms include:
- **Physical constraints:** hard limits imposed by physical law
- **Operational constraints:** process windows and safety limits
- **Logical constraints:** logical entailments between concepts
- **Mutual-exclusion rules:** conditions that cannot both be true
- **Boundary conditions:** the conditions under which the model fails

### Natural-Language Axiom Format

```
AXIOM <id>: <natural-language statement>

Constraint type: hard | soft | heuristic
Applies to: <list of concepts>
Consequence of violation: <what happens if it is violated>
Source: <knowledge chunk reference>
```

### Examples

```
AXIOM temp_viscosity_01:
  "For every 10°C rise in PET melt temperature, viscosity falls by roughly 30-40% (within the 270-290°C range)"
  Constraint type: heuristic (Arrhenius approximation)
  Applies to: melt_temp_C, melt_viscosity_Pa_s
  Consequence of violation: if the temperature drops below 270°C the rule fails (unmelted particles are present)
  Source: kb_pet_physics_003

AXIOM diabetes_hba1c_01:
  "HbA1c ≥ 6.5% is diagnostic of diabetes; 5.7-6.4% is prediabetes; <5.7% is normal"
  Constraint type: hard (ADA diagnostic criteria)
  Applies to: hba1c_pct
  Consequence of violation: in patients with hemoglobinopathy or anemia, HbA1c may be inaccurate
  Source: kb_clinical_guideline_001

AXIOM legal_noncompete_01:
  "Non-compete clauses are generally unenforceable in California but enforceable in Delaware (if reasonable in scope)"
  Constraint type: hard (state law)
  Applies to: governing_law_state, non_compete_enforceability
  Consequence of violation: relying on an unenforceable non-compete clause may void the entire contract clause
  Source: kb_legal_precedent_007

AXIOM credit_fairness_01:
  "The model must not use protected attributes (race, sex, age group) as direct inputs to default prediction (ECOA compliance)"
  Constraint type: hard (federal regulation)
  Applies to: all related_concepts in credit scoring model
  Consequence of violation: regulatory penalties + litigation risk
  Source: kb_regulatory_ecoa_001
```

---

## 6. Instantiation Examples

### Principle
Every abstract concept must have at least one concrete instance, showing:
- **Typical value:** the expected value under normal operation / standard conditions
- **Abnormal-value example:** what a value looks like when it is abnormal
- **Instance context:** the scenario in which this value occurs
- **Inference path:** how domain knowledge is inferred from this value

### Examples

```
Concept: HbA1c (hba1c_pct)
Instantiation:
  Normal instance: { value: 5.2%, context: "45-year-old Asian woman, no history of diabetes, routine check-up" }
  Abnormal instance: { value: 8.1%, context: "55-year-old African-American man, type 2 diabetes
             diagnosed 3 years ago, inference: poor glycemic control, medication regimen may need adjustment" }
  Boundary instance: { value: 6.3%, context: "60-year-old white woman, obese (BMI=32),
             inference: prediabetes, lifestyle intervention required" }
```

```
Concept: spindle vibration velocity (spindle_vib_mm_s)
Instantiation:
  Normal instance: { value: 1.2 mm/s RMS, context: "new bearing, 8000 RPM, aluminum alloy machining" }
  Abnormal instance: { value: 5.8 mm/s RMS, context: "after 2000 hours of operation,
             inference: ISO 10816 Zone C (unsatisfactory), probable bearing wear,
             expected surface roughness Ra > 1.6 μm" }
  Marginal instance: { value: 4.3 mm/s RMS, context: "near the upper limit of Zone B,
             inference: planned maintenance required, quality not yet affected" }
```

---

## 7. Provenance

### Principle
Every claim in the ontology must be traceable to its source knowledge and annotated with a confidence level:
- **Source citation:** every concept, relationship, axiom, and entity cites a source chunk_id
- **Confidence:** KNOWN (direct evidence) / INFERRED (indirect evidence) / UNKNOWN (no evidence)
- **Reasoning record:** why this claim was derived from this knowledge chunk
- **Conflict flag:** if different sources give contradictory information, flag it explicitly

### Anti-patterns
```
❌ A concept definition with no knowledge_source at all
❌ Every concept's confidence is KNOWN (unrealistic)
❌ No record of the reasoning process ("normal HbA1c <5.7%" — from which guideline?)
❌ Conflicting information present but not flagged

✅ Every claim has a source chunk_id + confidence + 1-2 sentences of reasoning
✅ Conflicting information is flagged, with the reason for the choice stated
✅ UNKNOWN concepts are listed in clarification_needed.json
```

---

## Quality Self-Assessment Checklist

After completing the ontology construction, self-check every item below:

### A. Concept Precision
- [ ] Every concept has a unique, precise natural-language definition
- [ ] The definition includes a "what it is not" disambiguation statement
- [ ] A domain expert can decide instance membership from the definition

### B. Hierarchical Completeness
- [ ] Every core concept appears in at least one IS-A or PART-OF hierarchy chain
- [ ] IS-A and PART-OF are not confused
- [ ] No nesting deeper than 4 levels
- [ ] No completely orphaned nodes

### C. Relationship Semantic Richness
- [ ] Every relationship has a precise type (not "related_to")
- [ ] Every relationship has a 2-3 sentence mechanism description
- [ ] Causal direction, time lag, and conditional constraints are all annotated
- [ ] No circular causal chains

### D. Terminology Mapping
- [ ] Core concepts have a synonym list
- [ ] Abbreviations and cross-language terms are present
- [ ] The mapping between data column names and ontology concept names is recorded

### E. Axioms and Constraints
- [ ] At least 3 natural-language axioms
- [ ] Axioms are annotated with a constraint type (hard/soft/heuristic)
- [ ] Axioms are annotated with the consequence of violation
- [ ] Boundary conditions are recorded

### F. Instantiation Examples
- [ ] Core concepts have normal instances and abnormal instances
- [ ] Instances include context and an inference path

### G. Provenance
- [ ] Every claim has a source chunk_id
- [ ] Confidence (KNOWN/INFERRED/UNKNOWN) is annotated
- [ ] Conflicting information is flagged, with the reason for the choice stated
- [ ] UNKNOWN concepts are listed in clarification_needed

If any item fails, fix it before submitting.
