<template>
  <div class="message-stream" ref="streamEl" @scroll="handleScroll">
    <div v-if="!connected && isRunning" class="ms-connecting">
      <div class="spinner-sm"></div>
      <span>正在连接诊断引擎...</span>
    </div>

    <template v-for="(item, i) in renderedItems" :key="item.key || i">
      <div v-if="item.kind === 'thinking'" class="ms-item ms-thinking">
        <div class="ms-rail"><div class="ms-dot dot-purple"></div></div>
        <div class="ms-body">
          <div class="ms-card card-thinking" @click="toggleThinking(item)">
            <div class="ms-card-header">
              <span class="ms-card-icon">🧠</span>
              <span class="ms-card-title">Claude 思考中</span>
              <span class="ms-card-toggle" :class="{ open: expandedThinking.has(item.key) }">▶</span>
            </div>
            <div v-if="expandedThinking.has(item.key)" class="ms-thinking-content">{{ item.content }}</div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'assistant'" class="ms-item ms-msg chat-row assistant-row">
        <div class="ms-rail"><div class="ms-dot dot-blue"></div></div>
        <div class="ms-body">
          <div class="chat-message-wrap">
            <div class="chat-avatar assistant-avatar">C</div>
            <div class="chat-bubble assistant-bubble">
              <div class="chat-name">Claude</div>
              <div class="msg-content" v-html="renderMd(item.content)"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'user'" class="ms-item ms-user chat-row user-row">
        <div class="ms-rail"><div class="ms-dot dot-green"></div></div>
        <div class="ms-body">
          <div class="chat-message-wrap">
            <div class="chat-bubble user-bubble">
              <div class="chat-name">你</div>
              <div class="msg-content" v-html="renderMd(item.content)"></div>
            </div>
            <div class="chat-avatar user-avatar">你</div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'tool'" class="ms-item ms-tool">
        <div class="ms-rail"><div class="ms-dot" :class="toolDotClass(item.name)"></div></div>
        <div class="ms-body">
          <div class="ms-card card-tool" :class="['tool-' + toolCategory(item.name), item.result ? 'tool-complete' : 'tool-running']">
            <div class="ms-card-header">
              <span class="ms-tool-badge">{{ item.title }}</span>
              <span class="ms-tool-id" v-if="item.shortId">{{ item.shortId }}</span>
              <span class="tool-state" :class="item.result?.isError ? 'tool-state-error' : 'tool-state-ok'">
                {{ item.result ? (item.result.isError ? '失败' : '完成') : '执行中' }}
              </span>
            </div>
            <div class="tool-summary">{{ item.summary }}</div>
            <div class="ms-tool-input">
              <template v-if="item.preview">
                <code>{{ item.preview }}</code>
              </template>
            </div>
            <div v-if="item.result?.summary" :class="['ms-result-card tool-result-inline', item.result.isError ? 'result-err' : 'result-ok']">
              <span class="result-icon">{{ item.result.isError ? '✗' : '✓' }}</span>
              <span class="result-text">{{ item.result.summary }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'subagent'" class="ms-item ms-progress">
        <div class="ms-rail"><div class="ms-dot dot-cyan"></div></div>
        <div class="ms-body">
          <div class="ms-card card-progress" :class="'progress-' + (item.status || 'running')">
            <div class="ms-card-header">
              <span class="ms-card-icon">{{ statusIcon(item.status) }}</span>
              <span class="ms-card-title">{{ item.title }}</span>
              <span class="stage-chip" :class="'stage-' + item.stage.tone">{{ item.stage.label }}</span>
              <span :class="['progress-badge', 'badge-' + statusBadgeClass(item.status)]">{{ item.statusLabel }}</span>
            </div>
            <div class="progress-detail" v-if="item.step">
              <span class="progress-step">{{ item.step }}</span>
            </div>
            <div class="progress-bar-wrapper" v-if="item.progress">
              <div class="progress-bar"><div class="progress-fill" :style="{ width: progressPercent(item.progress) + '%' }"></div></div>
              <span class="progress-text">{{ progressText(item.progress) }}</span>
            </div>
            <div v-if="item.highlights.length" class="sa-events">
              <div v-for="(entry, index) in item.highlights" :key="index" class="sa-event">
                <span class="sa-icon">{{ entry.icon }}</span>
                <span class="sa-label">{{ entry.label }}</span>
                <span class="sa-fallback-preview">{{ entry.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'question'" class="ms-item ms-question">
        <div class="ms-rail"><div class="ms-dot dot-purple"></div></div>
        <div class="ms-body">
          <div class="ms-card card-question">
            <div class="ms-card-header">
              <span class="ms-card-icon">❓</span>
              <span class="ms-card-title">需要你的回答</span>
              <span class="ms-question-count" v-if="item.questions?.length">共 {{ item.questions.length }} 题</span>
            </div>
            <div class="question-list">
              <div v-for="(q, qi) in item.questions" :key="qi" class="question-block">
                <div class="question-header" v-if="q.header"><span class="q-chip">{{ q.header }}</span></div>
                <div class="question-text"><span class="question-num">{{ qi + 1 }}.</span>{{ q.question }}</div>
                <div class="question-options">
                  <div v-for="(opt, oi) in q.options" :key="oi" class="question-option">
                    <span class="option-marker">{{ q.multiSelect ? '☐' : '○' }}</span>
                    <div class="option-info">
                      <span class="option-label">{{ opt.label }}</span>
                      <span class="option-desc" v-if="opt.description">{{ opt.description }}</span>
                      <div class="option-preview" v-if="opt.preview">
                        <div class="option-preview-chip">👁 预览</div>
                        <div class="option-preview-content" v-html="renderMd(opt.preview)"></div>
                      </div>
                    </div>
                  </div>
                  <div v-if="!q.options || q.options.length === 0" class="question-option question-option-empty">
                    <span class="option-marker">—</span>
                    <span class="option-label">自由文本输入</span>
                  </div>
                </div>
                <div class="question-type-badge" v-if="q.multiSelect">多选</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'system'" class="ms-item ms-sys">
        <div class="ms-rail"><div class="ms-dot" :class="systemDotClass(item.level)"></div></div>
        <div class="ms-body">
          <div class="ms-sys-card" :class="'sys-' + item.level">
            <strong><span class="sys-icon">{{ systemIcon(item.level) }}</span>{{ item.title }}</strong>
            <span v-if="item.text"> · {{ item.text }}</span>
            <div v-if="item.details?.length" class="sys-details">
              <span v-for="(detail, di) in item.details" :key="di" class="sys-detail-chip">{{ detail }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'stats'" class="ms-item ms-stats">
        <div class="ms-rail"><div class="ms-dot dot-yellow"></div></div>
        <div class="ms-body">
          <div class="ms-stats-card">
            <div class="stat-item"><span class="stat-val">{{ item.numTurns }}</span><span class="stat-lbl">轮次</span></div>
            <div class="stat-item"><span class="stat-val">{{ formatDuration(item.durationMs) }}</span><span class="stat-lbl">耗时</span></div>
            <div class="stat-item"><span class="stat-val">${{ (item.totalCost || 0).toFixed(4) }}</span><span class="stat-lbl">成本</span></div>
            <div class="stat-item" v-if="item.stopReason"><span class="stat-val">{{ item.stopReason }}</span><span class="stat-lbl">原因</span></div>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'complete'" class="ms-item ms-complete">
        <div class="ms-rail"><div class="ms-dot" :class="item.status === 'failed' ? 'dot-red' : 'dot-green'"></div></div>
        <div class="ms-body">
          <div :class="['ms-result-card', item.status === 'failed' ? 'result-err' : 'result-ok']">
            <span class="result-icon">{{ item.status === 'failed' ? '✗' : '✓' }}</span>
            <span class="result-text">{{ item.text }}</span>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'error'" class="ms-item ms-error">
        <div class="ms-rail"><div class="ms-dot dot-red"></div></div>
        <div class="ms-body">
          <div class="ms-card card-hitl">
            <div class="hitl-warn">⚠ 运行时错误</div>
            <code class="hitl-cmd">{{ item.text }}</code>
          </div>
        </div>
      </div>

      <div v-else-if="item.kind === 'hitl'" class="ms-item ms-hitl">
        <div class="ms-rail"><div class="ms-dot dot-red pulse"></div></div>
        <div class="ms-body">
          <div class="ms-card card-hitl">
            <div class="hitl-warn">⚠ 高风险命令：{{ item.riskDesc }}</div>
            <code class="hitl-cmd">{{ item.command }}</code>
          </div>
        </div>
      </div>
    </template>

    <div v-if="isRunning && connected" class="ms-item ms-typing">
      <div class="ms-rail"><div class="ms-dot dot-blue pulse"></div></div>
      <div class="ms-body">
        <div class="typing-indicator"><span></span><span></span><span></span></div>
      </div>
    </div>

    <div ref="bottomSentinel" class="ms-bottom-sentinel" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onBeforeUpdate, onMounted, onUpdated } from 'vue';
import { renderMarkdown } from '../../utils/markdown.js';

const props = defineProps({
  events: { type: Array, default: () => [] },
  isRunning: { type: Boolean, default: false },
  connected: { type: Boolean, default: false },
});

const expandedThinking = ref(new Set());
const streamEl = ref(null);
const bottomSentinel = ref(null);
const MAX_ITEMS = 300;
const autoScrollPinned = ref(true);
const pendingAutoScroll = ref(true);
let resizeObserver = null;
let scrollFrame = null;

const renderedItems = computed(() => {
  const items = [];
  const toolMap = new Map();
  const subagentMap = new Map();
  const systemMap = new Map();

  for (const ev of props.events || []) {
    if (!ev) continue;

    if (ev.type === 'message' && ev.data?.content) {
      const prev = items[items.length - 1];
      if (prev?.kind === 'assistant') {
        prev.content = `${prev.content}\n\n${ev.data.content}`;
      } else {
        items.push({
          kind: 'assistant',
          key: `msg:${ev._seq}`,
          content: ev.data.content,
        });
      }
      continue;
    }

    if (ev.type === 'user_message' && ev.data?.content) {
      items.push({
        kind: 'user',
        key: `user:${ev._seq}`,
        content: ev.data.content,
      });
      continue;
    }

    if (ev.type === 'thinking' && ev.data?.content) {
      const prev = items[items.length - 1];
      if (prev?.kind === 'thinking') {
        prev.content = `${prev.content}\n\n${ev.data.content}`;
      } else {
        items.push({
          kind: 'thinking',
          key: `thinking:${ev._seq}`,
          content: ev.data.content,
        });
      }
      continue;
    }

    if (ev.type === 'tool_use') {
      const item = {
        kind: 'tool',
        key: `tool:${ev.data?.id || ev._seq}`,
        toolId: ev.data?.id || null,
        name: ev.data?.name || 'Tool',
        title: toolTitle(ev.data?.name),
        shortId: ev.data?.id?.slice(0, 8) || '',
        summary: toolSummary(ev.data?.name),
        preview: toolPreview(ev.data?.name, ev.data?.input),
        result: null,
      };
      toolMap.set(item.toolId, item);
      items.push(item);
      continue;
    }

    if (ev.type === 'tool_result') {
      const matched = toolMap.get(ev.data?.toolUseId);
      if (matched) {
        const isQuestionTool = matched.name === 'AskUserQuestion';
        const rawSummary = ev.data?.summary || '';
        const looksLikeQuestionAck = isQuestionTool && /answer questions\??/i.test(rawSummary);
        matched.result = looksLikeQuestionAck
          ? { summary: '问题已发出，等待回答。', isError: false }
          : { summary: rawSummary, isError: !!ev.data?.isError };
      } else {
        items.push({
          kind: 'tool',
          key: `tool-result:${ev._seq}`,
          toolId: ev.data?.toolUseId || null,
          name: 'Tool Result',
          title: '工具结果',
          shortId: ev.data?.toolUseId?.slice?.(0, 8) || '',
          summary: '工具执行已结束',
          preview: '',
          result: { summary: ev.data?.summary || '', isError: !!ev.data?.isError },
        });
      }
      continue;
    }

    if (ev.type === 'task_progress' || ev.type === 'stream_event') {
      const subagent = normalizeSubagentEvent(ev);
      if (subagent) {
        const key = subagent.id || `subagent:${subagent.title}`;
        const existing = subagentMap.get(key);
        if (existing) {
          existing.status = subagent.status || existing.status;
          existing.statusLabel = subagent.statusLabel || existing.statusLabel;
          existing.step = subagent.step || existing.step;
          existing.progress = subagent.progress ?? existing.progress;
          if (subagent.highlights.length) existing.highlights = dedupeHighlights([...existing.highlights, ...subagent.highlights]).slice(-8);
        } else {
          subagentMap.set(key, subagent);
          items.push(subagent);
        }
        continue;
      }
    }

    if (ev.type === 'question') {
      items.push({
        kind: 'question',
        key: `question:${ev.data?.questionId || ev._seq}`,
        questions: ev.data?.questions || [],
      });
      continue;
    }

    if (ev.type === 'system') {
      const systemItem = normalizeSystemEvent(ev);
      if (systemItem) {
        if (systemItem.aggregateKey) {
          const existing = systemMap.get(systemItem.aggregateKey);
          if (existing) {
            mergeSystemItem(existing, systemItem);
          } else {
            systemMap.set(systemItem.aggregateKey, systemItem);
            items.push(systemItem);
          }
        } else {
          items.push(systemItem);
        }
      }
      continue;
    }

    if (ev.type === 'stats') {
      items.push({
        kind: 'stats',
        key: `stats:${ev._seq}`,
        numTurns: ev.data?.numTurns || 0,
        durationMs: ev.data?.durationMs || 0,
        totalCost: ev.data?.totalCost || 0,
        stopReason: ev.data?.stopReason || '',
      });
      continue;
    }

    if (ev.type === 'complete') {
      items.push({
        kind: 'complete',
        key: `complete:${ev._seq}`,
        status: ev.data?.status || 'completed',
        text: ev.data?.status === 'failed'
          ? `诊断失败：${ev.data?.error || ''}`
          : ev.data?.status === 'stopped'
            ? '诊断已停止'
            : `诊断已完成${ev.data?.verdict ? ` · 结论：${ev.data.verdict}` : ''}${ev.data?.score != null ? ` · 评分：${ev.data.score}` : ''}`,
      });
      continue;
    }

    if (ev.type === 'error') {
      items.push({
        kind: 'error',
        key: `error:${ev._seq}`,
        text: ev.data?.error || 'Unknown runtime error',
      });
      continue;
    }

    if (ev.type === 'hitl_request') {
      items.push({
        kind: 'hitl',
        key: `hitl:${ev.data?.hitlId || ev._seq}`,
        command: ev.data?.command || '',
        riskDesc: ev.data?.riskDesc || 'Dangerous command',
      });
    }
  }

  if (items.length <= MAX_ITEMS) return items;
  return items.slice(-MAX_ITEMS);
});

function toggleThinking(item) {
  const next = new Set(expandedThinking.value);
  if (next.has(item.key)) next.delete(item.key);
  else next.add(item.key);
  expandedThinking.value = next;
}

function renderMd(text) {
  return renderMarkdown(text);
}

function toolCategory(name) {
  if (['Read', 'Glob'].includes(name)) return 'read';
  if (['Write', 'Edit', 'NotebookEdit'].includes(name)) return 'write';
  if (name === 'Bash') return 'bash';
  if (['WebSearch', 'WebFetch'].includes(name)) return 'web';
  if (['Skill', 'Agent', 'AskUserQuestion'].includes(name)) return 'skill';
  return 'default';
}

function toolDotClass(name) {
  const map = {
    Read: 'dot-blue', Glob: 'dot-blue', Bash: 'dot-yellow', Write: 'dot-green',
    Edit: 'dot-green', Skill: 'dot-purple', Agent: 'dot-purple', WebSearch: 'dot-cyan', WebFetch: 'dot-cyan',
    AskUserQuestion: 'dot-purple',
  };
  return map[name] || 'dot-blue';
}

function toolTitle(name) {
  const map = {
    Read: '读取文件',
    Glob: '搜索文件',
    Write: '写入文件',
    Edit: '编辑文件',
    NotebookEdit: '编辑 notebook',
    Bash: '执行命令',
    WebSearch: '搜索网络',
    WebFetch: '抓取网页',
    Skill: '调用技能',
    Agent: '启动子代理',
    AskUserQuestion: '准备提问',
  };
  return map[name] || (name || '执行工具');
}

function toolSummary(name) {
  const map = {
    Read: '正在检查源码或数据内容。',
    Glob: '正在定位匹配的文件或模式。',
    Write: '正在创建或覆盖文件内容。',
    Edit: '正在修补已有内容。',
    NotebookEdit: '正在更新 notebook 单元或文件。',
    Bash: '正在执行 shell 命令。',
    WebSearch: '正在收集外部信息。',
    WebFetch: '正在打开远程页面。',
    Skill: '正在委托专业技能执行。',
    Agent: '正在启动并跟踪后台子任务。',
    AskUserQuestion: '正在暂停并等待结构化用户输入。',
  };
  return map[name] || '正在调用外部工具。';
}

function toolPreview(name, input) {
  if (!input) return '';
  if (name === 'Bash') return input.command || '';
  if (name === 'Read' || name === 'Write' || name === 'Edit' || name === 'NotebookEdit') return input.file_path || '';
  if (name === 'Glob') return input.pattern || '';
  if (name === 'WebSearch') return input.query || '';
  if (name === 'WebFetch') return input.url || input.query || '';
  if (name === 'Skill') return input.skill || input.args || '';
  if (name === 'Agent') return input.description || input.name || input.subagent_type || '';
  if (name === 'AskUserQuestion') return `已准备 ${input.questions?.length || 0} 个问题`;
  try {
    return JSON.stringify(input).slice(0, 200);
  } catch {
    return String(input).slice(0, 200);
  }
}

function normalizeSubagentEvent(ev) {
  const data = ev.data || {};
  if (ev.type === 'stream_event' && shouldHideRawStreamEvent(ev)) {
    return null;
  }
  const baseTitle = data.agentName || data.name || data.task?.name || inferSubagentTitleFromStream(data) || '子代理';
  const status = data.status || data.task?.status || inferStatusFromStream(data) || 'running';
  const highlights = extractHighlights(data.events || [data]);
  const stage = inferSubagentStage(baseTitle, data, highlights);
  return {
    kind: 'subagent',
    key: `subagent:${ev._seq}:${baseTitle}`,
    id: data.taskId || data.task?.id || data.id || baseTitle,
    title: baseTitle,
    status,
    statusLabel: humanizeStatus(status),
    step: data.currentStep || data.message || data.current_step || inferStepFromStream(data),
    progress: data.progress || null,
    highlights,
    stage,
  };
}

function normalizeSystemEvent(ev) {
  const subtype = ev.subtype || ev.data?.subtype || 'system';
  if (subtype === 'status') return null;
  if (subtype === 'init') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey: 'system:init',
      title: '诊断引擎已初始化',
      text: `模型 ${ev.data?.model || 'unknown'} · ${ev.data?.tools?.length || 0} 个工具 · 权限 ${ev.data?.permissionMode || 'default'}`,
      level: 'important',
      details: [],
    };
  }
  if (subtype === 'continue') {
    return { kind: 'system', key: `system:${ev._seq}`, title: '继续当前运行', text: ev.data?.message || '诊断流程已恢复。', level: 'important', details: [] };
  }
  if (subtype === 'chat_sent') {
    return { kind: 'system', key: `system:${ev._seq}`, title: '已发送补充说明', text: (ev.data?.message || '').slice(0, 200), level: 'normal', details: [] };
  }
  if (subtype === 'chat_error') {
    return { kind: 'system', key: `system:${ev._seq}`, title: '补充说明发送失败', text: ev.data?.error || '未知聊天错误', level: 'warning', details: [] };
  }
  if (subtype === 'session_chat') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      title: '会话消息已发送',
      text: ev.data?.message || '已发送到当前 Claude session。',
      level: 'normal',
      details: [],
    };
  }
  if (subtype === 'task_started') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey: `task:${ev.data?.task_id || ev._seq}`,
      title: '后台任务已启动',
      text: ev.data?.description || ev.data?.task_id || '',
      level: 'important',
      details: [ev.data?.subagent_type || ev.data?.task_type || ''].filter(Boolean),
    };
  }
  if (subtype === 'task_updated') {
    return null;
  }
  if (subtype === 'task_progress') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey: `task:${ev.data?.task_id || ev._seq}`,
      title: '后台任务进行中',
      text: ev.data?.description || ev.data?.summary || '',
      level: 'normal',
      details: [ev.data?.subagent_type || ev.data?.task_type || ''].filter(Boolean),
    };
  }
  if (subtype === 'task_notification') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey: `task-note:${ev.data?.task_id || ev._seq}`,
      title: ev.data?.status === 'completed' ? '后台任务已完成' : '后台任务通知',
      text: ev.data?.summary || ev.data?.description || '',
      level: ev.data?.status === 'completed' ? 'important' : 'normal',
      details: [ev.data?.subagent_type || ev.data?.task_type || ''].filter(Boolean),
    };
  }
  if (subtype.startsWith('hook_')) {
    return normalizeHookSystemEvent(ev, subtype);
  }
  return {
    kind: 'system',
    key: `system:${ev._seq}`,
    title: humanizeLabel(subtype),
    text: summarizeSystemPayload(ev.data),
    level: inferSystemLevel(subtype, ev.data),
    details: [],
  };
}

function normalizeHookSystemEvent(ev, subtype) {
  const hookName = ev.data?.hook_name || 'system hook';
  const hookEvent = ev.data?.hook_event || '';
  const aggregateKey = `hook:${hookName}`;
  if (subtype === 'hook_started') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey,
      title: '系统钩子执行中',
      text: `${hookName}${hookEvent ? ` · ${hookEvent}` : ''}`,
      hookState: 'running',
      level: 'normal',
      details: [],
    };
  }
  if (subtype === 'hook_progress') {
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey,
      title: '系统钩子执行中',
      text: `${hookName}${hookEvent ? ` · ${hookEvent}` : ''}`,
      hookState: 'running',
      level: 'normal',
      details: collectHookDetails(ev.data),
    };
  }
  if (subtype === 'hook_response') {
    const outcome = ev.data?.outcome || (ev.data?.exit_code === 0 ? 'success' : 'finished');
    return {
      kind: 'system',
      key: `system:${ev._seq}`,
      aggregateKey,
      title: outcome === 'success' ? '系统钩子已完成' : '系统钩子已结束',
      text: `${hookName}${hookEvent ? ` · ${hookEvent}` : ''}`,
      hookState: outcome,
      level: outcome === 'success' ? 'normal' : 'important',
      details: collectHookDetails(ev.data),
    };
  }
  return {
    kind: 'system',
    key: `system:${ev._seq}`,
    aggregateKey,
    title: '系统钩子',
    text: `${hookName}${hookEvent ? ` · ${hookEvent}` : ''}`,
    hookState: 'running',
    level: 'normal',
    details: collectHookDetails(ev.data),
  };
}

function mergeSystemItem(existing, incoming) {
  existing.title = incoming.title || existing.title;
  existing.text = incoming.text || existing.text;
  existing.hookState = incoming.hookState || existing.hookState;
  const merged = [...(existing.details || []), ...(incoming.details || [])];
  existing.details = dedupeTextList(merged).slice(-3);
}

function collectHookDetails(data) {
  const details = [];
  const metrics = extractHookMetrics(data);
  if (metrics) details.push(metrics);
  const outcome = extractHookOutcome(data);
  if (outcome) details.push(outcome);
  return details;
}

function extractHookMetrics(data) {
  const raw = [data?.stdout, data?.output].filter(Boolean).join('\n');
  const match = raw.match(/sdk_bootstrap_ms\":\s*(\d+)/) || raw.match(/\"pv\":\s*(\d+)/);
  if (match) {
    if (raw.includes('sdk_bootstrap_ms')) {
      const ms = raw.match(/sdk_bootstrap_ms\":\s*(\d+)/)?.[1];
      return ms ? `引导 ${ms}ms` : '';
    }
    if (raw.includes('"pv"')) {
      const pv = raw.match(/\"pv\":\s*(\d+)/)?.[1];
      return pv ? `上下文 ${pv}` : '';
    }
  }
  return '';
}

function extractHookOutcome(data) {
  if (data?.outcome) return humanizeLabel(data.outcome);
  if (typeof data?.exit_code === 'number') return `退出码 ${data.exit_code}`;
  return '';
}

function shouldHideRawStreamEvent(ev) {
  const subtype = ev?.subtype || ev?.data?.type || '';
  return [
    'content_block_delta',
    'content_block_start',
    'content_block_stop',
    'message_delta',
    'message_start',
    'message_stop',
    'signature_delta',
  ].includes(subtype);
}

function dedupeTextList(list) {
  const seen = new Set();
  return list.filter((item) => {
    if (!item) return false;
    if (seen.has(item)) return false;
    seen.add(item);
    return true;
  });
}

function summarizeSystemPayload(value) {
  if (!value || typeof value !== 'object') return summarizeAny(value);
  const filtered = {};
  for (const [key, val] of Object.entries(value)) {
    if (['stdout', 'stderr', 'output', 'additionalContext'].includes(key)) continue;
    if (val == null || val === '') continue;
    filtered[key] = val;
  }
  return summarizeAny(filtered);
}

function inferSystemLevel(subtype, data) {
  if (String(subtype).includes('error')) return 'warning';
  if (String(subtype).includes('init') || String(subtype).includes('continue')) return 'important';
  if (data?.outcome && data.outcome !== 'success') return 'warning';
  return 'normal';
}

function inferSubagentStage(title, data, highlights) {
  const haystack = [
    title,
    data?.currentStep,
    data?.message,
    ...(highlights || []).map(h => `${h.label} ${h.text}`),
  ].filter(Boolean).join(' ').toLowerCase();

  if (/(read|load|inspect|parse|csv|excel|json|schema|browse|file)/.test(haystack)) {
    return { key: 'data', label: '读数据', tone: 'blue' };
  }
  if (/(plot|chart|figure|visual|trend|draw|graph|heatmap)/.test(haystack)) {
    return { key: 'visual', label: '画图', tone: 'cyan' };
  }
  if (/(reason|diagnos|root cause|infer|physics|ontology|hypothesis|analysis)/.test(haystack)) {
    return { key: 'reason', label: '推理', tone: 'purple' };
  }
  if (/(report|summary|write report|markdown|output|deliverable)/.test(haystack)) {
    return { key: 'report', label: '报告', tone: 'green' };
  }
  return { key: 'general', label: '处理中', tone: 'gray' };
}

function systemIcon(level) {
  return level === 'warning' ? '⚠ ' : level === 'important' ? '✦ ' : 'ℹ ';
}

function systemDotClass(level) {
  if (level === 'warning') return 'dot-red';
  if (level === 'important') return 'dot-yellow';
  return 'dot-gray';
}

function extractHighlights(events) {
  return dedupeHighlights((events || []).map((entry) => {
    if (!entry) return null;
    if (['content_block_delta', 'content_block_start', 'content_block_stop', 'message_delta', 'message_start', 'message_stop', 'signature_delta'].includes(entry.type)) {
      return null;
    }
    if (entry.type === 'thinking') return { icon: '🧠', label: '思考', text: summarizeAny(entry.thinking || entry.content) };
    if (entry.type === 'message' || entry.type === 'text') return { icon: '💬', label: '消息', text: summarizeAny(entry.content || entry.text) };
    if (entry.type === 'tool_use') return { icon: '⚙️', label: entry.name || 'Tool', text: toolPreview(entry.name, entry.input) };
    if (entry.type === 'tool_result') return { icon: entry.is_error ? '✗' : '✓', label: '结果', text: summarizeAny(entry.summary || entry.content || entry.text) };
    if (entry.type === 'task_progress') return { icon: '🔄', label: entry.name || entry.task?.name || '任务', text: entry.message || entry.current_step || entry.status || '' };
    return { icon: '📡', label: humanizeLabel(entry.type || 'event'), text: summarizeAny(entry) };
  }).filter(Boolean)).slice(-6);
}

function dedupeHighlights(entries) {
  const seen = new Set();
  return entries.filter((entry) => {
    const key = `${entry.icon}:${entry.label}:${entry.text}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function inferSubagentTitleFromStream(data) {
  if (data?.type === 'tool_use') return '子代理工具动作';
  if (data?.type === 'tool_result') return '子代理工具结果';
  if (data?.type === 'thinking') return '子代理推理';
  if (data?.type === 'message' || data?.type === 'text') return '子代理更新';
  return '';
}

function inferStatusFromStream(data) {
  if (data?.type === 'tool_result' && data?.is_error) return 'failed';
  return 'running';
}

function inferStepFromStream(data) {
  if (data?.type === 'tool_use') return `${data.name || '工具'} 执行中`;
  if (data?.type === 'tool_result') return `${data.is_error ? '工具失败' : '工具完成'}`;
  if (data?.type === 'message' || data?.type === 'text') return summarizeAny(data.content || data.text);
  if (data?.type === 'thinking') return '正在推理下一步';
  return '';
}

function summarizeAny(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value.slice(0, 180);
  if (Array.isArray(value)) {
    return value.map((v) => summarizeAny(v)).join(' ').slice(0, 180);
  }
  if (typeof value === 'object') {
    if (typeof value.text === 'string') return value.text.slice(0, 180);
    if (typeof value.content === 'string') return value.content.slice(0, 180);
    try {
      return JSON.stringify(value).slice(0, 180);
    } catch {
      return String(value).slice(0, 180);
    }
  }
  return String(value).slice(0, 180);
}

function humanizeStatus(status) {
  const map = {
    running: '运行中',
    in_progress: '运行中',
    awaiting_input: '等待回答',
    completed: '已完成',
    failed: '失败',
    pending: '待执行',
    stopped: '已停止',
  };
  return map[status] || '运行中';
}

function humanizeLabel(text) {
  const label = String(text || 'event')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
  const map = {
    Success: '成功',
    Error: '错误',
    Finished: '结束',
    Event: '事件',
    Requesting: '请求中',
    Status: '状态',
    'Task Progress': '任务进展',
    'Task Started': '任务启动',
  };
  return map[label] || label;
}

function formatDuration(ms) {
  if (!ms) return '0s';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

function statusIcon(status) {
  const map = {
    running: '🔄', in_progress: '🔄', completed: '✅', failed: '❌',
    pending: '⏳', stopped: '⏹', awaiting_input: '❓',
  };
  return map[status] || '📌';
}

function statusBadgeClass(status) {
  const map = {
    running: 'blue', in_progress: 'blue', completed: 'green',
    failed: 'red', pending: 'yellow', stopped: 'yellow', awaiting_input: 'purple',
  };
  return map[status] || 'blue';
}

function progressPercent(progress) {
  if (!progress) return 0;
  if (typeof progress === 'number') return Math.min(100, Math.max(0, progress));
  if (progress.completed != null && progress.total) return Math.min(100, Math.round((progress.completed / progress.total) * 100));
  return 0;
}

function progressText(progress) {
  if (!progress) return '';
  if (typeof progress === 'number') return `${progress}%`;
  if (progress.completed != null && progress.total) return `${progress.completed}/${progress.total}`;
  return '';
}

function isPinnedToBottom() {
  const el = streamEl.value;
  if (!el) return true;
  return el.scrollHeight - el.scrollTop - el.clientHeight < 48;
}

function scrollToLatest(behavior = 'auto') {
  const el = streamEl.value;
  if (!el) return;
  if (scrollFrame) cancelAnimationFrame(scrollFrame);
  scrollFrame = requestAnimationFrame(() => {
    const sentinel = bottomSentinel.value;
    if (sentinel?.scrollIntoView) {
      sentinel.scrollIntoView({ block: 'end', behavior });
    } else {
      el.scrollTo({ top: el.scrollHeight, behavior });
    }
    scrollFrame = null;
  });
}

function handleScroll() {
  autoScrollPinned.value = isPinnedToBottom();
}

onBeforeUpdate(() => {
  pendingAutoScroll.value = isPinnedToBottom();
});

onUpdated(() => {
  if (!pendingAutoScroll.value) return;
  scrollToLatest('auto');
  autoScrollPinned.value = true;
});

onMounted(() => {
  scrollToLatest('auto');
  if (typeof ResizeObserver !== 'undefined' && streamEl.value) {
    resizeObserver = new ResizeObserver(() => {
      if (!autoScrollPinned.value && !isPinnedToBottom()) return;
      scrollToLatest('auto');
    });
    resizeObserver.observe(streamEl.value);
  }
});

onBeforeUnmount(() => {
  if (scrollFrame) {
    cancelAnimationFrame(scrollFrame);
    scrollFrame = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
});
</script>

<style scoped>
.message-stream {
  background:
    radial-gradient(circle at 10% 0%, rgba(88, 166, 255, .06), transparent 32%),
    linear-gradient(180deg, rgba(13, 17, 23, .88), rgba(13, 17, 23, .96));
  border: 1px solid rgba(139, 148, 158, .14);
  border-radius: 18px;
  padding: 18px clamp(14px, 3vw, 34px);
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  min-height: 200px;
}
.ms-bottom-sentinel {
  width: 100%;
  height: 1px;
}
.ms-connecting {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  padding: 32px;
  color: var(--text2);
  font-size: 13px;
}
.ms-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  animation: fadeSlideIn .25s ease;
}
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.ms-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
  position: relative;
}
.ms-rail::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: var(--border);
  transform: translateX(-50%);
}
.ms-item:first-child .ms-rail::before { top: 50%; }
.ms-item:last-child .ms-rail::before { bottom: 50%; }
.ms-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  z-index: 1;
  position: relative;
  flex-shrink: 0;
  margin: 6px 0;
}
.dot-blue { background: var(--accent); }
.dot-green { background: var(--green); }
.dot-red { background: var(--red); }
.dot-yellow { background: var(--yellow); }
.dot-purple { background: var(--purple); }
.dot-cyan { background: #22d3ee; }
.dot-gray { background: var(--text2); }
.ms-dot.pulse { animation: dotPulse 1.5s infinite; }
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50% { box-shadow: 0 0 0 4px transparent; }
}
.dot-blue.pulse { color: var(--accent); }
.dot-red.pulse { color: var(--red); }
.ms-body { flex: 1; min-width: 0; padding-right: 4px; }
.chat-row {
  gap: 0;
  padding: 16px 0;
}
.chat-row .ms-rail {
  display: none;
}
.chat-row .ms-body {
  display: flex;
  padding: 0;
}
.assistant-row .ms-body {
  justify-content: flex-start;
}
.user-row .ms-body {
  justify-content: flex-end;
}
.chat-message-wrap {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: min(100%, 900px);
}
.user-row .chat-message-wrap {
  justify-content: flex-end;
}
.chat-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .2px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .18);
}
.assistant-avatar {
  color: #dbeafe;
  background: linear-gradient(135deg, rgba(31, 111, 235, .92), rgba(88, 166, 255, .72));
}
.user-avatar {
  color: #dcfce7;
  background: linear-gradient(135deg, rgba(35, 134, 54, .92), rgba(63, 185, 80, .72));
}
.chat-bubble {
  min-width: 0;
  max-width: min(820px, calc(100% - 42px));
}
.assistant-bubble {
  color: var(--text);
  padding-top: 2px;
}
.user-bubble {
  background: linear-gradient(180deg, rgba(28, 35, 51, .96), rgba(22, 27, 34, .96));
  border: 1px solid rgba(139, 148, 158, .2);
  border-radius: 18px 18px 6px 18px;
  padding: 12px 15px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, .16);
}
.chat-name {
  margin-bottom: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--text2);
}
.user-bubble .chat-name {
  text-align: right;
  color: rgba(230, 237, 243, .66);
}
.ms-card { border-radius: 8px; overflow: hidden; }
.card-thinking {
  background: rgba(188,140,255,.05);
  border: 1px solid rgba(188,140,255,.15);
  border-radius: 8px;
  cursor: pointer;
}
.card-thinking:hover { background: rgba(188,140,255,.08); }
.ms-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 12px;
}
.ms-card-icon { font-size: 14px; }
.ms-card-title { font-weight: 600; color: var(--text2); }
.ms-card-toggle { margin-left: auto; font-size: 10px; color: var(--text2); transition: transform .2s; }
.ms-card-toggle.open { transform: rotate(90deg); }
.ms-thinking-content {
  padding: 8px 16px 12px;
  font-size: 12px;
  color: var(--text2);
  line-height: 1.6;
  font-family: 'SF Mono', 'Fira Code', monospace;
  border-top: 1px solid rgba(188,140,255,.1);
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}
.card-msg { background: transparent; border: none; }
.card-user { background: transparent; border: none; }
.msg-content { font-size: 14px; line-height: 1.78; color: var(--text); }
.assistant-bubble .msg-content { font-size: 15px; }
.user-bubble .msg-content { font-size: 14px; line-height: 1.65; }
.msg-content :deep(p) { margin: 4px 0; }
.msg-content :deep(p:first-child) { margin-top: 0; }
.msg-content :deep(p:last-child) { margin-bottom: 0; }
.msg-content :deep(code) {
  background: var(--surface2);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: var(--accent);
}
.msg-content :deep(pre) {
  background: var(--surface2);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  margin: 8px 0;
}
.msg-content :deep(pre code) { background: none; padding: 0; color: var(--text); }
.msg-content :deep(ul), .msg-content :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg-content :deep(strong) { font-weight: 700; color: #fff; }
.msg-content :deep(h1), .msg-content :deep(h2), .msg-content :deep(h3) { margin: 12px 0 4px; font-size: 15px; color: var(--accent); }
.msg-content :deep(blockquote) { border-left: 3px solid var(--accent); padding-left: 12px; color: var(--text2); margin: 8px 0; }
.msg-content :deep(table) { border-collapse: collapse; margin: 8px 0; width: 100%; }
.msg-content :deep(th), .msg-content :deep(td) { border: 1px solid var(--border); padding: 6px 10px; font-size: 12px; }
.msg-content :deep(th) { background: var(--surface2); font-weight: 600; }
.ms-tool,
.ms-progress,
.ms-sys,
.ms-stats,
.ms-complete,
.ms-thinking,
.ms-error,
.ms-hitl {
  max-width: 900px;
  margin: 0 auto;
}
.ms-tool .ms-rail,
.ms-progress .ms-rail,
.ms-sys .ms-rail,
.ms-stats .ms-rail,
.ms-complete .ms-rail,
.ms-thinking .ms-rail {
  opacity: .45;
}
.card-tool {
  border-radius: 12px;
  padding: 8px 10px;
  opacity: .88;
}
.tool-read { background: rgba(88,166,255,.05); border: 1px solid rgba(88,166,255,.12); }
.tool-write { background: rgba(63,185,80,.05); border: 1px solid rgba(63,185,80,.12); }
.tool-bash { background: rgba(210,153,34,.05); border: 1px solid rgba(210,153,34,.12); }
.tool-web { background: rgba(34,211,238,.05); border: 1px solid rgba(34,211,238,.12); }
.tool-skill { background: rgba(188,140,255,.05); border: 1px solid rgba(188,140,255,.12); }
.tool-default { background: var(--surface2); border: 1px solid var(--border); }
.tool-running {
  position: relative;
  overflow: hidden;
}
.tool-running::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.05), transparent);
  transform: translateX(-100%);
  animation: toolSweep 1.8s infinite;
  pointer-events: none;
}
.tool-complete::after { display: none; }
@keyframes toolSweep {
  to { transform: translateX(100%); }
}
.ms-tool-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(255,255,255,.04);
  color: var(--text);
  letter-spacing: .3px;
}
.ms-tool-id { font-size: 10px; color: var(--text2); font-family: monospace; }
.tool-state {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(88,166,255,.08);
  color: var(--accent);
}
.tool-state-ok { background: rgba(63,185,80,.1); color: var(--green); }
.tool-state-error { background: rgba(248,81,73,.1); color: var(--red); }
.tool-summary {
  padding: 0 8px 6px;
  font-size: 11px;
  color: var(--text2);
  line-height: 1.5;
}
.ms-tool-input {
  margin: 0 8px 6px;
  font-size: 12px;
  line-height: 1.5;
}
.ms-tool-input code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--accent);
  background: rgba(88,166,255,.06);
  padding: 6px 8px;
  border-radius: 4px;
  word-break: break-all;
  display: block;
}
.tool-result-inline { margin: 0 8px 2px; }
.ms-result-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
}
.result-ok { background: rgba(63,185,80,.05); color: var(--green); }
.result-err { background: rgba(248,81,73,.05); color: var(--red); }
.result-icon { font-weight: 700; flex-shrink: 0; }
.result-text {
  color: var(--text2);
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  max-height: 120px;
  overflow-y: auto;
  line-height: 1.5;
  word-break: break-all;
}
.ms-sys-card {
  font-size: 12px;
  color: var(--text2);
  padding: 6px 10px;
  background: rgba(139,148,158,.035);
  border-radius: 999px;
}
.ms-sys-card.sys-normal {
  border-left: 3px solid rgba(139,148,158,.35);
}
.ms-sys-card.sys-important {
  border-left: 3px solid rgba(210,153,34,.8);
  background: rgba(210,153,34,.05);
}
.ms-sys-card.sys-warning {
  border-left: 3px solid rgba(248,81,73,.85);
  background: rgba(248,81,73,.06);
}
.ms-sys-card strong { color: var(--text); }
.sys-icon { opacity: .9; }
.sys-details {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.sys-detail-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  background: rgba(255,255,255,.05);
  color: var(--text2);
}
.ms-stats-card {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: rgba(210,153,34,.04);
  border: 1px solid rgba(210,153,34,.1);
  border-radius: 12px;
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 14px; font-weight: 700; color: var(--yellow); font-variant-numeric: tabular-nums; }
.stat-lbl { font-size: 10px; color: var(--text2); text-transform: uppercase; }
.card-hitl {
  padding: 10px 14px;
  background: rgba(248,81,73,.05);
  border: 1px solid rgba(248,81,73,.15);
  border-radius: 8px;
}
.hitl-warn { font-size: 12px; color: var(--red); font-weight: 600; margin-bottom: 6px; }
.hitl-cmd { font-size: 11px; color: var(--text2); font-family: monospace; word-break: break-all; }
.ms-typing .ms-rail { display: none; }
.ms-typing .ms-body {
  max-width: 900px;
  margin: 0 auto;
}
.typing-indicator { display: flex; gap: 4px; padding: 8px 42px; }
.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  opacity: .4;
  animation: typingBounce 1.2s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: .2s; }
.typing-indicator span:nth-child(3) { animation-delay: .4s; }
@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: .4; }
  30% { transform: translateY(-4px); opacity: 1; }
}
.spinner-sm {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.card-question { border-left: 3px solid var(--purple); }
.ms-question-count {
  font-size: 11px;
  color: var(--text2);
  background: var(--surface2);
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: auto;
}
.question-list { padding: 10px 14px 6px; }
.question-block { margin-bottom: 16px; }
.question-block:last-child { margin-bottom: 8px; }
.question-header { margin-bottom: 6px; }
.q-chip {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: rgba(188, 140, 255, .1);
  color: var(--purple);
}
.question-text {
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
  margin-bottom: 8px;
  line-height: 1.45;
}
.question-num { color: var(--purple); font-weight: 700; margin-right: 4px; }
.question-options { display: flex; flex-direction: column; gap: 4px; padding-left: 2px; }
.question-option {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text);
  line-height: 1.45;
  transition: background .1s;
  border: 1px solid transparent;
}
.question-option:hover {
  background: rgba(188, 140, 255, .04);
  border-color: rgba(188, 140, 255, .1);
}
.question-option-empty { color: var(--text2); font-style: italic; }
.option-marker {
  flex-shrink: 0;
  width: 18px;
  text-align: center;
  color: var(--purple);
  font-size: 13px;
  margin-top: 1px;
}
.option-info { flex: 1; min-width: 0; }
.option-label { font-weight: 600; color: var(--text); }
.option-desc { color: var(--text2); font-size: 12px; margin-top: 2px; display: block; }
.option-preview { margin-top: 8px; }
.option-preview-chip {
  display: inline-block;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(188, 140, 255, .08);
  color: var(--purple);
  margin-bottom: 6px;
}
.option-preview-content {
  padding: 8px 12px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}
.option-preview-content :deep(pre) {
  background: var(--bg);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.option-preview-content :deep(code) {
  background: var(--bg);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--accent);
}
.option-preview-content :deep(pre code) { background: none; padding: 0; }
.question-type-badge {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(88, 166, 255, .1);
  color: var(--accent);
}
.card-progress {
  border-left: 3px solid var(--accent);
  border-radius: 12px;
  background: rgba(22, 27, 34, .54);
}
.card-progress.progress-completed { border-left-color: var(--green); }
.card-progress.progress-failed { border-left-color: var(--red); }
.progress-badge { margin-left: auto; }
.stage-chip {
  margin-left: auto;
  margin-right: 8px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 700;
  letter-spacing: .2px;
}
.stage-blue { background: rgba(88,166,255,.12); color: var(--accent); }
.stage-cyan { background: rgba(34,211,238,.12); color: #22d3ee; }
.stage-purple { background: rgba(188,140,255,.12); color: var(--purple); }
.stage-green { background: rgba(63,185,80,.12); color: var(--green); }
.stage-gray { background: rgba(139,148,158,.12); color: var(--text2); }
.progress-detail { padding: 6px 12px 2px; }
.progress-step { font-size: 13px; color: var(--text); line-height: 1.45; }
.progress-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
}
.progress-bar-wrapper .progress-bar {
  flex: 1;
  height: 6px;
  background: var(--surface2);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-wrapper .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent2), var(--accent));
  border-radius: 3px;
  transition: width .4s ease;
}
.card-progress.progress-completed .progress-fill { background: linear-gradient(90deg, #238636, var(--green)); }
.card-progress.progress-failed .progress-fill { background: linear-gradient(90deg, #da3633, var(--red)); }
.progress-text {
  font-size: 12px;
  color: var(--text2);
  flex-shrink: 0;
  min-width: 40px;
  text-align: right;
  font-weight: 600;
}
.sa-events {
  border-top: 1px solid var(--border);
  padding: 6px 12px;
  max-height: 260px;
  overflow-y: auto;
}
.sa-event {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.45;
  border-bottom: 1px solid rgba(48, 54, 61, .4);
}
.sa-event:last-child { border-bottom: none; }
.sa-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  font-size: 11px;
  color: var(--text2);
  margin-top: 2px;
}
.sa-label { color: var(--text2); font-weight: 600; font-size: 11px; flex-shrink: 0; }
.sa-fallback-preview {
  flex: 1;
  font-family: monospace;
  font-size: 10px;
  color: var(--text2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 720px) {
  .message-stream {
    padding: 14px 12px;
    border-radius: 14px;
  }
  .chat-row {
    padding: 13px 0;
  }
  .chat-avatar {
    width: 28px;
    height: 28px;
    border-radius: 9px;
  }
  .chat-message-wrap {
    gap: 9px;
  }
  .chat-bubble {
    max-width: calc(100% - 37px);
  }
  .user-bubble {
    padding: 10px 12px;
  }
  .assistant-bubble .msg-content {
    font-size: 14px;
  }
}
</style>
