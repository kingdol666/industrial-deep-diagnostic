#!/usr/bin/env node
// webfrp/expose.mjs — Cloudflare Tunnel quick exposure script
// Exposes local Industrial Diagnostic service to the public internet

import { spawn, execSync } from 'child_process';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');
const BACKEND_DIR = join(PROJECT_ROOT, 'app', 'backend');
const FRONTEND_DIR = join(PROJECT_ROOT, 'app', 'frontend');
const FRONTEND_DIST = join(FRONTEND_DIR, 'dist');

const PORT = process.env.SERVER_PORT || 3210;

// ─── Helpers ──────────────────────────────────────────────

function isPortFree(port) {
  try {
    const result = execSync(`lsof -ti:${port}`, { encoding: 'utf-8', timeout: 3000 }).trim();
    return result.length === 0;
  } catch {
    return true; // lsof returns non-zero when nothing found
  }
}

function killPort(port) {
  try {
    execSync(`lsof -ti:${port} | xargs kill -9`, { encoding: 'utf-8', timeout: 3000 });
  } catch {}
}

// ─── Pre-flight checks ────────────────────────────────────

function checkCloudflared() {
  try {
    execSync('which cloudflared', { encoding: 'utf-8', timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

function checkFrontendBuilt() {
  return existsSync(join(FRONTEND_DIST, 'index.html'));
}

async function buildFrontend() {
  console.log('  [BUILD] Building frontend...');
  return new Promise((resolve, reject) => {
    const child = spawn('npx', ['vite', 'build'], {
      cwd: FRONTEND_DIR,
      stdio: 'inherit',
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
  const child = spawn('node', ['src/index.mjs'], {
    cwd: BACKEND_DIR,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PORT: String(PORT) },
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
        child.kill('SIGTERM');
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
      const child = spawn('npm', ['install'], { cwd: BACKEND_DIR, stdio: 'inherit' });
      child.on('close', (code) => code === 0 ? resolve() : reject(new Error('npm install failed')));
    });
  }

  // 4. Ensure port is free
  if (!isPortFree(PORT)) {
    console.log('  [WARN] Port ' + PORT + ' is in use, killing existing process...');
    killPort(PORT);
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
    backend.kill('SIGTERM');
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
  const cleanup = () => {
    console.log('');
    console.log('  Shutting down...');
    tunnel.child.kill('SIGTERM');
    backend.kill('SIGTERM');
    console.log('  All services stopped.');
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  // Keep alive
  await new Promise((resolve) => {
    backend.on('close', () => { tunnel.child.kill(); resolve(); });
    tunnel.child.on('close', () => { backend.kill(); resolve(); });
  });
}

main().catch((err) => {
  console.error('  [ERROR] ' + err.message);
  process.exit(1);
});
