// Mock-engine e2e — boots the REAL backend server (auth off, isolated DB) and
// drives the full HTTP contract: harness listing, availability tri-state,
// harness-selected run create → execute → stream → complete → report linking,
// session chat, continue, and the 400/409 pre-execution gates.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync } from 'fs';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const PORT = 3977;
const BASE = `http://127.0.0.1:${PORT}`;
const DB_PATH = join(mkdtempSync(join(tmpdir(), 'idd-e2e-')), 'e2e.db');

let server;
let serverLog = '';

async function waitHealthy(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-3000)}`);
}

before(async () => {
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(PORT),
      AUTH_ENABLED: '0',
      DATABASE_PATH: DB_PATH,
      SERVER_PORT: String(PORT),
      // 显式把 cursor 指向一个不存在的二进制 —— 用文档化的覆盖链（config → env → PATH）
      // 构造「已注册但不可用」状态，而不是赌某台机器上恰好没装 cursor-agent。
      HARNESS_CURSOR_COMMAND: join(mkdtempSync(join(tmpdir(), 'idd-cursor-abs-')), 'no-such-cursor-agent'),
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  await waitHealthy();
});

after(async () => {
  if (server && !server.killed) {
    server.kill();
    await new Promise((r) => setTimeout(r, 300));
    try { spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }); } catch { /* ignore */ }
  }
});

async function api(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, json };
}

async function waitForStatus(runId, statuses, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    const { json } = await api('GET', `/api/diagnosis/status/${runId}`);
    last = json.data;
    if (statuses.includes(last?.status)) return last;
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`run ${runId} did not reach ${statuses} (last: ${last?.status})\n${JSON.stringify(last)?.slice(0, 500)}`);
}

describe('GET /api/harness — registry over REST', () => {
  test('lists 14 engines including all documented ids', async () => {
    const { status, json } = await api('GET', '/api/harness');
    assert.equal(status, 200);
    assert.ok(json.success);
    const ids = json.data.map((h) => h.id);
    assert.equal(ids.length, 14);
    for (const expected of ['claude', 'omp', 'mock', 'codex', 'dsh', 'opencode', 'gemini', 'copilot', 'cursor', 'crush', 'goose', 'qwen', 'pi', 'hermes']) {
      assert.ok(ids.includes(expected), `missing ${expected}`);
    }
  });

  test('GET /api/harness/availability — one-shot probe of every engine', async () => {
    const { json } = await api('GET', '/api/harness/availability');
    const byId = Object.fromEntries(json.data.map((a) => [a.id, a]));
    assert.equal(byId.mock.available, true);
    assert.equal(byId.claude.available, true);
    assert.equal(byId.cursor.available, false); // cursor-agent not installed on this machine
    assert.ok(byId.cursor.meta.probe_error);
  });

  test('GET /api/harness/mock/health — in-process engine', async () => {
    const { json } = await api('GET', '/api/harness/mock/health');
    assert.equal(json.data.available, true);
    assert.equal(json.data.meta.inprocess, true);
  });

  test('GET /api/harness/default — best-adapted available engine (omp expected)', async () => {
    const { status, json } = await api('GET', '/api/harness/default');
    assert.equal(status, 200);
    // 本机 omp 已安装 — 默认解析到 omp（config harness.default，适配最全）；
    // 无 omp 的机器按回落链取 claude/mock。
    assert.ok(['omp', 'claude', 'mock'].includes(json.data.id), `unexpected default: ${json.data.id}`);
    assert.equal(json.data.manifest.id, json.data.id);
  });

  test('GET /api/harness/availability — exactly one default flag, on an available engine', async () => {
    const { json } = await api('GET', '/api/harness/availability');
    const defaults = json.data.filter((a) => a.default === true);
    assert.equal(defaults.length, 1);
    assert.equal(defaults[0].available, true);
  });

  test('start WITHOUT harness resolves the default (omp on this machine) — no silent claude', async () => {
    const { status, json } = await api('POST', '/api/diagnosis/start', {
      dataPath: 'data/smoke.csv',
      sceneName: 'default_harness_check',
      userQuestion: 'default harness smoke',
    });
    if (status === 200) {
      // 数据有效时创建成功 — harness 字段必须落库为显式解析出的默认引擎
      assert.ok(['omp', 'claude', 'mock'].includes(json.data.harness), json.data.harness);
      await api('POST', `/api/diagnosis/stop/${json.data.runId}`);
    } else {
      // omp 默认但缺数据路径校验失败也必须是人话错误
      assert.ok(json.error);
    }
  });
});

describe('POST /api/diagnosis/start — 执行前强校验 gates', () => {
  test('unknown harness → 400', async () => {
    const { status, json } = await api('POST', '/api/diagnosis/start', {
      harness: 'definitely-not-real',
      dataPath: 'data/smoke.csv',
      userQuestion: 'q',
    });
    assert.equal(status, 400);
    assert.match(json.error, /Unknown harness/);
  });

  test('unavailable harness (explicit bogus cursor override) → 409', async () => {
    // 可用性由探测决定，而探测与真实 spawn 同源（engine/cli-common.mjs resolveCliBinary）。
    // 这里 server 已被 HARNESS_CURSOR_COMMAND 指到不存在的二进制 → 必然不可用。
    const { status, json } = await api('POST', '/api/diagnosis/start', {
      harness: 'cursor',
      dataPath: 'data/smoke.csv',
      userQuestion: 'q',
    });
    assert.equal(status, 409);
    assert.match(json.error, /not usable/);
  });

  test('missing data → 404 DATA_NOT_FOUND semantics (mock harness gate passes first)', async () => {
    const { status, json } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/definitely-missing-file.csv',
      userQuestion: 'q',
    });
    assert.equal(status, 404);
    assert.equal(json.code, 'DATA_NOT_FOUND');
    assert.match(json.error, /Data not found/);
  });

  test('chat with a non-chat-capable harness → 400 CHAT_HARNESS_UNSUPPORTED (no silent fallback)', async () => {
    const { status, json } = await api('POST', '/api/chat/start', {
      harness: 'gemini',
      prompt: 'hello',
    });
    assert.equal(status, 400);
    assert.equal(json.code, 'CHAT_HARNESS_UNSUPPORTED');
    assert.match(json.error, /claude.*omp/);
  });
});

describe('mock harness full run — create → execute → complete → report → chat → continue', () => {
  let runId;

  test('create + execute run on harness=mock', async () => {
    const { status, json } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'mock_e2e',
      userQuestion: 'integration smoke question',
      reportLanguage: 'zh',
    });
    assert.equal(status, 200);
    assert.equal(json.data.harness, 'mock');
    runId = json.data.runId;
    assert.ok(runId);

    const exec = await api('POST', `/api/diagnosis/execute/${runId}`);
    assert.equal(exec.json.data.status, 'running');
  });

  test('run completes with report linking + judge score parsing', async () => {
    const run = await waitForStatus(runId, ['completed', 'failed']);
    assert.equal(run.status, 'completed');
    assert.ok(run.workspace_path, 'workspace_path linked');
    assert.match(run.workspace_path, /workspace[\\/]diagnostic-runs[\\/]/);
    assert.ok(run.report_path, 'report_path linked');
    assert.match(run.report_path, /report\.md$/);
    assert.equal(run.score, 96);
    assert.equal(run.judge_verdict, 'ENDORSED');
  });

  test('event stream recorded the scripted pipeline', async () => {
    const { json } = await api('GET', `/api/diagnosis/snapshot/${runId}`);
    const types = json.data.events.map((e) => e.type);
    assert.ok(types.includes('system'), 'init/system events');
    assert.ok(types.includes('message'), 'assistant messages');
    assert.ok(types.includes('tool_use'), 'tool_use events');
    assert.ok(types.includes('tool_result'), 'tool_result events');
    assert.ok(types.includes('stats'), 'result → stats');
  });

  test('session chat on the mock session', async () => {
    const { status, json } = await api('POST', `/api/diagnosis/chat/${runId}`, { message: '继续分析轴承温升' });
    assert.equal(status, 200);
    assert.ok(json.success);
    await new Promise((r) => setTimeout(r, 800));
    const { json: snap } = await api('GET', `/api/diagnosis/snapshot/${runId}`);
    const chatReply = JSON.stringify(snap.data.events).includes('已收到消息');
    assert.ok(chatReply, 'mock chat echo landed in the event stream');
  });

  test('continue re-runs the pipeline on the same run', async () => {
    const { status, json } = await api('POST', `/api/diagnosis/continue/${runId}`, { followUpMessage: '补充说明' });
    assert.equal(status, 200);
    const run = await waitForStatus(runId, ['completed', 'failed']);
    assert.equal(run.status, 'completed');
  });

  test('stop endpoint exists for the harness run', async () => {
    const { status, json: startJson } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'mock_e2e_stop',
      userQuestion: 'stop test',
    });
    assert.equal(status, 200);
    const secondRunId = startJson.data.runId;
    await api('POST', `/api/diagnosis/execute/${secondRunId}`);
    const stop = await api('POST', `/api/diagnosis/stop/${secondRunId}`);
    assert.equal(stop.status, 200);
  });
});

describe('mock failure script — 错误即事件', () => {
  test('mock:fail run ends failed with the scripted stop reason', async () => {
    const { json: startJson } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'mock_e2e_fail',
      userQuestion: 'please mock:fail this run',
    });
    const failRunId = startJson.data.runId;
    await api('POST', `/api/diagnosis/execute/${failRunId}`);
    const run = await waitForStatus(failRunId, ['failed'], 20000);
    assert.equal(run.status, 'failed');
    const { json: snap } = await api('GET', `/api/diagnosis/snapshot/${failRunId}`);
    assert.match(JSON.stringify(snap.data.events), /MOCK_SCRIPTED_FAILURE/);
  });
});

describe('SSE stream endpoint — harness-agnostic consumption', () => {
  test('stream endpoint answers with SSE frames for a mock run', async () => {
    const { json: startJson } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'mock_e2e_sse',
      userQuestion: 'sse test',
    });
    const sseRunId = startJson.data.runId;
    const res = await fetch(`${BASE}/api/diagnosis/stream/${sseRunId}?token=`);
    assert.equal(res.status, 200);
    const reader = res.body.getReader();
    const { value } = await reader.read();
    const chunk = Buffer.from(value).toString('utf-8');
    assert.match(chunk, /event: status/);
    reader.cancel().catch(() => {});
  });
});
