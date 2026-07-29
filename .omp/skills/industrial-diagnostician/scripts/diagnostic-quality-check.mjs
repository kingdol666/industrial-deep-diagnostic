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
const confidence = readJson('04_diagnostics/confidence.json', {});
const reasoningChain = readJson('04_diagnostics/reasoning_chain.json', {});
const anomaly = readJson('02_processed/anomaly_report.json', {});
const dataConclusion = readJson('02_processed/data_analysis_conclusion.json', {});
const physics = readJson('02_processed/physics_check.json', {});
const visual = readJson('03_figures/visual_analysis.json', {});
const judge = readJson('05_review/judge_feedback.json', {});
const ontology = readJson('01_ontology/ontology.json', {});

const issues = [];
const surviving = diagnosis.hypotheses?.surviving || [];
const eliminated = diagnosis.hypotheses?.eliminated || [];
const dt = diagnosis.diagnosis_type || 'UNKNOWN';
const physicalChecks = physics?.physical_checks && typeof physics.physical_checks === 'object'
  ? physics.physical_checks
  : {};

// ----- P1 CHECK 1: COMPETING HYPOTHESES -----
if (!nonEmptyArray(surviving)) {
  addIssue(issues, 'critical', 'NO_SURVIVING_HYPOTHESES', 'diagnosis.json 没有 surviving hypotheses，无法形成可审计诊断。');
} else {
  if (dt === 'DETERMINED') {
    if (!nonEmptyArray(eliminated) || eliminated.length < 2) {
      addIssue(issues, 'critical', 'INSUFFICIENT_ELIMINATED',
        `diagnosis_type=${dt} 但 eliminated ${eliminated ? '仅有' + eliminated.length : '为空'}，需要至少排除 2 个假设。`,
        'DETERMINED 要求至少 2 个假设被排除');
    }
  } else if (dt === 'COMPETING_SET') {
    if (surviving.length < 2) {
      addIssue(issues, 'critical', 'COMPETING_SET_TOO_FEW',
        `diagnosis_type=COMPETING_SET 但 surviving 只有 ${surviving.length} 个。COMPETING_SET 必须 ≥ 2。`,
        'COMPETING_SET 要求至少 2 个存活假设');
    }
    const competingSets = diagnosis.hypotheses?.competing_sets || [];
    if (!nonEmptyArray(competingSets)) {
      addIssue(issues, 'critical', 'COMPETING_SETS_MISSING',
        'diagnosis_type=COMPETING_SET 但缺少 competing_sets 定义。',
        'COMPETING_SET 必须有 competing_sets 块描述每组不可区分的假设');
    }
    const dm = diagnosis.discriminability_matrix || [];
    if (!nonEmptyArray(dm)) {
      addIssue(issues, 'warning', 'DISCRIMINABILITY_MATRIX_MISSING',
        'diagnosis_type=COMPETING_SET 但缺少 discriminability_matrix。');
    }
  }
}

// ----- P1 CHECK 6: PRODUCT STRATIFICATION -----
const hasProductColumn = ontology.parameters?.some(p => p.role === 'grouping');
if (hasProductColumn && !diagnosis.product_stratified_analysis?.has_product_column) {
  addIssue(issues, 'warning', 'PRODUCT_STRATIFICATION_MISSING',
    'ontology 中有 grouping(产品) 参数，但 diagnosis 缺少 product_stratified_analysis。');
}

// ----- P1 CHECK 2: REASONING CHAIN R1-R8 -----
const rChains = reasoningChain.reasoning_chains || [];
const expectedStepIds = [1, 2, 3, 4, 5, 6, 7, 8];
const missingStepIds = expectedStepIds.filter(sid => !rChains.find(c => c.step_id === sid));
if (rChains.length < 8 || missingStepIds.length > 0) {
  addIssue(issues, rChains.length >= 6 ? 'warning' : 'critical', 'REASONING_CHAIN_INCOMPLETE',
    `reasoning_chain 只有 ${rChains.length} 段（需要 8 段），缺失: R${missingStepIds.join(', R')}`,
    '推理链必须包含完整的 R1-R8');
}
// Check each segment has key fields
for (const seg of rChains) {
  if (!nonEmptyArray(seg.inputs)) {
    addIssue(issues, 'warning', `REASONING_R${seg.step_id}_INPUTS_MISSING`,
      `R${seg.step_id} 缺少 inputs 数组。`);
  }
  if (!seg.reasoning || !seg.reasoning.step_by_step) {
    addIssue(issues, 'warning', `REASONING_R${seg.step_id}_REASONING_MISSING`,
      `R${seg.step_id} 缺少 reasoning.step_by_step。`);
  }
  if (!nonEmptyArray(seg.outputs)) {
    addIssue(issues, 'warning', `REASONING_R${seg.step_id}_OUTPUTS_MISSING`,
      `R${seg.step_id} 缺少 outputs。`);
  }
  if (!seg.falsification_condition) {
    addIssue(issues, 'warning', `REASONING_R${seg.step_id}_FALSIFICATION_MISSING`,
      `R${seg.step_id} 缺少 falsification_condition。`);
  }
}

// ----- P1 CHECK 4: CONFIDENCE BREAKDOWN -----
const cBreakdown = confidence.confidence_breakdown || {};
const cHypIds = Object.keys(cBreakdown);
if (cHypIds.length === 0) {
  addIssue(issues, 'critical', 'CONFIDENCE_BREAKDOWN_EMPTY',
    'confidence.json 的 confidence_breakdown 为空，缺少五因素分解。');
} else {
  for (const surv of surviving) {
    const hid = surv.id;
    if (hid && !cBreakdown[hid]) {
      addIssue(issues, 'warning', `CONFIDENCE_H${hid}_MISSING`,
        `假设 ${hid} 在 diagnosis 中存活但 confidence_breakdown 中没有对应条目。`);
    }
  }
  for (const [hid, entry] of Object.entries(cBreakdown)) {
    const ffd = entry.five_factor_breakdown || {};
    const requiredFactors = ['statistical_strength', 'physical_plausibility', 'temporal_evidence', 'absence_of_confounds', 'symptom_completeness'];
    const missingFactors = requiredFactors.filter(f => ffd[f] === undefined || ffd[f] === null);
    if (missingFactors.length > 0) {
      addIssue(issues, 'critical', `CONFIDENCE_${hid}_FACTORS_MISSING`,
        `假设 ${hid} 的五因素分解缺少: ${missingFactors.join(', ')}。`,
        '每个 hypothesis 必须有完整的 5 因素分解');
    }
    // Check score <= max
    const factorMax = { statistical_strength: 25, physical_plausibility: 25, temporal_evidence: 20, absence_of_confounds: 20, symptom_completeness: 10 };
    for (const [fname, fdata] of Object.entries(ffd)) {
      if (fdata && typeof fdata.score === 'number' && fdata.score > factorMax[fname]) {
        addIssue(issues, 'warning', `CONFIDENCE_${hid}_${fname}_EXCEEDS_MAX`,
          `${hid}.${fname} score=${fdata.score} 超过 max=${factorMax[fname]}。`);
      }
    }
  }
}
const adjLog = confidence.adjustment_log || [];
if (!nonEmptyArray(adjLog)) {
  addIssue(issues, 'warning', 'CONFIDENCE_ADJUSTMENT_LOG_EMPTY',
    'confidence.json 的 adjustment_log 为空，所有假设无置信度调整。');
} else {
  for (const adj of adjLog) {
    if (!adj.hypothesis_id || !adj.adjustment || !adj.reason) {
      addIssue(issues, 'warning', 'CONFIDENCE_ADJUSTMENT_INCOMPLETE',
        'adjustment_log 某条缺少 hypothesis_id/adjustment/reason。');
    }
  }
}

// ----- P1 CHECK 5: EVIDENCE -----
const eviInv = evidence.evidence_inventory || {};
if (!nonEmptyArray(eviInv.visual_evidence) && !nonEmptyArray(eviInv.numerical_evidence)) {
  addIssue(issues, 'critical', 'EVIDENCE_INVENTORY_EMPTY',
    'evidence.json 的 visual_evidence 和 numerical_evidence 都为空。');
}
if (!nonEmptyArray(eviInv.validation_evidence)) {
  addIssue(issues, 'warning', 'VALIDATION_EVIDENCE_MISSING',
    'evidence.json 缺少 validation_evidence，无法追踪统计验证结果的传递。');
}
if (!nonEmptyArray(eviInv.physical_evidence)) {
  addIssue(issues, 'warning', 'PHYSICAL_EVIDENCE_MISSING',
    'evidence.json 缺少 physical_evidence。');
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
    dataConclusion.analysis_coverage_matrix?.process_inspection_dual_drive?.status === 'not_applicable';
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
const warnings = issues.filter((item) => item.severity === 'warning');
const report = {
  run_dir: runDir,
  checked_at: new Date().toISOString(),
  status: criticalIssues.length === 0 ? 'PASS' : 'FAIL',
  summary: {
    critical_issues: criticalIssues.length,
    warnings: warnings.length,
    surviving_hypotheses: surviving.length,
    eliminated_hypotheses: eliminated.length,
    reasoning_chain_segments: rChains.length,
    confidence_breakdown_hypotheses: cHypIds.length,
    adjustment_log_entries: adjLog.length,
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
