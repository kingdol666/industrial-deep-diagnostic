# Supplementary Artifact Layer — Build Manifest (round41)

The Data Availability statement promises "the complete evaluation artifact layer … as
supplementary material". This manifest defines exactly what that layer contains and how to
build it. Total size of the 13 canonical run directories: **≈59 MB** (zips to well under
Elsevier supplementary limits).

## Inventory

1. **run_dirs/** — exactly the thirteen canonical run directories (the recorded 2026-09-17
   batch plus the drawn re-execution 202609172247007). The interrupted 2026-09-18 batch is
   EXCLUDED per the data statement (exclusion is chronological, not selective):
   - 202609171630389_bench_skab_valve1_1
   - 202609171630579_bench_skab_cavitation_13
   - 202609171631116_bench_skab_normal_control
   - 202609171632332_bench_tep_d01_ac_feed_ratio
   - 202609171632563_bench_tep_d03_hard
   - 202609171633136_bench_tep_d00_normal_control
   - 202609171633340_bench_indpensim_batch093
   - 202609171636045_bench_indpensim_batch001_control
   - 202609171639066_bench_tep_d04_reactor_cooling_step
   - 202609171639214_bench_tep_d07_header_pressure
   - 202609171639527_bench_tep_d11_reactor_cooling_random
   - 202609171640072_bench_tep_d14_reactor_valve_sticking
   - 202609172247007_bench_tep_d11_reactor_cooling_random
   Each contains: 00_input (blind briefs + user context), 01_ontology, 02_processed
   (data_analysis_conclusion.json etc.), 03_figures, 04_diagnostics (diagnosis.json, evidence,
   confidence, reasoning chains), 05_review (judge_feedback.json; for tep_d03 additionally
   judge_feedback_round1.json), report.md, run_summary.json, diagnostic-report.html,
   .pipeline_events.jsonl.

2. **results_benchmark/** — the full evaluation layer:
   README-artifact-fields.md, rubric.json, metrics.json, baselines.json,
   baselines_input_audit.json (12 brief SHA-256 fingerprints), suite_determinism.json,
   consistency_audit.json, retest_selection.json (seed + draw), repro_report.json (153/153
   fingerprint re-verification), benchmark_report_en.md, dataset_manifest.json,
   baseline_pca_rca.json, tier_state.json, report.md.

3. **scripts/** — the aggregation / verification / report scripts the statement names:
   - baseline-lab/scripts/verify-fe.mjs (the FE-replication 21-check verification gate;
     §7.3/§8.3's "passes all 21 checks" claim — T² max rel. err 2.8e-12)
   - scripts/benchmark/: run-tier.mjs, judge-rubric.mjs, aggregate.mjs, verify-repro.mjs,
     select-retest-case.mjs, consistency-audit.mjs, build-english-benchmark-report.mjs,
     run-benchmark-pipeline.mjs, benchmark_cases.json (frozen scenario definitions; grading
     keyword sets pinned at commit 221d061)

4. **supplementary_fe_table1_transcription.md** — the double-checked FE Table-1 transcription
   (only the 6 verified rows), cited from the per-fault appendix table.

5. **figure_sources/** (added round44) — the figure sources the Fig. 1 / Fig. 2 captions
   promise as "released with the paper": both drawio diagrams
   (fig_architecture.drawio, fig_pipeline.drawio), the HTML/CSS sources of the ten data
   figures (fig_*.html + aei_template.css), and the render chain that produces the
   manuscript PNGs from these sources (drawio_render.py, render_all.sh, trim_white.py).

## Build

Run `python build_supplementary.py` from the repository root (script in this directory).
Output: `paper/submission/supplementary_artifact_layer.zip` (strips `.mimosa` scratch
directories, which are tool residue, not artifacts).

## Notes

- The GitHub repository ships the SOURCE (harness + system); the artifact layer ships HERE.
  This split is exactly what the Data Availability statement declares.
- Zenodo DOI: mint on acceptance (declared in the statement); deposit = this zip + the
  pinned commit hash.
- Third-party datasets (SKAB, TEP/rieth2017, IndPenSim) are NOT redistributed in full inside
  run directories beyond the brief excerpts each scenario needs; they are available from their
  cited sources (statement: "Third-party datasets are publicly available from their cited
  sources").
