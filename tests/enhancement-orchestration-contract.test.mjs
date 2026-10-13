import assert from 'node:assert/strict';
import test from 'node:test';
import {
  resolveEnhancementStatus,
  shouldBuildAssociationGraph,
  isFreshBySignature,
  reviewIsPassing,
} from '../.claude/skills/industrial-analysis-enhance-auto/scripts/orchestration_contract.mjs';

test('a failed current launch cannot inherit a stale READY knowledge artifact', () => {
  assert.equal(resolveEnhancementStatus({ launchOk: false, knowledgeStatus: 'READY' }), 'FAILED');
});

test('a failing or warning reviewer verdict cannot produce READY', () => {
  assert.equal(reviewIsPassing({ verdict: 'pass', overall_score: 90, blocking_issues: [] }), true);
  assert.equal(reviewIsPassing({ verdict: 'fail', overall_score: 100, blocking_issues: [] }), false);
  assert.equal(reviewIsPassing({ verdict: 'warn', overall_score: 85, blocking_issues: [] }), false);
  assert.equal(reviewIsPassing({ verdict: 'pass', overall_score: 95, blocking_issues: ['missing chart'] }), false);
  assert.equal(resolveEnhancementStatus({ launchOk: true, knowledgeStatus: 'READY', review: { verdict: 'fail' } }), 'FAILED');
  assert.equal(resolveEnhancementStatus({ launchOk: true, knowledgeStatus: 'READY', review: { verdict: 'warn', overall_score: 85, blocking_issues: [] } }), 'FAILED');
});

test('E3 graph output suppresses the redundant standalone E3.5 scan', () => {
  assert.equal(shouldBuildAssociationGraph({ e3Ok: true, graphExists: true }), false);
  assert.equal(shouldBuildAssociationGraph({ e3Ok: true, graphExists: false }), true);
  assert.equal(shouldBuildAssociationGraph({ e3Ok: false, graphExists: false }), false);
});

test('freshness signatures detect input and script changes independent of mtime', () => {
  const prior = { scriptHash: 'a', inputs: { selection: 'x', data: 'y' } };
  assert.equal(isFreshBySignature(prior, { scriptHash: 'a', inputs: { selection: 'x', data: 'y' } }), true);
  assert.equal(isFreshBySignature(prior, { scriptHash: 'b', inputs: { selection: 'x', data: 'y' } }), false);
  assert.equal(isFreshBySignature(prior, { scriptHash: 'a', inputs: { selection: 'z', data: 'y' } }), false);
  assert.equal(isFreshBySignature(prior, { scriptHash: 'a', inputs: { selection: 'x', data: 'y', regime: 'r' } }), false);
});
