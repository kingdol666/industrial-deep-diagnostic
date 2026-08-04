// DemoHarness — a minimal reference implementation used to prove the
// capability-driven UI. It exposes ONLY ['runs', 'report'] (no html, no
// enhancement) — exactly what a Codex/OpenCode-style engine might start
// with. Enabled via IDD_DEMO_HARNESS=1 so production runs stay clean.
//
// This file doubles as the onboarding example: copy it, swap the data
// source, register it — done.

import { BaseHarness } from './base.mjs';
import { listOmpRuns, getOmpRun, getOmpArtifact } from '../services/omp.service.mjs';

export class DemoHarness extends BaseHarness {
  id = 'demo';
  name = 'Demo Engine';
  kind = 'runs';
  description = '最小能力参考实现（runs + report，无 html/enhancement）';
  capabilities = ['runs', 'report'];

  async health() {
    const { ompHealth } = await import('../services/omp.service.mjs');
    const h = ompHealth();
    return {
      available: h.available,
      meta: { runs_dir: h.runs_dir, run_count: h.run_count, engine: 'demo' },
    };
  }

  async listRuns() {
    return listOmpRuns();
  }

  async getRun(name) {
    return getOmpRun(name);
  }

  async getArtifact(runId, kind) {
    // demo serves only the two kinds it declares
    if (!['report', 'optimizer'].includes(kind)) return null;
    return getOmpArtifact(runId, kind);
  }

  // getEnhancement / getHtml intentionally NOT overridden → BaseHarness
  // throws HarnessNotSupportedError → REST returns 400 → UI shows the
  // capability hint instead of the tab.
}
