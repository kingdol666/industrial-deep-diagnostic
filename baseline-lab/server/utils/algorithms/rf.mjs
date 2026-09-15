// Random forest classifier — Breiman 2001.
//
// PROTOCOL
// --------
// Training source : the LABELLED TEP corpus shipped inside the FaultExplainer
//                   clone (baselines/FaultExplainer/backend/data/faultN.csv)
//                   via dataset.mjs#loadFeTrainingSet() — 16 named runs
//                   (Normal + IDV1..IDV15), 480 fault-active rows each.
// Features        : the case's FAULT WINDOW aggregated per column into
//                   [mean, sd, mean |first difference|] -> 156 features, built
//                   identically (over 80-sample / stride-20 sliding windows)
//                   for the training corpus. Standardised with TRAINING
//                   statistics only.
// Model           : 120 bootstrap trees, fully grown to depth <= 12, mtry =
//                   floor(sqrt(156)) = 12 candidate features examined per node,
//                   Gini impurity split selection over exact thresholds,
//                   majority vote; class probability = vote fraction.
// Determinism     : one makeRng(SEED) stream drives bootstrap sampling and the
//                   per-node feature draws in a fixed order.
//
// APPLICABILITY LIMIT (honesty requirement)
// -----------------------------------------
// The only labelled corpus in this repository is TEP. For any non-TEP case this
// module returns applicable:false and makes no prediction.

import { makeRng, colStats } from '../linalg.mjs';
import { loadFeTrainingSet, FE_FAULT_DESCRIPTIONS } from '../dataset.mjs';

export const meta = {
  id: 'rf-forest',
  label: '随机森林分类器',
  short: 'RF',
  family: 'supervised',
  kind: 'classifier',
  deterministic: true,
  requiresProvider: false,
  needsReference: false,
  needsTraining: true,
  domains: ['tep'],
  description:
    'Breiman random forest (120 bootstrap trees, depth<=12, mtry=floor(sqrt(nFeatures))=12, exact-threshold Gini splits, majority vote with the vote fraction as class probability) trained on 3*m window features of the labelled FaultExplainer TEP corpus and applied to TEP cases only.',
  provenance: {
    basis: ['breiman2001random'],
    repo: null,
    note:
      'Dependency-free reimplementation of the random-forest protocol; not a port of any specific library and not tuned on the benchmark cases.',
  },
};

// ------------------------------------------------------------------ config

export const SEED = 20240917;
export const TRAIN_WINDOW = 80;
export const TRAIN_STRIDE = 20;

const N_TREES = 120;
const MAX_DEPTH = 12;
const TOP_K_PROB = 5;
const USE_NAMED_CLASSES_ONLY = true;

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
    usedRows: t.y.length - dropped,
    droppedRows: dropped,
    unnamedRuns: t.labelNames.length - classCount,
  };
  return CORPUS;
}

/** Align case columns to the training corpus by NAME; throw on any mismatch. */
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
  const rows = [];
  const labels = [];
  for (let k = 0; k < corpus.classCount; k++) {
    const idx = corpus.byClass[k];
    for (let s = 0; s + TRAIN_WINDOW <= idx.length; s += TRAIN_STRIDE) {
      const win = [];
      for (let t = s; t < s + TRAIN_WINDOW; t++) win.push(corpus.X[idx[t]]);
      rows.push(windowFeatureVector(win, identity, m));
      labels.push(k);
    }
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

// ------------------------------------------------------------------- trees

const scratch = [];

/**
 * One CART classification tree grown on a bootstrap sample with Gini impurity.
 * Split selection maximises lSq/nL + rSq/nR where sq = sum of squared per-class
 * counts — algebraically identical to minimising the weighted Gini impurity of
 * the two children, and O(1) per candidate threshold.
 *
 * The bootstrap draw is a MULTISET: `bootRows` may contain the same sample
 * several times. It is collapsed once at the root into (distinct index, weight)
 * so the presorted-column scan stays O(n) per feature while the split score
 * still uses the true bootstrap multiplicities.
 */
function buildTree(X, F, y, bootRows, K, sortedIdx, mark, wmark, stampRef, rng, sampler) {
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

  // Collapse the bootstrap multiset into distinct indices + counts.
  const rootIdx = [];
  const rootW = [];
  const seen = new Map();
  for (let t = 0; t < bootRows.length; t++) {
    const i = bootRows[t];
    const p = seen.get(i);
    if (p === undefined) {
      seen.set(i, rootIdx.length);
      rootIdx.push(i);
      rootW.push(1);
    } else rootW[p]++;
  }

  const leftCount = new Float64Array(K);
  const rightCount = new Float64Array(K);
  const stack = [{ id: 0, rows: rootIdx, w: Float64Array.from(rootW), depth: 0 }];
  while (stack.length) {
    const node = stack.pop();
    const nodeRows = node.rows;
    const nodeW = node.w;
    const nDistinct = nodeRows.length;

    let nNode = 0;
    const totCount = new Float64Array(K);
    for (let t = 0; t < nDistinct; t++) {
      const w = nodeW[t];
      nNode += w;
      totCount[y[nodeRows[t]]] += w;
    }
    let totSq = 0;
    let majority = 0;
    for (let k = 0; k < K; k++) {
      totSq += totCount[k] * totCount[k];
      if (totCount[k] > totCount[majority]) majority = k;
    }
    val[node.id] = majority;

    if (node.depth >= MAX_DEPTH || nDistinct < 2) continue;
    if (totSq === nNode * nNode) continue; // pure node

    const stamp = ++stampRef.v;
    for (let t = 0; t < nDistinct; t++) {
      const i = nodeRows[t];
      mark[i] = stamp;
      wmark[i] = nodeW[t];
    }

    // mtry distinct features drawn uniformly for THIS node (partial Fisher-Yates).
    sampler.draw(rng);

    let bestSq = totSq / nNode;
    let bestFeat = -1;
    let bestThr = 0;
    for (let ci = 0; ci < sampler.k; ci++) {
      const f = sampler.pool[ci];
      const sorted = sortedIdx[f];
      scratch.length = 0;
      for (let t = 0; t < sorted.length; t++) {
        const i = sorted[t];
        if (mark[i] === stamp) scratch.push(i);
      }
      if (scratch.length < 2) continue;
      // Exact incremental Gini: the scan moves each sample from the right side
      // to the left, keeping lSq = sum_k left_k^2 and rSq = sum_k right_k^2
      // exactly (rSq = totSq - lSq would be WRONG: sum (t-l)^2 != sum t^2 - sum l^2).
      leftCount.fill(0);
      rightCount.set(totCount);
      let lSq = 0;
      let rSq = totSq;
      let nl = 0;
      for (let t = 0; t + 1 < scratch.length; t++) {
        const i = scratch[t];
        const w = wmark[i];
        const yk = y[i];
        rSq += w * (w - 2 * rightCount[yk]);
        rightCount[yk] -= w;
        lSq += w * (2 * leftCount[yk] + w);
        leftCount[yk] += w;
        nl += w;
        const nr = nNode - nl;
        if (nl <= 0 || nr <= 0) continue;
        const v1 = X[i * F + f];
        const v2 = X[scratch[t + 1] * F + f];
        if (!(v1 < v2)) continue;
        const score = lSq / nl + rSq / nr;
        if (score > bestSq) {
          bestSq = score;
          bestFeat = f;
          bestThr = (v1 + v2) / 2;
        }
      }
    }
    sampler.undo();
    if (bestFeat < 0) continue;

    const L = [];
    const LW = [];
    const R = [];
    const RW = [];
    for (let t = 0; t < nDistinct; t++) {
      const i = nodeRows[t];
      if (X[i * F + bestFeat] <= bestThr) {
        L.push(i);
        LW.push(nodeW[t]);
      } else {
        R.push(i);
        RW.push(nodeW[t]);
      }
    }
    if (!L.length || !R.length) continue;

    feat[node.id] = bestFeat;
    thr[node.id] = bestThr;
    const li = push();
    const ri = push();
    left[node.id] = li;
    right[node.id] = ri;
    stack.push({ id: li, rows: L, w: Float64Array.from(LW), depth: node.depth + 1 });
    stack.push({ id: ri, rows: R, w: Float64Array.from(RW), depth: node.depth + 1 });
  }
  return { feat, thr, left, right, val, nodes: feat.length };
}

function treePredict(tree, x) {
  let id = 0;
  while (tree.feat[id] >= 0) {
    id = x[tree.feat[id]] <= tree.thr[id] ? tree.left[id] : tree.right[id];
  }
  return tree.val[id];
}

// -------------------------------------------------------------------- model

const MODEL_CACHE = new Map();

export function __resetCacheForTest() {
  MODEL_CACHE.clear();
}

function configKey(F, classCount) {
  return JSON.stringify({
    id: meta.id, seed: SEED, F, classCount, TRAIN_WINDOW, TRAIN_STRIDE,
    N_TREES, MAX_DEPTH, USE_NAMED_CLASSES_ONLY,
  });
}

function fit() {
  const t0 = Date.now();
  const corpus = loadCorpus();
  const { rows, labels, m, F } = buildTrainingMatrix(corpus);
  const K = corpus.classCount;
  const n = rows.length;

  const { mu, sd } = colStats(rows, 1);
  const X = standardizeRows(rows, mu, sd);
  const y = Int32Array.from(labels);

  const sortedIdx = Array.from({ length: F }, (_, f) => {
    const idx = Array.from({ length: n }, (_, i) => i);
    idx.sort((a, b) => X[a * F + f] - X[b * F + f]);
    return idx;
  });
  const mark = new Int32Array(n).fill(-1);
  const wmark = new Float64Array(n);
  const stampRef = { v: 0 };
  const rng = makeRng(SEED);
  const mtry = Math.max(1, Math.floor(Math.sqrt(F)));
  // Uniform mtry-subset sampler: partial Fisher-Yates over a persistent pool,
  // undone after each node so the pool stays the identity permutation.
  const pool = Int32Array.from({ length: F }, (_, i) => i);
  const js = new Int32Array(mtry);
  const sampler = {
    pool,
    k: mtry,
    draw(r) {
      for (let i = 0; i < mtry; i++) {
        const j = i + Math.floor(r() * (F - i));
        js[i] = j;
        const t = pool[i];
        pool[i] = pool[j];
        pool[j] = t;
      }
    },
    undo() {
      for (let i = mtry - 1; i >= 0; i--) {
        const j = js[i];
        const t = pool[i];
        pool[i] = pool[j];
        pool[j] = t;
      }
    },
  };

  const trees = [];
  let totalNodes = 0;
  for (let t = 0; t < N_TREES; t++) {
    const boot = new Array(n);
    for (let i = 0; i < n; i++) boot[i] = Math.floor(rng() * n);
    const tree = buildTree(X, F, y, boot, K, sortedIdx, mark, wmark, stampRef, rng, sampler);
    totalNodes += tree.nodes;
    trees.push(tree);
  }

  let correct = 0;
  for (let i = 0; i < n; i++) {
    const p = predictProbabilities(trees, X.subarray(i * F, i * F + F), K);
    let best = 0;
    for (let k = 1; k < K; k++) if (p[k] > p[best]) best = k;
    if (best === y[i]) correct++;
  }

  return {
    F,
    K,
    mu,
    sd,
    trees,
    mtry,
    labelNames: corpus.labelNames,
    trainRows: n,
    trainRawRows: corpus.usedRows,
    droppedRows: corpus.droppedRows,
    unnamedRuns: corpus.unnamedRuns,
    source: corpus.source,
    trainAccuracy: correct / n,
    totalNodes,
    seconds: (Date.now() - t0) / 1000,
  };
}

/** Class probability = vote fraction across the forest. */
function predictProbabilities(trees, x, K) {
  const votes = new Float64Array(K);
  for (let t = 0; t < trees.length; t++) votes[treePredict(trees[t], x)]++;
  const total = trees.length || 1;
  for (let k = 0; k < K; k++) votes[k] /= total;
  return votes;
}

function getModel(F, K) {
  const key = configKey(F, K);
  const hit = MODEL_CACHE.has(key);
  if (!hit) MODEL_CACHE.set(key, fit());
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
      `Not applicable to the '${ds}' domain: the only labelled training corpus available in this repository is the ` +
      `Tennessee Eastman (TEP) FaultExplainer set (Normal + IDV1..IDV15). No labelled '${ds}' data exists, so a ` +
      `TEP-trained random forest cannot be applied to this process and NO prediction is made. ` +
      `Returning applicable:false rather than forcing a label, falling back to an unsupervised detector, or fabricating a fault class.`,
    runtime_ms: Date.now() - t0,
  };
}

export async function run(ctx) {
  const t0 = Date.now();
  const caseDef = ctx.caseDef;
  if (!caseDef || caseDef.dataset !== 'tep') return notApplicable(ctx, t0);

  const corpus = loadCorpus();
  const m = corpus.cols.length;
  const perm = alignmentPerm(corpus.cols, ctx.matrix.colNames);
  const win = ctx.faultWindow;
  const rows = ctx.matrix.X.slice(win.start, win.end);
  if (!rows.length) throw new Error(`empty fault window for ${caseDef.case_id}`);

  const raw = windowFeatureVector(rows, perm, m);
  const F = 3 * m;
  const { model, cached } = getModel(F, corpus.classCount);
  const x = standardizeVector(raw, model.mu, model.sd);

  const probs = predictProbabilities(model.trees, x, model.K);
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
      votes_for_top_class: Math.round(top.p * model.trees.length),
      n_trees: model.trees.length,
      train_accuracy: Number(model.trainAccuracy.toFixed(4)),
      model: 'random forest (majority vote, vote fraction as probability)',
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
      `over ${model.F} features = 3 x ${m} (mean, sd, mean |first difference|); ${model.trees.length} bootstrap trees, maxDepth ${MAX_DEPTH}, mtry ${model.mtry}, ` +
      `Gini splits, ${model.totalNodes} nodes total; in-bag training accuracy ${(model.trainAccuracy * 100).toFixed(2)}%. ` +
      `Fault window = rows ${win.start}..${win.end - 1} (${rows.length} samples). ` +
      `Prediction: '${predicted}' with vote fraction ${top.p.toFixed(4)}` +
      (runnerUp ? `, runner-up '${model.labelNames[runnerUp.k]}' with ${runnerUp.p.toFixed(4)}` : '') +
      `. ` +
      (top.k === 0
        ? `The top-ranked class is 0 (Normal). This is reported honestly and NOT dropped from the ranking` +
          (caseDef.control ? `, which is the expected answer for this control case.` : `, even though the case is a fault case.`)
        : `Ranked top-3: ${top3.map((s, i) => `${i + 1}. ${s}`).join(' | ')}. ` +
          `Vote fractions are quantised in steps of 1/${model.trees.length}, so a probability of 0.5 is not a calibrated confidence but a near-tie in the forest.`) +
      (model.unnamedRuns > 0
        ? ` Note: the FaultExplainer clone also ships ${model.unnamedRuns} further labelled runs (fault16..fault20) with no published fault description; ` +
          `they are excluded (${model.droppedRows} rows) so that every emitted label is a documented TEP fault name.`
        : ''),
    runtime_ms: Date.now() - t0,
  };
}
