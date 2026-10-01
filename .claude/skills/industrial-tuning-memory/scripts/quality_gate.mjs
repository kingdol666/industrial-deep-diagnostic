#!/usr/bin/env node
// quality_gate.mjs — deterministic exit-code gate for industrial-tuning-memory.
// Exit 0 = all pass; exit 1 = at least one FAIL (named check IDs).
//
// T1 artifact presence (fails only when NOTHING gateable exists)
// T2 all 5 frozen schemas validated via shared validate.mjs
//    (action_log, attribution_report, tuning_experience, fault_signature, recommendation)
// T3 STRICT extra-keys check (validate.mjs only warns on additionalProperties)
// T4 honesty assertions: not_estimable => reason_code AND effect=null;
//    effect!=null => status!=not_estimable; truncated => truncated_by set;
//    compromised => reason_code set; attribution reports are E0/E1 only
// T5 enum literal validation — every enum field checked against
//    .claude/shared/schemas/closedloop_enums.json (single source of truth)
// T6 store consistency: admission rule (no not_estimable), E2/E3 promotion
//    preconditions, retro entries locked to E0
// T7 recommendation consistency: playbook grades match the store, playbook_hit
//    requires match_scope + score>=0.55, autonomy_level NEVER written by IDD,
//    ack.status enum
// T8 privacy: raw actor ids from the alias map must not leak into
//    06_experience/** or conclusions/**
//
// Usage: node quality_gate.mjs <run_dir> --skill-path <skill> --shared-path <shared>
//        [--alias-map <path>]

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(path.join(SCRIPT_DIR, '..', '..', '..', '..'));

const argv = process.argv.slice(2);
const runDir = argv[0];
if (!runDir) {
  console.error('Usage: node quality_gate.mjs <run_dir> --skill-path <skill> --shared-path <shared> [--alias-map <path>]');
  process.exit(1);
}
function flag(name, fallback) {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
}
const skillPath = flag('--skill-path', path.join(REPO_ROOT, '.claude', 'skills', 'industrial-tuning-memory'));
const sharedPath = flag('--shared-path', path.join(REPO_ROOT, '.claude', 'shared'));
const schema = (name) => path.join(skillPath, 'schemas', name);

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id} ${ok ? '' : '- ' + detail}`);
}
const readJson = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return null; } };

const ENUMS = readJson(path.join(sharedPath, 'schemas', 'closedloop_enums.json')) || {};
const TM = ENUMS.tuning_memory || {};
const EVIDENCE = Object.keys(ENUMS.evidence_grades || { E0: 1, E1: 1, E2: 1, E3: 1 });

const P = {
  actionLog: path.join(runDir, '00_input', 'action_log.json'),
  retroLog: path.join(runDir, '06_experience', 'retro_action_log.json'),
  attributionDir: path.join(runDir, '06_experience', 'attribution'),
  store: path.join(runDir, '06_experience', 'tuning_experience.jsonl'),
  faultSig: path.join(runDir, '00_input', 'fault_signature.json'),
  recommendation: path.join(runDir, 'conclusions', 'recommendation.json'),
};

// ------------------------------------------------------------------ T1
const gateables = [P.actionLog, P.retroLog, P.attributionDir, P.store, P.faultSig, P.recommendation]
  .filter((p) => fs.existsSync(p));
check('T1_something_to_gate', gateables.length > 0, 'no gateable artifacts found in run_dir');

// ------------------------------------------------- T2 schema via validate.mjs
const validator = path.join(sharedPath, 'scripts', 'validate.mjs');
const tmpDir = path.join(runDir, '06_experience', '.gate_tmp');
const schemaJobs = []; // {file, schemaName, label}
if (fs.existsSync(P.actionLog)) schemaJobs.push({ file: P.actionLog, schemaName: 'action_log.schema.json', array: true, label: 'action_log' });
if (fs.existsSync(P.retroLog)) schemaJobs.push({ file: P.retroLog, schemaName: 'action_log.schema.json', array: true, label: 'retro_action_log' });
if (fs.existsSync(P.faultSig)) schemaJobs.push({ file: P.faultSig, schemaName: 'fault_signature.schema.json', array: false, label: 'fault_signature' });
if (fs.existsSync(P.recommendation)) schemaJobs.push({ file: P.recommendation, schemaName: 'recommendation.schema.json', array: false, label: 'recommendation' });
if (fs.existsSync(P.attributionDir)) {
  for (const f of fs.readdirSync(P.attributionDir).filter((f) => f.endsWith('.json')).sort()) {
    schemaJobs.push({ file: path.join(P.attributionDir, f), schemaName: 'attribution_report.schema.json', array: false, label: `attribution/${f}` });
  }
}
if (fs.existsSync(P.store)) schemaJobs.push({ file: P.store, schemaName: 'tuning_experience.schema.json', jsonl: true, label: 'tuning_experience' });

let schemaBad = [];
if (fs.existsSync(validator)) {
  fs.mkdirSync(tmpDir, { recursive: true });
  let n = 0;
  for (const job of schemaJobs) {
    let elements = [];
    try {
      if (job.jsonl) elements = fs.readFileSync(job.file, 'utf-8').split(/\r?\n/).filter(Boolean)
        .map((l, i) => ({ data: JSON.parse(l), idx: i }));
      else if (job.array) {
        const raw = readJson(job.file);
        const arr = Array.isArray(raw) ? raw : [raw];
        elements = arr.map((data, idx) => ({ data, idx }));
      } else elements = [{ data: readJson(job.file), idx: 0 }];
    } catch (e) {
      schemaBad.push(`${job.label}: unparseable (${String(e.message).slice(0, 80)})`);
      continue;
    }
    for (const el of elements) {
      const tmp = path.join(tmpDir, `${job.label.replace(/[\\/]/g, '_')}_${el.idx}.json`);
      fs.writeFileSync(tmp, JSON.stringify(el.data), 'utf-8');
      try {
        execFileSync('node', [validator, schema(job.schemaName), tmp], { stdio: 'pipe' });
      } catch (e) {
        schemaBad.push(`${job.label}[${el.idx}]: ${String(e.stderr || e.message).slice(0, 140)}`);
      }
      n += 1;
    }
  }
  fs.rmSync(tmpDir, { recursive: true, force: true });
  check(`T2_schema_validation (${schemaJobs.length} artifact(s), ${n} element(s))`,
    schemaBad.length === 0, schemaBad.slice(0, 5).join('; '));
} else {
  check('T2_schema_validation', false, `validator not found at ${validator}`);
}

// ----------------------------------------------------------- T3 strict keys
const ACTION_LOG_KEYS = ['schema_version', 'action_log_id', 'ts', 'actor', 'actions',
  'bundled_action', 'context', 'trigger', 'outcome', 'attribution_confounds',
  'recommendation_ref', 'ingest_meta'];
const ACTION_NESTED = {
  actor: ['actor_id', 'actor_type', 'display_alias'],
  actions_item: ['parameter', 'from', 'to', 'to_level', 'unit'],
  bundled_action: ['is_bundle', 'bundle_reason', 'note'],
  context: ['product', 'machine', 'regime_label', 'steady_segment_ref', 'group_key'],
  steady_segment_ref: ['data_path', 'row_range', 'time_range'],
  trigger: ['trigger_type', 'ref_id'],
  outcome: ['metric', 'before_window', 'after_window', 'observed_trajectory', 'observed_by'],
  window: ['row_range', 'time_range'],
  confound: ['type', 'note', 'ts'],
  ingest_meta: ['source', 'ingested_at'],
};
const ATTR_KEYS = ['report_version', 'action_log_id', 'bundle_scope', 'attribution_status',
  'reason_code', 'metric', 'segments', 'effect', 'confound_detected',
  'attribution_compromised', 'anti_spurious', 'evidence_grade', 'provenance'];
const ATTR_NESTED = {
  segments: ['baseline', 'effect', 'dead_time_used'],
  segment: ['row_range', 'n', 'n_eff', 'lag1_autocorr', 'truncated_by'],
  effect: ['delta', 'ci95', 'n_eff_hi', 'n_eff_lo', 'direction_established', 'stratified'],
  strat_item: ['group', 'n', 'delta', 'ci95', 'skipped'],
  anti_spurious: ['trend_check', 'outlier_check'],
  provenance: ['script_version', 'authored_by'],
};
const EXP_KEYS = ['experience_version', 'experience_type', 'regime_key', 'payload',
  'applicability', 'provenance', 'confidence_label', 'evidence_grade',
  'corroboration_count', 'refutation_count', 'cross_regime_consistent',
  'invalidation_conditions',
  // local-store envelope (stripped before AWS kb_agent ingestion):
  'chunk_id', 'action_signature', 'retro_mined', 'param_directions'];
const EXP_NESTED = {
  payload: ['action_summary', 'effect', 'attribution_status', 'confound_detected',
    'trajectory', 'fault_signature', 'action_sequence', 'applicability_note',
    'final_setpoints', 'achieved', 'rounds_used', 'trials_used', 'confirm_status', 'lesson'],
  effect: ['metric', 'delta', 'ci95', 'n_eff', 'direction_established'],
  seq_item: ['parameter', 'to', 'to_level', 'unit', 'step_order', 'expected_effect'],
  applicability: ['factor_observed_ranges', 'system', 'scenario_tags'],
  provenance: ['actor_alias', 'action_log_ids', 'run_ids', 'batch_ids', 'regime_key',
    'attribution_version', 'built_from', 'judge_score', 'era'],
};
const REC_KEYS = ['contract_version', 'recommendation_id', 'generated_at', 'source',
  'recommendation_status', 'match_scope', 'degradation_path', 'playbooks',
  'final_setpoints', 'fallback', 'ack', 'provenance'];
// autonomy_level intentionally absent — IDD never sets a dispatch policy (v1.4)
const REC_NESTED = {
  source: ['fault_signature', 'trigger_alert_id', 'campaign_id'],
  playbook: ['experience_id', 'action_sequence', 'expected_effect', 'evidence_grade',
    'corroboration_count', 'refutation_count', 'provenance_alias',
    'invalidation_conditions', 'match_score', 'autonomy_level'],
  fallback: ['doe_analyzer_hint'],
  ack: ['status', 'ack_at', 'executed_action_log_id', 'note'],
  provenance: ['script_version', 'authored_by'],
};
const SIG_KEYS = ['signature_version', 'source_ref', 'anomalous_params', 'regime', 'degraded_metric'];
const SIG_NESTED = {
  param_item: ['parameter', 'direction', 'severity'],
  regime: ['product', 'machine', 'regime_label'],
};

const extra = (obj, allowed) => Object.keys(obj || {}).filter((k) => !allowed.includes(k));

function checkActionLogStrict(file, label) {
  const raw = readJson(file);
  const arr = Array.isArray(raw) ? raw : (raw ? [raw] : []);
  let bad = [];
  for (const log of arr) {
    bad = bad.concat(extra(log, ACTION_LOG_KEYS).map((k) => `${label}.${k}`));
    bad = bad.concat(extra(log.actor, ACTION_NESTED.actor).map((k) => `${label}.actor.${k}`));
    for (const a of log.actions || []) bad = bad.concat(extra(a, ACTION_NESTED.actions_item).map((k) => `${label}.actions.${k}`));
    if (log.bundled_action) bad = bad.concat(extra(log.bundled_action, ACTION_NESTED.bundled_action).map((k) => `${label}.bundled.${k}`));
    if (log.context) {
      bad = bad.concat(extra(log.context, ACTION_NESTED.context).map((k) => `${label}.context.${k}`));
      if (log.context.steady_segment_ref) bad = bad.concat(extra(log.context.steady_segment_ref, ACTION_NESTED.steady_segment_ref).map((k) => `${label}.ctx_ref.${k}`));
    }
    if (log.trigger) bad = bad.concat(extra(log.trigger, ACTION_NESTED.trigger).map((k) => `${label}.trigger.${k}`));
    if (log.outcome) {
      bad = bad.concat(extra(log.outcome, ACTION_NESTED.outcome).map((k) => `${label}.outcome.${k}`));
      for (const w of ['before_window', 'after_window']) {
        if (log.outcome[w]) bad = bad.concat(extra(log.outcome[w], ACTION_NESTED.window).map((k) => `${label}.${w}.${k}`));
      }
    }
    for (const c of log.attribution_confounds || []) bad = bad.concat(extra(c, ACTION_NESTED.confound).map((k) => `${label}.confound.${k}`));
    if (log.ingest_meta) bad = bad.concat(extra(log.ingest_meta, ACTION_NESTED.ingest_meta).map((k) => `${label}.ingest.${k}`));
  }
  return bad;
}

function checkAttribStrict(file, label) {
  const r = readJson(file);
  if (!r) return [`${label}: unreadable`];
  let bad = extra(r, ATTR_KEYS).map((k) => `${label}.${k}`);
  if (r.segments) {
    bad = bad.concat(extra(r.segments, ATTR_NESTED.segments).map((k) => `${label}.segments.${k}`));
    for (const s of ['baseline', 'effect']) {
      if (r.segments[s]) bad = bad.concat(extra(r.segments[s], ATTR_NESTED.segment).map((k) => `${label}.segments.${s}.${k}`));
    }
  }
  if (r.effect) {
    bad = bad.concat(extra(r.effect, ATTR_NESTED.effect).map((k) => `${label}.effect.${k}`));
    for (const s of r.effect.stratified || []) {
      bad = bad.concat(extra(s, ATTR_NESTED.strat_item).map((k) => `${label}.strat.${k}`));
    }
  }
  if (r.anti_spurious) bad = bad.concat(extra(r.anti_spurious, ATTR_NESTED.anti_spurious).map((k) => `${label}.anti_spurious.${k}`));
  if (r.provenance) bad = bad.concat(extra(r.provenance, ATTR_NESTED.provenance).map((k) => `${label}.provenance.${k}`));
  return bad;
}

let strictBad = [];
if (fs.existsSync(P.actionLog)) strictBad = strictBad.concat(checkActionLogStrict(P.actionLog, 'action_log'));
if (fs.existsSync(P.retroLog)) strictBad = strictBad.concat(checkActionLogStrict(P.retroLog, 'retro'));
if (fs.existsSync(P.attributionDir)) {
  for (const f of fs.readdirSync(P.attributionDir).filter((f) => f.endsWith('.json')).sort()) {
    strictBad = strictBad.concat(checkAttribStrict(path.join(P.attributionDir, f), `attr/${f}`));
  }
}
if (fs.existsSync(P.store)) {
  const entries = fs.readFileSync(P.store, 'utf-8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
  entries.forEach((e, i) => {
    let bad = extra(e, EXP_KEYS).map((k) => `store[${i}].${k}`);
    if (e.payload) bad = bad.concat(extra(e.payload, EXP_NESTED.payload).map((k) => `store[${i}].payload.${k}`));
    if (e.payload && e.payload.effect) bad = bad.concat(extra(e.payload.effect, EXP_NESTED.effect).map((k) => `store[${i}].effect.${k}`));
    for (const s of (e.payload || {}).action_sequence || []) bad = bad.concat(extra(s, EXP_NESTED.seq_item).map((k) => `store[${i}].seq.${k}`));
    if (e.applicability) bad = bad.concat(extra(e.applicability, EXP_NESTED.applicability).map((k) => `store[${i}].applicability.${k}`));
    if (e.provenance) bad = bad.concat(extra(e.provenance, EXP_NESTED.provenance).map((k) => `store[${i}].provenance.${k}`));
    strictBad = strictBad.concat(bad);
  });
}
if (fs.existsSync(P.recommendation)) {
  const r = readJson(P.recommendation);
  let bad = extra(r, REC_KEYS).map((k) => `recommendation.${k}`);
  if (r.source) bad = bad.concat(extra(r.source, REC_NESTED.source).map((k) => `recommendation.source.${k}`));
  for (const p of r.playbooks || []) bad = bad.concat(extra(p, REC_NESTED.playbook).map((k) => `playbook.${k}`));
  if (r.fallback) bad = bad.concat(extra(r.fallback, REC_NESTED.fallback).map((k) => `fallback.${k}`));
  if (r.ack) bad = bad.concat(extra(r.ack, REC_NESTED.ack).map((k) => `ack.${k}`));
  if (r.provenance) bad = bad.concat(extra(r.provenance, REC_NESTED.provenance).map((k) => `provenance.${k}`));
  strictBad = strictBad.concat(bad);
}
if (fs.existsSync(P.faultSig)) {
  const s = readJson(P.faultSig);
  let bad = extra(s, SIG_KEYS).map((k) => `fault_signature.${k}`);
  for (const p of s.anomalous_params || []) bad = bad.concat(extra(p, SIG_NESTED.param_item).map((k) => `sig_param.${k}`));
  if (s.regime) bad = bad.concat(extra(s.regime, SIG_NESTED.regime).map((k) => `sig_regime.${k}`));
  strictBad = strictBad.concat(bad);
}
check('T3_strict_extra_keys', strictBad.length === 0,
  strictBad.length ? `undeclared keys: ${strictBad.slice(0, 8).join(', ')}` : '');

// ------------------------------------------------------------ T4 + T5 honesty & enums
function walkAttribReports(fn) {
  const bad = [];
  if (fs.existsSync(P.attributionDir)) {
    for (const f of fs.readdirSync(P.attributionDir).filter((f) => f.endsWith('.json')).sort()) {
      const r = readJson(path.join(P.attributionDir, f));
      if (r) bad.push(...fn(r, f).map((m) => `${f}: ${m}`));
    }
  }
  return bad;
}

let honestyBad = [];
honestyBad = honestyBad.concat(walkAttribReports((r, f) => {
  const out = [];
  if (r.attribution_status === 'not_estimable') {
    if (r.reason_code == null) out.push('not_estimable without reason_code');
    if (r.effect !== null) out.push('not_estimable with non-null effect (fabrication)');
  }
  if (r.effect !== null && r.attribution_status === 'not_estimable') out.push('effect present on not_estimable');
  if (r.attribution_status === 'truncated'
      && !(((r.segments || {}).effect || {}).truncated_by)) out.push('truncated without truncated_by');
  if (r.attribution_compromised === true && r.reason_code == null) out.push('compromised without reason_code');
  if (!['E0', 'E1'].includes(r.evidence_grade)) out.push(`single-run grade ${r.evidence_grade} not in {E0,E1}`);
  if ((r.provenance || {}).authored_by !== 'script') out.push('attribution report must be authored_by=script');
  const eff = r.effect;
  if (eff && eff.direction_established === true && eff.ci95
      && !((eff.ci95[0] > 0) || (eff.ci95[1] < 0))) {
    out.push('direction_established=true but CI95 crosses 0');
  }
  return out;
}));
check('T4_honesty_attribution', honestyBad.length === 0, honestyBad.slice(0, 5).join('; '));

let enumBad = [];
enumBad = enumBad.concat(walkAttribReports((r, f) => {
  const out = [];
  if (!(TM.attribution_status || []).includes(r.attribution_status)) out.push(`attribution_status=${r.attribution_status}`);
  if (!( [null, ...(TM.not_estimable_reason_codes || [])].includes(r.reason_code))) out.push(`reason_code=${r.reason_code}`);
  if (!EVIDENCE.includes(r.evidence_grade)) out.push(`evidence_grade=${r.evidence_grade}`);
  for (const k of ['trend_check', 'outlier_check']) {
    const v = (r.anti_spurious || {})[k] ?? null;
    if (!(['PASS', 'CAUTION', 'FAIL', null].includes(v))) out.push(`${k}=${v}`);
  }
  return out;
}));
const checkActionLogEnums = (file, label) => {
  const raw = readJson(file);
  const arr = Array.isArray(raw) ? raw : (raw ? [raw] : []);
  const out = [];
  arr.forEach((log, i) => {
    const at = (log.actor || {}).actor_type;
    if (!(TM.actor_types || []).includes(at)) out.push(`[${i}] actor_type=${at}`);
    const tr = (log.trigger || {}).trigger_type;
    if (tr !== undefined && !(TM.trigger_types || []).includes(tr)) out.push(`[${i}] trigger_type=${tr}`);
    const bt = (log.bundled_action || {}).bundle_reason;
    if (bt !== undefined && !['coupled_move', 'recipe_change', 'single', null].includes(bt)) out.push(`[${i}] bundle_reason=${bt}`);
    const ot = (log.outcome || {}).observed_trajectory;
    if (ot !== undefined && ![...(TM.observed_trajectories || []), null].includes(ot)) out.push(`[${i}] observed_trajectory=${ot}`);
    const src = (log.ingest_meta || {}).source;
    if (src !== undefined && !['api', 'csv_import', 'retro_mined', null].includes(src)) out.push(`[${i}] ingest source=${src}`);
  });
  return out.map((m) => `${label} ${m}`);
};
if (fs.existsSync(P.actionLog)) enumBad = enumBad.concat(checkActionLogEnums(P.actionLog, 'action_log'));
if (fs.existsSync(P.retroLog)) enumBad = enumBad.concat(checkActionLogEnums(P.retroLog, 'retro'));

let storeEntries = [];
if (fs.existsSync(P.store)) {
  storeEntries = fs.readFileSync(P.store, 'utf-8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
  storeEntries.forEach((e, i) => {
    if (!(TM.experience_types || []).includes(e.experience_type)) enumBad.push(`store[${i}] experience_type=${e.experience_type}`);
    if (e.payload && e.payload.attribution_status !== undefined
        && ![...(TM.attribution_status || []), null].includes(e.payload.attribution_status)) {
      enumBad.push(`store[${i}] attribution_status=${e.payload.attribution_status}`);
    }
    if (!['verified', 'observation', null].includes(e.confidence_label ?? null)) enumBad.push(`store[${i}] confidence_label=${e.confidence_label}`);
    if (e.evidence_grade !== undefined && ![...EVIDENCE, null].includes(e.evidence_grade)) enumBad.push(`store[${i}] evidence_grade=${e.evidence_grade}`);
  });
}
if (fs.existsSync(P.faultSig)) {
  const s = readJson(P.faultSig);
  for (const p of s.anomalous_params || []) {
    if (!['high', 'low', 'unknown'].includes(p.direction)) enumBad.push(`fault_signature direction=${p.direction}`);
  }
}
if (fs.existsSync(P.recommendation)) {
  const r = readJson(P.recommendation);
  if (!(TM.recommendation_status || []).includes(r.recommendation_status)) enumBad.push(`recommendation_status=${r.recommendation_status}`);
  if (r.match_scope !== undefined && ![...(TM.match_scopes || []), null].includes(r.match_scope)) enumBad.push(`match_scope=${r.match_scope}`);
  if (r.ack !== undefined && r.ack !== null
      && !([...(ENUMS.ack || {}).statuses || [], null].includes((r.ack || {}).status ?? null))) {
    enumBad.push(`ack.status=${(r.ack || {}).status}`);
  }
  for (const p of r.playbooks || []) {
    if (!EVIDENCE.includes(p.evidence_grade)) enumBad.push(`playbook evidence_grade=${p.evidence_grade}`);
  }
}
check('T5_enum_literals_from_closedloop_enums', enumBad.length === 0,
  enumBad.length ? enumBad.slice(0, 6).join('; ') : '');

// -------------------------------------------------------- T6 store consistency
let storeBad = [];
storeEntries.forEach((e, i) => {
  if (e.payload && e.payload.attribution_status === 'not_estimable') {
    storeBad.push(`store[${i}]: not_estimable entry admitted (admission rule violated)`);
  }
  if (e.retro_mined === true && e.evidence_grade !== 'E0') {
    storeBad.push(`store[${i}]: retro_mined entry must stay E0`);
  }
  if (['E2', 'E3'].includes(e.evidence_grade)) {
    const p = e.payload || {};
    const ci = (p.effect || {}).ci95;
    const ciExcl0 = Array.isArray(ci) && ci.length === 2 && (ci[0] > 0 || ci[1] < 0);
    if ((e.corroboration_count || 0) < 2) storeBad.push(`store[${i}]: E2+ with corroboration<2`);
    if (!ciExcl0) storeBad.push(`store[${i}]: E2+ but CI95 crosses 0`);
    if (p.confound_detected === true) storeBad.push(`store[${i}]: E2+ with confound`);
    if (p.attribution_status !== 'estimable') storeBad.push(`store[${i}]: E2+ without estimable status`);
    if (p.confirm_status === 'unconfirmed') storeBad.push(`store[${i}]: E2+ on unconfirmed execution`);
    if (e.retro_mined === true) storeBad.push(`store[${i}]: E2+ on retro entry`);
    if (e.evidence_grade === 'E3' && e.cross_regime_consistent !== true) {
      storeBad.push(`store[${i}]: E3 without cross_regime_consistent`);
    }
  }
});
check('T6_store_consistency', storeBad.length === 0, storeBad.slice(0, 5).join('; '));

// ---------------------------------------------------- T7 recommendation logic
let recBad = [];
if (fs.existsSync(P.recommendation)) {
  const r = readJson(P.recommendation);
  // v1.4: the frozen contract keeps autonomy_level as the AWS-side dispatch-policy
  // carrier — IDD must leave it null (top level) and never set a policy value anywhere
  if ('autonomy_level' in r && r.autonomy_level !== null) {
    recBad.push(`top-level autonomy_level=${r.autonomy_level} — IDD never sets a dispatch policy`);
  }
  for (const p of r.playbooks || []) {
    if ('autonomy_level' in p && p.autonomy_level !== null) {
      recBad.push(`playbook ${p.experience_id} autonomy_level=${p.autonomy_level} — IDD always writes null`);
    }
  }
  if (!('autonomy_level' in ((r.playbooks || [])[0] || {}))
      && (r.playbooks || []).length) {
    recBad.push('playbooks[0] missing autonomy_level:null (frozen contract requires the key)');
  }
  if (r.recommendation_status === 'playbook_hit') {
    if (!(r.playbooks || []).length) recBad.push('playbook_hit without playbooks');
    if (r.match_scope == null) recBad.push('playbook_hit without match_scope');
    for (const p of r.playbooks || []) {
      if (p.match_score != null && p.match_score < 0.55) recBad.push(`playbook ${p.experience_id} score ${p.match_score} < 0.55 on a hit`);
    }
  }
  if (r.recommendation_status === 'fallback_generic'
      && !((((r.fallback || {}).doe_analyzer_hint) || '').length)) {
    recBad.push('fallback_generic without doe_analyzer_hint');
  }
  const byId = new Map(storeEntries.map((e) => [e.chunk_id, e]));
  for (const p of r.playbooks || []) {
    const e = byId.get(p.experience_id);
    if (e && p.evidence_grade !== e.evidence_grade) {
      recBad.push(`playbook ${p.experience_id} grade ${p.evidence_grade} != store ${e.evidence_grade}`);
    }
  }
}
check('T7_recommendation_consistency', recBad.length === 0, recBad.slice(0, 5).join('; '));

// ------------------------------------------------------------------ T8 privacy
let privacyBad = [];
let aliasMap = null;
const aliasFlag = flag('--alias-map', null);
for (const cand of [aliasFlag, path.join(runDir, '00_input', 'actor_alias_map.json'), path.join(REPO_ROOT, 'config', 'tuning_memory.json')]) {
  if (cand && fs.existsSync(cand)) { aliasMap = readJson(cand); break; }
}
if (aliasMap) {
  const rawIds = Object.keys(aliasMap).filter((k) => k && k !== String(aliasMap[k]));
  const scanDirs = [path.join(runDir, '06_experience'), path.join(runDir, 'conclusions')];
  const scan = (dir) => {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name);
      if (entry.isDirectory()) { scan(p); continue; }
      if (!/\.(json|jsonl|md)$/.test(entry.name)) continue;
      const text = fs.readFileSync(p, 'utf-8');
      for (const rid of rawIds) {
        if (rid.length >= 3 && text.includes(rid)) {
          privacyBad.push(`${path.relative(runDir, p)} leaks raw actor id`);
        }
      }
    }
  };
  scanDirs.forEach(scan);
  check('T8_privacy_no_raw_ids', privacyBad.length === 0,
    privacyBad.length ? privacyBad.slice(0, 5).join('; ') : `checked ${rawIds.length} alias-mapped id(s)`);
} else {
  check('T8_privacy_no_raw_ids', true, 'no alias map found — check skipped');
}

const failed = results.filter((r) => !r.ok);
console.log(`\n[GATE] ${results.length - failed.length}/${results.length} checks passed`
  + (failed.length ? ` — FAIL(${failed.map((f) => f.id.split(' ')[0]).join(', ')})` : ' — ALL PASS'));
process.exit(failed.length ? 1 : 0);
