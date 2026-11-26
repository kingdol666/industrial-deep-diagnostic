// D5 — omp binary resolution must use the documented shared chain
//
//   harness.engines.<id>.binary → env HARNESS_<ID>_COMMAND → where/PATH
//
// The omp client resolved config.omp.binary / PATH on its own, so the override
// every other engine honors was silently ignored for omp: probe and spawn
// agreed with each other but not with the documented contract (and never with
// HARNESS_OMP_COMMAND). resolveOmpBinary now goes through cli-common's
// resolveCliBinary('omp') (探测与拉起同源) and is exported so tests can pin
// exactly what the spawn path will execute.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync, rmSync, writeFileSync } from 'fs';
import { setTimeout as delay } from 'node:timers/promises';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const HANG_FIXTURE = join(here, 'fixtures', 'fake-hang.mjs');
const work = mkdtempSync(join(tmpdir(), 'idd-omp-chain-'));
const traceFile = join(work, 'trace.log');

// The override must be in place BEFORE the first resolution in this process.
const { makeCliShim, drain, findResult, commandEnvKey } = await import('./helpers.mjs');
const shim = makeCliShim(HANG_FIXTURE, 'omp', { name: 'fake-omp-chain', dir: work });
process.env[commandEnvKey('omp')] = shim;
process.env.FAKE_TRACE = traceFile;

const { resolveCliBinary, invalidateBinaryCache } = await import('../src/engine/cli-common.mjs');
const { resolveOmpBinary, probeOmpEngine, startDiagnosis } = await import('../src/engine/omp-client.mjs');
const { PROJECT_ROOT } = await import('../../../config/loader.mjs');

const sessionDir = join(PROJECT_ROOT, 'workspace', '.omp-sessions', `omp_binary_chain_${process.pid}`);

function pidTraceLines() {
  if (!existsSync(traceFile)) return [];
  return readFileSync(traceFile, 'utf-8').split(/\r?\n/).filter((l) => /^PID \d+ omp$/.test(l.trim()));
}

after(() => {
  rmSync(work, { recursive: true, force: true });
  rmSync(sessionDir, { recursive: true, force: true });
});

describe('omp binary chain — env override is authoritative for probe AND spawn', () => {
  test('resolveOmpBinary honors HARNESS_OMP_COMMAND and agrees with resolveCliBinary', () => {
    invalidateBinaryCache('omp');
    assert.equal(resolveCliBinary('omp'), shim, 'shared chain resolves the override');
    assert.equal(resolveOmpBinary(), shim, 'the spawn path resolves the SAME binary as the probe');
  });

  test('the availability probe really executes the overridden binary', async () => {
    invalidateBinaryCache('omp');
    const probe = await probeOmpEngine();
    assert.equal(probe.available, true);
    assert.equal(probe.binary, shim, 'probe reports the overridden command, not a PATH install');
    assert.match(String(probe.version), /fake-hang omp/);
    assert.ok(pidTraceLines().length >= 1, 'the fake binary actually ran');
  });

  test('startDiagnosis spawns the overridden binary (fake RPC records its pid)', async () => {
    invalidateBinaryCache('omp');
    const before = pidTraceLines().length;
    const result = startDiagnosis({
      analysisTarget: { mode: 'resume' },
      userQuestion: 'hang',
      sceneName: 'omp_binary_chain',
      runId: `omp_binary_chain_${process.pid}`,
      timeoutMinutes: 0.02, // the fixture never finishes a turn — kill it fast
    });
    try {
      const events = await drain(result.query, { timeoutMs: 12000 });
      const res = findResult(events);
      assert.equal(res.subtype, 'error_during_execution');
      assert.equal(res.stop_reason, 'omp_timeout');
      assert.ok(pidTraceLines().length > before, 'the overridden fake binary is the process that was spawned');
    } finally {
      try { result.query.close(); } catch { /* already closed */ }
    }
  });

  test('a bogus override fails honestly (no silent fallback to a PATH install)', async () => {
    const key = commandEnvKey('omp');
    const previous = process.env[key];
    try {
      process.env[key] = join(work, 'no-such-omp.exe');
      invalidateBinaryCache('omp');
      assert.equal(resolveOmpBinary(), join(work, 'no-such-omp.exe'));
      const probe = await probeOmpEngine();
      assert.equal(probe.available, false);
      assert.match(String(probe.error), /ENOENT/);
    } finally {
      process.env[key] = previous;
      invalidateBinaryCache('omp');
    }
  });

  test('without an override the chain falls back to the install/PATH resolution', () => {
    const key = commandEnvKey('omp');
    const previous = process.env[key];
    try {
      delete process.env[key];
      invalidateBinaryCache('omp');
      const shared = resolveCliBinary('omp');
      const resolved = resolveOmpBinary();
      assert.notEqual(resolved, shim, 'no override → not the fake binary');
      if (shared !== 'omp') {
        assert.equal(resolved, shared, 'shared resolution wins (config path / where / PATH hit)');
      } else {
        assert.ok(resolved === 'omp' || existsSync(resolved), `legacy fallback must be usable (${resolved})`);
      }
    } finally {
      process.env[key] = previous;
      invalidateBinaryCache('omp');
    }
  });
});

const memoryToolNames = ['mcp__idd_memory_memory_search', 'mcp__idd_memory_memory_get'];
const memoryToken = 'synthetic-omp-knowledge-token';
const knowledgeTransport = { url: 'http://127.0.0.1:54321/mcp', token: memoryToken };
const memoryFixture = join(work, 'knowledge-rpc.mjs');
writeFileSync(memoryFixture, `
import { appendFileSync, readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { join } from 'node:path';
const args = process.argv.slice(2);
const trace = record => appendFileSync(process.env.FAKE_TRACE, JSON.stringify(record) + '\\n');
const send = event => console.log(JSON.stringify(event));
const cfgPath = args.find(arg => arg.startsWith('--config='))?.slice('--config='.length);
const root = process.env.PI_CODING_AGENT_DIR;
let cfg, mcp, auth;
if (cfgPath) {
  cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
  mcp = JSON.parse(readFileSync(join(root, 'mcp.json'), 'utf8'));
  auth = process.env[mcp.mcpServers.idd_memory.headers.Authorization];
}
trace({ args, root, cfg, mcp, authOK: auth === 'Bearer ${memoryToken}',
  profile: process.env.OMP_PROFILE, baseUrl: process.env.LM_STUDIO_BASE_URL });
send({ type: 'ready' });
createInterface({ input: process.stdin }).on('line', (line) => {
  const msg = JSON.parse(line);
  trace(msg);
  if (msg.type === 'get_state') {
    const bad = process.env.FAKE_OMP_BAD_STATE;
    send({ type: 'response', id: msg.id, command: msg.type, success: true, data: {
      model: { provider: bad === 'model' ? 'other' : 'lm-studio', id: 'google/gemma-4-12b-qat',
        baseUrl: bad === 'endpoint' ? 'http://example.invalid/v1' : 'http://127.0.0.1:1234/v1' },
      systemPrompt: [${JSON.stringify(memoryToolNames[0])}, ...(bad === 'tools' ? [] : [${JSON.stringify(memoryToolNames[1])}])],
      dumpTools: [{ name: 'eval' }],
    } });
  } else if (msg.type === 'prompt') {
    if (cfgPath) send({ type: 'notice', level: 'error', message: 'echo ' + auth });
    send({ type: 'agent_end' });
    // Like real RPC, a turn completion does not close stdin or exit.
  }
});
`);

function useKnowledgeFixture(t, badState) {
  const key = commandEnvKey('omp');
  const runId = `omp_knowledge_${process.pid}_${t.name.replace(/\W/g, '_')}`;
  const trace = join(work, `${runId}.jsonl`);
  const previous = { [key]: process.env[key], FAKE_TRACE: process.env.FAKE_TRACE,
    FAKE_OMP_BAD_STATE: process.env.FAKE_OMP_BAD_STATE, OMP_PROFILE: process.env.OMP_PROFILE };
  process.env[key] = makeCliShim(memoryFixture, '', { name: 'fake-omp-knowledge', dir: work });
  process.env.FAKE_TRACE = trace;
  process.env.OMP_PROFILE = 'operator-profile';
  if (badState) process.env.FAKE_OMP_BAD_STATE = badState;
  else delete process.env.FAKE_OMP_BAD_STATE;
  invalidateBinaryCache('omp');
  t.after(() => {
    for (const [name, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    invalidateBinaryCache('omp');
    rmSync(join(PROJECT_ROOT, 'workspace', '.omp-sessions', runId), { recursive: true, force: true });
  });
  return {
    run: { runId, analysisTarget: { mode: 'resume' }, userQuestion: 'Synthetic QA', sceneName: 'test', timeoutMinutes: 0.15 },
    records: () => readFileSync(trace, 'utf8').trim().split('\n').map(JSON.parse),
  };
}

async function assertAttemptRemoved(dir) {
  for (let i = 0; i < 100 && existsSync(dir); i++) await delay(25);
  assert.equal(existsSync(dir), false, 'attempt config is removed when the RPC process stops');
}

test('OMP knowledge: private config, bearer header, verified registration and pinned local model', async (t) => {
  const { run, records } = useKnowledgeFixture(t);
  const built = startDiagnosis({ ...run, knowledgeTransport });
  const events = await drain(built.query);
  assert.equal(findResult(events).subtype, 'success');
  const [spawn, state, prompt] = records();
  assert.ok(spawn.args.includes('--model=lm-studio/google/gemma-4-12b-qat'));
  assert.equal(spawn.baseUrl, 'http://127.0.0.1:1234/v1');
  assert.equal(spawn.profile, 'default');
  assert.equal(process.env.OMP_PROFILE, 'operator-profile');
  assert.deepEqual(spawn.cfg.enabledProviders, ['lm-studio']);
  assert.equal(spawn.cfg.retry.modelFallback, false);
  assert.deepEqual(spawn.cfg.mcp, { enableProjectConfig: false, startupTimeoutMs: 0 });
  assert.equal(spawn.mcp.mcpServers.idd_memory.type, 'http');
  assert.equal(spawn.mcp.mcpServers.idd_memory.url, knowledgeTransport.url);
  assert.equal(spawn.authOK, true);
  assert.equal(state.type, 'get_state', 'registration checked before prompting');
  assert.equal(prompt.type, 'prompt');
  assert.equal(prompt.message, built.prompt);
  for (const name of memoryToolNames) assert.ok(built.prompt.includes(name));
  assert.ok(!built.prompt.includes(knowledgeTransport.url));
  assert.ok(!JSON.stringify({ spawn, events, prompt }).includes(memoryToken));
  await assertAttemptRemoved(spawn.root);
});

for (const [badState, reason] of [['model', 'omp_knowledge_model_mismatch'], ['endpoint', 'omp_knowledge_model_mismatch'], ['tools', 'omp_knowledge_tools_unavailable']]) {
  test(`OMP knowledge rejects mismatched ${badState} before sending the prompt`, async (t) => {
    const { run, records } = useKnowledgeFixture(t, badState);
    const built = startDiagnosis({ ...run, knowledgeTransport });
    const result = findResult(await drain(built.query));
    assert.equal(result.subtype, 'error_during_execution');
    assert.equal(result.stop_reason, reason);
    const [spawn, state, ...rest] = records();
    assert.equal(state.type, 'get_state');
    assert.deepEqual(rest, []);
    await assertAttemptRemoved(spawn.root);
  });
}

test('OMP leaves the old mode untouched when transport is absent', async (t) => {
  const { run, records } = useKnowledgeFixture(t);
  const built = startDiagnosis(run);
  assert.equal(findResult(await drain(built.query)).subtype, 'success');
  const [spawn, prompt] = records();
  assert.equal(spawn.cfg, undefined);
  assert.equal(spawn.profile, 'operator-profile');
  assert.ok(!spawn.args.some(arg => arg.startsWith('--model=')));
  assert.equal(prompt.type, 'prompt');
  assert.ok(!built.prompt.includes('memory_search'));
});

test('OMP rejects invalid knowledge transports or replay instead of spawning', (t) => {
  const { run } = useKnowledgeFixture(t);
  assert.throws(() => startDiagnosis({ ...run, knowledgeTransport: { ...knowledgeTransport, url: 'https://example.invalid/mcp' } }), /loopback/);
  assert.throws(() => startDiagnosis({ ...run, knowledgeTransport: { ...knowledgeTransport, token: 'bad\r\nsecret' } }), /transport/);
  assert.throws(() => startDiagnosis({ ...run, knowledgeTransport, sessionId: 'omp:run:previous' }), /resume/);
});
