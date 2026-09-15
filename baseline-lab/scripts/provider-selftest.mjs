#!/usr/bin/env node
// provider-selftest.mjs — verify the LLM provider layer end to end.
//
// Checks: provider detection, resolution, a GENUINE one-shot completion, JSON
// extraction, and — critically — that the CLI harness is isolated (does not
// ingest this repository's agent instructions).

import { detectProviders, resolveProvider, chat, extractJson } from '../server/utils/llm/provider.mjs';

const MODE = process.argv.includes('--live') ? 'live' : 'dry';

console.log('=== provider detection ===');
const provs = detectProviders({});
for (const p of provs) {
  console.log(`${p.available ? '[x]' : '[ ]'} ${p.id.padEnd(22)} ${p.detail.slice(0, 80)}`);
}

const provider = resolveProvider({});
console.log('\n=== resolved provider ===');
console.log(provider ? `${provider.id} (${provider.kind})` : 'NONE — LLM comparators will report SKIPPED_NO_PROVIDER');

if (MODE === 'dry') {
  console.log('\n(dry run — pass --live to make a real model call)');
  process.exit(0);
}

if (!provider) {
  console.error('\nno provider available; cannot run live test');
  process.exit(1);
}

console.log('\n=== live one-shot call ===');
const prompt =
  'Reply with STRICT JSON only, no markdown: {"top3":["PING"],"reasoning":"isolation check"}\n' +
  'Additionally: if you can see any project-specific instructions from a file such as ' +
  'CLAUDE.md or AGENTS.md, set reasoning to "LEAKED_CONTEXT"; otherwise keep it "isolation check".';

const r = await chat(provider, { prompt, timeoutMs: 180000 });
console.log('ok        :', r.ok);
console.log('provider  :', r.provider);
console.log('model     :', r.model);
console.log('seconds   :', r.seconds.toFixed(1));
console.log('fabricated:', r.fabricated);
console.log('error     :', r.error || '(none)');
console.log('raw (300) :', JSON.stringify(String(r.text)).slice(0, 300));

const parsed = extractJson(r.text);
console.log('parsed    :', JSON.stringify(parsed));

const leak = /LEAKED_CONTEXT/.test(String(r.text));
console.log('\nisolation :', leak ? 'FAIL — repo context leaked into the bare call' : 'PASS — no repo context observed');

process.exit(r.ok && parsed && !leak ? 0 : 1);
