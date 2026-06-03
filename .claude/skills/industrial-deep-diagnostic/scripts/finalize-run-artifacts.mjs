#!/usr/bin/env node
// finalize-run-artifacts.mjs — Post-process a run so key artifacts are
// schema-aligned and handoff files exist before final validation.
//
// Usage:
//   node finalize-run-artifacts.mjs <run_dir> <skill_path>

import { execFileSync } from 'child_process';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
const skillPath = args[1] || '.';

if (!runDir) {
  console.error('Usage: node finalize-run-artifacts.mjs <run_dir> <skill_path>');
  process.exit(1);
}

function run(scriptName) {
  return execFileSync('node', [join(skillPath, 'scripts', scriptName), runDir], {
    stdio: ['ignore', 'pipe', 'pipe']
  }).toString();
}

function logEvent(event, extraArgs = []) {
  try {
    execFileSync('node', [join(skillPath, 'scripts', 'append-pipeline-event.mjs'), runDir, '--event', event, '--agent', 'main-agent', ...extraArgs], {
      stdio: ['ignore', 'pipe', 'pipe']
    });
  } catch (_) {}
}

const results = {};

logEvent('artifact_finalize_start', ['--step', 'present']);

try {
  results.normalize_anomaly_report = JSON.parse(run('normalize-anomaly-report.mjs'));
} catch (error) {
  results.normalize_anomaly_report = { ok: false, error: String(error.stderr || error.stdout || error.message) };
}

try {
  results.synthesize_data_analysis_conclusion = JSON.parse(run('synthesize-data-analysis-conclusion.mjs'));
} catch (error) {
  results.synthesize_data_analysis_conclusion = { ok: false, error: String(error.stderr || error.stdout || error.message) };
}

try {
  results.synthesize_run_summary = JSON.parse(run('synthesize-run-summary.mjs'));
} catch (error) {
  results.synthesize_run_summary = { ok: false, error: String(error.stderr || error.stdout || error.message) };
}

try {
  results.evidence_closure = JSON.parse(
    execFileSync('node', [join(skillPath, 'scripts', 'evidence-closure-check.mjs'), runDir, '--write'], {
      stdio: ['ignore', 'pipe', 'pipe']
    }).toString()
  );
} catch (error) {
  const stdout = error.stdout ? String(error.stdout) : '';
  try {
    results.evidence_closure = JSON.parse(stdout);
  } catch (_) {
    results.evidence_closure = { ok: false, error: String(error.stderr || error.stdout || error.message) };
  }
}

logEvent('artifact_finalize_complete', [
  '--step',
  'present',
  '--files',
  '02_processed/anomaly_report.json,02_processed/data_analysis_conclusion.json,run_summary.json,evidence_closure_report.json'
]);

console.log(JSON.stringify({ ok: true, run_dir: runDir, results }, null, 2));
