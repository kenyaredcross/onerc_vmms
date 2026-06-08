import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const rawTarget = env.FRAPPE_URL || 'http://tanzania.localhost:8000'
  // Node.js cannot resolve *.localhost subdomains via DNS; use 127.0.0.1 and
  // forward the Host header so Frappe's multi-site routing works correctly.
  const targetUrl = new URL(rawTarget)
  const target = `${targetUrl.protocol}//127.0.0.1:${targetUrl.port || 80}`
  const proxyHost = targetUrl.hostname

  return {
    base: '/vmms/',
    plugins: [vue()],
    resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
    server: {
      port: 8080,
      proxy: {
        '/api':    { target, changeOrigin: true, secure: false, headers: { Host: proxyHost } },
        '/assets': { target, changeOrigin: true, headers: { Host: proxyHost } },
        '/files':  { target, changeOrigin: true, headers: { Host: proxyHost } },
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
