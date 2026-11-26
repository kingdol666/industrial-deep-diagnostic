import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { config } from '../../../config/loader.mjs';
import { buildMemoryToolDirective } from '../src/engine/claude-client.mjs';
import { invalidateBinaryCache } from '../src/engine/cli-common.mjs';
import { closeQuery, startDiagnosis } from '../src/engine/opencode-client.mjs';
import { commandEnvKey, drain, findResult, makeCliShim } from './helpers.mjs';

const provider = 'idd-lmstudio';
const model = 'google/gemma-4-12b-qat';
const transport = { url: 'http://127.0.0.1:54321/mcp', token: 'synthetic-memory-token' };
const run = { runId: 'test-oc', analysisTarget: { mode: 'resume' }, userQuestion: 'Synthetic QA', sceneName: 'test', timeoutMinutes: 0.5 };
const drainRun = (query) => drain(query, { timeoutMs: 35000 });

const fakeServer = `
import { createServer } from 'node:http';
import { appendFileSync } from 'node:fs';
const args = process.argv.slice(2);
const cfg = process.env.OPENCODE_CONFIG_CONTENT;
const env = process.env;
const auth = env.OPENCODE_SERVER_PASSWORD
  ? 'Basic ' + Buffer.from(env.OPENCODE_SERVER_USERNAME + ':' + env.OPENCODE_SERVER_PASSWORD).toString('base64')
  : undefined;
const trace = (record) => appendFileSync(env.FAKE_OPENCODE_TRACE, JSON.stringify(record) + '\\n');
const reapIfOrphaned = () => setTimeout(() => process.exit(0), 5000).unref();
trace({ args, cfg, protected: Boolean(auth) });
const server = createServer(async (req, res) => {
  if (req.headers.authorization !== auth) { res.writeHead(401).end(); return; }
  if (req.url === '/config') {
    let effective = {};
    if (args.includes('--pure')) effective = JSON.parse(cfg);
    if (env.FAKE_OPENCODE_OVERRIDE) {
      effective.model = 'cloud/other';
      reapIfOrphaned();
    }
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify(effective));
  } else if (req.url === '/session') {
    res.end(JSON.stringify({ id: 'fake-session' }));
  } else if (req.url === '/event') {
    res.writeHead(200, { 'content-type': 'text/event-stream' });
    res.flushHeaders();
  } else if (req.url === '/session/fake-session/message') {
    const body = [];
    for await (const bytes of req) body.push(bytes);
    trace({ payload: JSON.parse(Buffer.concat(body).toString()) });
    res.end(JSON.stringify({ parts: [{ type: 'text', text: 'Synthetic answer' }] }));
    reapIfOrphaned();
  } else {
    res.writeHead(404).end();
  }
});
server.listen(Number(args[args.indexOf('--port') + 1]), '127.0.0.1');
`;

function fixture(t, { serviceEnv = {}, harnessEnv = {}, engineModel = 'configured', engineProvider = 'configured-provider' } = {}) {
  const tmp = mkdtempSync(join(tmpdir(), 'idd-oc-test-'));
  const script = join(tmp, 'server.mjs');
  const trace = join(tmp, 'trace.jsonl');
  writeFileSync(script, fakeServer);
  const env = {
    [commandEnvKey('opencode')]: makeCliShim(script, '', { name: 'test-opencode', dir: tmp }),
    FAKE_OPENCODE_TRACE: trace,
    FAKE_OPENCODE_OVERRIDE: undefined,
    IDD_OPENCODE_LMSTUDIO: undefined,
    IDD_OPENCODE_LMSTUDIO_MODEL: undefined,
    OPENCODE_CONFIG_CONTENT: undefined,
    OPENCODE_SERVER_PASSWORD: undefined,
    OPENCODE_SERVER_USERNAME: undefined,
    ...serviceEnv,
  };
  const saved = Object.fromEntries(Object.keys(env).map((key) => [key, process.env[key]]));
  const harness = config.harness.engines.opencode;
  config.harness.engines.opencode = { ...harness, port: undefined, model: engineModel, provider: engineProvider, env: harnessEnv };
  const setEnv = (values) => Object.entries(values).forEach(([key, value]) => {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  });
  setEnv(env);
  invalidateBinaryCache('opencode');
  t.after(() => {
    closeQuery(run.runId);
    invalidateBinaryCache('opencode');
    config.harness.engines.opencode = harness;
    setEnv(saved);
    rmSync(tmp, { recursive: true, force: true });
  });
  return () => readFileSync(trace, 'utf8').trim().split('\n').map((row) => JSON.parse(row));
}

test('diagnosis injects an attempt-local bearer MCP server and advisory, preserving existing JSONC', async (t) => {
  const original = `{
    // Keep the operator settings.
    "instructions": ["https://example.invalid/keep/*",],
    "mcp": { "existing": { "type": "local", "command": ["already-configured"] }, },
  }`;
  const readTrace = fixture(t, { harnessEnv: { OPENCODE_CONFIG_CONTENT: original } });
  const built = startDiagnosis({ ...run, knowledgeTransport: transport });
  assert.ok(built.prompt.endsWith(buildMemoryToolDirective({})));
  assert.doesNotMatch(built.prompt, /synthetic-memory-token|54321/);
  assert.equal(findResult(await drainRun(built.query)).subtype, 'success');
  const [{ cfg, protected: isProtected }, { payload }] = readTrace();
  assert.equal(isProtected, true, 'bearer-bearing config is not exposed via unauthenticated HTTP');
  const actual = JSON.parse(cfg);
  assert.deepEqual(actual.instructions, ['https://example.invalid/keep/*']);
  assert.deepEqual(actual.mcp.existing, { type: 'local', command: ['already-configured'] });
  assert.deepEqual(actual.mcp.idd_memory, {
    type: 'remote', enabled: true, url: transport.url,
    headers: { Authorization: `Bearer ${transport.token}` }, oauth: false,
  });
  assert.deepEqual(payload.model, { modelID: 'configured', providerID: 'configured-provider' });
  assert.equal(payload.parts[0].text, built.prompt);
});

test('without transport or server opt-in, leaves spawn and model settings alone', async (t) => {
  const original = '{ /* operator config */ "model": "other/keep", }';
  const readTrace = fixture(t, { harnessEnv: { OPENCODE_CONFIG_CONTENT: original, IDD_OPENCODE_LMSTUDIO: '1' } });
  const built = startDiagnosis(run);
  assert.ok(!built.prompt.includes(buildMemoryToolDirective({})));
  assert.equal(findResult(await drainRun(built.query)).subtype, 'success');
  const [{ args, cfg, protected: isProtected }, { payload }] = readTrace();
  assert.equal(cfg, original);
  assert.equal(isProtected, false);
  assert.ok(!args.includes('--pure'));
  assert.deepEqual(payload.model, { modelID: 'configured', providerID: 'configured-provider' });
});

for (const modelOverride of [undefined, 'synthetic/custom-model']) {
  test(`LM Studio pins the ${modelOverride ? 'overridden' : 'default'} model and permits only its local provider`, async (t) => {
    const modelID = modelOverride ?? model;
    const modelRef = `${provider}/${modelID}`;
    const readTrace = fixture(t, { serviceEnv: {
      IDD_OPENCODE_LMSTUDIO: '1', IDD_OPENCODE_LMSTUDIO_MODEL: modelOverride,
      OPENCODE_CONFIG_CONTENT: '{"enabled_providers":["cloud"],"disabled_providers":["idd-lmstudio"],"model":"cloud/large","small_model":"cloud/small"}',
    } });
    const built = startDiagnosis({ ...run, knowledgeTransport: transport });
    assert.equal(findResult(await drainRun(built.query)).subtype, 'success');
    const [{ args, cfg }, { payload }] = readTrace();
    const actual = JSON.parse(cfg);
    assert.ok(args.includes('--pure'));
    assert.deepEqual(actual.enabled_providers, [provider]);
    assert.deepEqual(actual.disabled_providers, []);
    assert.equal(actual.model, modelRef);
    assert.equal(actual.small_model, modelRef);
    const local = actual.provider[provider];
    assert.equal(local.npm, '@ai-sdk/openai-compatible');
    assert.equal(local.options.baseURL, 'http://127.0.0.1:1234/v1');
    assert.deepEqual(local.whitelist, [modelID]);
    assert.equal(local.models[modelID].id, modelID);
    assert.equal(local.models[modelID].tool_call, true);
    assert.equal(actual.mcp.idd_memory.headers.Authorization, `Bearer ${transport.token}`);
    assert.deepEqual(payload.model, { modelID, providerID: provider });
  });
}

test('LM Studio fails closed before prompt if resolved config disagrees', async (t) => {
  const readTrace = fixture(t, { serviceEnv: { IDD_OPENCODE_LMSTUDIO: '1', FAKE_OPENCODE_OVERRIDE: 'yes' } });
  const built = startDiagnosis(run);
  const result = findResult(await drainRun(built.query));
  assert.equal(result.subtype, 'error_during_execution');
  assert.match(result.stop_reason, /opencode_lmstudio_config_mismatch/);
  assert.equal(readTrace().length, 1, 'no request reached a prompt route');
});
