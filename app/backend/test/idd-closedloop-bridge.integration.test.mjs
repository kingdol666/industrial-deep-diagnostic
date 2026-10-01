// AWS 插件层集成测试 — Workstream D 两级测试之第二级。
//
// 动态 import AgentWorkShop 的 `idd-closedloop-bridge` 插件（真实 handler），
// 用 mocked ctx（config.get / kv 内存 Map / logger / timer / omp.registerTool
// 捕获工具表）调 setup(ctx)，然后逐个真实调用工具 handler，打在同一个真实
// IDD 后端（127.0.0.1 绑定，满足 helpers.baseOf 的域校验）：
//
//   sentinel_screen(exit2)→(建档)→sentinel_screen(告警)→sentinel_watch→
//   sentinel_status → experience_log → experience_recommend →
//   experience_feedback → optimizer_campaign → optimizer_round(design)→
//   (ingest) → optimizer_state
//
// 断言每个工具返回文本含关键标识（task_id / 推荐 status / 布点 trial_id 等）；
// 最后手动驱动一次插件 15s sweep，验证 KV 任务跟踪到终态。
// 数据集注册（experience 归因所需的 data.csv+metric）通过同一后端的
// POST /api/experience/actions 直接完成——插件 experience_log 不携带数据，
// 服务端按最近注册数据集继承（契约语义），本测试同时验证该继承。

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { mkdtempSync, mkdirSync, rmSync, readFileSync, existsSync } from 'fs';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const PORT = 3992;
const BASE = `http://127.0.0.1:${PORT}`;
const DB_PATH = join(mkdtempSync(join(tmpdir(), 'idd-aws-bridge-')), 'e2e.db');
const CL_ROOT = join(repoRoot, 'workspace', `.closedloop-aws-test-${process.pid}`);
const FX = join(here, 'fixtures', 'closedloop');
const PLUGIN_PATH = 'D:\\codes\\ABO\\AgentWorkShop\\.AgentWorkShop\\plugins\\idd-closedloop-bridge\\index.mjs';

let server;
let serverLog = '';
let tools = {};          // omp.registerTool 捕获的工具表
let sweepFn = null;      // timer.setInterval 捕获的 sweep
let campaignId = null;   // optimizer_campaign 文本捕获的 campaign id
const kvStore = new Map();

const ctx = {
  config: {
    get(key) {
      if (key === 'plugins.idd-closedloop-bridge.base_url') return BASE;
      if (key === 'plugins.idd-closedloop-bridge.token') return '';
      return undefined;
    },
  },
  kv: {
    get: (k) => kvStore.get(k),
    set: (k, v) => kvStore.set(k, v),
  },
  logger: {
    info: (...a) => console.log('[plugin]', ...a),
    warn: (...a) => console.warn('[plugin:warn]', ...a),
    error: (...a) => console.error('[plugin:err]', ...a),
  },
  timer: { setInterval: (fn, _ms) => { sweepFn = fn; return 1; } },
  omp: { registerTool: (t) => { tools[t.name] = t; } },
};

async function req(method, path, { body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  return { status: res.status, body: json };
}

async function pollUntil(fn, { timeoutMs = 100000, intervalMs = 1000, label = 'task' } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    last = await fn();
    if (last?.done) return last.value;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`${label} not done after ${timeoutMs}ms: ${String(last?.value).slice(0, 300)}`);
}

before(async () => {
  mkdirSync(CL_ROOT, { recursive: true });
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(PORT),
      SERVER_PORT: String(PORT),
      AUTH_ENABLED: '0',
      DATABASE_PATH: DB_PATH,
      CLOSEDLOOP_DATA_DIR: CL_ROOT,
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  // waitHealthy
  const deadline = Date.now() + 40000;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) break;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 400));
  }

  // 动态 import 插件（真实 handler），setup 挂工具
  const plugin = (await import(pathToFileURL(PLUGIN_PATH).href)).default;
  assert.equal(plugin.name, 'idd-closedloop-bridge');
  plugin.setup(ctx);
  for (const name of ['sentinel_screen', 'sentinel_watch', 'sentinel_status', 'sentinel_baseline',
    'experience_log', 'experience_recommend', 'experience_feedback',
    'optimizer_campaign', 'optimizer_round', 'optimizer_state']) {
    assert.ok(tools[name], `tool ${name} registered`);
  }
});

after(async () => {
  if (server) { server.kill(); server = null; }
  try { rmSync(CL_ROOT, { recursive: true, force: true }); } catch { /* ignore */ }
  try { rmSync(DB_PATH, { force: true }); } catch { /* ignore */ }
});

// ───────────────────────────── 哨兵 ──────────────────────────────────────

describe('idd-closedloop-bridge 工具 handler → 真实 IDD 后端', () => {
  test('sentinel_screen 无基线 → exit=2 指引建档文本', async () => {
    const out = await tools.sentinel_screen.handler({ data_path: join(FX, 'sentinel_fast_alert.csv') });
    assert.match(out.text, /无法判定/);
    assert.match(out.text, /sentinel_baseline/);
  });

  test('sentinel_screen 建档后（显式 baseline_path）→ 告警文本', { timeout: 120000 }, async () => {
    const sub = await req('POST', '/api/sentinel/baseline', {
      body: { line: 'AWS-LINE-A', history_csv: join(FX, 'sentinel_history.csv'), time_col: 't' },
    });
    assert.equal(sub.status, 200);
    await pollUntil(async () => {
      const v = await req('GET', `/api/sentinel/tasks/${sub.body.data.task_id}`);
      return { done: v.body?.data?.status === 'completed', value: v.body?.data?.status };
    }, { label: 'baseline' });

    const out = await tools.sentinel_screen.handler({
      data_path: join(FX, 'sentinel_fast_alert.csv'),
      baseline_path: join(CL_ROOT, 'sentinel', 'baselines', 'AWS-LINE-A', 'watch_baseline.json'),
    });
    assert.match(out.text, /筛查完成:发现 \d+ 条告警/);
    assert.match(out.text, /status=alert/);
  });

  test('sentinel_watch 提交即返 task_id → sentinel_status 取告警与报告路径', { timeout: 180000 }, async () => {
    const submit = await tools.sentinel_watch.handler({
      data_path: join(FX, 'sentinel_watch_alert.csv'),
      baseline_path: join(CL_ROOT, 'sentinel', 'baselines', 'AWS-LINE-A', 'watch_baseline.json'),
      time_col: 't',
    });
    assert.match(submit.text, /task_id=(SNW-[A-Za-z0-9-]+)/);
    const taskId = /task_id=(SNW-[A-Za-z0-9-]+)/.exec(submit.text)[1];

    const statusText = await pollUntil(async () => {
      const out = await tools.sentinel_status.handler({ task_id: taskId });
      return { done: /状态=completed/.test(out.text), value: out.text };
    }, { label: 'sentinel_status' });
    assert.match(statusText, /告警 \d+ 条/);
    assert.match(statusText, /watch_report\.md/);
    assert.match(statusText, /alert\.json/);
    const runs = kvStore.get('idd_closedloop_runs') ?? [];
    assert.ok(runs.some((r) => r.id === taskId && r.kind === 'sentinel_watch'),
      'plugin KV tracks the submitted watch task');
  });
});

// ────────────────────────── 调优经验库 ───────────────────────────────────

describe('experience 工具链：log → recommend → feedback', () => {
  test('数据集注册（直接 API，归因 job 完成 estimable）', { timeout: 180000 }, async () => {
    const ing = await req('POST', '/api/experience/actions', {
      body: {
        action_log: {
          schema_version: '1.0',
          action_log_id: '20260301_aws00001',
          ts: '2026-01-15T00:05:00Z',
          actor: { actor_id: 'aws_agent', actor_type: 'control_system' },
          actions: [{ parameter: 'temp', from: 50.0, to: 55.0, unit: 'degC' }],
          context: { product: 'P1', machine: 'M1', regime_label: 'R1' },
          trigger: { trigger_type: 'manual' },
          attribution_confounds: [],
          recommendation_ref: null,
          ingest_meta: { source: 'api' },
        },
        data_path: join(FX, 'experience_data.csv'),
        metric: 'y',
        time_col: 't',
      },
    });
    assert.equal(ing.status, 200);
    const jobId = ing.body.data.attribution_job_id;
    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/experience/attribution/${jobId}`);
      return { done: ['completed', 'failed'].includes(v.body?.data?.status), value: v.body?.data?.status };
    }, { label: 'attribution' });
    assert.equal(done, 'completed');
  });

  test('experience_log（插件 payload：无数据字段，继承已注册数据集）→ 归因任务文本', { timeout: 180000 }, async () => {
    const out = await tools.experience_log.handler({
      actions: [{ parameter: 'temp', from: 55.0, to: 52.0, unit: 'degC' }],
      ts: '2026-01-15T00:08:00Z',
      product: 'P1',
      machine: 'M1',
      trigger_alert_id: 'ALT-20261001-000',
      confounds: 'none',
    });
    assert.match(out.text, /动作已登记 id=(\S+)\(归因任务 (attr-\S+),异步执行\)/);
    const jobId = /归因任务 (attr-\S+),/.exec(out.text)[1];
    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/experience/attribution/${jobId}`);
      return { done: ['completed', 'failed'].includes(v.body?.data?.status), value: v.body?.data };
    }, { label: 'plugin experience_log attribution' });
    assert.equal(done.status, 'completed', JSON.stringify(done).slice(0, 400));
    assert.ok(existsSync(join(CL_ROOT, 'experience', 'library', '06_experience', 'attribution', `${done.action_log_ids[0]}.json`)));
  });

  test('experience_recommend → playbook_hit + recommendation_id 文本', async () => {
    const out = await tools.experience_recommend.handler({
      anomalous_params: [{ parameter: 'temp', direction: 'high' }],
      product: 'P1',
      machine: 'M1',
      regime_label: 'R1',
      degraded_metric: 'y',
    });
    assert.match(out.text, /推荐 status=playbook_hit match_scope=regime recommendation_id=(REC-\S+?)。/);
    assert.match(out.text, /\[E\d\/[^\]]*\]/); // evidence_grade/autonomy 载体
    assert.match(out.text, /experience_log\(带 recommendation_id=/); // 回执链指引
  });

  test('experience_feedback → 佐证计数文本（E2 晋升）', async () => {
    const storePath = join(CL_ROOT, 'experience', 'library', '06_experience', 'tuning_experience.jsonl');
    // 挑直连摄取的那条（regime R1、E1 可晋升）；插件的 00:08 动作落在前一动
    // 作的效果窗内（overlapping_action → E0 锁定），不是晋升对象
    const lines = readFileSync(storePath, 'utf-8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
    const target = lines.find((e) => String(e.chunk_id).includes('P1|M1|R1') && e.evidence_grade === 'E1')
      ?? lines.find((e) => String(e.chunk_id).includes('P1|M1|R1'));
    assert.ok(target, `store lines: ${lines.map((e) => e.chunk_id).join(', ')}`);
    const out = await tools.experience_feedback.handler({
      experience_id: target.chunk_id,
      result: 'effective',
      note: 'aws integration',
    });
    assert.match(out.text, /反馈已记录/);
    assert.match(out.text, /"corroboration":\s*2/);
    assert.match(out.text, /"evidence_grade":\s*"E2"/);
  });
});

// ────────────────────────── 目标闭环寻优 ─────────────────────────────────

describe('optimizer 工具链：campaign → round(design→ingest) → state', () => {
  test('optimizer_campaign（goal=target + 安全限）→ 已创建文本', { timeout: 120000 }, async () => {
    const out = await tools.optimizer_campaign.handler({
      target_metric: 'brix',
      goal: 'target',
      target_low: 1.52,
      target_high: 1.56,
      factors: [{ name: 'temp', type: 'numeric', min: 140, max: 180, unit: 'degC' }],
      constraints: JSON.stringify([{ factor: 'temp', min: 140, max: 180, type: 'safety', hard: true }]),
      max_rounds: 12,
    });
    const m = /campaign (OPT-\d{8}-\d+) 已创建\(phase=initialized\)/.exec(out.text);
    assert.ok(m, out.text);
    campaignId = m[1];
  });

  test('optimizer_round design → 布点 trial_id 文本；ingest → 状态转移文本', { timeout: 180000 }, async () => {
    assert.ok(campaignId, 'campaign created by the previous test');
    const design = await tools.optimizer_round.handler({ campaign_id: campaignId, action: 'design' });
    assert.match(design.text, /R 轮布点\(phase=\w+, method=\w+\)剩预算/);
    assert.match(design.text, /R001-T01/);
    assert.match(design.text, /trial_result 回收/);

    // 从布点文本解析 trial_id，构造 trial_result（插件 ingest payload 形状）
    const trialIds = [...design.text.matchAll(/- (R001-T\d+):/g)].map((m) => m[1]);
    assert.ok(trialIds.length >= 1);
    const ingest = await tools.optimizer_round.handler({
      campaign_id: campaignId,
      action: 'ingest',
      trial_result: {
        result_version: '1.0',
        campaign_id: campaignId,
        round_id: 'R001',
        trials: trialIds.map((id) => ({
          trial_id: id,
          status: 'completed',
          measurements: { brix: [1.541, 1.539, 1.543] },
          measured_at: '2026-10-01T00:00:00Z',
        })),
        ingest_meta: { source: 'api' },
      },
    });
    assert.match(ingest.text, /结果已回收:phase=(\w+) 转移=/);
  });

  test('optimizer_state → phase/rounds/trials/incumbent/next 文本', async () => {
    const out = await tools.optimizer_state.handler({ campaign_id: campaignId });
    assert.match(out.text, new RegExp(`campaign ${campaignId}: phase=\\w+ rounds=1 trials=\\d+`));
    assert.match(out.text, /next=\w/);
    assert.match(out.text, /budget=/);
  });

  test('插件 sweep 驱动一次 → KV 任务全部到终态', { timeout: 60000 }, async () => {
    assert.ok(sweepFn, 'sweep captured from timer.setInterval');
    await sweepFn();
    const runs = kvStore.get('idd_closedloop_runs') ?? [];
    assert.ok(runs.length >= 2, `watch + experience tasks tracked: ${JSON.stringify(runs).slice(0, 200)}`);
    for (const r of runs) {
      const doneEntry = kvStore.get(`iddcl:${r.id}`);
      assert.ok(doneEntry, `run ${r.id} (${r.kind}) has a done KV entry`);
      assert.equal(doneEntry.meta.status, 'completed');
      assert.ok(doneEntry.meta.result, 'done entry carries the result payload');
    }
  });
});
