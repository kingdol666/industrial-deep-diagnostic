// Harness Engine Definitions — the single source of truth for all engines
// (多 Harness 架构 · 原则 2: 单一事实源注册表).
//
// Frontend dropdown, availability probing, pre-execution validation and the
// capability matrix ALL derive from this table. Adding an engine = one entry
// here (+ an engine client module) — nothing else changes.
//
// capabilities use THIS project's flag set (see base.mjs):
//   live  — can be selected as a run engine (dispatched via diagnosis.service)
//   chat  — supports session resume chats (startSessionChat)
//   runs  — exposes completed run listings
// The doc's seven-face capability matrix (steer/supervise/hitl/…) is
// collapsed into `features` for documentation purposes.

import { BaseHarness } from './base.mjs';
import { probeCliBinary } from '../engine/cli-common.mjs';
import { config } from '../../../../config/loader.mjs';

// ── The 14-engine table ─────────────────────────────────────────────
// processModel: 'inprocess' | 'resident' (常驻会话型) | 'oneshot' (一次性回合型)
export const HARNESS_DEFS = [
  {
    id: 'mock',
    name: 'Mock Engine',
    processModel: 'inprocess',
    homepage: null,
    description: '进程内剧本引擎（无 LLM，联调/CI/冒烟测试专用，恒可用）',
    capabilities: ['live', 'chat'],
    features: { steer: true, supervise: false, hitl: false, terminal: false, contextStats: false, compact: false },
    authEnv: [],
  },
  {
    id: 'codex',
    name: 'OpenAI Codex CLI',
    processModel: 'resident',
    homepage: 'https://github.com/openai/codex',
    description: 'codex app-server — stdio NDJSON JSON-RPC v2（thread/start + turn/start）',
    capabilities: ['live'],
    features: { steer: true, supervise: true, hitl: true, terminal: false, contextStats: true, compact: true },
    authEnv: ['CODEX_HOME'],
  },
  {
    id: 'dsh',
    name: 'DeepSeek Harness',
    processModel: 'resident',
    homepage: 'https://github.com/deepseek-ai/DeepSeek-Harness',
    description: 'dsh --profile acp — 标准 ACP v1（session/new + session/prompt 单飞）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: true, terminal: false, contextStats: true, compact: false },
    authEnv: ['DEEPSEEK_BASE_URL', 'DEEPSEEK_API_KEY'],
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    processModel: 'resident',
    homepage: 'https://opencode.ai',
    description: 'opencode serve — HTTP API + 全局 SSE（prompt_async / permissions / summarize）',
    capabilities: ['live'],
    features: { steer: true, supervise: true, hitl: true, terminal: false, contextStats: true, compact: true },
    authEnv: ['OPENCODE_API_KEY'],
  },
  {
    id: 'gemini',
    name: 'Gemini CLI',
    processModel: 'oneshot',
    homepage: 'https://github.com/google-gemini/gemini-cli',
    description: 'gemini --output-format stream-json — 一次性回合，session_id 续会话',
    capabilities: ['live', 'chat'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: true, compact: false },
    authEnv: ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
  },
  {
    id: 'copilot',
    name: 'GitHub Copilot CLI',
    processModel: 'oneshot',
    homepage: 'https://docs.github.com/en/copilot/how-tos/copilot-cli',
    description: 'copilot --output-format json — 一次性回合（GitHub 账号鉴权）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: false, compact: false },
    authEnv: ['COPILOT_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'],
  },
  {
    id: 'cursor',
    name: 'Cursor CLI',
    processModel: 'oneshot',
    homepage: 'https://cursor.com/docs/cli/headless',
    description: 'cursor-agent --output-format stream-json — Claude 同构帧（默认不带 --force）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: false, compact: false },
    authEnv: ['CURSOR_API_KEY'],
  },
  {
    id: 'crush',
    name: 'Charm Crush',
    processModel: 'oneshot',
    homepage: 'https://github.com/charmbracelet/crush',
    description: 'crush run -q — 纯文本 stdout 一次性回合（v0.92+ 无 JSON 格式）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: true, compact: false },
    authEnv: ['AW_CRUSH_API_KEY'],
  },
  {
    id: 'goose',
    name: 'Block Goose',
    processModel: 'oneshot',
    homepage: 'https://blockgoose.io',
    description: 'goose run -t --output-format stream-json — 一次性回合，--resume 续会话',
    capabilities: ['live', 'chat'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: true, compact: false },
    authEnv: ['OPENAI_API_KEY', 'GOOSE_PROVIDER', 'OPENAI_HOST', 'OPENAI_BASE_PATH'],
  },
  {
    id: 'qwen',
    name: 'Qwen Code',
    processModel: 'resident',
    homepage: 'https://github.com/QwenLM/qwen-code',
    description: 'qwen --experimental-acp — 旧版 Zed ACP（camelCase 方法、单隐式会话）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: true, terminal: false, contextStats: false, compact: false },
    authEnv: ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL'],
  },
  {
    id: 'pi',
    name: 'pi coding agent',
    processModel: 'oneshot',
    homepage: 'https://github.com/badlogic/pi-mono',
    description: 'pi -p --mode json — 一次性回合，prompt 经 @临时文件 投递',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: false, terminal: false, contextStats: true, compact: false },
    authEnv: ['PI_API_KEY'],
  },
  {
    id: 'hermes',
    name: 'Hermes Agent',
    processModel: 'resident',
    homepage: 'https://github.com/NousResearch/hermes-agent',
    description: 'hermes acp — 标准 ACP v1（与 dsh 同型实现）',
    capabilities: ['live'],
    features: { steer: false, supervise: true, hitl: true, terminal: false, contextStats: true, compact: false },
    authEnv: ['GLM_API_KEY', 'HERMES_PROVIDER', 'HERMES_MODEL'],
  },
];

/** Engine ids from the definition table (mock + 11 CLI engines). */
export const ENGINE_IDS = HARNESS_DEFS.map((d) => d.id);

// ── Health probe cache (探测 30s 缓存 — 探测与拉起同源) ──
const probeCache = new Map(); // id -> { at, promise }

function cacheTtlMs() {
  const v = Number(config.harness?.health_cache_ms);
  return Number.isFinite(v) && v >= 0 ? v : 30000;
}

/**
 * Probe an engine's availability (cached). In-process engines are always
 * available; CLI engines resolve + execute `--version` via the SAME binary
 * resolution the real spawn uses.
 */
export function probeEngineAvailability(id, { force = false } = {}) {
  const def = HARNESS_DEFS.find((d) => d.id === id);
  if (!def) return Promise.resolve({ available: false, error: `unknown harness: ${id}` });

  if (def.processModel === 'inprocess') {
    return Promise.resolve({ available: true, binary: null, inprocess: true, version: null, error: null });
  }

  const ttl = cacheTtlMs();
  const cached = probeCache.get(id);
  if (!force && ttl > 0 && cached && Date.now() - cached.at < ttl) {
    return cached.promise;
  }
  const promise = probeCliBinary(id, { versionArgs: def.versionArgs || ['--version'] });
  probeCache.set(id, { at: Date.now(), promise });
  return promise;
}

/** Drop cached probes (tests / config reload). */
export function invalidateProbeCache(id) {
  if (id) probeCache.delete(id);
  else probeCache.clear();
}

// ── Default harness — best-adapted AVAILABLE engine (默认 harness 动态解析) ──
// Preference: config harness.default (omp — richest adaptation: live+runs+
// report+html+enhancement+chat), then by adaptation richness. The FIRST
// AVAILABLE engine in the chain wins; availability uses the shared probe cache.
const ADAPTATION_PRIORITY = [
  'omp',       // 原生管线引擎 — 全能力面（live/runs/report/html/enhancement/chat）
  'claude',    // Claude Agent SDK — live + chat
  'mock',      // 进程内剧本引擎 — 恒可用（联调/CI）
  'opencode', 'codex', 'gemini', 'goose', 'dsh', 'hermes',
  'qwen', 'pi', 'cursor', 'copilot', 'crush',
];

export function defaultHarnessChain() {
  const preferred = (config.harness?.default || 'omp').toLowerCase();
  return [preferred, ...ADAPTATION_PRIORITY.filter((id) => id !== preferred)];
}

/**
 * Best-adapted currently-available harness (async — uses cached probes).
 * Falls back to the first registered id when nothing probes available.
 */
export async function resolveBestAvailableHarness() {
  const { getHarness, listHarnessIds } = await import('./registry.mjs');
  const ids = listHarnessIds();
  const results = await Promise.all(ids.map(async (id) => {
    try {
      return [id, (await getHarness(id).health()).available === true];
    } catch {
      return [id, false];
    }
  }));
  const available = new Set(results.filter(([, a]) => a).map(([id]) => id));
  for (const id of defaultHarnessChain()) {
    if (available.has(id)) return id;
  }
  return ids[0];
}

// ── Generic live harness for the 12 definition-table engines ──
export function createLiveHarness(def) {
  const clientLoader = {
    mock: () => import('../engine/mock-client.mjs'),
    codex: () => import('../engine/codex-client.mjs'),
    opencode: () => import('../engine/opencode-client.mjs'),
    dsh: () => import('../engine/acp-client.mjs').then((m) => m.dshClient),
    hermes: () => import('../engine/acp-client.mjs').then((m) => m.hermesClient),
    qwen: () => import('../engine/acp-client.mjs').then((m) => m.qwenClient),
    gemini: () => import('../engine/oneshot-specs.mjs').then((m) => m.geminiClient),
    copilot: () => import('../engine/oneshot-specs.mjs').then((m) => m.copilotClient),
    cursor: () => import('../engine/oneshot-specs.mjs').then((m) => m.cursorClient),
    crush: () => import('../engine/oneshot-specs.mjs').then((m) => m.crushClient),
    goose: () => import('../engine/oneshot-specs.mjs').then((m) => m.gooseClient),
    pi: () => import('../engine/oneshot-specs.mjs').then((m) => m.piClient),
  }[def.id];

  return new class extends BaseHarness {
    id = def.id;
    name = def.name;
    kind = 'live';
    description = def.description;
    capabilities = [...def.capabilities];
    processModel = def.processModel;
    homepage = def.homepage;
    features = { ...def.features };
    authEnv = [...(def.authEnv || [])];

    manifest() {
      return {
        ...super.manifest(),
        processModel: this.processModel,
        homepage: this.homepage,
        features: this.features,
        authEnv: this.authEnv,
      };
    }

    async health() {
      const probe = await probeEngineAvailability(def.id);
      return {
        available: probe.available,
        meta: {
          engine: def.id,
          process_model: def.processModel,
          binary: probe.binary || null,
          version: probe.version || null,
          inprocess: probe.inprocess === true,
          probe_error: probe.error || null,
          auth_env: this.authEnv,
        },
      };
    }

    async startDiagnosis(params) {
      const client = await clientLoader();
      return client.startDiagnosis(params);
    }
  }();
}
