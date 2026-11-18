#!/usr/bin/env node
// quality_gate.mjs — E-1H quality gate (plan v1.1 §7, exit codes I2).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--raw-path <dir|file>] [--schema-dir <dir>]
// Exit: 0 ok | 1 hard error (bad inputs) | 2 undetermined (stage marker absent)
//       | 3 gate-fail (any H check failed)
//
// Every check is mechanical: H1 schema+strict-extra-keys, H2 joined==anchor rows
// order + HX tail-only, H3 provenance recompute + _src_ts<=ts, H4 coverage
// honesty, H5 zero-LLM static scan, H6/H6b time format + non-midnight, H7
// E-1 immutability + write whitelist, H8 naming contract.

import { spawnSync } from 'child_process';
import { createHash } from 'crypto';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { dirname, join, resolve, sep } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHARED_SCRIPTS = resolve(HERE, '..', '..', '..', '..', '.claude', 'shared', 'scripts');
const VALIDATE = join(SHARED_SCRIPTS, 'validate.mjs');

const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR = resolve(argOf('--run-dir') || '.');
const RAW_PATH = argOf('--raw-path');
const HET = join(RUN_DIR, '07_hetero');
const SCHEMA_DIR = resolve(argOf('--schema-dir') || join(HERE, '..', 'schemas'));

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);
// GAP-1 closure: any unexpected error still emits a STRUCTURED verdict (fail-closed)
process.on('uncaughtException', (e) => {
  console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict: 'gate_fail', fails: [...FAILS, `GATE: unhandled error: ${e.message}`], notes: NOTES }, null, 2));
  process.exit(3);
});

const sha256File = (p) => {
  const h = createHash('sha256');
  try {
    h.update(readFileSync(p));
    return 'sha256:' + h.digest('hex');
  } catch { return null; }
};

// minimal CSV reader: header + rows (machine-generated CSVs; quoted newlines unsupported by design)
function readCsv(path, maxRows = Infinity) {
  const text = readFileSync(path, 'utf-8').replace(/^\uFEFF/, '');
  const lines = text.split(/\r?\n/).filter((l, i, a) => !(l === '' && i === a.length - 1));
  if (!lines.length) return { header: [], rows: [] };
  const split = (line) => {
    const out = []; let cur = '', q = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (q) { if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; }
      else if (c === '"') q = true;
      else if (c === ',') { out.push(cur); cur = ''; }
      else cur += c;
    }
    out.push(cur); return out;
  };
  const header = split(lines[0]);
  const rows = [];
  for (let i = 1; i < lines.length && rows.length < maxRows; i++) rows.push(split(lines[i]));
  return { header, rows };
}

function validateAgainst(schemaPath, dataPath) {
  const r = spawnSync('node', [VALIDATE, schemaPath, dataPath], { encoding: 'utf-8', timeout: 60000 });
  if (r.status !== 0) return { ok: false, report: r.stdout || r.stderr || String(r.status) };
  let report = {};
  try { report = JSON.parse(r.stdout || '{}'); } catch { return { ok: false, report: { errors: ['unparseable validator output'] } }; }
  return { ok: !!report.valid, report: JSON.stringify(report.errors || []) };
}

// H1b: strict extra-keys (validate.mjs only warns on additionalProperties:false)
function extraKeys(data, schema, path = '$') {
  const bad = [];
  if (schema && schema.properties && data && typeof data === 'object' && !Array.isArray(data)) {
    for (const k of Object.keys(data)) if (!(k in schema.properties)) bad.push(`${path}.${k}`);
    for (const k of Object.keys(schema.properties)) {
      if (k in data) bad.push(...extraKeys(data[k], schema.properties[k], `${path}.${k}`));
    }
  }
  if (schema && schema.items && data && Array.isArray(data)) {
    data.forEach((item, i) => bad.push(...extraKeys(item, schema.items, `${path}[${i}]`)));
  }
  return bad;
}

const iso = (s) => /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$/.test(String(s || '').trim());

// ───────────────────────────── main ─────────────────────────────
const manifestPath = join(HET, 'hetero_manifest.json');
if (!existsSync(manifestPath)) {
  console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict: 'undetermined', reason: 'marker manifest absent — E-1H stage did not run (or was removed)' }, null, 2));
  process.exit(2);
}
let manifest;
try { manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')); } catch (e) {
  console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict: 'hard_error', reason: `manifest unparseable: ${e.message}` }, null, 2));
  process.exit(1);
}
if (manifest.status === 'off') {
  const verdict = FAILS.length ? 'gate_fail' : 'ok';
  console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict, status: manifest.status, fails: FAILS, notes: NOTES }, null, 2));
  process.exit(FAILS.length ? 3 : 0);
}
if (manifest.status === 'no_hetero_sources' && !(manifest.sources || []).length) {
  // strict zero-write branch applies ONLY when nothing was even detected;
  // a run whose sources were all skipped/insufficient legitimately emits
  // contract artifacts and takes the full-check path below.
  for (const f of manifest.h7_guard?.files || []) {
    const p = join(RUN_DIR, f.path);
    if (existsSync(p) && sha256File(p) !== f.sha256) fail('H7', `guard file modified: ${f.path}`);
  }
  const allowed = new Set([manifestPath]);
  const walk = (d) => { for (const e of readdirSync(d)) { const p = join(d, e); if (statSync(p).isDirectory()) walk(p); else allowed.add(p); } };
  if (existsSync(HET)) walk(HET);
  if (allowed.size > 1) fail('H7', `no-source run wrote extra files: ${[...allowed].filter((p) => p !== manifestPath).join(', ')}`);
  const verdict = FAILS.length ? 'gate_fail' : 'ok';
  console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict, status: manifest.status, fails: FAILS, notes: NOTES }, null, 2));
  process.exit(FAILS.length ? 3 : 0);
}

// ---- H1 schema + strict extra keys ----------------------------------------
const checks = [
  ['hetero_manifest.json', 'hetero_manifest_schema.json'],
  ['column_contract.json', 'column_contract_schema.json'],
];
const annPath = join(HET, 'annotations.json');
if (existsSync(annPath)) checks.push(['annotations.json', 'annotations_schema.json']);
for (const [data, schema] of checks) {
  const dp = join(HET, data);
  const r = validateAgainst(join(SCHEMA_DIR, schema), dp);
  if (!r.ok) fail('H1', `${data} schema invalid: ${r.report}`);
  try {
    const bad = extraKeys(JSON.parse(readFileSync(dp, 'utf-8')), JSON.parse(readFileSync(join(SCHEMA_DIR, schema), 'utf-8')));
    if (bad.length) fail('H1b', `${data} strict extra keys: ${bad.slice(0, 8).join(', ')}${bad.length > 8 ? ` (+${bad.length - 8})` : ''}`);
  } catch (e) { fail('H1b', `${data} extra-key scan error: ${e.message}`); }
}

// ---- H8 naming contract ----------------------------------------------------
let contract = { columns: [] };
try { contract = JSON.parse(readFileSync(join(HET, 'column_contract.json'), 'utf-8')); } catch { /* H1 reports */ }
const slugToSources = new Map();
for (const c of contract.columns || []) {
  if (!/^HX-(PROF|MAP|IMG|TXT|IDX)-[A-Z0-9]+-[A-Z0-9-]+$/.test(c.column) || c.column.length > 64) fail('H8', `bad column name: ${c.column}`);
}
for (const s of manifest.sources || []) {
  if (!s.slug) continue;
  if (slugToSources.has(s.slug) && slugToSources.get(s.slug) !== s.source_id) fail('H8', `slug collision: ${s.slug}`);
  slugToSources.set(s.slug, s.source_id);
}
for (const f of (existsSync(join(HET, 'features')) ? readdirSync(join(HET, 'features')) : []).concat([manifest.outputs?.joined_table || ''])) {
  const low = String(f).toLowerCase();
  for (const tok of ['merged', 'merge', 'align', 'combined', '_full', 'joined']) {
    if (low.includes(tok)) fail('H8', `forbidden token "${tok}" in emitted file name: ${f}`);
  }
}

// ---- H3 provenance ----------------------------------------------------------
for (const c of contract.columns || []) {
  const insufficient = c.insufficient_data === true;
  if (!(c.n_inputs > 0) && !insufficient) fail('H3', `column ${c.column}: n_inputs not > 0`);
  if (RAW_PATH) {
    const src = join(RUN_DIR, c.source_path?.replace(/^([A-Za-z]:)?[\\/]/, '') || '') ;
    const candidate = existsSync(c.source_path) ? c.source_path : (existsSync(src) ? src : null);
    if (candidate && c.source_sha256 && sha256File(candidate) !== c.source_sha256) fail('H3', `column ${c.column}: source_sha256 mismatch for ${c.source_path}`);
  }
}
const featDir = join(HET, 'features');
if (existsSync(featDir)) {
  for (const f of readdirSync(featDir)) {
    const { header, rows } = readCsv(join(featDir, f));
    const iTs = header.indexOf('ts');
    const iSrc = header.indexOf('_src_ts');
    if (iTs < 0) { fail('H3', `features/${f}: missing ts column`); continue; }
    for (const r of rows) {
      if (!iso(r[iTs])) { fail('H3', `features/${f}: non-ISO ts "${r[iTs]}"`); break; }
      if (iSrc >= 0 && r[iSrc] && iso(r[iSrc]) && String(r[iSrc]) > String(r[iTs])) {
        fail('H3', `features/${f}: _src_ts ${r[iSrc]} > ts ${r[iTs]} (look-ahead)`);
        break;
      }
    }
  }
} else if (manifest.status === 'ok') fail('H3', 'features/ dir missing for a status=ok run');

// ---- H4 coverage honesty ----------------------------------------------------
for (const c of contract.columns || []) {
  if (c.coverage < 0.3 && !c.sparse) fail('H4', `column ${c.column}: coverage ${c.coverage} <0.3 but sparse=false`);
  if (c.stats_eligible && c.coverage < 0.5) fail('H4', `column ${c.column}: stats_eligible with coverage ${c.coverage} <0.5`);
  if (c.insufficient_data && c.stats_eligible) fail('H4', `column ${c.column}: insufficient_data but stats_eligible`);
}

// ---- H5 zero-LLM static scan -------------------------------------------------
if (manifest.zero_llm !== true) fail('H5', 'manifest.zero_llm is not true');
const scanDir = join(HERE, 'heterocore');
const FORBIDDEN = [/\brequests\b/, /\bhttpx\b/, /\burllib\b/, /\bopenai\b/i, /\banthropic\b/i, /requests\.post/, /urlopen/];
const scanPy = (d) => {
  for (const e of readdirSync(d)) {
    const p = join(d, e);
    if (statSync(p).isDirectory()) { scanPy(p); continue; }
    if (!e.endsWith('.py')) continue;
    const text = readFileSync(p, 'utf-8');
    FORBIDDEN.forEach((re, i) => { if (re.test(text)) fail('H5', `forbidden pattern ${FORBIDDEN[i]} in ${e}`); });
  }
};
scanPy(scanDir);

// ---- H2 joined table identity ------------------------------------------------
if (manifest.outputs?.joined_table) {
  const joinedPath = join(RUN_DIR, manifest.outputs.joined_table);
  if (!existsSync(joinedPath)) fail('H2', `joined_table missing: ${manifest.outputs.joined_table}`);
  else {
    const anchorPath = manifest.anchor?.path ? (existsSync(manifest.anchor.path) ? manifest.anchor.path : join(RUN_DIR, manifest.anchor.path)) : null;
    const j = readCsv(joinedPath, 1);
    const anchorCols = manifest.anchor?.columns || manifest.anchor_columns;
    // GAP-2 closure: contract ↔ product membership — a phantom contract column
    // (never computed) or an unregistered joined HX column must both fail.
    const contractCols = new Set((contract.columns || []).map((c) => c.column));
    const joinedHx = j.header.filter((c) => /^HX-/.test(c));
    for (const c of contractCols) {
      if (!joinedHx.includes(c)) fail('H2', `contract column absent from joined table: ${c}`);
    }
    for (const c of joinedHx) {
      if (!contractCols.has(c)) fail('H2', `joined HX column not in contract: ${c}`);
    }
    if (anchorCols) {
      const prefix = j.header.slice(0, anchorCols.length);
      const same = prefix.length === anchorCols.length && prefix.every((c, i) => c === anchorCols[i]);
      if (!same) fail('H2', `joined prefix columns differ from anchor: ${prefix.join(',')} vs ${anchorCols.join(',')}`);
      const tail = j.header.slice(anchorCols.length);
      if (tail.some((c) => !c.startsWith('HX-'))) fail('H2', `non-HX column injected: ${tail.filter((c) => !c.startsWith('HX-')).join(', ')}`);
    }
    // row identity: count + time column order vs anchor (streamed compare)
    if (anchorPath && existsSync(anchorPath)) {
      const tCol = manifest.anchor?.time_column;
      const a = readCsv(anchorPath, Infinity);
      const b = readCsv(joinedPath, Infinity);
      if (a.rows.length !== b.rows.length) fail('H2', `row count drift: anchor ${a.rows.length} vs joined ${b.rows.length}`);
      else if (tCol) {
        const ia = a.header.indexOf(tCol);
        const ib = b.header.indexOf(tCol);
        for (let i = 0; i < a.rows.length; i++) {
          if (a.rows[i][ia] !== b.rows[i][ib]) { fail('H2', `row order drift at line ${i + 2}`); break; }
        }
      }
    }
    if (j.header.some((c) => /^HX-/.test(c))) {
      // HX columns must be strictly at the tail (fingerprint stability, plan D6)
      const firstHx = j.header.findIndex((c) => /^HX-/.test(c));
      if (j.header.slice(firstHx).some((c) => !/^HX-/.test(c))) fail('H2', 'HX columns are not contiguous at the tail');
    }
  }
}

// ---- H6/H6b time discipline ---------------------------------------------------
if (existsSync(featDir)) {
  for (const f of readdirSync(featDir)) {
    const { header, rows } = readCsv(join(featDir, f), 5000);
    const iTs = header.indexOf('ts');
    if (iTs < 0) continue;
    const nonMidnight = rows.some((r) => { const v = String(r[iTs] || ''); return iso(v) && !v.endsWith('00:00:00'); });
    const src = (manifest.sources || []).find((s) => f.startsWith(`${(s.slug || '').toUpperCase()}-`) || f.toUpperCase().includes(String(s.source_id || '').toUpperCase()));
    if (rows.length >= 10 && !nonMidnight && (src?.cadence_s ?? 3600) < 86400) {
      fail('H6b', `features/${f}: sub-daily source but every ts is midnight — time-of-day likely truncated (R4 trap)`);
    }
  }
}

// ---- H7 E-1 immutability + write whitelist ------------------------------------
const WHITELIST_OUTSIDE = new Set([
  join(RUN_DIR, '00_input', 'run_config.json'),
  join(RUN_DIR, '.pipeline_events.jsonl'),
  join(RUN_DIR, '03_figures', 'fig_hetero_profile_heatmap.png'),
  join(RUN_DIR, '03_figures', 'plot_manifest.json'),
].map((p) => resolve(p)));
for (const f of manifest.h7_guard?.files || []) {
  const p = join(RUN_DIR, f.path);
  if (!existsSync(p) || sha256File(p) !== f.sha256) fail('H7', `guard file modified or missing: ${f.path}`);
}
for (const w of manifest.h7_guard?.written || []) {
  const rp = resolve(RUN_DIR, w);
  if (!rp.startsWith(resolve(HET) + sep) && !WHITELIST_OUTSIDE.has(rp)) fail('H7', `write outside whitelist: ${w}`);
}

// ---- verdict -------------------------------------------------------------------
const verdict = FAILS.length ? 'gate_fail' : 'ok';
console.log(JSON.stringify({ gate: 'hetero_quality_gate', verdict, status: manifest.status, checks: { fails: FAILS, notes: NOTES }, columns: (contract.columns || []).length, sources: (manifest.sources || []).length }, null, 2));
process.exit(FAILS.length ? 3 : 0);
