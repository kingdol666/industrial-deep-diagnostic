// D5 — omp binary resolution must use the documented shared chain
//
//   harness.engines.<id>.binary → env HARNESS_<ID>_COMMAND → where/PATH
//
// The omp client resolved config.omp.binary / PATH on its own, so the override
// every other engine honors was silently ignored for omp: probe and spawn
// agreed with each other but not with the documented contract (and never with
// HARNESS_OMP_COMMAND). resolveOmpBinary now goes through cli-common's
// resolveCliBinary('omp') (探测与拉起同源) and is exported so tests can pin
// exactly what the spawn path will execute.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const HANG_FIXTURE = join(here, 'fixtures', 'fake-hang.mjs');
const work = mkdtempSync(join(tmpdir(), 'idd-omp-chain-'));
const traceFile = join(work, 'trace.log');

// The override must be in place BEFORE the first resolution in this process.
const { makeCliShim, drain, findResult, commandEnvKey } = await import('./helpers.mjs');
const shim = makeCliShim(HANG_FIXTURE, 'omp', { name: 'fake-omp-chain', dir: work });
process.env[commandEnvKey('omp')] = shim;
process.env.FAKE_TRACE = traceFile;

const { resolveCliBinary, invalidateBinaryCache } = await import('../src/engine/cli-common.mjs');
const { resolveOmpBinary, probeOmpEngine, startDiagnosis } = await import('../src/engine/omp-client.mjs');
const { PROJECT_ROOT } = await import('../../../config/loader.mjs');

const sessionDir = join(PROJECT_ROOT, 'workspace', '.omp-sessions', `omp_binary_chain_${process.pid}`);

function pidTraceLines() {
  if (!existsSync(traceFile)) return [];
  return readFileSync(traceFile, 'utf-8').split(/\r?\n/).filter((l) => /^PID \d+ omp$/.test(l.trim()));
}

after(() => {
  rmSync(work, { recursive: true, force: true });
  rmSync(sessionDir, { recursive: true, force: true });
});

describe('omp binary chain — env override is authoritative for probe AND spawn', () => {
  test('resolveOmpBinary honors HARNESS_OMP_COMMAND and agrees with resolveCliBinary', () => {
    invalidateBinaryCache('omp');
    assert.equal(resolveCliBinary('omp'), shim, 'shared chain resolves the override');
    assert.equal(resolveOmpBinary(), shim, 'the spawn path resolves the SAME binary as the probe');
  });

  test('the availability probe really executes the overridden binary', async () => {
    invalidateBinaryCache('omp');
    const probe = await probeOmpEngine();
    assert.equal(probe.available, true);
    assert.equal(probe.binary, shim, 'probe reports the overridden command, not a PATH install');
    assert.match(String(probe.version), /fake-hang omp/);
    assert.ok(pidTraceLines().length >= 1, 'the fake binary actually ran');
  });

  test('startDiagnosis spawns the overridden binary (fake RPC records its pid)', async () => {
    invalidateBinaryCache('omp');
    const before = pidTraceLines().length;
    const result = startDiagnosis({
      analysisTarget: { mode: 'resume' },
      userQuestion: 'hang',
      sceneName: 'omp_binary_chain',
      runId: `omp_binary_chain_${process.pid}`,
      timeoutMinutes: 0.02, // the fixture never finishes a turn — kill it fast
    });
    try {
      const events = await drain(result.query, { timeoutMs: 12000 });
      const res = findResult(events);
      assert.equal(res.subtype, 'error_during_execution');
      assert.equal(res.stop_reason, 'omp_timeout');
      assert.ok(pidTraceLines().length > before, 'the overridden fake binary is the process that was spawned');
    } finally {
      try { result.query.close(); } catch { /* already closed */ }
    }
  });

  test('a bogus override fails honestly (no silent fallback to a PATH install)', async () => {
    const key = commandEnvKey('omp');
    const previous = process.env[key];
    try {
      process.env[key] = join(work, 'no-such-omp.exe');
      invalidateBinaryCache('omp');
      assert.equal(resolveOmpBinary(), join(work, 'no-such-omp.exe'));
      const probe = await probeOmpEngine();
      assert.equal(probe.available, false);
      assert.match(String(probe.error), /ENOENT/);
    } finally {
      process.env[key] = previous;
      invalidateBinaryCache('omp');
    }
  });

  test('without an override the chain falls back to the install/PATH resolution', () => {
    const key = commandEnvKey('omp');
    const previous = process.env[key];
    try {
      delete process.env[key];
      invalidateBinaryCache('omp');
      const shared = resolveCliBinary('omp');
      const resolved = resolveOmpBinary();
      assert.notEqual(resolved, shim, 'no override → not the fake binary');
      if (shared !== 'omp') {
        assert.equal(resolved, shared, 'shared resolution wins (config path / where / PATH hit)');
      } else {
        assert.ok(resolved === 'omp' || existsSync(resolved), `legacy fallback must be usable (${resolved})`);
      }
    } finally {
      process.env[key] = previous;
      invalidateBinaryCache('omp');
    }
  });
});
