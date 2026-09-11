# Anti-Spurious Correlation Rules (v6.4–v6.7)

These rules defend against the five most common sources of spurious correlation in industrial data. Each rule gates downstream causal claims — a correlation that fails any applicable rule MUST be downgraded or excluded.

---

## Rule v6.4: Time-Lag Auto-Compensation

**Threat**: Process sensors record at the machine; quality inspection happens downstream. Zero-lag Pearson r compares process(t) with quality(t), but the true relationship is process(t) → quality(t+lag). Without compensation, genuinely causal process→quality relationships are systematically underestimated.

**Applicability**: BOTH of:
1. Valid time column exists (`input_manifest.json.time_column` is not null)
2. Data mode is `process_plus_inspection` (both process and quality targets exist)

**Script**: `$SKILL_PATH/scripts/time_lag_compensator.mjs` — reads `feature_summary.json` CCF data + `ontology.json` time-lag priors, finds optimal lag via peak-finding with ±3 adjacent-lag consistency check, compares physics-expected vs data-observed lag, reports `lag_compensated_correlation` and `r_improvement_pct`.

**Validation criteria**:

| Scenario | Action |
|----------|--------|
| Raw r < 0.2, compensated r > 0.4 | Major hidden relationship — upgrade causal priority |
| Raw r > 0.5, compensated r similar | Zero-lag adequate — no correction needed |
| Optimal lag found but consistency < 0.5 | Isolated spike — unreliable, do not use |
| Physics says lag=1-3h, data says 10min | Physics/data mismatch — investigate alternative mechanism |
| Ontology `time_lag` = "unknown" but CCF finds consistent lag | Data-driven discovery — feed back to enrich ontology |

**Key outputs to extract for diagnostics**:
- `recommendations`: pairs with `r_improvement ≥ 15%`, sorted by absolute improvement
- `physics_discrepancy_alerts`: pairs where expected lag disagrees with observed optimal lag
- `key_findings`: `confidence: high` or `moderate` pairs with `interpretation`

---

## Rule v6.5: Production Regime Detection & Steady-State Filtering

**Threat**: Real production lines have startup, steady-state, and shutdown states. Correlations computed on mixed-state data conflate transient dynamics (ramping, purging) with steady-state causal relationships. Product-switch confounding (Simpson's Paradox) is the #1 source of spurious r>0.7 correlations in multi-product datasets.

**Applicability**: ALWAYS — runs before any statistical analysis (Phase 2). Gates all downstream work.

**Script**: `$SKILL_PATH/scripts/production_regime_detector.py` (or via `dp_toolkit.py regime-filter`)

**Parameters**:
```
--window-minutes 10
--variance-threshold 3.0
--min-steady-ratio 0.4
```

### Steady-State Filtering Criteria

| Condition | Action |
|-----------|--------|
| Steady-state rows exist (`cleaned_data_steady_only.csv` non-empty) | Use as STATS_INPUT for all Phase 2 analysis |
| No steady-state subset available | Use full data; emit WARNING |
| `steady_state_ratio < min_steady_ratio` (default 0.4) | WARNING: too few steady rows for reliable statistics. Flag in `data_analysis_conclusion.json`. Consider lowering `variance_threshold` or widening window. |

### Per-Product Anomaly-Focused Analysis (MANDATORY CONSTRAINT)

When dataset contains multiple products (group column with 2+ distinct values):
1. Identify `focus_product` — product with highest anomaly rate
2. Isolate this product's rows only
3. Further filter to steady-state rows: `focus_product_rows ∩ steady_row_indices`
4. Re-run correlation, trend, CCF, and time-lag on within-product steady-state rows
5. Compare within-product vs cross-product aggregate correlations
6. If they differ → document as Simpson's Paradox evidence
7. Summarize in `data_analysis_conclusion.json`

**Simpson's Paradox verification**: A parameter with |r_aggregate| > 0.5 but |r_within_product| < 0.2 for every product is a classic Simpson's Paradox case. The aggregate correlation is a product-switch artifact, NOT a causal relationship.

---

## Rule v6.6: Batch Identity Integrity

**Threat**: When batch/lot IDs appear across multiple rows ("split records"), batch-cumulative effects are misread as independent observations. Example: an extreme batch split into scratch=0 and scratch=2757 rows is misdiagnosed as two separate events, inflating apparent dispersion and masking batch-level patterns.

**Applicability**: When a batch/lot ID column exists (detected by column names: `batch_id`, `batch`, `lot`, `lot_id`, `batchno`, `批次`).

**Validation criteria**:
- Detect: any batch_id appearing in ≥2 rows
- For each duplicate batch: merge by time-window aggregation of detection values
- Write `duplicate_batch_report.json` with: dup batch_id, split row count, pre/post-merge comparison
- Annotate in `data_analysis_conclusion.json`
- **NEVER treat split batch rows as independent observations**

**Note**: Batch identity repair is a data-quality FIX, not a cleaning-damage fallback trigger. It does NOT cause raw fallback — it enriches the cleaned data.

---

## Rule v6.7: Correlation Robustness Validation (stats_validate.mjs)

**Script**: `$SKILL_PATH/scripts/stats_validate.mjs` — runs AFTER stats.mjs. Produces `validate_report.json`.

### 1. Simpson's Paradox Detection

**When**: Group column exists (2+ groups).

**Method**: Compute full-dataset r vs within-group weighted-average r. Checks for:
- **direction_reversal**: full r and strata r have opposite signs
- **simpson_paradox**: |full_r - weighted_strata_r| / max(|full_r|, |weighted_strata_r|) > 0.5

**Severity levels**:
- `CRITICAL`: direction_reversal detected
- `SERIOUS`: |full_r| > 0.4 but |weighted_strata_r| < 0.15
- `MODERATE`: r attenuation > 50% between full and strata

### 2. Time Trend Confounding

**When**: Time column exists.

**Method**: Linear detrend both variables, compute detrended r. Compare raw r vs detrended r.

**Criteria**:
- `trend_confounded`: |raw_r - detrended_r| / |raw_r| > 0.4
- `attenuation_pct`: percentage reduction in r after detrending
- Flag pairs where both variables independently trend with time (|x_time_trend_r| > 0.3 AND |y_time_trend_r| > 0.3)

### 3. Outlier Sensitivity

**Method**: IQR-based outlier removal (1.5×IQR), re-compute r.

**Criteria**:
- `outlier_driven`: |clean_r - full_r| / |full_r| > 0.5
- Report: outliers_removed count, outlier_pct, r_change_pct
- `SERIOUS` when >10% of data points are outliers AND r_change_pct > 30%

### 4. Spearman Divergence (Nonlinearity)

**Method**: Compare Pearson r vs Spearman ρ.

**Criteria**:
- `SERIOUS`: |r_pearson - rho_spearman| > 0.3 — outliers dominate Pearson
- `MODERATE`: divergence 0.15–0.3 — possible nonlinearity, check scatter plot

### 5. Change-Point Detection

**When**: Time column exists.

**Method**: Sliding window (window_size = n/3, step = n/30) correlation between variable pairs.

**Criteria**:
- `has_regime_change`: window correlation sign flips from positive to negative (or vice versa)
- `instability_score`: fraction of windows where correlation is unstable

### Overall Validity Verdict

| Condition | Verdict |
|-----------|---------|
| ≥1 CRITICAL Simpson's OR outlier_driven pair | `FATAL — Statistical evidence is unreliable. Root cause claims based on correlation alone are prohibited.` |
| ≥2 SERIOUS trend_confounded pairs | `CONDITIONAL — Correlations require detrended confirmation. Only detrended r may support causal claims.` |
| <2 SERIOUS and 0 CRITICAL | `ROBUST — Statistical evidence passes robustness checks.` |

---

## Cross-Rule Decision Matrix

When multiple rules flag a correlation, apply the STRICTEST downgrade:

| Rule finding | Max causal claim allowed |
|-------------|------------------------|
| Simpson's Paradox CRITICAL (direction reversal) | EXCLUDED from causal evidence |
| Simpson's Paradox SERIOUS OR outlier_driven | "Weak statistical signal — requires within-product confirmation" |
| Trend confounded (attenuation > 50%) | "Trend-artifact — use detrended r only" |
| Lag compensation r_improvement > 30% | "Hidden relationship — use compensated r" |
| Batch identity split detected for this pair | "Batch-aggregated analysis required" |
| All rules pass | Full statistical evidence admissible |
