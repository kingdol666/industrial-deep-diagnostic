#!/usr/bin/env node
// finalize-run-artifacts.mjs — Post-process a run so key artifacts are
// schema-aligned and handoff files exist before final validation.
//
// Usage:
//   node finalize-run-artifacts.mjs <run_dir> <skill_path>

import { execFileSync } from 'child_process';
import { join } from 'path';
import fs from 'fs';

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
  console.error('Usage: node finalize-run-artifacts.mjs <run_dir> <skill_path>');
  process.exit(1);
}

function run(scriptName) {
  return execFileSync('node', [resolveScript(scriptName), runDir], {
    stdio: ['ignore', 'pipe', 'pipe']
  }).toString();
}

function runWithArgs(scriptName, extraArgs = []) {
  return execFileSync('node', [resolveScript(scriptName), runDir, ...extraArgs], {
    stdio: ['ignore', 'pipe', 'pipe']
  }).toString();
}

function logEvent(event, extraArgs = []) {
  try {
    execFileSync('node', [resolveScript('append-pipeline-event.mjs'), runDir, '--event', event, '--agent', 'main-agent', ...extraArgs], {
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
  results.judge_gate_before_summary = JSON.parse(runWithArgs('judge-gate-check.mjs', ['--skip-summary']));
} catch (error) {
  const stdout = error.stdout ? String(error.stdout) : '';
  try {
    results.judge_gate_before_summary = JSON.parse(stdout);
  } catch (_) {
    results.judge_gate_before_summary = { ok: false, error: String(error.stderr || error.stdout || error.message) };
  }
  logEvent('run_failed', [
    '--step',
    'present',
    '--status',
    'JUDGE_GATE_NOT_PASSED',
    '--errors',
    'Judge gate failed before run finalization'
  ]);
  console.error(JSON.stringify({ ok: false, error: 'JUDGE_GATE_NOT_PASSED', run_dir: runDir, results }, null, 2));
  process.exit(1);
}

try {
  results.synthesize_run_summary = JSON.parse(run('synthesize-run-summary.mjs'));
} catch (error) {
  results.synthesize_run_summary = { ok: false, error: String(error.stderr || error.stdout || error.message) };
}

try {
  results.judge_gate_after_summary = JSON.parse(runWithArgs('judge-gate-check.mjs'));
} catch (error) {
  const stdout = error.stdout ? String(error.stdout) : '';
  try {
    results.judge_gate_after_summary = JSON.parse(stdout);
  } catch (_) {
    results.judge_gate_after_summary = { ok: false, error: String(error.stderr || error.stdout || error.message) };
  }
  logEvent('run_failed', [
    '--step',
    'present',
    '--status',
    'JUDGE_GATE_NOT_PASSED',
    '--errors',
    'Judge gate failed after run summary synthesis'
  ]);
  console.error(JSON.stringify({ ok: false, error: 'JUDGE_GATE_NOT_PASSED', run_dir: runDir, results }, null, 2));
  process.exit(1);
}

/**
 * Validate HTML delivery: check diagnostic-report.html exists, >= 5KB,
 * and 05_review/html_review.json exists with verdict "pass".
 * If user explicitly opted out of HTML (HTML_OPT_OUT marker file exists),
 * skip validation and return empty issues.
 */
function validateHTMLDelivery() {
  const htmlPath = join(runDir, 'diagnostic-report.html');
  const reviewPath = join(runDir, '05_review', 'html_review.json');
  const optOutPath = join(runDir, '00_input', 'html_opt_out');

  // User explicitly opted out of HTML generation → skip validation
  if (fs.existsSync(optOutPath)) {
    return [];
  }

  const issues = [];

  if (!fs.existsSync(htmlPath)) {
    issues.push('diagnostic-report.html missing');
  } else {
    const stat = fs.statSync(htmlPath);
    const sizeBytes = stat.size;
    if (sizeBytes < 5120) {
      issues.push(`diagnostic-report.html too small: ${sizeBytes} bytes (min 5120)`);
    }
  }

  if (!fs.existsSync(reviewPath)) {
    issues.push('05_review/html_review.json missing');
  } else {
    try {
      const review = JSON.parse(fs.readFileSync(reviewPath, 'utf-8'));
      if (review.verdict !== 'pass') {
        issues.push(`html_review verdict is "${review.verdict}", expected "pass"`);
      }
    } catch (e) {
      issues.push(`05_review/html_review.json failed to parse: ${e.message}`);
    }
  }

  return issues;
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

// Validate HTML delivery after evidence closure check
const htmlIssues = validateHTMLDelivery();
if (htmlIssues.length > 0) {
  logEvent('run_failed', [
    '--step',
    'present',
    '--status',
    'HTML_DELIVERY_FAILED',
    '--errors',
    htmlIssues.join('; ')
  ]);
  console.error(JSON.stringify({ ok: false, error: 'HTML_DELIVERY_FAILED', html_issues: htmlIssues, run_dir: runDir, results }, null, 2));
  process.exit(1);
}

logEvent('artifact_finalize_complete', [
  '--step',
  'present',
  '--files',
  '02_processed/anomaly_report.json,02_processed/data_analysis_conclusion.json,run_summary.json,optimizer.md,evidence_closure_report.json'
]);

logEvent('run_completed', ['--step', 'present']);

console.log(JSON.stringify({ ok: true, run_dir: runDir, results }, null, 2));
