// Provider error classification (2026-10-22 remediation, Phase B).
//
// The exact OMP failure observed: "Retry budget exhausted after 10 retries:
// 429 Budget has been exceeded! Key=… Current cost: 100.38, Max budget: 100.0"
// It must classify as quota (actionable: top up/switch key), not generic 429.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const {
  classifyProviderError, tagProviderError, recordProviderError, getProviderError, resetProviderErrors,
} = await import('../src/services/provider-error.service.mjs');

describe('classifyProviderError', () => {
  test('OMP budget-exhausted text → provider_quota (quota wins over 429)', () => {
    const text = 'Retry budget exhausted after 10 retries: 429 Budget has been exceeded! '
      + 'Key=SA25218311 Current cost: 100.3821847999999, Max budget: 100.0';
    const c = classifyProviderError(text);
    assert.equal(c.code, 'provider_quota');
    assert.match(c.label, /预算|配额/);
  });

  test('generic 429 → provider_rate_limit', () => {
    assert.equal(classifyProviderError('HTTP 429 Too Many Requests').code, 'provider_rate_limit');
  });

  test('401/403 → provider_auth', () => {
    assert.equal(classifyProviderError('401 invalid api key').code, 'provider_auth');
    assert.equal(classifyProviderError('403 forbidden').code, 'provider_auth');
  });

  test('5xx / timeout → provider_unavailable', () => {
    assert.equal(classifyProviderError('503 Service Unavailable').code, 'provider_unavailable');
    assert.equal(classifyProviderError('OMP RPC handshake timeout (no ready event)').code, 'provider_unavailable');
  });

  test('non-provider text and empty input → null', () => {
    assert.equal(classifyProviderError('Agent ended without producing report.md'), null);
    assert.equal(classifyProviderError(''), null);
    assert.equal(classifyProviderError(null), null);
  });
});

describe('tagging + per-harness record', () => {
  test('tagProviderError prefixes the category for DB rows', () => {
    const tagged = tagProviderError('Budget has been exceeded');
    assert.equal(tagged.category.code, 'provider_quota');
    assert.match(tagged.text, /^\[provider_quota\] /);
    const plain = tagProviderError('some agent logic error');
    assert.equal(plain.category, null);
    assert.equal(plain.text, 'some agent logic error');
  });

  test('recordProviderError is per harness and returns the latest', () => {
    resetProviderErrors();
    recordProviderError('omp', 'Budget has been exceeded');
    recordProviderError('claude', '429 rate limit');
    assert.equal(getProviderError('omp').code, 'provider_quota');
    assert.equal(getProviderError('claude').code, 'provider_rate_limit');
    assert.equal(getProviderError('mock'), null);
    resetProviderErrors();
    assert.equal(getProviderError('omp'), null);
  });
});
