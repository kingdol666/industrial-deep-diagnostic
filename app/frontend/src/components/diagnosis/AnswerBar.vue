<template>
  <div class="answer-bar" v-if="currentQuestion">
    <!-- Header -->
    <div class="ab-header">
      <div class="ab-header-left">
        <span class="ab-icon">❓</span>
        <span class="ab-title">Claude needs your input</span>
        <span class="ab-count" v-if="totalQuestions > 1">
          {{ answeredCount }}/{{ totalQuestions }} answered
        </span>
      </div>
      <button class="ab-skip-all" @click="$emit('skip', currentQuestion.questionId)">
        Skip All
      </button>
    </div>

    <!-- Question Blocks -->
    <div class="ab-body">
      <div
        v-for="(q, qi) in currentQuestion.questions"
        :key="qi"
        class="ab-question-block"
      >
        <!-- Question chip -->
        <div class="ab-q-header">
          <template v-if="q.header">
            <span class="ab-q-chip">{{ q.header }}</span>
          </template>
          <span class="ab-q-text">{{ q.question }}</span>
          <span class="ab-q-type" v-if="q.multiSelect">(select all that apply)</span>
        </div>

        <!-- Options grid -->
        <div class="ab-options-grid">
          <div
            v-for="(opt, oi) in q.options"
            :key="oi"
            :class="[
              'ab-option-card',
              {
                selected: isOptionSelected(qi, opt.label),
                'has-preview': !!opt.preview,
              },
            ]"
            @click="selectOption(qi, opt, q.multiSelect)"
          >
            <div class="ab-option-main">
              <div class="ab-option-radio">
                <span v-if="!isOptionSelected(qi, opt.label)" class="radio-ring"></span>
                <span v-else class="radio-dot">●</span>
              </div>
              <div class="ab-option-content">
                <div class="ab-option-label">{{ opt.label }}</div>
                <div class="ab-option-desc" v-if="opt.description">{{ opt.description }}</div>
              </div>
            </div>
          </div>

          <!-- Custom "Other" input -->
          <div class="ab-option-card ab-option-other" :class="{ selected: customAnswers[qi] }">
            <div class="ab-option-main">
              <div class="ab-option-radio">
                <span v-if="!customAnswers[qi]" class="radio-ring other-ring"></span>
                <span v-else class="radio-dot other-dot">●</span>
              </div>
              <div class="ab-option-content">
                <div class="ab-option-label other-label">Other</div>
                <input
                  v-model="customAnswers[qi]"
                  type="text"
                  placeholder="Type your own answer..."
                  class="ab-other-input"
                  @click.stop
                  @focus="focusOther(qi)"
                  @input="onOtherInput(qi)"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Multi-select tags -->
        <div v-if="q.multiSelect && multiSelections[qi]?.length" class="ab-selected-tags">
          <span
            v-for="(label, si) in multiSelections[qi]"
            :key="si"
            class="ab-tag"
            @click.stop="removeMulti(qi, label)"
          >
            {{ label }}
            <span class="ab-tag-x">×</span>
          </span>
        </div>
      </div>
    </div>

    <!-- Preview Panel -->
    <div v-if="activePreview" class="ab-preview-panel">
      <div class="ab-preview-header">
        <span class="ab-preview-icon">👁</span>
        <span class="ab-preview-title">Preview — {{ activePreviewLabel }}</span>
        <button class="ab-preview-close" @click="closePreview">×</button>
      </div>
      <div class="ab-preview-content" v-html="renderPreviewMd(activePreview)"></div>
    </div>

    <!-- Actions -->
    <div class="ab-actions">
      <div class="ab-actions-left">
        <span class="ab-hint" v-if="!hasAllAnswered && totalQuestions > 1">
          Answer all questions to submit, or use chat below to continue instead
        </span>
      </div>
      <div class="ab-actions-right">
        <button class="ab-btn-skip" @click="skipCurrent">
          Skip
        </button>
        <button
          class="ab-btn-submit"
          :disabled="!hasAnyAnswer"
          @click="submitAnswers"
        >
          Submit &amp; Continue
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { renderMarkdown } from '../../utils/markdown.js';

const props = defineProps({
  questionData: { type: Object, default: null },
  runId: { type: String, default: null },
});

const emit = defineEmits(['answer', 'skip']);

const currentQuestion = ref(null);
const answers = ref({});
const customAnswers = ref({});
const answeredCount = ref(0);
const activePreview = ref('');
const activePreviewLabel = ref('');

const totalQuestions = computed(() => currentQuestion.value?.questions?.length || 0);

const hasAnyAnswer = computed(() => answeredCount.value > 0);
const hasAllAnswered = computed(() => answeredCount.value >= totalQuestions.value);

// Multi-select state (per question index, array of labels)
const multiSelections = computed(() => {
  const map = {};
  for (const [qi, ans] of Object.entries(answers.value)) {
    if (Array.isArray(ans)) {
      map[qi] = ans;
    }
  }
  return map;
});

watch(() => props.questionData, (qd) => {
  if (qd) {
    currentQuestion.value = qd;
    answers.value = {};
    customAnswers.value = {};
    answeredCount.value = 0;
    activePreview.value = '';
    activePreviewLabel.value = '';
  } else {
    currentQuestion.value = null;
    answers.value = {};
    customAnswers.value = {};
  }
});

function isOptionSelected(qi, label) {
  const ans = answers.value[qi];
  if (Array.isArray(ans)) return ans.includes(label);
  return ans === label;
}

function selectOption(qi, opt, multi) {
  // Preview logic: toggle preview when option has preview content
  if (opt.preview) {
    if (activePreview.value === opt.preview && activePreviewLabel.value === opt.label) {
      closePreview();
    } else {
      activePreview.value = opt.preview;
      activePreviewLabel.value = opt.label;
    }
  }

  // For single-select that's already selected: deselect does NOT toggle preview
  if (!multi && answers.value[qi] === opt.label) {
    answers.value[qi] = null;
    recalcCount();
    return;
  }

  if (multi) {
    // Multi-select toggle
    const prev = Array.isArray(answers.value[qi]) ? [...answers.value[qi]] : [];
    const idx = prev.indexOf(opt.label);
    if (idx >= 0) {
      prev.splice(idx, 1);
    } else {
      prev.push(opt.label);
    }
    answers.value[qi] = prev;
    // Clear other if multi
    if (customAnswers.value[qi] && prev.length > 0) {
      customAnswers.value[qi] = '';
    }
  } else {
    // Single-select: pick this option, clear any custom input
    answers.value[qi] = opt.label;
    if (customAnswers.value[qi]) {
      customAnswers.value[qi] = '';
    }
  }
  recalcCount();
}

function focusOther(qi) {
  if (!currentQuestion.value?.questions[qi]?.multiSelect) {
    answers.value[qi] = null;
  }
}

function onOtherInput(qi) {
  if (customAnswers.value[qi]) {
    if (!currentQuestion.value?.questions[qi]?.multiSelect) {
      answers.value[qi] = customAnswers.value[qi];
    }
  }
  recalcCount();
}

function removeMulti(qi, label) {
  if (Array.isArray(answers.value[qi])) {
    answers.value[qi] = answers.value[qi].filter(l => l !== label);
  }
  recalcCount();
}

function recalcCount() {
  let count = 0;
  for (const k of Object.keys(answers.value)) {
    const v = answers.value[k];
    if (v != null && (Array.isArray(v) ? v.length > 0 : v !== '')) {
      count++;
    }
  }
  // Also count custom answers
  for (const k of Object.keys(customAnswers.value)) {
    if (customAnswers.value[k] && !answers.value[k]) {
      count++;
    }
  }
  answeredCount.value = count;
}

function closePreview() {
  activePreview.value = '';
  activePreviewLabel.value = '';
}

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

function skipCurrent() {
  if (currentQuestion.value) {
    // Build placeholder answers so Claude can continue
    const placeholder = {};
    const questions = currentQuestion.value.questions || [];
    for (let qi = 0; qi < questions.length; qi++) {
      placeholder[questions[qi].question] = '(skipped)';
    }
    emit('answer', {
      questionId: currentQuestion.value.questionId,
      toolUseId: currentQuestion.value.toolUseId,
      answers: placeholder,
    });
  }
  currentQuestion.value = null;
  answers.value = {};
  customAnswers.value = {};
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

function renderPreviewMd(text) {
  return renderMarkdown(text);
}
</script>

<style scoped>
.answer-bar {
  background: var(--surface);
  border: 1px solid rgba(188, 140, 255, .25);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 8px;
  flex-shrink: 0;
}

/* ── Header ── */
.ab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(188, 140, 255, .06);
  border-bottom: 1px solid rgba(188, 140, 255, .1);
}

.ab-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ab-icon { font-size: 18px; }

.ab-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--purple);
}

.ab-count {
  font-size: 11px;
  color: var(--text2);
  background: var(--surface2);
  padding: 2px 10px;
  border-radius: 10px;
}

.ab-skip-all {
  background: none;
  border: 1px solid var(--border);
  color: var(--text2);
  font-size: 12px;
  cursor: pointer;
  padding: 5px 12px;
  border-radius: 6px;
  transition: all .15s;
}
.ab-skip-all:hover {
  color: var(--red);
  border-color: var(--red);
  background: rgba(248, 81, 73, .06);
}

/* ── Body ── */
.ab-body {
  padding: 16px 20px;
  max-height: 420px;
  overflow-y: auto;
}

.ab-question-block {
  margin-bottom: 20px;
}
.ab-question-block:last-child { margin-bottom: 0; }

.ab-q-header {
  margin-bottom: 12px;
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.ab-q-chip {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: rgba(188, 140, 255, .12);
  color: var(--purple);
  flex-shrink: 0;
}

.ab-q-text {
  font-size: 14px;
  color: var(--text);
  font-weight: 600;
  line-height: 1.4;
}

.ab-q-type {
  font-size: 12px;
  color: var(--text2);
  font-weight: 400;
  font-style: italic;
}

/* ── Options Grid ── */
.ab-options-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ── Option Card ── */
.ab-option-card {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all .15s ease;
  position: relative;
  background: var(--surface);
}
.ab-option-card:hover {
  border-color: rgba(188, 140, 255, .3);
  background: rgba(188, 140, 255, .03);
}
.ab-option-card.selected {
  border-color: var(--purple);
  background: rgba(188, 140, 255, .08);
  box-shadow: 0 0 0 1px rgba(188, 140, 255, .2);
}
.ab-option-card.has-preview {
  cursor: pointer;
}
.ab-option-card.has-preview::after {
  content: '👁 Click to preview';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--text2);
  opacity: 0;
  transition: opacity .15s;
  pointer-events: none;
}
.ab-option-card.has-preview:hover::after {
  opacity: .7;
}

.ab-option-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  width: 100%;
}

.ab-option-radio {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}

.radio-ring {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  transition: all .15s;
}
.ab-option-card:hover .radio-ring { border-color: rgba(188, 140, 255, .4); }
.ab-option-card.selected .radio-ring { border-color: var(--purple); }

.radio-dot {
  font-size: 20px;
  line-height: 1;
  color: var(--purple);
}

.other-ring {
  border-style: dashed;
  border-color: var(--border);
}
.other-dot {
  color: var(--accent);
}

.ab-option-content {
  flex: 1;
  min-width: 0;
}

.ab-option-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
}

.ab-option-desc {
  font-size: 12px;
  color: var(--text2);
  margin-top: 3px;
  line-height: 1.4;
}

/* ── Other Input ── */
.ab-option-other {
  background: transparent;
}

.other-label {
  color: var(--text2);
  font-style: italic;
}

.ab-other-input {
  margin-top: 6px;
  width: 100%;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  transition: border-color .15s;
}
.ab-other-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(88, 166, 255, .1);
}
.ab-other-input::placeholder {
  color: var(--text2);
  opacity: .5;
}

/* ── Selected Tags (multi-select) ── */
.ab-selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  padding-left: 32px;
}

.ab-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 16px;
  background: rgba(188, 140, 255, .12);
  color: var(--purple);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background .15s;
}
.ab-tag:hover {
  background: rgba(248, 81, 73, .15);
  color: var(--red);
}

.ab-tag-x {
  font-size: 14px;
  font-weight: 700;
  opacity: .6;
}

/* ── Preview Panel ── */
.ab-preview-panel {
  border-top: 1px solid rgba(188, 140, 255, .15);
  background: rgba(30, 35, 50, .6);
  max-height: 280px;
  overflow-y: auto;
}

.ab-preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(188, 140, 255, .06);
  border-bottom: 1px solid rgba(188, 140, 255, .08);
  position: sticky;
  top: 0;
  z-index: 1;
}

.ab-preview-icon { font-size: 14px; }
.ab-preview-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--purple);
  flex: 1;
}

.ab-preview-close {
  background: none;
  border: none;
  color: var(--text2);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  border-radius: 4px;
}
.ab-preview-close:hover { color: var(--red); }

.ab-preview-content {
  padding: 16px 20px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
}

.ab-preview-content :deep(pre) {
  background: var(--surface2);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  border: 1px solid var(--border);
}

.ab-preview-content :deep(code) {
  background: var(--surface2);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: var(--accent);
}

.ab-preview-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text);
}

/* ── Actions ── */
.ab-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: rgba(0, 0, 0, .1);
}

.ab-actions-left { flex: 1; }

.ab-actions-right {
  display: flex;
  gap: 8px;
}

.ab-hint {
  font-size: 12px;
  color: var(--text2);
}

.ab-btn-skip {
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text2);
  transition: all .15s;
}
.ab-btn-skip:hover {
  color: var(--text);
  border-color: var(--text2);
  background: var(--surface2);
}

.ab-btn-submit {
  padding: 9px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  background: linear-gradient(135deg, var(--accent2), var(--accent));
  color: #fff;
  transition: all .15s;
  box-shadow: 0 2px 8px rgba(31, 111, 235, .25);
}
.ab-btn-submit:hover:not(:disabled) {
  opacity: .9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 111, 235, .35);
}
.ab-btn-submit:active:not(:disabled) {
  transform: translateY(0);
}
.ab-btn-submit:disabled {
  opacity: .35;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
