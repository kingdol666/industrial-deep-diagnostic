#!/usr/bin/env node
/**
 * Backfill line memory from historical runs (REAL artifacts only).
 *
 * Scans workspace/diagnostic-runs/* for completed DB runs whose intent has an
 * extractor, extracts findings deterministically (no LLM), registers lines and
 * re-mines consensus. Safe to re-run: ingestion is idempotent (finding_id).
 *
 * Usage:
 *   node scripts/backfill-line-memory.mjs                 # all completed runs
 *   node scripts/backfill-line-memory.mjs --dry-run       # report only
 *   node scripts/backfill-line-memory.mjs --runs 202610310633486,202611021705070
 *   node scripts/backfill-line-memory.mjs --store-dir data/line_memory
 */
import { existsSync, readdirSync, statSync } from 'fs';
import { join, resolve, isAbsolute } from 'path';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';

import {
  defaultStoreDir, ingestRun, readRegistry, readConsensus,
} from '../.claude/shared/scripts/line_memory.mjs';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const RUNS_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
const EXTRACTABLE = new Set(['deep-diagnosis', 'stability-report', 'quick-screen', 'doe-analysis', 'experience-mining', 'optimizer-campaign']);

const args = process.argv.slice(2);
const arg = (name, def = null) => {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : def;
};
const has = (name) => args.includes('--' + name);
const dryRun = has('dry-run');
const storeDirArg = arg('store-dir', null);
const storeDir = storeDirArg
  ? (isAbsolute(storeDirArg) ? storeDirArg : resolve(storeDirArg))
  : defaultStoreDir();
const runFilter = (arg('runs') || '').split(',').map((s) => s.trim()).filter(Boolean);

const require = createRequire(join(PROJECT_ROOT, 'app', 'backend', 'package.json'));
const Database = require('better-sqlite3');
const db = new Database(join(PROJECT_ROOT, 'data', 'diagnostic.db'), { readonly: true });
const rows = db.prepare("SELECT run_id, analysis_intent, scene_name, status, completed_at, workspace_path, harness FROM diagnostic_runs WHERE status = 'completed'").all();
db.close();

const byPrefix = new Map();
for (const row of rows) {
  // Older runs use the timestamp prefix as run_id; newer ones use 8-char ids
  // with the dir recorded in workspace_path. Index both.
  byPrefix.set(row.run_id, row);
}

const dirs = existsSync(RUNS_DIR)
  ? readdirSync(RUNS_DIR).filter((n) => statSync(join(RUNS_DIR, n)).isDirectory())
  : [];
const targets = [];
for (const dirName of dirs) {
  const prefix = dirName.split('_')[0];
  if (runFilter.length && !runFilter.some((f) => dirName.startsWith(f) || prefix === f)) continue;
  const row = byPrefix.get(prefix) || rows.find((r) => r.workspace_path && r.workspace_path.replace(/\\/g, '/').endsWith('/' + dirName));
  if (!row) continue;
  if (!EXTRACTABLE.has(row.analysis_intent)) continue;
  // Mock-harness runs are test fixtures, not real production evidence.
  if (row.harness === 'mock') continue;
  targets.push({ dirName, runDir: join(RUNS_DIR, dirName), row, observedAt: row.completed_at || null });
}

console.log(`backfill: ${targets.length} completed run dir(s) matched; store=${storeDir}${dryRun ? ' [dry-run]' : ''}`);
let ingested = 0;
let skippedEmpty = 0;
for (const tgt of targets) {
  if (dryRun) {
    console.log('  would ingest', tgt.row.run_id, tgt.row.analysis_intent, tgt.dirName);
    continue;
  }
  try {
    const r = ingestRun({
      storeDir,
      runDir: tgt.runDir,
      runId: tgt.row.run_id,
      intent: tgt.row.analysis_intent,
      sceneKey: tgt.row.scene_name,
      sceneName: tgt.row.scene_name,
      observedAt: tgt.observedAt,
    });
    if (r.empty) { skippedEmpty += 1; continue; }
    ingested += 1;
    console.log(`  ${tgt.row.run_id} → line=${r.lineKey} added=${r.findings_added} skipped=${r.skipped} stats=${JSON.stringify(r.consensus && r.consensus.stats)}`);
  } catch (err) {
    console.log(`  ${tgt.row.run_id} FAILED: ${err.message}`);
  }
}

const reg = readRegistry(storeDir);
console.log(`\nlines: ${Object.keys(reg.lines).length} (ingested ${ingested}, empty ${skippedEmpty})`);
for (const [key, entry] of Object.entries(reg.lines)) {
  const c = readConsensus(storeDir, key);
  console.log(`  ${key} | ${entry.name} | ${c ? JSON.stringify(c.stats) : 'no consensus'}`);
}
