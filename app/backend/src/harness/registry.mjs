// Harness Registry — the single source of truth for available engines.
//
// 14 engines from the multi-harness architecture (mock/claude/omp resident
// trio + the 11 CLI adapters) are registered here. Adding a new harness:
//   1. implement the engine client (engine/<name>-client.mjs or a spec in
//      oneshot-specs.mjs / acp-client.mjs)
//   2. add a definition to HARNESS_DEFS in engines.mjs (if not present)
//   3. the REST layer and the frontend pick it up automatically

import { BaseHarness, HarnessNotFoundError } from './base.mjs';
import { OmpHarness } from './omp-harness.mjs';
import { ClaudeHarness } from './claude-harness.mjs';
import { HARNESS_DEFS, createLiveHarness } from './engines.mjs';

/** Ordered list — display/preference order; the RUNTIME default harness is
 *  resolved separately from availability (config harness.default → chain, see
 *  engines.mjs resolveBestAvailableHarness). */
const harnesses = [new ClaudeHarness(), new OmpHarness()];

// The 12 definition-table engines (mock + 11 CLI adapters), in table order.
for (const def of HARNESS_DEFS) {
  harnesses.push(createLiveHarness(def));
}

// Optional reference implementation (capability-driven UI proof) —
// enabled explicitly via IDD_DEMO_HARNESS=1, never on in production runs.
if (process.env.IDD_DEMO_HARNESS === '1') {
  const { DemoHarness } = await import('./demo-harness.mjs');
  harnesses.push(new DemoHarness());
}

/** All registered harness manifests (public metadata). */
export function listHarnesses() {
  return harnesses.map((h) => h.manifest());
}

/** Look up a harness by id; throws HarnessNotFoundError when absent. */
export function getHarness(id) {
  const h = harnesses.find((x) => x.id === id);
  if (!h) throw new HarnessNotFoundError(id);
  return h;
}

/** Membership check without throwing (normalize / validation fast path). */
export function hasHarness(id) {
  return typeof id === 'string' && harnesses.some((x) => x.id === id);
}

/** All known harness ids, registry order (first = default). */
export function listHarnessIds() {
  return harnesses.map((h) => h.id);
}

/** Instantiate an unregistered harness (for tests / plugins). */
export function registerHarness(harness) {
  if (!(harness instanceof BaseHarness)) {
    throw new TypeError('registerHarness expects a BaseHarness subclass instance');
  }
  harnesses.push(harness);
  return harness;
}

export { BaseHarness, HarnessNotFoundError };
