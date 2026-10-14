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

import { createHash } from 'crypto';
import { join, relative, isAbsolute, dirname, sep } from 'path';
import { existsSync, mkdirSync, writeFileSync, readdirSync, readFileSync, statSync } from 'fs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  closedloopRoot, ensureDir, readJsonSafe, resolveDataFile, resolveDataDirectory,
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
    const err = new Error(`${name} is required`);
    err.status = 400;
    throw err;
  }
  if (name === 'data_path') {
    return resolveDataFile(value, name, ['.csv', '.tsv', '.xlsx', '.xls', '.parquet', '.json']);
  }
  if (name === 'doe_run_dir') return resolveDataDirectory(value, name);
  if (name === 'baseline_path') return resolveDataFile(value, name, ['.json']);
  if (name === 'ontology_path') return resolveDataFile(value, name, ['.json']);
  const resolved = resolveServerPath(String(value));
  if (!existsSync(resolved)) {
    const err = new Error(`${name}: path not found: ${value}`);
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
    data_path = null, data_dir = null, input_kind = null,
    line_id = null, product = null, time_col = null,
    start = null, end = null, baseline_path = null, action_log = null,
    doe_run_dir = null, spec_limits = null, weights = null,
    parameter_cols = null, inspection_cols = null, metric = null,
    ontology_path = null, scene = null, doe_auto = false,
  } = body;

  if (Boolean(data_path) === Boolean(data_dir) || (input_kind && input_kind !== (data_dir ? 'directory' : 'file'))) {
    const err = new Error('provide exactly one of data_path or data_dir with a matching input_kind');
    err.status = 400;
    throw err;
  }
  const resolvedKind = data_dir ? 'directory' : 'file';
  if (input_kind && input_kind !== resolvedKind) {
    const err = new Error(`input_kind must be '${resolvedKind}' for the selected input`);
    err.status = 400;
    throw err;
  }
  const dataAbs = data_dir
    ? resolveDataDirectory(data_dir, 'data_dir')
    : resolveDataFile(data_path, 'data_path', ['.csv', '.tsv', '.xlsx', '.xls', '.parquet', '.json']);
  const baselineAbs = baseline_path ? resolveInputPath(baseline_path, 'baseline_path') : null;
  const doeAbs = doe_run_dir ? resolveInputPath(doe_run_dir, 'doe_run_dir') : null;
  let ontologyAbs = ontology_path ? resolveInputPath(ontology_path, 'ontology_path') : null;
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
    const outDir = ensureDir(join(runDir, 'line_report'));
    const log = jobLogFor(task.task_id);
    const context = {};
    if (!data_dir && dataAbs) context.data_path = dataAbs;
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

    log.log(`[hub] 提交产线稳定性报告任务 ${task.task_id}（input=${data_dir || data_path}）`);
    let analysisDataPath = dataAbs;
    if (data_dir) {
      log.log('[hub] 文件夹输入：启动自适应文件发现与预处理…');
      const preprocessor = join(PROJECT_ROOT, '.claude', 'skills', 'industrial-data-preprocessor', 'scripts', 'data_preprocessor.py');
      const prep = await uvPythonStreaming(preprocessor, [
        '--data-path', dataAbs,
        '--output', inputDir,
        '--name', line_id || task.task_id,
        '--stability-single-primary',
        '--recursive',
      ], { timeoutMs: 300000, onLine: (line, stream) => log.log(line, stream) });
      const prepReportPath = join(inputDir, 'preprocessing_report.json');
      const prepReport = readJsonSafe(prepReportPath, null);
      if (prep.code !== 0 || !prepReport) {
        throw new Error(`folder preprocessing failed (${prep.code}): ${tail(prep.stderr) || tail(prep.stdout)}`);
      }
      if (prepReport.status !== 'ok' || !existsSync(join(inputDir, 'preprocessed_data.csv'))) {
        const auditPath = join(runDir, 'input_audit.json');
        writeFileSync(auditPath, JSON.stringify(prepReport, null, 2));
        throw new Error(`folder contains no usable primary time series: ${prepReport.status || 'missing canonical table'}; audit: ${auditPath}`);
      }
      const selected = prepReport.selected_table;
      if (!selected || !selected.time_column || Number(selected.n_rows || 0) < 50) {
        throw new Error('folder preprocessing did not find a time-series primary table with at least 50 rows');
      }
      const sourceFiles = (prepReport.source_dispositions || []).map((item) => {
        if (item.role === 'protected_truth' || item.disposition === 'protected_excluded') {
          return { ...item, sha256: null, size_bytes: null };
        }
        const sourcePath = item.relative_path ? join(dataAbs, item.relative_path) : null;
        if (!sourcePath || !existsSync(sourcePath) || !statSync(sourcePath).isFile()) {
          return { ...item, sha256: null, size_bytes: null };
        }
        const info = statSync(sourcePath);
        return { ...item, sha256: `sha256:${createHash('sha256').update(readFileSync(sourcePath)).digest('hex')}`, size_bytes: info.size };
      });
      context.preprocessing = {
        mode: 'directory_adaptive',
        source_directory: dataAbs,
        recursive_discovery: true,
        report_path: prepReportPath,
        manifest_path: join(inputDir, 'input_manifest.json'),
        source_files: sourceFiles,
        selected_table: prepReport.selected_table,
        merge: prepReport.merge,
        merge_exclusions: prepReport.merge_exclusions || [],
        source_dispositions: prepReport.source_dispositions || [],
        context_files: prepReport.context_files || [],
        skipped_files: prepReport.skipped_files || [],
        quality: prepReport.quality || {},
      };
      analysisDataPath = join(inputDir, 'preprocessed_data.csv');
      context.data_path = analysisDataPath;
      context.time_col = time_col || selected.time_column;
      const inputHash = createHash('sha256').update(readFileSync(analysisDataPath)).digest('hex');
      const manifest = {
        manifest_version: 'line-report-folder-input/1.0',
        input_kind: 'directory',
        source_directory: dataAbs,
        discovered_files: sourceFiles,
        selected_table: prepReport.selected_table,
        scoring_table: { path: analysisDataPath, sha256: `sha256:${inputHash}`, rows: selected.n_rows, columns: selected.n_cols, time_column: selected.time_column },
        merge: prepReport.merge,
        merge_exclusions: prepReport.merge_exclusions || [],
        source_dispositions: sourceFiles,
        context_files: prepReport.context_files || [],
        skipped_files: prepReport.skipped_files || [],
      };
      context.preprocessing = { ...context.preprocessing, manifest_path: join(inputDir, 'input_manifest.json'), scoring_table: manifest.scoring_table };
      writeFileSync(join(inputDir, 'input_manifest.json'), JSON.stringify(manifest, null, 2));
      writeFileSync(join(inputDir, 'report_context.json'), JSON.stringify(context, null, 2));
      if (!ontologyAbs) {
        const ontologyFile = (prepReport.source_dispositions || []).find((item) =>
          item.disposition === 'context_only' && /ontology[^/]*\.json$/i.test(item.relative_path || ''));
        if (ontologyFile) {
          ontologyAbs = resolveDataFile(join(dataAbs, ontologyFile.relative_path), 'ontology_path', ['.json']);
          context.ontology_path = ontologyAbs;
          writeFileSync(join(inputDir, 'report_context.json'), JSON.stringify(context, null, 2));
          log.log(`[hub] 检测到文件夹内本体 ${ontologyFile.relative_path}，自动接线为本体输入`);
        }
      }
      log.log(`[hub] 预处理完成：主表 ${selected.file}${selected.sheet ? ` / ${selected.sheet}` : ''}，${selected.n_rows} 行、${selected.n_cols} 列`);
      for (const item of prepReport.merge_exclusions || []) log.log(`[hub] 未并入 ${item.file}: ${item.reason_code} — ${item.detail}`);
      for (const item of prepReport.source_dispositions || []) {
        if (['event', 'auxiliary', 'context', 'metadata', 'protected_truth', 'skipped'].includes(item.role)
            || ['excluded_from_scoring', 'context_only', 'protected_excluded', 'skipped'].includes(item.disposition)) {
          log.log(`[hub] 文件 ${item.relative_path}: ${item.role}/${item.disposition} — ${item.reason}`);
        }
      }
    }
    const args = ['analyze', '--run-dir', runDir, '--out-dir', outDir];
    if (analysisDataPath) args.push('--data', analysisDataPath);
    if (time_col && !(data_dir && time_col === 't')) args.push('--time-col', String(time_col));
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
        input_manifest_path: data_dir ? join(inputDir, 'input_manifest.json') : null,
        preprocessing_report_path: data_dir ? join(inputDir, 'preprocessing_report.json') : null,
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
    report: rep,
  };
}

export { reportTasks };
