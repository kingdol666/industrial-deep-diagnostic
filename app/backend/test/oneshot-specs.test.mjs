// Per-engine spec tests — pure argv/session-marker discipline (no spawn) for
// every one-shot engine, mirroring the documented integration cards.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const specs = await import('../src/engine/oneshot-specs.mjs');

const SPEC_BY_ID = {
  gemini: specs.geminiClient.spec,
  copilot: specs.copilotClient.spec,
  cursor: specs.cursorClient.spec,
  crush: specs.crushClient.spec,
  goose: specs.gooseClient.spec,
  pi: specs.piClient.spec,
};

describe('one-shot engine specs — argv discipline (勿信文档，逐引擎探针固化)', () => {
  test('gemini: stream-json + stdin prompt, resume via --resume <sid>', () => {
    const s = SPEC_BY_ID.gemini;
    assert.equal(s.promptDelivery, 'stdin');
    assert.deepEqual(s.buildArgs({}), ['--output-format', 'stream-json', '-p']);
    assert.deepEqual(s.buildArgs({ resumeSessionId: 'abc' }), ['--output-format', 'stream-json', '-p', '--resume', 'abc']);
  });

  test('copilot: json output, no resume (GitHub 账号锁定)', () => {
    const s = SPEC_BY_ID.copilot;
    assert.equal(s.promptDelivery, 'stdin');
    assert.deepEqual(s.buildArgs({}), ['--output-format', 'json', '-p']);
    assert.equal(s.parseSessionId('copilot:xyz').resumable, false);
  });

  test('cursor: stream-json, 默认不带 --force (文件变更只提案)', () => {
    const args = SPEC_BY_ID.cursor.buildArgs({});
    assert.ok(!args.includes('--force'));
    assert.ok(args.includes('stream-json'));
  });

  test('crush: plaintext mode, run -q', () => {
    const s = SPEC_BY_ID.crush;
    assert.equal(s.mode, 'plaintext');
    assert.deepEqual(s.buildArgs({}), ['run', '-q']);
    assert.equal(s.sessionMarker, true);
  });

  test('goose: -t required, whitespace flattened + argv length cap, bare --resume', () => {
    const s = SPEC_BY_ID.goose;
    assert.equal(s.promptDelivery, 'arg');
    const longPrompt = Array.from({ length: 700 }, () => 'industrial diagnosis narrative').join('\n');
    const args = s.buildArgs({ prompt: longPrompt });
    const t = args[args.indexOf('-t') + 1];
    assert.ok(t.length <= 6200, `goose -t prompt must stay under the Windows argv cap (got ${t.length})`);
    assert.ok(!t.includes('\n'));
    assert.match(t, /truncated for CLI argv limit/);
    assert.deepEqual(args.filter((a) => a === '--resume'), []);
    const resumeArgs = s.buildArgs({ prompt: 'x', resumeSessionId: 'goose:run:r1' });
    assert.deepEqual(resumeArgs.filter((a) => a === '--resume'), ['--resume']);
    // run marker is resumable (name-based); unbound is not
    assert.equal(s.parseSessionId('goose:run:r1').resumable, true);
    assert.equal(s.parseSessionId('goose:unbound:r2').resumable, false);
    assert.equal(s.engineEnv().GOOSE_MODE, 'auto');
    assert.equal(s.engineEnv().GOOSE_DISABLE_SESSION_NAMING, 'true');
  });

  test('pi: @argFile prompt delivery bypasses the ~8K argv cap', () => {
    const s = SPEC_BY_ID.pi;
    assert.equal(s.promptDelivery, 'argFile');
    const args = s.buildArgs({ promptFile: 'C:\\tmp\\p.txt' });
    assert.deepEqual(args, ['--mode', 'json', '-p', '@C:\\tmp\\p.txt']);
    assert.equal(s.parseSessionId('pi:abc').resumable, false);
  });
});

describe('one-shot engine specs — claudeish + goose/pi line mappers', () => {
  test('claudeish mapper (cursor/copilot): frames → standardized events', () => {
    const mapper = SPEC_BY_ID.cursor.parseLine;
    const out = [];
    const ctx = {
      session: (s) => out.push(['session', s]),
      assistant: (c) => out.push(['assistant', c]),
      text: (t) => out.push(['text', t]),
      toolUse: (t) => out.push(['toolUse', t]),
      toolResult: (t) => out.push(['toolResult', t]),
      result: (s2, r) => out.push(['result', s2, r]),
      unknown: (k) => out.push(['unknown', k]),
    };
    mapper({ type: 'system', subtype: 'init', session_id: 'c1' }, ctx);
    mapper({ type: 'assistant', message: { content: [{ type: 'text', text: 'a' }, { type: 'tool_use', id: 't', name: 'Bash', input: {} }] } }, ctx);
    mapper({ type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: 't', content: 'ok', is_error: false }] } }, ctx);
    mapper({ type: 'result', subtype: 'success' }, ctx);
    mapper({ type: 'mystery_event' }, ctx);

    assert.deepEqual(out[0], ['session', 'c1']);
    assert.equal(out[1][0], 'assistant');
    assert.equal(out[1][1].length, 2);
    assert.equal(out[2][0], 'toolResult');
    assert.deepEqual(out[3], ['result', 'success', 'success']);
    assert.deepEqual(out[4], ['unknown', 'mystery_event']); // unknown counted, never thrown
  });

  test('goose mapper: message blocks → text + tool_use, finish → success', () => {
    const mapper = SPEC_BY_ID.goose.parseLine;
    const out = [];
    const ctx = {
      session: (s) => out.push(['session', s]),
      turn: () => out.push(['turn']),
      assistant: (c) => out.push(['assistant', c]),
      toolResult: (t) => out.push(['toolResult', t]),
      result: (s2, r) => out.push(['result', s2, r]),
      unknown: () => {},
    };
    mapper({ type: 'message', message: { role: 'assistant', content: [{ type: 'text', text: 'x' }, { type: 'tool_call', id: 't1', name: 'shell', arguments: '{"cmd":"ls"}' }] } }, ctx);
    mapper({ type: 'tool_call_response', id: 't1', output: 'ok' }, ctx);
    mapper({ type: 'finish', reason: 'done' }, ctx);
    assert.deepEqual(out[0], ['turn']);
    const blocks = out[1][1];
    assert.equal(blocks[0].type, 'text');
    assert.deepEqual(blocks[1].input, { cmd: 'ls' }); // string arguments parsed to object
    assert.equal(out[2][0], 'toolResult');
    assert.deepEqual(out[3], ['result', 'success', 'done']);
  });

  test('pi mapper: message_end assistant blocks, deltas ignored', () => {
    const mapper = SPEC_BY_ID.pi.parseLine;
    const out = [];
    const ctx = {
      session: (s) => out.push(['session', s]),
      turn: () => out.push(['turn']),
      assistant: (c) => out.push(['assistant', c]),
      unknown: () => out.push(['unknown']),
    };
    mapper({ type: 'session', id: 'p1' }, ctx);
    mapper({ type: 'message_update' }, ctx);            // known delta type — deliberately ignored
    mapper({ type: 'totally_unknown_frame' }, ctx);     // unknown → counted, never thrown
    mapper({ type: 'message_end', message: { role: 'assistant', content: [{ type: 'text', text: 'hi' }] } }, ctx);
    assert.deepEqual(out[0], ['session', 'p1']);
    assert.equal(out[1][0], 'unknown'); // unknown counted, ignored
    assert.deepEqual(out[2], ['turn']);
    assert.equal(out[3][1][0].text, 'hi');
  });
});
