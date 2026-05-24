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
  groupValues = [...new Set(rows.map(r => String(r[groupCol] || '')))].filter(v => v);
  if (groupValues.length >= 2) {
    const groupColData = rows.map(r => String(r[groupCol] || ''));
    stratifiedResults = stratifiedAnalysis(colData, effectiveTargets, groupColData, groupValues);
  }
}

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
  target_analysis: targetAnalysis,
  multiple_testing: multiTestReport,
  stratified_analysis: stratifiedResults
};

console.log(JSON.stringify(result, null, 2));
