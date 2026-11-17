#!/usr/bin/env node
// append-pipeline-event.mjs — Append structured pipeline events and keep
// run_manifest.json in sync with execution state.
//
// Robustness contract (2026-10-17):
//   - run_manifest.json is written atomically (temp file + rename) — a crash
//     mid-write can no longer leave a truncated manifest that hard-blocks the
//     repair loop.
//   - If run_manifest.json is corrupt/unreadable, the manifest is rebuilt from
//     .pipeline_events.jsonl (which is the append-only source of truth), the
//     corrupt file is backed up as run_manifest.json.corrupt-<ts>, and the
//     rebuilt manifest carries `rebuilt_from_events: true`. Only when the JSONL
//     is ALSO missing/unreadable does the script keep its hard exit.
//   - Corrupt JSONL lines are skipped with a warning on read paths — never fatal.
//
// Usage examples:
//   node append-pipeline-event.mjs <run_dir> --event agent_start --agent data-processor
//   node append-pipeline-event.mjs <run_dir> --event agent_complete --agent reporter --files report.md,run_summary.json
//   node append-pipeline-event.mjs <run_dir> --event repair_spawn --agent main-agent --step diagnostician --data '{"source":"judge","diag_iters_total":1}'
//   node append-pipeline-event.mjs <run_dir> --event artifact_check_complete --agent main-agent --step present --status PASS

import fs from 'fs';
import { join, resolve, basename } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

const VALID_EVENTS = new Set([
  'run_initialized',
  'step_start',
  'step_complete',
  'agent_start',
  'agent_complete',
  'dependency_wait',
  'dependency_ready',
  'clarification_auto_inferred',
  'clarification_user_confirmed',
  'repair_spawn',
  'repair_cap_reached',
  'artifact_finalize_start',
  'artifact_finalize_complete',
  'artifact_check_complete',
  // documented conditional-stage skips (SKILL.md Step 9.5 / Step 10):
  // non-blocking degrade markers — never gate run_completed
  'experience_skipped',
  'enhance_skipped',
  'run_completed',
  'run_failed'
]);

const AGENT_TO_STEP = {
  'context-builder': 'context_builder',
  'data-processor': 'data_processor',
  diagnostician: 'diagnostician',
  judge: 'judge',
  reporter: 'reporter',
  'report-reviewer': 'audit',
  'main-agent': null
};

const STEP_PREREQUISITES = {
  inspect: ['setup'],
  context_builder: ['inspect'],
  clarification_gate: ['context_builder'],
  data_processor: ['context_builder'],
  diagnostician: ['data_processor'],
  judge: ['diagnostician'],
  reporter: ['judge'],
  audit: ['reporter'],
  present: ['audit']
};

function flag(name) {
  const index = args.indexOf(name);
  return index === -1 ? undefined : args[index + 1];
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

/** 读取原始文本（区分「读不到文件」与「内容不是 JSON」——重建逻辑需要两者）。 */
function readText(pathLike) {
  try {
    return { ok: true, text: fs.readFileSync(pathLike, 'utf8') };
  } catch (error) {
    return { ok: false, error };
  }
}

/** 原子写 JSON：同目录唯一后缀临时文件 → renameSync 覆盖目标。
 *  崩溃/并发只会留下一个孤儿 tmp，目标文件永远是完整的一代。 */
function writeJson(pathLike, data) {
  const tmp = `${pathLike}.tmp-${process.pid}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  fs.writeFileSync(tmp, `${JSON.stringify(data, null, 2)}\n`);
  try {
    fs.renameSync(tmp, pathLike);
  } catch (error) {
    try { fs.unlinkSync(tmp); } catch (_) { /* ignore */ }
    throw error;
  }
}

function timestampSuffix() {
  return new Date().toISOString().replace(/[:.]/g, '-'); // Windows 文件名安全
}

/** 事件日志读取：损坏行跳过并告警（单行损坏绝不能中断重建/审计）。 */
function readEventsFile(logPath) {
  const read = readText(logPath);
  if (!read.ok) return { events: [], corruptLines: 0, unreadable: true, error: read.error };
  const events = [];
  let corruptLines = 0;
  const lines = read.text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) continue;
    try {
      const ev = JSON.parse(line);
      if (ev && typeof ev === 'object' && !Array.isArray(ev)) events.push(ev);
      else { corruptLines += 1; console.error(`WARNING: skipping non-object .pipeline_events.jsonl line ${i + 1} in ${logPath}`); }
    } catch (_) {
      corruptLines += 1;
      console.error(`WARNING: skipping corrupt .pipeline_events.jsonl line ${i + 1} in ${logPath}`);
    }
  }
  return { events, corruptLines, unreadable: false };
}

// 标准管线步骤清单（与 setup.mjs 的 pipelineSteps 同源）——重建 steps[] 的骨架，
// 保证 index/owner 与初始 manifest 一致；事件里出现的新步骤追加在尾部。
const PIPELINE_STEPS = [
  { step: 'setup', owner: 'main-agent' },
  { step: 'hetero_preprocess', owner: 'main-agent' },
  { step: 'inspect', owner: 'main-agent' },
  { step: 'context_builder', owner: 'context-builder' },
  { step: 'clarification_gate', owner: 'main-agent' },
  { step: 'data_processor', owner: 'data-processor' },
  { step: 'diagnostician', owner: 'diagnostician' },
  { step: 'judge', owner: 'judge' },
  { step: 'reporter', owner: 'reporter' },
  { step: 'audit', owner: 'report-reviewer' },
  { step: 'present', owner: 'main-agent' }
];
const STEP_OWNER = new Map(PIPELINE_STEPS.map((item) => [item.step, item.owner]));

// delivery_contract 是常量契约（setup.mjs 写入的同一清单），事件无法证明它；
// 留空会让 pipeline-finalize 的 delivery-contract 检查静默空转（required=[] →
// 永远 VALID），因此按契约默认值重建，并用 rebuilt_from_events 标记来源。
const DEFAULT_REQUIRED_ARTIFACTS = [
  '00_input/run_config.json',
  '00_input/input_manifest.json',
  '01_ontology/ontology.json',
  '02_processed/scenario_classification.json',
  '02_processed/anomaly_report.json',
  '02_processed/data_analysis_conclusion.json',
  '03_figures/plot_manifest.json',
  '03_figures/visual_analysis.json',
  '03_figures/image_captions.json',
  '04_diagnostics/diagnosis.json',
  '04_diagnostics/evidence.json',
  '04_diagnostics/confidence.json',
  '04_diagnostics/reasoning_chain.json',
  '05_review/judge_feedback.json',
  'report.md',
  'run_summary.json',
  'optimizer.md',
  'evidence_closure_report.json'
];

/**
 * run_manifest.json 损坏/不可读时，从 .pipeline_events.jsonl（append-only 事实源）
 * 重建最小可用清单：只写事件能证明的事实（状态、步骤进度、repair 计数、
 * artifact 检查与跳阶段记录、run_id/时间戳），无法证明的部分保持缺省，
 * 并打 `rebuilt_from_events: true` 标记。
 *
 * @returns {{ok:true, manifest, backupPath, events, corruptLines} | {ok:false, reason}}
 */
function rebuildManifestFromEvents({ manifestPath, corruptText }) {
  const logPath = join(runDir, '.pipeline_events.jsonl');
  const { events, corruptLines, unreadable } = readEventsFile(logPath);
  if (unreadable) return { ok: false, reason: `.pipeline_events.jsonl unreadable at ${logPath}` };
  if (events.length === 0) return { ok: false, reason: `.pipeline_events.jsonl has no parsable events at ${logPath}` };

  const init = events.find((ev) => ev.event === 'run_initialized') || null;
  const steps = new Map();
  const skippedStages = [];
  let diagIters = 0;
  let repairSpawns = 0;
  let finalizeRuns = 0;
  let capReached = false;
  let lastArtifactCheck = null;
  let runCompleted = false;
  let runFailed = false;
  let lastEvent = null;
  let currentStep = init?.step || null;
  let currentOwner = init?.agent || null;

  for (const ev of events) {
    if (ev.step) {
      if (!steps.has(ev.step)) {
        steps.set(ev.step, {
          step: ev.step,
          owner: STEP_OWNER.get(ev.step) || ev.agent || 'main-agent',
          status: 'pending',
          attempts: 0,
          started_at: null,
          completed_at: null,
          last_event: null,
          outputs: [],
          notes: []
        });
      }
      const rec = steps.get(ev.step);
      if (ev.event === 'step_start' || ev.event === 'agent_start') {
        // 与主流程同一回退守卫：已完成的步骤不被迟到的 start 翻回 in_progress
        if (!['completed', 'completed_with_errors'].includes(rec.status)) {
          rec.status = 'in_progress';
          rec.started_at = rec.started_at || ev.timestamp || null;
          rec.attempts += 1;
          rec.last_event = ev.event;
        }
      } else if (ev.event === 'step_complete' || ev.event === 'agent_complete') {
        rec.status = ev.errors ? 'completed_with_errors' : 'completed';
        rec.completed_at = ev.timestamp || null;
        rec.last_event = ev.event;
        rec.outputs = Array.from(new Set([...(rec.outputs || []), ...(Array.isArray(ev.files_written) ? ev.files_written : [])]));
        if (ev.errors) rec.notes.push(`errors:${ev.errors}`);
      } else if (ev.event.startsWith('clarification_')) {
        rec.status = 'completed';
        rec.completed_at = ev.timestamp || null;
        rec.last_event = ev.event;
        rec.attempts = Math.max(rec.attempts || 0, 1);
      }
      if (['step_start', 'agent_start', 'step_complete', 'agent_complete'].includes(ev.event)) {
        currentStep = ev.step;
        currentOwner = ev.agent || STEP_OWNER.get(ev.step) || currentOwner;
      }
    }
    if (ev.event === 'repair_spawn') { diagIters += 1; repairSpawns += 1; }
    if (ev.event === 'repair_cap_reached') capReached = true;
    if (ev.event === 'artifact_finalize_start') finalizeRuns += 1;
    if (ev.event === 'artifact_finalize_complete') { currentStep = 'present'; currentOwner = 'main-agent'; }
    if (ev.event === 'artifact_check_complete') {
      lastArtifactCheck = ev.status || ev.integrity_check || 'unknown';
      if (ev.skipped_stage && ev.reason) {
        const record = { stage: ev.skipped_stage, reason: ev.reason, event: ev.event };
        const index = skippedStages.findIndex((item) => item.stage === record.stage);
        if (index >= 0) skippedStages[index] = record;
        else skippedStages.push(record);
      }
    }
    if (ev.event === 'run_completed') runCompleted = true;
    if (ev.event === 'run_failed') runFailed = true;
    lastEvent = ev;
  }

  const stepList = PIPELINE_STEPS.map((item, index) => {
    const rec = steps.get(item.step) || {
      step: item.step, owner: item.owner, status: 'pending', attempts: 0,
      started_at: null, completed_at: null, last_event: null, outputs: [], notes: []
    };
    return { index, ...rec };
  });
  const known = new Set(PIPELINE_STEPS.map((item) => item.step));
  for (const [name, rec] of steps) {
    if (!known.has(name)) stepList.push({ index: stepList.length, ...rec });
  }

  const runConfig = readJson(join(runDir, '00_input', 'run_config.json'), null);
  const firstTs = init?.timestamp || events[0]?.timestamp || new Date().toISOString();
  const rebuilt = {
    run_id: init?.run_id || basename(resolve(runDir)),
    created: firstTs,
    run_dir: init?.run_dir || resolve(runDir),
    status: runCompleted ? 'completed' : (runFailed ? 'failed' : 'initialized'),
    steps: stepList,
    execution_policy: {
      run_mode: runConfig?.run_mode || 'full',
      audit: { skipped_stages: skippedStages }
    },
    delivery_contract: {
      strict_pipeline_required: true,
      evidence_closure_required: true,
      required_runtime_artifacts: DEFAULT_REQUIRED_ARTIFACTS
    },
    pipeline: {
      version: 'v6.5',
      current_step: currentStep,
      current_owner: currentOwner,
      diag_iters_total: diagIters,
      repair_spawn_count: repairSpawns,
      artifact_finalize_runs: finalizeRuns,
      integrity: {
        repair_cap_reached: capReached,
        ...(lastArtifactCheck ? { last_artifact_check: lastArtifactCheck } : {})
      }
    },
    updated_at: lastEvent?.timestamp || new Date().toISOString(),
    rebuilt_from_events: true,
    rebuilt_at: new Date().toISOString(),
    rebuilt_note: 'run_manifest.json was unreadable; this manifest was reconstructed from .pipeline_events.jsonl (append-only source of truth). Unprovable fields use pipeline defaults.'
  };

  let backupPath = null;
  if (typeof corruptText === 'string') {
    backupPath = `${manifestPath}.corrupt-${timestampSuffix()}`;
    try { fs.writeFileSync(backupPath, corruptText); } catch (_) { backupPath = null; }
  }
  return { ok: true, manifest: rebuilt, backupPath, events: events.length, corruptLines };
}

function ensureArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null) return [];
  return [value];
}

function parseJsonFlag(name, fallback = {}) {
  const raw = flag(name);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error(`Invalid JSON for ${name}: ${error.message}`);
    process.exit(1);
  }
}

function parseFiles(value) {
  if (!value) return [];
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function upsertNote(stepRecord, note) {
  stepRecord.notes = ensureArray(stepRecord.notes);
  if (!stepRecord.notes.includes(note)) {
    stepRecord.notes.push(note);
  }
}

function getStepRecord(manifest, step) {
  const steps = ensureArray(manifest.steps);
  return steps.find((item) => item.step === step) || null;
}

function stepStatus(manifest, step) {
  const record = getStepRecord(manifest, step);
  return record?.status || 'missing';
}

function isPreReportAudit(step, agent, extraData) {
  if (step !== 'audit' || agent !== 'report-reviewer') return false;
  return extraData.audit_mode === 'pre_report' || extraData.PRE_REPORT_AUDIT === true;
}

function prerequisitesFor(step, agent, extraData) {
  if (isPreReportAudit(step, agent, extraData)) {
    return ['diagnostician'];
  }
  return STEP_PREREQUISITES[step] || [];
}

function enforceStepPrerequisites(manifest, step, eventName, agent, extraData) {
  if (!step || !['step_start', 'agent_start'].includes(eventName)) return;
  const prerequisites = prerequisitesFor(step, agent, extraData);
  const incomplete = prerequisites.filter((requiredStep) => stepStatus(manifest, requiredStep) !== 'completed');
  if (incomplete.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'PIPELINE_ORDER_VIOLATION',
          step,
          agent,
          missing_prerequisites: incomplete
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

function judgeGateIssues() {
  // Best-effort bypass: if judge_repair_summary.json proves 3 repair rounds
  // exhausted without reaching 90, the pipeline proceeds with [BEST_EFFORT]
  // (see SKILL.md §Best-of-Judge Protocol). Gate passes in that case.
  const summaryPath = join(runDir, '05_review', 'judge_repair_summary.json');
  const summary = readJson(summaryPath, null);
  if (summary && summary.converged === false && Number(summary.rounds_attempted) >= 3) {
    return [];
  }

  const judgePath = join(runDir, '05_review', 'judge_feedback.json');
  if (!fs.existsSync(judgePath)) {
    return ['05_review/judge_feedback.json is missing'];
  }

  const judge = readJson(judgePath, null);
  if (!judge || typeof judge !== 'object') {
    return ['05_review/judge_feedback.json is unreadable'];
  }

  const score = Number(judge.overall_score ?? judge.score ?? judge.judge_score ?? 0);
  const verdict = typeof judge.verdict === 'object' ? judge.verdict?.verdict : judge.verdict;
  const blockingIssues = Array.isArray(judge.blocking_issues) ? judge.blocking_issues.length : 0;
  const reasoningBlocking = Array.isArray(judge.reasoning_chain_audit?.blocking_issues)
    ? judge.reasoning_chain_audit.blocking_issues.length
    : 0;
  const noOverClaimingValue = judge.criteria_scores?.no_over_claiming?.blocking_issues;
  const noOverClaimingBlocking = Array.isArray(noOverClaimingValue)
    ? noOverClaimingValue.length
    : Number(noOverClaimingValue ?? 0);
  const issues = [];

  if (!Number.isFinite(score) || score < 90) issues.push(`judge overall_score ${Number.isFinite(score) ? score : 'missing'} < 90`);
  if (verdict !== 'pass') issues.push(`judge verdict is ${verdict || 'missing'}, not pass`);
  if (blockingIssues > 0 || reasoningBlocking > 0 || noOverClaimingBlocking > 0) {
    issues.push(`judge blocking issues present (${blockingIssues + reasoningBlocking + noOverClaimingBlocking})`);
  }

  return issues;
}

function enforceReporterJudgeGate(step, eventName, agent) {
  if (!['step_start', 'agent_start'].includes(eventName)) return;
  if (step !== 'reporter' && agent !== 'reporter') return;

  const issues = judgeGateIssues();
  if (issues.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'JUDGE_GATE_NOT_PASSED',
          step,
          agent,
          issues
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

function enforceCompletionJudgeGate(step, eventName, status) {
  const claimsFinalCompletion =
    eventName === 'run_completed' ||
    eventName === 'artifact_finalize_complete' ||
    (eventName === 'step_complete' && step === 'present') ||
    (eventName === 'artifact_check_complete' && (status === 'PASS' || extraData.integrity_check === 'PASS'));

  if (!claimsFinalCompletion) return;

  const issues = judgeGateIssues();
  if (issues.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'JUDGE_GATE_NOT_PASSED',
          event: eventName,
          step,
          issues
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

if (!runDir) {
  console.error('Usage: node append-pipeline-event.mjs <run_dir> --event <event> [--agent <agent>] [--step <pipeline_step>] [--files a,b] [--data <json>] [--errors <text>] [--status <status>]');
  process.exit(1);
}

const eventName = flag('--event');
if (!eventName || !VALID_EVENTS.has(eventName)) {
  console.error(`Missing or invalid --event. Supported events: ${Array.from(VALID_EVENTS).join(', ')}`);
  process.exit(1);
}

const manifestPath = join(runDir, 'run_manifest.json');
const manifestRead = readText(manifestPath);
let manifest = null;
if (manifestRead.ok) {
  try {
    const parsed = JSON.parse(manifestRead.text);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) manifest = parsed;
  } catch (_) { /* corrupt JSON → rebuild below */ }
}
if (!manifest) {
  // 损坏的 manifest 不再硬退出：事件日志是 append-only 事实源，先重建。
  const rebuilt = rebuildManifestFromEvents({
    manifestPath,
    corruptText: manifestRead.ok ? manifestRead.text : null,
  });
  if (!rebuilt.ok) {
    console.error(
      `Missing or unreadable run_manifest.json at ${manifestPath}\n`
      + `  - manifest: ${manifestRead.ok ? 'present but not a JSON object (corrupt)' : `unreadable (${manifestRead.error.message})`}\n`
      + `  - rebuild from .pipeline_events.jsonl failed: ${rebuilt.reason}`
    );
    process.exit(1);
  }
  console.error(
    `WARNING: run_manifest.json was ${manifestRead.ok ? 'corrupt' : 'unreadable'} — rebuilt from .pipeline_events.jsonl `
    + `(${rebuilt.events} event(s)${rebuilt.corruptLines ? `, ${rebuilt.corruptLines} corrupt line(s) skipped` : ''})`
    + `${rebuilt.backupPath ? `; corrupt copy: ${rebuilt.backupPath}` : ''}`
  );
  manifest = rebuilt.manifest;
}
manifest.steps = ensureArray(manifest.steps);
manifest.pipeline = manifest.pipeline || {
  version: 'v6.5',
  current_step: null,
  current_owner: null,
  diag_iters_total: 0,
  repair_spawn_count: 0,
  artifact_finalize_runs: 0,
  integrity: {}
};
manifest.pipeline.integrity = manifest.pipeline.integrity || {};

const logPath = join(runDir, '.pipeline_events.jsonl');
const agent = flag('--agent') || 'main-agent';
let explicitStep = flag('--step');
const inferredStep = explicitStep || AGENT_TO_STEP[agent] || null;
// 防御：显式 --step 若不在 manifest 步骤清单且该 agent 有标准映射，则纠正为映射步骤
// （历史事故：派发提示词写 --step report，而 manifest 步骤名为 reporter）。
if (explicitStep && AGENT_TO_STEP[agent]) {
  const manifestStepNames = new Set((manifest?.steps || []).map(s => s.step));
  if (!manifestStepNames.has(explicitStep) && manifestStepNames.has(AGENT_TO_STEP[agent])) {
    console.error(JSON.stringify({
      ok: false,
      error: 'STEP_NAME_CORRECTED',
      from: explicitStep,
      to: AGENT_TO_STEP[agent],
    }, null, 2));
    explicitStep = AGENT_TO_STEP[agent];
  }
}
const filesWritten = parseFiles(flag('--files'));
const extraData = parseJsonFlag('--data', {});
const errors = flag('--errors');
const status = flag('--status');
const allowMissingFiles = args.includes('--allow-missing-files');
const event = {
  event: eventName,
  agent,
  timestamp: new Date().toISOString(),
  ...extraData
};

if (inferredStep) {
  event.step = inferredStep;
}
if (filesWritten.length > 0) {
  event.files_written = filesWritten;
}
if (errors !== undefined) {
  event.errors = errors;
}
if (status) {
  event.status = status;
}

enforceStepPrerequisites(manifest, inferredStep, eventName, agent, extraData);
enforceReporterJudgeGate(inferredStep, eventName, agent);
enforceCompletionJudgeGate(inferredStep, eventName, status);

if (filesWritten.length > 0 && ['agent_complete', 'step_complete', 'artifact_finalize_complete'].includes(eventName) && !allowMissingFiles) {
  const missingFiles = filesWritten.filter((filePath) => !fs.existsSync(join(runDir, filePath)));
  if (missingFiles.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'PIPELINE_OUTPUT_MISSING',
          step: inferredStep,
          missing_files: missingFiles
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

const shouldUpdateStepRecord = !isPreReportAudit(inferredStep, agent, extraData);
const stepRecord = inferredStep && shouldUpdateStepRecord ? getStepRecord(manifest, inferredStep) : null;

if (stepRecord) {
  if (eventName === 'dependency_wait') {
    upsertNote(stepRecord, `dependency_wait:${extraData.waiting_for || 'unknown'}`);
  }

  if (eventName === 'dependency_ready') {
    upsertNote(stepRecord, `dependency_ready:${extraData.dependency || extraData.waiting_for || 'unknown'}`);
  }

  if (['step_start', 'agent_start'].includes(eventName)) {
    // 回退守卫：已完成（或带错误完成）的步骤不允许被迟到的 start 事件翻回
    // in_progress——那会让前置条件门与真实进度脱钩（2026-10-13 fieldtest 实测）。
    if (['completed', 'completed_with_errors'].includes(stepRecord.status || '')) {
      console.error(JSON.stringify({
        ok: false,
        error: 'STEP_ALREADY_COMPLETED',
        step: inferredStep,
        status: stepRecord.status,
        hint: 'append step_complete instead, or record a new attempt via repair_spawn'
      }, null, 2));
      process.exit(1);
    }
    stepRecord.status = 'in_progress';
    stepRecord.started_at = stepRecord.started_at || event.timestamp;
    stepRecord.attempts = (stepRecord.attempts || 0) + 1;
    stepRecord.last_event = eventName;
    manifest.pipeline.current_step = inferredStep;
    manifest.pipeline.current_owner = agent;
  }

  if (['step_complete', 'agent_complete'].includes(eventName)) {
    stepRecord.status = errors ? 'completed_with_errors' : 'completed';
    stepRecord.completed_at = event.timestamp;
    stepRecord.last_event = eventName;
    stepRecord.outputs = Array.from(new Set([...(stepRecord.outputs || []), ...filesWritten]));
    if (errors) {
      upsertNote(stepRecord, `errors:${errors}`);
    }
  }
}

if (eventName === 'repair_spawn') {
  manifest.pipeline.diag_iters_total = (manifest.pipeline.diag_iters_total || 0) + 1;
  manifest.pipeline.repair_spawn_count = (manifest.pipeline.repair_spawn_count || 0) + 1;
}

if (eventName === 'repair_cap_reached') {
  manifest.pipeline.integrity.repair_cap_reached = true;
}

if (eventName === 'artifact_finalize_start') {
  manifest.pipeline.artifact_finalize_runs = (manifest.pipeline.artifact_finalize_runs || 0) + 1;
}

if (eventName === 'artifact_finalize_complete') {
  manifest.pipeline.current_step = 'present';
  manifest.pipeline.current_owner = 'main-agent';
}

if (eventName === 'artifact_check_complete') {
  manifest.pipeline.integrity.last_artifact_check = status || extraData.integrity_check || 'unknown';
  if (extraData.skipped_stage && extraData.reason) {
    const audit = manifest.execution_policy?.audit;
    if (!manifest.execution_policy || !audit) {
      console.error('SKIPPED_STAGE_POLICY_MISSING: run_manifest.execution_policy.audit is required');
      process.exit(1);
    }
    const record = { stage: extraData.skipped_stage, reason: extraData.reason, event: eventName };
    const skipped = audit.skipped_stages = Array.isArray(audit.skipped_stages) ? audit.skipped_stages : [];
    const index = skipped.findIndex(item => item.stage === record.stage);
    if (index >= 0) skipped[index] = record;
    else skipped.push(record);
  }
}

if (eventName === 'run_completed') {
  manifest.status = 'completed';
  const presentStep = getStepRecord(manifest, 'present');
  if (presentStep) {
    presentStep.status = 'completed';
    presentStep.completed_at = event.timestamp;
    presentStep.last_event = eventName;
  }
}

if (eventName === 'run_failed') {
  manifest.status = 'failed';
}

if (eventName.startsWith('clarification_')) {
  const clarificationStep = getStepRecord(manifest, 'clarification_gate');
  if (clarificationStep) {
    clarificationStep.status = 'completed';
    clarificationStep.completed_at = event.timestamp;
    clarificationStep.last_event = eventName;
    clarificationStep.attempts = Math.max(clarificationStep.attempts || 0, 1);
  }
}

manifest.updated_at = event.timestamp;
fs.appendFileSync(logPath, `${JSON.stringify(event)}\n`);
writeJson(manifestPath, manifest);

console.log(JSON.stringify({ ok: true, log_path: logPath, manifest_path: manifestPath, event }, null, 2));
