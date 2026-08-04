// Harness Interface — the unified contract every analysis engine implements.
//
// A "harness" is an execution engine that runs diagnostic analyses. The web
// console talks to engines ONLY through this interface, so adding a new
// engine (Codex, OpenCode, a remote cluster, ...) means implementing this
// contract and registering it in registry.mjs — no frontend changes needed.
//
// ── Contract ─────────────────────────────────────────────────────────
//   id            string   unique engine id (used in /api/harness/:id/*)
//   name          string   display name
//   kind          string   'live' | 'runs' | 'hybrid' — capability class
//   description   string   one-line human description
//   capabilities  string[] feature flags, any of:
//                    'live'      — can START a diagnosis (real-time engine)
//                    'runs'      — exposes completed run listings
//                    'report'    — can serve report.md content
//                    'html'      — can serve diagnostic HTML for iframe
//                    'enhancement'— can serve E1-E8 enhancement artifacts
//                    'chat'      — can resume conversations
//   health()        → Promise<{ available: boolean, meta: object }>
//   listRuns()      → Promise<RunSummary[]>   (requires 'runs')
//   getRun(id)      → Promise<RunDetail|null> (requires 'runs')
//   getArtifact(runId, kind) → Promise<Artifact|null>   (requires 'report')
//   getEnhancement(runId, kind) → Promise<Artifact|null> (requires 'enhancement')
//   getHtml(runId, mode) → Promise<string|null>          (requires 'html')
//   startDiagnosis(params) → Promise<object>  (requires 'live') — may throw
//                                                NotImplemented when absent
//
// RunSummary  { name, display_name, created, status, verdict, flags... }
// RunDetail   { name, display_name, manifest, baseline, enhancement,
//               artifacts, events }
// Artifact    { kind, path, size, content }
//
// Engines are READ-ONLY for run browsing: getArtifact/getHtml never mutate
// engine-owned data. Live engines additionally write their own run state.

/**
 * Base class with safe defaults — subclasses override what they support.
 * Unsupported operations throw HarnessNotSupportedError.
 */
export class HarnessNotSupportedError extends Error {
  constructor(message = 'Operation not supported by this harness') {
    super(message);
    this.code = 'HARNESS_NOT_SUPPORTED';
  }
}

export class HarnessNotFoundError extends Error {
  constructor(id) {
    super(`Harness not found: ${id}`);
    this.code = 'HARNESS_NOT_FOUND';
  }
}

export class BaseHarness {
  /** @type {string} unique id */
  id = 'base';
  /** @type {string} display name */
  name = 'Base Harness';
  /** @type {'live'|'runs'|'hybrid'} */
  kind = 'runs';
  /** @type {string} one-liner */
  description = '';
  /** @type {string[]} feature flags */
  capabilities = [];

  constructor() {
    if (new.target === BaseHarness) {
      throw new Error('BaseHarness is abstract — implement a concrete harness');
    }
  }

  supports(flag) {
    return this.capabilities.includes(flag);
  }

  async health() {
    return { available: false, meta: {} };
  }

  async listRuns() {
    throw new HarnessNotSupportedError(`${this.id} does not list runs`);
  }

  async getRun() {
    throw new HarnessNotSupportedError(`${this.id} does not expose run details`);
  }

  async getArtifact() {
    throw new HarnessNotSupportedError(`${this.id} does not serve artifacts`);
  }

  async getEnhancement() {
    throw new HarnessNotSupportedError(`${this.id} does not serve enhancement artifacts`);
  }

  async getHtml() {
    throw new HarnessNotSupportedError(`${this.id} does not serve HTML`);
  }

  async startDiagnosis() {
    throw new HarnessNotSupportedError(`${this.id} cannot start diagnoses (use a live harness)`);
  }

  /** Public manifest — what the registry/frontend sees about this engine. */
  manifest() {
    return {
      id: this.id,
      name: this.name,
      kind: this.kind,
      description: this.description,
      capabilities: this.capabilities,
    };
  }
}
