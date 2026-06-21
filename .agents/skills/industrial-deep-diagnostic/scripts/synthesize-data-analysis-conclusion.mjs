#!/usr/bin/env node
// synthesize-data-analysis-conclusion.mjs — Deterministically generate the
// expert data-analysis handoff from existing run artifacts.
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

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function writeJson(pathLike, data) {
  fs.writeFileSync(pathLike, `${JSON.stringify(data, null, 2)}\n`);
}

const runManifest = readJson(join(runDir, 'run_manifest.json'), {});
const inputManifest = readJson(join(runDir, '00_input', 'input_manifest.json'), {});
const ontology = readJson(join(runDir, '01_ontology', 'ontology.json'), {});
const analysisParameterSelection = readJson(join(runDir, '02_processed', 'analysis_parameter_selection.json'), null);
const featureSummary = readJson(join(runDir, '02_processed', 'feature_summary.json'), {});
const validateReport = readJson(join(runDir, '02_processed', 'validate_report.json'), {});
const anomalyReport = readJson(join(runDir, '02_processed', 'anomaly_report.json'), {});
const dataQualityReport = readJson(join(runDir, '02_processed', 'data_quality_report.json'), {});
const productGroupAnalysis = readJson(join(runDir, '02_processed', 'product_group_analysis.json'), null);
const zoneAnalysis = readJson(join(runDir, '02_processed', 'zone_analysis.json'), null);
const pairedSensorAnalysis = readJson(join(runDir, '02_processed', 'paired_sensor_analysis.json'), null);
const transitionCandidates = readJson(join(runDir, '02_processed', 'transition_candidates.json'), null);
const processHealthAnalysis = readJson(join(runDir, '02_processed', 'process_health_analysis.json'), null);
const plotManifest = readJson(join(runDir, '03_figures', 'plot_manifest.json'), { plots: [] });

const scriptsDir = join(runDir, '06_scripts');
const customScripts = fs.existsSync(scriptsDir)
  ? fs.readdirSync(scriptsDir).filter((file) => file.endsWith('.py') || file.endsWith('.mjs') || file.endsWith('.js'))
  : [];

const plotFiles = Array.isArray(plotManifest.plots)
  ? plotManifest.plots.map((plot) => plot.file || plot.path).filter(Boolean)
  : [];

function plotArtifactPath(plotFile) {
  if (!plotFile) return null;
  return plotFile.startsWith('03_figures/') ? plotFile : `03_figures/${plotFile}`;
}

const temporalPlotFiles = Array.isArray(plotManifest.plots)
  ? plotManifest.plots
    .filter((plot) => {
      const haystack = [
        plot.file,
        plot.filename,
        plot.title,
        plot.plot_type,
        plot.description
      ].filter(Boolean).join(' ').toLowerCase();
      return /temporal|time|timeline|aligned|时序|时间|对齐/.test(haystack);
    })
    .map((plot) => plotArtifactPath(plot.file || plot.filename || plot.path))
    .filter(Boolean)
  : [];

function artifactExists(relativePath) {
  return fs.existsSync(join(runDir, relativePath));
}

function nonEmptyObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0;
}

function countObjectKeys(value) {
  return nonEmptyObject(value) ? Object.keys(value).length : 0;
}

function coverageItem(status, evidenceArtifacts, summary, gaps = []) {
  return {
    status,
    evidence_artifacts: evidenceArtifacts.filter(Boolean),
    summary,
    gaps
  };
}

const dataShapesDetected = [];
const timeColumn = inputManifest.time_column || dataQualityReport.time_column || anomalyReport.dual_drive_analysis?.time_column || null;
const groupColumn = inputManifest.primary_group_column || dataQualityReport.primary_group_column || anomalyReport.dual_drive_analysis?.group_column || null;
const processParameterCount = countObjectKeys(anomalyReport.process_parameter_fluctuation);
const processParameterNames = Object.keys(anomalyReport.process_parameter_fluctuation || {});
const targetCount = countObjectKeys(anomalyReport.targets);
const targetNames = Object.keys(anomalyReport.targets || {});
const integratedLinkCount = Array.isArray(anomalyReport.dual_drive_analysis?.cross_domain_links)
  ? anomalyReport.dual_drive_analysis.cross_domain_links.length
  : 0;
const perProductAnalysisCount = countObjectKeys(anomalyReport.dual_drive_analysis?.per_product_analysis);

if (timeColumn) dataShapesDetected.push('time_series');
if (groupColumn) dataShapesDetected.push('product_or_batch_grouping');
if (processParameterCount > 0) dataShapesDetected.push('process_parameters');
if (targetCount > 0) dataShapesDetected.push('inspection_or_quality_targets');
if (productGroupAnalysis || perProductAnalysisCount > 0) dataShapesDetected.push('product_group_analysis');
if (zoneAnalysis || countObjectKeys(anomalyReport.zone_signals) > 0) dataShapesDetected.push('multi_zone_sensors');
if (pairedSensorAnalysis || countObjectKeys(anomalyReport.paired_sensor_signals) > 0) dataShapesDetected.push('paired_or_cascaded_sensors');
if (transitionCandidates || (Array.isArray(anomalyReport.transition_events) && anomalyReport.transition_events.length > 0)) dataShapesDetected.push('transition_or_event_markers');
if (processHealthAnalysis) dataShapesDetected.push('process_health_custom_analysis');

const hasTrueDualDriveEvidence = processParameterCount > 0 && targetCount > 0 && integratedLinkCount > 0;
const dataViewMode = processParameterCount > 0 && targetCount > 0
  ? 'process_plus_inspection'
  : (processParameterCount > 0 ? 'process_only' : (targetCount > 0 ? 'inspection_only' : 'unknown'));

const modeJustification = {
  process_plus_inspection: `Detected ${processParameterCount} process-parameter fluctuation summaries and ${targetCount} inspection/quality target summaries.`,
  process_only: `Detected ${processParameterCount} process-parameter fluctuation summaries but no reliable inspection/quality target summaries in anomaly_report.json.`,
  inspection_only: `Detected ${targetCount} inspection/quality target summaries but no process-parameter fluctuation summaries.`,
  unknown: 'Could not reliably distinguish process parameters from inspection/quality targets from the available Step 3 artifacts.'
}[dataViewMode];

const selectedAnalyses = [];
const skippedOrNotApplicable = [];

if (processParameterCount > 0) {
  selectedAnalyses.push({
    analysis: 'pure_process_fluctuation_and_drift',
    reason: 'Process parameters were available, so independent process stability screening is required before causal interpretation.',
    evidence_artifacts: ['02_processed/anomaly_report.json'],
    coverage_status: 'covered'
  });
} else {
  skippedOrNotApplicable.push({
    analysis: 'pure_process_fluctuation_and_drift',
    status: 'not_applicable',
    reason: 'No process-parameter fluctuation block was available in anomaly_report.json.'
  });
}

if (dataViewMode === 'process_plus_inspection') {
  selectedAnalyses.push({
    analysis: 'process_inspection_dual_drive',
    reason: 'Both process and inspection/quality signals were available, so cross-domain linkage must be tested.',
    evidence_artifacts: ['02_processed/anomaly_report.json'],
    coverage_status: hasTrueDualDriveEvidence ? 'covered' : 'partial'
  });
} else {
  skippedOrNotApplicable.push({
    analysis: 'process_inspection_dual_drive',
    status: 'not_applicable',
    reason: dataViewMode === 'process_only'
      ? 'Process-only data has no true inspection/quality targets; linkage to defects remains an evidence gap.'
      : 'The available artifacts do not contain both process-side and inspection-side evidence.'
  });
}

if (groupColumn || productGroupAnalysis || perProductAnalysisCount > 0) {
  selectedAnalyses.push({
    analysis: 'grouping_and_confounding_checks',
    reason: `Detected grouping column ${groupColumn || productGroupAnalysis?.group_column || 'unknown'}, so aggregate relationships must be compared with within-group behavior.`,
    evidence_artifacts: ['02_processed/product_group_analysis.json', '02_processed/anomaly_report.json', '02_processed/validate_report.json'].filter((path) => artifactExists(path)),
    coverage_status: productGroupAnalysis || perProductAnalysisCount > 0 ? 'covered' : 'partial'
  });
} else {
  skippedOrNotApplicable.push({
    analysis: 'grouping_and_confounding_checks',
    status: 'not_applicable',
    reason: 'No product/lot/batch-style grouping column was detected in Step 3 artifacts.'
  });
}

if (timeColumn || transitionCandidates) {
  selectedAnalyses.push({
    analysis: 'temporal_regime_event_analysis',
    reason: timeColumn
      ? `Detected time column ${timeColumn}; time-aligned overlays, lag/sequence review, and transition analysis are applicable.`
      : 'Transition candidates were detected even without a reliable time column.',
    evidence_artifacts: [...temporalPlotFiles, '02_processed/transition_candidates.json'].filter((path) => artifactExists(path)),
    coverage_status: temporalPlotFiles.some((path) => artifactExists(path)) || transitionCandidates ? 'covered' : 'partial'
  });
} else {
  skippedOrNotApplicable.push({
    analysis: 'temporal_regime_event_analysis',
    status: 'not_applicable',
    reason: 'No reliable time column or transition/event candidate artifact was detected.'
  });
}

const scenarioArtifacts = [];
if (zoneAnalysis) scenarioArtifacts.push('02_processed/zone_analysis.json');
if (pairedSensorAnalysis) scenarioArtifacts.push('02_processed/paired_sensor_analysis.json');
if (processHealthAnalysis) scenarioArtifacts.push('02_processed/process_health_analysis.json');
if (customScripts.length > 0) scenarioArtifacts.push(...customScripts.map((file) => `06_scripts/${file}`));
if (scenarioArtifacts.length > 0) {
  selectedAnalyses.push({
    analysis: 'scenario_specific_expert_analysis',
    reason: 'Detected data structures or custom scripts requiring analysis beyond the universal baseline.',
    evidence_artifacts: scenarioArtifacts,
    coverage_status: 'covered'
  });
} else {
  skippedOrNotApplicable.push({
    analysis: 'scenario_specific_expert_analysis',
    status: 'skipped',
    reason: 'No scenario-specific artifact or custom script was present; the run should justify why the baseline was sufficient.'
  });
}

const adaptiveDecisionAudit = {
  data_view_mode: dataViewMode,
  mode_justification: modeJustification,
  data_shapes_detected: [...new Set(dataShapesDetected.length ? dataShapesDetected : ['unknown'])],
  selected_analyses: selectedAnalyses,
  skipped_or_not_applicable: skippedOrNotApplicable,
  custom_analysis_required: customScripts.length > 0 || dataViewMode === 'process_only' || Boolean(zoneAnalysis) || Boolean(pairedSensorAnalysis),
  custom_analysis_reason: customScripts.length > 0
    ? 'Custom scripts were present for scenario-specific analysis.'
    : (dataViewMode === 'process_only'
      ? 'Process-only data usually requires process-health interpretation and explicit evidence-gap handling.'
      : 'No custom script artifacts were found; baseline sufficiency must be justified by the Data Processor.'),
  expert_review_summary: `Adaptive review classified the run as ${dataViewMode}, detected ${[...new Set(dataShapesDetected)].join(', ') || 'no special data shapes'}, and selected ${selectedAnalyses.length} analysis families with ${skippedOrNotApplicable.length} skipped/not-applicable decisions.`
};

const analysisCoverageMatrix = {
  pure_process_analysis: processParameterCount > 0
    ? coverageItem('covered', ['02_processed/anomaly_report.json'], `Screened ${processParameterCount} process parameters for fluctuation, drift, span, and abrupt behavior.`)
    : coverageItem('missing', [], 'No process-parameter fluctuation evidence was available.', ['Provide process parameter columns or repair anomaly detection.']),
  process_inspection_dual_drive: dataViewMode === 'process_plus_inspection'
    ? coverageItem(
      hasTrueDualDriveEvidence ? 'covered' : 'partial',
      ['02_processed/anomaly_report.json'],
      hasTrueDualDriveEvidence ? `Detected ${integratedLinkCount} process-inspection linkage candidates.` : 'Process and inspection targets exist, but no strong cross-domain link was extracted.',
      hasTrueDualDriveEvidence ? [] : ['Review whether target/process column selection is correct and whether timing/group windows are too sparse.']
    )
    : coverageItem('not_applicable', ['02_processed/anomaly_report.json'], 'No true dual-drive linkage can be claimed because the data does not contain both process and inspection/quality evidence.', ['Add inspection/quality/test data to evaluate process-to-quality linkage.']),
  grouping_confounding: groupColumn || productGroupAnalysis || perProductAnalysisCount > 0
    ? coverageItem(
      productGroupAnalysis || perProductAnalysisCount > 0 ? 'covered' : 'partial',
      ['02_processed/product_group_analysis.json', '02_processed/anomaly_report.json', '02_processed/validate_report.json'].filter((path) => artifactExists(path)),
      `Grouping/confounding analysis used primary grouping column ${groupColumn || productGroupAnalysis?.group_column || 'unknown'}.`,
      productGroupAnalysis || perProductAnalysisCount > 0 ? [] : ['Product group artifact missing; verify grouped analysis ran.']
    )
    : coverageItem('not_applicable', [], 'No product/lot/batch-style grouping column was detected.', []),
  temporal_regime_event: timeColumn || transitionCandidates
    ? coverageItem(
      temporalPlotFiles.some((path) => artifactExists(path)) || transitionCandidates ? 'covered' : 'partial',
      [...temporalPlotFiles, '02_processed/transition_candidates.json'].filter((path) => artifactExists(path)),
      timeColumn ? `Temporal/regime analysis is applicable through time column ${timeColumn}.` : 'Transition/event candidates were available without a reliable time column.',
      temporalPlotFiles.some((path) => artifactExists(path)) || !timeColumn ? [] : ['A time-aligned or temporal plot is missing from plot_manifest.json.']
    )
    : coverageItem('not_applicable', [], 'No reliable time column or transition/event artifact was detected.', ['Temporal order claims should not be made.']),
  scenario_specific: scenarioArtifacts.length > 0
    ? coverageItem('covered', scenarioArtifacts, 'Scenario-specific artifacts/custom scripts were generated for the detected data structure.')
    : coverageItem('partial', [], 'No scenario-specific artifact was generated; baseline-only sufficiency needs explicit justification.', ['Consider zone, paired-sensor, event, nonlinear, cyclic, or process-health custom analysis if data shape supports it.'])
};

const topPairs = []
  .concat(featureSummary.top_correlations || [])
  .concat(featureSummary.strongest_links || [])
  .slice(0, 3);

const baselineFindings = topPairs.map((item) => ({
  finding: item.summary || item.description || `${item.parameter || item.feature || 'parameter'} shows a notable relationship with ${item.target || 'quality target'}.`,
  source: '02_processed/feature_summary.json',
  evidence_rank: 3
}));

if (baselineFindings.length === 0) {
  baselineFindings.push({
    finding: 'Baseline statistical scripts completed, but no high-confidence correlation summary was automatically extracted.',
    source: '02_processed/feature_summary.json',
    evidence_rank: 3
  });
}

const discrepancySignals = ontology.discrepancy_signals || ontology.discrepancySignals || [];
const ontologyInterpretation = discrepancySignals.slice(0, 3).map((signal) => ({
  parameter_or_pattern: signal.parameter || signal.name || 'unknown_pattern',
  ontology_role: signal.ontology_role || signal.role || 'ontology-linked process feature',
  industry_knowledge: signal.industry_knowledge || signal.knowledge || 'Industry context indicates this feature can influence quality through a process mechanism.',
  interpretation: signal.interpretation || signal.description || 'The ontology/data mismatch is diagnostically meaningful and should be tested downstream.',
  confidence: signal.confidence || 'medium'
}));

function collectOntologySignals(value, bucket = []) {
  if (!value || typeof value !== 'object') return bucket;
  if (Array.isArray(value)) {
    for (const item of value) collectOntologySignals(item, bucket);
    return bucket;
  }

  const candidateName = value.name || value.id || value.column || value.column_name || value.signal || value.parameter;
  const hasSemanticContent = value.role || value.ontology_role || value.physical_meaning || value.process_stage || value.stage || value.governing_law || value.unit;
  if (candidateName && hasSemanticContent) {
    bucket.push(value);
  }

  for (const key of ['parameters', 'signals', 'process_parameters', 'quality_targets', 'measurements']) {
    if (value[key]) collectOntologySignals(value[key], bucket);
  }
  return bucket;
}

function normalizeName(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '');
}

const ontologySignals = collectOntologySignals(ontology, []);
const candidateDataColumns = [...processParameterNames, ...targetNames];
const matchedOntologyInterpretation = [];
for (const column of candidateDataColumns.slice(0, 8)) {
  const normalizedColumn = normalizeName(column);
  const match = ontologySignals.find((item) => {
    const names = [item.name, item.id, item.column, item.column_name, item.signal, item.parameter].map(normalizeName);
    return names.some((name) => name && (name === normalizedColumn || name.includes(normalizedColumn) || normalizedColumn.includes(name)));
  });
  if (!match) continue;
  matchedOntologyInterpretation.push({
    parameter_or_pattern: column,
    ontology_role: match.role || match.ontology_role || match.type || 'ontology-linked measured signal',
    industry_knowledge: [
      match.physical_meaning ? `Physical meaning: ${match.physical_meaning}` : null,
      match.process_stage || match.stage ? `Process stage: ${match.process_stage || match.stage}` : null,
      match.governing_law ? `Governing law: ${match.governing_law}` : null,
      match.unit ? `Unit: ${match.unit}` : null
    ].filter(Boolean).join('; ') || 'Ontology provides semantic context for this measured signal.',
    interpretation: processParameterNames.includes(column)
      ? 'This process-side data pattern should be interpreted through its ontology role before being promoted to a root-cause hypothesis.'
      : 'This inspection/quality-side signal defines the outcome side of any dual-drive causal claim.',
    confidence: match.confidence || 'medium'
  });
}

for (const item of matchedOntologyInterpretation) {
  if (ontologyInterpretation.length >= 6) break;
  if (!ontologyInterpretation.some((existing) => existing.parameter_or_pattern === item.parameter_or_pattern)) {
    ontologyInterpretation.push(item);
  }
}

if (ontologyInterpretation.length === 0) {
  ontologyInterpretation.push({
    parameter_or_pattern: inputManifest.time_column || 'dominant_process_pattern',
    ontology_role: 'process-context anchor',
    industry_knowledge: 'Process interpretation depends on the mapping between measured signals and process stages.',
    interpretation: 'The ontology did not expose explicit discrepancy signals, so downstream diagnosis should rely on validated data evidence and first-principles checks.',
    confidence: 'low'
  });
}

const conclusions = [];
if (dataViewMode === 'process_only') {
  conclusions.push({
    conclusion: 'Process-only data supports process-health screening, but does not support process-to-quality or defect-causality claims without inspection/quality targets.',
    supporting_sources: ['02_processed/anomaly_report.json'],
    evidence_strength: processParameterCount > 0 ? 'moderate' : 'weak',
    diagnostic_relevance: 'Use this to form process-stability hypotheses or NEEDS_DATA conclusions rather than final quality root-cause claims.',
    known_caveats: ['Inspection/quality/test data is required to validate whether process abnormalities caused a quality outcome.']
  });
}
if (dataViewMode === 'process_plus_inspection' && anomalyReport.dual_drive_analysis?.summary) {
  conclusions.push({
    conclusion: anomalyReport.dual_drive_analysis.summary,
    supporting_sources: ['02_processed/anomaly_report.json'],
    evidence_strength: hasTrueDualDriveEvidence ? 'moderate' : 'weak',
    diagnostic_relevance: 'Use this as process-plus-inspection linkage evidence in the competing-hypothesis stage.',
    known_caveats: hasTrueDualDriveEvidence ? [] : ['No strong integrated process-inspection links were extracted automatically.']
  });
}
if (validateReport.summary || validateReport.validation_summary) {
  conclusions.push({
    conclusion: 'Statistical validation completed and should bound confidence for any causal claim.',
    supporting_sources: ['02_processed/validate_report.json'],
    evidence_strength: 'strong',
    diagnostic_relevance: 'Validated findings should be prioritized over raw correlations.',
    known_caveats: []
  });
}
if (conclusions.length === 0) {
  conclusions.push({
    conclusion: 'Processed data artifacts exist, but the diagnostic handoff should explicitly test whether observed parameter changes survive subgroup and physics checks.',
    supporting_sources: ['02_processed/feature_summary.json'],
    evidence_strength: 'weak',
    diagnostic_relevance: 'Treat this as a starting point rather than a root-cause conclusion.',
    known_caveats: ['No richer structured conclusion was available at synthesis time.']
  });
}

const customScriptInventory = customScripts.map((file) => ({
  script: `06_scripts/${file}`,
  purpose: 'Scenario-specific custom analysis or plotting generated during the run.',
  inputs: ['02_processed/cleaned_data.csv', '01_ontology/ontology.json'],
  outputs: plotFiles.filter((plot) => plot.includes(basename(file, '.' + file.split('.').pop()))).slice(0, 3)
}));

// Data cleaning provenance (留痕) — propagate Phase 2.2.5 cleaning_integrity so the
// Diagnostician, Reporter, and HTML all disclose the same data source & cleaning actions.
const cleaningIntegrity = (dataQualityReport && dataQualityReport.cleaning_integrity) || null;
const dataCleaningProvenance = cleaningIntegrity
  ? {
      data_source: cleaningIntegrity.data_source || 'cleaned',
      data_source_reason: cleaningIntegrity.fallback_reason
        || (cleaningIntegrity.data_source === 'raw_fallback'
          ? 'cleaned_data failed integrity checks beyond in-place repair; fell back to raw DATA_PATH'
          : 'cleaned_data passed Phase 2.2.5 integrity checks (row/type/range fidelity)'),
      integrity_checks: {
        row_count: cleaningIntegrity.row_count_check || {},
        type_integrity: cleaningIntegrity.type_integrity || {},
        range_fidelity: cleaningIntegrity.range_fidelity || {}
      },
      cleaning_operations: cleaningIntegrity.cleaning_operations || [],
      repair_attempts: cleaningIntegrity.repair_attempts || []
    }
  : {
      data_source: 'cleaned',
      data_source_reason: 'cleaning_integrity not recorded (Phase 2.2.5 did not run or pre-dates the gate) — provenance incomplete, data-processor must enrich',
      integrity_checks: {},
      cleaning_operations: [],
      repair_attempts: []
    };

const handoff = {
  run_id: runManifest.run_id || basename(runDir),
  generated_at: new Date().toISOString(),
  analysis_mode: analysisParameterSelection
    ? (customScripts.length > 0 ? 'ontology_guided_plus_custom' : 'ontology_guided_baseline')
    : (customScripts.length > 0 ? 'baseline_plus_custom' : 'baseline_only_with_justification'),
  baseline_script_results: {
    scripts_run: [
      'convert.mjs',
      'dp_toolkit.py preprocess',
      'stats.mjs / stats_analysis.py',
      'stats_validate.mjs',
      'dp_toolkit.py anomaly',
      'physics_check.py'
    ],
    key_findings: baselineFindings,
    limitations: [
      'Aggregate patterns should not be treated as causal without subgroup and physics confirmation.',
      inputManifest.time_column ? 'Temporal reasoning depends on the detected time column remaining valid after preprocessing.' : 'No reliable time column was detected, so lag claims must remain limited.'
    ]
  },
  expert_custom_analysis: {
    custom_scripts_written: customScripts.length > 0,
    script_inventory: customScriptInventory,
    analysis_questions: [
      'Which process-side abnormalities remain after validation and grouping checks?',
      'Do inspection anomalies align with process-side instability in the same product or time context?'
    ],
    custom_outputs: customScripts.length > 0 ? customScripts.map((file) => `06_scripts/${file}`) : [],
    why_needed: customScripts.length > 0
      ? 'Custom scripts were needed to answer scenario-specific questions beyond the baseline statistical pipeline.'
      : adaptiveDecisionAudit.custom_analysis_reason
  },
  ontology_industry_interpretation: ontologyInterpretation,
  adaptive_decision_audit: adaptiveDecisionAudit,
  analysis_coverage_matrix: analysisCoverageMatrix,
  analysis_boundary: analysisParameterSelection ? {
    tiers: analysisParameterSelection.analysis_tiers,
    pruned_pairs: analysisParameterSelection.pruned,
    predictor_cols: analysisParameterSelection.predictor_cols,
    exclude_cols: analysisParameterSelection.exclude_cols,
    derived_features: analysisParameterSelection.derived_features_to_compute || []
  } : { missing: 'Phase 0.4 analysis_parameter_selection.json not found — analysis ran without ontology-guided filtering' },
  data_cleaning_provenance: dataCleaningProvenance,
  data_supported_conclusions: conclusions,
  handoff_to_diagnostician: {
    priority_hypothesis_inputs: conclusions.slice(0, 3).map((item, index) => ({
      candidate: `candidate_${index + 1}`,
      why_prioritized: item.conclusion,
      supporting_artifacts: item.supporting_sources
    })),
    evidence_gaps: [
      'Need final competing-hypothesis testing before turning data patterns into root-cause claims.',
      ...(dataViewMode === 'process_only' ? ['Inspection/quality/test data is missing, so process-to-quality linkage is not directly testable.'] : [])
    ],
    recommended_diagnostic_focus: [
      'Cross-check statistical patterns against physics plausibility and ontology roles.',
      'Verify whether product-group differences or event transitions explain the anomaly better than a universal process drift.'
    ]
  }
};

const outputPath = join(runDir, '02_processed', 'data_analysis_conclusion.json');
writeJson(outputPath, handoff);
console.log(JSON.stringify({ ok: true, output: outputPath, custom_scripts_detected: customScripts.length }, null, 2));
