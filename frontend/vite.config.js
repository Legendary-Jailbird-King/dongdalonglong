import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,   // 暴露到局域网，另一台电脑才能访问
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',   // 本机用 127.0.0.1
        // 另一台电脑自己跑前端时改为: http://10.31.95.247:8001
        changeOrigin: true,
        ws: true,   // 支持 WebSocket
      },
    },
  },
})
