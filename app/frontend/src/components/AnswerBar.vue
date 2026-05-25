<template>
  <div class="answer-bar" v-if="currentQuestion">
    <div class="ab-header">
      <span class="ab-icon">❓</span>
      <span class="ab-title">Claude needs your input</span>
      <span class="ab-count" v-if="currentQuestion.questions.length > 1">
        {{ answeredCount + 1 }}/{{ currentQuestion.questions.length }}
      </span>
      <button class="ab-close" @click="$emit('skip', currentQuestion.questionId)">Skip All</button>
    </div>

    <div class="ab-body">
      <div
        v-for="(q, qi) in currentQuestion.questions"
        :key="qi"
        class="ab-question"
      >
        <div class="ab-q-text">
          <span class="ab-q-num">{{ qi + 1 }}.</span>
          {{ q.question }}
        </div>
        <div class="ab-q-options">
          <template v-if="q.multiSelect">
            <label
              v-for="(opt, oi) in q.options"
              :key="oi"
              :class="['ab-opt', { selected: isSelected(qi, opt.label) }]"
            >
              <input
                type="checkbox"
                :checked="isSelected(qi, opt.label)"
                @change="toggleMulti(qi, opt.label)"
              />
              <span>{{ opt.label }}</span>
              <span class="ab-opt-desc" v-if="opt.description"> — {{ opt.description }}</span>
            </label>
          </template>
          <template v-else>
            <label
              v-for="(opt, oi) in q.options"
              :key="oi"
              :class="['ab-opt', { selected: answers[qi] === opt.label }]"
            >
              <input
                type="radio"
                :name="'q_' + qi"
                :value="opt.label"
                :checked="answers[qi] === opt.label"
                @change="selectSingle(qi, opt.label)"
              />
              <span>{{ opt.label }}</span>
              <span class="ab-opt-desc" v-if="opt.description"> — {{ opt.description }}</span>
            </label>
          </template>
          <!-- Custom input for "Other" -->
          <div class="ab-custom">
            <span class="ab-custom-label">Other:</span>
            <input
              v-model="customAnswers[qi]"
              type="text"
              placeholder="Type your answer..."
              class="ab-custom-input"
              @input="onCustomInput(qi)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="ab-actions">
      <button class="ab-btn ab-btn-skip" @click="skipCurrent">
        Skip
      </button>
      <button class="ab-btn ab-btn-submit" @click="submitAnswers" :disabled="!hasAnyAnswer">
        Submit Answer
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  questionData: { type: Object, default: null },
  runId: { type: String, default: null },
});

const emit = defineEmits(['answer', 'skip']);

const currentQuestion = ref(null);
const answers = ref({});
const customAnswers = ref({});
const answeredCount = ref(0);

watch(() => props.questionData, (qd) => {
  if (qd) {
    currentQuestion.value = qd;
    answers.value = {};
    customAnswers.value = {};
    answeredCount.value = 0;
  } else {
    currentQuestion.value = null;
    answers.value = {};
    customAnswers.value = {};
  }
});

function isSelected(qi, label) {
  const ans = answers.value[qi];
  if (Array.isArray(ans)) return ans.includes(label);
  return ans === label;
}

function selectSingle(qi, label) {
  answers.value[qi] = label;
  answeredCount.value = Object.keys(answers.value).filter(k => answers.value[k] != null && answers.value[k] !== '').length;
}

function toggleMulti(qi, label) {
  if (!Array.isArray(answers.value[qi])) {
    answers.value[qi] = [];
  }
  const arr = answers.value[qi];
  const idx = arr.indexOf(label);
  if (idx >= 0) arr.splice(idx, 1);
  else arr.push(label);
  answeredCount.value = Object.keys(answers.value).filter(k => {
    const v = answers.value[k];
    return v != null && (Array.isArray(v) ? v.length > 0 : v !== '');
  }).length;
}

function onCustomInput(qi) {
  const val = customAnswers.value[qi];
  if (val) {
    if (currentQuestion.value?.questions[qi]?.multiSelect) {
      if (!Array.isArray(answers.value[qi])) answers.value[qi] = [];
      // custom answer tracked separately
    } else {
      answers.value[qi] = val;
    }
  }
  answeredCount.value = Object.keys(answers.value).filter(k => {
    const v = answers.value[k];
    return v != null && (Array.isArray(v) ? v.length > 0 : v !== '');
  }).length;
}

const hasAnyAnswer = computed(() => answeredCount.value > 0);

function buildAnswers() {
  const result = {};
  if (!currentQuestion.value) return result;
  currentQuestion.value.questions.forEach((q, qi) => {
    let ans = answers.value[qi];
    const custom = customAnswers.value[qi];
    if (custom) {
      if (Array.isArray(ans)) {
        ans = [...ans, custom];
      } else if (ans) {
        ans = ans + '; ' + custom;
      } else {
        ans = custom;
      }
    }
    if (ans != null && ans !== '' && !(Array.isArray(ans) && ans.length === 0)) {
      result[q.question] = Array.isArray(ans) ? ans.join(', ') : ans;
    }
  });
  return result;
}

function submitAnswers() {
  if (!currentQuestion.value) return;
  const ans = buildAnswers();
  if (Object.keys(ans).length === 0) return;

  emit('answer', {
    questionId: currentQuestion.value.questionId,
    toolUseId: currentQuestion.value.toolUseId,
    answers: ans,
  });
  currentQuestion.value = null;
  answers.value = {};
  customAnswers.value = {};
}

function skipCurrent() {
  if (currentQuestion.value) {
    emit('skip', currentQuestion.value.questionId);
  }
  currentQuestion.value = null;
  answers.value = {};
  customAnswers.value = {};
}
</script>

<style scoped>
.answer-bar {
  background: var(--surface); border: 1px solid rgba(188,140,255,.25);
  border-radius: var(--radius); overflow: hidden;
  margin-top: 8px; flex-shrink: 0;
}

.ab-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px;
  background: rgba(188,140,255,.06);
  border-bottom: 1px solid rgba(188,140,255,.1);
}

.ab-icon { font-size: 16px; }

.ab-title {
  font-size: 13px; font-weight: 700; color: var(--purple);
  flex: 1;
}

.ab-count { font-size: 11px; color: var(--text2); background: var(--surface2); padding: 2px 8px; border-radius: 10px; }

.ab-close {
  background: none; border: none; color: var(--text2);
  font-size: 12px; cursor: pointer; padding: 4px 8px; border-radius: 4px;
}
.ab-close:hover { color: var(--red); background: rgba(248,81,73,.08); }

.ab-body { padding: 12px 16px; max-height: 300px; overflow-y: auto; }

.ab-question { margin-bottom: 12px; }
.ab-question:last-child { margin-bottom: 0; }

.ab-q-text {
  font-size: 13px; color: var(--text); font-weight: 600;
  margin-bottom: 8px; line-height: 1.4;
}
.ab-q-num { color: var(--purple); font-weight: 700; margin-right: 4px; }

.ab-q-options { display: flex; flex-direction: column; gap: 4px; }

.ab-opt {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 10px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: var(--text); transition: background .1s;
}
.ab-opt:hover { background: var(--surface2); }
.ab-opt.selected { background: rgba(88,166,255,.08); }
.ab-opt input { margin-top: 3px; flex-shrink: 0; }
.ab-opt-desc { color: var(--text2); font-size: 12px; }

.ab-custom {
  display: flex; align-items: center; gap: 8px; margin-top: 4px;
  padding: 4px 10px;
}
.ab-custom-label { font-size: 12px; color: var(--text2); flex-shrink: 0; }
.ab-custom-input {
  flex: 1; background: var(--surface2); border: 1px solid var(--border);
  border-radius: 4px; padding: 4px 8px; color: var(--text);
  font-size: 12px; font-family: inherit;
}
.ab-custom-input:focus { outline: none; border-color: var(--accent); }

.ab-actions {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 10px 16px; border-top: 1px solid var(--border);
}

.ab-btn {
  padding: 7px 18px; border-radius: 6px; font-size: 13px;
  font-weight: 600; cursor: pointer; border: none; transition: all .15s;
}
.ab-btn-skip { background: transparent; color: var(--text2); border: 1px solid var(--border); }
.ab-btn-skip:hover { color: var(--text); border-color: var(--text2); }
.ab-btn-submit { background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff; }
.ab-btn-submit:hover { opacity: .9; }
.ab-btn-submit:disabled { opacity: .4; cursor: not-allowed; }
</style>
