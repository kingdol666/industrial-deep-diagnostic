#!/usr/bin/env node
// commands/cross-platform.mjs — Cross-platform utilities
// Provides OS-agnostic wrappers for process management, port checking,
// and command resolution. Replaces bash scripts and UNIX-only tools.
// Works on Windows, Linux, and macOS.

import { spawn, execSync, execFileSync } from 'child_process';
import { platform, EOL } from 'os';
import { createServer } from 'net';

export const isWindows = platform() === 'win32';

// ─── Command Resolution ──────────────────────────────────────

/**
 * Resolve the platform-appropriate npx command.
 * On Windows CMD/PowerShell, uses 'npx.cmd'.
 * In Git Bash / MSYS2 / Cygwin, uses 'npx' (shell script).
 * Falls back gracefully if the .cmd variant doesn't exist.
 */
export function npxCmd() {
  if (!isWindows) return 'npx';
  // In Git Bash / MSYS2, npx is a shell script, not .cmd
  // Check if npx.cmd exists; if not, use npx
  try {
    execFileSync('where', ['npx.cmd'], { stdio: 'ignore' });
    return 'npx.cmd';
  } catch {
    return 'npx';
  }
}

/**
 * Resolve the platform-appropriate npm command.
 */
export function npmCmd() {
  if (!isWindows) return 'npm';
  try {
    execFileSync('where', ['npm.cmd'], { stdio: 'ignore' });
    return 'npm.cmd';
  } catch {
    return 'npm';
  }
}

/**
 * Resolve the platform-appropriate node command.
 */
export function nodeCmd() {
  if (!isWindows) return 'node';
  try {
    execFileSync('where', ['node.exe'], { stdio: 'ignore' });
    return 'node.exe';
  } catch {
    return 'node';
  }
}

/** Check if a command exists in PATH (cross-platform which/where) */
export function commandExists(cmd) {
  try {
    if (isWindows) {
      execFileSync('where', [cmd], { stdio: 'ignore' });
    } else {
      execFileSync('which', [cmd], { stdio: 'ignore' });
    }
    return true;
  } catch {
    return false;
  }
}

// ─── Port Management ─────────────────────────────────────────

/**
 * Check if a port is free using Node.js net module.
 * No lsof dependency — works on all platforms.
 */
export function isPortFree(port) {
  return new Promise((resolve) => {
    const server = createServer();
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(false);
      } else {
        // Other errors (EACCES, etc.) — treat as free to let the
        // actual server fail with a clear message
        resolve(true);
      }
    });
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    server.listen(port, '127.0.0.1');
  });
}

/**
 * Find and kill process(es) occupying a port.
 * Cross-platform: uses netstat + taskkill on Windows, lsof + kill on Unix.
 */
export function killPortProcess(port) {
  try {
    if (isWindows) {
      // Windows: netstat -ano | findstr :PORT
      const output = execSync(`netstat -ano | findstr :${port}`, {
        encoding: 'utf-8',
        timeout: 5000,
      });
      const lines = output.split(/\r?\n/).filter(Boolean);
      const pids = new Set();
      for (const line of lines) {
        const match = line.trim().match(/(\d+)\s*$/);
        if (match) {
          const pid = parseInt(match[1], 10);
          if (pid > 0 && pid !== process.pid) pids.add(pid);
        }
      }
      for (const pid of pids) {
        try {
          execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore', timeout: 5000 });
        } catch {}
      }
    } else {
      // Unix: lsof -ti:PORT | xargs kill -9
      try {
        const pids = execSync(`lsof -ti:${port}`, { encoding: 'utf-8', timeout: 5000 })
          .trim()
          .split('\n')
          .filter(Boolean)
          .map(p => parseInt(p.trim(), 10))
          .filter(p => p > 0 && p !== process.pid);
        for (const pid of pids) {
          try { process.kill(pid, 'SIGKILL'); } catch {}
        }
      } catch {
        // lsof returns non-zero when no process found — that's fine
      }
    }
  } catch {
    // netstat/findstr may fail if port is free — that's fine
  }
}

// ─── Process Management ──────────────────────────────────────

/**
 * Kill a child process. On Windows, use taskkill /T to kill the
 * entire process tree. On Unix, use SIGTERM then SIGKILL.
 */
export function killProcess(child, { force = false } = {}) {
  if (!child || !child.pid) return;
  try {
    if (isWindows) {
      // /T kills the process tree; /F forces termination
      const flag = force ? '/F' : '';
      execSync(`taskkill /PID ${child.pid} /T ${flag}`, {
        stdio: 'ignore',
        timeout: 5000,
      });
    } else {
      child.kill(force ? 'SIGKILL' : 'SIGTERM');
    }
  } catch {
    // Process may already be dead
  }
}

/**
 * Gracefully shutdown: SIGTERM first, then SIGKILL after timeout.
 */
export function gracefulKill(child, { timeout = 3000 } = {}) {
  if (!child || !child.pid) return;
  try {
    if (isWindows) {
      // Windows doesn't have graceful shutdown concept — just taskkill /T
      try {
        execSync(`taskkill /PID ${child.pid} /T`, { stdio: 'ignore', timeout: 5000 });
      } catch {}
      return;
    }

    child.kill('SIGTERM');
    const killTimer = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch {}
    }, timeout);

    child.once('close', () => clearTimeout(killTimer));
  } catch {}
}

// ─── Spawn Helpers ───────────────────────────────────────────

/**
 * spawn as a promise. Resolves with exit code 0, rejects otherwise.
 */
export function spawnAsync(cmd, args = [], opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      isWindows && !cmd.endsWith('.exe') && !cmd.endsWith('.cmd') ? `${cmd}.cmd` : cmd,
      args,
      { stdio: 'inherit', ...opts }
    );
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

/**
 * Spawn a process and return the child + a promise that resolves when
 * a pattern appears in stdout/stderr.
 */
export function spawnUntil(cmd, args = [], { pattern, timeout = 30000, cwd, env } = {}) {
  return new Promise((resolve, reject) => {
    const resolvedCmd = isWindows && !cmd.endsWith('.exe') && !cmd.endsWith('.cmd')
      ? `${cmd}.cmd` : cmd;
    const child = spawn(resolvedCmd, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });

    let resolved = false;
    const timer = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        child.kill();
        reject(new Error(`${cmd} timed out after ${timeout}ms waiting for: ${pattern}`));
      }
    }, timeout);

    function checkOutput(data) {
      if (!resolved && data.toString().includes(pattern)) {
        resolved = true;
        clearTimeout(timer);
        resolve(child);
      }
    }

    child.stdout.on('data', checkOutput);
    child.stderr.on('data', checkOutput);

    child.on('close', (code) => {
      if (!resolved) {
        clearTimeout(timer);
        reject(new Error(`${cmd} exited with code ${code} before matching pattern`));
      }
    });

    child.on('error', (err) => {
      if (!resolved) {
        clearTimeout(timer);
        reject(err);
      }
    });
  });
}

// ─── Signal Handling ─────────────────────────────────────────

/**
 * Register cleanup handlers for graceful shutdown.
 * On Windows, process.on('SIGTERM') never fires, so we only use SIGINT.
 * On Unix, both SIGINT and SIGTERM are handled.
 */
export function onShutdown(cleanup) {
  process.on('SIGINT', () => {
    cleanup();
    process.exit(0);
  });

  if (!isWindows) {
    process.on('SIGTERM', () => {
      cleanup();
      process.exit(0);
    });
  }
}

// ─── Misc ────────────────────────────────────────────────────

/** Get current formatted timestamp for logging */
export function timestamp() {
  return new Date().toISOString();
}

/** Print a centered banner line */
export function printBanner(title, subtitle = '') {
  const line = '═'.repeat(46);
  console.log('');
  console.log(`  ╔${line}╗`);
  console.log(`  ║   ${title.padEnd(40)}║`);
  if (subtitle) console.log(`  ║   ${subtitle.padEnd(40)}║`);
  console.log(`  ╚${line}╝`);
  console.log('');
}