// Diagnosis Service — Core business logic for diagnosis orchestration
// Handles: run creation, Claude process management, streaming, HITL, questions

import { v4 as uuid } from 'uuid';
import { readdir, stat, realpath } from 'fs/promises';
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, basename, relative } from 'path';
import {
  startDiagnosis, parseStreamLine, isDangerousCommand,
  PROJECT_ROOT, WORKSPACE_DIR, DATA_DIR, registerChild, writeAnswer,
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
  const child = getChild(runId);
  if (child && !child.killed) {
    child.kill('SIGTERM');
  }
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

// Send a chat message — ALWAYS resume session: kill current child, spawn new --resume
export function sendChatMessage(runId, message) {
  // Kill any running child process for this run
  const child = getChild(runId);
  if (child && !child.killed) {
    try { child.kill('SIGKILL'); } catch {}
    setChild(runId, null);
  }
  // Clear execution guard from the killed process so re-entry works
  executingRuns.delete(runId);

  // Resume the session with the user's message
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

  // Kill any existing child process — we're starting fresh
  const existingChild = getChild(runId);
  if (existingChild && !existingChild.killed) {
    try { existingChild.kill('SIGKILL'); } catch {}
    setChild(runId, null);
  }

  stmts.updateRunStatus.run({ runId, status: 'running' });

  setMeta(runId, {
    followUpMessage: followUpMessage || null,
    sessionId: run.session_id || null,
  });

  executeDiagnosis(runId, run, true);
  return { runId, status: 'running', continued: true };
}

// Submit answer to AskUserQuestion
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
  if (!wrote) return false;

  emit(runId, {
    type: 'question_result',
    data: { questionId, answers, timestamp: new Date().toISOString() },
  });

  return true;
}

// Core diagnosis execution — spawns Claude, streams events, handles HITL
function executeDiagnosis(runId, run, isRetry = false) {
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

  let child = null;
  const hitlTimeoutMs = secConfig.hitl_auto_deny_seconds * 1000;

  try {
    const meta = getMeta(runId);
    const timeoutMinutes = meta.timeoutMinutes || config.claude.timeout_minutes;
    const followUpMessage = meta.followUpMessage || null;
    const sessionId = meta.sessionId || null;

    // Snapshot workspace dirs BEFORE spawning Claude to detect new dirs later
    const preExistingDirs = snapshotWorkspaceDirs();

    const result = startDiagnosis({
      analysisTarget,
      userQuestion: run.user_question,
      sceneName: run.scene_name,
      runId,
      maxTurns: run.max_turns,
      timeoutMinutes,
      reportLanguage: run.report_language || diagConfig.default_language,
      followUpMessage,
      sessionId,
    });

    child = result.child;
    setChild(runId, child);
    registerChild(runId, child);

    let buffer = '';

    child.stdout.on('data', (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const parsed = parseStreamLine(line);
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
            // Capture Claude session_id only on FIRST run — don't overwrite on resume
            if (parsed.session_id && !run.session_id) {
              stmts.updateRunSession.run({ runId, sessionId: parsed.session_id });
            }
          }
        } else if (parsed.type === 'assistant') {
          const content = parsed.message?.content || [];
          for (const block of content) {
            if (block.type === 'text') {
              stmts.insertLog.run({
                runId, role: 'assistant', content: block.text,
                messageType: 'text', toolName: null,
              });
              emit(runId, {
                type: 'message',
                data: { role: 'assistant', content: block.text },
              });
            } else if (block.type === 'tool_use') {
              stmts.insertLog.run({
                runId, role: 'assistant',
                content: JSON.stringify(block.input),
                messageType: 'tool_use', toolName: block.name,
              });

              // HITL: Check for dangerous Bash commands
              if (block.name === 'Bash' && block.input?.command) {
                const danger = isDangerousCommand(block.input.command);
                if (danger) {
                  const hitlId = `hitl_${runId}_${++hitlSeq}`;

                  emit(runId, {
                    type: 'hitl_request',
                    data: {
                      hitlId, runId, command: block.input.command,
                      riskLevel: danger.level, riskDesc: danger.desc,
                      dangerMatch: danger.match, toolUseId: block.id,
                    },
                  });

                  if (child && !child.killed) {
                    try { process.kill(child.pid, 'SIGSTOP'); } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Diagnosis' }); }
                  }

                  const hitlPromise = new Promise((resolve) => {
                    hitlRequests.set(hitlId, { resolve, child, runId });

                    setTimeout(() => {
                      if (hitlRequests.has(hitlId)) {
                        hitlRequests.delete(hitlId);
                        emit(runId, {
                          type: 'hitl_result',
                          data: { hitlId, approved: false, reason: 'Timeout — auto-denied' },
                        });
                        try { process.kill(child.pid, 'SIGKILL'); } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Diagnosis' }); }
                        resolve(false);
                      }
                    }, hitlTimeoutMs);
                  });

                  hitlPromise.then((approved) => {
                    if (approved) {
                      emit(runId, { type: 'hitl_result', data: { hitlId, approved: true } });
                      try { process.kill(child.pid, 'SIGCONT'); } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Diagnosis' }); }
                    } else {
                      emit(runId, { type: 'hitl_result', data: { hitlId, approved: false, reason: 'Denied by user' } });
                      try { process.kill(child.pid, 'SIGKILL'); } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Diagnosis' }); }
                    }
                  });
                }
              }

              // AskUserQuestion detection
              if (block.name === 'AskUserQuestion' && block.input?.questions) {
                const questionId = `q_${runId}_${Date.now()}`;
                emit(runId, {
                  type: 'question',
                  data: {
                    questionId, toolUseId: block.id,
                    questions: block.input.questions.map(q => ({
                      question: q.question || '',
                      header: q.header || '',
                      options: q.options || [],
                      multiSelect: q.multiSelect || false,
                    })),
                  },
                });
              }

              emit(runId, {
                type: 'tool_use',
                data: { name: block.name, input: block.input, id: block.id },
              });
            } else if (block.type === 'thinking') {
              emit(runId, {
                type: 'thinking',
                data: { content: block.thinking?.slice(0, 500) || '' },
              });
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
              stmts.insertLog.run({
                runId, role: 'tool', content: summary,
                messageType: 'tool_result', toolName: block.tool_use_id || null,
              });
              emit(runId, {
                type: 'tool_result',
                data: { toolUseId: block.tool_use_id, summary, isError: block.is_error || false },
              });
            }
          }
        } else if (parsed.type === 'result') {
          emit(runId, {
            type: 'stats',
            data: {
              subtype: parsed.subtype, durationMs: parsed.duration_ms,
              numTurns: parsed.num_turns, totalCost: parsed.total_cost_usd,
              stopReason: parsed.stop_reason,
            },
          });
        } else if (parsed.type === 'task_progress') {
          emit(runId, {
            type: 'task_progress',
            data: {
              taskId: parsed.task_id || parsed.id || '',
              name: parsed.name || parsed.task_name || '',
              status: parsed.status || '',
              currentStep: parsed.current_step || parsed.message || '',
              progress: parsed.progress || null,
            },
          });
        } else if (parsed.type === 'stream_event' && parsed.event) {
          // Handle nested stream_event wrapper (newer Claude Code format)
          const ev = parsed.event;
          if (ev.type === 'task_progress') {
            emit(runId, {
              type: 'task_progress',
              data: {
                taskId: ev.task?.id || ev.task_id || '',
                name: ev.task?.name || ev.name || '',
                status: ev.task?.status || ev.status || '',
                currentStep: ev.message || ev.current_step || '',
                progress: ev.progress || null,
              },
            });
          } else {
            // Generic fallback for other stream_event types
            emit(runId, { type: 'stream_event', subtype: ev.type, data: ev });
          }
        } else {
          // Catch-all: emit unrecognized types so frontend can still see them
          emit(runId, { type: 'unknown', subtype: parsed.type || 'unknown', data: parsed });
        }
      }
    });

    child.stdout.on('error', () => {});

    let stderrBuf = '';
    child.stderr.on('data', (chunk) => {
      stderrBuf += chunk.toString();
      const lines = stderrBuf.split('\n');
      stderrBuf = lines.pop() || '';
      for (const line of lines) {
        if (line.trim()) {
          emit(runId, { type: 'log', data: { level: 'stderr', message: line } });
        }
      }
    });

    child.stderr.on('error', () => {});

    child.on('close', async (code) => {
      // Guard: ignore close events from stale children (killed and replaced by new resume)
      if (getChild(runId) && getChild(runId).pid !== child.pid) return;

      // Clean up HITL requests for this run
      for (const [id, req] of hitlRequests) {
        if (req.runId === runId) {
          req.resolve(false);
          hitlRequests.delete(id);
        }
      }

      try {
        const runDir = await findLatestRunDir(run.scene_name, preExistingDirs);
        let reportPath = null, score = null, verdict = null, hasOptimizer = false;

        if (runDir) {
          const runDirName = basename(runDir);
          const workspaceRel = `workspace/diagnostic-runs/${runDirName}`;

          const reportFile = join(runDir, pipeConfig.report_filename);
          if (existsSync(reportFile)) {
            reportPath = `${workspaceRel}/${pipeConfig.report_filename}`;
          }

          const optimizerFile = join(runDir, pipeConfig.optimizer_filename);
          hasOptimizer = existsSync(optimizerFile);

          const reviewDir = join(runDir, '05_review');
          if (existsSync(reviewDir)) {
            const prefix = pipeConfig.judge_feedback_prefix;
            const reviewFiles = readdirSync(reviewDir)
              .filter(f => f.startsWith(prefix) && f.endsWith('.json'))
              .sort();
            for (let i = reviewFiles.length - 1; i >= 0; i--) {
              try {
                const jf = JSON.parse(readFileSync(join(reviewDir, reviewFiles[i]), 'utf-8'));
                if (jf.score != null) { score = jf.score; verdict = jf.verdict || jf.result || null; break; }
              } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Diagnosis' }); }
            }
          }

          const artifacts = [];
          for (const d of pipeConfig.artifact_dirs) {
            if (existsSync(join(runDir, d))) artifacts.push(d);
          }
          if (reportPath) artifacts.push(pipeConfig.report_filename);
          if (hasOptimizer) artifacts.push(pipeConfig.optimizer_filename);
          emit(runId, {
            type: 'system',
            subtype: 'artifacts',
            data: { runDir: workspaceRel, artifacts, score, verdict, hasOptimizer },
          });
        }

        const wasHITLDenied = code === null;

        if (code === 0 || reportPath) {
          stmts.completeRun.run({
            runId,
            workspacePath: runDir ? `workspace/diagnostic-runs/${basename(runDir)}` : null,
            reportPath, score, judgeVerdict: verdict,
          });
          updateStatus(runId, 'completed');
          emit(runId, {
            type: 'complete',
            data: { status: 'completed', reportPath, score, verdict, hasOptimizer, exitCode: code },
          });
        } else if (wasHITLDenied) {
          stmts.failRun.run({ runId, error: 'Stopped: dangerous command denied by user' });
          updateStatus(runId, 'failed');
          emit(runId, {
            type: 'error',
            data: { status: 'failed', error: 'Stopped: dangerous command denied by user' },
          });
        } else {
          stmts.failRun.run({ runId, error: `Process exited with code ${code}` });
          updateStatus(runId, 'failed');
          emit(runId, {
            type: 'error',
            data: { status: 'failed', exitCode: code, error: `Process exited with code ${code}` },
          });
        }
      } catch (err) {
        stmts.failRun.run({ runId, error: err.message });
        updateStatus(runId, 'failed');
        emit(runId, { type: 'error', data: { status: 'failed', error: err.message } });
      }

      // Clear execution guard immediately so re-entry is possible
      executingRuns.delete(runId);
      // Delay SSE cleanup to let last events flush
      setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
    });

  } catch (err) {
    executingRuns.delete(runId);
    updateStatus(runId, 'failed');
    stmts.failRun.run({ runId, error: err.message });
    emit(runId, { type: 'error', data: { status: 'failed', error: err.message } });
    // Delay SSE cleanup to let last events flush
    setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
  }
}

// SSE subscription helper — subscribes to run events and maps them to SSE event types
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
      case 'unknown': sseEvent = 'unknown'; break;
      case 'stream_end': sseEvent = 'stream_end'; break;
      default: return;
    }
    callback(sseEvent, event.data);
  });
}

// Trigger diagnosis for a pending run
export function triggerDiagnosis(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    throw err;
  }
  if (run.status !== 'pending') {
    const err = new Error(`Run is not pending (status: ${run.status})`);
    err.status = 400;
    throw err;
  }
  const existingChild = getChild(runId);
  if (existingChild && !existingChild.killed && existingChild.exitCode === null) {
    const err = new Error('Run is already executing');
    err.status = 409;
    throw err;
  }

  executeDiagnosis(runId, run);
  return { runId, status: 'running' };
}

// Start streaming for a run — returns run info or starts diagnosis if pending
export function startStream(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) return null;

  const currentStatus = getStatus(runId) || run.status;

  if ((currentStatus === 'completed' || currentStatus === 'failed') && !hasRun(runId)) {
    return { run, currentStatus, isFinished: true };
  }

  return { run, currentStatus, isFinished: false };
}

// Take a snapshot of existing workspace dirs before spawning Claude.
// After completion, find any NEW dir that appeared.
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
