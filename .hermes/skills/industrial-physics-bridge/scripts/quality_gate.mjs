#!/usr/bin/env node
// quality_gate.mjs — industrial-physics-bridge deterministic quality gate.
// Gates the E5 artifact enhancement/physics_bridge.json (five-item physics
// verifications + mechanism chains + competing explanations + evidence gaps).
// Zero dependencies (node builtins only; validate.mjs is spawned, never imported).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR>
// Exit: 0 ok | 1 hard error (bad inputs / usage) | 2 undetermined (the
//       enhancement/ stage dir is absent — the E-stage did not run)
//       | 3 gate-fail (any check failed)
//
// Checks (all mechanical):
//   B1 enhancement/physics_bridge.json exists
//   B2 it parses
//   B3 it validates against .claude/shared/schemas/physics_bridge_schema.json
//   B4 five-item verification enums per relationship_verifications[]:
//        direction/functional_form/time_lag ∈ MATCH|MISMATCH|UNTESTED
//        magnitude                          ∈ PLAUSIBLE|STRONG|IMPLAUSIBLE|UNTESTED
//        state_dependence                   ∈ STABLE|STATE_DEPENDENT|REVERSES|UNTESTED
//   B5 direction=MISMATCH ⇒ overall_status=inconsistent (SKILL.md overall-status
//      rule: direction mismatch is the critical diagnostic signal)
//   B6 mechanism chains: unique chain_id matching MC-NNN; when
//      04_diagnostics/diagnosis.json is present, every surviving hypothesis
//      produces one mechanism chain (AC-2 contract)
//   B7 AC-2 direction rule (when 01_ontology/ontology.json is present): a
//      relationship flagged data_direction_validated=false must yield
//      direction=MISMATCH in its verification
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
const SCHEMA = join(SHARED_DIR, 'schemas', 'physics_bridge_schema.json');

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
  console.log(JSON.stringify({
    gate: 'physics_bridge_quality_gate',
    verdict,
    checks: CHECKS,
    fails,
    notes: NOTES,
    summary: `${CHECKS.filter((c) => c.ok).length}/${CHECKS.length} checks passed`,
    ...extra,
  }, null, 2));
  process.exit(exitCode);
}

// fail-closed: any unexpected error still emits a structured verdict
process.on('uncaughtException', (e) => {
  check('GATE', false, `unhandled error: ${e.message}`);
  emit('gate_fail', 3);
});

function validateAgainst(schemaPath, dataPath) {
  const r = spawnSync(process.execPath, [VALIDATE, schemaPath, dataPath], { encoding: 'utf-8', timeout: 60000 });
  if (!r.stdout) return { ok: false, errors: [`validator produced no output (rc=${r.status})`] };
  let report = {};
  try { report = JSON.parse(r.stdout); } catch { return { ok: false, errors: ['validator output unparseable'] }; }
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

const ENH_DIR = join(RUN_DIR, 'enhancement');
if (!existsSync(ENH_DIR) || !statSync(ENH_DIR).isDirectory()) {
  console.log(JSON.stringify({
    gate: 'physics_bridge_quality_gate',
    verdict: 'undetermined',
    run_dir: RUN_DIR,
    reason: 'enhancement/ absent — the enhancement stage (E5 physics bridge) did not run (or was removed)',
    checks: [],
    fails: [],
    notes: NOTES,
  }, null, 2));
  process.exit(2);
}

// ── B1/B2: existence + parse ──────────────────────────────────────
const bridgePath = join(ENH_DIR, 'physics_bridge.json');
if (!existsSync(bridgePath) || !statSync(bridgePath).isFile()) {
  check('B1_bridge_exists', false, `missing ${join('enhancement', 'physics_bridge.json')} (enhancement/ exists — E5 produced no output)`);
  emit('gate_fail', 3, { run_dir: RUN_DIR });
}
check('B1_bridge_exists', true, `enhancement/physics_bridge.json (${statSync(bridgePath).size} bytes)`);

let bridge = null;
try {
  bridge = readJson(bridgePath);
  check('B2_bridge_parses', true);
} catch (e) {
  check('B2_bridge_parses', false, `unparseable: ${e.message}`);
  emit('gate_fail', 3, { run_dir: RUN_DIR });
}

// ── B3: schema ────────────────────────────────────────────────────
{
  const r = validateAgainst(SCHEMA, bridgePath);
  check('B3_schema_valid', r.ok, r.ok ? '' : r.errors.slice(0, 4).join('; '));
}

const verifications = Array.isArray(bridge.relationship_verifications) ? bridge.relationship_verifications : [];

// ── B4: five-item enum literals ───────────────────────────────────
{
  const ENUMS = {
    direction: ['MATCH', 'MISMATCH', 'UNTESTED'],
    functional_form: ['MATCH', 'MISMATCH', 'UNTESTED'],
    time_lag: ['MATCH', 'MISMATCH', 'UNTESTED'],
    magnitude: ['PLAUSIBLE', 'STRONG', 'IMPLAUSIBLE', 'UNTESTED'],
    state_dependence: ['STABLE', 'STATE_DEPENDENT', 'REVERSES', 'UNTESTED'],
  };
  const bad = [];
  verifications.forEach((v, i) => {
    for (const [field, allowed] of Object.entries(ENUMS)) {
      const val = v && v[field];
      if (typeof val !== 'string' || !allowed.includes(val)) {
        bad.push(`[${i}] ${v && v.predictor}→${v && v.target} ${field}=${JSON.stringify(val)}`);
      }
    }
  });
  check('B4_five_item_enums', bad.length === 0,
    bad.length ? `${bad.length} invalid five-item value(s): ${bad.slice(0, 4).join('; ')}` : `${verifications.length} verification(s) checked`);
}

// ── B5: direction=MISMATCH ⇒ overall_status=inconsistent ──────────
{
  const bad = [];
  verifications.forEach((v, i) => {
    if (v && v.direction === 'MISMATCH' && v.overall_status !== 'inconsistent') {
      bad.push(`[${i}] ${v.predictor}→${v.target} direction=MISMATCH but overall_status=${JSON.stringify(v.overall_status)}`);
    }
  });
  check('B5_mismatch_status_rule', bad.length === 0,
    bad.length ? bad.slice(0, 4).join('; ') : 'no direction-mismatch status violations');
}

// ── B6: mechanism chains (uniqueness + AC-2 surviving-hypothesis rule) ──
{
  const chains = Array.isArray(bridge.mechanism_chains) ? bridge.mechanism_chains : [];
  const ids = chains.map((c) => c && c.chain_id);
  const badFormat = ids.filter((id) => typeof id !== 'string' || !/^MC-\d{3}$/.test(id));
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  const errs = [];
  if (badFormat.length) errs.push(`chain_id not matching MC-NNN: ${badFormat.slice(0, 4).join(', ')}`);
  if (dupes.length) errs.push(`duplicate chain_id: ${[...new Set(dupes)].join(', ')}`);

  const diagPath = join(RUN_DIR, '04_diagnostics', 'diagnosis.json');
  if (existsSync(diagPath)) {
    try {
      const diag = readJson(diagPath);
      const surviving = diag && diag.hypotheses && Array.isArray(diag.hypotheses.surviving) ? diag.hypotheses.surviving : [];
      if (surviving.length > 0 && chains.length < surviving.length) {
        errs.push(`AC-2: ${surviving.length} surviving hypothesis(es) but only ${chains.length} mechanism chain(s)`);
      }
    } catch (e) {
      note(`B6 note — 04_diagnostics/diagnosis.json unparseable (${e.message}); surviving-hypothesis count not checked`);
    }
  } else {
    note('B6 note — 04_diagnostics/diagnosis.json absent; surviving-hypothesis count not checked');
  }
  check('B6_mechanism_chains', errs.length === 0,
    errs.length ? errs.join('; ') : `${chains.length} chain(s), ids well-formed`);
}

// ── B7: AC-2 ontology direction rule ──────────────────────────────
{
  const ontPath = join(RUN_DIR, '01_ontology', 'ontology.json');
  if (!existsSync(ontPath)) {
    note('B7 skipped — 01_ontology/ontology.json absent; AC-2 direction rule not cross-checked');
  } else {
    try {
      const ont = readJson(ontPath);
      const idx = new Map();
      for (const rel of Array.isArray(ont.relationships) ? ont.relationships : []) {
        if (rel && typeof rel.from === 'string' && typeof rel.to === 'string') idx.set(`${rel.from}\u0000${rel.to}`, rel);
      }
      const bad = [];
      for (const v of verifications) {
        const rel = v ? idx.get(`${v.predictor}\u0000${v.target}`) : undefined;
        if (!rel) continue;
        const dirValidated = String(rel.data_direction_validated ?? '').trim().toLowerCase();
        if (dirValidated === 'false' && v.direction !== 'MISMATCH') {
          bad.push(`${v.predictor}→${v.target}: ontology data_direction_validated=false but direction=${JSON.stringify(v.direction)}`);
        }
      }
      check('B7_ontology_direction_rule', bad.length === 0,
        bad.length ? `AC-2 violation(s): ${bad.slice(0, 4).join('; ')}` : 'AC-2 direction rule holds for all ontology-matched relationships');
    } catch (e) {
      note(`B7 note — ontology.json unparseable (${e.message}); AC-2 direction rule not cross-checked`);
    }
  }
}

// ── verdict ───────────────────────────────────────────────────────
const allOk = CHECKS.every((c) => c.ok);
emit(allOk ? 'ok' : 'gate_fail', allOk ? 0 : 3, {
  run_dir: RUN_DIR,
  relationship_verifications: verifications.length,
  mechanism_chains: Array.isArray(bridge.mechanism_chains) ? bridge.mechanism_chains.length : 0,
});
