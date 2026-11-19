#!/usr/bin/env node
// build_manifest.mjs — Step 1 inspect: build 00_input/input_manifest.json
// (file inventory + SHA-256 + rows/columns) and fill run_config.data_path
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const runDir = process.argv[2];
if (!runDir) { console.error('usage: node build_manifest.mjs <run_dir>'); process.exit(2); }

const sha256 = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

const csvPath = path.join(runDir, '00_input', 'bearing_data.csv');
const ctxPath = path.join(runDir, '00_input', 'user_context.json');
const inspectPath = path.join(runDir, '02_inspect_raw.json');
const profile = JSON.parse(fs.readFileSync(inspectPath, 'utf8'));

const csvText = fs.readFileSync(csvPath, 'utf8');
const lines = csvText.trim().split(/\r?\n/);
const nRows = lines.length - 1;
const nCols = lines[0].split(',').length;

const manifest = {
  generated_at: new Date().toISOString(),
  run_dir: path.resolve(runDir),
  files: [
    {
      path: '00_input/bearing_data.csv',
      sha256: sha256(csvPath),
      bytes: fs.statSync(csvPath).size,
      format: 'csv',
      rows: nRows,
      columns: nCols,
      column_names: lines[0].split(','),
      role: 'primary_time_series'
    },
    {
      path: '00_input/user_context.json',
      sha256: sha256(ctxPath),
      bytes: fs.statSync(ctxPath).size,
      format: 'json',
      role: 'user_complaint'
    }
  ],
  time_column: profile.time_column || 'timestamp',
  sampling_interval: '2min',
  data_profile: {
    rows: profile.rows,
    columns: profile.columns,
    column_details: profile.column_details,
    missing_total: (profile.column_details || []).reduce((s, c) => s + (c.stats?.missing || 0), 0)
  }
};
fs.writeFileSync(path.join(runDir, '00_input', 'input_manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');

// Fingerprint contract (SKILL.md Step 1): write DATA_PATH back into run_config
const cfgPath = path.join(runDir, '00_input', 'run_config.json');
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
cfg.data_path = '00_input/bearing_data.csv';
cfg.user_objective = '轴承温度偏高,请查根因';
fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2), 'utf8');

console.log(JSON.stringify({
  input_manifest: '00_input/input_manifest.json',
  csv_sha256: manifest.files[0].sha256,
  rows: nRows,
  columns: nCols,
  run_config_data_path: cfg.data_path
}));
