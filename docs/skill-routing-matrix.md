# Skill Routing Matrix — intent → unique skill

> One intent, one skill. This table is derived from the **actual frontmatter descriptions** of the
> 24 skills in `.claude/skills/` (the routing contract the harness matches against) plus the backend
> specialist-intent map `ANALYSIS_INTENTS` in `app/backend/src/engine/claude-client.mjs:110-122`.
> It exists so that overlapping trigger keywords (audit / review / report / analysis / 可视化)
> resolve to exactly one skill by *artifact*, not by wording.

Columns: **intent phrase examples** (as a user would say them) → **chosen skill** → **why** (one line).

## 1. HTML family — 5-way split (build vs review × plain vs enhanced, plus the standalone builder)

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| "生成诊断 HTML 页面", "build the diagnostic report page" (inside a pipeline run, CP-8 ENDORSED) | `industrial-html-visualizer` | Pipeline Step 8 builder: writes `render_manifest.json` first, assembles the page from the diagnostic-html-visualizer design system, then `html_selfcheck.json` (8 items). Requires `optimizer.md` ENDORSED — it never builds without the gate. |
| "HTML 审计", "review the built page", "页面评审" (after Step 8) | `industrial-html-reviewer` | Pipeline Step 8.5 independent reviewer: six objectives + 15-item red-line blacklist, cross-checks page against `render_manifest.json`/`html_selfcheck.json`, outputs `html_review.json`. Never trusts the builder's self-declared quality. |
| "增强 HTML", "enhanced visualization page" (after E0-E8) | `industrial-enhanced-html-visualizer` | E7b of the enhancement chain: builds `enhanced-analysis.html` with 5 chart types from `enhanced_knowledge.json` (CDN multi-source fallback + runtime self-check). |
| "enhanced HTML review", "增强页面复审" (after E7b) | `industrial-enhanced-html-reviewer` | E7c: reviews `enhanced-analysis.html` against `enhanced_knowledge.json` → `enhancement_html_review.json` (pass/warn/fail + 0-100 score). |
| "visualize this run folder", "把结果目录做成给操作员看的页面" (standalone, no pipeline context) | `diagnostic-html-visualizer` | Standalone run-folder → explainer page generator and the design-system source that the pipeline visualizer reuses; triggers when a folder contains `report.md` / `diagnosis.json` / `3d_model_data.json` but no pipeline Step-8 contract is needed. |

Build-vs-review rule: **builders write the page, reviewers write `*_review.json`**; a reviewer is never
dispatched to improve a page and a builder is never dispatched to bless one.
Plain-vs-enhanced rule: plain pages come from diagnostic artifacts (`04_diagnostics/**`), enhanced pages
come from the enhancement layer (`enhancement/enhanced_knowledge.json`).

## 2. Judge vs physical auditor (quality scoring vs physical truth)

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| "质量门禁", "给诊断结果打分", "judge this run", repair-loop routing | `industrial-judge` | 10-criterion integrity scoring of diagnostic artifacts (reasoning + statistics + schema), outputs `judge_feedback.json` with verdict + `repair_instructions`; gates the Reporter (score ≥ 90). |
| "物理审计", "physical-truth audit", pre-report audit / final ENDORSED verdict | `industrial-physical-auditor` | Independent physical audit tracing every causal chain back to its governing equation: PRE_REPORT_AUDIT → `optimizer_preflight.md` (parallel with the Judge), FINAL_AUDIT → `optimizer.md` ENDORSED/CONDITIONAL/REJECTED. |

Rule of thumb: **Judge scores how well the artifacts are built; the auditor checks whether the physics
is true.** The Judge never re-derives mechanisms; the auditor never issues repair instructions.

## 3. `industrial-analysis-auto` vs the six specialist analysis intents

The backend routes `POST /api/diagnosis/start { analysisIntent }` (`claude-client.mjs:110-122`):

| Intent phrase examples | Chosen skill (intent) | Why |
|---|---|---|
| "完整诊断", "root cause from raw data", default run | `industrial-analysis-auto` (`deep-diagnosis`, default) | The 9-stage orchestrator from raw sensor/process data to `report.md` + `diagnostic-report.html`; its sub-skills (ontology-builder → data-processor → diagnostician → judge → auditor → reporter → HTML) are dispatched **by it** — never chosen in its place. |
| "只做根因诊断", "engine-only diagnosis" on a run that already has `data_analysis_conclusion.json` | `industrial-diagnostician` | Single-purpose competing-hypotheses engine; consumes upstream artifacts and refuses to start without the mandatory handoff. |
| "产线稳不稳定", "稳定性报告", line stability report | `industrial-line-stability-report` (`stability-report`) | 0-100 scoring (A≥85/B≥70/C≥50/D<50) + Chinese HTML landing page; honest `not_assessable` instead of fabricating. |
| "产线监控", "快筛", "watch mode", SPC/Nelson alerting | `industrial-sentinel` (`quick-screen`) | Pure-analysis standing watch; batch (1k-100k rows) + incremental (1-500 rows) screening against a frozen baseline; emits alerts/reports only. |
| "DOE", "试验数据分析", "操作窗口", factorial/RSM/ANOVA | `industrial-doe-analyzer` (`doe-analysis`) | Standalone deterministic effect/ANOVA/RSM engine + observational mode; key artifact `conclusions/recommendations.json`. |
| "调优经验库", "动作归因", "上次调参有没有效果" | `industrial-tuning-memory` (`experience-mining`) | Action→effect attribution + local experience store (E0-E3 advisory) + playbook retrieval; never dispatches parameters. |
| "闭环寻优", "参数寻优 campaign", DMTA rounds | `industrial-optimizer-loop` (`optimizer-campaign`) | Session round state machine (init → design → ingest → converge) producing trial DESIGN artifacts only. |

The boundary between row 1 and rows 2-7: `analysis-auto` runs a **pipeline**; the specialists run
**one deterministic analysis intent**. An `analysisIntent` directive supersedes the 9-stage flow
(`claude-client.mjs:133-152`).

## 4. DOE analyzer vs data-processor vs optimizer-loop

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| designed experiment (factorial/CCD/BBD/LHS/orthogonal), "试验数据分析", operating windows | `industrial-doe-analyzer` | Auto-detects the design, runs extra-SS ANOVA + BH-FDR + RSM/desirability; zero-LLM scripts with a deterministic gate; standalone (NOT a pipeline stage). |
| "统计一下这些数据", cleaning, Simpson/correlation/CCF, charts — Step 3 of the diagnosis pipeline | `industrial-data-processor` | Ontology-guided statistical analysis + visualization charts; mandatory handoff `data_analysis_conclusion.json` to the diagnostician. |
| "布点试验", "收敛试验", multi-round target seeking | `industrial-optimizer-loop` | DMTA round machine: designs each new round (seeded from doe-analyzer priors via `window_seed` / `lhs_fill` / `gp_ei` …) and converges with a dual gate (m≥3 confirm replicates + 95% CI in limits + D≥0.8·D_max). |

One-liners: **data-processor = statistics inside the pipeline; doe-analyzer = one-shot experiment /
condition analysis outside it; optimizer-loop = the multi-round campaign that consumes both** (doe
priors for seeding, replicate statistics for convergence).

## 5. Sentinel vs line-stability-report vs tuning-memory

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| "实时监控", incremental screening, alert/告警 | `industrial-sentinel` | Standing watch over rolling windows: SPC + drift projection + regime mapping + anti-alert-storm trio; fast-screen ≤ 5s per increment. |
| "产线运行情况报告", "给老板看产线报告", periodic stability score | `industrial-line-stability-report` | Period-scoped scoring report that *consumes* sentinel (baseline), tuning-memory (attribution) and doe-analyzer (windows) as cooperative inputs; the only skill that emits the graded Chinese HTML landing page. |
| "经验入库", "这个动作有效吗", playbook retrieval, 调优经验 | `industrial-tuning-memory` | Action→effect attribution (Welch + AR(1) correction) into a local experience store with E0-E3 grades and fault-signature playbook search. |

One-liners: **sentinel watches now, line-stability scores a period, tuning-memory judges actions.**

## 6. data-preprocessor vs data-processor vs hetero-preprocessor

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| "多格式数据", xlsm multi-sheet, a directory of mixed exports, "预处理" | `industrial-data-preprocessor` (stage E-1) | The only format-adaptation stage: any file/directory → canonical `preprocessed_data.csv` + audit report + context files; never computes statistics. |
| "统计分析", "画图", correlation/CCF/Simpson — on already-canonical data | `industrial-data-processor` (Step 3) | Statistical engine + charts under ontology guidance; not a format adapter. |
| 剖面/膜厚剖面, 2D field/温度场, image sequence/WAXS, 操作备注/交接班 | `industrial-hetero-preprocessor` (stage E-1H) | Projects the four non-scalar shapes (PROF/MAP/IMG/TXT) into deterministic `HX-*` scalar features anchored to the canonical time axis; runs chained immediately after E-1 in Step 0.5. |

## 7. Enhancement chain — deep-analysis vs physics-bridge vs enhance-auto

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| coverage matrix / derived features / conditional analysis / tradeoffs (E1-E4) | `industrial-deep-analysis` | Deterministic E1-E4 layer writing `analysis_coverage.json`, `derived_features.json`, `deep_data_analysis.json`, `association_graph.json` under `RUN_DIR/enhancement/`. |
| "物理机理桥接", mechanism verification of statistical relations (E5) | `industrial-physics-bridge` | Validates statistical relationships as physical causal chains → `physics_bridge.json`; records evidence gaps. |
| "跑增强流水线", E0-E8 in one call | `industrial-analysis-enhance-auto` | The orchestrator (E0 readiness → … → E8 finalization, plus Mode A: new data through baseline + enhancement); single layers are not its job. |

## 8. Ontology / knowledge base

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| pipeline `01_ontology/ontology.json` for a diagnosis run (industrial, data-coupled) | `industrial-ontology-builder` | Pipeline Step 2 engine: RAG + data self-description → `ontology.json` + clarification gate; depends on `rag-knowledge-builder` for the underlying knowledge-base construction. |
| "build a knowledge base", build/design/extend a domain ontology (any domain, ChromaDB + web) | `rag-knowledge-builder` | Domain-agnostic KB construction: `rag_ontology_draft.json` + NL spec + structured data + scored chunks + audit log into `<run_dir>/00_input/`; consumer-call or standalone. |

## 9. Meta

| Intent phrase examples | Chosen skill | Why |
|---|---|---|
| skill fitness, 技能评分演变, "did this skill get better?" | `darwin-skill` | Internal OMP meta-skill tracking skill scores over time in `results.tsv` (validated by `scripts/quality_gate.mjs`); no industrial analysis. |

## Boundary gaps (residual ambiguity, deliberately documented)

1. **`industrial-data-processor` lacks a reverse-format clause.** Its description says "Do NOT use for
   general data analysis" but does not say "Do NOT use for format adaptation (use
   industrial-data-preprocessor)". A user pasting a multi-sheet xlsm may still match *data-processor*
   first. Mitigated by the E-1 clause added today and by this matrix; the data-processor frontmatter
   itself was owned by a different wave and was not restructured.
2. **Bare "audit the diagnosis" matches both judge and physical-auditor keywords** ("audit",
   "review" live in both descriptions). Resolved by artifact: pre-report artifact scoring →
   judge; physical-truth verdict on `report.md` → physical-auditor. The two run in parallel by design
   in Step 5a/5b, so a joint dispatch is correct only for a full pipeline run, never for a one-off ask.
3. **`diagnostic-html-visualizer` vs `industrial-html-visualizer`** both match "generate HTML from a
   run folder". Inside a pipeline run (CP-8 ENDORSED present) the pipeline builder wins because it
   owns the Step-8 contract; the standalone builder is for run folders outside pipeline control.
4. **Sentinel settle/视界 thresholds are not documented in the skill** (grep found no such constants);
   only the documented minimums in §"Input contract" apply (1k-100k watch window, 1-500 fast-screen,
   ≥100 steady rows for a self-baseline). If a settle/horizon policy exists, it lives in code-only
   constants — worth a doc line in a future wave.
5. **`industrial-tuning-memory` "fault signature" trigger** overlaps fault-analysis phrasing that
   otherwise routes to `industrial-diagnostician`. Resolved by input: an action/parameter-change log
   → tuning-memory; sensor/process data without actions → diagnostician.
