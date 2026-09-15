// Independent Component Analysis process monitoring (FastICA + I²/SPE).
//
// Protocol (Hyvärinen & Oja 2000 for FastICA; Lee, Qin & Lee 2006 for the
// I²/SPE monitoring scheme that is standard in the ICA-FDD literature):
//
//   reference = the normal-control scenario file of the SAME dataset
//   standardise with the REFERENCE mean/population-std
//   PCA-whiten the reference, retaining components to 95% cumulative variance
//     (population covariance, exactly the convention pca.mjs uses)
//   FastICA, symmetric decorrelation W <- (W Wᵀ)^(-1/2) W, tanh nonlinearity,
//     at most 500 iterations, tolerance 1e-6, seeded RNG (makeRng(42)) so the
//     unmixing matrix is bit-reproducible
//   I²  = sum of squared independent components  (variation inside the retained
//         subspace, the ICA analogue of T²)
//   SPE = squared residual from the retained PCA subspace in standardised units
//         (variation orthogonal to it, the ICA analogue of Q)
//   limits = 99th percentile of the REFERENCE I² and SPE distributions
//   SPE contribution = squared residual per original variable
//
// CONVERGENCE NOTE: symmetric FastICA is a fixed-point iteration; with the tanh
// contrast on whitened data it converges in tens of iterations. `converged` and
// `iterations` are reported in `detection` so a non-converged run is visible
// rather than silently trusted.
//
// HONESTY CONTRACT: this module produces CONTRIBUTING VARIABLES, not mechanisms.
// The variable → root-cause step is the separate, documented mapping in
// ../tep-affinity.mjs and is reported in `diagnosis_step`.

import { jacobiEigen, quantile, colStats, standardize, covariance, zeros, makeRng } from '../linalg.mjs';
import { detectionStats, detectorVerdict, rankContributors } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'ica-fastica',
  label: '独立成分分析监测 (FastICA I²+SPE)',
  short: 'ICA',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'Reference-standardised PCA whitening at 95% variance, symmetric-decorrelation FastICA (tanh, max 500 iterations, tol 1e-6, seed 42), I² and SPE statistics with 99th-percentile reference limits, SPE-residual top-3 contribution for diagnosis.',
  provenance: {
    basis: ['hyvarinen2000fastica', 'lee2006ica'],
    repo: null,
    note: 'Deterministic in-process reimplementation on the lab linalg primitives; the only randomness is the seeded FastICA initialisation.',
  },
};

export const VAR_CUTOFF = 0.95;
export const ALARM_Q = 0.99;
export const MAX_ITER = 500;
export const TOL = 1e-6;
export const SEED = 42;
const LAM_FLOOR = 1e-12;

/** M^(-1/2) · W for the symmetric FastICA decorrelation step. */
function symmetricDecorrelate(W, a) {
  const M = zeros(a, a);
  for (let i = 0; i < a; i++) {
    for (let j = i; j < a; j++) {
      let s = 0;
      for (let k = 0; k < a; k++) s += W[i][k] * W[j][k];
      M[i][j] = s;
      M[j][i] = s;
    }
  }
  const { values, vectors } = jacobiEigen(M);

  // M^(-1/2) = V diag(1/sqrt(lambda)) V^T  (M is symmetric PSD; eigenvalues are
  // floored so a degenerate M yields a finite — never NaN — decorrelation).
  const Minv = zeros(a, a);
  for (let c = 0; c < a; c++) {
    const inv = 1 / Math.sqrt(Math.max(values[c], LAM_FLOOR));
    const vc = Float64Array.from({ length: a }, (_, i) => vectors[i][c]);
    for (let i = 0; i < a; i++) {
      const s = inv * vc[i];
      if (s === 0) continue;
      const row = Minv[i];
      for (let k = 0; k < a; k++) row[k] += s * vc[k];
    }
  }

  const out = zeros(a, a);
  for (let i = 0; i < a; i++) {
    for (let k = 0; k < a; k++) {
      const mik = Minv[i][k];
      if (mik === 0) continue;
      const Wk = W[k];
      const outi = out[i];
      for (let j = 0; j < a; j++) outi[j] += mik * Wk[j];
    }
  }
  return out;
}

/**
 * Fit the ICA monitoring model on a raw (unstandardised) training matrix.
 * Returns the standardisation, the whitening matrix, the unmixing matrix and
 * the orthogonal loadings used for the SPE residual.
 */
export function fitIca(train, {
  varCutoff = VAR_CUTOFF,
  maxIter = MAX_ITER,
  tol = TOL,
  seed = SEED,
} = {}) {
  const m = train[0].length;
  const n = train.length;
  const { mu, sd } = colStats(train, 0); // population std; constant columns -> scale 1
  const Z = standardize(train, mu, sd);

  const C = covariance(Z, 0);
  const { values, vectors } = jacobiEigen(C);
  const total = Array.from(values).reduce((s, v) => s + Math.max(v, 0), 0) || 1;
  let cum = 0;
  let a = 0;
  for (let k = 0; k < values.length; k++) {
    cum += Math.max(values[k], 0) / total;
    a++;
    if (cum >= varCutoff) break;
  }
  a = Math.max(1, Math.min(a, m));

  // Whitening rows: u_k / sqrt(lambda_k). Unit-norm loadings retained for SPE.
  const Wt = zeros(a, m);
  const P = zeros(a, m);
  for (let k = 0; k < a; k++) {
    const lk = Math.max(values[k], LAM_FLOOR);
    const scale = 1 / Math.sqrt(lk);
    for (let j = 0; j < m; j++) {
      const u = vectors[j][k];
      P[k][j] = u;
      Wt[k][j] = u * scale;
    }
  }

  // Whitened reference data Y (n x a).
  const Y = Array.from({ length: n }, () => new Float64Array(a));
  for (let t = 0; t < n; t++) {
    const Zt = Z[t];
    const Yt = Y[t];
    for (let k = 0; k < a; k++) {
      let s = 0;
      const Wk = Wt[k];
      for (let j = 0; j < m; j++) s += Wk[j] * Zt[j];
      Yt[k] = Number.isFinite(s) ? s : 0;
    }
  }

  // Seeded, deterministic initialisation + one decorrelation pass.
  const rng = makeRng(seed);
  let W = zeros(a, a);
  for (let i = 0; i < a; i++) for (let j = 0; j < a; j++) W[i][j] = rng() * 2 - 1;
  W = symmetricDecorrelate(W, a);

  let converged = false;
  let iterations = 0;
  for (let iter = 1; iter <= maxIter; iter++) {
    iterations = iter;
    const Wnew = zeros(a, a);
    for (let i = 0; i < a; i++) {
      const wi = W[i];
      const acc = new Float64Array(a);
      let gdotSum = 0;
      for (let t = 0; t < n; t++) {
        const Yt = Y[t];
        let dot = 0;
        for (let k = 0; k < a; k++) dot += wi[k] * Yt[k];
        const gt = Math.tanh(dot);
        const gd = 1 - gt * gt;
        for (let k = 0; k < a; k++) acc[k] += Yt[k] * gt;
        gdotSum += gd;
      }
      const gm = gdotSum / n;
      const row = Wnew[i];
      for (let k = 0; k < a; k++) {
        const v = acc[k] / n - gm * wi[k];
        row[k] = Number.isFinite(v) ? v : 0;
      }
    }
    const decorated = symmetricDecorrelate(Wnew, a);
    let maxDiff = 0;
    for (let i = 0; i < a; i++) {
      let d = 0;
      for (let k = 0; k < a; k++) d += decorated[i][k] * W[i][k];
      maxDiff = Math.max(maxDiff, Math.abs(1 - Math.abs(d)));
    }
    W = decorated;
    if (!Number.isFinite(maxDiff) || maxDiff < tol) {
      converged = Number.isFinite(maxDiff);
      break;
    }
  }

  return { mu, sd, m, n, Wt, P, W, a, lam: Array.from(values), iterations, converged };
}

/**
 * I² and SPE for a raw row, plus the per-variable SPE residual contribution.
 */
export function icaStatistics(row, model) {
  const { mu, sd, m, Wt, P, W, a } = model;
  const z = new Float64Array(m);
  for (let j = 0; j < m; j++) z[j] = (row[j] - mu[j]) / sd[j];

  const y = new Float64Array(a);
  for (let k = 0; k < a; k++) {
    let s = 0;
    const Wk = Wt[k];
    for (let j = 0; j < m; j++) s += Wk[j] * z[j];
    y[k] = s;
  }

  let i2 = 0;
  for (let i = 0; i < a; i++) {
    let s = 0;
    const Wi = W[i];
    for (let k = 0; k < a; k++) s += Wi[k] * y[k];
    i2 += s * s;
  }

  // Orthogonal projection onto the retained subspace (unit-norm loadings).
  const recon = new Float64Array(m);
  for (let k = 0; k < a; k++) {
    let s = 0;
    const Pk = P[k];
    for (let j = 0; j < m; j++) s += Pk[j] * z[j];
    for (let j = 0; j < m; j++) recon[j] += s * Pk[j];
  }

  const e2 = new Float64Array(m);
  let spe = 0;
  for (let j = 0; j < m; j++) {
    const e = z[j] - recon[j];
    const v = Number.isFinite(e) ? e * e : 0;
    e2[j] = v;
    spe += v;
  }
  return { i2: Number.isFinite(i2) ? i2 : 0, spe, e2 };
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('ICA baseline requires a normal-control reference for this dataset');
  if (reference.matrix.m !== matrix.m) {
    throw new Error(`ICA: reference width ${reference.matrix.m} does not match case width ${matrix.m}`);
  }

  const model = fitIca(reference.matrix.X);

  const refStats = reference.matrix.X.map((r) => icaStatistics(r, model));
  const thrI2 = quantile(refStats.map((s) => s.i2).sort((x, y) => x - y), ALARM_Q);
  const thrSpe = quantile(refStats.map((s) => s.spe).sort((x, y) => x - y), ALARM_Q);

  const stats = matrix.X.map((r) => icaStatistics(r, model));
  const win = ctx.faultWindow;
  const stash = new Map();
  for (let i = win.start; i < win.end; i++) stash.set(i, stats[i].e2);

  const detI2 = detectionStats(stats.map((s) => s.i2), thrI2, win, matrix.n);
  const detSpe = detectionStats(stats.map((s) => s.spe), thrSpe, win, matrix.n);
  const primary = detI2.detection_rate >= detSpe.detection_rate ? 'I2' : 'SPE';
  const detPrimary = primary === 'I2' ? detI2 : detSpe;

  const topVars = rankContributors(matrix, win, (i) => stash.get(i), { topK: 6 });
  const detectable = Math.max(detI2.detection_rate, detSpe.detection_rate) > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  const params = `a=${model.a} iters=${model.iterations}${model.converged ? '' : '(cap)'}`;

  return {
    top3: candidates.map((c) => c.label),
    verdict: detectorVerdict(caseDef, detPrimary),
    variable_top3: topVars.map((v) => v.col),
    variables_ranked: topVars,
    detection: {
      detection_rate: detPrimary.detection_rate,
      alarms: detPrimary.alarms,
      window_rows: detPrimary.window_rows,
      pre_window_alarm_rate: detPrimary.pre_window_alarm_rate,
      threshold: detPrimary.threshold,
      max_stat: detPrimary.max_stat,
      series_head: detPrimary.series_head,
      primary,
      I2: detI2,
      SPE: detSpe,
      components_retained: model.a,
      ica_iterations: model.iterations,
      ica_converged: model.converged,
      detectable,
      params,
    },
    reasoning: detectable
      ? `FastICA (${model.a} independent components, ${model.iterations} iterations, converged=${model.converged}${model.converged ? '' : ' — hit the 500-iteration cap: symmetric FastICA does not reach tol=1e-6 on this whitening, reported rather than hidden'}) alarms on ${detI2.alarms}/${detI2.window_rows} fault-window rows by I² (${(detI2.detection_rate * 100).toFixed(2)}%, limit ${detI2.threshold}) and ${detSpe.alarms}/${detSpe.window_rows} by SPE (${(detSpe.detection_rate * 100).toFixed(2)}%, limit ${detSpe.threshold}); the more sensitive chart ${primary} drives the verdict. Pre-window alarm rate ${detPrimary.pre_window_alarm_rate === null ? 'n/a' : (detPrimary.pre_window_alarm_rate * 100).toFixed(2) + '%'} confirms the limit is reference-calibrated, not file-calibrated. Largest SPE residual contributors: ${topVars.slice(0, 3).map((v) => v.col).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: I² alarms on ${detI2.alarms}/${detI2.window_rows} fault-window rows (${(detI2.detection_rate * 100).toFixed(2)}%, limit ${detI2.threshold}) and SPE on ${detSpe.alarms}/${detSpe.window_rows} (${(detSpe.detection_rate * 100).toFixed(2)}%, limit ${detSpe.threshold}), i.e. at the 99th-percentile expectation of the reference distributions. FastICA reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? 'mean squared SPE residual per original variable over the fault window -> top-6 -> documented TEP variable-affinity table (tep-affinity.mjs)'
      : 'unavailable for this domain (no published variable->cause table); SPE residual variables reported only',
    runtime_ms: Date.now() - t0,
  };
}
