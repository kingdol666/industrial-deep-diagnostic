// Claude Client — wraps the Claude Agent SDK for diagnostic runs
// Replaces the old child_process-based Claude CLI execution.

import { existsSync, readdirSync, readFileSync } from 'fs';
import { join, extname, basename, isAbsolute } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { loadOmpAgents, buildOmpSystemPrompt, buildOmpChatSystemPrompt } from './omp-engine.mjs';

// Dynamic SDK import (ESM-only module)
let queryFn = null;
let getSessionMessagesFn = null;
let getSessionInfoFn = null;
let sdkAvailable = true;

try {
  const sdk = await import('@anthropic-ai/claude-agent-sdk');
  queryFn = sdk.query;
  getSessionMessagesFn = sdk.getSessionMessages;
  getSessionInfoFn = sdk.getSessionInfo;
} catch (e) {
  sdkAvailable = false;
  logger.error(`SDK not available: ${e.message}`, { context: 'ClaudeClient' });
}

const DATA_DIR = join(PROJECT_ROOT, config.data.dir);
const WORKSPACE_DIR = join(PROJECT_ROOT, config.data.workspace_dir);
const SKILL_DIR = join(PROJECT_ROOT, config.claude.skill_dir);
const SKILL_MD = join(SKILL_DIR, 'SKILL.md');
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function sanitize(str) {
  return str.replace(/[\x00-\x08\x0A-\x1F]/g, '').trim();
}

function normalizeClaudeSessionId(value) {
  if (!value || typeof value !== 'string') return null;
  const trimmed = value.trim();
  return UUID_RE.test(trimmed) ? trimmed : null;
}

export function buildRuntimeProtocol(sceneName, reportLanguage) {
  const safeScene = sanitize(sceneName || config.diagnosis.default_scene_name);
  const languageRule = reportLanguage === 'zh'
    ? '所有 narrative、标题、分析说明、建议、summary markdown 与 report.md 必须使用中文；变量名、列名、JSON enum、代码保持英文。'
    : 'All narrative output, headings, analysis descriptions, recommendations, summary markdown, and report.md content must be written in English.';

  return `You are executing the industrial deep diagnostic skill for scene "${safeScene}".

Runtime-critical rules:
1. Treat the skill protocol as binding. Follow the full pipeline contract and do not skip, reorder, or silently omit steps.
2. Main agent orchestrates only. Sub-agent work MUST be delegated to the required specialized agents instead of being completed directly by the main agent.
3. Context building must produce ontology-grounded understanding before final diagnosis. Data analysis, diagnosis, review, report, and audit must stay aligned to the same ontology semantics.
4. Diagnosis must use competing hypotheses, temporal precedence, statistical evidence, physical mechanism, and contradiction checks. If evidence cannot discriminate, output COMPETING_SET or NEEDS_DATA instead of guessing.
5. Validate required structured artifacts and honor repair / review gates before considering the run complete.
6. Use exact absolute data paths provided by the runtime. Do not reinterpret them relative to the skill directory. All sub-agent file writes MUST use the absolute run-dir path given in the dispatch prompt — never relative paths.
7. ${languageRule}
8. If the user provides follow-up answers or continuation instructions, continue from the existing session state while preserving the same pipeline discipline.
9. Ontology asset policy: honor the ONTOLOGY DIRECTIVE in the prompt (mode reuse/extend/full). In reuse mode, copy the given store ontology into the run dir via ontology_store.mjs and re-validate with CP-2 — never rebuild, never call RAG or web research. In extend mode, build incrementally for NEW columns only and merge into the source ontology. In full mode, follow the standard pipeline. Publish the validated ontology back to the store after CP-2 passes.
10. Enhancement policy: honor the ENHANCEMENT DIRECTIVE. When deep enhancement is requested (policy on / intent hit), after Step 9 completes run the enhance orchestrator (E0-E8) on the SAME run dir — reuse the same ontology, never rebuild the baseline. When skipped, emit the enhance_skipped pipeline event.`;
}

// ── Ontology directive — appended to the user prompt for both engines ──
export function buildOntologyDirective(ontology) {
  if (!ontology || typeof ontology !== 'object') return '';
  // P1-6: the DOE intent carries profile="doe" and gets its own directive. The
  // diagnosis rendering below stays byte-identical for every other run.
  if (ontology.profile === 'doe') return buildDoeOntologyDirective(ontology);
  // Plan v2 P1.5/P2.4: watch-family profiles carry their own deterministic
  // ontology stage (the skill's ontology_prepare.py) ahead of the analysis.
  if (ontology.profile === 'stability' || ontology.profile === 'sentinel') {
    return buildWatchOntologyDirective(ontology);
  }
  const mode = ontology.mode || 'full';
  const lines = ['', '## Ontology Directive', '', `- ONTOLOGY_MODE: ${mode}`];
  if (ontology.source) lines.push(`- ONTOLOGY_SOURCE (store asset, absolute path): ${ontology.source}`);
  if (ontology.scene_key) lines.push(`- ONTOLOGY_SCENE: ${ontology.scene_key} (store v${ontology.version ?? '?'})`);
  lines.push(`- Reason: ${ontology.reason || 'n/a'}`);
  if (mode === 'reuse') {
    // Fast path (plan v5 F1/F4): the orchestrator will run the deterministic
    // fast-reuse script before dispatching any agent. Advisory only — the
    // script still gates on CP-2; a store change after run start can flip it.
    lines.push(`The orchestrator first attempts the deterministic fast path (ontology_store.mjs fast-reuse — copy + CP-2 + publish, ≤60s). If it reports fastPath:true, Step 2 is complete without dispatching any agent — do not re-describe or re-verify parameter semantics beyond CP-2. If fastPath:false, execute Phase -1 below.`);
    return lines.join('\n') + '\n';
  }
  lines.push(`Execute Phase -1 of the ontology-builder protocol exactly according to this mode. CP-2 validation is mandatory in every mode; after it passes, publish the ontology to the store:`);
  lines.push(`node .claude/shared/scripts/ontology_store.mjs publish --run-dir "<RUN_DIR>"${ontology.scene_key ? ` --scene ${ontology.scene_key}` : ''} --build-mode ${mode}`);
  return lines.join('\n') + '\n';
}

// ── Ontology directive, DOE profile (P1-6) ──────────────────────────────
// A DOE run is ontology-first and gated: the deterministic ontology stage runs
// before any statistics, and the agent must read the brief before analyzing.
// `mode` uses the DOE namespace {auto, full, reuse, extend} — `off` is refused
// in production (dev override only), so the ontology can never be silently
// blanked out of a DOE run the way it was before this fix.
export function buildDoeOntologyDirective(ontology) {
  const mode = ontology.mode || 'auto';
  const dataStage = ontology.data_stage || 'collected';
  const lines = ['', '## Ontology Directive (DOE profile)', '',
    `- ONTOLOGY_PROFILE: doe`,
    `- ONTOLOGY_MODE: ${mode}`,
    `- ONTOLOGY_DATA_STAGE: ${dataStage}`];
  if (ontology.scene_key) lines.push(`- ONTOLOGY_SCENE: ${ontology.scene_key} (store v${ontology.version ?? '?'})`);
  if (ontology.source) lines.push(`- ONTOLOGY_SOURCE (store asset, absolute path): ${ontology.source}`);
  lines.push(`- Reason: ${ontology.reason || 'n/a'}`);
  lines.push(`This run executes the thin DOE orchestration contract `.concat(
    '.claude/skills/industrial-doe-orchestrator/SKILL.md — prepare → brief → analyzer → consistency → next_design — in that order. The ontology stage is a HARD GATE: statistics must not start before it finishes.'));
  lines.push(`Run the deterministic ontology stage first (it computes the context fingerprint, looks the store up by profile=doe + scene_key + context_fp, reuses on an exact hit, extends on a changed context, otherwise builds — and writes 01_ontology/ontology.json + ontology_brief.json/.md + ontology_coverage.json):`);
  lines.push(`uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/scripts/doe_ontology_prepare.py --run-dir "<RUN_DIR>" --mode ${mode}${ontology.scene_key ? ` --scene ${ontology.scene_key}` : ''}`);
  lines.push(`Then READ 01_ontology/ontology_brief.json and write 01_profile/analysis_plan.md (scene / factors / responses / units / expected directions / confounders / limitations) — the analyzer refuses to run without both (ONTOLOGY_BRIEF_REQUIRED / ANALYSIS_PLAN_REQUIRED).`);
  if (dataStage === 'design_only') {
    lines.push(`DATA_STAGE=design_only: responses are not measured yet. Only the ontology/profile/build stages may run — never invent response behaviour or run statistics (DESIGN_ONLY_NO_RESPONSE).`);
  }
  lines.push('Ontology assets are published with profile=doe + context_fp so the next run of the same scene/context reuses them in ≤60s with zero RAG/web calls.');
  return lines.join('\n') + '\n';
}

// ── Ontology directive, watch profiles (stability / sentinel — plan v2) ──
// Same ontology-first discipline as the DOE profile, one profile per watch
// skill: prepare (fingerprint → store lookup → reuse/extend/build, declared
// priors only) writes 01_ontology/ontology.json + brief + coverage, and the
// analysis must not start before reading the brief (the analyzer/watch gate
// enforces ONTOLOGY_BRIEF_REQUIRED when mode != off).
export function buildWatchOntologyDirective(ontology) {
  const mode = ontology.mode || 'auto';
  const isStability = ontology.profile === 'stability';
  const prepareScript = isStability
    ? '.claude/skills/industrial-line-stability-report/scripts/ontology_prepare.py'
    : '.claude/skills/industrial-sentinel/scripts/sentinel_ontology_prepare.py';
  const lines = ['', '## Ontology Directive (watch profile)', '',
    `- ONTOLOGY_PROFILE: ${ontology.profile}`,
    `- ONTOLOGY_MODE: ${mode}`];
  if (ontology.scene_key) lines.push(`- ONTOLOGY_SCENE: ${ontology.scene_key} (store v${ontology.version ?? '?'})`);
  if (ontology.source) lines.push(`- ONTOLOGY_SOURCE (ontology asset path): ${ontology.source}`);
  lines.push(`- Reason: ${ontology.reason || 'n/a'}`);
  lines.push(`Run the deterministic ontology stage FIRST (fingerprint → store lookup by profile=${ontology.profile} + scene_key + context_fp → reuse on an exact hit / extend on a changed context / otherwise build a declared-prior ontology — declarations only, no RAG, no web, never invented units):`);
  lines.push(`uv run --project .claude/shared/scripts python ${prepareScript} --run-dir "<RUN_DIR>" --mode ${mode}${ontology.scene_key ? ` --scene ${ontology.scene_key}` : ''}${ontology.source ? ` --ontology "${ontology.source}"` : ''}`);
  lines.push(`Then READ 01_ontology/ontology_brief.json (+ .md) before any analysis step — units, roles, specs and their sources (user declaration vs shipped dictionary reference band) come from the brief; a column without a declared unit is reported as "单位未声明 (unit undeclared)".`);
  if (!isStability) {
    lines.push('For watch windows: build the baseline with --ontology pointing at 01_ontology/ontology.json — declared windows carry window_source="ontology_declared" and confirmation_needed=true (severity capped at warn, never high/critical). Never feed ontology values into indicators.');
  }
  lines.push('Ontology assets are published with profile=' + ontology.profile + ' + context_fp so the next run of the same scene/context reuses them in seconds with zero RAG/web calls.');
  return lines.join('\n') + '\n';
}

// ── Enhancement directive — appended to the user prompt for both engines ──
export function buildEnhancementDirective(enhancement) {
  if (!enhancement || typeof enhancement !== 'object') return '';
  const policy = enhancement.policy || 'auto';
  const lines = ['', '## Enhancement Directive', '', `- ENHANCEMENT_POLICY: ${policy}`, `- ENHANCEMENT_INTENT_HIT: ${enhancement.intentHit ? 'true' : 'false'}`];
  if (enhancement.matched?.length) lines.push(`- Matched signals: ${enhancement.matched.join(', ')}`);
  if (policy === 'on') {
    lines.push('The user requested deep enhanced diagnosis. After Step 9 (finalize) completes on the baseline, execute the E0-E8 enhancement chain on the SAME run dir:');
    lines.push('node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs --run-dir "<RUN_DIR>"');
    lines.push('If E0 reports BLOCKED (baseline artifacts incomplete), record enhancement_status.json with status=blocked and finish gracefully — do not fail the run.');
  } else if (policy === 'off') {
    lines.push('The user explicitly declined deep enhancement. Do not run E0-E8. Emit pipeline event: enhance_skipped (reason: policy off).');
  } else {
    lines.push(enhancement.intentHit
      ? 'Deep-enhancement intent detected from the user question. After Step 9 completes, execute the E0-E8 chain on the SAME run dir (same command as policy on).'
      : 'No deep-enhancement intent detected. Do not run E0-E8. Emit pipeline event: enhance_skipped (reason: no_intent).');
  }
  return lines.join('\n') + '\n';
}

// ── Analysis intent directive — appended to the user prompt for ALL engines ──
// v4 AgentWorkShop: the product has no fixed-script analysis surface. Every
// run is executed by the real agent; a non-default intent re-points the run
// at the matching skill protocol instead of the 9-stage deep-diagnosis
// pipeline. The skill's own scripts still run — but under agent control,
// reading real outputs and iterating, never as a canned HTTP wrapper.
export const ANALYSIS_INTENTS = {
  'deep-diagnosis': null, // default — full 9-stage pipeline via industrial-analysis-auto
  'stability-report': {
    skill: 'industrial-line-stability-report',
    // Folder input: the analyzer consumes one tidy table. The deterministic
    // preprocessor selects the single primary time-series table (default) or,
    // on an explicit `preprocessingMode: 'integrate_merge'` opt-in, performs
    // the gated time-axis merge (cadence gate + column audit); it never merges
    // different cadences silently.
    preprocessStep: (opts = {}) => {
      const integrate = opts.preprocessingMode === 'integrate_merge';
      const modeFlag = integrate ? '--integrate-merge' : '--stability-single-primary';
      return 'uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py'
        + ` --data-path "<INPUT_FOLDER>" --output "<RUN_DIR>/00_input" ${modeFlag} --recursive`;
    },
    unitRule: true,
  },
  'quick-screen': {
    skill: 'industrial-sentinel',
    // Deterministic HTML step — the sentinel protocol ends at alert.json +
    // watch_report.md; this builder turns them into the viewable HTML report.
    htmlStep: 'uv run --project .claude/shared/scripts python .claude/skills/industrial-sentinel/scripts/build_screen_report.py --run-dir "<RUN_DIR>"',
    unitRule: true,
  },
  'doe-analysis': { skill: 'industrial-doe-analyzer' },
  'experience-mining': { skill: 'industrial-tuning-memory' },
  'optimizer-campaign': { skill: 'industrial-optimizer-loop' },
};

export function resolveAnalysisIntent(value) {
  if (value === undefined || value === null || value === '' || value === 'deep-diagnosis') {
    return 'deep-diagnosis';
  }
  return Object.prototype.hasOwnProperty.call(ANALYSIS_INTENTS, String(value))
    ? String(value)
    : null;
}

// Folder-input preprocessing policy for the stability-report intent (plan v2
// §4): single-primary selection is the default; the gated time-axis merge is
// an explicit opt-in. Any other intent + a non-empty value is a contract trap
// (accepted-then-ignored), so it is rejected explicitly — same philosophy as
// the ontology field guard.
export const PREPROCESSING_MODES = ['single_primary', 'integrate_merge'];

export function resolvePreprocessingMode(analysisIntent, rawValue) {
  const requested = typeof rawValue === 'string' ? rawValue.trim() : '';
  if (!requested) return 'single_primary';
  if (!PREPROCESSING_MODES.includes(requested)) {
    const err = new Error(
      `Unknown preprocessingMode: ${JSON.stringify(rawValue)} (supported: ${PREPROCESSING_MODES.join(', ')})`,
    );
    err.status = 400;
    err.code = 'PREPROCESSING_MODE_UNKNOWN';
    throw err;
  }
  if (analysisIntent !== 'stability-report') {
    const err = new Error(
      `preprocessingMode is only supported for analysisIntent=stability-report (got ${analysisIntent}).`,
    );
    err.status = 400;
    err.code = 'PREPROCESSING_MODE_UNSUPPORTED_INTENT';
    throw err;
  }
  return requested;
}

export function buildIntentDirective(intent, sceneName, opts = {}) {
  const resolved = resolveAnalysisIntent(intent);
  if (!resolved || resolved === 'deep-diagnosis') return '';
  const spec = ANALYSIS_INTENTS[resolved];
  // A spec step may be a static string or an opts-driven template (the
  // stability preprocessStep switches on `preprocessingMode`).
  const preprocessStep = typeof spec.preprocessStep === 'function'
    ? spec.preprocessStep(opts)
    : spec.preprocessStep;
  // Filename-grade normalization: this string lands in a command the agent
  // is told to copy-execute, so it must stay a safe single path segment.
  const safeRunScene = sanitize(sceneName || '').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 80) || 'run';
  return `
## Analysis Intent Directive

- ANALYSIS_INTENT: ${resolved}
- This run does NOT execute the default 9-stage deep-diagnosis pipeline. Do not run the industrial-analysis-auto pipeline steps, do not dispatch its sub-agent topology, and do not apply its judge/review gates — the pipeline-specific runtime rules above are superseded by this directive.
- Executing skill: ${spec.skill}. FIRST read .claude/skills/${spec.skill}/SKILL.md in full (plus the references it points to) and follow that protocol as the binding contract of this run.
- Create the run workspace first, then keep every artifact inside it:
  node .claude/skills/industrial-analysis-auto/scripts/setup.mjs --name "${safeRunScene}" --mode fast --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
- Perform the analysis for real on the data files listed above: run the skill's scripts as tools against the actual data, read their real outputs, and iterate on what they return. Every number you report must come from a tool executed during this run — never fabricate, hard-code, or copy example values.
${preprocessStep ? `- Folder input (MANDATORY, before the skill analysis): run \`${preprocessStep}\` with <INPUT_FOLDER> set to the folder path shown in ## Data and <RUN_DIR> set to the run workspace. Analyze the canonical primary table it produces; do not merge files or sampling cadences manually.` : ''}
${spec.unitRule ? '- Unit rule: only use units declared by report_context / ontology / input columns. If a unit is absent, write "单位未声明 (unit undeclared)" — never infer mm/µm/°C from the product name or experience.' : ''}
${spec.htmlStep ? `- HTML report step (MANDATORY, after the analysis, before writing report.md): run \`${spec.htmlStep}\` with <RUN_DIR> set to the run workspace. If uv is unavailable, execute the same script with the shared venv python (.claude/shared/scripts/.venv/Scripts/python.exe on Windows, .venv/bin/python elsewhere). Verify the HTML file path it prints exists before finishing.` : ''}
- Finish by writing report.md at the root of the run dir: a narrative in the report language that answers the analysis question, citing only artifacts produced in this run.
`;
}

export function buildSystemPrompt(sceneName, reportLanguage, skillContent) {
  const runtimeProtocol = buildRuntimeProtocol(sceneName, reportLanguage);
  if (!skillContent) return runtimeProtocol;

  return `${runtimeProtocol}

Authoritative skill reference excerpt:
${skillContent}`;
}

function discoverDataFiles(folderPath) {
  const absolutePath = isAbsolute(folderPath)
    ? folderPath
    : join(PROJECT_ROOT, folderPath);
  const entries = readdirSync(absolutePath);
  const exts = config.data.allowed_extensions;
  return entries
    .filter(e => exts.includes(extname(e).toLowerCase()))
    .map(e => join(absolutePath, e))
    .sort();
}

export function buildPrompt(sceneName, userQuestion, target, reportLanguage, followUpMessage) {
  const safeScene = sanitize(sceneName || config.diagnosis.default_scene_name);
  const safeQuestion = sanitize(userQuestion || '');

  let dataDescription;
  if (target.mode === 'multi') {
    const files = target.files.map(f => sanitize(f)).join('\n  - ');
    dataDescription = `${target.files.length} files:\n  - ${files}`;
  } else if (target.mode === 'folder') {
    const safeFolder = sanitize(target.folderPath);
    const fileList = target.dataFiles.map(f => sanitize(basename(f))).join(', ');
    dataDescription = `Folder (absolute path): ${safeFolder}\n  Files (${target.dataFiles.length}): ${fileList}`;
  } else {
    dataDescription = `File (absolute path): ${sanitize(target.dataPath || '(missing data path)')}`;
  }

  const langRule = reportLanguage === 'zh'
    ? 'IMPORTANT: Write ALL narrative text, headings, analysis descriptions, recommendations, and report.md content in Chinese (中文). Keep technical terms, variable names, column names, and code in English.'
    : 'Write all output in English.';

  const basePrompt = `Industrial deep diagnostic run for scene "${safeScene}" — follow the skill protocol provided in your system prompt.

## Data

${dataDescription}

Use the exact absolute path(s) above when reading data files. Do not reinterpret them relative to any skill directory.

## Analysis Question

${safeQuestion || config.diagnosis.default_question}

## Language

${langRule}`;

  if (followUpMessage) {
    return `${basePrompt}

## Follow-Up Instruction

The previous run ended. Additional instruction from user:

${sanitize(followUpMessage)}

Please address the follow-up instruction above and continue the analysis.`;
  }

  return basePrompt;
}

function buildResumePrompt(followUpMessage) {
  return sanitize(followUpMessage || 'Continue.');
}

// ── Dangerous Command Detection ──
const DANGEROUS_PATTERNS = config.security.dangerous_patterns.map(rule => ({
  pattern: new RegExp(rule.pattern),
  level: rule.level,
  desc: rule.desc,
}));

export function isDangerousCommand(command) {
  if (!command || typeof command !== 'string') return null;
  for (const rule of DANGEROUS_PATTERNS) {
    if (rule.pattern.test(command)) {
      return { level: rule.level, desc: rule.desc, match: command.match(rule.pattern)[0] };
    }
  }
  return null;
}

// ── Disallowed tool names ──
const disallowedTools = [];

// ── Active query objects (for close and stdin writing) ──
const activeQueries = new Map();

// ── Shared: resolve analysis target into absolute paths ──
// Returns { dataPaths, promptTarget } — throws DATA_NOT_FOUND / NO_DATA_FOUND.
export function resolveAnalysisTarget(analysisTarget) {
  const dataPaths = [];
  const promptTarget = { ...analysisTarget };

  function resolveDataPath(p) {
    if (isAbsolute(p)) return p;
    const fromRoot = join(PROJECT_ROOT, p);
    if (existsSync(fromRoot)) return fromRoot;
    const fromData = join(DATA_DIR, p);
    if (existsSync(fromData)) return fromData;
    return fromRoot;
  }

  if (analysisTarget.mode === 'resume') {
    // The existing session already has the diagnostic data context.
    return { dataPaths, promptTarget };
  }

  if (analysisTarget.mode === 'multi') {
    promptTarget.files = [];
    for (const dp of analysisTarget.files) {
      const abs = resolveDataPath(dp);
      if (!existsSync(abs)) {
        const err = new Error(`Data path not found: ${abs}`);
        err.code = 'DATA_NOT_FOUND';
        throw err;
      }
      dataPaths.push(abs);
      promptTarget.files.push(abs);
    }
  } else if (analysisTarget.mode === 'folder') {
    const absFolder = resolveDataPath(analysisTarget.folderPath);
    if (!existsSync(absFolder)) {
      const err = new Error(`Folder not found: ${absFolder}`);
      err.code = 'DATA_NOT_FOUND';
      throw err;
    }
    const folderFiles = discoverDataFiles(absFolder);
    if (folderFiles.length === 0) {
      const err = new Error(`No data files found in folder: ${absFolder}`);
      err.code = 'NO_DATA_FOUND';
      throw err;
    }
    dataPaths.push(...folderFiles);
    promptTarget.folderPath = absFolder;
    promptTarget.dataFiles = folderFiles;
  } else {
    const abs = resolveDataPath(analysisTarget.dataPath);
    if (!existsSync(abs)) {
      const err = new Error(`Data path not found: ${abs}`);
      err.code = 'DATA_NOT_FOUND';
      throw err;
    }
    dataPaths.push(abs);
    promptTarget.dataPath = abs;
  }

  return { dataPaths, promptTarget };
}

// ── Start Diagnosis via SDK ──
export function startDiagnosis({
  analysisTarget, userQuestion, sceneName,
  runId, maxTurns = 0, timeoutMinutes = 0,
  reportLanguage, followUpMessage, sessionId = null,
  ontology = null, enhancement = null,
  analysisIntent = 'deep-diagnosis',
  preprocessingMode = null,
  model = null, permissionMode = null,
}) {
  if (!sdkAvailable || !queryFn) {
    throw new Error('Claude Agent SDK not available. Install with: npm install @anthropic-ai/claude-agent-sdk');
  }

  const lang = reportLanguage || config.diagnosis.default_language;
  const timeout = timeoutMinutes || config.claude.timeout_minutes;

  const { dataPaths, promptTarget } = resolveAnalysisTarget(analysisTarget);

  const resumeSessionId = normalizeClaudeSessionId(sessionId);

  // Resume must be a clean continuation: do not re-inject the diagnostic
  // system prompt, skill text, or original data context after the first turn.
  let systemPrompt;
  if (!resumeSessionId) {
    let skillContent = '';
    if (existsSync(SKILL_MD)) {
      try {
        skillContent = readFileSync(SKILL_MD, 'utf-8').slice(0, 8000);
      } catch { /* ignore */ }
    }
    systemPrompt = buildSystemPrompt(sceneName, lang, skillContent);
  }

  const prompt = resumeSessionId
    ? buildResumePrompt(followUpMessage)
    : buildPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)
      + buildIntentDirective(analysisIntent, sceneName, { preprocessingMode })
      + buildOntologyDirective(ontology)
      + buildEnhancementDirective(enhancement);

  // Build SDK options — model and permissionMode are per-run switchable
  // (validated against the harness catalog upstream). bypassPermissions is
  // the pipeline default and needs allowDangerouslySkipPermissions; the
  // other SDK modes must NOT set that flag.
  const effPermissionMode = permissionMode || 'bypassPermissions';
  const options = {
    cwd: PROJECT_ROOT,
    model: model || config.claude.model,
    permissionMode: effPermissionMode,
    allowDangerouslySkipPermissions: effPermissionMode === 'bypassPermissions',
    includePartialMessages: true,
    forwardSubagentText: true,
    maxTurns: maxTurns > 0 ? maxTurns : undefined,
  };

  if (resumeSessionId) {
    options.resume = resumeSessionId;
  }

  if (systemPrompt) options.systemPrompt = systemPrompt;

  // Start the SDK query
  const query = queryFn({ prompt, options });

  // Register for later reference
  activeQueries.set(runId, query);

  const getSessionId = () => query.sessionId || null;

  return { query, dataPaths, prompt, getSessionId, runId, isResume: !!resumeSessionId };
}

export function startSessionChat({ runId, sessionId, message, maxTurns = 1, harness = 'claude' }) {
  if (!sdkAvailable || !queryFn) {
    throw new Error('Claude Agent SDK not available. Install with: npm install @anthropic-ai/claude-agent-sdk');
  }
  const resumeSessionId = normalizeClaudeSessionId(sessionId);
  if (!resumeSessionId) {
    const err = new Error('No valid Claude session ID for selected diagnosis session');
    err.status = 400;
    throw err;
  }

  const isOmp = harness === 'omp';
  const options = {
    cwd: PROJECT_ROOT,
    model: config.claude.model,
    permissionMode: 'bypassPermissions',
    allowDangerouslySkipPermissions: true,
    includePartialMessages: true,
    forwardSubagentText: true,
    maxTurns,
    resume: resumeSessionId,
  };

  if (isOmp) {
    // OMP harness continuation: keep the same OMP agent topology available
    // in the resumed process so delegated OMP agents stay invocable.
    const { agents, count } = loadOmpAgents();
    if (count > 0) options.agents = agents;
    options.systemPrompt = buildOmpChatSystemPrompt();
  }

  const query = queryFn({
    prompt: sanitize(message || ''),
    options,
  });

  activeQueries.set(runId, query);
  return { query, runId, sessionId: resumeSessionId };
}

// ── Write tool_result to the query (for AskUserQuestion answers) ──
export async function writeAnswer(runId, message) {
  const query = activeQueries.get(runId);
  if (!query) return false;

  try {
    // Send the user message as an async iterable
    await query.streamInput(
      (async function* () {
        yield message;
      })()
    );
    return true;
  } catch (e) {
    logger.error(`writeAnswer failed: ${e.message}`, { context: 'ClaudeClient', runId });
    return false;
  }
}

// ── Close / kill a query ──
export function closeQuery(runId) {
  const query = activeQueries.get(runId);
  if (query) {
    try { query.close(); } catch { /* ignore */ }
    activeQueries.delete(runId);
  }
}

// ── Parse SDK stream event into standardized format ──
export function parseStreamEvent(message) {
  // The SDK emits various message types:
  // - SDKAssistantMessage: { type: 'assistant', message: { content: [...] } }
  // - SDKUserMessage: { type: 'user', message: { role: 'user', content: [...] } }
  // - SDKResultMessage: { type: 'result', subtype, duration_ms, num_turns, total_cost_usd, ... }
  // - SDKPartialAssistantMessage: { type: 'stream_event', ... } (partial text chunks)

  if (!message || typeof message !== 'object') return null;

  const type = message.type;

  if (type === 'assistant') {
    return { type: 'assistant', message: message.message };
  } else if (type === 'user') {
    return { type: 'user', message: message.message };
  } else if (type === 'result') {
    return {
      type: 'result',
      subtype: message.subtype,
      duration_ms: message.duration_ms,
      num_turns: message.num_turns,
      total_cost_usd: message.total_cost_usd,
      stop_reason: message.stop_reason,
      session_id: message.session_id,
    };
  } else if (type === 'system') {
    return { type: 'system', subtype: message.subtype || 'system', ...message };
  } else if (type === 'stream_event') {
    return { type: 'stream_event', event: message.event };
  }

  // Fallback — pass through
  return message;
}

// ── Extract report path from output ──
export function extractReportPath(output) {
  const match = output.match(/workspace\/diagnostic-runs\/[^\s]+\/report\.md/);
  return match ? match[0] : null;
}

// ── Legacy compat: registerChild / writeAnswer (for diagnosis.service.mjs) ──
const _noop = {};
export function registerChild(runId, _query) {
  // Stub — SDK manages child processes internally
  activeQueries.set(runId, _query);
}

export async function getSessionMessages(sessionId) {
  if (!getSessionMessagesFn) {
    throw new Error('SDK not available — cannot fetch session messages');
  }
  return getSessionMessagesFn(sessionId, { dir: PROJECT_ROOT, includeSystemMessages: true });
}

export async function getSessionInfo(sessionId) {
  if (!getSessionInfoFn) {
    throw new Error('SDK not available — cannot fetch session info');
  }
  return getSessionInfoFn(sessionId, { dir: PROJECT_ROOT });
}

export { PROJECT_ROOT, DATA_DIR, WORKSPACE_DIR };
