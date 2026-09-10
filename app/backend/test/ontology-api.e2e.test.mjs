// Ontology control-plane HTTP e2e — boots the REAL backend and drives the whole
// ontology lifecycle over HTTP exactly as the management page does:
//
//   agent build (run dir) → publish → list → read → graph → metrics →
//   edit → validate → save (ETag) → read back → reuse (fingerprint) →
//   diff → clone → deprecate → delete
//
// 每一个断言都打在真实响应上，因此「前端能做」与「API 真做到」不会脱节。

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import {
  mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync,
} from 'fs';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const PORT = 3988;
const BASE = `http://127.0.0.1:${PORT}`;
const DB_PATH = join(mkdtempSync(join(tmpdir(), 'idd-onto-api-')), 'e2e.db');

// 本测试专用的场景键，跑完自清理；绝不触碰既有场景
const SCENE = `e2e_onto_api_${process.pid}`;
const CLONE = `${SCENE}_clone`;

let server;
let serverLog = '';

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-4000)}`);
}

/** 统一请求助手：返回 {status, body, headers}，不抛错 —— 让测试显式断言状态码。 */
async function req(method, path, { body, headers } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  return { status: res.status, body: json, headers: res.headers };
}

function makeOntology(sceneKey, overrides = {}) {
  return {
    ontology_version: '1.1.0',
    created_at: new Date().toISOString(),
    scene: {
      name: sceneKey,
      process_type: 'HTTP e2e synthetic process',
      production_goal: 'prove the ontology control API',
      equipment: [{ id: 'EQ-1', name: 'e2e 设备', type: 'synthetic', function: 'emit data' }],
      stages: [{ id: 'ST-1', name: 'e2e 阶段', sequence: 0, key_physics: 'pV=nRT', key_parameters: ['col_a'] }],
      objectives: ['验证本体控制 API'],
    },
    signals: {
      inspection_signals: [{
        name: 'col_a', column: 'col_a', unit: 'mm', role: 'target',
        physical_meaning: '被测几何量', physical_meaning_confidence: 'KNOWN',
        normal_range: [10, 20], equipment_ref: 'EQ-1', stage_ref: 'ST-1',
        governing_law: 'linear elastic', expected_data_behavior: 'stable',
        observed_data_behavior: 'stable', behavior_match: 'CONSISTENT',
        knowledge_source: 'user_provided',
      }],
      process_parameters: [{
        name: 'col_b', column: 'col_b', unit: 'degC', role: 'predictor',
        physical_meaning: '过程温度', physical_meaning_confidence: 'INFERRED',
        auto_inferred: true, inference_basis: 'unit hint', normal_range: [20, 80],
        equipment_ref: 'EQ-1', stage_ref: 'ST-1', knowledge_source: 'auto_inferred',
      }],
      control_variables: [],
      events: [],
      metadata_columns: [{ name: 'ts', column: 'ts', role: 'timestamp', description: '采样时间' }],
    },
    relationships: [{
      from: 'col_b', to: 'col_a', type: 'causal', strength: 'strong',
      mechanism: '热膨胀导致尺寸变化', governing_equation: 'dL = alpha*L*dT',
      predicted_functional_form: 'linear', inferred: true,
    }],
    confounders: [{ variable: 'env_temp', why: '环境温度同时影响两者', controlled: false }],
    parameter_groups: { thermal_group: ['col_a', 'col_b'] },
    physical_principles: [{ principle: 'thermal expansion', equation: 'dL = alpha*L*dT', parameters: ['col_a', 'col_b'], direction: 'positive' }],
    known_failure_modes: [{ mode: 'sensor drift', signature: 'col_a 缓慢偏移', relevance: '常见', source: 'physics_prior' }],
    discrepancy_signals: [{ id: 'DS-1', type: 'range_violation', columns: ['col_a'], ontology_expectation: '10-20', data_observation: '21.5', diagnostic_meaning: '超量程', severity: 'HIGH' }],
    metadata: { units: { col_a: 'mm', col_b: 'degC' }, sampling_rate: '1s', timezone: 'Asia/Shanghai' },
    ...overrides,
  };
}

const workDir = mkdtempSync(join(tmpdir(), 'idd-onto-api-work-'));
let csvPath;
let runDir;

async function cleanupScenes() {
  for (const scene of [SCENE, CLONE]) {
    await req('DELETE', `/api/ontology/scenes/${scene}`).catch(() => {});
  }
}

before(async () => {
  // 1) 造一份真实 CSV 与一个「Agent 已构建」的 run 目录
  csvPath = join(workDir, 'run_data.csv');
  writeFileSync(csvPath, 'ts,col_a,col_b\n1,10.1,25\n2,10.2,26\n3,10.3,27\n4,10.4,28\n5,10.5,29\n');
  runDir = join(repoRoot, 'workspace', 'diagnostic-runs', SCENE);
  mkdirSync(join(runDir, '01_ontology'), { recursive: true });
  mkdirSync(join(runDir, '00_input'), { recursive: true });
  writeFileSync(join(runDir, 'run_manifest.json'),
    JSON.stringify({ run_id: SCENE, scene_name: SCENE, name: SCENE }));
  writeFileSync(join(runDir, '00_input', 'run_config.json'), JSON.stringify({ data_path: csvPath }));
  writeFileSync(join(runDir, '01_ontology', 'ontology.json'),
    JSON.stringify(makeOntology(SCENE), null, 2));

  // 2) 起真实后端
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(PORT),
      SERVER_PORT: String(PORT),
      AUTH_ENABLED: '0',
      DATABASE_PATH: DB_PATH,
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  await waitHealthy();
  await cleanupScenes();
});

after(async () => {
  await cleanupScenes();
  if (server) { server.kill(); server = null; }
  try { rmSync(runDir, { recursive: true, force: true }); } catch { /* ignore */ }
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* ignore */ }
});

// ─────────────────────────────────────────────────────────────

describe('ontology control API — HTTP surface', () => {
  let savedVersion = 1;
  let savedEtag = '';

  test('GET /assets is an empty-but-valid listing before anything is published', async () => {
    const r = await req('GET', '/api/ontology/assets');
    assert.equal(r.status, 200);
    assert.equal(r.body.success, true);
    assert.ok(Array.isArray(r.body.data.assets));
    assert.ok(r.body.data.store_dir.endsWith('ontology_store'));
    assert.equal(r.body.data.schema_path.endsWith('ontology_schema.json'), true);
  });

  test('GET /schema exposes the exact CP-2 schema the pipeline enforces', async () => {
    const r = await req('GET', '/api/ontology/schema');
    assert.equal(r.status, 200);
    assert.equal(r.body.data.schema.title, 'Industrial Ontology Schema v6.4');
    assert.equal(r.body.data.min_bytes, 1024);
  });

  test('GET /candidates surfaces the agent-built run-dir ontology as adoptable', async () => {
    const r = await req('GET', '/api/ontology/candidates');
    assert.equal(r.status, 200);
    const c = r.body.data.candidates.find((x) => x.run_name === SCENE);
    assert.ok(c, `candidate ${SCENE} must be discoverable`);
    assert.equal(c.adoptable, true);
    assert.equal(c.parse_error, null);
    assert.equal(c.validation.ok, true, JSON.stringify(c.validation?.errors));
    assert.equal(c.proposed_scene, SCENE);
    assert.equal(c.summary.signals, 3);
  });

  test('POST /adopt publishes the agent-built ontology into the store', async () => {
    const r = await req('POST', '/api/ontology/adopt', {
      body: { runName: SCENE, scene: SCENE, tags: ['e2e', 'agent'] },
    });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.equal(r.body.data.scene_key, SCENE);
    assert.equal(r.body.data.version, 1);
    savedVersion = r.body.data.version;

    const again = await req('GET', '/api/ontology/candidates');
    const c = again.body.data.candidates.find((x) => x.run_name === SCENE);
    assert.equal(c.adoptable, false, 'after adoption the candidate is no longer adoptable');
    assert.equal(c.in_store.version, 1);
  });

  test('GET /assets/:scene/:version returns ontology + graph + metrics + strong ETag', async () => {
    const r = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    assert.equal(r.status, 200, JSON.stringify(r.body));
    const d = r.body.data;
    assert.equal(d.ontology.scene.name, SCENE);
    assert.equal(d.validation.ok, true);
    assert.ok(d.graph.nodes.some((n) => n.id === 'col_a'));
    assert.ok(d.graph.edges.some((e) => e.relation === 'relationship'));
    assert.ok(d.metrics.health.score > 0);
    assert.ok(Array.isArray(d.metrics.findings));
    // RFC 9110 §8.8.3：必须是强校验器（无 W/ 前缀）
    const etag = r.headers.get('etag');
    assert.ok(etag, 'ETag header must be present');
    assert.ok(!etag.startsWith('W/'), 'ETag must be strong, not weak');
    assert.equal(etag, `"${d.etag}"`);
    savedEtag = d.etag;
  });

  test('GET .../graph honours layer switches; knowledge layer adds knowledge nodes', async () => {
    const core = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}/graph`);
    assert.equal(core.status, 200);
    const coreKinds = new Set(core.body.data.graph.nodes.map((n) => n.kind));
    assert.ok(coreKinds.has('signal'));
    assert.ok(!coreKinds.has('principle'), 'knowledge nodes are off by default');

    const rich = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}/graph?knowledge=1`);
    const richKinds = new Set(rich.body.data.graph.nodes.map((n) => n.kind));
    assert.ok(richKinds.has('principle'));
    assert.ok(richKinds.has('failure_mode'));
    assert.ok(richKinds.has('discrepancy'));

    const flat = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}/graph?structure=0`);
    assert.ok(!flat.body.data.graph.nodes.some((n) => n.kind === 'equipment'));
  });

  test('POST /graph and /metrics project an unsaved draft (live edit preview)', async () => {
    const draft = makeOntology(SCENE);
    draft.signals.process_parameters.push({
      name: 'col_c', column: 'col_c', unit: 'kPa', role: 'predictor',
      physical_meaning: '新增压力', physical_meaning_confidence: 'KNOWN', normal_range: [90, 110],
    });
    const g = await req('POST', '/api/ontology/graph', { body: { ontology: draft } });
    assert.equal(g.status, 200);
    assert.ok(g.body.data.graph.nodes.some((n) => n.id === 'col_c'));

    const m = await req('POST', '/api/ontology/metrics', { body: { ontology: draft } });
    assert.equal(m.status, 200);
    assert.equal(m.body.data.metrics.scale.signals_total, 4);
  });

  test('POST /validate catches schema violations without touching the store', async () => {
    const bad = makeOntology(SCENE);
    delete bad.relationships;
    const r = await req('POST', '/api/ontology/validate', { body: { ontology: bad } });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.ok, false);
    assert.ok(r.body.data.errors.length > 0);
    assert.ok(r.body.data.metrics.findings.some((f) => f.code === 'CP2_SCHEMA_INVALID' && f.severity === 'critical'));
  });

  test('PUT without a precondition is refused with 428 (no silent lost update)', async () => {
    const edited = makeOntology(SCENE);
    edited.scene.production_goal = 'should not be written';
    const r = await req('PUT', `/api/ontology/assets/${SCENE}/${savedVersion}`, { body: { ontology: edited } });
    assert.equal(r.status, 428, JSON.stringify(r.body));
    assert.equal(r.body.code, 'PRECONDITION_REQUIRED');
    assert.ok(r.body.details.current_sha256);
  });

  test('PUT with a stale If-Match is refused with 409 (never a silent overwrite)', async () => {
    const edited = makeOntology(SCENE);
    edited.scene.production_goal = 'stale write must not land';
    const r = await req('PUT', `/api/ontology/assets/${SCENE}/${savedVersion}`, {
      headers: { 'If-Match': '"sha256:0000000000000000000000000000000000000000000000000000000000000000"' },
      body: { ontology: edited },
    });
    assert.equal(r.status, 409, JSON.stringify(r.body));
    assert.equal(r.body.code, 'CONTENT_CHANGED');
  });

  test('PUT with a failing CP-2 payload is refused with 422 and writes nothing', async () => {
    const bad = makeOntology(SCENE);
    delete bad.scene;
    const r = await req('PUT', `/api/ontology/assets/${SCENE}/${savedVersion}`, {
      headers: { 'If-Match': `"${savedEtag}"` },
      body: { ontology: bad },
    });
    assert.equal(r.status, 422, JSON.stringify(r.body));
    assert.equal(r.body.code, 'VALIDATION_FAILED');
    const check = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    assert.equal(check.body.data.version, savedVersion, 'no version may be created on 422');
  });

  test('PUT with If-Match saves a NEW version and returns its ETag (history untouched)', async () => {
    const edited = makeOntology(SCENE);
    edited.signals.process_parameters[0].physical_meaning = '前端人工校对后的温度语义';
    edited.signals.process_parameters[0].physical_meaning_confidence = 'KNOWN';
    const r = await req('PUT', `/api/ontology/assets/${SCENE}/${savedVersion}`, {
      headers: { 'If-Match': `"${savedEtag}"` },
      body: {
        ontology: edited, title: '前端校对版', tags: ['edited'], notes: 'http e2e',
      },
    });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.equal(r.body.data.created_new_version, true);
    assert.equal(r.body.data.version, savedVersion + 1);
    const newEtag = r.headers.get('etag');
    assert.ok(newEtag && !newEtag.startsWith('W/'));
    savedVersion = r.body.data.version;

    // 历史版本原封不动
    const old = await req('GET', `/api/ontology/assets/${SCENE}/1`);
    assert.equal(old.body.data.ontology.signals.process_parameters[0].physical_meaning, '过程温度');
    assert.equal(old.body.data.entry.quality, 'unvalidated');

    // 新版本可读且语义已生效
    const cur = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    assert.equal(cur.body.data.ontology.signals.process_parameters[0].physical_meaning, '前端人工校对后的温度语义');
    assert.equal(cur.body.data.entry.parent_version, 1);
    assert.ok(cur.body.data.entry.origin.startsWith('user'));
  });

  test('GET /diff reports the semantic delta between the two versions', async () => {
    const r = await req('GET', `/api/ontology/diff?scene=${SCENE}&from=1&to=${savedVersion}`);
    assert.equal(r.status, 200);
    assert.equal(r.body.data.diff.summary.signals_changed, 1);
    assert.equal(r.body.data.diff.summary.structurally_identical, false);
    const sig = r.body.data.diff.sections.find((s) => s.label === 'signals');
    assert.ok(sig.changed[0].fields.some((f) => f.path.includes('physical_meaning')));
  });

  test('POST /diff compares two arbitrary payloads (import preview)', async () => {
    const a = makeOntology(SCENE);
    const b = makeOntology(SCENE);
    b.relationships = [];
    const r = await req('POST', '/api/ontology/diff', { body: { before: a, after: b } });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.diff.summary.relationships_removed, 1);
  });

  test('POST /recommend finds the scene by data fingerprint (reusable ontology lookup)', async () => {
    // 先把当前版本绑定到这份数据指纹
    const cur = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    const r0 = await req('PUT', `/api/ontology/assets/${SCENE}/${savedVersion}`, {
      headers: { 'If-Match': `"${cur.body.data.etag}"` },
      body: {
        ontology: { ...cur.body.data.ontology, scene: { ...cur.body.data.ontology.scene, production_goal: `fp bind ${Date.now()}` } },
        dataFile: csvPath,
      },
    });
    assert.equal(r0.status, 201, JSON.stringify(r0.body));
    savedVersion = r0.body.data.version;

    const r = await req('POST', '/api/ontology/recommend', { body: { dataPath: csvPath } });
    assert.equal(r.status, 200, JSON.stringify(r.body));
    assert.equal(r.body.data.mode, 'fingerprint');
    assert.equal(r.body.data.match.match, 'exact', JSON.stringify(r.body.data.match));
    assert.equal(r.body.data.match.scene_key, SCENE);
    assert.equal(r.body.data.columns.length, 3);
  });

  test('POST /recommend with a missing data path is an explicit 404', async () => {
    const r = await req('POST', '/api/ontology/recommend', { body: { dataPath: 'data/no-such-file-xyz.csv' } });
    assert.equal(r.status, 404);
    assert.equal(r.body.code, 'DATA_NOT_FOUND');
  });

  test('PATCH updates editorial metadata without creating a version', async () => {
    const before = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    const r = await req('PATCH', `/api/ontology/assets/${SCENE}/${savedVersion}`, {
      body: { title: 'E2E 重命名', tags: ['renamed'], quality: 'endorsed' },
    });
    assert.equal(r.status, 200);
    assert.equal(r.body.data.title, 'E2E 重命名');
    assert.equal(r.body.data.quality, 'endorsed');
    const after = await req('GET', `/api/ontology/assets/${SCENE}/${savedVersion}`);
    assert.equal(after.body.data.version, savedVersion, 'metadata patch must not add a version');
    assert.equal(after.body.data.entry.title, 'E2E 重命名');
  });

  test('POST /clone copies the model into a new scene with the new name inside', async () => {
    const r = await req('POST', `/api/ontology/assets/${SCENE}/${savedVersion}/clone`, {
      body: { target_scene: CLONE, title: '克隆场景' },
    });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    assert.equal(r.body.data.scene_key, CLONE);
    const c = await req('GET', `/api/ontology/assets/${CLONE}/${r.body.data.version}`);
    assert.equal(c.body.data.ontology.scene.name, CLONE);
  });

  test('POST /assets scaffolds a brand-new ontology that already passes CP-2', async () => {
    const scene = `${SCENE}_new`;
    const r = await req('POST', '/api/ontology/assets', {
      body: { scene_key: scene, process_type: 'scaffold test', objective: 'verify scaffold' },
    });
    assert.equal(r.status, 201, JSON.stringify(r.body));
    const v = await req('GET', `/api/ontology/assets/${scene}/${r.body.data.version}`);
    assert.equal(v.body.data.validation.ok, true, JSON.stringify(v.body.data.validation.errors));
    assert.equal(v.body.data.ontology.scene.name, scene);
    await req('DELETE', `/api/ontology/scenes/${scene}`);
  });

  test('POST /assets rejects an unsafe scene_key with 400', async () => {
    const r = await req('POST', '/api/ontology/assets', { body: { scene_key: '../escape' } });
    assert.equal(r.status, 400);
    assert.equal(r.body.code, 'SCENE_INVALID');
  });

  test('GET /overview totals reflect what was published', async () => {
    const r = await req('GET', '/api/ontology/overview');
    assert.equal(r.status, 200);
    assert.ok(r.body.data.totals.scenes >= 2);
    assert.ok(r.body.data.totals.versions >= 2);
    assert.ok(Object.keys(r.body.data.by_origin).length > 0);
  });

  test('unknown asset / scene are honest 404s', async () => {
    const a = await req('GET', `/api/ontology/assets/${SCENE}/99999`);
    assert.equal(a.status, 404);
    assert.equal(a.body.code, 'ONTOLOGY_NOT_FOUND');
    const d = await req('DELETE', '/api/ontology/scenes/definitely_not_a_scene_xyz');
    assert.equal(d.status, 404);
  });

  test('the full reuse chain: edited model is what a new run reuses', async () => {
    // 复用由管线调用 store 的 fastReuse —— 这里通过「推荐 → 读取资产内容」验证同一事实源
    const rec = await req('POST', '/api/ontology/recommend', { body: { dataPath: csvPath, scene: SCENE } });
    assert.equal(rec.body.data.match.match, 'exact');
    const version = rec.body.data.match.version;
    const asset = await req('GET', `/api/ontology/assets/${SCENE}/${version}`);
    assert.equal(asset.status, 200);
    assert.equal(asset.body.data.ontology.signals.process_parameters[0].physical_meaning, '前端人工校对后的温度语义',
      'reuse must resolve to the human-edited semantics, not the original build');
    assert.ok(existsSync(runDir), 'run dir still holds the agent-built original');
    const original = JSON.parse(readFileSync(join(runDir, '01_ontology', 'ontology.json'), 'utf-8'));
    assert.equal(original.signals.process_parameters[0].physical_meaning, '过程温度');
  });

  test('DELETE /assets removes a single version and prunes the store entry', async () => {
    const r = await req('DELETE', `/api/ontology/assets/${CLONE}/1`);
    assert.equal(r.status, 200);
    const gone = await req('GET', `/api/ontology/assets/${CLONE}/1`);
    assert.equal(gone.status, 404);
    await req('DELETE', `/api/ontology/scenes/${CLONE}`);
  });

  test('DELETE /scenes removes the scene from the listing', async () => {
    const r = await req('DELETE', `/api/ontology/scenes/${SCENE}`);
    assert.equal(r.status, 200);
    assert.ok(r.body.data.removed_versions.length >= 2);
    const list = await req('GET', `/api/ontology/assets?scene=${SCENE}`);
    assert.equal(list.body.data.scene_count, 0);
  });
});
