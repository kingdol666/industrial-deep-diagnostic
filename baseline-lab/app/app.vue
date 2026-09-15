<script setup>
// Application shell: sidebar navigation + a global state fetch shared by pages.
const { data: state, refresh } = await useFetch('/api/state', { key: 'lab-state' });
provide('lab-state', { state, refresh });

const nav = [
  { to: '/', num: '01', label: '复现审计', hint: 'Audit' },
  { to: '/custom', num: '02', label: '自建数据诊断', hint: 'Your data' },
  { to: '/run', num: '03', label: '运行基线', hint: 'Run' },
  { to: '/results', num: '04', label: '结果对比', hint: 'Results' },
  { to: '/algorithms', num: '05', label: '算法清单', hint: 'Algorithms' },
  { to: '/cases', num: '06', label: '场景与数据', hint: 'Cases' },
];
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">BL</div>
        <div class="brand-text">Baseline Lab</div>
      </div>
      <div class="brand-sub">IDD benchmark</div>

      <nav class="nav">
        <NuxtLink v-for="n in nav" :key="n.to" :to="n.to">
          <span class="num">{{ n.num }}</span>
          <span>{{ n.label }}</span>
        </NuxtLink>
      </nav>

      <div style="margin-top: 22px; border-top: 1px solid var(--line); padding-top: 14px">
        <div class="tiny muted" style="text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px">
          LLM provider
        </div>
        <div v-if="state?.resolved_provider">
          <span class="badge ok">{{ state.resolved_provider.id }}</span>
        </div>
        <div v-else>
          <span class="badge warn">none</span>
          <div class="tiny muted" style="margin-top: 6px">
            LLM 基线将报告 skipped_no_provider（不编造答案）
          </div>
        </div>
      </div>

      <div v-if="state?.comparability?.status === 'different_model'" style="margin-top: 18px">
        <div class="tiny muted" style="text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px">
          可比性
        </div>
        <span class="badge bad">model confound</span>
        <div class="tiny muted" style="margin-top: 6px">
          归档基线模型 ≠ 本次调用模型，LLM 数字不可直比。
        </div>
      </div>

      <div style="margin-top: 18px">
        <div class="tiny muted" style="text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px">
          算法覆盖
        </div>
        <div class="tiny dim mono">
          {{ state?.headline?.lab_algorithms_runnable ?? '—' }} runnable
          <span v-if="state?.headline?.lab_modules_missing" style="color: var(--warn)">
            / {{ state.headline.lab_modules_missing }} missing
          </span>
        </div>
        <div class="tiny muted mono" style="margin-top: 3px">
          {{ state?.cases?.length ?? '—' }} cases · {{ state?.sweeps?.length ?? 0 }} sweeps
        </div>
      </div>
    </aside>

    <main class="main">
      <NuxtPage />
    </main>
  </div>
</template>
