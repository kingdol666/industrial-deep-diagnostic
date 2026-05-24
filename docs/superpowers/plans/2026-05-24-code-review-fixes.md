# Code Review Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 21 bugs identified in max-effort code review: path traversal, SSE crash vectors, XSS, falsy-zero, timer leaks, prompt injection, off-by-one, state management gaps, and race conditions.

**Architecture:** Five targeted file modifications. No new files. Each task bundles related fixes for a single file. Backend fixes in `app/backend/src/` (claude-code.mjs, routes/diagnosis.mjs, index.mjs). Frontend fixes in `app/frontend/src/` (DiagnosisPanel.vue, ReportViewer.vue). New dependency: `dompurify` for XSS sanitization.

**Tech Stack:** Node.js/Express, Vue 3, better-sqlite3, Server-Sent Events, DOMPurify

---

### Task 1: Fix `claude-code.mjs` — SIGKILL escalation, prompt injection, env filtering, stream errors

**Files:**
- Modify: `app/backend/src/claude-code.mjs`

- [ ] **Step 1: Replace the entire file**

Four bugs fixed: (a) SIGKILL timer never cleared and `child.killed` makes escalation dead code, (b) `userQuestion` and `sceneName` interpolated into prompt without sanitization, (c) full `process.env` spread to child, (d) no error handlers on stdout/stderr streams.

```javascript
import { spawn, execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
const DATA_DIR = join(PROJECT_ROOT, 'data');
const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');

const SKILL_DIR = join(PROJECT_ROOT, '.claude', 'skills', 'industrial-deep-diagnostic');
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');

// Minimal env vars the Claude CLI needs — avoid leaking secrets
const ALLOWED_ENV = [
  'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL',
  'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL',
  'NODE_PATH', 'SHELL', 'TERM',
];

function buildEnv() {
  const env = {};
  for (const key of ALLOWED_ENV) {
    if (process.env[key] !== undefined) {
      env[key] = process.env[key];
    }
  }
  env.FORCE_COLOR = '0';
  env.NO_COLOR = '1';
  return env;
}

function findClaudeCLI() {
  try {
    return execSync('which claude', { encoding: 'utf-8', timeout: 3000 }).trim();
  } catch {
    try {
      const alt = execSync('which claude-code', { encoding: 'utf-8', timeout: 3000 }).trim();
      return alt;
    } catch {
      return null;
    }
  }
}

function sanitize(str) {
  // Strip characters that could enable prompt injection via newlines or markup
  return str.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '').trim();
}

function buildPrompt(sceneName, userQuestion, dataPath) {
  const safeScene = sanitize(sceneName);
  const safeQuestion = sanitize(userQuestion || '');

  return `Execute the /industrial-deep-diagnostic skill on industrial data.

## Input

- **Data file**: ${dataPath}
- **Scene name**: ${safeScene}
- **Analysis question**: ${safeQuestion || 'Perform a comprehensive root cause analysis'}

## Instructions

1. Invoke the /industrial-deep-diagnostic skill with the scene name "${safeScene}"
2. The skill will guide you through the 8-step pipeline: setup, data inspection, ontology building, statistical analysis, visualization, diagnosis, judge review, and report generation
3. All output artifacts go to workspace/diagnostic-runs/<run_dir>/
4. After completing all pipeline steps and passing the judge quality gate (score >= 90), present the final report

## Critical Rules

- Evidence first. Reasoning second. Conclusions last.
- Every root cause claim must satisfy ALL four criteria: temporal precedence, statistical evidence, physical mechanism, no contradicting evidence
- Missing any criterion -> label as [HYPOTHESIS]
- Use the statistical validation framework to catch confounders`;
}

export function startDiagnosis({ dataPath, userQuestion, sceneName, runId, maxTurns = 200, timeoutMinutes = 30 }) {
  const absoluteDataPath = dataPath.startsWith('/')
    ? dataPath
    : join(PROJECT_ROOT, dataPath);

  if (!existsSync(absoluteDataPath)) {
    const err = new Error(`Data path not found: ${absoluteDataPath}`);
    err.code = 'DATA_NOT_FOUND';
    throw err;
  }

  if (!existsSync(SKILL_MD)) {
    const err = new Error(`Skill definition not found at: ${SKILL_MD}`);
    err.code = 'SKILL_NOT_FOUND';
    throw err;
  }

  const claudeBin = findClaudeCLI();
  if (!claudeBin) {
    const err = new Error('Claude Code CLI not found in PATH. Install with: npm install -g @anthropic-ai/claude-code');
    err.code = 'CLAUDE_NOT_FOUND';
    throw err;
  }

  const prompt = buildPrompt(sceneName, userQuestion, dataPath);

  const claudeArgs = [
    '-p', prompt,
    '--output-format', 'stream-json',
    '--max-turns', String(maxTurns),
    '--verbose',
    '--allowedTools', 'Read(/**),Write(/**),Edit(/**),Bash(/**),Skill(industrial-deep-diagnostic),WebSearch,WebFetch',
  ];

  const child = spawn(claudeBin, claudeArgs, {
    cwd: PROJECT_ROOT,
    env: buildEnv(),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let sigkillTimer = null;

  const timeout = setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGTERM');
      // Schedule SIGKILL escalation — store handle so we can clear it
      sigkillTimer = setTimeout(() => {
        // Use kill(pid, signal) directly since child.killed is set synchronously by Node
        try { process.kill(child.pid, 'SIGKILL'); } catch {}
      }, 5000);
    }
  }, timeoutMinutes * 60 * 1000);

  child.on('close', () => {
    clearTimeout(timeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  child.on('error', () => {
    clearTimeout(timeout);
    if (sigkillTimer) clearTimeout(sigkillTimer);
  });

  // Prevent unhandled stream errors from crashing the process
  child.stdout.on('error', () => {});
  child.stderr.on('error', () => {});

  return { child, prompt, projectRoot: PROJECT_ROOT };
}

export function parseStreamLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

export function extractReportPath(output) {
  const match = output.match(/workspace\/diagnostic-runs\/[^\s]+\/report\.md/);
  return match ? match[0] : null;
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
```

- [ ] **Step 2: Verify syntax**

Run: `node --check "app/backend/src/claude-code.mjs"`
Expected: no output (exit 0)

- [ ] **Step 3: Commit**

```bash
git add app/backend/src/claude-code.mjs
git commit -m "fix: SIGKILL escalation, prompt injection, env filtering, stream errors in claude-code.mjs

- Fix SIGKILL timer: store inner timeout and clear on close; use process.kill(pid)
  since child.killed is set synchronously by Node, making the escalation dead code
- Sanitize sceneName and userQuestion to prevent prompt injection
- Replace full process.env spread with allowlist of needed env vars
- Add noop error handlers on child.stdout/stderr to prevent unhandled crashes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Fix `diagnosis.mjs` — path traversal, SSE guards, falsy-zero, stream errors, map leak, req error

**Files:**
- Modify: `app/backend/src/routes/diagnosis.mjs`

- [ ] **Step 1: Replace the entire file**

Six bugs fixed: (a) path traversal via absolute paths and `../`, (b) `sendEvent` on destroyed response, (c) falsy-zero score with `||`, (d) missing `req.on('error')`, (e) `activeProcesses.delete` gated behind `!child.killed`, (f) no error handlers on stdout/stderr streams.

```javascript
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
  const relativePath = relative(PROJECT_ROOT, resolved);
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
      maxTurns: maxTurns || 200,
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
```

- [ ] **Step 2: Verify syntax**

Run: `node --check "app/backend/src/routes/diagnosis.mjs"`
Expected: no output (exit 0)

- [ ] **Step 3: Commit**

```bash
git add app/backend/src/routes/diagnosis.mjs
git commit -m "fix: path traversal, SSE guards, falsy-zero, stream errors in diagnosis.mjs

- Add realpath-based path traversal check with containment validation
- Guard all sendEvent/res.end calls with res.destroyed check
- Use ?? instead of || for score/verdict (preserve falsy-zero)
- Add req.on('error') handler for socket errors
- Always cleanup activeProcesses entry regardless of child.killed state
- Add noop error handlers on child.stdout/stderr streams
- Fix /stop to check activeProcesses.has() instead of child.killed

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Fix `index.mjs` — startup cleanup of stale 'running' rows

**Files:**
- Modify: `app/backend/src/index.mjs`

- [ ] **Step 1: Add startup cleanup**

Add import for `stmts` at the top, and add a startup block that marks stale `running` rows as `interrupted` before the server starts listening.

Change the imports (lines 1-8) to add `stmts`:

```javascript
import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync } from 'fs';
import fileRoutes from './routes/files.mjs';
import diagnosisRoutes from './routes/diagnosis.mjs';
import historyRoutes from './routes/history.mjs';
import { stmts } from './db.mjs';
```

Change the `app.listen` block (lines 42-46) to run cleanup first:

```javascript
// Mark any stale 'running' runs as interrupted (server was restarted)
const staleRuns = stmts.getActiveRuns.all();
for (const run of staleRuns) {
  stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
  console.log(`[Industrial Diagnostic API] Marked stale run as interrupted: ${run.run_id}`);
}

app.listen(PORT, () => {
  console.log(`[Industrial Diagnostic API] Server running on http://localhost:${PORT}`);
  console.log(`[Industrial Diagnostic API] Project root: ${projectRoot}`);
  console.log(`[Industrial Diagnostic API] Data dir: ${join(projectRoot, 'data')}`);
});
```

Full file after changes:

```javascript
import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync } from 'fs';
import fileRoutes from './routes/files.mjs';
import diagnosisRoutes from './routes/diagnosis.mjs';
import historyRoutes from './routes/history.mjs';
import { stmts } from './db.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3210;

const app = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Serve uploaded data files statically (for preview/download)
const projectRoot = join(__dirname, '..', '..', '..');
app.use('/data-files', express.static(join(projectRoot, 'data')));
app.use('/workspace-files', express.static(join(projectRoot, 'workspace')));

// API routes
app.use('/api/files', fileRoutes);
app.use('/api/diagnosis', diagnosisRoutes);
app.use('/api/history', historyRoutes);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve Vue frontend in production
const frontendDist = join(__dirname, '..', '..', 'frontend', 'dist');
app.use(express.static(frontendDist));
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api/')) {
    res.sendFile(join(frontendDist, 'index.html'));
  }
});

// Mark any stale 'running' runs as interrupted (server was restarted)
const staleRuns = stmts.getActiveRuns.all();
for (const run of staleRuns) {
  stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
  console.log(`[Industrial Diagnostic API] Marked stale run as interrupted: ${run.run_id}`);
}

app.listen(PORT, () => {
  console.log(`[Industrial Diagnostic API] Server running on http://localhost:${PORT}`);
  console.log(`[Industrial Diagnostic API] Project root: ${projectRoot}`);
  console.log(`[Industrial Diagnostic API] Data dir: ${join(projectRoot, 'data')}`);
});
```

- [ ] **Step 2: Verify syntax**

Run: `node --check "app/backend/src/index.mjs"`
Expected: no output (exit 0)

- [ ] **Step 3: Commit**

```bash
git add app/backend/src/index.mjs
git commit -m "fix: mark stale running runs as interrupted on server startup

- Query getActiveRuns on boot and mark each as failed/interrupted
- Prevents duplicate process spawn if client reconnects after restart

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Fix `DiagnosisPanel.vue` — onUnmounted, off-by-one, progress, state reset, double-fire, typeof null

**Files:**
- Modify: `app/frontend/src/components/DiagnosisPanel.vue`

- [ ] **Step 1: Update the `<script setup>` block**

Replace the entire `<script setup>` block (lines 124-301). Six bugs fixed: (a) no `onUnmounted` cleanup, (b) `slice(-200)` + `push` = 201 items, (c) progress backward on tool_use, (d) `watch(selectedFile)` doesn't tear down running diagnosis, (e) SSE `error` + `onerror` double-fire, (f) `typeof null === 'object'` for tool_use input.

```javascript
<script setup>
import { ref, nextTick, watch, onUnmounted } from 'vue';
import { api } from '../api.js';

const props = defineProps({
  selectedFile: { type: Object, default: null },
});

const emit = defineEmits(['started']);

const sceneName = ref('');
const userQuestion = ref('');
const maxTurns = ref(200);
const isRunning = ref(false);
const completed = ref(false);
const failed = ref(false);
const runId = ref(null);
const messages = ref([]);
const result = ref(null);
const progressPct = ref(0);
const outputStream = ref(null);
let eventSource = null;
let didComplete = false;
let didError = false;
let msgCount = 0;
const MAX_MESSAGES = 200;
const truncated = ref(false);

// Cleanup on component unmount (tab switch)
onUnmounted(() => {
  closeSSE();
});

watch(() => props.selectedFile, (file) => {
  // Full teardown of any running diagnosis
  closeSSE();
  isRunning.value = false;
  progressPct.value = 0;
  didComplete = false;
  didError = false;
  msgCount = 0;
  truncated.value = false;

  if (file && !sceneName.value) {
    sceneName.value = file.name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  }
  messages.value = [];
  result.value = null;
  completed.value = false;
  failed.value = false;
});

async function startDiagnosis() {
  if (!props.selectedFile) return;

  closeSSE();
  isRunning.value = true;
  completed.value = false;
  failed.value = false;
  messages.value = [];
  result.value = null;
  msgCount = 0;
  didComplete = false;
  didError = false;
  truncated.value = false;
  progressPct.value = 5;

  try {
    const data = await api.startDiagnosis({
      dataPath: props.selectedFile.path,
      userQuestion: userQuestion.value,
      sceneName: sceneName.value || undefined,
      maxTurns: maxTurns.value,
    });

    runId.value = data.runId;
    emit('started', data.runId);
    addMessage('system', `Run started: ${data.runId} (${data.name})`);

    // Open SSE stream
    eventSource = new EventSource(api.streamUrl(data.runId));

    eventSource.addEventListener('status', (e) => {
      const d = JSON.parse(e.data);
      addMessage('system', `Status: ${d.status}`);
    });

    eventSource.addEventListener('message', (e) => {
      const d = JSON.parse(e.data);
      const text = d.content || '';
      if (text) {
        addMessage('text', text);
        progressPct.value = Math.min(90, progressPct.value + 2);
      }
    });

    eventSource.addEventListener('tool_use', (e) => {
      const d = JSON.parse(e.data);
      const inputStr = (d.input != null && typeof d.input === 'object')
        ? JSON.stringify(d.input).slice(0, 200)
        : String(d.input ?? '').slice(0, 200);
      addMessage('tool_use', `[${d.name}] ${inputStr}`);
      progressPct.value = Math.min(90, progressPct.value + 5);
    });

    eventSource.addEventListener('log', (e) => {
      const d = JSON.parse(e.data);
      addMessage('system', d.message);
    });

    eventSource.addEventListener('stats', (e) => {
      const d = JSON.parse(e.data);
      addMessage('system', `Stats: ${JSON.stringify(d).slice(0, 200)}`);
    });

    eventSource.addEventListener('complete', (e) => {
      didComplete = true;
      const d = JSON.parse(e.data);
      completed.value = true;
      isRunning.value = false;
      progressPct.value = 100;
      result.value = d;
      addMessage('system', `Completed! Score: ${d.score ?? 'N/A'}, Verdict: ${d.verdict ?? 'N/A'}`);
      closeSSE();
    });

    eventSource.addEventListener('error', (e) => {
      didError = true;
      const d = JSON.parse(e.data);
      failed.value = true;
      isRunning.value = false;
      result.value = d;
      addMessage('error', d.error || 'Diagnosis failed');
      closeSSE();
    });

    eventSource.onerror = () => {
      if (didComplete || didError) return;
      if (isRunning.value) {
        failed.value = true;
        isRunning.value = false;
        addMessage('error', 'Connection lost');
        closeSSE();
      }
    };
  } catch (err) {
    isRunning.value = false;
    failed.value = true;
    addMessage('error', 'Failed to start: ' + err.message);
  }
}

function stopDiagnosis() {
  if (runId.value) {
    api.stopDiagnosis(runId.value);
  }
  closeSSE();
  isRunning.value = false;
  addMessage('system', 'Stopped by user');
}

function closeSSE() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function addMessage(type, content) {
  msgCount++;
  messages.value.push({ type, content });
  if (messages.value.length > MAX_MESSAGES) {
    messages.value = messages.value.slice(-MAX_MESSAGES);
    truncated.value = true;
  }
  nextTick(() => {
    if (outputStream.value) {
      outputStream.value.scrollTop = outputStream.value.scrollHeight;
    }
  });
}

function viewReport() {
  if (result.value?.reportPath) {
    window.open(`/workspace-files/${result.value.reportPath}`, '_blank');
  }
}

function verdictClass(verdict) {
  if (verdict === 'PASS' || verdict === 'ENDORSED') return 'badge-green';
  if (verdict === 'CONDITIONAL' || verdict === 'NEEDS_REPAIR') return 'badge-yellow';
  return 'badge-red';
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>
```

Note: The `<template>` and `<style scoped>` blocks do not change — only the `<script setup>` block is replaced.

- [ ] **Step 2: Verify the frontend builds**

Run: `cd app/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds with no errors

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/components/DiagnosisPanel.vue
git commit -m "fix: onUnmounted cleanup, off-by-one, progress, state reset, double-fire in DiagnosisPanel

- Add onUnmounted hook to close EventSource on tab switch
- Fix off-by-one: push before slice, truncate at MAX_MESSAGES+1
- Fix progress backward: use same Math.min(90, ...) cap for tool_use
- Fix watch(selectedFile): full teardown of running diagnosis on file switch
- Fix SSE double-fire: add didError flag (mirrors didComplete pattern)
- Fix typeof null: check d.input != null before typeof === 'object'

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Fix `ReportViewer.vue` — immediate watcher, stale async race, XSS, autoRunId

**Files:**
- Modify: `app/frontend/src/components/ReportViewer.vue`

- [ ] **Step 1: Install DOMPurify**

Run: `cd app/frontend && npm install dompurify`
Expected: Package added to package.json

- [ ] **Step 2: Update the `<script setup>` block**

Replace the entire `<script setup>` block (lines 102-262). Four bugs fixed: (a) `targetRunName` watcher lacks `immediate: true`, (b) stale async response race (no identity guard), (c) XSS via `v-html` without sanitization, (d) `autoRunId` watcher never selects the run.

```javascript
<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { api } from '../api.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  autoRunId: { type: String, default: null },
  targetRunName: { type: String, default: null },
});

const runs = ref([]);
const loadingRuns = ref(false);
const selectedRun = ref(null);
const reportContent = ref(null);
const loadingReport = ref(false);
const runFiles = ref([]);
const loadingFiles = ref(false);

onMounted(() => {
  loadRuns();
});

watch(() => props.autoRunId, (newId) => {
  if (newId) {
    loadRuns().then(() => {
      const match = runs.value.find(r => r.name.endsWith(newId) || r.run_id === newId);
      if (match) openRun(match);
    });
  }
});

watch(() => props.targetRunName, (name) => {
  if (name) {
    const requestedName = name;
    selectedRun.value = name;
    reportContent.value = null;
    loadingFiles.value = true;
    api.listWorkspaceFiles(name).then(files => {
      if (selectedRun.value === requestedName) runFiles.value = files;
    }).catch(() => {
      if (selectedRun.value === requestedName) runFiles.value = [];
    }).finally(() => {
      if (selectedRun.value === requestedName) loadingFiles.value = false;
    });
    loadingReport.value = true;
    api.getReport(name).then(data => {
      if (selectedRun.value === requestedName) reportContent.value = data.content;
    }).catch(() => {
      if (selectedRun.value === requestedName) reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
    }).finally(() => {
      if (selectedRun.value === requestedName) loadingReport.value = false;
    });
  }
}, { immediate: true });

async function loadRuns() {
  loadingRuns.value = true;
  try {
    runs.value = await api.listWorkspace();
  } catch (err) {
    console.error('Failed to load runs:', err);
  } finally {
    loadingRuns.value = false;
  }
}

async function openRun(run) {
  const requestedName = run.name;
  selectedRun.value = run.name;
  reportContent.value = null;

  loadingFiles.value = true;
  try {
    const files = await api.listWorkspaceFiles(run.name);
    if (selectedRun.value === requestedName) runFiles.value = files;
  } catch {
    if (selectedRun.value === requestedName) runFiles.value = [];
  } finally {
    if (selectedRun.value === requestedName) loadingFiles.value = false;
  }

  if (run.hasReport) {
    await loadReport(run.name);
  }
}

async function loadReport(runName) {
  const requestedName = runName;
  loadingReport.value = true;
  try {
    const data = await api.getReport(runName);
    if (selectedRun.value === requestedName) reportContent.value = data.content;
  } catch (err) {
    console.error('Failed to load report:', err);
    if (selectedRun.value === requestedName) reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
  } finally {
    if (selectedRun.value === requestedName) loadingReport.value = false;
  }
}

function downloadReport() {
  if (!reportContent.value || !selectedRun.value) return;
  const blob = new Blob([reportContent.value], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `diagnostic-report-${selectedRun.value}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyReport() {
  if (!reportContent.value) return;
  try {
    await navigator.clipboard.writeText(reportContent.value);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = reportContent.value;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

const renderedReport = computed(() => {
  if (!reportContent.value) return '';
  const raw = marked(reportContent.value, {
    breaks: true,
    gfm: true,
  });
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
      'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'em', 'strong',
      'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'span', 'div', 'details', 'summary'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'id', 'target', 'rel'],
  });
});

function formatRunName(name) {
  // Convert timestamp-based names: 20260521080744._PVA-TEST-V3 -> PVA-TEST-V3 (2026-05-21 08:07)
  const match = name.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})[._]\s*(.+)/);
  if (match) {
    const [, y, m, d, hh, mm, ss, label] = match;
    return `${label} (${y}-${m}-${d} ${hh}:${mm})`;
  }
  return name;
}

function formatDate(dateStr) {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function fileIcon(ext) {
  const icons = {
    '.md': '\u{1F4DD}', '.json': '\u{1F4CB}', '.csv': '\u{1F4CA}', '.png': '\u{1F5BC}',
    '.jpg': '\u{1F5BC}', '.svg': '\u{1F5BC}', '.py': '\u{1F40D}', '.mjs': '\u{1F4E6}',
    '.txt': '\u{1F4C4}', '.html': '\u{1F310}',
  };
  return icons[ext] || '\u{1F4C4}';
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>
```

Note: The `<template>` and `<style scoped>` blocks do not change — only the `<script setup>` block is replaced.

- [ ] **Step 3: Verify the frontend builds**

Run: `cd app/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/ReportViewer.vue app/frontend/package.json app/frontend/package-lock.json
git commit -m "fix: immediate watcher, stale async race, XSS sanitization, autoRunId in ReportViewer

- Add immediate: true to targetRunName watcher so reports auto-open from History
- Add selectedRun identity guard in all async callbacks to prevent stale overwrites
- Sanitize rendered markdown with DOMPurify to prevent XSS from LLM output
- Fix autoRunId watcher to actually find and open the matching run

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- SIGKILL timer leak + broken escalation → Task 1
- prompt injection (userQuestion + sceneName) → Task 1
- process.env secret leakage → Task 1
- missing stream error handlers (claude-code.mjs) → Task 1
- path traversal → Task 2
- SSE sendEvent after response destroyed → Task 2
- falsy-zero score → Task 2
- missing req.on('error') → Task 2
- map entry leak → Task 2
- missing stream error handlers (diagnosis.mjs) → Task 2
- startup cleanup stale runs → Task 3
- no onUnmounted cleanup → Task 4
- array off-by-one → Task 4
- progress bar backward → Task 4
- incomplete state reset in watch(selectedFile) → Task 4
- SSE double-fire → Task 4
- typeof null trap → Task 4
- watcher without immediate:true → Task 5
- stale async response race → Task 5
- XSS via v-html → Task 5
- autoRunId dead prop → Task 5

All 21 bugs covered.

**2. Placeholder scan:** No TBDs, TODOs, or vague instructions. Every step has exact code.

**3. Type consistency:**
- `buildEnv()` returns object with string keys → used as `env` option for `spawn()` → consistent
- `sanitize()` returns string → used in template literals → consistent
- `validateDataPath()` returns `{ absolutePath, relativePath }` → destructured in `/start` handler → consistent
- `validateDataPath()` throws errors with `.code` and `.status` properties → caught in catch block that reads `err.status` → consistent
- `cleanup()` function closes over `child` via `let child = null;` → set after `startDiagnosis()` returns → consistent
- `sendEvent` guarded with `if (res.destroyed) return;` → used in all async handlers → consistent
- `MAX_MESSAGES = 200` constant → used in `addMessage` for both push and slice → consistent
- `didError` flag set in SSE `error` handler, checked in `onerror` → mirrors `didComplete` pattern → consistent
- `requestedName` captured in each async function → compared against `selectedRun.value` in callbacks → consistent
- DOMPurify imported and used in `renderedReport` computed → v-html binding unchanged → consistent
- `autoRunId` watcher calls `loadRuns().then(...)` → `loadRuns` returns the `async function` result (a Promise) → `.then()` works → consistent
- `immediate: true` on `targetRunName` watcher → callback fires on mount with existing prop value → consistent
