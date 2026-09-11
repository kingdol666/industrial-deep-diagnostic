// Codex Client — OpenAI Codex CLI via `codex app-server` (stdio NDJSON
// JSON-RPC v2). 协议: thread/start 建会话 → turn/start 驱动回合; 审批经
// server→client request (requestApproval, decision: accept/decline);
// item/turn notifications 映射为标准事件。方法名漂移时只改 METHOD 表。

import { spawnCli, killTree, stderrTailRef } from './cli-common.mjs';
import { createStdioJsonRpc } from './stdio-jsonrpc.mjs';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import {
  resolveAnalysisTarget, buildRuntimeProtocol,
  buildPrompt as buildDataPrompt,
  buildOntologyDirective, buildEnhancementDirective,
} from './claude-client.mjs';
import { existsSync } from 'fs';
import { join } from 'path';

// ── Notification / item mappers (exported for tests) ──
export function mapCodexItem(item, ctx) {
  if (!item || typeof item !== 'object') return;
  const type = item.type || item.itemType || '';
  switch (type) {
    case 'agentMessage':
    case 'agent_message':
    case 'message': {
      const text = item.text || item.content || '';
      if (text) ctx.assistant([{ type: 'text', text: String(text) }]);
      break;
    }
    case 'reasoning':
    case 'agent_reasoning': {
      const text = item.text || item.summary || '';
      if (text) ctx.assistant([{ type: 'thinking', thinking: String(text) }]);
      break;
    }
    case 'commandExecution':
    case 'fileChange':
    case 'mcpToolCall':
    case 'tool_call': {
      ctx.toolUse({
        id: item.id || item.call_id,
        name: item.command || item.tool || type,
        input: item.aggregatedOutput ? { output: item.aggregatedOutput } : (item.input || {}),
      });
      break;
    }
    default:
      ctx.unknown(type || 'item');
  }
}

export function mapCodexNotification(method, params, ctx) {
  const m = String(method || '');
  const p = params || {};
  if (/^item\/(started|completed|updated)$/.test(m)) {
    mapCodexItem(p.item || p, ctx);
    return;
  }
  if (m === 'turn/completed' || m === 'task/complete' || m === 'thread/completed') {
    ctx.result('success', 'success');
    return;
  }
  if (m === 'error' || m === 'turn/failed' || m === 'task/failed') {
    ctx.result('error_during_execution', p.message || p.error?.message || 'codex_error');
    return;
  }
  // token_count / thread/started / … — tolerated, ignored
  ctx.unknown(m || 'notification');
}

// ── Query wrapper ──
function createCodexQuery({ turnKey, prompt }) {
  const engCfg = config.harness?.engines?.codex || {};
  const queue = [];
  let wake = null;
  let closed = false;
  let threadId = null;
  let numTurns = 0;
  let startedAt = Date.now();
  let finished = false;
  const state = { proc: null };

  const push = (msg) => {
    queue.push(msg);
    if (msg?.type === 'assistant') numTurns += 1;
    if (wake) { wake(); wake = null; }
  };
  const end = () => { closed = true; if (wake) { wake(); wake = null; } };
  const emit = (msg) => push(msg);
  const result = (subtype, stopReason) => {
    if (finished) return;
    finished = true;
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: numTurns,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: threadId ? `codex:${threadId}` : `codex:run:${turnKey}`,
    });
    end();
    // 回合终点 = 进程终点（延迟自杀，避免僵尸 app-server 进程）。
    setTimeout(() => killTree(proc), 250);
  };

  const ctx = {
    assistant: (content) => emit({ type: 'assistant', message: { role: 'assistant', content } }),
    toolUse: (tool) => ctx.assistant([{ type: 'tool_use', id: tool.id || 'tool', name: tool.name || 'tool', input: tool.input || {} }]),
    result: (subtype, stop) => result(subtype, stop),
    unknown: () => {},
  };

  const proc = spawnCli('codex', engCfg.server_args || ['app-server'], { cwd: PROJECT_ROOT });
  state.proc = proc;
  const getStderrTail = stderrTailRef(proc);

  proc.on('exit', (code) => {
    if (!finished) {
      const tail = getStderrTail().split(/\r?\n/).filter(Boolean).slice(-3).join(' | ');
      result('error_during_execution', `CODEX_EXIT_${code ?? 'null'}${tail ? `: ${tail.slice(0, 300)}` : ''}`);
    }
  });

  const rpc = createStdioJsonRpc(proc, {
    label: 'codex:app-server',
    requestTimeoutMs: 30000,
    onRequest: async (method) => {
      if (/approval/i.test(method)) {
        const autoApprove = engCfg.auto_approve !== false;
        logger.info(`[codex] ${method} → ${autoApprove ? 'accept (auto_approve)' : 'decline (fail-closed)'}`, { context: 'Codex', turnKey });
        emit({ type: 'system', subtype: 'permission_request', data: { engine: 'codex', method, autoApprove } });
        return { decision: autoApprove ? 'accept' : 'decline' };
      }
      emit({ type: 'system', subtype: 'server_request', data: { engine: 'codex', method } });
      return {};
    },
    onNotification: (n) => mapCodexNotification(n.method, n.params, ctx),
  });

  (async () => {
    try {
      // initialize (best-effort — older app-servers may not require it)
      await rpc.request('initialize', {
        clientInfo: { name: 'industrial-deep-diagnostic', title: 'IDD Console', version: '1.0.0' },
      }, { timeoutMs: 20000 }).catch((e) => {
        logger.warn(`[codex] initialize not accepted (continuing): ${e.message}`, { context: 'Codex', turnKey });
        return null;
      });

      const thread = await rpc.request('thread/start', {
        cwd: PROJECT_ROOT,
        model: engCfg.model || undefined,
        approvalPolicy: engCfg.approval_policy || 'on-request',
      }, { timeoutMs: 30000 });
      threadId = thread?.threadId || thread?.thread_id || thread?.id || null;

      emit({ type: 'system', subtype: 'session_ready', data: { engine: 'codex', threadId } });

      await rpc.request('turn/start', {
        threadId,
        input: [{ type: 'text', text: prompt }],
        items: [{ type: 'text', text: prompt }],
      }, { timeoutMs: 0 })
        .then(() => result('success', 'success'))
        .catch((e) => result('error_during_execution', `codex_turn_failed: ${e.message}`));
    } catch (e) {
      logger.error(`[codex] session setup failed: ${e.message}`, { context: 'Codex', turnKey });
      result('error_during_execution', `codex_session_failed: ${e.message}`);
    }
  })();

  return {
    engine: 'codex',
    sessionId: `codex:run:${turnKey || Date.now()}`,
    close() {
      killTree(state.proc);
      closed = true;
      if (wake) { wake(); wake = null; }
    },
    get killed() {
      const p = state.proc;
      return p ? (p.killed || p.exitCode !== null) : false;
    },
    async *[Symbol.asyncIterator]() {
      while (true) {
        if (queue.length > 0) {
          yield queue.shift();
          continue;
        }
        if (closed) return;
        await new Promise((resolve) => { wake = resolve; });
      }
    },
  };
}

// ── Shared prompt assembly ──
function buildCodexPrompt({ analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement }) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const { dataPaths, promptTarget } = resolveAnalysisTarget(analysisTarget);
  const skillMd = join(PROJECT_ROOT, config.claude.skill_dir || '.claude/skills/industrial-analysis-auto', 'SKILL.md');
  const skillRef = existsSync(skillMd)
    ? `First read the authoritative skill definition at ${skillMd} and follow its full pipeline contract as binding.`
    : 'Follow the industrial deep diagnostic skill protocol (industrial-analysis-auto).';
  const prompt = `${buildRuntimeProtocol(sceneName, lang)}

${skillRef}

${buildDataPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)}${buildOntologyDirective(ontology)}${buildEnhancementDirective(enhancement)}`;
  return { dataPaths, prompt };
}

// ── Standard engine client module shape ──
const activeQueries = new Map();

export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
  ontology = null, enhancement = null,
}) {
  void maxTurns; void timeoutMinutes; void sessionId; // codex threads don't resume cross-process here
  const built = buildCodexPrompt({
    analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement,
  });
  const query = createCodexQuery({ turnKey: runId, prompt: built.prompt });
  activeQueries.set(runId, query);
  return { query, dataPaths: built.dataPaths, prompt: built.prompt, getSessionId: () => query.sessionId, runId, isResume: false };
}

export function startSessionChat({ runId, sessionId, message }) {
  void runId; void message;
  const err = new Error(`codex does not support cross-process session resume (session id: ${sessionId || 'none'}) — use Continue instead, which re-runs with the follow-up context`);
  err.status = 400;
  throw err;
}

export function parseStreamEvent(message) {
  if (!message || typeof message !== 'object') return null;
  return message;
}

export function registerChild(runId, query) { activeQueries.set(runId, query); }

export function closeQuery(runId) {
  const q = activeQueries.get(runId);
  if (q) {
    try { q.close(); } catch { /* ignore */ }
    activeQueries.delete(runId);
  }
}
