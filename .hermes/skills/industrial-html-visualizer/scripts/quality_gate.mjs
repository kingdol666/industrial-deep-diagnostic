#!/usr/bin/env node
// quality_gate.mjs — Step 8 page gate (plain diagnostic-report.html).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--html <path>]
// Exit: 0 ok | 1 hard error (bad inputs) | 2 undetermined (page absent — Step 8 not run)
//       | 3 gate-fail (page present but corrupt/undersized/unparseable)
//
// Checks (all mechanical, node builtins only):
//   V1 page exists (else undetermined)         V2 >= MIN_BYTES (5120)
//   V3 looks like HTML (html/head/body tags)   V4 non-empty <title>
//   V5 no NUL bytes (binary garbage)           V6 script/style tags balanced

import { existsSync, readFileSync, statSync } from 'fs';
import { resolve } from 'path';

const MIN_BYTES = 5120;
const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR = argOf('--run-dir') || args.find((a) => !a.startsWith('--'));
const HTML = resolve(argOf('--html') || (RUN_DIR ? resolve(RUN_DIR, 'diagnostic-report.html') : '.'));
const TARGET = RUN_DIR ? resolve(RUN_DIR, 'diagnostic-report.html') : HTML;

const FAILS = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const emit = (verdict, extra = {}) => {
  console.log(JSON.stringify({
    gate: 'html_visualizer_quality_gate', artifact: HTML, run_dir: RUN_DIR || null, verdict,
    fails: FAILS, ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
};

// bad invocation is a hard error, never a silent pass
if (!RUN_DIR && !argOf('--html')) {
  emit('hard_error', { reason: 'usage: quality_gate.mjs --run-dir <RUN_DIR> [--html <path>]' });
}

// ── V1: exists ──────────────────────────────────────────────────────────────
if (!existsSync(HTML) || !statSync(HTML).isFile()) {
  emit('undetermined', { reason: `${TARGET} absent — Step 8 (industrial-html-visualizer) has not run` });
}

let text;
try { text = readFileSync(HTML, 'utf-8'); }
catch (e) { fail('V1', `page unreadable: ${e.message}`); emit('gate_fail'); }

const low = text.toLowerCase();
const bytes = Buffer.byteLength(text, 'utf-8');
const title = (text.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i) || [])[1];
const structureOk = ['<html', '</html>', '<head', '<body'].every((t) => low.includes(t))
  && /<title\b[^>]*>[\s\S]*?<\/title>/i.test(text);
const tagBalance = {};
for (const tag of ['script', 'style']) {
  const open = (low.match(new RegExp(`<${tag}\\b`, 'g')) || []).length;
  const close = (low.match(new RegExp(`</${tag}>`, 'g')) || []).length;
  tagBalance[tag] = { open, close };
}

// ── V2: size sanity ─────────────────────────────────────────────────────────
if (bytes < MIN_BYTES) fail('V2', `page is ${bytes} bytes (< ${MIN_BYTES} minimum)`);
// ── V3: HTML structure ──────────────────────────────────────────────────────
if (!structureOk) fail('V3', 'not a parseable HTML document (missing html/head/body or <title>)');
// ── V4: real title ──────────────────────────────────────────────────────────
if (title !== undefined && !title.trim()) fail('V4', 'empty <title> — placeholder page');
// ── V5: binary garbage ──────────────────────────────────────────────────────
if (text.includes('\u0000')) fail('V5', 'NUL byte found — file is not text/HTML');
// ── V6: tag balance (cheap well-formedness signal) ──────────────────────────
for (const [tag, c] of Object.entries(tagBalance)) {
  if (c.open !== c.close) fail('V6', `unbalanced <${tag}> tags: ${c.open} open vs ${c.close} close`);
}

emit(FAILS.length ? 'gate_fail' : 'ok', {
  bytes,
  title: (title || '').trim().slice(0, 120),
  checks: { V1: true, V2: bytes >= MIN_BYTES, V3: structureOk, V4: !!title && !!title.trim(), V5: !text.includes('\u0000'), V6: Object.values(tagBalance).every((c) => c.open === c.close) },
});
