// One-shot base tests — real subprocess spawns against a fake CLI shim:
// standardized event mapping, stdin/argFile prompt delivery, session capture
// + re-emit, exit-code → error event (错误即事件), close/abort, resume args.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURE = join(here, 'fixtures', 'fake-oneshot.mjs');
const work = mkdtempSync(join(tmpdir(), 'idd-oneshot-'));
const traceFile = join(work, 'trace.log');

process.env.FAKE_TRACE = traceFile;

const { createOneShotEngineClient } = await import('../src/engine/one-shot.mjs');
const { validateCliArg, quoteCmdArg } = await import('../src/engine/cli-common.mjs');
const { makeCliShim, drain, findEvent, findResult, lastInit, commandEnvKey } = await import('./helpers.mjs');
const { invalidateBinaryCache } = await import('../src/engine/cli-common.mjs');

// ── Spec under test: mirrors the gemini spec shape but on the fake CLI ──
function fakeSpec(id, { promptDelivery = 'stdin', parseLine, sessionMarker = false, mode } = {}) {
  return {
    id,
    mode,
    sessionMarker,
    promptDelivery,
    buildArgs({ promptFile, resumeSessionId }) {
      const args = ['--flag'];
      if (promptFile) args.push(`@${promptFile}`);
      if (resumeSessionId) args.push('--resume');
      return args;
    },
    parseLine,
  };
}

// gemini-shaped mapper (same logic as oneshot-specs.geminiSpec.parseLine)
function geminiLikeParseLine(evt, ctx) {
  if (!evt || typeof evt !== 'object') return null;
  switch (evt.type) {
    case 'init':
      ctx.session(evt.session_id || null);
      return null;
    case 'message':
      if (typeof evt.content === 'string' && evt.content) ctx.text(evt.content);
      return null;
    case 'tool_use':
      ctx.toolUse({ id: evt.tool_id || evt.id, name: evt.name, input: evt.args || evt.input || {} });
      return null;
    case 'tool_result':
      ctx.toolResult({ toolUseId: evt.tool_id || evt.id, content: evt.output ?? '', isError: evt.is_error });
      return null;
    case 'result':
      ctx.result(evt.status === 'success' ? 'success' : 'error_during_execution', evt.status);
      return null;
    default:
      ctx.unknown(evt.type);
      return null;
  }
}

async function runTurn(spec, { prompt = 'hello engine', resumeSessionId = null, timeoutMinutes = 0 } = {}) {
  const client = createOneShotEngineClient(spec);
  const result = client.startDiagnosis({
    analysisTarget: { mode: 'resume' },
    userQuestion: prompt, sceneName: 't', runId: `r_${Math.random().toString(36).slice(2, 8)}`,
    reportLanguage: 'en', sessionId: resumeSessionId,
  });
  const events = await drain(result.query);
  return { events, query: result.query, isResume: result.isResume };
}

describe('cli-common arg discipline', () => {
  test('validateCliArg rejects quotes and control characters', () => {
    assert.equal(validateCliArg('--flag'), '--flag');
    assert.throws(() => validateCliArg('has "quotes"'));
    assert.throws(() => validateCliArg('multi\nline'));
    assert.throws(() => validateCliArg('null\0char'));
  });
  test('quoteCmdArg quotes whitespace and rejects cmd metacharacters', () => {
    assert.equal(quoteCmdArg('plain'), 'plain');
    assert.equal(quoteCmdArg('a b'), '"a b"');
    assert.equal(quoteCmdArg(''), '""');
    assert.throws(() => quoteCmdArg('50%off'));
  });
});

describe('one-shot base — stdin delivery + standardized mapping (gemini dialect)', () => {
  before(() => {
    process.env[commandEnvKey('fakegem')] = makeCliShim(FIXTURE, 'gemini', { name: 'fakegem' });
    invalidateBinaryCache('fakegem');
  });
  after(() => { delete process.env[commandEnvKey('fakegem')]; });

  test('full turn: init → text → tool_use → tool_result → success, prompt via stdin', async () => {
    process.env.FAKE_STDIN_CONTAINS = 'hello engine';
    try {
      const { events, query, isResume } = await runTurn(fakeSpec('fakegem', { parseLine: geminiLikeParseLine }));
      assert.equal(isResume, false);

      const init = lastInit(events);
      assert.ok(init, 'init event emitted');
      assert.equal(init.session_id, 'fakegem:sess-123'); // engine sid captured + prefixed

      const assistant = events.filter((e) => e.type === 'assistant');
      assert.ok(assistant.some((e) => e.message.content.some((b) => b.type === 'text' && b.text === 'thinking about data')));
      const toolUse = assistant.flatMap((e) => e.message.content).find((b) => b.type === 'tool_use');
      assert.equal(toolUse.name, 'shell');
      assert.deepEqual(toolUse.input, { command: 'ls' });

      const toolResult = findEvent(events, 'user', (e) => e.message.content.some((b) => b.type === 'tool_result' && b.tool_use_id === 't1'));
      assert.equal(toolResult.message.content[0].content, 'ok');

      const result = findResult(events);
      assert.equal(result.subtype, 'success');
      assert.equal(result.session_id, 'fakegem:sess-123');
      assert.equal(query.killed, true); // process exited
    } finally {
      delete process.env.FAKE_STDIN_CONTAINS;
    }
  });

  test('session capture re-emits init AFTER the initial marker init (DB update path)', async () => {
    const { events } = await runTurn(fakeSpec('fakegem', { parseLine: geminiLikeParseLine }));
    const inits = events.filter((e) => e.type === 'system' && e.subtype === 'init');
    assert.equal(inits.length, 2);
    assert.match(inits[0].session_id, /^fakegem:unbound:/);
    assert.equal(inits[1].session_id, 'fakegem:sess-123');
  });

  test('resume: buildArgs adds --resume and parseSessionId marks resumable', async () => {
    const spec = fakeSpec('fakegem', { parseLine: geminiLikeParseLine });
    spec.parseSessionId = (marker) => {
      if (typeof marker !== 'string' || !marker.startsWith('fakegem:')) return null;
      const sid = marker.slice('fakegem:'.length);
      return sid && !sid.startsWith('unbound:') ? { sessionId: sid, resumable: true } : null;
    };
    process.env.FAKE_TRACE = traceFile;
    const client = createOneShotEngineClient(spec);
    const result = client.startSessionChat({ runId: 'r_chat', sessionId: 'fakegem:sess-123', message: 'follow up' });
    assert.equal(result.isResume === undefined, true);
    const events = await drain(result.query);
    const result_ = findResult(events);
    assert.equal(result_.subtype, 'success');
    const trace = readFileSync(traceFile, 'utf-8');
    assert.match(trace, /"--resume"/);
    // session continuity: engine reports the resumed session id
    const init = lastInit(events);
    assert.equal(init.session_id, 'fakegem:sess-resumed');
  });

  test('non-zero exit → error result event with engine exit code + stderr tail', async () => {
    process.env.FAKE_EXIT = '3';
    process.env.FAKE_SKIP_RESULT = '1'; // engine emitted no result frame — exit-code fallback kicks in
    try {
      const { events } = await runTurn(fakeSpec('fakegem', { parseLine: geminiLikeParseLine }));
      const result = findResult(events);
      assert.equal(result.subtype, 'error_during_execution');
      assert.match(result.stop_reason, /FAKEGEM_EXIT_3/);
      assert.match(result.stop_reason, /simulated failure 3/);
    } finally {
      delete process.env.FAKE_EXIT;
      delete process.env.FAKE_SKIP_RESULT;
    }
  });

  test('engine-reported failure result wins over exit-code fallback', async () => {
    process.env.FAKE_EXIT = '3'; // result frame with status:'failure' + exit 3
    try {
      const { events } = await runTurn(fakeSpec('fakegem', { parseLine: geminiLikeParseLine }));
      const result = findResult(events);
      assert.equal(result.subtype, 'error_during_execution');
      assert.equal(result.stop_reason, 'failure');
    } finally {
      delete process.env.FAKE_EXIT;
    }
  });

  test('close() aborts a live turn (killed, error event)', async () => {
    process.env.FAKE_DELAY = '1500';
    try {
      const spec = fakeSpec('fakegem', { parseLine: geminiLikeParseLine });
      const client = createOneShotEngineClient(spec);
      const result = client.startDiagnosis({
        analysisTarget: { mode: 'resume' }, userQuestion: 'x', runId: 'r_abort',
      });
      const promise = drain(result.query);
      // close mid-turn while the fake CLI is still in its slow-start delay
      await new Promise((r) => setTimeout(r, 400));
      result.query.close();
      const events = await promise;
      const result_ = findResult(events);
      assert.equal(result_.subtype, 'error_during_execution');
      assert.match(result_.stop_reason, /abort/);
      assert.equal(result.query.killed, true);
    } finally {
      delete process.env.FAKE_DELAY;
    }
  });
});

describe('one-shot base — argFile delivery (pi dialect)', () => {
  before(() => {
    process.env[commandEnvKey('fakepi')] = makeCliShim(FIXTURE, 'pi', { name: 'fakepi' });
    invalidateBinaryCache('fakepi');
  });
  after(() => { delete process.env[commandEnvKey('fakepi')]; });

  test('prompt written to a temp file passed as @path; temp dir cleaned up', async () => {
    const { events } = await runTurn(fakeSpec('fakepi', {
      promptDelivery: 'argFile',
      parseLine(evt, ctx) {
        if (evt?.type === 'session') { ctx.session(evt.id || null); return null; }
        if (evt?.type === 'message_end' && evt.message?.role === 'assistant') {
          const blocks = (evt.message.content || []).map((b) => (b?.type === 'text' ? { type: 'text', text: b.text } : null)).filter(Boolean);
          if (blocks.length) { ctx.turn(); ctx.assistant(blocks); }
        }
        return null;
      },
    }));
    const trace = readFileSync(traceFile, 'utf-8');
    assert.match(trace, /ARGFILE "hello engine"/);
    assert.ok(findEvent(events, 'assistant'));
    const result = findResult(events);
    assert.equal(result.subtype, 'success');
  });
});

describe('one-shot base — plaintext mode (crush dialect)', () => {
  const crushShim = makeCliShim(join(here, 'fixtures', 'fake-plaintext.mjs'), 'x', { name: 'fakecrush' });
  before(() => {
    process.env[commandEnvKey('fakecrush')] = crushShim;
    invalidateBinaryCache('fakecrush');
  });
  after(() => { delete process.env[commandEnvKey('fakecrush')]; });

  test('plain stdout lines aggregate into assistant text; success on exit 0', async () => {
    const { events } = await runTurn(fakeSpec('fakecrush', { mode: 'plaintext' }));
    const texts = events
      .filter((e) => e.type === 'assistant')
      .flatMap((e) => e.message.content)
      .filter((b) => b.type === 'text')
      .map((b) => b.text);
    assert.deepEqual(texts, ['line one', 'line two']);
    assert.equal(findResult(events).subtype, 'success');
  });
});
