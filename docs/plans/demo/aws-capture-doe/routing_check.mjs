#!/usr/bin/env node
/**
 * Cross-repo routing check: does each real scenario pick the right skill?
 *
 * IDD side (authoritative): every analysis intent resolves to a real agent run
 * whose directive names exactly one skill protocol; the DOE intent additionally
 * carries the ontology-first hard gate (prepare → brief → plan → analyzer).
 *
 * AgentWorkShop side (caller): the bridge's intent catalog must name the same
 * skills, and its default question for each intent must not be the generic
 * deep-diagnosis text. The bridge's question-override defect is reported as a
 * platform finding (the IDD directive still binds the run, but the business
 * question reaching the agent would be wrong).
 *
 * Usage:
 *   node routing_check.mjs [--aws <AgentWorkShop root>] [--json]
 * Exit 0 when every IDD check passes (AWS findings are reported separately).
 */
import { existsSync, readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { join, resolve } from 'node:path';

const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const REPO = resolve(HERE, '../../../..');
const args = process.argv.slice(2);
const awsIdx = args.indexOf('--aws');
const AWS_ROOT = awsIdx >= 0 ? resolve(args[awsIdx + 1])
  : (process.env.AWS_ROOT ? resolve(process.env.AWS_ROOT) : 'D:/codes/ABO/AgentWorkShop');
const AS_JSON = args.includes('--json');

const checks = [];
const warnings = [];
function check(id, ok, detail = '') {
  checks.push({ id, ok, detail });
  if (!AS_JSON) console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${id}${ok ? '' : `  ${detail}`}`);
}

const idd = await import(pathToFileURL(join(REPO, 'app/backend/src/engine/claude-client.mjs')).href);
const IDD_INTENTS = ['deep-diagnosis', 'stability-report', 'quick-screen',
  'doe-analysis', 'experience-mining', 'optimizer-campaign'];
const EXPECTED_SKILL = {
  'stability-report': 'industrial-line-stability-report',
  'quick-screen': 'industrial-sentinel',
  'doe-analysis': 'industrial-doe-analyzer',
  'experience-mining': 'industrial-tuning-memory',
  'optimizer-campaign': 'industrial-optimizer-loop',
};

for (const id of IDD_INTENTS) {
  check(`idd.resolve.${id}`, idd.resolveAnalysisIntent(id) === id);
}
check('idd.unknown.rejected', idd.resolveAnalysisIntent('sentinel') === null);
check('idd.default.empty_directive', idd.buildIntentDirective('deep-diagnosis', 'x') === '');

for (const [id, skill] of Object.entries(EXPECTED_SKILL)) {
  const text = idd.buildIntentDirective(id, 'bopet-lineA');
  check(`idd.directive.${id}`,
    text.includes(`ANALYSIS_INTENT: ${id}`) && text.includes(`Executing skill: ${skill}`)
    && /never fabricate/i.test(text),
    'directive does not bind the skill');
}

const doeText = idd.buildIntentDirective('doe-analysis', 'bopet-lineA');
check('idd.doe.directive_names_orchestrator',
  /industrial-doe-analyzer/.test(doeText) && /SKILL\.md/.test(doeText));
const doeOnt = idd.buildOntologyDirective({
  profile: 'doe', mode: 'auto', data_stage: 'collected',
  scene_key: 'bopet-lineA-12um-tdo', version: 1, reason: 'routing check',
});
const p1 = doeOnt.indexOf('doe_ontology_prepare.py');
const p2 = doeOnt.indexOf('Then READ 01_ontology/ontology_brief.json');
const p3 = doeOnt.indexOf('write 01_profile/analysis_plan.md');
check('idd.doe.ontology_first_gate', p1 > 0 && p2 > p1 && p3 > p2 && /HARD GATE/.test(doeOnt),
  `order prepare=${p1} brief=${p2} plan=${p3}`);
check('idd.doe.design_only_refused', /DESIGN_ONLY_NO_RESPONSE/.test(
  idd.buildOntologyDirective({ profile: 'doe', mode: 'auto', data_stage: 'design_only' })));
check('idd.quick_screen.html_step',
  /build_screen_report\.py/.test(idd.buildIntentDirective('quick-screen', 'x')));

let aws = null;
const awsIntentsPath = join(AWS_ROOT, '.AgentWorkShop/plugins/diag-bridge/host/intents.mjs');
if (existsSync(awsIntentsPath)) {
  const mod = await import(pathToFileURL(awsIntentsPath).href);
  const awsCatalog = mod.ANALYSIS_INTENTS;
  let aligned = 0;
  for (const [id, skill] of Object.entries(EXPECTED_SKILL)) {
    if (awsCatalog?.[id]?.skill === skill) aligned += 1;
  }
  check('aws.skill_alignment', aligned === Object.keys(EXPECTED_SKILL).length,
    `${aligned}/${Object.keys(EXPECTED_SKILL).length} skills differ`);
  check('aws.intent_resolution', mod.resolveBridgeIntent('doe-analysis') === 'doe-analysis'
    && mod.resolveBridgeIntent('nonsense') === null);
  const q = mod.defaultQuestionFor('doe-analysis', { line: 'bopet-lineA' });
  check('aws.doe_question_template', /DOE/.test(q) && !/根因诊断/.test(q), q.slice(0, 120));
  // The bridge builds a deep-diagnosis question whenever the caller omits one,
  // which makes the intent template above unreachable on that path.
  const pluginPath = join(AWS_ROOT, '.AgentWorkShop/plugins/diag-bridge/host/plugin.mjs');
  if (existsSync(pluginPath)) {
    const src = readFileSync(pluginPath, 'utf8');
    const block = src.slice(src.indexOf('if (!question)'), src.indexOf('if (!question)') + 700);
    const consultsIntent = /analysis_intent|defaultQuestionFor|intent/.test(block);
    if (!consultsIntent) {
      warnings.push({
        id: 'aws.diag_run_question_override',
        severity: 'P0-platform',
        detail: 'diag_run fills a deep-diagnosis question when question is absent; '
          + 'the per-intent template is unreachable on that path. IDD still binds the '
          + 'run through the intent directive, but the business question is wrong.',
      });
    }
  }
  aws = { root: AWS_ROOT, catalog: Object.keys(awsCatalog || {}) };
} else {
  warnings.push({ id: 'aws.absent', severity: 'info',
    detail: `AgentWorkShop not found at ${AWS_ROOT}; AWS half skipped` });
}

const passed = checks.filter((c) => c.ok).length;
const out = { passed, total: checks.length, checks, warnings, aws };
if (AS_JSON) console.log(JSON.stringify(out, null, 2));
else {
  console.log(`\n[routing] ${passed}/${checks.length} IDD checks passed`);
  for (const w of warnings) console.log(`[routing] ${w.severity}: ${w.id} — ${w.detail}`);
}
process.exit(checks.every((c) => c.ok) ? 0 : 1);
