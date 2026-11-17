// P0-3 — hung engine processes must time out.
//
// Every client case below hangs a REAL subprocess (fake CLI completes only the
// handshake, then never finishes the turn) and asserts the engine client:
//   · emits the engine's own timeout error result frame,
//   · kills the process tree for real (verified at the OS level through the
//     fixture's `PID <pid>` trace line — SIGKILL/taskkill never run exit
//     handlers, so an exit trace line would be unreachable on Windows),
//   · terminates the query iteration (drain returns / the guard is cancelled,
//     so no timer or wake listener is left behind).
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { existsSync, mkdtempSync, readFileSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const HANG_FIXTURE = join(here, 'fixtures', 'fake-hang.mjs');
const ONESHOT_FIXTURE = join(here, 'fixtures', 'fake-oneshot.mjs');
const work = mkdtempSync(join(tmpdir(), 'idd-timeout-'));
const traceFile = join(work, 'trace.log');

process.env.FAKE_TRACE = traceFile;

const { makeCliShim, drain, findEvent, findResult, commandEnvKey } = await import('./helpers.mjs');
const {
  withTimeout, invalidateBinaryCache, resolveEngineTimeoutMinutes,
} = await import('../src/engine/cli-common.mjs');
const { createOneShotEngineClient } = await import('../src/engine/one-shot.mjs');
const { createOmpQuery } = await import('../src/engine/omp-client.mjs');
const { withQueryTimeout } = await import('../src/engine/claude-client.mjs');

// Fractional minutes exercise the real kill path in ~1s instead of 2h.
const SHORT_MIN = 0.02;   // 1.2s — handshake-free clients
const DRAIN_MS = 12000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** OS-level liveness: process.kill(pid, 0) is a real existence probe on win32 too. */
function processAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

async function waitForPid(mode, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  const re = new RegExp(`PID (\\d+) ${mode}`);
  while (Date.now() < deadline) {
    if (existsSync(traceFile)) {
      const m = readFileSync(traceFile, 'utf-8').match(re);
      if (m) return Number(m[1]);
    }
    await sleep(50);
  }
  return null;
}

async function waitForDeath(pid, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!processAlive(pid)) return true;
    await sleep(50);
  }
  return false;
}

// ── The helper itself ────────────────────────────────────────────────────
describe('withTimeout — shared turn-timeout guard', () => {
  test('fires after fractional minutes: runs onTimeout, then kills the child', async () => {
    const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
    await sleep(200);
    const calls = [];
    const guard = withTimeout({
      minutes: 0.01, label: 'unit', context: 'Test',
      onTimeout: () => calls.push('onTimeout'),
      child,
    });

    assert.equal(guard.fired, false);
    assert.ok(Math.abs(guard.ms - 600) < 1, `fractional minutes honored (ms=${guard.ms})`);

    const firedMs = await guard.promise;
    assert.ok(Math.abs(firedMs - 600) < 1);
    assert.equal(guard.fired, true);
    assert.deepEqual(calls, ['onTimeout'], 'onTimeout ran exactly once');
    assert.ok(await waitForDeath(child.pid), 'child process really died');
    guard.cancel(); // idempotent after firing — must not throw
  });

  test('cancel() clears the timer — the guard never fires (no lingering timer)', async () => {
    let fires = 0;
    const guard = withTimeout({ minutes: 0.005, label: 'unit', onTimeout: () => { fires += 1; } }); // 300ms
    guard.cancel();
    await sleep(700); // well past the deadline
    assert.equal(guard.fired, false);
    assert.equal(fires, 0);
  });

  test('minutes <= 0 disables the guard (0 = unlimited)', () => {
    for (const minutes of [0, -5, null, undefined, NaN]) {
      const guard = withTimeout({ minutes, onTimeout: () => assert.fail(`must not fire (${minutes})`) });
      assert.equal(guard.ms, 0);
      assert.equal(guard.fired, false);
      guard.cancel();
    }
  });

  test('resolveEngineTimeoutMinutes: explicit run value wins, else the harness config chain', () => {
    assert.equal(resolveEngineTimeoutMinutes('codex', SHORT_MIN), SHORT_MIN);
    assert.equal(resolveEngineTimeoutMinutes('codex', 7), 7);
    // No explicit value / per-engine override → global harness budget (0 = unlimited).
    assert.ok(resolveEngineTimeoutMinutes('codex', 0) >= 0);
    assert.equal(resolveEngineTimeoutMinutes('codex', 0), resolveEngineTimeoutMinutes('codex', undefined));
    assert.equal(resolveEngineTimeoutMinutes('codex', 0), resolveEngineTimeoutMinutes('dsh', 0));
  });
});

// ── One-shot family (real fake CLI that never returns) ───────────────────
describe('one-shot turn timeout (fake CLI stuck for 60s)', () => {
  before(() => {
    process.env[commandEnvKey('fakehang')] = makeCliShim(ONESHOT_FIXTURE, 'gemini', { name: 'fake-hang-oneshot' });
    invalidateBinaryCache('fakehang');
  });
  after(() => { delete process.env[commandEnvKey('fakehang')]; });

  test('emits <engine>_timeout and kills the process (exit observed)', async () => {
    process.env.FAKE_DELAY = '60000'; // engine stays alive long past the timeout
    try {
      const client = createOneShotEngineClient({ id: 'fakehang', buildArgs: () => ['--flag'] });
      const result = client.startDiagnosis({
        analysisTarget: { mode: 'resume' }, userQuestion: 'hang', runId: 'oneshot_hang',
        timeoutMinutes: SHORT_MIN,
      });
      const events = await drain(result.query, { timeoutMs: DRAIN_MS });

      const res = findResult(events);
      assert.equal(res.subtype, 'error_during_execution');
      assert.equal(res.stop_reason, 'fakehang_timeout');
      assert.equal(result.query.killed, true);
      const exit = await result.query.exitPromise;
      assert.ok(exit && (exit.signal === 'SIGKILL' || exit.code !== 0), `exit observed: ${JSON.stringify(exit)}`);

      // Registry hygiene: the timed-out turn leaves no stale state behind — a
      // second turn on the same runId starts clean and times out the same way.
      client.closeQuery('oneshot_hang');
      const again = client.startDiagnosis({
        analysisTarget: { mode: 'resume' }, userQuestion: 'hang', runId: 'oneshot_hang',
        timeoutMinutes: SHORT_MIN,
      });
      const events2 = await drain(again.query, { timeoutMs: DRAIN_MS });
      assert.equal(findResult(events2).stop_reason, 'fakehang_timeout');
      assert.equal(again.query.killed, true);
    } finally {
      delete process.env.FAKE_DELAY;
    }
  });
});

// ── codex app-server (turn accepted, never completed) ────────────────────
describe('codex turn timeout (app-server accepts the turn, never completes)', () => {
  before(() => {
    process.env[commandEnvKey('codex')] = makeCliShim(HANG_FIXTURE, 'codex', { name: 'fake-hang-codex' });
    invalidateBinaryCache('codex');
  });
  after(() => { delete process.env[commandEnvKey('codex')]; });

  test('stalled turn → codex_timeout result + process tree killed', async () => {
    const codex = await import('../src/engine/codex-client.mjs');
    const result = codex.startDiagnosis({
      analysisTarget: { mode: 'resume' }, userQuestion: 'hang', sceneName: 't',
      runId: `codex_hang_${Date.now()}`, reportLanguage: 'en', timeoutMinutes: SHORT_MIN,
    });
    const events = await drain(result.query, { timeoutMs: DRAIN_MS });

    const res = findResult(events);
    assert.equal(res.subtype, 'error_during_execution');
    assert.equal(res.stop_reason, 'codex_timeout');
    assert.equal(result.query.killed, true);

    const pid = await waitForPid('codex');
    assert.ok(pid, 'fixture pid captured');
    assert.ok(await waitForDeath(pid), 'fake codex process really exited');
  });
});

// ── ACP v1 (dsh dialect: session/prompt never resolves) ──────────────────
describe('ACP turn timeout (session/prompt accepted, never resolved)', () => {
  before(() => {
    process.env[commandEnvKey('dsh')] = makeCliShim(HANG_FIXTURE, 'acp', { name: 'fake-hang-dsh' });
    invalidateBinaryCache('dsh');
  });
  after(() => { delete process.env[commandEnvKey('dsh')]; });

  test('stalled session/prompt → dsh_timeout result + process tree killed', async () => {
    const { dshClient } = await import('../src/engine/acp-client.mjs');
    const result = dshClient.startDiagnosis({
      analysisTarget: { mode: 'resume' }, userQuestion: 'hang', sceneName: 't',
      runId: `dsh_hang_${Date.now()}`, reportLanguage: 'en', timeoutMinutes: SHORT_MIN,
    });
    const events = await drain(result.query, { timeoutMs: DRAIN_MS });

    const ready = findEvent(events, 'system', (e) => e.subtype === 'session_ready');
    assert.ok(ready, 'handshake completed — the hang is a stalled prompt, not a dead process');

    const res = findResult(events);
    assert.equal(res.subtype, 'error_during_execution');
    assert.equal(res.stop_reason, 'dsh_timeout');
    assert.equal(result.query.killed, true);

    const pid = await waitForPid('acp');
    assert.ok(pid, 'fixture pid captured');
    assert.ok(await waitForDeath(pid), 'fake ACP engine really exited');
  });
});

// ── opencode (resident serve: SSE never reaches session.idle) ────────────
describe('opencode turn timeout (serve process + SSE stall after prompt delivery)', () => {
  before(() => {
    process.env[commandEnvKey('opencode')] = makeCliShim(HANG_FIXTURE, 'opencode', { name: 'fake-hang-opencode' });
    invalidateBinaryCache('opencode');
  });
  after(() => { delete process.env[commandEnvKey('opencode')]; });

  test('silent SSE stream → opencode_timeout result + serve process killed', async () => {
    const opencode = await import('../src/engine/opencode-client.mjs');
    const result = opencode.startDiagnosis({
      analysisTarget: { mode: 'resume' }, userQuestion: 'hang', sceneName: 't',
      runId: `oc_hang_${Date.now()}`, reportLanguage: 'en',
      timeoutMinutes: 0.06, // 3.6s — leaves room for spawn + readiness probe + session create
    });
    const events = await drain(result.query, { timeoutMs: DRAIN_MS });

    const ready = findEvent(events, 'system', (e) => e.subtype === 'session_ready');
    assert.ok(ready, 'session created — the hang is a silent SSE stream, not a failed spawn');

    const res = findResult(events);
    assert.equal(res.subtype, 'error_during_execution');
    assert.equal(res.stop_reason, 'opencode_timeout');
    assert.equal(result.query.killed, true);

    const pid = await waitForPid('opencode');
    assert.ok(pid, 'fixture pid captured');
    assert.ok(await waitForDeath(pid), 'fake serve process really exited');
  });
});

// ── omp rpc (ready handshake, no agent_end) ──────────────────────────────
// startDiagnosis spawns the real `omp` binary (no override hook), so the
// client is driven directly with a fake RPC process it owns — same query
// object and same timeout guard startDiagnosis wires.
describe('omp turn timeout (RPC ready, agent_end never arrives)', () => {
  test('silent process → omp_timeout result + process tree killed', async () => {
    const proc = spawn(process.execPath, [HANG_FIXTURE, 'omp'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, FAKE_TRACE: traceFile },
      windowsHide: true,
    });
    try {
      const query = createOmpQuery(proc, { runKey: 'omp_hang', label: 'test-omp', timeoutMinutes: SHORT_MIN });
      await query.sendPrompt('hang'); // fixture is mid-turn from here on — never finishes

      const events = await drain(query, { timeoutMs: DRAIN_MS });
      const res = findResult(events);
      assert.equal(res.subtype, 'error_during_execution');
      assert.equal(res.stop_reason, 'omp_timeout');
      assert.equal(query.killed, true);

      const pid = await waitForPid('omp');
      assert.ok(pid, 'fixture pid captured');
      assert.ok(await waitForDeath(pid), 'fake OMP process really exited');
    } finally {
      if (proc.exitCode === null && proc.signalCode === null) { try { proc.kill('SIGKILL'); } catch { /* ignore */ } }
    }
  });
});

// ── claude SDK path (fake Query: async iterator, no abort support needed) ──
function makeFakeSdkQuery({ sessionId = 'sess-fake-1' } = {}) {
  const stats = { interrupt: 0, close: 0, disposed: 0, streamInputs: 0 };
  let closed = false;
  return {
    sessionId,
    interrupt() { stats.interrupt += 1; return Promise.resolve(undefined); },
    close() { stats.close += 1; closed = true; },
    streamInput() { stats.streamInputs += 1; return Promise.resolve(); },
    [Symbol.asyncIterator]() {
      return {
        next: () => (closed ? Promise.resolve({ done: true, value: undefined }) : new Promise(() => { /* hung turn */ })),
        return: () => { stats.disposed += 1; return Promise.resolve({ done: true }); },
      };
    },
    stats,
  };
}

describe('claude SDK query timeout wrapper', () => {
  test('timeout: interrupt + close the SDK query, emit claude_timeout, end the loop', async () => {
    const fake = makeFakeSdkQuery();
    const guarded = withQueryTimeout(fake, { minutes: 0.01, runId: 'sdk_hang' });

    const events = [];
    for await (const msg of guarded) events.push(msg); // must terminate on its own

    const res = events.find((e) => e.type === 'result');
    assert.ok(res, 'result frame emitted');
    assert.equal(res.subtype, 'error_during_execution');
    assert.equal(res.stop_reason, 'claude_timeout');
    assert.equal(res.session_id, 'sess-fake-1');
    assert.equal(typeof res.duration_ms, 'number');

    await sleep(20); // fire-and-forget interrupt settles on the next tick
    assert.equal(fake.stats.close, 1, 'SDK query closed exactly once');
    assert.equal(fake.stats.interrupt, 1, 'SDK interrupt attempted');
    assert.equal(fake.stats.disposed, 1, 'underlying iterator disposed — no dangling pull');
  });

  test('sessionId / streamInput pass through to the SDK query', async () => {
    const fake = makeFakeSdkQuery();
    const guarded = withQueryTimeout(fake, { minutes: 0, runId: 'sdk_pass' }); // unlimited → raw query
    assert.equal(guarded, fake, '0 minutes passes the raw query through');

    const limited = withQueryTimeout(makeFakeSdkQuery({ sessionId: 'sess-2' }), { minutes: 5, runId: 'sdk_pass2' });
    assert.equal(limited.sessionId, 'sess-2');
    await limited.streamInput((async function* () {})());
    limited.close();
  });

  test('external close() cancels the guard — no late timeout result', async () => {
    const fake = makeFakeSdkQuery();
    const guarded = withQueryTimeout(fake, { minutes: 0.01, runId: 'sdk_close' });
    guarded.close();
    assert.equal(fake.stats.close, 1);
    await sleep(900); // well past the 600ms deadline
    assert.equal(fake.stats.interrupt, 0, 'guard never fired');
    assert.equal(fake.stats.close, 1);
  });
});
