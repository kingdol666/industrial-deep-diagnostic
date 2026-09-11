// Registry & availability tests — the multi-harness single source of truth.
import { test, describe, before } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

// Bogus override for codex BEFORE first resolution — proves the override chain
// is authoritative (不存在的显式覆盖必须如实 409，而不是回退到真实安装).
process.env.HARNESS_CODEX_COMMAND = join(mkdtempSync(join(tmpdir(), 'idd-registry-')), 'no-such-binary.cmd');

const { listHarnesses, getHarness, hasHarness, listHarnessIds } = await import('../src/harness/registry.mjs');
const { assertHarnessUsable, HarnessUnknownError, HarnessUnavailableError } = await import('../src/harness/availability.mjs');
const { HARNESS_DEFS, probeEngineAvailability } = await import('../src/harness/engines.mjs');

describe('harness registry — 14 engines', () => {
  test('registers exactly the documented engine set, claude first (default)', () => {
    const ids = listHarnessIds();
    assert.equal(ids[0], 'claude');
    for (const expected of ['claude', 'omp', 'mock', 'codex', 'dsh', 'opencode', 'gemini', 'copilot', 'cursor', 'crush', 'goose', 'qwen', 'pi', 'hermes']) {
      assert.ok(ids.includes(expected), `missing harness: ${expected}`);
    }
    assert.equal(ids.length, 14);
  });

  test('manifests carry the contract fields', () => {
    for (const m of listHarnesses()) {
      for (const key of ['id', 'name', 'kind', 'description', 'capabilities']) {
        assert.ok(m[key] !== undefined, `${m.id} missing ${key}`);
      }
      assert.ok(Array.isArray(m.capabilities));
    }
  });

  test('capability matrix matches the declared truth (能力如实声明)', () => {
    const caps = Object.fromEntries(listHarnesses().map((m) => [m.id, m.capabilities]));
    assert.deepEqual(caps.claude, ['live', 'chat']);
    assert.deepEqual(caps.omp, ['live', 'runs', 'report', 'html', 'enhancement']);
    assert.deepEqual(caps.mock, ['live', 'chat']);
    for (const id of ['codex', 'dsh', 'opencode', 'copilot', 'cursor', 'crush', 'qwen', 'pi', 'hermes']) {
      assert.deepEqual(caps[id], ['live'], `${id} should be live-only`);
    }
    for (const id of ['gemini', 'goose']) {
      assert.deepEqual(caps[id], ['live', 'chat']);
    }
    // runs browsing stays OMP-only
    for (const id of ['mock', 'codex', 'dsh', 'gemini', 'goose', 'pi', 'hermes', 'qwen', 'opencode']) {
      assert.ok(!caps[id].includes('runs'));
    }
  });

  test('definition table metadata exposes processModel + homepage', () => {
    const defs = Object.fromEntries(HARNESS_DEFS.map((d) => [d.id, d]));
    assert.equal(defs.mock.processModel, 'inprocess');
    assert.equal(defs.gemini.processModel, 'oneshot');
    assert.equal(defs.codex.processModel, 'resident');
    assert.ok(defs.gemini.homepage.includes('gemini-cli'));
    // 第 2 章一览表中的进程模型纪律
    const oneshot = new Set(['gemini', 'copilot', 'cursor', 'crush', 'goose', 'pi']);
    for (const d of HARNESS_DEFS) {
      assert.equal(oneshot.has(d.id), d.processModel === 'oneshot', `${d.id} processModel`);
    }
  });
});

describe('availability — 探测与拉起同源, three-state assertion', () => {
  test('in-process mock is always available', async () => {
    const probe = await probeEngineAvailability('mock', { force: true });
    assert.equal(probe.available, true);
    assert.equal(probe.inprocess, true);
    const health = await assertHarnessUsable('mock');
    assert.equal(health.available, true);
  });

  test('bogus command override → deterministic 409 HARNESS_UNAVAILABLE', async () => {
    await assert.rejects(
      () => assertHarnessUsable('codex'),
      (err) => {
        assert.ok(err instanceof HarnessUnavailableError);
        assert.equal(err.status, 409);
        assert.equal(err.code, 'HARNESS_UNAVAILABLE');
        assert.match(err.message, /HARNESS_CODEX_COMMAND|config harness\.engines\.codex\.binary/);
        return true;
      },
    );
  });

  test('unknown harness → 400 HARNESS_UNKNOWN with the full registry list', async () => {
    await assert.rejects(
      () => assertHarnessUsable('definitely-not-a-harness'),
      (err) => {
        assert.ok(err instanceof HarnessUnknownError);
        assert.equal(err.status, 400);
        assert.match(err.message, /claude, omp, mock/);
        return true;
      },
    );
  });

  test('hasHarness membership check', () => {
    assert.equal(hasHarness('omp'), true);
    assert.equal(hasHarness('OMP'), false); // membership is exact — callers normalize case first
    assert.equal(hasHarness('nope'), false);
    assert.equal(hasHarness(undefined), false);
    assert.ok(getHarness('pi').capabilities.includes('live'));
  });

  test('default harness chain — omp first (适配最全), config-driven', async () => {
    const { defaultHarnessChain, resolveBestAvailableHarness } = await import('../src/harness/engines.mjs');
    const chain = defaultHarnessChain();
    assert.equal(chain[0], 'omp'); // config harness.default
    assert.ok(chain.includes('claude') && chain.includes('mock'));
    assert.equal(new Set(chain).size, chain.length, 'no duplicates in fallback chain');
    // resolution returns an available, registered id
    const best = await resolveBestAvailableHarness();
    assert.ok(listHarnessIds().includes(best));
  });
});
