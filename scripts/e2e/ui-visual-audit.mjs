#!/usr/bin/env node
// UI acceptance audit: real browser interaction + console/network health +
// screenshots for visual review (AC-D/AC-E of
// docs/plans/followups-acceptance-2026-10-22.md).
//
// Interactions use the DevTools Input domain (real mouse/keys). The audit fails
// on: uncaught page exceptions, console errors, failed /api/* responses,
// horizontal page overflow, missing score/verdict text, empty report/HTML.
//
//   node scripts/e2e/ui-visual-audit.mjs --api http://127.0.0.1:3211 --web http://127.0.0.1:5181 \
//     --run 46833919 --out workspace/acceptance/2026-10-22
import { spawn } from 'child_process';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join, resolve } from 'path';

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const API = opt('api', 'http://127.0.0.1:3211').replace(/\/$/, '');
const WEB = opt('web', 'http://127.0.0.1:5181').replace(/\/$/, '');
const RUN = opt('run', '46833919');
const OUT = resolve(opt('out', 'workspace/acceptance/2026-10-22'));
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');

let failures = 0;
const results = [];
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 240)}` : ''}`);
  results.push({ name, ok: !!ok, detail: String(detail || '') });
  if (!ok) failures += 1;
  return ok;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function freePort() {
  return new Promise((resolvePromise) => {
    const srv = createServer();
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolvePromise(port));
    });
  });
}

function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = process.platform === 'win32'
    ? [
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
        'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
      ]
    : process.platform === 'darwin'
      ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
      : ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/microsoft-edge'];
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
        const { resolve: res, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${msg.error.message} (${msg.error.code})`));
        else res(msg.result);
        return;
      }
      if (msg.method) for (const fn of this.listeners.get(msg.method) || []) fn(msg.params);
    });
  }

  async open() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise((res, rej) => {
      this.ws.addEventListener('open', res, { once: true });
      this.ws.addEventListener('error', () => rej(new Error('CDP socket error')), { once: true });
    });
  }

  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((res, rej) => {
      this.pending.set(id, { resolve: res, reject: rej });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) { this.pending.delete(id); rej(new Error(`CDP timeout: ${method}`)); }
      }, 30000).unref?.();
    });
  }

  on(method, fn) {
    if (!this.listeners.has(method)) this.listeners.set(method, []);
    this.listeners.get(method).push(fn);
  }

  close() { try { this.ws.close(); } catch { /* closed */ } }
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
  while (Date.now() < deadline) {
    try { if (await evaluate(cdp, expression)) return true; } catch { /* page swapping */ }
    await sleep(150);
  }
  throw new Error(`waitFor timeout: ${label}`);
}

async function center(cdp, selector) {
  const info = await evaluate(cdp, `(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) {
      const row = document.querySelector('[data-testid^="history-"]');
      return { state: 'missing', anyHistoryNode: !!row };
    }
    el.scrollIntoView({ block: 'center', inline: 'center' });
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) {
      return { state: 'zero-rect', w: r.width, h: r.height, display: getComputedStyle(el).display,
               visible: el.offsetParent !== null };
    }
    return { state: 'ok', x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
  })()`);
  if (!info || info.state !== 'ok') throw new Error(`not interactable: ${selector} ${JSON.stringify(info)}`);
  return info;
}

async function click(cdp, selector) {
  const { x, y } = await center(cdp, selector);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 });
}

async function type(cdp, selector, text) {
  await click(cdp, selector);
  await cdp.send('Input.insertText', { text });
}

async function shot(cdp, name, { full = false } = {}) {
  // The console scrolls inside .app-content (not the window). Reset it so the
  // capture includes the table header / page top; leave inner panes (message
  // stream) alone.
  await evaluate(cdp, `(() => {
    document.querySelector('.app-content')?.scrollTo?.(0, 0);
    const wrapper = document.querySelector('.history-table-wrapper');
    if (wrapper) wrapper.scrollLeft = 0;
    window.scrollTo(0, 0);
  })()`).catch(() => {});
  await sleep(250);
  let params = { format: 'png' };
  if (full) {
    const { cssContentSize } = await cdp.send('Page.getLayoutMetrics');
    params = {
      format: 'png', captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: Math.ceil(cssContentSize.width), height: Math.min(Math.ceil(cssContentSize.height), 4000), scale: 1 },
    };
  }
  const { data } = await cdp.send('Page.captureScreenshot', params);
  const file = join(OUT, name);
  writeFileSync(file, Buffer.from(data, 'base64'));
  console.log(`  screenshot ${file}`);
  return file;
}

const consoleErrors = [];
const pageExceptions = [];
const failedApi = [];

function wireAudit(cdp) {
  cdp.on('Runtime.exceptionThrown', (p) => {
    pageExceptions.push(p.exceptionDetails?.exception?.description || p.exceptionDetails?.text || 'exception');
  });
  cdp.on('Runtime.consoleAPICalled', (p) => {
    if (p.type !== 'error') return;
    const text = (p.args || []).map((a) => a.value ?? a.description ?? '').join(' ').trim();
    if (text) consoleErrors.push(text);
  });
  cdp.on('Log.entryAdded', (p) => {
    if (p.entry?.level !== 'error') return;
    if (p.entry.source === 'network') return; // network audit below
    consoleErrors.push(`${p.entry.source}: ${p.entry.text}`);
  });
  cdp.on('Network.responseReceived', (p) => {
    const { url, status } = p.response || {};
    if (typeof url === 'string' && url.includes('/api/') && status >= 400) {
      failedApi.push(`${status} ${url.replace(API, '').slice(0, 160)}`);
    }
  });
  cdp.on('Network.loadingFailed', (p) => {
    if (p.errorText === 'net::ERR_ABORTED') return;
    const url = p.url || '';
    if (url.includes('/api/')) failedApi.push(`FAILED ${p.errorText} ${url.replace(API, '').slice(0, 160)}`);
  });
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = findBrowser();
  if (!browser) { console.error('no Chrome/Edge — set CHROME_PATH'); process.exit(2); }
  const health = await fetch(`${API}/api/health`).then((r) => r.ok).catch(() => false);
  if (!health) { console.error(`backend not healthy at ${API}`); process.exit(2); }
  const web = await fetch(`${WEB}/`).then((r) => r.ok).catch(() => false);
  if (!web) { console.error(`frontend not reachable at ${WEB}`); process.exit(2); }

  const port = await freePort();
  const profile = mkdtempSync(join(tmpdir(), 'idd-visual-audit-'));
  const proc = spawn(browser, [
    '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--hide-scrollbars',
    '--window-size=1440,900',
  ], { stdio: 'ignore', windowsHide: true });
  const cleanup = () => {
    try { proc.kill(); } catch { /* gone */ }
    if (process.platform === 'win32' && proc.pid) {
      try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true }); } catch { /* gone */ }
    }
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* locked */ }
  };

  let cdp = null;
  try {
    let target = null;
    for (let i = 0; i < 100 && !target; i += 1) {
      await sleep(150);
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
        if (res.ok) target = await res.json();
      } catch { /* starting */ }
    }
    if (!target) throw new Error('browser did not expose a DevTools target');
    cdp = new CDP(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');
    await cdp.send('Network.enable');
    wireAudit(cdp);

    await cdp.send('Page.navigate', { url: WEB });
    await waitFor(cdp, `document.querySelector('[data-testid="auth-username"]') !== null`, {
      label: 'login form', timeout: 45000,
    });
    await shot(cdp, '01-login.png');
    check('E1 login: no horizontal overflow', await evaluate(cdp, 'document.documentElement.scrollWidth <= window.innerWidth + 1'),
      await evaluate(cdp, '`${document.documentElement.scrollWidth}x${window.innerWidth}`'));
    check('E1 login: form fully visible', await evaluate(cdp, `(() => {
      const el = document.querySelector('.auth-plate'); if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.width > 300 && r.left >= 0 && r.right <= window.innerWidth + 1;
    })()`));

    await type(cdp, '[data-testid="auth-username"]', USER);
    await type(cdp, '[data-testid="auth-password"]', PASS);
    await click(cdp, '[data-testid="auth-submit"]');
    await waitFor(cdp, `document.querySelector('[data-testid="nav-history"]') !== null`, { label: 'login', timeout: 30000 });
    check('D1 login succeeds with native input', true);

    await click(cdp, '[data-testid="nav-history"]');
    await waitFor(cdp, `document.querySelector('[data-testid="history-row-${RUN}"]') !== null`, { label: 'history row', timeout: 30000 });
    await sleep(800);
    await evaluate(cdp, `document.querySelector('[data-testid="history-row-${RUN}"]')?.scrollIntoView({block:'center'})`);
    await sleep(400);
    await shot(cdp, '02-history.png');

    check('E2 history: no horizontal page overflow', await evaluate(cdp, 'document.documentElement.scrollWidth <= window.innerWidth + 1'),
      await evaluate(cdp, '`${document.documentElement.scrollWidth}x${window.innerWidth}`'));
    check('E2 history: score/verdict rendered from artifacts', await evaluate(cdp, `(() => {
      const row = document.querySelector('[data-testid="history-row-${RUN}"]');
      if (!row) return false;
      const text = row.innerText;
      return /65\\.8/.test(text) && text.includes('C \\u00b7 \\u6ce2\\u52a8');
    })()`));
    check('D3 history: verdict badge tone is grade-aware (C = yellow)', await evaluate(cdp, `(() => {
      const row = document.querySelector('[data-testid="history-row-${RUN}"]');
      const badge = row?.querySelector('.verdict-badge');
      return !!badge && badge.classList.contains('badge-yellow') && !!badge.getAttribute('title');
    })()`));
    check('E2 history: table scrolls inside its wrapper', await evaluate(cdp, `(() => {
      const w = document.querySelector('.history-table-wrapper');
      return !!w && getComputedStyle(w).overflowX !== 'visible';
    })()`));

    await click(cdp, `[data-testid="history-continue-${RUN}"]`);
    await waitFor(cdp, `document.querySelector('[data-testid="run-chat-input"]') !== null`, { label: 'run view', timeout: 30000 });
    await sleep(1200);
    await shot(cdp, '03-run-view.png');
    check('D5 continue opens the run chat', true);
    check('E3 run view: chat dock visible in viewport', await evaluate(cdp, `(() => {
      const el = document.querySelector('[data-testid="run-chat-input"]');
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.top >= 0 && r.bottom <= window.innerHeight + 1 && r.width > 100;
    })()`));
    check('E3 run view: no horizontal overflow', await evaluate(cdp, 'document.documentElement.scrollWidth <= window.innerWidth + 1'));

    await click(cdp, '[data-testid="nav-history"]');
    await waitFor(cdp, `document.querySelector('[data-testid="history-row-${RUN}"]') !== null`, { label: 'history row (second pass)', timeout: 30000 });
    let reportBtnFound = true;
    try {
      await waitFor(cdp, `document.querySelector('[data-testid="history-report-${RUN}"]') !== null`, { label: 'history report button', timeout: 15000 });
    } catch (err) {
      reportBtnFound = false;
      const dbg = await evaluate(cdp, `(() => ({
        activeNav: document.querySelector('.app-nav-item.active')?.textContent?.trim() || null,
        row: !!document.querySelector('[data-testid="history-row-${RUN}"]'),
        reportBtns: document.querySelectorAll('[data-testid^="history-report-"]').length,
        continueBtns: document.querySelectorAll('[data-testid^="history-continue-"]').length,
      }))()`).catch((e) => ({ evalError: e.message }));
      check('D4 history report button present', false, JSON.stringify(dbg));
    }
    if (reportBtnFound) {
      await click(cdp, `[data-testid="history-report-${RUN}"]`);
      await waitFor(cdp, 'document.querySelector("[data-testid=\\"report-body\\"]") !== null', { label: 'report body', timeout: 45000 });
      await sleep(800);
      const reportStats = await evaluate(cdp, `(() => {
        const body = document.querySelector('[data-testid="report-body"]');
        return { len: body?.innerText?.length || 0, headings: body?.querySelectorAll('h1,h2,h3').length || 0 };
      })()`);
      check('D4 report markdown rendered', reportStats.len > 500 && reportStats.headings >= 1, JSON.stringify(reportStats));
      await shot(cdp, '04-report-md.png');
    }

    const hasHtmlTab = reportBtnFound
      && await evaluate(cdp, 'document.querySelector("[data-testid=\\"report-tab-html-0\\"]") !== null');
    if (hasHtmlTab) {
      await click(cdp, '[data-testid="report-tab-html-0"]');
      await waitFor(cdp, 'document.querySelector("[data-testid=\\"report-html-frame\\"]") !== null', { label: 'html iframe', timeout: 30000 });
      // The report HTML pulls ECharts from CDNs (with fallbacks); a blocked
      // network can delay the document. Poll instead of a fixed sleep.
      let frame = null;
      for (let i = 0; i < 60; i += 1) {
        frame = await evaluate(cdp, `(() => {
          const f = document.querySelector('[data-testid="report-html-frame"]');
          if (!f) return null;
          const r = f.getBoundingClientRect();
          let len = -1;
          let readyState = null;
          try {
            readyState = f.contentDocument?.readyState ?? null;
            len = f.contentDocument?.body?.innerText?.length ?? -1;
          } catch { len = -2; }
          return {
            w: Math.round(r.width), h: Math.round(r.height), len, readyState,
            sandbox: f.getAttribute('sandbox'),
            src: String(f.getAttribute('src') || '').slice(0, 160),
          };
        })()`);
        if (frame && frame.len > 100) break;
        await sleep(250);
      }
      check('D4/E4 HTML report iframe has content', !!frame && frame.w > 300 && frame.h > 300 && frame.len > 100, JSON.stringify(frame));
      await shot(cdp, '05-report-html.png');
    } else {
      check('D4/E4 HTML report tab present', false, 'no html tab for this run');
    }

    // Responsive pass
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 1280, height: 800, deviceScaleFactor: 1, mobile: false,
    });
    await click(cdp, '[data-testid="nav-history"]');
    await waitFor(cdp, `document.querySelector('[data-testid="history-row-${RUN}"]') !== null`, { label: 'history at 1280', timeout: 30000 });
    await sleep(600);
    await shot(cdp, '06-history-1280.png');
    check('E5 1280px: no horizontal page overflow', await evaluate(cdp, 'document.documentElement.scrollWidth <= window.innerWidth + 1'),
      await evaluate(cdp, '`${document.documentElement.scrollWidth}x${window.innerWidth}`'));
    // The outcome lanes must stay clear of the sticky action rail at 1280.
    check('E5 1280px: verdict visible beside the sticky action rail', await evaluate(cdp, `(() => {
      const row = document.querySelector('[data-testid="history-row-${RUN}"]');
      const badge = row?.querySelector('.verdict-badge');
      const actions = row?.querySelector('.cell-actions');
      if (!badge || !actions) return false;
      const v = badge.getBoundingClientRect();
      const a = actions.getBoundingClientRect();
      return v.width > 0 && v.left >= 0 && v.right <= a.left + 1 && v.right <= window.innerWidth + 1;
    })()`));

    await cdp.send('Emulation.clearDeviceMetricsOverride');

    check('D1 no uncaught page exceptions', pageExceptions.length === 0, pageExceptions.slice(0, 3).join(' | '));
    check('D1 no console errors', consoleErrors.length === 0, consoleErrors.slice(0, 5).join(' | '));
    check('D1/D6 no failed /api requests', failedApi.length === 0, failedApi.slice(0, 5).join(' | '));

    writeFileSync(join(OUT, 'audit.json'), JSON.stringify({
      run: RUN, api: API, web: WEB, at: new Date().toISOString(),
      results, consoleErrors, pageExceptions, failedApi,
    }, null, 2));
    console.log(`\n[RESULT] failures=${failures}`);
    process.exit(failures ? 1 : 0);
  } catch (err) {
    check('audit flow', false, err.message);
    writeFileSync(join(OUT, 'audit.json'), JSON.stringify({
      run: RUN, api: API, web: WEB, at: new Date().toISOString(),
      results, consoleErrors, pageExceptions, failedApi, fatal: err.message,
    }, null, 2));
    console.log(`\n[RESULT] failures=${failures}`);
    process.exit(1);
  } finally {
    if (cdp) cdp.close();
    cleanup();
  }
}

main().catch((err) => { console.error(err); process.exit(1); });
