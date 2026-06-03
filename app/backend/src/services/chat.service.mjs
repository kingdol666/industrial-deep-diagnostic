// Chat Service — direct Claude Agent SDK chat with streaming SSE
// Supports custom config: model, permissionMode, maxTurns, tools, session resume

import { EventEmitter } from 'events';
import logger from '../utils/logger.mjs';
import { stmts } from '../db/database.mjs';

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
    title,
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
  const sdkSessionId = query.sessionId || null;

  stmts.insertChatSession.run({
    chatId,
    title: title || prompt.slice(0, 60),
    sessionId: sdkSessionId,
    status: 'active',
    model: model || 'default',
    permissionMode,
  });
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
      stmts.updateChatSession.run({ chatId, title: null, sessionId: sdkSessionId, status: 'completed' });
    } catch (err) {
      emitter.emit('event', 'chat_error', { chatId, error: err.message });
      logger.error(`Chat error [${chatId}]: ${err.message}`, { context: 'Chat' });
      stmts.insertChatMessage.run({
        chatId,
        role: 'system',
        content: err.message,
        eventType: 'error',
        eventSubtype: 'chat_error',
      });
      stmts.updateChatSession.run({ chatId, title: null, sessionId: sdkSessionId, status: 'failed' });
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
  stmts.updateChatSession.run({ chatId, title: null, sessionId: entry.sessionId || entry.query?.sessionId || null, status: 'stopped' });
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
    sessionId: entry?.sessionId || entry?.query?.sessionId || stored?.session_id || null,
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
    sessionId: row.session_id,
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
  let sessionId = params.sessionId;
  const stored = stmts.getChatSessionByChatId.get(chatId);

  if (entry) {
    // Extract from stored entry first, then from query object
    if (!sessionId && entry.sessionId) sessionId = entry.sessionId;
    if (!sessionId && entry.query?.sessionId) sessionId = entry.query.sessionId;
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }

  if (!sessionId && stored?.session_id) sessionId = stored.session_id;

  if (!sessionId) throw new Error('No active session to continue — provide sessionId parameter or use /start first');

  return startChat({
    prompt: followUpMessage,
    sessionId,
    title: stored?.title || followUpMessage.slice(0, 60),
    ...params,
  });
}

/**
 * Get emitter for SSE streaming.
 */
export function getChatEmitter(chatId) {
  return activeChats.get(chatId)?.emitter || null;
}

export function getChatSession(chatId) {
  const row = stmts.getChatSessionByChatId.get(chatId);
  if (!row) return null;
  return {
    chatId: row.chat_id,
    sessionId: row.session_id,
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
      sessionId: session.session_id,
      title: session.title,
      status: activeChats.has(session.chat_id) ? 'active' : session.status,
      createdAt: session.created_at,
      updatedAt: session.updated_at,
    },
    messages,
  };
}

export function renameChatSession(chatId, title) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return null;
  stmts.renameChatSession.run({ chatId, title });
  return getChatSession(chatId);
}

export function deleteChatSession(chatId) {
  const session = stmts.getChatSessionByChatId.get(chatId);
  if (!session) return false;
  const entry = activeChats.get(chatId);
  if (entry) {
    try { entry.query.close(); } catch {}
    activeChats.delete(chatId);
  }
  stmts.deleteChatSession.run(chatId);
  return true;
}
