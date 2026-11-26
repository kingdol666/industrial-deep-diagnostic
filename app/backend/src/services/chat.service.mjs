// Chat Service — direct Claude Agent SDK chat with streaming SSE
// Supports custom config: model, permissionMode, maxTurns, tools, session resume

import { EventEmitter } from 'events';
import { existsSync, readdirSync, rmSync } from 'fs';
import { homedir } from 'os';
import { join, resolve } from 'path';
import logger from '../utils/logger.mjs';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT, config } from '../../../../config/loader.mjs';
import * as ompClient from '../engine/omp-client.mjs';
import { getEngineClient } from '../harness/engines.mjs';
import { hasHarness } from '../harness/registry.mjs';
import { validateEngineOption } from '../harness/engine-options.mjs';
import { canView, resolveOwnerId, INTERNAL } from './tenancy.mjs';

let queryFn = null;
try {
  const sdk = await import('@anthropic-ai/claude-agent-sdk');
  queryFn = sdk.query;
} catch (e) {
  logger.error(`Chat SDK init failed: ${e.message}`, { context: 'Chat' });
}

// Active chat sessions: chatId -> { query, emitter }
const activeChats = new Map();
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MISSING_CONVERSATION_RE = /No conversation found with session ID/i;

// Chat runs on every registered harness: claude (SDK) and omp (RPC) keep
// their dedicated resident-session paths; every definition-table engine
// (mock / one-shot family / ACP family / codex / opencode) rides the
// generic turn path below — native session resume when the engine supports
// it, transcript replay when it does not. Never a silent engine swap.
const DEDICATED_CHAT_HARNESSES = new Set(['claude', 'omp']);

function normalizeChatHarness(value) {
  const id = typeof value === 'string' ? value.trim().toLowerCase() : '';
  if (!id) return (config.harness?.default || 'omp') === 'omp' ? 'omp' : 'claude';
  if (DEDICATED_CHAT_HARNESSES.has(id)) return id;
  if (hasHarness(id)) return id;
  const err = new Error(
    `Unknown chat harness: "${id}" — see GET /api/harness for the registry. `
    + `Diagnoses accept the same ids via POST /api/diagnosis/start.`,
  );
  err.status = 400;
  err.code = 'CHAT_HARNESS_UNSUPPORTED';
  throw err;
}

// ── Tenancy (P0-6) ──────────────────────────────────────────────────────────
// A chat session is visible/administrable to its owner (or an admin); a NULL
// owner (created while AUTH_ENABLED=0) is admin-only. Every read/act below
// answers a foreign session exactly like a missing one (null / false → 404);
// `viewer` is req.user for API callers and INTERNAL for trusted internal calls.

/** May `viewer` see/act on this stored chat row? (No row → true: new chat.) */
function canViewChat(viewer, stored) {
  if (!stored) return true; // no persisted session yet — creation is allowed
  return canView(viewer, stored.owner_user_id);
}

function chatNotFoundError() {
  const err = new Error('Chat session not found');
  err.status = 404;
  err.code = 'CHAT_NOT_FOUND';
  return err;
}

function externalResumeError() {
  const err = new Error('客户端提供的 Claude session 不能直接恢复，请先从所属 Chat 继续对话');
  err.status = 400;
  err.code = 'CHAT_RESUME_FORBIDDEN';
  return err;
}

// A stored chat is OMP-backed when its harness column says so or its
// session marker is an OMP opaque id (omp:chat:<chatId>).
function storedChatIsOmp(stored) {
  if (!stored) return false;
  return stored.harness === 'omp'
    || ompClient.parseOmpSessionId(stored.session_id) !== null
    || ompClient.parseOmpSessionId(stored.origin_session_id) !== null;
}
const ALLOWED_PERMISSION_MODES = new Set([
  'default',
  'acceptEdits',
  'bypassPermissions',
  'plan',
  'dontAsk',
  'auto',
]);

function normalizeClaudeSessionId(value) {
  if (!value || typeof value !== 'string') return null;
  const trimmed = value.trim();
  return UUID_RE.test(trimmed) ? trimmed : null;
}

function getOriginSessionId(source) {
  if (!source) return null;
  return normalizeClaudeSessionId(source.origin_session_id || source.originSessionId || null);
}

function getEffectiveResumeSessionId(source) {
  if (!source) return null;
  return getOriginSessionId(source)
    || normalizeClaudeSessionId(source.session_id || source.sessionId || null)
    || null;
}

function getLiveSessionId(source) {
  if (!source) return null;
  return normalizeClaudeSessionId(source.sessionId)
    || normalizeClaudeSessionId(source.query?.sessionId)
    || getEffectiveResumeSessionId(source)
    || null;
}

function normalizePermissionMode(value, fallback = 'default') {
  if (typeof value !== 'string') return fallback;
  const trimmed = value.trim();
  return ALLOWED_PERMISSION_MODES.has(trimmed) ? trimmed : fallback;
}

function normalizeChatCwd(value, fallback = PROJECT_ROOT) {
  const raw = typeof value === 'string' && value.trim() ? value.trim() : fallback;
  const resolved = resolve(raw);
  if (!existsSync(resolved)) {
    const err = new Error(`Working directory not found: ${resolved}`);
    err.status = 400;
    throw err;
  }
  return resolved;
}

function isStartedChatSession(source) {
  if (!source) return false;
  return Boolean(source.chat_id || source.chatId || source.status === 'active' || source.status === 'completed' || source.status === 'failed' || source.status === 'stopped');
}

function safeRemovePath(targetPath, removedPaths) {
  if (!targetPath || !existsSync(targetPath)) return;
  rmSync(targetPath, { recursive: true, force: true });
  removedPaths.push(targetPath);
}

function collectClaudeSessionArtifactPaths(sessionId) {
  const normalized = normalizeClaudeSessionId(sessionId);
  if (!normalized) return [];

  const claudeRoot = join(homedir(), '.claude');
  const candidates = [
    join(claudeRoot, 'security', `security_warnings_state_${normalized}.json`),
    join(claudeRoot, 'security', `security_warnings_state_${normalized}.lock`),
    join(claudeRoot, 'session-env', normalized),
    join(claudeRoot, 'hud', 'cache', `stdin.${normalized}.json`),
    join(claudeRoot, 'hud', 'cache', `statusline.${normalized}.txt`),
  ];

  const projectsRoot = join(claudeRoot, 'projects');
  if (existsSync(projectsRoot)) {
    for (const workspaceName of readdirSync(projectsRoot)) {
      const workspaceDir = join(projectsRoot, workspaceName);
      candidates.push(join(workspaceDir, `${normalized}.jsonl`));
      candidates.push(join(workspaceDir, normalized));
    }
  }

  return candidates;
}

function deleteClaudeSessionArtifacts(sessionIds = []) {
  const removedPaths = [];
  const seen = new Set();

  for (const rawSessionId of sessionIds) {
    const sessionId = normalizeClaudeSessionId(rawSessionId);
    if (!sessionId || seen.has(sessionId)) continue;
    seen.add(sessionId);
    for (const targetPath of collectClaudeSessionArtifactPaths(sessionId)) {
      safeRemovePath(targetPath, removedPaths);
    }
  }

  return removedPaths;
}

/**
 * Start a chat session with full streaming support.
 * `params.ownerUserId` (a user object or an id) is persisted as the session's
 * owner_user_id; absent/null → NULL row (unowned, admin-only with auth on).
 * Returns { chatId, emitter } — the emitter fires SSE-compatible events.
 */
export async function startChat(params = {}) {
  const ownerUserId = resolveOwnerId(params.ownerUserId);
  const viewer = params.viewer ?? INTERNAL;
  const requestedChatId = params.chatId;
  const earlyChatId = requestedChatId || `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const earlyStored = stmts.getChatSessionByChatId.get(earlyChatId);
  if (earlyStored && !canViewChat(viewer, earlyStored)) throw chatNotFoundError();

  const requestedSessionId = normalizeClaudeSessionId(params.originSessionId)
    || normalizeClaudeSessionId(params.sessionId);
  const trustedStoredSessionId = getEffectiveResumeSessionId(earlyStored);
  if (requestedSessionId && (!earlyStored || requestedSessionId !== trustedStoredSessionId)) {
    throw externalResumeError();
  }

  // Harness resolution: an existing chat is sticky to its original engine —
  // the global selector only decides the engine for NEW chats.
  const harness = storedChatIsOmp(earlyStored)
    ? 'omp'
    : (earlyStored ? normalizeChatHarness(earlyStored.harness || params.harness || 'claude')
                   : normalizeChatHarness(params.harness));

  // Model / permission-mode selections must exist in the harness's own catalog
  // — same gate as diagnosis run creation, so both surfaces 400 identically
  // (mock is scripted in-process and has no real option surface to check).
  if (harness !== 'mock' && (params.model || params.permissionMode)) {
    const check = validateEngineOption(harness, {
      model: params.model || null,
      permissionMode: params.permissionMode || null,
    });
    if (!check.ok) {
      const err = new Error(check.errors.map((e) => e.message).join(' | '));
      err.status = 400;
      err.code = check.errors[0].code;
      throw err;
    }
  }

  if (harness === 'omp') {
    return startOmpChat({
      chatId: earlyChatId,
      prompt: params.prompt,
      stored: earlyStored,
      title: params.title,
      ownerUserId,
    });
  }

  // ── Generic definition-table engines (mock / one-shot / ACP / codex / opencode) ──
  if (harness !== 'claude') {
    return startGenericEngineChat({
      chatId: earlyChatId,
      prompt: params.prompt,
      stored: earlyStored,
      title: params.title,
      harness,
      model: params.model || null,
      ownerUserId,
    });
  }

  // ── Claude harness path ──
  if (!queryFn) throw new Error('Claude Agent SDK not available');

  const {
    chatId: _chatIdUnused,
    prompt,
    model,
    permissionMode = 'default',
    maxTurns,
    cwd,
    extraArgs,      // additional CLI args
    systemPrompt,   // system prompt override
    tools,          // allowed tools list
    env,            // environment vars
    effort,         // 'low'|'medium'|'high'|'xhigh'|'max'
    thinking,       // { type: 'adaptive' } | { type: 'enabled', budgetTokens: N }
    forkSession,    // fork on resume
    title,
  } = params;

  if (!prompt || typeof prompt === 'undefined' || typeof prompt !== 'string') {
    throw new Error('prompt is required');
  }

  const chatId = earlyChatId;
  const existingSession = earlyStored;
  const sessionId = getEffectiveResumeSessionId(existingSession);
  const emitter = new EventEmitter();
  const normalizedPermissionMode = normalizePermissionMode(permissionMode, 'default');
  const normalizedCwd = normalizeChatCwd(cwd, PROJECT_ROOT);
  if (sessionId && existingSession) {
    const existingCwd = normalizeChatCwd(existingSession.cwd || PROJECT_ROOT, PROJECT_ROOT);
    if ((sessionId || isStartedChatSession(existingSession)) && normalizedCwd !== existingCwd) {
      const err = new Error('当前聊天已经绑定到既有 Claude session，不能在续聊时切换工作目录。请新建 Chat 后再选择新的工作目录。');
      err.status = 400;
      err.code = 'CHAT_CWD_IMMUTABLE';
      throw err;
    }
  }

  // Build SDK options
  const options = {
    permissionMode: normalizedPermissionMode,
    allowDangerouslySkipPermissions: normalizedPermissionMode === 'bypassPermissions',
    includePartialMessages: true,
    forwardSubagentText: true,
    model: model || undefined,
    cwd: normalizedCwd,
    maxTurns: maxTurns || undefined,
    effort: effort || undefined,
    thinking: thinking || undefined,
  };

  if (sessionId) {
    options.resume = sessionId;
    options.forkSession = !!forkSession;
  }

  if (systemPrompt) options.systemPrompt = systemPrompt;
  if (extraArgs) options.extraArgs = extraArgs;
  if (tools) options.tools = tools;

  // Start SDK query
  const query = queryFn({ prompt, options });
  const sdkSessionId = query.sessionId || null;
  activeChats.set(chatId, {
    query,
    emitter,
    sessionId: sdkSessionId || null,
    originSessionId: sessionId || null,
  });

  if (existingSession) {
    stmts.updateChatSession.run({
      chatId,
      title: title || null,
      sessionId: sdkSessionId,
      originSessionId: getOriginSessionId(existingSession) || sdkSessionId,
      permissionMode: normalizedPermissionMode,
      cwd: normalizedCwd,
      status: 'active',
      harness: 'claude',
    });
  } else {
    stmts.insertChatSession.run({
      chatId,
      title: title || prompt.slice(0, 60),
      sessionId: sdkSessionId,
      originSessionId: sdkSessionId,
      status: 'active',
      model: model || 'default',
      permissionMode: normalizedPermissionMode,
      cwd: normalizedCwd,
      harness: 'claude',
      ownerUserId,
    });
  }
  stmts.insertChatMessage.run({
    chatId,
    role: 'user',
    content: prompt,
    eventType: 'user_message',
    eventSubtype: null,
  });

  // Emit init event with session info
  emitter.emit('event', 'chat_init', {
    chatId,
    sessionId: sdkSessionId,
    model: model || 'default',
    permissionMode: normalizedPermissionMode,
    cwd: normalizedCwd,
    timestamp: new Date().toISOString(),
  });

  // Iterate SDK messages and emit as SSE events
  (async () => {
    try {
      for await (const msg of query) {
        if (!msg || typeof msg !== 'object') continue;

        const liveSessionId = normalizeClaudeSessionId(msg.session_id) || normalizeClaudeSessionId(query.sessionId);
        if (liveSessionId) {
          const entry = activeChats.get(chatId);
          if (entry) {
            entry.sessionId = liveSessionId;
            if (!entry.originSessionId) entry.originSessionId = liveSessionId;
          }
        }

        const type = msg.type;

        if (type === 'system') {
          emitter.emit('event', 'system', { subtype: msg.subtype || 'system', ...msg });
          // Capture sessionId from init event
          if (msg.subtype === 'init' && msg.session_id) {
            const entry = activeChats.get(chatId);
            if (entry) {
              entry.sessionId = msg.session_id;
              if (!entry.originSessionId) entry.originSessionId = msg.session_id;
              // Re-emit chat_init now that we have the sessionId
              emitter.emit('event', 'chat_init', {
                chatId,
                sessionId: liveSessionId,
                model: msg.model || 'unknown',
                permissionMode: normalizedPermissionMode,
                cwd: normalizedCwd,
                timestamp: new Date().toISOString(),
              });
              stmts.updateChatSession.run({
                chatId,
                title: null,
                sessionId: liveSessionId,
                originSessionId: liveSessionId,
                permissionMode: normalizedPermissionMode,
                cwd: normalizedCwd,
                harness: null,
                status: 'active',
                harness: 'claude',
              });
            }
          }
          stmts.insertChatMessage.run({
            chatId,
            role: 'system',
            content: JSON.stringify({ subtype: msg.subtype || 'system' }),
            eventType: 'system',
            eventSubtype: msg.subtype || 'system',
          });
        } else if (type === 'assistant') {
          const content = msg.message?.content || [];
          for (const block of content) {
            if (block.type === 'text') {
              emitter.emit('event', 'message', { role: 'assistant', content: block.text });
              stmts.insertChatMessage.run({
                chatId,
                role: 'assistant',
                content: block.text,
                eventType: 'message',
                eventSubtype: 'text',
              });
            } else if (block.type === 'tool_use') {
              emitter.emit('event', 'tool_use', { name: block.name, input: block.input, id: block.id });
              stmts.insertChatMessage.run({
                chatId,
                role: 'assistant',
                content: JSON.stringify({ name: block.name, input: block.input, id: block.id }),
                eventType: 'tool_use',
                eventSubtype: block.name,
              });
            } else if (block.type === 'thinking') {
              emitter.emit('event', 'thinking', { content: block.thinking?.slice(0, 500) || '' });
              stmts.insertChatMessage.run({
                chatId,
                role: 'assistant',
                content: block.thinking?.slice(0, 500) || '',
                eventType: 'thinking',
                eventSubtype: null,
              });
            }
          }
        } else if (type === 'user') {
          const content = msg.message?.content || [];
          for (const block of content) {
            if (block.type === 'tool_result') {
              const summary = typeof block.content === 'string'
                ? block.content.slice(0, 300)
                : '';
              emitter.emit('event', 'tool_result', { toolUseId: block.tool_use_id, summary, isError: !!block.is_error });
              stmts.insertChatMessage.run({
                chatId,
                role: 'tool',
                content: summary,
                eventType: 'tool_result',
                eventSubtype: block.is_error ? 'error' : 'success',
              });
            }
          }
        } else if (type === 'result') {
          const latestSessionId = getLiveSessionId(activeChats.get(chatId)) || liveSessionId || sessionId || sdkSessionId;
          emitter.emit('event', 'result', {
            subtype: msg.subtype,
            durationMs: msg.duration_ms,
            numTurns: msg.num_turns,
            totalCost: msg.total_cost_usd,
            stopReason: msg.stop_reason,
            sessionId: latestSessionId,
          });
          stmts.insertChatMessage.run({
            chatId,
            role: 'system',
            content: JSON.stringify({
              subtype: msg.subtype,
              durationMs: msg.duration_ms,
              numTurns: msg.num_turns,
              totalCost: msg.total_cost_usd,
              stopReason: msg.stop_reason,
            }),
            eventType: 'result',
            eventSubtype: msg.subtype,
          });
        } else if (type === 'stream_event') {
          emitter.emit('event', 'stream_event', msg.event || msg);
          stmts.insertChatMessage.run({
            chatId,
            role: 'system',
            content: JSON.stringify(msg.event || msg),
            eventType: 'stream_event',
            eventSubtype: msg.event?.type || msg.type || 'stream_event',
          });
        } else {
          emitter.emit('event', 'raw', msg);
          stmts.insertChatMessage.run({
            chatId,
            role: 'system',
            content: JSON.stringify(msg),
            eventType: 'raw',
            eventSubtype: msg.type || 'raw',
          });
        }
      }
      const latestSessionId = getLiveSessionId(activeChats.get(chatId)) || sessionId || sdkSessionId;
      emitter.emit('event', 'chat_complete', { chatId, sessionId: latestSessionId });
      stmts.updateChatSession.run({
        chatId,
        title: null,
        sessionId: latestSessionId,
        originSessionId: latestSessionId,
        permissionMode: normalizedPermissionMode,
        cwd: normalizedCwd,
        harness: null,
        status: 'completed',
        harness: 'claude',
      });
    } catch (err) {
      const latestSessionId = getLiveSessionId(activeChats.get(chatId)) || sessionId || sdkSessionId;
      const message = MISSING_CONVERSATION_RE.test(err.message || '')
        ? `选中的 Claude session 已不可恢复：${sessionId || 'unknown'}。请新建 Chat，或选择仍存在 session_id 的历史对话。`
        : err.message;
      emitter.emit('event', 'chat_error', { chatId, error: message });
      logger.error(`Chat error [${chatId}]: ${err.message}`, { context: 'Chat' });
      stmts.insertChatMessage.run({
        chatId,
        role: 'system',
        content: message,
        eventType: 'error',
        eventSubtype: 'chat_error',
      });
      stmts.updateChatSession.run({
        chatId,
        title: null,
        sessionId: latestSessionId,
        originSessionId: latestSessionId || sessionId,
        permissionMode: normalizedPermissionMode,
        cwd: normalizedCwd,
        harness: null,
        status: 'failed',
        harness: 'claude',
      });
    } finally {
      activeChats.delete(chatId);
    }
  })();

  // Store sessionId for later follow-ups
  if (sdkSessionId) {
    const activeEntry = activeChats.get(chatId);
    if (activeEntry) {
      activeEntry.sessionId = sdkSessionId;
      if (!activeEntry.originSessionId) activeEntry.originSessionId = sdkSessionId;
    }
  }

  return {
    chatId,
    emitter,
    sessionId: sessionId || sdkSessionId,
    currentSessionId: sdkSessionId || null,
    originSessionId: sessionId || sdkSessionId || null,
    permissionMode: normalizedPermissionMode,
    cwd: normalizedCwd,
    harness: 'claude',
  };
}

/**
 * OMP harness chat — spawns omp --mode=rpc and adapts its event stream
 * into the same SSE event names the Claude path emits.
 */
function startOmpChat({ chatId, prompt, stored, title, ownerUserId = null }) {
  if (!prompt || typeof prompt !== 'string') {
    throw new Error('prompt is required');
  }

  // Continue the chat's own OMP session when one exists (per-chatId session dir).
  const hasPriorSession = storedChatIsOmp(stored);
  const sessionId = ompClient.ompChatSessionId(chatId);
  const emitter = new EventEmitter();
  const permissionMode = 'bypassPermissions'; // OMP runs with --auto-approve
  const cwd = PROJECT_ROOT;

  const query = ompClient.startChatQuery({ chatId, prompt, resume: hasPriorSession });
  activeChats.set(chatId, {
    query,
    emitter,
    sessionId,
    originSessionId: sessionId,
    harness: 'omp',
  });

  if (stored) {
    stmts.updateChatSession.run({
      chatId,
      title: title || null,
      sessionId,
      originSessionId: sessionId,
      permissionMode,
      cwd,
      status: 'active',
      harness: 'omp',
    });
  } else {
    stmts.insertChatSession.run({
      chatId,
      title: title || prompt.slice(0, 60),
      sessionId,
      originSessionId: sessionId,
      status: 'active',
      model: 'omp',
      permissionMode,
      cwd,
      harness: 'omp',
      ownerUserId,
    });
  }
  stmts.insertChatMessage.run({
    chatId,
    role: 'user',
    content: prompt,
    eventType: 'user_message',
    eventSubtype: null,
  });

  emitter.emit('event', 'chat_init', {
    chatId,
    sessionId,
    model: 'omp',
    permissionMode,
    cwd,
    harness: 'omp',
    timestamp: new Date().toISOString(),
  });

  runEngineChatLoop({ chatId, query, emitter, harness: 'omp', stored, title, sessionId, model: 'omp', permissionMode, cwd });

  return {
    chatId,
    emitter,
    sessionId,
    currentSessionId: sessionId,
    originSessionId: sessionId,
    permissionMode,
    cwd,
    harness: 'omp',
  };
}

/**
 * Shared chat consumption loop — every harness emits Claude-SDK-shaped
 * messages, so one loop maps ANY engine's stream onto the same SSE event
 * names and chat_message persistence the Claude path established.
 */
function runEngineChatLoop({ chatId, query, emitter, harness, stored, title, sessionId, model, permissionMode = null, cwd = PROJECT_ROOT }) {
  (async () => {
    let failed = false;
    try {
      for await (const msg of query) {
        if (!msg || typeof msg !== 'object') continue;

        if (msg.type === 'assistant') {
          for (const block of msg.message?.content || []) {
            if (block.type === 'text') {
              emitter.emit('event', 'message', { role: 'assistant', content: block.text });
              stmts.insertChatMessage.run({
                chatId, role: 'assistant', content: block.text, eventType: 'message', eventSubtype: 'text',
              });
            } else if (block.type === 'tool_use') {
              emitter.emit('event', 'tool_use', { name: block.name, input: block.input, id: block.id });
              stmts.insertChatMessage.run({
                chatId, role: 'assistant', content: JSON.stringify({ name: block.name, input: block.input, id: block.id }),
                eventType: 'tool_use', eventSubtype: block.name,
              });
            } else if (block.type === 'thinking') {
              emitter.emit('event', 'thinking', { content: (block.thinking || '').slice(0, 500) });
              stmts.insertChatMessage.run({
                chatId, role: 'assistant', content: (block.thinking || '').slice(0, 500),
                eventType: 'thinking', eventSubtype: null,
              });
            }
          }
        } else if (msg.type === 'user') {
          for (const block of msg.message?.content || []) {
            if (block.type === 'tool_result') {
              const summary = typeof block.content === 'string' ? block.content.slice(0, 300) : '';
              emitter.emit('event', 'tool_result', {
                toolUseId: block.tool_use_id, summary, isError: !!block.is_error,
              });
              stmts.insertChatMessage.run({
                chatId, role: 'tool', content: summary,
                eventType: 'tool_result', eventSubtype: block.is_error ? 'error' : 'success',
              });
            }
          }
        } else if (msg.type === 'system') {
          emitter.emit('event', 'system', { subtype: msg.subtype || 'system', message: msg.data?.message || '' });
          stmts.insertChatMessage.run({
            chatId, role: 'system', content: JSON.stringify({ subtype: msg.subtype || 'system' }),
            eventType: 'system', eventSubtype: msg.subtype || 'system',
          });
        } else if (msg.type === 'result') {
          if (msg.subtype === 'error_during_execution') failed = true;
          emitter.emit('event', 'result', {
            subtype: msg.subtype,
            durationMs: msg.duration_ms,
            numTurns: msg.num_turns,
            totalCost: null,
            stopReason: msg.stop_reason,
            sessionId,
          });
          stmts.insertChatMessage.run({
            chatId, role: 'system',
            content: JSON.stringify({
              subtype: msg.subtype, durationMs: msg.duration_ms, numTurns: msg.num_turns, stopReason: msg.stop_reason,
            }),
            eventType: 'result', eventSubtype: msg.subtype,
          });
        }
      }
      emitter.emit('event', 'chat_complete', { chatId, sessionId });
      stmts.updateChatSession.run({
        chatId,
        title: null,
        sessionId,
        originSessionId: sessionId,
        permissionMode,
        cwd,
        status: failed ? 'failed' : 'completed',
        harness,
      });
    } catch (err) {
      emitter.emit('event', 'chat_error', { chatId, error: err.message });
      logger.error(`${harness} chat error [${chatId}]: ${err.message}`, { context: 'Chat' });
      stmts.insertChatMessage.run({
        chatId, role: 'system', content: err.message, eventType: 'error', eventSubtype: 'chat_error',
      });
      stmts.updateChatSession.run({
        chatId,
        title: null,
        sessionId,
        originSessionId: sessionId,
        permissionMode,
        cwd,
        status: 'failed',
        harness,
      });
    } finally {
      try { query.close(); } catch { /* ignore */ }
      activeChats.delete(chatId);
    }
  })();
}

/**
 * Stateless engines (ACP single-flight, codex threads, copilot…) have no
 * cross-turn memory — replay the recent transcript ahead of the new message
 * so a chat is still a REAL conversation, just with explicit context.
 */
function buildReplayPrompt(chatId, message, { maxTurns = 12 } = {}) {
  const rows = stmts.getChatMessagesByChatId.all(chatId) || [];
  const recent = rows
    .filter((r) => (r.event_type === 'message' || r.event_type === 'user_message') && r.content)
    .slice(-maxTurns);
  if (recent.length === 0) return message;
  const transcript = recent
    .map((r) => `${r.role === 'user' ? 'User' : 'Assistant'}: ${String(r.content).replace(/\s+\n/g, '\n')}`)
    .join('\n\n');
  return `You are continuing an existing conversation. Earlier turns are replayed below for context.\n\n--- Conversation so far ---\n${transcript}\n--- End of earlier conversation ---\n\nUser: ${message}`;
}

/**
 * Generic definition-table engine chat — mock / one-shot family / ACP family
 * / codex / opencode. Turn 1 rides the engine's raw startChatTurn; follow-ups
 * use native session resume when the engine supports it, transcript replay
 * when it does not. Engine-side failures propagate honestly (no fallback).
 */
async function startGenericEngineChat({ chatId, prompt, stored, title, harness, model = null, ownerUserId = null }) {
  if (!prompt || typeof prompt !== 'string') {
    throw new Error('prompt is required');
  }
  const client = await getEngineClient(harness);
  const emitter = new EventEmitter();
  const isFollowUp = Boolean(stored);
  const cwd = PROJECT_ROOT;

  let query = null;
  let sessionId = null;
  let replayed = false;

  if (isFollowUp && stored?.session_id && stored.harness === harness) {
    try {
      const resumed = client.startSessionChat({ runId: chatId, sessionId: stored.session_id, message: prompt });
      query = resumed.query;
      sessionId = resumed.query?.sessionId || resumed.sessionId || stored.session_id;
    } catch (e) {
      if (e?.status !== 400) throw e; // engine-side errors are real — surface them
      query = null;                   // no cross-process resume → replay below
    }
  }
  if (!query) {
    replayed = isFollowUp;
    const turnPrompt = replayed ? buildReplayPrompt(chatId, prompt) : prompt;
    const turn = client.startChatTurn({ runId: chatId, prompt: turnPrompt, model });
    query = turn.query;
    sessionId = (turn.getSessionId ? turn.getSessionId() : null) || turn.sessionId || `${harness}:chat:${chatId}`;
  }

  activeChats.set(chatId, { query, emitter, sessionId, originSessionId: sessionId, harness });
  if (stored) {
    stmts.updateChatSession.run({
      chatId, title: title || null, sessionId, originSessionId: sessionId,
      permissionMode: null, cwd, status: 'active', harness,
    });
  } else {
    stmts.insertChatSession.run({
      chatId, title: title || prompt.slice(0, 60), sessionId, originSessionId: sessionId,
      status: 'active', model: harness, permissionMode: null, cwd, harness,
      ownerUserId,
    });
  }
  stmts.insertChatMessage.run({
    chatId, role: 'user', content: prompt, eventType: 'user_message', eventSubtype: null,
  });

  emitter.emit('event', 'chat_init', {
    chatId, sessionId, model: harness, permissionMode: null, cwd, harness, timestamp: new Date().toISOString(),
  });

  runEngineChatLoop({ chatId, query, emitter, harness, stored, title, sessionId, model: harness, permissionMode: null, cwd });

  return { chatId, emitter, sessionId, currentSessionId: sessionId, originSessionId: sessionId, permissionMode: null, cwd, harness, replayed };
}

/**
 * Stop an active chat session. Refuses (false) a chat the viewer may not see.
 */
export function stopChat(chatId, viewer = INTERNAL) {
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (stored && !canViewChat(viewer, stored)) return false;
  const entry = activeChats.get(chatId);
  if (!entry) return false;
  try { entry.query.close(); } catch {}
  activeChats.delete(chatId);
  stmts.updateChatSession.run({
    chatId,
    title: null,
    sessionId: entry.sessionId || entry.query?.sessionId || null,
    originSessionId: entry.originSessionId || entry.sessionId || entry.query?.sessionId || null,
    permissionMode: null,
    cwd: null,
    harness: null,
    status: 'stopped',
    harness: entry.harness || 'claude',
  });
  return true;
}

/**
 * Get active chat session info. A chat the viewer may not see → null
 * (route answers the same as for an unknown chat).
 */
export function getChatInfo(chatId, viewer = INTERNAL) {
  const entry = activeChats.get(chatId);
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (!entry && !stored) return null;
  if (!canViewChat(viewer, stored)) return null;
  return {
    chatId,
    active: !!entry,
    sessionId: getEffectiveResumeSessionId(entry) || getEffectiveResumeSessionId(stored),
    currentSessionId: entry?.sessionId || entry?.query?.sessionId || stored?.session_id || null,
    originSessionId: getOriginSessionId(entry) || getOriginSessionId(stored),
    title: stored?.title || null,
    status: stored?.status || (entry ? 'active' : 'unknown'),
    permissionMode: stored?.permission_mode || 'default',
    cwd: stored?.cwd || PROJECT_ROOT,
    harness: stored?.harness || entry?.harness || 'claude',
  };
}

/**
 * List all chat sessions the viewer may see (own chats; every chat for an
 * admin; NULL-owner chats are admin-only).
 */
export function listActiveChats(viewer = INTERNAL) {
  return stmts.getAllChatSessions.all()
    .filter((row) => canViewChat(viewer, row))
    .map(row => ({
    chatId: row.chat_id,
    sessionId: getEffectiveResumeSessionId(row),
    currentSessionId: row.session_id,
    originSessionId: getOriginSessionId(row),
    title: row.title,
    status: activeChats.has(row.chat_id) ? 'active' : row.status,
    permissionMode: row.permission_mode || 'default',
    cwd: row.cwd || PROJECT_ROOT,
    harness: row.harness || 'claude',
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }));
}

/**
 * Send a follow-up message to an existing chat session (resume).
 * `params.viewer` (default INTERNAL) gates the act: a chat the viewer may not
 * see is a 404 — same answer as an unknown chat. `params.ownerUserId` stamps
 * ownership when this call creates the session (first message of a new chat).
 */
export async function sendChatMessage(chatId, followUpMessage, params = {}) {
  const viewer = params.viewer ?? INTERNAL;
  const ownerUserId = resolveOwnerId(params.ownerUserId);
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (stored && !canViewChat(viewer, stored)) throw chatNotFoundError();

  const requestedSessionId = normalizeClaudeSessionId(params.originSessionId)
    || normalizeClaudeSessionId(params.sessionId);
  const trustedStoredSessionId = getEffectiveResumeSessionId(stored);
  if (requestedSessionId && (!stored || requestedSessionId !== trustedStoredSessionId)) {
    throw externalResumeError();
  }

  // ── OMP harness: continue the chat's own OMP session ──
  const ompRequested = storedChatIsOmp(stored)
    || (!stored && normalizeChatHarness(params.harness) === 'omp');
  if (ompRequested) {
    const entry = activeChats.get(chatId);
    if (entry) {
      try { entry.query.close(); } catch { /* ignore */ }
      activeChats.delete(chatId);
    }
    return startOmpChat({
      chatId,
      prompt: followUpMessage,
      stored,
      title: stored?.title || followUpMessage.slice(0, 60),
      ownerUserId,
    });
  }

  // ── Generic definition-table engines: native resume when possible,
  //    transcript replay otherwise. An existing chat is sticky to the
  //    engine that created it. ──
  if (stored && stored.harness && !DEDICATED_CHAT_HARNESSES.has(stored.harness)) {
    const stale = activeChats.get(chatId);
    if (stale) {
      try { stale.query.close(); } catch { /* ignore */ }
      activeChats.delete(chatId);
    }
    return startGenericEngineChat({
      chatId,
      prompt: followUpMessage,
      stored,
      title: stored.title || followUpMessage.slice(0, 60),
      harness: stored.harness,
      model: stored.model || null,
      ownerUserId,
    });
  }

  const entry = activeChats.get(chatId);
  const sessionId = getEffectiveResumeSessionId(stored);

  if (entry) {
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }

  if (!sessionId) {
    const err = new Error('No active session to continue — use /start first');
    err.status = 409;
    err.code = 'CHAT_SESSION_NOT_RESUMABLE';
    throw err;
  }

  const inheritedPermissionMode = normalizePermissionMode(
    params.permissionMode,
    normalizePermissionMode(stored?.permission_mode, 'default'),
  );
  const inheritedCwd = normalizeChatCwd(params.cwd, stored?.cwd || PROJECT_ROOT);
  const storedCwd = normalizeChatCwd(stored?.cwd || PROJECT_ROOT, PROJECT_ROOT);
  if (stored && (getEffectiveResumeSessionId(stored) || isStartedChatSession(stored)) && inheritedCwd !== storedCwd) {
    const err = new Error('当前聊天已经绑定到既有 Claude session，不能在续聊时切换工作目录。请新建 Chat 后再选择新的工作目录。');
    err.status = 400;
    throw err;
  }

  const inheritedHarness = stored?.harness || 'claude';
  return startChat({
    ...params,
    chatId,
    prompt: followUpMessage,
    sessionId,
    permissionMode: inheritedPermissionMode,
    cwd: inheritedCwd,
    harness: params.harness === 'omp' || params.harness === 'claude' ? params.harness : inheritedHarness,
    title: stored?.title || followUpMessage.slice(0, 60),
  });
}

/**
 * Get emitter for SSE streaming. A chat the viewer may not see → null (the
 * route then falls through to the replay path, which is gated too).
 */
export function getChatEmitter(chatId, viewer = INTERNAL) {
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (stored && !canViewChat(viewer, stored)) return null;
  return activeChats.get(chatId)?.emitter || null;
}

export function subscribeChatEvents(chatId, callback, viewer = INTERNAL) {
  // WS subscription seam: the transport passes the connection's authenticated
  // user here (ws.authUser) — without it the legacy INTERNAL default keeps the
  // pre-tenancy behaviour rather than silently disabling every subscription.
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (stored && !canViewChat(viewer, stored)) return () => {};
  const emitter = getChatEmitter(chatId, viewer);
  if (!emitter || typeof callback !== 'function') {
    return () => {};
  }

  const handler = (eventType, data) => {
    callback(eventType, data);
  };

  emitter.on('event', handler);
  return () => {
    emitter.off('event', handler);
  };
}

/** Single chat session view; null when missing OR not visible to `viewer`. */
export function getChatSession(chatId, viewer = INTERNAL) {
  const row = stmts.getChatSessionByChatId.get(chatId);
  if (!row) return null;
  if (!canViewChat(viewer, row)) return null;
  return {
    chatId: row.chat_id,
    sessionId: getEffectiveResumeSessionId(row),
    currentSessionId: row.session_id,
    originSessionId: getOriginSessionId(row),
    title: row.title,
    status: activeChats.has(row.chat_id) ? 'active' : row.status,
    permissionMode: row.permission_mode || 'default',
    cwd: row.cwd || PROJECT_ROOT,
    harness: row.harness || 'claude',
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function getChatHistory(chatId, viewer = INTERNAL) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  if (!canViewChat(viewer, session)) return null;
  const messages = stmts.getChatMessagesByChatId.all(chatId);
  return {
    session: {
      chatId: session.chat_id,
      sessionId: getEffectiveResumeSessionId(session),
      currentSessionId: session.session_id,
      originSessionId: getOriginSessionId(session),
      title: session.title,
      status: activeChats.has(session.chat_id) ? 'active' : session.status,
      permissionMode: session.permission_mode || 'default',
      cwd: session.cwd || PROJECT_ROOT,
      harness: session.harness || 'claude',
      createdAt: session.created_at,
      updatedAt: session.updated_at,
    },
    messages,
  };
}

export function getChatReplay(chatId, viewer = INTERNAL) {
  const history = getChatHistory(chatId, viewer);
  if (!history) return null;

  const { session, messages } = history;
  const events = [];

  events.push({
    eventType: 'chat_init',
    data: {
      chatId: session.chatId,
      sessionId: session.sessionId,
      title: session.title,
      timestamp: session.createdAt,
      permissionMode: session.permissionMode || 'default',
      cwd: session.cwd || PROJECT_ROOT,
    },
  });

  for (const msg of messages) {
    const mapped = mapStoredMessageToSSE(msg);
    if (mapped) events.push(mapped);
  }

  if (session.status === 'failed') {
    events.push({
      eventType: 'chat_error',
      data: {
        chatId: session.chatId,
        error: 'Stored chat ended with failure',
        sessionId: session.sessionId,
      },
    });
  } else {
    events.push({
      eventType: 'chat_complete',
      data: {
        chatId: session.chatId,
        sessionId: session.sessionId,
      },
    });
  }

  return { session, events };
}

function mapStoredMessageToSSE(row) {
  const eventType = row.event_type;
  if (eventType === 'user_message') return null;

  if (eventType === 'message') {
    return {
      eventType: 'message',
      data: { role: 'assistant', content: row.content || '' },
    };
  }

  if (eventType === 'thinking') {
    return {
      eventType: 'thinking',
      data: { content: row.content || '' },
    };
  }

  if (eventType === 'tool_use') {
    try {
      return {
        eventType: 'tool_use',
        data: JSON.parse(row.content || '{}'),
      };
    } catch {
      return {
        eventType: 'tool_use',
        data: { name: row.event_subtype || 'Tool', input: { raw: row.content || '' } },
      };
    }
  }

  if (eventType === 'tool_result') {
    return {
      eventType: 'tool_result',
      data: {
        toolUseId: '',
        summary: row.content || '',
        isError: row.event_subtype === 'error',
      },
    };
  }

  if (eventType === 'system') {
    try {
      const parsed = JSON.parse(row.content || '{}');
      return {
        eventType: 'system',
        data: { subtype: parsed.subtype || row.event_subtype || 'system', ...parsed },
      };
    } catch {
      return {
        eventType: 'system',
        data: { subtype: row.event_subtype || 'system', content: row.content || '' },
      };
    }
  }

  if (eventType === 'stream_event') {
    try {
      return {
        eventType: 'stream_event',
        data: JSON.parse(row.content || '{}'),
      };
    } catch {
      return {
        eventType: 'stream_event',
        data: { type: row.event_subtype || 'stream_event', raw: row.content || '' },
      };
    }
  }

  if (eventType === 'result') {
    try {
      return {
        eventType: 'result',
        data: JSON.parse(row.content || '{}'),
      };
    } catch {
      return {
        eventType: 'result',
        data: { subtype: row.event_subtype || 'completed' },
      };
    }
  }

  if (eventType === 'error') {
    return {
      eventType: 'chat_error',
      data: { error: row.content || 'Stored chat error' },
    };
  }

  if (eventType === 'raw') {
    try {
      return {
        eventType: 'raw',
        data: JSON.parse(row.content || '{}'),
      };
    } catch {
      return {
        eventType: 'raw',
        data: { raw: row.content || '' },
      };
    }
  }

  return null;
}

export function renameChatSession(chatId, title, viewer = INTERNAL) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  if (!canViewChat(viewer, session)) return null;
  stmts.renameChatSession.run({ chatId, title });
  return getChatSession(chatId, viewer);
}

export function updateChatSessionConfig(chatId, { title = null, permissionMode, cwd } = {}, viewer = INTERNAL) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  if (!canViewChat(viewer, session)) return null;
  const nextPermissionMode = permissionMode == null
    ? null
    : normalizePermissionMode(permissionMode, normalizePermissionMode(session.permission_mode, 'default'));
  const nextCwd = cwd == null ? null : normalizeChatCwd(cwd, session.cwd || PROJECT_ROOT);
  const currentCwd = normalizeChatCwd(session.cwd || PROJECT_ROOT, PROJECT_ROOT);
  if (nextCwd && nextCwd !== currentCwd && (getEffectiveResumeSessionId(session) || isStartedChatSession(session))) {
    const err = new Error('当前聊天已经绑定到 Claude session，工作目录不能再修改。请新建 Chat 后选择新的工作目录。');
    err.status = 400;
    throw err;
  }
  stmts.patchChatSessionConfig.run({
    chatId,
    title,
    permissionMode: nextPermissionMode,
    cwd: nextCwd,
  });
  return getChatSession(chatId, viewer);
}

/** Delete a chat session. A chat the viewer may not see → false (route 404). */
export async function deleteChatSession(chatId, viewer = INTERNAL) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return false;
  if (!canViewChat(viewer, session)) return false;
  const entry = activeChats.get(chatId);
  if (entry) {
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }
  const removedClaudeArtifacts = deleteClaudeSessionArtifacts([
    session.origin_session_id,
    session.session_id,
    entry?.originSessionId,
    entry?.sessionId,
    entry?.query?.sessionId,
  ]);
  const removedOmpSession = storedChatIsOmp(session)
    ? ompClient.deleteChatArtifacts(chatId)
    : false;
  stmts.deleteChatSession.run(chatId);
  logger.info(`Deleted chat session ${chatId} (claude artifacts: ${removedClaudeArtifacts.length}, omp session removed: ${removedOmpSession})`, {
    context: 'Chat',
    chatId,
    removedClaudeArtifacts,
  });
  return {
    deleted: true,
    removedClaudeArtifacts,
  };
}
