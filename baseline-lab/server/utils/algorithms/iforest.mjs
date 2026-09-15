// Isolation Forest anomaly detection (Liu, Ting & Zhou 2008).
//
// Protocol:
//   reference = the normal-control scenario file of the SAME dataset
//   standardise with the REFERENCE mean/population-std (zero-variance columns
//     guarded to scale 1 by colStats)
//   nTrees = 100 isolation trees, each grown on a subsample of
//     psi = min(256, nReference) reference rows drawn WITHOUT replacement from
//     makeRng(42) — the only randomness in the module, fully seeded
//   split: pick a feature uniformly among the features that actually vary at the
//     node, pick a split value uniformly in [min, max] of that feature, recurse
//     until depth ceil(log2 psi) or an unsplittable node
//   anomaly score  s(x, n) = 2^(-E[h(x)] / c(n)),
//     c(n) = 2 H(n-1) - 2 (n-1)/n,  H(i) = ln(i) + 0.5772156649
//   control limit = 99th percentile of the REFERENCE score distribution
//   alarm when s(x) > limit
//   contributors = mean over trees of (number of path splits on variable j)
//     times |z_j| — a *split-participation depth proxy*, NOT an exact
//     per-variable decomposition of the path length. An isolation tree has no
//     additive per-variable path-length decomposition (a split on variable A
//     changes which variables are offered later), so this proxy is reported as
//     a proxy and the contribution list is labelled accordingly.
//
// The reference-side forest + score law are cached per reference matrix object:
// they depend only on the reference file, so reuse across cases of the same
// dataset changes no number.
//
// HONESTY CONTRACT: this module produces CONTRIBUTING VARIABLES, not mechanisms.
// The variable → root-cause step is the separate, documented mapping in
// ../tep-affinity.mjs and is reported in `diagnosis_step`.

import { quantile, colStats, standardize, makeRng } from '../linalg.mjs';
import { detectionStats, detectorVerdict, rankContributors } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'iforest',
  label: '孤立森林异常检测 (Isolation Forest)',
  short: 'IForest',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'Isolation Forest (100 trees, subsample psi=min(256,nRef), seeded RNG 42, path-length score 2^(-E[h]/c(psi))) trained only on the standardised normal reference, alarmed against the 99th percentile of the reference score distribution, with a split-participation path-depth proxy for diagnosis.',
  provenance: {
    basis: ['liu2008iforest'],
    repo: null,
    note: 'Deterministic in-process reimplementation on the lab linalg primitives; the original paper’s psi=256 subsampling and height limit are kept, and all randomness is seeded so the forest is reproducible.',
  },
};

export const N_TREES = 100;
export const PSI_MAX = 256;
export const SEED = 42;
export const ALARM_Q = 0.99;
const EULER_GAMMA = 0.5772156649;

/** c(n) — average path length of an unsuccessful search in a BST. c(0)=c(1)=0. */
export function cNorm(n) {
  if (n <= 1) return 0;
  const H = Math.log(n - 1) + EULER_GAMMA;
  return 2 * H - (2 * (n - 1)) / n;
}

/** Grow one isolation tree over the reference rows listed in `indices`. */
export function buildTree(Z, indices, depth, maxDepth, m, rng) {
  const size = indices.length;
  if (depth >= maxDepth || size <= 1) return { leaf: true, size };

  const mn = new Float64Array(m).fill(Infinity);
  const mx = new Float64Array(m).fill(-Infinity);
  for (let a = 0; a < size; a++) {
    const r = Z[indices[a]];
    for (let j = 0; j < m; j++) {
      const v = r[j];
      if (v < mn[j]) mn[j] = v;
      if (v > mx[j]) mx[j] = v;
    }
  }
  const splittable = [];
  for (let j = 0; j < m; j++) if (mx[j] > mn[j]) splittable.push(j);
  if (!splittable.length) return { leaf: true, size };

  const q = splittable[Math.floor(rng() * splittable.length)];
  const v = mn[q] + rng() * (mx[q] - mn[q]);

  const left = [];
  const right = [];
  for (let a = 0; a < size; a++) {
    const i = indices[a];
    if (Z[i][q] < v) left.push(i);
    else right.push(i);
  }
  // A degenerate split would create an empty child whose c(0) is undefined.
  if (!left.length || !right.length) return { leaf: true, size };

  return {
    leaf: false,
    q,
    v,
    size,
    left: buildTree(Z, left, depth + 1, maxDepth, m, rng),
    right: buildTree(Z, right, depth + 1, maxDepth, m, rng),
  };
}

/**
 * Path length of z through one tree; when `acc` is supplied, also accumulates
 * how many splits on each variable the path used (the attribution proxy).
 */
export function pathLength(tree, z, acc = null) {
  let node = tree;
  let depth = 0;
  while (!node.leaf) {
    if (acc) acc[node.q] += 1;
    node = z[node.q] < node.v ? node.left : node.right;
    depth++;
  }
  return depth + cNorm(node.size);
}

const FIT_CACHE = new WeakMap();

/** Fit the reference-side forest and the reference score law. */
export function fitIfForest(refX, { nTrees = N_TREES, psiMax = PSI_MAX, seed = SEED, q = ALARM_Q } = {}) {
  const cached = FIT_CACHE.get(refX);
  if (cached && cached.nTrees === nTrees && cached.psiMax === psiMax && cached.seed === seed && cached.q === q) {
    return cached;
  }

  const { mu, sd } = colStats(refX, 0);
  const Z = standardize(refX, mu, sd);
  const n = Z.length;
  const m = Z[0].length;
  const psi = Math.max(1, Math.min(psiMax, n));
  const maxDepth = Math.max(1, Math.ceil(Math.log2(psi)));

  const rng = makeRng(seed);
  const base = Array.from({ length: n }, (_, i) => i);
  const trees = [];
  for (let t = 0; t < nTrees; t++) {
    const pool = base.slice();
    for (let i = 0; i < psi; i++) {
      const j = i + Math.floor(rng() * (n - i));
      const tmp = pool[i];
      pool[i] = pool[j];
      pool[j] = tmp;
    }
    trees.push(buildTree(Z, pool.slice(0, psi), 0, maxDepth, m, rng));
  }

  const cpsi = cNorm(psi);
  const refScore = new Float64Array(n);
  for (let i = 0; i < n; i++) refScore[i] = scoreRow(Z[i], trees, cpsi);
  const threshold = quantile(Array.from(refScore).sort((a, b) => a - b), q);

  const model = { mu, sd, Z, n, m, psi, maxDepth, nTrees, seed, q, trees, cpsi, refScore, threshold };
  FIT_CACHE.set(refX, model);
  return model;
}

/** Anomaly score of one standardised row: s = 2^(-E[h]/c(psi)). */
export function scoreRow(z, trees, cpsi) {
  if (!(cpsi > 0)) return 0.5;
  let sum = 0;
  for (let t = 0; t < trees.length; t++) sum += pathLength(trees[t], z);
  const eh = sum / trees.length;
  const s = Math.pow(2, -eh / cpsi);
  return Number.isFinite(s) ? s : 0.5;
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('IForest baseline requires a normal-control reference for this dataset');
  if (reference.matrix.m !== matrix.m) {
    throw new Error(`IForest: reference width ${reference.matrix.m} does not match case width ${matrix.m}`);
  }

  const model = fitIfForest(reference.matrix.X);
  const win = ctx.faultWindow;
  const Ztest = matrix.X === reference.matrix.X
    ? model.Z
    : standardize(matrix.X, model.mu, model.sd);

  const stat = new Array(matrix.n);
  const stash = new Map();
  const m = matrix.m;
  for (let i = 0; i < matrix.n; i++) {
    const z = Ztest[i];
    if (i >= win.start && i < win.end) {
      const acc = new Float64Array(m);
      let sum = 0;
      for (let t = 0; t < model.trees.length; t++) sum += pathLength(model.trees[t], z, acc);
      const eh = sum / model.trees.length;
      const s = model.cpsi > 0 ? Math.pow(2, -eh / model.cpsi) : 0.5;
      stat[i] = Number.isFinite(s) ? s : 0.5;
      const contrib = new Float64Array(m);
      for (let j = 0; j < m; j++) {
        const c = (acc[j] / model.trees.length) * Math.abs(z[j]);
        contrib[j] = Number.isFinite(c) ? c : 0;
      }
      stash.set(i, contrib);
    } else {
      stat[i] = scoreRow(z, model.trees, model.cpsi);
    }
  }

  const det = detectionStats(stat, model.threshold, win, matrix.n);
  const topVars = rankContributors(matrix, win, (i) => stash.get(i), { topK: 6 });
  const detectable = det.detection_rate > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  const params = `trees=${model.nTrees} psi=${model.psi} h=${model.maxDepth}`;

  return {
    top3: candidates.map((c) => c.label),
    verdict: detectorVerdict(caseDef, det),
    variable_top3: topVars.map((v) => v.col),
    variables_ranked: topVars,
    detection: {
      detection_rate: det.detection_rate,
      alarms: det.alarms,
      window_rows: det.window_rows,
      pre_window_alarm_rate: det.pre_window_alarm_rate,
      threshold: det.threshold,
      max_stat: det.max_stat,
      series_head: det.series_head,
      iforest: det,
      n_trees: model.nTrees,
      psi: model.psi,
      height_limit: model.maxDepth,
      reference_rows: model.n,
      seed: model.seed,
      c_psi: Number(model.cpsi.toFixed(6)),
      attribution: 'split-participation path-depth proxy (not an additive decomposition)',
      detectable,
      params,
    },
    reasoning: detectable
      ? `Isolation Forest (${model.nTrees} trees, psi=${model.psi}, height limit ${model.maxDepth}, seed ${model.seed}) alarms on ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%) against the reference 99th-percentile score ${det.threshold} over the ${model.n}-row reference score law (max score ${det.max_stat}, pre-window alarm rate ${det.pre_window_alarm_rate === null ? 'n/a' : (det.pre_window_alarm_rate * 100).toFixed(2) + '%'}). Highest split-participation depth proxy x |z|: ${topVars.slice(0, 3).map((v) => v.col).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: the Isolation Forest score exceeds the reference 99th-percentile limit ${det.threshold} on only ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%; max score ${det.max_stat}), i.e. at the control-limit expectation. IForest reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? 'mean over the 100 trees of (number of path splits on variable j) x |z_j|, averaged over the fault window -> top-6 -> documented TEP variable-affinity table (tep-affinity.mjs). NOTE: this is a split-participation depth PROXY, not an exact additive per-variable path-length decomposition — isolation-tree paths are not additive in the variables.'
      : 'unavailable for this domain (no published variable->cause table); split-participation proxy variables reported only',
    runtime_ms: Date.now() - t0,
  };
}
