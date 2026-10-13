#!/usr/bin/env node
/** enhance_orchestrator.mjs — Task 5: Enhancement Pipeline Orchestrator
 *
 * E0  readiness check   — verify baseline files, compute sha256, write manifest
 * E1-E5 launcher        — run E1-E4 Python scripts + E5 physics-bridge
 * E6  knowledge fusion  — run knowledge_fusion.py
 * E7a markdown publish  — run markdown_publisher.py
 * E8  finalize          — write enhancement_status.json, print summary
 *
 * CLI: node enhance_orchestrator.mjs --run-dir PATH [--data-path PATH]
 * Prints status JSON to stdout.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { spawn, execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import {
  fileHash,
  isFreshBySignature,
  resolveEnhancementStatus,
  reviewIsPassing,
  shouldBuildAssociationGraph,
} from './orchestration_contract.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ── helpers ────────────────────────────────────────────────────────────

function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function fileExists(filePath) {
  try {
    const stat = fs.statSync(filePath);
    return stat.size > 0;
  } catch {
    return false;
  }
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

/** Run a command, return { ok, stdout, stderr, code } */
/** Resolve the uv execution environment via uv_env_setup.mjs (uv-first engine).
 *  Returns { uvCmd: ["uv","run","--project",<dir>] | null, python: <venv python> }.
 *  When uv is available, all Python scripts run via `uv run --project <shared>`.
 */
function resolvePythonEnv() {
  const sharedPath = path.resolve(__dirname, '..', '..', '..', 'shared', 'scripts');
  try {
    const out = execFileSync(process.execPath, [
      path.join(sharedPath, 'uv_env_setup.mjs'),
    ], { encoding: 'utf-8', timeout: 60000 });
    const parsed = JSON.parse(out.trim());
    if (parsed.uv_cmd && parsed.uv_cmd.length) {
      return { uvCmd: parsed.uv_cmd, python: parsed.python };
    }
    if (parsed.python) {
      return { uvCmd: null, python: parsed.python };
    }
  } catch (_) { /* fall through */ }
  return { uvCmd: null, python: 'python' }; // last-resort fallback
}

const PY_ENV = process.env.HARNESS_TEST_PYTHON
  ? { uvCmd: null, python: process.env.HARNESS_TEST_PYTHON }
  : resolvePythonEnv();
const PYTHON_BIN = PY_ENV.python;

/** Build argv for a Python script: uv run prefix when available, else venv python. */
function pythonArgs(scriptArgs) {
  if (PY_ENV.uvCmd) {
    return [...PY_ENV.uvCmd.slice(1), 'python', ...scriptArgs];
  }
  return scriptArgs;
}

const UV_CMD = PY_ENV.uvCmd ? PY_ENV.uvCmd[0] : PYTHON_BIN;

function runCmd(cmd, args, cwd, timeout = 120000, { shell = true } = {}) {
  return new Promise((resolve) => {
    // shell:false when cmd is a resolved binary path (e.g. process.execPath —
    // "D:\Program Files\..." breaks under cmd word-splitting).
    const proc = spawn(cmd, args, { cwd, shell, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    const timer = setTimeout(() => { proc.kill(); resolve({ ok: false, stdout, stderr, code: -1 }); }, timeout);
    proc.on('close', (code) => {
      clearTimeout(timer);
      resolve({ ok: code === 0, stdout, stderr, code });
    });
  });
}

function signaturePath(output) {
  return `${output}.signature.json`;
}

function phaseSignature(scriptPath, inputs, schemaPath = null) {
  const sourceHash = fileHash(scriptPath);
  const schemas = schemaPath ? (Array.isArray(schemaPath) ? schemaPath : [schemaPath]) : [];
  const schemaHashes = schemas.map(fileHash);
  if (!sourceHash || schemaHashes.some(hash => !hash)) return null;
  const scriptHash = crypto.createHash('sha256').update(JSON.stringify([sourceHash, ...schemaHashes])).digest('hex');
  const inputHashes = {};
  for (const entry of inputs) {
    const input = typeof entry === 'string' ? entry : entry.path;
    const optional = typeof entry === 'object' && entry.optional === true;
    const hash = fileHash(input);
    if (!hash && !optional) return null;
    inputHashes[path.resolve(input)] = hash;
  }
  return { scriptHash, inputs: inputHashes };
}

function isCurrent(output, inputs, scriptPath, schemaPath = null) {
  if (!fileExists(output)) return false;
  const previousPath = signaturePath(output);
  if (!fileExists(previousPath)) return false;
  try {
    const previous = JSON.parse(fs.readFileSync(previousPath, 'utf8'));
    const current = phaseSignature(scriptPath, inputs, schemaPath);
    return isFreshBySignature(previous, current);
  } catch {
    return false;
  }
}

function writePhaseSignature(output, inputs, scriptPath, schemaPath = null) {
  const signature = phaseSignature(scriptPath, inputs, schemaPath);
  if (!signature) throw new Error(`Cannot fingerprint all inputs for ${path.basename(output)}`);
  fs.writeFileSync(signaturePath(output), JSON.stringify(signature, null, 2) + '\\n');
}

async function validateArtifact(schemaName, artifactPath, cwd) {
  const sharedRoot = path.resolve(__dirname, '..', '..', '..', 'shared');
  const validator = path.join(sharedRoot, 'scripts', 'validate.mjs');
  const schema = path.join(sharedRoot, 'schemas', schemaName);
  const result = await runCmd(process.execPath, [validator, schema, artifactPath], cwd, 30000, { shell: false });
  return result.ok ? null : (result.stdout || result.stderr || `schema validation failed: ${schemaName}`).slice(0, 500);
}

// ── E0: readiness check ────────────────────────────────────────────────

const BASELINE_CHECKS = [
  { file: '01_ontology/ontology.json', required: true, label: 'ontology' },
  { file: '02_processed/cleaned_data.csv', required: true, label: 'cleaned_data' },
  { file: '02_processed/feature_summary.json', required: true, label: 'feature_summary' },
  { file: '02_processed/validate_report.json', required: true, label: 'validate_report' },
  { file: '02_processed/data_analysis_conclusion.json', required: true, label: 'data_analysis_conclusion' },
  { file: '02_processed/analysis_parameter_selection.json', required: true, label: 'analysis_parameter_selection' },
  { file: '02_processed/production_regime_filter.json', required: false, label: 'production_regime_filter' },
  { file: '04_diagnostics/diagnosis.json', required: true, label: 'diagnosis' },
  { file: '04_diagnostics/evidence.json', required: true, label: 'evidence' },
  { file: '04_diagnostics/confidence.json', required: true, label: 'confidence' },
  { file: '04_diagnostics/reasoning_chain.json', required: true, label: 'reasoning_chain' },
  { file: '03_figures/plot_manifest.json', required: true, label: 'plot_manifest' },
  { file: '03_figures/visual_analysis.json', required: true, label: 'visual_analysis' },
];

function readinessCheck(runDir, dataPath = null) {
  const missing = [];
  const present = {};
  // Execution-policy contract: a VLM skip recorded in the run manifest (with
  // matching evidence event) downgrades visual_analysis.json to optional —
  // the L4 image-caption fallback carries the visual layer instead.
  let vlmSkipped = false;
  try {
    const manifest = JSON.parse(fs.readFileSync(path.join(runDir, 'run_manifest.json'), 'utf8'));
    const skipped = manifest.execution_policy?.audit?.skipped_stages || [];
    vlmSkipped = skipped.some(s => s.stage === 'vlm_analysis' && s.reason && s.event);
  } catch { /* manifest absent → default required */ }
  const captionsPresent = fileExists(path.join(runDir, '03_figures', 'image_captions.json'));
  for (const check of BASELINE_CHECKS) {
    const fp = path.join(runDir, check.file);
    const optionalNow = check.file === '03_figures/visual_analysis.json' && vlmSkipped && captionsPresent;
    const ok = fileExists(fp);
    if (ok) {
      present[check.label] = true;
    } else if (check.required && !optionalNow) {
      missing.push(check.file);
    }
  }
  if (missing.length > 0) {
    const enhanceDir = path.join(runDir, 'enhancement');
    ensureDir(enhanceDir);
    const blockerStatus = {
      status: 'BLOCKED',
      missing,
      created_at: new Date().toISOString(),
      guidance: 'Baseline diagnostic artifacts are missing. Run the baseline first via industrial-analysis-auto (Step 0-9), or dispatch the enhance-orchestrator agent with DATA_PATH for entry-A full flow (auto baseline + enhancement).',
    };
    fs.writeFileSync(
      path.join(enhanceDir, 'enhancement_status.json'),
      JSON.stringify(blockerStatus, null, 2) + '\n'
    );
    return { ok: false, missing, blockerStatus };
  }

  // Compute sha256 of cleaned_data.csv
  const csvPath = path.join(runDir, '02_processed', 'cleaned_data.csv');
  const csvHash = sha256File(csvPath);

  // Count rows and columns
  const header = fs.readFileSync(csvPath, 'utf8').split('\n')[0];
  const cols = header.split(',').length;
  const lines = fs.readFileSync(csvPath, 'utf8').trim().split('\n');
  const rows = lines.length - 1; // minus header

  // Create enhancement + figures dirs
  const enhanceDir = path.join(runDir, 'enhancement');
  ensureDir(enhanceDir);
  ensureDir(path.join(enhanceDir, 'figures'));

  // Build manifest
  const manifest = {
    run_id: `enhance-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}`,
    baseline_run_dir: runDir,
    input_mode: 'B_existing_run',
    data_source: {
      file: 'cleaned_data.csv',
      original_path: dataPath || null,
      sha256: csvHash,
      rows,
      cols,
    },
    baseline_artifacts: {
      ontology: true,
      diagnosis: true,
      report: fileExists(path.join(runDir, 'report.md')),
      evidence: true,
      reasoning_chain: true,
      data_analysis_conclusion: true,
    },
    enhancement_version: '1.0.0',
    created_at: new Date().toISOString(),
    enhancement_artifacts: {
      analysis_coverage: false,
      derived_features: false,
      deep_data_analysis: false,
      association_graph: false,
      physics_bridge: false,
    },
  };

  fs.writeFileSync(
    path.join(enhanceDir, 'enhancement_manifest.json'),
    JSON.stringify(manifest, null, 2) + '\n'
  );

  return { ok: true, manifest, csvHash, rows, cols };
}

// ── E1-E5 launcher + E6/E7a ───────────────────────────────────────────

async function launchScripts(runDir) {
  const enhanceDir = path.join(runDir, 'enhancement');
  const skillRoot = path.resolve(__dirname, '..', '..');

  const scripts = [
    {
      phase: 'E1',
      cmd: UV_CMD,
      args: pythonArgs([
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'coverage_builder.py'),
        '--run-dir', runDir,
      ]),
      output: path.join(enhanceDir, 'analysis_coverage.json'),
      script: path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'coverage_builder.py'),
      schema: 'analysis_coverage_schema.json',
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'feature_summary.json'),
        path.join(runDir, '02_processed', 'cleaned_data.csv'),
        path.join(runDir, '02_processed', 'analysis_parameter_selection.json'),
        path.join(runDir, '02_processed', 'data_analysis_conclusion.json'),
      ],
    },
    {
      phase: 'E2',
      cmd: UV_CMD,
      args: pythonArgs([
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'derived_feature_builder.py'),
        '--run-dir', runDir,
      ]),
      output: path.join(enhanceDir, 'derived_features.json'),
      script: path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'derived_feature_builder.py'),
      schema: 'derived_features_schema.json',
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'cleaned_data.csv'),
        path.join(runDir, '02_processed', 'analysis_parameter_selection.json'),
        path.join(enhanceDir, 'analysis_coverage.json'),
      ],
    },
    {
      phase: 'E3',
      cmd: UV_CMD,
      args: pythonArgs([
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'conditional_analysis.py'),
        '--run-dir', runDir,
      ]),
      output: path.join(enhanceDir, 'deep_data_analysis.json'),
      graphOutput: path.join(enhanceDir, 'association_graph.json'),
      graphSchema: 'association_graph_schema.json',
      script: path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'conditional_analysis.py'),
      schema: 'deep_data_analysis_schema.json',
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'cleaned_data.csv'),
        path.join(runDir, '02_processed', 'analysis_parameter_selection.json'),
        { path: path.join(runDir, '02_processed', 'production_regime_filter.json'), optional: true },
        { path: path.join(enhanceDir, 'derived_data.csv'), optional: true },
        path.join(enhanceDir, 'analysis_coverage.json'),
        path.join(enhanceDir, 'derived_features.json'),
        path.join(runDir, '02_processed', 'data_analysis_conclusion.json'),
      ],
    },
    {
      phase: 'E5',
      cmd: UV_CMD,
      args: pythonArgs([
        path.join(skillRoot, 'industrial-physics-bridge', 'scripts', 'physics_bridge_builder.py'),
        '--run-dir', runDir,
      ]),
      output: path.join(enhanceDir, 'physics_bridge.json'),
      script: path.join(skillRoot, 'industrial-physics-bridge', 'scripts', 'physics_bridge_builder.py'),
      schema: 'physics_bridge_schema.json',
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'analysis_parameter_selection.json'),
        { path: path.join(runDir, '02_processed', 'production_regime_filter.json'), optional: true },
        { path: path.join(enhanceDir, 'derived_data.csv'), optional: true },
        path.join(runDir, '04_diagnostics', 'diagnosis.json'),
        path.join(runDir, '04_diagnostics', 'evidence.json'),
        path.join(runDir, '04_diagnostics', 'confidence.json'),
        path.join(runDir, '04_diagnostics', 'reasoning_chain.json'),
        { path: path.join(runDir, '03_figures', 'visual_analysis.json'), optional: true },
        { path: path.join(runDir, '00_input', 'rag_deep_understanding.json'), optional: true },
        path.join(enhanceDir, 'deep_data_analysis.json'),
        path.join(enhanceDir, 'association_graph.json'),
      ],
    },
  ];

  const results = [];
  const schemaFile = (name) => path.join(path.resolve(__dirname, '..', '..', '..', 'shared', 'schemas'), name);
  for (const s of scripts) {
    const output = s.output;
    const schemaPath = s.graphSchema ? [schemaFile(s.schema), schemaFile(s.graphSchema)] : schemaFile(s.schema);
    const graphSchemaPath = s.graphSchema ? schemaFile(s.graphSchema) : null;
    const graphCurrent = s.phase !== 'E3' || isCurrent(s.graphOutput, s.inputs, s.script, graphSchemaPath);
    if (isCurrent(output, s.inputs, s.script, schemaPath) && graphCurrent) {
      const graphError = s.phase === 'E3' ? await validateArtifact(s.graphSchema, s.graphOutput, runDir) : null;
      if (!graphError) {
        results.push({ phase: s.phase, status: 'skipped', reason: 'input+script signatures are current' });
        continue;
      }
    }
    if (s.phase === 'E3') {
      for (const stale of [s.output, signaturePath(s.output), s.graphOutput, signaturePath(s.graphOutput)]) {
        try { fs.rmSync(stale, { force: true }); } catch (_) {}
      }
    }
    const r = await runCmd(s.cmd, s.args, runDir, 120000);
    results.push({
      phase: s.phase,
      status: r.ok ? 'ok' : 'failed',
      code: r.code,
      stderr: r.stderr ? r.stderr.slice(0, 500) : '',
    });
    if (!r.ok) return { ok: false, results };
    if (!fileExists(output)) {
      results.push({ phase: s.phase, status: 'failed', reason: `output ${output} not created` });
      return { ok: false, results };
    }
    const validationError = await validateArtifact(s.schema, output, runDir);
    if (validationError) {
      results.push({ phase: s.phase, status: 'failed', reason: validationError });
      return { ok: false, results };
    }
    if (s.phase === 'E3') {
      if (!fileExists(s.graphOutput)) {
        results.push({ phase: s.phase, status: 'failed', reason: 'E3 did not emit association_graph.json' });
        return { ok: false, results };
      }
      const graphError = await validateArtifact(s.graphSchema, s.graphOutput, runDir);
      if (graphError) {
        results.push({ phase: s.phase, status: 'failed', reason: graphError });
        return { ok: false, results };
      }
      writePhaseSignature(s.graphOutput, s.inputs, s.script, graphSchemaPath);
    }
    writePhaseSignature(output, s.inputs, s.script, schemaPath);
  }

  // E6: knowledge fusion
  const fusionOutput = path.join(enhanceDir, 'enhanced_knowledge.json');
  const fusionScript = path.join(__dirname, 'knowledge_fusion.py');
  const fusionInputs = [
    path.join(enhanceDir, 'analysis_coverage.json'),
    path.join(enhanceDir, 'derived_features.json'),
    path.join(enhanceDir, 'deep_data_analysis.json'),
    path.join(enhanceDir, 'association_graph.json'),
    path.join(enhanceDir, 'physics_bridge.json'),
    path.join(runDir, '04_diagnostics', 'diagnosis.json'),
    path.join(runDir, '04_diagnostics', 'evidence.json'),
    path.join(runDir, '04_diagnostics', 'confidence.json'),
    path.join(runDir, '04_diagnostics', 'reasoning_chain.json'),
  ];
  const knowledgeSchema = schemaFile('enhanced_knowledge_schema.json');
  if (!isCurrent(fusionOutput, fusionInputs, fusionScript, knowledgeSchema)) {
    const fusionResult = await runCmd(UV_CMD, pythonArgs([fusionScript, '--run-dir', runDir, '--output', fusionOutput]), runDir);
    results.push({ phase: 'E6', status: fusionResult.ok ? 'ok' : 'failed', code: fusionResult.code,
      stderr: fusionResult.stderr ? fusionResult.stderr.slice(0, 500) : '' });
    if (!fusionResult.ok) return { ok: false, results };
    if (!fileExists(fusionOutput)) return { ok: false, results: [...results, { phase: 'E6', status: 'failed', reason: 'enhanced_knowledge.json not created' }] };
    const validationError = await validateArtifact('enhanced_knowledge_schema.json', fusionOutput, runDir);
    if (validationError) return { ok: false, results: [...results, { phase: 'E6', status: 'failed', reason: validationError }] };
    writePhaseSignature(fusionOutput, fusionInputs, fusionScript, knowledgeSchema);
  } else {
    results.push({ phase: 'E6', status: 'skipped', reason: 'input+script signature is current' });
  }

  // E7a: markdown publisher
  const mdOutput = path.join(enhanceDir, 'enhanced_analysis.md');
  const tmplPath = path.join(__dirname, '..', 'templates', 'enhanced_analysis.md.tmpl');
  const pubScript = path.join(__dirname, 'markdown_publisher.py');
  const pubInputs = [fusionOutput, tmplPath];
  if (!isCurrent(mdOutput, pubInputs, pubScript)) {
    const pubResult = await runCmd(UV_CMD, pythonArgs([pubScript, '--knowledge', fusionOutput, '--template', tmplPath, '--output', mdOutput]), runDir);
    results.push({ phase: 'E7a', status: pubResult.ok ? 'ok' : 'failed', code: pubResult.code,
      stderr: pubResult.stderr ? pubResult.stderr.slice(0, 500) : '' });
    if (!pubResult.ok || !fileExists(mdOutput)) return { ok: false, results };
    writePhaseSignature(mdOutput, pubInputs, pubScript);
  } else {
    results.push({ phase: 'E7a', status: 'skipped', reason: 'input+script signature is current' });
  }

  // E7b: enhanced HTML visualizer
  const htmlOutput = path.join(enhanceDir, 'enhanced-analysis.html');
  const htmlBuilderScript = path.join(skillRoot, 'industrial-enhanced-html-visualizer', 'scripts', 'html_builder.py');
  const htmlInputs = [fusionOutput];
  if (!isCurrent(htmlOutput, htmlInputs, htmlBuilderScript)) {
    const htmlResult = await runCmd(UV_CMD, pythonArgs([htmlBuilderScript, '--knowledge', fusionOutput, '--output', htmlOutput]), runDir);
    results.push({ phase: 'E7b', status: htmlResult.ok ? 'ok' : 'failed', code: htmlResult.code,
      stderr: htmlResult.stderr ? htmlResult.stderr.slice(0, 500) : '' });
    if (!htmlResult.ok || !fileExists(htmlOutput)) return { ok: false, results };
    writePhaseSignature(htmlOutput, htmlInputs, htmlBuilderScript);
  } else {
    results.push({ phase: 'E7b', status: 'skipped', reason: 'input+script signature is current' });
  }

  // E7c: HTML review verdict is a release gate, not merely a successful subprocess.
  const reviewOutput = path.join(enhanceDir, 'enhancement_html_review.json');
  const selfcheckPath = path.join(enhanceDir, 'html_selfcheck.json');
  const reviewerScript = path.join(skillRoot, 'industrial-enhanced-html-reviewer', 'scripts', 'html_reviewer.py');
  const reviewResult = await runCmd(UV_CMD, pythonArgs([reviewerScript, '--knowledge', fusionOutput, '--html', htmlOutput, '--output', reviewOutput, '--selfcheck', selfcheckPath]), runDir);
  results.push({ phase: 'E7c', status: reviewResult.ok ? 'ok' : 'failed', code: reviewResult.code,
    stderr: reviewResult.stderr ? reviewResult.stderr.slice(0, 500) : '' });
  if (!reviewResult.ok || !fileExists(reviewOutput)) return { ok: false, results };
  const reviewValidation = await validateArtifact('enhancement_html_review_schema.json', reviewOutput, runDir);
  if (reviewValidation) return { ok: false, results: [...results, { phase: 'E7c', status: 'failed', reason: reviewValidation }] };
  let review;
  try { review = JSON.parse(fs.readFileSync(reviewOutput, 'utf8')); }
  catch { return { ok: false, results: [...results, { phase: 'E7c', status: 'failed', reason: 'review JSON is unreadable' }] }; }
  if (!reviewIsPassing(review)) {
    return { ok: false, results: [...results, { phase: 'E7c', status: 'failed', reason: `review verdict=${review.verdict}` }] };
  }

  return { ok: true, results, fusionOutput, markdownOutput: mdOutput, htmlOutput, reviewOutput };
}

// ── E8: finalize ──────────────────────────────────────────────────────

function finalize(runDir, manifest, launchResults) {
  const enhanceDir = path.join(runDir, 'enhancement');
  const kbPath = path.join(enhanceDir, 'enhanced_knowledge.json');

  let knowledgeStatus = 'FAILED';
  let warnings = [];

  if (fileExists(kbPath)) {
    try {
      const kb = JSON.parse(fs.readFileSync(kbPath, 'utf8'));
      knowledgeStatus = kb.enhancement_status || 'FAILED';

      // Count CONFOUNDED and NOT_IDENTIFIABLE among edges that carry a real
      // operability verdict (UNCLASSIFIED graph edges from the full pairwise
      // network must not drive status downgrades).
      const relationships = kb.relationship_graph?.edges || [];
      const OPER_ENUM = ['LEVER_IDENTIFIED', 'LEVER_OBSERVATIONAL', 'ENDOGENOUS_RESPONSE',
                         'CONFOUNDED', 'NOT_IDENTIFIABLE', 'CONSTRAINT_UNCONTROLLABLE'];
      const classified = relationships.filter((e) => OPER_ENUM.includes(e.operability));
      const confoundedCount = classified.filter(
        (e) => e.operability === 'CONFOUNDED' || e.operability === 'NOT_IDENTIFIABLE'
      ).length;
      if (classified.length > 0 && confoundedCount / classified.length > 0.3) {
        if (knowledgeStatus !== 'READY_WITH_WARNINGS') {
          warnings.push(
            `${confoundedCount}/${relationships.length} relationships are CONFOUNDED or NOT_IDENTIFIABLE (>30%)`
          );
        }
      }
    } catch {
      warnings.push('Failed to parse enhanced_knowledge.json');
    }
  }

  let review = null;
  const reviewPath = path.join(enhanceDir, 'enhancement_html_review.json');
  try {
    if (fileExists(reviewPath)) review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));
  } catch { /* invalid or stale review remains a hard failure below */ }
  const launchOk = launchResults.ok === true;
  const enhancementStatus = resolveEnhancementStatus({ launchOk, knowledgeStatus, review });
  if (!launchOk) warnings.push('One or more required enhancement stages failed; stale prior artifacts cannot mark this run READY.');
  if (review && review.verdict !== 'pass') warnings.push(`HTML reviewer verdict=${review.verdict}; READY is blocked.`);
  if (!review) warnings.push('HTML review artifact is missing or unreadable.');

  const statusObj = {
    status: enhancementStatus,
    warnings,
    run_id: manifest.run_id,
    created_at: new Date().toISOString(),
    artifact_paths: {
      manifest: path.join(enhanceDir, 'enhancement_manifest.json'),
      enhanced_knowledge: path.join(enhanceDir, 'enhanced_knowledge.json'),
      markdown: path.join(enhanceDir, 'enhanced_analysis.md'),
      html: path.join(enhanceDir, 'enhanced-analysis.html'),
      html_review: path.join(enhanceDir, 'enhancement_html_review.json'),
      html_selfcheck: path.join(enhanceDir, 'html_selfcheck.json'),
    },
    launch_results: launchResults.results || [],
  };

  fs.writeFileSync(
    path.join(enhanceDir, 'enhancement_status.json'),
    JSON.stringify(statusObj, null, 2) + '\n'
  );

  return statusObj;
}

// ── main ───────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  let runDir = null;
  let dataPath = null;
  let name = null;
  let baseDir = null;
  let requestedMode = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--run-dir' && i + 1 < args.length) runDir = args[++i];
    if (args[i] === '--data-path' && i + 1 < args.length) dataPath = args[++i];
    if (args[i] === '--name' && i + 1 < args.length) name = args[++i];
    if (args[i] === '--base-dir' && i + 1 < args.length) baseDir = args[++i];
    if (args[i] === '--mode' && i + 1 < args.length) requestedMode = args[++i];
  }
  if (requestedMode && !['fast', 'full'].includes(requestedMode)) {
    console.error(`ERROR: invalid --mode ${JSON.stringify(requestedMode)}; expected fast or full`);
    process.exit(2);
  }

  // Mode A: no --run-dir but --data-path given → initialize the run dir first
  if (!runDir && dataPath) {
    if (!name) {
      console.error('Usage (entry A): node enhance_orchestrator.mjs --data-path <data> --name <run_name> [--mode fast|full] [--base-dir <dir>]');
      process.exit(1);
    }
    const initArgs = ['--data-path', dataPath, '--name', name, '--mode', requestedMode || 'full'];
    if (baseDir) initArgs.push('--base-dir', baseDir);
    const initScript = path.join(__dirname, 'entry_a_init.mjs');
    const initResult = await runCmd(process.execPath, [initScript, ...initArgs], process.cwd(), 120000);
    if (!initResult.ok) {
      console.error('ERROR: entry-A initialization failed:', initResult.stderr || initResult.code);
      process.exit(1);
    }
    let initOut = null;
    try {
      initOut = JSON.parse(initResult.stdout.trim());
    } catch (_) {
      console.error('ERROR: entry-a-init output not parseable:', initResult.stdout);
      process.exit(1);
    }
    runDir = initOut.run_dir;
    if (!initOut.baseline_complete) {
      // Baseline LLM steps still missing — enhancement cannot proceed yet.
      console.log(JSON.stringify({
        phase: 'A0',
        status: 'BASELINE_PENDING',
        run_dir: runDir,
        missing_baseline: initOut.missing_baseline,
        next_steps: initOut.next_steps,
        message: 'Entry-A init done. Run the auto baseline Step 2-9 on this RUN_DIR, or dispatch the enhance-orchestrator agent with DATA_PATH for fully automatic baseline+enhancement.',
      }, null, 2));
      process.exit(1);
    }
    console.log(JSON.stringify({
      phase: 'A0',
      status: 'BASELINE_READY',
      run_dir: runDir,
    }, null, 2));
  }

  if (!runDir) {
    console.error('Usage: node enhance_orchestrator.mjs --run-dir PATH | --data-path <data> --name <run_name>');
    process.exit(1);
  }

  runDir = path.resolve(runDir);
  const configPath = path.join(runDir, '00_input', 'run_config.json');
  let runConfig = null;
  try { runConfig = JSON.parse(fs.readFileSync(configPath, 'utf8')); } catch { /* E0 reports the missing/corrupt config */ }
  if (runConfig && !['fast', 'full'].includes(runConfig.run_mode)) {
    console.error(`ERROR: run_config.run_mode must be fast or full; got ${JSON.stringify(runConfig.run_mode)}`);
    process.exit(2);
  }
  if (requestedMode && runConfig && requestedMode !== runConfig.run_mode) {
    console.error(`ERROR: --mode ${requestedMode} does not match RUN_DIR run_mode ${runConfig.run_mode}`);
    process.exit(2);
  }

  // E0: readiness check
  const ready = readinessCheck(runDir, dataPath);
  if (!ready.ok) {
    console.log(JSON.stringify({
      phase: 'E0',
      status: 'BLOCKED',
      missing: ready.missing,
      enhancement_status: ready.blockerStatus,
    }, null, 2));
    process.exit(1);
  }

  console.log(JSON.stringify({
    phase: 'E0',
    status: 'READY',
    manifest: ready.manifest,
  }, null, 2));

  // E1-E5 + E6 + E7a
  const launchResults = await launchScripts(runDir);

  // E8: finalize
  const statusObj = finalize(runDir, ready.manifest, launchResults);

  const finalOutput = {
    phase: 'E8',
    status: statusObj.status,
    run_id: ready.manifest.run_id,
    warnings: statusObj.warnings,
    artifacts: statusObj.artifact_paths,
    launch_phases: statusObj.launch_results,
  };

  console.log(JSON.stringify(finalOutput, null, 2));
  process.exit(statusObj.status === 'BLOCKED' || statusObj.status === 'FAILED' ? 1 : 0);
}

main().catch((err) => {
  console.error('FATAL:', err.message);
  process.exit(1);
});
