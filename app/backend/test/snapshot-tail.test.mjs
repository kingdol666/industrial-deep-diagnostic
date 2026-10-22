// Snapshot window + event-log retention (2026-10-22 remediation, Phase A).
//
// A long claude run emitted 53,490 events; GET /snapshot serialized all of them
// (11.5 MB) while the UI only renders the tail. These tests pin the bounded
// read, its truthful metadata, and the per-run row cap (MAX(seq) preserved).
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const {
  getRunRealtimeSnapshot, getRunEventStreamTail, clampSnapshotEventsLimit,
  SNAPSHOT_EVENTS_DEFAULT, SNAPSHOT_EVENTS_MAX,
} = await import('../src/services/diagnosis.service.mjs');
const { applyEventStreamRetention } = await import('../src/services/retention.service.mjs');
const { db, stmts } = await import('../src/db/database.mjs');
const { config } = await import('../../../config/loader.mjs');

const RUN = 'zz-snapshot-tail';
const RUN_PRUNE = 'zz-snapshot-prune';

function cleanup(id = RUN) {
  try { stmts.deleteEventStreamByRunId.run(id); } catch { /* ignore */ }
  try { stmts.deleteLogsByRunId.run(id); } catch { /* ignore */ }
  try { stmts.deleteRunRow.run(id); } catch { /* ignore */ }
}

function insertRun(id) {
  stmts.insertRun.run({
    runId: id, name: id, title: id, sceneName: 'zz_snapshot_scene',
    dataPath: 'data/smoke.csv', dataFolder: null, userQuestion: '',
    model: null, maxTurns: 10, reportLanguage: 'zh', harness: 'claude',
    ontologyHit: 0, enhancementPolicy: 'auto', enhancementTriggered: 0,
    analysisIntent: 'deep-diagnosis', userId: null,
  });
  stmts.updateRunStatus.run({ runId: id, status: 'completed' });
}

function insertEvents(id, count, extra = []) {
  const insert = db.transaction(() => {
    for (let i = 0; i < count; i += 1) {
      stmts.insertEventStream.run({
        runId: id,
        seq: i,
        eventType: 'message',
        eventSubtype: null,
        payloadJson: JSON.stringify({ type: 'message', data: { content: `m${i}` }, seq: i }),
      });
    }
    for (const ev of extra) {
      stmts.insertEventStream.run({
        runId: id,
        seq: ev.seq,
        eventType: ev.type,
        eventSubtype: ev.subtype || null,
        payloadJson: JSON.stringify(ev),
      });
    }
  });
  insert();
}

describe('snapshot event window', () => {
  test('limit is clamped to a usable range', () => {
    assert.equal(clampSnapshotEventsLimit(undefined), SNAPSHOT_EVENTS_DEFAULT);
    assert.equal(clampSnapshotEventsLimit('abc'), SNAPSHOT_EVENTS_DEFAULT);
    assert.equal(clampSnapshotEventsLimit(0), SNAPSHOT_EVENTS_DEFAULT);
    assert.equal(clampSnapshotEventsLimit(10), 100);
    assert.equal(clampSnapshotEventsLimit(500), 500);
    assert.equal(clampSnapshotEventsLimit(999999), SNAPSHOT_EVENTS_MAX);
  });

  test('snapshot returns the newest N events with truthful totals', () => {
    cleanup(RUN);
    try {
      insertRun(RUN);
      insertEvents(RUN, 50);
      const snap = getRunRealtimeSnapshot(RUN, { eventsLimit: 100 });
      assert.equal(snap.events.length, 50);
      assert.equal(snap.events_total, 50);
      assert.equal(snap.events_truncated, false);

      const { events, total } = getRunEventStreamTail(RUN, 100);
      assert.equal(total, 50);
      assert.equal(events.length, 50);
      assert.deepEqual(events.slice(-1).map((e) => e._seq), [49]);
      assert.ok(events.every((e, i, arr) => i === 0 || e._seq > arr[i - 1]._seq), 'ascending seq');
    } finally { cleanup(RUN); }
  });

  test('tail read is bounded (does not scan/serialize the whole run)', () => {
    cleanup(RUN);
    try {
      insertRun(RUN);
      insertEvents(RUN, 5000);
      const started = performance.now();
      const snap = getRunRealtimeSnapshot(RUN, { eventsLimit: 200 });
      const elapsed = performance.now() - started;
      assert.equal(snap.events.length, 200);
      assert.equal(snap.events_total, 5000);
      assert.equal(snap.events_truncated, true);
      assert.deepEqual(snap.events.slice(-1).map((e) => e._seq), [4999]);
      assert.ok(elapsed < 500, `tail snapshot took ${elapsed.toFixed(1)}ms`);
    } finally { cleanup(RUN); }
  });

  test('pending question is derived from the visible tail', () => {
    cleanup(RUN);
    try {
      insertRun(RUN);
      insertEvents(RUN, 10, [
        { type: 'question', seq: 10, data: { questionId: 'q1', toolUseId: 't1', questions: [] } },
      ]);
      const asking = getRunRealtimeSnapshot(RUN, { eventsLimit: 100 });
      assert.equal(asking.currentQuestion?.questionId, 'q1');

      stmts.insertEventStream.run({
        runId: RUN, seq: 11, eventType: 'question_result', eventSubtype: null,
        payloadJson: JSON.stringify({ type: 'question_result', data: { questionId: 'q1' } }),
      });
      const answered = getRunRealtimeSnapshot(RUN, { eventsLimit: 100 });
      assert.equal(answered.currentQuestion, null);
    } finally { cleanup(RUN); }
  });
});

describe('event-log retention per run', () => {
  test('prunes oldest rows, keeps MAX(seq) for session-chat continuation', () => {
    cleanup(RUN_PRUNE);
    const original = config.data.event_stream_max_rows_per_run;
    try {
      insertRun(RUN_PRUNE);
      insertEvents(RUN_PRUNE, 500);
      assert.equal(stmts.countEventStreamByRunId.get(RUN_PRUNE).n, 500);

      config.data.event_stream_max_rows_per_run = 100;
      // Scope the sweep to THIS test run — never call the global sweep with a
      // test-sized cap (it would prune every run in the database).
      const { eventRunsPruned, eventRowsDeleted } = applyEventStreamRetention({ runIds: [RUN_PRUNE] });
      assert.ok(eventRunsPruned >= 1, JSON.stringify({ eventRunsPruned, eventRowsDeleted }));
      assert.ok(eventRowsDeleted >= 400, JSON.stringify({ eventRunsPruned, eventRowsDeleted }));

      assert.equal(stmts.countEventStreamByRunId.get(RUN_PRUNE).n, 100);
      assert.equal(stmts.getMaxEventSeq.get(RUN_PRUNE).maxSeq, 499);
      const tail = getRunEventStreamTail(RUN_PRUNE, 1000);
      assert.equal(tail.total, 100);
      assert.equal(tail.events[0]._seq, 400);
      assert.equal(tail.events.at(-1)._seq, 499);
    } finally {
      config.data.event_stream_max_rows_per_run = original;
      cleanup(RUN_PRUNE);
    }
  });
});
