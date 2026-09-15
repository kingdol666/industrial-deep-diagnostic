#!/usr/bin/env node
// verify-fe.mjs — fidelity gate for the FaultExplainer protocol replica.
//
// FaultExplainer committed its own processed outputs to
// baselines/FaultExplainer/frontend/public/fault*.csv. Each file carries the raw
// 52 TEP columns PLUS the pipeline's own `t2_stat`, `anomaly` and 52
// `t2_<feature>` contribution columns. Feeding the raw columns back through
// this lab's reimplementation must reproduce those numbers.
//
// Pass criteria (per file):
//   - t2_stat      : max relative deviation < 1e-4
//   - anomaly      : 100% agreement on the boolean flag
//   - contributions: mean relative deviation < 1e-3
//   - trigger index: identical (FE's k-consecutive rule)
//
// A failure means the replica is NOT faithful and must not be reported as
// FaultExplainer's protocol.

import fs from 'node:fs';
import { repoPath, exists } from '../server/utils/paths.mjs';
import { readCsv, TEP_TAG_ORDER } from '../server/utils/dataset.mjs';
import { fitFeModel, feStatistics, findTrigger, FE_CONFIG } from '../server/utils/algorithms/fe-official.mjs';

const PUB = repoPath('baselines', 'FaultExplainer', 'frontend', 'public');
if (!exists(PUB)) {
  console.error(`[verify-fe] FE processed outputs not found: ${PUB}`);
  process.exit(2);
}

const files = process.argv.slice(2).filter((a) => !a.startsWith('-'));
const targets = files.length
  ? files
  : fs.readdirSync(PUB).filter((f) => /^fault\d+\.csv$/.test(f)).sort((a, b) => {
      const n = (s) => Number(s.match(/\d+/)[0]);
      return n(a) - n(b);
    });

const model = fitFeModel();
console.log('=== FaultExplainer protocol replica — fidelity gate ===\n');
console.log(`training file : ${model.trainingFile.replace(/\\/g, '/')}`);
console.log(`scaler rows   : ${model.n}   components retained: ${model.a}   T² limit: ${model.t2Threshold.toFixed(6)}`);
console.log(`trigger rule  : ${FE_CONFIG.fault_trigger_consecutive_step} consecutive anomalous samples\n`);

const hdr = ['file', 'rows', 't2_maxrelerr', 'anom_match', 'contrib_meanrelerr', 'trigger', 'verdict'];
console.log(hdr.map((h, i) => h.padEnd([10, 6, 15, 13, 20, 9, 8][i])).join(''));
console.log('-'.repeat(84));

let pass = 0, fail = 0;
const failures = [];

for (const f of targets) {
  const { header, rows } = readCsv(`${PUB}/${f}`);
  const rawIdx = TEP_TAG_ORDER.map((t) => header.indexOf(t));
  const t2Idx = header.indexOf('t2_stat');
  const anomIdx = header.indexOf('anomaly');
  const contribIdx = TEP_TAG_ORDER.map((t) => header.indexOf(`t2_${t}`));

  if (rawIdx.some((i) => i < 0) || t2Idx < 0 || anomIdx < 0) {
    console.log(`${f.padEnd(10)} SKIP (missing expected columns)`);
    continue;
  }

  const X = rows.map((r) => rawIdx.map((j) => Number(r[j])));
  const refT2 = rows.map((r) => Number(r[t2Idx]));
  const refAnom = rows.map((r) => String(r[anomIdx]).toLowerCase() === 'true' || r[anomIdx] === '1' || r[anomIdx] === 'True');
  const refContrib = rows.map((r) => contribIdx.map((j) => (j >= 0 ? Number(r[j]) : null)));

  const stats = feStatistics(X, model);

  // t2_stat agreement
  let maxRel = 0;
  for (let i = 0; i < stats.length; i++) {
    const d = Math.abs(stats[i].t2 - refT2[i]);
    const scale = Math.max(Math.abs(refT2[i]), 1e-9);
    maxRel = Math.max(maxRel, d / scale);
  }

  // anomaly agreement
  const anomMatch = stats.filter((s, i) => s.anomaly === refAnom[i]).length;

  // contribution agreement (only where a reference value exists)
  let num = 0, den = 0, pairs = 0;
  for (let i = 0; i < stats.length; i++) {
    for (let j = 0; j < contribIdx.length; j++) {
      const ref = refContrib[i][j];
      if (ref === null || Number.isNaN(ref)) continue;
      num += Math.abs(stats[i].contrib[j] - ref);
      den += Math.abs(ref);
      pairs++;
    }
  }
  const contribRel = den > 0 ? num / den : 0;

  const trigger = findTrigger(stats, FE_CONFIG.fault_trigger_consecutive_step);
  const refTrigger = findTrigger(
    refT2.map((t, i) => ({ t2: t, anomaly: refAnom[i] })),
    FE_CONFIG.fault_trigger_consecutive_step,
  );

  const ok =
    maxRel < 1e-4 &&
    anomMatch === stats.length &&
    contribRel < 1e-3 &&
    trigger === refTrigger;
  ok ? pass++ : fail++;
  if (!ok) failures.push({ file: f, maxRel, anomMatch, n: stats.length, contribRel, trigger, refTrigger });

  const row = [
    f.padEnd(10),
    String(stats.length).padEnd(6),
    maxRel.toExponential(2).padEnd(15),
    `${anomMatch}/${stats.length}`.padEnd(13),
    contribRel.toExponential(2).padEnd(20),
    `${trigger}/${refTrigger}`.padEnd(9),
    ok ? 'PASS' : 'FAIL',
  ];
  console.log(row.join(''));
}

console.log('-'.repeat(84));
console.log(`PASS ${pass}  FAIL ${fail}   (contribution pairs compared: all 52 features × all rows)`);

if (failures.length) {
  console.log('\nfailures:');
  for (const f of failures) {
    console.log(`  ${f.file}: t2_maxrelerr=${f.maxRel.toExponential(3)} anom=${f.anomMatch}/${f.n} contrib_rel=${f.contribRel.toExponential(3)} trigger=${f.trigger} (FE: ${f.refTrigger})`);
  }
}
process.exit(fail === 0 ? 0 : 1);
