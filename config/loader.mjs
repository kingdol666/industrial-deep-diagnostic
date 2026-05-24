import { readFileSync, existsSync, writeFileSync } from 'fs';
import { load, dump } from 'js-yaml';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '..');

// Load YAML file, return {} if missing or unparseable
function loadYAML(filePath) {
  if (!existsSync(filePath)) return {};
  try {
    const raw = readFileSync(filePath, 'utf-8');
    const interpolated = raw.replace(/\$\{(\w+)\}/g, (_, name) => process.env[name] || '');
    return load(interpolated) || {};
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
    ['DATA_MAX_FILE_SIZE_MB', 'data.upload.max_file_size_mb', Number],
    ['ENGINE_MAX_EVENT_BUFFER', 'engine.max_event_buffer', Number],
    ['ENGINE_CLOSE_RUN_DELAY', 'engine.close_run_delay_seconds', Number],
    ['SECURITY_HITL_TIMEOUT', 'security.hitl_auto_deny_seconds', Number],
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

// ─── Load and export config ─────────────────────────────────────
const defaults = loadYAML(join(__dirname, 'default.yaml'));
const local = loadYAML(join(__dirname, 'local.yaml'));
const merged = deepMerge(defaults, local);
applyEnvOverrides(merged);

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

export { getKey, setKey, removeKey, saveLocalYaml, loadLocalYaml };

export default merged;
