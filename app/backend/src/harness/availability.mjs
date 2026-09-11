// Harness Availability — 执行前强校验 (多 Harness 架构 · 原则 7).
//
// Three-state assertion used by every entry point that starts work on an
// engine (run create / execute / continue):
//   unknown harness  → 400 HARNESS_UNKNOWN
//   not installed    → 409 HARNESS_UNAVAILABLE (with resolved command hint)
//   installed        → health details
//
// Probes share the binary resolution of the real spawn (探测与拉起同源) and
// are cached for the 12 definition-table engines (default 30s); claude/omp
// use their own harness health implementations.

import { hasHarness, getHarness, listHarnessIds } from './registry.mjs';

export class HarnessUnknownError extends Error {
  constructor(id) {
    super(`Unknown harness: "${typeof id === 'string' ? id.trim() : String(id)}". Registered harnesses: ${listHarnessIds().join(', ')}`);
    this.code = 'HARNESS_UNKNOWN';
    this.status = 400;
  }
}

export class HarnessUnavailableError extends Error {
  constructor(id, reason) {
    super(
      `Harness "${id}" is not usable: ${reason}`
      + `. Install the engine CLI, or override the command via config harness.engines.${id}.binary / env HARNESS_${String(id).toUpperCase()}_COMMAND.`,
    );
    this.code = 'HARNESS_UNAVAILABLE';
    this.status = 409;
  }
}

/**
 * Assert a harness can start work right now. Returns the health payload.
 * Throws HarnessUnknownError (400) / HarnessUnavailableError (409).
 */
export async function assertHarnessUsable(id) {
  const normalized = typeof id === 'string' ? id.trim().toLowerCase() : '';
  if (!normalized) {
    throw new HarnessUnknownError(id);
  }
  if (!hasHarness(normalized)) {
    throw new HarnessUnknownError(id);
  }
  const health = await getHarness(normalized).health();
  if (!health?.available) {
    const meta = health?.meta || {};
    const reason = meta.probe_error || meta.omp_probe_error || meta.note
      || (meta.binary ? `binary "${meta.binary}" failed its version probe` : 'availability probe failed');
    throw new HarnessUnavailableError(normalized, reason);
  }
  return health;
}
