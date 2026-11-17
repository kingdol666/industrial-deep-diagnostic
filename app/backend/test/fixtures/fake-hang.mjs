// Fake "hung engine" CLI — completes only the handshake, then never finishes
// the turn. Used by the engine-timeout tests (P0-3) to prove that a stalled
// engine process is killed instead of hanging the run forever.
//
// Usage: node fake-hang.mjs <codex|acp|opencode|omp> [flags...]
//
// On startup it appends `PID <pid>` to FAKE_TRACE so tests can verify at the
// OS level that the process really died (a SIGKILL/taskkill never runs exit
// handlers, so an exit trace line would be unreachable on Windows).
import { appendFileSync } from 'fs';
import { createServer } from 'http';

const mode = process.argv[2] || 'omp';
const args = process.argv.slice(3);

const trace = (line) => {
  if (process.env.FAKE_TRACE) {
    try { appendFileSync(process.env.FAKE_TRACE, `${line}\n`); } catch { /* ignore */ }
  }
};
trace(`PID ${process.pid} ${mode}`);

if (args.includes('--version')) {
  process.stdout.write(`fake-hang ${mode} 1.0.0\n`);
  process.exit(0);
}

const write = (obj) => process.stdout.write(`${JSON.stringify(obj)}\n`);
const respond = (id, result) => write({ jsonrpc: '2.0', id, result });

function readLines(handler) {
  let buf = '';
  process.stdin.setEncoding('utf-8');
  process.stdin.on('data', (d) => {
    buf += d;
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;
      let frame;
      try { frame = JSON.parse(line); } catch { continue; }
      handler(frame);
    }
  });
}

if (mode === 'codex') {
  // app-server: initialize + thread/start + turn/start are answered (the turn
  // is "accepted"), then no turn/completed ever arrives — the turn hangs.
  readLines((frame) => {
    if (frame.method === 'initialize') respond(frame.id, { userAgent: 'fake-hang' });
    else if (frame.method === 'thread/start') respond(frame.id, { thread: { id: 'thr_hang' } });
    else if (frame.method === 'turn/start') { trace('PROMPT_HUNG'); respond(frame.id, { turn: { id: 'turn_hang', status: 'inProgress' } }); }
    else respond(frame.id, {});
  });
} else if (mode === 'acp') {
  // ACP v1 (dsh/hermes): initialize + session/new are answered; the
  // session/prompt request is accepted and never resolved.
  readLines((frame) => {
    if (frame.method === 'initialize') respond(frame.id, { protocolVersion: 1, agentCapabilities: {} });
    else if (frame.method === 'session/new') respond(frame.id, { sessionId: 'acp-hang-1' });
    else if (frame.method === 'session/prompt') trace('PROMPT_HUNG');
    else respond(frame.id, {});
  });
} else if (mode === 'opencode') {
  // Resident `serve` process: answers the readiness probe, session create and
  // prompt delivery; the SSE stream stays open forever (no session.idle).
  const portIdx = args.indexOf('--port');
  const port = portIdx >= 0 ? Number(args[portIdx + 1]) : 0;
  const server = createServer((req, res) => {
    const url = (req.url || '').split('?')[0];
    if (req.method === 'GET' && url === '/config') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end('{}');
      return;
    }
    if (req.method === 'POST' && url === '/session') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ id: 'hang-session' }));
      return;
    }
    if (req.method === 'GET' && url === '/event') {
      res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      res.write(': connected\n\n');
      return; // hold the stream open — never emit session.idle
    }
    if (req.method === 'POST' && /\/session\/[^/]+\/(prompt_async|message_async|message|prompt)$/.test(url)) {
      trace('PROMPT_HUNG');
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end('{}');
      return;
    }
    res.writeHead(404);
    res.end();
  });
  server.listen(port, '127.0.0.1');
} else {
  // omp --mode=rpc: ready handshake, then silence (no agent_end ever).
  write({ type: 'ready', protocolVersion: 1 });
  readLines((evt) => {
    if (evt.type === 'prompt') trace('PROMPT_HUNG');
  });
}

// The point of the fixture: stay alive indefinitely until the client kills it.
setInterval(() => {}, 1000);
