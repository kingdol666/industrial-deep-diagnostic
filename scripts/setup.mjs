#!/usr/bin/env node
// scripts/setup.mjs — ONE-COMMAND post-clone bootstrap (npm run setup)
//
// 拉取仓库后唯一的入口命令：自动完成
//   1. 根 / app/backend / app/frontend 依赖安装（已装则跳过）
//   2. Python venv 引导（.claude/shared/scripts/uv_env_setup.mjs，uv 优先）
//   3. 数据目录初始化
//   4. 全局指令注册（npm link → ind-diag）
//   5. 三个服务启动（backend / frontend / rag）
//   6. 健康检查轮询，全部就绪后打印访问入口
//
// 幂等：重复运行安全，已完成的步骤自动跳过。
// Flags: --no-start（只初始化不启动）  --skip-link（跳过全局注册）

import { execSync, spawn } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const IS_WIN = process.platform === 'win32';
const NPM = IS_WIN ? 'npm.cmd' : 'npm';

const args = process.argv.slice(2);
const NO_START = args.includes('--no-start');
const SKIP_LINK = args.includes('--skip-link');

const G = '\x1b[32m', R = '\x1b[31m', Y = '\x1b[33m', C = '\x1b[36m', B = '\x1b[1m', NC = '\x1b[0m';
const ok = (m) => console.log(`  ${G}✓${NC} ${m}`);
const skip = (m) => console.log(`  ${Y}↷${NC} ${m} (已就绪，跳过)`);
const fail = (m) => console.log(`  ${R}✗${NC} ${m}`);
const step = (m) => console.log(`\n${B}${C}▸ ${m}${NC}`);

function run(cmd, opts = {}) {
  execSync(cmd, { cwd: ROOT, stdio: opts.quiet ? 'pipe' : 'inherit', shell: IS_WIN, ...opts });
}
function runOut(cmd) {
  return execSync(cmd, { cwd: ROOT, encoding: 'utf-8', shell: IS_WIN }).trim();
}
function hasNodeModules(dir) {
  return existsSync(join(ROOT, dir, 'node_modules'));
}

async function main() {
  console.log(`${B}  ╔══════════════════════════════════════════════════╗${NC}`);
  console.log(`${B}  ║   Industrial Deep Diagnostic — One-shot Setup    ║${NC}`);
  console.log(`${B}  ╚══════════════════════════════════════════════════╝${NC}`);

  // ── 1. 依赖安装 ──
  step('1/5 依赖安装（root / backend / frontend）');
  if (!hasNodeModules('.')) { run(`${NPM} install --no-audit --no-fund`); ok('root 依赖已安装'); }
  else skip('root 依赖');
  if (!hasNodeModules('app/backend')) { run(`${NPM} install --no-audit --no-fund`, { cwd: join(ROOT, 'app', 'backend') }); ok('backend 依赖已安装'); }
  else skip('backend 依赖');
  if (!hasNodeModules('app/frontend')) { run(`${NPM} install --no-audit --no-fund`, { cwd: join(ROOT, 'app', 'frontend') }); ok('frontend 依赖已安装'); }
  else skip('frontend 依赖');

  // ── 2. Python venv ──
  step('2/5 Python venv 引导（uv 优先）');
  const venvPy = IS_WIN
    ? join(ROOT, '.claude', 'shared', 'scripts', '.venv', 'Scripts', 'python.exe')
    : join(ROOT, '.claude', 'shared', 'scripts', '.venv', 'bin', 'python');
  if (existsSync(venvPy)) { skip(`venv (${venvPy})`); }
  else {
    run(`${JSON.stringify(process.execPath)} .claude/shared/scripts/uv_env_setup.mjs`);
    existsSync(venvPy) ? ok('venv 已创建') : fail('venv 创建失败（继续——诊断的 Python 增强步骤会降级并如实标注）');
  }

  // ── 3. 数据目录 ──
  step('3/5 数据目录初始化');
  const dataDir = join(ROOT, 'data');
  if (!existsSync(dataDir)) { mkdirSync(dataDir, { recursive: true }); ok('data/ 已创建'); }
  else skip('data/ 已存在');

  // ── 4. 全局指令注册 ──
  step('4/5 全局指令注册（npm link → ind-diag）');
  if (SKIP_LINK) { skip('按要求跳过'); }
  else {
    try {
      run(`${NPM} link`);
      ok('全局指令 ind-diag 已注册（npm link）');
      try { console.log(`    ind-diag → ${runOut('ind-diag --version').split('\n')[1] || 'v?'}（可全局调用）`); } catch { /* 某些 shell 需重开终端 */ }
    } catch (e) {
      fail('npm link 失败（权限不足或网络策略）');
      console.log(`      ${Y}手动替代：${NC}npm link  或  npm install -g .`);
      console.log(`      ${Y}临时替代：${NC}npm run status / npm run start（不依赖全局指令）`);
    }
  }

  // ── 5. 启动 + 健康检查 ──
  if (NO_START) { console.log(`\n${G}✓ 初始化完成（--no-start：未启动服务）。运行 npm start 启动。${NC}`); return; }
  step('5/5 启动服务（backend :3210 · frontend :5180 · rag :8764）');
  run(`${JSON.stringify(process.execPath)} commands/cli.mjs start --all --detach`);

  console.log(`\n${B}${C}▸ 健康检查${NC}`);
  const checks = [
    { name: 'Backend ', url: 'http://localhost:3210/api/health', validate: (s) => s.includes('"status":"ok"') },
    { name: 'Frontend', url: 'http://localhost:5180/', validate: (s) => s.includes('<div id="app"') || s.includes('<!DOCTYPE') || s.length > 0 },
    { name: 'RAG     ', url: 'http://localhost:8764/health', altUrl: 'http://localhost:8764/', validate: (s) => s.length > 0 },
  ];
  const TIMEOUT = 120000;
  const t0 = Date.now();
  let allUp = false;
  while (Date.now() - t0 < TIMEOUT) {
    allUp = true;
    for (const c of checks) {
      if (c.up) continue;
      try {
        const res = await fetch(c.url, { signal: AbortSignal.timeout(3000) });
        const body = await res.text();
        if (res.ok && c.validate(body)) { c.up = true; ok(`${c.name} → ${c.url}`); }
        else allUp = false;
      } catch {
        try {
          const alt = c.altUrl ? c.altUrl : null;
          if (alt) {
            const res2 = await fetch(alt, { signal: AbortSignal.timeout(3000) });
            if (res2.ok) { c.up = true; ok(`${c.name} → ${alt}`); }
            else allUp = false;
          } else allUp = false;
        } catch { allUp = false; }
      }
    }
    if (allUp) break;
    await new Promise((r) => setTimeout(r, 3000));
    process.stdout.write(`${Y}·${NC}`);
  }

  console.log('');
  if (allUp) {
    console.log(`${G}${B}  ✓ 全部服务就绪！${NC}`);
    console.log(`\n  前端控制台 : ${C}http://localhost:5180${NC}`);
    console.log(`  后端 API   : ${C}http://localhost:3210/api/health${NC}`);
    console.log(`  RAG 引擎   : ${C}http://localhost:8764${NC}`);
    console.log(`\n  全局指令：${B}ind-diag status${NC} / ${B}ind-diag stop --all${NC} / ${B}ind-diag restart --all${NC}`);
  } else {
    fail('部分服务未在超时内就绪 —— 运行 npm run status 查看详情');
    process.exit(1);
  }
}

main().catch((err) => { console.error(`  ${R}FATAL:${NC}`, err.message); process.exit(1); });
