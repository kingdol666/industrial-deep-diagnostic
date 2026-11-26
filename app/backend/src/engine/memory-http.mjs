import { randomBytes, timingSafeEqual } from 'node:crypto';
import { createServer } from 'node:http';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { createMemoryToolServer } from './memory-tools.mjs';

const MAX_REQUEST = 16 * 1024;

/** One stateless, loopback-only MCP endpoint per engine attempt. */
export async function openMemoryHttp(handlers) {
  const token = randomBytes(32).toString('base64url');
  const expected = Buffer.from(`Bearer ${token}`);
  let host;
  let closed = false;
  const server = createServer({ requestTimeout: 5000, headersTimeout: 4000, maxHeaderSize: 4096 }, (req, res) => {
    const finish = (code) => { res.writeHead(code, { 'Cache-Control': 'no-store' }); res.end(); };
    if (closed || req.headers.host !== host || req.headers.origin !== undefined) return finish(403);
    if (req.url !== '/mcp') return finish(404);
    const auth = Buffer.from(req.headers.authorization || '');
    if (auth.length !== expected.length || !timingSafeEqual(auth, expected)) return finish(401);
    if (req.method !== 'POST') return finish(405);
    if (!/^application\/json(?:;|$)/i.test(req.headers['content-type'] || '')) return finish(415);
    if (Number(req.headers['content-length']) > MAX_REQUEST) return finish(413);
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size <= MAX_REQUEST) chunks.push(chunk);
      else if (!res.headersSent) finish(413);
    });
    req.on('end', async () => {
      if (closed || res.headersSent || res.destroyed) return;
      let message;
      try { message = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return finish(400); }
      // Batch requests are not needed by the adapters or by MCP 2025-06-18.
      if (!message || typeof message !== 'object' || Array.isArray(message)) return finish(400);
      const { instance } = createMemoryToolServer(handlers);
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
      res.once('close', () => { void instance.close().catch(() => {}); });
      try {
        await instance.connect(transport);
        if (closed) { if (!res.headersSent && !res.destroyed) finish(410); return; }
        await transport.handleRequest(req, res, message);
      } catch {
        if (!res.headersSent && !res.destroyed) finish(500);
        else res.end();
      }
    });
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => { server.off('error', reject); resolve(); });
  });
  host = `127.0.0.1:${server.address().port}`;
  let closing;
  return {
    url: `http://${host}/mcp`, token,
    close() {
      if (!closing) {
        closed = true;
        closing = new Promise((resolve) => server.close(resolve));
        server.closeAllConnections();
      }
      return closing;
    },
  };
}
