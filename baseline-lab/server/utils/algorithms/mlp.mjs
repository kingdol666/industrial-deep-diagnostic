// Multilayer perceptron classifier — real forward + backward propagation.
//
// PROTOCOL
// --------
// Training source : TWO, selected by ctx.training (see _shared.mjs#resolveTraining)
//
//                   (a) TEP benchmark case -> the LABELLED TEP corpus shipped
//                       inside the FaultExplainer clone
//                       (baselines/FaultExplainer/backend/data/faultN.csv) via
//                       dataset.mjs#loadFeTrainingSet() — 16 named runs
//                       (Normal + IDV1..IDV15), 480 fault-active rows each.
//                       This is the published protocol and it is byte-for-byte
//                       unchanged (156 -> 64 -> 32 -> 16).
//
//                   (b) uploaded user data -> the USER'S OWN labelled file
//                       (ctx.training.path). Feature columns are joined BY NAME
//                       against the diagnosis matrix's columns (a mismatch is an
//                       error, never a guess); the class labels are the distinct
//                       strings in ctx.training.label_column, sorted
//                       deterministically; the head widens to that class count
//                       (F -> 64 -> 32 -> K). No TEP row and no TEP fault name
//                       enters a user-trained model.
//
//                   When neither is available the module returns
//                   status:'not_applicable' with the reason and makes no
//                   prediction — it never invents classes and never falls back
//                   to an unsupervised detector.
// Features        : the case's FAULT WINDOW aggregated per column into
//                   [mean, sd, mean |first difference|] -> 3*m features, built
//                   identically (80-sample / stride-20 sliding windows for TEP)
//                   for the training corpus; standardised with TRAINING
//                   statistics only. A small user file shortens the window
//                   (disclosed in the result) so every class contributes real
//                   window samples instead of none. On the user path the
//                   MONITORED window is then scored in the same w-row windows the
//                   network was trained on (the triple is not scale-free: sd and
//                   mean|diff| depend on window length), and the reported
//                   probability is the mean over those windows, with the
//                   agreement between them reported.
// Network         : F -> 64 -> 32 -> K, ReLU hidden activations, softmax
//                   output, cross-entropy loss, He initialisation
//                   N(0, sqrt(2/fan_in)) drawn from makeRng(SEED).
// Optimiser       : mini-batch SGD, batchSize 64, lr 0.01, momentum 0.9,
//                   60 epochs, per-epoch reshuffle from a dedicated
//                   makeRng(SEED + 1) stream.
// Backprop        : hand-written. dZ3 = (P - Y)/B; dW3 = A2^T dZ3;
//                   dA2 = dZ3 W3^T masked by (Z2 > 0); ... dW1 = X^T dZ1.
// Stability       : global-norm gradient clipping (5.0); a batch whose loss or
//                   gradients are non-finite is skipped and counted instead of
//                   poisoning the weights; the loss is clamped so log(0) can
//                   never produce Infinity.
// Determinism     : every stochastic step draws from makeRng(SEED)/(SEED+1). The
//                   model cache is keyed on the training SOURCE (and file), so
//                   one user's model is never served for another's data.

import { makeRng, shuffle, colStats } from '../linalg.mjs';
import { loadFeTrainingSet, FE_FAULT_DESCRIPTIONS } from '../dataset.mjs';
import { loadUserTrainingCorpus, uploadNormalClassIndex, scoringWindows } from './_shared.mjs';

export const meta = {
  id: 'mlp-classifier',
  label: '多层感知机分类器',
  short: 'MLP',
  family: 'supervised',
  kind: 'classifier',
  deterministic: true,
  requiresProvider: false,
  needsReference: false,
  needsTraining: true,
  domains: ['tep', 'custom'],
  description:
    'Hand-written multilayer perceptron (F->64->32->K, ReLU hidden layers, softmax output, cross-entropy, He init, 60 epochs of momentum SGD at lr 0.01 / batch 64 / momentum 0.9, gradient clipping) trained on 3*m window features: on the labelled FaultExplainer TEP corpus for TEP cases (156->64->32->16, unchanged benchmark protocol), or on the user\'s OWN labelled training file for uploaded data (feature columns joined by name, class labels taken from the user\'s label column). Both feature constructions are identical, so the comparison stays apples-to-apples.',
  provenance: {
    basis: ['rumelhart1986backprop', 'he2015delving'],
    repo: null,
    note:
      'Forward and backward passes implemented from the chain rule in plain JavaScript; no autodiff library, no framework, and no tuning against the benchmark cases.',
  },
};

// ------------------------------------------------------------------ config

export const SEED = 20240917;
export const TRAIN_WINDOW = 80;
export const TRAIN_STRIDE = 20;

const HIDDEN = [64, 32];
const EPOCHS = 60;
const BATCH_SIZE = 64;
const LR = 0.01;
const MOMENTUM = 0.9;
const CLIP_NORM = 5.0;
const TOP_K_PROB = 5;
const USE_NAMED_CLASSES_ONLY = true;
/**
 * Smallest window-sample count a user-trained network will accept. A network with
 * F*64+64*32+32*K weights fitted on a handful of samples is over-parameterised
 * noise, so the module refuses instead of reporting a degenerate model.
 */
const MIN_TRAIN_SAMPLES = 20;

// ------------------------------------------------------------- feature core

let CORPUS = null;

function loadCorpus() {
  if (CORPUS) return CORPUS;
  const t = loadFeTrainingSet();
  const classCount = USE_NAMED_CLASSES_ONLY
    ? Math.min(FE_FAULT_DESCRIPTIONS.length, t.labelNames.filter(Boolean).length)
    : t.labelNames.length;
  const byClass = Array.from({ length: classCount }, () => []);
  let dropped = 0;
  for (let i = 0; i < t.y.length; i++) {
    const y = t.y[i];
    if (y >= 0 && y < classCount) byClass[y].push(i);
    else dropped++;
  }
  for (let k = 0; k < classCount; k++) {
    if (!byClass[k].length) throw new Error(`training corpus has no rows for class ${k}`);
  }
  CORPUS = {
    cols: t.cols,
    X: t.X,
    byClass,
    labelNames: Array.from({ length: classCount }, (_, k) => t.labelNames[k] || `class${k}`),
    classCount,
    source: t.source,
    cacheKey: 'tep-faultexplainer',
    usedRows: t.y.length - dropped,
    droppedRows: dropped,
    unnamedRuns: t.labelNames.length - classCount,
  };
  return CORPUS;
}

/**
 * Training corpus for a case.
 *   TEP benchmark case      -> the labelled FaultExplainer corpus (unchanged).
 *   uploaded user dataset   -> the user's own labelled file, joined by name.
 */
function corpusFor(ctx) {
  if (!ctx.is_upload) return loadCorpus();
  return loadUserTrainingCorpus(ctx.training, ctx.matrix.colNames, {
    window: TRAIN_WINDOW,
    stride: TRAIN_STRIDE,
  });
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

function windowFeatureVector(rows, perm, m) {
  const n = rows.length;
  const out = new Float64Array(3 * m);
  for (let p = 0; p < m; p++) {
    const c = perm[p];
    let mu = 0;
    for (let i = 0; i < n; i++) mu += rows[i][c];
    mu /= n;
    let v = 0;
    for (let i = 0; i < n; i++) {
      const d = rows[i][c] - mu;
      v += d * d;
    }
    let d1 = 0;
    for (let i = 1; i < n; i++) d1 += Math.abs(rows[i][c] - rows[i - 1][c]);
    out[p] = mu;
    out[m + p] = Math.sqrt(v / n);
    out[2 * m + p] = n > 1 ? d1 / (n - 1) : 0;
  }
  return out;
}

function buildTrainingMatrix(corpus) {
  const m = corpus.cols.length;
  const identity = Int32Array.from({ length: m }, (_, p) => p);
  // The window/stride come from the corpus: TEP uses the protocol constants, a
  // user file may have adapted them to its smallest class (disclosed in the result).
  const window = corpus.window ?? TRAIN_WINDOW;
  const stride = corpus.stride ?? TRAIN_STRIDE;
  const rows = [];
  const labels = [];
  for (let k = 0; k < corpus.classCount; k++) {
    const idx = corpus.byClass[k];
    if (idx.length < window) {
      throw new Error(
        `class ${k} (${corpus.labelNames[k]}) has ${idx.length} labelled rows, fewer than the ${window}-sample aggregation window`,
      );
    }
    for (let s = 0; s + window <= idx.length; s += stride) {
      const win = [];
      for (let t = s; t < s + window; t++) win.push(corpus.X[idx[t]]);
      rows.push(windowFeatureVector(win, identity, m));
      labels.push(k);
    }
  }
  if (rows.length < MIN_TRAIN_SAMPLES) {
    throw new Error(
      `only ${rows.length} training window sample(s) could be built from '${corpus.source}' `
      + `(${corpus.classCount} classes, ${window}-sample windows) — the network needs at least ${MIN_TRAIN_SAMPLES}; `
      + 'supply more labelled rows per class.',
    );
  }
  return { rows, labels, m, F: 3 * m };
}

function standardizeRows(rows, mu, sd) {
  const n = rows.length;
  const F = mu.length;
  const Z = new Float64Array(n * F);
  for (let i = 0; i < n; i++) {
    const r = rows[i];
    for (let j = 0; j < F; j++) {
      const z = (r[j] - mu[j]) / sd[j];
      Z[i * F + j] = Number.isFinite(z) ? z : 0;
    }
  }
  return Z;
}

function standardizeVector(vec, mu, sd) {
  const F = mu.length;
  const z = new Float64Array(F);
  for (let j = 0; j < F; j++) {
    const v = (vec[j] - mu[j]) / sd[j];
    z[j] = Number.isFinite(v) ? v : 0;
  }
  return z;
}

// ------------------------------------------------------------------ network

/** Standard normal via Box-Muller on a seeded uniform stream. */
function gauss(rng) {
  let u = rng();
  if (u < 1e-12) u = 1e-12;
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function initLayer(rng, fanIn, fanOut) {
  const W = new Float64Array(fanIn * fanOut);
  const scale = Math.sqrt(2 / fanIn); // He normal
  for (let i = 0; i < W.length; i++) W[i] = gauss(rng) * scale;
  return { W, b: new Float64Array(fanOut), fanIn, fanOut };
}

function forward(net, x, B) {
  const [l1, l2, l3] = net.layers;
  const Z1 = new Float64Array(B * l1.fanOut);
  const A1 = new Float64Array(B * l1.fanOut);
  for (let i = 0; i < B; i++) {
    for (let o = 0; o < l1.fanOut; o++) {
      let s = l1.b[o];
      for (let j = 0; j < l1.fanIn; j++) s += x[i * l1.fanIn + j] * l1.W[j * l1.fanOut + o];
      Z1[i * l1.fanOut + o] = s;
      A1[i * l1.fanOut + o] = s > 0 ? s : 0; // ReLU
    }
  }
  const Z2 = new Float64Array(B * l2.fanOut);
  const A2 = new Float64Array(B * l2.fanOut);
  for (let i = 0; i < B; i++) {
    for (let o = 0; o < l2.fanOut; o++) {
      let s = l2.b[o];
      for (let j = 0; j < l2.fanIn; j++) s += A1[i * l2.fanIn + j] * l2.W[j * l2.fanOut + o];
      Z2[i * l2.fanOut + o] = s;
      A2[i * l2.fanOut + o] = s > 0 ? s : 0;
    }
  }
  const Z3 = new Float64Array(B * l3.fanOut);
  const P = new Float64Array(B * l3.fanOut);
  for (let i = 0; i < B; i++) {
    let max = -Infinity;
    for (let o = 0; o < l3.fanOut; o++) {
      let s = l3.b[o];
      for (let j = 0; j < l3.fanIn; j++) s += A2[i * l3.fanIn + j] * l3.W[j * l3.fanOut + o];
      Z3[i * l3.fanOut + o] = s;
      if (s > max) max = s;
    }
    let sum = 0;
    for (let o = 0; o < l3.fanOut; o++) {
      const e = Math.exp(Z3[i * l3.fanOut + o] - max);
      const v = Number.isFinite(e) ? e : 0;
      P[i * l3.fanOut + o] = v;
      sum += v;
    }
    if (!(sum > 0)) {
      for (let o = 0; o < l3.fanOut; o++) P[i * l3.fanOut + o] = 1 / l3.fanOut;
    } else {
      for (let o = 0; o < l3.fanOut; o++) P[i * l3.fanOut + o] /= sum;
    }
  }
  return { Z1, A1, Z2, A2, P };
}

/** Momentum buffers for every parameter tensor. */
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

function applyUpdate(net, velocity, grads, scale, lr, momentum) {
  const [g1, g2, g3] = grads;
  const [v1, v2, v3] = velocity;
  const pairs = [
    [net.layers[0], g1, v1],
    [net.layers[1], g2, v2],
    [net.layers[2], g3, v3],
  ];
  for (const [layer, g, v] of pairs) {
    for (let i = 0; i < layer.W.length; i++) {
      const gi = g.W[i] * scale;
      v.W[i] = momentum * v.W[i] - lr * gi;
      layer.W[i] += v.W[i];
    }
    for (let i = 0; i < layer.b.length; i++) {
      const gi = g.b[i] * scale;
      v.b[i] = momentum * v.b[i] - lr * gi;
      layer.b[i] += v.b[i];
    }
  }
}

/**
 * One mini-batch step. Returns { loss, finite } — a non-finite batch is
 * reported and skipped by the caller rather than corrupting the weights.
 */
function trainBatch(net, X, F, y, idx, B, lr, momentum, velocity) {
  const [l1, l2, l3] = net.layers;
  const K = l3.fanOut;
  const xb = new Float64Array(B * F);
  for (let i = 0; i < B; i++) xb.set(X.subarray(idx[i] * F, idx[i] * F + F), i * F);

  const { Z1, A1, Z2, A2, P } = forward(net, xb, B);

  let loss = 0;
  for (let i = 0; i < B; i++) loss -= Math.log(Math.max(P[i * K + y[idx[i]]], 1e-12));
  loss /= B;

  // ---- backward ----
  const dZ3 = new Float64Array(B * K);
  for (let i = 0; i < B; i++) {
    for (let o = 0; o < K; o++) {
      dZ3[i * K + o] = (P[i * K + o] - (y[idx[i]] === o ? 1 : 0)) / B;
    }
  }
  const g3 = { W: new Float64Array(l3.W.length), b: new Float64Array(l3.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l3.fanIn; j++) {
      const a = A2[i * l3.fanIn + j];
      if (a === 0) continue;
      for (let o = 0; o < K; o++) g3.W[j * K + o] += a * dZ3[i * K + o];
    }
    for (let o = 0; o < K; o++) g3.b[o] += dZ3[i * K + o];
  }
  const dA2 = new Float64Array(B * l2.fanOut);
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l2.fanOut; j++) {
      let s = 0;
      for (let o = 0; o < K; o++) s += dZ3[i * K + o] * l3.W[j * K + o];
      dA2[i * l2.fanOut + j] = s;
    }
  }
  const dZ2 = new Float64Array(B * l2.fanOut);
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l2.fanOut; j++) {
      dZ2[i * l2.fanOut + j] = Z2[i * l2.fanOut + j] > 0 ? dA2[i * l2.fanOut + j] : 0;
    }
  }
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
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l1.fanOut; j++) {
      dZ1[i * l1.fanOut + j] = Z1[i * l1.fanOut + j] > 0 ? dA1[i * l1.fanOut + j] : 0;
    }
  }
  const g1 = { W: new Float64Array(l1.W.length), b: new Float64Array(l1.b.length) };
  for (let i = 0; i < B; i++) {
    for (let j = 0; j < l1.fanIn; j++) {
      const a = xb[i * F + j];
      if (a === 0) continue;
      for (let o = 0; o < l1.fanOut; o++) g1.W[j * l1.fanOut + o] += a * dZ1[i * l1.fanOut + o];
    }
    for (let o = 0; o < l1.fanOut; o++) g1.b[o] += dZ1[i * l1.fanOut + o];
  }

  const grads = [g1, g2, g3];
  let finite = Number.isFinite(loss);
  for (const g of grads) {
    for (let i = 0; i < g.W.length && finite; i++) if (!Number.isFinite(g.W[i])) finite = false;
    for (let i = 0; i < g.b.length && finite; i++) if (!Number.isFinite(g.b[i])) finite = false;
  }
  if (!finite) return { loss, finite: false };

  const { scale } = clipByGlobalNorm([g1.W, g1.b, g2.W, g2.b, g3.W, g3.b], CLIP_NORM);
  applyUpdate(net, velocity, grads, scale, lr, momentum);
  return { loss, finite: true };
}

function netPredict(net, x) {
  const { P } = forward(net, x, 1);
  const K = net.layers[2].fanOut;
  const p = new Float64Array(K);
  let s = 0;
  for (let k = 0; k < K; k++) {
    const v = Number.isFinite(P[k]) ? Math.max(P[k], 0) : 0;
    p[k] = v;
    s += v;
  }
  if (!(s > 0)) {
    p.fill(1 / K);
    return p;
  }
  for (let k = 0; k < K; k++) p[k] /= s;
  return p;
}

// -------------------------------------------------------------------- model

const MODEL_CACHE = new Map();

export function __resetCacheForTest() {
  MODEL_CACHE.clear();
}

function configKey(F, classCount, corpus) {
  return JSON.stringify({
    id: meta.id, seed: SEED, F, classCount, TRAIN_WINDOW, TRAIN_STRIDE,
    HIDDEN, EPOCHS, BATCH_SIZE, LR, MOMENTUM, CLIP_NORM, USE_NAMED_CLASSES_ONLY,
    // Training-source isolation. Without this, a model trained on one user's
    // labelled file would be reused for a different user's data whenever the
    // feature count and class count happened to match.
    training: corpus.cacheKey,
    window: corpus.window ?? null,
    stride: corpus.stride ?? null,
    labels: corpus.labelNames,
  });
}

function fit(corpus) {
  const t0 = Date.now();
  const { rows, labels, m, F } = buildTrainingMatrix(corpus);
  const K = corpus.classCount;
  const n = rows.length;

  const { mu, sd } = colStats(rows, 1);
  const X = standardizeRows(rows, mu, sd);
  const y = Int32Array.from(labels);

  const initRng = makeRng(SEED);
  const net = {
    layers: [
      initLayer(initRng, F, HIDDEN[0]),
      initLayer(initRng, HIDDEN[0], HIDDEN[1]),
      initLayer(initRng, HIDDEN[1], K),
    ],
  };
  const velocity = zeroVelocity(net);
  const shuffleRng = makeRng(SEED + 1);

  const all = Array.from({ length: n }, (_, i) => i);
  let firstLoss = null;
  let lastLoss = null;
  let skippedBatches = 0;
  let diverged = false;

  for (let epoch = 0; epoch < EPOCHS; epoch++) {
    const order = shuffle(all, shuffleRng);
    let epochLoss = 0;
    let epochBatches = 0;
    for (let s = 0; s < order.length; s += BATCH_SIZE) {
      const idx = order.slice(s, Math.min(s + BATCH_SIZE, order.length));
      const { loss, finite } = trainBatch(net, X, F, y, idx, idx.length, LR, MOMENTUM, velocity);
      if (!finite) {
        skippedBatches++;
        diverged = true;
        continue;
      }
      epochLoss += loss;
      epochBatches++;
    }
    const meanLoss = epochBatches ? epochLoss / epochBatches : NaN;
    if (Number.isFinite(meanLoss)) {
      if (firstLoss === null) firstLoss = meanLoss;
      lastLoss = meanLoss;
    }
  }

  // Guard: if the network still holds non-finite weights, fall back to uniform.
  let weightsFinite = true;
  for (const l of net.layers) {
    for (let i = 0; i < l.W.length && weightsFinite; i++) if (!Number.isFinite(l.W[i])) weightsFinite = false;
    for (let i = 0; i < l.b.length && weightsFinite; i++) if (!Number.isFinite(l.b[i])) weightsFinite = false;
  }

  let correct = 0;
  for (let i = 0; i < n; i++) {
    const p = netPredict(net, X.subarray(i * F, i * F + F));
    let best = 0;
    for (let k = 1; k < K; k++) if (p[k] > p[best]) best = k;
    if (best === y[i]) correct++;
  }

  return {
    net,
    F,
    K,
    mu,
    sd,
    labelNames: corpus.labelNames,
    trainRows: n,
    trainRawRows: corpus.usedRows,
    droppedRows: corpus.droppedRows,
    unnamedRuns: corpus.unnamedRuns,
    runsPerClass: corpus.byClass.map((a) => a.length),
    source: corpus.source,
    trainingFile: corpus.original_name || corpus.path || null,
    labelColumn: corpus.label_column || null,
    window: corpus.window ?? null,
    stride: corpus.stride ?? null,
    minRowsPerClass: corpus.minRowsPerClass ?? null,
    trainAccuracy: correct / n,
    firstLoss,
    lastLoss,
    skippedBatches,
    diverged: diverged || !weightsFinite,
    weightsFinite,
    architecture: [F, ...HIDDEN, K],
    seconds: (Date.now() - t0) / 1000,
  };
}

function getModel(F, K, corpus) {
  const key = configKey(F, K, corpus);
  const hit = MODEL_CACHE.has(key);
  if (!hit) MODEL_CACHE.set(key, fit(corpus));
  return { model: MODEL_CACHE.get(key), cached: hit };
}

// --------------------------------------------------------------- entrypoint

function notApplicable(ctx, t0) {
  const ds = ctx.caseDef.dataset;
  return {
    status: 'not_applicable',
    applicable: false,
    top3: [],
    verdict: null,
    predicted_class: 'N/A',
    class_probabilities: [],
    variable_top3: [],
    detection: {},
    training: { rows: 0, classes: 0, features: 0, source: 'not trained (domain outside the labelled corpus)', seconds: 0, cached: false },
    reasoning:
      `Not applicable to the '${ds}' domain: the only labelled training corpus available in this repository is the ` +
      `Tennessee Eastman (TEP) FaultExplainer set (Normal + IDV1..IDV15). No labelled '${ds}' data exists, so a ` +
      `TEP-trained multilayer perceptron cannot be applied to this process and NO prediction is made. ` +
      `Returning applicable:false rather than forcing a label, falling back to an unsupervised detector, or fabricating a fault class.`,
    runtime_ms: Date.now() - t0,
  };
}

/** No labelled training data was supplied with an upload: refuse, with the reason. */
function notTrained(ctx, t0, reason) {
  return {
    status: 'not_applicable',
    applicable: false,
    top3: [],
    verdict: null,
    predicted_class: 'N/A',
    class_probabilities: [],
    variable_top3: [],
    detection: {},
    training: { rows: 0, classes: 0, features: 0, source: 'not trained (no labelled training file)', seconds: 0, cached: false },
    reasoning: reason,
    runtime_ms: Date.now() - t0,
  };
}

const DEFAULT_NO_TRAINING_REASON =
  'No labelled training data is available for this upload, so the multilayer perceptron was NOT applied and no '
  + 'prediction is made: a classifier needs labelled examples of each class and inventing them would be fabrication. '
  + 'Re-upload the dataset together with a labelled training CSV (one row per sample, the same sensor column names as '
  + 'the data, plus a class/label column) to make this algorithm usable.';

export async function run(ctx) {
  const t0 = Date.now();
  const caseDef = ctx.caseDef;

  // ---- uploaded user data: train on the user's OWN labelled file -----------
  if (ctx.is_upload) {
    const training = ctx.training;
    if (!training || !training.available || training.source !== 'user-upload') {
      return notTrained(ctx, t0, training?.reason || DEFAULT_NO_TRAINING_REASON);
    }
    return runUserTrained(ctx, t0);
  }

  // ---- benchmark case: the published TEP protocol, unchanged ---------------
  if (!caseDef || caseDef.dataset !== 'tep') return notApplicable(ctx, t0);
  return runTep(ctx, t0);
}

async function runTep(ctx, t0) {
  const caseDef = ctx.caseDef;
  const corpus = loadCorpus();
  const m = corpus.cols.length;
  const perm = alignmentPerm(corpus.cols, ctx.matrix.colNames);
  const win = ctx.faultWindow;
  const rows = ctx.matrix.X.slice(win.start, win.end);
  if (!rows.length) throw new Error(`empty fault window for ${caseDef.case_id}`);

  const raw = windowFeatureVector(rows, perm, m);
  const F = 3 * m;
  const { model, cached } = getModel(F, corpus.classCount, corpus);
  const x = standardizeVector(raw, model.mu, model.sd);

  const probs = netPredict(model.net, x);
  const ranked = Array.from({ length: model.K }, (_, k) => ({ k, p: probs[k] }))
    .sort((a, b) => b.p - a.p || a.k - b.k);
  const top3 = ranked.slice(0, 3).map((r) => model.labelNames[r.k]);
  const top5 = ranked.slice(0, TOP_K_PROB).map((r) => ({
    label: model.labelNames[r.k],
    p: Number(r.p.toFixed(6)),
  }));
  const top = ranked[0];
  const predicted = model.labelNames[top.k];
  const runnerUp = ranked[1];

  return {
    applicable: true,
    top3,
    verdict: top.k === 0 ? 'normal' : 'fault',
    predicted_class: predicted,
    class_probabilities: top5,
    variable_top3: [],
    detection: {
      confidence: Number(top.p.toFixed(6)),
      margin_to_runner_up: Number((top.p - (runnerUp ? runnerUp.p : 0)).toFixed(6)),
      train_accuracy: Number(model.trainAccuracy.toFixed(4)),
      diverged: model.diverged,
      skipped_batches: model.skippedBatches,
      model: `MLP ${model.architecture.join('-')}, ReLU + softmax, momentum SGD`,
    },
    training: {
      rows: model.trainRows,
      classes: model.K,
      features: model.F,
      source: model.source,
      seconds: Number(model.seconds.toFixed(3)),
      cached,
      raw_labelled_rows: model.trainRawRows,
      excluded_rows: model.droppedRows,
      unnamed_runs_excluded: model.unnamedRuns,
      epochs: EPOCHS,
      first_epoch_loss: model.firstLoss === null ? null : Number(model.firstLoss.toFixed(6)),
      last_epoch_loss: model.lastLoss === null ? null : Number(model.lastLoss.toFixed(6)),
    },
    reasoning:
      `Trained on ${model.trainRows} window samples (${model.trainRawRows} labelled TEP rows, 16 named classes, ${TRAIN_WINDOW}-sample windows / stride ${TRAIN_STRIDE}) ` +
      `over ${model.F} features = 3 x ${m} (mean, sd, mean |first difference|); MLP ${model.architecture.join(' -> ')} with ReLU hidden layers and a softmax head, ` +
      `${EPOCHS} epochs of momentum SGD (batch ${BATCH_SIZE}, lr ${LR}, momentum ${MOMENTUM}, gradient clipping at norm ${CLIP_NORM}); ` +
      `cross-entropy loss ${model.firstLoss === null ? 'n/a' : model.firstLoss.toFixed(4)} -> ${model.lastLoss === null ? 'n/a' : model.lastLoss.toFixed(4)} ` +
      `(${model.skippedBatches} non-finite batches skipped, weights ${model.weightsFinite ? 'finite' : 'DIVERGED'}); training-set accuracy ${(model.trainAccuracy * 100).toFixed(2)}%. ` +
      `Fault window = rows ${win.start}..${win.end - 1} (${rows.length} samples). ` +
      `Prediction: '${predicted}' with p=${top.p.toFixed(4)}` +
      (runnerUp ? `, runner-up '${model.labelNames[runnerUp.k]}' p=${runnerUp.p.toFixed(4)}` : '') +
      `. ` +
      (top.k === 0
        ? `The top-ranked class is 0 (Normal). This is reported honestly and NOT dropped from the ranking` +
          (caseDef.control ? `, which is the expected answer for this control case.` : `, even though the case is a fault case.`)
        : `Ranked top-3: ${top3.map((s, i) => `${i + 1}. ${s}`).join(' | ')}. ` +
          `Softmax outputs are not calibrated probabilities: with ${model.trainRows} training windows and ${model.F * 64 + 64 * 32 + 32 * model.K} weights the network is over-parameterised, so a high p means "confidently inside a decision region", not "calibrated confidence".`) +
      (model.unnamedRuns > 0
        ? ` Note: the FaultExplainer clone also ships ${model.unnamedRuns} further labelled runs (fault16..fault20) with no published fault description; ` +
          `they are excluded (${model.droppedRows} rows) so that every emitted label is a documented TEP fault name.`
        : ''),
    runtime_ms: Date.now() - t0,
  };
}

/**
 * Uploaded data WITH a user-supplied labelled file: train on that file.
 * The answer space is exactly the user's own class strings — no TEP class can be
 * emitted, because no TEP row took part in the training.
 */
async function runUserTrained(ctx, t0) {
  const caseDef = ctx.caseDef;
  const corpus = corpusFor(ctx);
  const m = corpus.cols.length;
  const perm = alignmentPerm(corpus.cols, ctx.matrix.colNames); // identity by construction
  const win = ctx.faultWindow;
  const rows = ctx.matrix.X.slice(win.start, win.end);
  if (!rows.length) throw new Error(`empty fault window for ${caseDef.case_id}`);

  const F = 3 * m;
  const { model, cached } = getModel(F, corpus.classCount, corpus);

  // Score the monitored window in the SAME w-row windows the model was trained
  // on (see _shared.mjs#scoringWindows): the feature triple is not scale-free, so
  // one whole-record aggregate is out of distribution for a network trained on
  // short windows. The reported probability is the mean over those windows.
  const segments = scoringWindows(rows, model.window, model.stride);
  const probs = new Float64Array(model.K);
  const hits = new Int32Array(model.K);
  for (let i = 0; i < segments.length; i++) {
    const x = standardizeVector(windowFeatureVector(segments[i], perm, m), model.mu, model.sd);
    const p = netPredict(model.net, x);
    let best = 0;
    for (let k = 0; k < model.K; k++) {
      probs[k] += p[k];
      if (p[k] > p[best]) best = k;
    }
    hits[best]++;
  }
  for (let k = 0; k < model.K; k++) probs[k] /= segments.length;

  const ranked = Array.from({ length: model.K }, (_, k) => ({ k, p: probs[k] }))
    .sort((a, b) => b.p - a.p || a.k - b.k);
  const top3 = ranked.slice(0, 3).map((r) => model.labelNames[r.k]);
  const top5 = ranked.slice(0, TOP_K_PROB).map((r) => ({
    label: model.labelNames[r.k],
    p: Number(r.p.toFixed(6)),
  }));
  const top = ranked[0];
  const predicted = model.labelNames[top.k];
  const runnerUp = ranked[1];
  const normalIdx = uploadNormalClassIndex(model.labelNames);
  const verdict = normalIdx < 0 ? null : (top.k === normalIdx ? 'normal' : 'fault');
  const agreement = hits[top.k] / segments.length;

  return {
    applicable: true,
    top3,
    verdict,
    predicted_class: predicted,
    class_probabilities: top5,
    variable_top3: [],
    detection: {
      confidence: Number(top.p.toFixed(6)),
      margin_to_runner_up: Number((top.p - (runnerUp ? runnerUp.p : 0)).toFixed(6)),
      train_accuracy: Number(model.trainAccuracy.toFixed(4)),
      diverged: model.diverged,
      skipped_batches: model.skippedBatches,
      scored_windows: segments.length,
      window_rows: model.window,
      window_agreement: Number(agreement.toFixed(4)),
      short_monitored_window: segments.length === 1 && rows.length < model.window,
      model: `MLP ${model.architecture.join('-')}, ReLU + softmax, momentum SGD, trained on the user-supplied labelled file`,
    },
    training: {
      rows: model.trainRows,
      classes: model.K,
      features: model.F,
      source: model.source,
      seconds: Number(model.seconds.toFixed(3)),
      cached,
      raw_labelled_rows: model.trainRawRows,
      excluded_rows: model.droppedRows,
      unnamed_runs_excluded: model.unnamedRuns,
      training_file: model.trainingFile,
      label_column: model.labelColumn,
      class_names: model.labelNames,
      window: model.window,
      stride: model.stride,
      rows_per_class: model.runsPerClass,
      unlabelled_rows_dropped: corpus.unlabelledRows ?? 0,
      epochs: EPOCHS,
      first_epoch_loss: model.firstLoss === null ? null : Number(model.firstLoss.toFixed(6)),
      last_epoch_loss: model.lastLoss === null ? null : Number(model.lastLoss.toFixed(6)),
    },
    reasoning:
      `Trained on THIS upload's own labelled file ${model.trainingFile ? `'${model.trainingFile}'` : ''}: ` +
      `${model.trainRawRows} labelled row(s), ${model.K} classes (${model.labelNames.join(' | ')}) read from column '${model.labelColumn}'; ` +
      `feature columns joined BY NAME to the diagnosis data, aggregated into ${model.trainRows} window samples of ` +
      `${model.window} rows (stride ${model.stride}` +
      (model.window !== TRAIN_WINDOW
        ? `, shortened from the ${TRAIN_WINDOW}-sample benchmark protocol because the smallest class holds only ${model.minRowsPerClass} rows`
        : '') +
      `) over the same ${model.F} features = 3 x ${m} (mean, sd, mean |first difference|) the TEP protocol uses. ` +
      `MLP ${model.architecture.join(' -> ')} with ReLU hidden layers and a softmax head, ${EPOCHS} epochs of momentum SGD ` +
      `(batch ${BATCH_SIZE}, lr ${LR}, momentum ${MOMENTUM}, gradient clipping at norm ${CLIP_NORM}); cross-entropy loss ` +
      `${model.firstLoss === null ? 'n/a' : model.firstLoss.toFixed(4)} -> ${model.lastLoss === null ? 'n/a' : model.lastLoss.toFixed(4)} ` +
      `(${model.skippedBatches} non-finite batches skipped, weights ${model.weightsFinite ? 'finite' : 'DIVERGED'}); training-set accuracy ${(model.trainAccuracy * 100).toFixed(2)}%. ` +
      `No TEP data and no TEP fault name was used: the answer space is exactly the ${model.K} label(s) supplied by the user. ` +
      `Fault window = rows ${win.start}..${win.end - 1} (${rows.length} samples), scored as ${segments.length} window(s) of ${model.window} rows ` +
      `— the same aggregation the network was trained on` +
      (segments.length === 1 && rows.length < model.window ? ' (the record is shorter than one training window, so the single aggregate is reported as-is)' : '') +
      `; the probabilities below are the mean over those windows and ${hits[top.k]}/${segments.length} of them agree on the top class. ` +
      `Prediction: '${predicted}' with p=${top.p.toFixed(4)}` +
      (runnerUp ? `, runner-up '${model.labelNames[runnerUp.k]}' p=${runnerUp.p.toFixed(4)}` : '') +
      `. Ranked top-3: ${top3.map((s, i) => `${i + 1}. ${s}`).join(' | ')}. ` +
      `Softmax outputs are not calibrated probabilities: with ${model.trainRows} training windows and ${model.F * 64 + 64 * 32 + 32 * model.K} weights, ` +
      `a high p means "confidently inside a decision region", not "calibrated confidence". ` +
      (verdict === null
        ? `None of the supplied label names identifies a normal/healthy class, so no normal-vs-fault verdict is asserted — `
          + `the ranking above is the complete answer.`
        : `'${model.labelNames[normalIdx]}' is read as the normal class from its name, so the verdict is '${verdict}'.`),
    runtime_ms: Date.now() - t0,
  };
}
