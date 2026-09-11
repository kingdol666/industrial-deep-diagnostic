#!/usr/bin/env node
// test-pipeline-smoke.mjs — functional smoke matrix for the diagnostic system.
//
// Validates, per skill, that its deterministic entry point RUNS against a real
// benchmark run dir and yields the expected artifact/verdict — i.e. every skill
// works standalone AND the pipeline's integrated artifact set satisfies each
// stage's checker. Protocol-only skills (no scripts) are checked by their
// persisted artifacts + schema validation.
//
// Usage: node scripts/test-pipeline-smoke.mjs [--run-dir <dir>] [--json]
// Exit 0 = all PASS/WARN, 1 = at least one FAIL.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const PY = path.join(ROOT, '.claude/shared/scripts/.venv/Scripts/python.exe');
const VALIDATE = path.join(ROOT, '.claude/shared/scripts/validate.mjs');
const ONTOLOGY_STORE = path.join(ROOT, '.claude/shared/scripts/ontology_store.mjs');

const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);

// Pick the most recent complete benchmark run dir as fixture.
function defaultFixture() {
  const dir = path.join(ROOT, 'workspace', 'diagnostic-runs');
  const candidates = fs.readdirSync(dir)
    .filter((d) => d.includes('bench_') && fs.existsSync(path.join(dir, d, '05_review', 'judge_feedback.json')))
    .sort();
  return path.join(dir, candidates[candidates.length - 1] || '');
}

const rdArg = opt('--run-dir', '');
const RD = rdArg
  ? (path.isAbsolute(rdArg) ? rdArg : path.join(ROOT, rdArg))
  : defaultFixture();
if (!fs.existsSync(RD)) {
  console.error(`fixture run dir not found: ${RD}`);
  process.exit(2);
}

const results = [];
let fails = 0;
let warns = 0;

function check(skill, name, fn) {
  try {
    const detail = fn();
    results.push(`PASS  ${skill.padEnd(34)} ${name}${detail ? ` — ${detail}` : ''}`);
  } catch (e) {
    const warn = e.warn === true;
    if (warn) warns += 1; else fails += 1;
    results.push(`${warn ? 'WARN' : 'FAIL'}  ${skill.padEnd(34)} ${name}${e.message ? ` — ${e.message}` : ''}`);
  }
}

function run(cmd, cmdArgs, { cwd = ROOT, timeout = 120000 } = {}) {
  return execFileSync(cmd, cmdArgs, { cwd, encoding: 'utf8', timeout, stdio: ['ignore', 'pipe', 'pipe'] });
}

function mustExist(p, label) {
  if (!fs.existsSync(p)) throw new Error(`${label} missing: ${path.relative(ROOT, p)}`);
  return `${path.relative(ROOT, p)} (${fs.statSync(p).size}B)`;
}

const f = (rel) => path.join(RD, rel);
const events = fs.readFileSync(f('.pipeline_events.jsonl'), 'utf8').trim().split('\n').map((l) => { try { return JSON.parse(l); } catch { return {}; } });

// ── 1. industrial-analysis-auto — pipeline orchestration + execution proof ──
check('industrial-analysis-auto', 'pipeline-log-check PASS', () => {
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs'), RD]);
  if (!/PASS|ok/i.test(out)) throw new Error(out.slice(0, 120));
  return 'event log accepted';
});
check('industrial-analysis-auto', 'execution-proof steps present', () => {
  const kinds = new Set(events.map((e) => e.type || e.event || ''));
  for (const required of ['run_initialized', 'step_complete']) {
    if (!kinds.has(required)) throw new Error(`missing event type: ${required}`);
  }
  return `${events.length} events`;
});
check('industrial-analysis-auto', 'finalize report overall=PASS', () => {
  const reps = ['pipeline_final_report.json', 'finalize_report.json', 'pipeline-finalize_report.json'];
  const p = reps.map((r) => f(r)).find((x) => fs.existsSync(x));
  if (!p) throw Object.assign(new Error('finalize report not found (checked 3 names)'), { warn: true });
  const j = JSON.parse(fs.readFileSync(p, 'utf8'));
  if (!/PASS|ENDORSED/i.test(JSON.stringify(j.overall || j.status || j))) throw new Error(`overall=${JSON.stringify(j.overall || j.status).slice(0, 60)}`);
  return `overall OK (${path.basename(p)})`;
});

// ── 2. industrial-data-preprocessor — cleaning entry ──
check('industrial-data-preprocessor', 'data_preprocessor.py CLI responds', () => {
  const out = run(PY, [path.join(ROOT, '.claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py'), '--help'], { timeout: 60000 });
  if (!/--|usage|input/i.test(out)) throw new Error('no CLI surface found');
  return 'CLI OK';
});
check('industrial-data-preprocessor', 'cleaning artifacts present in run', () => {
  return mustExist(f('02_processed/cleaned_data.json'), 'cleaned_data.json');
});

// ── 3. industrial-data-processor — stats/validation/finalize ──
check('industrial-data-processor', 'feature_summary validates against schema', () => {
  run('node', [VALIDATE, path.join(ROOT, '.claude/shared/schemas/feature_summary_schema.json'), f('02_processed/feature_summary.json')]);
  return 'schema OK';
});
check('industrial-data-processor', 'cleaning integrity check', () => {
  const script = path.join(ROOT, '.claude/skills/industrial-data-processor/scripts/cleaning_integrity_check.py');
  const out = run(PY, [script, RD, f('00_input/data.csv')], { timeout: 120000 });
  if (/FAIL/i.test(out)) throw new Error(out.slice(0, 120));
  return 'integrity OK';
});
check('industrial-data-processor', 'anomaly report present', () => mustExist(f('02_processed/anomaly_report.json'), 'anomaly_report.json'));

// ── 4. industrial-ontology-builder — persistence round-trip (persistent editing and storage of the ontology) ──
check('industrial-ontology-builder', 'ontology validates against schema', () => {
  run('node', [VALIDATE, path.join(ROOT, '.claude/shared/schemas/ontology_schema.json'), f('01_ontology/ontology.json')]);
  return 'schema OK';
});
check('industrial-ontology-builder', 'store publish → list → find → reuse (persistence round-trip)', () => {
  const tmp = fs.mkdtempSync(path.join(ROOT, 'workspace', 'ontology-store-smoke-'));
  const rd = path.join(tmp, 'run');
  fs.mkdirSync(path.join(rd, '01_ontology'), { recursive: true });
  fs.copyFileSync(f('01_ontology/ontology.json'), path.join(rd, '01_ontology/ontology.json'));
  const pub = run('node', [ONTOLOGY_STORE, 'publish', '--run-dir', rd, '--scene', `smoke_persist_${Date.now()}`, '--build-mode', 'full']);
  if (!/published|ok|scene/i.test(pub)) throw new Error(`publish: ${pub.slice(0, 100)}`);
  const list = run('node', [ONTOLOGY_STORE, 'list']);
  if (!/smoke_persist_/.test(list)) throw new Error('published scene not visible in store list');
  const targetDir = path.join(ROOT, 'data/benchmark/prepared/skab');
  if (fs.existsSync(targetDir)) {
    const found = run('node', [ONTOLOGY_STORE, 'find', targetDir]);
    const match = String(found).match(/"match"\s*:\s*"(\w+)"/);
    if (!match) throw new Error(`find: ${found.slice(0, 100)}`);
    if (match[1] === 'miss') return 'find responds (cross-dataset fingerprint miss = correct)';
  }
  fs.rmSync(tmp, { recursive: true, force: true });
  return 'publish/list/find round-trip OK';
});

// ── 5. industrial-diagnostician — diagnosis quality gates on real artifacts ──
check('industrial-diagnostician', 'diagnosis.json + evidence + confidence present', () => {
  for (const p of ['04_diagnostics/diagnosis.json', '04_diagnostics/evidence.json', '04_diagnostics/confidence.json', '04_diagnostics/reasoning_chain.json']) mustExist(f(p), p);
  return 'artifact set complete';
});
check('industrial-diagnostician', 'root-cause conclusion present (per design logic)', () => {
  const d = JSON.parse(fs.readFileSync(f('04_diagnostics/diagnosis.json'), 'utf8'));
  const type = d.diagnosis_type;
  if (!['DETERMINED', 'COMPETING_SET', 'NEEDS_DATA'].includes(type)) throw new Error(`type=${type}`);
  if (!d.primary_finding) throw new Error('missing primary_finding');
  const hyp = d.hypotheses || {};
  if (type === 'DETERMINED' && (hyp.surviving || []).length < 1) throw new Error('DETERMINED without surviving hypothesis');
  return `type=${type}, surviving=${(hyp.surviving || []).length}, eliminated=${(hyp.eliminated || []).length}`;
});
check('industrial-diagnostician', 'parameter relationships present (correlation/association)', () => {
  const d = JSON.parse(fs.readFileSync(f('04_diagnostics/diagnosis.json'), 'utf8'));
  const links = d.integrated_dual_drive_analysis?.process_to_quality_links
    || d.integrated_dual_drive_analysis?.cross_domain_links || [];
  if (links.length) return `dual-drive links: ${links.length}`;
  const vr = JSON.parse(fs.readFileSync(f('02_processed/validate_report.json'), 'utf8'));
  const pairs = JSON.stringify(vr).match(/"(top_pairs|cross_domain_links|correlations)"/);
  if (pairs) return `in validate_report (${pairs[1]})`;
  throw Object.assign(new Error('no parameter-relationship block found'), { warn: true });
});
check('industrial-diagnostician', 'diagnostic-quality-check', () => {
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-diagnostician/scripts/diagnostic-quality-check.mjs'), RD]);
  if (/FAIL/i.test(out)) throw new Error(out.slice(0, 120));
  return 'quality gate OK';
});

// ── 6. industrial-judge — quality gate ──
check('industrial-judge', 'judge_feedback validates + gate check', () => {
  run('node', [VALIDATE, path.join(ROOT, '.claude/shared/schemas/judge_feedback_schema.json'), f('05_review/judge_feedback.json')]);
  const jf = JSON.parse(fs.readFileSync(f('05_review/judge_feedback.json'), 'utf8'));
  const score = jf.overall_score ?? jf.score;
  if (!(score >= 0 && score <= 100)) throw new Error(`judge score=${score}`);
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-judge/scripts/judge-gate-check.mjs'), RD]);
  return `score=${score}, gate=${/PASS|ENDORSED|ok/i.test(out) ? 'OK' : 'see output'}`;
});

// ── 7. industrial-physical-auditor — audit artifacts ──
check('industrial-physical-auditor', 'audit artifacts present', () => {
  const p = ['optimizer.md', 'optimizer_preflight.md', '05_review/audit_report.json'].map((x) => f(x)).find((x) => fs.existsSync(x));
  if (!p) throw Object.assign(new Error('no audit artifact (optimizer*.md / audit_report.json)'), { warn: true });
  return path.relative(RD, p);
});

// ── 8. industrial-reporter — report + summary ──
check('industrial-reporter', 'report.md present + section check', () => {
  mustExist(f('report.md'), 'report.md');
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-reporter/scripts/report-section-check.mjs'), RD]);
  const rep = JSON.parse(out);
  if (rep.status !== 'PASS') throw new Error(`missing: ${(rep.missing_sections || []).join(', ')}`);
  return `sections ${rep.found_count}/${rep.total_sections} OK`;
});
check('industrial-reporter', 'run_summary synthesis (idempotent regen)', () => {
  run('node', [path.join(ROOT, '.claude/skills/industrial-reporter/scripts/synthesize-run-summary.mjs'), RD]);
  return mustExist(f('run_summary.json'), 'run_summary.json');
});

// ── 9. html-visualizer / html-reviewer ──
check('industrial-html-visualizer', 'diagnostic-report.html present (≥5KB)', () => {
  const p = mustExist(f('diagnostic-report.html'), 'diagnostic-report.html');
  if (fs.statSync(f('diagnostic-report.html')).size < 5120) throw new Error('report suspiciously small');
  return p;
});
check('industrial-html-reviewer', 'html_review.json validates', () => {
  run('node', [VALIDATE, path.join(ROOT, '.claude/shared/schemas/html_review_schema.json'), f('05_review/html_review.json')]);
  return 'schema OK';
});

// ── 10. industrial-deep-analysis — coverage rebuild (idempotent) ──
check('industrial-deep-analysis', 'coverage_builder rebuild', () => {
  run(PY, [path.join(ROOT, '.claude/skills/industrial-deep-analysis/scripts/coverage_builder.py'), '--run-dir', RD], { timeout: 180000 });
  const coverage = f('enhancement/analysis_coverage.json');
  if (fs.existsSync(coverage)) return path.relative(RD, coverage);
  return mustExist(f('03_figures/plot_manifest.json'), 'plot_manifest.json');
});

// ── 11. industrial-physics-bridge ──
check('industrial-physics-bridge', 'physics artifacts present or rebuildable', () => {
  const p = ['enhancement/physics_bridge.json', '04_diagnostics/physics_check.json'].map((x) => f(x)).find((x) => fs.existsSync(x));
  if (p) return path.relative(RD, p);
  throw Object.assign(new Error('physics bridge artifact absent in this run tier'), { warn: true });
});

// ── 12. industrial-analysis-enhance-auto — E0 gate on a baseline-only run ──
check('industrial-analysis-enhance-auto', 'E0 gate behaves deterministically', () => {
  let out = '';
  try {
    out = run('node', [path.join(ROOT, '.claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs'), '--run-dir', RD], { timeout: 300000 });
  } catch (e) {
    out = String(e.stdout || '') + String(e.message || '');
  }
  const statusPath = f('enhancement/enhancement_status.json');
  if (fs.existsSync(statusPath)) {
    const st = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
    if (st.status === 'READY') return 'READY (full enhancement ran)';
    if (st.status === 'BLOCKED' && Array.isArray(st.missing)) return `BLOCKED gate correct (${st.missing.length} baseline files absent — expected for baseline-only tier)`;
    throw new Error(`unexpected enhancement_status: ${st.status}`);
  }
  if (/READY/.test(out)) return 'READY (full enhancement)';
  throw new Error('no enhancement_status.json produced');
});

// ── 13. rag-knowledge-builder — CLI surface (server-independent) ──
check('rag-knowledge-builder', 'rag_client.py CLI responds', () => {
  const out = run(PY, [path.join(ROOT, '.claude/skills/rag-knowledge-builder/scripts/rag_client.py'), '--help'], { timeout: 60000 });
  if (!/--|usage|retrieve/i.test(out)) throw new Error('no CLI surface');
  return 'CLI OK';
});

// ── 14. industrial-benchmark-runner — reproducibility gate ──
check('industrial-benchmark-runner', 'verify-repro REPRODUCIBLE', () => {
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs')]);
  if (!/REPRODUCIBLE/.test(out)) throw new Error(out.slice(-120));
  return 'gates green';
});

// ── 15. protocol-only skills — spec compliance + artifact evidence ──
for (const [skill, evidence] of [
  ['darwin-skill', null],
  ['diagnostic-html-visualizer', 'diagnostic-report.html'],
  ['industrial-enhanced-html-visualizer', null],
  ['industrial-enhanced-html-reviewer', null],
]) {
  check(skill, 'SKILL.md spec frontmatter', () => {
    const md = fs.readFileSync(path.join(ROOT, '.claude/skills', skill, 'SKILL.md'), 'utf8').replace(/^\uFEFF/, '');
    if (!/^---\r?\nname: /.test(md)) throw new Error('frontmatter missing');
    if (!/Trigger:/i.test(md.slice(0, 1500))) throw new Error('description lacks Trigger keywords');
    return `${md.split('\n').length} lines`;
  });
  if (evidence) {
    check(skill, 'pipeline artifact evidence', () => mustExist(f(evidence), evidence));
  }
}

// ── summary ──
const pass = results.filter((r) => r.startsWith('PASS')).length;
console.log(results.join('\n'));
console.log(`\nfixture: ${path.relative(ROOT, RD)}`);
console.log(`${pass} PASS / ${warns} WARN / ${fails} FAIL`);
if (args.includes('--json')) {
  fs.writeFileSync(path.join(ROOT, 'results', 'pipeline-smoke.json'), JSON.stringify({ fixture: RD, pass, warns, fails, results }, null, 1));
}
process.exit(fails > 0 ? 1 : 0);
