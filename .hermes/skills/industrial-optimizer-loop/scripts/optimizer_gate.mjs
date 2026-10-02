#!/usr/bin/env node
// optimizer_gate.mjs — deterministic guardrail gate O-G1..O-G8 for
// industrial-optimizer-loop. Exit 0 = all pass; exit 1 = at least one FAIL.
//
// O-G1  objective contract (goal=target <=> target_range; tolerance mutex; ...)
// O-G2  domain hard wall: every designed setpoint inside
//       factor[min,max] ∩ box constraints ∩ prior.factor_observed_ranges
// O-G3  data support: coded distance > 0.8 from all data (or boundary touch)
//       => extrapolation MUST be true
// O-G4  converged anti-fluke: m>=3 confirm replicates all in target window
//       AND one-sided 95% CI in limits AND D >= 0.8*D_max (state flags + raw
//       replicate values cross-checked) — <3 replicates or any out-of-window
//       with phase=converged is a FAIL
// O-G5  safety limits absolute priority: no designed point violates a
//       machine-readable safety constraint; safety_aborted => phase=aborted
//       + needs_human
// O-G6  result integrity: failed/safety_aborted trials carry failure_reason;
//       reported trial_ids must be designed
// O-G7  provenance: machine artifacts authored_by="script" + script_version
// O-G8  4-schema double validation (validate.mjs) + STRICT extra-keys + enum
//       literals read from .claude/shared/schemas/closedloop_enums.json
//       (single enum source, R9)

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
const runDir = args[0];
if (!runDir) {
  console.error('Usage: node optimizer_gate.mjs <run_dir> [--skill-path <skill>] [--shared-path <shared>]');
  process.exit(1);
}
function flag(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const skillPath = flag('--skill-path', path.resolve(HERE, '..'));
const sharedPath = flag('--shared-path',
  path.resolve(HERE, '..', '..', '..', '..', '.claude', 'shared'));

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail: String(detail || '') });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id}${ok ? '' : ' - ' + detail}`);
}

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}
function exists(p) { try { return fs.existsSync(p); } catch { return false; } }

const j = (...rel) => path.join(runDir, ...rel);
const manifest = readJson(j('run_manifest.json'));
const objective = readJson(j('00_input', 'objective.json'));
const state = readJson(j('01_state', 'optimizer_state.json'));
const enums = readJson(path.join(sharedPath, 'schemas', 'closedloop_enums.json'));

// ---------------------------------------------------------------- file presence
check('FILE_manifest', !!manifest, 'run_manifest.json missing');
check('FILE_objective', !!objective, '00_input/objective.json missing');
check('FILE_state', !!state, '01_state/optimizer_state.json missing');
if (!objective || !state) {
  console.log('[gate] cannot continue without objective/state');
  process.exit(1);
}
const phase = state.phase;
const roundDirs = exists(j('02_rounds'))
  ? fs.readdirSync(j('02_rounds')).filter((d) => /^R\d{3}$/.test(d)).sort()
  : [];
const rounds = roundDirs.map((rid) => ({
  rid,
  design: readJson(j('02_rounds', rid, 'trial_design.json')),
  result: readJson(j('02_rounds', rid, 'trial_result.json')),
}));

if (phase === 'converged') {
  for (const f of ['conclusions/optimization_conclusion.json',
    'conclusions/recipe.json', 'report.md']) {
    check(`FILE_${f.replace(/[/.]/g, '_')}`, exists(j(f)), `missing ${f}`);
  }
}

// ---------------------------------------------------------------- O-G1
(function og1() {
  const errs = [];
  const goal = objective.goal;
  const tr = objective.target_range;
  const tol = objective.tolerance;
  if (enums && !enums.optimizer.goals.includes(goal)) errs.push(`goal ${goal} not in closedloop enums`);
  if (goal === 'target') {
    if (!Array.isArray(tr) || tr.length !== 2 || tr.some((v) => typeof v !== 'number')) {
      errs.push('O-G1a: goal=target requires numeric target_range [lo, hi]');
    } else if (tr[0] > tr[1]) errs.push('O-G1a: target_range lo > hi');
    if (tol !== null && tol !== undefined) errs.push('O-G1a: tolerance mutually exclusive with goal=target');
  } else if (tr !== null && tr !== undefined) {
    errs.push('O-G1a: target_range only allowed when goal=target');
  }
  for (const f of objective.factors || []) {
    if (f.type === 'numeric') {
      if (!(typeof f.min === 'number' && typeof f.max === 'number' && f.min < f.max)) {
        errs.push(`factor ${f.name}: numeric requires min<max`);
      }
    } else if (f.type === 'categorical') {
      if (!Array.isArray(f.levels) || f.levels.length === 0) {
        errs.push(`factor ${f.name}: categorical requires levels`);
      }
    } else errs.push(`factor ${f.name}: bad type`);
  }
  const b = objective.budget || {};
  if (!(Number.isInteger(b.max_rounds) && b.max_rounds >= 1)) errs.push('budget.max_rounds invalid');
  if (!(Number.isInteger(b.max_trials) && b.max_trials >= 1)) errs.push('budget.max_trials invalid');
  if (objective.contract_version !== '1.0') errs.push('contract_version must be "1.0"');
  check('OG1_objective_contract', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- domain (O-G2)
function resolveDomain() {
  const boxes = {};
  for (const c of objective.constraints || []) {
    if (c.type === 'box' && c.factor) {
      const cur = boxes[c.factor] || [null, null];
      if (typeof c.min === 'number') cur[0] = cur[0] === null ? c.min : Math.max(cur[0], c.min);
      if (typeof c.max === 'number') cur[1] = cur[1] === null ? c.max : Math.min(cur[1], c.max);
      boxes[c.factor] = cur;
    }
  }
  const priorRanges = {};
  const prior = objective.prior || {};
  const cand = [];
  if (prior.doe_analyzer_run_dir) {
    cand.push(path.join(runDir, prior.doe_analyzer_run_dir, 'conclusions', 'recommendations.json'));
    cand.push(path.join(prior.doe_analyzer_run_dir, 'conclusions', 'recommendations.json'));
  }
  cand.push(j('00_input', 'recommendations.json'));
  for (const p of cand) {
    const recs = exists(p) ? readJson(p) : null;
    if (recs) {
      Object.assign(priorRanges, (recs.applicability_domain || {}).factor_observed_ranges || {});
      break;
    }
  }
  const dom = {};
  for (const f of objective.factors || []) {
    if (f.type === 'categorical') { dom[f.name] = { levels: f.levels }; continue; }
    let lo = f.min; let hi = f.max;
    const bc = boxes[f.name];
    if (bc) { if (bc[0] !== null) lo = Math.max(lo, bc[0]); if (bc[1] !== null) hi = Math.min(hi, bc[1]); }
    const pr = priorRanges[f.name];
    if (pr && typeof pr.min === 'number' && typeof pr.max === 'number' && pr.min < pr.max
        && pr.min <= hi && pr.max >= lo) {
      lo = Math.max(lo, pr.min); hi = Math.min(hi, pr.max);
    }
    dom[f.name] = { lo, hi };
  }
  return dom;
}
const domain = resolveDomain();
const numericNames = (objective.factors || []).filter((f) => f.type === 'numeric').map((f) => f.name);
const coded = (sp) => {
  const out = {};
  numericNames.forEach((f, i) => {
    const d = domain[f];
    out[`x${i}`] = 2 * (Number(sp[f]) - d.lo) / (d.hi - d.lo) - 1;
  });
  return out;
};

(function og2() {
  const errs = [];
  for (const { rid, design } of rounds) {
    if (!design) continue;
    for (const t of design.trials || []) {
      for (const [f, spec] of Object.entries(domain)) {
        const v = (t.setpoints || {})[f];
        if (v === undefined || v === null) { errs.push(`${rid}/${t.trial_id}: missing ${f}`); continue; }
        if (spec.levels) {
          if (!spec.levels.includes(v)) errs.push(`${rid}/${t.trial_id}: ${f}=${v} not a declared level`);
        } else if (!(Number(v) >= spec.lo - 1e-9 && Number(v) <= spec.hi + 1e-9)) {
          errs.push(`${rid}/${t.trial_id}: ${f}=${v} outside domain [${spec.lo}, ${spec.hi}] (O-G2)`);
        }
      }
    }
  }
  check('OG2_domain_wall', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G3
(function og3() {
  const errs = [];
  const NEIGHBORHOOD = (enums && enums.optimizer.constants.neighborhood_coded) || 0.8;
  const dataCoded = [];
  const isBoundary = (c) => Object.values(c).some((v) => Math.abs(v) >= 1 - 1e-9);
  for (const { rid, design, result } of rounds) {
    if (!design) continue;
    for (const t of design.trials || []) {
      if (dataCoded.length === 0) continue; // first data-less round: nothing to compare
      const c = coded(t.setpoints || {});
      let dmin = Infinity;
      for (const d of dataCoded) {
        const dist = Math.sqrt(numericNames.reduce((s, _f, i) => {
          const dv = (c[`x${i}`] || 0) - (d[`x${i}`] || 0); return s + dv * dv;
        }, 0));
        dmin = Math.min(dmin, dist);
      }
      const unsupported = dmin > NEIGHBORHOOD || isBoundary(c);
      if (unsupported && t.extrapolation !== true) {
        errs.push(`${rid}/${t.trial_id}: unsupported (nearest coded ${dmin.toFixed(3)}) but extrapolation=${t.extrapolation} (O-G3)`);
      }
    }
    if (result) {
      const byId = Object.fromEntries((design.trials || []).map((t) => [t.trial_id, t]));
      for (const rt of result.trials || []) {
        if (!['completed', 'partial'].includes(rt.status)) continue;
        const dt = byId[rt.trial_id];
        if (dt && dt.setpoints) dataCoded.push(coded(dt.setpoints));
      }
    }
  }
  check('OG3_support_flagged', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G4
(function og4() {
  if (phase !== 'converged') { check('OG4_converged_dual_gate', true, 'phase != converged (n/a)'); return; }
  const errs = [];
  const confirm = [...rounds].reverse().find(
    ({ design }) => design && design.method === 'confirm_replicates');
  if (!confirm) { errs.push('phase=converged but no confirm_replicates round found'); }
  else {
    const { rid, design, result } = confirm;
    const confTrial = (design.trials || []).find(
      (t) => t.method === undefined || true); // single confirm trial
    const rTrial = result && ((result.trials || []).find(
      (t) => t.trial_id === (confTrial || {}).trial_id) || (result.trials || [])[0]);
    const metric = objective.target_metric;
    const vals = (((rTrial || {}).measurements || {})[metric] || []).filter(
      (v) => typeof v === 'number');
    if (vals.length < 3) errs.push(`${rid}: only ${vals.length} confirm replicate value(s), need >= 3 (O-G4)`);
    if (objective.goal === 'target') {
      const [lo, hi] = objective.target_range;
      const outside = vals.filter((v) => v < lo || v > hi);
      if (outside.length > 0) errs.push(`${rid}: ${outside.length} replicate(s) outside target_range (O-G4)`);
    }
  }
  const ts = state.target_status || {};
  if (ts.ci_in_limits !== true) errs.push('state.target_status.ci_in_limits is not true (O-G4)');
  if (ts.desirability_gate !== true) errs.push('state.target_status.desirability_gate is not true (O-G4)');
  check('OG4_converged_dual_gate', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G5
(function og5() {
  const errs = [];
  const safety = (objective.constraints || []).filter((c) => c.type === 'safety');
  for (const { rid, design } of rounds) {
    if (!design) continue;
    for (const t of design.trials || []) {
      for (const c of safety) {
        if (!c.factor) continue; // expr-only safety: agent review, not machine
        const v = Number((t.setpoints || {})[c.factor]);
        if (Number.isNaN(v)) continue;
        if (typeof c.min === 'number' && v < c.min - 1e-9) {
          errs.push(`${rid}/${t.trial_id}: ${c.factor}=${v} violates safety min ${c.min} (O-G5)`);
        }
        if (typeof c.max === 'number' && v > c.max + 1e-9) {
          errs.push(`${rid}/${t.trial_id}: ${c.factor}=${v} violates safety max ${c.max} (O-G5)`);
        }
      }
    }
  }
  let aborted = false;
  for (const { result } of rounds) {
    for (const rt of (result || {}).trials || []) {
      if (rt.status === 'safety_aborted') aborted = true;
    }
  }
  if (aborted) {
    if (state.phase !== 'aborted') errs.push('safety_aborted trial present but state.phase != aborted (O-G5)');
    if ((state.next_action || {}).recommendation !== 'needs_human') {
      errs.push('safety_aborted trial present but next_action != needs_human (O-G5)');
    }
  }
  check('OG5_safety_absolute', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G6
(function og6() {
  const errs = [];
  for (const { rid, design, result } of rounds) {
    if (!design) { if (result) errs.push(`${rid}: result without design`); continue; }
    if (result) {
      if (result.round_id !== rid) errs.push(`${rid}: result.round_id mismatch`);
      const ids = new Set((design.trials || []).map((t) => t.trial_id));
      for (const rt of result.trials || []) {
        if (!ids.has(rt.trial_id)) errs.push(`${rid}: ${rt.trial_id} not in design`);
        if (['failed', 'safety_aborted'].includes(rt.status)
            && !(rt.failure_reason || '').trim()) {
          errs.push(`${rid}/${rt.trial_id}: ${rt.status} without failure_reason (O-G6b)`);
        }
      }
    }
  }
  check('OG6_result_integrity', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G7
(function og7() {
  const errs = [];
  if (state.provenance?.authored_by !== 'script') errs.push('state.provenance.authored_by != "script"');
  if (!state.provenance?.script_version) errs.push('state.provenance.script_version missing');
  for (const { rid, design } of rounds) {
    if (!design) continue;
    if (design.provenance?.authored_by !== 'script') errs.push(`${rid}: design authored_by != "script"`);
    if (!design.provenance?.script_version) errs.push(`${rid}: design script_version missing`);
  }
  check('OG7_provenance_script', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- O-G8
const SCHEMA_MAP = {
  '00_input/objective.json': 'objective.schema.json',
  '01_state/optimizer_state.json': 'optimizer_state.schema.json',
};
for (const { rid } of rounds) {
  SCHEMA_MAP[`02_rounds/${rid}/trial_design.json`] = 'trial_design.schema.json';
  SCHEMA_MAP[`02_rounds/${rid}/trial_result.json`] = 'trial_result.schema.json';
}
(function og8_schema() {
  const validateMjs = path.join(sharedPath, 'scripts', 'validate.mjs');
  const errs = [];
  for (const [rel, schemaName] of Object.entries(SCHEMA_MAP)) {
    const dataPath = j(rel);
    if (!exists(dataPath)) continue; // trial_result may legitimately be absent
    const schemaPath = path.join(skillPath, 'schemas', schemaName);
    if (!exists(schemaPath)) { errs.push(`schema missing: ${schemaName}`); continue; }
    try {
      const out = execFileSync('node', [validateMjs, schemaPath, dataPath],
        { encoding: 'utf8', timeout: 60000 });
      const report = JSON.parse(out || '{}');
      const errList = report.errors || [];
      if (errList.length > 0) {
        errs.push(`${rel}: ${errList.slice(0, 2).map((e) => e.message || JSON.stringify(e)).join('; ')}`);
      }
    } catch (e) {
      const msg = (e.stdout && e.stdout.slice(0, 200)) || e.message || String(e);
      errs.push(`${rel}: validate.mjs failed (${String(msg).replace(/\s+/g, ' ').slice(0, 160)})`);
    }
  }
  check('OG8_schema_valid', errs.length === 0, errs.slice(0, 4).join('; '));
})();

(function og8_strict() {
  const errs = [];
  function strictWalk(inst, sch, at) {
    if (!sch || typeof inst !== 'object' || inst === null) return;
    if (Array.isArray(inst)) {
      if (sch.items) inst.forEach((v, i) => strictWalk(v, sch.items, `${at}[${i}]`));
      return;
    }
    const props = sch.properties || {};
    const patternKeys = Object.keys(sch.patternProperties || {});
    if (!sch.additionalProperties && Object.keys(props).length > 0) {
      for (const key of Object.keys(inst)) {
        const ok = Object.prototype.hasOwnProperty.call(props, key)
          || patternKeys.some((p) => { try { return new RegExp(p).test(key); } catch { return false; } });
        if (!ok) errs.push(`${at}.${key} not in schema (strict extra-keys)`);
      }
    }
    for (const [key, val] of Object.entries(inst)) {
      if (Object.prototype.hasOwnProperty.call(props, key)) strictWalk(val, props[key], `${at}.${key}`);
    }
  }
  for (const [rel, schemaName] of Object.entries(SCHEMA_MAP)) {
    const inst = readJson(j(rel));
    const sch = readJson(path.join(skillPath, 'schemas', schemaName));
    if (inst && sch) strictWalk(inst, sch, rel);
  }
  check('OG8_strict_keys', errs.length === 0, errs.slice(0, 4).join('; '));
})();

(function og8_enums() {
  const errs = [];
  if (enums) {
    if (!enums.optimizer.phases.includes(state.phase)) errs.push(`state.phase ${state.phase} not in closedloop enums`);
    if (state.next_action && !enums.optimizer.next_actions.includes(state.next_action.recommendation)) {
      errs.push(`next_action ${state.next_action.recommendation} not in closedloop enums`);
    }
    for (const { rid, design } of rounds) {
      if (!design) continue;
      if (!enums.optimizer.methods.includes(design.method)) errs.push(`${rid}: method ${design.method} not in enums`);
      if (!['explore', 'exploit', 'confirm'].includes(design.phase)) errs.push(`${rid}: design.phase ${design.phase} invalid`);
      for (const t of design.trials || []) {
        if (t.trial_id !== `${rid}-T${String((design.trials || []).indexOf(t) + 1).padStart(2, '0')}`) {
          errs.push(`${rid}: trial_id ${t.trial_id} does not match Rxxx-Tnn pattern order`);
        }
      }
    }
    for (const { result } of rounds) {
      for (const rt of (result || {}).trials || []) {
        if (!enums.optimizer.trial_status.includes(rt.status)) errs.push(`trial status ${rt.status} not in enums`);
      }
    }
  } else errs.push('closedloop_enums.json unreadable');
  check('OG8_enum_literals', errs.length === 0, errs.slice(0, 4).join('; '));
})();

// ---------------------------------------------------------------- summary
const failed = results.filter((r) => !r.ok);
console.log(`\n[gate] ${results.length - failed.length}/${results.length} passed`
  + (failed.length ? ` — FAILED: ${failed.map((r) => r.id).join(', ')}` : ' — ALL PASS'));
process.exit(failed.length ? 1 : 0);
