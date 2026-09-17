# Round-3 fix drafts (working notes — content to be integrated into main.tex)

> Sources: V2 (system exposition) + V4 (structure/taste) findings. All facts below are
> extracted from the real system files named in the briefing; nothing here is invented.

## A. New table — module contract (§3.2): Stage | Agent | Input | Output | Gate

| Stage | Agent (sub-skill) | Input artifact | Output artifact | Checkpoint |
|---|---|---|---|---|
| 0/1 Setup, Inspect | main agent | scenario CSV, user context | `00_input/input_manifest.json`, `user_context.json`, `run_config.json` | CP-1 |
| 2 Ontology | context-builder (`industrial-ontology-builder`) | `input_manifest.json`, RAG deep understanding (`rag_deep_understanding.json`), process description | `01_ontology/ontology.json`, `clarification_needed.json` | CP-2, CP-3 |
| 3 Statistics + features | data-processor (`industrial-data-processor`) | `ontology.json`, cleaned data | `02_processed/data_analysis_conclusion.json` (mandatory handoff), `validate_report.json`, `03_figures/*` | CP-4 |
| 3.5 Visual evidence | vlm-visual-analyzer | `03_figures/*`, `image_captions.json` (non-visual fallback) | `03_figures/visual_analysis.json` | — |
| 4 Diagnosis | diagnostician (`industrial-diagnostician`) | `data_analysis_conclusion.json` + `ontology.json` | `04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json` | CP-5 |
| 5a Judge | judge (`industrial-judge`) | `04_diagnostics/*` | `05_review/judge_feedback.json` | CP-6 |
| 5b Pre-audit ∥ | report-reviewer (`industrial-physical-auditor`, PRE_REPORT_AUDIT) | `04_diagnostics/*`, `02_processed/*` | `05_review/optimizer_preflight.md` | CP-6 |
| 6 Report | reporter (`industrial-reporter`) | all upstream artifacts | `report.md`, `run_summary.json` | CP-7 |
| 7 Final audit | report-reviewer (`industrial-physical-auditor`) | `report.md`, artifacts | `optimizer.md` containing ENDORSED | CP-8 |
| 8 HTML build | html-visualizer (`industrial-html-visualizer`) | artifacts + design system | `render_manifest.json` → `diagnostic-report.html` → `html_selfcheck.json` | — |
| 8.5 HTML review | html-reviewer (`industrial-html-reviewer`) | HTML + manifest | `05_review/html_review.json` (verdict=pass) | CP-9 |
| 9 Finalize | deterministic script | 14 artifacts | `pipeline_finalize_report.json` (overall=PASS), `evidence_closure_report.json` | — |

Contract sentence already in paper (§3.1): sub-agents communicate only through workspace
artifacts. Now it must name the artifacts (above) — that is the "artifact-only interface".

## B. New table — checkpoint predicates (§4.5 or §3.2)

| CP | Transition | Machine predicate | Failure action |
|---|---|---|---|
| CP-1 | 1→2 | `input_manifest.json` + `user_context.json` + `run_config.json` exist | back to Step 0 |
| CP-2 | 2→2.5 | `ontology.json` ≥1 KB and schema-valid | re-run ontology-builder |
| CP-3 | 2.5→3 | `clarification_status ∈ {AUTO_RESOLVED, USER_CONFIRMED}` | resolve clarification |
| CP-4 | 3→4 | `data_analysis_conclusion.json` present and plots>0 | re-run data-processor |
| CP-5 | 4→5 | 4 diagnosis JSONs schema-valid + quality check | repair diagnosis |
| CP-6 | 5→6 | `judge_repair_summary.json` + pre-audit has no FATAL | repair (best-of-3) |
| CP-7 | 6→7 | `report.md` + `run_summary.json` | re-run reporter |
| CP-8 | 7→8 | `optimizer.md` contains `ENDORSED` | repair loop |
| CP-9 | 8.5 | `diagnostic-report.html` ≥5120 B and review verdict=pass | re-run html-visualizer |

Design statement to add: every checkpoint predicate is *mechanical* — file existence,
JSON-schema validity, or a numeric lower bound — so a non-expert can re-run the gate.

## C. Formalisation block for §4 (V4 F4: the AEI method-threshold item)

Notation (compact, no invented math; each item is a real protocol rule):

- Scenario S with data window D_S; candidate hypothesis set H = {h_1..h_k}, k ≥ 3.
- Evidence levels ℓ(h) ∈ {L1..L7}; a conclusion's level is the *lowest* level in its chain:
  ℓ(h) = min over cited evidence items  (paper §4.2 already states "bounded by its lowest evidence level").
- Confidence ceiling as a function of verdict state:
  c ≤ 0.90 for DETERMINED; c ≤ 0.70 for COMPETING_SET; c ≤ 0.50 when the anti-oscillation rule fires.
- Three-state decision function (paper §4.4):
  DETERMINED iff |H_surv| = 1 and every elimination cited contradicting evidence;
  COMPETING_SET iff |H_surv| ≥ 2 and pairwise discriminant channels absent;
  NEEDS_DATA iff evidence for the surviving chain < L5 or a required channel is unmeasured.
- Four-condition anti-spurious predicate for citing a correlation as causal support (§4.3):
  temporal precedence (lag-compensated CCF) ∧ significance surviving detrending/Simpson/multiplicity
  ∧ an ontology-annotated physical mechanism ∧ no leave-one-out contradiction.

Algorithm box (Algorithm 1) — the pipeline as pseudocode (deterministic scripts vs agents
marked distinctly; the ablation §8.3 is cited as empirical support for the split):

```
Algorithm 1  IDD diagnosis run for scenario S
 1: prepare deterministically: fingerprint D_S, compute statistics, write blind brief   [script]
 2: ontology ← ontology_store.fast_reuse(S) or context-builder(S)                       [script | agent]  → CP-2/3
 3: A ← data-processor(D_S, ontology)                                                   [agent]            → CP-4
 4: H ← generate ≥3 hypotheses; for each: evidence with levels, contradictions          [agent]
 5: H_surv ← eliminate h where contradictions outweigh support                          [agent]            → verdict ∈ {DET, CS, ND}
 6: c ← min(two-factor score, ceiling(verdict)); audit c                                [agent+gates]
 7: if judge(A, H_surv) < 90: snapshot best_round; repair in scope (≤3, global ≤5)      → CP-6
 8: report ← reporter(...); audit ← physical-auditor(report) must return ENDORSED       → CP-7/8
 9: html ← html-visualizer(manifest-first); review ← html-reviewer (pass)               → CP-9
10: finalize: 14-artifact inventory + schema + closure + log ⇒ PASS, else run ungradeable [script]
```

## D. §8 restructure plan (V4 F2/F3)

- Retitle §8: "Comparison, Ablation, Stability, and an Evidence-Chain Case Study".
- Move §8.2 (Register B reference-only context) into §7.4 or trim to one paragraph (it is
  context, not comparison) → reduces §8 mass.
- Keep §8.4 stability and §8.5 case study but as clearly-labelled subsections under the new title.
- Expand §4 to carry the formalisation (Section C) and the protocol definitions (Section B).

## E. Declarations layout (V4 F1)

Order all five blocks *after* the bibliography, grouped:
CRediT → Declaration of competing interest → Funding → Data availability → GenAI declaration.
(Removes the current split placement and the half-empty last page.)

## F. 18 skills × 14 agents scoping (V2 F4)

Rewrite §3.1 sentence to distinguish the *diagnostic path* (Steps 2–8.5: 8 sub-agents /
8 skills) from the full package (18 skills × 14 agents), and add one paragraph naming the
optional layers: data-preprocessor (E0–E8 enhancement pipeline via
`industrial-analysis-enhance-auto`), deep-analysis/physics-bridge agents, RAG knowledge
builder, plus the 14-engine harness layer (`app/backend/src/harness/engines.mjs`,
`ENGINES` dispatch in `diagnosis.service.mjs`).

## G. Layer descriptions to add (V2 F5/F6/F7, V4 F4 context)

- Semantic-knowledge layer: `rag-retrieval-engine/` (FastAPI + ChromaDB, port 8764) with a
  3-second health probe; on unavailability the ontology builder falls back to
  `parameter_to_physics.json` + web search (recorded in the run dir). L6 evidence can only
  enter through this layer.
- Ontology asset store: `.claude/shared/scripts/ontology_store.mjs publish|fast-reuse` —
  schema-fingerprint matching reuses a validated ontology verbatim (deterministic, seconds).
- Web service: Express backend (:3210) + Vue 3/Vite frontend (:5180), `POST /api/diagnosis/start {harness}`,
  400 `HARNESS_UNKNOWN` / 409 `HARNESS_UNAVAILABLE`, SSE/WebSocket live stream, SQLite (WAL).
