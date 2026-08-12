#!/usr/bin/env node
/**
 * e2e-pipeline-test.mjs — Full end-to-end deterministic pipeline smoke test.
 *
 * Exercises every SCRIPT-driven step of both the baseline and enhancement
 * pipelines on a synthetic dataset, verifying that:
 *   1. setup.mjs → inspect.mjs → convert → dp_toolkit preprocess → stats →
 *      anomaly → finalize produces valid, schema-conformant artifacts.
 *   2. Enhancement E1-E8 scripts run successfully on the baseline output.
 *
 * Agent-driven steps (ontology, diagnosis, judge, reporter) are mocked with
 * minimal valid JSON so downstream schema validation proves the contract.
 *
 * Usage: node e2e-pipeline-test.mjs
 * Exit 0 = all pass, 1 = any failure.
 */

import fs from 'fs';
import path from 'path';
import { execFileSync, execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..', '..', '..');
const SHARED = path.join(PROJECT_ROOT, '.claude', 'shared', 'scripts');
const SKILLS = path.join(PROJECT_ROOT, '.claude', 'skills');
const TMPDIR = path.join(PROJECT_ROOT, 'workspace', 'e2e-test');

let passed = 0;
let failed = 0;
const failures = [];

function ok(name) { console.log(`  ✅ ${name}`); passed++; }
function fail(name, err) { console.log(`  ❌ ${name}: ${err}`); failed++; failures.push({ name, err: String(err) }); }

function run(cmd, args, label, cwd) {
  try {
    // When cmd is the resolved venv python and uv is available, execute via
    // `uv run --project <shared>` so the uv project environment is authoritative.
    let execCmd = cmd;
    let execArgs = args;
    if (cmd === PY_ENV?.python && PY_ENV?.uv_cmd && PY_ENV.uv_cmd.length) {
      execCmd = PY_ENV.uv_cmd[0];
      execArgs = [...PY_ENV.uv_cmd.slice(1), 'python', ...args];
    }
    const out = execFileSync(execCmd, execArgs, { encoding: 'utf-8', timeout: 60000, cwd: cwd || PROJECT_ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
    return out;
  } catch (e) {
    throw new Error(`${label} failed: ${(e.stderr || e.stdout || e.message || '').slice(0, 300)}`);
  }
}

function runValidate(schemaRel, dataPath) {
  const schemaPath = path.join(SKILLS, 'industrial-analysis-auto', 'schemas', schemaRel);
  const sharedSchema = path.join(PROJECT_ROOT, '.claude', 'shared', 'schemas', schemaRel);
  const sp = fs.existsSync(schemaPath) ? schemaPath : sharedSchema;
  const out = execFileSync('node', [path.join(SHARED, 'validate.mjs'), sp, dataPath], {
    encoding: 'utf-8', timeout: 15000, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const report = JSON.parse(out);
  if (!report.valid) throw new Error(`Schema invalid: ${(report.errors || []).map(e => e.message).join('; ')}`);
  return true;
}

// Resolve uv execution environment (uv-first engine)
let PY_ENV = null;
PY_ENV = JSON.parse(run(process.execPath, [path.join(SHARED, 'uv_env_setup.mjs')], 'uv_env_setup'));
const PYTHON = PY_ENV.python;

// ── Setup ──
console.log('\n=== E2E Pipeline Smoke Test ===\n');
console.log(`Python: ${PYTHON}`);
console.log(`Project: ${PROJECT_ROOT}\n`);

// Clean previous
if (fs.existsSync(TMPDIR)) fs.rmSync(TMPDIR, { recursive: true });
fs.mkdirSync(TMPDIR, { recursive: true });

const dataFile = path.join(TMPDIR, 'synthetic_process_data.csv');
const runDir = path.join(TMPDIR, 'run');

// ── Generate synthetic data ──
console.log('Phase 0: Generate synthetic data');
{
  const lines = ['timestamp,reactor_temp,feed_rate,cooling_flow,catalyst_age,product_purity,product_grade'];
  for (let i = 0; i < 200; i++) {
    const t = 80 + 0.1 * i + Math.sin(i * 0.15) * 3;
    const f = 100 + Math.cos(i * 0.08) * 4;
    const c = 50 - 0.05 * i + Math.sin(i * 0.2) * 2;
    const cat = 10 + i * 0.1; // catalyst ages linearly
    // Purity depends on temp (+), cooling (-), feed (+), catalyst age (-)
    const purity = 95 + (t - 80) * 0.4 - (c - 50) * 0.3 + (f - 100) * 0.2 - (cat - 10) * 0.15 + Math.sin(i * 0.5) * 0.5;
    const grade = i % 3 === 0 ? 'A' : i % 3 === 1 ? 'B' : 'C';
    const ts = `2024-01-${String((i % 28) + 1).padStart(2, '0')} ${String((i % 24)).padStart(2, '0')}:00:00`;
    lines.push(`${ts},${t.toFixed(1)},${f.toFixed(1)},${c.toFixed(1)},${cat.toFixed(1)},${purity.toFixed(2)},${grade}`);
  }
  fs.writeFileSync(dataFile, lines.join('\n') + '\n', 'utf-8');
  ok('Synthetic data generated (200 rows, 7 cols)');
}

// ── Step 0: setup.mjs ──
console.log('\nPhase 0: Run setup.mjs');
try {
  const out = run(process.execPath, [path.join(SKILLS, 'industrial-analysis-auto', 'scripts', 'setup.mjs'),
    '--name', 'e2e_test', '--base-dir', TMPDIR], 'setup.mjs');
  const parsed = JSON.parse(out.trim());
  const actualRunDir = parsed.run_dir;
  // setup creates timestamped dir; symlink or copy to our expected runDir
  if (actualRunDir !== runDir) {
    fs.cpSync(actualRunDir, runDir, { recursive: true });
    fs.rmSync(actualRunDir, { recursive: true });
  }
  if (!fs.existsSync(path.join(runDir, 'run_manifest.json'))) throw new Error('run_manifest.json missing');
  if (!fs.existsSync(path.join(runDir, '.pipeline_events.jsonl'))) throw new Error('events log missing');
  ok('setup.mjs created run_dir with manifest + events log');
} catch (e) { fail('setup.mjs', e.message); }

// ── Step 0.5: data_preprocessor.py ──
console.log('\nPhase 0.5: Run data_preprocessor.py');
try {
  const out = run(PYTHON, [
    path.join(SKILLS, 'industrial-data-preprocessor', 'scripts', 'data_preprocessor.py'),
    '--data-path', dataFile, '--output', path.join(runDir, '00_input'), '--name', 'e2e_test',
  ], 'data_preprocessor.py');
  const parsed = JSON.parse(out.trim());
  if (parsed.status !== 'ok') throw new Error(`status=${parsed.status}`);
  const csvPath = path.join(runDir, '00_input', 'preprocessed_data.csv');
  if (!fs.existsSync(csvPath)) throw new Error('preprocessed_data.csv not created');
  ok('data_preprocessor.py produced preprocessed_data.csv');
} catch (e) { fail('data_preprocessor.py', e.message); }

// ── Step 1: inspect.mjs ──
console.log('\nPhase 1: Run inspect.mjs');
const inspectedPath = path.join(runDir, '00_input', 'preprocessed_data.csv');
try {
  const out = run(process.execPath, [path.join(SKILLS, 'industrial-analysis-auto', 'scripts', 'inspect.mjs'),
    inspectedPath], 'inspect.mjs');
  const parsed = JSON.parse(out.trim());
  if (parsed.rows !== 200) throw new Error(`expected 200 rows, got ${parsed.rows}`);
  if (parsed.columns !== 7) throw new Error(`expected 7 cols, got ${parsed.columns}`);

  // Write input_manifest.json (normally done by main-agent)
  const manifest = {
    run_id: 'e2e_test',
    data_path: inspectedPath,
    raw_data_path: dataFile,
    data_profile: { rows: parsed.rows, columns: parsed.columns },
    columns: (parsed.column_details || []).map(c => ({ name: c.name, type: c.type })),
    inspected_at: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(runDir, '00_input', 'input_manifest.json'), JSON.stringify(manifest, null, 2) + '\n', 'utf-8');
  fs.writeFileSync(path.join(runDir, '00_input', 'user_context.json'),
    JSON.stringify({ run_id: 'e2e_test', user_objective: 'Maximize purity', process_description: 'CSTR reactor' }, null, 2) + '\n', 'utf-8');
  ok('inspect.mjs profiled data + wrote input_manifest');
} catch (e) { fail('inspect.mjs', e.message); }

// ── Mock ontology + context-builder artifacts ──
console.log('\nPhase 2: Mock ontology (agent step)');
try {
  const ontology = {
    run_id: 'e2e_test',
    process_category: 'chemical_reaction',
    scene_type: 'process_plus_inspection',
    parameters: [
      { name: 'timestamp', physical_meaning: '时间戳', unit: 'datetime', role: 'metadata', controllable: false },
      { name: 'reactor_temp', physical_meaning: '反应器温度', unit: '°C', role: 'process_parameter', equipment_stage: 'reactor', governing_law: 'Arrhenius: k=A·exp(-Ea/RT)', controllable: true },
      { name: 'feed_rate', physical_meaning: '进料流量', unit: 'kg/h', role: 'process_parameter', equipment_stage: 'feed', controllable: true },
      { name: 'cooling_flow', physical_meaning: '冷却水流量', unit: 'L/min', role: 'process_parameter', equipment_stage: 'cooling', governing_law: 'Q=m·c·ΔT', controllable: true },
      { name: 'catalyst_age', physical_meaning: '催化剂使用时长', unit: 'h', role: 'process_parameter', equipment_stage: 'reactor', controllable: false },
      { name: 'product_purity', physical_meaning: '产品纯度', unit: '%', role: 'quality_target', controllable: false },
      { name: 'product_grade', physical_meaning: '产品等级', unit: 'category', role: 'grouping', controllable: false },
    ],
    relationships: [
      { from: 'reactor_temp', to: 'product_purity', data_direction_validated: 'true', predicted_functional_form: 'positive_monotonic' },
      { from: 'cooling_flow', to: 'product_purity', data_direction_validated: 'true', predicted_functional_form: 'negative_monotonic' },
      { from: 'feed_rate', to: 'product_purity', data_direction_validated: 'true', predicted_functional_form: 'positive_monotonic' },
      { from: 'catalyst_age', to: 'product_purity', data_direction_validated: 'true', predicted_functional_form: 'negative_monotonic' },
    ],
  };
  fs.mkdirSync(path.join(runDir, '01_ontology'), { recursive: true });
  fs.writeFileSync(path.join(runDir, '01_ontology', 'ontology.json'), JSON.stringify(ontology, null, 2) + '\n', 'utf-8');
  fs.writeFileSync(path.join(runDir, '00_input', 'clarification_needed.json'),
    JSON.stringify({ clarification_status: 'AUTO_RESOLVED' }, null, 2) + '\n', 'utf-8');
  ok('Mock ontology written');
} catch (e) { fail('Mock ontology', e.message); }

// ── Step 3: data-processor scripts ──
console.log('\nPhase 3: Run data-processor scripts');

// 3a: convert
try {
  run(process.execPath, [path.join(SHARED, 'convert.mjs'), inspectedPath,
    '--output', path.join(runDir, '02_processed', 'cleaned_data.json')], 'convert.mjs');
  ok('convert.mjs produced cleaned_data.json');
} catch (e) { fail('convert.mjs', e.message); }

// 3b: dp_toolkit preprocess
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'dp_toolkit.py'),
    'preprocess', inspectedPath, path.join(runDir, '02_processed')], 'dp_toolkit preprocess');
  const cleanedCsv = path.join(runDir, '02_processed', 'cleaned_data.csv');
  if (!fs.existsSync(cleanedCsv)) throw new Error('cleaned_data.csv not created');
  ok('dp_toolkit preprocess produced cleaned_data.csv');
} catch (e) { fail('dp_toolkit preprocess', e.message); }

// 3c: stats run.py
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'stats', 'run.py'),
    '--run-dir', runDir, '--mode', 'full'], 'stats/run.py');
  const vr = path.join(runDir, '02_processed', 'validate_report.json');
  if (!fs.existsSync(vr)) throw new Error('validate_report.json not created');
  ok('stats/run.py produced validate_report.json');
} catch (e) { fail('stats/run.py', e.message); }

// 3d: production regime detector
try {
  const cleanedCsv = path.join(runDir, '02_processed', 'cleaned_data.csv');
  run(PYTHON, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'production_regime_detector.py'),
    cleanedCsv, path.join(runDir, '02_processed'), '--time-col', 'timestamp', '--group-col', 'product_grade'], 'production_regime_detector.py');
  const rf = path.join(runDir, '02_processed', 'production_regime_filter.json');
  if (!fs.existsSync(rf)) throw new Error('production_regime_filter.json not created');
  ok('production_regime_detector.py produced regime filter');
} catch (e) { fail('production_regime_detector.py', e.message); }

// 3e: dp_toolkit anomaly
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'dp_toolkit.py'),
    'anomaly', path.join(runDir, '02_processed', 'cleaned_data.json'), path.join(runDir, '02_processed'),
    '--target-cols', 'product_purity', '--process-cols', 'reactor_temp,cooling_flow,feed_rate,catalyst_age',
    '--data-view-mode', 'process_plus_inspection'], 'dp_toolkit anomaly');
  const ar = path.join(runDir, '02_processed', 'anomaly_report.json');
  if (!fs.existsSync(ar)) throw new Error('anomaly_report.json not created');
  ok('dp_toolkit anomaly produced anomaly_report.json');
} catch (e) { fail('dp_toolkit anomaly', e.message); }

// 3f: data-processor-finalize
try {
  // Need to write feature_summary.json and analysis_parameter_selection.json first
  const featureSummary = {
    total_rows: 200,
    numeric_columns: ['reactor_temp', 'feed_rate', 'cooling_flow', 'catalyst_age', 'product_purity'],
    target_columns: ['product_purity'],
    correlations: [
      { x: 'reactor_temp', y: 'product_purity', r: 0.65, p_value: 0.001 },
      { x: 'cooling_flow', y: 'product_purity', r: -0.55, p_value: 0.003 },
      { x: 'feed_rate', y: 'product_purity', r: 0.35, p_value: 0.02 },
      { x: 'catalyst_age', y: 'product_purity', r: -0.45, p_value: 0.008 },
    ],
  };
  fs.writeFileSync(path.join(runDir, '02_processed', 'feature_summary.json'), JSON.stringify(featureSummary, null, 2) + '\n', 'utf-8');

  const paramSelection = {
    source: 'Phase 0.4 ontology-guided analysis selection',
    ontology_file: '01_ontology/ontology.json',
    parameter_physical_groups: { thermal: ['reactor_temp', 'cooling_flow'] },
    quality_targets: ['product_purity'],
    analysis_tiers: { tier_1: [{target: 'product_purity', predictor: 'reactor_temp', justification: 'Arrhenius law'}, {target: 'product_purity', predictor: 'cooling_flow', justification: 'Heat removal'}], tier_2: [{target: 'product_purity', predictor: 'feed_rate', justification: 'Stoichiometry'}, {target: 'product_purity', predictor: 'catalyst_age', justification: 'Deactivation'}], tier_3: [], pruned: [] },
    pruned: [],
    predictor_cols: ['reactor_temp', 'cooling_flow', 'feed_rate', 'catalyst_age'],
    exclude_cols: ['timestamp', 'product_grade'],
  };
  fs.writeFileSync(path.join(runDir, '02_processed', 'analysis_parameter_selection.json'), JSON.stringify(paramSelection, null, 2) + '\n', 'utf-8');

  const scenarioClassification = {
    scene_type: 'process_plus_inspection',
    process_category: 'chemical_reaction',
    confidence: 'high',
    classification_basis: ['ontology', 'column_name_heuristics', 'value_range_patterns'],
    expected_physics: ['temperature drives reaction rate'],
  };
  fs.writeFileSync(path.join(runDir, '02_processed', 'scenario_classification.json'), JSON.stringify(scenarioClassification, null, 2) + '\n', 'utf-8');

  run(process.execPath, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'data-processor-finalize.mjs'), runDir],
    'data-processor-finalize.mjs');
  const dac = path.join(runDir, '02_processed', 'data_analysis_conclusion.json');
  if (!fs.existsSync(dac)) throw new Error('data_analysis_conclusion.json not created');
  ok('data-processor-finalize.mjs produced data_analysis_conclusion.json');
} catch (e) { fail('data-processor-finalize.mjs', e.message); }

// 3g: generate_captions (skeleton)
try {
  // Need plot_manifest.json — create minimal
  const plotManifest = {
    plots: [
      { filename: 'fig_01_temporal_overlay.png', figure_type: 'temporal_overlay', priority: 'high', plot_type: 'temporal_overlay' },
    ],
    metadata: { generated_at: new Date().toISOString() },
  };
  fs.mkdirSync(path.join(runDir, '03_figures'), { recursive: true });
  fs.writeFileSync(path.join(runDir, '03_figures', 'plot_manifest.json'), JSON.stringify(plotManifest, null, 2) + '\n', 'utf-8');

  run(process.execPath, [path.join(SKILLS, 'industrial-data-processor', 'scripts', 'generate_captions.mjs'), runDir],
    'generate_captions.mjs');
  const ic = path.join(runDir, '03_figures', 'image_captions.json');
  if (!fs.existsSync(ic)) throw new Error('image_captions.json not created');
  ok('generate_captions.mjs produced image_captions.json');
} catch (e) { fail('generate_captions.mjs', e.message); }

// ── Phase 3 schema validation ──
console.log('\nPhase 3: Schema validation of data-processor outputs');
try {
  runValidate('scenario_classification_schema.json', path.join(runDir, '02_processed', 'scenario_classification.json'));
  ok('scenario_classification.json schema-valid');
} catch (e) { fail('scenario_classification schema', e.message); }
try {
  runValidate('analysis_parameter_selection_schema.json', path.join(runDir, '02_processed', 'analysis_parameter_selection.json'));
  ok('analysis_parameter_selection.json schema-valid');
} catch (e) { fail('analysis_parameter_selection schema', e.message); }
try {
  runValidate('data_analysis_conclusion_schema.json', path.join(runDir, '02_processed', 'data_analysis_conclusion.json'));
  ok('data_analysis_conclusion.json schema-valid');
} catch (e) { fail('data_analysis_conclusion schema', e.message); }

// ── Enhancement pipeline E1-E8 ──
console.log('\n=== Enhancement Pipeline (E1-E8) ===\n');

// E1: coverage_builder
console.log('E1: coverage_builder.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-deep-analysis', 'scripts', 'coverage_builder.py'),
    '--run-dir', runDir], 'coverage_builder.py');
  const ac = path.join(runDir, 'enhancement', 'analysis_coverage.json');
  if (!fs.existsSync(ac)) throw new Error('analysis_coverage.json not created');
  ok('E1 coverage_builder produced analysis_coverage.json');
} catch (e) { fail('E1 coverage_builder', e.message); }

// E2: derived_feature_builder
console.log('E2: derived_feature_builder.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-deep-analysis', 'scripts', 'derived_feature_builder.py'),
    '--run-dir', runDir], 'derived_feature_builder.py');
  const df = path.join(runDir, 'enhancement', 'derived_features.json');
  if (!fs.existsSync(df)) throw new Error('derived_features.json not created');
  ok('E2 derived_feature_builder produced derived_features.json');
} catch (e) { fail('E2 derived_feature_builder', e.message); }

// E3: conditional_analysis
console.log('E3: conditional_analysis.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-deep-analysis', 'scripts', 'conditional_analysis.py'),
    '--run-dir', runDir], 'conditional_analysis.py');
  const dd = path.join(runDir, 'enhancement', 'deep_data_analysis.json');
  if (!fs.existsSync(dd)) throw new Error('deep_data_analysis.json not created');
  ok('E3 conditional_analysis produced deep_data_analysis.json');
} catch (e) { fail('E3 conditional_analysis', e.message); }

// E3.5: association_graph_builder
console.log('E3.5: association_graph_builder.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-deep-analysis', 'scripts', 'association_graph_builder.py'),
    '--run-dir', runDir], 'association_graph_builder.py');
  const ag = path.join(runDir, 'enhancement', 'association_graph.json');
  if (!fs.existsSync(ag)) throw new Error('association_graph.json not created');
  ok('E3.5 association_graph_builder produced association_graph.json');
} catch (e) { fail('E3.5 association_graph_builder', e.message); }

// ── Mock diagnosis artifacts for E5 ──
console.log('\nPhase 4: Mock diagnosis artifacts');
try {
  const diagDir = path.join(runDir, '04_diagnostics');
  fs.mkdirSync(diagDir, { recursive: true });

  const diagnosis = {
    run_id: 'e2e_test',
    diagnosis_type: 'DETERMINED',
    root_cause: {
      primary_hypothesis: 'H1',
      parameter: 'reactor_temp',
      mechanism: 'Higher temperature increases reaction rate, improving conversion and purity',
      confidence: 82,
    },
    hypotheses: {
      surviving: [{ id: 'H1', root_cause: 'reactor_temp driving purity', falsification_conditions: ['If temp-purity correlation vanishes in steady-state only'] }],
      eliminated: [
        { id: 'H2', root_cause: 'cooling_flow', exclusion_reason: 'Endogenous response to temperature changes', exclusion_confidence: 92 },
        { id: 'H3', root_cause: 'feed_rate', exclusion_reason: 'Weak partial correlation after controlling for temp', exclusion_confidence: 88 },
      ],
    },
    falsification_conditions: [{ hypothesis: 'H1', condition: 'Remove temp-purity correlation in detrended analysis' }],
  };
  fs.writeFileSync(path.join(diagDir, 'diagnosis.json'), JSON.stringify(diagnosis, null, 2) + '\n', 'utf-8');

  const evidence = {
    run_id: 'e2e_test',
    evidence_items: [
      { id: 'E1', rank: 'L2', description: 'Temperature-purity correlation r=0.65', supports: 'H1', evidence_type: 'statistical' },
      { id: 'E2', rank: 'L3', description: 'Physical mechanism: Arrhenius equation', supports: 'H1', evidence_type: 'physical' },
    ],
    validation_evidence: [{ id: 'V1', description: 'Simpson check passed', result: 'pass' }],
  };
  fs.writeFileSync(path.join(diagDir, 'evidence.json'), JSON.stringify(evidence, null, 2) + '\n', 'utf-8');

  const confidence = {
    run_id: 'e2e_test',
    confidence_breakdown: {
      H1: {
        five_factor_breakdown: {
          statistical_strength: { score: 20, evidence_gaps: [] },
          physical_plausibility: { score: 22, evidence_gaps: [] },
          temporal_evidence: { score: 16, evidence_gaps: [] },
          absence_of_confounds: { score: 14, evidence_gaps: [] },
          symptom_completeness: { score: 8, evidence_gaps: [] },
        },
        overall_confidence: 80,
        adjustment_log: [],
        ceilings: {},
      },
    },
  };
  fs.writeFileSync(path.join(diagDir, 'confidence.json'), JSON.stringify(confidence, null, 2) + '\n', 'utf-8');

  const reasoningChain = {
    run_id: 'e2e_test',
    reasoning_chains: Array.from({ length: 8 }, (_, i) => ({
      step_id: i + 1,
      stage: ['observation', 'hypothesis', 'testing', 'exclusion', 'synthesis', 'validation', 'confidence', 'conclusion'][i],
      description: `Step ${i + 1}`,
      evidence_refs: [],
      uncertainty_summary: 'Low uncertainty',
    })),
  };
  fs.writeFileSync(path.join(diagDir, 'reasoning_chain.json'), JSON.stringify(reasoningChain, null, 2) + '\n', 'utf-8');

  ok('Mock diagnosis artifacts written');
} catch (e) { fail('Mock diagnosis', e.message); }

// Mock visual_analysis.json for E5
try {
  const va = {
    generated_at: new Date().toISOString(),
    observation_mode: 'metadata_fallback',
    time_alignment_applicable: true,
    analysis_provenance: { source_agent: 'skeleton', stage: 'fallback', skeleton_overwritten: false },
    chart_inventory: [],
    visual_observations: [],
    cross_parameter_temporal_alignment: {},
    synthesis: 'Metadata fallback mode — no VLM analysis available.',
  };
  fs.writeFileSync(path.join(runDir, '03_figures', 'visual_analysis.json'), JSON.stringify(va, null, 2) + '\n', 'utf-8');
  ok('Mock visual_analysis.json written');
} catch (e) { fail('Mock visual_analysis', e.message); }

// E5: physics_bridge_builder
console.log('\nE5: physics_bridge_builder.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-physics-bridge', 'scripts', 'physics_bridge_builder.py'),
    '--run-dir', runDir], 'physics_bridge_builder.py');
  const pb = path.join(runDir, 'enhancement', 'physics_bridge.json');
  if (!fs.existsSync(pb)) throw new Error('physics_bridge.json not created');
  ok('E5 physics_bridge_builder produced physics_bridge.json');
} catch (e) { fail('E5 physics_bridge_builder', e.message); }

// E6: knowledge_fusion
console.log('\nE6: knowledge_fusion.py');
try {
  run(PYTHON, [path.join(SKILLS, 'industrial-analysis-enhance-auto', 'scripts', 'knowledge_fusion.py'),
    '--run-dir', runDir, '--output', path.join(runDir, 'enhancement', 'enhanced_knowledge.json')], 'knowledge_fusion.py');
  const ek = path.join(runDir, 'enhancement', 'enhanced_knowledge.json');
  if (!fs.existsSync(ek)) throw new Error('enhanced_knowledge.json not created');
  const kb = JSON.parse(fs.readFileSync(ek, 'utf-8'));
  if (!kb.causal_pathways) throw new Error('causal_pathways missing');
  if (!kb.control_levers) throw new Error('control_levers missing');
  if (!kb.parameter_centrality) throw new Error('parameter_centrality missing');
  if (!kb.physical_context) throw new Error('physical_context missing');
  ok(`E6 knowledge_fusion produced enhanced_knowledge.json (${kb.causal_pathways.length} pathways, ${kb.control_levers.length} levers)`);
} catch (e) { fail('E6 knowledge_fusion', e.message); }

// E7a: markdown_publisher
console.log('\nE7a: markdown_publisher.py');
try {
  const tmpl = path.join(SKILLS, 'industrial-analysis-enhance-auto', 'templates', 'enhanced_analysis.md.tmpl');
  run(PYTHON, [path.join(SKILLS, 'industrial-analysis-enhance-auto', 'scripts', 'markdown_publisher.py'),
    '--knowledge', path.join(runDir, 'enhancement', 'enhanced_knowledge.json'),
    '--template', tmpl, '--output', path.join(runDir, 'enhancement', 'enhanced_analysis.md')], 'markdown_publisher.py');
  const md = path.join(runDir, 'enhancement', 'enhanced_analysis.md');
  if (!fs.existsSync(md)) throw new Error('enhanced_analysis.md not created');
  const mdContent = fs.readFileSync(md, 'utf-8');
  if (!mdContent.includes('AI 可操作摘要')) throw new Error('AI summary section missing');
  if (!mdContent.includes('控制杠杆')) throw new Error('Control levers section missing');
  if (!mdContent.includes('因果路径')) throw new Error('Causal pathways section missing');
  ok(`E7a markdown_publisher produced enhanced_analysis.md (${mdContent.length} bytes, all new sections present)`);
} catch (e) { fail('E7a markdown_publisher', e.message); }

// ── Summary ──
console.log('\n' + '='.repeat(60));
console.log('E2E PIPELINE TEST SUMMARY');
console.log('='.repeat(60));
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
if (failed > 0) {
  console.log('\nFailures:');
  for (const f of failures) console.log(`  ❌ ${f.name}: ${f.err}`);
}
console.log('='.repeat(60));
process.exit(failed > 0 ? 1 : 0);
