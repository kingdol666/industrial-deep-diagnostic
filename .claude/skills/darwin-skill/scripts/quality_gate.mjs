#!/usr/bin/env node
// quality_gate.mjs — darwin-skill evaluation-log quality gate (house pattern).
//
// Usage: node quality_gate.mjs [--file <results.tsv>]
//        (default: <this-skill-dir>/results.tsv)
// Exit: 0 ok | 1 hard error (file missing/unreadable, bad args)
//       | 2 undetermined (header present, zero evaluations recorded)
//       | 3 gate-fail (any D-check failed)
//
// The artifact contract is the 9-column results.tsv table documented in
// SKILL.md (timestamp/commit/skill/old_score/new_score/status/dimension/note/
// eval_mode). Comment lines starting with '#' and blank lines are allowed and
// skipped — the log's own history contains one mid-file phase comment.
//
// Checks (all mechanical):
//   D1 header: exactly the 9 documented columns, exact names, exact order
//   D2 every data line splits into exactly 9 tab-separated fields
//   D3 timestamp matches ^YYYY-MM-DDTHH:MM(:SS)?(+HH:MM)?$ — minute precision
//      is the established floor (the first baseline row uses it) and the offset
//      suffix is in actual use in later entries
//   D4 old_score/new_score are '-' or an integer in 0..999 (the historical
//      scale is 0-100-ish; later entries legitimately record >100)
//   D5 status is a lowercase slug; documented statuses are
//      baseline|improved|regressed|optimized — any other slug is accepted but
//      reported as a vocabulary-drift note (the log's own history uses
//      ecosystem_fix / independence_audit; a closed enum would fail it)
//   D6 eval_mode is dry_run or live (closed enum — both documented and the
//      only values ever recorded)
//   D7 score monotonic sanity when both scores are numeric:
//      improved/optimized => new >= old ; regressed => new <= old
//
// Zero dependencies (node builtins only).

import { existsSync, readFileSync, statSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const FILE = resolve(argOf('--file') || join(HERE, '..', 'results.tsv'));

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);
process.on('uncaughtException', (e) => {
  console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict: 'gate_fail', fails: [...FAILS, `GATE: unhandled error: ${e.message}`], notes: NOTES }, null, 2));
  process.exit(3);
});

const HEADER = ['timestamp', 'commit', 'skill', 'old_score', 'new_score', 'status', 'dimension', 'note', 'eval_mode'];
const DOCUMENTED_STATUSES = new Set(['baseline', 'improved', 'regressed', 'optimized']);
const EVAL_MODES = new Set(['dry_run', 'live']);
const TS_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2})?$/;
const SCORE_RE = /^\d{1,3}$/;
const SCORE_MAX = 999;
const SLUG_RE = /^[a-z][a-z0-9_]*$/;
const KNOWN_KEBAB_RE = /^[a-z0-9][a-z0-9._+-]*$/;

// ── inputs ────────────────────────────────────────────────────────────
if (!existsSync(FILE) || !statSync(FILE).isFile()) {
  console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict: 'hard_error', reason: `results file missing or not a file: ${FILE}` }, null, 2));
  process.exit(1);
}
let raw;
try { raw = readFileSync(FILE, 'utf-8'); } catch (e) {
  console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict: 'hard_error', reason: `unreadable: ${e.message}` }, null, 2));
  process.exit(1);
}
const lines = raw.replace(/^\uFEFF/, '').split(/\r?\n/);
const dataLines = [];
let headerSeen = null;
let lineNo = 0;
for (const line of lines) {
  lineNo += 1;
  if (line.trim() === '' || line.trimStart().startsWith('#')) continue;
  if (headerSeen === null) { headerSeen = { line, lineNo }; continue; }
  dataLines.push({ line, lineNo });
}

if (headerSeen === null) {
  console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict: 'hard_error', reason: 'no header row found' }, null, 2));
  process.exit(1);
}
if (dataLines.length === 0) {
  console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict: 'undetermined', reason: 'header present but zero evaluations recorded — nothing to validate yet' }, null, 2));
  process.exit(2);
}

// ── D1 header ─────────────────────────────────────────────────────────
const header = headerSeen.line.split('\t');
if (header.length !== 9 || !header.every((c, i) => c.trim() === HEADER[i])) {
  fail('D1', `header mismatch at line ${headerSeen.lineNo}: got [${header.join('|')}], want [${HEADER.join('|')}]`);
}

// ── per-row checks ────────────────────────────────────────────────────
let checked = 0;
let driftStatuses = new Set();
for (const { line, lineNo } of dataLines) {
  const f = line.split('\t');
  if (f.length !== 9) { fail('D2', `line ${lineNo}: ${f.length} fields, want 9`); continue; }
  const [timestamp, commit, skill, oldScore, newScore, status, dimension, , evalMode] = f.map((s) => s.trim());
  checked += 1;

  if (!TS_RE.test(timestamp)) fail('D3', `line ${lineNo}: timestamp "${timestamp}" is not YYYY-MM-DDTHH:MM[:SS][+HH:MM]`);
  for (const [label, v] of [['old_score', oldScore], ['new_score', newScore]]) {
    if (v === '-') continue;
    if (!SCORE_RE.test(v) || Number(v) > SCORE_MAX) fail('D4', `line ${lineNo}: ${label} "${v}" is not '-' or an integer 0..${SCORE_MAX}`);
  }
  if (!SLUG_RE.test(status)) fail('D5', `line ${lineNo}: status "${status}" is not a lowercase slug`);
  else if (!DOCUMENTED_STATUSES.has(status)) driftStatuses.add(status);
  if (dimension === '') fail('D5', `line ${lineNo}: dimension is empty ('-' allowed)`);
  if (!EVAL_MODES.has(evalMode)) fail('D6', `line ${lineNo}: eval_mode "${evalMode}" not in {dry_run, live}`);
  if (commit === '') fail('D5', `line ${lineNo}: commit is empty`);
  if (!KNOWN_KEBAB_RE.test(skill)) fail('D5', `line ${lineNo}: skill "${skill}" is not a kebab-ish slug`);

  // D7 monotonic sanity — only when both scores are numeric
  const o = oldScore === '-' ? null : Number(oldScore);
  const n = newScore === '-' ? null : Number(newScore);
  if (o !== null && n !== null) {
    if ((status === 'improved' || status === 'optimized') && n < o) {
      fail('D7', `line ${lineNo}: status ${status} but score decreased ${o} -> ${n}`);
    }
    if (status === 'regressed' && n > o) {
      fail('D7', `line ${lineNo}: status regressed but score increased ${o} -> ${n}`);
    }
  }
}
if (driftStatuses.size) {
  note(`status vocabulary beyond the documented set (accepted, logged for drift): ${[...driftStatuses].sort().join(', ')}`);
}

// ── verdict ───────────────────────────────────────────────────────────
const verdict = FAILS.length ? 'gate_fail' : 'ok';
console.log(JSON.stringify({ gate: 'darwin_quality_gate', verdict, file: FILE, evaluations: checked, fails: FAILS, notes: NOTES }, null, 2));
process.exit(FAILS.length ? 3 : 0);
