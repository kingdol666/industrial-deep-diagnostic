# Reviewer A — Methodology & Statistics (blind review, round 20)

Manuscript: `paper/main.tex` (50-page compiled PDF). Evidence audited: `results/benchmark/`
(metrics.json, gradings/, journal.jsonl, consistency_audit.json, baselines.json,
suite_determinism.json, repro_report.json, rubric.json, retest_selection.json,
baselines_input_audit.json, README-artifact-fields.md, benchmark_report_en.md), run artifacts
under `D:\codes\idd-run-archive\diagnostic-runs\`, and the provenance note
`paper/review/round20/PROVENANCE.md`. All arithmetic below was recomputed by this reviewer from
the released artifacts, not taken from the paper.

## Paper Summary (3 sentences)

The paper presents IDD, a nine-stage agentic root-cause-analysis pipeline whose LLM reasoning is
wrapped in deterministic statistics, competing-hypotheses elimination, L1–L7 evidence grading,
confidence ceilings, and machine-checked gates, and argues that its contribution is an
*auditable, capped-honest process* rather than accuracy. It evaluates the pipeline on a
12-scenario corpus (SKAB, TEP, IndPenSim) under a truth-isolated, fingerprinted, gate-graded
evaluation contract, reporting 4/9 resolved Top-1 (bracketed by identity-strict 3/9 and a joint
recall floor of 0/9), top-k 9/9 at a disclosed keyword instrument's family level, 3/3 controls
(one blind), a same-model bare-call ablation that scores 9/9 and therefore bounds every accuracy
claim, one seeded re-execution pair (n=1, consistent), and a 45/45 byte-identical deterministic
suite re-run. The manuscript is unusually explicit about its own weaknesses: identifier-bearing
run names as a residual leakage channel with a committed but unexecuted neutralized-identifier
re-run, author-designed instruments awaiting blinded expert anchoring, single-execution evidence,
and one-directional verdict typing.

## Verification performed (context for the issues)

Before listing issues, what I checked and confirmed — because the verdict depends on it:

- **Wilson 95% CIs recomputed (z=1.96), all match the printed values to the digit**: 4/9 →
  [18.88, 73.34]; 3/9 → [12.06, 64.58]; 9/9 → [70.09, 100]; 3/3 → [43.86, 100]; 8/9 →
  [56.50, 98.00]; 4/4 conditional → [51.01, 100]; 7/11 → [35.37, 84.82]; 9/11 → [52.30, 94.86];
  3/6 → [18.76, 81.24]. The released scorer's constant (1.96) and `metrics.json → cdr_ci95`
  agree.
- **Identity-strict accounting verified from gradings**: the four DETERMINED fault verdicts are
  tep_d01 (0.91), tep_d07 (0.78), tep_d14 (0.80), indpensim_batch093 (0.82); discounting batch-93
  gives Top-1 3/9 and precision 3/4, exactly as printed; `overconfident: 0` in metrics.json
  matches "no DETERMINED-and-wrong verdict".
- **Forced-commit counterfactual 6/9 verified from `04_diagnostics/diagnosis.json` survivor
  lists**: skab_valve1 (truth second of 2), skab_cavitation (second of 2), tep_d03 (second of 3,
  steam-side first), tep_d04 (truth first of 2), tep_d11-canonical (branch-level cooling first of
  4). Forced commitment → 4 + 2 = 6/9 with exactly three wrong commitments; uniform random
  commitment expectation 4 + (1/2+1/2+1/3+1/2+1/4) = 6.08 ≈ 6/9. The paper's numbers are correct.
- **Seeded draw replays**: mulberry32(1003818694) → 0.8467923 → index 7 → tep_d11, matching
  `retest_selection.json` (pool, raw value, contract text).
- **Stability pair**: `consistency_audit.json` records 0.62 vs 0.60 (Δ=2), same type, same
  primary tag XMV10, same mechanism class, cause-token overlap 0.1417 ("0.14" in text), and 11
  scenarios honestly listed INSUFFICIENT-RUNS.
- **Keyword provenance**: token sets released in `scripts/benchmark/cases/benchmark_cases.json`;
  `git log` confirms the last edit to that file is commit 221d061 (2026-09-15) while all
  current-era executions are 2026-09-17/18 — the "calibrated then frozen before execution" claim
  holds. Leave-one-token-out verified structurally: tep_d07's recorded hits are exactly
  ["header"] (the diagnosis string uses "C-header"; the Chinese synonym 集管 does not occur in
  it), so removing "header" drops Top-1 to 3/9; d01 (two variant tokens), d14 (stiction-specific
  tokens) and batch-93 (three tokens incl. generic 偏差) survive any single removal. Matches the
  text.
- **Repair accounting**: exactly one `repair_spawn` event across all 13 event logs (tep_d03);
  the d03 judge record shows iteration 2, score 90, both round-1 blocking issues resolved.
- **Rubric/judge aggregates**: rubric mean 1135/12 = 94.58 ≈ 94.6; judge mean 1136/12 = 94.67 ≈
  94.7, range 90–98; R4 failures at 0.91 and 0.93 and the SKAB-valve allowed-set violation all
  present in `rubric.json` as described.
- **Raw-data spot check**: recomputed the SKAB valve flow window from `00_input/data.csv`
  (rows 621–927): medians 30.9998 vs 32.0 L/min, −3.13%, quantisation levels {30,31} in-window vs
  {32} out-window — matches the diagnosis artifact and Table 7.
- **Excluded second batch**: 12 run dirs dated 2026-09-18 exist in the archive; 10 lack
  finalization (genuinely interrupted); **2 closed all gates** (see Major Issue 3).
- **Cost claim**: the drawn re-execution's event span recomputes to exactly 117.1 min.
- **Determinism/repro**: `suite_determinism.json` 45/45 identical (timestamps excluded);
  `repro_report.json` 153/153 fingerprints, 12/12 coverage and execution proofs, zero drift.

## Major Issues

1. **The neutralized-identifier re-run must be executed before the accuracy headline is
   acceptable (anchors: Abstract; §1 contribution 4; §7.2 last sentence; §9 "Prompt-knowledge
   contamination"; Table 6; Data availability).** The identifier channel is real and verified:
   all 13 canonical run-directory names embed the documented mechanism or case id
   (`..._bench_tep_d14_reactor_valve_sticking`, `..._bench_skab_cavitation_13`), the leakage
   sentinel checks brief/user-context content but not directory names, and the twelve canonical
   scenarios ran batched under one orchestrating session that could carry names across
   scenarios. Consequently *every* resolved verdict that carries the headline Top-1 (the three
   TEP hits; the fourth, batch-93, is already identity-discounted) is identifier-exposed, and the
   paper says so. My audit confirms the disclosure and bounding apparatus is accurate and
   internally consistent (joint floor 0/9 is arithmetically forced; the 16-h re-run cost equals
   8 scenarios × the measured 2.0 h). But a Q1 journal should not publish a headline accuracy
   number whose own text concedes it is "recall-possible" pending a committed control —
   especially when the control is fully specified, bounded (~16 h), and carries a released
   contract. Disclosure-plus-contract is exemplary practice, but it is a promissory note, not
   evidence. **Required fix**: execute the re-run (opaque hash run ids, identifier-stripped brief
   headers, one orchestrating session per scenario, all eight TEP+SKAB fault scenarios) and
   report it in a revised manuscript, including the promised keyword-coverage re-check (§7.2)
   and a pre-stated statement of which reading (identity-inclusive vs identity-strict) becomes
   headline conditional on its outcome. If the re-run is genuinely impossible before the
   publication deadline, the alternative is full demotion: Top-1 must move out of the abstract,
   contribution list, and conclusion as a headline number, with the identity-strict 3/9 and the
   0/9 floor promoted to primary — I would accept that only under protest, since the experiment
   is cheap and the authors themselves call it "the first post-revision execution".

2. **The grading instrument is author-designed, calibrated in-sample, and shared across the
   compared arms; what the current disclosures still do not provide (anchors: §6.1 (C1); §6.2
   Metrics; §7.2 disclosures; Table 6 instrument-readings block).** The instrument-readings block
   (identity-strict row, batch-93-excluded 3/8, leave-one-token-out 3/9–4/9, branch-localized 8/9)
   is the right structure and every number in it reproduces; the LOTO sensitivity and the
   branch-localized reading are genuine strengths. What is still missing for instrument validity:
   (i) **external anchoring** — the keyword sets were calibrated by the authors against v1-era
   executions of *these same twelve scenarios* (in-sample), and the blinded expert adjudication
   that would validate the instrument is "planned", so all truth-comparison numbers rest on an
   instrument whose construct validity is self-asserted; the paper admits this, but acceptance
   should require at least one externally anchored reading (e.g., keyword sets and allowed
   verdict sets proposed by an independent process-engineering colleague blind to the outputs, or
   the planned expert adjudication executed on the released evidence chains for the nine fault
   scenarios); (ii) **a LOTO table** — the first-order LOTO analysis is narrative only; a
   per-scenario table (hit tokens, tokens removed, resulting Top-1) is reconstructable from the
   released gradings and should be in the appendix, since the 3/9–4/9 bound is now a headline
   qualifier; (iii) **shared-instrument correlation** — the bare-LLM arm and IDD are scored by
   the same keyword instrument, so instrument miscalibration moves both arms of the central 9/9
   vs 4/9 contrast in the same direction; this is never stated as a property of that contrast;
   (iv) the grader's matching rule (substring? which artifact fields are scanned?) should be
   stated precisely in an appendix — I could infer it, but a reader should not have to.

3. **The excluded second-round batch: two of its twelve runs closed all gates, and the main
   text does not say so (anchors: Data availability "an interrupted, never-graded second-round
   batch"; §8.4 "the remaining eleven fault-or-control scenarios each hold a single current-era
   execution"; released `README-artifact-fields.md`).** I verified the 2026-09-18 batch
   (202609181728xxx–1738xxx): ten runs lack finalization and are genuinely interrupted, but
   `202609181729062` (SKAB control) and `202609181731134` (TEP control) contain complete
   gate-passing artifact sets with `pipeline_finalize_report.json` PASS, and both reached
   DETERMINED-normal verdicts agreeing with the canonical runs. The released README honestly
   discloses "4 of 12 reached final audit; 2 closed all gates" — but the manuscript itself says
   only "interrupted, never-graded", which a reader will take to mean nothing completed, and the
   §8.4 statement "each hold a single current-era execution" is true of the deposit, not of the
   released archive. Because the completions are controls whose verdicts *agree*, reporting them
   would strengthen the paper at zero cost. **Required fix**: state in §8.4 and Data availability
   that two second-batch runs completed all gates (both controls, verdicts concordant), run the
   existing `consistency-audit.mjs` comparison over them or state why the audit's proven-run
   criterion does not apply, and scope the "single current-era execution" sentence to the
   canonical/deposit set explicitly.

4. **Stability evidence is one coarse-criterion pair, and the consistency criterion's
   disjunction is weaker than the prose implies (anchors: §8.4; `consistency_audit.json`
   consistency_rule).** The rule is CONSISTENT = same diagnosis_type AND (same primary equipment
   tag OR same mechanism_class with ≥0.35 cause-token overlap). The actual pair passed via the
   tag disjunct while its free-text token overlap was 0.1417; under this rule, two runs naming
   XMV10 with lexically unrelated mechanisms would still count as stable. The paper is candid
   about the n=1 power limit, the wording drift, the mechanically easy signature of the drawn
   scenario, and the unmeasured yield of one draw — this honesty is a model for the genre — but
   the criterion itself is never critiqued. **Required fix**: (i) report per-pair which disjunct
   fired and the token overlap value in the audit table (the JSON has them; the paper should too);
   (ii) pre-register that future pairs passing only via the tag disjunct with overlap < 0.35 are
   labeled WEAK, not CONSISTENT; (iii) since the supersession rule (latest proven execution is
   canonical) was applied to the only repeat and is immaterial here (Δconfidence 0.02, no
   aggregate changes), add one sentence noting it was checked to be immaterial, closing the
   researcher-degrees-of-freedom the rule otherwise opens. The single-execution bounding of all
   headline claims (every number n=1 per scenario, flagged in Table 6's caption and §9) is
   otherwise honestly done and I do not fault it beyond the above.

## Minor Issues

1. **Abstract, "same-rule family-level comparison: 9/9 vs 9/9"**: this juxtaposes a top-1
   strict-commitment instrument (bare arm) with a set-membership instrument (pipeline top-k,
   design-aided). The phrase "same-rule" is doing quiet work; §8.3 is precise but the abstract
   compresses two instruments into one ratio. Rephrase (e.g., "9/9 top-1 keyword hits for the
   bare call vs 9/9 family-level set membership for the pipeline").

2. **Precision row asymmetry (Table 6)**: the identity-inclusive 4/4 carries a conditional CI
   [51.0, 100] while the identity-strict 3/4 alongside it carries none (its Wilson CI would be
   [9.6, 70.0] — recomputed). Either print both or neither; the caption's explanation does not
   justify printing an interval for only the more favorable reading.

3. **Printing sampling CIs at all for purposive, non-exchangeable scenarios**: the caption
   correctly demotes them to second-order corpus-level uncertainty, but several rows (top-k,
   controls, precision) are bounded at 100% by construction, where a Wilson interval adds no
   information. Consider reserving intervals for the two rows where sampling uncertainty is even
   nominally meaningful, or moving all CIs to the figure only.

4. **R4 payload conflation for the IndPenSim control**: `rubric.json` records the control's R4
   failure with `{"confidence": 0.93, "ceiling": 0.9, "type": "DETERMINED", "allowed":
   ["NORMAL"]}` — the payload carries both a ceiling exceedance and a raw-type/allowed-set
   mismatch without a sub-flag saying which fired. The README's folding note explains the
   SKAB-valve case but not this one; add a sub-key or one README line so the −15 is unambiguous.

5. **Float drift**: Table 6 is first cited on p. 22 and appears on p. 25; the preamble declares
   float placement best-effort, but for the paper's single most important table, `\begin{table
   [!t]}` on the citation page or a sideCaption layout should be attempted.

6. **Per-stage cost medians (§9 Cost)**: I reproduced the 117.1-min event span of the drawn
   re-execution exactly, and its per-stage spans (ontology 14.0, statistics 22.2, diagnosis 26.9,
   reviews 9.8+21.8 min) are close to but not identical with the quoted medians (≈14/22/20/29),
   which are presumably medians over 13 runs. Release the per-run span table (it is one groupby
   over the event logs) so the medians are checkable without re-deriving them.

7. **One-directional verdict typing is disclosed with the "8/9 is an upper bound" caveat —
   good — but the corpus's typing power is even thinner than stated**: only one of nine fault
   scenarios (SKAB valve) had a DETERMINED-only allowed set, so the benchmark could have flagged
   over-capping in at most one scenario by construction. State that count; it recalibrates the
   reader's reading of "8/9".

8. **Top-k reconstructability**: the gradings record `kw_hits` but not *where* the hit occurred
   (primary finding vs a surviving hypothesis); the top-k count requires re-reading
   `diagnosis.json`. It is fully reconstructable from released artifacts (I did so), but the
   grading record should carry the matched artifact field so graders-of-graders need not re-parse
   free text.

9. **FE no-candidate figure transcription**: the paper transcribes FE's 8/11 while flagging that
   FE's own text contradicts it (faults 10 and 13 named as failing). This is the right handling,
   but Table A1's row should carry a superscript pointing to that flag so the number is never
   quoted without it.

## Verdict: MINOR REVISION

Every number I recomputed — nine Wilson intervals, the identity-strict accounting, the 6/9
forced-commit counterfactual, the seeded draw, the rubric/judge aggregates, the raw-data
signature, the event-span cost, and the determinism/repro gates — reproduces exactly from the
released artifacts, which is rare and to the authors' great credit. The revision is minor in
scope but non-negotiable in one respect: the neutralized-identifier re-run (Major Issue 1) is
fully specified, bounded at ~16 h, committed by the authors themselves as "the first
post-revision execution", and must be executed and reported before a headline accuracy claim that
the paper itself concedes is recall-contaminated can stand in a Q1 journal; the remaining items
(Issues 2–4 and the minors) are disclosure, tabulation, and phrasing fixes that do not require
new methodology.
