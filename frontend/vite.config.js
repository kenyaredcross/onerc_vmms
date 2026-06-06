import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/assets/onerc_vmms/assets/',
  build: {
    outDir: '../onerc_vmms/public/assets',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://tanzania.localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/assets': {
        target: 'http://tanzania.localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
