# CONTENT AUDIT — round18, final pre-submission read

Manuscript: `paper/main.tex` (691 lines, read in full; READ-ONLY).
Ground truth read: `results/benchmark/{metrics.json, rubric.json, baselines.json, suite_determinism.json, consistency_audit.json, retest_selection.json}`, `scripts/benchmark/cases/benchmark_cases.json`, plus artifact-level verification against the 13 released run dirs (`04_diagnostics/diagnosis.json`, `.pipeline_events.jsonl`) and `results/benchmark/gradings/`.

---

## PASS A — NUMBER CONSISTENCY (final text)

### A.1 Headline numbers — ALL VERIFIED against ground truth

| Claim (location) | Paper | Ground truth | Status |
|---|---|---|---|
| Top-1 (abstract, §1 contrib 4, §7.1, tab:overall, §10) | 4/9 = 44.4%, Wilson CI [18.9, 73.3] | metrics.json top1=4/9, cdr_ci95 [18.88, 73.34] | OK |
| top-k (abstract, §1, §7.1, tab:overall, §9, §10) | 9/9, CI [70.1, 100] | metrics topk=9; Wilson(9/9)=[70.09,100] recomputed | OK |
| Controls | 3/3 pass, zero false alarms | metrics control_pass=3, false_alarms=0; CI [43.8,100] recomputed | OK |
| Rubric (abstract, §7.1, tab:overall, §10) | 94.6/100; nine at 100, two at 85, one at 65 | rubric.json: 9×100, {skab_valve 85, tep_d01 85}, {batch001_control 65}; mean 1135/12 = 94.58 | OK |
| Judge gate (§7.1, tab:overall) | 94.7 mean, range 90–98, n=12 | per_case judge scores mean 1136/12 = 94.67, min 90 (tep_d03 post-repair), max 98 (tep_d07) | OK |
| DET precision | 4/4 | 4 DETERMINED faults (d01, batch093, d07, d14), all top1=true | OK |
| Verdict-type compliance | 8/9, CI [56.5, 98.0] | metrics calibrated=8; miss = skab_valve (type CS vs allowed [DETERMINED], per rubric R4); Wilson recomputed [56.5, 98.0] | OK |
| Five capped verdicts truth-ranked | 5/9 | CS cases: skab_valve, skab_cav, tep_d03, tep_d04, tep_d11 — all topk=true | OK |
| Finalisation / consistency / determinism | 12/12 PASS; gate verified; 45/45 byte-identical (timestamps excluded) | metrics finalize_passed ×12; suite_determinism compared=45 identical=45 DETERMINISTIC | OK |
| Deduction decomposition (§7.1 + tab:overall caption) | skab_valve −15 (R4 type), tep_d01 −15 (R4 calib 0.91 vs 0.90), indpensim control −35 (R4 0.93 vs 0.90 −15; R3 −20) | matches rubric.json checks exactly | OK |
| Non-CS ceiling row | 5/7, two exceed by 0.01/0.03 (0.91, 0.93) | non-CS states: 0.91, 0.78, 0.80, 0.82, 0.86, 0.90, 0.93 | OK |
| FE Register-A (§8.1) | GPT-4o 7/11 (63.6%, CI [35.4, 84.8]); o1-preview 9/11 (81.8%, CI [52.3, 94.9]); no-candidate regime 8/11; TEP subset 3/6 CI [18.8, 81.2]; matched subset 3/4 vs 3/4 vs 4/4 | all Wilson intervals recomputed and correct; transcription claims consistent with tab:perfault | OK |
| Ablation table (tab:ablation) | FE-protocol 6/6 (all three arms); FE-official 5/6; single-LLM 9/9; controls 2/2 zero FA; PCA IDV3 T²2.9/SPE 4.8, IDV4 SPE 100 vs T² 48.8, controls 1% | baselines.json: strict/FE-style 6/6 per arm; fe_official 5/6 (miss tep_d04); llm 9/9 faults, 2/2 normal controls, 0 false alarms; pca d03 0.0288/0.0475, d04 0.4875/1.0, controls 0.0101–0.0106 | OK |
| Stability (abstract, tab:stability, §7.5, fig:consistency, §10) | R1 CS 0.62 / R2 CS 0.60, Δ −0.02; within-era 1/1, zero divergences; 11 scenarios single-execution; seed 1003818694 | consistency_audit.json: pair CONSISTENT, conf 62 vs 60, agreement 1/1, insufficient_runs 11; retest_selection.json seed/uniform/index match | OK |

### A.2 §6.1 batch-93 description (line 326) vs benchmark_cases.json truth — MINOR MISMATCH

Paper: "whose logged deviation is actuator-side: out-of-band pH and temperature excursions driven by the acid-dosing and heating-water flows".
Truth field (indpensim_batch093): "pH 与温度控制执行侧多执行器同步越限（酸流加、加热水），被控量 pH 与底物浓度出带" — i.e. the multi-actuator limit violation is on the acid-dosing and heating-water flows, and the **controlled** variables out-of-band are **pH and substrate concentration** (temperature appears only at the actuator/flow level).
"Actuator-side", "acid-dosing", "heating-water" all match; but "out-of-band … temperature excursions" shifts the out-of-band attribute from substrate concentration to temperature. Minor note (4 below); the sentence explicitly attributes the description to the case definition, so the paraphrase should track it.

### A.3 "3/7" Top-1 excluding near-tautological tokens (§6.2 line 353 setup, §7.1 line 367 number) — VERIFIED

9 faults − {skab_valve1_1 (keywords contain 阀/valve), indpensim_batch093 (keywords contain deviation/偏差)} = 7; Top-1 winners among the 7 = tep_d01, tep_d07, tep_d14 → **3/7**. Paper states 3/7 with the correct two exclusions. Confirmed from gradings/indpensim_batch093.json that the generic token is in the hit set (kw_hits include 偏差), so §6.2's "supported by the generic token" is accurate.

### A.4 Per-CS rank disclosure (§7.3 line 456) vs diagnosis.json — TWO PRECISION FAILURES

Surviving-hypothesis order read from each graded run's `04_diagnostics/diagnosis.json` vs `benchmark_cases.json` truth:

| Case (graded run) | Survivors (ranked) | Truth rank | Paper claim | Status |
|---|---|---|---|---|
| skab_valve (202609171630389) | S1 downstream throttling 0.65; S2 upstream supply restriction 0.60 | S2 = truth → **2nd of 2** | "second of two" | OK |
| skab_cav (202609171630579) | S1 valve throttling 0.64; S2 suction-side cavitation 0.64 | S2 = truth → **2nd of 2** | "second of two" | OK |
| tep_d04 (202609171639066) | S1 inlet-temp step 0.65; S2 UA loss 0.65 | S1 = truth → **1st of 2** | "ranks first" | OK |
| tep_d03 (202609171632563) | S1 steam-side thermal 0.55; S2 stripper feed thermal state (D/E feed temp) 0.50; S3 condenser/separator cooling 0.40 [WEAK_EXCLUSION, not in CS1] | S2 = truth → **2nd of 3 survivors** (2nd of the 2-member CS1 fork) | "second of two" | **MISMATCH** — the released rubric itself records surviving=3 |
| tep_d11 retest (202609172247007) | S1 branch-level cooling-branch unmeasured disturbance 0.72; S2 steam branch 0.38; S3 form A inlet-temp variation 0.55; S4 form B UA loss 0.48 | S3 = documented truth; S1 subsumes it at branch level → truth-family 1st, specific truth 3rd of 4 (1st of its 2-form fork) | "the documented truth ranks first in … (IDV4, IDV11)" | **OVERSTATED** — holds only at family/branch level |

The contrast the sentence draws ("the documented truth ranks first" vs "the truth-family is ranked second") is exactly what a reviewer will re-check against the released artifacts; both flagged cells deviate.

### A.5 §9 cost medians (line 574) — RECOMPUTED, VERIFIED

Recomputed from `.pipeline_events.jsonl` agent_start/agent_complete spans across **all 13** released event logs (better than the requested 3-sample check):

| Stage | Paper | Recomputed median (13 runs) |
|---|---|---|
| Ontology | ≈14 min | 14.0 |
| Statistics | ≈22 min | 21.9 |
| Diagnosis | ≈20 min | 20.1 |
| Two review stages combined | ≈29 min | 29.3 |
| Reporting + HTML ("the remaining") | ≈26 min | 26.7 (remainder of total: 111.7 − 85.3 = 26.4) |
| Median full-pipeline agent span | ≈1.9 h (≈112 min) | 111.7 min = 1.86 h |
| Retest end-to-end | ≈2.0 h (117 min event span) | 117.1 min wall span (§6 line 359 also says 117) |
| Canonical batched spans | ≈6.0–6.3 h | 361–375.5 min |

All consistent. Also cross-checked §3's batching statement and §6/§9's cross-references.

### A.6 IDV11 signature 40.1/16.4 (retest) vs 6.3/4.0 (superseded run) — VERIFIED

- Retest primary_finding: 方差×40.1 (XMV_10 flow), 温度方差×16.4, Δmean 0.01σ, lag-5 (900 s) r=−0.636.
- First run (202609171639527, superseded): ×6.33 / ×4.04.
- Paper §6.2 (line 406) and tab:mech (line 429) both use **40.1/16.4** with conf 0.60; grep confirms 6.33/4.04 appear **nowhere** in main.tex. tab:stability confidences (0.62/0.60, Δ −0.02) match consistency_audit.json (graded canonical = retest, as metrics.json per_case also records). §7.5's lag-5 r=−0.636 matches the retest. Consistent everywhere the canonical run is described.

---

## PASS B — TONE REGRESSION on new/edited passages

Scanned: §2 citations area (91–123), §4.1 elimination weighting (226), §5 C1 keyword paragraph (277), §6.1–6.2 (326–410), §7.2–7.3 (456–458), §8.1 caveats (464–472), §8.4 stability (535–551), §9 cost/deployment/provenance (566–591), §10 (596–598).

- Banned vocabulary: **zero** hits for crucial / comprehensive / notably / It is worth noting / landscape / delve / furthermore / moreover / underscore / leverage / showcase / pivotal / seamless.
- Em-dash pileups: no sentence with 3+ em-dashes found (line-level counts of 3–6 are per-paragraph; per-sentence max is a paired aside, occasionally 2 + a nested parenthetical, e.g. line 326's opening sentence — within the paper's established style).
- Comma splices: none found in the scanned passages (punctuation is semicolon/dash-governed throughout).
- Performative disclosure verbs: "we state" ×1 (line 535), "we disclose" ×2 (lines 568, 589), "we refrain" (472), "We note" (287) — each carries concrete content in a limitations/disclosure context; acceptable, density not alarming.
- Formulaic enumerators: **"Three design decisions deserve emphasis" (line 328)** and **"Three observations deserve emphasis" (line 404)** — the identical template twice in adjacent sections; minor style note (5 below), not a new reintroduction of removed text.

## PASS C — COHERENCE (abstract → §1 → §5 → §7 → §10)

- **Dangling cross-references: none.** All 34 `\ref` targets resolve; `eq:ceiling`/`eq:verdict` are referenced via `\eqref`.
- **Uncited floats: 2.** `tab:stability` (line 537) and `fig:consistency` (line 553) are never cited in prose — every other table/figure is. Editorial must-fix (3 below).
- **Verbatim repetition:** no duplicated sentences; one near-verbatim restatement — "The twelve canonical scenarios were executed as concurrent batches under one orchestrating agent…" appears at line 359 (§6 Implementation) and line 574 (§9 Cost). Cross-section consistency device; minor note (6).
- **Abstract vs conclusion:** every abstract promise is delivered in §10 with identical numbers (4/9 44.4% CI [18.9,73.3]; top-k 9/9; zero false alarms; five capped verdicts ranking truth and naming measurements; 9/9 bare-LLM bound; retest reproducing verdict state/actuator/mechanism class within two points; 45/45 byte-identical; rubric 94.6). No contradictions found between abstract, §1, §5, §7, and §10; the 0.91/0.93 gate-gap story is told identically in §4.1, §7.1, §7.3, fig:calib, and §10.

---

## CONTENT VERDICT: ISSUES

Must-fix (3):

1. **§7.3 line 456 (IDV3 rank):** "in the SKAB valve and IDV3 cases the truth-family is ranked second of two" — the IDV3 surviving set has **three** hypotheses (the released rubric records surviving=3; the third, condenser/separator cooling, is a WEAK_EXCLUSION residual outside CS1). The truth ranks 2nd of 3 survivors (2nd of the two-member separating fork). Reword, e.g. "second of its three surviving hypotheses, second of two within the indistinguishable set".
2. **§7.3 line 456 (IDV11 rank):** "the documented truth ranks first in two of the five capped verdicts (IDV4, IDV11)" — in the graded IDV11 re-execution the top-ranked survivor is the **branch-level** cooling-branch conclusion (conf 0.72); the documented truth's specific form (inlet-temperature random variation) is ranked **3rd of 4** survivors, though first within its two-form separating fork and first at family level. Reword to family level (as §7.5 already does) or state both facts; the current sentence is falsifiable from the released diagnosis.json.
3. **Uncited floats:** `tab:stability` (line 537) and `fig:consistency` (line 553) are never referenced in the text; add citations in §7.5 (e.g. "Table~\ref{tab:stability} … Fig.~\ref{fig:consistency}") per Elsevier practice.

Minor notes (no numbering obligation):

4. §6.1 line 326: batch-93 paraphrase — case definition puts out-of-band at **pH and substrate concentration** with temperature deviating at the actuator (heating-water flow) level; consider "out-of-band pH and substrate excursions driven by acid-dosing and heating-water actuator deviations".
5. "Three X deserve emphasis" template appears twice (lines 328, 404); vary one.
6. The batching sentence is repeated near-verbatim at lines 359 and 574; compress the §9 instance to a cross-reference.
