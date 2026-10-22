// DOE artifact manifest — the single retrieval contract for the tasks API and
// the external API. Unit-level: no DB, no server.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const {
  DOE_ARTIFACTS, buildArtifactManifest, resolveRunDir,
} = await import('../src/services/artifact-manifest.service.mjs');

function makeRun({ manifest = false, omit = [] } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'doe-artifacts-'));
  for (const [kind, rel] of DOE_ARTIFACTS) {
    if (omit.includes(kind)) continue;
    const abs = join(dir, rel);
    mkdirSync(join(abs, '..'), { recursive: true });
    const body = rel.endsWith('.json')
      ? JSON.stringify({ contract_version: '1.1', kind })
      : `<html>${kind}</html>`;
    writeFileSync(abs, body);
  }
  if (manifest) {
    writeFileSync(join(dir, 'artifact_manifest.json'), JSON.stringify({
      contract_version: '1.1',
      run_id: 'run-1',
      artifacts: [{ kind: 'effect_table', path: '02_analysis/effect_table.json', sha256: 'x'.repeat(64) }],
      missing: [],
    }));
  }
  return dir;
}

describe('DOE_ARTIFACTS', () => {
  test('covers every v1.1 artifact kind the agent must read', () => {
    const kinds = DOE_ARTIFACTS.map(([k]) => k);
    for (const k of ['ontology', 'ontology_brief', 'ontology_coverage', 'analysis_plan',
      'data_profile', 'effect_table', 'model', 'association_screen', 'doe_conclusion',
      'recommendations', 'next_design', 'optimization_guidance', 'report']) {
      assert.ok(kinds.includes(k), `missing ${k}`);
    }
    assert.equal(new Set(kinds).size, kinds.length);
  });
});

describe('buildArtifactManifest', () => {
  test('probing a complete run dir returns every artifact with sha256 + schema_version', () => {
    const dir = makeRun();
    try {
      const m = buildArtifactManifest(dir);
      assert.equal(m.source, 'probe');
      assert.equal(m.missing.length, 0);
      assert.equal(m.artifacts.length, DOE_ARTIFACTS.length);
      for (const a of m.artifacts) {
        assert.match(a.sha256, /^[0-9a-f]{64}$/);
        assert.equal(a.url, null); // URLs are added by the API layer
        assert.ok(a.bytes > 0);
      }
      const eff = m.artifacts.find((a) => a.kind === 'effect_table');
      assert.equal(eff.schema_version, '1.1');
      assert.equal(eff.path, '02_analysis/effect_table.json');
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('a writer-authored artifact_manifest.json is the single source (source=analyzer)', () => {
    const dir = makeRun({ manifest: true });
    try {
      const m = buildArtifactManifest(dir);
      assert.equal(m.source, 'analyzer');
      assert.equal(m.run_id, 'run-1');
      assert.equal(m.artifacts.length, 1);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('a missing required artifact is explicit; report/plan are conditional', () => {
    const dir = makeRun({ omit: ['effect_table', 'report', 'analysis_plan'] });
    try {
      const m = buildArtifactManifest(dir);
      assert.ok(m.missing.some((x) => x.kind === 'effect_table'));
      assert.ok(!m.missing.some((x) => x.kind === 'report'));
      assert.ok(!m.missing.some((x) => x.kind === 'analysis_plan'));
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('a corrupt manifest is rebuilt, never trusted', () => {
    const dir = makeRun();
    try {
      writeFileSync(join(dir, 'artifact_manifest.json'), '{not json');
      const m = buildArtifactManifest(dir);
      assert.equal(m.source, 'probe');
      assert.equal(m.missing.length, 0);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('absent run dir returns an empty manifest, not a throw', () => {
    const m = buildArtifactManifest(join(tmpdir(), 'does-not-exist-idd'));
    assert.equal(m.source, 'absent');
    assert.deepEqual(m.artifacts, []);
  });

  test('intents with no inventory get an explicit not-applicable manifest (no false missing)', () => {
    const dir = makeRun({ omit: ['effect_table', 'recommendations'] });
    try {
      const m = buildArtifactManifest(dir, { analysisIntent: 'experience-mining' });
      assert.equal(m.applicable, false);
      assert.equal(m.source, 'not-applicable');
      assert.equal(m.analysis_intent, 'experience-mining');
      assert.deepEqual(m.artifacts, []);
      assert.deepEqual(m.missing, []);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('specialist inventories (plan v2 Phase C2): stability and sentinel artifacts are indexed', () => {
    const dir = makeRun();
    try {
      // A stability run dir: the specialist products live under line_report/.
      mkdirSync(join(dir, 'line_report'), { recursive: true });
      writeFileSync(join(dir, 'line_report', 'stability_report.json'), JSON.stringify({ contract_version: 'line-stability-report/1.0' }));
      writeFileSync(join(dir, 'line_report', 'line_stability_report.html'), '<html>zh</html>');
      writeFileSync(join(dir, 'line_report', 'line_stability_report.md'), '# 报告');
      const st = buildArtifactManifest(dir, { analysisIntent: 'stability-report' });
      assert.equal(st.applicable, true);
      assert.ok(st.artifacts.some((a) => a.kind === 'stability_report'));
      assert.ok(st.artifacts.some((a) => a.kind === 'stability_html'));
      assert.ok(st.artifacts.some((a) => a.kind === 'stability_md'));
      assert.ok(!st.missing.some((x) => x.kind === 'stability_report'));

      // A sentinel run dir: alert.json + two reports under sentinel/.
      mkdirSync(join(dir, 'sentinel'), { recursive: true });
      writeFileSync(join(dir, 'sentinel', 'alert.json'), JSON.stringify({ contract_version: 'sentinel-alert/1.0' }));
      writeFileSync(join(dir, 'sentinel', 'watch_report.md'), '# 巡检');
      writeFileSync(join(dir, 'sentinel', 'quick_screen_report.html'), '<html>zh</html>');
      const sn = buildArtifactManifest(dir, { analysisIntent: 'quick-screen' });
      assert.equal(sn.applicable, true);
      assert.ok(sn.artifacts.some((a) => a.kind === 'alert'));
      assert.ok(sn.artifacts.some((a) => a.kind === 'watch_report'));
      assert.ok(sn.artifacts.some((a) => a.kind === 'quick_screen_html'));
      assert.deepEqual(sn.missing.filter((x) => ['alert', 'watch_report', 'quick_screen_html'].includes(x.kind)), []);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test('doe-analysis keeps the DOE inventory and missing semantics', () => {
    const dir = makeRun({ omit: ['effect_table'] });
    try {
      const m = buildArtifactManifest(dir, { analysisIntent: 'doe-analysis' });
      assert.equal(m.applicable, true);
      assert.ok(m.missing.some((x) => x.kind === 'effect_table'));
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
});

describe('resolveRunDir', () => {
  test('absolute stays absolute; relative joins the project root', () => {
    const abs = 'C:/runs/x';
    assert.equal(resolveRunDir('C:/proj', abs), abs);
    assert.equal(resolveRunDir('C:/proj', 'workspace/x'), join('C:/proj', 'workspace/x'));
    assert.equal(resolveRunDir('C:/proj', null), null);
  });
});
