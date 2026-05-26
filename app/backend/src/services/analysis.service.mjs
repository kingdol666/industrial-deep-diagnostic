import { existsSync, readdirSync, readFileSync } from 'fs';
import { join } from 'path';
import { WORKSPACE_DIR } from '../engine/claude-client.mjs';

/**
 * Extract chart-ready data from a completed diagnostic run workspace.
 * Returns structured data for each chart type, or null if unavailable.
 */
export function getRunChartData(runDirName) {
  const runDir = join(WORKSPACE_DIR, runDirName);
  if (!existsSync(runDir)) return null;

  const result = {};

  // Read processed feature summary (correlation data)
  const processedDir = join(runDir, '02_processed');
  if (existsSync(processedDir)) {
    const files = readdirSync(processedDir);
    for (const f of files) {
      if (f === 'feature_summary.json') {
        try {
          result.featureSummary = JSON.parse(readFileSync(join(processedDir, f), 'utf-8'));
        } catch {}
      }
    }
  }

  // Read diagnosis JSON
  const diagDir = join(runDir, '04_diagnostics');
  if (existsSync(diagDir)) {
    const files = readdirSync(diagDir);
    for (const f of files) {
      if (f === 'diagnosis.json') {
        try {
          result.diagnosis = JSON.parse(readFileSync(join(diagDir, f), 'utf-8'));
        } catch {}
      }
      if (f === 'evidence.json') {
        try {
          result.evidence = JSON.parse(readFileSync(join(diagDir, f), 'utf-8'));
        } catch {}
      }
    }
  }

  // Read run summary
  const summaryFile = join(runDir, 'run_summary.json');
  if (existsSync(summaryFile)) {
    try {
      result.runSummary = JSON.parse(readFileSync(summaryFile, 'utf-8'));
    } catch {}
  }

  // Build chart-friendly datasets
  const charts = {};

  // 1. Feature correlation heatmap
  if (result.featureSummary?.correlations) {
    const corr = result.featureSummary.correlations;
    const vars = Object.keys(corr);
    charts.heatmap = {
      type: 'correlation',
      variables: vars,
      data: vars.flatMap((v1, i) =>
        vars.map((v2, j) => ({ x: i, y: j, value: corr[v1]?.[v2] ?? 0 }))
      ),
      xLabels: vars,
      yLabels: vars,
    };
  }

  // 2. Confidence/score gauge
  if (result.diagnosis?.confidence) {
    const conf = result.diagnosis.confidence;
    charts.confidence = {
      type: 'gauge',
      overall: typeof conf.overall === 'number' ? conf.overall : 0,
      dimensions: Object.entries(conf)
        .filter(([k]) => k !== 'overall')
        .map(([k, v]) => ({ name: k, value: typeof v === 'number' ? v : (v?.score || 0) })),
    };
  }

  // 3. Score and verdict from run summary
  if (result.runSummary) {
    charts.runSummary = {
      score: result.runSummary.score,
      verdict: result.runSummary.verdict || result.runSummary.judge_verdict,
    };
  }

  return Object.keys(charts).length > 0 ? charts : null;
}
