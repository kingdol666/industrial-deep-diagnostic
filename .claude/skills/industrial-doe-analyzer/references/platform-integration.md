# Platform integration — IDD ⇄ AgentWorkShop

How a real platform capture becomes a DOE answer, what is guaranteed by IDD, and which
platform-side gaps remain. This page is written against AgentWorkShop v0.7.66 and IDD
`feat/doe-ontology-first` (contracts v1.1).

## 1. Two integration surfaces

| Surface | Endpoint | Use |
|---|---|---|
| Internal task API (diag-bridge uses this) | `POST /api/diagnosis/tasks` → `GET /api/diagnosis/tasks/:id` | The platform submits `dataPath` / `dataPaths` / `folderPath`, `sceneName`, `userQuestion`, `harness`, `analysisIntent`, ontology fields; the backend runs a real agent and returns a task view |
| External integration API | `POST /api/external/v1/analyze` → `GET /api/external/v1/tasks/:id/result` | Token-authenticated sibling used by non-AgentWorkShop callers; same intents and result shape |

Both create the same diagnosis run and both return the **same artifact manifest** (see §5), so a
result is retrievable regardless of which door was used.

## 2. Analysis intents (scenario → skill)

`analysisIntent` is not a label: it re-points the run at one skill protocol. IDD validates it
strictly (unknown → 400 `ANALYSIS_INTENT_UNKNOWN`, never a silent fallback).

| Intent | Skill | Deterministic core | Output |
|---|---|---|---|
| `deep-diagnosis` (default) | `industrial-analysis-auto` | 9-stage pipeline | root cause + evidence |
| `stability-report` | `industrial-line-stability-report` | `stability_analyzer.py` + `report_builder.py` | score/grade + HTML |
| `quick-screen` | `industrial-sentinel` | `sentinel.py watch` + `build_screen_report.py` | alert.json + HTML |
| `doe-analysis` | `industrial-doe-analyzer` + `industrial-doe-orchestrator` | ontology prepare → analyze → gate | effects/joint setpoints/next design + HTML |
| `experience-mining` | `industrial-tuning-memory` | tune_stats attribution | experience entries |
| `optimizer-campaign` | `industrial-optimizer-loop` | campaign state machine | trial design / recommendation |

The agent receives an `Analysis Intent Directive` that forbids the default pipeline and binds the
skill. For `doe-analysis` it also receives the **DOE Ontology Directive**: run
`doe_ontology_prepare.py`, read `ontology_brief.json`, write `01_profile/analysis_plan.md`, then
run the analyzer. Missing brief/plan is a hard gate (`ONTOLOGY_BRIEF_REQUIRED` /
`ANALYSIS_PLAN_REQUIRED`); `mode=off` is refused in production.

## 3. What the platform sends

AgentWorkShop's `diag_run` has three data sources:

1. `line` + time window → a 5-second snapshot CSV (`timestamp,<nodeId>…`).
2. `data_path` → an existing IDD-side file.
3. `export_id` → a DAQ export dataset (`manifest.json` + one full-rate CSV per node). The bridge
   uploads every file; IDD runs in `multi` mode. This is still **time series**, not a run table.

For DOE the platform must send a **run-level table**: one row per execution, columns = design
factors + responses. Today that assembly happens in IDD's capture adapter:

```
runs/<run_id>/manifest.json + nodes/*.csv   ─┐
trial_design.csv (factor setpoints)          ├─ aws_capture.py build ─→ run_table.csv
qc_measurements.csv (lab responses)          │                          doe_context.json
hetero_features.csv (E-1H, optional)        ─┘
                                                      │
                                                      ▼
                                            doe_context_adapter.py → analysis_context.json
```

`pivot` produces the wide time-series table sentinel/stability need from the same export.

### Ontology parameters

| Field | Values | Default |
|---|---|---|
| `ontologyMode` | `auto` / `full` / `reuse` / `extend` (DOE namespace) | `auto` |
| `ontologyScene` | scene key (e.g. `bopet-lineA-12um-tdo`) | from `doe_context.ontology.scene_key` |
| `ontologySource` | store asset path (reuse/extend) | from the store lookup |
| `ontologyDataStage` | `design_only` / `collected` | inferred from measured responses |
| `ontologyDevOverride` | `true` only for an audited debug run | absent (production refuses `off`) |

The store key is `profile + scene_key + context_fp` (columns/dtypes/units/ranges/specs/design
region/blocks/covariates/data stage). An exact hit reuses in ≤60 s; a changed context extends;
otherwise the builder creates a new version from prior knowledge + data.

## 4. What IDD returns

A completed run writes:

```
01_ontology/ontology.json, ontology_brief.json/.md, ontology_coverage.json
01_profile/data_profile.json, analysis_plan.md
02_analysis/effect_table.json, model.json, association_screen.json, ontology_consistency.json
conclusions/doe_conclusion.json, recommendations.json, next_design.json, optimization_guidance.json
report.html
artifact_manifest.json
```

`recommendations.json` v1.1 is the downstream contract:

- `joint_setpoints[]` — the **only executable carrier**; each carries factor values, predicted
  responses with `mean_ci95`/`pi95`/`d`, desirability, feasibility and hard-constraint violations.
- `operating_windows[]` — per-factor marginal diagnostics (`window_role=marginal_diagnostic`);
  never execute a midpoint from this list without checking the joint point.
- `units`, `design_region`, `grid_plan`, `factor_response_matrix`, `actionable_summary`.

`optimization_guidance.json` turns the joint point into platform actions:

- `recipe_patch[]` — `{factor, from, to, unit, platform_ref, hard_limits, within_limits,
  actionable, blockers}`. A factor without `platform_ref` is removed and disclosed
  (`platform_ref_missing`), never fabricated.
- `node_setpoints[]` — expected response setpoints for platform metrics.
- `next_design.json` — confirm / augment / space-filling runs with executable settings.

## 5. Artifact retrieval (the retrieval contract)

IDD writes `artifact_manifest.json` with `{kind, path, url, sha256, schema_version, bytes}` for
every artifact (15 kinds: ontology, brief, coverage, feedback, consistency, profile, plan, effect
table, model, association screen, conclusion, recommendations, next design, guidance, report).
The backend exposes the same manifest on both `GET /api/diagnosis/tasks/:id` and
`GET /api/external/v1/tasks/:id/result` — one source of truth (`artifact-manifest.service.mjs`).
The manifest is the retrieval index: fetch by `kind`, verify by `sha256`, never scrape the run
directory.

`GET /api/external/v1/tasks/:id/result` also returns the stored result including `report_md_path`,
HTML paths and the artifact list. Large JSON stays behind file paths/URLs; it is not truncated
into a chat message.

## 6. AgentWorkShop bridge status (verified 2026-10-17)

Working:

- `analysis_intent` is passed to IDD; the six intents and their skill names match IDD's catalog
  (routing check: 20/20 IDD checks; AWS skill alignment 5/5).
- `export_id` uploads the full dataset, `dataPaths` runs in multi mode, `sync` polls to terminal.
- Completion callback/`diag_status` reaches the requesting agent/channel; `kb_agent` can ingest
  the report.

Known platform-side gaps (not blocking IDD's execution, but they must be fixed for a first-class
DOE loop):

1. **P0 — default question override.** In `diag-bridge/host/plugin.mjs`, `diag_run` fills
   “深度根因诊断” whenever `question` is absent, before `startDiagnosis` can use
   `defaultQuestionFor(intent)`. The per-intent template is therefore unreachable on that path.
   IDD's intent directive still binds the skill, but the business question is wrong. Fix: only
   synthesize the deep-diagnosis question when the resolved intent is `deep-diagnosis`, otherwise
   use `defaultQuestionFor(intent, …)` (both the project and builtin copies).
2. **No run-level export.** DAQ exports are per-node time series with no per-sample `run_id`,
   factor columns or responses. The platform needs a run-scoped export (one row per execution) or
   must keep using the capture adapter.
3. **No DOE ingestion.** `diag_status` returns text + `report_md_path`; it does not pull the
   artifact manifest or `recommendations.json`. Add an idempotent outbox keyed on
   `(diag_run_id, kind, sha256)`.
4. **No DOE entity/UI.** The platform schema has no experiment/factor/response/trial tables, so a
   campaign cannot be assembled or reviewed there yet.
5. **E-1H timestamp format.** E-1H's time catalog does not parse `…T08:03:50.000Z`; normalize
   timestamps on the way into `industrial-hetero-preprocessor` (the capture adapter's prepared
   hetero tables already do).

## 7. End-to-end sequence (tested)

```
AgentWorkShop capture (history / line / campaign exports)
  │
  ├─ aws_capture.py pivot ──────────────→ sentinel watch ──→ alert.json ──→ quick-screen HTML
  │                                        (C2 uses DOE windows if present)
  │
  ├─ E-1H profiles/notes ──→ HX-* features ─┐
  │                                          ▼
  └─ aws_capture.py build ──→ run_table + doe_context
                                     │
                                     ▼
                    doe_ontology_prepare (build/reuse) ──→ ontology_brief
                                     │
                                     ▼
                    analysis_plan.md ──→ analyze.py all ──→ G1-G11
                                     │
                                     ├─ recommendations → joint_setpoints
                                     ├─ optimization_guidance → recipe_patch
                                     ├─ next_design
                                     └─ report.html
                                     │
                                     ▼
                    stability_analyzer (ontology + sentinel baseline + DOE windows)
                                     ▼
                    line_stability_report.html
```

## 8. Limits and safety

- All IDD analysis is deterministic (numpy/scipy/pandas); the agent interprets, it does not
  compute. The gate blocks bad artifacts.
- IDD never dispatches parameters. `recipe_patch`/`node_setpoints` are **recommendations**;
  the platform applies them through its recipe + HITL + four-layer limits.
- Entity resolutions (`platform_ref`) are mandatory for an executable handoff; without them the
  analysis is offline-only and says so.
- Evidence levels: designed effects are causal-grade (L3); observational associations are
  correlation-grade and never enter a window (`causal_claim: none`).
- The external API is token-authenticated; the internal task API is intended for the local
  AgentWorkShop bridge. Data paths are validated inside the project root.
