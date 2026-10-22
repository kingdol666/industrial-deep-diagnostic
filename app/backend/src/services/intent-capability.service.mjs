// Intent × harness capability matrix — engine capability as DATA, not a guess.
//
// Every live engine currently executes every analysis intent through the same
// directive contract (buildIntentDirective + intent-specific skill reference).
// A future engine may declare `intents: ['deep-diagnosis']` in HARNESS_DEFS;
// this module is the ONE place that decides supported combinations, so both the
// UI and the external API answer from the same table.
import { HARNESS_DEFS } from '../harness/engines.mjs';
import { ANALYSIS_INTENTS } from '../engine/claude-client.mjs';

const ALL_INTENTS = Object.freeze(Object.keys(ANALYSIS_INTENTS));

/**
 * Intents a harness can execute. `intents: null` (the default for every current
 * engine) means "all registered intents". An engine id absent from the table is
 * a dedicated harness (claude/omp), whose existence is validated elsewhere —
 * it is treated as unrestricted, never as silently unsupported.
 */
export function supportedIntentsFor(harnessId, defs = HARNESS_DEFS) {
  const id = String(harnessId || '').trim().toLowerCase();
  const def = defs.find((d) => d.id === id);
  if (!def) return [...ALL_INTENTS];
  return Array.isArray(def.intents) ? [...def.intents] : [...ALL_INTENTS];
}

export function isIntentSupported(harnessId, intent, defs = HARNESS_DEFS) {
  return supportedIntentsFor(harnessId, defs).includes(String(intent));
}

/** Hard 400 for an explicitly unsupported combination (never a silent fallback). */
export function assertIntentSupportedOnHarness(intent, harnessId, defs = HARNESS_DEFS) {
  const supported = supportedIntentsFor(harnessId, defs);
  if (supported.includes(String(intent))) return;
  const err = new Error(
    `analysisIntent "${intent}" is not supported on harness "${harnessId}" `
    + `(supported on this harness: ${supported.join(', ') || 'none'}). `
    + 'Pick a supported intent or a harness that declares it.',
  );
  err.status = 400;
  err.code = 'INTENT_UNSUPPORTED_ON_HARNESS';
  err.harness = harnessId;
  err.intent = String(intent);
  err.supported = supported;
  throw err;
}

export { ALL_INTENTS };
