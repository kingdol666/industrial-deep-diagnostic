# Task 2 Report: 纯 numpy/pandas 统计工具 (`stat_utils.py`)

## Deliverable
Created `.claude/skills/industrial-deep-analysis/scripts/stat_utils.py` — a focused,
importable numerical utility module (stdlib + numpy + pandas only). No production
side effects on import; an `if __name__ == "__main__"` smoke path is included.

## Public API implemented (all per brief signatures & result keys)
1. `ols_centered(X, y)` → `beta, se, t, p, r2, resid, n, rank, columns` (+`status`).
   Centered design, intercept at predictor means, `pinv`-based (collinearity-safe),
   two-sided normal-approx p-values via `math.erf`. `status="constant_response"` /
   `"empty"` / `"insufficient_dof"` for degenerate input.
2. `slope_at_current(x, y, x0)` → `linear, quadratic, slope_at_current, curvature,
   x_mean, x0, n, status`. Derivative = `beta_linear + 2*beta_quadratic*(x0-x_mean)`.
   `status="insufficient_data"` for <3 valid rows.
3. `partial_correlation(df, x, y, controls)` → `r, p, n, controls, status`.
   Residualizes against intercept + all controls, drops non-finite rows, Fisher-z
   p-value with effective df `n-k-3`. Constant/insufficient → `r/p=None`.
4. `block_bootstrap_ci(values, groups, statistic, B, seed, alpha)` → `estimate, ci,
   n_rows, n_blocks, B, seed, statistic, status`. Whole-block resample with
   replacement; `numpy.random.default_rng(seed)` deterministic; `"mean"`/`"median"`/
   callable; `status="insufficient_blocks"` + null CI for <2 blocks.
5. `benjamini_hochberg(p_values)` → ordered q-values; invalid p → `None`; empty → `[]`;
   monotonic enforced, clipped to [0,1].
6. `durbin_watson(resid)` → float or `None` (<2 points / zero denominator).
7. `stationarity_check(series)` → `is_stationary, n, variance_level, variance_diff,
   ratio, status`. Transparent first-difference variance-ratio heuristic; explicitly
   NOT a formal unit-root test.
8. `support_domain(series)` → exactly `p5, p25, p50, p75, p95, n, current_median`
   (+`status`); numpy percentiles; empty → `status="empty"`.

Helpers: `_to_float_array` / `_to_matrix` (numeric coercion, drop-invalid),
`_finite_mask`, `_normal_cdf`, `_two_sided_normal_p`, `_pearson_r`, `_resolve_statistic`.

## Dependency surface (verified)
`python -c "import ast..."` → imports: `__future__, math, numpy, pandas, typing`.
**Forbidden (scipy/statsmodels/sklearn/jinja2/sqlite/services): none.**

## Verification — exact commands & results

### A. Focused unit verification
Command:
```
python .superpowers/sdd/doe-enhance-plan/verify_stat_utils.py
```
Result: `ALL_CHECKS_PASS` (28/28 checks). Key observations:
- `ols_centered` synthetic quadratic: `status=ok`, beta finite, p finite, `rank=2`.
  Linear-only R²=0.6058 (correct — linear fit to a parabola); 2-D `[x, x²]` fit
  R²>0.95. Constant response → `status="constant_response"`. DataFrame column order
  preserved: `["intercept","b","a"]`.
- `slope_at_current`: derivative at mean = -0.9839, at x0=9 = -3.3948 (**differs** from
  raw linear coef, as required). `<3 rows` → `insufficient_data`.
- `partial_correlation` (2 controls, NaN injected): `r=0.3978`, `n=195` (5 dropped),
  `controls=["B","C"]` order preserved; independent pair `r=-0.0222`.
- `block_bootstrap_ci`: `n_blocks=3`, **deterministic** (identical CI on repeat with
  seed 0), block CI `[-0.141, 20.077]` **differs** from iid-row CI `[8.247, 11.580]`
  on strongly-grouped data (proves block resampling, not iid). `<2 blocks` →
  `insufficient_blocks`. Callable statistic works (`status=ok`).
- `benjamini_hochberg([0.01,0.04,0.03,0.20,0.60])` → `[0.05,0.0667,0.0667,0.25,0.6]`,
  monotone, order-preserving. `[]` → `[]`. Invalid input
  `[0.5,None,1.5,-0.1,"x",0.05]` → `[0.5,None,None,None,None,0.1]` (m=2 valid).
- `durbin_watson`: finite value; single point → `None`; all-zero residuals → `None`.
- `stationarity_check`: white-noise → `is_stationary=True`; random walk → `False`;
  constant → `status="constant_series"`; <3 → `insufficient_data`.
- `support_domain([1..10])`: `p50=5.5=current_median`, keys exact; NaN-only → `empty`.

### B. CSTR `cleaned_data.csv` smoke call
Command:
```
python .superpowers/sdd/doe-enhance-plan/smoke_cstr_stat_utils.py
```
Data: 1200 rows. Results:
- `support_domain(Haze)`: p5=2.7937, p25=3.003, p50=3.1446, p75=3.299, p95=3.4909,
  n=1200, current_median=3.1446, status=ok.
- `block_bootstrap_ci(Defect_Density, product, mean, B=300, seed=0)`: estimate=0.65,
  ci=[0.502, 0.7979], n_rows=1200, n_blocks=2 (2 products), status=ok.

## Concerns
1. **Normal-approx p-values, not t-distribution.** `ols_centered` and
   `partial_correlation` use a two-sided standard-normal tail (`math.erf`) per the
   brief ("two-sided normal-approximation p-values"). These are slightly
   anti-conservative for small n; acceptable as a screen and matches the explicit
   spec, but Task 3 consumers should treat p-values as approximate.
2. **`stationarity_check` is a heuristic only.** First-difference variance ratio is a
   transparent screen, not a unit-root test (ADF/KPSS unavailable without scipy). The
   docstring and the `status` field flag this; persistent-but-stationary AR series may
   be mislabelled. Documented in-function.
3. **`durbin_watson` on constant non-zero residuals (e.g. `[3,3,3]`) returns 0.0**, not
   `None` — the denominator `resid@resid` is non-zero, so DW=0 (perfect positive
   autocorrelation) is the mathematically correct value. `None` is reserved for the
   true zero-denominator case (all-zero residuals) and <2 points, per the brief.
4. **Block bootstrap CI can be wide on few blocks.** With n_blocks=2 (CSTR product
   grouping) the resampled distribution is coarse; this is inherent to block
   bootstrapping and expected, not a bug.
5. Report/verification scripts live under the gitignored `.superpowers/sdd/` tree; the
   report was force-added to match the Task 1 commit pattern. Verification scripts are
   left as local working artifacts.

---

## Fix Round (post 3a607c5) — reviewer edge-case hardening

Three edge cases in `stat_utils.py` hardened:

1. **slope_at_current x0 coercion** — `x0=None` raised `TypeError` in the n>=3 code
   path but was guarded only in the insufficient-data branch. x0 is now coerced
   upfront via try/except; invalid x0 (None, NaN, ±∞, non-numeric) returns
   `status="invalid_x0"` uniformly, with linear/quadratic/slope_at_current all set
   to None. Valid x0 continues to `status="ok"` as before.

2. **partial_correlation eff≤0 boundary** — When `n == k+3` (eff=0), Fisher-z cannot
   compute a p-value but the function previously returned `status="ok"` with p=None.
   Now emits `status="insufficient_dof"` when `eff <= 0`, preserving r (which is
   computable) but setting p=None. Downstream status-ok consumers never encounter
   a None p-value.

3. **ols_centered rank deficiency** — Collinear design matrices (rank < n_cols)
   previously passed through to se/t/p computed via pinv, yielding spuriously
   significant individual p-values under `status="ok"`. Now a rank-deficiency gate
   after the df check sets `status="rank_deficient"`, nulls se/t/p, and preserves
   beta (minimum-norm solution) and rank.

### Exact commands & results

**Core regression (28 checks):**
```
python .superpowers/sdd/doe-enhance-plan/verify_stat_utils.py
→ ALL_CHECKS_PASS
```

**Reviewer-targeted edge cases (20 checks):**
```
python .superpowers/sdd/doe-enhance-plan/verify_reviewer_edges.py
→ REVIEWER_CHECKS_PASS
```
Key observations:
- `slope_at_current(x,y,None)` → `status="invalid_x0"`, `slope_at_current=None`
- `slope_at_current(x,y,NaN)` → `status="invalid_x0"`
- `slope_at_current(x,y,±∞)` → `status="invalid_x0"`
- `slope_at_current(x,y,"bad")` → `status="invalid_x0"`
- `slope_at_current(x,y,5.0)` → `status="ok"`, derivative=0.5, curvature=-0.2
- `partial_correlation(n=6,k=3)` (eff=0) → `status="insufficient_dof"`, p=None, r≠None
- `partial_correlation(n=6,k=4)` → `status="insufficient_data"`
- `partial_correlation(n=200,k=2)` → `status="ok"`, p finite
- `ols_centered` [x, 2x, x+1] → `status="rank_deficient"`, rank=2<4, se=None, p=None, beta≠None
- `ols_centered` [x, x²] → `status="ok"`, se≠None

**CSTR smoke (no regression):**
```
python .superpowers/sdd/doe-enhance-plan/smoke_cstr_stat_utils.py
→ support_domain + block_bootstrap_ci both status=ok, values unchanged
```
