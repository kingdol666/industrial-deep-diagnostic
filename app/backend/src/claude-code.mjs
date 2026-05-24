import { spawn, execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
const DATA_DIR = join(PROJECT_ROOT, 'data');
const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');

const SKILL_DIR = join(PROJECT_ROOT, '.claude', 'skills', 'industrial-deep-diagnostic');
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');

// Minimal env vars the Claude CLI needs — avoid leaking secrets
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
  return env;
}

function findClaudeCLI() {
  try {
    return execSync('which claude', { encoding: 'utf-8', timeout: 3000 }).trim();
  } catch {
    try {
      const alt = execSync('which claude-code', { encoding: 'utf-8', timeout: 3000 }).trim();
      return alt;
    } catch {
      return null;
    }
  }
}

function sanitize(str) {
  // Strip characters that could enable prompt injection via newlines or markup
  return str.replace(/[\x00-\x08\x0A-\x1F]/g, '').trim();
}

function buildPrompt(sceneName, userQuestion, dataPath) {
  const safeScene = sanitize(sceneName);
  const safeQuestion = sanitize(userQuestion || '');

  return `Execute the /industrial-deep-diagnostic skill on industrial data.

## Input

- **Data file**: ${dataPath}
- **Scene name**: ${safeScene}
- **Analysis question**: ${safeQuestion || 'Perform a comprehensive root cause analysis'}

## Instructions

1. Invoke the /industrial-deep-diagnostic skill with the scene name "${safeScene}"
2. The skill will guide you through the 8-step pipeline: setup, data inspection, ontology building, statistical analysis, visualization, diagnosis, judge review, and report generation
3. All output artifacts go to workspace/diagnostic-runs/<run_dir>/
4. After completing all pipeline steps and passing the judge quality gate (score >= 90), present the final report

## Critical Rules

- Evidence first. Reasoning second. Conclusions last.
- Every root cause claim must satisfy ALL four criteria: temporal precedence, statistical evidence, physical mechanism, no contradicting evidence
- Missing any criterion -> label as [HYPOTHESIS]
- Use the statistical validation framework to catch confounders`;
}

export function startDiagnosis({ dataPath, userQuestion, sceneName, runId, maxTurns = 200, timeoutMinutes = 30 }) {
  const absoluteDataPath = dataPath.startsWith('/')
    ? dataPath
    : join(PROJECT_ROOT, dataPath);

  if (!existsSync(absoluteDataPath)) {
    const err = new Error(`Data path not found: ${absoluteDataPath}`);
    err.code = 'DATA_NOT_FOUND';
    throw err;
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

  const prompt = buildPrompt(sceneName, userQuestion, dataPath);

  const claudeArgs = [
    '-p', prompt,
    '--output-format', 'stream-json',
    '--max-turns', String(maxTurns),
    '--verbose',
    '--allowedTools', 'Read(/**),Write(/**),Edit(/**),Bash(/**),Skill(industrial-deep-diagnostic),WebSearch,WebFetch',
  ];

  const child = spawn(claudeBin, claudeArgs, {
    cwd: PROJECT_ROOT,
    env: buildEnv(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let sigkillTimer = null;

  const timeout = setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGTERM');
      // Schedule SIGKILL escalation — store handle so we can clear it
      sigkillTimer = setTimeout(() => {
        // Use kill(pid, signal) directly since child.killed is set synchronously by Node
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

  // Prevent unhandled stream errors from crashing the process
  child.stdout.on('error', () => {});
  child.stderr.on('error', () => {});

  return { child, prompt, projectRoot: PROJECT_ROOT };
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

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
