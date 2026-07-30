#!/usr/bin/env node
// validate-schemas.mjs — Schema file validator
// JSON.parse + shape check + optional ajv compile for all schemas/*.json
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');

// ---- Recursive glob for schemas/*.json under .claude/skills/ and .omp/skills/ ----
function globSchemas(baseDir) {
  const results = [];
  const skillsDir = path.join(REPO_ROOT, baseDir, 'skills');
  if (!fs.existsSync(skillsDir)) return results;
  for (const skill of fs.readdirSync(skillsDir)) {
    const schemasDir = path.join(skillsDir, skill, 'schemas');
    if (!fs.existsSync(schemasDir)) continue;
    for (const f of fs.readdirSync(schemasDir)) {
      if (f.endsWith('.json')) {
        results.push({
          file: path.join(baseDir, 'skills', skill, 'schemas', f).replace(/\\/g, '/'),
          skill,
          fullPath: path.join(schemasDir, f),
        });
      }
    }
  }
  return results;
}

const schemas = [
  ...globSchemas('.claude'),
  ...globSchemas('.omp'),
];

// ---- Check ajv availability ----
let ajv = null;
try {
  const AjvModule = await import('ajv');
  const Ajv = AjvModule.default || AjvModule;
  ajv = new Ajv({ schemaId: 'auto', allErrors: true });
} catch (e) {
  // ajv not available — skip compile step
}

// ---- Validate a single schema file ----
function validateSchema(entry) {
  const result = {
    file: entry.file,
    skill: entry.skill,
    parse_ok: false,
    shape_ok: false,
    compile: 'skipped',
    error: null,
    status: 'FAIL',
  };

  let raw;
  try {
    raw = fs.readFileSync(entry.fullPath, 'utf-8');
  } catch (e) {
    result.error = `READ_ERROR: ${e.message}`;
    return result;
  }

  // (a) JSON.parse
  let parsed;
  try {
    parsed = JSON.parse(raw);
    result.parse_ok = true;
  } catch (e) {
    result.error = `JSON_PARSE: ${e.message}`;
    return result;
  }

  // (b) Shape check: must have $schema or type+properties
  const hasDollarSchema = parsed && typeof parsed === 'object' && typeof parsed.$schema === 'string';
  const hasTypeProps = parsed && typeof parsed === 'object' && (parsed.type || parsed.properties);
  if (hasDollarSchema || hasTypeProps) {
    result.shape_ok = true;
  } else {
    result.error = 'SHAPE: missing $schema and missing type/properties';
    return result;
  }

  // Extra: if $schema present, verify it references draft-07
  if (parsed.$schema) {
    if (!parsed.$schema.includes('draft-07') && !parsed.$schema.includes('draft/07')) {
      result.error = `SHAPE: $schema is "${parsed.$schema}" (not draft-07)`;
      result.shape_ok = false;
      return result;
    }
  }

  // (c) ajv compile
  if (ajv) {
    try {
      ajv.compile(parsed);
      result.compile = 'ok';
    } catch (e) {
      result.compile = 'error';
      result.error = `AJV_COMPILE: ${e.message}`;
      result.status = 'FAIL';
      return result;
    }
  }

  // Determine status
  if (result.parse_ok && result.shape_ok && result.compile !== 'error') {
    result.status = 'PASS';
  } else if (result.parse_ok && result.shape_ok && result.compile === 'skipped') {
    result.status = 'WARN'; // shape ok but couldn't compile (ajv not available)
  }

  return result;
}

// ---- Cross-check: referenced schemas exist on disk ----
function crossCheckReferences() {
  // Collect all schema basenames on disk
  const onDisk = new Set();
  for (const s of schemas) {
    onDisk.add(path.basename(s.file));
  }

  // Collect referenced schema names from all .md and .mjs files
  const referenced = new Set();
  const refSources = [];

  function scanDir(dir) {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { recursive: true })) {
      const full = path.join(dir, entry);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) continue;
      if (!entry.endsWith('.md') && !entry.endsWith('.mjs')) continue;
      try {
        const content = fs.readFileSync(full, 'utf-8');
        const matches = content.matchAll(/(?:schemas\/|_schema\.json["'\s])([\w-]+_schema\.json)/g);
        for (const m of matches) {
          referenced.add(m[1]);
          if (!onDisk.has(m[1])) {
            refSources.push({ ref: m[1], source: path.relative(REPO_ROOT, full).replace(/\\/g, '/') });
          }
        }
      } catch (e) { /* skip unreadable */ }
    }
  }

  scanDir(path.join(REPO_ROOT, '.claude'));
  scanDir(path.join(REPO_ROOT, '.omp'));

  return { onDisk: onDisk.size, referenced: referenced.size, missing: refSources };
}

// ---- Main ----
console.log(`\nSchema Validation Report — ${schemas.length} schema files found\n`);

const results = schemas.map(validateSchema);

let pass = 0, warn = 0, fail = 0;
for (const r of results) {
  if (r.status === 'PASS') pass++;
  else if (r.status === 'WARN') warn++;
  else fail++;
  if (r.status !== 'PASS') {
    console.log(`  ${r.status}  ${r.file}  ${r.error || '(shape ok, ajv skipped)'}`);
  }
}

// Cross-check
const refCheck = crossCheckReferences();

// Summary
console.log(`\n--- Summary ---`);
console.log(`  TOTAL:     ${results.length}`);
console.log(`  PASS:      ${pass}`);
console.log(`  WARN:      ${warn}`);
console.log(`  FAIL:      ${fail}`);
console.log(`  ajv:       ${ajv ? 'available' : 'not available'}`);
console.log(`  Disk refs: ${refCheck.onDisk}`);
console.log(`  Code refs: ${refCheck.referenced}`);
if (refCheck.missing.length > 0) {
  console.log(`\n  MISSING REFERENCED SCHEMAS:`);
  for (const m of refCheck.missing) {
    console.log(`    ${m.ref}  ← referenced in ${m.source}`);
  }
}

// Write report
const report = {
  agent: 'SchemaValidator',
  summary: {
    pass,
    warn,
    fail,
    total: results.length,
    ajv_available: !!ajv,
    cross_check: {
      schemas_on_disk: refCheck.onDisk,
      referenced_in_code: refCheck.referenced,
      missing_references: refCheck.missing,
    },
  },
  schemas: results,
};

const outPath = path.join(__dirname, 'schema-validator-report.json');
fs.writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(`\nReport written to: workspace/skill-test/schema-validator-report.json`);