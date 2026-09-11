// Fake standard ACP v1 engine (dsh/hermes dialect) — NDJSON JSON-RPC on stdio.
// Script: initialize → session/new → session/prompt → (session/update notifications
// + session/request_permission server→client request) → prompt response end_turn.
// Traces the permission outcome to FAKE_TRACE for test assertions.
import { appendFileSync } from 'fs';

const trace = (line) => {
  if (process.env.FAKE_TRACE) {
    try { appendFileSync(process.env.FAKE_TRACE, `${line}\n`); } catch { /* ignore */ }
  }
};

if (process.argv.includes('--version')) {
  process.stdout.write('fake-acp 1.0.0\n');
  process.exit(0);
}

let buf = '';
const respond = (id, result) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`);
const notify = (method, params) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', method, params })}\n`);

const pending = new Map();
let nextId = 100;

function handleLine(line) {
  let frame;
  try { frame = JSON.parse(line); } catch { return; }
  if (frame.id !== undefined && (frame.result !== undefined || frame.error !== undefined)) {
    const p = pending.get(frame.id);
    if (p) { pending.delete(frame.id); p(frame); }
    return;
  }
  const { id, method, params } = frame;
  if (method === 'initialize') {
    respond(id, { protocolVersion: 1, agentCapabilities: { loadSession: false } });
  } else if (method === 'session/new') {
    respond(id, { sessionId: 'acp-sess-1' });
  } else if (method === 'session/prompt') {
    // drive the turn
    notify('session/update', { sessionId: 'acp-sess-1', update: { sessionUpdate: 'agent_message_chunk', content: { type: 'text', text: 'hi from acp' } } });
    notify('session/update', { sessionId: 'acp-sess-1', update: { sessionUpdate: 'tool_call', toolCallId: 't1', title: 'Bash', kind: 'execute', input: { command: 'ls' } } });
    notify('session/update', { sessionId: 'acp-sess-1', update: { sessionUpdate: 'tool_call_update', toolCallId: 't1', status: 'completed', output: 'ok' } });
    // server→client approval request
    process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id: nextId, method: 'session/request_permission', params: { sessionId: 'acp-sess-1', toolCall: { title: 'Bash' }, options: [{ kind: 'allow_once', optionId: 'allow_once' }, { kind: 'reject_once', optionId: 'reject' }] } })}\n`);
    pending.set(nextId, (resp) => {
      trace(`PERM ${JSON.stringify(resp.result)}`);
      respond(id, { stopReason: 'end_turn' });
    });
    nextId += 1;
  } else if (method === 'session/cancel') {
    trace('CANCEL');
  } else {
    respond(id, {});
  }
}

process.stdin.setEncoding('utf-8');
process.stdin.on('data', (d) => {
  buf += d;
  let idx;
  while ((idx = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, idx).trim();
    buf = buf.slice(idx + 1);
    if (line) handleLine(line);
  }
});
