#!/usr/bin/env node
// select-retest-case.mjs — benchmark pipeline step 3a: pick ONE scenario at
// RANDOM for an independent repeat diagnosis (verdict-consistency study).
//
// Why a script instead of "just look at the results": the consistency claim in
// a benchmark report is only defensible if the re-tested scenario was NOT
// hand-picked. This picks a scenario with a recorded, replayable RNG seed so a
// reviewer can (a) verify the draw was uniform over the declared pool and
// (b) reproduce the exact same draw.
//
// The old flow hard-coded tep_d14_reactor_valve_sticking (and even hard-coded
// its two run-dir timestamps) inside the report generator. That is selection
// bias, not a consistency test. This script replaces it.
//
// Output: results/benchmark/retest_selection.json  (append-only round history)
// Stdout: the selected case_id (last line, greppable)
//
// Usage:
//   node scripts/benchmark/select-retest-case.mjs                  # random draw, fresh seed
//   node scripts/benchmark/select-retest-case.mjs --seed 20260916  # reproducible draw
//   node scripts/benchmark/select-retest-case.mjs --faults-only    # pool = 9 fault scenarios
//   node scripts/benchmark/select-retest-case.mjs --only a,b       # restricted pool
//   node scripts/benchmark/select-retest-case.mjs --peek           # show last draw, do not draw

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RESULTS = path.join(ROOT, 'results', 'benchmark');
const TIER = path.join(ROOT, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json');
const SELECTION = path.join(RESULTS, 'retest_selection.json');

const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const has = (n) => args.includes(n);

/** mulberry32 — tiny deterministic PRNG; same seed => same draw, in any runtime. */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const tier = JSON.parse(fs.readFileSync(TIER, 'utf8'));

if (has('--peek')) {
  const rec = fs.existsSync(SELECTION) ? JSON.parse(fs.readFileSync(SELECTION, 'utf8')) : null;
  const last = rec?.rounds?.at(-1);
  if (!last) {
    console.error('[select-retest] no draw recorded yet');
    process.exit(2);
  }
  console.log(JSON.stringify(last, null, 1));
  console.log(last.case_id);
  process.exit(0);
}

// ---- pool ----
let pool = tier.cases.map((c) => ({ case_id: c.case_id, dataset: c.dataset, control: !!c.control }));
const only = opt('--only', '').split(',').map((s) => s.trim()).filter(Boolean);
if (only.length) pool = pool.filter((c) => only.includes(c.case_id));
if (has('--faults-only')) pool = pool.filter((c) => !c.control);
if (has('--pool-nonce')) { /* reserved */ }
if (!pool.length) {
  console.error('[select-retest] empty pool — check --only / --faults-only');
  process.exit(2);
}

// ---- seed ----
const seedArg = opt('--seed', '');
const seed = seedArg !== '' ? Number(seedArg) : (Date.now() ^ (process.pid << 16)) >>> 0;
if (!Number.isFinite(seed)) {
  console.error(`[select-retest] --seed must be numeric, got ${seedArg}`);
  process.exit(2);
}

// ---- uniform draw ----
const rnd = mulberry32(seed);
const u = rnd();                       // single uniform in [0,1)
const idx = Math.floor(u * pool.length);
const picked = pool[idx];

// ---- append-only history ----
fs.mkdirSync(RESULTS, { recursive: true });
const rec = fs.existsSync(SELECTION) ? JSON.parse(fs.readFileSync(SELECTION, 'utf8')) : { rounds: [] };
const round = {
  round: rec.rounds.length + 1,
  selected_at: new Date().toISOString(),
  rng: 'mulberry32',
  seed,
  uniform_draw: Number(u.toFixed(9)),
  pool_size: pool.length,
  pool: pool.map((c) => c.case_id),
  pool_filter: has('--faults-only') ? 'faults-only' : only.length ? 'explicit-list' : 'all-12',
  index: idx,
  case_id: picked.case_id,
  dataset: picked.dataset,
  control: picked.control,
  // reproducibility contract — what the executing agent must do next
  contract: [
    `Re-run the FULL skill://industrial-analysis-auto pipeline (Steps 2-9) for ${picked.case_id} in a FRESH run dir.`,
    'Never copy artifacts between run dirs; never re-use the canonical run dir as a source of truth.',
    'Then: node scripts/benchmark/consistency-audit.mjs --case ' + picked.case_id,
  ],
};
rec.rounds.push(round);
rec.last = round;
fs.writeFileSync(SELECTION, JSON.stringify(rec, null, 1) + '\n');

console.log(`[select-retest] round ${round.round} · seed=${seed} · pool=${pool.length} · u=${round.uniform_draw} → index ${idx}`);
console.log(`[select-retest] SELECTED: ${picked.case_id} (${picked.dataset}${picked.control ? ', control' : ''})`);
console.log(`[select-retest] recorded → ${path.relative(ROOT, SELECTION)}`);
console.log(picked.case_id);
