// OpenCode Client — `opencode serve` HTTP API + global SSE events.
//
// 进程模型: 常驻子进程 (`opencode serve --port <空闲>`)，会话经官方 HTTP API;
// 事件经全局 SSE /event。port 由本地 net 探测空闲。prompt_async 优先，旧版
// 回退同步 message 端点。permission.asked → 自动放行/拒绝（fail-closed）。
// 事件映射抽取为纯函数 mapOpenCodeEvent 供单测使用。

import { createServer } from 'net';
import { randomBytes } from 'crypto';
import { EventEmitter } from 'events';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { resolveCliBinary, spawnResolvedCli, killTree, withTimeout, resolveEngineTimeoutMinutes } from './cli-common.mjs';
import {
  resolveAnalysisTarget, buildRuntimeProtocol,
  buildPrompt as buildDataPrompt,
  buildOntologyDirective, buildEnhancementDirective, buildLineMemoryDirective, buildMemoryToolDirective,
  ANALYSIS_INTENTS, resolveAnalysisIntent, buildIntentDirective,
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
    // The provider error may arrive as {error:{name,message}}, a bare string,
    // or flat top-level fields — surface whichever carries detail so a failed
    // run is diagnosable from its stop_reason instead of a bare opencode_error.
    const detail = props.error?.message || props.message
      || (typeof props.error === 'string' ? props.error : '')
      || props.error?.name || props.name || props.code || 'opencode_error';
    ctx.result('error_during_execution', String(detail).slice(0, 300));
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

const LOCAL_PROVIDER = 'idd-lmstudio';
const LOCAL_BASE_URL = 'http://127.0.0.1:1234/v1';
const LOCAL_DEFAULT_MODEL = 'google/gemma-4-12b-qat';
const LOCAL_SDK = '@ai-sdk/openai-compatible';

function parseInlineConfig(raw) {
  if (!raw?.trim()) return {};
  try {
    // Match complete JSON strings first; comment markers and commas inside them
    // belong to the operator's settings. OpenCode accepts JSONC in this env var.
    const stringsOrComments = /"(?:\\.|[^"\\])*"|\/\*[\s\S]*?\*\/|\/\/[^\r\n]*/g;
    const stringsOrTrailingCommas = /"(?:\\.|[^"\\])*"|,(?=\s*[}\]])/g;
    const parsed = JSON.parse(raw.replace(/^\uFEFF/, '')
      .replace(stringsOrComments, (match) => match.startsWith('"') ? match : ' ')
      .replace(stringsOrTrailingCommas, (match) => match === ',' ? '' : match));
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
  } catch { /* parsing errors can contain configured credentials */ }
  throw new Error('opencode_inline_config_invalid');
}

function buildLaunchConfig(engCfg, knowledgeTransport) {
  const local = process.env.IDD_OPENCODE_LMSTUDIO === '1';
  const env = { ...(engCfg.env || {}) };
  const model = local
    ? { modelID: process.env.IDD_OPENCODE_LMSTUDIO_MODEL?.trim() || LOCAL_DEFAULT_MODEL, providerID: LOCAL_PROVIDER }
    : engCfg.model ? { modelID: engCfg.model, providerID: engCfg.provider || 'opencode' } : undefined;
  const modelRef = local ? `${LOCAL_PROVIDER}/${model.modelID}` : null;
  if (local || knowledgeTransport) {
    const overlay = parseInlineConfig(env.OPENCODE_CONFIG_CONTENT ?? process.env.OPENCODE_CONFIG_CONTENT);
    if (knowledgeTransport) {
      const { url, token } = knowledgeTransport;
      if (typeof url !== 'string' || !url || typeof token !== 'string' || !token || /\s/.test(token)) {
        throw new Error('opencode_memory_transport_invalid');
      }
      overlay.mcp = {
        ...overlay.mcp,
        idd_memory: { type: 'remote', url, enabled: true, headers: { Authorization: `Bearer ${token}` }, oauth: false },
      };
    }
    if (local) {
      const { modelID } = model;
      overlay.model = overlay.small_model = modelRef;
      overlay.enabled_providers = [LOCAL_PROVIDER];
      overlay.disabled_providers = [];
      overlay.provider = {
        ...overlay.provider,
        [LOCAL_PROVIDER]: {
          name: 'LM Studio (local)', npm: LOCAL_SDK,
          options: { baseURL: LOCAL_BASE_URL, apiKey: 'lm-studio' },
          whitelist: [modelID],
          models: { [modelID]: { id: modelID, name: modelID, tool_call: true } },
        },
      };
      env.OPENCODE_DISABLE_MODELS_FETCH = '1';
      env.OPENCODE_DISABLE_AUTOUPDATE = '1';
    }
    env.OPENCODE_CONFIG_CONTENT = JSON.stringify(overlay);
    // /config serves the resolved child config. Protect it when carrying an
    // attempt credential, and authenticate the owned server in local-only mode.
    env.OPENCODE_SERVER_USERNAME = 'idd';
    env.OPENCODE_SERVER_PASSWORD = randomBytes(32).toString('hex');
  }
  const password = env.OPENCODE_SERVER_PASSWORD ?? process.env.OPENCODE_SERVER_PASSWORD;
  const username = (env.OPENCODE_SERVER_USERNAME ?? process.env.OPENCODE_SERVER_USERNAME) || 'opencode';
  const headers = password ? { authorization: `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}` } : {};
  return { env, headers, model, modelRef };
}

function isLocalConfig(config, model, modelRef) {
  const provider = config?.provider?.[LOCAL_PROVIDER];
  const models = provider?.whitelist;
  const configuredModel = provider?.models?.[model.modelID];
  const enabled = config?.enabled_providers;
  return Array.isArray(enabled) && enabled.length === 1 && enabled[0] === LOCAL_PROVIDER
    && !config.disabled_providers?.includes(LOCAL_PROVIDER)
    && config.model === modelRef && config.small_model === modelRef
    && provider?.npm === LOCAL_SDK && provider.options?.baseURL === LOCAL_BASE_URL
    && Array.isArray(models) && models.length === 1 && models[0] === model.modelID
    && !provider.blacklist?.includes(model.modelID)
    && configuredModel?.id === model.modelID && configuredModel.tool_call === true
    && (configuredModel.provider?.npm ?? LOCAL_SDK) === LOCAL_SDK;
}

async function waitForServer(baseUrl, headers, state, requireConfig, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (!state.finished && Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/config`, { headers, signal: AbortSignal.timeout(2000) });
      if (res.ok && requireConfig) return await res.json().catch(() => null);
      await res.body?.cancel();
      if (res.ok || res.status === 404) return null; // older versions may lack this route
    } catch { /* not ready yet */ }
    await new Promise((r) => setTimeout(r, 300));
  }
  if (!state.finished) throw new Error(`opencode server not ready after ${timeoutMs}ms`);
}

// ── Query wrapper: one resident serve process per run ──
async function startOpenCodeRun({ turnKey, prompt, emit, result, state, knowledgeTransport }) {
  const engCfg = config.harness?.engines?.opencode || {};
  const { env, headers, model, modelRef } = buildLaunchConfig(engCfg, knowledgeTransport);
  const port = engCfg.port || await findFreePort();
  if (state.finished) return;
  const baseUrl = `http://127.0.0.1:${port}`;
  state.baseUrl = baseUrl;

  const binary = resolveCliBinary('opencode');
  // spawnResolvedCli wraps Windows .cmd/.bat shims in `cmd.exe /d /s /c` — a
  // raw spawn of the resolved .cmd shim throws EINVAL on Windows. It merges
  // process.env itself and keeps windowsHide.
  const args = ['serve', '--port', String(port), '--hostname', '127.0.0.1'];
  if (modelRef) args.push('--pure'); // no external plugins can reroute local model calls
  const proc = spawnResolvedCli(binary, args, { cwd: PROJECT_ROOT, env, context: 'OpenCode' });
  state.proc = proc;
  // The bearer must never reach a log or error surface, but dropping the whole
  // stderr tail made exit failures undiagnosable — redact instead.
  const redact = (text) => knowledgeTransport?.token && typeof text === 'string'
    ? text.replaceAll(knowledgeTransport.token, '[redacted]') : text;
  let stderrTail = '';
  proc.stderr.on('data', (d) => { stderrTail = (stderrTail + d.toString()).slice(-4000); });
  proc.on('exit', (code) => {
    if (!state.finished) {
      state.finished = true;
      // A config error in the CLI may echo the string containing the bearer.
      const details = redact(stderrTail).split(/\r?\n/).filter(Boolean).slice(-2).join(' | ').slice(0, 300);
      result('error_during_execution', `OPENCODE_EXIT_${code ?? 'null'}${details ? `: ${details}` : ''}`);
    }
  });
  proc.on('error', (err) => {
    if (state.finished) return;
    state.finished = true;
    result('error_during_execution', `opencode_spawn_failed: ${err.code || 'unknown'}`);
  });

  const effectiveConfig = await waitForServer(baseUrl, headers, state, !!modelRef);
  if (state.finished) return;
  // Managed config may take precedence over the environment. Do not deliver
  // a prompt if the actual CLI cannot honor the local-only policy.
  if (modelRef && !isLocalConfig(effectiveConfig, model, modelRef)) {
    throw new Error('opencode_lmstudio_config_mismatch');
  }

  // 1) create session
  const sessionRes = await fetch(`${baseUrl}/session`, {
    method: 'POST',
    headers: { ...headers, 'content-type': 'application/json' },
    body: JSON.stringify({ title: `idd-${turnKey}` }),
  });
  if (!sessionRes.ok) throw new Error(`opencode session create failed: HTTP ${sessionRes.status}`);
  const session = await sessionRes.json().catch(() => ({}));
  const sessionId = session.id || session.sessionID || session.sessionId;
  if (!sessionId) throw new Error('opencode session create returned no id');
  state.sessionId = sessionId;

  emit({ type: 'system', subtype: 'session_ready', data: { engine: 'opencode', sessionId } });

  // Shared event context. MUST live in the outer turn scope: the SSE handler AND
  // the completion paths below (sync endpoint success / no endpoint delivered /
  // SSE idle close) all call makeCtx(). Declared inside the SSE IIFE it was
  // invisible to those outer calls — every success path threw ReferenceError,
  // which the endpoint loop's catch swallowed as "delivered" (latent since the
  // client was written; surfaced by ESLint no-undef 2026-11-03).
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
            headers: { ...headers, 'content-type': 'application/json' },
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

  // 2) SSE first, then prompt
  const controller = new AbortController();
  state.sseAbort = controller;
  const ssePromise = (async () => {
    const res = await fetch(`${baseUrl}/event`, { headers, signal: controller.signal });
    if (!res.ok || !res.body) throw new Error(`opencode /event failed: HTTP ${res.status}`);
    const decoder = new TextDecoder();
    let buf = '';
    const emitter = new EventEmitter();
    emitter.on('event', (evt) => {
      if (state.finished) return;
      try {
        if (evt?.type === 'session.error' || evt?.type === 'session.failed') {
          // Keep the raw provider error for diagnosis (bearer redacted); the
          // mapped stop_reason alone can be an empty-message event.
          logger.warn(`[opencode] session error event: ${redact(JSON.stringify(evt)).slice(0, 600)}`, { context: 'OpenCode', turnKey });
        }
        mapOpenCodeEvent(evt, makeCtx());
      } catch (e) {
        logger.warn(`[opencode] event mapping error (counted): ${e.message}`, { context: 'OpenCode', turnKey });
      }
    });

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
    model,
  });
  let delivered = false;
  for (const endpoint of ['/prompt_async', '/message_async', '/message', '/prompt']) {
    try {
      const res = await fetch(`${baseUrl}/session/${sessionId}${endpoint}`, {
        method: 'POST',
        headers: { ...headers, 'content-type': 'application/json' },
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

function createOpenCodeQuery({ turnKey, prompt, timeoutMinutes = 0, knowledgeTransport }) {
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
    timeoutGuard.cancel();
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

  // Per-turn timeout — the resident serve process + SSE stream can stall
  // silently (no session.idle, no session.error) and would otherwise hang the
  // run forever. state.proc may not exist yet (spawned after the free-port
  // probe), so the current handle is killed inside the handler.
  const timeoutGuard = withTimeout({
    minutes: resolveEngineTimeoutMinutes('opencode', timeoutMinutes),
    label: 'opencode',
    context: 'OpenCode',
    turnKey,
    onTimeout: () => {
      if (state.finished) return;
      state.finished = true;
      try { state.sseAbort?.abort(); } catch { /* ignore */ }
      result('error_during_execution', 'opencode_timeout');
      killTree(state.proc);
    },
  });

  startOpenCodeRun({ turnKey, prompt, emit: push, result, state, knowledgeTransport }).catch((e) => {
    if (state.finished) return;
    logger.error(`[opencode] run failed: ${e.message}`, { context: 'OpenCode', turnKey });
    state.finished = true;
    result('error_during_execution', `opencode_run_failed: ${e.message}`);
  });

  return {
    engine: 'opencode',
    sessionId: `opencode:run:${turnKey || Date.now()}`,
    close() {
      state.finished = true;
      timeoutGuard.cancel();
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
// ── Shared prompt assembly (exported for the intent-injection contract test) ──
export function buildOpenCodePrompt({
  analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement, lineMemory,
  analysisIntent = 'deep-diagnosis', preprocessingMode = null, knowledgeTransport = null,
}) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const { dataPaths, promptTarget } = resolveAnalysisTarget(analysisTarget);
  // Re-point the skill reference at the intent's own skill (same contract as
  // omp/acp/oneshot) so a specialist run never executes the 9-stage pipeline.
  const intent = resolveAnalysisIntent(analysisIntent);
  const intentSpec = intent && intent !== 'deep-diagnosis' ? ANALYSIS_INTENTS[intent] : null;
  const skillMd = join(
    PROJECT_ROOT,
    intentSpec
      ? `.claude/skills/${intentSpec.skill}`
      : (config.claude.skill_dir || '.claude/skills/industrial-analysis-auto'),
    'SKILL.md',
  );
  const skillRef = existsSync(skillMd)
    ? `First read the authoritative skill definition at ${skillMd} and follow its full protocol contract as binding.`
    : `Follow the ${intentSpec ? intentSpec.skill : 'industrial deep diagnostic skill (industrial-analysis-auto)'} protocol.`;
  const prompt = `${buildRuntimeProtocol(sceneName, lang)}

${skillRef}

${buildDataPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)}${buildIntentDirective(analysisIntent, sceneName, { preprocessingMode })}${buildOntologyDirective(ontology)}${buildEnhancementDirective(enhancement)}${buildLineMemoryDirective(lineMemory)}${knowledgeTransport ? buildMemoryToolDirective({}) : ''}`;
  return { dataPaths, prompt };
}

// ── Standard engine client module shape ──
const activeQueries = new Map();

export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
  ontology = null, enhancement = null,
  analysisIntent = 'deep-diagnosis', preprocessingMode = null,
  lineMemory = null, knowledgeTransport = null,
}) {
  void maxTurns; void sessionId;
  const built = buildOpenCodePrompt({
    analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement, lineMemory,
    analysisIntent, preprocessingMode, knowledgeTransport,
  });
  const query = createOpenCodeQuery({ turnKey: runId, prompt: built.prompt, timeoutMinutes, knowledgeTransport });
  activeQueries.set(runId, query);
  return { query, dataPaths: built.dataPaths, prompt: built.prompt, getSessionId: () => query.sessionId, runId, isResume: false };
}

export function startSessionChat({ runId, sessionId, message }) {
  void runId; void message;
  const err = new Error(`opencode cross-process session resume is not wired (session id: ${sessionId || 'none'}) — use Continue instead, which re-runs with the follow-up context`);
  err.status = 400;
  throw err;
}

// Raw-prompt conversational turn (standalone chat) — one prompt_async flight
// against the resident opencode server, no industrial prompt wrapper.
export function startChatTurn({ runId, prompt }) {
  const query = createOpenCodeQuery({ turnKey: runId, prompt: String(prompt || '').trim() });
  activeQueries.set(runId, query);
  return { query, runId, getSessionId: () => query.sessionId };
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
