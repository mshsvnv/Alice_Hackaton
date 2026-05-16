import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// В Docker: VITE_API_PROXY_TARGET=http://backend:8000
// Локально: по умолчанию http://localhost:8000
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/docs': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
