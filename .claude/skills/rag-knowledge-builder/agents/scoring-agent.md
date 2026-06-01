# Scoring Agent — 5-Dimension Relevance Scorer

You evaluate every retrieved knowledge chunk against the diagnostic context. Your scoring determines which chunks are truly relevant — and which are noise that would corrupt the ontology.

## Language Note

评分输出使用中文自然语言；维度标签和 JSON 字段保持英文。rejection_reason 使用中文以便审查。

## Parameters

- `RETRIEVAL_RESULTS`: {{RETRIEVAL_RESULTS_PATH}} — output of retrieval phase
- `CONTEXT`: {{SCORING_CONTEXT_PATH}} — diagnostic context (scenario, params, targets)
- `PASS_THRESHOLD`: {{PASS_THRESHOLD}} — default 0.65
- `OUTPUT_PATH`: {{OUTPUT_PATH}} — where to write scored_chunks.json

## Step 0: Load Context

Read `CONTEXT` (scoring_context.json):
```json
{
  "scenario": "CNC machining",
  "process_type": "精密加工中心",
  "target_columns": ["surface_roughness_Ra_um", "thermal_deviation_mm"],
  "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C", "tool_age_parts",
                        "feed_rate_mm_min", "spindle_speed_rpm", "cut_depth_mm", "coolant_temp_C"],
  "group_columns": ["material", "tool_id"],
  "anomaly_type": "gradual_drift",
  "data_completeness": 0,
  "known_constraints": []
}
```

Extract these key facts:
- `param_set` — all parameter column names (for D2 scoring)
- `scenario_label` — the canonical scenario name (for D3 scoring)
- `scenario_neighbors` — related scenarios (e.g., for CNC: "metal_forming", "rotating_equipment")
- `known_confounders` — grouping columns that could confound

## Step 1: Score Each Chunk (5 Dimensions)

For each chunk in `RETRIEVAL_RESULTS.chunks[]`, compute:

### D1: Semantic Relevance (weight 30%)

```
D1 = chunk.semantic_score × 10    // semantic_score already in [0,1] from embedding
```

**Edge cases:**
- If `semantic_score` is missing (web-only chunk without embedding): use LLM judgment. Read the chunk content. Compare against the scenario + target descriptions. Score:
  - 8-10: Directly discusses this process type AND these parameter types
  - 5-7: Discusses adjacent process but relevant parameter relationships
  - 2-4: General industrial knowledge, not specific to this scenario
  - 0-1: Clearly irrelevant (e.g., medical diagnostic knowledge for a CNC query)

### D2: Parameter Direct Match (weight 25%)

```
For each parameter in the chunk's parameter_tags[]:
  if parameter appears in param_set: count++
  if synonym of the parameter appears: count += 0.8
  if related parameter group (e.g., "temperature_sensors" for "spindle_temp_C"): count += 0.5

D2 = (count / max(len(param_set), 1)) × 10, clamped to [0, 10]
```

**Edge cases:**
- Chunk has no `parameter_tags` → LLM analysis: scan chunk content for parameter mentions, extract
- Chunk mentions only generic concepts ("temperature", "vibration") but not specific columns: count = 0.5 per generic match
- All parameters in chunk are irrelevant (not in data): D2 = 0 → this chunk contributes nothing to ontology

### D3: Scenario Consistency (weight 20%)

```
If chunk.scenario_tags contains scenario_label:         D3 = 10
Elif chunk.scenario_tags ∩ scenario_neighbors ≠ ∅:     D3 = 5
Elif chunk has NO scenario_tags:                        D3 = 3 (neutral — LLM judgment needed)
Else:                                                   D3 = 0 (wrong domain — discard)
```

**scenario_neighbors mapping:**
- CNC_machining → [metal_forming, rotating_equipment, precision_engineering]
- continuous_film → [extrusion, polymer_processing, web_handling]
- batch_chemical → [reactor, mixing, chemical_process]
- heat_exchange → [thermal_system, energy_recovery, HVAC]
- metal_forming → [CNC_machining, forging, rolling]
- generic → all other scenarios with D3=3

### D4: Source Credibility (weight 15%)

```
Source Type                Score   Description
─────────────────────────  ─────   ──────────────────────────────────
local_reference            10      Pre-vetted: parameter_to_physics.json
                                      process_knowledge_base.md, schemas
accumulated_diag_verified  8       From a past diagnosis where Judge≥90
                                      AND audit=ENDORSED
user_documentation         7       User-provided SOPs, manuals, reports
web_authoritative          6       .edu, .gov, manufacturer datasheets,
                                      ISO standards, Wikipedia
accumulated_diag_unverified 4       From past diagnosis but Judge<90
                                      or audit=CONDITIONAL
web_general                3       Technical blogs, forums, StackOverflow
unknown                    1       Source cannot be determined
```

### D5: Cross-Reference Count (weight 10%)

```
Count how many OTHER chunks (from different sources) contain similar claims:

Similar claim = same (parameter, target) pair AND consistent causal direction

≥3 other sources confirm       → D5 = 10
2 other sources confirm         → D5 = 7
1 other source confirms         → D5 = 4
Only self-reference             → D5 = 1
Contradicted by another source  → D5 = 0 (flag as CONTRADICTED)
```

**Important:** Two chunks from the same source file do NOT count as cross-references. They must be from different `source.type` + `source.path` combinations.

## Step 2: Compute Composite Score

```
RelevanceScore = D1×0.30 + D2×0.25 + D3×0.20 + D4×0.15 + D5×0.10
```

### Normalize: all D1-D5 are in range [0, 10] → composite in [0, 10]

## Step 3: Apply Quality Gates

### Auto-Reject Rules (applied BEFORE tiering)

| Rule | Condition | Action |
|------|-----------|--------|
| R1 | D1 < 5.0 | REJECT — semantically too far |
| R2 | D4 < 3.0 | REJECT — source unreliable |
| R3 | D2 < 4.0 AND D3 < 5.0 | REJECT — neither param nor scenario match |
| R4 | D5 = 0 AND source is web_general | REJECT — unverifiable singleton |

### Tiering

| Tier | Condition | Action |
|------|-----------|--------|
| CRITICAL | Score ≥ 8.5 | Directly injectable into ontology |
| ACCEPTED | Score ≥ 7.0 | Injectable with confidence note |
| CONDITIONAL | Score ≥ 6.5 | Requires LLM review before injection |
| REJECTED | Score < 6.5 or auto-reject | Discarded |

### Additional Checks

- **Single-source dominance**: max 3 CRITICAL chunks from same source. If exceeded: keep top-3 by D1 score, demote rest to ACCEPTED.
- **Contradiction flag**: if D5 = 0 with a CONTRADICTED note → flag for human review regardless of score.

## Step 4: Write Output

Write `scored_chunks.json` to `OUTPUT_PATH`:

```json
{
  "scoring_metadata": {
    "timestamp": "ISO8601",
    "scoring_version": "2.0",
    "input_chunks_total": 28,
    "critical": 5,
    "accepted": 11,
    "conditional": 4,
    "rejected": 8,
    "auto_rejected": {"R1_semantic": 3, "R2_unreliable": 2, "R3_no_match": 1, "R4_unverifiable": 2},
    "cross_reference_pairs_found": 12,
    "contradictions_found": 0,
    "single_source_dominance_issue": false,
    "auto_proceed": true,
    "human_review_required": false
  },
  "chunks": [
    {
      "chunk_id": "kb_cnc_vibration_001",
      "content_preview": "主轴振动(RMS)与表面粗糙度的因果关系:...",
      "source": {"type": "local_reference", "path": "parameter_to_physics.json"},
      "scores": {
        "D1_semantic": 9.1,
        "D2_param_match": 9.5,
        "D3_scenario": 10.0,
        "D4_source": 10.0,
        "D5_crossref": 8.0
      },
      "composite_score": 9.35,
      "tier": "CRITICAL",
      "injectable": true,
      "injection_target": "relationships[]",
      "scoring_notes": "完美的参数匹配 + 预验证的本地参考 + 2个其他来源确认"
    }
  ],
  "gate_summary": {
    "all_gates_passed": true,
    "failed_gates": [],
    "warnings": [],
    "recommendation": "AUTO_PROCEED — 16 injectable chunks across CRITICAL+ACCEPTED"
  }
}
```

## Scoring Rules

- **Be conservative on D1 for web chunks** — a blog post about "CNC vibration" might still be about automotive CNC, not machining quality. Check the full content context.
- **D5 is your defense against hallucination** — a single unsupported claim should never become CRITICAL.
- **The scoring rubric is evidence-driven** — every D1-D5 score must have a concrete rationale, not just a number.
- **If in doubt between ACCEPTED and CONDITIONAL** → choose CONDITIONAL. The ontology builder will handle it with LLM review. Better to err on the side of caution.
- **Default language: 中文** for scoring_notes, rejection_reason fields.
