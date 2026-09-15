#!/usr/bin/env node
// Check that the LLM digest now uses the same calibration split as the
// detectors, i.e. that a sustained fault is no longer masked by its own effect
// on the record-wide standard deviation.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createUpload, deleteUpload, uploadMatrix } from '../server/utils/uploads.mjs';
import { anomalyDigest, calibrationRows, topCorrelationPairs } from '../server/utils/dataset.mjs';

// Planted fault, same construction the verify script uses.
const rows = ['timestamp,InletTemp,CoolantFlow,VibrationRMS,Pressure'];
let seed = 12345;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
for (let i = 0; i < 600; i++) {
  const step = i >= 420 ? 1 : 0;
  rows.push([
    i,
    (80 + 2 * Math.sin(i / 40) + rnd() * 0.4).toFixed(4),
    (120 + 5 * Math.cos(i / 55) + rnd() * 1.2 - step * 18).toFixed(4),
    (1.5 + 0.1 * Math.sin(i / 12) + rnd() * 0.05 + step * 1.9).toFixed(4),
    (3.2 + 0.05 * Math.sin(i / 30) + rnd() * 0.02 - step * 0.35).toFixed(4),
  ].join(','));
}
const file = path.join(os.tmpdir(), `lab-digest-check-${Date.now()}.csv`);
fs.writeFileSync(file, rows.join('\n'), 'utf8');

const meta = createUpload(fs.readFileSync(file), 'digest-check.csv', { calibration_fraction: 0.3 });
const matrix = uploadMatrix(meta.upload_id);
const cut = calibrationRows(matrix.n, 0.3);

const whole = anomalyDigest(matrix, { topK: 4 });
const split = anomalyDigest(matrix, { topK: 4, referenceRows: cut });

console.log(`\nrows=${matrix.n}  calibration split=${cut}  monitored=${matrix.n - cut}\n`);
console.log('column'.padEnd(16), 'WHOLE-RECORD stats'.padEnd(34), 'CALIBRATION-SPLIT stats');
console.log('-'.repeat(88));
for (let i = 0; i < whole.length; i++) {
  const a = whole[i], b = split[i];
  console.log(
    String(a.col).padEnd(16),
    `max|z|=${String(a.max_abs_z).padEnd(7)} ${(a.pct_z3 * 100).toFixed(1)}% >3sigma`.padEnd(16),
    `max|z|=${String(b.max_abs_z).padEnd(7)} ${(b.pct_z3 * 100).toFixed(1)}% >3sigma`,
  );
}

console.log('\ncorrelations (split basis):', topCorrelationPairs(matrix, { topK: 3, referenceRows: cut }).join('  |  '));

const maxWhole = Math.max(...whole.map((d) => d.max_abs_z));
const maxSplit = Math.max(...split.map((d) => d.max_abs_z));
console.log(`\nlargest excursion seen by the model: whole-record=${maxWhole}  calibration-split=${maxSplit}`);
console.log(
  maxSplit > maxWhole
    ? '\nRESULT: the calibration split reveals excursions the whole-record basis masked — the LLM now sees the same baseline the detectors test against.'
    : '\nRESULT: no masking difference on this record.',
);

deleteUpload(meta.upload_id);
fs.rmSync(file, { force: true });
