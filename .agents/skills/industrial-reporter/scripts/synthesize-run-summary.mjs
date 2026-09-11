#!/usr/bin/env node
// synthesize-run-summary.mjs — Generate a schema-aligned run_summary.json from
// the artifacts already present in a run directory.
//
// Usage:
//   node synthesize-run-summary.mjs <run_dir>

import fs from 'fs';
import { join, basename } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

if (!runDir) {
  console.error('Usage: node synthesize-run-summary.mjs <run_dir>');
  process.exit(1);
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function countLines(pathLike) {
  try {
    return fs.readFileSync(pathLike, 'utf8').split('\n').length;
  } catch (_) {
    return 0;
  }
}

function fileSize(pathLike) {
  try {
    return fs.statSync(pathLike).size;
  } catch (_) {
    return 0;
  }
}

function firstExistingPath(paths) {
  return paths.find((pathLike) => fs.existsSync(pathLike)) || paths[0];
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return Object.values(value);
  if (typeof value === 'string') return [value];
  return [];
}

function normalizeDataSources(manifest) {
  const candidates = [
    ...asArray(manifest?.files),
    ...asArray(manifest?.data_files),
    ...asArray(manifest?.sources)
  ];

  const normalized = [];
  const seen = new Set();

  for (const entry of candidates) {
    let source = 'unknown';
    let rows = 0;
    let columns = 0;

    if (typeof entry === 'string') {
      source = entry;
    } else if (entry && typeof entry === 'object') {
      source = entry.path || entry.name || entry.source || entry.file || 'unknown';
      rows = Number.isInteger(entry.rows) ? entry.rows : 0;
      columns = Number.isInteger(entry.columns) ? entry.columns : 0;
    }

    const key = `${source}::${rows}::${columns}`;
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push({ source, rows, columns });
  }

  return normalized;
}

const runManifest = readJson(join(runDir, 'run_manifest.json'), {});
const diagnosis = readJson(join(runDir, '04_diagnostics', 'diagnosis.json'), {});
const judgeFeedback = readJson(join(runDir, '05_review', 'judge_feedback.json'), {});
const inputManifest = readJson(join(runDir, '00_input', 'input_manifest.json'), {});
const optimizerExists = fs.existsSync(join(runDir, 'optimizer.md'));
const existingSummary = readJson(join(runDir, 'run_summary.json'), {});
const reportPath = firstExistingPath([
  join(runDir, 'report.md'),
  join(runDir, '05_review', 'report.md')
]);
const plotManifest = readJson(join(runDir, '03_figures', 'plot_manifest.json'), { plots: [] });
const reportText = fs.existsSync(reportPath) ? fs.readFileSync(reportPath, 'utf8') : '';

const stepChecks = [
  ['setup', fs.existsSync(join(runDir, 'run_manifest.json'))],
  ['inspect', fs.existsSync(join(runDir, '00_input', 'input_manifest.json'))],
  ['context_builder', fs.existsSync(join(runDir, '01_ontology', 'ontology.json'))],
  ['clarification_gate', fs.existsSync(join(runDir, '00_input', 'run_config.json')) || fs.existsSync(join(runDir, '00_input', 'clarification_needed.json'))],
  ['data_processor', fs.existsSync(join(runDir, '02_processed', 'feature_summary.json'))],
  ['diagnostician', fs.existsSync(join(runDir, '04_diagnostics', 'diagnosis.json'))],
  ['judge', fs.existsSync(join(runDir, '05_review', 'judge_feedback.json'))],
  ['reporter', fs.existsSync(reportPath) || fs.existsSync(join(runDir, 'run_summary.json'))],
  ['audit', optimizerExists]
];

const pipelineStepsCompleted = stepChecks.filter(([, present]) => present).map(([name]) => name);

const dataSources = normalizeDataSources(inputManifest);

const judgeVerdict = typeof judgeFeedback.verdict === 'object'
  ? judgeFeedback.verdict
  : {
      score: judgeFeedback.overall_score ?? judgeFeedback.score ?? judgeFeedback.judge_score ?? 0,
      verdict: judgeFeedback.verdict || ((judgeFeedback.overall_score ?? judgeFeedback.score ?? judgeFeedback.judge_score ?? 0) >= 90 ? 'pass' : 'needs_repair')
    };

const auditVerdict = optimizerExists
  ? { verdict: 'CONDITIONAL', physical_match_rating: 0 }
  : undefined;

const report = {
  run_id: runManifest.run_id || basename(runDir),
  scene_name: inputManifest.scene_name
    || inputManifest.process_name
    || inputManifest.scenario_name
    || runManifest.scene_name
    || existingSummary.scene_name
    || runManifest.run_id
    || basename(runDir),
  timestamp: runManifest.completed || runManifest.created || existingSummary.timestamp || new Date().toISOString(),
  pipeline_steps_completed: pipelineStepsCompleted,
  diagnosis_type: diagnosis.diagnosis_type || 'NEEDS_DATA',
  primary_finding: diagnosis.primary_finding || diagnosis.summary || '',
  judge_verdict: {
    score: judgeVerdict.score || 0,
    verdict: judgeVerdict.verdict || 'needs_repair'
  },
  data_sources: dataSources,
  figure_count: Array.isArray(plotManifest.plots) ? plotManifest.plots.length : 0,
  report_stats: {
    total_lines: countLines(reportPath),
    sections_count: reportText.length === 0 ? 0 : reportText.split('\n').filter((line) => line.startsWith('## ')).length,
    figures_referenced: Array.isArray(plotManifest.plots) ? plotManifest.plots.length : 0,
    file_size_bytes: fileSize(reportPath)
  },
  diagnostic_iterations: 1
};

if (auditVerdict) {
  report.audit_verdict = auditVerdict;
}

fs.writeFileSync(join(runDir, 'run_summary.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ ok: true, output: join(runDir, 'run_summary.json') }, null, 2));
