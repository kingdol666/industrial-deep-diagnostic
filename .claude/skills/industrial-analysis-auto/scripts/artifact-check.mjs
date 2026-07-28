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


// Cross-skill script resolution: scripts referenced by the orchestrator
// may live in dependent skill directories, not the orchestrator's own scripts/.
const parentSkillsDir = join(skillPath, '..');
const SCRIPT_TO_SKILL = {
  'judge-gate-check.mjs': 'industrial-judge',
  'diagnostic-quality-check.mjs': 'industrial-diagnostician',
  'normalize-anomaly-report.mjs': 'industrial-data-processor',
  'synthesize-data-analysis-conclusion.mjs': 'industrial-data-processor',
  'synthesize-run-summary.mjs': 'industrial-reporter',
};
function resolveScript(scriptName) {
  const owner = SCRIPT_TO_SKILL[scriptName];
  if (owner) return join(parentSkillsDir, owner, 'scripts', scriptName);
  return join(skillPath, 'scripts', scriptName);
}

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

function validateOptimizerMarkdown(critical = true) {
  const filePath = 'optimizer.md';
  const fullPath = join(runDir, filePath);
  if (!fs.existsSync(fullPath)) {
    return { label: 'Optimizer Content Contract', path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }

  const content = fs.readFileSync(fullPath, 'utf-8');
  const normalized = content.toLowerCase();
  const requiredPatterns = [
    {
      name: 'scenario-specific process optimization plan',
      patterns: [/##\s*10\.\s*scenario-specific process optimization plan/i, /场景特异性.*优化方案/]
    },
    {
      name: 'current scene problems and improvement opportunities',
      patterns: [/##\s*11\.\s*current scene problems and improvement opportunities/i, /当前场景.*问题.*改善/]
    },
    {
      name: 'next-step diagnostic confirmation plan',
      patterns: [/##\s*12\.\s*next-step diagnostic confirmation plan/i, /下一步.*诊断.*确认计划/]
    },
    {
      name: 'action classification',
      patterns: [/##\s*13\.\s*action classification/i, /行动分类/]
    }
  ];

  const missing = requiredPatterns
    .filter(({ patterns }) => !patterns.some((pattern) => pattern.test(content)))
    .map(({ name }) => name);

  const evidenceWords = [
    'evidence',
    'diagnosis',
    'ontology',
    'physics',
    'visual',
    '数据',
    '诊断',
    '本体',
    '物理',
    '证据',
    '图像'
  ];
  const hasEvidenceGrounding = evidenceWords.filter((word) => normalized.includes(word.toLowerCase())).length >= 3;

  if (missing.length > 0 || !hasEvidenceGrounding) {
    const issues = [];
    if (missing.length > 0) issues.push(`missing sections: ${missing.join(', ')}`);
    if (!hasEvidenceGrounding) issues.push('insufficient evidence/data/ontology/physics grounding terms');
    return {
      label: 'Optimizer Content Contract',
      path: filePath,
      status: `INVALID: ${issues.join('; ').slice(0, 300)}`,
      critical
    };
  }

  return { label: 'Optimizer Content Contract', path: filePath, status: 'VALID', critical };
}

function validateReportContentContract(critical = true) {
  const filePath = 'report.md';
  const fullPath = join(runDir, filePath);
  if (!fs.existsSync(fullPath)) {
    return { label: 'Report Content Contract', path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }

  const content = fs.readFileSync(fullPath, 'utf-8');
  const trimmed = content.trim();
  const lines = trimmed.length === 0 ? [] : trimmed.split('\n');
  const nonEmptyLines = lines.filter((line) => line.trim().length > 0);
  const level2Sections = nonEmptyLines.filter((line) => /^##\s+/.test(line.trim()));
  const requiredPatterns = [
    { name: 'title', pattern: /^#\s+Industrial Diagnostic Report/m },
    { name: 'executive summary', pattern: /^##\s+1\.\s*执行摘要/m },
    { name: 'visual evidence section', pattern: /^##\s+11\.\s*可视化证据/m },
    { name: 'diagnostic findings section', pattern: /^##\s+12\.\s*诊断结果/m },
    { name: 'confidence section', pattern: /^##\s+14\.\s*统计验证与置信度评估/m }
  ];

  const missingPatterns = requiredPatterns
    .filter(({ pattern }) => !pattern.test(content))
    .map(({ name }) => name);
  const issues = [];
  if (trimmed.length === 0) issues.push('report.md is empty');
  if (nonEmptyLines.length < 40) issues.push(`too few non-empty lines: ${nonEmptyLines.length} < 40`);
  if (level2Sections.length < 8) issues.push(`too few level-2 sections: ${level2Sections.length} < 8`);
  if (missingPatterns.length > 0) issues.push(`missing required sections: ${missingPatterns.join(', ')}`);

  const summary = readJsonIfExists('run_summary.json');
  if (summary?.report_stats) {
    const stats = summary.report_stats;
    if (Number.isFinite(stats.total_lines) && stats.total_lines > 0 && nonEmptyLines.length === 0) {
      issues.push('run_summary reports report lines but report.md is empty');
    }
    if (Number.isFinite(stats.sections_count) && stats.sections_count > 0 && level2Sections.length === 0) {
      issues.push('run_summary reports sections_count > 0 but report.md has no sections');
    }
  }

  return {
    label: 'Report Content Contract',
    path: filePath,
    status: issues.length === 0 ? 'VALID' : `INVALID: ${issues.join('; ').slice(0, 300)}`,
    critical
  };
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
    execFileSync('node', [resolveScript('validate.mjs'), schemaFullPath, fileFullPath], {
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
    const stdout = execFileSync('node', [resolveScript('pipeline-log-check.mjs'), runDir], {
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
  const plotManifest = readJsonIfExists('03_figures/plot_manifest.json');
  const hasTimeColumn = Boolean(inputManifest && inputManifest.time_column);
  const temporalPlot = Array.isArray(plotManifest?.plots)
    ? plotManifest.plots.find((plot) => {
      const haystack = [
        plot.file,
        plot.filename,
        plot.title,
        plot.plot_type,
        plot.description
      ].filter(Boolean).join(' ').toLowerCase();
      return /temporal|time|timeline|aligned|process_health|时序|时间|对齐|工艺健康/.test(haystack);
    })
    : null;
  const temporalPath = temporalPlot
    ? (temporalPlot.file || temporalPlot.filename || temporalPlot.path || '')
    : '';
  const normalizedTemporalPath = temporalPath && temporalPath.startsWith('03_figures/')
    ? temporalPath
    : (temporalPath ? `03_figures/${temporalPath}` : '03_figures/<temporal-or-process-health-plot>');

  if (hasTimeColumn) {
    if (temporalPath && exists(normalizedTemporalPath)) {
      return {
        label: 'Temporal / Process-Health Figure',
        path: normalizedTemporalPath,
        status: 'VALID',
        critical: true
      };
    }
    return {
      label: 'Temporal / Process-Health Figure',
      path: normalizedTemporalPath,
      status: 'MISSING (time column exists but plot_manifest has no existing temporal/aligned/process-health figure)',
      critical: true
    };
  }

  const notApplicable = visualAnalysis && visualAnalysis.time_alignment_applicable === false;
  const reason = visualAnalysis && (visualAnalysis.not_applicable_reason || visualAnalysis.cross_parameter_temporal_alignment?.not_applicable_reason);

  if (notApplicable && reason) {
    return {
      label: 'Temporal / Process-Health Figure',
      path: normalizedTemporalPath,
      status: `NOT_APPLICABLE (${String(reason).slice(0, 160)})`,
      critical: false
    };
  }

  return {
    label: 'Temporal / Process-Health Figure',
    path: normalizedTemporalPath,
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

  return {
    label: 'Delivery Contract',
    path: 'run_manifest.json',
    status: issues.length === 0 ? 'VALID' : `INVALID: ${issues.join('; ').slice(0, 300)}`,
    critical: true
  };
}

function validateEvidenceClosure(label, critical = true) {
  try {
    const stdout = execFileSync('node', [resolveScript('evidence-closure-check.mjs'), runDir], {
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
    const stdout = execFileSync('node', [resolveScript('diagnostic-quality-check.mjs'), runDir], {
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

function validateJudgeGate(label, critical = true) {
  try {
    const stdout = execFileSync('node', [resolveScript('judge-gate-check.mjs'), runDir], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
    return {
      label,
      path: '05_review/judge_feedback.json',
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
      path: '05_review/judge_feedback.json',
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

function validateDataProcessorExpertContract() {
  const conclusion = readJsonIfExists('02_processed/data_analysis_conclusion.json');
  const planPath = join(runDir, '02_processed', 'analysis_plan.md');
  const planText = fs.existsSync(planPath) ? fs.readFileSync(planPath, 'utf-8') : '';
  const issues = [];

  if (!conclusion) {
    return {
      label: 'Data Processor Expert Contract',
      path: '02_processed/data_analysis_conclusion.json',
      status: 'MISSING (critical)',
      critical: true
    };
  }

  const audit = conclusion.adaptive_decision_audit || {};
  const coverage = conclusion.analysis_coverage_matrix || {};
  const selectedAnalyses = Array.isArray(audit.selected_analyses) ? audit.selected_analyses : [];
  const skippedAnalyses = Array.isArray(audit.skipped_or_not_applicable) ? audit.skipped_or_not_applicable : [];
  const custom = conclusion.expert_custom_analysis || {};
  const scriptInventory = Array.isArray(custom.script_inventory) ? custom.script_inventory : [];

  if (!['process_plus_inspection', 'process_only', 'inspection_only', 'unknown'].includes(audit.data_view_mode)) {
    issues.push('adaptive_decision_audit.data_view_mode is missing or invalid');
  }
  if (selectedAnalyses.length === 0) {
    issues.push('adaptive_decision_audit.selected_analyses is empty');
  }
  if (selectedAnalyses.length + skippedAnalyses.length < 3) {
    issues.push('too few adaptive analysis decisions recorded');
  }

  for (const key of ['pure_process_analysis', 'process_inspection_dual_drive', 'grouping_confounding', 'temporal_regime_event', 'scenario_specific']) {
    if (!coverage[key]?.status || !coverage[key]?.summary) {
      issues.push(`analysis_coverage_matrix.${key} missing status or summary`);
    }
  }

  if (!planText.trim()) {
    issues.push('analysis_plan.md is missing or empty');
  } else {
    if (!/Adaptive Decision Audit/i.test(planText) && !/自适应.*决策/.test(planText)) {
      issues.push('analysis_plan.md lacks Adaptive Decision Audit section');
    }
    if (!/Analysis Coverage Matrix/i.test(planText) && !/覆盖矩阵/.test(planText)) {
      issues.push('analysis_plan.md lacks Analysis Coverage Matrix section');
    }
  }

  const referencedArtifacts = new Set();
  for (const item of selectedAnalyses) {
    for (const relPath of item.evidence_artifacts || []) referencedArtifacts.add(relPath);
  }
  for (const item of Object.values(coverage)) {
    for (const relPath of item?.evidence_artifacts || []) referencedArtifacts.add(relPath);
  }
  const missingArtifacts = Array.from(referencedArtifacts)
    .filter((relPath) => relPath && !relPath.includes('*') && !exists(relPath));
  if (missingArtifacts.length > 0) {
    issues.push(`referenced evidence artifacts missing: ${missingArtifacts.slice(0, 6).join(', ')}`);
  }

  const missingScripts = scriptInventory
    .map((item) => item.script)
    .filter((relPath) => relPath && !exists(relPath));
  if (missingScripts.length > 0) {
    issues.push(`declared custom scripts missing: ${missingScripts.slice(0, 6).join(', ')}`);
  }
  if (custom.custom_scripts_written === true && scriptInventory.length === 0) {
    issues.push('custom_scripts_written=true but script_inventory is empty');
  }

  return {
    label: 'Data Processor Expert Contract',
    path: '02_processed/data_analysis_conclusion.json',
    status: issues.length === 0 ? 'VALID' : `INVALID: ${issues.join('; ').slice(0, 300)}`,
    critical: true
  };
}

function validateHTMLDeliveryContract() {
  const htmlPath = join(runDir, 'diagnostic-report.html');
  const reviewPath = join(runDir, '05_review', 'html_review.json');
  const optOutPath = join(runDir, '00_input', 'html_opt_out');

  // User explicitly opted out of HTML generation → skip validation gracefully
  if (fs.existsSync(optOutPath)) {
    return {
      label: 'HTML Delivery Contract',
      path: 'diagnostic-report.html + 05_review/html_review.json (opt-out)',
      status: 'SKIPPED (user opted out of HTML visualization)',
      critical: false
    };
  }

  const issues = [];

  // 1. Validate diagnostic-report.html exists and >= 5KB
  if (!fs.existsSync(htmlPath)) {
    issues.push('diagnostic-report.html missing');
  } else {
    const stat = fs.statSync(htmlPath);
    const sizeBytes = stat.size;
    if (sizeBytes < 5120) {
      issues.push(`diagnostic-report.html too small: ${sizeBytes} bytes (min 5120)`);
    }
    // Check for essential structural markers
    try {
      const snippet = fs.readFileSync(htmlPath, 'utf-8').slice(0, 8192);
      if (!snippet.includes('<html')) issues.push('diagnostic-report.html missing <html> tag');
      if (!snippet.includes('echarts')) issues.push('diagnostic-report.html missing ECharts reference');
    } catch (e) {
      issues.push(`diagnostic-report.html unreadable: ${e.message}`);
    }
  }

  // 2. Validate 05_review/html_review.json exists, has verdict "pass", and schema validates
  if (!fs.existsSync(reviewPath)) {
    issues.push('05_review/html_review.json missing');
  } else {
    try {
      const review = JSON.parse(fs.readFileSync(reviewPath, 'utf-8'));
      if (review.verdict !== 'pass') {
        issues.push(`html_review verdict is "${review.verdict}", expected "pass"`);
      }
      if (typeof review.overall_score !== 'number' || review.overall_score < 0 || review.overall_score > 100) {
        issues.push(`html_review overall_score invalid: ${review.overall_score}`);
      }
      if (!Array.isArray(review.checks) || review.checks.length < 5) {
        issues.push(`html_review checks insufficient: ${Array.isArray(review.checks) ? review.checks.length : 0} items (min 5)`);
      }
      // Verify no blocking issues remain
      if (Array.isArray(review.blocking_issues) && review.blocking_issues.length > 0) {
        issues.push(`html_review has unresolved blocking issues: ${review.blocking_issues.slice(0, 3).join('; ')}`);
      }
    } catch (e) {
      issues.push(`05_review/html_review.json failed to parse: ${e.message}`);
    }
  }

  return {
    label: 'HTML Delivery Contract',
    path: 'diagnostic-report.html + 05_review/html_review.json',
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
  check('Extracted Knowledge', '00_input/extracted_knowledge.json', false),
  check('Clarification Needed', '01_ontology/clarification_needed.json', false),
  check('RAG Deep Understanding', '00_input/rag_deep_understanding.json', false),

  // Stage 3: Data Processing
  check('Data JSON', '02_processed/data.json', false),
  check('Analysis Plan', '02_processed/analysis_plan.md', false),
  check('Cleaned Data CSV', '02_processed/cleaned_data.csv', false),
  check('Cleaned Data JSON', '02_processed/cleaned_data.json', false),
  check('Scenario Classification', '02_processed/scenario_classification.json'),
  check('Feature Summary', '02_processed/feature_summary.json'),
  check('Validate Report', '02_processed/validate_report.json'),
  check('Anomaly Report', '02_processed/anomaly_report.json'),
  check('Analysis Parameter Selection', '02_processed/analysis_parameter_selection.json'),
  check('Physics Check', '02_processed/physics_check.json', false),
  check('Causal Evidence Map', '02_processed/causal_evidence_map.json', false),
  check('Data Quality Report', '02_processed/data_quality_report.json', false),
  check('Time Lag Analysis', '02_processed/time_lag_analysis.json', false),
  check('Production Regime Filter', '02_processed/production_regime_filter.json', false),
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
  check('Judge Feedback', '05_review/judge_feedback.json'),
  check('Pre-Audit Report', '05_review/optimizer_preflight.md', false),

  // Stage 6: Report
  check('Report', 'report.md', false),
  check('Run Summary', 'run_summary.json'),

  // Stage 7: Optimizer
  check('Optimizer', 'optimizer.md', false),
  check('Evidence Closure Report', 'evidence_closure_report.json', false),

  // Stage 8: HTML Visualization Delivery
  check('Diagnostic HTML Report', 'diagnostic-report.html'),
  check('HTML Review', '05_review/html_review.json'),
];

const schemaChecks = [
  validate('Ontology', 'schemas/ontology_schema.json', '01_ontology/ontology.json'),
  validate('Scenario Classification', 'schemas/scenario_classification_schema.json', '02_processed/scenario_classification.json'),
  validate('Feature Evidence Map', 'schemas/causal_evidence_map_schema.json', '02_processed/causal_evidence_map.json', false),
  validate('Anomaly Report', 'schemas/anomaly_report_schema.json', '02_processed/anomaly_report.json'),
  validate('Analysis Parameter Selection', 'schemas/analysis_parameter_selection_schema.json', '02_processed/analysis_parameter_selection.json'),
  validate('Data Analysis Conclusion', 'schemas/data_analysis_conclusion_schema.json', '02_processed/data_analysis_conclusion.json'),
  validate('Visual Analysis (VLM)', 'schemas/visual_analysis_schema.json', '03_figures/visual_analysis.json'),
  validate('Image Captions (VLM)', 'schemas/image_captions_schema.json', '03_figures/image_captions.json', false),
  validateVisualExecutionProof(),
  validateDataProcessorExpertContract(),
  validate('Diagnosis', 'schemas/diagnosis_schema.json', '04_diagnostics/diagnosis.json'),
  validate('Evidence', 'schemas/evidence_schema.json', '04_diagnostics/evidence.json'),
  validate('Confidence', 'schemas/confidence_schema.json', '04_diagnostics/confidence.json'),
  validate('Reasoning Chain', 'schemas/reasoning_chain_schema.json', '04_diagnostics/reasoning_chain.json'),
  validate('Judge Feedback', 'schemas/judge_feedback_schema.json', '05_review/judge_feedback.json'),
  validateJudgeGate('Judge Final Report Gate'),
  validateReportContentContract(),
  validate('Run Summary', 'schemas/run_summary_schema.json', 'run_summary.json'),
  validateOptimizerMarkdown(),
  validateHTMLDeliveryContract(),
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
    resolveScript('append-pipeline-event.mjs'),
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
