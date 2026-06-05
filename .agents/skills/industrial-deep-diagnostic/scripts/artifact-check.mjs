#!/usr/bin/env node
// artifact-check.mjs — Verify all required pipeline artifacts exist
// Run at pipeline completion to validate integrity.
//
// Usage: node artifact-check.mjs <run_dir> [skill_path]
//   Returns exit code 0 if all required files exist, 1 otherwise.
//   Prints missing files report to stdout.

import fs from 'fs';
import { join } from 'path';
import { execFileSync } from 'child_process';

const args = process.argv.slice(2);
const runDir = args[0];
const skillPath = args[1] || '.';

if (!runDir) {
  console.error('Usage: node artifact-check.mjs <run_dir> [skill_path]');
  process.exit(1);
}

function exists(p) {
  return fs.existsSync(join(runDir, p));
}

function check(label, filePath, critical = true) {
  const fullPath = join(runDir, filePath);
  if (!fs.existsSync(fullPath)) {
    return { label, path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }
  const stat = fs.statSync(fullPath);
  const sizeKb = (stat.size / 1024).toFixed(1);
  return { label, path: filePath, status: `OK (${sizeKb} KB)`, critical };
}

function validate(label, schemaPath, filePath, critical = true) {
  const schemaFullPath = join(skillPath, schemaPath);
  const fileFullPath = join(runDir, filePath);
  if (!fs.existsSync(fileFullPath)) {
    return { label: `${label} Schema Validation`, path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }
  if (!fs.existsSync(schemaFullPath)) {
    return { label: `${label} Schema Validation`, path: schemaPath, status: 'SCHEMA MISSING', critical };
  }
  try {
    execFileSync('node', [join(skillPath, 'scripts', 'validate.mjs'), schemaFullPath, fileFullPath], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
    return { label: `${label} Schema Validation`, path: filePath, status: 'VALID', critical };
  } catch (error) {
    const stderr = error.stderr ? String(error.stderr).trim() : '';
    const stdout = error.stdout ? String(error.stdout).trim() : '';
    return {
      label: `${label} Schema Validation`,
      path: filePath,
      status: `INVALID${stderr || stdout ? `: ${(stderr || stdout).slice(0, 300)}` : ''}`,
      critical
    };
  }
}

function validatePipelineLog(label, critical = true) {
  try {
    const stdout = execFileSync('node', [join(skillPath, 'scripts', 'pipeline-log-check.mjs'), runDir], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
    return {
      label,
      path: '.pipeline_events.jsonl',
      status: 'VALID',
      critical,
      detail: JSON.parse(String(stdout))
    };
  } catch (error) {
    const stdout = error.stdout ? String(error.stdout).trim() : '';
    const stderr = error.stderr ? String(error.stderr).trim() : '';
    let detail = null;
    if (stdout) {
      try {
        detail = JSON.parse(stdout);
      } catch (_) {}
    }
    return {
      label,
      path: '.pipeline_events.jsonl',
      status: `INVALID${stderr ? `: ${stderr.slice(0, 300)}` : ''}`,
      critical,
      detail
    };
  }
}

function readJsonIfExists(filePath) {
  const full = join(runDir, filePath);
  if (!fs.existsSync(full)) return null;
  try {
    return JSON.parse(fs.readFileSync(full, 'utf-8'));
  } catch (_) {
    return null;
  }
}

function conditionalFigureCheck() {
  const inputManifest = readJsonIfExists('00_input/input_manifest.json');
  const visualAnalysis = readJsonIfExists('03_figures/visual_analysis.json');
  const hasTimeColumn = Boolean(inputManifest && inputManifest.time_column);
  const masterFigurePath = '03_figures/fig_master_time_aligned_overlay.png';

  if (hasTimeColumn) {
    return check('Master Time Aligned Overlay', masterFigurePath, true);
  }

  const notApplicable = visualAnalysis && visualAnalysis.time_alignment_applicable === false;
  const reason = visualAnalysis && (visualAnalysis.not_applicable_reason || visualAnalysis.cross_parameter_temporal_alignment?.not_applicable_reason);

  if (notApplicable && reason) {
    return {
      label: 'Master Time Aligned Overlay',
      path: masterFigurePath,
      status: `NOT_APPLICABLE (${String(reason).slice(0, 160)})`,
      critical: false
    };
  }

  return {
    label: 'Master Time Aligned Overlay',
    path: masterFigurePath,
    status: 'MISSING (expected explicit NA proof or figure)',
    critical: true
  };
}

function validateDeliveryContract() {
  const manifest = readJsonIfExists('run_manifest.json');
  const issues = [];
  const presentStep = manifest && Array.isArray(manifest.steps) ? manifest.steps.find((step) => step.step === 'present') : null;
  const requiredArtifacts = manifest?.delivery_contract?.required_runtime_artifacts || [];

  for (const relPath of requiredArtifacts) {
    if (!exists(relPath)) {
      issues.push(`missing required artifact: ${relPath}`);
    }
  }

  if (!presentStep || !['completed', 'completed_with_errors'].includes(presentStep.status || '')) {
    issues.push('present step not completed in run_manifest.json');
  }

  if (manifest?.pipeline?.integrity?.last_artifact_check && manifest.pipeline.integrity.last_artifact_check !== 'PASS') {
    issues.push(`last_artifact_check=${manifest.pipeline.integrity.last_artifact_check}`);
  }

  return {
    label: 'Delivery Contract',
    path: 'run_manifest.json',
    status: issues.length === 0 ? 'VALID' : `INVALID: ${issues.join('; ').slice(0, 300)}`,
    critical: true
  };
}

function validateEvidenceClosure(label, critical = true) {
  try {
    const stdout = execFileSync('node', [join(skillPath, 'scripts', 'evidence-closure-check.mjs'), runDir], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
    return {
      label,
      path: 'evidence_closure_report.json',
      status: 'VALID',
      critical,
      detail: JSON.parse(String(stdout))
    };
  } catch (error) {
    const stdout = error.stdout ? String(error.stdout).trim() : '';
    const stderr = error.stderr ? String(error.stderr).trim() : '';
    let detail = null;
    if (stdout) {
      try {
        detail = JSON.parse(stdout);
      } catch (_) {}
    }
    return {
      label,
      path: 'evidence_closure_report.json',
      status: `INVALID${stderr ? `: ${stderr.slice(0, 300)}` : ''}`,
      critical,
      detail
    };
  }
}

function validateDiagnosticQuality(label, critical = true) {
  try {
    const stdout = execFileSync('node', [join(skillPath, 'scripts', 'diagnostic-quality-check.mjs'), runDir], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
    return {
      label,
      path: '04_diagnostics/diagnosis.json',
      status: 'VALID',
      critical,
      detail: JSON.parse(String(stdout))
    };
  } catch (error) {
    const stdout = error.stdout ? String(error.stdout).trim() : '';
    const stderr = error.stderr ? String(error.stderr).trim() : '';
    let detail = null;
    if (stdout) {
      try {
        detail = JSON.parse(stdout);
      } catch (_) {}
    }
    return {
      label,
      path: '04_diagnostics/diagnosis.json',
      status: `INVALID${stderr ? `: ${stderr.slice(0, 300)}` : ''}`,
      critical,
      detail
    };
  }
}

function validateVisualExecutionProof() {
  const visual = readJsonIfExists('03_figures/visual_analysis.json');
  if (!visual) {
    return {
      label: 'Visual Execution Proof',
      path: '03_figures/visual_analysis.json',
      status: 'MISSING (critical)',
      critical: true
    };
  }

  const provenance = visual.analysis_provenance || {};
  const issues = [];

  if (visual.observation_mode === 'skeleton_pre_vlm') {
    issues.push('observation_mode is still skeleton_pre_vlm');
  }
  if (provenance.source_agent !== 'vlm-visual-analyzer') {
    issues.push('source_agent is not vlm-visual-analyzer');
  }
  if (provenance.stage !== 'final_vlm_output') {
    issues.push('analysis_provenance.stage is not final_vlm_output');
  }
  if (provenance.skeleton_overwritten !== true) {
    issues.push('skeleton_overwritten is not true');
  }
  if (!Array.isArray(provenance.context_files_read) || provenance.context_files_read.length === 0) {
    issues.push('context_files_read is empty');
  }
  if (!Array.isArray(provenance.figure_inputs_attempted) || provenance.figure_inputs_attempted.length === 0) {
    issues.push('figure_inputs_attempted is empty');
  }
  if (visual.observation_mode === 'direct_image_reading' && (!Array.isArray(provenance.figure_inputs_read_successfully) || provenance.figure_inputs_read_successfully.length === 0)) {
    issues.push('direct_image_reading claimed without successful figure reads');
  }

  const allObservations = Array.isArray(visual.visual_observations)
    ? visual.visual_observations.flatMap((item) => Array.isArray(item?.observations) ? item.observations : [])
    : [];
  const groundedObservationCount = allObservations.filter((item) => {
    const meanings = item?.ontology_context?.parameter_physical_meanings;
    const stage = item?.ontology_context?.process_stage;
    return (meanings && Object.keys(meanings).length > 0) || typeof stage === 'string';
  }).length;
  if (groundedObservationCount < 2) {
    issues.push('fewer than 2 observations contain ontology grounding');
  }

  return {
    label: 'Visual Execution Proof',
    path: '03_figures/visual_analysis.json',
    status: issues.length === 0 ? 'VALID' : `INVALID: ${issues.join('; ').slice(0, 300)}`,
    critical: true
  };
}

// Define required artifacts per pipeline stage
const checks = [
  check('Run Manifest', 'run_manifest.json'),
  check('Run Config', '00_input/run_config.json'),
  // Stage 1: Input
  check('Input Manifest', '00_input/input_manifest.json', false),
  check('User Context', '00_input/user_context.json', false),

  // Stage 2: Context
  check('Ontology', '01_ontology/ontology.json'),
  check('Schema', '01_ontology/schema.json'),

  // Stage 3: Data Processing
  check('Data JSON', '02_processed/data.json', false),
  check('Analysis Plan', '02_processed/analysis_plan.md', false),
  check('Cleaned Data CSV', '02_processed/cleaned_data.csv', false),
  check('Cleaned Data JSON', '02_processed/cleaned_data.json', false),
  check('Scenario Classification', '02_processed/scenario_classification.json'),
  check('Feature Summary', '02_processed/feature_summary.json'),
  check('Validate Report', '02_processed/validate_report.json'),
  check('Anomaly Report', '02_processed/anomaly_report.json'),
  check('Physics Check', '02_processed/physics_check.json', false),
  check('Causal Evidence Map', '02_processed/causal_evidence_map.json', false),
  check('Data Quality Report', '02_processed/data_quality_report.json', false),
  check('Data Analysis Conclusion', '02_processed/data_analysis_conclusion.json'),
  check('Plot Manifest', '03_figures/plot_manifest.json'),
  check('Visual Analysis', '03_figures/visual_analysis.json'),
  check('Image Captions', '03_figures/image_captions.json'),
  conditionalFigureCheck(),

  // Stage 4: Diagnosis
  check('Diagnosis', '04_diagnostics/diagnosis.json'),
  check('Evidence', '04_diagnostics/evidence.json'),
  check('Confidence', '04_diagnostics/confidence.json'),
  check('Reasoning Chain', '04_diagnostics/reasoning_chain.json'),

  // Stage 5: Judge
  check('Judge Feedback', '05_review/judge_feedback.json', false),

  // Stage 6: Report
  check('Report', 'report.md', false),
  check('Run Summary', 'run_summary.json', false),

  // Stage 7: Optimizer
  check('Optimizer', 'optimizer.md', false),
  check('Evidence Closure Report', 'evidence_closure_report.json', false),
];

const schemaChecks = [
  validate('Ontology', 'schemas/ontology_schema.json', '01_ontology/ontology.json'),
  validate('Scenario Classification', 'schemas/scenario_classification_schema.json', '02_processed/scenario_classification.json'),
  validate('Feature Evidence Map', 'schemas/causal_evidence_map_schema.json', '02_processed/causal_evidence_map.json', false),
  validate('Anomaly Report', 'schemas/anomaly_report_schema.json', '02_processed/anomaly_report.json'),
  validate('Data Analysis Conclusion', 'schemas/data_analysis_conclusion_schema.json', '02_processed/data_analysis_conclusion.json'),
  validate('Visual Analysis (VLM)', 'schemas/visual_analysis_schema.json', '03_figures/visual_analysis.json'),
  validate('Image Captions (VLM)', 'schemas/image_captions_schema.json', '03_figures/image_captions.json', false),
  validateVisualExecutionProof(),
  validate('Diagnosis', 'schemas/diagnosis_schema.json', '04_diagnostics/diagnosis.json'),
  validate('Evidence', 'schemas/evidence_schema.json', '04_diagnostics/evidence.json'),
  validate('Confidence', 'schemas/confidence_schema.json', '04_diagnostics/confidence.json'),
  validate('Reasoning Chain', 'schemas/reasoning_chain_schema.json', '04_diagnostics/reasoning_chain.json'),
  validate('Judge Feedback', 'schemas/judge_feedback_schema.json', '05_review/judge_feedback.json', false),
  validate('Run Summary', 'schemas/run_summary_schema.json', 'run_summary.json', false),
  validateDeliveryContract(),
  validatePipelineLog('Pipeline Event Log'),
  validateEvidenceClosure('Evidence Closure'),
  validateDiagnosticQuality('Diagnostic Quality Contract')
];

// Count figures
let figureCount = 0;
const figuresDir = join(runDir, '03_figures');
if (fs.existsSync(figuresDir)) {
  try {
    const entries = fs.readdirSync(figuresDir);
    figureCount = entries.filter(f => f.endsWith('.png')).length;
  } catch (_) {}
}

const allChecks = checks.concat(schemaChecks);
const missing = allChecks.filter(c => c.status.startsWith('MISSING'));
const invalid = allChecks.filter(c => c.status.startsWith('INVALID') || c.status === 'SCHEMA MISSING');
const criticalMissing = missing.filter(c => c.critical);
const criticalInvalid = invalid.filter(c => c.critical);
const warnings = missing.filter(c => !c.critical);
const validationWarnings = invalid.filter(c => !c.critical);

const report = {
  run_dir: runDir,
  verified_at: new Date().toISOString(),
  figure_count: figureCount,
  integrity_check: criticalMissing.length === 0 && criticalInvalid.length === 0 ? 'PASS' : 'FAIL',
  summary: {
    total_checks: allChecks.length,
    ok: allChecks.length - missing.length - invalid.length,
    missing_critical: criticalMissing.length,
    invalid_critical: criticalInvalid.length,
    missing_optional: warnings.length,
    invalid_optional: validationWarnings.length,
    figures_generated: figureCount
  },
  critical_gaps: criticalMissing.concat(criticalInvalid).map(c => ({ file: c.path, stage: c.label, status: c.status })),
  details: allChecks
};

try {
  execFileSync('node', [
    join(skillPath, 'scripts', 'append-pipeline-event.mjs'),
    runDir,
    '--event',
    'artifact_check_complete',
    '--agent',
    'main-agent',
    '--step',
    'present',
    '--status',
    report.integrity_check,
    '--data',
    JSON.stringify({ summary: report.summary })
  ], {
    stdio: ['ignore', 'pipe', 'pipe']
  });
} catch (_) {}

console.log(JSON.stringify(report, null, 2));
process.exit(report.integrity_check === 'PASS' ? 0 : 1);
