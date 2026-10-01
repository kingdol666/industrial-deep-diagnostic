#!/usr/bin/env node
// quality_gate.mjs — deterministic gate for industrial-sentinel artifacts.
// Exit 0 = all pass; exit 1 = at least one FAIL (named check IDs).
//
// Usage:
//   node quality_gate.mjs <alert.json> [--baseline <watch_baseline.json>]
//                         [--skill-path <skill>] [--shared-path <shared>]
//
// S1 closedloop_enums.json literal validation — every severity / rule_name /
//    check_type / mode / status / urgency / suggested_next_skill /
//    baseline.mode / contract_version emitted in alert.json must be a member
//    of the shared enum file (single source of truth, v1.4: no autonomy).
// S2 schema validation of alert.json (+ watch_baseline.json when present)
//    via the shared validate.mjs; fast_state.json when given.
// S3 STRICT extra-keys check on the alert contract (top level, alerts[]
//    items, observed/threshold/evidence) — validate.mjs only warns.
// S4 storm self-check — no duplicate suppression_key / alert_id, and
//    repeat_count accounting correct (>= 1, matches suppression.applied).
// S5 zero-LLM assertion — provenance.zero_llm === true AND a source scan of
//    the Python surface (sentinel.py, sentinel_fast.py, build_baseline.py,
//    sentinelcore/**.py) for network/LLM call patterns.

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const args = process.argv.slice(2);
const alertPath = args[0];
if (!alertPath) {
  console.error('Usage: node quality_gate.mjs <alert.json> [--baseline <baseline.json>] [--skill-path P] [--shared-path P]');
  process.exit(1);
}
function flag(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const skillPath = flag('--skill-path', path.join('..', 'industrial-sentinel'));
const sharedPath = flag('--shared-path', path.join('..', '..', '..', '.claude', 'shared'));
const baselineArg = flag('--baseline', null);

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id} ${ok ? '' : '- ' + detail}`);
}
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

const alert = readJson(alertPath);
if (!alert) {
  console.log(`FAIL ALERT_READ ${alertPath} not readable`);
  process.exit(1);
}

// ---- S1: enum literals from closedloop_enums.json -------------------------
const enums = readJson(path.join(sharedPath, 'schemas', 'closedloop_enums.json'));
if (!enums) {
  check('S1_enums_loaded', false, `closedloop_enums.json not found under ${sharedPath}`);
} else {
  const bad = [];
  if (alert.contract_version !== enums.contract_versions.sentinel_alert) {
    bad.push(`contract_version=${alert.contract_version}`);
  }
  if (!enums.sentinel.modes.includes(alert.mode)) bad.push(`mode=${alert.mode}`);
  if (!enums.sentinel.status.includes(alert.status)) bad.push(`status=${alert.status}`);
  for (const a of alert.alerts || []) {
    if (!enums.sentinel.check_types.includes(a.check_type)) bad.push(`check_type=${a.check_type}`);
    if (!enums.sentinel.rule_names.includes(a.rule_name)) bad.push(`rule=${a.rule_name}`);
    if (!enums.severity.includes(a.severity)) bad.push(`severity=${a.severity}`);
    if (!enums.urgency.includes(a.urgency)) bad.push(`urgency=${a.urgency}`);
    const nxt = a.suggested_next_skill;
    if (nxt != null && !enums.sentinel.suggested_next_skill.includes(nxt)) {
      bad.push(`next_skill=${nxt}`);
    }
  }
  const bMode = alert.baseline && alert.baseline.mode;
  if (!['prior', 'self'].includes(bMode)) bad.push(`baseline.mode=${bMode}`);
  if (JSON.stringify(alert).includes('"autonomy"')) {
    bad.push('forbidden key autonomy (retired v1.4)');
  }
  check('S1_enum_literals', bad.length === 0, bad.slice(0, 8).join('; '));
}

// ---- S2: schema validation via validate.mjs -------------------------------
const validator = path.join(sharedPath, 'scripts', 'validate.mjs');
let schemaBad = [];
if (fs.existsSync(validator)) {
  const targets = [[alertPath, 'alert.schema.json']];
  let baselinePath = baselineArg;
  if (!baselinePath && alert.baseline && alert.baseline.path &&
      fs.existsSync(alert.baseline.path)) {
    baselinePath = alert.baseline.path;
  }
  if (baselinePath && fs.existsSync(baselinePath)) {
    targets.push([baselinePath, 'watch_baseline.schema.json']);
  }
  for (const [file, schema] of targets) {
    const schemaPath = path.join(skillPath, 'schemas', schema);
    try {
      execFileSync('node', [validator, schemaPath, file], { stdio: 'pipe' });
    } catch (e) {
      schemaBad.push(`${schema}: ${String(e.stderr || e.message).slice(0, 160)}`);
    }
  }
  check('S2_schema_validation', schemaBad.length === 0, schemaBad.join('; '));
} else {
  check('S2_schema_validation', false, `validator not found at ${validator}`);
}

// ---- S3: STRICT extra-keys -------------------------------------------------
const TOP_KEYS = ['contract_version', 'alert_id', 'mode', 'status', 'group_scope',
  'generated_at', 'source', 'baseline', 'checks_summary', 'alerts',
  'regime_summary', 'projection_summary', 'suppression', 'provenance'];
const ALERT_KEYS = ['alert_id', 'check_type', 'rule_name', 'parameter', 'indicator',
  'group', 'severity', 'urgency', 'observed', 'threshold', 'evidence',
  'suggested_check', 'suggested_next_skill', 'advisory', 'suppression_key',
  'repeat_count', 'interpretation'];
const OBSERVED_KEYS = ['value', 'statistic', 'index', 'timestamp', 'run_length'];
const THRESHOLD_KEYS = ['bound', 'sigma_level', 'lsl', 'usl', 'window',
  'd2_limit', 'hours_warn', 'hours_alarm'];
const EVIDENCE_KEYS = ['n_points', 'slope_per_hour', 'hours_to_edge', 'direction',
  'd2', 'contributing_params', 'ratio', 'cp_position', 'hysteresis_downgraded'];

function extraKeys(obj, allowed) {
  return Object.keys(obj || {}).filter((k) => !allowed.includes(k));
}
{
  const bad = extraKeys(alert, TOP_KEYS);
  for (const a of alert.alerts || []) {
    bad.push(...extraKeys(a, ALERT_KEYS).map((k) => `${a.rule_name}.${k}`));
    bad.push(...extraKeys(a.observed, OBSERVED_KEYS).map((k) => `${a.rule_name}.observed.${k}`));
    bad.push(...extraKeys(a.threshold, THRESHOLD_KEYS).map((k) => `${a.rule_name}.threshold.${k}`));
    bad.push(...extraKeys(a.evidence, EVIDENCE_KEYS).map((k) => `${a.rule_name}.evidence.${k}`));
  }
  check('S3_strict_extra_keys', bad.length === 0,
    bad.length ? `undeclared keys: ${bad.slice(0, 8).join(', ')}` : '');
}

// ---- S4: storm self-check ---------------------------------------------------
// Same suppression_key may appear several times ONLY as distinct episodes:
// pairwise observed.index gaps must exceed the suppression window (60, the
// row-space image of suppress_window_minutes at the canonical 1/min cadence).
// repeat_count accounting is cross-checked against suppression.applied
// (per-key summed repeat_count).
{
  const bad = [];
  const seenId = new Set();
  const perKey = new Map(); // key -> [indices], totals
  for (const a of alert.alerts || []) {
    if (seenId.has(a.alert_id)) bad.push(`duplicate alert_id ${a.alert_id}`);
    seenId.add(a.alert_id);
    const rc = a.repeat_count;
    if (!Number.isInteger(rc) || rc < 1) bad.push(`repeat_count=${rc}`);
    const idx = a.observed && a.observed.index;
    const entry = perKey.get(a.suppression_key) || { idxs: [], total: 0 };
    entry.idxs.push(idx);
    entry.total += rc;
    perKey.set(a.suppression_key, entry);
  }
  const SUPPRESS_WINDOW = (enums && enums.sentinel && enums.sentinel.suppression
    && enums.sentinel.suppression.suppress_window_minutes) || 60;
  for (const [key, { idxs }] of perKey) {
    const known = idxs.filter((i) => typeof i === 'number').sort((x, y) => x - y);
    if (known.length !== idxs.length && idxs.length > 1) {
      bad.push(`same-key alerts without positions: ${key}`);
    }
    for (let i = 1; i < known.length; i++) {
      if (known[i] - known[i - 1] <= SUPPRESS_WINDOW) {
        bad.push(`same-key alerts within suppression window: ${key}@${known[i]}`);
        break;
      }
    }
  }
  const applied = (alert.suppression && alert.suppression.applied) || [];
  for (const entry of applied) {
    const agg = perKey.get(entry.suppression_key);
    if (!agg) bad.push(`suppression.applied references unknown key ${entry.suppression_key}`);
    else if (agg.total !== entry.repeat_count) {
      bad.push(`repeat_count mismatch ${entry.suppression_key}: alerts sum=${agg.total} applied=${entry.repeat_count}`);
    }
  }
  check('S4_storm_self_check', bad.length === 0, bad.slice(0, 6).join('; '));
}

// ---- S5: zero-LLM assertion -------------------------------------------------
{
  const pyFiles = [];
  const roots = [
    path.join(skillPath, 'scripts', 'sentinelcore'),
    path.join(skillPath, 'scripts'),
  ];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    for (const name of fs.readdirSync(root)) {
      const fp = path.join(root, name);
      if (fs.statSync(fp).isDirectory()) {
        for (const n2 of fs.readdirSync(fp)) {
          if (n2.endsWith('.py')) pyFiles.push(path.join(fp, n2));
        }
      } else if (name.endsWith('.py')) {
        pyFiles.push(fp);
      }
    }
  }
  const FORBIDDEN = /\b(requests|urllib|httpx|socket|http\.client|aiohttp|openai|anthropic|litellm|langchain)\b|\bfetch\s*\(|https?:\/\/(?!localhost)/;
  const offenders = [];
  for (const fp of pyFiles) {
    const text = fs.readFileSync(fp, 'utf8');
    const lines = text.split(/\r?\n/);
    lines.forEach((line, i) => {
      if (FORBIDDEN.test(line)) offenders.push(`${path.basename(fp)}:${i + 1}`);
    });
  }
  check('S5_zero_llm_sources', offenders.length === 0,
    offenders.length ? `network/LLM pattern in ${offenders.slice(0, 5).join(', ')}` : `${pyFiles.length} py files scanned`);
  check('S5_zero_llm_flag', alert.provenance && alert.provenance.zero_llm === true,
    `zero_llm=${alert.provenance && alert.provenance.zero_llm}`);
}

const failed = results.filter((r) => !r.ok);
console.log(`\n[GATE] ${results.length - failed.length}/${results.length} checks passed` +
  (failed.length ? ` — FAIL(${failed.map((f) => f.id).join(', ')})` : ' — ALL PASS'));
process.exit(failed.length ? 1 : 0);
