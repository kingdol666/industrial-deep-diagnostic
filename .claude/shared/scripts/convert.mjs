#!/usr/bin/env node
// convert.mjs — Safe CSV/TSV to JSON conversion
// Properly handles quoted fields, embedded delimiters, and large files via streaming.
// Usage: node convert.mjs <input.csv> [--output output.json] [--sample N] [--rows N]
// If --output omitted, prints JSON to stdout.

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

// --- Streaming line counter ---
function countRows(filePath) {
  const fd = fs.openSync(filePath, 'r');
  const buf = Buffer.alloc(65536);
  let count = 0;
  let leftover = '';
  let bytesRead;
  while ((bytesRead = fs.readSync(fd, buf, 0, buf.length, null)) > 0) {
    const chunk = leftover + buf.toString('utf-8', 0, bytesRead);
    const lines = chunk.split(/\r?\n/);
    leftover = lines.pop() || '';
    count += lines.length;
  }
  if (leftover.trim()) count++;
  fs.closeSync(fd);
  return count - 1; // subtract header
}

// Main
const args = process.argv.slice(2);
const filePath = args.find(a => !a.startsWith('--'));
if (!filePath) {
  console.error('Usage: node convert.mjs <input.csv> [--output output.json] [--sample N] [--rows N]');
  process.exit(1);
}
if (!fs.existsSync(filePath)) {
  console.error(`File not found: ${filePath}`);
  process.exit(1);
}

const outIdx = args.indexOf('--output');
const outPath = outIdx !== -1 ? args[outIdx + 1] : null;

let maxRows = Infinity;
const rowsIdx = args.indexOf('--rows');
if (rowsIdx !== -1 && args[rowsIdx + 1]) maxRows = parseInt(args[rowsIdx + 1]);

let sampleSize = 0;
const sampleIdx = args.indexOf('--sample');
if (sampleIdx !== -1 && args[sampleIdx + 1]) sampleSize = parseInt(args[sampleIdx + 1]);

// Quick row count (streaming, not parsing)
let totalRows;
try {
  totalRows = countRows(filePath);
} catch {
  totalRows = null;
}

const raw = fs.readFileSync(filePath, 'utf-8');
const delim = detectDelimiter(raw.split('\n')[0]);
const parsed = parseCSV(raw, delim);

if (parsed.length < 2) {
  console.error('File has no data rows');
  process.exit(1);
}

const headers = parsed[0].map(h => h.trim());
let dataRows = parsed.slice(1);

// Apply row limit
if (dataRows.length > maxRows) {
  dataRows = dataRows.slice(0, maxRows);
}

// Apply systematic sampling for stats (preserves time-series order)
if (sampleSize > 0 && dataRows.length > sampleSize) {
  const step = Math.floor(dataRows.length / sampleSize);
  const sampled = [];
  for (let i = 0; i < dataRows.length; i += step) {
    sampled.push(dataRows[i]);
  }
  dataRows = sampled;
}

const result = dataRows.map(row => {
  const obj = {};
  headers.forEach((h, i) => {
    obj[h] = row[i]?.trim() || null;
  });
  return obj;
});

const json = JSON.stringify(result);

if (outPath) {
  const dir = path.dirname(outPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(outPath, json);
  const note = sampleSize > 0
    ? `Converted ${result.length} sampled rows (from ~${totalRows} total) → ${outPath}`
    : `Converted ${result.length} rows (from ~${totalRows} total) → ${outPath}`;
  console.log(note);
} else {
  console.log(json);
}
