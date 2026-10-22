#!/usr/bin/env node
// Native-input UI smoke: login → History → continue → send → reply.
//
// "Native" is the point: every click is a real CDP Input.dispatchMouseEvent and
// every keystroke is Input.insertText. No element.click(), no Vue internals, no
// DOM value assignment — the script fails if the UI only responds to synthetic
// JavaScript events. This is the regression gate for the click-timeout defect
// (element re-render churn + infinite animations) recorded in the follow-up plan.
//
// Requires the real backend and the Vite dev server:
//   node scripts/e2e/ui-smoke-native.mjs --api http://127.0.0.1:3211 --web http://127.0.0.1:5181
//
// Uses the locally installed Chrome/Edge via the DevTools Protocol; no extra npm
// dependency. CHROME_PATH overrides binary discovery.
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
const API = opt('api', 'http://127.0.0.1:3211').replace(/\/$/, '');
const WEB = opt('web', 'http://127.0.0.1:5181').replace(/\/$/, '');
const KEEP = args.includes('--keep');

let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (!ok) failures += 1;
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
    : process.platform === 'darwin'
      ? [
          '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
          '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        ]
      : ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge'];
  return candidates.find((p) => existsSync(p)) || null;
}

// ── minimal DevTools Protocol client ─────────────────────────────────────
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
      if (msg.method) {
        for (const fn of this.listeners.get(msg.method) || []) fn(msg.params);
      }
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

  on(method, fn) {
    if (!this.listeners.has(method)) this.listeners.set(method, []);
    this.listeners.get(method).push(fn);
  }

  close() {
    try { this.ws.close(); } catch { /* already closed */ }
  }
}

async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text || 'evaluate failed');
  return result?.value;
}

async function waitFor(cdp, expression, { timeout = 30000, label = expression } = {}) {
  const deadline = Date.now() + timeout;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const ok = await evaluate(cdp, expression);
      if (ok) return true;
    } catch (err) {
      lastErr = err;
    }
    await sleep(150);
  }
  throw new Error(`waitFor timeout: ${label}${lastErr ? ` (${lastErr.message})` : ''}`);
}

function selectorExpr(selector) {
  return `document.querySelector(${JSON.stringify(selector)})`;
}

async function elementCenter(cdp, selector) {
  const rect = await evaluate(cdp, `(() => {
    const el = ${selectorExpr(selector)};
    if (!el) return null;
    el.scrollIntoView({ block: 'center', inline: 'center' });
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
  })()`);
  if (!rect) throw new Error(`element not visible: ${selector}`);
  return rect;
}

/** A real mouse click (pointer events + focus), not element.click(). */
async function nativeClick(cdp, selector) {
  const { x, y } = await elementCenter(cdp, selector);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1,
  });
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1,
  });
}

/** Focus + real text insertion (fires the same input events as typing). */
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

async function main() {
  const browser = findBrowser();
  if (!browser) {
    console.error('no Chrome/Edge found — set CHROME_PATH');
    process.exit(2);
  }
  const health = await apiJson('/api/health').catch(() => null);
  if (!health || health.status !== 200) {
    console.error(`backend not healthy at ${API} — start it first`);
    process.exit(2);
  }
  const webProbe = await fetch(`${WEB}/`).catch(() => null);
  if (!webProbe || !webProbe.ok) {
    console.error(`frontend not reachable at ${WEB} — start it first`);
    process.exit(2);
  }

  const username = `uismoke_${Date.now().toString(36)}`;
  const password = 'Smoke12345';
  const reg = await apiJson('/api/auth/register', { method: 'POST', body: { username, password } });
  if (reg.status !== 200) {
    check('register smoke user', false, JSON.stringify(reg.json).slice(0, 200));
    process.exit(1);
  }
  check('register smoke user', true, username);
  const token = reg.json.data.session_token;

  // A completed mock run owned by this user: History must offer Continue.
  const started = await apiJson('/api/diagnosis/start', {
    method: 'POST',
    token,
    body: {
      harness: 'mock',
      dataPath: 'data/smoke.csv',
      sceneName: 'ui_native_smoke',
      userQuestion: 'native input smoke',
      reportLanguage: 'zh',
    },
  });
  if (started.status !== 200) {
    check('create mock run', false, JSON.stringify(started.json).slice(0, 200));
    process.exit(1);
  }
  const runId = started.json.data.runId;
  await apiJson(`/api/diagnosis/execute/${runId}`, { method: 'POST', token });
  check('create mock run', true, runId);

  let runStatus = null;
  for (let i = 0; i < 100; i += 1) {
    const s = await apiJson(`/api/diagnosis/status/${runId}`, { token });
    runStatus = s.json?.data?.status;
    if (runStatus === 'completed' || runStatus === 'failed') break;
    await sleep(200);
  }
  check('mock run completes', runStatus === 'completed', String(runStatus));

  const port = await freePort();
  const profile = mkdtempSync(join(tmpdir(), 'idd-ui-smoke-'));
  const proc = spawn(browser, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--hide-scrollbars',
    '--window-size=1440,900',
  ], { stdio: 'ignore', windowsHide: true });

  const cleanup = () => {
    try { proc.kill(); } catch { /* gone */ }
    if (process.platform === 'win32' && proc.pid) {
      try { spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true }); } catch { /* gone */ }
    }
    if (!KEEP) {
      try { rmSync(profile, { recursive: true, force: true }); } catch { /* locked */ }
    }
  };

  let cdp = null;
  try {
    let target = null;
    for (let i = 0; i < 100 && !target; i += 1) {
      await sleep(150);
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
        if (res.ok) target = await res.json();
      } catch { /* browser not up yet */ }
    }
    if (!target) throw new Error('browser did not expose a DevTools target');
    cdp = new CDP(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');

    await cdp.send('Page.navigate', { url: WEB });
    await waitFor(cdp, `document.querySelector('[data-testid="auth-username"]') !== null`, {
      label: 'login form rendered', timeout: 45000,
    });
    check('login form rendered', true);

    // Reduced-motion contract: decorative loops must stop when the OS asks.
    await cdp.send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
    });
    const animDuration = await evaluate(cdp, `(() => {
      const el = document.querySelector('.auth-rail-dot');
      return el ? getComputedStyle(el).animationDuration : null;
    })()`);
    check('reduced-motion stops decorative animation', parseFloat(animDuration) < 0.01, animDuration);
    await cdp.send('Emulation.setEmulatedMedia', { features: [] });

    await nativeType(cdp, '[data-testid="auth-username"]', username);
    await nativeType(cdp, '[data-testid="auth-password"]', password);
    const typed = await evaluate(cdp, `document.querySelector('[data-testid="auth-username"]').value`);
    check('native keystrokes reach the form', typed === username, typed);

    await nativeClick(cdp, '[data-testid="auth-submit"]');
    await waitFor(cdp, `document.querySelector('[data-testid="nav-history"]') !== null`, {
      label: 'login accepted', timeout: 30000,
    });
    check('native click submits login', true);

    await nativeClick(cdp, '[data-testid="nav-history"]');
    await waitFor(cdp, `document.querySelector('[data-testid="history-row-${runId}"]') !== null`, {
      label: 'history row for smoke run', timeout: 30000,
    });
    check('native click opens History', true);

    await nativeClick(cdp, `[data-testid="history-continue-${runId}"]`);
    await waitFor(cdp, `document.querySelector('[data-testid="run-chat-input"]') !== null`, {
      label: 'chat input after Continue', timeout: 30000,
    });
    check('native click opens the run chat', true);

    const message = `native smoke ${Date.now().toString(36)}`;
    await nativeType(cdp, '[data-testid="run-chat-input"]', message);
    const chatTyped = await evaluate(cdp, `document.querySelector('[data-testid="run-chat-input"]').value`);
    check('native keystrokes reach the chat input', chatTyped === message, chatTyped);

    await nativeClick(cdp, '[data-testid="run-chat-send"]');
    await waitFor(cdp, `document.body.innerText.includes('(mock) 已收到消息')`, {
      label: 'assistant reply rendered', timeout: 30000,
    });
    const pageText = await evaluate(cdp, 'document.body.innerText');
    check('reply is rendered in the live view', pageText.includes('(mock) 已收到消息'));
    check('reply echoes the native-typed message', pageText.includes(message));

    // Registration path (not exercised by the login-only flow above): log out,
    // register a fresh user through the form, and confirm auto-login.
    await nativeClick(cdp, '[data-testid="logout"]');
    await waitFor(cdp, `document.querySelector('[data-testid="auth-tab-register"]') !== null`, {
      label: 'auth form after logout', timeout: 20000,
    });
    check('logout returns to the auth form', true);

    const regUser = `uireg_${Date.now().toString(36)}`;
    await nativeClick(cdp, '[data-testid="auth-tab-register"]');
    await nativeType(cdp, '[data-testid="auth-username"]', regUser);
    await nativeType(cdp, '[data-testid="auth-password"]', password);
    await nativeClick(cdp, '[data-testid="auth-submit"]');
    await waitFor(cdp, `document.querySelector('[data-testid="nav-history"]') !== null`, {
      label: 'registration auto-login', timeout: 30000,
    });
    const regText = await evaluate(cdp, 'document.body.innerText');
    check('native registration auto-logs in', regText.includes(regUser));

    await nativeClick(cdp, '[data-testid="logout"]');
    await waitFor(cdp, `document.querySelector('[data-testid="auth-username"]') !== null`, {
      label: 'auth form after registered-user logout', timeout: 20000,
    });
    check('registered user can log out', true);
  } catch (err) {
    check('native UI flow', false, err.message);
  } finally {
    if (cdp) cdp.close();
    cleanup();
  }

  console.log(`\n[RESULT] failures=${failures}`);
  process.exit(failures ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
