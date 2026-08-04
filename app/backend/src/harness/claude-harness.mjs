// ClaudeHarness — implements the Harness interface over the built-in
// Claude Code SDK engine (live real-time diagnosis + session chat).
//
// This is the original engine the console was built around: it STARTS
// diagnoses via the Claude Agent SDK and streams events over SSE/WebSocket.
// The harness wrapper keeps the console's engine-agnostic routing while the
// live machinery stays in engine/claude-client.mjs untouched.

import { BaseHarness } from './base.mjs';
import { existsSync } from 'fs';
import { createRequire } from 'module';

// Probe SDK availability without importing at module top (SDK is optional —
// the server must boot even without it, e.g. when only OMP runs are browsed).
function probeSdk() {
  try {
    const require = createRequire(import.meta.url);
    require.resolve('@anthropic-ai/claude-agent-sdk');
    return true;
  } catch {
    return false;
  }
}

export class ClaudeHarness extends BaseHarness {
  id = 'claude';
  name = 'Claude Code';
  kind = 'live';
  description = 'Claude Code SDK 实时诊断引擎';
  capabilities = ['live', 'chat'];

  async health() {
    const sdkOk = probeSdk();
    return {
      available: sdkOk,
      meta: {
        engine: 'claude-agent-sdk',
        sdk_installed: sdkOk,
        note: sdkOk ? 'SDK ready — live diagnoses available' : 'SDK 未安装 — 只能浏览 OMP 运行或安装 @anthropic-ai/claude-agent-sdk',
      },
    };
  }

  async startDiagnosis(params) {
    // Lazy import so the server boots without the SDK installed.
    const mod = await import('../engine/claude-client.mjs');
    return mod.startDiagnosis(params);
  }
}
