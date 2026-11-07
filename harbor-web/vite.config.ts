import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const SHOP_TARGET = process.env.VITE_SHOP_PROXY || 'http://127.0.0.1:8787'

export default defineConfig({
  base: '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
    proxy: {
      // /harbor-api is for XHR/fetch only. User-facing shop HTML must open shopOrigin (8787), never this path.
      '/harbor-api': {
        target: SHOP_TARGET,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/harbor-api/, ''),
        cookieDomainRewrite: '',
        cookiePathRewrite: '/',
        ws: true,
      },
    },
  },
})
