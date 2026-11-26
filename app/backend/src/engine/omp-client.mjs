// OMP Client — live execution harness over the OMP CLI's RPC mode.
//
// Spawns `omp --mode=rpc` (NDJSON over stdin/stdout) and adapts its event
// stream into the same standardized message shapes the Claude Agent SDK
// emits, so diagnosis.service.mjs / chat.service.mjs can dispatch between
// the 'claude' and 'omp' engines without touching their consumption loops.
//
// Protocol (observed, protocolVersion 1):
//   → {"type":"prompt","message":"..."}       after the "ready" handshake
//   ← message_start/message_end (role: user|assistant|toolResult)
//   ← tool_execution_start/update/end (toolCallId, toolName, result)
//   ← turn_start/turn_end, agent_start/agent_end (isTerminal)

import {
  config, PROJECT_ROOT,
} from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { recordProviderError } from '../services/provider-error.service.mjs';
import { whereLookup, spawnResolvedCli, killTree, withTimeout, resolveEngineTimeoutMinutes, resolveCliBinary } from './cli-common.mjs';
import { existsSync, mkdirSync, mkdtempSync, rmSync, readdirSync, statSync, writeFileSync } from 'fs';
import { join, isAbsolute } from 'path';
import { tmpdir } from 'os';
import {
  buildRuntimeProtocol, buildPrompt, resolveAnalysisTarget,
  isDangerousCommand, buildOntologyDirective, buildEnhancementDirective, buildLineMemoryDirective, buildMemoryToolDirective,
  ANALYSIS_INTENTS, resolveAnalysisIntent, buildIntentDirective,
  DATA_DIR, WORKSPACE_DIR,
} from './claude-client.mjs';

// ── Binary resolution ──
// 探测与拉起同源: probeOmpEngine (the availability gate for /start|/execute)
// and the real spawn share this function, and it resolves through cli-common's
// shared chain — config harness.engines.omp.binary → env HARNESS_OMP_COMMAND →
// `where`/PATH — exactly like every other harness. The documented legacy knob
// `config.omp.binary` is consulted only when the shared chain found nothing
// more specific than the bare name.
//
// No module-local memoization on purpose: the shared chain is cached inside
// cli-common (invalidateBinaryCache('omp') drops it), and a separate cache here
// would survive env/config changes and re-create the probe/spawn divergence.
//
// Node's spawn on Windows cannot execute the extensionless `omp` bash shim,
// and PATH resolution differs between shells — resolve to an absolute path.
export function resolveOmpBinary() {
  const shared = resolveCliBinary('omp'); // env override / explicit config path / PATH hit
  const configured = config.omp?.binary || 'omp';

  let resolved;
  if (shared !== 'omp') {
    resolved = shared;
  } else if (isAbsolute(configured)) {
    resolved = configured;
  } else {
    const candidates = [];
    // 1) `where omp` / `which omp` — whereLookup prefers .exe then .cmd/.bat;
    //    on Windows it must NEVER pick the extensionless sh shim (npm global
    //    installs emit sh/.cmd/.ps1 shims; the sh one cannot be spawned).
    const found = whereLookup(configured);
    if (found) candidates.push(found);
    // 2) Common install locations
    if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
      candidates.push(join(process.env.LOCALAPPDATA, 'omp', 'omp.exe'));
    }
    // 3) Bare name — works when the backend runs under a POSIX shell
    candidates.push(configured);

    resolved = candidates.find(c => existsSync(c)) || candidates[candidates.length - 1];
  }

  logger.info(`OMP binary resolved to: ${resolved}`, { context: 'OmpClient' });
  return resolved;
}

// ── Session dirs ──
function ompConfig() {
  return config.omp || {};
}

export function runSessionDir(runId) {
  const dir = join(PROJECT_ROOT, ompConfig().session_root || 'workspace/.omp-sessions', runId);
  mkdirSync(dir, { recursive: true });
  return dir;
}

export function chatSessionDir(chatId) {
  const dir = join(PROJECT_ROOT, ompConfig().chat_session_root || 'workspace/.omp-chats', chatId);
  mkdirSync(dir, { recursive: true });
  return dir;
}

// Opaque session marker stored in DB session_id columns (non-UUID by design;
// Claude-specific resume paths ignore/reject it, OMP paths parse it back).
export const OMP_SESSION_PREFIX = 'omp:';

export function ompRunSessionId(runId) {
  return `${OMP_SESSION_PREFIX}run:${runId}`;
}

export function ompChatSessionId(chatId) {
  return `${OMP_SESSION_PREFIX}chat:${chatId}`;
}

export function parseOmpSessionId(marker) {
  if (typeof marker !== 'string' || !marker.startsWith(OMP_SESSION_PREFIX)) return null;
  const rest = marker.slice(OMP_SESSION_PREFIX.length);
  if (rest.startsWith('run:')) return { kind: 'run', id: rest.slice(4) };
  if (rest.startsWith('chat:')) return { kind: 'chat', id: rest.slice(5) };
  return null;
}

// ── Spawn an OMP RPC process ──
// timeoutMinutes (per-run, minutes) wins over ompConfig().timeout_minutes;
// 0/undefined keeps the config default. The service layer forwards the run's
// requested budget so a long pipeline is not silently killed at the default.
/**
 * The run's own session file: the OLDEST jsonl in its session dir.
 *
 * Resume must target THIS file explicitly (`--resume=<path>`) instead of `-c`
 * (continue-latest): when a resume ever hits OMP's cross-process session lock,
 * OMP falls back to a fresh session file whose replay turns are empty — and
 * `-c` would then keep resuming the poisoned file forever.
 */
export function resolveOmpSessionFile(sessionDir) {
  try {
    const files = readdirSync(sessionDir)
      .filter((f) => f.endsWith('.jsonl'))
      .map((f) => ({ f, m: statSync(join(sessionDir, f)).mtimeMs }))
      .sort((a, b) => a.m - b.m);
    return files.length ? join(sessionDir, files[0].f) : null;
  } catch {
    return null;
  }
}

const KNOWLEDGE_PROVIDER = 'lm-studio';
// Model pin for knowledge-transport attempts: these runs verify the resolved
// provider/model before prompting, so the declared and served model must
// match. Override with IDD_OMP_KNOWLEDGE_MODEL (e.g. a small remote model).
const KNOWLEDGE_MODEL = process.env.IDD_OMP_KNOWLEDGE_MODEL?.trim() || 'google/gemma-4-12b-qat';
const KNOWLEDGE_BASE_URL = 'http://127.0.0.1:1234/v1';
const KNOWLEDGE_TOOLS = ['mcp__idd_memory_memory_search', 'mcp__idd_memory_memory_get'];
const KNOWLEDGE_AUTH_ENV = 'IDD_OMP_KNOWLEDGE_AUTH';
const KNOWLEDGE_STATE_ID = 'idd-knowledge-startup';

function validateKnowledgeTransport(transport, resume) {
  if (resume) throw new Error('OMP knowledge transport does not support session resume');
  if (typeof transport.url !== 'string' || !/^http:\/\/127\.0\.0\.1:[1-9]\d{0,4}\/mcp(?![\s\S])/.test(transport.url)) {
    throw new Error('OMP knowledge transport must use the loopback MCP endpoint');
  }
  try { new URL(transport.url); } catch { throw new Error('Invalid OMP knowledge transport URL'); }
  if (typeof transport.token !== 'string' || !transport.token || /[^A-Za-z0-9._~+/=-]/.test(transport.token)) {
    throw new Error('Invalid OMP knowledge transport token');
  }
}

function prepareKnowledgeAttempt({ url, token }) {
  const dir = mkdtempSync(join(tmpdir(), 'idd-omp-knowledge-'));
  const cleanup = () => {
    try { rmSync(dir, { recursive: true, force: true, maxRetries: 3, retryDelay: 50 }); }
    catch { logger.warn('Could not remove OMP knowledge attempt directory', { context: 'OmpClient' }); }
  };
  const write = (file, value) => writeFileSync(join(dir, file), JSON.stringify(value), { mode: 0o600, flag: 'wx' });
  try {
    // OMP reads servers from the agent directory's mcp.json (not --config).
    // In 18.12.2 a bare header value naming an env var resolves at connection
    // time. Keep the actual bearer out of files, argv, and the prompt.
    write('mcp.json', { mcpServers: { idd_memory: { type: 'http', url,
      headers: { Authorization: KNOWLEDGE_AUTH_ENV } } } });
    // A cold OMP profile can miss LM Studio's discovery deadline. Declare
    // the exact model under the native provider rather than relying on cache.
    write('models.yml', { providers: { [KNOWLEDGE_PROVIDER]: {
      baseUrl: KNOWLEDGE_BASE_URL, api: 'openai-completions', apiKey: KNOWLEDGE_PROVIDER,
      models: [{ id: KNOWLEDGE_MODEL, name: KNOWLEDGE_MODEL, reasoning: false,
        input: ['text', 'image'], contextWindow: 65536, maxTokens: 8192,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }],
    } } });
    write('idd-config.yml', {
      enabledProviders: [KNOWLEDGE_PROVIDER],
      retry: { modelFallback: false },
      mcp: { enableProjectConfig: false, startupTimeoutMs: 0 },
    });
  } catch (error) {
    cleanup();
    throw error;
  }
  return {
    args: [`--config=${join(dir, 'idd-config.yml')}`, `--model=${KNOWLEDGE_PROVIDER}/${KNOWLEDGE_MODEL}`,
      '--no-prewalk', '--no-title', '--no-extensions'],
    env: {
      PI_CODING_AGENT_DIR: dir, OMP_PROFILE: 'default', PI_PROFILE: 'default',
      LM_STUDIO_BASE_URL: KNOWLEDGE_BASE_URL, [KNOWLEDGE_AUTH_ENV]: `Bearer ${token}`,
    },
    cleanup,
  };
}

function spawnOmpRpc({ sessionDir, resume = false, label = 'omp', timeoutMinutes = 0, knowledgeTransport }) {
  const binary = resolveOmpBinary();
  const args = ['--mode=rpc', '-p'];

  if (ompConfig().auto_approve !== false) args.push('--auto-approve');
  if (ompConfig().thinking && ompConfig().thinking !== 'auto') args.push(`--thinking=${ompConfig().thinking}`);
  const maxTimeMinutes = Number(timeoutMinutes) > 0 ? Number(timeoutMinutes) : ompConfig().timeout_minutes;
  if (maxTimeMinutes) args.push(`--max-time=${Math.round(maxTimeMinutes * 60)}`);
  args.push(`--session-dir=${sessionDir}`);
  if (resume) {
    const sessionFile = resolveOmpSessionFile(sessionDir);
    if (sessionFile) args.push(`--resume=${sessionFile}`);
    else args.push('-c');
  }

  const attempt = knowledgeTransport && prepareKnowledgeAttempt(knowledgeTransport);
  if (attempt) args.push(...attempt.args);
  let proc;
  try {
    logger.info(`Spawning ${label}: ${binary} ${args.join(' ')}`, { context: 'OmpClient' });
    proc = spawnResolvedCli(binary, args, { cwd: PROJECT_ROOT, context: 'OmpClient', env: attempt?.env });
  } catch (error) {
    attempt?.cleanup();
    throw error;
  }
  if (attempt) proc.once('close', attempt.cleanup);

  let stderrTail = '';
  proc.stderr.on('data', (d) => {
    if (!attempt) stderrTail = (stderrTail + d.toString()).slice(-4000);
  });

  return { proc, stderrTailRef: () => stderrTail };
}

// ── Event adapter ──
// Wraps an OMP RPC process as an async iterable of standardized messages
// (Claude-SDK-compatible shapes), plus a close() handle.
// Exported for tests (spawned with a directly-owned fake RPC process).
export function createOmpQuery(proc, { runKey, maxTurns = 0, label = 'omp', timeoutMinutes = 0, knowledgeToken }) {
  const queue = [];
  let wake = null;
  let closed = false;
  let sawReady = false;
  let knowledgeVerified = !knowledgeToken;
  let wakeStartup;
  const startup = new Promise((resolve) => { wakeStartup = resolve; });
  let sawAgentEnd = false;
  let sawResult = false;
  let turnCount = 0;
  let startedAt = Date.now();
  const pendingToolCalls = new Map(); // toolCallId -> { name }
  const emittedToolResults = new Set(); // toolCallId already emitted (protocol reports results twice)

  const push = (msg) => { queue.push(msg); if (wake) { wake(); wake = null; } };
  const end = () => { closed = true; wakeStartup(); if (wake) { wake(); wake = null; } };

  const redact = (text) => knowledgeToken && typeof text === 'string' ? text.replaceAll(knowledgeToken, '[redacted]') : text;

  const emitToolResultOnce = (toolCallId, text, isError) => {
    if (emittedToolResults.has(toolCallId)) return;
    emittedToolResults.add(toolCallId);
    push({
      type: 'user',
      message: {
        role: 'user',
        content: [{
          type: 'tool_result',
          tool_use_id: toolCallId,
          content: text,
          is_error: isError === true,
        }],
      },
    });
  };

  const emitAssistantMessage = (ompMessage) => {
    const blocks = [];
    for (const block of ompMessage.content || []) {
      if (block.type === 'text') {
        if (block.text && block.text.trim()) blocks.push({ type: 'text', text: block.text });
      } else if (block.type === 'thinking') {
        blocks.push({ type: 'thinking', thinking: block.thinking || '' });
      } else if (block.type === 'toolCall') {
        let input = block.arguments;
        if (typeof input === 'string') {
          try { input = JSON.parse(input); } catch { input = { raw: input }; }
        }
        blocks.push({ type: 'tool_use', id: block.id, name: block.name, input: input || {} });
        pendingToolCalls.set(block.id, { name: block.name });
      }
    }
    if (blocks.length > 0) {
      push({ type: 'assistant', message: { role: 'assistant', content: blocks } });
    }
  };

  const emitToolResult = (ompMessage) => {
    const text = (ompMessage.content || [])
      .map(b => (typeof b === 'string' ? b : b.text || ''))
      .join('\n');
    emitToolResultOnce(ompMessage.toolCallId, text, ompMessage.isError);
  };

  const emitResult = (subtype, stopReason) => {
    if (sawResult) return;
    sawResult = true;
    timeoutGuard.cancel();
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: turnCount,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: null,
    });
  };

  const failStartup = (reason) => {
    if (closed) return;
    emitResult('error_during_execution', reason);
    end();
    killTree(proc);
  };
  const handleLine = (line) => {
    if (knowledgeToken && closed) return;
    let evt;
    try { evt = JSON.parse(line); } catch { return; }
    if (!evt || typeof evt !== 'object') return;

    switch (evt.type) {
      case 'ready':
        if (sawReady) break;
        sawReady = true;
        if (knowledgeToken) {
          proc.stdin.write(`${JSON.stringify({ type: 'get_state', id: KNOWLEDGE_STATE_ID })}\n`);
        } else wakeStartup();
        break;
      case 'response':
        if (knowledgeToken && !knowledgeVerified && evt.id === KNOWLEDGE_STATE_ID && evt.command === 'get_state') {
          const { model, dumpTools, systemPrompt } = evt.data ?? {};
          if (!evt.success || model?.provider !== KNOWLEDGE_PROVIDER || model?.id !== KNOWLEDGE_MODEL
            || model?.baseUrl !== KNOWLEDGE_BASE_URL) {
            failStartup('omp_knowledge_model_mismatch');
            break;
          }
          const names = new Set((dumpTools ?? []).map(tool => tool.name));
          // Default OMP 18.12.2 exposes MCP via eval's mounted-device catalog,
          // not as native model tools. get_state carries that in systemPrompt.
          const catalog = new Set((systemPrompt ?? []).join('\n').match(/\bmcp__\w+\b/g));
          if (!KNOWLEDGE_TOOLS.every(name => names.has(name) || (names.has('eval') && catalog.has(name)))) {
            failStartup('omp_knowledge_tools_unavailable');
            break;
          }
          knowledgeVerified = true;
          wakeStartup();
          break;
        }
        if (evt.command === 'prompt' && evt.success === false) {
          logger.error(`OMP rejected prompt [${label}]: ${evt.error || 'unknown'}`, { context: 'OmpClient', runKey });
          emitResult('error_during_execution', `omp_prompt_rejected: ${evt.error || 'unknown'}`);
          end();
        }
        break;
      case 'agent_start':
        startedAt = Date.now();
        turnCount = 0;
        break;
      case 'turn_start':
        turnCount += 1;
        if (maxTurns > 0 && turnCount > maxTurns) {
          logger.warn(`OMP run ${runKey} exceeded maxTurns=${maxTurns} — stopping`, { context: 'OmpClient', runKey });
          killTree(proc);
        }
        break;
      case 'message_start':
      case 'message_update':
        // Partial deltas are ignored — full content arrives with message_end.
        break;
      case 'message_end': {
        const role = evt.message?.role;
        if (role === 'assistant') {
          // A provider-failed turn (429/5xx) arrives as an assistant message
          // with empty content and stopReason=error. Surfacing it beats a
          // silently empty reply the user cannot distinguish from success.
          if (evt.message.stopReason === 'error') {
            const detail = redact(evt.message.errorMessage || evt.message.errorStatus || 'provider error');
            const provider = recordProviderError('omp', evt.message.errorMessage || evt.message.errorStatus || 'provider error');
            push({
              type: 'system',
              subtype: 'notice',
              data: {
                level: 'error',
                message: `OMP assistant turn failed: ${detail}`,
                provider_error: provider?.code || null,
                provider_label: provider?.label || null,
              },
            });
          }
          emitAssistantMessage(evt.message);
        } else if (role === 'toolResult') emitToolResult(evt.message);
        break;
      }
      case 'tool_execution_start':
        pendingToolCalls.set(evt.toolCallId, { name: evt.toolName || 'tool' });
        break;
      case 'tool_execution_end': {
        // Results also arrive as a toolResult message_end — emitToolResultOnce dedupes.
        const resultText = (evt.result?.content || [])
          .map(c => (typeof c === 'string' ? c : c.text || ''))
          .join('\n');
        emitToolResultOnce(evt.toolCallId, resultText, evt.result?.isError || evt.isError);
        break;
      }
      case 'agent_end':
        sawAgentEnd = true;
        emitResult('success', 'success');
        end();
        break;
      case 'notice':
        // Real OMP connection errors can echo the resolved header value —
        // never let the bearer reach events or logs.
        if (evt.level === 'error') {
          push({ type: 'system', subtype: 'notice', data: { message: redact(evt.message) } });
        }
        break;
      default:
        // extension_ui_request / available_commands_update / turn_end / etc.
        break;
    }
  };

  let lineBuf = '';
  proc.stdout.on('data', (d) => {
    lineBuf += d.toString();
    let idx;
    while ((idx = lineBuf.indexOf('\n')) >= 0) {
      const line = lineBuf.slice(0, idx).trim();
      lineBuf = lineBuf.slice(idx + 1);
      if (line) handleLine(line);
    }
  });

  proc.on('exit', (code) => {
    if (!sawAgentEnd) {
      logger.error(`OMP process exited before agent_end [${label}] code=${code}`, { context: 'OmpClient', runKey });
      emitResult('error_during_execution', `omp_process_exit:${code ?? 'null'}`);
    }
    end();
  });

  proc.on('error', (err) => {
    logger.error(`OMP process error [${label}]: ${err.message}`, { context: 'OmpClient', runKey });
    emitResult('error_during_execution', `omp_spawn_error: ${err.message}`);
    end();
  });

  // Per-turn timeout — a silent OMP process (no ready handshake, no agent_end)
  // would otherwise hang the run forever; the CLI-side --max-time cap is
  // best-effort and this guard is the backstop that owns the process tree.
  const timeoutGuard = withTimeout({
    minutes: resolveEngineTimeoutMinutes('omp', timeoutMinutes),
    label: 'omp',
    context: 'OmpClient',
    turnKey: runKey,
    onTimeout: () => {
      emitResult('error_during_execution', 'omp_timeout');
      end();
    },
    child: proc,
  });

  if (knowledgeToken) proc.stdin.on('error', () => failStartup('omp_knowledge_rpc_write_failed'));

  return {
    async sendPrompt(message) {
      if (closed) throw new Error('OMP process already closed');
      if (!sawReady || !knowledgeVerified) {
        let timer;
        try {
          await Promise.race([
            startup,
            new Promise((_, reject) => {
              timer = setTimeout(() => reject(new Error('OMP RPC startup timeout')), 30000);
            }),
          ]);
        } catch (error) {
          if (!knowledgeToken) throw error;
          failStartup('omp_knowledge_startup_timeout');
        } finally { clearTimeout(timer); }
      }
      if (closed) return;
      proc.stdin.write(`${JSON.stringify({ type: 'prompt', message })}\n`);
    },
    close() {
      timeoutGuard.cancel();
      end();
      killTree(proc);
    },
    get killed() { return proc.killed || proc.exitCode !== null; },
    async *[Symbol.asyncIterator]() {
      while (true) {
        if (queue.length > 0) {
          yield queue.shift();
          continue;
        }
        if (closed) return;
        await new Promise(resolve => { wake = resolve; });
      }
    },
  };
}

// ── Start Diagnosis via OMP ──
export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
  ontology = null, enhancement = null,
  analysisIntent = 'deep-diagnosis',
  preprocessingMode = null,
  lineMemory = null, knowledgeTransport = null,
}) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const ompSession = parseOmpSessionId(sessionId);
  const isResume = !!ompSession;
  if (knowledgeTransport !== null) validateKnowledgeTransport(knowledgeTransport, isResume);

  const { dataPaths, promptTarget } = resolveAnalysisTarget(isResume ? { mode: 'resume' } : analysisTarget);

  let prompt;
  if (isResume) {
    // Clean continuation — the session already carries the pipeline context.
    prompt = (followUpMessage || 'Continue.').replace(/[\x00-\x08\x0A-\x1F]/g, (c) => (c === '\n' ? '\n' : '')).trim();
  } else {
    // OMP discovers .claude/skills natively; point it at the skill explicitly
    // and inline the runtime protocol (avoiding oversized argv payloads).
    // A non-default analysis intent re-points the skill reference at the
    // intent's own skill — buildIntentDirective marks the pipeline rules as
    // superseded for that run.
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
    prompt = `${buildRuntimeProtocol(sceneName, lang)}

${skillRef}

${buildPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)}${buildIntentDirective(analysisIntent, sceneName, { preprocessingMode })}${buildOntologyDirective(ontology)}${buildEnhancementDirective(enhancement)}${buildLineMemoryDirective(lineMemory)}`;
  }
  if (knowledgeTransport) {
    prompt += buildMemoryToolDirective(knowledgeTransport)
      .replace('memory_search', KNOWLEDGE_TOOLS[0]).replace('memory_get', KNOWLEDGE_TOOLS[1]);
  }

  const sessionDir = runSessionDir(runId);
  // The CLI cap and the JS process-tree guard remain in force for both modes.
  const label = `omp-diagnosis:${runId}`;
  const { proc } = spawnOmpRpc({ sessionDir, resume: isResume, label, timeoutMinutes, knowledgeTransport });
  const query = createOmpQuery(proc, { runKey: runId, maxTurns, label, timeoutMinutes, knowledgeToken: knowledgeTransport?.token });

  query.sendPrompt(prompt).catch(err => {
    logger.error(`OMP sendPrompt failed for ${runId}: ${err.message}`, { context: 'OmpClient', runId });
    query.close();
  });

  query.sessionId = ompRunSessionId(runId);

  return {
    query,
    dataPaths,
    prompt,
    getSessionId: () => ompRunSessionId(runId),
    runId,
    isResume,
  };
}

// ── Session chat: continue the run's OMP session with a follow-up message ──
export function startSessionChat({ runId, sessionId, message, maxTurns = 1 }) {
  const ompSession = parseOmpSessionId(sessionId);
  if (!ompSession) {
    const err = new Error('No valid OMP session ID for selected diagnosis session');
    err.status = 400;
    throw err;
  }

  const sessionDir = runSessionDir(ompSession.id);
  const { proc } = spawnOmpRpc({ sessionDir, resume: true, label: `omp-chat:${runId}` });
  const query = createOmpQuery(proc, { runKey: runId, maxTurns, label: `omp-chat:${runId}` });

  const text = (message || '').replace(/[\x00-\x08]/g, '').trim();
  query.sendPrompt(text).catch(err => {
    logger.error(`OMP chat sendPrompt failed for ${runId}: ${err.message}`, { context: 'OmpClient', runId });
    query.close();
  });

  query.sessionId = sessionId;

  return { query, runId, sessionId };
}

// ── Chat engine (chat.service.mjs OMP branch) ──
export function startChatQuery({ chatId, prompt, resume = false, maxTurns = 0 }) {
  const sessionDir = chatSessionDir(chatId);
  const { proc } = spawnOmpRpc({ sessionDir, resume, label: `omp-webchat:${chatId}` });
  const query = createOmpQuery(proc, { runKey: chatId, maxTurns, label: `omp-webchat:${chatId}` });

  query.sendPrompt(prompt).catch(err => {
    logger.error(`OMP webchat sendPrompt failed for ${chatId}: ${err.message}`, { context: 'OmpClient', chatId });
    query.close();
  });

  query.sessionId = ompChatSessionId(chatId);

  return query;
}

export function deleteChatArtifacts(chatId) {
  const dir = join(PROJECT_ROOT, ompConfig().chat_session_root || 'workspace/.omp-chats', chatId);
  let removed = false;
  try {
    if (existsSync(dir)) {
      rmSync(dir, { recursive: true, force: true });
      removed = true;
    }
  } catch (e) {
    logger.warn(`Failed to remove OMP chat artifacts for ${chatId}: ${e.message}`, { context: 'OmpClient', chatId });
  }
  return removed;
}

// ── Standardized-event passthrough ──
// The adapter already emits standardized messages; parsing is a no-op.
export function parseStreamEvent(message) {
  if (!message || typeof message !== 'object') return null;
  return message;
}

// ── Query registry (mirrors claude-client for stop/close semantics) ──
const activeQueries = new Map();

export function registerChild(runId, query) {
  activeQueries.set(runId, query);
}

export function closeQuery(runId) {
  const query = activeQueries.get(runId);
  if (query) {
    try { query.close(); } catch { /* ignore */ }
    activeQueries.delete(runId);
  }
}

export async function writeAnswer(runId, message) {
  const query = activeQueries.get(runId);
  if (!query) return false;
  try {
    await query.sendPrompt(message);
    return true;
  } catch {
    return false;
  }
}

// ── Health probe: verify the OMP binary actually executes ──
export function probeOmpEngine() {
  return new Promise(resolve => {
    const binary = resolveOmpBinary();
    const timeoutMs = ompConfig().health_timeout_ms || 8000;
    let settled = false;
    const done = (result) => {
      if (!settled) { settled = true; resolve(result); }
    };

    let proc;
    try {
      proc = spawnResolvedCli(binary, ['--version'], { cwd: PROJECT_ROOT, context: 'OmpClient' });
    } catch (e) {
      done({ available: false, binary, error: e.message });
      return;
    }

    let out = '';
    const timer = setTimeout(() => {
      try { proc.kill(); } catch { /* ignore */ }
      done({ available: false, binary, error: `timeout after ${timeoutMs}ms` });
    }, timeoutMs);

    proc.stdout.on('data', d => { out += d.toString(); });
    proc.on('error', (e) => {
      clearTimeout(timer);
      done({ available: false, binary, error: e.message });
    });
    proc.on('exit', (code) => {
      clearTimeout(timer);
      const version = (out.match(/omp\/(\S+)/) || [])[1] || out.trim().split(/\r?\n/)[0] || null;
      done({ available: code === 0, binary, version, raw: out.trim().slice(0, 100) });
    });
  });
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
