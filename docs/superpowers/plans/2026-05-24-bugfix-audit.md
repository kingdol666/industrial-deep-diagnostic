# Audit Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 12 bugs identified in end-to-end audit: data extraction, path matching, SSE race conditions, unused dependencies, hardcoded paths, prompt hygiene, error handling, UX gaps.

**Architecture:** Six targeted file modifications. No new files. Each fix is isolated and backward-compatible. Backend fixes are in `app/backend/src/` (claude-code.mjs, routes/diagnosis.mjs, package.json). Frontend fixes are in `app/frontend/src/` (DiagnosisPanel.vue, App.vue, ReportViewer.vue).

**Tech Stack:** Node.js/Express, Vue 3, better-sqlite3, Server-Sent Events

---

### Task 1: Fix `claude-code.mjs` — hardcoded paths, prompt hygiene, CLI check, timeout

**Files:**
- Modify: `app/backend/src/claude-code.mjs`

- [ ] **Step 1: Replace the entire file**

The current file has four problems: (a) `buildPrompt` embeds absolute machine-specific paths, (b) the prompt duplicates the skill's own workflow instructions, (c) no pre-flight check that `claude` CLI is in PATH, (d) no wall-clock timeout. The rewrite below fixes all four.

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

function buildPrompt(sceneName, userQuestion) {
  return `Execute the /industrial-deep-diagnostic skill on the data file in the workspace.

## Input

- **Scene name**: ${sceneName}
- **Analysis question**: ${userQuestion || 'Perform a comprehensive root cause analysis'}

## Instructions

1. Invoke the /industrial-deep-diagnostic skill with the scene name "${sceneName}"
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

  const prompt = buildPrompt(sceneName, userQuestion);

  const claudeArgs = [
    '-p', prompt,
    '--output-format', 'stream-json',
    '--max-turns', String(maxTurns),
    '--verbose',
    '--allowedTools', 'Read(/**),Write(/**),Edit(/**),Bash(/**),Skill(industrial-deep-diagnostic),WebSearch,WebFetch',
  ];

  const child = spawn(claudeBin, claudeArgs, {
    cwd: PROJECT_ROOT,
    env: {
      ...process.env,
      FORCE_COLOR: '0',
      NO_COLOR: '1',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  const timeout = setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGTERM');
      setTimeout(() => { if (!child.killed) child.kill('SIGKILL'); }, 5000);
    }
  }, timeoutMinutes * 60 * 1000);

  child.on('close', () => clearTimeout(timeout));
  child.on('error', () => clearTimeout(timeout));

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
git commit -m "fix: hardcoded paths, prompt hygiene, CLI check, timeout in claude-code.mjs

- Replace absolute paths with relative paths in prompt (cwd-aware)
- Simplify prompt to delegate to the skill instead of duplicating workflow
- Add pre-flight check for Claude Code CLI in PATH
- Add configurable wall-clock timeout (default 30 min)
- Add --allowedTools to scope permissions
- Add structured error codes for missing data/skill/cli

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Fix `diagnosis.mjs` — dataFolder extraction, findLatestRunDir, SSE guards

**Files:**
- Modify: `app/backend/src/routes/diagnosis.mjs`

- [ ] **Step 1: Fix `dataFolder` extraction (line 40)**

Change:
```javascript
dataFolder: dataPath.includes('/') ? dataPath.split('/')[1] : null,
```
To:
```javascript
const pathParts = dataPath.split('/');
const dataFolder = pathParts.length > 2 ? pathParts[1] : null;
```

And use `dataFolder` in the insert:
```javascript
stmts.insertRun.run({
  runId,
  name,
  sceneName: scene,
  dataPath,
  dataFolder,
  userQuestion: userQuestion || '',
  model: 'claude-opus-4-7',
  maxTurns: maxTurns || 200,
});
```

- [ ] **Step 2: Fix `findLatestRunDir` — use suffix-anchored regex instead of loose `includes`**

Change the matching line from:
```javascript
if (entry.includes(sceneName)) {
```
To:
```javascript
const escapedName = sceneName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const dirPattern = new RegExp(`_${escapedName}$`);
if (dirPattern.test(entry)) {
```

- [ ] **Step 3: Fix SSE guards — send proper SSE events instead of JSON**

Change the two early-return guards (lines 57-67) from `res.json(...)` to proper SSE init + status event + close:

```javascript
// Guard: run already completed or failed -> send SSE status event then close
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

// Guard: run already active -> send SSE error then close
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
```

- [ ] **Step 4: Verify syntax**

Run: `node --check "app/backend/src/routes/diagnosis.mjs"`
Expected: no output (exit 0)

- [ ] **Step 5: Commit**

```bash
git add app/backend/src/routes/diagnosis.mjs
git commit -m "fix: dataFolder extraction, findLatestRunDir matching, SSE guards in diagnosis.mjs

- Fix dataFolder to only set for nested paths (length > 2)
- Use suffix-anchored regex for workspace directory matching
- Send proper SSE events instead of JSON for completed/failed/active guards

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Fix `DiagnosisPanel.vue` — SSE race condition, message truncation UX

**Files:**
- Modify: `app/frontend/src/components/DiagnosisPanel.vue`

- [ ] **Step 1: Add `didComplete` flag and fix the `onerror` handler**

In `<script setup>`, add a flag after `let eventSource = null;`:

```javascript
let didComplete = false;
```

In the `complete` event handler, set the flag at the very top:

```javascript
eventSource.addEventListener('complete', (e) => {
  didComplete = true;
  const d = JSON.parse(e.data);
  completed.value = true;
  isRunning.value = false;
  progressPct.value = 100;
  result.value = d;
  addMessage('system', `Completed! Score: ${d.score || 'N/A'}, Verdict: ${d.verdict || 'N/A'}`);
  closeSSE();
});
```

In the `onerror` handler, check the flag:

```javascript
eventSource.onerror = () => {
  if (didComplete) return;
  if (isRunning.value) {
    failed.value = true;
    isRunning.value = false;
    addMessage('error', 'Connection lost');
    closeSSE();
  }
};
```

- [ ] **Step 2: Add message truncation indicator**

Add a ref after `let msgCount = 0;`:

```javascript
const truncated = ref(false);
```

Reset it in `startDiagnosis` (after `msgCount = 0;`):

```javascript
truncated.value = false;
```

In `addMessage`, set the flag when truncating:

```javascript
function addMessage(type, content) {
  msgCount++;
  if (messages.value.length >= 200) {
    truncated.value = true;
  }
  messages.value = messages.value.slice(-200);
  messages.value.push({ type, content });
  nextTick(() => {
    if (outputStream.value) {
      outputStream.value.scrollTop = outputStream.value.scrollHeight;
    }
  });
}
```

- [ ] **Step 3: Add the truncation notice in the template**

In the output-card div, add after the `output-stream` div and before the `v-if="isRunning"` div:

```html
<div v-if="truncated" class="truncation-notice">
  Output truncated — showing last 200 messages
</div>
```

Add the corresponding style in `<style scoped>`:

```css
.truncation-notice {
  font-size: 11px;
  color: var(--yellow);
  background: rgba(210, 153, 34, 0.08);
  padding: 4px 12px;
  border-radius: 4px;
  margin-top: 8px;
  text-align: center;
}
```

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/DiagnosisPanel.vue
git commit -m "fix: SSE race condition and message truncation UX in DiagnosisPanel

- Add didComplete flag to prevent onerror from overriding successful completion
- Add visual truncation notice when output exceeds 200 messages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Fix `App.vue` — forward `reportPath` in `onOpenReport`

**Files:**
- Modify: `app/frontend/src/App.vue`

- [ ] **Step 1: Add `openReportPath` ref and forward to ReportViewer**

Add a new ref after `const autoOpenRunId = ref(null);`:

```javascript
const openReportPath = ref(null);
```

Update `onOpenReport` to store the path:

```javascript
function onOpenReport(reportPath) {
  openReportPath.value = reportPath;
  currentTab.value = 'reports';
}
```

Update `onDiagnosisStarted` to also forward the completed report path later. Change the emit name to be more specific — actually the ReportViewer needs the workspace run name, not the full path. Update the `ReportViewer` binding to accept a `targetRun` prop:

```html
<ReportViewer
  v-if="currentTab === 'reports'"
  :auto-run-id="autoOpenRunId"
  :target-run-name="openReportPath"
/>
```

Wait — `openReportPath` is cleared when switching away and back. Let me use a different approach. Instead of a reactive prop that gets lost, have `DiagnosisPanel` emit a `completed` event with the report path, and App forwards it.

Actually, the simplest correct fix: the `onOpenReport` callback from HistoryList already provides the `reportPath` (from the DB record's `report_path` field). Extract the workspace run name from it and pass it:

```javascript
function onOpenReport(reportPath) {
  if (reportPath) {
    // Extract run directory name from path like "workspace/diagnostic-runs/20260521..._name/report.md"
    const parts = reportPath.split('/');
    openReportPath.value = parts[parts.length - 2] || '';
  }
  currentTab.value = 'reports';
}
```

And bind it to ReportViewer's `targetRunName` prop:

```html
<ReportViewer
  v-if="currentTab === 'reports'"
  :auto-run-id="autoOpenRunId"
  :target-run-name="openReportPath"
/>
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/App.vue
git commit -m "fix: forward reportPath from HistoryList to ReportViewer

- Extract workspace run name from report path
- Pass target-run-name prop to ReportViewer for auto-opening

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Fix `ReportViewer.vue` — auto-open report by target run name

**Files:**
- Modify: `app/frontend/src/components/ReportViewer.vue`

- [ ] **Step 1: Add `targetRunName` prop and watcher**

Add the new prop:

```javascript
const props = defineProps({
  autoRunId: { type: String, default: null },
  targetRunName: { type: String, default: null },
});
```

Add a watcher that auto-opens when targetRunName is set:

```javascript
watch(() => props.targetRunName, (name) => {
  if (name) {
    selectedRun.value = name;
    reportContent.value = null;
    loadingFiles.value = true;
    api.listWorkspaceFiles(name).then(files => {
      runFiles.value = files;
    }).catch(() => {
      runFiles.value = [];
    }).finally(() => {
      loadingFiles.value = false;
    });
    api.getReport(name).then(data => {
      reportContent.value = data.content;
    }).catch(() => {
      reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
    }).finally(() => {
      loadingReport.value = false;
    });
  }
});
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/components/ReportViewer.vue
git commit -m "fix: auto-open report by target run name in ReportViewer

- Add targetRunName prop to auto-open specific workspace runs
- Watcher triggers report loading when prop changes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Fix `package.json` — remove unused `@anthropic-ai/claude-code` dependency

**Files:**
- Modify: `app/backend/package.json`

- [ ] **Step 1: Remove the unused dependency line**

Delete this line from the `dependencies` block:
```
"@anthropic-ai/claude-code": "^1.0.0",
```

- [ ] **Step 2: Commit**

```bash
git add app/backend/package.json
git commit -m "chore: remove unused @anthropic-ai/claude-code dependency

The backend spawns the globally installed 'claude' CLI directly,
not the npm SDK package.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- dataFolder extraction → Task 2 Step 1
- findLatestRunDir matching → Task 2 Step 2
- SSE JSON guards → Task 2 Step 3
- SSE race condition → Task 3 Step 1
- unused dependency → Task 6 Step 1
- hardcoded paths → Task 1
- prompt hygiene → Task 1
- CLI check → Task 1
- timeout → Task 1
- message truncation → Task 3 Step 2-3
- onOpenReport → Task 4
- auto-open report → Task 5

**2. Placeholder scan:** No TBDs, TODOs, or vague instructions. Every step has exact code.

**3. Type consistency:**
- `targetRunName` prop defined in Task 5, consumed in Task 4's template update → consistent
- `didComplete` flag defined and checked in same task → consistent
- `truncated` ref defined, set, and used in template → consistent
- Error codes (`DATA_NOT_FOUND`, `SKILL_NOT_FOUND`, `CLAUDE_NOT_FOUND`) defined in Task 1 → no consumers yet, but structured for future use
- `timeoutMinutes` parameter added to `startDiagnosis` signature → caller in diagnosis.mjs doesn't pass it (uses default 30), which is fine
- `findClaudeCLI` returns `null` on failure → caller checks for falsy value → consistent
- `buildPrompt` signature changed from `(dataPath, userQuestion, sceneName)` to `(sceneName, userQuestion)` → caller in `startDiagnosis` updated to match
