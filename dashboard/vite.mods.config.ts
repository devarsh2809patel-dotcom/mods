// Vite config used instead of the upstream one so the dashboard works when the
// browser is not on the same machine (cloud sessions, port previews).
// The client talks to /obs/* on its own origin; Vite forwards that to the server.
// On a personal computer the page listens on this machine only; in a Claude cloud
// session it listens on all interfaces so the app's port preview can reach it.
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const serverPort = process.env.SERVER_PORT || '4000'
const isCloud = process.env.CLAUDE_CODE_REMOTE === 'true'

export default defineConfig({
  plugins: [vue()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('/obs'),
    'import.meta.env.VITE_WS_URL': JSON.stringify('/obs/stream'),
  },
  server: {
    host: isCloud ? '0.0.0.0' : '127.0.0.1',
    port: parseInt(process.env.CLIENT_PORT || '5173'),
    strictPort: true,
    allowedHosts: isCloud ? true : undefined,
    proxy: {
      '/obs': {
        target: `http://127.0.0.1:${serverPort}`,
        ws: true,
        rewrite: (p) => p.replace(/^\/obs/, ''),
      },
    },
  },
})
