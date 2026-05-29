#!/usr/bin/env node
// inspect.mjs — Zero-dependency data file inspection
// Reads CSV/JSON/TSV with streaming parse. Delegates Excel/Parquet/Feather to inspect.py.
// For files > 100K rows, samples for stats computation to avoid OOM.
// Usage: node inspect.mjs <file> [--rows N] [--sample-size N]

import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

function parseCSV(text, delimiter = ',') {
  const rows = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const row = [];
    let inQ = false, field = '';
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"' && line[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') { inQ = false; }
        else { field += c; }
      } else {
        if (c === '"') { inQ = true; }
        else if (c === delimiter) { row.push(field); field = ''; }
        else { field += c; }
      }
    }
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function detectDelimiter(header) {
  if (header.includes('\t')) return '\t';
  if (header.includes(';')) return ';';
  return ',';
}

function inferType(values) {
  let numCount = 0, dateCount = 0, total = 0;
  for (const v of values) {
    if (v === '' || v === null || v === undefined) continue;
    total++;
    if (!isNaN(Number(v))) { numCount++; continue; }
    if (/^\d{4}[-/]\d{2}[-/]\d{2}/.test(v) || /^\d{2}[-/]\d{2}[-/]\d{2}/.test(v)) {
      const d = new Date(v);
      if (!isNaN(d.getTime())) { dateCount++; continue; }
    }
  }
  if (total === 0) return 'string';
  if (numCount / total > 0.9) return 'number';
  if (dateCount / total > 0.9) return 'datetime';
  return 'string';
}

function numericStats(values) {
  const nums = values.map(Number).filter(v => !isNaN(v));
  if (nums.length === 0) return null;
  const n = nums.length;
  const sorted = [...nums].sort((a, b) => a - b);
  const sum = nums.reduce((a, b) => a + b, 0);
  const mean = sum / n;
  const variance = nums.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
  const std = Math.sqrt(variance);
  const missing = values.length - nums.length;
  return {
    count: n, missing, missing_pct: +((missing / values.length) * 100).toFixed(2),
    mean: +mean.toFixed(4), std: +std.toFixed(4),
    min: sorted[0], max: sorted[n - 1],
    p25: sorted[Math.floor(n * 0.25)],
    p50: sorted[Math.floor(n * 0.5)],
    p75: sorted[Math.floor(n * 0.75)],
  };
}

function stringStats(values) {
  const counts = {};
  let missing = 0;
  for (const v of values) {
    if (v === '' || v === null || v === undefined) { missing++; continue; }
    counts[v] = (counts[v] || 0) + 1;
  }
  const unique = Object.keys(counts).length;
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return { count: values.length - missing, missing, missing_pct: +((missing / values.length) * 100).toFixed(2), unique, top_values: top };
}

function detectTimeColumn(columns) {
  const keywords = ['time', 'timestamp', 'datetime', 'date', 'zeit', 'ts'];
  for (const col of columns) {
    const name = typeof col === 'string' ? col : col.name;
    const lower = name.toLowerCase().trim();
    if (keywords.some(k => lower.includes(k))) return name;
  }
  for (const col of columns) {
    if (col.type === 'datetime') return col.name;
  }
  return null;
}

// --- Streaming row counter (avoids loading entire file) ---
function countRowsCSV(filePath) {
  const fd = fs.openSync(filePath, 'r');
  const buf = Buffer.alloc(65536);
  let rowCount = 0;
  let leftover = '';
  let bytesRead;
  while ((bytesRead = fs.readSync(fd, buf, 0, buf.length, null)) > 0) {
    const chunk = leftover + buf.toString('utf-8', 0, bytesRead);
    const lines = chunk.split(/\r?\n/);
    leftover = lines.pop() || '';
    rowCount += lines.length;
  }
  fs.closeSync(fd);
  return rowCount - 1; // subtract header
}

// --- File format dispatch ---
const BINARY_FORMATS = new Set(['.xlsx', '.xls', '.parquet', '.feather', '.ipc', '.arrow']);

function delegateToPython(filePath, previewRows) {
  const scriptDir = path.dirname(new URL(import.meta.url).pathname);
  const pyScript = path.join(scriptDir, 'file_inspect.py');
  const cmd = `python3 "${pyScript}" "${filePath}" --rows ${previewRows}`;
  try {
    const result = execSync(cmd, { encoding: 'utf-8', maxBuffer: 50 * 1024 * 1024, timeout: 120000 });
    return result;
  } catch (e) {
    // Fallback: try python3.11
    try {
      const cmd2 = `python3.11 "${pyScript}" "${filePath}" --rows ${previewRows}`;
      return execSync(cmd2, { encoding: 'utf-8', maxBuffer: 50 * 1024 * 1024, timeout: 120000 });
    } catch (e2) {
      return JSON.stringify({
        error: `Python inspection failed. Install dependencies: pip3 install pandas numpy openpyxl pyarrow\n  Node: ${e.stderr || e.message}\n  Python: ${e2.stderr || e2.message}`,
        file: filePath,
      });
    }
  }
}

// Main
const args = process.argv.slice(2);
const filePath = args.find(a => !a.startsWith('--') && args.indexOf(a) < 2) || args[0];
if (!filePath) { console.error('Usage: node inspect.mjs <file> [--rows N] [--sample-size N]'); process.exit(1); }
if (!fs.existsSync(filePath)) { console.error(`File not found: ${filePath}`); process.exit(1); }

let previewRows = 5;
const rowsIdx = args.indexOf('--rows');
if (rowsIdx !== -1 && args[rowsIdx + 1]) previewRows = parseInt(args[rowsIdx + 1]);

let sampleSize = 50000;
const sampleIdx = args.indexOf('--sample-size');
if (sampleIdx !== -1 && args[sampleIdx + 1]) sampleSize = parseInt(args[sampleIdx + 1]);

const ext = path.extname(filePath).toLowerCase();

// Route binary/proprietary formats to Python
if (BINARY_FORMATS.has(ext)) {
  const output = delegateToPython(filePath, previewRows);
  console.log(output);
  process.exit(0);
}

// --- Streaming row count for large CSV (fast, doesn't parse) ---
let totalRows;
try {
  totalRows = countRowsCSV(filePath);
} catch (e) {
  totalRows = null;
}

const USE_SAMPLE = totalRows !== null && totalRows > 100000;

const raw = fs.readFileSync(filePath, 'utf-8');
let headers, dataRows;

if (ext === '.json') {
  const json = JSON.parse(raw);
  const arr = Array.isArray(json) ? json : json.data || [json];
  if (arr.length === 0) { console.error('Empty JSON array'); process.exit(1); }
  totalRows = arr.length;
  headers = Object.keys(arr[0]);
  if (totalRows > 100000) {
    // Reservoir-sample ~50K rows for stats
    const sampled = [];
    const step = Math.max(1, Math.floor(totalRows / sampleSize));
    for (let i = 0; i < totalRows; i += step) sampled.push(arr[i]);
    dataRows = sampled.map(obj => headers.map(h => obj[h] ?? ''));
  } else {
    dataRows = arr.map(obj => headers.map(h => obj[h] ?? ''));
  }
} else {
  const delim = detectDelimiter(raw.split('\n')[0]);
  const parsed = parseCSV(raw, delim);
  if (parsed.length < 2) { console.error('File has no data rows'); process.exit(1); }
  headers = parsed[0];
  const allDataRows = parsed.slice(1);

  if (USE_SAMPLE) {
    // Systematic sample for stats computation
    const step = Math.max(1, Math.floor(allDataRows.length / sampleSize));
    const sampledRows = [];
    for (let i = 0; i < allDataRows.length; i += step) {
      sampledRows.push(allDataRows[i]);
    }
    dataRows = sampledRows;
  } else {
    dataRows = allDataRows;
  }
}

// Build columns
const nRows = dataRows.length;
const columns = headers.map((name, ci) => {
  const values = dataRows.map(row => row[ci] ?? '');
  const type = inferType(values);
  const stats = type === 'number' ? numericStats(values) : stringStats(values);
  return { name, index: ci, type, stats };
});

const timeCol = detectTimeColumn(columns);
const previewDataRows = dataRows.slice(0, previewRows);
const preview = previewDataRows.map(row => {
  const obj = {};
  headers.forEach((h, i) => obj[h] = row[i] ?? '');
  return obj;
});

const result = {
  file: path.resolve(filePath),
  format: ext.replace('.', ''),
  rows: totalRows || nRows,
  columns: headers.length,
  time_column: timeCol,
  column_details: columns,
  preview,
};

if (USE_SAMPLE) {
  result._note = `Stats computed on systematic sample of ${nRows} rows from ${totalRows} total rows. Use --rows for preview count, --sample-size to change sample size.`;
}

console.log(JSON.stringify(result, null, 2));
