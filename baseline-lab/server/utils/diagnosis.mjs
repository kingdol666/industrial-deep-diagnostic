// Diagnosis service — the backend that actually performs a diagnosis on a
// user's uploaded data and streams it to the frontend as it happens.
//
// WHY THIS EXISTS SEPARATELY FROM runner.mjs
// ------------------------------------------
// runner.mjs is the BENCHMARK harness: it sweeps algorithms x fixed cases and
// SCORES them against hidden ground truth. A diagnosis of user data is a
// different job with a different contract:
//
//   * no ground truth, so there is nothing to score;
//   * one dataset, N algorithms, and the user must WATCH it happen — a single
//     LLM call takes 40-80 s, and a silent gap is indistinguishable from a
//     frozen script;
//   * the frontend needs structured, renderable findings, not a JSON blob.
//
// So a diagnosis is a long-lived job that emits an ordered event stream
// (stage / algorithm_start / llm_call_start / llm_call_done / algorithm_done /
// complete) and accumulates a structured report. The frontend renders the
// events live and the report at the end.

import { randomUUID } from 'node:crypto';
import { getUpload } from './uploads.mjs';
import { listAlgorithms, getAlgorithm } from './registry.mjs';
import { runOne } from './runner.mjs';
import { uploadCaseDef, writeJson, RESULTS_DIR, ensureDir } from './paths.mjs';
import path from 'node:path';

/**
 * Default algorithm set for a diagnosis: every registered algorithm that can run
 * on an uploaded dataset. Derived from each module's declared domains rather
 * than a hand-maintained list, so it cannot drift when an algorithm gains or
 * loses upload support.
 */
export function defaultDiagnosable() {
  return listAlgorithms()
    .filter((a) => !a.domains || a.domains.includes('custom'))
    .map((a) => a.id);
}

/** In-memory diagnosis jobs (the persisted report lives on disk). */
const jobs = new Map();

export function getDiagnosisJob(jobId) {
  return jobs.get(jobId) || null;
}

export function pruneDiagnosisJobs(maxAgeMs = 6 * 60 * 60 * 1000) {
  const cutoff = Date.now() - maxAgeMs;
  for (const [id, job] of jobs) {
    if (job.state !== 'running' && new Date(job.finished_at || job.started_at).getTime() < cutoff) jobs.delete(id);
  }
}

function diagnosisDir(jobId) {
  return path.join(RESULTS_DIR, 'diagnoses', jobId);
}

/**
 * Start a diagnosis of an uploaded dataset.
 * Returns immediately with a job handle; the work runs in the background and
 * publishes events that `subscribe()` consumers receive.
 */
export function startDiagnosis({ uploadId, algorithms, options = {}, config = {} }) {
  const meta = getUpload(uploadId);
  if (!meta) throw new Error(`unknown upload: ${uploadId}`);
  const caseId = meta.case_id;

  const requested = (algorithms && algorithms.length ? algorithms : defaultDiagnosable()).filter(Boolean);
  if (!requested.length) throw new Error('select at least one algorithm');

  // Reject anything that cannot run on this data, with the reason — rather than
  // silently dropping it or producing a meaningless "result".
  const runnable = [];
  const refused = [];
  for (const id of requested) {
    const algo = getAlgorithm(id); // throws on unknown
    if (algo.meta.domains && !algo.meta.domains.includes('custom')) {
      refused.push({
        algorithm: id,
        label: algo.meta.label,
        reason: `declares domains [${algo.meta.domains.join(', ')}] and cannot be applied to an uploaded dataset`,
      });
    } else {
      runnable.push(id);
    }
  }
  if (!runnable.length) {
    throw new Error(`none of the selected algorithms can run on uploaded data: ${refused.map((r) => `${r.algorithm} (${r.reason})`).join('; ')}`);
  }

  const jobId = randomUUID();
  const job = {
    job_id: jobId,
    state: 'running',
    upload_id: uploadId,
    case_id: caseId,
    dataset_label: meta.label,
    algorithms: runnable,
    refused,
    started_at: new Date().toISOString(),
    finished_at: null,
    events: [],          // ordered event log (also what SSE replays on connect)
    listeners: new Set(), // active SSE subscribers
    findings: [],
    report: null,
    error: null,
    seq: 0,
  };
  jobs.set(jobId, job);

  const emit = (type, data = {}) => {
    const event = { seq: ++job.seq, t: Date.now(), type, ...data };
    job.events.push(event);
    for (const fn of job.listeners) {
      try { fn(event); } catch { /* a dead subscriber must not kill the diagnosis */ }
    }
    return event;
  };

  (async () => {
    try {
      const ctxMeta = uploadCaseDef(uploadId);
      emit('stage', {
        stage: 'ingest',
        message: `Dataset "${meta.label}" — ${meta.rows} rows × ${meta.numeric_columns} columns`,
        columns: meta.columns,
        calibration_fraction: meta.calibration_fraction,
        calibration_rows: Math.round(meta.rows * (meta.calibration_fraction ?? 0.3)),
      });
      if (refused.length) {
        emit('stage', {
          stage: 'refused',
          message: `${refused.length} algorithm(s) cannot run on this data and were not executed`,
          refused,
        });
      }
      emit('stage', {
        stage: 'running',
        message: `Executing ${runnable.length} algorithm(s) against your data — every LLM call below is a real request`,
        algorithms: runnable,
      });

      for (const algorithmId of runnable) {
        const algo = getAlgorithm(algorithmId);
        emit('algorithm_start', {
          algorithm: algorithmId,
          label: algo.meta.label,
          family: algo.meta.family,
          deterministic: algo.meta.deterministic,
          requires_provider: Boolean(algo.meta.requiresProvider),
        });

        const result = await runOne({
          algorithmId,
          caseId,
          config,
          options,
          onEvent: (type, data) => {
            // Forward the algorithm's own lifecycle events, tagged with the
            // algorithm so the UI can attribute each model call.
            emit(type, { algorithm: algorithmId, ...data });
          },
        });

        const finding = toFinding(algorithmId, algo.meta, result);
        job.findings.push(finding);
        emit('algorithm_done', {
          algorithm: algorithmId,
          status: result.status,
          verdict: finding.verdict,
          duration_ms: result.runtime_ms ?? null,
          summary: finding.summary,
          invocations: finding.invocations.map((i) => ({
            tag: i.tag, provider: i.provider, model: i.model, ok: i.ok, seconds: i.seconds, archived: i.archived,
          })),
        });
      }

      // `finished_at` MUST be set before building the report: buildReport derives
      // duration_ms from it, and setting it afterwards silently reported 0.0s.
      job.finished_at = new Date().toISOString();
      job.report = buildReport(job, meta, ctxMeta);
      job.state = 'complete';

      // Persist the report so it is auditable after the process restarts.
      const dir = ensureDir(diagnosisDir(jobId));
      writeJson(path.join(dir, 'report.json'), job.report);
      writeJson(path.join(dir, 'events.json'), job.events);

      emit('complete', { report: job.report });
    } catch (err) {
      job.state = 'error';
      job.error = String(err && err.stack ? err.stack : err);
      job.finished_at = new Date().toISOString();
      emit('error', { message: String(err && err.message ? err.message : err) });
    } finally {
      // Release SSE subscribers so the client's stream ends.
      for (const fn of job.listeners) {
        try { fn({ seq: ++job.seq, t: Date.now(), type: 'end' }); } catch { /* ignore */ }
      }
      job.listeners.clear();
    }
  })();

  return job;
}

/** Subscribe to a job's events. Returns an unsubscribe function. */
export function subscribe(job, fn) {
  job.listeners.add(fn);
  return () => job.listeners.delete(fn);
}

/**
 * Shape one algorithm's raw result into a renderable finding.
 * The frontend should not have to know that pca reports detection.T2/SPE while
 * spc reports detection.detection_rate — that normalisation belongs here.
 */
function toFinding(algorithmId, meta, result) {
  const o = result.output || {};
  const d = o.detection || {};
  const detectionRate = typeof d.detection_rate === 'number'
    ? d.detection_rate
    : (d.T2 || d.SPE
      ? Math.max(d.T2?.detection_rate ?? 0, d.SPE?.detection_rate ?? 0)
      : null);

  return {
    algorithm: algorithmId,
    label: meta.label,
    short: meta.short,
    family: meta.family,
    deterministic: meta.deterministic,
    status: result.status,
    verdict: o.verdict ?? null,
    hypotheses: Array.isArray(o.top3) ? o.top3.filter(Boolean) : [],
    reasoning: o.reasoning || '',
    confidence: o.confidence ?? null,
    schema_conformance: o.schema_conformance ?? null,
    diagnosis_type: o.diagnosis_type ?? (o.top3?.length ? 'DETERMINED' : null),
    detection_rate: detectionRate,
    detection_detail: detectionRate === null ? null : {
      T2: d.T2?.detection_rate ?? null,
      SPE: d.SPE?.detection_rate ?? null,
      threshold: d.threshold ?? d.T2?.threshold ?? null,
      alarms: d.alarms ?? null,
      window_rows: d.window_rows ?? null,
      pre_window_alarm_rate: d.pre_window_alarm_rate ?? null,
      components_retained: d.components_retained ?? null,
    },
    variables: Array.isArray(o.variables_ranked)
      ? o.variables_ranked.slice(0, 8).map((v) => ({ column: v.col, contribution: Number(v.contribution) }))
      : [],
    tool_calls: Array.isArray(o.tool_calls)
      ? o.tool_calls.map((t) => ({ tool: t.tool, args: t.args, observation: t.observation, recognised: t.recognised !== false }))
      : [],
    // Evidence integrity: whether an LLM answer is actually grounded in real
    // tool output, or was produced after the model fabricated its own.
    evidence_integrity: o.evidence_integrity ?? null,
    integrity_note: o.integrity_note ?? null,
    protocol_violations: Array.isArray(o.protocol_violations) ? o.protocol_violations : [],
    reference: o.detection?.reference ?? null,
    diagnosis_step: o.diagnosis_step || null,
    invocations: Array.isArray(o.invocations) ? o.invocations : [],
    runtime_ms: result.runtime_ms ?? o.runtime_ms ?? null,
    not_applicable_reason: result.status === 'not_applicable' ? (o.reasoning || '') : null,
    summary: summarizeFinding(algorithmId, result, o, detectionRate),
  };
}

function summarizeFinding(algorithmId, result, o, detectionRate) {
  if (result.status === 'not_applicable') return 'not applicable to this dataset';
  if (result.status === 'skipped_no_provider') return 'skipped — no LLM provider configured (no answer invented)';
  if (result.status === 'error') return `failed: ${o.reasoning || 'unknown error'}`;
  const parts = [];
  if (detectionRate !== null) parts.push(`alarm rate ${(detectionRate * 100).toFixed(1)}%`);
  if (o.top3?.length) parts.push(`top: ${String(o.top3[0]).slice(0, 90)}`);
  else if (o.verdict === 'normal') parts.push('verdict: normal');
  else if (o.verdict === 'fault') parts.push('verdict: fault (no ranked cause given)');
  return parts.join(' · ') || 'executed';
}

/** Assemble the rendered diagnosis report. */
function buildReport(job, uploadMeta, caseDef) {
  const detected = job.findings.filter((f) => f.verdict === 'fault');
  const normals = job.findings.filter((f) => f.verdict === 'normal');
  const executed = job.findings.filter((f) => f.status === 'executed');
  const llmFindings = job.findings.filter((f) => f.family === 'llm' || f.family === 'official');
  const contaminated = job.findings.filter((f) => f.evidence_integrity === 'contaminated');
  const unverified = job.findings.filter((f) => f.evidence_integrity === 'unverified');

  // Variables that several detectors independently flag are the most credible
  // signal available without ground truth.
  const varTally = new Map();
  for (const f of job.findings) {
    for (const v of f.variables.slice(0, 5)) varTally.set(v.column, (varTally.get(v.column) || 0) + 1);
  }
  const consensusVariables = [...varTally.entries()]
    .map(([column, algorithms]) => ({ column, algorithms }))
    .sort((a, b) => b.algorithms - a.algorithms);

  return {
    job_id: job.job_id,
    dataset: {
      upload_id: job.upload_id,
      case_id: job.case_id,
      label: job.dataset_label,
      original_name: uploadMeta.original_name,
      rows: uploadMeta.rows,
      numeric_columns: uploadMeta.numeric_columns,
      columns: uploadMeta.columns,
      time_column: uploadMeta.time_col,
      excluded_index_column: uploadMeta.excluded_index_column,
      excluded_index_reason: uploadMeta.excluded_index_reason,
      process_description: uploadMeta.process_description || '',
    },
    method: {
      algorithms_run: job.algorithms,
      algorithms_refused: job.refused,
      calibration_fraction: uploadMeta.calibration_fraction,
      calibration_rows: Math.round(uploadMeta.rows * (uploadMeta.calibration_fraction ?? 0.3)),
      monitored_rows: uploadMeta.rows - Math.round(uploadMeta.rows * (uploadMeta.calibration_fraction ?? 0.3)),
      truthfulness: 'No ground truth exists for uploaded data, so nothing here is scored. '
        + 'Detection statistics and root-cause hypotheses are genuine executions; an algorithm that '
        + 'found nothing is reported as such rather than given a fabricated cause.',
    },
    headline: {
      executed: executed.length,
      fault_verdicts: detected.length,
      normal_verdicts: normals.length,
      llm_mechanisms: llmFindings.filter((f) => f.hypotheses.length).length,
      consensus_variables: consensusVariables.filter((v) => v.algorithms > 1).length,
      contaminated_answers: contaminated.length,
      unverified_answers: unverified.length,
    },
    // Surfaced at the top of the report so a contaminated answer can never be
    // read as a grounded diagnosis.
    evidence_warnings: [...contaminated, ...unverified].map((f) => ({
      algorithm: f.algorithm,
      integrity: f.evidence_integrity,
      note: f.integrity_note,
      violations: f.protocol_violations,
    })),
    consensus_variables: consensusVariables,
    // The LLM findings are the mechanism layer; detectors give variables only.
    mechanism_hypotheses: llmFindings
      .filter((f) => f.hypotheses.length)
      .map((f) => ({
        algorithm: f.algorithm,
        label: f.label,
        model: f.invocations[0]?.model || null,
        provider: f.invocations[0]?.provider || null,
        seconds: f.invocations.reduce((s, i) => s + (i.seconds || 0), 0),
        calls: f.invocations.length,
        hypotheses: f.hypotheses,
        reasoning: f.reasoning,
        confidence: f.confidence,
      })),
    findings: job.findings,
    generated_at: new Date().toISOString(),
    started_at: job.started_at,
    finished_at: job.finished_at,
    duration_ms: job.finished_at ? new Date(job.finished_at).getTime() - new Date(job.started_at).getTime() : null,
    elapsed_ms_at_build: Date.now() - new Date(job.started_at).getTime(),
  };
}

export { defaultDiagnosable as DIAGNOSABLE_ALGORITHMS };

/** Which registered algorithms can run on uploaded data, and why the rest cannot. */
export function diagnosableAlgorithms() {
  const all = listAlgorithms();
  const runnable = [];
  const refused = [];
  for (const a of all) {
    const ok = !a.domains || a.domains.includes('custom');
    (ok ? runnable : refused).push({ ...a, why_not: ok ? null : `declares domains [${a.domains.join(', ')}]` });
  }
  return { runnable, refused };
}
