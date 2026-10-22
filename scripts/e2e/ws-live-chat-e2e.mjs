#!/usr/bin/env node
// Live chat rendering over the SAME WebSocket transport the UI uses.
//
// Proves that a chat turn on a completed run is pushed to an already-open
// subscriber (the UI's run view): subscribe_run first, then POST the chat, then
// assert a `message` run_event with the assistant reply arrives without a
// refresh. This is the regression test for the "subscribe on a closed run
// silently no-ops" bug.
//
// Usage: node scripts/e2e/ws-live-chat-e2e.mjs --run <runId> --base http://127.0.0.1:3211
// Uses Node's built-in WebSocket (Node >= 22), same wire protocol as the UI.

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const BASE = opt('base', 'http://127.0.0.1:3211');
const RUN = opt('run', 'b5c9236a');
const CREDS = { username: 'e2e_ontology', password: 'E2e-Onto-2026!' };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (!ok) failures += 1;
};

async function sessionToken() {
  const login = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(CREDS),
  }).then((r) => r.json());
  return login?.data?.session_token;
}

const jwt = await sessionToken();
if (!jwt) { console.error('login failed'); process.exit(2); }

const wsUrl = `${BASE.replace(/^http/, 'ws')}/ws?token=${encodeURIComponent(jwt)}`;
const ws = new WebSocket(wsUrl);
const events = [];
let subscribed = false;

ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ type: 'subscribe_run', runId: RUN }));
});
ws.addEventListener('message', (event) => {
  let msg;
  try { msg = JSON.parse(typeof event.data === 'string' ? event.data : String(event.data)); } catch { return; }
  // The server terminates clients that miss its app-level heartbeat.
  if (msg.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong', data: { ts: Date.now() } }));
    return;
  }
  if (msg.type === 'subscribed' && msg.data?.runId === RUN) subscribed = true;
  if (msg.type === 'run_event' && msg.data?.runId === RUN) {
    events.push(msg.data.event);
  }
});
ws.addEventListener('error', () => { console.error('WS error'); });

// Wait for the subscription ack (the run entry is created by subscribe()).
const subDeadline = Date.now() + 10000;
while (!subscribed && Date.now() < subDeadline) await sleep(200);
check('ws 订阅已确认（已关闭的 completed run 也能订阅）', subscribed, `subscribed=${subscribed}`);

const H = { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` };
const marker = `WS实时渲染-${Date.now().toString(36).slice(-5)}`;
// Replayed history from subscribe() must not satisfy the assertions: only
// events with a seq ABOVE this watermark were produced by the POST.
const seqBefore = events.reduce((max, e) => Math.max(max, Number(e?._seq ?? -1)), -1);
const post = await fetch(`${BASE}/api/diagnosis/chat/${RUN}`, {
  method: 'POST', headers: H, body: JSON.stringify({ message: `${marker}：只回答两个字“收到”`, maxTurns: 4 }),
});
check('chat POST accepted', post.status === 200, post.status);

// Wait up to 120s for the assistant message event over the socket.
const deadline = Date.now() + (Number(opt('wait-seconds', '120')) * 1000);
let assistantMsg = null;
while (!assistantMsg && Date.now() < deadline) {
  assistantMsg = [...events].reverse().find((e) =>
    Number(e?._seq ?? -1) > seqBefore
    && e?.type === 'message' && e?.data?.source === 'session_chat' && (e?.data?.content || '').trim());
  if (!assistantMsg) await sleep(1000);
}
check('WS 实时收到 assistant 消息（无需刷新）', !!assistantMsg,
  assistantMsg ? JSON.stringify(assistantMsg.data.content).slice(0, 120) : `events=${events.length}`);
const userEv = events.find((e) => Number(e?._seq ?? -1) > seqBefore
  && e?.type === 'user_message' && (e?.data?.content || '').includes(marker));
check('WS 实时收到原样用户消息', !!userEv, userEv ? JSON.stringify(userEv.data.content).slice(0, 120) : 'missing');
if (userEv) {
  check('用户消息无额外提示词注入', userEv.data.content === `${marker}：只回答两个字“收到”`,
    JSON.stringify(userEv.data.content).slice(0, 160));
}

ws.close();
console.log(`\n[RESULT] failures=${failures} events_seen=${events.length}`);
process.exit(failures ? 1 : 0);
