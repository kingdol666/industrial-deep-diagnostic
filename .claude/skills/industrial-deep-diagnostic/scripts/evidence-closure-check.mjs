#!/usr/bin/env node
// evidence-closure-check.mjs — Verify that the diagnosis closes the loop from
// process evidence -> ontology/physics interpretation -> dual-drive diagnosis
// -> review/report handoff.
//
// Usage:
//   node evidence-closure-check.mjs <run_dir> [--write]

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
const shouldWrite = args.includes('--write');

if (!runDir) {
  console.error('Usage: node evidence-closure-check.mjs <run_dir> [--write]');
  process.exit(1);
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function exists(pathLike) {
  return fs.existsSync(pathLike);
}

function nonEmptyArray(value) {
  return Array.isArray(value) && value.length > 0;
}

function nonEmptyObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0;
}

function addIssue(issues, severity, code, message, detail = undefined) {
  issues.push({ severity, code, message, detail });
}

const paths = {
  anomaly: join(runDir, '02_processed', 'anomaly_report.json'),
  dataConclusion: join(runDir, '02_processed', 'data_analysis_conclusion.json'),
  diagnosis: join(runDir, '04_diagnostics', 'diagnosis.json'),
  evidence: join(runDir, '04_diagnostics', 'evidence.json'),
  validate: join(runDir, '02_processed', 'validate_report.json'),
  visual: join(runDir, '03_figures', 'visual_analysis.json'),
  judge: join(runDir, '05_review', 'judge_feedback.json'),
  report: join(runDir, 'report.md'),
  summary: join(runDir, 'run_summary.json')
};

const anomaly = readJson(paths.anomaly, {});
const dataConclusion = readJson(paths.dataConclusion, {});
const diagnosis = readJson(paths.diagnosis, {});
const evidence = readJson(paths.evidence, {});
const judge = readJson(paths.judge, {});
const validateReport = readJson(paths.validate, {});
const visual = readJson(paths.visual, {});
const runSummary = readJson(paths.summary, {});
const reportText = exists(paths.report) ? fs.readFileSync(paths.report, 'utf8') : '';

const issues = [];
const dataViewMode =
  dataConclusion.adaptive_decision_audit?.data_view_mode ||
  anomaly.summary?.data_view_mode ||
  anomaly.dual_drive_analysis?.data_view_mode ||
  'unknown';
const dualDriveApplicable = dataViewMode === 'process_plus_inspection' ||
  diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === true;

const processFluctuationPresent = nonEmptyObject(anomaly.process_parameter_fluctuation);
const diagnosisProcessPresent =
  diagnosis.process_fluctuation_analysis?.analysis_performed === true &&
  nonEmptyArray(diagnosis.process_fluctuation_analysis?.key_process_findings);

if (!processFluctuationPresent) {
  addIssue(
    issues,
    'critical',
    'PROCESS_FLUCTUATION_INPUT_MISSING',
    'anomaly_report.json 缺少 process_parameter_fluctuation，无法证明纯工艺波动分析入口存在。'
  );
}

if (!diagnosisProcessPresent) {
  addIssue(
    issues,
    'critical',
    'PROCESS_FLUCTUATION_DIAG_MISSING',
    'diagnosis.json 缺少有效的 process_fluctuation_analysis，纯工艺波动诊断未闭环。'
  );
}

const dualDriveLinksPresent = nonEmptyArray(anomaly.dual_drive_analysis?.cross_domain_links);
const diagnosisDualDrivePresent =
  diagnosis.integrated_dual_drive_analysis?.analysis_performed === true &&
  nonEmptyArray(diagnosis.integrated_dual_drive_analysis?.process_to_quality_links);

if (dualDriveApplicable && !dualDriveLinksPresent) {
  addIssue(
    issues,
    'critical',
    'DUAL_DRIVE_INPUT_MISSING',
    'anomaly_report.json 缺少 dual_drive_analysis.cross_domain_links，无法证明工艺+检测双驱动入口存在。'
  );
}

if (dualDriveApplicable && !diagnosisDualDrivePresent) {
  addIssue(
    issues,
    'critical',
    'DUAL_DRIVE_DIAG_MISSING',
    'diagnosis.json 缺少 integrated_dual_drive_analysis 或其关键链路为空，双驱动诊断未闭环。'
  );
}

if (!dualDriveApplicable) {
  const dualDriveMarkedNotApplicable =
    diagnosis.integrated_dual_drive_analysis?.has_quality_or_inspection_targets === false ||
    // data_view_mode not process_plus_inspection means dual-drive not applicable
    (dataConclusion.adaptive_decision_audit?.data_view_mode &&
     dataConclusion.adaptive_decision_audit.data_view_mode !== 'process_plus_inspection');
  if (!dualDriveMarkedNotApplicable) {
    addIssue(
      issues,
      'critical',
      'DUAL_DRIVE_NA_PROOF_MISSING',
      '当前数据模式不适用双驱动分析，但 diagnosis 或 data_analysis_conclusion 未明确记录不适用原因。'
    );
  }
}

// Ontology-physics bridge: validated_correlations.pairs[].physics (behavior_match/governing_law merged from ontology)
const v2OntologyBridge =
  nonEmptyArray(dataConclusion.validated_correlations?.pairs) &&
  dataConclusion.validated_correlations.pairs.some((p) => p?.physics?.behavior_match || p?.physics?.governing_law);
const ontologyBridgePresent =
  v2OntologyBridge &&
  (nonEmptyArray(diagnosis.process_fluctuation_analysis?.ontology_physics_reasoning) ||
    (Array.isArray(diagnosis.hypotheses?.surviving) &&
      diagnosis.hypotheses.surviving.some((item) => nonEmptyArray(item?.physical_logic_chain))));

if (!ontologyBridgePresent) {
  addIssue(
    issues,
    'critical',
    'ONTOLOGY_PHYSICS_BRIDGE_MISSING',
    '本体/行业知识到诊断物理链条的桥接不足，无法证明统计发现被物理语义正确消化。'
  );
}

const validationCarryForwardPresent =
  exists(paths.validate) &&
  (nonEmptyArray(evidence.evidence_inventory?.validation_evidence) ||
    nonEmptyArray(judge.validation_findings_cited) ||
    nonEmptyArray(judge.blocking_issues) ||
    nonEmptyArray(judge.warnings));

if (!validationCarryForwardPresent) {
  addIssue(
    issues,
    'critical',
    'VALIDATION_CARRY_FORWARD_MISSING',
    'validate_report 的关键约束没有被 evidence.json 或 judge_feedback.json 明确承接。'
  );
}

const visualCarryForwardPresent =
  exists(paths.visual) &&
  nonEmptyArray(visual.visual_observations) &&
  nonEmptyArray(evidence.evidence_inventory?.visual_evidence) &&
  nonEmptyArray(diagnosis.hypotheses?.surviving?.flatMap((item) => item.visual_evidence?.vlm_observations || []));

if (!visualCarryForwardPresent) {
  addIssue(
    issues,
    'warning',
    'VISUAL_EVIDENCE_CARRY_FORWARD_WEAK',
    'visual_analysis 的观察未充分闭环到 evidence.json 或 surviving hypotheses.visual_evidence。'
  );
}

const supportedEvidenceSources = [
  ...((diagnosis.hypotheses?.surviving || []).flatMap((item) => item.supporting_evidence || [])),
  ...(evidence.evidence_inventory?.numerical_evidence || []),
  ...(evidence.evidence_inventory?.visual_evidence || []),
  ...(evidence.evidence_inventory?.physical_evidence || [])
];

const invalidSources = supportedEvidenceSources
  .map((item) => item.source)
  .filter((source) => typeof source === 'string' && source.startsWith('0'))
  .filter((source) => !exists(join(runDir, source)));

if (invalidSources.length > 0) {
  addIssue(
    issues,
    'critical',
    'EVIDENCE_SOURCE_BROKEN',
    '部分 evidence source 指向的文件不存在，证据链不可追溯。',
    { invalid_sources: Array.from(new Set(invalidSources)) }
  );
}

const reportSectionsPresent =
  reportText.includes('纯工艺波动诊断') &&
  (reportText.includes('双重分析') || reportText.includes('双驱动')) &&
  reportText.includes('数据分析专家结论');

if (!reportSectionsPresent) {
  addIssue(
    issues,
    'warning',
    'REPORT_CLOSURE_SECTION_WEAK',
    'report.md 没有明确呈现纯工艺波动诊断、双驱动分析、数据分析专家结论三类闭环章节。'
  );
}

if (runSummary.primary_finding && diagnosis.primary_finding && runSummary.primary_finding !== diagnosis.primary_finding) {
  addIssue(
    issues,
    'warning',
    'RUN_SUMMARY_MISMATCH',
    'run_summary.json 的 primary_finding 与 diagnosis.json 不一致，最终交付摘要存在漂移。'
  );
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
    process_fluctuation_entry_present: processFluctuationPresent,
    process_fluctuation_diagnosed: diagnosisProcessPresent,
    data_view_mode: dataViewMode,
    dual_drive_applicable: dualDriveApplicable,
    dual_drive_entry_present: dualDriveLinksPresent,
    dual_drive_diagnosed: dualDriveApplicable ? diagnosisDualDrivePresent : false,
    ontology_bridge_present: ontologyBridgePresent,
    validation_carried_forward: validationCarryForwardPresent,
    visual_evidence_carried_forward: visualCarryForwardPresent,
    report_sections_present: !!reportSectionsPresent
  },
  issues
};

if (shouldWrite) {
  fs.writeFileSync(join(runDir, 'evidence_closure_report.json'), `${JSON.stringify(report, null, 2)}\n`);
}

console.log(JSON.stringify(report, null, 2));
process.exit(report.status === 'PASS' ? 0 : 1);
