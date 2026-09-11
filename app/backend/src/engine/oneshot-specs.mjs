// One-shot engine specs — the per-engine "mapping table" for the
// one-shot CLI family (多 Harness 架构 · 原则 3).
//
//   gemini   gemini --output-format stream-json            JSONL init/message/tool_use/result
//   copilot  copilot --output-format json                  JSONL (prompt via stdin)
//   cursor   cursor-agent -p --output-format stream-json   Claude-Code-isomorphic frames
//   crush    crush run -q                                  plain-text stdout (v0.92+ removed --format json)
//   goose    goose run -t --output-format stream-json      JSONL message/tool_call frames, resume via --resume
//   pi       pi -p --mode json                             JSONL session/message_end/turn_end, prompt via @argFile
//
// All specs: probes share spawn resolution (探测与拉起同源), prompts travel
// via stdin or @argFile — never through argv (except goose's required -t,
// which is whitespace-flattened and length-capped), unknown events are
// counted and skipped (schema drift ≠ crash), and non-zero exits become
// error result events with a stderr tail.

import { existsSync } from 'fs';
import { join } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { probeCliBinary } from './cli-common.mjs';
import { createOneShotEngineClient } from './one-shot.mjs';
import {
  resolveAnalysisTarget, buildRuntimeProtocol,
  buildPrompt as buildDataPrompt,
  buildOntologyDirective, buildEnhancementDirective,
} from './claude-client.mjs';

// ── Shared prompt assembly (mirrors omp-client startDiagnosis) ──
function buildEnginePrompt({ analysisTarget, userQuestion, sceneName, reportLanguage, followUpMessage, ontology, enhancement }) {
  const lang = reportLanguage || config.diagnosis.default_language;
  const { dataPaths, promptTarget } = resolveAnalysisTarget(analysisTarget);

  const skillMd = join(PROJECT_ROOT, config.claude.skill_dir || '.claude/skills/industrial-analysis-auto', 'SKILL.md');
  const skillRef = existsSync(skillMd)
    ? `First read the authoritative skill definition at ${skillMd} and follow its full pipeline contract as binding.`
    : 'Follow the industrial deep diagnostic skill protocol (industrial-analysis-auto).';

  const prompt = `${buildRuntimeProtocol(sceneName, lang)}

${skillRef}

${buildDataPrompt(sceneName, userQuestion, promptTarget, lang, followUpMessage)}${buildOntologyDirective(ontology)}${buildEnhancementDirective(enhancement)}`;

  return { dataPaths, prompt };
}

function harnessTimeout(id) {
  const t = config.harness?.engines?.[id]?.timeout_minutes;
  return Number.isFinite(t) && t > 0 ? t : (config.harness?.timeout_minutes || 0);
}

function probeFor(id, versionArgs) {
  return () => probeCliBinary(id, { versionArgs });
}

function sessionIdMarker(id, value, { resumable }) {
  return { sessionId: value ? `${id}:${value}` : `${id}:run`, resumable: !!value && resumable };
}

function runMarker(id, runId, { resumable = false } = {}) {
  return { sessionId: `${id}:run:${runId}`, resumable };
}

// ── Shared "Claude-Code-isomorphic" line mapper (cursor / copilot) ──
// Frames: {type:'system',subtype:'init',session_id} · {type:'assistant',message:{content[]}}
//         {type:'user',message:{content:[{type:'tool_result'...}]}} · {type:'result',...}
function claudeishParseLine(evt, ctx) {
  if (!evt || typeof evt !== 'object') {
    if (typeof evt === 'string' && evt.trim()) ctx.text(evt);
    return null;
  }
  switch (evt.type) {
    case 'system':
      if (evt.session_id) ctx.session(evt.session_id);
      return null;
    case 'assistant': {
      const content = evt.message?.content;
      if (typeof content === 'string') { ctx.text(content); return null; }
      const blocks = Array.isArray(content) ? content.map((b) => {
        if (b?.type === 'text') return { type: 'text', text: b.text || '' };
        if (b?.type === 'thinking') return { type: 'thinking', thinking: b.thinking || '' };
        if (b?.type === 'tool_use' || b?.type === 'tool_call') {
          return { type: 'tool_use', id: b.id, name: b.name, input: b.input || {} };
        }
        return null;
      }).filter(Boolean) : [];
      if (blocks.length) ctx.assistant(blocks);
      return null;
    }
    case 'user': {
      const content = evt.message?.content;
      if (Array.isArray(content)) {
        for (const b of content) {
          if (b?.type === 'tool_result') {
            ctx.toolResult({ toolUseId: b.tool_use_id, content: b.content, isError: b.is_error });
          }
        }
      }
      return null;
    }
    case 'result':
      ctx.result(evt.subtype === 'success' || evt.is_error === false ? 'success' : 'error_during_execution', evt.subtype || evt.stop_reason);
      return null;
    default:
      ctx.unknown(evt.type);
      return null;
  }
}

// ── gemini ──
const geminiSpec = {
  id: 'gemini',
  model: config.harness?.engines?.gemini?.model || null,
  versionArgs: ['--version'],
  promptDelivery: 'stdin',
  buildArgs({ resumeSessionId }) {
    const args = ['--output-format', 'stream-json', '-p'];
    if (resumeSessionId) args.push('--resume', resumeSessionId);
    return args;
  },
  engineEnv() {
    return { GEMINI_CLI_TRUST_WORKSPACE: 'true' };
  },
  parseLine(evt, ctx) {
    if (!evt || typeof evt !== 'object') return null;
    switch (evt.type) {
      case 'init':
        ctx.session(evt.session_id || evt.sessionId || null);
        return null;
      case 'message': {
        const content = evt.content ?? evt.text;
        if (typeof content === 'string' && content) ctx.text(content);
        else if (Array.isArray(content)) {
          const blocks = content.map((b) => (b?.type === 'text'
            ? { type: 'text', text: b.text || '' }
            : b?.type === 'tool_use' ? { type: 'tool_use', id: b.id, name: b.name, input: b.input || {} } : null)).filter(Boolean);
          if (blocks.length) ctx.assistant(blocks);
        }
        return null;
      }
      case 'tool_use':
        ctx.toolUse({ id: evt.tool_id || evt.id, name: evt.name, input: evt.args || evt.input || {} });
        return null;
      case 'tool_result':
      case 'tool_response':
        ctx.toolResult({ toolUseId: evt.tool_id || evt.id, content: evt.output ?? evt.content ?? '', isError: evt.is_error });
        return null;
      case 'result':
        ctx.result(evt.status === 'success' ? 'success' : 'error_during_execution', evt.status || evt.error?.message);
        return null;
      default:
        ctx.unknown(evt.type);
        return null;
    }
  },
  parseSessionId(marker) {
    if (typeof marker !== 'string' || !marker.startsWith('gemini:')) return null;
    const sid = marker.slice('gemini:'.length);
    // "unbound" = the engine never reported a session id — resume impossible.
    return sid && !sid.startsWith('unbound:') ? { sessionId: sid, resumable: true } : null;
  },
  probe: probeFor('gemini', ['--version']),
};

// ── copilot ──
const copilotSpec = {
  id: 'copilot',
  model: config.harness?.engines?.copilot?.model || null,
  versionArgs: ['--version'],
  promptDelivery: 'stdin',
  buildArgs() {
    return ['--output-format', 'json', '-p'];
  },
  engineEnv() {
    return { NO_COLOR: '1' };
  },
  parseLine: claudeishParseLine,
  parseSessionId(marker) {
    // GitHub 账号锁定、无程序化 session resume — follow-ups go through Continue.
    return sessionIdMarker('copilot', typeof marker === 'string' ? marker.slice('copilot:'.length) : null, { resumable: false });
  },
  probe: probeFor('copilot', ['--version']),
};

// ── cursor ──
const cursorSpec = {
  id: 'cursor',
  model: config.harness?.engines?.cursor?.model || null,
  versionArgs: ['--version'],
  promptDelivery: 'stdin',
  buildArgs() {
    // 默认不带 --force — 文件变更只提案不落地（与平台写控制哲学一致）。
    return ['--output-format', 'stream-json', '-p'];
  },
  parseLine: claudeishParseLine,
  parseSessionId(marker) {
    return sessionIdMarker('cursor', typeof marker === 'string' ? marker.slice('cursor:'.length) : null, { resumable: false });
  },
  probe: probeFor('cursor', ['--version']),
};

// ── crush (plain-text stdout) ──
const crushSpec = {
  id: 'crush',
  mode: 'plaintext',
  sessionMarker: true, // no programmatic session id — opaque run marker only
  versionArgs: ['--version'],
  promptDelivery: 'stdin',
  buildArgs() {
    return ['run', '-q'];
  },
  engineEnv() {
    const apiKey = config.harness?.engines?.crush?.api_key;
    return apiKey ? { AW_CRUSH_API_KEY: apiKey } : {};
  },
  parseLine: null, // plaintext mode — base aggregates raw lines as assistant text
  parseSessionId(marker) {
    return sessionIdMarker('crush', typeof marker === 'string' ? marker.slice('crush:'.length) : null, { resumable: false });
  },
  probe: probeFor('crush', ['--version']),
};

// ── goose ──
const gooseSpec = {
  id: 'goose',
  model: config.harness?.engines?.goose?.model || null,
  sessionMarker: true, // resume via --name + bare --resume — the run marker IS the session reference
  versionArgs: ['--version'],
  promptDelivery: 'arg', // goose requires -t; positional/stdin prompts are refused (exit 2)
  buildArgs({ prompt, resumeSessionId }) {
    // argv 长度纪律: flatten whitespace + cap below the Windows ~8K cmdline limit.
    const flat = String(prompt).replace(/[\x00-\x1F\x7F]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
    const capped = flat.length > 6000
      ? `${flat.slice(0, 6000)} …[truncated for CLI argv limit — see run dir for the full run context]`
      : flat;
    const args = [
      'run', '--output-format', 'stream-json',
      '--name', `idd-${config.harness?.engines?.goose?.session_name || 'diag'}`,
      '-t', capped,
    ];
    if (resumeSessionId) args.push('--resume');
    return args;
  },
  engineEnv() {
    return {
      GOOSE_MODE: 'auto',
      GOOSE_CONTEXT_STRATEGY: 'summarize',
      GOOSE_DISABLE_SESSION_NAMING: 'true',
    };
  },
  parseLine(evt, ctx) {
    if (!evt || typeof evt !== 'object') return null;
    switch (evt.type) {
      case 'message': {
        const msg = evt.message || evt;
        const content = msg.content;
        if (typeof content === 'string' && content) { ctx.text(content); return null; }
        if (Array.isArray(content)) {
          const blocks = content.map((b) => {
            if (b?.type === 'text') return { type: 'text', text: b.text || '' };
            if (b?.type === 'tool_call' || b?.type === 'tool_use') {
              let input = b.arguments ?? b.input ?? {};
              if (typeof input === 'string') { try { input = JSON.parse(input); } catch { input = { raw: input }; } }
              return { type: 'tool_use', id: b.id, name: b.name || b.tool, input };
            }
            if (b?.type === 'thinking') return { type: 'thinking', thinking: b.thinking || '' };
            return null;
          }).filter(Boolean);
          if (blocks.length) {
            ctx.turn();
            ctx.assistant(blocks);
          }
        }
        return null;
      }
      case 'tool_call':
        ctx.toolUse({ id: evt.id, name: evt.name || evt.tool, input: evt.arguments || evt.input || {} });
        return null;
      case 'tool_call_response':
        ctx.toolResult({ toolUseId: evt.id, content: evt.output ?? evt.content ?? '', isError: evt.is_error });
        return null;
      case 'finish':
      case 'result':
        ctx.result('success', evt.reason || 'success');
        return null;
      default:
        ctx.unknown(evt.type);
        return null;
    }
  },
  parseSessionId(marker) {
    // goose resumes the latest session for --name; the DB marker only proves
    // THIS run created a named goose session.
    if (typeof marker === 'string' && marker.startsWith('goose:run:')) return { sessionId: marker, resumable: true };
    return runMarker('goose', '', { resumable: false });
  },
  probe: probeFor('goose', ['--version']),
};

// ── pi (@argFile prompt delivery) ──
const piSpec = {
  id: 'pi',
  model: config.harness?.engines?.pi?.model || null,
  versionArgs: ['--version'],
  promptDelivery: 'argFile', // prompt written to a temp file, passed as @<path> — Windows ~8K argv cap workaround
  buildArgs({ promptFile }) {
    const args = ['--mode', 'json', '-p'];
    if (promptFile) args.push(`@${promptFile}`);
    return args;
  },
  parseLine(evt, ctx) {
    if (!evt || typeof evt !== 'object') return null;
    switch (evt.type) {
      case 'session':
        ctx.session(evt.id || evt.session_id || evt.sessionId || null);
        return null;
      case 'message_end': {
        const msg = evt.message || {};
        if (msg.role !== 'assistant') return null;
        const content = msg.content;
        if (typeof content === 'string' && content) { ctx.turn(); ctx.text(content); return null; }
        if (Array.isArray(content)) {
          const blocks = content.map((b) => {
            if (b?.type === 'text') return { type: 'text', text: b.text || '' };
            if (b?.type === 'tool_call' || b?.type === 'tool_use') return { type: 'tool_use', id: b.id, name: b.name, input: b.input || b.arguments || {} };
            if (b?.type === 'thinking') return { type: 'thinking', thinking: b.thinking || '' };
            return null;
          }).filter(Boolean);
          if (blocks.length) { ctx.turn(); ctx.assistant(blocks); }
        }
        return null;
      }
      case 'message_update':
      case 'turn_end':
      case 'turn_start':
        return null; // deltas ignored — full content arrives with message_end
      default:
        ctx.unknown(evt.type);
        return null;
    }
  },
  parseSessionId(marker) {
    return sessionIdMarker('pi', typeof marker === 'string' ? marker.slice('pi:'.length) : null, { resumable: false });
  },
  probe: probeFor('pi', ['--version']),
};

// ── Engine clients (standard module shape for diagnosis.service) ──
function clientFor(spec) {
  return createOneShotEngineClient(spec, {
    buildPrompt: buildEnginePrompt,
    defaultTimeoutMinutes: harnessTimeout(spec.id),
  });
}

export const geminiClient = clientFor(geminiSpec);
export const copilotClient = clientFor(copilotSpec);
export const cursorClient = clientFor(cursorSpec);
export const crushClient = clientFor(crushSpec);
export const gooseClient = clientFor(gooseSpec);
export const piClient = clientFor(piSpec);

// One-shot runs write prompts into the project cwd — assert the dir exists.
if (!existsSync(PROJECT_ROOT)) {
  logger.error('PROJECT_ROOT missing — one-shot engines will fail to spawn', { context: 'OneShotSpecs' });
}
