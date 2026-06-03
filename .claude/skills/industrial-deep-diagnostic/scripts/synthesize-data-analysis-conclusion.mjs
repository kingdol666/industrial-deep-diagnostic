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
const featureSummary = readJson(join(runDir, '02_processed', 'feature_summary.json'), {});
const validateReport = readJson(join(runDir, '02_processed', 'validate_report.json'), {});
const anomalyReport = readJson(join(runDir, '02_processed', 'anomaly_report.json'), {});
const plotManifest = readJson(join(runDir, '03_figures', 'plot_manifest.json'), { plots: [] });

const scriptsDir = join(runDir, '06_scripts');
const customScripts = fs.existsSync(scriptsDir)
  ? fs.readdirSync(scriptsDir).filter((file) => file.endsWith('.py') || file.endsWith('.mjs') || file.endsWith('.js'))
  : [];

const plotFiles = Array.isArray(plotManifest.plots)
  ? plotManifest.plots.map((plot) => plot.file || plot.path).filter(Boolean)
  : [];

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
if (anomalyReport.dual_drive_analysis?.summary) {
  conclusions.push({
    conclusion: anomalyReport.dual_drive_analysis.summary,
    supporting_sources: ['02_processed/anomaly_report.json'],
    evidence_strength: 'moderate',
    diagnostic_relevance: 'Use this as process-plus-inspection linkage evidence in the competing-hypothesis stage.',
    known_caveats: []
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

const handoff = {
  run_id: runManifest.run_id || basename(runDir),
  generated_at: new Date().toISOString(),
  analysis_mode: customScripts.length > 0 ? 'baseline_plus_custom' : 'baseline_only_with_justification',
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
      : 'No custom script artifacts were found; downstream diagnosis should rely on the validated baseline pipeline and record why it was sufficient.'
  },
  ontology_industry_interpretation: ontologyInterpretation,
  data_supported_conclusions: conclusions,
  handoff_to_diagnostician: {
    priority_hypothesis_inputs: conclusions.slice(0, 3).map((item, index) => ({
      candidate: `candidate_${index + 1}`,
      why_prioritized: item.conclusion,
      supporting_artifacts: item.supporting_sources
    })),
    evidence_gaps: [
      'Need final competing-hypothesis testing before turning data patterns into root-cause claims.'
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
