import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.FRAPPE_URL || 'http://tanzania.localhost:8000'

  return {
    plugins: [vue()],
    resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
    server: {
      port: 8080,
      proxy: {
        '/api':    { target, changeOrigin: true, secure: false },
        '/assets': { target, changeOrigin: true },
        '/files':  { target, changeOrigin: true },
      }
    },
    build: {
      outDir: '../onerc_vmms/public/vmms',
      emptyOutDir: true,
      rollupOptions: {
        output: {
          entryFileNames: 'assets/index.js',
          chunkFileNames: 'assets/[name].js',
          assetFileNames: 'assets/[name].[ext]',
        }
      }
    }
  }
})
