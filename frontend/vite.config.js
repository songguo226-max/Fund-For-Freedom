import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

const frontendDir = fileURLToPath(new URL('.', import.meta.url))
const sharedAssetsDir = fileURLToPath(new URL('../assets', import.meta.url))
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8010'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    fs: {
      allow: [frontendDir, sharedAssetsDir],
    },
    proxy: {
      '/api': proxyTarget,
    },
  },
})
