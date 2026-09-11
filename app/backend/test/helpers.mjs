// Test helpers — CLI shims + query draining for the multi-harness test suite.
import { chmodSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';

const escape = (p) => p.replace(/\\/g, '\\\\');

/**
 * Create an executable shim that runs `node <fixtureScript> <fixtureArg> %*`
 * and return its absolute path. Windows npm-style: a .cmd wrapper (exercises
 * the cmd.exe /d /s /c spawn path in cli-common).
 */
export function makeCliShim(fixtureScript, fixtureArg, { name, dir = join(tmpdir(), `idd-harness-test`) } = {}) {
  mkdirSync(dir, { recursive: true });
  const scriptPath = fixtureScript.replace(/\\/g, '/');
  if (process.platform === 'win32') {
    const file = join(dir, `${name}.cmd`);
    // %~dp0-free: absolute script path; node resolves forward slashes fine.
    writeFileSync(file, `@node "${scriptPath}" ${fixtureArg} %*\r\n`, 'utf-8');
    return file;
  }
  const file = join(dir, name);
  writeFileSync(file, `#!/bin/sh\nexec node "${scriptPath}" ${fixtureArg} "$@"\n`, 'utf-8');
  try { chmodSync(file, 0o755); } catch { /* ignore */ }
  return file;
}

/** Collect every standardized message a query emits until it closes. */
export async function drain(query, { timeoutMs = 15000 } = {}) {
  const events = [];
  const deadline = Date.now() + timeoutMs;
  try {
    for await (const msg of query) {
      events.push(msg);
      if (Date.now() > deadline) {
        throw new Error(`drain timeout — ${events.length} events collected`);
      }
    }
  } finally {
    try { query.close(); } catch { /* already closed */ }
  }
  return events;
}

export function findEvent(events, type, predicate = () => true) {
  return events.find((e) => e.type === type && predicate(e));
}

/** Engines re-emit init when the engine-side session id lands — take the last. */
export function lastInit(events) {
  const inits = events.filter((e) => e.type === 'system' && e.subtype === 'init');
  return inits[inits.length - 1] || null;
}

export function findResult(events) {
  return events.find((e) => e.type === 'result');
}

export const commandEnvKey = (id) => `HARNESS_${id.toUpperCase()}_COMMAND`;
