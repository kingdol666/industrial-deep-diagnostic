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
  isFailed: { type: Boolean, default: false },
  runId: { type: String, default: null },
});

const emit = defineEmits(['send-message', 'resume-with-message']);

const text = ref('');
const sending = ref(false);
const inputEl = ref(null);

const placeholder = computed(() => {
  if (props.isFailed) return 'Send a follow-up instruction and resume...';
  if (props.isRunning) return 'Send a message to guide the analysis...';
  return 'Type a message...';
});

const sendLabel = computed(() => {
  if (sending.value) return 'Sending...';
  if (props.isFailed) return 'Send & Resume';
  return 'Send';
});

const hint = computed(() => {
  if (props.isFailed) return 'The process ended. Your message will start a new analysis session with context from the previous run.';
  if (props.isRunning) return 'Your message will be sent to the running analysis. Claude will process it in the next turn.';
  return '';
});

async function send() {
  const msg = text.value.trim();
  if (!msg || sending.value) return;

  sending.value = true;
  try {
    if (props.isFailed) {
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
