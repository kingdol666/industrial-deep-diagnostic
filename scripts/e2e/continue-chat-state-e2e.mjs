#!/usr/bin/env node
// Continue-chat + state-management acceptance (plan v2, focused re-test).
//
// Requirements verified against a real backend + real harnesses:
//   P1  resume turns are VERBATIM: no prompt anchor / scaffolding is injected
//       (the mock engine echoes the received message, which makes this provable);
//   P2  a completed run can continue, and its status stays `completed`;
//   P3  a stopped run that HAS a harness session can continue (resume), and its
//       status stays `stopped`;
//   P4  a run that was `pending` when the server restarted becomes `stopped`
//       (and can then be continued through the rebuild path);
//   P5  a run that was `running` when the server restarted becomes `failed`.
//
// Usage:
//   node scripts/e2e/continue-chat-state-e2e.mjs before --base http://127.0.0.1:3210
//   # restart the backend
//   node scripts/e2e/continue-chat-state-e2e.mjs after  --base http://127.0.0.1:3210
import { readFileSync, writeFileSync } from 'node:fs';
import { stmts } from '../../app/backend/src/db/database.mjs';

const args = process.argv.slice(2);
const stage = args[0];
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const BASE = opt('base', 'http://127.0.0.1:3210');
const CREDS = { username: 'e2e_ontology', password: 'E2e-Onto-2026!' };
const STATE = '.runtime-e2e-chat-state.json';

let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (!ok) failures += 1;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function token() {
  const login = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(CREDS),
  }).then((r) => r.json());
  const jwt = login?.data?.session_token;
  const tok = await fetch(`${BASE}/api/auth/tokens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
    body: JSON.stringify({ name: 'e2e-chat-state', expires_in_days: 1 }),
  }).then((r) => r.json());
  return tok?.data?.token;
}

function mkApi(idd) {
  const H = { 'Content-Type': 'application/json', Authorization: `Bearer ${idd}` };
  return async (method, path, body) => {
    const res = await fetch(`${BASE}${path}`, { method, headers: H, body: body === undefined ? undefined : JSON.stringify(body) });
    let json = null;
    try { json = await res.json(); } catch { /* non-JSON */ }
    return { status: res.status, json };
  };
}

/** Wait until a run has a harness session id (session-map) or a deadline hits. */
async function waitForSession(api, runId, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const map = await api('GET', `/api/diagnosis/session-map/${runId}`);
    const sid = map.json?.data?.session_id;
    if (sid) return { sessionId: sid, map: map.json.data };
    await sleep(3000);
  }
  return null;
}

/** Wait for an assistant log after `sinceCount`, return it. */
async function waitForAssistant(api, runId, sinceCount, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const detail = await api('GET', `/api/history/runs/${runId}`);
    const logs = detail.json?.data?.logs || [];
    const fresh = logs.slice(sinceCount);
    const assistant = [...fresh].reverse().find((l) => l.role === 'assistant' && (l.content || '').trim());
    if (assistant) return { assistant, logs };
    await sleep(2500);
  }
  return null;
}

function insertRun(id, { status, harness, intent = 'deep-diagnosis', scene = 'e2e_chat_state' }) {
  stmts.insertRun.run({
    runId: id, name: id, title: id, sceneName: scene,
    dataPath: 'data/lsr_demo', dataFolder: 'lsr_demo', userQuestion: 'state fixture',
    model: null, maxTurns: 10, reportLanguage: 'zh', harness,
    ontologyHit: 0, enhancementPolicy: 'auto', enhancementTriggered: 0,
    analysisIntent: intent, userId: null,
  });
  stmts.updateRunStatus.run({ runId: id, status });
}

async function stageBefore(api) {
  const suffix = Date.now().toString(36).slice(-5);
  const state = { suffix };

  // ── P1: verbatim passthrough (mock engine echoes the received message) ──
  const mock = await api('POST', '/api/external/v1/analyze', {
    folderPath: 'lsr_demo', analysisIntent: 'stability-report', harness: 'mock',
    sceneName: `chat_passthrough_${suffix}`, question: 'passthrough fixture',
    ontologyMode: 'auto', wait: true, wait_timeout_minutes: 5,
  });
  check('P1a mock run completed', mock.status === 200 && mock.json?.data?.status === 'completed', JSON.stringify(mock.json).slice(0, 160));
  state.mockRun = mock.json?.data?.run_id;

  const marker = `透传校验-${suffix}`;
  const before = await api('GET', `/api/history/runs/${state.mockRun}`);
  const beforeCount = (before.json?.data?.logs || []).length;
  const chat1 = await api('POST', `/api/diagnosis/chat/${state.mockRun}`, { message: marker, maxTurns: 4 });
  check('P1b chat accepted', chat1.status === 200, JSON.stringify(chat1.json).slice(0, 120));
  const r1 = await waitForAssistant(api, state.mockRun, beforeCount, 40000);
  const echoed = r1?.assistant?.content || '';
  check('P1c 续聊消息原样透传（无任何额外注入）',
    echoed === `(mock) 已收到消息: ${marker}`,
    `echo=${JSON.stringify(echoed).slice(0, 200)}`);
  const afterMock = await api('GET', `/api/history/runs/${state.mockRun}`);
  check('P1d completed 状态在续聊后保持不变', afterMock.json?.data?.status === 'completed', afterMock.json?.data?.status);
  const userLog = (afterMock.json?.data?.logs || []).find((l) => l.role === 'user' && l.content === marker);
  check('P1e 用户消息日志为原文', !!userLog, userLog ? 'exact match' : 'missing/added text');

  // ── P2: completed real run (claude) continues ──
  state.completedRun = 'b5c9236a';
  const mapC = await api('GET', `/api/diagnosis/session-map/${state.completedRun}`);
  check('P2a completed run 映射为 claude 可续会话',
    mapC.json?.data?.harness === 'claude' && mapC.json?.data?.resumable === true,
    JSON.stringify(mapC.json?.data).slice(0, 180));
  const cBefore = await api('GET', `/api/history/runs/${state.completedRun}`);
  const cCount = (cBefore.json?.data?.logs || []).length;
  const marker2 = `完成续聊-${suffix}`;
  const chat2 = await api('POST', `/api/diagnosis/chat/${state.completedRun}`, { message: marker2, maxTurns: 4 });
  check('P2b completed run 续聊受理', chat2.status === 200, JSON.stringify(chat2.json).slice(0, 120));
  const r2 = await waitForAssistant(api, state.completedRun, cCount, 120000);
  check('P2c completed run 收到 assistant 回复', !!r2, r2 ? r2.assistant.content.slice(0, 100) : 'timeout');
  const cAfter = await api('GET', `/api/history/runs/${state.completedRun}`);
  check('P2d completed 状态不变', cAfter.json?.data?.status === 'completed', cAfter.json?.data?.status);

  // ── P3: stop a live run that already has a session, then continue it ──
  const live = await api('POST', '/api/external/v1/analyze', {
    folderPath: 'lsr_demo', analysisIntent: 'stability-report', harness: 'claude',
    sceneName: `chat_stop_${suffix}`, question: 'stop fixture', ontologyMode: 'auto',
    timeoutMinutes: 240, maxTurns: 200,
  });
  check('P3a live run accepted', live.status === 202 && !!live.json?.data?.run_id, JSON.stringify(live.json).slice(0, 140));
  state.stopRun = live.json?.data?.run_id;
  const sess = await waitForSession(api, state.stopRun, 120000);
  check('P3b 运行已捕获 harness session', !!sess, sess ? sess.sessionId : 'no session before timeout');
  state.stopSession = sess?.sessionId || null;
  if (sess) {
    const stop = await api('POST', `/api/diagnosis/stop/${state.stopRun}`);
    check('P3c stop → stopped', stop.status === 200 && stop.json?.data?.status === 'stopped', JSON.stringify(stop.json).slice(0, 120));
    const sBefore = await api('GET', `/api/history/runs/${state.stopRun}`);
    const sCount = (sBefore.json?.data?.logs || []).length;
    const marker3 = `停止后续聊-${suffix}`;
    const chat3 = await api('POST', `/api/diagnosis/chat/${state.stopRun}`, { message: marker3, maxTurns: 4 });
    check('P3d stopped run 续聊受理', chat3.status === 200, JSON.stringify(chat3.json).slice(0, 120));
    const r3 = await waitForAssistant(api, state.stopRun, sCount, 120000);
    check('P3e stopped run 收到 assistant 回复', !!r3, r3 ? r3.assistant.content.slice(0, 100) : 'timeout');
    const sAfter = await api('GET', `/api/history/runs/${state.stopRun}`);
    check('P3f stopped 状态在续聊后保持不变', sAfter.json?.data?.status === 'stopped', sAfter.json?.data?.status);
  } else {
    state.stopSession = null;
  }

  // ── P4/P5 fixtures for the restart stage ──
  state.pendingRun = `chat-pend-${suffix}`;
  insertRun(state.pendingRun, { status: 'pending', harness: 'mock' });
  state.runningRun = `chat-run-${suffix}`;
  insertRun(state.runningRun, { status: 'running', harness: 'mock' });

  writeFileSync(STATE, JSON.stringify(state, null, 2));
  console.log(`\nstate → ${STATE}`);
  console.log(`[BEFORE] failures=${failures}`);
  process.exit(failures ? 1 : 0);
}

async function stageAfter(api) {
  const state = JSON.parse(readFileSync(STATE, 'utf8'));

  // P4: pending → stopped after restart
  const pend = await api('GET', `/api/history/runs/${state.pendingRun}`);
  check('P4a pending→stopped after restart',
    pend.json?.data?.status === 'stopped' && /restarted before execution/i.test(pend.json?.data?.error_message || ''),
    `status=${pend.json?.data?.status}`);

  // P4b: the stopped run (no session) can still be continued — rebuild path
  const pBefore = (await api('GET', `/api/history/runs/${state.pendingRun}`)).json?.data?.logs?.length || 0;
  const chatP = await api('POST', `/api/diagnosis/chat/${state.pendingRun}`, { message: `无会话续聊-${state.suffix}`, maxTurns: 4 });
  check('P4b stopped(no session) 续聊受理（重建路径）', chatP.status === 200, JSON.stringify(chatP.json).slice(0, 120));
  const rP = await waitForAssistant(api, state.pendingRun, pBefore, 60000);
  check('P4c stopped(no session) 得到回复', !!rP, rP ? rP.assistant.content.slice(0, 100) : 'timeout');

  // P5: running → failed after restart
  const run = await api('GET', `/api/history/runs/${state.runningRun}`);
  check('P5 running→failed after restart',
    run.json?.data?.status === 'failed' && /interrupted/i.test(run.json?.data?.error_message || ''),
    `status=${run.json?.data?.status} err=${run.json?.data?.error_message}`);

  // Stopped-with-session run from the before stage stays stopped.
  if (state.stopRun && state.stopSession) {
    const s = await api('GET', `/api/history/runs/${state.stopRun}`);
    const map = await api('GET', `/api/diagnosis/session-map/${state.stopRun}`);
    check('P3g stopped+session 映射仍在且可续',
      s.json?.data?.status === 'stopped'
      && map.json?.data?.session_id === state.stopSession
      && map.json?.data?.resumable === true,
      JSON.stringify(map.json?.data).slice(0, 180));
  }

  console.log(`[AFTER] failures=${failures}`);
  process.exit(failures ? 1 : 0);
}

const idd = await token();
if (!idd) { console.error('cannot obtain API token'); process.exit(2); }
const api = mkApi(idd);
if (stage === 'before') await stageBefore(api);
else if (stage === 'after') await stageAfter(api);
else { console.error('usage: continue-chat-state-e2e.mjs before|after --base <url>'); process.exit(2); }
