#!/usr/bin/env node
// inspect.mjs — Zero-dependency data file inspection
// Reads CSV/JSON/TSV, outputs schema, stats, and preview as JSON
// Usage: node inspect.mjs <file> [--rows 5]

import fs from 'fs';
import path from 'path';

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
  const keywords = ['time', 'timestamp', 'datetime', 'date', 'zeit', '时间', '时刻', 'ts'];
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

// Main
const filePath = process.argv[2];
if (!filePath) { console.error('Usage: node inspect.mjs <file> [--rows N]'); process.exit(1); }
if (!fs.existsSync(filePath)) { console.error(`File not found: ${filePath}`); process.exit(1); }

let previewRows = 5;
const rowsIdx = process.argv.indexOf('--rows');
if (rowsIdx !== -1 && process.argv[rowsIdx + 1]) previewRows = parseInt(process.argv[rowsIdx + 1]);

const ext = path.extname(filePath).toLowerCase();
const raw = fs.readFileSync(filePath, 'utf-8');
let headers, dataRows;

if (ext === '.json') {
  const json = JSON.parse(raw);
  const arr = Array.isArray(json) ? json : json.data || [json];
  if (arr.length === 0) { console.error('Empty JSON array'); process.exit(1); }
  headers = Object.keys(arr[0]);
  dataRows = arr.map(obj => headers.map(h => obj[h] ?? ''));
} else {
  const delim = detectDelimiter(raw.split('\n')[0]);
  const parsed = parseCSV(raw, delim);
  if (parsed.length < 2) { console.error('File has no data rows'); process.exit(1); }
  headers = parsed[0];
  dataRows = parsed.slice(1);
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
const preview = dataRows.slice(0, previewRows).map(row => {
  const obj = {};
  headers.forEach((h, i) => obj[h] = row[i] ?? '');
  return obj;
});

const result = {
  file: path.resolve(filePath),
  format: ext.replace('.', ''),
  rows: nRows,
  columns: headers.length,
  time_column: timeCol,
  column_details: columns,
  preview,
};

console.log(JSON.stringify(result, null, 2));
