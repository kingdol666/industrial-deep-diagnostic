// Dataset loading + matrix preparation for the Baseline Lab.
//
// Two TEP encodings exist in this repository and they must be reconciled:
//
//   results-side (benchmark cases)   data/benchmark/prepared/tep/dNN_te.csv
//                                    timestamp,XMEAS_1..41,XMV_1..11     (53 cols)
//
//   training-side (FaultExplainer)   baselines/FaultExplainer/backend/data/faultN.csv
//                                    time,<52 human-readable TEP tags>
//
// FE's 52 tags are the standard Downs-Vogel ordering, so the mapping below is
// exact and order-preserving. It lets the supervised baselines train on FE's
// labelled normal/fault runs and then score the benchmark cases.

import fs from 'node:fs';
import { repoPath, exists } from './paths.mjs';

// ------------------------------------------------------------- CSV parsing

/** Quoted-CSV parser (same semantics as scripts/benchmark/baseline_pca.mjs). */
export function parseCsv(text) {
  const rows = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false;
      } else field += ch;
    } else if (ch === '"') inQ = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else field += ch;
  }
  row.push(field);
  if (row.length > 1 || row[0] !== '') rows.push(row);
  const header = rows.shift() || [];
  return { header: header.map((h) => h.trim()), rows };
}

export function readCsv(file) {
  return parseCsv(fs.readFileSync(file, 'utf8'));
}

// ------------------------------------------------- TEP tag reconciliation

/** Standard Downs-Vogel order of FE's human-readable TEP tags. */
export const TEP_TAG_ORDER = [
  'A Feed', 'D Feed', 'E Feed', 'A and C Feed', 'Recycle Flow', 'Reactor Feed Rate',
  'Reactor Pressure', 'Reactor Level', 'Reactor Temperature', 'Purge Rate',
  'Product Sep Temp', 'Product Sep Level', 'Product Sep Pressure', 'Product Sep Underflow',
  'Stripper Level', 'Stripper Pressure', 'Stripper Underflow', 'Stripper Temp',
  'Stripper Steam Flow', 'Compressor Work', 'Reactor Coolant Temp', 'Separator Coolant Temp',
  'Component A to Reactor', 'Component B to Reactor', 'Component C to Reactor',
  'Component D to Reactor', 'Component E to Reactor', 'Component F to Reactor',
  'Component A in Purge', 'Component B in Purge', 'Component C in Purge',
  'Component D in Purge', 'Component E in Purge', 'Component F in Purge',
  'Component G in Purge', 'Component H in Purge',
  'Component D in Product', 'Component E in Product', 'Component F in Product',
  'Component G in Product', 'Component H in Product',
  'D feed load', 'E feed load', 'A feed load', 'A and C feed load',
  'Compressor recycle valve', 'Purge valve', 'Separator liquid load', 'Stripper liquid load',
  'Stripper steam valve', 'Reactor coolant load', 'Condenser coolant load',
];

/** FE tag -> canonical XMEAS_n / XMV_n name. */
export const TEP_TAG_TO_CANON = (() => {
  const map = new Map();
  TEP_TAG_ORDER.forEach((tag, i) => {
    map.set(tag, i < 41 ? `XMEAS_${i + 1}` : `XMV_${i - 40}`);
  });
  return map;
})();

export function isTepCanonical(cols) {
  return cols.some((c) => /^XMEAS_\d+$/.test(c));
}

// -------------------------------------------------------- matrix extraction

/**
 * Load a CSV into { times, cols, X } where X is row-major Float64Array rows.
 * Offline / sparse-sampled columns are forward-filled then back-filled from the
 * first observation (process-measurement convention, same as baseline_pca.mjs);
 * fully non-numeric columns (timestamps) are dropped.
 */
export function loadMatrix(file) {
  const { header, rows } = readCsv(file);
  const colNames = [];
  const columns = [];
  for (let j = 0; j < header.length; j++) {
    const raw = rows.map((r) => (r[j] === '' || r[j] === undefined ? null : Number(r[j])));
    if (raw.every((v) => v === null || Number.isNaN(v))) continue;
    // forward-fill, then back-fill leading gaps
    let last = null;
    for (let i = 0; i < raw.length; i++) {
      if (raw[i] === null || Number.isNaN(raw[i])) raw[i] = last;
      else last = raw[i];
    }
    let first = null;
    for (let i = 0; i < raw.length; i++) if (raw[i] !== null) { first = raw[i]; break; }
    for (let i = 0; i < raw.length; i++) if (raw[i] === null) raw[i] = first ?? 0;
    columns.push(Float64Array.from(raw));
    colNames.push(header[j]);
  }
  const n = rows.length;
  const X = Array.from({ length: n }, (_, i) => Float64Array.from(columns.map((c) => c[i])));
  const timeIdx = header.findIndex((h) => /^(timestamp|time|datetime|date)$/i.test(h));
  const times = timeIdx >= 0 ? rows.map((r) => r[timeIdx]) : rows.map((_, i) => String(i + 1));
  return { header, colNames, times, X, n, m: colNames.length };
}

/** Cache key -> loaded matrix (datasets are read repeatedly across a sweep). */
const cache = new Map();
export function loadMatrixCached(file) {
  if (!cache.has(file)) cache.set(file, loadMatrix(file));
  return cache.get(file);
}

/** Load a benchmark case's dataset (sanitized case object required). */
export function loadCaseMatrix(caseDef) {
  const abs = caseDef.csv_abs || repoPath(caseDef.csv);
  if (!exists(abs)) throw new Error(`dataset missing: ${abs}`);
  return loadMatrixCached(abs);
}

// ---------------------------------------------- FaultExplainer training set

export const FE_FAULT_DESCRIPTIONS = [
  'Normal Operating Conditions',
  'IDV(1) A/C Feed Ratio, B Composition Constant (Stream 4) & Step',
  'IDV(2) B Composition, A/C Ratio Constant (Stream 4) & Step',
  'IDV(3) D Feed Temperature (Stream 2) & Step',
  'IDV(4) Reactor Cooling Water Inlet Temperature & Step',
  'IDV(5) Condenser Cooling Water Inlet Temperature & Step',
  'IDV(6) A Feed Loss (Stream 1) & Step',
  'IDV(7) C Header Pressure Loss - Reduced Availability (Stream 4) & Step',
  'IDV(8) A, B, C Feed Composition (Stream 4) & Random Variation',
  'IDV(9) D Feed Temperature (Stream 2) & Random Variation',
  'IDV(10) C Feed Temperature (Stream 4) & Random Variation',
  'IDV(11) Reactor Cooling Water Inlet Temperature & Random Variation',
  'IDV(12) Condenser Cooling Water Inlet Temperature & Random Variation',
  'IDV(13) Reaction Kinetics & Slow Drift',
  'IDV(14) Reactor Cooling Water Valve & Sticking',
  'IDV(15) Condenser Cooling Water Valve & Sticking',
];

/**
 * Load FaultExplainer's labelled TEP runs, re-keyed to canonical XMEAS/XMV
 * names so they line up with the benchmark case matrices.
 * Returns { X, y, labelNames, faultIndexToIdv, cols }.
 */
export function loadFeTrainingSet() {
  const dir = repoPath('baselines', 'FaultExplainer', 'backend', 'data');
  if (!exists(dir)) throw new Error(`FaultExplainer data not found: ${dir}`);

  const files = fs.readdirSync(dir).filter((f) => /^fault\d+\.csv$/.test(f));
  const X = [];
  const y = [];
  let canonCols = null;
  const labelNames = [];

  files
    .map((f) => ({ f, idx: Number(f.match(/(\d+)/)[1]) }))
    .sort((a, b) => a.idx - b.idx)
    .forEach(({ f, idx }) => {
      const { header, rows } = readCsv(`${dir}/${f}`);
      const tagIdx = header.map((h) => TEP_TAG_TO_CANON.get(h) ?? null);
      if (canonCols === null) canonCols = tagIdx.filter(Boolean);
      const keep = [];
      tagIdx.forEach((c, j) => { if (c) keep.push(j); });
      // FE files carry 500 rows; rows 0..19 are the start-up transient — the FE
      // protocol itself ignores the first 20 samples (analysis.py iloc[20:]).
      for (let i = 20; i < rows.length; i++) {
        const r = rows[i];
        const vals = keep.map((j) => Number(r[j]));
        if (vals.some((v) => Number.isNaN(v))) continue;
        X.push(Float64Array.from(vals));
        y.push(idx);
      }
      labelNames[idx] = FE_FAULT_DESCRIPTIONS[idx] || `fault${idx}`;
    });

  return { X, y, labelNames, cols: canonCols, source: 'baselines/FaultExplainer/backend/data' };
}

/**
 * Fault-window extraction.
 * TEP prepared files are 960 samples with the published onset at sample 161
 * (1-based) — the same convention baseline_pca.mjs uses.
 */
export function faultWindow(caseDef, n) {
  if (caseDef.dataset === 'tep') {
    const start = Math.min(160, Math.max(0, n - 1)); // 0-based index of row 161
    return { start, end: n };
  }
  return { start: 0, end: n };
}

/** Blind per-column anomaly digest — the same shape the pipeline brief uses. */
export function anomalyDigest(matrix, { topK = 8 } = {}) {
  const { X, colNames } = matrix;
  const n = X.length;
  const m = colNames.length;
  const stats = [];
  for (let j = 0; j < m; j++) {
    let s = 0;
    for (let i = 0; i < n; i++) s += X[i][j];
    const mu = s / n;
    let v = 0;
    for (let i = 0; i < n; i++) { const d = X[i][j] - mu; v += d * d; }
    const sd = Math.sqrt(v / Math.max(1, n - 1)) || 1e-12;
    let maxAbsZ = 0, beyond = 0;
    for (let i = 0; i < n; i++) {
      const z = Math.abs((X[i][j] - mu) / sd);
      if (z > maxAbsZ) maxAbsZ = z;
      if (z > 3) beyond++;
    }
    stats.push({ col: colNames[j], maxAbsZ, pctBeyond3: beyond / n });
  }
  stats.sort((a, b) => b.maxAbsZ - a.maxAbsZ);
  return stats.slice(0, topK).map((s) => ({
    col: s.col,
    max_abs_z: Number(s.maxAbsZ.toFixed(2)),
    pct_z3: Number(s.pctBeyond3.toFixed(4)),
  }));
}

/** Column index lookup by canonical name. */
export function colIndex(matrix, name) {
  return matrix.colNames.indexOf(name);
}
