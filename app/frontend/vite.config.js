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
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            // Suppress EPIPE / ECONNRESET when backend is down or restarting
            if (err.code === 'EPIPE' || err.code === 'ECONNRESET' || err.code === 'ECONNREFUSED') {
              return;
            }
            console.error('[ws proxy]', err.message);
          });
          proxy.on('close', () => {
            // Proxy socket closed — expected during backend restart
          });
        },
      },
    },
  },
});
