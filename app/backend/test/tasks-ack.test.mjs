// D7 — the async-task API must acknowledge the REAL admission result.
//
// POST /api/diagnosis/tasks used to hardcode `status: 'running'`, and
// getDiagTaskView folded every non-terminal state (including the concurrency
// queue's 'queued') into 'running'. A run that was only WAITING for a slot was
// therefore reported as executing — the caller could not tell the difference.
// This test mounts the diagnosis router over an isolated DB, saturates the
// concurrency cap with the in-process mock engine and drives the real HTTP
// contract: acks reflect queued/running, GET /tasks/:id maps 'queued' honestly
// (run_status stays 'queued'), and the queued task later completes.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, readdirSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const workDir = mkdtempSync(join(tmpdir(), 'idd-tasks-ack-'));

// One execution slot, isolated DB, no delayed close timers — all before the
// service modules (config/DB) are imported.
process.env.DATABASE_PATH = join(workDir, 'tasks.db');
process.env.MAX_CONCURRENT_RUNS = '1';
process.env.ENGINE_CLOSE_RUN_DELAY = '0';

const { PROJECT_ROOT, config } = await import('../../../config/loader.mjs');
const svc = await import('../src/services/diagnosis.service.mjs');

let server;
let baseUrl;

function api(method, path, body) {
  return fetch(`${baseUrl}${path}`, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  }).then(async (res) => ({ status: res.status, json: await res.json().catch(() => ({})) }));
}

async function waitForStatus(runId, statuses, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = svc.getRunStatus(runId);
    if (last && statuses.includes(last.status)) return last;
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(`run ${runId} did not reach ${statuses} (last: ${last?.status})`);
}

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

after(() => {
  if (server) server.close();
  // Remove the mock engine's run dirs this test created (workspace debris).
  // Successful runs are linked through workspace_path; the scripted-failure run
  // never is, so fall back to the scene suffix the mock names its dir with.
  const runsDir = join(PROJECT_ROOT, config.data.workspace_dir);
  for (const runId of createdRunIds) {
    const run = svc.getRunStatus(runId);
    if (run?.workspace_path) {
      rmSync(join(PROJECT_ROOT, run.workspace_path), { recursive: true, force: true });
    }
    for (const scene of SCENES) {
      for (const entry of readdirSync(runsDir)) {
        if (entry.endsWith(`_${scene}`)) {
          rmSync(join(runsDir, entry), { recursive: true, force: true });
        }
      }
    }
  }
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

const createdRunIds = [];
const SCENES = ['d7_tasks_a', 'd7_tasks_b', 'd7_tasks_fail'];

async function startTask(tag, { userQuestion } = {}) {
  const { status, json } = await api('POST', '/api/diagnosis/tasks', {
    harness: 'mock',
    dataPath: 'data/smoke.csv',
    sceneName: `d7_tasks_${tag}`,
    userQuestion: userQuestion || `tasks ack ${tag}`,
    reportLanguage: 'zh',
  });
  assert.equal(status, 200, JSON.stringify(json));
  assert.ok(json.data.task_id);
  createdRunIds.push(json.data.task_id);
  return { status, ack: json.data };
}

describe('POST /api/diagnosis/tasks — the ack is the admission result', () => {
  test('first task (slot free) acks running; the over-cap task acks queued', async () => {
    const first = await startTask('a');
    assert.equal(first.ack.status, 'running');
    assert.equal(first.ack.poll, `GET /api/diagnosis/tasks/${first.ack.task_id}`);

    const second = await startTask('b');
    // The mock engine holds its slot from the first synchronous slice of
    // executeDiagnosis, so the second task is admitted as 'queued' — the ack
    // must say so (the defect acked 'running' here).
    assert.equal(second.ack.status, 'queued');

    // GET view agrees: status AND run_status both say queued.
    const { status, json } = await api('GET', `/api/diagnosis/tasks/${second.ack.task_id}`);
    assert.equal(status, 200);
    assert.equal(json.data.status, 'queued');
    assert.equal(json.data.run_status, 'queued');
    assert.equal(json.data.result, null);
    assert.equal(json.data.task_id, second.ack.task_id);

    // The queued task is still a real run: it starts when the first frees the
    // slot and completes through the same path — the view must flip with it.
    const firstDone = await waitForStatus(first.ack.task_id, ['completed', 'failed']);
    assert.equal(firstDone.status, 'completed', firstDone.error_message || '');
    const secondDone = await waitForStatus(second.ack.task_id, ['completed', 'failed']);
    assert.equal(secondDone.status, 'completed', secondDone.error_message || '');

    const { json: finalView } = await api('GET', `/api/diagnosis/tasks/${second.ack.task_id}`);
    assert.equal(finalView.data.status, 'completed');
    assert.equal(finalView.data.run_status, 'completed');
    assert.ok(finalView.data.result, 'completed task carries the result payload');
    assert.match(String(finalView.data.result.report_md_path), /report\.md$/);
  });

  test('task view of a failed run maps to failed (shape preserved)', async () => {
    // mock:fail is the scripted failure path.
    const failing = await startTask('fail', { userQuestion: 'please mock:fail this run' });
    const { json: view } = await api('GET', `/api/diagnosis/tasks/${failing.ack.task_id}`);
    assert.ok(['running', 'failed'].includes(view.data.status));
    const done = await waitForStatus(failing.ack.task_id, ['failed']);
    assert.equal(done.status, 'failed');
    const { json: failedView } = await api('GET', `/api/diagnosis/tasks/${failing.ack.task_id}`);
    assert.equal(failedView.data.status, 'failed');
    assert.equal(failedView.data.run_status, 'failed');
    assert.ok(failedView.data.result.error);
    assert.equal(failedView.data.result.report_md_path, undefined);
  });
});
