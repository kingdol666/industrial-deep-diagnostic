import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const workDir = mkdtempSync(join(tmpdir(), 'idd-chat-resume-'));
process.env.DATABASE_PATH = join(workDir, 'chat.db');
process.env.AUTH_ENABLED = '1';

const [{ default: express }, { default: chatRoutes }, { db }, { PROJECT_ROOT }] = await Promise.all([
  import('express'),
  import('../src/routes/chat.routes.mjs'),
  import('../src/db/database.mjs'),
  import('../../../config/loader.mjs'),
]);

const ALICE = { id: 71, username: 'alice', password_hash: 'test', role: 'user' };
const BOB = { id: 72, username: 'bob', password_hash: 'test', role: 'user' };
const CHAT_ID = 'alice-owned-chat';
const STORED_SESSION_ID = `mock:chat:${CHAT_ID}`;
const EXTERNAL_CLAUDE_SESSION_ID = '123e4567-e89b-12d3-a456-426614174000';
let server;
let baseUrl;

function seedChat({ chatId = CHAT_ID, ownerId = ALICE.id, harness = 'mock', sessionId = STORED_SESSION_ID } = {}) {
  db.prepare(`
    INSERT INTO chat_sessions
      (chat_id, title, session_id, origin_session_id, status, model, permission_mode, cwd, harness, owner_user_id)
    VALUES (?, 'owned chat', ?, ?, 'completed', ?, NULL, ?, ?, ?)
  `).run(chatId, sessionId, sessionId, harness, PROJECT_ROOT, harness, ownerId);
}

async function request(method, path, { userId, body } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(userId ? { 'X-Test-User': String(userId) } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return { status: response.status, body: await response.json() };
}

before(async () => {
  db.prepare('INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)').run(
    ALICE.id, ALICE.username, ALICE.password_hash, ALICE.role,
  );
  db.prepare('INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)').run(
    BOB.id, BOB.username, BOB.password_hash, BOB.role,
  );
  seedChat();

  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    const id = Number(req.header('X-Test-User'));
    req.user = process.env.AUTH_ENABLED === '0'
      ? undefined
      : (Number.isInteger(id) && id > 0 ? { id, role: 'user' } : null);
    next();
  });
  app.use('/api/chat', chatRoutes);
  server = createServer(app);
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/chat`;
});

after(async () => {
  try { await request('POST', `/stop/${CHAT_ID}`, { userId: ALICE.id, body: {} }); } catch { /* best effort */ }
  if (server) await new Promise((resolve) => server.close(resolve));
  db.close();
  rmSync(workDir, { recursive: true, force: true });
  delete process.env.DATABASE_PATH;
  delete process.env.AUTH_ENABLED;
});

test('foreign owners cannot resume a chat through /start or /send', async () => {
  const start = await request('POST', '/start', {
    userId: BOB.id,
    body: { chatId: CHAT_ID, prompt: 'cross-owner start', harness: 'mock' },
  });
  assert.equal(start.status, 404);
  assert.equal(start.body.code, 'CHAT_NOT_FOUND');
  assert.equal(start.body.success, false);

  const send = await request('POST', `/send/${CHAT_ID}`, {
    userId: BOB.id,
    body: { message: 'cross-owner send', sessionId: EXTERNAL_CLAUDE_SESSION_ID },
  });
  assert.equal(send.status, 404);
  assert.equal(send.body.code, 'CHAT_NOT_FOUND');

  const row = db.prepare('SELECT owner_user_id FROM chat_sessions WHERE chat_id = ?').get(CHAT_ID);
  assert.equal(row.owner_user_id, ALICE.id);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM chat_messages WHERE chat_id = ?').get(CHAT_ID).n, 0);
});

test('an owned continuation uses the stored engine session, not a client UUID', async () => {
  const response = await request('POST', `/send/${CHAT_ID}`, {
    userId: ALICE.id,
    body: { message: 'continue mine', sessionId: STORED_SESSION_ID },
  });
  assert.equal(response.status, 200, JSON.stringify(response.body));
  assert.equal(response.body.data.sessionId, STORED_SESSION_ID);
  assert.equal(db.prepare('SELECT session_id FROM chat_sessions WHERE chat_id = ?').get(CHAT_ID).session_id, STORED_SESSION_ID);
});

test('a fresh chat cannot resume an arbitrary Claude UUID', async () => {
  const start = await request('POST', '/start', {
    userId: ALICE.id,
    body: { prompt: 'unsafe external resume', sessionId: EXTERNAL_CLAUDE_SESSION_ID },
  });
  assert.equal(start.status, 400);
  assert.equal(start.body.code, 'CHAT_RESUME_FORBIDDEN');
  assert.equal(start.body.success, false);

  const send = await request('POST', '/send/not-a-chat', {
    userId: ALICE.id,
    body: { message: 'unsafe external resume', sessionId: EXTERNAL_CLAUDE_SESSION_ID },
  });
  assert.equal(send.status, 400);
  assert.equal(send.body.code, 'CHAT_RESUME_FORBIDDEN');
});

test('auth-disabled mode retains the existing single-operator continuation behavior', async () => {
  process.env.AUTH_ENABLED = '0';
  try {
    const response = await request('POST', '/start', {
      body: { chatId: CHAT_ID, prompt: 'local continuation', harness: 'mock' },
    });
    assert.equal(response.status, 200, JSON.stringify(response.body));
    assert.equal(response.body.data.sessionId, STORED_SESSION_ID);
    assert.equal(db.prepare('SELECT owner_user_id FROM chat_sessions WHERE chat_id = ?').get(CHAT_ID).owner_user_id, ALICE.id);
  } finally {
    process.env.AUTH_ENABLED = '1';
  }
});
