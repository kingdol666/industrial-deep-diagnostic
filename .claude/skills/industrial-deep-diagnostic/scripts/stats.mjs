#!/usr/bin/env node
// stats.mjs — Zero-dependency statistical analysis
// Reads a JSON data file (from inspect output or CSV converted), computes correlations, z-scores, abnormal intervals
// Usage: node stats.mjs <data.json> --time-col <col> --target-cols <col1,col2,...>

import fs from 'fs';

function loadData(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  const parsed = JSON.parse(raw);
  if (Array.isArray(parsed)) return parsed;
  if (parsed.column_details) {
    // Convert inspect output format to row objects
    return parsed.preview || [];
  }
  return parsed.data || [parsed];
}

function pearson(x, y) {
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
  return den === 0 ? 0 : +(num / den).toFixed(4);
}

function laggedCorr(x, y, maxLag) {
  let bestR = 0, bestLag = 0;
  for (let lag = -maxLag; lag <= maxLag; lag++) {
    const xSlice = [], ySlice = [];
    for (let i = 0; i < x.length; i++) {
      const yi = i + lag;
      if (yi < 0 || yi >= y.length) continue;
      if (x[i] != null && y[yi] != null && !isNaN(x[i]) && !isNaN(y[yi])) {
        xSlice.push(x[i]); ySlice.push(y[yi]);
      }
    }
    const r = pearson(xSlice, ySlice);
    if (Math.abs(r) > Math.abs(bestR)) { bestR = r; bestLag = lag; }
  }
  return { r: bestR, lag_periods: bestLag };
}

function zScoreAbnormal(values, baselineEnd) {
  const baseline = values.slice(0, Math.min(baselineEnd, values.length));
  const valid = baseline.filter(v => v != null && !isNaN(v));
  if (valid.length < 5) return [];
  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const std = Math.sqrt(valid.reduce((a, b) => a + (b - mean) ** 2, 0) / valid.length);
  if (std === 0) return [];

  const abnormal = [];
  let inAbnormal = false, start = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null || isNaN(v)) continue;
    const z = Math.abs((v - mean) / std);
    if (z > 3) {
      if (!inAbnormal) { start = i; inAbnormal = true; }
    } else {
      if (inAbnormal) {
        abnormal.push({ start_idx: start, end_idx: i - 1, count: i - start });
        inAbnormal = false;
      }
    }
  }
  if (inAbnormal) abnormal.push({ start_idx: start, end_idx: values.length - 1, count: values.length - start });
  return abnormal;
}

// Main
const args = process.argv.slice(2);
const filePath = args[0];
if (!filePath) { console.error('Usage: node stats.mjs <data.json> [--time-col X] [--target-cols A,B,C] [--max-lag N]'); process.exit(1); }

const raw = fs.readFileSync(filePath, 'utf-8');
const rows = JSON.parse(raw);
if (!Array.isArray(rows) || rows.length === 0) { console.error('Expected JSON array of objects'); process.exit(1); }

const timeCol = (args[args.indexOf('--time-col') + 1]) || null;
const targetColsStr = (args[args.indexOf('--target-cols') + 1]) || '';
const targetCols = targetColsStr ? targetColsStr.split(',').map(s => s.trim()) : [];
const maxLag = parseInt(args[args.indexOf('--max-lag') + 1]) || 30;

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

// Correlation matrix
const correlations = {};
for (const c1 of numericCols) {
  correlations[c1] = {};
  for (const c2 of numericCols) {
    correlations[c1][c2] = pearson(colData[c1], colData[c2]);
  }
}

// Abnormal intervals for target columns
const abnormalIntervals = [];
for (const col of (targetCols.length ? targetCols : numericCols.slice(0, 3))) {
  if (!colData[col]) continue;
  const baselineEnd = Math.floor(rows.length * 0.2);
  const intervals = zScoreAbnormal(colData[col], baselineEnd);
  for (const iv of intervals) {
    abnormalIntervals.push({
      column: col,
      start_idx: iv.start_idx,
      end_idx: iv.end_idx,
      count: iv.count,
      start_value: timeCol && rows[iv.start_idx]?.[timeCol] ? rows[iv.start_idx][timeCol] : iv.start_idx,
      end_value: timeCol && rows[iv.end_idx]?.[timeCol] ? rows[iv.end_idx][timeCol] : iv.end_idx,
    });
  }
}

// Lagged correlations (target cols vs all numeric)
const laggedCorrelations = {};
for (const target of (targetCols.length ? targetCols : numericCols.slice(0, 1))) {
  if (!colData[target]) continue;
  laggedCorrelations[target] = {};
  for (const col of numericCols) {
    if (col === target) continue;
    laggedCorrelations[target][col] = laggedCorr(colData[target], colData[col], maxLag);
  }
}

const result = { correlations, abnormal_intervals: abnormalIntervals, lagged_correlations: laggedCorrelations, numeric_columns: numericCols };
console.log(JSON.stringify(result, null, 2));
