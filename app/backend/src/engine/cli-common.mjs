// CLI Common — shared infrastructure for all external CLI harness engines.
//
// Implements the multi-harness architecture disciplines that every engine
// integration must follow:
//   · 探测与拉起同源  — availability probing and real spawning resolve the
//     binary through the SAME function (resolveCliBinary).
//   · 命令覆盖链      — config harness.engines.<id>.binary → env
//     HARNESS_<ID>_COMMAND → `where`/`which` → PATH+PATHEXT scan → bare name.
//   · Windows .cmd shim 受控包装 — npm global CLIs are .cmd shims that
//     CreateProcess cannot exec directly; they are wrapped in a LITERAL
//     `cmd.exe /d /s /c` invocation with a verbatim quoted command string
//     (never shell:true, never env-derived wrappers).
//   · 逐参数校验      — every argv element is validated (no quotes, no
//     control characters) because prompts are delivered via stdin/argFile,
//     never through argv.
//   · 错误即事件      — probe/spawn failures return structured results
//     instead of throwing at module load.

import { spawn, execFileSync } from 'child_process';
import { existsSync, statSync } from 'fs';
import { join, isAbsolute, extname, delimiter } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

// ── Per-engine config section (config/default.yaml → harness.engines.<id>) ──
export function engineConfig(id) {
  return config.harness?.engines?.[id] || {};
}

function envCommandOverride(id) {
  const key = `HARNESS_${String(id).toUpperCase()}_COMMAND`;
  const value = process.env[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

// ── PATH + PATHEXT scan (Windows CreateProcess semantics) ──
function scanPath(name) {
  const paths = (process.env.PATH || '').split(delimiter).filter(Boolean);
  const pathext = process.platform === 'win32'
    ? (process.env.PATHEXT || '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean)
    : [''];
  for (const dir of paths) {
    for (const ext of pathext) {
      const candidate = join(dir, `${name}${ext.toLowerCase()}`);
      if (existsSync(candidate)) {
        try {
          if (statSync(candidate).isFile()) return candidate;
        } catch { /* ignore */ }
      }
    }
  }
  return null;
}

export function whereLookup(name) {
  try {
    const lookup = execFileSync(process.platform === 'win32' ? 'where' : 'which', [name], {
      encoding: 'utf-8', timeout: 5000, windowsHide: true,
    });
    const lines = (lookup || '').split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    if (lines.length === 0) return null;
    // npm 全局包会同时生成 sh/.cmd/.ps1 三种 shim — Windows 只能执行
    // .exe/.cmd/.bat；extensionless sh shim 选中会导致 spawn ENOENT。
    const pick = () => {
      const lower = (s) => s.toLowerCase();
      const exe = lines.find((l) => lower(l).endsWith('.exe'));
      if (exe) return exe;
      const cmd = lines.find((l) => lower(l).endsWith('.cmd') || lower(l).endsWith('.bat'));
      if (cmd) return cmd;
      return process.platform === 'win32' ? null : lines[0];
    };
    const chosen = pick();
    return chosen && existsSync(chosen) ? chosen : null;
  } catch {
    return null;
  }
}

const resolvedCache = new Map(); // id -> absolute path | bare name

/**
 * Resolve the executable for an engine id. Probing and spawning share this
 * function so a health probe can never disagree with the real spawn.
 * Cached per id — HARNESS_<ID>_COMMAND / config overrides are read once.
 */
export function resolveCliBinary(id) {
  if (resolvedCache.has(id)) return resolvedCache.get(id);

  const engCfg = engineConfig(id);
  const name = engCfg.binary || id;

  let resolved;
  const envOverride = envCommandOverride(id);
  if (envOverride) {
    // 显式覆盖是命令覆盖链的最后一环 — 具权威性：文件不存在时探测如实失败
    // (409)，绝不静默回退到 PATH 上的真实安装。
    resolved = envOverride;
  } else if (isAbsolute(name) || /[\\/]/.test(name)) {
    resolved = name; // explicit path in config — authoritative as well
  } else {
    const candidates = [];
    candidates.push(whereLookup(name));
    if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
      candidates.push(join(process.env.LOCALAPPDATA, 'Programs', name, `${name}.exe`));
    }
    candidates.push(scanPath(name));
    candidates.push(name); // bare name — works under POSIX shells
    resolved = candidates.find(c => c && existsSync(c)) || name;
  }

  resolvedCache.set(id, resolved);
  if (resolved === name && !existsSync(name)) {
    logger.warn(`Harness CLI "${id}" not found on PATH — using bare name "${name}"`, { context: 'CliCommon' });
  } else {
    logger.info(`Harness CLI "${id}" resolved to: ${resolved}`, { context: 'CliCommon' });
  }
  return resolved;
}

/** Drop the cached resolution (used by tests / config reload). */
export function invalidateBinaryCache(id) {
  if (id) resolvedCache.delete(id);
  else resolvedCache.clear();
}

// ── Argument validation — prompts never travel through argv ──
export function validateCliArg(arg, { allowQuotes = false } = {}) {
  const s = String(arg);
  // eslint-disable-next-line no-control-regex
  if (/[\x00-\x1F\x7F]/.test(s)) {
    throw new Error(`CLI argument contains control characters: ${JSON.stringify(s.slice(0, 80))}`);
  }
  if (!allowQuotes && s.includes('"')) {
    throw new Error(`CLI argument contains double quotes (deliver free text via stdin/argFile): ${JSON.stringify(s.slice(0, 80))}`);
  }
  return s;
}

const CMD_META_RE = /[%^&|<>()!]/;

export function quoteCmdArg(arg) {
  const s = validateCliArg(arg);
  if (s === '') return '""';
  if (!/[\s"^]/.test(s) && !CMD_META_RE.test(s)) return s;
  // Inside double quotes cmd still expands %VAR%; reject rather than mis-execute.
  if (s.includes('%')) {
    throw new Error(`CLI argument contains "%" which cmd.exe would expand: ${JSON.stringify(s.slice(0, 80))}`);
  }
  return `"${s.replace(/(\\*)"/g, '$1$1\\"')}"`;
}

/**
 * Spawn an already-resolved binary path. Windows .cmd/.bat shims are wrapped
 * in a literal `cmd.exe /d /s /c` with a verbatim, self-quoted command string
 * (the documented Node/cmd.exe contract — never shell:true, never an
 * env-configurable wrapper). Shared by spawnCli and the omp client so every
 * engine gets identical shim handling (探测与拉起同源).
 */
export function spawnResolvedCli(resolved, args, { cwd = PROJECT_ROOT, env = {}, windowsVerbatimArguments, context = 'CliCommon' } = {}) {
  const safeArgs = (args || []).map((a) => validateCliArg(a));
  const mergedEnv = { ...process.env, ...env };

  const ext = extname(resolved).toLowerCase();
  if (process.platform === 'win32' && (ext === '.cmd' || ext === '.bat')) {
    const commandLine = [quoteCmdArg(resolved), ...safeArgs.map(quoteCmdArg)].join(' ');
    logger.info(`spawn [${context}]: cmd.exe /d /s /c ${commandLine}`.slice(0, 400), { context: 'CliCommon' });
    return spawn('cmd.exe', ['/d', '/s', '/c', commandLine], {
      cwd,
      env: mergedEnv,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      windowsVerbatimArguments: windowsVerbatimArguments !== false,
    });
  }

  logger.info(`spawn [${context}]: ${resolved} ${safeArgs.join(' ')}`.slice(0, 400), { context: 'CliCommon' });
  return spawn(resolved, safeArgs, {
    cwd,
    env: mergedEnv,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  });
}

export function spawnCli(id, args, { cwd = PROJECT_ROOT, env = {}, windowsVerbatimArguments } = {}) {
  const resolved = resolveCliBinary(id);
  const mergedEnv = { ...engineConfig(id).env, ...env };
  return spawnResolvedCli(resolved, args, { cwd, env: mergedEnv, windowsVerbatimArguments, context: id });
}

/**
 * Probe whether an engine CLI actually executes: `<binary> --version`.
 * Same resolution path as spawnCli (探测与拉起同源).
 */
export function probeCliBinary(id, { versionArgs = ['--version'], timeoutMs } = {}) {
  // 15s — qwen/pi 等慢启动 CLI 在 Windows 上 8s 探测会假阴性（available=false）
  const timeout = timeoutMs || config.harness?.health_timeout_ms || 15000;
  return new Promise((resolve) => {
    let proc;
    try {
      proc = spawnCli(id, versionArgs, { cwd: PROJECT_ROOT });
    } catch (e) {
      resolve({ available: false, binary: resolveCliBinary(id), error: e.message });
      return;
    }

    let out = '';
    let err = '';
    let settled = false;
    const done = (result) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(result);
      }
    };
    const timer = setTimeout(() => {
      killTree(proc);
      done({ available: false, binary: resolveCliBinary(id), error: `version probe timeout after ${timeout}ms` });
    }, timeout);

    proc.stdout?.on('data', (d) => { out += d.toString(); });
    proc.stderr?.on('data', (d) => { err += d.toString(); });
    proc.on('error', (e) => done({ available: false, binary: resolveCliBinary(id), error: e.message }));
    proc.on('exit', (code) => {
      const raw = (out || err).trim();
      done({
        available: code === 0,
        binary: resolveCliBinary(id),
        version: raw.split(/\r?\n/)[0]?.slice(0, 80) || null,
        raw: raw.slice(0, 200),
        code,
      });
    });
  });
}

// ── Process-tree kill (win32 taskkill /T /F; POSIX kill -pid) ──
export function killTree(proc) {
  if (!proc || proc.exitCode !== null) return;
  const pid = proc.pid;
  // win32: taskkill /T reaps the tree by walking the root's children, so it
  // MUST run while the root is still alive. Terminating the root first turns
  // /T into a no-op that leaks the grandchildren of npm-style .cmd shims
  // (cmd.exe /c node …) — the tree-kill is therefore synchronous and first.
  let treeKilled = false;
  if (process.platform === 'win32' && pid) {
    try {
      execFileSync('taskkill', ['/pid', String(pid), '/T', '/F'], { timeout: 5000, windowsHide: true, stdio: 'ignore' });
      treeKilled = true;
    } catch { /* root already gone / taskkill unavailable — kill() below is the fallback */ }
  }
  // Belt-and-braces: the handle must report `killed` (stop-route semantics
  // rely on it) — taskkill already reaped the root, so kill() cannot mark it.
  if (treeKilled) {
    try { proc.killed = true; } catch { /* no setter in this Node build */ }
  } else {
    try { proc.kill('SIGKILL'); } catch { /* already dead */ }
  }
  if (process.platform !== 'win32' && pid) {
    try { process.kill(-pid, 'SIGKILL'); } catch { /* root already gone */ }
  }
}

// ── Turn-timeout guard (shared by every CLI engine client) ──
// minutes <= 0 disables the guard; fractional minutes are honored (tests use
// them to exercise the kill path in milliseconds). On fire the guard logs one
// line, runs the caller's own hard-error path (onTimeout — emit the result
// frame / mark the query finished), then kills the owned process tree.
// cancel() must be called on every terminal path (process exit, result
// emitted, close) so a finished turn never fires.
export function withTimeout({
  minutes, label = 'engine', context = 'CliCommon', turnKey = '',
  onTimeout = null, child = null, logger: log = logger,
}) {
  const ms = (Number(minutes) || 0) * 60 * 1000;
  if (!(ms > 0)) {
    return {
      ms: 0,
      get fired() { return false; },
      cancel() { /* disabled — nothing to clear */ },
      promise: new Promise(() => { /* never settles — racers wait on the operation */ }),
    };
  }

  let timer = null;
  let fired = false;
  let resolveFired = null;
  const promise = new Promise((resolve) => { resolveFired = resolve; });

  timer = setTimeout(() => {
    timer = null;
    fired = true;
    log.error(`[${label}] turn timed out after ${ms}ms — killing process tree`, { context, turnKey });
    try {
      onTimeout?.();
    } catch (e) {
      log.warn(`[${label}] timeout handler failed: ${e.message}`, { context, turnKey });
    }
    if (child) killTree(child);
    resolveFired(ms);
  }, ms);

  return {
    ms,
    promise,
    get fired() { return fired; },
    cancel() {
      if (timer) { clearTimeout(timer); timer = null; }
    },
  };
}

/**
 * Effective per-turn timeout (minutes) for an engine: explicit run value →
 * per-engine config (harness.engines.<id>.timeout_minutes) → global
 * harness.timeout_minutes → 0 (unlimited). Mirrors the one-shot family's
 * harnessTimeout() chain so every client resolves the budget identically.
 */
export function resolveEngineTimeoutMinutes(id, override) {
  const explicit = Number(override);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  const perEngine = Number(engineConfig(id).timeout_minutes);
  if (Number.isFinite(perEngine) && perEngine > 0) return perEngine;
  const global = Number(config.harness?.timeout_minutes);
  return Number.isFinite(global) && global > 0 ? global : 0;
}

/** Keep the last `max` characters of a stream — used for error-event tails. */
export function stderrTailRef(proc, max = 4000) {
  let tail = '';
  proc.stderr?.on('data', (d) => { tail = (tail + d.toString()).slice(-max); });
  return () => tail;
}
