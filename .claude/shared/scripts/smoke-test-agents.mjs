#!/usr/bin/env node
/**
 * OMP Agent Spawn Smoke Test
 * 
 * Verifies that:
 * 1. All agents have .md files with valid frontmatter
 * 2. There are exactly 9 pipeline agents + their spawn relationships are correct
 * 3. context-builder and data-processor can delegate (spawns=*, has task tool)
 * 4. vlm-visual-analyzer is dispatchable from data-processor
 * 5. Skills and agents form a complete pipeline coverage
 * 
 * This is the gate test — run before any pipeline execution.
 */

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(join(__dirname, '..', '..', '..'));  // always project root from any shared/scripts/ location
const SHARED_DIR = join(PROJECT_ROOT, '.claude', 'shared');
const SKILLS_DIR = join(PROJECT_ROOT, '.claude', 'skills');
const AGENTS_DIR = join(PROJECT_ROOT, '.omp', 'agents');

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

const EXPECTED_AGENTS = 9;
const EXPECTED_SKILLS = 12;

console.log('=== OMP Agent Spawn Smoke Test ===\n');

// 1. Agent count
const agentFiles = readdirSync(AGENTS_DIR).filter(f => f.endsWith('.md'));
const agents = {};
for (const f of agentFiles) {
  const fm = parseFM(readFileSync(join(AGENTS_DIR, f), 'utf-8'));
  if (fm?.name) agents[fm.name] = { file: f, ...fm };
}

console.log(`1. Agent count: ${Object.keys(agents).length} (expected ${EXPECTED_AGENTS})`);
if (Object.keys(agents).length !== EXPECTED_AGENTS) {
  console.log('   FAIL: Wrong agent count');
  process.exit(1);
}
console.log('   PASS');

// 2. Required agents all present
const required = [
  'context-builder', 'data-processor', 'vlm-visual-analyzer',
  'diagnostician', 'judge', 'report-reviewer',
  'reporter', 'html-visualizer', 'html-reviewer'
];
console.log(`\n2. Required agents:`);
let allPresent = true;
for (const name of required) {
  const ok = !!agents[name];
  console.log(`   ${ok ? 'PASS' : 'FAIL'}: ${name}`);
  if (!ok) allPresent = false;
}
if (!allPresent) process.exit(1);

// 3. Spawn hierarchy
console.log('\n3. Spawn hierarchy:');
const spawners = ['context-builder', 'data-processor'];
for (const name of spawners) {
  const a = agents[name];
  const canSpawn = a.spawns === '*' && a.tools?.includes('task');
  console.log(`   ${canSpawn ? 'PASS' : 'FAIL'}: ${name} spawns=${a.spawns}, tools=${a.tools} -> can_delegate=${canSpawn}`);
  if (!canSpawn) process.exit(1);
}

// Leaf agents
const leafAgents = required.filter(n => !spawners.includes(n));
for (const name of leafAgents) {
  const a = agents[name];
  const isLeaf = a.spawns === '';
  console.log(`   ${isLeaf ? 'PASS' : 'FAIL'}: ${name} spawns="${a.spawns}" -> leaf=${isLeaf}`);
  if (!isLeaf) process.exit(1);
}

// 4. VLM dispatch chain
console.log('\n4. VLM dispatch chain:');
const vlm = agents['vlm-visual-analyzer'];
const dp = agents['data-processor'];
const vlmOk = vlm && vlm.model === 'vision' && dp && dp.tools?.includes('task');
console.log(`   ${vlmOk ? 'PASS' : 'FAIL'}: vlm-visual-analyzer (model=vision), data-processor (has task)`);
if (!vlmOk) process.exit(1);

// Check three files all reference VLM dispatch
const dpSkill = readFileSync(join(SKILLS_DIR, 'industrial-data-processor', 'SKILL.md'), 'utf-8');
const dpProtocol = readFileSync(join(SKILLS_DIR, 'industrial-data-processor', 'references', 'agent-protocol.md'), 'utf-8');
const dpAgentMd = readFileSync(join(AGENTS_DIR, 'data-processor.md'), 'utf-8');

const checks = [
  ['industrial-data-processor/SKILL.md', dpSkill],
  ['agent-protocol.md', dpProtocol],
  ['data-processor.md', dpAgentMd]
];
for (const [name, content] of checks) {
  const has = content.includes('vlm-visual-analyzer');
  console.log(`   ${has ? 'PASS' : 'FAIL'}: ${name} references vlm-visual-analyzer`);
  if (!has) process.exit(1);
}

// 5. Skill coverage
console.log('\n5. Skill coverage:');
const skillDirs = readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory()).map(d => d.name);
let skillCount = 0;
for (const dir of skillDirs) {
  if (existsSync(join(SKILLS_DIR, dir, 'SKILL.md'))) skillCount++;
}
const skillOk = skillCount === EXPECTED_SKILLS;
console.log(`   ${skillOk ? 'PASS' : 'FAIL'}: ${skillCount}/${EXPECTED_SKILLS} skills discoverable`);
if (!skillOk) process.exit(1);

// 6. Model assignments
console.log('\n6. Model assignments:');
for (const [name, a] of Object.entries(agents).sort()) {
  const expected = name === 'vlm-visual-analyzer' ? 'vision' : 'default';
  const ok = a.model === expected;
  console.log(`   ${ok ? 'PASS' : 'FAIL'}: ${name} model=${a.model} (expected ${expected})`);
  if (!ok) process.exit(1);
}

console.log('\n=== ALL SMOKE TESTS PASSED ===');
console.log(`${EXPECTED_AGENTS} agents, ${EXPECTED_SKILLS} skills, spawn hierarchy verified, VLM dispatch chain complete.`);
process.exit(0);
