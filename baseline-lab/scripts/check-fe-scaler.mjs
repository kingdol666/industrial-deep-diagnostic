#!/usr/bin/env node
// check-fe-scaler.mjs — fidelity check for the FaultExplainer protocol replica.
//
// FE's backend/stats/features_mean_std.csv was produced by sklearn's
// StandardScaler fitted on fault0.csv (the normal run). Reproducing those exact
// numbers pins down the two conventions that matter: the variance divisor
// (ddof) and the row set. If our scaler matches FE's stored file, the T²
// threshold and contributions that depend on it are faithful too.

import { readCsv, TEP_TAG_ORDER } from '../server/utils/dataset.mjs';
import { repoPath } from '../server/utils/paths.mjs';
import { mean } from '../server/utils/linalg.mjs';

const csvPath = repoPath('baselines', 'FaultExplainer', 'backend', 'data', 'fault0.csv');
const statsPath = repoPath('baselines', 'FaultExplainer', 'backend', 'stats', 'features_mean_std.csv');

const { header, rows } = readCsv(csvPath);
const stored = readCsv(statsPath);
const storedRows = stored.rows.map((r) => ({ feature: r[0], mean: Number(r[1]), std: Number(r[2]) }));

function variance(values, ddof) {
  const n = values.length;
  const mu = mean(values);
  let s = 0;
  for (const v of values) s += (v - mu) * (v - mu);
  return s / (n - ddof);
}

const rowSets = {
  all_500: rows.map((_, i) => i),
  drop_first_20: rows.map((_, i) => i).filter((i) => i >= 20),
};

console.log('feature'.padEnd(24), 'stored_mean'.padEnd(16), 'mu(all500)'.padEnd(16), 'match', ' std_ddof0'.padEnd(12), 'std_ddof1'.padEnd(12), 'stored_std');
console.log('-'.repeat(120));

let exact = 0, total = 0;
const summary = {};
for (const target of storedRows.slice(0, 12)) {
  const j = header.indexOf(target.feature);
  if (j < 0) { console.log(target.feature.padEnd(24), 'COLUMN NOT FOUND'); continue; }
  const all = rows.map((r) => Number(r[j]));
  const cut = all.slice(20);
  const muAll = mean(all);
  const muCut = mean(cut);
  const s0 = Math.sqrt(variance(all, 0));
  const s1 = Math.sqrt(variance(all, 1));
  const s0c = Math.sqrt(variance(cut, 0));
  const s1c = Math.sqrt(variance(cut, 1));
  const best = [
    ['all/ddof0', muAll, s0], ['all/ddof1', muAll, s1],
    ['cut20/ddof0', muCut, s0c], ['cut20/ddof1', muCut, s1c],
  ].map(([k, m, s]) => ({ k, m, s, err: Math.abs(s - target.std) + Math.abs(m - target.mean) }))
    .sort((a, b) => a.err - b.err)[0];

  total++;
  const ok = best.err < 1e-6;
  if (ok) exact++;
  summary[best.k] = (summary[best.k] || 0) + (ok ? 1 : 0);

  console.log(
    target.feature.padEnd(24),
    target.mean.toFixed(8).padEnd(16),
    muAll.toFixed(8).padEnd(16),
    (Math.abs(muAll - target.mean) < 1e-9 ? 'mu=OK' : 'mu=DIFF').padEnd(9),
    s0.toFixed(8).padEnd(12),
    s1.toFixed(8).padEnd(12),
    target.std.toFixed(8),
  );
}

console.log('-'.repeat(120));
console.log('best-matching convention per feature:', JSON.stringify(summary));
console.log(`exact matches: ${exact}/${total}`);
console.log(
  exact === total
    ? '\nRESULT: the FE scaler convention is pinned — replica can claim fidelity.'
    : '\nRESULT: no single convention matches exactly; inspect before claiming fidelity.',
);
process.exit(exact === total ? 0 : 1);
