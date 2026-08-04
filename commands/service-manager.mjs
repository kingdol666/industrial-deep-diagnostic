#!/usr/bin/env node
// commands/service-manager.mjs — Cross-platform service lifecycle management
//
// Manages start/stop/status/health of three services:
//   - backend  (Express, port 3210)
//   - frontend (Vite,    port 5180)
//   - rag      (FastAPI, port 8764)
//
// Stores runtime state in .runtime/ (PID files + status JSON).
// Uses cross-platform.mjs utilities for port and process ops.
//
// API / CLI:
//   node service-manager.mjs start   [--all|--backend|--frontend|--rag]  [--detach]
//   node service-manager.mjs stop    [--all|--backend|--frontend|--rag]
//   node service-manager.mjs status  [--json]
//   node service-manager.mjs restart [--all|--backend|--frontend|--rag]
//   node service-manager.mjs health  [--all|--backend|--frontend|--rag]

import { spawn } from 'child_process';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, mkdirSync, writeFileSync, readFileSync, unlinkSync } from 'fs';
import { createServer } from 'net';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');
const RUNTIME_DIR = join(PROJECT_ROOT, '.runtime', 'pids');

// Ensure runtime dir exists
if (!existsSync(RUNTIME_DIR)) {
  mkdirSync(RUNTIME_DIR, { recursive: true });
}

// ─── Service Definitions ──────────────────────────────────

const SERVICES = {
  backend: {
    name: 'Backend',
    port: 3210,
    color: '\x1b[36m',  // cyan
    dir: join(PROJECT_ROOT, 'app', 'backend'),
    startCmd: 'node',
    startArgs: ['src/index.mjs'],
    env: { SERVER_PORT: '3210' },
    healthPath: '/api/health',
    pidFile: join(RUNTIME_DIR, 'backend.pid'),
    logFile: join(PROJECT_ROOT, '.runtime', 'backend.log'),
  },
  frontend: {
    name: 'Frontend',
    port: 5180,
    color: '\x1b[35m',  // magenta
    dir: join(PROJECT_ROOT, 'app', 'frontend'),
    // Run vite directly through the Node binary (no shell/npx indirection) so
    // the spawned PID is the real server process on every platform — npx on
    // Windows spawns cmd.exe shims whose PID dies with the console.
    startCmd: 'node',
    startArgs: [join(PROJECT_ROOT, 'app', 'frontend', 'node_modules', 'vite', 'bin', 'vite.js'), '--port', '5180'],
    env: { FRONTEND_PORT: '5180' },
    healthPath: '/',
    pidFile: join(RUNTIME_DIR, 'frontend.pid'),
    logFile: join(PROJECT_ROOT, '.runtime', 'frontend.log'),
  },
  rag: {
    name: 'RAG Engine',
    port: 8764,
    color: '\x1b[33m',  // yellow
    dir: join(PROJECT_ROOT, 'rag-retrieval-engine'),
    startCmd: 'node',
    startArgs: ['start.mjs'],
    env: { RAG_PORT: '8764', RAG_HOST: '0.0.0.0' },
    healthPath: '/health',
    pidFile: join(RUNTIME_DIR, 'rag.pid'),
    logFile: join(PROJECT_ROOT, '.runtime', 'rag.log'),
  },
};

// ─── Platform Utilities ───────────────────────────────────

const IS_WIN = process.platform === 'win32';
const NODE = process.execPath;
const NPX = IS_WIN ? 'npx.cmd' : 'npx';

function resolveCommand(svc) {
  if (svc.startCmd === 'node') return NODE;
  if (svc.startCmd === 'npx') return NPX;
  // For python: try python3, python, or .venv
  if (svc.startCmd === 'python') {
    const venvPy = IS_WIN
      ? join(svc.dir, '.venv', 'Scripts', 'python.exe')
      : join(svc.dir, '.venv', 'bin', 'python');
    if (existsSync(venvPy)) return venvPy;
    return IS_WIN ? 'python' : 'python3';
  }
  return svc.startCmd;
}

// ─── PID File Management ──────────────────────────────────

function readPid(file) {
  try {
    return parseInt(readFileSync(file, 'utf-8').trim(), 10);
  } catch { return null; }
}

function writePid(file, pid) {
  writeFileSync(file, String(pid));
}

function removePid(file) {
  try { unlinkSync(file); } catch { /* ok */ }
}

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0); // signal 0 = existence check
    return true;
  } catch { return false; }
}

// ─── Port / Health Check ──────────────────────────────────

function checkPort(port) {
  return new Promise((resolve) => {
    const server = createServer();
    server.once('error', () => resolve(false)); // port in use
    server.once('listening', () => {
      server.close();
      resolve(true); // port free
    });
    server.listen(port, '127.0.0.1');
  });
}

async function checkHealth(port, path = '/') {
  try {
    const url = `http://127.0.0.1:${port}${path}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    return res.ok ? 'healthy' : 'unhealthy';
  } catch {
    return 'not_reachable';
  }
}

// ─── Start Service ────────────────────────────────────────

async function startService(key, { detach = false } = {}) {
  const svc = SERVICES[key];
  if (!svc) throw new Error(`Unknown service: ${key}`);

  // Check if already running
  const existingPid = readPid(svc.pidFile);
  if (existingPid && isProcessAlive(existingPid)) {
    return { service: key, status: 'already_running', pid: existingPid };
  }

  // Check port
  const portFree = await checkPort(svc.port);
  if (!portFree) {
    // Try to kill the port occupant
    const { execSync } = await import('child_process');
    try {
      if (IS_WIN) {
        execSync(`netstat -ano | findstr :${svc.port}`, { encoding: 'utf-8' });
        const lines = execSync(`netstat -ano | findstr :${svc.port}`, { encoding: 'utf-8' }).trim().split('\n');
        for (const line of lines) {
          const pid = line.trim().split(/\s+/).pop();
          if (pid && pid !== '0') execSync(`taskkill /F /PID ${pid} 2>nul`, { encoding: 'utf-8' });
        }
      }
      await new Promise(r => setTimeout(r, 1000));
    } catch { /* port was actually free or cleanup failed */ }
    const stillBlocked = !(await checkPort(svc.port));
    if (stillBlocked) return { service: key, status: 'port_blocked', port: svc.port };
  }

  // Ensure node_modules exist (skip RAG which has its own venv via start.mjs)
  if (key !== 'rag' && !existsSync(join(svc.dir, 'node_modules'))) {
    const { execSync } = await import('child_process');
    try {
      console.log(`  ${svc.color}[${svc.name}]${'\x1b[0m'} Installing dependencies...`);
      execSync('npm install --no-audit --no-fund', { cwd: svc.dir, stdio: 'ignore' });
    } catch (e) {
      return { service: key, status: 'deps_failed', error: e.message };
    }
  }

  // Resolve command
  const cmd = resolveCommand(svc);

  // Spawn — direct binary, no shell, so child.pid is the REAL server process
  // on Windows/Linux/macOS alike (shell:true would hand back the cmd shim PID).
  const env = { ...process.env, ...svc.env };
  const child = spawn(cmd, svc.startArgs, {
    cwd: svc.dir,
    env,
    stdio: detach ? 'ignore' : 'inherit',
    detached: detach,
    shell: false,
  });

  writePid(svc.pidFile, child.pid);

  if (detach) child.unref();

  // Wait for the service to answer HTTP (health probe is the reliable
  // cross-platform signal — raw port probes misfire on IPv6 dual-stack
  // listeners that accept 127.0.0.1 binds while the service is running).
  const maxWait = key === 'rag' ? 600 : 60;
  let healthy = false;
  for (let i = 0; i < maxWait; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const h = await checkHealth(svc.port, svc.healthPath);
    if (h !== 'not_reachable') {
      healthy = true;
      break;
    }
    // Report progress for long waits
    if (i > 0 && i % 30 === 0) {
      console.log(`  ${svc.color}[${svc.name}]${'\x1b[0m'} Still waiting for ${svc.healthPath} on port ${svc.port}... (${i}s)`);
    }
  }

  if (!healthy && !detach) {
    // Kill and report failure
    try { process.kill(child.pid, 'SIGTERM'); } catch { }
    removePid(svc.pidFile);
    return { service: key, status: 'start_timeout', port: svc.port, message: `Port ${svc.port} not ready after ${maxWait}s. Check logs for details.` };
  }

  const health = healthy ? await checkHealth(svc.port, svc.healthPath) : 'starting';

  return {
    service: key,
    status: healthy ? 'running' : 'starting',
    pid: child.pid,
    port: svc.port,
    health,
  };
}

// ─── Stop Service ─────────────────────────────────────────

async function stopService(key) {
  const svc = SERVICES[key];
  if (!svc) throw new Error(`Unknown service: ${key}`);

  const pid = readPid(svc.pidFile);

  // Try graceful kill on PID
  if (pid && isProcessAlive(pid)) {
    try { process.kill(pid, 'SIGTERM'); } catch { }
    // Wait for exit
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 500));
      if (!isProcessAlive(pid)) break;
    }
    // Force kill if still alive
    if (isProcessAlive(pid)) {
      try { process.kill(pid, 'SIGKILL'); } catch { }
    }
  }

  removePid(svc.pidFile);

  // Also try port-based killing (belt and suspenders)
  const portFree = await checkPort(svc.port);
  if (!portFree) {
    const { execSync } = await import('child_process');
    try {
      if (IS_WIN) {
        const lines = execSync(`netstat -ano | findstr :${svc.port}`, { encoding: 'utf-8' }).trim().split('\n');
        for (const line of lines) {
          const pid = line.trim().split(/\s+/).pop();
          if (pid && pid !== '0') execSync(`taskkill /F /PID ${pid} 2>nul`, { encoding: 'utf-8' });
        }
      } else {
        execSync(`lsof -ti :${svc.port} | xargs kill -9 2>/dev/null`, { encoding: 'utf-8' });
      }
    } catch { /* cleanup was fine */ }
  }

  return { service: key, status: 'stopped' };
}

// ─── Status ───────────────────────────────────────────────

async function getStatus(key) {
  const svc = SERVICES[key];
  const pid = readPid(svc.pidFile);
  const alive = pid ? isProcessAlive(pid) : false;
  // HTTP health probe decides running state (port probes misfire on
  // dual-stack listeners); fall back to PID liveness for 'starting'.
  const health = await checkHealth(svc.port, svc.healthPath);
  const running = health !== 'not_reachable';

  let status = 'stopped';
  if (running) status = 'running';
  else if (alive) status = 'starting';
  else status = 'stopped';

  return {
    service: key,
    name: svc.name,
    port: svc.port,
    status,
    pid: alive ? pid : null,
    health: running ? health : null,
  };
}

// ─── CLI Router ───────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  const targets = args.slice(1).filter(f => !f.startsWith('--'));



  const jsonOutput = args.includes('--json');

  switch (command) {
    case 'start': {
      if (!jsonOutput) {
        console.log('');
        console.log('  \x1b[1;32m╔══════════════════════════════════════╗\x1b[0m');
        console.log('  \x1b[1;32m║   Starting Services...                ║\x1b[0m');
        console.log('  \x1b[1;32m╚══════════════════════════════════════╝\x1b[0m');
        console.log('');
      }
      const detach = args.includes('--detach');
      const results = {};
      for (const key of targets) {
        if (!jsonOutput) process.stdout.write(`  Starting ${SERVICES[key].name}... `);
        const r = await startService(key, { detach });
        results[key] = r;
        if (!jsonOutput) {
          console.log(r.status === 'running' || r.status === 'already_running'
            ? `\x1b[32mOK\x1b[0m (${r.status})`
            : `\x1b[31m${r.status}\x1b[0m`);
        }
      }
      if (jsonOutput) console.log(JSON.stringify(results, null, 2));
      break;
    }

    case 'stop': {
      if (!jsonOutput) {
        console.log('');
        console.log('  \x1b[1;31m╔══════════════════════════════════════╗\x1b[0m');
        console.log('  \x1b[1;31m║   Stopping Services...                ║\x1b[0m');
        console.log('  \x1b[1;31m╚══════════════════════════════════════╝\x1b[0m');
        console.log('');
      }
      const results = {};
      for (const key of targets) {
        if (!jsonOutput) process.stdout.write(`  Stopping ${SERVICES[key].name}... `);
        const r = await stopService(key);
        results[key] = r;
        if (!jsonOutput) console.log('\x1b[32mOK\x1b[0m');
      }
      if (jsonOutput) console.log(JSON.stringify(results, null, 2));
      break;
    }

    case 'status': {
      const results = {};
      const keys = targets.length > 0 ? targets : allKeys;
      for (const key of keys) {
        results[key] = await getStatus(key);
      }

      if (jsonOutput) {
        console.log(JSON.stringify(results, null, 2));
      } else {
        console.log('');
        console.log('  \x1b[1;34m╔══════════════════════════════════════════════════════╗\x1b[0m');
        console.log('  \x1b[1;34m║   Service Status                                     ║\x1b[0m');
        console.log('  \x1b[1;34m╚══════════════════════════════════════════════════════╝\x1b[0m');
        console.log('');
        console.log('  \x1b[1mService       Port     Status      PID       Health\x1b[0m');
        console.log('  ──────────   ────     ──────      ───       ──────');

        for (const key of keys) {
          const r = results[key];
          const statusIcon = r.status === 'running' ? '\x1b[32m●\x1b[0m' :
                               r.status === 'starting' ? '\x1b[33m◐\x1b[0m' :
                               '\x1b[31m○\x1b[0m';
          const statusStr = r.status.padEnd(10);
          const pidStr = (r.pid || '-').toString().padEnd(9);
          const healthStr = (r.health || '-').padEnd(10);
          console.log(`  ${r.name.padEnd(12)} ${String(r.port).padEnd(8)} ${statusIcon} ${statusStr} ${pidStr} ${healthStr}`);
        }

        const allRunning = Object.values(results).every(r => r.status === 'running');
        console.log('');
        if (allRunning) {
          console.log('  \x1b[32m✓ All services running\x1b[0m');
        } else {
          console.log('  \x1b[33m⚠ Some services are not running\x1b[0m');
        }
        console.log('');
      }
      break;
    }

    case 'restart': {
      for (const key of targets) {
        if (!jsonOutput) console.log(`  Restarting ${SERVICES[key].name}...`);
        await stopService(key);
        await new Promise(r => setTimeout(r, 2000));
        const r = await startService(key);
        if (!jsonOutput) {
          console.log(`  ${SERVICES[key].name}: ${r.status}`);
        }
      }
      break;
    }

    case 'health': {
      for (const key of targets) {
        const r = await getStatus(key);
        if (jsonOutput) {
          console.log(JSON.stringify(r));
        } else {
          const icon = r.health === 'healthy' ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
          console.log(`  ${icon} ${r.name}: ${r.health || 'offline'}`);
        }
      }
      break;
    }

    default:
      console.log('Usage: node service-manager.mjs <start|stop|status|restart|health> [--all|--backend|--frontend|--rag] [--json] [--detach]');
      process.exit(1);
  }
}

main().catch((err) => {
  console.error('\x1b[31mFATAL:\x1b[0m', err.message);
  process.exit(1);
});
