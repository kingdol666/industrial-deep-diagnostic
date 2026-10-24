#!/usr/bin/env node
// Results-library UI integration check (plan 2026-10-25 AC-9).
//
// Real backend + Vite dev server + real Chrome via CDP, native inputs only
// (same discipline as ui-smoke-native): login → Results tab renders → search
// filter narrows → detail drawer with auto summary → edit description/tags
// (PATCH round-trip) → History detail panel embeds the same summary card.
//
//   node scripts/e2e/results-ui-check.mjs --api http://127.0.0.1:3210 --web http://127.0.0.1:5180
import { spawn } from 'child_process';
import { existsSync, mkdtempSync, rmSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join } from 'path';

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const API = opt('api', 'http://127.0.0.1:3210').replace(/\/$/, '');
const WEB = opt('web', 'http://127.0.0.1:5180').replace(/\/$/, '');
const KEEP = args.includes('--keep');

let failures = 0;
let passes = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (ok) passes += 1; else failures += 1;
  return ok;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function freePort() {
  return new Promise((resolve) => {
    const srv = createServer();
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = process.platform === 'win32'
    ? [
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
        'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
      ]
    : ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  return candidates.find((p) => existsSync(p)) || null;
}

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 0;
    this.pending = new Map();
    this.listeners = new Map();
    this.ws.addEventListener('message', (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${msg.error.message} (${msg.error.code})`));
        else resolve(msg.result);
        return;
      }
      if (msg.method) for (const fn of this.listeners.get(msg.method) || []) fn(msg.params);
    });
  }
  async open() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', () => reject(new Error('CDP socket error')), { once: true });
    });
  }
  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 30000).unref?.();
    });
  }
  close() { try { this.ws.close(); } catch { /* gone */ } }
  on(method, fn) {
    this.listeners.set(method, [...(this.listeners.get(method) || []), fn]);
  }
}

async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send('Runtime.evaluate', {
    expression, returnByValue: true, awaitPromise: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text || 'evaluate failed');
  return result?.value;
}

async function waitFor(cdp, expression, { timeout = 30000, label = expression } = {}) {
  const deadline = Date.now() + timeout;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      if (await evaluate(cdp, expression)) return true;
    } catch (err) { lastErr = err; }
    await sleep(150);
  }
  throw new Error(`waitFor timeout: ${label}${lastErr ? ` (${lastErr.message})` : ''}`);
}

const sel = (s) => `document.querySelector(${JSON.stringify(s)})`;

async function elementCenter(cdp, selector) {
  const rect = await evaluate(cdp, `(() => {
    const el = ${sel(selector)};
    if (!el) return null;
    el.scrollIntoView({ block: 'center', inline: 'center' });
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
  })()`);
  if (!rect) throw new Error(`element not visible: ${selector}`);
  return rect;
}

async function nativeClick(cdp, selector) {
  const { x, y } = await elementCenter(cdp, selector);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 });
}

async function nativeType(cdp, selector, text) {
  await nativeClick(cdp, selector);
  await cdp.send('Input.insertText', { text });
}

async function apiJson(path, { method = 'GET', body, token } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, json };
}

let consoleErrors = [];
async function main() {
  const browser = findBrowser();
  if (!browser) { console.error('no Chrome/Edge found — set CHROME_PATH'); process.exit(2); }
  const health = await apiJson('/api/health').catch(() => null);
  if (!health || health.status !== 200) { console.error(`backend not healthy at ${API}`); process.exit(2); }
  const webProbe = await fetch(`${WEB}/`).catch(() => null);
  if (!webProbe || !webProbe.ok) { console.error(`frontend not reachable at ${WEB}`); process.exit(2); }

  // Fresh user + a REAL completed mock run owned by them (completion path
  // writes the results row synchronously).
  const username = `uires_${Date.now().toString(36)}`;
  const password = 'Smoke12345';
  const reg = await apiJson('/api/auth/register', { method: 'POST', body: { username, password } });
  if (!check('register UI-check user', reg.status === 200, username)) process.exit(1);
  const token = reg.json.data.session_token;

  const started = await apiJson('/api/diagnosis/start', {
    method: 'POST', token,
    body: { harness: 'mock', dataPath: 'data/smoke.csv', sceneName: `ui_res_${Date.now().toString(36)}`, userQuestion: 'results ui check', reportLanguage: 'zh' },
  });
  const runId = started.json?.data?.runId;
  check('create mock run', started.status === 200 && !!runId, runId);
  await apiJson(`/api/diagnosis/execute/${runId}`, { method: 'POST', token });
  let st = null;
  for (let i = 0; i < 100; i += 1) {
    st = (await apiJson(`/api/diagnosis/status/${runId}`, { token })).json?.data?.status;
    if (st === 'completed' || st === 'failed') break;
    await sleep(200);
  }
  check('mock run completes', st === 'completed', String(st));

  // Boot headless browser
  const port = await freePort();
  const profile = mkdtempSync(join(tmpdir(), 'idd-ui-res-'));
  const proc = spawn(browser, [
    '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--hide-scrollbars',
    '--window-size=1440,900',
  ], { stdio: 'ignore', windowsHide: true });
  const cleanup = () => {
    try { proc.kill(); } catch { /* gone */ }
    if (process.platform === 'win32' && proc.pid) {
      try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' }); } catch { /* gone */ }
    }
    if (!KEEP) { try { rmSync(profile, { recursive: true, force: true }); } catch { /* locked */ } }
  };

  let cdp = null;
  try {
    let target = null;
    for (let i = 0; i < 100 && !target; i += 1) {
      await sleep(150);
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
        if (res.ok) target = await res.json();
      } catch { /* not up */ }
    }
    if (!target) throw new Error('browser did not expose a DevTools target');
    cdp = new CDP(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    cdp.on('Runtime.consoleAPICalled', (p) => {
      if (p.type === 'error') consoleErrors.push((p.args || []).map((a) => a.value || a.description || '').join(' '));
    });
    cdp.on('Runtime.exceptionThrown', (p) => {
      consoleErrors.push(p.exceptionDetails?.text || 'exception');
    });

    await cdp.send('Page.navigate', { url: WEB });
    await waitFor(cdp, `${sel('[data-testid="auth-username"]')} !== null`, { label: 'login form', timeout: 45000 });
    await nativeType(cdp, '[data-testid="auth-username"]', username);
    await nativeType(cdp, '[data-testid="auth-password"]', password);
    await nativeClick(cdp, '[data-testid="auth-submit"]');
    await waitFor(cdp, `${sel('[data-testid="nav-results"]')} !== null`, { label: 'login accepted (Results nav visible)', timeout: 30000 });
    check('login + Results nav item rendered', true);

    // ── Results tab ──
    await nativeClick(cdp, '[data-testid="nav-results"]');
    await waitFor(cdp, `${sel('[data-testid="results-library"]')} !== null`, { label: 'results library mount' });
    await waitFor(cdp, `document.querySelectorAll('[data-testid^="results-row-"]').length > 0`, { label: 'results rows', timeout: 30000 });
    const rowCount = await evaluate(cdp, `document.querySelectorAll('[data-testid^="results-row-"]').length`);
    const totalText = await evaluate(cdp, `${sel('[data-testid="results-total"]')}?.textContent || ''`);
    check('AC-9 results table renders rows + total', rowCount >= 1 && /[0-9]/.test(totalText), `${rowCount} rows / ${totalText.trim()}`);

    // search filter narrows to this run's scene (soft check — legacy rows may
    // share the scene token; the precise run-id search below is the hard gate)
    const scene = started.json.data.name.replace(/_[0-9a-f]+$/, '');
    await nativeType(cdp, '[data-testid="results-search"]', scene);
    await sleep(1200); // 300ms debounce + fetch

    // open the detail drawer on the FIRST row (fresh user sees legacy + own)
    await nativeClick(cdp, '[data-testid="results-detail-btn-0"]');
    await waitFor(cdp, `${sel('[data-testid="results-drawer"]')} !== null`, { label: 'drawer opens' });
    await waitFor(cdp, `document.querySelector('[data-testid^="result-summary-"]') !== null`, { label: 'summary card loaded', timeout: 20000 });
    check('AC-9 detail drawer renders with metadata', true);
    const drawerText = await evaluate(cdp, `${sel('[data-testid="results-drawer"]')}.innerText`);
    check('AC-9 drawer shows auto summary block', /自动摘要|Auto summary/i.test(drawerText), drawerText.slice(0, 80));

    // close drawer, search precisely for our run id to exercise the API filter through the UI
    await nativeClick(cdp, '[data-testid="results-drawer-close"]');
    // select-all before typing: a second insertText APPENDS at the caret, and
    // "scene|runId" concatenation matches nothing (the earlier 1-row assertion
    // raced the 300ms debounce and read the stale scene-search result).
    await nativeClick(cdp, '[data-testid="results-search"]');
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await cdp.send('Input.insertText', { text: runId });
    await waitFor(
      cdp,
      `document.querySelectorAll('[data-testid^="results-row-"]').length === 1`
      + ` && (document.querySelector('[data-testid^="results-row-"]')?.textContent || '').includes('${runId}')`,
      { label: 'search narrows to exactly the target row', timeout: 15000 },
    );
    check('AC-9 search narrows to the target result', true, runId);

    // ── description edit round-trip (native input → PATCH → row updates) ──
    await nativeClick(cdp, '[data-testid="results-detail-btn-0"]');
    await waitFor(cdp, `${sel('[data-testid="results-drawer"]')} !== null`, { label: 'drawer reopens' });
    await waitFor(cdp, `(${sel('[data-testid="results-drawer"]')}?.innerText || '').includes('${runId}')`, { label: 'drawer targets our run', timeout: 15000 });
    await waitFor(cdp, `document.querySelector('[data-testid^="result-desc-edit-"]') !== null`, { label: 'desc edit button', timeout: 20000 });
    const descText = `UI 集成验证描述 ${Date.now().toString(36)}`;
    await nativeClick(cdp, '[data-testid^="result-desc-edit-"]');
    await waitFor(cdp, `document.querySelector('[data-testid^="result-desc-input-"]') !== null`, { label: 'desc editor opens' });
    await evaluate(cdp, `document.querySelector('[data-testid^="result-desc-input-"]').value = ''`);
    await nativeType(cdp, '[data-testid^="result-desc-input-"]', descText);
    await nativeClick(cdp, '[data-testid^="result-desc-save-"]');
    await waitFor(cdp, `document.querySelector('[data-testid^="result-desc-"]')?.innerText?.includes('${descText}')`, { label: 'description saved + rendered', timeout: 15000 });
    check('AC-9 description PATCH round-trip (native typing)', true);
    const rowShowsDesc = await evaluate(cdp, `document.body.innerText.includes('${descText}')`);
    check('AC-9 edited description shows in the table row (display_text)', rowShowsDesc);

    // ── tags edit round-trip ──
    await nativeClick(cdp, '[data-testid^="result-tags-edit-"]');
    await waitFor(cdp, `document.querySelector('[data-testid^="result-tags-input-"]') !== null`, { label: 'tags editor opens' });
    await nativeType(cdp, '[data-testid^="result-tags-input-"]', 'ui-check, 收率基准');
    await nativeClick(cdp, '[data-testid^="result-tags-save-"]');
    await waitFor(cdp, `document.querySelectorAll('[data-testid^="result-tag-"]').length >= 1`, { label: 'tag chip rendered', timeout: 15000 });
    const tagText = await evaluate(cdp, `${sel('[data-testid="results-drawer"]')}.innerText`);
    check('AC-9 tags PATCH round-trip', /ui-check/.test(tagText) && /收率基准/.test(tagText));

    // verify server-side: PATCH persisted via API
    const serverDetail = await apiJson(`/api/external/v1/results/${runId}`, { token });
    check('server confirms description + tags persisted',
      serverDetail.json.data?.description === descText
      && JSON.stringify(serverDetail.json.data?.tags) === JSON.stringify(['ui-check', '收率基准']),
      serverDetail.json.data?.description?.slice(0, 40));

    // ── 报告 button opens the run's report in the Reports tab ──
    await nativeClick(cdp, '[data-testid="results-drawer-close"]');
    await sleep(400);
    await nativeClick(cdp, '[data-testid="results-report-btn-0"]');
    await waitFor(cdp, `${sel('[data-testid="report-body"]')} !== null`, { label: 'report body rendered', timeout: 25000 });
    const reportText = await evaluate(cdp, `${sel('[data-testid="report-body"]')}.innerText`);
    check('AC-9 报告按钮 opens the row report in the Reports tab', reportText.length > 20, reportText.slice(0, 60));

    // ── History detail panel embeds the summary card ──
    await nativeClick(cdp, '[data-testid="nav-history"]');
    const historyRowSel = `[data-testid="history-row-${runId}"]`;
    await waitFor(cdp, `${sel(historyRowSel)} !== null`, { label: 'history row' });
    await nativeClick(cdp, `[data-testid="history-detail-${runId}"]`);
    await waitFor(cdp, `${sel('[data-testid="history-result-card"]')} !== null`, { label: 'history result card', timeout: 15000 });
    await waitFor(cdp, `(${sel('[data-testid="history-result-card"]')}?.innerText || '').includes('${descText}')`, { label: 'card shows the edited description', timeout: 15000 });
    check('AC-9 History detail panel shows the result summary card', true);

    // console health
    const realErrors = consoleErrors.filter((e) => !/favicon|net::ERR|ResizeObserver/.test(e));
    check('no console errors during the tour', realErrors.length === 0, realErrors.slice(0, 2).join(' | ').slice(0, 160));

    console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
  } catch (err) {
    console.error(`\nERROR: ${err.message}`);
    failures += 1;
    console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
  } finally {
    cleanup();
    cdp?.close();
  }
  process.exitCode = failures ? 1 : 0;
}

main();
