// Session integrity — runId ↔ harness sessionId truth keeping (plan v2 Phase B0).
//
// Three invariants this module enforces:
//   1. restart semantics: a run that was only ever `pending` (its execution was
//      never started) is marked `stopped`, not left dangling (B0.1);
//   2. runId → sessionId mapping is complete: rows that lost/never captured a
//      session id are reconciled from the persisted event stream, the omp
//      session directory, or the deterministic omp marker (B0.3);
//   3. a chat/continue never crosses harnesses: the session id must belong to
//      the run's harness, otherwise resuming would look up a session that does
//      not exist in that engine (B0.4).
import { existsSync } from 'fs';
import { join } from 'path';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import { parseOmpSessionId, ompRunSessionId } from '../engine/omp-client.mjs';
import logger from '../utils/logger.mjs';

// Locally normalized: a stored harness id was already resolved at creation, so
// this only guards casing/emptiness. Importing it from diagnosis.service would
// create a cycle (that module imports this one).
function normalizeStoredHarness(value) {
  const id = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return id || 'claude';
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const GOOSE_PREFIX = 'goose:';

/** Which engine owns this session id (best-effort, format based). */
export function sessionKind(sessionId) {
  if (!sessionId || typeof sessionId !== 'string') return 'none';
  if (parseOmpSessionId(sessionId)) return 'omp';
  if (sessionId.startsWith(GOOSE_PREFIX)) return 'goose';
  if (UUID_RE.test(sessionId)) return 'claude';
  return 'unknown';
}

/** Harnesses that can resume an existing process-external session. */
const RESUMABLE = new Set(['claude', 'omp', 'goose']);

/** Engines that can actually resume a process-external session (single truth). */
export const RESUMABLE_HARNESSES = Object.freeze([...RESUMABLE]);

/**
 * Can `startSessionChat` work for this harness at all?
 * mock has an in-process scripted chat (used by the chat-contract E2E), so it
 * counts as chat-capable even though nothing survives a process restart.
 * Every other engine that lacks cross-process resume must go through a rebuild.
 */
export function engineSupportsSessionChat(harnessId) {
  const id = normalizeStoredHarness(harnessId);
  return RESUMABLE.has(id) || id === 'mock';
}

/** Does this run carry enough context to rebuild the analysis from scratch? */
export function hasRebuildContext(run) {
  return !!(run && (run.data_path || run.data_folder));
}

/**
 * Decide how a chat/continue turn is served, without side effects:
 *   { mode: 'session' }                         — resume the stored session;
 *   { mode: 'rebuild', reason }                 — full re-run, same harness;
 *   throws 409 RESUME_UNSUPPORTED               — nothing to resume or rebuild.
 *
 * Rationale: "继续对话" must work for every harness (the user clicks one
 * button). A non-resumable engine rebuilds with the same harness/intent/data;
 * only a run with no data context at all is genuinely unrecoverable.
 */
export function resolveChatRoute(run) {
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    err.code = 'RUN_NOT_FOUND';
    throw err;
  }
  const harness = normalizeStoredHarness(run.harness);
  if (run.session_id && engineSupportsSessionChat(harness)) {
    return { mode: 'session', harness };
  }
  if (hasRebuildContext(run)) {
    return {
      mode: 'rebuild',
      harness,
      reason: run.session_id ? 'engine_no_resume' : 'no_session',
    };
  }
  const err = new Error(
    `Run ${run.run_id} cannot be continued: the ${harness} engine has no resumable session `
    + 'and the run carries no data path to rebuild from. Start a new analysis with data.',
  );
  err.status = 409;
  err.code = 'RESUME_UNSUPPORTED';
  err.harness = harness;
  err.runId = run.run_id;
  throw err;
}

/** User-facing explanation emitted as a system line before a rebuild. */
export function rebuildNotice(route) {
  const label = String(route?.harness || '').toUpperCase();
  if (route?.reason === 'engine_no_resume') {
    return `该引擎（${label}）不支持会话级恢复，已按当前诊断上下文重建（同一引擎 / 同一分析意图 / 同一数据）。`;
  }
  return `该会话没有可恢复的历史 session，已按当前诊断上下文重新建立（同一引擎与同一分析意图）。`;
}

/**
 * Refuse a chat/continue whose stored session id cannot belong to the run's
 * harness. A silent engine switch is exactly how a session id becomes
 * unfindable, so this is a hard 409 rather than a fallback.
 * `unknown` session formats are allowed (some engines store opaque ids) but
 * reported as such by sessionMap().
 */
export function assertSessionHarnessMatch(run) {
  if (!run) return;
  const kind = sessionKind(run.session_id);
  if (kind === 'none' || kind === 'unknown') return;
  const harness = normalizeStoredHarness(run.harness);
  if (kind !== harness) {
    const err = new Error(
      `Session ${run.session_id} belongs to the ${kind} engine but this run is recorded as ${harness}. `
      + 'Refusing to switch engines — that would look up a session that does not exist. '
      + 'Use the original harness for this run.',
    );
    err.status = 409;
    err.code = 'RUN_HARNESS_MISMATCH';
    throw err;
  }
}

// ── chat turn policy + run anchor (B2/B3) ────────────────────────────────
// These live here (not in diagnosis.service) so the contract can be unit
// tested without pulling in the engine layer, whose timers keep the process
// alive.

export const CHAT_TURNS_DEFAULT = 8;
export const CHAT_TURNS_MAX = 20;

/** Clamp a requested chat turn budget; the old hard-coded 1 could not use tools. */
export function clampChatTurns(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return CHAT_TURNS_DEFAULT;
  return Math.min(CHAT_TURNS_MAX, Math.max(1, Math.trunc(n)));
}

/**
 * Resume-turn contract: a chat/continue turn sends the user's message VERBATIM
 * to the run's own harness session. No prompt scaffolding, run anchors or
 * skill directives are injected — the session already holds the run context
 * (and the harness is pinned to the one that created that session).
 */
export const CHAT_TURN_PASSTHROUGH = true;

/** Public mapping view (GET /api/diagnosis/session-map/:runId). */
export function sessionMap(run) {
  if (!run) return null;
  const kind = sessionKind(run.session_id);
  const harness = normalizeStoredHarness(run.harness);
  const matching = kind === 'none' || kind === 'unknown' || kind === harness;
  return {
    run_id: run.run_id,
    harness,
    session_id: run.session_id || null,
    session_kind: kind,
    resumable: matching && RESUMABLE.has(harness) && !!run.session_id,
    harness_matches_session: matching,
    // A completed/stopped run without a session id can still be reconciled from
    // its persisted event stream / omp session dir on the next startup.
    reconcilable: !run.session_id && ['completed', 'stopped', 'failed'].includes(run.status),
    workspace_path: run.workspace_path || null,
  };
}

// Recover a claude/omp session id from the persisted event stream: the init
// event carries `session_id` (claude) and omp emits its session metadata early.
function sessionFromEventStream(runId) {
  let rows;
  try {
    rows = stmts.getEventStreamByRunId.all(runId);
  } catch {
    return null;
  }
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    const row = rows[i];
    if (!row.payload_json) continue;
    let payload;
    try {
      payload = JSON.parse(row.payload_json);
    } catch {
      continue;
    }
    const sid = payload?.session_id || payload?.sessionId
      || payload?.data?.session_id || payload?.data?.sessionId;
    if (typeof sid === 'string' && sid.trim()) return sid.trim();
  }
  return null;
}

/**
 * Backfill missing session ids for terminal runs (B0.3).
 * Sources, in order: event stream init payload → omp session directory →
 * deterministic omp marker (only when the run's harness is omp).
 * @returns {{scanned:number, recovered:object[], failed:string[]}}
 */
export function reconcileSessionIds() {
  const rows = stmts.getRunsMissingSession.all();
  const recovered = [];
  const failed = [];
  for (const row of rows) {
    let sid = sessionFromEventStream(row.run_id);
    let source = sid ? 'event_stream' : null;
    if (!sid && normalizeStoredHarness(row.harness) === 'omp') {
      const dir = join(PROJECT_ROOT, 'workspace', '.omp-sessions', row.run_id);
      if (existsSync(dir)) {
        sid = ompRunSessionId(row.run_id);
        source = 'omp_session_dir';
      }
    }
    if (!sid) {
      failed.push(row.run_id);
      continue;
    }
    stmts.setRunSessionIfNull.run({ runId: row.run_id, sessionId: sid });
    recovered.push({ run_id: row.run_id, session_id: sid, source });
  }
  if (recovered.length || failed.length) {
    logger.info(
      `Session reconcile: recovered ${recovered.length}, unresolved ${failed.length}`
      + `${failed.length ? ` (${failed.slice(0, 5).join(', ')})` : ''}`,
      { context: 'Session' },
    );
  }
  return { scanned: rows.length, recovered, failed };
}

/**
 * Startup semantics (B0.1): pending runs never executed, so restarting the
 * server means they were terminated before execution → `stopped` (a state the
 * user can resume from), not `failed` (an execution error) and never left
 * dangling as `pending`. `running` rows keep the legacy `failed` mapping.
 */
export function recoverInterruptedRuns() {
  const pending = stmts.getPendingRuns.all();
  for (const row of pending) {
    stmts.markStopped.run({
      runId: row.run_id,
      error: 'Server restarted before execution — marked stopped (resumable)',
    });
  }
  if (pending.length) {
    logger.info(`Marked ${pending.length} pending run(s) as stopped after restart`, { context: 'Session' });
  }
  return { stopped: pending.map((r) => r.run_id) };
}
