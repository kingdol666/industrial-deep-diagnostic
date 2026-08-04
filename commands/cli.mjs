#!/usr/bin/env node
// commands/cli.mjs — Unified project CLI (ind-diag)
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, readFileSync } from 'fs';
import { execSync, spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');
const IS_WIN = process.platform === 'win32';
const NC = '\x1b[0m', B = '\x1b[1m', G = '\x1b[32m', R = '\x1b[31m', C = '\x1b[36m', Y = '\x1b[33m';
const NODE = process.execPath;
const ALL_SERVICES = ['backend', 'frontend', 'rag'];

// ─── Helpers ────────────────────────────────────────────────
function heading(text) {
  console.log(`\n  ${B}${C}╔══════════════════════════════════════╗${NC}`);
  console.log(`  ${B}${C}║   ${text.padEnd(34)}║${NC}`);
  console.log(`  ${B}${C}╚══════════════════════════════════════╝${NC}\n`);
}
function ok(msg) { console.log(`  ${G}✓${NC} ${msg}`); }
function fail(msg) { console.log(`  ${R}✗${NC} ${msg}`); }
function info(msg) { console.log(`  ${Y}→${NC} ${msg}`); }

// Parse flags like --backend --detach → targets=[backend], detach=true
function parseFlags(rawFlags) {
  const detach = rawFlags.includes('--detach');
  const all = rawFlags.includes('--all');
  let targets = rawFlags
    .filter(f => ALL_SERVICES.includes(f.replace(/^--/, '')))
    .map(f => f.replace(/^--/, ''));
  if (all || targets.length === 0) targets = ALL_SERVICES;
  return { targets, detach };
}

// ─── Service Manager Proxy (handles target resolution) ──────
async function sm(command, flags) {
  return new Promise((resolve, reject) => {
    const { targets, detach } = parseFlags(flags);
    if (targets.length === 0) { resolve(); return; }

    // Pass --detach through — parseFlags consumed it, but service-manager
    // needs it to decide background vs foreground (lost before → services
    // were started foreground, then killed by the 30s timeout path).
    const smArgs = [join(__dirname, 'service-manager.mjs'), command, ...targets];
    if (detach) smArgs.push('--detach');

    const child = spawn(NODE, smArgs, {
      cwd: PROJECT_ROOT,
      stdio: 'inherit',
      shell: IS_WIN,
    });
    const timer = setTimeout(() => { child.kill(); reject(new Error('Service manager timeout')); }, 120000);
    child.on('close', (code) => { clearTimeout(timer); code === 0 ? resolve() : reject(new Error(`Exit ${code}`)); });
    child.on('error', (err) => { clearTimeout(timer); reject(err); });
  });
}

// ─── Commands ────────────────────────────────────────────────
async function cmdStart(args) {
  heading('Starting Services');
  await sm('start', args.slice(1));
}
async function cmdStop(args) {
  heading('Stopping Services');
  await sm('stop', args.slice(1));
}
async function cmdStatus() {
  await sm('status', ['--all']);
}
async function cmdRestart(args) {
  heading('Restarting Services');
  await sm('restart', args.slice(1));
}

function cmdInit() {
  heading('Environment Check');
  info(`Node.js: ${process.version}`);
  try { ok(`npm: ${execSync('npm --version', { encoding: 'utf-8' }).trim()}`); } catch { fail('npm not found'); }
  const pyCmd = IS_WIN ? 'python' : 'python3';
  try { ok(`Python: ${execSync(`${pyCmd} --version 2>&1`, { encoding: 'utf-8' }).trim()}`); } catch { fail('Python not found'); }
  info('Checking ports…');
  import('./cross-platform.mjs').then(async ({ isPortFree }) => {
    for (const [name, port] of Object.entries({ Backend: 3210, Frontend: 5180, 'RAG Engine': 8764 })) {
      const free = await isPortFree(port);
      (free ? ok : fail)(`${name} port ${port}: ${free ? 'free' : 'IN USE'}`);
    }
    console.log('');
  });
}

function cmdBuild() {
  heading('Production Build');
  const dir = join(PROJECT_ROOT, 'app', 'frontend');
  try { execSync('npm run build', { cwd: dir, stdio: 'inherit' }); ok('Frontend built'); }
  catch { fail('Build failed'); }
}

function cmdVersion() {
  const pkg = JSON.parse(readFileSync(join(PROJECT_ROOT, 'package.json'), 'utf-8'));
  console.log(`\n  ${B}industrial-deep-diagnostic${NC} v${pkg.version}`);
  console.log(`  ${pkg.description}\n`);
  console.log('  ind-diag start   [--all|--backend|--frontend|--rag]');
  console.log('  ind-diag stop    [--all|--backend|--frontend|--rag]');
  console.log('  ind-diag status');
  console.log('  ind-diag restart [--all|--backend|--frontend|--rag]');
  console.log('  ind-diag init');
  console.log('  ind-diag build\n');
}

function printUsage() { cmdVersion(); }

// ─── Router ──────────────────────────────────────────────────
async function main() {
  const cmd = process.argv[2];
  const args = process.argv.slice(2);
  switch (cmd) {
    case 'start': case 'up': return cmdStart(args);
    case 'stop': case 'down': return cmdStop(args);
    case 'status': case 'ps': return cmdStatus();
    case 'restart': return cmdRestart(args);
    case 'init': case 'check': return cmdInit();
    case 'build': return cmdBuild();
    case 'version': case '--version': case '-v': case undefined: return cmdVersion();
    default: return printUsage();
  }
}
main().catch((err) => { console.error(`  ${R}FATAL:${NC}`, err.message); process.exit(1); });
