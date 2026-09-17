# Round 3 — Reviewer Briefing (multi-reviewer blind review)

> Purpose: independent review of the current manuscript against AEI expectations with four
> distinct mandates. Reviewers are read-only; they must ground every finding in a file,
> page, or command output. No file may be modified.

## Manuscript

- LaTeX source: `paper/main.tex` (elsarticle, `\journal{Advanced Engineering Informatics}`)
- Compiled PDF: `paper/main.pdf` — **77 pp** (review mode: double spacing + line numbers), 0 errors, 0 undefined refs. Note: the stability section (§6.4) and Discussion now report the audited retest outcome — within-era agreement 15/16 with the tep_d11 verdict-state divergence disclosed; re-verify against the artifacts below if reviewing that claim.
- Bibliography: `paper/refs.bib`
- Rendered pages (130 dpi PNG) for figure/table inspection: `paper/pagepng/rev_p{8,9,10,11,24,25,28,29,32,33,35,37,38,55}.png`
  — regenerate any other page with: `cd paper && pdftoppm -png -r 130 -f N -l N main.pdf pagepng/rev_pN`
- Figures (vector sources + 220 dpi previews): `paper/figures/fig_{benchmark,calibration,tep,forest,suite_matrix}.{pdf,png}`
- Highlights: `paper/highlights.md`; supplementary transcription: `paper/supplementary_fe_table1_transcription.md`
- Prior review trail: `paper/review/` (round1 roadmap, response_to_reviewers.md, round2_external_review_and_fixes.md)

## Ground-truth artifacts for consistency checks (all machine-readable)

| Artifact | Content |
|---|---|
| `results/benchmark/metrics.json` | executed 12/12, Top-1 6/9, top-k 8/9, calibrated 8, control 3/3, false alarms 0, mean rubric 97.9, judge mean 93.08, Wilson CIs |
| `results/benchmark/rubric.json` | per-scenario R1–R7: 10×100, tep_d11=90 (R6), skab_valve1_1=85 (R4) |
| `results/benchmark/gradings/*.json` | per-scenario verdict type, top1/topk, confidence, judge score, run_dir provenance |
| `results/benchmark/baselines.json` | same-model bare LLM 9/9 strict; FE-style 6/6; controls 2/2 zero false alarms; classical PCA detection rates |
| `results/benchmark/stability_report.json` | era-aware within-version agreement 15/16 (era boundary 20260914), 41 run dirs; the 1 unstable pair is tep_d11 v2 (type flip DETERMINED→COMPETING_SET, same tag/class/top mechanism) |
| `results/benchmark/consistency_audit.json` | random-draw retest audit: divergent 1 (tep_d11), within-era 3/4 (2 consistent, 1 weak), insufficient_runs 8 |
| `results/benchmark/retest_selection.json` | five seeded mulberry32 draws (rounds 2–4 drew tep_d11; that retest executed 2026-09-17 and is audited); round 5: seed 368776031, u=0.131221641, skab_cavitation_13 — fresh-run contract outstanding |
| `results/benchmark/suite_determinism.json` | suite re-run diff verdict: DETERMINISTIC (45/45 byte-identical) |
| `results/benchmark/repro_report.json` | reproducibility gate: REPRODUCIBLE, dataset integrity 153/153 |
| `results/benchmark/benchmark_report_en.md` / `.html` | **English benchmark report** (12 sections + Appendix A ground truth) |
| `results/benchmark/report.md`, `experience/benchmark-report.html` | scoring report + HTML |
| `workspace/diagnostic-runs/<ts>_bench_<case>/` | real run dirs: agent-authored artifacts (`04_diagnostics/*.json`, `report.md`, `diagnostic-report.html`, `optimizer.md`), `.pipeline_events.jsonl` event logs |

Useful commands (Git Bash, run from repo root):

```bash
node -e "const m=require('./results/benchmark/metrics.json');console.log(m.top1,m.topk,m.mean_rubric,m.calibrated)"
node scripts/benchmark/verify-repro.mjs --tier scripts/benchmark/cases/benchmark_cases.json
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs workspace/diagnostic-runs/<dir>
pdftotext -layout paper/main.pdf - | head -100
```

## The system the paper must explain (for the "system exposition" mandate)

- `AGENTS.md` — project overview: 9-stage pipeline, 18 skills × 14 agents, harness mirrors, 14 execution engines, directory conventions, evidence levels L1–L7.
- `docs/benchmark/` — protocol docs (README, design, execution-guide, reproduction-guide, benchmark-pipeline-runbook, baseline-suite-pipeline).
- `.claude/skills/industrial-analysis-auto/SKILL.md` — the orchestrator skill (checkpoints CP-1…CP-9, repair loop, anti-oscillation rules).
- `.claude/skills/industrial-{ontology-builder,data-processor,diagnostician,judge,physical-auditor,reporter,html-visualizer,html-reviewer}/SKILL.md` — per-stage skills.
- `app/backend/src/harness/engines.mjs` — 14 execution engines behind one event contract; `app/backend/src/services/diagnosis.service.mjs` — unified dispatch.
- `baselines/baseline-suite/` (Nuxt replication: classical PCA / FE protocol / bare-LLM) and `baselines/FaultExplainer/` (vendored upstream).
- `scripts/benchmark/zcode_direct_pipeline.mjs` (prepare/verify/grade), `run-tier.mjs` (stage orchestration), `run-benchmark.mjs` (S0–S6), `run-benchmark-pipeline.mjs` (four-step runbook).

## Mandates (one per reviewer)

- **V1 — Figures & tables.** Check every figure and table on its rendered page: legibility at print size; colour-blind safety; caption self-sufficiency; whether the visual actually carries the intended message; redundancy between figures and tables; whether standard AEI system-paper figure types are missing (e.g. module/cooperation view, artifact-flow contract view, case-study evidence-chain view). Report per-figure findings with page + evidence.
- **V2 — System exposition.** Judge whether the paper explains the project well enough for an AEI reader: architecture, every module's function, how modules cooperate (inputs/outputs/handoffs), and the design rationale for the choices. Cross-check against the real system docs listed above; name concrete missing descriptions and where they belong.
- **V3 — Benchmark consistency.** Verify paper claims against the artifact table above: every number, table, and figure cell; verdict types; confidence values; ablation counts; claims about the evaluation framework. Report every mismatch (paper vs artifact) or unverifiable claim.
- **V4 — AEI structure, layout and taste.** Compare the manuscript's structure/balance/figure density/appendix/readability with typical AEI systems papers; check abstract/highlights/keywords, section order, length, and whether the paper reads like an AEI article. Recommend concrete structural/layout changes.

## Output format (all reviewers)

1. Overall assessment (3–5 sentences).
2. Numbered findings — each: severity (Critical/Major/Minor), exact location (page/section/表/figure/line quote), evidence (file, command output, or page image), concrete suggested fix.
3. A "must-fix before acceptance" shortlist.
4. Verdict: publishable as-is / minor revision / major revision + one-paragraph justification.
