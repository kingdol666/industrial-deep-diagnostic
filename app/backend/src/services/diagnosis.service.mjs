// Diagnosis Service — Core business logic for diagnosis orchestration
// Handles: run creation, Claude process management, streaming, HITL, questions

import { v4 as uuid } from 'uuid';
import { readdir, stat, realpath } from 'fs/promises';
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, basename, relative } from 'path';
import {
  startDiagnosis, startSessionChat, parseStreamEvent, isDangerousCommand,
  PROJECT_ROOT, WORKSPACE_DIR, DATA_DIR, registerChild, closeQuery,
  getSessionMessages, getSessionInfo,
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

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'stopped']);
const PAUSED_STATUSES = new Set(['awaiting_input']);
const MISSING_CONVERSATION_RE = /No conversation found with session ID/i;

function formatResumeError(err, runId, sessionId) {
  if (MISSING_CONVERSATION_RE.test(err?.message || '')) {
    return `选中的诊断 Claude session 已不可恢复：${sessionId || 'unknown'}。runId=${runId} 只是本系统运行编号，不会作为 Claude session 传入。请重新启动一次诊断或选择仍可恢复的会话。`;
  }
  return err?.message || 'Diagnosis failed';
}

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

function parseEventStreamRow(row) {
  if (!row) return null;
  try {
    const payload = row.payload_json ? JSON.parse(row.payload_json) : {};
    return {
      type: payload.type || row.event_type || 'unknown',
      subtype: payload.subtype || row.event_subtype || null,
      data: payload.data ?? null,
      _seq: payload.seq ?? row.seq ?? 0,
      _ts: payload.ts ?? row.created_at ?? null,
    };
  } catch {
    return {
      type: row.event_type || 'unknown',
      subtype: row.event_subtype || null,
      data: null,
      _seq: row.seq ?? 0,
      _ts: row.created_at ?? null,
    };
  }
}

export function getRunEventStream(runId) {
  return stmts.getEventStreamByRunId.all(runId).map(parseEventStreamRow).filter(Boolean);
}

function derivePendingQuestionFromEvents(events) {
  let latestQuestion = null;
  for (const event of events) {
    if (!event) continue;
    if (event.type === 'question' && event.data?.questionId) {
      latestQuestion = event.data;
    } else if (event.type === 'question_result') {
      latestQuestion = null;
    } else if ((event.type === 'status' || event.type === 'complete') && TERMINAL_STATUSES.has(event.data?.status)) {
      latestQuestion = null;
    }
  }
  return latestQuestion;
}

export function getRunRealtimeSnapshot(runId) {
  const run = getRunStatus(runId);
  if (!run) return null;
  const liveStatus = getStatus(runId) || run.status;
  const hasActiveEngineRun = !TERMINAL_STATUSES.has(liveStatus)
    && !PAUSED_STATUSES.has(liveStatus)
    && hasRun(runId);
  const events = getRunEventStream(runId);
  const pendingQuestion = questionSessions.get(runId) || derivePendingQuestionFromEvents(events);
  return {
    run,
    events,
    liveStatus,
    hasActiveEngineRun,
    currentQuestion: pendingQuestion ? {
      questionId: pendingQuestion.questionId,
      toolUseId: pendingQuestion.toolUseId,
      questions: (pendingQuestion.questions || []).map(q => ({
        question: q.question || '',
        header: q.header || '',
        options: (q.options || []).map(o => ({
          label: o.label || '',
          description: o.description || '',
          preview: o.preview || '',
        })),
        multiSelect: q.multiSelect || false,
      })),
    } : null,
  };
}

// Stop a running diagnosis
export function stopDiagnosis(runId) {
  closeQuery(runId);
  questionSessions.delete(runId);
  updateStatus(runId, 'stopped');
  stmts.updateRunStatus.run({ runId, status: 'stopped' });
  emit(runId, { type: 'status', data: { status: 'stopped', runId } });
  emit(runId, { type: 'complete', data: { status: 'stopped', runId } });
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
  const run = stmts.getRunById.get(runId);
  if (!run) return false;
  closeQuery(runId);
  executingRuns.delete(runId);
  try {
    if (!hasRun(runId)) createRun(runId);
    updateStatus(runId, run.status);
    stmts.insertLog.run({
      runId,
      role: 'user',
      content: message,
      messageType: 'text',
      toolName: null,
    });
    emit(runId, {
      type: 'user_message',
      data: {
        role: 'user',
        content: message,
        source: 'chat',
      },
    });
    emit(runId, {
      type: 'system',
      subtype: 'session_chat',
      data: { message: '已发送到当前 Claude session，不重新启动诊断流程。' },
    });

    const result = startSessionChat({
      runId,
      sessionId: run.session_id,
      message,
      maxTurns: 1,
    });
    setChild(runId, result.query);
    registerChild(runId, result.query);
    consumeSessionChat(runId, result.query, run.session_id);
    return true;
  } catch (err) {
    const errorMessage = formatResumeError(err, runId, run.session_id);
    emit(runId, { type: 'error', data: { status: run.status, runId, error: errorMessage } });
    return false;
  }
}

async function consumeSessionChat(runId, query, sessionId) {
  try {
    for await (const msg of query) {
      const parsed = parseStreamEvent(msg);
      if (!parsed) continue;

      if (parsed.type === 'system') {
        const subtype = parsed.subtype || 'system';
        emit(runId, { type: 'system', subtype, data: parsed });
        if (parsed.subtype === 'init' && parsed.session_id) {
          stmts.updateRunSession.run({ runId, sessionId: parsed.session_id });
          setMeta(runId, { sessionId: parsed.session_id });
        }
      } else if (parsed.type === 'assistant') {
        const content = parsed.message?.content || [];
        for (const block of content) {
          if (block.type === 'text') {
            stmts.insertLog.run({ runId, role: 'assistant', content: block.text, messageType: 'text', toolName: null });
            emit(runId, { type: 'message', data: { role: 'assistant', content: block.text, source: 'session_chat' } });
          } else if (block.type === 'tool_use') {
            emit(runId, { type: 'tool_use', data: { name: block.name, input: block.input, id: block.id, source: 'session_chat' } });
          } else if (block.type === 'thinking') {
            emit(runId, { type: 'thinking', data: { content: block.thinking?.slice(0, 500) || '' } });
          }
        }
      } else if (parsed.type === 'user') {
        const userContent = parsed.message?.content || [];
        for (const block of userContent) {
          if (block.type === 'tool_result') {
            const summary = typeof block.content === 'string'
              ? block.content.slice(0, 300)
              : (block.content?.map?.(c => typeof c === 'string' ? c : c?.text).join('').slice(0, 300) || '');
            emit(runId, { type: 'tool_result', data: { toolUseId: block.tool_use_id, summary, isError: block.is_error || false } });
          }
        }
      } else if (parsed.type === 'result') {
        emit(runId, {
          type: 'stats',
          data: {
            subtype: 'session_chat',
            durationMs: parsed.duration_ms,
            numTurns: parsed.num_turns,
            totalCost: parsed.total_cost_usd,
            stopReason: parsed.stop_reason,
          },
        });
      } else if (parsed.type === 'stream_event') {
        emit(runId, { type: 'stream_event', subtype: parsed.event?.type || 'event', data: parsed.event });
      }
    }
  } catch (err) {
    emit(runId, {
      type: 'error',
      data: { runId, error: formatResumeError(err, runId, sessionId) },
    });
  } finally {
    closeQuery(runId);
    setChild(runId, null);
  }
}

// Continue / retry a failed or stopped run
export function continueDiagnosis(runId, followUpMessage, options = {}) {
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

  if (followUpMessage) {
    if (options.emitUserMessage !== false) {
      emit(runId, {
        type: 'user_message',
        data: {
          role: 'user',
          content: followUpMessage,
          source: 'continue',
        },
      });
    }
    emit(runId, {
      type: 'system',
      subtype: 'continue',
      data: {
        message: '已收到补充说明，继续当前诊断会话。',
      },
    });
  }

  executeDiagnosis(runId, run, true);
  return { runId, status: 'running', continued: true };
}

// Track active question sessions (child is SIGSTOPPED waiting for user answer)
const questionSessions = new Map();

// Submit answer to AskUserQuestion — write tool_result to stdin + SIGCONT the paused child
export function answerQuestion(runId, questionId, toolUseId, answers) {
  const entry = questionSessions.get(runId);
  if (!entry) return false;

  const answerText = Object.entries(answers)
    .map(([q, a]) => {
      const value = Array.isArray(a) ? a.join(', ') : a;
      return `- ${q}: ${value}`;
    })
    .join('\n');

  questionSessions.delete(runId);

  emit(runId, {
    type: 'question_result',
    data: { questionId, answers, timestamp: new Date().toISOString() },
  });

  emit(runId, {
    type: 'user_message',
    data: {
      role: 'user',
      content: answerText,
      source: 'question_answer',
      questionId,
    },
  });

  const followUpMessage = [
    '以下是对你上一轮结构化问题的正式回答，请基于这些答案继续当前诊断，不要再次重复提问，除非确有新的关键缺失信息：',
    answerText,
  ].join('\n\n');

  try {
    continueDiagnosis(runId, followUpMessage, { emitUserMessage: false });
    return true;
  } catch (err) {
    logger.error(`Failed to resume run ${runId} after answer: ${err.message}`, {
      context: 'Diagnosis',
      runId,
    });
    return false;
  }
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
  const meta = getMeta(runId);
  const isSessionResume = isRetry && !!meta.sessionId;
  if (!isRetry && run.user_question) {
    emit(runId, {
      type: 'user_message',
      data: {
        role: 'user',
        content: run.user_question,
        source: 'initial_question',
      },
    });
  }

  let analysisTarget;
  if (isSessionResume) {
    analysisTarget = { mode: 'resume' };
  } else {
    const dp = run.data_path;
    if (dp && dp.startsWith('[')) {
      analysisTarget = { mode: 'multi', files: JSON.parse(dp) };
    } else if (run.data_folder && dp === run.data_folder) {
      analysisTarget = { mode: 'folder', folderPath: dp };
    } else {
      analysisTarget = { mode: 'file', dataPath: dp };
    }
  }

  const hitlTimeoutMs = secConfig.hitl_auto_deny_seconds * 1000;
  let shouldCloseRun = true;
  let pausedForQuestion = false;
  let resumeSessionId = null;

  try {
    const followUpMessage = meta.followUpMessage || null;
    const sessionId = meta.sessionId || null;
    resumeSessionId = sessionId;

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
              questionSessions.set(runId, {
                questionId,
                toolUseId: block.id,
                questions: block.input.questions,
              });
              updateStatus(runId, 'awaiting_input');
              stmts.updateRunStatus.run({ runId, status: 'awaiting_input' });
              emit(runId, {
                type: 'status',
                data: {
                  status: 'awaiting_input',
                  runId,
                  questionId,
                  toolUseId: block.id,
                },
              });
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
              pausedForQuestion = true;
              shouldCloseRun = false;
            }

            emit(runId, { type: 'tool_use', data: { name: block.name, input: block.input, id: block.id } });
            if (pausedForQuestion) break;
          } else if (block.type === 'thinking') {
            emit(runId, { type: 'thinking', data: { content: block.thinking?.slice(0, 500) || '' } });
          }
        }
        if (pausedForQuestion) {
          closeQuery(runId);
          break;
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
        const pendingQuestion = questionSessions.get(runId);
        if (pendingQuestion && parsed.subtype === 'success') {
          shouldCloseRun = false;
          updateStatus(runId, 'awaiting_input');
          stmts.updateRunStatus.run({ runId, status: 'awaiting_input' });
          emit(runId, {
            type: 'status',
            data: {
              status: 'awaiting_input',
              runId,
              questionId: pendingQuestion.questionId,
              toolUseId: pendingQuestion.toolUseId,
            },
          });
          continue;
        }
        // Handle completion
        try {
          const runDir = await findLatestRunDir(run.scene_name, preExistingDirs);
          let workspacePath = null, reportPath = null, score = null, verdict = null;
          if (runDir) {
            workspacePath = relative(PROJECT_ROOT, runDir);
            const absReportPath = join(runDir, 'report.md');
            if (existsSync(absReportPath)) {
              reportPath = relative(PROJECT_ROOT, absReportPath);
              const reportContent = readFileSync(absReportPath, 'utf-8');
              const scoreMatch = reportContent.match(/Judge Score:\s*(\d+)\/100/);
              if (scoreMatch) score = parseInt(scoreMatch[1]);
              const verdictMatch = reportContent.match(/Judge Score:.*?\((\w+)/);
              if (verdictMatch) verdict = verdictMatch[1];
            }
          }
          if (parsed.subtype === 'success') {
            questionSessions.delete(runId);
            updateStatus(runId, 'completed');
            stmts.completeRun.run({
              runId,
              workspacePath,
              reportPath,
              score: score ?? null,
              judgeVerdict: verdict ?? null,
            });
            emit(runId, {
              type: 'status',
              data: { status: 'completed', runId, workspacePath, reportPath, score, verdict },
            });
            emit(runId, {
              type: 'complete',
              data: { status: 'completed', runId, workspacePath, reportPath, score, verdict },
            });
          } else {
            questionSessions.delete(runId);
            const error = `Query stopped: ${parsed.stop_reason || parsed.subtype}`;
            updateStatus(runId, 'failed');
            stmts.failRun.run({ runId, error });
            emit(runId, {
              type: 'status',
              data: { status: 'failed', runId, error },
            });
            emit(runId, {
              type: 'complete',
              data: { status: 'failed', runId, error },
            });
          }
        } catch (err) {
          const errorMessage = formatResumeError(err, runId, sessionId);
          questionSessions.delete(runId);
          updateStatus(runId, 'failed');
          stmts.failRun.run({ runId, error: errorMessage });
          emit(runId, {
            type: 'status',
            data: { status: 'failed', runId, error: errorMessage },
          });
          emit(runId, { type: 'error', data: { status: 'failed', runId, error: errorMessage } });
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
    if (shouldCloseRun) {
      setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
    }

  } catch (err) {
    const errorMessage = formatResumeError(err, runId, resumeSessionId);
    executingRuns.delete(runId);
    questionSessions.delete(runId);
    updateStatus(runId, 'failed');
    stmts.failRun.run({ runId, error: errorMessage });
    logger.error(`Diagnosis execution error for run ${runId}: ${err.message}`, { context: 'Diagnosis', runId });
    emit(runId, { type: 'status', data: { status: 'failed', runId, error: errorMessage } });
    emit(runId, { type: 'error', data: { status: 'failed', runId, error: errorMessage } });
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
  if ((currentStatus === 'completed' || currentStatus === 'failed' || currentStatus === 'stopped') && !hasRun(runId)) {
    return { run, currentStatus, isFinished: true };
  }
  return { run, currentStatus, isFinished: false };
}

export async function getSessionContent(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    throw err;
  }
  if (!run.session_id) {
    const err = new Error('No session ID associated with this run');
    err.status = 400;
    throw err;
  }

  let sessionInfo = null;
  try {
    sessionInfo = await getSessionInfo(run.session_id);
  } catch (e) {
    logger.warn(`Failed to get session info for ${run.session_id}: ${e.message}`, { context: 'Diagnosis' });
  }

  const rawMessages = await getSessionMessages(run.session_id);

  const events = [];
  let seq = 0;

  for (const msg of rawMessages) {
    seq++;
    if (msg.type === 'user') {
      const userMsg = msg.message || {};
      const content = userMsg.content || [];

      for (const block of content) {
        if (block.type === 'text') {
          events.push({
            type: 'user_message',
            data: {
              role: 'user',
              content: block.text || '',
              source: 'session',
            },
            _seq: seq,
          });
        }
        if (block.type === 'tool_result') {
          const resultContent = block.content;
          const summary = typeof resultContent === 'string'
            ? resultContent.slice(0, 300)
            : (Array.isArray(resultContent)
                ? resultContent.map(c => typeof c === 'string' ? c : c?.text).join('').slice(0, 300)
                : String(resultContent).slice(0, 300));

          events.push({
            type: 'tool_result',
            data: {
              toolUseId: block.tool_use_id,
              summary,
              isError: block.is_error || false,
            },
            _seq: seq,
          });
        }
      }
    } else if (msg.type === 'assistant') {
      const asstMsg = msg.message || {};
      const content = asstMsg.content || [];

      for (const block of content) {
        if (block.type === 'text') {
          events.push({
            type: 'message',
            data: { content: block.text || '', uuid: msg.uuid },
            _seq: seq,
          });
        } else if (block.type === 'tool_use') {
          if (block.name === 'AskUserQuestion' && block.input?.questions) {
            const questionId = `q_${runId}_${seq}`;
            events.push({
              type: 'question',
              data: {
                questionId,
                toolUseId: block.id,
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
              _seq: seq,
            });
          }

          events.push({
            type: 'tool_use',
            data: { name: block.name, input: block.input, id: block.id },
            _seq: seq,
          });
        } else if (block.type === 'thinking') {
          events.push({
            type: 'thinking',
            data: { content: block.thinking?.slice(0, 500) || '' },
            _seq: seq,
          });
        }
      }
    } else if (msg.type === 'system') {
      events.push({
        type: 'system',
        subtype: 'system',
        data: { message: msg },
        _seq: seq,
      });
    }
  }

  return {
    runId,
    sessionId: run.session_id,
    sessionInfo: sessionInfo ? {
      summary: sessionInfo.summary || '',
      lastModified: sessionInfo.lastModified || '',
      createdAt: sessionInfo.createdAt || '',
    } : null,
    messages: events,
  };
}
