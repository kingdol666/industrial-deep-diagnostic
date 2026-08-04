// OMP Service — bridge to the native OMP harness outputs.
//
// OMP (oh-my-claudecode) runs the diagnostic pipeline via agents and writes
// artifacts into workspace/diagnostic-runs/<run_dir>/. This service reads
// those NATIVE outputs (pipeline event log, optimizer verdict, enhancement
// status, reports, HTML) and exposes them over REST — a read-only RPC bridge
// into the OMP engine's filesystem contract. It never writes into run dirs.

import { readdirSync, readFileSync, existsSync, statSync } from 'fs';
import { join, basename, extname } from 'path';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';

const RUNS_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');

// ── helpers ──────────────────────────────────────────────────────────

function tryReadJson(filePath) {
  try {
    if (!existsSync(filePath)) return null;
    return JSON.parse(readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function tryReadText(filePath, maxBytes = 200_000) {
  try {
    if (!existsSync(filePath)) return null;
    const buf = readFileSync(filePath);
    return buf.subarray(0, maxBytes).toString('utf8');
  } catch {
    return null;
  }
}

function tryReadLines(filePath) {
  const text = tryReadText(filePath, 500_000);
  if (!text) return [];
  return text.split('\n').filter((l) => l.trim().length > 0);
}

/** Parse .pipeline_events.jsonl into ordered events with step grouping. */
export function parsePipelineEvents(runDir) {
  const lines = tryReadLines(join(runDir, '.pipeline_events.jsonl'));
  const events = [];
  for (const line of lines) {
    try {
      const ev = JSON.parse(line);
      events.push({
        type: ev.event || ev.type || 'unknown',
        agent: ev.agent || null,
        step: ev.step || null,
        time: ev.timestamp || ev.time || null,
        files: ev.files || null,
        data: ev.data || null,
      });
    } catch {
      // skip malformed lines
    }
  }
  return events;
}

/** Derive baseline pipeline status from events + optimizer + report presence. */
function deriveBaselineStatus(runDir) {
  const events = parsePipelineEvents(runDir);
  const agents = [...new Set(events.map((e) => e.agent).filter(Boolean))];
  const completedSteps = new Set(
    events.filter((e) => e.type === 'agent_complete' || e.type === 'step_complete').map((e) => e.step || e.agent)
  );
  const optimizer = tryReadText(join(runDir, 'optimizer.md'), 60_000) || '';
  let verdict = null;
  if (/ENDORSED/.test(optimizer)) verdict = 'ENDORSED';
  else if (/CONDITIONAL/.test(optimizer)) verdict = 'CONDITIONAL';
  else if (/REJECTED/.test(optimizer)) verdict = 'REJECTED';

  const hasReport = existsSync(join(runDir, 'report.md'));
  const hasHtml = existsSync(join(runDir, 'diagnostic-report.html'));
  const hasDiagnosis = existsSync(join(runDir, '04_diagnostics', 'diagnosis.json'));

  let status = 'unknown';
  if (verdict === 'ENDORSED' && hasHtml && hasReport) status = 'completed';
  else if (hasReport && hasDiagnosis) status = 'report_ready';
  else if (hasDiagnosis) status = 'diagnosed';
  else if (events.length > 0) status = 'in_progress';
  else status = 'initialized';

  return { status, verdict, agents, completedSteps: [...completedSteps], hasReport, hasHtml, hasDiagnosis };
}

/** Derive enhancement pipeline status from enhancement/ artifacts. */
function deriveEnhancementStatus(runDir) {
  const enhDir = join(runDir, 'enhancement');
  if (!existsSync(enhDir)) return null;
  const statusFile = tryReadJson(join(enhDir, 'enhancement_status.json'));
  const manifest = tryReadJson(join(enhDir, 'enhancement_manifest.json'));
  const artifacts = {};
  for (const f of ['analysis_coverage.json', 'derived_features.json', 'deep_data_analysis.json',
                   'association_graph.json', 'physics_bridge.json', 'enhanced_knowledge.json',
                   'enhanced_analysis.md', 'enhanced-analysis.html', 'enhancement_html_review.json']) {
    artifacts[f] = existsSync(join(enhDir, f));
  }
  return {
    status: statusFile?.status || (manifest ? 'initialized' : null),
    warnings: statusFile?.warnings || [],
    run_id: statusFile?.run_id || manifest?.run_id || null,
    data_sha256: manifest?.data_source?.sha256 || null,
    rows: manifest?.data_source?.rows ?? null,
    cols: manifest?.data_source?.cols ?? null,
    artifacts,
  };
}

/** Build artifact inventory for a run dir (key files with sizes). */
function artifactInventory(runDir) {
  const entries = [];
  const KEYS = [
    ['01_ontology/ontology.json', 'ontology'],
    ['02_processed/cleaned_data.csv', 'cleaned_data'],
    ['02_processed/data_analysis_conclusion.json', 'analysis_conclusion'],
    ['02_processed/validate_report.json', 'validate_report'],
    ['02_processed/physics_check.json', 'physics_check'],
    ['03_figures/plot_manifest.json', 'plot_manifest'],
    ['03_figures/visual_analysis.json', 'visual_analysis'],
    ['04_diagnostics/diagnosis.json', 'diagnosis'],
    ['04_diagnostics/evidence.json', 'evidence'],
    ['04_diagnostics/confidence.json', 'confidence'],
    ['04_diagnostics/reasoning_chain.json', 'reasoning_chain'],
    ['05_review/judge_feedback.json', 'judge_feedback'],
    ['05_review/html_review.json', 'html_review'],
    ['05_review/optimizer_preflight.md', 'optimizer_preflight'],
    ['report.md', 'report'],
    ['run_summary.json', 'run_summary'],
    ['optimizer.md', 'optimizer'],
    ['diagnostic-report.html', 'html'],
    ['evidence_closure_report.json', 'evidence_closure'],
  ];
  for (const [rel, key] of KEYS) {
    const p = join(runDir, rel);
    if (existsSync(p)) {
      entries.push({ key, path: rel, size: statSync(p).size });
    }
  }
  return entries;
}

// ── public API ───────────────────────────────────────────────────────

export function ompHealth() {
  const ok = existsSync(RUNS_DIR);
  let runCount = 0;
  if (ok) runCount = readdirSync(RUNS_DIR, { withFileTypes: true }).filter((d) => d.isDirectory()).length;
  return {
    available: ok,
    runs_dir: RUNS_DIR,
    run_count: runCount,
    engine: 'omp',
  };
}

export function listOmpRuns() {
  if (!existsSync(RUNS_DIR)) return [];
  const runs = readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && existsSync(join(RUNS_DIR, d.name, 'run_manifest.json')))
    .map((d) => {
      const dir = join(RUNS_DIR, d.name);
      const manifest = tryReadJson(join(dir, 'run_manifest.json')) || {};
      const baseline = deriveBaselineStatus(dir);
      const enhancement = deriveEnhancementStatus(dir);
      const created = statSync(dir).birthtime?.toISOString() || null;
      return {
        name: d.name,
        display_name: manifest.name || manifest.scene_name || d.name,
        created,
        baseline_status: baseline.status,
        verdict: baseline.verdict,
        agents: baseline.agents,
        completed_steps: baseline.completedSteps,
        has_report: baseline.hasReport,
        has_html: baseline.hasHtml,
        has_diagnosis: baseline.hasDiagnosis,
        enhancement_status: enhancement?.status || null,
        enhancement_ready: enhancement?.artifacts?.['enhanced-analysis.html'] || false,
        artifact_count: artifactInventory(dir).length,
      };
    })
    .sort((a, b) => (b.created || '').localeCompare(a.created || ''));
  return runs;
}

export function getOmpRun(name) {
  const runDir = join(RUNS_DIR, name);
  if (!existsSync(runDir) || !existsSync(join(runDir, 'run_manifest.json'))) return null;
  const manifest = tryReadJson(join(runDir, 'run_manifest.json')) || {};
  const baseline = deriveBaselineStatus(runDir);
  const enhancement = deriveEnhancementStatus(runDir);
  return {
    name,
    display_name: manifest.name || manifest.scene_name || name,
    manifest,
    baseline,
    enhancement,
    artifacts: artifactInventory(runDir),
    events: parsePipelineEvents(runDir),
  };
}

export function getOmpArtifact(name, kind) {
  const runDir = join(RUNS_DIR, name);
  if (!existsSync(runDir)) return null;
  const MAP = {
    report: 'report.md',
    optimizer: 'optimizer.md',
    html: 'diagnostic-report.html',
    run_summary: 'run_summary.json',
    diagnosis: '04_diagnostics/diagnosis.json',
    evidence: '04_diagnostics/evidence.json',
    confidence: '04_diagnostics/confidence.json',
    reasoning_chain: '04_diagnostics/reasoning_chain.json',
    judge_feedback: '05_review/judge_feedback.json',
    html_review: '05_review/html_review.json',
    physics_check: '02_processed/physics_check.json',
    conclusion: '02_processed/data_analysis_conclusion.json',
    validate_report: '02_processed/validate_report.json',
    visual_analysis: '03_figures/visual_analysis.json',
    ontology: '01_ontology/ontology.json',
    preflight: '05_review/optimizer_preflight.md',
    evidence_closure: 'evidence_closure_report.json',
  };
  const rel = MAP[kind];
  if (!rel) return null;
  const p = join(runDir, rel);
  if (!existsSync(p)) return null;
  const isJson = extname(p) === '.json';
  const raw = readFileSync(p, 'utf8');
  return {
    kind,
    path: rel,
    size: statSync(p).size,
    content: isJson ? tryReadJson(p) : raw,
  };
}

export function getOmpEnhancement(name, kind) {
  const runDir = join(RUNS_DIR, name);
  const enhDir = join(runDir, 'enhancement');
  if (!existsSync(enhDir)) return null;
  const MAP = {
    coverage: 'analysis_coverage.json',
    derived: 'derived_features.json',
    deep: 'deep_data_analysis.json',
    graph: 'association_graph.json',
    bridge: 'physics_bridge.json',
    knowledge: 'enhanced_knowledge.json',
    markdown: 'enhanced_analysis.md',
    html: 'enhanced-analysis.html',
    review: 'enhancement_html_review.json',
    status: 'enhancement_status.json',
    manifest: 'enhancement_manifest.json',
    selfcheck: 'html_selfcheck.json',
  };
  const rel = MAP[kind];
  if (!rel) return null;
  const p = join(enhDir, rel);
  if (!existsSync(p)) return null;
  const isJson = extname(p) === '.json';
  return {
    kind,
    path: `enhancement/${rel}`,
    size: statSync(p).size,
    content: isJson ? tryReadJson(p) : tryReadText(p, 300_000),
  };
}

/** Enrichment summaries for the frontend cards (kept light). */
export function getOmpSummary(name) {
  const runDir = join(RUNS_DIR, name);
  if (!existsSync(runDir)) return null;
  const conclusion = tryReadJson(join(runDir, '02_processed', 'data_analysis_conclusion.json'));
  const diagnosis = tryReadJson(join(runDir, '04_diagnostics', 'diagnosis.json'));
  const knowledge = tryReadJson(join(runDir, 'enhancement', 'enhanced_knowledge.json'));
  return {
    primary_finding: diagnosis?.primary_finding || null,
    diagnosis_type: diagnosis?.diagnosis_type || null,
    conclusion_summary: conclusion?.summary || conclusion?.conclusion || null,
    enhanced_relationships: knowledge?.relationship_graph?.edges?.length ?? null,
    enhanced_mechanism_chains: knowledge?.mechanism_chains?.length ?? null,
    enhanced_gaps: knowledge?.evidence_gaps?.length ?? null,
  };
}

export { RUNS_DIR };
