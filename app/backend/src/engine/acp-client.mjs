// ACP Client — Agent Client Protocol v1 over stdio for the resident-session
// engines dsh (DeepSeek Harness), hermes, and qwen (legacy Zed ACP dialect).
//
// 协议参考: https://agentclientprotocol.com
//   standard:  initialize → session/new → session/prompt (单飞, 响应在回合终点)
//              notifications: session/update { agent_message_chunk / agent_thought_chunk /
//                             tool_call / tool_call_update }
//              server→client request: session/request_permission → 自动放行/拒绝
//   qwen 旧版: initialize / sendUserMessage{content[]} / cancelSendMessage;
//              streamAssistantMessageChunk 增量; requestToolCallConfirmation 审批。
//              camelCase 方法、无 sessionId、单隐式会话。
//
// 方法名集中在一处常量表（pre-1.0 协议漂移只改这里）。审批超时/取消一律
// fail-closed（拒绝）。进程模型：每回合一个常驻子进程，回合结束即销毁。

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

// ── Method tables — the single place that knows each dialect's names ──
export const METHODS = {
  standard: {
    initialize: 'initialize',
    sessionNew: 'session/new',
    sessionPrompt: 'session/prompt',
    sessionCancel: 'session/cancel',
    sessionUpdate: 'session/update',
    requestPermission: 'session/request_permission',
  },
  qwen: {
    initialize: 'initialize',
    sessionNew: null,                    // 单隐式会话 — no session/new
    sessionPrompt: 'sendUserMessage',    // camelCase 旧版 Zed ACP
    sessionCancel: 'cancelSendMessage',
    sessionUpdate: 'streamAssistantMessageChunk',
    requestPermission: 'requestToolCallConfirmation',
  },
};

export function engineMethodTable(id) {
  return id === 'qwen' ? METHODS.qwen : METHODS.standard;
}

export function engineSpawnArgs(id) {
  const engCfg = config.harness?.engines?.[id] || {};
  if (id === 'dsh') return engCfg.acp_args || ['--profile', 'acp'];
  if (id === 'hermes') return engCfg.acp_args || ['acp'];
  if (id === 'qwen') return engCfg.acp_args || ['--experimental-acp'];
  return engCfg.acp_args || [];
}

// ── session/update → standardized messages ──
export function mapAcpUpdate(params, emit) {
  const upd = params?.update || params;
  const kind = upd?.sessionUpdate || upd?.type || upd?.kind;
  switch (kind) {
    case 'agent_message_chunk': {
      const c = upd.content ?? upd.contents;
      const text = typeof c === 'string' ? c : (c?.text || (Array.isArray(c) ? c.map((x) => x?.text || '').join('') : ''));
      if (text) emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text }] } });
      break;
    }
    case 'agent_thought_chunk': {
      const c = upd.content ?? upd.contents;
      const text = typeof c === 'string' ? c : (c?.text || '');
      if (text) emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'thinking', thinking: text }] } });
      break;
    }
    case 'tool_call': {
      emit({
        type: 'assistant',
        message: {
          role: 'assistant',
          content: [{
            type: 'tool_use',
            id: upd.toolCallId || upd.id || 'tool',
            name: upd.title || upd.name || upd.kind || 'tool',
            input: upd.input || upd.rawInput || {},
          }],
        },
      });
      break;
    }
    case 'tool_call_update': {
      const status = upd.status || 'completed';
      if (status === 'completed' || status === 'failed' || upd.output || upd.content) {
        emit({
          type: 'user',
          message: {
            role: 'user',
            content: [{
              type: 'tool_result',
              tool_use_id: upd.toolCallId || upd.id || '',
              content: typeof upd.output === 'string' ? upd.output : JSON.stringify(upd.output ?? upd.content ?? ''),
              is_error: status === 'failed',
            }],
          },
        });
      }
      break;
    }
    default:
      break; // plan / available_commands_update / … — tolerated, ignored
  }
}

// ── Spawns the engine process and performs the ACP handshake + prompt ──
// `state` is populated synchronously (proc) so close()/killed work before
// the async handshake completes.
async function startAcpSession(id, { turnKey, prompt, label, state, emit, result, onEngineSession }) {
  const engCfg = config.harness?.engines?.[id] || {};
  const methods = engineMethodTable(id);
  const proc = spawnCli(id, engineSpawnArgs(id), { cwd: PROJECT_ROOT });
  state.proc = proc;
  const getStderrTail = stderrTailRef(proc);
  let finished = false;

  const finish = (subtype, stopReason) => {
    if (finished) return;
    finished = true;
    result(subtype, stopReason);
    // 回合终点 = 进程终点：延迟自杀，避免常驻子进程在 run 结束后变成僵尸。
    setTimeout(() => killTree(proc), 250);
  };

  proc.on('exit', (code) => {
    if (!finished) {
      const tail = getStderrTail().split(/\r?\n/).filter(Boolean).slice(-3).join(' | ');
      finish('error_during_execution', `${id.toUpperCase()}_EXIT_${code ?? 'null'}${tail ? `: ${tail.slice(0, 300)}` : ''}`);
    }
  });

  const rpc = createStdioJsonRpc(proc, {
    label: `${id}:${label}`,
    requestTimeoutMs: 30000,
    // 审批：auto_approve（默认 true，无人值守诊断必须）立即放行；关闭时 fail-closed 拒绝。
    onRequest: async (method, params) => {
      if (method === methods.requestPermission || /permission|approval|confirmation/i.test(method)) {
        const autoApprove = engCfg.auto_approve !== false;
        logger.info(`[${id}] ${method} → ${autoApprove ? 'allow (auto_approve)' : 'deny (fail-closed)'}`, { context: 'Acp', turnKey });
        emit({ type: 'system', subtype: 'permission_request', data: { engine: id, method, autoApprove } });
        if (!autoApprove) return { outcome: { outcome: 'rejected' } };
        // Standard ACP: select the first allow-like option; legacy qwen: allow flag.
        const options = Array.isArray(params?.options) ? params.options : [];
        const allowOpt = options.find((o) => /allow|proceed|accept/i.test(o?.kind || o?.name || o?.optionId || ''));
        if (allowOpt) return { outcome: { outcome: 'selected', optionId: allowOpt.optionId ?? allowOpt.kind } };
        return { outcome: { outcome: 'selected', optionId: 'allow' }, allow: true };
      }
      emit({ type: 'system', subtype: 'server_request', data: { engine: id, method } });
      return {};
    },
    onNotification: (n) => {
      if (n.method === methods.sessionUpdate) {
        mapAcpUpdate(n.params, emit);
      } else if (!/read|list|available/i.test(n.method)) {
        emit({ type: 'system', subtype: 'notice', data: { engine: id, method: n.method } });
      }
    },
  });

  try {
    // 1) initialize handshake
    await rpc.request(methods.initialize, {
      protocolVersion: 1,
      clientCapabilities: { fs: { readTextFile: false, writeTextFile: false }, terminal: false },
    }, { timeoutMs: 30000 });

    // 2) session/new (qwen 旧版无此步 — 单隐式会话)
    let engineSessionId = null;
    if (methods.sessionNew) {
      const created = await rpc.request(methods.sessionNew, {
        cwd: PROJECT_ROOT,
        mcpServers: [],
      }, { timeoutMs: 30000 });
      engineSessionId = created?.sessionId || created?.session_id || created?.id || null;
    }
    onEngineSession(engineSessionId);

    emit({ type: 'system', subtype: 'session_ready', data: { engine: id, engineSessionId } });

    // 3) session/prompt — 单飞: the response only arrives at the turn's end.
    const promptParams = methods.sessionNew
      ? { sessionId: engineSessionId, prompt: [{ type: 'text', text: prompt }] }
      : { content: [{ type: 'text', text: prompt }] }; // qwen: sendUserMessage{content[]}

    await rpc.request(methods.sessionPrompt, promptParams, { timeoutMs: 0 })
      .then((res) => {
        const stop = res?.stopReason || res?.stop_reason || 'end_turn';
        finish(stop === 'end_turn' || stop === 'complete' || stop === 'success' ? 'success' : 'error_during_execution', stop);
        return res;
      })
      .catch((e) => {
        finish('error_during_execution', `${id}_prompt_failed: ${e.message}`);
        return null;
      });
  } catch (e) {
    logger.error(`[${id}] ACP session setup failed: ${e.message}`, { context: 'Acp', turnKey });
    finish('error_during_execution', `${id}_session_failed: ${e.message}`);
  }
}

// ── Query wrapper: standardized async iterable over an ACP session ──
function createAcpQuery(id, { turnKey, prompt, label }) {
  const queue = [];
  let wake = null;
  let closed = false;
  let sessionId = `${id}:run:${turnKey || Date.now()}`;
  let numTurns = 0;
  let startedAt = Date.now();
  const state = { proc: null };

  const push = (msg) => {
    queue.push(msg);
    if (msg?.type === 'assistant') numTurns += 1;
    if (wake) { wake(); wake = null; }
  };
  const end = () => { closed = true; if (wake) { wake(); wake = null; } };

  const emit = (msg) => push(msg);
  const result = (subtype, stopReason) => {
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: numTurns,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: sessionId,
    });
    end();
  };

  void startAcpSession(id, {
    turnKey, prompt, label, state, emit, result,
    onEngineSession: (sid) => { if (sid) sessionId = `${id}:${sid}`; },
  });

  return {
    engine: id,
    sessionId,
    close() {
      killTree(state.proc);
      closed = true;
      if (wake) { wake(); wake = null; }
    },
    get killed() {
      const proc = state.proc;
      return proc ? (proc.killed || proc.exitCode !== null) : false;
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

// ── Shared prompt assembly (mirrors omp-client / one-shot specs) ──
function buildAcpPrompt({ analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement }) {
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
function createAcpEngineClient(id) {
  const activeQueries = new Map();

  function startDiagnosis({
    analysisTarget, userQuestion, sceneName,
    runId, maxTurns = 0, timeoutMinutes = 0,
    reportLanguage, followUpMessage, sessionId = null,
    ontology = null, enhancement = null,
  }) {
    void maxTurns; void timeoutMinutes; // turn budget enforced by abort + engine limits
    void sessionId; // ACP v1 无跨进程 session resume — follow-ups 走 Continue 全量重放
    const built = buildAcpPrompt({
      analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement,
    });
    const query = createAcpQuery(id, {
      turnKey: runId,
      prompt: built.prompt,
      label: `diagnosis:${runId}`,
    });
    activeQueries.set(runId, query);
    return { query, dataPaths: built.dataPaths, prompt: built.prompt, getSessionId: () => query.sessionId, runId, isResume: false };
  }

  function startSessionChat({ runId, sessionId, message }) {
    // 诚实语义: this ACP dialect has no cross-process session resume —
    // refuse instead of silently restarting a context-free engine session.
    void runId; void message;
    const err = new Error(`${id} does not support cross-process session resume (session id: ${sessionId || 'none'}) — use Continue instead, which re-runs with the follow-up context`);
    err.status = 400;
    throw err;
  }

  function parseStreamEvent(message) {
    if (!message || typeof message !== 'object') return null;
    return message;
  }

  function registerChild(runId, query) { activeQueries.set(runId, query); }
  function closeQuery(runId) {
    const q = activeQueries.get(runId);
    if (q) {
      try { q.close(); } catch { /* ignore */ }
      activeQueries.delete(runId);
    }
  }

  return { startDiagnosis, startSessionChat, parseStreamEvent, registerChild, closeQuery };
}

export const dshClient = createAcpEngineClient('dsh');
export const hermesClient = createAcpEngineClient('hermes');
export const qwenClient = createAcpEngineClient('qwen');
