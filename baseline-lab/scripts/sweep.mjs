#!/usr/bin/env node
// sweep.mjs — run a baseline sweep from the command line.
//
//   node scripts/sweep.mjs --help
//   node scripts/sweep.mjs --classical                       # all deterministic baselines, 12 cases
//   node scripts/sweep.mjs --algorithms pca-t2-spe,knn-fdd   # explicit
//   node scripts/sweep.mjs --llm --cases tep_d01_ac_feed_ratio --algorithms llm-direct
//   node scripts/sweep.mjs --list
//
// The sweep writes results/runs/<runId>/{sweep,results,summary}.json and prints
// a comparison table.

import { listAlgorithms } from '../server/utils/registry.mjs';
import { listCaseIds, loadCasesRaw } from '../server/utils/paths.mjs';
import { runSweep, listSweeps } from '../server/utils/runner.mjs';
import { wilson } from '../server/utils/scoring.mjs';
import { detectProviders, resolveProvider } from '../server/utils/llm/provider.mjs';

const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const val = (f, d = null) => {
  const i = argv.indexOf(f);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : d;
};

if (has('--help') || has('-h')) {
  console.log(`IDD Baseline Lab — sweep driver

Usage:
  node scripts/sweep.mjs [options]

Selection:
  --algorithms a,b,c     comma-separated algorithm ids (default: all)
  --cases x,y            comma-separated case ids (default: all 12)
  --family <f>           classical | supervised | llm | official
  --classical            shorthand for --family classical
  --supervised           shorthand for --family supervised
  --llm                  shorthand for --family llm + official
  --list                 list algorithms / cases / available sweeps, then exit

Provider (LLM algorithms only):
  --provider <id>        e.g. cli:claude, cli:dsh, openai-compatible
  --model <name>

Other:
  --label <name>         label embedded in the run id
  --json                 print the raw summary JSON instead of a table
  -h, --help             this text
`);
  process.exit(0);
}

const all = listAlgorithms();

if (has('--list')) {
  console.log('=== algorithms ===');
  for (const a of all) {
    console.log(
      `${a.id.padEnd(18)} ${String(a.family).padEnd(11)} ${a.deterministic ? 'deterministic' : 'stochastic '} ${a.requiresProvider ? 'needs-LLM' : 'offline    '}  ${a.label}`,
    );
  }
  console.log('\n=== cases ===');
  for (const c of loadCasesRaw()) {
    console.log(`${c.case_id.padEnd(32)} ${String(c.dataset).padEnd(11)} ${c.control ? 'CONTROL' : 'fault  '}`);
  }
  console.log('\n=== LLM providers ===');
  for (const p of detectProviders({})) {
    console.log(`${p.available ? '[x]' : '[ ]'} ${p.id.padEnd(22)} ${p.detail.slice(0, 70)}`);
  }
  const sweeps = listSweeps();
  console.log(`\n=== past sweeps (${sweeps.length}) ===`);
  for (const s of sweeps.slice(0, 10)) {
    console.log(`${s.run_id.padEnd(34)} ${s.complete ? 'complete' : 'partial '} rows=${String(s.result_count).padEnd(5)} ${s.algorithms.length} algos x ${s.cases.length} cases`);
  }
  process.exit(0);
}

// ---- resolve selection
let algorithms = val('--algorithms') ? val('--algorithms').split(',').map((s) => s.trim()).filter(Boolean) : null;
const family =
  val('--family') ||
  (has('--classical') ? 'classical' : null) ||
  (has('--supervised') ? 'supervised' : null) ||
  (has('--llm') ? 'llm' : null);
if (!algorithms && family) {
  algorithms = all.filter((a) => a.family === family || (family === 'llm' && a.family === 'official')).map((a) => a.id);
}
const cases = val('--cases') ? val('--cases').split(',').map((s) => s.trim()).filter(Boolean) : null;

const config = {};
if (val('--provider')) config.llmProvider = val('--provider');
if (val('--model')) config.llmModel = val('--model');
config.llmTimeoutMs = Number(process.env.BASELINE_LLM_TIMEOUT_MS || 300000);

const needsProvider = (algorithms || all.map((a) => a.id))
  .map((id) => all.find((a) => a.id === id))
  .some((a) => a?.requiresProvider);

console.log('=== IDD Baseline Lab — sweep ===');
console.log(`algorithms : ${(algorithms || ['<all>']).join(', ')}`);
console.log(`cases      : ${(cases || listCaseIds()).length}`);
if (needsProvider) {
  let p = null;
  try { p = resolveProvider(config); } catch (e) { console.log(`provider   : ERROR ${e.message}`); }
  console.log(`provider   : ${p ? `${p.id} (${p.detail})` : 'NONE — LLM algorithms will report skipped_no_provider'}`);
}
console.log('');

const t0 = Date.now();
const { run_id, results, summary } = await runSweep({
  algorithms,
  cases,
  config,
  label: val('--label', 'sweep'),
  onProgress: (p) => {
    if (p.phase === 'start') {
      process.stdout.write(`[${String(p.done + 1).padStart(3)}/${p.total}] ${p.algorithmId} x ${p.caseId} ... `);
    } else {
      const s = p.result.scored;
      const status = p.result.status;
      let verdict;
      if (status === 'executed') {
        verdict = s.control
          ? (s.control_pass ? 'control-pass' : 'FALSE-ALARM')
          : (s.strict_top1_hit ? 'HIT' : (s.top3.length ? 'miss' : 'abstain'));
      } else verdict = status;
      console.log(verdict);
    }
  },
});

const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

if (has('--json')) {
  console.log(JSON.stringify(summary, null, 2));
} else {
  console.log(`\n=== summary (run ${run_id}, ${elapsed}s) ===`);
  console.log('top1%   = IDD rubric keyword/IDV hit on rank-1 (family-level for shared-keyword fault families)');
  console.log('exact%  = rank-1 names the TRUE IDV number (stricter; TEP faults only)\n');
  const head = ['algorithm', 'status', 'top1', 'top1%', 'Wilson95', 'exact', 'exact%', 'FE@3', 'ctrl', 'FA', 'abst', 'err', 'N/A'];
  const w = [18, 17, 7, 7, 14, 7, 7, 6, 6, 4, 6, 5, 4];
  console.log(head.map((h, i) => h.padEnd(w[i])).join(''));
  console.log('-'.repeat(w.reduce((a, b) => a + b, 0)));
  for (const [id, s] of Object.entries(summary.by_algorithm)) {
    const m = s.metrics;
    const ci = m.fault_cases && m.top1 != null ? wilson(m.top1, m.fault_cases) : null;
    const row = [
      id.padEnd(w[0]),
      String(s.status).padEnd(w[1]),
      `${m.top1}/${m.fault_cases}`.padEnd(w[2]),
      (m.top1_rate == null ? '-' : (m.top1_rate * 100).toFixed(0)).padEnd(w[3]),
      (ci ? `[${ci[0]},${ci[1]}]` : '-').padEnd(w[4]),
      `${m.exact_idv_top1}/${m.tep_fault_cases}`.padEnd(w[5]),
      (m.exact_idv_top1_rate == null ? '-' : (m.exact_idv_top1_rate * 100).toFixed(0)).padEnd(w[6]),
      `${m.fe_style_top3}/${m.tep_fault_cases}`.padEnd(w[7]),
      `${m.control_pass}/${m.control_cases}`.padEnd(w[8]),
      String(m.false_alarms).padEnd(w[9]),
      String(m.abstained).padEnd(w[10]),
      String(s.errors).padEnd(w[11]),
      String(s.not_applicable).padEnd(w[12]),
    ];
    console.log(row.join(''));
  }
  console.log(`\nresults: baseline-lab/results/runs/${run_id}/`);
}
