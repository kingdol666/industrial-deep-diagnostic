#!/usr/bin/env node
// Screenshot the new Results tab + History summary card for visual acceptance.
//   node scripts/e2e/results-ui-screenshots.mjs --api http://127.0.0.1:3210 --web http://127.0.0.1:5180 --out workspace/acceptance/2026-10-25
import { spawn } from 'child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join } from 'path';

const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const API = opt('api', 'http://127.0.0.1:3210').replace(/\/$/, '');
const WEB = opt('web', 'http://127.0.0.1:5180').replace(/\/$/, '');
const OUT = opt('out', 'workspace/acceptance/2026-10-25');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function freePort() {
  return new Promise((resolve) => {
    const srv = createServer();
    srv.listen(0, '127.0.0.1', () => { const { port } = srv.address(); srv.close(() => resolve(port)); });
  });
}
function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const c = process.platform === 'win32'
    ? ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe']
    : ['/usr/bin/google-chrome', '/usr/bin/chromium'];
  return c.find((p) => existsSync(p)) || null;
}

const login = await fetch(`${API}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const token = (await login.json())?.data?.session_token || '';
if (!token) { console.error('login failed'); process.exit(1); }

const browser = findBrowser();
const port = await freePort();
const profile = mkdtempSync(join(tmpdir(), 'idd-shot-'));
const proc = spawn(browser, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--disable-gpu', '--hide-scrollbars', '--window-size=1440,900',
], { stdio: 'ignore', windowsHide: true });
mkdirSync(OUT, { recursive: true });

class CDP {
  constructor(url) { this.ws = new WebSocket(url); this.nextId = 0; this.pending = new Map();
    this.ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id); this.pending.delete(msg.id);
        msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
      }
    });
  }
  async open() { await new Promise((r, j) => { this.ws.addEventListener('open', r, { once: true }); this.ws.addEventListener('error', j, { once: true }); }); }
  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => this.pending.has(id) && (this.pending.delete(id), reject(new Error(`timeout ${method}`))), 30000).unref?.();
    });
  }
  close() { try { this.ws.close(); } catch {} }
}
async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (exceptionDetails) throw new Error(exceptionDetails.text);
  return result?.value;
}
async function waitFor(cdp, expression, timeout = 30000) {
  const dl = Date.now() + timeout;
  while (Date.now() < dl) {
    if (await evaluate(cdp, expression).catch(() => false)) return;
    await sleep(150);
  }
  throw new Error(`waitFor timeout: ${expression}`);
}
const sel = (s) => `document.querySelector(${JSON.stringify(s)})`;
async function center(cdp, selector) {
  const r = await evaluate(cdp, `(() => { const el=${sel(selector)}; if(!el) return null; el.scrollIntoView({block:'center'}); const b=el.getBoundingClientRect(); return {x:Math.round(b.left+b.width/2),y:Math.round(b.top+b.height/2)}; })()`);
  if (!r) throw new Error(`not visible: ${selector}`);
  return r;
}
async function click(cdp, s) {
  const { x, y } = await center(cdp, s);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 });
}
async function type(cdp, s, text) {
  await click(cdp, s);
  await cdp.send('Input.insertText', { text });
}
async function shot(cdp, name) {
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
  const p = join(OUT, name);
  writeFileSync(p, Buffer.from(data, 'base64'));
  console.log('screenshot', p, `${Math.round(data.length / 1024)}KB`);
}

try {
  let target = null;
  for (let i = 0; i < 100 && !target; i += 1) {
    await sleep(150);
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
      if (res.ok) target = await res.json();
    } catch {}
  }
  const cdp = new CDP(target.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  // login via localStorage token (screenshots don't need native typing)
  await cdp.send('Page.navigate', { url: WEB });
  await waitFor(cdp, `${sel('[data-testid="auth-username"]')} !== null`, 45000);
  await evaluate(cdp, `localStorage.setItem('auth_token', ${JSON.stringify(token)}); localStorage.setItem('auth_user', ${JSON.stringify(JSON.stringify({ id: 21, username: USER, role: 'user' }))}); true`);
  await cdp.send('Page.navigate', { url: WEB });
  await waitFor(cdp, `${sel('[data-testid="nav-results"]')} !== null`, 30000);

  // 1) Results tab — full table
  await click(cdp, '[data-testid="nav-results"]');
  await waitFor(cdp, `document.querySelectorAll('[data-testid^="results-row-"]').length > 0`);
  await sleep(800);
  await shot(cdp, 'results-tab-1440.png');

  // 2) Detail drawer on the real stability run (score 65.8)
  await type(cdp, '[data-testid="results-search"]', 'accept_api');
  await sleep(1000);
  await click(cdp, '[data-testid="results-detail-btn-0"]');
  await waitFor(cdp, `document.querySelector('[data-testid^="result-summary-"]') !== null`);
  await sleep(500);
  await shot(cdp, 'results-detail-drawer.png');

  // 3) drawer edit mode
  await click(cdp, '[data-testid^="result-desc-edit-"]');
  await sleep(400);
  await shot(cdp, 'results-detail-editing.png');

  // 4) History detail with embedded summary card
  await click(cdp, '[data-testid="nav-history"]');
  await waitFor(cdp, `document.querySelectorAll('[data-testid^="history-row-"]').length > 0`);
  await type(cdp, '[data-testid="history-search"]', 'accept_api');
  await sleep(1000);
  const firstRowId = await evaluate(cdp, `document.querySelector('[data-testid^="history-row-"]')?.getAttribute('data-testid') || ''`);
  const runId = firstRowId.replace('history-row-', '');
  await click(cdp, `[data-testid="history-detail-${runId}"]`);
  await waitFor(cdp, `${sel('[data-testid="history-result-card"]')} !== null`);
  await sleep(500);
  await shot(cdp, 'history-detail-summary-card.png');

  console.log('[RESULT] screenshots captured');
  cdp.close();
} catch (err) {
  console.error('ERROR:', err.message);
  process.exitCode = 1;
} finally {
  try { proc.kill(); } catch {}
  if (process.platform === 'win32' && proc.pid) {
    try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' }); } catch {}
  }
  await sleep(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
