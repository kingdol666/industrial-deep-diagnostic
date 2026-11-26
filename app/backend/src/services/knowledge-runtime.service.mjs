import { randomUUID } from 'node:crypto';
import { db } from '../db/database.mjs';
import { requireLineAction, requireRunKnowledgeScope } from './production-line.service.mjs';
import { getPublishedVersion, stageComparisonDataset } from './knowledge-publication.service.mjs';
import { getForRun, searchForRun } from './knowledge.service.mjs';

const actorById = db.prepare('SELECT id, username, role FROM users WHERE id = ?');
const fail = (code, message, status = 409) => Object.assign(new Error(message), { status, code });

// Harnesses fed through the ephemeral loopback MCP broker (same policy layer
// as the Claude in-process tools). OMP additionally verifies the resolved
// provider/model/tool registration in its startup handshake before prompting.
const remoteTransports = new Set(['codex', 'opencode', 'omp']);
export const supportsMemoryTools = (harness) => harness === 'claude' || remoteTransports.has(harness);

export function assertKnowledgeHarness(harness, policy) {
  if (policy?.mode === 'on_demand' && !supportsMemoryTools(harness)) {
    throw fail('KNOWLEDGE_UNAVAILABLE_ON_HARNESS', '该引擎未配置按需记忆适配器；请选择支持的引擎或明确关闭记忆');
  }
}

export function validateKnowledgeSelection(actor, lineId, policy, datasets = []) {
  for (const ref of policy?.references ?? []) {
    try {
      const version = getPublishedVersion(actor, ref, 'reuse');
      if (version.kind === 'dataset') throw fail('KNOWLEDGE_SOURCE_UNAVAILABLE', '所选知识版本不可用');
    } catch (err) {
      if (!err.status || err.status >= 500) throw err;
      throw fail('KNOWLEDGE_SOURCE_UNAVAILABLE', '所选知识版本不可用或已撤权');
    }
  }
  for (const ref of datasets) {
    try { stageComparisonDataset({ actor, line_id: lineId }, ref); } catch (err) {
      if (!err.status || err.status >= 500) throw err;
      throw fail('KNOWLEDGE_SOURCE_UNAVAILABLE', '所选对照数据版本不可用或已撤权');
    }
  }
}

// Tool registration does not establish filesystem, environment or network isolation.
// Until an isolated execution adapter is verified, cross-line execution stays closed.
export function assertKnowledgeExecutionPolicy(policy, datasets, { resuming = false } = {}) {
  if (datasets?.length || policy?.references?.length) {
    throw fail('KNOWLEDGE_ISOLATION_REQUIRED', '跨线共享执行尚未通过引擎隔离验收；可在授权范围内预览，不会把共享内容发送给模型');
  }
  if (policy?.mode !== 'on_demand') return false;
  if (resuming) throw fail('KNOWLEDGE_RESUME_UNSUPPORTED', '此按需记忆作业不支持恢复旧模型会话，请新建作业');
  if (process.env.IDD_TRUSTED_KNOWLEDGE_RUNTIME !== '1') {
    throw fail('KNOWLEDGE_ISOLATION_REQUIRED', '按需记忆引擎只在明确配置的受信开发环境启用；请选择关闭记忆');
  }
  return true;
}

export function preflightKnowledgeRun(run, { resuming = false } = {}) {
  if (!run.line_id) return null;
  const actor = run.owner_user_id && actorById.get(run.owner_user_id);
  if (!actor || String(actor.id) !== run.user_id) throw fail('RUN_NOT_FOUND', '作业归属无法核验', 404);
  requireLineAction(actor, run.line_id, 'run');
  const scope = requireRunKnowledgeScope(actor, run.run_id);
  const policy = scope.knowledge_policy;
  const datasets = scope.dataset_refs ?? [];
  assertKnowledgeHarness(run.harness, policy);
  validateKnowledgeSelection(actor, run.line_id, policy, datasets);
  return assertKnowledgeExecutionPolicy(policy, datasets, { resuming }) ? actor : null;
}

function bindHandlers(run, actor, active) {
  const attempt_id = randomUUID();
  const scope = () => {
    if (!active()) throw fail('KNOWLEDGE_ITEM_NOT_FOUND', '执行尝试已结束', 404);
    const current = actorById.get(actor.id);
    if (!current) throw fail('RUN_NOT_FOUND', '作业不存在或不可用', 404);
    return { actor: current, run_id: run.run_id, attempt_id };
  };
  return {
    search: (input) => searchForRun(scope(), input),
    get: (ref) => getForRun(scope(), ref),
  };
}

export async function bindKnowledgeTools(run, actor, active) {
  if (!actor) return null;
  const { createMemoryToolServer } = await import('../engine/memory-tools.mjs');
  return createMemoryToolServer(bindHandlers(run, actor, active));
}

export async function bindKnowledgeTransport(run, actor, active) {
  if (!actor || !remoteTransports.has(run.harness)) return null;
  const { openMemoryHttp } = await import('../engine/memory-http.mjs');
  return openMemoryHttp(bindHandlers(run, actor, active));
}
