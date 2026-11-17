#!/usr/bin/env node
// quality_gate.mjs — E-1 quality gate for industrial-data-preprocessor.
//
// Post-hoc verification of a run dir that went through the adaptive data
// preprocessing stage (E-1). Zero dependencies (node builtins only).
//
// Usage:
//   node quality_gate.mjs --run-dir <RUN_DIR> [--raw-path <dir|file>]
//
// Exit codes (house convention):
//   0 ok        — canonical table produced and internally consistent
//   1 hard error — bad inputs (no/unreadable --run-dir, --raw-path missing on
//                  disk) or the audit is unreadable so the stage identity
//                  cannot be decided
//   2 undetermined — the E-1 stage did not produce a canonical table; either
//                  it never ran (single-file passthrough: the raw file is
//                  consumed directly → no report AND no csv) or it ran and
//                  documented a non-production outcome (report.status in
//                  {no_tabular_data, no_time_series} — "the caller decides")
//   3 gate-fail — the stage ran but its contract is violated: report claims
//                  success while the declared output is missing, the
//                  canonical csv is corrupt/empty, report↔disk rows/cols
//                  disagree, a declared time column is absent, merge/dedup
//                  actions are internally inconsistent, or a reported output
//                  path resolves outside 00_input
//
// Documented passthrough semantics (decides 2 vs 3 when preprocessed_data.csv
// is absent, read from 00_input/preprocessing_report.json):
//   * report absent + csv absent           → 2  (stage did not run)
//   * report.status no_tabular_data / no_time_series + csv absent → 2
//     (stage ran, honestly reported no canonical table — never a silent pass)
//   * any other status + csv absent        → 3  (report claims success but its
//     declared output is not on disk)
//
// Checks (all mechanical, no LLM, no network):
//   D1 stage identity + passthrough decision (see above)
//   D2 canonical csv non-empty (>=1 data row, non-empty unique headers)
//   D3 report↔disk agreement (rows/cols/numeric columns vs the emitted csv)
//   D4 time contract per the skill's convention (declared time column must
//      exist; time-hint headers disclosed as notes — time-less cross-sectional
//      data is a supported scenario, never a fail)
//   D5 selected_table.file resolves against --raw-path when given
//   D6 merge/dedup actions internally consistent (strategies, merged file
//      names against report.tables, exclusion reason codes, duplicate-row
//      disclosure arithmetic; dedup is NEVER applied by E-1)
//   D7 every reported output path resolves inside RUN_DIR/00_input

import { existsSync, readFileSync, statSync } from 'fs';
import { basename, join, resolve, sep } from 'path';

const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR_ARG = argOf('--run-dir');
const RAW_PATH = argOf('--raw-path');

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);

function emit(verdict, reason, extra = {}) {
  console.log(JSON.stringify({
    gate: 'data_preprocessor_quality_gate',
    verdict,
    ...(reason ? { reason } : {}),
    fails: FAILS,
    notes: NOTES,
    ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
}

// Fail-closed: any unexpected error still emits a STRUCTURED verdict.
process.on('uncaughtException', (e) => {
  fail('GATE', `unhandled error: ${e.message}`);
  emit('gate_fail', null);
});

// ── args ───────────────────────────────────────────────────────────────
if (!RUN_DIR_ARG) {
  FAILS.push('ARGS: missing --run-dir <RUN_DIR>');
  emit('hard_error', 'usage: node quality_gate.mjs --run-dir <RUN_DIR> [--raw-path <dir|file>]');
}
const RUN_DIR = resolve(RUN_DIR_ARG);
if (!existsSync(RUN_DIR) || !statSync(RUN_DIR).isDirectory()) {
  FAILS.push('ARGS', `run dir does not exist or is not a directory: ${RUN_DIR}`);
  emit('hard_error', null);
}
if (RAW_PATH !== undefined && !existsSync(RAW_PATH)) {
  FAILS.push('ARGS', `--raw-path does not exist: ${RAW_PATH}`);
  emit('hard_error', null);
}

const IN_DIR = join(RUN_DIR, '00_input');
const CSV_PATH = join(IN_DIR, 'preprocessed_data.csv');
const REPORT_PATH = join(IN_DIR, 'preprocessing_report.json');
const csvExists = existsSync(CSV_PATH);
const reportExists = existsSync(REPORT_PATH);

// Minimal CSV reader (machine-generated CSVs; E-1 never emits quoted newlines).
function readCsv(path) {
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
  return { header: split(lines[0]), rows: lines.slice(1).map(split) };
}

// ── D1: stage identity + passthrough decision ──────────────────────────
if (!csvExists && !reportExists) {
  emit('undetermined', '00_input/preprocessed_data.csv and 00_input/preprocessing_report.json both absent — E-1 did not run for this run dir (single-file passthrough: the raw file is consumed directly)');
}

let report = null;
if (reportExists) {
  try {
    report = JSON.parse(readFileSync(REPORT_PATH, 'utf-8'));
  } catch (e) {
    if (!csvExists) {
      emit('hard_error', `preprocessing_report.json is unreadable (${e.message}) and no preprocessed_data.csv exists — stage identity cannot be decided`);
    }
    emit('gate_fail', `preprocessing_report.json unparseable next to a produced canonical table: ${e.message}`);
  }
}

if (!csvExists) {
  // Report exists, canonical table does not — the documented marker decides.
  const status = String(report?.status || '');
  if (status === 'no_tabular_data' || status === 'no_time_series') {
    emit('undetermined', `documented non-production outcome: report.status=${status} — the stage ran and reported that no canonical table exists (the caller decides; see SKILL.md passthrough semantics)`);
  }
  emit('gate_fail', `report.status=${status || '(missing)'} but the declared output 00_input/preprocessed_data.csv is absent`);
}

// csv exists; report must exist and parse (checked above).
if (!reportExists) {
  emit('gate_fail', 'preprocessed_data.csv exists but 00_input/preprocessing_report.json is absent — the stage contract always emits the audit next to the table');
}

// ── D2: canonical csv non-empty ────────────────────────────────────────
let csv;
try {
  csv = readCsv(CSV_PATH);
} catch (e) {
  emit('gate_fail', `preprocessed_data.csv unreadable: ${e.message}`);
}
if (!csv.header.length || csv.header.every((h) => String(h).trim() === '')) {
  fail('D2', 'preprocessed_data.csv has no header row');
} else {
  const empty = csv.header.filter((h) => String(h).trim() === '');
  if (empty.length) fail('D2', `empty column name(s) at index ${csv.header.map((h, i) => (String(h).trim() === '' ? i : -1)).filter((i) => i >= 0).join(', ')}`);
  const seen = new Set();
  const dupes = [];
  for (const h of csv.header) {
    if (seen.has(h)) dupes.push(h);
    seen.add(h);
  }
  if (dupes.length) fail('D2', `duplicate column names (normalization contract requires dedup): ${dupes.slice(0, 5).join(', ')}`);
}
if (csv.rows.length === 0) fail('D2', 'preprocessed_data.csv has 0 data rows (non-empty canonical table required)');

// ── D3: report ↔ disk agreement ────────────────────────────────────────
const quality = report.quality && typeof report.quality === 'object' ? report.quality : {};
const declared = report.selected_table && typeof report.selected_table === 'object' ? report.selected_table : {};
if (Number.isInteger(quality.rows) && quality.rows !== csv.rows.length) {
  fail('D3', `report.quality.rows=${quality.rows} but the csv has ${csv.rows.length} data rows (table swapped/truncated after the stage ran)`);
}
if (quality.rows !== undefined && !Number.isInteger(quality.rows)) fail('D3', 'report.quality.rows is not an integer');
if (Number.isInteger(quality.cols) && quality.cols !== csv.header.length) {
  fail('D3', `report.quality.cols=${quality.cols} but the csv header has ${csv.header.length} columns`);
}
if (Number.isInteger(declared.n_rows) && Number.isInteger(quality.rows) && declared.n_rows !== quality.rows) {
  fail('D3', `selected_table.n_rows=${declared.n_rows} != quality.rows=${quality.rows}`);
}
for (const c of Array.isArray(quality.numeric_columns) ? quality.numeric_columns : []) {
  if (!csv.header.includes(String(c))) fail('D3', `report.quality.numeric_columns lists "${c}" which is not a csv header`);
}

// ── D4: time contract (skill convention: name hints + declared time column) ──
const TIME_HINTS = ['time', 'timestamp', 'datetime', 'date', 'zeit', 'ts_', '时间', '日期', '时刻'];
const isTimeHint = (h) => TIME_HINTS.some((k) => String(h).toLowerCase().includes(k));
const declaredTime = quality.time_column ?? declared.time_column ?? null;
if (declaredTime !== null && declaredTime !== undefined && declaredTime !== '') {
  if (!csv.header.includes(String(declaredTime))) {
    fail('D4', `declared time column "${declaredTime}" is not in the csv header`);
  }
} else if (csv.header.some(isTimeHint)) {
  note(`D4: header has time-hinted column(s) [${csv.header.filter(isTimeHint).join(', ')}] but the report declares no time_column — inspect the audit if time axis matters`);
} else {
  note('D4: no time-hinted column and no declared time_column — cross-sectional/time-less source (supported scenario; downstream time-series guards apply)');
}

// ── D5: selected_table.file resolves against --raw-path ────────────────
if (declared.file) {
  if (RAW_PATH !== undefined) {
    let resolved = null;
    try {
      if (statSync(RAW_PATH).isDirectory()) {
        const p = join(RAW_PATH, String(declared.file));
        if (existsSync(p)) resolved = p;
      } else if (basename(RAW_PATH) === basename(String(declared.file))) {
        resolved = RAW_PATH; // single-file input: the file IS the selected table
      }
    } catch (e) { /* statSync failure already handled by the ARGS check */ }
    if (!resolved) fail('D5', `selected_table.file "${declared.file}" does not resolve under --raw-path ${RAW_PATH}`);
  } else {
    note(`D5: selected_table.file "${declared.file}" not resolved (no --raw-path given)`);
  }
} else if (Number.isInteger(quality.rows)) {
  fail('D5', 'report.selected_table.file is missing on a produced table');
}

// ── D6: merge / dedup internal consistency ─────────────────────────────
const tableFiles = new Set((Array.isArray(report.tables) ? report.tables : []).map((t) => String(t?.file ?? '')));
const merge = report.merge && typeof report.merge === 'object' ? report.merge : null;
// outer_merge_on_time_column / abandoned : regular adaptive mode;
// single_primary_no_merge : --stability-single-primary folder mode (documented
// policy: one primary table, no resampling, no multi-cadence merge).
const MERGE_STRATEGIES = new Set(['outer_merge_on_time_column', 'abandoned', 'single_primary_no_merge']);
if (merge) {
  const strategy = String(merge.strategy || '');
  if (!MERGE_STRATEGIES.has(strategy)) fail('D6', `merge.strategy=${strategy || '(missing)'} not in {${[...MERGE_STRATEGIES].join(', ')}}`);
  const mergedFiles = Array.isArray(merge.merged_files) ? merge.merged_files.map(String) : [];
  for (const f of mergedFiles) {
    if (!tableFiles.has(f)) fail('D6', `merge.merged_files lists "${f}" which is not among report.tables[].file`);
  }
  if (strategy === 'outer_merge_on_time_column') {
    if (mergedFiles.length < 2) fail('D6', `outer merge recorded with only ${mergedFiles.length} merged file(s) — the merge gate requires >= 2`);
    const stc = merge.source_time_columns && typeof merge.source_time_columns === 'object' ? merge.source_time_columns : null;
    if (!stc) fail('D6', 'outer merge lacks source_time_columns');
    else {
      for (const k of Object.keys(stc)) {
        if (!mergedFiles.includes(String(k))) fail('D6', `source_time_columns key "${k}" is not in merged_files`);
      }
      const key = String(merge.key || '');
      const keyVals = Object.values(stc).map(String);
      if (!key || !(keyVals.includes(key) || String(merge.primary_time_column || '') === key)) {
        fail('D6', `merge.key "${key}" matches no source_time_columns value nor primary_time_column`);
      }
      // emitted csv rows must match the recorded merged row count
      if (Number.isInteger(declared.n_rows) && declared.n_rows !== csv.rows.length) {
        fail('D6', `merged table row count drift: selected_table.n_rows=${declared.n_rows} vs csv ${csv.rows.length}`);
      }
    }
  } else if (strategy === 'abandoned') {
    if (!String(merge.reason || '').trim()) fail('D6', 'abandoned merge lacks reason');
  } else if (strategy === 'single_primary_no_merge') {
    if (!String(merge.reason || '').trim()) fail('D6', 'single_primary_no_merge lacks reason (the one-primary policy must be disclosed)');
    if (mergedFiles.length) fail('D6', `single_primary_no_merge must not list merged files: ${mergedFiles.join(', ')}`);
  }
}

const EXCLUSION_CODES = new Set(['below_min_rows', 'no_timestamp', 'low_overlap', 'premerged_file_used', 'merge_not_attempted', 'single_primary_policy']);
for (const ex of Array.isArray(report.merge_exclusions) ? report.merge_exclusions : []) {
  const f = String(ex?.file ?? '');
  if (!tableFiles.has(f)) fail('D6', `merge_exclusions entry "${f}" is not among report.tables[].file`);
  if (!EXCLUSION_CODES.has(String(ex?.reason_code ?? ''))) {
    fail('D6', `merge_exclusions entry "${f}" has unknown reason_code "${ex?.reason_code}"`);
  }
}

// dedup disclosure: E-1 never applies dedup, but the audit must be arithmetically sound.
for (const t of Array.isArray(report.tables) ? report.tables : []) {
  const dup = t?.quality_flags?.exact_duplicate_rows;
  if (!dup || typeof dup !== 'object') continue;
  const n = Number(dup.count);
  if (!Number.isInteger(n) || n < 0) fail('D6', `tables[${t.file}].exact_duplicate_rows.count is not a non-negative integer`);
  if (Number.isInteger(n) && Number.isInteger(t.n_rows) && n > t.n_rows) {
    fail('D6', `tables[${t.file}].exact_duplicate_rows.count=${n} exceeds n_rows=${t.n_rows}`);
  }
  if (Number.isInteger(n) && n > 0 && (!Array.isArray(dup.row_indices_0based) || dup.row_indices_0based.length === 0)) {
    fail('D6', `tables[${t.file}] declares ${n} duplicate row(s) but lists no row indices`);
  }
  if (Array.isArray(dup.row_indices_0based)) {
    for (const i of dup.row_indices_0based) {
      if (!Number.isInteger(i) || i < 0 || (Number.isInteger(t.n_rows) && i >= t.n_rows)) {
        fail('D6', `tables[${t.file}].exact_duplicate_rows row index ${i} is out of range`);
      }
    }
  }
}
// The emitted csv row count equals the selected table's row count (dedup NOT applied).
if (Number.isInteger(declared.n_rows) && !merge && declared.n_rows !== csv.rows.length) {
  fail('D6', `selected_table.n_rows=${declared.n_rows} != emitted csv rows=${csv.rows.length} (E-1 never dedups; the counts must agree)`);
}

// ── D7: reported output paths resolve inside RUN_DIR/00_input ──────────
// Accepted forms: (a) the canonical in-place path, (b) RUN_DIR-relative or
// absolute paths that resolve inside 00_input, (c) a path whose canonical
// suffix is 00_input/<expected> (or 00_input/context/<file> for context
// entries) — this keeps moved/exported run dirs valid while still rejecting
// outputs written anywhere else (e.g. ../02_processed/x.csv).
const toSlash = (p) => String(p).replace(/\\/g, '/');
const partsOf = (p) => toSlash(p).replace(/\/+$/, '').split('/').filter(Boolean);
const insideDir = (base, p) => {
  const r = resolve(base, p);
  return r === resolve(base) || r.startsWith(resolve(base) + sep);
};
const OUTPUT_NAMES = { 'preprocessed_data.csv': 'preprocessed_data.csv', 'preprocessed_data.json': 'preprocessed_data.json', context_dir: 'context' };
const outputs = report.outputs && typeof report.outputs === 'object' ? report.outputs : null;
if (!outputs) {
  fail('D7', 'report.outputs is missing on a status=ok report');
} else {
  for (const [k, expectName] of Object.entries(OUTPUT_NAMES)) {
    const p = outputs[k];
    if (typeof p !== 'string' || !p.trim()) { fail('D7', `report.outputs.${k} is empty`); continue; }
    const parts = partsOf(p);
    const canonicalInPlace = resolve(RUN_DIR, p) === resolve(IN_DIR, expectName) || resolve(p) === resolve(IN_DIR, expectName);
    const inDir = insideDir(IN_DIR, p);
    const canonicalSuffix = parts[parts.length - 1] === expectName && parts[parts.length - 2] === '00_input';
    if (!canonicalInPlace && !inDir && !canonicalSuffix) {
      fail('D7', `report.outputs.${k} points outside 00_input (expected .../00_input/${expectName}): ${p}`);
    }
  }
  for (const k of Object.keys(outputs)) {
    if (!(k in OUTPUT_NAMES)) note(`D7: report.outputs has an extra key "${k}" (not part of the documented contract)`);
  }
}
for (const cf of Array.isArray(report.context_files) ? report.context_files : []) {
  if (typeof cf !== 'string' || !cf.trim()) { fail('D7', 'context_files contains an empty entry'); continue; }
  const parts = partsOf(cf);
  const inContext = insideDir(join(IN_DIR, 'context'), cf) || insideDir(IN_DIR, cf);
  const canonicalSuffix = parts.length >= 3 && parts[parts.length - 3] === '00_input' && parts[parts.length - 2] === 'context';
  if (!inContext && !canonicalSuffix) {
    fail('D7', `context_files entry resolves outside 00_input/context: ${cf}`);
  }
}

// ── verdict ────────────────────────────────────────────────────────────
if (FAILS.length) emit('gate_fail', null, { artifacts: { csv: CSV_PATH, report: REPORT_PATH } });
emit('ok', null, {
  rows: csv.rows.length,
  cols: csv.header.length,
  status: report.status,
  time_column: declaredTime ?? null,
  merged: !!(merge && merge.strategy === 'outer_merge_on_time_column'),
});
