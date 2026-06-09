// Chat Service — direct Claude Agent SDK chat with streaming SSE
// Supports custom config: model, permissionMode, maxTurns, tools, session resume

import { EventEmitter } from 'events';
import { existsSync, readdirSync, rmSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';
import logger from '../utils/logger.mjs';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';

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
 * Returns { chatId, emitter } — the emitter fires SSE-compatible events.
 */
export async function startChat(params = {}) {
  if (!queryFn) throw new Error('Claude Agent SDK not available');

  const {
    chatId: requestedChatId,
    prompt,
    model,
    permissionMode = 'bypassPermissions',
    maxTurns,
    cwd,
    sessionId: rawSessionId, // resume existing Claude session UUID
    extraArgs,      // additional CLI args
    systemPrompt,   // system prompt override
    tools,          // allowed tools list
    env,            // environment vars
    effort,         // 'low'|'medium'|'high'|'xhigh'|'max'
    thinking,       // { type: 'adaptive' } | { type: 'enabled', budgetTokens: N }
    forkSession,    // fork on resume
    title,
  } = params;

  if (!prompt || typeof prompt !== 'string') {
    throw new Error('prompt is required');
  }

  const chatId = requestedChatId || `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const sessionId = normalizeClaudeSessionId(rawSessionId);
  const emitter = new EventEmitter();

  // Build SDK options
  const options = {
    permissionMode,
    allowDangerouslySkipPermissions: permissionMode === 'bypassPermissions',
    includePartialMessages: true,
    forwardSubagentText: true,
    model: model || undefined,
    cwd: cwd || PROJECT_ROOT,
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

  const existingSession = stmts.getChatSessionByChatId.get(chatId);
  if (existingSession) {
    stmts.updateChatSession.run({
      chatId,
      title: title || null,
      sessionId: sdkSessionId,
      originSessionId: getOriginSessionId(existingSession) || sdkSessionId,
      status: 'active',
    });
  } else {
    stmts.insertChatSession.run({
      chatId,
      title: title || prompt.slice(0, 60),
      sessionId: sdkSessionId,
      originSessionId: sdkSessionId,
      status: 'active',
      model: model || 'default',
      permissionMode,
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
    permissionMode,
    timestamp: new Date().toISOString(),
  });

  // Iterate SDK messages and emit as SSE events
  (async () => {
    try {
      for await (const msg of query) {
        if (!msg || typeof msg !== 'object') continue;

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
                sessionId: msg.session_id,
                model: msg.model || 'unknown',
                permissionMode,
                timestamp: new Date().toISOString(),
              });
              stmts.updateChatSession.run({
                chatId,
                title: null,
                sessionId: msg.session_id,
                originSessionId: msg.session_id,
                status: 'active',
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
          emitter.emit('event', 'result', {
            subtype: msg.subtype,
            durationMs: msg.duration_ms,
            numTurns: msg.num_turns,
            totalCost: msg.total_cost_usd,
            stopReason: msg.stop_reason,
            sessionId: sdkSessionId,
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
      emitter.emit('event', 'chat_complete', { chatId, sessionId: sdkSessionId });
      stmts.updateChatSession.run({
        chatId,
        title: null,
        sessionId: sdkSessionId,
        originSessionId: sdkSessionId,
        status: 'completed',
      });
    } catch (err) {
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
        sessionId: sdkSessionId,
        originSessionId: sdkSessionId || sessionId,
        status: 'failed',
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
  };
}

/**
 * Stop an active chat session.
 */
export function stopChat(chatId) {
  const entry = activeChats.get(chatId);
  if (!entry) return false;
  try { entry.query.close(); } catch {}
  activeChats.delete(chatId);
  stmts.updateChatSession.run({
    chatId,
    title: null,
    sessionId: entry.sessionId || entry.query?.sessionId || null,
    originSessionId: entry.originSessionId || entry.sessionId || entry.query?.sessionId || null,
    status: 'stopped',
  });
  return true;
}

/**
 * Get active chat session info.
 */
export function getChatInfo(chatId) {
  const entry = activeChats.get(chatId);
  const stored = stmts.getChatSessionByChatId.get(chatId);
  if (!entry && !stored) return null;
  return {
    chatId,
    active: !!entry,
    sessionId: getEffectiveResumeSessionId(entry) || getEffectiveResumeSessionId(stored),
    currentSessionId: entry?.sessionId || entry?.query?.sessionId || stored?.session_id || null,
    originSessionId: getOriginSessionId(entry) || getOriginSessionId(stored),
    title: stored?.title || null,
    status: stored?.status || (entry ? 'active' : 'unknown'),
  };
}

/**
 * List all active chat sessions.
 */
export function listActiveChats() {
  return stmts.getAllChatSessions.all().map(row => ({
    chatId: row.chat_id,
    sessionId: getEffectiveResumeSessionId(row),
    currentSessionId: row.session_id,
    originSessionId: getOriginSessionId(row),
    title: row.title,
    status: activeChats.has(row.chat_id) ? 'active' : row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }));
}

/**
 * Send a follow-up message to an existing chat session (resume).
 */
export async function sendChatMessage(chatId, followUpMessage, params = {}) {
  const entry = activeChats.get(chatId);
  let sessionId = normalizeClaudeSessionId(params.originSessionId)
    || normalizeClaudeSessionId(params.sessionId);
  const stored = stmts.getChatSessionByChatId.get(chatId);

  if (entry) {
    // Extract from stored entry first, then from query object
    if (!sessionId && getOriginSessionId(entry)) sessionId = getOriginSessionId(entry);
    if (!sessionId && entry.sessionId) sessionId = normalizeClaudeSessionId(entry.sessionId);
    if (!sessionId && entry.query?.sessionId) sessionId = normalizeClaudeSessionId(entry.query.sessionId);
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }

  if (!sessionId && getOriginSessionId(stored)) sessionId = getOriginSessionId(stored);
  if (!sessionId && stored?.session_id) sessionId = normalizeClaudeSessionId(stored.session_id);

  if (!sessionId) throw new Error('No active session to continue — provide sessionId parameter or use /start first');

  return startChat({
    ...params,
    chatId,
    prompt: followUpMessage,
    sessionId,
    title: stored?.title || followUpMessage.slice(0, 60),
  });
}

/**
 * Get emitter for SSE streaming.
 */
export function getChatEmitter(chatId) {
  return activeChats.get(chatId)?.emitter || null;
}

export function subscribeChatEvents(chatId, callback) {
  const emitter = getChatEmitter(chatId);
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

export function getChatSession(chatId) {
  const row = stmts.getChatSessionByChatId.get(chatId);
  if (!row) return null;
  return {
    chatId: row.chat_id,
    sessionId: getEffectiveResumeSessionId(row),
    currentSessionId: row.session_id,
    originSessionId: getOriginSessionId(row),
    title: row.title,
    status: activeChats.has(row.chat_id) ? 'active' : row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function getChatHistory(chatId) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  const messages = stmts.getChatMessagesByChatId.all(chatId);
  return {
    session: {
      chatId: session.chat_id,
      sessionId: getEffectiveResumeSessionId(session),
      currentSessionId: session.session_id,
      originSessionId: getOriginSessionId(session),
      title: session.title,
      status: activeChats.has(session.chat_id) ? 'active' : session.status,
      createdAt: session.created_at,
      updatedAt: session.updated_at,
    },
    messages,
  };
}

export function getChatReplay(chatId) {
  const history = getChatHistory(chatId);
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

export function renameChatSession(chatId, title) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  stmts.renameChatSession.run({ chatId, title });
  return getChatSession(chatId);
}

export async function deleteChatSession(chatId) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return false;
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
  stmts.deleteChatSession.run(chatId);
  logger.info(`Deleted chat session ${chatId} and ${removedClaudeArtifacts.length} Claude artifact(s)`, {
    context: 'Chat',
    chatId,
    removedClaudeArtifacts,
  });
  return {
    deleted: true,
    removedClaudeArtifacts,
  };
}
