#!/usr/bin/env node
// test-shared-scripts.mjs — safety tests for the shared pipeline scripts.
//
// Covers the 2026-10-17 hardening of three shared scripts:
//
//   [1] ontology_store.mjs — cross-process write lock
//       Two concurrent node processes each publish N=25 versions into the SAME
//       scene of a TEMP store (ONTOLOGY_STORE_DIR). Asserted: every call returns
//       a version, the union of returned versions is exactly {1..50} (no lost
//       update, no duplicate nextVersion), index.json parses, every indexed
//       version has its ontology.json, the scene dir matches the index (prune
//       policy: index keeps the newest MAX_VERSIONS_PER_SCENE non-endorsed
//       versions), and no .index.lock is left behind.
//       [1b] a fresh lock file blocks a writer until it is released (the lock is
//            actually honored, not decorative).
//
//   [2] ontology_store.mjs — corrupt index.json
//       A corrupt/non-array index must NOT be silently read as an empty store:
//       readIndex backs the bad file up to index.json.corrupt-<ts> and throws
//       OntologyStoreCorruptError (with backupPath); a mutator call throws too
//       and leaves the on-disk index byte-identical (nothing zeroed).
//
//   [3] append-pipeline-event.mjs — corrupt run_manifest.json
//       With a corrupt manifest but a valid .pipeline_events.jsonl (including one
//       deliberately corrupt line), the CLI rebuilds the manifest from the event
//       log (rebuilt_from_events: true, repair counters from repair_spawn events,
//       completed/in_progress steps from the log), backs up the corrupt manifest
//       as run_manifest.json.corrupt-<ts>, appends the new event, and writes the
//       manifest atomically. If the JSONL is missing too, the hard exit remains
//       and names both failures.
//
//   [4] validate.mjs — draft-07 null semantics
//       enum without null rejects null; enum listing null accepts it; `nullable:
//       true` is a real escape hatch; type/const/oneOf/anyOf/if-then-else/allOf/
//       $ref/items behavior for null is unchanged.
//
// Usage: node scripts/test-shared-scripts.mjs
// Exit 0 = all PASS, 1 = any FAIL. Temp stores/run dirs live under os.tmpdir().

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(import.meta.dirname, '..');
const ONTOLOGY_STORE = path.join(ROOT, '.claude/shared/scripts/ontology_store.mjs');
const APPEND_EVENT = path.join(ROOT, '.claude/shared/scripts/append-pipeline-event.mjs');
const VALIDATE = path.join(ROOT, '.claude/shared/scripts/validate.mjs');
const STORE_URL = pathToFileURL(ONTOLOGY_STORE).href;
const NODE = process.execPath;

const CONCURRENCY = 25;   // publishes per writer process
const SCENE = 'concurrency_probe';
const tmpDirs = [];

let pass = 0;
let fail = 0;
const failures = [];

function check(name, ok, detail = '') {
  if (ok) { pass += 1; console.log(`  PASS: ${name}`); }
  else { fail += 1; failures.push(name); console.log(`  FAIL: ${name}${detail ? ` — ${detail}` : ''}`); }
}

function makeTmp(prefix) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  tmpDirs.push(dir);
  return dir;
}

/** Run a snippet of ESM source in a child node process (top-level await allowed). */
function runNodeEsm(source, { env = {}, cwd = ROOT, timeout = 60000 } = {}) {
  return spawnSync(NODE, ['--input-type=module', '-e', source], {
    cwd,
    env: { ...process.env, ...env },
    encoding: 'utf8',
    timeout,
    windowsHide: true,
  });
}

// The child writer used by [1]: publish CONCURRENCY distinct versions into one
// scene, print the allocated version numbers as a JSON array on stdout.
const PUBLISH_WORKER = `
const mod = await import(process.env.STORE_URL);
const n = Number(process.env.PUBLISH_N);
const scene = process.env.SCENE_KEY;
const childId = process.env.CHILD_ID;
const versions = [];
for (let i = 0; i < n; i += 1) {
  const res = mod.addVersion({
    sceneKey: scene,
    ontology: { scene: { name: scene }, marker: childId + ':' + i, pad: 'x'.repeat(1200) },
    origin: 'cli',
    buildMode: 'edit',
  });
  if (res.deduped) throw new Error('unexpected dedupe for distinct payload ' + childId + ':' + i);
  versions.push(res.version);
}
console.log(JSON.stringify(versions));
`;

// ────────────────────────── [1] concurrency ──────────────────────────

async function testConcurrency() {
  console.log('\n[1] ontology_store: 2 x %d concurrent publishes into one scene', CONCURRENCY);

  const storeDir = makeTmp('ont-store-conc-');
  const childEnv = { ONTOLOGY_STORE_DIR: storeDir, STORE_URL, SCENE_KEY: SCENE, PUBLISH_N: String(CONCURRENCY) };

  // spawn both writers at once (no await between the two spawnSyncs in a way that
  // serializes them: spawnSync blocks, so run them via spawn + Promise instead)
  const { spawn } = await import('node:child_process');
  const runWriter = (childId) => new Promise((resolve) => {
    const cp = spawn(NODE, ['--input-type=module', '-e', PUBLISH_WORKER], {
      cwd: ROOT,
      env: { ...process.env, ...childEnv, CHILD_ID: childId },
      windowsHide: true,
    });
    let out = ''; let err = '';
    cp.stdout.on('data', (d) => { out += d; });
    cp.stderr.on('data', (d) => { err += d; });
    cp.on('close', (code) => resolve({ code, out: out.trim(), err: err.trim() }));
  });

  const results = await Promise.all([runWriter('a'), runWriter('b')]);

  for (const [i, r] of results.entries()) {
    check(`writer ${i + 1} exited 0`, r.code === 0, `exit=${r.code} stderr=${r.err.slice(0, 300)}`);
  }
  const parseVersions = (r, i) => {
    try {
      const v = JSON.parse(r.out);
      return Array.isArray(v) ? v.map(Number) : [];
    } catch {
      check(`writer ${i + 1} printed a version array`, false, `stdout=${r.out.slice(0, 200)}`);
      return [];
    }
  };
  const v1 = parseVersions(results[0], 1);
  const v2 = parseVersions(results[1], 2);
  check(`both writers published ${CONCURRENCY} versions each`, v1.length === CONCURRENCY && v2.length === CONCURRENCY,
    `got ${v1.length} + ${v2.length}`);

  const all = [...v1, ...v2];
  const distinct = new Set(all);
  check(`union of returned versions has exactly ${CONCURRENCY * 2} distinct values (no lost update, no duplicate nextVersion)`,
    distinct.size === CONCURRENCY * 2, `distinct=${distinct.size} of ${all.length}`);
  const expected = Array.from({ length: CONCURRENCY * 2 }, (_, i) => i + 1);
  const sorted = [...distinct].sort((a, b) => a - b);
  check(`allocated versions are exactly 1..${CONCURRENCY * 2}`, JSON.stringify(sorted) === JSON.stringify(expected),
    `got ${JSON.stringify(sorted.slice(0, 5))}...${JSON.stringify(sorted.slice(-3))}`);

  // index integrity
  let idx = null;
  try { idx = JSON.parse(fs.readFileSync(path.join(storeDir, 'index.json'), 'utf8')); } catch (e) {
    check('index.json parses', false, e.message);
  }
  if (idx) {
    check('index.json parses', true);
    const entries = (idx.entries || []).filter((e) => e.scene_key === SCENE);
    const entryVersions = entries.map((e) => e.version);
    const maxVersion = Math.max(...entryVersions);
    check('indexed max version equals the last allocated version', maxVersion === CONCURRENCY * 2, `max=${maxVersion}`);
    check('index has no duplicate version numbers', new Set(entryVersions).size === entryVersions.length,
      `versions=${JSON.stringify(entryVersions)}`);
    let missing = 0;
    for (const e of entries) {
      if (!fs.existsSync(path.join(storeDir, e.path))) missing += 1;
    }
    check('every indexed version has its ontology.json on disk', missing === 0, `${missing} missing`);
    // prune policy (MAX_VERSIONS_PER_SCENE=10) keeps the newest N: the on-disk
    // scene dir must match the index exactly — no orphan version dirs.
    const onDisk = fs.readdirSync(path.join(storeDir, SCENE)).filter((n) => /^v\d+$/.test(n))
      .map((n) => Number(n.slice(1))).sort((a, b) => a - b);
    check('scene dirs on disk match the index exactly (prune kept index and disk in sync)',
      JSON.stringify(onDisk) === JSON.stringify([...entryVersions].sort((a, b) => a - b)),
      `disk=${JSON.stringify(onDisk)} index=${JSON.stringify([...entryVersions].sort((a, b) => a - b))}`);
  }

  check('no .index.lock left behind', !fs.existsSync(path.join(storeDir, '.index.lock')));

  // [1b] a fresh lock blocks a writer until released. The release must come from
  // a SEPARATE process: spawnSync blocks the parent event loop, so a parent-side
  // timer could never fire while the writer waits. Repeated 3x because the
  // create/unlink race is exactly where Windows surfaces EPERM/EACCES
  // (pending-delete) instead of EEXIST — an intermittent failure here means the
  // lock hardening regressed.
  for (let round = 1; round <= 3; round += 1) {
    const lockPath = path.join(storeDir, '.index.lock');
    fs.writeFileSync(lockPath, JSON.stringify({ pid: process.pid, ts: new Date().toISOString(), nonce: 'test-holder' }));
    const releaser = spawn(NODE, ['-e', 'setTimeout(() => { try { require("fs").unlinkSync(process.env.LOCK_PATH); } catch {} }, 500);'],
      { env: { ...process.env, LOCK_PATH: lockPath }, stdio: 'ignore', windowsHide: true });
    const started = Date.now();
    const blocked = runNodeEsm(`
const mod = await import(process.env.STORE_URL);
const r = mod.addVersion({ sceneKey: process.env.SCENE_KEY, ontology: { scene: { name: process.env.SCENE_KEY }, pad: 'l'.repeat(1200) } });
console.log(JSON.stringify({ version: r.version }));
`, { env: { ONTOLOGY_STORE_DIR: storeDir, STORE_URL, SCENE_KEY: `${SCENE}_lock` }, timeout: 20000 });
    const elapsed = Date.now() - started;
    await new Promise((resolve) => releaser.on('close', resolve));
    check(`writer honored the fresh lock (round ${round}: waited for release, then succeeded)`,
      blocked.status === 0 && elapsed >= 350, `status=${blocked.status} elapsed=${elapsed}ms stderr=${(blocked.stderr || '').slice(0, 900)}`);
    check(`writer released the lock it acquired (round ${round})`, !fs.existsSync(lockPath));
  }
}

// ────────────────────────── [2] corrupt index ──────────────────────────

function testCorruptIndex() {
  console.log('\n[2] ontology_store: corrupt index.json is backed up + throws (never zeroed)');

  const storeDir = makeTmp('ont-store-corrupt-');
  const env = { ONTOLOGY_STORE_DIR: storeDir, STORE_URL };

  const seed = runNodeEsm(`
const mod = await import(process.env.STORE_URL);
mod.addVersion({ sceneKey: 'keepme', ontology: { scene: { name: 'keepme' }, pad: 'k'.repeat(1200) } });
console.log(JSON.stringify(mod.readIndex().entries.length));
`, { env });
  check('seed publish into temp store succeeded', seed.status === 0 && seed.stdout.trim() === '1',
    `status=${seed.status} stdout=${seed.stdout.trim()} stderr=${(seed.stderr || '').slice(0, 200)}`);

  const indexPath = path.join(storeDir, 'index.json');
  const corruptText = '{"version":1,"entries":[  <<< truncated mid-write';
  fs.writeFileSync(indexPath, corruptText);

  const probe = runNodeEsm(`
const mod = await import(process.env.STORE_URL);
const out = { readThrew: false };
try { mod.readIndex(); } catch (e) { out.readThrew = true; out.name = e.name; out.code = e.code; out.message = e.message; out.backupPath = e.backupPath || null; }
try { out.listThrew = false; mod.listStore(); } catch (e) { out.listThrew = true; }
try {
  mod.addVersion({ sceneKey: 'keepme', ontology: { scene: { name: 'keepme' }, pad: 'm'.repeat(1200) } });
  out.mutateThrew = false;
} catch (e) { out.mutateThrew = true; out.mutateError = e.name; }
console.log(JSON.stringify(out));
`, { env });

  let report = null;
  try { report = JSON.parse(probe.stdout.trim()); } catch { /* asserted below */ }
  check('corrupt-index probe ran', probe.status === 0 && report !== null, `status=${probe.status} stdout=${probe.stdout.slice(0, 200)} stderr=${(probe.stderr || '').slice(0, 300)}`);
  if (!report) return;

  check('readIndex throws on corrupt JSON', report.readThrew === true);
  check('error is OntologyStoreCorruptError with code ONTOLOGY_STORE_CORRUPT',
    report.name === 'OntologyStoreCorruptError' && report.code === 'ONTOLOGY_STORE_CORRUPT',
    `name=${report.name} code=${report.code}`);
  check('error message names the backup path', typeof report.message === 'string'
    && report.message.includes('index.json.corrupt-') && typeof report.backupPath === 'string',
    `message=${report.message}`);
  check('listStore (a read caller) also throws', report.listThrew === true);
  check('addVersion (a mutator) throws instead of writing an empty index', report.mutateThrew === true,
    `mutateError=${report.mutateError}`);

  const backups = fs.readdirSync(storeDir).filter((f) => f.startsWith('index.json.corrupt-'));
  check('a index.json.corrupt-<ts> backup exists', backups.length === 1, `backups=${JSON.stringify(backups)}`);
  if (backups.length) {
    check('backup holds the corrupt bytes', fs.readFileSync(path.join(storeDir, backups[0]), 'utf8') === corruptText);
  }
  check('index.json on disk is untouched (stored entries not zeroed)',
    fs.readFileSync(indexPath, 'utf8') === corruptText);
  check('stored version directory still exists', fs.existsSync(path.join(storeDir, 'keepme', 'v1', 'ontology.json')));

  // non-array entries variant
  const storeDir2 = makeTmp('ont-store-nonarray-');
  fs.mkdirSync(storeDir2, { recursive: true });
  const badIdx = '{"version":1,"entries":{"nope":true}}';
  fs.writeFileSync(path.join(storeDir2, 'index.json'), badIdx);
  const probe2 = runNodeEsm(`
const mod = await import(process.env.STORE_URL);
try { mod.readIndex(); console.log(JSON.stringify({ threw: false })); }
catch (e) { console.log(JSON.stringify({ threw: true, name: e.name, backupPath: e.backupPath || null })); }
`, { env: { ONTOLOGY_STORE_DIR: storeDir2, STORE_URL } });
  let report2 = null;
  try { report2 = JSON.parse(probe2.stdout.trim()); } catch { /* asserted below */ }
  check('non-array entries[] also throws OntologyStoreCorruptError',
    report2?.threw === true && report2?.name === 'OntologyStoreCorruptError', `stdout=${probe2.stdout.slice(0, 200)}`);
  check('non-array entries[] file was backed up as well',
    fs.readdirSync(storeDir2).some((f) => f.startsWith('index.json.corrupt-'))
    && fs.readFileSync(path.join(storeDir2, 'index.json'), 'utf8') === badIdx);
}

// ────────────────────────── [3] manifest rebuild ──────────────────────────

function testManifestRebuild() {
  console.log('\n[3] append-pipeline-event: corrupt run_manifest.json rebuilt from .pipeline_events.jsonl');

  const runDir = makeTmp('pipe-rebuild-');
  fs.mkdirSync(path.join(runDir, '00_input'), { recursive: true });
  fs.writeFileSync(path.join(runDir, '00_input', 'run_config.json'), JSON.stringify({ run_mode: 'full' }));
  const corruptManifest = '{ "run_id": "broken", "steps": [';
  fs.writeFileSync(path.join(runDir, 'run_manifest.json'), corruptManifest);

  const events = [
    { event: 'run_initialized', step: 'setup', agent: 'main-agent', timestamp: '2026-10-17T00:00:00.000Z', run_id: '20261017000000000_tscene', run_dir: 'X', files_written: ['run_manifest.json'], status: 'completed' },
    { event: 'agent_start', step: 'context_builder', agent: 'context-builder', timestamp: '2026-10-17T00:01:00.000Z' },
    { event: 'agent_complete', step: 'context_builder', agent: 'context-builder', timestamp: '2026-10-17T00:02:00.000Z', files_written: ['01_ontology/ontology.json'] },
    { event: 'agent_start', step: 'data_processor', agent: 'data-processor', timestamp: '2026-10-17T00:03:00.000Z' },
    { event: 'agent_complete', step: 'data_processor', agent: 'data-processor', timestamp: '2026-10-17T00:04:00.000Z' },
    { event: 'repair_spawn', agent: 'main-agent', step: 'diagnostician', timestamp: '2026-10-17T00:05:00.000Z' },
    { event: 'repair_spawn', agent: 'main-agent', step: 'diagnostician', timestamp: '2026-10-17T00:06:00.000Z' },
  ];
  const logPath = path.join(runDir, '.pipeline_events.jsonl');
  const logLines = events.map((e) => JSON.stringify(e));
  logLines.splice(3, 0, 'garbage line {{{ not json'); // corrupt line must be skipped, not fatal
  fs.writeFileSync(logPath, `${logLines.join('\n')}\n`);
  const linesBefore = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean).length;

  const res = spawnSync(NODE, [APPEND_EVENT, runDir, '--event', 'agent_start', '--agent', 'diagnostician'], {
    cwd: ROOT, encoding: 'utf8', timeout: 30000, windowsHide: true,
  });
  check('CLI exits 0 (rebuild path)', res.status === 0, `status=${res.status} stderr=${(res.stderr || '').slice(0, 400)}`);
  check('warning names the skipped corrupt JSONL line', /skipping corrupt \.pipeline_events\.jsonl line/.test(res.stderr || ''),
    `stderr=${(res.stderr || '').slice(0, 300)}`);
  check('warning names the corrupt manifest backup', /run_manifest\.json\.corrupt-/.test(res.stderr || ''));

  let manifest = null;
  try { manifest = JSON.parse(fs.readFileSync(path.join(runDir, 'run_manifest.json'), 'utf8')); } catch (e) {
    check('rebuilt run_manifest.json parses', false, e.message);
  }
  if (manifest) {
    check('rebuilt run_manifest.json parses', true);
    check('manifest carries rebuilt_from_events: true', manifest.rebuilt_from_events === true);
    check('run_id recovered from run_initialized event', manifest.run_id === '20261017000000000_tscene', `run_id=${manifest.run_id}`);
    check('diag_iters_total == repair_spawn count (2)', manifest.pipeline?.diag_iters_total === 2, `got ${manifest.pipeline?.diag_iters_total}`);
    check('repair_spawn_count == 2', manifest.pipeline?.repair_spawn_count === 2);
    const steps = new Map((manifest.steps || []).map((s) => [s.step, s]));
    check('data_processor reconstructed as completed', steps.get('data_processor')?.status === 'completed');
    check('context_builder reconstructed as completed', steps.get('context_builder')?.status === 'completed');
    check('new event applied: diagnostician in_progress', steps.get('diagnostician')?.status === 'in_progress',
      `status=${steps.get('diagnostician')?.status}`);
    check('current_step/current_owner point at the new event', manifest.pipeline?.current_step === 'diagnostician'
      && manifest.pipeline?.current_owner === 'diagnostician');
    check('steps skeleton keeps the canonical pipeline list (setup..present)', Array.isArray(manifest.steps)
      && manifest.steps.length >= 11 && manifest.steps[0].step === 'setup'
      && manifest.steps.some((s) => s.step === 'present'));
    check('execution_policy.audit.skipped_stages reconstructed as an array',
      Array.isArray(manifest.execution_policy?.audit?.skipped_stages));
    check('delivery_contract.required_runtime_artifacts restored (gate would silently pass if empty)',
      Array.isArray(manifest.delivery_contract?.required_runtime_artifacts)
      && manifest.delivery_contract.required_runtime_artifacts.includes('report.md'));
  }

  const backups = fs.readdirSync(runDir).filter((f) => f.startsWith('run_manifest.json.corrupt-'));
  check('corrupt manifest backed up', backups.length === 1, `backups=${JSON.stringify(backups)}`);
  if (backups.length) {
    check('backup holds the corrupt bytes', fs.readFileSync(path.join(runDir, backups[0]), 'utf8') === corruptManifest);
  }
  const linesAfter = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean).length;
  check('new event appended to the JSONL (corrupt line preserved as-is)', linesAfter === linesBefore + 1,
    `before=${linesBefore} after=${linesAfter}`);

  // negative: corrupt manifest AND missing JSONL → hard exit naming both failures
  const runDir2 = makeTmp('pipe-norebuild-');
  fs.writeFileSync(path.join(runDir2, 'run_manifest.json'), corruptManifest);
  const res2 = spawnSync(NODE, [APPEND_EVENT, runDir2, '--event', 'agent_start', '--agent', 'diagnostician'], {
    cwd: ROOT, encoding: 'utf8', timeout: 30000, windowsHide: true,
  });
  const err2 = `${res2.stderr || ''}${res2.stdout || ''}`;
  check('no-JSONL case keeps the hard exit', res2.status !== 0, `status=${res2.status}`);
  check('hard exit names BOTH failure reasons', /run_manifest\.json/.test(err2) && /\.pipeline_events\.jsonl/.test(err2),
    `output=${err2.slice(0, 300)}`);
}

// ────────────────────────── [4] validate.mjs null semantics ──────────────────────────

function testValidateNullSemantics() {
  console.log('\n[4] validate.mjs: draft-07 null semantics');

  const dir = makeTmp('validate-null-');
  const schemaPath = path.join(dir, 'schema.json');
  const dataPath = path.join(dir, 'data.json');

  const cases = [
    ['enum without null rejects null', '{"enum":["a","b"]}', 'null', false],
    ['enum listing null accepts null', '{"enum":["a","b",null]}', 'null', true],
    ['nullable:true is a real escape hatch for type', '{"type":"string","nullable":true}', 'null', true],
    ['nullable:true escapes const as well', '{"nullable":true,"const":"a"}', 'null', true],
    ['nullable:false with unconstrained type still accepts null', '{"nullable":false}', 'null', true],
    ['type string alone rejects null (unchanged)', '{"type":"string"}', 'null', false],
    ['type [string,null] accepts null (unchanged)', '{"type":["string","null"]}', 'null', true],
    ['const null accepts null (unchanged)', '{"const":null}', 'null', true],
    ['oneOf with a null branch accepts null', '{"oneOf":[{"type":"string"},{"type":"null"}]}', 'null', true],
    ['oneOf without a null branch rejects null', '{"oneOf":[{"type":"string"},{"type":"integer"}]}', 'null', false],
    ['anyOf with a null branch accepts null', '{"anyOf":[{"type":"null"},{"type":"string"}]}', 'null', true],
    ['if/then/else still drives null', '{"if":{"type":"null"},"then":{"const":null},"else":{"type":"string"}}', 'null', true],
    ['allOf enum listing null accepts null', '{"allOf":[{"enum":["a",null]},{"type":["string","null"]}]}', 'null', true],
    ['allOf enum without null rejects null', '{"allOf":[{"enum":["a"]}]}', 'null', false],
    ['$ref to an enum without null rejects null', '{"definitions":{"E":{"enum":["a"]}},"$ref":"#/definitions/E"}', 'null', false],
    ['properties: null must satisfy the enum', '{"type":"object","properties":{"x":{"enum":["a"]}}}', '{"x":null}', false],
    ['properties: enum listing null accepts it', '{"type":"object","properties":{"x":{"enum":[null,"a"]}}}', '{"x":null}', true],
    ['array items enum without null rejects [null]', '{"type":"array","items":{"enum":["a"]}}', '[null]', false],
    ['array items enum listing null accepts [null]', '{"type":"array","items":{"enum":[null,"a"]}}', '[null]', true],
    ['not:{type:null} rejects null', '{"not":{"type":"null"}}', 'null', false],
    ['enum without null still accepts a listed string (no over-reach)', '{"enum":["a","b"]}', '"a"', true],
  ];

  for (const [name, schema, data, wantValid] of cases) {
    fs.writeFileSync(schemaPath, schema);
    fs.writeFileSync(dataPath, `${data}\n`);
    const r = spawnSync(NODE, [VALIDATE, schemaPath, dataPath], { cwd: ROOT, encoding: 'utf8', timeout: 20000, windowsHide: true });
    const valid = r.status === 0;
    check(name, valid === wantValid, `exit=${r.status} want_valid=${wantValid} schema=${schema} data=${data}`);
  }
}

// ────────────────────────── main ──────────────────────────

console.log('='.repeat(70));
console.log('SHARED SCRIPT SAFETY TESTS — ontology_store / append-pipeline-event / validate');
console.log('='.repeat(70));

try {
  await testConcurrency();
  testCorruptIndex();
  testManifestRebuild();
  testValidateNullSemantics();
} finally {
  for (const dir of tmpDirs) {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* best effort */ }
  }
}

console.log(`\nSUMMARY: ${pass} PASS / ${fail} FAIL`);
if (fail > 0) {
  console.log('Failures:');
  for (const name of failures) console.log(`  - ${name}`);
  process.exit(1);
}
console.log('ALL PASS');
process.exit(0);
