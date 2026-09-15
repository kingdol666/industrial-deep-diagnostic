// Kernel PCA process monitoring (RBF kernel, T² and SPE in feature space).
//
// Protocol (Schölkopf, Smola & Müller 1998 for KPCA itself; Lee, Yoo, Choi,
// Lee & Lee 2004 for the T²/SPE monitoring scheme):
//
//   reference = the normal-control scenario file of the SAME dataset
//   standardise with the REFERENCE mean/population-std (a kernel on raw units
//     would be dominated by whichever sensor has the largest engineering scale)
//   k(x,y)  = exp(-gamma * ||x-y||²)
//   K_c     = K - 1_n K - K 1_n + 1_n K 1_n          (feature-space centring)
//   eigen-decompose K_c with the library Jacobi routine
//   T²      = sum_{a kept} s_a² / lambda_a,  s_a = u_a · k̃(x)
//   SPE     = k̃(x,x) - sum_{a kept} s_a² / lambda_a, i.e. the squared
//             feature-space distance from Φ̃(x) to the retained subspace, with
//             k̃(x,x) = k(x,x) - (2/n) Σ_i k(x,x_i) + (1/n²) Σ_ij k(x_i,x_j).
//             T² + SPE = k̃(x,x) exactly (retained energy + residual energy).
//   limits  = 99th percentile of the REFERENCE T² and SPE distributions (never
//             the file under test); a row alarms when EITHER chart exceeds its
//             limit and both detection rates are reported separately.
//
// BANDWIDTH RULE (computed ONCE from the reference only, identical for every
// dataset and every case — never from the file under test):
//   (1) LOCAL-SCALE MEASURE. Build the training subsample, and for every
//       subsample row take the squared distance to its NEAREST neighbour
//       (leave-one-out). Let sigma2 = the MEDIAN of those nearest-neighbour
//       squared distances — a local scale, not the global median of all pairs
//       (the global median is ≈ 2m for standardised data and puts the kernel in
//       its saturated, non-discriminating regime). Set gamma = 1 / (2 sigma2).
//   (2) RESPONSIVENESS GUARD. If the resulting kernel is still degenerate —
//       mean OFF-DIAGONAL kernel entry >= OFFDIAG_MAX = 0.5, i.e. the Gram
//       matrix is nearly constant and hence nearly rank-1 — walk the fixed,
//       documented ladder gamma = c/m for c in GAMMA_LADDER = [1,2,4,...,128]
//       and take the FIRST rung whose off-diagonal mean drops below 0.5.
//   Both steps are global constants and global rules; nothing is chosen per
//   case, and only normal reference data ever enters them.
//
// COMPONENT RULE: Kaiser-style, retain components with lambda_a > mean(lambda)
//   = trace(K_c)/n. The previous 95%-of-mass rule kept ~85% of the spectrum
//   (216/256 components on TEP), which is dominated by numerical-noise
//   directions; the Kaiser rule keeps only directions that carry more variance
//   than an average direction. At least one component is always retained.
//
// COMPUTATIONAL CAP (uniform, not per-case tuning): the Jacobi eigendecomposition
// of K_c is O(n³) per sweep, so the kernel is trained on a systematic subsample
// of at most MAX_TRAIN = 256 reference rows (evenly spaced across the whole
// reference series so temporal coverage is preserved). The cap is identical for
// every dataset and every case; the 99th-percentile limits are still taken from
// the full reference T²/SPE distributions evaluated with that model.
//
// HONESTY CONTRACT: this module produces CONTRIBUTING VARIABLES, not mechanisms.
// The variable → root-cause step is the separate, documented mapping in
// ../tep-affinity.mjs and is reported in `diagnosis_step`.

import { jacobiEigen, quantile, colStats, standardize, mean } from '../linalg.mjs';
import { detectionStats, detectorVerdict, rankContributors } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'kpca-rbf',
  label: '核主成分分析监测 (RBF核 T²+SPE)',
  short: 'KPCA',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'RBF-kernel PCA with a local-scale bandwidth (gamma = 1/(2 x median nearest-neighbour squared distance) on the reference, plus a global c/m responsiveness ladder until the kernel off-diagonal mean < 0.5), Kaiser retention (lambda > mean lambda), feature-space centring, T² and SPE (subspace residual) with 99th-percentile reference limits and SPE-gradient contributions.',
  provenance: {
    basis: ['scholkopf1998kpca', 'lee2004kpca'],
    repo: null,
    note: 'Deterministic in-process reimplementation on the lab linalg primitives; kernel trained on a documented 256-row systematic subsample of the reference, with a global local-scale bandwidth rule (no per-case or per-dataset parameter choice).',
  },
};

export const ALARM_Q = 0.99;
export const MAX_TRAIN = 256;
export const OFFDIAG_MAX = 0.5;
export const GAMMA_LADDER = [1, 2, 4, 8, 16, 32, 64, 128];
const LAM_FLOOR = 1e-12;

/**
 * Deterministic systematic subsample: `cap` indices evenly spaced over [0, n-1].
 * No RNG — identical inputs always give identical indices.
 */
export function subsampleIndex(n, cap = MAX_TRAIN) {
  if (n <= cap) return Array.from({ length: n }, (_, i) => i);
  const idx = new Array(cap);
  for (let i = 0; i < cap; i++) idx[i] = Math.round((i * (n - 1)) / (cap - 1));
  return idx;
}

function rbfGram(train, gamma) {
  const n = train.length;
  const m = train[0].length;
  const K = Array.from({ length: n }, () => new Float64Array(n));
  let off = 0;
  for (let i = 0; i < n; i++) {
    K[i][i] = 1;
    for (let j = i + 1; j < n; j++) {
      let d = 0;
      const a = train[i];
      const b = train[j];
      for (let k = 0; k < m; k++) {
        const t = a[k] - b[k];
        d += t * t;
      }
      const v = Math.exp(-gamma * d);
      K[i][j] = v;
      K[j][i] = v;
      off += v;
    }
  }
  const pairs = (n * (n - 1)) / 2;
  return { K, offMean: pairs ? off / pairs : 0 };
}

/** Local-scale bandwidth + global responsiveness guard. Reference data only. */
export function selectGamma(train) {
  const n = train.length;
  const m = train[0].length;

  // (1) median leave-one-out nearest-neighbour squared distance
  const nn = new Float64Array(n).fill(Infinity);
  for (let i = 0; i < n; i++) {
    const a = train[i];
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      const b = train[j];
      let d = 0;
      for (let k = 0; k < m; k++) {
        const t = a[k] - b[k];
        d += t * t;
      }
      if (d < nn[i]) nn[i] = d;
    }
  }
  const finite = Array.from(nn).filter((v) => Number.isFinite(v));
  const sigma2 = finite.length ? quantile(finite.sort((x, y) => x - y), 0.5) : 0;
  let gamma = 1 / (2 * Math.max(sigma2, 1e-12));
  let rule = 'local-scale median nearest-neighbour (gamma = 1/(2 sigma2))';
  let offMean = rbfGram(train, gamma).offMean;

  // (2) responsiveness guard against a saturated (nearly rank-1) Gram matrix
  if (!(offMean < OFFDIAG_MAX)) {
    for (const c of GAMMA_LADDER) {
      const g = c / Math.max(1, m);
      const om = rbfGram(train, g).offMean;
      if (om < OFFDIAG_MAX) {
        gamma = g;
        rule = `responsiveness ladder gamma = ${c}/m (off-diagonal mean < ${OFFDIAG_MAX})`;
        offMean = om;
        break;
      }
      gamma = g;
      offMean = om;
    }
    if (!(offMean < OFFDIAG_MAX)) {
      rule = `responsiveness ladder exhausted at gamma = ${GAMMA_LADDER[GAMMA_LADDER.length - 1]}/m`;
    }
  }

  return { gamma, rule, sigma2, offMean };
}

/**
 * Fit KPCA on an already-standardised training matrix (array of rows).
 * Returns the centred-kernel model needed to score new standardised rows.
 */
export function fitKpca(train, { gamma = null, offdiagMax = OFFDIAG_MAX } = {}) {
  const n = train.length;
  const m = train[0].length;
  const selected = gamma === null ? selectGamma(train) : { gamma, rule: 'explicit gamma', sigma2: null, offMean: null };
  const g = selected.gamma;

  const { K, offMean: rawOffMean } = rbfGram(train, g);
  const offMean = selected.offMean === null ? rawOffMean : selected.offMean;

  // Feature-space centring: K_c = K - 1n K - K 1n + 1n K 1n.
  const rowMean = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = 0; j < n; j++) s += K[i][j];
    rowMean[i] = s / n;
  }
  let grand = 0;
  for (let i = 0; i < n; i++) grand += rowMean[i];
  grand /= n;

  const Kc = Array.from({ length: n }, () => new Float64Array(n));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) Kc[i][j] = K[i][j] - rowMean[i] - rowMean[j] + grand;
  }

  const { values, vectors } = jacobiEigen(Kc);
  const trace = mean(Array.from(values));

  // Kaiser-style retention: lambda > mean(lambda) = trace(K_c)/n.
  let a = 0;
  for (let k = 0; k < values.length; k++) {
    if (values[k] > trace && values[k] > 0) a++;
    else break;
  }
  a = Math.max(1, a);

  const alpha = [];
  const lam = [];
  for (let k = 0; k < a; k++) {
    alpha.push(Float64Array.from({ length: n }, (_, i) => vectors[i][k]));
    lam.push(values[k]);
  }

  return {
    n,
    m,
    gamma: g,
    gamma_rule: selected.rule,
    median_nn_sq_dist: selected.sigma2 === null ? null : Number(selected.sigma2.toFixed(6)),
    offdiag_mean: Number(offMean.toFixed(6)),
    train,
    rowMean,
    grand,
    alpha,
    lam,
    a,
    eigenvalue_trace_mean: Number(trace.toFixed(6)),
    retention_rule: 'lambda > mean(lambda) (Kaiser)',
  };
}

/** T², SPE and the centred kernel vector of one standardised row. */
export function kpcaRow(z, model) {
  const { n, m, gamma, train, rowMean, grand, alpha, lam } = model;
  const k = new Float64Array(n);
  let kMean = 0;
  for (let i = 0; i < n; i++) {
    const ti = train[i];
    let d = 0;
    for (let j = 0; j < m; j++) {
      const t = z[j] - ti[j];
      d += t * t;
    }
    const v = Math.exp(-gamma * d);
    k[i] = v;
    kMean += v;
  }
  kMean /= n;

  const kc = new Float64Array(n);
  for (let i = 0; i < n; i++) kc[i] = k[i] - rowMean[i] - kMean + grand;

  const A = alpha.length;
  const s = new Float64Array(A);
  for (let a = 0; a < A; a++) {
    const al = alpha[a];
    let acc = 0;
    for (let i = 0; i < n; i++) acc += al[i] * kc[i];
    s[a] = acc;
  }

  // T² = retained-subspace energy; SPE = k̃(x,x) - T² = residual energy.
  let t2 = 0;
  for (let a = 0; a < A; a++) t2 += (s[a] * s[a]) / Math.max(lam[a], LAM_FLOOR);
  const kxx = 1 - 2 * kMean + grand;
  const speRaw = kxx - t2;

  return {
    t2: Number.isFinite(t2) ? t2 : 0,
    spe: Number.isFinite(speRaw) ? Math.max(0, speRaw) : 0,
    k,
    s,
    kMean,
  };
}

/**
 * Per-variable contributions, analytic gradients of both charts times the
 * standardised deviation z_j (a first-order statistic change):
 *   dT²/dz_j  = Σ_a (2 s_a/lambda_a) ds_a/dz_j
 *   dSPE/dz_j = dk̃(x,x)/dz_j - dT²/dz_j        (since T² + SPE = k̃(x,x))
 * with ds_a/dz_j = Σ_i alpha_a[i] dk_i/dz_j - (Σ_i alpha_a[i]) mean_l(dk_l/dz_j)
 * and, for the RBF kernel, dk_i/dz_j = -2 gamma k_i (z_j - x_ij).
 */
export function kpcaContrib(z, model, row) {
  const { n, m, gamma, train, alpha, lam } = model;
  const k = row.k;
  const s = row.s;
  const A = alpha.length;

  const w = new Float64Array(n);
  for (let a = 0; a < A; a++) {
    const c = (2 * s[a]) / Math.max(lam[a], LAM_FLOOR);
    const al = alpha[a];
    for (let i = 0; i < n; i++) w[i] += c * al[i];
  }

  let B = 0, P = 0, S0 = 0;
  for (let i = 0; i < n; i++) {
    B += w[i];
    P += w[i] * k[i];
    S0 += k[i];
  }

  const QB = new Float64Array(m);
  const S1 = new Float64Array(m);
  for (let i = 0; i < n; i++) {
    const wk = w[i] * k[i];
    const ki = k[i];
    const ti = train[i];
    for (let j = 0; j < m; j++) {
      QB[j] += wk * ti[j];
      S1[j] += ki * ti[j];
    }
  }

  const t2 = new Float64Array(m);
  const spe = new Float64Array(m);
  for (let j = 0; j < m; j++) {
    const dT2 = -2 * gamma * (z[j] * (P - (B * S0) / n) - (QB[j] - (B * S1[j]) / n));
    const dKxx = ((4 * gamma) / n) * (z[j] * S0 - S1[j]);
    const dSpe = dKxx - dT2;
    const cT2 = dT2 * z[j];
    const cSpe = dSpe * z[j];
    t2[j] = Number.isFinite(cT2) ? Math.abs(cT2) : 0;
    spe[j] = Number.isFinite(cSpe) ? Math.abs(cSpe) : 0;
  }
  return { t2, spe };
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('KPCA baseline requires a normal-control reference for this dataset');
  if (reference.matrix.m !== matrix.m) {
    throw new Error(
      `KPCA: reference width ${reference.matrix.m} does not match case width ${matrix.m}`,
    );
  }

  // Reference-only standardisation (population std; zero-variance columns are
  // guarded to scale 1 by colStats, so constant sensors stay numerically inert).
  const { mu, sd } = colStats(reference.matrix.X, 0);
  const idx = subsampleIndex(reference.matrix.X.length, MAX_TRAIN);
  const train = standardize(idx.map((i) => reference.matrix.X[i]), mu, sd);
  const model = fitKpca(train);

  const refZ = standardize(reference.matrix.X, mu, sd);
  const refT2 = new Array(refZ.length);
  const refSpe = new Array(refZ.length);
  for (let i = 0; i < refZ.length; i++) {
    const r = kpcaRow(refZ[i], model);
    refT2[i] = r.t2;
    refSpe[i] = r.spe;
  }
  const thrT2 = quantile(refT2.slice().sort((x, y) => x - y), ALARM_Q);
  const thrSpe = quantile(refSpe.slice().sort((x, y) => x - y), ALARM_Q);

  const Z = standardize(matrix.X, mu, sd);
  const statT2 = new Array(matrix.n);
  const statSpe = new Array(matrix.n);
  const win = ctx.faultWindow;
  const stashT2 = new Map();
  const stashSpe = new Map();
  for (let i = 0; i < matrix.n; i++) {
    const r = kpcaRow(Z[i], model);
    statT2[i] = r.t2;
    statSpe[i] = r.spe;
    if (i >= win.start && i < win.end) {
      const c = kpcaContrib(Z[i], model, r);
      stashT2.set(i, c.t2);
      stashSpe.set(i, c.spe);
    }
  }

  const detT2 = detectionStats(statT2, thrT2, win, matrix.n);
  const detSpe = detectionStats(statSpe, thrSpe, win, matrix.n);
  const primary = detSpe.detection_rate >= detT2.detection_rate ? 'SPE' : 'T2';
  const detPrimary = primary === 'SPE' ? detSpe : detT2;

  // SPE is the sensitive chart; pca.mjs likewise ranks by the residual chart.
  let attribution = 'analytic SPE gradient |dSPE/dz_j * z_j|';
  let topVars = rankContributors(matrix, win, (i) => stashSpe.get(i), { topK: 6 });

  // SATURATION FALLBACK (structural, uniform, not per-case): if every reference
  // kernel value underflows to ~0 the point lies outside the kernel's support,
  // SPE collapses onto the saturation constant k̃(x,x) and its gradient is
  // identically zero — the statistic is locally flat, so it genuinely carries no
  // per-variable information. In that case rank by the standardized absolute
  // deviation from the reference mean and SAY SO, rather than emitting an
  // all-zero list tie-broken by column order.
  if (!topVars.length || topVars.every((v) => v.contribution === 0)) {
    attribution = 'standardized deviation |z_j| from the reference mean (kernel saturated: SPE gradient identically zero)';
    topVars = rankContributors(matrix, win, (i) => Z[i], { topK: 6 });
  }

  const topVarsT2 = rankContributors(matrix, win, (i) => stashT2.get(i), { topK: 6 });
  const detectable = Math.max(detT2.detection_rate, detSpe.detection_rate) > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  const params = `a=${model.a}/${model.n} gamma=${model.gamma.toFixed(5)} ntrain=${model.n}`;

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
      T2: detT2,
      SPE: detSpe,
      components_retained: model.a,
      retention_rule: model.retention_rule,
      training_rows: model.n,
      reference_rows: reference.matrix.X.length,
      gamma: Number(model.gamma.toFixed(8)),
      gamma_rule: model.gamma_rule,
      median_nn_sq_dist: model.median_nn_sq_dist,
      kernel_offdiag_mean: model.offdiag_mean,
      eigenvalue_mean: model.eigenvalue_trace_mean,
      contribution_rule: attribution,
      T2_contribution_variables: topVarsT2.map((v) => v.col),
      detectable,
      params,
    },
    reasoning: detectable
      ? `Feature-space monitoring with the RBF kernel (gamma=${model.gamma.toFixed(5)}, ${model.gamma_rule}) alarms on ${detSpe.alarms}/${detSpe.window_rows} fault-window rows by SPE (${(detSpe.detection_rate * 100).toFixed(2)}%, reference 99th-percentile limit ${detSpe.threshold}) and ${detT2.alarms}/${detT2.window_rows} by T² (${(detT2.detection_rate * 100).toFixed(2)}%, limit ${detT2.threshold}); the more sensitive chart ${primary} drives the verdict. Kaiser retention keeps ${model.a} of ${model.n} training components (eigenvalue mean ${model.eigenvalue_trace_mean}, kernel off-diagonal mean ${model.offdiag_mean}) on a ${model.n}-row systematic subsample of the ${reference.matrix.X.length}-row reference. Pre-window alarm rate ${detPrimary.pre_window_alarm_rate === null ? 'n/a' : (detPrimary.pre_window_alarm_rate * 100).toFixed(2) + '%'}. Variable attribution: ${attribution}. Top contributors: ${topVars.slice(0, 3).map((v) => v.col).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: SPE alarms on ${detSpe.alarms}/${detSpe.window_rows} fault-window rows (${(detSpe.detection_rate * 100).toFixed(2)}%, limit ${detSpe.threshold}) and T² on ${detT2.alarms}/${detT2.window_rows} (${(detT2.detection_rate * 100).toFixed(2)}%, limit ${detT2.threshold}), i.e. at the 99th-percentile expectation of the reference distributions (gamma=${model.gamma.toFixed(5)}, ${model.a} Kaiser-retained components). The kernel detector reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? `${attribution} averaged over the fault window -> top-6 -> documented TEP variable-affinity table (tep-affinity.mjs); kernel trained on a systematic ${MAX_TRAIN}-row (or fewer) subsample of the reference — a uniform tractability cap, not a per-case choice`
      : `unavailable for this domain (no published variable->cause table); ${attribution} reported as variables only`,
    runtime_ms: Date.now() - t0,
  };
}
