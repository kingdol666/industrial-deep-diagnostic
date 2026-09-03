// OmpHarness — implements the Harness interface over the native OMP engine.
//
// Two halves:
// 1. LIVE — diagnoses and chats driven through the OMP harness contract:
//    the OMP agent definitions under .omp/agents/ are the only sub-agent
//    source (injected into the SDK agents option by engine/omp-engine.mjs).
// 2. RUNS — the OMP agent pipeline's filesystem contract under
//    workspace/diagnostic-runs/: event log execution proof, optimizer verdict,
//    enhancement status, reports and HTML.

import { BaseHarness } from './base.mjs';
import {
  ompHealth,
  listOmpRuns,
  getOmpRun,
  getOmpArtifact,
  getOmpEnhancement,
  getOmpSummary,
} from '../services/omp.service.mjs';
import { loadOmpAgents } from '../engine/omp-engine.mjs';

export class OmpHarness extends BaseHarness {
  id = 'omp';
  name = 'OMP Engine';
  kind = 'runs';
  description = 'OMP 代理管线引擎（.omp/agents 契约实时驱动 + 运行产物桥接）';
  capabilities = ['runs', 'report', 'html', 'enhancement', 'live', 'chat'];

  async health() {
    const h = ompHealth();
    const { count } = loadOmpAgents();
    return {
      available: h.available,
      meta: {
        runs_dir: h.runs_dir,
        run_count: h.run_count,
        engine: h.engine,
        agent_contracts: count,
        note: count > 0
          ? `OMP harness ready — ${count} agent contracts loaded from .omp/agents`
          : '未找到 .omp/agents 契约 — 实时诊断将回退为直接执行',
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
