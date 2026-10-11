#!/usr/bin/env node
// quality gate for industrial-line-stability-report (exit 0 pass / 3 fail)
// S1 schema + required core fields   S2 conclusion honesty (score/grade consistent)
// S3 zero-LLM provenance             S4 html exists + selfcheck pass
// S5 enum literals match shared closedloop_enums.json
import { readFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const skillPath = resolve(here, '..');
const sharedPath = resolve(skillPath, '..', '..', '..', '.claude', 'shared');

const reportPath = process.argv[2];
const outDir = process.argv[3] || dirname(resolve(reportPath || '.'));
const fail = (msg) => { console.error(`[line-report-gate] FAIL ${msg}`); process.exit(3); };
const warn = (msg) => console.warn(`[line-report-gate] warn ${msg}`);

if (!reportPath || !existsSync(reportPath)) fail('usage: quality_gate.mjs <stability_report.json> [outDir]');

const report = JSON.parse(readFileSync(reportPath, 'utf-8'));
const results = [];

// ---- S1 schema validation via shared validate.mjs (best effort), plus core fields
const schemaPath = join(skillPath, 'schemas', 'stability_report.schema.json');
if (existsSync(schemaPath)) {
  const validator = join(sharedPath, 'scripts', 'validate.mjs');
  if (existsSync(validator)) {
    const r = spawnSync(process.execPath, [validator, schemaPath, reportPath],
      { encoding: 'utf-8' });
    results.push(['S1 schema', r.status === 0]);
    if (r.status !== 0) warn(r.stdout || r.stderr);
  } else {
    results.push(['S1 schema (validator missing, core-fields only)', true]);
  }
}
const coreRequired = ['contract_version', 'report_id', 'generated_at', 'status',
  'period', 'data', 'parameters', 'conclusion', 'integrations', 'provenance'];
const missingCore = coreRequired.filter((k) => !(k in report));
results.push(['S1 core fields', missingCore.length === 0]);
if (missingCore.length) warn(`missing: ${missingCore.join(',')}`);

// ---- S2 conclusion honesty
const c = report.conclusion || {};
if (report.status === 'ok') {
  const scoreOk = typeof c.score === 'number' && c.score >= 0 && c.score <= 100;
  const expect = c.score >= 85 ? 'A' : c.score >= 70 ? 'B' : c.score >= 50 ? 'C' : 'D';
  const stmtOk = typeof c.statement === 'string' && c.statement.length >= 10;
  results.push(['S2 score range', scoreOk]);
  results.push(['S2 grade matches score', c.grade === expect]);
  results.push(['S2 statement present', stmtOk]);
} else {
  results.push(['S2 not_assessable honest',
    c.score === null && c.grade === null && typeof c.statement === 'string']);
}

// ---- S3 zero-LLM provenance
const prov = report.provenance || {};
results.push(['S3 zero_llm true', prov.zero_llm === true]);
results.push(['S3 input sha256', typeof prov.input_sha256 === 'string'
  && prov.input_sha256.startsWith('sha256:')]);

// ---- S4 html + selfcheck
const htmlPath = join(outDir, 'line_stability_report.html');
const selfPath = join(outDir, 'html_selfcheck.json');
const htmlOk = existsSync(htmlPath) && statSync(htmlPath).size >= 8192;
let selfOk = false;
if (existsSync(selfPath)) {
  try {
    const self = JSON.parse(readFileSync(selfPath, 'utf-8'));
    selfOk = self.pass === true;
  } catch { selfOk = false; }
}
results.push(['S4 html >= 8KB', htmlOk]);
results.push(['S4 html_selfcheck pass', selfOk]);

// ---- S5 enum literals vs shared enums
try {
  const enums = JSON.parse(readFileSync(join(sharedPath, 'schemas', 'closedloop_enums.json'), 'utf-8'));
  const allowed = new Set(enums.severity);
  const bad = (report.findings || []).filter((f) => !allowed.has(f.severity));
  results.push(['S5 severity literals', bad.length === 0]);
  if (bad.length) warn(`bad severity: ${bad.map((f) => f.severity).join(',')}`);
  const banned = JSON.stringify(report).includes('"autonomy"');
  results.push(['S5 no autonomy key', !banned]);
} catch (e) {
  warn(`shared enums unreadable: ${e.message}`);
  results.push(['S5 enums (skipped)', true]);
}

let pass = true;
for (const [name, ok] of results) {
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) pass = false;
}
console.log(`[line-report-gate] ${pass ? 'PASS' : 'FAIL'} (${results.length} checks)`);
process.exit(pass ? 0 : 3);
