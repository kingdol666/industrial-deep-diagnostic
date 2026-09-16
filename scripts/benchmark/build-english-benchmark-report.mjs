#!/usr/bin/env node
// build-english-benchmark-report.mjs — benchmark pipeline step 4: the English
// benchmark-standard report (Markdown + HTML), derived ENTIRELY from artifacts
// on disk. Zero hard-coded verdicts; every number is read, never written.
//
// Sources (all grader-side, never visible to a diagnosing agent):
//   results/benchmark/metrics.json            aggregate metrics + per-case rows
//   results/benchmark/gradings/*.json         per-case truth-compared verdicts
//   results/benchmark/baselines.json          PCA / FE-protocol / bare-LLM arms
//   baselines/baseline-suite/runs/*.json      suite's own live executions
//   results/benchmark/consistency_audit.json  run-over-run consistency
//   results/benchmark/retest_selection.json   the RANDOM re-test draw (seed+case)
//   results/benchmark/suite_determinism.json  suite double-run byte diff
//   results/benchmark/repro_report.json       reproducibility gate verdict
//   scripts/benchmark/cases/benchmark_cases.json  case metadata + ground truth
//
// Output: results/benchmark/benchmark_report_en.md
//         results/benchmark/benchmark_report_en.html
//
// Usage: node scripts/benchmark/build-english-benchmark-report.mjs

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RES = path.join(ROOT, 'results', 'benchmark');
const SUITE_RUNS = path.join(ROOT, 'baselines', 'baseline-suite', 'runs');
const TIER_FILE = path.join(ROOT, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json');

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const exists = (p) => fs.existsSync(p);
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`);
const num = (x, d = 1) => (x == null ? '—' : Number(x).toFixed(d));
const code = (s) => `\`${s}\``;

// ───────────────────────────── load artifacts ─────────────────────────────
const tier = readJson(TIER_FILE);
const metrics = exists(path.join(RES, 'metrics.json')) ? readJson(path.join(RES, 'metrics.json')) : null;
const baselines = exists(path.join(RES, 'baselines.json')) ? readJson(path.join(RES, 'baselines.json')) : null;
const repro = exists(path.join(RES, 'repro_report.json')) ? readJson(path.join(RES, 'repro_report.json')) : null;
const consistency = exists(path.join(RES, 'consistency_audit.json')) ? readJson(path.join(RES, 'consistency_audit.json')) : null;
const retest = exists(path.join(RES, 'retest_selection.json')) ? readJson(path.join(RES, 'retest_selection.json')) : null;
const suiteDet = exists(path.join(RES, 'suite_determinism.json')) ? readJson(path.join(RES, 'suite_determinism.json')) : null;
const stability = exists(path.join(RES, 'stability_report.json')) ? readJson(path.join(RES, 'stability_report.json')) : null;

const gradings = {};
if (exists(path.join(RES, 'gradings'))) {
  for (const f of fs.readdirSync(path.join(RES, 'gradings')).filter((x) => x.endsWith('.json'))) {
    const g = readJson(path.join(RES, 'gradings', f));
    gradings[g.case_id] = g;
  }
}
const suiteRuns = {};
if (exists(SUITE_RUNS)) {
  for (const f of fs.readdirSync(SUITE_RUNS).filter((x) => x.endsWith('.json'))) {
    const j = readJson(path.join(SUITE_RUNS, f));
    if (!j.case_id) continue;
    suiteRuns[j.case_id] = suiteRuns[j.case_id] || {};
    suiteRuns[j.case_id][f.replace(`${j.case_id}.`, '').replace('.json', '')] = j;
  }
}
const suiteRunCount = Object.values(suiteRuns).reduce((s, a) => s + Object.keys(a).length, 0);

const MODEL = baselines?.model ?? 'not recorded';
const generatedAt = new Date().toISOString().slice(0, 19).replace('T', ' ') + ' UTC';
const latestRunPrefix = Object.keys(gradings)
  .map((k) => path.basename(gradings[k].run_dir || '').slice(0, 8))
  .filter(Boolean)
  .sort()
  .at(-1) ?? '—';

// ───────────────────────────── scenario table ─────────────────────────────
const faultCases = tier.cases.filter((c) => !c.control);
const controlCases = tier.cases.filter((c) => c.control);

function iddCell(g, control) {
  if (!g) return 'not graded';
  if (control) return `control_pass = ${g.control_pass ?? '—'}`;
  const hit = g.top1 ? 'HIT' : 'miss';
  return `${hit} · ${g.diagnosis_type ?? '—'} · conf ${g.confidence ?? '—'}`;
}
function bareCell(id, control) {
  const l = baselines?.llm?.[id]?.no_candidates;
  if (!l) return 'not run';
  if (control) return l.normal_verdict === true ? 'normal ✓' : l.normal_verdict === false ? 'FALSE ALARM' : 'not run';
  return l.strict_top1_hit ? 'HIT' : 'miss';
}
function feStyleCell(id, control) {
  const f = baselines?.llm?.[id]?.with_candidates?.fe_style_top3_hit;
  if (control || f === undefined) return 'n/a';
  return f ? 'HIT' : 'miss';
}

const caseRows = tier.cases.map((c) => {
  const g = gradings[c.case_id];
  const spca = suiteRuns[c.case_id]?.pca;
  const sfe = suiteRuns[c.case_id]?.fe;
  return {
    case_id: c.case_id,
    dataset: c.dataset,
    role: c.control ? 'control' : 'fault',
    expected_type: (c.expect_type_set || []).join(' / ') || '—',
    idd: iddCell(g, c.control),
    bare: bareCell(c.case_id, c.control),
    feStyle: feStyleCell(c.case_id, c.control),
    pcaT2: spca ? pct(spca.detection?.detection_rate_T2) : '—',
    pcaSPE: spca ? pct(spca.detection?.detection_rate_SPE) : '—',
    suiteFe: sfe ? (sfe.detection?.detected ? `detected (${sfe.features?.[0]?.feature ?? '—'})` : 'not detected') : '—',
    judge: g?.judge_score ?? '—',
    rubric: g?.rubric?.score ?? '—',
    finalized: g?.checks?.finalize_passed ?? g?.finalize_passed ?? false,
  };
});

// ───────────────────────────── consistency section ─────────────────────────────
const lastDraw = retest?.last ?? null;
const retestCase = lastDraw?.case_id ?? null;
const retestAudit = retestCase && consistency?.cases?.[retestCase] ? consistency.cases[retestCase] : null;
const withinEraPairs = retestAudit?.eras?.[retestAudit.canonical_era]?.pairs?.filter((p) => p.era === retestAudit.canonical_era) ?? [];

// ───────────────────────────── Markdown ─────────────────────────────
const md = [];
md.push(`# Industrial Deep Diagnostic (IDD) — Diagnosis Benchmark Report`);
md.push('');
md.push(`> **Generated:** ${generatedAt} · **Generator:** ${code('scripts/benchmark/build-english-benchmark-report.mjs')} (derived from on-disk artifacts; zero hard-coded verdicts)`);
md.push(`> **System under test:** IDD full diagnosis pipeline ${code('industrial-analysis-auto')} Steps 2–9 (context-builder → data-processor → diagnostician → judge ∥ pre-audit → reporter → final audit → html-visualizer → html-reviewer → finalize)`);
md.push(`> **Latest canonical run batch:** ${latestRunPrefix} · **Baseline model:** ${MODEL}`);
md.push('');
md.push(`> ⚠️ **TRUTH-CONTAINING ARTIFACT (grader-side).** Appendix A lists ground truth. Do not expose this file to a diagnosing agent — it would break the blind protocol.`);
md.push('');

md.push(`## 1. Scope and object of evaluation`);
md.push('');
md.push(`The unit under evaluation is **one complete industrial diagnosis run**, not a per-sample label. Each scenario is executed end-to-end by the pipeline and scored by an independent grader that reads the artifacts the sub-agents actually wrote.`);
md.push('');
md.push(`| Dimension | What is measured |`);
md.push(`|---|---|`);
md.push(`| Correctness | Top-1 / Top-k root-cause hit against documented ground truth |`);
md.push(`| Calibration | Whether the declared three-state verdict (DETERMINED / COMPETING_SET / NEEDS_DATA) matches the achievable discriminability |`);
md.push(`| Control behaviour | False-alarm rate on three anomaly-free control scenarios |`);
md.push(`| Process quality | Deterministic rubric R1–R7 computed from artifacts, plus judge and audit gates |`);
md.push(`| Repeatability | Verdict and mechanism agreement across independent re-executions |`);
md.push(`| Reproducibility | Artifact-level execution proofs and dataset fingerprint stability |`);
md.push('');

md.push(`## 2. Benchmark protocol`);
md.push('');
md.push('```');
md.push('S0 environment    fail-fast contract checks + truth-leakage sentinel');
md.push('S1 prepare        deterministic statistics per scenario (same data + same code => byte-identical digest)');
md.push('S2 brief          blind evidence pack (statistics + process description only; no truth)');
md.push('S3 pipeline       REAL industrial-analysis-auto Steps 2-9 per scenario, sub-agents per their skill protocols');
md.push('S4 grade          independent scorer reads agent-authored artifacts, compares against truth + deterministic rubric');
md.push('S5 aggregate      metrics.json + reproducibility gate (must report REPRODUCIBLE)');
md.push('S6 report         scoring report build');
md.push('```');
md.push('');
md.push(`The four-step agent-executable test pipeline is documented in ${code('docs/benchmark/benchmark-pipeline-runbook.md')}:`);
md.push(`(1) run the pipeline on the scenario data, (2) run the baseline/LLM replication suite on the same data, (3) draw a scenario **at random** and re-run it for consistency, (4) regenerate this report.`);
md.push('');

md.push(`## 3. Scenario suite`);
md.push('');
md.push(`**${tier.cases.length} scenarios** — ${faultCases.length} fault cases + ${controlCases.length} anomaly-free controls. TEP faults carry per-fault literature baselines (FaultExplainer, arXiv:2412.14492 Table 1) and PCA detectability annotations (Chiang et al. 2001).`);
md.push('');
md.push(`| # | Scenario | Dataset | Role | Expected verdict type |`);
md.push(`|---|---|---|---|---|`);
tier.cases.forEach((c, i) => {
  md.push(`| ${i + 1} | ${code(c.case_id)} | ${c.dataset} | ${c.control ? 'control' : 'fault'} | ${(c.expect_type_set || []).join(' / ') || '—'} |`);
});
md.push('');
md.push(`Ground truth for every scenario is isolated in ${code('scripts/benchmark/cases/benchmark_cases.json')} and is never written into any pipeline-visible input, brief, or run directory.`);
md.push('');

md.push(`## 4. Primary results`);
md.push('');
if (metrics) {
  md.push(`| Metric | Value |`);
  md.push(`|---|---|`);
  md.push(`| Scenarios executed | ${metrics.executed}/${metrics.total_cases} |`);
  md.push(`| Top-1 hit (fault group) | ${metrics.top1}/${metrics.fault_cases} = ${pct(metrics.top1 / metrics.fault_cases)} (Wilson 95% CI ${num(metrics.top1_ci95?.[0], 1)}–${num(metrics.top1_ci95?.[1], 1)}%) |`);
  md.push(`| Top-k hit (fault group) | ${metrics.topk}/${metrics.fault_cases} = ${pct(metrics.topk / metrics.fault_cases)} |`);
  md.push(`| Correct-delivery rate (Top-1 ∧ DETERMINED) | ${num(metrics.cdr, 2)} (${metrics.cdr_count}/${metrics.fault_cases}) |`);
  md.push(`| Three-state calibration correct | ${metrics.calibrated}/${metrics.fault_cases} |`);
  md.push(`| Overconfident verdicts (DETERMINED ∧ wrong) | ${metrics.overconfident} |`);
  md.push(`| Controls passed | ${metrics.control_pass}/${metrics.control_cases} |`);
  md.push(`| Control false alarms | ${metrics.false_alarms} |`);
  md.push(`| Mean deterministic rubric (R1–R7) | ${metrics.mean_rubric}/100 |`);
  md.push('');
  md.push(`### 4.1 By dataset`);
  md.push('');
  md.push(`| Dataset | Cases | Top-1 | Top-k | Controls passed |`);
  md.push(`|---|---|---|---|---|`);
  for (const [ds, v] of Object.entries(metrics.by_dataset || {})) {
    md.push(`| ${ds} | ${v.cases} | ${v.top1} | ${v.topk} | ${v.control_pass}/${v.controls} |`);
  }
  md.push('');
  md.push(`> Reported as measured. No metric floor is asserted — a threshold would create an incentive to dress up results to clear the gate.`);
} else {
  md.push(`_metrics.json not found — run ${code('scripts/benchmark/aggregate.mjs')}._`);
}
md.push('');

md.push(`## 5. Per-scenario results`);
md.push('');
md.push(`| Scenario | Role | IDD verdict | Bare-LLM strict | FE-style top-3 | Suite PCA T² / SPE | Suite FE | Judge | Rubric | Finalized |`);
md.push(`|---|---|---|---|---|---|---|---|---|---|`);
for (const r of caseRows) {
  md.push(`| ${code(r.case_id)} | ${r.role} | ${r.idd} | ${r.bare} | ${r.feStyle} | ${r.pcaT2} / ${r.pcaSPE} | ${r.suiteFe} | ${r.judge} | ${r.rubric} | ${r.finalized ? 'PASS' : '—'} |`);
}
md.push('');
md.push(`Reading the table: ${code('IDD verdict')} is the truth-compared outcome of the full pipeline (hit/miss, three-state type, confidence). ${code('Bare-LLM strict')} is the same-model single-call baseline scored on mechanism keywords. ${code('Suite PCA / FE')} are the replicated classical baselines recomputed live by the baseline suite on the same prepared data.`);
md.push('');

md.push(`## 6. Baseline arms`);
md.push('');
md.push(`Three comparison arms are executed on the identical prepared data, with the model variable held constant (same deployment as the pipeline):`);
md.push('');
md.push(`| Arm | Method | Provenance |`);
md.push(`|---|---|---|`);
md.push(`| PCA | Classic PCA monitoring: reference training / 95% variance / T² + Q / 99th-percentile alarm / SPE top-3 | Chiang et al. 2001; Qin 2012 — deterministic reimplementation |`);
md.push(`| FE protocol | PCA(0.9) + T² (α=0.01 F-limit) + 6-consecutive trigger + per-sample top-6 T² contributions + EXPLAIN_ROOT | ${esc(baselines?.fe_official_code?.source ?? 'li-group/FaultExplainer')} |`);
md.push(`| Bare LLM | Single blind call per scenario, three regimes (no candidates / with candidates / FE official prompt) | ${MODEL} |`);
md.push('');
if (baselines?.summary) {
  md.push(`Suite statistics as recorded in ${code('results/benchmark/baselines.json')}:`);
  md.push('');
  md.push(`- TEP subset, FE-protocol regime with candidate list — FE-style top-3 hit: **${baselines.summary.fe_protocol_replication_with_candidates?.fe_style_top3_hit ?? '—'}**`);
  md.push(`- TEP subset, FE-protocol regime, no candidates: **${baselines.summary.fe_protocol_replication_no_candidates_strict ?? '—'}**`);
  md.push(`- FE official prompts, strict: **${baselines.summary.fe_official_prompts_strict ?? '—'}**`);
  md.push(`- Same-digest bare-LLM ablation: ${baselines.summary.single_llm_same_digest_ablation ?? '—'}`);
  md.push(`- Controls: ${baselines.summary.controls?.bare_llm_normal_verdicts ?? '—'} normal verdicts, ${baselines.summary.controls?.false_alarms ?? '—'} false alarms`);
  md.push('');
  md.push(`> ${baselines.summary.headline ?? ''}`);
  md.push('');
}
md.push(`Suite executions on disk: **${suiteRunCount}** run files across ${Object.keys(suiteRuns).length} scenarios, each written by the Nuxt replication suite at ${code('baselines/baseline-suite/runs/')}.`);
md.push('');

md.push(`## 7. Consistency (repeatability)`);
md.push('');
md.push(`### 7.1 Random re-test draw`);
if (lastDraw) {
  md.push('');
  md.push(`The re-tested scenario was selected by a uniform draw over the ${lastDraw.pool_size}-scenario pool using a recorded seed, so the choice cannot be hand-picked after seeing results:`);
  md.push('');
  md.push(`| Field | Value |`);
  md.push(`|---|---|`);
  md.push(`| Draw round | ${lastDraw.round} |`);
  md.push(`| RNG | ${lastDraw.rng} |`);
  md.push(`| Seed | ${code(String(lastDraw.seed))} |`);
  md.push(`| Uniform draw u | ${lastDraw.uniform_draw} |`);
  md.push(`| Pool size / filter | ${lastDraw.pool_size} / ${lastDraw.pool_filter} |`);
  md.push(`| **Selected scenario** | **${code(lastDraw.case_id)}** (${lastDraw.dataset}${lastDraw.control ? ', control' : ''}) |`);
  md.push('');
  md.push(`Replay the identical draw: ${code(`node scripts/benchmark/select-retest-case.mjs --seed ${lastDraw.seed}`)}.`);
  md.push('');
  if (retestAudit) {
    const nInEra = retestAudit.eras?.[retestAudit.canonical_era]?.n_runs_proven ?? 0;
    md.push(`**Outcome** — ${nInEra} proven execution(s) in the current era (${retestAudit.n_runs_proven} on disk across all eras), canonical era ${retestAudit.canonical_era}, audit status **${retestAudit.status}**.`);
    md.push('');
    if (withinEraPairs.length) {
      md.push(`| Against run | Verdict | Type (canonical = re-run) | Primary tag | Mechanism class | Confidence Δ |`);
      md.push(`|---|---|---|---|---|---|`);
      for (const p of withinEraPairs) {
        md.push(`| ${code(p.run)} | ${p.verdict} | ${p.canonical_type} = ${p.run_type} | ${p.canonical_primary_tag ?? '—'} = ${p.run_primary_tag ?? '—'} | ${p.canonical_mechanism_class ?? '—'} = ${p.run_mechanism_class ?? '—'} | ${p.confidence_delta ?? '—'} |`);
      }
      md.push('');
    }
    if (retestAudit.status === 'INSUFFICIENT-RUNS') {
      md.push(`> **Execution contract (outstanding).** This scenario has only ${nInEra} proven execution(s) in the current era; the consistency claim needs a second one. Run the full ${code('industrial-analysis-auto')} pipeline (Steps 2–9) for ${code(lastDraw.case_id)} in a **fresh run directory**, then re-run ${code('node scripts/benchmark/consistency-audit.mjs --case ' + lastDraw.case_id)}. Never copy artifacts between run directories.`);
      md.push('');
    }
  }
} else {
  md.push('');
  md.push(`_No draw recorded yet — run ${code('node scripts/benchmark/select-retest-case.mjs')}._`);
  md.push('');
}
md.push(`### 7.2 Consistency across all scenarios`);
md.push('');
if (consistency) {
  const s = consistency.summary;
  md.push(`Structured mechanism signature comparison (diagnosis type + primary equipment tag + mechanism class), era-aware:`);
  md.push('');
  md.push(`| Metric | Value |`);
  md.push(`|---|---|`);
  md.push(`| Re-tested cases with ≥${consistency.min_runs} proven runs (same era) | ${s.cases_audited} |`);
  md.push(`| Verdict-stable | ${s.consistent} consistent, ${s.weak} weak |`);
  md.push(`| Divergent (within era) | ${s.divergent} |`);
  md.push(`| Awaiting a second in-era execution | ${s.insufficient_runs} |`);
  md.push(`| Within-era verdict agreement | **${s.within_era_agreement}** |`);
  md.push('');
  md.push(`Cross-era pairs excluded from the headline: ${s.cross_era_divergent_pairs} (run-dir prefix < ${consistency.era_boundary} is the pre-discipline system revision — a documented version change, not run-to-run instability).`);
  md.push('');
  const perCase = Object.entries(consistency.cases).filter(([, v]) => v.n_runs_proven >= 2);
  if (perCase.length) {
    md.push(`| Scenario | Canonical era | Proven in era / total | Status | Types observed (in era) | Confidence range (in era) |`);
    md.push(`|---|---|---|---|---|---|`);
    for (const [id, v] of perCase) {
      const e = v.eras[v.canonical_era] || {};
      md.push(`| ${code(id)} | ${v.canonical_era} | ${e.n_runs_proven ?? 0} / ${v.n_runs_proven} | ${v.status} | ${(e.verdict_types || []).join(', ')} | ${e.confidence_range ? `${e.confidence_range[0]}–${e.confidence_range[1]}` : '—'} |`);
    }
    md.push('');
    md.push(`Status is decided **within the canonical era**; the "total" column includes the earlier-era executions, which are not counted toward consistency.`);
    md.push('');
  }
} else {
  md.push(`_consistency_audit.json not found — run ${code('node scripts/benchmark/consistency-audit.mjs')}._`);
  md.push('');
}
md.push(`### 7.3 Baseline suite determinism`);
md.push('');
if (suiteDet) {
  md.push(`The baseline suite was executed and its outputs compared file-by-file against the prior execution (timestamps excluded):`);
  md.push('');
  md.push(`| Metric | Value |`);
  md.push(`|---|---|`);
  md.push(`| Run files compared | ${suiteDet.compared} |`);
  md.push(`| Byte-identical (timestamp-stripped) | ${suiteDet.identical} |`);
  md.push(`| Differing | ${suiteDet.differing} |`);
  md.push(`| Verdict | **${suiteDet.verdict}** |`);
  md.push('');
} else {
  md.push(`_suite_determinism.json not found — run ${code('node scripts/benchmark/run-benchmark-pipeline.mjs --step 3')}._`);
  md.push('');
}

md.push(`## 8. Reproducibility and execution proofs`);
md.push('');
if (repro) {
  const c = repro.checks;
  md.push(`| Check | Result |`);
  md.push(`|---|---|`);
  md.push(`| Dataset fingerprint integrity | ${c.dataset_integrity?.verified}/${c.dataset_integrity?.entries} verified, ${c.dataset_integrity?.mismatched} mismatched |`);
  md.push(`| Scenario coverage | ${c.case_coverage?.prepared} prepared, ${c.case_coverage?.graded} graded, ${c.case_coverage?.missing?.length ?? 0} missing |`);
  md.push(`| Metric recomputation drift | ${c.metric_reproducibility?.drift_fields?.length ?? 0} drifting field(s) |`);
  md.push(`| Execution proofs | ${c.execution_proof?.pipeline_log_pass}/${c.execution_proof?.checked} pipeline-log PASS, ${c.execution_proof?.finalize_pass}/${c.execution_proof?.checked} finalize PASS |`);
  md.push(`| **Gate verdict** | **${repro.status}** |`);
  md.push('');
} else {
  md.push(`_repro_report.json not found — run ${code('node scripts/benchmark/verify-repro.mjs')}._`);
  md.push('');
}
md.push(`Every graded run carries ${code('.pipeline_events.jsonl')} plus a ${code('pipeline_finalize_report.json')} with ${code('overall = PASS')}. A run without that proof is never counted, never rated.`);
md.push('');

md.push(`## 9. Limitations and scope gaps`);
md.push('');
md.push(`1. **Sample size.** ${faultCases.length} fault scenarios is a small evaluation set; the Wilson interval on Top-1 spans ${num(metrics?.top1_ci95?.[0], 1)}–${num(metrics?.top1_ci95?.[1], 1)}%. Treat point estimates as indicative.`);
md.push(`2. **Indistinguishable-signature scenarios.** Where the recorded data cannot separate competing mechanisms, the pipeline returns ${code('COMPETING_SET')} rather than forcing a single root cause. These count as Top-1 misses but are protocol-conformant, and confidence is capped ≤65.`);
md.push(`3. **Baseline LLM arm.** Without a configured live endpoint the suite replays archived raw replies of the same deployment; each response is labelled ${code('recorded')}. One control (tep_d00) has no archived bare-LLM triple — a declared protocol gap, not a fabricated result.`);
md.push(`4. **In-era repetition.** Only the cases listed in §7.2 currently hold ≥${consistency?.min_runs ?? 2} proven executions in the current era; the rest carry an explicit re-run contract rather than an assumed stability claim.`);
md.push(`5. **No accuracy advantage claimed.** On documented public faults a single same-model LLM call matches or exceeds the pipeline on keyword-scored accuracy. The pipeline's contribution is process quality: auditability, execution proofs, ceiling compliance, and honest capped verdicts where the data cannot discriminate.`);
md.push('');

md.push(`## 10. Artifact index and provenance`);
md.push('');
md.push(`| Artifact | Content |`);
md.push(`|---|---|`);
md.push(`| ${code('results/benchmark/metrics.json')} | Aggregate metrics + per-case rows |`);
md.push(`| ${code('results/benchmark/gradings/<case>.json')} | Per-case truth-compared verdict + gate results |`);
md.push(`| ${code('results/benchmark/baselines.json')} | Scored PCA / FE-protocol / bare-LLM arms |`);
md.push(`| ${code('baselines/baseline-suite/runs/<case>.<arm>.json')} | Suite's own live executions (${suiteRunCount} files) |`);
md.push(`| ${code('results/benchmark/consistency_audit.json')} | Run-over-run consistency audit |`);
md.push(`| ${code('results/benchmark/retest_selection.json')} | Random re-test draw (seed + pool + case) |`);
md.push(`| ${code('results/benchmark/suite_determinism.json')} | Suite double-run byte diff |`);
md.push(`| ${code('results/benchmark/repro_report.json')} | Reproducibility gate verdict |`);
md.push(`| ${code('results/benchmark/journal.jsonl')} | Append-only scoring journal |`);
md.push(`| ${code('scripts/benchmark/cases/benchmark_cases.json')} | Scenario definitions + ground truth (grader-side only) |`);
md.push('');
md.push(`## Appendix A — Ground truth (grader-side)`);
md.push('');
md.push(`> ⚠️ Truth-bearing. Never expose to a diagnosing agent.`);
md.push('');
md.push(`| Scenario | Ground truth root cause | Keyword set | Expected verdict type |`);
md.push(`|---|---|---|---|`);
for (const c of tier.cases) {
  md.push(`| ${code(c.case_id)} | ${String(c.truth).replace(/\|/g, '\\|')} | ${(c.keywords || []).join(', ')} | ${(c.expect_type_set || []).join(' / ') || '—'} |`);
}
md.push('');
md.push(`---`);
md.push('');
md.push(`_Generated by ${code('scripts/benchmark/build-english-benchmark-report.mjs')} from artifacts on disk. Regenerate with ${code('node scripts/benchmark/run-benchmark-pipeline.mjs --step 4')}._`);

const mdText = md.join('\n') + '\n';

// ───────────────────────────── HTML ─────────────────────────────
const metricCards = metrics ? [
  ['Scenarios executed', `${metrics.executed}/${metrics.total_cases}`],
  ['Top-1 (faults)', `${metrics.top1}/${metrics.fault_cases} · ${pct(metrics.top1 / metrics.fault_cases)}`],
  ['Top-k (faults)', `${metrics.topk}/${metrics.fault_cases} · ${pct(metrics.topk / metrics.fault_cases)}`],
  ['CDR (Top-1 ∧ DETERMINED)', num(metrics.cdr, 2)],
  ['Calibrated', `${metrics.calibrated}/${metrics.fault_cases}`],
  ['Overconfident', String(metrics.overconfident)],
  ['Controls passed', `${metrics.control_pass}/${metrics.control_cases}`],
  ['False alarms', String(metrics.false_alarms)],
  ['Mean rubric', `${metrics.mean_rubric}/100`],
] : [];

const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IDD Diagnosis Benchmark Report</title>
<style>
 :root{--ink:#152029;--muted:#5b6b7a;--line:#dbe3ec;--bg:#eef2f7;--card:#fff;--accent:#1f5eff;--ok:#0f7b4f;--warn:#a8620a;--bad:#b3261e}
 *{box-sizing:border-box}
 body{font-family:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;color:var(--ink);background:var(--bg);margin:0;padding:40px 24px 80px;line-height:1.7;font-size:15px}
 .wrap{max-width:1120px;margin:0 auto}
 h1{font-size:27px;margin:0 0 6px;line-height:1.3}
 h2{font-size:19px;margin:36px 0 10px;padding-bottom:7px;border-bottom:2px solid var(--ink)}
 h3{font-size:16px;margin:24px 0 6px;color:#243244}
 .meta{color:var(--muted);font-size:13.5px;margin-bottom:18px}
 .banner{background:#fff4e5;border:1px solid #f0c07a;border-left:5px solid var(--warn);border-radius:6px;padding:12px 16px;font-size:13.5px;margin:16px 0 22px;color:#6b4207}
 .card{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:20px 24px;margin:14px 0}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
 .kpi{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:14px 16px}
 .kpi .lbl{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
 .kpi .val{font-size:20px;font-weight:650;margin-top:4px}
 table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;background:var(--card);border-radius:6px;overflow:hidden}
 th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
 th{background:#e7eef8;font-weight:650;font-size:12.5px}
 tbody tr:nth-child(even){background:#fafcfe}
 code{background:#f0f4f9;border:1px solid #e0e8f0;border-radius:4px;padding:1px 5px;font-size:12.5px;font-family:"Cascadia Mono",Consolas,monospace}
 pre{background:#f5f8fb;border:1px solid var(--line);border-radius:7px;padding:14px 16px;overflow:auto;font-size:12.5px;font-family:"Cascadia Mono",Consolas,monospace;line-height:1.6}
 .ok{color:var(--ok);font-weight:600}.warn{color:var(--warn);font-weight:600}.bad{color:var(--bad);font-weight:600}
 .scroll{overflow-x:auto}
 blockquote{border-left:4px solid var(--line);margin:12px 0;padding:2px 0 2px 14px;color:var(--muted);font-size:13.5px}
 ul{margin:8px 0 8px 20px;padding:0}
 li{margin:5px 0}
 .foot{color:var(--muted);font-size:12.5px;margin-top:30px;border-top:1px solid var(--line);padding-top:14px}
</style></head><body><div class="wrap">
<h1>Industrial Deep Diagnostic (IDD) — Diagnosis Benchmark Report</h1>
<div class="meta">Generated ${esc(generatedAt)} · generator <code>scripts/benchmark/build-english-benchmark-report.mjs</code> (derived from on-disk artifacts, zero hard-coded verdicts)<br>
System under test: IDD full pipeline <code>industrial-analysis-auto</code> Steps 2–9 · Latest canonical batch ${esc(latestRunPrefix)} · Baseline model: ${esc(MODEL)}</div>
<div class="banner"><b>TRUTH-CONTAINING ARTIFACT (grader-side).</b> Appendix A lists ground truth. Do not expose this file to a diagnosing agent — it would break the blind protocol.</div>

<h2>1. Scope and object of evaluation</h2>
<div class="card">The unit under evaluation is <b>one complete industrial diagnosis run</b>, not a per-sample label. Each scenario is executed end-to-end by the pipeline and scored by an independent grader reading the artifacts the sub-agents actually wrote.
<table><tr><th>Dimension</th><th>What is measured</th></tr>
<tr><td>Correctness</td><td>Top-1 / Top-k root-cause hit against documented ground truth</td></tr>
<tr><td>Calibration</td><td>Whether the declared three-state verdict (DETERMINED / COMPETING_SET / NEEDS_DATA) matches achievable discriminability</td></tr>
<tr><td>Control behaviour</td><td>False-alarm rate on anomaly-free control scenarios</td></tr>
<tr><td>Process quality</td><td>Deterministic rubric R1–R7 from artifacts, plus judge and audit gates</td></tr>
<tr><td>Repeatability</td><td>Verdict and mechanism agreement across independent re-executions</td></tr>
<tr><td>Reproducibility</td><td>Artifact-level execution proofs and dataset fingerprint stability</td></tr></table></div>

<h2>2. Benchmark protocol</h2>
<pre>S0 environment    fail-fast contract checks + truth-leakage sentinel
S1 prepare        deterministic statistics per scenario (same data + same code =&gt; byte-identical digest)
S2 brief          blind evidence pack (statistics + process description only; no truth)
S3 pipeline       REAL industrial-analysis-auto Steps 2-9 per scenario, sub-agents per their skill protocols
S4 grade          independent scorer reads agent-authored artifacts, compares against truth + deterministic rubric
S5 aggregate      metrics.json + reproducibility gate (must report REPRODUCIBLE)
S6 report         scoring report build</pre>
<p>The four-step agent-executable test pipeline is documented in <code>docs/benchmark/benchmark-pipeline-runbook.md</code>: (1) run the pipeline on the scenario data, (2) run the baseline/LLM replication suite on the same data, (3) draw a scenario <b>at random</b> and re-run it for consistency, (4) regenerate this report.</p>

<h2>3. Scenario suite</h2>
<p><b>${tier.cases.length} scenarios</b> — ${faultCases.length} fault cases + ${controlCases.length} anomaly-free controls. TEP faults carry per-fault literature baselines (FaultExplainer, arXiv:2412.14492 Table 1) and PCA detectability annotations (Chiang et al. 2001). Ground truth is isolated in <code>scripts/benchmark/cases/benchmark_cases.json</code>.</p>
<div class="scroll"><table><tr><th>#</th><th>Scenario</th><th>Dataset</th><th>Role</th><th>Expected verdict type</th></tr>
${tier.cases.map((c, i) => `<tr><td>${i + 1}</td><td><code>${esc(c.case_id)}</code></td><td>${esc(c.dataset)}</td><td>${c.control ? 'control' : 'fault'}</td><td>${esc((c.expect_type_set || []).join(' / ') || '—')}</td></tr>`).join('\n')}
</table></div>

<h2>4. Primary results</h2>
<div class="grid">${metricCards.map(([l, v]) => `<div class="kpi"><div class="lbl">${esc(l)}</div><div class="val">${esc(v)}</div></div>`).join('')}</div>
${metrics ? `<h3>4.1 By dataset</h3><div class="scroll"><table><tr><th>Dataset</th><th>Cases</th><th>Top-1</th><th>Top-k</th><th>Controls passed</th></tr>
${Object.entries(metrics.by_dataset || {}).map(([ds, v]) => `<tr><td>${esc(ds)}</td><td>${v.cases}</td><td>${v.top1}</td><td>${v.topk}</td><td>${v.control_pass}/${v.controls}</td></tr>`).join('')}
</table></div>` : ''}
<blockquote>Reported as measured. No metric floor is asserted — a threshold would create an incentive to dress up results to clear the gate.</blockquote>

<h2>5. Per-scenario results</h2>
<div class="scroll"><table><tr><th>Scenario</th><th>Role</th><th>IDD verdict</th><th>Bare-LLM strict</th><th>FE-style top-3</th><th>Suite PCA T² / SPE</th><th>Suite FE</th><th>Judge</th><th>Rubric</th><th>Finalized</th></tr>
${caseRows.map((r) => `<tr><td><code>${esc(r.case_id)}</code></td><td>${r.role}</td><td>${esc(r.idd)}</td><td>${esc(r.bare)}</td><td>${esc(r.feStyle)}</td><td>${esc(r.pcaT2)} / ${esc(r.pcaSPE)}</td><td>${esc(r.suiteFe)}</td><td>${esc(r.judge)}</td><td>${esc(r.rubric)}</td><td class="${r.finalized ? 'ok' : 'bad'}">${r.finalized ? 'PASS' : '—'}</td></tr>`).join('\n')}
</table></div>

<h2>6. Baseline arms</h2>
<div class="card">Three comparison arms run on the identical prepared data, model held constant (same deployment as the pipeline):
<table><tr><th>Arm</th><th>Method</th><th>Provenance</th></tr>
<tr><td>PCA</td><td>Reference training / 95% variance / T² + Q / 99th-percentile alarm / SPE top-3</td><td>Chiang et al. 2001; Qin 2012 — deterministic reimplementation</td></tr>
<tr><td>FE protocol</td><td>PCA(0.9) + T² (α=0.01 F-limit) + 6-consecutive trigger + per-sample top-6 T² contributions + EXPLAIN_ROOT</td><td>${esc(baselines?.fe_official_code?.source ?? 'li-group/FaultExplainer')}</td></tr>
<tr><td>Bare LLM</td><td>Single blind call per scenario; regimes: no candidates / with candidates / FE official prompt</td><td>${esc(MODEL)}</td></tr></table>
${baselines?.summary ? `<ul>
<li>TEP, FE-protocol regime with candidate list — FE-style top-3 hit: <b>${esc(baselines.summary.fe_protocol_replication_with_candidates?.fe_style_top3_hit ?? '—')}</b></li>
<li>TEP, strict single-verdict scoring: <b>${esc(baselines.summary.fe_protocol_replication_no_candidates_strict ?? '—')}</b></li>
<li>FE official prompts, strict: <b>${esc(baselines.summary.fe_official_prompts_strict ?? '—')}</b></li>
<li>Same-digest bare-LLM ablation: ${esc(baselines.summary.single_llm_same_digest_ablation ?? '—')}</li>
<li>Controls: ${esc(baselines.summary.controls?.bare_llm_normal_verdicts ?? '—')} normal verdicts, ${esc(baselines.summary.controls?.false_alarms ?? '—')} false alarms</li>
</ul>
<blockquote>${esc(baselines.summary.headline ?? '')}</blockquote>` : ''}
<p>Suite executions on disk: <b>${suiteRunCount}</b> run files across ${Object.keys(suiteRuns).length} scenarios.</p></div>

<h2>7. Consistency (repeatability)</h2>
<h3>7.1 Random re-test draw</h3>
${lastDraw ? `<div class="card">The re-tested scenario was selected by a uniform draw over the ${lastDraw.pool_size}-scenario pool using a recorded seed, so the choice cannot be hand-picked after seeing results.
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>Draw round</td><td>${lastDraw.round}</td></tr>
<tr><td>RNG</td><td>${esc(lastDraw.rng)}</td></tr>
<tr><td>Seed</td><td><code>${esc(String(lastDraw.seed))}</code></td></tr>
<tr><td>Uniform draw u</td><td>${lastDraw.uniform_draw}</td></tr>
<tr><td>Pool size / filter</td><td>${lastDraw.pool_size} / ${esc(lastDraw.pool_filter)}</td></tr>
<tr><td><b>Selected scenario</b></td><td><b><code>${esc(lastDraw.case_id)}</code></b> (${esc(lastDraw.dataset)}${lastDraw.control ? ', control' : ''})</td></tr></table>
<p>Replay the identical draw: <code>node scripts/benchmark/select-retest-case.mjs --seed ${esc(String(lastDraw.seed))}</code></p>
${retestAudit ? `<p><b>Outcome</b> — ${retestAudit.eras?.[retestAudit.canonical_era]?.n_runs_proven ?? 0} proven execution(s) in the current era (${retestAudit.n_runs_proven} on disk across all eras), canonical era ${esc(retestAudit.canonical_era)}, audit status <b>${esc(retestAudit.status)}</b>.</p>
${withinEraPairs.length ? `<div class="scroll"><table><tr><th>Against run</th><th>Verdict</th><th>Type (canonical = re-run)</th><th>Primary tag</th><th>Mechanism class</th><th>Confidence Δ</th></tr>
${withinEraPairs.map((p) => `<tr><td><code>${esc(p.run)}</code></td><td class="${p.verdict === 'CONSISTENT' ? 'ok' : p.verdict === 'DIVERGENT' ? 'bad' : 'warn'}">${esc(p.verdict)}</td><td>${esc(p.canonical_type)} = ${esc(p.run_type)}</td><td>${esc(p.canonical_primary_tag ?? '—')} = ${esc(p.run_primary_tag ?? '—')}</td><td>${esc(p.canonical_mechanism_class ?? '—')} = ${esc(p.run_mechanism_class ?? '—')}</td><td>${esc(p.confidence_delta ?? '—')}</td></tr>`).join('')}
</table></div>` : ''}
${retestAudit.status === 'INSUFFICIENT-RUNS' ? `<div class="banner"><b>Execution contract (outstanding).</b> This scenario has only ${retestAudit.eras?.[retestAudit.canonical_era]?.n_runs_proven ?? 0} proven execution(s) in the current era; the consistency claim needs a second one. Run the full <code>industrial-analysis-auto</code> pipeline (Steps 2–9) for <code>${esc(lastDraw.case_id)}</code> in a <b>fresh run directory</b>, then re-run <code>node scripts/benchmark/consistency-audit.mjs --case ${esc(lastDraw.case_id)}</code>. Never copy artifacts between run directories.</div>` : ''}` : ''}</div>` : `<p><i>No draw recorded yet — run <code>node scripts/benchmark/select-retest-case.mjs</code>.</i></p>`}

<h3>7.2 Consistency across all scenarios</h3>
${consistency ? `<div class="card">Structured mechanism-signature comparison (diagnosis type + primary equipment tag + mechanism class), era-aware.
<div class="grid">
<div class="kpi"><div class="lbl">Re-tested (≥${consistency.min_runs} in-era runs)</div><div class="val">${consistency.summary.cases_audited}</div></div>
<div class="kpi"><div class="lbl">Consistent / weak</div><div class="val">${consistency.summary.consistent} / ${consistency.summary.weak}</div></div>
<div class="kpi"><div class="lbl">Divergent (in era)</div><div class="val ${consistency.summary.divergent ? 'bad' : 'ok'}">${consistency.summary.divergent}</div></div>
<div class="kpi"><div class="lbl">Awaiting 2nd in-era run</div><div class="val warn">${consistency.summary.insufficient_runs}</div></div>
<div class="kpi"><div class="lbl">Within-era agreement</div><div class="val">${esc(consistency.summary.within_era_agreement)}</div></div>
</div>
<p>Cross-era pairs excluded from the headline: ${consistency.summary.cross_era_divergent_pairs} — run-dir prefix &lt; ${esc(consistency.era_boundary)} is the pre-discipline system revision (a documented version change, not run-to-run instability).</p>
${Object.entries(consistency.cases).filter(([, v]) => v.n_runs_proven >= 2).length ? `<div class="scroll"><table><tr><th>Scenario</th><th>Canonical era</th><th>Proven in era / total</th><th>Status</th><th>Types observed (in era)</th><th>Confidence range (in era)</th></tr>
${Object.entries(consistency.cases).filter(([, v]) => v.n_runs_proven >= 2).map(([id, v]) => { const e = v.eras[v.canonical_era] || {}; return `<tr><td><code>${esc(id)}</code></td><td>${esc(v.canonical_era)}</td><td>${e.n_runs_proven ?? 0} / ${v.n_runs_proven}</td><td class="${v.status === 'CONSISTENT' ? 'ok' : v.status === 'DIVERGENT' ? 'bad' : 'warn'}">${esc(v.status)}</td><td>${esc((e.verdict_types || []).join(', '))}</td><td>${e.confidence_range ? `${e.confidence_range[0]}–${e.confidence_range[1]}` : '—'}</td></tr>`; }).join('')}
</table></div><p>Status is decided <b>within the canonical era</b>; the "total" column includes earlier-era executions, which are not counted toward consistency.</p>` : ''}</div>` : `<p><i>consistency_audit.json not found.</i></p>`}

<h3>7.3 Baseline suite determinism</h3>
${suiteDet ? `<div class="card"><table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Run files compared</td><td>${suiteDet.compared}</td></tr>
<tr><td>Byte-identical (timestamp-stripped)</td><td class="ok">${suiteDet.identical}</td></tr>
<tr><td>Differing</td><td class="${suiteDet.differing ? 'bad' : 'ok'}">${suiteDet.differing}</td></tr>
<tr><td><b>Verdict</b></td><td><b>${esc(suiteDet.verdict)}</b></td></tr></table></div>` : `<p><i>suite_determinism.json not found.</i></p>`}

<h2>8. Reproducibility and execution proofs</h2>
${repro ? `<div class="card"><table><tr><th>Check</th><th>Result</th></tr>
<tr><td>Dataset fingerprint integrity</td><td>${repro.checks.dataset_integrity?.verified}/${repro.checks.dataset_integrity?.entries} verified, ${repro.checks.dataset_integrity?.mismatched} mismatched</td></tr>
<tr><td>Scenario coverage</td><td>${repro.checks.case_coverage?.prepared} prepared, ${repro.checks.case_coverage?.graded} graded, ${repro.checks.case_coverage?.missing?.length ?? 0} missing</td></tr>
<tr><td>Metric recomputation drift</td><td>${repro.checks.metric_reproducibility?.drift_fields?.length ?? 0} drifting field(s)</td></tr>
<tr><td>Execution proofs</td><td>${repro.checks.execution_proof?.pipeline_log_pass}/${repro.checks.execution_proof?.checked} pipeline-log PASS, ${repro.checks.execution_proof?.finalize_pass}/${repro.checks.execution_proof?.checked} finalize PASS</td></tr>
<tr><td><b>Gate verdict</b></td><td><b class="${repro.status === 'REPRODUCIBLE' ? 'ok' : 'bad'}">${esc(repro.status)}</b></td></tr></table>
<p>Every graded run carries <code>.pipeline_events.jsonl</code> plus a <code>pipeline_finalize_report.json</code> with <code>overall = PASS</code>. A run without that proof is never counted, never rated.</p></div>` : `<p><i>repro_report.json not found.</i></p>`}

<h2>9. Limitations and scope gaps</h2>
<div class="card"><ul>
<li><b>Sample size.</b> ${faultCases.length} fault scenarios is a small evaluation set; the Wilson interval on Top-1 spans ${num(metrics?.top1_ci95?.[0], 1)}–${num(metrics?.top1_ci95?.[1], 1)}%. Treat point estimates as indicative.</li>
<li><b>Indistinguishable-signature scenarios.</b> Where the recorded data cannot separate competing mechanisms the pipeline returns <code>COMPETING_SET</code> rather than forcing a root cause. These count as Top-1 misses but are protocol-conformant, with confidence capped ≤65.</li>
<li><b>Baseline LLM arm.</b> Without a configured live endpoint the suite replays archived raw replies of the same deployment, each labelled <code>recorded</code>. One control (tep_d00) has no archived bare-LLM triple — a declared protocol gap, not a fabricated result.</li>
<li><b>In-era repetition.</b> Only the cases in §7.2 hold ≥${consistency?.min_runs ?? 2} proven executions in the current era; the rest carry an explicit re-run contract rather than an assumed stability claim.</li>
<li><b>No accuracy advantage claimed.</b> On documented public faults a single same-model LLM call matches or exceeds the pipeline on keyword-scored accuracy. The pipeline's contribution is process quality: auditability, execution proofs, ceiling compliance, and honest capped verdicts.</li>
</ul></div>

<h2>10. Artifact index and provenance</h2>
<div class="card"><div class="scroll"><table><tr><th>Artifact</th><th>Content</th></tr>
<tr><td><code>results/benchmark/metrics.json</code></td><td>Aggregate metrics + per-case rows</td></tr>
<tr><td><code>results/benchmark/gradings/&lt;case&gt;.json</code></td><td>Per-case truth-compared verdict + gate results</td></tr>
<tr><td><code>results/benchmark/baselines.json</code></td><td>Scored PCA / FE-protocol / bare-LLM arms</td></tr>
<tr><td><code>baselines/baseline-suite/runs/&lt;case&gt;.&lt;arm&gt;.json</code></td><td>Suite's own live executions (${suiteRunCount} files)</td></tr>
<tr><td><code>results/benchmark/consistency_audit.json</code></td><td>Run-over-run consistency audit</td></tr>
<tr><td><code>results/benchmark/retest_selection.json</code></td><td>Random re-test draw (seed + pool + case)</td></tr>
<tr><td><code>results/benchmark/suite_determinism.json</code></td><td>Suite double-run byte diff</td></tr>
<tr><td><code>results/benchmark/repro_report.json</code></td><td>Reproducibility gate verdict</td></tr>
<tr><td><code>scripts/benchmark/cases/benchmark_cases.json</code></td><td>Scenario definitions + ground truth (grader-side only)</td></tr>
</table></div></div>

<h2>Appendix A — Ground truth (grader-side)</h2>
<div class="banner"><b>Truth-bearing.</b> Never expose to a diagnosing agent.</div>
<div class="scroll"><table><tr><th>Scenario</th><th>Ground truth root cause</th><th>Keyword set</th><th>Expected verdict type</th></tr>
${tier.cases.map((c) => `<tr><td><code>${esc(c.case_id)}</code></td><td>${esc(c.truth)}</td><td>${esc((c.keywords || []).join(', '))}</td><td>${esc((c.expect_type_set || []).join(' / ') || '—')}</td></tr>`).join('\n')}
</table></div>

<div class="foot">Generated by <code>scripts/benchmark/build-english-benchmark-report.mjs</code> from artifacts on disk · regenerate with <code>node scripts/benchmark/run-benchmark-pipeline.mjs --step 4</code></div>
</div></body></html>`;

fs.writeFileSync(path.join(RES, 'benchmark_report_en.md'), mdText);
fs.writeFileSync(path.join(RES, 'benchmark_report_en.html'), html);
console.log(`[report-en] results/benchmark/benchmark_report_en.{md,html}`);
console.log(`[report-en] ${tier.cases.length} scenarios · suite runs ${suiteRunCount} · consistency ${consistency ? consistency.summary.within_era_agreement : 'n/a'} · retest ${retestCase ?? 'n/a'} · repro ${repro?.status ?? 'n/a'}`);
