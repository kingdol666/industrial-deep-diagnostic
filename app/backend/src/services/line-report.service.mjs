// Line Stability Report Service — 产线运行稳定性报告（industrial-line-stability-report
// skill）的 HTTP 集成层业务逻辑。
//
// 包装三个真实 CLI（零业务计算，数字全部由脚本产出）：
//   - scripts/stability_analyzer.py analyze  确定性稳定性评估（exit 0 ok / 1
//                                            findings / 2 not_assessable / 3 bad input）
//   - scripts/report_builder.py              JSON → 自包含中文 HTML 落地页
//   - scripts/quality_gate.mjs               交付门禁（exit 0 才算完成）
//
// 任务产物：<root>/line_reports/<task_id>/line_report/*；HTML 经 /workspace-files
// 静态路由直接可开。协同输入（sentinel 基线 / tuning-memory action_log /
// doe-analyzer run）全部可选，缺席由脚本侧降级记录。

import { join, relative, isAbsolute } from 'path';
import { existsSync, mkdirSync, writeFileSync, readdirSync } from 'fs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  closedloopRoot, ensureDir, readJsonSafe,
  TaskTable, uvPythonStreaming, uvPython, nodeScript, tail, resolveServerPath,
  makeJobLog,
} from './closedloop.util.mjs';

const SKILL_SCRIPTS = '.claude/skills/industrial-line-stability-report/scripts';

function root() { return join(closedloopRoot(), 'line_reports'); }

// Map an absolute path under <repo>/workspace to a /workspace-files web URL
// (null when CLOSEDLOOP_DATA_DIR points outside the static root).
const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace');
function toWebUrl(absPath) {
  if (!absPath) return null;
  const rel = relative(WORKSPACE_DIR, absPath);
  if (!rel || rel.startsWith('..') || isAbsolute(rel)) return null;
  return `/workspace-files/${rel.split('\\').join('/')}`;
}

const reportTasks = new TaskTable();
const taskLogs = new Map(); // taskId -> makeJobLog（SSE 实时流 + 回放）

function jobLogFor(taskId) {
  if (!taskLogs.has(taskId)) taskLogs.set(taskId, makeJobLog());
  return taskLogs.get(taskId);
}

export function getTaskLog(taskId) {
  return taskLogs.get(taskId) ?? null;
}

// ── 校验 ─────────────────────────────────────────────────────────────────

function resolveInputPath(value, name, { optional = false } = {}) {
  if (value === undefined || value === null || value === '') {
    if (optional) return null;
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

// ── 任务提交 ─────────────────────────────────────────────────────────────

export function submitReport(body = {}) {
  const {
    data_path, line_id = null, product = null, time_col = null,
    start = null, end = null, baseline_path = null, action_log = null,
    doe_run_dir = null, spec_limits = null, weights = null,
    parameter_cols = null, inspection_cols = null, metric = null,
    ontology_path = null, scene = null, doe_auto = false,
  } = body;

  const dataAbs = resolveInputPath(data_path, 'data_path');
  const baselineAbs = baseline_path ? resolveInputPath(baseline_path, 'baseline_path') : null;
  const doeAbs = doe_run_dir ? resolveInputPath(doe_run_dir, 'doe_run_dir') : null;
  const ontologyAbs = ontology_path ? resolveInputPath(ontology_path, 'ontology_path') : null;
  if (doeAbs && !existsSync(join(doeAbs, 'conclusions', 'recommendations.json'))) {
    const err = new Error('doe_run_dir has no conclusions/recommendations.json — '
      + 'run industrial-doe-analyzer first');
    err.status = 400;
    throw err;
  }

  const task = reportTasks.create({ kind: 'line-report', prefix: 'LSR' });
  reportTasks.markRunning(task.task_id);

  (async () => {
    const runDir = join(root(), task.task_id);
    const inputDir = ensureDir(join(runDir, '00_input'));
    const outDir = join(runDir, 'line_report');

    const context = {};
    if (dataAbs) context.data_path = dataAbs;
    if (line_id) context.line_id = String(line_id);
    if (product) context.product = String(product);
    if (time_col) context.time_col = String(time_col);
    if (start) context.start = String(start);
    if (end) context.end = String(end);
    if (baselineAbs) context.baseline_path = baselineAbs;
    if (ontologyAbs) context.ontology_path = ontologyAbs;
    if (scene) context.scene = String(scene);
    if (spec_limits && typeof spec_limits === 'object') context.spec_limits = spec_limits;
    if (weights && typeof weights === 'object') context.weights = weights;
    if (Array.isArray(parameter_cols) && parameter_cols.length) context.parameter_cols = parameter_cols;
    if (Array.isArray(inspection_cols) && inspection_cols.length) context.inspection_cols = inspection_cols;
    writeFileSync(join(inputDir, 'report_context.json'), JSON.stringify(context, null, 2));

    let actionLogPath = null;
    if (action_log) {
      if (typeof action_log === 'string' && existsSync(resolveServerPath(action_log))) {
        actionLogPath = resolveInputPath(action_log);
      } else {
        actionLogPath = join(inputDir, 'action_log.json');
        writeFileSync(actionLogPath, JSON.stringify(action_log, null, 2));
      }
    }

    const log = jobLogFor(task.task_id);
    log.log(`[hub] 提交产线稳定性报告任务 ${task.task_id}（data=${data_path}）`);
    const args = ['analyze', '--run-dir', runDir, '--out-dir', outDir];
    if (time_col) args.push('--time-col', String(time_col));
    if (metric) args.push('--metric', String(metric));
    if (baselineAbs) args.push('--baseline', baselineAbs);
    if (actionLogPath) args.push('--action-log', actionLogPath);
    if (doeAbs) args.push('--doe-run-dir', doeAbs);
    if (doe_auto) args.push('--doe-auto');

    const analyzer = await uvPythonStreaming(join(SKILL_SCRIPTS, 'stability_analyzer.py'),
      args, {
        timeoutMs: 300000,
        onLine: (line, stream) => log.log(line, stream),
      });
    log.log(`[hub] 分析器退出码 ${analyzer.code}`);
    if (analyzer.code === 3 || analyzer.code < 0) {
      throw new Error(`stability analyzer failed (${analyzer.code}): ${tail(analyzer.stderr) || tail(analyzer.stdout)}`);
    }
    const report = readJsonSafe(join(outDir, 'stability_report.json'), null);
    if (!report) {
      throw new Error(`analyzer produced no stability_report.json (exit ${analyzer.code}) `
        + `stdout: ${tail(analyzer.stdout, 600)} stderr: ${tail(analyzer.stderr, 600)}`);
    }

    if (report.status === 'not_assessable' || analyzer.code === 2) {
      log.log('[hub] 数据不足以评估（not_assessable）——如实交付，不评分');
      reportTasks.markDone(task.task_id, {
        code: 2,
        status: 'completed',
        result: { run_dir: runDir, report_path: join(outDir, 'stability_report.json'),
                  outcome: 'not_assessable', report },
      });
      return;
    }

    log.log('[hub] 构建 HTML + Markdown 报告…');
    const builder = await uvPythonStreaming(join(SKILL_SCRIPTS, 'report_builder.py'), [
      '--report', join(outDir, 'stability_report.json'),
      '--charts', join(outDir, 'charts.json'),
      '--out', join(outDir, 'line_stability_report.html'),
      '--md', join(outDir, 'line_stability_report.md'),
    ], { timeoutMs: 120000, onLine: (line, stream) => log.log(line, stream) });
    if (builder.code !== 0) {
      throw new Error(`report builder failed: ${tail(builder.stderr) || tail(builder.stdout)}`);
    }

    log.log('[hub] 质量门禁…');
    const gate = await nodeScript(join(SKILL_SCRIPTS, 'quality_gate.mjs'),
      [join(outDir, 'stability_report.json'), outDir], { timeoutMs: 120000 });
    if (gate.code !== 0) {
      throw new Error(`quality gate failed: ${tail(gate.stdout) || tail(gate.stderr)}`);
    }
    log.log('[hub] 门禁通过，任务完成');

    const mdPath = join(outDir, 'line_stability_report.md');
    reportTasks.markDone(task.task_id, {
      code: analyzer.code, // 0 ok | 1 findings（均视为完成）
      status: 'completed',
      result: {
        run_dir: runDir,
        outcome: analyzer.code === 0 ? 'ok' : 'findings',
        report_path: join(outDir, 'stability_report.json'),
        html_path: join(outDir, 'line_stability_report.html'),
        html_url: toWebUrl(join(outDir, 'line_stability_report.html')),
        md_path: existsSync(mdPath) ? mdPath : null,
        md_url: existsSync(mdPath) ? toWebUrl(mdPath) : null,
        report,
      },
    });
  })().catch((err) => {
    jobLogFor(task.task_id).log(`[hub] 失败：${String(err.message || err)}`, 'stderr');
    reportTasks.markDone(task.task_id, { code: -1, status: 'failed', error: String(err.message || err) });
  });

  return { task_id: task.task_id, status: task.status, kind: task.kind };
}

export function reportTaskView(taskId) {
  const task = reportTasks.get(taskId);
  if (!task) return null;
  const result = task.result || {};
  const report = result.report || null;
  return {
    ...task,
    result: report
      ? { ...result, report: undefined,
          report_summary: {
            report_id: report.report_id, status: report.status,
            score: report.conclusion?.score ?? null,
            grade: report.conclusion?.grade ?? null,
            label: report.conclusion?.label ?? null,
            statement: report.conclusion?.statement ?? '',
            n_parameters_assessed: report.conclusion?.n_parameters_assessed ?? 0,
            findings_by_severity: report.conclusion?.findings_by_severity ?? null,
            parameters: (report.parameters || []).map((p) => ({
              name: p.name, role: p.role, score: p.score ?? null,
              n_violation_points: p.n_violation_points,
            })),
          },
          findings: report.findings || [] }
      : result,
  };
}

// ── 报告目录 ─────────────────────────────────────────────────────────────

export function listReports() {
  const dir = root();
  if (!existsSync(dir)) return [];
  const runs = [];
  for (const name of readdirSync(dir)) {
    const repPath = join(dir, name, 'line_report', 'stability_report.json');
    const rep = readJsonSafe(repPath, null);
    if (!rep) continue;
    runs.push({
      task_id: name,
      report_id: rep.report_id,
      line_id: rep.line?.line_id ?? null,
      status: rep.status,
      score: rep.conclusion?.score ?? null,
      grade: rep.conclusion?.grade ?? null,
      label: rep.conclusion?.label ?? null,
      statement: rep.conclusion?.statement ?? '',
      generated_at: rep.generated_at,
      html_url: toWebUrl(join(dir, name, 'line_report', 'line_stability_report.html')),
      report_path: repPath,
    });
  }
  runs.sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
  return runs;
}

export function getReport(taskId) {
  const repPath = join(root(), taskId, 'line_report', 'stability_report.json');
  const rep = readJsonSafe(repPath, null);
  if (!rep) return null;
  return {
    task_id: taskId,
    html_url: toWebUrl(join(root(), taskId, 'line_report', 'line_stability_report.html')),
    report_path: repPath,
    report,
  };
}

export { reportTasks };
