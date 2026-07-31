# Task 4 Report: Physics Bridge Implementation

**Date:** 2026-07-31
**Status:** Complete
**Revision:** 2 (fixed direction_verification, removed Arrhenius bleed, removed dead code)

## Files Changed

### Created

| File | Description |
|------|-------------|
| `.claude/skills/industrial-physics-bridge/SKILL.md` | Skill documentation |
| `.claude/skills/industrial-physics-bridge/references/agent-protocol.md` | Agent execution protocol |
| `.claude/skills/industrial-physics-bridge/resources/physics_verification_rules.md` | Physics verification rules reference |
| `.claude/skills/industrial-physics-bridge/scripts/physics_bridge_builder.py` | Main Python script |
| `.omp/agents/physics-bridge.md` | Agent definition |

### Modified

None.

## Execution Command

```bash
python .claude/skills/industrial-physics-bridge/scripts/physics_bridge_builder.py \
  --run-dir workspace/diagnostic-runs/202607300458012_cstr_catalyst_real
```

## Execution Result

```
[physics_bridge_builder] Wrote 11 relationship verifications
[physics_bridge_builder] Wrote 2 mechanism chains
[physics_bridge_builder] Wrote 2 competing explanations
[physics_bridge_builder] Wrote 15 evidence gaps
[physics_bridge_builder] Output: ...\enhancement\physics_bridge.json
```

## Schema Validation

```bash
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/physics_bridge_schema.json \
  workspace/diagnostic-runs/202607300458012_cstr_catalyst_real/enhancement/physics_bridge.json
```

**Result:** `valid: true`, 0 errors, 0 warnings.

## Relationship Verifications (from actual output)

| # | predictor | target | direction | functional_form | time_lag | magnitude | state_dependence | overall_status |
|---|-----------|--------|-----------|-----------------|----------|-----------|------------------|----------------|
| 1 | catalyst_bed_id | conversion_pct | MATCH | UNTESTED | MATCH | PLAUSIBLE | UNTESTED | plausible |
| 2 | cooling_water_temp_C | byproduct_ppm | UNTESTED | UNTESTED | UNTESTED | UNTESTED | REVERSES | plausible |
| 3 | feed_rate_kg_hr | conversion_pct | UNTESTED | UNTESTED | MATCH | IMPLAUSIBLE | REVERSES | rejected |
| 4 | feed_sulfur_ppm | byproduct_ppm | UNTESTED | UNTESTED | UNTESTED | UNTESTED | REVERSES | plausible |
| 5 | h2_partial_pressure_bar | byproduct_ppm | UNTESTED | UNTESTED | UNTESTED | UNTESTED | STATE_DEPENDENT | plausible |
| 6 | h2_partial_pressure_bar | conversion_pct | UNTESTED | MATCH | MISMATCH | PLAUSIBLE | STATE_DEPENDENT | plausible |
| 7 | h2_partial_pressure_bar | selectivity_pct | UNTESTED | UNTESTED | UNTESTED | UNTESTED | STATE_DEPENDENT | plausible |
| 8 | reactor_pressure_bar | conversion_pct | UNTESTED | UNTESTED | UNTESTED | UNTESTED | STATE_DEPENDENT | plausible |
| 9 | reactor_temp_C | byproduct_ppm | MATCH | MATCH | MATCH | PLAUSIBLE | REVERSES | plausible |
| 10 | **reactor_temp_C** | **conversion_pct** | **MISMATCH** | MATCH | MISMATCH | IMPLAUSIBLE | STATE_DEPENDENT | **inconsistent** |
| 11 | reactor_temp_C | selectivity_pct | MATCH | MATCH | MATCH | PLAUSIBLE | REVERSES | plausible |

## CSTR Contract (AC-2) Verification

The only row with `inconsistent` status is reactor_temp_C→conversion_pct (row 10):

```
reactor_temp_C → conversion_pct:
  direction         = MISMATCH   ✓
  functional_form   = MATCH
  time_lag          = MISMATCH
  magnitude         = IMPLAUSIBLE
  state_dependence  = STATE_DEPENDENT
  overall_status    = inconsistent ✓
```

Direction is derived from `ontology.data_direction_validated="false"` — the ontology authoritatively states that the observed data direction contradicts Arrhenius physics. The `inconsistent` status flows from the direction MISMATCH rule in `_determine_overall_status`.

## Mechanism Chains

| chain_id | Claim | Diagnosis Support |
|----------|-------|-------------------|
| MC-001 | 原料累积硫中毒不可逆失活 (H1) | confidence=80, SURVIVING |
| MC-002 | 积碳可逆失活 (H2) | confidence=66, SURVIVING |

## Competing Explanations

| Hypothesis | Exclusion Type | Confidence |
|------------|---------------|------------|
| H3: 热烧结不可逆失活 | PHYSICAL (烧结阈值>400 deg C, 数据最高191 deg C) | 95% |
| H4: 操作工提温补偿(是果非因) | PHYSICAL (因果方向错误) | 98% |

## Evidence Gaps (15 total)

Key critical/major gaps:
- [H1] 无催化剂离线活性测试(a(t))数据 (critical)
- [H1] 无进料硫物种的GC-MS或XRF分析 (critical)
- [Epistemic] 无进料硫物种的GC-MS或硫化学发光检测(GC-SCD)数据 (major)
- [Epistemic] 无催化剂离线表征(XPS/TEM/BET/CO化学吸附) (major)
- [Epistemic] 仅单次再生事件—无法验证可逆/不可逆比例的复现性 (major)
- [Epistemic] 再生后仅240h数据(10天)—长期趋势确认不足 (major)

## Quantity Checks

| Check | Required | Actual | Status |
|-------|----------|--------|--------|
| mechanism_chains >= 1 | 1 | 2 | PASS |
| competing_explanations >= 1 | 1 | 2 | PASS |
| evidence_gaps >= 2 | 2 | 15 | PASS |
| inconsistent count | 1 (only AC-2) | 1 | PASS |

## Bug Fixes (Revision 2)

### P0: Direction verification re-derived sign from noisy detrended r
**Fix:** `_direction_verification` now treats `data_direction_validated` as the authoritative comparison result from the ontology. "true" = MATCH, "false" = MISMATCH, "untested" = UNTESTED. Previously it computed a statistical sign from detrended r (which was near-zero and noise-dominated), overriding the ontology's authoritative determination. This caused reactor_temp_C→byproduct_ppm and reactor_temp_C→selectivity_pct to be misclassified as MISMATCH.

### P0: Arrhenius contradiction check bled across all ontology-matched relationships
**Fix:** Removed the tautological check from `_determine_overall_status`. The guard `pred_from == predictor and pred_to == target` was always true for matched relationships (both from the same onto_rel lookup). The check was also redundant — the direction=MISMATCH rule already correctly sets "inconsistent" for reactor_temp_C→conversion_pct. Three relationships were misclassified: catalyst_bed_id→conversion_pct, feed_rate→conversion_pct, h2→conversion_pct.

### P2: Dead code removal
Removed unused `confidence_val`/`level` computation in `_build_mechanism_chains` and removed unused `physics_check` parameter/loading.

## Test Summary

All 5 formal checks pass + schema validation clean:
- ✅ Schema validation: 0 errors, 0 warnings
- ✅ CSTR contract: direction=MISMATCH, overall_status=inconsistent
- ✅ mechanism_chains: 2 chains from surviving hypotheses (H1, H2)
- ✅ competing_explanations: 2 from eliminated hypotheses (H3, H4)
- ✅ evidence_gaps: 15 total (6 critical/major)
- ✅ Only 1 relationship with inconsistent status (the expected AC-2 row)

## Concerns

None. Fixed bugs were identified and resolved. The implementation now correctly delegates direction verdict to the ontology's authoritative `data_direction_validated` field and produces exactly one `inconsistent` status for the physics-contradicted Arrhenius relationship.
