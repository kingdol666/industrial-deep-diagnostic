// Mock Client — in-process scripted engine (剧本驱动, 无 LLM).
//
// 用途（多 Harness 架构 · mock 卡片）: 联调 / CI / e2e 在没有任何外部 CLI
// 与凭据的机器上全链路跑通平台语义 —— run 创建 → 引擎分发 → 标准事件流 →
// 完成落库 → 报告链接。恒可用（probe: inprocess）。
//
// 剧本: 模拟 9 阶段管线的关键事件形态（system init → 分阶段 assistant 文本 →
// tool_use/tool_result 对 → result success），并写入最小 report.md 使完成
// 路径的 workspace/report 关联与分数解析被真实执行。
// 触发失败剧本: userQuestion 含 "mock:fail" → result error（测试错误路径）。

import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import { WORKSPACE_DIR } from './claude-client.mjs';
import logger from '../utils/logger.mjs';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function mockRunDir(sceneName) {
  const safeScene = String(sceneName || config.diagnosis.default_scene_name).replace(/[^a-zA-Z0-9_一-龥]/g, '_');
  // WORKSPACE_DIR is already absolute (project-root-joined in claude-client).
  const dir = join(WORKSPACE_DIR, `${Date.now()}_${safeScene}`);
  mkdirSync(dir, { recursive: true });
  return dir;
}

function writeMockReport(dir, sceneName) {
  const report = `# 工业深度诊断报告（Mock 引擎剧本）— ${sceneName}

> 本报告由 mock 进程内引擎生成，用于验证平台与引擎之间的集成契约（非真实诊断结论）。

## Pipeline Summary

- Step 0: Setup ✅
- Step 1: Inspect ✅
- Step 2: Context (ontology) ✅
- Step 3: Process analysis ✅
- Step 4: Diagnosis (competing hypotheses) ✅
- Step 5: Judge / Pre-audit ✅
- Step 6: Report ✅
- Step 7: Final audit ✅

## Conclusion

- Type: DETERMINED (mock)
- Confidence: 90 (mock)

Judge Score: 96/100 (ENDORSED)
`;
  writeFileSync(join(dir, 'report.md'), report, 'utf-8');
  writeFileSync(join(dir, '.pipeline_events.jsonl'), [
    JSON.stringify({ ts: new Date().toISOString(), type: 'run_start', source: 'mock-engine' }),
    JSON.stringify({ ts: new Date().toISOString(), type: 'run_end', source: 'mock-engine', verdict: 'ENDORSED' }),
  ].join('\n'), 'utf-8');
}

function createMockQuery({ runId, sceneName, userQuestion, reportLanguage, isResume }) {
  const queue = [];
  let wake = null;
  let closed = false;
  const sessionId = `mock:run:${runId}`;
  const zh = (reportLanguage || config.diagnosis.default_language) === 'zh';
  const shouldFail = /mock:fail/i.test(userQuestion || '');

  const push = (msg) => { queue.push(msg); if (wake) { wake(); wake = null; } };

  const script = (async () => {
    await sleep(30);
    push({
      type: 'system',
      subtype: 'init',
      session_id: sessionId,
      engine: 'mock',
      model: 'mock-scripted',
    });

    let runDir = null;
    if (!isResume) {
      runDir = mockRunDir(sceneName);
      writeMockReport(runDir, sceneName);
      push({ type: 'system', subtype: 'run_dir', data: { runDir: runDir.replace(/\\/g, '/') } });
    }

    const phases = zh
      ? ['Phase 1/3: 读取数据与本体上下文（mock）', 'Phase 2/3: 统计分析 + 竞争性假设评估（mock）', 'Phase 3/3: 生成报告与审计（mock）']
      : ['Phase 1/3: data + ontology context (mock)', 'Phase 2/3: statistics + competing hypotheses (mock)', 'Phase 3/3: report + audit (mock)'];

    for (let i = 0; i < phases.length; i++) {
      if (closed) return;
      push({
        type: 'assistant',
        message: { role: 'assistant', content: [{ type: 'text', text: phases[i] }] },
      });
      const toolId = `mock_tool_${i}`;
      push({
        type: 'assistant',
        message: {
          role: 'assistant',
          content: [{ type: 'tool_use', id: toolId, name: 'Bash', input: { command: `echo "mock pipeline step ${i + 1}"`, description: 'mock tool call' } }],
        },
      });
      await sleep(20);
      push({
        type: 'user',
        message: {
          role: 'user',
          content: [{ type: 'tool_result', tool_use_id: toolId, content: `mock step ${i + 1} ok`, is_error: false }],
        },
      });
    }

    if (closed) return;
    await sleep(20);
    if (shouldFail) {
      push({
        type: 'result',
        subtype: 'error_during_execution',
        duration_ms: 200,
        num_turns: phases.length,
        total_cost_usd: 0,
        stop_reason: 'MOCK_SCRIPTED_FAILURE',
        session_id: sessionId,
      });
      return;
    }
    push({
      type: 'result',
      subtype: 'success',
      duration_ms: 200,
      num_turns: phases.length,
      total_cost_usd: 0,
      stop_reason: 'success',
      session_id: sessionId,
    });
  })();

  script.catch((e) => {
    logger.error(`mock engine script error: ${e.message}`, { context: 'MockClient', runId });
    push({
      type: 'result',
      subtype: 'error_during_execution',
      duration_ms: 0,
      num_turns: 0,
      total_cost_usd: 0,
      stop_reason: `mock_script_error: ${e.message}`,
      session_id: sessionId,
    });
  });

  return {
    engine: 'mock',
    sessionId,
    close() { closed = true; if (wake) { wake(); wake = null; } },
    get killed() { return closed; },
    async *[Symbol.asyncIterator]() {
      while (true) {
        if (queue.length > 0) {
          yield queue.shift();
          continue;
        }
        if (closed) return;
        await new Promise((resolve) => { wake = resolve; });
      }
    },
  };
}

// ── Standard engine client module shape ──
export function startDiagnosis({
  analysisTarget, userQuestion, sceneName, runId,
  maxTurns = 0, timeoutMinutes = 0, reportLanguage,
  followUpMessage, sessionId = null, ontology = null, enhancement = null,
}) {
  void analysisTarget; void maxTurns; void timeoutMinutes;
  void ontology; void enhancement; void followUpMessage;
  const isResume = typeof sessionId === 'string' && sessionId.startsWith('mock:');
  const query = createMockQuery({ runId, sceneName, userQuestion, reportLanguage, isResume });
  return {
    query,
    dataPaths: [],
    prompt: userQuestion || '(mock)',
    getSessionId: () => query.sessionId,
    runId,
    isResume,
  };
}

export function startSessionChat({ runId, sessionId, message }) {
  if (typeof sessionId !== 'string' || !sessionId.startsWith('mock:')) {
    const err = new Error(`No valid mock session ID (session id: ${sessionId || 'none'})`);
    err.status = 400;
    throw err;
  }
  const queue = [];
  let wake = null;
  let closed = false;
  const push = (msg) => { queue.push(msg); if (wake) { wake(); wake = null; } };

  (async () => {
    await sleep(20);
    push({ type: 'system', subtype: 'init', session_id: sessionId, engine: 'mock', model: 'mock-scripted' });
    push({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: `(mock) 已收到消息: ${String(message || '').slice(0, 200)}` }] } });
    push({
      type: 'result', subtype: 'success', duration_ms: 30, num_turns: 1,
      total_cost_usd: 0, stop_reason: 'success', session_id: sessionId,
    });
  })();

  return {
    query: {
      engine: 'mock',
      sessionId,
      close() { closed = true; if (wake) { wake(); wake = null; } },
      get killed() { return closed; },
      async *[Symbol.asyncIterator]() {
        while (true) {
          if (queue.length > 0) { yield queue.shift(); continue; }
          if (closed) return;
          await new Promise((resolve) => { wake = resolve; });
        }
      },
    },
    runId,
    sessionId,
  };
}

export function parseStreamEvent(message) {
  if (!message || typeof message !== 'object') return null;
  return message;
}

export function registerChild() { /* in-process — no registry needed */ }
export function closeQuery() { /* in-process — nothing to kill */ }
