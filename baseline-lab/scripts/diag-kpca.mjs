#!/usr/bin/env node
// Diagnose the KPCA statistics: compare T² and SPE on the reference's own
// training subsample, on held-out reference rows, and on fault files, and show
// whether the kernel is in a responsive regime or has saturated.
//
// Also prints the per-fault-window k(x, x_i) mean, which is the diagnostic for
// kernel saturation: when it collapses toward 0 every reference kernel value has
// underflowed and SPE is pinned at its saturation constant k̃(x,x).

import { colStats, standardize, quantile, mean } from '../server/utils/linalg.mjs';
import { loadMatrixCached } from '../server/utils/dataset.mjs';
import { repoPath } from '../server/utils/paths.mjs';
import { fitKpca, kpcaRow, subsampleIndex, selectGamma, MAX_TRAIN } from '../server/utils/algorithms/kpca.mjs';

const ref = loadMatrixCached(repoPath('data', 'benchmark', 'prepared', 'tep', 'd00_te.csv'));

const { mu, sd } = colStats(ref.X, 0);
const idx = subsampleIndex(ref.X.length, MAX_TRAIN);
const train = standardize(idx.map((i) => ref.X[i]), mu, sd);

const sel = selectGamma(train);
console.log(`reference rows=${ref.X.length}  train subsample=${idx.length}  m=${ref.m}`);
console.log(`gamma = 1/(2*sigma2) = ${sel.gamma.toFixed(6)}   sigma2 (median NN sq dist) = ${sel.sigma2.toFixed(3)}`);
console.log(`gamma rule          : ${sel.rule}`);
console.log(`kernel off-diag mean: ${sel.offMean.toFixed(4)}   (responsiveness guard trips at >= 0.5)`);

const model = fitKpca(train);
console.log(`a=${model.a}  retention="${model.retention_rule}"  mean(lambda)=${model.eigenvalue_trace_mean}`);
console.log(`eigenvalues (top 6): ${model.lam.slice(0, 6).map((v) => v.toExponential(3)).join(', ')}`);
console.log(`eigenvalues (last 3): ${model.lam.slice(-3).map((v) => v.toExponential(3)).join(', ')}`);

const refZ = standardize(ref.X, mu, sd);
const inTrain = new Set(idx);
const heldT2 = [], heldSpe = [];
const trainT2 = [], trainSpe = [];
const refK = [];
for (let i = 0; i < refZ.length; i++) {
  const r = kpcaRow(refZ[i], model);
  let km = 0;
  for (let q = 0; q < r.k.length; q++) km += r.k[q];
  km /= r.k.length;
  refK.push(km);
  (inTrain.has(i) ? trainT2 : heldT2).push(r.t2);
  (inTrain.has(i) ? trainSpe : heldSpe).push(r.spe);
}
const thrT2 = quantile(heldT2.slice().sort((a, b) => a - b), 0.99);
const thrSpe = quantile(heldSpe.slice().sort((a, b) => a - b), 0.99);

function stats(name, arr, fmt = (v) => v.toExponential(3)) {
  const s = arr.slice().sort((a, b) => a - b);
  console.log(
    `${name.padEnd(30)} n=${String(arr.length).padEnd(5)} mean=${fmt(mean(arr)).padEnd(11)} p50=${fmt(quantile(s, 0.5)).padEnd(11)} p99=${fmt(quantile(s, 0.99)).padEnd(11)} max=${fmt(Math.max(...arr))}`,
  );
}

const fixed = (v) => v.toFixed(4);
console.log('\n--- reference (d00) ---');
stats('REF in-training T2', trainT2, fixed);
stats('REF held-out  T2', heldT2, fixed);
stats('REF in-training SPE', trainSpe, fixed);
stats('REF held-out  SPE', heldSpe, fixed);
stats('REF mean k(x,x_i)', refK);
console.log(`held-out reference 99th-percentile limits: T2=${thrT2.toFixed(4)}  SPE=${thrSpe.toFixed(4)}`);

const faults = ['d01_te.csv', 'd03_te.csv', 'd04_te.csv', 'd07_te.csv', 'd11_te.csv', 'd14_te.csv'];
console.log('\n--- fault files (window = rows 161+) ---');
for (const f of faults) {
  const M = loadMatrixCached(repoPath('data', 'benchmark', 'prepared', 'tep', f));
  const Z = standardize(M.X, mu, sd);
  const win = Z.slice(160);
  const t2 = [], spe = [], km = [];
  for (const z of win) {
    const r = kpcaRow(z, model);
    let k = 0;
    for (let q = 0; q < r.k.length; q++) k += r.k[q];
    km.push(k / r.k.length);
    t2.push(r.t2);
    spe.push(r.spe);
  }
  const q = (a, p) => quantile(a.slice().sort((x, y) => x - y), p);
  const rateT2 = t2.filter((v) => v > thrT2).length / t2.length;
  const rateSpe = spe.filter((v) => v > thrSpe).length / spe.length;
  console.log(
    `${f.padEnd(12)} meanK=${mean(km).toExponential(2)}  ` +
    `T2 p50=${q(t2, 0.5).toFixed(4)} p99=${q(t2, 0.99).toFixed(4)} max=${Math.max(...t2).toFixed(4)} rate=${(rateT2 * 100).toFixed(2)}%  |  ` +
    `SPE p50=${q(spe, 0.5).toFixed(4)} p99=${q(spe, 0.99).toFixed(4)} max=${Math.max(...spe).toFixed(4)} rate=${(rateSpe * 100).toFixed(2)}%`,
  );
}
console.log('\nmeanK near the reference off-diagonal mean => responsive kernel;');
console.log('meanK << off-diagonal mean => the point is outside the kernel support and SPE is saturated.');
