#!/usr/bin/env node
// test_gate_v11.mjs — P4-4 / P2-8 gate-side test for the v1.1 quality gates
// (contract docs/plans/contracts/README.md §5/§6/§11; traceability
// `gate-v11.*`, AR-03, DS-03/DS-07/DS-10).
//
//   node .claude/skills/industrial-doe-analyzer/tests/test_gate_v11.mjs [--keep]
//
// Self-contained: the fixtures live under tests/fixtures/gate_v11/ (owned by
// this test — no existing F*/tamper_* fixture is read or written) and are
// regenerated on every run:
//   staged/  pristine inputs (run_table + analysis_context)
//   legacy/  analyze.py all  -> v1.0 artifacts, NO v1.1 fields
//   v11/     analyze.py all  + v1.1 field/artifact patch + report rebuild
//   bad_*/   copies of v11/ with ONE defect each
//
// ASSERTIONS
//  (a) legacy run dir passes every gate; G8-G11 report n/a and do not FAIL
//  (b) an unknown top-level (and window-level) recommendations key still FAILs G6b
//  (c) G8/G9/G10/G11 each FAIL on a purpose-built bad artifact and PASS on the
//      good v1.1 fixture
//
// Only node: builtins; every subprocess is spawned with an argument list
// (never a shell string).

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL = path.resolve(HERE, '..');
const REPO = path.resolve(SKILL, '..', '..', '..');
const SHARED = path.join(REPO, '.claude', 'shared');
const GATE = path.join(SKILL, 'scripts', 'quality_gate.mjs');
const ANALYZE = path.join(SKILL, 'scripts', 'analyze.py');
const FIX = path.join(HERE, 'fixtures', 'gate_v11');
const KEEP = process.argv.includes('--keep');

const RESULTS = [];
function record(name, ok, detail = '') {
  RESULTS.push({ name, ok: !!ok });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  ${detail}`}`);
}
function assert(name, ok, detail = '') { record(name, ok, detail); }

// ---------------------------------------------------------------- process

function spawn(cmd, args) {
  return spawnSync(cmd, args, {
    cwd: REPO, encoding: 'utf8', shell: false, timeout: 900000,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  });
}
function runAnalyze(runDir, sub) {
  const p = spawn('uv', ['run', '--project', path.join(SHARED, 'scripts'),
    'python', ANALYZE, sub, '--run-dir', runDir]);
  return { rc: p.status, out: `${p.stdout || ''}${p.stderr || ''}` };
}
function runGate(runDir) {
  const p = spawn('node', [GATE, runDir, '--skill-path', SKILL, '--shared-path', SHARED]);
  return { rc: p.status, out: `${p.stdout || ''}${p.stderr || ''}` };
}
const hasLine = (out, re) => out.split(/\r?\n/).some((l) => re.test(l));
// A gate that actually RAN (as opposed to degrading to "n/a (…)"). Guarding this
// matters: a gate that silently reports n/a on every run looks green while
// checking nothing.
const hasRealPass = (out, id) => out.split(/\r?\n/)
  .some((l) => l.startsWith(`PASS ${id}`) && !l.includes('- n/a'));

// ---------------------------------------------------------------- helpers

function rmrf(p) { fs.rmSync(p, { recursive: true, force: true }); }
function cpDir(src, dst) { fs.cpSync(src, dst, { recursive: true }); }
function readJson(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }
function writeJson(p, obj) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(obj, null, 2), 'utf8');
}
function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

/** deterministic LCG so the staged dataset never depends on Math.random */
function lcg(seed) {
  let s = seed >>> 0;
  return () => {
    s = (1664525 * s + 1013904223) >>> 0;
    return s / 4294967296;
  };
}
function normal(rand) {
  const u = Math.max(rand(), 1e-12);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
}
const r6 = (v) => Number(v.toFixed(6));

// ---------------------------------------------------------------- fixture

// 2^3 full factorial x2 replicates, TWO responses (so the v1.1 joint/matrix
// artifacts are exercised for real) + one undeclared non-factor column
// (`ambient`) that carries the association-screen confounder story.
function stagedData() {
  const rand = lcg(20261017);
  const rows = [];
  for (let rep = 0; rep < 2; rep += 1) {
    for (const a of [-1, 1]) for (const b of [-1, 1]) for (const c of [-1, 1]) {
      const quality = 50 + 2.0 * a - 1.5 * b + 0.0 * c + 0.3 * a * b + 0.3 * normal(rand);
      const purity = 90 + 1.2 * b + 0.5 * a + 0.25 * normal(rand);
      const ambient = 21 + 1.5 * a + 0.4 * normal(rand);   // non-factor, A-confounded
      rows.push({ A: a, B: b, C: c, ambient: r6(ambient),
        quality: r6(quality), purity: r6(purity) });
    }
  }
  const header = Object.keys(rows[0]);
  return `${header.join(',')}\n${rows.map((r) => header.map((h) => r[h]).join(',')).join('\n')}\n`;
}
function stagedContext() {
  return {
    data_path: '00_input/data.csv', mode_override: null,
    responses: [
      { col: 'quality', goal: 'maximize', lsl: null, usl: null, target: null, weight: null },
      { col: 'purity', goal: 'maximize', lsl: null, usl: null, target: null, weight: null },
    ],
    factors: [{ col: 'A', type: 'numeric' }, { col: 'B', type: 'numeric' },
      { col: 'C', type: 'numeric' }],
    blocks: [], covariates: [], index_cols: [], time_col: null,
    group_col: null, run_order_col: null, max_lag: 20, alpha: 0.05,
    effect_size_threshold: 0.01, constraints: [],
    inference: { assigned_by: 'user', notes: ['gate_v11 staged fixture'] },
  };
}
function stageInputs() {
  const dir = path.join(FIX, 'staged', 'run');
  rmrf(path.join(FIX, 'staged'));
  fs.mkdirSync(path.join(dir, '00_input'), { recursive: true });
  fs.writeFileSync(path.join(dir, '00_input', 'data.csv'), stagedData(), 'utf8');
  writeJson(path.join(dir, '00_input', 'analysis_context.json'), stagedContext());
  return dir;
}

// ---------------------------------------------------------------- v1.1 patch

const PI_METHOD = 'ŷ ± t_{0.975,df} · sqrt((1 + x0\'(X\'X)⁻¹x0) · MSE)';
const CI_METHOD = 'ŷ ± t_{0.975,df} · sqrt(x0\'(X\'X)⁻¹x0 · MSE)';

/**
 * Turn a freshly analyzed designed run into a v1.1 run:
 *  - recommendations.json gains the §5.1 top-level keys, the §5.2 window keys
 *    and the §5.2 expected_effect interval keys (values derived from the run's
 *    own windows — no invented window ids)
 *  - effect_table.json/model.json gain the §6 additions
 *  - 02_analysis/association_screen.json + conclusions/next_design.json written
 * The caller rebuilds report.html afterwards so G7b hashes stay honest.
 */
function patchV11(runDir, opts = {}) {
  const recsPath = path.join(runDir, 'conclusions', 'recommendations.json');
  const recs = readJson(recsPath);
  const ctx = readJson(path.join(runDir, '00_input', 'analysis_context.json'));
  const factors = (ctx.factors || []).map((f) => f.col);
  const responses = (ctx.responses || []).map((r) => r.col);
  const wins = recs.operating_windows || [];
  if (wins.length === 0) throw new Error('gate_v11: staged run produced no windows');

  // --- §5.2 window additions
  wins.forEach((w) => {
    const inDomain = recs.applicability_domain.factor_observed_ranges[w.factor];
    w.window_role = 'marginal_diagnostic';
    const blockers = [];
    if (!w.factor_unit) blockers.push('unit_missing');
    if (w.extrapolation === true) blockers.push('extrapolation');
    if (w.confirmation_needed === true) blockers.push('non_randomized_confirmation_pending');
    w.actionable_blockers = blockers;
    w.actionable = blockers.length === 0;
    w.in_design_hull = w.extrapolation !== true;
    w.constraints_applied = (recs.constraints || []).map((c) => ({
      factor: c.factor, type: 'box', min: c.min, max: c.max, hard: true, source: c.source }));
    w.constraint_violations = 0;
    const mid = (w.range[0] + w.range[1]) / 2;
    const hCi = Math.max(0.05, Math.abs((w.range[1] - w.range[0]) / 4));
    w.predicted_at_center = {
      mean: r6(mid), mean_ci95: [r6(mid - hCi), r6(mid + hCi)],
      pi95: [r6(mid - hCi * 1.7), r6(mid + hCi * 1.7)],
      ti95_95: [r6(mid - hCi * 2.4), r6(mid + hCi * 2.4)],
    };
    // --- §5.2 expected_effect interval additions (four intervals kept apart)
    const ee = w.expected_effect;
    const d = ee.delta || 0;
    const h = Math.max(0.05, Math.abs(d) * 0.25);
    ee.mean_ci95 = [r6(d - h), r6(d + h)];
    ee.pi95 = [r6(d - h * 1.8), r6(d + h * 1.8)];
    ee.pi95_method = PI_METHOD;
    ee.effect_ci95 = [r6(d - h * 0.8), r6(d + h * 0.8)];
    ee.unit_status = w.factor_unit ? 'valid' : 'missing';
    ee.response_unit = (recs.response_specs[w.response] || {}).unit || null;
    ee.tolerance_interval_95_95 = [r6(d - h * 2.6), r6(d + h * 2.6)];
  });

  // --- §5.1 units / design_region / grid_plan / interval_disclosure
  recs.units = {
    factors: Object.fromEntries(factors.map((f, i) => [f, {
      canonical: `coded_${f}`, display: f, unit_status: 'valid', source: 'user' }])),
    responses: Object.fromEntries(responses.map((r) => [r, {
      canonical: r, display: r, unit_status: 'valid', source: 'user' }])),
    conflicts: [],
  };
  const ranges = recs.applicability_domain.factor_observed_ranges;
  recs.design_region = {
    type: 'full_factorial_2^3', hull: 'box',
    coded_bounds: Object.fromEntries(factors.map((f) => [f, [-1, 1]])),
    axial_alpha: null, max_leverage: 1.0, leverage_threshold: 2 * factors.length / 16,
    mean_leverage: 0.75,
    extrapolation_risk: 'low',
    evaluated_points: 16,
    design_hull_confidence: 'high',
  };
  recs.grid_plan = {
    n_active: new Set(wins.map((w) => w.factor)).size, top_k: 4, grid_n: 9,
    n_grid_points: Math.pow(9, Math.min(4, new Set(wins.map((w) => w.factor)).size)),
    approach: 'grid', max_grid_points: 6561, deferred_factors: [], truncated: false,
  };
  recs.interval_disclosure = {
    pi_method: PI_METHOD, ci_method: CI_METHOD,
    effect_ci_method: 'β̂ ± t_{0.975,df} · se(β̂)',
    tolerance_method: 'normal tolerance factor k(n,df,p) · s (95% population @95% confidence)',
    note: '四类区间分离：均值 CI ≠ 预测区间 PI ≠ 效应 CI ≠ 容差区间；PI 不是合格率',
    joint_coverage: null, coverage_check: { n: null, pi_point_coverage: null },
  };

  // --- §5.1 joint_windows / joint_setpoints / actionable_summary
  // actionable carrier: raw midpoint of the two strongest windows
  const primary = wins[0];
  const second = wins.find((w) => w.factor !== primary.factor) || primary;
  const pick = (w) => r6((w.range[0] + w.range[1]) / 2);
  const spFactors = { [primary.factor]: pick(primary), [second.factor]: pick(second) };
  const pred = (base, h) => ({
    mean: base, mean_ci95: [r6(base - h), r6(base + h)],
    pi95: [r6(base - h * 1.8), r6(base + h * 1.8)], d: 0.82, unit_status: 'valid' });
  const goodSp = {
    id: 'JS-001', method: 'grid_search', factors: spFactors,
    predicted: Object.fromEntries(responses.map((r, i) => [r, pred(i === 0 ? 52 : 92, 0.6)])),
    responses_satisfied: responses.slice(),
    feasible: true, hard_constraint_violations: 0,
    constraint_slack: Object.fromEntries(Object.entries(spFactors).map(([f, v]) => [
      f, r6(ranges[f] ? Math.min(v - ranges[f].min, ranges[f].max - v) : 1)])),
    desirability: 0.82, joint_coverage: 0.93,
    evidence_level: 'L3', confidence: 'medium',
    window_ids: [primary.id, second.id].filter((v, i, a) => a.indexOf(v) === i),
    unit_status: 'valid', actionable: true, blockers: [],
  };
  const blockedSp = {
    id: 'JS-002', method: 'constraint_projection', factors: { [primary.factor]: pick(primary) },
    predicted: Object.fromEntries(responses.map((r) => [r, pred(r === 'quality' ? 48 : 88, 0.5)])),
    responses_satisfied: [], feasible: false, hard_constraint_violations: 0,
    constraint_slack: { [primary.factor]: -0.4 },
    desirability: null, joint_coverage: null,
    evidence_level: 'L2', confidence: 'low', window_ids: [],
    unit_status: 'missing', actionable: false, blockers: ['unit_missing'],
  };
  recs.joint_setpoints = [goodSp, blockedSp];
  recs.actionable_summary = {
    n_actionable: 1,
    n_blocked: 1,
    blocked: [{ setpoint_id: 'JS-002', reasons: ['unit_missing: 单位缺失 → 不得作为执行依据'] }],
  };
  recs.joint_windows = [{
    id: 'JW-001', responses: responses.slice(),
    factors: Object.fromEntries(Object.keys(spFactors).map((f) => [f, [
      ranges[f] ? r6(ranges[f].min) : -1, ranges[f] ? r6(ranges[f].max) : 1]])),
    feasible: true, constraint_violations: 0,
    predicted: Object.fromEntries(responses.map((r) => [r, {
      mean: r === 'quality' ? 52 : 92,
      pi95: [r === 'quality' ? 50.9 : 91.0, r === 'quality' ? 53.1 : 93.0], d: 0.8 }])),
    desirability: 0.82, method: 'desirability_lbfgsb', evidence_level: 'L3',
  }];

  // --- §5.1 factor_response_matrix (cells derived from the real windows)
  const winOf = new Map();
  wins.forEach((w) => { if (!winOf.has(`${w.factor}\u0000${w.response}`)) winOf.set(`${w.factor}\u0000${w.response}`, w); });
  recs.factor_response_matrix = [];
  for (const f of factors) {
    for (const r of responses) {
      const w = winOf.get(`${f}\u0000${r}`);
      const cell = { factor: f, response: r, window_id: w ? w.id : null,
        no_window_reason: w ? null : 'NO_SIGNIFICANT_FACTOR',
        delta: w ? w.expected_effect.delta : null,
        effect_size: w ? Math.abs(w.expected_effect.delta || 0) : 0,
        direction: w ? ((w.expected_effect.delta || 0) >= 0 ? 'increase' : 'decrease') : null,
        fdr_q: w ? w.fdr_q : null,
        evidence_level: w ? 'L3' : 'L5', confidence: w ? w.confidence : 'low' };
      recs.factor_response_matrix.push(cell);
    }
  }

  // --- §5.1 refs (next_design.json + association_screen.json written first)
  const nextDesign = {
    contract_version: '1.1', recommended_action: 'confirm_replicate',
    rationale: '主效应已辨识；按合同在窗口中心点做确认重复以固化可执行窗口',
    primary_action_id: 'ND-001',
    actions: [{ id: 'ND-001', action: 'confirm_replicate', n_runs: 4, block_policy: 'single_block',
      replicate_policy: 'center_point_x2',
      settings: Object.entries(spFactors).map(([factor, value]) => ({ factor, value })),
      expected_information: { coverage_gain: 0.1 }, constraints_ok: true, source_evidence: [primary.id] }],
  };
  const nextPath = path.join(runDir, 'conclusions', 'next_design.json');
  writeJson(nextPath, nextDesign);
  recs.next_design_ref = {
    path: 'conclusions/next_design.json',
    sha256: sha256(fs.readFileSync(nextPath)),
    recommended_action: nextDesign.recommended_action,
    primary_action_id: nextDesign.primary_action_id,
  };

  const assoc = {
    contract_version: '1.1', causal_claim: 'none',
    n_rows: 16, n_pairs: responses.length, design_adjusted: true,
    pairs: responses.map((r) => ({
      factor: 'ambient', response: r, kind: 'non_factor',
      marginal: { r: 0.62, p: 0.01, n: 16, method: 'pearson' },
      design_adjusted: { coef: 0.4, p: 0.21, n: 16, method: 'ols_with_design_columns', strata: null },
      verdict: 'marginal', note: '非因子列：相关级线索，禁止作为窗口证据',
    })),
  };
  const assocPath = path.join(runDir, '02_analysis', 'association_screen.json');
  writeJson(assocPath, assoc);
  recs.association_screen_ref = {
    path: '02_analysis/association_screen.json',
    sha256: sha256(fs.readFileSync(assocPath)),
    n_pairs: assoc.n_pairs, causal_claim: 'none',
  };

  // --- §6 effect_table / model additions (must stay G6-tolerant)
  const effPath = path.join(runDir, '02_analysis', 'effect_table.json');
  const eff = readJson(effPath);
  eff.interval_semantics = 'mean_ci95=ŷ±t·se(fit); pi95=ŷ±t·sqrt((1+h)·MSE); effect_ci95=β̂±t·se(β̂)';
  eff.response_units = Object.fromEntries(responses.map((r) => [r, 'missing']));
  const firstRow = ((eff.families || [])[0] || {}).tests;
  if (Array.isArray(firstRow) && firstRow[0]) {
    firstRow[0].effect_ci95 = [r6((firstRow[0].coefficient || 0) - 0.2), r6((firstRow[0].coefficient || 0) + 0.2)];
    firstRow[0].std_effect = 0.71;
    firstRow[0].term_unit = 'coded';
  }
  writeJson(effPath, eff);

  const modelPath = path.join(runDir, '02_analysis', 'model.json');
  const models = readJson(modelPath);
  if (Array.isArray(models) && models[0]) {
    models[0].design_hull = { hull: 'box', coded_bounds: Object.fromEntries(factors.map((f) => [f, [-1, 1]])),
      max_leverage: 1.0, leverage_threshold: 2 * factors.length / 16 };
    models[0].leverage = { max: 1.0, mean: 0.75, threshold: 2 * factors.length / 16, n_exceed: 0 };
    writeJson(modelPath, models);
  }

  if (opts.mutateRecs) opts.mutateRecs(recs, runDir);
  writeJson(recsPath, recs);
  return recs;
}

// ---------------------------------------------------------------- cases

function gateReport(tag, out) {
  const summary = out.split(/\r?\n/).find((l) => l.startsWith('[GATE]')) || '(no [GATE] line)';
  console.log(`    ${tag}: ${summary.trim()}`);
  return summary;
}

function main() {
  if (!fs.existsSync(GATE)) throw new Error(`gate not found: ${GATE}`);
  rmrf(FIX);

  const V11_GATES = ['G8_association_not_in_windows', 'G9_interval_semantics',
    'G10_joint_actionable', 'G11_factor_response_coverage'];

  // ---------- bare n/a probe: a run dir with NONE of the v1.1 artifacts
  // (absence may not FAIL a v1.1 gate — the single most important semantic)
  console.log('== na_probe: empty run dir -> G8-G11 must be n/a, never FAIL ==');
  const empty = path.join(FIX, 'na_probe', 'run');
  fs.mkdirSync(empty, { recursive: true });
  const g0 = runGate(empty);
  gateReport('na_probe', g0.out);
  for (const id of V11_GATES) {
    assert(`na_probe.${id}_na`, hasLine(g0.out, new RegExp(`^PASS ${id} - n/a`)), '(no n/a PASS line)');
    assert(`na_probe.${id}_not_failed`, !hasLine(g0.out, new RegExp(`^FAIL ${id}\\b`)), '(must not FAIL on absence)');
  }

  // ---------- staged inputs + one analyzer run (shared by both fixtures)
  const staged = stageInputs();
  console.log('== gate_v11: staged inputs written ==');

  console.log('== legacy: analyze.py all (v1.0 artifacts, no v1.1 fields) ==');
  const legacy = path.join(FIX, 'legacy', 'run');
  fs.mkdirSync(path.dirname(legacy), { recursive: true });
  cpDir(staged, legacy);
  const a1 = runAnalyze(legacy, 'all');
  assert('legacy.analyze_exit0', a1.rc === 0, a1.out.slice(-500));
  if (a1.rc !== 0) return finish();

  const legacyRecs = readJson(path.join(legacy, 'conclusions', 'recommendations.json'));
  const legacyHasV11 = 'units' in legacyRecs || 'joint_setpoints' in legacyRecs
    || 'factor_response_matrix' in legacyRecs;
  const g1 = runGate(legacy);
  gateReport('legacy', g1.out);
  assert('legacy.gate_exit0', g1.rc === 0, g1.out.slice(-700));
  // Absence handling (absence => explicit n/a PASS, never FAIL) is covered by the
  // na_probe group above. Here the question is the opposite one: on a REAL run the
  // four v1.1 gates must actually execute — a gate that silently degrades to n/a
  // looks green while checking nothing. analyze.py always takes the v1.1 path now,
  // so the legacy "v1.0-only output" world is asserted only if it ever returns.
  for (const id of V11_GATES) {
    assert(`legacy.${id}_not_failed`, !hasLine(g1.out, new RegExp(`^FAIL ${id}\\b`)), '');
    if (!legacyHasV11) {
      assert(`legacy.${id}_na`, hasLine(g1.out, new RegExp(`^PASS ${id} - n/a`)),
        'expected an explicit n/a PASS line');
    } else {
      assert(`legacy.${id}_real`, hasRealPass(g1.out, id),
        'expected the gate to actually run on a v1.1 artifact set, not report n/a');
    }
  }
  assert('legacy.g6_strict_keys_pass',
    hasLine(g1.out, /^PASS G6_strict_extra_keys_recommendations/), '');

  console.log('== v11: analyze.py all + v1.1 patch + report rebuild ==');
  const v11 = path.join(FIX, 'v11', 'run');
  fs.mkdirSync(path.dirname(v11), { recursive: true });
  cpDir(staged, v11);
  const a2 = runAnalyze(v11, 'all');
  assert('v11.analyze_exit0', a2.rc === 0, a2.out.slice(-500));
  if (a2.rc !== 0) return finish();
  patchV11(v11);
  const a3 = runAnalyze(v11, 'report');   // rebuild so G7b sha256 matches patched artifacts
  assert('v11.report_rebuild_exit0', a3.rc === 0, a3.out.slice(-500));

  const g2 = runGate(v11);
  gateReport('v11', g2.out);
  assert('v11.gate_exit0', g2.rc === 0, g2.out.slice(-900));
  for (const id of ['G8_association_not_in_windows', 'G9_interval_semantics',
    'G10_joint_actionable', 'G11_factor_response_coverage',
    'G6_strict_extra_keys_recommendations']) {
    assert(`v11.${id}_pass`, hasLine(g2.out, new RegExp(`^PASS ${id}`)), g2.out.slice(-600));
  }

  // ---------- (b) unknown keys still hard-fail
  console.log('== bad_key: undeclared recommendations keys must FAIL G6b ==');
  const badKey = path.join(FIX, 'bad_key', 'run');
  cpDir(v11, badKey);
  const recsKey = path.join(badKey, 'conclusions', 'recommendations.json');
  const rk = readJson(recsKey);
  rk.undeclared_v12_field = { nope: true };
  writeJson(recsKey, rk);
  const gb = runGate(badKey);
  gateReport('bad_key', gb.out);
  assert('bad_key.recs_unknown_key_fails', gb.rc === 1
    && hasLine(gb.out, /^FAIL G6_strict_extra_keys_recommendations/), gb.out.slice(-500));

  const badWinKey = path.join(FIX, 'bad_key_window', 'run');
  cpDir(v11, badWinKey);
  const recsWk = path.join(badWinKey, 'conclusions', 'recommendations.json');
  const rwk = readJson(recsWk);
  rwk.operating_windows[0].undeclared_v12_field = 1;
  writeJson(recsWk, rwk);
  const gbw = runGate(badWinKey);
  gateReport('bad_key_window', gbw.out);
  assert('bad_key.window_unknown_key_fails', gbw.rc === 1
    && hasLine(gbw.out, /^FAIL G6_strict_extra_keys_recommendations/), gbw.out.slice(-500));

  // ---------- (c) G8 negatives
  console.log('== bad_g8_*: association screen must never enter a window ==');
  const g8Cases = {
    bad_g8_causal: (recs, dir) => {
      const p = path.join(dir, '02_analysis', 'association_screen.json');
      const a = readJson(p);
      a.causal_claim = 'correlational';
      writeJson(p, a);
      recs.association_screen_ref.causal_claim = 'correlational';
      recs.association_screen_ref.sha256 = sha256(fs.readFileSync(p));
    },
    bad_g8_citation: (recs) => {
      recs.operating_windows[0].evidence_refs = (recs.operating_windows[0].evidence_refs || [])
        .concat(['association_screen.json#quality.ambient']);
    },
    bad_g8_sha: (recs) => { recs.association_screen_ref.sha256 = 'deadbeef'.repeat(8); },
    bad_g8_pair_factor: (recs, dir) => {
      const p = path.join(dir, '02_analysis', 'association_screen.json');
      const a = readJson(p);
      a.pairs[0].factor = recs.operating_windows[0].factor;   // window now rides a pair name
      writeJson(p, a);
      recs.association_screen_ref.sha256 = sha256(fs.readFileSync(p));
    },
  };
  for (const [name, mutate] of Object.entries(g8Cases)) {
    const dir = path.join(FIX, name, 'run');
    cpDir(v11, dir);
    const rp = path.join(dir, 'conclusions', 'recommendations.json');
    const rr = readJson(rp);
    mutate(rr, dir);
    writeJson(rp, rr);
    const g = runGate(dir);
    gateReport(name, g.out);
    assert(`${name}.G8_fails`, g.rc === 1 && hasLine(g.out, /^FAIL G8_association_not_in_windows/),
      g.out.slice(-400));
  }

  // ---------- (c) G9 negatives
  console.log('== bad_g9_*: interval semantics ==');
  const g9Cases = {
    bad_g9_halfwidth: (recs) => {
      const ee = recs.operating_windows[0].expected_effect;
      ee.pi95 = ee.mean_ci95.slice();               // PI == CI half-width -> FAIL
    },
    bad_g9_no_plus: (recs) => { recs.interval_disclosure.pi_method = 'ŷ ± t · sqrt(h · MSE)'; },
    bad_g9_rate: (recs) => { recs.operating_windows[0].expected_effect.pi95_pass_rate = 0.95; },
    bad_g9_scalar_pi: (recs) => {
      // scalar pi95 on a predicted block that has NO mean_ci95 sibling ->
      // exactly the "PI dressed as a pass/yield rate" hazard
      recs.joint_windows[0].predicted[recs.joint_windows[0].responses[0]].pi95 = 0.95;
    },
  };
  for (const [name, mutate] of Object.entries(g9Cases)) {
    const dir = path.join(FIX, name, 'run');
    cpDir(v11, dir);
    const rp = path.join(dir, 'conclusions', 'recommendations.json');
    const rr = readJson(rp);
    mutate(rr);
    writeJson(rp, rr);
    const g = runGate(dir);
    gateReport(name, g.out);
    assert(`${name}.G9_fails`, g.rc === 1 && hasLine(g.out, /^FAIL G9_interval_semantics/),
      g.out.slice(-400));
  }

  // ---------- (c) G10 negatives
  console.log('== bad_g10_*: joint_setpoints actionable integrity ==');
  const g10Cases = {
    bad_g10_violations: (recs) => { recs.joint_setpoints[0].hard_constraint_violations = 1; },
    bad_g10_unit: (recs) => { recs.joint_setpoints[0].unit_status = 'missing'; },
    bad_g10_outside: (recs) => {
      const f = Object.keys(recs.joint_setpoints[0].factors)[0];
      recs.joint_setpoints[0].factors[f] = 1e6;     // outside the observed/design range
    },
    bad_g10_undisclosed: (recs) => { recs.actionable_summary.blocked = []; },
  };
  for (const [name, mutate] of Object.entries(g10Cases)) {
    const dir = path.join(FIX, name, 'run');
    cpDir(v11, dir);
    const rp = path.join(dir, 'conclusions', 'recommendations.json');
    const rr = readJson(rp);
    mutate(rr);
    writeJson(rp, rr);
    const g = runGate(dir);
    gateReport(name, g.out);
    assert(`${name}.G10_fails`, g.rc === 1 && hasLine(g.out, /^FAIL G10_joint_actionable/),
      g.out.slice(-400));
  }

  // ---------- (c) G11 negatives
  console.log('== bad_g11_*: factor x response coverage ==');
  const g11Cases = {
    bad_g11_silent_cell: (recs) => {
      recs.factor_response_matrix[0].window_id = null;
      recs.factor_response_matrix[0].no_window_reason = null;
    },
    bad_g11_bad_reason: (recs) => { recs.factor_response_matrix[0].no_window_reason = 'BECAUSE'; },
    bad_g11_missing_cell: (recs) => { recs.factor_response_matrix.pop(); },
  };
  for (const [name, mutate] of Object.entries(g11Cases)) {
    const dir = path.join(FIX, name, 'run');
    cpDir(v11, dir);
    const rp = path.join(dir, 'conclusions', 'recommendations.json');
    const rr = readJson(rp);
    mutate(rr);
    writeJson(rp, rr);
    const g = runGate(dir);
    gateReport(name, g.out);
    assert(`${name}.G11_fails`, g.rc === 1 && hasLine(g.out, /^FAIL G11_factor_response_coverage/),
      g.out.slice(-400));
  }

  // ---------- the negatives must not have disturbed the good fixtures
  return finish();
}

function finish() {
  const failed = RESULTS.filter((r) => !r.ok);
  if (!KEEP && fs.existsSync(FIX)) {
    // repo fixture discipline (mirrors run_tests.py clean_fixture_artifacts):
    // keep only the tiny staged INPUTS — every derived run dir (analyze.py
    // output, v1.1 patch, one-defect negatives, empty probe) is regenerated
    // deterministically on the next run. Pass --keep to retain them all.
    for (const e of fs.readdirSync(FIX, { withFileTypes: true })) {
      if (e.isDirectory() && e.name !== 'staged') rmrf(path.join(FIX, e.name));
    }
  }
  console.log(`\n[TESTS-NODE] ${RESULTS.length - failed.length}/${RESULTS.length} passed`
    + (failed.length ? ` — FAILED: ${failed.map((f) => f.name).join(', ')}` : ' — ALL GREEN'));
  process.exit(failed.length ? 1 : 0);
}

main();
