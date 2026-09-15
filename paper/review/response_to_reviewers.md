# Response to Reviewers (Round 1 → Revision)

Manuscript: "Trustworthy agentic diagnosis for industrial processes" — AEI simulation panel, five seats (Journal-Fit, R1 Methodology, R2 Domain, R3 Perspective, Devil's Advocate). Round-1 decision: **Major Revision** (4× Major + DA 4 CRITICAL / 8 MAJOR). Roadmap: `round1_editorial_decision_and_roadmap.md` (R-01…R-20). Status column: **DONE** = addressed in the revised manuscript; **SCOPED** = executed as the scoped alternative the reviewer explicitly offered, with the full study pre-registered; **LIMITATION** = recorded as an acknowledged limitation per pipeline protocol.

| # | Concern (source) | Response | Status |
|---|---|---|---|
| R-01 | Underlying model/engine never identified (EIC-M1; R1-Maj1; R3-Maj1; DA-C2) | New "Benchmark configuration disclosure" in Implementation: harness (ZCode CLI-driver class), model family and snapshot (GLM family, Sept 2026), decoding non-exposure by the harness, VLM degradation status, execution window, one-execution-per-scenario statement, repair counts. Base-model capability flagged as a confound of the FE comparison; skill-package prompts added to the release. | DONE |
| R-02 | FE comparison incompleteness: no-candidate regime, top-3+alias scoring, o1 parity (R2-Maj2; DA-C2/M2; R3-Min4) | §2.2 now describes both FE regimes incl. General-Reasoning (8/11, both models, top-3, lenient "related"); Table 5 adds the 8/11 row and its caption states top-3+alias; abstract/§8.1 state parity with o1-preview on shared detectable faults (4/4 vs 4/4) and qualify the IDV1 sentence ("o1-preview resolves it"). | DONE |
| R-03 | "PCA-undetectable" misattribution (R2-Maj1) | {IDV3, IDV9, IDV15} at the detection limit, IDV4 weakly detected — attributed to classical studies (Russell et al. 2000 added to refs); the {3,4,9,15} exclusion now attributed to FaultExplainer's PCA implementation everywhere (6 occurrences corrected). | DONE |
| R-04 | "six faults with baselines" contradiction (R2-Maj3) | All occurrences rewritten: "four carry scored per-fault baselines; the remaining two are scored by IDD precisely where FaultExplainer excludes them" (abstract, contribution 4, §6.1, §8, conclusion). | DONE |
| R-05 | Rubric itemisation + validity/circularity (R1-Maj2; EIC-Min3; R2-Min3; R3-Min2; DA-M6) | Deductions itemised in Table 3/4 (SKAB valve −35 = R3+R4; IDV1 −10, IDV11 −10 = R6) and §7.1; rubric repositioned throughout as an author-designed protocol-compliance checklist measuring conformance, not correctness (explicitly: IDV3 scores 100 while being a mechanism-level miss); scoring keys released; circularity disclosed in §5 C1 and §8 (Inference authorship). | DONE |
| R-06 | Calibration naming + unpublished ceiling mapping (R1-Maj6; R2-Maj6; R3-Maj2; DA-M6) | Metric renamed **ceiling compliance** with explicit circularity statement (§7.3); configured caps published (DETERMINED ≤0.90, capped verdicts ≤0.70, anti-oscillation ≤0.50) with worked examples (IDV4 0.75; SKAB cavitation 0.58); Table 3 row split (ceiling compliance 9/9 vs type compliance 8/9); psychometric calibration study scoped as future work. | DONE |
| R-07 | Single execution + repair-loop selection + judge truncation (EIC-Maj4; R1-Maj4; R2-Maj5; R3-Maj3; DA-C4/M4) | "One recorded execution per scenario" stated in abstract/§6.4/§7/§10; per-scenario repair counts disclosed (11× zero, 1× one round); judge-gate truncation (≥90 post-threshold) noted in Table 3 caption; **pre-registered repeat-study protocol** (3× TEP subset; verdict-type stability + confidence spread) added to §8 and the repository. Full repeats are the SCOPED remainder — the reviewer's alternative ("explicitly frame all headline numbers as a single draw") was executed verbatim. | SCOPED |
| R-08 | No ablations; engine-independence non sequitur (R1-Maj3; R2-Maj4; R3-Maj5; DA-M7) | §3.3 empirical claim retracted ("harness consumes any compliant engine's stream identically; quality across engines is an empirical ablation question"); pre-registered ablation matrix (single-LLM on identical digests; filter-disabled controls; engine substitution) specified in Implementation and §8; no attribution claims remain without the ablation caveat. | SCOPED |
| R-09 | "REPRODUCIBLE" oversell (R1-Min5; DA-C4) | Gate renamed **artifact-consistency gate**; abstract/Table 3/conclusion now say "internally consistent (recomputed aggregates, verified fingerprints, execution proofs)"; §5 states it is deliberately not an independent re-execution. | DONE |
| R-10 | FE top-3+alias at per-fault granularity; "never wrong where a baseline is right" downgrade; IDV3 hardness source (R1-Maj5; DA-M2/m6) | §2.2/§8.1/Table 5/Fig.5 disclose top-3-with-alias and the alias classes per fault; claim downgraded to the descriptive per-fault statement ("correct wherever either baseline is correct"; 4/4 vs 3/4 vs 4/4); IDV3 hardness now cited to Russell et al./Chiang et al. | DONE |
| R-11 | Contamination: cause-table dynamic forms; L6 retrieval channel (DA-C3) | §8 now states the cause table records dynamic forms, that recall cannot be excluded by form discrimination alone, that the reasoning chains carry the per-recording discriminative statistics, and that **no external-retrieval channel was active in any run** (RAG unreachable, recorded degradation; L6 evidence never used). Novel-disturbance suite remains the definitive control. | DONE |
| R-12 | Related work depth (EIC-Maj5; R2 missing-refs; R3-Maj6) | Added 14 verifiable references: Qin 2012; Russell et al. 2000; Yuan & Qin 2014; Bauer et al. 2007; Iri et al. 1979; Hill 1965; Heuer 1999; Chow 1970; Morbach et al. 2009 (OntoCAPE); Tao et al. 2019 (digital twin); Parasuraman et al. 2000; Lee & See 2004; Wu et al. 2023 (AutoGen); Yao et al. 2023 (ReAct); plus Goldrick et al. 2019 (IndPenSim). New §2.4 grounds the three-state protocol in levels-of-automation, trust calibration, ACH, reject-tradeoff, and XAI faithfulness. | DONE |
| R-13 | Deployment governance/accountability (R3-Maj7) | New "Deployment governance" paragraph: decision-support positioning, human sign-off before maintenance action, model-change management via engine version disclosure, field-incident → graded-scenario loop. | DONE |
| R-14 | Demonstrated vs projected deployment; film-line anecdote; GxP (EIC-Maj3; R3-Maj5; DA-m3) | §9.1 opens with an explicit demonstrated/projected split; the film-line deployment expanded into an anonymised grounded vignette (context, data, NEEDS_DATA outcome, FDR numbers, redirect of investigation); GxP claim hedged with ALCOA+/GAMP 5 framing and explicitly disclaimed as a documentation property, not system validation. | DONE |
| R-15 | Release without persistent identifier (EIC-Maj2; DA-M8; R3-Min9) | Data availability rewritten: repository accompanies the submission as supplementary material; Zenodo DOI committed on acceptance; prompts and scoring keys added to the release list. | DONE |
| R-16 | Figure/table defects (EIC-Min1/2; R1-Min1/3; R3-Min3/5; R2-Min6) | TikZ Fig.2 bottom row reordered 6→7→8→9 (was 7→6) and CP-9 tag moved to Step 9; Fig.3(b) title un-clipped and x-axis starts at 50; Fig.4 in-figure label "ceiling for capped verdicts only"; Table 4 signatures trimmed to one clause, XMV_4 named, deduction footnote added; Table 3 Top-1/CDR rows merged, overconfidence row replaced by determined-verdict precision 6/6 with CI. | DONE |
| R-17 | Abstract/intro honesty pass (R2-Maj3; R3-Min4; R1-Min2) | Abstract rewritten: coverage phrasing, IDV1/o1 balance, "none of the six determined verdicts was wrong", single-draw caveat, internal-consistency wording. | DONE |
| R-18 | Tone/jargon/housekeeping (EIC-Min7–12; R3-Min1/6) | Colloquialisms removed ("has teeth", "not hypothetical", "unit of publication"); MSC codes removed; title shortened; "v2 protocol" caption phrase removed; CDR expanded at use ("correct-diagnosis rate"); highlights file added (highlights.md); CP-tag semantics defined at Fig.2; author name spelling retained per author preference (indexing split recorded in the submission metadata). | DONE |
| R-19 | Scenario-selection rule + blind-case verifiability (R1-Min6; DA-M1/M5; R3-Maj4 partial) | Documentation-based selection rule stated in §6.1; the official SKAB cavitation label printed; grading keywords + expected verdict sets versioned and released; blinded expert adjudication committed as the outstanding validation step (LIMITATION L-B). | DONE / L-B |
| R-20 | Bibliography hygiene (R2-Min4/5; EIC-Min5; DA-m7) | khan2024faultexplainer updated to the CCE 2025 published version; Goldrick et al. 2019 added for IndPenSim; zhao2023llm orphan deleted; 12.6 pp figure attributed to Vieira et al.; FE no-candidate condition incorporated. | DONE |

## Acknowledged limitations (explicit, per pipeline protocol)

- **L-A (repeat runs).** Headline numbers are single recorded executions. Pre-registered repeat-study protocol (3× TEP subset; verdict-type stability, confidence spread, repair counts) is in the released repository. This executes Reviewer 1's stated alternative.
- **L-B (external anchor).** Rubric/keywords are author-designed; blinded expert adjudication of released evidence chains is committed as the external validation step.
- **L-C (archival).** Supplementary snapshot accompanies submission; Zenodo DOI on acceptance.

## DA CRITICAL adjudication record

- C1 validated-in-part → R-05/R-19 + L-B (recorded; blocks silent Accept — recorded as L-B).
- C2 validated → R-01 + R-02 (fixed).
- C3 validated → R-11 (fixed; definitive control remains future work, recorded).
- C4 validated → R-09 + R-07 (renamed/scoped; repeat study pre-registered).

---

# Stage 3' Re-Review Outcome & Second-Round Mechanical Fixes

Stage 3' verification (independent item-by-item check against the revised manuscript): **17/20 roadmap items VERIFIED, 3 PARTLY, 0 NOT-ADDRESSED; all four DA CRITICAL adjudications verified executed. Outcome: Minor Revision** with a purely mechanical fix list. Second-round fixes applied and verified:

1. **Bibliography rebuilt in the shipped PDF** — the Round-2 build had run BibTeX from the wrong working directory (all in-text citations rendered as [?]; References section empty). Rebuilt inside `paper/`: 37 entries rendered, zero unresolved citations.
2. `indpensim2020` entry restored to refs.bib (had been displaced when Goldrick et al. 2019 was added); both IndPenSim citations now resolve.
3. Duplicate `katal2024causal` entry removed.
4. `morbach2009ontocape` now cited (§2.4 OntoCAPE ancestry sentence) — it had been present in refs.bib but uncited.
5. R-03 residuals corrected: §6.3 and §7.2 no longer attribute the {3,4,9,15} exclusion to Chiang et al. (now: classical detectability cited to Russell/Chiang; exclusion attributed to FE's PCA implementation); §8.3 heading renamed "…a Fault Excluded from Classical Scoring"; Fig.5 caption attributes detectability to FE's scoring with classical sources cited separately.
6. Terminology: §4.5 "Ceiling compliance is then auditable end-to-end…"; §4.1 cap stated as 0.70 with observed caps 0.58–0.65; contribution 3 wording aligned with the renamed artifact-consistency gate.

**Final state:** 45-page PDF, 0 LaTeX errors, 0 overfull boxes >10 pt, 6 vector figures (4 matplotlib PDFs + 2 TikZ), 37 rendered references, zero unresolved citations, evaluator PASS 100.

---

# Addendum: Model-Controlled Baselines Executed (post-Stage-3')

R-08 (ablations) and the model-confound (R-01/C2) are now partially **executed**, not just scoped:

- **FE-protocol replication, same model (GLM, Sept 2026):** TEP 6 faults, both regimes — with candidates: 6/6 FE-style top-3 and 6/6 strict single-verdict; without candidates: 6/6 strict single-verdict. A same-model bare LLM matches the pipeline on documented TEP faults.
- **Single-LLM, identical blind digest (the pre-registered ablation):** 9/9 faults strict keyword hits (incl. IDV3 by literature recall and both SKAB signatures); controls 2/2 normal, zero false alarms (tep_d00 not run bare).
- **Classical PCA baseline (Chiang 2001/Qin 2012 protocol):** IDV3 detection 0.6% (missed), IDV4 T² 9%/SPE 100% (reproducing the Russell/Chiang weak-detection nuance), controls ~1% false alarms; diagnosis stops at variable contributions — no mechanism verdicts.

**Honest conclusion added to the paper (§8.4, abstract, §8, §10):** the bare same-model call matches the pipeline's keyword-scored accuracy on documented public faults (9/9 vs 6/9 resolved + 8/9 ranked); the pipeline's demonstrated margins are auditability, ceiling compliance, execution proofs, and honest capped verdicts — not accuracy. Engine-substitution and filter-disabled arms remain pre-registered future work.

New artifacts: `results/benchmark/baselines.json`, `results/benchmark/baseline_pca_rca.json`, `results/benchmark/baseline_fe_prompts/`, `results/benchmark/baseline_fe_answers/`, `scripts/benchmark/cases/tep_cause_table.json`, `paper/pca_baseline.py`.

---

# Addendum (2026-09-15): Reproducible Stability & Baseline Stages + PCA Re-derivation

Two follow-through items convert the previously ad-hoc consistency and baseline work into
released, agent-executable pipeline stages, and one honesty fix:

1. **Verdict-consistency study formalized (`run-tier.mjs stability`).** The stage re-scans
   every recorded independent pipeline execution (53 run directories) with the same
   extraction semantics as the scorer and reports verdict-type + Top-1 agreement *within
   system versions* (era boundary 2026-09-14: before it, the pipeline lacked the
   anti-oscillation / confidence-cap discipline — a documented system revision).
   **Within-version agreement: 15/15 case-version pairs** (early era 12/12; current era
   3/3 pairs recorded so far); the three cross-era flips on the sensitive scenarios are
   the documented v1→v2 discipline tightening (uncapped DETERMINED → capped
   COMPETING_SET), not run-to-run instability. §8.5 and the limitations paragraph updated;
   scenarios with a single current-era run are flagged with an explicit re-run contract
   (fresh-session full pipeline; artifact copying forbidden) and expanding the current-era
   repeats remains pre-registered.

2. **Same-model baseline comparison formalized (`run-tier.mjs baselines`).** One command
   now re-runs the classical PCA baseline (new deterministic script
   `scripts/benchmark/baseline_pca.mjs` — pure-JS Jacobi, no venv dependency), regenerates
   the bare-LLM prompts idempotently, re-scores the archived raw GLM replies
   (`baseline_llm.mjs score` — verified 0 hard flag differences against the archived
   scoring; 5 no-candidate FE-style flags corrected from the prototype's substring match,
   which missed "IDV(1)"-style strings, to regex IDV extraction), checks answer coverage
   (missing answers produce an execution contract and a non-zero exit — hand-written
   answers are barred), and prints the per-scenario IDD vs bare-LLM vs FE vs PCA table.
   The MD report (§6/§7) and HTML report (§4B/§5B) gain the same sections, all derived,
   zero hard-coded numbers.

3. **Classical PCA baseline re-derived (numbers in Table 8 updated).** The prototype PCA
   script was lost and its T² implementation could not be recovered; the released
   deterministic script supersedes it. Agreement: all SPE statistics and all control rates
   match the prototype exactly (10/10 comparable scenarios); T² fine-structure differs on
   the weakest-signature faults. Table 8's PCA row now reads from the reproducible script:
   IDV3 T² 2.9%/SPE 4.8% (detection limit — the qualitative claim is unchanged), IDV4 SPE
   100% vs T² 48.8% (SPE-dominant detection unchanged), controls 1%. The prototype output
   is archived as `results/benchmark/legacy_pca_prototype.json` for audit. No conclusion
   of the paper is affected; every baseline number is now regenerable by the released
   scripts from the frozen inputs.

New/updated artifacts: `scripts/benchmark/{baseline_pca,baseline_llm}.mjs`,
`scripts/benchmark/run-tier.mjs` (stability + baselines stages),
`results/benchmark/{stability_report.json,baselines.json,baseline_pca_rca.json,
legacy_pca_prototype.json,legacy_baselines_prototype.json}`, `results/benchmark/report.md`
(§6/§7), `experience/benchmark-report.html` (§4B/§5B), `docs/benchmark/README.md` (§3.1),
`docs/benchmark/reproduction-guide.md` (§9/§10).
