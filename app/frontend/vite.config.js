import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { frontend, server as serverConfig } from '../../config/loader.mjs';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontend.port,
    proxy: {
      '/api': {
        target: frontend.backend_url,
        changeOrigin: true,
      },
      '/ws': {
        target: frontend.ws_url,
        ws: true,
      },
    },
  },
});
