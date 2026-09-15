#!/usr/bin/env node
// verify-classical.mjs — self-verification gate for the lab's five classical
// multivariate process-monitoring baselines.
//
// For every (algorithm, case) pair it runs the algorithm through the SAME
// sanitized context the lab uses (buildContext over loadCaseForAlgorithm, so no
// truth field ever reaches a module) and asserts:
//   1. detection.detection_rate is a finite number (no NaN / undefined)
//   2. EVERY numeric field anywhere inside `detection` is finite (NaN sweep)
//   3. verdict is exactly 'fault' or 'normal'
//   4. top3 / variable_top3 / variables_ranked are arrays, reasoning and
//      diagnosis_step are non-empty strings
//   5. a 'normal' verdict never carries root-cause candidates (top3 === [])
//   6. the honesty rule: for a non-TEP dataset `affinityAvailable()` is false, so
//      a DETECTED fault MUST still return top3 === [] rather than invent a
//      variable->cause mapping
//   7. a SECOND run of the same algorithm on a FRESH context reproduces the
//      detection_rate and verdict exactly (determinism check — `deterministic:
//      true` must be honest, which also rules out hidden cross-case state)
//
// It then runs a synthetic EDGE-CASE block: constant (zero-variance) columns,
// an all-constant reference, a 3-row reference and a 1-row reference — the
// degenerate inputs where a sloppy implementation produces NaN.
//
// Non-zero exit on any failure. This is a gate, not a benchmark: it asserts
// invariants and prints what was actually observed, it never adjusts a
// threshold (per-case threshold tuning would be truth leakage).

import { loadCasesRaw, loadCaseForAlgorithm } from '../server/utils/paths.mjs';
import { buildContext } from '../server/utils/algorithms/_shared.mjs';
import { makeRng } from '../server/utils/linalg.mjs';
import { affinityAvailable } from '../server/utils/tep-affinity.mjs';
import * as kpca from '../server/utils/algorithms/kpca.mjs';
import * as ica from '../server/utils/algorithms/ica.mjs';
import * as spc from '../server/utils/algorithms/spc.mjs';
import * as knn from '../server/utils/algorithms/knn.mjs';
import * as iforest from '../server/utils/algorithms/iforest.mjs';

const ALGOS = [kpca, ica, spc, knn, iforest];
const VALID_VERDICTS = new Set(['fault', 'normal']);

const pad = (s, n) => {
  const str = String(s ?? '');
  return str.length >= n ? `${str.slice(0, n - 1)}…` : str.padEnd(n);
};

/** Recursively collect every non-finite numeric value under `value`. */
function nonFinitePaths(value, path = 'detection', out = []) {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) out.push(`${path}=${value}`);
    return out;
  }
  if (Array.isArray(value)) {
    value.forEach((v, i) => nonFinitePaths(v, `${path}[${i}]`, out));
    return out;
  }
  if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) nonFinitePaths(v, `${path}.${k}`, out);
  }
  return out;
}

function checkResult(out, meta, caseDef) {
  const problems = [];
  if (!out || typeof out !== 'object') return ['run() did not return an object'];

  const rate = out.detection?.detection_rate;
  if (typeof rate !== 'number' || !Number.isFinite(rate)) {
    problems.push(`detection.detection_rate is ${JSON.stringify(rate)} (must be a finite number)`);
  }
  const bad = nonFinitePaths(out.detection);
  if (bad.length) problems.push(`non-finite values in detection: ${bad.slice(0, 6).join(', ')}`);

  if (!VALID_VERDICTS.has(out.verdict)) {
    problems.push(`verdict is ${JSON.stringify(out.verdict)} (must be 'fault' or 'normal')`);
  }
  if (!Array.isArray(out.top3)) problems.push(`top3 is ${typeof out.top3} (must be an array)`);
  if (!Array.isArray(out.variable_top3)) problems.push('variable_top3 is not an array');
  if (!Array.isArray(out.variables_ranked)) problems.push('variables_ranked is not an array');
  if (typeof out.reasoning !== 'string' || !out.reasoning.length) problems.push('reasoning is empty');
  if (typeof out.diagnosis_step !== 'string' || !out.diagnosis_step.length) problems.push('diagnosis_step is empty');
  if (typeof out.runtime_ms !== 'number' || !Number.isFinite(out.runtime_ms)) problems.push('runtime_ms is not a number');

  if (out.verdict === 'normal' && Array.isArray(out.top3) && out.top3.length !== 0) {
    problems.push(`verdict 'normal' but top3 has ${out.top3.length} entries (must be [])`);
  }
  // Honesty rule: non-TEP domains have no published variable->cause table, so a
  // detected fault must still abstain from naming a mechanism.
  if (caseDef && !affinityAvailable(caseDef.dataset) && Array.isArray(out.top3) && out.top3.length) {
    problems.push(`dataset '${caseDef.dataset}' has no affinity table but top3 names ${out.top3.length} causes`);
  }
  if (meta.deterministic !== true) problems.push('meta.deterministic must be true');
  if (meta.family !== 'classical' || meta.kind !== 'detector' || meta.needsReference !== true) {
    problems.push('meta family/kind/needsReference contract violated');
  }
  return problems;
}

// --------------------------------------------------------------- real cases

const cases = loadCasesRaw();
const rows = [];
const failures = [];
let pass = 0;
let fail = 0;

for (const algo of ALGOS) {
  const meta = algo.meta;
  for (const c of cases) {
    const caseDef = loadCaseForAlgorithm(c.case_id);
    const ctx1 = buildContext(caseDef);
    const out1 = await algo.run(ctx1);
    const problems = checkResult(out1, meta, caseDef);

    // Determinism: a fresh context (fresh matrices, fresh module caches on first
    // sight) must reproduce the identical detection_rate and verdict.
    const ctx2 = buildContext(loadCaseForAlgorithm(c.case_id));
    const out2 = await algo.run(ctx2);
    const r1 = out1?.detection?.detection_rate;
    const r2 = out2?.detection?.detection_rate;
    if (!(r1 === r2)) problems.push(`non-deterministic detection_rate: ${r1} vs ${r2}`);
    if (out1?.verdict !== out2?.verdict) {
      problems.push(`non-deterministic verdict: ${out1?.verdict} vs ${out2?.verdict}`);
    }

    const ok = problems.length === 0;
    ok ? pass++ : fail++;
    if (!ok) failures.push(`${meta.id} / ${c.case_id}: ${problems.join('; ')}`);

    rows.push({
      algo: meta.id,
      case_id: c.case_id,
      dataset: c.dataset,
      control: !!c.control,
      verdict: out1?.verdict,
      rate: r1,
      second_rate: r2,
      params: out1?.detection?.params ?? '',
      top3: Array.isArray(out1?.top3) ? out1.top3.slice(0, 2) : [],
      vars: Array.isArray(out1?.variable_top3) ? out1.variable_top3.slice(0, 2) : [],
      runtime_ms: out1?.runtime_ms,
      status: ok ? 'PASS' : 'FAIL',
    });
  }
}

// ------------------------------------------------------------ edge cases

/** Build a ctx-shaped object without touching the repo contract. */
function syntheticCtx({ id, refRows, caseRows, constantCols = [], m = 6, win = null, control = false, seed = 11 }) {
  const rng = makeRng(seed);
  const gen = (n, shift) => Array.from({ length: n }, (_, i) =>
    Float64Array.from({ length: m }, (_, j) => {
      if (constantCols.includes(j)) return 2.5; // zero-variance column
      const base = rng() * 2 - 1;
      return j === 4 ? base + shift : base;
    }));
  const ref = gen(refRows, 0);
  const test = caseRows === 'self' ? ref : gen(caseRows, 5);
  const mk = (X) => ({
    header: Array.from({ length: m }, (_, j) => `S${j}`),
    colNames: Array.from({ length: m }, (_, j) => `S${j}`),
    times: X.map((_, i) => String(i + 1)),
    X,
    n: X.length,
    m,
  });
  const matrix = mk(test);
  const caseDef = {
    case_id: id,
    dataset: 'synthetic',
    csv: '<synthetic>',
    time_col: null,
    target_cols: [],
    process_description: 'synthetic degenerate-input fixture',
    control,
  };
  const w = win || { start: 0, end: matrix.n };
  return {
    caseDef,
    matrix,
    faultWindow: w,
    reference: { case_id: `${id}__ref`, matrix: mk(ref), is_self: caseRows === 'self' },
    log: () => {},
    faultRows: () => matrix.X.slice(w.start, w.end),
  };
}

const EDGE = [
  ['constant-columns (2 of 6 zero-variance) + step fault', syntheticCtx({
    id: 'edge_constant_cols_fault', refRows: 200, caseRows: 200, constantCols: [1, 3], m: 6,
    win: { start: 100, end: 200 },
  })],
  ['all columns constant, case == reference', syntheticCtx({
    id: 'edge_all_constant', refRows: 120, caseRows: 'self', constantCols: [0, 1, 2, 3, 4, 5], m: 6, control: true,
  })],
  ['3-row reference', syntheticCtx({ id: 'edge_tiny_ref', refRows: 3, caseRows: 3, m: 3, control: true })],
  ['1-row reference and 1-row case', syntheticCtx({ id: 'edge_single_row', refRows: 1, caseRows: 1, m: 2, control: true })],
];

const edgeRows = [];
for (const [label, ctx] of EDGE) {
  for (const algo of ALGOS) {
    let out;
    let problems = [];
    try {
      out = await algo.run(ctx);
      problems = checkResult(out, algo.meta, ctx.caseDef);
    } catch (e) {
      problems = [`threw: ${e.message}`];
      out = null;
    }
    const ok = problems.length === 0;
    ok ? pass++ : fail++;
    if (!ok) failures.push(`${algo.meta.id} / ${ctx.caseDef.case_id}: ${problems.join('; ')}`);
    edgeRows.push({
      algo: algo.meta.id,
      case_id: ctx.caseDef.case_id,
      label,
      verdict: out?.verdict,
      rate: out?.detection?.detection_rate,
      status: ok ? 'PASS' : 'FAIL',
    });
  }
}

// ----------------------------------------------------------------- report

console.log('\n=== Classical baseline gate: 5 algorithms x 12 cases = 60 runs (each run twice) ===\n');
console.log(
  pad('algorithm', 14),
  pad('case_id', 32),
  pad('verdict', 8),
  pad('det_rate', 9),
  pad('params', 22),
  pad('top3(first 2)', 34),
  'runtime_ms',
);
console.log('-'.repeat(140));
for (const r of rows) {
  console.log(
    pad(r.algo, 14),
    pad(r.case_id, 32),
    pad(r.verdict, 8),
    pad(Number.isFinite(r.rate) ? r.rate.toFixed(4) : String(r.rate), 9),
    pad(r.params, 22),
    pad(r.top3.length ? r.top3.join(' | ') : `vars: ${r.vars.join(',') || '-'}`, 34),
    r.runtime_ms,
  );
}

const byAlgo = new Map();
for (const r of rows) {
  const b = byAlgo.get(r.algo) || { runs: 0, faults: 0, falseAlarms: 0, controls: 0, sumRate: 0, ms: 0 };
  b.runs++;
  if (r.control) {
    b.controls++;
    if (r.verdict === 'fault') b.falseAlarms++;
  }
  if (r.verdict === 'fault') b.faults++;
  b.sumRate += Number.isFinite(r.rate) ? r.rate : 0;
  b.ms += Number.isFinite(r.runtime_ms) ? r.runtime_ms : 0;
  byAlgo.set(r.algo, b);
}

console.log('-'.repeat(140));
console.log('\n--- per-algorithm summary (detection rates are observed, never tuned) ---\n');
for (const [id, b] of byAlgo) {
  console.log(
    pad(id, 14),
    `fault-verdicts ${b.faults}/${b.runs}`,
    ` control false alarms ${b.falseAlarms}/${b.controls}`,
    ` mean detection_rate ${(b.sumRate / b.runs).toFixed(4)}`,
    ` mean runtime ${(b.ms / b.runs).toFixed(0)}ms`,
  );
}

console.log('\n--- synthetic degenerate-input edge cases (no NaN, no throw) ---\n');
console.log(pad('algorithm', 14), pad('fixture', 42), pad('verdict', 8), pad('det_rate', 9), 'status');
console.log('-'.repeat(90));
for (const r of edgeRows) {
  console.log(
    pad(r.algo, 14),
    pad(r.case_id, 42),
    pad(r.verdict, 8),
    pad(Number.isFinite(r.rate) ? r.rate.toFixed(4) : String(r.rate), 9),
    r.status,
  );
}

if (failures.length) {
  console.log('\n--- failures ---');
  for (const f of failures) console.log(' ', f);
}
console.log(`\nPASS ${pass}  FAIL ${fail}`);
process.exit(fail === 0 ? 0 : 1);
