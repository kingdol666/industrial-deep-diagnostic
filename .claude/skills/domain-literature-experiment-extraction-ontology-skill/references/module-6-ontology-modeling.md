# Module 6: Ontology Modeling

> **Load this file when Module 6 is invoked.**
> Purpose: Construct a domain ontology from extracted experiment data — defining classes, entities, relationships, and attributes that can be exported to OWL, RDF/Turtle, or JSON-LD for knowledge graph construction.

## Ontology Construction Principles

1. **Data-driven**: Classes and relationships emerge from the extracted data, not from a pre-defined template. If no paper mentions a concept, it should not appear in the ontology.
2. **Hierarchical**: Organize classes in a taxonomy (superclass → subclass). Flat lists of concepts are not ontologies.
3. **Relationship-rich**: Classes connected by typed relationships (not just "relatedTo"). Every relationship must have a domain, range, and definition.
4. **Downstream-compatible**: Output formats (JSON-LD, Turtle, OWL) must be parseable by standard semantic web tools (Protégé, RDFlib, Apache Jena, Neo4j import).
5. **Incremental**: The ontology can be extended when new papers are added without rebuilding from scratch.

## Core Class Hierarchy

Based on the PVA/BOPET domain, define this class structure:

```
Thing
├── Material
│   ├── Polymer
│   │   ├── PVA
│   │   ├── PET
│   │   ├── TAC
│   │   ├── PMMA
│   │   ├── COP
│   │   └── PC
│   └── Additive
│       ├── Plasticizer
│       │   ├── Glycerol
│       │   ├── EthyleneGlycol
│       │   ├── PEG
│       │   └── Sorbitol
│       ├── Crosslinker
│       │   ├── BoricAcid
│       │   ├── Glutaraldehyde
│       │   └── CitricAcid
│       └── Nanofiller
│           ├── CNC
│           ├── CNF
│           ├── GO
│           ├── rGO
│           ├── MMT
│           ├── CNT
│           ├── SiO2
│           ├── TiO2
│           └── ZnO
├── Solvent
│   ├── Water
│   ├── DMSO
│   ├── DMF
│   └── Ethanol
├── Process
│   ├── PreparationMethod
│   │   ├── SolutionCasting
│   │   ├── MeltExtrusion
│   │   └── SpinCoating
│   ├── Drying
│   ├── Stretching
│   │   ├── UniaxialStretching
│   │   └── BiaxialStretching
│   └── HeatTreatment
├── Instrument
│   ├── UVVisSpectrophotometer
│   ├── HazeMeter
│   ├── UniversalTestingMachine
│   ├── DSC
│   ├── TGA
│   ├── SEM
│   ├── AFM
│   ├── XRD
│   └── FTIR
├── Measurement
│   ├── OpticalProperty
│   │   ├── LightTransmittance
│   │   ├── Haze
│   │   └── Absorbance
│   ├── MechanicalProperty
│   │   ├── TensileStrength
│   │   ├── ElongationAtBreak
│   │   └── YoungsModulus
│   ├── BarrierProperty
│   │   ├── WVTR
│   │   └── OTR
│   ├── ThermalProperty
│   │   ├── Tg
│   │   ├── Tm
│   │   └── Td
│   └── SurfaceProperty
│       └── ContactAngle
├── Condition
│   ├── TemperatureCondition
│   ├── TimeCondition
│   ├── ConcentrationCondition
│   └── HumidityCondition
└── Source
    └── Paper
```

## Relationships

Define typed relationships between classes:

| Relationship | Domain | Range | Definition |
|-------------|--------|-------|------------|
| `hasAdditive` | Material (Polymer) | Additive | The polymer composite contains this additive |
| `hasPlasticizer` | Material (Polymer) | Plasticizer | The polymer is plasticized with this compound |
| `hasCrosslinker` | Material (Polymer) | Crosslinker | The polymer is crosslinked with this agent |
| `dissolvedIn` | Material | Solvent | The material is dissolved in this solvent |
| `preparedBy` | Material | PreparationMethod | The film/sample was prepared using this method |
| `processedUnder` | PreparationMethod | Condition | The process step operates under specific conditions |
| `driedAt` | Drying | TemperatureCondition | Drying temperature condition |
| `driedFor` | Drying | TimeCondition | Drying duration condition |
| `stretchedAt` | Stretching | TemperatureCondition | Stretching temperature condition |
| `stretchedBy` | Stretching | StretchingRatio | Stretching ratio applied |
| `measuredWith` | Measurement | Instrument | The property was measured using this instrument |
| `measuredUnder` | Measurement | Condition | The measurement was taken under these conditions |
| `hasProperty` | Material | Measurement | The material exhibits this measured property |
| `hasValue` | Measurement | NumericValue | The quantitative result |
| `hasUnit` | Measurement | Unit | The unit of measurement |
| `hasError` | Measurement | ErrorValue | The measurement uncertainty |
| `comparedTo` | Measurement | Measurement | This result is compared to a baseline |
| `reportedIn` | Measurement | Source | The result is reported in this paper |
| `authoredBy` | Source | Author | The paper was written by these authors |
| `publishedIn` | Source | Journal | The paper was published in this journal |
| `publishedYear` | Source | Year | The publication year |

## Entity Extraction

For each class in the hierarchy, extract instances from the experiment data:

### Step 1: Extract Entities

Scan `experiments_normalized.json` and extract unique instances:

- **Materials**: Every unique combination of material_system + material_grade
- **Additives**: Every unique additive name
- **Solvents**: Every unique solvent name
- **Instruments**: Every unique instrument name
- **Process methods**: Every unique film_preparation_method
- **Properties**: Every unique measured_property value
- **Conditions**: Every temperature, time, concentration tuple that appears

### Step 2: Assign URIs

Generate unique, stable URIs for each entity:

```
http://example.org/ontology/pva-bopet/Material/PVA_1799
http://example.org/ontology/pva-bopet/Additive/CNC
http://example.org/ontology/pva-bopet/Instrument/UVVisSpectrophotometer
http://example.org/ontology/pva-bopet/Measurement/LightTransmittance
```

### Step 3: Extract Relationships

From each experiment record, instantiate relationships:

Example from record SRC_001_E001:
```
PVA_1799 --hasAdditive--> CNC
PVA_1799 --hasPlasticizer--> Glycerol
PVA_1799 --dissolvedIn--> Water
PVA_1799 --preparedBy--> SolutionCasting
SolutionCasting --driedAt--> TemperatureCondition(40°C)
SolutionCasting --driedFor--> TimeCondition(24h)
LightTransmittance --measuredWith--> UVVisSpectrophotometer
LightTransmittance --hasValue--> 90.5
LightTransmittance --hasUnit--> Percent
PVA_1799 --hasProperty--> LightTransmittance
LightTransmittance --reportedIn--> SRC_001
```

### Step 4: Handle Conflicts

When two papers use different names for what appears to be the same entity:

```
Paper A: "cellulose nanocrystal"
Paper B: "CNC"
Paper C: "nanocrystalline cellulose"
```

→ All map to canonical entity `CNC` (based on Module 3 normalization). The ontology uses the canonical name. Original names are preserved as `rdfs:label` alternatives.

When two papers report contradictory relationships:
```
Paper A: CNT --increases--> TensileStrength
Paper B: CNT --decreases--> TensileStrength (due to poor dispersion)
```

→ Both relationships are recorded. The relationship gets additional context: `dispersion_quality`, `cnt_loading`. Flag as `ontology_conflict` in `ambiguities.json`.

## Ontology Output Formats

### Internal JSON (ontology.json)

The primary format for internal use and incremental updates:

```json
{
  "ontology_id": "pva_bopet_ontology_v1",
  "domain": "PVA/BOPET Optical Films",
  "generated": "2026-05-30",
  "classes": [
    {
      "id": "Material",
      "label": "Material",
      "parent": "Thing",
      "definition": "A substance used as the primary component or additive in film formation",
      "instances": ["PVA_1799", "PET", "CNC", "Glycerol"]
    }
  ],
  "object_properties": [
    {
      "id": "hasAdditive",
      "label": "has additive",
      "domain": "Material",
      "range": "Additive",
      "definition": "The composite material contains this additive component"
    }
  ],
  "data_properties": [
    {
      "id": "concentration",
      "label": "concentration",
      "domain": "Additive",
      "range": "xsd:float",
      "definition": "The concentration of the additive in the composite (wt%)"
    }
  ],
  "individuals": [
    {
      "id": "PVA_1799",
      "class": "PVA",
      "label": "PVA 1799",
      "attributes": {
        "hydrolysis_degree": 99,
        "molecular_weight": "high",
        "grade": "1799"
      }
    }
  ],
  "triples": [
    {"subject": "PVA_1799", "predicate": "hasAdditive", "object": "CNC"},
    {"subject": "CNC", "predicate": "concentration", "object": 5},
    {"subject": "CNC", "predicate": "reportedIn", "object": "SRC_001"}
  ],
  "conflicts": [
    {
      "type": "relationship_contradiction",
      "subject": "CNT",
      "predicate": "affects",
      "object": "TensileStrength",
      "source_1": {"paper": "SRC_005", "claim": "increases"},
      "source_2": {"paper": "SRC_012", "claim": "decreases"},
      "resolution_notes": "Both papers agree CNT dispersion quality is the determining factor"
    }
  ]
}
```

### RDF/Turtle Export (ontology.ttl)

Generated from the internal JSON:

```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix pva: <http://example.org/ontology/pva-bopet/> .

pva:PVA a owl:Class ;
    rdfs:label "PVA" ;
    rdfs:subClassOf pva:Polymer .

pva:PVA_1799 a pva:PVA ;
    rdfs:label "PVA 1799" ;
    pva:hydrolysisDegree "99"^^xsd:integer .

pva:hasAdditive a owl:ObjectProperty ;
    rdfs:domain pva:Material ;
    rdfs:range pva:Additive .
```

### OWL Export (ontology.owl)

Full OWL 2 DL ontology for import into Protégé or similar tools. Generated from internal JSON with proper OWL axioms.

## Script Execution

```bash
python scripts/build_ontology.py \
  --experiments 03_normalized/experiments_normalized.json \
  --provenance 04_provenance/provenance.json \
  --output 06_ontology/ontology.json \
  --format json,ttl,owl \
  --domain pva_bopet
```

The script handles:
- Entity extraction from experiment records
- URI generation
- Relationship instantiation
- Format conversion (JSON → Turtle, JSON → OWL)
- Conflict detection and logging

## Incremental Ontology Updates

When new papers are added:

1. Load existing `ontology.json`
2. Extract entities and relationships from new experiment records only
3. Merge new entities: if an entity already exists, enrich its attributes; if new, add it
4. Merge new relationships: avoid duplicates (same subject-predicate-object); add provenance for new ones
5. Re-run conflict detection on the merged ontology
6. Bump `ontology_version`

## Quality Checks

After generation, verify:

- Every class has at least one instance (no empty classes)
- Every relationship connects entities that exist in the ontology
- Every entity has the required attributes defined in its class
- No circular subclass relationships (A subClassOf B subClassOf A)
- All conflict flags in `ambiguities.json` are referenced in `ontology.json`

## Edge Cases

| Scenario | Action |
|----------|--------|
| Entity mentioned by name only, no attributes | Create entity with minimal attributes; flag `sparse_entity: true` |
| Same chemical with multiple valid names (IUPAC, common, trade) | Use canonical name as primary; add all alternatives as `rdfs:label` |
| Paper describes a novel material not in the vocabulary | Add to ontology as new class under Material; preserve paper's naming |
| Relationship is implied but not explicitly stated | Do NOT add to ontology. Only explicit, extractable relationships are included. Flag as `implied_relationship` in ambiguities for human review |
| Measurement type appears only once across all papers | Include it but flag `single_occurrence: true` — may not be a robust concept |