// Intent outcome — artifact-first score/verdict extraction.
//
// Specialist runs have no Judge step; the numbers users see must come from the
// run's own JSON artifacts. These tests pin the artifact→(score, verdict)
// mapping and the read-time enrichment rules (never overwrite stored values).
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs';
import { join } from 'path';

const {
  extractIntentOutcome, deriveRunOutcome, enrichRunOutcome,
} = await import('../src/services/intent-outcome.service.mjs');

const ROOT = mkdtempSync(join(import.meta.dirname, '.tmp-outcome-'));
let seq = 0;

function runDir(files = {}) {
  const dir = join(ROOT, `run-${seq += 1}`);
  mkdirSync(dir, { recursive: true });
  for (const [rel, body] of Object.entries(files)) {
    const abs = join(dir, rel);
    mkdirSync(join(abs, '..'), { recursive: true });
    writeFileSync(abs, typeof body === 'string' ? body : JSON.stringify(body), 'utf-8');
  }
  return dir;
}

function cleanup() {
  try { rmSync(ROOT, { recursive: true, force: true }); } catch { /* best effort */ }
}
process.on('exit', cleanup);

describe('extractIntentOutcome — per-intent artifact contracts', () => {
  test('stability-report reads conclusion.score/grade/label', () => {
    const dir = runDir({
      'line_report/stability_report.json': {
        conclusion: { score: 65.8, grade: 'C', grade_key: 'fluctuating', label: '波动' },
      },
    });
    const out = extractIntentOutcome(dir, 'stability-report');
    assert.equal(out.score, 65.8);
    assert.equal(out.verdict, 'C · 波动');
    assert.match(out.source, /stability_report\.json/);
  });

  test('stability-report without a grade keeps an honest null verdict', () => {
    const dir = runDir({ 'line_report/stability_report.json': { conclusion: { score: null } } });
    assert.deepEqual(extractIntentOutcome(dir, 'stability-report'), { score: null, verdict: null, source: null });
  });

  test('quick-screen reads alert status + alert count', () => {
    const dir = runDir({
      'sentinel/alert.json': { status: 'alert', alerts: [{}, {}, {}] },
    });
    const out = extractIntentOutcome(dir, 'quick-screen');
    assert.equal(out.score, null);
    assert.equal(out.verdict, 'alert · 3 alerts');
  });

  test('doe-analysis reads evidence_grade/design_type (no invented score)', () => {
    const dir = runDir({
      'conclusions/doe_conclusion.json': {
        evidence_grade: 'A', design_type: 'rsm_ccd', key_findings: [],
      },
    });
    const out = extractIntentOutcome(dir, 'doe-analysis');
    assert.equal(out.score, null);
    assert.equal(out.verdict, 'A · rsm_ccd');
  });

  test('experience-mining reads recommendation_status + playbooks', () => {
    const dir = runDir({
      'conclusions/recommendation.json': {
        recommendation_status: 'playbook_hit', playbooks: [{}],
      },
    });
    assert.equal(extractIntentOutcome(dir, 'experience-mining').verdict, 'playbook_hit · 1 playbook');
  });

  test('optimizer-campaign reads phase + round_count', () => {
    const dir = runDir({
      '01_state/optimizer_state.json': { phase: 'exploiting', round_count: 2 },
    });
    assert.equal(extractIntentOutcome(dir, 'optimizer-campaign').verdict, 'exploiting · round 2');
  });

  test('deep-diagnosis is untouched (Judge Score stays the only source)', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 65.8, grade: 'C' } },
    });
    assert.deepEqual(extractIntentOutcome(dir, 'deep-diagnosis'), { score: null, verdict: null, source: null });
  });

  test('missing / malformed artifacts degrade to null, never throw', () => {
    const dir = runDir({ 'sentinel/alert.json': '{not json' });
    assert.deepEqual(extractIntentOutcome(dir, 'quick-screen'), { score: null, verdict: null, source: null });
    assert.deepEqual(extractIntentOutcome(join(dir, 'nope'), 'stability-report'), { score: null, verdict: null, source: null });
    assert.deepEqual(extractIntentOutcome(null, 'doe-analysis'), { score: null, verdict: null, source: null });
  });
});

describe('deriveRunOutcome / enrichRunOutcome — read-time only, never overwrite', () => {
  test('a terminal specialist row with empty outcome is enriched from its artifacts', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 65.8, grade: 'C', label: '波动' } },
    });
    const run = {
      run_id: `derived-${seq}`, status: 'completed', analysis_intent: 'stability-report',
      workspace_path: dir, score: null, judge_verdict: null,
    };
    const out = enrichRunOutcome(run);
    assert.equal(out.score, 65.8);
    assert.equal(out.judge_verdict, 'C · 波动');
    assert.equal(out.outcome_source, 'line_report/stability_report.json#conclusion');
    // original row untouched
    assert.equal(run.score, null);
  });

  test('stored values always win (no double authority)', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 65.8, grade: 'C' } },
    });
    const run = {
      run_id: `stored-${seq}`, status: 'completed', analysis_intent: 'stability-report',
      workspace_path: dir, score: 96, judge_verdict: 'ENDORSED',
    };
    assert.deepEqual(deriveRunOutcome(run), { score: null, verdict: null, source: null });
    assert.equal(enrichRunOutcome(run), run);
  });

  test('non-terminal runs and deep-diagnosis rows are never derived', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 65.8, grade: 'C' } },
    });
    assert.equal(deriveRunOutcome({
      run_id: `running-${seq}`, status: 'running', analysis_intent: 'stability-report',
      workspace_path: dir, score: null, judge_verdict: null,
    }).verdict, null);
    assert.equal(deriveRunOutcome({
      run_id: `deep-${seq}`, status: 'completed', analysis_intent: 'deep-diagnosis',
      workspace_path: dir, score: null, judge_verdict: null,
    }).verdict, null);
  });

  test('missing workspace path is a no-op', () => {
    const run = {
      run_id: `no-ws-${seq}`, status: 'completed', analysis_intent: 'quick-screen',
      workspace_path: null, score: null, judge_verdict: null,
    };
    assert.equal(enrichRunOutcome(run), run);
  });
});
