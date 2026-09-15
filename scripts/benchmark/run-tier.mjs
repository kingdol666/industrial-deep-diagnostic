#!/usr/bin/env node
// run-tier.mjs — reproducible tier orchestration for the diagnosis benchmark.
//
// The benchmark's agent-in-the-loop step is a REAL industrial-analysis-auto
// pipeline execution per scenario (Steps 2-9, sub-agents per their skill
// protocols). This driver makes everything AROUND it reproducible:
//
//   prepare  → deterministic data ingestion into a run dir (setup/inspect/convert)
//   brief    → blind evidence pack per case (leakage-sentinel input, rubric R3 basis)
//   pipeline → per-case verification that the FULL pipeline artifact set exists
//   commit   → grade each completed run dir against truth (reads the artifacts
//              the sub-skill agents actually wrote), append to journal.jsonl
//   status   → per-case state table
//   stability → verdict-consistency study across INDEPENDENT pipeline executions:
//              scans every run dir of each case, extracts the agent-authored
//              verdicts (same extraction semantics as `commit`), and reports
//              whether diagnosis_type / top1-hit / calibration agree run-over-run
//   baselines → same-model baseline comparison arm: re-runs the deterministic
//              classical-PCA baseline, (re)generates bare-LLM prompts, re-scores
//              the archived same-GLM bare-call answers, and prints the IDD vs
//              bare-LLM vs FE-protocol vs PCA comparison table
//
// Usage:
//   node run-tier.mjs prepare  --tier scripts/benchmark/cases/benchmark_cases.json [--force]
//   node run-tier.mjs brief    --tier <file>
//   node run-tier.mjs pipeline --tier <file> [--only case_a,case_b]
//   node run-tier.mjs commit   --tier <file> [--only case_a,case_b]
//   node run-tier.mjs status   --tier <file>
//   node run-tier.mjs stability --tier <file>   [--min-runs 2]
//   node run-tier.mjs baselines --tier <file>
//
// The v1 note-based path (notes/archive/note expansion) was DELETED — it let a
// script fabricate pipeline artifacts and agent events. Protocol documentation
// lives in docs/benchmark/ (NOT in a skill by design).

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const DIRECT = path.join(ROOT, 'scripts', 'benchmark', 'zcode_direct_pipeline.mjs');
const RESULTS = path.join(ROOT, 'results', 'benchmark');
const STATE = path.join(RESULTS, 'tier_state.json');

const args = process.argv.slice(2);
const stage = args[0];
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const tierArg = opt('--tier', 'scripts/benchmark/cases/benchmark_cases.json');
const TIER = path.isAbsolute(tierArg) ? tierArg : path.join(ROOT, tierArg);
const only = opt('--only', '').split(',').map((s) => s.trim()).filter(Boolean);

if (!fs.existsSync(TIER)) {
  console.error(`tier file not found: ${TIER}`);
  process.exit(2);
}
const tier = JSON.parse(fs.readFileSync(TIER, 'utf8'));
const state = fs.existsSync(STATE) ? JSON.parse(fs.readFileSync(STATE, 'utf8')) : { tiers: {} };
const tierKey = path.relative(ROOT, TIER).replace(/\\/g, '/');
state.tiers[tierKey] = state.tiers[tierKey] || { cases: {} };
const tierState = state.tiers[tierKey];

function cases() {
  return tier.cases.filter((c) => !only.length || only.includes(c.case_id));
}

function runDirect(stageName, extraArgs) {
  return execFileSync(process.execPath, [DIRECT, stageName, '--case-file', TIER, ...extraArgs], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function cmdPrepare() {
  for (const c of cases()) {
    const entry = tierState.cases[c.case_id] || (tierState.cases[c.case_id] = {});
    if (entry.run_dir && fs.existsSync(entry.run_dir) && !args.includes('--force')) {
      console.log(`[prepare] ${c.case_id} — reuse ${path.relative(ROOT, entry.run_dir)}`);
      continue;
    }
    const out = runDirect('prepare', ['--case', c.case_id]);
    const json = JSON.parse(out.slice(out.indexOf('{')));
    entry.run_dir = json.run_dir || entry.run_dir;
    entry.prepared_at = new Date().toISOString();
    console.log(`[prepare] ${c.case_id} → ${path.relative(ROOT, entry.run_dir || '')}`);
  }
  save();
}

/**
 * BLIND-DIAGNOSIS support (真实性保障):
 *   brief — per case, write an evidence brief containing ONLY what a real
 *           diagnostician may see: prepare_digest statistics + process
 *           description + column names. NO truth, NO keywords, NO gradings.
 *           v2: the diagnosing agent executes the real pipeline in the run dir;
 *           the brief is the leakage-sentinel scan target and the rubric-R3
 *           "numbers visible to this scenario" baseline.
 */
const BRIEFS_DIR = path.join(RESULTS, 'briefs');

function cmdBrief() {
  fs.mkdirSync(BRIEFS_DIR, { recursive: true });
  for (const c of cases()) {
    const entry = tierState.cases[c.case_id] || {};
    if (!entry.run_dir || !fs.existsSync(entry.run_dir)) {
      console.log(`[brief] ${c.case_id} — no prepared run dir (run prepare first)`);
      continue;
    }
    const digest = JSON.parse(fs.readFileSync(path.join(entry.run_dir, 'prepare_digest.json'), 'utf8'));
    const brief = {
      case_id: c.case_id,
      dataset: c.dataset,
      role: c.control ? 'control (expected: normal operation unless data proves otherwise)' : 'fault investigation',
      process_description: c.process_description,
      columns: digest.cols,
      rows: digest.rows,
      stats_engine: digest.engine,
      evidence: {
        anomaly_columns: digest.anomaly_columns, // per-column max|z| + %beyond-3sigma
        top_correlation_pairs: digest.top_pairs, // strongest cross-domain pairs with |r|
      },
      _rules: [
        'Reason ONLY from evidence above plus domain knowledge of the process described.',
        'Do NOT read results/benchmark/gradings/* or scripts/benchmark/cases/* truth fields.',
        'Every evidence claim must cite a number present in this brief.',
      ],
    };
    const out = path.join(BRIEFS_DIR, `${c.case_id}.brief.json`);
    fs.writeFileSync(out, JSON.stringify(brief, null, 1) + '\n');
    console.log(`[brief] ${c.case_id} → ${path.relative(ROOT, out)}`);
  }
}

/**
 * REAL-PIPELINE execution support:
 *   pipeline — per case, verify the run dir contains the artifacts of the FULL
 *              industrial-analysis-auto pipeline (ontology / diagnosis set /
 *              judge / audit / report / html trio / finalize). Prints what is
 *              missing so the executing agent knows what to run.
 *   commit   — grade each completed run dir against truth (reads the artifacts
 *              the sub-skill agents actually wrote; no note, no expansion).
 */
function cmdPipeline() {
  let incomplete = 0;
  for (const c of cases()) {
    try {
      const out = runDirect('pipeline-check', ['--case', c.case_id]);
      console.log(out.trim());
      if (/NO RUN DIR|INCOMPLETE/.test(out)) incomplete += 1;
    } catch (e) {
      console.log(`[pipeline-check] ${c.case_id} — ERROR ${String(e.message).slice(0, 140)}`);
      incomplete += 1;
    }
  }
  console.log(`
[pipeline] Execution contract (skill://industrial-analysis-auto, Steps 2-9, per run dir):
  Step 2   context-builder  → industrial-ontology-builder skill → 01_ontology/ontology.json (+ CP-2/CP-3)
  Step 3   data-processor   → industrial-data-processor skill → 02_processed/data_analysis_conclusion.json (+ Phase 0-6, CP-4)
  Step 4   diagnostician    → industrial-diagnostician skill → 04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json (CP-5)
  Step 5a∥5b judge + pre-audit (parallel) → 05_review/judge_feedback.json + optimizer_preflight.md
  Step 6   reporter         → report.md + run_summary.json (CP-7)
  Step 7   final audit      → optimizer.md must contain ENDORSED (CP-8)
  Step 8   html-visualizer  → diagnostic-html-visualizer design system: render_manifest.json FIRST → diagnostic-report.html → html_selfcheck.json
  Step 8.5 html-reviewer    → 05_review/html_review.json verdict=pass (independent; never self-written)
  Step 9   finalize         → pipeline-finalize.mjs
Scripted note expansion is RETIRED (it fabricated artifacts and agent events).`);
  if (incomplete > 0) {
    console.error(`\n[pipeline] ${incomplete} scenario(s) incomplete`);
    process.exit(1);
  }
}

function cmdCommit() {
  let done = 0;
  let skipped = 0;
  for (const c of cases()) {
    const entry = tierState.cases[c.case_id] || {};
    if (!entry.run_dir || !fs.existsSync(entry.run_dir)) {
      console.log(`[commit] ${c.case_id} — no prepared run dir (run 'prepare' first)`);
      skipped += 1;
      continue;
    }
    let out;
    try {
      out = runDirect('grade', ['--case', c.case_id]);
    } catch (e) {
      console.log(`[commit] ${c.case_id} — ${String(e.message).split('\n')[0].slice(0, 200)}`);
      skipped += 1;
      continue;
    }
    const json = JSON.parse(out.slice(out.indexOf('{')));
    entry.graded_at = new Date().toISOString();
    entry.grading = json;
    const hit = json.control ? `control_pass=${json.control_pass}` : `top1=${json.top1} topk=${json.topk}`;
    console.log(`[commit] ${c.case_id} — ${hit} type=${json.diagnosis_type} judge=${json.judge_score} (${json.execution_mode})`);
    done += 1;
  }
  save();
  console.log(`\ncommitted ${done}, skipped ${skipped}`);
}

function cmdStatus() {
  const rows = tier.cases.map((c) => {
    const e = tierState.cases[c.case_id] || {};
    const graded = fs.existsSync(path.join(RESULTS, 'gradings', `${c.case_id}.json`));
    return `${c.case_id.padEnd(26)} prepared=${e.run_dir ? 'Y' : '-'}  graded=${graded ? 'Y' : '-'}${c.control ? '  (control)' : ''}`;
  });
  console.log(rows.join('\n'));
}

/** Seed tier_state.json from existing gradings — lets the reproducibility
 *  chain attach to results produced before this skill existed. */
function cmdImportState() {
  let imported = 0;
  for (const c of tier.cases) {
    const gp = path.join(RESULTS, 'gradings', `${c.case_id}.json`);
    if (!fs.existsSync(gp)) continue;
    const g = JSON.parse(fs.readFileSync(gp, 'utf8'));
    if (!g.run_dir) continue;
    tierState.cases[c.case_id] = {
      ...(tierState.cases[c.case_id] || {}),
      run_dir: g.run_dir,
      graded_at: tierState.cases[c.case_id]?.graded_at || new Date().toISOString(),
      imported_from: 'gradings',
    };
    imported += 1;
    console.log(`[import-state] ${c.case_id} → ${path.relative(ROOT, g.run_dir)}`);
  }
  save();
  console.log(`\nimported ${imported} case state(s) from gradings`);
}

function save() {
  fs.mkdirSync(RESULTS, { recursive: true });
  fs.writeFileSync(STATE, JSON.stringify(state, null, 1) + '\n');
}

/**
 * VERDICT-CONSISTENCY STUDY (multiple independent runs per scenario):
 *   For each case, scan workspace/diagnostic-runs/*_bench_<case_id> — every
 *   dir is one FULL pipeline execution. Extract the agent-authored verdict the
 *   same way `commit` does (deep-flat text → keyword hit; diagnosis_type;
 *   overall_confidence) and report agreement ACROSS RUNS OF THE SAME SYSTEM
 *   VERSION. Era boundary 2026-09-14: before it the pipeline lacked the
 *   anti-oscillation / confidence-cap / missing-discriminating-channel
 *   discipline (documented system revision), so cross-era verdict flips on the
 *   sensitive scenarios are version evolution, NOT run-to-run instability.
 *   The headline metric is WITHIN-ERA agreement. Runs without a finalize PASS
 *   are listed but unproven (never counted). Cases with < min-runs proven runs
 *   in an era get the repeat contract: re-run the FULL pipeline in a FRESH
 *   session — never copy artifacts between run dirs, never --force-prepare.
 */
function cmdStability() {
  const RUNS = path.join(ROOT, 'workspace', 'diagnostic-runs');
  const minRuns = Number(opt('--min-runs', '2'));
  const ERA_BOUNDARY = '20260914'; // run-dir timestamp prefix; see doc above
  const eraOf = (dirName) => (dirName.slice(0, 8) >= ERA_BOUNDARY ? 'v2' : 'v1');
  const report = {
    generated_at: new Date().toISOString(),
    era_boundary: ERA_BOUNDARY,
    era_semantics: 'v1 = pre anti-oscillation/cap discipline (system revision), v2 = current benchmark system; headline metric is within-era agreement',
    extraction: 'same semantics as commit: diagnosis.json primary_finding + surviving hypotheses, truth keywords from the case file',
    cases: {},
  };
  let eraPairs = 0, eraPairsConsistent = 0;

  for (const c of cases()) {
    const dirs = fs.existsSync(RUNS)
      ? fs.readdirSync(RUNS).filter((d) => d.endsWith(`_bench_${c.case_id}`)).sort()
      : [];
    const runs = dirs.map((d) => {
      const runDir = path.join(RUNS, d);
      const finPath = path.join(runDir, 'pipeline_finalize_report.json');
      let finalized = false;
      try {
        finalized = JSON.parse(fs.readFileSync(finPath, 'utf8')).overall === 'PASS'
          && fs.existsSync(path.join(runDir, '.pipeline_events.jsonl'));
      } catch { finalized = false; }
      let diagnosisType = null, top1Hit = null, confidence = null, primary = '';
      try {
        const D = JSON.parse(fs.readFileSync(path.join(runDir, '04_diagnostics/diagnosis.json'), 'utf8'));
        diagnosisType = D.diagnosis_type ?? null;
        const flat = (v) => Array.isArray(v) ? v.map(flat).join(' ')
          : (v && typeof v === 'object') ? Object.values(v).map(flat).join(' ') : String(v ?? '');
        const surviving = D.hypotheses?.surviving ?? [];
        primary = String(D.primary_finding ?? '');
        const text = [primary,
          ...surviving.flatMap((h) => [h?.name, flat(h?.physical_logic_chain), flat(h?.supporting_evidence), flat(h?.ontology_data_physics_proof)]),
        ].filter(Boolean).join(' ').toLowerCase();
        if (!c.control) {
          top1Hit = diagnosisType === 'DETERMINED' && (c.keywords || []).some((k) => text.includes(k.toLowerCase()));
        } else {
          top1Hit = !/正常|normal|无异常|无故障|稳态|baseline|稳定/i.test(primary + ' ' + surviving.map((h) => h?.name ?? '').join(' ')); // true = false alarm
        }
        const CF = JSON.parse(fs.readFileSync(path.join(runDir, '04_diagnostics/confidence.json'), 'utf8'));
        const s = CF?.overall_confidence?.score;
        if (typeof s === 'number') confidence = +(s <= 1 ? s * 100 : s).toFixed(1);
      } catch { /* artifact missing — run listed as unproven */ }
      return { run_dir: path.relative(ROOT, runDir), era: eraOf(d), finalized, diagnosis_type: diagnosisType, top1_hit: top1Hit, confidence };
    });

    const byEra = {};
    for (const era of ['v1', 'v2']) {
      const proven = runs.filter((r) => r.era === era && r.finalized && r.diagnosis_type);
      const types = [...new Set(proven.map((r) => r.diagnosis_type))];
      const hits = [...new Set(proven.map((r) => r.top1_hit))];
      const typeConsistent = proven.length >= minRuns && types.length === 1;
      const hitConsistent = proven.length >= minRuns && hits.length === 1;
      const consistent = typeConsistent && hitConsistent;
      if (proven.length >= minRuns) { eraPairs++; if (consistent) eraPairsConsistent++; }
      byEra[era] = {
        n_runs_proven: proven.length,
        verdict_types: types,
        top1_hits: hits,
        confidence_range: proven.length ? [Math.min(...proven.map((r) => r.confidence)), Math.max(...proven.map((r) => r.confidence))] : null,
        verdict_type_consistent: typeConsistent,
        top1_consistent: hitConsistent,
        consistent,
      };
    }
    report.cases[c.case_id] = { n_runs_found: runs.length, eras: byEra, runs };
    for (const era of ['v1', 'v2']) {
      const e = byEra[era];
      if (!e.n_runs_proven) continue;
      const flag = e.n_runs_proven >= minRuns ? (e.consistent ? 'CONSISTENT' : 'DIVERGENT') : 'INSUFFICIENT-RUNS';
      console.log(`[stability] ${c.case_id.padEnd(28)} ${era} proven=${e.n_runs_proven} types=[${e.verdict_types.join(',')}] hits=[${e.top1_hits}] → ${flag}`);
      if (e.n_runs_proven < minRuns) {
        console.log(`[stability]   ↳ contract: re-run the FULL industrial-analysis-auto pipeline for this case in a FRESH session (reproduction guide §4); never copy artifacts between run dirs, never --force-prepare`);
      }
    }
  }
  report.summary = {
    min_runs_required: minRuns,
    era_case_pairs: eraPairs,
    era_case_pairs_consistent: eraPairsConsistent,
    within_era_agreement: eraPairs ? `${eraPairsConsistent}/${eraPairs}` : 'n/a',
  };
  fs.writeFileSync(path.join(RESULTS, 'stability_report.json'), JSON.stringify(report, null, 1) + '\n');
  console.log(`\n[stability] within-era verdict+top1 agreement: ${report.summary.within_era_agreement} case-era pair(s) with ≥${minRuns} proven independent runs → ${path.relative(ROOT, path.join(RESULTS, 'stability_report.json'))}`);
}

/**
 * SAME-MODEL BASELINE COMPARISON ARM:
 *   1. classical PCA baseline (deterministic, published protocol) — re-run
 *   2. bare-LLM prompts (never overwrites recorded inputs) + re-score of the
 *      archived same-GLM single-call answers + coverage check
 *   3. comparison table: IDD (committed gradings) vs bare-LLM vs FE-protocol vs PCA
 */
function cmdBaselines() {
  const run = (script, args2) => {
    console.log(`\n----- node ${path.relative(ROOT, script)} ${args2.join(' ')}`);
    execFileSync(process.execPath, [script, ...args2], { cwd: ROOT, stdio: 'inherit' });
  };
  const BM = path.join(ROOT, 'scripts', 'benchmark');
  run(path.join(BM, 'baseline_pca.mjs'), ['--tier', path.relative(ROOT, TIER)]);
  run(path.join(BM, 'baseline_llm.mjs'), ['prompts']);
  run(path.join(BM, 'baseline_llm.mjs'), ['score']);
  run(path.join(BM, 'baseline_llm.mjs'), ['check']);

  // comparison table — reads the committed gradings + freshly scored baselines
  const BL = JSON.parse(fs.readFileSync(path.join(RESULTS, 'baselines.json'), 'utf8'));
  console.log('\n[baselines] comparison — same harness, same GLM deployment, same scenarios');
  console.log('case                        | IDD top1/type          | bare-LLM strict | FE-style | PCA T2/SPE');
  for (const c of cases()) {
    const g = tierState.cases[c.case_id]?.grading;
    const l = BL.llm[c.case_id]?.no_candidates;
    const p = BL.pca[c.case_id];
    const idd = c.control
      ? `ctrl pass=${g?.control_pass ?? '-'}`
      : `${g?.top1 ? 'HIT ' : g ? 'miss' : '-   '} ${g?.diagnosis_type ?? '-'}`;
    const bare = c.control ? `normal=${l?.normal_verdict ?? '-'}` : `strict=${l ? (l.strict_top1_hit ? 'HIT' : 'miss') : 'n/a'}`;
    const fe = BL.llm[c.case_id]?.with_candidates?.fe_style_top3_hit;
    const pca = p ? `${(p.detection_rate_T2 * 100).toFixed(1)}%/${(p.detection_rate_SPE * 100).toFixed(1)}%` : '-';
    console.log(`${c.case_id.padEnd(28)}| ${idd.padEnd(23)}| ${bare.padEnd(16)}| ${(fe === undefined ? 'n/a' : fe ? 'HIT' : 'miss').padEnd(9)}| ${pca}`);
  }
  console.log(`
[baselines] provenance:
  PCA  : scripts/benchmark/baseline_pca.mjs (deterministic; Chiang 2001 / Qin 2012 protocol)
  LLM  : results/benchmark/baseline_fe_answers/ — archived raw replies of ${BL.model}
  IDD  : results/benchmark/tier_state.json gradings — committed pipeline-run verdicts
  FE official-code arm: ${BL.fe_official_code?.source ?? 'n/a'}`);
}

const stages = {
  prepare: cmdPrepare,
  pipeline: cmdPipeline,
  commit: cmdCommit,
  status: cmdStatus,
  'import-state': cmdImportState,
  brief: cmdBrief,
  stability: cmdStability,
  baselines: cmdBaselines,
};
if (!stages[stage]) {
  console.error('stage must be prepare|pipeline|commit|status|import-state|brief|stability|baselines (notes/archive retired — the note-expansion path was deleted)');
  process.exit(2);
}
stages[stage]();
