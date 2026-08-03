#!/usr/bin/env node
// time_lag_compensator.mjs — Auto Time-Lag Identification & Compensation Engine
//
// Three-stage analysis:
//   Stage 1: Read ontology expected_lag for each causal relationship (physics prior)
//   Stage 2: Compute optimal lag via CCF peak-finding with window consistency check
//   Stage 3: Compare expected vs observed lag → generate lag_adjustment_recommendations
//
// Output: time_lag_analysis.json — consumed by data_processor Phase 3 and diagnostician Phase 1
//
// Usage:
//   node time_lag_compensator.mjs <stats_output.json> \
//     --ontology ontology.json \
//     --max-lag <N, default auto-detected from sample rate> \
//     --time-col <name> \
//     [--lag-search-seconds <seconds, alternative to --max-lag] \
//     [--min-consistency 0.6]

import fs from 'fs';

// ═══════════════════════════════════════════════
//  DATA LOADING
// ═══════════════════════════════════════════════

function loadJSON(path) {
  return JSON.parse(fs.readFileSync(path, 'utf-8'));
}

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    statsFile: args[0] || null,
    ontologyPath: null,
    maxLag: null,
    lagSearchSeconds: null,
    timeCol: null,
    minConsistency: 0.6,
    help: false,
  };
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--ontology') opts.ontologyPath = args[++i];
    else if (args[i] === '--max-lag') opts.maxLag = parseInt(args[++i]);
    else if (args[i] === '--lag-search-seconds') opts.lagSearchSeconds = parseFloat(args[++i]);
    else if (args[i] === '--time-col') opts.timeCol = args[++i];
    else if (args[i] === '--min-consistency') opts.minConsistency = parseFloat(args[++i]);
    else if (args[i] === '--help' || args[i] === '-h') opts.help = true;
  }
  return opts;
}

// ═══════════════════════════════════════════════
//  TIME INTERVAL DETECTION
// ═══════════════════════════════════════════════

function detectSamplingInterval(timeValues) {
  // Compute median time delta from raw timestamps (ISO strings or numeric)
  const intervals = [];
  for (let i = 1; i < Math.min(timeValues.length, 500); i++) {
    const a = new Date(timeValues[i-1]).getTime();
    const b = new Date(timeValues[i]).getTime();
    if (!isNaN(a) && !isNaN(b)) intervals.push((b - a) / 1000); // seconds
  }
  if (intervals.length === 0) return null;
  intervals.sort((a, b) => a - b);
  return intervals[Math.floor(intervals.length / 2)]; // median seconds
}

// ═══════════════════════════════════════════════
//  LAG PARSING FROM ONTOLOGY
// ═══════════════════════════════════════════════

function parseExpectedLag(lagString) {
  // Parse strings like "2-5s", "1-3h", "5-30min", "0s", "数分钟至数小时",
  // "1-3天", "即时", "2-5天至周", "0-2h" — bilingual (en + zh)
  if (!lagString) return null;

  const lowered = lagString.toLowerCase().trim();

  // Skip non-numeric descriptions
  if (/^(数|several|a few|~|approximately)/.test(lowered) && !/\d/.test(lowered)) {
    return { min_seconds: null, max_seconds: null, parseable: false, raw: lagString };
  }

  const MULT = { s: 1, sec: 1, min: 60, h: 3600, hour: 3600, hr: 3600, day: 86400,
                秒: 1, 分: 60, 分钟: 60, 时: 3600, 小时: 3600, 天: 86400, 日: 86400, 周: 604800 };

  // "即时" / "immediate" → zero-lag prior
  if (/^(即时|实时|立即|immediate|real-?time)/.test(lowered)) {
    return { min_seconds: 0, max_seconds: 0, parseable: true, raw: lagString };
  }

  // Extract number ranges: "2-5s", "5-30min", "1-3h", "0.5-2h", "1-3天", "2至5分钟"
  const rangeMatch = lowered.match(/([\d.]+)\s*(?:-|–|至|to)+\s*([\d.]+)\s*(s|sec|min|h|hour|hr|day|秒|分|分钟|时|小时|天|日|周)/);
  if (rangeMatch) {
    const min = parseFloat(rangeMatch[1]);
    const max = parseFloat(rangeMatch[2]);
    const unit = rangeMatch[3];
    const mult = MULT[unit] || 1;
    return { min_seconds: min * mult, max_seconds: max * mult, parseable: true, raw: lagString };
  }

  // Single number: "0s", "5min", "2h", "3天", "5小时"
  const singleMatch = lowered.match(/^([\d.]+)\s*(s|sec|min|h|hour|hr|day|秒|分|分钟|时|小时|天|日|周)/);
  if (singleMatch) {
    const val = parseFloat(singleMatch[1]);
    const unit = singleMatch[2];
    const mult = MULT[unit] || 1;
    return { min_seconds: val * mult, max_seconds: val * mult * 1.5, parseable: true, raw: lagString };
  }

  return { min_seconds: null, max_seconds: null, parseable: false, raw: lagString };
}

// ═══════════════════════════════════════════════
//  CCF-BASED OPTIMAL LAG FINDER
// ═══════════════════════════════════════════════

function computeCCF(x, y, maxLag) {
  // x = process parameter (cause), y = quality target (effect)
  // Positive lag means y lags behind x (x shifted backward relative to y)
  const ccf = [];
  for (let lag = -maxLag; lag <= maxLag; lag++) {
    const xSlice = [], ySlice = [];
    for (let i = 0; i < x.length; i++) {
      const yi = i + lag;
      if (yi < 0 || yi >= y.length) continue;
      const xv = x[i], yv = y[yi];
      if (xv == null || yv == null || isNaN(xv) || isNaN(yv)) continue;
      xSlice.push(xv); ySlice.push(yv);
    }
    if (xSlice.length < 10) { ccf.push({ lag, r: 0, n: xSlice.length }); continue; }

    // Pearson
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    const n = xSlice.length;
    for (let j = 0; j < n; j++) {
      sumX += xSlice[j]; sumY += ySlice[j];
      sumXY += xSlice[j] * ySlice[j];
      sumX2 += xSlice[j] * xSlice[j];
      sumY2 += ySlice[j] * ySlice[j];
    }
    const cov = sumXY / n - (sumX / n) * (sumY / n);
    const sx = Math.sqrt(sumX2 / n - (sumX / n) ** 2);
    const sy = Math.sqrt(sumY2 / n - (sumY / n) ** 2);
    const r = (sx > 0 && sy > 0) ? cov / (sx * sy) : 0;
    ccf.push({ lag, r, n });
  }
  return ccf;
}

function findOptimalLag(ccf, minConsistency) {
  // Find lag with max |r|, then check window consistency

  // First pass: find global max |r|
  let best = null;
  for (const entry of ccf) {
    if (!best || Math.abs(entry.r) > Math.abs(best.r)) best = entry;
  }
  if (!best || best.n < 10) return { optimal_lag: 0, optimal_r: 0, confidence: 'insufficient_data', consistent: false };

  // Second pass: window consistency check (±3 adjacent lags)
  const bestIdx = ccf.indexOf(best);
  const windowSize = 3;
  let consistentCount = 0, totalAdjacent = 0;
  const bestSign = best.r > 0 ? 1 : -1;

  for (let d = -windowSize; d <= windowSize; d++) {
    if (d === 0) continue;
    const idx = bestIdx + d;
    if (idx >= 0 && idx < ccf.length) {
      totalAdjacent++;
      const adj = ccf[idx];
      const adjSign = adj.r > 0 ? 1 : -1;
      if (adjSign === bestSign && Math.abs(adj.r) >= minConsistency * Math.abs(best.r)) {
        consistentCount++;
      }
    }
  }

  const consistencyRatio = totalAdjacent > 0 ? consistentCount / totalAdjacent : 0;
  const consistent = consistencyRatio >= 0.5;

  // Confidence assessment
  let confidence;
  if (Math.abs(best.r) < 0.2) confidence = 'negligible_correlation';
  else if (!consistent) confidence = 'isolated_spike_unreliable';
  else if (consistencyRatio >= 0.75 && Math.abs(best.r) >= 0.5) confidence = 'high';
  else if (consistencyRatio >= 0.5 && Math.abs(best.r) >= 0.3) confidence = 'moderate';
  else confidence = 'low';

  return {
    optimal_lag: best.lag,
    optimal_r: best.r,
    n_samples: best.n,
    consistent,
    consistency_ratio: consistencyRatio,
    adjacent_consistent_count: consistentCount,
    total_adjacent: totalAdjacent,
    confidence,
  };
}

// ═══════════════════════════════════════════════
//  LAG COMPENSATED CORRELATION
// ═══════════════════════════════════════════════

function lagCompensatedCorrelation(x, y, lag) {
  // Shift x by `lag` positions relative to y, then compute correlation
  const xAligned = [], yAligned = [];
  for (let i = 0; i < x.length; i++) {
    const yi = i + lag;
    if (yi < 0 || yi >= y.length) continue;
    if (x[i] == null || y[yi] == null || isNaN(x[i]) || isNaN(y[yi])) continue;
    xAligned.push(x[i]);
    yAligned.push(y[yi]);
  }
  if (xAligned.length < 10) return { r: 0, n: xAligned.length, p: null };

  // Pearson
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
  const n = xAligned.length;
  for (let i = 0; i < n; i++) {
    sumX += xAligned[i]; sumY += yAligned[i];
    sumXY += xAligned[i] * yAligned[i];
    sumX2 += xAligned[i] * xAligned[i];
    sumY2 += yAligned[i] * yAligned[i];
  }
  const cov = sumXY / n - (sumX / n) * (sumY / n);
  const sx = Math.sqrt(sumX2 / n - (sumX / n) ** 2);
  const sy = Math.sqrt(sumY2 / n - (sumY / n) ** 2);
  const r = (sx > 0 && sy > 0) ? cov / (sx * sy) : 0;
  return { r, n, p: null };
}

// ═══════════════════════════════════════════════
//  PHYSICS-PRIOR VS DATA LAG COMPARISON
// ═══════════════════════════════════════════════

function compareLag(expected, observed, samplingIntervalSec) {
  // Compare expected lag (from ontology physics) with observed optimal lag (from CCF)
  // Returns: agreement level + discrepancy diagnostics

  if (!expected || !expected.parseable) {
    return { agreement: 'no_physics_prior', discrepancy: null, message: 'Physics prior unavailable or unparseable' };
  }

  const obsLagSteps = observed.optimal_lag;
  const base = { observed_steps: obsLagSteps };

  // Without a known sampling interval, observed steps cannot be converted to
  // seconds — comparing against a seconds-based physics prior would fabricate
  // agreement. Report the steps and abstain instead of assuming 1 s/step.
  if (!samplingIntervalSec || samplingIntervalSec <= 0) {
    return {
      ...base,
      agreement: 'unknown_interval',
      discrepancy: null,
      message: `Sampling interval unknown — observed lag ${obsLagSteps} steps cannot be compared against physics prior ${expected.min_seconds}-${expected.max_seconds}s; interval must be supplied (--time-col or time_interval_seconds)`,
    };
  }

  const obsLagSec = obsLagSteps * samplingIntervalSec;

  const inRange = obsLagSec >= expected.min_seconds && obsLagSec <= expected.max_seconds;

  let agreement, message;
  if (inRange) {
    agreement = 'consistent';
    message = `Observed lag ${obsLagSec.toFixed(1)}s (${obsLagSteps} steps) falls within physics-expected range ${expected.min_seconds}-${expected.max_seconds}s`;
  } else if (obsLagSec < expected.min_seconds * 0.7) {
    agreement = 'shorter_than_expected';
    const ratio = (expected.min_seconds / Math.max(obsLagSec, 1)).toFixed(1);
    message = `Observed lag ${obsLagSec.toFixed(1)}s is ${ratio}x shorter than physics minimum ${expected.min_seconds}s — possible sampling aliasing or fast control response`;
  } else if (obsLagSec > expected.max_seconds * 1.3) {
    agreement = 'longer_than_expected';
    const ratio = (obsLagSec / expected.max_seconds).toFixed(1);
    message = `Observed lag ${obsLagSec.toFixed(1)}s is ${ratio}x longer than physics maximum ${expected.max_seconds}s — possible transport delay or cascade propagation`;
  } else {
    agreement = 'borderline';
    message = `Observed lag ${obsLagSec.toFixed(1)}s near physics boundary ${expected.min_seconds}-${expected.max_seconds}s (within 30% tolerance)`;
  }

  return {
    observed_steps: obsLagSteps,
    observed_seconds: obsLagSec,
    agreement,
    discrepancy: !inRange ? { expected_range_s: [expected.min_seconds, expected.max_seconds], observed_s: obsLagSec, ratio: obsLagSec / Math.max(expected.max_seconds || 1, 1) } : null,
    message,
  };
}

// ═══════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════

function main() {
  const opts = parseArgs();

  if (opts.help || !opts.statsFile) {
    console.error('Usage: node time_lag_compensator.mjs <stats_output.json> --ontology ontology.json [--time-col X] [--max-lag N] [--lag-search-seconds S] [--min-consistency 0.6]');
    process.exit(opts.help ? 0 : 1);
  }

  const stats = loadJSON(opts.statsFile);
  const ontology = loadJSON(opts.ontologyPath);

  // Extract time column values
  const timeColName = opts.timeCol || stats.data_summary?.time_column;
  if (!timeColName) {
    console.error('ERROR: No time column specified. Use --time-col or ensure stats output has time_column.');
    process.exit(1);
  }

  // Detect sampling interval from multiple sources
  let samplingIntervalSec = null;

  // Source 1: stats output may include time_interval_seconds
  if (stats.data_summary?.time_interval_seconds) {
    samplingIntervalSec = stats.data_summary.time_interval_seconds;
  }

  // Source 2: stats.sorting_validation may include time_delta_seconds
  if (!samplingIntervalSec && stats.sorting_validation?.time_delta_seconds) {
    samplingIntervalSec = stats.sorting_validation.time_delta_seconds;
  }

  // Source 3: compute from time values in stats if raw data included
  if (!samplingIntervalSec) {
    const timeValues = (stats._time_values || []).length > 0 ? stats._time_values : null;
    if (timeValues) {
      samplingIntervalSec = detectSamplingInterval(timeValues);
    }
  }

  // NOTE: no fallback assumption. When the interval cannot be determined from
  // any source, samplingIntervalSec stays null and second-level lag
  // comparisons abstain (agreement='unknown_interval') instead of assuming
  // 1 second per step — minute/hour-sampled data would otherwise be
  // misjudged 60-3600×.

  // Determine max lag
  let maxLag = opts.maxLag;
  if (!maxLag && opts.lagSearchSeconds && samplingIntervalSec) {
    maxLag = Math.ceil(opts.lagSearchSeconds / samplingIntervalSec);
  }
  if (!maxLag) {
    maxLag = 30; // default: ±30 steps
  }

  // Build relationship lookup from ontology
  const relationships = (ontology.relationships || []);
  const relMap = {};
  for (const rel of relationships) {
    const key = `${rel.from}→${rel.to}`;
    relMap[key] = rel;
  }

  // Build expected lag map
  const expectedLagMap = {};
  for (const rel of relationships) {
    if (rel.time_lag) {
      const key = `${rel.from}→${rel.to}`;
      expectedLagMap[key] = parseExpectedLag(rel.time_lag);
      // Also register reverse direction for bidirectional lookups
      const revKey = `${rel.to}→${rel.from}`;
      if (!expectedLagMap[revKey]) {
        expectedLagMap[revKey] = parseExpectedLag(rel.time_lag);
      }
    }
  }

  // Get target analysis from stats
  const targetAnalysis = stats.target_analysis || {};
  const targets = Object.keys(targetAnalysis);

  const lagAnalysis = {
    run_id: `lag_${Date.now()}`,
    generated_at: new Date().toISOString(),
    sampling_interval_seconds: samplingIntervalSec,
    max_lag_steps: maxLag,
    max_lag_seconds: (samplingIntervalSec && maxLag) ? maxLag * samplingIntervalSec : null,
    pair_analyses: [],
    summary: {
      total_pairs: 0,
      significant_lags_found: 0,
      physics_consistent: 0,
      physics_discrepancy: 0,
      no_physics_prior: 0,
    },
  };

  for (const target of targets) {
    const analysis = targetAnalysis[target];
    const bestLags = analysis.best_lags || {};
    const laggedCCF = analysis.lagged_ccf || {};

    for (const [predictor, bestLagData] of Object.entries(bestLags)) {
      if (predictor === target) continue;

      const ccfData = laggedCCF[predictor];
      if (!ccfData || ccfData.length === 0) continue;

      // Re-compute optimal lag with consistency check
      const optimal = findOptimalLag(ccfData, opts.minConsistency);

      // Lag compensated correlation — use CCF value at optimal lag
      // (feature_summary.json does not contain raw column data arrays)
      const compensatedCorr = {
        r: optimal.optimal_r,
        n: optimal.n_samples,
        p: null,
        method: 'ccf_at_optimal_lag',
      };

      // Raw (zero-lag) correlation for comparison
      const rawCorr = analysis.pearson_correlations?.[predictor]?.r || 0;
      const rawCorrObj = analysis.pearson_correlations?.[predictor] || { r: rawCorr, n: 0 };

      // Physics comparison
      const physKey = `${predictor}→${target}`;
      const expectedLag = expectedLagMap[physKey] || null;
      const ontologyRel = relMap[physKey] || null;

      let physicsComparison = { agreement: 'no_physics_prior', discrepancy: null, message: 'No physics prior available for this pair' };
      if (expectedLag) {
        physicsComparison = compareLag(expectedLag, optimal, samplingIntervalSec || 1);
      }

      // Correlation improvement assessment
      const rImprovement = Math.abs(compensatedCorr.r) - Math.abs(rawCorr);
      const improvementRatio = (Math.abs(rawCorr) > 0.001)
        ? (Math.abs(compensatedCorr.r) - Math.abs(rawCorr)) / Math.abs(rawCorr)
        : (Math.abs(compensatedCorr.r) > 0.1 ? 1.0 : 0);

      const pairResult = {
        target,
        predictor,
        ontology_relationship: ontologyRel ? { type: ontologyRel.type, mechanism: ontologyRel.mechanism, strength: ontologyRel.strength } : null,
        expected_lag: expectedLag,
        raw_correlation: { r: rawCorrObj.r, n: rawCorrObj.n },
        optimal_lag: {
          steps: optimal.optimal_lag,
          seconds: samplingIntervalSec ? optimal.optimal_lag * samplingIntervalSec : null,
          confidence: optimal.confidence,
          consistent: optimal.consistent,
          consistency_ratio: optimal.consistency_ratio,
        },
        ccf_at_optimal: { r: optimal.optimal_r, n: optimal.n_samples },
        lag_compensated_correlation: compensatedCorr,
        r_improvement: {
          absolute: rImprovement,
          relative_pct: parseFloat((improvementRatio * 100).toFixed(1)),
          significant: improvementRatio > 0.15, // >15% improvement is meaningful
        },
        physics_agreement: physicsComparison,
      };

      lagAnalysis.pair_analyses.push(pairResult);
      lagAnalysis.summary.total_pairs++;

      if (optimal.confidence !== 'negligible_correlation' && optimal.confidence !== 'insufficient_data') {
        lagAnalysis.summary.significant_lags_found++;
      }
      if (physicsComparison.agreement === 'consistent') {
        lagAnalysis.summary.physics_consistent++;
      } else if (physicsComparison.discrepancy) {
        lagAnalysis.summary.physics_discrepancy++;
      }
      if (!expectedLag) {
        lagAnalysis.summary.no_physics_prior++;
      }
    }
  }

  // Top-N actionable recommendations
  const significantPairs = lagAnalysis.pair_analyses
    .filter(p => p.r_improvement.significant && p.optimal_lag.confidence !== 'negligible_correlation')
    .sort((a, b) => Math.abs(b.r_improvement.absolute) - Math.abs(a.r_improvement.absolute));

  lagAnalysis.recommendations = significantPairs.slice(0, 10).map(p => ({
    target: p.target,
    predictor: p.predictor,
    recommended_lag_steps: p.optimal_lag.steps,
    recommended_lag_seconds: p.optimal_lag.seconds,
    correlation_improvement_pct: p.r_improvement.relative_pct,
    raw_r: p.raw_correlation.r,
    compensated_r: p.lag_compensated_correlation.r,
    physics_agreement: p.physics_agreement.agreement,
    action: p.optimal_lag.steps !== 0
      ? `Apply ${p.optimal_lag.steps}-step lag compensation when analyzing ${p.predictor}→${p.target}. Compensated r=${p.lag_compensated_correlation.r.toFixed(3)} vs raw r=${p.raw_correlation.r.toFixed(3)} (+${p.r_improvement.relative_pct}%).`
      : `Zero-lag correlation already optimal for ${p.predictor}→${p.target}. No compensation needed.`,
  }));

  // Physics discrepancy alerts
  lagAnalysis.physics_discrepancy_alerts = lagAnalysis.pair_analyses
    .filter(p => p.physics_agreement.discrepancy)
    .map(p => ({
      pair: `${p.predictor}→${p.target}`,
      agreement: p.physics_agreement.agreement,
      message: p.physics_agreement.message,
      expected: p.expected_lag,
      observed_seconds: p.optimal_lag.seconds,
    }));

  console.log(JSON.stringify(lagAnalysis, null, 2));
}

main();
