# Data Auditor (DA) — Number-Trace Audit Report

Manuscript: `paper/main.tex` (blind review, first read)
Round: 19 · Auditor: DA (number traceability) · Date: 2026-09-19

## Audit Scope

Every quantitative claim in the Abstract, Table `tab:overall`, Table `tab:mech`, Table `tab:ablation`, Section 6.4 (stability), the cost paragraph, the case study (IDV4, batch-93), and the per-scenario signature numbers was traced to the released evidence corpus:

- `results/benchmark/metrics.json` (canonical aggregates + per_case, generated 2026-09-18T01:02Z)
- `results/benchmark/gradings/*.json` (12 per-scenario grading records)
- `results/benchmark/journal.jsonl` (13-line append-only scoring journal)
- `results/benchmark/consistency_audit.json`, `retest_selection.json`
- `results/benchmark/baselines.json` (PCA / FE-protocol / bare-LLM arms)
- `results/benchmark/suite_determinism.json`, `repro_report.json`, `rubric.json`
- `results/benchmark/benchmark_report_en.md` (machine-generated; Appendix A ground truth read audit-side only)
- Run artifacts under `D:\codes\idd-run-archive\diagnostic-runs\<dir>\` (mirror of the graded `workspace\diagnostic-runs\` 2026-09-17 batch: 12 canonical runs + drawn re-execution `202609172247007_bench_tep_d11_reactor_cooling_random`), including `.pipeline_events.jsonl`, `04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json`, `02_processed/*`, `pipeline_finalize_report.json`
- LaTeX integrity: `\label`/`\ref` graph, `\includegraphics` targets, `refs.bib` keys (checked programmatically)

All Wilson 95% intervals were independently recomputed (z = 1.96). Per-stage wall-clock medians were recomputed from all 13 released event logs with sequential agent_start/agent_complete pairing.

## Findings

Verdicts: **MATCH** = paper number reproduced from released artifacts; **UNTRACEABLE-EXT** = external-literature number, not expected to be in the corpus (paper flags it as a transcription); **NOTE** = cosmetic/wording observation, no numeric disagreement.

### A. Abstract and Table `tab:overall` vs `metrics.json`

1. 12 scenarios, 3 datasets, 9 fault + 3 control | metrics.json total_cases 12, fault 9, control 3; tab:bench composition 2+1/6+1/1+1 | **MATCH**
2. Top-1 4/9 = 44.4%, Wilson CI [18.9, 73.3] | metrics.json top1=4, cdr=0.4444, cdr_ci95 [18.88, 73.34]; recomputed Wilson identical | **MATCH**
3. Top-k 9/9 = 100%, CI [70.1, 100.0] | metrics.json topk=9; recomputed Wilson lower 0.7009 | **MATCH**
4. Determined-verdict precision 4/4, CI [51.0, 100] | 4 DET faults all top1=true (journal rows 4,7,10,12); Wilson 4/4 lower 0.5101 | **MATCH**
5. Capped CS verdicts 5/9, confidences 0.55–0.63 | journal/gradings: 60, 60, 55, 63, 60; all ≤ 0.65/0.70 caps | **MATCH**
6. Ceiling compliance capped states 5/5 | all five CS confidences ≤ 0.65 | **MATCH**
7. Ceiling compliance non-CS 5/7, two exceed 0.90 by 0.01/0.03 | non-CS set = {0.91, 0.78, 0.80, 0.82, 0.86, 0.90, 0.93}; exactly 0.91 and 0.93 exceed | **MATCH**
8. Verdict-type compliance 8/9, CI [56.5, 98.0] | rubric.json skab_valve1_1 fail (CS not in allowed ["DETERMINED"]) is the single miss; recomputed Wilson [0.565, 0.980] | **MATCH**
9. Controls 3/3, zero false alarms, CI [43.8, 100.0] | metrics.json control_pass 3, false_alarms 0; Wilson 3/3 lower 0.4385 | **MATCH**
10. Rubric mean 94.6, nine at 100 / two at 85 / one at 65 | metrics.json mean_rubric 94.6; rubric scores {85,100,100,85,100,100,100,65,100,100,100,100} | **MATCH**
11. Deductions: valve −15 R4 verdict-type; IDV1 −15 R4 calibration 0.91 vs 0.90; IndPenSim control −35 (R4 0.93 + R3 grounding) | rubric.json fails exactly these checks with exactly these values | **MATCH** (NOTE on naming: rubric.json calls the valve check `R4_calibration`; its substance is the allowed-set/verdict-type violation the paper describes — finding 8's file evidence)
12. Judge mean 94.7, range 90–98, 12/12 finalize PASS | metrics.json judge scores {95,90,97,96,90,96,96,94,97,98,93,94}, finalize_passed ×12 | **MATCH**
13. Artifact-consistency gate "verified" | repro_report.json status "REPRODUCIBLE", failures [], drift_fields [] | **MATCH**
14. Abstract: bare same-model call resolves 9/9 | baselines.json summary "all 9/9 faults hit"; per-case strict_top1_hit true ×9 | **MATCH**
15. Abstract: seeded re-execution reproduced verdict/actuator/mechanism class within two confidence points; 45 files byte-for-byte; integrity 153 | consistency_audit Δconfidence 2; suite_determinism 45/45; repro dataset 153/153 | **MATCH**

### B. Table `tab:mech` per-scenario rows vs metrics/gradings/run artifacts

16. SKAB valve: CS 0.60, rubric 85 | grading + journal + consistency_audit (conf 60) | **MATCH**
17. SKAB valve signature: plateau −3.13% (p=5.7e−158, rows 621–927); −0.115 A (p≈0.10); 0.327-bar quantisation | run `202609171630389`: "32→30-31 L/min, −3.13%, MW p=5.73e-158", "rows 621-927", "−0.115 A, p=0.1016", "量化步长0.327 bar"; survivor H1 65 (confidence.json) ∥ H2 60 | **MATCH**
18. SKAB cavitation: CS 0.60, rubric 100; 76 rows, 40 bursts of 1–3 s; 2.34 vs 2.40 A; +5%/+3%; +0.23 K | run `202609171630579`: "76/923 行, 40 次 1-3 s", "2.338 vs 2.396 A", "+5.0%/+3.0%", "+0.233 ℃" | **MATCH**
19. TEP IDV1: DET 0.91, rubric 85; +18.5σ lockstep r=0.9996; C-side −2.9/−6.9σ; steam trails lag 2 | run `202609171632332`: "XMV_3/XMEAS_1 +18.5σ/+18.7σ … XMV_4/XMEAS_4 −2.9σ/−6.9σ", "r(XMV_3,XMEAS_1)=0.9996", "最优滞后2采样(360s), lag补偿r=0.9457" | **MATCH**
20. TEP IDV3: CS 0.55, rubric 100; means ≤0.92σ; stripper steam var ×2.1–2.7, Levene p<1e−4; reactor settling z=−0.001 | run `202609171632563`: "全列均值偏移≤0.92σ", "方差×2.1-2.7", "Levene p<1e-4", "settled z=-0.001" | **MATCH**
21. TEP IDV4: CS 0.63, rubric 100; temp z=+10.5; XMV_10 +6.8σ step; loop-external flat | run `202609171639066`: "XMEAS_9 单样本尖峰 z=+10.47", "+6.82σ (41.14%→44.90%) … 无 ramp", "XMEAS_22 全程平坦(−0.08σ)"; see also findings 40–42 | **MATCH**
22. TEP IDV7: DET 0.78, rubric 100; XMV_4 +25.1% (z=12.4); gain −20.1% ⇒ ΔP ratio 0.64 | run `202609171639214`: "+25.13% (z=12.35)", "阀位增益损失(−20.11%)", "ΔP降至原0.638" | **MATCH**
23. TEP IDV11: CS 0.60, rubric 100; VR 40.1/16.4; Δmean ≤0.01σ; actuator leads 5 samples r=−0.64; lag-0 flip barred | canonical re-execution `202609172247007`: "方差×40.1", "温度方差×16.4", "均值位移仅0.01σ", "lag-5 (900 s) r=-0.636", "lag-0 +0.501为闭环符号翻转，禁引" | **MATCH** (NOTE: these are quoted from the canonical re-execution, as the paper states; the superseded batch run recorded XMEAS_9 var ×4.04 and valve mean drift +1.22σ — the paper's numbers trace to the run metrics.json grades, which is the correct binding)
24. TEP IDV14: DET 0.80, rubric 100; VR ×189/116/222; 633/800; lag tightens 1→5 (r=0.998/−0.964) | run `202609171640072`: "×189.4/×115.8/×221.5", "800个间隔中633次", "斜率+0.0345, r=0.998", "r=-0.9646/-0.9649" | **MATCH**
25. IndPenSim batch-93: DET 0.82, rubric 100; CW loop pinned 2.0 vs 200–700 L/h, 72/72 rows → 301.4 K; release → in band 2.4 h | run `202609171633340`: "Fc 恒等于 2.0 L/h ×72 行", "健康基线响应为 192.8-700.2 L/h", "T_max 301.44 K", "90.2 h 执行恢复后温度在 2.4 h 内自行回落入带" | **MATCH** (NOTE: "200–700" rounds the artifact's 192.8–700.2; rounding up 192.8→200 flatters the low end by ~3.7% — cosmetic)
26. Controls row: 3 DET normal, rubric 100/100/65, confidences 0.86–0.93; zero false alarms | journal: 0.86/0.90/0.93; rubric 100/100/65 | **MATCH**
27. Control signature numbers: IndPenSim |z|=16.2; TEP |r|≥0.95; SKAB |r| 0.71–0.89 | runs: "max_abs_z=16.2"; "阀门-流量对r≥0.95@lag0"; SKAB strong group |r| 0.706–0.830 plus refuted r=−0.891 | **MATCH** (NOTE: SKAB control's own primary_finding says "all strong raw correlations |r|=0.45–0.89"; the paper's 0.71–0.89 matches the specific refuted strong group it discusses, incl. r=0.713/0.706/−0.891)

### C. Table `tab:ablation` vs `baselines.json`

28. Classical PCA detection: IDV3 T² 2.9%/SPE 4.8%; IDV4 SPE 100% vs T² 48.8%; controls ~1% | baselines.json pca: tep_d03 0.0288/0.0475; tep_d04 0.4875/1.0; controls 0.0101–0.0106 | **MATCH**
29. PCA diagnosis arm: top-3 contributions only, no mechanism verdict | pca.*.top3_contribution_variables present; no verdict field | **MATCH**
30. FE-protocol replication (candidates, FE-style top-3 + alias) 6/6 | baselines.json summary fe_protocol_replication_with_candidates "6/6" | **MATCH**
31. FE-protocol (candidates, strict) 6/6 and (no candidates, strict) 6/6 | summary "strict single-verdict 6/6" ×2; per-case with_candidates/no_candidates strict_top1_hit true ×6 TEP faults | **MATCH**
32. FE official prompts (GLM, T²-contribution features): FE-style 5/6 and strict 5/6 | summary fe_official_prompts_strict "5/6"; per-case fe_official: 5 hits, tep_d04 miss (top3 = IDV1/2/8, strict_top1_hit false, fe_style_top3_hit false) — both readings give 5/6 | **MATCH**
33. FE official arm miss pattern (misses IDV4, feed-composition features dominate) | tep_d04 fe_official top3 = IDV(1)/IDV(2)/IDV(8) feed-composition faults | **MATCH**
34. Single-LLM identical blind digest 9/9 strict | summary "TEP 6/6, non-TEP 3/3 (all 9/9 faults hit)" | **MATCH**
35. Single-LLM controls 2/2, zero false alarms, TEP control not covered | summary controls "2/2", note "not every control was run"; skab_normal + batch001 normal_verdict true; benchmark_report_en.md §9.3 declares the tep_d00 gap | **MATCH**
36. IDD full pipeline 4/9 resolved, 5 capped CS with true mechanism ranked | metrics.json; journal topk=true ×9 | **MATCH**

### D. Stability section vs consistency_audit.json + retest_selection.json

37. Seed 1003818694, mulberry32, pool 9 faults-only, index 7 → tep_d11 | retest_selection.json: seed/rng/pool/index/case_id identical; raw draw u=0.846792349 recorded as claimed | **MATCH**
38. Run ids: original batch `202609171639527` (0.62), drawn re-execution `202609172247007` (0.60, canonical) | consistency_audit.json pair record + canonical_run_dir; metrics.json tep_d11 run_dir = 202609172247007 | **MATCH**
39. Confidence pair 0.62/0.60 (Δ=0.02), both under 0.65 cap; audit CONSISTENT; within-era agreement 1/1, zero divergences, 11 scenarios outstanding; token overlap 0.14 | audit: confidence_run 62 / canonical 60, delta 2, verdict CONSISTENT, same XMV10 tag + ENVIRONMENT class, cause_token_overlap 0.1417, summary within_era_agreement "1/1", insufficient_runs 11 | **MATCH**

### E. Cost claims vs event logs

40. Drawn re-execution ≈2.0 h, 117 min event span | `.pipeline_events.jsonl` of 202609172247007: run_initialized 22:47:00.748Z → run_completed 00:44:06.205Z = 117.1 min | **MATCH**
41. Canonical batch runs ≈6 h event spans (batching) | 12 canonical logs span 361.0–375.5 min (≈6.0–6.3 h) | **MATCH**
42. Median full-pipeline agent span ≈1.9 h ≈ 112 min (n=13) | recomputed per-run agent-busy sums: median 111.7 min | **MATCH**
43. Stage medians: ontology ≈14, statistics ≈22, diagnosis ≈20 min | recomputed: 14.0 / 21.9 / 20.1 min | **MATCH**
44. Two review stages ≈29 min combined; reporting+HTML ≈26 min | judge median 9.8 + report-reviewer (pre-audit + final audit) median ≈18.4 ⇒ ≈28.2; reporter+html-visualizer+html-reviewer median ≈26.7 | **MATCH** (reading "two review stages" = judge stage + report-reviewer stage, both of its appearances; components sum to ≈112 as stated)
45. Re-execution per-stage sanity (spot-check of the drawn dir): ontology 13m58s, statistics 22m13s, diagnosis 26m54s | event log timestamps | **MATCH**

### F. Determinism, integrity, framework counts

46. Deterministic suite 45/45 byte-identical, verdict DETERMINISTIC, timestamps excluded | suite_determinism.json compared 45 / identical 45 / differing 0; method discloses executed_at exclusion exactly as the paper phrases it | **MATCH**
47. Dataset integrity 153; coverage 12/12; execution proofs 12/12 | repro_report.json 153/153 verified, 0 mismatched; cases 12 prepared/graded; pipeline_log_pass 12, finalize_pass 12 | **MATCH**
48. Grader's 14-artifact completeness set | tab:artifacts list consistent with run-dir contents (spot-checked 202609172247007: all 14 present); Step-9 "≈45-check inventory" ≈ finalize report's inventory 33 + schema 14 = 47 checks | **MATCH** (approximate count, marked "≈" in paper)
49. Thirteen-run journal; RAG unavailable in every run; no L6 evidence | journal.jsonl 13 lines; not contradicted by any artifact read (degradation flags in checks; execution_integrity by_engine stats-package ×12) | **MATCH**
50. IDV3 repair disclosure: round-1 judge 75 with two blocking issues → targeted repair → 90; twelve of thirteen runs without diagnosis-layer repair | run `202609171632563` diagnosis.json repair_history: "score=75，2项blocking issue", scope "targeted repair"; event log shows judge repair_round 2; gradings judge_score 90. Other runs show empty repair history | **MATCH**

### G. Case-study numbers (IDV4) and cross-reference integrity

51. XMV_10 step 41.1%→44.9%, +6.8σ, no ramp | evidence.json/diagnosis.json: "+6.82σ (41.14%→44.90%, Welch t=-79.4, p=4.75e-164)"; z-window series non-monotonic (step, not ramp) | **MATCH**
52. Reactor temp z=+10.5; sister thermocouple +2.0/−2.3σ; separator-outlet −0.08σ | diagnosis.json: "z=+10.47", "XMEAS_21 瞬变 +2.01/-2.34σ", "XMEAS_22 … −0.08σ" | **MATCH**
53. Eliminations "each at ≥95% confidence"; six hypotheses, four eliminated | diagnosis.json hypotheses H1–H6; elimination_confidence 95,95,95,95; survivors H1+H6 (survival_count 2 in consistency_audit) | **MATCH**
54. UA-fork quantification: approach below 1.5 K ⇒ coolant inlet above ≈93 °C vs ≈26 K observed approach | optimizer.md / render_manifest.json / run_summary.json: "(T21−Tin)_old ≤ 1.47°C、Tin_old ≥ 93.1°C、T9−T21 ≈ 25.8°C" | **MATCH**
55. Verdict CS 0.63, INDISTINGUISHABLE ceiling 0.65, inlet-temperature step top-ranked, UA loss second | run_summary.json "{H1 … rank1; H6 突发 UA 阶跃 rank2} INDISTINGUISHABLE, ceiling 65"; consistency_audit conf 63, mechanism "冷却水入口温度阶跃升高" | **MATCH**
56. Judge 97/100, HTML review pass for IDV4 | grading + journal (judge 97, html_review pass) | **MATCH**
57. LaTeX cross-references: 0 undefined `\ref`, 0 duplicate labels, 10/10 `\includegraphics` files present in `paper/figures/`, 46/46 cite keys present in refs.bib | programmatic scan of main.tex | **MATCH** (3 labels never referenced: sec:intro, sec:anatomy, sec:conclusion — harmless)
58. Table A1 + comparison prose: IDD TEP Top-1 3/6 CI [18.8, 81.2]; shared detectable subset 3/4; top-k 6/6 | metrics tep top1=3/6 (IDV1/7/14); recomputed Wilson [0.188, 0.812]; gradings tep topk 6/6 | **MATCH**
59. Identity-strict Top-1 3/9 CI [12.1, 64.6] (batch-93 discount); clean-subset Top-1 3/7, top-k 7/7 | recomputed Wilson [0.1206, 0.6459]; batch-93 kw_hits ["加热","执行器","偏差"] include the generic token "deviation" per Appendix A keyword set — discount arithmetic consistent | **MATCH**
60. External-literature numbers (Register A/B): FE GPT-4o 7/11 (63.6%, CI [35.4, 84.8]), o1-preview 9/11 (81.8%, CI [52.3, 94.9]), no-candidate 8/11 both; AgentRCA 40.0%/61.5%; TEP deep 0.887–0.907; BeatGAN 0.970; SKAB 0.85/0.88; bearing AUROC 0.75–0.93 | third-party publications; Wilson CIs on the FE fractions recomputed and correct; corpus contains no artifact for them, and the paper explicitly frames these as transcriptions ("we transcribe the reported figure") | **UNTRACEABLE-EXT** (by design, disclosed)

### Observations (no action required, recorded for the panel)

61. A second, newer 12-run batch (run-dirs prefixed `2026091817xxxx`) exists on disk in both `workspace/diagnostic-runs/` and the archive, postdating the released metrics/report (generated 2026-09-18T01:02Z). It is not referenced by the paper, and every paper number binds cleanly to the released 2026-09-17 corpus; the "current corpus holds exactly one case-version pair" statement is true of the released audit artifact as generated. Flagging so the panel knows the on-disk tree is larger than the released corpus.
62. Paper's SKAB-valve rubric deduction is attributed to "R4 verdict-type compliance"; the released rubric encodes it as a failing `R4_calibration` check whose payload is the allowed-set violation. Substance identical; label differs.
63. Abstract "internal consistency is machine-verified" is supported by repro_report.json (gate verdict REPRODUCIBLE); the paper itself correctly scopes this gate as internal-consistency, not independent re-execution.

## Verdict

**PASS WITH FINDINGS.**

- Numbered findings 1–60: **59 MATCH**, **0 MISMATCH**, **1 UNTRACEABLE-EXT** (finding 60, a cluster of ~10 external-literature values — FE's 7/11, 9/11, 8/11, AgentRCA 40.0%/61.5%, and four Register-B reference figures — each explicitly framed in the paper as a transcription; the Wilson intervals the paper derives from the FE fractions recompute exactly). Plus 3 informational observations (61–63) and 9 MATCH-with-note items (11, 23, 25, 27, 40, 42, 45, 48, 57) whose notes are cosmetic.
- Every headline number (Abstract, `tab:overall`, `tab:mech`, `tab:ablation`, stability, cost, case study) reproduces exactly from `results/benchmark/metrics.json`, the per-case gradings/journal, `baselines.json`, `consistency_audit.json`/`retest_selection.json`, `suite_determinism.json`/`repro_report.json`, and the released run artifacts; all Wilson CIs recompute correctly; per-stage cost medians recompute from the 13 event logs; the drawn re-execution dir spot-check (117.1 min span) is exact.
- Findings are cosmetic only: rounding/label notes (findings 11, 23, 25, 27, 62) and one tree-hygiene observation (61). No claim in the paper is contradicted by any released artifact.
