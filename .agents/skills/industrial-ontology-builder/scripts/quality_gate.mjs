#!/usr/bin/env node
// quality_gate.mjs — industrial-ontology-builder deterministic quality gate.
// Executor of pipeline CP-2 (ontology schema + size) and CP-3 (clarification
// status) plus the E-1H heterogeneous-column merge rule. Zero dependencies
// (node builtins only; validate.mjs is spawned, never imported).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR>
// Exit: 0 ok | 1 hard error (bad inputs / usage) | 2 undetermined (01_ontology
//       absent — the ontology stage did not run) | 3 gate-fail (any check failed)
//
// Checks (all mechanical):
//   O1 01_ontology/ontology.json exists
//   O2 ontology.json parses
//   O3 ontology.json schema-valid against at least one ontology authority:
//        - skills/industrial-ontology-builder/schemas/ontology_schema.json
//          (the CP-2 single source of truth: the same file ontology_store.mjs
//          enforces on publish/reuse, and the one every ontology under
//          data/ontology_store validates against)
//        - .claude/shared/schemas/ontology_schema.json (domain-agnostic
//          two-shape form; accepted as an alternative authority)
//   O4 ontology.json >= 1024 bytes                              (CP-2 floor)
//   O5 signals/parameters structure sanity: >= 1 declared entry (canonical
//      signals buckets or flat parameters[])
//   O6 rag_deep_understanding.json parses (checked wherever present:
//      01_ontology/ per Phase 5, 00_input/ per the SKILL.md outputs table)
//   O7 CP-3: 00_input/clarification_needed.json carries clarification_status
//      AUTO_RESOLVED | USER_CONFIRMED
//   O8 hetero merge rule (only when 07_hetero/column_contract.json exists):
//      every HX-* contract column appears in the ontology and must never carry
//      physical_meaning_confidence=UNKNOWN (the deterministic mapping yields
//      KNOWN | INFERRED; HX-TXT-*-EVT-* event rows legitimately omit the field)
//
// Output: single machine-readable JSON verdict on stdout.

import { spawnSync } from 'child_process';
import { existsSync, readFileSync, statSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '..', '..', '..', '..');
const SHARED_DIR = join(REPO_ROOT, '.claude', 'shared');
const VALIDATE = join(SHARED_DIR, 'scripts', 'validate.mjs');
const CP2_SCHEMA = join(REPO_ROOT, '.claude', 'skills', 'industrial-ontology-builder', 'schemas', 'ontology_schema.json');
const SHARED_SCHEMA = join(SHARED_DIR, 'schemas', 'ontology_schema.json');

const args = process.argv.slice(2);
const argOf = (k) => {
  const i = args.indexOf(k);
  if (i >= 0) return args[i + 1];
  const pref = args.find((a) => a.startsWith(`${k}=`));
  return pref ? pref.slice(k.length + 1) : undefined;
};

const CHECKS = [];
const NOTES = [];
const check = (id, ok, detail = '') => CHECKS.push({ id, ok: !!ok, detail: String(detail) });
const note = (msg) => NOTES.push(msg);

function emit(verdict, exitCode, extra = {}) {
  const fails = CHECKS.filter((c) => !c.ok).map((c) => `${c.id}: ${c.detail || 'failed'}`);
  const out = {
    gate: 'ontology_quality_gate',
    verdict,
    checks: CHECKS,
    fails,
    notes: NOTES,
    summary: `${CHECKS.filter((c) => c.ok).length}/${CHECKS.length} checks passed`,
    ...extra,
  };
  console.log(JSON.stringify(out, null, 2));
  process.exit(exitCode);
}

// fail-closed: any unexpected error still emits a structured verdict
process.on('uncaughtException', (e) => {
  check('GATE', false, `unhandled error: ${e.message}`);
  emit('gate_fail', 3);
});

function validateAgainst(schemaPath, dataPath) {
  const r = spawnSync(process.execPath, [VALIDATE, schemaPath, dataPath], { encoding: 'utf-8', timeout: 60000 });
  let report = {};
  try { report = JSON.parse(r.stdout || '{}'); } catch { report = {}; }
  if (!r.stdout) return { ok: false, errors: [`validator produced no output (rc=${r.status})`] };
  return { ok: report.valid === true, errors: (report.errors || []).map((e) => `${e.path}: ${e.message}`) };
}

const readJson = (p) => JSON.parse(readFileSync(p, 'utf-8'));

// ───────────────────────────── inputs ─────────────────────────────
const runDirArg = argOf('--run-dir') || (args[0] && !args[0].startsWith('--') ? args[0] : undefined);
if (!runDirArg) {
  console.error('Usage: node quality_gate.mjs --run-dir <RUN_DIR>');
  process.exit(1);
}
const RUN_DIR = resolve(runDirArg);
if (!existsSync(RUN_DIR) || !statSync(RUN_DIR).isDirectory()) {
  check('GATE', false, `run dir not found: ${RUN_DIR}`);
  emit('hard_error', 1, { run_dir: RUN_DIR, reason: 'run dir does not exist or is not a directory' });
}

const ONT_DIR = join(RUN_DIR, '01_ontology');
if (!existsSync(ONT_DIR)) {
  console.log(JSON.stringify({
    gate: 'ontology_quality_gate',
    verdict: 'undetermined',
    run_dir: RUN_DIR,
    reason: '01_ontology absent — the ontology stage (CP-2/CP-3) did not run (or was removed)',
    checks: [],
    fails: [],
    notes: NOTES,
  }, null, 2));
  process.exit(2);
}

// ── O1/O2: existence + parse ──────────────────────────────────────
const ontPath = join(ONT_DIR, 'ontology.json');
const ontExists = existsSync(ontPath) && statSync(ontPath).isFile();
check('O1_ontology_exists', ontExists, ontExists ? ontPath : `missing ${ontPath}`);

let ont = null;
if (ontExists) {
  try {
    ont = readJson(ontPath);
    check('O2_ontology_parses', true);
  } catch (e) {
    check('O2_ontology_parses', false, `unparseable: ${e.message}`);
  }
} else {
  note('O2 skipped — ontology.json absent');
}

// ── O3: schema (at least one authority accepts) ───────────────────
if (ont) {
  const cp2 = validateAgainst(CP2_SCHEMA, ontPath);
  const shared = validateAgainst(SHARED_SCHEMA, ontPath);
  check('O3_ontology_schema_valid', cp2.ok || shared.ok,
    `cp2-schema=${cp2.ok ? 'valid' : `invalid (${cp2.errors.slice(0, 2).join('; ')})`}; ` +
    `shared-schema=${shared.ok ? 'valid' : `invalid (${shared.errors.slice(0, 2).join('; ')})`}`);
  if (cp2.ok && !shared.ok) note('ontology satisfies the CP-2 skill schema only (shared domain-agnostic schema rejects it — expected for v6.4 canonical-form runs)');
  if (!cp2.ok && shared.ok) note('ontology satisfies the shared domain-agnostic schema only (CP-2 skill schema rejects it — the ontology store publish gate may refuse this run)');
} else {
  note('O3 skipped — ontology.json unparseable/absent');
}

// ── O4: CP-2 size floor ───────────────────────────────────────────
if (ontExists) {
  const size = statSync(ontPath).size;
  check('O4_ontology_min_1kb', size >= 1024, `size=${size} bytes (CP-2 floor 1024)`);
}

// ── O5: signals/parameters non-empty ──────────────────────────────
if (ont) {
  const buckets = ont.signals && typeof ont.signals === 'object' ? ont.signals : {};
  const bucketNames = ['inspection_signals', 'process_parameters', 'control_variables', 'events', 'metadata_columns'];
  const declared = bucketNames
    .filter((k) => Array.isArray(buckets[k]))
    .map((k) => `${k}=${buckets[k].length}`)
    .join(', ');
  const bucketTotal = bucketNames.reduce((n, k) => n + (Array.isArray(buckets[k]) ? buckets[k].length : 0), 0);
  const flatTotal = Array.isArray(ont.parameters) ? ont.parameters.length : 0;
  check('O5_signals_non_empty', bucketTotal + flatTotal > 0,
    `no signal/parameter entries declared (signals: ${declared || 'none'}; parameters: ${Array.isArray(ont.parameters) ? ont.parameters.length : 'absent'})`);
}

// ── O6: rag_deep_understanding.json parses wherever present ───────
for (const rel of [join('01_ontology', 'rag_deep_understanding.json'), join('00_input', 'rag_deep_understanding.json')]) {
  const p = join(RUN_DIR, rel);
  if (!existsSync(p)) continue;
  try {
    readJson(p);
    check('O6_rag_deep_understanding_parses', true, `${rel} parses`);
  } catch (e) {
    check('O6_rag_deep_understanding_parses', false, `${rel} unparseable: ${e.message}`);
  }
}

// ── O7: CP-3 clarification gate ───────────────────────────────────
const clarPath = join(RUN_DIR, '00_input', 'clarification_needed.json');
if (!existsSync(clarPath)) {
  check('O7_clarification_status', false, 'missing 00_input/clarification_needed.json (CP-3)');
} else {
  try {
    const clar = readJson(clarPath);
    const status = clar && typeof clar === 'object' ? clar.clarification_status : undefined;
    const ok = status === 'AUTO_RESOLVED' || status === 'USER_CONFIRMED';
    check('O7_clarification_status', ok,
      ok ? `clarification_status=${status}` : `clarification_status=${JSON.stringify(status)} (CP-3 requires AUTO_RESOLVED|USER_CONFIRMED)`);
  } catch (e) {
    check('O7_clarification_status', false, `unparseable clarification_needed.json: ${e.message}`);
  }
}

// ── O8: heterogeneous column merge rule ───────────────────────────
const contractPath = join(RUN_DIR, '07_hetero', 'column_contract.json');
if (!existsSync(contractPath)) {
  note('O8 skipped — 07_hetero/column_contract.json absent (no heterogeneous sources this run)');
} else if (!ont) {
  note('O8 skipped — ontology.json unparseable; merge rule cannot be evaluated');
} else {
  let contract = null;
  try { contract = readJson(contractPath); } catch (e) {
    check('O8_hetero_merge', false, `07_hetero/column_contract.json unparseable: ${e.message}`);
  }
  if (contract) {
    const cols = Array.isArray(contract.columns) ? contract.columns.filter((c) => c && typeof c.column === 'string') : null;
    if (!cols) {
      check('O8_hetero_merge', false, 'column_contract.json has no columns[] array');
    } else if (cols.length === 0) {
      note('O8 note — column contract declares zero columns');
    } else {
      // index every ontology entry by column identifier across both shapes
      const index = new Map(); // name -> [{entry, bucket}]
      const add = (entry, bucket) => {
        if (!entry || typeof entry !== 'object') return;
        const key = (typeof entry.column === 'string' && entry.column) || (typeof entry.name === 'string' && entry.name) || null;
        if (!key) return;
        if (!index.has(key)) index.set(key, []);
        index.get(key).push({ entry, bucket });
      };
      const buckets = ont.signals && typeof ont.signals === 'object' ? ont.signals : {};
      for (const bucket of ['inspection_signals', 'process_parameters', 'control_variables', 'events', 'metadata_columns']) {
        if (!Array.isArray(buckets[bucket])) continue;
        for (const item of buckets[bucket]) {
          if (typeof item === 'string') add({ name: item }, bucket);
          else add(item, bucket);
        }
      }
      if (Array.isArray(ont.parameters)) for (const p of ont.parameters) add(p, 'parameters');

      const missing = [];
      const unknown = [];
      const missingConf = [];
      const badConf = [];
      for (const col of cols) {
        const name = col.column;
        if (!name.startsWith('HX-')) continue; // merge rule targets HX-* columns
        const hits = index.get(name) || [];
        if (hits.length === 0) { missing.push(name); continue; }
        const inEvents = hits.some((h) => h.bucket === 'events');
        let sawValid = false;
        for (const { entry } of hits) {
          const raw = entry.physical_meaning_confidence;
          if (raw === undefined || raw === null || raw === '') continue;
          const conf = String(raw).trim().toUpperCase();
          if (conf === 'UNKNOWN') unknown.push(`${name} (UNKNOWN is forbidden — contract merge must yield KNOWN|INFERRED)`);
          else if (conf === 'KNOWN' || conf === 'INFERRED') sawValid = true;
          else badConf.push(`${name}: physical_meaning_confidence=${JSON.stringify(raw)}`);
        }
        if (!sawValid && !unknown.some((u) => u.startsWith(`${name} (`)) && !inEvents) {
          missingConf.push(name);
        }
      }
      const fails = [];
      if (missing.length) fails.push(`HX columns absent from ontology (${missing.length}): ${missing.slice(0, 5).join(', ')}${missing.length > 5 ? ' (+more)' : ''}`);
      if (unknown.length) fails.push(`physical_meaning_confidence=UNKNOWN on HX columns: ${unknown.slice(0, 5).join('; ')}`);
      if (missingConf.length) fails.push(`HX columns without physical_meaning_confidence: ${missingConf.slice(0, 5).join(', ')}`);
      if (badConf.length) fails.push(`HX columns with non KNOWN|INFERRED confidence: ${badConf.slice(0, 5).join('; ')}`);
      check('O8_hetero_merge', fails.length === 0,
        fails.length ? fails.join(' | ') : `all ${cols.length} contract columns present (HX confidence KNOWN|INFERRED)`);
    }
  }
}

// ── verdict ───────────────────────────────────────────────────────
const allOk = CHECKS.every((c) => c.ok);
emit(allOk ? 'ok' : 'gate_fail', allOk ? 0 : 3, { run_dir: RUN_DIR });
