# Editor-in-Chief Review — Journal-Fit Seat (Round 18)

**Manuscript:** *Trustworthy agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines* (single author; `main.tex`, elsarticle `preprint,review,12pt`)
**Target journal:** Advanced Engineering Informatics (Elsevier, Q1)
**Review basis:** compiled 78-page review preprint; rendered pages read in full: pp. 1–20, 31, 38–58, 66–78 (mandated) plus 21–30, 32–37, 59–65 for storyline continuity — i.e., the entire build.
**My lane:** journal fit, originality, significance, reader comprehension, storyline completeness, length, title/abstract/keywords, figure–table programme. Methodology detail is Reviewer 1's lane and is not duplicated here.

---

## 1. Fit to Advanced Engineering Informatics

The fit is strong, and the manuscript actively cultivates it. The cited AEI cluster (CausalKGPT [24], FD-LLM [25], Wen et al. [26], Xu et al. [27], Liu et al. [20], plus causal-RCA papers [21–23]) is real and recent, and §2.2 explicitly reads the gap against "activity in this journal." The subject matter — an informatics pipeline that turns plant time series + documents into audited, human-signable engineering decisions — is squarely AEI's territory, closer to this journal than to Computers & Chemical Engineering or Control Engineering Practice. The deployment-prospects subsection (§9.1: historian/LIMS ingestion, data-sovereign engine substitution, GxP/ALCOA+ traceability) speaks the AEI reader's language. No fit concern.

## 2. Originality and significance

- **Originality.** §2.4 is admirably explicit that the intellectual ancestry (Heuer's competing hypotheses, Hill's criteria, Chow's reject option, Parasuraman/Lee & See trust calibration, OntoCAPE) is inherited and IDD is a "domain-specific, machine-checked instantiation." What is genuinely new, and verifiable from the manuscript: (i) the three-state calibrated verdict with hard, auditable confidence ceilings; (ii) the machine-checked evaluation contract (truth isolation + leakage sentinel, data fingerprinting, stage-authored provenance-labelled artifacts, execution proofs, artifact-consistency gate); (iii) the per-fault literature register against FaultExplainer; and (iv) the pre-registered, seeded random-draw re-execution. Table 1 positions this correctly, and the contemporaneous AgentRCA [28] is acknowledged and differentiated (ranked list without calibrated confidence). Against the closest published system (FaultExplainer) the delta is real and not manufactured.
- **Significance.** Moderate, honestly bounded. Twelve scenarios, single recorded execution per scenario, one model family at one deployment, keywords and rubric authored by the system's own author. The paper says all of this — repeatedly. What saves significance from being "a 12-case demo" is that the most transferable finding is the *evaluation contract plus the negative result*: a bare same-model call scores 9/9 where the pipeline resolves 4/9. Published honestly, that is a result the community can use. But note the asymmetry: the auditability claim (the paper's entire value proposition) is *asserted by construction*; no human-expert comparison, no measured incident in which the audit trail changed an outcome (the anonymised film-line NEEDS_DATA anecdote, §9.1, is the only deployment evidence). For AEI — a journal that prizes demonstrated engineering value — this is the significance bottleneck. It is acceptable for a first submission, but the discussion must make the argument for why audit artifacts are the deliverable (regulated operations) more concretely, ideally with one measured deployment data point or a worked regulated-scenario walkthrough, or the reader leaves unconvinced that the 2.0 h/scenario cost buys anything a screenshot of an LLM chat does not.

## 3. Can an AEI reader follow the story? (comprehension findings)

The macro-arc is complete and correctly ordered: obstacles (§1) → gap (§2) → architecture (§3) → methodology (§4) → evaluation contract (§5) → benchmark setup (§6) → results (§7) → comparison/ablation/stability/case (§8) → discussion/deployment (§9) → conclusion. Cross-referencing is dense and, in my reading, accurate; the negative result is stated in the abstract, contributions, §8.3, §9 and §10 consistently, with no contradiction anywhere in 78 pages. That is unusual discipline. The problems are at the level of reading *load*, not structure:

- **E1 — Label-system overload (the single biggest comprehension tax).** The reader must simultaneously track: pipeline Steps 0–9 (with 0/1, 3.5, 5a/5b, 8.5), agent Phases 0–7, reasoning segments R1–R8, method stages 1–6, checkpoints CP-1…CP-9, contracts C1–C5, rubric checks R1–R7, evidence levels L1–L7, registers A/B, verdict states DET/CS/ND, and at least four confidence caps (0.50, 0.65, 0.70, 0.90). p.14 even pauses the narrative to warn that "the paper's four numbering schemes … are independent." Worse, there is a direct **collision: R1–R8 (reasoning chain) vs R1–R7 (rubric checks)** — "R4" means different things in §4.1 (p.20) and §6.2 (p.32), and a first-time reader will misread it. Rename one family (e.g., rubric checks RU1–RU7 or G1–G7) and add a half-page "notation and label systems" table early in §3; paradoxically this lets you cut far more defensive prose later.
- **E2 — "Nine-stage" arithmetic does not close.** The pipeline is called nine-stage, but the figures and Table 2 label 13+ steps (0/1, 2, 3, 3.5, 4, 5a‖5b, 6, 7, 8, 8.5, 9) and the text on p.10 says the benchmarked diagnostic path "dispatches eight specialist sub-agents" of 18 packages run by 14 agents on 14 engines. None of this is wrong — Fig. 2 rescues it — but the counting friction is real. Either define "nine stages" once with an explicit mapping sentence (Step groups → nine stages) or drop the "nine-stage" branding.
- **E3 — Release-note prose in §3.** §3.1–§3.4 read in places like a repository changelog: the 18/14/8 bookkeeping, the "3+3.3" dispatch-table label, six-of-eighteen checklist accounting (p.10–11), `ontology_store.mjs` fast-reuse mechanics (p.12), port numbers 3210/5180, SQLite WAL mode, HTTP codes 400/409 stated *twice* (pp.12 and 15), and a 14-item engine name list. None of this is needed to follow the story; all of it is in the released repository. This is the most compressible section of the paper (see §5 below).
- **E4 — Opaque proper nouns.** §6.4 ("Benchmark configuration disclosure") names the "ZCode agent CLI" and the "GLM model family … under the provider's coding-plan configuration" with no citation, footnote, or one-line gloss. Disclosure is admirable; opacity is not. Add a footnote describing what these are, or the sentence reads as an in-joke.
- **E5 — Rubric definition arrives late and is over-weighted.** R4 is invoked in §4.1 (p.20) before the rubric exists (defined §6.2, pp.32–33); then §7.1 spends ~15 lines on rubric point deductions (−15/−15/−35/−20) that duplicate Table 6's caption, and Fig. 3's KPI tiles repeat the same numbers a third time. By the paper's own admission the rubric "is a conformance instrument with limited discriminative power: nine of the twelve scenarios score at ceiling" (p.33). Give it one sentence in §6.2 and move the R1–R7 spec to the appendix.
- **E6 — Duplicated evidence representations.** The TEP per-fault comparison appears three times: Fig. 6 (an HTML table rendered as an image, p.48, inner text below print legibility), Table A1 (appendix transcription, p.75), and prose bullets (pp.46–47). Fig. 8 (p.53) overlaps Table 7 + Table 8. Fig. 1 and Fig. 2 both depict the staged pipeline with gates. Choose one canonical representation per claim.
- **E7 — Half-empty and stranded pages.** p.17 ends half-way; Table 2 and Table 3 strand on float pages 18–19; Algorithm 1 occupies a nearly empty page 22; p.25 ends half-way; p.57 is ~40% full; appendix intro (p.74) half page. This is the `placeins`/float discipline interacting with the double-spaced review build, and it inflates the page count by ~4 pages of pure whitespace.
- **E8 — The deliverable is never shown.** For an *informatics* journal, the paper's product — the audited HTML diagnostic report / evidence chain UI — is described but never pictured. Fig. 5's evidence-chain strip is the closest thing. One small figure of an actual `diagnostic-report.html` (even abbreviated) would do more for deployment credibility than a page of §9.1 prose.

## 4. Is the contribution clearly framed against the negative result?

Mostly yes, and this is the manuscript's best feature. The chain — abstract's final sentence ("margins … are auditability, calibrated uncertainty, and gated process, not accuracy"), §8.3's "the gap between 9/9 and 4/9 is the paper's central cost statement," §9's "What the five capped verdicts mean," and §10's "accuracy is not the contribution" — is consistent, prominent, and falsifiable. Two weaknesses remain:

1. **The value claim is asserted, not evidenced.** The audit trail's worth is currently an argument from design (§4, §5) plus one anecdote (§9.1). Given the cost (≈2 h/scenario vs minutes for FE-style prompting, stated p.47 and §9), an AEI reader will ask for at least one measured deployment outcome or a quantified regulated-documentation scenario. I do not require a new study for this revision, but the discussion must stop generalising from n=1 anecdote and explicitly scope what is demonstrated vs projected (§9.1 does start this — "demonstrate from project" — keep and sharpen it).
2. **The attribution gap is under-dramatised.** If a bare call on the same blind digest resolves 9/9, the reader wants to know what the ontology/statistics/audit stages each buy. The paper concedes the filter-disabled and engine-substitution arms "remain future work" (pp.35, 52, 62). That is honest, but it means the central architectural claim is partially unvalidated; say so in one blunt sentence in §8.3 and once in the Conclusion, rather than distributing the concession across five locations, where it reads as hedging.

## 5. Length programme: from 78 to under 50 pages (specific cuts)

Current build: body ends p.67; references pp.67–74; appendix pp.74–76; back matter pp.77–78. Required reduction ≈ 28 pages. My accounting, per section, assuming the same review build (do **not** count on format tricks; the float/whitespace savings alone are worth ~4 pages and are pure win):

| Section (pages) | Action | Est. saving |
|---|---|---|
| Front matter (1–2) | Trim abstract to ≤200 words (see §6). | 0.3 pp |
| §1 Introduction (2–5) | Keep. Contribution 4's parenthetical cascade "(Section 5) (Sections 7–8)" is a typo-adjacent artifact — fix. | 0 |
| §2 Related Work (5–9) | Keep; it is the AEI positioning. Compress §2.2's FE-regime detail by ~1/3 (the alias-class enumeration reappears in §6.3, §8.1, Table A1 — state once). | 0.7 pp |
| §3 Architecture (10–17, floats 18–19) | Largest cut. Move the 18/14/8 qualification paragraph (pp.10–11), the ontology-store fast-reuse mechanics and integration-surface paragraph (p.12), and §3.4's engine roster + error codes (p.15) to a released technical note / appendix; compress §3.5's 8-of-13 rejection litany (p.17) to two sentences. Merge Table 3 (checkpoint predicates) into Table 2 or appendix. Demote Fig. 1 to appendix (Fig. 2 carries the same story). §3 from ~9.5 pp to ~5 pp. | 4.5 pp |
| §4 Methodology (20–25) | Tighten §4.1: the cap-set exposition (0.70/0.65/0.50/0.90 + reason codes, pp.20–21) duplicates §7.3 and Fig. 4's caption; keep one statement. Set Algorithm 1 inline `[h]` (kills the stranded p.22). | 1.5 pp |
| §5 Evaluation framework (26–29) | Keep C1–C5 (this is the contribution). Move Table 4 (14-artifact set) to appendix; state the C4 fabrication history once (it repeats in §9). | 1 pp |
| §6 Setup (30–35) | Move the R1–R7 rubric spec (pp.32–33) to appendix (one-sentence summary stays). Compress §6.4 by a third (see E3/E4). | 1.5 pp |
| §7 Results (35–44) | Simplify Fig. 3 to panel (b) + one compact bar panel; delete the five KPI tiles and in-figure notes (they duplicate Table 6). Cut the rubric-deduction accounting in §7.1 (dup of Table 6 caption). Table 7 is the best table in the paper — keep untouched. | 1.5 pp |
| §8 Comparison (45–58) | Merge §8.1's three outcome bullets (pp.46–47) into one paragraph pointing at Table 7 (they re-tell §7.2). **Drop Fig. 6** (illegible HTML-table-as-image) and keep Table A1 + Fig. 7; or keep a re-typeset Fig. 6 and drop Table A1 — one representation only. Keep Fig. 8 (the single best cross-arm visual) and drop Fig. 7 (five numbers with huge CIs already in the text) — or the reverse; do not keep both. Retypeset **Table 9 as a real LaTeX table** (currently one microscopic row, p.55 — illegible; a copy-editor would flag it). Trim §8.5 by 1/3. | 4.5 pp |
| §9 Discussion (59–65) | Compress "Statistical power" (third repetition of the CI caveat), "Cost" (drop second paragraph), and the "Documentation"/"Governance" paragraphs by ~40% combined. Keep the deployment subsection, sharpened per §4 above. | 2 pp |
| §10 Conclusion (65–67) | Keep; it is appropriately self-critical. | 0 |
| References (67–74) | 41 refs is fine; no action beyond final re-flow. | — |
| Appendix A (74–76) | Table A1 kept (per Fig. 6 decision) or dropped; Table A2 to supplementary material only, with a pointer. | 1.5 pp |
| Whitespace / floats (throughout) | Relax `placeins` [section] flush for the big floats (allow [tbp] drift within section), fix stranded pages 17/22/25/57. | 3.5 pp |
| Structural option (recommended) | Fold §4 into §3 (Algorithm 1 and the CP gates are architecture anyway) and fold §5's contracts into §6 as "Benchmark protocol." Fewer headers, tighter arc, ~1 pp of transition prose gone. | 1 pp |

Total realistic saving: ≈ 23–24 pp from the table above plus ~3 pp from the consequential re-flow (shorter §3 removes its stranded pages; fewer floats removes float pages) ≈ **26–27 pp → lands at 51–52**. The remaining 2–3 pages come from the abstract/highlights trim and the single-representation rule applied ruthlessly. This is achievable **without losing the storyline**; what leaves the paper is engineering bookkeeping and duplicated evidence, not argument. If the author prefers, the alternative is a genuine supplementary file (rubric, artifact tables, engine roster, Table A2) — I would endorse that over in-paper appendices for everything except Table A1.

## 6. Title, abstract, keywords, highlights

- **Title.** Informative but frontend-heavy; it promises a positive result ("Trustworthy … evaluated against per-fault literature baselines") and hides both the system name and the honest cost statement. Suggest either shortening ("Evidence-graded agentic root-cause analysis for industrial processes: an auditable pipeline and an honest benchmark") or making the trade-off explicit ("… auditability over accuracy"). Current title is acceptable; not a blocker.
- **Abstract.** ~300 words, single block, and the 4/9-vs-9/9 cost statement — the paper's defining move — is the *last* sentence. Cut to ≤200 words and move the negative result to the results paragraph's first position. Also "nine-stage agentic orchestration" collides with E2.
- **Keywords.** Six, appropriate. Consider adding "process monitoring" or "Industry 4.0" for discoverability; drop one of the two reasoning-related tags if a limit binds.
- **Highlights.** Elsevier caps highlights at 85 characters including spaces. Bullets 3 (~93) and 6 (~88) exceed it; bullet 1 is borderline. Rewrite to fit before submission — this is a desk-check item.

## 7. Figure/table programme as the reader experiences it

- 9 figures, 11 tables, 1 algorithm for a 12-scenario study: too many. Post-cut target: 6–7 figures, 6–7 tables in the main text.
- **Legibility defects (must fix regardless of length):** Table 9 (p.55) body text is unreadable (~4 pt effective); Fig. 6's inner cells and its 5-line grey "Reading:" block are below print size; Fig. 1's smaller boxes, Fig. 3's KPI tiles, and Fig. 8's footnote lines are marginal. All HTML-rendered figures must be re-exported (vector or ≥300 dpi at final size) with minimum ~7 pt effective text. In-figure narrative blocks ("Reading: …") duplicate captions and should be deleted.
- Colour usage is consistent (Okabe–Ito palette declared in the preamble) and the palette is colour-blind safe — good. Captions are self-contained, often to a fault (Table 6's caption is 20 lines; much of it belongs in §6.2/§7.1 text).
- The `figures$1.png` stray file in the submission directory is unreferenced but should be cleaned up before submission; Elsevier's build system chokes on `$` in filenames.

## 8. Smaller items

- Contribution 4 contains "(Section 5) (Sections 7–8)" — doubled section pointer, p.5.
- p.20: "the paper's four numbering schemes … are independent" — after E1's fixes this parenthetical can go.
- The AI-use declaration (p.78) is transparent and properly separates the writing tools from the IDD system under study — commendable and, given the subject matter, essential; keep it.
- Data availability statement is strong (released repository now, Zenodo DOI on acceptance). Good.
- CRediT, competing interests, funding: present and in order.

---

## Recommendation: **Major Revision**

**Justification (5 lines):**
1. Fit and originality are not in doubt: the AEI positioning is explicit and current, and the machine-checked evaluation contract plus the honest 9/9-vs-4/9 ablation constitute a genuinely novel, publishable systems+benchmark contribution.
2. The storyline is complete and internally consistent across 78 pages — no dangling claims were found — but the reading load is excessive: ~12 coexisting label systems (with an R1–R8/R1–R7 collision), release-note prose in §3, and duplicated evidence representations (Fig. 6/Table A1; Fig. 1/Fig. 2; Fig. 3/Table 6) block a first-read understanding.
3. The manuscript is 78 pages against the instructed <50; the cut list in §5 above reaches the target by removing bookkeeping and duplication, not argument, but it is a structural revision, not a copy-edit.
4. Hard presentation defects (illegible Table 9 and Fig. 6, over-long abstract burying the negative result, highlights exceeding Elsevier's 85-character cap, stranded float pages) are individually trivial but collectively disqualify the current build.
5. The value proposition (auditability) remains asserted rather than evidenced; the revision must scope demonstrated-vs-projected claims sharply and show the deliverable, or the paper's central claim stays rhetorical.

**Chapter-level actions for the revision (numbered):**
1. **Front matter:** abstract ≤200 words with the 4/9-vs-9/9 cost statement moved to the first results sentence; rewrite highlights to ≤85 chars each; optionally retitle to signal the auditability-over-accuracy trade-off.
2. **Global notation:** add a "label systems" table early in §3; rename the rubric checks (kill the R1–R8/R1–R7 collision); delete the "four numbering schemes" apology; fix the "(Section 5) (Sections 7–8)" doubled pointer in contribution 4.
3. **§3 Architecture:** cut to ~5 pp — move 18/14/8 accounting, ontology-store mechanics, integration surface (ports/WAL), engine roster and error codes to a technical appendix/supplement; merge Table 3 into Table 2 or move it out; demote Fig. 1; compress §3.5's rejection litany to two sentences.
4. **§4–§5:** inline Algorithm 1; de-duplicate the cap-set exposition (state the 0.90 machine gate once); keep C1–C5 as the section's spine; move Table 4 to the appendix; state the fabrication-history once (merge the §5 and §9 accounts).
5. **§6:** one-sentence rubric summary in §6.2, full R1–R7 spec to appendix; footnote-gloss "ZCode agent CLI" and "GLM … coding-plan configuration"; compress §6.4.
6. **§7:** simplify Fig. 3 (drop KPI tiles and in-figure notes); cut the §7.1 deduction accounting; keep Table 7 verbatim.
7. **§8:** merge the §8.1 bullets into one paragraph referencing Table 7; keep exactly one of {Fig. 6, Table A1} and at most one of {Fig. 7, Fig. 8}; retypeset Table 9 as a legible LaTeX table; trim §8.5 by a third; add one blunt sentence in §8.3 stating that stage-attribution (filter/ontology/audit) is not yet validated.
8. **§9:** compress the Statistical-power, Cost, Documentation and Governance paragraphs by ~40%; scope demonstrated-vs-projected explicitly; keep and sharpen the deployment subsection; ideally add one figure of an actual HTML diagnostic report (or move Fig. 5's evidence-chain strip there and label it as the deliverable).
9. **Back matter:** Table A2 (artifact index) to supplementary material only; clean the stray `figures$1.png`; re-export all HTML-rendered figures at legible effective sizes.
10. **Recompile and verify** the review build lands under 50 pages with no stranded float pages (pp.17/22/25/57 in the current build) before resubmission.

*Recommendation to the handling editor: the science merits publication at AEI after this revision; do not desk-reject. The revision is primarily an act of compression and presentation discipline, and I will verify the page target and the legibility fixes myself in the next round.*
