#!/usr/bin/env node
// webfrp/expose.mjs — Cloudflare Tunnel quick exposure script
// Exposes local Industrial Diagnostic service to the public internet
// Cross-platform: Windows, Linux, macOS

import { spawn, execSync } from 'child_process';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';
import {
  npxCmd, nodeCmd, npmCmd, isWindows,
  isPortFree, killPortProcess, killProcess, gracefulKill, onShutdown,
  commandExists, printBanner,
} from '../commands/cross-platform.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');
const BACKEND_DIR = join(PROJECT_ROOT, 'app', 'backend');
const FRONTEND_DIR = join(PROJECT_ROOT, 'app', 'frontend');
const FRONTEND_DIST = join(FRONTEND_DIR, 'dist');

const PORT = process.env.SERVER_PORT || 3210;

// ─── Helpers ──────────────────────────────────────────────

function checkCloudflared() {
  return commandExists('cloudflared');
}

function checkFrontendBuilt() {
  return existsSync(join(FRONTEND_DIST, 'index.html'));
}

async function buildFrontend() {
  console.log('  [BUILD] Building frontend...');
  return new Promise((resolve, reject) => {
    const child = spawn(npxCmd(), ['vite', 'build'], {
      cwd: FRONTEND_DIR,
      stdio: 'inherit',
      shell: isWindows,
    });
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`vite build exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

// ─── Start backend ────────────────────────────────────────

function startBackend() {
  const child = spawn(nodeCmd(), ['src/index.mjs'], {
    cwd: BACKEND_DIR,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: String(PORT) },
    shell: isWindows,
  });

  child.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        // Only show important backend logs
        if (line.includes('[Init]') || line.includes('FATAL') || line.includes('ERROR')) {
          console.log('  [BACKEND] ' + line.trim());
        }
      }
    }
  });

  child.stderr.on('data', (data) => {
    const msg = data.toString().trim();
    if (msg && !msg.includes('ExperimentalWarning')) {
      console.log('  [BACKEND:ERR] ' + msg);
    }
  });

  return child;
}

// ─── Start Cloudflare Tunnel ──────────────────────────────

function startTunnel() {
  return new Promise((resolve, reject) => {
    const child = spawn('cloudflared', ['tunnel', '--url', `http://localhost:${PORT}`], {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: isWindows,
    });

    let resolved = false;
    let outputBuffer = '';

    child.stdout.on('data', (data) => {
      outputBuffer += data.toString();
      const lines = outputBuffer.split('\n');
      outputBuffer = lines.pop() || '';

      for (const line of lines) {
        // Extract the public URL from cloudflared output
        const urlMatch = line.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
        if (urlMatch && !resolved) {
          resolved = true;
          resolve({ child, url: urlMatch[0] });
        }
      }
    });

    child.stderr.on('data', (data) => {
      outputBuffer += data.toString();
      const lines = outputBuffer.split('\n');
      outputBuffer = lines.pop() || '';

      for (const line of lines) {
        const urlMatch = line.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
        if (urlMatch && !resolved) {
          resolved = true;
          resolve({ child, url: urlMatch[0] });
        }
      }
    });

    child.on('error', (err) => {
      if (!resolved) reject(err);
    });

    child.on('close', (code) => {
      if (!resolved) reject(new Error(`cloudflared exited with code ${code}`));
    });

    // Timeout: if no URL in 30s, fail
    setTimeout(() => {
      if (!resolved) {
        killProcess(child);
        reject(new Error('cloudflared timed out (30s). Check your network connection.'));
      }
    }, 30000);
  });
}

// ─── Main ──────────────────────────────────────────────────

async function main() {
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   Industrial Diagnostic — Web Exposure       ║');
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');

  // 1. Check cloudflared
  console.log('  [CHECK] cloudflared...');
  if (!checkCloudflared()) {
    console.error('  [ERROR] cloudflared is not installed.');
    console.error('  Install: brew install cloudflared');
    process.exit(1);
  }
  console.log('  [OK] cloudflared found');

  // 2. Check / build frontend
  console.log('  [CHECK] Frontend build...');
  if (!checkFrontendBuilt()) {
    try {
      await buildFrontend();
      console.log('  [OK] Frontend built');
    } catch (err) {
      console.error('  [ERROR] Frontend build failed: ' + err.message);
      process.exit(1);
    }
  } else {
    console.log('  [OK] Frontend already built');
  }

  // 3. Check backend deps
  if (!existsSync(join(BACKEND_DIR, 'node_modules'))) {
    console.log('  [INSTALL] Installing backend dependencies...');
    await new Promise((resolve, reject) => {
      const child = spawn(npmCmd(), ['install'], { cwd: BACKEND_DIR, stdio: 'inherit', shell: isWindows });
      child.on('close', (code) => code === 0 ? resolve() : reject(new Error('npm install failed')));
    });
  }

  // 4. Ensure port is free
  const portFree = await isPortFree(PORT);
  if (!portFree) {
    console.log('  [WARN] Port ' + PORT + ' is in use, killing existing process...');
    killPortProcess(PORT);
    await new Promise(r => setTimeout(r, 1000));
  }

  // 5. Start backend
  console.log('  [START] Starting backend on port ' + PORT + '...');
  const backend = startBackend();

  // Wait for backend to be ready
  await new Promise((resolve, reject) => {
    let ready = false;
    const timer = setTimeout(() => {
      if (!ready) reject(new Error('Backend did not start within 10s'));
    }, 10000);

    backend.stdout.on('data', (data) => {
      if (!ready && data.toString().includes('HTTP + WebSocket server')) {
        ready = true;
        clearTimeout(timer);
        resolve();
      }
    });

    backend.on('close', () => {
      if (!ready) { clearTimeout(timer); reject(new Error('Backend process exited')); }
    });
  });
  console.log('  [OK] Backend is ready');

  // 6. Start Cloudflare Tunnel
  console.log('  [TUNNEL] Creating Cloudflare Tunnel...');
  let tunnel;
  try {
    tunnel = await startTunnel();
  } catch (err) {
    console.error('  [ERROR] Tunnel failed: ' + err.message);
    killProcess(backend);
    process.exit(1);
  }

  // 7. Success!
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   Service is LIVE on the internet!            ║');
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');
  console.log('  Public URL:');
  console.log('');
  console.log('    ' + tunnel.url);
  console.log('');
  console.log('  Share this URL with anyone to access the');
  console.log('  Industrial Diagnostic WebUI.');
  console.log('');
  console.log('  Press Ctrl+C to stop.');
  console.log('');

  // 8. Cleanup on exit
  onShutdown(() => {
    console.log('\n  Shutting down...');
    killProcess(tunnel.child);
    killProcess(backend);
    console.log('  All services stopped.');
  });

  // Keep alive
  await new Promise((resolve) => {
    backend.on('close', () => { killProcess(tunnel.child); resolve(); });
    tunnel.child.on('close', () => { killProcess(backend); resolve(); });
  });
}

main().catch((err) => {
  console.error('  [ERROR] ' + err.message);
  process.exit(1);
});
