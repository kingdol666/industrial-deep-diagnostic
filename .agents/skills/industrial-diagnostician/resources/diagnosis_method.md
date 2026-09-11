# Diagnosis Methodology

> **Canonical evidence rules, causation criteria, and confidence scoring:** See `evidence_rules.md`.
> This file contains the diagnostic methodology stages 1-6.

**Numbering note**: This file uses **Method Stage 1-6** — distinct from Pipeline Steps (0-8), Diagnostician Phases (0-7), and Reasoning Segments (R1-R8). See `pipeline-execution.md` §Numbering Systems.

## Stage 1: Statistical Validation (formerly Phase 0 — v4.2)

**Before any causal reasoning, validate the statistical evidence base:**

1. **Sorting check**: Is data sorted by time? If NOT → all lag correlations are invalid.
2. **Subgroup check**: Do key correlations hold within dominant product/grade subgroups? If NOT → Simpson's Paradox.
3. **Trend check**: Do detrended correlations differ from raw correlations? If attenuation > 50% → time-trend confounding.
4. **Outlier check**: Are key correlations driven by a few extreme batches?
5. **Method check**: Do Spearman and Pearson agree? For skewed defect data, Spearman is more reliable.
6. **Multiple testing check**: How many "significant" correlations are expected by chance?

**Every diagnostic hypothesis must be scored against these validation checks before confidence is assigned.**

## Stage 2: Observation

For each abnormal interval:
1. **What** changed — which signals deviated, by how much (absolute + %)
2. **When** — exact timestamps of onset, peak, recovery (ISO8601)
3. **Duration** — how long the deviation lasted
4. **Pattern** — gradual drift / sudden step / oscillation / spike
5. **What did NOT change** — signals that stayed stable (critical for ruling out hypotheses)

## Stage 3: Temporal & Correlation Analysis

1. Build a **timeline** — which signal changed first, second, third...
2. Compute **lagged cross-correlations** — for each process parameter vs each inspection signal, find the lag that maximizes |r|
   - **PREREQUISITE**: Data MUST be time-sorted. If not, skip lag analysis entirely — use only concurrent (lag=0) correlations.
3. Check **lag window consistency** — does the correlation persist across adjacent lags, or is it an isolated spike?
4. Compute **detrended correlations** — does the relationship survive removing shared time trends?
5. Compute **stratified correlations** — does the relationship hold within each product/grade subgroup?
6. Compute **Spearman correlations** — for robustness against outliers and non-linearity.
7. Cross-reference with **ontology relationships** — do observed correlations match known causal relationships?

## Stage 4: Hypothesis Formation

For each abnormal interval, list ALL plausible hypotheses. For each:
- Describe the physical mechanism (full causal chain)
- List supporting evidence (with ranks and validation status)
- List contradicting evidence (with ranks)
- **Note which validation checks the evidence passes/fails**
- Make testable predictions
- Rank by overall evidence strength (adjusted for validation findings)

### Confidence Adjustment Protocol

Start with evidence-based confidence, then adjust:

| Factor | Direction | Magnitude |
|--------|-----------|-----------|
| Data NOT time-sorted, lag used as evidence | DOWN | -25 to -40 |
| Simpson's Paradox in dominant subgroup | DOWN | -20 to -30 |
| Trend confounding (attenuation > 50%) | DOWN | -15 to -20 |
| Outlier-driven correlation | DOWN | -10 to -15 |
| Spearman-Pearson divergence > 0.15 | DOWN | -5 to -10 |
| Multiple independent evidence sources agree | UP | +5 to +10 |
| Quantitative physical model supports magnitude | UP | +10 to +15 |

## Stage 5: Confidence Assessment

Score each hypothesis 0-100 using 5 factors:

1. **Statistical strength** (0-25): Correlation magnitude, consistency across subgroups, detrending survival, Spearman agreement
2. **Physical plausibility** (0-20): Mechanism grounded in established process physics, quantitative magnitude check passed
3. **Temporal evidence** (0-20): Clear temporal ordering with validated time-sorting and consistent lag window
4. **Absence of confounds** (0-20): Survives stratification, detrending, and outlier checks
5. **Symptom completeness** (0-15): Explains all observed symptoms, no missing symptoms expected

Document:
- Supporting evidence
- Contradicting evidence
- Evidence gaps
- Assumptions made
- **Validation findings that affect confidence**
- Validation steps to confirm or reject

## Stage 6: Synthesis

1. Identify the primary hypothesis
2. Construct the causal chain with evidence at each step
3. **Mark each causal link as "directly observed" or "inferred"**
4. Assess overall confidence with validation adjustments disclosed
5. List recommended actions with priority, evidence reference, and validation notes
6. Disclose all limitations, especially validation-identified weaknesses

---

## Common Diagnostic Patterns

| Pattern | Likely Causes | What to Check |
|---------|--------------|---------------|
| Sudden step change | Control action, setpoint change, equipment switching, grade change | Control variables, event logs, product grade column |
| Gradual drift | Fouling, wear, degradation, environmental change | Trends, correlated slow variables, maintenance history |
| Oscillation | Controller tuning, mechanical looseness, flow instability | Control loop performance, frequency analysis |
| Spike | Transient disturbance, measurement noise, valve cycling | Duration, recovery, simultaneous events |
| Multi-variable cascade | One variable deviates, others follow in sequence | Temporal ordering, identify the leader signal |

---

## Statistical Thresholds

| Metric | Threshold | Notes |
|--------|-----------|-------|
| Z-score anomaly | \|z\| > 3 | Single variable |
| IQR outlier | 1.5 × IQR from Q1/Q3 | Robust to distribution |
| Pearson correlation | \|r\| > 0.7 strong, 0.3-0.7 moderate | Assumes linearity, outlier-sensitive |
| Spearman correlation | \|ρ\| > 0.7 strong, 0.3-0.7 moderate | Robust to outliers, monotonic |
| Detrended r attenuation | > 50% → trend-confounded | Always check for key correlations |
| Subgroup r direction | Opposite sign → Simpson's Paradox | Always stratify by product/grade |
| Pearson-Spearman divergence | > 0.15 → outlier influence | Prefer Spearman for skewed data |
| CCF isolated spike | Single lag with r > 0.3, neighbors near 0 | Red flag — check data sorting |
| Lag window consistency | ≥ 2 adjacent same-sign lags with \|r\| > 0.3×\|best_r\| | Required for temporal precedence claim |
| Bonferroni threshold | α / N_tests | Controls family-wise error rate |
| Expected false positives | N_tests × α | ~5% of tests "significant" by chance at α=0.05 |
| Sample for stratification | n > 20 per subgroup | Below this, stratified analysis unreliable |

---

> **Causation criteria (5 criteria for "X caused Y") and evidence ranking (1-7):** See `evidence_rules.md`.

