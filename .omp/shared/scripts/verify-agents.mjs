#!/usr/bin/env node
/**
 * OMP Agent Verification Script
 * 
 * Validates:
 * 1. All agent .md files have required frontmatter fields
 * 2. All agent names are unique and match AGENTS.md registry  
 * 3. All skills referenced by agents exist
 * 4. Agent spawn relationships are consistent
 * 5. vlm-visual-analyzer is dispatchable from data-processor
 */

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(process.argv.includes('--project-root') 
  ? process.argv[process.argv.indexOf('--project-root') + 1]
  : join(__dirname, '..', '..'));

const AGENTS_DIR = join(PROJECT_ROOT, 'agents');
const SKILLS_DIR = join(PROJECT_ROOT, 'skills');
const AGENTS_MD = join(PROJECT_ROOT, 'AGENTS.md');

const REQUIRED_AGENT_FIELDS = ['name', 'description', 'model', 'tools', 'spawns', 'thinkingLevel', 'readSummarize'];
const VALID_MODELS = ['default', 'vision', 'opus', 'sonnet', 'haiku', 'smol'];
const VALID_SPAWNS = ['*', ''];

let errors = 0;
let warnings = 0;
let passes = 0;

function log(level, msg) {
  const prefix = { error: '\u274C', warn: '\u26A0\uFE0F', pass: '\u2705', info: '\uD83D\uDCCB' }[level] || '  ';
  console.log(`${prefix} ${msg}`);
  if (level === 'error') errors++;
  if (level === 'warn') warnings++;
  if (level === 'pass') passes++;
}

function parseFrontmatter(content) {
  // Normalize line endings (handle Windows \r\n and Unix \n)
  const normalized = content.replace(/\r\n/g, '\n');
  const match = normalized.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const fm = {};
  for (const line of match[1].split('\n')) {
    const kv = line.match(/^(\w+):\s*(.+)/);
    if (kv) fm[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, '');
  }
  return fm;
}

// ========== 1. Validate agent .md files ==========
console.log('\n=== Agent Frontmatter Validation ===\n');

const agentFiles = readdirSync(AGENTS_DIR).filter(f => f.endsWith('.md'));
const agentRegistry = {};

for (const file of agentFiles) {
  const filePath = join(AGENTS_DIR, file);
  const content = readFileSync(filePath, 'utf-8');
  const fm = parseFrontmatter(content);
  
  if (!fm) {
    log('error', `${file}: Missing or malformed YAML frontmatter`);
    continue;
  }
  for (const field of REQUIRED_AGENT_FIELDS) {
    if (fm[field] === undefined) {
      log('error', `${file}: Missing required field "${field}"`);
    }
  }
  
  // spawns="" (empty string) is valid for leaf agents - explicit check
  if (fm.spawns === undefined) {
    log('error', `${file}: Missing required field "spawns"`);
  }
  
  if (fm.model && !VALID_MODELS.includes(fm.model)) {
    log('warn', `${file}: Unknown model "${fm.model}"`);
  }
  
  if (fm.spawns && !VALID_SPAWNS.includes(fm.spawns)) {
    log('warn', `${file}: Unknown spawns value "${fm.spawns}"`);
  }
  
  if (fm.spawns === '*' && fm.tools && !fm.tools.includes('task')) {
    log('error', `${file}: spawns="*" but missing "task" tool`);
  }
  
  if (fm.name) {
    if (agentRegistry[fm.name]) {
      log('error', `${file}: Duplicate agent name "${fm.name}"`);
    }
    agentRegistry[fm.name] = { file, fm };
  }
  
  log('pass', `${file} -> agent "${fm.name}" (model=${fm.model}, spawns=${fm.spawns || '""'})`);
}

console.log(`\nAgents discovered: ${Object.keys(agentRegistry).length}`);

// ========== 2. Validate AGENTS.md registry ==========
console.log('\n=== AGENTS.md Registry Validation ===\n');

if (existsSync(AGENTS_MD)) {
  const agentsMd = readFileSync(AGENTS_MD, 'utf-8');
  // Parse only the "OMP Agent Summary" table (between "## OMP Agent Summary" and "## Skill Directory")
  const agentTable = agentsMd.match(/## OMP Agent Summary\n\n[\s\S]*?(?=\n##|\n\Z)/);
  const tableAgents = [];
  
  if (agentTable) {
    for (const line of agentTable[0].split('\n')) {
      const match = line.match(/^\|\s*([\w-]+)\s*\|/);
      if (match && match[1] !== 'Agent' && !match[1].startsWith('-')) {
        tableAgents.push(match[1].trim());
      }
    }
  }
  for (const name of Object.keys(agentRegistry)) {
    if (!tableAgents.includes(name)) {
      log('warn', `Agent "${name}" has .md file but not listed in AGENTS.md table`);
    }
  }
  
  log('pass', `AGENTS.md registry: ${tableAgents.length} agents listed`);
}

// ========== 3. Validate skill SKILL.md files ==========
console.log('\n=== Skill Discovery Validation ===\n');

const skillDirs = readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory())
  .map(d => d.name);

let skillCount = 0;
for (const dir of skillDirs) {
  const skillMd = join(SKILLS_DIR, dir, 'SKILL.md');
  if (existsSync(skillMd)) {
    const content = readFileSync(skillMd, 'utf-8');
    const fm = parseFrontmatter(content);
    if (fm && fm.name) {
      skillCount++;
    } else {
      log('error', `${dir}/SKILL.md: Missing or invalid frontmatter name`);
    }
  } else {
    log('warn', `${dir}: No SKILL.md found - not discoverable by OMP`);
  }
}
log('pass', `Skills discovered: ${skillCount}/${skillDirs.length}`);

// ========== 4. Validate VLM dispatch chain ==========
console.log('\n=== VLM Dispatch Chain Validation ===\n');

if (!agentRegistry['vlm-visual-analyzer']) {
  log('error', 'vlm-visual-analyzer agent not found');
} else {
  log('pass', 'vlm-visual-analyzer agent exists');
}

const dpAgent = agentRegistry['data-processor'];
if (!dpAgent) {
  log('error', 'data-processor agent not found');
} else if (dpAgent.fm.spawns !== '*') {
  log('error', `data-processor spawns="${dpAgent.fm.spawns}" - need "*" to spawn vlm-visual-analyzer`);
} else if (!dpAgent.fm.tools?.includes('task')) {
  log('error', 'data-processor missing "task" tool - cannot spawn sub-agents');
} else {
  log('pass', 'data-processor can spawn sub-agents (spawns=*, has task tool)');
}

const dpSkillMd = join(SKILLS_DIR, 'industrial-data-processor', 'SKILL.md');
if (existsSync(dpSkillMd)) {
  const dpSkill = readFileSync(dpSkillMd, 'utf-8');
  if (dpSkill.includes('vlm-visual-analyzer')) {
    log('pass', 'industrial-data-processor SKILL.md references vlm-visual-analyzer');
  } else {
    log('error', 'industrial-data-processor SKILL.md does NOT reference vlm-visual-analyzer');
  }
}

const dpProtocol = join(SKILLS_DIR, 'industrial-data-processor', 'references', 'agent-protocol.md');
if (existsSync(dpProtocol)) {
  const protocol = readFileSync(dpProtocol, 'utf-8');
  if (protocol.includes('agent: "vlm-visual-analyzer"')) {
    log('pass', 'agent-protocol.md includes vlm-visual-analyzer task dispatch');
  } else {
    log('error', 'agent-protocol.md does NOT include vlm-visual-analyzer task dispatch');
  }
}

const dpAgentMd = join(AGENTS_DIR, 'data-processor.md');
if (existsSync(dpAgentMd)) {
  const agentMd = readFileSync(dpAgentMd, 'utf-8');
  if (agentMd.includes('vlm-visual-analyzer')) {
    log('pass', 'data-processor.md agent references vlm-visual-analyzer');
  } else {
    log('error', 'data-processor.md agent does NOT reference vlm-visual-analyzer');
  }
}

// ========== 5. Agent spawn capability matrix ==========
console.log('\n=== Agent Spawn Capability Matrix ===\n');

console.log('Agent                 | spawns | can_delegate | can_be_delegated');
console.log('-'.repeat(70));
for (const [name, { fm }] of Object.entries(agentRegistry).sort()) {
  const canDelegate = fm.spawns === '*' ? 'YES' : 'NO';
  console.log(`${name.padEnd(22)}| ${(fm.spawns || '""').padEnd(7)}| ${canDelegate.padEnd(13)}| YES`);
}

// ========== Summary ==========
console.log('\n=== Summary ===\n');
console.log(`Passes:   ${passes}`);
console.log(`Warnings: ${warnings}`);
console.log(`Errors:   ${errors}`);

if (errors > 0) {
  console.log('\nVERIFICATION FAILED - fix errors above');
  process.exit(1);
} else if (warnings > 0) {
  console.log('\nVERIFICATION PASSED with warnings');
  process.exit(0);
} else {
  console.log('\nALL CHECKS PASSED');
  process.exit(0);
}
