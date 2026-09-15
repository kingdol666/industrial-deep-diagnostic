#!/usr/bin/env node
// verify-supervised.mjs — self-verification gate for the four supervised /
// deep-learning baselines (xgb-gbdt, rf-forest, mlp-classifier, ae-reconstruction).
//
// GATES (a failure makes the script exit non-zero):
//   1. applicability  — every non-TEP case MUST return applicable:false with an
//                       empty top3 and a null verdict; every TEP case MUST
//                       return a non-empty ranking (classifiers: top3;
//                       detector: variable_top3, plus top3 whenever it alarms).
//   2. training       — TEP cases must have trained on a non-empty corpus.
//   3. probabilities  — no NaN / Infinity / out-of-range values, and the top-5
//                       class probabilities must not exceed 1.
//   4. determinism    — a repeat call returns an identical ranking, AND a full
//                       retrain after clearing the model cache returns the same
//                       predicted class (the cache must not be what makes it
//                       reproducible).
//   5. metadata       — id / family / kind / domains / deterministic contract.
//
// The TEP truth mapping printed at the end is REPORT-ONLY: it is deliberately
// not a gate, because tuning the baselines against the benchmark truth would
// invalidate the comparison.

import { loadCasesRaw, loadCaseForAlgorithm } from '../server/utils/paths.mjs';
import { buildContext } from '../server/utils/algorithms/_shared.mjs';
import * as xgb from '../server/utils/algorithms/xgb.mjs';
import * as rf from '../server/utils/algorithms/rf.mjs';
import * as mlp from '../server/utils/algorithms/mlp.mjs';
import * as ae from '../server/utils/algorithms/ae.mjs';

const MODULES = [xgb, rf, mlp, ae];

/** case_id -> expected IDV index for the TEP scenarios (report-only sanity map). */
const EXPECTED_IDV = {
  tep_d00_normal_control: 0,
  tep_d01_ac_feed_ratio: 1,
  tep_d03_hard: 3,
  tep_d04_reactor_cooling_step: 4,
  tep_d07_header_pressure: 7,
  tep_d11_reactor_cooling_random: 11,
  tep_d14_reactor_valve_sticking: 14,
};

let pass = 0;
let fail = 0;
const failures = [];

function check(ok, label) {
  if (ok) pass++;
  else {
    fail++;
    failures.push(label);
  }
  return ok;
}

const pad = (s, n) => {
  const str = String(s);
  return str.length > n ? `${str.slice(0, n - 1)}…` : str.padEnd(n);
};
const num = (v) => (Number.isFinite(v) ? v : NaN);

// ------------------------------------------------------------- metadata gate

const EXPECTED_META = {
  'xgb-gbdt': { short: 'XGB', kind: 'classifier' },
  'rf-forest': { short: 'RF', kind: 'classifier' },
  'mlp-classifier': { short: 'MLP', kind: 'classifier' },
  'ae-reconstruction': { short: 'AE', kind: 'detector' },
};

for (const mod of MODULES) {
  const m = mod.meta;
  const tag = `meta:${m.id}`;
  const want = EXPECTED_META[m.id];
  check(!!want, `${tag} is one of the four expected algorithm ids`);
  if (!want) continue;
  check(m.short === want.short, `${tag} short === ${want.short}`);
  check(m.kind === want.kind, `${tag} kind === ${want.kind}`);
  check(m.family === 'supervised', `${tag} family === supervised`);
  check(m.deterministic === true, `${tag} deterministic === true`);
  check(m.requiresProvider === false, `${tag} requiresProvider === false`);
  check(m.needsReference === false, `${tag} needsReference === false`);
  check(m.needsTraining === true, `${tag} needsTraining === true`);
  check(
    Array.isArray(m.domains) && m.domains.length === 1 && m.domains[0] === 'tep',
    `${tag} domains === ['tep']`,
  );
  check(typeof m.description === 'string' && m.description.length > 40, `${tag} has a protocol description`);
  check(
    m.provenance && Array.isArray(m.provenance.basis) && m.provenance.basis.length > 0,
    `${tag} declares provenance.basis`,
  );
  check(typeof mod.run === 'function', `${tag} exports run(ctx)`);
}

// ------------------------------------------------------------------ main run

const cases = loadCasesRaw();
const table = [];
const outcomes = new Map(); // `${id}|${case_id}` -> result

for (const mod of MODULES) {
  for (const c of cases) {
    const caseDef = loadCaseForAlgorithm(c.case_id);
    const ctx = buildContext(caseDef);
    const out = await mod.run(ctx);
    outcomes.set(`${mod.meta.id}|${c.case_id}`, out);

    const tag = `${mod.meta.id}|${c.case_id}`;
    const isTep = caseDef.dataset === 'tep';
    const detectionRate = out.detection && Number.isFinite(out.detection.detection_rate)
      ? out.detection.detection_rate
      : null;

    // -- gate 1: applicability ------------------------------------------------
    if (!isTep) {
      check(out.applicable === false, `${tag} non-TEP => applicable === false`);
      check(Array.isArray(out.top3) && out.top3.length === 0, `${tag} non-TEP => top3 === []`);
      check(out.verdict === null, `${tag} non-TEP => verdict === null`);
      check(out.predicted_class === 'N/A', `${tag} non-TEP => predicted_class === 'N/A'`);
      check(
        typeof out.reasoning === 'string' && /TEP/.test(out.reasoning) && /no prediction/i.test(out.reasoning),
        `${tag} non-TEP => reasoning states the TEP-only limit and that no prediction is made`,
      );
      check(out.training.rows === 0, `${tag} non-TEP => no model was trained`);
    } else {
      check(out.applicable === true, `${tag} TEP => applicable === true`);
      if (mod.meta.kind === 'classifier') {
        check(Array.isArray(out.top3) && out.top3.length === 3, `${tag} TEP classifier => 3 ranked labels`);
      } else {
        check(
          Array.isArray(out.variable_top3) && out.variable_top3.length > 0,
          `${tag} TEP detector => non-empty variable_top3`,
        );
        const detectable = !!(out.detection && out.detection.detectable);
        check(
          !detectable || out.top3.length > 0,
          `${tag} TEP detector => non-empty top3 whenever it alarms`,
        );
      }
      // -- gate 2: training ---------------------------------------------------
      check(out.training.rows > 0, `${tag} TEP => trained on a non-empty corpus`);
      check(out.training.classes > 0, `${tag} TEP => trained on at least one class`);
      check(out.training.features > 0, `${tag} TEP => feature space declared`);
      check(
        typeof out.training.source === 'string' && out.training.source.length > 0,
        `${tag} TEP => training source recorded`,
      );
    }

    // -- gate 3: probabilities ------------------------------------------------
    const probs = out.class_probabilities || [];
    check(Array.isArray(probs), `${tag} class_probabilities is an array`);
    let probOk = true;
    let probSum = 0;
    for (const p of probs) {
      if (!Number.isFinite(p.p) || p.p < 0 || p.p > 1) probOk = false;
      else probSum += p.p;
      if (typeof p.label !== 'string' || !p.label) probOk = false;
    }
    check(probOk, `${tag} no NaN/Infinity/out-of-range class probabilities`);
    check(probSum <= 1 + 1e-6, `${tag} class probabilities do not exceed 1 (sum=${probSum.toFixed(6)})`);
    if (mod.meta.kind === 'classifier' && isTep) {
      check(probs.length > 0, `${tag} TEP classifier => non-empty class_probabilities`);
      check(
        out.predicted_class === out.top3[0],
        `${tag} predicted_class === top3[0]`,
      );
      if (probs.length) {
        check(probs[0].label === out.predicted_class, `${tag} predicted_class === argmax probability`);
      }
    } else if (mod.meta.kind === 'detector' && isTep) {
      check(
        Number.isFinite(out.detection.threshold),
        `${tag} TEP detector => finite threshold`,
      );
      check(
        Number.isFinite(out.detection.detection_rate) &&
          out.detection.detection_rate >= 0 &&
          out.detection.detection_rate <= 1,
        `${tag} TEP detector => detection_rate in [0,1]`,
      );
    }

    // -- gate 4a: repeat call determinism -------------------------------------
    const again = await mod.run(buildContext(loadCaseForAlgorithm(c.case_id)));
    check(
      again.predicted_class === out.predicted_class && JSON.stringify(again.top3) === JSON.stringify(out.top3),
      `${tag} repeat call reproduces predicted_class and top3`,
    );

    table.push({
      algorithm: mod.meta.id,
      case_id: c.case_id,
      dataset: caseDef.dataset,
      applicable: out.applicable,
      predicted_class: out.predicted_class,
      verdict: out.verdict,
      detection_rate: detectionRate,
      top1: out.top3.length ? out.top3[0] : out.variable_top3.length ? `var:${out.variable_top3[0]}` : '-',
      train_rows: out.training.rows,
      runtime_ms: out.runtime_ms,
      out,
      caseDef,
    });
  }
}

// ------------------------------------------------- gate 4b: real retrain check

const PROBE_CASE = 'tep_d01_ac_feed_ratio';
for (const mod of MODULES) {
  const key = `${mod.meta.id}|${PROBE_CASE}`;
  const before = outcomes.get(key);
  mod.__resetCacheForTest();
  const after = await mod.run(buildContext(loadCaseForAlgorithm(PROBE_CASE)));
  check(
    after.predicted_class === before.predicted_class &&
      JSON.stringify(after.top3) === JSON.stringify(before.top3) &&
      after.training.rows === before.training.rows,
    `${mod.meta.id} full retrain from a cold cache reproduces predicted_class and top3`,
  );
  check(
    after.training.seconds > 0,
    `${mod.meta.id} cold-cache retrain reports a training duration`,
  );
}

// ------------------------------------------------------------------- output

console.log('\n=== Supervised / deep-learning baselines — verification ===\n');
console.log(
  pad('algorithm', 18),
  pad('case_id', 32),
  pad('applic', 7),
  pad('predicted_class', 46),
  pad('verdict', 8),
  pad('det_rate', 9),
  pad('top1', 34),
  pad('rows', 6),
  'runtime_ms',
);
console.log('-'.repeat(170));
for (const r of table) {
  console.log(
    pad(r.algorithm, 18),
    pad(r.case_id, 32),
    pad(r.applicable, 7),
    pad(r.predicted_class, 46),
    pad(r.verdict === null ? 'null' : r.verdict, 8),
    pad(r.detection_rate === null ? '-' : r.detection_rate.toFixed(4), 9),
    pad(r.top1, 34),
    pad(r.train_rows, 6),
    r.runtime_ms,
  );
}
console.log('-'.repeat(170));

// ------------------------------------------------------- per-case detail

console.log('\n--- Ranked output per TEP case (full labels) ---\n');
for (const r of table) {
  if (r.dataset !== 'tep') continue;
  const o = r.out;
  console.log(`${r.algorithm} | ${r.case_id}`);
  if (o.class_probabilities.length) {
    console.log(`   probabilities: ${o.class_probabilities.map((p) => `${p.label} = ${p.p.toFixed(4)}`).join('  |  ')}`);
    console.log(
      `   train rows ${o.training.rows}, ${o.training.features} features, ${o.training.seconds}s` +
        `${o.training.cached ? ' (cached)' : ' (cold)'}, train accuracy ${o.detection.train_accuracy}`,
    );
  } else {
    console.log(
      `   detection ${(o.detection.detection_rate * 100).toFixed(2)}% above threshold ${o.detection.threshold}` +
        ` (pre-window ${(o.detection.pre_window_alarm_rate * 100).toFixed(2)}%), ${o.training.seconds}s${o.training.cached ? ' (cached)' : ' (cold)'}`,
    );
    console.log(`   variables: ${o.variable_top3.join(', ')}`);
    console.log(`   candidates: ${o.top3.join('  |  ') || '(none — no alarm)'}`);
  }
  console.log('');
}

// ------------------------------------------- report-only TEP truth comparison

console.log('--- REPORT ONLY (not a pass/fail gate): TEP prediction vs case-id mapping ---\n');
console.log(pad('algorithm', 18), pad('case_id', 32), pad('expected', 22), pad('observed IDV', 14), 'mark');
console.log('-'.repeat(96));
const sane = [];
for (const r of table) {
  if (r.dataset !== 'tep') continue;
  const expected = EXPECTED_IDV[r.case_id];
  let observed = null;
  const source = r.out.predicted_class !== 'N/A' ? r.out.predicted_class : (r.out.top3[0] || '');
  const m = /IDV\(?(\d+)\)?/.exec(source);
  if (m) observed = Number(m[1]);
  else if (/^Normal/.test(source)) observed = 0;
  const mark = observed === null ? 'n/a (no mapped candidate)' : observed === expected ? 'OK' : `MISS (expected IDV${expected})`;
  sane.push({ algorithm: r.algorithm, case_id: r.case_id, expected, observed, mark });
  console.log(
    pad(r.algorithm, 18),
    pad(r.case_id, 32),
    pad(expected === 0 ? 'normal (class 0)' : `IDV${expected}`, 22),
    pad(observed === null ? '-' : observed === 0 ? 'normal' : `IDV${observed}`, 14),
    mark,
  );
}
const okCount = sane.filter((s) => s.mark === 'OK').length;
console.log('-'.repeat(96));
console.log(`rank-1 correct on ${okCount}/${sane.length} TEP cases (all algorithms pooled) — reported, never used for tuning.`);

// ------------------------------------------------------------- final verdict

console.log('');
if (failures.length) {
  console.log('--- failures ---');
  for (const f of failures) console.log('  x', f);
  console.log('');
}
console.log(`PASS ${pass}  FAIL ${fail}`);
process.exit(fail === 0 ? 0 : 1);
