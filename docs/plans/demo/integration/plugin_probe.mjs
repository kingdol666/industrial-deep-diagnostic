#!/usr/bin/env node
/**
 * AgentWorkShop plugin ⇄ IDD integration probe (real HTTP, real plugin code).
 *
 * Loads the builtin diag-bridge plugin and the project idd-closedloop-bridge
 * plugin with a minimal OMP-like ctx, then:
 *   1. diag_run(analysis_intent=doe-analysis, no explicit question) → IDD task
 *   2. diag_status poll → completion text
 *   3. GET /api/history/runs/:id → what question/intent actually reached IDD
 *   4. sentinel_screen → the closedloop bridge's endpoint family
 *
 * Usage: node plugin_probe.mjs [--base http://127.0.0.1:3211] [--token-file ...]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { join, resolve } from 'node:path';

const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const REPO = resolve(HERE, '../../../..');
const AWS = 'D:/codes/ABO/AgentWorkShop';
const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : dflt;
};
const BASE = arg('--base', 'http://127.0.0.1:3211');
const TOKEN = readFileSync(arg('--token-file', join(REPO, 'workspace/aws-capture-e2e/token.txt')), 'utf8').trim();
const DATA = 'workspace/doe-generality/heat_treat_ccd/00_input/run_table.csv';

function fakeCtx(config, tools) {
  const kv = new Map();
  return {
    config: {
      get: (k) => config[k],
      defineGroup: () => {},
      defineField: () => {},
    },
    kv: {
      get: (k) => kv.get(k),
      set: (k, v) => { kv.set(k, v); },
      all: () => Object.fromEntries(kv),
    },
    http: {
      get: async (url, opt) => {
        const r = await fetch(url, { method: 'GET', headers: opt?.headers });
        return { ok: r.ok, status: r.status, json: () => r.json() };
      },
      post: async (url, body, opt) => {
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'content-type': 'application/json', ...(opt?.headers || {}) },
          body: JSON.stringify(body),
        });
        return { ok: r.ok, status: r.status, json: () => r.json() };
      },
    },
    logger: { info: () => {}, warn: () => {}, error: () => {} },
    omp: { registerTool: (t) => { tools.set(t.name, t); } },
    timer: { setInterval: () => 0 },
    hooks: { on: () => {} },
    route: () => {},
    services: { get: async () => null },
    daq: {},
    cwd: REPO,
  };
}

const out = { base: BASE, data_path: DATA, checks: {} };
try {
  const diagMod = await import(pathToFileURL(join(AWS, 'server/plugins-builtin/diag-bridge/index.mjs')).href);
  const diagTools = new Map();
  const diagCtx = fakeCtx({
    'plugins.diag-bridge.base_url': BASE,
    'plugins.diag-bridge.token': TOKEN,
    'plugins.diag-bridge.harness': 'mock',
  }, diagTools);
  diagMod.default.setup(diagCtx);
  out.checks.diag_tools = [...diagTools.keys()];
  out.checks.diag_plugin_loaded = true;

  const run = await diagTools.get('diag_run').handler({
    data_path: DATA,
    analysis_intent: 'doe-analysis',
    harness: 'mock',
    mode: 'async',
  }, { agentId: 'probe', channelId: 'probe' });
  out.checks.diag_run_text = run?.text ?? String(run);
  const m = String(out.checks.diag_run_text).match(/task_id=([^\s()]+)/);
  const runId = m?.[1] || null;
  out.checks.run_id = runId;

  if (runId) {
    let last = null;
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      last = await diagTools.get('diag_status').handler({ run_id: runId });
      if (/completed|完成|失败/.test(String(last?.text ?? ''))) break;
    }
    out.checks.diag_status_text = last?.text ?? String(last);
    const hist = await fetch(`${BASE}/api/history/runs/${runId}`, {
      headers: { authorization: `Bearer ${TOKEN}` },
    }).then((r) => r.json()).catch(() => null);
    out.checks.id_history = hist?.success === true;
    out.checks.stored_intent = hist?.data?.analysis_intent ?? null;
    out.checks.stored_question = hist?.data?.user_question ?? null;
    out.checks.question_is_doe = /DOE|试验/.test(String(out.checks.stored_question || ''));
    out.checks.question_is_deep_diagnosis =
      /根因诊断/.test(String(out.checks.stored_question || ''));
  }
} catch (e) {
  out.checks.diag_plugin_loaded = false;
  out.checks.diag_error = `${e.name}: ${e.message}`;
}

try {
  const closedMod = await import(pathToFileURL(join(AWS, '.AgentWorkShop/plugins/idd-closedloop-bridge/index.mjs')).href);
  const closedTools = new Map();
  const closedCtx = fakeCtx({
    'plugins.idd-closedloop-bridge.base_url': BASE,
    'plugins.idd-closedloop-bridge.token': TOKEN,
  }, closedTools);
  closedMod.default.setup(closedCtx);
  out.checks.closedloop_tools = [...closedTools.keys()];
  out.checks.closedloop_plugin_loaded = true;
  const screen = await closedTools.get('sentinel_screen').handler({ data_path: DATA });
  out.checks.sentinel_screen_text = screen?.text
    ?? (typeof screen === 'string' ? screen : JSON.stringify(screen));
  out.checks.sentinel_screen_failed = /失败|404|Cannot POST|error/i.test(
    String(out.checks.sentinel_screen_text));
} catch (e) {
  out.checks.closedloop_plugin_loaded = false;
  out.checks.closedloop_error = `${e.name}: ${e.message}`;
}

writeFileSync(join(HERE, 'plugin_probe.json'),
  JSON.stringify(out, null, 2), 'utf8');
console.log(JSON.stringify(out, null, 2));
process.exitCode = out.checks.diag_plugin_loaded && out.checks.id_history ? 0 : 1;
// Let keep-alive sockets close naturally; process.exit() during an open fetch
// socket trips a libuv assertion on Windows (UV_HANDLE_CLOSING).
