// Harness Registry — the single source of truth for available engines.
//
// To add a new harness (Codex, OpenCode, a remote runner, ...):
//   1. implement app/backend/src/harness/<name>-harness.mjs (see base.mjs)
//   2. register an instance below
//   3. the REST layer and the frontend pick it up automatically
//
// The registry is intentionally tiny: discovery, lookup, enumeration.

import { BaseHarness, HarnessNotFoundError } from './base.mjs';
import { OmpHarness } from './omp-harness.mjs';
import { ClaudeHarness } from './claude-harness.mjs';

/** Ordered list — first entry is the default engine for the console. */
const harnesses = [new ClaudeHarness(), new OmpHarness()];

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

/** Instantiate an unregistered harness (for tests / plugins). */
export function registerHarness(harness) {
  if (!(harness instanceof BaseHarness)) {
    throw new TypeError('registerHarness expects a BaseHarness subclass instance');
  }
  harnesses.push(harness);
  return harness;
}

export { BaseHarness, HarnessNotFoundError };
