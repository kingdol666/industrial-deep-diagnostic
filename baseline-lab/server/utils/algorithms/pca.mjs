// Classical PCA process monitoring — Chiang et al. 2001 / Qin 2012 protocol.
//
// Faithful port of scripts/benchmark/baseline_pca.mjs (population std, ddof=0
// covariance, 95% cumulative-variance retention, T² + SPE, 99th-percentile
// control limits taken from the reference distribution, SPE top-3
// contributions). Keeping the arithmetic identical is deliberate: it lets the
// lab VERIFY itself against the repository's archived
// results/benchmark/baseline_pca_rca.json instead of merely asserting a
// reproduction.

import { jacobiEigen, quantile } from '../linalg.mjs';
import { detectionStats, detectorVerdict } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'pca-t2-spe',
  label: '经典 PCA 监测 (T²+SPE)',
  short: 'PCA',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'Normal-reference PCA, 95% cumulative variance retained, Hotelling T² + SPE (Q) statistics, 99th-percentile control limits from the reference distribution, SPE-contribution top-3 for diagnosis.',
  provenance: {
    basis: ['chiang2001fault', 'qin2012survey'],
    repo: null,
    note: 'Deterministic in-process reimplementation; arithmetic matches scripts/benchmark/baseline_pca.mjs.',
  },
};

export const VAR_CUTOFF = 0.95;
export const ALARM_Q = 0.99;

export function fitPca(train, { varCutoff = VAR_CUTOFF } = {}) {
  const n = train.length;
  const m = train[0].length;
  const mu = new Float64Array(m);
  const sd = new Float64Array(m);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) mu[j] += train[i][j] / n;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < m; j++) {
      const d = train[i][j] - mu[j];
      sd[j] += (d * d) / n; // population std (ddof=0) — matches the incumbent script
    }
  }
  for (let j = 0; j < m; j++) sd[j] = Math.sqrt(sd[j]) || 1;

  const Z = train.map((r) => Array.from(r, (v, j) => (v - mu[j]) / sd[j]));
  const C = Array.from({ length: m }, () => new Float64Array(m));
  for (const r of Z) {
    for (let a = 0; a < m; a++) {
      for (let b = a; b < m; b++) C[a][b] += (r[a] * r[b]) / n;
    }
  }
  for (let a = 0; a < m; a++) for (let b = 0; b < a; b++) C[a][b] = C[b][a];

  const { values, vectors } = jacobiEigen(C);
  const total = Array.from(values).reduce((s, v) => s + Math.max(v, 0), 0) || 1;
  let cum = 0, a = 0;
  for (let k = 0; k < values.length; k++) {
    cum += Math.max(values[k], 0) / total;
    a++;
    if (cum >= varCutoff) break;
  }
  const P = [];
  const lam = [];
  for (let k = 0; k < a; k++) {
    P.push(Array.from({ length: m }, (_, i) => vectors[i][k]));
    lam.push(Math.max(values[k], 0));
  }
  return { mu: Array.from(mu), sd: Array.from(sd), P, lam, a };
}

export function pcaStatistics(mat, model) {
  const { mu, sd, P, lam } = model;
  const m = mu.length;
  const out = [];
  for (const r of mat) {
    const z = new Array(m);
    for (let j = 0; j < m; j++) z[j] = (r[j] - mu[j]) / sd[j];
    const scores = new Array(P.length);
    for (let k = 0; k < P.length; k++) {
      let s = 0;
      const Pk = P[k];
      for (let j = 0; j < m; j++) s += Pk[j] * z[j];
      scores[k] = s;
    }
    const recon = new Float64Array(m);
    for (let k = 0; k < P.length; k++) {
      const s = scores[k], Pk = P[k];
      for (let j = 0; j < m; j++) recon[j] += s * Pk[j];
    }
    const e = new Float64Array(m);
    let t2 = 0, spe = 0;
    for (let k = 0; k < scores.length; k++) t2 += (scores[k] * scores[k]) / (lam[k] || 1e-12);
    for (let j = 0; j < m; j++) {
      e[j] = z[j] - recon[j];
      spe += e[j] * e[j];
    }
    out.push({ t2, spe, e });
  }
  return out;
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('PCA baseline requires a normal-control reference for this dataset');

  const model = fitPca(reference.matrix.X);
  const trainStats = pcaStatistics(reference.matrix.X, model);
  const thrT2 = quantile(trainStats.map((s) => s.t2).sort((x, y) => x - y), ALARM_Q);
  const thrSpe = quantile(trainStats.map((s) => s.spe).sort((x, y) => x - y), ALARM_Q);

  const stats = pcaStatistics(matrix.X, model);

  // Window convention: TEP fault cases start at the published onset (row 161);
  // control and non-TEP files are already windowed, so use the whole file.
  const start = caseDef.dataset === 'tep' && !caseDef.control ? 160 : 0;
  const win = { start, end: matrix.n };

  const detT2 = detectionStats(stats.map((s) => s.t2), thrT2, win, matrix.n);
  const detSpe = detectionStats(stats.map((s) => s.spe), thrSpe, win, matrix.n);

  const alarmRows = stats.slice(start).filter((s) => s.spe > thrSpe);
  const basis = alarmRows.length ? alarmRows : stats.slice(start);
  const sums = new Float64Array(matrix.m);
  for (const s of basis) for (let j = 0; j < matrix.m; j++) sums[j] += (s.e[j] * s.e[j]) / basis.length;
  const ranked = Array.from({ length: matrix.m }, (_, j) => ({ col: matrix.colNames[j], contribution: sums[j] }))
    .sort((a, b) => b.contribution - a.contribution);

  const topVars = ranked.slice(0, 6).map((r) => ({ col: r.col, contribution: Number(r.contribution.toFixed(6)) }));
  const detectable = Math.max(detT2.detection_rate, detSpe.detection_rate) > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  return {
    top3: candidates.map((c) => c.label),
    verdict: detectorVerdict(caseDef, detT2.detection_rate > detSpe.detection_rate ? detT2 : detSpe),
    variable_top3: topVars.map((v) => v.col),
    variables_ranked: topVars,
    detection: {
      T2: detT2,
      SPE: detSpe,
      components_retained: model.a,
      detectable,
    },
    reasoning: detectable
      ? `SPE alarm rate ${(detSpe.detection_rate * 100).toFixed(2)}% / T² ${(detT2.detection_rate * 100).toFixed(2)}% over the fault window. Dominant residual contributors: ${topVars.slice(0, 3).map((v) => v.col).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: SPE alarm rate ${(detSpe.detection_rate * 100).toFixed(2)}% and T² ${(detT2.detection_rate * 100).toFixed(2)}% are at the control-limit expectation. The classical detector reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? 'contribution top-6 -> documented TEP variable-affinity table (tep-affinity.mjs)'
      : 'unavailable for this domain (no published variable->cause table); variables reported only',
    runtime_ms: Date.now() - t0,
  };
}
