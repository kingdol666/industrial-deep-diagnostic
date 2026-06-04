// Chat Routes — direct Claude Agent SDK chat with streaming SSE
import { Router } from 'express';
import { startChat, stopChat, getChatInfo, listActiveChats, sendChatMessage, getChatEmitter, getChatHistory, getChatSession, renameChatSession, deleteChatSession, getChatReplay } from '../services/chat.service.mjs';

const router = Router();

// POST /api/chat/start — launch new chat, returns chatId + stream URL
router.post('/start', async (req, res) => {
  try {
    const result = await startChat(req.body);
    res.json({
      success: true,
      data: {
        chatId: result.chatId,
        sessionId: result.sessionId,
        streamUrl: `/api/chat/stream/${result.chatId}`,
      },
    });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// GET /api/chat/stream/:chatId — SSE stream of chat events
router.get('/stream/:chatId', (req, res) => {
  const { chatId } = req.params;
  const emitter = getChatEmitter(chatId);

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  if (!emitter) {
    const replay = getChatReplay(chatId);
    if (!replay) {
      res.status(404).json({ success: false, error: 'Chat not found or already ended' });
      return;
    }

    for (const evt of replay.events) {
      res.write(`event: ${evt.eventType}\ndata: ${JSON.stringify(evt.data)}\n\n`);
    }
    res.end();
    return;
  }

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

// POST /api/chat/stop/:chatId — stop a running chat
router.post('/stop/:chatId', (req, res) => {
  const stopped = stopChat(req.params.chatId);
  res.json({ success: true, data: { chatId: req.params.chatId, stopped } });
});

// POST /api/chat/send/:chatId — send follow-up to existing session
router.post('/send/:chatId', async (req, res) => {
  try {
    const result = await sendChatMessage(req.params.chatId, req.body.message, req.body);
    res.json({
      success: true,
      data: {
        chatId: result.chatId,
        sessionId: result.sessionId,
        streamUrl: `/api/chat/stream/${result.chatId}`,
      },
    });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// GET /api/chat/info/:chatId — chat session info
router.get('/info/:chatId', (req, res) => {
  const info = getChatInfo(req.params.chatId);
  res.json({ success: true, data: info || { active: false } });
});

// GET /api/chat/history/:chatId — persisted chat session + messages
router.get('/history/:chatId', (req, res) => {
  const history = getChatHistory(req.params.chatId);
  if (!history) {
    return res.status(404).json({ success: false, error: 'Chat history not found' });
  }
  res.json({ success: true, data: history });
});

// GET /api/chat/session/:chatId — persisted chat session only
router.get('/session/:chatId', (req, res) => {
  const session = getChatSession(req.params.chatId);
  if (!session) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({ success: true, data: session });
});

// PATCH /api/chat/session/:chatId — rename chat session
router.patch('/session/:chatId', (req, res) => {
  const { title } = req.body || {};
  if (!title || typeof title !== 'string' || !title.trim()) {
    return res.status(400).json({ success: false, error: 'title is required' });
  }
  const session = renameChatSession(req.params.chatId, title.trim());
  if (!session) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({ success: true, data: session });
});

// DELETE /api/chat/session/:chatId — delete chat session + history
router.delete('/session/:chatId', (req, res) => {
  const deleted = deleteChatSession(req.params.chatId);
  if (!deleted) {
    return res.status(404).json({ success: false, error: 'Chat session not found' });
  }
  res.json({ success: true, data: { chatId: req.params.chatId, deleted: true } });
});

// GET /api/chat/list — list persisted chat sessions
router.get('/list', (_req, res) => {
  res.json({ success: true, data: listActiveChats() });
});

export default router;
