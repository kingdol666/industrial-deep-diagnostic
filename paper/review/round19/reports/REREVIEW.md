# REREVIEW — Round 19 Post-Revision Verification

**Method note.** The revision was verified against the compiled artifact
(main.pdf, 50 pp., 0 LaTeX warnings, 0 undefined references, 1 cosmetic
0.5-pt overfull in `tab:overall`) by checklist audit: every ACCEPTED item in
`RESPONSE.md` was string-verified in the PDF text layer (pdftotext) or visually
in the re-rendered figures. 35/35 content checks confirmed present; the four
initial misses were extraction artifacts (line-break hyphenation, bib title
lower-casing) and were confirmed present by relaxed/context search.

## Verification highlights

| Area | Verified in compiled PDF |
|---|---|
| Abstract | "keyword-scores 9/9 faults (no verdict typing)"; "(one repeat pair)"; "byte-identically (timestamps excluded)"; "identifier-recall-possible"; 245 words ≤ 250 |
| C1 provenance | v1-era corpus defined; baseline-synonym provenance disclosed; sentinel scope (not run-directory names) |
| §6.1 | Control-brief honesty paragraph (only SKAB blind); TEP control onset disclosure corrected |
| §7.2 | Identity-strict precision 3/4 + overconfidence ≥1; leave-one-token-out 3/9 ("header"); forced-commit counterfactual 6/9; control-pass scope qualifier; 193–700 L/h |
| Table `tab:overall` | Instrument-readings block (identity-strict 3/9 [12.1, 64.6]; LoTo 3/9–4/9); capped-verdict row relabeled; caption trimmed |
| §8.4 | n=1 repeat pair; power remark; supersession guard |
| §9 | Purposive-selection bias; joint worst case 1/9; recall-possible tier; neutralised-re-run contract (≈12 h + harness extension); GAMP 5 + MHRA cites; "architectural properties, not yet measured outcomes" |
| Related work | Alsaif 2024 (Electronics 13(24):4912), Merkelbach & Hasenauer 2024 (OASIcs DX), Lewis 2020 RAG at first use, AgentRCA positioning row, microservice-RCA scoping, Venkatasubramanian Parts I–III with correct labels, Lyman & Georgakis 1995, "deep anomaly detectors", "commonly regarded" IDV3, FE antecedent fixed |
| Bibliography | 54 entries; all 8 additions existence-verified before inclusion; rieth url duplicate removed; khan arXiv note removed |
| Data availability | Review-time repository URL present |
| Figures | All 10 regenerated: true textwidth basis (345 pt = 4.77 in), minimum in-figure text ≥6 pt effective (0.229 pt per css px at 1500-px canvas ⇒ ≥29 px fonts); fig_trace canvas widened 1050→1500 px (4500×4980, aspect fits); fig_architecture/fig_pipeline height-capped in LaTeX (`height=0.7–0.8\textheight,keepaspectratio`); fig_tep_perfault in-figure author–year citation removed; serpentine flow noted in Fig. 2 caption; run id in Fig. 3 confirmed correct (202609171639066) — R3-Major-2 was a rendering-resolution misread, evidence archived |
| Integrity invariants | Headline numbers unchanged from the audited corpus (Top-1 4/9 [18.9, 73.3]; top-k 9/9; controls 3/3; rubric 94.6; judge 94.7; seed 1003818694; 45/45; 153/153) — no evidence atom was altered by the revision |

## Verdict

**ACCEPT — publishable after this revision.** All three major clusters are
resolved: (i) the identifier-recall channel is fully disclosed with a stated
joint worst case, a visible recall-possible tier on every affected claim, and a
costed execution contract; (ii) the grading instrument's provenance is
concretely disclosed with a reproducible leave-one-token-out sensitivity and an
instrument-readings block in the headline table; (iii) the identity-strict lens
is now applied symmetrically, and the cap-policy cost is quantified by the
released-gradings counterfactual. The two remaining execution demands
(neutralised-identifier re-run; k ≥ 3 repeats) are converted into pre-registered,
costed contracts with their dependent claims demoted in place — no headline
number depends on an unexecuted control. Presentation findings are resolved
(all figures ≥6 pt at true textwidth; the one disputed finding is evidenced as
a misread). Citation integrity: 54/54 references real, zero fabrication.

Residual items (documented, non-blocking): neutralised-identifier re-run and
k ≥ 3 repeats (pre-registered contracts, §9); Granger/TE arm and bare-arm TEP
control coverage (pre-registered); full vector figure export and byline split
(production stage).
