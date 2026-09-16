import nuxt from 'nuxt'

export default {
  devtools: { enabled: false },
  SSR: true,
  app: {
    head: {
      title: 'IDD Baseline Suite',
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
}
