# Reviewer A2 (Methodology & Statistics) — Independent Blind Re-Review, Round 21

Manuscript: `paper/main.tex` (build ~59 pages, 60 rendered PNGs). Evidence audited:
`results/benchmark/` (metrics.json, gradings/, consistency_audit.json, baselines.json,
suite_determinism.json, repro_report.json, retest_selection.json, rubric.json,
README-artifact-fields.md), run directories under
`workspace/diagnostic-runs/`, and the round-20 provenance dossier. Blind: round-19/20
review reports were not read.

## Paper Summary

The paper presents IDD, a nine-stage agentic industrial root-cause-analysis pipeline
(deterministic statistics, competing-hypotheses reasoning, L1–L7 evidence grading,
anti-spurious-correlation filters, bounded-repair gates), evaluated on a 12-scenario
benchmark (9 documented faults + 3 controls across SKAB, TEP, IndPenSim) under a
machine-checked evaluation framework. Headline: 4/9 resolved Top-1 (44.4%, presented
as a provisional upper bound with a joint worst-case floor of 0/9), top-k 9/9 at the
keyword instrument's family level (8/9 branch-localized), 0/3 false alarms, five capped
COMPETING_SET verdicts that each name the discriminating missing measurement. A
same-model bare-call ablation (9/9 strict keyword hits vs the pipeline's 4/9) bounds
every accuracy claim; the claimed contribution is the auditable, capped-honest process.
One seeded random-draw re-execution (n=1) reproduces the verdict structure; the
deterministic suite reproduces 45/45 outputs byte-identically.

## Verification Performed (focus areas as assigned)

### 1. Statistical arithmetic — all recomputed, all correct

I recomputed twelve Wilson 95% intervals at z=1.96 against the manuscript's printed
values:

| Quantity | Manuscript | Recomputed | Match |
|---|---|---|---|
| Top-1 4/9 | [18.9, 73.3] | [18.88, 73.34] | exact |
| Identity-strict 3/9 | [12.1, 64.6] | [12.09, 64.62] | exact |
| top-k 9/9 | [70.1, 100.0] | [70.09, 100.0] | exact |
| Control pass 3/3 | [43.9, 100.0] | [43.85, 100.0] | rounding boundary (see Minor-2) |
| Verdict-type 8/9 | [56.5, 98.0] | [56.55, 97.96] | exact |
| Precision 4/4 | [51.0, 100] | [51.02, 100] | exact |
| FE GPT-4o 7/11 | [35.4, 84.8] | [35.42, 84.76] | exact |
| FE o1-preview 9/11 | [52.3, 94.9] | [52.32, 94.93] | exact |
| IDD TEP 3/6 | [18.8, 81.2] | [18.79, 81.21] | exact |

Derived counts also verified against released artifacts:
- **Forced-commit counterfactual (6/9):** committing to each capped verdict's
  top-ranked survivor gives 4 resolved + IDV4 (truth family first) + IDV11 canonical
  (truth branch first) = 6/9, with exactly three wrong commitments (both SKAB capped
  cases and IDV3 rank the truth second) — confirmed from the gradings and the
  consistency-audit mechanism strings. The random-commit expectation is
  4 + 1/2 + 1/2 + 1/3 + 1/2 + 1/4 = 6.08 ≈ 6/9, exactly as the manuscript states;
  the recorded orderings do not manufacture the count.
- **Identity-strict symmetric accounting:** the batch-93 discount is applied
  symmetrically — Top-1 drops 4/9 → 3/9 *and* precision drops 4/4 → 3/4 with
  overconfidence ≥ 1 — reported in the abstract, Table 6, and Section 7.2. This is
  the correct symmetric treatment, not a per-metric most-favorable-lens quoting.
- Rubric mean 94.6 (1135/12, nine at 100, two at 85, one at 65) and the
  96.2-with-control-R3-excluded variant (1155/12 = 96.25) both recompute. Judge mean
  94.7 (1136/12, range 90–98) recomputes from metrics.json judge scores.
- Clean-subset readings (3/7 Top-1, 7/7 top-k excluding SKAB-valve and batch-93;
  bare arm 7/7 on the same subset) recompute from metrics.json and baselines.json.

### 2. Instrument validity — satisfied

- **Keyword provenance:** disclosed in three places (Metrics §6.2, Results §7.2,
  Table 6 caption): keyword sets were calibrated on v1-era executions of the same
  scenarios and are therefore "not an independent re-verification"; a hit certifies
  family agreement, never identity. The committed neutralized-identifier re-run will
  additionally re-check keyword coverage.
- **Leave-one-token-out (LOTO) sensitivity:** the manuscript's claim — Top-1 falls to
  3/9 only if the single token "header" is removed from IDV7's grading set, and IDV1's
  two hit tokens are spelling variants of one documented label — is verified verbatim
  against the released hit records: `gradings/tep_d07_header_pressure.json` has
  `kw_hits: ["header"]` (single token), and `gradings/tep_d01_ac_feed_ratio.json` has
  `kw_hits: ["进料配比", "配比"]` (two variants of "feed ratio"). The instrument-readings
  block in Table 6 (identity-strict, batch-93-excluded, LOTO rows) is present and
  renders correctly (checked p.25 rendering).
- **Shared-instrument caveat:** Section 8.3 states explicitly that the bare-LLM arm and
  the pipeline are scored by the *same* author-designed keyword instrument, so the
  9/9-vs-4/9 contrast is instrument-relative. This is the correct caveat and it is
  placed exactly where the contrast is interpreted.
- The `metrics.json` `calibrated`-flag folding and the `R4_calibration` rubric key are
  reconciled in the released `README-artifact-fields.md` and match the manuscript's
  footnote; I confirmed `rubric.json` uses `R4_calibration` and that the IndPenSim
  control's −35 = −20 (R3) − 15 (R4) decomposes as described.

### 3. Identifier-recall treatment — adequate; the re-run need not block publication

The treatment is the most complete I have seen on this failure mode:
- The scenario identifiers embed the documented mechanism (including the "brief-blind"
  SKAB case), the leakage sentinel covers briefs/user-context but not directory names,
  and the dispatcher-context channel is disclosed with a committed per-scenario-session
  remedy (§9, Table 9).
- The tiering is explicit and quantified: recall-possible bound "upper 4/9, lower 0/9"
  in Table 6; the joint floor (identifier recall on the three TEP-derived resolved
  verdicts + identity-strict on batch-93) is stated as 0/9 in §9 with the correct
  decomposition; the abstract and conclusion both carry the contingency.
- **Decision:** the re-run (~16 h agent time, hash-id harness extension) is committed
  as the first post-revision execution but has not executed. I judge the current
  treatment adequate **without** requiring pre-publication execution, because no claim
  in the paper depends on the favorable reading: every headline number is printed as a
  bound that remains true under the worst case (the central "process quality, not
  accuracy" conclusion is *strengthened* by the 0/9 floor). The re-run is confirmatory,
  not load-bearing. I strongly recommend it execute at proof stage with a one-sentence
  outcome note; if it does not, the contingency language must be retained verbatim
  (Minor-1).

### 4. Second-batch disclosure — accurate, verified on disk

I enumerated the on-disk second batch (`202609181728*`–`202609181738*`): exactly
12 run directories. Four contain `optimizer.md` + `report.md` (skab_valve1_1,
skab_cavitation_13, skab_normal_control, tep_d00_normal_control); exactly two closed
all gates (`pipeline_finalize_report.json` overall=PASS **and**
`evidence_closure_report.json` status=PASS) — and both of those are controls
(skab_normal_control, tep_d00_normal_control), whose diagnoses return concordant
normal verdicts ("无设备故障" / "数据不支持存在过程故障"). This matches the manuscript's
two disclosures (§8.4 parenthetical and Data Availability) word for word: "of its
twelve runs, four completed with reports and two controls closed all gates with
concordant normal verdicts, but the batch was never formally graded". Exclusion from
the deposit and from every statistic is confirmed (metrics.json per_case points only
at the 20260917 batch + the drawn re-execution), and `README-artifact-fields.md`
documents the batch and the tier_state restoration. The manuscript is accurate here.

### 5. Single-execution evidence and n=1 stability framing — satisfied

- The consistency audit (`consistency_audit.json`) shows exactly one in-era repeat
  pair (TEP IDV11): CONSISTENT, same verdict type (COMPETING_SET), same primary tag
  (XMV_10), same mechanism class (ENVIRONMENT), Δconfidence 0.02 (0.62 vs 0.60),
  cause-token overlap 0.1417 — matching the manuscript's "0.14 of cause tokens" and
  "within two confidence points" to the digit. Summary: within-era agreement 1/1,
  11 cases INSUFFICIENT-RUNS — matching the "eleven outstanding re-run contracts"
  framing rather than assumed stability.
- The manuscript itself enumerates the weaknesses of its own n=1: the drawn scenario's
  variance-burst signature makes structural agreement close to mechanical; the seed
  originates from the harness, not an external beacon; supersession was fixed before
  comparison. The draw record (`retest_selection.json`: seed 1003818694, mulberry32,
  uniform 0.846792349, pool of 9, index 7) matches the manuscript exactly.
- "Single recorded execution" is carried into Table 6's caption and §9's power
  paragraph; the deterministic-suite 45/45 byte-identical claim matches
  `suite_determinism.json` (verdict DETERMINISTIC, timestamps excluded) and is
  correctly scoped to the deterministic arms, not the stochastic reasoning layer.

## Major Issues

None. All five assigned focus areas verify against the released artifacts, and every
quantitative claim I recomputed (12 Wilson intervals, the forced-commit counterfactual,
the random-commit expectation, the symmetric identity-strict accounting, the rubric and
judge means, the second-batch census) matches the manuscript within rounding.

## Minor Issues

1. **Neutralized-identifier re-run (proof-stage condition).** Execute the committed
   eight-scenario re-run at proof stage and report the outcome in one sentence
   (whichever way it lands); if it cannot execute, retain the explicit contingency
   language ("no headline verdict is recall-clean until...") verbatim in the
   camera-ready. Not blocking — no published claim depends on the favorable reading.
2. **Control-pass CI rounding boundary.** The exact Wilson lower bound for 3/3 at
   z=1.96 is 43.85%; the manuscript prints [43.9, 100.0] (round-half-up) — defensible,
   but state the rounding convention or print three significant figures, since the
   same quantity rounds to 43.8 under other conventions.
3. **Corpus-freeze criterion.** The second-batch exclusion is chronological, not
   selective: metrics.json was generated 2026-09-18T01:02Z and the second batch began
   2026-09-18T17:28Z. State this timestamp boundary explicitly in §8.4 or the Data
   Availability note — it pre-empts any suspicion of post-hoc exclusion.
4. **Two gate-closed control re-executions are latent stability evidence.** Once
   formally graded, the two concordant second-batch controls would lift within-era
   agreement from 1/1 to 3/3 at zero execution cost; either fold them in under the
   pre-stated supersession rule in a future revision or explain why the corpus freeze
   takes precedence.
5. **Stale archive path.** The provenance dossier (and my review instructions) reference
   `D:/idd-run-archive/diagnostic-runs/`, which does not exist on this machine; the
   canonical runs live under `workspace/diagnostic-runs/`. Repository hygiene item
   only — the manuscript itself cites no such path.

## Verdict: SATISFIED-ACCEPT

Justification: this is the rare revision where every auditable claim audits clean. The
instrument's provenance, its LOTO sensitivity, and its shared-instrument limitation are
disclosed and verified against the released hit records; the recall-possible tiering
bounds the headline from above and below in the abstract itself; twelve Wilson
intervals, the forced-commit counterfactual, and the symmetric identity-strict
accounting all recompute exactly; the interrupted second batch is disclosed with
per-run accuracy that I confirmed file-by-file on disk; and the n=1 stability evidence
is framed as the beginning, not the end, of a stability study, with eleven explicit
re-run contracts instead of assumed stability. The remaining items are cosmetic or
proof-stage actions; none touches the validity of any published claim. The paper's
own honesty apparatus — printing the worst case next to every headline — is what makes
a satisfied verdict possible at this stage.

---

*Reviewer A2, Round 21. Blind re-review; round-19/20 review reports not consulted.
Artifacts referenced: `D:\codes\myskills\industrial-deep-diagnostic\results\benchmark\*`,
`D:\codes\myskills\industrial-deep-diagnostic\workspace\diagnostic-runs\2026091*`,
`D:\codes\myskills\industrial-deep-diagnostic\paper\main.tex`.*
