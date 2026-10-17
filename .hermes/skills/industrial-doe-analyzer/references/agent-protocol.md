# DOE Analyst — Agent Protocol (Phase 0-6)

Execution checklist for the `doe-analyst` agent. All statistics are computed by
`scripts/analyze.py`; you never hand-compute, never edit computed numbers, and
never raise the evidence grade. Python always runs through uv from the repo root:

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/analyze.py" ...
```

## Phase 0 — Context & Manifest

0. **Scope the run against the ontology FIRST (DOE v1.1, hard gate).**
   If `00_input/doe_context.json` exists, materialise the canonical context:
   ```bash
   uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/doe_context_adapter.py" \
     --run-dir "$RUN_DIR" [--context <doe_context.json>] [--data <run_table.csv>]
   ```
   It rejects `MISSING_COLUMN` / `DUPLICATE_RUN_ID` / `MISSING_RUN_TABLE` / `NO_RUN_TABLE`
   explicitly — never "fix" that by pointing at another file. It writes
   `00_input/analysis_context.json` with `provenance.assigned_by` per field.
   Then, whenever `analysis_context.ontology.mode != "off"`:
   ```bash
   uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/doe_ontology_prepare.py" \
     --run-dir "$RUN_DIR" --mode auto
   ```
   `auto` = store lookup by `profile=doe` + `scene_key` + `context_fp` → reuse /
   extend / build. It writes `01_ontology/{ontology.json,ontology_brief.json,
   ontology_brief.md,ontology_coverage.json}`.
   **Read `01_ontology/ontology_brief.md` and write `01_profile/analysis_plan.md`**
   (scene / factors / responses / units / expected directions / confounders /
   limitations / analysis mode). Without it `profile` exits
   `ANALYSIS_PLAN_REQUIRED`; without the brief it exits `ONTOLOGY_BRIEF_REQUIRED`.
   `data_stage=design_only` (response columns empty) allows only
   `ontology` / `profile` / `build`; statistics exit `DESIGN_ONLY_NO_RESPONSE`.

1. `RUN_DIR/run_manifest.json` — created automatically by `analyze.py profile`.
2. `RUN_DIR/00_input/analysis_context.json` — read if present (user-authored);
   otherwise it is auto-inferred on first `profile` run with every inferred field
   marked `inference.assigned_by: "auto"`.
3. Review the inference: fix only FACTUAL mistakes (wrong response column, wrong
   factor typing, missing spec limits the user stated in the prompt). Spec
   limits/goals (lsl/usl/target/goal/weight) materially change the windows —
   set them whenever the user provided them. Append each fix to
   `analysis_context.json` → `inference.notes` as
   `fix: <field> <before>→<after> (source: user prompt)`.

   **After editing analysis_context.json you MUST re-run the Phase 1 profile
   command before Phase 2 — the designed path's `run` consumes `data_profile.json`
   roles, not the raw context; a fix without a profile re-run has no effect.**
   (Observational reads responses directly from the context — different data sources.)
4. Log `agent_start` AFTER the first `profile` run created `run_manifest.json`
   (append-pipeline-event.mjs exits 1 without it):
   `node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_start --agent doe-analyst --step doe_analysis`

## Phase 1 — Profile & Mode Dispatch

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/analyze.py" profile --run-dir "$RUN_DIR"
```

- Read `01_profile/data_profile.json`: design detection (`design_type`,
  resolution, generators, alias chains, balance), caveats, quality.
- If you disagree with the mode, set `mode_override` in analysis_context.json
  and re-run profile. **Override changes the mode, never the evidence grade**
  (`overridden_by: "user"` is recorded; grade stays checklist-computed).

## Phase 2 — Deterministic Analysis

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/analyze.py" run --run-dir "$RUN_DIR"
```

- designed → `effect_table.json` (v1.1: `effect_ci95`, `std_effect`, `term_unit`,
  `interval_semantics`, `response_units`) + `model.json` (+ RSM stationary points,
  design hull, leverage)
- observational → `correlation_report.json` + `stability_report.json`
- both → figures + `plot_manifest.json` + `doe_conclusion.json` /
  `recommendations.json` (contract v1.1: `units`, `design_region`, `joint_windows`,
  `joint_setpoints`, `factor_response_matrix`, `grid_plan`, `interval_disclosure`,
  `actionable_summary`, `*_ref`), plus `02_analysis/association_screen.json`,
  `conclusions/next_design.json`, `conclusions/optimization_guidance.json`, and
  `artifact_manifest.json` (the artifact registry both APIs read).
- **Four interval types are distinct**: `mean_ci95` (mean response), `pi95` (a single
  future observation — always wider), `effect_ci95` (the coefficient), and
  `tolerance_interval_95_95`. Never present `pi95` as a pass/yield rate.
- **Marginal windows are diagnostic only.** `operating_windows[].window_role` is
  always `marginal_diagnostic`; executability is carried by `joint_setpoints[]`
  (`actionable` + `blockers`). Units missing or conflicting, a hard-constraint
  violation, extrapolation outside the design hull, or an unsatisfied spec-bearing
  response all set `actionable=false` — the window is kept, execution is blocked.
- Read every artifact. Script warnings (`reason_code`, caveats, drift flags)
  are load-bearing — carry them into the report, never delete them.

## Phase 3 — Interpretation (enrich the conclusion)

- Do NOT add new top-level keys to either conclusions file — G6b runs a strict
  extra-keys check and will FAIL. Enrich only existing fields.
- Rewrite `key_findings[].statement` in precise Chinese grounded in the
  computed numbers (keep ids, evidence_refs, confidence, fdr_q untouched).
- Add business-context limitations the scripts cannot see (units, physical
  constraints, upstream process knowledge from the user prompt).
- Flip `authored_by` to `"agent"` ONLY after your edits. Computed numbers stay
  byte-identical.

## Phase 4 — Recommendations Enrichment

- Review `recommendations.json`: fill `conflicts[].resolution` notes,
  `current_baseline.move_instruction` phrasing, and `watchlist` additions ONLY
  where the script left them empty for lack of information.
- NEVER set `confirmation_needed: false`; NEVER move a range outside
  `applicability_domain`; NEVER change `confidence` enums (they are
  deterministically mapped — see method_notes C7).
- Flip `provenance.authored_by` to `"agent"`.

## Phase 5 — Quality Gate

```bash
node "$SKILL_PATH/scripts/quality_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH"
```

- G1 effect rows complete (p/q or reason_code) · G2 |r|≥0.3 all carry anti-spurious
  verdicts · G3 windows in observed domain · G4 observational windows require
  confirmation · G5 figures pass ink gate · G6 all artifacts schema-valid +
  strict key check · G7 report.html · **G8** association pairs never enter a window
  (and the screen ref sha256 matches disk) · **G9** four-interval semantics
  (`pi95` strictly wider than `mean_ci95`; `pi95_method` names the `1 +` term; no
  pass-rate PI) · **G10** every `actionable` joint setpoint has zero hard-constraint
  violations, valid units, and is inside the design region · **G11**
  `factor_response_matrix` covers every factor × response with a window or a reason.
- **G8–G11 report `n/a` when the artifact they inspect is absent** — absence is not
  a failure (a legacy run without `association_screen.json` still passes).
- On FAIL: locate the failing check item, then branch:
  - (a) **Script artifact** FAIL → re-run the corresponding script step (never
    hand-edit JSON numbers); the only fix for this class.
  - (b) FAIL introduced by **your own Phase 3/4 edits** → revert your edit (not
    "hand-editing computed numbers"; script re-runs cannot fix it and would wipe enrichment).
  - (c) **Environmental failure** (e.g. validator missing) → stop and report
    the environment blocker; it does not consume fix rounds.
  Max 3 fix rounds (classes a/b); then report the blocker list.

## Phase 6 — Report & Handoff

- Write `RUN_DIR/report.md` from `templates/analysis_report_template.md`
  (Chinese; 10-second conclusion card → 1-minute evidence → deep audit).
  Placeholder → artifact mapping (never invent numbers):

  | Placeholder | Fill from |
  |---|---|
  | `{{TOP_FACTORS}}` | designed: `effect_table.json` families[].tests sorted by pareto_rank, top 3 · observational: `correlation_report.json` top 3 by ΔR² contribution |
  | `{{EVIDENCE_TABLE}}` | designed: families[].tests (bold q<0.05) · observational: correlation_report.pairs (bold where verdict != PASS) |
  | `{{GRADE_REASON}}` | method_notes C11 rubric (checklist fail count → A / A− / B) |
  | `{{STABILITY_SUMMARY}}` | `stability_report.json` capability + drift_flags |
  | `{{AUDIT_DETAILS}}` | designed: `model.json` (R²/adj-R²/Q²/lack-of-fit/saturation disclosure) · observational: correlation anti-spurious summary |
  | `{{LIMITATIONS}}` | `doe_conclusion.json` limitations copied VERBATIM (never delete entries) |
  | `{{CONFIRMATIONS}}` | `recommendations.json` confirmations[] (incl. design_hint / runs) |
  | `{{USAGE_RULES}}` | `recommendations.json` usage_rules copied verbatim |

- Render `RUN_DIR/report.html` — script-generated, NEVER hand-write or hand-edit
  the HTML:
  `uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/analyze.py" report --run-dir "$RUN_DIR"`
  Gate G7 (`quality_gate.mjs`) verifies it: ≥20KB and ≤5MB, embedded artifact
  sha256 matches disk, mode-required sections, 3-line caption per figure, no null/NaN leakage.
- Done: `report.md` non-empty + `report.html` exists + quality gate exit 0; then
  log `agent_complete`: `node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event agent_complete --agent doe-analyst --step doe_analysis --files conclusions/doe_conclusion.json,conclusions/recommendations.json`
- Print the downstream usage card (contract version, windows count, confirmations
  count, applicability domain, usage rules) for the tuning/optimization agent handoff.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Data file unreadable / no numeric columns | Refuse to run; report formats tried |
| All factors zero-variance | Abort; request usable data |
| Mode ambiguous | Conservative: observational via `mode_override` (Phase 1) + re-run profile + caveat |
| Regime detector finds no steady rows | Windows from best segments + confirmation; caveat |
| Gate FAIL after 3 rounds | Report blocker list; do NOT self-declare done |
