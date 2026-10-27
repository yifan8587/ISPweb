import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 客户门户：开发期把 /api 与 /ws 代理到 ISPmanager。
// deploy/pack.sh 与 deploy/install.sh 会改写下一行默认地址。
// 也可用环境变量 VITE_API_PROXY_TARGET 临时覆盖。
// DEPLOY_API_PROXY_TARGET_BEGIN
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET || 'https://123.253.225.92:38080'
// DEPLOY_API_PROXY_TARGET_END

// 本机开发只走明文 HTTP。Daphne 在 8000，不提供 TLS。
// 用 https 去连会得到 SSL wrong version number。打包地址仍用上面的 API_PROXY_TARGET。
const DEV_PROXY_TARGET = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    target: 'es2022',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('element-plus')) return 'element-plus'
          if (id.includes('echarts') || id.includes('zrender') || id.includes('vue-echarts')) return 'echarts'
          if (id.includes('@novnc') || id.includes('/novnc/')) return 'novnc'
          if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) return 'vue'
        },
      },
    },
  },
  esbuild: { target: 'es2022' },
  optimizeDeps: {
    esbuildOptions: { target: 'es2022', supported: { 'top-level-await': true } },
  },
  server: {
    host: '0.0.0.0',
    port: 5180,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
