# Diagnosis Methodology

## Phase 1: Observation

For each abnormal interval:
1. **What** changed — which signals deviated, by how much (absolute + %)
2. **When** — exact timestamps of onset, peak, recovery (ISO8601)
3. **Duration** — how long the deviation lasted
4. **Pattern** — gradual drift / sudden step / oscillation / spike
5. **What did NOT change** — signals that stayed stable (critical for ruling out hypotheses)

## Phase 2: Temporal & Correlation Analysis

1. Build a **timeline** — which signal changed first, second, third...
2. Compute **lagged cross-correlations** — for each process parameter vs each inspection signal, find the lag that maximizes |r|
3. Cross-reference with **ontology relationships** — do observed correlations match known causal relationships?
4. Check **PID/controller behavior** — did the control system respond correctly?

## Phase 3: Hypothesis Formation

For each abnormal interval, list ALL plausible hypotheses. For each:
- Describe the physical mechanism
- List supporting evidence (with ranks)
- List contradicting evidence (with ranks)
- Make testable predictions
- Rank by overall evidence strength

## Phase 4: Confidence Assessment

Score each hypothesis 0-100. Document:
- Supporting evidence (what makes us believe this)
- Contradicting evidence (what goes against this)
- Evidence gaps (what we don't know but wish we did)
- Assumptions made
- Validation steps to confirm or reject

## Phase 5: Synthesis

1. Identify the primary hypothesis
2. Construct the causal chain with evidence at each step
3. Assess overall confidence
4. List recommended actions with priority and evidence reference
5. Disclose all limitations and assumptions

## Common Diagnostic Patterns

| Pattern | Likely Causes | What to Check |
|---------|--------------|---------------|
| Sudden step change | Control action, setpoint change, equipment switching | Control variables, event logs |
| Gradual drift | Fouling, wear, degradation, environmental change | Trends, correlated slow variables, maintenance history |
| Oscillation | Controller tuning, mechanical looseness, flow instability | Control loop performance, frequency analysis |
| Spike | Transient disturbance, measurement noise, valve cycling | Duration, recovery, simultaneous events |
| Multi-variable cascade | One variable deviates, others follow in sequence | Temporal ordering, identify the leader signal |

## Statistical Thresholds

| Metric | Threshold | Notes |
|--------|-----------|-------|
| Z-score anomaly | \|z\| > 3 | Single variable |
| IQR outlier | 1.5 × IQR from Q1/Q3 | Robust to distribution |
| Correlation strength | \|r\| > 0.7 strong, 0.3-0.7 moderate | Pearson |
| Change point | p < 0.05 | Depends on algorithm |
