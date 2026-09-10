# Ontology Output Templates — Universal Natural Language Templates

> This file defines the template structure for ontology output. It applies to any knowledge domain.

> **Language directive:** The fenced blocks below are emitted-output templates: the ontology document rendered from them must be written in the configured output language — default **Chinese** (see the Language Default section of `SKILL.md`). Their English field values are structural placeholders only; YAML/JSON keys and enum values (`KNOWN`/`INFERRED`/`UNKNOWN`, and so on) always remain in English.

---

## Template A: Universal Domain (Generic Template)

Applies to any domain that no specialized template covers.

```yaml
template: universal
scene:
  name: "{domain_name}"
  domain_type: "{specific_domain_snake_case}"
  domain_summary: "2-3 sentence description (configured output language)"
  scope:
    included: ["scope covered by this ontology"]
    excluded: ["scope not covered"]
    boundary_conditions: ["conditions under which the model fails"]

concepts:
  target_concept_template:
    name: "canonical concept name"
    definition: "precise definition (configured output language): what it is, what it is not, validity conditions"
    definition_confidence: "KNOWN|INFERRED|UNKNOWN"
    concept_type: "measurement|outcome|..."
    unit: "SI or domain-specific unit"
    expected_value_range: "plausible range with an explanation"
    broader_concept: "parent concept (IS-A)"
    part_of_whole: "the whole it belongs to (PART-OF)"
    terminology:
      canonical_name: "canonical name"
      synonyms: []
      abbreviations: []
      cross_language: {}
      context_aliases: {}
    instantiation:
      normal: {value, context, inference}
      abnormal: {value, context, inference}

  related_concept_template:
    name: "concept name"
    definition: "..."
    concept_type: "predictor|input|control|mediator|..."
    # ...same structure as above

  context_dimension_template:
    name: "dimension name"
    definition: "what it stratifies"
    cardinality: "low|medium|high|continuous"
    typical_values: []

entity_template:
  id: "entity_id"
  name: "domain-specific entity name"
  type: "agent|component|organization|system|..."
  definition: "2-3 sentences (configured output language)"
  part_of: "parent entity"
  has_parts: []
  key_attributes: []
  role_in_domain: "description of its position"

relationship_template:
  id: "rel_NNN"
  from: "source concept"
  to: "target concept"
  type: "causal|correlative|physical|control|..."
  mechanism: "2-3 sentences (configured output language)"
  direction: "from↑→to↑ | from↑→to↓ | ..."
  conditions: ["preconditions"]
  exceptions: ["exceptional cases"]
  expected_lag: "time lag"
  knowledge_confidence: 0.0-1.0

constraint_template:
  id: "constraint_NNN"
  statement: "natural-language constraint statement"
  type: "hard|soft|heuristic"
  applicable_concepts: []
  violation_consequence: "consequence of violation"
  boundary_conditions: "conditions under which it fails"

confounder_template:
  name: "confounder name"
  type: "batch|category|..."
  reasoning: "2-3 sentences (configured output language)"
  confounded_relationships: []
  expected_impact: "high|medium|low"
```

---

## Template B: Industrial Process Control

Applies to: industrial domains such as manufacturing, processing, chemicals, and metallurgy.

### Additional concept type extensions

```yaml
concept_type_extensions:
  - "process_parameter"  # process parameter (adjustable)
  - "quality_indicator"  # quality indicator (target)
  - "equipment_state"    # equipment state (monitored)
  - "material_property"  # material property (intrinsic)
  - "environmental_factor" # environmental factor (uncontrollable)

relationship_type_extensions:
  - "physical"    # constrained by physical law
  - "control"     # control loop

constraint_type_examples:
  hard:
    - "Melt temperature >300°C causes thermal degradation of PET (irreversible)"
    - "Reactor pressure above the relief valve setpoint vents automatically"
  soft:
    - "MDO stretch temperature is recommended to stay within Tg+5~15°C"
    - "Bearing temperature >70°C suggests scheduling maintenance"
  heuristic:
    - "For every 10°C rise in temperature, viscosity drops by roughly 30-40% (Arrhenius approximation)"
    - "When vibration velocity exceeds 4.5 mm/s, surface roughness is very likely out of specification"
```

### Industrial-domain-specific fields

```yaml
industrial_extensions:
  process_stages:
    - id: "stage_id"
      name: "process stage name"
      order: 1
      function: "what this process stage does"
      key_equipment: ["entity_id"]
      key_parameters: ["concept_name"]
      input_material: "incoming material from upstream"
      output_material: "output passed downstream"

  degradation_mechanisms:
    - name: "degradation mechanism name"
      affected_entity: "entity_id"
      progression: "how the degradation develops over time / with conditions"
      early_warning_signals: ["concept_name"]
      intervention_options: ["possible interventions"]
```

---

## Template C: Clinical Medicine

Applies to: disease diagnosis, risk assessment, treatment plans, and similar.

### Additional concept type extensions

```yaml
concept_type_extensions:
  - "biomarker"        # biomarker
  - "clinical_outcome" # clinical outcome
  - "risk_factor"      # risk factor
  - "protective_factor" # protective factor
  - "medication"       # medication
  - "comorbidity"      # comorbidity

relationship_type_extensions:
  - "causal"      # biological / pathological causation
  - "statistical" # statistical model prediction

constraint_type_examples:
  hard:
    - "HbA1c ≥ 6.5% is diagnostic of diabetes (ADA criteria)"
    - "Metformin is contraindicated when eGFR <30 mL/min"
  soft:
    - "BMI >25 suggests glucose tolerance screening"
  heuristic:
    - "Each additional 10 years of age increases type 2 diabetes risk by roughly 1.5-fold"
```

### Medical-domain-specific fields

```yaml
clinical_extensions:
  diagnostic_criteria:
    - condition: "disease name"
      required_biomarkers: ["biomarker_name"]
      thresholds: {"biomarker": "threshold_value"}
      reference: "guideline source"

  treatment_pathways:
    - condition: "disease state"
      first_line: ["treatment option A"]
      second_line: ["treatment option B"]
      contraindications: ["contraindicated conditions"]
```

---

## Template D: Legal / Compliance

Applies to: contract review, compliance checks, regulatory analysis, and similar.

### Additional concept type extensions

```yaml
concept_type_extensions:
  - "legal_concept"     # legal concept
  - "contract_clause"   # contract clause
  - "obligation"        # obligation
  - "right"             # right
  - "liability"         # liability
  - "compliance_requirement" # compliance requirement

relationship_type_extensions:
  - "legal"        # legal causation
  - "precedential" # precedential relationship
  - "regulatory"   # regulatory relationship

constraint_type_examples:
  hard:
    - "Non-compete clauses are generally unenforceable in California"
    - "ECOA prohibits the use of race or sex as factors in credit decisions"
  soft:
    - "Indemnity caps are recommended not to exceed 200% of the total contract value"
```

---

## Template E: Finance / Risk

Applies to: credit scoring, market analysis, risk assessment, and similar.

### Additional concept type extensions

```yaml
concept_type_extensions:
  - "financial_metric"   # financial metric
  - "risk_score"         # risk score
  - "market_factor"      # market factor
  - "behavioral_signal"  # behavioral signal

relationship_type_extensions:
  - "statistical"  # statistical model relationship
  - "correlative"  # correlative relationship

constraint_type_examples:
  hard:
    - "The model must not use protected attributes as direct inputs to default prediction (ECOA compliance)"
    - "An LTV ratio >80% requires PMI insurance"
  heuristic:
    - "When the debt-to-income ratio exceeds 40%, default probability rises significantly"
```

---

## How to Use Templates (LLM Instructions)

1. **Do not apply the templates rigidly.** A template is a starting point, not an endpoint. Add or remove fields according to the characteristics of the domain.
2. **Keep the core structure complete first.** concepts, relationships, and constraints are mandatory. Extension fields depend on what the domain needs.
3. **Natural-language definitions always matter more than structured fields.** One good definition in the configured output language beats 10 empty fields.
4. **The constraint_type_examples in every template are references only.** You must extract constraints from the actual knowledge chunks, not copy the examples.
5. **If a domain spans templates (e.g., medicine + law), merge the fields of the relevant templates.**

**Anti-pattern:** Do not force-fill a field just because the template contains it. Leave fields with no supporting knowledge source empty or mark them UNKNOWN.
