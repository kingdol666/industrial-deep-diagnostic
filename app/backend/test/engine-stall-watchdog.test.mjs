// Slow-run watchdog (plan phase 5.4) — classifyStall semantics + the sweep's
// warn-once / re-arm / terminal-silence contract against the REAL engine module.
//
// The decision is a pure function precisely so it can be tested with an
// explicit clock instead of timers; the integration half then drives
// sweepStalledRuns (the same function the housekeeping interval calls) with a
// faked `now` and asserts the informational `run_stalled` event is emitted and
// persisted exactly once per idle window.

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const workDir = mkdtempSync(join(tmpdir(), 'idd-stall-watchdog-'));
process.env.DATABASE_PATH = join(workDir, 'stall.db');
process.env.ENGINE_CLOSE_RUN_DELAY = '0';

const {
  classifyStall, createRun, updateStatus, emit, subscribe, sweepStalledRuns, closeRun, getEvents,
} = await import('../src/engine/diagnosis-engine.mjs');
const { stmts } = await import('../src/db/database.mjs');

process.on('exit', () => {
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

const MIN = 60_000;
const T0 = 1_700_000_000_000; // fixed clock for the pure cases
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

describe('classifyStall — pure decision', () => {
  test('stalls only when running AND idle past the threshold', () => {
    const at = (now) => classifyStall({ status: 'running', lastEventTs: T0, now, thresholdMinutes: 10, lastWarnedFor: null });
    assert.equal(at(T0 + 9 * MIN).stalled, false, 'inside the threshold: no stall');
    const verdict = at(T0 + 11 * MIN);
    assert.equal(verdict.stalled, true, 'past the threshold: stall');
    assert.equal(verdict.mark, T0, 'the mark is the last-event timestamp the decision was made on');
    assert.equal(verdict.idleMs, 11 * MIN);
  });

  test('warns once per idle window and re-arms only after activity', () => {
    // The caller stores `mark` as lastWarnedFor after warning.
    const warm = 11 * MIN;
    const first = classifyStall({ status: 'running', lastEventTs: T0, now: T0 + warm, thresholdMinutes: 10, lastWarnedFor: null });
    assert.equal(first.stalled, true);

    const sameWindow = classifyStall({ status: 'running', lastEventTs: T0, now: T0 + warm + 5 * MIN, thresholdMinutes: 10, lastWarnedFor: first.mark });
    assert.equal(sameWindow.stalled, false, 'the same idle window never warns twice');

    // Real activity moved the clock past the mark, then silence returned.
    const T1 = T0 + warm + 5 * MIN;
    const afterActivity = classifyStall({ status: 'running', lastEventTs: T1, now: T1 + 11 * MIN, thresholdMinutes: 10, lastWarnedFor: first.mark });
    assert.equal(afterActivity.stalled, true, 'activity re-arms the window');
    assert.equal(afterActivity.mark, T1);
  });

  test('terminal / non-running / untimed / disabled cases never stall', () => {
    for (const status of ['completed', 'failed', 'stopped', 'pending', 'queued', 'awaiting_input']) {
      assert.equal(
        classifyStall({ status, lastEventTs: T0, now: T0 + 999 * MIN, thresholdMinutes: 10, lastWarnedFor: null }).stalled,
        false,
        `${status} must never be reported as stalled`,
      );
    }
    assert.equal(classifyStall({ status: 'running', lastEventTs: null, now: T0 + 999 * MIN, thresholdMinutes: 10 }).stalled, false,
      'no last-event timestamp → nothing to reason about');
    assert.equal(classifyStall({ status: 'running', lastEventTs: T0, now: T0 + 999 * MIN, thresholdMinutes: 0 }).stalled, false,
      'threshold 0 disables the watchdog');
    assert.equal(classifyStall({ status: undefined, lastEventTs: T0, now: T0 + 999 * MIN, thresholdMinutes: 10 }).stalled, false,
      'no status (unknown run) → no stall');
  });
});

describe('sweepStalledRuns — engine event path', () => {
  test('emits + persists run_stalled once, re-arms on activity, stays silent when terminal', async () => {
    const runId = `stall_run_${Date.now().toString(36)}`;
    stmts.insertRun.run({
      runId,
      name: runId,
      sceneName: 'stall_watchdog_scene',
      dataPath: 'data/smoke.csv',
      dataFolder: null,
      userQuestion: 'watchdog probe',
      model: 'mock',
      maxTurns: 1,
      reportLanguage: 'zh',
      harness: 'mock',
      ontologyHit: null,
      enhancementPolicy: null,
      enhancementTriggered: 0,
      analysisIntent: null,
      timeoutMinutes: null,
      ownerUserId: null,
    });

    createRun(runId);
    updateStatus(runId, 'running'); // starts the idle clock
    const seen = [];
    const unsubscribe = subscribe(runId, (event) => seen.push(event));
    const stalls = () => seen.filter((e) => e.type === 'run_stalled');
    const created = Date.now();

    // 1) Idle past the threshold → exactly one warning + one stream notice.
    sweepStalledRuns(created + 11 * MIN);
    assert.equal(stalls().length, 1, 'first idle window warns once');
    assert.equal(stalls()[0].data.idleMinutes, 11);
    assert.equal(stalls()[0].data.runId, runId);

    // 2) Still idle, same window → the notice itself must not re-arm the window.
    sweepStalledRuns(created + 13 * MIN);
    assert.equal(stalls().length, 1, 'no repeat warning inside the same idle window');

    // 3) Real activity, then silence again → warns again for the new window.
    // (The 5ms pause keeps the activity event strictly newer than the anchor
    // set by the notice: in production the anchor is ≥ threshold old, so this
    // only matters inside a same-millisecond unit test.)
    await sleep(5);
    emit(runId, { type: 'system', subtype: 'activity', data: { note: 'engine resumed' } });
    sweepStalledRuns(Date.now() + 11 * MIN);
    assert.equal(stalls().length, 2, 'activity re-arms the watchdog');

    // 4) Terminal runs stay silent (state is reset on the status transition).
    updateStatus(runId, 'completed');
    sweepStalledRuns(Date.now() + 60 * MIN);
    assert.equal(stalls().length, 2, 'a completed run never warns');

    // The notice is an ordinary stream event: buffered for WS/SSE replay and
    // persisted like any other event.
    assert.equal(getEvents(runId).filter((e) => e.type === 'run_stalled').length, 2);
    const persisted = stmts.getEventStreamByRunId.all(runId).filter((row) => row.event_type === 'run_stalled');
    assert.equal(persisted.length, 2, 'run_stalled reaches the persisted event stream');

    unsubscribe();
    closeRun(runId); // terminal cleanup: the watchdog state dies with the record
    sweepStalledRuns(Date.now() + 120 * MIN);
    assert.equal(stalls().length, 2, 'a closed run cannot warn');
  });
});
