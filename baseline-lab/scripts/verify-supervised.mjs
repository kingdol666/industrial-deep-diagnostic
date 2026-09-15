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
//   6. user upload    — the three supervised comparators must be usable on a
//                       user's OWN labelled file: trained on it, predicting with
//                       the USER's class strings, deterministic across runs,
//                       refusing (not inventing) when no labels were supplied,
//                       and erroring on a column mismatch.
//
// The TEP truth mapping printed at the end is REPORT-ONLY: it is deliberately
// not a gate, because tuning the baselines against the benchmark truth would
// invalidate the comparison.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { loadCasesRaw, loadCaseForAlgorithm } from '../server/utils/paths.mjs';
import { buildContext, loadUserTrainingCorpus } from '../server/utils/algorithms/_shared.mjs';
import { createUpload, deleteUpload } from '../server/utils/uploads.mjs';
import { runOne } from '../server/utils/runner.mjs';
import { makeRng } from '../server/utils/linalg.mjs';
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
  // The three classifiers train on TEP *and* on a user-supplied labelled file,
  // which is what makes them runnable on an upload (diagnosis.mjs gates on this
  // list). ae-reconstruction is not claimed here either way: this gate only
  // requires that every module keeps 'tep' and that all three classifiers
  // declare 'custom'.
  check(Array.isArray(m.domains) && m.domains.includes('tep'), `${tag} domains include 'tep'`);
  if (m.kind === 'classifier') {
    check(m.domains.includes('custom'), `${tag} domains include 'custom' (usable on an upload)`);
  }
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

// ================================================== gate 6: the user's OWN data
//
// The three classifiers must be usable on an uploaded dataset — which is only
// honest if they train on a LABELLED FILE THE USER SUPPLIES. This section
// exercises the real production path end to end:
//
//   uploads.createUpload(buffer, name, { training_buffer, training_filename, label_column })
//     -> paths.loadCaseForAlgorithm(meta.case_id)      (the upload store's own meta)
//     -> algorithms/_shared.buildContext()             (ctx.training / ctx.is_upload)
//     -> runner.runOne()  and  mod.run(ctx)            (the algorithms themselves)
//
// The corpus is synthetic and deterministic (3 classes x 60 rows x 3 sensors,
// seeded generator — no Math.random), so "the user's own class names" can be
// asserted exactly: the expected labels are known and are NOT TEP names.

const SYNTH_COLS = ['sensor_a', 'sensor_b', 'sensor_c'];
const SYNTH_LABEL_COL = 'fault_label';
const SYNTH_ROWS_PER_CLASS = 60;
const SYNTH_CLASSES = [
  // Distinct steady levels + a slow oscillation, so the per-window mean really
  // discriminates the classes; the noise stays well below the class separation.
  { label: 'healthy', mu: [50.0, 12.0, 200.0], amp: [0.6, 0.30, 1.4] },
  { label: 'bearing_wear', mu: [54.5, 15.6, 206.5], amp: [0.7, 0.35, 1.6] },
  { label: 'valve_stiction', mu: [45.5, 9.4, 192.5], amp: [0.5, 0.25, 1.2] },
];
const SYNTH_USER_LABELS = SYNTH_CLASSES.map((c) => c.label).slice().sort();
const PLANTED_CLASS = 'valve_stiction';
const SYNTH_DIAG_ROWS = 150;

/** Box-Muller on the lab's seeded xorshift stream (deterministic, no Math.random). */
function gauss(rng) {
  let u = rng();
  if (u < 1e-12) u = 1e-12;
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
}

function synthBlock(spec, n, rng, phase) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push(SYNTH_COLS.map((_, j) => spec.mu[j]
      + spec.amp[j] * Math.sin((i + phase) / (13 + 6 * j))
      + gauss(rng) * spec.amp[j] * 0.4));
  }
  return out;
}

function rowsToCsv(header, rows) {
  const fmt = (v) => (typeof v === 'number' ? v.toFixed(6) : String(v));
  return [header.join(','), ...rows.map((r) => r.map(fmt).join(','))].join('\n');
}

// The training file: 3 classes x 60 labelled rows, columns in a DIFFERENT order
// than the diagnosis file (the join must be by NAME, not by position).
const trainRng = makeRng(20240917);
const trainRows = [];
for (let k = 0; k < SYNTH_CLASSES.length; k++) {
  for (const row of synthBlock(SYNTH_CLASSES[k], SYNTH_ROWS_PER_CLASS, trainRng, k * 7)) {
    trainRows.push([row[1], row[2], row[0], SYNTH_CLASSES[k].label]); // b, c, a, label
  }
}
const trainHeader = [SYNTH_COLS[1], SYNTH_COLS[2], SYNTH_COLS[0], SYNTH_LABEL_COL];
const trainCsv = rowsToCsv(trainHeader, trainRows);

// The unlabelled file to diagnose: same sensor names, a different row count.
const diagRng = makeRng(4242);
const diagSpec = SYNTH_CLASSES.find((c) => c.label === PLANTED_CLASS);
const diagRows = synthBlock(diagSpec, SYNTH_DIAG_ROWS, diagRng, 3.5);
const diagCsv = rowsToCsv(SYNTH_COLS, diagRows);

// A deliberate column mismatch: the diagnosis file renames sensor_c.
const mismatchCsv = rowsToCsv([SYNTH_COLS[0], SYNTH_COLS[1], 'sensor_d'], diagRows);

// A file too small to train on: 2 classes x 10 rows (the upload store's own
// minimum is 20 rows), which cannot yield enough window samples.
const tinyRng = makeRng(99);
const tinyRows = [
  ...synthBlock(SYNTH_CLASSES[0], 10, tinyRng, 0).map((r) => [...r, SYNTH_CLASSES[0].label]),
  ...synthBlock(SYNTH_CLASSES[1], 10, tinyRng, 1).map((r) => [...r, SYNTH_CLASSES[1].label]),
];
const tinyCsv = rowsToCsv([...SYNTH_COLS, SYNTH_LABEL_COL], tinyRows);

// A single-class file (impossible through the upload store, which requires >= 2
// classes — checked on the loader directly, as the defensive layer of last resort).
const oneClassCsv = rowsToCsv(
  [...SYNTH_COLS, SYNTH_LABEL_COL],
  synthBlock(SYNTH_CLASSES[0], 60, makeRng(7), 0).map((r) => [...r, SYNTH_CLASSES[0].label]),
);

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'idl-verify-supervised-'));
const CLASSIFIERS = [xgb, rf, mlp];
const uploadIds = [];
let userMeta = null;
let controlMeta = null;
let mismatchMeta = null;
let tinyMeta = null;

console.log('\n=== GATE 6: user-supplied labelled training data (upload path) ===\n');
try {
  fs.writeFileSync(path.join(tmpDir, 'training.csv'), trainCsv, 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'diagnosis.csv'), diagCsv, 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'diagnosis_mismatch.csv'), mismatchCsv, 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'tiny_training.csv'), tinyCsv, 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'one_class.csv'), oneClassCsv, 'utf8');

  const ingest = (csv, name, options = {}) => {
    const meta = createUpload(Buffer.from(csv, 'utf8'), name, options);
    uploadIds.push(meta.upload_id);
    return meta;
  };

  // ---- 1. an upload WITH labelled training data --------------------------
  userMeta = ingest(diagCsv, 'synthetic_user_diagnosis.csv', {
    label: 'verify-supervised synthetic user dataset',
    process_description: 'Deterministic synthetic 3-sensor record generated by scripts/verify-supervised.mjs.',
    training_buffer: Buffer.from(trainCsv, 'utf8'),
    training_filename: 'synthetic_training_labels.csv',
    label_column: SYNTH_LABEL_COL,
    calibration_fraction: 0.3,
  });

  check(
    Boolean(userMeta.training) && userMeta.training.classes === SYNTH_CLASSES.length
      && userMeta.training.label_column === SYNTH_LABEL_COL,
    'upload store recorded the labelled training file (columns, 3 classes)',
  );
  check(fs.existsSync(userMeta.training.path), 'the training file was written to disk');

  const userCtx = buildContext(loadCaseForAlgorithm(userMeta.case_id));
  check(userCtx.is_upload === true, 'ctx.is_upload === true for the uploaded case');
  check(
    userCtx.training.available === true && userCtx.training.source === 'user-upload'
      && userCtx.training.path === userMeta.training.path,
    'ctx.training === { available: true, source: user-upload, path }',
  );
  check(
    userCtx.matrix.colNames.slice().sort().join('|') === SYNTH_COLS.slice().sort().join('|'),
    `the diagnosis matrix carries the synthetic columns (${userCtx.matrix.colNames.join(', ')})`,
  );

  console.log(`  upload ${userMeta.upload_id}: ${userMeta.rows} rows x ${userMeta.numeric_columns} cols, `
    + `training ${userMeta.training.rows} rows / ${userMeta.training.classes} classes `
    + `(label column '${userMeta.training.label_column}'), user labels: ${SYNTH_USER_LABELS.join(', ')}\n`);

  for (const mod of CLASSIFIERS) {
    const tag = `upload:${mod.meta.id}`;

    // --- through the real runner (status + scoring contract) ---
    const ran = await runOne({ algorithmId: mod.meta.id, caseId: userMeta.case_id });
    const o = ran.output || {};
    check(ran.status === 'executed', `${tag} status === executed`);
    check(ran.scored && ran.scored.scored === false, `${tag} upload run reported UNSCORED (no ground truth)`);

    // --- the answer must be the USER's classes ---
    check(o.applicable === true, `${tag} applicable === true on uploaded data`);
    check(Array.isArray(o.top3) && o.top3.length === SYNTH_CLASSES.length, `${tag} top3 has one entry per user class`);
    check(
      (o.top3 || []).every((l) => SYNTH_USER_LABELS.includes(l)),
      `${tag} top3 consists of the USER's label strings (${(o.top3 || []).join(' | ')})`,
    );
    check(
      (o.top3 || []).every((l) => !/IDV|Operating Conditions/i.test(l))
        && !/IDV|Operating Conditions/i.test(String(o.predicted_class)),
      `${tag} no TEP/IDV class name leaks into a user-trained prediction`,
    );
    check(o.predicted_class === o.top3[0], `${tag} predicted_class === top3[0]`);
    check(
      (o.class_probabilities || []).length === SYNTH_CLASSES.length
        && o.class_probabilities.every((p) => SYNTH_USER_LABELS.includes(p.label)),
      `${tag} class_probabilities use the user's labels only`,
    );
    check(
      o.training && o.training.source === 'user-upload' && o.training.classes === SYNTH_CLASSES.length
        && Array.isArray(o.training.class_names)
        && o.training.class_names.join('|') === SYNTH_USER_LABELS.join('|'),
      `${tag} training.class_names === the user's sorted labels`,
    );
    check(
      o.training && o.training.raw_labelled_rows === SYNTH_CLASSES.length * SYNTH_ROWS_PER_CLASS,
      `${tag} trained on all ${SYNTH_CLASSES.length * SYNTH_ROWS_PER_CLASS} user rows`,
    );
    check(o.training && o.training.training_file === 'synthetic_training_labels.csv', `${tag} training file recorded`);
    check(
      typeof o.reasoning === 'string' && /user/i.test(o.reasoning) && !/16 named classes/.test(o.reasoning),
      `${tag} reasoning describes user-supplied training, not the TEP corpus`,
    );

    // --- the planted class must actually be recovered (the model works) ---
    check(
      o.predicted_class === PLANTED_CLASS,
      `${tag} recovers the planted class '${PLANTED_CLASS}' (got '${o.predicted_class}')`,
    );

    // --- determinism: same answer on a repeat call ... ---
    const again = await mod.run(buildContext(loadCaseForAlgorithm(userMeta.case_id)));
    check(
      again.predicted_class === o.predicted_class
        && JSON.stringify(again.top3) === JSON.stringify(o.top3)
        && JSON.stringify(again.class_probabilities) === JSON.stringify(o.class_probabilities),
      `${tag} repeat call reproduces predicted_class, top3 and probabilities`,
    );

    // --- ... and after a COLD retrain (the cache is not what makes it stable) ---
    mod.__resetCacheForTest();
    const cold = await mod.run(buildContext(loadCaseForAlgorithm(userMeta.case_id)));
    check(
      cold.predicted_class === o.predicted_class && JSON.stringify(cold.top3) === JSON.stringify(o.top3),
      `${tag} cold-cache retrain from the user's file reproduces predicted_class and top3`,
    );
    check(
      cold.training.seconds > 0 && cold.training.cached === false,
      `${tag} cold-cache retrain really retrained (${cold.training.seconds}s)`,
    );

    // --- the cache must be keyed on the training source ---
    mod.__resetCacheForTest();
    const ctrlCtx0 = buildContext(loadCaseForAlgorithm('tep_d01_ac_feed_ratio'));
    await mod.run(ctrlCtx0);                       // trains + caches the TEP model
    const backToUser = await mod.run(buildContext(loadCaseForAlgorithm(userMeta.case_id)));
    check(
      backToUser.predicted_class === o.predicted_class && backToUser.training.source === 'user-upload',
      `${tag} a cached TEP model is NOT reused for the user's data (cache keyed on the training source)`,
    );
  }

  // ---- 2. an upload WITHOUT labels: refuse, never invent -------------------
  console.log('');
  controlMeta = ingest(diagCsv, 'synthetic_user_diagnosis_unlabelled.csv', {
    label: 'verify-supervised synthetic user dataset (no labels)',
  });
  check(controlMeta.training === null, 'the unlabelled upload carries no training file');

  const ctrlCtx = buildContext(loadCaseForAlgorithm(controlMeta.case_id));
  check(
    ctrlCtx.training.available === false && ctrlCtx.training.source === null
      && typeof ctrlCtx.training.reason === 'string' && ctrlCtx.training.reason.length > 0,
    'ctx.training === { available: false, source: null, reason }',
  );

  for (const mod of CLASSIFIERS) {
    const tag = `control:${mod.meta.id}`;
    const out = await mod.run(buildContext(loadCaseForAlgorithm(controlMeta.case_id)));
    check(out.status === 'not_applicable', `${tag} status === not_applicable`);
    check(out.applicable === false && out.predicted_class === 'N/A' && out.verdict === null, `${tag} no verdict asserted`);
    check(
      Array.isArray(out.top3) && out.top3.length === 0
        && Array.isArray(out.class_probabilities) && out.class_probabilities.length === 0,
      `${tag} no class was invented (top3 and class_probabilities empty)`,
    );
    check(out.training.rows === 0, `${tag} no model was trained`);
    check(out.reasoning === ctrlCtx.training.reason, `${tag} reasoning === ctx.training.reason`);
    check(/labelled training/i.test(out.reasoning), `${tag} reasoning tells the user what to upload`);

    const ran = await runOne({ algorithmId: mod.meta.id, caseId: controlMeta.case_id });
    check(ran.status === 'not_applicable', `${tag} runner reports not_applicable (not a fabricated executed run)`);
  }

  // ---- 3. column mismatch: a hard error, never a silent misalignment -------
  console.log('');
  mismatchMeta = ingest(mismatchCsv, 'synthetic_user_diagnosis_mismatched_columns.csv', {
    label: 'verify-supervised synthetic user dataset (column mismatch)',
    training_buffer: Buffer.from(trainCsv, 'utf8'),
    training_filename: 'synthetic_training_labels.csv',
    label_column: SYNTH_LABEL_COL,
  });

  for (const mod of CLASSIFIERS) {
    const tag = `mismatch:${mod.meta.id}`;
    let msg = null;
    try {
      await mod.run(buildContext(loadCaseForAlgorithm(mismatchMeta.case_id)));
    } catch (err) {
      msg = String(err && err.message ? err.message : err);
    }
    check(msg !== null, `${tag} mismatched feature columns throw`);
    check(Boolean(msg) && /sensor_d/.test(msg) && /sensor_c/.test(msg), `${tag} the error names the mismatched columns`);
    check(Boolean(msg) && /BY NAME/i.test(msg), `${tag} the error explains that columns are matched by name`);

    const ran = await runOne({ algorithmId: mod.meta.id, caseId: mismatchMeta.case_id });
    check(
      ran.status === 'error' && (ran.output?.top3 || []).length === 0,
      `${tag} the runner reports status=error with no prediction`,
    );
  }

  // ---- 4. too little labelled data: refuse, do not train a degenerate model -
  console.log('');
  tinyMeta = ingest(diagCsv, 'synthetic_user_diagnosis_small_training.csv', {
    label: 'verify-supervised synthetic user dataset (tiny training file)',
    training_buffer: Buffer.from(tinyCsv, 'utf8'),
    training_filename: 'tiny_training.csv',
    label_column: SYNTH_LABEL_COL,
  });
  check(tinyMeta.training.rows === 2 * 10, 'the 2 x 10-row labelled file was accepted by the upload store');

  for (const mod of CLASSIFIERS) {
    const tag = `tiny:${mod.meta.id}`;
    let msg = null;
    try {
      await mod.run(buildContext(loadCaseForAlgorithm(tinyMeta.case_id)));
    } catch (err) {
      msg = String(err && err.message ? err.message : err);
    }
    check(Boolean(msg) && /training window/i.test(msg) && /at least \d+/i.test(msg),
      `${tag} a 20-row labelled file is refused with a clear message`);
  }

  // ---- 5. one class only / no label column: refused at the loader ---------
  let oneClassMsg = null;
  try {
    loadUserTrainingCorpus(
      { path: path.join(tmpDir, 'one_class.csv'), label_column: SYNTH_LABEL_COL, original_name: 'one_class.csv' },
      SYNTH_COLS,
    );
  } catch (err) {
    oneClassMsg = String(err && err.message ? err.message : err);
  }
  check(
    Boolean(oneClassMsg) && /at least 2/i.test(oneClassMsg),
    'a single-class labelled file is refused (a classifier needs >= 2 classes)',
  );

  // Defensive: the upload store validates the label column at ingest, so this
  // state is unreachable through the HTTP path — the loader must still refuse it
  // precisely rather than train on a guess.
  let noLabelMsg = null;
  try {
    loadUserTrainingCorpus(
      { path: path.join(tmpDir, 'training.csv'), label_column: 'not_a_column', original_name: 'synthetic_training_labels.csv' },
      SYNTH_COLS,
    );
  } catch (err) {
    noLabelMsg = String(err && err.message ? err.message : err);
  }
  check(
    Boolean(noLabelMsg) && /not_a_column/.test(noLabelMsg) && /label column/i.test(noLabelMsg),
    'a training file without the declared label column is refused by name',
  );

  // ------------------------------------------------- printed prediction output
  if (userMeta) {
    console.log('\n--- REAL prediction output on the synthetic user dataset (3 user classes) ---\n');
    for (const mod of CLASSIFIERS) {
      const out = await mod.run(buildContext(loadCaseForAlgorithm(userMeta.case_id)));
      console.log(`${mod.meta.id.padEnd(18)} status=executed  verdict=${String(out.verdict).padEnd(7)} `
        + `predicted='${out.predicted_class}'  (planted class: ${PLANTED_CLASS})`);
      console.log(`   probabilities: ${out.class_probabilities.map((p) => `${p.label} = ${p.p.toFixed(4)}`).join('  |  ')}`);
      console.log(`   training: ${out.training.rows} window samples from ${out.training.raw_labelled_rows} user rows `
        + `(${out.training.classes} classes, window ${out.training.window} / stride ${out.training.stride}), `
        + `${out.training.seconds}s${out.training.cached ? ' (cached)' : ''}, train accuracy ${out.detection.train_accuracy}`);
      console.log(`   reasoning: ${out.reasoning}`);
      console.log('');
    }
  }
} finally {
  // Leave nothing behind: the uploads and the temp CSVs are scratch artifacts.
  for (const id of uploadIds) {
    try { deleteUpload(id); } catch { /* cleanup must not mask a real failure */ }
  }
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
  if (uploadIds.length) console.log(`  cleaned up ${uploadIds.length} scratch upload(s) and the temp CSVs\n`);
}

// ------------------------------------------------------------- final verdict

console.log('');
if (failures.length) {
  console.log('--- failures ---');
  for (const f of failures) console.log('  x', f);
  console.log('');
}
console.log(`PASS ${pass}  FAIL ${fail}`);
process.exit(fail === 0 ? 0 : 1);
