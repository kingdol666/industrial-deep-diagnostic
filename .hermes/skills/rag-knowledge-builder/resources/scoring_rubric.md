# Scoring Rubric — Detailed Examples & Edge Cases

> This file is the reference for examples and edge cases in `agents/scoring-agent.md`. Read it when scoring in Phase 2 runs into an uncertain case.

## D1: Semantic Relevance — Detailed Examples

| Scenario | Content excerpt | Score | Rationale |
|------|----------|:----:|------|
| CNC diagnosis, query "spindle vibration" | "Spindle bearing wear causes vibration increase... ISO 10816 Zone C >4.5mm/s" | **9.5** | Directly matches the query intent + quantitative threshold |
| CNC diagnosis, same query | "Rotating machinery vibration monitoring in power plants..." | **4.0** | Discusses rotating equipment but not CNC machining quality |
| CNC diagnosis, same query | "Heart rate variability monitoring using wearable sensors" | **0.5** | Irrelevant — medical domain |

## D2: Parameter Direct Match — Detailed Examples

**context params**: [spindle_vibration_mm_s, spindle_temp_C, surface_roughness_Ra_um]

| Parameter in the content | Match | Score |
|-------------|:---:|:----:|
| "spindle_vibration" (exact) + "surface roughness" (exact) | 2/3 exact match | **6.7** |
| "vibration" (generic) → matches "spindle_vibration" via token overlap | 1/3 partial match | **3.3** |
| "轴承温度" (bearing temperature, Chinese) + "粗糙度" (roughness, Chinese) | 2/3 semantic match | **5.0** |
| "oil viscosity" and "belt tension" | 0/3 match | **0.0** → **AUTO-REJECT** |

## D3: Scenario Consistency — Edge Cases

| Chunk tag | Current scenario | Score | Rationale |
|-----------|----------|:----:|------|
| "CNC_machining" | "CNC machining" | **10** | Exact match |
| "metal_forming" | "CNC machining" | **5** | Adjacent scenario — the bearing envelope of cold rolling shares the same physics as a CNC spindle |
| "batch_chemical" | "CNC machining" | **0** | Cross-domain — chemical reactor knowledge does not apply to CNC |
| no tag | "CNC machining" | **3** | Neutral — specificity cannot be judged |

## D4: Source Credibility — Evidence Level

| Source | Score | When to use |
|------|:----:|--------|
| `parameter_to_physics.json` | **10** | Pre-validated causal chains and quantitative formulas |
| `process_knowledge_base.md` | **10** | Distilled domain knowledge |
| Previous diagnostic run (Judge≥90 + ENDORSED) | **8** | A single data point — needs more verification before it can rise to 10 |
| User-provided SOP manual | **7** | Authoritative source from the user |
| Wikipedia / ISO standard / manufacturer datasheet | **6** | Publicly verifiable |
| Technical blog / StackOverflow | **3** | Unverified |
| Unidentifiable source | **1** | No information |

## D5: Cross-Reference Count — When a Confirming Link Is a Real Link

**Requirements for valid cross-validation:**
- References the same (parameter→target) pair → 1 confirmation
- References a causal chain in the **same direction** as the first source (not reversed) → 1 confirmation
- Comes **from a different source file/URL** → counted as independent
- **Not a confirmation:** another chunk in the same document with similar content — that is redundancy, not cross-validation

## Composite Score Reference Examples

| D1 | D2 | D3 | D4 | D5 | Composite | Tier | Reason |
|:--:|:--:|:--:|:--:|:--:|:---------:|------|------|
| 9.5 | 9.5 | 10 | 10 | 8 | **9.35** | CRITICAL | The ideal knowledge chunk |
| 8.0 | 7.0 | 10 | 10 | 5 | **8.25** | ACCEPTED | All good, but no cross-validation |
| 6.0 | 8.0 | 5 | 3 | 2 | **5.65** | REJECTED | D4 too low — singleton from a web_general source |
| 9.0 | 9.0 | 0 | 10 | 8 | — | REJECTED | D3=0 (AUTO-REJECT R3): CNC knowledge applied to a chemical scenario |
