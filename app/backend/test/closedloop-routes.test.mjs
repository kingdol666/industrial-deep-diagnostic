// Closed-loop trio routes HTTP e2e — Workstream D 集成层离线独立测试。
//
// 起真实 IDD 后端（AUTH_ENABLED=0），走真实 HTTP 打三组路由，底下是三个 skill
// 的真实 CLI 子进程（sentinel.py / sentinel_fast.py / build_baseline.py /
// tune_stats.py / experience_build.mjs / match_playbook.mjs / optimizer.py）：
//
//   sentinel : screen 无基线 exit 2 → 建基线 → screen 正例 exit 1 / 干净窗
//              exit 0 → watch 提交→轮询→完成
//   experience: 非法 payload 400 → 合法动作摄取→归因 job 完成 → recommend 命中
//               /无命中降级 → feedback 佐证计数 → 幂等重放
//   optimizer : campaign 创建（O-G1 400 路径）→ design 取布点 → 构造
//               trial_result ingest → 循环至 converged → state 查询 →
//               pause/resume 控制面
//
// 全部断言打在真实响应上；数据根目录指到本测试专属的仓库内目录
// （skill 脚本有 repo-root 路径白名单，测试目录必须位于仓库根之内）。

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync, mkdirSync, rmSync, existsSync } from 'fs';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const PORT = 3991;
const BASE = `http://127.0.0.1:${PORT}`;
const DB_PATH = join(mkdtempSync(join(tmpdir(), 'idd-closedloop-api-')), 'e2e.db');
// 仓库内隔离数据根（不用 workspace/closedloop 默认值，避免污染常驻目录）
const CL_ROOT = join(repoRoot, 'workspace', `.closedloop-test-${process.pid}`);
const FX = join(here, 'fixtures', 'closedloop');

let server;
let serverLog = '';

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-4000)}`);
}

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

/** 轮询异步任务直到 predicate 为真（sentinel watch / 归因 job 都是秒级）。 */
async function pollUntil(fn, { timeoutMs = 140000, intervalMs = 1200, label = 'task' } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    last = await fn();
    if (last?.done) return last.value;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`${label} not done after ${timeoutMs}ms: ${JSON.stringify(last?.value)?.slice(0, 500)}`);
}

/** optimizer objective 工厂（两个 describe 共用）。 */
const optObjective = (campaignId) => ({
  contract_version: '1.0',
  campaign_id: campaignId,
  target_metric: 'brix',
  goal: 'target',
  target_range: [1.52, 1.56],
  factors: [{ name: 'temp', type: 'numeric', min: 140, max: 180, unit: 'degC' }],
  constraints: [{ factor: 'temp', min: 140, max: 180, type: 'safety', hard: true }],
  budget: { max_rounds: 12, max_trials: 60 },
  seed: 42,
});

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
  await waitHealthy();
});

after(async () => {
  if (server) { server.kill(); server = null; }
  try { rmSync(CL_ROOT, { recursive: true, force: true }); } catch { /* ignore */ }
  try { rmSync(DB_PATH, { force: true }); } catch { /* ignore */ }
});

// ─────────────────────────── sentinel ────────────────────────────────────

describe('sentinel routes — 真实 CLI（build_baseline / sentinel_fast / watch）', () => {
  test('screen 无已登记基线 → 200 + exit_code=2（undetermined，不 spawn）', async () => {
    const r = await req('POST', '/api/sentinel/screen', {
      body: { data_path: join(FX, 'sentinel_fast_alert.csv') },
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.success, true);
    assert.equal(r.body.data.exit_code, 2);
    assert.equal(r.body.data.status, 'undetermined');
    assert.match(r.body.data.message, /baseline/i);
  });

  test('screen 非法 data_path → 400', async () => {
    const r = await req('POST', '/api/sentinel/screen', {
      body: { data_path: join(FX, 'no_such_file.csv') },
    });
    assert.equal(r.status, 400);
    assert.equal(r.body.success, false);
  });

  test('POST /baseline 异步建档 → 完成 + 登记生效', { timeout: 150000 }, async () => {
    const r = await req('POST', '/api/sentinel/baseline', {
      body: { line: 'PG31DS-test', history_csv: join(FX, 'sentinel_history.csv'), time_col: 't' },
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.success, true);
    const taskId = r.body.data.task_id;
    assert.ok(taskId);

    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/sentinel/tasks/${taskId}`);
      return { done: v.body?.data?.status === 'completed', value: v.body?.data };
    }, { label: 'baseline task' });
    assert.equal(done.exit_code, 0);
    assert.ok(done.baseline_path && existsSync(done.baseline_path), 'watch_baseline.json written');

    const reg = await req('GET', '/api/sentinel/baselines');
    assert.equal(reg.body.data.lines['PG31DS-test']?.line ?? 'PG31DS-test', 'PG31DS-test');
    assert.ok(reg.body.data.lines['PG31DS-test']);
  });

  test('screen 正例（异常窗，缺省基线回落登记表）→ exit_code=1 + high 告警', async () => {
    const r = await req('POST', '/api/sentinel/screen', {
      body: { data_path: join(FX, 'sentinel_fast_alert.csv') },
    });
    assert.equal(r.status, 200);
    const d = r.body.data;
    assert.equal(d.exit_code, 1);
    assert.ok(['alert', 'warn'].includes(d.alert_status));
    assert.ok(d.n_alerts > 0, `expect alerts, got ${JSON.stringify(d).slice(0, 300)}`);
    assert.ok(d.alerts.some((a) => ['high', 'critical'].includes(a.severity)));
    assert.ok(d.alert_path && existsSync(d.alert_path));
  });

  test('screen 干净窗（独立产线基线 PG31DS-B）→ exit_code=0 无告警', { timeout: 120000 }, async () => {
    // fast-screen 的 ring state 按基线文件派生并在调用间连续（哨兵防风暴语义：
    // 前一批 58 度异常行仍在 ring/抑制窗口内会持续告警）。干净窗用第二条产线
    // 基线 → 独立 state → 纯净判定；同时覆盖多产线登记与缺省回落。
    const reg = await req('POST', '/api/sentinel/baseline', {
      body: { line: 'PG31DS-B', history_csv: join(FX, 'sentinel_history.csv'), time_col: 't' },
    });
    assert.equal(reg.status, 200);
    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/sentinel/tasks/${reg.body.data.task_id}`);
      return { done: v.body?.data?.status === 'completed', value: v.body?.data };
    }, { label: 'baseline B task' });
    assert.ok(done.baseline_path);

    const r = await req('POST', '/api/sentinel/screen', {
      body: { data_path: join(FX, 'sentinel_fast_clean.csv') },
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.exit_code, 0, JSON.stringify(r.body.data).slice(0, 400));
    assert.equal(r.body.data.alert_status, 'ok');
    assert.equal(r.body.data.n_alerts, 0);
  });

  test('watch 批筛 提交→轮询→完成（exit 1 + alert.json/watch_report.md）', { timeout: 200000 }, async () => {
    const r = await req('POST', '/api/sentinel/tasks', {
      body: { data_path: join(FX, 'sentinel_watch_alert.csv'), time_col: 't' },
    });
    assert.equal(r.status, 200);
    const taskId = r.body.data.task_id;
    assert.ok(taskId);

    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/sentinel/tasks/${taskId}`);
      const s = v.body?.data?.status;
      return { done: s === 'completed' || s === 'failed', value: v.body?.data };
    }, { label: 'watch task' });
    assert.equal(done.status, 'completed');
    assert.equal(done.exit_code, 1, JSON.stringify(done).slice(0, 400));
    assert.ok(done.n_alerts > 0);
    assert.ok(done.alert_path && existsSync(done.alert_path));
    assert.ok(done.report_path && existsSync(done.report_path));
    assert.ok(done.alerts.some((a) => ['high', 'critical'].includes(a.severity)));
  });

  test('watch 缺 data_path → 400；未知 task → 404', async () => {
    const bad = await req('POST', '/api/sentinel/tasks', { body: {} });
    assert.equal(bad.status, 400);
    const nf = await req('GET', '/api/sentinel/tasks/SNW-nonexistent');
    assert.equal(nf.status, 404);
  });
});

// ─────────────────────────── experience ─────────────────────────────────

describe('experience routes — 真实 CLI（tune_stats / experience_build / match_playbook）', () => {
  const ACTION_LOG = {
    schema_version: '1.0',
    action_log_id: '20260301_e2e00001',
    ts: '2026-01-15T00:05:00Z',
    actor: { actor_id: 'aws_agent', actor_type: 'control_system' },
    actions: [{ parameter: 'temp', from: 50.0, to: 55.0, unit: 'degC' }],
    context: { product: 'P1', machine: 'M1', regime_label: 'R1' },
    trigger: { trigger_type: 'manual' },
    attribution_confounds: [],
    recommendation_ref: null,
    ingest_meta: { source: 'api' },
  };

  test('非法 payload → 400（schema 校验，缺 actions / actor_type 非法）', async () => {
    const missingActions = await req('POST', '/api/experience/actions', {
      body: { action_log: { schema_version: '1.0', ts: '2026-01-15T00:05:00Z', actor: { actor_id: 'x', actor_type: 'engineer' }, actions: [] } },
    });
    assert.equal(missingActions.status, 400);
    assert.match(missingActions.body.error, /schema validation failed/);

    const badActor = await req('POST', '/api/experience/actions', {
      body: { action_log: { ...ACTION_LOG, actor: { actor_id: 'x', actor_type: 'wizard' } } },
    });
    assert.equal(badActor.status, 400);
    assert.match(badActor.body.error, /actor_type/);

    const emptyBody = await req('POST', '/api/experience/actions', { body: {} });
    assert.equal(emptyBody.status, 400);
  });

  test('合法动作摄取（带 data_path+metric 注册）→ 归因 job 完成 estimable', { timeout: 180000 }, async () => {
    const r = await req('POST', '/api/experience/actions', {
      body: {
        action_log: ACTION_LOG,
        data_path: join(FX, 'experience_data.csv'),
        metric: 'y',
        time_col: 't',
      },
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.action_log_id, '20260301_e2e00001');
    const jobId = r.body.data.attribution_job_id;
    assert.ok(jobId);
    assert.equal(r.body.data.idempotent_replay, false);

    const done = await pollUntil(async () => {
      const v = await req('GET', `/api/experience/attribution/${jobId}`);
      return { done: v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed', value: v.body?.data };
    }, { label: 'attribution job' });
    assert.equal(done.status, 'completed', JSON.stringify(done).slice(0, 600));
    assert.equal(done.reports.length, 1);
    assert.equal(done.reports[0].action_log_id, '20260301_e2e00001');
    assert.equal(done.reports[0].attribution.attribution_status, 'estimable');
    assert.ok(done.reports[0].attribution.effect !== null);
    assert.ok(existsSync(done.reports[0].report_path));
  });

  test('GET /actions/:id/status → completed', async () => {
    const r = await req('GET', '/api/experience/actions/20260301_e2e00001/status');
    assert.equal(r.status, 200);
    assert.equal(r.body.data.action_log_id, '20260301_e2e00001');
    assert.equal(r.body.data.status, 'completed');
  });

  test('幂等重放：同 action_log 再摄取 → 同 id / 同 job / 不重复归因', async () => {
    const r = await req('POST', '/api/experience/actions', { body: { action_log: ACTION_LOG } });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.action_log_id, '20260301_e2e00001');
    assert.equal(r.body.data.idempotent_replay, true);
    assert.equal(r.body.data.status, 'completed');
  });

  test('recommend 命中（同工况同方向）→ playbook_hit + recommendation_id', async () => {
    const r = await req('POST', '/api/experience/recommend', {
      body: {
        fault_signature: {
          signature_version: '1.0',
          anomalous_params: [{ parameter: 'temp', direction: 'high' }],
          regime: { product: 'P1', machine: 'M1', regime_label: 'R1' },
          degraded_metric: 'y',
        },
        top_k: 5,
        regime_fallback: true,
      },
    });
    assert.equal(r.status, 200);
    const d = r.body.data;
    assert.equal(d.recommendation_status, 'playbook_hit');
    assert.equal(d.match_scope, 'regime');
    assert.ok(d.recommendation_id);
    assert.ok(Array.isArray(d.playbooks) && d.playbooks.length >= 1);
    assert.ok(['E1', 'E2', 'E3'].includes(d.playbooks[0].evidence_grade));
  });

  test('recommend 无命中 → 降级链（degradation_path + fallback）', async () => {
    const r = await req('POST', '/api/experience/recommend', {
      body: {
        fault_signature: {
          signature_version: '1.0',
          anomalous_params: [{ parameter: 'feedrate', direction: 'low' }],
          regime: { product: 'PX', machine: 'MX', regime_label: 'RX' },
        },
      },
    });
    assert.equal(r.status, 200);
    const d = r.body.data;
    assert.ok(['no_playbook_hit', 'fallback_generic', 'direction_only'].includes(d.recommendation_status),
      `unexpected status ${d.recommendation_status}`);
    assert.ok(Array.isArray(d.degradation_path) && d.degradation_path.length > 0);
  });

  test('recommend 缺 fault_signature → 400', async () => {
    const r = await req('POST', '/api/experience/recommend', { body: {} });
    assert.equal(r.status, 400);
    const g = await req('GET', '/api/experience/recommend');
    assert.equal(g.status, 400);
  });

  test('feedback 非法 result → 400；library 视图显示 1 条经验', async () => {
    const bad = await req('POST', '/api/experience/feedback', {
      body: { experience_id: 'whatever', result: 'magic' },
    });
    assert.equal(bad.status, 400);

    const lib = await req('GET', '/api/experience/library');
    assert.equal(lib.status, 200);
    assert.equal(lib.body.data.store_entries, 1, 'store holds exactly the e2e entry');
  });

  test('feedback 用真实 chunk_id → corroboration≥2 / grade=E2', async () => {
    // 从 store 读出真实 chunk_id（服务端零业务计算，条目由 experience_build 产出）
    const { readFileSync } = await import('fs');
    const store = readFileSync(join(CL_ROOT, 'experience', 'library', '06_experience', 'tuning_experience.jsonl'), 'utf-8');
    const chunkId = JSON.parse(store.split(/\r?\n/).filter(Boolean)[0]).chunk_id;
    assert.match(chunkId, /^exp_tuning_action_effect_/);

    const r = await req('POST', '/api/experience/feedback', {
      body: { experience_id: chunkId, result: 'effective', note: 'e2e effective' },
    });
    assert.equal(r.status, 200);
    assert.match(r.body.data.stdout_tail, /corroboration=/);
    assert.ok(r.body.data.counters, 'counters mirror present');
    assert.ok(Number(r.body.data.counters.corroboration ?? 0) >= 2,
      `expect corroboration>=2, got ${JSON.stringify(r.body.data.counters)}`);
    assert.equal(r.body.data.counters.evidence_grade, 'E2');
  });

  test('未知 action id / 未知 job → 404', async () => {
    const s = await req('GET', '/api/experience/actions/20990101_nope/status');
    assert.equal(s.status, 404);
    const j = await req('GET', '/api/experience/attribution/attr-nope');
    assert.equal(j.status, 404);
  });
});

// ─────────────────────────── optimizer ──────────────────────────────────

describe('optimizer routes — 真实 CLI（optimizer.py init/design/ingest + 状态机）', () => {
  // 与试验面一致：temp=160 时 brix=1.54 落窗中心（收敛双门槛可满足）
  let round = 0;
  function fabricateResult(design) {
    round += 1;
    let s = 42 + round * 7;
    const rnd = () => { s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648; };
    return {
      result_version: '1.0',
      campaign_id: design.campaign_id,
      round_id: design.round_id,
      trials: design.trials.map((t) => {
        const temp = t.setpoints.temp;
        const mean = 1.54 + 0.00012 * Math.pow(temp - 160, 2);
        return {
          trial_id: t.trial_id,
          status: 'completed',
          measurements: { brix: [0, 1, 2].map(() => +(mean + (rnd() - 0.5) * 0.004).toFixed(5)) },
          measured_at: '2026-10-01T00:00:00Z',
        };
      }),
      ingest_meta: { source: 'api', ingested_at: new Date().toISOString() },
    };
  }

  test('campaign 创建（goal=target 无 target_range）→ 400（O-G1a）', async () => {
    const bad = await req('POST', '/api/optimizer/campaign', {
      body: { ...optObjective('OPT-20261001-404'), target_range: undefined },
    });
    assert.equal(bad.status, 400);
  });

  test('campaign 创建 → phase=initialized；未知 campaign → 404', async () => {
    const r = await req('POST', '/api/optimizer/campaign', { body: optObjective('OPT-20261001-777') });
    assert.equal(r.status, 200, JSON.stringify(r.body).slice(0, 400));
    assert.equal(r.body.data.campaign_id, 'OPT-20261001-777');
    assert.equal(r.body.data.phase, 'initialized');
    assert.ok(existsSync(r.body.data.run_dir));

    const nf = await req('GET', '/api/optimizer/state?campaign_id=OPT-19700101-001');
    assert.equal(nf.status, 404);
    const nfRound = await req('POST', '/api/optimizer/round', { body: { campaign_id: 'OPT-19700101-001', action: 'design' } });
    assert.equal(nfRound.status, 404);
    const noId = await req('GET', '/api/optimizer/state');
    assert.equal(noId.status, 400);
  });

  test('design → 布点表（trial_id/setpoints/extrapolation）+ 预算', async () => {
    const r = await req('POST', '/api/optimizer/round', { body: { campaign_id: 'OPT-20261001-777', action: 'design' } });
    assert.equal(r.status, 200, JSON.stringify(r.body).slice(0, 400));
    const d = r.body.data;
    assert.equal(d.round_id, 'R001');
    assert.ok(d.method);
    assert.ok(Array.isArray(d.trial_design.trials) && d.trial_design.trials.length >= 1);
    for (const t of d.trial_design.trials) {
      assert.match(t.trial_id, /^R001-T\d{2}$/);
      assert.ok(t.setpoints && typeof t.setpoints.temp === 'number');
      assert.equal(typeof t.extrapolation, 'boolean');
    }
    assert.ok(d.budget_remaining.trials < 60);
    assert.ok(existsSync(d.design_path));
  });

  test('ingest 不带 trial_result → 400；round_id 不匹配 → 400', async () => {
    const missing = await req('POST', '/api/optimizer/round', { body: { campaign_id: 'OPT-20261001-777', action: 'ingest' } });
    assert.equal(missing.status, 400);
    const mismatch = await req('POST', '/api/optimizer/round', {
      body: {
        campaign_id: 'OPT-20261001-777', action: 'ingest',
        trial_result: { round_id: 'R099', trials: [{ trial_id: 'R099-T01', status: 'completed', measurements: { brix: [1.54] } }] },
      },
    });
    assert.equal(mismatch.status, 400);
    assert.match(mismatch.body.error, /R001/);
  });

  test('design→ingest 循环至 converged；state 查询含 incumbent/预算', { timeout: 300000 }, async () => {
    const campaignId = 'OPT-20261001-999';
    const created0 = await req('POST', '/api/optimizer/campaign', { body: optObjective(campaignId) });
    assert.equal(created0.status, 200);
    let lastPhase = 'initialized';
    for (let i = 0; i < 14; i += 1) {
      const design = await req('POST', '/api/optimizer/round', { body: { campaign_id: campaignId, action: 'design' } });
      if (design.status === 409) break; // 终态
      assert.equal(design.status, 200, JSON.stringify(design.body).slice(0, 400));

      const ing = await req('POST', '/api/optimizer/round', {
        body: { campaign_id: campaignId, action: 'ingest', trial_result: fabricateResult(design.body.data.trial_design) },
      });
      assert.equal(ing.status, 200, JSON.stringify(ing.body).slice(0, 600));
      lastPhase = ing.body.data.phase;
      assert.match(ing.body.data.transition, / -> /);
      if (['converged', 'paused', 'exhausted', 'aborted'].includes(lastPhase)) break;
    }
    assert.equal(lastPhase, 'converged', 'quadratic surface around 160 must converge (smoke: 6 rounds)');

    const st = await req('GET', `/api/optimizer/state?campaign_id=${campaignId}`);
    assert.equal(st.status, 200);
    const d = st.body.data;
    assert.equal(d.phase, 'converged');
    assert.ok(d.incumbent && d.incumbent.setpoints && typeof d.incumbent.setpoints.temp === 'number');
    assert.ok(d.budget && d.budget.rounds_used >= 1);
    assert.ok(Array.isArray(d.history) && d.history.length >= 1);
    assert.ok(d.next_action && d.next_action.recommendation);
  });
});

describe('optimizer pause/resume — 控制面（paused 为状态机合法 phase）', () => {
  test('design 一次后 pause → phase=paused；resume → 回到活跃态', async () => {
    const created = await req('POST', '/api/optimizer/campaign', { body: optObjective('OPT-20261001-888') });
    assert.equal(created.status, 200);
    const id = 'OPT-20261001-888';

    const design = await req('POST', '/api/optimizer/round', { body: { campaign_id: id, action: 'design' } });
    assert.equal(design.status, 200);

    const paused = await req('POST', '/api/optimizer/pause', { body: { campaign_id: id } });
    assert.equal(paused.status, 200);
    assert.equal(paused.body.data.phase, 'paused');
    assert.equal(paused.body.data.next_action.recommendation, 'needs_human');

    const stateView = await req('GET', `/api/optimizer/state?campaign_id=${id}`);
    assert.equal(stateView.body.data.phase, 'paused');

    const resumed = await req('POST', '/api/optimizer/resume', { body: { campaign_id: id } });
    assert.equal(resumed.status, 200);
    assert.equal(resumed.body.data.phase, 'exploring');
    assert.equal(resumed.body.data.next_action.recommendation, 'continue_exploit');
  });

  test('非活跃态 pause / 非 paused resume / terminal design → 409', async () => {
    // OPT-20261001-999 已收敛（前一个 describe 跑完双门槛循环）
    const pausedOps = await req('POST', '/api/optimizer/pause', { body: { campaign_id: 'OPT-20261001-999' } });
    assert.equal(pausedOps.status, 409);
    const resumedOps = await req('POST', '/api/optimizer/resume', { body: { campaign_id: 'OPT-20261001-999' } });
    assert.equal(resumedOps.status, 409);
    const designTerminal = await req('POST', '/api/optimizer/round', { body: { campaign_id: 'OPT-20261001-999', action: 'design' } });
    assert.equal(designTerminal.status, 409);
    // 888 已 resume 到 exploring（非 paused）→ resume 再按 409
    const resumed888 = await req('POST', '/api/optimizer/resume', { body: { campaign_id: 'OPT-20261001-888' } });
    assert.equal(resumed888.status, 409);
  });
});
