import { readFileSync, existsSync, writeFileSync } from 'fs';
import { load, dump } from 'js-yaml';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '..');

// Strict mode: every config problem is fatal instead of a warning (opt-in, so
// existing deployments and the Vite build are unaffected by default).
const STRICT = process.env.CONFIG_STRICT === '1';

// ${VAR} references that had no environment value. The old behaviour silently
// substituted '' (a typo in default.yaml/local.yaml or a forgotten export just
// produced an empty setting). Now each missing name is reported once per
// process, and CONFIG_STRICT=1 turns it into a hard failure naming the variable.
const missingEnvVars = new Set();

function interpolateEnvVars(raw) {
  return raw.replace(/\$\{(\w+)\}/g, (_, name) => {
    const value = process.env[name];
    if (value === undefined || value === '') {
      missingEnvVars.add(name);
      return '';
    }
    return value;
  });
}

// Load YAML file, return {} if missing or unparseable
function loadYAML(filePath) {
  if (!existsSync(filePath)) return {};
  try {
    const raw = readFileSync(filePath, 'utf-8');
    return load(interpolateEnvVars(raw)) || {};
  } catch (err) {
    console.warn(`[config] Failed to parse ${filePath}: ${err.message}`);
    return {};
  }
}

// Deep merge: target is mutated with source values
function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      if (!target[key]) target[key] = {};
      deepMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

// Get a nested value by dot-path: "server.port" → config.server.port
function getKey(obj, dotPath) {
  if (typeof dotPath !== 'string' || dotPath.length === 0) return obj;
  const keys = dotPath.split('.');
  let current = obj;
  for (const k of keys) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[k];
  }
  return current;
}

// Set a nested value by dot-path, creating intermediate objects as needed
function setKey(obj, dotPath, value) {
  if (obj == null || typeof obj !== 'object') return obj;
  if (typeof dotPath !== 'string' || dotPath.length === 0) return obj;
  const keys = dotPath.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (current[keys[i]] == null || typeof current[keys[i]] !== 'object') {
      current[keys[i]] = {};
    }
    current = current[keys[i]];
  }
  current[keys[keys.length - 1]] = value;
  return obj;
}

// Remove a nested key by dot-path
function removeKey(obj, dotPath) {
  if (typeof dotPath !== 'string' || dotPath.length === 0) return obj;
  const keys = dotPath.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (current == null || typeof current[keys[i]] !== 'object') return obj;
    current = current[keys[i]];
  }
  if (current && typeof current === 'object') {
    delete current[keys[keys.length - 1]];
  }
  return obj;
}

const LOCAL_YAML_PATH = join(__dirname, 'local.yaml');

function saveLocalYaml(configObj) {
  try {
    const yaml = dump(configObj, { indent: 2, lineWidth: 120, noRefs: true });
    writeFileSync(LOCAL_YAML_PATH, yaml, 'utf-8');
  } catch (err) {
    console.error(`[config] Failed to write local.yaml: ${err.message}`);
  }
}

function loadLocalYaml() {
  return loadYAML(LOCAL_YAML_PATH);
}

// Apply environment variable overrides (SERVER_PORT=3210 → config.server.port=3210)
// Supports: SERVER_PORT, CLAUDE_MODEL, DIAGNOSIS_DEFAULT_LANGUAGE, etc.
function applyEnvOverrides(config) {
  const envMap = [
    ['SERVER_PORT', 'server.port', Number],
    ['SERVER_BODY_LIMIT', 'server.body_limit', String],
    ['FRONTEND_PORT', 'frontend.port', Number],
    ['FRONTEND_BACKEND_URL', 'frontend.backend_url', String],
    ['CLAUDE_MODEL', 'claude.model', String],
    ['CLAUDE_MAX_TURNS', 'claude.max_turns', Number],
    ['CLAUDE_TIMEOUT_MINUTES', 'claude.timeout_minutes', Number],
    ['DIAGNOSIS_DEFAULT_LANGUAGE', 'diagnosis.default_language', String],
    ['DIAGNOSIS_DEFAULT_SCENE', 'diagnosis.default_scene_name', String],
    ['DATA_DIR', 'data.dir', String],
    ['DATABASE_PATH', 'database.path', String],
    ['DATA_MAX_FILE_SIZE_MB', 'data.upload.max_file_size_mb', Number],
    ['ENGINE_MAX_EVENT_BUFFER', 'engine.max_event_buffer', Number],
    ['ENGINE_CLOSE_RUN_DELAY', 'engine.close_run_delay_seconds', Number],
    // Health probes (GET /api/health/ready) — see config/default.yaml `health:`.
    ['READINESS_MIN_FREE_MB', 'health.min_free_mb', Number],
    ['READINESS_ENGINE_PROBE_TIMEOUT_MS', 'health.engine_probe_timeout_ms', Number],
  ];

  for (const [envKey, configPath, Coerce] of envMap) {
    if (process.env[envKey] !== undefined) {
      const value = Coerce(process.env[envKey]);
      const keys = configPath.split('.');
      let obj = config;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;
    }
  }

  return config;
}

// ─── Light schema validation (type/range only, no new dependency) ────────────
// Guards the MERGED config (default.yaml → local.yaml → env overrides) against
// the classic deployment accidents: a string port, a typo'd language, a
// negative timeout. Only known keys are checked — unknown/new keys are never
// flagged (forward compatible). All violations are reported together.
//
// Behaviour: warnings by default (existing deployments keep booting);
// CONFIG_STRICT=1 makes every violation (and every missing ${VAR}) fatal.
const LANGUAGE_VALUES = ['zh', 'en']; // diagnosis.default_language — read as `=== 'zh'` elsewhere
const SIZE_PATTERN = /^\d+(\.\d+)?\s*(b|kb|mb|gb)?$/i; // express body-parser size, e.g. "10mb"

function describe(value) {
  if (Array.isArray(value)) return 'an array';
  if (value === null) return 'null';
  if (typeof value === 'number' && Number.isNaN(value)) return 'NaN (check the environment override)';
  return `${typeof value} ${JSON.stringify(value)}`;
}

function validateConfig(cfg) {
  const problems = [];

  const checkNumber = (dotPath, { integer = false, min, max } = {}) => {
    const value = getKey(cfg, dotPath);
    if (value === undefined || value === null) return; // absent → the default applies, not an error
    if (typeof value !== 'number' || Number.isNaN(value)) {
      problems.push(`${dotPath}: expected a number, got ${describe(value)}`);
      return;
    }
    if (integer && !Number.isInteger(value)) {
      problems.push(`${dotPath}: expected an integer, got ${value}`);
      return;
    }
    if (min !== undefined && value < min) problems.push(`${dotPath}: expected >= ${min}, got ${value}`);
    if (max !== undefined && value > max) problems.push(`${dotPath}: expected <= ${max}, got ${value}`);
  };

  const checkString = (dotPath, pattern) => {
    const value = getKey(cfg, dotPath);
    if (value === undefined || value === null) return;
    if (typeof value !== 'string') {
      problems.push(`${dotPath}: expected a string, got ${describe(value)}`);
      return;
    }
    if (pattern && !pattern.test(value)) {
      problems.push(`${dotPath}: "${value}" does not match ${pattern} (expected e.g. "10mb")`);
    }
  };

  const checkEnum = (dotPath, allowed) => {
    const value = getKey(cfg, dotPath);
    if (value === undefined || value === null) return;
    if (!allowed.includes(value)) {
      problems.push(`${dotPath}: expected one of [${allowed.join(', ')}], got ${describe(value)}`);
    }
  };

  // HTTP server
  checkNumber('server.port', { integer: true, min: 1, max: 65535 });
  checkString('server.body_limit', SIZE_PATTERN);
  // Diagnosis defaults
  checkEnum('diagnosis.default_language', LANGUAGE_VALUES);
  // Engine budgets (0 is explicitly "unlimited" only where documented; the
  // Claude turn timeout must be a positive number of minutes)
  checkNumber('claude.timeout_minutes', { min: 1 });
  // Readiness probes (GET /api/health/ready)
  checkNumber('health.min_free_mb', { min: 0 });
  checkNumber('health.engine_probe_timeout_ms', { min: 1 });
  // Security: known numeric knobs + any *percent*-named value must be a sane
  // 0-100 percentage (keys owned by the security wave are only checked by name,
  // never rewritten).
  checkNumber('security.login_rate_limit.window_ms', { integer: true, min: 1 });
  checkNumber('security.login_rate_limit.max', { integer: true, min: 1 });
  for (const [key, value] of Object.entries(cfg.security || {})) {
    if (typeof value === 'number' && /(percent|pct)/i.test(key) && (value < 0 || value > 100)) {
      problems.push(`security.${key}: expected a percentage between 0 and 100, got ${value}`);
    }
  }

  return problems;
}

/** Report missing ${VAR} names + validation violations (see STRICT above). */
function reportConfigProblems(cfg) {
  const fatal = [];

  const missing = [...missingEnvVars].sort();
  if (missing.length > 0) {
    // Printed once per variable per process (Set-backed, one line in total).
    console.warn(`[config] WARNING: missing environment variable(s) — ${missing.join(', ')} — each \${VAR} reference to them was substituted with ''`);
    fatal.push(`missing environment variable(s): ${missing.join(', ')}`);
  }

  const violations = validateConfig(cfg);
  if (violations.length > 0) {
    if (STRICT) {
      fatal.push(...violations);
    } else {
      console.warn(`[config] WARNING: ${violations.length} configuration value(s) failed validation (warn-only — set CONFIG_STRICT=1 to make these fatal):`);
      for (const problem of violations) console.warn(`  - ${problem}`);
    }
  }

  if (STRICT && fatal.length > 0) {
    console.error('[config] FATAL: CONFIG_STRICT=1 — refusing to start with an invalid configuration:');
    for (const problem of fatal) console.error(`  - ${problem}`);
    process.exit(1);
  }
}

// ─── Load and export config ─────────────────────────────────────
const defaults = loadYAML(join(__dirname, 'default.yaml'));
const local = loadYAML(join(__dirname, 'local.yaml'));
const merged = deepMerge(defaults, local);
applyEnvOverrides(merged);
reportConfigProblems(merged);

// Re-export PROJECT_ROOT for convenience
export { PROJECT_ROOT };

// Export full config
export const config = merged;

// Convenience accessors
export const server = merged.server;
export const database = merged.database;
export const claude = merged.claude;
export const diagnosis = merged.diagnosis;
export const data = merged.data;
export const engine = merged.engine;
export const security = merged.security;
export const frontend = merged.frontend;
export const pipeline = merged.pipeline;

export const websocket = merged.websocket;

export { getKey, setKey, removeKey, saveLocalYaml, loadLocalYaml };

export default merged;
