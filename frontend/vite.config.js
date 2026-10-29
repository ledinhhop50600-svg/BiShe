import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  server: {
    port: 5173,
    proxy: {
      // 前端以 /api 开头的请求转发给后端 8080 端口，避免浏览器跨域问题。
      // 后端地址可用环境变量 VITE_BACKEND_TARGET 覆盖（例如换端口调试时使用）。
      '/api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  preview: {
    // 生产构建的本地预览：不跑 Vite dev 的模块转换与 HMR，内存明显更低。
    port: 4173,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
