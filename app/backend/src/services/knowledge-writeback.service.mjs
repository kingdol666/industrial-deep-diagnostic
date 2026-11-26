import { realpathSync, lstatSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT, WORKSPACE_DIR } from '../engine/claude-client.mjs';
import { isInside } from '../utils/pathGuard.mjs';
import { extractFindingsForRun } from '../../../../.claude/shared/scripts/line_memory.mjs';
import { recordCompletedEvidence } from './knowledge.service.mjs';

// Only deterministic local measurements are projected. Report conclusions,
// model-authored hypotheses and published material remain outside writeback.
const deterministicArtifact = {
  'quick-screen': ['sentinel', 'alert.json'],
  'stability-report': ['line_report', 'stability_report.json'],
};

export function recordRunLocalObservations(runId) {
  const run = stmts.getRunById.get(runId);
  const artifact = deterministicArtifact[run?.analysis_intent];
  if (!artifact || !run.line_id || !run.workspace_path || run.harness === 'mock') return 0;
  // Deliberately exclude runs with borrowed input until extraction can prove
  // per-observation lineage independently of a borrowed reference.
  const policy = JSON.parse(run.knowledge_policy_json || '{}');
  if (policy.references?.length || run.dataset_refs_json !== '[]') return 0;
  const root = realpathSync(WORKSPACE_DIR);
  const workspace = realpathSync(resolve(PROJECT_ROOT, run.workspace_path));
  if (!isInside(root, workspace)) return 0;
  let path = workspace;
  for (const part of artifact) {
    path = join(path, part);
    if (lstatSync(path).isSymbolicLink()) return 0;
  }
  const { findings } = extractFindingsForRun({ runDir: workspace, runId, intent: run.analysis_intent, observedAt: run.completed_at });
  return recordCompletedEvidence(runId, run.completion_revision, findings.filter((f) =>
    f.evidence_level === 'L3' && f.subject !== '__line__'));
}
