# DOE generality corpus — 12 industries × 12 design situations

This corpus exists to answer one question: **does the analyzer work beyond the one BOPET
scenario?** Every case is generated from a seeded simulation, declared through the same
`doe_context`/`analysis_context` contract, and run through the real pipeline
(`doe_context_adapter → doe_ontology_prepare → analysis_plan → analyze.py all → quality_gate.mjs`).

Run:

```bash
python docs/plans/demo/doe-generality/generate_cases.py --force
python docs/plans/demo/doe-generality/run_cases.py
```

Last result: **12/12 cases green, 132/132 checks passed.**

## Corpus

| Case | Industry | Expected → detected | Runs | Grade | Windows / joint | Key planted effect recovered |
|---|---|---|---:|---|---|---|
| `injection_full_factorial` | 注塑成型 | full_factorial → full_factorial | 18 | A | 3 / 1 | melt_temp +3.0, material effect; missing cell disclosed |
| `heat_treat_ccd` | 热处理 | rsm_ccd → rsm_ccd | 18 | A | 3 / 1 | aust_temp +1.57 (q=2.4e-8), distortion +0.029 |
| `reactor_bbd` | 化工反应 | rsm_bbd → rsm_bbd | 15 | A | 3 / 1 | react_temp +3.0, ph −2.0; linear constraint enforced |
| `etch_fractional` | 半导体刻蚀 | fractional/OA → orthogonal_array | 12 | A− | 4 / 1 | rf_power +55, pressure −30 on depth |
| `food_l9_oa` | 食品调味 | orthogonal_array → orthogonal_array | 9 | B | 1 / 1 | sugar +8.0 on taste; no pure error (9-run OA) |
| `battery_lhs` | 电池材料 | latin_hypercube → latin_hypercube | 20 | A− | 2 / 1 | ni_ratio +8 on capacity; LHS hull disclosed |
| `coating_conflict` | 涂布 | full_factorial → full_factorial | 11 | A | 2 / 1 | oven_temp improves gloss but worsens orange peel; joint trades off |
| `plastics_units` | 塑料薄膜 | rsm_ccd → rsm_ccd | 11 | A | 2 / 1 | die_temp +5 on thickness; unit conflict + missing platform_ref disclosed |
| `machining_noise` | 机加工 | full_factorial → full_factorial | 11 | A | 3 / 1 | feed +0.40 significant; pure-noise response has no false positive |
| `panel_high_throughput` | 显示面板 | fractional/OA → orthogonal_array | 20 | A− | 5 / 1 | 10 responses × 5 factors; per-family BH-FDR; 50-cell matrix zero-silent |
| `design_only` | 实验室设计 | full_factorial → (refused) | 6 | — | — | `DESIGN_ONLY_NO_RESPONSE`; brief `data_stage=design_only` |
| `paper_observational` | 造纸 | observational → observational | 600 | B | 4 / 0 | correlation/stability/capability path; windows `confirmation_needed` |

## What the corpus proves

- **Design detection is not BOPET-specific**: full factorial (numeric+categorical), CCD, BBD,
  orthogonal array L9, LHS, 2-level fractional/OA, and observational records all classify correctly.
- **Constraints and units are enforced across industries**: the reactor's linear `Σ coeff·x ≤ rhs`
  binds; the plastics case reports the factor/`platform_ref` unit conflict and removes the
  no-platform-ref factor from `recipe_patch`.
- **Multiple responses scale**: the panel case runs 10 responses × 5 factors (160 tests) and still
  produces a zero-silent 50-cell factor/response matrix.
- **Null effects stay null**: the machining case's pure-noise response has no BH-significant factor.
- **Design-only is refused honestly**: a matrix with empty responses builds an ontology brief but
  refuses statistics; no response behaviour is invented.
- **Observational records stay correlation-grade**: no joint setpoints, all windows require
  confirmation, evidence grade B.

## Defects exposed and fixed by the corpus

1. **2-factor factorial + centre points fell to observational.** `design_detect`'s centre-stripping
   retry required `≥ max(6, 2k)` non-centre rows, which is impossible for a 2² design with centres
   (4 corners). Changed to `≥ max(4, 2k)`; the retry still verifies the stripped grid.
2. **Observational manifests reported designed-only artifacts as missing.** `ontology_feedback` and
   `ontology_consistency` are designed-mode artifacts; `_expected_kinds` now requires them only in
   designed mode.
3. **Test-generation trap (not a product defect):** the first generator re-coded already-coded
   design columns against raw bounds, compressing every contrast by ~1/half-range. The corpus now
   uses `design_build.coded` directly.
4. **Saturated fractions need error df.** The 16-run 2⁵ fraction with the default 2FI model leaves
   `df_resid=1`; adding centre runs (4) restores error df. The analyzer's saturation pooler already
   drops terms until `df_resid>0`, but a design with no pure error cannot support full inference —
   the report discloses `no pure-error replicates`. Operational guidance: **add centre/replicate
   runs to screening designs before asking for p-values.**

## Evidence

- `evidence/generality_matrix.json` — every check, per case.
- `evidence/heat_treat_ccd_report.html` — RSM report with a saddle stationary point and a
  constrained joint optimum.
- `evidence/coating_conflict_report.html` — two conflicting responses.
- `evidence/panel_high_throughput_report.html` — 10-response, 5-factor report.
- `evidence/paper_observational_report.html` — observational correlation/stability report.

> `cases/*/truth.json` is acceptance ground truth and must never be given to a diagnosing agent.
