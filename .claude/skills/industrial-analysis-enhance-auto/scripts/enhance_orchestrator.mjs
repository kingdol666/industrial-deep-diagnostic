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
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

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
function runCmd(cmd, args, cwd, timeout = 120000) {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { cwd, shell: true, stdio: ['ignore', 'pipe', 'pipe'] });
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

/** Check if file f is newer than all files in refs[] */
function isNewerThan(f, refs) {
  if (!fileExists(f)) return false;
  const fstat = fs.statSync(f);
  for (const r of refs) {
    if (!fileExists(r)) return true; // ref missing → consider output stale
    if (fs.statSync(r).mtime > fstat.mtime) return false;
  }
  return true;
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
  for (const check of BASELINE_CHECKS) {
    const fp = path.join(runDir, check.file);
    const ok = fileExists(fp);
    if (ok) {
      present[check.label] = true;
    } else if (check.required) {
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
      cmd: 'python',
      args: [
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'coverage_builder.py'),
        '--run-dir', runDir,
      ],
      output: path.join(enhanceDir, 'analysis_coverage.json'),
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
      cmd: 'python',
      args: [
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'derived_feature_builder.py'),
        '--run-dir', runDir,
      ],
      output: path.join(enhanceDir, 'derived_features.json'),
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'cleaned_data.csv'),
        path.join(enhanceDir, 'analysis_coverage.json'),
      ],
    },
    {
      phase: 'E3',
      cmd: 'python',
      args: [
        path.join(skillRoot, 'industrial-deep-analysis', 'scripts', 'conditional_analysis.py'),
        '--run-dir', runDir,
      ],
      output: path.join(enhanceDir, 'deep_data_analysis.json'),
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '02_processed', 'cleaned_data.csv'),
        path.join(enhanceDir, 'analysis_coverage.json'),
        path.join(enhanceDir, 'derived_features.json'),
        path.join(runDir, '02_processed', 'data_analysis_conclusion.json'),
      ],
    },
    {
      phase: 'E5',
      cmd: 'python',
      args: [
        path.join(skillRoot, 'industrial-physics-bridge', 'scripts', 'physics_bridge_builder.py'),
        '--run-dir', runDir,
      ],
      output: path.join(enhanceDir, 'physics_bridge.json'),
      inputs: [
        path.join(runDir, '01_ontology', 'ontology.json'),
        path.join(runDir, '04_diagnostics', 'diagnosis.json'),
        path.join(runDir, '04_diagnostics', 'evidence.json'),
        path.join(runDir, '04_diagnostics', 'confidence.json'),
        path.join(runDir, '04_diagnostics', 'reasoning_chain.json'),
        path.join(runDir, '03_figures', 'visual_analysis.json'),
        path.join(enhanceDir, 'deep_data_analysis.json'),
      ],
    },
  ];

  const results = [];
  for (const s of scripts) {
    if (isNewerThan(s.output, s.inputs)) {
      results.push({ phase: s.phase, status: 'skipped', reason: 'output is current' });
      continue;
    }
    const r = await runCmd(s.cmd, s.args, runDir, 120000);
    results.push({
      phase: s.phase,
      status: r.ok ? 'ok' : 'failed',
      code: r.code,
      stderr: r.stderr ? r.stderr.slice(0, 500) : '',
    });
    if (!r.ok) {
      return { ok: false, results };
    }
    // Verify output was created
    if (!fileExists(s.output)) {
      results.push({ phase: s.phase, status: 'failed', reason: `output ${s.output} not created` });
      return { ok: false, results };
    }
  }

  // E6: knowledge fusion
  const fusionOutput = path.join(enhanceDir, 'enhanced_knowledge.json');
  const fusionScript = path.join(__dirname, 'knowledge_fusion.py');
  const fusionResult = await runCmd('python', [fusionScript, '--run-dir', runDir, '--output', fusionOutput], runDir);
  results.push({
    phase: 'E6',
    status: fusionResult.ok ? 'ok' : 'failed',
    code: fusionResult.code,
    stderr: fusionResult.stderr ? fusionResult.stderr.slice(0, 500) : '',
  });
  if (!fusionResult.ok) return { ok: false, results };

  // E7a: markdown publisher
  const mdOutput = path.join(enhanceDir, 'enhanced_analysis.md');
  const tmplPath = path.join(__dirname, '..', 'templates', 'enhanced_analysis.md.tmpl');
  const pubScript = path.join(__dirname, 'markdown_publisher.py');
  const pubResult = await runCmd('python', [pubScript, '--knowledge', fusionOutput, '--template', tmplPath, '--output', mdOutput], runDir);
  results.push({
    phase: 'E7a',
    status: pubResult.ok ? 'ok' : 'failed',
    code: pubResult.code,
    stderr: pubResult.stderr ? pubResult.stderr.slice(0, 500) : '',
  });

  // E7b: enhanced HTML visualizer
  const htmlOutput = path.join(enhanceDir, 'enhanced-analysis.html');
  const htmlBuilderScript = path.join(skillRoot, 'industrial-enhanced-html-visualizer', 'scripts', 'html_builder.py');
  const htmlResult = await runCmd('python', [htmlBuilderScript, '--knowledge', fusionOutput, '--output', htmlOutput], runDir);
  results.push({
    phase: 'E7b',
    status: htmlResult.ok ? 'ok' : 'failed',
    code: htmlResult.code,
    stderr: htmlResult.stderr ? htmlResult.stderr.slice(0, 500) : '',
  });

  // E7c: enhanced HTML reviewer
  const reviewOutput = path.join(enhanceDir, 'enhancement_html_review.json');
  const selfcheckPath = path.join(enhanceDir, 'html_selfcheck.json');
  const reviewerScript = path.join(skillRoot, 'industrial-enhanced-html-reviewer', 'scripts', 'html_reviewer.py');
  const reviewResult = await runCmd('python', [reviewerScript, '--knowledge', fusionOutput, '--html', htmlOutput, '--output', reviewOutput, '--selfcheck', selfcheckPath], runDir);
  results.push({
    phase: 'E7c',
    status: reviewResult.ok ? 'ok' : 'failed',
    code: reviewResult.code,
    stderr: reviewResult.stderr ? reviewResult.stderr.slice(0, 500) : '',
  });

  return {
    ok: fusionResult.ok && pubResult.ok && htmlResult.ok && reviewResult.ok,
    results,
    fusionOutput,
    markdownOutput: mdOutput,
    htmlOutput,
    reviewOutput,
  };
}

// ── E8: finalize ──────────────────────────────────────────────────────

function finalize(runDir, manifest, launchResults) {
  const enhanceDir = path.join(runDir, 'enhancement');
  const kbPath = path.join(enhanceDir, 'enhanced_knowledge.json');

  let enhancementStatus = 'FAILED';
  let warnings = [];

  if (fileExists(kbPath)) {
    try {
      const kb = JSON.parse(fs.readFileSync(kbPath, 'utf8'));
      enhancementStatus = kb.enhancement_status || 'FAILED';

      // Count CONFOUNDED and NOT_IDENTIFIABLE
      const relationships = kb.relationship_graph?.edges || [];
      const confoundedCount = relationships.filter(
        (e) => e.operability === 'CONFOUNDED' || e.operability === 'NOT_IDENTIFIABLE'
      ).length;
      if (relationships.length > 0 && confoundedCount / relationships.length > 0.3) {
        if (enhancementStatus !== 'READY_WITH_WARNINGS') {
          warnings.push(
            `${confoundedCount}/${relationships.length} relationships are CONFOUNDED or NOT_IDENTIFIABLE (>30%)`
          );
        }
      }
    } catch {
      warnings.push('Failed to parse enhanced_knowledge.json');
    }
  }

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

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--run-dir' && i + 1 < args.length) runDir = args[++i];
    if (args[i] === '--data-path' && i + 1 < args.length) dataPath = args[++i];
    if (args[i] === '--name' && i + 1 < args.length) name = args[++i];
    if (args[i] === '--base-dir' && i + 1 < args.length) baseDir = args[++i];
  }

  // Mode A: no --run-dir but --data-path given → initialize the run dir first
  if (!runDir && dataPath) {
    if (!name) {
      console.error('Usage (entry A): node enhance_orchestrator.mjs --data-path <data> --name <run_name> [--base-dir <dir>]');
      process.exit(1);
    }
    const initArgs = ['--data-path', dataPath, '--name', name];
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
