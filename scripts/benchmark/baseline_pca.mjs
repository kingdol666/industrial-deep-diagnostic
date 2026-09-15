#!/usr/bin/env node
// baseline_pca.mjs — classical PCA monitoring baseline (Chiang 2001 / Qin 2012).
//
// Protocol (fixed, published basis — NOT tuned per dataset):
//   train     = the dataset's normal-control scenario file (csv of the tier
//               entry with the same dataset and control == true)
//   model     = PCA on standardized control data, components = 95% cum. variance
//               (pure-JS Jacobi eigendecomposition; verified against the
//               published numpy-SVD numbers on all 12 scenarios)
//   stats     = Hotelling T2 + Q (SPE residual)
//   alarm     = 99th percentile of the TRAINING distribution (numpy-linear
//               quantile) — thresholds come from the control file, never from
//               the fault file being tested
//   detection = alarm rate over the scenario's FAULT window:
//                 tep  : data rows 161.. (published TEP d0X onset, 3-min sampling)
//                 other: whole file (prepared segments are already windowed)
//   rca       = top-3 SPE contribution variables (mean squared residual over
//               alarm rows, computed on standardized data)
//   columns   = offline / sparse-sampled columns are forward-filled then
//               back-filled from the first observation (process-measurement
//               convention: an offline assay value persists); fully
//               non-numeric columns (timestamps) are dropped
//
// Deterministic. Writes results/benchmark/baseline_pca_rca.json (same schema
// the paper's baseline table consumes). Usage:
//   node scripts/benchmark/baseline_pca.mjs [--tier scripts/benchmark/cases/benchmark_cases.json] [--out ...]

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const TEP_FAULT_START = 161; // 1-based data row; published TEP d0X protocol
const VAR_CUTOFF = 0.95;
const ALARM_Q = 0.99;
const TOP_K = 3;

const METHOD = 'PCA (normal-control training, 95% variance, T2+Q, 99th-pct alarm, SPE contribution top-3)';
const PUBLISHED_BASIS = ['chiang2001fault', 'qin2012survey'];

const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const tierPath = path.isAbsolute(opt('--tier', '')) ? opt('--tier', '') : path.join(ROOT, opt('--tier', 'scripts/benchmark/cases/benchmark_cases.json'));
const outPath = path.isAbsolute(opt('--out', '')) ? opt('--out', '') : path.join(ROOT, opt('--out', 'results/benchmark/baseline_pca_rca.json'));

// ---------- minimal quoted-CSV parser ----------
function parseCsv(file) {
  const text = fs.readFileSync(file, 'utf8');
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
  const header = rows.shift();
  return { header, rows };
}

// Numeric matrix + column names. Columns with at least one numeric value are
// kept: interior gaps forward-filled, leading gaps back-filled from the first
// observation. Columns with no numeric value at all (timestamps) are dropped.
function loadMatrix(file) {
  const { header, rows } = parseCsv(file);
  const cols = [];
  const columns = [];
  for (let j = 0; j < header.length; j++) {
    const raw = rows.map((r) => (r[j] === '' || r[j] === undefined ? null : Number(r[j])));
    if (raw.every((v) => v === null || Number.isNaN(v))) continue; // non-numeric column
    const filled = raw.map((v) => (v === null || Number.isNaN(v) ? null : v));
    let last = null, first = null;
    for (const v of filled) { if (v !== null) { first = v; break; } }
    for (let i = 0; i < filled.length; i++) {
      if (filled[i] !== null) last = filled[i];
      else filled[i] = last !== null ? last : first; // ffill; leading gaps bfill
    }
    cols.push(header[j]);
    columns.push(filled);
  }
  const mat = rows.map((_, i) => columns.map((c) => c[i]));
  if (!mat.length || !mat[0].length) throw new Error(`no usable numeric rows in ${file}`);
  return { mat, cols };
}

// ---------- linear algebra (pure JS, deterministic) ----------
// Symmetric-matrix eigenvalues/vectors via cyclic Jacobi rotations.
function jacobiEig(Ain, maxSweeps = 100) {
  const n = Ain.length;
  const A = Ain.map((r) => r.slice());
  const V = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < maxSweeps; sweep++) {
    let off = 0;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) off += A[p][q] * A[p][q];
    if (off < 1e-20) break;
    for (let p = 0; p < n; p++) {
      for (let q = p + 1; q < n; q++) {
        if (Math.abs(A[p][q]) < 1e-15) continue;
        const theta = (A[q][q] - A[p][p]) / (2 * A[p][q]);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1);
        const s = t * c;
        for (let k = 0; k < n; k++) {
          const akp = A[k][p], akq = A[k][q];
          A[k][p] = c * akp - s * akq;
          A[k][q] = s * akp + c * akq;
        }
        for (let k = 0; k < n; k++) {
          const apk = A[p][k], aqk = A[q][k];
          A[p][k] = c * apk - s * aqk;
          A[q][k] = s * apk + c * aqk;
        }
        for (let k = 0; k < n; k++) {
          const vkp = V[k][p], vkq = V[k][q];
          V[k][p] = c * vkp - s * vkq;
          V[k][q] = s * vkp + c * vkq;
        }
      }
    }
  }
  const eig = [];
  for (let i = 0; i < n; i++) eig.push({ val: Math.max(A[i][i], 0), vec: V.map((r) => r[i]) });
  eig.sort((a, b) => b.val - a.val);
  return eig;
}

function quantile(sorted, q) {
  // numpy.percentile 'linear' interpolation
  const pos = q * (sorted.length - 1);
  const lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

function pcaModel(train) {
  const m = train[0].length, n = train.length;
  const mu = new Array(m).fill(0), sd = new Array(m).fill(0);
  for (const r of train) for (let j = 0; j < m; j++) mu[j] += r[j] / n;
  for (const r of train) for (let j = 0; j < m; j++) sd[j] += (r[j] - mu[j]) ** 2 / n;
  for (let j = 0; j < m; j++) sd[j] = Math.sqrt(sd[j]) || 1;
  const Z = train.map((r) => r.map((v, j) => (v - mu[j]) / sd[j]));
  const C = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const r of Z) for (let i = 0; i < m; i++) for (let j = i; j < m; j++) C[i][j] += r[i] * r[j] / n;
  for (let i = 0; i < m; i++) for (let j = 0; j < i; j++) C[i][j] = C[j][i];
  const eig = jacobiEig(C);
  let cum = 0;
  const total = eig.reduce((acc, e) => acc + e.val, 0);
  let a = 0;
  for (const e of eig) { cum += e.val / total; a++; if (cum >= VAR_CUTOFF) break; }
  return { mu, sd, P: eig.slice(0, a).map((e) => e.vec), lam: eig.slice(0, a).map((e) => e.val) };
}

function statistics(mat, model) {
  const { mu, sd, P, lam } = model;
  const m = mu.length;
  return mat.map((r) => {
    const z = r.map((v, j) => (v - mu[j]) / sd[j]);
    const scores = P.map((pv) => pv.reduce((acc, pvj, j) => acc + pvj * z[j], 0));
    const recon = new Array(m).fill(0);
    for (let k = 0; k < P.length; k++) for (let j = 0; j < m; j++) recon[j] += scores[k] * P[k][j];
    const e = z.map((v, j) => v - recon[j]);
    let t2 = 0, spe = 0;
    for (let k = 0; k < scores.length; k++) t2 += (scores[k] * scores[k]) / lam[k];
    for (let j = 0; j < m; j++) spe += e[j] * e[j];
    return { t2, spe, e };
  });
}

// ---------- pipeline ----------
const tier = JSON.parse(fs.readFileSync(tierPath, 'utf8'));
const cases = tier.cases;
const controlRef = {};
for (const c of cases) if (c.control) controlRef[c.dataset] = path.join(ROOT, c.csv);

const scenarios = {};
for (const c of cases) {
  // train on the dataset's normal-control file; thresholds from ITS distribution
  const model = pcaModel(loadMatrix(controlRef[c.dataset]).mat);
  const trainStats = statistics(loadMatrix(controlRef[c.dataset]).mat, model);
  const thrT2 = quantile(trainStats.map((s) => s.t2).sort((x, y) => x - y), ALARM_Q);
  const thrSpe = quantile(trainStats.map((s) => s.spe).sort((x, y) => x - y), ALARM_Q);

  // test the scenario file
  const { mat, cols } = loadMatrix(path.join(ROOT, c.csv));
  const stats = statistics(mat, model);
  const start = c.dataset === 'tep' && !c.control ? TEP_FAULT_START - 1 : 0;
  const t2w = stats.slice(start).map((s) => s.t2).sort((x, y) => x - y);
  const spew = stats.slice(start).map((s) => s.spe).sort((x, y) => x - y);
  const rateT2 = t2w.filter((v) => v > thrT2).length / t2w.length;
  const rateSpe = spew.filter((v) => v > thrSpe).length / spew.length;

  const alarmRows = stats.slice(start).filter((s) => s.spe > thrSpe);
  const contrib = new Array(cols.length).fill(0);
  const basis = alarmRows.length ? alarmRows : stats.slice(start);
  for (const s of basis) for (let j = 0; j < cols.length; j++) contrib[j] += (s.e[j] * s.e[j]) / basis.length;
  const top3 = contrib.map((v, j) => [v, j]).sort((x, y) => y[0] - x[0]).slice(0, TOP_K).map(([, j]) => cols[j]);

  scenarios[c.case_id] = {
    dataset: c.dataset,
    control: !!c.control,
    detection_rate_T2: Math.round(rateT2 * 10000) / 10000,
    detection_rate_SPE: Math.round(rateSpe * 10000) / 10000,
    components_retained: model.P.length,
    top3_contribution_variables: top3,
  };
  const s = scenarios[c.case_id];
  console.log(`[pca] ${c.case_id.padEnd(28)} T2=${s.detection_rate_T2.toFixed(4)} SPE=${s.detection_rate_SPE.toFixed(4)} a=${s.components_retained} top3=${top3.join(',')}`);
}

const result = { method: METHOD, published_basis: PUBLISHED_BASIS, scenarios };
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(result, null, 1) + '\n');
console.log(`[pca] wrote ${path.relative(ROOT, outPath)}`);
