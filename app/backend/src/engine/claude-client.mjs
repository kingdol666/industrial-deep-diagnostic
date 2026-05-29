// Claude Client — wraps the Claude Agent SDK for diagnostic runs
// Replaces the old child_process-based Claude CLI execution.

import { existsSync, readdirSync, readFileSync } from 'fs';
import { join, extname, basename } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

// Dynamic SDK import (ESM-only module)
let queryFn = null;
let sdkAvailable = true;

try {
  const sdk = await import('@anthropic-ai/claude-agent-sdk');
  queryFn = sdk.query;
} catch (e) {
  sdkAvailable = false;
  logger.error(`SDK not available: ${e.message}`, { context: 'ClaudeClient' });
}

const DATA_DIR = join(PROJECT_ROOT, config.data.dir);
const WORKSPACE_DIR = join(PROJECT_ROOT, config.data.workspace_dir);
const SKILL_DIR = join(PROJECT_ROOT, config.claude.skill_dir);
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');

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

// ── Dangerous Command Detection ──
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

// ── Disallowed tool names ──
const disallowedTools = [];

// ── Active query objects (for close and stdin writing) ──
const activeQueries = new Map();

// ── Start Diagnosis via SDK ──
export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
}) {
  if (!sdkAvailable || !queryFn) {
    throw new Error('Claude Agent SDK not available. Install with: npm install @anthropic-ai/claude-agent-sdk');
  }

  const lang = reportLanguage || config.diagnosis.default_language;
  const timeout = timeoutMinutes || config.claude.timeout_minutes;
  let dataPaths = [];

  // Resolve data paths
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

  // Read skill content for system prompt enrichment
  let skillContent = '';
  if (existsSync(SKILL_MD)) {
    try {
      skillContent = readFileSync(SKILL_MD, 'utf-8').slice(0, 8000);
    } catch { /* ignore */ }
  }

  const prompt = sessionId
    ? (followUpMessage || 'Continue the analysis.')
    : buildPrompt(sceneName, userQuestion, analysisTarget, lang, followUpMessage);

  // Build SDK options
  const options = {
    cwd: PROJECT_ROOT,
    model: config.claude.model,
    permissionMode: 'bypassPermissions',
    allowDangerouslySkipPermissions: true,
    includePartialMessages: true,
    forwardSubagentText: true,
    maxTurns: maxTurns > 0 ? maxTurns : undefined,
  };

  if (sessionId) {
    options.resume = sessionId;
  }

  // Start the SDK query
  const query = queryFn({ prompt, options });

  // Register for later reference
  activeQueries.set(runId, query);

  const getSessionId = () => query.sessionId || null;

  return { query, dataPaths, prompt, getSessionId, runId };
}

// ── Write tool_result to the query (for AskUserQuestion answers) ──
export async function writeAnswer(runId, message) {
  const query = activeQueries.get(runId);
  if (!query) return false;

  try {
    // Send the user message as an async iterable
    await query.streamInput(
      (async function* () {
        yield message;
      })()
    );
    return true;
  } catch (e) {
    logger.error(`writeAnswer failed: ${e.message}`, { context: 'ClaudeClient', runId });
    return false;
  }
}

// ── Close / kill a query ──
export function closeQuery(runId) {
  const query = activeQueries.get(runId);
  if (query) {
    try { query.close(); } catch { /* ignore */ }
    activeQueries.delete(runId);
  }
}

// ── Parse SDK stream event into standardized format ──
export function parseStreamEvent(message) {
  // The SDK emits various message types:
  // - SDKAssistantMessage: { type: 'assistant', message: { content: [...] } }
  // - SDKUserMessage: { type: 'user', message: { role: 'user', content: [...] } }
  // - SDKResultMessage: { type: 'result', subtype, duration_ms, num_turns, total_cost_usd, ... }
  // - SDKPartialAssistantMessage: { type: 'stream_event', ... } (partial text chunks)

  if (!message || typeof message !== 'object') return null;

  const type = message.type;

  if (type === 'assistant') {
    return { type: 'assistant', message: message.message };
  } else if (type === 'user') {
    return { type: 'user', message: message.message };
  } else if (type === 'result') {
    return {
      type: 'result',
      subtype: message.subtype,
      duration_ms: message.duration_ms,
      num_turns: message.num_turns,
      total_cost_usd: message.total_cost_usd,
      stop_reason: message.stop_reason,
      session_id: message.session_id,
    };
  } else if (type === 'system') {
    return { type: 'system', subtype: message.subtype || 'system', ...message };
  } else if (type === 'stream_event') {
    return { type: 'stream_event', event: message.event };
  }

  // Fallback — pass through
  return message;
}

// ── Extract report path from output ──
export function extractReportPath(output) {
  const match = output.match(/workspace\/diagnostic-runs\/[^\s]+\/report\.md/);
  return match ? match[0] : null;
}

// ── Legacy compat: registerChild / writeAnswer (for diagnosis.service.mjs) ──
const _noop = {};
export function registerChild(runId, _query) {
  // Stub — SDK manages child processes internally
  activeQueries.set(runId, _query);
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
