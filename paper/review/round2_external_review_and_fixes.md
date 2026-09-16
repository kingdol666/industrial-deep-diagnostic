# Round 2 — Independent External Review (3 reviewers) and Itemised Fixes

> 2026-09-16. After the round-1 in-house panel and the 2026-09-15/16 reproducibility
> work (released `baseline_pca.mjs` / `baseline_llm.mjs` / stability stage / Nuxt
> baseline-suite), a fresh three-reviewer panel reviewed the current manuscript
> (55 pp) independently, with repository artifact access and live literature
> verification. Verdicts: **R1 (methods) Minor Revision · R2 (literature) Major
> Revision · R3 (presentation) Minor Revision.** All findings and their dispositions:

## R1 — Methods / evaluation rigor

| # | Finding | Disposition |
|---|---|---|
| M-1 (Critical) | `metrics.json` `execution_integrity` asserted tep_d01/tep_d00 were "stats-package failed, anti-spurious not executed" while gradings and run artifacts show the stats layer executed (306 pairs, Simpson-safe 306, LOO 222 on d01) | **FIXED (deterministic)**: root cause = `aggregate.mjs` engine detection assumed the v1 validate_report schema (top-level `correlation`); v2 runs use `{validations, summary, metadata}`. Detection unified to accept both schemas; the false hardcoded degradation note replaced by an evidence-gated note; metrics regenerated → `stats-package ×12, degraded_cases []`; `verify-repro` still REPRODUCIBLE. `detrended_robust_pairs` semantics documented in the schema (pairs flagged trend-confounded at >40% detrend attenuation; 0 = none). |
| M-2 | Table 4 valve1 "decisive signature" (V·I −4.1%/−8.4%, flow 32→31/30) came from the 09-14 stability run, not the graded 09-15 run | **FIXED**: Table 4 and §7.3 now quote the graded run's own chain (window mean 30.62 vs 31.73 L/min, −3.5%; 39.4% floor-bin dwell; pump load 0.990→0.947 A, −4.3%). |
| M-3 | Rubric cited as headline; near-structural ceiling | **FIXED**: removed from abstract; §5.2 adds the discriminative-power statement (10/12 at ceiling; correctness rests on the truth comparison); abstract rubric mention dropped. |
| m1 | "53 run directories" vs 40 on disk | **FIXED** → 40 (§8.4); stability report refreshed (coverage 40, 15/15 unchanged). |
| m2 | repair counts "in grading records" | **FIXED** → "released event logs" (§6.4 config disclosure). |
| m3 | bare-LLM controls 2/3 ambiguity | **FIXED** → §8.1 states "the two controls it was run on (the TEP fault-free control was not run bare)". |
| m4 | "strict keyword ≠ mechanism equivalence" | **FIXED** → §5.2 scope statement incl. the IndPenSim generic-token disclosure. |
| m5 | baseline arms are also n=1 | **FIXED** → §8.4 sentence added. |
| m6 | DETERMINED ≤0.90 cap absent from §4 | **FIXED** → added to the three-state definition. |
| m7 | abstract length | **FIXED** → see R3 M1. |
| m8 | ceiling-compliance circularity in Table 2 | **FIXED** → row annotated "(gate-enforced by construction)". |
| 9(i) | C1 keyword-commit timing | **VERIFIED**: keyword commit 2026-09-14 00:22 precedes all final executions (09-14 18:4x, 09-15 04:5x); claim stands. |

## R2 — Literature / novelty

| # | Finding | Disposition |
|---|---|---|
| M1 | refs.bib corruption (6 author lists, wrong volumes/pages, russell2000 DOI invalid, katal2024 unverifiable) | **FIXED**: all entries corrected against Crossref records fetched 2026-09-16 (pozdnjakov→Vitaliy/Aleksandr/Kirill…; vieira→João Paulo/Victor Afonso/Rodrigo Kobashikawa/Danilo; iliopoulos→Anastasios + BigDataService "Computing Service and Applications", 1–8; liu2025spatial→Yan Liu et al., vol 68; liu2024label→Zhenyu Liu et al.; yue2023root→Weichao Yue et al. (+Gui); reinartz→Christopher, vol 149; khan→CCE 199:109152 + DOI). `russell2000delay` converted to the Springer monograph (10.1007/978-1-4471-0409-4). `katal2024causal` (unverifiable) removed; the sentence now cites the in-bib verified causal-RCA literature (yuan2014root, bauer2007finding). |
| M2 | "12.6 percentage points" (Vieira) not in source | **FIXED** → "by up to 15.3 percentage points of Macro-AUROC under segmentation-level leakage" (arXiv:2509.22267 verifiable figure). |
| M3 | Missing related work: 4 AEI papers + AgentRCA; novelty claim too strong | **FIXED**: added CausalKGPT (AEI 59:102333), FD-LLM (AEI 65:103208), Wen et al. (AEI 65:103235), Xu et al. (AEI 69:103997), AgentRCA (arXiv:2607.22385, TEP 40.0/61.5, verified from full text); §2.2 novelty claim restated ("among published and contemporaneous systems none combines (i)–(iv); (iii)/(iv) absent from every cited system, AgentRCA naming uncertainty communication as future work"). |
| M4 | "matches" understates 9/9 vs 6/9 | **FIXED** in abstract, §7.4, §8.1, §8.4 caption, conclusion: "resolves 9/9 faults—more than the pipeline". The TEP shared-subject 4/4=4/4 "matching o1-preview" wording retained (it is a genuine match on that subset). |
| M5 | "Trustworthy" title / generalisation bounds | **FIXED** → conclusion adds explicit scope sentence (one model family, one deployment, twelve scenarios; cross-model/cross-plant generalisation of the process guarantees open). |
| m2 | khan2024faultexplainer published version | **FIXED** (CCE 199:109152 + DOI, arXiv kept as note). |
| m3 | FE alias class {IDV1,IDV2,IDV8} | **FIXED** in §2.2 and supplementary (with note that IDV2 is outside the paper's TEP subset). |
| m4 | FE internal 8/11 arithmetic | **FIXED** → transcribing note added in §2.2. |
| m5 | IDV4 weak detection → T²-specific | **FIXED** in §1 and §2.1. |
| m6 | Pozdnyakov 28-class scope | **FIXED** in Register B (§8.2). |
| m9 | katal replacement | Covered by M1 disposition. |

## R3 — Presentation / AEI format

| # | Finding | Disposition |
|---|---|---|
| M1 | Abstract ~350 words (AEI limit 250) | **FIXED** → ~250 words, restructured. |
| M2 | Missing Conflict of interest + Funding | **FIXED** → standard Elsevier declarations added; a generative-AI-in-writing declaration added per Elsevier policy (distinguishing writing tools from the evaluated system). |
| M3 | Highlights >85 chars (3/5) | **FIXED** → all five ≤85 chars. |
| M4 | Tables 4/6 \resizebox → ~5 pt | **FIXED** → resizebox removed; Table 4 signature column p{7.0cm}, Table 6 reflowed with p-columns; float overflow warning cleared. Figure figsize noted: matplotlib exports already render legibly at \textwidth (verified in 220 dpi crops); matrix-cell labels checked. |
| M5 | British/American mixing | **FIXED** → "artifact" retained as the released-system term (majority usage); the 3 remaining "artefact" and both "formalized" converted; em-dash spacing unified (no-space style). |
| m1 | Tables 5/7 unreferenced; Fig 6 caption "table" | **FIXED** → both tables referenced in text; caption reworded. |
| m4 | "verifies the evaluation internally consistent" | **FIXED** → "verifies that the evaluation is internally consistent". |
| m5 | corresponding-author marker | **FIXED** marker deferred to submission metadata (single-author paper; email already in frontmatter). |
| m6 | Fig 2 serpentine row | **FIXED** → caption notes the right-to-left bottom row; deliverables row raised to \scriptsize. |
| m7 | Table 2 slash-cite | **FIXED** → \cite{downs1993plant,chiang2001fault}. |
| m8 | Table 3 non-numeric row | **FIXED** → "verified". |
| m2 (fig/table redundancy), m9 (length) | Fig 5 vs Table 5 kept deliberately (figure for trend, table for record; AEI permits); 55 pp preprint ≈ 22–25 pp two-column, acceptable. | NOT CHANGED (justified). |

## Post-fix state

- Full recompile (pdflatex ×2 + bibtex inside paper/): **55 pages, 0 errors, 0 undefined references**; all released artifacts regenerated and gates green (metrics/rubric/stability/verify-repro REPRODUCIBLE).
- Review artifacts: this file is the audit trail; reviewer reports preserved verbatim in the session log.

## Round-2 verifier findings (independent re-check) and dispositions

A fresh verification reviewer re-checked all ten items against the recompiled PDF and
artifacts: items 1, 2, 5, 6, 7, 8, 9, 10 **PASS** (abstract 244 words with the honest
9/9-vs-6/9 statement; 97.9/93.1/deduction structure verified against rubric.json;
valve1 Table 4 signature verified word-for-word against the graded run's
diagnosis.json; 40 run directories; katal/12.6/artefact/formalized zero hits;
10+ spot-checked numbers all match). Two findings:

| # | Finding | Disposition |
|---|---|---|
| N1 (must fix) | Removing \resizebox without narrowing columns left Tables 4/6 overfull by 149.2/129.4 pt — right-edge clipping worse than the small-font state; the earlier note "float overflow warning cleared" was misleading (it referred to a different warning) | **FIXED**: Tables 4/6 re-set in \scriptsize with p-columns and \tabcolsep 4 pt; verdict column abbreviated (\textsc{det}/\textsc{cs}, legend in caption); scenario names shortened. Final compile: **both tables Overfull-free** (the tab:ablation 2.09 pt residual was eliminated by narrowing the Result column to 3.05 cm). Remaining Overfull boxes document: 3.81 pt at the tab:related \resizebox closing line (L107, pre-existing), and 0.79/3.50 pt in a §3.3 paragraph (L197–198, pre-existing) — all paragraph-level, sub-mm, invisible. The misleading sentence above is hereby corrected. |
| N2/N3 (cosmetic) | highlights.md is a separate file (not in main.tex); one decorative em-dash inside Fig 1 TikZ | Highlights verified present with all five bullets ≤85 chars; Fig 1 separator converted to "·". |

Reviewer's round-2 closing note: "不建议再送外审：请作者收窄两表列宽并消除 Overfull
警告、更正修复记录表述后，编辑可直接验收" — all requested actions are complete,
including the optional elimination of the 2.09 pt residual (Table 6 Result column
narrowed to 3.05 cm; verified: tab:mech and tab:ablation now compile Overfull-free).
The verifier's acceptance pass returned **Publishable as-is**.
