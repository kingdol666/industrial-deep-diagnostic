# Tuning Memory — Agent Protocol (Phase 0-6)

Execution checklist for the `tuning-memory` agent. All statistics are computed by
`scripts/*` (zero LLM); you never hand-compute, never edit computed numbers, never
raise an evidence grade, and never write a dispatch decision. Python always runs
through uv from the repo root:

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/<script>.py" ...
node "$SKILL_PATH/scripts/<script>.mjs" ...
```

## Phase 0 — Run context

1. Confirm `RUN_DIR/00_input/` contains the time-ordered data (CSV; time column +
   metric column) and `action_log.json` (single object, array, JSONL, or a
   directory of action logs). Missing either → request it; do not invent actions.
2. Note the Δt convention: **1 row = 1 sampling step**; all segment quantities
   are in steps.
3. If an actor alias map exists (`00_input/actor_alias_map.json` or
   `config/tuning_memory.json`), reference it in later phases (privacy: raw ids
   must never reach `06_experience/**` or `conclusions/**`).

## Phase 1 — Attribution (deterministic)

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/tune_stats.py" attribute \
  --run-dir "$RUN_DIR" --data 00_input/data.csv --time-col t --metric <metric> \
  [--group-key <col>] [--dead-time <steps|unknown>]
```

- One `06_experience/attribution/{action_log_id}.json` per action log; bundle
  (one log) = attribution unit.
- `--dead-time` omitted → assumed 0 (degradation annotated into the experience
  entry); `--dead-time unknown` → honest `not_estimable/dead_time_unknown`.
- Read each report. `not_estimable` with a reason_code and `effect=null` is a
  valid, honest outcome — carry it forward verbatim, never fabricate a delta.
- Load-bearing fields: `attribution_status`, `reason_code`, `anti_spurious`,
  `confound_detected`, `attribution_compromised`, `evidence_grade`.

## Phase 2 — Experience store build

```bash
node "$SKILL_PATH/scripts/experience_build.mjs" build --run-dir "$RUN_DIR" \
  [--alias-map 00_input/actor_alias_map.json]
```

- Admission: `attribution_status != not_estimable` (E0 retro entries allowed as
  observation-grade). Skipped logs are listed on stdout with the reason.
- Same action signature + same regime = idempotent (replay no-ops); a different
  action log with the same signature corroborates (+1) and can promote E1→E2.
- aws_executor actions must carry `recommendation_ref` with a received/executed
  ack, otherwise the resulting entries are marked `unconfirmed` and excluded
  from promotion (B13).

## Phase 3 — Retrieval / recommendation

```bash
node "$SKILL_PATH/scripts/match_playbook.mjs" recommend --run-dir "$RUN_DIR" \
  [--signature 00_input/fault_signature.json]
```

- Regime hard-filter relaxes regime→product→machine→generic; score = 0.5·direction
  + 0.3·Jaccard + 0.2·regime-overlap; threshold 0.55 → `playbook_hit`.
- Four-level degradation chain lands in `degradation_path`; `fallback_generic`
  carries the doe-analyzer hint.
- **Never** set `autonomy_level` to a policy value: the frozen contract keeps it as
  the AWS-side dispatch-policy carrier and IDD always writes `null`; evidence grades
  travel as advisory strength with the note "dispatch policy is AWS-side".

### Execution receipt (when the ack file arrives)

```bash
node "$SKILL_PATH/scripts/match_playbook.mjs" ack --run-dir "$RUN_DIR" \
  --ack-file <inbox>/ack-{ts}-{seq}.json   # {recommendation_id, status, executed_action_log_id}
```

## Phase 4 — Feedback loop

```bash
node "$SKILL_PATH/scripts/experience_build.mjs" feedback --run-dir "$RUN_DIR" \
  --chunk-id <chunk_id> --result effective|ineffective|harmful|confirmed [--note "..."]
```

- effective → corroboration+1; ineffective|harmful → refutation+1 (any refutation
  caps at E1; ≥2 demotes verified→observation); confirmed → completes retro
  ownership attribution (the E0 retro lock itself stays).
- Promotion/demotion is count+statistics driven only — never LLM-judged.

## Phase 5 — Quality gate

```bash
node "$SKILL_PATH/scripts/quality_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH" [--alias-map <path>]
```

- T1 presence · T2 five schemas via validate.mjs · T3 strict extra-keys ·
  T4 honesty (not_estimable ⇒ reason_code ∧ effect=null) · T5 enum literals from
  `closedloop_enums.json` · T6 store consistency · T7 recommendation consistency ·
  T8 privacy grep.
- On FAIL: fix by RE-RUNNING the corresponding script step (never hand-edit JSON
  numbers). Max 3 fix rounds; then report the blocker list.

## Phase 6 — Handoff

- `06_experience/kb_summary.md` is the kb-ready artifact. Hand-off message to the
  main agent names: run dir, entry count, per-regime sections, evidence grades.
- KB ingestion path: **AWS agent → rag-bridge kb_agent**（regime_key 场景化分库）。
  The tuning-memory skill never calls a KB/RAG API itself. Envelope fields
  (`chunk_id`, `action_signature`, `retro_mined`) are local-store-only.
- Report in Chinese; JSON enums stay English.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| No action logs + data shows steps | step_detector retro mining → E0 advisory entries (Phase 2 with `--action-log 06_experience/retro_action_log.json`) |
| Metric column missing from data | `not_estimable/metric_missing` — ask for the correct metric; do not substitute silently |
| Gate FAIL after 3 rounds | Report blocker list; do NOT self-declare done |
| Raw actor id found by gate T8 | Regenerate the store with the alias map; the input action_log may keep raw ids (it never leaves 00_input) |
