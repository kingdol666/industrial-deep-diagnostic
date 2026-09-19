# Round 19 — Editor-in-Chief Synthesis & Point-by-Point Response

**Manuscript:** "Trustworthy agentic diagnosis for industrial processes" (main.tex, post-revision build)
**Panel:** R1 (methodology), R2 (domain, LLM-FDD), R3 (presentation/figures), DA (data audit), CITE ×3 (citation integrity)
**Pre-revision verdicts:** R1 MAJOR REVISION · R2 MAJOR REVISION · R3 MINOR REVISION · DA PASS WITH FINDINGS (59 MATCH / 0 MISMATCH / 1 UNTRACEABLE-EXT) · CITE 46/46 VERIFIED

## EIC synthesis

The panel converges on one overall judgement: the evaluation machinery is
unusually sound (every number traced and reproduced by two independent
auditors; all 46 references verified real, zero fabrication), and the required
work is bounded. The revision executed below addresses all three shared major
clusters — the identifier-recall channel, the grading-instrument provenance,
and the asymmetric identity-strict accounting — plus all presentation findings.
One reviewer finding (R3-Major-2, the alleged run-id contradiction) was
verified against the figure source and is a misreading; the evidence crop is
archived (`_figtrace_top.png`) and the item is DISPUTED below. Two
execution-demand items (neutralised-identifier re-run; k≥3 repeats) are
resolved by quantified revision contracts plus in-text demotion of the affected
claims, not by new runs inside this revision cycle — the cost (~12 h and ~18 h
of agent time respectively) and the contained harness extension required are
stated in the manuscript itself, and every dependent claim is now qualified in
place so that no headline number relies on the unexecuted control.

## Point-by-point response

### R1 (methodology)

| # | Item | Disposition |
|---|---|---|
| M1 | Identifier channel breaks truth isolation; decisive control deferred | **PARTLY ACCEPTED / CONTRACT.** The neutralised-identifier re-run requires a contained harness extension (hash-id run dirs + identifier-stripped brief headers) and ≈12 h of agent time; it is committed in §9 as the first post-revision execution. R1's own fallback is fully implemented: the three TEP-derived resolved verdicts are now an explicit *recall-possible tier* in the abstract, Table `tab:overall`, and §9; the leakage-sentinel scope (briefs/user-context, not directory names) is now stated in C1 and §9. |
| M2 | Grading instrument calibrated with truth knowledge | **ACCEPTED.** C1 now defines the "v1-era corpus" (pre-discipline batch of the same 12 scenarios), discloses that the published baselines contributed the mechanism synonyms, and states the sentinel's scope. A leave-one-token-out re-scoring over the released keyword-hit records was computed: Top-1 moves to 3/9 only under removal of the single token "header" (IDV1's two hits are spelling variants of one label). Table `tab:overall` now carries an "Instrument readings" block: calibrated 4/9, identity-strict 3/9 [12.1, 64.6], leave-one-token-out 3/9–4/9. |
| M3 | Asymmetric identity-strict accounting | **ACCEPTED.** §7.2 now states that under the strict lens precision becomes 3/4 and overconfidence at least one, "reported rather than quoted in each metric's most favourable lens"; the concurrent-anomaly reading is attached to the precision metric as it was to Top-1. |
| M4 | Bare-arm metric naming; forced-commit counterfactual; inferred mechanism | **ACCEPTED.** Abstract now says the bare call "keyword-scores 9/9 faults (no verdict typing)---more than the pipeline resolves". The forced-commit counterfactual is computed and added to §8.3: forced commitment to the top-ranked survivors yields Top-1 6/9 with three wrong commitments; the cap "trades three false determinations for two foregone resolutions". The cap/elimination-vs-orchestration attribution is now marked *inferred, not tested*; the filter-disabled arm stays pre-registered. |
| M5 | n=1 stability; near-mechanical agreement rule; supersession guard | **ACCEPTED.** §8.4 now names the pair "$n=1$", adds the power remark (the drawn scenario's deterministic signature makes structural agreement close to mechanical; a draw on IDV3 or SKAB would have stressed the rule), and pre-commits that the supersession rule will not be applied selectively. Abstract clause now reads "(one repeat pair)". |
| m1 | §6.1 promise unkept in §9 | **ACCEPTED.** §9 power paragraph adds the selection-bias sentence (purposive selection over-represents documented episodes; intervals read as measurement uncertainty, not population generalisation). |
| m2 | Abstract byte-for-byte qualifier | **ACCEPTED** ("byte-identically (timestamps excluded)"). |
| m3 | metrics.json `calibrated` semantics | **ACCEPTED.** New `results/benchmark/README-artifact-fields.md` + a manuscript footnote at the rubric paragraph. |
| m4 | Rubric R3 mis-specified for controls | **ACCEPTED.** §6.2 R3 entry scoped to fault scenarios with the mis-specification note. |
| m5 | tab:overall capped-verdict row mixes count+property | **ACCEPTED** (relabeled "5 of 9 faults, true mechanism ranked in all five"). |
| m6 | TEP control brief onset declaration | **ACCEPTED — and the check surfaced a real inaccuracy.** The briefs were re-read: TEP and IndPenSim control briefs *do* disclose the segment's normal status; only SKAB's is blind. §6.1 now states exactly this and reframes the zero-false-alarm claim (non-fabrication under an honest brief; SKAB alone tests blind discrimination); §7.2 carries the scope qualifier. |
| m7 | AgentRCA resolvability | **VERIFIED.** The citation-integrity audit resolved arXiv:2607.22385 (Wei & Fink, Jul 2026); record real. |
| m8 | Bare-arm recording timestamps; TEP-control bare coverage | **PARTLY ACCEPTED.** The arms' provenance as recorded replays is already disclosed in Table `tab:ablation` and §8.3; the released `baselines.json` carries the per-reply records. Running the bare arm on the TEP control would change released artifacts mid-revision and is left to the same post-revision execution contract as the neutralised re-run. |
| m9 | Figs 1/3/4 small text | **ACCEPTED** — all ten figures regenerated at the true textwidth (345 pt = 4.77 in, vs the 5.4 in the pipeline assumed) with minimum in-figure text ≥6 pt (see FIGREBUILD.md). |
| m10 | Review-time artifact access path | **ACCEPTED** — Data availability now cites the public repository. |

### R2 (domain)

| # | Item | Disposition |
|---|---|---|
| Maj 1 | Identifier recall; joint worst case unstated; execute re-run | **ACCEPTED (worst case) / CONTRACT (re-run).** Joint worst case now stated in §9: identifier recall + identity-strict discount ⇒ resolved Top-1 could be as low as 1/9; recall-possible tier marked in abstract/Table/Fig. Re-run commitment as in R1-M1. |
| Maj 2 | n=1 stability; execute k≥3 repeats | **PARTLY ACCEPTED / CONTRACT.** Abstract demoted to "(one repeat pair)"; §8.4 adds the power remark and guard. Executing 27 pipeline runs (~54 h) is beyond one revision cycle; the pre-registration stands and the abstract no longer treats the pair as a stability *result*. |
| Maj 3 | Keyword provenance circularity | **ACCEPTED** — as R1-M2 (v1-era definition, baseline-synonym provenance, LoTo sensitivity, instrument-readings block). |
| Maj 4 | Alsaif 2024; Merkelbach 2024; RAG uncited; microservice-RCA scoping | **ACCEPTED.** All three added **after verification**: Alsaif et al. 2024 is *Electronics* 13(24):4912 (DOI 10.3390/electronics13244912) — the panel note said "Sensors"; the actual record was checked on MDPI and it evaluates Siemens forum/PLC fault data, *not* TEP, so the paper cites it for its actual scope (multimodal LLM FDD over industrial fault records). Merkelbach & Hasenauer 2024 (OASIcs DX.2024, 10.4230/OASIcs.DX.2024.31) added. Lewis et al. 2020 (NeurIPS; arXiv:2005.11401) now cited at first RAG use. Microservice-RCA scoping sentence added to §2.2. |
| Maj 5 | AgentRCA missing from positioning table | **ACCEPTED** — row added (TEP series / yes ranked list / partial traces / no / no); the "combines all five" claim now stands with the closest competitor in the table. |
| Maj 6 | No classical RCA baseline; auditability construct unmeasured | **PARTLY ACCEPTED.** Auditability: abstract and §9 now say the margins are *architectural properties, not yet measured outcomes* (rubric = conformance; blinded expert adjudication outstanding). A Granger/TE arm: deferred with scope reasoning — pairwise-influence scoring answers a different question than mechanism-family identification, and a rushed arm would weaken rather than strengthen the suite; it is added to the pre-registration alongside the filter-disabled and engine-substitution arms. We note the paper's own §2.1 already frames the classical RCA lineage as the reading the system must be judged against, and Register A/B keep it as context. |
| m1 | Dangling `\ref{app:artifacts}` ×2 | **ACCEPTED** ("Appendix~\ref" both places). |
| m2 | Venkatasubramanian mislabelled; only Part I cited | **ACCEPTED** — original tripartite labels, Parts I–III now cited (verified DOIs 10.1016/S0098-1354(02)00218-X / -219-1). |
| m3 | "deep classifiers" loose | **ACCEPTED** ("deep anomaly detectors"). |
| m4 | tao2019 survey-level support | **ACCEPTED** ("digital-twin practice (surveyed in …)"). |
| m5 | GxP/ALCOA+/GAMP name-dropped | **ACCEPTED** — GAMP 5 2nd ed. (ISPE 2022) and MHRA 'GXP' Data Integrity Guidance Rev 1 (2018) cited, both existence-verified. |
| m6 | Abstract length | **ALREADY RESOLVED** — the abstract is 245 words (Elsevier limit 250); the reviewer's ~370-word estimate predates the trim in this revision cycle. |
| m7 | "the paper's own PCA implementation" antecedent | **ACCEPTED** ("FaultExplainer's own PCA implementation"). |
| m8 | Lyman & Georgakis 1995 missing | **ACCEPTED with corrected attribution** — added at the TEP dataset introduction as the plant-wide-control companion (CCE 19(3):321–331, DOI verified). It is *not* attached to the detectability claims (those rest on Russell et al. 2000 / Chiang et al. 2001, which compile the detection tables; L&G1995 is the control-design study). |
| m9 | Reference count low; key-year mismatches | **PARTLY ACCEPTED** — 8 additions bring the list to 54. Bib keys are internal identifiers and invisible to readers; rendered years were audited by the citation-integrity pass (46/46 fields match). |
| m10 | IDV3 superlative unsupported | **ACCEPTED** ("commonly regarded", anchored to Russell et al. 2000). |
| m11 | 3/3 CI rounding; Vieira 15.3 pp | **CHECKED.** Wilson lower for 3/3 is 0.43847 → [43.8, 100.0] is correct rounding of the exact value (the reviewer's 43.85 truncation overstates). The 15.3-pp figure was verified against the Vieira et al. record in the bibliographic pass. |
| m12 | Vector figures preferred | **PARTLY ACCEPTED** — all figures re-rendered ≥600-dpi effective at placed width; vector export of the HTML-diagram figures is logged for the production handoff. |

### R3 (presentation)

| # | Item | Disposition |
|---|---|---|
| Maj 1 | In-figure text <6 pt; PRINT_W 5.4 vs real 4.77 in | **ACCEPTED** — root cause confirmed (345 pt = 4.77 in); all ten figures rebuilt at the true width with ≥6 pt minimum text; per-figure verification table in FIGREBUILD.md. |
| Maj 2 | Fig. 3 run-id vs §8.4 contradiction | **DISPUTED — verified not an error.** The figure source (fig_trace.html) and the rendered PNG both read `202609171639066`, the correct tep_d04 directory; §8.4's `202609171639527` correctly belongs to tep_d11. Evidence crop archived (`_figtrace_top.png`). The misread is itself a symptom of Maj 1's tiny text, now fixed. |
| Maj 3 | Em-dash / nested-parenthetical density | **ACCEPTED (focused pass).** The two named worst spots are restructured (abstract; §6.1 dataset paragraph split into per-dataset sentences). A full 150-instance sweep is out of one cycle's risk budget; flagged for the copyedit stage. |
| m1 | artefact/artifact | **ACCEPTED** (unified). |
| m2 | "Three X" scaffolding ×8 | **PARTLY ACCEPTED** — two varied; the remainder carry literal counts. |
| m3 | Repeated mitigation sentence | **ACCEPTED** (§7.3 instance removed; §9 keeps one). |
| m4 | Table 1 bare-citation rows | **ACCEPTED** (named systems: TranAD; Causal RCA e.g. Yue et al.). |
| m5 | Over-long captions (Table 6, Fig. 7) | **ACCEPTED** (Table 6 caption trimmed ~60%; Fig. 7 trim included in the figure rebuild pass). |
| m6 | Table 7 justified narrow column | **ACCEPTED** (`\raggedright`). |
| m7 | Table 2 wrapping | **ACCEPTED** (`\raggedright` columns + tie; released filenames preserved). |
| m8 | Fig. 7 author–year in-figure citation | **ACCEPTED** (dropped; caption cites). |
| m9 | Fig. 2 serpentine unexplained | **ACCEPTED** (caption note added). |
| m10 | Float drift | **PARTLY ACCEPTED** — evaluated; `placeins [section]` already bounds drift and the additions grew the text 3 pages; aggressive `\clearpage` insertion produced near-empty pages in trial and was rejected. |
| m11 | Fig. 9 / Table 8 redundancy | **ACCEPTED** (division-of-labour sentence in Table 8 caption). |
| m12 | Bib hygiene ([6] dup, [21] et al., [1] note) | **ACCEPTED** ([6] url dropped; [1] preprint note dropped — the published CCE record is cited; [21]'s "and others" retained: the Constantinides et al. author list is long and the truncation is standard bibtex practice, verified by the integrity pass). |
| m13 | Byline given/family split | **AUTHOR DECISION** — the byline is the author's legal name format; Elsevier metadata handles mononyms poorly but this is the author's call, flagged for the production stage. |
| m14 | Sentence-initial "Fig." | **ACCEPTED** ("Figure" at sentence start, both spots). |
| m15 | Table A1 tight | **PARTLY ACCEPTED** — longest cell shortened, improving effective size; full landscape rotation deferred to production. |
| m16 | §8 title overloaded | **ACCEPTED** (retitled; case study remains a titled subsection). |

### DA (data audit)

59 MATCH findings: no action. Finding 25's rounding ("200–700" vs 192.8–700.2): **ACCEPTED**, table now reads 193–700. Findings 11/62 label notes: **ACCEPTED** via the artifact README + footnote. Observation 61 (on-disk tree larger than released corpus): **ACKNOWLEDGED** — the interrupted second-round batch is documented in the artifact README and excluded from the released corpus; `tier_state.json` was restored to the canonical batch via the sanctioned `run-tier.mjs import-state`.

### Citation integrity (CITE-A/B/C)

46/46 entries verified real against DOI registries, publisher pages, arXiv, Zenodo/Harvard Dataverse, and the SKAB repository's own citation block; zero fabrication, zero field corrections. The 8 newly added references were each verified before inclusion (MDPI record, OASIcs record, NeurIPS proceedings/arXiv, Crossref DOIs).

## Post-revision status

All major items are resolved or converted into quantified, in-manuscript
contracts with their dependent claims demoted in place. The manuscript was
recompiled (0 LaTeX warnings, 0 undefined references) and re-reviewed by a
fresh panel — see `REREVIEW.md`.
