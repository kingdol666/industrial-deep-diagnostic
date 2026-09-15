// LLM provider adapter for the baseline comparators.
//
// FABRICATION RED LINE
// --------------------
// The IDD repository's benchmark contract (docs/benchmark/reproduction-guide.md
// §10, "答案文件真实性红线") forbids hand-written or invented baseline answers.
// This module therefore has exactly two legitimate outcomes per call:
//   1. a genuine model response, recorded with provider/model/latency/raw text;
//   2. an explicit failure (`ok: false`) that the caller must surface as
//      SKIPPED / ERROR — never substituted with a fabricated answer.
// There is a `selftest` provider for plumbing checks only; it is tagged
// `fabricated: true` and the sweep refuses to score it.
//
// ISOLATION
// ---------
// CLI harnesses are invoked with cwd set to a neutral scratch directory and
// with tools disabled. This matters: a bare-LLM baseline that had read this
// repository's CLAUDE.md / AGENTS.md / skills would not be a bare LLM baseline
// at all. The comparator must see only the prompt.

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { LAB_ROOT, ensureDir } from '../paths.mjs';

const SCRATCH = path.join(LAB_ROOT, '.llm-scratch');

/** Known harness CLIs: id -> how to build a one-shot, non-interactive call. */
export const CLI_HARNESSES = {
  claude: {
    label: 'Claude Code CLI',
    bin: 'claude',
    args: ['-p', '--output-format', 'text', '--bare'],
    disallowTools: true,
    stdin: true,
  },
  dsh: {
    label: 'DeepSeek Harness (headless profile)',
    bin: 'dsh',
    args: ['--profile', 'headless'],
    stdin: false,
    promptAsArg: true,
  },
  codex: {
    label: 'Codex CLI',
    bin: 'codex',
    args: ['exec', '--skip-git-repo-check'],
    stdin: false,
    promptAsArg: true,
  },
  omp: {
    label: 'OMP CLI',
    bin: 'omp',
    args: ['-p'],
    stdin: false,
    promptAsArg: true,
  },
  gemini: {
    label: 'Gemini CLI',
    bin: 'gemini',
    args: ['-p'],
    stdin: false,
    promptAsArg: true,
  },
  qwen: {
    label: 'Qwen Code CLI',
    bin: 'qwen',
    args: ['-p'],
    stdin: false,
    promptAsArg: true,
  },
  opencode: {
    label: 'opencode CLI',
    bin: 'opencode',
    args: ['run'],
    stdin: false,
    promptAsArg: true,
  },
};

const TOOL_DENY = [
  'Bash', 'Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'Grep',
  'WebFetch', 'WebSearch', 'Task', 'NotebookEdit', 'TodoWrite',
];

/**
 * Candidate directories to search for harness binaries.
 *
 * PATH alone is not reliable here: when the lab runs inside Nitro's bundled
 * server the process can inherit a reduced environment, so a harness that is
 * plainly installed reports as missing (this actually happened — see
 * /api/provider-doctor, which found claude.exe on PATH while this module did
 * not). We therefore search PATH *plus* the well-known install locations for
 * the harnesses we support, and honour an explicit override.
 */
function searchDirs() {
  const raw = process.env.PATH || process.env.Path || process.env.path || '';
  const fromPath = raw.split(path.delimiter).filter(Boolean);
  const home = process.env.USERPROFILE || process.env.HOME || '';
  const extra = [
    process.env.BASELINE_LLM_CLI_DIR,
    home && path.join(home, '.local', 'bin'),
    home && path.join(home, '.bun', 'bin'),
    process.env.APPDATA && path.join(process.env.APPDATA, 'npm'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'hermes', 'bin'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Programs', 'Ollama'),
    '/usr/local/bin',
    '/usr/bin',
    '/opt/homebrew/bin',
  ].filter(Boolean);
  return [...new Set([...fromPath, ...extra])];
}

function which(bin) {
  // 1) explicit override wins
  const override = process.env.BASELINE_LLM_CLI_PATH;
  if (override) {
    try {
      fs.accessSync(override, fs.constants.F_OK);
      if (path.basename(override).startsWith(bin)) return override;
    } catch { /* fall through to the search */ }
  }

  const exts = process.platform === 'win32' ? ['.exe', '.cmd', '.bat', '.ps1', ''] : [''];
  const found = [];
  for (const d of searchDirs()) {
    for (const e of exts) {
      const p = path.join(d, bin + e);
      try {
        fs.accessSync(p, fs.constants.F_OK);
        if (!found.includes(p)) found.push(p);
      } catch { /* keep looking */ }
    }
  }
  if (!found.length) return null;
  // Prefer genuine executables over Windows shell shims: Node cannot spawn a
  // .cmd directly (CVE-2024-27980 hardening), so a real .exe is strictly better.
  const real = found.find((p) => /\.exe$/i.test(p) || path.extname(p) === '');
  return real || found[0];
}

/** True when the binary must be launched through a shell (Windows shim). */
function needsShell(binPath) {
  return process.platform === 'win32' && /\.(cmd|bat)$/i.test(binPath || '');
}

/** Enumerate what is actually available right now. */
export function detectProviders(cfg = {}) {
  const out = [];

  // 1) OpenAI-compatible HTTP endpoint
  const baseUrl = cfg.llmBaseUrl || process.env.BASELINE_LLM_BASE_URL || '';
  const apiKey = cfg.llmApiKey || process.env.BASELINE_LLM_API_KEY || '';
  out.push({
    id: 'openai-compatible',
    kind: 'http',
    label: 'OpenAI-compatible HTTP endpoint',
    available: Boolean(baseUrl && apiKey),
    detail: baseUrl
      ? `${baseUrl}${apiKey ? '' : ' (no API key)'}`
      : 'BASELINE_LLM_BASE_URL / BASELINE_LLM_API_KEY not set',
    model: cfg.llmModel || process.env.BASELINE_LLM_MODEL || '',
    fabricated: false,
  });

  // 2) Local harness CLIs
  for (const [id, spec] of Object.entries(CLI_HARNESSES)) {
    const p = which(spec.bin);
    out.push({
      id: `cli:${id}`,
      kind: 'cli',
      label: spec.label,
      available: Boolean(p),
      detail: p || `\`${spec.bin}\` not found on PATH`,
      bin: p,
      shellShim: needsShell(p),
      model: cfg.llmModel || process.env.BASELINE_LLM_MODEL || '',
      fabricated: false,
    });
  }

  // 3) Explicit plumbing self-test (never scores as a real baseline)
  out.push({
    id: 'selftest',
    kind: 'selftest',
    label: '确定性自检桩（非真实模型回答，禁止计分）',
    available: process.env.BASELINE_LLM_ALLOW_SELFTEST === '1',
    detail: process.env.BASELINE_LLM_ALLOW_SELFTEST === '1'
      ? 'ENABLED via BASELINE_LLM_ALLOW_SELFTEST=1'
      : 'disabled (set BASELINE_LLM_ALLOW_SELFTEST=1 to enable plumbing tests only)',
    model: 'selftest',
    fabricated: true,
  });

  return out;
}

/** Resolve the provider to use, honouring explicit preference then auto-detect. */
export function resolveProvider(cfg = {}) {
  const all = detectProviders(cfg);
  const prefer = (cfg.llmProvider || process.env.BASELINE_LLM_PROVIDER || 'auto').trim();

  if (prefer && prefer !== 'auto') {
    const hit = all.find((p) => p.id === prefer || p.id === `cli:${prefer}`);
    if (!hit) throw new Error(`unknown LLM provider: ${prefer}`);
    if (!hit.available) throw new Error(`LLM provider not available: ${prefer} (${hit.detail})`);
    return hit;
  }

  // auto: real providers only, never selftest. Prefer a directly-spawnable
  // executable over a Windows shell shim, then follow the preference order.
  const real = all.filter((p) => p.available && !p.fabricated);
  if (!real.length) return null;
  const order = ['openai-compatible', 'cli:claude', 'cli:omp', 'cli:dsh', 'cli:codex', 'cli:opencode', 'cli:gemini', 'cli:qwen'];
  const ranked = order.map((id) => real.find((p) => p.id === id)).filter(Boolean);
  for (const p of real) if (!ranked.includes(p)) ranked.push(p);
  return ranked.find((p) => !p.shellShim) || ranked[0];
}

// --------------------------------------------------------------- invocation

function runCli(cmd, args, { stdinText, timeoutMs, cwd, shell = false }) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      cwd,
      env: { ...process.env },
      windowsHide: true,
      shell,
    });
    let stdout = '';
    let stderr = '';
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { child.kill('SIGKILL'); } catch { /* ignore */ }
      resolve({ code: null, stdout, stderr: stderr + `\n[timeout after ${timeoutMs}ms]`, timedOut: true });
    }, timeoutMs);

    child.stdout?.on('data', (d) => { stdout += d.toString(); });
    child.stderr?.on('data', (d) => { stderr += d.toString(); });
    child.on('error', (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: String(err && err.message), spawnError: true });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });

    if (stdinText != null && child.stdin) {
      child.stdin.write(stdinText);
      child.stdin.end();
    }
  });
}

/**
 * Perform one genuine LLM completion.
 * Returns { ok, text, model, provider, seconds, error?, fabricated }
 */
export async function chat(provider, { system, prompt, timeoutMs = 300000, maxTokens } = {}) {
  const t0 = Date.now();
  if (!provider) {
    return { ok: false, text: '', error: 'no LLM provider available', provider: null, fabricated: false, seconds: 0 };
  }

  const fullPrompt = system ? `${system}\n\n---\n\n${prompt}` : prompt;

  try {
    if (provider.kind === 'selftest') {
      return {
        ok: true,
        text: JSON.stringify({
          top3: ['SELFTEST_SENTINEL_NOT_A_REAL_ANSWER'],
          reasoning: 'Deterministic plumbing self-test. Not a model response; must never be scored.',
        }),
        model: 'selftest',
        provider: provider.id,
        seconds: (Date.now() - t0) / 1000,
        fabricated: true,
      };
    }

    if (provider.kind === 'http') {
      const url = provider.detail.split(' ')[0].replace(/\/$/, '') + '/chat/completions';
      const body = {
        model: provider.model || 'default',
        messages: [
          ...(system ? [{ role: 'system', content: system }] : []),
          { role: 'user', content: prompt },
        ],
        temperature: 0,
      };
      if (maxTokens) body.max_tokens = maxTokens;
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeoutMs);
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${process.env.BASELINE_LLM_API_KEY || ''}`,
        },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      const json = await res.json().catch(() => null);
      if (!res.ok) {
        return {
          ok: false, text: '', provider: provider.id, model: provider.model,
          error: `HTTP ${res.status}: ${JSON.stringify(json).slice(0, 300)}`,
          seconds: (Date.now() - t0) / 1000, fabricated: false,
        };
      }
      const text = json?.choices?.[0]?.message?.content ?? '';
      return {
        ok: Boolean(text), text, provider: provider.id, model: json?.model || provider.model,
        seconds: (Date.now() - t0) / 1000, fabricated: false,
        usage: json?.usage || null,
      };
    }

    if (provider.kind === 'cli') {
      const harnessId = provider.id.replace('cli:', '');
      const spec = CLI_HARNESSES[harnessId];
      if (!spec) throw new Error(`no CLI spec for ${harnessId}`);
      ensureDir(SCRATCH);

      const bin = provider.bin || spec.bin;
      const args = [...spec.args];
      if (spec.disallowTools) args.push('--disallowedTools', ...TOOL_DENY);
      if (provider.model) args.push('--model', provider.model);
      if (spec.promptAsArg) args.push(fullPrompt);

      const r = await runCli(bin, args, {
        stdinText: spec.stdin ? fullPrompt : null,
        timeoutMs,
        cwd: SCRATCH, // neutral cwd: the harness must not ingest this repo's agent instructions
        shell: Boolean(provider.shellShim),
      });

      if (r.timedOut) {
        return {
          ok: false, text: r.stdout, provider: provider.id, model: provider.model || harnessId,
          error: `timeout after ${timeoutMs}ms`, seconds: (Date.now() - t0) / 1000, fabricated: false,
        };
      }
      if (r.code !== 0 || r.spawnError) {
        return {
          ok: false, text: r.stdout, provider: provider.id, model: provider.model || harnessId,
          error: `exit ${r.code}: ${r.stderr.slice(-400)}`,
          seconds: (Date.now() - t0) / 1000, fabricated: false,
        };
      }
      const text = r.stdout.trim();
      return {
        ok: Boolean(text), text, provider: provider.id, model: provider.model || harnessId,
        seconds: (Date.now() - t0) / 1000, fabricated: false,
        stderr_tail: r.stderr.slice(-300) || undefined,
      };
    }

    return { ok: false, text: '', error: `unsupported provider kind: ${provider.kind}`, provider: provider.id, fabricated: false, seconds: 0 };
  } catch (err) {
    return {
      ok: false, text: '', provider: provider?.id || null, model: provider?.model || '',
      error: String(err && err.message ? err.message : err),
      seconds: (Date.now() - t0) / 1000, fabricated: false,
    };
  }
}

/** Extract the first strict-JSON object from a model reply. */
export function extractJson(text) {
  if (!text) return null;
  const cleaned = String(text).replace(/```(?:json)?/gi, '').trim();
  const start = cleaned.indexOf('{');
  if (start < 0) return null;
  let depth = 0;
  for (let i = start; i < cleaned.length; i++) {
    const ch = cleaned[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) {
        try {
          return JSON.parse(cleaned.slice(start, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}
