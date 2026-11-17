// P0-5 concurrency governance — end-to-end through the mock engine with an
// isolated DB, exactly as a client drives it (create → trigger):
//
//   MAX_CONCURRENT_RUNS=2 → run 3 is stored 'queued' (never repurposing
//   'pending'), re-triggering a queued run is idempotent, and when a slot frees
//   the queued run starts through the SAME execution path and completes. A
//   queued run that is stopped leaves the FIFO and never starts.
//
// The env is set BEFORE the service import: config/loader.mjs and the DB
// resolve their paths at module load (same pattern as files.service.test.mjs).
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const workDir = mkdtempSync(join(tmpdir(), 'idd-cc-queue-'));
process.env.DATABASE_PATH = join(workDir, 'concurrency.db');
process.env.MAX_CONCURRENT_RUNS = '2';
// Runs schedule closeRun(delay) after their stream ends — keep the delay at 0
// so this in-process test does not sit on 60s timers per completed run.
process.env.ENGINE_CLOSE_RUN_DELAY = '0';

const svc = await import('../src/services/diagnosis.service.mjs');

process.on('exit', () => {
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

function startMockRun(tag) {
  return svc.createDiagnosisRun({
    harness: 'mock',
    dataPath: 'data/smoke.csv',
    sceneName: `cc_queue_${tag}`,
    userQuestion: `concurrency queue ${tag}`,
    reportLanguage: 'zh',
  });
}

async function waitForStatus(runId, statuses, timeoutMs = 25000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = svc.getRunStatus(runId);
    if (last && statuses.includes(last.status)) return last;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`run ${runId} did not reach ${statuses} (last: ${last?.status})`);
}

describe('resolveMaxConcurrentRuns — env override → config fallback', () => {
  test('env wins, invalid env falls back to config, absent env uses the config value', () => {
    try {
      assert.equal(svc.resolveMaxConcurrentRuns(), 2);
      process.env.MAX_CONCURRENT_RUNS = '3';
      assert.equal(svc.resolveMaxConcurrentRuns(), 3);
      process.env.MAX_CONCURRENT_RUNS = 'not-a-number';
      assert.equal(svc.resolveMaxConcurrentRuns(), 2, 'config diagnosis.max_concurrent_runs');
      delete process.env.MAX_CONCURRENT_RUNS;
      assert.equal(svc.resolveMaxConcurrentRuns(), 2, 'config default');
    } finally {
      process.env.MAX_CONCURRENT_RUNS = '2';
    }
  });
});

describe('MAX_CONCURRENT_RUNS — FIFO admission through the real execution path', () => {
  test('third run is stored queued; it starts when a slot frees and completes', async () => {
    const a = startMockRun('a');
    const b = startMockRun('b');
    const c = startMockRun('c');

    assert.deepEqual(svc.triggerDiagnosis(a.runId), { runId: a.runId, status: 'running' });
    assert.deepEqual(svc.triggerDiagnosis(b.runId), { runId: b.runId, status: 'running' });
    const third = svc.triggerDiagnosis(c.runId);
    assert.equal(third.status, 'queued');
    assert.equal(third.queuePosition, 1);
    assert.equal(third.maxConcurrentRuns, 2);

    // All of the above is synchronous (the mock's first emission is ≥30ms
    // away), so the stored statuses are exactly the admission decision.
    assert.equal(svc.getRunStatus(a.runId).status, 'running');
    assert.equal(svc.getRunStatus(b.runId).status, 'running');
    assert.equal(svc.getRunStatus(c.runId).status, 'queued');
    const snap = svc.getConcurrencySnapshot();
    assert.deepEqual([...snap.executing].sort(), [a.runId, b.runId].sort());
    assert.deepEqual(snap.queued, [c.runId]);

    // A repeated /execute for the queued run is idempotent — no second slot.
    const again = svc.triggerDiagnosis(c.runId);
    assert.equal(again.status, 'queued');
    assert.equal(again.queuePosition, 1);
    assert.deepEqual(svc.getConcurrencySnapshot().queued, [c.runId]);

    // Dedup by runId for an executing run is unchanged: the pending gate refuses.
    assert.throws(
      () => svc.triggerDiagnosis(a.runId),
      (e) => e.status === 400 && /not pending/.test(e.message),
    );

    // The queued run runs through the same execution path once a and b settle.
    const finalC = await waitForStatus(c.runId, ['completed', 'failed']);
    assert.equal(finalC.status, 'completed', finalC.error_message || '');
    const statuses = svc.getRunEventStream(c.runId)
      .filter((e) => e.type === 'status')
      .map((e) => e.data?.status);
    assert.ok(statuses.includes('queued'), `queued status recorded: ${statuses}`);
    assert.ok(statuses.indexOf('running') > statuses.indexOf('queued'), `queued precedes running: ${statuses}`);
    assert.equal(statuses[statuses.length - 1], 'completed');

    await waitForStatus(a.runId, ['completed', 'failed']);
    await waitForStatus(b.runId, ['completed', 'failed']);
    assert.deepEqual(svc.getConcurrencySnapshot().queued, []);
  });

  test('a stopped queued run leaves the FIFO and never starts', async () => {
    const d = startMockRun('d');
    const e = startMockRun('e');
    const f = startMockRun('f');
    svc.triggerDiagnosis(d.runId);
    svc.triggerDiagnosis(e.runId);
    assert.equal(svc.triggerDiagnosis(f.runId).status, 'queued');

    svc.stopDiagnosis(f.runId);
    assert.equal(svc.getRunStatus(f.runId).status, 'stopped');
    assert.deepEqual(svc.getConcurrencySnapshot().queued, []);

    await waitForStatus(d.runId, ['completed', 'failed']);
    await waitForStatus(e.runId, ['completed', 'failed']);
    // Give any wrong drain a chance to (not) start the stopped run.
    await new Promise((r) => setTimeout(r, 200));
    assert.equal(svc.getRunStatus(f.runId).status, 'stopped');
  });

  test('a queued row without a FIFO entry (restart orphan) is re-admitted by /execute', async () => {
    const g = startMockRun('g');
    // Simulate a process restart: the row says queued while the in-memory FIFO
    // is empty. /execute must re-admit it, not refuse it or leak its slot.
    const { stmts } = await import('../src/db/database.mjs');
    stmts.updateRunStatus.run({ runId: g.runId, status: 'queued' });
    assert.deepEqual(svc.getConcurrencySnapshot().queued, []);

    const res = svc.triggerDiagnosis(g.runId);
    assert.equal(res.status, 'running', 'capacity is free — the orphan runs');
    const done = await waitForStatus(g.runId, ['completed', 'failed']);
    assert.equal(done.status, 'completed', done.error_message || '');
  });
});
