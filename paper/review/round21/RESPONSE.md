# Round 21 — Response to Reviews and Change Log

**Manuscript state reviewed:** `paper/main.tex` as of 2026-09-25 (external-edit-20260924-0224 adopted as base + fix layer). Three fresh blind reviewers: A2 (methodology/statistics), B2 (domain), C2 (presentation). Reports in `reports/`.

## Verdicts

| Reviewer | Verdict | Majors | Minors |
|---|---|---|---|
| A2 methodology | **SATISFIED-ACCEPT** | 0 | 5 |
| B2 domain | MINOR REVISION | 3 | 10 |
| C2 presentation | MINOR REVISION | 2 (+2 caption errors) | 11 |

## B2 majors — all resolved in text

- **M1a (citation error, confirmed).** `merkelbach2024multimodal` author list corrected to the verified seven-author list (Merkelbach, Diedrich, Sztyber-Betley, Travé-Massuyès, Chanthery, Niggemann, Dumitrescu; OASIcs 125, 31:1–31:15), verified against the Dagstuhl landing page (`drops.dagstuhl.de/entities/document/10.4230/OASIcs.DX.2024.31`) before editing; in-text "Merkelbach and Hasenauer" → "Merkelbach et al." Root cause acknowledged: the entry was drafted from a search-engine summary ("S. Merkelbach … Hasenauer") without opening the source. This is precisely the failure mode the citation-verification discipline exists to prevent; all eight round-19 additions were re-checked, and the remaining seven verified clean (B2's 11/12 pass rate independently confirms).
- **M1b (AgentRCA characterization).** §2.2 reworded: the evaluation "scores Top-1/Top-2 against TEP ground truth but, like FE's, ships no machine-replayable external evaluation harness" — the truth-comparison mischaracterization is gone, the Table 1 "no" on reproducibility is retained and now motivated in place.
- **M1c (Vieira 15.3 pp).** Confirmed against the paper body (arXiv:2509.22267, journal ref MSSP 258:114640 matches the bib exactly): "elevating the Macro AUROC by 7.3% and 15.3% for time and frequency representations" under segmentation-level leakage. The manuscript's "up to 15.3 percentage points of Macro-AUROC" stands as printed; no text change required. Author list also re-verified (Victor Afonso Bauler per the arXiv abs page; the HTML full text abbreviates).
- **M2 (FE-replication verification gate).** One sentence added to §7.3 stating the gate and its numbers — re-verified live on this machine before writing (`baseline-lab/scripts/verify-fe.mjs`: PASS 21/0, T² max rel. err 2.8e-12, anomaly flags 500/500 per fault, contribution mean rel. err ≤1.3e-12, identical trigger indices, FE's per-component clip-then-sum convention) — plus a clause in the Table 5 (tab:ablation) caption and a pointer via the §7.3 sentence.
- **M3 (filter attribution).** §4.5 sentence bound to the design claim ("the mechanism by which the pipeline bars control-loop correlations from causal citation") with the corpus limit stated in place: the filter-free bare arm also passes its two covered controls, and isolating the filter's contribution requires the pre-registered filter-disabled arm.

## B2 minors

- m2 (6/6 ceiling): clause added in the tab:ablation caption. m3 (digest is a pipeline product): clause added at the 9/9-vs-4/9 sentence and in the caption. m4 (FE trigger vs scoring screen): half-sentence added at the suite-matrix paragraph. m7 (survey regime limitations): sentence added in §2.2. m1/m5/m6/m8/m9/m10: no action or already satisfied (m1 resolved via the abstract rewrite below; m6: the branch-localized reading is defined at §5.1 first use and used with back-references; m8 explicitly no action per B2).

## C2 majors — all resolved

- **M1 (abstract).** Rewritten to be self-contained: 217 words (limit 250), one parenthetical, reading-structure taxonomy (upper-bound / identity-strict / branch-localized / one-of-three-blind / byte-identical scoping) removed from the abstract; a single pointer sentence retains the worst-case-bounds commitment ("reported alongside explicit worst-case bounds under the disclosed identifier-recall channel"). The taxonomy remains defined in §5.1 and analyzed in §7.2/§9. Keywords reduced 7 → 6 ("Evidence grading" dropped); the keyword block no longer splits across pages 1→2.
- **M2/M3 (appendix tables).** Table A1 (tab:perfault) and Table A2 (tab:baselinedetail): `\resizebox` removed, set in `\footnotesize` (8 pt, ≥6 pt floor) with ragged-right narrow columns; captions cut from ≈200 to ≈95/115 words (the FE no-candidate contradiction note lives once in §2.2; glossary compacted). Table 6 (tab:overall) caption cut from ≈230 to ≈105 words, with the interval-rounding convention ("bounds rounded half-up to one decimal") now stated. Table 8 (tab:ablation) wall-clock commentary removed. Build: 0 errors, 0 overfull, 59 pages.
- **Caption errors.** Fig. 10: asterisk now glossed as "the mechanism-blind fault scenario SKAB cav*" (was: "the brief-blind control"). Fig. 3: chip legend reworded to the drawing's actual coding (grey = script-dominated Step 0/1 and Step 9; blue = agent-executed stages incl. hybrid Step 3), verified against `fig_trace.html` source before rewording. Fig. 4 caption aligned with its legend ("shaded grey rows = controls").

## C2 minors

- BrE→AmE harmonized (`quantised/quantisation/synchronised/itemised/synthesised/anonymised/defence/localised` → American forms) in main.tex **and** figure sources; Fig. 7's "localised" fixed at source and re-rendered. Fig. 6 in-panel "Quantisation" → "Quantization" and "Volume Flow RateRMS" → "Volume Flow Rate RMS" at source, re-rendered. Fig. 3 smallest detail lines bumped at source (25→27 px, 26→28 px at 1500-px canvas → ≥6.2 pt print) and re-rendered. Not done, with reasons: float-drift tuning and the Table 9 28-page forward reference (C2 itself: "acceptable for print"; the forward reference is load-bearing for the framework section); the 8.5/9.2 parenthetical-density restyle (stylistic, risk of introducing errors late); em-dash density left as-is beyond the abstract fix.

## A2 minors

- #2: rounding convention now stated (Table 6 caption). #3/#4: corpus-freeze timestamps added to Data availability (aggregation generated 2026-09-18 01:02 UTC; second batch's first run directory 09:28 UTC; exclusion chronological, not selective; the two gated control runs noted as latent within-era agreement evidence). #1: proof-stage action unchanged; contingency language retained verbatim. #5: repo hygiene — the canonical run directories live at `workspace/diagnostic-runs/` under this repository; `D:/idd-run-archive/...` in the round-20 dossier instructions is stale (a junction legacy); corrected in the round-22 reviewer brief.

## Artifact integrity

- `refs.bib` accent regression introduced and caught during this round's edit transport (`Trav{\'e}` lost its backslash mid-write); fixed and re-verified: fresh bibtex run, 0 "skipping" warnings, `main.bbl` carries the corrected accent sequence. Full build after all changes: pdflatex ×2, **0 errors, 0 overfull, 59 pages**; preprint (12 pt) variant regenerated: 75 pages, 2 sub-2 pt float overfulls (accepted). `pagepng/` regenerated from the current build (59 pages, C2's process note actioned). All re-rendered figures: fig_casestudy, fig_tep_perfault, fig_trace, fig_calibration (+ pass over the rest via `render_all.sh`).
