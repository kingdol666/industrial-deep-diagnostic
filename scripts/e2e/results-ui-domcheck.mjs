#!/usr/bin/env node
// DOM verification: results table summary density + visual structure sanity.
import { spawn } from 'child_process';
import { existsSync, mkdtempSync, rmSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join } from 'path';

const API = 'http://127.0.0.1:3210';
const WEB = 'http://127.0.0.1:5180';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((resolve) => {
  const srv = createServer();
  srv.listen(0, '127.0.0.1', () => { const { port } = srv.address(); srv.close(() => resolve(port)); });
});
const findBrowser = () => ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']
  .find((p) => existsSync(p));

const login = await fetch(`${API}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: 'e2e_ontology', password: 'E2e-Onto-2026!' }),
});
const token = (await login.json())?.data?.session_token || '';

const port = await freePort();
const profile = mkdtempSync(join(tmpdir(), 'idd-dom-'));
const proc = spawn(findBrowser(), [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--disable-gpu', '--hide-scrollbars', '--window-size=1440,900',
], { stdio: 'ignore', windowsHide: true });

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
      setTimeout(() => this.pending.has(id) && (this.pending.delete(id), reject(new Error('timeout'))), 30000).unref?.();
    });
  }
  close() { try { this.ws.close(); } catch {} }
}
async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (exceptionDetails) throw new Error(exceptionDetails.text);
  return result?.value;
}
async function waitFor(cdp, expr, timeout = 30000) {
  const dl = Date.now() + timeout;
  while (Date.now() < dl) {
    if (await evaluate(cdp, expr).catch(() => false)) return;
    await sleep(150);
  }
  throw new Error(`timeout: ${expr}`);
}
const sel = (s) => `document.querySelector(${JSON.stringify(s)})`;
async function click(cdp, s) {
  const { x, y } = await evaluate(cdp, `(() => { const el=${sel(s)}; el.scrollIntoView({block:'center'}); const b=el.getBoundingClientRect(); return {x:Math.round(b.left+b.width/2),y:Math.round(b.top+b.height/2)}; })()`);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 });
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
  await cdp.send('Page.navigate', { url: WEB });
  await waitFor(cdp, `${sel('[data-testid="auth-username"]')} !== null`, 45000);
  await evaluate(cdp, `localStorage.setItem('auth_token', ${JSON.stringify(token)}); localStorage.setItem('auth_user', ${JSON.stringify(JSON.stringify({ id: 21, username: 'e2e_ontology', role: 'user' }))}); true`);
  await cdp.send('Page.navigate', { url: WEB });
  await waitFor(cdp, `${sel('[data-testid="nav-results"]')} !== null`);
  await click(cdp, '[data-testid="nav-results"]');
  await waitFor(cdp, `document.querySelectorAll('[data-testid^="results-row-"]').length > 0`);
  await sleep(1000);

  const stats = await evaluate(cdp, `(() => {
    const rows = [...document.querySelectorAll('[data-testid^="results-row-"]')];
    const cells = rows.map((r) => r.querySelector('.cell-summary')?.textContent?.trim() || '');
    const withSummary = cells.filter((c) => c && c !== '--').length;
    const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    // column alignment sanity: every row has 8 cells
    const cellCounts = rows.map((r) => r.querySelectorAll('td').length);
    return { rows: rows.length, withSummary, overflowX, cellCountsOk: cellCounts.every((n) => n === 8) };
  })()`);
  console.log('[DOM]', JSON.stringify(stats));
  const ok = stats.rows > 0 && stats.withSummary >= Math.floor(stats.rows * 0.7) && !stats.overflowX && stats.cellCountsOk;
  console.log(`[RESULT] ${ok ? 'PASS' : 'FAIL'} — ${stats.withSummary}/${stats.rows} rows carry a summary, overflowX=${stats.overflowX}, cells8=${stats.cellCountsOk}`);
  cdp.close();
  process.exitCode = ok ? 0 : 1;
} finally {
  try { proc.kill(); } catch {}
  if (proc.pid) { try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' }); } catch {} }
  await sleep(400);
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
