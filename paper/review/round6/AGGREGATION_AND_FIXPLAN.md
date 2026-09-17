# Round 6 — Aggregated Verdicts & Verified Fix Plan

## Verdicts
| ID | Taste | Verdict | Must-fix |
|---|---|---|---|
| R1 | methodology skeptic | MAJOR | 8 (2 rejected after verification) |
| R2 | systems architect | MINOR | 3 |
| R3 | figures & visual communication | MINOR | 3 |
| R4 | reproducibility & integrity | MINOR | 3 |

## Adjudication (lead verified every must-fix against the repository)
**CONFIRMED (fix):**
1. **Five-factor weights = 25/25/20/20/10** (statistical 25, physical 25, temporal 20, confounds 20, symptom 10; sums 100). Evidence: `diagnostic-quality-check.mjs:151`, `confidence-completeness-check.mjs:55-61`, released `confidence.json` H1 maxes. Paper's 25/20/20/20/10 (sums 95) is WRONG (main.tex:284). (R1#1, R2#1; R4's contradicting spot-check overruled.)
2. **DETERMINED 0.90 cap does not exist in the protocol.** Skill documents only {65 INDIST, 70 CS, 50 anti-osc} (`industrial-diagnostician/SKILL.md:106`). Canonical IDV4 confidence.json carries a reason-coded DIRECT_MEASUREMENT ceiling binding 0.75. Fix Eq(1) (main.tex:272), L305, L487. (R1#4.)
3. **Elimination rule**: skill = "≥2 eliminations, exclusion_confidence ≥ 90, cite contradicting evidence, record revival conditions" (SKILL.md:73,95). Paper's lone |X_i|>|E_i| (main.tex:275) omits the binding contract. (R1#5.)
4. **C1 keyword timing claim FALSE**: canonical runs 09-15 04:53 → keyword-calibration commit 221d061 09-15 19:20 → gradings 09-16 17:43 hit added tokens (tep_d04 kw_hits ["反应器冷却","冷却水"]). The commit note itself says "修订先于 v2 最终聚合一次性uniform应用" (before final AGGREGATION, not before execution). Rewrite main.tex:326 with precise honest timing. (R1#2.)
5. **C4 14-artifact gate list**: verified `zcode_direct_pipeline.mjs:288-303` — includes diagnostic-report.html (+<5120B re-check), NOT optimizer.md. Paper Table 4 enumeration must match exactly. (R2#3.)
6. **Table A2 `00_input/brief.json` row dead**: no run dir contains brief.json; briefs live at `results/benchmark/briefs/<case_id>.brief.json`. (R2#2, R4#3.)
7. **Universal RAG-failure claim FALSE**: canonical skab_valve1_1 rag_deep_understanding.json = successful retrieval (engine reached, chunks_retrieved 21), no degradation event. Fix main.tex:132 and :611; "no L6 in any verdict" part verified TRUE (zero web citations in released 04_diagnostics/*) and stays. (R4#1.)
8. **Blind-set residual identifier channel**: brief case_id `skab_cavitation_13` embeds the English fault word; sentinel scans description/keys/glossary but not case_id. Disclose in main.tex:611. (R4#2.)
9. **Fig 7/forest caption colour error**: controls row drawn GREEN (`fig_forest` rows: GREEN constant), caption says "Blue: … and the three controls". Fix caption. (R3#1.)
10. **Amber semantics clash across Figs 3(a)/4/6/8**: standardise on Fig 8's convention — sky = capped CS with true mechanism ranked; amber = capped CS without it (IDV3). Recolour fig_benchmark(a) + fig_calibration; fig_tep & fig_suite_matrix already conform. (R3#2.)
11. **Fig 5 annotation collision/overflow** (make_figures.py:407-410 region): shorten/reposition inside axes. (R3#3, R1#7.)
12. **Stability provenance clarifier**: 15/15 = 12 pre-discipline-era pairs over provenance-verified recorded run directories of the earlier pipeline version + 3 current-era; the archived note-era contributes no pairs. Add one clarifying sentence at main.tex:601-605. (R1#3, partially confirmed — paper already splits 12/12+3/3; add provenance clause.)

**REJECTED (no change, rationale recorded):**
- R1#8 "Wilson 3/3 lower bound should be 43.8": exact value 43.8502% → 43.9 is correct rounding.
- R1#3's stronger form ("12 pairs are disowned note-era runs"): rejected — the v1 stability pairs come from real recorded pipeline run directories (stability_report.json `n_runs_proven`), not the archived legacy_note_era gradings; the clarifier above suffices.

## Should-fix accepted (cheap, honesty/consistency value)
- Retest-draw history: 4 recorded rounds, 3 selecting TEP IDV11; disclose beside the round-4 citation (R1).
- Tightening disclosure: brief rewrites after internal leakage audit + judge replacement (R1) — one sentence at the "documented tightening" passage.
- Verdict-type typing is one-directional (8/9 allowed sets admit both states) — state beside the compliance-miss caveat (R1).
- Abstract: scope per-fault literature baselines to the TEP subset (main.tex:52) (R1).
- C2: print "153 fingerprints re-verified, sentinel PASS" (verify numbers in released repro report first) (R4).
- Table 8 caption: state LLM arms are recorded replays; Table 6 caption: judge mean denominator n=12; A1/A2 "L1–L7 ranks" → numeric ranks wording (R4).
- Algorithm-1 "14-artifact inventory" → grader's completeness set (finalize runs ≈45 core checks); "nine skill packages" skills-vs-agents wording; "only parallel step" → "only mandatory parallel step"; §6.4 ZCode CLI-driver clarification (R2).
- Figure print-size: include result figures at \textwidth (0.88–0.98 currently shrink 7.2pt → ≈6.4pt); Fig 8 last-cell text overflow; Fig 2 caption cycle wording; Fig 1 \tiny line; appendix table float placement (R3).

## Declined (recorded, with reason)
- Full keyword-sensitivity re-scoring under pre-revision sets: the revision's deletions are over-generic single-character tokens (only removable inflation sources) and additions are mechanism synonyms already subsumed (e.g. 冷却 ⊂ 冷却水); precise timing disclosure + released pre-revision sets address the concern; re-scoring post-hoc would fork the frozen corpus. Pre-registered as a released-history sensitivity note instead.
- Zenodo DOI minting: external action, tracked in data-availability statement.
- Fig 1/2 float-placement drift (2–3 pages): copy-edit stage; layout churn risk outweighs gain.

## Execution
- Fixer-Tex: main.tex only (items 1-9 text, caption fixes, should-fix text) via Edit tool.
- Fixer-Fig: paper/figures/make_figures.py only (items 10-11 + overflow/legibility), re-render via venv python, confirm all 6 PDFs regenerate.
- Lead: recompile, re-render pages, verify must-fixes, then Round 7 fresh blind review.
