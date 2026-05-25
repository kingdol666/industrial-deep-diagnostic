import { Router } from 'express';
import { v4 as uuid } from 'uuid';
import { readdir, stat, realpath } from 'fs/promises';
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, basename, relative } from 'path';
import { startDiagnosis, parseStreamLine, isDangerousCommand, PROJECT_ROOT, WORKSPACE_DIR, DATA_DIR, registerChild, writeAnswer } from '../claude-code.mjs';
import {
  createRun, setChild, getChild, updateStatus, getStatus, emit, closeRun, hasRun, subscribe,
  setMeta, getMeta, resetRun,
} from '../diagnosis-engine.mjs';
import { stmts } from '../db.mjs';
import { config, diagnosis as diagConfig, security as secConfig, pipeline as pipeConfig, engine as engConfig } from '../../../../config/loader.mjs';

const router = Router();

// Validate that a resolved data path is safe (contained within project root)
async function validateDataPath(dataPath) {
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

// Start a new diagnosis
router.post('/start', async (req, res) => {
  try {
    const { dataPath, folderPath, dataPaths, userQuestion, sceneName, maxTurns, timeoutMinutes, reportLanguage } = req.body;

    let mode, dataPathForDb, scene, dataFolder;

    if (dataPaths && Array.isArray(dataPaths) && dataPaths.length > 0) {
      mode = 'multi';
      for (const dp of dataPaths) {
        await validateDataPath(dp);
      }
      dataPathForDb = JSON.stringify(dataPaths);
      const first = dataPaths[0];
      const parts = first.split('/');
      dataFolder = parts.length > 1 ? parts[0] : null;
      scene = sceneName || basename(first).replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
    } else if (folderPath) {
      mode = 'folder';
      const { relativePath } = await validateDataPath(folderPath);
      dataPathForDb = relativePath;
      dataFolder = relativePath;
      scene = sceneName || basename(relativePath).replace(/[^a-zA-Z0-9]/g, '_');
    } else if (dataPath) {
      mode = 'file';
      const { relativePath } = await validateDataPath(dataPath);
      dataPathForDb = relativePath;
      const pathParts = relativePath.split('/');
      dataFolder = pathParts.length > 1 ? pathParts[0] : null;
      scene = sceneName || basename(relativePath).replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
    } else {
      return res.status(400).json({ success: false, error: 'One of dataPath, folderPath, or dataPaths is required' });
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

    res.json({ success: true, data: { runId, name, status: 'pending', mode } });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// List all diagnosis runs
router.get('/list', (_req, res) => {
  try {
    const runs = stmts.getAllRuns.all();
    const enriched = runs.map(r => ({
      ...r,
      engineStatus: getStatus(r.run_id) || r.status,
    }));
    res.json({ success: true, data: enriched });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Track HITL requests per run: hitlId -> { resolve, child }
const hitlRequests = new Map();
let hitlSeq = 0;

// Trigger the actual diagnosis execution
function executeDiagnosis(runId, run, isRetry = false) {
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

    const result = startDiagnosis({
      analysisTarget,
      userQuestion: run.user_question,
      sceneName: run.scene_name,
      runId,
      maxTurns: run.max_turns,
      timeoutMinutes,
      reportLanguage: run.report_language || diagConfig.default_language,
      followUpMessage,
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
          emit(runId, {
            type: 'system',
            subtype,
            data: parsed,
          });
          if (parsed.subtype === 'init') {
            stmts.insertLog.run({
              runId,
              role: 'system',
              content: JSON.stringify({ subtype: 'init', model: parsed.model, tools: parsed.tools?.length }),
              messageType: 'system',
              toolName: null,
            });
          }
        } else if (parsed.type === 'assistant') {
          const content = parsed.message?.content || [];
          for (const block of content) {
            if (block.type === 'text') {
              stmts.insertLog.run({
                runId,
                role: 'assistant',
                content: block.text,
                messageType: 'text',
                toolName: null,
              });
              emit(runId, {
                type: 'message',
                data: { role: 'assistant', content: block.text },
              });
            } else if (block.type === 'tool_use') {
              stmts.insertLog.run({
                runId,
                role: 'assistant',
                content: JSON.stringify(block.input),
                messageType: 'tool_use',
                toolName: block.name,
              });

              // HITL: Check for dangerous Bash commands
              if (block.name === 'Bash' && block.input?.command) {
                const danger = isDangerousCommand(block.input.command);
                if (danger) {
                  const hitlId = `hitl_${runId}_${++hitlSeq}`;

                  emit(runId, {
                    type: 'hitl_request',
                    data: {
                      hitlId,
                      runId,
                      command: block.input.command,
                      riskLevel: danger.level,
                      riskDesc: danger.desc,
                      dangerMatch: danger.match,
                      toolUseId: block.id,
                    },
                  });

                  if (child && !child.killed) {
                    try { process.kill(child.pid, 'SIGSTOP'); } catch {}
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
                        try { process.kill(child.pid, 'SIGKILL'); } catch {}
                        resolve(false);
                      }
                    }, hitlTimeoutMs);
                  });

                  hitlPromise.then((approved) => {
                    if (approved) {
                      emit(runId, { type: 'hitl_result', data: { hitlId, approved: true } });
                      try { process.kill(child.pid, 'SIGCONT'); } catch {}
                    } else {
                      emit(runId, { type: 'hitl_result', data: { hitlId, approved: false, reason: 'Denied by user' } });
                      try { process.kill(child.pid, 'SIGKILL'); } catch {}
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
                    questionId,
                    toolUseId: block.id,
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
                runId,
                role: 'tool',
                content: summary,
                messageType: 'tool_result',
                toolName: block.tool_use_id || null,
              });
              emit(runId, {
                type: 'tool_result',
                data: {
                  toolUseId: block.tool_use_id,
                  summary,
                  isError: block.is_error || false,
                },
              });
            }
          }
        } else if (parsed.type === 'result') {
          emit(runId, {
            type: 'stats',
            data: {
              subtype: parsed.subtype,
              durationMs: parsed.duration_ms,
              numTurns: parsed.num_turns,
              totalCost: parsed.total_cost_usd,
              stopReason: parsed.stop_reason,
            },
          });
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
      for (const [id, req] of hitlRequests) {
        if (req.runId === runId) {
          req.resolve(false);
          hitlRequests.delete(id);
        }
      }

      try {
        const runDir = await findLatestRunDir(run.scene_name);
        let reportPath = null;
        let score = null;
        let verdict = null;
        let hasOptimizer = false;

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
                if (jf.score != null) {
                  score = jf.score;
                  verdict = jf.verdict || jf.result || null;
                  break;
                }
              } catch {}
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
            reportPath,
            score,
            judgeVerdict: verdict,
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

      setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
    });

  } catch (err) {
    updateStatus(runId, 'failed');
    stmts.failRun.run({ runId, error: err.message });
    emit(runId, { type: 'error', data: { status: 'failed', error: err.message } });
    setTimeout(() => closeRun(runId), engConfig.close_run_delay_seconds * 1000);
  }
}

// SSE stream endpoint
router.get('/stream/:runId', async (req, res) => {
  const { runId } = req.params;
  const run = stmts.getRunById.get(runId);

  if (!run) {
    return res.status(404).json({ success: false, error: 'Run not found' });
  }

  const currentStatus = getStatus(runId) || run.status;

  if ((currentStatus === 'completed' || currentStatus === 'failed') && !hasRun(runId)) {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    res.write(`event: complete\ndata: ${JSON.stringify({ status: currentStatus, reportPath: run.report_path, score: run.score, verdict: run.judge_verdict })}\n\n`);
    res.end();
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const sendSSE = (event, data) => {
    if (res.destroyed) return;
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  const unsub = subscribe(runId, (event) => {
    if (res.destroyed) return;
    switch (event.type) {
      case 'status':
        sendSSE('status', event.data);
        break;
      case 'message':
        sendSSE('message', event.data);
        break;
      case 'tool_use':
        sendSSE('tool_use', event.data);
        break;
      case 'tool_result':
        sendSSE('tool_result', event.data);
        break;
      case 'thinking':
        sendSSE('thinking', event.data);
        break;
      case 'system':
        sendSSE('system', event.data);
        break;
      case 'stats':
        sendSSE('stats', event.data);
        break;
      case 'log':
        sendSSE('log', event.data);
        break;
      case 'question':
        sendSSE('question', event.data);
        break;
      case 'hitl_request':
        sendSSE('hitl_request', event.data);
        break;
      case 'hitl_result':
        sendSSE('hitl_result', event.data);
        break;
      case 'complete':
        sendSSE('complete', event.data);
        break;
      case 'error':
        sendSSE('error', event.data);
        break;
      case 'stream_end':
        if (!res.destroyed) res.end();
        break;
    }
  });

  req.on('close', () => {
    unsub();
    if (!res.destroyed) res.end();
  });

  if (currentStatus === 'pending') {
    executeDiagnosis(runId, run);
  }
});

// Stop a running diagnosis
router.post('/stop/:runId', (req, res) => {
  const { runId } = req.params;
  const child = getChild(runId);
  if (child && !child.killed) {
    child.kill('SIGTERM');
    updateStatus(runId, 'stopped');
    stmts.updateRunStatus.run({ runId, status: 'stopped' });
    emit(runId, { type: 'status', data: { status: 'stopped' } });
    res.json({ success: true, data: { runId, status: 'stopped' } });
  } else if (hasRun(runId)) {
    updateStatus(runId, 'stopped');
    stmts.updateRunStatus.run({ runId, status: 'stopped' });
    res.json({ success: true, data: { runId, status: 'stopped' } });
  } else {
    res.status(404).json({ success: false, error: 'No active process for this run' });
  }
});

// Trigger execution for an already-created pending run
router.post('/execute/:runId', async (req, res) => {
  const { runId } = req.params;
  const run = stmts.getRunById.get(runId);

  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  if (run.status !== 'pending') {
    return res.status(400).json({ success: false, error: `Run is not pending (status: ${run.status})` });
  }
  const existingChild = getChild(runId);
  if (existingChild && !existingChild.killed && existingChild.exitCode === null) {
    return res.status(409).json({ success: false, error: 'Run is already executing' });
  }

  executeDiagnosis(runId, run);

  res.json({ success: true, data: { runId, status: 'running' } });
});

// Send a chat message to running Claude process
router.post('/chat/:runId', (req, res) => {
  const { runId } = req.params;
  const { message } = req.body;

  if (!message || typeof message !== 'string') {
    return res.status(400).json({ success: false, error: 'message is required' });
  }

  // Send as a user text message via stdin
  const userMessage = {
    type: 'user',
    message: {
      role: 'user',
      content: [{ type: 'text', text: message }],
    },
  };

  const wrote = writeAnswer(runId, userMessage);
  if (!wrote) {
    return res.status(404).json({
      success: false,
      error: 'Process not found or already ended. Use /continue to restart with a follow-up message.',
    });
  }

  emit(runId, {
    type: 'system',
    subtype: 'chat_sent',
    data: { message, timestamp: new Date().toISOString() },
  });

  res.json({ success: true, data: { runId, sent: true } });
});

// Continue / retry a failed or stopped run
router.post('/continue/:runId', async (req, res) => {
  const { runId } = req.params;
  const { followUpMessage } = req.body || {};
  const run = stmts.getRunById.get(runId);

  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  if (!['failed', 'stopped'].includes(run.status)) {
    return res.status(400).json({ success: false, error: `Run status is "${run.status}" — only failed or stopped runs can be continued` });
  }
  const existingChild = getChild(runId);
  if (existingChild && !existingChild.killed && existingChild.exitCode === null) {
    return res.status(409).json({ success: false, error: 'Run is already executing' });
  }

  stmts.updateRunStatus.run({ runId, status: 'running' });

  // Store follow-up message in meta so executeDiagnosis can use it
  if (followUpMessage) {
    setMeta(runId, { followUpMessage });
  }

  executeDiagnosis(runId, run, true);

  res.json({ success: true, data: { runId, status: 'running', continued: true } });
});

// Handle HITL approval/denial from frontend
router.post('/hitl/:hitlId', (req, res) => {
  const { hitlId } = req.params;
  const { approved } = req.body;

  const entry = hitlRequests.get(hitlId);
  if (!entry) {
    return res.status(404).json({ success: false, error: 'HITL request not found or already resolved' });
  }

  hitlRequests.delete(hitlId);
  entry.resolve(approved === true);

  res.json({ success: true, data: { hitlId, approved } });
});

// Submit answer to AskUserQuestion
router.post('/answer/:runId', (req, res) => {
  const { runId } = req.params;
  const { questionId, toolUseId, answers } = req.body;

  if (!toolUseId || !answers) {
    return res.status(400).json({ success: false, error: 'toolUseId and answers are required' });
  }

  // Build the Claude CLI expected response format
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
    return res.status(404).json({ success: false, error: 'Process not found or already ended' });
  }

  emit(runId, {
    type: 'question_result',
    data: { questionId, answers, timestamp: new Date().toISOString() },
  });

  res.json({ success: true, data: { runId, questionId, answered: true } });
});

// Get run status
router.get('/status/:runId', (req, res) => {
  const run = stmts.getRunById.get(req.params.runId);
  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });

  const engineStatus = getStatus(req.params.runId);
  res.json({
    success: true,
    data: {
      ...run,
      engineStatus: engineStatus || run.status,
    },
  });
});

// Check pending HITL requests for a run
router.get('/hitl/:runId', (req, res) => {
  const { runId } = req.params;
  const pending = [];
  for (const [id, entry] of hitlRequests) {
    if (entry.runId === runId) {
      pending.push({ hitlId: id, runId });
    }
  }
  res.json({ success: true, data: { pending } });
});

async function findLatestRunDir(sceneName) {
  if (!existsSync(WORKSPACE_DIR)) return null;
  const entries = await readdir(WORKSPACE_DIR);
  let latest = null;
  let latestTime = 0;
  for (const entry of entries) {
    const escapedName = sceneName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const dirPattern = new RegExp(`_${escapedName}$`);
    if (dirPattern.test(entry)) {
      const s = await stat(join(WORKSPACE_DIR, entry));
      if (s.mtimeMs > latestTime) {
        latestTime = s.mtimeMs;
        latest = join(WORKSPACE_DIR, entry);
      }
    }
  }
  return latest;
}

export { hitlRequests };

export default router;
