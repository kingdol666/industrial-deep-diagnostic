// D4 — the per-run `timeoutMinutes` knob must actually reach the engine.
//
// Defect: createDiagnosisRun kept the value in in-process meta only, while
// executeDiagnosis passes `run.timeout_minutes` — a column diagnostic_runs did
// not have. The API knob was therefore dead: a hung engine ran to the harness
// default (120 min) instead of the requested budget. This test drives the REAL
// service path (createDiagnosisRun → triggerDiagnosis → engine dispatch) with a
// hung fake one-shot CLI and asserts:
//   · the value is persisted on the row the execution path reads (and is what
//     /status serves), not just in memory,
//   · the hung engine is killed and the run reaches the terminal 'failed' state
//     with the documented "Query stopped: <engine>_timeout" error, at the tiny
//     requested timeout,
//   · a later /execute of the same run still finds the value in the DB (a
//     fresh row read — the meta-only path could not survive this).
import { test, describe, after, before } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const workDir = mkdtempSync(join(tmpdir(), 'idd-run-timeout-'));

// Isolated DB + a hung fake gemini CLI — both must be in place BEFORE the
// service (and its config/DB modules) are imported.
process.env.DATABASE_PATH = join(workDir, 'timeout.db');
process.env.MAX_CONCURRENT_RUNS = '2';
process.env.ENGINE_CLOSE_RUN_DELAY = '0';
process.env.FAKE_DELAY = '60000'; // the fake CLI stays silent past any test timeout

const { makeCliShim, commandEnvKey } = await import('./helpers.mjs');
process.env[commandEnvKey('gemini')] = makeCliShim(join(here, 'fixtures', 'fake-oneshot.mjs'), 'gemini', {
  name: 'fake-timeout-gemini', dir: workDir,
});

const { stmts } = await import('../src/db/database.mjs');
const { getMeta } = await import('../src/engine/diagnosis-engine.mjs');
const svc = await import('../src/services/diagnosis.service.mjs');

const TINY_TIMEOUT_MIN = 0.02; // 1.2s — the real kill path, fast

process.on('exit', () => {
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

// The verifier's repro vector, verbatim at the HTTP layer:
//   POST /api/diagnosis/start { harness, timeoutMinutes } + POST /execute/:runId
let server;
let baseUrl;

before(async () => {
  const express = (await import('express')).default;
  const { default: diagnosisRoutes } = await import('../src/routes/diagnosis.routes.mjs');
  const app = express();
  app.use(express.json());
  app.use('/api/diagnosis', diagnosisRoutes);
  server = app.listen(0);
  await new Promise((r) => server.once('listening', r));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(() => { if (server) server.close(); });

async function api(method, path, body) {
  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, json: await res.json().catch(() => ({})) };
}

function createHungRun(tag, params = {}) {
  return svc.createDiagnosisRun({
    harness: 'gemini',
    // non-default intent: skip ontology/enhancement resolution (the fixture
    // hangs before any prompt is consumed anyway — the timeout is the subject).
    analysisIntent: 'quick-screen',
    dataPath: 'data/smoke.csv',
    sceneName: `d4_timeout_${tag}`,
    userQuestion: `hang ${tag}`,
    ...params,
  });
}

async function waitForStatus(runId, statuses, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = svc.getRunStatus(runId);
    if (last && statuses.includes(last.status)) return last;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`run ${runId} did not reach ${statuses} (last: ${last?.status})`);
}

describe('per-run timeoutMinutes — persisted, read from the DB row, honored by the engine', () => {
  test('persisted on the row executeDiagnosis reads (not just in-memory meta)', () => {
    const created = createHungRun('persist', { timeoutMinutes: TINY_TIMEOUT_MIN });
    const row = stmts.getRunById.get(created.runId); // the exact accessor the execution path uses
    assert.equal(row.timeout_minutes, TINY_TIMEOUT_MIN);
    assert.equal(svc.getRunStatus(created.runId).timeout_minutes, TINY_TIMEOUT_MIN, 'served by /status');
    assert.equal(getMeta(created.runId).timeoutMinutes, undefined, 'meta is not a second source of truth');
    // Re-read after dropping all in-process state: the DB still carries it.
    const fresh = stmts.getRunById.get(created.runId);
    assert.equal(fresh.timeout_minutes, TINY_TIMEOUT_MIN);
  });

  test('a run without the knob stores NULL — the engine config chain stays in charge', () => {
    const created = createHungRun('default');
    const row = stmts.getRunById.get(created.runId);
    // NULL (not a claude-flavored default): resolveEngineTimeoutMinutes then
    // falls through per-engine config → global harness budget, exactly as it
    // did before the column existed.
    assert.equal(row.timeout_minutes, null);
  });

  test('a non-positive / non-numeric knob never disables the engine guard', () => {
    for (const bogus of [0, -5, 'abc', NaN, Infinity, {}]) {
      const created = createHungRun(`bogus_${typeof bogus === 'string' ? 'text' : String(bogus)}`, { timeoutMinutes: bogus });
      const row = stmts.getRunById.get(created.runId);
      assert.equal(row.timeout_minutes, null, `bogus ${String(bogus)} must fall back to the chain, not persist`);
    }
  });

  test('a hung engine hits the persisted timeout: terminal failed, prompt kill', async () => {
    const created = createHungRun('hang', { timeoutMinutes: TINY_TIMEOUT_MIN });
    assert.equal(stmts.getRunById.get(created.runId).timeout_minutes, TINY_TIMEOUT_MIN);

    const startedAt = Date.now();
    const admission = svc.triggerDiagnosis(created.runId);
    assert.equal(admission.status, 'running');

    const final = await waitForStatus(created.runId, ['failed', 'completed']);
    const elapsedMs = Date.now() - startedAt;
    assert.equal(final.status, 'failed', final.error_message || '');
    // diagnosis.service maps the engine's timeout result through the terminal
    // "Query stopped" path (stop_reason from the engine client).
    assert.match(final.error_message, /Query stopped: gemini_timeout/);
    assert.ok(elapsedMs < 10000, `terminal in ${elapsedMs}ms — the 0.02min budget reached the engine (120min harness default would still be running)`);

    const statuses = svc.getRunEventStream(created.runId)
      .filter((e) => e.type === 'status')
      .map((e) => e.data?.status);
    assert.ok(statuses.includes('running') && statuses.includes('failed'), `status trail: ${statuses}`);
  });

  test('HTTP path: /start { timeoutMinutes } + /execute → prompt terminal failure', async () => {
    // The verifier's repro: POST /start with a tiny fractional timeout, then
    // /execute against the hung engine — the run must not sit in 'running'.
    const started = await api('POST', '/api/diagnosis/start', {
      harness: 'gemini',
      analysisIntent: 'quick-screen',
      dataPath: 'data/smoke.csv',
      sceneName: 'd4_timeout_http',
      userQuestion: 'hang http',
      timeoutMinutes: TINY_TIMEOUT_MIN,
    });
    assert.equal(started.status, 200, JSON.stringify(started.json));
    const runId = started.json.data.runId;

    const exec = await api('POST', `/api/diagnosis/execute/${runId}`);
    assert.equal(exec.status, 200, JSON.stringify(exec.json));
    assert.equal(exec.json.data.status, 'running');

    const final = await waitForStatus(runId, ['failed', 'completed']);
    assert.equal(final.status, 'failed');
    assert.match(final.error_message, /Query stopped: gemini_timeout/);
  });
});
