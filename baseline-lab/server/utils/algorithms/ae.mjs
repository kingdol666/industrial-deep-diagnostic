// Autoencoder reconstruction anomaly detector — real backprop, unsupervised.
//
// PROTOCOL
// --------
// Training source : the NORMAL run of the LABELLED TEP corpus shipped inside
//                   the FaultExplainer clone (fault0.csv, y === 0) via
//                   dataset.mjs#loadFeTrainingSet(). Rows are individual
//                   time samples (52 columns), NOT window aggregates — the
//                   detector scores one row at a time.
// Standardisation : per-column mean/sd of the NORMAL training rows only, so the
//                   autoencoder never sees the case under test.
// Network         : 52 -> 16 -> 6 -> 16 -> 52, tanh activations on the three
//                   hidden layers, linear reconstruction output, MSE loss,
//                   Xavier-uniform init drawn from makeRng(SEED).
// Optimiser       : mini-batch momentum SGD, 100 epochs, batch 64, lr 0.01,
//                   momentum 0.9, global-norm gradient clipping (5.0).
// Score           : per-row squared reconstruction error ||x - x_hat||^2 on the
//                   standardised input.
// Threshold       : 99th percentile of that score over the NORMAL TRAINING rows
//                   (never over the case under test).
// Diagnosis       : the detector itself produces a VARIABLE ranking (mean
//                   squared residual per column over the fault window), which is
//                   then mapped to TEP cause candidates by the shared,
//                   explicitly knowledge-based step in tep-affinity.mjs —
//                   exactly as the classical detectors do.
//
// APPLICABILITY LIMIT (honesty requirement)
// -----------------------------------------
// The normal-behaviour model is learned from TEP data only. For any non-TEP case
// this module returns applicable:false and makes no claim at all.

import { makeRng, shuffle, colStats, quantile } from '../linalg.mjs';
import { loadFeTrainingSet } from '../dataset.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'ae-reconstruction',
  label: '自编码器重构异常检测',
  short: 'AE',
  family: 'supervised',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: false,
  needsTraining: true,
  domains: ['tep', 'custom'],
  description:
    'Autoencoder (52->16->6->16->52, tanh, linear output) trained by hand-written backpropagation with MSE loss on the NORMAL TEP run only; per-row squared reconstruction error scored against its 99th training-percentile threshold, residual ranking mapped to TEP causes through the published variable-affinity table.',
  provenance: {
    basis: ['sakurada2014anomaly', 'hinton2006reducing'],
    repo: null,
    note:
      'Dependency-free reimplementation of the reconstruction-error autoencoder detector; the normal-only training protocol and the 99th-percentile limit follow the classical unsupervised anomaly-detection setup.',
  },
};

// ------------------------------------------------------------------ config

export const SEED = 20240917;
const HIDDEN = [16, 6, 16];
const EPOCHS = 100;
const BATCH_SIZE = 64;
const LR = 0.01;
const MOMENTUM = 0.9;
const CLIP_NORM = 5.0;
export const ALARM_Q = 0.99;
const MIN_ALARM_RATE = 0.05;

// ------------------------------------------------------------------- corpus

let CORPUS = null;

/**
 * The "normal" corpus the autoencoder trains on.
 *
 * TEP  -> the normal rows of FaultExplainer's labelled runs (published protocol).
 * UPLOAD -> the upload's own CALIBRATION SEGMENT. The AE is unsupervised, so an
 *   unlabelled record is enough; this is what makes it usable on a user's
 *   process. It is never cached process-wide, because a model trained on one
 *   user's record must not be reused for another's.
 */
function loadCorpus(override = null) {
  if (override) {
    const X = override.X.map((r) => Array.from(r));
    if (!X.length) throw new Error('calibration segment is empty — nothing to train the autoencoder on');
    return {
      cols: override.cols.slice(),
      X,
      normal: X.map((_, i) => i),
      labelNames: ['Normal (upload calibration segment)'],
      source: override.source,
      totalRows: X.length,
      from_upload: true,
    };
  }
  if (CORPUS) return CORPUS;
  const t = loadFeTrainingSet();
  const normal = [];
  for (let i = 0; i < t.y.length; i++) if (t.y[i] === 0) normal.push(i);
  if (!normal.length) throw new Error('training corpus contains no normal (y === 0) rows');
  CORPUS = {
    cols: t.cols,
    X: t.X,
    normal,
    labelNames: t.labelNames,
    source: t.source,
    totalRows: t.X.length,
    from_upload: false,
  };
  return CORPUS;
}

function alignmentPerm(trainCols, caseCols) {
  const m = trainCols.length;
  const pos = new Map(trainCols.map((c, i) => [c, i]));
  const perm = new Int32Array(m).fill(-1);
  let matched = 0;
  for (let c = 0; c < caseCols.length; c++) {
    const p = pos.get(caseCols[c]);
    if (p === undefined) continue;
    if (perm[p] !== -1) throw new Error(`duplicate canonical column in case matrix: ${caseCols[c]}`);
    perm[p] = c;
    matched++;
  }
  const unmatched = [];
  for (let p = 0; p < m; p++) if (perm[p] === -1) unmatched.push(trainCols[p]);
  if (matched !== m || caseCols.length !== m || unmatched.length) {
    throw new Error(
      `column alignment failed: case matrix has ${caseCols.length} columns, training corpus has ${m}; ` +
      `matched ${matched}; missing canonical columns: [${unmatched.slice(0, 8).join(', ')}]`,
    );
  }
  return perm;
}

// ------------------------------------------------------------------ network

function gauss(rng) {
  let u = rng();
  if (u < 1e-12) u = 1e-12;
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Xavier-uniform init: U(-a, a), a = sqrt(6 / (fanIn + fanOut)). */
function initLayer(rng, fanIn, fanOut) {
  const a = Math.sqrt(6 / (fanIn + fanOut));
  const W = new Float64Array(fanIn * fanOut);
  for (let i = 0; i < W.length; i++) W[i] = (rng() * 2 - 1) * a;
  return { W, b: new Float64Array(fanOut), fanIn, fanOut };
}

function forward(net, x, B) {
  const A = [];
  let prev = x;
  let prevDim = net.layers[0].fanIn;
  for (let li = 0; li < net.layers.length; li++) {
    const l = net.layers[li];
    const Z = new Float64Array(B * l.fanOut);
    const out = new Float64Array(B * l.fanOut);
    const linear = li === net.layers.length - 1; // linear reconstruction output
    for (let i = 0; i < B; i++) {
      for (let o = 0; o < l.fanOut; o++) {
        let s = l.b[o];
        for (let j = 0; j < l.fanIn; j++) s += prev[i * prevDim + j] * l.W[j * l.fanOut + o];
        Z[i * l.fanOut + o] = s;
        out[i * l.fanOut + o] = linear ? s : Math.tanh(s);
      }
    }
    A.push({ Z, A: out });
    prev = out;
    prevDim = l.fanOut;
  }
  return A;
}

function zeroVelocity(net) {
  return net.layers.map((l) => ({ W: new Float64Array(l.W.length), b: new Float64Array(l.b.length) }));
}

function clipByGlobalNorm(tensors, maxNorm) {
  let sq = 0;
  for (const t of tensors) for (let i = 0; i < t.length; i++) sq += t[i] * t[i];
  const norm = Math.sqrt(sq);
  if (!Number.isFinite(norm)) return { norm: Infinity, scale: 0 };
  if (norm <= maxNorm || norm === 0) return { norm, scale: 1 };
  return { norm, scale: maxNorm / norm };
}

function trainBatch(net, X, m, idx, B, lr, momentum, velocity) {
  const xb = new Float64Array(B * m);
  for (let i = 0; i < B; i++) xb.set(X.subarray(idx[i] * m, idx[i] * m + m), i * m);

  const A = forward(net, xb, B);
  const A1 = A[0].A;
  const A2 = A[1].A;
  const A3 = A[2].A;
  const Xhat = A[3].A;
  const [l1, l2, l3, l4] = net.layers;

  let loss = 0;
  for (let i = 0; i < B * m; i++) {
    const d = xb[i] - Xhat[i];
    loss += d * d;
  }
  loss /= B * m;

  // dL/dXhat = -2 (x - xhat) / (B m)
  const dZ4 = new Float64Array(B * m);
  for (let i = 0; i < B * m; i++) dZ4[i] = (-2 * (xb[i] - Xhat[i])) / (B * m);

  const g4 = { W: new Float64Array(l4.W.length), b: new Float64Array(l4.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l4.fanIn; j++) {
      const a = A3[i * l4.fanIn + j];
      if (a === 0) continue;
      for (let o = 0; o < l4.fanOut; o++) g4.W[j * l4.fanOut + o] += a * dZ4[i * l4.fanOut + o];
    }
    for (let o = 0; o < l4.fanOut; o++) g4.b[o] += dZ4[i * l4.fanOut + o];
  }

  const dA3 = new Float64Array(B * l3.fanOut);
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l3.fanOut; j++) {
      let s = 0;
      for (let o = 0; o < l4.fanOut; o++) s += dZ4[i * l4.fanOut + o] * l4.W[j * l4.fanOut + o];
      dA3[i * l3.fanOut + j] = s;
    }
  }
  const dZ3 = new Float64Array(B * l3.fanOut);
  for (let i = 0; i < B * l3.fanOut; i++) dZ3[i] = dA3[i] * (1 - A3[i] * A3[i]); // tanh'

  const g3 = { W: new Float64Array(l3.W.length), b: new Float64Array(l3.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l3.fanIn; j++) {
      const a = A2[i * l3.fanIn + j];
      if (a === 0) continue;
      for (let o = 0; o < l3.fanOut; o++) g3.W[j * l3.fanOut + o] += a * dZ3[i * l3.fanOut + o];
    }
    for (let o = 0; o < l3.fanOut; o++) g3.b[o] += dZ3[i * l3.fanOut + o];
  }

  const dA2 = new Float64Array(B * l2.fanOut);
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l2.fanOut; j++) {
      let s = 0;
      for (let o = 0; o < l3.fanOut; o++) s += dZ3[i * l3.fanOut + o] * l3.W[j * l3.fanOut + o];
      dA2[i * l2.fanOut + j] = s;
    }
  }
  const dZ2 = new Float64Array(B * l2.fanOut);
  for (let i = 0; i < B * l2.fanOut; i++) dZ2[i] = dA2[i] * (1 - A2[i] * A2[i]);

  const g2 = { W: new Float64Array(l2.W.length), b: new Float64Array(l2.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l2.fanIn; j++) {
      const a = A1[i * l2.fanIn + j];
      if (a === 0) continue;
      for (let o = 0; o < l2.fanOut; o++) g2.W[j * l2.fanOut + o] += a * dZ2[i * l2.fanOut + o];
    }
    for (let o = 0; o < l2.fanOut; o++) g2.b[o] += dZ2[i * l2.fanOut + o];
  }

  const dA1 = new Float64Array(B * l1.fanOut);
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l1.fanOut; j++) {
      let s = 0;
      for (let o = 0; o < l2.fanOut; o++) s += dZ2[i * l2.fanOut + o] * l2.W[j * l2.fanOut + o];
      dA1[i * l1.fanOut + j] = s;
    }
  }
  const dZ1 = new Float64Array(B * l1.fanOut);
  for (let i = 0; i < B * l1.fanOut; i++) dZ1[i] = dA1[i] * (1 - A1[i] * A1[i]);

  const g1 = { W: new Float64Array(l1.W.length), b: new Float64Array(l1.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l1.fanIn; j++) {
      const a = xb[i * l1.fanIn + j];
      if (a === 0) continue;
      for (let o = 0; o < l1.fanOut; o++) g1.W[j * l1.fanOut + o] += a * dZ1[i * l1.fanOut + o];
    }
    for (let o = 0; o < l1.fanOut; o++) g1.b[o] += dZ1[i * l1.fanOut + o];
  }

  const grads = [g1, g2, g3, g4];
  let finite = Number.isFinite(loss);
  for (const g of grads) {
    for (let i = 0; i < g.W.length && finite; i++) if (!Number.isFinite(g.W[i])) finite = false;
    for (let i = 0; i < g.b.length && finite; i++) if (!Number.isFinite(g.b[i])) finite = false;
  }
  if (!finite) return { loss, finite: false };

  const { scale } = clipByGlobalNorm(
    [g1.W, g1.b, g2.W, g2.b, g3.W, g3.b, g4.W, g4.b],
    CLIP_NORM,
  );
  const pairs = [
    [net.layers[0], g1, velocity[0]],
    [net.layers[1], g2, velocity[1]],
    [net.layers[2], g3, velocity[2]],
    [net.layers[3], g4, velocity[3]],
  ];
  for (const [layer, g, v] of pairs) {
    for (let i = 0; i < layer.W.length; i++) {
      v.W[i] = momentum * v.W[i] - lr * g.W[i] * scale;
      layer.W[i] += v.W[i];
    }
    for (let i = 0; i < layer.b.length; i++) {
      v.b[i] = momentum * v.b[i] - lr * g.b[i] * scale;
      layer.b[i] += v.b[i];
    }
  }
  return { loss, finite: true };
}

/** Per-row squared reconstruction error and per-column squared residual. */
function reconstruct(net, xrow, m, residOut) {
  const A = forward(net, xrow, 1);
  const Xhat = A[3].A;
  let score = 0;
  for (let j = 0; j < m; j++) {
    const d = xrow[j] - Xhat[j];
    const sq = d * d;
    score += sq;
    if (residOut) residOut[j] += sq;
  }
  return Number.isFinite(score) ? score : Number.MAX_VALUE;
}

// -------------------------------------------------------------------- model

const MODEL_CACHE = new Map();

export function __resetCacheForTest() {
  MODEL_CACHE.clear();
}

function configKey(m) {
  return JSON.stringify({
    id: meta.id, seed: SEED, m, HIDDEN, EPOCHS, BATCH_SIZE, LR, MOMENTUM, CLIP_NORM, ALARM_Q,
  });
}

function fit(corpus) {
  const t0 = Date.now();
    // Corpus is PASSED IN: getModel already resolved and cache-keyed the correct one.
    // Re-loading here would train on TEP while the cache claimed an upload entry.
  const m = corpus.cols.length;
  const n = corpus.normal.length;

  const normalRows = corpus.normal.map((i) => corpus.X[i]);
  const { mu, sd } = colStats(normalRows, 1);
  const X = new Float64Array(n * m);
  for (let i = 0; i < n; i++) {
    const r = normalRows[i];
    for (let j = 0; j < m; j++) {
      const z = (r[j] - mu[j]) / sd[j];
      X[i * m + j] = Number.isFinite(z) ? z : 0;
    }
  }

  const rng = makeRng(SEED);
  const net = {
    layers: [
      initLayer(rng, m, HIDDEN[0]),
      initLayer(rng, HIDDEN[0], HIDDEN[1]),
      initLayer(rng, HIDDEN[1], HIDDEN[2]),
      initLayer(rng, HIDDEN[2], m),
    ],
  };
  const velocity = zeroVelocity(net);
  const shuffleRng = makeRng(SEED + 1);
  const all = Array.from({ length: n }, (_, i) => i);

  let firstLoss = null;
  let lastLoss = null;
  let skippedBatches = 0;
  for (let epoch = 0; epoch < EPOCHS; epoch++) {
    const order = shuffle(all, shuffleRng);
    let epochLoss = 0;
    let batches = 0;
    for (let s = 0; s < order.length; s += BATCH_SIZE) {
      const idx = order.slice(s, Math.min(s + BATCH_SIZE, order.length));
      const { loss, finite } = trainBatch(net, X, m, idx, idx.length, LR, MOMENTUM, velocity);
      if (!finite) {
        skippedBatches++;
        continue;
      }
      epochLoss += loss;
      batches++;
    }
    const meanLoss = batches ? epochLoss / batches : NaN;
    if (Number.isFinite(meanLoss)) {
      if (firstLoss === null) firstLoss = meanLoss;
      lastLoss = meanLoss;
    }
  }

  let weightsFinite = true;
  for (const l of net.layers) {
    for (let i = 0; i < l.W.length && weightsFinite; i++) if (!Number.isFinite(l.W[i])) weightsFinite = false;
    for (let i = 0; i < l.b.length && weightsFinite; i++) if (!Number.isFinite(l.b[i])) weightsFinite = false;
  }

  // Threshold = 99th percentile of the reconstruction error over NORMAL TRAINING rows.
  const trainScores = new Float64Array(n);
  for (let i = 0; i < n; i++) trainScores[i] = reconstruct(net, X.subarray(i * m, i * m + m), m, null);
  const sorted = Array.from(trainScores).sort((a, b) => a - b);
  const threshold = quantile(sorted, ALARM_Q);

  return {
    net,
    m,
    mu,
    sd,
    threshold,
    trainRows: n,
    trainMeanScore: sorted.reduce((s, v) => s + v, 0) / n,
    trainMedianScore: quantile(sorted, 0.5),
    source: corpus.source,
    totalRows: corpus.totalRows,
    normalRunsUsed: 1,
    firstLoss,
    lastLoss,
    skippedBatches,
    weightsFinite,
    architecture: [m, ...HIDDEN, m],
    seconds: (Date.now() - t0) / 1000,
  };
}

function getModel(m, corpus = null) {
  // The corpus is part of the cache key: a TEP model and an upload model of the
  // same width must never share an entry, or one user's normal would score another's.
  const key = configKey(m) + '|' + (corpus?.from_upload ? corpus.source + ':' + corpus.totalRows : 'tep');
  const hit = MODEL_CACHE.has(key);
  if (!hit) MODEL_CACHE.set(key, fit(corpus || loadCorpus()));
  return { model: MODEL_CACHE.get(key), cached: hit };
}

// --------------------------------------------------------------- entrypoint

function notApplicable(ctx, t0) {
  const ds = ctx.caseDef.dataset;
  return {
    applicable: false,
    top3: [],
    verdict: null,
    predicted_class: 'N/A',
    class_probabilities: [],
    variable_top3: [],
    detection: {},
    training: { rows: 0, classes: 0, features: 0, source: 'not trained (domain outside the labelled corpus)', seconds: 0, cached: false },
    reasoning:
      `Not applicable to the '${ds}' domain: this reconstruction model is trained exclusively on the labelled Tennessee Eastman ` +
      `(TEP) FaultExplainer normal run, and its alarm threshold is the 99th percentile of the TEP-only normal reconstruction ` +
      `error. A TEP-trained model — supervised or unsupervised — cannot be applied to the '${ds}' plant, whose sensors, units ` +
      `and operating envelope are different, so NO prediction is made: no detection claim, no verdict and no cause candidate ` +
      `are produced. Returning applicable:false rather than forcing a verdict, transferring the TEP threshold to foreign data, ` +
      `or fabricating a fault class.`,
    runtime_ms: Date.now() - t0,
  };
}

export async function run(ctx) {
  const t0 = Date.now();
  const caseDef = ctx.caseDef;
  const isUpload = ctx.is_upload === true || caseDef?.dataset === 'custom' || Boolean(caseDef?.upload);

  if (!isUpload && caseDef?.dataset !== 'tep') return notApplicable(ctx, t0);

  // Trained on the same columns as the record under test, so alignment is exact
  // and the "normal" definition comes from the user's own calibration segment.
  const corpus = isUpload && ctx.reference?.matrix
    ? loadCorpus({
        X: ctx.reference.matrix.X,
        cols: ctx.reference.matrix.colNames,
        source: 'upload-calibration-segment',
      })
    : loadCorpus();

  const m = corpus.cols.length;
  const perm = alignmentPerm(corpus.cols, ctx.matrix.colNames);
  const win = ctx.faultWindow;
  const rows = ctx.matrix.X.slice(win.start, win.end);
  if (!rows.length) throw new Error(`empty fault window for ${caseDef.case_id}`);

  const { model, cached } = getModel(m, corpus);

  const scoreRow = (row) => {
    const z = new Float64Array(m);
    for (let p = 0; p < m; p++) {
      const v = (row[perm[p]] - model.mu[p]) / model.sd[p];
      z[p] = Number.isFinite(v) ? v : 0;
    }
    return z;
  };

  // Detection over the fault window.
  const resid = new Float64Array(m);
  let alarms = 0;
  let maxScore = 0;
  let sumScore = 0;
  for (let i = win.start; i < win.end; i++) {
    const s = reconstruct(model.net, scoreRow(ctx.matrix.X[i]), m, resid);
    if (s > model.threshold) alarms++;
    if (s > maxScore) maxScore = s;
    sumScore += s;
  }
  const winRows = win.end - win.start;
  const detectionRate = alarms / winRows;

  // Pre-window context (the un-faulted lead-in of the same file), when present.
  let preAlarms = 0;
  const preRows = win.start;
  for (let i = 0; i < win.start; i++) {
    const s = reconstruct(model.net, scoreRow(ctx.matrix.X[i]), m, null);
    if (s > model.threshold) preAlarms++;
  }
  const preRate = preRows ? preAlarms / preRows : null;

  const meanResid = Array.from({ length: m }, (_, p) => ({ col: corpus.cols[p], contribution: resid[p] / winRows }))
    .sort((a, b) => b.contribution - a.contribution);
  const ranked = meanResid.slice(0, 6).map((r) => ({
    col: r.col,
    contribution: Number(r.contribution.toFixed(6)),
  }));

  const detectable = detectionRate > MIN_ALARM_RATE;
  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(ranked.map((v) => v.col))
    : [];

  return {
    applicable: true,
    top3: candidates.map((c) => c.label),
    verdict: detectable ? 'fault' : 'normal',
    predicted_class: 'N/A',
    class_probabilities: [],
    variable_top3: ranked.slice(0, 3).map((v) => v.col),
    variables_ranked: ranked,
    candidates: candidates.map((c) => ({ idv: c.idv, label: c.label, score: c.score })),
    detection: {
      detection_rate: Number(detectionRate.toFixed(4)),
      alarms,
      window_rows: winRows,
      threshold: Number(model.threshold.toFixed(6)),
      pre_window_alarm_rate: preRate === null ? null : Number(preRate.toFixed(4)),
      max_score: Number(maxScore.toFixed(6)),
      mean_score: Number((sumScore / winRows).toFixed(6)),
      train_mean_score: Number(model.trainMeanScore.toFixed(6)),
      train_median_score: Number(model.trainMedianScore.toFixed(6)),
      detectable,
      diverged: !model.weightsFinite,
    },
    training: {
      rows: model.trainRows,
      classes: 1,
      features: model.m,
      source: model.source,
      seconds: Number(model.seconds.toFixed(3)),
      cached,
      labelled_rows_available: model.totalRows,
      normal_runs_used: model.normalRunsUsed,
      epochs: EPOCHS,
      first_epoch_loss: model.firstLoss === null ? null : Number(model.firstLoss.toFixed(6)),
      last_epoch_loss: model.lastLoss === null ? null : Number(model.lastLoss.toFixed(6)),
    },
    reasoning:
      `Autoencoder ${model.architecture.join(' -> ')} (tanh hidden, linear output) trained by backpropagation ONLY on the ${model.trainRows} normal-class TEP rows ` +
      `(${EPOCHS} epochs of momentum SGD, batch ${BATCH_SIZE}, lr ${LR}, momentum ${MOMENTUM}); MSE ${model.firstLoss === null ? 'n/a' : model.firstLoss.toFixed(4)} -> ${model.lastLoss === null ? 'n/a' : model.lastLoss.toFixed(4)}. ` +
      `Alarm threshold = 99th percentile of the per-row squared reconstruction error over those normal rows = ${model.threshold.toFixed(4)} ` +
      `(normal-row median ${model.trainMedianScore.toFixed(4)}). ` +
      `Over the fault window (rows ${win.start}..${win.end - 1}, ${winRows} samples) ${alarms} rows exceed the threshold -> detection rate ${(detectionRate * 100).toFixed(2)}%` +
      (preRate === null ? '' : `, versus ${(preRate * 100).toFixed(2)}% in the ${preRows}-row lead-in`) +
      `. ` +
      (detectable
        ? `Dominant reconstruction residuals: ${ranked.slice(0, 3).map((v) => v.col).join(', ')}. Cause mapping (separate knowledge step, tep-affinity.mjs): ${candidates.map((c) => c.idv).join(' > ') || 'none'}. ` +
          `This is a detector, not a classifier: it reports which variables deviate from the learned normal manifold, and the cause ranking is produced by the same published variable-affinity table the classical detectors use.`
        : `No detection: the reconstruction error over the fault window is at the level implied by the 99th-percentile control limit on normal data, so the autoencoder reports no anomaly and yields no cause candidate.`) +
      ` No labelled fault class is predicted by this algorithm (predicted_class = 'N/A' by design).`,
    runtime_ms: Date.now() - t0,
  };
}
