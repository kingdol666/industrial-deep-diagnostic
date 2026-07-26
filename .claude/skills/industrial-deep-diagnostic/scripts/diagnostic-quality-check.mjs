#!/usr/bin/env node
// diagnostic-quality-check.mjs — Cross-artifact quality gate for excellent
// data + ontology + physics driven diagnosis.
//
// Usage:
//   node diagnostic-quality-check.mjs <run_dir>

import fs from 'fs';
import { join } from 'path';

const runDir = process.argv[2];

if (!runDir) {
  console.error('Usage: node diagnostic-quality-check.mjs <run_dir>');
  process.exit(1);
}

function readJson(relPath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(join(runDir, relPath), 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function exists(relPath) {
  return fs.existsSync(join(runDir, relPath));
}

function nonEmptyArray(value) {
  return Array.isArray(value) && value.length > 0;
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function addIssue(issues, severity, code, message, detail = undefined) {
  issues.push({ severity, code, message, ...(detail === undefined ? {} : { detail }) });
}

const diagnosis = readJson('04_diagnostics/diagnosis.json', {});
const evidence = readJson('04_diagnostics/evidence.json', {});
const anomaly = readJson('02_processed/anomaly_report.json', {});
const dataConclusion = readJson('02_processed/data_analysis_conclusion.json', {});
const physics = readJson('02_processed/physics_check.json', {});
const visual = readJson('03_figures/visual_analysis.json', {});
const judge = readJson('05_review/judge_feedback.json', {});

const issues = [];
const surviving = diagnosis.hypotheses?.surviving || [];
const physicalChecks = physics?.physical_checks && typeof physics.physical_checks === 'object'
  ? physics.physical_checks
  : {};

if (!nonEmptyArray(surviving)) {
  addIssue(issues, 'critical', 'NO_SURVIVING_HYPOTHESES', 'diagnosis.json 没有 surviving hypotheses，无法形成可审计诊断。');
}

for (const hyp of surviving) {
  const id = hyp.id || '(unknown)';
  const proof = hyp.ontology_data_physics_proof;

  if (!proof || typeof proof !== 'object') {
    addIssue(issues, 'critical', 'HYPOTHESIS_PROOF_MISSING', `假设 ${id} 缺少 ontology_data_physics_proof。`);
    continue;
  }

  if (['WEAK', 'CONTRADICTED'].includes(proof.overall_proof_strength) && hyp.confidence > 50) {
    addIssue(
      issues,
      'critical',
      'CONFIDENCE_EXCEEDS_PROOF',
      `假设 ${id} 的 proof_strength=${proof.overall_proof_strength}，但 confidence=${hyp.confidence}，置信度超过证据强度。`
    );
  }

  if (!nonEmptyArray(proof.data_sources)) {
    addIssue(issues, 'critical', 'PROOF_DATA_SOURCE_MISSING', `假设 ${id} 的本体-数据-物理证明缺少 data_sources。`);
  }
  if (!nonEmptyArray(proof.physics_sources)) {
    addIssue(issues, 'critical', 'PROOF_PHYSICS_SOURCE_MISSING', `假设 ${id} 的本体-数据-物理证明缺少 physics_sources。`);
  }
  if (!nonEmptyArray(proof.ontology_sources)) {
    addIssue(issues, 'critical', 'PROOF_ONTOLOGY_SOURCE_MISSING', `假设 ${id} 的本体-数据-物理证明缺少 ontology_sources。`);
  }
  if (!nonEmptyArray(hyp.physical_logic_chain)) {
    addIssue(issues, 'critical', 'PHYSICAL_CHAIN_MISSING', `假设 ${id} 缺少 physical_logic_chain。`);
  }
  if (!nonEmptyArray(hyp.falsification_conditions)) {
    addIssue(issues, 'critical', 'FALSIFICATION_MISSING', `假设 ${id} 缺少 falsification_conditions。`);
  }
}

const dualDriveInputs = anomaly.dual_drive_analysis?.cross_domain_links || [];
const dualDriveOutputs = diagnosis.integrated_dual_drive_analysis?.process_to_quality_links || [];
const dataViewMode =
  dataConclusion.adaptive_decision_audit?.data_view_mode ||
  anomaly.summary?.data_view_mode ||
  anomaly.dual_drive_analysis?.data_view_mode ||
  'unknown';
const dualDriveApplicable = dataViewMode === 'process_plus_inspection' ||
  diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === true;

if (diagnosis.integrated_dual_drive_analysis?.analysis_performed === true && dualDriveApplicable) {
  if (!nonEmptyArray(dualDriveInputs)) {
    addIssue(
      issues,
      'critical',
      'DUAL_DRIVE_OUTPUT_WITHOUT_INPUT',
      'diagnosis.json 声称执行双驱动诊断，但 anomaly_report.json 缺少 cross_domain_links。'
    );
  }
  if (!nonEmptyArray(dualDriveOutputs)) {
    addIssue(
      issues,
      'critical',
      'DUAL_DRIVE_LINKS_MISSING',
      'integrated_dual_drive_analysis.process_to_quality_links 为空，无法证明工艺异常进入质量链。'
    );
  }
}

if (!dualDriveApplicable) {
  const markedNotApplicable =
    diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === false ||
    dataConclusion.analysis_coverage_matrix?.process_inspection_dual_drive?.status === 'not_applicable' ||
    // V2: data_view_mode not process_plus_inspection means dual-drive not applicable
    (dataConclusion.schema_version === '2.0' &&
     dataConclusion.adaptive_decision_audit?.data_view_mode &&
     dataConclusion.adaptive_decision_audit.data_view_mode !== 'process_plus_inspection');
  if (!markedNotApplicable) {
    addIssue(
      issues,
      'critical',
      'DUAL_DRIVE_NA_NOT_RECORDED',
      '当前数据模式不适用双驱动诊断，但 diagnosis 或 data_analysis_conclusion 没有明确记录不适用。'
    );
  }
}

const checksPerformed = physics?.checks_performed ??
  physics?.summary?.checks_performed ??
  anomaly.physics_check_summary?.checks_performed ??
  Object.keys(physicalChecks).length;
if (Number(checksPerformed) === 0 && !exists('02_processed/physics_manual_verification.md')) {
  addIssue(
    issues,
    'critical',
    'PHYSICS_ZERO_CHECKS_WITHOUT_MANUAL_VERIFICATION',
    'physics_check.py 没有执行自动物理检查，但缺少 physics_manual_verification.md 的 L1-L5 手工量级证明。'
  );
}

const visualProvenance = visual.analysis_provenance || {};
if (exists('03_figures/visual_analysis.json')) {
  if (visual.observation_mode === 'skeleton_pre_vlm') {
    addIssue(issues, 'critical', 'VLM_LEFT_AS_SKELETON', 'visual_analysis.json 仍为 skeleton_pre_vlm。');
  }
  if (visualProvenance.source_agent !== 'vlm-visual-analyzer') {
    addIssue(issues, 'critical', 'VLM_SOURCE_NOT_PROVEN', 'visual_analysis.json 未证明由 vlm-visual-analyzer 生成。');
  }
}

if (!nonEmptyArray(evidence.evidence_inventory?.physical_evidence)) {
  addIssue(issues, 'critical', 'PHYSICAL_EVIDENCE_INVENTORY_MISSING', 'evidence.json 缺少 physical_evidence。');
}

if (exists('05_review/judge_feedback.json')) {
  const verdict = judge.verdict || judge.overall_verdict;
  const score = judge.overall_score ?? judge.score;
  if (typeof score === 'number' && score < 90 && String(verdict).toLowerCase() === 'pass') {
    addIssue(issues, 'critical', 'JUDGE_PASS_WITH_LOW_SCORE', `judge score=${score} 但 verdict=PASS。`);
  }
}

const criticalIssues = issues.filter((item) => item.severity === 'critical');
const report = {
  run_dir: runDir,
  checked_at: new Date().toISOString(),
  status: criticalIssues.length === 0 ? 'PASS' : 'FAIL',
  summary: {
    critical_issues: criticalIssues.length,
    warnings: issues.length - criticalIssues.length,
    surviving_hypotheses: surviving.length,
    data_view_mode: dataViewMode,
    dual_drive_applicable: dualDriveApplicable,
    dual_drive_inputs: dualDriveInputs.length,
    dual_drive_outputs: dualDriveOutputs.length,
    physics_checks_performed: checksPerformed ?? null
  },
  issues
};

console.log(JSON.stringify(report, null, 2));
process.exit(report.status === 'PASS' ? 0 : 1);
