// OpenCode Client — `opencode serve` HTTP API + global SSE events.
//
// 进程模型: 常驻子进程 (`opencode serve --port <空闲>`)，会话经官方 HTTP API;
// 事件经全局 SSE /event。port 由本地 net 探测空闲。prompt_async 优先，旧版
// 回退同步 message 端点。permission.asked → 自动放行/拒绝（fail-closed）。
// 事件映射抽取为纯函数 mapOpenCodeEvent 供单测使用。

import { spawn } from 'child_process';
import { createServer } from 'net';
import { EventEmitter } from 'events';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { resolveCliBinary, killTree } from './cli-common.mjs';
import {
  resolveAnalysisTarget, buildRuntimeProtocol,
  buildPrompt as buildDataPrompt,
  buildOntologyDirective, buildEnhancementDirective,
} from './claude-client.mjs';
import { existsSync } from 'fs';
import { join } from 'path';

// ── Pure event mapper (exported for tests) ──
// ctx: { text(partId, textDelta), flushText(partId), toolUse, toolResult,
//        session(sid), result(subtype, reason) }
export function mapOpenCodeEvent(evt, ctx) {
  if (!evt || typeof evt !== 'object') return;
  const type = evt.type || '';
  const props = evt.properties || evt.payload || evt;

  if (type === 'message.part.updated' || type === 'message.part.updated.v2') {
    const part = props.part || props;
    if (part.type === 'text') {
      const timeEnd = part.time?.end;
      if (timeEnd) {
        ctx.flushText(part.id || part.messageID, part.text || '');
      } else if (part.text) {
        ctx.text(part.id || part.messageID, part.text);
      }
    } else if (part.type === 'tool' || part.tool) {
      const status = part.state?.status || part.status;
      if (status === 'completed' || status === 'error') {
        ctx.toolResult({
          toolUseId: part.id || part.callID,
          content: part.state?.output ?? part.output ?? '',
          isError: status === 'error',
        });
      } else {
        ctx.toolUse({
          id: part.id || part.callID,
          name: part.tool || part.name,
          input: part.state?.input || part.input || {},
        });
      }
    }
    return;
  }
  if (type === 'permission.asked' || type === 'question.asked') {
    // Handled at the transport layer (needs the session id to respond);
    // surfaced to the stream for observability.
    ctx.permissionAsked?.(props);
    return;
  }
  if (type === 'session.idle' || type === 'session.completed') {
    ctx.flushAll();
    ctx.result('success', 'success');
    return;
  }
  if (type === 'session.error' || type === 'session.failed') {
    ctx.flushAll();
    ctx.result('error_during_execution', props.error?.message || props.message || 'opencode_error');
    return;
  }
  if (type === 'message.updated' || type === 'session.updated' || type === 'storage.write' || type === 'file.edited') {
    return; // metadata noise — tolerated
  }
  ctx.unknown?.(type || 'event');
}

// ── Free-port probe (local net listen on 0) ──
function findFreePort() {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

async function waitForServer(baseUrl, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/config`, { signal: AbortSignal.timeout(2000) });
      if (res.ok || res.status === 404) return true; // server answers — version-dependent route
    } catch { /* not ready yet */ }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`opencode server not ready after ${timeoutMs}ms`);
}

// ── Query wrapper: one resident serve process per run ──
async function startOpenCodeRun({ turnKey, prompt, emit, result, state }) {
  const engCfg = config.harness?.engines?.opencode || {};
  const port = engCfg.port || await findFreePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  state.baseUrl = baseUrl;

  const binary = resolveCliBinary('opencode');
  const proc = spawn(binary, ['serve', '--port', String(port), '--hostname', '127.0.0.1'], {
    cwd: PROJECT_ROOT,
    env: { ...process.env, ...(engCfg.env || {}) },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  state.proc = proc;
  let stderrTail = '';
  proc.stderr.on('data', (d) => { stderrTail = (stderrTail + d.toString()).slice(-4000); });
  proc.on('exit', (code) => {
    if (!state.finished) {
      state.finished = true;
      result('error_during_execution', `OPENCODE_EXIT_${code ?? 'null'}: ${stderrTail.split(/\r?\n/).filter(Boolean).slice(-2).join(' | ').slice(0, 300)}`);
    }
  });

  await waitForServer(baseUrl);

  // 1) create session
  const sessionRes = await fetch(`${baseUrl}/session`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: `idd-${turnKey}` }),
  });
  if (!sessionRes.ok) throw new Error(`opencode session create failed: HTTP ${sessionRes.status}`);
  const session = await sessionRes.json().catch(() => ({}));
  const sessionId = session.id || session.sessionID || session.sessionId;
  if (!sessionId) throw new Error('opencode session create returned no id');
  state.sessionId = sessionId;

  emit({ type: 'system', subtype: 'session_ready', data: { engine: 'opencode', sessionId } });

  // 2) SSE first, then prompt
  const controller = new AbortController();
  state.sseAbort = controller;
  const ssePromise = (async () => {
    const res = await fetch(`${baseUrl}/event`, { signal: controller.signal });
    if (!res.ok || !res.body) throw new Error(`opencode /event failed: HTTP ${res.status}`);
    const decoder = new TextDecoder();
    let buf = '';
    const emitter = new EventEmitter();
    emitter.on('event', (evt) => {
      if (state.finished) return;
      try {
        mapOpenCodeEvent(evt, makeCtx());
      } catch (e) {
        logger.warn(`[opencode] event mapping error (counted): ${e.message}`, { context: 'OpenCode', turnKey });
      }
    });

    function makeCtx() {
      return {
        text(partId, text) { state.textParts.set(partId, text); },
        flushText(partId, text) {
          if (text) emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text }] } });
          state.textParts.delete(partId);
        },
        flushAll() {
          for (const [partId, text] of state.textParts) {
            if (text) emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text }] } });
            state.textParts.delete(partId);
          }
        },
        toolUse: (t) => emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'tool_use', id: t.id || 'tool', name: t.name || 'tool', input: t.input || {} }] } }),
        toolResult: (t) => emit({
          type: 'user',
          message: {
            role: 'user',
            content: [{ type: 'tool_result', tool_use_id: t.toolUseId || '', content: String(t.content ?? ''), is_error: t.isError === true }],
          },
        }),
        permissionAsked: async (props) => {
          const autoApprove = engCfg.auto_approve !== false;
          logger.info(`[opencode] permission.asked → ${autoApprove ? 'once (auto_approve)' : 'reject (fail-closed)'}`, { context: 'OpenCode', turnKey });
          emit({ type: 'system', subtype: 'permission_request', data: { engine: 'opencode', autoApprove } });
          const permId = props.id || props.permissionID;
          const sid = props.sessionID || sessionId;
          if (permId) {
            fetch(`${baseUrl}/session/${sid}/permissions/${permId}`, {
              method: 'POST',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ response: autoApprove ? 'once' : 'reject' }),
            }).catch(() => {});
          }
        },
        result: (subtype, reason) => {
          if (state.finished) return;
          state.finished = true;
          result(subtype, reason);
        },
        unknown: () => {},
      };
    }

    const onSseEvent = (raw) => {
      for (const line of raw.split(/\r?\n/)) {
        if (!line.startsWith('data:')) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === '[DONE]') continue;
        try { emitter.emit('event', JSON.parse(payload)); } catch { /* malformed SSE frame — counted via noise */ }
      }
    };

    const reader = res.body.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          onSseEvent(frame);
        }
      }
    } catch { /* aborted or stream error — result handled elsewhere */ }
  })();

  // 3) deliver the prompt — prompt_async first, sync message fallback
  const payload = JSON.stringify({
    parts: [{ type: 'text', text: prompt }],
    model: engCfg.model ? { modelID: engCfg.model, providerID: engCfg.provider || 'opencode' } : undefined,
  });
  let delivered = false;
  for (const endpoint of ['/prompt_async', '/message_async', '/message', '/prompt']) {
    try {
      const res = await fetch(`${baseUrl}/session/${sessionId}${endpoint}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: payload,
      });
      if (res.status === 404 || res.status === 405) continue; // try next route shape
      if (!res.ok) throw new Error(`opencode prompt failed: HTTP ${res.status} via ${endpoint}`);
      delivered = true;
      // Sync endpoints answer with the completed messages — drive completion.
      if (endpoint === '/message' || endpoint === '/prompt') {
        const data = await res.json().catch(() => null);
        const messages = Array.isArray(data) ? data : (data?.parts ? [data] : data?.messages || []);
        for (const msg of messages) {
          const info = msg.info || msg;
          const parts = msg.parts || [];
          for (const part of parts) {
            if (part.type === 'text' && part.text) {
              emit({ type: 'assistant', message: { role: info.role || 'assistant', content: [{ type: 'text', text: part.text }] } });
            } else if (part.type === 'tool') {
              emit({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'tool_use', id: part.id || part.callID, name: part.tool || 'tool', input: part.state?.input || {} }] } });
            }
          }
        }
        makeCtx().result('success', 'success');
      }
      break;
    } catch (e) {
      if (delivered) break;
      logger.warn(`[opencode] prompt via ${endpoint} failed: ${e.message}`, { context: 'OpenCode', turnKey });
    }
  }
  if (!delivered) {
    makeCtx().result('error_during_execution', 'opencode_prompt_failed: no supported prompt endpoint responded');
  }

  await ssePromise.catch(() => {});
  if (!state.finished) {
    state.finished = true;
    makeCtx().result('success', 'success'); // SSE closed after idle — normal end
  }
}

function createOpenCodeQuery({ turnKey, prompt }) {
  const queue = [];
  let wake = null;
  let closed = false;
  let numTurns = 0;
  const startedAt = Date.now();
  const state = {
    proc: null, finished: false, textParts: new Map(), sseAbort: null, sessionId: null,
  };

  const push = (msg) => {
    queue.push(msg);
    if (msg?.type === 'assistant') numTurns += 1;
    if (wake) { wake(); wake = null; }
  };
  const end = () => { closed = true; if (wake) { wake(); wake = null; } };
  const result = (subtype, stopReason) => {
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: numTurns,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: state.sessionId ? `opencode:${state.sessionId}` : `opencode:run:${turnKey}`,
    });
    end();
    // 回合终点 = 进程终点（延迟自杀：serve 进程 + SSE 连接）。
    setTimeout(() => {
      try { state.sseAbort?.abort(); } catch { /* ignore */ }
      killTree(state.proc);
    }, 250);
  };

  startOpenCodeRun({ turnKey, prompt, emit: push, result, state }).catch((e) => {
    logger.error(`[opencode] run failed: ${e.message}`, { context: 'OpenCode', turnKey });
    state.finished = true;
    result('error_during_execution', `opencode_run_failed: ${e.message}`);
  });

  return {
    engine: 'opencode',
    sessionId: `opencode:run:${turnKey || Date.now()}`,
    close() {
      try { state.sseAbort?.abort(); } catch { /* ignore */ }
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
function buildOpenCodePrompt({ analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement }) {
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
  void maxTurns; void timeoutMinutes; void sessionId;
  const built = buildOpenCodePrompt({
    analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement,
  });
  const query = createOpenCodeQuery({ turnKey: runId, prompt: built.prompt });
  activeQueries.set(runId, query);
  return { query, dataPaths: built.dataPaths, prompt: built.prompt, getSessionId: () => query.sessionId, runId, isResume: false };
}

export function startSessionChat({ runId, sessionId, message }) {
  void runId; void message;
  const err = new Error(`opencode cross-process session resume is not wired (session id: ${sessionId || 'none'}) — use Continue instead, which re-runs with the follow-up context`);
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
