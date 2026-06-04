#!/usr/bin/env node
// normalize-anomaly-report.mjs — Repair/normalize anomaly_report.json so it
// satisfies the current schema while preserving existing analysis.
//
// Usage:
//   node normalize-anomaly-report.mjs <run_dir>

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

if (!runDir) {
  console.error('Usage: node normalize-anomaly-report.mjs <run_dir>');
  process.exit(1);
}

function readJson(pathLike) {
  return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
}

function writeJson(pathLike, data) {
  fs.writeFileSync(pathLike, `${JSON.stringify(data, null, 2)}\n`);
}

function safeNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function safeInteger(value, fallback = null) {
  const numeric = Number(value);
  if (Number.isInteger(numeric) && numeric >= 0) {
    return numeric;
  }
  return fallback;
}

function normalizeSeverity(value, fallbackMetric = null) {
  if (typeof value === 'string') {
    const lowered = value.toLowerCase();
    if (['low', 'medium', 'high', 'critical'].includes(lowered)) {
      return lowered;
    }
  }
  const metric = safeNumber(value) ?? safeNumber(fallbackMetric);
  if (metric == null) return 'medium';
  if (metric >= 4.5) return 'critical';
  if (metric >= 3) return 'high';
  if (metric >= 2) return 'medium';
  return 'low';
}

function normalizeConcurrentParams(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const result = {};
  for (const [key, item] of Object.entries(value)) {
    result[key] = typeof item === 'string' ? item : JSON.stringify(item);
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

function normalizeInterval(item, index) {
  const startIndex = safeInteger(item?.start_index)
    ?? safeInteger(item?.index)
    ?? safeInteger(item?.row_index)
    ?? safeInteger(item?.start)
    ?? index;
  const endIndex = safeInteger(item?.end_index)
    ?? safeInteger(item?.end)
    ?? startIndex;

  const interval = {
    start_index: startIndex,
    end_index: endIndex,
    severity: normalizeSeverity(item?.severity, item?.z_score ?? item?.max_deviation_sigma)
  };

  const sigma = safeNumber(item?.max_deviation_sigma) ?? safeNumber(item?.z_score);
  if (sigma != null) {
    interval.max_deviation_sigma = sigma;
  }

  const concurrentParams = normalizeConcurrentParams(item?.concurrent_params);
  if (concurrentParams) {
    interval.concurrent_params = concurrentParams;
  }

  return interval;
}

function normalizeThresholdAnalysis(value, fallbackThreshold = 0, fallbackIntervals = []) {
  const threshold = safeNumber(value?.critical_threshold)
    ?? safeNumber(value?.threshold)
    ?? safeNumber(fallbackThreshold)
    ?? 0;

  const percentAboveThreshold = safeNumber(value?.percent_above_threshold)
    ?? safeNumber(value?.percent_above)
    ?? 0;

  const crossingIndex = safeInteger(value?.threshold_crossing_index)
    ?? (fallbackIntervals.length > 0 ? fallbackIntervals[0].start_index : null);

  const normalized = {
    critical_threshold: threshold,
    percent_above_threshold: Math.max(0, Math.min(100, percentAboveThreshold))
  };

  if (crossingIndex != null) {
    normalized.threshold_crossing_index = crossingIndex;
  }

  return normalized;
}

const anomalyPath = join(runDir, '02_processed', 'anomaly_report.json');
if (!fs.existsSync(anomalyPath)) {
  console.error(`Missing anomaly report: ${anomalyPath}`);
  process.exit(1);
}

const report = readJson(anomalyPath);

const manifestPath = join(runDir, '00_input', 'input_manifest.json');
const featureSummaryPath = join(runDir, '02_processed', 'feature_summary.json');
const manifest = fs.existsSync(manifestPath) ? readJson(manifestPath) : {};
const featureSummary = fs.existsSync(featureSummaryPath) ? readJson(featureSummaryPath) : {};

const targetCandidates = []
  .concat(manifest.target_columns || [])
  .concat(report.target_columns || [])
  .concat(featureSummary.target_columns || [])
  .filter((value, index, array) => value && array.indexOf(value) === index);

const targets = {};

const existingTargets = report.targets && typeof report.targets === 'object' && !Array.isArray(report.targets)
  ? report.targets
  : {};

for (const [target, value] of Object.entries(existingTargets)) {
  const normalizedIntervals = Array.isArray(value?.anomaly_intervals)
    ? value.anomaly_intervals.map((item, index) => normalizeInterval(item, index))
    : [];
  targets[target] = {
    anomaly_intervals: normalizedIntervals,
    threshold_analysis: normalizeThresholdAnalysis(
      value?.threshold_analysis,
      report.anomaly_thresholds?.[target]?.p90 ?? report.anomaly_thresholds?.[target]?.mean ?? report.anomaly_thresholds?.[target]?.max ?? 0,
      normalizedIntervals
    )
  };
}

if (Array.isArray(report.anomaly_intervals) && targetCandidates.length > 0) {
  const normalizedIntervals = report.anomaly_intervals.map((item, index) => normalizeInterval(item, index));
  const primaryTarget = targetCandidates[0];
  const existingTarget = targets[primaryTarget];
  targets[primaryTarget] = {
    anomaly_intervals: existingTarget?.anomaly_intervals?.length ? existingTarget.anomaly_intervals : normalizedIntervals,
    threshold_analysis: normalizeThresholdAnalysis(
      existingTarget?.threshold_analysis,
      report.anomaly_thresholds?.[primaryTarget]?.p90
        ?? report.anomaly_thresholds?.[primaryTarget]?.mean
        ?? report.anomaly_thresholds?.[primaryTarget]?.max
        ?? 0,
      existingTarget?.anomaly_intervals?.length ? existingTarget.anomaly_intervals : normalizedIntervals
    )
  };
}

if (Array.isArray(report.anomaly_batches) && targetCandidates.length > 0) {
  const primaryTarget = targetCandidates[0];
  const normalizedIntervals = report.anomaly_batches.map((item, index) => normalizeInterval(item, index));
  if (!targets[primaryTarget] || targets[primaryTarget].anomaly_intervals.length === 0) {
    targets[primaryTarget] = {
      anomaly_intervals: normalizedIntervals,
      threshold_analysis: normalizeThresholdAnalysis(
        undefined,
        report.anomaly_thresholds?.[primaryTarget]?.p90
          ?? report.anomaly_thresholds?.[primaryTarget]?.mean
          ?? report.anomaly_thresholds?.[primaryTarget]?.max
          ?? 0,
        normalizedIntervals
      )
    };
  }
}

for (const target of targetCandidates) {
  if (!targets[target]) {
    targets[target] = {
      anomaly_intervals: [],
      threshold_analysis: normalizeThresholdAnalysis(
        undefined,
        report.anomaly_thresholds?.[target]?.p90
          ?? report.anomaly_thresholds?.[target]?.mean
          ?? report.anomaly_thresholds?.[target]?.max
          ?? 0,
        []
      )
    };
  }
}

const transitionEvents = Array.isArray(report.transition_events)
  ? report.transition_events.map((item, index) => {
      const normalized = {
        index: safeInteger(item?.index, index),
        type: String(item?.type || 'state_change'),
        column: String(item?.column || item?.feature || item?.name || 'unknown')
      };
      if (item?.from != null) normalized.from = String(item.from);
      if (item?.to != null) normalized.to = String(item.to);
      if (item?.quality_before && typeof item.quality_before === 'object' && !Array.isArray(item.quality_before)) {
        normalized.quality_before = item.quality_before;
      }
      if (item?.quality_after && typeof item.quality_after === 'object' && !Array.isArray(item.quality_after)) {
        normalized.quality_after = item.quality_after;
      }
      const jump = safeNumber(item?.quality_jump_sigma);
      if (jump != null) normalized.quality_jump_sigma = jump;
      return normalized;
    })
  : [];

const normalized = {
  ...report,
  targets,
  transition_events: transitionEvents,
  summary: {
    ...(report.summary || {}),
    normalized_from_legacy_shape: true
  }
};

writeJson(anomalyPath, normalized);
console.log(JSON.stringify({
  ok: true,
  changed: true,
  anomaly_path: anomalyPath,
  targets_written: Object.keys(targets),
  transition_count: normalized.transition_events.length
}, null, 2));
