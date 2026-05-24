#!/usr/bin/env node
// stats_validate.mjs — Statistical Validation & Robustness Engine
// Runs AFTER stats.mjs. Produces a validation report that feeds directly
// into the Diagnostician and Judge agents.
//
// Detects: Simpson's Paradox, confounding, outlier sensitivity,
//          distribution issues, missing variable warnings.
//
// Usage: node stats_validate.mjs <stats_output.json> <data.json>
//        [--group-col G] [--time-col T] [--output validate_report.json]

import fs from 'fs';

// ═══════════════════════════════════════════
//  BASIC STATISTICS (self-contained, no deps)
// ═══════════════════════════════════════════

function pearsonSimple(x, y) {
  const n = Math.min(x.length, y.length);
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0, count = 0;
  for (let i = 0; i < n; i++) {
    if (x[i] == null || y[i] == null || isNaN(x[i]) || isNaN(y[i])) continue;
    sumX += x[i]; sumY += y[i]; sumXY += x[i] * y[i];
    sumX2 += x[i] * x[i]; sumY2 += y[i] * y[i]; count++;
  }
  if (count < 3) return 0;
  const num = count * sumXY - sumX * sumY;
  const den = Math.sqrt((count * sumX2 - sumX * sumX) * (count * sumY2 - sumY * sumY));
  return den === 0 ? 0 : num / den;
}

function median(arr) {
  const sorted = [...arr].filter(v => v != null && !isNaN(v)).sort((a, b) => a - b);
  if (sorted.length === 0) return NaN;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function iqr(arr) {
  const sorted = [...arr].filter(v => v != null && !isNaN(v)).sort((a, b) => a - b);
  if (sorted.length < 4) return { q1: sorted[0], q3: sorted[sorted.length - 1], iqr: sorted[sorted.length - 1] - sorted[0] };
  const q1Idx = Math.floor(sorted.length * 0.25);
  const q3Idx = Math.floor(sorted.length * 0.75);
  const q1 = sorted[q1Idx];
  const q3 = sorted[q3Idx];
  return { q1, q3, iqr: q3 - q1 };
}

function skewness(arr) {
  const valid = arr.filter(v => v != null && !isNaN(v));
  if (valid.length < 3) return 0;
  const n = valid.length;
  const mean = valid.reduce((a, b) => a + b, 0) / n;
  const variance = valid.reduce((s, v) => s + (v - mean) ** 2, 0) / n;
  const std = Math.sqrt(variance);
  if (std === 0) return 0;
  const m3 = valid.reduce((s, v) => s + ((v - mean) / std) ** 3, 0) / n;
  return m3;
}

// ═══════════════════════════════════════════
//  OUTLIER SENSITIVITY ANALYSIS
// ═══════════════════════════════════════════

function outlierSensitivity(x, y, method = 'iqr') {
  // Remove outliers using IQR method (1.5×IQR) and re-calculate correlation
  const validPairs = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null && !isNaN(x[i]) && !isNaN(y[i])) {
      validPairs.push({ x: x[i], y: y[i] });
    }
  }
  if (validPairs.length < 10) return null;

  const xVals = validPairs.map(p => p.x);
  const yVals = validPairs.map(p => p.y);

  let outlierMask;
  if (method === 'iqr') {
    const { q1: q1x, q3: q3x, iqr: iqrx } = iqr(xVals);
    const { q1: q1y, q3: q3y, iqr: iqry } = iqr(yVals);
    const lowX = q1x - 1.5 * iqrx, highX = q3x + 1.5 * iqrx;
    const lowY = q1y - 1.5 * iqry, highY = q3y + 1.5 * iqry;
    outlierMask = validPairs.map(p => p.x < lowX || p.x > highX || p.y < lowY || p.y > highY);
  } else {
    // top/bottom 5% trimming
    const n = validPairs.length;
    const trimN = Math.floor(n * 0.05);
    outlierMask = new Array(n).fill(false);
    // mark extremes in both x and y
    const sortedX = [...validPairs].map((p, i) => ({ v: p.x, i })).sort((a, b) => a.v - b.v);
    for (let i = 0; i < trimN; i++) outlierMask[sortedX[i].i] = true;
    for (let i = n - trimN; i < n; i++) outlierMask[sortedX[i].i] = true;
    const sortedY = [...validPairs].map((p, i) => ({ v: p.y, i })).sort((a, b) => a.v - b.v);
    for (let i = 0; i < trimN; i++) outlierMask[sortedY[i].i] = true;
    for (let i = n - trimN; i < n; i++) outlierMask[sortedY[i].i] = true;
  }

  const cleanX = [], cleanY = [];
  for (let i = 0; i < validPairs.length; i++) {
    if (!outlierMask[i]) {
      cleanX.push(validPairs[i].x);
      cleanY.push(validPairs[i].y);
    }
  }

  const fullR = pearsonSimple(xVals, yVals);
  const cleanR = pearsonSimple(cleanX, cleanY);
  const nRemoved = validPairs.length - cleanX.length;

  return {
    full_r: +fullR.toFixed(4),
    clean_r: +cleanR.toFixed(4),
    r_change: +(cleanR - fullR).toFixed(4),
    r_change_pct: fullR !== 0 ? +(((cleanR - fullR) / Math.abs(fullR)) * 100).toFixed(1) : 0,
    outliers_removed: nRemoved,
    outlier_pct: +((nRemoved / validPairs.length) * 100).toFixed(1),
    outlier_driven: Math.abs(cleanR - fullR) / (Math.abs(fullR) + 1e-12) > 0.5
  };
}

// ═══════════════════════════════════════════
//  DISTRIBUTION ANALYSIS
// ═══════════════════════════════════════════

function distributionCheck(colData) {
  const results = {};
  for (const [name, values] of Object.entries(colData)) {
    const valid = values.filter(v => v != null && !isNaN(v));
    if (valid.length < 3) continue;
    const sk = skewness(valid);
    const med = median(valid);
    const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
    const meanMedianRatio = med !== 0 ? mean / med : (mean === 0 ? 1 : Infinity);

    results[name] = {
      skewness: +sk.toFixed(3),
      mean_median_ratio: +meanMedianRatio.toFixed(3),
      is_heavily_skewed: Math.abs(sk) > 2 || meanMedianRatio > 3 || meanMedianRatio < 0.33,
      pearson_appropriate: Math.abs(sk) < 1.5 && meanMedianRatio > 0.5 && meanMedianRatio < 2,
      recommendation: Math.abs(sk) > 2 ?
        'SPEARMAN_RECOMMENDED: Heavy skew. Spearman correlation is more reliable than Pearson.' :
        Math.abs(sk) > 1 ?
        'MODERATE_SKEW: Consider Spearman as robustness check alongside Pearson.' :
        'NORMAL_ENOUGH: Pearson correlation is appropriate.'
    };
  }
  return results;
}

// ═══════════════════════════════════════════
//  CONFOUNDER PARTIAL CORRELATION
// ═══════════════════════════════════════════

function partialCorrelation(x, y, z) {
  // Partial correlation r_xy.z — controls for variable z
  const valid = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] != null && y[i] != null && z[i] != null && !isNaN(x[i]) && !isNaN(y[i]) && !isNaN(z[i])) {
      valid.push({ x: x[i], y: y[i], z: z[i] });
    }
  }
  if (valid.length < 5) return null;

  const rxy = pearsonSimple(valid.map(p => p.x), valid.map(p => p.y));
  const rxz = pearsonSimple(valid.map(p => p.x), valid.map(p => p.z));
  const ryz = pearsonSimple(valid.map(p => p.y), valid.map(p => p.z));

  const denom = Math.sqrt((1 - rxz * rxz) * (1 - ryz * ryz));
  if (denom < 1e-12) return null;

  const rPartial = (rxy - rxz * ryz) / denom;
  return {
    r_partial: +rPartial.toFixed(4),
    r_original: +rxy.toFixed(4),
    r_change: +(rPartial - rxy).toFixed(4),
    confound_suspect: Math.abs(rPartial - rxy) / (Math.abs(rxy) + 1e-12) > 0.4
  };
}

// ═══════════════════════════════════════════
//  TIME TREND CONFOUNDING
// ═══════════════════════════════════════════

function timeTrendConfounding(x, y) {
  // Check if two variables share a common time trend
  const n = x.length;
  const t = Array.from({ length: n }, (_, i) => i);

  const xTrend = pearsonSimple(t, x.filter(v => v != null && !isNaN(v)) ? x : []);
  const yTrend = pearsonSimple(t, y.filter(v => v != null && !isNaN(v)) ? y : []);

  // If both have strong time trends, the raw correlation may be spurious
  const rawR = pearsonSimple(x, y);

  // Detrend and recompute
  const xMean = x.filter(v => v != null && !isNaN(v)).reduce((a, b) => a + b, 0) / x.filter(v => v != null && !isNaN(v)).length;
  const yMean = y.filter(v => v != null && !isNaN(v)).reduce((a, b) => a + b, 0) / y.filter(v => v != null && !isNaN(v)).length;

  // Simple linear detrend
  const xTrend_slope = computeSlope(t, x);
  const yTrend_slope = computeSlope(t, y);

  const xDetrended = x.map((v, i) => v != null && !isNaN(v) ? v - (xTrend_slope * i + xMean - xTrend_slope * (n / 2)) : null);
  const yDetrended = y.map((v, i) => v != null && !isNaN(v) ? v - (yTrend_slope * i + yMean - yTrend_slope * (n / 2)) : null);

  const detrendedR = pearsonSimple(xDetrended, yDetrended);

  return {
    raw_r: +rawR.toFixed(4),
    detrended_r: +detrendedR.toFixed(4),
    x_time_trend_r: +xTrend.toFixed(4),
    y_time_trend_r: +yTrend.toFixed(4),
    attenuation_pct: rawR !== 0 ? +(((rawR - detrendedR) / Math.abs(rawR)) * 100).toFixed(1) : 0,
    trend_confounded: Math.abs(rawR - detrendedR) / (Math.abs(rawR) + 1e-12) > 0.4
  };
}

function computeSlope(t, vals) {
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, count = 0;
  for (let i = 0; i < vals.length; i++) {
    if (vals[i] == null || isNaN(vals[i])) continue;
    sumX += t[i]; sumY += vals[i]; sumXY += t[i] * vals[i]; sumX2 += t[i] * t[i]; count++;
  }
  if (count < 2) return 0;
  return (count * sumXY - sumX * sumY) / (count * sumX2 - sumX * sumX + 1e-12);
}

// ═══════════════════════════════════════════
//  SIMPSON'S PARADOX DEEP DETECTION
// ═══════════════════════════════════════════

function simpsonParadoxCheck(targetData, paramData, groupData, groupValues) {
  const fullR = pearsonSimple(targetData, paramData);
  const strata = [];

  for (const gVal of groupValues) {
    const indices = [];
    for (let i = 0; i < groupData.length; i++) {
      if (String(groupData[i]) === String(gVal)) indices.push(i);
    }
    if (indices.length < 10) continue;

    const xSub = indices.map(i => targetData[i]).filter(v => v != null && !isNaN(v));
    const ySub = indices.map(i => paramData[i]).filter(v => v != null && !isNaN(v));
    const minN = Math.min(xSub.length, ySub.length);
    const r = pearsonSimple(xSub.slice(0, minN), ySub.slice(0, minN));

    strata.push({
      group: gVal,
      r: +r.toFixed(4),
      n: indices.length,
      direction: r > 0.1 ? 'positive' : r < -0.1 ? 'negative' : 'neutral'
    });
  }

  if (strata.length < 2) return null;

  // Check: do all strata agree on direction?
  const directions = strata.map(s => s.direction);
  const hasPositive = directions.some(d => d === 'positive');
  const hasNegative = directions.some(d => d === 'negative');
  const directionReversal = hasPositive && hasNegative;

  // Check: weighted average of stratum correlations vs full
  const totalN = strata.reduce((s, st) => s + st.n, 0);
  const weightedR = strata.reduce((s, st) => s + st.r * st.n, 0) / totalN;

  return {
    full_r: +fullR.toFixed(4),
    weighted_strata_r: +weightedR.toFixed(4),
    direction_reversal: directionReversal,
    paradox_type: directionReversal ? 'DIRECTION_REVERSAL' :
                  Math.abs(weightedR - fullR) / (Math.abs(fullR) + 1e-12) > 0.5 ? 'STRONG_ATTENUATION' :
                  Math.abs(weightedR - fullR) / (Math.abs(fullR) + 1e-12) > 0.3 ? 'MODERATE_ATTENUATION' :
                  'CONSISTENT',
    strata: strata
  };
}

// ═══════════════════════════════════════════
//  MAIN VALIDATION ENGINE
// ═══════════════════════════════════════════

const args = process.argv.slice(2);
const statsPath = args[0];
const dataPath = args[1];

if (!statsPath || !dataPath) {
  console.error('Usage: node stats_validate.mjs <stats_output.json> <data.json> [--group-col G] [--time-col T] [--output validate_report.json]');
  process.exit(1);
}

const statsRaw = fs.readFileSync(statsPath, 'utf-8');
const stats = JSON.parse(statsRaw);

const dataRaw = fs.readFileSync(dataPath, 'utf-8');
const dataParsed = JSON.parse(dataRaw);
const rows = Array.isArray(dataParsed) ? dataParsed : dataParsed.data || [dataParsed];

const groupCol = args[args.indexOf('--group-col') + 1] || null;
const timeCol = args[args.indexOf('--time-col') + 1] || null;
const outputPath = args[args.indexOf('--output') + 1] || null;

// Extract numeric columns from data
const numericCols = [];
for (const key of Object.keys(rows[0] || {})) {
  if (key === timeCol) continue;
  const vals = rows.map(r => Number(r[key])).filter(v => !isNaN(v));
  if (vals.length > rows.length * 0.5) numericCols.push(key);
}

const colData = {};
for (const col of numericCols) {
  colData[col] = rows.map(r => { const v = Number(r[col]); return isNaN(v) ? null : v; });
}

const targets = stats.data_summary?.target_columns || numericCols.slice(0, 5);

// ═══ 1. Distribution Check ═══
const distributions = distributionCheck(colData);

// ═══ 2. Outlier Sensitivity for Key Correlations ═══
const outlierChecks = [];
for (const target of targets) {
  const analysis = stats.target_analysis?.[target];
  if (!analysis) continue;

  // Check top 5 Pearson correlations per target
  const corrEntries = Object.entries(analysis.pearson_correlations || {})
    .filter(([, v]) => Math.abs(v.r) > 0.2)
    .sort((a, b) => Math.abs(b[1].r) - Math.abs(a[1].r))
    .slice(0, 5);

  for (const [param, corrInfo] of corrEntries) {
    if (!colData[param]) continue;
    const sensitivity = outlierSensitivity(colData[target], colData[param], 'iqr');
    if (sensitivity) {
      outlierChecks.push({
        target, parameter: param,
        full_r: sensitivity.full_r, clean_r: sensitivity.clean_r,
        r_change_pct: sensitivity.r_change_pct,
        outliers_removed: sensitivity.outliers_removed,
        outlier_driven: sensitivity.outlier_driven,
        severity: sensitivity.outlier_driven ? 'SERIOUS' : 'OK'
      });
    }
  }
}

// ═══ 3. Time Trend Confounding ═══
const trendChecks = [];
for (const target of targets) {
  const analysis = stats.target_analysis?.[target];
  if (!analysis) continue;

  const corrEntries = Object.entries(analysis.pearson_correlations || {})
    .filter(([, v]) => Math.abs(v.r) > 0.25)
    .sort((a, b) => Math.abs(b[1].r) - Math.abs(a[1].r))
    .slice(0, 8);

  for (const [param] of corrEntries) {
    if (!colData[param]) continue;
    const trend = timeTrendConfounding(colData[target], colData[param]);
    if (trend && trend.trend_confounded) {
      trendChecks.push({
        target, parameter: param,
        raw_r: trend.raw_r, detrended_r: trend.detrended_r,
        attenuation_pct: trend.attenuation_pct,
        x_time_trend_r: trend.x_time_trend_r,
        y_time_trend_r: trend.y_time_trend_r
      });
    }
  }
}

// ═══ 4. Simpson's Paradox via Group Column ═══
let simpsonResults = [];
if (groupCol) {
  const groupData = rows.map(r => String(r[groupCol] || ''));
  const groupValues = [...new Set(groupData)].filter(v => v);
  const dominantGroup = groupValues.reduce((best, g) => {
    const count = groupData.filter(v => v === g).length;
    return count > best.count ? { group: g, count } : best;
  }, { group: null, count: 0 });

  for (const target of targets) {
    const analysis = stats.target_analysis?.[target];
    if (!analysis) continue;

    const topParams = Object.entries(analysis.pearson_correlations || {})
      .filter(([, v]) => Math.abs(v.r) > 0.2)
      .sort((a, b) => Math.abs(b[1].r) - Math.abs(a[1].r))
      .slice(0, 6);

    for (const [param] of topParams) {
      if (!colData[param]) continue;
      // Use stats' own stratified results if available
      const fromStats = stats.stratified_analysis?.find(
        s => s.target === target && s.parameter === param
      );

      if (fromStats) {
        simpsonResults.push(fromStats);
      } else {
        const check = simpsonParadoxCheck(colData[target], colData[param], groupData, groupValues);
        if (check && check.paradox_type !== 'CONSISTENT') {
          simpsonResults.push({
            target, parameter: param,
            full_r: check.full_r,
            weighted_strata_r: check.weighted_strata_r,
            paradox_type: check.paradox_type,
            direction_reversal: check.direction_reversal,
            strata: check.strata
          });
        }
      }
    }
  }

  // Add dominant group info
  simpsonResults._meta = {
    group_column: groupCol,
    n_groups: groupValues.length,
    dominant_group: dominantGroup.group,
    dominant_pct: +((dominantGroup.count / rows.length) * 100).toFixed(1)
  };
}

// ═══ 5. Lag Analysis Data Sorting Check ═══
const sortingValidation = stats.sorting_validation || { time_sorted: null };
let lagWarning = null;
if (sortingValidation.time_sorted === false) {
  lagWarning = {
    severity: 'FATAL',
    message: 'Data is NOT sorted by time. All lag correlation results are likely sorting artifacts, not genuine temporal relationships.',
    action: 'Re-sort data by time column and re-run lag analysis.',
    affected_claims: 'Any hypothesis relying on lagged correlations (especially negative lags) must be re-evaluated after re-sorting.'
  };
}

// ═══ 6. Multiple Testing Warning ═══
const multiTest = stats.multiple_testing || {};
let multiTestWarning = null;
if (multiTest.nominally_significant_p0_05 && multiTest.expected_false_positives) {
  const ratio = multiTest.nominally_significant_p0_05 / multiTest.expected_false_positives;
  if (ratio < 2) {
    multiTestWarning = {
      severity: 'MODERATE',
      message: `Only ${multiTest.nominally_significant_p0_05} significant results vs ${multiTest.expected_false_positives.toFixed(1)} expected false positives. Many "significant" correlations may be chance findings.`,
      action: 'Focus interpretation on correlations that survive Bonferroni correction or have |r| > 0.5 with p < 0.001.'
    };
  }
}

// ═══ 7. Pearson vs Spearman Divergence ═══
const spearmanWarnings = [];
for (const target of targets) {
  const analysis = stats.target_analysis?.[target];
  if (!analysis) continue;

  for (const param of Object.keys(analysis.pearson_correlations || {})) {
    const pCorr = analysis.pearson_correlations[param];
    const sCorr = analysis.spearman_correlations?.[param];
    if (!pCorr || !sCorr || Math.abs(pCorr.r) < 0.2) continue;

    const divergence = Math.abs(pCorr.r - sCorr.r);
    if (divergence > 0.15) {
      spearmanWarnings.push({
        target, parameter: param,
        pearson_r: pCorr.r,
        spearman_r: sCorr.r,
        divergence: +divergence.toFixed(3),
        severity: divergence > 0.3 ? 'SERIOUS' : 'MODERATE',
        interpretation: divergence > 0.3 ?
          'Large Pearson-Spearman divergence indicates outliers dominate the Pearson correlation. Use Spearman for interpretation.' :
          'Moderate divergence. Consider checking scatter plot for nonlinearity or outlier influence.'
      });
    }
  }
}

// ═══ Assemble Report ═══
const validateReport = {
  generated_at: new Date().toISOString(),
  summary: {
    total_targets: targets.length,
    total_parameters: numericCols.length - targets.length,
    skew_affected_columns: Object.values(distributions).filter(d => d.is_heavily_skewed).length,
    outlier_driven_correlations: outlierChecks.filter(c => c.outlier_driven).length,
    trend_confounded_correlations: trendChecks.length,
    simpson_paradox_findings: simpsonResults.filter(s => s.simpson_paradox || s.direction_reversal).length,
    spearman_divergence_findings: spearmanWarnings.filter(w => w.severity === 'SERIOUS').length,
    fatal_issues: lagWarning ? 1 : 0
  },
  sorting_validation: sortingValidation,
  lag_warning: lagWarning,
  distribution_analysis: distributions,
  outlier_sensitivity: outlierChecks,
  time_trend_confounding: trendChecks,
  simpson_paradox: simpsonResults,
  spearman_divergence: spearmanWarnings,
  multiple_testing_warning: multiTestWarning,
  overall_validity: null  // Set below
};

// Determine overall validity
const fatalCount = validateReport.summary.fatal_issues;
const seriousCount = (
  simpsonResults.filter(s => s.simpson_paradox || s.direction_reversal || s.severity === 'CRITICAL').length +
  outlierChecks.filter(c => c.outlier_driven).length +
  spearmanWarnings.filter(w => w.severity === 'SERIOUS').length
);
const moderateCount = (
  trendChecks.length +
  simpsonResults.filter(s => s.severity === 'SERIOUS' && !s.simpson_paradox && !s.direction_reversal).length
);

if (fatalCount > 0) {
  validateReport.overall_validity = 'FATAL_ISSUES — Fundamental data problems must be fixed before diagnosis can be trusted.';
} else if (seriousCount > 2) {
  validateReport.overall_validity = 'SERIOUS_CONCERNS — Multiple statistical robustness issues detected. Key correlations should be re-verified before drawing causal conclusions.';
} else if (seriousCount > 0 || moderateCount > 3) {
  validateReport.overall_validity = 'MODERATE_CONCERNS — Some statistical issues found. Flag them in the report and adjust confidence scores accordingly.';
} else if (moderateCount > 0) {
  validateReport.overall_validity = 'MINOR_CONCERNS — Minor statistical caveats. Report should mention them but overall diagnosis direction is supported.';
} else {
  validateReport.overall_validity = 'ROBUST — Statistical evidence passes robustness checks. Correlation findings are stable.';
}

const output = outputPath || statsPath.replace('.json', '_validate_report.json');
fs.writeFileSync(output, JSON.stringify(validateReport, null, 2));
console.log(JSON.stringify(validateReport, null, 2));
