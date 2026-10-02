// Live API-track E2E against the running backend (127.0.0.1:3210).
// Chain: sentinel baseline task -> sentinel watch task -> experience recommend
//        -> optimizer campaign -> design/ingest rounds -> converged -> state.
// All inputs are the real artifacts produced by the T4 file-track E2E.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const BASE = 'http://127.0.0.1:3210';
const ROOT = 'D:/codes/myskills/industrial-deep-diagnostic';
const E2E = `${ROOT}/workspace/e2e-closedloop-t4/e2e`;

const checks = [];
function record(name, ok, detail = '') {
  checks.push([name, !!ok, String(detail)]);
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`);
}

async function api(method, path, body = null) {
  const res = await fetch(BASE + path, {
    method,
    headers: { 'content-type': 'application/json', ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}) },
    body: body ? JSON.stringify(body) : null,
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-json */ }
  return { status: res.status, json };
}

let TOKEN = null;
async function authenticate() {
  const cred = { username: `e2e-t4-${Date.now() % 100000}`, password: 'E2e-T4-Test#2026' };
  let r = await api('POST', '/api/auth/login', cred);
  if (r.status !== 200) r = await api('POST', '/api/auth/register', cred);
  TOKEN = r.json?.data?.token ?? r.json?.data?.session_token ?? null;
  return { status: r.status, ok: !!TOKEN, user: r.json?.data?.user?.username };
}

async function waitTask(taskId, timeoutMs = 120000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const { json } = await api('GET', `/api/sentinel/tasks/${taskId}`);
    const st = json?.data?.status;
    if (st === 'completed' || st === 'failed') return json.data;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return { status: 'timeout' };
}

// ── 0. authenticate ──────────────────────────────────────────────────────────
console.log('[API-0] auth (register/login)');
const auth = await authenticate();
record('A0.authenticated', auth.ok, `status=${auth.status} user=${auth.user}`);
if (!auth.ok) {
  console.log('[API-LIVE] cannot proceed without auth');
  process.exit(1);
}

// ── 1. sentinel baseline (async) ─────────────────────────────────────────────
console.log('[API-1] POST /api/sentinel/baseline');
let r = await api('POST', '/api/sentinel/baseline', {
  line: 'L1-T4E2E',
  history_csv: `${E2E}/sentinel/history.csv`,
  doe_run_dir: `${E2E}/doe_run`,
  time_col: 't',
});
record('A1.baseline_submit_202', r.status === 200 && r.json?.success === true,
  `status=${r.status} task=${r.json?.data?.task_id}`);
const bl = await waitTask(r.json?.data?.task_id);
record('A1.baseline_completed', bl.status === 'completed', `status=${bl.status}`);

// ── 2. sentinel watch (async) ────────────────────────────────────────────────
console.log('[API-2] POST /api/sentinel/tasks (watch)');
mkdirSync(`${E2E}/api_out`, { recursive: true });
r = await api('POST', '/api/sentinel/tasks', {
  data_path: `${E2E}/sentinel/window_fault.csv`,
  baseline_path: `${E2E}/sentinel/watch_baseline.json`,
  time_col: 't',
  out_dir: `${E2E}/api_out/watch`,
});
record('A2.watch_submit_202', r.status === 200 && r.json?.success === true,
  `status=${r.status} task=${r.json?.data?.task_id}`);
const wt = await waitTask(r.json?.data?.task_id);
const alertCount = wt?.result?.alert_count ?? wt?.result?.alerts?.length ?? null;
record('A2.watch_completed_with_alerts',
  wt.status === 'completed' && (alertCount === null || alertCount > 0),
  `status=${wt.status} alerts=${alertCount} code=${wt.code ?? wt?.result?.exit_code}`);

// ── 3. experience: ingest actions -> attribution job -> recommend ───────────
console.log('[API-3] POST /api/experience/actions (attribution job) -> recommend');
const A1log = {
  schema_version: '1.0', ts: '2026-01-05T00:33:20Z',
  actor: { actor_id: 'ENG-ZHANG-0091', actor_type: 'engineer', display_alias: null },
  actions: [{ parameter: 'temp', from: 85.0, to: 88.0, unit: 'degC' }],
  bundled_action: { is_bundle: false, bundle_reason: 'single', note: null },
  context: { product: 'PA', machine: 'L1', regime_label: 'S1', steady_segment_ref: null, group_key: null },
  trigger: { trigger_type: 'alert', ref_id: 'ALT-API-E2E-001' },
  attribution_confounds: [], recommendation_ref: null,
  ingest_meta: { source: 'csv_import', ingested_at: null },
};
const A2log = {
  ...A1log, ts: '2026-01-05T01:06:40Z',
  actions: [{ parameter: 'temp', from: 88.0, to: 84.0, unit: 'degC' }],
  trigger: { trigger_type: 'manual', ref_id: null },
};
r = await api('POST', '/api/experience/actions', {
  action_log: [A1log, A2log],
  data_path: `${E2E}/tune_run/00_input/data.csv`,
  metric: 'yield_pct', time_col: 't',
});
record('A3.actions_ingest_200', r.status === 200 && r.json?.success === true,
  `status=${r.status} job=${r.json?.data?.attribution_job_id}`);
const jobId = r.json?.data?.attribution_job_id;
let job = null;
{
  const t0 = Date.now();
  while (Date.now() - t0 < 180000) {
    const v = await api('GET', `/api/experience/attribution/${jobId}`);
    job = v.json?.data;
    if (job?.status === 'completed' || job?.status === 'failed') break;
    await new Promise((res) => setTimeout(res, 1500));
  }
  record('A3.attribution_completed', job?.status === 'completed', `status=${job?.status} err=${(job?.error || '').slice(0, 120)}`);
}
const sig = JSON.parse(readFileSync(`${E2E}/tune_run/00_input/fault_signature.json`, 'utf8'));
r = await api('POST', '/api/experience/recommend', { fault_signature: sig, top_k: 3 });
const recStatus = r.json?.data?.recommendation_status;
record('A3.recommend_playbook_hit',
  r.status === 200 && recStatus === 'playbook_hit',
  `status=${r.status} recommendation_status=${recStatus}`);

// ── 4. optimizer campaign -> rounds -> converged ────────────────────────────
console.log('[API-4] POST /api/optimizer/campaign');
const objective = {
  contract_version: '1.0',
  campaign_id: `OPT-20261001-${String(Math.floor(Math.random() * 900) + 100)}`,
  target_metric: 'yield_pct',
  goal: 'target',
  target_range: [98.0, 100.2],
  factors: [
    { name: 'temp', type: 'numeric', min: 82.0, max: 88.0, unit: 'degC' },
    { name: 'press', type: 'numeric', min: 0.55, max: 0.65, unit: 'MPa' },
  ],
  budget: { max_rounds: 10, max_trials: 30 },
  noise: { replicates_for_sigma: 3 },
  seed: 11,
};
r = await api('POST', '/api/optimizer/campaign', { objective });
record('A4.campaign_init_200', r.status === 200 && r.json?.success === true,
  `status=${r.status} campaign=${r.json?.data?.campaign_id} phase=${r.json?.data?.phase}`);
const campaignId = r.json?.data?.campaign_id;

const ORDER = ['temp', 'press'];
function plant(temp, press) {
  return 100.0 - 0.25 * (temp - 84.0) ** 2 - 60.0 * (press - 0.60) ** 2;
}
let phase = r.json?.data?.phase ?? null;
let rounds = 0;
let terminal = false;
const { execSync } = await import('node:child_process');
for (let i = 1; i <= 14 && !terminal; i++) {
  const rd = await api('POST', '/api/optimizer/round', { campaign_id: campaignId, action: 'design' });
  if (rd.status !== 200) { record('A4.round_design', false, JSON.stringify(rd.json).slice(0, 200)); break; }
  const design = rd.json?.data?.trial_design ?? {};
  const trials = design?.trials ?? [];
  const rid = rd.json?.data?.round_id ?? `R${String(i).padStart(3, '0')}`;
  const trialsOut = trials.map((t) => ({
    trial_id: t.trial_id,
    status: 'completed',
    measurements: {
      [objective.target_metric]: Array.from(
        { length: t.replicates ?? 1 },
        () => Number((plant(t.setpoints[ORDER[0]], t.setpoints[ORDER[1]])
          + (Math.random() * 0.6 - 0.3)).toFixed(4)),
      ),
    },
  }));
  const result = {
    result_version: '1.0', campaign_id: campaignId, round_id: rid, trials: trialsOut,
  };
  const ing = await api('POST', '/api/optimizer/round', {
    campaign_id: campaignId, action: 'ingest', trial_result: result,
  });
  if (ing.status !== 200) { record('A4.round_ingest', false, JSON.stringify(ing.json).slice(0, 300)); break; }
  rounds = i;
  phase = ing.json?.data?.state?.phase ?? ing.json?.data?.phase ?? phase;
  if (['converged', 'exhausted', 'paused', 'aborted'].includes(phase)) terminal = true;
}
record('A4.campaign_terminal', terminal, `phase=${phase} rounds=${rounds}`);

console.log('[API-5] GET /api/optimizer/state');
const st = await api('GET', `/api/optimizer/state?campaign_id=${campaignId}`);
record('A5.state_readback', st.status === 200 && st.json?.success === true,
  `phase=${st.json?.data?.phase}`);

// ── summary ──────────────────────────────────────────────────────────────────
const npass = checks.filter(([, ok]) => ok).length;
console.log('\n' + '='.repeat(62));
for (const [name, ok, detail] of checks) if (!ok) console.log(`  FAIL  ${name}  ${detail}`);
console.log(`[API-LIVE] ${npass}/${checks.length} checks passed — ${npass === checks.length ? 'ALL GREEN' : 'FAILURES PRESENT'}`);
process.exit(npass === checks.length ? 0 : 1);
