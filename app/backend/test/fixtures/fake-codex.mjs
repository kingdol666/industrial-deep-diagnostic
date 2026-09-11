// Fake codex app-server — NDJSON JSON-RPC v2 on stdio.
// Script: initialize → thread/start {threadId} → turn/start → notifications
// (item/completed agentMessage, commandExecution approval request) → turn/completed.
// Traces the approval decision to FAKE_TRACE.
import { appendFileSync } from 'fs';

const trace = (line) => {
  if (process.env.FAKE_TRACE) {
    try { appendFileSync(process.env.FAKE_TRACE, `${line}\n`); } catch { /* ignore */ }
  }
};

if (process.argv.includes('--version')) {
  process.stdout.write('fake-codex 1.0.0\n');
  process.exit(0);
}

let buf = '';
const respond = (id, result) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`);
const notify = (method, params) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', method, params })}\n`);

const pending = new Map();
let nextId = 500;

function handleLine(line) {
  let frame;
  try { frame = JSON.parse(line); } catch { return; }
  if (frame.id !== undefined && (frame.result !== undefined || frame.error !== undefined)) {
    const p = pending.get(frame.id);
    if (p) { pending.delete(frame.id); p(frame); }
    return;
  }
  const { id, method } = frame;
  if (method === 'initialize') {
    respond(id, { userAgent: { name: 'fake-codex', version: '1.0.0' } });
  } else if (method === 'thread/start') {
    respond(id, { threadId: 'thr_fake_1' });
  } else if (method === 'turn/start') {
    notify('item/completed', { threadId: 'thr_fake_1', item: { id: 'i1', type: 'agentMessage', text: 'hi from codex' } });
    process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id: nextId, method: 'item/commandExecution/requestApproval', params: { threadId: 'thr_fake_1', itemId: 'i2', command: 'ls' } })}\n`);
    pending.set(nextId, (resp) => {
      trace(`APPROVAL ${JSON.stringify(resp.result)}`);
      notify('item/completed', { threadId: 'thr_fake_1', item: { id: 'i2', type: 'commandExecution', command: 'ls', aggregatedOutput: 'ok' } });
      notify('turn/completed', { threadId: 'thr_fake_1', usage: { total: 42 } });
      respond(id, { turnId: 'turn_1' });
    });
    nextId += 1;
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
