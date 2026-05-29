#!/usr/bin/env node
// setup.mjs — Create run directory structure for a diagnostic session
// Usage: node setup.mjs --name <run_name> [--base-dir ./workspace/diagnostic-runs]

import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const nameIdx = args.indexOf('--name');
const baseIdx = args.indexOf('--base-dir');

const name = nameIdx !== -1 ? args[nameIdx + 1] : `run_${Date.now()}`;
const baseDir = baseIdx !== -1 ? args[baseIdx + 1] : './workspace/diagnostic-runs';

const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 15);
const runDir = path.join(baseDir, `${timestamp}_${name}`);

const subdirs = [
  '00_input',
  '01_ontology',
  '02_processed',
  '03_figures',
  '04_diagnostics',
  '05_review',
  '06_scripts',
];

fs.mkdirSync(runDir, { recursive: true });
for (const sub of subdirs) {
  fs.mkdirSync(path.join(runDir, sub), { recursive: true });
}

const manifest = {
  run_id: `${timestamp}_${name}`,
  created: new Date().toISOString(),
  run_dir: path.resolve(runDir),
  status: 'initialized',
  steps: subdirs.map((s, i) => ({ dir: s, index: i, status: 'pending' })),
};

fs.writeFileSync(path.join(runDir, 'run_manifest.json'), JSON.stringify(manifest, null, 2));

// Output the run directory path for the caller
console.log(JSON.stringify({ run_dir: path.resolve(runDir), manifest }));
