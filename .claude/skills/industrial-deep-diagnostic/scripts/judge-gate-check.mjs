#!/usr/bin/env node
// judge-gate-check.mjs — Hard final gate for report completion.
//
// Usage:
//   node judge-gate-check.mjs <run_dir> [--min-score 90] [--skip-summary]

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
const minScoreIndex = args.indexOf('--min-score');
const minScore = minScoreIndex >= 0 ? Number(args[minScoreIndex + 1]) : 90;
const skipSummary = args.includes('--skip-summary');

if (!runDir) {
  console.error('Usage: node judge-gate-check.mjs <run_dir> [--min-score 90] [--skip-summary]');
  process.exit(1);
}

function exists(relPath) {
  return fs.existsSync(join(runDir, relPath));
}

function readJson(relPath) {
  const fullPath = join(runDir, relPath);
  try {
    return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
  } catch (error) {
    return { __read_error: error.message };
  }
}

function asScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? score : 0;
}

function blockingCount(value) {
  return Array.isArray(value) ? value.length : 0;
}

function numericOrArrayCount(value) {
  if (Array.isArray(value)) return value.length;
  return asScore(value);
}

const issues = [];

if (!exists('05_review/judge_feedback.json')) {
  issues.push({
    code: 'JUDGE_FEEDBACK_MISSING',
    severity: 'critical',
    message: '05_review/judge_feedback.json is required before report finalization.'
  });
} else {
  const judge = readJson('05_review/judge_feedback.json');
  if (judge.__read_error) {
    issues.push({
      code: 'JUDGE_FEEDBACK_UNREADABLE',
      severity: 'critical',
      message: `judge_feedback.json is not valid JSON: ${judge.__read_error}`
    });
  } else {
    const score = asScore(judge.overall_score ?? judge.score ?? judge.judge_score);
    const verdict = typeof judge.verdict === 'object' ? judge.verdict?.verdict : judge.verdict;
    const blockingIssues = blockingCount(judge.blocking_issues);
    const reasoningBlocking = blockingCount(judge.reasoning_chain_audit?.blocking_issues);
    const noOverClaimingBlocking = numericOrArrayCount(judge.criteria_scores?.no_over_claiming?.blocking_issues);

    if (score < minScore) {
      issues.push({
        code: 'JUDGE_SCORE_BELOW_GATE',
        severity: 'critical',
        message: `Judge overall_score ${score} is below the required final gate ${minScore}.`
      });
    }
    if (verdict !== 'pass') {
      issues.push({
        code: 'JUDGE_VERDICT_NOT_PASS',
        severity: 'critical',
        message: `Judge verdict must be "pass" before final report completion; got "${verdict || 'missing'}".`
      });
    }
    if (blockingIssues > 0 || reasoningBlocking > 0 || noOverClaimingBlocking > 0) {
      issues.push({
        code: 'JUDGE_BLOCKING_ISSUES_PRESENT',
        severity: 'critical',
        message: `Judge reported blocking issues: blocking_issues=${blockingIssues}, reasoning_chain_audit.blocking_issues=${reasoningBlocking}, no_over_claiming.blocking_issues=${noOverClaimingBlocking}.`
      });
    }

    if (!skipSummary && exists('run_summary.json')) {
      const summary = readJson('run_summary.json');
      if (summary.__read_error) {
        issues.push({
          code: 'RUN_SUMMARY_UNREADABLE',
          severity: 'critical',
          message: `run_summary.json is not valid JSON: ${summary.__read_error}`
        });
      } else {
        const summaryScore = asScore(summary.judge_verdict?.score);
        const summaryVerdict = summary.judge_verdict?.verdict;
        if (summaryScore !== score || summaryVerdict !== verdict) {
          issues.push({
            code: 'RUN_SUMMARY_JUDGE_DRIFT',
            severity: 'critical',
            message: `run_summary.json judge_verdict must match judge_feedback.json exactly; summary=${summaryScore}/${summaryVerdict}, judge=${score}/${verdict}.`
          });
        }
      }
    }
  }
}

if ((exists('report.md') || exists('run_summary.json')) && issues.length > 0) {
  issues.push({
    code: 'FINAL_ARTIFACTS_WITHOUT_PASSED_JUDGE',
    severity: 'critical',
    message: 'Final artifacts exist but the Judge gate did not pass; this run is not complete.'
  });
}

const report = {
  ok: issues.length === 0,
  gate: 'judge_final_report_gate',
  min_score: minScore,
  run_dir: runDir,
  checked_at: new Date().toISOString(),
  issues
};

console.log(JSON.stringify(report, null, 2));
process.exit(report.ok ? 0 : 1);
