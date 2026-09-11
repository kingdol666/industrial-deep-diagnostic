# Report Reviewer — Detailed Execution Reference

## Step 0: Ensure Python Dependencies (uv venv)

```bash
PYTHON=$(node "$SHARED_PATH/scripts/uv_env_setup.mjs" 2>/dev/null | node -e "
  let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{
    try{const j=JSON.parse(d.split('\n').pop());process.stdout.write(j.python||'')}catch{process.stdout.write('')}
  })
")
if [ -z "$PYTHON" ] || ! "$PYTHON" -c "import matplotlib, numpy, pandas" 2>/dev/null; then
  VENV_PY="$SHARED_PATH/scripts/.venv/bin/python"
  if [ -f "$VENV_PY" ] && "$VENV_PY" -c "import matplotlib, numpy, pandas" 2>/dev/null; then
    PYTHON="$VENV_PY"
  else
    echo "[WARNING] No Python environment available — will skip independent verification and rely on pipeline summaries"
    PYTHON=""
  fi
fi
```

If Python is NOT available (`$PYTHON` is empty), skip Step 2 (Independent Statistical Checks) but continue with all other steps.

## Step 0.5: Load Resources

Read from SKILL_PATH:
- `resources/evidence_rules.md`
- `resources/diagnosis_method.md`
- `resources/process_knowledge_base.md`

Read from RUN_DIR (required for final mode; pre-report skips report.md):
- `report.md` — The report to audit (required only in final mode)
- `04_diagnostics/diagnosis.json` — Structured diagnosis
- `04_diagnostics/evidence.json` — Evidence chains
- `04_diagnostics/confidence.json` — Confidence assessment
- `04_diagnostics/reasoning_chain.json` — Full CoT reasoning trace
- `00_input/rag_deep_understanding.json` — Physics principles, validated claims, confounders
- `02_processed/rag_validation_report.json` — Stage 2 thorough RAG validation (if exists)
- `02_processed/feature_summary.json` — Pearson, Spearman, detrended, CCF
- `02_processed/validate_report.json` — Statistical validation report (primary verification tool)
- `01_ontology/ontology.json` — Process ontology
- `02_processed/analysis_plan.md` — Data-processor's analysis rationale (if exists)
- `02_processed/zone_analysis.json` — Per-zone drift localization (if multi-zone)
- `02_processed/event_analysis.json` — Quality reset classifications (if event markers)
- `02_processed/physics_manual_verification.md` — Manual L1-L5 derivations
- `03_figures/plot_manifest.json` — Visualization manifest

**Read the ACTUAL DATA** (via inspect.mjs or direct CSV reading) — do not rely solely on the pipeline's summary statistics.

In final mode, if `05_review/optimizer_preflight.md` exists, read it first and reuse already-verified findings.

## Step 1: Physical Mechanism Verification (THE CORE)

### 1.1 Mechanism Chain Construction

For the primary diagnosis, answer:

| Check | Question | What to verify |
|-------|----------|---------------|
| Physical plausibility | Does the proposed mechanism actually produce the observed symptoms? | Check against known physics/chemistry |
| **Magnitude match** | **Is the magnitude of effect plausible given the magnitude of cause?** | **Use Arrhenius kinetics, thermal expansion, etc.** |
| Timescale match | Does the degradation timeline match known physics? | Compare half-lives at process temperature vs claim timescale |
| Symptom completeness | Does the mechanism explain ALL observed symptoms? | List every abnormal observation and check |
| Missing symptom check | Would the mechanism produce symptoms NOT observed? | If yes → why aren't they seen? |

### 1.2 Domain-Specific Quantitative Verification

**How to verify any claim quantitatively:**

1. **Identify the governing physics**: Thermal (ΔL = α×L₀×ΔT), Kinetics (Arrhenius), Fluid (Darcy/Bernoulli), Mechanical (Hooke's), Mass transfer (Fick's), Electrical (Ohm's)
2. **Estimate the expected magnitude**: Plug actual data values into the equation
3. **Verify timescale consistency**: Compare claimed rate against known physics
4. **Symptom completeness check**: Does mechanism explain ALL observed symptoms?
5. **Missing symptom check**: Would mechanism produce effects NOT observed?
6. **Use whatever domain knowledge you have** — derive from first principles if needed

### 1.3 Parameter Physical Meaning Verification

For EVERY parameter claimed as a key predictor:
1. What is the physical quantity? (temperature, pressure, speed, position, power?)
2. What is the measurement location? (before/after process step, at equipment or at product?)
3. Is the claimed mechanism consistent with the parameter's actual physical role?

**If a parameter's physical meaning is unknown**: Flag it, reduce confidence ceiling.

### 1.1b RAG Knowledge Cross-Check

Cross-check diagnosis against `rag_deep_understanding.json`:
1. **Physics Principle Alignment**: Does diagnosis align with extracted physics principles?
2. **Failure Mode Consistency**: Does diagnosis match known failure modes?
3. **Confounder Coverage**: Are key confounders addressed?
4. **Validated Claim Usage**: If diagnosis relies on CONTRADICTED claims → **FATAL**
5. **Domain Constraint Violation**: Does mechanism violate domain constraints?

If `rag_validation_report.json` exists:
6. **PARTIALLY_VALIDATED claims**: Does diagnosis acknowledge partial validation?
7. **CONTRADICTED claims**: Any used as primary evidence? → **FATAL** if yes

## Step 1.2: Reasoning Chain Audit — Hallucination Detection

### 1.2.1 Pattern Detection

Scan the reasoning chain for these hallucination red flags:

| Pattern | Indicator | Action |
|---------|-----------|--------|
| Vague quantification | "high correlation" without numbers | Verify exact r values |
| Unanchored inference | Observation→conclusion without intermediate reasoning | Check mechanism links |
| Missing alternative | Hypothesis with no alternatives | Ensure `alternatives_considered` non-empty |
| Unfalsifiable conclusion | `falsification_condition` empty or "none" | Flag as **BLOCKING** |
| Evidence rank inflation | Rank 3 should be Rank 5, [OBSERVED] should be [INFERRED] | Verify against data sources |
| Confidence overstatement | Confidence > 80 when >3 links are [INFERRED] | Flag as overconfident |
| Ignored contradiction | Validation flags unreliable correlation, reasoning still uses it | Flag as **BLOCKING** |
| Regime blindness | Change points detected but entire dataset treated as one regime | Flag as caveat |

### 1.2.2 Spot-Check Protocol

Randomly select 3 conclusions and trace BACK through reasoning chain:
1. Find conclusion in `diagnosis.json`
2. Trace to evidence in `reasoning_chain.json`
3. Verify evidence: real data, correctly ranked, properly tagged [OBSERVED]/[INFERRED]
4. Check uncertainty bounds are reasonable

If ANY of 3 spot-checks fail → **BLOCKING ISSUE**

### 1.2.3 Logical Gap Detection

- Input → Output gap: Does output logically follow from step's inputs?
- Assumption hidden as fact: Flag as [UNSTATED_ASSUMPTION]
- Circular reasoning: Flag as **BLOCKING**

### 1.2.4 Uncertainty Integrity Check

- Is `overall_confidence_ceiling` justified by `epistemic_gaps`?
- Are `aleatory_limits` genuinely irreducible?
- Does `what_would_change_conclusions` list SPECIFIC, ACTIONABLE next steps?
- If uncertainty is trivialized → flag as overconfident

## Step 2: Confounding Variable Detection — WITH INDEPENDENT VERIFICATION

### 2.1 Run Independent Statistical Checks

Read the data-processor's cleaning decision first (do NOT independently re-decide cleaned vs raw):

```python
import pandas as pd, numpy as np, os, json

# Respect data-processor's cleaning decision
_dqr_path = os.path.join(RUN_DIR, "02_processed", "data_quality_report.json")
_authoritative_source = "cleaned"
if os.path.exists(_dqr_path):
    _ci = json.load(open(_dqr_path)).get("cleaning_integrity", {})
    _authoritative_source = _ci.get("data_source", "cleaned")
    if _authoritative_source == "raw_fallback":
        print(f"NOTE: data-processor flagged raw_fallback — use RAW")

cleaned_csv = os.path.join(RUN_DIR, "02_processed", "cleaned_data.csv")
if _authoritative_source == "raw_fallback":
    df = pd.read_csv(DATA_PATH)
    df_raw = df
elif os.path.exists(cleaned_csv):
    df = pd.read_csv(cleaned_csv)
    df_raw = pd.read_csv(DATA_PATH)
else:
    df = pd.read_csv(DATA_PATH)
    df_raw = df

# Compare cleaned vs raw
if 'df_raw' in dir() and len(df) != len(df_raw):
    print(f"NOTE: Cleaned {len(df)} rows vs raw {len(df_raw)} rows")

# Derive column roles from ontology.json (not hardcoded names)
ontology_path = os.path.join(RUN_DIR, "01_ontology", "ontology.json")
if os.path.exists(ontology_path):
    ontology = json.load(open(ontology_path))
    signals = ontology.get("signals", {})
    targets = [p.get("column", "") for p in signals.get("inspection_signals", [])]
    predictors = [p.get("column", "") for p in signals.get("process_parameters", [])]
    control_cols = [p.get("column", "") for p in signals.get("control_variables", [])]
    meta = signals.get("metadata_columns", [])
    group_cols = [m.get("column", "") for m in meta if m.get("role") in ("product_code", "batch_id")]
else:
    cat_cols = [c for c in df.columns if df[c].dtype == 'object' and df[c].nunique() < 20]
    targets = [c for c in df.columns if df[c].dtype in ('float64', 'int64')][-4:]
    predictors = [c for c in df.columns if df[c].dtype in ('float64', 'int64') and c not in targets][:10]
    group_cols = cat_cols[:2]

time_col = next((c for c in df.columns if 'time' in c.lower() or 'ts_' in c.lower()), None)

# 1. Check within-group correlations (Simpson's Paradox)
for group_col in group_cols[:3]:
    for group_val in df[group_col].unique()[:5]:
        subset = df[df[group_col] == group_val]
        # Compare within-group r vs full-dataset r for key pairs

# 2. Check detrended correlations for key pairs
# 3. Check data sorting for CCF validity
```

### 2.2-2.7: Additional Verification Steps

Document Simpson's Paradox, trend confounding, sorting issues, outlier-driven correlations, and data quality concerns in the optimizer output.

## Output

- Final mode: `RUN_DIR/optimizer.md` with verdict ENDORSED/CONDITIONAL/REJECTED
- Pre-report mode: `RUN_DIR/05_review/optimizer_preflight.md` with verdict PREFLIGHT_PASS/NEEDS_REPAIR/BLOCKED

Include concrete `repair_instruction` items when repair is needed.
