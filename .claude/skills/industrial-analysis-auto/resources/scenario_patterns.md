# Scenario-Specific Analysis Patterns

Load this file during data-processor Phase 3 (Scenario-Specific Deep Analysis).
Read only the sections that match your detected data shapes. Skip the rest.

---

## A. Multi-Zone Sensors

**Detection**: Same prefix, sequential numbering (e.g., `zone_1` through `zone_12`)

**Key question**: Is the degradation GLOBAL (all zones drift together) or LOCAL (only specific zones drift)?

**Analysis to run**:
1. **Zone drift localization**: Compute trend slope per zone. Rank zones by drift magnitude.
2. **Spatial profile evolution**: Plot the spatial profile at t=start, t=middle, t=end.
3. **Zone correlation matrix**: Pairwise correlations between zones.
4. **Adjacent-zone differentials**: Δ = zone[i] - zone[i-1] over time.

**Output**: `02_processed/zone_analysis.json`

---

## B. Paired / Cascaded Sensors

**Detection**: Pairs like `inlet_temp`/`outlet_temp`, `feed_pressure`/`die_pressure`

**Key question**: Where in the process chain does degradation occur?

**Analysis to run**:
1. **Differential trends**: Plot inlet-outlet differentials over time.
2. **Efficiency metrics**: ε = (T_in-T_out)/(T_in-T_ambient); ΔP/Q²; η = ρgQH/P
3. **Cascade timing**: Lagged correlations to verify cascade direction.

---

## C. Multi-Level Grouping

**Detection**: Multiple categorical columns with nesting (product > batch > reel)

**Key question**: At which level does variation occur?

**Analysis to run**:
1. **Variance decomposition**: Compute variance components at each grouping level.
2. **Level-specific trends**: Trends within each batch, compare slopes across batches.
3. **Interaction detection**: Grade-specific correlations.

---

## C1. Product / Lot / Grade Grouping (MANDATORY when such columns exist)

**Key question**: Within-product instability or between-product difference?

**Analysis to run**:
1. **Primary grouping selection**: Pick one main grouping column, justify why.
2. **Within-product time ordering**: Sort within each product group by time.
3. **Per-product timeline analysis**: Overlay process params + inspection targets per product.
4. **Between-product confounding check**: Aggregate r vs within-product r.
5. **Product-switch transition analysis**: Quality baselines at product boundaries.
6. **Per-product fluctuation severity**: Within-product CV / p05-p95 span / drift slope.
7. **Dual-drive integration**: Process-side abnormality + inspection-side abnormality per product.

**Required outputs**: `anomaly_report.json.dual_drive_analysis.per_product_analysis`, product-grouped figures in `03_figures/`

---

## D. Event Markers

**Detection**: Columns that change value at specific times (maintenance, grade changes)

**Key question**: Does quality reset after events? (Most powerful diagnostic signal.)

**Analysis to run**:
1. **Quality reset analysis**: Quality before/after events → RESET / NO_RESET / WORSENED
2. **Event-aligned averaging**: Average quality trajectory aligned at t=0 for each event type
3. **Cumulative degradation**: Quality vs time-since-last-event

**Output**: `02_processed/event_analysis.json`

---

## E. Nonlinear Relationships

**Detection**: Scatter plots show nonlinear patterns

**Analysis to run**:
1. **Threshold detection**: Piecewise linear fit, LOWESS inflection detection
2. **Operating regime identification**: Map thresholds to physical boundaries
3. **Regime-separated statistics**: Correlations above/below threshold

---

## F. Periodic / Cyclic Patterns

**Detection**: FFT shows dominant frequencies in quality metrics

**Analysis to run**:
1. **Spectral analysis**: Identify dominant frequencies (24h = diurnal, ~8h = shift-related)
2. **Cycle-phase analysis**: Quality mean/variance per cycle phase
3. **Partial correlation with cyclic removal**

---

## G. Zero Automatic Physics Checks

If `physics_check.py` returns 0 checks: perform manual quantitative verification.

1. Identify governing physics for top-3 parameter-quality pairs (L1-L5)
2. Magnitude check: predicted vs observed effect size
3. Document in `02_processed/physics_manual_verification.md`

---

## H. Process-Only Data (no quality/inspection target)

Do not invent quality targets. Analyze process health only.

**Analysis to run**:
1. **Process stability ranking**: CV, p05-p95 span, rolling volatility, drift slope, abrupt-change indicators
2. **Regime and event segmentation**: Step changes, product/lot switches, setpoint changes
3. **Spatial / cascade localization**: Where drift/volatility concentrates
4. **Control behavior checks**: Tracking error, saturation, oscillation, delayed response
5. **Sensor consistency checks**: Flatlined sensors, duplicated channels, implausible jumps

Required: `data_analysis_conclusion.json.adaptive_decision_audit.data_view_mode = "process_only"`, evidence gap stated in `analysis_coverage_matrix`

---

## I. Startup / Shutdown / Abnormal Period Auto-Detection & Steady-State Filtering (v6.5 MANDATORY)

**Context**: Real production lines transition through startup (ramp-up), steady-state (normal operation), and shutdown (ramp-down) states. During startup/shutdown, process parameters exhibit large, non-representative excursions. Including these periods in statistical analysis produces inflated correlations and misleading causal conclusions. Most factories do NOT digitally log startup/shutdown events — detection must be algorithmic.

**Detection method**: Three independent algorithms fused via consensus voting:
1. **Multi-parameter sliding window variance ratio** — startup/shutdown = sudden high variance across multiple parameters
2. **Binary segmentation change-point detection** — identifies regime transition boundaries where parameter means shift
3. **Directional ramp detection** — positive slope = startup (parameters rising to setpoints), negative slope = shutdown (parameters falling from setpoints)

**Required inputs**: Raw CSV data with at least 1 numeric column and ≥ 20 rows.

**Required outputs**:
- `02_processed/production_regime_filter.json` — per-row regime labels + filter mask + per-product anomaly analysis
- `02_processed/cleaned_data_steady_only.csv` — steady-state-only data subset (when steady rows exist)

**Fusion logic**:
| Variance ratio | Ramp score | Near change point | Final label |
|---------------|------------|-------------------|-------------|
| >> 1 | > +0.03 | no | `startup` |
| >> 1 | < -0.03 | no | `shutdown` |
| >> 1 | near 0 | no | `abnormal` |
| any | any | yes | `transition` |
| ~ 1 | near 0 | no | `steady` |
| 0.7-1× threshold | any | no | `marginal` |

**Filtering rule for downstream analysis**:
- **EXCLUDE**: `startup`, `shutdown`, `transition` — these contain non-representative parameter excursions
- **CAUTION on**: `abnormal`, `marginal` — flag for review, may indicate sensor faults or unlogged events
- **INCLUDE for core analysis**: `steady` only — represents the true process operating condition

**Per-product mandatory analysis** (when `group_column` detected):
- Identify the product with the highest target anomaly rate (`focus_product`)
- Isolate this product's steady-state rows
- Re-run within-product correlation, trend, CCF, time-lag analysis
- Compare aggregate (cross-product) correlations vs within-product correlations
- Document Simpson's Paradox evidence if they differ substantially
- This is NON-NEGOTIABLE for multi-product datasets

**Script**: `production_regime_detector.py` (standalone) or `dp_toolkit.py regime-filter` (wrapper invocation).
