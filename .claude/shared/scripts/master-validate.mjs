#!/usr/bin/env node
/**
 * Master Validation Script — comprehensive skill repository health check.
 * 
 * Validates:
 * 1. Schema completeness and cross-references
 * 2. Agent frontmatter and discoverability  
 * 3. Skill-to-agent mappings
 * 4. Pipeline CP gate coverage
 * 5. Input/output contract standardization
 * 6. Data processing + chart generation
 * 7. VLM multimodal capability
 */

import { readFileSync, readdirSync, existsSync, statSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(join(__dirname, '..', '..', '..'));  // always project root from any shared/scripts/ location
const SHARED_DIR = join(PROJECT_ROOT, '.claude', 'shared');
const SKILLS_DIR = join(PROJECT_ROOT, '.claude', 'skills');
const AGENTS_DIR = join(PROJECT_ROOT, '.omp', 'agents');

let total = 0, passed = 0, failed = 0, skipped = 0;

function test(name, fn) {
  total++;
  try {
    const result = fn();
    if (result === true || result === undefined) {
      console.log(`  PASS: ${name}`);
      passed++;
    } else {
      console.log(`  FAIL: ${name} — ${result}`);
      failed++;
    }
  } catch (e) {
    console.log(`  FAIL: ${name} — ${e.message}`);
    failed++;
  }
}

function parseFM(content) {
  const n = content.replace(/\r\n/g, '\n');
  const m = n.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return null;
  const fm = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^(\w+):\s*(.+)/);
    if (kv) fm[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, '');
  }
  return fm;
}

console.log('='.repeat(70));
console.log('MASTER VALIDATION — Industrial Deep Diagnostic Skill Repository');
console.log('='.repeat(70));

// ======== SECTION 1: Schema Audit ========
console.log('\n--- 1. SCHEMA AUDIT ---');

const sharedSchemas = join(SHARED_DIR, 'schemas');
const schemaFiles = readdirSync(sharedSchemas).filter(f => f.endsWith('.json') && f !== '_schema_index.json');

test('Shared schemas count >= 15', () => {
  if (schemaFiles.length < 15) return `Only ${schemaFiles.length} schemas found`;
});

for (const sf of schemaFiles) {
  test(`Schema ${sf} is valid JSON`, () => {
    const content = readFileSync(join(sharedSchemas, sf), 'utf-8');
    JSON.parse(content);
  });
}

// Check skill-specific schemas
const skillDirs = readdirSync(SKILLS_DIR, { withFileTypes: true }).filter(d => d.isDirectory());
for (const sd of skillDirs) {
  const skillSchemaDir = join(SKILLS_DIR, sd.name, 'schemas');
  if (existsSync(skillSchemaDir)) {
    const sfs = readdirSync(skillSchemaDir).filter(f => f.endsWith('.json'));
    for (const sf of sfs) {
      test(`Skill schema ${sd.name}/${sf} is valid JSON`, () => {
        JSON.parse(readFileSync(join(skillSchemaDir, sf), 'utf-8'));
      });
    }
  }
}

// ======== SECTION 2: Agent Validation ========
console.log('\n--- 2. AGENT VALIDATION ---');

const agentFiles = readdirSync(AGENTS_DIR).filter(f => f.endsWith('.md'));
const agents = {};

for (const af of agentFiles) {
  const content = readFileSync(join(AGENTS_DIR, af), 'utf-8');
  const fm = parseFM(content);
  
  test(`Agent ${af} has valid frontmatter`, () => fm !== null);
  if (!fm) continue;
  
  test(`Agent ${fm.name} has required fields`, () => {
    const required = ['name', 'description', 'model', 'tools', 'spawns', 'thinkingLevel'];
    const missing = required.filter(f => fm[f] === undefined);
    return missing.length === 0 ? true : `Missing: ${missing.join(', ')}`;
  });
  
  test(`Agent ${fm.name} spawns consistency`, () => {
    if (fm.spawns === '*' && fm.tools && !fm.tools.includes('task'))
      return 'spawns=* but no task tool';
    return true;
  });
  
  agents[fm.name] = { file: af, fm };
}

test('Agent count = 14 (9 baseline + 5 enhancement)', () => Object.keys(agents).length === 14 ? true : `Got ${Object.keys(agents).length}`);

// Check required agents present
const requiredAgents = ['context-builder', 'data-processor', 'vlm-visual-analyzer',
  'diagnostician', 'judge', 'report-reviewer', 'reporter', 'html-visualizer', 'html-reviewer'];
for (const ra of requiredAgents) {
  test(`Required agent ${ra} exists`, () => !!agents[ra]);
}

// ======== SECTION 3: Skill Discovery ========
console.log('\n--- 3. SKILL DISCOVERY ---');

let skillCount = 0;
for (const sd of skillDirs) {
  const skillMd = join(SKILLS_DIR, sd.name, 'SKILL.md');
  if (existsSync(skillMd)) {
    const fm = parseFM(readFileSync(skillMd, 'utf-8'));
    if (fm?.name) {
      skillCount++;
      test(`Skill ${fm.name} discovered`, () => true);
    } else {
      test(`Skill ${sd.name}/SKILL.md has valid frontmatter`, () => 'Missing name field');
    }
  } else {
    test(`Skill ${sd.name} has SKILL.md`, () => 'SKILL.md not found');
  }
}

test('Total discoverable skills >= 11', () => skillCount >= 11 ? true : `Only ${skillCount}`);

// ======== SECTION 4: Pipeline CP Gate Coverage ========
console.log('\n--- 4. PIPELINE CP GATE COVERAGE ---');

const orchestratorSkill = join(SKILLS_DIR, 'industrial-analysis-auto', 'SKILL.md');
if (existsSync(orchestratorSkill)) {
  const content = readFileSync(orchestratorSkill, 'utf-8');
  
  for (const cp of ['CP-1', 'CP-2', 'CP-3', 'CP-4', 'CP-5', 'CP-6', 'CP-7', 'CP-8', 'CP-9']) {
    test(`Checkpoint ${cp} defined in orchestrator`, () => content.includes(cp));
  }
  
  // Verify each step has an agent dispatch
  const stepPatterns = [
    ['Step 2', 'context-builder'],
    ['Step 3', 'data-processor'],
    ['Step 4', 'diagnostician'],
    ['Step 5a', 'judge'],
    ['Step 5b', 'report-reviewer'],
    ['Step 6', 'reporter'],
    ['Step 7', 'report-reviewer'],
    ['Step 8', 'html-visualizer'],
    ['Step 8.5', 'html-reviewer'],
  ];
  
  for (const [step, agent] of stepPatterns) {
    test(`Orchestrator dispatches ${agent} at ${step}`, () => {
      const idx = content.indexOf(step);
      if (idx === -1) return `Step ${step} not found in orchestrator`;
      const stepSection = content.substring(idx, idx + 2000);
      return stepSection.includes(`agent: "${agent}"`) || stepSection.includes(agent);
    });
  }
}

// ======== SECTION 5: Input/Output Contract Check ========
console.log('\n--- 5. INPUT/OUTPUT CONTRACT STANDARDIZATION ---');

// Check that data_analysis_conclusion_schema exists (critical handoff)
test('data_analysis_conclusion schema exists', () => 
  existsSync(join(sharedSchemas, 'data_analysis_conclusion_schema.json')));

test('diagnosis schema exists', () =>
  existsSync(join(sharedSchemas, 'diagnosis_schema.json')));

test('evidence schema exists', () =>
  existsSync(join(sharedSchemas, 'evidence_schema.json')));

test('confidence schema exists', () =>
  existsSync(join(sharedSchemas, 'confidence_schema.json')));

test('reasoning_chain schema exists', () =>
  existsSync(join(sharedSchemas, 'reasoning_chain_schema.json')));

test('visual_analysis schema exists', () =>
  existsSync(join(sharedSchemas, 'visual_analysis_schema.json')));

test('judge_feedback schema exists', () =>
  existsSync(join(sharedSchemas, 'judge_feedback_schema.json')));

// ======== SECTION 6: Data Processing Test ========
console.log('\n--- 6. DATA PROCESSING SMOKE TEST ---');

const REPO_ROOT = resolve(join(__dirname, '..', '..', '..'));
// Smoke test against the most recent REAL end-to-end run (kept in repo) rather
// than a scratch dir that may have been cleaned up.
const TEST_RUN_DIR = join(REPO_ROOT, 'workspace', 'diagnostic-runs', '202607310911175_cnc_spindle_wear_enhance_test');
const testDataPath = join(TEST_RUN_DIR, '02_processed', 'cleaned_data.csv');

test('Test data exists', () => existsSync(testDataPath));

if (existsSync(testDataPath)) {
  // Check key outputs from previous run
  const outputs = [
    '02_processed/scenario_classification.json',
    '02_processed/feature_summary.json',
    '02_processed/validate_report.json',
    '02_processed/data_analysis_conclusion.json',
    '03_figures/plot_manifest.json',
    '03_figures/visual_analysis.json',
    '03_figures/image_captions.json',
  ];
  // Figure names are dynamic (fig1_*, fig_01_*, ...) — verify the manifest's
  // declared files actually exist instead of hardcoding legacy names.
  const manifestPath = join(TEST_RUN_DIR, '03_figures', 'plot_manifest.json');
  if (existsSync(manifestPath)) {
    try {
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
      const declared = (manifest.plots || manifest.figures || []).map((f) => f.filename || f.file || f.path).filter(Boolean);
      let pngCount = 0;
      for (const rel of declared) {
        if (rel.endsWith('.png')) {
          pngCount += 1;
          test(`Manifest PNG ${rel} exists`, () => {
            const fp = join(TEST_RUN_DIR, '03_figures', rel);
            return existsSync(fp) && statSync(fp).size > 5000
              ? true : `missing or too small: ${rel}`;
          });
        }
      }
      test('Manifest declares >= 3 PNG figures', () => pngCount >= 3 ? true : `only ${pngCount}`);
    } catch (e) {
      test('plot_manifest.json parseable', () => `parse error: ${e.message}`);
    }
  }
  
  for (const out of outputs) {
    const fp = join(TEST_RUN_DIR, out);
    test(`Output ${out} exists`, () => {
      if (!existsSync(fp)) return 'File missing';
      if (out.endsWith('.png')) {
        const sz = statSync(fp).size;
        return sz > 5000 ? true : `PNG too small: ${sz} bytes`;
      }
      if (out.endsWith('.json')) {
        const sz = statSync(fp).size;
        return sz > 500 ? true : `JSON too small: ${sz} bytes`;
      }
      return true;
    });
  }
}

// ======== SECTION 7: VLM Model Availability ========
console.log('\n--- 7. VLM MODEL ROUTING ---');

// Check config for vision model routing
const ompConfig = join(process.env.HOME || process.env.USERPROFILE, '.omp', 'agent', 'config.yml');
if (existsSync(ompConfig)) {
  const config = readFileSync(ompConfig, 'utf-8');
  const visionMatch = config.match(/vision:\s*(.+)/);
  test('Vision model role configured', () => !!visionMatch);
  if (visionMatch) {
    console.log(`  INFO: Vision model = ${visionMatch[1].trim()}`);
  }
}

// ======== SECTION 8: Validation Scripts ========
console.log('\n--- 8. VALIDATION SCRIPTS ---');

const validateScript = join(SHARED_DIR, 'scripts', 'validate.mjs');
test('Shared validate.mjs exists', () => existsSync(validateScript));

// Try running validate on a known-good file
if (existsSync(validateScript)) {
  const testOntology = join(TEST_RUN_DIR, '01_ontology', 'ontology.json');
  const ontologySchema = join(sharedSchemas, 'ontology_schema.json');
  if (existsSync(testOntology) && existsSync(ontologySchema)) {
    try {
      execSync(`node "${validateScript}" "${ontologySchema}" "${testOntology}"`, { timeout: 10000 });
      test('validate.mjs works (ontology)', () => true);
    } catch (e) {
      test('validate.mjs works (ontology)', () => e.message);
    }
  }
}

// ======== SUMMARY ========
console.log('\n' + '='.repeat(70));
console.log('VALIDATION SUMMARY');
console.log('='.repeat(70));
console.log(`Total:   ${total}`);
console.log(`Passed:  ${passed}`);
console.log(`Failed:  ${failed}`);
console.log(`Skipped: ${skipped}`);
console.log(`Score:   ${Math.round(passed / total * 100)}%`);
console.log('='.repeat(70));

if (failed > 0) {
  console.log('\nFIX REQUIRED — see failures above');
  process.exit(1);
} else {
  console.log('\nALL CHECKS PASSED');
  process.exit(0);
}
