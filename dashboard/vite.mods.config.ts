// Vite config used instead of the upstream one so the dashboard works when the
// browser is not on the same machine (cloud sessions, port previews).
// The client talks to /obs/* on its own origin; Vite forwards that to the server.
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const serverPort = process.env.SERVER_PORT || '4000'

export default defineConfig({
  plugins: [vue()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('/obs'),
    'import.meta.env.VITE_WS_URL': JSON.stringify('/obs/stream'),
  },
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.CLIENT_PORT || '5173'),
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/obs': {
        target: `http://localhost:${serverPort}`,
        ws: true,
        rewrite: (p) => p.replace(/^\/obs/, ''),
      },
    },
  },
})
