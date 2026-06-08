#!/usr/bin/env node
// synthesize-bottom-line-summary.mjs — Generate a standalone Markdown summary
// after report generation and final audit are complete.
//
// Usage:
//   node synthesize-bottom-line-summary.mjs <run_dir>

import fs from 'fs';
import { join, basename } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

if (!runDir) {
  console.error('Usage: node synthesize-bottom-line-summary.mjs <run_dir>');
  process.exit(1);
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function readText(pathLike, fallback = '') {
  try {
    return fs.readFileSync(pathLike, 'utf8');
  } catch (_) {
    return fallback;
  }
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return Object.values(value);
  if (typeof value === 'string') return [value];
  return [];
}

function textValue(value, fallback = '') {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map((item) => textValue(item)).filter(Boolean).join('; ');
  if (value && typeof value === 'object') {
    for (const key of ['summary', 'finding', 'description', 'name', 'hypothesis', 'root_cause', 'action', 'recommendation', 'conclusion', 'detail', 'reason']) {
      if (value[key]) return textValue(value[key]);
    }
  }
  return fallback;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const text = textValue(value).trim();
    if (text) return text;
  }
  return '';
}

function firstArray(...values) {
  for (const value of values) {
    if (Array.isArray(value) && value.length > 0) return value;
  }
  return [];
}

function truncate(text, max = 380) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim();
  return normalized.length > max ? `${normalized.slice(0, max - 1)}...` : normalized;
}

function figureFileOf(entry) {
  if (!entry || typeof entry !== 'object') return '';
  const raw = entry.file || entry.figure || entry.filename || entry.path || entry.source || entry.name || '';
  return String(raw || '').replace(/^03_figures[\\/]/, '');
}

function imageCaptionEntries(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') {
    return Object.entries(value).map(([file, payload]) => ({
      figure: file,
      ...(payload && typeof payload === 'object' ? payload : { description: textValue(payload) })
    }));
  }
  return [];
}

function imageCaptionFor(file) {
  const normalized = String(file || '').replace(/^03_figures[\\/]/, '');
  return imageCaptionEntries(imageCaptions)
    .find((entry) => figureFileOf(entry) === normalized || basename(figureFileOf(entry)) === basename(normalized));
}

const runManifest = readJson(join(runDir, 'run_manifest.json'), {});
const diagnosis = readJson(join(runDir, '04_diagnostics', 'diagnosis.json'), {});
const evidence = readJson(join(runDir, '04_diagnostics', 'evidence.json'), {});
const confidence = readJson(join(runDir, '04_diagnostics', 'confidence.json'), {});
const judgeFeedback = readJson(join(runDir, '05_review', 'judge_feedback.json'), {});
const plotManifest = readJson(join(runDir, '03_figures', 'plot_manifest.json'), {});
const visualAnalysis = readJson(join(runDir, '03_figures', 'visual_analysis.json'), {});
const imageCaptions = readJson(join(runDir, '03_figures', 'image_captions.json'), {});
const optimizerText = readText(join(runDir, 'optimizer.md'));

const diagnosisType = diagnosis.diagnosis_type || 'NEEDS_DATA';
const sceneName = runManifest.scene_name || runManifest.run_id || basename(runDir);

function extractConfidence() {
  return firstNonEmpty(
    confidence.overall_confidence?.confidence_level,
    confidence.overall_confidence?.score,
    confidence.overall_confidence?.confidence_score,
    confidence.diagnostic_confidence,
    diagnosis.confidence,
    diagnosis.primary_confidence,
    diagnosis.confidence_level,
    '未量化'
  );
}

function extractConclusion() {
  if (diagnosisType === 'DETERMINED') {
    return firstNonEmpty(
      diagnosis.root_cause,
      diagnosis.primary_root_cause,
      diagnosis.primary_finding,
      diagnosis.summary,
      '当前诊断已形成确定性根因，但结构化诊断文件未提供简短结论。'
    );
  }

  if (diagnosisType === 'COMPETING_SET') {
    const competing = firstArray(diagnosis.hypotheses?.competing_sets, diagnosis.competing_sets)
      .flatMap((set) => firstArray(set.hypotheses, set.members, set.items))
      .map((item) => firstNonEmpty(item))
      .filter(Boolean)
      .slice(0, 3);
    const suffix = competing.length > 0
      ? `当前存在不可区分的竞争机制: ${competing.join('; ')}。`
      : '当前存在竞争假设集合，证据不足以唯一判定单一根因。';
    return `${firstNonEmpty(diagnosis.primary_finding, diagnosis.summary)} ${suffix}`.trim();
  }

  return firstNonEmpty(
    diagnosis.primary_finding,
    diagnosis.summary,
    '当前证据不足以完成可审计的根因判定，需要先补齐关键数据。'
  );
}

function extractPhysicalEvidence() {
  const surviving = firstArray(diagnosis.hypotheses?.surviving);
  const chain = surviving
    .flatMap((hypothesis) => asArray(hypothesis?.physical_logic_chain))
    .map((link) => {
      const logic = firstNonEmpty(link?.link, link?.description, link);
      const quantification = firstNonEmpty(link?.quantification);
      return quantification ? `${logic}；${quantification}` : logic;
    })
    .find(Boolean);

  const proofSummary = surviving
    .map((hypothesis) => firstNonEmpty(hypothesis?.ontology_data_physics_proof?.proof_summary, hypothesis?.root_physical_cause))
    .find(Boolean);

  return firstNonEmpty(
    chain,
    proofSummary,
    diagnosis.physical_mechanism,
    diagnosis.causal_chain,
    diagnosis.root_cause_model,
    '未在结构化诊断文件中抽取到独立物理链条；需回看diagnosis.json中的假设细节。'
  );
}

function extractStatisticalEvidence() {
  const surviving = firstArray(diagnosis.hypotheses?.surviving);
  const supporting = surviving
    .flatMap((hypothesis) => asArray(hypothesis?.supporting_evidence))
    .map((item) => {
      const rank = item?.rank ? `证据等级${item.rank}` : '';
      const source = firstNonEmpty(item?.source);
      const detail = firstNonEmpty(item?.detail, item?.summary, item);
      return [rank, source, detail].filter(Boolean).join('；');
    })
    .find((text) => /r=|rho|spearman|pearson|p=|相关|trend|simpson|n=/i.test(text));

  const direct = [
    ...asArray(evidence.key_evidence),
    ...asArray(evidence.evidence_items),
    ...asArray(evidence.supporting_evidence),
    ...asArray(diagnosis.key_evidence),
    ...asArray(diagnosis.evidence_summary)
  ]
    .map((item) => firstNonEmpty(item))
    .find((text) => /r=|rho|spearman|pearson|p=|相关|trend|simpson|n=/i.test(text));

  return firstNonEmpty(
    supporting,
    direct,
    diagnosis.statistical_evidence,
    diagnosis.validation_summary,
    '未抽取到独立统计摘要；需查看validate_report.json、feature_summary.json和data_analysis_conclusion.json。'
  );
}

function figurePurposeOf(file) {
  const figures = [
    ...asArray(plotManifest.figures),
    ...asArray(plotManifest.plots),
    ...asArray(visualAnalysis.chart_inventory)
  ];
  const normalized = String(file || '').replace(/^03_figures[\\/]/, '');
  const match = figures.find((entry) => figureFileOf(entry) === normalized || basename(figureFileOf(entry)) === basename(normalized));
  const caption = imageCaptionFor(normalized);
  return firstNonEmpty(match?.purpose, match?.description, caption?.purpose, caption?.description);
}

function figureObservationOf(file) {
  const normalized = String(file || '').replace(/^03_figures[\\/]/, '');
  const caption = imageCaptionFor(normalized);
  const captionObservation = firstNonEmpty(
    caption?.diagnostic_implication,
    caption?.key_observations?.[0],
    caption?.description
  );

  const visualObservation = asArray(visualAnalysis.visual_observations)
    .map((entry) => ({
      file: figureFileOf(entry),
      text: firstNonEmpty(entry.diagnostic_implication, entry.description, entry.observation, entry.finding, entry.summary)
    }))
    .find((entry) => entry.file === normalized || (entry.file && normalized.includes(entry.file)));

  return firstNonEmpty(visualObservation?.text, captionObservation, figurePurposeOf(file));
}

function figureWeight(file) {
  const normalized = String(file || '').replace(/^03_figures[\\/]/, '');
  const inventory = asArray(visualAnalysis.chart_inventory)
    .find((entry) => figureFileOf(entry) === normalized || basename(figureFileOf(entry)) === basename(normalized));
  const priorityList = asArray(plotManifest.vlm_priority_order).map((entry) => String(entry || '').replace(/^03_figures[\\/]/, ''));
  const priority = priorityList.indexOf(normalized);
  const text = `${figurePurposeOf(file)} ${figureObservationOf(file)}`.toLowerCase();
  let score = 0;
  if (inventory?.diagnostic_weight === 'CRITICAL') score += 10;
  if (priority >= 0) score += Math.max(0, 8 - priority);
  for (const hint of ['simpson', 'correlation', '相关', '产品切换', 'switch', 'temporal', 'overlay', 'drift', 'torque', 'profile', '趋势', 'change']) {
    if (text.includes(hint.toLowerCase())) score += 2;
  }
  return score;
}

function extractFigureEvidence() {
  const files = [
    ...asArray(plotManifest.vlm_priority_order),
    ...asArray(plotManifest.figures).map(figureFileOf),
    ...asArray(plotManifest.plots).map(figureFileOf),
    ...imageCaptionEntries(imageCaptions).map(figureFileOf)
  ]
    .map((file) => String(file || '').replace(/^03_figures[\\/]/, ''))
    .filter(Boolean);

  const items = [...new Set(files)]
    .map((file) => ({ file, observation: figureObservationOf(file), score: figureWeight(file) }))
    .filter((item) => item.observation)
    .sort((a, b) => b.score - a.score)
    .slice(0, 2);

  if (items.length === 0) {
    return ['- 未抽取到可渲染图像证据；请查看 `03_figures/` 和 `03_figures/visual_analysis.json`。'];
  }

  return items.flatMap((item) => [
    `![${basename(item.file)}](03_figures/${basename(item.file)})`,
    `- ${truncate(item.observation, 260)}`
  ]);
}

function extractCounterEvidence() {
  const surviving = firstArray(diagnosis.hypotheses?.surviving);
  const contradicting = surviving
    .flatMap((hypothesis) => asArray(hypothesis?.contradicting_evidence))
    .map((item) => firstNonEmpty(item?.detail, item?.summary, item))
    .find(Boolean);

  const eliminated = firstNonEmpty(diagnosis.eliminated_hypotheses, diagnosis.hypotheses?.eliminated);
  return firstNonEmpty(
    contradicting,
    eliminated,
    '未抽取到明确反证排除项；请关注诊断类型和数据缺口。'
  );
}

function extractImmediateAction() {
  const actions = firstArray(
    diagnosis.recommended_next_steps,
    diagnosis.recommendations,
    diagnosis.recommended_actions,
    diagnosis.hypotheses?.surviving?.[0]?.recommended_actions
  );

  const optimizerTableAction = optimizerText
    .split('\n')
    .map((line) => line.trim())
    .find((line) => /^\|/.test(line) && /\bP[01]\b|P0|P1|立即|低风险/.test(line) && /检查|采集|验证|修正|校准|安装|建立|观察|行动/.test(line));

  if (optimizerTableAction) {
    const cells = optimizerTableAction
      .split('|')
      .map((cell) => cell.replace(/\*\*/g, '').trim())
      .filter(Boolean);
    const actionCell = cells.find((cell) => /检查|采集|验证|修正|校准|安装|建立|观察/.test(cell));
    if (actionCell) return actionCell;
  }

  const optimizerBulletAction = optimizerText
    .split('\n')
    .map((line) => line.trim())
    .find((line) => /^[-*]\s+/.test(line) && /建议|检查|采集|验证|优化|action|measure/i.test(line) && !/未|错误|问题|误导|不存在|审计未/.test(line));

  return firstNonEmpty(
    actions[0],
    optimizerBulletAction?.replace(/^[-*]\s+/, ''),
    '先执行低风险现场复核，并补采能够区分竞争假设的关键过程数据。'
  );
}

function extractAuditStatus() {
  if (!optimizerText.trim()) return '最终审计文件 `optimizer.md` 不存在或为空。';
  const verdictLine = optimizerText
    .split('\n')
    .find((line) => /ENDORSED|CONDITIONAL|REJECTED|通过|有条件|拒绝|审计/i.test(line));
  return firstNonEmpty(verdictLine, '最终审计已生成 `optimizer.md`，请结合其中限制条件执行建议。');
}

const lines = [
  '# 最简诊断结论摘要',
  '',
  `**场景**: ${sceneName}`,
  `**运行目录**: \`${basename(runDir)}\``,
  `**诊断类型/置信度**: ${diagnosisType} / ${extractConfidence()}`,
  '',
  '## 结论',
  `**${truncate(extractConclusion(), 900)}**`,
  '',
  '## 为什么这样判断',
  `- **物理逻辑证据**: ${truncate(extractPhysicalEvidence(), 700)}`,
  `- **关键统计证据**: ${truncate(extractStatisticalEvidence(), 520)}`,
  '',
  '## 关键图像证据',
  ...extractFigureEvidence(),
  '',
  '## 反证与不确定性',
  `- ${truncate(extractCounterEvidence(), 520)}`,
  '',
  '## 审计后行动',
  `- **最终审计状态**: ${truncate(extractAuditStatus(), 320)}`,
  `- **立即建议**: ${truncate(extractImmediateAction(), 420)}`,
  '',
  '> 本文件在 `report.md` 生成且 `optimizer.md` 最终审计完成后生成，用于快速阅读；完整证据链仍以结构化产物和正式报告为准。',
  ''
];

const outputPath = join(runDir, 'bottom_line_summary.md');
fs.writeFileSync(outputPath, lines.join('\n'));
console.log(JSON.stringify({ ok: true, output: outputPath }, null, 2));
