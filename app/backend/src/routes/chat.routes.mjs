// Chat Routes — direct Claude Agent SDK chat with streaming SSE
//
// Tenancy (P0-6): every chat-scoped endpoint passes `req.user` as the viewer.
// A session the caller may not see answers exactly like a missing one (404 /
// null payload) — see chat.service.mjs for the policy.
import { Router } from 'express';
import { startChat, stopChat, getChatInfo, listActiveChats, sendChatMessage, getChatEmitter, getChatHistory, getChatSession, renameChatSession, deleteChatSession, getChatReplay, updateChatSessionConfig } from '../services/chat.service.mjs';
import { listChatDirectories, pickChatDirectory } from '../services/files.service.mjs';
import { resolveOwnerId } from '../services/tenancy.mjs';
import logger from '../utils/logger.mjs';

const router = Router();

// 4xx 保留人话 message+code（引擎/选项校验等）；5xx 只回稳定 code + 通用消息，
// 真实错误进服务端日志（B4）。
function sendError(res, err, fallbackCode = 'CHAT_ERROR') {
  const status = err?.status || 500;
  if (status >= 500) {
    logger.error(`[chat] ${err?.stack || err?.message || err}`, { context: 'Chat' });
    return res.status(status).json({ success: false, code: err?.code || fallbackCode, error: '聊天服务内部错误，请查看后端日志后重试' });
  }
  return res.status(status).json({ success: false, code: err?.code || fallbackCode, error: err?.message || '请求无效' });
}

// POST /api/chat/start — launch new chat, returns chatId + stream URL
router.post('/start', async (req, res) => {
  try {
    const result = await startChat({
      ...req.body,
      viewer: req.user,
      ownerUserId: resolveOwnerId(req.user),
    });
    res.json({
      success: true,
      data: {
        chatId: result.chatId,
        sessionId: result.sessionId,
        originSessionId: result.originSessionId || result.sessionId || null,
        currentSessionId: result.currentSessionId || null,
        permissionMode: result.permissionMode || 'default',
        harness: result.harness || 'claude',
        cwd: result.cwd || null,
        streamUrl: `/api/chat/stream/${result.chatId}`,
      },
    });
  } catch (err) {
    sendError(res, err);
  }
});

// GET /api/chat/stream/:chatId — SSE stream of chat events
router.get('/stream/:chatId', (req, res) => {
  const { chatId } = req.params;
  const emitter = getChatEmitter(chatId, req.user);

  // Resolve the stream source BEFORE any header is written: a gone emitter with
  // no replay (unknown, finished-long-ago or foreign chat) must answer a real
  // 404 — the old order wrote SSE 200 headers first and then threw on
  // res.status(), tearing the socket down instead.
  if (!emitter) {
    const replay = getChatReplay(chatId, req.user);
    if (!replay) {
      return res.status(404).json({ success: false, error: 'Chat not found or already ended' });
    }
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    });
    for (const evt of replay.events) {
      res.write(`event: ${evt.eventType}\ndata: ${JSON.stringify(evt.data)}\n\n`);
    }
    res.end();
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const handler = (eventType, data) => {
    if (res.destroyed) { emitter.off('event', handler); return; }
    res.write(`event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`);
    if (eventType === 'chat_complete' || eventType === 'chat_error') {
      emitter.off('event', handler);
      if (!res.destroyed) res.end();
    }
  };

  emitter.on('event', handler);

  req.on('close', () => {
    emitter.off('event', handler);
    if (!res.destroyed) res.end();
  });
});

// POST /api/chat/stop/:chatId — stop a running chat (owner/admin only)
router.post('/stop/:chatId', (req, res) => {
  const session = getChatSession(req.params.chatId, req.user);
  if (!session) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  const stopped = stopChat(req.params.chatId, req.user);
  res.json({ success: true, data: { chatId: req.params.chatId, stopped } });
});

// POST /api/chat/send/:chatId — send follow-up to existing session
router.post('/send/:chatId', async (req, res) => {
  try {
    const result = await sendChatMessage(req.params.chatId, req.body.message, {
      ...req.body,
      viewer: req.user,
      ownerUserId: resolveOwnerId(req.user),
    });
    res.json({
      success: true,
      data: {
        chatId: result.chatId,
        sessionId: result.sessionId,
        originSessionId: result.originSessionId || result.sessionId || null,
        currentSessionId: result.currentSessionId || null,
        permissionMode: result.permissionMode || 'default',
        cwd: result.cwd || null,
        streamUrl: `/api/chat/stream/${result.chatId}`,
      },
    });
  } catch (err) {
    sendError(res, err);
  }
});

// GET /api/chat/info/:chatId — chat session info
router.get('/info/:chatId', (req, res) => {
  const info = getChatInfo(req.params.chatId, req.user);
  res.json({ success: true, data: info || { active: false } });
});

// GET /api/chat/history/:chatId — persisted chat session + messages
router.get('/history/:chatId', (req, res) => {
  const history = getChatHistory(req.params.chatId, req.user);
  if (!history) {
    return res.status(404).json({ success: false, error: 'Chat history not found' });
  }
  res.json({ success: true, data: history });
});

// GET /api/chat/session/:chatId — persisted chat session only
router.get('/session/:chatId', (req, res) => {
  const session = getChatSession(req.params.chatId, req.user);
  if (!session) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({ success: true, data: session });
});

// PATCH /api/chat/session/:chatId/config — update per-chat cwd / permissions / title
router.patch('/session/:chatId/config', (req, res) => {
  try {
    const updated = updateChatSessionConfig(req.params.chatId, req.body || {}, req.user);
    if (!updated) {
      return res.status(404).json({ success: false, error: 'Chat session not found' });
    }
    res.json({ success: true, data: updated });
  } catch (err) {
    sendError(res, err);
  }
});

// PATCH /api/chat/session/:chatId — rename chat session
router.patch('/session/:chatId', (req, res) => {
  const { title } = req.body || {};
  if (!title || typeof title !== 'string' || !title.trim()) {
    return res.status(400).json({ success: false, error: 'title is required' });
  }
  const session = renameChatSession(req.params.chatId, title.trim(), req.user);
  if (!session) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({ success: true, data: session });
});

// DELETE /api/chat/session/:chatId — delete chat session + history
router.delete('/session/:chatId', async (req, res) => {
  const deleted = await deleteChatSession(req.params.chatId, req.user);
  if (!deleted) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({
    success: true,
    data: {
      chatId: req.params.chatId,
      deleted: true,
      removedClaudeArtifacts: deleted.removedClaudeArtifacts || [],
    },
  });
});

// GET /api/chat/directories?path=... — browse server-side directories for chat cwd selection
router.get('/directories', async (req, res) => {
  try {
    const data = await listChatDirectories(req.query.path || undefined);
    res.json({ success: true, data });
  } catch (err) {
    sendError(res, err);
  }
});

// POST /api/chat/directories/pick — open native folder picker for chat cwd selection
router.post('/directories/pick', async (req, res) => {
  try {
    const data = await pickChatDirectory(req.body?.path || undefined);
    res.json({ success: true, data });
  } catch (err) {
    sendError(res, err);
  }
});

// GET /api/chat/list — list persisted chat sessions (own chats; all for an admin)
router.get('/list', (req, res) => {
  res.json({ success: true, data: listActiveChats(req.user) });
});

export default router;
