#!/usr/bin/env node
// verify-pca.mjs — self-verification gate for the lab's PCA reimplementation.
//
// Compares the lab's pca-t2-spe output against the repository's ARCHIVED
// results/benchmark/baseline_pca_rca.json (produced by the independent
// scripts/benchmark/baseline_pca.mjs). Detection rates and retained-component
// counts must match EXACTLY; the top-3 contribution variables must match as a
// set. A mismatch means the reproduction is not faithful and the lab must not
// report PCA numbers.

import { readFileSync, existsSync } from 'node:fs';
import { loadCasesRaw, loadCaseForAlgorithm, PCA_BASELINE } from '../server/utils/paths.mjs';
import { buildContext } from '../server/utils/algorithms/_shared.mjs';
import * as pca from '../server/utils/algorithms/pca.mjs';

const archivedPath = PCA_BASELINE();
if (!existsSync(archivedPath)) {
  console.error(`[verify-pca] archived baseline not found: ${archivedPath}`);
  process.exit(2);
}
const archived = JSON.parse(readFileSync(archivedPath, 'utf8')).scenarios;

let pass = 0, fail = 0;
const rows = [];

for (const c of loadCasesRaw()) {
  const ref = archived[c.case_id];
  if (!ref) {
    rows.push({ case_id: c.case_id, status: 'NO_ARCHIVE' });
    continue;
  }
  const ctx = buildContext(loadCaseForAlgorithm(c.case_id));
  const out = await pca.run(ctx);

  const checks = {
    T2: Math.abs(out.detection.T2.detection_rate - ref.detection_rate_T2) < 1e-4,
    SPE: Math.abs(out.detection.SPE.detection_rate - ref.detection_rate_SPE) < 1e-4,
    components: out.detection.components_retained === ref.components_retained,
    top3: sameSet(out.variable_top3.slice(0, 3), ref.top3_contribution_variables),
  };
  const ok = Object.values(checks).every(Boolean);
  ok ? pass++ : fail++;
  rows.push({
    case_id: c.case_id,
    status: ok ? 'PASS' : 'FAIL',
    checks,
    lab: {
      T2: out.detection.T2.detection_rate,
      SPE: out.detection.SPE.detection_rate,
      a: out.detection.components_retained,
      top3: out.variable_top3.slice(0, 3),
    },
    archived: {
      T2: ref.detection_rate_T2,
      SPE: ref.detection_rate_SPE,
      a: ref.components_retained,
      top3: ref.top3_contribution_variables,
    },
  });
}

function sameSet(a = [], b = []) {
  return a.length === b.length && [...a].sort().join('|') === [...b].sort().join('|');
}

const pad = (s, n) => String(s).padEnd(n);
console.log('\n=== PCA reproduction gate (lab vs. archived baseline_pca_rca.json) ===\n');
console.log(pad('case_id', 30), pad('status', 8), pad('T2 lab/arch', 20), pad('SPE lab/arch', 22), 'a');
console.log('-'.repeat(96));
for (const r of rows) {
  if (r.status === 'NO_ARCHIVE') {
    console.log(pad(r.case_id, 30), pad('N/A', 8));
    continue;
  }
  const t2 = `${r.lab.T2.toFixed(4)}/${r.archived.T2.toFixed(4)}`;
  const spe = `${r.lab.SPE.toFixed(4)}/${r.archived.SPE.toFixed(4)}`;
  console.log(pad(r.case_id, 30), pad(r.status, 8), pad(t2, 20), pad(spe, 22), `${r.lab.a}/${r.archived.a}`);
  if (r.status === 'FAIL') {
    console.log('   checks:', JSON.stringify(r.checks));
    console.log('   lab top3     :', r.lab.top3.join(','));
    console.log('   archived top3:', r.archived.top3.join(','));
  }
}
console.log('-'.repeat(96));
console.log(`PASS ${pass}  FAIL ${fail}`);
process.exit(fail === 0 ? 0 : 1);
