# Physics Verification Rules

Detailed rules for the five-item per-relationship physics verification.

## 1. Direction Verification

Compares statistical slope sign against physics prediction from the ontology.

### Rules

1. If `ontology.data_direction_validated == "untested"` → `UNTESTED`
2. If no detectable linear relationship with statistical significance → `UNTESTED`
3. If `ontology.data_direction_validated == "false"` → `MISMATCH` (ontology explicitly flags physics contradiction)
4. If `ontology.data_direction_validated == "true"`:
   - Stat sign matches ontology-governed expected sign → `MATCH`
   - Stat sign opposite → `MISMATCH`

### Key Physics Priors

| Relationship Type | Expected Sign | Physics Basis |
|---|---|---|
| Temperature → reaction rate | Positive | Arrhenius: k = A·exp(-Ea/RT) |
| Reactant concentration → rate | Positive | Mass action law |
| Feed rate → residence time | Negative | τ = V/Q |
| Pressure → gas-phase concentration | Positive | Henry's Law / ideal gas |
| Inhibitor → activity | Negative | Activity suppression |

## 2. Functional Form Verification

Compares data form_match from deep_data_analysis against ontology.predicted_functional_form.

### Form Match Categories

| Ontology Form | Accepts Data Forms Containing |
|---|---|
| `exponential` | exponential, exp |
| `linear` | linear |
| `monotonic` | monotonic, linear, "consistent with linear" |
| `inverse` | inverse, hyperbolic |
| `threshold` | threshold, step |
| `delayed_response` | delayed, lag, nonlinear |

### Verdicts

- Data form string contains a recognized alias → `MATCH`
- Data form explicitly contradicts ontology → `MISMATCH`
- Data form indeterminate ("no detectable", "insufficient") → `UNTESTED`
- No ontology predicted_form → `UNTESTED`

## 3. Time Lag Verification

Compares statistical lag detection results against ontology time delay predictions.

### Lag Agreement Levels

| Ontology lag_agreement | Meaning | Default Verdict |
|---|---|---|
| `consistent` | Ontology already confirmed lag alignment | `MATCH` |
| `no_physics_prior` | No physics-based lag test performed | Check significance |
| `(manual)` | Manually determined | `MATCH` if manual detection |

### Lag Significance Logic

- `lag_significant=true` on a `no_physics_prior` relationship → `MISMATCH` (unexpected lag found)
- `lag_significant=false` with "近实时" ontology → `MATCH`
- Global r ≈ 0 with "长滞后" ontology → `MATCH` (expected)
- Global r significant with "长滞后" ontology → `MISMATCH` (contradicts)

## 4. Magnitude Verification

First-principles order-of-magnitude check.

### Plausibility Assessment

| Condition | Verdict |
|---|---|
| Direction contradicts physics | `IMPLAUSIBLE` |
| \|r\| > 0.6 AND physics-consistent | `STRONG` |
| \|r\| > 0.3 AND physics-consistent | `PLAUSIBLE` |
| Operability = CONFOUNDED/ENDOGENOUS | `IMPLAUSIBLE` |
| No governing_equation | `UNTESTED` |
| Otherwise | `PLAUSIBLE` |

## 5. State Dependence Verification

Checks per_group and per_regime variation for non-stationary behavior.

### State Dependence Levels

| Condition | Verdict |
|---|---|
| Direction sign reverses across groups | `REVERSES` |
| Effect vanishes in some groups (r≈0) | `STATE_DEPENDENT` |
| Magnitude varies >50% across states | `STATE_DEPENDENT` |
| Consistent sign and stable magnitude | `STABLE` |
| No per_group or per_regime data | `UNTESTED` |

## Overall Status Decision Matrix

| Direction | Func Form | Time Lag | Magnitude | State Dep | → Status |
|---|---|---|---|---|---|
| MISMATCH | any | any | any | any | **inconsistent** |
| any | any | any | IMPLAUSIBLE | any | **rejected** |
| MATCH | MATCH | MATCH | PLAUSIBLE/STRONG | STABLE | **consistent** |
| mixed | mixed | mixed | mixed | mixed | **plausible** |
| UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | **untestable** |

The `inconsistent` verdict for direction MISMATCH is the primary diagnostic signal for physics contradictions like Arrhenius reversals.
