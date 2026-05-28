#!/usr/bin/env node
// validate.mjs — Runtime JSON Schema validation (zero-dependency)
// Validates JSON output files against draft-07 schemas.
// Checks: required fields, types, min/max, enum, pattern.
// Falls back to basic structural checks for all constraints.
//
// Usage: node validate.mjs <schema.json> <data.json>
//   Returns exit code 0 if valid, 1 if invalid.
//   Prints JSON validation report to stdout.

import fs from 'fs';

// ═══════════════════════════════════════════════
//  VALIDATION ENGINE
// ═══════════════════════════════════════════════

const ERRORS = [];
let WARNINGS = [];

function addError(path, msg) {
  ERRORS.push({ path, message: msg, severity: 'error' });
}

function addWarning(path, msg) {
  WARNINGS.push({ path, message: msg, severity: 'warning' });
}

function validateValue(value, schema, path = '$') {
  if (schema === null || schema === undefined) return true;
  if (schema.const !== undefined) {
    if (value !== schema.const) {
      addError(path, `Expected constant ${JSON.stringify(schema.const)}, got ${JSON.stringify(value)}`);
    }
    return;
  }

  // Type checks — supports both single type string and array of types (JSON Schema draft-07)
  if (schema.type) {
    const typeMap = {
      string: 'string',
      integer: 'number',
      number: 'number',
      boolean: 'boolean',
      array: 'array',
      object: 'object'
    };
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const actual = typeof value;
    const isArray = Array.isArray(value);

    let matched = false;
    for (const t of types) {
      if (t === 'null' && value === null) { matched = true; break; }
      const expected = typeMap[t];
      if (expected === undefined) continue;
      if (t === 'integer' && actual === 'number') {
        if (Number.isInteger(value)) { matched = true; break; }
      } else if (expected === 'array') {
        if (isArray) { matched = true; break; }
      } else if (expected === 'object') {
        if (actual === 'object' && !isArray && value !== null) { matched = true; break; }
      } else if (actual === expected) {
        matched = true; break;
      }
    }
    if (!matched) {
      addError(path, `Value type not in [${types.join(', ')}], got ${value === null ? 'null' : actual}`);
    }
  }

  if (value === null || value === undefined) return;

  // Nullable
  if (schema.nullable && value === null) return;

  // Enum
  if (schema.enum && !schema.enum.includes(value)) {
    addError(path, `Value ${JSON.stringify(value)} not in enum [${schema.enum.join(', ')}]`);
  }

  // Number constraints
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) {
      addError(path, `Value ${value} < minimum ${schema.minimum}`);
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      addError(path, `Value ${value} > maximum ${schema.maximum}`);
    }
  }

  // String constraints
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      addError(path, `String length ${value.length} < minLength ${schema.minLength}`);
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      addError(path, `String length ${value.length} > maxLength ${schema.maxLength}`);
    }
    if (schema.pattern) {
      const re = new RegExp(schema.pattern);
      if (!re.test(value)) {
        addError(path, `String ${JSON.stringify(value)} does not match pattern ${schema.pattern}`);
      }
    }
    if (schema.format === 'date-time') {
      const d = new Date(value);
      if (isNaN(d.getTime())) {
        addError(path, `Invalid date-time format: ${value}`);
      }
    }
    if (schema.format === 'date') {
      const d = new Date(value);
      if (isNaN(d.getTime())) {
        addError(path, `Invalid date format: ${value}`);
      }
    }
  }

  // Array
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      addError(path, `Array length ${value.length} < minItems ${schema.minItems}`);
    }
    if (schema.maxItems !== undefined && value.length > schema.maxItems) {
      addError(path, `Array length ${value.length} > maxItems ${schema.maxItems}`);
    }
    if (schema.items) {
      for (let i = 0; i < value.length; i++) {
        validateValue(value[i], schema.items, `${path}[${i}]`);
      }
    }
    if (schema.uniqueItems && value.length !== new Set(value).size) {
      addError(path, 'Array items are not unique');
    }
  }

  // Object
  if (typeof value === 'object' && !Array.isArray(value) && value !== null) {
    // Required fields
    if (schema.required) {
      for (const reqKey of schema.required) {
        if (!(reqKey in value)) {
          addError(path, `Missing required field: ${reqKey}`);
        }
      }
    }

    // Properties
    if (schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        if (key in value) {
          validateValue(value[key], propSchema, `${path}.${key}`);
        }
      }
    }

    // Additional properties
    if (schema.additionalProperties === false) {
      const allowed = new Set(Object.keys(schema.properties || {}));
      for (const key of Object.keys(value)) {
        if (!allowed.has(key) && !key.startsWith('_')) {
          addWarning(path, `Unexpected property: ${key}`);
        }
      }
    }

    // Pattern properties
    if (schema.patternProperties) {
      for (const [pattern, propSchema] of Object.entries(schema.patternProperties)) {
        const re = new RegExp(pattern);
        for (const [key, val] of Object.entries(value)) {
          if (re.test(key)) {
            validateValue(val, propSchema, `${path}.${key}`);
          }
        }
      }
    }

    // additionalProperties schema for open-ended objects
    if (schema.additionalProperties && typeof schema.additionalProperties === 'object') {
      const defined = new Set(Object.keys(schema.properties || {}));
      for (const [key, val] of Object.entries(value)) {
        if (!defined.has(key)) {
          validateValue(val, schema.additionalProperties, `${path}.${key}`);
        }
      }
    }

    // Property count
    if (schema.minProperties !== undefined && Object.keys(value).length < schema.minProperties) {
      addError(path, `Property count ${Object.keys(value).length} < minProperties ${schema.minProperties}`);
    }
    if (schema.maxProperties !== undefined && Object.keys(value).length > schema.maxProperties) {
      addError(path, `Property count ${Object.keys(value).length} > maxProperties ${schema.maxProperties}`);
    }
  }
}

// ═══════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════

const args = process.argv.slice(2);
const schemaPath = args[0];
const dataPath = args[1];

if (!schemaPath || !dataPath) {
  console.error('Usage: node validate.mjs <schema.json> <data.json>');
  process.exit(1);
}

const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

validateValue(data, schema);

const report = {
  schema: schemaPath,
  data: dataPath,
  valid: ERRORS.length === 0,
  timestamp: new Date().toISOString(),
  errors: ERRORS,
  warnings: WARNINGS,
  summary: {
    errors: ERRORS.length,
    warnings: WARNINGS.length
  }
};

console.log(JSON.stringify(report, null, 2));
process.exit(report.valid ? 0 : 1);
