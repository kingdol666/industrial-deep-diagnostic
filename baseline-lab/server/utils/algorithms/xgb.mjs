// XGBoost-style gradient-boosted decision trees — Friedman 2001 / Chen & Guestrin 2016.
//
// PROTOCOL
// --------
// Training source : TWO, selected by ctx.training (see _shared.mjs#resolveTraining)
//
//                   (a) TEP benchmark case -> the LABELLED TEP corpus shipped
//                       inside the FaultExplainer clone
//                       (baselines/FaultExplainer/backend/data/faultN.csv),
//                       reached through dataset.mjs#loadFeTrainingSet(). Each of
//                       the 16 named runs contributes 480 fault-active rows (FE
//                       drops the first 20 start-up samples; in the TEP
//                       *training* encoding the fault is injected at sample 21,
//                       not at the published test-set sample 161). This is the
//                       published protocol and it is byte-for-byte unchanged.
//
//                   (b) uploaded user data -> the USER'S OWN labelled file
//                       (ctx.training.path). Feature columns are joined BY NAME
//                       against the diagnosis matrix's columns (a mismatch is an
//                       error, never a guess); the class labels are the distinct
//                       strings in ctx.training.label_column, sorted
//                       deterministically. No TEP row and no TEP fault name
//                       enters a user-trained model.
//
//                   When neither is available the module returns
//                   status:'not_applicable' with the reason and makes no
//                   prediction — it never invents classes and never falls back
//                   to an unsupervised detector.
// Features        : the case's FAULT WINDOW is aggregated per column into
//                   [mean, sd, mean |first difference|] -> 3 * m = 156 features.
//                   The training corpus is aggregated the same way over sliding
//                   windows (80 samples / stride 20 for TEP, i.e. 21 windows per
//                   run), never over the case under test. A small user file
//                   shortens the window (disclosed in the result) so that every
//                   class contributes real window samples instead of none.
//                   On the user path the MONITORED window is then scored in the
//                   same w-row windows the model was trained on (the triple is
//                   not scale-free: sd and mean|diff| depend on window length),
//                   and the reported probability is the mean over those windows,
//                   with the agreement between them reported.
// Standardisation : column statistics (ddof=1) computed from the TRAINING
//                   feature matrix only.
// Model           : 120 boosting rounds of genuine multiclass softmax GBST.
//                   Per round: p = softmax(F); g_ik = p_ik - y_ik;
//                   h_ik = 2 p_ik (1 - p_ik)   (XGBoost's softmax hessian);
//                   one exact-split regression tree per class fitted on
//                   (g, h) with leaf weight -G / (H + lambda) and split gain
//                   0.5 [G_L^2/(H_L+l) + G_R^2/(H_R+l) - G^2/(H+l)];
//                   F += lr * tree_k.  Logistic one-vs-rest was NOT used: this
//                   is the real multiclass objective, documented so the result
//                   cannot be mistaken for an OvR approximation.
// Determinism     : every stochastic step draws from makeRng(SEED); no
//                   Math.random, no Date, no Map-order dependence. The model
//                   cache is keyed on the training SOURCE (and file), so one
//                   user's model is never served for another's data.

import { makeRng, shuffle, colStats } from '../linalg.mjs';
import { loadFeTrainingSet, FE_FAULT_DESCRIPTIONS } from '../dataset.mjs';
import { loadUserTrainingCorpus, uploadNormalClassIndex, scoringWindows } from './_shared.mjs';

export const meta = {
  id: 'xgb-gbdt',
  label: 'XGBoost 梯度提升树分类器',
  short: 'XGB',
  family: 'supervised',
  kind: 'classifier',
  deterministic: true,
  requiresProvider: false,
  needsReference: false,
  needsTraining: true,
  domains: ['tep', 'custom'],
  description:
    'Gradient-boosted decision trees with a genuine multiclass softmax objective (per-class exact-split regression trees on the multinomial logistic gradient/hessian), 120 rounds, lr 0.1, depth 4, 0.8 row subsample, 0.7 column subsample, L2 leaf lambda 1.0, min 5 samples per leaf. Trained on 3*m window features: on the labelled FaultExplainer TEP corpus for TEP cases (unchanged benchmark protocol), or on the user\'s OWN labelled training file for uploaded data (feature columns joined by name, class labels taken from the user\'s label column). Both feature constructions are identical, so the comparison stays apples-to-apples.',
  provenance: {
    basis: ['friedman2001greedy', 'chen2016xgboost'],
    repo: null,
    note:
      'Dependency-free reimplementation of the XGBoost multiclass protocol (softmax gradient boosting with second-order leaf weights); not a port of the upstream C++ code and not tuned on the benchmark cases.',
  },
};

// ------------------------------------------------------------------ config

export const SEED = 20240917;
/** Sliding-window length used to turn each labelled training run into samples. */
export const TRAIN_WINDOW = 80;
export const TRAIN_STRIDE = 20;

const N_ESTIMATORS = 120;
const LEARNING_RATE = 0.1;
const MAX_DEPTH = 4;
const SUBSAMPLE = 0.8;
const COLSAMPLE = 0.7;
const LAMBDA = 1.0;
const MIN_LEAF = 5;
const TOP_K_PROB = 5;
/** The benchmark answer space is Normal + IDV1..IDV15 (16 readable classes). */
const USE_NAMED_CLASSES_ONLY = true;
/**
 * Smallest window-sample count a user-trained model will accept. Below this the
 * boosting rounds would fit a handful of rows with MIN_LEAF=5 — a constant, not a
 * classifier — so the module refuses instead of reporting a degenerate model.
 */
const MIN_TRAIN_SAMPLES = 12;

// ------------------------------------------------------------- feature core
// (kept local: this module must stay self-contained — no new shared files)

let CORPUS = null;

/** Labelled TEP corpus, restricted to the classes that carry a published name. */
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
    totalRows: t.X.length,
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

/**
 * Align the case's columns to the training corpus by NAME (never by index).
 * Returns perm[p] = index of the case column holding training column p.
 * Throws when the alignment is not exact — a silent mis-prediction is worse.
 */
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

/**
 * Per-column [mean, sd, mean |first difference|] over `rows`, re-ordered from
 * case order into training order. Population sd (ddof=0) — documented choice.
 */
function windowFeatureVector(rows, perm, m) {
  const n = rows.length;
  const F = 3 * m;
  const out = new Float64Array(F);
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

/** Training feature matrix: sliding windows over every labelled run. */
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
      + `(${corpus.classCount} classes, ${window}-sample windows) — at least ${MIN_TRAIN_SAMPLES} are needed; `
      + 'supply more labelled rows per class.',
    );
  }
  return { rows, labels, m, F: 3 * m };
}

/** Standardise a list of feature vectors with training-only statistics. */
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

// ------------------------------------------------------------------- trees

const scratch = [];

/**
 * One exact-split regression tree on (g, h) — the XGBoost structure score.
 * Candidate thresholds are midpoints between adjacent distinct values of a
 * feature, scanned over that feature's globally pre-sorted index list.
 */
function buildTree(X, F, g, h, rows, cols, sortedIdx, mark, stampRef) {
  const feat = [-1];
  const thr = [0];
  const left = [-1];
  const right = [-1];
  const val = [0];
  const push = () => {
    feat.push(-1);
    thr.push(0);
    left.push(-1);
    right.push(-1);
    val.push(0);
    return feat.length - 1;
  };

  const stack = [{ id: 0, rows, depth: 0 }];
  while (stack.length) {
    const node = stack.pop();
    const nodeRows = node.rows;
    let G = 0;
    let H = 0;
    for (let t = 0; t < nodeRows.length; t++) {
      const i = nodeRows[t];
      G += g[i];
      H += h[i];
    }
    const denom = H + LAMBDA;
    val[node.id] = denom > 1e-12 ? -G / denom : 0;

    if (node.depth >= MAX_DEPTH || nodeRows.length < 2 * MIN_LEAF) continue;

    const stamp = ++stampRef.v;
    for (let t = 0; t < nodeRows.length; t++) mark[nodeRows[t]] = stamp;
    const base = (G * G) / (H + LAMBDA + 1e-12);

    let bestGain = 0;
    let bestFeat = -1;
    let bestThr = 0;
    for (let ci = 0; ci < cols.length; ci++) {
      const f = cols[ci];
      const sorted = sortedIdx[f];
      scratch.length = 0;
      for (let t = 0; t < sorted.length; t++) {
        const i = sorted[t];
        if (mark[i] === stamp) scratch.push(i);
      }
      if (scratch.length < 2 * MIN_LEAF) continue;
      let gl = 0;
      let hl = 0;
      for (let t = 0; t + 1 < scratch.length; t++) {
        const i = scratch[t];
        gl += g[i];
        hl += h[i];
        const nl = t + 1;
        const nr = scratch.length - nl;
        if (nl < MIN_LEAF || nr < MIN_LEAF) continue;
        const v1 = X[i * F + f];
        const v2 = X[scratch[t + 1] * F + f];
        if (!(v1 < v2)) continue;
        const gr = G - gl;
        const hr = H - hl;
        if (hl + LAMBDA <= 1e-12 || hr + LAMBDA <= 1e-12) continue;
        const gain = 0.5 * ((gl * gl) / (hl + LAMBDA) + (gr * gr) / (hr + LAMBDA) - base);
        if (gain > bestGain && Number.isFinite(gain)) {
          bestGain = gain;
          bestFeat = f;
          bestThr = (v1 + v2) / 2;
        }
      }
    }
    if (bestFeat < 0) continue;

    const L = [];
    const R = [];
    for (let t = 0; t < nodeRows.length; t++) {
      const i = nodeRows[t];
      if (X[i * F + bestFeat] <= bestThr) L.push(i);
      else R.push(i);
    }
    if (L.length < MIN_LEAF || R.length < MIN_LEAF) continue;

    feat[node.id] = bestFeat;
    thr[node.id] = bestThr;
    const li = push();
    const ri = push();
    left[node.id] = li;
    right[node.id] = ri;
    stack.push({ id: li, rows: L, depth: node.depth + 1 });
    stack.push({ id: ri, rows: R, depth: node.depth + 1 });
  }
  return { feat, thr, left, right, val, nodes: feat.length };
}

function treePredict(tree, x, F) {
  let id = 0;
  while (tree.feat[id] >= 0) {
    id = x[tree.feat[id]] <= tree.thr[id] ? tree.left[id] : tree.right[id];
  }
  return tree.val[id];
}

function softmaxInto(out, offset, K, scale = 1) {
  let max = -Infinity;
  for (let k = 0; k < K; k++) if (out[offset + k] > max) max = out[offset + k];
  let s = 0;
  for (let k = 0; k < K; k++) {
    const e = Math.exp((out[offset + k] - max) * scale);
    out[offset + k] = Number.isFinite(e) ? e : 0;
    s += out[offset + k];
  }
  if (!(s > 0)) {
    for (let k = 0; k < K; k++) out[offset + k] = 1 / K;
    return;
  }
  for (let k = 0; k < K; k++) out[offset + k] /= s;
}

// -------------------------------------------------------------------- model

const MODEL_CACHE = new Map();

export function __resetCacheForTest() {
  MODEL_CACHE.clear();
}

function configKey(F, classCount, corpus) {
  return JSON.stringify({
    id: meta.id,
    seed: SEED,
    F,
    classCount,
    TRAIN_WINDOW,
    TRAIN_STRIDE,
    N_ESTIMATORS,
    LEARNING_RATE,
    MAX_DEPTH,
    SUBSAMPLE,
    COLSAMPLE,
    LAMBDA,
    MIN_LEAF,
    USE_NAMED_CLASSES_ONLY,
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

  const prior = new Float64Array(K);
  for (let i = 0; i < n; i++) prior[y[i]]++;
  for (let k = 0; k < K; k++) prior[k] = Math.max(prior[k] / n, 1e-9);

  const margins = new Float64Array(n * K);
  for (let i = 0; i < n; i++) {
    for (let k = 0; k < K; k++) margins[i * K + k] = Math.log(prior[k]);
  }

  // Global per-feature sorted index lists (built once; reused by every node).
  const sortedIdx = Array.from({ length: F }, (_, f) => {
    const idx = Array.from({ length: n }, (_, i) => i);
    idx.sort((a, b) => X[a * F + f] - X[b * F + f]);
    return idx;
  });
  const mark = new Int32Array(n).fill(-1);
  const stampRef = { v: 0 };
  const allCols = Array.from({ length: F }, (_, f) => f);
  const allRows = Array.from({ length: n }, (_, i) => i);

  const rng = makeRng(SEED);
  const trees = [];
  let totalNodes = 0;

  for (let round = 0; round < N_ESTIMATORS; round++) {
    const P = Float64Array.from(margins);
    for (let i = 0; i < n; i++) softmaxInto(P, i * K, K);

    const g = new Float64Array(n * K);
    const h = new Float64Array(n * K);
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < K; k++) {
        const p = Math.min(Math.max(P[i * K + k], 1e-9), 1 - 1e-9);
        g[i * K + k] = p - (y[i] === k ? 1 : 0);
        h[i * K + k] = Math.max(2 * p * (1 - p), 1e-6);
      }
    }

    const rowSubset = shuffle(allRows, rng).slice(0, Math.max(2 * MIN_LEAF, Math.round(SUBSAMPLE * n)));
    const roundTrees = [];
    for (let k = 0; k < K; k++) {
      const gk = new Float64Array(n);
      const hk = new Float64Array(n);
      for (let t = 0; t < rowSubset.length; t++) {
        const i = rowSubset[t];
        gk[i] = g[i * K + k];
        hk[i] = h[i * K + k];
      }
      const nCols = Math.max(1, Math.round(COLSAMPLE * F));
      const cols = shuffle(allCols, rng).slice(0, nCols);
      const tree = buildTree(X, F, gk, hk, rowSubset, cols, sortedIdx, mark, stampRef);
      totalNodes += tree.nodes;
      roundTrees.push(tree);
      for (let t = 0; t < rowSubset.length; t++) {
        const i = rowSubset[t];
        const upd = LEARNING_RATE * treePredict(tree, X.subarray(i * F, i * F + F), F);
        if (Number.isFinite(upd)) margins[i * K + k] += upd;
      }
    }
    trees.push(roundTrees);
  }

  // Training accuracy (reported, not used for tuning).
  let correct = 0;
  for (let i = 0; i < n; i++) {
    const mrow = predictMargins(trees, X.subarray(i * F, i * F + F), F, K, prior);
    let best = 0;
    for (let k = 1; k < K; k++) if (mrow[k] > mrow[best]) best = k;
    if (best === y[i]) correct++;
  }

  const model = {
    F,
    K,
    mu,
    sd,
    prior,
    trees,
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
    totalNodes,
    seconds: (Date.now() - t0) / 1000,
    cached: false,
  };
  return model;
}

function predictMargins(trees, x, F, K, prior) {
  const out = new Float64Array(K);
  for (let k = 0; k < K; k++) out[k] = Math.log(Math.max(prior[k], 1e-9));
  for (let r = 0; r < trees.length; r++) {
    const roundTrees = trees[r];
    for (let k = 0; k < K; k++) {
      const v = treePredict(roundTrees[k], x, F);
      if (Number.isFinite(v)) out[k] += LEARNING_RATE * v;
    }
  }
  return out;
}

function getModel(F, K, corpus) {
  const key = configKey(F, K, corpus);
  const hit = MODEL_CACHE.has(key);
  if (!hit) MODEL_CACHE.set(key, fit(corpus));
  return { model: MODEL_CACHE.get(key), cached: hit };
}

// --------------------------------------------------------------- entrypoint

function result(t0, extra) {
  return { runtime_ms: Date.now() - t0, ...extra };
}

function notApplicable(ctx, t0) {
  const ds = ctx.caseDef.dataset;
  return result(t0, {
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
      `TEP-trained gradient-boosted classifier cannot be transferred to this process and NO prediction is made. ` +
      `Returning applicable:false rather than forcing a label, falling back to an unsupervised detector, or fabricating a fault class.`,
  });
}

/** No labelled training data was supplied with an upload: refuse, with the reason. */
function notTrained(ctx, t0, reason) {
  return result(t0, {
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
  });
}

const DEFAULT_NO_TRAINING_REASON =
  'No labelled training data is available for this upload, so the gradient-boosted classifier was NOT applied and '
  + 'no prediction is made: a classifier needs labelled examples of each class and inventing them would be '
  + 'fabrication. Re-upload the dataset together with a labelled training CSV (one row per sample, the same sensor '
  + 'column names as the data, plus a class/label column) to make this algorithm usable.';

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

  const margins = predictMargins(model.trees, x, F, model.K, model.prior);
  const probs = Float64Array.from(margins);
  softmaxInto(probs, 0, model.K);

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

  return result(t0, {
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
      model: 'softmax gradient boosting (multiclass, second-order)',
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
    },
    reasoning:
      `Trained on ${model.trainRows} window samples (${model.trainRawRows} labelled TEP rows, 16 named classes, ${TRAIN_WINDOW}-sample windows / stride ${TRAIN_STRIDE}) ` +
      `over ${model.F} features = 3 x ${m} (mean, sd, mean |first difference|); ${N_ESTIMATORS} boosting rounds x ${model.K} per-class trees ` +
      `(${model.totalNodes} nodes total, lr ${LEARNING_RATE}, depth ${MAX_DEPTH}, subsample ${SUBSAMPLE}, colsample ${COLSAMPLE}, lambda ${LAMBDA}, min leaf ${MIN_LEAF}); ` +
      `training-set accuracy ${(model.trainAccuracy * 100).toFixed(2)}%. ` +
      `Fault window = rows ${win.start}..${win.end - 1} (${rows.length} samples). ` +
      `Prediction: '${predicted}' with p=${top.p.toFixed(4)}` +
      (runnerUp ? `, runner-up '${model.labelNames[runnerUp.k]}' p=${runnerUp.p.toFixed(4)}` : '') +
      `. ` +
      (top.k === 0
        ? `The top-ranked class is 0 (Normal). This is reported honestly and NOT dropped from the ranking: ` +
          `the rule learner finds the fault-window aggregate of this case indistinguishable from the labelled normal run` +
          (caseDef.control ? `, which is the expected answer for this control case.` : `, even though the case is a fault case.`)
        : `Ranked top-3: ${top3.map((s, i) => `${i + 1}. ${s}`).join(' | ')}.`) +
      (model.unnamedRuns > 0
        ? ` Note: the FaultExplainer clone also ships ${model.unnamedRuns} further labelled runs (fault16..fault20) with no published fault description; ` +
          `they are excluded (${model.droppedRows} rows) so that every emitted label is a documented TEP fault name.`
        : ''),
  });
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
  // on (see _shared.mjs#scoringWindows): the feature triple is not scale-free,
  // so one whole-record aggregate would be out of distribution for a model
  // trained on short windows. The reported probability is the mean over windows.
  const segments = scoringWindows(rows, model.window, model.stride);
  const probs = new Float64Array(model.K);
  const hits = new Int32Array(model.K);
  for (let i = 0; i < segments.length; i++) {
    const x = standardizeVector(windowFeatureVector(segments[i], perm, m), model.mu, model.sd);
    const margins = predictMargins(model.trees, x, F, model.K, model.prior);
    const p = Float64Array.from(margins);
    softmaxInto(p, 0, model.K);
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

  return result(t0, {
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
      scored_windows: segments.length,
      window_rows: model.window,
      window_agreement: Number(agreement.toFixed(4)),
      short_monitored_window: segments.length === 1 && rows.length < model.window,
      model: 'softmax gradient boosting (multiclass, second-order), trained on the user-supplied labelled file',
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
      `${N_ESTIMATORS} boosting rounds x ${model.K} per-class trees (${model.totalNodes} nodes total, lr ${LEARNING_RATE}, depth ${MAX_DEPTH}, ` +
      `subsample ${SUBSAMPLE}, colsample ${COLSAMPLE}, lambda ${LAMBDA}, min leaf ${MIN_LEAF}); training-set accuracy ${(model.trainAccuracy * 100).toFixed(2)}%. ` +
      `No TEP data and no TEP fault name was used: the answer space is exactly the ${model.K} label(s) supplied by the user. ` +
      `Fault window = rows ${win.start}..${win.end - 1} (${rows.length} samples), scored as ${segments.length} window(s) of ${model.window} rows ` +
      `— the same aggregation the model was trained on` +
      (segments.length === 1 && rows.length < model.window ? ' (the record is shorter than one training window, so the single aggregate is reported as-is)' : '') +
      `; the probabilities below are the mean over those windows and ${hits[top.k]}/${segments.length} of them agree on the top class. ` +
      `Prediction: '${predicted}' with p=${top.p.toFixed(4)}` +
      (runnerUp ? `, runner-up '${model.labelNames[runnerUp.k]}' p=${runnerUp.p.toFixed(4)}` : '') +
      `. Ranked top-3: ${top3.map((s, i) => `${i + 1}. ${s}`).join(' | ')}. ` +
      (verdict === null
        ? `None of the supplied label names identifies a normal/healthy class, so no normal-vs-fault verdict is asserted — `
          + `the ranking above is the complete answer.`
        : `'${model.labelNames[normalIdx]}' is read as the normal class from its name, so the verdict is '${verdict}'.`),
  });
}
