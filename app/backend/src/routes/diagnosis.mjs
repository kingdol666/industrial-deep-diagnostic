import { Router } from 'express';
import { v4 as uuid } from 'uuid';
import { readdir, stat, readFile, realpath } from 'fs/promises';
import { existsSync } from 'fs';
import { join, basename, relative } from 'path';
import { startDiagnosis, parseStreamLine, PROJECT_ROOT, WORKSPACE_DIR } from '../claude-code.mjs';
import { stmts } from '../db.mjs';

const router = Router();

// Active diagnosis processes (in-memory)
const activeProcesses = new Map();

// Validate that a resolved data path is safe (contained within project root)
async function validateDataPath(dataPath) {
  const absoluteDataPath = dataPath.startsWith('/')
    ? dataPath
    : join(PROJECT_ROOT, dataPath);

  if (!existsSync(absoluteDataPath)) {
    const err = new Error(`Data not found: ${dataPath}`);
    err.code = 'DATA_NOT_FOUND';
    throw err;
  }

  // Resolve symlinks and check containment
  const resolved = await realpath(absoluteDataPath);
  const resolvedRoot = await realpath(PROJECT_ROOT);
  const rel = relative(resolvedRoot, resolved);

  if (rel.startsWith('..') || rel === '') {
    const err = new Error(`Path traversal blocked: ${dataPath}`);
    err.code = 'PATH_TRAVERSAL';
    err.status = 403;
    throw err;
  }

  // Store the relative path for the database
  const relativePath = relative(resolvedRoot, resolved);
  return { absolutePath: resolved, relativePath };
}

// Start a new diagnosis
router.post('/start', async (req, res) => {
  try {
    const { dataPath, userQuestion, sceneName, maxTurns } = req.body;

    if (!dataPath) {
      return res.status(400).json({ success: false, error: 'dataPath is required' });
    }

    const { relativePath } = await validateDataPath(dataPath);

    const runId = uuid().slice(0, 8);
    const scene = sceneName || basename(relativePath).replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
    const name = `${scene}_${runId}`;

    const pathParts = relativePath.split('/');
    const dataFolder = pathParts.length > 1 ? pathParts[0] : null;

    stmts.insertRun.run({
      runId,
      name,
      sceneName: scene,
      dataPath: relativePath,
      dataFolder,
      userQuestion: userQuestion || '',
      model: 'claude-opus-4-7',
      maxTurns: maxTurns ?? 200,
    });

    res.json({ success: true, data: { runId, name, status: 'pending' } });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Stream diagnosis progress via SSE
router.get('/stream/:runId', async (req, res) => {
  const { runId } = req.params;
  const run = stmts.getRunById.get(runId);

  if (!run) {
    return res.status(404).json({ success: false, error: 'Run not found' });
  }

  if (run.status === 'completed' || run.status === 'failed') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    res.write(`event: complete\ndata: ${JSON.stringify({ status: run.status, reportPath: run.report_path, score: run.score, verdict: run.judge_verdict })}\n\n`);
    res.end();
    return;
  }

  if (activeProcesses.has(runId)) {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    res.write(`event: error\ndata: ${JSON.stringify({ status: 'failed', error: 'Run already active in another connection' })}\n\n`);
    res.end();
    return;
  }

  // Set up SSE
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const sendEvent = (event, data) => {
    if (res.destroyed) return;
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  sendEvent('status', { status: 'starting', runId });

  stmts.updateRunStatus.run({ runId, status: 'running' });

  let child = null;

  const cleanup = () => {
    activeProcesses.delete(runId);
    if (child && !child.killed) {
      child.kill('SIGTERM');
    }
  };

  // Handle client disconnect or error
  req.on('close', cleanup);
  req.on('error', cleanup);

  try {
    const result = startDiagnosis({
      dataPath: run.data_path,
      userQuestion: run.user_question,
      sceneName: run.scene_name,
      runId,
      maxTurns: run.max_turns,
    });

    child = result.child;
    activeProcesses.set(runId, child);

    let buffer = '';

    child.stdout.on('data', (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const parsed = parseStreamLine(line);
        if (!parsed) continue;

        if (parsed.type === 'assistant') {
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
              sendEvent('message', { role: 'assistant', content: block.text });
            } else if (block.type === 'tool_use') {
              stmts.insertLog.run({
                runId,
                role: 'assistant',
                content: JSON.stringify(block.input),
                messageType: 'tool_use',
                toolName: block.name,
              });
              sendEvent('tool_use', { name: block.name, input: block.input });
            }
          }
        } else if (parsed.type === 'result') {
          const stats = parsed;
          sendEvent('stats', stats);
        } else if (parsed.type === 'system' && parsed.message) {
          sendEvent('system', parsed.message);
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
          sendEvent('log', { level: 'stderr', message: line });
        }
      }
    });

    child.stderr.on('error', () => {});

    child.on('close', async (code) => {
      activeProcesses.delete(runId);

      if (res.destroyed) return;

      try {
        const runDir = await findLatestRunDir(run.scene_name);
        let reportPath = null;
        let score = null;
        let verdict = null;

        if (runDir) {
          const rp = join(runDir, 'report.md');
          if (existsSync(rp)) reportPath = `workspace/diagnostic-runs/${basename(runDir)}/report.md`;

          const jp = join(runDir, '05_review', 'judge_feedback.json');
          if (existsSync(jp)) {
            try {
              const jf = JSON.parse(await readFile(jp, 'utf-8'));
              score = jf.score ?? null;
              verdict = jf.verdict ?? null;
            } catch {}
          }
        }

        if (code === 0 || reportPath) {
          stmts.completeRun.run({
            runId,
            workspacePath: runDir ? `workspace/diagnostic-runs/${basename(runDir)}` : null,
            reportPath,
            score,
            judgeVerdict: verdict,
          });
          sendEvent('complete', {
            status: 'completed',
            reportPath,
            score,
            verdict,
            exitCode: code,
          });
        } else {
          stmts.failRun.run({ runId, error: `Process exited with code ${code}` });
          sendEvent('error', { status: 'failed', exitCode: code });
        }
      } catch (err) {
        stmts.failRun.run({ runId, error: err.message });
        sendEvent('error', { status: 'failed', error: err.message });
      }

      if (!res.destroyed) res.end();
    });

  } catch (err) {
    activeProcesses.delete(runId);
    sendEvent('error', { status: 'failed', error: err.message });
    if (!res.destroyed) res.end();
  }
});

// Stop a running diagnosis
router.post('/stop/:runId', (req, res) => {
  const { runId } = req.params;
  const child = activeProcesses.get(runId);
  if (child) {
    if (!child.killed) {
      child.kill('SIGTERM');
    }
    activeProcesses.delete(runId);
    stmts.updateRunStatus.run({ runId, status: 'stopped' });
    res.json({ success: true, data: { runId, status: 'stopped' } });
  } else {
    res.status(404).json({ success: false, error: 'No active process for this run' });
  }
});

// Get run status
router.get('/status/:runId', (req, res) => {
  const run = stmts.getRunById.get(req.params.runId);
  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: run });
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

export default router;
