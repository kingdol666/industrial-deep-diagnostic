# Round 40 — Regression Check (loop iteration 2, 2026-09-26)

Trigger: loop wake (iteration 2) + user request for a final objective publishability assessment.
Method: two fresh seats — (S1) GfA compliance regression audit (source + compiled PDF), (S2)
hostile statistician + production editor (fresh, blind). All findings fixed and re-verified in
this round; loop stopped afterward (see "Stopping decision").

## S1 — compliance regression: 8/8 prior fixes verified landed; 1 regression found & fixed

All round-39 fixes confirmed in sources and the compiled PDF (arXiv 8/8 "arXiv preprint"; BrE
sweep complete incl. figure HTML; abstract 4 new phrases consistent with §6/§7/§8/§9 and Tables
6/7/8; AI declaration correct; caption edits render; identity-strict 3/8 arithmetic confirmed
against Table 6; 96.3 = 1155/12 confirmed). One layout regression:

- **R1 (fixed)**: the longer abstract pushed the keyword "ontology" onto page 2. Fixed by
  trimming two unprotected abstract phrases ("verdicts that each name the measurement that would
  settle" → "verdicts, each naming the measurement that settles"; "evaluation framework of
  provenance-labeled artifacts" → "provenance-labeled evaluation framework"), abstract
  240→236 words; all six keywords verified back on page 1 (pdftotext -f 1 -l 1).

## S2 — hostile stats + production: Minor Revision; 3 findings (2 fixed, 1 rejected after recomputation)

- **F1 (fixed)**: "authorise" → "authorize" (main.tex §9 deployment governance; missed by the
  round-39 sweep family list).
- **F2 (fixed)**: "semantic judgement" rasterized in fig_trace.png legend → "judgment" in
  fig_trace.html, re-exported (1500×2400 → 4416×6607), visual re-check PASS.
- **F3 (fixed)**: controls Wilson lower bound printed [43.9, 100.0] but the paper's stated
  convention is z=1.96 with half-up rounding → 43.8494 → **43.8**. Verified by independent node
  recomputation (z=1.96 → 43.8494; z=1.959964 → 43.8503). Changed in Table 6 (main.tex:416) and
  fig_forest.html row data; fig_forest re-exported (4379×2063), visual re-check PASS.
  **Process note**: the reviewer's formula was initially suspected wrong, but a node check
  overturned that suspicion — the reviewer was right. Both directions of verification matter.
- Rejected/optional (no action): figure legends' "Khan et al., 2025" author–year style vs numeric
  citations (optional, production-stage); `\definecolor{iddgrey}` rename (internal only);
  A2's "(one is in Chinese)" repeated disclosure (not required).
- S2 clean bill: 8/9 Wilson CIs recompute exactly (the 9th was F3); every denominator matches its
  metric; the three ablation framings mutually consistent and artifact-supported (incl. bare-arm
  strict 9/9, forced-commitment 6/9 with three wrong ≈ random-commitment expectation 6.08,
  family-level both arms 9/9 via root_cause_kw_hit=true on all nine gradings); zero broken refs /
  duplicate labels / orphan floats in main.pdf; 76/76 bib entries cited.

## Post-fix state

- main.pdf: **60 pages, 0 errors / 0 Overfull / 0 Float-too-large / 0 ref-warnings / 0 undefined,
  bibtex 0 skipping; abstract 236 words; all six keywords on page 1**; pagepng_r40 visual gate
  2/2 PASS (p-24, p-36).
- main_preprint.pdf: 75 pages, 0 errors/warnings (3 known 12pt-variant float overhangs remain —
  submission-prep task, see round39 record).

## Stopping decision

Round-40 findings were all at the spelling / last-place-rounding / single-page-break level — the
defect curve has flattened to the achievable steady state predicted in round 38. Internal review
cannot reduce the remaining acceptance risk, which is (a) evidence-side (pre-registered reruns not
executed — author decisions) and (b) inherent peer-review uncertainty. Loop stopped by the agent
after this round's fixes; no further wake armed. Any future loop should start from NEW material
(e.g. executed reruns), not from re-reviewing the same text.
