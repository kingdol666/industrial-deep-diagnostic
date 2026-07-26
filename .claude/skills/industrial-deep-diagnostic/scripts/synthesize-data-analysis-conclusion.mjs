#!/usr/bin/env node
// synthesize-data-analysis-conclusion.mjs — V2-aware deterministic handoff generator.
//
// V2 BEHAVIOR (critical): MERGES into existing V2 handoff instead of overwriting.
//   - If data_analysis_conclusion.json already has schema_version "2.0":
//       preserve LLM-written judgment fields (expert_gap_analysis, param_ambiguity,
//       diagnostician_handoff, visual_evidence_summary), fill/refresh MECHANICAL
//       fields deterministically (validated_correlations, adaptive_decision_audit,
//       anomaly_highlights, process_health, dual_drive_linkages, data_cleaning_provenance).
//   - If absent or V1: generate full V2 from artifacts.
//
// This fixes the V2 pipeline-breaking bug where the old V1 synthesize OVERWROTE
// data-processor's V2 handoff with V1 structure, breaking diagnostician's read of
// validated_correlations.pairs[].
//
// Usage:
//   node synthesize-data-analysis-conclusion.mjs <run_dir>

import fs from 'fs';
import { join, basename } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
if (!runDir) {
  console.error('Usage: node synthesize-data-analysis-conclusion.mjs <run_dir>');
  process.exit(1);
}

function readJson(rel, fallback = null) {
  try { return JSON.parse(fs.readFileSync(join(runDir, rel), 'utf8')); }
  catch (_) { return fallback; }
}
function writeJson(rel, data) {
  fs.writeFileSync(join(runDir, rel), `${JSON.stringify(data, null, 2)}\n`);
}
function exists(rel) { return fs.existsSync(join(runDir, rel)); }

// ── Load source artifacts ──
const runManifest = readJson('run_manifest.json', {});
const inputManifest = readJson('00_input/input_manifest.json', {});
const ontology = readJson('01_ontology/ontology.json', {});
const featureSummary = readJson('02_processed/feature_summary.json', {});
const validateReport = readJson('02_processed/validate_report.json', {});
const anomalyReport = readJson('02_processed/anomaly_report.json', {});
const dataQualityReport = readJson('02_processed/data_quality_report.json', {});
const timeLagAnalysis = readJson('02_processed/time_lag_analysis.json', null);
const physicsCheck = readJson('02_processed/physics_check.json', null);
const visualAnalysis = readJson('03_figures/visual_analysis.json', null);
const clarificationNeeded = readJson('01_ontology/clarification_needed.json', null);
const existing = readJson('02_processed/data_analysis_conclusion.json', null);

// ── V2 merge: preserve LLM judgment fields if existing is V2 ──
const isExistingV2 = existing && existing.schema_version === '2.0';
const preserved = isExistingV2 ? {
  expert_gap_analysis: existing.expert_gap_analysis || { custom_scripts_run: [], custom_findings: [], remaining_gaps: [], recommended_extra_data: [] },
  param_ambiguity: existing.param_ambiguity || { ambiguous_params: [], resolved_count: 0, unresolved_count: 0 },
  diagnostician_handoff: existing.diagnostician_handoff || { priority_hypothesis_inputs: [], evidence_gaps: [] },
  visual_evidence_summary: existing.visual_evidence_summary || null,  // prefer LLM version; fall back to mechanical below
} : {};

// ── Helper: flatten feature_summary.correlations[target][predictor] → pairs ──
// Recursively strip null/undefined so schema-typed fields aren't violated.
function stripNulls(obj) {
  if (obj === null || obj === undefined) return undefined;
  if (Array.isArray(obj)) return obj.map(stripNulls).filter(v => v !== undefined);
  if (typeof obj === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      const cleaned = stripNulls(v);
      if (cleaned !== undefined && cleaned !== null) out[k] = cleaned;
    }
    return out;
  }
  return obj;
}

function extractCorrelations(fs_, fallbackN) {
  const pairs = [];
  const corrs = fs_.correlations || {};
  const detrended = fs_.detrended_correlations || {};
  const spearman = fs_.spearman_correlations || {};
  for (const [target, preds] of Object.entries(corrs)) {
    if (!preds || typeof preds !== 'object') continue;
    for (const [predictor, vals] of Object.entries(preds)) {
      if (vals == null) continue;  // skip null/undefined; numbers AND objects are valid
      const r = typeof vals === 'number' ? vals : (vals.pearson_r ?? vals.r ?? vals.value);
      if (r == null || Math.abs(r) < 0.3) continue;  // V2 threshold: |r| >= 0.3
      const detrended_r = detrended?.[target]?.[predictor];
      const spearman_rho = spearman?.[target]?.[predictor];
      pairs.push(stripNulls({
        predictor, target,
        pearson_r: typeof r === 'number' ? r : null,
        pearson_p: typeof vals === 'object' ? (vals.p_value ?? vals.p) : null,
        spearman_rho: typeof spearman_rho === 'number' ? spearman_rho : null,
        detrended_r: typeof detrended_r === 'number' ? detrended_r : null,
        mi_score: null,  // populated if feature_summary has MI
        sample_n: (typeof vals === 'object' ? (vals.n ?? vals.sample_size) : null) ?? fallbackN,
      }));
    }
  }
  return pairs;
}

// ── Helper: look up validation status for a predictor/target pair ──
function lookupValidation(predictor, target, vr) {
  const findings = [];
  let simpson_safe = true, trend_confounded = false, outlier_driven = false;
  let leave_one_out_safe = true, leave_one_out_delta_r = 0;
  const time_sorted = vr.sorting_validation?.time_sorted !== false;
  // regime_filtered: assume true if production_regime_filter exists (data-processor enforces)
  const regime_filtered = exists('02_processed/production_regime_filter.json');

  // Simpson: scan simpson_paradox list for this pair
  for (const sp of (vr.simpson_paradox || [])) {
    const involved = JSON.stringify(sp).toLowerCase();
    if (involved.includes(predictor.toLowerCase()) && involved.includes(target.toLowerCase())) {
      simpson_safe = false;
      findings.push(`Simpson reversal: ${sp.summary || sp.description || JSON.stringify(sp).slice(0, 120)}`);
    }
  }
  // Trend confounding
  for (const tc of (vr.time_trend_confounding || [])) {
    const involved = JSON.stringify(tc).toLowerCase();
    if (involved.includes(predictor.toLowerCase()) && involved.includes(target.toLowerCase())) {
      const attenuation = tc.attenuation_pct ?? tc.attenuation;
      if (attenuation > 50) { trend_confounded = true; findings.push(`Trend confounded (attenuation ${attenuation}%): ${tc.summary || ''}`); }
    }
  }
  // Outlier sensitivity
  const outlier = vr.outlier_sensitivity || vr.outlier_analysis || {};
  if (outlier[predictor] || outlier[target]) {
    const o = outlier[predictor] || outlier[target];
    if (o && (o.outlier_driven || o.leverage_driven)) { outlier_driven = true; findings.push(`Outlier-driven: ${o.summary || ''}`); }
    if (o && typeof o.delta_r === 'number' && Math.abs(o.delta_r) > 0.2) {
      leave_one_out_safe = false; leave_one_out_delta_r = o.delta_r;
      findings.push(`Leave-one-out |Δr|=${o.delta_r.toFixed(3)} > 0.2 → leverage_driven`);
    }
  }
  return { simpson_safe, trend_confounded, outlier_driven, leave_one_out_safe, leave_one_out_delta_r, time_sorted, regime_filtered, findings };
}

// ── Helper: look up time_lag for a pair ──
function lookupTimeLag(predictor, target, tla) {
  if (!tla || !tla.key_findings) return { optimal_lag_steps: null, optimal_lag_seconds: null, lag_compensated_r: null, raw_r: null, r_improvement_pct: 0, confidence: 'not_applicable', physics_agreement: 'not_applicable' };
  const entry = (tla.key_findings || []).find(f => f.predictor === predictor && f.target === target);
  if (!entry) return { optimal_lag_steps: null, optimal_lag_seconds: null, lag_compensated_r: null, raw_r: null, r_improvement_pct: 0, confidence: 'not_applicable', physics_agreement: 'not_applicable' };
  return {
    optimal_lag_steps: entry.optimal_lag_steps ?? null,
    optimal_lag_seconds: entry.optimal_lag_seconds ?? null,
    lag_compensated_r: entry.lag_compensated_r ?? null,
    raw_r: entry.raw_r ?? null,
    r_improvement_pct: entry.r_improvement_pct ?? 0,
    confidence: entry.confidence || 'moderate',
    physics_agreement: entry.physics_agreement || 'not_applicable',
  };
}

// ── Helper: look up physics proof for a pair ──
function lookupPhysics(predictor, target, pc, onto) {
  const defaultPhysics = { behavior_match: 'UNVERIFIED', governing_law: null, predicted_functional_form: null, functional_form_match: null, direction_match: null, magnitude_ratio: null, magnitude_verdict: 'UNTESTED', proof_strength: 'WEAK' };
  if (!pc && !onto) return defaultPhysics;
  // behavior_match from ontology parameters
  const ontoParams = onto?.parameters || onto?.signals?.process_parameters || [];
  const match = ontoParams.find(p => (p.name || p.column) === predictor);
  const behavior_match = match?.behavior_match || 'UNVERIFIED';
  const governing_law = match?.governing_law || null;
  return { ...defaultPhysics, behavior_match, governing_law };
}

// ── Build validated_correlations.pairs[] ──
const fallbackN = dataQualityReport?.row_count || inputManifest?.rows || anomalyReport?.metadata?.row_count || 0;
const basePairs = extractCorrelations(featureSummary, fallbackN);
const pairs = basePairs.slice(0, 30).map(p => stripNulls({
  ...p,
  validation: lookupValidation(p.predictor, p.target, validateReport),
  time_lag: lookupTimeLag(p.predictor, p.target, timeLagAnalysis),
  physics: lookupPhysics(p.predictor, p.target, physicsCheck, ontology),
}));

const validated_correlations = {
  description: `Top ${pairs.length} correlations with |r|>=0.3, merged from feature_summary + validate_report + time_lag_analysis + physics_check. Cite as validated_correlations.pairs[N] downstream.`,
  pairs,
};

// ── Build adaptive_decision_audit (V2 field names) ──
const processParamCount = anomalyReport.process_parameter_fluctuation ? Object.keys(anomalyReport.process_parameter_fluctuation).length : 0;
const targetCount = anomalyReport.targets ? Object.keys(anomalyReport.targets).length : 0;
const dataViewMode = processParamCount > 0 && targetCount > 0 ? 'process_plus_inspection' : (processParamCount > 0 ? 'process_only' : (targetCount > 0 ? 'inspection_only' : 'unknown'));
const timeColumn = inputManifest.time_column;
const groupColumn = inputManifest.primary_group_column;
const data_shapes_detected = [];
if (timeColumn) data_shapes_detected.push('time_series');
if (groupColumn) data_shapes_detected.push('product_grouping');
if (processParamCount > 0) data_shapes_detected.push('process_parameters');
if (targetCount > 0) data_shapes_detected.push('inspection_or_quality_targets');

const adaptive_decision_audit = {
  data_view_mode: dataViewMode,
  mode_justification: `Detected ${processParamCount} process params, ${targetCount} targets. View mode: ${dataViewMode}.`,
  data_shapes_detected,
  selected_analyses: [
    { analysis: 'pure_process_fluctuation', why: 'process params available', evidence_artifacts: ['02_processed/anomaly_report.json'] },
    ...(dataViewMode === 'process_plus_inspection' ? [{ analysis: 'dual_drive_linkage', why: 'both process + inspection present', evidence_artifacts: ['02_processed/anomaly_report.json'] }] : []),
    ...(groupColumn ? [{ analysis: 'product_stratified_correlation', why: `group col ${groupColumn} detected → Simpson risk`, evidence_artifacts: ['02_processed/validate_report.json'] }] : []),
  ],
  skipped_analyses: [
    ...(timeColumn ? [] : [{ analysis: 'time_lag_compensation', why: 'no time column' }]),
  ],
};

// ── Build anomaly_highlights from anomaly_report ──
const anomaly_windows = [];
const targets = anomalyReport.targets || {};
for (const [tname, tdata] of Object.entries(targets)) {
  for (const iv of (tdata.anomaly_intervals || [])) {
    anomaly_windows.push({
      product: null,
      time_range: iv.start_index != null ? `index ${iv.start_index}-${iv.end_index}` : 'unknown',
      quality_target: tname,
      process_params_involved: [],
      onset_pattern: iv.severity || 'anomaly',
      quality_reset: 'NOT_APPLICABLE',
    });
  }
}
const anomaly_highlights = { anomaly_windows: anomaly_windows.slice(0, 10) };

// ── Build process_health ──
const abnormal_params = [];
const procFluct = anomalyReport.process_parameter_fluctuation || {};
for (const [param, info] of Object.entries(procFluct)) {
  abnormal_params.push({
    param,
    pattern: (info.pattern || info.fluctuation_type || 'high_variability'),
    rate: info.drift_rate || info.rate || null,
    duration: info.duration || null,
  });
}
const steady_ratio = readJson('02_processed/production_regime_filter.json', {})?.steady_state_ratio ?? 1.0;
const process_health = { abnormal_params, regime_shifts_detected: false, steady_state_ratio: steady_ratio };

// ── Build dual_drive_linkages ──
const linkages = [];
const dd = anomalyReport.dual_drive_analysis || {};
for (const link of (dd.cross_domain_links || [])) {
  linkages.push({
    product: link.group || link.product || null,
    process_anomaly: link.process_anomaly || link.process_parameter || 'process fluctuation',
    quality_anomaly: link.quality_anomaly || link.target || 'quality anomaly',
    temporal_order: link.temporal_order || 'UNKNOWN',
    lead_time: link.lead_time || null,
    cross_validated_by: link.cross_validated_by || [],
  });
}
const dual_drive_linkages = { linkages };

// ── Build visual_evidence_summary (only if LLM didn't write it) ──
let visual_evidence_summary = preserved.visual_evidence_summary;
if (!visual_evidence_summary && visualAnalysis) {
  visual_evidence_summary = {
    synchronous_groups: (visualAnalysis.synchronous_groups || visualAnalysis.cross_parameter_temporal_alignment?.synchronous_groups || []).slice(0, 5),
    precedence_signals: (visualAnalysis.precedence_signals || []).slice(0, 5),
    event_responses: (visualAnalysis.event_responses || []).slice(0, 5),
  };
}

// ── Build data_cleaning_provenance from cleaning_integrity ──
const ci = (dataQualityReport && dataQualityReport.cleaning_integrity) || readJson('02_processed/cleaning_integrity.json', null);
const data_cleaning_provenance = ci ? {
  data_source: ci.data_source || 'cleaned',
  data_source_reason: ci.data_source_reason || (ci.data_source === 'raw_fallback' ? 'failed integrity checks' : 'passed integrity checks'),
  integrity_checks: ci.integrity_checks || {
    row_count: ci.row_count_check || ci.integrity_checks?.row_count || {},
    type_integrity: ci.type_integrity || ci.integrity_checks?.type_integrity || {},
    range_fidelity: ci.range_fidelity || ci.integrity_checks?.range_fidelity || {},
    batch_identity: ci.batch_identity_integrity || ci.integrity_checks?.batch_identity || {},
  },
  cleaning_operations: ci.cleaning_operations || [],
  repair_attempts: ci.repair_attempts || [],
} : { data_source: 'cleaned', data_source_reason: 'cleaning_integrity not recorded', integrity_checks: {}, cleaning_operations: [], repair_attempts: [] };

// ── Build param_ambiguity from clarification_needed (only if LLM didn't write it) ──
let param_ambiguity = preserved.param_ambiguity;
if (!param_ambiguity || !param_ambiguity.ambiguous_params) {
  const ambiguous = [];
  if (clarificationNeeded && Array.isArray(clarificationNeeded.parameters)) {
    for (const p of clarificationNeeded.parameters) {
      if (p.physical_meaning_confidence === 'UNKNOWN' || p.confidence === 'UNKNOWN') {
        ambiguous.push({ param: p.name || p.column, reason: p.reason || 'opaque name + ambiguous range', best_guess: p.best_guess || p.inferred_meaning || null, confidence_ceiling_applies: true });
      }
    }
  }
  param_ambiguity = { ambiguous_params: ambiguous, resolved_count: 0, unresolved_count: ambiguous.length };
}

// ── Build expert_gap_analysis (preserve LLM version or minimal) ──
const scriptsDir = join(runDir, '06_scripts');
const customScripts = exists('06_scripts') ? fs.readdirSync(scriptsDir).filter(f => f.endsWith('.py') || f.endsWith('.mjs')) : [];
const expert_gap_analysis = preserved.expert_gap_analysis || {
  custom_scripts_run: customScripts.map(f => `06_scripts/${f}`),
  custom_findings: [],
  remaining_gaps: [],
  recommended_extra_data: [],
};

// ── Build diagnostician_handoff (preserve LLM version, or minimal from top pairs) ──
let diagnostician_handoff = preserved.diagnostician_handoff;
if (!diagnostician_handoff || !Array.isArray(diagnostician_handoff.priority_hypothesis_inputs) || diagnostician_handoff.priority_hypothesis_inputs.length === 0) {
  // Mechanical fallback: top 3 surviving validated pairs → priority inputs
  const surviving = pairs.filter(p => p.validation.simpson_safe && !p.validation.outlier_driven && p.validation.leave_one_out_safe).slice(0, 3);
  diagnostician_handoff = {
    priority_hypothesis_inputs: surviving.map((p, i) => ({
      hypothesis: `${p.predictor} affects ${p.target} (r=${p.pearson_r?.toFixed(2)}, validation passed)`,
      confidence_from_data_side: Math.abs(p.pearson_r) > 0.6 ? 'high' : 'medium',
      key_evidence_refs: [`validated_correlations.pairs[${pairs.indexOf(p)}]`],
      caveats: p.validation.findings.length ? p.validation.findings : [],
      falsification_condition: `If ${p.predictor} returns to baseline and ${p.target} does not improve, hypothesis falsified`,
    })),
    evidence_gaps: dataViewMode === 'process_only' ? ['Inspection/quality data missing — process-to-quality linkage not testable'] : [],
  };
}

// ── Assemble V2 handoff ──
const handoff = {
  schema_version: '2.0',
  run_id: runManifest.run_id || basename(runDir),
  generated_at: new Date().toISOString(),
  data_view_mode: dataViewMode,
  adaptive_decision_audit,
  validated_correlations,
  anomaly_highlights,
  process_health,
  dual_drive_linkages,
  ...(visual_evidence_summary ? { visual_evidence_summary } : {}),
  expert_gap_analysis,
  param_ambiguity,
  diagnostician_handoff,
  data_cleaning_provenance,
};

writeJson('02_processed/data_analysis_conclusion.json', handoff);
console.log(JSON.stringify({
  ok: true,
  schema_version: '2.0',
  output: '02_processed/data_analysis_conclusion.json',
  mode: isExistingV2 ? 'merged_into_existing_v2' : 'generated_full_v2',
  validated_pairs: pairs.length,
  preserved_llm_fields: isExistingV2 ? Object.keys(preserved) : [],
}, null, 2));
