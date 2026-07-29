# Diagnostician — Execution Reference

Detailed commands, tables, and templates moved from agent-protocol.md. Read only when the checklist items need clarification.

---

## Phase 0: Detailed File Lists

### 0.1 CRITICAL Files (missing → error and stop)
- `02_processed/feature_summary.json`
- `02_processed/validate_report.json`
- `01_ontology/ontology.json`
- `03_figures/plot_manifest.json`
- `00_input/extracted_knowledge.json`
- `03_figures/image_captions.json`
- `03_figures/visual_analysis.json`

### 0.1 IMPORTANT Files (missing → note, continue)
- `02_processed/anomaly_report.json`
- `02_processed/data_analysis_conclusion.json` — Data Processor's expert handoff
- `02_processed/causal_evidence_map.json`
- `02_processed/scenario_classification.json`
- `02_processed/analysis_plan.md`
- `02_processed/zone_analysis.json`
- `02_processed/event_analysis.json`
- `02_processed/physics_manual_verification.md`
- `00_input/rag_deep_understanding.json`
- `00_input/clarification_needed.json`
- `$SKILL_PATH/resources/parameter_to_physics.json`

### 0.2 Evidence Artifacts — Full Table

| Artifact | What to Extract | Role |
|----------|----------------|------|
| `rag_deep_understanding.json` | Physics principles, validated/contradicted claims, domain constraints, confounders | Domain context |
| `parameter_to_physics.json` | PATTERNS for physics inference structure | Physics inference template |
| `extracted_knowledge.json` | Known fault patterns, causal relationships | External reference [Evidence Rank 2] |
| `clarification_needed.json` | Parameters with UNKNOWN physical meaning | Ambiguity guard |
| `scenario_classification.json` | Process characterization | Scenario context |
| `analysis_plan.md` | Data-processor's data shape detection | Analysis context |
| `analysis_parameter_selection.json` | Tier assignments, pruned pairs | Analysis boundary |
| `data_analysis_conclusion.json` | Baseline + custom analyses, priority hypothesis inputs | Expert data-analysis handoff |
| `zone_analysis.json` | Per-zone drift localization | Spatial root cause |
| `event_analysis.json` | Quality reset classifications | #1 diagnostic discriminator |
| `physics_manual_verification.md` | Manual L1-L5 derivations | First-principles physics bridge |
| `ontology.json` + `schema.json` | Parameter meanings, `behavior_match`, `governing_law`, `time_lag` | Process structure + proof foundation |
| `feature_summary.json` | Correlations, MI, Granger, interactions | Statistical data side |
| `time_lag_analysis.json` | Lag-compensated r, physics-vs-data comparison | Lag-aware causal timing |
| `production_regime_filter.json` | Steady/startup/shutdown labels, focus_product | Row-level data quality filter |
| `validate_report.json` | Simpson, trend, change points, sorting | Validity constraints |
| `anomaly_report.json` | `process_parameter_fluctuation`, `dual_drive_analysis` | Fused dual-drive evidence |
| `causal_evidence_map.json` | Validated edges, co-linear groups | Graph structure |
| `plot_manifest.json` + `image_captions.json` | `diagnostic_implication` per plot | Visual alignment |
| `visual_analysis.json` | VLM observations: sync groups, precedence, event response | PRIMARY visual evidence |

**Visual evidence hierarchy**: `visual_analysis.json` (primary, qualitative) > `image_captions.json` (fallback, numerical values). When they conflict, visual_analysis.json takes precedence for qualitative observations; image_captions.json for specific numbers.

### 0.3 Validation Report Constraints (Detailed)

1. **Sorting**: `time_sorted=false` → ALL lag claims invalid
2. **Simpson's Paradox**: Collapse within subgroups → BETWEEN_PRODUCT_ONLY
3. **Trend confounding**: `attenuation>50%` → time-drift, not coupling
4. **Outlier-driven**: Correlations vanish after outlier removal → OUTLIER_ARTIFACT
5. **Change points**: Regime shifts may invalidate cross-regime correlations

### 0.3A Data-Processor's Two Diagnostic Entries

1. **Pure process-side**: `anomaly_report.process_parameter_fluctuation` — which parameters show drift/high_variability/step_change/threshold_crossing?
2. **Integrated dual-drive**: `anomaly_report.dual_drive_analysis` — which product groups show simultaneous process + quality anomalies?

**Rule**: Do not merge these two views too early. Diagnose process abnormality first, then decide whether quality evidence upgrades it.

### 0.3B Expert Data Analysis Conclusion

Extract from `data_analysis_conclusion.json`:
- Fixed baseline script findings and limitations
- Custom script outputs
- Ontology/industry interpretation of patterns
- Data-supported conclusions with caveats
- Priority hypothesis inputs and evidence gaps

Use to prioritize — do NOT accept as final diagnosis.

### 0.3C Time-Lag Compensation

From `02_processed/time_lag_analysis.json`:

| Scenario | Action |
|----------|--------|
| Raw r < 0.2, compensated r > 0.4 | Major hidden relationship — upgrade causal priority |
| Raw r > 0.5, compensated r similar | Zero-lag adequate |
| Optimal lag found but consistency < 0.5 | Isolated spike — do not use |
| Physics says lag=1-3h, data says 10min | Physics/data mismatch — investigate |
| Ontology lag="unknown", CCF finds consistent lag | Data-driven discovery — enrich ontology |

### 0.4 Ontology Discrepancy Signals

| behavior_match | Meaning | Diagnostic Action |
|---------------|---------|-------------------|
| CONTRADICTED | Data contradicts physics | Highest priority — investigate mismatch |
| CONSISTENT | Data matches physics | Normal baseline |
| UNVERIFIED | Could not verify | Derive from first principles |

### 0.4a Clarification Needed — UNKNOWN Parameters Gate

1. `physical_meaning_confidence=UNKNOWN` → confidence ceiling 50 for hypotheses using that parameter as primary predictor; `[PARAM_AMBIGUITY]` required
2. Unresolved RAG unknowns → cannot be used in DETERMINED; only COMPETING_SET or NEEDS_DATA
3. Judge will check for over-claiming violations

### 0.5 Parameter→Physics Mapping (Pattern Library)

`parameter_to_physics.json` is a PATTERN LIBRARY, not a lookup table. Study its structure:
- Causal chain: mechanism → check_function → time_lag
- Quantitative checks: equation + expected range
- Competing hypotheses: H1 vs H2 vs H3 with observables
- Threshold physics: critical values with justification

### 0.6 RAG Deep Understanding

From `rag_deep_understanding.json`:
- Extracted physics principles (conservation laws, constitutive relations, scaling laws, thresholds)
- Validated/contradicted RAG claims
- Domain constraints, known failure modes, key confounders

---

## Phase 1: Physics Inference Ladder — Full Detail

### Level 1: Physical Quantity Identification

| Clue Source | Examples | Inference |
|-------------|----------|------------|
| Column name prefix | TH*, temp*, T_* | Temperature |
| Column name prefix | PS*, PR*, press* | Pressure |
| Column name prefix | FR*, FL*, flow* | Flow rate |
| Column name prefix | SP*, RPM*, speed* | Rotational/linear speed |
| Column name prefix | VIB*, ACC*, VEL* | Vibration |
| Column name prefix | PW*, POW*, kW*, W* | Power/energy |
| Column name prefix | POS*, DISP*, gap* | Position/displacement |
| Value range | 0-150 (~25 ambient) | Temperature |
| Value range | 0-10 (~1 typical) | Pressure |
| Value range | 0-5000 (non-zero baseline) | Speed |
| Value range | 0-1 or -1 to 1 | Normalized |
| Statistical signature | Step changes, low variance | Setpoint/control |
| Statistical signature | Gradual monotonic drift | Degradation indicator |
| Statistical signature | High-freq noise, zero-mean | Vibration/turbulence |
| Statistical signature | Cyclic with fixed period | Cyclic process |

**If Level 1 fails**: Mark `[PARAM_AMBIGUITY]`, confidence ceiling 50, PLAUSIBLE_HYPOTHESIS only.

### Level 2: Governing Law Selection

| Physical Quantity | Governing Laws | Key Equation |
|-------------------|---------------|-------------|
| Temperature | Energy conservation, Newton cooling, Fourier | m·Cp·dT/dt = Q̇in − Q̇out |
| Pressure (fluid) | Bernoulli, Darcy-Weisbach, Ideal gas | ΔP = f·(L/D)·(ρv²/2) |
| Flow rate | Continuity, Pump affinity | Q = A·v; Q ∝ N |
| Vibration | Forced oscillator, ISO 10816 | mẍ + cẋ + kx = F(t) |
| Force/Torque | Newton's 2nd, Cutting mechanics | F = m·a; F = ks·ap·f |
| Speed (rotational) | Kinematics, Power | v = π·D·N/60; P = τ·ω |
| Position/Displacement | Thermal expansion, Elastic deformation | ΔL = α·L₀·ΔT; ΔL = F·L/(A·E) |
| Power/Current | Motor power, Mechanical power | P = V·I·cosφ·η; P = τ·ω |
| Concentration | Reaction kinetics, Arrhenius | r = k·Cⁿ; k = A·exp(−Ea/RT) |
| Dimension (thickness) | Mass balance, Preston, Taylor | RR = Kp·P·v; VTⁿ = C |
| pH | Nernst, Corrosion rate | corrosion_rate ∝ [H⁺]ⁿ |
| Humidity/Moisture | Psychrometrics, Fick diffusion | J = −D·∇C |

### Level 3: Causal Chain Construction

Template: `Parameter deviation (ΔX) → [Governing Law L1] → Intermediate state (ΔY) → [Governing Law L2] → Quality metric (ΔQ)`

Each arrow must: reference a specific governing law, have a direction (+/−), have order-of-magnitude estimate.

### Level 4: Magnitude Estimation

1. **Dimensional analysis**: Do units work?
2. **Order-of-magnitude**: Predicted ΔY from equation vs observed
3. **Time constant**: τ = m·Cp/(h·A) for thermal, τ = L²/D for diffusion

Results: PLAUSIBLE (≤10×), BORDERLINE (10-100×), IMPLAUSIBLE (>100× — mechanism excluded).

### Level 5: Competing Mechanism Analysis

Identify ≥2 alternatives that could produce the SAME data pattern:
- Common cause (third variable Z drives both X and Y)
- Reverse causation (Y→X instead of X→Y)
- Measurement artifact (sensor cross-talk)
- Control system (loop compensating)
- Confounding event (maintenance, grade change)

### 1.3 First-Principles Documentation

```json
{
  "parameter": "novel_column_name",
  "physics_source": "first_principles_inference",
  "inference_levels": {
    "L1_physical_quantity": "...",
    "L2_governing_law": "...",
    "L3_causal_chain": "...",
    "L4_magnitude_check": "PLAUSIBLE/BORDERLINE/IMPLAUSIBLE",
    "L5_competing_mechanisms": ["Alt 1", "Alt 2"]
  },
  "confidence": "INFERRED_PHYSICS"
}
```

---

## Phase 1.5: Ontology-Data-Physics Proof Construction — Full Detail

### 5-Step Protocol

**Step 1 — Extract Ontology Prediction**: From `ontology.json` for each parameter: `physical_meaning`, `governing_law`, `predicted_functional_form`, `time_lag`, `behavior_match`.

**Step 2 — Map Ontology to Data**: Bridge abstract ontology descriptions to concrete data columns. Map `relationships[].from` → data column for cause, `relationships[].to` → data column for effect. Map governing equation variables to data values.

**Step 3 — Construct Testable Proof**: "If parameter X causes quality Y via mechanism M (equation E), then data MUST show: (a) functional form F, (b) lag τ, (c) magnitude within [min, max]."

**Step 4 — Validate Against Data**:

| Proof Element | Data Source | Validation |
|:---|:---|:---|
| Functional form | feature_summary + image_captions scatter | MATCH/MISMATCH/UNTESTABLE |
| Lag τ | feature_summary CCF, anomaly_onset_coincidence | MATCH/MISMATCH/UNTESTABLE |
| Magnitude | phyiscal_checks or first-principles | STRONG/PLAUSIBLE/BORDERLINE/IMPLAUSIBLE |
| Direction | feature_summary correlation sign + validate_report | MATCH/MISMATCH |

**Step 5 — Assign Proof Strength**:

| Proof Strength | Conditions | Confidence Impact |
|:---|:---|:---|
| PROVEN | All 4 MATCH + Magnitude STRONG | +15, label [PROVEN_MECHANISM] |
| STRONG_EVIDENCE | 3/4 match, none contradicted | +10 |
| SUPPORTIVE | 2/4 match, none contradicted | +5 |
| WEAK | 1/4 match, or any MISMATCH | −10, investigate |
| CONTRADICTED | Opposite direction MISMATCH | −20 or eliminate |

### Handling Ontology-Data Mismatches

| Mismatch Pattern | What It Proves |
|:---|:---|
| behavior_match CONTRADICTED + physics check NEGLIGIBLE | Ontology mechanism is NOT the cause → excludes hypothesis |
| Direction reversed (r opposite to predicted) | Parameter measures something different OR control loop compensating |
| Predicted exponential, data is linear | Degradation NOT thermally activated → excludes temperature-driven |
| Predicted lag minutes, observed lag hours | Different physical mechanism → knowledge gap |
| Magnitude IMPLAUSIBLE (ratio >100×) | Something beyond assumed physics → deeper investigation needed |

### Proof Template (for evidence.json)

```json
{
  "ontology_data_physics_proof": {
    "ontology_prediction": {
      "physical_meaning": "...",
      "governing_law": "...",
      "predicted_functional_form": "linear|monotonic|threshold|inverse|delayed_response",
      "time_lag": "... or NOT_APPLICABLE",
      "predicted_direction": "positive|negative|nonmonotonic|threshold-dependent",
      "behavior_match_precheck": "CONSISTENT|CONTRADICTED|UNVERIFIED"
    },
    "proof_elements": {
      "functional_form": {"predicted": "...", "observed": "...", "result": "MATCH", "evidence_source": "..."},
      "lag": {"predicted": "...", "observed": "...", "result": "MATCH", "evidence_source": "..."},
      "magnitude": {"predicted_equation": "...", "observed_slope": "...", "ratio_observed_to_predicted": "...", "result": "STRONG", "evidence_source": "..."},
      "direction": {"predicted": "...", "observed": "...", "result": "MATCH", "evidence_source": "..."}
    },
    "proof_strength": "PROVEN",
    "proof_statement": "..."
  }
}
```

---

## Phase 2: Pre-Computed Evidence + VLM Integration — Full Detail

### 2.1 Quality Reset Analysis

| reset_classification | Meaning | Root Cause Implication |
|---------------------|---------|------------------------|
| RESET | Quality changed after component change | Component IS the root cause |
| NO_RESET | Quality unchanged after component change | Component is NOT root cause |
| WORSENED | Quality got worse | Improper setup or incompatible component |
| INCONCLUSIVE | Insufficient data | Note as gap |

### 2.2 Anomaly-Onset Coincidence

| Classification | Meaning | Implication |
|---------------|---------|-------------|
| POTENTIAL_CAUSE | Parameter changed BEFORE quality | Strong root cause candidate |
| CONCURRENT_CHANGE | Changed simultaneously | Likely correlate or co-effect |
| Not in list | Did not change | Cannot be immediate cause |

### 2.3 Physical Threshold Verification

| Conclusion | Meaning | Use |
|-----------|---------|-----|
| PLAUSIBLE | Physics check confirms | Support hypothesis |
| NEGLIGIBLE | Effect too small | Exclude mechanism |
| CLIFF_DETECTED | Threshold found | Provide exact limit |
| IMPOSSIBLE | Violates physical law | Eliminate hypothesis |
| INCONCLUSIVE | Check not run | Knowledge gap |

### 2.4 VLM Visual Insight Integration

| Visual Insight Type | Evidence Weight |
|:---|:---|
| `synchronous_groups[]` — parameters moving together | STRONG — visual confirmation of correlation |
| `precedence_signals[]` — which parameter changes first | STRONG — visual temporal ordering |
| `independent_parameters[]` — visually uncorrelated | MODERATE — visual exclusion signal |
| `event_response` — jump/recovery patterns | CRITICAL — visual confirmation of quality reset |
| `trend_morphology` — linear vs accelerating | MODERATE — degradation pattern |

**Integration rules**:
1. Visual ↔ Statistical: both confirm → `VISUALLY_CONFIRMED_CORRELATION` (+5). Contradiction → investigate.
2. Visual temporal ordering + CCF confirms → `VISUALLY_CONFIRMED_PRECEDENCE`. Contradiction → trust CCF.
3. Visual event response + quality_reset_analysis alignment required.
4. Trend morphology: accelerating → progressive mechanism; linear → constant-rate; inflection → cross-reference change points.

---

## Phase 3: Candidate Shortlisting — Detailed Screening

### 3.1 KEEP if ALL conditions met:

1. **Data side**: Validated correlation (survives Simpson + detrending + outlier) OR MI > 0.3
2. **Physics side**: Pre-cached OR rag-extracted OR first-principles derived
3. **Evidence fusion**: Quality reset or onset coincidence supports direction
4. **Visual confirmation** (optional but strengthening)

**Adaptive scoring**: No time column → temporal factor 0/20. No grouping column → Simpson not applicable.

### 3.1 REMOVE if:
- BETWEEN_PRODUCT_ONLY or OUTLIER_ARTIFACT or trend-confounded (>50%)
- No physics available → `[UNKNOWN_PHYSICS]`
- Quality reset NO_RESET for component
- CONCURRENT but NOT PRECURSOR timing

### 3.3 Two Diagnostic Views (MANDATORY)

**View A — Pure Process-Fluctuation**: From `process_parameter_fluctuation` — which parameters show drift/high_variability/step_change/threshold_crossing/regime_switch/cyclic? Answers: "从纯工艺数据波动角度，系统本身出了什么问题？"

**View B — Integrated Dual-Drive**: From `dual_drive_analysis` — linked process-quality pairs with timing. Answers: "从工艺异常与质量异常结合的角度，哪条链更像真正根因？"

Final conclusion must state: process-side only / integrated dual-drive only / both.

### 3.4 Expert Handoff Usage

For each `data_analysis_conclusion.json.data_supported_conclusions[]`: map to hypotheses, verify artifacts, check caveats. For `priority_hypothesis_inputs[]`: treat as candidate input, require physical mechanism + falsification.

---

## Phase 4: 5-STEP COMPETING HYPOTHESES PROTOCOL — Full Detail

### STEP A: Hypothesis Generation Template

```
H[N]: [Descriptive title]

Physics Mechanism (source: pre_cached|rag_extracted|first_principles):
  [Full causal chain with governing equations at each step]

Quantitative Verification:
  - [Check name]: [conclusion] — [numerical result]
  - Magnitude check: predicted ΔQ=[X], observed ΔQ=[Y] → [PLAUSIBLE/BORDERLINE]

Data Evidence:
  - Correlation: r=[value], detrended r=[value]
  - Quality reset: [RESET/NO_RESET] on [event]
  - Onset coincidence: [PRECURSOR/CONCURRENT] (d=[value])

Visual Alignment:
  - [fig_N]: [diagnostic_implication from image_captions]
  - VLM observation: [specific observation from visual_analysis.json]
  - Temporal alignment group: [synchronous_group]

Chain Quality: [X]% OBSERVED + KNOWN_PHYSICS → [ACTIONABLE/PLAUSIBLE/RESEARCH_QUESTION]
```

**Required**: ≥3 competing hypotheses, each with falsification conditions.

### STEP A2: Chain Link Validation

For each causal chain, split into arrows `[cause]→[mechanism]→[intermediate]→[mechanism]→[effect]`. Each arrow must pass:

| Check | Data Source | Pass Condition |
|------|-------------|---------------|
| Data column exists | feature_summary column_names | Both ends map to data columns |
| Statistical correlation | feature_summary correlation matrix | Pair has raw r entry |
| Direction consistency | feature_summary r sign | Sign matches arrow direction |
| Physical feasibility | Magnitude check L4 | Ratio ≤10× (PLAUSIBLE) or ≤100× (BORDERLINE) |

**Results**: ALL_LINKS_VALIDATED / DATA_LINK_MISSING / CORRELATION_ABSENT / DIRECTION_MISMATCH / MAGNITUDE_IMPLAUSIBLE

**Rules**:
- CORRELATION_ABSENT → must document in `diagnosis.json.causal_chain_validation` and `reasoning_chain.json` R4, not silently deleted
- >1 arrow unverified → hypothesis cannot be DETERMINED, must be COMPETING_SET
- All results go to `evidence.json.validation_evidence[]` and `diagnosis.json.inference_gaps[]`

### STEP B: Cross-Check Evidence

| Check | Evidence Source | Decision |
|-------|----------------|----------|
| Quality reset | anomaly_report.quality_reset_analysis | RESET→SUPPORTED; NO_RESET→CONTRADICTED |
| Onset timing | anomaly_report.anomaly_onset_coincidence | PRECURSOR→STRONG; CONCURRENT→WEAK |
| Physics check | anomaly_report.phyiscal_checks | PLAUSIBLE→+5; IMPOSSIBLE→-20 (eliminate) |
| Causal map | causal_evidence_map.edges[] | validated=true→CONSISTENT |
| Visual evidence | visual_analysis + image_captions | Consistent→SUPPORTED; confirmation→+5 |
| Ontology behavior | ontology parameters[].behavior_match | CONTRADICTED→INVESTIGATE |
| RAG validation | rag_deep_understanding.claim_validations[] | CONTRADICTED→reduced confidence |
| Parameter ambiguity | clarification_needed.json | UNKNOWN→ceiling 50, [PARAM_AMBIGUITY] |

### STEP C: Data Discriminability

For every pair of surviving hypotheses:
- Different predicted observables?
- Quality reset discriminates? (one RESET, other NO_RESET)
- Onset timing discriminates? (different ordering)
- Physics check discriminates? (one PLAUSIBLE, other IMPOSSIBLE)
- Magnitude discriminates?

Classification: INDISTINGUISHABLE (ceiling 65), PARTIALLY_DISCRIMINABLE, DISCRIMINABLE, ONE_SIDE_EXCLUDED.

### STEP D: Exclusion Verification

**Physical exclusion**: ARRHENIUS_NEGLIGIBLE, THERMAL_EXPANSION_INSUFFICIENT, ENERGY_NEGLIGIBLE, FORCE_EXCEEDS_MODEL, IMPLAUSIBLE magnitude check → mechanism EXCLUDED.

**Quality reset exclusion**: NO_RESET after component replacement → component ELIMINATED (single most powerful exclusion test).

**Statistical exclusion**: No validated correlation, direction contradiction.

**Ontology discrepancy exclusion**: behavior_match CONTRADICTED with strong physics → mechanism may not apply.

**Required**: ≥2 excluded hypotheses.

### STEP E: Diagnostic Conclusion

**DETERMINED**: Single hypothesis survives with physics confirmation + quality reset support + PRECURSOR timing + visual alignment.

**COMPETING_SET**: Multiple remain. Specify: discriminating data needed, insufficient evidence, physics of each.

**NEEDS_DATA**: Insufficient evidence. Specify: needed measurements, incomplete checks, missing first-principles info.

**Every conclusion MUST include**: Physical mechanism trace (governing equation + source), data evidence (specific numbers), pre-computed physics evidence, quality reset/onset evidence, visual evidence, falsification condition.

---

## Phase 5: Reasoning Chain — R1-R8 Segments

| Segment | Content | Key Sources |
|---------|---------|-------------|
| R1 | Data characterization + scenario description | scenario_classification, ontology, input_manifest |
| R2 | Statistical discovery + fusion evidence + VLM observations | feature_summary, anomaly_report.*, visual_analysis |
| R3 | Validation filter + anomaly annotations | validate_report, anomaly_report.anomaly_intervals[] |
| R4 | Hypothesis generation with causal chains, ontology-data-physics proof, VLM evidence | parameter_to_physics, rag, ontology, visual_analysis |
| R5 | Discriminability assessment | quality_reset_analysis, phyiscal_checks[] |
| R6 | Exclusion documentation | Quality reset exclusions, physics exclusions, statistical exclusions |
| R7 | Diagnostic conclusion + falsification condition | Synthesis of ALL evidence |
| R8 | Uncertainty bounding + recommended measurements | Knowledge gaps, unresolved clarifications |

---

## Phase 6: Output Files — Schemas and Templates

**Schema-First rule**: Before writing ANY output file, read its schema + template:

| Output File | Read First |
|-------------|------------|
| `diagnosis.json` | `schemas/diagnosis_schema.json` + `templates/diagnosis_template.json` |
| `evidence.json` | `schemas/evidence_schema.json` |
| `confidence.json` | `schemas/confidence_schema.json` |
| `reasoning_chain.json` | `schemas/reasoning_chain_schema.json` |

### 6.1 diagnosis.json Required Fields
- `root_cause`: DETERMINED or COMPETING_SET
- `physics_mechanism`: causal chain + governing equation + source annotation
- `quantitative_verification`: physics check results or first-principles magnitude
- `quality_reset_evidence`: specific reset analysis
- `visual_evidence`: VLM observations + image captions
- `process_fluctuation_analysis`: standalone process-only conclusion
- `integrated_dual_drive_analysis`: standalone process+quality conclusion

### 6.1A Two Views Writing Rule
1. `process_fluctuation_analysis` must NOT depend on defect evidence. Answers: "仅从工艺参数波动与工艺机理看，哪里异常？"
2. `integrated_dual_drive_analysis` must connect process abnormality to quality. Answers: "哪些工艺异常真的进入了质量/缺陷结果链？"
3. Both must reference ontology + physics.

### 6.2 evidence.json Required Fields
- `visual_evidence[]`: `source`, `finding`, `rank` (1-7), `implication`
- `numerical_evidence[]`: `source`, `finding`, `rank`
- `physical_evidence[]`: `source`, `finding`, `rank`
- `validation_evidence[]`: `source`, `finding`, `affected_hypotheses`

Each item cites BOTH data source AND physics source.

### 6.3 confidence.json — 5-Factor Breakdown

| Factor | Max | Source | Notes |
|--------|-----|--------|-------|
| Statistical Strength | 20 | validate_report | Survives Simpson + detrending + outlier |
| Physical Plausibility | 25 | Quantitative calculation | Pre-cached: baseline. RAG-extracted: -5. First-principles (PLAUSIBLE): -10. First-principles (BORDERLINE): -15. Proof strength adjustments: PROVEN +15, STRONG_EVIDENCE +10, SUPPORTIVE +5, WEAK -10, CONTRADICTED -20/eliminate |
| Temporal Evidence | 20 | CCF + visual | **No time column → auto 0/20.** Lag-compensated r preferred |
| Confounding-Free | 20 | Simpson check | **No grouping column → reduced.** BETWEEN_PRODUCT_ONLY reduces |
| Symptom Completeness | 15 | Anomaly interval coverage | How much of anomaly window does hypothesis explain? |

**Confidence ceilings**:
- 65: INDISTINGUISHABLE competing hypotheses
- 50: [PARAM_AMBIGUITY] / UNKNOWN-meaning parameter as primary predictor
- Tiebreaker: stricter (lower) ceiling wins

**Adjustments**:
- Quality reset supports: +5 to +10
- Quality reset contradicts: -10 to -20
- Physics check PLAUSIBLE: +5 to +10
- Physics check IMPOSSIBLE: -20 (eliminate)
- Missing physics check: -10

---

## Phase 7: Schema Validation Commands

```bash
node $SHARED_PATH/scripts/validate.mjs $SHARED_PATH/schemas/diagnosis_schema.json $RUN_DIR/04_diagnostics/diagnosis.json
node $SHARED_PATH/scripts/validate.mjs $SHARED_PATH/schemas/evidence_schema.json $RUN_DIR/04_diagnostics/evidence.json
node $SHARED_PATH/scripts/validate.mjs $SHARED_PATH/schemas/confidence_schema.json $RUN_DIR/04_diagnostics/confidence.json
node $SHARED_PATH/scripts/validate.mjs $SHARED_PATH/schemas/reasoning_chain_schema.json $RUN_DIR/04_diagnostics/reasoning_chain.json
node $SKILL_PATH/scripts/diagnostic-quality-check.mjs $RUN_DIR
```

Quality check is a completion gate — if it fails, repair before declaring complete.

---

## Pipeline Event Log

```jsonl
{"event": "agent_start", "agent": "diagnostician", "timestamp": "..."}
{"event": "agent_complete", "agent": "diagnostician", "timestamp": "...", "files_written": [...], "physics_source_counts": {"pre_cached": N, "rag_extracted": N, "first_principles": N}, "errors": null}
```

---

## Rules — Full Reference

### Universal Physics Rule
Every hypothesis MUST have a physical mechanism. Pre-cached → use. Novel → derive L1-L5. RAG principles apply across parameters.

### Data-Physics Fusion Rule
Both data AND physics must support. Statistical-only → `STATISTICAL_ONLY`. Physics-only → `UNVERIFIED_HYPOTHESIS`. Pre-computed physics checks are authoritative. Quality reset is the most powerful discriminator.

### First-Principles Fallback Rule
Novel parameters → MANDATORY Ladder. Level 1 fails → [PARAM_AMBIGUITY], ceiling 50. Level 4 fails → mechanism EXCLUDED.

### Ontology Discrepancy Rule
CONTRADICTED behavior_match is a PRIMARY diagnostic signal. Surface mismatches — they are evidence, not errors.

### Ontology-Data-Physics Proof Rule
Every hypothesis must have Phase 1.5 proof. Correlation without proof → `STATISTICAL_ONLY`. Mismatches are proofs in themselves.

### Statistical Honesty
Never cite aggregate correlation reversed in dominant subgroup. Always report detrended r when attenuation >30%. Pre-validated correlations from causal_evidence_map take precedence.

### Confidence Integrity
All ceilings and adjustments listed in Phase 6.3 above. Proof strength from Phase 1.5.

### Hallucination Prevention — STOP Checklist

Before writing ANY conclusion:
- [ ] Specific data backing? (cite exact numbers)
- [ ] Physical mechanism? (cite governing equation + source)
- [ ] Quantitative check done? (pre-computed or first-principles)
- [ ] Ontology-data-physics proof constructed? (Phase 1.5: MATCH/MISMATCH documented)
- [ ] Mismatch documented as diagnostic discovery?
- [ ] Chain link validation done? (STEP A2: each arrow checked)
- [ ] CORRELATION_ABSENT documented in inference_gaps[] and chain corrected?
- [ ] Quality reset analysis cited?
- [ ] Onset coincidence cited? (PRECURSOR vs CONCURRENT)
- [ ] Ontology behavior match cited? (CONTRADICTED → explain diagnostic implication)
- [ ] Image caption diagnostic_implication cited?
- [ ] VLM visual analysis cited? (sync group? precedence? event response?)
- [ ] Visual evidence consistent with statistical evidence? (flag contradictions)
- [ ] Evidence rank cited?
- [ ] Conclusion falsifiable?
- [ ] Can a reasonable expert disagree? (if yes, downgrade confidence)
