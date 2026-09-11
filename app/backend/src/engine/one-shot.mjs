// One-Shot turn engine base — shared substrate for the one-shot CLI family
// (gemini / copilot / cursor / crush / goose / pi).
//
// Process model (多 Harness 架构 · 原则 3): every turn spawns one child
// process; the turn ends when the process exits. Session continuity relies
// on the engine's own session id + resume flags.
//
// Engine differences collapse into an EngineSpec:
//   buildArgs({ prompt, promptFile, resumeSessionId }) → argv (flags/paths only)
//   promptDelivery: 'stdin' (default) | 'argFile' (@file position arg) | 'arg'
//   parseLine(lineText | jsonObj, ctx) → standardized event(s) or null
//   extractSession(evt) → engine session id | null   (via ctx.session)
//   parseSessionId(dbMarker) → { sessionId, resumable } | null
//   versionArgs → availability probe flags
//
// Output contract: identical to claude-client / omp-client — an async
// iterable of Claude-SDK-shaped messages (system/assistant/user/result),
// a close() handle and a `killed` flag, so diagnosis.service consumes all
// engines through one consumption loop.

import { mkdtempSync, writeFileSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { spawnCli, killTree, stderrTailRef } from './cli-common.mjs';
import logger from '../utils/logger.mjs';

let argFileSeq = 0;

function writePromptArgFile(id, prompt) {
  const dir = mkdtempSync(join(tmpdir(), `idd-${id}-`));
  const file = join(dir, `prompt-${Date.now()}-${++argFileSeq}.txt`);
  writeFileSync(file, prompt, 'utf-8');
  return { file, dir };
}

/**
 * Run one one-shot turn. Returns a query object:
 *   { [Symbol.asyncIterator], close(), killed, sessionId, exitPromise }
 * `sessionId` is `<engine>:`-prefixed (opaque for the DB, parseable by the
 * owning engine module — mirrors omp-client's session markers).
 */
export function createOneShotTurn(spec, {
  prompt, resumeSessionId = null, timeoutMinutes = 0, turnKey = '',
}) {
  const id = spec.id;

  // argFile delivery materializes the prompt BEFORE buildArgs so the spec can
  // place `@<path>` in argv (pi mode — bypasses the Windows ~8K cmdline cap).
  let argFileMeta = null;
  if ((spec.promptDelivery || 'stdin') === 'argFile') {
    argFileMeta = writePromptArgFile(id, prompt);
  }

  let args;
  try {
    args = spec.buildArgs({ prompt, promptFile: argFileMeta?.file || null, resumeSessionId });
  } catch (e) {
    if (argFileMeta) { try { rmSync(argFileMeta.dir, { recursive: true, force: true }); } catch { /* ignore */ } }
    logger.error(`[${id}] buildArgs failed: ${e.message}`, { context: 'OneShot', turnKey });
    return closedQueryWithImmediateError(id, `${id}_buildargs_error: ${e.message}`);
  }

  const proc = spawnCli(id, args, { env: spec.engineEnv ? spec.engineEnv({ resumeSessionId }) : {} });
  const getStderrTail = stderrTailRef(proc);
  const startedAt = Date.now();

  const queue = [];
  let wake = null;
  let closed = false;
  let sawResult = false;
  // sessionMarker specs (goose/crush) resume via opaque run markers; engine
  // specs (gemini/cursor/…) overwrite the unbound fallback once the engine
  // reports its own session id (re-emitting init so the service persists it).
  const useRunMarker = spec.sessionMarker === true;
  let sessionId = useRunMarker
    ? `${id}:run:${turnKey || Date.now()}`
    : `${id}:unbound:${turnKey || Date.now()}`;
  let rawEngineSession = null;
  let numTurns = 0;
  const unknownEvents = { count: 0 };

  const push = (msg) => { queue.push(msg); if (wake) { wake(); wake = null; } };
  const end = () => {
    if (argFileMeta) {
      try { rmSync(argFileMeta.dir, { recursive: true, force: true }); } catch { /* ignore */ }
      argFileMeta = null;
    }
    closed = true;
    if (wake) { wake(); wake = null; }
  };

  const emitInit = () => {
    push({
      type: 'system',
      subtype: 'init',
      session_id: sessionId,
      engine: id,
      model: spec.model || null,
    });
  };

  const emitResult = (subtype, stopReason) => {
    if (sawResult) return;
    sawResult = true;
    push({
      type: 'result',
      subtype,
      duration_ms: Date.now() - startedAt,
      num_turns: numTurns,
      total_cost_usd: null,
      stop_reason: stopReason || subtype,
      session_id: sessionId,
    });
  };

  // Shared mapper context — engine specs use these to emit standardized msgs.
  const ctx = {
    engine: id,
    session: (sid) => {
      if (sid && !rawEngineSession && !useRunMarker) {
        rawEngineSession = sid;
        sessionId = `${id}:${sid}`;
        emitInit(); // re-emit so diagnosis.service persists the real session id
      }
    },
    turn: () => { numTurns += 1; },
    assistant: (content) => push({ type: 'assistant', message: { role: 'assistant', content } }),
    text: (t) => ctx.assistant([{ type: 'text', text: String(t) }]),
    toolUse: (tool) => ctx.assistant([{
      type: 'tool_use', id: tool.id || `tool_${numTurns}_${tool.name || 'tool'}`, name: tool.name || 'tool', input: tool.input || {},
    }]),
    thinking: (t) => ctx.assistant([{ type: 'thinking', thinking: String(t || '') }]),
    toolResult: (r) => push({
      type: 'user',
      message: {
        role: 'user',
        content: [{
          type: 'tool_result',
          tool_use_id: r.toolUseId || r.id || '',
          content: typeof r.content === 'string' ? r.content : JSON.stringify(r.content ?? ''),
          is_error: r.isError === true,
        }],
      },
    }),
    result: (subtype, stopReason) => emitResult(subtype, stopReason),
    unknown: (kind) => {
      unknownEvents.count += 1;
      void kind;
    },
  };

  const handleLine = (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    let evt = null;
    try { evt = JSON.parse(trimmed); } catch { /* plain text line */ }
    try {
      if (spec.parseLine) {
        const out = spec.parseLine(evt ?? trimmed, ctx);
        if (Array.isArray(out)) out.forEach(push);
        else if (out) push(out);
      } else if (spec.mode === 'plaintext') {
        // Plain-text engines (crush): every stdout line is assistant narration.
        ctx.text(trimmed);
      } else if (evt && typeof evt === 'object') {
        ctx.unknown(evt.type || 'object');
      }
    } catch (e) {
      // Schema drift must never crash the turn — count and continue.
      logger.warn(`[${id}] parseLine error (counted, continuing): ${e.message}`, { context: 'OneShot', turnKey });
      ctx.unknown('parse_error');
    }
  };

  let lineBuf = '';
  proc.stdout.on('data', (d) => {
    lineBuf += d.toString();
    let idx;
    while ((idx = lineBuf.indexOf('\n')) >= 0) {
      const line = lineBuf.slice(0, idx);
      lineBuf = lineBuf.slice(idx + 1);
      handleLine(line);
    }
  });
  proc.stderr.on('data', () => { /* captured via stderrTailRef; engine stderr is informational */ });

  emitInit();

  // Prompt delivery — stdin (default), @argFile (already in argv), or arg.
  const delivery = spec.promptDelivery || 'stdin';
  try {
    if (delivery === 'stdin') {
      proc.stdin.write(prompt);
      proc.stdin.end();
    } else {
      // stdin EOF even for arg/argFile delivery — engines waiting on stdin must not hang.
      proc.stdin.end();
    }
  } catch (e) {
    logger.warn(`[${id}] prompt delivery failed: ${e.message}`, { context: 'OneShot', turnKey });
  }

  // Timeout guard (timeoutMinutes; 0 = unlimited).
  let timeoutTimer = null;
  const timeoutMs = (timeoutMinutes || 0) * 60 * 1000;
  if (timeoutMs > 0) {
    timeoutTimer = setTimeout(() => {
      logger.error(`[${id}] turn timed out after ${timeoutMs}ms — killing process tree`, { context: 'OneShot', turnKey });
      emitResult('error_during_execution', `${id}_timeout`);
      killTree(proc);
    }, timeoutMs);
  }

  const exitPromise = new Promise((resolve) => {
    proc.on('error', (err) => {
      logger.error(`[${id}] spawn error: ${err.message}`, { context: 'OneShot', turnKey });
      emitResult('error_during_execution', `${id}_spawn_error: ${err.message}`);
      end();
      resolve({ code: null, error: err.message });
    });
    proc.on('exit', (code, signal) => {
      if (timeoutTimer) clearTimeout(timeoutTimer);
      if (!sawResult) {
        if (code === 0) {
          emitResult('success', 'success');
        } else {
          const tail = getStderrTail().split(/\r?\n/).filter(Boolean).slice(-3).join(' | ');
          emitResult('error_during_execution', `${id.toUpperCase()}_EXIT_${code ?? signal}${tail ? `: ${tail.slice(0, 300)}` : ''}`);
        }
      }
      end();
      resolve({ code, signal });
    });
  });

  return {
    engine: id,
    get sessionId() { return sessionId; },
    exitPromise,
    unknownEventCount: () => unknownEvents.count,
    close() {
      if (!sawResult) {
        emitResult('error_during_execution', `${id}_aborted`);
      }
      killTree(proc);
      closed = true;
      if (wake) { wake(); wake = null; }
    },
    get killed() {
      return proc.killed || proc.exitCode !== null || proc.signalCode !== null;
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

function closedQueryWithImmediateError(id, reason) {
  const queue = [{
    type: 'result',
    subtype: 'error_during_execution',
    duration_ms: 0,
    num_turns: 0,
    total_cost_usd: null,
    stop_reason: reason,
    session_id: `${id}:error`,
  }];
  return {
    engine: id,
    sessionId: `${id}:error`,
    exitPromise: Promise.resolve({ code: 1 }),
    close() { /* already closed */ },
    get killed() { return true; },
    async *[Symbol.asyncIterator]() {
      while (queue.length) yield queue.shift();
    },
  };
}

/**
 * Build the standard engine client module shape consumed by
 * diagnosis.service.mjs, parameterized by a one-shot EngineSpec.
 */
export function createOneShotEngineClient(spec, { buildPrompt, defaultTimeoutMinutes = 0 } = {}) {
  const activeQueries = new Map();

  function startDiagnosis({
    analysisTarget, userQuestion, sceneName,
    runId, maxTurns = 0, timeoutMinutes = 0,
    reportLanguage, followUpMessage, sessionId = null,
    ontology = null, enhancement = null,
  }) {
    void maxTurns; // one-shot engines loop internally; turn budget == timeout
    const parsed = spec.parseSessionId ? spec.parseSessionId(sessionId) : null;
    const resumeSessionId = parsed?.resumable ? parsed.sessionId : null;
    const isResume = !!resumeSessionId;

    let dataPaths = [];
    let prompt;
    if (isResume) {
      prompt = String(followUpMessage || 'Continue.').trim();
    } else if (buildPrompt) {
      const built = buildPrompt({
        analysisTarget, userQuestion, sceneName, reportLanguage,
        followUpMessage, ontology, enhancement,
      });
      dataPaths = built.dataPaths || [];
      prompt = built.prompt;
    } else {
      prompt = followUpMessage || userQuestion || 'Continue.';
    }

    const query = createOneShotTurn(spec, {
      prompt,
      resumeSessionId,
      timeoutMinutes: timeoutMinutes || defaultTimeoutMinutes,
      turnKey: runId,
    });
    activeQueries.set(runId, query);
    return { query, dataPaths, prompt, getSessionId: () => query.sessionId, runId, isResume };
  }

  function startSessionChat({ runId, sessionId, message }) {
    const parsed = spec.parseSessionId ? spec.parseSessionId(sessionId) : null;
    if (!parsed?.resumable) {
      const err = new Error(`${spec.id} does not support session resume (session id: ${sessionId || 'none'}) — use Continue instead, which re-runs with the follow-up context`);
      err.status = 400;
      throw err;
    }
    const query = createOneShotTurn(spec, {
      prompt: String(message || '').trim(),
      resumeSessionId: parsed.sessionId,
      turnKey: runId,
    });
    activeQueries.set(runId, query);
    return { query, runId, sessionId };
  }

  function parseStreamEvent(message) {
    if (!message || typeof message !== 'object') return null;
    return message; // the adapter already emits standardized shapes
  }

  function registerChild(runId, query) {
    activeQueries.set(runId, query);
  }

  function closeQuery(runId) {
    const q = activeQueries.get(runId);
    if (q) {
      try { q.close(); } catch { /* ignore */ }
      activeQueries.delete(runId);
    }
  }

  return {
    spec,
    startDiagnosis, startSessionChat, parseStreamEvent, registerChild, closeQuery,
    probe: (options) => spec.probe(options),
  };
}
