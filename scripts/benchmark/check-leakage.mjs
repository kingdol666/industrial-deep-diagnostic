#!/usr/bin/env node
// check-leakage.mjs — truth-isolation sentinel for the IDD benchmark.
//
// The benchmark's central integrity claim is that the diagnosing agent sees
// statistical evidence and a process description, and never the answer. That
// claim is only as good as the weakest process_description, so this script
// enforces it mechanically instead of trusting review.
//
// It checks, for every non-control scenario:
//   L1  no truth field of ANY scenario appears in ANY agent-visible brief
//   L2  no fault-identity keyword appears in that scenario's own process_description
//   L3  the brief carries no truth/keywords/expect_type_set/literature_baseline keys
//   L4  fault-specific vocabulary is not sitting in the generic column glossary
//
// Exit code 1 on any violation, so it can gate the benchmark run.
//
// Usage: node scripts/benchmark/check-leakage.mjs [--tier <cases.json>]

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const args = process.argv.slice(2);
const tierIdx = args.indexOf('--tier');
const TIER = tierIdx >= 0 ? args[tierIdx + 1] : 'scripts/benchmark/cases/benchmark_cases.json';
const BRIEFS = path.join(ROOT, 'results/benchmark/briefs');

const cases = JSON.parse(fs.readFileSync(path.join(ROOT, TIER), 'utf8')).cases;

// A process description may legitimately name the medium, the equipment and the
// column semantics. It may not name the fault. These are the words that only
// appear when the answer is being disclosed.
const FAULT_VOCAB = [
  '阶跃', 'step', '粘滞', 'sticking', '随机变化', 'random variation',
  '进料比', 'feed ratio', '集管压力', 'header pressure', '气蚀', 'cavitation',
  '空化', '两相流', '节流', 'throttl', '泄漏', 'leak', '堵塞', 'blockage',
  '漂移', 'drift', '偏差故障', 'deviation fault', 'IDV',
];

const FORBIDDEN_BRIEF_KEYS = ['truth', 'keywords', 'expect_type_set', 'literature_baseline'];

// Generic process vocabulary: legitimate in a process description, useless as a
// fault identifier because any diagnosis of that process will contain it.
const GENERIC_TERMS = new Set([
  'aeration', '曝气', 'do2', '溶氧', 'feed', '流加', 'ph', '阀', 'valve',
  '水', 'water', '温度', 'temperature', '压力', 'pressure', '流量', 'flow',
  '冷却', 'cooling', '进料', '成分', 'composition', '反应器', 'reactor',
  'stream 4', '入口', 'inlet', '关闭', 'close', '节流', 'throttle',
]);

const violations = [];
const notes = [];
function bad(code, msg) { violations.push({ code, msg }); }
function info(msg) { notes.push(msg); }

// ── L1/L2: per-scenario ──
for (const c of cases) {
  const briefPath = path.join(BRIEFS, `${c.case_id}.brief.json`);
  if (!fs.existsSync(briefPath)) { info(`${c.case_id}: no brief emitted yet (skipped)`); continue; }
  const briefRaw = fs.readFileSync(briefPath, 'utf8');
  const brief = JSON.parse(briefRaw);
  const pd = String(brief.process_description ?? '');
  const pdLower = pd.toLowerCase();

  // L3 — the brief must not carry grader-only keys, at any depth.
  const walk = (o, trail) => {
    if (o === null || typeof o !== 'object') return;
    for (const [k, v] of Object.entries(o)) {
      if (FORBIDDEN_BRIEF_KEYS.includes(k)) bad('L3', `${c.case_id}: brief exposes grader key "${k}" at ${trail || '$'}`);
      walk(v, `${trail}.${k}`);
    }
  };
  walk(brief, '');

  if (c.control) continue; // controls have no fault identity to conceal

  // L1 — no OTHER scenario's truth text may appear in this brief.
  for (const other of cases) {
    if (other.case_id === c.case_id || other.control) continue;
    const t = String(other.truth ?? '').trim();
    if (t.length < 6) continue;
    // compare on the distinctive part, ignoring the punctuation-heavy wrapper
    const core = t.replace(/^IDV\(\d+\)[：:]\s*/, '').split(/[（(]/)[0].trim();
    if (core.length >= 4 && pdLower.includes(core.toLowerCase())) {
      bad('L1', `${c.case_id}: brief contains truth text of ${other.case_id} ("${core}")`);
    }
  }

  // L2 — the scenario's own fault vocabulary must not appear in its description.
  for (const w of FAULT_VOCAB) {
    if (pdLower.includes(w.toLowerCase())) {
      bad('L2', `${c.case_id}: process_description discloses fault vocabulary "${w}"`);
    }
  }

  // L2b — any grading keyword that is fault-specific must not appear verbatim.
  for (const k of (c.keywords ?? [])) {
    if (k.length < 2) continue;
    if (GENERIC_TERMS.has(k.toLowerCase())) continue;
    if (pdLower.includes(k.toLowerCase())) {
      bad('L2', `${c.case_id}: process_description contains grading keyword "${k}"`);
    }
  }
}

// ── L4: keyword discrimination ──
// A keyword that also appears in every other scenario's generic vocabulary, or
// that is a plain column name, cannot identify a fault.
for (const c of cases) {
  if (c.control) continue;
  const kw = (c.keywords ?? []).map((k) => k.toLowerCase());
  const generic = kw.filter((k) => GENERIC_TERMS.has(k));
  if (generic.length === kw.length && kw.length > 0) {
    bad('L4', `${c.case_id}: every keyword is a generic process term (${generic.join(', ')}) — matches any diagnosis`);
  } else if (generic.length) {
    info(`${c.case_id}: ${generic.length}/${kw.length} keywords are generic (${generic.join(', ')})`);
  }
}

// ── L5: the note must not reproduce the withheld label verbatim ──
// Some ground truths carry an English gloss lifted from the source dataset's
// own label file (e.g. SKAB's ground_truth.json). If the note reproduces that
// phrase word-for-word, the label reached the agent somehow.
for (const c of cases) {
  if (c.control) continue;
  const notePath = path.join(ROOT, 'results/benchmark/notes', `${c.case_id}.note.json`);
  if (!fs.existsSync(notePath)) continue;
  const noteText = fs.readFileSync(notePath, 'utf8').toLowerCase();
  const glosses = [...String(c.truth ?? '').matchAll(/[（(]([^）)]*[a-zA-Z][^）)]*)[）)]/g)]
    .map((m) => m[1].trim().toLowerCase())
    .filter((g) => g.length >= 12);
  for (const g of glosses) {
    if (noteText.includes(g)) {
      bad('L5', `${c.case_id}: note reproduces the dataset label gloss verbatim ("${g}") — label may have leaked`);
    }
  }
}

// ── L6: run-dir user_context.json must satisfy the same fault-vocabulary ban ──
// The brief is not the only agent-visible input: prepare() writes
// 00_input/user_context.json into the run directory from the same
// process_description. A run dir that predates a de-leak still leaks.
const statePath = path.join(ROOT, 'results/benchmark/tier_state.json');
if (fs.existsSync(statePath)) {
  const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
  for (const t of Object.values(state.tiers ?? {})) {
    for (const [cid, e] of Object.entries(t.cases ?? {})) {
      const uc = e.run_dir ? path.join(e.run_dir, '00_input', 'user_context.json') : null;
      if (!uc || !fs.existsSync(uc)) continue;
      const pdLower = fs.readFileSync(uc, 'utf8').toLowerCase();
      const c = cases.find((x) => x.case_id === cid);
      if (!c || c.control) continue;
      for (const w of FAULT_VOCAB) {
        if (pdLower.includes(w.toLowerCase())) {
          bad('L6', `${cid}: run-dir user_context.json discloses fault vocabulary "${w}" (stale run dir — re-prepare with --force)`);
        }
      }
    }
  }
}

function main() {
  console.log('truth-isolation sentinel — IDD benchmark\n');
  for (const n of notes) console.log(`  note  ${n}`);
  if (!violations.length) {
    console.log('\n  RESULT: PASS — no truth leakage detected in agent-visible briefs');
    return 0;
  }
  console.log('');
  for (const v of violations) console.log(`  FAIL  [${v.code}] ${v.msg}`);
  console.log(`\n  RESULT: FAIL — ${violations.length} leakage violation(s)`);
  return 1;
}

// Generic process vocabulary lives with the other rule tables (declared above).

process.exit(main());
