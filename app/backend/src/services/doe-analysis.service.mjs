// DOE/工况分析 Service — industrial-doe-analyzer skill 的 HTTP 集成层。
//
// 包装真实 CLI：scripts/analyze.py <run|all> --run-dir R（自动判别 designed /
// observational，7 产物/模式，全部数字由 numpy/scipy 产出），随后跑该 skill 自带
// quality_gate.mjs。实时日志经 makeJobLog → SSE（/tasks/:id/stream）。
// 产物落 <root>/doe_runs/<task_id>/；report.html 与 conclusions 经
// /workspace-files 静态路由打开。

import { join, relative, isAbsolute } from 'path';
import { existsSync, readdirSync, writeFileSync, copyFileSync } from 'fs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  closedloopRoot, ensureDir, readJsonSafe,
  TaskTable, uvPythonStreaming, nodeScript, tail, resolveServerPath, makeJobLog,
} from './closedloop.util.mjs';

const SKILL_SCRIPTS = '.claude/skills/industrial-doe-analyzer/scripts';

function root() { return join(closedloopRoot(), 'doe_runs'); }

const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace');
function toWebUrl(absPath) {
  if (!absPath) return null;
  const rel = relative(WORKSPACE_DIR, absPath);
  if (!rel || rel.startsWith('..') || isAbsolute(rel)) return null;
  return `/workspace-files/${rel.split('\\').join('/')}`;
}

const doeTasks = new TaskTable();
const taskLogs = new Map();

function jobLogFor(taskId) {
  if (!taskLogs.has(taskId)) taskLogs.set(taskId, makeJobLog());
  return taskLogs.get(taskId);
}

export function getTaskLog(taskId) {
  return taskLogs.get(taskId) ?? null;
}

function resolveInputPath(value, name) {
  if (value === undefined || value === null || value === '') {
    const err = new Error(`${name} is required (got ${value === undefined ? 'undefined' : JSON.stringify(value)})`);
    err.status = 400;
    throw err;
  }
  const resolved = resolveServerPath(String(value));
  if (!resolved || !existsSync(resolved)) {
    const err = new Error(`${name}: file not found: ${value}`);
    err.status = 400;
    throw err;
  }
  if (!resolved.startsWith(PROJECT_ROOT)) {
    const err = new Error(`${name}: path outside project root is not allowed: ${value}`);
    err.status = 400;
    throw err;
  }
  return resolved;
}

function collectArtifacts(runDir) {
  const keep = [];
  const walk = (dir, prefix) => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      const rel = join(prefix, name);
      if (['01_profile', '02_analysis', '03_figures', 'conclusions'].includes(name) && !prefix) {
        walk(full, name);
      } else if (prefix && /\.(json|html|png|md)$/i.test(name)) {
        keep.push(rel.split('\\').join('/'));
      } else if (!prefix && /^report\.html$|^run_manifest\.json$/i.test(name)) {
        keep.push(rel.split('\\').join('/'));
      }
    }
  };
  try { walk(runDir, ''); } catch { /* dir vanished */ }
  return keep.sort();
}

export function submitDoeAnalysis(body = {}) {
  const {
    data_path, time_col = null, context = null, mode = null, scene = null,
  } = body;
  const dataAbs = resolveInputPath(data_path, 'data_path');

  const task = doeTasks.create({ kind: 'doe-analysis', prefix: 'DOE' });
  doeTasks.markRunning(task.task_id);
  const log = jobLogFor(task.task_id);

  (async () => {
    const runDir = join(root(), task.task_id);
    ensureDir(join(runDir, '00_input'));
    log.log(`[hub] 提交 DOE/工况分析任务 ${task.task_id}（data=${data_path}）`);
    copyFileSync(dataAbs, join(runDir, '00_input', 'data.csv'));
    // analyze.py 不收 --time-col：时间列等偏好统一走 analysis_context.json
    const ctx = { data_path: '00_input/data.csv' };
    if (time_col) ctx.time_col = String(time_col);
    if (scene) ctx.scene = String(scene);
    if (context && typeof context === 'object') Object.assign(ctx, context);
    writeFileSync(join(runDir, '00_input', 'analysis_context.json'),
      JSON.stringify(ctx, null, 2));

    // all = profile + run + report（report 阶段渲染 report.html）
    const analyzer = await uvPythonStreaming(join(SKILL_SCRIPTS, 'analyze.py'),
      ['all', '--run-dir', runDir],
      { timeoutMs: 600000, onLine: (line, stream) => log.log(line, stream) });
    log.log(`[hub] analyze.py 退出码 ${analyzer.code}`);
    if (analyzer.code !== 0) {
      throw new Error(`doe analyze failed (${analyzer.code}): `
        + `${tail(analyzer.stderr) || tail(analyzer.stdout)}`);
    }

    const conclusion = readJsonSafe(join(runDir, 'conclusions', 'doe_conclusion.json'), null);
    const recommendations = readJsonSafe(join(runDir, 'conclusions', 'recommendations.json'), null);
    const correlation = readJsonSafe(join(runDir, '02_analysis', 'correlation_report.json'), null);
    const effectTable = readJsonSafe(join(runDir, '02_analysis', 'effect_table.json'), null);

    log.log('[hub] 质量门禁…');
    // doe 门禁的默认 skill/shared 路径按其脚本位置相对解析；显式传绝对路径
    const gate = await nodeScript(join(SKILL_SCRIPTS, 'quality_gate.mjs'), [
      runDir,
      '--skill-path', resolveServerPath('.claude/skills/industrial-doe-analyzer'),
      '--shared-path', resolveServerPath('.claude/shared'),
    ], { timeoutMs: 120000 });
    let gate_status = gate.code === 0 ? 'pass' : `fail(exit ${gate.code})`;
    log.log(`[hub] 门禁 ${gate_status}`);
    if (gate.code !== 0) {
      throw new Error(`doe quality gate failed: ${tail(gate.stdout) || tail(gate.stderr)}`);
    }

    const reportHtml = join(runDir, 'report.html');
    log.log('[hub] 任务完成');
    doeTasks.markDone(task.task_id, {
      code: 0,
      status: 'completed',
      result: {
        run_dir: runDir,
        outcome: 'ok',
        mode: conclusion?.mode ?? conclusion?.analysis_mode ?? null,
        scene: scene ?? null,
        report_path: existsSync(reportHtml) ? reportHtml : null,
        report_url: toWebUrl(reportHtml),
        conclusions: {
          doe_conclusion: conclusion,
          recommendations,
          correlation_report: correlation,
          effect_table: effectTable,
        },
        artifacts: collectArtifacts(runDir),
      },
    });
  })().catch((err) => {
    jobLogFor(task.task_id).log(`[hub] 失败：${String(err.message || err)}`, 'stderr');
    doeTasks.markDone(task.task_id, { code: -1, status: 'failed', error: String(err.message || err) });
  });

  return { task_id: task.task_id, status: task.status, kind: task.kind };
}

export function doeTaskView(taskId) {
  const task = doeTasks.get(taskId);
  if (!task) return null;
  const result = task.result || {};
  const conclusions = result.conclusions || null;
  const view = { ...task, result: { ...result } };
  if (conclusions) {
    view.result.conclusions_summary = {
      mode: result.mode ?? conclusions.doe_conclusion?.mode ?? null,
      headline: conclusions.doe_conclusion?.headline
        ?? conclusions.doe_conclusion?.summary ?? null,
      n_windows: (conclusions.recommendations?.operating_windows ?? []).length,
      n_findings: (conclusions.correlation_report?.pairs ?? []).length
        || (conclusions.effect_table?.effects ?? []).length,
    };
    delete view.result.conclusions; // 大 JSON 不进任务视图，走 /runs/:id 全量取
  }
  return view;
}

export function listDoeRuns() {
  const dir = root();
  if (!existsSync(dir)) return [];
  const runs = [];
  for (const name of readdirSync(dir)) {
    const conclusion = readJsonSafe(join(dir, name, 'conclusions', 'doe_conclusion.json'), null);
    if (!conclusion) continue;
    const reportHtml = join(dir, name, 'report.html');
    runs.push({
      task_id: name,
      mode: conclusion.mode ?? null,
      scene: conclusion.scene?.name ?? null,
      headline: conclusion.headline ?? conclusion.summary ?? null,
      generated_at: conclusion.generated_at ?? null,
      report_url: existsSync(reportHtml) ? toWebUrl(reportHtml) : null,
      run_dir: join(dir, name),
    });
  }
  runs.sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
  return runs;
}

export function getDoeRun(taskId) {
  const runDir = join(root(), taskId);
  const conclusion = readJsonSafe(join(runDir, 'conclusions', 'doe_conclusion.json'), null);
  if (!conclusion) return null;
  const reportHtml = join(runDir, 'report.html');
  return {
    task_id: taskId,
    report_url: existsSync(reportHtml) ? toWebUrl(reportHtml) : null,
    run_dir: runDir,
    conclusions: {
      doe_conclusion: conclusion,
      recommendations: readJsonSafe(join(runDir, 'conclusions', 'recommendations.json'), null),
      correlation_report: readJsonSafe(join(runDir, '02_analysis', 'correlation_report.json'), null),
      effect_table: readJsonSafe(join(runDir, '02_analysis', 'effect_table.json'), null),
    },
    artifacts: collectArtifacts(runDir),
  };
}

export { doeTasks };
