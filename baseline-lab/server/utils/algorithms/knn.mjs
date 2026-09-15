// k-NN fault detection (He & Wang 2007 style nearest-neighbour distance
// monitoring, with the standard k = 5 choice).
//
// Protocol:
//   reference = the normal-control scenario file of the SAME dataset
//   standardise with the REFERENCE mean/population-std (zero-variance columns
//     guarded to scale 1 by colStats)
//   training set = ALL reference rows (k-NN is a lazy learner: no model fitting,
//     every normal reference sample is a prototype)
//   per test row x:  D²(x) = (1/k) Σ_{i in kNN(x)} ||z_x - z_i||²   (k = 5)
//   control limit = 99th percentile of the REFERENCE-to-REFERENCE k-NN distance
//     distribution, computed leave-one-out (a reference row is never its own
//     neighbour, otherwise the distribution would be all zeros)
//   alarm when D²(x) > limit
//   contributors = per-variable squared deviation in the nearest-neighbour
//     residual, averaged over the k neighbours and over the fault window
//
// SELF-MATCH RULE (applies to the control case, where the case file IS the
// reference file): a test row is likewise never its own neighbour. That makes
// the control case a leave-one-out novelty test — a strictly harder, more
// honest check than letting each reference row match itself at distance 0.
//
// The reference-side fit (standardisation + LOO distance distribution) is cached
// per reference matrix object: it depends only on the reference file, so reuse
// across cases of the same dataset changes no number.
//
// HONESTY CONTRACT: this module produces CONTRIBUTING VARIABLES, not mechanisms.
// The variable → root-cause step is the separate, documented mapping in
// ../tep-affinity.mjs and is reported in `diagnosis_step`.

import { quantile, colStats, standardize } from '../linalg.mjs';
import { detectionStats, detectorVerdict, rankContributors } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'knn-fdd',
  label: 'k近邻故障检测 (k-NN 距离监测)',
  short: 'kNN',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'Reference-standardised k-NN fault detection with k=5: mean squared Euclidean distance to the five nearest normal reference rows, alarmed against the 99th percentile of the leave-one-out reference-to-reference distance distribution, with nearest-neighbour residual contributions for diagnosis.',
  provenance: {
    basis: ['he2007knn'],
    repo: null,
    note: 'Deterministic in-process reimplementation on the lab linalg primitives; brute-force exact k-NN (no approximate index), so results are exact and reproducible.',
  },
};

export const K_NEIGHBOURS = 5;
export const ALARM_Q = 0.99;

/** Exact k-nearest search in standardised space; `exclude` implements leave-one-out. */
export function knnSearch(z, Zref, k, exclude = -1) {
  const m = z.length;
  const n = Zref.length;
  const bd = new Float64Array(k).fill(Infinity);
  const bi = new Int32Array(k).fill(-1);
  for (let i = 0; i < n; i++) {
    if (i === exclude) continue;
    const r = Zref[i];
    let d = 0;
    for (let j = 0; j < m; j++) {
      const t = z[j] - r[j];
      d += t * t;
    }
    if (d >= bd[k - 1]) continue;
    let p = k - 1;
    while (p > 0 && bd[p - 1] > d) {
      bd[p] = bd[p - 1];
      bi[p] = bi[p - 1];
      p--;
    }
    bd[p] = d;
    bi[p] = i;
  }
  return { bd, bi };
}

/** Mean squared distance + per-variable residual for an explicit neighbour list. */
export function knnResidual(z, Zref, ids, k) {
  const m = z.length;
  const res = new Float64Array(m);
  let sum = 0;
  let cnt = 0;
  for (let p = 0; p < k; p++) {
    const i = ids[p];
    if (i < 0) continue;
    const r = Zref[i];
    let d = 0;
    for (let j = 0; j < m; j++) {
      const t = z[j] - r[j];
      res[j] += t * t;
      d += t * t;
    }
    sum += d;
    cnt++;
  }
  if (!cnt) return { md2: 0, res };
  for (let j = 0; j < m; j++) res[j] /= cnt;
  return { md2: sum / cnt, res };
}

const FIT_CACHE = new WeakMap();

/** Fit the reference-side k-NN model (standardisation + LOO distance law). */
export function fitKnn(refX, { k = K_NEIGHBOURS, q = ALARM_Q } = {}) {
  const cached = FIT_CACHE.get(refX);
  if (cached && cached.k === k && cached.q === q) return cached;

  const { mu, sd } = colStats(refX, 0);
  const Z = standardize(refX, mu, sd);
  const n = Z.length;
  const refDist = new Float64Array(n);
  const neigh = new Int32Array(n * k).fill(-1);

  for (let i = 0; i < n; i++) {
    const { bd, bi } = knnSearch(Z[i], Z, k, i);
    let s = 0;
    let c = 0;
    for (let p = 0; p < k; p++) {
      if (bi[p] < 0) continue;
      s += bd[p];
      c++;
      neigh[i * k + p] = bi[p];
    }
    refDist[i] = c ? s / c : 0;
  }

  const threshold = quantile(Array.from(refDist).sort((a, b) => a - b), q);
  const model = { mu, sd, Z, n, k, q, refDist, neigh, threshold };
  FIT_CACHE.set(refX, model);
  return model;
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('kNN baseline requires a normal-control reference for this dataset');
  if (reference.matrix.m !== matrix.m) {
    throw new Error(`kNN: reference width ${reference.matrix.m} does not match case width ${matrix.m}`);
  }

  const model = fitKnn(reference.matrix.X);
  const Zref = model.Z;
  const k = model.k;
  const win = ctx.faultWindow;

  const Ztest = matrix.X === reference.matrix.X
    ? Zref
    : standardize(matrix.X, model.mu, model.sd);
  const selfMatch = reference.is_self && matrix.X === reference.matrix.X;

  const stat = new Array(matrix.n);
  const stash = new Map();
  for (let i = 0; i < matrix.n; i++) {
    let md2;
    let res = null;
    if (selfMatch) {
      md2 = model.refDist[i];
      if (i >= win.start && i < win.end) {
        res = knnResidual(Ztest[i], Zref, model.neigh.subarray(i * k, i * k + k), k).res;
      }
    } else {
      const s = knnSearch(Ztest[i], Zref, k, -1);
      const r = knnResidual(Ztest[i], Zref, s.bi, k);
      md2 = r.md2;
      res = r.res;
    }
    stat[i] = md2;
    if (res) stash.set(i, res);
  }

  const det = detectionStats(stat, model.threshold, win, matrix.n);
  const topVars = rankContributors(matrix, win, (i) => stash.get(i), { topK: 6 });
  const detectable = det.detection_rate > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  const params = `k=${k} nref=${model.n}${selfMatch ? ' loo' : ''}`;

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
      knn: det,
      k,
      reference_rows: model.n,
      leave_one_out: selfMatch,
      detectable,
      params,
    },
    reasoning: detectable
      ? `k-NN (k=${k}) mean squared distance alarms on ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%) against the reference leave-one-out 99th-percentile limit ${det.threshold} (max distance ${det.max_stat}, pre-window alarm rate ${det.pre_window_alarm_rate === null ? 'n/a' : (det.pre_window_alarm_rate * 100).toFixed(2) + '%'}). The 99th percentile comes from the ${model.n}-row reference-to-reference distribution, so the limit never sees the file under test. Largest nearest-neighbour residual contributions: ${topVars.slice(0, 3).map((v) => v.col).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: the k-NN mean squared distance (k=${k}) alarms on only ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%) against the reference leave-one-out 99th-percentile limit ${det.threshold} (max distance ${det.max_stat}), i.e. at the control-limit expectation. k-NN reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? 'mean squared nearest-neighbour residual per original variable (mean over the k=5 neighbours, then over the fault window) -> top-6 -> documented TEP variable-affinity table (tep-affinity.mjs)'
      : 'unavailable for this domain (no published variable->cause table); nearest-neighbour residual variables reported only',
    runtime_ms: Date.now() - t0,
  };
}
