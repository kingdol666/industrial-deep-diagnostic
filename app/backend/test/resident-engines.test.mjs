// Resident-engine tests — fake ACP v1 engine (dsh dialect) and fake codex
// app-server over real stdio: handshake, single-flight prompt, notification
// mapping, approval requests (auto-approve / fail-closed), error paths.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const ACP_FIXTURE = join(here, 'fixtures', 'fake-acp.mjs');
const CODEX_FIXTURE = join(here, 'fixtures', 'fake-codex.mjs');
const work = mkdtempSync(join(tmpdir(), 'idd-resident-'));
const traceFile = join(work, 'trace.log');

process.env.FAKE_TRACE = traceFile;

const { makeCliShim, drain, findEvent, findResult, commandEnvKey } = await import('./helpers.mjs');
const { invalidateBinaryCache } = await import('../src/engine/cli-common.mjs');

describe('dsh (standard ACP v1) — handshake, 单飞 prompt, permission 放行', () => {
  before(() => {
    process.env[commandEnvKey('dsh')] = makeCliShim(ACP_FIXTURE, 'acp', { name: 'fake-dsh' });
    invalidateBinaryCache('dsh');
  });
  after(() => { delete process.env[commandEnvKey('dsh')]; });

  test('full diagnosis turn: session/new → updates mapped → permission allow → end_turn', async () => {
    const { dshClient } = await import('../src/engine/acp-client.mjs');
    const result = dshClient.startDiagnosis({
      analysisTarget: { mode: 'resume' }, userQuestion: 'q', sceneName: 't',
      runId: `dsh_${Date.now()}`, reportLanguage: 'en',
    });
    const events = await drain(result.query);

    const ready = findEvent(events, 'system', (e) => e.subtype === 'session_ready');
    assert.ok(ready, 'session_ready emitted');
    assert.equal(ready.data.engineSessionId, 'acp-sess-1');

    const text = events
      .filter((e) => e.type === 'assistant')
      .flatMap((e) => e.message.content)
      .find((b) => b.type === 'text');
    assert.equal(text.text, 'hi from acp');

    const toolUse = events
      .filter((e) => e.type === 'assistant')
      .flatMap((e) => e.message.content)
      .find((b) => b.type === 'tool_use');
    assert.equal(toolUse.name, 'Bash');

    const toolResult = findEvent(events, 'user', (e) => e.message.content.some((b) => b.type === 'tool_result'));
    assert.equal(toolResult.message.content[0].content, 'ok');

    const resultMsg = findResult(events);
    assert.equal(resultMsg.subtype, 'success');
    assert.equal(resultMsg.stop_reason, 'end_turn');

    // approval was auto-approved (allow_once option selected by kind match)
    const trace = readFileSync(traceFile, 'utf-8');
    assert.match(trace, /PERM .*allow_once/);

    // DB session marker: ACP has no cross-process resume — opaque marker only
    assert.match(result.query.sessionId, /^dsh:run:/);
  });

  test('session chat refuses cross-process resume (诚实语义, 400)', async () => {
    const { dshClient } = await import('../src/engine/acp-client.mjs');
    assert.throws(
      () => dshClient.startSessionChat({ runId: 'x', sessionId: 'dsh:run:x', message: 'hi' }),
      (err) => err.status === 400 && /does not support cross-process session resume/.test(err.message),
    );
  });
});

describe('codex (app-server JSON-RPC) — thread/start + turn/start + approval', () => {
  before(() => {
    process.env[commandEnvKey('codex')] = makeCliShim(CODEX_FIXTURE, 'codex', { name: 'fake-codex' });
    invalidateBinaryCache('codex');
  });
  after(() => { delete process.env[commandEnvKey('codex')]; });

  test('turn: thread created, agentMessage mapped, approval accepted, turn/completed → success', async () => {
    const codex = await import('../src/engine/codex-client.mjs');
    const result = codex.startDiagnosis({
      analysisTarget: { mode: 'resume' }, userQuestion: 'q', sceneName: 't',
      runId: `codex_${Date.now()}`, reportLanguage: 'en',
    });
    const events = await drain(result.query);

    const ready = findEvent(events, 'system', (e) => e.subtype === 'session_ready');
    assert.equal(ready.data.threadId, 'thr_fake_1');

    const text = events
      .filter((e) => e.type === 'assistant')
      .flatMap((e) => e.message.content)
      .find((b) => b.type === 'text');
    assert.equal(text.text, 'hi from codex');

    const toolUse = events
      .filter((e) => e.type === 'assistant')
      .flatMap((e) => e.message.content)
      .find((b) => b.type === 'tool_use');
    assert.match(toolUse.name, /ls|commandExecution/);

    const trace = readFileSync(traceFile, 'utf-8');
    assert.match(trace, /APPROVAL \{"decision":"accept"\}/);

    const resultMsg = findResult(events);
    assert.equal(resultMsg.subtype, 'success');
    assert.equal(resultMsg.session_id, 'codex:thr_fake_1');
  });
});

describe('mapAcpUpdate — session/update mapping table', () => {
  test('agent_message_chunk / thought / tool_call / tool_call_update', async () => {
    const { mapAcpUpdate } = await import('../src/engine/acp-client.mjs');
    const out = [];
    const emit = (m) => out.push(m);
    mapAcpUpdate({ update: { sessionUpdate: 'agent_message_chunk', content: { type: 'text', text: 'a' } } }, emit);
    mapAcpUpdate({ update: { sessionUpdate: 'agent_thought_chunk', content: { text: 't' } } }, emit);
    mapAcpUpdate({ update: { sessionUpdate: 'tool_call', toolCallId: 'x1', title: 'Edit', input: { p: 1 } } }, emit);
    mapAcpUpdate({ update: { sessionUpdate: 'tool_call_update', toolCallId: 'x1', status: 'failed', output: 'boom' } }, emit);
    mapAcpUpdate({ update: { sessionUpdate: 'plan', entries: [] } }, emit); // tolerated

    assert.equal(out[0].message.content[0].type, 'text');
    assert.equal(out[1].message.content[0].type, 'thinking');
    const tool = out[2].message.content[0];
    assert.equal(tool.type, 'tool_use');
    assert.deepEqual(tool.input, { p: 1 });
    const toolRes = out[3].message.content[0];
    assert.equal(toolRes.is_error, true);
    assert.equal(out.length, 4);
  });
});
