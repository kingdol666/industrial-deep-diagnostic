// Analysis intent tests — the agent-workbench single entry (no fixed-script analysis).
// Every intent resolves to a real agent run; non-default intents re-point the
// prompt at the matching skill protocol via buildIntentDirective.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const {
  ANALYSIS_INTENTS, resolveAnalysisIntent, resolvePreprocessingMode,
  buildIntentDirective, buildPrompt, buildOntologyDirective,
} = await import('../src/engine/claude-client.mjs');
const { assertOntologyIntentSupported } = await import('../src/services/ontology-intent-guard.mjs');

describe('resolveAnalysisIntent', () => {
  test('absent / empty / default → deep-diagnosis', () => {
    assert.equal(resolveAnalysisIntent(undefined), 'deep-diagnosis');
    assert.equal(resolveAnalysisIntent(null), 'deep-diagnosis');
    assert.equal(resolveAnalysisIntent(''), 'deep-diagnosis');
    assert.equal(resolveAnalysisIntent('deep-diagnosis'), 'deep-diagnosis');
  });

  test('registered non-default intents pass through as strings', () => {
    for (const id of ['stability-report', 'quick-screen', 'doe-analysis', 'experience-mining', 'optimizer-campaign']) {
      assert.equal(resolveAnalysisIntent(id), id);
    }
  });

  test('unknown intent → null (caller must 400, never silently fall back)', () => {
    assert.equal(resolveAnalysisIntent('bogus'), null);
    assert.equal(resolveAnalysisIntent('sentinel'), null); // legacy script-panel name is retired
  });
});

describe('buildIntentDirective', () => {
  test('default intent appends nothing (baseline pipeline prompt unchanged)', () => {
    assert.equal(buildIntentDirective('deep-diagnosis', 'scene'), '');
    assert.equal(buildIntentDirective(undefined, 'scene'), '');
  });

  test('each non-default intent names its skill and forbids fabrication', () => {
    const cases = [
      ['stability-report', 'industrial-line-stability-report'],
      ['quick-screen', 'industrial-sentinel'],
      ['doe-analysis', 'industrial-doe-analyzer'],
      ['experience-mining', 'industrial-tuning-memory'],
      ['optimizer-campaign', 'industrial-optimizer-loop'],
    ];
    for (const [intent, skill] of cases) {
      const directive = buildIntentDirective(intent, 'bopet_line');
      assert.match(directive, new RegExp(`ANALYSIS_INTENT: ${intent}`));
      assert.match(directive, new RegExp(`Executing skill: ${skill}`));
      assert.match(directive, /SKILL\.md/);
      assert.match(directive, /setup\.mjs/);
      assert.match(directive, /report\.md/);
      assert.match(directive, /never fabricate/i);
      // The directive must supersede the pipeline rules, not coexist ambiguously.
      assert.match(directive, /superseded/);
    }
  });

  test('scene name is filename-normalized into the setup command', () => {
    const directive = buildIntentDirective('quick-screen', 'bad\nscene; rm -rf');
    assert.ok(!directive.includes('\nscene'));
    assert.match(directive, /--name "badscene__rm_-rf"/);
  });

  test('folder-input intents get the deterministic preprocessor step', () => {
    const stability = buildIntentDirective('stability-report', 'line1');
    assert.match(stability, /data_preprocessor\.py/);
    assert.match(stability, /--stability-single-primary/);
    assert.match(stability, /do not merge files or sampling cadences/i);
  });

  test('report intents carry the no-invented-unit rule', () => {
    for (const intent of ['stability-report', 'quick-screen']) {
      const directive = buildIntentDirective(intent, 'line1');
      assert.match(directive, /unit undeclared/i);
      assert.match(directive, /never infer mm\/µm\/°C/i);
    }
  });
});

describe('ANALYSIS_INTENTS registry', () => {
  test('default intent is registered with no skill override', () => {
    assert.equal(ANALYSIS_INTENTS['deep-diagnosis'], null);
  });
});

describe('preprocessingMode policy (plan v2 §4)', () => {
  test('default renders the single-primary preprocessor step only', () => {
    const directive = buildIntentDirective('stability-report', 'line1');
    assert.match(directive, /--stability-single-primary/);
    assert.doesNotMatch(directive, /--integrate-merge/);
  });

  test('integrate_merge opt-in renders the gated merge mode only', () => {
    const directive = buildIntentDirective('stability-report', 'line1', { preprocessingMode: 'integrate_merge' });
    assert.match(directive, /--integrate-merge/);
    assert.doesNotMatch(directive, /--stability-single-primary/);
  });

  test('other intents never render a preprocess step from the mode', () => {
    const directive = buildIntentDirective('quick-screen', 'line1', { preprocessingMode: 'integrate_merge' });
    assert.doesNotMatch(directive, /data_preprocessor\.py/);
  });

  test('resolver: default / accepted / unknown / wrong intent', () => {
    assert.equal(resolvePreprocessingMode('stability-report', undefined), 'single_primary');
    assert.equal(resolvePreprocessingMode('stability-report', ''), 'single_primary');
    assert.equal(resolvePreprocessingMode('stability-report', 'integrate_merge'), 'integrate_merge');
    assert.throws(
      () => resolvePreprocessingMode('stability-report', 'bogus'),
      (err) => err.status === 400 && err.code === 'PREPROCESSING_MODE_UNKNOWN',
    );
    assert.throws(
      () => resolvePreprocessingMode('quick-screen', 'integrate_merge'),
      (err) => err.status === 400 && err.code === 'PREPROCESSING_MODE_UNSUPPORTED_INTENT',
    );
  });
});

describe('ontology field contract', () => {
  test('ontology fields on an unsupported specialist intent are rejected, not ignored', () => {
    for (const intent of ['experience-mining', 'optimizer-campaign']) {
      assert.throws(
        () => assertOntologyIntentSupported(intent, { ontologyMode: 'auto' }),
        (err) => err.status === 400 && err.code === 'ONTOLOGY_UNSUPPORTED_INTENT',
      );
    }
  });

  test('the same fields are accepted for doe-analysis and the watch-family intents', () => {
    for (const intent of ['doe-analysis', 'stability-report', 'quick-screen']) {
      assert.doesNotThrow(
        () => assertOntologyIntentSupported(intent, { ontologyMode: 'auto' }),
      );
    }
  });
});

describe('prompt composition stays intent-safe', () => {
  test('buildPrompt keeps data paths absolute and directive is append-only', () => {
    const target = { mode: 'folder', folderPath: 'D:/data/line1', dataFiles: ['D:/data/line1/a.csv'] };
    const base = buildPrompt('line1', '为什么波动?', target, 'zh', null);
    const withIntent = base + buildIntentDirective('stability-report', 'line1');
    assert.match(withIntent, /D:\/data\/line1/);
    assert.ok(withIntent.startsWith(base));
  });
});

describe('DOE ontology-first directive', () => {
  const doeOntology = {
    profile: 'doe', mode: 'auto', data_stage: 'collected',
    scene_key: 'bopet-lineA-12um-tdo', version: 3, source: null,
    reason: 'doe-analysis intent — ontology-first policy',
  };

  test('profile=doe routes to the DOE directive, not the diagnosis one', () => {
    const text = buildOntologyDirective(doeOntology);
    assert.match(text, /Ontology Directive \(DOE profile\)/);
    assert.match(text, /ONTOLOGY_PROFILE: doe/);
    assert.match(text, /ONTOLOGY_DATA_STAGE: collected/);
    assert.match(text, /ONTOLOGY_SCENE: bopet-lineA-12um-tdo/);
  });

  test('the directive orders prepare → brief → plan → analyzer (hard gate)', () => {
    const text = buildOntologyDirective(doeOntology);
    const prepare = text.indexOf('doe_ontology_prepare.py');
    const readBrief = text.indexOf('Then READ 01_ontology/ontology_brief.json');
    const plan = text.indexOf('write 01_profile/analysis_plan.md');
    const gate = text.indexOf('HARD GATE');
    assert.ok(prepare > 0 && readBrief > prepare && plan > readBrief,
      `order broken: prepare=${prepare} brief=${readBrief} plan=${plan}`);
    assert.ok(gate > 0);
    assert.match(text, /industrial-doe-orchestrator/);
    assert.match(text, /reuses on an exact hit/);
  });

  test('design_only forbids statistics instead of inventing response behaviour', () => {
    const text = buildOntologyDirective({ ...doeOntology, data_stage: 'design_only' });
    assert.match(text, /DATA_STAGE=design_only/);
    assert.match(text, /never invent response behaviour/);
    assert.match(text, /DESIGN_ONLY_NO_RESPONSE/);
  });

  test('a diagnosis profile never leaks the DOE gate', () => {
    const text = buildOntologyDirective({ mode: 'auto', scene_key: 's', reason: 'r' });
    assert.doesNotMatch(text, /doe_ontology_prepare/);
    assert.doesNotMatch(text, /DOE profile/);
  });
});

describe('watch-family ontology directives (plan v2 P1.5/P2.4)', () => {
  test('stability profile renders the stability prepare step and brief-first order', () => {
    const text = buildOntologyDirective({
      profile: 'stability', mode: 'auto', scene_key: 'lineA', data_stage: 'collected',
      source: null, hit: 'pending', reason: 'stability-report intent — ontology-first policy',
    });
    assert.match(text, /Ontology Directive \(watch profile\)/);
    assert.match(text, /ONTOLOGY_PROFILE: stability/);
    assert.match(text, /ontology_prepare\.py/);
    assert.match(text, /industrial-line-stability-report/);
    assert.match(text, /--mode auto/);
    assert.match(text, /--scene lineA/);
    const prepare = text.indexOf('ontology_prepare.py');
    const readBrief = text.indexOf('READ 01_ontology/ontology_brief.json');
    assert.ok(prepare > 0 && readBrief > prepare, 'brief must be read after prepare');
    assert.match(text, /unit undeclared/i);
  });

  test('sentinel profile renders the sentinel prepare step and the window caps', () => {
    const text = buildOntologyDirective({
      profile: 'sentinel', mode: 'full', scene_key: 'millB', data_stage: 'collected',
      source: 'D:/assets/ontology.json', hit: 'pending', reason: 'quick-screen intent',
    });
    assert.match(text, /sentinel_ontology_prepare\.py/);
    assert.match(text, /industrial-sentinel/);
    assert.match(text, /--ontology "D:\/assets\/ontology\.json"/);
    assert.match(text, /ontology_declared/);
    assert.match(text, /capped at warn/);
    assert.match(text, /Never feed ontology values into indicators/);
  });

  test('watch directives never leak DOE-specific gates', () => {
    for (const profile of ['stability', 'sentinel']) {
      const text = buildOntologyDirective({ profile, mode: 'auto', reason: 'r' });
      assert.doesNotMatch(text, /analysis_plan\.md/);
      assert.doesNotMatch(text, /DESIGN_ONLY_NO_RESPONSE/);
      assert.doesNotMatch(text, /doe_ontology_prepare/);
    }
  });
});
