# Analysis Methods Catalog — adaptive method-selection catalog

The single source of methods for Phase 1.2 (hypothesis-driven method selection). **The skill defines only the direction and the selection rules; the concrete execution, parameters, and scripts are for the agent to judge from the actual state of the data.**

## Selection Rules (iron law)

1. **Methods follow hypotheses**: every candidate hypothesis H must map to ≥1 minimal method set that can **discriminate** it; any method that cannot discriminate it is not run at all.
2. **Minimal sufficiency**: prefer the method combination that "discriminates the most hypotheses with the least computation"; run the full battery (`--mode full`) only when the method plan explicitly selects all three stats modes.
3. **Skips must leave a trace**: when a traditional "must-run" method is skipped, state in `skipped` of `analysis_method_plan.json` why its trigger conditions are not met.
4. **If the catalog falls short, build your own**: when no existing tool can discriminate a hypothesis → write a focused custom script (M13) and register it in the plan.
5. **Unmet preconditions = automatic skip**: each method's Preconditions are hard thresholds; self-check before running.

## Method entries

### M1 · Correlation Screening — `stats/run.py --mode correlation`
- **Discriminates**: which predictors carry (spurious) correlation leads with the target
- **Preconditions**: ≥2 numeric predictors + ≥1 numeric target; non-numeric columns already stratified in Phase 0.4
- **Produces**: the correlation section of validate_report.json
- **Do not use**: when all targets are constant/categorical; for purely categorical targets use the M8 stratified comparison instead

### M2 · Anti-Spurious Battery — `stats/run.py --mode spurious`
- **Discriminates**: whether the M1 leads are real or spurious (Simpson / detrending attenuation / change point / leave-one-out leverage)
- **Preconditions**: a grouping column (Simpson/LOO) or a time column (detrending/change point) — at least one of the two
- **Do not use**: single product with no time column (nothing to decompose); when M1 found no candidate with |r|≥0.3 it may be degraded to change point only

### M3 · Batch Integrity — `stats/run.py --mode batch`
- **Discriminates**: batch identity completeness, cross-batch contamination (v6.6)
- **Preconditions**: a batch/_lot/_id identity column exists
- **Do not use**: no batch identity column at all

### M4 · Anomaly Detection — `dp_toolkit.py anomaly`
- **Discriminates**: the distribution of anomalies, their onset time, and their co-occurrence with the target
- **Preconditions**: ≥1 numeric column (almost always satisfied) → **default baseline method**
- **Do not use**: none (when unavailable, simply state the reason)

### M5 · Production Regime Filter — `dp_toolkit.py regime-filter`
- **Discriminates**: whether non-steady-state operation (startup/shutdown/product changeover) contaminated the statistics; determines the stats input source
- **Preconditions**: time column + regime-type signals
- **Do not use**: no time column (fallback to full data + WARNING, already defined in protocol Phase 1.5)

### M6 · Time-Lag CCF Compensation — `time_lag_compensator.mjs`
- **Discriminates**: whether X precedes Y or is synchronous/inverse (evidence of causal direction, v6.4)
- **Preconditions**: time column + process_plus_inspection dual-drive data
- **Do not use**: no time column; one-sided data (under process_only the missing causal-temporal evidence is a natural evidence gap — write it into the conclusion rather than forcing the run)

### M7 · Physics Constraint Checks — `physics_check.py`
- **Discriminates**: whether the ontology's physical relationships (direction/magnitude/functional form) agree with the data direction
- **Preconditions**: numerically checkable relationships exist in ontology relationships + the corresponding columns exist
- **Do not use**: the ontology has no checkable physical relationship (0 checks is legitimate, but must be stated)

### M8 · Stratified / Per-Product Analysis — `stats/run.py --group-col <col>` + mode C
- **Discriminates**: whether an aggregate correlation is fabricated by between-group differences (the positive verification of Simpson); locates the worst group
- **Preconditions**: a product/group column with ≥2 groups and adequate samples per group (≥30 rows preferred)
- **Do not use**: no grouping column, or number of groups = 1

### M9 · Paired-Sensor Differential & Efficiency — mode B (custom script, T3)
- **Discriminates**: **which segment** of a cascade chain is degrading (Δ=inlet−outlet, trend/change point of the ε efficiency metric)
- **Preconditions**: paired sensors (inlet/outlet, feed/die, etc.) or a derivable efficiency measure
- **Do not use**: no paired structure

### M10 · Zone Drift Localization — mode A (custom script, T3)
- **Discriminates**: whether degradation is global or local (zone slope ranking, adjacent differencing)
- **Preconditions**: identically prefixed + sequentially numbered zone columns (zone_1..zone_N)
- **Do not use**: no zone structure

### M11 · Event-Response Alignment — custom script, T3
- **Discriminates**: whether a step/trend change exists in the indicators before and after an event (tool change/cleaning/maintenance)
- **Preconditions**: an event marker column or known event time points + a time column
- **Do not use**: no event information

### M12 · Scenario-Pattern Deep Dives — `resources/scenario_patterns.md` A–H
- Load the section matching the data shape detected in Phase 1; **execute only when the method plan maps it to a hypothesis**
- A pattern added outside the plan → the reason must be back-filled in the Adaptive Decision Audit

### M13 · Custom Focused Script (escape hatch)
- Discriminates: targeted computation when nothing in the catalog applies
- Requirements: write into `06_scripts/`, obey the Data Truth Mandate, and write the outputs back for citation in the conclusion

## Hypothesis → Method quick reference (example mapping, not exhaustive)

| Hypothesis type | Typical discriminative methods |
|---------|-------------|
| "Drift in parameter X degrades the target" | M1 → M2 (detrending/change point) → M6 (temporal precedence) → M7 (physical direction) |
| "A product/tool-specific problem" | M8 → M2 (stratified Simpson) → M4 (anomaly rate of the worst group) |
| "Efficiency drop in one segment of a cascade chain" | M9 → M7 (efficiency physics formula) → M2 (change point of the Δ metric) |
| "Batch contamination / mislabeling" | M3 → M8 |
| "Non-steady-state regimes mixed into the statistics" | M5 → M2 (steady-state before/after comparison) |
| "Localized zone degradation" | M10 → M1 (zone ranking) |
