import { spawn, execSync } from 'child_process';
import { existsSync, readdirSync } from 'fs';
import { resolve, join, dirname, extname, basename } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
const DATA_DIR = join(PROJECT_ROOT, 'data');
const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');

const SKILL_DIR = join(PROJECT_ROOT, '.claude', 'skills', 'industrial-deep-diagnostic');
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');

const ALLOWED_ENV = [
  'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL',
  'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL',
  'NODE_PATH', 'SHELL', 'TERM',
];

function buildEnv() {
  const env = {};
  for (const key of ALLOWED_ENV) {
    if (process.env[key] !== undefined) {
      env[key] = process.env[key];
    }
  }
  env.FORCE_COLOR = '0';
  env.NO_COLOR = '1';
  env.SKILL_PATH = SKILL_DIR;
  return env;
}

function findClaudeCLI() {
  try {
    return execSync('which claude', { encoding: 'utf-8', timeout: 3000 }).trim();
  } catch {
    try {
      return execSync('which claude-code', { encoding: 'utf-8', timeout: 3000 }).trim();
    } catch {
      return null;
    }
  }
}

function sanitize(str) {
  return str.replace(/[\x00-\x08\x0A-\x1F]/g, '').trim();
}

function discoverDataFiles(folderPath) {
  const absolutePath = folderPath.startsWith('/')
    ? folderPath
    : join(PROJECT_ROOT, folderPath);
  const entries = readdirSync(absolutePath);
  const exts = ['.csv', '.xlsx', '.xls', '.parquet', '.json', '.tsv'];
  return entries
    .filter(e => exts.includes(extname(e).toLowerCase()))
    .map(e => join(absolutePath, e))
    .sort();
}

function buildPrompt(sceneName, userQuestion, target, reportLanguage = 'zh') {
  const safeScene = sanitize(sceneName || 'industrial_analysis');
  const safeQuestion = sanitize(userQuestion || '');

  let dataDescription;
  if (target.mode === 'multi') {
    const files = target.files.map(f => sanitize(f)).join('\n  - ');
    dataDescription = `${target.files.length} files:\n  - ${files}`;
  } else if (target.mode === 'folder') {
    const safeFolder = sanitize(target.folderPath);
    const fileList = target.dataFiles.map(f => sanitize(basename(f))).join(', ');
    dataDescription = `Folder: ${safeFolder}\n  Files (${target.dataFiles.length}): ${fileList}`;
  } else {
    dataDescription = `File: ${sanitize(target.dataPath)}`;
  }

  const langRule = reportLanguage === 'zh'
    ? 'IMPORTANT: Write ALL narrative text, headings, analysis descriptions, recommendations, and report.md content in Chinese (中文). Keep technical terms, variable names, column names, and code in English.'
    : 'Write all output in English.';

  return `/industrial-deep-diagnostic ${safeScene}

## Data

${dataDescription}

## Analysis Question

${safeQuestion || 'Perform a comprehensive root cause analysis following the full 8-step pipeline.'}

## Language

${langRule}`;
}

// Dangerous command patterns for HITL interception
const DANGEROUS_PATTERNS = [
  { pattern: /rm\s+-rf\s+\//, level: 'CRITICAL', desc: 'Recursive delete from root' },
  { pattern: /rm\s+-rf\s+\/\*/, level: 'CRITICAL', desc: 'Delete all files from root' },
  { pattern: /rm\s+-rf\s+~/, level: 'CRITICAL', desc: 'Delete home directory' },
  { pattern: /rm\s+-rf\s+\$HOME/, level: 'CRITICAL', desc: 'Delete home directory' },
  { pattern: /chmod\s+(-R\s+)?777\s+\//, level: 'CRITICAL', desc: 'World-writable permissions on system dirs' },
  { pattern: /chown\s+-R\s+\S+\s+\//, level: 'CRITICAL', desc: 'Recursive ownership change from root' },
  { pattern: />\s*\/dev\/sd[a-z]/, level: 'CRITICAL', desc: 'Write directly to disk device' },
  { pattern: /dd\s+if=/, level: 'CRITICAL', desc: 'Raw disk copy operation' },
  { pattern: /mkfs\./, level: 'CRITICAL', desc: 'Filesystem creation (destroys data)' },
  { pattern: /mount\s+-o\s+remount/, level: 'HIGH', desc: 'Remount filesystem' },
  { pattern: /:\\(\\)\s*\{\s*:\|\:&\s*\}/, level: 'CRITICAL', desc: 'Fork bomb' },
  { pattern: /while\s+true\s*;\s*do\s+\S+\s*;\s*done/, level: 'HIGH', desc: 'Infinite loop' },
  { pattern: /curl\s+\S+\s*\|\s*(ba)?sh/, level: 'CRITICAL', desc: 'Curl piped to shell' },
  { pattern: /wget\s+\S+\s*-O\s*-\s*\|\s*(ba)?sh/, level: 'CRITICAL', desc: 'Wget piped to shell' },
  { pattern: /curl\s+\S+\s*\|\s*sudo\s*(ba)?sh/, level: 'CRITICAL', desc: 'Curl piped to sudo shell' },
  { pattern: /git\s+push\s+(-f|--force)\s+origin\s+(main|master)/, level: 'HIGH', desc: 'Force push to main/master' },
  { pattern: /sudo\s+su/, level: 'CRITICAL', desc: 'Switch to root user' },
  { pattern: /sudo\s+passwd/, level: 'CRITICAL', desc: 'Change passwords via sudo' },
  { pattern: /sudo\s+rm/, level: 'HIGH', desc: 'Delete with sudo' },
  { pattern: /iptables\s+-F/, level: 'HIGH', desc: 'Flush firewall rules' },
  { pattern: /systemctl\s+disable/, level: 'HIGH', desc: 'Disable system service' },
  { pattern: /kill\s+-9\s+-1/, level: 'CRITICAL', desc: 'Kill all processes' },
];

export function isDangerousCommand(command) {
  if (!command || typeof command !== 'string') return null;
  for (const rule of DANGEROUS_PATTERNS) {
    if (rule.pattern.test(command)) {
      return { level: rule.level, desc: rule.desc, match: command.match(rule.pattern)[0] };
    }
  }
  return null;
}

const pendingHITL = new Map();

export function resolveHITL(permissionId, approved) {
  const entry = pendingHITL.get(permissionId);
  if (!entry) return false;
  pendingHITL.delete(permissionId);
  entry.resolve(approved === true);
  return true;
}

export function startDiagnosis({ analysisTarget, userQuestion, sceneName, runId: _runId, maxTurns = 0, timeoutMinutes = 120, reportLanguage = 'zh' }) {
  let dataPaths = [];

  // Paths are stored relative to PROJECT_ROOT (e.g. data/file.csv) or relative to DATA_DIR
  // validateDataPath already verified existence against DATA_DIR, normalize all to absolute
  function resolveDataPath(p) {
    if (p.startsWith('/')) return p;
    // Try PROJECT_ROOT first (for paths like data/file.csv), then DATA_DIR
    const fromRoot = join(PROJECT_ROOT, p);
    if (existsSync(fromRoot)) return fromRoot;
    const fromData = join(DATA_DIR, p);
    if (existsSync(fromData)) return fromData;
    return fromRoot; // let caller throw the error
  }

  if (analysisTarget.mode === 'multi') {
    for (const dp of analysisTarget.files) {
      const abs = resolveDataPath(dp);
      if (!existsSync(abs)) {
        const err = new Error(`Data path not found: ${abs}`);
        err.code = 'DATA_NOT_FOUND';
        throw err;
      }
      dataPaths.push(abs);
    }
  } else if (analysisTarget.mode === 'folder') {
    const absFolder = resolveDataPath(analysisTarget.folderPath);
    if (!existsSync(absFolder)) {
      const err = new Error(`Folder not found: ${absFolder}`);
      err.code = 'DATA_NOT_FOUND';
      throw err;
    }
    dataPaths = discoverDataFiles(absFolder);
    if (dataPaths.length === 0) {
      const err = new Error(`No data files found in folder: ${absFolder}`);
      err.code = 'NO_DATA_FOUND';
      throw err;
    }
    analysisTarget.dataFiles = dataPaths;
  } else {
    const abs = resolveDataPath(analysisTarget.dataPath);
    if (!existsSync(abs)) {
      const err = new Error(`Data path not found: ${abs}`);
      err.code = 'DATA_NOT_FOUND';
      throw err;
    }
    dataPaths = [abs];
  }

  if (!existsSync(SKILL_MD)) {
    const err = new Error(`Skill definition not found at: ${SKILL_MD}`);
    err.code = 'SKILL_NOT_FOUND';
    throw err;
  }

  const claudeBin = findClaudeCLI();
  if (!claudeBin) {
    const err = new Error('Claude Code CLI not found in PATH. Install with: npm install -g @anthropic-ai/claude-code');
    err.code = 'CLAUDE_NOT_FOUND';
    throw err;
  }

  const prompt = buildPrompt(sceneName, userQuestion, analysisTarget, reportLanguage);

  // Use -p for direct prompt input (not stream-json input) — skill invocation needs natural language
  const claudeArgs = [
    '-p', prompt,
    '--output-format', 'stream-json',
    '--verbose',
    '--dangerously-skip-permissions',
    '--allowedTools', 'Read(/**),Write(/**),Edit(/**),Bash(/**),Skill(industrial-deep-diagnostic),WebSearch,WebFetch,NotebookEdit,Task',
  ];
  if (maxTurns > 0) {
    claudeArgs.push('--max-turns', String(maxTurns));
  }

  const child = spawn(claudeBin, claudeArgs, {
    cwd: PROJECT_ROOT,
    env: buildEnv(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  // Close stdin immediately — prompt is passed via -p flag
  child.stdin.end();

  let sigkillTimer = null;

  const timeout = setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGTERM');
      sigkillTimer = setTimeout(() => {
        try { process.kill(child.pid, 'SIGKILL'); } catch {}
      }, 5000);
    }
  }, timeoutMinutes * 60 * 1000);

  child.on('close', () => {
    clearTimeout(timeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  child.on('error', () => {
    clearTimeout(timeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  child.stdout.on('error', () => {});
  child.stderr.on('error', () => {});

  return { child, prompt, projectRoot: PROJECT_ROOT, timeoutMinutes };
}

export function parseStreamLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

export function extractReportPath(output) {
  const match = output.match(/workspace\/diagnostic-runs\/[^\s]+\/report\.md/);
  return match ? match[0] : null;
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR, pendingHITL };
