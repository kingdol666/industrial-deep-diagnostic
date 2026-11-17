#!/usr/bin/env node
// quality_gate.mjs — enhanced build gate (enhanced-analysis.html + html_selfcheck.json marker).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--html <path>] [--marker <path>]
// Exit: 0 ok | 1 hard error (bad inputs) | 2 undetermined (page or marker absent — build not run)
//       | 3 gate-fail (artifact present but corrupt/non-compliant)
//
// Defaults: <RUN_DIR>/enhancement/enhanced-analysis.html and <RUN_DIR>/enhancement/html_selfcheck.json
// (exact paths written by scripts/html_builder.py).
//
// Checks:
//   E1 page + marker both exist (else undetermined)  E2 page >= 5120 bytes, real <title>, HTML structure
//   E3 marker parses as JSON                         E4 marker identity: builder == "enhanced_html_builder"
//   E5 marker claims: charts_built == 5, size_requirement_met == true, html_size_bytes >= 5120
//   E6 marker lists the 3 CDN sources                E7 page contains the 5 chart containers + ECharts loader

import { existsSync, readFileSync, statSync } from 'fs';
import { resolve } from 'path';

const MIN_BYTES = 5120;
const CHART_CONTAINERS = ['chartNetwork', 'chartHeatmap', 'radarGrid', 'chartOperMatrix', 'physicsGrid'];
const CDN_MARKERS = ['cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com'];
const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR = argOf('--run-dir') || args.find((a) => !a.startsWith('--'));
const HTML = argOf('--html') || (RUN_DIR ? resolve(RUN_DIR, 'enhancement', 'enhanced-analysis.html') : '');
const MARKER = argOf('--marker') || (RUN_DIR ? resolve(RUN_DIR, 'enhancement', 'html_selfcheck.json') : '');

const FAILS = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const emit = (verdict, extra = {}) => {
  console.log(JSON.stringify({
    gate: 'enhanced_html_visualizer_quality_gate', html: HTML, marker: MARKER, run_dir: RUN_DIR || null,
    verdict, fails: FAILS, ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
};

if (!RUN_DIR && !(argOf('--html') && argOf('--marker'))) {
  emit('hard_error', { reason: 'usage: quality_gate.mjs --run-dir <RUN_DIR> [--html <path>] [--marker <path>]' });
}

// ── E1: both artifacts exist ────────────────────────────────────────────────
const missing = [HTML, MARKER].filter((p) => !existsSync(p) || !statSync(p).isFile());
if (missing.length) {
  emit('undetermined', {
    reason: `enhanced build artifacts absent (${missing.join(', ')}) — industrial-enhanced-html-visualizer has not run`,
  });
}

// ── E2: page checks ─────────────────────────────────────────────────────────
const html = readFileSync(HTML, 'utf-8');
const low = html.toLowerCase();
const bytes = Buffer.byteLength(html, 'utf-8');
const title = (html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i) || [])[1];
if (bytes < MIN_BYTES) fail('E2', `enhanced-analysis.html is ${bytes} bytes (< ${MIN_BYTES})`);
if (!['<html', '</html>', '<head', '<body'].every((t) => low.includes(t)) || !title) {
  fail('E2', 'enhanced-analysis.html is not a parseable HTML document (structure or <title> missing)');
}
if (title !== undefined && !title.trim()) fail('E2', 'empty <title> — placeholder page');

// ── E3: marker parses ───────────────────────────────────────────────────────
let marker;
try { marker = JSON.parse(readFileSync(MARKER, 'utf-8')); }
catch (e) { fail('E3', `html_selfcheck.json unparseable: ${e.message}`); emit('gate_fail'); }
if (typeof marker !== 'object' || marker === null || Array.isArray(marker)) {
  fail('E3', 'html_selfcheck.json is not a JSON object'); emit('gate_fail');
}

// ── E4: marker identity ─────────────────────────────────────────────────────
if (marker.builder !== 'enhanced_html_builder') {
  fail('E4', `marker builder is "${marker.builder}" (expected "enhanced_html_builder")`);
}

// ── E5: marker claims ───────────────────────────────────────────────────────
if (marker.charts_built !== 5) fail('E5', `marker charts_built is ${marker.charts_built} (expected 5)`);
if (marker.size_requirement_met !== true) fail('E5', 'marker size_requirement_met is not true');
if (!(Number(marker.html_size_bytes) >= MIN_BYTES)) {
  fail('E5', `marker html_size_bytes is ${marker.html_size_bytes} (< ${MIN_BYTES})`);
}
if (Array.isArray(marker.chart_types) && marker.chart_types.length !== 5) {
  fail('E5', `marker chart_types has ${marker.chart_types.length} entries (expected 5)`);
}

// ── E6: CDN sources ─────────────────────────────────────────────────────────
const cdn = Array.isArray(marker.echarts_cdn_sources) ? marker.echarts_cdn_sources.join(' ') : '';
const cdnMissing = CDN_MARKERS.filter((m) => !cdn.includes(m));
if (cdnMissing.length) fail('E6', `marker echarts_cdn_sources missing: ${cdnMissing.join(', ')}`);

// ── E7: page carries the load contract ──────────────────────────────────────
const containersMissing = CHART_CONTAINERS.filter((id) => !html.includes(id));
if (containersMissing.length) fail('E7', `page missing chart containers: ${containersMissing.join(', ')}`);
if (!html.includes('echarts_available') || !html.includes('staticFallback')) {
  fail('E7', 'page missing runtime self-check / static fallback wiring');
}

emit(FAILS.length ? 'gate_fail' : 'ok', {
  bytes,
  title: (title || '').trim().slice(0, 120),
  marker_builder: marker.builder,
  charts_built: marker.charts_built,
});
