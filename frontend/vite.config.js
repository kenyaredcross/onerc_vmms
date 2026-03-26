import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
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
