// Closed-loop trio shared utilities — spawn bridges + in-memory async task table.
//
// Workstream D 集成层的公共底座：三个 skill（industrial-sentinel /
// industrial-tuning-memory / industrial-optimizer-loop）的 CLI 子进程桥与
// 异步任务表。业务逻辑分别在 sentinel/experience/optimizer 三个 service；
// 这里只有 spawn 收集、任务生命周期与数据根目录三件事。
//
// 子进程纪律（对齐仓库基准管线）：
//   - Python 一律 `uv run --project .claude/shared/scripts python <script>`（cwd=仓库根）
//   - Node 脚本 `spawn(process.execPath, [...])`
//   - 只收集 exit code / stdout / stderr；结果文件路径回传，脚本产物不搬运不改写

import { spawn } from 'child_process';
import { join, resolve } from 'path';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'fs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';

// 数据根目录：默认 workspace/closedloop（评测敏感的 data/ 目录绝不触碰）。
// 测试通过 env 指到仓库内的独立目录（skill 脚本有 repo-root 路径白名单校验，
// 因此即使是测试目录也必须位于仓库根之内）。
let cachedRoot = null;
export function closedloopRoot() {
  if (!cachedRoot) {
    cachedRoot = process.env.CLOSEDLOOP_DATA_DIR
      ? resolve(process.env.CLOSEDLOOP_DATA_DIR)
      : join(PROJECT_ROOT, 'workspace', 'closedloop');
  }
  return cachedRoot;
}

// 服务器侧路径解析：绝对路径原样；仓库相对路径（data/…、workspace/…）按
// PROJECT_ROOT 解析。后端进程 cwd 是 app/backend，直接 existsSync 会 404，
// 前端闭环控制台传的正是仓库相对路径（datalist 候选与文件面板同源）。
export function resolveServerPath(value) {
  const raw = String(value ?? '');
  if (!raw) return raw;
  if (resolve(raw) === raw) return raw; // already absolute
  const rooted = join(PROJECT_ROOT, raw);
  if (existsSync(rooted)) return rooted;
  return raw;
}

export function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
  return dir;
}

/** spawn 一次子进程，收集 exit code 与 stdout/stderr（带超时杀进程）。 */
export function runProcess(command, args, { timeoutMs = 120000, cwd = PROJECT_ROOT } = {}) {
  return new Promise((resolvePromise) => {
    const child = spawn(command, args, { cwd, windowsHide: true });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      try { child.kill(); } catch { /* already gone */ }
    }, timeoutMs);
    child.stdout.on('data', (d) => { stdout += d.toString(); });
    child.stderr.on('data', (d) => { stderr += d.toString(); });
    child.on('error', (err) => {
      clearTimeout(timer);
      resolvePromise({ code: -1, stdout, stderr: `${stderr}${err.message}`, timedOut });
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolvePromise({ code, stdout, stderr, timedOut });
    });
  });
}

/** Python skill 脚本的 uv 命令行（cwd 必须是仓库根，相对路径按仓库根解析）。 */
export function uvPython(scriptPath, cliArgs, opts = {}) {
  return runProcess('uv', ['run', '--project', '.claude/shared/scripts', 'python', scriptPath, ...cliArgs], opts);
}

/** Node skill 脚本（experience_build.mjs / match_playbook.mjs 等）。 */
export function nodeScript(scriptPath, cliArgs, opts = {}) {
  return runProcess(process.execPath, [scriptPath, ...cliArgs], opts);
}

/** stdout/stderr 尾部（任务视图里回传，避免把几十 KB 日志塞进 HTTP 响应）。 */
export function tail(text, n = 2000) {
  const s = String(text ?? '');
  return s.length <= n ? s : s.slice(-n);
}

let taskSeq = 0;
export function makeTaskId(prefix) {
  taskSeq += 1;
  const ts = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${ts}-${rand}${String(taskSeq).padStart(3, '0')}`;
}

/**
 * 内存异步任务表（POST /tasks 提交即返 task_id，GET /tasks/:id 轮询）。
 * 任务状态：queued → running → completed | failed。
 */
export class TaskTable {
  constructor() { this.tasks = new Map(); }

  create({ kind, prefix }) {
    const id = makeTaskId(prefix);
    const task = {
      task_id: id, kind, status: 'queued',
      created_at: new Date().toISOString(), finished_at: null,
      exit_code: null, error: null, result: null,
    };
    this.tasks.set(id, task);
    // 表只保留最近 200 条，防止长驻进程无限增长
    if (this.tasks.size > 200) {
      const oldest = this.tasks.keys().next().value;
      this.tasks.delete(oldest);
    }
    return task;
  }

  get(id) { return this.tasks.get(String(id ?? '').trim()) || null; }

  markRunning(id) { const t = this.get(id); if (t) t.status = 'running'; }

  /**
   * 落终态。status 可显式指定——sentinel watch 的 exit 1（findings）是成功的
   * 筛查结果而非失败，任务状态仍为 completed（exit_code 如实保留）。
   */
  markDone(id, { code, status = null, error = null, result = null }) {
    const t = this.get(id);
    if (!t) return;
    t.status = status ?? (code === 0 ? 'completed' : 'failed');
    t.exit_code = code;
    t.finished_at = new Date().toISOString();
    t.error = error;
    t.result = result;
  }

  /** 任务执行骨架：排队 → 跑 → 落状态；业务结果由 runFn 返回（存 task.result）。 */
  async run(task, runFn) {
    this.markRunning(task.task_id);
    try {
      const out = await runFn();
      if (out && typeof out === 'object' && out.__code !== undefined) {
        this.markDone(task.task_id, { code: out.__code, error: out.__error, result: out.result });
      } else {
        this.markDone(task.task_id, { code: 0, result: out });
      }
    } catch (err) {
      this.markDone(task.task_id, { code: -1, error: err.message });
    }
    return task;
  }
}

/** 读写小 JSON 状态文件（注册表 / 数据集元信息；损坏按缺省处理）。 */
export function readJsonSafe(path, fallback = null) {
  try {
    if (!existsSync(path)) return fallback;
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return fallback;
  }
}

export function writeJson(path, obj) {
  ensureDir(join(path, '..'));
  writeFileSync(path, JSON.stringify(obj, null, 2), 'utf-8');
  return path;
}
