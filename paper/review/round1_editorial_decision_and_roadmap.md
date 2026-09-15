# Editorial Decision — Round 1 (AEI simulation, five-seat panel per academic-paper-reviewer v1.11.1)

Date: 2026-09-15 · Manuscript: main.tex (37 pp, v2 full-pipeline benchmark) · Language: English

## Panel verdicts

| Seat | Verdict | Key blockers |
|---|---|---|
| Journal-Fit Reviewer (EIC) | Major Revision | model undisclosed; no archived release; application value stops at simulators; presentation defects |
| Reviewer 1 (Methodology) | Major Revision | model/decoding undisclosed; rubric unitemised + no validity evidence; no ablations; single runs; FE alias overlap |
| Reviewer 2 (Domain) | Major Revision | PCA-detectability misattribution; FE no-candidate condition omitted; "six baselines" contradiction; no ablation/repeats; ceiling mapping unpublished |
| Reviewer 3 (Perspective) | Major Revision | model/decoding undisclosed; "calibration" is gate-enforced compliance; single runs + repair selection; grading-key provenance; deployment demonstrated-vs-projected; human-factors grounding absent |
| Devil's Advocate | 4 CRITICAL / 8 MAJOR | C1 self-eval loop; C2 model + FE Table 2 omitted; C3 contamination defense contradicted by cause-table dynamic forms; C4 REPRODUCIBLE oversell |

**Decision: Major Revision.** All five seats endorse the core assets (evaluation-contract engineering, mechanism-correct verdicts, honest reporting) as publishable after revision.

## DA CRITICAL adjudication (Checkpoint Rule #4)

- **C1 (closed self-evaluation loop)** — VALIDATED in part: the rubric/keywords/allowed sets are author-designed and no external anchor exists in the paper. Adjudication: accept the critique; revision (i) repositions the rubric as an author-designed protocol-compliance checklist (not a quality judgement), (ii) releases scoring keys with the benchmark definitions, (iii) scopes all accuracy claims as keyword-rubric-relative, (iv) commits to the already-planned blinded expert adjudication as the external anchor. Partially unresolved until the expert test exists → blocks silent Accept; recorded here.
- **C2 (undisclosed model + omitted FE no-candidate condition)** — VALIDATED. Revision: implementation disclosure (engine, model family, snapshot, decoding non-exposure, run window, degradation status); FE Table-2 no-candidate condition (8/11 both models, top-3, lenient) added to §2.2/§8 and Table 5; o1-preview parity on shared detectable faults stated in abstract.
- **C3 (contamination defense vs cause-table dynamic forms; L6 channel)** — VALIDATED. The documented cause table includes per-fault dynamic forms, so label recall can produce mechanism names. Revision: §8 rewritten to acknowledge recall cannot be excluded by form-discrimination alone; retrieval disclosure added (RAG engine unreachable in all runs — no L6 lookups fired; degradation recorded in event logs); novel-disturbance suite remains the definitive control (acknowledged limitation).
- **C4 (REPRODUCIBLE oversell; single-run)** — VALIDATED. Revision: gate renamed in claims as artifact/consistency verification; abstract/conclusion wording aligned; single-execution framing added; per-scenario repair counts disclosed; pre-registered repeat-study protocol stated.

## Consensus findings → Revision Roadmap (immutable; items R-01…R-20)

- R-01 Model/engine/decoding disclosure table in Implementation (EIC-M1, R1-Maj1, R3-Maj1, DA-C2)
- R-02 FE comparison completeness: no-candidate condition, top-3+alias scoring, o1 parity, IDV1 abstract phrasing (R2-Maj2, DA-C2/M2, R3-Min4)
- R-03 PCA-detectability attribution: {3,4,9,15} = FE's PCA implementation; cite Russell et al. 2000; qualify IDV4 (R2-Maj1)
- R-04 Baseline-coverage wording: four scored baselines; two scored where FE excludes (R2-Maj3)
- R-05 Rubric: itemised deductions + repositioned as author-designed compliance checklist + circularity disclosure (R1-Maj2, EIC-Min3, R2-Min3, R3-Min2, DA-M6)
- R-06 Calibration → ceiling compliance; publish configured cap table + worked examples; split Table 3 row (R1-Maj6, R2-Maj6, R3-Maj2, DA-M6)
- R-07 Single-execution framing + per-scenario repair counts + judge truncation note (EIC-Maj4, R1-Maj4, R2-Maj5, R3-Maj3, DA-C4/M4)
- R-08 Ablation/engine-independence: retract empirical claim → design axis; pre-registered ablation matrix as future work (R1-Maj3, R2-Maj4, R3-Maj5, DA-M7)
- R-09 REPRODUCIBLE → artifact-consistency verification wording (R1-Min5, DA-C4)
- R-10 FE top-3+alias disclosure at per-fault granularity; downgrade "never wrong where a baseline is right" to descriptive; cite IDV3 hardness source (R1-Maj5, DA-M2/m6)
- R-11 Contamination: acknowledge cause-table dynamic forms; L6/RAG retrieval disclosure (DA-C3)
- R-12 Related work: +~14 verifiable references (Qin 2012; Russell 2000; Yuan & Qin 2014; Bauer 2007; Iri 1979; Hill 1965; Heuer 1999; Chow 1970; Morbach 2009; Tao 2019; Parasuraman 2000; Lee & See 2004; Wu AutoGen 2023; Yao ReAct 2023) (R2 missing-refs, EIC-Maj5, R3-Maj6)
- R-13 Human-factors/trust/XAI grounding + deployment governance/accountability paragraph (R3-Maj6/Maj7)
- R-14 Deployment section split demonstrated vs projected; film-line vignette (anonymised, grounded) or cut; GxP hedged with ALCOA+/GAMP 5 framing (EIC-Maj3, R3-Maj5, DA-m3)
- R-15 Data availability: archival commitment + supplementary statement (EIC-Maj2, DA-M8, R3-Min9)
- R-16 Figure/table defects: Fig.2 arrow order 6→7 and CP-9 tag; Fig.3(b) clipped title; Fig.4 ceiling label; Table 4 signature trim + XMV_4 tag; Table 3 row merge/split + CIs (EIC-Min1/2, R1-Min1/3, R3-Min3/5, R2-Min6)
- R-17 Abstract/intro honesty pass (coverage phrasing, IDV1/o1 balance, overconfidence phrasing, single-draw caveat) (R2-Maj3, R3-Min4, R1-Min2)
- R-18 Tone/jargon/housekeeping: colloquialisms; MSC removal; highlights file; "v2 protocol" definition or deletion; CDR expansion (EIC-Min7–12, R3-Min1/6)
- R-19 Scenario-selection rule stated; SKAB blind-case official label + keywords printed; grading-key release commitment (R1-Min6, DA-M1/M5, R3-Maj4 partial)
- R-20 Bibliography hygiene: khan2024→CCE 2025; indpensim entry; rieth year harmonisation; zhao2023llm orphan; author lists; 12.6 pp attribution (R2-Min4/5, EIC-Min5, DA-m7)

## Acknowledged limitations (recorded, not silently dropped)

- L-A: repeat-run stability and ablation matrix not executed in this revision (panel offered scoped alternatives; R1 accepted "explicit single-draw framing + pre-registered plan"). Pre-registered protocol documented in the response letter.
- L-B: blinded expert adjudication of verdicts not yet run (conceded in manuscript §8 already); keyword release + commitment added.
- L-C: no archived DOI yet at submission time; supplementary snapshot accompanies the submission, archival on acceptance committed.
