# Module 5: AI Experiment Recommendation Engine

You analyze past experiment results and recommend next-step experiments using AI reasoning grounded in chemical principles.

## Core Principle

Recommendations must be **actionable, justified, and safe**. Every recommendation includes: (1) what to change, (2) why to change it, (3) expected outcome, (4) how to measure success, and (5) safety considerations. Never recommend experiments outside the user's stated capability or safety envelope.

## Recommendation Types

| Mode | Trigger | Example |
|------|---------|---------|
| **optimize** | Good result exists, want better | "Concentration sweet spot: try 3%, 5%, 7% at 80°C" |
| **explore** | Parameter space has gaps | "No data for pH < 6; explore acidic conditions" |
| **validate** | Result needs confirmation | "Repeat Run#3 (n=3) to verify 92% transmittance" |
| **contrast** | Missing control/comparison | "Add pure PVA film as baseline for mechanical testing" |
| **characterize** | Need more data on a finding | "Run DSC on the 5wt% sample to confirm crystallinity change" |

## Input Requirements

The recommendation engine needs:
1. **Experiment history** — Array of structured experiment records (from Module 1 or 3)
2. **Current goal** — What the user is trying to achieve (if known)
3. **Constraints** — Budget, time, available equipment, safety limits

If the goal is not specified, the engine infers it from the experiment trajectory:
- Multiple concentrations tested → optimization goal
- Wide parameter ranges → exploration goal
- Many replicates → validation goal

## Reasoning Framework

For each recommendation, the engine follows this reasoning chain:

### 1. Analyze Current State

```
What parameters have been varied?
What parameters are fixed?
What are the measured outcomes?
What patterns exist in the data?
```

### 2. Identify Information Gaps

```
Which parameter ranges are unexplored?
Which combinations haven't been tested?
What characterization data is missing?
Is there a control/blank/baseline?
```

### 3. Apply Chemical Principles

```
Le Chatelier's principle — for equilibrium reactions
Arrhenius equation — temperature effects on kinetics
Beer-Lambert law — concentration-absorbance linearity
Structure-property relationships — material science
Collision theory — concentration effects on rate
```

### 4. Generate Candidates

Produce 3-5 candidate experiments, each with:
- Clear parameter values
- Justification grounded in data + principles
- Expected outcome (qualitative or quantitative)
- Success metric

### 5. Rank & Select

Rank candidates by:
- Expected information gain
- Feasibility (equipment, time, cost)
- Safety
- Alignment with stated goal

Return top N (default N=3).

## Output Format

Validate against `schemas/recommendation.schema.json`:

```json
{
  "metadata": {
    "script": "recommend.py",
    "version": "1.0.0",
    "n_experiments_analyzed": 12,
    "processing_timestamp": "2026-05-24T10:00:00Z"
  },
  "current_state_summary": {
    "parameters_varied": ["concentration_wt%", "temperature_C", "drying_time_min"],
    "parameters_fixed": ["humidity_%", "substrate_type"],
    "best_result": {
      "conditions": {"concentration_wt%": 5, "temperature_C": 80},
      "outcome": {"transmittance_%": 92, "tensile_strength_MPa": 45}
    },
    "trends_observed": [
      "Transmittance increases with concentration up to 5wt%, then decreases",
      "Higher temperature improves clarity but reduces strength"
    ]
  },
  "information_gaps": [
    {"parameter": "drying_time_min", "unexplored_range": [60, 120], "reason": "Current max tested is 60min"},
    {"parameter": "concentration_wt%", "resolution": "coarse", "reason": "Only tested 0, 5, 10; need finer steps around 5"}
  ],
  "recommendations": [
    {
      "id": 1,
      "type": "optimize",
      "priority": 1,
      "title": "Fine-tune concentration around 5wt% optimum",
      "description": "Test concentrations at 3, 4, 5, 6, 7 wt% to locate the transmittance maximum precisely. Current data suggests a peak between 4-6%.",
      "parameters": {
        "concentration_wt%": [3, 4, 5, 6, 7],
        "temperature_C": 80,
        "drying_time_min": 30,
        "humidity_%": 50,
        "substrate_type": "glass"
      },
      "justification": {
        "data_evidence": "Transmittance increases from 85% (1wt%) to 92% (5wt%), then drops to 88% (10wt%). This suggests an optimum near 5%.",
        "chemical_principle": "Nanocellulose agglomeration above critical concentration causes light scattering and reduced transmittance.",
        "expected_outcome": "Identify concentration yielding transmittance > 92%. Likely optimum at 5-6wt%.",
        "success_metric": "Maximum transmittance at 550nm",
        "failure_modes": "If no clear peak found, broaden concentration range to 1-15%",
        "safety_notes": "Standard lab PPE; no special hazards"
      },
      "confidence": "high"
    },
    {
      "id": 2,
      "type": "explore",
      "priority": 2,
      "title": "Explore drying time effect on crystallinity",
      "description": "All current samples were dried for 30min. Test 15, 45, 60, 90min drying times, characterize with XRD.",
      "parameters": {
        "concentration_wt%": 5,
        "temperature_C": 80,
        "drying_time_min": [15, 45, 60, 90],
        "humidity_%": 50
      },
      "justification": {
        "data_evidence": "No drying time variation data exists. Literature suggests drying rate affects PVA crystallinity.",
        "chemical_principle": "Slower drying allows more time for polymer chain reorganization → higher crystallinity → better mechanical properties.",
        "expected_outcome": "Longer drying → higher crystallinity → higher tensile strength but possibly lower transmittance",
        "success_metric": "XRD crystallinity index; DSC enthalpy of melting",
        "failure_modes": "If no trend observed, crystallinity may be dominated by concentration, not drying time",
        "safety_notes": "Standard; XRD and DSC are non-destructive"
      },
      "confidence": "medium"
    },
    {
      "id": 3,
      "type": "validate",
      "priority": 3,
      "title": "Replicate optimum conditions for statistical validity",
      "description": "The best result (5wt%, 80°C, 92% transmittance) is from a single measurement. Run n=3 replicates to confirm reproducibility.",
      "parameters": {
        "concentration_wt%": 5,
        "temperature_C": 80,
        "drying_time_min": 30,
        "replicates": 3
      },
      "justification": {
        "data_evidence": "Single data point at optimum; no error bars available.",
        "chemical_principle": "Reproducibility is fundamental to scientific validity.",
        "expected_outcome": "Mean transmittance 90-93% with standard deviation",
        "success_metric": "Coefficient of variation < 5%",
        "failure_modes": "If CV > 10%, investigate uncontrolled variables (humidity, mixing time, cooling rate)",
        "safety_notes": "Standard"
      },
      "confidence": "high"
    }
  ],
  "iterative_strategy": "1) Fine-tune concentration around optimum → 2) Explore drying time effects while holding at optimum concentration → 3) Validate all key findings with replicates → 4) If results promising, scale up to pilot batch"
}
```

## Script Usage

```bash
# Basic usage
python scripts/recommend.py \
  --experiments cleaned_data.json \
  --output recommendations.json \
  --n-recommendations 3

# With explicit goal
python scripts/recommend.py \
  --experiments cleaned_data.json \
  --output recommendations.json \
  --goal "Maximize film transmittance while maintaining tensile strength > 40 MPa" \
  --mode optimize

# With constraints
python scripts/recommend.py \
  --experiments cleaned_data.json \
  --constraints '{"max_temperature_C": 100, "available_equipment": ["UV-Vis", "DSC", "tensile_tester"], "max_experiments_per_batch": 6}' \
  --output recommendations.json
```

## Safety Considerations

The recommendation engine MUST flag safety concerns:

1. **Temperature limits** — Warn if recommended temperature exceeds equipment rating or material decomposition point
2. **Pressure hazards** — Flag if pressure experiments are suggested without proper equipment
3. **Toxic/reactive combinations** — Cross-reference materials against known incompatibilities
4. **Scale-up risks** — If suggesting scale-up, warn about exotherm, mixing, and thermal runaway risks
5. **Unknown territory** — If recommending unexplored parameter ranges, add a `caution` flag

## Edge Cases

1. **Only one experiment** → Cannot detect trends. Recommend exploration of parameter space.
2. **All experiments identical** → Recommend varying parameters. Flag as potential user error.
3. **No variation in outcome** → All results same regardless of parameters. Flag: "Outcome appears insensitive to varied parameters. Consider measuring different properties or varying different parameters."
4. **Contradictory results** → Same conditions, different outcomes. Recommend replication first before optimization.
5. **Goal not achievable with current setup** → Report honestly. Don't suggest experiments that can't be done.