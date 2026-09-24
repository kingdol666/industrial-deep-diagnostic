# Reviewer C — Presentation Review (figures, tables, layout, language)

Manuscript: `paper/main.tex` (elsarticle preprint, 10pt). **Build reviewed: `main.pdf`, 59 pages (Sep 24 build).**
Workflow note: the supplied render set `paper/pagepng/p-01…p-50.png` (dated Sep 19) is **stale** — it does not correspond to the current 59-page build. I re-rendered all 59 pages of the current `main.pdf` at 110 dpi and reviewed those; page numbers below refer to the current build. All 10 figure pages, all 10 table pages, and ~10 text pages were viewed at 110 dpi, plus high-resolution crops of `paper/figures/*.png` where 110-dpi legibility was in doubt.

## Paper Summary

The paper presents IDD, a nine-stage agentic pipeline for industrial root-cause analysis built on competing-hypothesis reasoning, L1–L7 evidence grading, an anti-spurious-correlation filter, and machine-checked quality gates, evaluated on a 12-scenario benchmark (SKAB, TEP, IndPenSim) with per-fault FaultExplainer baselines, same-model ablations, and a seeded re-execution. Headline: 4/9 resolved Top-1 (multiple disclosed discount readings down to 0/9), top-k 9/9 family-level, 0 false alarms on 3 controls, with an unusually heavy apparatus of self-disclosed limitations. The presentation burden is correspondingly large: 10 figures, 10 tables (2 appendix), many multi-reading numbers.

## Major Issues

**M1. Result-section figures drift up to 9 pages from their first citations, producing one near-empty page and two half-empty float pages (pp. 30–34).**
Fig. 3 is first cited on p. 22 (opening sentence of Section 7.1) but appears on p. 31; Fig. 4 cited p. 23–24 → p. 32; Fig. 5 cited p. 28 → p. 33; Fig. 6 cited p. 28–29 → p. 34. Readers traverse all of Sections 7.2–7.5 with no figures in sight, then meet four consecutive float pages. Page 30 carries ~10 lines of text and ~85% whitespace (1.6% ink); pp. 32 and 33 are ~45–55% empty. The preamble comment concedes this is "best effort", and `placeins [section]` confines the damage to Section 7, but a reviewer/reader experience this as broken pagination. Fix by reducing figure heights (e.g., Fig. 3 at 0.94\textwidth is a full-page float), interleaving floats between Sections 7.2–7.5, or converting Figs. 3/5 to `width≈0.85\textwidth` so two floats can share pages.

**M2. The abstract is at the word limit and beyond comfortable readability.**
~245 words (within the 250 limit), but essentially one sentence chain carrying the headline claim plus four alternative readings inside a single parenthesis — "(Top-1 44.4%---a provisional upper bound, since run-directory names can embed the documented mechanism; the joint worst-case floor is 0/9; identity-strict 3/9)" — followed by six further parentheticals and appositives. The paper-wide density is extreme: 235 em-dashes and ~600 parenthesis pairs across the manuscript; several sentences (e.g., the IndPenSim scenario definition, Section 6.1, one ~120-word sentence with four nested dash/parenthesis asides) require multiple parses. This is an editorial-pass problem: move reading-structure detail to Section 7.2, keep at most two numbers-with-caveats in the abstract.

**M3. Table 6 (headline results) is the hardest-to-read object in the paper.**
A 20-line caption that re-argues material from Sections 7.2/7.4 (caption duplication), over a resizebox-scaled `footnotesize` table whose narrow value column wraps badly: "upper 4/9, lower 0/9" breaks over three lines; "[51.0, 100] cond. on the deter-mined set" hyphenates mid-word; "5/5 (five of the nine faults capped)" over three lines. The paper's single most important table needs re-padding (wider value column, `\raggedright`), and its caption cut to ~6 lines with the reading-structure notes moved to text.

**M4. Mixed British/American spelling, including inside single sentences and between figure and text.**
US "color" (×14, incl. figure captions "Cell colors") and "behavior" (×2) coexist with BrE "quantised" (×10), "synchronised", "anonymised", "synthesised", "itemised", "computerised" (×2), "labour" (×2), "grey" (×7); -ise adjectives appear in the same sentences as -ize/-or US forms ("three synchronised channels … an actuator behavior", Section 7.3). Figure 1's in-figure text says "14 specialised agents" while the body text (Section 3.1) says "14 specialized agents". One consistent dialect pass (body *and* regenerated figures) is required.

## Minor Issues

1. **Keywords widow**: the last two keywords ("Evidence grading, Process ontology") spill onto p. 2, separated from the keyword block on p. 1 — a side effect of the very long abstract (M2).
2. **Fig. 5 y-axis two-line labels sit at the legibility floor** at print size (≈6 pt effective). At 110 dpi I initially misread "72/72 rows" as "7/72"; verified correct in the 4105×2752 source, but the risk at print size is real. Consider shortening the secondary grey line.
3. **Fig. 10 rotated x-labels are small** (≈9 px at 110 dpi) and the in-figure legend omits the asterisk's meaning (explained only in the caption: asterisk = brief-blind control).
4. **Fig. 9 caption gap**: the orange "no" on IDV3 (FE trigger fails to fire on a true fault — the informative cell) is not glossed; only the green "no" on the fault-free control is explained.
5. **Tables 2 and A2 sit at the legibility margin** (scriptsize inside resizebox): Table 2's long `\texttt` filename cells and Table A2's quoted bare-LLM answers are readable at 110 dpi but will be near 6 pt in print. Table A2's caption alone runs ~15 lines (channel glossary included — legitimate, but consider splitting to a table note).
6. **Table 1**: the "Evidence trail" header wraps, and the IDD row's "yes (L1–L7)" breaks as "yes (L1– / L7)"; widen that column slightly.
7. **"gradeable"** (×2) is a nonstandard spelling ("gradable" is the common form); it is at least used consistently. Similarly "excl." glyphs in Fig. 3 are fine.
8. **Fig. 7 evidence cell says "+18.5/+18.7σ"** while Table 7 and Section 8.1 use "+18.5σ lockstep"; the pair (valve/flow) is presumably intended in the figure — make the table match or gloss.
9. **Sections 6.1's scenario-definition sentence** (IndPenSim) is a ~120-word chain of dash/parenthesis asides that will defeat many readers; rewrite as 2–3 sentences.
10. **Tab. 7 row "Controls (3)"**: the rubric column mixes "100/100/65" into one cell — acceptable, but the 65 belongs to the IndPenSim control and is only explained two pages later; a footnote marker would help.
11. Workflow: the stale `pagepng/` set (50 pp) should be regenerated or deleted to avoid confusing later rounds.

Positive presentation findings, for balance: figure palette (Okabe-Ito) is consistent across all ten figures and matches the LaTeX preamble definitions; caption-vs-image number checks passed everywhere I probed (Fig. 3's 0.63/cap-65, judge 97/100, ENDORSED, PASS; Fig. 4's fractions/CIs vs Table 6; Fig. 5's 0.70/0.90 thresholds and +0.01/+0.03 crossings; Fig. 6's −3.13%, p = 5.7×10⁻¹⁵⁸, 0.327 bar, survivor chips; Fig. 8's five CI rows; Fig. 9's detection matrix vs Table 8; Fig. 10's seed and run IDs vs Section 8.4); appendix labeling (Appendix A, Tables A1/A2) is correct; all AEI declarations are present and correctly ordered (CRediT, competing interest, funding, data availability, generative-AI declaration); references carry DOIs; no float escapes its section.

## Figure-by-Figure

- **Fig. 1 (p. 9, architecture)**: five planes legible at 110 dpi; 14 engine chips / 18 packages / 8 sub-agents match caption and text; in-figure "specialised" vs body "specialized" (M4); page mostly float, 2 lines of text at bottom.
- **Fig. 2 (p. 11, pipeline)**: serpentine row and return arrow match caption; blue CP tags match Table 3; amber repair loops annotated "≤3 rounds · global ≤5 · cap 0.50" consistent with Section 4.6; three green hard gates as captioned. Well placed (same page as citation).
- **Fig. 3 (p. 31, IDV4 trace)**: every quoted string/number (onset idx 160, +6.8σ, CS 0.63 cap 65, judge 97/100, ENDORSED FATAL 0, PASS) cross-checks against Sections 7.1/7.5; grey rail labels at the print-size floor; appears 9 pages after citation (M1).
- **Fig. 4 (p. 32, benchmark outcomes)**: bars proportional to dataset fault counts as captioned; six summary tiles match Table 6 (4/9 [18.9,73.3]; 9/9 [70.1,100]; 3/3; 8/9; 94.6/94.7; 12/12); page half empty (M1).
- **Fig. 5 (p. 33, confidence bars)**: 0.70 dashed / 0.90 dotted lines and orange cross markers match caption; all 12 bar values match Table 7; two-line y-labels at legibility margin, "72/72 rows" verified in source (Minor 2); page half empty.
- **Fig. 6 (p. 34, SKAB valve case study)**: pale-amber plateau window (rows 621–927) verified in source; −3.13%, MW p = 5.7×10⁻¹⁵⁸, −0.115 A (p = 0.10), 0.327-bar quantisation, survivors 0.65∥0.60 all match caption and Section 7.4; evidence-chain strip legible.
- **Fig. 7 (p. 37, TEP per-fault)**: cell colors match the caption legend (vermilion ✗ / green ✓ / grey unscored / solid + hatched IDD chips); chips match Table A1; "+18.5/+18.7σ" vs "+18.5σ" shorthand mismatch (Minor 8).
- **Fig. 8 (p. 38, forest)**: all five rows with printed CIs match Sections 7.2/8.1; open markers at the 100% edge as captioned; legible.
- **Fig. 9 (p. 41, baseline matrix)**: detection cells match Table 8 and Table A2 (IDV3 2.9/4.8; IDV4 48.8/100; controls ≈1%); summary tiles consistent; orange "no" on IDV3 unglossed (Minor 4).
- **Fig. 10 (p. 43, consistency audit)**: 13 executions, CS cap 0.70 dashed, re-test pair 0.62/0.60, seed 1003818694, run IDs and CONSISTENT stamp all match Section 8.4; rotated labels small (Minor 3).

Tables: **T1** (p6) fine; **T2** (p10) marginal legibility (Minor 5); **T3** (p10) fine; **T4** (p18) fine; **T5** (p20) fine; **T6** (p25) M3; **T7** (p27) small but readable, controls-row footnote (Minor 10); **T8** (p39) fine; **T9** (p47) dense but readable; **A1/A2** (p59) very dense, A2 at legibility margin (Minor 5).

## Verdict: **MINOR REVISION**

The presentation layer is fundamentally sound: the figure system is palette-consistent and, unusually for a submission this dense, every caption-vs-image number check I performed passed; AEI conventions (declarations, keywords, appendix labeling, numbering) are all in place; the abstract is within the 250-word limit. But four presentation defects are visible to any reader and must be fixed before this is publication-ready: (M1) the 9-page figure drift with a near-empty p. 30 and two half-empty float pages, (M2) an overloaded abstract and extreme em-dash/parenthesis density, (M3) a badly wrapping, over-captioned Table 6, and (M4) mixed BrE/AmE spelling across body and figures. All four are mechanical to repair and none requires re-execution or re-analysis — hence minor revision, not major — but the float-rebalancing pass (M1) needs a full re-render and re-check of the pagination after the fix.

*Counts: 4 major, 11 minor issues; 10 figures + 10 tables individually inspected.*
