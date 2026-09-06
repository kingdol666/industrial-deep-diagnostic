// OMP Client — live execution harness over the OMP CLI's RPC mode.
//
// Spawns `omp --mode=rpc` (NDJSON over stdin/stdout) and adapts its event
// stream into the same standardized message shapes the Claude Agent SDK
// emits, so diagnosis.service.mjs / chat.service.mjs can dispatch between
// the 'claude' and 'omp' engines without touching their consumption loops.
//
// Protocol (observed, protocolVersion 1):
//   → {"type":"prompt","message":"..."}       after the "ready" handshake
//   ← message_start/message_end (role: user|assistant|toolResult)
//   ← tool_execution_start/update/end (toolCallId, toolName, result)
//   ← turn_start/turn_end, agent_start/agent_end (isTerminal)

import { spawn, execFileSync } from 'child_process';
import { existsSync, mkdirSync, rmSync, readFileSync } from 'fs';
import { join, isAbsolute } from 'path';
import {
  config, PROJECT_ROOT,
} from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import {
  buildRuntimeProtocol, buildPrompt, resolveAnalysisTarget,
  isDangerousCommand, buildOntologyDirective, buildEnhancementDirective,
  DATA_DIR, WORKSPACE_DIR,
} from './claude-client.mjs';

// ── Binary resolution ──
// Node's spawn on Windows cannot execute the extensionless `omp` bash shim,
// and PATH resolution differs between shells — resolve to an absolute path.
let resolvedBinary = null;
function resolveOmpBinary() {
  if (resolvedBinary && existsSync(resolvedBinary)) return resolvedBinary;

  const configured = config.omp?.binary || 'omp';
  const candidates = [];
  if (isAbsolute(configured)) {
    candidates.push(configured);
  } else {
    // 1) `where omp` (Windows) / `which omp` (POSIX)
    try {
      const lookup = execFileSync(process.platform === 'win32' ? 'where' : 'which', [configured], {
        encoding: 'utf-8', timeout: 5000, windowsHide: true,
      });
      const first = (lookup || '').split(/\r?\n/).map(l => l.trim()).filter(Boolean)[0];
      if (first) candidates.push(first);
    } catch { /* ignore */ }
    // 2) Common install locations
    if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
      candidates.push(join(process.env.LOCALAPPDATA, 'omp', 'omp.exe'));
    }
    // 3) Bare name — works when the backend runs under a POSIX shell
    candidates.push(configured);
  }

  resolvedBinary = candidates.find(c => existsSync(c)) || candidates[candidates.length - 1];
  logger.info(`OMP binary resolved to: ${resolvedBinary}`, { context: 'OmpClient' });
  return resolvedBinary;
}

// ── Session dirs ──
function ompConfig() {
  return config.omp || {};
}

export function runSessionDir(runId) {
  const dir = join(PROJECT_ROOT, ompConfig().session_root || 'workspace/.omp-sessions', runId);
  mkdirSync(dir, { recursive: true });
  return dir;
}

export function chatSessionDir(chatId) {
  const dir = join(PROJECT_ROOT, ompConfig().chat_session_root || 'workspace/.omp-chats', chatId);
  mkdirSync(dir, { recursive: true });
  return dir;
}

// Opaque session marker stored in DB session_id columns (non-UUID by design;
// Claude-specific resume paths ignore/reject it, OMP paths parse it back).
export const OMP_SESSION_PREFIX = 'omp:';

export function ompRunSessionId(runId) {
  return `${OMP_SESSION_PREFIX}run:${runId}`;
}

export function ompChatSessionId(chatId) {
  return `${OMP_SESSION_PREFIX}chat:${chatId}`;
}

export function parseOmpSessionId(marker) {
  if (typeof marker !== 'string' || !marker.startsWith(OMP_SESSION_PREFIX)) return null;
  const rest = marker.slice(OMP_SESSION_PREFIX.length);
  if (rest.startsWith('run:')) return { kind: 'run', id: rest.slice(4) };
  if (rest.startsWith('chat:')) return { kind: 'chat', id: rest.slice(5) };
  return null;
}

// ── Spawn an OMP RPC process ──
function spawnOmpRpc({ sessionDir, resume = false, label = 'omp' }) {
  const binary = resolveOmpBinary();
  const args = ['--mode=rpc', '-p'];

  if (ompConfig().auto_approve !== false) args.push('--auto-approve');
  if (ompConfig().thinking && ompConfig().thinking !== 'auto') args.push(`--thinking=${ompConfig().thinking}`);
  if (ompConfig().timeout_minutes) args.push(`--max-time=${Math.round(ompConfig().timeout_minutes * 60)}`);
  args.push(`--session-dir=${sessionDir}`);
  if (resume) args.push('-c');

  logger.info(`Spawning ${label}: ${binary} ${args.join(' ')}`, { context: 'OmpClient' });

  const proc = spawn(binary, args, {
    cwd: PROJECT_ROOT,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    env: { ...process.env },
  });

  let stderrTail = '';
  proc.stderr.on('data', (d) => {
    stderrTail = (stderrTail + d.toString()).slice(-4000);
  });

  return { proc, stderrTailRef: () => stderrTail };
}

// ── Event adapter ──
// Wraps an OMP RPC process as an async iterable of standardized messages
// (Claude-SDK-compatible shapes), plus a close() handle.
function createOmpQuery(proc, { runKey, maxTurns = 0, label = 'omp' }) {
  const queue = [];
  let wake = null;
  let closed = false;
  let sawReady = false;
  let sawAgentEnd = false;
  let turnCount = 0;
  let startedAt = Date.now();
  const pendingToolCalls = new Map(); // toolCallId -> { name }
  const emittedToolResults = new Set(); // toolCallId already emitted (protocol reports results twice)

  const push = (msg) => { queue.push(msg); if (wake) { wake(); wake = null; } };
  const end = () => { closed = true; if (wake) { wake(); wake = null; } };

  const emitToolResultOnce = (toolCallId, text, isError) => {
    if (emittedToolResults.has(toolCallId)) return;
    emittedToolResults.add(toolCallId);
    push({
      type: 'user',
      message: {
        role: 'user',
        content: [{
          type: 'tool_result',
          tool_use_id: toolCallId,
          content: text,
          is_error: isError === true,
        }],
      },
    });
  };

  const emitAssistantMessage = (ompMessage) => {
    const blocks = [];
    for (const block of ompMessage.content || []) {
      if (block.type === 'text') {
        if (block.text && block.text.trim()) blocks.push({ type: 'text', text: block.text });
      } else if (block.type === 'thinking') {
        blocks.push({ type: 'thinking', thinking: block.thinking || '' });
      } else if (block.type === 'toolCall') {
        let input = block.arguments;
        if (typeof input === 'string') {
          try { input = JSON.parse(input); } catch { input = { raw: input }; }
        }
        blocks.push({ type: 'tool_use', id: block.id, name: block.name, input: input || {} });
        pendingToolCalls.set(block.id, { name: block.name });
      }
    }
    if (blocks.length > 0) {
      push({ type: 'assistant', message: { role: 'assistant', content: blocks } });
    }
  };

  const emitToolResult = (ompMessage) => {
    const text = (ompMessage.content || [])
      .map(b => (typeof b === 'string' ? b : b.text || ''))
      .join('\n');
    emitToolResultOnce(ompMessage.toolCallId, text, ompMessage.isError);
  };

  const emitResult = (subtype, stopReason) => {
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: turnCount,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: null,
    });
  };

  const handleLine = (line) => {
    let evt;
    try { evt = JSON.parse(line); } catch { return; }
    if (!evt || typeof evt !== 'object') return;

    switch (evt.type) {
      case 'ready':
        sawReady = true;
        break;
      case 'response':
        if (evt.command === 'prompt' && evt.success === false) {
          logger.error(`OMP rejected prompt [${label}]: ${evt.error || 'unknown'}`, { context: 'OmpClient', runKey });
          emitResult('error_during_execution', `omp_prompt_rejected: ${evt.error || 'unknown'}`);
          end();
        }
        break;
      case 'agent_start':
        startedAt = Date.now();
        turnCount = 0;
        break;
      case 'turn_start':
        turnCount += 1;
        if (maxTurns > 0 && turnCount > maxTurns) {
          logger.warn(`OMP run ${runKey} exceeded maxTurns=${maxTurns} — stopping`, { context: 'OmpClient', runKey });
          try { proc.kill(); } catch { /* ignore */ }
        }
        break;
      case 'message_start':
      case 'message_update':
        // Partial deltas are ignored — full content arrives with message_end.
        break;
      case 'message_end': {
        const role = evt.message?.role;
        if (role === 'assistant') emitAssistantMessage(evt.message);
        else if (role === 'toolResult') emitToolResult(evt.message);
        break;
      }
      case 'tool_execution_start':
        pendingToolCalls.set(evt.toolCallId, { name: evt.toolName || 'tool' });
        break;
      case 'tool_execution_end': {
        // Results also arrive as a toolResult message_end — emitToolResultOnce dedupes.
        const resultText = (evt.result?.content || [])
          .map(c => (typeof c === 'string' ? c : c.text || ''))
          .join('\n');
        emitToolResultOnce(evt.toolCallId, resultText, evt.result?.isError || evt.isError);
        break;
      }
      case 'agent_end':
        sawAgentEnd = true;
        emitResult('success', 'success');
        end();
        break;
      case 'notice':
        if (evt.level === 'error') {
          push({ type: 'system', subtype: 'notice', data: { message: evt.message } });
        }
        break;
      default:
        // extension_ui_request / available_commands_update / turn_end / etc.
        break;
    }
  };

  let lineBuf = '';
  proc.stdout.on('data', (d) => {
    lineBuf += d.toString();
    let idx;
    while ((idx = lineBuf.indexOf('\n')) >= 0) {
      const line = lineBuf.slice(0, idx).trim();
      lineBuf = lineBuf.slice(idx + 1);
      if (line) handleLine(line);
    }
  });

  proc.on('exit', (code) => {
    if (!sawAgentEnd) {
      logger.error(`OMP process exited before agent_end [${label}] code=${code}`, { context: 'OmpClient', runKey });
      emitResult('error_during_execution', `omp_process_exit:${code ?? 'null'}`);
    }
    end();
  });

  proc.on('error', (err) => {
    logger.error(`OMP process error [${label}]: ${err.message}`, { context: 'OmpClient', runKey });
    emitResult('error_during_execution', `omp_spawn_error: ${err.message}`);
    end();
  });

  return {
    async sendPrompt(message) {
      if (closed) throw new Error('OMP process already closed');
      if (!sawReady) {
        await Promise.race([
          new Promise(resolve => {
            const check = () => { if (sawReady || closed) resolve(); else setTimeout(check, 50); };
            check();
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('OMP RPC handshake timeout (no ready event)')), 30000)),
        ]);
      }
      proc.stdin.write(`${JSON.stringify({ type: 'prompt', message })}\n`);
    },
    close() {
      closed = true;
      try { proc.kill(); } catch { /* ignore */ }
    },
    get killed() { return proc.killed || proc.exitCode !== null; },
    async *[Symbol.asyncIterator]() {
      while (true) {
        if (queue.length > 0) {
          yield queue.shift();
          continue;
        }
        if (closed) return;
        await new Promise(resolve => { wake = resolve; });
      }
    },
  };
}

// ── Start Diagnosis via OMP ──
export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
  ontology = null, enhancement = null,
}) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const ompSession = parseOmpSessionId(sessionId);
  const isResume = !!ompSession;

  const { dataPaths, promptTarget } = resolveAnalysisTarget(isResume ? { mode: 'resume' } : analysisTarget);

  const sessionDir = runSessionDir(runId);
  const { proc } = spawnOmpRpc({ sessionDir, resume: isResume, label: `omp-diagnosis:${runId}` });
  const query = createOmpQuery(proc, { runKey: runId, maxTurns, label: `omp-diagnosis:${runId}` });

  let prompt;
  if (isResume) {
    // Clean continuation — the session already carries the pipeline context.
    prompt = (followUpMessage || 'Continue.').replace(/[\x00-\x08\x0A-\x1F]/g, (c) => (c === '\n' ? '\n' : '')).trim();
  } else {
    // OMP discovers .claude/skills natively; point it at the skill explicitly
    // and inline the runtime protocol (avoiding oversized argv payloads).
    const skillMd = join(PROJECT_ROOT, config.claude.skill_dir || '.claude/skills/industrial-analysis-auto', 'SKILL.md');
    const skillRef = existsSync(skillMd)
      ? `First read the authoritative skill definition at ${skillMd} and follow its full pipeline contract as binding.`
      : `Follow the industrial deep diagnostic skill protocol (industrial-analysis-auto).`;
    prompt = `${buildRuntimeProtocol(sceneName, lang)}

${skillRef}

${buildPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)}${buildOntologyDirective(ontology)}${buildEnhancementDirective(enhancement)}`;
  }

  query.sendPrompt(prompt).catch(err => {
    logger.error(`OMP sendPrompt failed for ${runId}: ${err.message}`, { context: 'OmpClient', runId });
    query.close();
  });

  query.sessionId = ompRunSessionId(runId);

  return {
    query,
    dataPaths,
    prompt,
    getSessionId: () => ompRunSessionId(runId),
    runId,
    isResume,
  };
}

// ── Session chat: continue the run's OMP session with a follow-up message ──
export function startSessionChat({ runId, sessionId, message, maxTurns = 1 }) {
  const ompSession = parseOmpSessionId(sessionId);
  if (!ompSession) {
    const err = new Error('No valid OMP session ID for selected diagnosis session');
    err.status = 400;
    throw err;
  }

  const sessionDir = runSessionDir(ompSession.id);
  const { proc } = spawnOmpRpc({ sessionDir, resume: true, label: `omp-chat:${runId}` });
  const query = createOmpQuery(proc, { runKey: runId, maxTurns, label: `omp-chat:${runId}` });

  const text = (message || '').replace(/[\x00-\x08]/g, '').trim();
  query.sendPrompt(text).catch(err => {
    logger.error(`OMP chat sendPrompt failed for ${runId}: ${err.message}`, { context: 'OmpClient', runId });
    query.close();
  });

  query.sessionId = sessionId;

  return { query, runId, sessionId };
}

// ── Chat engine (chat.service.mjs OMP branch) ──
export function startChatQuery({ chatId, prompt, resume = false, maxTurns = 0 }) {
  const sessionDir = chatSessionDir(chatId);
  const { proc } = spawnOmpRpc({ sessionDir, resume, label: `omp-webchat:${chatId}` });
  const query = createOmpQuery(proc, { runKey: chatId, maxTurns, label: `omp-webchat:${chatId}` });

  query.sendPrompt(prompt).catch(err => {
    logger.error(`OMP webchat sendPrompt failed for ${chatId}: ${err.message}`, { context: 'OmpClient', chatId });
    query.close();
  });

  query.sessionId = ompChatSessionId(chatId);

  return query;
}

export function deleteChatArtifacts(chatId) {
  const dir = join(PROJECT_ROOT, ompConfig().chat_session_root || 'workspace/.omp-chats', chatId);
  let removed = false;
  try {
    if (existsSync(dir)) {
      rmSync(dir, { recursive: true, force: true });
      removed = true;
    }
  } catch (e) {
    logger.warn(`Failed to remove OMP chat artifacts for ${chatId}: ${e.message}`, { context: 'OmpClient', chatId });
  }
  return removed;
}

// ── Standardized-event passthrough ──
// The adapter already emits standardized messages; parsing is a no-op.
export function parseStreamEvent(message) {
  if (!message || typeof message !== 'object') return null;
  return message;
}

// ── Query registry (mirrors claude-client for stop/close semantics) ──
const activeQueries = new Map();

export function registerChild(runId, query) {
  activeQueries.set(runId, query);
}

export function closeQuery(runId) {
  const query = activeQueries.get(runId);
  if (query) {
    try { query.close(); } catch { /* ignore */ }
    activeQueries.delete(runId);
  }
}

export async function writeAnswer(runId, message) {
  const query = activeQueries.get(runId);
  if (!query) return false;
  try {
    await query.sendPrompt(message);
    return true;
  } catch {
    return false;
  }
}

// ── Health probe: verify the OMP binary actually executes ──
export function probeOmpEngine() {
  return new Promise(resolve => {
    const binary = resolveOmpBinary();
    const timeoutMs = ompConfig().health_timeout_ms || 8000;
    let settled = false;
    const done = (result) => {
      if (!settled) { settled = true; resolve(result); }
    };

    let proc;
    try {
      proc = spawn(binary, ['--version'], { stdio: 'pipe', windowsHide: true, cwd: PROJECT_ROOT });
    } catch (e) {
      done({ available: false, binary, error: e.message });
      return;
    }

    let out = '';
    const timer = setTimeout(() => {
      try { proc.kill(); } catch { /* ignore */ }
      done({ available: false, binary, error: `timeout after ${timeoutMs}ms` });
    }, timeoutMs);

    proc.stdout.on('data', d => { out += d.toString(); });
    proc.on('error', (e) => {
      clearTimeout(timer);
      done({ available: false, binary, error: e.message });
    });
    proc.on('exit', (code) => {
      clearTimeout(timer);
      const version = (out.match(/omp\/(\S+)/) || [])[1] || out.trim().split(/\r?\n/)[0] || null;
      done({ available: code === 0, binary, version, raw: out.trim().slice(0, 100) });
    });
  });
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
