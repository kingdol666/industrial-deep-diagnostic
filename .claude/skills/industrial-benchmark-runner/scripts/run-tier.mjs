#!/usr/bin/env node
// run-tier.mjs — reproducible tier orchestration for the diagnosis benchmark.
//
// The benchmark has one human/agent-in-the-loop step (the diagnostic inference
// itself). This driver makes everything AROUND it reproducible:
//
//   prepare  → deterministic data ingestion into a run dir (setup/inspect/convert)
//   notes    → emit one note skeleton per case (the exact note schema the
//              direct runner consumes) for the diagnosing agent to fill
//   commit   → expand filled notes into schema-compliant artifacts, run the
//              pipeline gates, grade each case, append to journal.jsonl
//   status   → per-case state table (prepared / note filled / graded)
//
// Usage:
//   node run-tier.mjs prepare --tier scripts/benchmark/cases/tier0_smoke.json
//   node run-tier.mjs notes   --tier <file> --out results/benchmark/notes
//   node run-tier.mjs commit  --tier <file> [--only case_a,case_b]
//   node run-tier.mjs status  --tier <file>

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..', '..', '..');
const DIRECT = path.join(ROOT, 'scripts', 'benchmark', 'zcode_direct_pipeline.mjs');
const RESULTS = path.join(ROOT, 'results', 'benchmark');
const STATE = path.join(RESULTS, 'tier_state.json');

const args = process.argv.slice(2);
const stage = args[0];
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const tierArg = opt('--tier', 'scripts/benchmark/cases/tier0_smoke.json');
const TIER = path.isAbsolute(tierArg) ? tierArg : path.join(ROOT, tierArg);
const NOTES_DIR = path.resolve(ROOT, opt('--out', 'results/benchmark/notes'));
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

function notePath(caseId) {
  return path.join(NOTES_DIR, `${caseId}.note.json`);
}

/** Note skeleton — mirrors the exact schema zcode_direct_pipeline.mjs consumes. */
function noteTemplate(c) {
  return {
    _instructions: [
      'Fill every REQUIRED field following the diagnostic skill protocol; delete this _instructions key before commit.',
      'confidence is a 0-1 float. Control cases must be diagnosed as normal operation with calibrated confidence.',
      'Every hypothesis needs: name, mechanism_class (fluid-restriction|rotor-dynamics|cavitation|operating-point|feed-composition-step|cooling-disturbance|feed-loss|ph-control-fault|aeration-fault|agitator-fault|sensor-drift|feed-system-fault|normal-operation|normal-appearance|upstream-suppressed), confidence (0-1), verdict (surviving|eliminated), logic_chain[], evidence[], contradiction[], falsification[].',
      'analysis_findings needs key_process_findings[] and ontology_industry_interpretation[] (both string arrays).',
      'Do NOT read results/benchmark/gradings/* (ground truth leak) — the truth lives only in the grader.',
    ],
    _case_id: c.case_id,
    _control: !!c.control,
    diagnosis_type: 'DETERMINED | COMPETING_SET | NEEDS_DATA',
    primary_finding: '<the surviving root cause in one sentence>',
    confidence: 0.0,
    ontology: {
      domain: 'process domain inferred from column semantics',
      physics_notes: 'governing physical principles for this process (string or list of strings)',
      variables: [{ name: '<column>', unit: '<unit>', meaning: '<physical meaning>' }],
    },
    hypotheses: [
      {
        name: '<hypothesis name>',
        mechanism_class: 'operating-point',
        confidence: 0.0,
        verdict: 'surviving | eliminated',
        logic_chain: ['<mechanism step 1>', '<mechanism step 2>'],
        evidence: ['<statistical/visual evidence, evidence level L1-L7 noted>'],
        contradiction: ['<evidence against — required for eliminated hypotheses>'],
        falsification: ['<what observation would revive/reject this>'],
        proof: '<physical magnitude/direction sanity check>',
        predicted: ['<observable consequences>'],
      },
    ],
    analysis_findings: {
      key_process_findings: ['<key finding from the statistics stage>'],
      ontology_industry_interpretation: ['<domain interpretation grounding the findings>'],
      time_lag: '<cross-parameter temporal relation, e.g. 同相耦合 / 温度滞后流量约X个采样>',
      data_supported_conclusions: ['<conclusion directly supported by the data>'],
    },
    visual_observations: ['<what is seen in fig_temporal_overview.png>'],
    judge: { score: 0, warnings: [], validation_findings_cited: ['<validation finding cited by the judge>'] },
    audit: { verdict: 'ENDORSED | CONDITIONAL | REJECTED', notes: '<physical-audit notes>' },
    data_gaps: [],
    inference_gaps: [],
  };
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

function cmdNotes() {
  fs.mkdirSync(NOTES_DIR, { recursive: true });
  for (const c of cases()) {
    const p = notePath(c.case_id);
    if (fs.existsSync(p) && !args.includes('--force')) {
      console.log(`[notes] ${c.case_id} — exists, keeping`);
      continue;
    }
    fs.writeFileSync(p, JSON.stringify(noteTemplate(c), null, 1) + '\n');
    console.log(`[notes] ${c.case_id} → ${path.relative(ROOT, p)}`);
  }
}

function noteIsFilled(note) {
  if (!note || note._instructions) return false;
  return !!(note.diagnosis_type && note.ontology?.variables?.length && Array.isArray(note.hypotheses)
    && note.hypotheses.length && note.hypotheses.every((h) => h.verdict) && note.primary_finding && note.confidence);
}

function cmdCommit() {
  let done = 0;
  let skipped = 0;
  for (const c of cases()) {
    const entry = tierState.cases[c.case_id] || {};
    const p = notePath(c.case_id);
    if (!entry.run_dir || !fs.existsSync(entry.run_dir)) {
      console.log(`[commit] ${c.case_id} — no prepared run dir (run 'prepare' first)`);
      skipped += 1;
      continue;
    }
    if (!fs.existsSync(p)) {
      console.log(`[commit] ${c.case_id} — no note (run 'notes', fill it, then commit)`);
      skipped += 1;
      continue;
    }
    const note = JSON.parse(fs.readFileSync(p, 'utf8'));
    if (!noteIsFilled(note)) {
      console.log(`[commit] ${c.case_id} — note still a template/partial, skipping`);
      skipped += 1;
      continue;
    }
    const out = runDirect('diagnose', ['--case', c.case_id, '--run-dir', entry.run_dir, '--note', p]);
    const json = JSON.parse(out.slice(out.indexOf('{')));
    entry.graded_at = new Date().toISOString();
    entry.grading = json;
    console.log(`[commit] ${c.case_id} — top1=${json.top1} topk=${json.topk} type=${json.diagnosis_type} judge=${json.judge_score}`);
    done += 1;
  }
  save();
  console.log(`\ncommitted ${done}, skipped ${skipped}`);
}

function cmdStatus() {
  const rows = tier.cases.map((c) => {
    const e = tierState.cases[c.case_id] || {};
    const noteOk = fs.existsSync(notePath(c.case_id)) && noteIsFilled(JSON.parse(fs.readFileSync(notePath(c.case_id), 'utf8')));
    const graded = fs.existsSync(path.join(RESULTS, 'gradings', `${c.case_id}.json`));
    return `${c.case_id.padEnd(26)} prepared=${e.run_dir ? 'Y' : '-'}  note=${noteOk ? 'Y' : '-'}  graded=${graded ? 'Y' : '-'}${c.control ? '  (control)' : ''}`;
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

const stages = { prepare: cmdPrepare, notes: cmdNotes, commit: cmdCommit, status: cmdStatus, 'import-state': cmdImportState };
if (!stages[stage]) {
  console.error('stage must be prepare|notes|commit|status|import-state');
  process.exit(2);
}
stages[stage]();
