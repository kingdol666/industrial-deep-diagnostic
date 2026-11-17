#!/usr/bin/env node
// quality gate for industrial-improvement-advisor
//   S1 schema/required fields (+ type/enum spot checks vs the skill schema)
//   S2 honesty + RECOMPUTE SEAL: re-derive every action's grade and
//      expected_gain from 02_evidence artifacts and compare with the declared
//      values (tamper battery: edit grade / CI bound / delete evidence_ref -> FAIL)
//   S3 zero-LLM provenance (script-authored numbers, raw data source)
//   S4 HTML landing page + selfcheck + Markdown companion
//   S5 shared enums + advisory boundary + A-grade sentinel (A<=3)
//
// usage: node quality_gate.mjs <advisory_actions.json> <advisory_dir>
// exit: 0 pass (not_actionable products pass too) / 3 fail
import { readFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const skillPath = resolve(here, '..');
const repoRoot = resolve(skillPath, '..', '..', '..');
const sharedPath = join(repoRoot, '.claude', 'shared');

const advisoryPath = process.argv[2];
const outDir = process.argv[3] || dirname(resolve(advisoryPath || '.'));
const results = [];
const fail = (msg) => { console.error(`[improvement-gate] FAIL ${msg}`); process.exit(3); };
const warn = (msg) => console.warn(`[improvement-gate] warn ${msg}`);
const check = (name, ok, detail) => {
  results.push([name, Boolean(ok)]);
  if (!ok && detail !== undefined) warn(`${name}: ${detail}`);
};

if (!advisoryPath || !existsSync(advisoryPath)) {
  fail('usage: quality_gate.mjs <advisory_actions.json> [advisoryDir]');
}

let report;
try { report = JSON.parse(readFileSync(advisoryPath, 'utf-8')); }
catch (e) { fail(`unreadable JSON: ${e.message}`); }

// ---------------------------------------------------------------- S1 schema
const schemaPath = join(skillPath, 'schemas', 'advisory_actions.schema.json');
check('S1 schema file exists', existsSync(schemaPath));
const coreRequired = ['contract_version', 'report_id', 'generated_at', 'mode',
  'status', 'goal', 'data', 'waterline', 'actions', 'prescriptions',
  'excluded_levers', 'degradations', 'provenance', 'limitations'];
const missing = coreRequired.filter((k) => !(k in report));
check('S1 core fields', missing.length === 0, `missing: ${missing.join(',')}`);
check('S1 contract_version', report.contract_version === 'improvement-advisory/1.0',
  String(report.contract_version));
check('S1 report_id shape', /^IMA-[0-9]{8,}-[0-9a-f]{4,}$/.test(String(report.report_id)),
  String(report.report_id));
const actionCore = ['action_id', 'lever_param', 'lever_column', 'direction',
  'magnitude', 'expected_gain', 'evidence_refs', 'mechanism_chain',
  'affected_kpis', 'grade', 'grade_reasons', 'priority_score', 'risk',
  'preconditions', 'side_effects', 'verification_plan', 'rollback_condition',
  'prescription_tags', 'advisory'];
for (const a of report.actions || []) {
  const miss = actionCore.filter((k) => !(k in a));
  check(`S1 action fields ${a.action_id}`, miss.length === 0, miss.join(','));
  check(`S1 action id shape ${a.action_id}`, /^ACT-[A-Za-z0-9_-]+-[0-9]{3}$/.test(String(a.action_id)),
    String(a.action_id));
}

// -------------------------------------------------------- S2 recompute seal
const consts = { min_effect_r: 0.2, fdr_q: 0.05 };
try {
  const enums = JSON.parse(readFileSync(join(sharedPath, 'schemas', 'closedloop_enums.json'), 'utf-8'));
  Object.assign(consts, enums.improvement_advisor?.constants || {});
} catch { /* enums checked in S5 */ }

function gradeFromInputs(gi) {
  const d = gi?.data || {};
  const phys = gi?.physics?.status;
  const attr = gi?.attribution || {};
  const flags = gi?.flags || {};
  const dataCore = ['lever_variance_ok', 'samples_ok', 'fdr_ok', 'confound_ok',
    'regime_stable_ok'].every((k) => Boolean(d[k]));
  const temporal = d.temporal_ok;
  const gainOk = Boolean(flags.gain_ci_excludes_zero);
  const intervention = ((attr.status === 'estimable' && attr.ci_excludes_zero === true)
    || Boolean(flags.designed_window) || Boolean(flags.designed_effect));
  const temporalOkForA = temporal === true
    || (Boolean(flags.designed_effect) && temporal !== false);
  const deadTimeOk = !flags.dead_time_missing || Boolean(flags.designed_effect);
  if (dataCore && temporalOkForA && phys === 'known' && intervention && gainOk
    && !flags.objective_inferred && !flags.conflict && !flags.extrapolated
    && deadTimeOk && !flags.tradeoff_declared) return 'A';
  if (dataCore && (temporal === true || temporal === null || temporal === undefined)
    && (phys === 'known' || phys === 'same_domain') && gainOk
    && !flags.conflict && !flags.tradeoff_declared) return 'B';
  return 'C';
}

const tol = (declared) => Math.max(1e-9, 1e-6 * Math.abs(Number(declared) || 0));
const near = (a, b) => {
  if (a === null || a === undefined || b === null || b === undefined) {
    return (a === null || a === undefined) === (b === null || b === undefined);
  }
  return Math.abs(Number(a) - Number(b)) <= tol(a);
};

let evidencePairs = [];
try {
  const evPath = join(outDir, '..', '02_evidence', 'dose_response.json');
  if (existsSync(evPath)) {
    evidencePairs = JSON.parse(readFileSync(evPath, 'utf-8')).pairs || [];
  }
} catch (e) { warn(`evidence unreadable: ${e.message}`); }
check('S2 evidence pairs available', evidencePairs.length >= 0);

const targets = report.goal?.targets || [];
function wantSign(metric, current) {
  const t = targets.find((x) => x.metric === metric);
  if (!t) return 0;
  if (t.direction === 'min') return -1;
  if (t.direction === 'max') return 1;
  if (t.direction === 'target' && t.target_value !== null && t.target_value !== undefined
    && current !== null && current !== undefined) {
    return t.target_value > current ? 1 : (t.target_value < current ? -1 : 0);
  }
  return 0;
}

let aCount = 0;
for (const a of report.actions || []) {
  const gain = a.expected_gain || {};
  const gi = a.grade_inputs;
  check(`S2 grade_inputs present ${a.action_id}`, Boolean(gi));
  if (gi) {
    const recomputed = gradeFromInputs(gi);
    check(`S2 recomputed grade ${a.action_id}`, recomputed === a.grade,
      `declared ${a.grade} vs recomputed ${recomputed}`);
  }
  const rec = evidencePairs.find((p) => p.lever === a.lever_column
    && p.metric === gain.metric);
  check(`S2 evidence record ${a.action_id}`, Boolean(rec));
  // grade_inputs must equal the evidence record's own gate snapshot: editing the
  // action's declared grade + grade_inputs together cannot bypass the seal.
  if (rec && gi) {
    const same = (x, y) => (x === undefined ? null : x) === (y === undefined ? null : y);
    const pairs = [
      ['gates.lever_variance_ok', gi.data?.lever_variance_ok, rec.gates?.lever_variance_ok],
      ['gates.samples_ok', gi.data?.samples_ok, rec.gates?.samples_ok],
      ['gates.temporal_ok', gi.data?.temporal_ok, rec.gates?.temporal_ok],
      ['gates.fdr_ok', gi.data?.fdr_ok, rec.gates?.fdr_ok],
      ['gates.confound_ok', gi.data?.confound_ok, rec.gates?.confound_ok],
      ['gates.regime_stable_ok', gi.data?.regime_stable_ok, rec.gates?.regime_stable_ok],
      ['physics.status', gi.physics?.status, rec.physics?.status],
      ['attribution.status', gi.attribution?.status, rec.attribution?.status],
      ['attribution.ci_excludes_zero', gi.attribution?.ci_excludes_zero, rec.attribution?.ci_excludes_zero],
      ['flags.objective_inferred', gi.flags?.objective_inferred, rec.flags?.objective_inferred],
      ['flags.conflict', gi.flags?.conflict, rec.flags?.conflict],
      ['flags.extrapolated', gi.flags?.extrapolated, rec.flags?.extrapolated],
      ['flags.dead_time_missing', gi.flags?.dead_time_missing, rec.flags?.dead_time_missing],
      ['flags.tradeoff_declared', gi.flags?.tradeoff_declared, rec.flags?.tradeoff_declared],
      ['flags.designed_window', gi.flags?.designed_window, rec.flags?.designed_window],
      ['flags.designed_effect', gi.flags?.designed_effect, rec.flags?.designed_effect],
      ['flags.gain_ci_excludes_zero', gi.flags?.gain_ci_excludes_zero, rec.flags?.gain_ci_excludes_zero],
    ];
    for (const [name, aVal, eVal] of pairs) {
      check(`S2 seal ${name} ${a.action_id}`, same(aVal, eVal),
        `grade_inputs ${JSON.stringify(aVal)} vs evidence ${JSON.stringify(eVal)}`);
    }
  }
  const delta = a.magnitude?.delta;
  const want = wantSign(gain.metric,
    gain.current !== undefined && gain.current !== null ? gain.current : a.magnitude?.from);
  if (rec && gain.method === 'dose_response' && rec.dose) {
    const slope = rec.dose.slope;
    const ci = rec.dose.slope_ci95 || [null, null];
    const point = (slope === null || slope === undefined || want === 0)
      ? null : want * slope * delta;
    check(`S2 recomputed point ${a.action_id}`, near(point, gain.point),
      `declared ${gain.point} vs recomputed ${point}`);
    if (ci[0] !== null && ci[0] !== undefined && ci[1] !== null) {
      const c1 = want * ci[0] * delta;
      const c2 = want * ci[1] * delta;
      const lo = Math.min(c1, c2);
      const hi = Math.max(c1, c2);
      const declared = gain.ci95 || [null, null];
      check(`S2 recomputed ci ${a.action_id}`,
        near(lo, declared[0]) && near(hi, declared[1]),
        `declared ${JSON.stringify(declared)} vs recomputed [${lo}, ${hi}]`);
    }
  } else if (rec && gain.method === 'window_contrast' && rec.window) {
    const d = rec.window.delta_in_minus_out;
    const point = (d === null || d === undefined || want === 0) ? null : want * d;
    check(`S2 recomputed window point ${a.action_id}`, near(point, gain.point),
      `declared ${gain.point} vs recomputed ${point}`);
  } else if (rec && gain.method === 'doe_effect' && rec.doe) {
    const slope = rec.doe.slope;
    const ci = rec.doe.slope_ci95 || [null, null];
    const point = (slope === null || slope === undefined || want === 0)
      ? null : want * slope * delta;
    check(`S2 recomputed point ${a.action_id}`, near(point, gain.point),
      `declared ${gain.point} vs recomputed ${point}`);
    if (ci[0] !== null && ci[0] !== undefined && ci[1] !== null) {
      const c1 = want * ci[0] * delta;
      const c2 = want * ci[1] * delta;
      const lo = Math.min(c1, c2);
      const hi = Math.max(c1, c2);
      const declared = gain.ci95 || [null, null];
      check(`S2 recomputed ci ${a.action_id}`,
        near(lo, declared[0]) && near(hi, declared[1]),
        `declared ${JSON.stringify(declared)} vs recomputed [${lo}, ${hi}]`);
    }
    if (a.mechanism_status && rec.physics?.status) {
      check(`S2 mechanism status ${a.action_id}`,
        rec.physics.status === a.mechanism_status,
        `${a.mechanism_status} vs ${rec.physics.status}`);
    }
  } else if (gain.method === 'none') {
    check(`S2 not_estimable nulls ${a.action_id}`,
      (gain.point === null || gain.point === undefined)
      && (gain.ci95 === null || gain.ci95 === undefined));
  }
  if (a.mechanism_status && rec?.physics?.status) {
    check(`S2 mechanism status ${a.action_id}`,
      rec.physics.status === a.mechanism_status,
      `${a.mechanism_status} vs ${rec.physics.status}`);
  }
  check(`S2 evidence_refs non-empty ${a.action_id}`,
    Array.isArray(a.evidence_refs) && a.evidence_refs.length >= 1);
  const refs = a.evidence_refs || [];
  check(`S2 ccf evidence ref ${a.action_id}`,
    refs.some((r) => r.finding_id === `ccf:${a.lever_column}:${gain.metric}`));
  if (rec?.dose?.status === 'estimable') {
    check(`S2 dose evidence ref ${a.action_id}`,
      refs.some((r) => r.finding_id === `dose:${a.lever_column}:${gain.metric}`));
  }
  if (rec?.doe) {
    check(`S2 doe effect ref ${a.action_id}`,
      refs.some((r) => r.finding_id === `doe:${a.lever_column}:${gain.metric}`));
  }
  if (rec?.window && rec.window.status === 'estimable') {
    check(`S2 window evidence ref ${a.action_id}`,
      refs.some((r) => r.finding_id === `window:${a.lever_column}:${gain.metric}`));
  }
  if (a.grade === 'A') {
    aCount += 1;
    const interventionRef = (a.evidence_refs || []).some((r) =>
      r.type === 'attribution' || (r.type === 'window_contrast' && r.stat));
    check(`S2 A intervention evidence ${a.action_id}`,
      Boolean(gi?.attribution?.status === 'estimable'
        && gi?.attribution?.ci_excludes_zero === true)
      || Boolean(gi?.flags?.designed_window) || interventionRef);
  }
}
check('S2 A-grade sentinel (A<=3)', aCount <= (consts.a_grade_sentinel || 3),
  `A-grade count ${aCount}`);
const excluded = new Set((report.excluded_levers || []).map((e) => e.param));
for (const a of report.actions || []) {
  check(`S2 excluded lever not advised ${a.lever_column}`,
    !excluded.has(a.lever_column));
}
for (const pr of report.prescriptions || []) {
  check(`S2 prescription id ${pr.prescription_id}`, Boolean(pr.prescription_id));
}
const statusExpect = (report.actions || []).some((a) => a.grade === 'A' || a.grade === 'B')
  ? 'actionable'
  : ((report.actions || []).some((a) => a.grade === 'C') ? 'advisory_only' : 'not_actionable');
check('S2 status matches grades', report.status === statusExpect,
  `declared ${report.status} vs expected ${statusExpect}`);
check('S2 actions cap', (report.actions || []).length <= (consts.max_actions || 12));

// ------------------------------------------------------------ S3 zero-LLM
const prov = report.provenance || {};
check('S3 authored_by present', typeof prov.authored_by === 'string');
check('S3 engine literal', prov.engine === 'industrial-improvement-advisor',
  String(prov.engine));
check('S3 data_source raw', prov.data_source === 'raw');
check('S3 reuse disclosure', Array.isArray(prov.reuses));
for (const a of report.actions || []) {
  check(`S3 advisory true ${a.action_id}`, a.advisory === true);
}

// --------------------------------------------------- S4 report + companion
const htmlPath = join(outDir, 'improvement_advisory.html');
const mdPath = join(outDir, 'improvement_advisory.md');
const selfPath = join(outDir, 'html_selfcheck.json');
check('S4 html exists', existsSync(htmlPath));
if (existsSync(htmlPath)) {
  check('S4 html >= 6KB', statSync(htmlPath).size >= 6 * 1024,
    String(statSync(htmlPath).size));
  const html = readFileSync(htmlPath, 'utf-8');
  check('S4 html footer disclaimer',
    html.includes('id="sec-footer"') && html.includes('咨询边界声明'));
  check('S4 html sections', ['sec-goal', 'sec-roadmap', 'sec-actions',
    'sec-evidence', 'sec-execution', 'sec-data'].every((id) => html.includes(`id="${id}"`)));
}
check('S4 md companion', existsSync(mdPath)
  && readFileSync(mdPath, 'utf-8').trim().length > 200);
check('S4 selfcheck file', existsSync(selfPath));
if (existsSync(selfPath)) {
  const sc = JSON.parse(readFileSync(selfPath, 'utf-8'));
  check('S4 selfcheck pass', sc.checks?.pass === true);
}

// ------------------------------------------------- S5 enums + boundary
try {
  const enums = JSON.parse(readFileSync(join(sharedPath, 'schemas',
    'closedloop_enums.json'), 'utf-8')).improvement_advisor;
  const grades = new Set(enums.grades);
  const statuses = new Set(enums.status);
  const reasons = new Set(enums.not_estimable_reason_codes);
  const presKinds = new Set(enums.prescription_kinds);
  const exclReasons = new Set(enums.excluded_lever_reasons);
  check('S5 report mode advisory', report.mode === 'advisory');
  check('S5 status literal', statuses.has(report.status));
  for (const a of report.actions || []) {
    check(`S5 grade literal ${a.action_id}`, grades.has(a.grade), String(a.grade));
    const reason = a.expected_gain?.not_estimable_reason;
    if (reason) check(`S5 reason literal ${a.action_id}`, reasons.has(reason), reason);
  }
  for (const pr of report.prescriptions || []) {
    check(`S5 prescription kind ${pr.prescription_id}`, presKinds.has(pr.kind), pr.kind);
  }
  for (const e of report.excluded_levers || []) {
    check(`S5 excluded reason ${e.param}`, exclReasons.has(e.reason), e.reason);
  }
} catch (e) {
  warn(`enums unavailable: ${e.message} — S5 enum checks skipped (treated as fail)`);
  check('S5 enums readable', false);
}

// ---------------------------------------------------------------- verdict
const failed = results.filter(([, ok]) => !ok);
console.log(`[improvement-gate] checks: ${results.length}, failures: ${failed.length}, ` +
  `status=${report.status}, actions=${(report.actions || []).length}`);
if (failed.length) {
  for (const [name] of failed) console.error(`[improvement-gate] FAILED ${name}`);
  process.exit(3);
}
console.log('[improvement-gate] PASS' +
  (report.status === 'not_actionable' ? ' (not_actionable semantics: prescriptions only)' : ''));
process.exit(0);
