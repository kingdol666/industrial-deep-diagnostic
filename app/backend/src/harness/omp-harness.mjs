// OmpHarness — implements the Harness interface over the native OMP engine.
//
// Reads the OMP agent pipeline's filesystem contract under
// workspace/diagnostic-runs/: event log execution proof, optimizer verdict,
// enhancement status, reports and HTML. Read-only by design.

import { BaseHarness } from './base.mjs';
import {
  ompHealth,
  listOmpRuns,
  getOmpRun,
  getOmpArtifact,
  getOmpEnhancement,
  getOmpSummary,
} from '../services/omp.service.mjs';

export class OmpHarness extends BaseHarness {
  id = 'omp';
  name = 'OMP Engine';
  kind = 'runs';
  description = 'OMP 代理管线原生产物桥接（只读）';
  capabilities = ['runs', 'report', 'html', 'enhancement'];

  async health() {
    const h = ompHealth();
    return {
      available: h.available,
      meta: { runs_dir: h.runs_dir, run_count: h.run_count, engine: h.engine },
    };
  }

  async listRuns() {
    return listOmpRuns();
  }

  async getRun(name) {
    return getOmpRun(name);
  }

  async getArtifact(runId, kind) {
    return getOmpArtifact(runId, kind);
  }

  async getEnhancement(runId, kind) {
    return getOmpEnhancement(runId, kind);
  }

  async getHtml(runId, mode = 'baseline') {
    if (mode === 'enhanced') {
      return getOmpEnhancement(runId, 'html')?.content ?? null;
    }
    return getOmpArtifact(runId, 'html')?.content ?? null;
  }

  async getSummary(runId) {
    return getOmpSummary(runId);
  }
}
