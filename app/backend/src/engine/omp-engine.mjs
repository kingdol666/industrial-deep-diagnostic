// OMPEngine — drives live diagnoses and chats through the OMP harness contract.
//
// The OMP agent contracts (.omp/agents/*.md — YAML frontmatter + prompt body)
// are the single source of truth for sub-agent topology when the OMP harness
// is selected. They are parsed here and injected into the Claude Agent SDK's
// `agents` option, so sub-agent work is delegated to the OMP-defined agents
// (context-builder, data-processor, diagnostician, judge, reporter, ...)
// instead of the built-in .claude/agents set.

import { existsSync, readdirSync, readFileSync, statSync } from 'fs';
import { join, basename } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const OMP_AGENTS_DIR = join(PROJECT_ROOT, '.omp', 'agents');

function parseFrontmatter(raw) {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return { meta: {}, body: raw };
  const [, fmText, body] = match;
  const meta = {};
  for (const line of fmText.split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) meta[kv[1].trim().toLowerCase()] = kv[2].trim();
  }
  return { meta, body };
}

function normalizeModel(rawModel) {
  if (!rawModel || /^default$/i.test(rawModel)) return undefined;
  return rawModel;
}

// Parse a single .omp/agents/*.md contract into an SDK AgentDefinition.
// NOTE: the contract's `tools` frontmatter lists lowercase tool names that
// don't match SDK tool IDs (and `bash` has no equivalent on Windows, where
// shell access is `PowerShell`). Passing a restrictive list would strip shell
// access from pipeline agents, so tools are intentionally omitted — each
// agent inherits the parent's full toolset (per the SDK contract).
export function parseOmpAgentContract(raw, fallbackName) {
  const { meta, body } = parseFrontmatter(raw);
  const name = meta.name || fallbackName;
  if (!name || !body.trim()) return null;
  return {
    name,
    definition: {
      description: meta.description || `OMP agent ${name}`,
      prompt: body.trim(),
      ...(normalizeModel(meta.model) ? { model: normalizeModel(meta.model) } : {}),
    },
  };
}

// Load every OMP agent contract into an SDK agents map (cached on disk mtime).
let agentsCache = { mtime: 0, agents: null, names: [] };

export function loadOmpAgents() {
  if (!existsSync(OMP_AGENTS_DIR)) {
    return { agents: {}, names: [], count: 0 };
  }
  const files = readdirSync(OMP_AGENTS_DIR).filter(f => f.endsWith('.md'));
  let latestMtime = 0;
  for (const f of files) {
    try { latestMtime = Math.max(latestMtime, statSync(join(OMP_AGENTS_DIR, f)).mtimeMs); } catch { /* ignore */ }
  }

  if (agentsCache.agents && agentsCache.mtime === latestMtime && latestMtime > 0) {
    return { agents: agentsCache.agents, names: agentsCache.names, count: agentsCache.names.length };
  }

  const agents = {};
  const names = [];
  for (const f of files) {
    try {
      const raw = readFileSync(join(OMP_AGENTS_DIR, f), 'utf-8');
      const parsed = parseOmpAgentContract(raw, basename(f, '.md'));
      if (parsed) {
        agents[parsed.name] = parsed.definition;
        names.push(parsed.name);
      }
    } catch (e) {
      logger.warn(`OMP agent contract ${f} failed to parse: ${e.message}`, { context: 'OMPEngine' });
    }
  }

  agentsCache = { mtime: latestMtime, agents, names };
  logger.info(`OMP harness contract loaded: ${names.length} agents (${names.join(', ')})`, { context: 'OMPEngine' });
  return { agents, names, count: names.length };
}

function stat() {
  // eslint-disable-next-line no-undef
  return require('fs').statSync(OMP_AGENTS_DIR);
}

// System prompt for live OMP harness runs: binds the main agent to orchestrate
// the OMP agent contracts with the same pipeline discipline as the built-in
// engine, but with OMP topology as the only sub-agent source.
export function buildOmpSystemPrompt({ sceneName, reportLanguage, skillContent }) {
  const { names } = loadOmpAgents();
  const safeScene = String(sceneName || config.diagnosis.default_scene_name || 'diagnosis').replace(/[\x00-\x08\x0A-\x1F]/g, '').trim();
  const languageRule = reportLanguage === 'en'
    ? 'All narrative output, headings, analysis descriptions, recommendations, summary markdown, and report.md content must be written in English.'
    : '所有 narrative、标题、分析说明、建议、summary markdown 与 report.md 必须使用中文；变量名、列名、JSON enum、代码保持英文。';

  const agentList = names.length ? names.join(', ') : '(no OMP contracts found — fall back to direct execution)';

  return `You are executing the industrial deep diagnostic pipeline for scene "${safeScene}" under the OMP harness.

OMP harness contract (binding):
1. Sub-agent topology comes exclusively from the OMP contract directory (.omp/agents/). Available OMP agents: ${agentList}.
2. Main agent orchestrates only. Every pipeline step with a matching OMP agent MUST be delegated via the Agent tool to that OMP agent (Step 2 → context-builder, Step 3 → data-processor, Step 4 → diagnostician, Step 5 → judge, Step 6 → reporter, Step 7 → report-reviewer, Step 8 → html-visualizer, Step 8.5 → html-reviewer). Do not complete delegated work directly and do not invent agents outside the OMP contract.
3. Treat the skill protocol as binding. Follow the full pipeline contract and do not skip, reorder, or silently omit steps.
4. Context building must produce ontology-grounded understanding before final diagnosis. Data analysis, diagnosis, review, report, and audit must stay aligned to the same ontology semantics.
5. Diagnosis must use competing hypotheses, temporal precedence, statistical evidence, physical mechanism, and contradiction checks. If evidence cannot discriminate, output COMPETING_SET or NEEDS_DATA instead of guessing.
6. Validate required structured artifacts and honor repair / review gates before considering the run complete.
7. Use exact absolute data paths provided by the runtime. Do not reinterpret them relative to any skill or agent directory.
8. ${languageRule}
9. If the user provides follow-up answers or continuation instructions, continue from the existing session state while preserving the same pipeline discipline.${skillContent ? `\n\nAuthoritative skill reference excerpt:\n${skillContent}` : ''}`;
}

// Lighter system prompt for OMP harness chats (no pipeline contract): the OMP
// agents stay available for delegation, but conversation is not forced into
// the 9-step diagnostic pipeline.
export function buildOmpChatSystemPrompt() {
  const { names } = loadOmpAgents();
  const agentList = names.length ? names.join(', ') : '(none)';
  return `You are the OMP harness console assistant. Sub-agent topology comes exclusively from the OMP contract directory (.omp/agents/). Available OMP agents: ${agentList}. Delegate to the matching OMP agent via the Agent tool whenever the user's request maps to a specialized pipeline step (ontology building, statistical processing, diagnosis, judging, reporting, HTML visualization); otherwise answer directly. Do not invent agents outside the OMP contract.`;
}
