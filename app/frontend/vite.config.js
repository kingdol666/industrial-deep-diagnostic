import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { frontend, server as serverConfig } from '../../config/loader.mjs';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontend.port,
    watch: {
      // Atomic writes replace a file by creating `.<name>.<pid>.<uuid>.tmpdir/`
      // beside it, then renaming over the target. On Windows the watcher can
      // land on that directory mid-rename and raise EBUSY — an unhandled
      // 'error' event on FSWatcher, which kills the whole dev server rather
      // than just the one HMR update. These paths are never served, so
      // ignoring them costs nothing and makes edits crash-proof.
      ignored: ['**/.*.tmpdir/**', '**/*.tmp', '**/.mimosa/**'],
    },
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
