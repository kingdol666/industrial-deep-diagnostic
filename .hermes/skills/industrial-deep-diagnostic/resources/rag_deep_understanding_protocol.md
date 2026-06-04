# RAG Knowledge Deep Understanding Protocol

> **Reference file for SKILL.md §RAG Deep Understanding.** Load this when the context-builder agent (Step 2) needs the full R1-R4 protocol for deep knowledge comprehension, or when the diagnostician (Step 4) needs to understand how RAG knowledge was validated.

## RAG Knowledge Deep Understanding Protocol (R1-R4)

> **This is the foundation for universal diagnosis.** RAG knowledge is not a lookup table — it's a knowledge transfer that must be deeply understood before application.

### Step R1: Semantic Comprehension (NOT mechanical mapping)

When the `rag-knowledge-builder` skill returns structured knowledge, do NOT blindly copy fields. Instead:

1. **Understand the physics principles**: For each causal relationship in the RAG output, articulate the underlying physical mechanism in your own terms. What conservation law does it obey? What is the governing equation? What are the boundary conditions?

2. **Understand the domain constraints**: What assumptions does the RAG knowledge make? (steady-state? ideal gas? Newtonian fluid? linear elasticity?) Are these assumptions valid for THIS data?

3. **Understand the failure modes**: What are the known degradation mechanisms in this domain? What are their characteristic time scales? What are their tell-tale statistical signatures?

4. **Understand the confounders**: What variables typically co-vary in this domain? What operational changes (grade switches, maintenance, ambient conditions) affect multiple parameters simultaneously?

### Step R2: Knowledge-Data Alignment Validation

For every RAG-sourced claim, cross-validate against the ACTUAL data:

| RAG Claim | Data Validation | Action if Mismatch |
|-----------|----------------|---------------------|
| "Parameter A causes quality defect B" | Does A change BEFORE B in the data? Is the correlation direction consistent with the claimed mechanism? | If temporal order contradicts → downgrade RAG claim confidence |
| "Normal range for X is [a, b]" | Are the actual data values within [a, b]? | If significantly outside → the process may be operating in an abnormal regime, or the RAG knowledge may be for a different process variant |
| "The governing law is Y = f(X)" | Does the data show the functional form predicted by the governing law? | If not → either the law doesn't apply (wrong domain), the data is confounded, or the measurement is of a different physical quantity |
| "Degradation mechanism Z has time constant τ" | Does the observed degradation rate in the data match τ? | If orders of magnitude off → the degradation mechanism is different from what RAG suggests |

### Step R3: Physics Principle Extraction

From the RAG knowledge, extract REUSABLE physics principles that apply regardless of specific parameter names:

- **Conservation laws**: mass, energy, momentum — what must be conserved in this process?
- **Constitutive relations**: stress-strain, viscosity-shear rate, reaction rate-temperature — what material/process behaviors are governed by equations?
- **Scaling laws**: how do quantities scale with size, speed, temperature?
- **Threshold physics**: at what values do qualitative changes occur (phase transitions, yield points, resonance)?

These extracted principles become the basis for physics-based reasoning about ANY parameter, even those not explicitly mentioned in the RAG knowledge.

### Step R4: Gap-Aware Knowledge Integration

Identify what the RAG knowledge does NOT cover:

1. **Parameter-level gaps**: Which data columns have NO corresponding RAG concept? → These need first-principles physics inference
2. **Mechanism-level gaps**: Which statistical relationships have NO RAG causal explanation? → These are research questions
3. **Domain-level gaps**: Is the RAG knowledge from a sufficiently similar process? → If not, mark as ANALOGY (reduced confidence)
