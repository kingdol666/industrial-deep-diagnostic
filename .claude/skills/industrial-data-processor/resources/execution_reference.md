# Data Processor — Execution Reference

Detailed bash commands, script parameters, and procedural code for each phase. For the checklist overview, see `references/agent-protocol.md`.

---

## Phase 0: Data Understanding

### 0.1 Required Reading

| File | What to extract |
|------|----------------|
| `00_input/input_manifest.json` | Column names, types, value ranges, statistical signatures, categorical columns, time column |
| `00_input/user_context.json` | User's stated process type, known issues, target columns |
| `01_ontology/ontology.json` | **MANDATORY before analysis.** Process stages, equipment, parameter physical meanings, `behavior_match`, `discrepancy_signals` |
| `00_input/rag_deep_understanding.json` | Physics principles, known failure modes, confounders |

### 0.3 Analysis Plan Required Sections

Write `RUN_DIR/02_processed/analysis_plan.md` with:
- Detected data view mode: `process_plus_inspection`, `process_only`, `inspection_only`, or `unknown`, with justification
- What statistical tests make sense for THIS data
- What derived features would be diagnostically useful
- What visualizations would reveal the causal structure
- Product grouping strategy (if applicable)
- Process-side + inspection-side evidence combination strategy
- What you will NOT do (and why)
- `Adaptive Decision Audit` table: EXECUTE / SKIP / NOT_APPLICABLE per candidate analysis
- `Analysis Coverage Matrix`: pure process, dual-drive, grouping/confounding, temporal/regime, scenario-specific

### 0.4 Ontology-Guided Analysis Selection

**Machine-readable output**: `RUN_DIR/02_processed/analysis_parameter_selection.json`

Key fields:
- `parameter_physical_groups`: groupings by process stage, physical domain, causal chain
- `quality_targets`: identified quality/inspection columns
- `analysis_tiers`: tier_1 / tier_2 / tier_3 / pruned with physical justification
- `predictor_cols`: Tier 1+2 parameter column names (plus Tier 3 if justified)
- `exclude_cols`: metadata columns + PRUNED parameters to never feed to analysis
- `derived_features_to_compute`: scenario-specific features from ontology roles

---

## Phase 1: Scenario Classification

### 1.1 Process Physics from Column Patterns

Physical quantity inference:
- Column name tokens: temp, pressure, speed, flow, gap, thickness, tension, current, power, vibration, concentration, pH, humidity, position, angle, force, torque, rpm, frequency, voltage, level, weight, density, viscosity
- Value ranges: 0-150 → likely °C; 0-10 → likely bar; thousands → likely rpm or μm; 0-1 → likely normalized
- Statistical signatures: stationary → setpoint/control; monotonic drift → degradation; cyclic → environmental; step → discrete events

### 1.2 Data Shape Detection Table

| Data characteristic | How to detect | Affects which analysis |
|--------------------|---------------|----------------------|
| Multi-zone sensors | Same prefix, sequential numbering (zone_1 through zone_12) | Spatial profile plots, zone-to-zone differentials, drift localization |
| Paired/in-out sensors | Pairs like inlet_temp/outlet_temp, feed_pressure/die_pressure | Differential calculation, efficiency metrics |
| Hierarchical grouping | Multiple categorical columns with nesting (batch → reel → grade) | Multi-level stratification, variance decomposition |
| Product / lot grouping | Columns like product_no, product_code, product_grade, lot_id, batch_id | Per-product time ordering, within-product trend, between-product confounding checks, product-switch transition |
| Profile/array data | Many columns measuring same quantity at different positions | Profile evolution over time, CD/MD decomposition |
| Event markers | Columns that change value at specific times | Before/after analysis, reset detection |
| Derived/calculated columns | Columns that are formulas from other columns | Identify to avoid circular analysis |

### 1.3 Output

Write `RUN_DIR/02_processed/scenario_classification.json` per `schemas/scenario_classification_schema.json`. Required fields: `scene_type`, `process_category`, `confidence`, `classification_basis`, `ontology_available`, `adaptive_visualization_plan`, `expected_physics`, `degradation_candidates`.

---

## Phase 1.5: Production State Detection (v6.5)

### Run Production Regime Detector

```bash
# Resolve Python via shared uv setup
PYTHON=$(node "$SHARED_PATH/scripts/uv_env_setup.mjs" 2>/dev/null | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const j=JSON.parse(d.trim().split('\\n').pop());process.stdout.write(j.python||'')}catch(e){process.stdout.write('')}})")
"$PYTHON" "$SKILL_PATH/scripts/production_regime_detector.py" "$DATA_PATH" "$RUN_DIR/02_processed" \
  --group-col <primary_group_col_if_exists> \
  --time-col <time_col_if_exists> \
  --window-minutes 10 \
  --variance-threshold 3.0 \
  --min-steady-ratio 0.4
```

Alternative via dp_toolkit:
```bash
"$PYTHON" "$SKILL_PATH/scripts/dp_toolkit.py" regime-filter "$DATA_PATH" "$RUN_DIR/02_processed" \
  --group-col <primary_group_col> --time-col <time_col>
```

### Consume Output

Read `RUN_DIR/02_processed/production_regime_filter.json`:
- `regime_distribution`: steady-state ratio and regime counts
- `steady_row_indices`: filter ALL downstream analysis rows with these
- `filter_recommendation.exclude_regimes`: exclude startup, shutdown, transition rows
- `filter_recommendation.caution_regimes`: flag abnormal, marginal rows
- `per_product_anomaly_analysis.focus_product`: MANDATORY when not null — isolate and deeply analyze
- `per_product_anomaly_analysis.focus_product_directive`: print verbatim

### Steady-State-Only Data Selection

```bash
STEADY_DATA="$RUN_DIR/02_processed/cleaned_data_steady_only.csv"
if [ -s "$STEADY_DATA" ]; then
  STATS_INPUT="$STEADY_DATA"
  echo "[data-processor] Using steady-state subset for analysis: $(wc -l < "$STEADY_DATA") rows"
else
  STATS_INPUT="$DATA_PATH"
  echo "[data-processor] WARNING: No steady-state subset available — using full data"
fi
```

---

## Phase 2: Universal Analysis

### Edge Cases Gate (Check BEFORE Running Scripts)

| Edge case | Detection | Behavior change |
|-----------|-----------|----------------|
| No time column | `input_manifest.json.time_column` is null | Skip CCF, lag analysis, time-derived features. Label as "snapshot/cross-sectional" |
| No group column | No categorical columns with 2-20 unique values | Skip stratified correlation. Simpson's Paradox N/A |
| Product grouping exists | Product/grade/lot/batch categorical column | Group by product first; sort within product by time; compare within-product vs cross-product |
| Single numeric column | Only 1 numeric column besides time/group | Skip correlation matrix. Run only trend and anomaly detection |
| All columns numeric | No categorical/metadata columns | Grouping unavailable. Stratification limited to value-based binning |
| < 50 rows | `input_manifest.json.rows` < 50 | Statistical tests unreliable. Visual inspection + simple trend only. Flag "low data confidence" |
| Process-only data | No true quality/inspection targets | Do not force dual-drive. Pass `--data-view-mode process_only`, leave `--target-cols` empty |
| Multiple products exist | Group column with 2+ distinct values | v6.5 MANDATORY: identify focus product, isolate steady-state rows, within-product analysis |
| Low steady-state ratio | `steady_state_ratio < 0.4` | WARNING: too few steady rows. Flag in conclusion. Consider lowering threshold |
| Production regime data available | `production_regime_filter.json` exists | Use `steady_row_indices` to filter all Phase 2 analysis rows |

### 2.1 Convert Data to JSON

```bash
if [ ! -s "$RUN_DIR/02_processed/data.json" ] || [ "$DATA_PATH" -nt "$RUN_DIR/02_processed/data.json" ]; then
  node "$SHARED_PATH/scripts/convert.mjs" "$DATA_PATH" --output "$RUN_DIR/02_processed/data.json"
fi
```

### 2.2 Preprocess

```bash
PYTHON=$(node "$SHARED_PATH/scripts/uv_env_setup.mjs" 2>/dev/null | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const j=JSON.parse(d.trim().split('\\n').pop());process.stdout.write(j.python||'')}catch(e){process.stdout.write('')}})")
if [ ! -s "$RUN_DIR/02_processed/cleaned_data.csv" ] || [ "$DATA_PATH" -nt "$RUN_DIR/02_processed/cleaned_data.csv" ]; then
  "$PYTHON" "$SKILL_PATH/scripts/dp_toolkit.py" preprocess "$DATA_PATH" "$RUN_DIR/02_processed" --group-col <primary_group_col>
fi
```

Convert cleaned CSV to JSON:
```bash
if [ ! -s "$RUN_DIR/02_processed/cleaned_data.json" ] || [ "$RUN_DIR/02_processed/cleaned_data.csv" -nt "$RUN_DIR/02_processed/cleaned_data.json" ]; then
  node "$SHARED_PATH/scripts/convert.mjs" "$RUN_DIR/02_processed/cleaned_data.csv" --output "$RUN_DIR/02_processed/cleaned_data.json"
fi
```

### Derived Features Based on Data Shape

| Data shape detected | Derived features to add |
|--------------------|------------------------|
| Multi-zone sensors | zone-to-zone differentials, zone range (max-min), zone deviation from baseline, zone drift rate |
| Paired sensors | differential (in-out), efficiency ratio (out/in), log-mean difference |
| Hierarchical groups | per-group centered values (value - group_mean) |
| Product grouping | per-product mean, per-product centered values, per-product volatility (CV), product-switch markers |
| Profile data | CD profile mean/std/skew, edge-center-edge gradient |
| Time-series with events | time-since-last-event, cumulative-time-in-current-regime |

Add features inline with pandas, extending the cleaned CSV.

### 2.2.5 Cleaning Integrity Verification (MANDATORY GATE)

**Four checks** (run inline pandas, write to `data_quality_report.json.cleaning_integrity`):

| Check | Pass condition | Fail action |
|-------|---------------|-------------|
| `row_count_check` | `len(cleaned) ≤ len(raw)`, drop rate < 0.05 | 5-20%: record and continue; >20%: raw fallback |
| `type_integrity` | Numeric columns: `pd.to_numeric(errors='coerce')` success ≥50% | String leak → coerce repair; still <50% → raw fallback |
| `range_fidelity` | Cleaned min/max/mean vs raw: mean relative deviation <10% | >10% deviation → raw fallback |
| `batch_identity_integrity` (v6.6) | No duplicate batch/lot IDs across rows | Merge dup batches, write `duplicate_batch_report.json` |

**Data source decision**:
- Default: `data_source = "cleaned"`, use `cleaned_data.csv`
- Fallback: any check triggers `raw_fallback` when beyond repair threshold → use raw `DATA_PATH`, record `fallback_reason` + `repair_attempts`
- In-place repair (e.g., string-to-numeric coercion) → keep cleaned, record in `repair_attempts`
- All Phase 2.3+ analysis and Phase 5 plotting reads from `cleaning_integrity.data_source`

Reference implementation — inline pandas:

```python
import pandas as pd, json
raw = pd.read_csv(DATA_PATH)
cleaned = pd.read_csv(f"{RUN_DIR}/02_processed/cleaned_data.csv")
numeric_cols = [...]  # from ontology/input_manifest

# 1. row count
dropped = len(raw) - len(cleaned)
row_check = {"raw_rows": len(raw), "cleaned_rows": len(cleaned),
             "dropped": dropped, "drop_rate": round(dropped/len(raw), 4)}

# 2. type integrity
type_issues = {}
for c in numeric_cols:
    if c not in cleaned.columns: continue
    if cleaned[c].dtype not in ("float64", "int64"):
        coerced = pd.to_numeric(cleaned[c], errors="coerce")
        ok_rate = coerced.notna().mean()
        if ok_rate >= 0.5:
            cleaned[c] = coerced
            type_issues[c] = {"leaked": True, "repaired": True, "stray_tokens_sample": cleaned[c].isna().sum()}
        else:
            type_issues[c] = {"leaked": True, "repaired": False, "ok_rate": round(ok_rate, 3)}

# 3. range fidelity
range_drift = {}
for c in numeric_cols:
    if c in cleaned.columns and cleaned[c].dtype in ("float64", "int64") and c in raw.columns:
        raw_n = pd.to_numeric(raw[c], errors="coerce")
        rel = abs(cleaned[c].mean() - raw_n.mean()) / (abs(raw_n.mean()) + 1e-9)
        range_drift[c] = round(float(rel), 4)

# 4. batch identity integrity
batch_cols = [c for c in cleaned.columns if str(c).lower() in ("batch_id","batch","lot","lot_id","batchno","批次")]
batch_dup = {"applicable": False, "id_col": None, "duplicate_batches": [], "split_record_count": 0, "action": "none"}
if batch_cols:
    bid = batch_cols[0]
    vc = cleaned[bid].astype(str).value_counts()
    dups = vc[vc > 1].index.tolist()
    batch_dup = {"applicable": True, "id_col": bid, "duplicate_batches": dups,
                 "split_record_count": int(vc[vc > 1].sum() - len(dups)),
                 "action": "merge_or_flag" if dups else "none"}
    if dups:
        dup_rows = cleaned[cleaned[bid].astype(str).isin(dups)].sort_values(bid)
        dup_rows.to_csv(f"{RUN_DIR}/02_processed/duplicate_batch_report.csv", index=False)

# decision
trigger_fallback = (row_check["drop_rate"] > 0.20 or
                    any(v["leaked"] and not v["repaired"] for v in type_issues.values()) or
                    any(v > 0.10 for v in range_drift.values()))
result = {"row_count_check": row_check, "type_integrity": type_issues, "range_fidelity": range_drift,
          "batch_identity_integrity": batch_dup,
          "data_source": "raw_fallback" if trigger_fallback else "cleaned",
          "repair_attempts": [], "fallback_reason": None}
```

### 2.3 Unified Statistical Analysis & Validation (v7.0 merged pipeline)

**Single entry point** replaces the old `stats.mjs` / `stats_analysis.py` / `stats_validate.mjs` trio.
The pipeline runs correlation analysis, anti-spurious validation, and batch integrity checks in one pass.

**Before running**: Read `analysis_parameter_selection.json` from Phase 0.4. Extract `predictor_cols` and `exclude_cols`. Do NOT feed all numeric columns.

Read Phase 0.4 selection:
```bash
if [ -f "$RUN_DIR/02_processed/analysis_parameter_selection.json" ]; then
  PREDICTOR_COLS=$(node -e "const j=JSON.parse(require('fs').readFileSync('$RUN_DIR/02_processed/analysis_parameter_selection.json','utf-8')); process.stdout.write((j.predictor_cols||[]).join(','))")
  EXCLUDE_COLS=$(node -e "const j=JSON.parse(require('fs').readFileSync('$RUN_DIR/02_processed/analysis_parameter_selection.json','utf-8')); process.stdout.write((j.exclude_cols||[]).join(','))")
  QUALITY_COLS=$(node -e "const j=JSON.parse(require('fs').readFileSync('$RUN_DIR/02_processed/analysis_parameter_selection.json','utf-8')); process.stdout.write((j.quality_targets||[]).join(','))")
  echo "[data-processor] Phase 0.4 selection: predictors=${PREDICTOR_COLS}, excluded=${EXCLUDE_COLS}, targets=${QUALITY_COLS}"
else
  echo "[data-processor] WARNING: analysis_parameter_selection.json not found — Phase 0.4 was skipped. All numeric columns will be analyzed."
  PREDICTOR_COLS=""
  EXCLUDE_COLS=""
  QUALITY_COLS=""
fi
```

Build args and run unified pipeline:
```bash
PREDICTOR_ARG=""
[ -n "$PREDICTOR_COLS" ] && PREDICTOR_ARG="--predictor-cols $PREDICTOR_COLS"
EXCLUDE_ARG=""
[ -n "$EXCLUDE_COLS" ] && EXCLUDE_ARG="--exclude-cols $EXCLUDE_COLS"

"$PYTHON" "$SKILL_PATH/scripts/stats/run.py" --run-dir "$RUN_DIR" --mode full \
  --target-cols "$QUALITY_COLS" $PREDICTOR_ARG $EXCLUDE_ARG \
  --group-col <group_col> --time-col <time_col> \
  --max-lag 20 --alpha 0.05 \
  --data-view-mode <process_plus_inspection|process_only|inspection_only|unknown>
```

This single command produces:
- Correlation analysis (Pearson, Spearman, detrended, CCF, MI, Granger, stratified)
- Anti-spurious validation (Simpson's Paradox, outlier sensitivity, leave-one-out leverage,
  trend confounding, change-point detection, Pearson-Spearman divergence, distribution check)
- Batch integrity check (duplicate batch ID detection)
- Output: `RUN_DIR/02_processed/validate_report.json`

See `resources/anti_spurious_rules.md` for detailed validation criteria (v6.4–v6.7).

### 2.5 Anomaly Detection

```bash
if [ ! -s "$RUN_DIR/02_processed/anomaly_report.json" ] || [ "$RUN_DIR/02_processed/cleaned_data.json" -nt "$RUN_DIR/02_processed/anomaly_report.json" ]; then
  "$PYTHON" "$SKILL_PATH/scripts/dp_toolkit.py" anomaly "$RUN_DIR/02_processed/cleaned_data.json" "$RUN_DIR/02_processed" \
    --data-view-mode <process_plus_inspection|process_only|inspection_only|unknown> \
    --target-cols <quality_cols_comma_separated> \
    --process-cols <process_cols_comma_separated> \
    --group-col <group_col>
fi
```

### 2.6 Time-Lag Auto-Compensation (v6.4)

```bash
if [ -f "$RUN_DIR/01_ontology/ontology.json" ] && [ -f "$RUN_DIR/02_processed/feature_summary.json" ]; then
  TIME_COL=$(node -e "const j=JSON.parse(require('fs').readFileSync('$RUN_DIR/00_input/input_manifest.json','utf-8')); process.stdout.write(j.time_column||'')")
  if [ -n "$TIME_COL" ]; then
    node "$SKILL_PATH/scripts/time_lag_compensator.mjs" \
      "$RUN_DIR/02_processed/feature_summary.json" \
      --ontology "$RUN_DIR/01_ontology/ontology.json" \
      --time-col "$TIME_COL" \
      --max-lag 30 \
      > "$RUN_DIR/02_processed/time_lag_analysis.json"
    echo "[data-processor] v6.4 Time-lag compensation complete → time_lag_analysis.json"
  else
    echo "[data-processor] No time column — time-lag compensation not applicable"
  fi
else
  echo "[data-processor] Skipping time-lag compensation — missing ontology or feature_summary"
fi
```

### 2.7 Baseline Result Review

Document in `analysis_plan.md` under "Baseline Script Findings and Gaps". Review each artifact:

| Baseline artifact | Expert question |
|------------------|-----------------|
| `feature_summary.json` | Which relationships are statistically strong, and which are suspicious or likely confounded? |
| `validate_report.json` | Which correlations cannot be trusted because of Simpson's Paradox, trend confounding, sorting, outliers, or regime shifts? |
| `anomaly_report.json` | Which parameters or quality targets actually show abnormal intervals, transitions, or product-specific behavior? |
| `physics_check.json` | Which mechanisms are physically plausible, impossible, negligible, or still untested? |
| `ontology.json` | Which findings match or contradict the ontology's expected physics? |

### Expert Gap Analysis

After fixed scripts, ask:
1. What evidence would a human process engineer still ask for?
2. Which important plot or metric is missing from the fixed toolkit?
3. Which ontology-predicted mechanism has not been tested yet?
4. Which RAG claim needs custom validation?
5. Which data structure demands a scenario-specific script?
6. If process_only: which process-health questions remain unanswered?

If fixed scripts already answer all questions, set `custom_scripts_written=false` with justification. Otherwise, write focused Python scripts under `RUN_DIR/06_scripts/`.

---

## Phase 3: Scenario-Specific Deep Analysis

### 3.2 Automated Physics Checks

```bash
PHYSICS_OUTPUT="$RUN_DIR/02_processed/physics_check.json"

"$PYTHON" "$SKILL_PATH/scripts/physics_check.py" "$RUN_DIR" \
  "$RUN_DIR/01_ontology/ontology.json" \
  "$RUN_DIR/02_processed/feature_summary.json" \
  "$RUN_DIR/02_processed/anomaly_report.json" \
  --output "$PHYSICS_OUTPUT" \
  --cleaned-data "$RUN_DIR/02_processed/cleaned_data.json" \
  --quality-targets <quality_cols> --candidate-params <process_cols> \
  --temp-col <best_temp_col> --dev-col <best_dev_col>
```

Check `checks_performed`. If 0 and no inspection targets exist, that is valid for process_only data — document reason. Otherwise, proceed to manual L1-L5 verification.

### 3.3 Merge Physics Results into Anomaly Report

```bash
if [ -f "$PHYSICS_OUTPUT" ]; then
  node -e "
    const fs = require('fs');
    const anomaly = JSON.parse(fs.readFileSync('$RUN_DIR/02_processed/anomaly_report.json', 'utf-8'));
    const physics = JSON.parse(fs.readFileSync('$PHYSICS_OUTPUT', 'utf-8'));
    anomaly.quality_reset_analysis = physics.physical_checks.quality_reset_analysis || null;
    anomaly.anomaly_onset_coincidence = physics.physical_checks.anomaly_onset_coincidence || [];
    anomaly.physical_checks = {};
    for (const [k, v] of Object.entries(physics.physical_checks || {})) {
      if (!['quality_reset_analysis', 'anomaly_onset_coincidence'].includes(k)) {
        anomaly.physical_checks[k] = v;
      }
    }
    fs.writeFileSync('$RUN_DIR/02_processed/anomaly_report.json', JSON.stringify(anomaly, null, 2));
  "
fi
```

### 3.4 Dual-Drive Diagnostic Layer

When both process and inspection data exist, build two-sided diagnostic statements:
- **Process side**: Which parameters showed abnormal fluctuation, drift, regime switch, threshold crossing?
- **Inspection side**: Which quality metrics showed anomaly intervals, reset behavior, excursions?
- **Linkage**: Did they occur in the same product group, same time window, or plausible causal order?

At minimum, outputs must enable the Diagnostician to answer:
1. Which product group showed significant process parameter anomalies?
2. Which inspection metric was abnormal in the same group?
3. Are they synchronous, sequential, or group-level co-occurrence?
4. Is this more like "internal process instability" or "product formulation/switching artifact"?

### 3.5 Data Analysis Conclusion

Write `RUN_DIR/02_processed/data_analysis_conclusion.json` per `schemas/data_analysis_conclusion_schema.json` and `templates/data_analysis_conclusion_template.json`.

Must contain:
- Which fixed scripts ran and what they found
- Which custom scripts were written and why
- Custom artifacts/figures generated
- How ontology changes interpretation of raw statistics
- Adaptive decision audit with justification
- Analysis coverage matrix
- Data-supported conclusions with caveats
- Priority hypothesis inputs for Diagnostician
- Data cleaning provenance (`data_cleaning_provenance`) with `cleaning_operations`, each with `rationale`

Deployable workflow helpers:
```bash
node "$SKILL_PATH/scripts/data-processor-finalize.mjs" "$RUN_DIR"
```

---

## Phase 4: RAG Knowledge Validation

If `RUN_DIR/00_input/rag_deep_understanding.json` exists with `validation_queue`:
- Temporal validation: CCF from feature_summary to check X precedes Y
- Stratified validation: correlation within each group
- Detrended validation: raw r vs detrended r; flag attenuation > 50%
- Functional form validation: data follows claimed equation shape?

Output: `RUN_DIR/02_processed/rag_validation_report.json`

---

## Phase 5: Visualization

### 5.0 Product Split Strategy (MANDATORY before any plot)

If product group column exists with multiple values:
1. Split data by product, analyze each independently
2. Read `focus_product` from `production_regime_filter.json`
3. If `focus_product` is null: use highest anomaly rate from `anomaly_report.json.dual_drive_analysis.per_product_analysis`
4. Focus product first, then remaining products

### 5.1 Per-Product Time-Aligned Overlays (HIGHEST PRIORITY)

```bash
"$PYTHON" "$SKILL_PATH/scripts/visual_analysis.py" "$RUN_DIR" \
  --target-cols <quality_cols_comma_separated> \
  --key-params <ALL_process_params_comma_separated> \
  --group-col <group_col>
```

`--key-params` must include ALL process parameters, not just top 8. `visual_analysis.py` handles grouping and sub-figure splitting.

**Layout strategy**:
- ≤12 params: single figure per product
- >12 params: split by process stage from ontology, ≤12 lines per sub-figure
- Every sub-figure includes ALL quality targets (★ black thick lines)

### Chart Standards (Mandatory)

| Standard | Requirement | Anti-pattern |
|----------|------------|-------------|
| Data truth | All points/lines/annotations from actual `data_source` values | Smooth curves replacing real data fluctuations |
| Axis labels | Physical meaning + units (e.g., "Temperature (°C)") | "X", "Y", "Value" |
| Legend clarity | Parameter physical names from ontology, not raw column names | `COL_TEMP_01` |
| Statistical annotation | Scatter plots: r, p-value, n | "Significant correlation" without numbers |
| Anomaly interval marking | Semi-transparent red background with timestamps | Anomalies only in text |
| Color accessibility | Viridis/plasma/tab10, distinguishable with color blindness | Red-green only |
| Font size | Text ≥10pt, titles ≥14pt | 8pt labels |
| Event markers | Red dashed vertical lines with text labels | Events with timestamps only |
| Resolution | ≥150 DPI, 300 DPI for key diagnostic charts | 72 DPI |

### VLM Design Principle

Design every chart so a VLM Agent can read it:
- Shared time axis across time-series overlays
- z-score normalization for different-unit comparison
- Negative-correlation parameters reversed (all lines move same direction when healthy)
- Event markers: red dashed lines with bold labels
- Anomaly intervals: red semi-transparent shading
- Large fonts (≥12pt), high contrast, clean layout
- Legend with direction annotations

See `resources/visual_analysis_framework.md` for full VLM chart design guide.

### 5.2–5.4 Supplementary Charts

- **5.2**: Per-quality-target temporal alignment with top-3 most correlated parameters
- **5.3**: Top-parameter scatter grid colored by group column, per-group regression lines
- **5.4**: Correlation robustness bar chart: raw r vs detrended r vs Spearman ρ for top-15 pairs

### 5.5 VLM-Specific Supplementary Charts

| Chart | Design feature | What VLM reads |
|-------|---------------|----------------|
| Per-product temporal overlay | ALL params + quality on shared time axis, z-score normalized, direction-aligned | Synchronous groups, temporal precedence, event responses, drift patterns |
| Event response | Before/after coloring, mean lines, transition marker | Quality resets at events, jump magnitude, recovery completeness |
| Simpson Paradox | Per-stratum subplots with regression lines, direction arrows | Direction reversal across strata, r-value contrast |
| Synchronization heatmap | Rolling correlation over time, threshold lines | Correlation stability vs time-variation, breakdown timing |

### 5.6 Scenario-Specific Plots

Generate ONLY matching data patterns:

| Data pattern | Plots |
|-------------|-------|
| Multi-zone sensors | Spatial profile at t=0/mid/end; Zone drift bar chart; Zone correlation heatmap |
| Paired sensors | Inlet vs outlet overlaid; Differential trend; Efficiency metric over time |
| Event markers | Quality before/after box plots per event; Event-aligned average trajectory; Cumulative degradation between events |
| Grouping columns | Per-group correlation bar chart; Variance decomposition pie/donut |
| Product grouping + time | Per-product grouped timeline; Product-switch timeline; Process fluctuation by product bar |
| Monotonic drift | Degradation curve with LOWESS fit and critical threshold marker |
| Cyclic patterns | FFT periodogram; Phase-averaged quality by cycle position |
| Nonlinear relationships | Scatter with piecewise linear fit and breakpoint marker; Regime-separated correlation panels |
| Hierarchical groups | Multi-panel scatter, one panel per group, shared axes, separate regression lines |

### 5.7 Causal Evidence Map

Always generate. Python script that:
1. Reads feature_summary for all correlations
2. Reads validate_report to filter out Simpson/trend-confounded/outlier-driven pairs
3. Draws nodes (parameters, targets) and edges (validated correlations, colored by strength, labeled with r)
4. Marks root cause candidates (nodes connecting to multiple quality targets)

Output: `02_processed/causal_evidence_map.json` + `03_figures/fig_causal_map.png`

### 5.8 Visualization Execution

Universal plots + causal map:
```bash
"$PYTHON" "$SKILL_PATH/scripts/dp_toolkit.py" visualize \
  "$RUN_DIR/02_processed/cleaned_data.json" \
  "$RUN_DIR/02_processed/feature_summary.json" \
  "$RUN_DIR/02_processed/anomaly_report.json" \
  "$RUN_DIR/03_figures" \
  --target-cols <quality_cols> --key-params <top_params> --group-col <group_col> \
  --data-view-mode <process_plus_inspection|process_only|inspection_only|unknown>
```

Scenario-specific plots:
```bash
"$PYTHON" "$RUN_DIR/06_scripts/scenario_plots.py"
```

### 5.9 Post-Generation Verification Gate (MANDATORY)

| # | Check | Pass condition | Fail action |
|---|-------|---------------|-------------|
| 1 | `plot_manifest.json` non-empty | ≥1 plot entry, each `path` points to existing PNG | Rerun visual_analysis.py / scenario_plots.py |
| 2 | PNG non-placeholder | Each PNG > 5KB | Check matplotlib errors, redraw |
| 3 | Real data coverage | Claimed parameters are numeric in `data_source` | Data issue — return to Phase 2.2.5 |
| 4 | ABORT handling | `visual_analysis.py` did not abort with "zero numeric columns" | Fix data first (string-type recast / raw fallback), then rerun. NEVER skip plotting |

Quick gate check:
```bash
"$PYTHON" - << 'PY'
import json, os
pm = json.load(open(f"{RUN_DIR}/03_figures/plot_manifest.json"))
plots = pm.get("plots", [])
assert plots, "ABORT: plot_manifest empty — regenerate before VLM"
for p in plots:
    path = p.get("path","")
    assert os.path.exists(path) and os.path.getsize(path) > 5120, f"ABORT: {path} missing or empty"
print(f"Gate OK: {len(plots)} verified plots")
PY
```

---

## Phase 5.5: VLM Visual Analysis

**Now a separate pipeline step (Step 3.5).** data-processor does NOT launch vlm-visual-analyzer. The main agent launches it independently after data-processor completes.

---

## Phase 6: Stabilize

### 6.1 Write Plot Manifest and Captions

```bash
if [ ! -s "$RUN_DIR/03_figures/image_captions.json" ]; then
  node "$SKILL_PATH/scripts/generate_captions.mjs" "$RUN_DIR" 2>&1 || echo "Captions generation skipped — writing manually"
else
  echo "image_captions.json already exists — preserve VLM-generated captions"
fi
```

If `image_captions.json` exists from vlm-visual-analyzer, preserve and validate. Otherwise use `generate_captions.mjs`. If script fails, write manually. Each entry MUST include:
- `key_observations`: 3-5 bullets with ACTUAL NUMBERS (r values, threshold values, anomaly counts, drift rates)
- `diagnostic_implication`: one sentence explaining what this plot tells the Diagnostician

### 6.2 Output Contract — Required Files

```
02_processed/analysis_plan.md
02_processed/analysis_parameter_selection.json
02_processed/data_analysis_conclusion.json
02_processed/data.json
02_processed/cleaned_data.csv / cleaned_data.json
02_processed/data_quality_report.json          ← includes cleaning_integrity
02_processed/scenario_classification.json
02_processed/feature_summary.json
02_processed/validate_report.json
02_processed/anomaly_report.json               ← merged with physics
02_processed/physics_check.json
02_processed/causal_evidence_map.json
02_processed/rag_validation_report.json        ← if RAG claims exist
02_processed/zone_analysis.json                ← if multi-zone sensors
02_processed/event_analysis.json               ← if event markers
02_processed/physics_manual_verification.md    ← if physics_check ran 0 checks
02_processed/*_analysis.json                   ← custom expert script artifacts
03_figures/*.png
03_figures/fig_vlm_temporal_overlay*.png       ← at least one when time column exists
03_figures/plot_manifest.json
03_figures/visual_analysis.json                ← from Step 3.5 vlm-visual-analyzer
03_figures/image_captions.json
06_scripts/scenario_plots.py
06_scripts/expert_analysis.py                  ← if custom analysis needed
06_scripts/ontology_validation.py              ← if ontology validation needed
```

### 6.3 Pipeline Events

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_start --agent data-processor
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_complete --agent data-processor --files 02_processed/anomaly_report.json,02_processed/data_analysis_conclusion.json,03_figures/plot_manifest.json
```

---

## dp_toolkit.py Command Reference

| Command | Purpose |
|---------|---------|
| `preprocess` | Data cleaning + quality report generation |
| `regime-filter` | Production state detection & steady-state filtering (wrapper for production_regime_detector.py) |
| `anomaly` | Dual-drive anomaly detection |
| `visualize` | Universal plots + causal evidence map generation |

All commands accept `--data-view-mode` (one of: `process_plus_inspection`, `process_only`, `inspection_only`, `unknown`).

---

## Custom Script Template

Requirements for any script under `06_scripts/`:
- Read from `02_processed/cleaned_data.csv` or `cleaned_data.json`
- Read `01_ontology/ontology.json` when physical meaning matters
- Write deterministic outputs with stable filenames
- Avoid hardcoding example-specific columns unless justified in `analysis_plan.md`
- Use only pandas, numpy, matplotlib unless another package is genuinely required

Recommended names:
- `expert_analysis.py` — scenario-specific data analysis
- `scenario_plots.py` — scenario-specific visualization
- `ontology_validation.py` — testing ontology-predicted behavior
