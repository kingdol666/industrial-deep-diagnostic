// Diagnosis Service — Core business logic for diagnosis orchestration
// Handles: run creation, Claude process management, streaming, HITL, questions

import { v4 as uuid } from 'uuid';
import { readdir, stat, realpath } from 'fs/promises';
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, basename, relative } from 'path';
import {
  startDiagnosis, parseStreamEvent, isDangerousCommand,
  PROJECT_ROOT, WORKSPACE_DIR, DATA_DIR, registerChild, writeAnswer, closeQuery,
} from '../engine/claude-client.mjs';
import {
  createRun, setChild, getChild, updateStatus, getStatus, emit, closeRun,
  hasRun, subscribe, setMeta, getMeta, resetRun,
} from '../engine/diagnosis-engine.mjs';
import { stmts } from '../db/database.mjs';
import {
  config, diagnosis as diagConfig, security as secConfig,
  pipeline as pipeConfig, engine as engConfig,
} from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

// Track HITL requests per run: hitlId -> { resolve, child }
const hitlRequests = new Map();
let hitlSeq = 0;

// Guard: prevent double execution of the same run
const executingRuns = new Set();

// Validate that a resolved data path is safe (contained within project root)
export async function validateDataPath(dataPath) {
  if (dataPath.startsWith('/')) {
    if (!existsSync(dataPath)) {
      const err = new Error(`Data not found: ${dataPath}`);
      err.code = 'DATA_NOT_FOUND';
      throw err;
    }
    const resolved = await realpath(dataPath);
    const resolvedRoot = await realpath(PROJECT_ROOT);
    const rel = relative(resolvedRoot, resolved);
    if (rel.startsWith('..') || rel === '') {
      const err = new Error(`Path traversal blocked: ${dataPath}`);
      err.code = 'PATH_TRAVERSAL';
      err.status = 403;
      throw err;
    }
    return { absolutePath: resolved, relativePath: rel };
  }

  const candidates = [join(PROJECT_ROOT, dataPath), join(DATA_DIR, dataPath)];
  let resolved = null;

  for (const abs of candidates) {
    if (existsSync(abs)) {
      resolved = await realpath(abs);
      const resolvedRoot = await realpath(PROJECT_ROOT);
      const rel = relative(resolvedRoot, resolved);
      if (!rel.startsWith('..') && rel !== '') {
        return { absolutePath: resolved, relativePath: rel };
      }
    }
  }

  if (!resolved) {
    const err = new Error(`Data not found: ${dataPath}`);
    err.code = 'DATA_NOT_FOUND';
    throw err;
  }

  const err = new Error(`Path traversal blocked: ${dataPath}`);
  err.code = 'PATH_TRAVERSAL';
  err.status = 403;
  throw err;
}

// Create a new diagnosis run (DB + engine state)
export function createDiagnosisRun(params) {
  const { dataPath, folderPath, dataPaths, userQuestion, sceneName, maxTurns, timeoutMinutes, reportLanguage } = params;

  let mode, dataPathForDb, scene, dataFolder;

  if (dataPaths && Array.isArray(dataPaths) && dataPaths.length > 0) {
    mode = 'multi';
    dataPathForDb = JSON.stringify(dataPaths);
    const first = dataPaths[0];
    const parts = first.split('/');
    dataFolder = parts.length > 1 ? parts[0] : null;
    scene = sceneName || basename(first).replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  } else if (folderPath) {
    mode = 'folder';
    const relPath = folderPath.startsWith('/')
      ? relative(PROJECT_ROOT, folderPath)
      : folderPath;
    dataPathForDb = relPath;
    dataFolder = relPath;
    scene = sceneName || basename(relPath).replace(/[^a-zA-Z0-9]/g, '_');
  } else if (dataPath) {
    mode = 'file';
    const relPath = dataPath.startsWith('/')
      ? relative(PROJECT_ROOT, dataPath)
      : dataPath;
    dataPathForDb = relPath;
    const pathParts = relPath.split('/');
    dataFolder = pathParts.length > 1 ? pathParts[0] : null;
    scene = sceneName || basename(relPath).replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  } else {
    const err = new Error('One of dataPath, folderPath, or dataPaths is required');
    err.status = 400;
    throw err;
  }

  const runId = uuid().slice(0, diagConfig.run_id_length);
  const name = `${scene}_${runId}`;

  stmts.insertRun.run({
    runId,
    name,
    sceneName: scene,
    dataPath: dataPathForDb,
    dataFolder,
    userQuestion: userQuestion || '',
    model: config.claude.model,
    maxTurns: maxTurns ?? config.claude.max_turns,
    reportLanguage: reportLanguage || diagConfig.default_language,
  });

  createRun(runId);
  setMeta(runId, { timeoutMinutes: timeoutMinutes ?? config.claude.timeout_minutes });

  return { runId, name, status: 'pending', mode };
}

// List all runs enriched with engine status
export function listRuns() {
  const runs = stmts.getAllRuns.all();
  return runs.map(r => ({
    ...r,
    engineStatus: getStatus(r.run_id) || r.status,
  }));
}

// Get single run status
export function getRunStatus(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) return null;
  const engineStatus = getStatus(runId);
  return { ...run, engineStatus: engineStatus || run.status };
}

// Stop a running diagnosis
export function stopDiagnosis(runId) {
  closeQuery(runId);
  updateStatus(runId, 'stopped');
  stmts.updateRunStatus.run({ runId, status: 'stopped' });
  emit(runId, { type: 'status', data: { status: 'stopped' } });
}

// Resolve a HITL request
export function resolveHITLRequest(hitlId, approved) {
  const entry = hitlRequests.get(hitlId);
  if (!entry) return null;
  hitlRequests.delete(hitlId);
  entry.resolve(approved === true);
  return { hitlId, approved };
}

// Get pending HITL requests for a run
export function getPendingHITL(runId) {
  const pending = [];
  for (const [id, entry] of hitlRequests) {
    if (entry.runId === runId) {
      pending.push({ hitlId: id, runId });
    }
  }
  return pending;
}

// Send a chat message — close current query and resume session with message
export function sendChatMessage(runId, message) {
  closeQuery(runId);
  executingRuns.delete(runId);
  try {
    continueDiagnosis(runId, message);
    return true;
  } catch {
    return false;
  }
}

// Continue / retry a failed or stopped run
export function continueDiagnosis(runId, followUpMessage) {
  const run = stmts.getRunById.get(runId);
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    throw err;
  }
  // Allow continue for ANY non-pending status
  if (run.status === 'pending') {
    const err = new Error('Run is still pending — execute it first');
    err.status = 400;
    throw err;
  }

  // Clear execution guard from previous run (enables re-entry)
  executingRuns.delete(runId);

  // Close any existing query — we're starting fresh
  closeQuery(runId);

  stmts.updateRunStatus.run({ runId, status: 'running' });

  setMeta(runId, {
    followUpMessage: followUpMessage || null,
    sessionId: run.session_id || null,
  });

  executeDiagnosis(runId, run, true);
  return { runId, status: 'running', continued: true };
}

// Track active question sessions (child is SIGSTOPPED waiting for user answer)
const questionSessions = new Map();

// Submit answer to AskUserQuestion — write tool_result to stdin + SIGCONT the paused child
export function answerQuestion(runId, questionId, toolUseId, answers) {
  const answerText = Object.entries(answers)
    .map(([q, a]) => `Q: ${q}\nA: ${a}`)
    .join('\n\n');

  const responseMessage = {
    type: 'user',
    message: {
      role: 'user',
      content: [{
        type: 'tool_result',
        tool_use_id: toolUseId,
        content: [{ type: 'text', text: answerText }],
      }],
    },
  };

  const wrote = writeAnswer(runId, responseMessage);
  if (!wrote) {
    logger.error(`Failed to write answer for run ${runId}`, { context: 'Diagnosis', runId });
    return false;
  }

  // SIGCONT the paused child so Claude reads the real tool_result and continues naturally
  const child = getChild(runId);
  if (child && child.pid) {
    try { process.kill(child.pid, 'SIGCONT'); } catch (e) { /* ignore */ }
  }

  questionSessions.delete(runId);

  emit(runId, {
    type: 'question_result',
    data: { questionId, answers, timestamp: new Date().toISOString() },
  });

  return true;
}

// Core diagnosis execution — spawns Claude, streams events, handles HITL
// Core diagnosis execution — uses SDK query, iterates stream events, handles HITL and AskUserQuestion
async function executeDiagnosis(runId, run, isRetry = false) {
  // Guard: prevent double execution of the same run
  if (executingRuns.has(runId)) {
    logger.warn(`executeDiagnosis called twice for run: ${runId} — skipping duplicate`, { context: 'Diagnosis', runId });
    return;
  }
  executingRuns.add(runId);

  if (isRetry) {
    resetRun(runId);
  } else {
    if (!hasRun(runId)) createRun(runId);
  }

  updateStatus(runId, 'running');
  stmts.updateRunStatus.run({ runId, status: 'running' });
  emit(runId, { type: 'status', data: { status: 'running', runId, isRetry } });

  let analysisTarget;
  const dp = run.data_path;
  if (dp && dp.startsWith('[')) {
    analysisTarget = { mode: 'multi', files: JSON.parse(dp) };
  } else if (run.data_folder && dp === run.data_folder) {
    analysisTarget = { mode: 'folder', folderPath: dp };
  } else {
    analysisTarget = { mode: 'file', dataPath: dp };
  }

  const hitlTimeoutMs = secConfig.hitl_auto_deny_seconds * 1000;

  try {
    const meta = getMeta(runId);
    const followUpMessage = meta.followUpMessage || null;
    const sessionId = meta.sessionId || null;

    // Snapshot workspace dirs BEFORE spawning to detect new dirs
    const preExistingDirs = snapshotWorkspaceDirs();

    const result = startDiagnosis({
      analysisTarget,
      userQuestion: run.user_question,
      sceneName: run.scene_name,
      runId,
      maxTurns: run.max_turns,
      timeoutMinutes: run.timeout_minutes,
      reportLanguage: run.report_language || diagConfig.default_language,
      followUpMessage,
      sessionId,
    });

    const query = result.query;
    setChild(runId, query);
    registerChild(runId, query);

    // Store session ID from SDK
    const sdkSessionId = query.sessionId || null;
    if (!sessionId && sdkSessionId) {
      stmts.updateRunSession.run({ runId, sessionId: sdkSessionId });
      setMeta(runId, { sessionId: sdkSessionId });
    }

    // ── Iterate SDK messages ──
    for await (const msg of query) {
      const parsed = parseStreamEvent(msg);
      if (!parsed) continue;

      if (parsed.type === 'system') {
        const subtype = parsed.subtype || 'system';
        emit(runId, { type: 'system', subtype, data: parsed });
        if (parsed.subtype === 'init') {
          stmts.insertLog.run({
            runId, role: 'system',
            content: JSON.stringify({ subtype: 'init', model: parsed.model, tools: parsed.tools?.length }),
            messageType: 'system', toolName: null,
          });
          // Capture session ID from SDK init event (may come after start)
          if (parsed.session_id && !getMeta(runId).sessionId) {
            stmts.updateRunSession.run({ runId, sessionId: parsed.session_id });
            setMeta(runId, { sessionId: parsed.session_id });
          }
        }
      } else if (parsed.type === 'assistant') {
        const content = parsed.message?.content || [];
        for (const block of content) {
          if (block.type === 'text') {
            stmts.insertLog.run({ runId, role: 'assistant', content: block.text, messageType: 'text', toolName: null });
            emit(runId, { type: 'message', data: { role: 'assistant', content: block.text } });
          } else if (block.type === 'tool_use') {
            stmts.insertLog.run({ runId, role: 'assistant', content: JSON.stringify(block.input), messageType: 'tool_use', toolName: block.name });

            // HITL: dangerous Bash commands
            if (block.name === 'Bash' && block.input?.command) {
              const danger = isDangerousCommand(block.input.command);
              if (danger) {
                const hitlId = `hitl_${runId}_${++hitlSeq}`;
                emit(runId, { type: 'hitl_request', data: { hitlId, runId, command: block.input.command, riskLevel: danger.level, riskDesc: danger.desc, dangerMatch: danger.match, toolUseId: block.id } });
                // With SDK and bypassPermissions, dangerous commands are auto-allowed
                // HITL approval is informational in SDK mode; auto-deny after timeout
              }
            }

            // AskUserQuestion detection
            if (block.name === 'AskUserQuestion' && block.input?.questions) {
              const questionId = `q_${runId}_${Date.now()}`;
              questionSessions.set(runId, { questionId, toolUseId: block.id });
              emit(runId, {
                type: 'question',
                data: {
                  questionId, toolUseId: block.id,
                  questions: block.input.questions.map(q => ({
                    question: q.question || '',
                    header: q.header || '',
                    options: (q.options || []).map(o => ({
                      label: o.label || '',
                      description: o.description || '',
                      preview: o.preview || '',
                    })),
                    multiSelect: q.multiSelect || false,
                  })),
                },
              });
            }

            emit(runId, { type: 'tool_use', data: { name: block.name, input: block.input, id: block.id } });
          } else if (block.type === 'thinking') {
            emit(runId, { type: 'thinking', data: { content: block.thinking?.slice(0, 500) || '' } });
          }
        }
      } else if (parsed.type === 'user') {
        const userContent = parsed.message?.content || [];
        for (const block of userContent) {
          if (block.type === 'tool_result') {
            const resultContent = block.content;
            const summary = typeof resultContent === 'string'
              ? resultContent.slice(0, 300)
              : (resultContent?.map?.(c => typeof c === 'string' ? c : c?.text).join('').slice(0, 300) || '');
            stmts.insertLog.run({ runId, role: 'tool', content: summary, messageType: 'tool_result', toolName: block.tool_use_id || null });
            emit(runId, { type: 'tool_result', data: { toolUseId: block.tool_use_id, summary, isError: block.is_error || false } });
          }
        }
      } else if (parsed.type === 'result') {
        emit(runId, { type: 'stats', data: { subtype: parsed.subtype, durationMs: parsed.duration_ms, numTurns: parsed.num_turns, totalCost: parsed.total_cost_usd, stopReason: parsed.stop_reason } });
        // Handle completion
        try {
          const runDir = await findLatestRunDir(run.scene_name, preExistingDirs);
          let reportPath = null, score = null, verdict = null;
          if (runDir) {
            reportPath = join(runDir, 'report.md');
            if (existsSync(reportPath)) {
              const reportContent = readFileSync(reportPath, 'utf-8');
              const scoreMatch = reportContent.match(/Judge Score:\s*(\d+)\/100/);
              if (scoreMatch) score = parseInt(scoreMatch[1]);
              const verdictMatch = reportContent.match(/Judge Score:.*?\((\w+)/);
              if (verdictMatch) verdict = verdictMatch[1];
              stmts.updateRunWorkspace.run({ runId, workspacePath: relative(PROJECT_ROOT, runDir) });
              stmts.updateRunReport.run({ runId, reportPath: relative(PROJECT_ROOT, reportPath) });
            }
          }
          if (parsed.subtype === 'success') {
            updateStatus(runId, 'completed');
            stmts.updateRunCompleted.run({ runId, status: 'completed', score: score ?? null, verdict: verdict ?? null, reportPath: reportPath ? relative(PROJECT_ROOT, reportPath) : null });
            emit(runId, { type: 'complete', data: { status: 'completed', reportPath, score, verdict } });
          } else {
            updateStatus(runId, 'failed');
            stmts.failRun.run({ runId, error: `Query stopped: ${parsed.stop_reason || parsed.subtype}` });
            emit(runId, { type: 'complete', data: { status: 'failed', error: `Query stopped: ${parsed.stop_reason || parsed.subtype}` } });
          }
        } catch (err) {
          updateStatus(runId, 'failed');
          emit(runId, { type: 'error', data: { status: 'failed', error: err.message } });
        }
      } else if (parsed.type === 'stream_event') {
        const ev = parsed.event;
        if (ev?.type === 'task_progress') {
          const raw = ev.events || ev.task?.events || [];
          emit(runId, { type: 'task_progress', data: { taskId: ev.task?.id || ev.task_id || '', agentName: ev.task?.name || ev.name || '', status: ev.task?.status || ev.status || '', currentStep: ev.message || ev.current_step || '', progress: ev.progress || null, events: raw.slice(0, 50) } });
        } else {
          emit(runId, { type: 'stream_event', subtype: ev?.type || 'event', data: ev });
        }
      } else if (parsed.type === 'task_progress') {
        const raw = parsed.events || [];
        emit(runId, { type: 'task_progress', data: { taskId: parsed.task_id || parsed.id || '', agentName: parsed.name || parsed.task_name || '', status: parsed.status || '', currentStep: parsed.current_step || parsed.message || '', progress: parsed.progress || null, events: raw.slice(0, 50) } });
      } else {
        emit(runId, { type: 'unknown', subtype: parsed.type || 'unknown', data: parsed });
      }
    }

    // Stream ended
    executingRuns.delete(runId);
    setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);

  } catch (err) {
    executingRuns.delete(runId);
    updateStatus(runId, 'failed');
    logger.error(`Diagnosis execution error for run ${runId}: ${err.message}`, { context: 'Diagnosis', runId });
    emit(runId, { type: 'error', data: { status: 'failed', error: err.message } });
    setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
  }
}
export function snapshotWorkspaceDirs() {
  if (!existsSync(WORKSPACE_DIR)) return new Set();
  return new Set(readdirSync(WORKSPACE_DIR));
}

async function findLatestRunDir(sceneName, knownDirs = new Set()) {
  if (!existsSync(WORKSPACE_DIR)) return null;
  const entries = await readdir(WORKSPACE_DIR);
  const escapedName = sceneName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const dirPattern = new RegExp(`_${escapedName}$`);

  // Collect all matching dirs, excluding known ones (from snapshot)
  // and directories already claimed by other runs in the DB
  const claimedDirs = new Set(
    stmts.getClaimedWorkspacePaths.all().map(r => r.workspace_path)
  );

  let latest = null, latestTime = 0;
  for (const entry of entries) {
    if (!dirPattern.test(entry)) continue;
    const fullPath = join(WORKSPACE_DIR, entry);
    const relPath = `workspace/diagnostic-runs/${entry}`;
    // Skip directories that existed before this run started or are claimed by others
    if (knownDirs.has(entry) || claimedDirs.has(relPath)) continue;
    try {
      const s = await stat(fullPath);
      if (s.mtimeMs > latestTime) {
        latestTime = s.mtimeMs;
        latest = fullPath;
      }
    } catch {}
  }
  return latest;
}

export { hitlRequests, executeDiagnosis };

// ── SSE + streaming helpers ──
export function subscribeSSE(runId, callback) {
  return subscribe(runId, (event) => {
    let sseEvent;
    switch (event.type) {
      case 'status': sseEvent = 'status'; break;
      case 'message': sseEvent = 'message'; break;
      case 'tool_use': sseEvent = 'tool_use'; break;
      case 'tool_result': sseEvent = 'tool_result'; break;
      case 'thinking': sseEvent = 'thinking'; break;
      case 'system': sseEvent = 'system'; break;
      case 'stats': sseEvent = 'stats'; break;
      case 'log': sseEvent = 'log'; break;
      case 'question': sseEvent = 'question'; break;
      case 'hitl_request': sseEvent = 'hitl_request'; break;
      case 'hitl_result': sseEvent = 'hitl_result'; break;
      case 'complete': sseEvent = 'complete'; break;
      case 'error': sseEvent = 'error'; break;
      case 'task_progress': sseEvent = 'task_progress'; break;
      case 'question_result': sseEvent = 'question_result'; break;
      case 'stream_event': sseEvent = 'stream_event'; break;
      case 'unknown': sseEvent = 'unknown'; break;
      case 'stream_end': sseEvent = 'stream_end'; break;
      default: return;
    }
    callback(sseEvent, event.data);
  });
}

export function triggerDiagnosis(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) { const err = new Error('Run not found'); err.status = 404; throw err; }
  if (run.status !== 'pending') { const err = new Error(`Run is not pending (status: ${run.status})`); err.status = 400; throw err; }
  const existingQuery = getChild(runId);
  if (existingQuery && !existingQuery.closed) { const err = new Error('Run is already executing'); err.status = 409; throw err; }
  executeDiagnosis(runId, run);
  return { runId, status: 'running' };
}

export function startStream(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) return null;
  const currentStatus = getStatus(runId) || run.status;
  if ((currentStatus === 'completed' || currentStatus === 'failed') && !hasRun(runId)) {
    return { run, currentStatus, isFinished: true };
  }
  return { run, currentStatus, isFinished: false };
}
