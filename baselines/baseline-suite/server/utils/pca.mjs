// pca.mjs — the suite's own classical PCA monitoring engine (deterministic).
// Same published protocol as scripts/benchmark/baseline_pca.mjs (Chiang 2001 /
// Qin 2012): normal-control training, 95% cumulative variance, T2 + Q(SPE),
// alarm = 99th percentile of the TRAINING distribution, detection over the
// scenario fault window (TEP from row 161; other datasets: whole file),
// diagnosis = top-3 SPE contribution variables. Pure-JS Jacobi eigendecomposition.
import fs from 'node:fs';
import path from 'node:path';
import { REPO } from './repo.mjs';

export const TEP_FAULT_START = 161;
const VAR_CUTOFF = 0.95;
const ALARM_Q = 0.99;
const TOP_K = 3;

function parseCsv(file) {
  const text = fs.readFileSync(file, 'utf8');  const rows = [];
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

export function loadMatrix(relCsv) {
  const { header, rows } = parseCsv(path.join(REPO, relCsv));
  const cols = [], columns = [];
  for (let j = 0; j < header.length; j++) {
    const raw = rows.map((r) => (r[j] === '' || r[j] === undefined ? null : Number(r[j])));
    if (raw.every((v) => v === null || Number.isNaN(v))) continue;
    const filled = raw.map((v) => (v === null || Number.isNaN(v) ? null : v)); // unparseable cells ffill like gaps
    let last = null, first = null;
    for (const v of filled) { if (v !== null) { first = v; break; } }
    for (let i = 0; i < filled.length; i++) {
      if (filled[i] !== null) last = filled[i];
      else filled[i] = last !== null ? last : first;
    }
    cols.push(header[j]);
    columns.push(filled);
  }
  return { mat: rows.map((_, i) => columns.map((c) => c[i])), cols };
}

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
        for (let k = 0; k < n; k++) { const akp = A[k][p], akq = A[k][q]; A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq; }
        for (let k = 0; k < n; k++) { const apk = A[p][k], aqk = A[q][k]; A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk; }
        for (let k = 0; k < n; k++) { const vkp = V[k][p], vkq = V[k][q]; V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq; }
      }
    }
  }
  const eig = [];
  for (let i = 0; i < n; i++) eig.push({ val: Math.max(A[i][i], 0), vec: V.map((r) => r[i]) });
  eig.sort((a, b) => b.val - a.val);
  return eig;
}

function quantile(sorted, q) {
  const pos = q * (sorted.length - 1);
  const lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function pcaModel(train, cutoff = VAR_CUTOFF) {
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
  for (const e of eig) { cum += e.val / total; a++; if (cum >= cutoff) break; }
  return { mu, sd, P: eig.slice(0, a).map((e) => e.vec), lam: eig.slice(0, a).map((e) => e.val), a, m };
}

export function statistics(mat, model) {
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
    return { t2, spe, e, z, scores };
  });
}

/** Classical PCA arm — detection rates + top-3 SPE contribution variables. */
export function runPcaArm(routing) {
  const controlRouting = scenarioControl(routing.dataset);
  const model = pcaModel(loadMatrix(controlRouting.csv).mat);
  const trainStats = statistics(loadMatrix(controlRouting.csv).mat, model);
  const thrT2 = quantile(trainStats.map((s) => s.t2).sort((x, y) => x - y), ALARM_Q);
  const thrSpe = quantile(trainStats.map((s) => s.spe).sort((x, y) => x - y), ALARM_Q);

  const { mat, cols } = loadMatrix(routing.csv);
  const stats = statistics(mat, model);
  const start = routing.dataset === 'tep' && !routing.control ? TEP_FAULT_START - 1 : 0;
  const t2w = stats.slice(start).map((s) => s.t2).sort((x, y) => x - y);
  const spew = stats.slice(start).map((s) => s.spe).sort((x, y) => x - y);
  const rateT2 = t2w.filter((v) => v > thrT2).length / t2w.length;
  const rateSpe = spew.filter((v) => v > thrSpe).length / spew.length;
  const alarmRows = stats.slice(start).filter((s) => s.spe > thrSpe);
  const basis = alarmRows.length ? alarmRows : stats.slice(start);
  const contrib = new Array(cols.length).fill(0);
  for (const s of basis) for (let j = 0; j < cols.length; j++) contrib[j] += (s.e[j] * s.e[j]) / basis.length;
  const top3 = contrib.map((v, j) => [v, j]).sort((x, y) => y[0] - x[0]).slice(0, TOP_K)
    .map(([v, j]) => ({ variable: cols[j], mean_squared_residual: +v.toFixed(4) }));
  return {
    arm: 'pca-classical',
    method: 'PCA (normal-control training, 95% variance, T2+Q, 99th-pct training alarm, SPE top-3)',
    detection: {
      window: routing.dataset === 'tep' && !routing.control ? `rows ${TEP_FAULT_START}..${stats.length}` : `rows 1..${stats.length}`,
      detection_rate_T2: Math.round(rateT2 * 10000) / 10000,
      detection_rate_SPE: Math.round(rateSpe * 10000) / 10000,
      threshold_T2: +thrT2.toFixed(3),
      threshold_SPE: +thrSpe.toFixed(3),
      components_retained: model.a,
    },
    diagnosis: { top3_contribution_variables: top3, mechanism_verdict: null, note: 'classical PCA outputs variable contributions only — no mechanism verdict, no confidence, no evidence state' },
  };
}

function scenarioControl(dataset) {
  // routing table re-scan (control entry per dataset) — truth-free fields only
  const tier = JSON.parse(fs.readFileSync(path.join(REPO, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json'), 'utf8'));
  const hit = tier.cases.find((c) => c.dataset === dataset && c.control);
  if (!hit) throw new Error(`no control scenario for dataset ${dataset}`);
  return { csv: hit.csv, case_id: hit.case_id };
}
export { scenarioControl };
