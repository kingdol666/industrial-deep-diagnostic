import { spawn, execSync } from 'child_process';
import { existsSync, readdirSync } from 'fs';
import { join, extname, basename } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';

const DATA_DIR = join(PROJECT_ROOT, config.data.dir);
const WORKSPACE_DIR = join(PROJECT_ROOT, config.data.workspace_dir);
const SKILL_DIR = join(PROJECT_ROOT, config.claude.skill_dir);
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');

function buildEnv() {
  const env = {};
  for (const key of config.security.allowed_env_vars) {
    if (process.env[key] !== undefined) {
      env[key] = process.env[key];
    }
  }
  // Fallback: use config values when env vars are missing (e.g. backend runs under sudo)
  if (!env.ANTHROPIC_BASE_URL && config.claude.api_base_url) {
    env.ANTHROPIC_BASE_URL = config.claude.api_base_url;
  }
  if (!env.ANTHROPIC_API_KEY && config.claude.api_key) {
    env.ANTHROPIC_API_KEY = config.claude.api_key;
  }
  if (!env.ANTHROPIC_AUTH_TOKEN && config.claude.api_auth_token) {
    env.ANTHROPIC_AUTH_TOKEN = config.claude.api_auth_token;
  }
  env.FORCE_COLOR = '0';
  env.NO_COLOR = '1';
  env.SKILL_PATH = SKILL_DIR;
  return env;
}

function findClaudeCLI() {
  const bins = [config.claude.binary, config.claude.fallback_binary];
  for (const bin of bins) {
    try {
      return execSync(`which ${bin}`, { encoding: 'utf-8', timeout: 3000 }).trim();
    } catch { /* try next */ }
  }
  return null;
}

function sanitize(str) {
  return str.replace(/[\x00-\x08\x0A-\x1F]/g, '').trim();
}

function discoverDataFiles(folderPath) {
  const absolutePath = folderPath.startsWith('/')
    ? folderPath
    : join(PROJECT_ROOT, folderPath);
  const entries = readdirSync(absolutePath);
  const exts = config.data.allowed_extensions;
  return entries
    .filter(e => exts.includes(extname(e).toLowerCase()))
    .map(e => join(absolutePath, e))
    .sort();
}

function buildPrompt(sceneName, userQuestion, target, reportLanguage, followUpMessage) {
  const safeScene = sanitize(sceneName || config.diagnosis.default_scene_name);
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

  const basePrompt = `${config.claude.skill_command} ${safeScene}

## Data

${dataDescription}

## Analysis Question

${safeQuestion || config.diagnosis.default_question}

## Language

${langRule}`;

  if (followUpMessage) {
    return `${basePrompt}

## Follow-Up Instruction

The previous run ended. Additional instruction from user:

${sanitize(followUpMessage)}

Please address the follow-up instruction above and continue the analysis.`;
  }

  return basePrompt;
}

// Build dangerous command patterns from config
const DANGEROUS_PATTERNS = config.security.dangerous_patterns.map(rule => ({
  pattern: new RegExp(rule.pattern),
  level: rule.level,
  desc: rule.desc,
}));

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

export function startDiagnosis({ analysisTarget, userQuestion, sceneName, runId: _runId, maxTurns = 0, timeoutMinutes = 0, reportLanguage, followUpMessage }) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const timeout = timeoutMinutes || config.claude.timeout_minutes;

  let dataPaths = [];

  function resolveDataPath(p) {
    if (p.startsWith('/')) return p;
    const fromRoot = join(PROJECT_ROOT, p);
    if (existsSync(fromRoot)) return fromRoot;
    const fromData = join(DATA_DIR, p);
    if (existsSync(fromData)) return fromData;
    return fromRoot;
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

  const prompt = buildPrompt(sceneName, userQuestion, analysisTarget, lang, followUpMessage);

  const allowedTools = config.claude.allowed_tools;
  const claudeArgs = [
    '-p', prompt,
    '--output-format', config.claude.output_format,
    '--verbose',
    '--dangerously-skip-permissions',
    '--allowedTools', allowedTools,
  ];
  if (maxTurns > 0) {
    claudeArgs.push('--max-turns', String(maxTurns));
  }

  const child = spawn(claudeBin, claudeArgs, {
    cwd: PROJECT_ROOT,
    env: buildEnv(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let sigkillTimer = null;
  const graceMs = (config.claude.sigkill_grace_seconds || 5) * 1000;

  const killTimeout = setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGTERM');
      sigkillTimer = setTimeout(() => {
        try { process.kill(child.pid, 'SIGKILL'); } catch {}
      }, graceMs);
    }
  }, timeout * 60 * 1000);

  child.on('close', () => {
    clearTimeout(killTimeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  child.on('error', () => {
    clearTimeout(killTimeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  child.stdout.on('error', () => {});
  child.stderr.on('error', () => {});

  return { child, prompt, projectRoot: PROJECT_ROOT, timeoutMinutes: timeout };
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

// Active child processes tracked by runId for stdin writing (question answering)
const activeChildren = new Map();

export function registerChild(runId, child) {
  activeChildren.set(runId, child);
}

export function unregisterChild(runId) {
  activeChildren.delete(runId);
}

export function writeAnswer(runId, answerJson) {
  const child = activeChildren.get(runId);
  if (!child || child.killed) {
    return false;
  }
  try {
    child.stdin.write(JSON.stringify(answerJson) + '\n');
    return true;
  } catch {
    return false;
  }
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR, pendingHITL };
