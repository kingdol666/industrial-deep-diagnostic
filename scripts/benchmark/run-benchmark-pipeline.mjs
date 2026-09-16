#!/usr/bin/env node
// run-benchmark-pipeline.mjs — the single agent-executable entry point for the
// four-step IDD benchmark test pipeline:
//
//   STEP 1  Run the current IDD diagnosis pipeline on the scenario data
//           (prepare -> blind brief -> REAL industrial-analysis-auto S2-9 ->
//            grade -> aggregate -> reproducibility gate)
//   STEP 2  Run the LLM-replication baseline suite on the same scenario data
//           (Nuxt suite: classic PCA / FE protocol / same-model bare LLM),
//           then verify suite determinism by diffing against the prior run
//   STEP 3  Draw ONE scenario AT RANDOM and audit diagnosis consistency across
//           independent executions (structured mechanism signature, era-aware)
//   STEP 4  Generate the English benchmark-standard report (Markdown + HTML)
//
// Every stage fails loudly instead of fabricating. Where a stage needs an agent
// to execute the real pipeline (Step 1 gaps, Step 3 re-run), the script prints an
// explicit EXECUTION CONTRACT and exits non-zero — it never writes the artifacts
// itself. This is the v2 anti-fabrication rule: scripts may verify and score,
// never author.
//
// Usage:
//   node scripts/benchmark/run-benchmark-pipeline.mjs                 # all four steps
//   node scripts/benchmark/run-benchmark-pipeline.mjs --step 3        # one step
//   node scripts/benchmark/run-benchmark-pipeline.mjs --steps 2,4
//   node scripts/benchmark/run-benchmark-pipeline.mjs --seed 20260916 # reproducible draw
//   node scripts/benchmark/run-benchmark-pipeline.mjs --allow-gaps    # report gaps, do not fail
//   node scripts/benchmark/run-benchmark-pipeline.mjs --skip-suite-server  # assume suite already up

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawn } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const BM = path.join(ROOT, 'scripts', 'benchmark');
const RES = path.join(ROOT, 'results', 'benchmark');
const SUITE = path.join(ROOT, 'baselines', 'baseline-suite');
const SUITE_RUNS = path.join(SUITE, 'runs');
const CASES = 'scripts/benchmark/cases/benchmark_cases.json';
const SUITE_PORT = Number(process.env.SUITE_PORT || 5181);

const args = process.argv.slice(2);
const has = (n) => args.includes(n);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);

const stepArg = opt('--step', '');
const stepsArg = opt('--steps', '');
const wanted = new Set(
  stepArg ? [Number(stepArg)]
    : stepsArg ? stepsArg.split(',').map((s) => Number(s.trim()))
      : [1, 2, 3, 4],
);
const seed = opt('--seed', '');
const allowGaps = has('--allow-gaps');

/** Outstanding gaps per step — reported distinctly from hard failures. */
const gapNotes = {};

const banner = (t) => {
  console.log('');
  console.log('═'.repeat(74));
  console.log(`  ${t}`);
  console.log('═'.repeat(74));
};

/** Run a node script, streaming output. Returns {ok, out}. */
function node(script, scriptArgs = [], { ok404 = false } = {}) {
  const abs = path.isAbsolute(script) ? script : path.join(ROOT, script);
  try {
    const out = execFileSync(process.execPath, [abs, ...scriptArgs], {
      cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 3600000,
    });
    process.stdout.write(out);
    return { ok: true, out, code: 0 };
  } catch (e) {
    const out = (e.stdout || '') + (e.stderr || '');
    process.stdout.write(out);
    return { ok: false, out, code: e.status ?? 1 };
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Probe a host for the baseline suite's truth-free scenario endpoint. */
async function probeSuite(base) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(`${base}/api/scenarios`, { signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) return null;
    const j = await res.json();
    if (!Array.isArray(j) || !j.length || !j[0].case_id) return null;
    return { base, scenarios: j };
  } catch { return null; }
}

/** Start the Nuxt suite dev server and wait until its API answers. */
async function ensureSuite() {
  for (const port of [SUITE_PORT]) {
    const found = await probeSuite(`http://localhost:${port}`);
    if (found) {
      console.log(`[step2] baseline suite already serving on ${found.base} (${found.scenarios.length} scenarios)`);
      return found.base;
    }
  }
  if (has('--skip-suite-server')) {
    throw new Error(`no baseline suite reachable on localhost:${SUITE_PORT} and --skip-suite-server was set`);
  }
  const entry = path.join(SUITE, 'node_modules', 'nuxt', 'bin', 'nuxt.mjs');
  if (!fs.existsSync(entry)) {
    throw new Error(`baseline suite deps missing — run: cd baselines/baseline-suite && npm install`);
  }
  console.log(`[step2] starting baseline suite (nuxt dev, preferred port ${SUITE_PORT})…`);
  const logPath = path.join(RES, '.suite-dev.log');
  fs.mkdirSync(RES, { recursive: true });
  const logFd = fs.openSync(logPath, 'w');
  const child = spawn(process.execPath, [entry, 'dev', '--port', String(SUITE_PORT)], {
    cwd: SUITE, stdio: ['ignore', logFd, logFd], detached: false,
  });
  // nuxt falls back to another port when the preferred one is busy — read the log.
  let port = SUITE_PORT;
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    await sleep(1500);
    let log = '';
    try { log = fs.readFileSync(logPath, 'utf8'); } catch { /* not yet */ }
    const m = log.match(/Local:\s+http:\/\/localhost:(\d+)/);
    if (m) port = Number(m[1]);
    const found = await probeSuite(`http://localhost:${port}`);
    if (found) {
      console.log(`[step2] baseline suite ready on ${found.base} (requested ${SUITE_PORT}, actual ${port}) — log: ${path.relative(ROOT, logPath)}`);
      return found.base;
    }
    if (/ERROR|Error:/.test(log) && /cannot find|failed to|EADDR/.test(log)) {
      throw new Error(`baseline suite failed to start — see ${path.relative(ROOT, logPath)}`);
    }
  }
  try { child.kill(); } catch { /* ignore */ }
  throw new Error(`baseline suite did not become ready within 120s — see ${path.relative(ROOT, logPath)}`);
}

/** Snapshot suite run files, then diff after a re-run (timestamps excluded). */
function diffSuiteRuns(snapshotDir) {
  const files = fs.readdirSync(SUITE_RUNS).filter((f) => f.endsWith('.json'));
  const strip = (o) => { const c = { ...o }; delete c.executed_at; return JSON.stringify(c); };
  let compared = 0, identical = 0;
  const differing = [];
  for (const f of files) {
    const prior = path.join(snapshotDir, f);
    if (!fs.existsSync(prior)) continue;
    compared += 1;
    const a = strip(JSON.parse(fs.readFileSync(prior, 'utf8')));
    const b = strip(JSON.parse(fs.readFileSync(path.join(SUITE_RUNS, f), 'utf8')));
    if (a === b) identical += 1; else differing.push(f);
  }
  return { compared, identical, differing: differing.length, differing_files: differing.slice(0, 20) };
}

// ─────────────────────────── STEP 1 ───────────────────────────
function step1() {
  banner('STEP 1 — Run the IDD diagnosis pipeline on the scenario data');
  let failed = false;

  console.log('\n[1.0] contract checks + truth-leakage sentinel');
  const leak = node(path.join(BM, 'check-leakage.mjs'), ['--tier', CASES]);
  if (!leak.ok) { failed = true; console.log('[1.0] FAIL — leakage sentinel did not pass'); }

  console.log('\n[1.1] prepare (deterministic statistics per scenario)');
  if (!node(path.join(BM, 'run-tier.mjs'), ['prepare', '--tier', CASES]).ok) failed = true;

  console.log('\n[1.2] blind briefs (leakage-sentinel input + rubric R3 basis)');
  if (!node(path.join(BM, 'run-tier.mjs'), ['brief', '--tier', CASES]).ok) failed = true;

  console.log('\n[1.3] verify the full pipeline artifact set per scenario');
  const pipe = node(path.join(BM, 'run-tier.mjs'), ['pipeline', '--tier', CASES]);
  if (!pipe.ok) {
    failed = true;
    gapNotes[1] = 'scenario run dir(s) lack the full Step 2-9 artifact set — execute the contract below';
    console.log(`
┌──────────────────────────────────────────────────────────────────────────┐
│ EXECUTION CONTRACT — the real pipeline must be run by an agent           │
└──────────────────────────────────────────────────────────────────────────┘
  The run directories above do not carry the complete Step 2-9 artifact set.
  For EACH incomplete scenario, in its prepared run dir
  (workspace/diagnostic-runs/<ts>_bench_<case_id>/) execute
  skill://industrial-analysis-auto Steps 2-9 and dispatch the sub-agents per
  their own skill protocols:
    Step 2    context-builder  -> 01_ontology/ontology.json          (CP-2/CP-3)
    Step 3    data-processor   -> 02_processed/data_analysis_conclusion.json (CP-4)
    Step 4    diagnostician    -> 04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json (CP-5)
    Step 5a||5b judge + pre-audit (parallel) -> 05_review/judge_feedback.json + optimizer_preflight.md
    Step 6    reporter         -> report.md + run_summary.json       (CP-7)
    Step 7    final audit      -> optimizer.md must contain ENDORSED (CP-8)
    Step 8    html-visualizer  -> render_manifest.json FIRST -> diagnostic-report.html -> html_selfcheck.json
    Step 8.5  html-reviewer    -> 05_review/html_review.json verdict=pass (independent)
    Step 9    finalize         -> pipeline-finalize.mjs
  Never let a script write these artifacts — scripted expansion is RETIRED.
  Per-case gap list: node scripts/benchmark/run-tier.mjs pipeline
`);
  }

  console.log('\n[1.4] grade from real artifacts + deterministic rubric');
  if (!node(path.join(BM, 'run-tier.mjs'), ['commit', '--tier', CASES]).ok) failed = true;
  if (!node(path.join(BM, 'judge-rubric.mjs'), ['--tier', CASES]).ok) failed = true;

  console.log('\n[1.5] aggregate + reproducibility gate');
  if (!node(path.join(BM, 'aggregate.mjs'), ['--tier-file', CASES]).ok) failed = true;
  const repro = node(path.join(BM, 'verify-repro.mjs'), ['--tier', CASES]);
  if (!/REPRODUCIBLE/.test(repro.out)) { failed = true; console.log('[1.5] FAIL — reproducibility gate not REPRODUCIBLE'); }

  const m = fs.existsSync(path.join(RES, 'metrics.json')) ? JSON.parse(fs.readFileSync(path.join(RES, 'metrics.json'), 'utf8')) : null;
  if (m) console.log(`\n[1.6] result — executed ${m.executed}/${m.total_cases} · Top-1 ${m.top1}/${m.fault_cases} · CDR ${m.cdr} · controls ${m.control_pass}/${m.control_cases} · false alarms ${m.false_alarms} · overconfident ${m.overconfident} · mean rubric ${m.mean_rubric}`);

  return failed;
}

// ─────────────────────────── STEP 2 ───────────────────────────
async function step2() {
  banner('STEP 2 — Run the LLM-replication baseline suite on the same scenario data');
  let failed = false;

  console.log('\n[2.0] resolve / start the baseline suite');
  let base;
  try {
    base = await ensureSuite();
  } catch (e) {
    console.log(`[2.0] FAIL — ${e.message}`);
    return true;
  }

  console.log('\n[2.1] snapshot prior suite outputs (determinism evidence)');
  const snap = path.join(RES, '.suite-prior');
  fs.rmSync(snap, { recursive: true, force: true });
  fs.mkdirSync(snap, { recursive: true });
  const priorFiles = fs.readdirSync(SUITE_RUNS).filter((f) => f.endsWith('.json'));
  for (const f of priorFiles) fs.copyFileSync(path.join(SUITE_RUNS, f), path.join(snap, f));
  console.log(`[2.1] snapshotted ${priorFiles.length} prior run file(s) -> ${path.relative(ROOT, snap)}`);

  console.log('\n[2.2] execute every scenario x every arm (PCA / FE / bare-LLM regimes)');
  const runAll = node(path.join(SUITE, 'scripts', 'run-all.mjs'), ['--base', base]);
  if (!runAll.ok) failed = true;
  const m = runAll.out.match(/done: (\d+) run\(s\) saved to runs\/, (\d+) failure/);
  if (m) console.log(`[2.2] suite reported ${m[1]} run(s), ${m[2]} failure(s)`);
  if (m && Number(m[2]) > 0) failed = true;

  console.log('\n[2.3] determinism — diff fresh outputs against the snapshot (timestamps excluded)');
  const det = diffSuiteRuns(snap);
  const verdict = det.differing === 0 ? 'DETERMINISTIC' : 'NON-DETERMINISTIC';
  const record = {
    generated_at: new Date().toISOString(),
    suite_base: base,
    compared: det.compared,
    identical: det.identical,
    differing: det.differing,
    differing_files: det.differing_files,
    verdict,
    method: 'consecutive executions of the same suite; only executed_at is excluded from the comparison',
  };
  fs.mkdirSync(RES, { recursive: true });
  fs.writeFileSync(path.join(RES, 'suite_determinism.json'), JSON.stringify(record, null, 1) + '\n');
  console.log(`[2.3] ${det.identical}/${det.compared} byte-identical -> ${verdict} (results/benchmark/suite_determinism.json)`);
  if (det.differing > 0) {
    console.log(`[2.3] differing files: ${det.differing_files.join(', ')}`);
    console.log('[2.3] NOTE — deterministic arms (PCA/FE) must not drift; a recorded-replay arm differing means the archived answers were edited. Investigate before reporting.');
    failed = true;
  }
  return failed;
}

// ─────────────────────────── STEP 3 ───────────────────────────
function step3() {
  banner('STEP 3 — Draw a scenario AT RANDOM and audit diagnosis consistency');
  let failed = false;

  console.log('\n[3.1] uniform random draw over the scenario pool (recorded seed)');
  const drawArgs = ['--faults-only'];
  if (seed !== '') drawArgs.push('--seed', seed);
  const draw = node(path.join(BM, 'select-retest-case.mjs'), drawArgs);
  if (!draw.ok) return true;
  const caseId = draw.out.trim().split('\n').pop().trim();
  const rec = JSON.parse(fs.readFileSync(path.join(RES, 'retest_selection.json'), 'utf8'));
  const round = rec.rounds.at(-1);
  console.log(`[3.1] draw replayable with: --seed ${round.seed}`);

  console.log('\n[3.2] consistency audit across all scenarios (structured mechanism signature)');
  const audit = node(path.join(BM, 'consistency-audit.mjs'), []);
  if (!audit.ok) {
    failed = true;
    console.log('[3.2] DIVERGENT within-era pair(s) detected — inspect results/benchmark/consistency_audit.json before reporting.');
  }

  console.log('\n[3.3] audit the drawn scenario specifically');
  const one = node(path.join(BM, 'consistency-audit.mjs'), ['--case', caseId]);
  // re-running on a single case rewrites the audit file — regenerate the full audit after
  node(path.join(BM, 'consistency-audit.mjs'), []);
  const auditAll = JSON.parse(fs.readFileSync(path.join(RES, 'consistency_audit.json'), 'utf8'));
  const st = auditAll.cases[caseId];

  if (!st || st.status === 'INSUFFICIENT-RUNS') {
    const canonEraCount = st?.eras?.[st.canonical_era]?.n_runs_proven ?? 0;
    failed = true;
    gapNotes[3] = `${caseId} needs a 2nd in-era execution (has ${canonEraCount}) — execute the contract below`;
    console.log(`
┌──────────────────────────────────────────────────────────────────────────┐
│ EXECUTION CONTRACT — this scenario needs an independent re-run           │
└──────────────────────────────────────────────────────────────────────────┘
  Drawn scenario : ${caseId}
  Proven executions in the current era (${st?.canonical_era ?? 'v2'}) : ${canonEraCount}
  (proven executions on disk across all eras: ${st?.n_runs_proven ?? 0} — cross-era runs are a
   documented system revision and are not counted toward consistency.)
  The consistency claim needs >= 2 in-era executions. Execute the FULL pipeline
  (Steps 2-9) for this scenario in a FRESH run directory:

    1) node scripts/benchmark/run-tier.mjs prepare --tier ${CASES}   # reuse: run dir already prepared
    2) In workspace/diagnostic-runs/<new_ts>_bench_${caseId}/ run
       skill://industrial-analysis-auto Steps 2-9 (sub-agents per their skill
       protocols; same contract as Step 1 above).
    3) node scripts/benchmark/run-tier.mjs commit --tier ${CASES} --only ${caseId}
    4) node scripts/benchmark/consistency-audit.mjs --case ${caseId}
    5) node scripts/benchmark/run-benchmark-pipeline.mjs --step 4

  Rules: never copy artifacts between run dirs; never re-use the canonical run
  dir as a source; never edit a result json by hand. The run is only counted if
  pipeline_finalize_report.json has overall = PASS and .pipeline_events.jsonl exists.
`);
  } else {
    console.log(`[3.3] ${caseId} -> ${st.status} (in-era proven runs: ${st.n_runs_proven}, era ${st.canonical_era})`);
  }
  return failed;
}

// ─────────────────────────── STEP 4 ───────────────────────────
function step4() {
  banner('STEP 4 — Generate the English benchmark-standard report (MD + HTML)');
  const ok = node(path.join(BM, 'build-english-benchmark-report.mjs'), []).ok;
  const mdP = path.join(RES, 'benchmark_report_en.md');
  const htmlP = path.join(RES, 'benchmark_report_en.html');
  for (const p of [mdP, htmlP]) {
    if (!fs.existsSync(p)) { console.log(`[4.0] FAIL — missing ${path.relative(ROOT, p)}`); return true; }
  }
  const kb = (fs.statSync(mdP).size / 1024).toFixed(1);
  const hb = (fs.statSync(htmlP).size / 1024).toFixed(1);
  console.log(`[4.0] ${path.relative(ROOT, mdP)} (${kb} KB) + ${path.relative(ROOT, htmlP)} (${hb} KB)`);
  return !ok;
}

// ─────────────────────────── driver ───────────────────────────
const results = {};
if (wanted.has(1)) results[1] = step1();
if (wanted.has(2)) results[2] = await step2();
if (wanted.has(3)) results[3] = step3();
if (wanted.has(4)) results[4] = step4();

banner('SUMMARY');
for (const n of [1, 2, 3, 4]) {
  if (!(n in results)) continue;
  const label = {
    1: 'pipeline diagnosis (IDD)',
    2: 'LLM-replication baseline suite',
    3: 'random re-test + consistency audit',
    4: 'English benchmark report (MD + HTML)',
  }[n];
  const state = !results[n] ? 'OK' : (allowGaps && gapNotes[n] ? 'OK-WITH-GAPS' : 'INCOMPLETE');
  console.log(`  STEP ${n}  ${String(label).padEnd(40)} ${state}`);
  if (gapNotes[n]) console.log(`          └─ ${gapNotes[n]}`);
}
console.log('');
const strictFail = Object.values(results).some(Boolean);
if (strictFail && !allowGaps) {
  console.log('  Overall: INCOMPLETE — outstanding execution contracts are printed above and are not optional.');
  process.exit(1);
}
if (strictFail) {
  console.log('  Overall: OK-WITH-GAPS (--allow-gaps) — outstanding execution contracts are listed above.');
  console.log('  Hand those contracts to an executing agent, then re-run the affected step.');
  process.exit(0);
}
console.log('  Overall: OK — artifacts under results/benchmark/ and baselines/baseline-suite/runs/');
console.log('');
