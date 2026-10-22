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
      // Codex must never spawn for real in this suite: a seeded non-resumable
      // run is chatted into, and its rebuild path would start that engine.
      HARNESS_CODEX_COMMAND: join(mkdtempSync(join(tmpdir(), 'idd-codex-abs-')), 'no-such-codex'),
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

  test('chat with an unknown harness → 400 CHAT_HARNESS_UNSUPPORTED; every REGISTERED harness is chat-capable (generic turn path)', async () => {
    // 2026-09-19 起：通用 turn 路径让全部注册引擎都能聊天（原生 resume 优先，
    // 否则历史重放）——只有未注册的 id 才 400，绝不静默换引擎。
    const { status, json } = await api('POST', '/api/chat/start', {
      harness: 'not-a-real-engine',
      prompt: 'hello',
    });
    assert.equal(status, 400);
    assert.equal(json.code, 'CHAT_HARNESS_UNSUPPORTED');
    assert.match(json.error, /Unknown chat harness/);
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
    // No model was selected → the run row must not carry a claude default
    // (Bug A: claude model must not leak into non-claude engine runs).
    assert.equal(run.model ?? null, null);
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

describe('false-success guard — success result without report.md must fail', () => {
  test('mock:noreport ends failed with the guard error even on result success', async () => {
    const { json: startJson } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'mock_e2e_noreport',
      userQuestion: 'please mock:noreport this run',
    });
    const noreportRunId = startJson.data.runId;
    await api('POST', `/api/diagnosis/execute/${noreportRunId}`);
    const run = await waitForStatus(noreportRunId, ['failed'], 20000);
    assert.equal(run.status, 'failed');
    assert.match(run.error_message, /report\.md/);
    assert.equal(run.error_message.includes('false success'), true);
    assert.equal(run.report_path ?? null, null);
    const { json: snap } = await api('GET', `/api/diagnosis/snapshot/${noreportRunId}`);
    const lastComplete = [...snap.data.events].reverse().find((e) => e.type === 'complete');
    assert.equal(lastComplete?.data?.status, 'failed');
  });
});

describe('chat option validation — same catalog gate as diagnosis runs', () => {
  test('chat with a model outside the harness catalog → 400 MODEL_NOT_SUPPORTED', async () => {
    const { status, json } = await api('POST', '/api/chat/start', {
      harness: 'codex',
      model: 'gpt-99',
      prompt: 'hello',
    });
    assert.equal(status, 400);
    assert.equal(json.code, 'MODEL_NOT_SUPPORTED');
    assert.match(json.error, /gpt-99/);
  });

  test('chat with a permission mode outside the harness catalog → 400 PERMISSION_NOT_SUPPORTED', async () => {
    const { status, json } = await api('POST', '/api/chat/start', {
      harness: 'omp',
      permissionMode: 'plan', // claude-style mode — omp only supports auto-approve
      prompt: 'hello',
    });
    assert.equal(status, 400);
    assert.equal(json.code, 'PERMISSION_NOT_SUPPORTED');
    assert.match(json.error, /plan/);
  });

  test('mock chat accepts any model (scripted engine is exempt from the catalog gate)', async () => {
    const { status, json } = await api('POST', '/api/chat/start', {
      harness: 'mock',
      model: 'any-model-string',
      prompt: 'mock chat smoke',
    });
    assert.equal(status, 200);
    assert.ok(json.data.chatId);
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

describe('zombie pending hygiene — listRuns lazily expires orphaned pendings', () => {
  test('a start-without-execute run older than 24h flips to expired; fresh pendings survive', async () => {
    // Seed the isolated DB directly: one backdated orphaned pending (created
    // via /start, /execute never arrived) and one fresh pending.
    const { default: Database } = await import('better-sqlite3');
    const db = new Database(DB_PATH);
    const insertStale = db.prepare(`
      INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, status, created_at, updated_at)
      VALUES (?, ?, 'zombie_pending', 'data/smoke.csv', 'pending', datetime('now', '-25 hours'), datetime('now', '-25 hours'))
    `);
    const insertFresh = db.prepare(`
      INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, status)
      VALUES (?, ?, 'zombie_pending', 'data/smoke.csv', 'pending')
    `);
    const staleRunId = 'zombiestale01';
    const freshRunId = 'zombiefresh01';
    insertStale.run(staleRunId, 'zombie_stale');
    insertFresh.run(freshRunId, 'zombie_fresh');
    db.close();

    const { json } = await api('GET', '/api/diagnosis/list');
    assert.ok(json.success);
    const byId = Object.fromEntries(json.data.map((r) => [r.run_id, r]));
    assert.equal(byId[staleRunId].status, 'expired');
    assert.equal(byId[freshRunId].status, 'pending');

    // An expired run is no longer executable — the pending gate refuses it.
    const exec = await api('POST', `/api/diagnosis/execute/${staleRunId}`);
    assert.equal(exec.status, 400);
    assert.match(exec.json.error, /not pending/);
  });
});

describe('continue/chat routing — rebuild fallback + honest HTTP semantics', () => {
  const seedRun = async (id, {
    harness, status = 'completed', sessionId = null,
    dataPath = 'data/smoke.csv', intent = 'deep-diagnosis', score = null, verdict = null,
  }) => {
    const { default: Database } = await import('better-sqlite3');
    const db = new Database(DB_PATH);
    db.prepare(`
      INSERT INTO diagnostic_runs
        (run_id, name, scene_name, data_path, status, harness, analysis_intent,
         session_id, score, judge_verdict, created_at, updated_at)
      VALUES (?, ?, 'route_contract', ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    `).run(id, id, dataPath, status, harness, intent, sessionId, score, verdict);
    db.close();
    return id;
  };

  test('capabilities expose honest session_resume + supported_intents', async () => {
    const { status, json } = await api('GET', '/api/external/v1/capabilities');
    assert.equal(status, 200);
    const byId = Object.fromEntries(json.data.harnesses.map((h) => [h.id, h]));
    for (const id of ['claude', 'omp', 'goose', 'mock']) {
      assert.equal(byId[id].session_resume, true, id);
    }
    for (const id of ['codex', 'opencode', 'gemini', 'cursor']) {
      assert.equal(byId[id].session_resume, false, id);
    }
    for (const h of json.data.harnesses) {
      assert.equal(h.supported_intents.length, 6, `${h.id} intents`);
      assert.ok(h.supported_intents.includes('stability-report'));
    }
  });

  test('a non-resumable engine chat is served by rebuild (200), not a 404', async () => {
    const id = `routeCodex${Date.now().toString(36).slice(-5)}`;
    await seedRun(id, { harness: 'codex', sessionId: 'codex:run:whatever' });
    const { status, json } = await api('POST', `/api/diagnosis/chat/${id}`, { message: '继续' });
    assert.equal(status, 200, JSON.stringify(json));
    assert.equal(json.data.mode, 'rebuild');
    assert.equal(json.data.resumed, false);
    assert.equal(json.data.reason, 'engine_no_resume');
    // The banner explains the rebuild instead of pretending it resumed.
    await new Promise((r) => setTimeout(r, 300));
    const { json: snap } = await api('GET', `/api/diagnosis/snapshot/${id}`);
    const banner = (snap.data?.events || []).find((e) =>
      e.type === 'system' && e.subtype === 'session_chat' && e.data?.mode === 'rebuild');
    assert.ok(banner, 'rebuild system banner emitted');
    assert.match(banner.data.message, /不支持会话级恢复/);
  });

  test('a resumable engine chat still goes to its own session (mock)', async () => {
    const { json: startJson } = await api('POST', '/api/diagnosis/start', {
      harness: 'mock', dataPath: 'data/smoke.csv', sceneName: 'route_mock_session',
      userQuestion: 'session routing',
    });
    const id = startJson.data.runId;
    await api('POST', `/api/diagnosis/execute/${id}`);
    await waitForStatus(id, ['completed', 'failed']);
    const { status, json } = await api('POST', `/api/diagnosis/chat/${id}`, { message: '继续' });
    assert.equal(status, 200);
    assert.equal(json.data.mode, 'session');
    assert.equal(json.data.resumed, true);
  });

  test('no resumable session AND no data context → 409 RESUME_UNSUPPORTED', async () => {
    const id = `routeNoCtx${Date.now().toString(36).slice(-5)}`;
    await seedRun(id, { harness: 'codex', sessionId: 'codex:run:none', dataPath: '' });
    const { status, json } = await api('POST', `/api/diagnosis/chat/${id}`, { message: '继续' });
    assert.equal(status, 409, JSON.stringify(json));
    assert.equal(json.code, 'RESUME_UNSUPPORTED');
    assert.equal(json.harness, 'codex');
    assert.equal(json.run_id, id);
  });

  test('a missing run is a 404 with RUN_NOT_FOUND (never a fake rebuild)', async () => {
    const { status, json } = await api('POST', '/api/diagnosis/chat/does-not-exist-xyz', { message: 'hi' });
    assert.equal(status, 404);
    assert.equal(json.code, 'RUN_NOT_FOUND');
    const ext = await api('POST', '/api/external/v1/chat', { run_id: 'does-not-exist-xyz', message: 'hi' });
    assert.equal(ext.status, 404);
    assert.equal(ext.json.code, 'RUN_NOT_FOUND');
  });
});

describe('external result — analysis_mode honesty + artifact-derived outcome', () => {
  test('a mock analysis is labelled analysis_mode=mock on result and task entry', async () => {
    const created = await api('POST', '/api/external/v1/analyze', {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      analysisIntent: 'deep-diagnosis',
      sceneName: 'ext_mock_mode',
      question: 'mode label probe',
    });
    assert.equal(created.status, 202, JSON.stringify(created.json));
    const { run_id: runId, task_id: taskId } = created.json.data;
    await waitForStatus(runId, ['completed', 'failed'], 40000);

    const result = await api('GET', `/api/external/v1/analyze/${runId}`);
    assert.equal(result.status, 200);
    assert.equal(result.json.data.analysis_mode, 'mock');
    assert.equal(result.json.data.harness, 'mock');

    const tasks = await api('GET', '/api/external/v1/tasks');
    const entry = (tasks.json.data || []).find((t) => t.task_id === taskId);
    assert.ok(entry, 'task entry listed');
    assert.equal(entry.analysis_mode, 'mock');
  });

  test('a non-mock run is analysis_mode=real', async () => {
    const { default: Database } = await import('better-sqlite3');
    const id = `realMode${Date.now().toString(36).slice(-5)}`;
    const db = new Database(DB_PATH);
    db.prepare(`
      INSERT INTO diagnostic_runs
        (run_id, name, scene_name, data_path, status, harness, analysis_intent, created_at, updated_at)
      VALUES (?, ?, 'mode_real', 'data/smoke.csv', 'completed', 'claude', 'deep-diagnosis', datetime('now'), datetime('now'))
    `).run(id, id);
    db.close();
    const result = await api('GET', `/api/external/v1/analyze/${id}`);
    assert.equal(result.status, 200);
    assert.equal(result.json.data.analysis_mode, 'real');
  });
});
