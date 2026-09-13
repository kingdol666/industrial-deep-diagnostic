#!/usr/bin/env node
// audit-structural.mjs — independent, deterministic quality audit of a bench run.
//
// WHY THIS EXISTS
// ---------------
// The benchmark's judge score was not a judgement. In the expansion step the
// ten "criteria" were all set to the same number:
//
//     criteria_scores: Object.fromEntries(CRIT.map(k => [k, { score: Math.round(note.judge.score / 10) }]))
//     (scripts/benchmark/zcode_direct_pipeline.mjs:503)
//
// so a scenario's gate score was the diagnosing agent's own opinion, copied ten
// times. Measured across all twelve runs, every one of the ten criteria scored
// exactly 9 — the "10-criterion quality gate" carried ZERO discriminative
// information, and the reported mean of 91.0 was a restatement of what the
// graded artifact said about itself.
//
// This script computes a score that is independent of the note by inspecting the
// pipeline's own artifacts. It is deliberately *structural*: it verifies that the
// evidence a criterion claims to rest on is actually present, traceable and
// non-degenerate. It does not attempt to re-do the reasoning, and it is not a
// substitute for a domain expert — it is a floor that a non-executed run cannot
// clear.
//
// Usage: node scripts/benchmark/audit-structural.mjs [--only <case>] [--json]

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RUNS = path.join(ROOT, 'workspace/diagnostic-runs');
const OUT = path.join(ROOT, 'results/benchmark/structural_audit.json');
const args = process.argv.slice(2);
const only = args.includes('--only') ? args[args.indexOf('--only') + 1] : null;
const asJson = args.includes('--json');

// readJson must not conflate "file missing" with "file failed to parse" — an
// earlier revision swallowed both as null and reported four false failures.
const loadErrors = [];
const readJson = (p) => {
  if (!fs.existsSync(p)) { loadErrors.push(`MISSING ${p}`); return null; }
  const txt = fs.readFileSync(p, 'utf8');
  try { return JSON.parse(txt); }
  catch (e) { loadErrors.push(`PARSE-FAIL ${p}: ${e.message} (${txt.length} bytes)`); return null; }
};
const readText = (p) => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } };
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

// diagnosis.hypotheses is an OBJECT: { surviving: [...], competing_sets: [...], eliminated: [...] }.
// Each surviving hypothesis carries supporting_evidence[], falsification_conditions[]
// and physical_logic_chain[]; each eliminated one carries specific_evidence and
// revival_condition. Reading it as a flat array was a bug in an earlier revision
// of this auditor and produced four spurious all-run failures.
const surviving = (a) => a.diagnosis?.hypotheses?.surviving ?? [];
const eliminated = (a) => a.diagnosis?.hypotheses?.eliminated ?? [];

// Each criterion returns { score: 0..10, checks: [{name, ok, detail}] }.
// A criterion with unmet core checks cannot score above 5, so a run that skipped
// the work cannot present as "excellent".
const CRITERIA = [
  ['data_quality_awareness', (a) => {
    const c = [];
    const vr = a.validate_report?.correlation?.data_summary;
    c.push({ name: 'validate_report carries a data summary', ok: !!vr });
    c.push({ name: 'records total row count', ok: isNum(vr?.total_rows) && vr.total_rows > 0, detail: vr?.total_rows });
    c.push({ name: 'records analysed vs total column counts', ok: isNum(vr?.numeric_columns_total) && isNum(vr?.numeric_columns_analyzed) });
    c.push({ name: 'states which columns were excluded and why', ok: 'excluded_columns' in (vr ?? {}) });
    c.push({ name: 'diagnosis discloses data gaps', ok: Array.isArray(a.diagnosis?.data_gaps) });
    return c;
  }],
  ['variable_classification', (a) => {
    const c = [];
    const sig = a.ontology?.signals ?? {};
    const all = Object.values(sig).flat().filter(Boolean);
    c.push({ name: 'ontology enumerates signals', ok: all.length > 0, detail: all.length });
    c.push({ name: 'every signal declares a role', ok: all.length > 0 && all.every((s) => !!s.role) });
    // The ontology schema defines TWO role vocabularies: signal roles
    // [target, predictor, confounder, control, metadata] and metadata_columns
    // roles [batch_id, product_code, timestamp, operator]. Checking every entry
    // against only the first flagged the legitimate batch_id as invalid.
    const SIGNAL_ROLES = ['target', 'predictor', 'confounder', 'control', 'metadata'];
    const META_ROLES = ['batch_id', 'product_code', 'timestamp', 'operator'];
    for (const [bucket, entries] of Object.entries(sig)) {
      if (!Array.isArray(entries) || !entries.length) continue;
      const vocab = /metadata/i.test(bucket) ? META_ROLES : SIGNAL_ROLES;
      const bad = entries.filter((s) => s.role && !vocab.includes(s.role)).map((s) => `${bucket}:${s.role}`);
      c.push({ name: `roles in "${bucket}" use its schema vocabulary`, ok: bad.length === 0, detail: bad.join(',') || `n=${entries.length}` });
    }
    // Physical meaning is optional in the ontology schema; it is satisfied when
    // the ontology carries per-variable semantics OR records physical principles
    // OR the diagnosis annotates variables — the semantics must exist somewhere.
    const principles = a.ontology?.physical_principles ?? [];
    const withMeaning = all.filter((s) => s.physical_meaning).length;
    c.push({ name: 'variable semantics recorded somewhere (ontology or diagnosis)',
      ok: withMeaning > 0 || principles.length > 0 || surviving(a).some((h) => (h.physical_logic_chain ?? []).length > 0),
      detail: `meaning=${withMeaning}/${all.length}, principles=${principles.length}` });
    return c;
  }],
  ['time_alignment_and_sorting', (a) => {
    const c = [];
    const timeCol = a.input_manifest?.time_col ?? a.input_manifest?.time_column;
    c.push({ name: 'a time column is declared', ok: !!timeCol, detail: timeCol });
    const mode = a.validate_report?.correlation?.data_summary?.data_view_mode;
    const sorted = a.validate_report?.anti_spurious?.sorting_validation?.time_sorted;
    c.push({ name: 'time ordering is validated', ok: !!mode || sorted === true, detail: mode ?? String(sorted) });
    const rc = a.reasoning_chain?.reasoning_chains ?? [];
    const r1 = rc.find((s) => /R1|数据探查|Data Probing/i.test(s.step_name ?? ''));
    c.push({ name: 'R1 records dimensions read from the file', ok: !!r1 && /\d+\s*(行|rows)/.test(JSON.stringify(r1)) });
    return c;
  }],
  ['visualization_quality', (a) => {
    const c = [];
    c.push({ name: 'figure PNG exists on disk', ok: a._figuresPng.length > 0, detail: a._figuresPng.length });
    c.push({ name: 'plot_manifest records the plots', ok: !!a.plot_manifest });
    c.push({ name: 'visual_analysis.json present (charts were read, not just drawn)', ok: !!a.visual_analysis });
    c.push({ name: 'image_captions fallback present', ok: !!a.image_captions });
    const va = JSON.stringify(a.visual_analysis ?? {});
    c.push({ name: 'at least one visual finding is recorded', ok: va.length > 60 });
    return c;
  }],
  ['evidence_based_conclusions', (a) => {
    const c = [];
    const inv = a.evidence?.evidence_inventory ?? {};
    const items = Object.values(inv).flat().filter(Boolean);
    c.push({ name: 'evidence inventory is non-empty', ok: items.length > 0, detail: items.length });
    c.push({ name: 'every evidence item carries a level', ok: items.length > 0 && items.every((e) => isNum(e.evidence_level)) });
    c.push({ name: 'every evidence item cites a source', ok: items.length > 0 && items.every((e) => !!e.source) });
    c.push({ name: 'conclusions reference recorded figures', ok: /03_figures|\.png/.test(JSON.stringify(inv)) });
    const sv = surviving(a);
    c.push({ name: 'surviving hypotheses each carry supporting evidence',
      ok: sv.length > 0 && sv.every((h) => (h.supporting_evidence ?? []).length > 0),
      detail: `${sv.length} surviving` });
    return c;
  }],
  ['correlation_vs_causation', (a) => {
    const c = [];
    const as = a.validate_report?.anti_spurious;
    c.push({ name: 'anti-spurious validation block present', ok: !!as });
    const blob = JSON.stringify(as ?? {});
    c.push({ name: 'lag / cross-correlation evidence recorded', ok: /lag|ccf|lead/i.test(blob) });
    c.push({ name: 'confounders annotated in the ontology', ok: Array.isArray(a.ontology?.confounders) });
    // A control-loop / definitional pair is a correlation with no causal content.
    // The layer that catches these is the Simpson / leave-one-out / trend block.
    c.push({ name: 'control-loop and confound handling recorded',
      ok: /simpson|leave_one_out|time_trend|distribution_analysis/i.test(blob),
      detail: (as ? Object.keys(as).filter((k) => /simpson|leave_one_out|time_trend|distribution/i.test(k)).join(',') : 'no block') });
    return c;
  }],
  ['uncertainty_disclosure', (a) => {
    const c = [];
    const conf = a.confidence;
    c.push({ name: 'confidence artifact present', ok: !!conf });
    // overall_confidence is an object {score, level, summary} per
    // confidence_schema.json — NOT a bare float. Accept the schema shape.
    const oc = conf?.overall_confidence;
    const score = typeof oc === 'object' && oc !== null ? oc.score : oc;
    c.push({ name: 'overall confidence present and in range (0-100 or 0-1)', ok: isNum(score) && score > 0 && score <= 100, detail: typeof oc === 'object' ? score : oc });
    c.push({ name: 'overall confidence declares a level', ok: typeof oc === 'object' && ['HIGH', 'MEDIUM', 'LOW', 'VERY_LOW'].includes(oc.level), detail: oc?.level });
    c.push({ name: 'per-hypothesis breakdown recorded', ok: Object.keys(conf?.confidence_breakdown ?? {}).length > 0 });
    c.push({ name: 'any ceiling application is logged', ok: Array.isArray(conf?.confidence_ceilings_applied) });
    c.push({ name: 'diagnosis states inference gaps', ok: Array.isArray(a.diagnosis?.inference_gaps) });
    return c;
  }],
  ['report_quality', (a) => {
    const c = [];
    const md = a._reportMd;
    c.push({ name: 'report.md exists', ok: !!md });
    c.push({ name: 'report has section headings', ok: !!md && (md.match(/^#{1,3}\s/gm) ?? []).length >= 5, detail: md ? (md.match(/^#{1,3}\s/gm) ?? []).length : 0 });
    c.push({ name: 'report carries an executive summary', ok: !!md && /执行摘要|Executive Summary/i.test(md) });
    c.push({ name: 'report names the conclusion type', ok: !!md && /DETERMINED|COMPETING_SET|NEEDS_DATA/i.test(md) });
    c.push({ name: 'HTML report exists', ok: !!a._reportHtml });
    return c;
  }],
  ['no_over_claiming', (a) => {
    const c = [];
    const type = a.diagnosis?.diagnosis_type;
    // normalise the schema object to a 0-1 float
    const oc = a.confidence?.overall_confidence;
    const conf = (typeof oc === 'object' && oc !== null ? oc.score / 100 : oc);
    c.push({ name: 'a three-state conclusion type is present', ok: ['DETERMINED', 'COMPETING_SET', 'NEEDS_DATA'].includes(type), detail: type });
    // The protocol caps a COMPETING_SET confidence; a run that violates its own
    // cap is over-claiming regardless of how confident its prose sounds.
    if (type === 'COMPETING_SET') {
      c.push({ name: 'COMPETING_SET respects the documented confidence cap (<=0.70)', ok: isNum(conf) && conf <= 0.70 + 1e-9, detail: conf });
    } else {
      c.push({ name: 'COMPETING_SET cap check not applicable', ok: true, detail: type });
    }
    // Falsification lives on surviving hypotheses as falsification_conditions,
    // and on eliminated ones as revival_condition.
    const sv = surviving(a), el = eliminated(a);
    const svOk = sv.length > 0 && sv.every((h) => (h.falsification_conditions ?? []).length > 0);
    const elOk = el.length === 0 || el.every((h) => !!h.revival_condition);
    c.push({ name: 'falsification / revival conditions recorded for every hypothesis', ok: svOk && elOk,
      detail: `surviving=${sv.length} (${sv.filter((h) => (h.falsification_conditions ?? []).length).length} with conditions), eliminated=${el.length}` });
    // A conclusion that claims near-certainty on a weak signature is over-claiming.
    c.push({ name: 'weak-signature confidence stays below certainty', ok: !isNum(conf) || conf < 0.95, detail: conf });
    return c;
  }],
  ['completeness', (a) => {
    const required = ['input_manifest', 'user_context', 'run_config', 'ontology', 'schema', 'feature_summary',
      'analysis_parameter_selection', 'scenario_classification', 'anomaly_report', 'validate_report',
      'data_analysis_conclusion', 'plot_manifest', 'visual_analysis', 'image_captions', 'diagnosis',
      'evidence', 'confidence', 'reasoning_chain', 'judge_feedback', 'report', 'run_summary',
      'optimizer', 'html_review', 'evidence_closure_report'];
    const missing = required.filter((k) => !a._present[k]);
    return [{ name: `all ${required.length} required artifacts present`, ok: missing.length === 0, detail: missing.join(',') || 'none missing' }];
  }],
];

function collect(runDir) {
  const j = (rel) => readJson(path.join(runDir, rel));
  const figDir = path.join(runDir, '03_figures');
  return {
    input_manifest: j('00_input/input_manifest.json'),
    user_context: j('00_input/user_context.json'),
    run_config: j('00_input/run_config.json'),
    ontology: j('01_ontology/ontology.json'),
    schema: j('01_ontology/schema.json'),
    feature_summary: j('02_processed/feature_summary.json'),
    analysis_parameter_selection: j('02_processed/analysis_parameter_selection.json'),
    scenario_classification: j('02_processed/scenario_classification.json'),
    anomaly_report: j('02_processed/anomaly_report.json'),
    validate_report: j('02_processed/validate_report.json'),
    data_analysis_conclusion: j('02_processed/data_analysis_conclusion.json'),
    plot_manifest: j('03_figures/plot_manifest.json'),
    visual_analysis: j('03_figures/visual_analysis.json'),
    image_captions: j('03_figures/image_captions.json'),
    diagnosis: j('04_diagnostics/diagnosis.json'),
    evidence: j('04_diagnostics/evidence.json'),
    confidence: j('04_diagnostics/confidence.json'),
    reasoning_chain: j('04_diagnostics/reasoning_chain.json'),
    judge_feedback: j('05_review/judge_feedback.json'),
    html_review: j('05_review/html_review.json'),
    optimizer_preflight: readText(path.join(runDir, '05_review/optimizer_preflight.md')),
    report: readText(path.join(runDir, 'report.md')),
    run_summary: j('run_summary.json'),
    optimizer: readText(path.join(runDir, 'optimizer.md')),
    evidence_closure_report: j('evidence_closure_report.json'),
    _reportMd: readText(path.join(runDir, 'report.md')),
    _reportHtml: readText(path.join(runDir, 'diagnostic-report.html')),
    _figuresPng: fs.existsSync(figDir) ? fs.readdirSync(figDir).filter((f) => f.endsWith('.png')) : [],
    _present: Object.fromEntries(['00_input/input_manifest.json', '00_input/user_context.json', '00_input/run_config.json',
      '01_ontology/ontology.json', '01_ontology/schema.json', '02_processed/feature_summary.json',
      '02_processed/analysis_parameter_selection.json', '02_processed/scenario_classification.json',
      '02_processed/anomaly_report.json', '02_processed/validate_report.json', '02_processed/data_analysis_conclusion.json',
      '03_figures/plot_manifest.json', '03_figures/visual_analysis.json', '03_figures/image_captions.json',
      '04_diagnostics/diagnosis.json', '04_diagnostics/evidence.json', '04_diagnostics/confidence.json',
      '04_diagnostics/reasoning_chain.json', '05_review/judge_feedback.json', 'report.md', 'run_summary.json',
      'optimizer.md', '05_review/html_review.json', 'evidence_closure_report.json']
      .map((rel) => [rel.replace(/^.*\//, '').replace(/\.(json|md)$/, ''), fs.existsSync(path.join(runDir, rel))])),
  };
}

// ── run ──
const runDirs = fs.readdirSync(RUNS).filter((d) => d.includes('_bench_') && (!only || d.includes(only))).sort();
const results = [];

for (const dir of runDirs) {
  const runDir = path.join(RUNS, dir);
  const caseId = dir.split('_bench_', 2)[1];
  loadErrors.length = 0;
  const a = collect(runDir);
  const per = {};
  let weighted = 0, totalWeight = 0;
  const hardFails = [];

  // weights mirror the project's judge template
  const WEIGHTS = { data_quality_awareness: 0.15, variable_classification: 0.10, time_alignment_and_sorting: 0.10,
    visualization_quality: 0.10, evidence_based_conclusions: 0.20, correlation_vs_causation: 0.10,
    uncertainty_disclosure: 0.10, report_quality: 0.10, no_over_claiming: 0.10, completeness: 0.05 };

  for (const [name, fn] of CRITERIA) {
    const checks = fn(a);
    const passed = checks.filter((c) => c.ok).length;
    let score = checks.length ? Math.round((passed / checks.length) * 10) : 0;
    // A criterion whose core checks failed cannot present as excellent.
    if (passed < checks.length) score = Math.min(score, 5 + Math.round(3 * (passed / checks.length)));
    per[name] = { score, passed, total: checks.length, checks };
    weighted += score * WEIGHTS[name];
    totalWeight += WEIGHTS[name];
    for (const c of checks) if (!c.ok) hardFails.push(`${name}: ${c.name}${c.detail !== undefined ? ` (${c.detail})` : ''}`);
    }

  const structural = Math.round(weighted / totalWeight * 10); // 0..100
  const selfReported = a.judge_feedback?.overall_score ?? null;
  results.push({
    case_id: caseId, run_dir: path.relative(ROOT, runDir).replace(/\\/g, '/'),
    structural_score: structural,
    note_self_reported_score: selfReported,
    delta: selfReported === null ? null : selfReported - structural,
    criteria: per,
    unmet_checks: hardFails,
    load_errors: [...loadErrors],
  });
}

const summary = {
  generated_at: new Date().toISOString(),
  purpose: 'Independent structural audit of bench runs. Replaces the note-copied judge score, which scored all ten criteria identically in every run.',
  runs_audited: results.length,
  mean_structural_score: results.length ? +(results.reduce((s, r) => s + r.structural_score, 0) / results.length).toFixed(1) : null,
  mean_self_reported_score: results.length ? +(results.reduce((s, r) => s + (r.note_self_reported_score ?? 0), 0) / results.length).toFixed(1) : null,
  distinct_self_reported_scores: [...new Set(results.map((r) => r.note_self_reported_score))].sort((x, y) => x - y),
  distinct_structural_scores: [...new Set(results.map((r) => r.structural_score))].sort((x, y) => x - y),
  results,
};
fs.writeFileSync(OUT, JSON.stringify(summary, null, 1));

if (asJson) { console.log(JSON.stringify(summary, null, 1)); }
else {
  console.log('independent structural audit — bench runs\n');
  console.log(`  ${'case'.padEnd(30)} ${'structural'.padStart(10)} ${'self-rep'.padStart(9)} ${'delta'.padStart(6)}  unmet`);
  for (const r of results) {
    console.log(`  ${r.case_id.padEnd(30)} ${String(r.structural_score).padStart(10)} ${String(r.note_self_reported_score).padStart(9)} ${String(r.delta).padStart(6)}  ${r.unmet_checks.length}`);
  }
  console.log(`\n  mean structural      : ${summary.mean_structural_score}`);
  console.log(`  mean self-reported   : ${summary.mean_self_reported_score}`);
  console.log(`  distinct self-reported scores : [${summary.distinct_self_reported_scores.join(', ')}]`);
  console.log(`  distinct structural   scores  : [${summary.distinct_structural_scores.join(', ')}]`);
  console.log(`\n  -> ${path.relative(ROOT, OUT)}`);
}
