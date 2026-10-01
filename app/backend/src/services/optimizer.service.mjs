// Optimizer Service — 目标闭环寻优（industrial-optimizer-loop skill）的 HTTP 集成层。
//
// campaign = 一个 RUN_DIR（<root>/optimizer/campaigns/<campaign_id>）。全部记忆在
// 01_state/optimizer_state.json（skill 的会话式状态机，进程不驻留）：
//   - POST /campaign  optimizer.py init（O-G1 校验；失败 400 原样回传逐条错误）
//   - POST /round     action=design → trial_design.json 布点表；
//                     action=ingest → 落 trial_result.json 后状态机转移
//   - GET  /state     读 01_state/optimizer_state.json（phase/incumbent/预算/信念）
//   - POST /pause|resume   控制面操作：paused 是状态机的合法 phase；CLI 未暴露
//                     子命令，由本服务以受控方式改写 state（记录 prev_phase 与
//                     原因；数值字段零触碰）
//
// 本服务只做文件编排与状态读取，布点/收敛判定全部由 optimizer.py 产出
// （authored_by=script，纯分析系统：绝不代执行试验、绝不下发参数）。

import { join } from 'path';
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'fs';
import {
  closedloopRoot, ensureDir, readJsonSafe, writeJson, uvPython, tail,
} from './closedloop.util.mjs';

const SKILL_SCRIPTS = '.claude/skills/industrial-optimizer-loop/scripts';
const CAMPAIGN_ID_RE = /^OPT-[0-9]{8}-[0-9]{3,}$/;
const ACTIVE_PHASES = new Set(['initialized', 'exploring', 'exploiting', 'confirming']);
const TERMINAL_PHASES = new Set(['converged', 'paused', 'exhausted', 'aborted']);
const GOALS = new Set(['target', 'minimize', 'maximize']);

let seq = 0;

function campaignsDir() { return join(closedloopRoot(), 'optimizer', 'campaigns'); }
function campaignDir(id) { return join(campaignsDir(), String(id)); }
function statePath(id) { return join(campaignDir(id), '01_state', 'optimizer_state.json'); }

function loadState(campaignId) {
  return readJsonSafe(statePath(campaignId), null);
}

function latestRoundDir(campaignId) {
  const rd = join(campaignDir(campaignId), '02_rounds');
  if (!existsSync(rd)) return null;
  const ids = readdirSync(rd).filter((d) => /^R\d{3}$/.test(d)).sort();
  return ids.length ? ids[ids.length - 1] : null;
}

function budgetRemaining(state) {
  const b = state?.budget ?? {};
  return {
    rounds: Math.max(Number(b.max_rounds ?? 0) - Number(b.rounds_used ?? 0), 0),
    trials: Math.max(Number(b.max_trials ?? 0) - Number(b.trials_used ?? 0), 0),
  };
}

function requireCampaign(campaignId) {
  const id = String(campaignId ?? '').trim();
  if (!id) {
    const err = new Error('campaign_id is required');
    err.status = 400;
    throw err;
  }
  const state = loadState(id);
  if (!state) {
    const err = new Error(`campaign not found: ${id}`);
    err.status = 404;
    throw err;
  }
  return { id, state };
}

/** skill CLI 的 CONTRACT ERROR（exit 1）→ 409 冲突（执行契约语义）。 */
function contractError(output, fallback) {
  const err = new Error(tail(output, 1200).trim() || fallback);
  err.status = 409;
  return err;
}

function objectiveError(output, fallback) {
  const err = new Error(tail(output, 1200).trim() || fallback);
  err.status = 400;
  return err;
}

// ── POST /campaign：init ────────────────────────────────────────────────

export async function createCampaign(body) {
  const objective = (body && typeof body.objective === 'object' && !Array.isArray(body.objective))
    ? body.objective
    : body;
  if (!objective || typeof objective !== 'object') {
    const err = new Error('objective (contract 1.0) is required');
    err.status = 400;
    throw err;
  }
  if (objective.contract_version !== '1.0') {
    const err = new Error('objective.contract_version must be "1.0"');
    err.status = 400;
    throw err;
  }
  if (!GOALS.has(objective.goal)) {
    const err = new Error(`objective.goal must be one of ${[...GOALS].join('|')}`);
    err.status = 400;
    throw err;
  }
  if (objective.goal === 'target') {
    const r = objective.target_range;
    if (!Array.isArray(r) || r.length !== 2 || !(Number(r[0]) < Number(r[1]))) {
      const err = new Error('goal=target requires target_range [low, high] with low < high (O-G1a)');
      err.status = 400;
      throw err;
    }
  }
  if (!Array.isArray(objective.factors) || objective.factors.length === 0) {
    const err = new Error('objective.factors must be a non-empty array');
    err.status = 400;
    throw err;
  }

  let campaignId = String(objective.campaign_id ?? '').trim();
  if (!campaignId) {
    seq += 1;
    const day = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    campaignId = `OPT-${day}-${String((Date.now() % 900) + 100)}${seq > 1 ? String(seq) : ''}`;
    objective.campaign_id = campaignId;
  }
  if (!CAMPAIGN_ID_RE.test(campaignId)) {
    const err = new Error(`objective.campaign_id must match ${CAMPAIGN_ID_RE} (got ${campaignId})`);
    err.status = 400;
    throw err;
  }

  const rd = campaignDir(campaignId);
  ensureDir(rd);
  const objectiveFile = join(closedloopRoot(), 'optimizer', 'objectives', `${campaignId}.json`);
  writeJson(objectiveFile, objective);

  const proc = await uvPython(
    join(SKILL_SCRIPTS, 'optimizer.py'),
    ['init', '--run-dir', rd, '--objective', objectiveFile],
    { timeoutMs: 90000 },
  );
  if (Number(proc.code) !== 0) {
    // O-G1 校验失败：逐条错误原样回传（绝不放宽校验）
    throw objectiveError(proc.stdout + proc.stderr, `optimizer init failed (exit ${proc.code})`);
  }
  const state = loadState(campaignId);
  return {
    campaign_id: campaignId,
    phase: state?.phase ?? 'initialized',
    run_dir: rd,
    objective_path: objectiveFile,
    next_action: state?.next_action ?? null,
    init_stdout: tail(proc.stdout, 600),
  };
}

// ── POST /round：design | ingest ────────────────────────────────────────

export async function round({ campaign_id, action, trial_result = null } = {}) {
  const { id, state: prev } = requireCampaign(campaign_id);
  const act = String(action ?? '').trim().toLowerCase();
  if (act !== 'design' && act !== 'ingest') {
    const err = new Error(`action must be design|ingest (got ${action})`);
    err.status = 400;
    throw err;
  }
  if (TERMINAL_PHASES.has(prev.phase)) {
    const err = new Error(`campaign ${id} is terminal (phase=${prev.phase}) — nothing to ${act}`);
    err.status = 409;
    throw err;
  }
  const rd = campaignDir(id);

  if (act === 'design') {
    const proc = await uvPython(join(SKILL_SCRIPTS, 'optimizer.py'), ['design', '--run-dir', rd], { timeoutMs: 120000 });
    if (Number(proc.code) !== 0) throw contractError(proc.stdout + proc.stderr, `optimizer design failed (exit ${proc.code})`);
    const rid = latestRoundDir(id);
    const designPath = rid ? join(rd, '02_rounds', rid, 'trial_design.json') : null;
    const design = designPath && existsSync(designPath) ? readJsonSafe(designPath, null) : null;
    const state = loadState(id);
    return {
      campaign_id: id,
      phase: state?.phase ?? null,
      round_id: design?.round_id ?? rid,
      method: design?.method ?? null,
      trial_design: design,
      design_path: designPath,
      budget_remaining: budgetRemaining(state),
      stdout_tail: tail(proc.stdout, 500),
    };
  }

  // action === 'ingest'
  if (!trial_result || typeof trial_result !== 'object' || Array.isArray(trial_result)) {
    const err = new Error('action=ingest requires trial_result ({round_id, trials:[...]})');
    err.status = 400;
    throw err;
  }
  const rid = latestRoundDir(id);
  if (!rid) {
    const err = new Error(`campaign ${id} has no designed round — call action=design first`);
    err.status = 409;
    throw err;
  }
  if (trial_result.round_id && String(trial_result.round_id) !== rid) {
    const err = new Error(`trial_result.round_id ${trial_result.round_id} != latest designed round ${rid}`);
    err.status = 400;
    throw err;
  }
  if (!Array.isArray(trial_result.trials) || trial_result.trials.length === 0) {
    const err = new Error('trial_result.trials must be a non-empty array');
    err.status = 400;
    throw err;
  }
  const resultPath = join(rd, '02_rounds', rid, 'trial_result.json');
  writeJson(resultPath, trial_result);

  const proc = await uvPython(join(SKILL_SCRIPTS, 'optimizer.py'), ['ingest', '--run-dir', rd], { timeoutMs: 180000 });
  if (Number(proc.code) !== 0) {
    // 回投结果非法 / 状态机拒绝：409 + CLI 原文（执行契约语义）
    throw contractError(proc.stdout + proc.stderr, `optimizer ingest failed (exit ${proc.code})`);
  }
  const state = loadState(id);
  return {
    campaign_id: id,
    round_id: rid,
    phase: state?.phase ?? null,
    transition: `${prev.phase} -> ${state?.phase ?? '?'}`,
    incumbent: state?.incumbent ?? null,
    next_action: state?.next_action ?? null,
    budget_remaining: budgetRemaining(state),
    result_path: resultPath,
    stdout_tail: tail(proc.stdout, 500),
  };
}

// ── GET /state ──────────────────────────────────────────────────────────

export function state({ campaign_id } = {}) {
  const { id, state } = requireCampaign(campaign_id);
  return {
    ...state,
    campaign_id: id,
    run_dir: campaignDir(id),
    state_path: statePath(id),
  };
}

// ── POST /pause | /resume（控制面；paused 是状态机合法 phase）──────────

export function pause({ campaign_id } = {}) {
  const { id, state } = requireCampaign(campaign_id);
  if (!ACTIVE_PHASES.has(state.phase)) {
    const err = new Error(`campaign ${id} phase=${state.phase} is not active — cannot pause`);
    err.status = 409;
    throw err;
  }
  state.stop_resume = {
    can_pause: false,
    resume_hint: `paused via API; prev_phase=${state.phase}`,
  };
  state.phase = 'paused';
  state.next_action = {
    recommendation: 'needs_human',
    reasons: ['paused via POST /api/optimizer/pause — resume with POST /api/optimizer/resume'],
    agent_review_required: false,
  };
  writeFileSync(statePath(id), JSON.stringify(state, null, 2), 'utf-8');
  return { campaign_id: id, phase: state.phase, prev_phase_hint: state.stop_resume.resume_hint, next_action: state.next_action };
}

export function resume({ campaign_id } = {}) {
  const { id, state } = requireCampaign(campaign_id);
  if (state.phase !== 'paused') {
    const err = new Error(`campaign ${id} phase=${state.phase} is not paused`);
    err.status = 409;
    throw err;
  }
  const m = /prev_phase=(\w+)/.exec(String(state.stop_resume?.resume_hint ?? ''));
  const prev = m && ACTIVE_PHASES.has(m[1]) ? m[1] : 'exploring';
  state.phase = prev;
  state.next_action = {
    recommendation: 'continue_exploit',
    reasons: [`resumed via POST /api/optimizer/resume (from paused; prev_phase=${prev})`],
    agent_review_required: false,
  };
  state.stop_resume = { can_pause: true, resume_hint: 'ingest each round\'s trial_result.json' };
  writeFileSync(statePath(id), JSON.stringify(state, null, 2), 'utf-8');
  return { campaign_id: id, phase: state.phase, next_action: state.next_action };
}

/** 运维/测试：列出全部 campaign。 */
export function listCampaigns() {
  const dir = campaignsDir();
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .map((id) => ({ campaign_id: id, phase: loadState(id)?.phase ?? null }))
    .filter((x) => x.phase !== null);
}
