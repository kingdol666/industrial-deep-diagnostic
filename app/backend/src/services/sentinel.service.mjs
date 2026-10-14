// Sentinel Service — 产线哨兵（industrial-sentinel skill）的 HTTP 集成层业务逻辑。
//
// 包装三个真实 CLI（零业务计算，数字全部由脚本产出）：
//   - scripts/build_baseline.py  历史数据 → watch_baseline.json（异步任务）
//   - scripts/sentinel.py watch  整窗批筛（异步任务；exit 0 ok / 1 findings /
//                                2 undetermined / 3 gate-fail）
//   - scripts/sentinel_fast.py   增量快筛（同步 ≤15s；无基线 exit 2 拒跑）
//
// 基线登记表：POST /baseline 成功后按产线名登记；screen/watch 未显式给
// baseline_path 时回落到最近登记的基线（插件 sentinel_screen 的“缺省用该
// 产线已登记基线”语义）。登记表持久化到 <root>/sentinel/baselines/registry.json。

import { join } from 'path';
import { existsSync, statSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  closedloopRoot, ensureDir, readJsonSafe, writeJson, resolveDataFile, resolveDataDirectory,
  TaskTable, uvPython, uvPythonStreaming, tail, resolveServerPath,
} from './closedloop.util.mjs';

const SKILL_SCRIPTS = '.claude/skills/industrial-sentinel/scripts';

function root() { return join(closedloopRoot(), 'sentinel'); }
function registryPath() { return join(root(), 'baselines', 'registry.json'); }

const watchTasks = new TaskTable();
const baselineTasks = new TaskTable();

// ── 基线登记表 ───────────────────────────────────────────────────────────

function loadRegistry() {
  return readJsonSafe(registryPath(), { lines: {}, last_line: null }) || { lines: {}, last_line: null };
}

function saveRegistry(reg) {
  writeJson(registryPath(), reg);
}

function registerBaseline(line, entry) {
  const reg = loadRegistry();
  reg.lines[String(line)] = { ...entry, registered_at: new Date().toISOString() };
  reg.last_line = String(line);
  saveRegistry(reg);
}

export function getBaselineFor(line = null, explicitPath = null) {
  if (explicitPath) {
    return existsSync(explicitPath) ? explicitPath : null;
  }
  const reg = loadRegistry();
  const key = line && reg.lines[line] ? line : reg.last_line;
  const entry = key ? reg.lines[key] : null;
  return entry && existsSync(entry.baseline_path) ? entry.baseline_path : null;
}

// ── 公共校验 ─────────────────────────────────────────────────────────────

const FOLDER_PREPROCESSOR = join(PROJECT_ROOT, '.claude', 'skills', 'industrial-data-preprocessor', 'scripts', 'data_preprocessor.py');

/** 目录输入 → 自适应预处理 → 主时序规范表（含 manifest 落盘）。 */
async function stageFolderPrimary(dataAbs, stagingDir, name) {
  const proc = await uvPythonStreaming(FOLDER_PREPROCESSOR, [
    '--data-path', dataAbs,
    '--output', stagingDir,
    '--name', name,
    '--single-primary',
    '--recursive',
  ], { timeoutMs: 300000 });
  const report = readJsonSafe(join(stagingDir, 'preprocessing_report.json'), null);
  if (proc.code !== 0 || !report || report.status !== 'ok') {
    throw new Error(`folder preprocessing failed: ${report?.status || tail(proc.stderr) || tail(proc.stdout)}`);
  }
  const canonical = join(stagingDir, 'preprocessed_data.csv');
  if (!existsSync(canonical)) {
    throw new Error('folder preprocessing produced no canonical table');
  }
  writeFileSync(join(stagingDir, 'input_manifest.json'), JSON.stringify({
    manifest_version: 'sentinel-folder-input/1.0',
    source_directory: String(dataAbs),
    selected_table: report.selected_table,
    source_dispositions: report.source_dispositions || [],
    merge_exclusions: report.merge_exclusions || [],
    context_files: report.context_files || [],
    skipped_files: report.skipped_files || [],
  }, null, 2));
  return canonical;
}

function requireExistingFile(value, name, { optional = false, extensions = ['.csv', '.tsv', '.tab', '.parquet', '.pq'] } = {}) {
  if (value === undefined || value === null || value === '') {
    if (optional) return null;
    const err = new Error(`${name} is required`);
    err.status = 400;
    throw err;
  }
  return resolveDataFile(value, name, extensions);
}

/** 读快筛/批筛产出的 alert.json，裁成 HTTP 摘要（原文件路径一并回传）。 */
function alertSummary(alertPath, exitCode, extra = {}) {
  const alert = alertPath && existsSync(alertPath) ? readJsonSafe(alertPath, null) : null;
  if (!alert) {
    return {
      exit_code: exitCode, alert_status: null,
      status: exitCode === 0 ? 'ok' : 'unknown',
      alerts: [], alert_path: alertPath ?? null, ...extra,
    };
  }
  return {
    exit_code: exitCode,
    status: alert.status ?? null,
    alert_status: alert.status ?? null,
    mode: alert.mode ?? null,
    group_scope: alert.group_scope ?? null,
    n_rows: alert.source?.n_rows ?? null,
    alerts: alert.alerts ?? [],
    n_alerts: (alert.alerts ?? []).length,
    alert_path: alertPath,
    baseline_mode: alert.baseline?.mode ?? null,
    checks_summary: alert.checks_summary ?? null,
    ...extra,
  };
}

// ── fast-screen（同步）──────────────────────────────────────────────────

/**
 * POST /api/sentinel/screen —— sentinel_fast.py 同步包装（≤15s）。
 * 返回 exit_code + alert 摘要；无可用基线时不spawn，直接 exit_code=2 语义。
 * fast_state.json 由本服务按基线路径派生托管（ring buffer 跨调用连续）。
 */
export async function screen({ data_path, baseline_path = null, time_col = null, group_col = null }) {
  const dataAbs = requireExistingFile(data_path, 'data_path');
  const baselineAbs = baseline_path
    ? resolveDataFile(baseline_path, 'baseline_path', ['.json'])
    : getBaselineFor(null, null);

  if (!baselineAbs) {
    // skill 契约：fast 无基线 exit 2 拒跑（指引先建基线）
    return {
      exit_code: 2,
      status: 'undetermined',
      alerts: [],
      message: 'no baseline available — register one first via POST /api/sentinel/baseline (build_baseline.py), then re-screen',
    };
  }

  const stateKey = createHash('sha1').update(baselineAbs).digest('hex').slice(0, 12);
  const statePath = join(root(), 'fast_state', `${stateKey}.json`);
  const outDir = ensureDir(join(root(), 'screens', `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`));
  const outPath = join(outDir, 'fast_alert.json');

  const args = [
    '--data', dataAbs,
    '--state', statePath,
    '--baseline', baselineAbs,
    '--out', outPath,
  ];
  if (group_col) args.push('--group', String(group_col));

  const started = Date.now();
  const proc = await uvPython(join(SKILL_SCRIPTS, 'sentinel_fast.py'), args, { timeoutMs: 12000 });
  if (proc.timedOut) {
    const err = new Error('sentinel_fast exceeded 12s — aborted');
    err.status = 504;
    throw err;
  }
  const code = Number(proc.code ?? -1);
  if (code === 2) {
    return {
      exit_code: 2,
      status: 'undetermined',
      alerts: [],
      message: tail(proc.stdout + proc.stderr, 800).trim() || 'sentinel_fast refused (exit 2)',
      baseline_path: baselineAbs,
    };
  }
  if (code === -1) {
    const err = new Error(`sentinel_fast failed to launch: ${tail(proc.stderr, 400)}`);
    err.status = 500;
    throw err;
  }
  return alertSummary(outPath, code, {
    report: null,
    stdout_tail: tail(proc.stdout, 600),
    duration_ms: Date.now() - started,
    baseline_path: baselineAbs,
    data_path: dataAbs,
  });
}

// ── watch（异步任务）────────────────────────────────────────────────────

/**
 * POST /api/sentinel/tasks —— sentinel.py watch 异步包装，提交即返 task_id。
 * 完成后 GET /api/sentinel/tasks/:taskId 取 alert.json / watch_report.md 路径。
 */
export function submitWatch(body) {
  const {
    data_path = null, data_dir = null, input_kind = null,
    baseline_path = null, time_col = null, group_col = null, out_dir = null,
  } = body ?? {};
  const resolvedKind = data_dir ? 'directory' : 'file';
  if (Boolean(data_path) === Boolean(data_dir) || (input_kind && input_kind !== resolvedKind)) {
    const err = new Error(`provide exactly one of data_path or data_dir with matching input_kind '${resolvedKind}'`);
    err.status = 400;
    throw err;
  }
  const dataAbs = data_dir
    ? resolveDataDirectory(data_dir, 'data_dir')
    : requireExistingFile(data_path, 'data_path');
  const baselineAbs = baseline_path ? resolveDataFile(baseline_path, 'baseline_path', ['.json']) : getBaselineFor(null, null);

  const task = watchTasks.create({ kind: 'sentinel_watch', prefix: 'SNW' });
  const outDir = out_dir ? ensureDir(String(out_dir)) : ensureDir(join(root(), 'watch', task.task_id));

  // 异步前先落 queued 任务（submit 后台执行；HTTP 立即返回）
  (async () => {
    let inputData = dataAbs;
    let input_manifest_path = null;
    if (data_dir) {
      inputData = await stageFolderPrimary(dataAbs, ensureDir(join(outDir, '00_input')), task.task_id);
      input_manifest_path = join(outDir, '00_input', 'input_manifest.json');
    }
    const args = ['watch', '--data', inputData, '--out-dir', outDir];
    if (baselineAbs) args.push('--baseline', baselineAbs);
    if (time_col) args.push('--time-col', String(time_col));
    if (group_col) args.push('--group-col', String(group_col));
    const proc = await uvPython(join(SKILL_SCRIPTS, 'sentinel.py'), args, { timeoutMs: 180000 });
    const code = Number(proc.code ?? -1);
    const view = alertSummary(join(outDir, 'alert.json'), code, {
      data_path: inputData,
      data_dir: data_dir ? dataAbs : null,
      input_manifest_path,
      baseline_path: baselineAbs,
      report_path: existsSync(join(outDir, 'watch_report.md')) ? join(outDir, 'watch_report.md') : null,
      stdout_tail: tail(proc.stdout, 800),
    });
    watchTasks.markDone(task.task_id, {
      code,
      // watch 退出码语义：0 ok / 1 findings 都算完成任务（告警是有效结果）；
      // 2 undetermined / 3 gate-fail 才是 failed
      status: code === 0 || code === 1 ? 'completed' : 'failed',
      error: code === 2 || code === 3 || code < 0 ? tail(proc.stdout + proc.stderr, 800) : null,
      result: view,
    });
  })().catch((err) => watchTasks.markDone(task.task_id, { code: -1, error: err.message }));

  return {
    task_id: task.task_id,
    status: task.status,
    poll: `GET /api/sentinel/tasks/${task.task_id}`,
    out_dir: outDir,
    baseline_used: baselineAbs,
  };
}

/** GET /api/sentinel/tasks/:taskId —— 任务视图（status + alerts + 产物路径）。
 * 注意 status 恒为任务生命周期状态（queued/running/completed/failed，插件的
 * sweep 以此判定终态）；alert 本体的 status 以 alert_status 字段透传。 */
export function watchTaskView(taskId) {
  const t = watchTasks.get(taskId);
  if (!t) return null;
  const { status: alertStatus, ...resultFields } = t.result ?? {};
  return {
    task_id: t.task_id,
    kind: t.kind,
    status: t.status,
    alert_status: alertStatus ?? null,
    created_at: t.created_at,
    finished_at: t.finished_at,
    exit_code: t.exit_code,
    error: t.error,
    ...resultFields,
  };
}

// ── baseline 构建（异步任务）────────────────────────────────────────────

/**
 * POST /api/sentinel/baseline —— build_baseline.py 异步包装。
 * 成功后按 line 登记基线（后续 screen/watch 缺省回落）。
 */
export function submitBaseline({ line, history_csv = null, data_dir = null, input_kind = null, doe_run_dir = null, time_col = null, group_col = null }) {
  if (!line || typeof line !== 'string') {
    const err = new Error('line is required (产线/机组标识)');
    err.status = 400;
    throw err;
  }
  const resolvedKind = data_dir ? 'directory' : 'file';
  if (Boolean(history_csv) === Boolean(data_dir) || (input_kind && input_kind !== resolvedKind)) {
    const err = new Error(`provide exactly one of history_csv or data_dir with matching input_kind '${resolvedKind}'`);
    err.status = 400;
    throw err;
  }
  let historyAbs = data_dir
    ? resolveDataDirectory(data_dir, 'data_dir')
    : requireExistingFile(history_csv, 'history_csv', { extensions: ['.csv', '.tsv', '.tab', '.parquet', '.pq'] });
  const doeDir = doe_run_dir ? resolveServerPath(doe_run_dir) : null;
  if (doe_run_dir && (!doeDir || !existsSync(doeDir) || !statSync(doeDir).isDirectory())) {
    const err = new Error(`doe_run_dir must be an existing directory: ${doe_run_dir}`);
    err.status = 400;
    throw err;
  }

  const task = baselineTasks.create({ kind: 'sentinel_baseline', prefix: 'SNB' });
  const outPath = join(root(), 'baselines', line, 'watch_baseline.json');
  ensureDir(join(outPath, '..'));
  const stagingDir = data_dir ? ensureDir(join(root(), 'baselines', line, '_staging')) : null;

  (async () => {
    if (data_dir) {
      historyAbs = await stageFolderPrimary(dataAbs, stagingDir, line);
    }
    const args = ['--history-csv', historyAbs, '--out', outPath];
    if (doeDir) args.push('--doe-run-dir', doeDir);
    if (time_col) args.push('--time-col', String(time_col));
    if (group_col) args.push('--group-col', String(group_col));
    const proc = await uvPython(join(SKILL_SCRIPTS, 'build_baseline.py'), args, { timeoutMs: 120000 });
    const code = Number(proc.code ?? -1);
    if (code === 0 && existsSync(outPath)) {
      registerBaseline(line, { baseline_path: outPath, history_csv: historyAbs, doe_run_dir: doeDir });
    }
    baselineTasks.markDone(task.task_id, {
      code,
      error: code === 0 ? null : tail(proc.stdout + proc.stderr, 800),
      result: {
        line,
        baseline_path: existsSync(outPath) ? outPath : null,
        history_csv: historyAbs,
        data_dir: data_dir ? dataAbs : null,
        doe_run_dir,
        stdout_tail: tail(proc.stdout, 600),
      },
    });
  })().catch((err) => baselineTasks.markDone(task.task_id, { code: -1, error: err.message }));

  return {
    task_id: task.task_id,
    status: task.status,
    line,
    poll: `GET /api/sentinel/tasks/${task.task_id}`,
  };
}

/** 基线任务复用 GET /tasks/:taskId 轮询（插件 sentinel_baseline 即此语义）。 */
export function anyTaskView(taskId) {
  return watchTaskView(taskId) || baselineTaskView(taskId);
}

function baselineTaskView(taskId) {
  const t = baselineTasks.get(taskId);
  if (!t) return null;
  const { status: alertStatus = null, ...resultFields } = t.result ?? {};
  return {
    task_id: t.task_id,
    kind: t.kind,
    status: t.status,
    alert_status: alertStatus,
    created_at: t.created_at,
    finished_at: t.finished_at,
    exit_code: t.exit_code,
    error: t.error,
    ...resultFields,
    alert_path: null,
    report_path: null,
  };
}

/** 测试与运维：列出已登记基线。 */
export function listBaselines() {
  return loadRegistry();
}
