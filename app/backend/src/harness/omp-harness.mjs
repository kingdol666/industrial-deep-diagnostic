// OmpHarness — implements the Harness interface over the native OMP engine.
//
// Live execution: diagnosis runs and chats are dispatched to `omp --mode=rpc`
// by engine dispatch in diagnosis.service / chat.service. This harness also
// browses the OMP pipeline's filesystem contract under workspace/diagnostic-runs/
// (event log execution proof, optimizer verdict, enhancement status, reports, HTML).

import { BaseHarness } from './base.mjs';
import {
  ompHealth,
  listOmpRuns,
  getOmpRun,
  getOmpArtifact,
  getOmpEnhancement,
  getOmpSummary,
} from '../services/omp.service.mjs';
import { probeOmpEngine } from '../engine/omp-client.mjs';

export class OmpHarness extends BaseHarness {
  id = 'omp';
  name = 'OMP Engine';
  kind = 'runs';
  description = 'OMP 代理管线原生引擎（RPC 实时执行 + 运行浏览）';
  capabilities = ['live', 'runs', 'report', 'html', 'enhancement'];

  async health() {
    const [h, engine] = await Promise.all([
      Promise.resolve(ompHealth()),
      probeOmpEngine(),
    ]);
    return {
      // Available only when the omp binary actually executes (--version probe).
      available: engine.available,
      meta: {
        runs_dir: h.runs_dir,
        run_count: h.run_count,
        engine: h.engine,
        omp_binary: engine.binary,
        omp_version: engine.version || null,
        omp_probe_error: engine.error || null,
      },
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
