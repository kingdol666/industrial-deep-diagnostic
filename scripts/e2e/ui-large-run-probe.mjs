#!/usr/bin/env node
// Large-run rendering probe: open a run with a big event stream in the real UI
// and measure time-to-interactive, DOM weight, heap, and input latency.
// Usage: node scripts/e2e/ui-large-run-probe.mjs --run <runId> --web http://127.0.0.1:5180
import { spawn } from 'child_process';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join } from 'path';

const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const API = opt('api', 'http://127.0.0.1:3210').replace(/\/$/, '');
const WEB = opt('web', 'http://127.0.0.1:5180').replace(/\/$/, '');
const RUN = opt('run');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');
if (!RUN) { console.error('--run required'); process.exit(2); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function freePort() { return new Promise((res) => { const s = createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); }); }
function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const c = process.platform === 'win32'
    ? ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']
    : ['/usr/bin/google-chrome'];
  return c.find((p) => existsSync(p));
}
class CDP {
  constructor(u) { this.ws = new WebSocket(u); this.i = 0; this.p = new Map();
    this.ws.addEventListener('message', (ev) => { let m; try { m = JSON.parse(ev.data); } catch { return; }
      if (m.id && this.p.has(m.id)) { const { resolve: res, reject } = this.p.get(m.id); this.p.delete(m.id); m.error ? reject(new Error(m.error.message)) : res(m.result); return; }
      if (m.method) for (const f of this.l.get(m.method) || []) f(m.params); }); }
  async open() { await new Promise((res, rej) => { this.ws.addEventListener('open', res, { once: true }); this.ws.addEventListener('error', () => rej(new Error('ws')), { once: true }); }); }
  send(method, params = {}) { const id = ++this.i; return new Promise((res, rej) => { this.p.set(id, { resolve: res, reject: rej }); this.ws.send(JSON.stringify({ id, method, params })); setTimeout(() => { if (this.p.has(id)) { this.p.delete(id); rej(new Error('to ' + method)); } }, 30000).unref?.(); }); }
  on(m, f) { if (!this.l) this.l = new Map(); if (!this.l.has(m)) this.l.set(m, []); this.l.get(m).push(f); }
}
const ev_ = async (c, e) => (await c.send('Runtime.evaluate', { expression: e, returnByValue: true })).result?.value;
const click = async (c, s) => { const r = await ev_(c, `(()=>{const el=document.querySelector(${JSON.stringify(s)});if(!el)return null;el.scrollIntoView({block:'center'});const b=el.getBoundingClientRect();return{x:Math.round(b.left+b.width/2),y:Math.round(b.top+b.height/2)};})()`);
  await c.send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...r });
  await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...r, button: 'left', buttons: 1, clickCount: 1 });
  await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...r, button: 'left', buttons: 0, clickCount: 1 }); };

const login_ = await fetch(`${API}/api/auth/login`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ username: USER, password: PASS }) }).then((r) => r.json());
if (!login_?.data?.session_token) { console.error('login failed'); process.exit(2); }
const token = login_.data.session_token;
const snap = await fetch(`${API}/api/diagnosis/snapshot/${RUN}`, { headers: { authorization: `Bearer ${token}` } }).then((r) => r.json());
const eventCount = snap.data?.events?.length ?? -1;

const port = await freePort();
const profile = mkdtempSync(join(tmpdir(), 'idd-large-'));
const proc = spawn(findBrowser(), ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', '--window-size=1440,900'], { stdio: 'ignore', windowsHide: true });
const errors = [];
try {
  let target = null;
  for (let i = 0; i < 100 && !target; i += 1) { await sleep(150); try { const r = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' }); if (r.ok) target = await r.json(); } catch { } }
  const c = new CDP(target.webSocketDebuggerUrl); await c.open();
  c.on('Runtime.consoleAPICalled', (p) => { if (p.type === 'error') errors.push((p.args || []).map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 160)); });
  c.on('Runtime.exceptionThrown', (p) => errors.push(String(p.exceptionDetails?.exception?.description || p.exceptionDetails?.text || 'exception').slice(0, 160)));
  await c.send('Page.enable'); await c.send('Runtime.enable');
  await c.send('Page.navigate', { url: WEB });
  for (let i = 0; i < 300; i += 1) { if (await ev_(c, `!!document.querySelector('[data-testid="auth-username"]')`)) break; await sleep(150); }
  await click(c, '[data-testid="auth-username"]'); await c.send('Input.insertText', { text: USER });
  await click(c, '[data-testid="auth-password"]'); await c.send('Input.insertText', { text: PASS });
  await click(c, '[data-testid="auth-submit"]');
  for (let i = 0; i < 300; i += 1) { if (await ev_(c, `!!document.querySelector('[data-testid="nav-history"]')`)) break; await sleep(150); }
  await click(c, '[data-testid="nav-history"]');
  for (let i = 0; i < 300; i += 1) { if (await ev_(c, `!!document.querySelector('[data-testid="history-continue-${RUN}"]')`)) break; await sleep(150); }
  const t0 = Date.now();
  await click(c, `[data-testid="history-continue-${RUN}"]`);
  let opened = false;
  for (let i = 0; i < 600; i += 1) { if (await ev_(c, `!!document.querySelector('[data-testid="run-chat-input"]')`)) { opened = true; break; } await sleep(100); }
  const openMs = Date.now() - t0;
  await sleep(3000); // let replay/autoscroll settle
  const stats = await ev_(c, `(() => {
    const stream = document.querySelector('.message-stream');
    return {
      domNodes: document.querySelectorAll('*').length,
      streamNodes: stream ? stream.querySelectorAll('*').length : -1,
      renderedItems: stream ? stream.children.length : -1,
      heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
      streamTextHead: stream ? stream.innerText.replace(/\s+/g, ' ').slice(0, 220) : null,
      windowBadge: document.querySelector('.sm-window')?.innerText?.replace(/\s+/g, ' ').trim() || null,
    };
  })()`);
  const latencies = [];
  for (let i = 0; i < 5; i += 1) { const t = Date.now(); await ev_(c, '1+1'); latencies.push(Date.now() - t); await sleep(100); }
  const shotPath = opt('shot');
  if (shotPath) {
    const { data } = await c.send('Page.captureScreenshot', { format: 'png' });
    mkdirSync(join(shotPath, '..'), { recursive: true });
    writeFileSync(shotPath, Buffer.from(data, 'base64'));
    console.log(`screenshot ${shotPath}`);
  }
  console.log(JSON.stringify({
    run: RUN, apiEvents: eventCount, openMs, opened,
    evalLatencyMs: latencies, consoleErrors: errors.slice(0, 5), ...stats,
  }, null, 2));
} finally {
  try { proc.kill(); } catch { }
  if (process.platform === 'win32' && proc.pid) { try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true }); } catch { } }
  try { rmSync(profile, { recursive: true, force: true }); } catch { }
}
process.exit(0);
