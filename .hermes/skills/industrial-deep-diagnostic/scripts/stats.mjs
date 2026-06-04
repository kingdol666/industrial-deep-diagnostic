#!/usr/bin/env node
// stats.mjs — Advanced statistical analysis engine
// Computes: Pearson, Spearman, detrended correlations, stratified analysis,
//           full lag CCF, multiple testing correction, sorting validation.
// Usage: node stats.mjs <data.json> [--time-col X] [--target-cols A,B,C]
//        [--max-lag N] [--group-col G] [--alpha 0.05]

import fs from 'fs';

// ═══════════════════════════════════════════════
//  DATA LOADING
// ═══════════════════════════════════════════════

function loadData(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  const parsed = JSON.parse(raw);
  if (Array.isArray(parsed)) return { data: parsed, note: null };
  if (parsed.column_details) {
    const previewRows = (parsed.preview || []).length;
    return {
      data: parsed.preview || [],
      note: `WARNING: Input is inspect.mjs output with only ${previewRows} preview rows. Use 'node convert.mjs <file.csv> --output data.json' first.`
    };
  }
  if (parsed.data && Array.isArray(parsed.data)) return { data: parsed.data, note: null };
  return { data: [parsed], note: null };
}

// ═══════════════════════════════════════════════
//  RANKING UTILITY
// ═══════════════════════════════════════════════

function rankArray(arr) {
  // Returns ranks (1-based) with average ranks for ties
  const sorted = arr.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
  const ranks = new Array(arr.length);
  let i = 0;
  while (i < sorted.length) {
    let j = i;
    while (j < sorted.length && sorted[j].v === sorted[i].v) j++;
    const avgRank = (i + j + 2) / 2; // 1-based average
    for (let k = i; k < j; k++) {
      ranks[sorted[k].i] = avgRank;
    }
    i = j;
  }
  return ranks;
}

// ═══════════════════════════════════════════════
//  CORRELATION FUNCTIONS
// ═══════════════════════════════════════════════

function pearson(x, y) {
  const n = Math.min(x.length, y.length);
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0, count = 0;
  for (let i = 0; i < n; i++) {
    if (x[i] == null || y[i] == null || isNaN(x[i]) || isNaN(y[i])) continue;
    sumX += x[i]; sumY += y[i]; sumXY += x[i] * y[i];
    sumX2 += x[i] * x[i]; sumY2 += y[i] * y[i]; count++;
  }
  if (count < 3) return { r: 0, n: count };
  const num = count * sumXY - sumX * sumY;
  const den = Math.sqrt((count * sumX2 - sumX * sumX) * (count * sumY2 - sumY * sumY));
  const r = den === 0 ? 0 : num / den;
  // Two-tailed p-value via t-distribution approximation
  const t = r * Math.sqrt((count - 2) / (1 - r * r + 1e-12));
  const p = tDist2Tailed(Math.abs(t), count - 2);
  return { r: +r.toFixed(4), n: count, p: +p.toFixed(4) };
}

function spearman(x, y) {
  // Remove null/NaN pairs
  const validX = [], validY = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null && !isNaN(x[i]) && !isNaN(y[i])) {
      validX.push(x[i]); validY.push(y[i]);
    }
  }
  if (validX.length < 3) return { r: 0, n: validX.length };
  const rankX = rankArray(validX);
  const rankY = rankArray(validY);
  return pearson(rankX, rankY);
}

// ═══════════════════════════════════════════════
//  T-DISTRIBUTION (for p-values, no external deps)
// ═══════════════════════════════════════════════

function tDist2Tailed(t, df) {
  // Regularized incomplete beta for t-distribution CDF
  // Uses series expansion for accuracy
  if (df <= 0) return 1;
  const x = df / (df + t * t);
  const p1 = regularizedBeta(x, df / 2, 0.5);
  return Math.min(1, p1);
}

function regularizedBeta(x, a, b) {
  // Continued fraction representation for regularized incomplete beta
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  return betaCf(x, a, b);
}

function betaCf(x, a, b) {
  const maxIter = 200;
  const epsilon = 1e-10;
  const qab = a + b;
  const qap = a + 1;
  const qam = a - 1;
  let c = 1;
  let d = 1 - qab * x / qap;
  if (Math.abs(d) < 1e-30) d = 1e-30;
  d = 1 / d;
  let h = d;

  for (let m = 1; m <= maxIter; m++) {
    const m2 = 2 * m;
    let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < 1e-30) d = 1e-30;
    c = 1 + aa / c;
    if (Math.abs(c) < 1e-30) c = 1e-30;
    d = 1 / d;
    h *= d * c;
    aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < 1e-30) d = 1e-30;
    c = 1 + aa / c;
    if (Math.abs(c) < 1e-30) c = 1e-30;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < epsilon) break;
  }

  return Math.exp(a * Math.log(x) + b * Math.log(1 - x) + lnGamma(a + b) - lnGamma(a) - lnGamma(b)) * h / a;
}

function lnGamma(z) {
  // Lanczos approximation
  if (z < 0.5) {
    return Math.log(Math.PI / Math.sin(Math.PI * z)) - lnGamma(1 - z);
  }
  z -= 1;
  const g = 7;
  const c = [
    0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7
  ];
  let x = c[0];
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i);
  const t = z + g + 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}

// ═══════════════════════════════════════════════
//  LINEAR DETRENDING
// ═══════════════════════════════════════════════

function linearDetrend(arr) {
  const n = arr.length;
  const valid = [];
  for (let i = 0; i < n; i++) {
    if (arr[i] != null && !isNaN(arr[i])) valid.push({ i, v: arr[i] });
  }
  if (valid.length < 3) return arr.slice();

  // Simple linear regression: y = a + b*x
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  for (const pt of valid) {
    sumX += pt.i; sumY += pt.v;
    sumXY += pt.i * pt.v; sumX2 += pt.i * pt.i;
  }
  const m = valid.length;
  const slope = (m * sumXY - sumX * sumY) / (m * sumX2 - sumX * sumX + 1e-12);
  const intercept = (sumY - slope * sumX) / m;

  const detrended = arr.slice();
  for (let i = 0; i < n; i++) {
    if (arr[i] != null && !isNaN(arr[i])) {
      detrended[i] = arr[i] - (slope * i + intercept);
    }
  }
  return detrended;
}

function detrendedCorrelation(x, y) {
  const xDetrended = linearDetrend(x);
  const yDetrended = linearDetrend(y);
  const raw = pearson(x, y);
  const detrended = pearson(xDetrended, yDetrended);
  const attenuation = raw.r !== 0 ? (raw.r - detrended.r) / Math.abs(raw.r) : 0;
  return {
    raw_r: raw.r,
    raw_p: raw.p,
    detrended_r: detrended.r,
    detrended_p: detrended.p,
    attenuation_pct: +(attenuation * 100).toFixed(1),
    trend_confounded: Math.abs(attenuation) > 0.5,
    n: raw.n
  };
}

// ═══════════════════════════════════════════════
//  FULL LAG CROSS-CORRELATION FUNCTION
// ═══════════════════════════════════════════════

function fullLagCCF(x, y, maxLag) {
  // Returns ALL lags, not just best. Enables lag window consistency check.
  const ccf = [];
  for (let lag = -maxLag; lag <= maxLag; lag++) {
    const xSlice = [], ySlice = [];
    for (let i = 0; i < x.length; i++) {
      const yi = i + lag;
      if (yi < 0 || yi >= y.length) continue;
      if (x[i] != null && y[yi] != null && !isNaN(x[i]) && !isNaN(y[yi])) {
        xSlice.push(x[i]); ySlice.push(y[yi]);
      }
    }
    const { r, n } = pearson(xSlice, ySlice);
    ccf.push({ lag, r, n });
  }
  return ccf;
}

function findBestLag(ccf) {
  let best = ccf[0];
  for (const entry of ccf) {
    if (Math.abs(entry.r) > Math.abs(best.r)) best = entry;
  }
  return best;
}

function lagWindowConsistency(ccf, bestLag, windowSize = 3) {
  // Check if adjacent lags show consistent correlation pattern (not an isolated spike)
  const center = bestLag + maxLag; // convert to array index in CCF (offset by maxLag)
  const result = { best_lag: bestLag, best_r: ccf[center]?.r || 0, adjacent_r: [], consistent: true };

  for (let d = -windowSize; d <= windowSize; d++) {
    if (d === 0) continue;
    const idx = center + d;
    if (idx >= 0 && idx < ccf.length) {
      result.adjacent_r.push({ lag: ccf[idx].lag, r: ccf[idx].r });
    }
  }

  // Signal is consistent if at least 2 adjacent lags have |r| > 0.3 * |best_r|
  // AND the sign is the same
  const bestSign = result.best_r > 0 ? 1 : -1;
  let consistentCount = 0;
  for (const adj of result.adjacent_r) {
    const adjSign = adj.r > 0 ? 1 : -1;
    if (adjSign === bestSign && Math.abs(adj.r) > 0.3 * Math.abs(result.best_r)) {
      consistentCount++;
    }
  }
  result.consistent = consistentCount >= 2;
  result.isolated_spike = !result.consistent && Math.abs(result.best_r) > 0.5;
  result.consistent_count = consistentCount;

  return result;
}

// ═══════════════════════════════════════════════
//  STRATIFIED ANALYSIS (Simpson's Paradox Detection)
// ═══════════════════════════════════════════════

function stratifiedAnalysis(colData, targetCols, groupColData, groupValues) {
  // For each target-defect relationship, compute corr within each group
  // and detect Simpson's Paradox (direction reversal or dramatic attenuation)
  const results = [];

  for (const target of targetCols) {
    if (!colData[target]) continue;

    for (const [paramName, paramValues] of Object.entries(colData)) {
      if (paramName === target) continue;

      // Full dataset correlation
      const fullCorr = pearson(colData[target], paramValues);

      // Stratified correlations
      const strata = {};
      let reversalDetected = false;
      let maxAttenuation = 0;

      for (const gVal of groupValues) {
        const indices = [];
        for (let i = 0; i < groupColData.length; i++) {
          if (String(groupColData[i]) === String(gVal)) indices.push(i);
        }
        if (indices.length < 10) continue; // skip tiny subgroups

        const xSub = indices.map(i => colData[target][i]);
        const ySub = indices.map(i => paramValues[i]);
        const subCorr = pearson(xSub, ySub);

        strata[gVal] = { r: subCorr.r, p: subCorr.p, n: indices.length };

        // Check direction reversal
        if (fullCorr.r !== 0 && subCorr.r !== 0 && (fullCorr.r > 0) !== (subCorr.r > 0)) {
          reversalDetected = true;
        }

        // Check attenuation
        const att = fullCorr.r !== 0 ? Math.abs((fullCorr.r - subCorr.r) / fullCorr.r) : 0;
        if (att > maxAttenuation) maxAttenuation = att;
      }

      if (Object.keys(strata).length > 0) {
        results.push({
          target: target,
          parameter: paramName,
          full_r: fullCorr.r,
          full_p: fullCorr.p,
          strata: strata,
          simpson_paradox: reversalDetected,
          max_attenuation_pct: +(maxAttenuation * 100).toFixed(1),
          severity: reversalDetected ? 'CRITICAL' :
                    maxAttenuation > 0.5 ? 'SERIOUS' :
                    maxAttenuation > 0.3 ? 'MODERATE' : 'MILD'
        });
      }
    }
  }

  // Sort by severity
  const severityOrder = { 'CRITICAL': 0, 'SERIOUS': 1, 'MODERATE': 2, 'MILD': 3 };
  results.sort((a, b) => (severityOrder[a.severity] || 4) - (severityOrder[b.severity] || 4));

  return results;
}

// ═══════════════════════════════════════════════
//  DATA SORTING VALIDATION
// ═══════════════════════════════════════════════

function validateTimeSorting(rows, timeCol) {
  if (!timeCol || rows.length < 2) return { time_sorted: null, warning: 'no time column or insufficient rows' };

  const times = rows.map(r => {
    const v = r[timeCol];
    if (v == null) return null;
    const d = new Date(v);
    return isNaN(d.getTime()) ? null : d.getTime();
  });

  let increasing = 0, decreasing = 0;
  for (let i = 1; i < times.length; i++) {
    if (times[i] == null || times[i - 1] == null) continue;
    if (times[i] > times[i - 1]) increasing++;
    else if (times[i] < times[i - 1]) decreasing++;
  }

  const total = increasing + decreasing;
  const isTimeSorted = total > 0 && increasing / total > 0.95;

  return {
    time_sorted: isTimeSorted,
    increasing_pct: total > 0 ? +((increasing / total) * 100).toFixed(1) : 0,
    decreasing_pct: total > 0 ? +((decreasing / total) * 100).toFixed(1) : 0,
    total_comparisons: total,
    warning: isTimeSorted ? null :
      'CRITICAL: Data is NOT sorted by time column. All lag analysis results are UNRELIABLE and likely represent row-ordering artifacts rather than true temporal relationships. Re-sort data by time column before lag analysis.'
  };
}

// ═══════════════════════════════════════════════
//  MULTIPLE TESTING CORRECTION
// ═══════════════════════════════════════════════

function bonferroniThreshold(alpha, nComparisons) {
  return alpha / nComparisons;
}

function multipleTestingReport(correlations, targetCols, alpha = 0.05) {
  const allCorrs = [];
  for (const target of targetCols) {
    if (!correlations[target]) continue;
    for (const [param, result] of Object.entries(correlations[target])) {
      allCorrs.push({ target, param, r: result.r, p: result.p, n: result.n });
    }
  }

  const nTests = allCorrs.length;
  const bonfThreshold = bonferroniThreshold(alpha, nTests);
  let significantCount = 0;
  let bonfSignificantCount = 0;

  for (const c of allCorrs) {
    if (c.p < alpha) significantCount++;
    if (c.p < bonfThreshold) bonfSignificantCount++;
  }

  const expectedFalsePositives = nTests * alpha;

  return {
    total_tests: nTests,
    alpha: alpha,
    bonferroni_threshold: +bonfThreshold.toFixed(6),
    nominally_significant_p0_05: significantCount,
    bonferroni_significant: bonfSignificantCount,
    expected_false_positives: +expectedFalsePositives.toFixed(1),
    warning: significantCount < expectedFalsePositives * 2 ?
      'WARNING: Few significant results relative to expected false positives. Most "significant" correlations may be spurious.' :
      null
  };
}

// ═══════════════════════════════════════════════
//  MUTUAL INFORMATION (k-NN estimator, no external deps)
// ═══════════════════════════════════════════════

function mutualInformation(x, y, k = 3) {
  // k-nearest neighbor estimator of mutual information
  // Uses Kraskov estimator: I(X;Y) ≈ ψ(k) - ⟨ψ(n_x+1)⟩ - ⟨ψ(n_y+1)⟩ + ψ(N)
  // where ψ is the digamma function
  const valid = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null && !isNaN(x[i]) && !isNaN(y[i])) {
      valid.push({ xi: x[i], yi: y[i] });
    }
  }
  const n = valid.length;
  if (n < k + 2) return { mi: 0, n, warning: 'insufficient data' };

  // Normalize to [0,1] for distance computation
  const xs = valid.map(v => v.xi);
  const ys = valid.map(v => v.yi);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;

  const points = valid.map(v => ({
    xn: (v.xi - xMin) / xRange,
    yn: (v.yi - yMin) / yRange
  }));

  // Compute distances and k-th nearest neighbor distances
  let sumDigammaNx = 0, sumDigammaNy = 0;
  const digammaN = digamma(n);

  for (let i = 0; i < n; i++) {
    const dists = [];
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      const dx = points[i].xn - points[j].xn;
      const dy = points[i].yn - points[j].yn;
      dists.push({ dx: Math.abs(dx), dy: Math.abs(dy), dist: Math.max(Math.abs(dx), Math.abs(dy)) });
    }
    // Sort by Chebyshev (max) distance
    dists.sort((a, b) => a.dist - b.dist);
    const eps = dists[k - 1].dist;

    // Count points with |x - xi| < eps and |y - yi| < eps
    let nx = 0, ny = 0;
    for (const d of dists) {
      if (d.dx < eps) nx++;
      if (d.dy < eps) ny++;
    }
    sumDigammaNx += digamma(nx + 1);
    sumDigammaNy += digamma(ny + 1);
  }

  const mi = Math.max(0, digammaN + digamma(k) - sumDigammaNx / n - sumDigammaNy / n);

  // Normalize by entropy estimate: MI_norm ≈ MI / max(Hx, Hy)
  // Use a simple normalization: MI / (0.5 * log2(N)) as a rough upper bound
  const maxMi = 0.5 * Math.log2(n);
  const miNormalized = maxMi > 0 ? Math.min(1, mi / maxMi) : 0;

  return { mi: +mi.toFixed(4), mi_normalized: +miNormalized.toFixed(4), n, k };
}

function digamma(x) {
  // Digamma function ψ(x) = Γ'(x)/Γ(x)
  // Asymptotic expansion for large x
  if (x < 6) {
    return digamma(x + 1) - 1 / x;
  }
  const invX = 1 / x;
  const invX2 = invX * invX;
  const invX4 = invX2 * invX2;
  const invX6 = invX4 * invX2;
  return Math.log(x) - 0.5 * invX - (1/12) * invX2 + (1/120) * invX4 - (1/252) * invX6;
}

// ═══════════════════════════════════════════════
//  GRANGER CAUSALITY TEST
// ═══════════════════════════════════════════════

function grangerCausality(x, y, maxLag = 5) {
  // Tests whether past values of X help predict Y beyond past values of Y alone
  // H0: X does NOT Granger-cause Y
  // Uses F-test on restricted (Y lags only) vs unrestricted (Y + X lags) models

  const valid = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null && !isNaN(x[i]) && !isNaN(y[i])) {
      valid.push({ xi: x[i], yi: y[i] });
    }
  }
  const n = valid.length;
  if (n < maxLag + 10) return { f_stat: 0, p_value: 1, significant: false, warning: 'insufficient data' };

  // Build lag matrix for each candidate lag count
  const results = [];
  for (let lag = 1; lag <= maxLag; lag++) {
    const T = n - lag;
    if (T < 10) continue;

    // Build Y vector (dependent variable)
    const Y = [];
    for (let t = lag; t < n; t++) {
      Y.push(valid[t].yi);
    }

    // Restricted model: Y_t = α + Σ β_i Y_{t-i} + ε_t
    const X_restricted = [];
    for (let t = lag; t < n; t++) {
      const row = [1]; // intercept
      for (let i = 1; i <= lag; i++) {
        row.push(valid[t - i].yi);
      }
      X_restricted.push(row);
    }

    // Unrestricted model: Y_t = α + Σ β_i Y_{t-i} + Σ γ_i X_{t-i} + ε_t
    const X_unrestricted = [];
    for (let t = lag; t < n; t++) {
      const row = [1]; // intercept
      for (let i = 1; i <= lag; i++) {
        row.push(valid[t - i].yi);
      }
      for (let i = 1; i <= lag; i++) {
        row.push(valid[t - i].xi);
      }
      X_unrestricted.push(row);
    }

    // OLS: β = (X'X)^-1 X'Y
    const ssrRestricted = olsSSR(Y, X_restricted);
    const ssrUnrestricted = olsSSR(Y, X_unrestricted);

    const pRestricted = lag + 1; // intercept + lag Y terms
    const pUnrestricted = 2 * lag + 1; // intercept + lag Y + lag X terms
    const dfNum = pUnrestricted - pRestricted; // number of X lag terms
    const dfDen = T - pUnrestricted;

    if (dfDen <= 0 || ssrUnrestricted < 0 || ssrRestricted < 0) continue;

    const fStat = ((ssrRestricted - ssrUnrestricted) / dfNum) / (ssrUnrestricted / dfDen);
    const pValue = fTestPValue(Math.max(0, fStat), dfNum, dfDen);

    results.push({
      lag,
      f_stat: +fStat.toFixed(4),
      p_value: +pValue.toFixed(4),
      significant: pValue < 0.05,
      ssr_restricted: +ssrRestricted.toFixed(4),
      ssr_unrestricted: +ssrUnrestricted.toFixed(4)
    });
  }

  // Find best lag (lowest p-value)
  let best = results[0] || null;
  for (const r of results) {
    if (r.p_value < (best?.p_value || 1)) best = r;
  }

  return {
    best_lag: best?.lag || 0,
    best_f_stat: best?.f_stat || 0,
    best_p_value: best?.p_value || 1,
    significant: best?.significant || false,
    all_lags: results,
    direction: best?.significant ? 'X → Y (Granger-causes)' : 'no evidence of Granger causality',
    warning: null
  };
}

function olsSSR(y, X) {
  // Ordinary Least Squares: compute sum of squared residuals
  const n = X.length;
  const p = X[0].length;
  if (n <= p) return -1;

  // Solve normal equations: (X'X) β = X'y
  // Use Gaussian elimination on augmented matrix

  // Build X'X and X'y
  const XtX = new Array(p).fill(0).map(() => new Array(p).fill(0));
  const Xty = new Array(p).fill(0);

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < p; j++) {
      Xty[j] += X[i][j] * y[i];
      for (let k = 0; k < p; k++) {
        XtX[j][k] += X[i][j] * X[i][k];
      }
    }
  }

  // Gaussian elimination with partial pivoting
  const aug = new Array(p).fill(0).map((_, i) => [...XtX[i], Xty[i]]);

  for (let col = 0; col < p; col++) {
    // Find pivot
    let maxRow = col;
    for (let row = col + 1; row < p; row++) {
      if (Math.abs(aug[row][col]) > Math.abs(aug[maxRow][col])) maxRow = row;
    }
    [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]];

    if (Math.abs(aug[col][col]) < 1e-12) continue;

    for (let row = col + 1; row < p; row++) {
      const factor = aug[row][col] / aug[col][col];
      for (let j = col; j <= p; j++) {
        aug[row][j] -= factor * aug[col][j];
      }
    }
  }

  // Back substitution
  const beta = new Array(p).fill(0);
  for (let i = p - 1; i >= 0; i--) {
    let sum = aug[i][p];
    for (let j = i + 1; j < p; j++) {
      sum -= aug[i][j] * beta[j];
    }
    beta[i] = Math.abs(aug[i][i]) < 1e-12 ? 0 : sum / aug[i][i];
  }

  // Compute SSR
  let ssr = 0;
  for (let i = 0; i < n; i++) {
    let pred = 0;
    for (let j = 0; j < p; j++) {
      pred += X[i][j] * beta[j];
    }
    ssr += (y[i] - pred) * (y[i] - pred);
  }

  return ssr;
}

function fTestPValue(f, df1, df2) {
  // F-test p-value via regularized incomplete beta
  if (f <= 0) return 1;
  const x = df2 / (df2 + df1 * f);
  return regularizedBeta(x, df2 / 2, df1 / 2);
}

// ═══════════════════════════════════════════════
//  INTERACTION EFFECT ANALYSIS
// ═══════════════════════════════════════════════

function interactionAnalysis(colData, targetCols, numericCols) {
  // For parameter pairs with weak individual correlations but potential synergy:
  // compute interaction term X1 × X2 and test against target
  const results = [];

  for (const target of targetCols) {
    if (!colData[target]) continue;
    const y = colData[target];

    // Get individual correlations first
    const individualR = {};
    for (const col of numericCols) {
      if (col === target) continue;
      const { r } = pearson(y, colData[col]);
      individualR[col] = r;
    }

    // Find pairs where both have weak individual correlations (|r| < 0.3)
    // but whose product may have stronger correlation (synergy detection)
    const candidateParams = numericCols.filter(c => c !== target && Math.abs(individualR[c]) < 0.3);

    // Limit candidates to avoid combinatorial explosion
    const topN = Math.min(candidateParams.length, 15);
    const sorted = candidateParams.sort((a, b) => Math.abs(individualR[b]) - Math.abs(individualR[a]));
    const candidates = sorted.slice(0, topN);

    for (let i = 0; i < candidates.length; i++) {
      for (let j = i + 1; j < candidates.length; j++) {
        const c1 = candidates[i], c2 = candidates[j];
        const x1 = colData[c1], x2 = colData[c2];

        // Compute interaction term
        const interaction = [];
        let validCount = 0;
        for (let k = 0; k < y.length; k++) {
          if (x1[k] != null && x2[k] != null && y[k] != null &&
              !isNaN(x1[k]) && !isNaN(x2[k]) && !isNaN(y[k])) {
            interaction.push(x1[k] * x2[k]);
            validCount++;
          } else {
            interaction.push(null);
          }
        }

        if (validCount < 20) continue;

        const { r: rInteraction, p: pInteraction } = pearson(y, interaction);
        const r1 = individualR[c1], r2 = individualR[c2];

        // Detect synergy: interaction r is substantially stronger than both individual r's
        const synergyGain = Math.abs(rInteraction) - Math.max(Math.abs(r1), Math.abs(r2));
        const isSynergistic = synergyGain > 0.2 && Math.abs(rInteraction) > 0.4;

        if (isSynergistic || Math.abs(rInteraction) > 0.3) {
          results.push({
            target,
            param_1: c1, param_2: c2,
            r_p1: +r1.toFixed(4), r_p2: +r2.toFixed(4),
            r_interaction: +rInteraction.toFixed(4),
            p_interaction: +pInteraction.toFixed(4),
            synergy_gain: +synergyGain.toFixed(4),
            synergistic: isSynergistic,
            interpretation: isSynergistic ?
              `${c1} and ${c2} individually have weak effects, but their interaction shows a strong relationship with ${target}. This suggests a synergistic failure mode where both conditions must co-occur.` :
              `Interaction effect detected but not definitively synergistic.`
          });
        }
      }
    }
  }

  // Sort by synergy gain descending
  results.sort((a, b) => b.synergy_gain - a.synergy_gain);
  return results;
}

// ═══════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════

const args = process.argv.slice(2);
const filePath = args[0];
if (!filePath) {
  console.error('Usage: node stats.mjs <data.json> [--time-col X] [--target-cols A,B,C] [--max-lag N] [--group-col G] [--alpha 0.05]');
  process.exit(1);
}

const { data: rows, note } = loadData(filePath);
if (note) console.error(note);
if (!Array.isArray(rows) || rows.length === 0) {
  console.error('Expected JSON array of objects.');
  process.exit(1);
}

const timeCol = (args[args.indexOf('--time-col') + 1]) || null;
const targetColsStr = (args[args.indexOf('--target-cols') + 1]) || '';
const targetCols = targetColsStr ? targetColsStr.split(',').map(s => s.trim()) : [];
const maxLag = parseInt(args[args.indexOf('--max-lag') + 1]) || 20;
const groupCol = (args[args.indexOf('--group-col') + 1]) || null;
const alpha = parseFloat(args[args.indexOf('--alpha') + 1]) || 0.05;

// Validate time sorting (critical for lag analysis)
const sortingValidation = validateTimeSorting(rows, timeCol);

// Get all numeric columns
const numericCols = [];
for (const key of Object.keys(rows[0])) {
  if (key === timeCol) continue;
  const vals = rows.map(r => Number(r[key])).filter(v => !isNaN(v));
  if (vals.length > rows.length * 0.5) numericCols.push(key);
}

// Extract numeric arrays
const colData = {};
for (const col of numericCols) {
  colData[col] = rows.map(r => { const v = Number(r[col]); return isNaN(v) ? null : v; });
}

// Pearson Correlation Matrix
const pearsonMatrix = {};
for (const c1 of numericCols) {
  pearsonMatrix[c1] = {};
  for (const c2 of numericCols) {
    pearsonMatrix[c1][c2] = pearson(colData[c1], colData[c2]).r;
  }
}

// Spearman Correlation Matrix
const spearmanMatrix = {};
for (const c1 of numericCols) {
  spearmanMatrix[c1] = {};
  for (const c2 of numericCols) {
    spearmanMatrix[c1][c2] = spearman(colData[c1], colData[c2]).r;
  }
}

// Per-target detailed analysis
const effectiveTargets = targetCols.length ? targetCols : numericCols.slice(0, 5);
const targetAnalysis = {};

for (const target of effectiveTargets) {
  if (!colData[target]) continue;
  const analysis = {
    pearson_correlations: {},
    spearman_correlations: {},
    detrended_correlations: {},
    lagged_ccf: {},
    best_lags: {},
    lag_window_consistency: {}
  };

  for (const col of numericCols) {
    if (col === target) continue;

    // Pearson
    analysis.pearson_correlations[col] = pearson(colData[target], colData[col]);

    // Spearman
    analysis.spearman_correlations[col] = spearman(colData[target], colData[col]);

    // Detrended
    analysis.detrended_correlations[col] = detrendedCorrelation(colData[target], colData[col]);

    // Full lag CCF
    const ccf = fullLagCCF(colData[target], colData[col], maxLag);
    analysis.lagged_ccf[col] = ccf;

    // Best lag
    const best = findBestLag(ccf);
    analysis.best_lags[col] = best;

    // Lag window consistency (only for non-zero best lags)
    if (best.lag !== 0 && Math.abs(best.r) > 0.3) {
      analysis.lag_window_consistency[col] = lagWindowConsistency(ccf, best.lag, maxLag);
    }
  }

  targetAnalysis[target] = analysis;
}

// Multiple testing report
const multiTestReport = multipleTestingReport(
  Object.fromEntries(effectiveTargets.map(t => [t, targetAnalysis[t]?.pearson_correlations || {}])),
  effectiveTargets, alpha
);

// Stratified analysis (if group column provided)
let stratifiedResults = null;
let groupValues = [];
if (groupCol) {
  groupValues = [...new Set(rows.map(r => String(r[groupCol] || '').trim()))].filter(v => v);
  if (groupValues.length >= 2) {
    const groupColData = rows.map(r => String(r[groupCol] || '').trim());
    stratifiedResults = stratifiedAnalysis(colData, effectiveTargets, groupColData, groupValues);
  }
}

// Mutual Information matrix (non-linear dependency)
const miMatrix = {};
if (numericCols.length <= 50) { // Skip for very wide datasets
  for (const c1 of numericCols) {
    miMatrix[c1] = {};
    for (const c2 of numericCols) {
      if (c1 === c2) {
        miMatrix[c1][c2] = { mi: 1.0, mi_normalized: 1.0 };
      } else if (c1 < c2) { // compute once, mirror
        const mi = mutualInformation(colData[c1], colData[c2]);
        miMatrix[c1][c2] = mi;
        if (!miMatrix[c2]) miMatrix[c2] = {};
        miMatrix[c2][c1] = mi;
      }
    }
  }
}

// Granger causality tests (only if time-sorted and time column exists)
let grangerResults = null;
if (sortingValidation.time_sorted && timeCol) {
  grangerResults = {};
  for (const target of effectiveTargets) {
    if (!colData[target]) continue;
    grangerResults[target] = {};
    for (const col of numericCols) {
      if (col === target) continue;
      const gc = grangerCausality(colData[col], colData[target], Math.min(maxLag, 5));
      grangerResults[target][col] = gc;
    }
  }
}

// Interaction effect analysis
const interactionResults = interactionAnalysis(colData, effectiveTargets, numericCols);

// Build output
const result = {
  data_summary: {
    total_rows: rows.length,
    numeric_columns: numericCols.length,
    target_columns: effectiveTargets,
    time_column: timeCol,
    group_column: groupCol,
    group_values: groupValues,
    max_lag: maxLag,
    alpha: alpha
  },
  sorting_validation: sortingValidation,
  correlation_matrices: {
    pearson: pearsonMatrix,
    spearman: spearmanMatrix
  },
  mutual_information: miMatrix,
  target_analysis: targetAnalysis,
  granger_causality: grangerResults,
  interaction_effects: interactionResults,
  multiple_testing: multiTestReport,
  stratified_analysis: stratifiedResults
};

console.log(JSON.stringify(result, null, 2));
