import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

const engineModule = '../src/engine/memory-http.mjs';

test('an attempt-local MCP listener authorizes before opening tools and closes with the attempt', async (t) => {
  const module = await import(engineModule).catch((err) => {
    assert.notEqual(err.code, 'ERR_MODULE_NOT_FOUND', 'the attempt MCP transport must exist');
    throw err;
  });
  const calls = [];
  const broker = await module.openMemoryHttp({
    search(args) { calls.push(args); return { items: [] }; },
    get() { return { item: null }; },
  });
  t.after(() => broker.close());
  assert.equal(new URL(broker.url).hostname, '127.0.0.1');
  const unknown = await fetch(broker.url, { method: 'POST', body: '{}' });
  assert.equal(unknown.status, 401);
  const browser = await fetch(broker.url, { method: 'POST', headers: { Origin: 'http://example.test', Authorization: `Bearer ${broker.token}` }, body: '{}' });
  assert.equal(browser.status, 403);
  const client = new Client({ name: 'memory-http-test', version: '1' });
  const transport = new StreamableHTTPClientTransport(new URL(broker.url), {
    requestInit: { headers: { Authorization: `Bearer ${broker.token}` } },
  });
  t.after(() => client.close());
  await client.connect(transport);
  assert.deepEqual((await client.listTools()).tools.map((tool) => tool.name).sort(), ['memory_get', 'memory_search']);
  assert.deepEqual(calls, []);
  const result = await client.callTool({ name: 'memory_search', arguments: { query: '测温', user_id: 123, line_id: 'other' } });
  assert.deepEqual(JSON.parse(result.content[0].text), { items: [] });
  assert.deepEqual(calls, [{ query: '测温' }]);
  await broker.close();
  await assert.rejects(() => fetch(broker.url));
});
