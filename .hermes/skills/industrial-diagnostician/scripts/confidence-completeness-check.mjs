#!/usr/bin/env node
// confidence-completeness-check.mjs — Verify confidence.json five-factor
// breakdown completeness.
//
// Usage:
//   node confidence-completeness-check.mjs <RUN_DIR>
//
// Exit code: 0 = PASS, 1 = FAIL

import fs from 'fs';
import { join } from 'path';

const runDir = process.argv[2];
if (!runDir) {
  console.error('Usage: node confidence-completeness-check.mjs <RUN_DIR>');
  process.exit(1);
}

function readJson(relPath) {
  try {
    return JSON.parse(fs.readFileSync(join(runDir, relPath), 'utf8'));
  } catch { return null; }
}

const confidence = readJson('04_diagnostics/confidence.json');
const checks = [];

if (!confidence) {
  console.log(JSON.stringify({ status: 'FAIL', error: 'confidence.json not found or invalid' }, null, 2));
  process.exit(1);
}

// Check 1: overall_confidence.score in 0-100
const overallScore = confidence.overall_confidence?.score;
const overallOk = typeof overallScore === 'number' && overallScore >= 0 && overallScore <= 100;
checks.push({
  check: 'OVERALL_CONFIDENCE_RANGE',
  status: overallOk ? 'pass' : 'fail',
  detail: overallOk ? `score=${overallScore}` : `score=${overallScore} not in [0,100]`
});

// Check 2: confidence_breakdown has at least 1 hypothesis
// Schema contract: confidence_breakdown is an OBJECT keyed by hypothesis id
// ({"H1": {...}, "H2": {...}}). Accept both shapes defensively.
const rawBreakdown = confidence.confidence_breakdown || {};
const breakdowns = Array.isArray(rawBreakdown) ? rawBreakdown : Object.values(rawBreakdown);
const breakdownOk = breakdowns.length >= 1;
checks.push({
  check: 'CONFIDENCE_BREAKDOWN_COUNT',
  status: breakdownOk ? 'pass' : 'fail',
  detail: breakdownOk ? `${breakdowns.length} hypotheses` : 'empty confidence_breakdown'
});

// Check 3: each hypothesis has complete five_factor_breakdown
const REQUIRED_FACTORS = [
  { key: 'statistical_strength', max: 25 },
  { key: 'physical_plausibility', max: 25 },
  { key: 'temporal_evidence', max: 20 },
  { key: 'absence_of_confounds', max: 20 },
  { key: 'symptom_completeness', max: 10 },
];

const hypothesisChecks = [];
// Schema contract: each factor is {score, max, note}; accept plain numbers too.
const factorScore = (v) => (typeof v === 'number' ? v : (v && typeof v === 'object' ? v.score : undefined));
for (const h of breakdowns) {
  const factors = h.five_factor_breakdown || {};
  const missing = REQUIRED_FACTORS.filter(f => factorScore(factors[f.key]) === undefined);
  const outOfRange = REQUIRED_FACTORS.filter(f => {
    const s = factorScore(factors[f.key]);
    return typeof s === 'number' && (s < 0 || s > f.max);
  });

  const sum = REQUIRED_FACTORS.reduce((s, f) => s + (factorScore(factors[f.key]) || 0), 0);
  const scoreOk = Math.abs(sum - (h.confidence_score || 0)) <= 1;

  hypothesisChecks.push({
    hypothesis: h.hypothesis_id || h.id || '(unnamed)',
    complete: missing.length === 0 && outOfRange.length === 0,
    all_factors: REQUIRED_FACTORS.map(f => f.key),
    missing_factors: missing.map(f => f.key),
    out_of_range: outOfRange.map(f => `${f.key}=${factors[f.key]} (max ${f.max})`),
    sum_matches_score: scoreOk
  });
}
checks.push({
  check: 'FIVE_FACTOR_BREAKDOWN',
  status: hypothesisChecks.every(h => h.complete && h.sum_matches_score) ? 'pass' : 'fail',
  detail: hypothesisChecks.map(h =>
    `${h.hypothesis}: complete=${h.complete}, sum_matches=${h.sum_matches_score}` +
    (h.missing_factors.length ? ` missing=[${h.missing_factors.join(',')}]` : '') +
    (h.out_of_range.length ? ` out_of_range=[${h.out_of_range.join(',')}]` : '')
  ).join('; ')
});

// Check 4: adjustment_log entries
const adjustments = confidence.adjustment_log || [];
const adjOk = adjustments.length >= 1;
const adjComplete = adjustments.every(a =>
  a.hypothesis_id && a.adjustment && a.reason && a.source
);
checks.push({
  check: 'ADJUSTMENT_LOG',
  status: adjOk && adjComplete ? 'pass' : 'fail',
  detail: adjOk
    ? `${adjustments.length} entries, all ${adjComplete ? 'complete' : 'incomplete'}`
    : 'adjustment_log is empty or missing'
});

// Check 5: hypothesis confidence <= ceiling
const ceilings = confidence.confidence_ceilings_applied || [];
const ceilingChecks = [];
for (const h of breakdowns) {
  const hId = h.hypothesis_id || h.id || '';
  const relatedCeiling = ceilings.find(c => c.hypothesis_ids?.includes(hId));
  if (relatedCeiling && relatedCeiling.ceiling !== undefined) {
    const exceeds = (h.confidence_score || 0) > relatedCeiling.ceiling;
    ceilingChecks.push({ hypothesis: hId, ceiling: relatedCeiling.ceiling, score: h.confidence_score, exceeds });
  }
}
const ceilingOk = ceilingChecks.every(c => !c.exceeds);
if (ceilings.length > 0) {
  checks.push({
    check: 'CONFIDENCE_CEILING_RESPECTED',
    status: ceilingOk ? 'pass' : 'fail',
    detail: ceilingOk ? 'all within ceilings' : ceilingChecks.filter(c => c.exceeds).map(c =>
      `${c.hypothesis}: score ${c.score} exceeds ceiling ${c.ceiling}`
    ).join('; ')
  });
}

// Check 6: each ceiling has reason
const ceilingReasonOk = ceilings.every(c => c.reason && String(c.reason).trim().length > 0);
if (ceilings.length > 0) {
  checks.push({
    check: 'CEILING_REASON',
    status: ceilingReasonOk ? 'pass' : 'fail',
    detail: ceilingReasonOk ? 'all ceilings have reasons' : 'some ceilings missing reason'
  });
}

const passed = checks.filter(c => c.status === 'pass').length;
const result = {
  status: passed === checks.length ? 'PASS' : 'FAIL',
  hypothesis_count: breakdowns.length,
  checks,
  adjustment_log_entries: adjustments.length,
  ceilings_applied: ceilings.length
};

console.log(JSON.stringify(result, null, 2));
process.exit(result.status === 'PASS' ? 0 : 1);
