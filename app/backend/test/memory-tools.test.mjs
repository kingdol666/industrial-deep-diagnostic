import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

async function connect(t, handlers) {
  const { createMemoryToolServer } = await import('../src/engine/memory-tools.mjs');
  const configuration = createMemoryToolServer(handlers);
  const client = new Client({ name: 'idd-test-client', version: '1' });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await configuration.instance.connect(serverTransport);
  await client.connect(clientTransport);
  t.after(async () => { await client.close(); await configuration.instance.close(); });
  return client;
}

const readJson = (reply) => JSON.parse(reply.content[0].text);

test('SDK exposes read-only tools and does not resolve memory before the first tool call', async (t) => {
  const calls = [];
  const client = await connect(t, {
    search: (args) => { calls.push(args); return { items: [{ ref_id: 'ref-1', excerpt: '校准测温' }] }; },
    get: (ref) => ({ item: { ref_id: ref, evidence_level: 'L5' } }),
  });
  const list = await client.listTools();
  assert.deepEqual(list.tools.map((tool) => tool.name).sort(), ['memory_get', 'memory_search']);
  assert.equal(calls.length, 0);
  const result = await client.callTool({ name: 'memory_search', arguments: { query: '测温' } });
  assert.equal(result.isError, undefined);
  assert.equal(readJson(result).items[0].ref_id, 'ref-1');
  assert.equal(calls[0].query, '测温');
  assert.equal(readJson(await client.callTool({ name: 'memory_get', arguments: { ref_id: 'ref-1' } })).item.evidence_level, 'L5');
});

test('MCP handlers accept no caller-provided permission and mask internal errors', async (t) => {
  let received;
  const client = await connect(t, {
    search(args) { received = args; return { items: [] }; },
    get() { throw new Error('internal-secret-should-not-leave'); },
  });
  await client.callTool({ name: 'memory_search', arguments: { query: '测温', user_id: 99, line_id: 'other' } });
  if (received) assert.deepEqual(received, { query: '测温' });
  const invalid = await client.callTool({ name: 'memory_search', arguments: { query: '测温', limit: 11 } });
  assert.equal(invalid.isError, true);
  const failed = await client.callTool({ name: 'memory_get', arguments: { ref_id: 'ref-1' } });
  assert.equal(failed.isError, true);
  assert.deepEqual(readJson(failed), { code: 'KNOWLEDGE_UNAVAILABLE' });
});
