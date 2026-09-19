// One-shot protocol probe for `codex app-server` (codex-cli 0.155.x).
// Confirms the fixed request shapes, then is deleted.
import { spawn } from 'child_process';

const CODEX = 'C:/nvm4w/nodejs/codex.cmd';
const proc = spawn(CODEX, ['app-server'], { cwd: process.cwd(), stdio: ['pipe', 'pipe', 'pipe'], shell: true });
let buf = '';
const pending = new Map();
let seq = 0;

proc.stdout.on('data', (d) => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i); buf = buf.slice(i + 1);
    if (!line.trim()) continue;
    let j; try { j = JSON.parse(line); } catch { continue; }
    if (j.id !== undefined && pending.has(j.id)) {
      const res = pending.get(j.id); pending.delete(j.id);
      console.log(`<< RESPONSE id=${j.id}`, j.error ? 'ERROR=' + JSON.stringify(j.error) : 'OK ' + JSON.stringify(j.result ?? {}).slice(0, 220));
      res(j);
    } else if (j.method) {
      if (!/^(mcpServer|configWarning|remoteControl)/.test(j.method)) {
        console.log('<< NOTIFY', j.method, JSON.stringify(j.params ?? {}).slice(0, 140));
      }
    }
  }
});
proc.stderr.on('data', () => {});

function request(method, params, timeoutMs = 20000) {
  const id = ++seq;
  console.log('>>', method, JSON.stringify(params).slice(0, 220));
  proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  return new Promise((resolve) => {
    const t = setTimeout(() => { pending.delete(id); resolve({ TIMEOUT: true }); }, timeoutMs);
    pending.set(id, (r) => { clearTimeout(t); resolve(r); });
  });
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
await sleep(800);

await request('initialize', { clientInfo: { name: 'idd-probe', title: 'probe', version: '1.0.0' } });
const th = await request('thread/start', { cwd: process.cwd(), approvalPolicy: 'on-request' });
const threadId = th.result?.threadId || th.result?.thread_id || th.result?.id || th.result?.thread?.id;
console.log('== threadId =', threadId);

console.log('== FIXED shape: turn/start { threadId, input:[{type:"text",text}] }');
const tr = await request('turn/start', { threadId, input: [{ type: 'text', text: 'Reply with exactly: OK-FROM-CODEX' }] }, 90000);
console.log('== turn/start resolved:', JSON.stringify(tr.result ?? tr.error ?? tr).slice(0, 200));

await sleep(10000);
proc.kill();
process.exit(0);
