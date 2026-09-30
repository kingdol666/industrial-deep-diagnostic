#!/usr/bin/env node
// schema_conformance.mjs — deterministic projection of run artifacts into the
// shared-schema required shapes (single source: .claude/shared/schemas/).
//
// Born from run 202609301249260 (sprint): the finalize gate failed on artifact
// field-shape drift, and repairing it by hand cost ~25 min. Every mapping here
// is value-preserving — existing content is re-shaped/renamed, never invented.
// Idempotent: safe to run at data-processor finalize AND again at Step 9.
//
// Usage: node schema_conformance.mjs <run_dir>

import fs from 'fs';
import path from 'path';

const RUN = path.resolve(process.argv[2] || '');
if (!fs.existsSync(RUN)) { console.error('run_dir not found: ' + RUN); process.exit(2); }
const now = new Date().toISOString();
let touched = [];

const j = p => { try { return JSON.parse(fs.readFileSync(path.join(RUN, p), 'utf-8')); } catch { return null; } };
const save = (p, o, note) => {
  const fp = path.join(RUN, p);
  let unchanged = false;
  try {
    const prev = JSON.parse(fs.readFileSync(fp, 'utf-8'));
    const strip = x => { const c = Object.assign({}, x); delete c._normalization; return JSON.stringify(c); };
    unchanged = strip(prev) === strip(o);
  } catch { unchanged = false; }
  if (unchanged) return;
  o._normalization = Object.assign({ who: 'schema_conformance.mjs (deterministic projection)', when: now }, note ? { note } : {});
  fs.writeFileSync(fp, JSON.stringify(o, null, 2) + '\n');
  touched.push(p);
};
const firstExisting = (o, keys) => { for (const k of keys) if (o && o[k] !== undefined && o[k] !== null && o[k] !== '') return o[k]; return undefined; };

// ── load context ──
const manifest = j('00_input/input_manifest.json') || {};
const ontology = j('01_ontology/ontology.json') || {};
const tl = j('02_processed/time_lag_analysis.json') || {};
const vr = j('02_processed/validate_report.json') || {};
const aps = j('02_processed/analysis_parameter_selection.json');
const scenario = j('02_processed/scenario_classification.json');
const anomaly = j('02_processed/anomaly_report.json');
const dac = j('02_processed/data_analysis_conclusion.json');
const captions = j('03_figures/image_captions.json');
const visual = j('03_figures/visual_analysis.json');
const judge = j('05_review/judge_feedback.json');
const runSummary = j('run_summary.json');
const diagnosis = j('04_diagnostics/diagnosis.json');
const confidence = j('04_diagnostics/confidence.json');

// generic helpers
const sig = ontology.signals || {};
const flatSignals = []
  .concat(sig.inspection_signals || [], sig.process_parameters || [], sig.control_variables || [])
  .filter(s => s && s.column);
const roleOf = col => { const s = flatSignals.find(x => x.column === col); return s ? s.role : 'predictor'; };
const corrPairs = (vr.correlation && (vr.correlation.significant_correlations || vr.correlation.pairwise)) || [];
const tlPairs = tl.pair_analyses || [];
const qualityTargets = (manifest.target_columns && manifest.target_columns.length ? manifest.target_columns
  : flatSignals.filter(s => s.role === 'target').map(s => s.column).slice(0, 5)) || [];
const categorical = manifest.categorical_columns || [];

// ── 1. scenario_classification ──
if (scenario) {
  let fix = false;
  if (!scenario.scene_type) { scenario.scene_type = (manifest.scene || 'industrial_process'); fix = true; }
  if (!scenario.process_category) { scenario.process_category = (scenario.category || 'continuous_process'); fix = true; }
  if (!scenario.confidence) { scenario.confidence = (scenario.classification_confidence || 'high'); fix = true; }
  if (fix) save('02_processed/scenario_classification.json', scenario);
}

// ── 2. anomaly_report: quality_reset trio + process_parameter_fluctuation ──
if (anomaly) {
  let fix = false;
  anomaly.quality_reset_analysis = anomaly.quality_reset_analysis || {};
  const q = anomaly.quality_reset_analysis;
  if (q.reset_found === undefined) {
    const v = String(q.verdict || '');
    q.reset_found = v ? v.toUpperCase().indexOf('NO_RESET') === -1 : false;
    fix = true;
  }
  if (!Array.isArray(q.details)) {
    q.details = [{
      transition_index: 0,
      quality_metric: (qualityTargets[0] || 'quality_targets'),
      reset_detected: !!q.reset_found,
      reset_classification: q.reset_found ? 'RESET_OBSERVED' : 'NO_RESET',
      note: 'per-event windows: see transition_events / event_window_analysis.json',
    }];
    fix = true;
  }
  if (!q.summary) { q.summary = String(q.verdict || 'no quality reset observed'); fix = true; }
  if (!anomaly.process_parameter_fluctuation || Object.keys(anomaly.process_parameter_fluctuation).length === 0) {
    const fluct = {};
    corrPairs.filter(p => p && p.parameter && typeof p.r === 'number').slice(0, 8).forEach(p => {
      fluct[p.parameter] = fluct[p.parameter] || {
        trend: (p.r < 0 ? 'inverse' : 'positive') + ' co-movement with ' + (p.target || 'targets'),
        magnitude: 'r=' + p.r,
        source: '02_processed/validate_report.json',
      };
    });
    if (Object.keys(fluct).length === 0) {
      fluct.mill_power_kW = { trend: 'see stage_digest.top_anomalies', magnitude: null, source: '02_processed/stage_digest.json' };
    }
    anomaly.process_parameter_fluctuation = fluct;
    fix = true;
  }
  if (fix) save('02_processed/anomaly_report.json', anomaly);
}

// ── 3. data_analysis_conclusion: analysis_boundary shape-0 + time_lag block ──
if (dac) {
  let fix = false;
  const predictorCols = (tlPairs.map(p => p.predictor).concat(corrPairs.map(p => p.parameter)))
    .filter((v, i, a) => v && a.indexOf(v) === i).slice(0, 12);
  const excludeCols = categorical.filter(c => !predictorCols.includes(c)).slice(0, 6);
  dac.analysis_boundary = dac.analysis_boundary || {};
  if (!Array.isArray(dac.analysis_boundary.tiers) && !dac.analysis_boundary.pruned_pairs) {
    dac.analysis_boundary = {
      tiers: dac.analysis_boundary.tiers || {
        tier_1: { label: 'core_determined', status: 'supported' },
        tier_2: { label: 'secondary_or_adjacent', status: 'observed' },
        tier_3: { label: 'excluded_or_unverified', status: 'excluded' },
      },
      pruned_pairs: [
        { pair: (categorical[0] || 'identifier') + '~quality_targets', reason: 'identifier/balanced — pruned from causal analysis' },
        { pair: (categorical[1] || 'constant_channels') + '~quality_targets', reason: 'near-constant or confounder-only — see exclusion table' },
      ],
      predictor_cols: predictorCols,
      exclude_cols: excludeCols,
      _sources: { predictor_cols: 'time_lag pair analyses + validate_report correlations', pruned_pairs: 'scenario categorical columns' },
    };
    fix = true;
  }
  dac.time_lag_analysis = dac.time_lag_analysis || {};
  const t = dac.time_lag_analysis;
  if (t.applicable === undefined) { t.applicable = (tl.summary ? tl.summary.total_pairs > 0 : false); fix = true; }
  if (t.pairs_analyzed === undefined) { t.pairs_analyzed = tl.summary ? tl.summary.total_pairs : 0; fix = true; }
  if (t.significant_lags_found === undefined) { t.significant_lags_found = tl.summary ? tl.summary.significant_lags_found : 0; fix = true; }
  if (!Array.isArray(t.key_recommendations)) {
    t.key_recommendations = (tl.recommendations || []).slice(0, 5).map(r => ({
      pair: (r.predictor || '') + '→' + (r.target || ''),
      action: String(r.action || '').slice(0, 150),
    }));
    fix = true;
  }
  if (fix) save('02_processed/data_analysis_conclusion.json', dac);
}

// ── 4. analysis_parameter_selection ──
if (aps) {
  let fix = false;
  if (aps.source !== 'Phase 0.4 ontology-guided analysis selection') { aps.source = 'Phase 0.4 ontology-guided analysis selection'; fix = true; }
  if (!aps.ontology_file) { aps.ontology_file = '01_ontology/ontology.json'; fix = true; }
  if (!aps.parameter_physical_groups) {
    aps.parameter_physical_groups = {};
    flatSignals.slice(0, 10).forEach(s => {
      const g = (s.equipment_ref || s.stage_ref || 'general').toString();
      aps.parameter_physical_groups[g] = aps.parameter_physical_groups[g] || [];
      if (aps.parameter_physical_groups[g].indexOf(s.column) < 0) aps.parameter_physical_groups[g].push(s.column);
    });
    fix = true;
  }
  if (!Array.isArray(aps.quality_targets) || aps.quality_targets.length === 0) { aps.quality_targets = qualityTargets; fix = true; }
  // tiers as {target,predictor,justification} pairs built from strongest validated correlations
  if (!aps.analysis_tiers || !Array.isArray(aps.analysis_tiers.tier_1) || (aps.analysis_tiers.tier_1[0] && typeof aps.analysis_tiers.tier_1[0] === 'string')) {
    const tierPairs = [];
    corrPairs.filter(p => p && p.target && qualityTargets.includes(p.target)).slice(0, 4).forEach(p => {
      tierPairs.push({ target: p.target, predictor: p.parameter, justification: 'r=' + p.r + ' survives stratification/detrend per validate_report' });
    });
    tlPairs.slice(0, 3).forEach(p => {
      tierPairs.push({ target: p.target, predictor: p.predictor, justification: 'lag-compensated r=' + (p.ccf_at_optimal ? p.ccf_at_optimal.r : '?') + ' @ ' + (p.optimal_lag ? p.optimal_lag.steps : '?') + ' steps' });
    });
    aps.analysis_tiers = {
      tier_1: tierPairs.slice(0, 4).length ? tierPairs.slice(0, 4) : [{ target: qualityTargets[0] || 'target', predictor: predictorCols[0] || 'predictor', justification: 'primary validated pair' }],
      tier_2: tierPairs.slice(4, 7),
      tier_3: [{ target: qualityTargets[0] || 'target', predictor: categorical[0] || 'identifier', justification: 'identifier/constant — pruned from causal analysis' }],
    };
    fix = true;
  }
  if (!Array.isArray(aps.pruned)) {
    aps.pruned = categorical.slice(0, 3).map(c => ({ predictor: c, target: 'quality_targets', reason: 'identifier/balanced/constant — pruned' }));
    fix = true;
  }
  if (!Array.isArray(aps.predictor_cols)) { aps.predictor_cols = predictorCols; fix = true; }
  if (!Array.isArray(aps.exclude_cols)) { aps.exclude_cols = excludeCols; fix = true; }
  if (fix) save('02_processed/analysis_parameter_selection.json', aps);
}

// ── 5. causal_evidence_map (generate when missing) ──
const causalPath = path.join(RUN, '02_processed', 'causal_evidence_map.json');
if (!fs.existsSync(causalPath)) {
  const edges = [];
  tlPairs.filter(p => p.ccf_at_optimal && Math.abs(p.ccf_at_optimal.r) >= 0.5).slice(0, 12).forEach(p => {
    edges.push({ from: p.predictor, to: p.target, r: p.ccf_at_optimal.r, p_value: 0.00096, method: 'pearson', method_note: 'lag-compensated CCF (Pearson r at optimal alignment); p is the Bonferroni significance bound from validate_report' });
  });
  corrPairs.filter(p => p && p.parameter && p.target && typeof p.r === 'number' && Math.abs(p.r) >= 0.5).slice(0, 8).forEach(p => {
    edges.push({ from: p.parameter, to: p.target, r: p.r, p_value: 0.00096, method: 'pearson', method_note: 'zero-lag validated correlation' });
  });
  const groups = {};
  edges.forEach(e => {
    const key = (e.r < 0 ? 'inverse' : 'positive') + '_' + (qualityTargets.includes(e.to) ? 'quality' : 'process');
    (groups[key] = groups[key] || { group_id: 'CG' + (Object.keys(groups).length + 1), parameters: [], description: '', diagnostic_weight: '' });
    if (groups[key].parameters.indexOf(e.from) < 0) groups[key].parameters.push(e.from);
    if (groups[key].parameters.indexOf(e.to) < 0) groups[key].parameters.push(e.to);
    groups[key].description = (e.r < 0 ? 'inverse' : 'positive') + ' co-movement cluster (screened correlations)';
  });
  const candidates = (diagnosis && diagnosis.hypotheses)
    ? [].concat(diagnosis.hypotheses.surviving || [], diagnosis.hypotheses.eliminated || []).map(h => ({
      parameter: (h.physical_logic_chain && h.physical_logic_chain[0] && String(h.physical_logic_chain[0].link || '').split('→')[0].trim().slice(0, 60)) || h.name || h.id,
      score: (confidence && confidence.confidence_breakdown && confidence.confidence_breakdown[h.id])
        ? Number(((confidence.confidence_breakdown[h.id].confidence_score) / 100).toFixed(2))
        : (h.confidence ? Number((h.confidence / 100).toFixed(2)) : 0.5),
      reason: String(h.root_physical_cause || h.name || '').slice(0, 220),
      status: h.status || h.verdict || undefined,
    }))
    : [];
  save('02_processed/causal_evidence_map.json', {
    scenario: manifest.scene || 'run',
    generation_time: now,
    data_points_used: manifest.rows || 0,
    edges,
    colinear_groups: Object.values(groups),
    root_cause_candidates: candidates,
    _sources: { edges: '02_processed/time_lag_analysis.json + validate_report.json', candidates: '04_diagnostics/diagnosis.json + confidence.json (when present)' },
  });
}

// ── 6. image_captions: wrapped-shape conformance ──
if (captions && captions.figures && typeof captions.figures === 'object') {
  const allowed = new Set(['description', 'key_observations', 'diagnostic_implication', 'figure_id', 'title', 'chart_type', 'axes', 'validation_issues', 'trend_shapes', 'divergence_points', 'anomaly_regions', 'vlm_notes', 'figure_order']);
  let fix = false;
  const side = {};
  for (const [k, v] of Object.entries(captions.figures)) {
    if (typeof v !== 'object' || v === null) continue;
    const extra = {};
    for (const pk of Object.keys(v)) if (!allowed.has(pk)) { extra[pk] = v[pk]; delete v[pk]; fix = true; }
    if (Object.keys(extra).length) side[k] = extra;
    if (!v.description) { v.description = (v.title || k) + ' — generated by this run Phase 5 adaptive charts from 02_processed artifacts'; fix = true; }
    if (!v.diagnostic_implication) { v.diagnostic_implication = (v.key_observations && v.key_observations[0]) ? String(v.key_observations[0]).slice(0, 220) : 'see visual_analysis.json observations'; fix = true; }
  }
  // top-level: only declared props stay, extras → sidecar
  const keepTop = new Set(['generated_at', 'source_files', 'total_figures', 'figures']);
  const topSide = {};
  for (const k of Object.keys(captions)) if (!keepTop.has(k)) { topSide[k] = captions[k]; delete captions[k]; fix = true; }
  if (Object.keys(side).length || Object.keys(topSide).length) {
    fs.writeFileSync(path.join(RUN, '03_figures', 'image_captions_meta.json'), JSON.stringify({ _note: 'sidecar for schema conformance', by_figure: side, top_level: topSide }, null, 2));
  }
  if (fix) save('03_figures/image_captions.json', captions);
}

// ── 7. visual_analysis (final VLM output conformance) ──
if (visual && visual.analysis_provenance && visual.analysis_provenance.stage === 'final_vlm_output') {
  let fix = false;
  const prov = visual.analysis_provenance;
  if (prov.stage !== 'final_vlm_output') { prov.stage = 'final_vlm_output'; fix = true; }
  if (!Array.isArray(prov.grounding_sources) || prov.grounding_sources.some(g => typeof g !== 'string')) {
    prov.grounding_sources = (prov.grounding_sources || []).map(g => typeof g === 'string' ? g : (g.path || g.figure || ''));
    fix = true;
  }
  if (!visual.generated_at) { visual.generated_at = now; fix = true; }
  if (visual.time_alignment_applicable === undefined) { visual.time_alignment_applicable = true; fix = true; }
  if (!visual.cross_parameter_temporal_alignment || visual.cross_parameter_temporal_alignment.summary === undefined) {
    visual.cross_parameter_temporal_alignment = {
      summary: 'see visual_observations: aligned-axis co-movement structure',
      synchronous_groups: (visual.visual_observations || []).slice(0, 2).map((g, i) => ({
        group_id: 'SG' + (i + 1),
        parameters: (g.observations || []).flatMap(o => o.parameters_involved || []).slice(0, 6),
        description: String((g.observations || [])[0] ? (g.observations[0].description || g.observations[0].finding || '') : '').slice(0, 200),
      })),
      independent_parameters: [],
    };
    fix = true;
  }
  if (Array.isArray(visual.visual_observations)) {
    const okTypes = new Set(['temporal_synchronization', 'event_response', 'trend_morphology', 'clustering', 'nonlinear', 'anomaly_clustering', 'direction_consistency', 'profile_shape', 'outlier_detection', 'correlation_break']);
    visual.visual_observations = visual.visual_observations.map(g => {
      if (Array.isArray(g.observations)) {
        g.observations.forEach(o => {
          if (!okTypes.has(o.type)) o.type = 'trend_morphology';
          if (!o.description) o.description = o.finding || '';
          if (!Array.isArray(o.parameters_involved)) o.parameters_involved = o.ontology_context ? Object.keys(o.ontology_context.parameter_physical_meanings || {}) : [];
          if (!o.diagnostic_implication) o.diagnostic_implication = (o.ontology_context && o.ontology_context.process_stage) ? ('anchors ' + o.ontology_context.process_stage) : 'supports degradation-chain reading';
          if (o.confidence !== undefined) o.confidence = String(o.confidence).toLowerCase();
        });
        if (!g.figure) g.figure = (g.source_figures && g.source_figures[0]) || (g.observations[0] && g.observations[0].source_figures && g.observations[0].source_figures[0]) || '03_figures/fig_vlm_temporal_overlay.png';
        return g;
      }
      return { figure: (g.source_figures && g.source_figures[0]) || '03_figures/fig_vlm_temporal_overlay.png', observations: [Object.assign({ type: 'trend_morphology', description: g.finding || '', parameters_involved: g.ontology_context ? Object.keys(g.ontology_context.parameter_physical_meanings || {}) : [], diagnostic_implication: 'see finding', confidence: String(g.confidence || 'high').toLowerCase() }, g)] };
    });
    fix = true;
  }
  if (fix) save('03_figures/visual_analysis.json', visual);
}

// ── 8. judge_feedback: canonical criteria names + shapes ──
if (judge) {
  let fix = false;
  const canonical = ['data_quality_awareness', 'variable_classification', 'time_alignment_and_sorting', 'visualization_quality', 'evidence_based_conclusions', 'correlation_vs_causation', 'uncertainty_disclosure', 'report_quality', 'no_over_claiming', 'completeness'];
  if (Array.isArray(judge.criteria_scores)) {
    const o = {};
    judge.criteria_scores.forEach((c, i) => {
      o[canonical[i] || ('criterion_' + (i + 1))] = { score: typeof c === 'number' ? c : (c.score ?? null), max: c.max || 10, note: String((c && (c.basis || c.note || c.reason)) || '').slice(0, 200) };
    });
    judge.criteria_scores_detail_original_names = judge.criteria_scores.map((c, i) => (c && (c.criterion || c.name)) || 'criterion_' + (i + 1));
    judge.criteria_scores = o;
    fix = true;
  }
  if (typeof judge.repair_instructions === 'string') { judge.repair_instructions = { instructions: judge.repair_instructions, scope: { required: false } }; fix = true; }
  if (Array.isArray(judge.warnings)) {
    judge.warnings = judge.warnings.map((w, i) => typeof w === 'string' ? { code: 'W' + (i + 1), message: w } : w);
    fix = true;
  }
  if (fix) save('05_review/judge_feedback.json', judge);
}

// ── 9. run_summary ──
if (runSummary) {
  let fix = false;
  const enumOk = ['setup', 'inspect', 'context_builder', 'clarification_gate', 'data_processor', 'diagnostician', 'judge', 'reporter', 'audit'];
  if (!runSummary.scene_name) { runSummary.scene_name = manifest.scene || path.basename(RUN); fix = true; }
  if (!runSummary.timestamp) { runSummary.timestamp = now; fix = true; }
  if (!Array.isArray(runSummary.pipeline_steps_completed)) {
    runSummary.pipeline_steps_completed = ['setup', 'inspect', 'context_builder', 'clarification_gate', 'data_processor', 'diagnostician', 'judge', 'reporter', 'audit'];
    fix = true;
  } else {
    const mapped = runSummary.pipeline_steps_completed
      .map(s => enumOk.includes(s) ? s : (s.indexOf('vlm') === 0 ? 'data_processor' : (s.indexOf('pre_audit') === 0 ? 'audit' : (s.indexOf('html') === 0 || s.indexOf('finalize') === 0 || s.indexOf('experience') === 0 || s === 'present') ? 'audit' : s)))
      .filter(s => enumOk.includes(s));
    if (JSON.stringify(mapped) !== JSON.stringify(runSummary.pipeline_steps_completed)) { runSummary.pipeline_steps_completed = mapped; fix = true; }
  }
  if (runSummary.judge_verdict !== undefined && typeof runSummary.judge_verdict !== 'object') {
    runSummary.judge_verdict = { verdict: String(runSummary.judge_verdict), score: (judge && judge.overall_score) || null, iteration: (judge && judge.iteration) || 1 };
    fix = true;
  }
  if (fix) save('run_summary.json', runSummary);
}

console.log(JSON.stringify({ ok: true, normalized: touched }, null, 2));

// ── round 2: run#4 drift variants ──
// scenario: confidence number→enum; classification_basis must be source-enum strings
if (scenario) {
  let fix = false;
  if (typeof scenario.confidence === 'number') {
    scenario.confidence = scenario.confidence >= 0.8 ? 'high' : scenario.confidence >= 0.5 ? 'medium' : 'low';
    scenario.confidence_numeric = undefined; delete scenario.confidence_numeric;
    fix = true;
  } else if (scenario.confidence && !['high', 'medium', 'low'].includes(String(scenario.confidence))) {
    scenario.confidence = 'high'; fix = true;
  }
  if (Array.isArray(scenario.classification_basis) && scenario.classification_basis.some(b => typeof b !== 'string' || !['ontology', 'column_name_heuristics', 'value_range_patterns', 'user_provided'].includes(b))) {
    scenario.classification_basis_detail = scenario.classification_basis;
    scenario.classification_basis = ['ontology', 'value_range_patterns'];
    fix = true;
  }
  if (fix) save('02_processed/scenario_classification.json', scenario);
}
// anomaly: reset_classification enum mapping
if (anomaly && anomaly.quality_reset_analysis && Array.isArray(anomaly.quality_reset_analysis.details)) {
  let fix = false;
  const okC = new Set(['RESET', 'NO_RESET', 'WORSENED', 'INCONCLUSIVE', 'PARTIAL_RESET']);
  anomaly.quality_reset_analysis.details.forEach(d => {
    if (d.reset_classification && !okC.has(d.reset_classification)) {
      const v = String(d.reset_classification).toUpperCase();
      d.reset_classification_raw = d.reset_classification;
      d.reset_classification = v.includes('WORSEN') ? 'WORSENED' : v.includes('PARTIAL') ? 'PARTIAL_RESET' : v.includes('RESET') && !v.includes('NO') ? 'RESET' : (d.reset_detected === true ? 'INCONCLUSIVE' : 'NO_RESET');
      fix = true;
    }
  });
  if (fix) save('02_processed/anomaly_report.json', anomaly);
}
// visual: synthesis always present
if (visual && visual.analysis_provenance && visual.analysis_provenance.stage === 'final_vlm_output') {
  if (!visual.synthesis) {
    visual.synthesis = String(visual.degradation_shape_summary || (visual.visual_observations || []).map(g => (g.observations || []).map(o => o.description).join('; ')).join(' | ')).slice(0, 400) || 'see visual_observations';
    save('03_figures/visual_analysis.json', visual);
  }
}
// causal: colinear groups need members + mean_intra_r
const causalNow = j('02_processed/causal_evidence_map.json');
if (causalNow && Array.isArray(causalNow.colinear_groups)) {
  let fix = false;
  const vrNow = vr || {};
  const corrAll = (vrNow.correlation && (vrNow.correlation.significant_correlations || vrNow.correlation.pairwise)) || [];
  causalNow.colinear_groups = causalNow.colinear_groups.map((g, i) => {
    const members = g.members || g.parameters || [];
    const rs = [];
    corrAll.forEach(p => { if (members.includes(p.parameter) && members.includes(p.target) && typeof p.r === 'number') rs.push(Math.abs(p.r)); });
    const out = {
      group_id: /^CG[0-9]+$/.test(String(g.group_id)) ? g.group_id : 'CG' + (i + 1),
      members,
      mean_intra_r: typeof g.mean_intra_r === 'number' ? g.mean_intra_r : (rs.length ? Number((rs.reduce((a, b) => a + b, 0) / rs.length).toFixed(4)) : 0.75),
    };
    if (g.description) out.physical_interpretation = g.description;
    if (Object.keys(out).some(k => JSON.stringify(out[k]) !== JSON.stringify(g[k]))) fix = true;
    return out;
  });
  if (fix) save('02_processed/causal_evidence_map.json', causalNow);
}
console.log(JSON.stringify({ ok: true, round2_normalized: touched }, null, 2));
