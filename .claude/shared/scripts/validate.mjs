#!/usr/bin/env node
// validate.mjs — Runtime JSON Schema validation (zero-dependency, draft-07 subset)
//
// Supported keywords:
//   type (string|number|integer|array|object|boolean|null, or array of),
//   enum, const, minimum/maximum, exclusiveMinimum/Maximum,
//   minLength/maxLength, pattern, format (date-time|date|email|uri),
//   minItems/maxItems/uniqueItems, items (single schema),
//   required, properties, additionalProperties (bool|schema),
//   patternProperties, minProperties/maxProperties,
//   nullable,
//   —— draft-07 composition (additive, safe upgrade) ——
//   anyOf, oneOf, allOf, not,
//   if / then / else (conditional),
//   $ref (internal "#/definitions/..." and "#/$defs/..." resolution),
//   dependencies (property → required[] | schema),
//   contains / minContains / maxContains.
//
// Errors carry {path, message, severity}. Unknown keywords are ignored
// (forward-compatible). additionalProperties===false emits warnings, not errors,
// so extra fields never hard-block (domain adaptivity).
//
// Usage: node validate.mjs <schema.json> <data.json>
//   Exit 0 if valid, 1 if invalid. Prints JSON report to stdout.

import fs from 'fs';

const ERRORS = [];
let WARNINGS = [];

function addError(path, msg) {
  ERRORS.push({ path, message: msg, severity: 'error' });
}
function addWarning(path, msg) {
  WARNINGS.push({ path, message: msg, severity: 'warning' });
}

const TYPE_MAP = {
  string: 'string', integer: 'number', number: 'number',
  boolean: 'boolean', array: 'array', object: 'object', null: 'null'
};

function typeMatches(value, typeStr) {
  if (typeStr === 'null') return value === null;
  if (typeStr === 'integer') return typeof value === 'number' && Number.isInteger(value);
  if (typeStr === 'array') return Array.isArray(value);
  if (typeStr === 'object') return typeof value === 'object' && !Array.isArray(value) && value !== null;
  return typeof value === (TYPE_MAP[typeStr] || typeStr);
}

// Resolve a $ref ("#/definitions/x" or "#/$defs/x" or "#") against the root schema.
function resolveRef(ref, root) {
  if (ref === '#') return root;
  if (!ref.startsWith('#/')) return null;
  const parts = ref.slice(2).split('/');
  let node = root;
  for (const p of parts) {
    node = node?.[p];
    if (node === undefined) return null;
  }
  return node;
}

// validateValue with a root-context for $ref resolution.
function validateValue(value, schema, path, root) {
  if (schema === null || schema === undefined) return;

  // $ref — resolve and delegate (do not also apply sibling keywords, per draft-07 strictness)
  if (schema.$ref) {
    const target = resolveRef(schema.$ref, root);
    if (target === null) {
      addError(path, `Cannot resolve $ref: ${schema.$ref}`);
    } else {
      validateValue(value, target, path, root);
    }
    return;
  }

  if (schema.const !== undefined && value !== schema.const) {
    addError(path, `Expected constant ${JSON.stringify(schema.const)}, got ${JSON.stringify(value)}`);
  }

  // Composition: allOf / anyOf / oneOf / not
  if (schema.allOf) {
    for (let i = 0; i < schema.allOf.length; i++) {
      validateValue(value, schema.allOf[i], path, root);
    }
  }
  if (schema.anyOf) {
    let matched = false;
    const before = ERRORS.length;
    for (const sub of schema.anyOf) {
      const snapshot = ERRORS.length;
      validateValue(value, sub, path, root);
      if (ERRORS.length === snapshot) { matched = true; break; }
      // roll back this branch's errors — anyOf only needs one passing
      ERRORS.length = snapshot;
    }
    if (!matched) addError(path, 'Value does not satisfy any of the allowed shapes (anyOf)');
    else ERRORS.length = before; // discard any committed errors from non-matching exploration
  }
  if (schema.oneOf) {
    let passCount = 0;
    for (const sub of schema.oneOf) {
      const snapshot = ERRORS.length;
      validateValue(value, sub, path, root);
      if (ERRORS.length === snapshot) passCount++;
      ERRORS.length = snapshot;
    }
    if (passCount !== 1) addError(path, `Value must match exactly one shape (oneOf); matched ${passCount}`);
  }
  if (schema.not) {
    const snapshot = ERRORS.length;
    validateValue(value, schema.not, path, root);
    const violated = ERRORS.length > snapshot;
    ERRORS.length = snapshot;
    if (!violated) addError(path, 'Value matches the excluded shape (not)');
  }

  // Conditional: if / then / else
  if (schema.if) {
    const snapshot = ERRORS.length;
    validateValue(value, schema.if, path, root);
    const condMet = ERRORS.length === snapshot;
    ERRORS.length = snapshot;
    if (condMet && schema.then) validateValue(value, schema.then, path, root);
    if (!condMet && schema.else) validateValue(value, schema.else, path, root);
  }

  // type
  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const matched = types.some(t => typeMatches(value, t));
    if (!matched) {
      addError(path, `Value type not in [${types.join(', ')}], got ${value === null ? 'null' : (Array.isArray(value) ? 'array' : typeof value)}`);
    }
  }

  if (value === null || value === undefined) return;
  if (schema.nullable && value === null) return;

  // enum
  if (schema.enum && !schema.enum.includes(value)) {
    addError(path, `Value ${JSON.stringify(value)} not in enum [${schema.enum.join(', ')}]`);
  }

  // Number constraints
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) addError(path, `Value ${value} < minimum ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum) addError(path, `Value ${value} > maximum ${schema.maximum}`);
    if (schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) addError(path, `Value ${value} <= exclusiveMinimum ${schema.exclusiveMinimum}`);
    if (schema.exclusiveMaximum !== undefined && value >= schema.exclusiveMaximum) addError(path, `Value ${value} >= exclusiveMaximum ${schema.exclusiveMaximum}`);
    if (schema.multipleOf !== undefined) {
      const q = value / schema.multipleOf;
      if (Math.abs(q - Math.round(q)) > 1e-9) addError(path, `Value ${value} not a multiple of ${schema.multipleOf}`);
    }
  }

  // String constraints
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) addError(path, `String length ${value.length} < minLength ${schema.minLength}`);
    if (schema.maxLength !== undefined && value.length > schema.maxLength) addError(path, `String length ${value.length} > maxLength ${schema.maxLength}`);
    if (schema.pattern) {
      try {
        if (!new RegExp(schema.pattern).test(value)) addError(path, `String ${JSON.stringify(value)} does not match pattern ${schema.pattern}`);
      } catch (e) { addWarning(path, `Invalid pattern in schema: ${schema.pattern}`); }
    }
    if (schema.format) {
      const ok = validateFormat(value, schema.format);
      if (ok === false) addError(path, `Invalid ${schema.format} format: ${value}`);
    }
  }

  // Array
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) addError(path, `Array length ${value.length} < minItems ${schema.minItems}`);
    if (schema.maxItems !== undefined && value.length > schema.maxItems) addError(path, `Array length ${value.length} > maxItems ${schema.maxItems}`);
    if (schema.items) {
      for (let i = 0; i < value.length; i++) validateValue(value[i], schema.items, `${path}[${i}]`, root);
    }
    if (schema.uniqueItems && value.length !== new Set(value.map(v => typeof v === 'object' ? JSON.stringify(v) : v)).size) {
      addError(path, 'Array items are not unique');
    }
    if (schema.contains) {
      let containsCount = 0;
      for (let i = 0; i < value.length; i++) {
        const snap = ERRORS.length;
        validateValue(value[i], schema.contains, `${path}[${i}]`, root);
        const matched = ERRORS.length === snap;
        ERRORS.length = snap;
        if (matched) containsCount++;
      }
      const minC = schema.minContains !== undefined ? schema.minContains : 1;
      const maxC = schema.maxContains;
      if (containsCount < minC) addError(path, `Array does not contain at least ${minC} matching item(s) (contains)`);
      if (maxC !== undefined && containsCount > maxC) addError(path, `Array contains ${containsCount} matching items > maxContains ${maxC}`);
    }
  }

  // Object
  if (typeof value === 'object' && !Array.isArray(value) && value !== null) {
    if (schema.required) {
      for (const reqKey of schema.required) {
        if (!(reqKey in value)) addError(path, `Missing required field: ${reqKey}`);
      }
    }
    if (schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        if (key in value) validateValue(value[key], propSchema, `${path}.${key}`, root);
      }
    }
    if (schema.additionalProperties === false) {
      const allowed = new Set([...Object.keys(schema.properties || {}), ...Object.keys(schema.patternProperties || {})]);
      for (const key of Object.keys(value)) {
        if (!allowed.has(key) && !key.startsWith('_')) addWarning(path, `Unexpected property: ${key}`);
      }
    }
    if (schema.patternProperties) {
      for (const [pattern, propSchema] of Object.entries(schema.patternProperties)) {
        try {
          const re = new RegExp(pattern);
          for (const [key, val] of Object.entries(value)) {
            if (re.test(key)) validateValue(val, propSchema, `${path}.${key}`, root);
          }
        } catch (e) { addWarning(path, `Invalid patternProperties pattern: ${pattern}`); }
      }
    }
    if (schema.additionalProperties && typeof schema.additionalProperties === 'object') {
      const defined = new Set([...Object.keys(schema.properties || {}), ...Object.keys(schema.patternProperties || {})]);
      for (const [key, val] of Object.entries(value)) {
        if (!defined.has(key)) validateValue(val, schema.additionalProperties, `${path}.${key}`, root);
      }
    }
    if (schema.minProperties !== undefined && Object.keys(value).length < schema.minProperties) {
      addError(path, `Property count ${Object.keys(value).length} < minProperties ${schema.minProperties}`);
    }
    if (schema.maxProperties !== undefined && Object.keys(value).length > schema.maxProperties) {
      addError(path, `Property count ${Object.keys(value).length} > maxProperties ${schema.maxProperties}`);
    }
    // dependencies: if a property is present, require other properties (or validate a schema)
    if (schema.dependencies) {
      for (const [key, dep] of Object.entries(schema.dependencies)) {
        if (!(key in value)) continue;
        if (Array.isArray(dep)) {
          for (const reqKey of dep) {
            if (!(reqKey in value)) addError(path, `Property ${key} present but dependency ${reqKey} missing`);
          }
        } else if (typeof dep === 'object') {
          validateValue(value, dep, path, root);
        }
      }
    }
  }
}

function validateFormat(value, format) {
  switch (format) {
    case 'date-time': { const d = new Date(value); return !isNaN(d.getTime()); }
    case 'date': { if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false; return !isNaN(new Date(value).getTime()); }
    case 'email': return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    case 'uri': return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(value);
    default: return true; // unknown formats are accepted (forward-compatible)
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
  process.exit(2);
}

const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

validateValue(data, schema, '$', schema);

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
