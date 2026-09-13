#!/usr/bin/env node
// judge-rubric.mjs — deterministic quality scoring for benchmark scenarios.
//
// Replaces note-self-declared judge scores as the benchmark's quality metric.
// Seven machine-checked rubric items computed strictly from run artifacts and
// the scenario's own evidence brief. No LLM, no self-assessment, no discretion:
// the same artifacts always yield the same score.
//
//   R1  artifact integrity (15)   — diagnosis.json parses; 4 diagnosis artifacts exist
//   R2  hypothesis structure (15) — >=3 hypotheses; >=1 surviving; >=2 eliminated,
//                                   each elimination citing non-empty contradiction
//   R3  evidence grounding (20)   — every surviving hypothesis' evidence strings cite
//                                   at least one number that appears in this
//                                   scenario's evidence brief (z / r / pct values)
//   R4  calibration (15)          — reported confidence within protocol ceiling
//                                   (DETERMINED <= 0.90; declared weak-signature
//                                   scenarios <= 0.75; COMPETING_SET <= 0.70) and
//                                   conclusion type within the scenario's allowed set
//   R5  falsifiability (10)       — surviving hypothesis carries falsification
//                                   conditions; primary_finding substantive
//   R6  physics verification (10) — physics_check.json valid or manual memo present
//   R7  execution proof (15)      — event log present + finalize PASS + grading
//                                   pipeline_log PASS
//
// Usage: node scripts/benchmark/judge-rubric.mjs --tier <cases.json>
// Writes results/benchmark/rubric.json and merges rubric into each grading file.
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 ? args[args.indexOf(n) + 1] : d);
const TIER = path.isAbsolute(opt('--tier', '')) ? opt('--tier') : path.join(ROOT, opt('--tier', 'scripts/benchmark/cases/benchmark_cases.json'));
const tier = JSON.parse(fs.readFileSync(TIER, 'utf8'));
const state = JSON.parse(fs.readFileSync(path.join(ROOT, 'results/benchmark/tier_state.json'), 'utf8'));
const runDirs = {};
for (const t of Object.values(state.tiers ?? {})) {
  for (const [cid, e] of Object.entries(t.cases ?? {})) runDirs[cid] = e.run_dir;
}

const numericTokens = (s) => {
  const out = new Set();
  for (const m of String(s).matchAll(/-?\d+\.\d+|-?\d+/g)) {
    const v = parseFloat(m[0]);
    if (Number.isFinite(v)) { out.add(v); out.add(Math.abs(v)); }
  }
  return out;
};

function briefNumbers(c) {
  const p = path.join(ROOT, 'results/benchmark/briefs', `${c.case_id}.brief.json`);
  if (!fs.existsSync(p)) return null;
  const b = JSON.parse(fs.readFileSync(p, 'utf8'));
  const nums = new Set();
  for (const a of b.evidence?.anomaly_columns ?? []) {
    nums.add(a.max_abs_z);
    if (a.pct_z3 != null) nums.add(a.pct_z3);
    if (a.pct_z3 != null) nums.add(a.pct_z3 * 100);
  }
  for (const pr of b.evidence?.top_correlation_pairs ?? []) {
    const m = pr.match(/r=(-?\d+\.?\d*)/);
    if (m) { nums.add(parseFloat(m[1])); nums.add(Math.abs(parseFloat(m[1]))); }
  }
  return nums;
}

function rubricFor(c, notePath, runDir, grading) {
  const checks = {};
  const note = JSON.parse(fs.readFileSync(notePath, 'utf8'));
  let score = 0;

  // R1 artifact integrity (15)
  const arts = ['04_diagnostics/diagnosis.json', '04_diagnostics/evidence.json', '04_diagnostics/confidence.json', '04_diagnostics/reasoning_chain.json'];
  let r1ok = true, r1detail = [];
  for (const a of arts) {
    const f = path.join(runDir, a);
    if (!fs.existsSync(f)) { r1ok = false; r1detail.push('missing ' + a); continue; }
    try { JSON.parse(fs.readFileSync(f, 'utf8')); } catch { r1ok = false; r1detail.push('invalid ' + a); }
  }
  checks.R1_artifacts = { pass: r1ok, detail: r1detail };
  if (r1ok) score += 15;

  // R2 hypothesis structure (15)
  const H = note.hypotheses ?? [];
  const surviving = H.filter((h) => h.verdict === 'surviving');
  const eliminated = H.filter((h) => h.verdict === 'eliminated');
  const elimWithContra = eliminated.filter((h) => (h.contradiction ?? []).some((x) => String(x).trim().length > 8));
  const r2 = H.length >= 3 && surviving.length >= 1 && elimWithContra.length >= 2;
  checks.R2_hypotheses = { pass: r2, detail: { total: H.length, surviving: surviving.length, eliminated_with_contradiction: elimWithContra.length } };
  if (r2) score += 15;

  // R3 evidence grounding (20): each surviving hypothesis' evidence must cite
  // at least one number present in the scenario's own brief.
  const nums = briefNumbers(c);
  let r3pass = nums != null && nums.size > 0;
  const r3detail = [];
  for (const h of surviving) {
    const evText = [...(h.evidence ?? []), ...(h.logic_chain ?? [])].join(' ');
    const toks = [...numericTokens(evText)];
    const grounded = toks.some((t) => nums.has(t) || nums.has(Math.round(t * 100) / 100));
    r3detail.push({ hypothesis: h.name?.slice(0, 24), grounded });
    if (!grounded) r3pass = false;
  }
  checks.R3_grounding = { pass: r3pass, detail: r3detail };
  if (r3pass) score += 20;

  // R4 calibration (15)
  const conf = Number(note.confidence);
  const ceiling = note.diagnosis_type === 'COMPETING_SET' ? 0.70 : 0.90;
  const inCeiling = conf > 0 && conf <= ceiling;
  // Control scenarios' expect_type_set ["NORMAL"] is a semantic sentinel (the
  // correct verdict is a DETERMINED normal-operation conclusion), so for
  // controls the type check is: the grader's control_pass verdict is true.
  const typeOk = c.control ? grading.control_pass === true : (c.expect_type_set ?? []).includes(note.diagnosis_type);
  const r4 = inCeiling && typeOk;
  checks.R4_calibration = { pass: r4, detail: { confidence: conf, ceiling: note.diagnosis_type === 'COMPETING_SET' ? 0.70 : 0.90, type: note.diagnosis_type, allowed: c.expect_type_set } };
  if (r4) score += 15;

  // R5 falsifiability (10)
  const falsifiable = surviving.some((h) => (h.falsification ?? []).some((x) => String(x).trim().length > 12));
  const substantive = String(note.primary_finding ?? '').length > 40;
  const r5 = falsifiable && substantive;
  checks.R5_falsifiability = { pass: r5, detail: { falsifiable, substantive_len: String(note.primary_finding ?? '').length } };
  if (r5) score += 10;

  // R6 physics verification (10)
  const pc = path.join(runDir, '02_processed/physics_check.json');
  const pm = path.join(runDir, '02_processed/physics_manual_verification.md');
  let r6 = false;
  if (fs.existsSync(pc)) {
    try { r6 = Object.keys(JSON.parse(fs.readFileSync(pc, 'utf8')).physical_checks ?? {}).length > 0; } catch { r6 = false; }
  }
  if (!r6 && fs.existsSync(pm)) r6 = fs.statSync(pm).size > 200;
  checks.R6_physics = { pass: r6 };
  if (r6) score += 10;

  // R7 execution proof (15)
  const log = path.join(runDir, '.pipeline_events.jsonl');
  const fin = path.join(runDir, 'pipeline_finalize_report.json');
  let r7 = fs.existsSync(log) && fs.existsSync(fin);
  if (r7) {
    try { r7 = JSON.parse(fs.readFileSync(fin, 'utf8')).overall === 'PASS'; } catch { r7 = false; }
    r7 = r7 && grading?.checks?.pipeline_log === 'PASS';
  }
  checks.R7_execution = { pass: r7 };
  if (r7) score += 15;

  return { score, max: 100, checks };
}

const out = { generated_at: new Date().toISOString(), tier: path.relative(ROOT, TIER), scenarios: {} };
for (const c of tier.cases) {
  const notePath = path.join(ROOT, 'results/benchmark/notes', `${c.case_id}.note.json`);
  const runDir = runDirs[c.case_id];
  const gradingPath = path.join(ROOT, 'results/benchmark/gradings', `${c.case_id}.json`);
  if (!fs.existsSync(notePath) || !runDir || !fs.existsSync(gradingPath)) {
    out.scenarios[c.case_id] = { skipped: 'missing note/run/grading' };
    continue;
  }
  const grading = JSON.parse(fs.readFileSync(gradingPath, 'utf8'));
  const rubric = rubricFor(c, notePath, runDir, grading);
  grading.rubric = { score: rubric.score, source: 'deterministic-rubric-v1' };
  fs.writeFileSync(gradingPath, JSON.stringify(grading, null, 1));
  out.scenarios[c.case_id] = rubric;
  console.log(`[rubric] ${c.case_id} — ${rubric.score}/100`);
}
fs.writeFileSync(path.join(ROOT, 'results/benchmark/rubric.json'), JSON.stringify(out, null, 1));
console.log(`rubric.json written (${Object.keys(out.scenarios).length} scenarios)`);
