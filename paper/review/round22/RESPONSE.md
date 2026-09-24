# Round 22 — Verification Pass Response

Round 22 dispatched two fresh blind verification reviewers after the Round-21 fixes (reports in `reports/`):

## D2 (domain verification) — VERDICT: SATISFIED-ACCEPT

All five Round-21 B2 satisfaction conditions verified against primary sources, independently:

1. **Merkelbach citation** — refs.bib 7-author list byte-consistent with the Dagstuhl DROPS record; "Hasenauer" zero matches in main.tex/refs.bib; in-text "Merkelbach et al." on printed p.5.
2. **AgentRCA wording** — new sentence factually consistent with the arXiv full text (40.0/61.5 confirmed verbatim, exclusions and reasons confirmed).
3. **Vieira 15.3 pp** — source sentence located in arXiv:2509.22267v1 §6.1 ("7.3% and 15.3% for time and frequency representations"); bib matches the arXiv journal-ref exactly.
4. **FE-replication gate** — D2 re-ran `node baseline-lab/scripts/verify-fe.mjs` independently: PASS 21 / FAIL 0 (max T² rel err 2.84e-12; contribution ≤1.17e-12); printed in §8.3 and the Table 8 caption.
5. **Filter attribution** — printed §4.4 carries the mechanism phrasing + the non-isolation disclaimer cross-referencing the bare arm's 2/2 covered-control passes and the pre-registered filter-disabled arm.

Bibtex re-run on a scratch copy: exit 0, no skipping warnings; merkelbach bbl entry renders all 7 authors with correct accents.

**D2 non-blocking observation adopted anyway (citation-accuracy discipline):** the `wei2026agentrca` bib title carried an "AgentRCA:" prefix absent from the arXiv-registered title ("Agentic Root Cause Analysis through Evidence-Grounded Reasoning", Amaury Wei and Olga Fink — authors re-verified). Prefix removed; full bibtex cycle re-run (0 skipping), main.pdf 59 pp regenerated.

## P2 (presentation verification) — REMAINING-ISSUES → both fixed and print-verified

P2 verified 4 of 5 conditions PASS (appendix tables at footnotesize off the resizebox floor with unhyphenated ragged-right cells; both caption errors fixed against the drawings; zero British spellings in main.tex; re-rendered figures clean). Two residual items, both closed after its report:

1. **"byte-identically" remained in the abstract** (the one machinery string my rewrite missed). Fixed: the sentence now reads "re-running the deterministic suite arms reproduces all 45 recorded run outputs exactly." Verified on the re-rendered p-01.png at print resolution.
2. **"quantised" survived in two figure assets** (Fig. 5 calibration IDV14 annotation; Fig. 7 per-fault IDV14 cell) — my figure-source sweep covered quantisation/localised but missed the bare quantised form. Fixed at source in `fig_calibration.html` and `fig_tep_perfault.html`, both figures re-rendered, and the sweep extended to all ten figure HTML sources (zero British spellings remain in `figures-html/`). Verified on the re-rendered p-30.png ("quantized stepping, lag 1→5").

After both fixes: full recompile (main 59 pp, 0 errors / 0 overfull; preprint 75 pp), pagepng set regenerated from the final build. A scoped confirmation check of exactly these two printed spots (p-01 abstract sentence; p-30/p-35 figure strings) is archived in `reports/P3-spot-confirm.md`.

## State after Round 22

- A2 (Round 21): SATISFIED-ACCEPT, 0 majors; its minors #2/#3/#4 folded in during Round 21 (rounding convention; corpus-freeze timestamps; latent-stability note), #1 is the proof-stage re-run contract, #5 repo hygiene noted.
- B2 conditions: closed and independently verified by D2.
- C2 conditions: closed; P2's two residuals fixed with print-level evidence.
