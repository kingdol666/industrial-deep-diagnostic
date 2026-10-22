#!/usr/bin/env node
// Intent prompt-injection contract (plan v2, acceptance S-prompt).
//
// Verifies against the REAL backend code path (buildIntentDirective) that:
//   * deep-diagnosis injects nothing (the 9-stage prompt stays untouched);
//   * every specialist intent injects its own skill + run constraints;
//   * stability-report carries its folder preprocess step, quick-screen its
//     HTML step, and neither leaks the other's step;
//   * two different intents produce different directives.
//
// Usage: node scripts/e2e/intent-prompt-contract.mjs
import { pathToFileURL } from 'node:url';

const clientPath = pathToFileURL(
  new URL('../../app/backend/src/engine/claude-client.mjs', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'),
).href;
const m = await import(clientPath);

const intents = ['deep-diagnosis', 'stability-report', 'quick-screen', 'doe-analysis', 'experience-mining', 'optimizer-campaign'];
let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 160)}` : ''}`);
  if (!ok) failures += 1;
};

for (const intent of intents) {
  const directive = m.buildIntentDirective(intent, 'sceneA');
  const skill = m.ANALYSIS_INTENTS[intent]?.skill || null;
  if (intent === 'deep-diagnosis') {
    check('默认模式不注入意图指令', directive === '', JSON.stringify(directive).slice(0, 40));
    continue;
  }
  const flags = {
    intent: directive.includes(`ANALYSIS_INTENT: ${intent}`),
    skill: skill ? directive.includes(`Executing skill: ${skill}`) : false,
    setup: directive.includes('setup.mjs'),
    report: directive.includes('report.md'),
    preprocess: directive.includes('data_preprocessor.py'),
    htmlStep: directive.includes('build_screen_report.py'),
  };
  console.log(`${intent}: ${JSON.stringify(flags)} len=${directive.length}`);
  check(`${intent} 注入自己的技能与运行约束`,
    flags.intent && flags.skill && flags.setup && flags.report);
  if (intent === 'stability-report') check('stability 模式注入 preprocessStep', flags.preprocess && !flags.htmlStep);
  if (intent === 'quick-screen') check('quick-screen 模式注入 htmlStep', flags.htmlStep && !flags.preprocess);
  if (intent === 'doe-analysis') check('doe 模式不误注入 preprocess/html', !flags.preprocess && !flags.htmlStep);
}

const stability = m.buildIntentDirective('stability-report', 'sceneA');
const quickScreen = m.buildIntentDirective('quick-screen', 'sceneA');
check('不同模式指令内容确实不同',
  stability !== quickScreen
  && stability.includes('ANALYSIS_INTENT: stability-report')
  && stability.includes('data_preprocessor.py')
  && !stability.includes('build_screen_report.py')
  && quickScreen.includes('ANALYSIS_INTENT: quick-screen')
  && quickScreen.includes('build_screen_report.py')
  && !quickScreen.includes('data_preprocessor.py'));

// ── codex / opencode prompt builders ──────────────────────────────────────
// These two engines used to ignore `analysisIntent` entirely: a specialist
// request ran the generic 9-stage protocol. Assert the REAL builders now carry
// the directive and re-point the skill reference.
const codexPath = pathToFileURL(
  new URL('../../app/backend/src/engine/codex-client.mjs', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'),
).href;
const opencodePath = pathToFileURL(
  new URL('../../app/backend/src/engine/opencode-client.mjs', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'),
).href;
const codex = await import(codexPath);
const opencode = await import(opencodePath);

const built = (builder) => builder({
  analysisTarget: { mode: 'file', dataPath: 'app/backend/package.json' },
  userQuestion: 'contract probe',
  sceneName: 'sceneA',
  reportLanguage: 'zh',
  followUpMessage: null,
  ontology: null,
  enhancement: null,
});

for (const [label, builder] of [['codex', codex.buildCodexPrompt], ['opencode', opencode.buildOpenCodePrompt]]) {
  for (const intent of intents) {
    if (intent === 'deep-diagnosis') {
      const prompt = built((args) => builder({ ...args, analysisIntent: intent })).prompt;
      check(`${label}/deep-diagnosis 不注入意图指令`, !prompt.includes('ANALYSIS_INTENT:'));
      continue;
    }
    const spec = m.ANALYSIS_INTENTS[intent];
    const prompt = built((args) => builder({ ...args, analysisIntent: intent })).prompt;
    const ok = prompt.includes(`ANALYSIS_INTENT: ${intent}`)
      && prompt.includes(`Executing skill: ${spec.skill}`)
      && prompt.includes(`.claude/skills/${spec.skill}/SKILL.md`)
      && prompt.includes('setup.mjs')
      && prompt.includes('report.md');
    check(`${label}/${intent} prompt 注入意图 + 技能重定向`, ok, prompt.length);
  }
}
const stabCodex = built((args) => codex.buildCodexPrompt({ ...args, analysisIntent: 'stability-report' })).prompt;
check('codex/stability 携带 preprocessStep', stabCodex.includes('data_preprocessor.py') && !stabCodex.includes('build_screen_report.py'));

console.log(`\n[RESULT] failures=${failures}`);
process.exit(failures ? 1 : 0);
