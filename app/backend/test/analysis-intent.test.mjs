// Analysis intent tests — the agent-workbench single entry (no fixed-script analysis).
// Every intent resolves to a real agent run; non-default intents re-point the
// prompt at the matching skill protocol via buildIntentDirective.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const {
  ANALYSIS_INTENTS, resolveAnalysisIntent, buildIntentDirective, buildPrompt,
  buildOntologyDirective,
} = await import('../src/engine/claude-client.mjs');

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
});

describe('ANALYSIS_INTENTS registry', () => {
  test('default intent is registered with no skill override', () => {
    assert.equal(ANALYSIS_INTENTS['deep-diagnosis'], null);
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
