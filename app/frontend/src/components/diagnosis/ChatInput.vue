<template>
  <div class="chat-input-bar">
    <div class="ci-row">
      <input
        ref="inputEl"
        v-model="text"
        type="text"
        :placeholder="placeholder"
        class="ci-input"
        @keydown.enter="send"
        :disabled="sending"
      />
      <button
        class="ci-send-btn"
        @click="send"
        :disabled="!text.trim() || sending"
      >
        {{ sendLabel }}
      </button>
    </div>
    <div class="ci-hint" v-if="hint">{{ hint }}</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue';

const props = defineProps({
  isRunning: { type: Boolean, default: false },
  terminalStatus: { type: String, default: '' },
  runId: { type: String, default: null },
});

const emit = defineEmits(['send-message', 'resume-with-message']);

const text = ref('');
const sending = ref(false);
const inputEl = ref(null);

const placeholder = computed(() => {
  if (props.terminalStatus === 'completed') return '输入追问，让系统基于当前结果继续分析...';
  if (props.terminalStatus === 'failed' || props.terminalStatus === 'stopped') return '输入补充指令并继续当前诊断...';
  if (props.isRunning) return '输入消息来引导当前诊断...';
  return '输入消息...';
});

const sendLabel = computed(() => {
  if (sending.value) return '发送中...';
  if (props.terminalStatus) return '发送并继续';
  return '发送';
});

const hint = computed(() => {
  if (props.terminalStatus === 'completed') return '当前运行已结束。你的消息会基于这次结果开启后续分析。';
  if (props.terminalStatus === 'failed' || props.terminalStatus === 'stopped') return '当前运行已结束。你的消息会带着上一轮上下文继续诊断。';
  if (props.isRunning) return '你的消息会发送给当前运行中的诊断流程，并在下一轮处理中生效。';
  return '';
});

async function send() {
  const msg = text.value.trim();
  if (!msg || sending.value) return;

  sending.value = true;
  try {
    if (props.terminalStatus) {
      emit('resume-with-message', msg);
    } else {
      emit('send-message', msg);
    }
    text.value = '';
  } finally {
    sending.value = false;
    nextTick(() => inputEl.value?.focus());
  }
}

function focus() {
  nextTick(() => inputEl.value?.focus());
}

defineExpose({ focus });
</script>

<style scoped>
.chat-input-bar {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 10px 14px;
  margin-top: 8px; flex-shrink: 0;
}

.ci-row {
  display: flex; align-items: center; gap: 8px;
}

.ci-input {
  flex: 1; background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 9px 14px; color: var(--text);
  font-size: 13px; font-family: inherit;
}
.ci-input:focus { outline: none; border-color: var(--accent); }
.ci-input:disabled { opacity: .5; }

.ci-send-btn {
  padding: 9px 18px; border: none; border-radius: 6px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  background: linear-gradient(135deg, var(--accent2), var(--accent));
  color: #fff; transition: all .15s; white-space: nowrap;
}
.ci-send-btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.ci-send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; }

.ci-hint {
  font-size: 11px; color: var(--text2); margin-top: 6px; line-height: 1.4;
}
</style>
