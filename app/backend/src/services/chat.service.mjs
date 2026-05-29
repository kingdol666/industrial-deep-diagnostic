// Chat Service — direct Claude Agent SDK chat with streaming SSE
// Supports custom config: model, permissionMode, maxTurns, tools, session resume

import { EventEmitter } from 'events';
import logger from '../utils/logger.mjs';

let queryFn = null;
try {
  const sdk = await import('@anthropic-ai/claude-agent-sdk');
  queryFn = sdk.query;
} catch (e) {
  logger.error(`Chat SDK init failed: ${e.message}`, { context: 'Chat' });
}

// Active chat sessions: chatId -> { query, emitter }
const activeChats = new Map();

/**
 * Start a chat session with full streaming support.
 * Returns { chatId, emitter } — the emitter fires SSE-compatible events.
 */
export async function startChat(params = {}) {
  if (!queryFn) throw new Error('Claude Agent SDK not available');

  const {
    prompt,
    model,
    permissionMode = 'bypassPermissions',
    maxTurns,
    cwd,
    sessionId,      // resume existing session
    extraArgs,      // additional CLI args
    systemPrompt,   // system prompt override
    tools,          // allowed tools list
    env,            // environment vars
    effort,         // 'low'|'medium'|'high'|'xhigh'|'max'
    thinking,       // { type: 'adaptive' } | { type: 'enabled', budgetTokens: N }
    forkSession,    // fork on resume
  } = params;

  if (!prompt || typeof prompt !== 'string') {
    throw new Error('prompt is required');
  }

  const chatId = `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const emitter = new EventEmitter();

  // Build SDK options
  const options = {
    permissionMode,
    allowDangerouslySkipPermissions: permissionMode === 'bypassPermissions',
    includePartialMessages: true,
    forwardSubagentText: true,
    model: model || undefined,
    cwd: cwd || undefined,
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
  activeChats.set(chatId, { query, emitter });

  // Emit init event with session info
  const sdkSessionId = query.sessionId || null;
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
              // Re-emit chat_init now that we have the sessionId
              emitter.emit('event', 'chat_init', {
                chatId,
                sessionId: msg.session_id,
                model: msg.model || 'unknown',
                permissionMode,
                timestamp: new Date().toISOString(),
              });
            }
          }
        } else if (type === 'assistant') {
          const content = msg.message?.content || [];
          for (const block of content) {
            if (block.type === 'text') {
              emitter.emit('event', 'message', { role: 'assistant', content: block.text });
            } else if (block.type === 'tool_use') {
              emitter.emit('event', 'tool_use', { name: block.name, input: block.input, id: block.id });
            } else if (block.type === 'thinking') {
              emitter.emit('event', 'thinking', { content: block.thinking?.slice(0, 500) || '' });
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
        } else if (type === 'stream_event') {
          emitter.emit('event', 'stream_event', msg.event || msg);
        } else {
          emitter.emit('event', 'raw', msg);
        }
      }
      emitter.emit('event', 'chat_complete', { chatId, sessionId: sdkSessionId });
    } catch (err) {
      emitter.emit('event', 'chat_error', { chatId, error: err.message });
      logger.error(`Chat error [${chatId}]: ${err.message}`, { context: 'Chat' });
    } finally {
      activeChats.delete(chatId);
    }
  })();

  // Store sessionId for later follow-ups
  if (sdkSessionId) {
    activeChats.get(chatId).sessionId = sdkSessionId;
  }

  return { chatId, emitter, sessionId: sdkSessionId };
}

/**
 * Stop an active chat session.
 */
export function stopChat(chatId) {
  const entry = activeChats.get(chatId);
  if (!entry) return false;
  try { entry.query.close(); } catch {}
  activeChats.delete(chatId);
  return true;
}

/**
 * Get active chat session info.
 */
export function getChatInfo(chatId) {
  const entry = activeChats.get(chatId);
  if (!entry) return null;
  return {
    chatId,
    active: true,
    sessionId: entry.sessionId || entry.query?.sessionId || null,
  };
}

/**
 * List all active chat sessions.
 */
export function listActiveChats() {
  return [...activeChats.keys()];
}

/**
 * Send a follow-up message to an existing chat session (resume).
 */
export async function sendChatMessage(chatId, followUpMessage, params = {}) {
  const entry = activeChats.get(chatId);
  let sessionId = params.sessionId;

  if (entry) {
    // Extract from stored entry first, then from query object
    if (!sessionId && entry.sessionId) sessionId = entry.sessionId;
    if (!sessionId && entry.query?.sessionId) sessionId = entry.query.sessionId;
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }

  if (!sessionId) throw new Error('No active session to continue — provide sessionId parameter or use /start first');

  return startChat({
    prompt: followUpMessage,
    sessionId,
    ...params,
  });
}

/**
 * Get emitter for SSE streaming.
 */
export function getChatEmitter(chatId) {
  return activeChats.get(chatId)?.emitter || null;
}
