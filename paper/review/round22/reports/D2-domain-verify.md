# Round 22 — Reviewer D2 (Domain / LLM-Diagnosis) — Blind Verification Report

Scope: verification pass after MINOR revision. Five stated satisfaction conditions of the previous
domain reviewer were checked against (i) the current `paper/main.tex` / `refs.bib` / `main.bbl`,
(ii) the rendered page PNGs (`paper/pagepng/`), (iii) the primary online sources, and (iv) a fresh
re-run of the released FE fidelity gate. Prior-round reports were not read (blindness rule held).
No repository file was modified; bibtex was exercised only on a scratch copy in /tmp.

---

## Condition 1 — Merkelbach citation: VERIFIED

**(a) Bib metadata.** `refs.bib` entry `merkelbach2024multimodal` (lines 518–527) now carries:
- Authors in order: Merkelbach, Silke; Diedrich, Alexander; Sztyber-Betley, Anna;
  Trav{\'e}-Massuy{\`e}s, Louise; Chanthery, Elodie; Niggemann, Oliver; Dumitrescu, Roman —
  **matches the Dagstuhl DROPS record exactly** (fetched
  https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.DX.2024.31).
- Title "Using Multi-Modal LLMs to Create Models for Fault Diagnosis (Short Paper)" — matches
  (the "(Short Paper)" variant).
- OASIcs vol. 125, pp. 31:1–31:15, DX 2024, DOI 10.4230/OASIcs.DX.2024.31 — all match
  (DROPS additionally confirms 35th DX, published 2024-11-26; editors Pill/Natan/Wotawa, not
  required in the bib).

**(b) In-text form.** main.tex line 96 reads "Merkelbach et al.~\cite{merkelbach2024multimodal}";
printed on p.5 as "Merkelbach et al. [34] ... while documenting significant drawbacks."
Grep for "Hasenauer" across `main.tex` and `refs.bib`: **zero matches**.

## Condition 2 — AgentRCA wording: VERIFIED

**Text.** §2.2 (main.tex line 97; printed p.5) now reads: "its evaluation scores Top-1/Top-2
against TEP ground truth but, like FE's, ships no machine-replayable external evaluation harness
(hence Table 1's 'no' on reproducibility)". The old phrase "stops short of an external
truth-comparison harness" is gone (grep: no match). Table 1 (p.6) shows AgentRCA Repro. gate "no",
consistent.

**Factual check** (arXiv 2607.22385, abstract + HTML full text + arXiv API):
- "AgentRCA achieved 40.0% Top-1 accuracy and 61.5% Top-2 accuracy without access to any faulty
  training data" — matches the manuscript's 40.0/61.5 on the TEP evaluation set.
- Exclusions confirmed in the source: "We excluded faults 16–20 because their physical causes are
  unspecified, and faults 3, 9, and 15 because prior literature ... show weak or inconsistent
  diagnostic signatures" — matches the manuscript's IDV3/9/15 detectability exclusion and its
  extension to IDV16–20.
- Output is "a ranked list of diagnostic hypotheses ... accompanied by an evidence-grounded
  textual trace"; no calibrated confidence; uncertainty communication appears only as future work —
  both manuscript statements match.
- Harness: the source only promises code "will be released in a public repository upon acceptance"
  and describes no machine-replayable evaluation harness — "ships no machine-replayable external
  evaluation harness" is accurate.
- "(July 2026)" matches the 24 Jul 2026 v1 date; bib authors Wei/Fink match.

## Condition 3 — Vieira 15.3pp: VERIFIED

**Text.** §2.1 (main.tex line 91): "random segment splits inflate reported AUROC---by up to 15.3
percentage points of Macro-AUROC under segmentation-level leakage in Vieira et al."

**Source check** (https://arxiv.org/html/2509.22267v1, §6.1): "The more severe segmentation-level
leakage produced an higher performance increase, elevating the Macro AUROC by 7.3% and 15.3% for
time and frequency representations, respectively." — "up to 15.3 percentage points" is a faithful
rendering (the larger of the two arms).

**Bib check** (`vieira2026towards`, refs.bib lines 70–78) vs https://arxiv.org/abs/2509.22267:
authors João Paulo Vieira, Victor Afonso Bauler, Rodrigo Kobashikawa Rosa, Danilo Silva (exact);
Mechanical Systems and Signal Processing, vol. 258 (2026), article 114640; DOI
10.1016/j.ymssp.2026.114640 — all match the arXiv journal-ref and related-DOI.

## Condition 4 — FE-replication verification sentence: VERIFIED (gate re-run)

**Text.** sec:ablation, "Model-Controlled Baselines and Pipeline Ablation" (main.tex line 530;
printed §8.3, p.36): "The FE-protocol replication's numerical fidelity is gated, not self-attested:
a released verification script replays the replication's feature extraction against FaultExplainer's
own committed per-fault outputs and passes all 21 checks---$T^2$ statistics to a maximum relative
error of $2.8\times10^{-12}$, anomaly flags agreeing on all 500 rows of every fault, contribution
values to a mean relative error below $1.3\times10^{-12}$, and identical trigger indices under FE's
six-consecutive-anomaly rule---reproducing FE's per-component clip-then-sum aggregation convention".
**Table 8 caption** (tab:ablation, printed p.37) carries the pointer clause: "...verified
check-by-check against FaultExplainer's own committed outputs (21/21; Section 8.3)."

**Gate re-run** (`node baseline-lab/scripts/verify-fe.mjs`): **PASS 21 / FAIL 0.** Observed values
match every printed number:
- t2 max rel err across the 21 files: max 2.84e-12 (fault4) → "2.8e-12" correct;
- anomaly agreement: 500/500 on all 21 fault files;
- contribution mean rel err: max 1.17e-12 (fault11) < 1.3e-12, so "below 1.3e-12" correct;
- trigger indices identical on both sides wherever FE's rule fires (31/31, 37/37, 25/25, ...);
- the script's stated inputs are FE's own committed outputs
  (`baselines/FaultExplainer/frontend/public/fault*.csv`, raw 52 columns + FE-committed
  t2_stat/anomaly/contribution columns), and `fe-official.mjs` implements the clip-then-sum
  convention with an explicit comment ("FE clips EACH component's term at zero BEFORE summing,
  np.maximum(c_ji, 0) inside calculate_c, then .sum()").

## Condition 5 — Filter attribution bound: VERIFIED

**Text.** The anti-spurious-filter subsection (main.tex line 263; printed §4.4, p.15) now reads:
"In the benchmark this filter is the mechanism by which the pipeline bars control-loop correlations
from causal citation, and the reason normal batches with impulsive recipe-dosing spikes ($|z|$ up to
16.2) are graded as healthy rather than faulty. The corpus does not isolate the filter's marginal
necessity: the filter-free bare-LLM arm of Section 8.3 also passes its two covered controls, and
isolating the filter's contribution requires the pre-registered filter-disabled arm."

- (b) fully satisfied: explicit non-isolation statement, cross-reference to the filter-free
  bare-LLM arm's covered-control passes, and to the pre-registered filter-disabled arm.
  Corroborated elsewhere: Table 8 records the bare arm at "2/2; zero false alarms" on its two
  covered controls (the TEP fault-free control disclosed as not run bare), and the filter-disabled
  arm is consistently pre-registered/future work in the setup-disclosure, ablation-results, and
  discussion passages.
- (a) satisfied in substance: the blanket "filter is the reason the controls pass" claim is gone.
  The remaining "the reason ... graded as healthy rather than faulty" clause is scoped to the
  pipeline's own decision procedure on the spiky control batches (a code-inspectable mechanism
  claim), and the very next sentence explicitly disclaims marginal necessity — the passage as a
  whole no longer attributes the control outcomes to the filter as an evidential claim.
- Factual anchor for |z|=16.2: released diagnostic-run artifacts
  (`workspace/diagnostic-runs/202609171636045_bench_indpensim_batch001_control/04_diagnostics/`
  and the 202609181734271 re-execution) record Fa max_abs_z=16.2 with impulsive recipe-dosing pulse
  morphology on the normal IndPenSim batch control; §7.4 (printed p.32) states the same figure and
  attribution consistently.

## BibTeX spot-check: CLEAN

`bibtex main` re-run on a scratch copy of `main.aux` + `refs.bib`: exit 0; **no "skipping"
warnings**. Three benign warnings only — "empty pages" in yao2023react (ICLR), lewis2020rag
(NeurIPS 2020), zheng2023judging (NeurIPS 2023 track) — conference entries that legitimately have
no page numbers. The regenerated `merkelbach2024multimodal` bbl entry renders all 7 authors with
correct accents ("L.~Trav{\'e}-Massuy{\`e}s"), "(short paper)", OASIcs vol. 125, pp. 31:1--31:15,
DOI link, and is byte-identical to the committed `main.bbl` entry.

---

## Notes and new observations (non-blocking)

1. **Section-number drift between the revision conditions and the current print** (not a manuscript
   defect): the conditions' "§4.5" is printed as **§4.4 Anti-Spurious-Correlation Filter** (p.15)
   and "§7.3" as **§8.3 Model-Controlled Baselines and Pipeline Ablation** (pp.35–38; Table 8 on
   p.37). Identification was by the given titles/labels, which are unambiguous; the manuscript's
   internal cross-references ("Section 8.3" on pp.13, 15, and in Table 8's caption) are consistent.
2. **wei2026agentrca bib title prefix (cosmetic):** the bib title is "{AgentRCA}: Agentic Root
   Cause Analysis through Evidence-Grounded Reasoning", but the arXiv-registered title (API and
   document header) has **no "AgentRCA:" prefix**. Optional alignment; does not affect any claim.
3. The three empty-pages bibtex warnings above are pre-existing and benign.

All five satisfaction conditions are met in the printed text and every checked number/claim is
factually accurate against its primary source or the re-run gate.

VERDICT: SATISFIED-ACCEPT
