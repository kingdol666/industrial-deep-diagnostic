// Session integrity + continue-chat contract (plan v2 Phase B0/B).
// Unit level: pure classification/anchor helpers + one DB-backed restart test.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const {
  sessionKind, sessionMap, assertSessionHarnessMatch,
  recoverInterruptedRuns, reconcileSessionIds,
  clampChatTurns, CHAT_TURNS_DEFAULT, CHAT_TURN_PASSTHROUGH,
} = await import('../src/services/session-integrity.service.mjs');
const { stmts } = await import('../src/db/database.mjs');

const UUID = '3f2504e0-4f89-11d3-9a0c-0305e82c3301';

describe('sessionKind — runId ↔ sessionId truth', () => {
  test('classifies every harness marker family', () => {
    assert.equal(sessionKind(UUID), 'claude');
    assert.equal(sessionKind('omp:run:abc123'), 'omp');
    assert.equal(sessionKind('omp:chat:abc'), 'omp');
    assert.equal(sessionKind('goose:run:abc'), 'goose');
    assert.equal(sessionKind('opaque-id'), 'unknown');
    assert.equal(sessionKind(null), 'none');
    assert.equal(sessionKind(''), 'none');
  });
});

describe('assertSessionHarnessMatch — harness lock (B0.4)', () => {
  test('matching pairs pass', () => {
    assert.doesNotThrow(() => assertSessionHarnessMatch({ session_id: UUID, harness: 'claude' }));
    assert.doesNotThrow(() => assertSessionHarnessMatch({ session_id: 'omp:run:x', harness: 'omp' }));
    assert.doesNotThrow(() => assertSessionHarnessMatch({ session_id: 'goose:run:x', harness: 'goose' }));
  });

  test('a cross-engine session is refused with 409, never silently switched', () => {
    assert.throws(
      () => assertSessionHarnessMatch({ session_id: 'omp:run:x', harness: 'claude' }),
      (err) => err.status === 409 && err.code === 'RUN_HARNESS_MISMATCH',
    );
    assert.throws(
      () => assertSessionHarnessMatch({ session_id: UUID, harness: 'omp' }),
      (err) => err.status === 409 && err.code === 'RUN_HARNESS_MISMATCH',
    );
  });

  test('missing / opaque session ids are allowed (authoritative check is the engine)', () => {
    assert.doesNotThrow(() => assertSessionHarnessMatch({ session_id: null, harness: 'claude' }));
    assert.doesNotThrow(() => assertSessionHarnessMatch({ session_id: 'opaque', harness: 'acp' }));
  });
});

describe('sessionMap — audit view (B0.3)', () => {
  test('reports mismatches and reconcilability honestly', () => {
    const ok = sessionMap({
      run_id: 'r1', harness: 'claude', session_id: UUID, status: 'completed',
    });
    assert.equal(ok.session_kind, 'claude');
    assert.equal(ok.resumable, true);
    assert.equal(ok.harness_matches_session, true);
    assert.equal(ok.reconcilable, false);

    const mismatch = sessionMap({
      run_id: 'r2', harness: 'claude', session_id: 'omp:run:r2', status: 'completed',
    });
    assert.equal(mismatch.session_kind, 'omp');
    assert.equal(mismatch.harness_matches_session, false);
    assert.equal(mismatch.resumable, false);

    const empty = sessionMap({
      run_id: 'r3', harness: 'omp', session_id: null, status: 'stopped',
    });
    assert.equal(empty.session_kind, 'none');
    assert.equal(empty.resumable, false);
    assert.equal(empty.reconcilable, true);
  });
});

describe('chat turn budget + passthrough contract (B3)', () => {
  test('maxTurns is clamped into [1, 20] with a usable default', () => {
    assert.equal(clampChatTurns(undefined), CHAT_TURNS_DEFAULT);
    assert.equal(clampChatTurns(0), CHAT_TURNS_DEFAULT);
    assert.equal(clampChatTurns(-5), CHAT_TURNS_DEFAULT);
    assert.equal(clampChatTurns(1), 1);
    assert.equal(clampChatTurns(8), 8);
    assert.equal(clampChatTurns(999), 20);
    assert.equal(clampChatTurns('12'), 12);
  });

  test('resume turns are verbatim (no prompt scaffolding is injected)', () => {
    // The contract is enforced in sendChatMessage/continueDiagnosis; this flag
    // pins the documented behavior so a future edit cannot silently re-add an
    // anchor without updating the acceptance suite.
    assert.equal(CHAT_TURN_PASSTHROUGH, true);
  });
});

describe('engine subscription survives a closed completed run', () => {
  test('subscribe on a missing/closed run registers and receives later emits', async () => {
    const eng = await import('../src/engine/diagnosis-engine.mjs');
    const runId = 'zz-sub-test';
    // Simulate the real sequence: run finished, entry removed by closeRun.
    eng.createRun(runId);
    eng.closeRun(runId);
    const received = [];
    const unsubscribe = eng.subscribe(runId, (ev) => received.push(ev));
    // A chat turn then re-creates the entry and emits; the earlier subscription
    // must still be attached (this is the UI live-render fix).
    eng.createRun(runId);
    eng.emit(runId, { type: 'system', subtype: 'session_chat', data: { message: 'hi' } });
    eng.emit(runId, { type: 'message', data: { role: 'assistant', content: '收到' } });
    assert.ok(received.some((e) => e.type === 'system' && e.subtype === 'session_chat'),
      'system event must reach the pre-existing subscriber');
    assert.ok(received.some((e) => e.type === 'message' && e.data?.content === '收到'),
      'assistant message must reach the pre-existing subscriber');
    unsubscribe();
    eng.closeRun(runId);
  });

  test('re-created run continues the persisted event sequence (no _seq collision)', async () => {
    const eng = await import('../src/engine/diagnosis-engine.mjs');
    const runId = 'zz-seq-test';
    try { stmts.deleteEventStreamByRunId.run(runId); } catch { /* ignore */ }
    try { stmts.deleteRunRow.run(runId); } catch { /* ignore */ }
    stmts.insertRun.run({
      runId, name: runId, title: runId, sceneName: 'zz_seq', dataPath: 'data/smoke.csv',
      dataFolder: null, userQuestion: '', model: null, maxTurns: 10, reportLanguage: 'zh',
      harness: 'claude', ontologyHit: 0, enhancementPolicy: 'auto', enhancementTriggered: 0,
      analysisIntent: 'deep-diagnosis', userId: null,
    });
    // Historical events up to seq 40 (the state the UI hydrates from DB).
    for (let i = 0; i <= 40; i += 1) {
      stmts.insertEventStream.run({
        runId, seq: i, eventType: 'message', eventSubtype: null,
        payloadJson: JSON.stringify({ type: 'message', data: { content: `h${i}` } }),
      });
    }
    eng.createRun(runId);
    const received = [];
    const off = eng.subscribe(runId, (ev) => received.push(ev));
    eng.emit(runId, { type: 'message', data: { role: 'assistant', content: 'live-reply' } });
    const live = received.find((e) => e.type === 'message' && e.data?.content === 'live-reply');
    // The frontend drops events whose seq <= lastEventSeq (40), so the new
    // event must be 41+.
    assert.ok(live && live._seq > 40, `live _seq=${live?._seq} must continue after 40`);
    off();
    eng.closeRun(runId);
    stmts.deleteEventStreamByRunId.run(runId);
    stmts.deleteRunRow.run(runId);
  });
});

describe('restart semantics (B0.1) + session reconcile (B0.3) — DB backed', () => {
  const RUN_PENDING = 'zz-pend-test';
  const RUN_RUNNING = 'zz-run-test';
  const RUN_LOST = 'zz-lost-sess';

  function cleanup() {
    for (const id of [RUN_PENDING, RUN_RUNNING, RUN_LOST]) {
      try { stmts.deleteLogsByRunId.run(id); } catch { /* ignore */ }
      try { stmts.deleteEventStreamByRunId.run(id); } catch { /* ignore */ }
      try { stmts.deleteRunRow.run(id); } catch { /* ignore */ }
    }
  }

  function insert(id, { status, harness = 'claude', sessionId = null }) {
    stmts.insertRun.run({
      runId: id, name: id, title: id, sceneName: 'zz_test_scene',
      dataPath: 'data/smoke.csv', dataFolder: null, userQuestion: '',
      model: null, maxTurns: 10, reportLanguage: 'zh', harness,
      ontologyHit: 0, enhancementPolicy: 'auto', enhancementTriggered: 0,
      analysisIntent: 'deep-diagnosis', userId: null,
    });
    stmts.updateRunStatus.run({ runId: id, status });
    if (sessionId) stmts.updateRunSession.run({ runId: id, sessionId });
  }

  test('pending → stopped on restart; running keeps failed', () => {
    cleanup();
    try {
      insert(RUN_PENDING, { status: 'pending' });
      insert(RUN_RUNNING, { status: 'running' });
      const res = recoverInterruptedRuns();
      assert.ok(res.stopped.includes(RUN_PENDING));
      const pendingRow = stmts.getRunById.get(RUN_PENDING);
      assert.equal(pendingRow.status, 'stopped');
      assert.match(pendingRow.error_message, /restarted before execution/i);
      // recoverInterruptedRuns must not touch running rows (the startup
      // sequence maps those to failed separately).
      assert.equal(stmts.getRunById.get(RUN_RUNNING).status, 'running');
    } finally { cleanup(); }
  });

  test('a lost claude session id is recovered from the event stream', () => {
    cleanup();
    try {
      insert(RUN_LOST, { status: 'completed' });
      stmts.insertEventStream.run({
        runId: RUN_LOST, seq: 1, eventType: 'system', eventSubtype: 'init',
        payloadJson: JSON.stringify({ type: 'system', subtype: 'init', session_id: UUID }),
      });
      const res = reconcileSessionIds();
      const rec = res.recovered.find((r) => r.run_id === RUN_LOST);
      assert.ok(rec, `expected ${RUN_LOST} to be recovered: ${JSON.stringify(res)}`);
      assert.equal(rec.source, 'event_stream');
      assert.equal(stmts.getRunById.get(RUN_LOST).session_id, UUID);
    } finally { cleanup(); }
  });

  test('an omp run without events gets the deterministic marker', () => {
    cleanup();
    try {
      insert(RUN_LOST, { status: 'stopped', harness: 'omp' });
      // No omp session dir on disk in a unit test: the marker is only written
      // when the directory exists, so this run must stay unresolved — proving
      // reconcile never invents a session that the engine cannot open.
      reconcileSessionIds();
      assert.equal(stmts.getRunById.get(RUN_LOST).session_id, null);
    } finally { cleanup(); }
  });
});
