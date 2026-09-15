// IDD Baseline Lab — Nuxt config.
//
// The lab is a *sibling* of the IDD repository: it reads the repo's benchmark
// cases, datasets and truth files as the single source of truth, and never
// writes into them. All lab output lands under baseline-lab/results/.
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: false },

  // Server routes shell out to harness CLIs (claude/dsh/codex/...) for the LLM
  // comparators, and read multi-hundred-KB CSVs; give Nitro room.
  nitro: {
    experimental: { asyncContext: true },
    // Every server module imports explicitly. Leaving `dirs` empty stops Nitro
    // from scanning server/utils/** for auto-imports, which would otherwise
    // collide on the `meta` / `run` exports that every algorithm module shares.
    imports: { dirs: [] },
    routeRules: {
      '/api/**': { cors: true },
    },
  },

  runtimeConfig: {
    // Repo root; overridable with NUXT_IDD_REPO_ROOT.
    iddRepoRoot: process.env.IDD_REPO_ROOT || '..',
    // LLM comparator provider settings (see server/utils/llm/provider.mjs).
    llmProvider: process.env.BASELINE_LLM_PROVIDER || 'auto',
    llmModel: process.env.BASELINE_LLM_MODEL || '',
    llmBaseUrl: process.env.BASELINE_LLM_BASE_URL || '',
    llmApiKey: process.env.BASELINE_LLM_API_KEY || '',
    llmCli: process.env.BASELINE_LLM_CLI || 'claude',
    llmTimeoutMs: process.env.BASELINE_LLM_TIMEOUT_MS || '300000',
  },

  app: {
    head: {
      title: 'IDD Baseline Lab',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Runnable reproductions of comparator diagnostic algorithms for the Industrial Deep Diagnostic benchmark.',
        },
      ],
    },
  },

  css: ['~/assets/css/main.css'],
})
