# Method Notes — Statistical Caliber of industrial-doe-analyzer (v1.0)

Every formula and rule the deterministic core implements, pinned here so that
reviewers (human or agent) can audit without reading code. Companion of plan
`.omc/plans/industrial-doe-analyzer-skill-v1.md` (v1.1, three-seat review).

## C1 Coding
Effect/deviation coding only (dummy coding forbidden — collinear with intercept).
Continuous factors: `coded = (x − mean) / half_range` (half-range of the observed
column), so coded units are [−1, 1]. Categorical L levels → L−1 deviation columns
(reference = last level: 1 / 0 / −1). Quadratic terms only for continuous factors.
Blocks/covariates enter as flagged main terms — they consume df but never produce
windows or recommendations.

## C2 Extra-SS ANOVA (single-deletion; Type-II-equivalent on orthogonal designs)
Implemented as reduced-model refit: SS(term) = RSS(reduced model without the
term's columns) − RSS(full model), df = rank difference. The emitted field is
`ss_extra_ss` — deliberately NOT labelled "Type-II": on orthogonal (balanced)
designs the single deletion coincides exactly with classical Type-II (tests
assert this on F1), but on unbalanced designs the reduced model retains the
interactions containing the tested term (deviation coding), so the value is the
Type-III-style single-deletion extra-SS and p values are coding-dependent there.
Whenever a designed-mode family is fitted to an unbalanced design
(`balanced: false`, `balance_ratio` in the profile), the profile discloses this
with an `UNBALANCED_DESIGN` caveat.

## C3 Saturation strategy (in order)
1. Pure error available (replicate rows / center points) → use it.
2. No replicates → pool highest-order terms (3FI first, then 2FI, then quadratic;
   mains last) into error until df_resid ≥ 1; pooled terms disclosed in
   `pooled_terms` and reported with `reason_code: "pooled"` (no p/q).
3. Still df_resid = 0 → rows report coefficient only, `reason_code: "saturated"`.

## C4 Lack-of-fit
Estimable only when df_resid > df_pure_error > 0. Per-mode matrix:
full factorial with replicates/center points → yes (incl. center-point curvature
t = the RSM-upgrade trigger); fractional without replicates → no (reason given);
CCD/BBD with center replicates → yes; LHS / observational → no.

## C5 Multiple testing — BH-FDR by family
One family per response (designed effects) / per target (observational pairs).
Aliased, saturated and pooled rows NEVER enter a family. q = Benjamini-Hochberg
(PRDS holds for the pairwise-correlation family; valid). **Effect-size double
gate** for recommendations: q < 0.05 AND partial η² ≥ 0.01 — at observational n
everything is "significant"; without the effect gate G3/G4 could not stop junk
windows. Note: the legacy diagnosis stack uses Bonferroni; this skill
deliberately uses BH for high-throughput power (documented divergence, not a
silent replacement).

## C6 Capability — honest labels
- Pp/Ppk from the OVERALL sigma (always reported when specs exist).
- Cp/Cpk from MR̄/d2 (d2 = 1.128, individuals chart) ONLY when time-ordered;
  label `Cpk(within, MRbar/d2)`.
- Normality: skewness/kurtosis + Anderson-Darling double condition (AD alone
  rejects almost everything at n > 5000). Non-normal → Cpk marked INDICATIVE
  and quantile index Cnp = (USL−LSL)/(P99.865−P0.135).
- lag-1 autocorrelation → n_eff = n(1−ρ)/(1+ρ) warning; one-sided specs →
  Cpu/Cpl with Cp = null.

## C7 Confidence enum (deterministic, agent cannot invent numbers)
- designed: high = q<0.05 ∧ effect gate ∧ resolution ≥ V (or full design);
  medium = q<0.05 ∧ effect gate otherwise; low = the rest.
- observational: always low (correlation-grade; confirmation mandatory).
- key_findings[].confidence uses a coarser deterministic rule (q<0.01→high,
  else medium; conclusion baseline; observational findings are always low) —
  distinct from the window confidence above. Both are script-computed; do not
  reconcile them in reports.

## C8 Randomization & MDE
Run-order/time vs factor Spearman |ρ| > 0.5 → NON_RANDOMIZED caveat, grade
checklist fails, confirmation forced. MDE per response =
(t_{0.975} + t_{0.8}) · σ_pure · 2/√n for a 2-level coded main effect —
distinguishes "not significant" from "not measured". MDE caliber = full
2-level level-mean difference (range), i.e. 2× the coded main-effect
coefficient reported in the same table.

## C9 Factor importance (two calibers, DoEgen-inspired)
designed: standardized |t| Pareto AND level-mean range (captures categorical /
non-monotone effects). observational: leave-one-factor-out ΔR² contribution.

## C10 Caliber consistency with the diagnosis stack
All r / p / lag values come from the reused `core_stats`
(pearson / spearman / full_lag_ccf / detrended_correlation) — never recomputed
with np.corrcoef. **Lag sign convention (core_stats construction
target(t) ~ param(t+lag)): negative best_lag = the PARAMETER led the target**
(param moved first) — the causal direction for observational windows.
Anti-spurious verdicts come from `run_anti_spurious_checks` fed with the
`correlation_result` (+ group_col / time_col) — without it those checks silently
run empty (verified against anti_spurious.py source).

## C11 Evidence grade rubric (audit mirror of conclusion_template.py `_grade`)
Checklist items and their source fields (current code behavior):

| Checklist item | Source | Mode |
|---|---|---|
| `randomization_ok` | true iff no `NON_RANDOMIZED` caveat in `data_profile.json` caveats (C8 Spearman check) | designed |
| `pure_error_df_gt0` | true iff any `effect_table.json` family has `df_pure_error > 0` | designed |
| `resolution_ok` | true iff `design_type` ∈ {full_factorial, rsm_ccd, rsm_bbd, latin_hypercube} OR `resolution` ≥ 5 | designed |
| `balanced` | `design.balanced` — `None` (not evaluated, e.g. RSM/LHS replicate centers/axials) is excluded from scoring; `false` counts as a fail | designed |
| `model_adequacy_ok` | false iff any response family is `saturated` or has significant lack-of-fit (estimable LOF with p<0.05); `None` when not evaluable | designed |
| `anti_spurious_ok` | true iff no correlation pair has \|r\| ≥ 0.3 AND verdict FAIL | observational |

Grading: observational → **B** unconditionally. Designed → count `false` items
(`null` items and `overridden_by` are excluded from scoring): 0 fails → **A**,
1 fail → **A−**, ≥2 fails → **B**. `mode_override` is recorded as
`overridden_by: "user"` but never changes the score.

Checklist membership and scoring are maintained by the script
(`conclusion_template.py`); this section is an audit mirror — if it ever
disagrees with the code, the code is the truth and this document must be fixed.

## Design detection rules (order matters)
1. C distinct combos == ∏levels and balanced → full_factorial (counting keys on
   C, NOT run count — replicated fractionals must not look full).
2. Binary, C < 2^k, ±1-orthogonal → fractional_factorial + generator recovery
   (word group via elementwise product ≡ 1; resolution = min word length;
   alias chains = S ⊕ W). Dangerous-alias rule: an effect with an alias of the
   SAME OR LOWER order → estimable:false, out of the BH family, fold-over
   confirmation generated. Consequence: at resolution III a main effect's
   aliases are 2FIs (HIGHER order) → mains STAY estimable with the alias chain
   disclosed; it is the 2FIs that get killed. At resolution IV the 2FIs alias
   each other (same order) → 2FIs are killed, mains unaffected. Same-order
   aliases always kill each other, at any resolution.
3. Center points ≥ 2 ∧ axial points ≥ 2k → rsm_ccd (α from axial distance).
4. 3-level pairwise balance without all-extreme corners → rsm_bbd.
5. Strength-2 orthogonality across all column pairs → orthogonal_array
   (mixed-level OA aliasing NOT fully disclosed in v1 — causal reading
   restricted).
6. Per-factor 1-D stratification occupancy ≥ 0.85 → latin_hypercube.
7. Otherwise observational (conservative). RSM/LHS branches require ≥ 2 numeric
   factor columns (a single drifting column is observational, never a 1-factor
   RSM). Numeric dtype (not level count) drives the RSM branch — CCD axial
   points make factors look "discrete" by uniqueness.

## Window derivation
- designed W1-W5: feasible = {x : one-sided-95% prediction bound still inside
  spec (goal-aware side)}; desirability D = (∏ d_i^{w_i})^{1/Σw} with
  Derringer-Suich individual desirabilities; window per factor = projection of
  {feasible ∧ D ≥ 0.8·D_max} (connected block containing the optimum;
  disconnected → watchlist); window edge on the design boundary →
  extrapolation:true; linear-only model (no significant curvature/2FI or
  df_resid < 3) → W4 downgrade: directional advice in watchlist + generated
  confirmation design (runs = active factors + 5).
- observational W6-W8: top-K (≤3) steady segments by segment-Cpk / goal score;
  window = P10-P90 of the factor within pooled selected rows; delta = upper vs
  lower tercile mean difference with Welch CI (stratified by group column when
  present: weighted δ, SE = √Σ(n_g/N)²·SE_g²); ALL windows
  confirmation_needed:true, confidence low.

## Downstream contract v1.0
`conclusions/recommendations.json` — key semantics: `expected_effect.delta` is
per +1 RAW unit of the factor (designed: coded main coefficient / half-range);
`current_baseline` = factor medians of the full dataset with per-window
distance; conflicts resolved to the higher-|delta| window (loser demoted to
watchlist, never silently dropped); `applicability_domain.factor_observed_ranges`
is the hard G3 boundary; `invalidation_conditions` are the standing re-run
triggers. Headless runs author the baseline with `authored_by: "script"`;
agents may only enrich (flip to "agent") — never renumber, never edit computed
values.

## Q² note
LOO Q² via hat matrix; replicate (twin) rows can leak — reported as an
optimistic bound (see model.json q_squared_note).

## Reuse map (all verified against source)
file_inspect.load_file / detect_time_column · dp_toolkit preprocess (CLI) ·
core_stats.run_correlation_analysis / pearson / full_lag_ccf /
detrended_correlation · anti_spurious.run_anti_spurious_checks /
_detect_change_points · production_regime_detector fast functions
(in-process: detect_by_variance_fast / detect_change_points_fast /
detect_drift_ramps_fast / fuse_regimes, row-window) ·
plot_verification._ink_check · shared validate.mjs ·
append-pipeline-event.mjs (requires run_manifest.json — Phase 0 creates it).

## External borrowings
jkitchin/skillz design-of-experiments (question-driven dispatch, pitfalls) ·
DoEgen (level-mean-range importance, balance/orthogonality criteria) ·
K-Dense scientific-agent-skills (scripts-must-ship-tests convention → this
test suite) · Derringer-Suich desirability · Benjamini-Hochberg ·
PySpc/statprocon chart taxonomy reference. pyDOE3 / OApackage deliberately NOT
added (zero new dependencies).
