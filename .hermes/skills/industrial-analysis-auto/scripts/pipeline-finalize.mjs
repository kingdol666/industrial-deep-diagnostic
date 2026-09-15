#!/usr/bin/env node
// pipeline-finalize.mjs — Unified pipeline finalization and validation.
// Merges: evidence-closure-check.mjs + artifact-check.mjs + finalize-run-artifacts.mjs
//
// Usage:
//   node pipeline-finalize.mjs <run_dir> [skill_path]
//   Returns exit 0 if all checks pass, 1 otherwise.
//   Writes pipeline_finalize_report.json to <run_dir>.

import fs from 'fs';
import { join } from 'path';
import { execFileSync } from 'child_process';

const args = process.argv.slice(2);
const runDir = args[0];
const skillPath = args[1] || '.';

if (!runDir) {
  console.error('Usage: node pipeline-finalize.mjs <run_dir> [skill_path]');
  process.exit(1);
}

// ── helpers ──────────────────────────────────────────────────────
function exists(p) { return fs.existsSync(join(runDir, p)); }
function readJson(relPath, fallback = null) {
  try { return JSON.parse(fs.readFileSync(join(runDir, relPath), 'utf8')); }
  catch (_) { return fallback; }
}
function readJsonIfExists(relPath) { return readJson(relPath, null); }
function nonEmptyArray(v) { return Array.isArray(v) && v.length > 0; }
function nonEmptyObject(v) { return !!v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length > 0; }
function statSizeKb(relPath) {
  try { return (fs.statSync(join(runDir, relPath)).size / 1024).toFixed(1); }
  catch (_) { return '0.0'; }
}

// Shared-script resolution (same convention as artifact-check.mjs)
const SHARED_SCRIPTS_DIR = join(skillPath, '..', '..', 'shared', 'scripts');
const parentSkillsDir = join(skillPath, '..');
const SCRIPT_TO_SKILL = {
  'judge-gate-check.mjs': 'industrial-judge',
  'diagnostic-quality-check.mjs': 'industrial-diagnostician',
  'pipeline-log-check.mjs': 'industrial-analysis-auto',
};
const SHARED_SCRIPTS = ['validate.mjs', 'append-pipeline-event.mjs', 'uv_env_setup.mjs', 'convert.mjs'];
function resolveScript(scriptName) {
  if (SHARED_SCRIPTS.includes(scriptName)) return join(SHARED_SCRIPTS_DIR, scriptName);
  const owner = SCRIPT_TO_SKILL[scriptName];
  if (owner) return join(parentSkillsDir, owner, 'scripts', scriptName);
  return join(skillPath, 'scripts', scriptName);
}

// Quick check helper
function check(label, filePath, critical = true) {
  const fullPath = join(runDir, filePath);
  if (!fs.existsSync(fullPath)) {
    return { label, path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }
  const kb = statSizeKb(filePath);
  return { label, path: filePath, status: `OK (${kb} KB)`, critical };
}

// run a script, return stdout
function runScript(scriptName, extraArgs = []) {
  return execFileSync('node', [resolveScript(scriptName), runDir, ...extraArgs], {
    stdio: ['ignore', 'pipe', 'pipe']
  }).toString();
}

// append pipeline event (fire-and-forget)
function logEvent(event, extraArgs = []) {
  try {
    execFileSync('node', [resolveScript('append-pipeline-event.mjs'), runDir, '--event', event, '--agent', 'main-agent', '--step', 'present', ...extraArgs], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
  } catch (_) {}
}

// ── results accumulators ─────────────────────────────────────────
let figureCount = 0;
const figuresDir = join(runDir, '03_figures');
if (fs.existsSync(figuresDir)) {
  try { figureCount = fs.readdirSync(figuresDir).filter(f => f.endsWith('.png')).length; }
  catch (_) {}
}

const steps = {
  inventory: null,
  schema: null,
  closure: null,
  judge: null,
  events: null,
};

// ================================================================
// STEP 1: Artifact Inventory (~45 core checks)
// ================================================================

function runInventory() {
  const invChecks = [
    // ── Core runtime ──
    check('Run Manifest', 'run_manifest.json'),
    check('Run Config', '00_input/run_config.json'),

    // ── Stage 1: Input ──
    check('Input Manifest', '00_input/input_manifest.json', false),
    check('User Context', '00_input/user_context.json', false),

    // ── Stage 2: Ontology ──
    check('Ontology', '01_ontology/ontology.json'),
    check('Schema', '01_ontology/schema.json'),
    check('Clarification Needed', '00_input/clarification_needed.json', false),

    // ── Stage 2 RAG extras (grouped: 4 optional files → 1 check) ──
    (() => {
      const ragFiles = ['00_input/extracted_knowledge.json', '01_ontology/rag_deep_understanding.json'];
      const missing = ragFiles.filter(f => !exists(f));
      if (missing.length === 0) return { label: 'RAG Knowledge Artifacts', path: ragFiles.join(', '), status: 'OK', critical: false };
      if (missing.length === ragFiles.length) return { label: 'RAG Knowledge Artifacts', path: ragFiles.join(', '), status: 'MISSING', critical: false };
      return { label: 'RAG Knowledge Artifacts', path: missing.join(', '), status: 'PARTIAL', critical: false };
    })(),

    // ── Stage 3: Data Processing ──
    check('Data JSON', '02_processed/data.json', false),
    check('Analysis Plan', '02_processed/analysis_plan.md', false),
    check('Scenario Classification', '02_processed/scenario_classification.json'),
    check('Feature Summary', '02_processed/feature_summary.json'),
    check('Validate Report', '02_processed/validate_report.json'),
    check('Anomaly Report', '02_processed/anomaly_report.json'),
    check('Analysis Parameter Selection', '02_processed/analysis_parameter_selection.json'),
    check('Data Analysis Conclusion', '02_processed/data_analysis_conclusion.json'),

    // ── Stage 3 optional processing files (grouped) ──
    (() => {
      const dpOpt = [
        '02_processed/cleaned_data.csv', '02_processed/cleaned_data.json',
        '02_processed/data_quality_report.json', '02_processed/physics_check.json',
        '02_processed/causal_evidence_map.json', '02_processed/time_lag_analysis.json',
        '02_processed/production_regime_filter.json'
      ];
      const present = dpOpt.filter(f => exists(f));
      const missing = dpOpt.filter(f => !exists(f));
      return {
        label: 'Data Processing Optional Artifacts',
        path: `${present.length}/${dpOpt.length} present`,
        status: present.length >= 3 ? `OK (${present.length} files, missing: ${missing.map(m => m.split('/').pop()).join(',')})` : `WEAK (${present.length}/${dpOpt.length})`,
        critical: false
      };
    })(),

    // ── Stage 3.5: Figures & VLM ──
    check('Plot Manifest', '03_figures/plot_manifest.json'),
    check('Visual Analysis', '03_figures/visual_analysis.json'),
    check('Image Captions', '03_figures/image_captions.json'),

    // ── Temporal figure (conditional) ──
    (() => {
      const inputManifest = readJsonIfExists('00_input/input_manifest.json');
      const visual = readJsonIfExists('03_figures/visual_analysis.json');
      const plotManifest = readJsonIfExists('03_figures/plot_manifest.json');
      const hasTimeCol = Boolean(inputManifest && (inputManifest.time_column || inputManifest.data_profile?.time_column));
      const temporalPlot = Array.isArray(plotManifest?.plots)
        ? plotManifest.plots.find(p => {
          const h = [p.file, p.filename, p.title, p.plot_type, p.description].filter(Boolean).join(' ').toLowerCase();
          return /temporal|time|timeline|aligned|process_health|时序|时间|对齐|工艺健康/.test(h);
        }) : null;
      const tpath = temporalPlot ? (temporalPlot.file || temporalPlot.filename || '') : '';
      const normalized = tpath.startsWith('03_figures/') ? tpath : (tpath ? `03_figures/${tpath}` : '03_figures/<temporal-plot>');

      if (hasTimeCol) {
        if (tpath && exists(normalized)) return { label: 'Temporal / Process-Health Figure', path: normalized, status: 'VALID', critical: true };
        return { label: 'Temporal / Process-Health Figure', path: normalized, status: 'MISSING (time column exists but no temporal figure)', critical: true };
      }
      const na = visual && visual.time_alignment_applicable === false;
      const reason = visual && (visual.not_applicable_reason || visual.cross_parameter_temporal_alignment?.not_applicable_reason);
      if (na && reason) return { label: 'Temporal / Process-Health Figure', path: normalized, status: `NOT_APPLICABLE (${String(reason).slice(0, 160)})`, critical: false };
      return { label: 'Temporal / Process-Health Figure', path: normalized, status: 'MISSING (expected NA proof or figure)', critical: true };
    })(),

    // ── Stage 4: Diagnosis ──
    check('Diagnosis', '04_diagnostics/diagnosis.json'),
    check('Evidence', '04_diagnostics/evidence.json'),
    check('Confidence', '04_diagnostics/confidence.json'),
    check('Reasoning Chain', '04_diagnostics/reasoning_chain.json'),

    // ── Stage 5: Judge & Audit ──
    check('Judge Feedback', '05_review/judge_feedback.json'),
    check('Pre-Audit Report', '05_review/optimizer_preflight.md', false),

    // ── Stage 6-7: Report & Optimizer ──
    check('Report', 'report.md', false),
    check('Run Summary', 'run_summary.json'),
    check('Optimizer', 'optimizer.md', false),
    check('Evidence Closure Report', 'evidence_closure_report.json', false),

    // ── Stage 8: HTML Visualization ──
    check('Diagnostic HTML Report', 'diagnostic-report.html'),
    check('HTML Review', '05_review/html_review.json'),
  ];

  const missing = invChecks.filter(c => c.status.startsWith('MISSING'));
  const invalid = invChecks.filter(c => c.status.startsWith('INVALID') || c.status === 'SCHEMA MISSING');
  const critMissing = missing.filter(c => c.critical);
  const critInvalid = invalid.filter(c => c.critical);

  return {
    ok: invChecks.filter(c => !c.status.startsWith('MISSING') && !c.status.startsWith('INVALID') && c.status !== 'SCHEMA MISSING').length,
    total: invChecks.length,
    missing_critical: critMissing.length,
    invalid_critical: critInvalid.length,
    missing_optional: missing.filter(c => !c.critical).length,
    invalid_optional: invalid.filter(c => !c.critical).length,
    figures_generated: figureCount,
    critical_gaps: critMissing.concat(critInvalid).map(c => ({ file: c.path, stage: c.label, status: c.status })),
    details: invChecks,
  };
}

steps.inventory = runInventory();

// ================================================================
// STEP 2: Batch Schema Validation
// ================================================================

function runSchemaValidation() {
  const schemaList = [
    { label: 'Ontology', schema: 'schemas/ontology_schema.json', file: '01_ontology/ontology.json', critical: true },
    { label: 'Scenario Classification', schema: 'schemas/scenario_classification_schema.json', file: '02_processed/scenario_classification.json', critical: true },
    { label: 'Anomaly Report', schema: 'schemas/anomaly_report_schema.json', file: '02_processed/anomaly_report.json', critical: true },
    { label: 'Analysis Parameter Selection', schema: 'schemas/analysis_parameter_selection_schema.json', file: '02_processed/analysis_parameter_selection.json', critical: true },
    { label: 'Data Analysis Conclusion', schema: 'schemas/data_analysis_conclusion_schema.json', file: '02_processed/data_analysis_conclusion.json', critical: true },
    { label: 'Visual Analysis (VLM)', schema: 'schemas/visual_analysis_schema.json', file: '03_figures/visual_analysis.json', critical: true },
    { label: 'Image Captions', schema: 'schemas/image_captions_schema.json', file: '03_figures/image_captions.json', critical: false },
    { label: 'Causal Evidence Map', schema: 'schemas/causal_evidence_map_schema.json', file: '02_processed/causal_evidence_map.json', critical: false },
    { label: 'Diagnosis', schema: 'schemas/diagnosis_schema.json', file: '04_diagnostics/diagnosis.json', critical: true },
    { label: 'Evidence', schema: 'schemas/evidence_schema.json', file: '04_diagnostics/evidence.json', critical: true },
    { label: 'Confidence', schema: 'schemas/confidence_schema.json', file: '04_diagnostics/confidence.json', critical: true },
    { label: 'Reasoning Chain', schema: 'schemas/reasoning_chain_schema.json', file: '04_diagnostics/reasoning_chain.json', critical: true },
    { label: 'Judge Feedback', schema: 'schemas/judge_feedback_schema.json', file: '05_review/judge_feedback.json', critical: true },
    { label: 'Run Summary', schema: 'schemas/run_summary_schema.json', file: 'run_summary.json', critical: true },
  ];

  const results = schemaList.map(({ label, schema, file, critical }) => {
    const schemaFull = join(skillPath, schema);
    const fileFull = join(runDir, file);
    if (!fs.existsSync(fileFull)) {
      return { label: `${label} Schema`, path: file, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
    }
    if (!fs.existsSync(schemaFull)) {
      return { label: `${label} Schema`, path: schema, status: 'SCHEMA MISSING', critical };
    }
    try {
      execFileSync('node', [join(SHARED_SCRIPTS_DIR, 'validate.mjs'), schemaFull, fileFull], { stdio: ['ignore', 'pipe', 'pipe'] });
      return { label: `${label} Schema`, path: file, status: 'VALID', critical };
    } catch (err) {
      const msg = (err.stderr || err.stdout || '').toString().trim();
      return { label: `${label} Schema`, path: file, status: `INVALID${msg ? `: ${msg.slice(0, 250)}` : ''}`, critical };
    }
  });

  const critFail = results.filter(r => r.critical && (r.status.startsWith('INVALID') || r.status.startsWith('MISSING')));
  return {
    ok: results.filter(r => r.status === 'VALID').length,
    total: results.length,
    failed_critical: critFail.length,
    details: results,
  };
}

steps.schema = runSchemaValidation();

// ================================================================
// STEP 3: Evidence Closure Check (4 core rules)
// ================================================================

function runClosureCheck() {
  const anomaly = readJsonIfExists('02_processed/anomaly_report.json') || {};
  const dataConclusion = readJsonIfExists('02_processed/data_analysis_conclusion.json') || {};
  const diagnosis = readJsonIfExists('04_diagnostics/diagnosis.json') || {};
  const evidence = readJsonIfExists('04_diagnostics/evidence.json') || {};
  const judge = readJsonIfExists('05_review/judge_feedback.json') || {};
  const visual = readJsonIfExists('03_figures/visual_analysis.json') || {};
  const runSummary = readJsonIfExists('run_summary.json') || {};
  const reportText = exists('report.md') ? fs.readFileSync(join(runDir, 'report.md'), 'utf8') : '';

  const issues = [];

  function addIssue(severity, code, message, detail) {
    issues.push({ severity, code, message, detail });
  }

  const dataViewMode =
    dataConclusion.adaptive_decision_audit?.data_view_mode ||
    anomaly.summary?.data_view_mode ||
    anomaly.dual_drive_analysis?.data_view_mode ||
    'unknown';
  const dualDriveApplicable = dataViewMode === 'process_plus_inspection' ||
    diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === true;

  // Rule 1: Process fluctuation entry → diagnosis closure
  const processFluctuationPresent = nonEmptyObject(anomaly.process_parameter_fluctuation);
  const diagnosisProcessPresent =
    diagnosis.process_fluctuation_analysis?.analysis_performed === true &&
    nonEmptyArray(diagnosis.process_fluctuation_analysis?.key_process_findings);

  if (!processFluctuationPresent) {
    addIssue('critical', 'PROCESS_FLUCTUATION_INPUT_MISSING',
      'anomaly_report.json missing process_parameter_fluctuation — cannot prove process-only analysis entry.');
  }
  if (!diagnosisProcessPresent) {
    addIssue('critical', 'PROCESS_FLUCTUATION_DIAG_MISSING',
      'diagnosis.json missing valid process_fluctuation_analysis — process diagnosis not closed.');
  }

  // Rule 2: Dual-drive entry → diagnosis closure
  const dualDriveLinksPresent = nonEmptyArray(anomaly.dual_drive_analysis?.cross_domain_links);
  const diagnosisDualDrivePresent =
    diagnosis.integrated_dual_drive_analysis?.analysis_performed === true &&
    nonEmptyArray(diagnosis.integrated_dual_drive_analysis?.process_to_quality_links);

  if (dualDriveApplicable && !dualDriveLinksPresent) {
    addIssue('critical', 'DUAL_DRIVE_INPUT_MISSING',
      'anomaly_report.json missing dual_drive_analysis.cross_domain_links — cannot prove dual-drive entry.');
  }
  if (dualDriveApplicable && !diagnosisDualDrivePresent) {
    addIssue('critical', 'DUAL_DRIVE_DIAG_MISSING',
      'diagnosis.json missing integrated_dual_drive_analysis or its key links are empty.');
  }
  if (!dualDriveApplicable) {
    const naMarked =
      diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === false ||
      dataConclusion.analysis_coverage_matrix?.process_inspection_dual_drive?.status === 'not_applicable';
    if (!naMarked) {
      addIssue('critical', 'DUAL_DRIVE_NA_PROOF_MISSING',
        'Dual-drive not applicable but diagnosis/data_conclusion fail to record why.');
    }
  }

  // Rule 3: Ontology/physics bridge closure
  const ontologyBridgePresent =
    nonEmptyArray(dataConclusion.ontology_industry_interpretation) &&
    (nonEmptyArray(diagnosis.process_fluctuation_analysis?.ontology_physics_reasoning) ||
      (Array.isArray(diagnosis.hypotheses?.surviving) &&
        diagnosis.hypotheses.surviving.some(item => nonEmptyArray(item?.physical_logic_chain))));

  if (!ontologyBridgePresent) {
    addIssue('critical', 'ONTOLOGY_PHYSICS_BRIDGE_MISSING',
      'Ontology/industry knowledge bridge to diagnosis physical chain insufficient.');
  }

  // Rule 4: Validation & visual carry-forward
  const validationCarryForward =
    exists('02_processed/validate_report.json') &&
    (nonEmptyArray(evidence.evidence_inventory?.validation_evidence) ||
      nonEmptyArray(judge.validation_findings_cited) ||
      nonEmptyArray(judge.blocking_issues) ||
      nonEmptyArray(judge.warnings));

  if (!validationCarryForward) {
    addIssue('critical', 'VALIDATION_CARRY_FORWARD_MISSING',
      'validate_report constraints not cited in evidence.json or judge_feedback.json.');
  }

  const visualCarryForward =
    exists('03_figures/visual_analysis.json') &&
    nonEmptyArray(visual.visual_observations) &&
    nonEmptyArray(evidence.evidence_inventory?.visual_evidence) &&
    nonEmptyArray(diagnosis.hypotheses?.surviving?.flatMap(item => item.visual_evidence?.vlm_observations || []));

  if (!visualCarryForward) {
    addIssue('warning', 'VISUAL_EVIDENCE_CARRY_FORWARD_WEAK',
      'visual_analysis observations not fully closed to evidence.json or surviving hypotheses.');
  }

  // Evidence source integrity
  const supportedSources = [
    ...((diagnosis.hypotheses?.surviving || []).flatMap(item => item.supporting_evidence || [])),
    ...(evidence.evidence_inventory?.numerical_evidence || []),
    ...(evidence.evidence_inventory?.visual_evidence || []),
    ...(evidence.evidence_inventory?.physical_evidence || []),
  ];
  // Normalize evidence sources: entries may combine multiple refs ("a + b"),
  // carry #field selectors, or inline annotations "(note)".
  const normalizedSources = supportedSources
    .map(item => String(item.source || ''))
    .flatMap(s => s.split(/\s*\+\s*/))
    .map(s => s.split('#')[0])
    // dotted field access "file.json.some_field" (legacy evidence format)
    .map(s => s.replace(/(\.(?:json|md|csv|py|png))\.[A-Za-z_][A-Za-z0-9_]*$/, '$1'))
    .map(s => s.replace(/\s*\(.*\)\s*$/, '').trim())
    .filter(s => /^(0[1-5]_)|^0[0-9]_/.test(s) || /^(0[1-5]\/)/.test(s) || /^0[0-9]\//.test(s));
  const invalidSources = [...new Set(normalizedSources.filter(s => !exists(s)))];

  if (invalidSources.length > 0) {
    addIssue('critical', 'EVIDENCE_SOURCE_BROKEN',
      'Evidence source files missing — chain untraceable.',
      { invalid_sources: [...new Set(invalidSources)] });
  }

  // Report sections closure
  // Current reporter contract: 9-section pyramid. Closure requires an evidence
  // appendix and a recommendations section (old 14-section wording relaxed).
  const reportSectionsPresent =
    (reportText.includes('证据附录') || reportText.includes('证据') && reportText.includes('附录')) &&
    (reportText.includes('建议与后续') || reportText.includes('建议'));

  if (!reportSectionsPresent) {
    addIssue('warning', 'REPORT_CLOSURE_SECTION_WEAK',
      'report.md missing process-only diagnosis, dual-drive, or data expert conclusion sections.');
  }

  // Run summary consistency
  if (runSummary.primary_finding && diagnosis.primary_finding && runSummary.primary_finding !== diagnosis.primary_finding) {
    addIssue('warning', 'RUN_SUMMARY_MISMATCH',
      'run_summary.json primary_finding differs from diagnosis.json — final deliverable drift.');
  }

  const criticalIssues = issues.filter(i => i.severity === 'critical');
  const warnings = issues.filter(i => i.severity === 'warning');

  // Write evidence_closure_report.json (replaces --write flag)
  const report = {
    run_dir: runDir,
    checked_at: new Date().toISOString(),
    status: criticalIssues.length === 0 ? 'PASS' : 'FAIL',
    summary: {
      critical_issues: criticalIssues.length,
      warnings: warnings.length,
      process_fluctuation_entry_present: processFluctuationPresent,
      process_fluctuation_diagnosed: diagnosisProcessPresent,
      data_view_mode: dataViewMode,
      dual_drive_applicable: dualDriveApplicable,
      dual_drive_entry_present: dualDriveLinksPresent,
      dual_drive_diagnosed: dualDriveApplicable ? diagnosisDualDrivePresent : false,
      ontology_bridge_present: ontologyBridgePresent,
      validation_carried_forward: validationCarryForward,
      visual_evidence_carried_forward: visualCarryForward,
      report_sections_present: !!reportSectionsPresent,
    },
    issues,
  };
  try { fs.writeFileSync(join(runDir, 'evidence_closure_report.json'), JSON.stringify(report, null, 2) + '\n'); } catch (_) {}

  return {
    status: report.status,
    summary: report.summary,
    critical_issues: criticalIssues.length,
    warnings: warnings.length,
    details: issues,
  };
}

steps.closure = runClosureCheck();

// ================================================================
// STEP 4: Judge Gate Cross-Audit
// ================================================================

function runJudgeCrossAudit() {
  const judge = readJsonIfExists('05_review/judge_feedback.json');
  const results = { checks: [], passed: true };

  // Judge gate basic existence + quality
  if (!judge) {
    results.checks.push({ label: 'Judge Feedback Exists', status: 'MISSING', critical: true });
    results.passed = false;
    return results;
  }
  results.checks.push({ label: 'Judge Feedback Exists', status: 'OK', critical: true });

  // Verdict must be "pass"
  if (judge.verdict !== 'pass') {
    results.checks.push({ label: 'Judge Verdict', status: `FAIL (verdict=${judge.verdict}, need "pass")`, critical: true });
    results.passed = false;
  } else {
    results.checks.push({ label: 'Judge Verdict', status: 'PASS', critical: true });
  }

  // Score sanity (judge_feedback schema field is overall_score)
  const judgeScore = typeof judge.score === 'number' ? judge.score : judge.overall_score;
  if (typeof judgeScore !== 'number' || judgeScore < 0 || judgeScore > 100) {
    results.checks.push({ label: 'Judge Score', status: `INVALID (score=${judgeScore})`, critical: true });
    results.passed = false;
  } else if (judgeScore < 90) {
    results.checks.push({ label: 'Judge Score', status: `WARN (score=${judgeScore} < 90)`, critical: false });
  } else {
    results.checks.push({ label: 'Judge Score', status: `OK (${judgeScore})`, critical: true });
  }

  // Blocking issues should be empty
  if (nonEmptyArray(judge.blocking_issues)) {
    results.checks.push({ label: 'Judge Blocking Issues', status: `BLOCKING (${judge.blocking_issues.length} issues)`, critical: true, detail: judge.blocking_issues.slice(0, 5) });
    results.passed = false;
  } else {
    results.checks.push({ label: 'Judge Blocking Issues', status: 'CLEAR', critical: true });
  }

  // Dimension coverage: the judge schema records 10 scored dimensions either as
  // `criteria_scores` (name->score) or `dimension_scores` (object) or `checks` (array).
  const dimCount = Array.isArray(judge.checks) ? judge.checks.length
    : (typeof judge.criteria_scores === 'object' && judge.criteria_scores !== null) ? Object.keys(judge.criteria_scores).length
    : (typeof judge.dimension_scores === 'object' && judge.dimension_scores !== null) ? Object.keys(judge.dimension_scores).length : 0;
  if (dimCount < 5) {
    results.checks.push({ label: 'Judge Checks Coverage', status: `INSUFFICIENT (${dimCount} items, need ≥5)`, critical: true });
    results.passed = false;
  } else {
    results.checks.push({ label: 'Judge Checks Coverage', status: `OK (${dimCount} dimensions)`, critical: true });
  }

  // Cross-check: judge validation_findings_cited vs evidence
  const evidence = readJsonIfExists('04_diagnostics/evidence.json') || {};
  const judgeValidation = nonEmptyArray(judge.validation_findings_cited);
  const evidenceValidation = nonEmptyArray(evidence.evidence_inventory?.validation_evidence);
  if (judgeValidation && !evidenceValidation) {
    results.checks.push({ label: 'Judge-Evidence Validation Cross-Check', status: 'WARN (judge cites validation but evidence.json lacks validation_evidence)', critical: false });
  }

  // Cross-check: judge warnings vs diagnosis repairs
  const diagnosis = readJsonIfExists('04_diagnostics/diagnosis.json') || {};
  if (nonEmptyArray(judge.warnings) && !diagnosis.repair_history) {
    results.checks.push({ label: 'Judge Warnings vs Diagnosis Repairs', status: 'WARN (judge has warnings but diagnosis lacks repair_history)', critical: false });
  }

  return results;
}

steps.judge = runJudgeCrossAudit();

// ================================================================
// STEP 5: Pipeline Event Archive + Pipeline-Log-Check
// ================================================================

function runEventArchive() {
  const results = { checks: [], passed: true };

  // 5a: Run pipeline-log-check
  let logDetail = null;
  try {
    const stdout = runScript('pipeline-log-check.mjs');
    logDetail = JSON.parse(stdout);
    results.checks.push({ label: 'Pipeline Log Check', status: 'VALID', detail: logDetail });
  } catch (err) {
    const stdout = (err.stdout || '').toString().trim();
    try { logDetail = JSON.parse(stdout); } catch (_) {}
    results.checks.push({ label: 'Pipeline Log Check', status: `INVALID${(err.stderr || '').toString().trim() ? `: ${err.stderr.toString().trim().slice(0, 200)}` : ''}`, critical: true, detail: logDetail });
    results.passed = false;
  }

  // 5b: Validate delivery contract (run_manifest.json present step)
  const manifest = readJsonIfExists('run_manifest.json');
  if (manifest) {
    const presentStep = Array.isArray(manifest.steps) ? manifest.steps.find(s => s.step === 'present') : null;
    if (!presentStep || !['completed', 'completed_with_errors'].includes(presentStep.status || '')) {
      results.checks.push({ label: 'Delivery Contract (present step)', path: 'run_manifest.json', status: 'INVALID (present step not completed)', critical: true });
      results.passed = false;
    } else {
      results.checks.push({ label: 'Delivery Contract (present step)', path: 'run_manifest.json', status: 'VALID', critical: true });
    }

    // Required runtime artifacts
    const required = manifest.delivery_contract?.required_runtime_artifacts || [];
    const missingA = required.filter(p => !exists(p));
    if (missingA.length > 0) {
      results.checks.push({ label: 'Delivery Contract (artifacts)', path: 'run_manifest.json', status: `INVALID (missing: ${missingA.join(', ')})`, critical: true });
      results.passed = false;
    } else {
      results.checks.push({ label: 'Delivery Contract (artifacts)', path: 'run_manifest.json', status: 'VALID', critical: true });
    }
  }

  // 5c: HTML delivery validation
  (() => {
    const htmlPath = join(runDir, 'diagnostic-report.html');
    const reviewPath = join(runDir, '05_review', 'html_review.json');
    const optOutPath = join(runDir, '00_input', 'html_opt_out');

    if (fs.existsSync(optOutPath)) {
      results.checks.push({ label: 'HTML Delivery', status: 'SKIPPED (user opt-out)', critical: false });
      return;
    }
    const htmlIssues = [];
    if (!fs.existsSync(htmlPath)) {
      htmlIssues.push('diagnostic-report.html missing');
    } else {
      const sz = fs.statSync(htmlPath).size;
      if (sz < 5120) htmlIssues.push(`diagnostic-report.html too small: ${sz} bytes (min 5120)`);
      try {
        const snip = fs.readFileSync(htmlPath, 'utf-8');
        if (!snip.includes('<html')) htmlIssues.push('missing <html> tag');
        if (!snip.toLowerCase().includes('echarts')) htmlIssues.push('missing ECharts reference');
      } catch (e) { htmlIssues.push(`unreadable: ${e.message}`); }
    }
    if (!fs.existsSync(reviewPath)) {
      htmlIssues.push('05_review/html_review.json missing');
    } else {
      try {
        const review = JSON.parse(fs.readFileSync(reviewPath, 'utf-8'));
        if (review.verdict !== 'pass') htmlIssues.push(`html_review verdict="${review.verdict}", expected "pass"`);
        if (typeof review.overall_score !== 'number' || review.overall_score < 0 || review.overall_score > 100) htmlIssues.push(`html_review overall_score invalid: ${review.overall_score}`);
        if (!Array.isArray(review.checks) || review.checks.length < 5) htmlIssues.push(`html_review checks insufficient: ${Array.isArray(review.checks) ? review.checks.length : 0} items`);
        if (nonEmptyArray(review.blocking_issues)) htmlIssues.push(`unresolved blocking issues: ${review.blocking_issues.slice(0, 3).join('; ')}`);
      } catch (e) { htmlIssues.push(`html_review.json parse failed: ${e.message}`); }
    }
    if (htmlIssues.length > 0) {
      results.checks.push({ label: 'HTML Delivery', status: `INVALID: ${htmlIssues.join('; ').slice(0, 300)}`, critical: true });
      results.passed = false;
    } else {
      results.checks.push({ label: 'HTML Delivery', status: 'VALID', critical: true });
    }
  })();

  // 5d: Optimizer content contract
  (() => {
    const optPath = join(runDir, 'optimizer.md');
    if (!fs.existsSync(optPath)) {
      results.checks.push({ label: 'Optimizer Content', path: 'optimizer.md', status: 'MISSING', critical: false });
      return;
    }
    const content = fs.readFileSync(optPath, 'utf-8').toLowerCase();
    const patterns = [
      { name: 'audit overview', re: [/audit overview/i, /审计总览|独立验算|判定/] },
      { name: 'statistical verification', re: [/statistical verification/i, /统计.*(核验|基础|验证)/] },
      { name: 'physics verification', re: [/physics verification/i, /物理.*(核验|真实|验证)/] },
      { name: 'verdict', re: [/verdict/i, /判定|终审|ENDORSED|CONDITIONAL|REJECTED/] },
    ];
    const missingSecs = patterns.filter(p => !p.re.some(r => r.test(content))).map(p => p.name);
    const evidenceTerms = ['evidence', 'diagnosis', 'ontology', 'physics', 'visual', '数据', '诊断', '本体', '物理', '证据', '图像'];
    const hasGrounding = evidenceTerms.filter(t => content.includes(t.toLowerCase())).length >= 3;
    if (missingSecs.length > 0 || !hasGrounding) {
      const reasons = [];
      if (missingSecs.length > 0) reasons.push(`missing sections: ${missingSecs.join(', ')}`);
      if (!hasGrounding) reasons.push('insufficient evidence grounding terms');
      results.checks.push({ label: 'Optimizer Content', path: 'optimizer.md', status: `INVALID: ${reasons.join('; ')}`, critical: true });
      results.passed = false;
    } else {
      results.checks.push({ label: 'Optimizer Content', path: 'optimizer.md', status: 'VALID', critical: true });
    }
  })();

  // 5e: Report content contract
  (() => {
    const rp = join(runDir, 'report.md');
    if (!fs.existsSync(rp)) {
      results.checks.push({ label: 'Report Content', path: 'report.md', status: 'MISSING', critical: false });
      return;
    }
    const content = fs.readFileSync(rp, 'utf-8').trim();
    const lines = content ? content.split('\n') : [];
    const nonEmpty = lines.filter(l => l.trim());
    const h2s = nonEmpty.filter(l => /^##\s+/.test(l.trim()));
    const issues = [];
    // Current reporter contract: 9-section pyramid (Chinese). Required anchors:
    // title, executive summary, statistical findings, root-cause conclusion,
    // evidence appendix.
    const required = [
      { name: 'title', re: /^#\s+.*(工业诊断报告|Industrial Diagnostic Report)/m },
      { name: 'executive summary', re: /^##\s+1\.\s*执行摘要/m },
      { name: 'statistical findings', re: /^##\s+4\.\s*统计分析发现|^##\s+14\.\s*统计验证与置信度评估/m },
      { name: 'root cause conclusion', re: /^##\s+6\.\s*根因结论|^##\s+12\.\s*诊断结果/m },
      { name: 'evidence appendix', re: /^##\s+7\.\s*(证据附录|证据全景)|^##\s+11\.\s*可视化证据/m },
    ];
    const missingRe = required.filter(r => !r.re.test(content)).map(r => r.name);
    if (!content) issues.push('report.md is empty');
    if (nonEmpty.length < 40) issues.push(`too few non-empty lines: ${nonEmpty.length} < 40`);
    if (h2s.length < 8) issues.push(`too few level-2 sections: ${h2s.length} < 8`);
    if (missingRe.length > 0) issues.push(`missing sections: ${missingRe.join(', ')}`);
    if (issues.length > 0) {
      results.checks.push({ label: 'Report Content', path: 'report.md', status: `INVALID: ${issues.join('; ').slice(0, 300)}`, critical: true });
      results.passed = false;
    } else {
      results.checks.push({ label: 'Report Content', path: 'report.md', status: 'VALID', critical: true });
    }
  })();

  // 5f: Append final pipeline events
  logEvent('pipeline_finalize_complete', ['--status', results.passed ? 'PASS' : 'FAIL',
    '--data', JSON.stringify({
      inventory_ok: steps.inventory.ok,
      inventory_total: steps.inventory.total,
      schema_ok: steps.schema.ok,
      schema_total: steps.schema.total,
      closure_status: steps.closure.status,
      judge_passed: steps.judge.passed,
    })
  ]);
  logEvent('run_completed', ['--status', results.passed ? 'PASS' : 'FAIL']);

  return results;
}

steps.events = runEventArchive();

// ================================================================
// COMPILE FINAL REPORT
// ================================================================

const inventoryPass = steps.inventory.missing_critical === 0 && steps.inventory.invalid_critical === 0;
const schemaPass = steps.schema.failed_critical === 0;
const closurePass = steps.closure.status === 'PASS';
const judgePass = steps.judge.passed;
const eventsPass = steps.events.passed;

const overallPass = inventoryPass && schemaPass && closurePass && judgePass && eventsPass;

const finalReport = {
  run_dir: runDir,
  verified_at: new Date().toISOString(),
  overall: overallPass ? 'PASS' : 'FAIL',
  steps_summary: {
    inventory: { pass: inventoryPass, ok: steps.inventory.ok, total: steps.inventory.total, missing_critical: steps.inventory.missing_critical, invalid_critical: steps.inventory.invalid_critical },
    schema: { pass: schemaPass, ok: steps.schema.ok, total: steps.schema.total, failed_critical: steps.schema.failed_critical },
    closure: { pass: closurePass, status: steps.closure.status, critical_issues: steps.closure.critical_issues, warnings: steps.closure.warnings },
    judge_cross_audit: { pass: judgePass, checks: steps.judge.checks },
    event_archive: { pass: eventsPass, checks: steps.events.checks },
  },
  figures_generated: figureCount,
  inventory_details: steps.inventory.details,
  schema_details: steps.schema.details,
  closure_details: steps.closure.details,
};

// Write final report
try { fs.writeFileSync(join(runDir, 'pipeline_finalize_report.json'), JSON.stringify(finalReport, null, 2) + '\n'); } catch (_) {}
console.log(JSON.stringify(finalReport, null, 2));
process.exit(overallPass ? 0 : 1);
