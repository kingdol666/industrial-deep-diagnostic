# Round 42 — Preprint Float Fit + Consistency Seat (Loop Closure)

Date: 2026-09-26. Loop: AEI-strictest `$loop` (user re-invocation), iteration 4 of the restarted loop
(rounds 39 → 40 → 41 → 42). Hard cap round44. **This round closes the loop: zero adjudicated
must-fix findings.**

## ① State probes (round41 regression check) — both false alarms

Two suspicious reads surfaced at session restore; both verified as stale mid-round snapshots, not
regressions:

- `refs.bib` `cemri2025mast` — carries the full 13-author list (Cemri/Pan/Yang/Agrawal/Chopra/
  Tiwari/Keutzer/Parameswaran/Klein/Ramchandran/Zaharia/Gonzalez/Stoica), no "and others". ✓
- `fig_pipeline` "(Table 3)" — absent from `.drawio`, `.html`, `.svg`, `_svg.html`; the whole
  render chain (drawio 01:38 → svg/svg.html 01:38 → png 01:39) was re-rendered after the edit, so
  the PNG in the compiled PDF is clean. The aux `fig_pipeline.html` (edited 02:20, not in the
  render chain) is also clean. ✓

## ② main_preprint 12pt variant: 3 float overhangs → 0

Known overhangs (`main_preprint.log`): Table `tab:overall` +122.81pt (line 423),
`fig:casestudy` +21.27pt (line 483), `tab:baselinedetail` +182.78pt (line 734).

Fix (all in `main.tex`, conditional on the class option, **no-op in the 10pt build**):

```latex
\makeatletter
\@ifclasswith{elsarticle}{12pt}{%
  \newcommand{\preprinttabfit}{\scriptsize\selectfont}%    % 12pt \scriptsize = 8pt = 10pt-class \footnotesize
  \newcommand{\preprintcapfit}{\footnotesize\selectfont}%  % 12pt \footnotesize = 10pt captions
  \newcommand{\preprintcasew}{0.92\textwidth}%             % casestudy: keep internal text >= ~6pt print
}{ ...empty... }
\makeatother
```

Applied to: `tab:overall` (`\footnotesize\preprinttabfit` before its `\resizebox`; `\preprintcapfit`
before caption), `tab:baselinedetail` (same pattern), `fig:casestudy`
(`width=\preprintcasew` + `\preprintcapfit` caption). The 12pt `\scriptsize` reproduces the 10pt
build's absolute table font (8pt), so table heights match the accepted 10pt layout. `\preprintcasew`
was set to 0.88 first, then tightened to **0.92** so the figure's internal minimum text stays at or
above the 6pt print floor in the review variant (12% shrink would have put ~6.6pt text at ~5.8pt;
8% shrink still frees ~30pt > the 21.3pt needed).

Result: `Float too large` 3 → **0**; preprint 75pp, 0 errors / 0 ref-warnings / 0 bibtex-skipping.
Remaining: 2 known sub-2pt overfull boxes (0.53pt hbox, 1.41pt vbox) — visually invisible,
documented, not chased. Main build verified byte-level no-op in layout: 60pp, all gates 0,
keywords on p1, abstract untouched (242 words ≤ 250).

`\@ifclasswith{elsarticle}{12pt}` probed in a scratch file before use (elsarticle does not define
`\@ptsize`; the kernel class-option test works).

## ③ Fresh consistency seat (blind, read-only)

Charter: round41 text surgery coherence — abstract ↔ contributions ↔ §7.3 ablation ↔ conclusion;
back-reference targets; citation corrections vs body; three load-bearing statistics re-verified
against `results/benchmark/` artifacts.

Seat verdict: **FAIL** on one must-fix — **REJECTED after dual-source verification**:

- Seat claimed `panickssery2024selfpref` must be arXiv:**2404.13096** ("13076 is stale").
- Independent verification (fetch of arxiv.org/abs pages + web search, both directions):
  **2404.13076 = "LLM Evaluators Recognize and Favor Their Own Generations" (Panickssery, Bowman,
  Feng)** — the bib is correct. **2404.13096 = "Reducing Redundant Computation in Multi-Agent
  Coordination through Locally Centralized Execution" (Bai & Sugawara)** — an unrelated paper; the
  seat's proposed "fix" would have inserted a wrong identifier.
- The seat hallucinated a citation correction while auditing for citation hallucinations. This is
  the round40 lesson ("verify reviewer claims with code, in both directions") now confirmed for
  LLM seats on citation identifiers: **no bib edit was made**.

Everything else the seat checked **passed**, with artifact-level evidence:

- All three headline statistics reproduce from released artifacts: Top-1 4/9 CI [18.9, 73.3]
  (`metrics.json` cdr_ci95 [18.877, 73.335]); rubric 94.6 = 1135/12 with the 96.3 adjusted reading
  reconstructing exactly ((1135+20)/12 → 96.25 → 96.3 half-up); controls 3/3 zero false alarms.
- Ablation numbers agree everywhere (abstract/contrib-2/contrib-4/sec:ablation/tab:ablation/
  conclusion); the 6/9-with-three-wrong counterfactual reproduces from the run directories'
  survivor sets (valve1, cavitation, IDV3, IDV4, IDV11).
- All 44 labels present, zero semantic \ref mismatches beyond the two should-fixes below;
  conclusion back-references (recall-possible tier, expert anchoring, seed 1003818694, Δconf 0.02,
  token overlap 0.1417, 45/45 determinism) all land on real content/artifacts.
- Citation coherence: body claims match corrected entries (MAST taxonomy, SensorIQ benchmark,
  AgentRCA, FaultExplainer transcription 7/11-9/11-8/11 with PCA exclusions).

## Should-fixes (both applied and verified by rebuild)

1. **Conclusion (main.tex:663)**: "8/9 when a survivor must carry the specific form or stream
   branch" claimed a form-specific top-k that no body section computes (only the branch-localized
   IDV3 discount is computed, tab:overall "8/9"; and IDV11's capped set does not carry the
   documented random-variation form, so a form-specific reading would price below 8/9).
   → Reworded: "8/9 under the branch-localized reading, which demands the specific stream branch
   rather than the family alone; Section~\ref{sec:overall}".
2. **Related Work (main.tex:139)**: "(fabricated artifacts → C4, inter-agent misalignment →
   CP-5/6)" used contract/checkpoint notation before definition, and "C4" sits next to a MAST
   citation whose own taxonomy uses C1–C3 labels — misread bait.
   → Now: "(fabricated artifacts → contract C4, Section~\ref{sec:framework}; inter-agent
   misalignment → checkpoints CP-5/6, Table~\ref{tab:checkpoints})".

## Final build state (loop closure)

- `main.pdf`: 60 pages; ERR=0 / OVERFULL=0 / FLOAT=0 / REF=0 / UNDEF=0 / bibtex skipping=0;
  keywords on p1; abstract 242 words ≤ 250.
- `main_preprint.pdf`: 75 pages; ERR=0 / FLOAT=0 / REF=0 / skipping=0; 2 sub-2pt overfulls (known).
- Submission package `paper/submission/` complete (round41): cover letter draft, highlights,
  supplementary zip (789 files / 27MB / 13 canonical run dirs), EM upload README.

## Loop disposition

Stopping rule (armed at round41): round42 zero NEW must-fix → stop; else fix and re-arm, cap 44.
Adjudication: the seat's single must-fix was factually wrong (rejected with dual-source evidence);
its two should-fixes were applied and verified. **Zero adjudicated must-fix → the loop stops here
(no round43 wake armed).**

Remaining items are outside the text loop, by design:

- Author-only submission metadata: ORCID, confirm Zhang = family name, declare prior preprint
  postings, suggested reviewers, personalize the cover letter salutation; competing-interest
  declaration via Elsevier's tool at submission.
- Research-side decisions (pre-registered, unchanged): neutralized-identifier re-run (~16h),
  k≥3 repeats, expert blind adjudication; Zenodo DOI at acceptance.
- Working tree is uncommitted (no commit/push requested; Mimosa scanner blocks commits anyway).
