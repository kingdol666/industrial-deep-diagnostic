// Fake one-shot CLI — speaks each documented engine dialect for tests.
// Usage: node fake-oneshot.mjs <gemini|cursor|goose|pi> [flags...]
//
// Env knobs:
//   FAKE_SESSION    session id reported by the init frame   (default sess-123)
//   FAKE_EXIT       process exit code                       (default 0)
//   FAKE_STDIN_CONTAINS  when set: stdin must contain this, else exit 5
//   FAKE_TRACE      when set: append argv/stdin info to this file (test assertions)
import { appendFileSync } from 'fs';

const engineKey = process.argv[2] || 'gemini';
const args = process.argv.slice(3);
const SESSION = process.env.FAKE_SESSION || 'sess-123';
const EXIT = Number(process.env.FAKE_EXIT || 0);
const trace = (line) => {
  if (process.env.FAKE_TRACE) {
    try { appendFileSync(process.env.FAKE_TRACE, `${line}\n`); } catch { /* ignore */ }
  }
};

if (args.includes('--version')) {
  process.stdout.write('fake-oneshot 1.0.0\n');
  process.exit(0);
}

const stdinText = await new Promise((resolve) => {
  let buf = '';
  process.stdin.setEncoding('utf-8');
  process.stdin.on('data', (d) => { buf += d; });
  process.stdin.on('end', () => resolve(buf));
  setTimeout(() => resolve(buf), 1500).unref?.();
});
trace(`ARGS ${JSON.stringify(args)}`);
trace(`STDIN ${JSON.stringify(stdinText.slice(0, 200))}`);

const need = process.env.FAKE_STDIN_CONTAINS;
if (need && !stdinText.includes(need)) {
  process.stderr.write(`stdin missing: ${need}\n`);
  process.exit(5);
}

const argFile = args.find((a) => a.startsWith('@'));
if (argFile) {
  const { readFileSync } = await import('fs');
  const content = readFileSync(argFile.slice(1), 'utf-8');
  trace(`ARGFILE ${JSON.stringify(content.slice(0, 200))}`);
}

const resumed = args.includes('--resume') || args.some((a) => String(a).startsWith('--resume='));
const sid = resumed ? 'sess-resumed' : SESSION;

// slow-start knob: lets tests abort a genuinely live turn
if (process.env.FAKE_DELAY) {
  await new Promise((r) => setTimeout(r, Number(process.env.FAKE_DELAY)));
}

const frames = {
  gemini: [
    { type: 'init', session_id: sid, model: 'fake-gemini' },
    { type: 'message', role: 'assistant', content: 'thinking about data' },
    { type: 'tool_use', tool_id: 't1', name: 'shell', args: { command: 'ls' } },
    { type: 'tool_result', tool_id: 't1', output: 'ok' },
    { type: 'result', status: EXIT === 0 ? 'success' : 'failure' },
  ],
  cursor: [
    { type: 'system', subtype: 'init', session_id: sid },
    { type: 'assistant', message: { content: [{ type: 'text', text: 'hi from cursor' }, { type: 'tool_use', id: 't1', name: 'Bash', input: { command: 'ls' } }] } },
    { type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'ok', is_error: false }] } },
    { type: 'result', subtype: EXIT === 0 ? 'success' : 'error_during_execution' },
  ],
  copilot: [
    { type: 'system', subtype: 'init', session_id: sid },
    { type: 'assistant', message: { content: [{ type: 'text', text: 'hi from copilot' }] } },
    { type: 'result', subtype: 'success' },
  ],
  goose: [
    { type: 'start', session_id: sid },
    { type: 'message', message: { role: 'assistant', content: [{ type: 'text', text: 'hi from goose' }, { type: 'tool_call', id: 't1', name: 'shell', arguments: { cmd: 'ls' } }] } },
    { type: 'tool_call_response', id: 't1', output: 'ok' },
    { type: 'finish', reason: EXIT === 0 ? 'done' : 'error' },
  ],
  pi: [
    { type: 'session', id: sid },
    { type: 'message_end', message: { role: 'assistant', content: [{ type: 'text', text: 'hi from pi' }, { type: 'tool_call', id: 't1', name: 'read', input: { path: 'x' } }] } },
    { type: 'message_end', message: { role: 'toolResult', content: [{ type: 'text', text: 'ok' }] } },
    { type: 'turn_end' },
  ],
};

const out = frames[engineKey] || frames.gemini;
const skipResult = process.env.FAKE_SKIP_RESULT === '1';
for (const f of out) {
  if (skipResult && f.type === 'result') continue; // exit-code fallback test: no engine result frame
  process.stdout.write(`${JSON.stringify(f)}\n`);
}

if (EXIT !== 0) {
  process.stderr.write(`simulated failure ${EXIT}\n`);
}
process.exit(EXIT);
