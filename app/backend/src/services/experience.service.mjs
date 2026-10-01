// Experience Service — 调优经验库（industrial-tuning-memory skill）的 HTTP 集成层。
//
// 职责链（全部委托真实 CLI，零业务计算）：
//   1. POST /actions        校验 action_log（schema v1.0，批量≤100，失败 400）→
//                           幂等落盘 00_input/action_log/<id>.json →
//                           异步归因 job：tune_stats.py attribute →
//                           experience_build.mjs build → 返回 attribution_job_id
//   2. GET /actions/:id/status   按动作 id 查归因 job 状态
//   3. GET /attribution/:jobId   归因报告（诚实状态机原样透传）
//   4. GET|POST /recommend       match_playbook.mjs recommend（fault_signature
//                                → playbook 命中或四级降级链）
//   5. POST /feedback            experience_build.mjs feedback（佐证/反证计数）
//
// 经验库 = 一个持久 RUN_DIR（<root>/experience/library）：跨摄取累积
// tuning_experience.jsonl，同工况同动作签名自动佐证(+1)。归因需要参考数据集
// （00_input/data.csv + metric 列）：请求体可选携带 data_path/metric 注册；
// 未携带时沿用最近注册的数据集（插件 experience_log 不传数据，此为继承语义）；
// 从未注册则 tune_stats 以 not_estimable/metric_missing 诚实收尾，job 仍算完成。

import { join, resolve } from 'path';
import { existsSync, mkdirSync, copyFileSync, writeFileSync, readFileSync, readdirSync, rmSync } from 'fs';
import { createHash } from 'crypto';
import {
  closedloopRoot, ensureDir, readJsonSafe, writeJson,
  uvPython, nodeScript, tail,
} from './closedloop.util.mjs';

const SKILL_SCRIPTS = '.claude/skills/industrial-tuning-memory/scripts';

const ACTOR_TYPES = new Set(['engineer', 'control_system', 'batch_recipe', 'aws_executor', 'unknown_retro_inferred']);
const TRIGGER_TYPES = new Set(['alert', 'experience_recipe', 'manual', 'aws_optimization']);
const CONFOUND_TYPES = new Set(['batch_change', 'environment', 'maintenance', 'other_action']);
const FEEDBACK_RESULTS = new Set(['effective', 'ineffective', 'harmful', 'confirmed']);
const MAX_BATCH = 100;

let jobs = null;          // Map<job_id, job>
let jobSeq = 0;
let actionIndex = null;   // Map<action_log_id, job_id>

function libraryDir() { return join(closedloopRoot(), 'experience', 'library'); }
function actionLogDir() { return join(libraryDir(), '00_input', 'action_log'); }
function datasetMetaPath() { return join(libraryDir(), '00_input', 'dataset_meta.json'); }

function ensureLibrary() {
  ensureDir(actionLogDir());
  ensureDir(join(libraryDir(), 'conclusions'));
  if (!jobs) jobs = new Map();
  if (!actionIndex) actionIndex = new Map();
}
function jobsMap() { ensureLibrary(); return jobs; }
function indexMap() { ensureLibrary(); return actionIndex; }

// ── action_log 校验（schema v1.0 的服务端子集；失败必须 400）───────────

function validateActionLog(log, where) {
  const errs = [];
  const push = (m) => errs.push(`${where}: ${m}`);
  if (!log || typeof log !== 'object' || Array.isArray(log)) {
    return [`${where}: action_log must be an object`];
  }
  if (log.schema_version !== '1.0') push('schema_version must be "1.0"');
  if (typeof log.ts !== 'string' || !log.ts) push('ts (ISO8601 string) is required');
  const actor = log.actor ?? {};
  if (typeof actor.actor_id !== 'string' || !actor.actor_id) push('actor.actor_id is required');
  if (!ACTOR_TYPES.has(actor.actor_type)) push(`actor.actor_type must be one of ${[...ACTOR_TYPES].join('|')}`);
  if (!Array.isArray(log.actions) || log.actions.length === 0) push('actions must be a non-empty array');
  else {
    if (log.actions.length > 10) push(`actions length ${log.actions.length} > 10`);
    log.actions.forEach((a, i) => {
      if (!a || typeof a !== 'object') { push(`actions[${i}] must be an object`); return; }
      if (typeof a.parameter !== 'string' || !a.parameter) push(`actions[${i}].parameter is required`);
      if (typeof a.to !== 'number') push(`actions[${i}].to must be a number`);
      if (typeof a.unit !== 'string' || !a.unit) push(`actions[${i}].unit is required`);
      if (a.from !== undefined && a.from !== null && typeof a.from !== 'number') push(`actions[${i}].from must be number|null`);
    });
  }
  const trigger = log.trigger;
  if (trigger !== undefined) {
    if (!trigger || typeof trigger !== 'object') push('trigger must be an object');
    else if (!TRIGGER_TYPES.has(trigger.trigger_type)) push(`trigger.trigger_type must be one of ${[...TRIGGER_TYPES].join('|')}`);
  }
  if (log.attribution_confounds !== undefined) {
    if (!Array.isArray(log.attribution_confounds)) push('attribution_confounds must be an array');
    else log.attribution_confounds.forEach((c, i) => {
      if (!c || typeof c !== 'object' || !CONFOUND_TYPES.has(c.type)) push(`attribution_confounds[${i}].type invalid`);
    });
  }
  return errs;
}

// ── 幂等 id：与 experience_build.mjs 同源（ts8 + sha256(canonical)[..8]）──

function canon(obj) {
  if (obj === null || typeof obj !== 'object') return JSON.stringify(obj ?? null);
  if (Array.isArray(obj)) return '[' + obj.map(canon).join(',') + ']';
  const keys = Object.keys(obj).filter((k) => obj[k] !== undefined).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canon(obj[k])).join(',') + '}';
}

function deriveActionLogId(log) {
  if (log.action_log_id) return String(log.action_log_id);
  const ts8 = String(log.ts || '').replace(/\D/g, '').slice(0, 8) || '00000000';
  const sha = createHash('sha256').update(canon(log)).digest('hex');
  return ts8 + sha.slice(0, 8);
}

// ── 数据集注册 ───────────────────────────────────────────────────────────

function registerDataset({ data_path, metric = null, time_col = 't', group_key = null, dead_time = null }) {
  if (!data_path) return datasetMeta();
  const abs = resolve(String(data_path));
  if (!existsSync(abs)) {
    const err = new Error(`data_path not found: ${data_path}`);
    err.status = 400;
    throw err;
  }
  copyFileSync(abs, join(libraryDir(), '00_input', 'data.csv'));
  const meta = {
    data_path: abs, metric, time_col: time_col || 't', group_key: group_key ?? null,
    dead_time: dead_time ?? null, registered_at: new Date().toISOString(),
  };
  writeJson(datasetMetaPath(), meta);
  return meta;
}

function datasetMeta() {
  return readJsonSafe(datasetMetaPath(), null);
}

// ── 归因 job ─────────────────────────────────────────────────────────────

function newJob(actionLogIds) {
  jobSeq += 1;
  const jobId = `attr-${Date.now()}-${String(jobSeq).padStart(4, '0')}`;
  const job = {
    job_id: jobId,
    action_log_ids: actionLogIds,
    status: 'queued',
    created_at: new Date().toISOString(),
    finished_at: null,
    error: null,
    reports: [],
  };
  jobsMap().set(jobId, job);
  for (const id of actionLogIds) indexMap().set(id, jobId);
  if (jobsMap().size > 300) {
    const oldest = jobsMap().keys().next().value;
    jobsMap().delete(oldest);
  }
  return job;
}

async function runAttribution(job, meta) {
  job.status = 'running';
  const rd = libraryDir();
  const args = [
    'attribute', '--run-dir', rd,
    '--data', '00_input/data.csv',
    // 摄取的动作日志按 id 分文件落在 00_input/action_log/ 目录（load_action_logs
    // 原生支持目录形态：目录下全部 *.json 都进归因）
    '--action-log', '00_input/action_log',
    '--time-col', meta?.time_col || 't',
  ];
  if (meta?.metric) args.push('--metric', String(meta.metric));
  if (meta?.group_key) args.push('--group-key', String(meta.group_key));
  if (meta?.dead_time !== null && meta?.dead_time !== undefined && meta?.dead_time !== '') {
    args.push('--dead-time', String(meta.dead_time));
  }

  const attr = await uvPython(join(SKILL_SCRIPTS, 'tune_stats.py'), args, { timeoutMs: 120000 });
  if (attr.timedOut) {
    job.status = 'failed';
    job.error = 'tune_stats attribute timed out';
    job.finished_at = new Date().toISOString();
    return;
  }
  if (Number(attr.code) !== 0) {
    job.status = 'failed';
    job.error = tail(attr.stdout + attr.stderr, 1200);
    job.finished_at = new Date().toISOString();
    return;
  }

  // 归因成功 → 重建本地经验库（幂等：同签名同工况 replay no-op / 佐证 +1）
  // 同样指向 00_input/action_log/ 目录（experience_build 的 loadActionLogs
  // 原生支持目录形态；缺省值是单文件 00_input/action_log.json）
  const build = await nodeScript(
    join(SKILL_SCRIPTS, 'experience_build.mjs'),
    ['build', '--run-dir', rd, '--action-log', '00_input/action_log'],
    { timeoutMs: 60000 },
  );
  if (Number(build.code) !== 0) {
    job.status = 'failed';
    job.error = tail(build.stdout + build.stderr, 1200);
    job.finished_at = new Date().toISOString();
    return;
  }

  job.reports = job.action_log_ids
    .map((id) => {
      const p = join(rd, '06_experience', 'attribution', `${id}.json`);
      return { action_log_id: id, report_path: existsSync(p) ? p : null };
    });
  job.status = 'completed';
  job.finished_at = new Date().toISOString();
}

// ── 路由服务函数 ─────────────────────────────────────────────────────────

/**
 * POST /api/experience/actions —— 批量摄取动作日志（≤100），schema 校验失败 400；
 * 幂等 action_log_id（重放不重复落盘、不重复归因）；返回 attribution_job_id。
 * body: { action_log: object|array, data_path?, metric?, time_col?, group_key?, dead_time? }
 */
export function ingestActions(body) {
  ensureLibrary();
  const raw = body?.action_log;
  const logs = Array.isArray(raw) ? raw : [raw];
  if (!raw || logs.length === 0) {
    const err = new Error('action_log (object or non-empty array) is required');
    err.status = 400;
    throw err;
  }
  if (logs.length > MAX_BATCH) {
    const err = new Error(`batch too large: ${logs.length} action logs (max ${MAX_BATCH})`);
    err.status = 400;
    throw err;
  }
  const validationErrors = logs.flatMap((log, i) => validateActionLog(log, `action_log[${i}]`));
  if (validationErrors.length) {
    const err = new Error(`action_log schema validation failed: ${validationErrors.join('; ')}`);
    err.status = 400;
    throw err;
  }

  // 数据集注册（可选；未带则沿用最近注册的 metric/data）
  let meta = datasetMeta();
  if (body?.data_path) meta = registerDataset(body);

  // 幂等落盘 + 已知 job 复用
  const existingJobs = new Set();
  const freshIds = [];
  const ids = [];
  for (const log of logs) {
    const id = deriveActionLogId(log);
    ids.push(id);
    const file = join(actionLogDir(), `${id}.json`);
    if (!existsSync(file)) {
      writeJson(file, log);
      freshIds.push(id);
    }
    const knownJob = indexMap().get(id);
    if (knownJob) existingJobs.add(knownJob);
  }

  const allKnown = freshIds.length === 0 && existingJobs.size > 0;
  if (allKnown) {
    // 幂等重放：返回既有 job（不重复归因；store 侧天然 replay no-op）
    const jobId = existingJobs.has(indexMap().get(ids[0]))
      ? indexMap().get(ids[0])
      : [...existingJobs][0];
    const job = jobsMap().get(jobId);
    return {
      action_log_ids: ids,
      action_log_id: ids[0],
      attribution_job_id: jobId,
      status: job?.status ?? 'unknown',
      idempotent_replay: true,
    };
  }

  const job = newJob(ids);
  runAttribution(job, meta).catch((err) => {
    job.status = 'failed';
    job.error = err.message;
    job.finished_at = new Date().toISOString();
  });
  return {
    action_log_ids: ids,
    action_log_id: ids[0],
    attribution_job_id: job.job_id,
    status: job.status,
    idempotent_replay: false,
  };
}

/** GET /api/experience/actions/:id/status —— 按动作 id 查归因 job 状态。 */
export function actionStatus(actionLogId) {
  ensureLibrary();
  const jobId = indexMap().get(String(actionLogId));
  if (!jobId) return null;
  const job = jobsMap().get(jobId);
  if (!job) return null;
  return {
    action_log_id: String(actionLogId),
    attribution_job_id: jobId,
    status: job.status,
    created_at: job.created_at,
    finished_at: job.finished_at,
    error: job.error,
  };
}

/** GET /api/experience/attribution/:jobId —— 归因 job 视图（报告原样透传）。 */
export function attributionView(jobId) {
  ensureLibrary();
  const job = jobsMap().get(String(jobId));
  if (!job) return null;
  const data = {
    job_id: job.job_id,
    status: job.status,
    action_log_ids: job.action_log_ids,
    created_at: job.created_at,
    finished_at: job.finished_at,
    error: job.error,
    reports: [],
  };
  if (job.status === 'completed') {
    data.reports = job.reports.map(({ action_log_id, report_path }) => ({
      action_log_id,
      report_path,
      attribution: report_path ? readJsonSafe(report_path, null) : null,
    }));
  }
  return data;
}

/**
 * GET|POST /api/experience/recommend —— match_playbook.mjs recommend 同步包装。
 * body|query: fault_signature（anomalous_params 非空，否则 400）；top_k 缺省 5。
 * 返回 conclusions/recommendation.json 原文（recommendation_status /
 * match_scope / degradation_path / playbooks / recommendation_id）。
 */
export async function recommend({ fault_signature, top_k = 5 } = {}) {
  ensureLibrary();
  if (!fault_signature || typeof fault_signature !== 'object' ||
      !Array.isArray(fault_signature.anomalous_params) || fault_signature.anomalous_params.length === 0) {
    const err = new Error('fault_signature with non-empty anomalous_params is required');
    err.status = 400;
    throw err;
  }
  const reqId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const sigRel = `00_input/fs_${reqId}.json`;
  const outRel = `conclusions/recommendation_${reqId}.json`;
  writeJson(join(libraryDir(), sigRel), fault_signature);

  try {
    const proc = await nodeScript(
      join(SKILL_SCRIPTS, 'match_playbook.mjs'),
      ['recommend', '--run-dir', libraryDir(), '--signature', sigRel, '--out', outRel, '--top', String(Number(top_k) || 5)],
      { timeoutMs: 45000 },
    );
    if (Number(proc.code) !== 0) {
      const err = new Error(`match_playbook recommend failed: ${tail(proc.stdout + proc.stderr, 800)}`);
      err.status = 500;
      throw err;
    }
    const rec = readJsonSafe(join(libraryDir(), outRel), null);
    if (!rec) {
      const err = new Error('recommendation.json missing after recommend run');
      err.status = 500;
      throw err;
    }
    return rec;
  } finally {
    try { rmSync(join(libraryDir(), sigRel), { force: true }); } catch { /* best effort */ }
  }
}

/**
 * POST /api/experience/feedback —— experience_build.mjs feedback 同步包装。
 * result ∈ effective|ineffective|harmful|confirmed（否则 400）；
 * 返回该条经验更新后的佐证/反证计数与证据分级。
 */
export async function feedback({ experience_id, result, note = null } = {}) {
  ensureLibrary();
  if (!experience_id || typeof experience_id !== 'string') {
    const err = new Error('experience_id is required');
    err.status = 400;
    throw err;
  }
  if (!FEEDBACK_RESULTS.has(result)) {
    const err = new Error(`result must be one of ${[...FEEDBACK_RESULTS].join('|')}`);
    err.status = 400;
    throw err;
  }
  const args = ['feedback', '--run-dir', libraryDir(), '--chunk-id', experience_id, '--result', result];
  if (note) args.push('--note', String(note));
  const proc = await nodeScript(join(SKILL_SCRIPTS, 'experience_build.mjs'), args, { timeoutMs: 45000 });
  if (Number(proc.code) !== 0) {
    const err = new Error(`experience feedback failed: ${tail(proc.stdout + proc.stderr, 600)}`);
    err.status = Number(proc.code) === 2 ? 404 : 500;
    throw err;
  }
  return {
    experience_id,
    result,
    stdout_tail: tail(proc.stdout, 600).trim(),
    counters: feedbackCounters(experience_id),
    store_path: join(libraryDir(), '06_experience', 'tuning_experience.jsonl'),
  };
}

/**
 * feedback 后的计数镜像（06_experience/accumulated/state.json：counters 按
 * chunk_id 记 corroboration/refutation）+ 库内条目当前的证据分级。
 */
function feedbackCounters(chunkId) {
  const state = readJsonSafe(join(libraryDir(), '06_experience', 'accumulated', 'state.json'), null);
  const counter = state?.counters?.[chunkId] ?? null;
  let evidenceGrade = null;
  try {
    const lines = readFileSync(join(libraryDir(), '06_experience', 'tuning_experience.jsonl'), 'utf-8')
      .split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      const entry = JSON.parse(line);
      if (entry?.chunk_id === chunkId) { evidenceGrade = entry.evidence_grade ?? null; break; }
    }
  } catch { /* empty store */ }
  if (!counter) return evidenceGrade ? { evidence_grade: evidenceGrade } : null;
  return {
    corroboration: counter.corroboration ?? null,
    refutation: counter.refutation ?? null,
    evidence_grade: evidenceGrade,
  };
}

/** 运维/测试：经验库当前位置与库内条目数。 */
export function libraryInfo() {
  ensureLibrary();
  const store = join(libraryDir(), '06_experience', 'tuning_experience.jsonl');
  let n = 0;
  try {
    n = readFileSync(store, 'utf-8').split(/\r?\n/).filter(Boolean).length;
  } catch { /* empty store */ }
  let nLogs = 0;
  try { nLogs = readdirSync(actionLogDir()).filter((f) => f.endsWith('.json')).length; } catch { /* none */ }
  return {
    run_dir: libraryDir(),
    store_path: store,
    store_entries: n,
    ingested_action_logs: nLogs,
    dataset: datasetMeta(),
  };
}
