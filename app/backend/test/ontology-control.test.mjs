// Ontology control-plane tests — store primitives, graph projection, metrics,
// diff, save/concurrency invariants, run-dir candidates & adoption.
//
// 这些用例直接针对 service/store 层（不起 HTTP），因此可在 CI 中确定性地
// 断言「建模 → 持久化 → 读取 → 复用 → 编辑 → 再复用」全链路的不变式。

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

// 破坏性用例只操作「新建的测试场景」，绝不触碰既有场景。
const store = await import('../../../.claude/shared/scripts/ontology_store.mjs');
const svc = await import('../src/services/ontology.service.mjs');

const TEST_SCENE = `test_ontology_ctrl_${process.pid}`;
const CLONE_SCENE = `${TEST_SCENE}_clone`;

/** 构造一个满足 CP-2（schema + ≥1KB）的最小本体。 */
function makeOntology(overrides = {}) {
  const base = {
    ontology_version: '1.1.0',
    created_at: new Date().toISOString(),
    scene: {
      name: TEST_SCENE,
      process_type: 'unit-test synthetic process',
      production_goal: 'verify ontology control plane',
      equipment: [{ id: 'EQ-1', name: '测试设备', type: 'synthetic', function: 'produce data' }],
      stages: [{ id: 'ST-1', name: '测试阶段', sequence: 0, key_physics: 'pV = nRT', key_parameters: ['col_a'] }],
      objectives: ['验证本体控制面'],
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
  };
  return deepMerge(base, overrides);
}

function deepMerge(a, b) {
  if (Array.isArray(b)) return b;
  if (b && typeof b === 'object') {
    const out = { ...a };
    for (const [k, v] of Object.entries(b)) out[k] = deepMerge(a?.[k], v);
    return out;
  }
  return b === undefined ? a : b;
}

function cleanup() {
  for (const scene of [TEST_SCENE, CLONE_SCENE]) {
    try { store.removeScene(scene); } catch { /* not present */ }
  }
}

before(() => cleanup());
after(() => cleanup());

// ─────────────────────── store 原语 ───────────────────────

describe('ontology store — write primitives', () => {
  test('addVersion persists ontology + provenance and indexes metadata', () => {
    const res = store.addVersion({
      sceneKey: TEST_SCENE,
      ontology: makeOntology(),
      buildMode: 'edit',
      title: '单测场景',
      tags: ['unit-test', 'synthetic'],
      notes: 'created by test',
      origin: 'user',
    });
    assert.equal(res.scene_key, TEST_SCENE);
    assert.equal(res.version, 1);
    assert.ok(existsSync(res.path), 'ontology.json must exist on disk');
    const onDisk = JSON.parse(readFileSync(res.path, 'utf-8'));
    assert.equal(onDisk.scene.name, TEST_SCENE);
    const provPath = join(res.path, '..', 'provenance.json');
    assert.ok(existsSync(provPath), 'provenance.json must exist');
    const entry = store.getEntry(TEST_SCENE, 1);
    assert.equal(entry.title, '单测场景');
    assert.deepEqual(entry.tags, ['unit-test', 'synthetic']);
    assert.equal(entry.origin, 'user');
    assert.ok(entry.content_sha256.startsWith('sha256:'));
    assert.equal(entry.summary.signals, 3);
    assert.equal(entry.summary.relationships, 1);
  });

  test('addVersion dedups identical content instead of creating a noise version', () => {
    const first = store.readAsset(TEST_SCENE, 1);
    const again = store.addVersion({ sceneKey: TEST_SCENE, ontology: first.ontology, buildMode: 'edit' });
    assert.equal(again.deduped, true);
    assert.equal(again.version, 1);
    assert.equal(store.listSceneVersions(TEST_SCENE).length, 1);
  });

  test('addVersion rejects sub-1KB payloads (CP-2 floor) and unsafe scene keys', () => {
    assert.throws(() => store.addVersion({ sceneKey: TEST_SCENE, ontology: { scene: { name: 'x' } } }), /CP-2 floor/);
    assert.throws(() => store.addVersion({ sceneKey: '../escape', ontology: makeOntology() }), /invalid scene_key/);
    assert.throws(() => store.addVersion({ sceneKey: '中文场景', ontology: makeOntology() }), /invalid scene_key/);
  });

  test('updateEntry patches metadata without creating a version', () => {
    const before = store.listSceneVersions(TEST_SCENE).length;
    const e = store.updateEntry(TEST_SCENE, 1, { title: '改名后', tags: ['a'], notes: 'n', quality: 'endorsed' });
    assert.equal(e.title, '改名后');
    assert.equal(e.quality, 'endorsed');
    assert.equal(store.listSceneVersions(TEST_SCENE).length, before, 'metadata patch must not add a version');
    assert.throws(() => store.updateEntry(TEST_SCENE, 1, { quality: 'nonsense' }), /invalid quality/);
    const prov = JSON.parse(readFileSync(join(store.STORE_DIR, TEST_SCENE, 'v1', 'provenance.json'), 'utf-8'));
    assert.equal(prov.quality, 'endorsed');
  });

  test('validateOntology accepts a good payload and rejects schema violations', () => {
    const good = store.validateOntology(makeOntology());
    assert.equal(good.ok, true, JSON.stringify(good.errors));
    assert.ok(good.bytes >= store.ONTOLOGY_MIN_BYTES);

    const bad = makeOntology();
    delete bad.relationships;              // required by schema
    bad.signals.process_parameters[0].role = 'not-a-role'; // enum violation
    const res = store.validateOntology(bad);
    assert.equal(res.ok, false);
    assert.ok(res.errors.length > 0);
  });
});

// ─────────────────────── 图投影 ───────────────────────

describe('ontology graph projection', () => {
  const onto = makeOntology();

  test('core layer emits signal nodes, typed edges and stable categories', () => {
    const g = svc.buildGraph(onto);
    const ids = g.nodes.map((n) => n.id);
    assert.ok(ids.includes('col_a') && ids.includes('col_b'));
    assert.ok(ids.includes('scene::root'));
    const rel = g.edges.find((e) => e.relation === 'relationship');
    assert.ok(rel, 'causal relationship must be projected as an edge');
    assert.equal(rel.source, 'col_b');
    assert.equal(rel.target, 'col_a');
    assert.equal(rel.arrow, true);
    assert.equal(rel.dashed, true, 'inferred relationship must render dashed');
    assert.ok(g.categories.some((c) => c.name === 'target'));
    assert.ok(g.categories.some((c) => c.name === 'equipment'));
    assert.ok(g.groups.some((x) => x.label === 'thermal_group'));
  });

  test('knowledge layer adds principles / failure modes / discrepancies', () => {
    const g = svc.buildGraph(onto, { layers: { knowledge: true } });
    const kinds = new Set(g.nodes.map((n) => n.kind));
    assert.ok(kinds.has('principle'));
    assert.ok(kinds.has('failure_mode'));
    assert.ok(kinds.has('discrepancy'));
    assert.ok(g.edges.some((e) => e.relation === 'principle'));
    assert.ok(g.edges.some((e) => e.relation === 'discrepancy'));
  });

  test('structure layer can be switched off', () => {
    const g = svc.buildGraph(onto, { layers: { structure: false } });
    assert.ok(!g.nodes.some((n) => n.kind === 'equipment'));
    assert.ok(!g.nodes.some((n) => n.kind === 'stage'));
    assert.ok(g.nodes.some((n) => n.id === 'col_a'));
  });

  test('dangling relationship endpoints are reported, never silently dropped', () => {
    const broken = makeOntology();
    broken.relationships.push({ from: 'col_b', to: 'col_ghost', type: 'causal', strength: 'weak' });
    const g = svc.buildGraph(broken);
    assert.equal(g.unresolved.length, 1);
    assert.equal(g.unresolved[0].to, 'col_ghost');
    assert.equal(g.unresolved[0].reason, 'target_not_a_signal');
  });

  test('unregistered stage_ref / equipment_ref become explicit placeholder nodes', () => {
    const onto2 = makeOntology();
    onto2.signals.process_parameters[0].stage_ref = 'ST-UNKNOWN';
    const g = svc.buildGraph(onto2);
    const ph = g.nodes.find((n) => n.id === 'stage::ST-UNKNOWN');
    assert.ok(ph, 'placeholder node must exist');
    assert.equal(ph.unresolved_ref, true);
    assert.ok(g.unresolved_refs.includes('stage::ST-UNKNOWN'));
  });

  test('empty / malformed ontology yields an empty graph, not a crash', () => {
    assert.equal(svc.buildGraph(null).empty, true);
    assert.equal(svc.buildGraph('nonsense').empty, true);
    assert.equal(svc.buildGraph({}).nodes.length, 1, 'scene root only');
  });
});

// ─────────────────────── 质量度量 ───────────────────────

describe('ontology health metrics', () => {
  test('computes an explainable score with per-signal ratios', () => {
    const m = svc.computeMetrics(makeOntology());
    assert.equal(m.available, true);
    assert.equal(m.scale.signals_total, 3);
    assert.equal(m.scale.relationships, 1);
    assert.equal(m.semantic_coverage.known, 1);
    assert.equal(m.semantic_coverage.inferred, 1);
    assert.equal(m.semantic_coverage.unit_ratio, 1, 'both numeric signals carry a unit; metadata columns are excluded');
    assert.equal(m.relationship_quality.mechanism_ratio, 1);
    assert.equal(m.relationship_quality.typed_ratio, 1);
    assert.ok(m.health.score > 0 && m.health.score <= 100);
    assert.ok(['A', 'B', 'C', 'D', 'E'].includes(m.health.grade));
    assert.equal(m.health.breakdown.length, 7);
    assert.ok(Math.abs(m.health.breakdown.reduce((s, b) => s + b.points, 0) - m.health.score) <= 1,
      'score must equal the sum of its breakdown points');
  });

  test('flags dangling relationships, duplicate columns and orphans as actionable findings', () => {
    const bad = makeOntology();
    bad.relationships = [{ from: 'col_b', to: 'ghost', type: 'causal' }];
    bad.signals.process_parameters.push({ ...bad.signals.process_parameters[0], role: 'predictor' }); // duplicate column
    const m = svc.computeMetrics(bad);
    const codes = m.findings.map((i) => i.code);
    assert.ok(codes.includes('DANGLING_RELATIONSHIP'));
    assert.ok(codes.includes('DUPLICATE_COLUMN'));
    assert.ok(codes.includes('ORPHAN_SIGNAL'));
    assert.ok(m.consistency.duplicate_columns.length >= 1);
  });

  test('CP-2 failure surfaces as critical findings and caps the score', () => {
    const bad = makeOntology();
    delete bad.signals;   // schema violation
    const v = store.validateOntology(bad);
    const m = svc.computeMetrics(bad, { validation: v });
    assert.equal(v.ok, false);
    assert.ok(m.findings.some((f) => f.code === 'CP2_SCHEMA_INVALID' && f.severity === 'critical'));
    assert.ok(m.health.score < 100);
  });

  test('findings carry RFC 6901 JSON Pointers aligned with RFC 6902 patch coordinates', () => {
    assert.equal(svc.toJsonPointer('$.signals.process_parameters[0].unit'), '/signals/process_parameters/0/unit');
    assert.equal(svc.toJsonPointer('$'), '');
    // `~` 必须先于 `/` 转义（顺序不可交换）
    assert.equal(svc.toJsonPointer('$.a.b~c'), '/a/b~0c');
    assert.equal(svc.toJsonPointer('$.a.http://x'), '/a/http:~1~1x');

    const bad = makeOntology();
    bad.relationships.push({ from: 'col_b', to: 'ghost', type: 'causal' });
    const m = svc.computeMetrics(bad);
    const f = m.findings.find((x) => x.code === 'DANGLING_RELATIONSHIP');
    assert.ok(f, 'dangling relationship must produce a finding');
    assert.equal(f.severity, 'critical');
    assert.equal(f.sourceRule, 'referential-integrity');
    assert.ok(f.justification.length > 0, 'a finding must carry its minimal asserting subset');
  });

  test('findings use the three-level SHACL severity vocabulary only', () => {
    const m = svc.computeMetrics(makeOntology());
    const allowed = new Set(['critical', 'important', 'minor']);
    for (const f of m.findings) {
      assert.ok(allowed.has(f.severity), `unexpected severity: ${f.severity}`);
      assert.ok(f.code && f.sourceRule && f.message);
    }
    assert.deepEqual(Object.keys(m.finding_counts).sort(), ['critical', 'important', 'minor']);
  });

  test('detects causal cycles and contradiction clustering by stage', () => {
    const cyc = makeOntology();
    cyc.relationships = [
      { from: 'col_a', to: 'col_b', type: 'causal', strength: 'strong', mechanism: 'm' },
      { from: 'col_b', to: 'col_a', type: 'causal', strength: 'strong', mechanism: 'm' },
    ];
    const m1 = svc.computeMetrics(cyc);
    assert.equal(m1.topology.causal_cycle_count, 1);
    assert.ok(m1.findings.some((f) => f.code === 'CAUSAL_CYCLE' && f.severity === 'critical'));

    const clustered = makeOntology();
    clustered.signals.process_parameters.push(
      { name: 'col_c', column: 'col_c', role: 'predictor', behavior_match: 'CONTRADICTED', stage_ref: 'ST-1', physical_meaning: 'x' },
      { name: 'col_d', column: 'col_d', role: 'predictor', behavior_match: 'CONTRADICTED', stage_ref: 'ST-1', physical_meaning: 'y' },
    );
    const m2 = svc.computeMetrics(clustered);
    assert.equal(m2.topology.contradiction_clusters.length, 1);
    assert.equal(m2.topology.contradiction_clusters[0].stage, 'ST-1');
    assert.ok(m2.findings.some((f) => f.code === 'CONTRADICTION_CLUSTER'));
  });

  test('impactAnalysis walks the causal graph downstream / upstream', () => {
    const onto = makeOntology();
    const down = svc.impactAnalysis(onto, 'col_b', { direction: 'downstream' });
    assert.equal(down.levels.length, 1);
    assert.equal(down.levels[0].nodes[0].id, 'col_a');
    const up = svc.impactAnalysis(onto, 'col_a', { direction: 'upstream' });
    assert.equal(up.levels[0].nodes[0].id, 'col_b');
  });
});

// ─────────────────────── 差异 ───────────────────────

describe('ontology diff', () => {
  test('aligned by column name — reordering is not a semantic change', () => {
    const a = makeOntology();
    const b = makeOntology();
    const extra = {
      name: 'col_c', column: 'col_c', unit: 'mm', role: 'predictor',
      physical_meaning: '第三列', physical_meaning_confidence: 'KNOWN', normal_range: [1, 3],
    };
    a.signals.process_parameters.push({ ...extra });
    b.signals.process_parameters.push({ ...extra });
    b.signals.process_parameters.reverse();  // 顺序变化不应产生语义差异
    const d = svc.diffOntologies(a, b);
    assert.equal(d.summary.identical, false, 'byte-level identity is expected to differ after reordering');
    assert.equal(d.summary.structurally_identical, true, 'no semantic change may be reported');
    assert.equal(d.summary.signals_changed, 0);
    assert.equal(d.summary.signals_added, 0);
    assert.equal(d.summary.signals_removed, 0);
  });

  test('identical payloads report identical on both axes', () => {
    const d = svc.diffOntologies(makeOntology(), makeOntology());
    assert.equal(d.summary.identical, true);
    assert.equal(d.summary.structurally_identical, true);
  });

  test('reports added / removed / field-changed signals and relationships', () => {
    const a = makeOntology();
    const b = makeOntology();
    b.signals.process_parameters[0].physical_meaning = '改写的物理含义';
    b.signals.process_parameters.push({
      name: 'col_c', column: 'col_c', unit: 'mm', role: 'predictor', physical_meaning: '新增列',
      physical_meaning_confidence: 'KNOWN', normal_range: [1, 2],
    });
    b.relationships.push({ from: 'col_b', to: 'col_a', type: 'correlative', strength: 'weak' });
    const d = svc.diffOntologies(a, b);
    assert.equal(d.summary.signals_added, 1);
    assert.equal(d.summary.signals_changed, 1);
    const sig = d.sections.find((s) => s.label === 'signals');
    assert.deepEqual(sig.added, ['col_c']);
    const changed = sig.changed.find((c) => c.key === 'col_b');
    assert.ok(changed.fields.some((f) => f.path.includes('physical_meaning')));
  });

  test('diffVersions reads both versions out of the store', () => {
    const v2 = store.addVersion({
      sceneKey: TEST_SCENE, ontology: makeOntology({ scene: { production_goal: '第 2 版目标' } }),
      buildMode: 'edit', parentVersion: 1, inheritFrom: store.getEntry(TEST_SCENE, 1),
    });
    const res = svc.diffVersions(TEST_SCENE, 1, v2.version);
    assert.equal(res.scene_key, TEST_SCENE);
    assert.equal(res.from.version, 1);
    assert.equal(res.to.version, v2.version);
    assert.ok(res.diff.scene.length >= 1);
    assert.equal(res.diff.summary.identical, false);
  });
});

// ─────────────────────── 保存不变式 ───────────────────────

describe('saveAsset — persistence invariants', () => {
  test('rejects an invalid payload with 422 and writes nothing', () => {
    const versionsBefore = store.listSceneVersions(TEST_SCENE).length;
    const bad = makeOntology();
    delete bad.scene;
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    assert.throws(
      () => svc.saveAsset({
        sceneKey: TEST_SCENE, ontology: bad, baseVersion: latest,
        expectedSha256: store.getEntry(TEST_SCENE, latest).content_sha256,
      }),
      (e) => e instanceof svc.OntologyError && e.status === 422 && e.code === 'VALIDATION_FAILED',
    );
    assert.equal(store.listSceneVersions(TEST_SCENE).length, versionsBefore, 'no version must be written on 422');
  });

  test('optimistic concurrency: stale base_version is rejected with 409', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    assert.throws(
      () => svc.saveAsset({
        sceneKey: TEST_SCENE, ontology: makeOntology({ scene: { production_goal: 'stale' } }),
        baseVersion: latest - 1, expectedSha256: store.getEntry(TEST_SCENE, latest - 1).content_sha256,
      }),
      (e) => e instanceof svc.OntologyError && e.status === 409 && e.code === 'VERSION_CONFLICT'
        && e.details.latest_version === latest,
    );
  });

  test('a valid edit creates v+1 that inherits the schema fingerprint (reuse stays possible)', () => {
    const before = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    const base = store.getEntry(TEST_SCENE, before);
    const edited = makeOntology();
    edited.signals.process_parameters[0].physical_meaning = '人工校对后的温度语义';
    const res = svc.saveAsset({
      sceneKey: TEST_SCENE, ontology: edited, baseVersion: before,
      expectedSha256: base.content_sha256,
      title: '人工编辑版', tags: ['edited'], notes: 'e2e', author: 'tester',
    });
    assert.equal(res.created_new_version, true);
    assert.equal(res.version, before + 1);
    const entry = store.getEntry(TEST_SCENE, res.version);
    assert.equal(entry.parent_version, before);
    assert.equal(entry.origin, 'user:tester');
    assert.equal(entry.build_mode, 'edit');
    assert.equal(entry.schema_fp, base.schema_fp, 'schema fingerprint must be inherited so findMatch still hits');
    assert.ok(res.metrics.health.score > 0);
    // 历史版本必须原封不动
    const old = store.readAsset(TEST_SCENE, before);
    assert.equal(old.ontology.signals.process_parameters[0].physical_meaning, '过程温度');
  });

  test('editing an existing version without a precondition is a 428 (RFC 6585 §3)', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    assert.throws(
      () => svc.saveAsset({
        sceneKey: TEST_SCENE,
        ontology: makeOntology({ scene: { production_goal: `no-precond ${Date.now()}` } }),
        baseVersion: latest,
      }),
      (e) => e instanceof svc.OntologyError && e.status === 428 && e.code === 'PRECONDITION_REQUIRED'
        && typeof e.details.current_sha256 === 'string',
    );
  });

  test('a stale precondition is a 409 CONTENT_CHANGED — never a silent overwrite', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    assert.throws(
      () => svc.saveAsset({
        sceneKey: TEST_SCENE,
        ontology: makeOntology({ scene: { production_goal: `stale-etag ${Date.now()}` } }),
        baseVersion: latest,
        expectedSha256: 'sha256:0000000000000000000000000000000000000000000000000000000000000000',
      }),
      (e) => e instanceof svc.OntologyError && e.status === 409 && e.code === 'CONTENT_CHANGED'
        && !!e.details.expected && !!e.details.actual,
    );
  });

  test('force=true skips the precondition but still records provenance', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    const res = svc.saveAsset({
      sceneKey: TEST_SCENE, ontology: makeOntology({ scene: { production_goal: `forced ${Date.now()}` } }),
      baseVersion: latest, force: true,
    });
    assert.equal(res.created_new_version, true);
    assert.equal(store.getEntry(TEST_SCENE, res.version).parent_version, latest);
  });

  test('force=true records a rejected version instead of silently pretending success', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    const bad = makeOntology();
    delete bad.relationships;
    const res = svc.saveAsset({ sceneKey: TEST_SCENE, ontology: bad, baseVersion: latest, force: true });
    assert.equal(res.created_new_version, true);
    assert.equal(store.getEntry(TEST_SCENE, res.version).quality, 'rejected');
  });
});

// ─────────────────────── 复用推荐 ───────────────────────

describe('reuse recommendation', () => {
  test('without a data path it lists every asset as a candidate', () => {
    const r = svc.recommend({});
    assert.equal(r.mode, 'list');
    assert.ok(Array.isArray(r.candidates));
    assert.ok(r.candidates.some((c) => c.scene_key === TEST_SCENE));
  });

  test('with a matching data fingerprint it reports an exact reuse hit', () => {
    const dir = mkdtempSync(join(tmpdir(), 'idd-onto-reco-'));
    const csv = join(dir, 'sample.csv');
    writeFileSync(csv, 'ts,col_a,col_b\n1,10.1,25\n2,10.2,26\n3,10.3,27\n');
    try {
      const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
      const asset = store.readAsset(TEST_SCENE, latest);
      const saved = store.addVersion({
        sceneKey: TEST_SCENE,
        ontology: makeOntology({ scene: { production_goal: `fingerprint bind ${Date.now()}` } }),
        buildMode: 'edit', dataFile: csv, parentVersion: latest, inheritFrom: asset.entry,
      });
      const fp = store.computeFingerprint(csv);
      assert.equal(store.getEntry(TEST_SCENE, saved.version).schema_fp, fp.schema_fp);

      const r = svc.recommend({ dataPath: csv });
      assert.equal(r.mode, 'fingerprint');
      assert.equal(r.match.match, 'exact', `expected exact hit, got ${JSON.stringify(r.match)}`);
      assert.equal(r.match.scene_key, TEST_SCENE);
      assert.ok(Array.isArray(r.columns) && r.columns.length === 3);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test('a missing data path is a 404, not a silent empty result', () => {
    assert.throws(() => svc.recommend({ dataPath: 'data/does-not-exist-xyz.csv' }),
      (e) => e instanceof svc.OntologyError && e.status === 404);
  });
});

// ─────────────────────── 克隆 / 删除 ───────────────────────

describe('clone and delete', () => {
  test('clone renames the scene inside the ontology body', () => {
    const latest = Math.max(...store.listSceneVersions(TEST_SCENE).map((e) => e.version));
    const res = svc.cloneAsset({ sceneKey: TEST_SCENE, version: latest, targetScene: CLONE_SCENE });
    assert.equal(res.scene_key, CLONE_SCENE);
    const cloned = store.readAsset(CLONE_SCENE, res.version);
    assert.equal(cloned.ontology.scene.name, CLONE_SCENE);
    assert.match(JSON.stringify(cloned.provenance), new RegExp(`${TEST_SCENE}|${latest}`));
  });

  test('cloning onto an existing scene is a 409', () => {
    assert.throws(() => svc.cloneAsset({ sceneKey: TEST_SCENE, version: 1, targetScene: CLONE_SCENE }),
      (e) => e instanceof svc.OntologyError && e.status === 409);
  });

  test('deleteVersion removes index + disk and prunes the emptied scene dir', () => {
    const versions = store.listSceneVersions(CLONE_SCENE).map((e) => e.version);
    const dir = join(store.STORE_DIR, CLONE_SCENE, `v${versions[0]}`);
    assert.ok(existsSync(dir));
    svc.deleteVersion(CLONE_SCENE, versions[0]);
    assert.ok(!existsSync(dir), 'version directory must be gone');
    assert.equal(store.listSceneVersions(CLONE_SCENE).length, 0);
    assert.ok(!existsSync(join(store.STORE_DIR, CLONE_SCENE)), 'emptied scene directory must be pruned');
  });

  test('deleting an unknown scene is a 404, not a 500', () => {
    assert.throws(() => svc.deleteScene('no_such_scene_xyz'),
      (e) => e instanceof svc.OntologyError && e.status === 404);
    assert.throws(() => svc.deleteVersion(TEST_SCENE, 99999),
      (e) => e instanceof svc.OntologyError && e.status === 404);
  });
});

// ─────────────────────── 列表 / 总览 / run 候选 ───────────────────────

describe('asset listing and overview', () => {
  test('listAssets aggregates versions per scene with health flags', () => {
    const l = svc.listAssets({ scene: TEST_SCENE });
    assert.equal(l.scene_count, 1);
    const s = l.assets[0];
    assert.equal(s.scene_key, TEST_SCENE);
    assert.ok(s.version_count >= 1);
    assert.equal(s.latest_version, Math.max(...s.versions.map((v) => v.version)));
    assert.equal(s.versions[0].version, s.latest_version, 'versions must be newest-first');
    assert.ok(s.versions.every((v) => v.present === true));
    assert.equal(s.broken, false);
    assert.ok(s.summary.signals >= 3);
  });

  test('overview totals add up', () => {
    const o = svc.storeOverview();
    assert.ok(o.totals.scenes >= 1);
    assert.ok(o.totals.versions >= o.totals.scenes);
    assert.ok(o.store_dir.endsWith('ontology_store'));
    assert.ok(Array.isArray(o.totals.broken_scenes));
  });

  test('run-dir candidates expose agent-built ontologies and their store status', () => {
    const c = svc.listCandidates({ includeInStore: true, limit: 500 });
    assert.ok(Array.isArray(c.candidates));
    assert.ok(c.candidates.every((x) => typeof x.run_name === 'string'));
    assert.ok(c.candidates.every((x) => x.proposed_scene && /^[A-Za-z0-9._-]+$/.test(x.proposed_scene)),
      'every proposed scene key must be filesystem safe');
    assert.ok(c.candidates.some((x) => x.validation && typeof x.validation.ok === 'boolean'));
  });

  test('deriveSceneKey normalizes unsafe names and rejects unusable ones', () => {
    // 中文语义名无法安全用作路径 → 归一化后仅保留 ASCII 骨架（原始名保留在 scene_name）
    assert.equal(svc.deriveSceneKey('100,000L 青霉素发酵批次过程'), '100_000L');
    assert.equal(svc.deriveSceneKey('three_system_e2e'), 'three_system_e2e');
    assert.equal(svc.deriveSceneKey('../etc/passwd'), 'etc_passwd');
    assert.equal(svc.deriveSceneKey('ab'), null, 'too short to be a meaningful scene key');
    assert.equal(svc.deriveSceneKey('  '), null);
  });
});

// ─────────────────────── 全链路 ───────────────────────

describe('end-to-end: build → persist → read → reuse → edit → reuse again', () => {
  test('the full lifecycle holds', () => {
    const scene = `${TEST_SCENE}_e2e`;
    const dir = mkdtempSync(join(tmpdir(), 'idd-onto-e2e-'));
    try {
      // 1) 建模：造数据 + 遵循 skill 协议写 RUN_DIR/01_ontology/ontology.json
      const csv = join(dir, 'run_data.csv');
      writeFileSync(csv, 'ts,col_a,col_b\n1,10.1,25\n2,10.2,26\n3,10.3,27\n4,10.4,28\n');
      const runDir = join(dir, 'run-1');
      mkdirSync(join(runDir, '01_ontology'), { recursive: true });
      mkdirSync(join(runDir, '00_input'), { recursive: true });
      writeFileSync(join(runDir, 'run_manifest.json'), JSON.stringify({ run_id: 'run-1', scene_name: scene }));
      writeFileSync(join(runDir, '00_input', 'run_config.json'), JSON.stringify({ data_path: csv }));
      writeFileSync(join(runDir, '01_ontology', 'ontology.json'),
        JSON.stringify(makeOntology({ scene: { name: scene } }), null, 2));

      // 2) Agent 侧发布（skill 协议路径）
      const pub = store.publish({ runDir, scene, buildMode: 'full' });
      assert.equal(pub.scene_key, scene);
      assert.equal(pub.version, 1);
      assert.ok(store.getEntry(scene, 1).schema_fp, 'publish must bind the data fingerprint');

      // 3) 前端读取：列表 + 单资产 + 图 + 度量
      const listed = svc.listAssets({ scene });
      assert.equal(listed.scene_count, 1);
      const asset = svc.getAsset(scene, 1);
      assert.equal(asset.ontology.scene.name, scene);
      assert.ok(asset.graph.nodes.length > 0);
      assert.ok(asset.metrics.health.score > 0);
      assert.equal(asset.validation.ok, true);

      // 4) 复用：指纹命中 → fastReuse 拷贝到新 run 目录
      const runDir2 = join(dir, 'run-2');
      mkdirSync(join(runDir2, '00_input'), { recursive: true });
      const fast = store.fastReuse({ dataPath: csv, runDir: runDir2, scene });
      assert.equal(fast.fastPath, true, JSON.stringify(fast));
      assert.ok(existsSync(join(runDir2, '01_ontology', 'ontology.json')));
      assert.equal(JSON.parse(readFileSync(join(runDir2, '01_ontology', 'ontology.json'), 'utf-8')).scene.name, scene);

      // 5) 前端编辑：改语义 → 保存为 v2（不覆盖 v1）
      const edited = JSON.parse(JSON.stringify(asset.ontology));
      edited.signals.process_parameters[0].physical_meaning = '前端人工校对后的温度语义';
      edited.signals.process_parameters[0].physical_meaning_confidence = 'KNOWN';
      const saved = svc.saveAsset({
        sceneKey: scene, ontology: edited, baseVersion: 1,
        expectedSha256: asset.entry.content_sha256, title: '前端校对版', author: 'e2e',
      });
      assert.equal(saved.version, 2);
      assert.equal(saved.created_new_version, true);

      // 6) 再复用：命中最新版本，且改后的语义生效
      const runDir3 = join(dir, 'run-3');
      mkdirSync(join(runDir3, '00_input'), { recursive: true });
      const fast2 = store.fastReuse({ dataPath: csv, runDir: runDir3, scene });
      assert.equal(fast2.fastPath, true, JSON.stringify(fast2));
      const reused = JSON.parse(readFileSync(join(runDir3, '01_ontology', 'ontology.json'), 'utf-8'));
      assert.equal(reused.signals.process_parameters[0].physical_meaning, '前端人工校对后的温度语义');
      assert.equal(fast2.store_version, 2);

      // 7) 差异可审计
      const d = svc.diffVersions(scene, 1, 2);
      assert.equal(d.diff.summary.identical, false);
      assert.equal(d.diff.summary.signals_changed, 1);

      // 8) 采纳路径：同一本体再次从 run 目录采纳入库 → 去重不产生噪声版本
      const adopted = svc.adoptCandidate({ runDir, scene });
      assert.equal(adopted.deduped, true);

      // 9) 清理
      svc.deleteScene(scene);
      assert.equal(svc.listAssets({ scene }).scene_count, 0);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
