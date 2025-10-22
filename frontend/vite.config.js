import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      jinjaBootData: true,
      lucideIcons: true,
      buildConfig: {
        indexHtmlPath: "../non_profit/www/vmms-portal.html",
        emptyOutDir: true,
        sourcemap: true,
      },
    }),

    vue(),

    /*
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'robots.txt'],
      manifest: {
        name: 'VMMS Portal',
        short_name: 'VMMS',
        start_url: '.',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#ff0000',
        icons: [],
      },
    }),
    */
  ],

  build: {
    outDir: "../non_profit/public/frontend",
    emptyOutDir: true,
    target: "es2015",
    sourcemap: true,
    chunkSizeWarningLimit: 1500,
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
    },
  },

  optimizeDeps: {
    include: [
      "feather-icons",
      "showdown",
      "highlight.js/lib/core",
      "interactjs",
    ],

    esbuildOptions: {
      define: {
        global: "globalThis",
      },
    },
  },

  server: {
    allowedHosts: true,
    port: 8080,
    open: true,
  },

  define: {
    "process.env": {},
  },
});
