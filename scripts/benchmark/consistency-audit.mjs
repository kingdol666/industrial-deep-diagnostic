#!/usr/bin/env node
// consistency-audit.mjs — benchmark pipeline step 3b: run-over-run consistency
// audit for one scenario (or all scenarios).
//
// Every dir matching workspace/diagnostic-runs/*_bench_<case_id> is ONE
// independent execution of the FULL industrial-analysis-auto pipeline. This
// script extracts the verdict each execution left on disk and compares the
// executions AGAINST EACH OTHER (not against truth — that is the grader's job,
// so this step can run inside the blind protocol).
//
// WHY A STRUCTURED SIGNATURE, NOT FREE-TEXT SIMILARITY
//   Two honest re-runs of the same scenario describe the same physics in
//   different words and at different verbosity, so raw text Jaccard is a bad
//   consistency proxy (measured: 0.16 for two runs that both say "XMV_10 valve
//   sticking -> temperature-loop limit cycle"). What is actually stable is:
//     mechanism_class   WEAR / DEGRADATION / CONTROL_TUNING / SENSOR / ...
//     primary_tag       the actuator/measurement tag the verdict pivots on
//                       (XMV_* actuator > XMEAS_* measurement > IDV* fault id)
//     cause_tokens      tokens of cause + class + hypothesis name
//   A re-run is CONSISTENT when diagnosis_type matches AND (the primary tag
//   matches, or the mechanism class matches with >= 0.35 cause-token overlap).
//
// ERA DISCIPLINE
//   Run-dir timestamp prefix < 20260914 is the v1 era: the pipeline had not yet
//   gained the anti-oscillation / confidence-cap / missing-discriminating-
//   channel discipline. Cross-era verdict flips are documented SYSTEM
//   REVISION, not run-to-run instability — so the headline metric is
//   WITHIN-ERA agreement and cross-era pairs are reported separately.
//
// Output: results/benchmark/consistency_audit.json
// Exit 1 if any within-era audited case is DIVERGENT (orchestrator gate).
//
// Usage:
//   node scripts/benchmark/consistency-audit.mjs --case tep_d14_reactor_valve_sticking
//   node scripts/benchmark/consistency-audit.mjs                 # all 12 scenarios
//   node scripts/benchmark/consistency-audit.mjs --min-runs 2 --era v2

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RESULTS = path.join(ROOT, 'results', 'benchmark');
const RUNS = path.join(ROOT, 'workspace', 'diagnostic-runs');
const TIER = path.join(ROOT, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json');
const OUT = path.join(RESULTS, 'consistency_audit.json');
const ERA_BOUNDARY = '20260914';

const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const caseFilter = opt('--case', '');
const minRuns = Number(opt('--min-runs', '2'));
const eraFilter = opt('--era', '');

const tier = JSON.parse(fs.readFileSync(TIER, 'utf8'));
const cases = tier.cases.filter((c) => !caseFilter || c.case_id === caseFilter);
if (!cases.length) {
  console.error(`[consistency] no case matches --case ${caseFilter}`);
  process.exit(2);
}

// ---------- text -> comparable token set (language agnostic) ----------
const STOP = new Set(['the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'are', 'was', 'were', 'has', 'have', 'not', 'but', 'its', 'due', 'via', 'per']);
function tokens(text) {
  const s = String(text ?? '').toLowerCase();
  const out = new Set();
  for (const t of s.match(/[a-z][a-z0-9_]{2,}/g) || []) if (!STOP.has(t)) out.add(t);
  const cjk = s.replace(/[^\u4e00-\u9fff]+/g, ' ');
  for (const chunk of cjk.split(/\s+/)) {
    for (let i = 0; i + 2 <= chunk.length; i++) out.add(chunk.slice(i, i + 2));
  }
  return out;
}
function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter += 1;
  return inter / (a.size + b.size - inter);
}

// ---------- equipment-tag extraction (objective, language independent) ----------
const TAG_RE = /\b(XMV|XMEAS|IDV|SPE|T2)[ _-]?(\d{1,3})\b/gi;
function tagsOf(...texts) {
  const s = texts.filter(Boolean).join(' ');
  const out = new Set();
  for (const m of s.matchAll(TAG_RE)) out.add(`${m[1].toUpperCase()}${Number(m[2])}`);
  return [...out].sort();
}
/** Priority: actuator (XMV) > measurement (XMEAS) > fault id (IDV). */
function primaryTag(tags) {
  const pick = (p) => tags.find((t) => t.startsWith(p));
  return pick('XMV') || pick('XMEAS') || pick('IDV') || null;
}

// ---------- read one run dir ----------
function readRun(dirName) {
  const runDir = path.join(RUNS, dirName);
  const rec = {
    run_id: dirName,
    run_dir: path.relative(ROOT, runDir).replace(/\\/g, '/'),
    timestamp_prefix: dirName.slice(0, 15),
    era: dirName.slice(0, 8) >= ERA_BOUNDARY ? 'v2' : 'v1',
    proven: false,
    diagnosis_type: null,
    primary_finding: '',
    survival_count: null,
    confidence: null,
    confidence_level: null,
    mechanism: null,
  };
  try {
    const fin = JSON.parse(fs.readFileSync(path.join(runDir, 'pipeline_finalize_report.json'), 'utf8'));
    rec.proven = fin.overall === 'PASS' && fs.existsSync(path.join(runDir, '.pipeline_events.jsonl'));
    rec.finalize_overall = fin.overall ?? null;
  } catch { rec.proven = false; }

  try {
    const D = JSON.parse(fs.readFileSync(path.join(runDir, '04_diagnostics/diagnosis.json'), 'utf8'));
    rec.diagnosis_type = D.diagnosis_type ?? null;
    rec.primary_finding = String(D.primary_finding ?? '');
    const surv = D.hypotheses?.surviving ?? [];
    rec.survival_count = surv.length;
    const h = surv[0] ?? null;
    const tags = tagsOf(rec.primary_finding, h?.name, h?.root_physical_cause, h?.physical_logic_chain);
    const causeText = [h?.name, h?.mechanism_class, h?.root_physical_cause].filter(Boolean).join(' ');
    rec.mechanism = {
      id: h?.id ?? null,
      name: h?.name ?? null,
      mechanism_class: h?.mechanism_class ?? null,
      root_physical_cause: String(h?.root_physical_cause ?? '').slice(0, 240),
      tags,
      primary_tag: primaryTag(tags),
      cause_tokens: [...tokens(causeText)].sort(),
    };
  } catch { /* artifact missing */ }

  try {
    const C = JSON.parse(fs.readFileSync(path.join(runDir, '04_diagnostics/confidence.json'), 'utf8'));
    const s = C?.overall_confidence?.score;
    if (typeof s === 'number') rec.confidence = +(s <= 1 ? s * 100 : s).toFixed(1);
    rec.confidence_level = C?.overall_confidence?.level ?? null;
  } catch { /* artifact missing */ }

  return rec;
}

// ---------- canonical run = the one the grader committed ----------
function canonicalRunDir(caseId) {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(RESULTS, 'gradings', `${caseId}.json`), 'utf8'));
    if (j.run_dir) return path.basename(j.run_dir);
  } catch { /* no grading */ }
  return null;
}

// ---------- comparison rule ----------
function compare(canon, run) {
  const sameType = run.diagnosis_type === canon.diagnosis_type;
  const cm = canon.mechanism ?? {};
  const rm = run.mechanism ?? {};
  const sameTag = !!cm.primary_tag && cm.primary_tag === rm.primary_tag;
  const sameClass = !!cm.mechanism_class && cm.mechanism_class === rm.mechanism_class;
  const causeOverlap = jaccard(new Set(cm.cause_tokens ?? []), new Set(rm.cause_tokens ?? []));
  let verdict;
  if (!sameType) verdict = 'DIVERGENT';
  else if (sameTag || (sameClass && causeOverlap >= 0.35)) verdict = 'CONSISTENT';
  else if (sameClass || causeOverlap >= 0.2) verdict = 'WEAK';
  else verdict = 'DIVERGENT';
  return {
    against: canon.run_id,
    run: run.run_id,
    era: run.era,
    verdict,
    same_diagnosis_type: sameType,
    canonical_type: canon.diagnosis_type,
    run_type: run.diagnosis_type,
    canonical_primary_tag: cm.primary_tag ?? null,
    run_primary_tag: rm.primary_tag ?? null,
    same_primary_tag: sameTag,
    canonical_mechanism_class: cm.mechanism_class ?? null,
    run_mechanism_class: rm.mechanism_class ?? null,
    same_mechanism_class: sameClass,
    cause_token_overlap: Number(causeOverlap.toFixed(4)),
    canonical_mechanism: cm.name ?? null,
    run_mechanism: rm.name ?? null,
    confidence_canonical: canon.confidence,
    confidence_run: run.confidence,
    confidence_delta: canon.confidence != null && run.confidence != null ? +(run.confidence - canon.confidence).toFixed(1) : null,
  };
}

const report = {
  generated_at: new Date().toISOString(),
  comparison: 'run-over-run (truth-free): each execution compared against the case canonical execution',
  consistency_rule: 'CONSISTENT = same diagnosis_type AND (same primary equipment tag OR same mechanism_class with >=0.35 cause-token overlap); WEAK = same type, weaker structural agreement; DIVERGENT = different diagnosis_type or unrelated mechanism',
  era_boundary: ERA_BOUNDARY,
  era_semantics: `run-dir prefix < ${ERA_BOUNDARY} = v1 (pre anti-oscillation/cap discipline, documented system revision); headline metric is WITHIN-ERA agreement`,
  min_runs: minRuns,
  cases: {},
};

let withinEraDivergent = 0;
let crossEraDivergent = 0;
let withinEraPairs = 0;
let withinEraPairsStable = 0;

for (const c of cases) {
  const dirs = fs.existsSync(RUNS) ? fs.readdirSync(RUNS).filter((d) => d.endsWith(`_bench_${c.case_id}`)).sort() : [];
  const runs = dirs.map(readRun);
  const canonDir = canonicalRunDir(c.case_id);
  const proven = runs.filter((r) => r.proven && r.diagnosis_type);
  const canon = runs.find((r) => r.run_id === canonDir) || proven.at(-1) || null;

  const pairs = [];
  const byEra = {};
  for (const era of ['v1', 'v2']) {
    const inEra = proven.filter((r) => r.era === era);
    const others = era === canon?.era ? inEra.filter((r) => r.run_id !== canon.run_id) : [];
    const eraPairs = canon ? others.map((r) => compare(canon, r)) : [];
    for (const p of eraPairs) {
      withinEraPairs += 1;
      if (p.verdict === 'DIVERGENT') withinEraDivergent += 1;
      else withinEraPairsStable += 1;
    }
    // cross-era pairs (informational only — documented system revision)
    const crossEra = canon && era !== canon.era ? inEra.map((r) => compare(canon, r)) : [];
    for (const p of crossEra) if (p.verdict === 'DIVERGENT') crossEraDivergent += 1;
    byEra[era] = {
      n_runs_proven: inEra.length,
      verdict_types: [...new Set(inEra.map((r) => r.diagnosis_type))],
      confidence_range: inEra.length && inEra.every((r) => r.confidence != null)
        ? [Math.min(...inEra.map((r) => r.confidence)), Math.max(...inEra.map((r) => r.confidence))] : null,
      pairs: [...eraPairs, ...crossEra],
    };
    pairs.push(...byEra[era].pairs);
  }

  // status is decided WITHIN the canonical run's era
  const canonEra = canon?.era ?? 'v2';
  const within = byEra[canonEra]?.pairs.filter((p) => p.era === canonEra) ?? [];
  let status;
  if (!canon || (byEra[canonEra]?.n_runs_proven ?? 0) < minRuns) status = 'INSUFFICIENT-RUNS';
  else if (within.some((p) => p.verdict === 'DIVERGENT')) status = 'DIVERGENT';
  else if (within.some((p) => p.verdict === 'WEAK')) status = 'WEAK';
  else status = 'CONSISTENT';

  report.cases[c.case_id] = {
    dataset: c.dataset,
    control: !!c.control,
    canonical_run_dir: canon?.run_dir ?? null,
    canonical_era: canonEra,
    n_runs_found: runs.length,
    n_runs_proven: proven.length,
    status,
    eras: byEra,
    runs: runs.map((r) => ({
      run_id: r.run_id, era: r.era, proven: r.proven, diagnosis_type: r.diagnosis_type,
      mechanism_class: r.mechanism?.mechanism_class ?? null,
      primary_tag: r.mechanism?.primary_tag ?? null,
      mechanism: r.mechanism?.name ?? null,
      survival_count: r.survival_count, confidence: r.confidence,
    })),
  };

  console.log(`[consistency] ${c.case_id.padEnd(30)} found=${runs.length} proven=${proven.length} canon_era=${canonEra} → ${status}`);
  for (const p of within) {
    console.log(`[consistency]   ↳ vs ${p.run}: ${p.verdict} type ${p.canonical_type}=${p.run_type} tag ${p.canonical_primary_tag}=${p.run_primary_tag} class ${p.canonical_mechanism_class}=${p.run_mechanism_class} cause_ov=${p.cause_token_overlap} confΔ=${p.confidence_delta}`);
  }
  for (const p of pairs.filter((q) => q.era !== canonEra)) {
    if (p.verdict === 'DIVERGENT') console.log(`[consistency]   ↳ (cross-era ${p.era}) ${p.run}: ${p.canonical_type}→${p.run_type} — documented system revision, excluded from headline`);
  }
  if (status === 'INSUFFICIENT-RUNS') {
    console.log(`[consistency]   ↳ contract: run the FULL industrial-analysis-auto pipeline (Steps 2-9) once more for ${c.case_id} in a FRESH run dir, then re-run this audit`);
  }
}

const statuses = Object.values(report.cases).map((c) => c.status);
report.summary = {
  cases_audited: statuses.filter((s) => s !== 'INSUFFICIENT-RUNS').length,
  consistent: statuses.filter((s) => s === 'CONSISTENT').length,
  weak: statuses.filter((s) => s === 'WEAK').length,
  divergent: statuses.filter((s) => s === 'DIVERGENT').length,
  insufficient_runs: statuses.filter((s) => s === 'INSUFFICIENT-RUNS').length,
  within_era_pairs: withinEraPairs,
  within_era_pairs_stable: withinEraPairsStable,
  within_era_agreement: withinEraPairs ? `${withinEraPairsStable}/${withinEraPairs}` : 'n/a',
  cross_era_divergent_pairs: crossEraDivergent,
  headline: withinEraPairs
    ? `within-era verdict agreement ${withinEraPairsStable}/${withinEraPairs} over ${statuses.filter((s) => s !== 'INSUFFICIENT-RUNS').length} re-tested case(s)`
    : 'n/a — no case has >=2 proven runs in the same era yet',
};

fs.mkdirSync(RESULTS, { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(report, null, 1) + '\n');
console.log(`\n[consistency] ${report.summary.headline} · divergent=${report.summary.divergent} weak=${report.summary.weak} insufficient=${report.summary.insufficient_runs}`);
console.log(`[consistency] cross-era divergent pairs (excluded, documented revision): ${crossEraDivergent} → ${path.relative(ROOT, OUT)}`);
process.exit(withinEraDivergent > 0 ? 1 : 0);
