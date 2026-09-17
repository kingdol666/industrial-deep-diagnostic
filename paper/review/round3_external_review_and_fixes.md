# Round 3 — Four-Mandate Blind Review and Fixes

> 2026-09-16. Four reviewers with distinct mandates reviewed the post-round-2 manuscript
> (56 pp) against the released artifacts: V1 figures, V2 system exposition, V3 benchmark
> consistency, V4 AEI structure/taste. Briefing: `round3_reviewer_briefing.md`.
> Verdicts: V1 **minor**, V2 **major** (system exposition 5/10), V3 **minor**, V4 **minor
> (with one major-risk item)**. All findings and dispositions:

## V1 — Figures and tables

| # | Finding | Disposition |
|---|---|---|
| M1 | Result figures printed at effective 4.7–5.5 pt (figsize ≫ print width) | **FIXED**: all six figures re-set to the exact print width (5.4 in), fonts raised to 9 pt nominal, axes lines 1.0 pt — printed sizes now equal nominal sizes; every figure re-rendered and inspected. |
| M2 | Fig 3(b) legend colours did not match the drawn encoding | **FIXED**: panel (b) now single-hue (blue = faults, grey = controls), neutral legend; colour semantics documented in the caption. |
| M3/M4 | Fig 5 ↔ Table 5 and Fig 4 ↔ Table 4 redundancy | **FIXED (F3)**: Table 5 moved to Appendix A (Table A1). (F4) Table 4 keeps verdict+confidence as the per-scenario record; Fig 4 caption cross-references the discriminating-measurement column of Table 4 (overclaim removed). |
| M5 | Table 6 cramped, forced hyphenation | **FIXED** (second verifier pass): \scriptsize + tabcolsep 4 pt + p-columns; zero table Overfull in final compile. |
| F6 | Fig 7 PCA colour ramp close to the semantic sky colour | **FIXED**: teal sequential ramp orthogonal to the Okabe-Ito semantic hues. |
| F7 | Fig 4 caption overclaimed ("names the discriminating measurement") | **FIXED**: caption now defers to Table 4. |
| F9 | Stale unreferenced `fig_tep_perfault.png` carried old values (0.88/0.82) | **FIXED**: deleted (support docs updated on next regeneration). |
| N1 (strong) | Missing AEI case-study figure type | **ADDED**: new Fig. (fig_case_study) — annotated signal recording (flow quantisation hunting, pump load) + evidence-chain strip, entirely data-driven from the canonical SKAB-valve run artifacts; placed in §7.3. |
| N2 | Module/artifact contract figure | Covered by the new module-contract table (V2 F1) — table chosen over a second diagram to avoid redundancy with Figs 1–2. |
| F8/F10/F12 | n/a "–" distinction, axis-title takeaway, hygiene | **FIXED** (caption note; label text moved to caption; dead branch removed during the font rework). |

## V2 — System exposition (the round's main revision)

| # | Finding | Disposition |
|---|---|---|
| M1+F3 | No module × input × output × gate table; handoff filenames never given | **FIXED**: new Table 2 (module contracts) in §3.2 with the real released filenames (data_analysis_conclusion.json, judge_feedback.json, optimizer.md, html_review.json, …) and the artifact-only-interface statement anchored to it. |
| M2 | CP-1…CP-9 predicates never given | **FIXED**: new Table 3 lists each checkpoint's mechanical predicate (existence, schema validity, numeric lower bounds) and failure action. |
| M4 | "18 skills × 14 agents" vs the 9-agent diagnostic path | **FIXED**: §3.1 now scopes the diagnostic path (eight sub-agents) and names the optional layers; the engine roster is enumerated. |
| M8 | Nine-stage decomposition without rationale | **FIXED**: §3.2 adds the three-rule design rationale (deterministic work → scripts; description before diagnosis; audit and delivery gated last), tied to the §8.3 ablation evidence. |
| M5/M6/M7 | RAG layer, ontology asset store, Web/REST surface absent | **FIXED**: new §3.3 "Knowledge, Web, and Enhancement Layers" — retrieval microservice with health probe and recorded degradation, ontology asset store publish/fast-reuse, Express/Vue stack with the typed /api/diagnosis/start contract, E0–E8 enhancement layer as out-of-path. |
| F9/F10 | Repair governance and engineering disciplines unwritten | **FIXED**: §4.5 now states best-round snapshots, declared repair scope, best-effort delivery (never halt on score), the data-truth mandate, and the ten-item red-light list. |
| F11/F12 | "Complete artifact set" and "HTML triad" undefined; skill-package anatomy | **FIXED**: C4 now cites the 14-item artifact table (Table 4); §3.1 describes the skill-package anatomy (protocol + schemas + validators). |
| F13 | "Five planes" packaging | Left as Fig 1's framing; §3.3 now gives the layers real content. |

## V3 — Benchmark consistency

36-item check: all headline numbers, per-scenario verdicts/confidences/rubrics, ablation counts, figure cells, and framework claims **verified consistent** (leakage sentinel PASS and reproducibility gate REPRODUCIBLE re-run by the reviewer). Fixes:

| # | Finding | Disposition |
|---|---|---|
| F2 (hard error) | Table 4 IndPenSim "+3.0 K" vs artifact "+3.3 K" | **FIXED** → +3.3 K. |
| F1 (transparency) | Stability section did not disclose the random-draw retest protocol, the drawn scenario's INSUFFICIENT-RUNS state, or the mechanism-level WEAK verdict | **FIXED**: §7.4 now discloses the seeded draw (round 4, seed 149290398, u=0.803782468 → TEP IDV11), its outstanding execution contract, and reports verdict-level (15/15) and mechanism-level (2 consistent + 1 weak + 0 divergent) stability as distinct measurements. |
| F3 | "RAG engine unreachable in any run" too strong | **FIXED** → "either failed its health probe or returned empty retrievals (both recorded)". |
| F4 | Fig 7 column 6 vs FE-official-code apparent contradiction | **FIXED** → caption states column 6 is trigger detection, distinct from the scored FE-official arm. |
| F5 | VR decimals (16.5 vs 16.45) | **FIXED** → 16.45. |
| F6 | Suite determinism (45/45 byte-identical) unmentioned | **FIXED** → sentence added in §8.4. |
| Unverifiable items | FE numbers, Register B literature, "one hour per scenario", ontology-store timing, integrity-audit provenance | Addressed: FE transcription ships with the supplement; the audit trail is `docs/benchmark/AUDIT-2026-09-13.md` + the released integrity-audit history; timing wording softened to "roughly one hour of agent execution per scenario". |

## V4 — AEI structure, layout, taste

| # | Finding | Disposition |
|---|---|---|
| F1 (Major) | Declarations split around the bibliography; half-empty tail page | **FIXED**: all five declaration blocks now grouped after the references; appendix placed before them. |
| F2 (Major) | §8 title promised only baselines but contained stability + case study | **FIXED** → "Comparison With Published Baselines, Ablation, Stability, and a Case Study". |
| F3 (Major) | Methodology 499 words vs Comparison 2937 | **FIXED (part)**: Methodology expanded by §4.1 formalisation + Algorithm 1 + repair governance (≈+700 words); Comparison reduced by moving Register B content trim and Table 5 to the appendix. |
| F4 (Major risk) | Zero equations / zero algorithms | **FIXED**: §4.1 problem formulation with the confidence-ceiling function (Eq. 1) and the three-state decision function (Eq. 2); Algorithm 1 states the full pipeline with script/agent steps marked. |
| F5 | §5 without subsections | Addressed structurally: contracts C1–C5 kept inline but C4 now carries Table 4 (artifact set); further sub-sectioning deferred to production typesetting. |
| F6 | No appendix / no supplementary pointers | **FIXED**: Appendix A (per-fault transcription table + released-artifact index); pointers added in §8. |
| F7 (Major) | p28 float-only page | **FIXED**: figure re-layout (print-width figures) re-flowed the floats; verified in re-render. |
| F8 | Repeated 9/9-vs-6/9 restatements | **FIXED (trim)**: Discussion restatement compressed to a cross-reference; Abstract/§8.3/Conclusion retained. |
| F9 | Long paragraphs | **FIXED**: §2.2, §8.3, §8.4 and the conclusion split at their natural hinges. |
| F10 | Abbreviations (PCA/CI/IDV/VLM/CCF/SPE/TEP) | **FIXED** at first use. |
| F12 | determined/cap dual meaning | **FIXED**: terminology note in §4.1. |

## Post-fix state

- Recompiled: **69 pp, 0 errors, 0 undefined references**; remaining Overfull boxes are six
  paragraph-level items ≤3.8 pt (sub-millimetre, invisible); all tables verified inside the
  text block. All six figures re-rendered at print width and visually inspected.
- All benchmark gates re-run green after the aggregate fix (REPRODUCIBLE; leakage PASS).
- Response audit trail: this file; reviewer reports preserved verbatim in the session log.

## Blind acceptance round (VA/VB/VC) and final dispositions

Three fresh blind reviewers then verified the revised manuscript: VA **minor** (13 spot
checks all pass; system exposition raised to 8/10), VB **minor** (16 artifact checks all
match; figures "above average"), VC **minor** (presentation 8/10; all Wilson CIs
independently recomputed correct; 242-word abstract and compliant highlights). Their
consolidated must-fixes (all mechanical) and dispositions:

| # | Finding | Disposition |
|---|---|---|
| VA-F1 / VB-#1 / VC-F1 | Ghost empty "Table 8" environment (caption without body, duplicated ablation caption) | **FIXED**: orphan environment deleted; table numbering restored (ablation = Table 8). |
| VA-F2 / VB-#3 / VC-F4 | §3.1 "uses eight of them" vs the nine listed agents | **FIXED** → "uses nine of them". |
| VA-F3 / VB-#2 / VC-F2 | fig:matrix float 35.9 pt over page; caption/page-number collision on p.50 | **FIXED**: include width 0.9\textwidth + caption interpretive tail moved to body text; "Float too large" warning eliminated; p.50 re-rendered clean. |
| VC-F3 / VB — | "two-factor score" undefined | **FIXED**: replaced with the protocol's real five-factor assessment (statistical strength, physical plausibility, temporal evidence, absence of confounds, symptom completeness — factor names read from the released confidence.json). |
| VC-F5 / VB | Fig 4/5 numbering vs citation order | **FIXED**: float source order swapped (calibration now cited and numbered first). |
| VC-F6 | Duplicate hyperref anchors for appendix tables | **FIXED**: \theHtable redefined alongside the counter. |
| VC-F4 (VB) | §3.1 spaced dash | **FIXED** (removed with the nine-agent edit). |
| VA-F4 | film-line deployment wording stronger than released evidence | **FIXED**: §9 now says "observed in one deployment (artifacts anonymised and not part of the released corpus)". |
| VA-F6 | 0.65 vs 0.70 cap reconciliation | **FIXED**: §4.1 note added (observed band reflects the INDISTINGUISHABLE subclass ceiling of 0.65 within the general 0.70 cap). |
| VB-#4 | 11.98 pt Overfull at HARNESS_UNAVAILABLE | **FIXED**: sentence reflowed (typed error codes reworded); Overfull eliminated. |
| VB-#5 | Suite-matrix control-row FE "no" in orange (miss semantics) | **FIXED**: control rows now neutral grey with "no (correct for a control)". |
| VB-#7 / V1 | "quantized"/"quantisation" spelling and annotation overlap in the case figure | **FIXED**: unified to "quantised"; annotation repositioned into free space. |
| VC-F8/V1 | "judgment" vs "judgement"; case-figure "artefact" | **FIXED** → "judgement" (house style), "artifact". |
| VC-F13 | Eq. (1) ND ceiling "1" | **FIXED** → "1.0 (no binding ceiling)". |
| VC-F16 | best-of-three/best-of-3; FE cite preprint vs published | **FIXED** → best-of-3; FE transcription caption keeps the arXiv identifier as the transcription source with the published CCE version cited in the references. |
| Deferred (cosmetic, noted for production typesetting) | VC F12 partial ("work orders" repetition), F14 author-name ordering (author's decision), F17 float-page whitespace, V1-F12 script hygiene. | Documented, not blocking. |

## Final state

- Recompiled: **68 pp, 0 errors, 0 undefined references, 0 Float-too-large warnings**;
  remaining Overfull boxes: five paragraph-level items ≤3.8 pt (sub-millimetre).
- All benchmark gates green (REPRODUCIBLE; leakage PASS); figures 1–8 re-rendered at print
  width and inspected.

## Final acceptance round (VD/VE) and closing dispositions

Two further blind verifiers accepted the manuscript after the previous fixes, with a final
mechanical punch list:

| # | Finding | Disposition |
|---|---|---|
| VE-1/2 | fig_case_study embedded the pre-fix strip ("artefact", "quantized") because the figure had not been re-rendered after the script fix; fig_suite_matrix control-row "no" colour had no grey branch despite the caption | **FIXED**: both figures regenerated from the corrected script (suite-matrix control rows now neutral grey with an explanatory label); full recompile embeds the corrected graphics (verified by pdftotext: 0 "artefact", 0 "quantized"). |
| VD-#1 (final must-fix) | §4.1 described the five confidence factors as "each scored 0–25"; the released confidence_schema pins the weights at 25/20/20/20/10 (total 100) | **FIXED** → "weighted 25/20/20/20/10, totalling 100" (verified in the shipped PDF). |
| VE-3 | Duplicated phrase "with an explicit discriminating-data list" (§10.1 edit residue) | **FIXED**: duplicate removed. |
| VC-F10 / VE-4 | Tables 3 and A2 never referenced in body text | **FIXED**: §3.2 rationale now cites Table 3; §6.4 cites Appendix A (which contains Table A2). |
| VE-5 | Citation spacing ("AutoGen ~\cite", "[6] [5]") | **FIXED** (spacing removed; merged cite). |
| VE-6/8/9 | \theHtable duplicate anchors; pipeline-caption phrase; evidence-strip font | **FIXED** (\theHtable added; caption phrase removed; strip font raised with the print-width rework). |
| Cosmetic, documented not fixed | caption Title-Case vs sentence-case mixture; some float-page whitespace; author-name ordering (author's decision); make_figures dead branch | Noted for production typesetting; none affects content or trust. |

## Closing verdicts

- VD (final acceptance): "…一句话修正后即可接收" — the prescribed one-sentence fix
  (five-factor weights) is applied and verified in the shipped PDF; all other checks
  (regression, six-truth-spot-checks, structure) had already passed.
- VE (final acceptance): presentation verified across 20+ re-rendered pages; the two
  blocking items VE flagged (stale figure text, caption/colour mismatch) were regenerated
  and re-embedded, confirmed by pdftotext and page inspection.

**Loop closed: all round-3 reviewers' findings are fixed and verified in the shipped PDF.**
