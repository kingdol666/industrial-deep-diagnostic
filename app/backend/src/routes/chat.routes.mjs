// Chat Routes — direct Claude Agent SDK chat with streaming SSE
import { Router } from 'express';
import { startChat, stopChat, getChatInfo, listActiveChats, sendChatMessage, getChatEmitter } from '../services/chat.service.mjs';

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

  if (!emitter) {
    res.status(404).json({ success: false, error: 'Chat not found or already ended' });
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

// GET /api/chat/list — list active chat IDs
router.get('/list', (_req, res) => {
  res.json({ success: true, data: listActiveChats() });
});

export default router;
